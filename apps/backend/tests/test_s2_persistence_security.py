"""Synthetic acceptance of Session 2 durable evidence and creator authorization."""

from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from typing import Any
from uuid import UUID, uuid4

import pytest
from phase13_test_clients import RawTestClient
from phase13_test_credentials import TEST_PASSWORD, build_test_authentication_service
from pydantic import ValidationError
from s2_legacy_schema_fixtures import omit_session2_fields
from test_manual_ownership_evidence import (
    FIXED_TIME,
    Cases,
    make_case,
    make_declaration,
    make_document,
)
from test_s2_ownership_intelligence import (
    DocumentReader,
    _declaration_for_current,
    official_garden_case,
    proposal,
    service_for,
)
from test_slice_a_legacy_compatibility import historical_raw
from test_zero_touch_orchestration import PDF, build_system

from app.api_auth import SESSION_COOKIE_NAME
from app.config import Settings
from app.connectors.idp import IdpDocumentInput, IdpProviderMetadata, IdpSourceResult
from app.connectors.mock_idp import MockIdpProvider
from app.connectors.registry_ownership import RegistryAcquisitionOwnershipProvider
from app.domain.access import SYNTHETIC_USER_PROFILES, TeamId
from app.domain.documents import (
    ComparisonStatus,
    DocumentFieldCandidate,
    DocumentFieldKey,
    DocumentPageEvidence,
    ExtractedField,
    ExtractionMethod,
    ExtractionQuality,
    FieldProvenance,
    IdpEnvironment,
    OwnershipObservationValues,
)
from app.domain.models import RegistryAcquisitionIssue
from app.domain.reconciliation import (
    ObservationValidity,
    ReconciliationField,
    ReconciliationObservation,
    ReconciliationSourceKind,
)
from app.main import create_app
from app.persistence.errors import PersistenceDataInvalidError
from app.persistence.models import DurableCaseSnapshot, reject_session2_legacy_fields
from app.persistence.mongo_case_store import MongoCaseStore
from app.services.admin_repository import InMemoryPolicyRepository
from app.services.authentication import generate_scrypt_password_hash
from app.services.document_errors import DocumentProcessingInfrastructureError
from app.services.manual_ownership_evidence import ManualOwnershipEvidenceProvider
from app.services.ownership_errors import OwnershipRequestError
from app.services.policy_management import PolicyManagementService
from app.services.repository import (
    InMemoryOnboardingCaseRepository,
    OnboardingCaseRepositoryConflictError,
)


def session2_snapshot() -> DurableCaseSnapshot:
    """Retain proposals, extraction metadata and two real service-authored decisions."""
    case = make_case().model_copy(
        update={"created_by_actor_id": "maya-lim", "team_id": TeamId.TEAM_A}
    )
    document = make_document()
    metadata = {
        "extraction_method": "LOCAL_TESSERACT_OCR",
        "extraction_quality": "HIGH",
        "score_kind": "DETERMINISTIC_EVIDENCE_SCORE",
        "score_formula": "LABEL_SCORE_TIMES_OCR_MEAN_OVER_100",
        "raw_ocr_mean_confidence": 94.0,
        "raw_ocr_word_count": 24,
    }
    observed = proposal(
        document, page_number=2, source_reference="PAGE_2_ROW_3",
        explicit_percentage="70", share_count="700", explicit_total_shares="1000",
        share_class="Ordinary", as_of_date=FIXED_TIME.date(), **metadata,
    )
    candidate = DocumentFieldCandidate(
        value=case.entity.legal_name, page_number=2, source_reference="PAGE_2_LINE_4",
        **metadata,
    )
    field = ExtractedField(
        field_key=DocumentFieldKey.LEGAL_NAME,
        original_extracted_value=candidate.value,
        normalized_value=candidate.value,
        canonical_value=candidate.value,
        confidence=0.9118,
        provenance=FieldProvenance(
            provider="LOCAL_PDF_TEXT", environment=IdpEnvironment.LOCAL,
            page_number=2, source_reference="PAGE_2_LINE_4",
        ),
        comparison_status=ComparisonStatus.MATCH, candidates=(candidate,), **metadata,
    )
    document = document.model_copy(update={
        "document_version": 1, "fields": [field], "ownership_observations": (observed,),
        "pages": (DocumentPageEvidence(
            page_number=2, source_reference="PAGE_2", **metadata,
        ),),
    })
    cases = Cases(case)
    reader = DocumentReader(document)
    service = service_for(cases, documents=reader)
    service.load(case_id=case.case_id)
    original = service.analyze(case_id=case.case_id)
    declaration = make_declaration().model_copy(update={
        "observed_document_versions": original.document_bindings,
        "selected_observation_ids": (observed.observation_id,),
    })
    provider = ManualOwnershipEvidenceProvider(
        declaration=declaration, reviewed_by_actor_id="maya-lim",
        cases=cases, documents=reader, clock=lambda: FIXED_TIME,
    )
    revised = service.replace_review_required_source(
        case_id=case.case_id, provider=provider, review_receipt=provider.review_receipt,
        expected_version=original.version,
    )
    revised = service.replace_review_required_source(
        case_id=case.case_id, provider=provider, review_receipt=provider.review_receipt,
        expected_version=revised.version,
    )
    return DurableCaseSnapshot(
        case_id=case.case_id, revision=0, onboarding=case,
        documents=(document,), ownership=revised,
        created_at=FIXED_TIME, updated_at=FIXED_TIME,
    )


