from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier, Event
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from phase13_test_clients import RawTestClient
from phase13_test_credentials import TEST_PASSWORD
from phase13_test_settings import ordinary_test_settings

from app.composition import (
    build_clm_orchestration_service,
    build_document_processing_service,
    build_onboarding_service,
    build_ownership_analysis_service,
    build_reconciliation_service,
    build_zero_touch_orchestrator,
)
from app.demo.zero_touch_control import ZeroTouchDemoControl, ZeroTouchDemoScenario
from app.domain.access import SYNTHETIC_PROFILE_BY_ID, AuthenticatedActor, TeamId
from app.domain.case_management import CasePortfolioScope, PortfolioScopeKind
from app.domain.models import OnboardingCase, WorkflowState
from app.main import create_app
from app.persistence.composition import build_persistence_bundle
from app.persistence.errors import (
    PersistenceConflictError,
    PersistenceDataInvalidError,
    PersistenceUnavailableError,
)
from app.persistence.mongo_case_store import MongoCaseStore
from app.services.authorization import CaseAccessPolicy, CaseNotAvailableError
from app.services.case_deletion import (
    CaseDeleteConflictError,
    CaseDeleteForbiddenError,
    CaseDeleteUnavailableError,
    CaseDeletionService,
)
from app.services.repository import (
    InMemoryOnboardingCaseRepository,
    OnboardingCaseRepositoryConflictError,
)
from app.services.zero_touch_errors import ZeroTouchRequestError
from app.services.zero_touch_repository import ZeroTouchAutomationRepository


