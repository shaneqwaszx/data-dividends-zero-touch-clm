"""ADR-017 P2-0 writer release: the dispatch fence, memory mode and structure (CT-0, CT-4..7,
CT-17, CT-18, CT-20 where they apply without a server). Physical counterpart:
``test_adr017_dispatch_fence_real_mongo.py``.
"""

from __future__ import annotations

import ast
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
from test_adr017_reader_release import _snapshot

from app.domain.target_submission import (
    GoldTierExecutionLedgerEntry,
    GoldTierExecutionLedgerState,
    GoldTierOperationMarker,
    WorkflowDispatchState,
)
from app.domain.workflows import ONBOARDING_WORKFLOW_ID, WorkflowDefinition, WorkflowVersion
from app.persistence.errors import PersistenceOutcomeAmbiguousError
from app.services.dispatch_fence import (
    CHECK_UNAVAILABLE,
    HOLD_INCOMPLETE,
    DispatchFence,
    FenceHealth,
)
from app.services.errors import DispatchFenceRefusedError
from app.services.target_execution_repository import (
    InMemoryTargetExecutionRepository,
    TargetExecutionRepositoryConflictError,
)
from app.services.workflow_repository import InMemoryWorkflowDefinitionRepository

BACKEND = Path(__file__).resolve().parents[1]
NOW = datetime(2031, 3, 1, 9, 0, tzinfo=UTC)
SHELL = GoldTierOperationMarker.SHELL


class Clock:
    def __init__(self) -> None:
        self.now = NOW

    def __call__(self) -> datetime:
        return self.now


def _entry(*attempted: GoldTierOperationMarker) -> GoldTierExecutionLedgerEntry:
    base = _snapshot().target_executions[0]
    return base.model_copy(
        update={
            "attempted_operations": attempted,
            "completed_operations": tuple(
                item for item in attempted if item == GoldTierOperationMarker.SEARCH
            ),
            "resolved_operations": tuple(
                item for item in attempted if item == GoldTierOperationMarker.SEARCH
            ),
        }
    )


def _definitions(version: int = 0) -> InMemoryWorkflowDefinitionRepository:
    repository = InMemoryWorkflowDefinitionRepository()
    versions = tuple(
        WorkflowVersion(version=number, stages=(), activated_at=NOW, activated_by="d-director")
        for number in range(1, version + 1)
    )
    repository.create(
        WorkflowDefinition(
            workflow_id=ONBOARDING_WORKFLOW_ID, name="Corporate onboarding",
            use_case="Corporate onboarding", country="Singapore", versions=versions,
            created_at=NOW, updated_at=NOW,
        )
    )
    return repository


def _fence(ledger, definitions, *, hold=None, available=True, on_hold=None) -> DispatchFence:
    return DispatchFence(
        ledger=ledger,
        definitions=definitions,
        workflow_id=ONBOARDING_WORKFLOW_ID,
        hold=hold or (lambda _case_id: None),
        health=lambda: FenceHealth(available=available, reason=None if available else "X"),
        on_hold=on_hold,
    )


def _ledger(entry: GoldTierExecutionLedgerEntry, clock: Clock):
    ledger = InMemoryTargetExecutionRepository(clock=clock)
    ledger.create(entry)
    return ledger


def _authorise(fence, entry, operation=SHELL):
    return fence.authorise_first_write(
        case_id=entry.submission_input.case_id,
        submission_id=entry.submission_input.submission_id,
        operation=operation,
    )


# --- D1-D6 happy path (CT-4) --------------------------------------------------------------


@pytest.mark.parametrize("version", [0, 2])
def test_the_fence_records_the_first_write_with_its_version_and_receipt(version) -> None:
    clock, entry = Clock(), _entry(GoldTierOperationMarker.SEARCH)
    ledger, definitions = _ledger(entry, clock), _definitions(version)
    written = _authorise(_fence(ledger, definitions), entry)
    claim = written.workflow_dispatch
    assert claim is not None and claim.state == WorkflowDispatchState.AUTHORISED
    assert claim.first_write is not None
    assert claim.first_write.operation == SHELL
    assert claim.first_write.version == version == claim.version
    assert claim.first_write.receipt == claim.receipt
    assert written.attempted_operations == (GoldTierOperationMarker.SEARCH, SHELL)
    assert claim.lease_until == NOW + timedelta(seconds=60)
    assert definitions._dispatch_authorisations[ONBOARDING_WORKFLOW_ID] == 1  # noqa: SLF001


