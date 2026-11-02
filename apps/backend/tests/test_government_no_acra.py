"""D-114: the UEN's entity type picks the register; a government body never calls ACRA.

The government register is the approved local synthetic dataset (the D-101 Demo Parks seed,
UEN T99GB0105G, code GB). Every lane uses an ACRA connector that fails the test if called.
"""

from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from scripts.seed_zero_touch_happy_path_companies import manage_fixtures
from scripts.zero_touch_happy_path_fixtures import COMPANIES, GOVERNMENT
from test_slice_b_registry_demo import confirm
from test_zero_touch_database_happy_path import NoAcra, RecordingTarget, sandbox_settings
from test_zero_touch_entity_types import GAMMA, blockers, confirm_government, government_at_status

from app.domain.jurisdiction import is_eligible_singapore_uen
from app.domain.models import RegistryFreshnessPolicy
from app.domain.registry_dataset import local_synthetic_registry_identity
from app.main import create_app
from app.persistence.composition import build_persistence_bundle
from app.services.registry_acquisition import RegistryAcquisitionCoordinator
from app.services.registry_cache_repository import InMemoryRegistrySnapshotRepository

ALPHA = COMPANIES[0]
NOW = datetime(2026, 11, 2, 3, 0, tzinfo=UTC)
UNSEEDED_GB_UEN = "T99GB0199G"
SOCIETY_UEN = "T09SS0001B"
# A government body filed under an ACRA-format UEN: bad register data the guard must catch.
MISFILED = replace(GOVERNMENT, uen="209990199A")


@contextmanager
def lane(*, seed: bool = True, extra=(), **settings_overrides):
    settings = sandbox_settings(**settings_overrides)
    bundle = build_persistence_bundle(settings)
    if seed:
        now = datetime.now(UTC)
        manage_fixtures(bundle.registry_snapshots, now=now, seed=True)
        for company in extra:
            bundle.registry_snapshots.create(company.snapshot(now))
    acra = NoAcra()
    target = RecordingTarget(GOVERNMENT.name, GOVERNMENT.uen)
    with (
        patch("app.main.build_persistence_bundle", return_value=bundle),
        TestClient(create_app(settings, acra_connector=acra, goldtier_transport=target)) as client,
    ):
        yield client, acra


def start(client, uen, name, **extra):
    response = client.post("/api/clm/zero-touch/cases", json={
        "uen": uen, "legal_name": name, "country_of_incorporation": "SG", **extra,
    })
    assert response.status_code == 201, response.json()
    return response.json()


def error_code(current) -> str | None:
    error = current["case"].get("error")
    return error["code"] if error else None


def card(current, code):
    return next(item for item in current["interventions"] if item.get("blocker_code") == code)


def correct(client, current, uen, name, **extra):
    return client.post(
        f"/api/clm/zero-touch/cases/{current['case']['case_id']}/registry-identity",
        json={"legal_name": name, "registration_number": uen, "country_of_incorporation": "SG",
              "expected_automation_version": current["version"],
              "expected_clm_version": current["clm"]["version"],
              "expected_case_event_count": len(current["case"]["events"]), **extra},
    )


# --- Government body (GB): register only -------------------------------------------------------


def test_gb_with_a_register_record_completes_the_government_path_without_acra():
    with lane() as (client, acra):
        waiting = government_at_status(client)
        route = waiting["case"]["uen_route"]
        assert (route["route"], route["pq_code"], route["uen_format"]) == (
            "GOVERNMENT_REGISTER", "GB", "C"
        )
        assert route["description"] == (
            "Government body (statutory board, code GB) · checked against the government "
            "register, not ACRA"
        )
        assert waiting["case"]["registry_acquisition"]["status"] == "PARTIAL"
        assert blockers(waiting) == ["GOVERNMENT_STATUS_REQUIRED"]
        confirmed = confirm_government(client, waiting)
        assert confirmed.status_code == 200, confirmed.json()
        assert confirm(client, confirmed.json())["status"] == "COMPLETED"
        assert acra.calls == []


@pytest.mark.parametrize("cache_off", [False, True], ids=["no-record", "cache-off"])
def test_gb_without_a_register_record_stops_without_acra(cache_off):
    overrides = {"seed": False, "registry_cache_mode": "disabled"} if cache_off else {}
    uen = GOVERNMENT.uen if cache_off else UNSEEDED_GB_UEN
    assert is_eligible_singapore_uen(uen)
    with lane(**overrides) as (client, acra):
        current = start(client, uen, "DEMO UNKNOWN FYP TEST AUTHORITY")
        assert error_code(current) == "GOVERNMENT_IDENTITY_NOT_FOUND"
        assert current["case"]["registry_acquisition"] is None
        assert current["case"]["uen_route"]["route"] == "GOVERNMENT_REGISTER"
        item = card(current, "GOVERNMENT_IDENTITY_NOT_FOUND")
        assert item["title"] == "Government register record not found"
        assert item["identity_correction_action"] == "IDENTITY_SEARCH_RECHECK"
        assert acra.calls == []


def test_an_unsupported_uen_entity_type_stops_without_any_registry_call():
    with lane() as (client, acra):
        current = start(client, SOCIETY_UEN, "DEMO SOCIETY FYP TEST")
        assert error_code(current) == "UEN_ENTITY_TYPE_UNSUPPORTED"
        assert current["case"]["error"]["message"] == (
            "This UEN belongs to an entity type this POC doesn't onboard (society). "
            "Check the UEN."
        )
        assert current["case"]["uen_route"]["route"] == "UNSUPPORTED"
        assert card(current, "UEN_ENTITY_TYPE_UNSUPPORTED")["title"] == (
            "UEN entity type not onboarded in this POC"
        )
        assert acra.calls == []