def _login(client: RawTestClient, user_id: str) -> str:
    response = client.post(
        "/api/auth/login",
        json={"user_id": user_id, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    return response.json()["csrf_token"]


def _create_case(client: RawTestClient, csrf: str, *, team_id: str | None = None) -> str:
    body: dict[str, str] = {"uen": "202400001A"}
    if team_id is not None:
        body["team_id"] = team_id
    response = client.post(
        "/api/clm/zero-touch/cases",
        json=body,
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 201
    return response.json()["case"]["case_id"]


def _client_set():
    application = create_app(ordinary_test_settings(demo_controls_enabled=True))
    return application, {
        user: RawTestClient(application)
        for user in ("maya-lim", "ethan-tan", "sophia-ng", "olivia-koh")
    }


def test_delete_role_matrix_safe_not_found_and_repeat() -> None:
    _, clients = _client_set()
    csrf = {user: _login(client, user) for user, client in clients.items()}

    maya_case = _create_case(clients["maya-lim"], csrf["maya-lim"])
    own_forbidden = clients["maya-lim"].delete(
        f"/api/clm/zero-touch/cases/{maya_case}",
        headers={"X-CSRF-Token": csrf["maya-lim"]},
    )
    assert own_forbidden.status_code == 403
    assert own_forbidden.json()["detail"]["code"] == "CASE_DELETE_FORBIDDEN"

    foreign_hidden = clients["sophia-ng"].delete(
        f"/api/clm/zero-touch/cases/{maya_case}",
        headers={"X-CSRF-Token": csrf["sophia-ng"]},
    )
    assert foreign_hidden.status_code == 404

    deleted = clients["ethan-tan"].delete(
        f"/api/clm/zero-touch/cases/{maya_case}",
        headers={"X-CSRF-Token": csrf["ethan-tan"]},
    )
    assert deleted.status_code == 204
    assert deleted.content == b""
    repeated = clients["ethan-tan"].delete(
        f"/api/clm/zero-touch/cases/{maya_case}",
        headers={"X-CSRF-Token": csrf["ethan-tan"]},
    )
    assert repeated.status_code == 404

    director_case = _create_case(clients["olivia-koh"], csrf["olivia-koh"], team_id="TEAM_B")
    director_delete = clients["olivia-koh"].delete(
        f"/api/clm/zero-touch/cases/{director_case}",
        headers={"X-CSRF-Token": csrf["olivia-koh"]},
    )
    assert director_delete.status_code == 204


def test_delete_requires_authentication_csrf_and_trusted_browser_source() -> None:
    application, clients = _client_set()
    maya_csrf = _login(clients["maya-lim"], "maya-lim")
    case_id = _create_case(clients["maya-lim"], maya_csrf)
    rm = clients["ethan-tan"]
    rm_csrf = _login(rm, "ethan-tan")

    unauthenticated = RawTestClient(application).delete(f"/api/clm/zero-touch/cases/{case_id}")
    assert unauthenticated.status_code == 401
    assert rm.delete(f"/api/clm/zero-touch/cases/{case_id}").status_code == 403
    hostile_origin = rm.delete(
        f"/api/clm/zero-touch/cases/{case_id}",
        headers={"X-CSRF-Token": rm_csrf, "Origin": "https://foreign.invalid"},
    )
    assert hostile_origin.status_code == 403
    duplicate_origin = rm.delete(
        f"/api/clm/zero-touch/cases/{case_id}",
        headers=[
            ("X-CSRF-Token", rm_csrf),
            ("Origin", "http://testserver"),
            ("origin", "http://testserver"),
        ],
    )
    assert duplicate_origin.status_code == 403


def test_memory_repository_insert_update_delete_prevents_resurrection() -> None:
    repository = InMemoryOnboardingCaseRepository()
    cases = build_onboarding_service(settings=ordinary_test_settings(), repository=repository)
    case = cases.create_staged_case("202400001A", team_id=TeamId.TEAM_A)

    with pytest.raises(OnboardingCaseRepositoryConflictError):
        repository.create(case)
    repository.delete_for_case(case.case_id)
    with pytest.raises(OnboardingCaseRepositoryConflictError):
        repository.save(case)


class _DeletionProbe:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.deleted: list[UUID] = []

    def delete(self, case_id: UUID) -> str | None:
        if self.error is not None:
            raise self.error
        self.deleted.append(case_id)
        return "b" * 32


def _case_for_service(team_id: TeamId | None = TeamId.TEAM_A):
    repository = InMemoryOnboardingCaseRepository()
    now = datetime.now(UTC)
    case = OnboardingCase(
        case_id=uuid4(),
        source_case_id="CASE-P14",
        correlation_id=uuid4(),
        requested_uen="202400001A",
        team_id=team_id,
        state=WorkflowState.REQUESTED,
        created_at=now,
        updated_at=now,
    )
    repository.create(case)
    return case, build_onboarding_service(settings=ordinary_test_settings(), repository=repository)


def test_deletion_service_handles_null_team_and_releases_only_after_delete() -> None:
    case, cases = _case_for_service(None)
    probe = _DeletionProbe()
    released: list[object] = []
    service = CaseDeletionService(
        cases=cases,
        access_policy=CaseAccessPolicy(),
        repository=probe,
        release_provider_binding=lambda value: released.append(value),
        release_demo_transients=lambda value: released.append(value),
    )
    service.delete(
        AuthenticatedActor(profile=SYNTHETIC_PROFILE_BY_ID["olivia-koh"]),
        case.case_id,
    )
    assert probe.deleted == [case.case_id]
    assert released == ["b" * 32, case.case_id]


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (PersistenceConflictError(), CaseDeleteConflictError),
        (PersistenceUnavailableError(), CaseDeleteUnavailableError),
    ],
)
def test_deletion_service_sanitizes_persistence_failures(
    error: Exception, expected: type[Exception]
) -> None:
    case, cases = _case_for_service()
    service = CaseDeletionService(
        cases=cases,
        access_policy=CaseAccessPolicy(),
        repository=_DeletionProbe(error),
        release_provider_binding=lambda _: None,
        release_demo_transients=lambda _: None,
    )
    with pytest.raises(expected):
        service.delete(
            AuthenticatedActor(profile=SYNTHETIC_PROFILE_BY_ID["ethan-tan"]),
            case.case_id,
        )


def test_deletion_service_hides_inaccessible_and_forbids_accessible_onboarder() -> None:
    case, cases = _case_for_service()
    service = CaseDeletionService(
        cases=cases,
        access_policy=CaseAccessPolicy(),
        repository=_DeletionProbe(),
        release_provider_binding=lambda _: None,
        release_demo_transients=lambda _: None,
    )
    with pytest.raises(CaseNotAvailableError):
        service.delete(
            AuthenticatedActor(profile=SYNTHETIC_PROFILE_BY_ID["sophia-ng"]),
            case.case_id,
        )
    with pytest.raises(CaseDeleteForbiddenError):
        service.delete(
            AuthenticatedActor(profile=SYNTHETIC_PROFILE_BY_ID["maya-lim"]),
            case.case_id,
        )


def test_delete_waits_for_the_canonical_case_lock() -> None:
    case, cases = _case_for_service()
    entered = Event()
    service = CaseDeletionService(
        cases=cases,
        access_policy=CaseAccessPolicy(),
        repository=_DeletionProbe(),
        release_provider_binding=lambda _: None,
        release_demo_transients=lambda _: None,
    )

    def delete() -> None:
        entered.set()
        service.delete(
            AuthenticatedActor(profile=SYNTHETIC_PROFILE_BY_ID["ethan-tan"]),
            case.case_id,
        )

    with ThreadPoolExecutor(max_workers=1) as executor:
        with cases.case_lock(case.case_id):
            future = executor.submit(delete)
            assert entered.wait(timeout=1)
            assert not future.done()
        future.result(timeout=1)


class _LateAutomationRepository:
    def __init__(self, delegate: ZeroTouchAutomationRepository) -> None:
        self.delegate = delegate
        self.entered = Event()
        self.release = Event()
        self.case_id: UUID | None = None
        self.pause = False
        self.fail = False

    def save(self, record, *, expected_version):  # type: ignore[no-untyped-def]
        if expected_version is None and self.pause:
            self.case_id = record.case_id
            self.entered.set()
            assert self.release.wait(timeout=5)
            if self.fail:
                raise RuntimeError("synthetic late establishment failure")
        return self.delegate.save(record, expected_version=expected_version)

    def get_for_case(self, case_id: UUID):  # type: ignore[no-untyped-def]
        return self.delegate.get_for_case(case_id)

    def list_records(self):  # type: ignore[no-untyped-def]
        return self.delegate.list_records()

    def delete_for_case(self, case_id: UUID) -> None:
        self.delegate.delete_for_case(case_id)


def _establishment_system(*, automation_repository_factory=None, demo_factory=None):  # type: ignore[no-untyped-def]
    settings = ordinary_test_settings(demo_controls_enabled=True)
    persistence = build_persistence_bundle(settings)
    automation_repository = (
        automation_repository_factory(persistence.automation)
        if automation_repository_factory is not None
        else persistence.automation
    )
    cases = build_onboarding_service(
        settings=settings,
        repository=persistence.onboarding,
        target_execution_repository=persistence.target_executions,
    )
    documents = build_document_processing_service(cases, settings, repository=persistence.documents)
    ownership = build_ownership_analysis_service(cases, settings, repository=persistence.ownership)
    reconciliation = build_reconciliation_service(
        cases, documents, repository=persistence.reconciliation
    )
    clm = build_clm_orchestration_service(
        cases,
        documents,
        ownership,
        reconciliation,
        repository=persistence.clm,
    )
    zero_touch = build_zero_touch_orchestrator(
        cases,
        documents,
        ownership,
        clm,
        reconciliation,
        settings,
        repository=automation_repository,
        establishment_discard=persistence.deletion.discard,
    )
    demo_control = (
        demo_factory(persistence.demo_scenarios)
        if demo_factory is not None
        else ZeroTouchDemoControl(persistence.demo_scenarios)
    )
    deletion = CaseDeletionService(
        cases=cases,
        access_policy=CaseAccessPolicy(),
        repository=persistence.deletion,
        release_provider_binding=zero_touch.release_provider_binding,
        release_demo_transients=demo_control.release_case_transients,
    )
    return SimpleNamespace(
        settings=settings,
        persistence=persistence,
        cases=cases,
        documents=documents,
        ownership=ownership,
        reconciliation=reconciliation,
        clm=clm,
        zero_touch=zero_touch,
        automation_repository=automation_repository,
        demo=demo_control,
        deletion=deletion,
    )


def _assert_initial_aggregate_absent(system, case_id: UUID) -> None:  # type: ignore[no-untyped-def]
    assert system.cases.get_case(case_id) is None
    assert system.clm.get(case_id=case_id) is None
    assert system.zero_touch.get(case_id=case_id) is None
    assert system.persistence.documents.list_for_case(case_id) == []
    assert system.persistence.ownership.get_for_case(case_id) is None
    assert system.persistence.reconciliation.get_for_case(case_id) is None
    assert system.demo.registered_scenario_for(case_id) is None
    assert all(
        item.case_id != case_id
        for item in system.persistence.portfolio.list_authorized(
            CasePortfolioScope(kind=PortfolioScopeKind.GLOBAL)
        )
    )


def test_create_holds_lifecycle_lock_through_late_automation_write_and_delete() -> None:
    system = _establishment_system(automation_repository_factory=_LateAutomationRepository)
    delayed = system.automation_repository
    delayed.pause = True
    actor = AuthenticatedActor(profile=SYNTHETIC_PROFILE_BY_ID["ethan-tan"])
    delete_entered = Event()

    with ThreadPoolExecutor(max_workers=2) as executor:
        created = executor.submit(
            system.zero_touch.create_case, "202400001A", team_id=TeamId.TEAM_A
        )
        assert delayed.entered.wait(timeout=2)
        assert delayed.case_id is not None

        def delete() -> None:
            delete_entered.set()
            system.deletion.delete(actor, delayed.case_id)  # type: ignore[arg-type]

        deleted = executor.submit(delete)
        assert delete_entered.wait(timeout=2)
        assert not deleted.done()
        delayed.release.set()
        established = created.result(timeout=2)
        deleted.result(timeout=2)

    _assert_initial_aggregate_absent(system, established.case_id)


def test_failed_late_establishment_rolls_back_without_touching_unrelated_case() -> None:
    system = _establishment_system(automation_repository_factory=_LateAutomationRepository)
    delayed = system.automation_repository
    unrelated = system.zero_touch.create_case("202400002B", team_id=TeamId.TEAM_A)
    delayed.pause = True
    delayed.fail = True
    delayed.release.set()

    with pytest.raises(RuntimeError, match="synthetic late establishment failure"):
        system.zero_touch.create_case("202400001A", team_id=TeamId.TEAM_A)

    assert delayed.case_id is not None
    _assert_initial_aggregate_absent(system, delayed.case_id)
    assert system.cases.get_case(unrelated.case_id) is not None
    assert system.clm.get(case_id=unrelated.case_id) is not None
    assert system.zero_touch.get(case_id=unrelated.case_id) is not None


def test_primary_establishment_failure_survives_successful_rollback() -> None:
    system = _establishment_system()
    unrelated = system.zero_touch.create_case("202400002B", team_id=TeamId.TEAM_A)
    attempted_case_id: UUID | None = None

    def fail_after_demo_registration(case_id: UUID) -> None:
        nonlocal attempted_case_id
        attempted_case_id = case_id
        system.demo.register(case_id, ZeroTouchDemoScenario.RECOVERY)
        raise ZeroTouchRequestError(
            code="ZERO_TOUCH_CASE_CREATION_FAILED",
            message="Onboarding could not be started safely.",
        )

    with pytest.raises(ZeroTouchRequestError) as captured:
        system.zero_touch.create_case(
            "202400001A",
            team_id=TeamId.TEAM_A,
            establishment_action=fail_after_demo_registration,
            establishment_rollback=system.demo.discard_case,
        )

    assert captured.value.code == "ZERO_TOUCH_CASE_CREATION_FAILED"
    assert captured.value.public_message == "Onboarding could not be started safely."
    assert attempted_case_id is not None
    _assert_initial_aggregate_absent(system, attempted_case_id)
    assert system.cases.get_case(unrelated.case_id) is not None
    assert system.clm.get(case_id=unrelated.case_id) is not None
    assert system.zero_touch.get(case_id=unrelated.case_id) is not None


class _ExactRollbackFailure(RuntimeError):
    pass


def test_primary_establishment_failure_survives_rollback_failure() -> None:
    system = _establishment_system()
    unrelated = system.zero_touch.create_case("202400002B", team_id=TeamId.TEAM_A)
    attempted_case_id: UUID | None = None

    def fail_after_demo_registration(case_id: UUID) -> None:
        nonlocal attempted_case_id
        attempted_case_id = case_id
        system.demo.register(case_id, ZeroTouchDemoScenario.RECOVERY)
        raise ZeroTouchRequestError(
            code="ZERO_TOUCH_CASE_CREATION_FAILED",
            message="Onboarding could not be started safely.",
        )

    def fail_after_demo_rollback(case_id: UUID) -> None:
        system.demo.discard_case(case_id)
        raise _ExactRollbackFailure("raw rollback driver detail")

    with pytest.raises(ZeroTouchRequestError) as captured:
        system.zero_touch.create_case(
            "202400001A",
            team_id=TeamId.TEAM_A,
            establishment_action=fail_after_demo_registration,
            establishment_rollback=fail_after_demo_rollback,
        )

    assert captured.value.code == "ZERO_TOUCH_CASE_CREATION_FAILED"
    assert captured.value.public_message == "Onboarding could not be started safely."
    assert "raw rollback driver detail" not in str(captured.value)
    assert isinstance(captured.value.__cause__, _ExactRollbackFailure)
    assert attempted_case_id is not None
    _assert_initial_aggregate_absent(system, attempted_case_id)
    assert system.cases.get_case(unrelated.case_id) is not None
    assert system.clm.get(case_id=unrelated.case_id) is not None
    assert system.zero_touch.get(case_id=unrelated.case_id) is not None


class _RollbackFailingDemoControl(ZeroTouchDemoControl):
    def __init__(self, repository) -> None:  # type: ignore[no-untyped-def]
        super().__init__(repository)
        self.case_id: UUID | None = None

    def register(self, case_id: UUID, scenario: ZeroTouchDemoScenario) -> None:
        self.case_id = case_id
        super().register(case_id, scenario)
        raise ZeroTouchRequestError(
            code="ZERO_TOUCH_CASE_CREATION_FAILED",
            message="Onboarding could not be started safely.",
        )

    def discard_case(self, case_id: UUID) -> None:
        super().discard_case(case_id)
        raise _ExactRollbackFailure("raw rollback driver detail")


def test_demo_api_keeps_primary_mapping_when_rollback_fails() -> None:
    system = _establishment_system(demo_factory=_RollbackFailingDemoControl)
    application = create_app(
        system.settings,
        onboarding_service=system.cases,
        document_processing_service=system.documents,
        ownership_analysis_service=system.ownership,
        reconciliation_service=system.reconciliation,
        clm_orchestration_service=system.clm,
        zero_touch_orchestrator=system.zero_touch,
        zero_touch_demo_control=system.demo,
    )
    client = RawTestClient(application, raise_server_exceptions=False)
    csrf = _login(client, "ethan-tan")

    response = client.post(
        "/api/demo/clm/zero-touch/cases",
        json={"uen": "202400001A", "scenario": "RECOVERY"},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": {
            "code": "ZERO_TOUCH_CASE_CREATION_FAILED",
            "message": "Onboarding could not be started safely.",
        }
    }
    assert "raw rollback driver detail" not in response.text
    assert system.demo.case_id is not None
    _assert_initial_aggregate_absent(system, system.demo.case_id)