def test_a_hold_at_d1_refuses_before_any_claim_and_supersedes() -> None:
    clock, entry = Clock(), _entry(GoldTierOperationMarker.SEARCH)
    ledger, superseded = _ledger(entry, clock), []
    fence = _fence(
        ledger, _definitions(), hold=lambda _case_id: HOLD_INCOMPLETE,
        on_hold=lambda case_id, code: superseded.append((case_id, code)),
    )
    with pytest.raises(DispatchFenceRefusedError) as refused:
        _authorise(fence, entry)
    assert refused.value.code == HOLD_INCOMPLETE
    assert superseded == [(entry.submission_input.case_id, HOLD_INCOMPLETE)]
    assert ledger.get(entry.submission_input.submission_id) == entry


@pytest.mark.parametrize("available", [False])
def test_an_unavailable_guarantee_refuses_every_dispatch(available) -> None:
    clock, entry = Clock(), _entry(GoldTierOperationMarker.SEARCH)
    ledger = _ledger(entry, clock)
    with pytest.raises(DispatchFenceRefusedError) as refused:
        _authorise(_fence(ledger, _definitions(), available=available), entry)
    assert refused.value.code == CHECK_UNAVAILABLE
    assert ledger.get(entry.submission_input.submission_id) == entry


def test_a_missing_onboarding_definition_is_refused_e2_amendment() -> None:
    clock, entry = Clock(), _entry(GoldTierOperationMarker.SEARCH)
    ledger = _ledger(entry, clock)
    with pytest.raises(DispatchFenceRefusedError) as refused:
        _authorise(_fence(ledger, InMemoryWorkflowDefinitionRepository()), entry)
    assert refused.value.code == CHECK_UNAVAILABLE
    assert ledger.get(entry.submission_input.submission_id) == entry


def test_d3_refuses_when_the_version_changes_after_d1_and_never_writes() -> None:
    """CT-4: a publication between D1 and D3 makes D3 match nothing (at most 3 retries)."""

    clock, entry = Clock(), _entry(GoldTierOperationMarker.SEARCH)
    ledger = _ledger(entry, clock)
    definitions = _definitions(1)
    stale = SimpleNamespace(
        dispatch_active_version=lambda _wid: 0,  # a stale D1 read
        authorise_dispatch=definitions.authorise_dispatch,
    )
    with pytest.raises(DispatchFenceRefusedError) as refused:
        _authorise(_fence(ledger, stale), entry)
    assert refused.value.code == CHECK_UNAVAILABLE
    stored = ledger.get(entry.submission_input.submission_id)
    assert stored is not None and stored.attempted_operations == entry.attempted_operations
    assert stored.workflow_dispatch is not None
    assert stored.workflow_dispatch.state == WorkflowDispatchState.TENTATIVE  # expires
    assert ONBOARDING_WORKFLOW_ID not in definitions._dispatch_authorisations  # noqa: SLF001


def test_a_slipped_legacy_append_fails_d3() -> None:
    definitions = _definitions(1)
    current = definitions.get(ONBOARDING_WORKFLOW_ID)
    assert current is not None
    slipped = current.model_copy(
        update={"versions": (*current.versions, WorkflowVersion(
            version=2, stages=(), activated_at=NOW, activated_by="legacy"))}
    )
    definitions._items[ONBOARDING_WORKFLOW_ID] = slipped  # noqa: SLF001 - simulated rollback
    assert definitions.authorise_dispatch(ONBOARDING_WORKFLOW_ID, 1) is False
    assert definitions.verify_dispatch_state() == [
        (ONBOARDING_WORKFLOW_ID, "LAST_VERSION_NOT_LATEST")
    ]


# --- leases, tokens, takeover (CT-18, CT-6) -------------------------------------------------


def test_a_live_claim_of_another_worker_stops_d2() -> None:
    clock, entry = Clock(), _entry(GoldTierOperationMarker.SEARCH)
    ledger = _ledger(entry, clock)
    sid = entry.submission_input.submission_id
    assert ledger.fence_claim(sid, token="1" * 32, version=0) is not None
    assert ledger.fence_claim(sid, token="2" * 32, version=0) is None
    with pytest.raises(DispatchFenceRefusedError):
        _authorise(_fence(ledger, _definitions()), entry)


