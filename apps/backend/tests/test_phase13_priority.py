from __future__ import annotations

import copy
from datetime import UTC, datetime
from uuid import UUID

import pytest
from phase13_test_clients import RawTestClient
from phase13_test_credentials import TEST_PASSWORD
from phase13_test_settings import ordinary_test_settings
from test_phase12_persistence import MemoryEnvelopeStore

from app.composition import build_onboarding_service
from app.domain.access import (
    SYNTHETIC_PROFILE_BY_ID,
    AuthenticatedActor,
    TeamId,
)
from app.domain.models import OnboardingCase
from app.main import create_app
from app.persistence.errors import PersistenceDataInvalidError, PersistenceSchemaUnsupportedError
from app.persistence.models import (
    DurableCaseSnapshot,
    DurableCaseSnapshotV1,
    LegacyOnboardingCaseV1,
)
from app.persistence.mongo_case_store import MongoCaseStore
from app.persistence.repositories import MongoOnboardingCaseRepository
from app.services.authorization import CaseAccessPolicy
from app.services.repository import CaseTeamImmutableError, InMemoryOnboardingCaseRepository


def _legacy_case(case: OnboardingCase) -> LegacyOnboardingCaseV1:
    value = case.model_dump()
    value.pop("created_by_actor_id")
    value.pop("target_classification_selections")
    value.pop("team_id")
    value.pop("priority")
    value.pop("policy_snapshot")
    value.pop("registry_evidence_binding")
    value.pop("initial_identity")
    value.pop("initial_target_search")
    value.pop("existing_target_state")
    value.pop("identity_corrections")
    value.pop("initial_target_search_attempts")
    value.pop("target_dispatch_confirmation")
    value.pop("policy_snapshot_revision")
    value.pop("policy_rebind_history")
    return LegacyOnboardingCaseV1.model_validate(value)


def _login(client: RawTestClient, user_id: str) -> str:
    response = client.post("/api/auth/login", json={"user_id": user_id, "password": TEST_PASSWORD})
    assert response.status_code == 200
    return response.json()["csrf_token"]


