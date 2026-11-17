"""C1/C2 and ADR-017 P2-0: the legacy CLM routes and a switched-off manager.

P2-0 retires the legacy target confirmation (it no longer exists: 404) and makes legacy
Submit recovery-only: it continues only a send the full D-136 E3 predicate covers, after
every existing check in its order (otherwise 409 CLM_SUBMIT_RECOVERY_ONLY). A required
added stage, or an unreadable check, still holds it first. Recovery never replays.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient
from scripts.seed_zero_touch_happy_path_companies import manage_fixtures
from scripts.zero_touch_happy_path_fixtures import SHARE_COMPANIES
from test_clm_orchestration import make_ready_case
from test_slice_b_registry_demo import confirm
from test_workflow_manager import STAGE, case_url, director_actor, login, onboarding_run
from test_zero_touch_database_happy_path import NoAcra, RecordingTarget, prepare, sandbox_settings
from workflow_publication_seed import publish_draft

from app.config import Settings
from app.domain.workflows import ONBOARDING_WORKFLOW_ID, WorkflowStage
from app.main import _refusing_unsendable_case, create_app
from app.persistence.composition import WorkflowPersistence, build_persistence_bundle
from app.persistence.errors import PersistenceDataInvalidError, PersistenceUnavailableError
from app.services.clm_errors import ClmInfrastructureError, ClmRequestError
from app.services.workflow_management import (
    HOLD_INCOMPLETE,
    HOLD_UNAVAILABLE,
    WorkflowManagementService,
)
from app.services.workflow_repository import (
    InMemoryWorkflowDefinitionRepository,
    InMemoryWorkflowRunRepository,
)

OPTIONAL_STAGE = {
    **STAGE,
    "stage_id": "optional-notes",
    "fields": [{"field_id": "notes", "label": "Notes", "kind": "TEXT", "required": False}],
}
HOLD_CODES = {HOLD_INCOMPLETE, HOLD_UNAVAILABLE}


class FailingRuns(InMemoryWorkflowRunRepository):
    def list_for_case(self, case_id: UUID) -> Any:
        raise PersistenceUnavailableError


class CorruptDefinitions(InMemoryWorkflowDefinitionRepository):
    def get(self, workflow_id: str) -> Any:
        raise PersistenceDataInvalidError


def activate(store: WorkflowPersistence, stage: dict[str, Any]) -> None:
    """Activate one onboarding stage in the given store, as a Director would."""

    actor = director_actor()
    service = WorkflowManagementService(
        definitions=store.definitions,
        runs=store.runs,
        cases=SimpleNamespace(),  # type: ignore[arg-type]
        clock=lambda: datetime(2020, 1, 1, tzinfo=UTC),
    )
    service.provision_onboarding()
    baseline = service.get_workflow(actor, ONBOARDING_WORKFLOW_ID)
    saved = service.save_draft(
        lambda: actor,
        ONBOARDING_WORKFLOW_ID,
        expected_revision=baseline.revision,
        stages=(WorkflowStage.model_validate(stage),),
    )
    del saved
    # Activation is frozen (ADR-017); publish as governed publication will.
    publish_draft(store.definitions, ONBOARDING_WORKFLOW_ID)


def storage(
    *,
    stage: dict[str, Any] | None = STAGE,
    definitions: InMemoryWorkflowDefinitionRepository | None = None,
    runs: InMemoryWorkflowRunRepository | None = None,
) -> WorkflowPersistence:
    store = WorkflowPersistence(
        definitions=(
            definitions if definitions is not None else InMemoryWorkflowDefinitionRepository()
        ),
        runs=runs if runs is not None else InMemoryWorkflowRunRepository(),
        close=lambda: None,
    )
    if stage is not None:
        activate(store, stage)
    return store


def unavailable_store() -> WorkflowPersistence:
    return storage(runs=FailingRuns())


def corrupt_store() -> WorkflowPersistence:
    return storage(stage=None, definitions=CorruptDefinitions())


def legacy_app(services: tuple[Any, ...], store: WorkflowPersistence, **overrides: Any) -> Any:
    cases, documents, ownership, clm = services
    with patch("app.main.build_workflow_persistence", return_value=store):
        return create_app(
            Settings(app_env="test", demo_controls_enabled=True, **overrides),
            onboarding_service=cases,
            document_processing_service=documents,
            ownership_analysis_service=ownership,
            clm_orchestration_service=clm,
        )


def http(app: Any) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def legacy_confirmation(
    case_id: UUID, version: int, event_count: int
) -> tuple[str, dict[str, int]]:
    return (
        f"/api/clm/cases/{case_id}/target-confirmation",
        {"expected_clm_version": version, "expected_case_event_count": event_count},
    )


def held(response: httpx.Response, code: str = HOLD_INCOMPLETE) -> bool:
    return response.status_code == 409 and response.json()["detail"]["code"] == code


def retired(response: Any) -> bool:
    """ADR-017 3.7: the legacy target confirmation route is retired."""

    return response.status_code == 404


RECOVERY_ONLY = "CLM_SUBMIT_RECOVERY_ONLY"


# T1 - legacy confirmation, required stage open: refused before any target step.
@pytest.mark.anyio
@pytest.mark.parametrize(
    ("store", "code"),
    [
        (storage, HOLD_INCOMPLETE),
        (unavailable_store, HOLD_UNAVAILABLE),  # T4
        (corrupt_store, HOLD_UNAVAILABLE),  # T4
    ],
)
async def test_legacy_confirmation_is_refused_before_any_target_step(store, code) -> None:
    """Retired in P2-0: the route is gone whatever the workflow store holds."""

    del code
    cases, documents, ownership, clm, target, case_id = make_ready_case(confirm=False)
    evaluated = clm.evaluate(case_id=case_id)
    events = len(cases.get_case(case_id).events)
    calls = list(target.calls)
    app = legacy_app((cases, documents, ownership, clm), store())
    async with http(app) as client:
        path, body = legacy_confirmation(case_id, evaluated.version, events)
        refused = await client.post(path, json=body)

    assert retired(refused), refused.text
    after = clm.get(case_id=case_id)
    assert after.version == evaluated.version
    assert after.submission_snapshot is None
    case = cases.get_case(case_id)
    assert case.target_dispatch_confirmation is None and len(case.events) == events
    assert target.calls == calls  # not even the confirmation-time Search ran


# T2 - legacy submit with a frozen snapshot but no write: not an in-flight send.
@pytest.mark.anyio
@pytest.mark.parametrize(
    ("store", "code"),
    [
        (storage, HOLD_INCOMPLETE),
        (unavailable_store, HOLD_UNAVAILABLE),  # T4
        (corrupt_store, HOLD_UNAVAILABLE),  # T4
    ],
)
async def test_a_frozen_snapshot_without_a_write_cannot_use_the_in_flight_exception(
    store, code
) -> None:
    cases, documents, ownership, clm, target, case_id = make_ready_case()
    assert clm.get(case_id=case_id).submission_snapshot is not None
    assert not clm.target_write_started(case_id=case_id)
    calls = list(target.calls)
    assert not {"shell", "policy", "amend"} & set(calls)
    app = legacy_app((cases, documents, ownership, clm), store())
    async with http(app) as client:
        refused = await client.post(f"/api/clm/cases/{case_id}/submit")

    assert held(refused, code), refused.text
    assert target.calls == calls
    assert not clm.target_write_started(case_id=case_id)
    assert clm.get(case_id=case_id).execution_receipt is None


# T3 - nothing required is open (empty store, or optional fields only): unchanged.
@pytest.mark.anyio
@pytest.mark.parametrize("stage", [None, OPTIONAL_STAGE])
async def test_legacy_routes_send_as_before_when_nothing_required_is_open(stage) -> None:
    """Nothing required is open: legacy Submit still never starts a first write."""

    cases, documents, ownership, clm, target, case_id = make_ready_case()
    assert clm.get(case_id=case_id).submission_snapshot is not None
    calls = list(target.calls)
    app = legacy_app((cases, documents, ownership, clm), storage(stage=stage))
    async with http(app) as client:
        submitted = await client.post(f"/api/clm/cases/{case_id}/submit")

    assert held(submitted, RECOVERY_ONLY), submitted.text
    assert target.calls == calls
    assert not clm.target_write_started(case_id=case_id)


# T5 - a send with a retained write keeps going, once, even if a stage appears mid-send.
@pytest.mark.anyio
async def test_a_send_with_a_retained_write_finishes_without_replay(monkeypatch) -> None:
    cases, documents, ownership, clm, target, case_id = make_ready_case()
    build_receipt = cases._build_execution_receipt  # type: ignore[attr-defined]
    failed = False

    def fail_once(*args: object, **kwargs: object) -> Any:
        nonlocal failed
        if not failed:
            failed = True
            raise RuntimeError("PRIVATE_RECEIPT_SENTINEL")
        return build_receipt(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(cases, "_build_execution_receipt", fail_once)
    store = storage(stage=None)
    app = legacy_app((cases, documents, ownership, clm), store)
    # The first write starts through the (fenced) service path; legacy Submit only recovers.
    with pytest.raises(ClmInfrastructureError) as first_error:
        clm.submit(case_id=case_id, reauthorize=lambda: None)
    assert first_error.value.code == "CLM_FINALIZATION_RETRY_REQUIRED"
    assert clm.target_write_started(case_id=case_id)
    first_text = str(first_error.value)
    async with http(app) as client:

        activate(store, STAGE)  # a required stage is published while the send is open
        checker = WorkflowManagementService(
            definitions=store.definitions, runs=store.runs, cases=cases
        )
        assert checker.send_hold_code(case_id) == HOLD_INCOMPLETE

        # The legacy confirmation is retired.
        path, body = legacy_confirmation(case_id, 0, 1)
        assert retired(await client.post(path, json=body))

        recovered = await client.post(f"/api/clm/cases/{case_id}/submit")

    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["status"] == "MOCK_GOLDTIER_SUBMITTED"
    assert target.calls == ["search", "search", "shell", "policy", "amend", "search"]
    assert "PRIVATE_RECEIPT_SENTINEL" not in first_text + recovered.text


# T6/T7 - guard order: reauthorization, then D-124, then the workflow check.
class FakeZeroTouch:
    def __init__(self, *, pending: bool = False, hold: str | None = None) -> None:
        self.calls: list[str] = []
        self._pending = pending
        self._hold = hold
        self.automation_repository = SimpleNamespace(get_for_case=lambda _case_id: object())

    def advisory_continuation_pending(self, record: object) -> bool:
        self.calls.append("continuation")
        return self._pending

    def workflow_send_hold(self, case_id: UUID) -> str | None:
        self.calls.append("hold")
        return self._hold


CASE_ID = UUID("00000000-0000-4000-8000-000000000001")


def test_a_failed_reauthorization_stops_every_later_check() -> None:
    zero = FakeZeroTouch(hold=HOLD_INCOMPLETE)

    def refused() -> None:
        raise PermissionError("not this actor")

    with pytest.raises(PermissionError):
        _refusing_unsendable_case(refused, zero, CASE_ID)()  # type: ignore[arg-type]
    assert zero.calls == []


def test_a_pending_continuation_is_refused_before_the_workflow_check() -> None:
    zero = FakeZeroTouch(pending=True, hold=HOLD_INCOMPLETE)
    with pytest.raises(ClmRequestError) as raised:
        _refusing_unsendable_case(lambda: None, zero, CASE_ID)()  # type: ignore[arg-type]
    assert raised.value.code == "CLM_NOT_READY"
    assert zero.calls == ["continuation"]


@pytest.mark.parametrize("hold", [HOLD_INCOMPLETE, HOLD_UNAVAILABLE])
def test_only_a_retained_write_waives_a_hold_and_only_where_passed(hold) -> None:
    started: list[bool] = []

    def write_started(value: bool):
        def check() -> bool:
            started.append(value)
            return value

        return check

    for guard in (
        _refusing_unsendable_case(lambda: None, FakeZeroTouch(hold=hold), CASE_ID),
        _refusing_unsendable_case(
            lambda: None, FakeZeroTouch(hold=hold), CASE_ID,
            target_write_started=write_started(False),
        ),
    ):
        with pytest.raises(ClmRequestError) as raised:
            guard()  # type: ignore[operator]
        assert raised.value.code == hold
    _refusing_unsendable_case(
        lambda: None, FakeZeroTouch(hold=hold), CASE_ID,  # type: ignore[arg-type]
        target_write_started=write_started(True),
    )()
    assert started == [False, True]


def test_no_hold_never_consults_the_ledger() -> None:
    def must_not_run() -> bool:
        raise AssertionError("the ledger is read only when a hold exists")

    _refusing_unsendable_case(
        lambda: None, FakeZeroTouch(hold=None), CASE_ID,  # type: ignore[arg-type]
        target_write_started=must_not_run,
    )()


# Real Sandbox lane: the API, Director activation, RM confirmation and GoldTier fake.
@contextmanager
def real_flow(store: WorkflowPersistence, **overrides: Any) -> Iterator[tuple[Any, Any, dict]]:
    company = SHARE_COMPANIES[0]
    settings = sandbox_settings(**overrides)
    bundle = build_persistence_bundle(settings)
    manage_fixtures(bundle.registry_snapshots, now=datetime.now(UTC), seed=True)
    target = RecordingTarget(company.name, company.uen)
    with (
        patch("app.main.build_persistence_bundle", return_value=bundle),
        patch("app.main.build_workflow_persistence", return_value=store),
        TestClient(
            create_app(settings, acra_connector=NoAcra(), goldtier_transport=target)
        ) as client,
    ):
        yield client, target, prepare(client, company)


def legacy_body(client: Any, case_id: str) -> dict[str, int]:
    summary = client.get(f"/api/clm/cases/{case_id}").json()
    return {
        "expected_clm_version": summary["version"],
        "expected_case_event_count": len(summary["case"]["events"]),
    }


def zero_touch_body(current: dict) -> dict[str, int]:
    return {
        "expected_automation_version": current["version"],
        "expected_clm_version": current["clm"]["version"],
        "expected_case_event_count": len(current["case"]["events"]),
    }


def writes(target: Any) -> list[tuple]:
    return [call for call in target.calls if call[0] != "GET"]


# T1/T3 on the Sandbox lane: no GoldTier write until the RM confirms the stage.
def test_neither_legacy_route_writes_to_goldtier_until_the_stage_is_confirmed() -> None:
    with real_flow(storage(), workflow_manager_enabled=True) as (client, target, current):
        case_id = current["case"]["case_id"]
        before = list(target.calls)
        refused_confirmation = client.post(
            f"/api/clm/cases/{case_id}/target-confirmation", json=legacy_body(client, case_id)
        )
        refused_submit = client.post(f"/api/clm/cases/{case_id}/submit")
        assert retired(refused_confirmation), refused_confirmation.text
        assert held(refused_submit), refused_submit.text  # the hold still comes first
        assert target.calls == before

        run = onboarding_run(client, case_id)
        answered = client.put(
            case_url(case_id, run, "signatory", "answers"),
            json={
                "expected_revision": run["revision"],
                "values": {"full-name": "Sample Person", "birth-date": "2000-01-01"},
            },
        )
        assert answered.status_code == 200, answered.text
        confirmed_stage = client.post(
            case_url(case_id, run, "signatory", "confirm"),
            json={"expected_revision": answered.json()["revision"]},
        )
        assert confirmed_stage.status_code == 200, confirmed_stage.text

        submitted = client.post(f"/api/clm/cases/{case_id}/submit")
        # Existing order: with no confirmation, that refusal precedes recovery-only.
        assert held(submitted, "CLM_TARGET_CONFIRMATION_REQUIRED"), submitted.text
        assert target.calls == before
        # The send goes through the zero-touch route and its fence.
        latest = client.get(f"/api/clm/zero-touch/cases/{case_id}")
        assert latest.status_code == 200, latest.text
        assert confirm(client, latest.json())["status"] == "COMPLETED"
        assert writes(target)


# T7 - RBAC is unchanged and runs first: refused callers never learn about the hold.
@pytest.mark.parametrize("user_id", ["support-user", "hr-admin"])
def test_callers_without_case_access_are_refused_as_before(user_id) -> None:
    with real_flow(storage(), workflow_manager_enabled=True) as (client, target, current):
        case_id = current["case"]["case_id"]
        body = legacy_body(client, case_id)
        before = list(target.calls)
        other = login(client.app, user_id)
        for response in (
            other.post(f"/api/clm/cases/{case_id}/target-confirmation", json=body),
            other.post(f"/api/clm/cases/{case_id}/submit"),
        ):
            assert response.status_code in {403, 404}, response.text
            detail = response.json()["detail"]
            assert not isinstance(detail, dict) or detail["code"] not in HOLD_CODES
        assert target.calls == before


# T8 - the manager is off but a stored activation is still enforced, fail closed.
@pytest.mark.parametrize(
    ("store", "code"),
    [(storage, HOLD_INCOMPLETE), (unavailable_store, HOLD_UNAVAILABLE)],
)
def test_a_switched_off_manager_still_holds_every_send_route(store, code) -> None:
    with real_flow(store(), workflow_manager_enabled=False) as (client, target, current):
        case_id = current["case"]["case_id"]
        director = login(client.app, "olivia-koh")
        disabled = director.get("/api/workflows")
        assert disabled.status_code == 404
        assert disabled.json()["detail"]["code"] == "WORKFLOW_MANAGER_DISABLED"
        before = list(target.calls)

        zero_touch = client.post(
            f"/api/clm/zero-touch/cases/{case_id}/target-confirmation",
            json=zero_touch_body(current),
        )
        assert zero_touch.status_code >= 400 and zero_touch.json()["detail"]["code"] == code
        assert retired(
            client.post(
                f"/api/clm/cases/{case_id}/target-confirmation",
                json=legacy_body(client, case_id),
            )
        )
        submitted = client.post(f"/api/clm/cases/{case_id}/submit")
        assert held(submitted, code), submitted.text
        assert target.calls == before


# T9 - the manager is off and nothing is stored: sending is exactly as before.
def test_a_switched_off_manager_with_an_empty_store_sends_as_before() -> None:
    with real_flow(storage(stage=None), workflow_manager_enabled=False) as (client, _, current):
        assert confirm(client, current)["status"] == "COMPLETED"