def test_an_expired_search_only_claim_is_taken_over() -> None:
    clock, entry = Clock(), _entry(GoldTierOperationMarker.SEARCH)
    ledger = _ledger(entry, clock)
    sid = entry.submission_input.submission_id
    assert ledger.fence_claim(sid, token="1" * 32, version=0) is not None
    clock.now = NOW + timedelta(seconds=61)
    written = _authorise(_fence(ledger, _definitions()), entry)
    assert written.workflow_dispatch is not None and written.workflow_dispatch.token != "1" * 32


def test_lease_expiry_before_d5_writes_no_marker() -> None:
    clock, entry = Clock(), _entry(GoldTierOperationMarker.SEARCH)
    ledger = _ledger(entry, clock)
    sid = entry.submission_input.submission_id
    assert ledger.fence_claim(sid, token="1" * 32, version=0) is not None
    assert ledger.fence_authorise(sid, token="1" * 32, version=0) is not None
    clock.now = NOW + timedelta(seconds=60)
    assert ledger.fence_first_write(sid, token="1" * 32, operation=SHELL) is None
    stored = ledger.get(sid)
    assert stored is not None and SHELL not in stored.attempted_operations


def test_a_stale_token_cannot_authorise_or_write() -> None:
    clock, entry = Clock(), _entry(GoldTierOperationMarker.SEARCH)
    ledger = _ledger(entry, clock)
    sid = entry.submission_input.submission_id
    assert ledger.fence_claim(sid, token="1" * 32, version=0) is not None
    assert ledger.fence_authorise(sid, token="2" * 32, version=0) is None
    assert ledger.fence_authorise(sid, token="1" * 32, version=0) is not None
    assert ledger.fence_first_write(sid, token="2" * 32, operation=SHELL) is None


def test_after_a_write_marker_no_claim_or_takeover_is_possible() -> None:
    """Expiry never authorises replay (CT-6)."""

    clock, entry = Clock(), _entry(GoldTierOperationMarker.SEARCH)
    ledger = _ledger(entry, clock)
    _authorise(_fence(ledger, _definitions()), entry)
    clock.now = NOW + timedelta(hours=1)
    sid = entry.submission_input.submission_id
    assert ledger.fence_claim(sid, token="3" * 32, version=0) is None
    with pytest.raises(DispatchFenceRefusedError):
        _authorise(_fence(ledger, _definitions()), entry)


def test_ledger_replace_can_never_record_a_first_write_marker() -> None:
    clock, entry = Clock(), _entry(GoldTierOperationMarker.SEARCH)
    ledger = _ledger(entry, clock)
    marked = entry.model_copy(update={"attempted_operations": (*entry.attempted_operations, SHELL)})
    with pytest.raises(TargetExecutionRepositoryConflictError):
        ledger.replace(
            marked,
            expected_state=GoldTierExecutionLedgerState.IN_PROGRESS.value,
            expected_attempted=entry.attempted_operations,
        )


def test_ledger_replace_asserts_the_attempts_it_read() -> None:
    """CT-17 (memory): a caller whose read is stale is refused, never overwrites."""

    clock, entry = Clock(), _entry(GoldTierOperationMarker.SEARCH)
    ledger = _ledger(entry, clock)
    with pytest.raises(TargetExecutionRepositoryConflictError):
        ledger.replace(
            entry,
            expected_state=GoldTierExecutionLedgerState.IN_PROGRESS.value,
            expected_attempted=(),
        )


def test_an_ambiguous_fence_step_stops_before_d6() -> None:
    clock, entry = Clock(), _entry(GoldTierOperationMarker.SEARCH)
    ledger = _ledger(entry, clock)

    def ambiguous(*_args, **_kwargs):
        raise PersistenceOutcomeAmbiguousError

    ledger.fence_first_write = ambiguous  # type: ignore[method-assign]
    with pytest.raises(DispatchFenceRefusedError) as refused:
        _authorise(_fence(ledger, _definitions()), entry)
    assert refused.value.code == CHECK_UNAVAILABLE


# --- the choke point (CT-0) ----------------------------------------------------------------

_WRITES = {"create_shell_customer": "SHELL", "create_policy": "POLICY", "amend_party": "AMEND"}


