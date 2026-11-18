"""ADR-018 3.5: a frozen applicability basis is write-once (memory; Mongo is physical)."""

import uuid
from datetime import UTC, datetime

import pytest

from app.domain.workflows import (
    ApplicabilityBasis,
    ApplicabilityBasisReason,
    ApplicabilityBasisStatus,
    WorkflowRun,
)
from app.persistence.errors import PersistenceConflictError
from app.services.workflow_repository import (
    InMemoryWorkflowRunRepository,
    frozen_basis_rewritten,
)

NOW = datetime(2026, 11, 18, tzinfo=UTC)


def _basis(*, frozen: bool) -> ApplicabilityBasis:
    return ApplicabilityBasis(
        legal_form=None,
        status=ApplicabilityBasisStatus.UNVERIFIED,
        reason=ApplicabilityBasisReason.NO_BINDING,
        evaluated_at=NOW,
        evaluated_from_version=1,
        frozen=frozen,
    )


def _run() -> WorkflowRun:
    return WorkflowRun(
        run_id=uuid.uuid4(),
        case_id=uuid.uuid4(),
        workflow_id="w-basis",
        workflow_name="Basis",
        use_case="Synthetic",
        workflow_version=1,
        stages=(),
        created_at=NOW,
        updated_at=NOW,
    )


def _next(run: WorkflowRun, **changes: object) -> WorkflowRun:
    return run.model_copy(update={**changes, "revision": run.revision + 1})


def test_unfrozen_basis_may_be_frozen_and_then_never_rewritten() -> None:
    runs = InMemoryWorkflowRunRepository()
    run = runs.create(_run())
    unfrozen = runs.update(
        _next(run, applicability_basis=_basis(frozen=False)), expected_revision=run.revision
    )
    frozen = runs.update(
        _next(unfrozen, applicability_basis=_basis(frozen=True)),
        expected_revision=unfrozen.revision,
    )
    carried = runs.update(_next(frozen), expected_revision=frozen.revision)  # unchanged: allowed
    for rewrite in (None, _basis(frozen=False)):
        with pytest.raises(PersistenceConflictError):
            runs.update(
                _next(carried, applicability_basis=rewrite), expected_revision=carried.revision
            )
    assert runs.get(run.run_id).applicability_basis == _basis(frozen=True)


def test_rewrite_predicate() -> None:
    run = _run()
    assert not frozen_basis_rewritten(
        run, run.model_copy(update={"applicability_basis": _basis(frozen=True)})
    )
    stored = run.model_copy(update={"applicability_basis": _basis(frozen=True)})
    assert not frozen_basis_rewritten(stored, stored)
    assert frozen_basis_rewritten(stored, run)