def test_an_acra_format_uen_with_a_government_record_stops_before_acra():
    with lane(extra=[MISFILED]) as (client, acra):
        current = start(client, MISFILED.uen, MISFILED.name)
        assert error_code(current) == "ENTITY_CATEGORY_MISMATCH"
        assert current["case"]["uen_route"]["route"] == "ACRA"
        assert card(current, "ENTITY_CATEGORY_MISMATCH")["title"] == (
            "UEN does not match the government register"
        )
        assert acra.calls == []


# --- Unchanged ACRA routes ----------------------------------------------------------------------


@pytest.mark.parametrize("company", [ALPHA, GAMMA], ids=["alpha", "gamma"])
def test_acra_route_cases_are_unchanged(company):
    with lane() as (client, acra):
        current = start(client, company.uen, company.name)
        assert error_code(current) is None
        assert current["case"]["uen_route"]["route"] == "ACRA"
        assert current["current_stage"] == "DOCUMENT"
        assert acra.calls == []


# --- The RM corrects the UEN; the route follows the UEN -----------------------------------------


def route_messages(current) -> list[str]:
    return [item["message"] for item in current["case"]["events"]
            if item["code"] == "UEN_ROUTE_CHANGED"]


def test_correcting_an_acra_uen_to_a_gb_uen_reroutes_visibly_without_acra():
    with lane(extra=[MISFILED]) as (client, acra):
        current = start(client, MISFILED.uen, MISFILED.name)
        assert error_code(current) == "ENTITY_CATEGORY_MISMATCH"
        response = correct(client, current, GOVERNMENT.uen, GOVERNMENT.name)
        assert response.status_code == 200, response.json()
        corrected = response.json()
        assert corrected["case"]["uen_route"]["route"] == "GOVERNMENT_REGISTER"
        assert corrected["case"]["entity"]["legal_name"] == GOVERNMENT.name
        assert route_messages(corrected) == [
            "Route changed from ACRA to government register (UEN type GB)."
        ]
        assert "ENTITY_CATEGORY_MISMATCH" not in blockers(corrected)
        assert acra.calls == []


def test_correcting_a_gb_uen_back_to_an_acra_uen_reroutes_visibly():
    with lane() as (client, acra):
        current = start(client, UNSEEDED_GB_UEN, ALPHA.name)
        assert error_code(current) == "GOVERNMENT_IDENTITY_NOT_FOUND"
        response = correct(client, current, ALPHA.uen, ALPHA.name)
        assert response.status_code == 200, response.json()
        corrected = response.json()
        assert corrected["case"]["uen_route"]["route"] == "ACRA"
        assert route_messages(corrected) == [
            "Route changed from government register to ACRA (UEN format B)."
        ]
        assert acra.calls == []  # Alpha is served from its fresh seed, as before D-114


@pytest.mark.parametrize("uen", [UNSEEDED_GB_UEN, SOCIETY_UEN], ids=["gb-no-record", "society"])
def test_a_correction_to_a_gb_or_unsupported_uen_is_refused_without_acra(uen):
    with lane() as (client, acra):
        current = start(client, UNSEEDED_GB_UEN, ALPHA.name)
        response = correct(client, current, uen, ALPHA.name)
        assert response.status_code in {409, 422}, response.json()
        assert acra.calls == []


# --- The RM no longer chooses an entity type ----------------------------------------------------


def test_requests_carrying_entity_category_are_rejected():
    with lane() as (client, acra):
        response = client.post("/api/clm/zero-touch/cases", json={
            "uen": GOVERNMENT.uen, "legal_name": GOVERNMENT.name,
            "country_of_incorporation": "SG", "entity_category": "GOVERNMENT",
        })
        assert response.status_code == 422
        current = start(client, UNSEEDED_GB_UEN, ALPHA.name)
        assert correct(client, current, ALPHA.uen, ALPHA.name,
                       entity_category="COMPANY").status_code == 422
        assert acra.calls == []


# --- Coordinator: no provider, so no ACRA -------------------------------------------------------


def coordinator(entry, *, now=NOW):
    repository = InMemoryRegistrySnapshotRepository()
    if entry is not None:
        repository.create(entry)
    return RegistryAcquisitionCoordinator(
        repository, RegistryFreshnessPolicy(), clock=lambda: now,
        local_seed_identity=local_synthetic_registry_identity(),
    )


def test_register_read_returns_only_a_fresh_government_record():
    fresh = coordinator(GOVERNMENT.snapshot(NOW))
    assert fresh.read_government_register(GOVERNMENT.uen) is not None
    stale = coordinator(GOVERNMENT.snapshot(NOW), now=NOW + timedelta(days=90))
    assert stale.read_government_register(GOVERNMENT.uen) is None
    assert coordinator(GAMMA.snapshot(NOW)).read_government_register(GAMMA.uen) is None
    assert coordinator(ALPHA.snapshot(NOW)).read_government_register(ALPHA.uen) is None
    assert coordinator(None).read_government_register(GOVERNMENT.uen) is None
    without_seed = RegistryAcquisitionCoordinator(
        InMemoryRegistrySnapshotRepository(), RegistryFreshnessPolicy()
    )
    assert without_seed.read_government_register(GOVERNMENT.uen) is None
