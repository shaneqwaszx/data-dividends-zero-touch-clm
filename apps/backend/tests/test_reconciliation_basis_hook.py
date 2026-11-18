"""ADR-018 3.5 F5 (M3-C QG P3-1): a committed legal-name decision re-runs the basis hook."""

from uuid import UUID

from test_phase11_reconciliation import FieldOverrideIdp, attach, build_system, current_discrepancy

from app.domain.documents import DocumentFieldKey
from app.domain.reconciliation import ReconciliationDecisionAction, ReconciliationField


def _decide(action: ReconciliationDecisionAction) -> tuple[list[str | None], UUID]:
    _, zero, _, _, _ = build_system()
    created = zero.create_case("202400001A")
    paused = attach(
        zero,
        created.case_id,
        FieldOverrideIdp({DocumentFieldKey.LEGAL_NAME: "DOCUMENT SELECTED PTE. LTD."}),
    )
    seen: list[str | None] = []

    def hook(case_id: UUID) -> str:
        case = zero._cases.get_case(case_id)  # noqa: SLF001
        seen.append(case.entity.legal_name if case and case.entity else None)
        return "UNCHANGED"

    zero._cases.bind_registry_binding_hook(hook)  # noqa: SLF001
    record = zero._reconciliation.get(case_id=created.case_id)  # noqa: SLF001
    assert record is not None
    discrepancy = current_discrepancy(record, ReconciliationField.LEGAL_NAME)
    zero.resolve_reconciliation_discrepancy(
        case_id=created.case_id,
        discrepancy_id=discrepancy.discrepancy_id,
        action=action,
        expected_automation_version=paused.version,
        expected_reconciliation_version=record.version,
        evidence_fingerprint=discrepancy.evidence_fingerprint,
    )
    return seen, created.case_id


def test_a_document_legal_name_decision_runs_the_hook_after_its_commit() -> None:
    seen, _ = _decide(ReconciliationDecisionAction.USE_DOCUMENT_VALUE)
    assert seen and seen[0] == "DOCUMENT SELECTED PTE. LTD."


def test_keeping_the_registry_value_does_not_run_the_hook_for_the_decision() -> None:
    seen, _ = _decide(ReconciliationDecisionAction.KEEP_REGISTRY_VALUE)
    assert "DOCUMENT SELECTED PTE. LTD." not in seen