def supplemental_snapshot() -> DurableCaseSnapshot:
    case = official_garden_case().model_copy(update={"created_by_actor_id": "maya-lim"})
    case = case.model_copy(update={
        "policy_snapshot": PolicyManagementService(InMemoryPolicyRepository()).case_snapshot(),
        "registry_acquisition": case.registry_acquisition.model_copy(update={
            "issues": (RegistryAcquisitionIssue(
                code="REGISTRY_EXPECTED_DATA_MISSING",
                message="Synthetic official ownership evidence is unavailable.",
            ),),
        }),
    })
    cases = Cases(case)
    provider = RegistryAcquisitionOwnershipProvider(
        cases, garden_supplement_enabled=True, clock=lambda: FIXED_TIME
    )
    service = service_for(cases, provider, supplement=True)
    service.load(case_id=case.case_id)
    ownership = service.analyze(case_id=case.case_id)
    return DurableCaseSnapshot(
        case_id=case.case_id, revision=0, onboarding=case, ownership=ownership,
        created_at=FIXED_TIME, updated_at=FIXED_TIME,
    )


def ambiguous_snapshot() -> DurableCaseSnapshot:
    _, zero, documents, _, _ = build_system(require_confirmation=True)
    created = zero.create_case(
        "202400001A", team_id=TeamId.TEAM_A, created_by_actor_id="maya-lim"
    )

    class AmbiguousProvider(MockIdpProvider):
        def process(self, document: IdpDocumentInput) -> object:
            result = super().process(document)
            result.fields = [
                item.model_copy(update={
                    "value": None, "extraction_quality": ExtractionQuality.AMBIGUOUS,
                    "candidates": (
                        DocumentFieldCandidate(
                            value="FIRST SYNTHETIC PTE. LTD.", page_number=1,
                            source_reference="PAGE_1_LINE_1",
                        ),
                        DocumentFieldCandidate(
                            value="SECOND SYNTHETIC PTE. LTD.", page_number=1,
                            source_reference="PAGE_1_LINE_2",
                        ),
                    ),
                }) if item.field_key == DocumentFieldKey.LEGAL_NAME else item
                for item in result.fields
            ]
            result.pages = (DocumentPageEvidence(page_number=1, source_reference="PAGE_1"),)
            return result

    zero.attach_document(
        case_id=created.case_id, display_name="Synthetic.pdf", content_type="application/pdf",
        content=PDF, idp_provider=AmbiguousProvider(),
    )
    reconciliation = zero._reconciliation.reconcile_current(case_id=created.case_id)  # noqa: SLF001
    case = zero._cases.get_case(created.case_id)  # noqa: SLF001
    return DurableCaseSnapshot(
        case_id=created.case_id, revision=0, onboarding=case,
        documents=tuple(documents.list_documents(case_id=created.case_id)),
        reconciliation=reconciliation, created_at=case.created_at, updated_at=case.updated_at,
    )


def test_schema9_codec_preserves_originals_metadata_decisions_and_prior_receipts() -> None:
    codec = object.__new__(MongoCaseStore)
    original = session2_snapshot()
    raw = codec._encode(original)  # noqa: SLF001 - owning durable representation
    restored = codec._decode(raw)  # noqa: SLF001
    assert restored == original
    assert raw["schema_version"] == 11
    assert restored.onboarding.created_by_actor_id == "maya-lim"
    document = restored.documents[0]
    assert document.document_version == 1
    assert document.fields[0].provenance.page_number == 2
    assert document.fields[0].raw_ocr_mean_confidence == 94
    assert document.fields[0].candidates[0].page_number == 2
    assert document.pages[0].extraction_method == ExtractionMethod.LOCAL_TESSERACT_OCR
    assert restored.ownership.document_observations == document.ownership_observations
    assert document.ownership_observations[0].decision_state == "PROPOSED"
    assert restored.ownership.document_discrepancies[0].verification_state == "REVIEWED"
    assert restored.ownership.prior_analyses[-1].manual_review_receipt is not None
    assert restored.ownership.prior_analyses[0].document_discrepancies[0].verification_state == (
        "REVIEW_REQUIRED"
    )
    assert restored.ownership.manual_review_receipt.selected_observation_ids == (
        document.ownership_observations[0].observation_id,
    )
    assert restored.ownership.manual_review_receipt.observed_document_versions == (
        restored.ownership.document_bindings
    )
    assert not {"raw_bytes", "full_text", "document_body", "raw_provider_payload"} & raw.keys()


