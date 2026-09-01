"""Quality-gate remediation tests for Phase 11 integrity authority boundaries."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from test_phase11_reconciliation import FieldOverrideIdp, attach
from test_zero_touch_orchestration import build_system

from app.domain.documents import DocumentFieldKey
from app.domain.models import SafeError
from app.domain.reconciliation import (
    DiscrepancyStatus,
    FieldReconciliationResult,
    ObservationValidity,
    ReconciliationCaseRecord,
    ReconciliationDecision,
    ReconciliationDecisionAction,
    ReconciliationDiscrepancy,
    ReconciliationField,
    ReconciliationObservation,
    ReconciliationOutcome,
    ReconciliationSourceKind,
    ReconciliationStatus,
    derive_allowed_actions,
)
from app.services.reconciliation_errors import (
    ReconciliationInfrastructureError,
    ReconciliationRequestError,
)
from app.services.reconciliation_repository import (
    ReconciliationRepositoryConflictError,
)

NOW = datetime(2026, 8, 29, 1, 0, tzinfo=UTC)


def source_observation(
    field: ReconciliationField,
    source: ReconciliationSourceKind,
    value: str | None,
    *,
    validity: ObservationValidity = ObservationValidity.VALID,
) -> ReconciliationObservation:
    return ReconciliationObservation(
        observation_id=uuid4(),
        field_name=field,
        raw_value=value,
        normalized_value=value,
        source_kind=source,
        source_system="ACRA" if source == ReconciliationSourceKind.REGISTRY else "LOCAL_IDP",
        environment="MOCK" if source == ReconciliationSourceKind.REGISTRY else "LOCAL_POC",
        observed_at=NOW,
        evidence_reference=(
            "registry:entity" if source == ReconciliationSourceKind.REGISTRY else "document:field"
        ),
        source_record_id=uuid4() if source == ReconciliationSourceKind.DOCUMENT_IDP else None,
        confidence=0.95 if source == ReconciliationSourceKind.DOCUMENT_IDP else None,
        validity=validity,
    )


def observations_for(
    field: ReconciliationField, outcome: ReconciliationOutcome
) -> tuple[ReconciliationObservation, ReconciliationObservation]:
    registry = source_observation(field, ReconciliationSourceKind.REGISTRY, "ACME PTE LTD")
    if outcome == ReconciliationOutcome.MATCH:
        document = source_observation(field, ReconciliationSourceKind.DOCUMENT_IDP, "ACME PTE LTD")
    elif outcome == ReconciliationOutcome.CONFLICT:
        document = source_observation(field, ReconciliationSourceKind.DOCUMENT_IDP, "OTHER PTE LTD")
    elif outcome == ReconciliationOutcome.MISSING_IN_SOURCE:
        document = source_observation(
            field,
            ReconciliationSourceKind.DOCUMENT_IDP,
            None,
            validity=ObservationValidity.MISSING,
        )
    elif outcome == ReconciliationOutcome.UNVERIFIABLE:
        document = source_observation(
            field,
            ReconciliationSourceKind.DOCUMENT_IDP,
            "OTHER PTE LTD",
            validity=ObservationValidity.UNVERIFIABLE,
        ).model_copy(update={"confidence": 0.4})
    else:
        document = source_observation(
            field,
            ReconciliationSourceKind.DOCUMENT_IDP,
            "INVALID VALUE",
            validity=ObservationValidity.INVALID,
        )
    return registry, document


def field_result(
    field: ReconciliationField,
    outcome: ReconciliationOutcome,
    discrepancy_id: UUID | None = None,
) -> FieldReconciliationResult:
    return FieldReconciliationResult(
        field_name=field,
        observations=observations_for(field, outcome),
        outcome=outcome,
        discrepancy_id=discrepancy_id,
    )


def discrepancy(
    field: ReconciliationField,
    outcome: ReconciliationOutcome,
    *,
    discrepancy_id: UUID | None = None,
    status: DiscrepancyStatus = DiscrepancyStatus.OPEN,
) -> ReconciliationDiscrepancy:
    observations = observations_for(field, outcome)
    allowed_actions = derive_allowed_actions(field, outcome, observations)
    decision = None
    if status == DiscrepancyStatus.RESOLVED:
        selected = observations[0]
        decision = ReconciliationDecision(
            action=ReconciliationDecisionAction.KEEP_REGISTRY_VALUE,
            selected_observation_id=selected.observation_id,
            selected_value=selected.normalized_value or "missing",
            decided_at=NOW,
            reconciliation_version=1,
            evidence_fingerprint="a" * 64,
        )
    return ReconciliationDiscrepancy(
        discrepancy_id=discrepancy_id or uuid4(),
        field_name=field,
        outcome=outcome,
        observations=observations,
        created_at=NOW,
        status=status,
        allowed_actions=allowed_actions,
        evidence_fingerprint="a" * 64,
        decision=decision,
    )


def record_with_status(status: ReconciliationStatus) -> ReconciliationCaseRecord:
    if status in {ReconciliationStatus.NOT_STARTED, ReconciliationStatus.FAILED}:
        return ReconciliationCaseRecord(
            case_id=uuid4(),
            reconciliation_id=uuid4(),
            status=status,
            evidence_fingerprint="b" * 64,
            error=(
                SafeError(code="RECONCILIATION_FAILED", message="Safe failure.")
                if status == ReconciliationStatus.FAILED
                else None
            ),
            created_at=NOW,
            updated_at=NOW,
        )
    discrepancies: list[ReconciliationDiscrepancy] = []
    fields: list[FieldReconciliationResult] = []
    if status in {ReconciliationStatus.REVIEW_REQUIRED, ReconciliationStatus.RESOLVED}:
        current = discrepancy(
            ReconciliationField.LEGAL_NAME,
            ReconciliationOutcome.CONFLICT,
            status=(
                DiscrepancyStatus.OPEN
                if status == ReconciliationStatus.REVIEW_REQUIRED
                else DiscrepancyStatus.RESOLVED
            ),
        )
        discrepancies.append(current)
        fields.append(
            FieldReconciliationResult(
                field_name=ReconciliationField.LEGAL_NAME,
                observations=current.observations,
                outcome=current.outcome,
                discrepancy_id=current.discrepancy_id,
            )
        )
    else:
        fields.append(field_result(ReconciliationField.LEGAL_NAME, ReconciliationOutcome.MATCH))
    fields.extend(
        field_result(field, ReconciliationOutcome.MATCH) for field in tuple(ReconciliationField)[1:]
    )
    return ReconciliationCaseRecord(
        case_id=uuid4(),
        reconciliation_id=uuid4(),
        status=status,
        source_document_ids=(uuid4(),),
        source_document_event_counts=(1,),
        evidence_fingerprint="b" * 64,
        fields=tuple(fields),
        discrepancies=discrepancies,
        error=(
            SafeError(code="RECONCILIATION_FAILED", message="Safe failure.")
            if status == ReconciliationStatus.FAILED
            else None
        ),
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.mark.parametrize(
    ("actual", "declared"),
    [
        (ReconciliationOutcome.CONFLICT, ReconciliationOutcome.MATCH),
        (ReconciliationOutcome.MATCH, ReconciliationOutcome.CONFLICT),
        (ReconciliationOutcome.CONFLICT, ReconciliationOutcome.INVALID),
        (ReconciliationOutcome.MATCH, ReconciliationOutcome.MISSING_IN_SOURCE),
        (ReconciliationOutcome.CONFLICT, ReconciliationOutcome.UNVERIFIABLE),
    ],
)
def test_direct_field_result_rejects_false_outcome(
    actual: ReconciliationOutcome, declared: ReconciliationOutcome
) -> None:
    with pytest.raises(ValidationError):
        FieldReconciliationResult(
            field_name=ReconciliationField.LEGAL_NAME,
            observations=observations_for(ReconciliationField.LEGAL_NAME, actual),
            outcome=declared,
            discrepancy_id=None if declared == ReconciliationOutcome.MATCH else uuid4(),
        )


@pytest.mark.parametrize("outcome", tuple(ReconciliationOutcome))
def test_direct_field_result_accepts_each_truthful_outcome(
    outcome: ReconciliationOutcome,
) -> None:
    result = field_result(
        ReconciliationField.LEGAL_NAME,
        outcome,
        None if outcome == ReconciliationOutcome.MATCH else uuid4(),
    )
    assert result.outcome == outcome


def test_discrepancy_rejects_invalid_without_invalid_evidence() -> None:
    with pytest.raises(ValidationError):
        ReconciliationDiscrepancy(
            discrepancy_id=uuid4(),
            field_name=ReconciliationField.LEGAL_NAME,
            outcome=ReconciliationOutcome.INVALID,
            observations=observations_for(
                ReconciliationField.LEGAL_NAME, ReconciliationOutcome.CONFLICT
            ),
            created_at=NOW,
            evidence_fingerprint="a" * 64,
        )


def test_discrepancy_rejects_conflict_without_distinct_usable_values() -> None:
    with pytest.raises(ValidationError):
        ReconciliationDiscrepancy(
            discrepancy_id=uuid4(),
            field_name=ReconciliationField.LEGAL_NAME,
            outcome=ReconciliationOutcome.CONFLICT,
            observations=observations_for(
                ReconciliationField.LEGAL_NAME, ReconciliationOutcome.MATCH
            ),
            created_at=NOW,
            evidence_fingerprint="a" * 64,
        )


def test_discrepancy_rejects_non_hex_fingerprint() -> None:
    observations = observations_for(ReconciliationField.LEGAL_NAME, ReconciliationOutcome.CONFLICT)
    with pytest.raises(ValidationError):
        ReconciliationDiscrepancy(
            discrepancy_id=uuid4(),
            field_name=ReconciliationField.LEGAL_NAME,
            outcome=ReconciliationOutcome.CONFLICT,
            observations=observations,
            created_at=NOW,
            allowed_actions=derive_allowed_actions(
                ReconciliationField.LEGAL_NAME,
                ReconciliationOutcome.CONFLICT,
                observations,
            ),
            evidence_fingerprint="z" * 64,
        )


def test_unverifiable_cannot_advertise_keep_registry() -> None:
    with pytest.raises(ValidationError):
        ReconciliationDiscrepancy(
            discrepancy_id=uuid4(),
            field_name=ReconciliationField.LEGAL_NAME,
            outcome=ReconciliationOutcome.UNVERIFIABLE,
            observations=observations_for(
                ReconciliationField.LEGAL_NAME, ReconciliationOutcome.UNVERIFIABLE
            ),
            created_at=NOW,
            allowed_actions=(ReconciliationDecisionAction.KEEP_REGISTRY_VALUE,),
            evidence_fingerprint="a" * 64,
        )


def test_unsupported_field_cannot_advertise_use_document() -> None:
    observations = observations_for(
        ReconciliationField.REGISTERED_ADDRESS, ReconciliationOutcome.CONFLICT
    )
    with pytest.raises(ValidationError):
        ReconciliationDiscrepancy(
            discrepancy_id=uuid4(),
            field_name=ReconciliationField.REGISTERED_ADDRESS,
            outcome=ReconciliationOutcome.CONFLICT,
            observations=observations,
            created_at=NOW,
            allowed_actions=(
                ReconciliationDecisionAction.KEEP_REGISTRY_VALUE,
                ReconciliationDecisionAction.USE_DOCUMENT_VALUE,
            ),
            evidence_fingerprint="a" * 64,
        )


@pytest.mark.parametrize(
    "status",
    (
        ReconciliationStatus.NOT_STARTED,
        ReconciliationStatus.MATCHED,
        ReconciliationStatus.REVIEW_REQUIRED,
        ReconciliationStatus.RESOLVED,
        ReconciliationStatus.FAILED,
    ),
)
def test_direct_case_record_accepts_each_valid_status(
    status: ReconciliationStatus,
) -> None:
    assert record_with_status(status).status == status


def test_case_rejects_matched_with_false_conflicting_field() -> None:
    candidate = record_with_status(ReconciliationStatus.MATCHED).model_copy(deep=True)
    fields = list(candidate.fields)
    fields[0] = FieldReconciliationResult.model_construct(
        field_name=ReconciliationField.LEGAL_NAME,
        observations=observations_for(
            ReconciliationField.LEGAL_NAME, ReconciliationOutcome.CONFLICT
        ),
        outcome=ReconciliationOutcome.MATCH,
        discrepancy_id=None,
    )
    candidate.fields = tuple(fields)
    with pytest.raises(ValidationError):
        ReconciliationCaseRecord.model_validate(candidate)


def test_case_rejects_matched_with_current_open_blocker() -> None:
    review = record_with_status(ReconciliationStatus.REVIEW_REQUIRED)
    review.status = ReconciliationStatus.MATCHED
    with pytest.raises(ValidationError):
        ReconciliationCaseRecord.model_validate(review)


def test_case_rejects_review_with_unreferenced_open_discrepancy() -> None:
    matched = record_with_status(ReconciliationStatus.MATCHED)
    unrelated = discrepancy(ReconciliationField.LEGAL_NAME, ReconciliationOutcome.CONFLICT)
    matched.status = ReconciliationStatus.REVIEW_REQUIRED
    matched.discrepancies = [unrelated]
    with pytest.raises(ValidationError):
        ReconciliationCaseRecord.model_validate(matched)


def test_case_rejects_resolved_with_current_open_blocker() -> None:
    review = record_with_status(ReconciliationStatus.REVIEW_REQUIRED)
    review.status = ReconciliationStatus.RESOLVED
    with pytest.raises(ValidationError):
        ReconciliationCaseRecord.model_validate(review)


def test_case_rejects_duplicate_current_discrepancy_linkage() -> None:
    legal = discrepancy(ReconciliationField.LEGAL_NAME, ReconciliationOutcome.CONFLICT)
    registration = field_result(
        ReconciliationField.REGISTRATION_IDENTIFIER,
        ReconciliationOutcome.CONFLICT,
        legal.discrepancy_id,
    )
    fields = [
        FieldReconciliationResult(
            field_name=ReconciliationField.LEGAL_NAME,
            observations=legal.observations,
            outcome=legal.outcome,
            discrepancy_id=legal.discrepancy_id,
        ),
        registration,
        field_result(ReconciliationField.REGISTERED_ADDRESS, ReconciliationOutcome.MATCH),
        field_result(
            ReconciliationField.COUNTRY_OF_INCORPORATION,
            ReconciliationOutcome.MATCH,
        ),
    ]
    with pytest.raises(ValidationError):
        ReconciliationCaseRecord(
            case_id=uuid4(),
            reconciliation_id=uuid4(),
            status=ReconciliationStatus.REVIEW_REQUIRED,
            source_document_ids=(uuid4(),),
            source_document_event_counts=(1,),
            evidence_fingerprint="b" * 64,
            fields=tuple(fields),
            discrepancies=[legal],
            created_at=NOW,
            updated_at=NOW,
        )


def conflict_context() -> tuple[Any, UUID, ReconciliationCaseRecord, Any, Any]:
    _, zero, _, _, _ = build_system()
    created = zero.create_case("202400001A")
    attach(
        zero,
        created.case_id,
        FieldOverrideIdp({DocumentFieldKey.LEGAL_NAME: "DOCUMENT SELECTED PTE. LTD."}),
    )
    case = zero._cases.get_case(created.case_id)  # noqa: SLF001
    record = zero._reconciliation.get(case_id=created.case_id)  # noqa: SLF001
    assert case is not None and record is not None
    current = record.open_discrepancies[0]
    return zero, created.case_id, record, current, case


def resolve_document_name(
    zero: Any,
    case_id: UUID,
    record: ReconciliationCaseRecord,
    current: ReconciliationDiscrepancy,
) -> ReconciliationCaseRecord:
    return zero._reconciliation.resolve_discrepancy(  # noqa: SLF001
        case_id=case_id,
        discrepancy_id=current.discrepancy_id,
        action=ReconciliationDecisionAction.USE_DOCUMENT_VALUE,
        expected_version=record.version,
        evidence_fingerprint=current.evidence_fingerprint,
    )


def assert_resolution_unchanged(
    zero: Any,
    case_id: UUID,
    original_case: Any,
    original_reconciliation: ReconciliationCaseRecord,
) -> None:
    assert zero._cases.get_case(case_id) == original_case  # noqa: SLF001
    assert (  # noqa: SLF001
        zero._reconciliation.get(case_id=case_id) == original_reconciliation
    )
    current = zero._reconciliation.get(case_id=case_id)  # noqa: SLF001
    assert current is not None
    assert current.open_discrepancies[0].decision is None
    assert not any(
        event.code == "RECONCILIATION_CANONICAL_UPDATED"
        for event in zero._cases.get_case(case_id).events  # type: ignore[union-attr]  # noqa: SLF001
    )


def test_atomicity_prepare_failure_changes_neither_aggregate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    zero, case_id, record, current, original_case = conflict_context()

    def fail_prepare(**_: Any) -> Any:
        raise ValueError("injected preparation failure")

    monkeypatch.setattr(
        zero._reconciliation._cases,  # noqa: SLF001
        "prepare_reconciled_value",
        fail_prepare,
    )
    with pytest.raises(ReconciliationRequestError):
        resolve_document_name(zero, case_id, record, current)
    assert_resolution_unchanged(zero, case_id, original_case, record)


def test_atomicity_decision_validation_failure_changes_neither_aggregate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    zero, case_id, record, current, original_case = conflict_context()

    def fail_validation(_: ReconciliationCaseRecord) -> ReconciliationCaseRecord:
        raise ValueError("injected candidate validation failure")

    monkeypatch.setattr(
        zero._reconciliation,  # noqa: SLF001
        "_validate_resolution_candidate",
        fail_validation,
    )
    with pytest.raises(ReconciliationInfrastructureError):
        resolve_document_name(zero, case_id, record, current)
    assert_resolution_unchanged(zero, case_id, original_case, record)


def test_atomicity_conflict_before_commit_changes_neither_aggregate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    zero, case_id, record, current, original_case = conflict_context()

    def conflict(*_: Any, **__: Any) -> Any:
        raise ReconciliationRepositoryConflictError

    monkeypatch.setattr(
        zero._reconciliation._repository,  # noqa: SLF001
        "transaction_prepare",
        conflict,
    )
    with pytest.raises(ReconciliationRequestError) as caught:
        resolve_document_name(zero, case_id, record, current)
    assert caught.value.code == "RECONCILIATION_CONFLICT"
    assert_resolution_unchanged(zero, case_id, original_case, record)


@pytest.mark.parametrize(
    "fault_stage",
    (
        "before_onboarding_commit",
        "before_reconciliation_commit",
        "after_reconciliation_commit",
    ),
)
def test_atomicity_commit_fault_restores_both_aggregates(fault_stage: str) -> None:
    zero, case_id, record, current, original_case = conflict_context()

    def fail(stage: str) -> None:
        if stage == fault_stage:
            raise RuntimeError("injected process-local persistence failure")

    zero._reconciliation._unit_of_work._fault = fail  # noqa: SLF001
    with pytest.raises(ReconciliationInfrastructureError) as caught:
        resolve_document_name(zero, case_id, record, current)
    assert caught.value.code == "RECONCILIATION_COMMIT_FAILED"
    assert_resolution_unchanged(zero, case_id, original_case, record)


def test_atomic_success_commits_canonical_and_decision_together() -> None:
    zero, case_id, record, current, original_case = conflict_context()
    resolved = resolve_document_name(zero, case_id, record, current)
    case = zero._cases.get_case(case_id)  # noqa: SLF001
    assert case is not None and case.entity is not None
    assert original_case.entity.legal_name != case.entity.legal_name
    assert case.entity.legal_name == "DOCUMENT SELECTED PTE. LTD."
    selected = next(
        item for item in resolved.discrepancies if item.discrepancy_id == current.discrepancy_id
    )
    assert selected.status == DiscrepancyStatus.RESOLVED
    assert selected.decision is not None
    assert selected.observations == current.observations
    assert any(event.code == "RECONCILIATION_CANONICAL_UPDATED" for event in case.events)


@pytest.mark.parametrize(
    "field",
    (
        ReconciliationField.REGISTRATION_IDENTIFIER,
        ReconciliationField.REGISTERED_ADDRESS,
        ReconciliationField.COUNTRY_OF_INCORPORATION,
    ),
)
def test_canonical_prepare_remains_legal_name_only(field: ReconciliationField) -> None:
    zero, case_id, _, _, original_case = conflict_context()
    with pytest.raises(ValueError):
        zero._cases.prepare_reconciled_value(  # noqa: SLF001
            case_id=case_id,
            field_name=field,
            selected_value="UNSUPPORTED",
            expected_entity_fingerprint=zero._cases.canonical_entity_fingerprint(case_id),  # noqa: SLF001
        )
    assert zero._cases.get_case(case_id) == original_case  # noqa: SLF001


def test_repository_rejects_original_false_matched_attack() -> None:
    zero, case_id, record, current, _ = conflict_context()
    forged = record.model_copy(deep=True)
    forged.fields = tuple(
        FieldReconciliationResult.model_construct(
            field_name=item.field_name,
            observations=item.observations,
            outcome=(
                ReconciliationOutcome.MATCH
                if item.discrepancy_id == current.discrepancy_id
                else item.outcome
            ),
            discrepancy_id=(
                None if item.discrepancy_id == current.discrepancy_id else item.discrepancy_id
            ),
        )
        for item in forged.fields
    )
    target = next(
        item for item in forged.discrepancies if item.discrepancy_id == current.discrepancy_id
    )
    target.status = DiscrepancyStatus.CANCELLED
    forged.status = ReconciliationStatus.MATCHED
    with pytest.raises(ValidationError):
        zero._reconciliation._repository.save(  # noqa: SLF001
            forged, expected_version=record.version
        )
    assert not zero._reconciliation.is_currently_cleared(case_id=case_id)  # noqa: SLF001
    assert zero._reconciliation.get(case_id=case_id) == record  # noqa: SLF001


def test_stale_duplicate_after_replacement_is_rejected_by_service() -> None:
    zero, case_id, record, current, _ = conflict_context()
    resolved = zero._reconciliation.resolve_discrepancy(  # noqa: SLF001
        case_id=case_id,
        discrepancy_id=current.discrepancy_id,
        action=ReconciliationDecisionAction.KEEP_REGISTRY_VALUE,
        expected_version=record.version,
        evidence_fingerprint=current.evidence_fingerprint,
    )
    document = zero._documents.list_documents(case_id=case_id)[0]  # noqa: SLF001
    zero.replace_document(
        case_id=case_id,
        document_id=document.document_id,
        expected_document_event_count=len(document.events),
        display_name="replacement-conflict.pdf",
        content_type="application/pdf",
        content=(
            Path(__file__).parent / "fixtures" / "uat" / "clean-company-profile.pdf"
        ).read_bytes(),
        idp_provider=FieldOverrideIdp({DocumentFieldKey.LEGAL_NAME: "NEW CONFLICT PTE. LTD."}),
    )
    new_current = zero._reconciliation.get(case_id=case_id)  # noqa: SLF001
    assert new_current is not None and new_current.status == ReconciliationStatus.REVIEW_REQUIRED
    with pytest.raises(ReconciliationRequestError) as caught:
        zero._reconciliation.resolve_discrepancy(  # noqa: SLF001
            case_id=case_id,
            discrepancy_id=current.discrepancy_id,
            action=ReconciliationDecisionAction.KEEP_REGISTRY_VALUE,
            expected_version=record.version,
            evidence_fingerprint=current.evidence_fingerprint,
        )
    assert caught.value.code == "RECONCILIATION_STALE"
    assert zero._reconciliation.get(case_id=case_id) == new_current  # noqa: SLF001
    assert resolved.version < new_current.version


def test_low_confidence_conflict_has_one_unverifiable_blocker_and_no_action() -> None:
    client, zero, _, target, _ = build_system()
    created = zero.create_case("202400001A")
    paused = attach(
        zero,
        created.case_id,
        FieldOverrideIdp(
            {DocumentFieldKey.LEGAL_NAME: "OTHER NAME PTE. LTD."},
            confidence={DocumentFieldKey.LEGAL_NAME: 0.4},
        ),
    )
    record = zero._reconciliation.get(case_id=created.case_id)  # noqa: SLF001
    assert paused.status == "WAITING_FOR_REVIEW"
    assert record is not None
    legal = [
        item
        for item in record.open_discrepancies
        if item.field_name == ReconciliationField.LEGAL_NAME
    ]
    assert len(legal) == 1
    assert legal[0].outcome == ReconciliationOutcome.UNVERIFIABLE
    assert legal[0].allowed_actions == ()
    response = client.get(f"/api/clm/zero-touch/cases/{created.case_id}")
    api_legal = [
        item
        for item in response.json()["reconciliation"]["discrepancies"]
        if item["field_name"] == "legal_name" and item["status"] == "OPEN"
    ]
    assert len(api_legal) == 1
    assert api_legal[0]["outcome"] == "UNVERIFIABLE"
    assert api_legal[0]["allowed_actions"] == []
    assert zero._ownership.get(case_id=created.case_id) is None  # noqa: SLF001
    assert target.calls == []