class _BlockingDemoControl(ZeroTouchDemoControl):
    def __init__(self, repository) -> None:  # type: ignore[no-untyped-def]
        super().__init__(repository)
        self.registered = Event()
        self.release = Event()

    def register(self, case_id: UUID, scenario: ZeroTouchDemoScenario) -> None:
        super().register(case_id, scenario)
        self.registered.set()
        assert self.release.wait(timeout=5)


@pytest.mark.parametrize("delay_response_until_deleted", [False, True])
def test_demo_route_registration_is_inside_establishment_delete_boundary(
    monkeypatch: pytest.MonkeyPatch, delay_response_until_deleted: bool
) -> None:
    system = _establishment_system(demo_factory=_BlockingDemoControl)
    demo = system.demo
    application = create_app(
        system.settings,
        onboarding_service=system.cases,
        document_processing_service=system.documents,
        ownership_analysis_service=system.ownership,
        reconciliation_service=system.reconciliation,
        clm_orchestration_service=system.clm,
        zero_touch_orchestrator=system.zero_touch,
        zero_touch_demo_control=system.demo,
    )
    client = RawTestClient(application)
    csrf = _login(client, "ethan-tan")
    actor = AuthenticatedActor(profile=SYNTHETIC_PROFILE_BY_ID["ethan-tan"])
    delete_started = Event()
    delete_completed = Event()
    chronology: list[str] = []
    original_create = system.zero_touch.create_case

    def create_then_delay_response(*args, **kwargs):  # type: ignore[no-untyped-def]
        record = original_create(*args, **kwargs)
        chronology.append("establishment_lock_released")
        if delay_response_until_deleted:
            assert delete_completed.wait(timeout=2), chronology
        return record

    monkeypatch.setattr(system.zero_touch, "create_case", create_then_delay_response)

    def create_demo():  # type: ignore[no-untyped-def]
        return client.post(
            "/api/demo/clm/zero-touch/cases",
            json={"uen": "202400001A", "scenario": "STRAIGHT_THROUGH"},
            headers={"X-CSRF-Token": csrf},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        created = executor.submit(create_demo)
        assert demo.registered.wait(timeout=2)
        records = system.zero_touch.automation_repository.list_records()
        assert len(records) == 1
        case_id = records[0].case_id

        def delete() -> None:
            chronology.append("deletion_requested")
            delete_started.set()
            system.deletion.delete(actor, case_id)
            chronology.append("deletion_completed")
            delete_completed.set()

        deleted = executor.submit(delete)
        assert delete_started.wait(timeout=2)
        assert not deleted.done()
        demo.release.set()
        response = created.result(timeout=2)
        chronology.append(f"response_{response.status_code}")
        assert response.status_code == 201, chronology
        deleted.result(timeout=2)

    _assert_initial_aggregate_absent(system, case_id)


def test_established_mutation_finishes_before_delete_removes_final_aggregate() -> None:
    system = _establishment_system()
    established = system.zero_touch.create_case("202400001A", team_id=TeamId.TEAM_A)
    actor = AuthenticatedActor(profile=SYNTHETIC_PROFILE_BY_ID["ethan-tan"])
    entered = Event()

    def delete() -> None:
        entered.set()
        system.deletion.delete(actor, established.case_id)

    with ThreadPoolExecutor(max_workers=1) as executor:
        with system.cases.case_lock(established.case_id):
            current = system.cases.get_case(established.case_id)
            assert current is not None
            current.updated_at = datetime.now(UTC)
            system.cases.case_repository.save(current)
            deleted = executor.submit(delete)
            assert entered.wait(timeout=2)
            assert not deleted.done()
        deleted.result(timeout=2)

    _assert_initial_aggregate_absent(system, established.case_id)


def test_concurrent_deletes_have_one_success_and_safe_follower() -> None:
    system = _establishment_system()
    established = system.zero_touch.create_case("202400001A", team_id=TeamId.TEAM_A)
    actor = AuthenticatedActor(profile=SYNTHETIC_PROFILE_BY_ID["ethan-tan"])
    barrier = Barrier(2)

    def delete() -> str:
        barrier.wait(timeout=2)
        try:
            system.deletion.delete(actor, established.case_id)
        except CaseNotAvailableError:
            return "not-found"
        return "deleted"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = [
            future.result(timeout=2)
            for future in (executor.submit(delete), executor.submit(delete))
        ]

    assert sorted(outcomes) == ["deleted", "not-found"]
    _assert_initial_aggregate_absent(system, established.case_id)


class _ProjectionCollection:
    def __init__(self, raw: dict[str, object]) -> None:
        self.raw = raw
        self.calls: list[tuple[dict[str, object], dict[str, object]]] = []

    def find(self, query: dict[str, object], projection: dict[str, object]):
        self.calls.append((query, projection))
        return [self.raw]


class _ScopeProjectionCollection:
    def __init__(self, raw_records: list[dict[str, object]]) -> None:
        self.raw_records = raw_records

    def find(self, query: dict[str, object], projection: dict[str, object]):
        del projection
        team_id = query.get("onboarding.team_id")
        return [
            item
            for item in self.raw_records
            if team_id is None
            or isinstance(item.get("onboarding"), dict)
            and item["onboarding"].get("team_id") == team_id  # type: ignore[union-attr]
        ]


def test_mongo_portfolio_is_one_projected_query_with_repository_team_scope() -> None:
    case_id = UUID("00000000-0000-4000-8000-000000000014")
    raw: dict[str, object] = {
        "_id": str(case_id),
        "schema_version": 2,
        "case_id": str(case_id),
        "revision": 7,
        "onboarding": {
            "case_id": str(case_id),
            "team_id": "TEAM_A",
            "priority": 9,
            "requested_uen": "202400001A",
            "entity": {"legal_name": "MERLION PTE. LTD."},
            "jurisdiction_resolution": {"resolved_jurisdiction": "SG"},
            "goldtier_result": {"party_id": "GT-MOCK-14"},
        },
        "automation": {
            "case_id": str(case_id),
            "status": "WAITING_FOR_REVIEW",
            "current_stage": "DOCUMENT",
            "created_at": datetime(2026, 9, 8, tzinfo=UTC),
            "updated_at": datetime(2026, 9, 8, 1, tzinfo=UTC),
            "completed_at": None,
            "exceptions": [
                {"status": "OPEN", "exception_type": "DOCUMENT_LOW_CONFIDENCE"},
                {"status": "OPEN", "exception_type": "DOCUMENT_LOW_CONFIDENCE"},
                {"status": "RESOLVED", "exception_type": "OWNERSHIP_CYCLE"},
            ],
            "metrics": {"human_interventions": 1, "final_outcome": None},
        },
    }
    collection = _ProjectionCollection(raw)
    store = object.__new__(MongoCaseStore)
    store._collection = collection  # type: ignore[attr-defined]  # noqa: SLF001

    records = store.list_portfolio(
        CasePortfolioScope(kind=PortfolioScopeKind.TEAM, team_id=TeamId.TEAM_A)
    )

    assert len(collection.calls) == 1
    assert collection.calls[0][0]["onboarding.team_id"] == "TEAM_A"
    assert "documents" not in collection.calls[0][1]
    assert collection.calls[0][1]["automation.exceptions.status"] == 1
    assert collection.calls[0][1]["automation.exceptions.exception_type"] == 1
    assert "automation.exceptions.explanation" not in collection.calls[0][1]
    assert records[0].active_exception_count == 2
    assert records[0].active_exception_types == ("DOCUMENT_LOW_CONFIDENCE",)
    assert records[0].mock_goldtier_party_id == "GT-MOCK-14"


@pytest.mark.parametrize(
    "exceptions",
    [
        [{"status": "OPEN"}],
        [{"exception_type": "DOCUMENT_LOW_CONFIDENCE"}],
        [{"status": "UNKNOWN", "exception_type": "DOCUMENT_LOW_CONFIDENCE"}],
        [{"status": "OPEN", "exception_type": "UNKNOWN"}],
        [{"status": "RESOLVED", "exception_type": "UNKNOWN"}],
        [
            {
                "status": "OPEN",
                "exception_type": "DOCUMENT_LOW_CONFIDENCE",
                "explanation": "must not be projected",
            }
        ],
    ],
)
def test_mongo_portfolio_rejects_malformed_projected_exception_pairs(
    exceptions: list[dict[str, str]],
) -> None:
    case_id = UUID("00000000-0000-4000-8000-000000000014")
    raw: dict[str, object] = {
        "_id": str(case_id),
        "schema_version": 1,
        "case_id": str(case_id),
        "revision": 0,
        "onboarding": {"case_id": str(case_id), "requested_uen": "202400001A"},
        "automation": {
            "case_id": str(case_id),
            "status": "WAITING_FOR_REVIEW",
            "current_stage": "DOCUMENT",
            "created_at": datetime(2026, 9, 8, tzinfo=UTC),
            "updated_at": datetime(2026, 9, 8, 1, tzinfo=UTC),
            "completed_at": None,
            "exceptions": exceptions,
            "metrics": {"human_interventions": 0, "final_outcome": None},
        },
    }
    collection = _ProjectionCollection(raw)
    store = object.__new__(MongoCaseStore)
    store._collection = collection  # type: ignore[attr-defined]  # noqa: SLF001

    with pytest.raises(PersistenceDataInvalidError):
        store.list_portfolio(CasePortfolioScope(kind=PortfolioScopeKind.GLOBAL))


@pytest.mark.parametrize("schema_version", [1, 2, 3, 4, 5])
def test_mongo_portfolio_attention_projection_supports_every_readable_schema(
    schema_version: int,
) -> None:
    case_id = UUID("00000000-0000-4000-8000-000000000014")
    onboarding: dict[str, object] = {
        "case_id": str(case_id),
        "requested_uen": "202400001A",
    }
    if schema_version >= 2:
        onboarding.update({"team_id": "TEAM_A", "priority": 7})
    raw: dict[str, object] = {
        "_id": str(case_id),
        "schema_version": schema_version,
        "case_id": str(case_id),
        "revision": 1,
        "onboarding": onboarding,
        "automation": {
            "case_id": str(case_id),
            "status": "WAITING_FOR_REVIEW",
            "current_stage": "OWNERSHIP",
            "created_at": datetime(2026, 9, 8, tzinfo=UTC),
            "updated_at": datetime(2026, 9, 8, 1, tzinfo=UTC),
            "completed_at": None,
            "exceptions": [
                {"status": "CANCELLED", "exception_type": "JURISDICTION_CONFLICT"},
                {"status": "OPEN", "exception_type": "OWNERSHIP_CYCLE"},
            ],
            "metrics": {"human_interventions": 1, "final_outcome": None},
        },
    }
    store = object.__new__(MongoCaseStore)
    store._collection = _ProjectionCollection(raw)  # type: ignore[attr-defined]  # noqa: SLF001

    record = store.list_portfolio(
        CasePortfolioScope(kind=PortfolioScopeKind.GLOBAL)
    )[0]

    assert record.active_exception_count == 1
    assert record.active_exception_types == ("OWNERSHIP_CYCLE",)


def test_mongo_team_scope_excludes_inaccessible_malformed_attention_data_before_decode() -> None:
    valid_id = UUID("00000000-0000-4000-8000-000000000014")
    invalid_id = UUID("00000000-0000-4000-8000-000000000015")

    def raw(case_id: UUID, team_id: str, exception_type: str) -> dict[str, object]:
        return {
            "_id": str(case_id),
            "schema_version": 4,
            "case_id": str(case_id),
            "revision": 1,
            "onboarding": {
                "case_id": str(case_id),
                "team_id": team_id,
                "priority": None,
                "requested_uen": "202400001A",
            },
            "automation": {
                "case_id": str(case_id),
                "status": "WAITING_FOR_REVIEW",
                "current_stage": "DOCUMENT",
                "created_at": datetime(2026, 9, 8, tzinfo=UTC),
                "updated_at": datetime(2026, 9, 8, 1, tzinfo=UTC),
                "completed_at": None,
                "exceptions": [{"status": "OPEN", "exception_type": exception_type}],
                "metrics": {"human_interventions": 0, "final_outcome": None},
            },
        }

    store = object.__new__(MongoCaseStore)
    store._collection = _ScopeProjectionCollection(  # type: ignore[attr-defined]  # noqa: SLF001
        [
            raw(valid_id, "TEAM_A", "DOCUMENT_LOW_CONFIDENCE"),
            raw(invalid_id, "TEAM_B", "UNKNOWN"),
        ]
    )

    records = store.list_portfolio(
        CasePortfolioScope(kind=PortfolioScopeKind.TEAM, team_id=TeamId.TEAM_A)
    )

    assert [record.case_id for record in records] == [valid_id]