def test_schema9_codec_preserves_official_and_local_supplement_originals() -> None:
    codec = object.__new__(MongoCaseStore)
    original = supplemental_snapshot()
    restored = codec._decode(codec._encode(original))  # noqa: SLF001
    assert restored == original
    assert restored.ownership.source_classification == "OFFICIAL_MOCK_PLUS_LOCAL_SUPPLEMENT"
    assert restored.ownership.supplemental_parties
    assert restored.ownership.supplemental_relationships
    assert restored.ownership.supplemental_evidence
    assert restored.onboarding.registry_acquisition.relationships == ()
    assert restored.onboarding.registry_acquisition.ownership_parties == ()


def legacy_document_raw() -> dict[str, Any]:
    raw = object.__new__(MongoCaseStore)._encode(session2_snapshot())  # noqa: SLF001
    omit_session2_fields(raw)
    return raw["documents"][0]


@pytest.mark.parametrize("version", range(1, 9))
def test_exact_legacy_reads_keep_creator_and_extraction_metadata_unknown(version: int) -> None:
    raw = historical_raw(version)
    raw["documents"] = [legacy_document_raw()]
    document = raw["documents"][0]
    document["case_id"] = raw["case_id"]
    for event in document["events"]:
        event["case_id"] = raw["case_id"]
    before = deepcopy(raw)
    restored = object.__new__(MongoCaseStore)._decode(raw)  # noqa: SLF001
    assert raw == before
    assert restored.schema_version == 11
    assert restored.onboarding.created_by_actor_id is None
    assert restored.documents[0].document_version is None
    assert restored.documents[0].pages == ()
    assert restored.documents[0].ownership_observations == ()
    field = restored.documents[0].fields[0]
    assert field.extraction_method == ExtractionMethod.UNKNOWN
    assert field.extraction_quality == ExtractionQuality.UNKNOWN
    assert field.score_kind == "LEGACY_UNSPECIFIED"
    assert field.raw_ocr_mean_confidence is None
    assert field.candidates == ()


@pytest.mark.parametrize("version", range(1, 9))
@pytest.mark.parametrize("location,field", [
    ("onboarding", "created_by_actor_id"),
    ("document", "document_version"), ("document", "pages"),
    ("document", "ownership_observations"),
    ("field", "extraction_method"), ("field", "extraction_quality"),
    ("field", "score_kind"), ("field", "score_formula"),
    ("field", "raw_ocr_mean_confidence"), ("field", "raw_ocr_word_count"),
    ("field", "candidates"),
])
def test_legacy_envelopes_reject_new_fields_even_when_explicitly_null(
    version: int, location: str, field: str,
) -> None:
    raw = historical_raw(version)
    if location == "onboarding":
        target = raw["onboarding"]
    else:
        raw["documents"] = [legacy_document_raw()]
        target = raw["documents"][0]
        if location == "field":
            target = target["fields"][0]
    target[field] = None
    with pytest.raises(PersistenceDataInvalidError):
        object.__new__(MongoCaseStore)._decode(raw)  # noqa: SLF001


@pytest.mark.parametrize("picked", [None, "FIRST CANDIDATE PTE. LTD."])
def test_ambiguous_reconciliation_has_no_picked_value(picked: str | None) -> None:
    values = {
        "observation_id": uuid4(), "field_name": ReconciliationField.LEGAL_NAME,
        "normalized_value": picked, "source_kind": ReconciliationSourceKind.DOCUMENT_IDP,
        "observed_at": FIXED_TIME, "source_record_id": uuid4(),
        "evidence_reference": "DOCUMENT_AMBIGUOUS_EXTRACTION",
        "validity": ObservationValidity.AMBIGUOUS,
    }
    if picked is not None:
        with pytest.raises(ValidationError):
            ReconciliationObservation(**values)
    else:
        observation = ReconciliationObservation(**values)
        assert observation.raw_value is None
        assert observation.normalized_value is None
        assert observation.validity == ObservationValidity.AMBIGUOUS


@pytest.mark.parametrize("mutate", ["save", "transaction_replace", "transaction_restore"])
@pytest.mark.parametrize("creator,replacement", [("maya-lim", "olivia-koh"), (None, "maya-lim")])
def test_creator_binding_is_immutable_in_memory_repository(
    mutate: str, creator: str | None, replacement: str,
) -> None:
    repository = InMemoryOnboardingCaseRepository()
    case = make_case().model_copy(update={"created_by_actor_id": creator})
    repository.create(case)
    changed = case.model_copy(update={"created_by_actor_id": replacement})
    with pytest.raises(OnboardingCaseRepositoryConflictError):
        if mutate == "transaction_restore":
            repository.transaction_restore(case.case_id, changed)
        else:
            getattr(repository, mutate)(changed)
    assert repository.get(case.case_id) == case


