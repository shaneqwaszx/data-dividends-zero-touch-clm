"""D-114: a Government case reads its identity only from the government register, never ACRA.

The register is the approved local synthetic dataset (the D-101 Demo Parks seed). Every lane
here uses an ACRA connector that fails the test if it is called.
"""

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from scripts.seed_zero_touch_happy_path_companies import manage_fixtures
from scripts.zero_touch_happy_path_fixtures import COMPANIES, GOVERNMENT
from test_zero_touch_database_happy_path import NoAcra, RecordingTarget, sandbox_settings
from test_zero_touch_entity_types import (
    GAMMA,
    blockers,
    complete,
    government_at_status,
    upload,
)

from app.domain.jurisdiction import is_eligible_singapore_uen
from app.domain.models import (
    EntityCategory,
    InitialCustomerIdentity,
    RegistryFreshnessPolicy,
)
from app.domain.registry_dataset import local_synthetic_registry_identity
from app.main import create_app
from app.persistence.composition import build_persistence_bundle
from app.services.registry_acquisition import RegistryAcquisitionCoordinator
from app.services.registry_cache_repository import InMemoryRegistrySnapshotRepository

ALPHA = COMPANIES[0]
NOW = datetime(2026, 11, 2, 3, 0, tzinfo=UTC)
# Eligible fictional UENs with no seed in the register.
UNSEEDED_GOVERNMENT_UEN = "T99FY0199G"


@contextmanager
def lane(*, seed: bool = True, **settings_overrides):
    settings = sandbox_settings(**settings_overrides)
    bundle = build_persistence_bundle(settings)
    if seed:
        manage_fixtures(bundle.registry_snapshots, now=datetime.now(UTC), seed=True)
    acra = NoAcra()
    target = RecordingTarget(GOVERNMENT.name, GOVERNMENT.uen)
    with (
        patch("app.main.build_persistence_bundle", return_value=bundle),
        TestClient(create_app(settings, acra_connector=acra, goldtier_transport=target)) as client,
    ):
        yield client, acra


def start(client, uen, name, category=None, *, route="/api/clm/zero-touch/cases"):
    body = {"uen": uen, "legal_name": name, "country_of_incorporation": "SG"}
    if category is not None:
        body["entity_category"] = category
    response = client.post(route, json=body)
    assert response.status_code == 201, response.json()
    return response.json()


def error_code(current) -> str | None:
    error = current["case"].get("error")
    return error["code"] if error else None


# --- Government: register only ------------------------------------------------------------------


def test_government_with_the_register_record_never_calls_acra():
    with lane() as (client, acra):
        current = government_at_status(client)
        assert current["case"]["initial_identity"]["entity_category"] == "GOVERNMENT"
        assert current["case"]["registry_acquisition"]["status"] == "PARTIAL"
        assert current["case"]["entity"]["legal_name"] == GOVERNMENT.name
        assert current["current_stage"] == "OWNERSHIP"
        assert "GOVERNMENT_STATUS_REQUIRED" in current["clm"]["readiness"]["blockers"]
        assert acra.calls == []


@pytest.mark.parametrize(
    "uen", [UNSEEDED_GOVERNMENT_UEN, ALPHA.uen, GAMMA.uen],
    ids=["no-record", "company-record", "partnership-record"],
)
def test_government_without_a_government_register_record_stops_without_acra(uen):
    assert is_eligible_singapore_uen(uen)
    with lane() as (client, acra):
        current = start(client, uen, "DEMO UNKNOWN FYP TEST AUTHORITY", "GOVERNMENT")
        assert error_code(current) == "GOVERNMENT_IDENTITY_NOT_FOUND"
        assert "GOVERNMENT_IDENTITY_NOT_FOUND" in blockers(current)
        assert current["case"]["registry_acquisition"] is None
        card = next(item for item in current["interventions"]
                    if item.get("blocker_code") == "GOVERNMENT_IDENTITY_NOT_FOUND")
        assert card["title"] == "Government register record not found"
        assert card["identity_correction_action"] == "IDENTITY_SEARCH_RECHECK"
        assert acra.calls == []


def test_government_with_the_registry_cache_off_stops_without_acra():
    with lane(seed=False, registry_cache_mode="disabled") as (client, acra):
        current = start(client, GOVERNMENT.uen, GOVERNMENT.name, "GOVERNMENT")
        assert error_code(current) == "GOVERNMENT_IDENTITY_NOT_FOUND"
        assert acra.calls == []


def test_government_without_a_legal_name_is_incomplete_and_never_reaches_a_register():
    with lane() as (client, acra):
        response = client.post("/api/clm/zero-touch/cases",
                               json={"uen": GOVERNMENT.uen, "entity_category": "GOVERNMENT"})
        assert response.status_code == 201, response.json()
        assert error_code(response.json()) == "INITIAL_IDENTITY_INCOMPLETE"
        assert acra.calls == []


