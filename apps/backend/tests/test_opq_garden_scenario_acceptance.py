"""D-121 and D-124: on the Marketplace Mock lane a UBO review never blocks readiness.

It holds for any company, with GoldTier in Mock or Sandbox. Issues and classifications stay
visible, nothing becomes verified ownership, and only the explicit confirmation sends.
Synthetic and in memory, with recorded GoldTier transports.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest
import test_poc_ownership_acceptance as t
from scripts.five_layer_hybrid_fixture import FIVE_LAYER_FIELDS
from scripts.slice_b_registry_fixture import GARDEN_FIELDS
from test_opq_garden_abc_scenario import MULTI
from test_opq_garden_abc_scenario import transport as abc_transport
from test_opq_garden_sim_lim_scenario import CHAIN, OBSERVED_OPQ_POSITIONS, opq_transport
from test_slice_b_registry_demo import confirm, start
from test_zero_touch_database_happy_path import sandbox_settings
from test_zero_touch_entity_types import GAMMA, gamma_at_ownership
from test_zero_touch_entity_types import lane as sandbox_lane

from app.composition import build_ownership_analysis_service
from app.config import Settings
from app.domain.ownership import OwnershipAnalysisState
from app.persistence.composition import build_persistence_bundle
from app.services.ownership_analysis import OwnershipAnalysisService

OPQ_PDF = "five-layer-marketplace-hybrid-client.pdf"
GARDEN_PDF = "garden-partnership-reviewed-client.pdf"
ADVISORY = {"acra_marketplace_ubo_review_mode": "advisory"}


def observed_opq() -> Any:
    return opq_transport(OBSERVED_OPQ_POSITIONS)


LANES = {
    "opq-garden-abc": (MULTI, abc_transport, FIVE_LAYER_FIELDS, OPQ_PDF),
    "opq-garden-sim-lim": (CHAIN, observed_opq, FIVE_LAYER_FIELDS, OPQ_PDF),
    "opq-five-layer": ({}, observed_opq, FIVE_LAYER_FIELDS, OPQ_PDF),
    "garden-direct": ({}, t.garden_transport, GARDEN_FIELDS, GARDEN_PDF),
    "garden-no-overlay": (
        {"acra_marketplace_ownership_overlay": "garden_legacy_supplement"},
        t.garden_transport,
        GARDEN_FIELDS,
        GARDEN_PDF,
    ),
}


def onboarded(name: str, **update: Any) -> tuple[Any, Any, Any, str]:
    options, protocol, fields, pdf = LANES[name]
    settings = t.lane(**{**options, **update})
    bundle = build_persistence_bundle(settings)
    context = t.runtime(settings, bundle, protocol())
    client = context.__enter__()
    return context, client, bundle, start(client, fields, pdf)["case"]["case_id"]


@pytest.mark.parametrize("name", LANES)
def test_a_ubo_review_never_blocks_and_only_confirmation_sends(name: str) -> None:
    context, client, bundle, case_id = onboarded(name, **ADVISORY)
    try:
        ownership = t.ownership_of(client, case_id)
        summary = t.summary_of(client, case_id)
        assert ownership["state"] == "REVIEW_REQUIRED"
        assert ownership["issues"]
        assert ownership["poc_basis_accepted"] is False  # advisory, never shown as accepted
        assert summary["clm"]["readiness"]["blockers"] == []
        assert [item["exception_type"] for item in summary["active_exceptions"]] == [
            "TARGET_CONFIRMATION_REQUIRED"
        ]
        assert all(
            item["classification"] != "PROVISIONAL_UBO_CANDIDATE"
            for item in ownership["candidates"]
        )
        assert summary["case"].get("goldtier_result") is None
        assert bundle.target_executions.list_for_case(UUID(case_id)) == ()
        assert confirm(client, summary)["status"] == "COMPLETED"
    finally:
        context.__exit__(None, None, None)


@pytest.mark.parametrize("name", ["opq-garden-abc", "garden-direct"])
def test_the_blocking_mode_still_holds_the_case(name: str) -> None:
    context, client, _, case_id = onboarded(name)
    try:
        blockers = t.summary_of(client, case_id)["clm"]["readiness"]["blockers"]
        assert "OWNERSHIP_REVIEW_REQUIRED" in blockers
    finally:
        context.__exit__(None, None, None)


def test_advisory_is_the_default_on_the_marketplace_lane_with_either_goldtier_mode() -> None:
    assert Settings(_env_file=None).acra_marketplace_ubo_review_mode == "advisory"
    settings = Settings(_env_file=None, app_env="test", acra_connector_mode="mock")
    bundle = build_persistence_bundle(settings)
    service = build_ownership_analysis_service(None, settings, repository=bundle.ownership)
    assert service._ubo_review_advisory is False  # noqa: SLF001
    sandbox = sandbox_settings()
    assert sandbox.acra_marketplace_ubo_review_mode == "advisory"
    bundle = build_persistence_bundle(sandbox)
    service = build_ownership_analysis_service(None, sandbox, repository=bundle.ownership)
    assert service._ubo_review_advisory is True  # noqa: SLF001


def test_on_the_goldtier_sandbox_lane_a_review_waits_only_for_confirmation() -> None:
    with sandbox_lane(GAMMA) as (client, _, target, _):
        current = gamma_at_ownership(client)
        case_id = current["case"]["case_id"]
        assert t.ownership_of(client, case_id)["state"] == "REVIEW_REQUIRED"
        assert only_target_confirmation_is_open(client, case_id)
        assert current["clm"]["submission_plan"]["environment"] == "SANDBOX"
        assert [call[0] for call in target.calls] == ["GET"]  # nothing written yet
        assert confirm(client, t.summary_of(client, case_id))["status"] == "COMPLETED"
        assert "POST" in [call[0] for call in target.calls]


def incomplete_declaration(client: Any, case_id: str) -> Any:
    summary = t.summary_of(client, case_id)
    ownership = t.ownership_of(client, case_id)
    documents = client.get(f"/api/onboarding/cases/{case_id}/documents").json()
    document = [item for item in documents if not item["superseded_by_document_id"]][0]
    root_id = ownership["root_party_id"]
    root = next(item for item in ownership["parties"] if item["party_id"] == root_id)
    return client.post(
        f"/api/clm/zero-touch/cases/{case_id}/manual-ownership-evidence",
        json={
            "root_registration_number": summary["case"]["entity"]["registration_number"],
            "evidence_document_id": document["document_id"],
            "evidence_document_version": len(document["events"]),
            "as_of_date": "2026-10-20",
            "rationale": None,
            "root_party_id": root_id,
            "parties": [
                root,
                {
                    "party_id": "HOLDING_X",
                    "display_name": "HOLDING X PTE LTD",
                    "party_type": "LEGAL_ENTITY",
                    "country": "SG",
                },
                {
                    "party_id": "PERSON_B",
                    "display_name": "SYNTH OWNER B",
                    "party_type": "NATURAL_PERSON",
                    "country": "SG",
                },
            ],
            "relationships": [
                {
                    "relationship_id": "R1",
                    "parent_party_id": root_id,
                    "child_party_id": "HOLDING_X",
                    "ownership_percent": "60",
                },
                {
                    "relationship_id": "R2",
                    "parent_party_id": root_id,
                    "child_party_id": "PERSON_B",
                    "ownership_percent": "40",
                },
            ],
            "observed_document_versions": ownership["document_bindings"],
            "selected_observation_ids": [],
            "source_selection": "USER_SUPPLIED_DECLARATION",
            "expected_automation_version": summary["version"],
            "expected_ownership_version": ownership["version"],
            "expected_case_event_count": len(summary["case"]["events"]),
        },
    )


def only_target_confirmation_is_open(client: Any, case_id: str) -> bool:
    summary = t.summary_of(client, case_id)
    return summary["clm"]["readiness"]["blockers"] == [] and [
        item["exception_type"] for item in summary["active_exceptions"]
    ] == ["TARGET_CONFIRMATION_REQUIRED"]


@pytest.mark.parametrize("name", ["opq-five-layer", "opq-garden-sim-lim"])
def test_an_incomplete_declaration_does_not_hold_the_case(name: str) -> None:
    context, client, bundle, case_id = onboarded(name, **ADVISORY)
    try:
        response = incomplete_declaration(client, case_id)
        assert response.status_code == 200, response.text
        assert t.ownership_of(client, case_id)["state"] == "REVIEW_REQUIRED"
        assert only_target_confirmation_is_open(client, case_id)
        assert bundle.target_executions.list_for_case(UUID(case_id)) == ()
    finally:
        context.__exit__(None, None, None)


def test_a_case_held_before_the_review_became_advisory_needs_an_explicit_resume(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, client, bundle, case_id = onboarded("opq-five-layer")
    try:
        held = t.summary_of(client, case_id)
        assert "OWNERSHIP_REVIEW_REQUIRED" in held["clm"]["readiness"]["blockers"]
        monkeypatch.setattr(
            OwnershipAnalysisService,
            "review_is_advisory",
            lambda self, record: (
                record.state == OwnershipAnalysisState.REVIEW_REQUIRED
                and self._current_for_readiness(record)  # noqa: SLF001
            ),
        )
        opened = t.summary_of(client, case_id)
        assert opened["version"] == held["version"]  # D-124: a read changes nothing
        assert opened["current_stage"] == "OWNERSHIP"
        resumed = client.post(
            f"/api/clm/zero-touch/cases/{case_id}/resume",
            headers={
                "X-Automation-Id": opened["automation_id"],
                "X-Automation-Version": str(opened["version"]),
                "X-Clm-Version": str(opened["clm"]["version"]),
                "X-Case-Event-Count": str(len(opened["case"]["events"])),
            },
        )
        assert resumed.status_code == 200, resumed.text
        assert only_target_confirmation_is_open(client, case_id)
        assert bundle.target_executions.list_for_case(UUID(case_id)) == ()
    finally:
        context.__exit__(None, None, None)