@pytest.fixture
def decision_system():
    _, zero, documents, target, _ = build_system(require_confirmation=True)
    zero._ownership._documents = documents  # noqa: SLF001 - exercise current composition seam
    settings = Settings(_env_file=None, app_env="test", demo_controls_enabled=True)
    encoded = generate_scrypt_password_hash(TEST_PASSWORD)
    authentication = build_test_authentication_service({
        profile.user_id: encoded for profile in SYNTHETIC_USER_PROFILES
    })
    application = create_app(
        settings, onboarding_service=zero._cases,  # noqa: SLF001
        document_processing_service=documents, ownership_analysis_service=zero._ownership,  # noqa: SLF001
        clm_orchestration_service=zero._clm, zero_touch_orchestrator=zero,  # noqa: SLF001
        authentication_service=authentication,
    )
    return application, authentication, zero, documents, target


def logged_in(application, user_id: str):
    client = RawTestClient(application)
    response = client.post(
        "/api/auth/login", json={"user_id": user_id, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200
    return client, {"X-CSRF-Token": response.json()["csrf_token"]}


def ready_decision_case(system, *, creator: str | None = "maya-lim"):
    application, _, zero, documents, _ = system
    client, headers = logged_in(application, "maya-lim")
    if creator is None:
        created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)
        case_id = created.case_id
    else:
        created = client.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"},
                              headers=headers)
        assert created.status_code == 201
        case_id = UUID(created.json()["case"]["case_id"])
    zero.attach_document(
        case_id=case_id, content=PDF, content_type="application/pdf",
        display_name="Synthetic.pdf",
    )
    document = documents.list_documents(case_id=case_id)[0]
    ownership = zero._ownership.get(case_id=case_id)  # noqa: SLF001
    automation = zero.get(case_id=case_id)
    case = zero._cases.get_case(case_id)  # noqa: SLF001
    declaration = _declaration_for_current(zero, document, ownership)
    payload = declaration.model_dump(mode="json")
    payload.pop("case_id")
    payload.pop("source_type")
    payload.update(
        expected_automation_version=automation.version,
        expected_ownership_version=ownership.version,
        expected_case_event_count=len(case.events),
    )
    return case_id, client, headers, payload


def test_creation_binds_server_actor_and_rejects_client_authored_creator(decision_system) -> None:
    application, _, zero, _, _ = decision_system
    client, headers = logged_in(application, "maya-lim")
    forged = client.post(
        "/api/clm/zero-touch/cases",
        json={"uen": "202400001A", "created_by_actor_id": "olivia-koh"}, headers=headers,
    )
    assert forged.status_code == 422
    created = client.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"},
                          headers=headers)
    assert created.status_code == 201
    case = zero._cases.get_case(UUID(created.json()["case"]["case_id"]))  # noqa: SLF001
    assert case.created_by_actor_id == "maya-lim"


@pytest.mark.parametrize("user_id,authorized", [
    ("maya-lim", True), ("ethan-tan", False), ("olivia-koh", False),
])
def test_summary_authority_is_backend_bound_to_creator(
    decision_system, user_id: str, authorized: bool,
) -> None:
    case_id, _, _, _ = ready_decision_case(decision_system)
    client, _ = logged_in(decision_system[0], user_id)
    detail = client.get(f"/api/clm/zero-touch/cases/{case_id}")
    assert detail.status_code == 200
    assert detail.json()["evidence_decision_authorized"] is authorized
    assert detail.json()["ownership_edit_authorized"] is authorized


@pytest.mark.parametrize("creator", ["maya-lim", None])
@pytest.mark.parametrize("user_id", ["ethan-tan", "olivia-koh"])
@pytest.mark.parametrize("selection", [
    "CURRENT_EVIDENCE", "DOCUMENT_OBSERVATIONS", "USER_SUPPLIED_DECLARATION",
])
def test_noncreator_source_choice_is_forbidden_without_any_mutation(
    decision_system, creator: str | None, user_id: str, selection: str,
) -> None:
    case_id, _, _, payload = ready_decision_case(decision_system, creator=creator)
    application, _, zero, documents, target = decision_system
    client, headers = logged_in(application, user_id)
    before = zero.get(case_id=case_id)
    old_ownership = zero._ownership.get(case_id=case_id)  # noqa: SLF001
    old_documents = documents.list_documents(case_id=case_id)
    calls = list(target.calls)
    payload["source_selection"] = selection
    denied = client.post(f"/api/clm/zero-touch/cases/{case_id}/manual-ownership-evidence",
                         json=payload, headers=headers)
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "CASE_EVIDENCE_DECISION_FORBIDDEN"
    assert zero.get(case_id=case_id) == before
    assert zero._ownership.get(case_id=case_id) == old_ownership  # noqa: SLF001
    assert documents.list_documents(case_id=case_id) == old_documents
    assert target.calls == calls


