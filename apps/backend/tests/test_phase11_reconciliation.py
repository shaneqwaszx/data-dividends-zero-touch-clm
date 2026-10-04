"""Focused Phase 11 source-neutral reconciliation and resume tests."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from test_zero_touch_orchestration import PDF, build_system

from app.connectors.mock_idp import MockIdpProvider, MockIdpScenario
from app.connectors.mock_ownership import MockOwnershipProvider
from app.domain.access import TeamId
from app.domain.documents import DocumentFieldKey, ReviewDecision
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
    derive_reconciliation_outcome,
)
from app.domain.zero_touch import ExceptionResolutionAction
from app.services.reconciliation_errors import ReconciliationRequestError

NOW = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)


class FieldOverrideIdp(MockIdpProvider):
    def __init__(
        self,
        values: dict[DocumentFieldKey, str | None],
        *,
        confidence: dict[DocumentFieldKey, float] | None = None,
    ) -> None:
        super().__init__(MockIdpScenario.ALL_FIELDS_MATCH)
        self._values = values
        self._confidence = confidence or {}
        self.calls = 0

    def process(self, document: Any) -> Any:
        self.calls += 1
        result = super().process(document)
        return result.model_copy(
            update={
                "fields": [
                    field.model_copy(
                        update={
                            "value": self._values.get(field.field_key, field.value),
                            "confidence": self._confidence.get(field.field_key, field.confidence),
                        }
                    )
                    for field in result.fields
                ]
            }
        )


def observation(
    *,
    field: ReconciliationField = ReconciliationField.LEGAL_NAME,
    source: ReconciliationSourceKind = ReconciliationSourceKind.REGISTRY,
    value: str | None = "MERLION PTE. LTD.",
    validity: ObservationValidity = ObservationValidity.VALID,
) -> ReconciliationObservation:
    return ReconciliationObservation(
        observation_id=uuid4(),
        field_name=field,
        raw_value=value,
        normalized_value=value,
        source_kind=source,
        source_system="ACRA" if source == ReconciliationSourceKind.REGISTRY else "LOCAL_IDP",
        environment="MOCK",
        observed_at=NOW,
        evidence_reference="evidence:one",
        confidence=0.97 if source == ReconciliationSourceKind.DOCUMENT_IDP else None,
        validity=validity,
    )


def attach(
    zero: Any,
    case_id: UUID,
    provider: FieldOverrideIdp,
) -> Any:
    return zero.attach_document(
        case_id=case_id,
        display_name="phase11.pdf",
        content_type="application/pdf",
        content=PDF,
        idp_provider=provider,
        ownership_provider=MockOwnershipProvider(),
    )


def current_discrepancy(record: ReconciliationCaseRecord, field: ReconciliationField) -> Any:
    return next(
        item
        for item in record.discrepancies
        if item.field_name == field and item.status == DiscrepancyStatus.OPEN
    )


def test_observation_requires_value_shape_and_document_only_confidence() -> None:
    with pytest.raises(ValidationError):
        observation(value=None, validity=ObservationValidity.VALID)
    payload = observation().model_dump()
    payload["confidence"] = 0.9
    with pytest.raises(ValidationError):
        ReconciliationObservation.model_validate(payload)


def test_observation_rejects_raw_provider_url_reference() -> None:
    payload = observation().model_dump()
    payload["evidence_reference"] = "https://provider.invalid/raw?id=1"
    with pytest.raises(ValidationError):
        ReconciliationObservation.model_validate(payload)


def test_field_result_direct_match_and_conflict_shapes() -> None:
    registry = observation()
    document = observation(source=ReconciliationSourceKind.DOCUMENT_IDP)
    matched = FieldReconciliationResult(
        field_name=ReconciliationField.LEGAL_NAME,
        observations=(registry, document),
        outcome=ReconciliationOutcome.MATCH,
    )
    assert matched.discrepancy_id is None
    with pytest.raises(ValidationError):
        FieldReconciliationResult(
            field_name=ReconciliationField.LEGAL_NAME,
            observations=(registry, document),
            outcome=ReconciliationOutcome.CONFLICT,
        )


def test_registry_only_outcome_is_bounded_to_optional_registered_address() -> None:
    registry = observation(
        field=ReconciliationField.REGISTERED_ADDRESS,
        value="18 INNOVATION WAY, 018956, SG",
    )
    document = observation(
        field=ReconciliationField.REGISTERED_ADDRESS,
        source=ReconciliationSourceKind.DOCUMENT_IDP,
        value=None,
        validity=ObservationValidity.MISSING,
    )

    assert derive_reconciliation_outcome(
        ReconciliationField.REGISTERED_ADDRESS,
        (registry, document),
        document_required=False,
    ) == ReconciliationOutcome.REGISTRY_ONLY
    result = FieldReconciliationResult(
        field_name=ReconciliationField.REGISTERED_ADDRESS,
        observations=(registry, document),
        outcome=ReconciliationOutcome.REGISTRY_ONLY,
        document_required=False,
    )
    assert result.discrepancy_id is None

    with pytest.raises(ValidationError):
        FieldReconciliationResult(
            field_name=ReconciliationField.LEGAL_NAME,
            observations=(
                observation(),
                observation(
                    source=ReconciliationSourceKind.DOCUMENT_IDP,
                    value=None,
                    validity=ObservationValidity.MISSING,
                ),
            ),
            outcome=ReconciliationOutcome.REGISTRY_ONLY,
            document_required=False,
        )


def test_discrepancy_rejects_match_and_duplicate_observation_ids() -> None:
    registry = observation()
    document = observation(source=ReconciliationSourceKind.DOCUMENT_IDP)
    with pytest.raises(ValidationError):
        ReconciliationDiscrepancy(
            discrepancy_id=uuid4(),
            field_name=ReconciliationField.LEGAL_NAME,
            outcome=ReconciliationOutcome.MATCH,
            observations=(registry, document),
            created_at=NOW,
            evidence_fingerprint="a" * 64,
        )
    with pytest.raises(ValidationError):
        ReconciliationDiscrepancy(
            discrepancy_id=uuid4(),
            field_name=ReconciliationField.LEGAL_NAME,
            outcome=ReconciliationOutcome.CONFLICT,
            observations=(registry, registry),
            created_at=NOW,
            evidence_fingerprint="a" * 64,
        )


def test_decision_cannot_select_unknown_observation() -> None:
    registry = observation()
    document = observation(source=ReconciliationSourceKind.DOCUMENT_IDP, value="OTHER")
    with pytest.raises(ValidationError):
        ReconciliationDiscrepancy(
            discrepancy_id=uuid4(),
            field_name=ReconciliationField.LEGAL_NAME,
            outcome=ReconciliationOutcome.CONFLICT,
            observations=(registry, document),
            created_at=NOW,
            status=DiscrepancyStatus.RESOLVED,
            allowed_actions=(ReconciliationDecisionAction.KEEP_REGISTRY_VALUE,),
            evidence_fingerprint="a" * 64,
            decision=ReconciliationDecision(
                action=ReconciliationDecisionAction.KEEP_REGISTRY_VALUE,
                selected_observation_id=uuid4(),
                selected_value=registry.normalized_value or "missing",
                decided_at=NOW,
                reconciliation_version=1,
                evidence_fingerprint="a" * 64,
            ),
        )


def test_case_record_cannot_be_resolved_with_open_blocker_or_duplicate_ids() -> None:
    _, zero, _, _, _ = build_system()
    created = zero.create_case("202400001A")
    attach(
        zero,
        created.case_id,
        FieldOverrideIdp({DocumentFieldKey.LEGAL_NAME: "DIFFERENT PTE. LTD."}),
    )
    record = zero._reconciliation.get(case_id=created.case_id)  # noqa: SLF001
    assert record is not None
    common = {
        "case_id": record.case_id,
        "reconciliation_id": record.reconciliation_id,
        "version": record.version,
        "source_document_ids": record.source_document_ids,
        "source_document_event_counts": record.source_document_event_counts,
        "evidence_fingerprint": record.evidence_fingerprint,
        "fields": record.fields,
        "error": None,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }
    with pytest.raises(ValidationError):
        ReconciliationCaseRecord(
            **common,
            status=ReconciliationStatus.RESOLVED,
            discrepancies=record.discrepancies,
        )
    with pytest.raises(ValidationError):
        ReconciliationCaseRecord(
            **common,
            status=ReconciliationStatus.REVIEW_REQUIRED,
            discrepancies=[record.discrepancies[0], record.discrepancies[0]],
        )
    mutated = record.model_copy(deep=True)
    mutated.status = ReconciliationStatus.RESOLVED
    with pytest.raises(ValidationError):
        zero._reconciliation._repository.save(  # noqa: SLF001
            mutated,
            expected_version=record.version,
        )


def test_all_fields_match_and_formatting_only_legal_name_match() -> None:
    _, zero, _, target, _ = build_system()
    created = zero.create_case("202400001A")
    result = attach(
        zero,
        created.case_id,
        FieldOverrideIdp({DocumentFieldKey.LEGAL_NAME: "  merlion   circular labs pte. ltd.  "}),
    )
    reconciliation = zero._reconciliation.get(case_id=created.case_id)  # noqa: SLF001
    assert result.status == "COMPLETED"
    assert reconciliation is not None and reconciliation.status == "MATCHED"
    assert [field.outcome for field in reconciliation.fields] == [ReconciliationOutcome.MATCH] * 4
    assert target.calls == ['search', 'search', 'shell', 'policy', 'amend', 'search']


def test_safe_review_correction_is_effective_and_preserves_original_evidence() -> None:
    _, zero, documents, _, _ = build_system()
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)
    document = documents.create_document(
        case_id=created.case_id,
        display_name="corrected.pdf",
        content_type="application/pdf",
        content=PDF,
        provider=MockIdpProvider(MockIdpScenario.FIELD_MISMATCH),
    )
    original = next(
        item.original_extracted_value
        for item in document.fields
        if item.field_key == DocumentFieldKey.LEGAL_NAME
    )
    for field in document.fields:
        document = documents.review_field(
            case_id=created.case_id,
            document_id=document.document_id,
            field_key=field.field_key,
            decision=(
                ReviewDecision.CORRECTED
                if field.field_key == DocumentFieldKey.LEGAL_NAME
                else ReviewDecision.ACCEPTED
            ),
            corrected_value=(
                "MERLION CIRCULAR LABS PTE. LTD."
                if field.field_key == DocumentFieldKey.LEGAL_NAME
                else None
            ),
        )

    reconciliation = zero._reconciliation.reconcile_current(  # noqa: SLF001
        case_id=created.case_id
    )
    legal = next(item for item in reconciliation.fields if item.field_name == "legal_name")
    reviewed_observation = next(
        item for item in legal.observations if item.source_kind == "DOCUMENT_IDP"
    )
    stored = documents.get_document(case_id=created.case_id, document_id=document.document_id)
    assert reconciliation.status == "MATCHED"
    assert reviewed_observation.raw_value == "MERLION CIRCULAR LABS PTE. LTD."
    assert reviewed_observation.source_system == "HUMAN_REVIEW"
    assert reviewed_observation.evidence_reference == "DOCUMENT_REVIEW_CORRECTION"
    assert reviewed_observation.confidence is None
    assert stored is not None
    assert (
        next(
            item.original_extracted_value
            for item in stored.fields
            if item.field_key == DocumentFieldKey.LEGAL_NAME
        )
        == original
    )


@pytest.mark.parametrize(
    ("scenario", "key", "decision", "expected_outcome"),
    [
        (
            MockIdpScenario.ALL_FIELDS_MATCH,
            DocumentFieldKey.LEGAL_NAME,
            ReviewDecision.REJECTED,
            ReconciliationOutcome.MISSING_IN_SOURCE,
        ),
        (
            MockIdpScenario.LOW_CONFIDENCE,
            DocumentFieldKey.REGISTERED_ADDRESS,
            ReviewDecision.CORRECTED,
            ReconciliationOutcome.UNVERIFIABLE,
        ),
    ],
)
def test_rejected_missing_and_low_confidence_reviews_remain_blocking(
    scenario: MockIdpScenario,
    key: DocumentFieldKey,
    decision: ReviewDecision,
    expected_outcome: ReconciliationOutcome,
) -> None:
    _, zero, documents, target, _ = build_system()
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)
    document = documents.create_document(
        case_id=created.case_id,
        display_name="blocked.pdf",
        content_type="application/pdf",
        content=PDF,
        provider=MockIdpProvider(scenario),
    )
    for field in document.fields:
        field_decision = decision if field.field_key == key else ReviewDecision.ACCEPTED
        document = documents.review_field(
            case_id=created.case_id,
            document_id=document.document_id,
            field_key=field.field_key,
            decision=field_decision,
            corrected_value=(
                "18 INNOVATION WAY, #04-01, 018956, SG"
                if field_decision == ReviewDecision.CORRECTED
                else None
            ),
        )

    reconciliation = zero._reconciliation.reconcile_current(  # noqa: SLF001
        case_id=created.case_id
    )
    discrepancy = current_discrepancy(reconciliation, ReconciliationField(key.value))
    assert reconciliation.status == "REVIEW_REQUIRED"
    assert discrepancy.outcome == expected_outcome
    assert target.calls == ["search"]


@pytest.mark.parametrize(
    ("field_key", "value", "field_name"),
    [
        (DocumentFieldKey.LEGAL_NAME, "DIFFERENT PTE. LTD.", ReconciliationField.LEGAL_NAME),
        (
            DocumentFieldKey.REGISTRATION_NUMBER,
            "202499999Z",
            ReconciliationField.REGISTRATION_IDENTIFIER,
        ),
        (
            DocumentFieldKey.COUNTRY_OF_INCORPORATION,
            "AU",
            ReconciliationField.COUNTRY_OF_INCORPORATION,
        ),
        (
            DocumentFieldKey.REGISTERED_ADDRESS,
            "99 OTHER ROAD, 999999, SG",
            ReconciliationField.REGISTERED_ADDRESS,
        ),
    ],
)
def test_each_active_field_conflict_stops_before_ownership_and_target(
    field_key: DocumentFieldKey,
    value: str,
    field_name: ReconciliationField,
) -> None:
    _, zero, _, target, _ = build_system()
    created = zero.create_case("202400001A")
    result = attach(zero, created.case_id, FieldOverrideIdp({field_key: value}))
    reconciliation = zero._reconciliation.get(case_id=created.case_id)  # noqa: SLF001
    assert result.status == "WAITING_FOR_REVIEW"
    assert result.current_stage == "DOCUMENT"
    assert zero._ownership.get(case_id=created.case_id) is None  # noqa: SLF001
    assert target.calls == ["search"]
    assert reconciliation is not None
    field = next(item for item in reconciliation.fields if item.field_name == field_name)
    assert field.outcome == ReconciliationOutcome.CONFLICT


def test_registry_only_invalid_and_unverifiable_are_distinct() -> None:
    scenarios = (
        (
            {DocumentFieldKey.REGISTERED_ADDRESS: None},
            {},
            ReconciliationField.REGISTERED_ADDRESS,
            ReconciliationOutcome.REGISTRY_ONLY,
            ["search", "shell", "policy", "amend"],
        ),
        (
            {DocumentFieldKey.COUNTRY_OF_INCORPORATION: "SINGAPORE"},
            {},
            ReconciliationField.COUNTRY_OF_INCORPORATION,
            ReconciliationOutcome.INVALID,
            ["search"],
        ),
        (
            {},
            {DocumentFieldKey.LEGAL_NAME: 0.4},
            ReconciliationField.LEGAL_NAME,
            ReconciliationOutcome.UNVERIFIABLE,
            ["search"],
        ),
    )
    for values, confidence, field_name, expected, expected_calls in scenarios:
        _, zero, _, target, _ = build_system()
        created = zero.create_case("202400001A")
        attach(
            zero,
            created.case_id,
            FieldOverrideIdp(values, confidence=confidence),
        )
        reconciliation = zero._reconciliation.get(case_id=created.case_id)  # noqa: SLF001
        assert reconciliation is not None
        assert (
            next(item for item in reconciliation.fields if item.field_name == field_name).outcome
            == expected
        )
        assert target.calls == (
            ['search', 'search', 'shell', 'policy', 'amend', 'search']
            if expected_calls == ['search', 'shell', 'policy', 'amend']
            else expected_calls
        )


def test_multiple_conflicts_resolve_one_stays_blocked_then_all_resume_once() -> None:
    _, zero, _, target, _ = build_system()
    created = zero.create_case("202400001A")
    paused = attach(
        zero,
        created.case_id,
        FieldOverrideIdp(
            {
                DocumentFieldKey.LEGAL_NAME: "DIFFERENT PTE. LTD.",
                DocumentFieldKey.REGISTERED_ADDRESS: "99 OTHER ROAD, 999999, SG",
            }
        ),
    )
    record = zero._reconciliation.get(case_id=created.case_id)  # noqa: SLF001
    assert record is not None and len(record.open_discrepancies) == 2
    first = current_discrepancy(record, ReconciliationField.LEGAL_NAME)
    still_blocked = zero.resolve_reconciliation_discrepancy(
        case_id=created.case_id,
        discrepancy_id=first.discrepancy_id,
        action=ReconciliationDecisionAction.USE_DOCUMENT_VALUE,
        expected_automation_version=paused.version,
        expected_reconciliation_version=record.version,
        evidence_fingerprint=first.evidence_fingerprint,
    )
    assert still_blocked.status == "WAITING_FOR_REVIEW"
    assert target.calls == ["search"]
    record = zero._reconciliation.get(case_id=created.case_id)  # noqa: SLF001
    assert record is not None and len(record.open_discrepancies) == 1
    second = record.open_discrepancies[0]
    active = next(
        item
        for item in still_blocked.active_exceptions
        if item.exception_id == second.discrepancy_id
    )
    completed = zero.resolve_exception(
        case_id=created.case_id,
        exception_id=second.discrepancy_id,
        action=ExceptionResolutionAction.KEEP_REGISTRY_VALUE,
        expected_automation_version=still_blocked.version,
        evidence_version=active.evidence_version,
    )
    assert completed.status == "COMPLETED"
    assert target.calls == ['search', 'search', 'search', 'shell', 'policy', 'amend', 'search']
    version = completed.version
    assert zero.start(case_id=created.case_id).version == version
    assert target.calls == ['search', 'search', 'search', 'shell', 'policy', 'amend', 'search']


def test_use_document_legal_name_updates_canonical_only_through_service() -> None:
    _, zero, _, target, _ = build_system()
    created = zero.create_case("202400001A")
    paused = attach(
        zero,
        created.case_id,
        FieldOverrideIdp({DocumentFieldKey.LEGAL_NAME: "DOCUMENT SELECTED PTE. LTD."}),
    )
    record = zero._reconciliation.get(case_id=created.case_id)  # noqa: SLF001
    assert record is not None
    discrepancy = current_discrepancy(record, ReconciliationField.LEGAL_NAME)
    assert discrepancy.allowed_actions == (
        ReconciliationDecisionAction.KEEP_REGISTRY_VALUE,
        ReconciliationDecisionAction.USE_DOCUMENT_VALUE,
    )
    completed = zero.resolve_reconciliation_discrepancy(
        case_id=created.case_id,
        discrepancy_id=discrepancy.discrepancy_id,
        action=ReconciliationDecisionAction.USE_DOCUMENT_VALUE,
        expected_automation_version=paused.version,
        expected_reconciliation_version=record.version,
        evidence_fingerprint=discrepancy.evidence_fingerprint,
    )
    case = zero._cases.get_case(created.case_id)  # noqa: SLF001
    record = zero._reconciliation.get(case_id=created.case_id)  # noqa: SLF001
    assert completed.status == "COMPLETED"
    assert case is not None and case.entity is not None and case.registry_acquisition is not None
    assert case.entity.legal_name == "DOCUMENT SELECTED PTE. LTD."
    assert case.registry_acquisition.entity_profile.legal_name == (
        "MERLION CIRCULAR LABS PTE. LTD."
    )
    assert record is not None and record.status == "RESOLVED"
    assert len(record.discrepancies[0].observations) == 2
    assert record.discrepancies[0].decision is not None
    assert record.discrepancies[0].decision.action == "USE_DOCUMENT_VALUE"
    assert target.calls == ['search', 'search', 'search', 'shell', 'policy', 'amend', 'search']


def test_unadvertised_use_document_action_is_rejected_for_address() -> None:
    _, zero, _, target, _ = build_system()
    created = zero.create_case("202400001A")
    attach(
        zero,
        created.case_id,
        FieldOverrideIdp({DocumentFieldKey.REGISTERED_ADDRESS: "99 OTHER ROAD, 999999, SG"}),
    )
    record = zero._reconciliation.get(case_id=created.case_id)  # noqa: SLF001
    assert record is not None
    discrepancy = current_discrepancy(record, ReconciliationField.REGISTERED_ADDRESS)
    with pytest.raises(ReconciliationRequestError) as caught:
        zero._reconciliation.resolve_discrepancy(  # noqa: SLF001
            case_id=created.case_id,
            discrepancy_id=discrepancy.discrepancy_id,
            action=ReconciliationDecisionAction.USE_DOCUMENT_VALUE,
            expected_version=record.version,
            evidence_fingerprint=discrepancy.evidence_fingerprint,
        )
    assert caught.value.code == "RECONCILIATION_ACTION_NOT_ALLOWED"
    assert target.calls == ["search"]


def test_stale_version_and_fingerprint_are_rejected() -> None:
    _, zero, _, target, _ = build_system()
    created = zero.create_case("202400001A")
    attach(
        zero,
        created.case_id,
        FieldOverrideIdp({DocumentFieldKey.LEGAL_NAME: "DIFFERENT PTE. LTD."}),
    )
    record = zero._reconciliation.get(case_id=created.case_id)  # noqa: SLF001
    assert record is not None
    discrepancy = record.open_discrepancies[0]
    with pytest.raises(ReconciliationRequestError) as caught:
        zero._reconciliation.resolve_discrepancy(  # noqa: SLF001
            case_id=created.case_id,
            discrepancy_id=discrepancy.discrepancy_id,
            action=ReconciliationDecisionAction.KEEP_REGISTRY_VALUE,
            expected_version=record.version + 1,
            evidence_fingerprint=discrepancy.evidence_fingerprint,
        )
    assert caught.value.code == "RECONCILIATION_STALE"
    with pytest.raises(ReconciliationRequestError) as caught:
        zero._reconciliation.resolve_discrepancy(  # noqa: SLF001
            case_id=created.case_id,
            discrepancy_id=discrepancy.discrepancy_id,
            action=ReconciliationDecisionAction.KEEP_REGISTRY_VALUE,
            expected_version=record.version,
            evidence_fingerprint="0" * 64,
        )
    assert caught.value.code == "RECONCILIATION_STALE"
    assert target.calls == ["search"]


def test_duplicate_identical_reconciliation_decision_is_idempotent() -> None:
    _, zero, _, _, _ = build_system()
    created = zero.create_case("202400001A")
    paused = attach(
        zero,
        created.case_id,
        FieldOverrideIdp({DocumentFieldKey.LEGAL_NAME: "DIFFERENT PTE. LTD."}),
    )
    record = zero._reconciliation.get(case_id=created.case_id)  # noqa: SLF001
    assert record is not None
    discrepancy = record.open_discrepancies[0]
    zero.resolve_reconciliation_discrepancy(
        case_id=created.case_id,
        discrepancy_id=discrepancy.discrepancy_id,
        action=ReconciliationDecisionAction.KEEP_REGISTRY_VALUE,
        expected_automation_version=paused.version,
        expected_reconciliation_version=record.version,
        evidence_fingerprint=discrepancy.evidence_fingerprint,
    )
    current = zero._reconciliation.get(case_id=created.case_id)  # noqa: SLF001
    assert current is not None
    duplicate = zero._reconciliation.resolve_discrepancy(  # noqa: SLF001
        case_id=created.case_id,
        discrepancy_id=discrepancy.discrepancy_id,
        action=ReconciliationDecisionAction.KEEP_REGISTRY_VALUE,
        expected_version=record.version,
        evidence_fingerprint=discrepancy.evidence_fingerprint,
    )
    assert duplicate.version == current.version
    assert len([item for item in duplicate.discrepancies if item.decision is not None]) == 1


def test_repeated_reads_do_not_rerun_idp_or_target() -> None:
    client, zero, _, target, _ = build_system()
    provider = FieldOverrideIdp({DocumentFieldKey.LEGAL_NAME: "DIFFERENT PTE. LTD."})
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)
    attach(zero, created.case_id, provider)
    for _ in range(3):
        response = client.get(f"/api/clm/zero-touch/cases/{created.case_id}")
        assert response.status_code == 200
    assert provider.calls == 1
    assert zero._ownership.get(case_id=created.case_id) is None  # noqa: SLF001
    assert target.calls == ["search"]


def test_replacement_document_cancels_old_discrepancy_and_resumes() -> None:
    _, zero, documents, target, _ = build_system()
    created = zero.create_case("202400001A")
    paused = attach(
        zero,
        created.case_id,
        FieldOverrideIdp({DocumentFieldKey.LEGAL_NAME: "DIFFERENT PTE. LTD."}),
    )
    current_document = documents.list_documents(case_id=created.case_id)[0]
    completed = zero.replace_document(
        case_id=created.case_id,
        document_id=current_document.document_id,
        expected_document_event_count=len(current_document.events),
        display_name="replacement.pdf",
        content_type="application/pdf",
        content=PDF,
        idp_provider=FieldOverrideIdp({}),
    )
    reconciliation = zero._reconciliation.get(case_id=created.case_id)  # noqa: SLF001
    assert paused.status == "WAITING_FOR_REVIEW"
    assert completed.status == "COMPLETED"
    assert reconciliation is not None and reconciliation.status == "MATCHED"
    assert any(item.status == "CANCELLED" for item in reconciliation.discrepancies)
    assert target.calls == ['search', 'search', 'shell', 'policy', 'amend', 'search']


def test_api_exposes_normalized_safe_state_and_explicit_resolution_endpoint() -> None:
    client, zero, _, target, _ = build_system()
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)
    paused = attach(
        zero,
        created.case_id,
        FieldOverrideIdp({DocumentFieldKey.LEGAL_NAME: "DIFFERENT PTE. LTD."}),
    )
    response = client.get(f"/api/clm/zero-touch/cases/{created.case_id}")
    payload = response.json()
    discrepancy = payload["reconciliation"]["discrepancies"][0]
    serialized = response.text
    assert response.status_code == 200
    assert "raw_value" not in serialized
    assert "registry_source_link" not in serialized
    assert "authoritative_evidence_digest" not in serialized
    assert discrepancy["allowed_actions"] == [
        "KEEP_REGISTRY_VALUE",
        "USE_DOCUMENT_VALUE",
    ]
    resolved = client.post(
        (
            f"/api/clm/zero-touch/cases/{created.case_id}/reconciliation/"
            f"discrepancies/{discrepancy['discrepancy_id']}/resolve"
        ),
        json={
            "action": "KEEP_REGISTRY_VALUE",
            "expected_automation_version": paused.version,
            "expected_reconciliation_version": payload["reconciliation"]["version"],
            "evidence_fingerprint": discrepancy["evidence_fingerprint"],
        },
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "COMPLETED"
    assert (
        resolved.json()["reconciliation"]["discrepancies"][0]["decision"]["action"]
        == "KEEP_REGISTRY_VALUE"
    )
    assert target.calls == ['search', 'search', 'shell', 'policy', 'amend', 'search']