def _create_case(
    client: RawTestClient,
    csrf: str,
    uen: str = "202400001A",
    *,
    priority: object = ...,
) -> str:
    body: dict[str, object] = {"uen": uen}
    if priority is not ...:
        body["priority"] = priority
    response = client.post(
        "/api/clm/zero-touch/cases",
        json=body,
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 201
    return response.json()["case"]["case_id"]


@pytest.mark.parametrize("priority", [..., None, 1, 5, 10])
def test_create_case_sets_strict_optional_priority_atomically(priority: object) -> None:
    client = RawTestClient(create_app(ordinary_test_settings(demo_controls_enabled=True)))
    csrf = _login(client, "maya-lim")

    case_id = _create_case(client, csrf, priority=priority)
    created = client.get(f"/api/clm/zero-touch/cases/{case_id}")

    assert created.status_code == 200
    assert created.json()["case"]["priority"] == (None if priority is ... else priority)
    assert not any(
        event.get("code") == "CASE_PRIORITY_UPDATED" for event in created.json()["case"]["events"]
    )


@pytest.mark.parametrize("priority", [0, 11, -1, 1.5, True, False, "10", "high"])
def test_create_case_rejects_invalid_priority_without_creating_case(priority: object) -> None:
    client = RawTestClient(create_app(ordinary_test_settings(demo_controls_enabled=True)))
    csrf = _login(client, "maya-lim")

    response = client.post(
        "/api/clm/zero-touch/cases",
        json={"uen": "202400001A", "priority": priority},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 422
    assert client.get("/api/clm/zero-touch/cases").json() == []


def test_schema_v1_reads_as_unassigned_null_priority_without_rewrite() -> None:
    onboarding = build_onboarding_service(settings=ordinary_test_settings())
    case = onboarding.create_staged_case("202400001A")
    now = datetime.now(UTC)
    legacy = DurableCaseSnapshotV1(
        case_id=case.case_id,
        revision=7,
        onboarding=_legacy_case(case),
        created_at=now,
        updated_at=now,
    )
    raw = legacy.model_dump(mode="json")
    raw["_id"] = str(case.case_id)
    before = copy.deepcopy(raw)
    store = object.__new__(MongoCaseStore)

    decoded = store._decode(raw)  # noqa: SLF001

    assert raw == before
    assert decoded.schema_version == 13
    assert decoded.revision == 7
    assert decoded.onboarding.team_id is None
    assert decoded.onboarding.priority is None
    assert decoded.onboarding.case_id == case.case_id


def test_schema_v7_is_written_and_invalid_metadata_fails_closed() -> None:
    onboarding = build_onboarding_service(settings=ordinary_test_settings())
    case = onboarding.create_staged_case("202400001A", team_id=TeamId.TEAM_A)
    case.priority = 10
    now = datetime.now(UTC)
    snapshot = DurableCaseSnapshot(
        case_id=case.case_id,
        revision=0,
        onboarding=case,
        created_at=now,
        updated_at=now,
    )
    store = object.__new__(MongoCaseStore)
    raw = store._encode(snapshot)  # noqa: SLF001

    assert raw["schema_version"] == 13
    assert store._decode(raw) == snapshot  # noqa: SLF001

    bad_team = copy.deepcopy(raw)
    bad_team["onboarding"]["team_id"] = "TEAM_C"
    with pytest.raises(PersistenceDataInvalidError):
        store._decode(bad_team)  # noqa: SLF001

    bad_priority = copy.deepcopy(raw)
    bad_priority["onboarding"]["priority"] = 0
    with pytest.raises(PersistenceDataInvalidError):
        store._decode(bad_priority)  # noqa: SLF001

    unknown = copy.deepcopy(raw)
    unknown["schema_version"] = 999
    with pytest.raises(PersistenceSchemaUnsupportedError):
        store._decode(unknown)  # noqa: SLF001


@pytest.mark.parametrize(
    "schema_version",
    [True, False, 1.0, 2.0, 1.5, "1", "2", None, [], {}, object()],
    ids=[
        "true",
        "false",
        "float-one",
        "float-two",
        "fractional-float",
        "string-one",
        "string-two",
        "null",
        "list",
        "object-map",
        "other-object",
    ],
)
def test_schema_discriminator_rejects_every_non_exact_integer(
    schema_version: object,
) -> None:
    onboarding = build_onboarding_service(settings=ordinary_test_settings())
    case = onboarding.create_staged_case("202400001A", team_id=TeamId.TEAM_A)
    now = datetime.now(UTC)
    snapshot = DurableCaseSnapshot(
        case_id=case.case_id,
        revision=0,
        onboarding=case,
        created_at=now,
        updated_at=now,
    )
    store = object.__new__(MongoCaseStore)
    raw = store._encode(snapshot)  # noqa: SLF001
    raw["schema_version"] = schema_version

    with pytest.raises(PersistenceDataInvalidError):
        store._decode(raw)  # noqa: SLF001


def test_schema_discriminator_accepts_only_supported_raw_integers() -> None:
    onboarding = build_onboarding_service(settings=ordinary_test_settings())
    case = onboarding.create_staged_case("202400001A", team_id=TeamId.TEAM_A)
    now = datetime.now(UTC)
    current = DurableCaseSnapshot(
        case_id=case.case_id,
        revision=0,
        onboarding=case,
        created_at=now,
        updated_at=now,
    )
    legacy = DurableCaseSnapshotV1(
        case_id=case.case_id,
        revision=0,
        onboarding=_legacy_case(case),
        created_at=now,
        updated_at=now,
    )
    store = object.__new__(MongoCaseStore)
    raw_current = store._encode(current)  # noqa: SLF001
    raw_legacy = legacy.model_dump(mode="json")
    raw_legacy["_id"] = str(case.case_id)

    assert type(raw_current["schema_version"]) is int
    assert type(raw_legacy["schema_version"]) is int
    assert store._decode(raw_current).schema_version == 13  # noqa: SLF001
    assert store._decode(raw_legacy).schema_version == 13  # noqa: SLF001


def test_team_id_is_immutable_in_memory_and_mongo_adapters() -> None:
    now = datetime.now(UTC)
    onboarding = build_onboarding_service(settings=ordinary_test_settings())
    team_case = onboarding.create_staged_case("202400001A", team_id=TeamId.TEAM_A)
    legacy_case = onboarding.create_staged_case("202400002B")

    memory = InMemoryOnboardingCaseRepository()
    memory.create(team_case)
    memory.create(legacy_case)
    with pytest.raises(CaseTeamImmutableError):
        memory.save(team_case.model_copy(update={"team_id": TeamId.TEAM_B}, deep=True))
    with pytest.raises(CaseTeamImmutableError):
        memory.save(legacy_case.model_copy(update={"team_id": TeamId.TEAM_A}, deep=True))

    store = MemoryEnvelopeStore()
    store.create(
        DurableCaseSnapshot(
            case_id=team_case.case_id,
            revision=0,
            onboarding=team_case,
            created_at=now,
            updated_at=now,
        )
    )
    store.create(
        DurableCaseSnapshot(
            case_id=legacy_case.case_id,
            revision=0,
            onboarding=legacy_case,
            created_at=now,
            updated_at=now,
        )
    )
    mongo = MongoOnboardingCaseRepository(store)  # type: ignore[arg-type]
    with pytest.raises(CaseTeamImmutableError):
        mongo.save(team_case.model_copy(update={"team_id": TeamId.TEAM_B}, deep=True))
    with pytest.raises(CaseTeamImmutableError):
        mongo.save(legacy_case.model_copy(update={"team_id": TeamId.TEAM_A}, deep=True))


def test_access_policy_hides_legacy_from_teams_and_allows_director() -> None:
    case = OnboardingCase(
        case_id=UUID("00000000-0000-4000-8000-000000000001"),
        source_case_id="CASE-LEGACY",
        correlation_id=UUID("00000000-0000-4000-8000-000000000002"),
        requested_uen="202400001A",
        state="REQUESTED",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    policy = CaseAccessPolicy()
    team = AuthenticatedActor(profile=SYNTHETIC_PROFILE_BY_ID["maya-lim"])
    director = AuthenticatedActor(profile=SYNTHETIC_PROFILE_BY_ID["olivia-koh"])

    assert not policy.can_access(team, case)
    assert policy.can_access(director, case)


@pytest.mark.parametrize("priority", [None, 1, 10])
def test_priority_endpoint_accepts_null_and_bounds(priority: int | None) -> None:
    client = RawTestClient(create_app(ordinary_test_settings(demo_controls_enabled=True)))
    csrf = _login(client, "maya-lim")
    case_id = _create_case(client, csrf)

    response = client.patch(
        f"/api/clm/zero-touch/cases/{case_id}/priority",
        json={"priority": priority},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 200
    assert response.json()["priority"] == priority
    assert response.json()["team_id"] == "TEAM_A"


@pytest.mark.parametrize("priority", [0, 11, -1, 1.0, True, "10", [], {}])
def test_priority_endpoint_rejects_invalid_types_and_values(priority: object) -> None:
    client = RawTestClient(create_app(ordinary_test_settings(demo_controls_enabled=True)))
    csrf = _login(client, "maya-lim")
    case_id = _create_case(client, csrf)

    response = client.patch(
        f"/api/clm/zero-touch/cases/{case_id}/priority",
        json={"priority": priority},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 422


def test_priority_clear_cross_team_non_mutation_and_automation_timestamp_stability() -> None:
    application = create_app(ordinary_test_settings(demo_controls_enabled=True))
    team_a = RawTestClient(application)
    team_b = RawTestClient(application)
    csrf_a = _login(team_a, "maya-lim")
    csrf_b = _login(team_b, "sophia-ng")
    case_id = _create_case(team_a, csrf_a)
    before = team_a.get("/api/clm/zero-touch/cases").json()[0]

    set_response = team_a.patch(
        f"/api/clm/zero-touch/cases/{case_id}/priority",
        json={"priority": 10},
        headers={"X-CSRF-Token": csrf_a},
    )
    denied = team_b.patch(
        f"/api/clm/zero-touch/cases/{case_id}/priority",
        json={"priority": 1},
        headers={"X-CSRF-Token": csrf_b},
    )
    after_denial = team_a.get("/api/clm/zero-touch/cases").json()[0]
    cleared = team_a.patch(
        f"/api/clm/zero-touch/cases/{case_id}/priority",
        json={"priority": None},
        headers={"X-CSRF-Token": csrf_a},
    )

    assert set_response.status_code == 200
    assert denied.status_code == 404
    assert after_denial["priority"] == 10
    assert before["updated_at"] == after_denial["updated_at"]
    assert cleared.status_code == 200
    assert cleared.json()["priority"] is None


def test_backend_priority_order_and_existing_tie_break_are_deterministic() -> None:
    application = create_app(ordinary_test_settings(demo_controls_enabled=True))
    client = RawTestClient(application)
    csrf = _login(client, "maya-lim")
    case_ids = [
        _create_case(client, csrf, uen)
        for uen in ("202400001A", "202400002B", "202400007G", "202400008H")
    ]
    priorities = (1, None, 10, 10)
    for case_id, priority in zip(case_ids, priorities, strict=True):
        response = client.patch(
            f"/api/clm/zero-touch/cases/{case_id}/priority",
            json={"priority": priority},
            headers={"X-CSRF-Token": csrf},
        )
        assert response.status_code == 200

    first = client.get("/api/clm/zero-touch/cases").json()
    second = client.get("/api/clm/zero-touch/cases").json()

    assert [item["priority"] for item in first] == [10, 10, 1, None]
    assert first == second
    tied = [item["case_id"] for item in first if item["priority"] == 10]
    tied_updates = [item["updated_at"] for item in first if item["priority"] == 10]
    if tied_updates[0] == tied_updates[1]:
        assert tied == sorted(tied, reverse=True)


def test_priority_filters_and_both_sort_directions_are_backend_authoritative() -> None:
    client = RawTestClient(create_app(ordinary_test_settings(demo_controls_enabled=True)))
    csrf = _login(client, "maya-lim")
    case_ids = [
        _create_case(client, csrf, uen, priority=priority)
        for uen, priority in zip(
            ("202400001A", "202400002B", "202400007G", "202400008H"),
            (1, 10, 5, None),
            strict=True,
        )
    ]

    highest = client.get("/api/clm/zero-touch/cases").json()
    lowest = client.get("/api/clm/zero-touch/cases?priority_sort=lowest_first").json()
    prioritised = client.get("/api/clm/zero-touch/cases?priority_filter=prioritised").json()
    exact = client.get("/api/clm/zero-touch/cases?priority_filter=5").json()
    unset = client.get("/api/clm/zero-touch/cases?priority_filter=unset").json()

    assert [item["priority"] for item in highest] == [10, 5, 1, None]
    assert [item["priority"] for item in lowest] == [1, 5, 10, None]
    assert [item["priority"] for item in prioritised] == [10, 5, 1]
    assert [item["case_id"] for item in exact] == [case_ids[2]]
    assert [item["case_id"] for item in unset] == [case_ids[3]]
    assert client.get("/api/clm/zero-touch/cases?priority_filter=0").status_code == 422
    assert client.get("/api/clm/zero-touch/cases?priority_sort=random").status_code == 422


def test_priority_filter_never_expands_team_authorization_scope() -> None:
    application = create_app(ordinary_test_settings(demo_controls_enabled=True))
    team_a = RawTestClient(application)
    team_b = RawTestClient(application)
    director = RawTestClient(application)
    csrf_a = _login(team_a, "maya-lim")
    csrf_b = _login(team_b, "sophia-ng")
    _login(director, "olivia-koh")
    case_a = _create_case(team_a, csrf_a, "202400001A", priority=1)
    case_b = _create_case(team_b, csrf_b, "202400002B", priority=10)

    team_result = team_a.get("/api/clm/zero-touch/cases?priority_filter=10").json()
    director_result = director.get("/api/clm/zero-touch/cases?priority_filter=10").json()

    assert team_result == []
    assert [item["case_id"] for item in director_result] == [case_b]
    assert case_a not in {item["case_id"] for item in director_result}


def test_team_lists_are_filtered_and_director_sees_both_teams() -> None:
    application = create_app(ordinary_test_settings(demo_controls_enabled=True))
    team_a = RawTestClient(application)
    team_b = RawTestClient(application)
    director = RawTestClient(application)
    csrf_a = _login(team_a, "maya-lim")
    csrf_b = _login(team_b, "sophia-ng")
    _login(director, "olivia-koh")
    case_a = _create_case(team_a, csrf_a, "202400001A")
    case_b = _create_case(team_b, csrf_b, "202400002B")

    list_a = team_a.get("/api/clm/zero-touch/cases").json()
    list_b = team_b.get("/api/clm/zero-touch/cases").json()
    list_director = director.get("/api/clm/zero-touch/cases").json()

    assert [item["case_id"] for item in list_a] == [case_a]
    assert [item["case_id"] for item in list_b] == [case_b]
    assert {item["case_id"] for item in list_director} == {case_a, case_b}
    assert list_a[0]["client_scope_label"] == "Alpha"
    assert list_b[0]["client_scope_label"] == "Beta"