def test_unknown_legacy_creator_grants_no_decision_authority(decision_system) -> None:
    case_id, client, headers, payload = ready_decision_case(decision_system, creator=None)
    summary = client.get(f"/api/clm/zero-touch/cases/{case_id}").json()
    assert summary["evidence_decision_authorized"] is False
    assert summary["ownership_edit_authorized"] is False
    denied = client.post(f"/api/clm/zero-touch/cases/{case_id}/manual-ownership-evidence",
                         json=payload, headers=headers)
    assert denied.status_code == 403


def test_creator_api_edit_retains_receipt_and_disables_edit_after_target_freeze(
    decision_system,
) -> None:
    case_id, client, headers, payload = ready_decision_case(decision_system)
    _, _, zero, _, target = decision_system
    before_calls = list(target.calls)
    accepted = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/manual-ownership-evidence",
        json=payload, headers=headers,
    )
    assert accepted.status_code == 200
    assert target.calls == before_calls
    retained = zero._ownership.get(case_id=case_id)  # noqa: SLF001
    assert retained.manual_review_receipt.actor_id == "maya-lim"
    assert retained.manual_review_receipt.source_selection == "USER_SUPPLIED_DECLARATION"
    assert retained.prior_analyses
    after_edit = accepted.json()
    frozen = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/target-confirmation",
        json={
            "expected_automation_version": after_edit["version"],
            "expected_clm_version": after_edit["clm"]["version"],
            "expected_case_event_count": len(after_edit["case"]["events"]),
        },
        headers=headers,
    )
    assert frozen.status_code == 200
    assert frozen.json()["status"] == "COMPLETED"
    assert frozen.json()["evidence_decision_authorized"] is True
    assert frozen.json()["ownership_edit_authorized"] is False
    calls = list(target.calls)
    payload.update(
        expected_automation_version=frozen.json()["version"],
        expected_ownership_version=retained.version,
        expected_case_event_count=len(frozen.json()["case"]["events"]),
    )
    denied = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/manual-ownership-evidence",
        json=payload, headers=headers,
    )
    assert denied.status_code == 409
    assert denied.json()["detail"]["code"] == "ZERO_TOUCH_MANUAL_OWNERSHIP_NOT_ALLOWED"
    assert target.calls == calls
    assert zero._ownership.get(case_id=case_id) == retained  # noqa: SLF001


def test_creator_ownership_edit_preserves_independent_target_blocker(decision_system) -> None:
    case_id, client, headers, payload = ready_decision_case(decision_system)
    _, _, zero, _, target = decision_system
    record = zero.get(case_id=case_id)
    confirmation = next(item for item in record.active_exceptions
                        if item.exception_type == "TARGET_CONFIRMATION_REQUIRED")
    independent = confirmation.model_copy(update={
        "exception_id": uuid4(), "evidence_version": "independent-target-safety:1",
    })
    revised = record.model_copy(deep=True)
    revised.exceptions.append(independent)
    saved = zero._save(record, revised)  # noqa: SLF001 - retained independent guard
    payload["expected_automation_version"] = saved.version
    before_calls = list(target.calls)
    accepted = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/manual-ownership-evidence",
        json=payload, headers=headers,
    )
    assert accepted.status_code == 200
    current = zero.get(case_id=case_id)
    assert current.status == "WAITING_FOR_REVIEW"
    assert next(item for item in current.active_exceptions
                if item.exception_id == independent.exception_id) == independent
    assert next(item for item in current.exceptions
                if item.exception_id == confirmation.exception_id).status == "RESOLVED"
    assert target.calls == before_calls


def test_source_choice_cross_team_is_indistinguishable_from_absent_case(decision_system) -> None:
    case_id, _, _, payload = ready_decision_case(decision_system)
    client, headers = logged_in(decision_system[0], "sophia-ng")
    foreign = client.post(f"/api/clm/zero-touch/cases/{case_id}/manual-ownership-evidence",
                          json=payload, headers=headers)
    absent = client.post(f"/api/clm/zero-touch/cases/{uuid4()}/manual-ownership-evidence",
                         json=payload, headers=headers)
    assert foreign.status_code == absent.status_code == 404
    assert foreign.json() == absent.json()