def test_every_shell_policy_or_amend_call_is_preceded_by_its_fenced_marker() -> None:
    offences: list[str] = []
    for module in (BACKEND / "app").rglob("*.py"):
        if "connectors" in module.parts or "mappers" in module.parts:
            continue
        tree = ast.parse(module.read_text(encoding="utf-8"))
        for function in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
            calls = [n for n in ast.walk(function) if isinstance(n, ast.Call)]
            for call in calls:
                name = getattr(call.func, "attr", None)
                if name not in _WRITES or "goldtier" not in ast.unparse(call.func).lower():
                    continue
                markers = [
                    other.lineno for other in calls
                    if getattr(other.func, "attr", None) == "_mark_operation_attempted"
                    and _WRITES[name] in ast.unparse(other)
                    and other.lineno < call.lineno
                ]
                if not markers:
                    offences.append(f"{module.name}:{call.lineno} {name}")
    assert offences == []
    onboarding = (BACKEND / "app/services/onboarding.py").read_text(encoding="utf-8")
    tree = ast.parse(onboarding)
    mark = next(
        n for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "_mark_operation_attempted"
    )
    source = ast.unparse(mark)
    assert "authorise_first_write" in source and "has_write_marker" in source


# --- sent predicate and re-confirmation (CT-7) ---------------------------------------------


def test_sent_means_a_marker_outcome_or_receipt_never_a_claim() -> None:
    from app.services.onboarding import OnboardingService

    clock, entry = Clock(), _entry(GoldTierOperationMarker.SEARCH)
    ledger = _ledger(entry, clock)
    service = SimpleNamespace(_target_executions=ledger)
    sent = OnboardingService.case_is_sent.__get__(service)  # type: ignore[attr-defined]
    case_id: UUID = entry.submission_input.case_id
    sid = entry.submission_input.submission_id
    assert ledger.fence_claim(sid, token="1" * 32, version=0) is not None
    assert sent(case_id) is False  # a TENTATIVE claim is not sent
    assert ledger.fence_authorise(sid, token="1" * 32, version=0) is not None
    assert sent(case_id) is False  # nor is AUTHORISED
    assert ledger.fence_first_write(sid, token="1" * 32, operation=SHELL) is not None
    assert sent(case_id) is True


def test_a_new_requirement_supersedes_the_confirmation_and_requires_reconfirming() -> None:
    """RD-3 / CT-7 through the real service: the fence supersedes (only for a newly
    applicable requirement); the recovery-only legacy check writes nothing (QG R0 P3-2)."""

    from uuid import uuid4

    from test_clm_orchestration import make_ready_case

    from app.main import _refusing_unsendable_case
    from app.services.clm_errors import ClmRequestError
    from app.services.dispatch_fence import RECONFIRMATION_REQUIRED

    cases, _documents, _ownership, _clm, _target, case_id = make_ready_case()
    assert cases.get_case(case_id).target_dispatch_confirmation is not None
    zero_touch = SimpleNamespace(
        automation_repository=SimpleNamespace(get_for_case=lambda _case_id: None),
        advisory_continuation_pending=lambda _record: False,
        workflow_send_hold=lambda _case_id: HOLD_INCOMPLETE,
    )
    check = _refusing_unsendable_case(
        lambda: None, zero_touch, case_id, target_write_started=lambda: False, onboarding=cases
    )
    events = len(cases.get_case(case_id).events)
    with pytest.raises(ClmRequestError) as held:
        check()
    assert held.value.code == HOLD_INCOMPLETE
    assert cases.get_case(case_id).target_dispatch_confirmation is not None
    assert len(cases.get_case(case_id).events) == events  # the legacy check wrote nothing

    fence = DispatchFence(
        ledger=cases.target_execution_repository, definitions=_definitions(),
        workflow_id=ONBOARDING_WORKFLOW_ID, hold=lambda _case_id: HOLD_INCOMPLETE,
        health=lambda: FenceHealth(available=True),
        on_hold=lambda cid, _code: cases.supersede_dispatch_confirmation(cid),
    )
    with pytest.raises(DispatchFenceRefusedError):
        fence.authorise_first_write(case_id=case_id, submission_id=uuid4(), operation=SHELL)
    case = cases.get_case(case_id)
    assert case.target_dispatch_confirmation is None
    assert case.events[-1].code == "DISPATCH_RECONFIRMATION_REQUIRED"
    assert "SUPERSEDED_BY_WORKFLOW_CHANGE" in case.events[-1].message
    zero_touch.workflow_send_hold = lambda _case_id: None  # the new stage is confirmed
    with pytest.raises(ClmRequestError) as again:
        check()
    assert again.value.code == RECONFIRMATION_REQUIRED
    assert cases.reconfirmation_required(case_id) is True


