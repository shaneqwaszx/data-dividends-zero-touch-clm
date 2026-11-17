"""D-120 physical proof: the POC ledger survives a restart in a fresh allowlisted database."""

import os
from collections.abc import Iterator
from copy import deepcopy
from typing import Any

import pytest
import test_poc_ownership_acceptance as t
from fastapi.testclient import TestClient
from pymongo import MongoClient
from scripts.mongo_test_safety import (
    cleanup_ephemeral_mongo_database,
    generate_ephemeral_mongo_database,
)
from test_official_shareholder_evidence import POC_REFUSAL
from test_opq_garden_abc_scenario import MULTI, transport
from test_poc_evidence_identity_guard import CORRECTED, Lane

from app.composition import build_acra_connector
from app.config import Settings
from app.main import create_app
from app.persistence.composition import build_persistence_bundle

URI = os.environ.get("PHASE12_MONGO_URI")
pytestmark = pytest.mark.skipif(not URI, reason="PHASE12_MONGO_URI is not configured")


@pytest.fixture
def physical() -> Iterator[tuple[Settings, Any]]:
    assert URI is not None
    database = generate_ephemeral_mongo_database("p16")
    settings = t.lane(
        **MULTI, clm_persistence_mode="mongo", mongo_uri=URI, mongo_database=database
    )
    client: MongoClient[dict[str, Any]] = MongoClient(URI)
    try:
        client.admin.command("ping")
        yield settings, client[database][settings.mongo_case_collection]
    finally:
        try:
            cleanup_ephemeral_mongo_database(client, database)
        finally:
            client.close()


def application(settings: Settings) -> TestClient:
    """One process lifetime: the composition builds its own Mongo persistence."""

    protocol = transport()
    connector = build_acra_connector(
        settings, transport=protocol, marketplace_token_transport=protocol
    )
    return TestClient(create_app(settings, acra_connector=connector))


class Restarted(Lane):
    """A fresh composition over the same durable case: nothing is carried in memory."""

    def __init__(self, client: Any, bundle: Any, case_id: str) -> None:
        self.client, self.bundle, self.case_id = client, bundle, case_id


def corrected(step: int) -> dict[str, str]:
    return {"ABCD123": str(70 + step), "TAN WEI LING": str(20 - step), "EFGH2345": "10"}


def assert_refused(response: Any) -> None:
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == POC_REFUSAL


def test_the_ledger_survives_restart_and_the_evidence_route_still_works(physical: Any) -> None:
    settings, cases = physical
    bundle = build_persistence_bundle(settings)
    with application(settings) as client:
        first = Lane(client, bundle)
        case_id, graph = first.case_id, first.ownership()
        # Evidence arrives while the case is under review, as the workflow offers it.
        first.upload(first.observation_rows())
        graph = first.ownership()
        for step in range(1, 7):
            declared = first.declare(graph=graph, rekey=True, percents=corrected(step))
            assert declared.status_code == 200, declared.text
    raw = cases.find_one({"_id": case_id})
    assert raw is not None and raw["schema_version"] == 21
    assert raw["ownership"]["poc_interest_ledger"]
    assert len(raw["ownership"]["prior_analyses"]) == 4
    assert graph["analysis_id"] not in {
        item["analysis_id"] for item in raw["ownership"]["prior_analyses"]
    }

    bundle = build_persistence_bundle(settings)
    with application(settings) as client:
        second = Restarted(client, bundle, case_id)
        assert_refused(second.declare(graph=graph))
        assert_refused(second.declare(graph=graph, rekey=True))
        selected = second.select_observations()
        assert selected.status_code == 200, selected.text
        assert second.ownership()["state"] == "ANALYZED"
        second.assert_unsent()
    stored = cases.find_one({"_id": case_id})
    assert stored is not None
    kept = raw["ownership"]["poc_interest_ledger"]
    assert stored["ownership"]["poc_interest_ledger"][: len(kept)] == kept


def test_a_stored_schema_18_case_fails_closed_and_is_not_rewritten_by_reads(physical: Any) -> None:
    settings, cases = physical
    bundle = build_persistence_bundle(settings)
    with application(settings) as client:
        first = Lane(client, bundle)
        case_id = first.case_id
        first.upload(first.observation_rows())
        graph = first.ownership()
        for step in range(1, 6):
            declared = first.declare(graph=graph, rekey=True, percents=corrected(step))
            assert declared.status_code == 200, declared.text
    raw = cases.find_one({"_id": case_id})
    assert raw is not None
    raw["schema_version"] = 18
    raw.pop("write_nonce", None)
    raw["ownership"].pop("poc_interest_ledger")
    assert cases.replace_one({"_id": case_id}, raw).matched_count == 1
    stored = deepcopy(cases.find_one({"_id": case_id}))

    bundle = build_persistence_bundle(settings)
    with application(settings) as client:
        restarted = Restarted(client, bundle, case_id)
        before = restarted.ownership()
        assert cases.find_one({"_id": case_id}) == stored
        # Its trimmed history cannot establish the interests, so no declaration passes.
        assert_refused(restarted.declare(graph=graph))
        assert_refused(restarted.declare(graph=graph, rekey=True, percents=CORRECTED))
        assert restarted.ownership() == before
        assert cases.find_one({"_id": case_id}) == stored
        # Selected current evidence stays available and writes the current schema.
        selected = restarted.select_observations()
        assert selected.status_code == 200, selected.text
        restarted.assert_unsent()
    written = cases.find_one({"_id": case_id})
    assert written is not None and written["schema_version"] == 21
    assert written["ownership"]["poc_interest_ledger"] is None