@pytest.mark.parametrize("change,status,code", [
    ("logout", 401, "AUTHENTICATION_REQUIRED"),
    ("team", 404, "CASE_NOT_FOUND"),
    ("creator", 403, "CASE_EVIDENCE_DECISION_FORBIDDEN"),
])
def test_source_decision_reauthorizes_session_team_and_creator_inside_lock(
    decision_system, monkeypatch: pytest.MonkeyPatch, change: str, status: int, code: str,
) -> None:
    case_id, client, headers, payload = ready_decision_case(decision_system)
    _, authentication, zero, documents, target = decision_system
    before = zero.get(case_id=case_id)
    old_ownership = zero._ownership.get(case_id=case_id)  # noqa: SLF001
    old_documents = documents.list_documents(case_id=case_id)
    calls = list(target.calls)
    original_lock = zero._cases.case_lock  # noqa: SLF001
    original_authenticate = authentication.authenticate_session
    inside_lock = False
    changed_session = None if change == "logout" else authentication.login(
        "sophia-ng" if change == "team" else "ethan-tan", TEST_PASSWORD
    ).record

    @contextmanager
    def tracked_lock(locked_case_id: UUID) -> Iterator[None]:
        nonlocal inside_lock
        with original_lock(locked_case_id):
            if change == "logout":
                authentication.logout(client.cookies[SESSION_COOKIE_NAME])
            inside_lock = True
            yield

    def authenticate(token: str | None):
        if not inside_lock:
            return original_authenticate(token)
        if change == "logout":
            return original_authenticate(token)
        return changed_session

    monkeypatch.setattr(zero._cases, "case_lock", tracked_lock)  # noqa: SLF001
    monkeypatch.setattr(authentication, "authenticate_session", authenticate)
    denied = client.post(f"/api/clm/zero-touch/cases/{case_id}/manual-ownership-evidence",
                         json=payload, headers=headers)
    assert inside_lock
    assert denied.status_code == status
    assert denied.json()["detail"]["code"] == code
    assert zero.get(case_id=case_id) == before
    assert zero._ownership.get(case_id=case_id) == old_ownership  # noqa: SLF001
    assert documents.list_documents(case_id=case_id) == old_documents
    assert target.calls == calls


@pytest.mark.parametrize("mutation", [
    "document_id", "document_version", "duplicate_observation", "changed_original",
    "future_binding", "unknown_selected", "foreign_receipt_document", "future_receipt_binding",
    "foreign_receipt_actor",
])
def test_current_codec_rejects_corrupt_original_and_review_bindings(mutation: str) -> None:
    codec = object.__new__(MongoCaseStore)
    raw = codec._encode(session2_snapshot())  # noqa: SLF001
    document = raw["documents"][0]
    ownership = raw["ownership"]
    receipt = ownership["manual_review_receipt"]
    if mutation == "document_id":
        document["ownership_observations"][0]["document_id"] = str(uuid4())
    elif mutation == "document_version":
        document["document_version"] = None
    elif mutation == "duplicate_observation":
        document["ownership_observations"].append(deepcopy(document["ownership_observations"][0]))
    elif mutation == "changed_original":
        ownership["document_observations"][0]["explicit_percentage"] = "71"
    elif mutation == "future_binding":
        ownership["document_bindings"][0]["event_count"] += 1
    elif mutation == "unknown_selected":
        receipt["selected_observation_ids"] = [str(uuid4())]
    elif mutation == "foreign_receipt_document":
        receipt["evidence_document_id"] = str(uuid4())
    elif mutation == "foreign_receipt_actor":
        receipt["actor_id"] = "olivia-koh"
    else:
        receipt["observed_document_versions"][0]["event_count"] += 1
    with pytest.raises(PersistenceDataInvalidError):
        codec._decode(raw)  # noqa: SLF001