# --- zero-touch send: a fence refusal never ends the case (QG R0 P2-1) --------------------


def _zero_touch_case_at_confirmation():
    from test_aws_goldtier_sandbox_readiness import UEN, ok, set_writes
    from test_goldtier_xpi_sandbox import PDF, FakeXpiTransport, _sandbox_zero_touch_system

    transport = FakeXpiTransport([ok([])])
    zero, _, _ = _sandbox_zero_touch_system(transport)
    set_writes(zero._cases, transport, allowed=True)  # noqa: SLF001
    created = zero.create_case(UEN)
    record = zero.attach_document(
        case_id=created.case_id, display_name="sandbox-profile.pdf",
        content_type="application/pdf", content=PDF,
    )
    assert any(i.exception_type == "TARGET_CONFIRMATION_REQUIRED" for i in record.active_exceptions)
    return zero, transport, record


def _refuse_once(monkeypatch, code: str) -> list[str]:
    original = DispatchFence.authorise_first_write
    refused: list[str] = []

    def once(self, **kwargs):
        if not refused:
            refused.append(code)
            raise DispatchFenceRefusedError(code)
        return original(self, **kwargs)

    monkeypatch.setattr(DispatchFence, "authorise_first_write", once)
    return refused


def test_an_unavailable_fence_pauses_the_send_and_the_same_submission_continues(
    monkeypatch,
) -> None:
    from test_aws_goldtier_sandbox_readiness import confirmation, full_path_transport, methods, ok

    zero, transport, record = _zero_touch_case_at_confirmation()
    transport.responses.extend([ok([]), *full_path_transport().responses])
    refused = _refuse_once(monkeypatch, CHECK_UNAVAILABLE)
    paused = zero.confirm_target_dispatch(**confirmation(zero, record))
    assert refused == [CHECK_UNAVAILABLE]
    assert paused.status == "RECOVERY_PENDING" and paused.technical_failure is None
    assert methods(transport).count("POST") == 0
    finished = zero.start(case_id=record.case_id)
    assert finished.status == "COMPLETED"
    assert methods(transport).count("POST") == 3


@pytest.mark.parametrize(
    "code", ["WORKFLOW_STAGE_INCOMPLETE", "WORKFLOW_DISPATCH_RECONFIRMATION_REQUIRED"]
)
def test_a_held_send_returns_to_confirmation_and_reconfirms_through_zero_touch(
    monkeypatch, code: str
) -> None:
    from test_aws_goldtier_sandbox_readiness import confirmation, full_path_transport, methods, ok

    zero, transport, record = _zero_touch_case_at_confirmation()
    transport.responses.extend([ok([]), *full_path_transport().responses])
    _refuse_once(monkeypatch, code)
    held = zero.confirm_target_dispatch(**confirmation(zero, record))
    assert held.status == "WAITING_FOR_REVIEW" and held.technical_failure is None
    assert held.current_stage == "READINESS"
    assert any(i.exception_type == "TARGET_CONFIRMATION_REQUIRED" for i in held.active_exceptions)
    assert methods(transport).count("POST") == 0
    finished = zero.confirm_target_dispatch(**confirmation(zero, held))
    assert finished.status == "COMPLETED", (
        finished.technical_failure, [e.code for e in finished.events[-4:]]
    )
    assert methods(transport).count("POST") == 3


def test_a_durable_ledger_without_a_bound_fence_refuses_every_first_write() -> None:
    """QG R0 P3-8: production never falls back to a process-local fence."""

    from app.services.onboarding import OnboardingService

    service = SimpleNamespace(
        _dispatch_fence=None, _target_executions=object(), _clock=lambda: NOW
    )
    with pytest.raises(DispatchFenceRefusedError) as refused:
        OnboardingService._fence(service)  # type: ignore[arg-type]
    assert refused.value.code == CHECK_UNAVAILABLE


def test_an_unreadable_check_never_supersedes_a_confirmation() -> None:
    """QG R0 P3-1: only a newly applicable requirement supersedes."""

    clock, entry = Clock(), _entry(GoldTierOperationMarker.SEARCH)
    superseded: list[str] = []
    fence = _fence(
        _ledger(entry, clock), _definitions(),
        hold=lambda _case_id: "WORKFLOW_STAGE_CHECK_UNAVAILABLE",
        on_hold=lambda _case_id, code: superseded.append(code),
    )
    with pytest.raises(DispatchFenceRefusedError):
        _authorise(fence, entry)
    assert superseded == []