@pytest.mark.parametrize("route", ["/api/onboarding/cases", "/api/clm/cases"])
def test_every_create_route_takes_the_government_category(route):
    with lane() as (client, acra):
        response = client.post(route, json={"uen": GOVERNMENT.uen, "legal_name": GOVERNMENT.name,
                                            "country_of_incorporation": "SG",
                                            "entity_category": "GOVERNMENT"})
        assert response.status_code == 201, response.json()
        assert acra.calls == []


# --- Coordinator: no provider, so no ACRA ---------------------------------------------------------


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


# --- Company and Partnership: unchanged, except a government UEN stops ----------------------------


@pytest.mark.parametrize("category", [None, "COMPANY", "PARTNERSHIP"],
                         ids=["default", "company", "partnership"])
def test_a_government_uen_entered_as_another_category_stops_before_acra(category):
    with lane() as (client, acra):
        current = start(client, GOVERNMENT.uen, GOVERNMENT.name, category)
        assert error_code(current) == "ENTITY_CATEGORY_MISMATCH"
        assert "ENTITY_CATEGORY_MISMATCH" in blockers(current)
        assert current["case"]["registry_acquisition"] is None
        card = next(item for item in current["interventions"]
                    if item.get("blocker_code") == "ENTITY_CATEGORY_MISMATCH")
        assert card["title"] == "Entity type does not match the government register"
        assert acra.calls == []


@pytest.mark.parametrize("company,category", [(ALPHA, None), (ALPHA, "COMPANY"),
                                              (GAMMA, "PARTNERSHIP"),
                                              (GAMMA, "COMPANY")])
def test_company_and_partnership_lookups_are_unchanged(company, category):
    with lane() as (client, acra):
        current = start(client, company.uen, company.name, category)
        assert error_code(current) is None
        assert current["case"]["registry_acquisition"] is not None
        assert current["current_stage"] == "DOCUMENT"
        assert acra.calls == []


def test_old_callers_get_company_and_their_stored_identity_is_unchanged():
    with lane() as (client, _):
        current = start(client, ALPHA.uen, ALPHA.name)
        assert "entity_category" not in current["case"]["initial_identity"]
    identity = InitialCustomerIdentity(legal_name="X", registration_number=ALPHA.uen,
                                       country_of_incorporation="SG")
    assert identity.entity_category == EntityCategory.COMPANY
    assert "entity_category" not in identity.model_dump()
    government = identity.model_copy(update={"entity_category": EntityCategory.GOVERNMENT})
    assert government.model_dump()["entity_category"] == "GOVERNMENT"


# --- Correction: the RM changes the category on the same case -------------------------------------


@pytest.mark.parametrize("route", ["identity-search-recheck", "registry-identity"])
def test_rm_corrects_a_mismatch_to_government_visibly_and_without_acra(route):
    with lane() as (client, acra):
        current = start(client, GOVERNMENT.uen, GOVERNMENT.name, "COMPANY")
        assert error_code(current) == "ENTITY_CATEGORY_MISMATCH"
        response = client.post(
            f"/api/clm/zero-touch/cases/{current['case']['case_id']}/{route}",
            json={"legal_name": GOVERNMENT.name, "registration_number": GOVERNMENT.uen,
                  "country_of_incorporation": "SG", "entity_category": "GOVERNMENT",
                  "expected_automation_version": current["version"],
                  "expected_clm_version": current["clm"]["version"],
                  "expected_case_event_count": len(current["case"]["events"])},
        )
        assert response.status_code == 200, response.json()
        corrected = response.json()
        assert corrected["case"]["initial_identity"]["entity_category"] == "GOVERNMENT"
        assert corrected["case"]["entity"]["legal_name"] == GOVERNMENT.name
        events = [item["message"] for item in corrected["case"]["events"]
                  if item["code"] == "ENTITY_CATEGORY_CORRECTED"]
        assert events == ["Entity type changed from Company to Government."]
        assert "ENTITY_CATEGORY_MISMATCH" not in blockers(corrected)
        upload(client, corrected, GOVERNMENT.government_status_lines, "status.txt")
        after = complete(client, corrected, 1)
        assert "GOVERNMENT_STATUS_REQUIRED" in after["clm"]["readiness"]["blockers"]
        assert acra.calls == []


def test_correction_to_government_with_an_unknown_uen_is_refused_without_acra():
    with lane() as (client, acra):
        current = start(client, ALPHA.uen, ALPHA.name, "COMPANY")
        response = client.post(
            f"/api/clm/zero-touch/cases/{current['case']['case_id']}/registry-identity",
            json={"legal_name": ALPHA.name, "registration_number": UNSEEDED_GOVERNMENT_UEN,
                  "country_of_incorporation": "SG", "entity_category": "GOVERNMENT",
                  "expected_automation_version": current["version"],
                  "expected_clm_version": current["clm"]["version"],
                  "expected_case_event_count": len(current["case"]["events"])},
        )
        assert response.status_code in {409, 422}, response.json()
        after = client.get(f"/api/clm/zero-touch/cases/{current['case']['case_id']}").json()
        assert after["case"]["initial_identity"].get("entity_category") is None
        assert acra.calls == []