@pytest.mark.parametrize("mutation", [
    "metadata_construct", "metadata_copy", "observation_construct", "observation_copy",
    "page_copy", "candidate_copy",
])
def test_document_service_revalidates_forged_typed_provider_evidence(
    decision_system, mutation: str,
) -> None:
    _, _, zero, documents, _ = decision_system
    case = zero._cases.create_staged_case(  # noqa: SLF001
        "202400001A", team_id=TeamId.TEAM_A, created_by_actor_id="maya-lim"
    )
    baseline = MockIdpProvider().process(IdpDocumentInput(
        profile=make_document().profile, content=b"synthetic",
    ))
    metadata = IdpProviderMetadata(provider_name="LOCAL_TEST", environment=IdpEnvironment.LOCAL)
    page = DocumentPageEvidence(page_number=1, source_reference="PAGE_1")
    observed = OwnershipObservationValues(
        page_number=1, source_reference="PAGE_1_ROW_1", evidence_score=0.9,
        owner_name="Synthetic Owner", explicit_percentage="70",
    )
    if mutation == "metadata_construct":
        metadata = IdpProviderMetadata.model_construct(
            provider_name="INVALID\nPROVIDER", environment=IdpEnvironment.LOCAL
        )
    elif mutation == "metadata_copy":
        metadata = metadata.model_copy(update={"environment": "UNRECOGNIZED"})
    elif mutation == "observation_construct":
        observed = OwnershipObservationValues.model_construct(
            **{**observed.model_dump(), "page_number": 0}
        )
    elif mutation == "observation_copy":
        observed = observed.model_copy(update={"explicit_percentage": "101"})
    elif mutation == "page_copy":
        page = page.model_copy(update={"page_number": 0})
    elif mutation == "candidate_copy":
        candidate = DocumentFieldCandidate(
            value=baseline.fields[0].value, page_number=1, source_reference="PAGE_1_LINE_1"
        ).model_copy(update={"page_number": 0})
        baseline.fields[0] = baseline.fields[0].model_copy(update={"candidates": (candidate,)})
    result = IdpSourceResult.model_construct(
        profile=baseline.profile, fields=baseline.fields,
        pages=(page,), ownership_observations=(observed,),
    )

    class ForgedProvider:
        def __init__(self) -> None:
            self.metadata = metadata

        def process(self, document: IdpDocumentInput) -> object:
            return result

    with pytest.raises(DocumentProcessingInfrastructureError) as failure:
        documents.create_document(
            case_id=case.case_id, display_name="Synthetic.txt", content_type="text/plain",
            content=b"synthetic typed boundary evidence", provider=ForgedProvider(),
        )
    assert failure.value.code == "IDP_MALFORMED_OUTPUT"
    retained = documents.list_documents(case_id=case.case_id)[0]
    assert retained.state == "FAILED"
    assert retained.fields == []
    assert retained.pages == ()
    assert retained.ownership_observations == ()
    assert retained.error.code == "IDP_MALFORMED_OUTPUT"


def test_current_ambiguous_reconciliation_retains_candidates_without_selected_value() -> None:
    codec = object.__new__(MongoCaseStore)
    snapshot = ambiguous_snapshot()
    restored = codec._decode(codec._encode(snapshot))  # noqa: SLF001
    assert restored == snapshot
    field = next(item for item in restored.documents[0].fields
                 if item.field_key == DocumentFieldKey.LEGAL_NAME)
    assert field.original_extracted_value is None
    assert field.normalized_value is None
    assert len({item.value for item in field.candidates}) == 2
    result = next(item for item in restored.reconciliation.fields
                  if item.field_name == ReconciliationField.LEGAL_NAME)
    assert result.outcome == "UNVERIFIABLE"
    observed = next(item for item in result.observations
                    if item.source_kind == ReconciliationSourceKind.DOCUMENT_IDP)
    assert observed.validity == "AMBIGUOUS"
    assert observed.normalized_value is None
    discrepancy = next(item for item in restored.reconciliation.discrepancies
                       if item.field_name == ReconciliationField.LEGAL_NAME)
    assert discrepancy.allowed_actions == ()
    assert discrepancy.decision is None


@pytest.mark.parametrize("mutation", ["missing_candidates", "different_document", "wrong_quality"])
def test_current_ambiguous_reconciliation_requires_original_candidates(mutation: str) -> None:
    codec = object.__new__(MongoCaseStore)
    raw = codec._encode(ambiguous_snapshot())  # noqa: SLF001
    field = next(item for item in raw["documents"][0]["fields"]
                 if item["field_key"] == "legal_name")
    if mutation == "missing_candidates":
        field["candidates"] = field["candidates"][:1]
    elif mutation == "wrong_quality":
        field["extraction_quality"] = "HIGH"
    else:
        for result in (*raw["reconciliation"]["fields"], *raw["reconciliation"]["discrepancies"]):
            for observation in result["observations"]:
                if observation["validity"] == "AMBIGUOUS":
                    observation["source_record_id"] = str(uuid4())
    with pytest.raises(PersistenceDataInvalidError):
        codec._decode(raw)  # noqa: SLF001


@pytest.mark.parametrize("version", range(1, 9))
@pytest.mark.parametrize("marker", ["validity", "evidence_reference"])
def test_historical_envelopes_reject_later_ambiguous_observation_state(
    version: int, marker: str,
) -> None:
    raw = historical_raw(version)
    # The historical guard must reject the later state before domain migration.
    observation = {
        "validity": "AMBIGUOUS" if marker == "validity" else "MISSING",
        "evidence_reference": "DOCUMENT_AMBIGUOUS_EXTRACTION" if marker == "evidence_reference"
        else None,
    }
    raw["reconciliation"] = {"fields": [{"observations": [observation]}]}
    with pytest.raises(ValueError, match="Historical schema cannot contain ambiguous extraction"):
        reject_session2_legacy_fields(raw)
    with pytest.raises(PersistenceDataInvalidError):
        object.__new__(MongoCaseStore)._decode(raw)  # noqa: SLF001


@pytest.mark.parametrize("complete_coverage", [False, True])
def test_document_source_selection_requires_observations_for_every_declared_edge(
    complete_coverage: bool,
) -> None:
    case = make_case()
    document = make_document()
    first = proposal(
        document, owner_name="Synthetic Garden Owner A",
        explicit_percentage="60", source_reference="PAGE_1_ROW_1",
    )
    second = proposal(
        document, owner_name="Synthetic Garden Owner B",
        explicit_percentage="40", source_reference="PAGE_1_ROW_2",
    )
    document = document.model_copy(update={
        "document_version": 1, "ownership_observations": (first, second),
    })
    cases = Cases(case)
    reader = DocumentReader(document)
    service = service_for(cases, documents=reader)
    service.load(case_id=case.case_id)
    original = service.analyze(case_id=case.case_id)
    selected = (first.observation_id, second.observation_id) if complete_coverage else (
        first.observation_id,
    )
    declaration = make_declaration().model_copy(update={
        "source_selection": "DOCUMENT_OBSERVATIONS",
        "observed_document_versions": original.document_bindings,
        "selected_observation_ids": selected,
    })
    provider = ManualOwnershipEvidenceProvider(
        declaration=declaration, reviewed_by_actor_id="maya-lim", cases=cases, documents=reader,
        clock=lambda: FIXED_TIME,
    )
    if not complete_coverage:
        with pytest.raises(OwnershipRequestError) as denied:
            service.replace_review_required_source(
                case_id=case.case_id, provider=provider,
                review_receipt=provider.review_receipt, expected_version=original.version,
            )
        assert denied.value.code == "OWNERSHIP_SELECTED_SOURCE_MISMATCH"
        assert service.get(case_id=case.case_id) == original
    else:
        revised = service.replace_review_required_source(
            case_id=case.case_id, provider=provider,
            review_receipt=provider.review_receipt, expected_version=original.version,
        )
        assert revised.state == "ANALYZED"
        assert revised.manual_review_receipt.source_selection == "DOCUMENT_OBSERVATIONS"
        assert revised.manual_review_receipt.selected_observation_ids == selected
        assert revised.document_observations == original.document_observations


def test_new_ownership_intake_retires_old_binding_and_preserves_prior_evidence(
    decision_system,
) -> None:
    _, _, zero, _, target = decision_system
    created = zero.create_case(
        "202400001A", team_id=TeamId.TEAM_A, created_by_actor_id="maya-lim"
    )

    class ProposingProvider(MockIdpProvider):
        def __init__(self, percentage: str) -> None:
            super().__init__()
            self.percentage = percentage

        def process(self, document: IdpDocumentInput) -> object:
            result = super().process(document)
            observed = OwnershipObservationValues(
                page_number=1, source_reference="PAGE_1_ROW_1", evidence_score=0.97,
                extraction_quality="HIGH", owner_name="Avery Tan", owner_type="NATURAL_PERSON",
                owned_entity_registration_identifier="202400001A",
                explicit_percentage=self.percentage,
            )
            return result.model_copy(update={
                "pages": (DocumentPageEvidence(page_number=1, source_reference="PAGE_1"),),
                "ownership_observations": (observed,),
            })

    waiting = zero.attach_document(
        case_id=created.case_id, display_name="Synthetic.pdf", content_type="application/pdf",
        content=PDF, idp_provider=ProposingProvider("60"),
    )
    assert waiting.status == "WAITING_FOR_REVIEW"
    assert waiting.current_stage == "OWNERSHIP"
    original = zero._ownership.get(case_id=created.case_id)  # noqa: SLF001
    obsolete_ids = {item.exception_id for item in waiting.active_exceptions
                    if item.stage == "OWNERSHIP"}
    calls = list(target.calls)
    zero.intake_document(
        case_id=created.case_id, display_name="Additional.pdf", content_type="application/pdf",
        content=PDF, idp_provider=ProposingProvider("70"),
    )
    after = zero.get(case_id=created.case_id)
    refreshed = zero._ownership.get(case_id=created.case_id)  # noqa: SLF001
    assert after.status == "WAITING_FOR_REVIEW"
    assert after.current_stage == "OWNERSHIP"
    assert after.technical_failure is None
    assert refreshed.analysis_id != original.analysis_id
    assert len(refreshed.document_bindings) == 2
    assert len(refreshed.document_observations) == 2
    assert refreshed.prior_analyses[-1].document_observations == original.document_observations
    assert refreshed.prior_analyses[-1].analysis_id == original.analysis_id
    assert not obsolete_ids & {item.exception_id for item in after.active_exceptions}
    assert target.calls == calls
