"""Strict GoldTier XPI sandbox contract and fail-closed composition tests."""

import importlib
from collections.abc import Mapping
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError

from app.config import Settings
from app.domain.access import AuthenticatedActor, Role, UserProfile
from app.services.admin_repository import InMemoryPolicyRepository
from app.services.policy_management import PolicyForbiddenError, PolicyManagementService

PDF = (Path(__file__).parent / "fixtures" / "uat" / "clean-company-profile.pdf").read_bytes()


def _xpi_models() -> object:
    return importlib.import_module("app.connectors.goldtier_xpi_models")


def _director() -> AuthenticatedActor:
    return AuthenticatedActor(
        profile=UserProfile(
            user_id="sandbox-policy-owner",
            display_name="Sandbox Policy Owner",
            role=Role.DIRECTOR,
            team_id=None,
        )
    )


def _sandbox_submission(*, ready: bool = True) -> object:
    policy = importlib.import_module("app.domain.policy")
    target = importlib.import_module("app.domain.target_submission")
    authority = (
        policy.PolicyAuthority.SPONSOR_SUPPLIED if ready else policy.PolicyAuthority.TBD_SPONSOR
    )
    value = "SPONSOR VALUE" if ready else "TBD_SPONSOR"

    def labelled() -> object:
        return policy.AuthorityLabelledTargetValue(value=value, authority=authority)

    return target.GoldTierSubmissionInput(
        submission_id=UUID("00000000-0000-4000-8000-000000000001"),
        case_id=UUID("00000000-0000-4000-8000-000000000002"),
        source_case_id="SYNTHETIC-CASE-001",
        correlation_id=UUID("00000000-0000-4000-8000-000000000003"),
        accepted_at=datetime(2026, 9, 24, tzinfo=UTC),
        provider_mode="SANDBOX",
        policy_catalogue_version=42,
        target_external_key="FYP-SYNTHETIC-001",
        target_policy=policy.GoldTierTargetPolicySnapshot(
            kyc_customer_type=labelled(),
            client_segment=labelled(),
            customer_external_system=labelled(),
            registration_type=labelled(),
            policy=labelled(),
            booking_entity=labelled(),
            account_entity_type=labelled(),
            product_type=labelled(),
        ),
        canonical_entity=target.SubmissionCanonicalEntity(
            registration_number="202400001A",
            legal_name="FYP ZERO TOUCH SME SYNTHETIC",
            country_of_incorporation="SG",
            party_type="Organisation",
            registration_date=date(2024, 1, 2),
            entity_status="SYNTHETIC",
            registered_address=target.SubmissionRegisteredAddress(
                address_line_1="1 SYNTHETIC WAY",
                address_line_2="#01-01",
                postal_code="018956",
                country_code="SG",
            ),
        ),
        idempotency=target.GoldTierIdempotencyBindings(
            search=UUID("00000000-0000-4000-8000-000000000011"),
            shell=UUID("00000000-0000-4000-8000-000000000012"),
            policy=UUID("00000000-0000-4000-8000-000000000013"),
            amend=UUID("00000000-0000-4000-8000-000000000014"),
        ),
    )


class FakeXpiTransport:
    def __init__(
        self,
        responses: list[object] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.responses = list(responses or [])
        self.error = error
        self.calls: list[dict[str, object]] = []

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        json_body: object | None,
        timeout_seconds: float,
        max_response_bytes: int,
    ) -> object:
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": dict(headers),
                "json_body": json_body,
                "timeout_seconds": timeout_seconds,
                "max_response_bytes": max_response_bytes,
            }
        )
        if self.error is not None:
            raise self.error
        assert self.responses
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_sandbox_mode_requires_explicit_https_configuration_and_keeps_values_backend_only() -> None:
    settings = Settings(
        _env_file=None,
        app_env="test",
        goldtier_connector_mode="sandbox",
        goldtier_sandbox_base_url="https://sandbox.goldtier.invalid",
        goldtier_sandbox_environment="synthetic",
        goldtier_sandbox_user_id=SecretStr("synthetic-user-id"),
        goldtier_sandbox_timeout_seconds=7.5,
    )

    assert settings.goldtier_connector_mode == "sandbox"
    assert settings.goldtier_sandbox_timeout_seconds == 7.5
    assert "synthetic-user-id" not in repr(settings)


@pytest.mark.parametrize(
    "overrides",
    [
        {},
        {"goldtier_sandbox_base_url": "http://sandbox.goldtier.invalid"},
        {"goldtier_sandbox_environment": "../escape"},
        {"goldtier_sandbox_user_id": SecretStr("line\nbreak")},
    ],
)
def test_sandbox_mode_fails_closed_for_missing_or_unsafe_configuration(
    overrides: dict[str, object],
) -> None:
    values: dict[str, object] = {
        "_env_file": None,
        "app_env": "test",
        "goldtier_connector_mode": "sandbox",
        "goldtier_sandbox_base_url": "",
        "goldtier_sandbox_environment": "synthetic",
        "goldtier_sandbox_user_id": SecretStr("synthetic-user-id"),
    }
    values.update(overrides)

    with pytest.raises(ValidationError):
        Settings(**values)  # type: ignore[arg-type]


def test_mock_remains_the_credential_free_default() -> None:
    settings = Settings(_env_file=None)

    assert settings.goldtier_connector_mode == "mock"
    assert settings.goldtier_sandbox_base_url == ""
    assert settings.goldtier_sandbox_user_id is None


def test_composition_selects_the_explicit_xpi_connector_and_mapper_without_fallback() -> None:
    composition = importlib.import_module("app.composition")
    transport = FakeXpiTransport()
    settings = Settings(
        _env_file=None,
        app_env="test",
        goldtier_connector_mode="sandbox",
        goldtier_sandbox_base_url="https://sandbox.goldtier.invalid",
        goldtier_sandbox_environment="synthetic",
        goldtier_sandbox_user_id=SecretStr("synthetic-user-id"),
    )

    service = composition.build_onboarding_service(
        settings=settings,
        goldtier_transport=transport,
    )
    case = service.create_staged_case("202400001A")
    submission = service.build_submission_input(case, provider_mode="SANDBOX")

    assert type(service._goldtier).__name__ == "GoldTierXpiSandboxConnector"
    assert type(service._goldtier_mapper).__name__ == "GoldTierXpiRequestMapper"
    assert submission.provider_mode == "SANDBOX"
    assert transport.calls == []


def test_execution_profile_reports_configured_sandbox_target_truthfully() -> None:
    main = importlib.import_module("app.main")
    settings = Settings(
        _env_file=None,
        app_env="test",
        goldtier_connector_mode="sandbox",
        goldtier_sandbox_base_url="https://sandbox.goldtier.invalid",
        goldtier_sandbox_environment="synthetic",
        goldtier_sandbox_user_id=SecretStr("synthetic-user-id"),
    )

    with TestClient(main.create_app(settings)) as client:
        profile = client.get("/api/system/execution-profile")

    assert profile.status_code == 200
    assert profile.json()["target_environment"] == "SANDBOX"
    assert profile.json()["target_provider_classification"] == "SANDBOX_PARTIAL"


def test_case_scoped_preview_exposes_only_bounded_fields_and_missing_authority() -> None:
    service = _xpi_onboarding_service(FakeXpiTransport(), target_ready=False)
    case = service.create_staged_case("202400001A")

    preview = service.build_request_preview(case, provider_mode="SANDBOX")

    assert preview.environment == "SANDBOX"
    assert preview.dispatch_ready is False
    assert preview.policy_version == case.policy_snapshot.catalogue_version
    assert "user_id" not in preview.model_dump_json()
    missing = {
        field.target_field
        for operation in preview.operations
        for field in operation.fields
        if field.missing
    }
    assert "kycCustomerType" in missing
    assert "policy" in missing


def test_clm_submission_plan_uses_the_configured_sandbox_preview() -> None:
    service = _xpi_onboarding_service(FakeXpiTransport(), target_ready=False)
    documents = importlib.import_module("app.services.document_processing")
    document_repository = importlib.import_module("app.services.document_repository")
    mock_idp = importlib.import_module("app.connectors.mock_idp")
    ownership = importlib.import_module("app.services.ownership_analysis")
    ownership_repository = importlib.import_module("app.services.ownership_repository")
    mock_ownership = importlib.import_module("app.connectors.mock_ownership")
    clm_service = importlib.import_module("app.services.clm_orchestration")
    clm_repository = importlib.import_module("app.services.clm_repository")
    document_service = documents.DocumentProcessingService(
        cases=service,
        idp=mock_idp.MockIdpProvider(),
        repository=document_repository.InMemoryDocumentProcessingRepository(),
        max_upload_bytes=5 * 1024 * 1024,
        review_confidence_threshold=0.85,
    )
    ownership_service = ownership.OwnershipAnalysisService(
        cases=service,
        provider=mock_ownership.MockOwnershipProvider(),
        repository=ownership_repository.InMemoryOwnershipAnalysisRepository(),
        threshold_percent=Decimal("25"),
        max_parties=100,
        max_relationships=200,
        max_depth=8,
        max_paths_per_candidate=64,
        max_total_paths=256,
    )
    clm = clm_service.ClmOrchestrationService(
        cases=service,
        documents=document_service,
        ownership=ownership_service,
        repository=clm_repository.InMemoryClmOrchestrationRepository(),
    )

    record = clm.create_case("202400001A")

    assert record.submission_plan.environment == "SANDBOX"
    assert record.submission_plan.provider_classification == "SANDBOX_PARTIAL"
    assert record.submission_plan.request_preview.dispatch_ready is False
    assert record.submission_plan.related_party_integration == "BLOCKED_CHILD_ID_LIFECYCLE"


def _sandbox_zero_touch_system(transport: FakeXpiTransport) -> tuple[object, object, object]:
    documents = importlib.import_module("app.services.document_processing")
    document_repository = importlib.import_module("app.services.document_repository")
    mock_idp = importlib.import_module("app.connectors.mock_idp")
    ownership = importlib.import_module("app.services.ownership_analysis")
    ownership_repository = importlib.import_module("app.services.ownership_repository")
    mock_ownership = importlib.import_module("app.connectors.mock_ownership")
    clm_service = importlib.import_module("app.services.clm_orchestration")
    clm_repository = importlib.import_module("app.services.clm_repository")
    zero_touch = importlib.import_module("app.services.zero_touch_orchestration")
    zero_touch_repository = importlib.import_module("app.services.zero_touch_repository")
    cases = _xpi_onboarding_service(transport)
    document_service = documents.DocumentProcessingService(
        cases=cases,
        idp=mock_idp.MockIdpProvider(),
        repository=document_repository.InMemoryDocumentProcessingRepository(),
        max_upload_bytes=5 * 1024 * 1024,
        review_confidence_threshold=0.85,
    )
    ownership_service = ownership.OwnershipAnalysisService(
        cases=cases,
        provider=mock_ownership.MockOwnershipProvider(),
        repository=ownership_repository.InMemoryOwnershipAnalysisRepository(),
        threshold_percent=Decimal("25"),
        max_parties=100,
        max_relationships=200,
        max_depth=8,
        max_paths_per_candidate=64,
        max_total_paths=256,
    )
    clm = clm_service.ClmOrchestrationService(
        cases=cases,
        documents=document_service,
        ownership=ownership_service,
        repository=clm_repository.InMemoryClmOrchestrationRepository(),
    )
    orchestrator = zero_touch.ZeroTouchOrchestrator(
        cases=cases,
        documents=document_service,
        ownership=ownership_service,
        clm=clm,
        repository=zero_touch_repository.InMemoryZeroTouchAutomationRepository(),
    )
    return orchestrator, document_service, ownership_service


def _run_sandbox_case(transport: FakeXpiTransport) -> tuple[object, object, object, object]:
    orchestrator, documents, ownership = _sandbox_zero_touch_system(transport)
    created = orchestrator.create_case("202400001A")
    terminal = orchestrator.attach_document(
        case_id=created.case_id,
        display_name="sandbox-profile.pdf",
        content_type="application/pdf",
        content=PDF,
    )
    if any(
        item.exception_type == "TARGET_CONFIRMATION_REQUIRED" for item in terminal.active_exceptions
    ):
        case = orchestrator._cases.get_case(created.case_id)  # noqa: SLF001
        pending_clm = orchestrator._clm.get(case_id=created.case_id)  # noqa: SLF001
        assert case is not None and pending_clm is not None
        terminal = orchestrator.confirm_target_dispatch(
            case_id=created.case_id,
            actor_id="sandbox-test-operator",
            expected_automation_version=terminal.version,
            expected_clm_version=pending_clm.version,
            expected_case_event_count=len(case.events),
        )
    clm = orchestrator._clm.get(case_id=created.case_id)  # noqa: SLF001
    assert clm is not None
    return orchestrator, documents, ownership, terminal


def _assert_no_mock_provider_claim(messages: list[str]) -> None:
    combined = "\n".join(messages).casefold()
    assert "mock goldtier" not in combined
    assert "goldtier mock" not in combined
    assert "mock submission" not in combined


def test_sandbox_success_retains_provider_truthful_clm_and_activity_messages() -> None:
    module = importlib.import_module("app.connectors.goldtier_xpi")
    transport = FakeXpiTransport(
        [
            module.GoldTierXpiHttpResponse(status_code=200, body=[]),
            module.GoldTierXpiHttpResponse(status_code=200, body=[]),
            module.GoldTierXpiHttpResponse(status_code=200, body={"goldTierId": 12345}),
            module.GoldTierXpiHttpResponse(status_code=200, body={}),
            module.GoldTierXpiHttpResponse(status_code=200, body={}),
            module.GoldTierXpiHttpResponse(status_code=200, body=[{"goldTierId": 12345}]),
        ]
    )

    orchestrator, _, _, terminal = _run_sandbox_case(transport)
    clm = orchestrator._clm.get(case_id=terminal.case_id)  # noqa: SLF001

    assert terminal.status == "COMPLETED"
    assert clm is not None
    assert clm.submission_plan.environment == "SANDBOX"
    assert clm.submission_plan.provider_classification == "SANDBOX_PARTIAL"
    _assert_no_mock_provider_claim([event.message for event in clm.events])
    _assert_no_mock_provider_claim([event.message for event in terminal.events])
    activity = importlib.import_module("app.domain.case_management")
    export = importlib.import_module("app.services.activity_export")
    page = activity.CaseActivityPage(
        items=tuple(
            activity.CaseActivityItem(
                **event.model_dump(),
                current_priority=None,
                current_client_scope_label=None,
            )
            for event in terminal.events
        ),
        offset=0,
        limit=len(terminal.events),
        has_more=False,
    )
    _assert_no_mock_provider_claim([export.render_case_activity_csv(page)])


@pytest.mark.parametrize(
    ("responses", "expected_status"),
    [
        (
            [
                {
                    "goldTierId": 12345,
                    "legalName": "FYP ZERO TOUCH SME SYNTHETIC",
                    "countryOfIncorporation": "SG",
                    "registrationNumber": "202400001A",
                },
                {
                    "goldTierId": 67890,
                    "legalName": "FYP ZERO TOUCH SME SYNTHETIC",
                    "countryOfIncorporation": "SG",
                    "registrationNumber": "202400001A",
                },
            ],
            "WAITING_FOR_REVIEW",
        ),
        ({"safe": "provider failure"}, "TECHNICAL_FAILURE"),
    ],
)
def test_sandbox_review_and_failure_messages_never_claim_mock(
    responses: object,
    expected_status: str,
) -> None:
    module = importlib.import_module("app.connectors.goldtier_xpi")
    status_code = 200 if isinstance(responses, list) else 500
    transport = FakeXpiTransport(
        [module.GoldTierXpiHttpResponse(status_code=status_code, body=responses)]
    )

    orchestrator, _, _, terminal = _run_sandbox_case(transport)
    clm = orchestrator._clm.get(case_id=terminal.case_id)  # noqa: SLF001
    messages = [event.message for event in terminal.events]
    messages.extend(exception.explanation for exception in terminal.active_exceptions)
    if terminal.technical_failure is not None:
        messages.append(terminal.technical_failure.message)
    if clm is not None:
        messages.extend(event.message for event in clm.events)
        if clm.error is not None:
            messages.append(clm.error.message)

    assert terminal.status == expected_status
    assert clm is not None and clm.submission_plan.environment == "SANDBOX"
    _assert_no_mock_provider_claim(messages)


def test_sandbox_malformed_target_response_is_provider_truthful() -> None:
    class MalformedSearchConnector:
        environment = "SANDBOX"

        def search_party(self, *_args: object, **_kwargs: object) -> object:
            return {"unexpected": "shape"}

    service = _xpi_onboarding_service(FakeXpiTransport())
    service._goldtier = MalformedSearchConnector()  # noqa: SLF001
    case = service.create_staged_case("202400001A")
    submission = service.build_submission_input(case, provider_mode="SANDBOX")

    _confirm_service_submission(service, submission)
    receipt = service.execute_submission_input(submission)
    current = service.get_case(case.case_id)

    assert receipt.classification == "FAILED"
    assert receipt.error is not None
    assert current is not None
    _assert_no_mock_provider_claim(
        [receipt.error.message, *(event.message for event in current.events)]
    )


def test_sandbox_messages_survive_schema_v5_codec_without_provider_reinterpretation() -> None:
    module = importlib.import_module("app.connectors.goldtier_xpi")
    persistence = importlib.import_module("app.persistence.models")
    mongo = importlib.import_module("app.persistence.mongo_case_store")
    transport = FakeXpiTransport(
        [
            module.GoldTierXpiHttpResponse(status_code=200, body=[]),
            module.GoldTierXpiHttpResponse(status_code=200, body={"goldTierId": 12345}),
            module.GoldTierXpiHttpResponse(status_code=200, body={}),
            module.GoldTierXpiHttpResponse(status_code=200, body={}),
            module.GoldTierXpiHttpResponse(status_code=200, body=[{"goldTierId": 12345}]),
        ]
    )
    orchestrator, documents, ownership, terminal = _run_sandbox_case(transport)
    case = orchestrator._cases.get_case(terminal.case_id)  # noqa: SLF001
    clm = orchestrator._clm.get(case_id=terminal.case_id)  # noqa: SLF001
    reconciliation = orchestrator._reconciliation.get(case_id=terminal.case_id)  # noqa: SLF001
    assert case is not None and clm is not None
    snapshot = persistence.DurableCaseSnapshot(
        case_id=terminal.case_id,
        revision=1,
        onboarding=case,
        documents=tuple(documents.list_documents(case_id=terminal.case_id)),
        ownership=ownership.get(case_id=terminal.case_id),
        reconciliation=reconciliation,
        clm=clm,
        automation=terminal,
        created_at=terminal.created_at,
        updated_at=terminal.updated_at,
    )
    codec = object.__new__(mongo.MongoCaseStore)

    decoded = codec._decode(codec._encode(snapshot))  # noqa: SLF001

    assert decoded.clm is not None and decoded.automation is not None
    assert decoded.clm.submission_plan.environment == "SANDBOX"
    _assert_no_mock_provider_claim([event.message for event in decoded.clm.events])
    _assert_no_mock_provider_claim([event.message for event in decoded.automation.events])


def test_customer_search_query_uses_exact_supplied_aliases_and_requires_a_criterion() -> None:
    models = _xpi_models()
    request = models.XpiCustomerSearchRequest(
        legal_name="FYP ZERO TOUCH SME SYNTHETIC",
        country_of_incorporation="SG",
    )

    assert request.query_items() == (
        ("legalName", "FYP ZERO TOUCH SME SYNTHETIC"),
        ("countryOfIncorporation", "SG"),
    )
    with pytest.raises(ValidationError):
        models.XpiCustomerSearchRequest()


def test_shell_policy_and_amend_models_serialize_exact_collection_field_names() -> None:
    models = _xpi_models()
    shell = models.XpiCreateCustomerRequest(
        legal_name="FYP ZERO TOUCH SME SYNTHETIC",
        kyc_customer_type="SPONSOR VALUE",
        client_segment="SPONSOR VALUE",
        system_reference=models.XpiSystemReference(
            customer_external_system="SPONSOR VALUE",
            customer_external_system_key="FYP-SYNTHETIC-001",
        ),
        legal_registered_address=models.XpiLegalRegisteredAddress(
            street1="1 SYNTHETIC WAY",
            city="SINGAPORE",
            country_iso2="SG",
            state="SINGAPORE",
            zip="018956",
        ),
        registration=models.XpiRegistration(
            registration_type="SPONSOR VALUE",
            country_iso2="SG",
            registration_number="FYP-SYNTHETIC-001",
        ),
        country_of_incorporation="SG",
    )
    assert shell.model_dump(by_alias=True, exclude_none=True) == {
        "legalName": "FYP ZERO TOUCH SME SYNTHETIC",
        "kycCustomerType": "SPONSOR VALUE",
        "clientSegment": "SPONSOR VALUE",
        "systemReference": {
            "customerExternalSystem": "SPONSOR VALUE",
            "customerExternalSystemKey": "FYP-SYNTHETIC-001",
        },
        "legalRegisteredAddress": {
            "street1": "1 SYNTHETIC WAY",
            "city": "SINGAPORE",
            "countryIso2": "SG",
            "state": "SINGAPORE",
            "zip": "018956",
        },
        "registration": {
            "registrationType": "SPONSOR VALUE",
            "countryIso2": "SG",
            "registrationNumber": "FYP-SYNTHETIC-001",
        },
        "countryOfIncorporation": "SG",
    }

    policy = models.XpiCreateCustomerPolicyRequest(
        customer_external_system="SPONSOR VALUE",
        customer_external_system_key="FYP-SYNTHETIC-001",
        goldtier_id="12345",
        policy="SPONSOR VALUE",
        booking_entity="SPONSOR VALUE",
        account_entity_type="SPONSOR VALUE",
        product_type="SPONSOR VALUE",
    )
    assert set(policy.model_dump(by_alias=True)) == {
        "customerExternalSystem",
        "customerExternalSystemKey",
        "goldTierId",
        "policy",
        "bookingEntity",
        "accountEntityType",
        "productType",
    }

    amend = models.XpiAmendCustomerRequest(
        goldtier_id="12345",
        policy="SPONSOR VALUE",
    )
    assert amend.model_dump(by_alias=True, exclude_none=True) == {
        "goldTierId": "12345",
        "policy": "SPONSOR VALUE",
    }


def test_related_party_models_require_a_real_child_id_and_explicit_relationship_values() -> None:
    models = _xpi_models()
    relationship = models.XpiRelationshipAttribute(
        relationship_type="SPONSOR VALUE",
        relationship_titles=("SPONSOR VALUE",),
        receivable_financing=False,
        authorized_signatory=False,
        controller=False,
        responsible_entity=False,
        owner_type="SPONSOR VALUE",
        owner_percent="25.000000",
    )
    request = models.XpiCreateRelatedPartyPolicyRequest(
        customer_external_system="SPONSOR VALUE",
        customer_external_system_key="FYP-SYNTHETIC-CHILD-001",
        goldtier_id="12345",
        child_id="67890",
        country_of_incorporation="SG",
        policy="SPONSOR VALUE",
        relationships=models.XpiRelationships(relationship_attribute=relationship),
    )

    assert request.model_dump(by_alias=True, exclude_none=True)["childId"] == "67890"
    with pytest.raises(ValidationError):
        models.XpiCreateRelatedPartyPolicyRequest(
            customer_external_system="SPONSOR VALUE",
            customer_external_system_key="FYP-SYNTHETIC-CHILD-001",
            goldtier_id="12345",
            child_id="",
            country_of_incorporation="SG",
            policy="SPONSOR VALUE",
            relationships=models.XpiRelationships(relationship_attribute=relationship),
        )


@pytest.mark.parametrize(
    "value",
    ["100.000001", "100.1", "101", "-0.1", "NaN", "Infinity", "0.0000001"],
)
def test_related_party_owner_percent_rejects_out_of_range_or_scale_values(value: str) -> None:
    models = _xpi_models()

    with pytest.raises(ValidationError):
        models.XpiRelationshipAttribute(
            relationship_type="SPONSOR VALUE",
            relationship_titles=("SPONSOR VALUE",),
            receivable_financing=False,
            authorized_signatory=False,
            controller=False,
            responsible_entity=False,
            owner_type="SPONSOR VALUE",
            owner_percent=value,
        )


@pytest.mark.parametrize("value", ["0", "0.000001", "25.000000", "100", "100.000000"])
def test_related_party_owner_percent_accepts_inclusive_bounded_values(value: str) -> None:
    models = _xpi_models()

    relationship = models.XpiRelationshipAttribute(
        relationship_type="SPONSOR VALUE",
        relationship_titles=("SPONSOR VALUE",),
        receivable_financing=False,
        authorized_signatory=False,
        controller=False,
        responsible_entity=False,
        owner_type="SPONSOR VALUE",
        owner_percent=value,
    )

    assert relationship.owner_percent == value


def test_target_classification_vocabulary_is_case_bound_not_globally_editable() -> None:
    policy = importlib.import_module("app.domain.policy")
    service = PolicyManagementService(InMemoryPolicyRepository())
    before = service.case_snapshot()
    rule = service.get(policy.GOLDTIER_KYC_CUSTOMER_TYPE_ID)

    assert rule.value == policy.StringPolicyValue(value="TBD_SPONSOR")
    assert rule.authority == policy.PolicyAuthority.TBD_SPONSOR
    assert before.goldtier_target.kyc_customer_type.value == "TBD_SPONSOR"
    assert before.goldtier_target.kyc_customer_type.authority == "TBD_SPONSOR"
    assert before.goldtier_target.dispatch_ready is False

    assert rule.allowed_values == ("TBD_SPONSOR", *policy.GOLDTIER_KYC_CUSTOMER_TYPE_VALUES)
    with pytest.raises(PolicyForbiddenError):
        service.update(
            _director(),
            rule.policy_id,
            expected_catalogue_version=service.catalogue().version,
            expected_rule_version=rule.version,
            value=policy.StringPolicyValue(value="Company - Private"),
            authority=policy.PolicyAuthority.USER_AUTHORIZED_POC,
        )
    after = service.case_snapshot()
    assert after.goldtier_target == before.goldtier_target
    assert after.catalogue_version == before.catalogue_version


def test_legacy_case_without_goldtier_target_does_not_offer_editable_classification() -> None:
    api_models = importlib.import_module("app.api_models")
    domain_models = importlib.import_module("app.domain.models")
    now = datetime(2026, 9, 27, tzinfo=UTC)
    case = domain_models.OnboardingCase(
        case_id=UUID("00000000-0000-4000-8000-000000000021"),
        source_case_id="LEGACY-NO-TARGET",
        correlation_id=UUID("00000000-0000-4000-8000-000000000022"),
        requested_uen="202400001A",
        state=domain_models.WorkflowState.REVIEW_REQUIRED,
        created_at=now,
        updated_at=now,
    )

    classification = api_models.BrowserTargetClassification.from_case(case)

    assert case.policy_snapshot.goldtier_target is None
    assert classification.editable is False
    assert classification.kyc_customer_type.selected_value is None
    assert classification.client_segment.selected_value is None


def test_case_target_classification_is_editable_until_confirmation_and_serialized_exactly() -> None:
    composition = importlib.import_module("app.composition")
    policy = importlib.import_module("app.domain.policy")
    policy_service = PolicyManagementService(InMemoryPolicyRepository())
    service = composition.build_onboarding_service(
        settings=Settings(
            _env_file=None,
            app_env="test",
            goldtier_connector_mode="sandbox",
            goldtier_sandbox_base_url="https://sandbox.goldtier.invalid",
            goldtier_sandbox_environment="synthetic",
            goldtier_sandbox_user_id=SecretStr("synthetic-user-id"),
        ),
        goldtier_transport=FakeXpiTransport(),
        policy_snapshot_provider=policy_service.case_snapshot,
    )
    case = service.create_staged_case("202400001A")

    with pytest.raises(ValueError, match="current vocabulary"):
        service.bind_goldtier_case_classification(
            case_id=case.case_id,
            kyc_customer_type="Multilateral Agencies",
            client_segment="Corporate",
        )

    bound = service.bind_goldtier_case_classification(
        case_id=case.case_id,
        kyc_customer_type="Company - Private",
        client_segment="Corporate",
    )
    target = bound.policy_snapshot.goldtier_target

    assert target.kyc_customer_type.value == "Company - Private"
    assert target.client_segment.value == "Corporate"
    assert target.kyc_customer_type.authority == policy.PolicyAuthority.USER_AUTHORIZED_POC
    assert target.client_segment.authority == policy.PolicyAuthority.USER_AUTHORIZED_POC
    assert target.registration_type.value == "ACRA"
    assert target.customer_external_system.value == "DSD"
    assert target.policy.value == "Singapore"
    assert target.booking_entity.value == "ANZBGL (Singapore Branch)"
    assert target.dispatch_ready is True
    edited = service.bind_goldtier_case_classification(
        case_id=case.case_id,
        kyc_customer_type="Company - Public",
        client_segment="Corporate",
    )
    assert edited.policy_snapshot.goldtier_target.kyc_customer_type.value == ("Company - Public")
    service.confirm_target_dispatch(
        case_id=case.case_id,
        actor_id="sandbox-test-operator",
        expected_case_event_count=len(edited.events),
        clm_version=None,
        destination="GOLDTIER_XPI_SANDBOX",
    )
    with pytest.raises(ValueError, match="already frozen"):
        service.bind_goldtier_case_classification(
            case_id=case.case_id,
            kyc_customer_type="Company - Private",
            client_segment="Corporate",
        )


def test_policy_contract_accepts_and_serializes_empty_optional_sponsor_fields() -> None:
    models = _xpi_models()
    request = models.XpiCreateCustomerPolicyRequest(
        customer_external_system="DSD",
        customer_external_system_key="FYP-SYNTHETIC-001",
        goldtier_id="12345",
        policy="SANDBOX POLICY EXAMPLE",
        booking_entity="SANDBOX BOOKING EXAMPLE",
    )

    assert request.model_dump(by_alias=True) == {
        "customerExternalSystem": "DSD",
        "customerExternalSystemKey": "FYP-SYNTHETIC-001",
        "goldTierId": "12345",
        "policy": "SANDBOX POLICY EXAMPLE",
        "bookingEntity": "SANDBOX BOOKING EXAMPLE",
        "accountEntityType": "",
        "productType": "",
    }


def test_account_entity_type_default_preserved_and_business_edit_retired() -> None:
    policy = importlib.import_module("app.domain.policy")
    service = PolicyManagementService(InMemoryPolicyRepository())
    before = service.case_snapshot()
    rule = service.get(policy.GOLDTIER_ACCOUNT_ENTITY_TYPE_ID)

    assert rule.value == policy.StringPolicyValue(value="PROJECT_DEFINED_PROVISIONAL")
    assert rule.default_value == rule.value
    assert rule.authority == policy.PolicyAuthority.PROJECT_DEFINED_PROVISIONAL
    assert rule.default_authority == policy.PolicyAuthority.PROJECT_DEFINED_PROVISIONAL
    assert before.goldtier_target.account_entity_type.value == "PROJECT_DEFINED_PROVISIONAL"
    assert (
        before.goldtier_target.account_entity_type.authority
        == policy.PolicyAuthority.PROJECT_DEFINED_PROVISIONAL
    )
    assert before.goldtier_target.missing_fields == (
        "kycCustomerType",
        "clientSegment",
    )

    with pytest.raises(PolicyForbiddenError):
        service.update(
            _director(), rule.policy_id, value=policy.StringPolicyValue(value="SPONSOR VALUE")
        )
    with pytest.raises(PolicyForbiddenError):
        service.reset_one(_director(), rule.policy_id)
    assert service.case_snapshot().goldtier_target == before.goldtier_target


def test_singapore_uen_registration_mapping_is_user_authorized_and_never_abn() -> None:
    policy = importlib.import_module("app.domain.policy")
    mapper_module = importlib.import_module("app.mappers.goldtier_xpi")
    service = PolicyManagementService(InMemoryPolicyRepository())
    registration_rule = service.get(policy.GOLDTIER_REGISTRATION_TYPE_ID)
    snapshot = service.case_snapshot().goldtier_target
    base = _sandbox_submission()
    submission = base.model_copy(
        update={
            "canonical_entity": base.canonical_entity.model_copy(
                update={"registration_number": "11111999A"}
            ),
            "target_policy": base.target_policy.model_copy(
                update={"registration_type": snapshot.registration_type}
            ),
        }
    )

    request = mapper_module.GoldTierXpiRequestMapper().build_shell_request(submission)
    serialized = request.model_dump(by_alias=True, exclude_none=True)

    assert registration_rule.value == policy.StringPolicyValue(value="ACRA")
    assert registration_rule.authority == policy.PolicyAuthority.USER_AUTHORIZED_POC
    assert snapshot.registration_type.value == "ACRA"
    assert snapshot.registration_type.authority == policy.PolicyAuthority.USER_AUTHORIZED_POC
    assert serialized["registration"] == {
        "registrationType": "ACRA",
        "countryIso2": "SG",
        "registrationNumber": "11111999A",
    }
    assert serialized["countryOfIncorporation"] == "SG"
    assert "ABN" not in str(serialized)


def test_sandbox_external_system_example_is_separate_from_acra_identity() -> None:
    policy = importlib.import_module("app.domain.policy")
    service = PolicyManagementService(InMemoryPolicyRepository())
    rule = service.get(policy.GOLDTIER_CUSTOMER_EXTERNAL_SYSTEM_ID)
    snapshot = service.case_snapshot().goldtier_target

    assert rule.value == policy.StringPolicyValue(value="DSD")
    assert rule.authority == policy.PolicyAuthority.SPONSOR_DOCUMENTED
    assert snapshot.customer_external_system.value == "DSD"
    assert snapshot.customer_external_system.authority == policy.PolicyAuthority.SPONSOR_DOCUMENTED


def test_target_policy_reset_preserves_the_fixed_value_and_authority() -> None:
    policy = importlib.import_module("app.domain.policy")
    service = PolicyManagementService(InMemoryPolicyRepository())
    original = service.get(policy.GOLDTIER_POLICY_ID)
    with pytest.raises(PolicyForbiddenError):
        service.update(
            _director(),
            original.policy_id,
            expected_catalogue_version=service.catalogue().version,
            expected_rule_version=original.version,
            value=policy.StringPolicyValue(value="SPONSOR VALUE"),
            authority=policy.PolicyAuthority.SPONSOR_SUPPLIED,
        )

    with pytest.raises(PolicyForbiddenError):
        service.reset_one(
            _director(),
            original.policy_id,
            expected_catalogue_version=service.catalogue().version,
            expected_rule_version=original.version,
        )
    retained = service.get(original.policy_id)
    assert retained.value == policy.StringPolicyValue(value="Singapore")
    assert retained.authority == policy.PolicyAuthority.SPONSOR_DOCUMENTED


def test_xpi_mapper_uses_canonical_fields_and_case_bound_target_policy() -> None:
    mapper_module = importlib.import_module("app.mappers.goldtier_xpi")
    mapper = mapper_module.GoldTierXpiRequestMapper()
    submission = _sandbox_submission()

    search = mapper.build_search_request(submission)
    assert search.query_items() == (
        ("legalName", "FYP ZERO TOUCH SME SYNTHETIC"),
        ("countryOfIncorporation", "SG"),
    )
    shell = mapper.build_shell_request(submission)
    payload = shell.model_dump(by_alias=True, exclude_none=True)
    assert payload["legalName"] == "FYP ZERO TOUCH SME SYNTHETIC"
    assert payload["systemReference"] == {
        "customerExternalSystem": "SPONSOR VALUE",
        "customerExternalSystemKey": "FYP-SYNTHETIC-001",
    }
    assert payload["registration"] == {
        "registrationType": "SPONSOR VALUE",
        "countryIso2": "SG",
        "registrationNumber": "202400001A",
    }
    assert "contact" not in payload
    assert "groupCompanyName" not in payload

    policy_request = mapper.build_policy_request(submission, "12345")
    assert policy_request.model_dump(by_alias=True) == {
        "customerExternalSystem": "SPONSOR VALUE",
        "customerExternalSystemKey": "FYP-SYNTHETIC-001",
        "goldTierId": "12345",
        "policy": "SPONSOR VALUE",
        "bookingEntity": "SPONSOR VALUE",
        "accountEntityType": "SPONSOR VALUE",
        "productType": "SPONSOR VALUE",
    }
    assert mapper.build_amend_request(submission, "12345").model_dump(
        by_alias=True, exclude_none=True
    ) == {"goldTierId": "12345", "policy": "SPONSOR VALUE"}


def test_xpi_mapper_blocks_missing_target_enrichment_before_request_construction() -> None:
    mapper_module = importlib.import_module("app.mappers.goldtier_xpi")
    mapper = mapper_module.GoldTierXpiRequestMapper()
    submission = _sandbox_submission(ready=False)

    with pytest.raises(mapper_module.MissingTargetEnrichmentError) as caught:
        mapper.build_shell_request(submission)

    assert "SPONSOR VALUE" not in str(caught.value)
    assert caught.value.missing_fields == (
        "kycCustomerType",
        "clientSegment",
        "customerExternalSystem",
        "registrationType",
        "policy",
        "bookingEntity",
    )


def test_xpi_mapper_emits_empty_optional_fields_without_treating_them_as_blockers() -> None:
    policy = importlib.import_module("app.domain.policy")
    mapper_module = importlib.import_module("app.mappers.goldtier_xpi")
    submission = _sandbox_submission().model_copy(
        update={
            "target_policy": _sandbox_submission().target_policy.model_copy(
                update={
                    "account_entity_type": policy.AuthorityLabelledTargetValue(
                        value="PROJECT_DEFINED_PROVISIONAL",
                        authority=policy.PolicyAuthority.PROJECT_DEFINED_PROVISIONAL,
                    ),
                    "product_type": policy.AuthorityLabelledTargetValue(
                        value="TBD_SPONSOR",
                        authority=policy.PolicyAuthority.TBD_SPONSOR,
                    ),
                }
            )
        }
    )

    mapper = mapper_module.GoldTierXpiRequestMapper()
    request = mapper.build_policy_request(submission, "12345")
    preview = mapper.build_preview(submission)
    policy_preview = next(item for item in preview.operations if item.operation == "POLICY")
    optional_fields = {
        item.target_field: item
        for item in policy_preview.fields
        if item.target_field in {"accountEntityType", "productType"}
    }

    assert request.model_dump(by_alias=True)["accountEntityType"] == ""
    assert request.model_dump(by_alias=True)["productType"] == ""
    assert preview.dispatch_ready is True
    assert all(item.required is False for item in optional_fields.values())
    assert all(item.missing is False for item in optional_fields.values())


def test_request_preview_is_network_free_authority_labelled_and_policy_versioned() -> None:
    mapper_module = importlib.import_module("app.mappers.goldtier_xpi")
    preview = mapper_module.GoldTierXpiRequestMapper().build_preview(
        _sandbox_submission(ready=False)
    )

    assert preview.environment == "SANDBOX"
    assert preview.policy_version == 42
    assert preview.dispatch_ready is False
    shell = next(item for item in preview.operations if item.operation == "SHELL")
    fields = {item.target_field: item for item in shell.fields}
    assert fields["legalName"].provenance == "CANONICAL_EVIDENCE"
    assert fields["legalName"].authority == "CANONICAL_EVIDENCE"
    assert fields["kycCustomerType"].provenance == "POLICY"
    assert fields["kycCustomerType"].authority == "TBD_SPONSOR"
    assert fields["kycCustomerType"].missing is True
    assert "user_id" not in preview.model_dump_json()


def _xpi_connector(
    transport: FakeXpiTransport,
    *,
    allow_writes: bool = True,
) -> object:
    module = importlib.import_module("app.connectors.goldtier_xpi")
    return module.GoldTierXpiSandboxConnector(
        connection=module.GoldTierXpiSandboxConnection(
            base_url="https://sandbox.goldtier.invalid",
            environment="synthetic",
            user_id=SecretStr("backend-only-user"),
            timeout_seconds=7.5,
            max_response_bytes=4096,
            allow_writes=allow_writes,
        ),
        transport=transport,
    )


def _metadata() -> object:
    models = importlib.import_module("app.connectors.goldtier_models")
    return models.GoldTierRequestMetadata(
        correlation_id=UUID("00000000-0000-4000-8000-000000000003"),
        source_case_id="SYNTHETIC-CASE-001",
        idempotency_key=UUID("00000000-0000-4000-8000-000000000011"),
    )


def _xpi_onboarding_service(
    transport: FakeXpiTransport,
    *,
    target_ready: bool = True,
    target_policy_override: object | None = None,
    acra_connector: object | None = None,
    reviewed_test_enrichment: bool = True,
) -> object:
    onboarding = importlib.import_module("app.services.onboarding")
    intelligence = importlib.import_module("app.services.onboarding_intelligence")
    mock_acra = importlib.import_module("app.connectors.mock_acra")
    repository = importlib.import_module("app.services.repository")
    mapper_type = importlib.import_module("app.mappers.goldtier_xpi").GoldTierXpiRequestMapper

    class ReviewedSyntheticEnrichmentMapper(mapper_type):
        """Explicit synthetic enrichment for retained optional-Amend test cases."""

        def build_amend_request(self, submission, party_id):
            return (
                super()
                .build_amend_request(submission, party_id)
                .model_copy(update={"group_company_name": "SYNTHETIC TEST GROUP"})
            )

    mapper = ReviewedSyntheticEnrichmentMapper() if reviewed_test_enrichment else mapper_type()
    policy_service = PolicyManagementService(InMemoryPolicyRepository())
    target_policy = (
        target_policy_override
        if target_policy_override is not None
        else _sandbox_submission(ready=target_ready).target_policy
    )
    snapshot = policy_service.case_snapshot().model_copy(
        update={"goldtier_target": target_policy},
        deep=True,
    )
    return onboarding.OnboardingService(
        acra=acra_connector or mock_acra.MockAcraConnector(),
        goldtier=_xpi_connector(transport),
        goldtier_mapper=mapper,
        entity_resolver=intelligence.OnboardingIntelligenceService(),
        repository=repository.InMemoryOnboardingCaseRepository(),
        policy_snapshot_provider=lambda: snapshot,
    )


def _confirm_service_submission(service: object, submission: object) -> None:
    case = service.get_case(submission.case_id)
    assert case is not None
    service.confirm_target_dispatch(
        case_id=case.case_id,
        actor_id="sandbox-test-operator",
        expected_case_event_count=len(case.events),
        clm_version=None,
        destination="GOLDTIER_XPI_SANDBOX",
    )


def test_xpi_connection_builds_exact_paths_and_query_encoding() -> None:
    module = importlib.import_module("app.connectors.goldtier_xpi")
    models = _xpi_models()
    connection = module.GoldTierXpiSandboxConnection(
        base_url="https://sandbox.goldtier.invalid/",
        environment="synthetic",
        user_id=SecretStr("backend-only-user"),
    )

    assert connection.search_endpoint(
        models.XpiCustomerSearchRequest(
            legal_name="FYP & ZERO/TOUCH", country_of_incorporation="SG"
        )
    ) == (
        "https://sandbox.goldtier.invalid/synthetic/gt-xpi/v1/customers/search"
        "?legalName=FYP+%26+ZERO%2FTOUCH&countryOfIncorporation=SG"
    )
    assert connection.operation_endpoint("SHELL") == (
        "https://sandbox.goldtier.invalid/synthetic/gt-xpi/v1/customers/create"
    )


def test_xpi_search_projects_no_match_unique_and_multiple_results_without_raw_retention() -> None:
    module = importlib.import_module("app.connectors.goldtier_xpi")
    models = _xpi_models()
    request = models.XpiCustomerSearchRequest(
        legal_name="FYP ZERO TOUCH SME SYNTHETIC",
        country_of_incorporation="SG",
    )
    candidate = {
        "goldTierId": 12345,
        "legalName": "FYP ZERO TOUCH SME SYNTHETIC",
        "countryOfIncorporation": "SG",
        "registrationNumber": "202400001A",
        "ignoredProviderField": "never retained",
    }
    transport = FakeXpiTransport(
        [
            module.GoldTierXpiHttpResponse(status_code=200, body=[]),
            module.GoldTierXpiHttpResponse(status_code=200, body=[candidate]),
            module.GoldTierXpiHttpResponse(
                status_code=200,
                body=[candidate, {**candidate, "goldTierId": 67890}],
            ),
        ]
    )
    connector = _xpi_connector(transport)

    no_match = connector.search_party(request, _metadata())
    unique = connector.search_party(request, _metadata())
    multiple = connector.search_party(request, _metadata())

    assert no_match.outcome == "NO_MATCH"
    assert no_match.candidates == ()
    assert unique.outcome == "MATCH_FOUND"
    assert unique.matched_party_id == "12345"
    assert unique.candidates[0].registration_number == "202400001A"
    assert "ignoredProviderField" not in unique.model_dump_json()
    assert multiple.outcome == "MULTIPLE_MATCHES"
    assert len(multiple.candidates) == 2
    assert transport.calls[0]["headers"] == {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "user_id": "backend-only-user",
        "X-Correlation-Id": "00000000-0000-4000-8000-000000000003",
    }
    assert "backend-only-user" not in repr(connector)


def test_xpi_search_maps_400_500_and_malformed_results_safely() -> None:
    module = importlib.import_module("app.connectors.goldtier_xpi")
    models = _xpi_models()
    request = models.XpiCustomerSearchRequest(legal_name="SYNTHETIC")
    transport = FakeXpiTransport(
        [
            module.GoldTierXpiHttpResponse(status_code=400, body={"private": "detail"}),
            module.GoldTierXpiHttpResponse(status_code=500, body={"private": "detail"}),
            module.GoldTierXpiHttpResponse(status_code=200, body={"unexpected": "shape"}),
        ]
    )
    connector = _xpi_connector(transport)

    invalid = connector.search_party(request, _metadata())
    unavailable = connector.search_party(request, _metadata())
    assert invalid.error_code == "GT_XPI_SEARCH_INVALID"
    assert unavailable.error_code == "GT_XPI_SERVICE_UNAVAILABLE"
    with pytest.raises(module.GoldTierXpiMalformedResponseError) as caught:
        connector.search_party(request, _metadata())
    assert "private" not in str(caught.value)


def test_xpi_customer_mutations_send_exact_shapes_and_map_safe_success() -> None:
    module = importlib.import_module("app.connectors.goldtier_xpi")
    mapper = importlib.import_module("app.mappers.goldtier_xpi").GoldTierXpiRequestMapper()
    submission = _sandbox_submission()
    transport = FakeXpiTransport(
        [
            module.GoldTierXpiHttpResponse(
                status_code=200,
                body={"goldTierId": 12345, "status": "provider-private-status"},
            ),
            module.GoldTierXpiHttpResponse(status_code=200, body={}),
            module.GoldTierXpiHttpResponse(status_code=200, body={}),
        ]
    )
    connector = _xpi_connector(transport)

    shell = connector.create_shell_customer(mapper.build_shell_request(submission), _metadata())
    policy = connector.create_policy(
        mapper.build_policy_request(submission, shell.party_id), _metadata()
    )
    amend = connector.amend_party(
        shell.party_id,
        mapper.build_amend_request(submission, shell.party_id),
        _metadata(),
    )

    assert (shell.party_id, shell.status) == ("12345", "SHELL_CREATED")
    assert policy.status == "POLICY_CREATED"
    assert policy.policy_id is None
    assert amend.status == "ENRICHED"
    assert [call["method"] for call in transport.calls] == ["POST", "POST", "POST"]
    assert transport.calls[0]["url"].endswith("/customers/create")
    assert transport.calls[1]["url"].endswith("/customers/createPolicy")
    assert transport.calls[2]["url"].endswith("/customers/amendCustomer")
    assert transport.calls[2]["json_body"] == {
        "goldTierId": "12345",
        "policy": "SPONSOR VALUE",
    }


def test_xpi_mutations_are_opt_in_and_timeout_is_non_replayable_uncertain_state() -> None:
    module = importlib.import_module("app.connectors.goldtier_xpi")
    mapper = importlib.import_module("app.mappers.goldtier_xpi").GoldTierXpiRequestMapper()
    request = mapper.build_shell_request(_sandbox_submission())
    disabled_transport = FakeXpiTransport()

    with pytest.raises(module.GoldTierXpiWritesDisabledError):
        _xpi_connector(disabled_transport, allow_writes=False).create_shell_customer(
            request, _metadata()
        )
    assert disabled_transport.calls == []

    http_request = httpx.Request("POST", "https://sandbox.goldtier.invalid")
    timed_out = _xpi_connector(
        FakeXpiTransport(error=httpx.ReadTimeout("private timeout", request=http_request))
    )
    with pytest.raises(module.GoldTierMutationOutcomeUncertainError) as caught:
        timed_out.create_shell_customer(request, _metadata())
    assert "private timeout" not in str(caught.value)


@pytest.mark.parametrize(
    "response_error_name",
    ["GoldTierXpiResponseTooLargeError", "GoldTierXpiResponseDecodeError"],
)
def test_post_dispatch_transport_response_errors_are_mutation_uncertain(
    response_error_name: str,
) -> None:
    module = importlib.import_module("app.connectors.goldtier_xpi")
    mapper = importlib.import_module("app.mappers.goldtier_xpi").GoldTierXpiRequestMapper()
    response_error = getattr(module, response_error_name)()
    connector = _xpi_connector(FakeXpiTransport(error=response_error))

    with pytest.raises(module.GoldTierMutationOutcomeUncertainError):
        connector.create_shell_customer(
            mapper.build_shell_request(_sandbox_submission()),
            _metadata(),
        )


def test_no_match_executes_customer_path_once_through_the_existing_target_ledger() -> None:
    module = importlib.import_module("app.connectors.goldtier_xpi")
    transport = FakeXpiTransport(
        [
            module.GoldTierXpiHttpResponse(status_code=200, body=[]),
            module.GoldTierXpiHttpResponse(status_code=200, body={"goldTierId": 12345}),
            module.GoldTierXpiHttpResponse(status_code=200, body={}),
            module.GoldTierXpiHttpResponse(status_code=200, body={}),
            module.GoldTierXpiHttpResponse(status_code=200, body=[{"goldTierId": 12345}]),
        ]
    )
    service = _xpi_onboarding_service(transport)
    case = service.create_staged_case("202400001A")
    submission = service.build_submission_input(case, provider_mode="SANDBOX")

    _confirm_service_submission(service, submission)
    receipt = service.execute_submission_input(submission)
    repeated = service.execute_submission_input(submission)

    assert receipt.classification == "SUCCESS"
    assert receipt.result.party_id == "12345"
    assert service.get_attempted_target_operations(submission.submission_id) == (
        "SEARCH",
        "SHELL",
        "POLICY",
        "AMEND",
        "READBACK",
    )
    assert repeated == receipt
    assert len(transport.calls) == 5
    assert transport.calls[-1]["url"].endswith("/customers/search?goldTierID=12345")


@pytest.mark.parametrize(
    "readback_body",
    [
        [],
        [{"goldTierId": 67890}],
        [{"goldTierId": 12345}, {"goldTierId": 67890}],
    ],
    ids=["no-match", "wrong-id", "multiple"],
)
def test_post_amend_readback_requires_one_exact_retained_customer(
    readback_body: list[dict[str, object]],
) -> None:
    module = importlib.import_module("app.connectors.goldtier_xpi")
    transport = FakeXpiTransport(
        [
            module.GoldTierXpiHttpResponse(status_code=200, body=[]),
            module.GoldTierXpiHttpResponse(status_code=200, body={"goldTierId": 12345}),
            module.GoldTierXpiHttpResponse(status_code=200, body={}),
            module.GoldTierXpiHttpResponse(status_code=200, body={}),
            module.GoldTierXpiHttpResponse(status_code=200, body=readback_body),
        ]
    )
    service = _xpi_onboarding_service(transport)
    case = service.create_staged_case("202400001A")
    submission = service.build_submission_input(case, provider_mode="SANDBOX")

    _confirm_service_submission(service, submission)
    receipt = service.execute_submission_input(submission)
    repeated = service.execute_submission_input(submission)

    assert receipt.classification == "REVIEW_REQUIRED"
    assert receipt.error is not None
    assert receipt.error.code == "GT_READBACK_IDENTITY_REVIEW_REQUIRED"
    assert repeated == receipt
    assert service.get_attempted_target_operations(submission.submission_id) == (
        "SEARCH",
        "SHELL",
        "POLICY",
        "AMEND",
        "READBACK",
    )
    assert len(transport.calls) == 5


def test_unique_exact_match_uses_existing_party_path_without_shell() -> None:
    module = importlib.import_module("app.connectors.goldtier_xpi")
    transport = FakeXpiTransport(
        [
            module.GoldTierXpiHttpResponse(
                status_code=200,
                body=[
                    {
                        "goldTierId": 12345,
                        "legalName": "MERLION CIRCULAR LABS PTE. LTD.",
                        "countryOfIncorporation": "SG",
                        "registrationNumber": "202400001A",
                    }
                ],
            ),
            module.GoldTierXpiHttpResponse(status_code=200, body={}),
            module.GoldTierXpiHttpResponse(status_code=200, body=[{"goldTierId": 12345}]),
        ]
    )
    service = _xpi_onboarding_service(transport)
    case = service.create_staged_case("202400001A")
    submission = service.build_submission_input(case, provider_mode="SANDBOX")

    _confirm_service_submission(service, submission)
    receipt = service.execute_submission_input(submission)

    assert receipt.classification == "SUCCESS"
    assert receipt.result.party_id == "12345"
    assert receipt.result.shell_status == "EXISTING_PARTY_REUSED"
    assert service.get_attempted_target_operations(submission.submission_id) == (
        "SEARCH",
        "AMEND",
        "READBACK",
    )
    assert not any(call["url"].endswith("/customers/create") for call in transport.calls)
    assert not any(call["url"].endswith("/customers/createPolicy") for call in transport.calls)


@pytest.mark.parametrize(
    "candidates",
    [
        [
            {
                "goldTierId": 12345,
                "legalName": "MERLION CIRCULAR LABS PTE. LTD.",
                "countryOfIncorporation": "SG",
                "registrationNumber": "202400001A",
            },
            {
                "goldTierId": 67890,
                "legalName": "MERLION CIRCULAR LABS PTE. LTD.",
                "countryOfIncorporation": "SG",
                "registrationNumber": "202400001A",
            },
        ],
        [
            {
                "goldTierId": 12345,
                "legalName": "MERLION CIRCULAR LABS PTE. LTD.",
                "countryOfIncorporation": "SG",
            }
        ],
        [
            {
                "goldTierId": 12345,
                "legalName": "MERLION CIRCULAR LABS PTE. LTD.",
                "countryOfIncorporation": "SG",
                "registrationNumber": "CONFLICTING-ID",
            }
        ],
    ],
    ids=["multiple", "probable", "hard-identifier-conflict"],
)
def test_non_exact_candidates_require_review_with_zero_shell_calls(
    candidates: list[dict[str, object]],
) -> None:
    module = importlib.import_module("app.connectors.goldtier_xpi")
    transport = FakeXpiTransport([module.GoldTierXpiHttpResponse(status_code=200, body=candidates)])
    service = _xpi_onboarding_service(transport)
    case = service.create_staged_case("202400001A")
    submission = service.build_submission_input(case, provider_mode="SANDBOX")

    _confirm_service_submission(service, submission)
    receipt = service.execute_submission_input(submission)

    assert receipt.classification == "REVIEW_REQUIRED"
    assert service.get_attempted_target_operations(submission.submission_id) == ("SEARCH",)
    assert len(transport.calls) == 1


def test_missing_target_enrichment_blocks_before_any_network_or_ledger_attempt() -> None:
    transport = FakeXpiTransport()
    service = _xpi_onboarding_service(transport, target_ready=False)
    case = service.create_staged_case("202400001A")
    submission = service.build_submission_input(case, provider_mode="SANDBOX")

    with pytest.raises(ValueError, match="target enrichment"):
        service.execute_submission_input(submission)

    assert transport.calls == []
    assert service.get_execution_state(submission.submission_id) == "NOT_STARTED"


@pytest.mark.parametrize("value", ["   ", "\t", "SPONSOR\nVALUE"])
def test_unusable_target_policy_text_is_rejected_at_policy_boundaries(value: str) -> None:
    policy = importlib.import_module("app.domain.policy")

    with pytest.raises(ValidationError):
        policy.StringPolicyValue(value=value)
    with pytest.raises(ValidationError):
        policy.AuthorityLabelledTargetValue(
            value=value,
            authority=policy.PolicyAuthority.SPONSOR_SUPPLIED,
        )


def test_corrupted_case_bound_target_policy_blocks_preview_and_execution_before_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    policy = importlib.import_module("app.domain.policy")
    valid_target = _sandbox_submission().target_policy
    assert valid_target is not None
    unusable = policy.AuthorityLabelledTargetValue.model_construct(
        value="   ",
        authority=policy.PolicyAuthority.SPONSOR_SUPPLIED,
    )
    corrupted_target = valid_target.model_copy(
        update={"kyc_customer_type": unusable},
        deep=True,
    )
    transport = FakeXpiTransport()
    service = _xpi_onboarding_service(
        transport,
        target_policy_override=corrupted_target,
    )
    with pytest.raises(ValidationError):
        service.create_staged_case("202400001A")
    assert transport.calls == []
    service = _xpi_onboarding_service(transport, target_policy_override=valid_target)
    case = service.create_staged_case("202400001A")
    corrupted_case = case.model_copy(
        update={
            "policy_snapshot": case.policy_snapshot.model_copy(
                update={"goldtier_target": corrupted_target}, deep=True
            )
        },
        deep=True,
    )
    original_get = service._repository.get
    # Fault-inject a read without allowing malformed content through validated writes.
    monkeypatch.setattr(
        service._repository,
        "get",
        lambda case_id: (
            corrupted_case.model_copy(deep=True)
            if case_id == case.case_id
            else original_get(case_id)
        ),
    )
    case = corrupted_case
    submission = service.build_submission_input(case, provider_mode="SANDBOX")

    preview = service.build_request_preview(case, provider_mode="SANDBOX")
    with pytest.raises(ValueError, match="target enrichment"):
        service.execute_submission_input(submission)

    assert preview.dispatch_ready is False
    assert transport.calls == []
    assert service.get_execution_state(submission.submission_id) == "NOT_STARTED"


@pytest.mark.parametrize("substitution", ["policy", "catalogue_version"])
def test_submission_target_policy_must_match_the_owning_case_snapshot(
    substitution: str,
) -> None:
    policy = importlib.import_module("app.domain.policy")
    transport = FakeXpiTransport()
    service = _xpi_onboarding_service(transport)
    case = service.create_staged_case("202400001A")
    submission = service.build_submission_input(case, provider_mode="SANDBOX")
    if substitution == "policy":
        assert submission.target_policy is not None
        replacement = policy.AuthorityLabelledTargetValue(
            value="DIFFERENT SPONSOR VALUE",
            authority=policy.PolicyAuthority.SPONSOR_SUPPLIED,
        )
        replaced_policy = submission.target_policy.model_copy(
            update={"policy": replacement},
            deep=True,
        )
        tampered = submission.model_copy(update={"target_policy": replaced_policy})
    else:
        tampered = submission.model_copy(
            update={"policy_catalogue_version": submission.policy_catalogue_version + 1}
        )

    with pytest.raises(ValueError, match="owning case policy snapshot"):
        service.execute_submission_input(tampered)

    assert transport.calls == []
    assert service.get_execution_state(submission.submission_id) == "NOT_STARTED"


def test_uncertain_shell_attempt_remains_in_progress_and_cannot_replay() -> None:
    module = importlib.import_module("app.connectors.goldtier_xpi")
    request = httpx.Request("POST", "https://sandbox.goldtier.invalid")

    class SearchThenTimeout(FakeXpiTransport):
        def request(self, method: str, url: str, **kwargs: object) -> object:
            if method == "GET":
                self.calls.append({"method": method, "url": url, **kwargs})
                return module.GoldTierXpiHttpResponse(status_code=200, body=[])
            self.calls.append({"method": method, "url": url, **kwargs})
            raise httpx.ReadTimeout("private timeout", request=request)

    transport = SearchThenTimeout()
    service = _xpi_onboarding_service(transport)
    case = service.create_staged_case("202400001A")
    submission = service.build_submission_input(case, provider_mode="SANDBOX")

    _confirm_service_submission(service, submission)
    with pytest.raises(Exception, match="uncertain"):
        service.execute_submission_input(submission)
    call_count = len(transport.calls)
    with pytest.raises(RuntimeError, match="already in progress") as replay:
        service.execute_submission_input(submission)

    assert service.get_execution_state(submission.submission_id) == "IN_PROGRESS"
    assert service.is_execution_outcome_uncertain(submission.submission_id) is True
    assert len(transport.calls) == call_count
    _assert_no_mock_provider_claim([str(replay.value)])


def test_provider_verified_recovery_resolves_uncertain_shell_without_replay() -> None:
    module = importlib.import_module("app.connectors.goldtier_xpi")
    target = importlib.import_module("app.domain.target_submission")
    timeout_request = httpx.Request("POST", "https://sandbox.goldtier.invalid")
    transport = FakeXpiTransport(
        [
            httpx.ReadTimeout("private timeout", request=timeout_request),
        ]
    )
    service = _xpi_onboarding_service(transport)
    case = service.create_staged_case("202400001A")
    submission = service.build_submission_input(case, provider_mode="SANDBOX")

    _confirm_service_submission(service, submission)
    with pytest.raises(Exception, match="uncertain"):
        service.advance_incremental_submission_input(
            submission,
            search_resolution=target.GoldTierSearchResolution.NO_MATCH,
            selected_party_id=None,
        )

    transport.responses.append(
        module.GoldTierXpiHttpResponse(
            status_code=200,
            body=[{"goldTierId": 12345, "legalName": case.entity.legal_name}],
        )
    )
    recovered = service.recover_uncertain_shell_from_provider(
        submission_input=submission,
        recovered_party_id="12345",
        legal_name=case.entity.legal_name,
        registration_number=case.requested_uen,
        country_of_incorporation=case.entity.country_of_incorporation,
        actor_id="director-test",
        origin=target.GoldTierRecoveryOrigin.UNCERTAIN_DURABLE_LEDGER,
    )
    repeated = service.recover_uncertain_shell_from_provider(
        submission_input=submission,
        recovered_party_id="12345",
        legal_name=case.entity.legal_name,
        registration_number=case.requested_uen,
        country_of_incorporation=case.entity.country_of_incorporation,
        actor_id="director-test",
        origin=target.GoldTierRecoveryOrigin.UNCERTAIN_DURABLE_LEDGER,
    )

    assert repeated == recovered
    assert tuple(item.value for item in recovered.attempted_operations) == ("SEARCH", "SHELL")
    assert tuple(item.value for item in recovered.definitively_completed_operations) == ("SEARCH",)
    assert tuple(item.value for item in recovered.lifecycle_resolved_operations) == (
        "SEARCH",
        "SHELL",
    )
    assert recovered.provider_verified_recovery is not None
    assert recovered.provider_verified_recovery.replayed is False
    assert [call["method"] for call in transport.calls] == ["POST", "GET"]
    recovered_case = service.get_case(case.case_id)
    assert recovered_case is not None
    assert recovered_case.state == "GT_SHELL_CREATED"
    assert recovered_case.goldtier_result is not None
    assert recovered_case.goldtier_result.party_id == "12345"
    assert recovered_case.goldtier_result.shell_status == "PROVIDER_VERIFIED_RECOVERY"
    assert recovered_case.events[-1].code == "GT_SHELL_PROVIDER_VERIFIED_RECOVERY"
    assert "uncertain" in recovered_case.events[-1].message
    assert "without replay" in recovered_case.events[-1].message

    transport.responses.extend(
        [
            module.GoldTierXpiHttpResponse(status_code=200, body={}),
            module.GoldTierXpiHttpResponse(status_code=200, body={}),
            module.GoldTierXpiHttpResponse(status_code=200, body=[{"goldTierId": 12345}]),
        ]
    )
    assert (
        service.advance_incremental_submission_input(
            submission,
            search_resolution=target.GoldTierSearchResolution.NO_MATCH,
            selected_party_id=None,
        )
        is None
    )
    assert (
        service.advance_incremental_submission_input(
            submission,
            search_resolution=target.GoldTierSearchResolution.NO_MATCH,
            selected_party_id=None,
        )
        is None
    )
    receipt = service.advance_incremental_submission_input(
        submission,
        search_resolution=target.GoldTierSearchResolution.NO_MATCH,
        selected_party_id=None,
    )
    assert receipt is not None
    assert receipt.classification == "SUCCESS"
    assert [call["method"] for call in transport.calls] == [
        "POST",
        "GET",
        "POST",
        "POST",
        "GET",
    ]


def _uncertain_policy_fixture() -> tuple[object, object, object, FakeXpiTransport]:
    errors = importlib.import_module("app.connectors.errors")
    module = importlib.import_module("app.connectors.goldtier_xpi")
    target = importlib.import_module("app.domain.target_submission")
    timeout_request = httpx.Request("POST", "https://sandbox.goldtier.invalid")
    transport = FakeXpiTransport(
        [
            httpx.ReadTimeout("private timeout", request=timeout_request),
        ]
    )
    service = _xpi_onboarding_service(transport)
    case = service.create_staged_case("202400001A")
    submission = service.build_submission_input(case, provider_mode="SANDBOX")
    _confirm_service_submission(service, submission)
    with pytest.raises(errors.MutationOutcomeUncertainError):
        service.advance_incremental_submission_input(
            submission,
            search_resolution=target.GoldTierSearchResolution.NO_MATCH,
            selected_party_id=None,
        )
    transport.responses.extend(
        [
            module.GoldTierXpiHttpResponse(
                status_code=200,
                body=[{"goldTierId": 12345, "legalName": case.entity.legal_name}],
            ),
            httpx.ReadTimeout("private timeout", request=timeout_request),
        ]
    )
    service.recover_uncertain_shell_from_provider(
        submission_input=submission,
        recovered_party_id="12345",
        legal_name=case.entity.legal_name,
        registration_number=case.requested_uen,
        country_of_incorporation=case.entity.country_of_incorporation,
        actor_id="director-test",
        origin=target.GoldTierRecoveryOrigin.UNCERTAIN_DURABLE_LEDGER,
    )
    with pytest.raises(errors.MutationOutcomeUncertainError):
        service.advance_incremental_submission_input(
            submission,
            search_resolution=target.GoldTierSearchResolution.NO_MATCH,
            selected_party_id=None,
        )
    return service, case, submission, transport


def test_policy_provider_recovery_preserves_uncertainty_and_never_replays_policy() -> None:
    errors = importlib.import_module("app.connectors.errors")
    module = importlib.import_module("app.connectors.goldtier_xpi")
    target = importlib.import_module("app.domain.target_submission")
    service, case, submission, transport = _uncertain_policy_fixture()
    assert submission.target_policy is not None
    call_count = len(transport.calls)

    with pytest.raises(errors.MutationOutcomeUncertainError):
        service.advance_incremental_submission_input(
            submission,
            search_resolution=target.GoldTierSearchResolution.NO_MATCH,
            selected_party_id=None,
        )
    assert len(transport.calls) == call_count

    recovered = service.recover_uncertain_policy_from_provider(
        submission_input=submission,
        recovered_party_id="12345",
        legal_name=case.entity.legal_name,
        registration_number=case.requested_uen,
        country_of_incorporation=case.entity.country_of_incorporation,
        provider_policy=submission.target_policy.policy.value,
        provider_policy_status="Requested",
        actor_id="director-test",
        origin=target.GoldTierRecoveryOrigin.UNCERTAIN_DURABLE_LEDGER,
    )
    repeated = service.recover_uncertain_policy_from_provider(
        submission_input=submission,
        recovered_party_id="12345",
        legal_name=case.entity.legal_name,
        registration_number=case.requested_uen,
        country_of_incorporation=case.entity.country_of_incorporation,
        provider_policy=submission.target_policy.policy.value,
        provider_policy_status="Requested",
        actor_id="director-test",
        origin=target.GoldTierRecoveryOrigin.UNCERTAIN_DURABLE_LEDGER,
    )

    assert repeated == recovered
    assert len(transport.calls) == call_count
    assert tuple(item.value for item in recovered.attempted_operations) == (
        "SEARCH",
        "SHELL",
        "POLICY",
    )
    assert tuple(item.value for item in recovered.definitively_completed_operations) == ("SEARCH",)
    assert tuple(item.value for item in recovered.lifecycle_resolved_operations) == (
        "SEARCH",
        "SHELL",
        "POLICY",
    )
    policy_recovery = recovered.provider_verified_policy_recovery
    assert policy_recovery is not None
    assert policy_recovery.original_outcome_uncertain is True
    assert policy_recovery.replayed is False
    assert policy_recovery.provider_policy == submission.target_policy.policy.value
    assert policy_recovery.provider_policy_status == "Requested"
    recovered_case = service.get_case(case.case_id)
    assert recovered_case is not None
    assert recovered_case.state == "GT_POLICY_CREATED"
    assert recovered_case.goldtier_result is not None
    assert recovered_case.goldtier_result.policy_status == "PROVIDER_VERIFIED_REQUESTED"
    assert recovered_case.events[-1].code == "GT_POLICY_PROVIDER_VERIFIED_RECOVERY"

    transport.responses.extend(
        [
            module.GoldTierXpiHttpResponse(status_code=200, body={}),
            module.GoldTierXpiHttpResponse(status_code=200, body=[{"goldTierId": 12345}]),
        ]
    )
    assert (
        service.advance_incremental_submission_input(
            submission,
            search_resolution=target.GoldTierSearchResolution.NO_MATCH,
            selected_party_id=None,
        )
        is None
    )
    receipt = service.advance_incremental_submission_input(
        submission,
        search_resolution=target.GoldTierSearchResolution.NO_MATCH,
        selected_party_id=None,
    )
    assert receipt is not None and receipt.classification == "SUCCESS"
    policy_calls = [
        call for call in transport.calls if str(call["url"]).endswith("/customers/createPolicy")
    ]
    amend_calls = [
        call for call in transport.calls if str(call["url"]).endswith("/customers/amendCustomer")
    ]
    assert len(policy_calls) == 1
    assert len(amend_calls) == 1


def test_provider_verified_amend_failure_is_durable_state_and_never_replayed() -> None:
    errors = importlib.import_module("app.connectors.errors")
    target = importlib.import_module("app.domain.target_submission")
    service, case, submission, transport = _uncertain_policy_fixture()
    assert submission.target_policy is not None
    service.recover_uncertain_policy_from_provider(
        submission_input=submission,
        recovered_party_id="12345",
        legal_name=case.entity.legal_name,
        registration_number=case.requested_uen,
        country_of_incorporation=case.entity.country_of_incorporation,
        provider_policy=submission.target_policy.policy.value,
        provider_policy_status="Requested",
        actor_id="director-test",
        origin=target.GoldTierRecoveryOrigin.UNCERTAIN_DURABLE_LEDGER,
    )
    timeout_request = httpx.Request("POST", "https://sandbox.goldtier.invalid")
    transport.responses.append(httpx.ReadTimeout("private timeout", request=timeout_request))

    with pytest.raises(errors.MutationOutcomeUncertainError):
        service.advance_incremental_submission_input(
            submission,
            search_resolution=target.GoldTierSearchResolution.NO_MATCH,
            selected_party_id=None,
        )
    call_count = len(transport.calls)

    failed = service.recover_uncertain_amend_failure_from_provider(
        submission_input=submission,
        recovered_party_id="12345",
        provider_status=target.GoldTierProviderFailureStatus.PROVIDER_VALIDATION_FAILED,
        provider_status_evidence="Valdiation Failed",
        actor_id="director-test",
        origin=target.GoldTierRecoveryOrigin.UNCERTAIN_DURABLE_LEDGER,
    )
    repeated = service.recover_uncertain_amend_failure_from_provider(
        submission_input=submission,
        recovered_party_id="12345",
        provider_status=target.GoldTierProviderFailureStatus.PROVIDER_VALIDATION_FAILED,
        provider_status_evidence="Valdiation Failed",
        actor_id="director-test",
        origin=target.GoldTierRecoveryOrigin.UNCERTAIN_DURABLE_LEDGER,
    )

    assert repeated == failed
    assert len(transport.calls) == call_count
    assert tuple(item.value for item in failed.attempted_operations) == (
        "SEARCH",
        "SHELL",
        "POLICY",
        "AMEND",
    )
    assert tuple(item.value for item in failed.lifecycle_resolved_operations) == (
        "SEARCH",
        "SHELL",
        "POLICY",
    )
    assert target.GoldTierOperationMarker.AMEND not in (failed.definitively_completed_operations)
    amend_failure = failed.provider_verified_amend_failure
    assert amend_failure is not None
    assert amend_failure.operation == target.GoldTierOperationMarker.AMEND
    assert amend_failure.original_outcome_uncertain is True
    assert amend_failure.provider_reconciliation == "PROVIDER_VERIFIED_FAILURE"
    assert amend_failure.provider_status == "PROVIDER_VALIDATION_FAILED"
    assert amend_failure.provider_status_evidence == "Valdiation Failed"
    assert amend_failure.replayed is False
    assert service.is_execution_outcome_uncertain(submission.submission_id) is True

    with pytest.raises(ValueError, match="provider-verified failure"):
        service.advance_incremental_submission_input(
            submission,
            search_resolution=target.GoldTierSearchResolution.NO_MATCH,
            selected_party_id=None,
        )
    assert len(transport.calls) == call_count


@pytest.mark.parametrize(
    ("recovered_party_id", "provider_policy", "expected_error"),
    [
        ("99999", "Singapore", "exactly match"),
        ("12345", "Australia", "does not match the case policy"),
    ],
)
def test_policy_provider_recovery_rejects_wrong_id_or_policy_without_network(
    recovered_party_id: str,
    provider_policy: str,
    expected_error: str,
) -> None:
    target = importlib.import_module("app.domain.target_submission")
    service, case, submission, transport = _uncertain_policy_fixture()
    call_count = len(transport.calls)

    with pytest.raises(ValueError, match=expected_error):
        service.recover_uncertain_policy_from_provider(
            submission_input=submission,
            recovered_party_id=recovered_party_id,
            legal_name=case.entity.legal_name,
            registration_number=case.requested_uen,
            country_of_incorporation=case.entity.country_of_incorporation,
            provider_policy=provider_policy,
            provider_policy_status="Requested",
            actor_id="director-test",
            origin=target.GoldTierRecoveryOrigin.UNCERTAIN_DURABLE_LEDGER,
        )
    assert len(transport.calls) == call_count


def test_policy_provider_recovery_rejects_wrong_case_without_network() -> None:
    target = importlib.import_module("app.domain.target_submission")
    service, case, submission, transport = _uncertain_policy_fixture()
    other = service.create_staged_case("202400001A")
    other_submission = service.build_submission_input(other, provider_mode="SANDBOX")
    call_count = len(transport.calls)

    with pytest.raises(ValueError, match="exactly match"):
        service.recover_uncertain_policy_from_provider(
            submission_input=other_submission,
            recovered_party_id="12345",
            legal_name=case.entity.legal_name,
            registration_number=case.requested_uen,
            country_of_incorporation=case.entity.country_of_incorporation,
            provider_policy=submission.target_policy.policy.value,
            provider_policy_status="Requested",
            actor_id="director-test",
            origin=target.GoldTierRecoveryOrigin.UNCERTAIN_DURABLE_LEDGER,
        )
    assert len(transport.calls) == call_count


def test_provider_verified_recovery_rejects_wrong_uen_before_provider_call() -> None:
    target = importlib.import_module("app.domain.target_submission")
    transport = FakeXpiTransport()
    service = _xpi_onboarding_service(transport)
    case = service.create_staged_case("202400001A")
    submission = service.build_submission_input(case, provider_mode="SANDBOX")

    with pytest.raises(ValueError, match="exactly match"):
        service.recover_uncertain_shell_from_provider(
            submission_input=submission,
            recovered_party_id="12345",
            legal_name=case.entity.legal_name,
            registration_number="WRONG-UEN",
            country_of_incorporation=case.entity.country_of_incorporation,
            actor_id="director-test",
            origin=target.GoldTierRecoveryOrigin.HISTORICAL_LOCAL_LEDGER_LOST,
        )

    assert transport.calls == []


@pytest.mark.parametrize(
    "provider_body",
    [
        [{"goldTierId": 67890, "legalName": "MERLION CIRCULAR LABS PTE. LTD."}],
        [
            {"goldTierId": 12345, "legalName": "MERLION CIRCULAR LABS PTE. LTD."},
            {"goldTierId": 67890, "legalName": "MERLION CIRCULAR LABS PTE. LTD."},
        ],
    ],
    ids=["name-only-wrong-id", "multiple-candidates"],
)
def test_provider_verified_recovery_rejects_non_exact_provider_evidence(
    provider_body: list[dict[str, object]],
) -> None:
    module = importlib.import_module("app.connectors.goldtier_xpi")
    target = importlib.import_module("app.domain.target_submission")
    transport = FakeXpiTransport(
        [module.GoldTierXpiHttpResponse(status_code=200, body=provider_body)]
    )
    service = _xpi_onboarding_service(transport)
    case = service.create_staged_case("202400001A")
    submission = service.build_submission_input(case, provider_mode="SANDBOX")

    with pytest.raises(ValueError, match="one exact target identity"):
        service.recover_uncertain_shell_from_provider(
            submission_input=submission,
            recovered_party_id="12345",
            legal_name=case.entity.legal_name,
            registration_number=case.requested_uen,
            country_of_incorporation=case.entity.country_of_incorporation,
            actor_id="director-test",
            origin=target.GoldTierRecoveryOrigin.HISTORICAL_LOCAL_LEDGER_LOST,
        )

    assert len(transport.calls) == 1
    assert transport.calls[0]["method"] == "GET"


def test_provider_verified_recovery_rejects_definitively_failed_shell() -> None:
    module = importlib.import_module("app.connectors.goldtier_xpi")
    target = importlib.import_module("app.domain.target_submission")
    transport = FakeXpiTransport(
        [
            module.GoldTierXpiHttpResponse(
                status_code=400,
                body={"errorCode": "GT_SHELL_FAILED"},
            )
        ]
    )
    service = _xpi_onboarding_service(transport)
    case = service.create_staged_case("202400001A")
    submission = service.build_submission_input(case, provider_mode="SANDBOX")
    _confirm_service_submission(service, submission)
    receipt = service.advance_incremental_submission_input(
        submission,
        search_resolution=target.GoldTierSearchResolution.NO_MATCH,
        selected_party_id=None,
    )
    call_count = len(transport.calls)

    assert receipt is not None and receipt.classification == "FAILED"
    with pytest.raises(ValueError, match="Only one uncertain Shell"):
        service.recover_uncertain_shell_from_provider(
            submission_input=submission,
            recovered_party_id="12345",
            legal_name=case.entity.legal_name,
            registration_number=case.requested_uen,
            country_of_incorporation=case.entity.country_of_incorporation,
            actor_id="director-test",
            origin=target.GoldTierRecoveryOrigin.UNCERTAIN_DURABLE_LEDGER,
        )
    assert len(transport.calls) == call_count


def test_provider_verified_recovery_rejects_conflicting_completed_target_id() -> None:
    target = importlib.import_module("app.domain.target_submission")
    transport = FakeXpiTransport()
    service = _xpi_onboarding_service(transport)
    case = service.create_staged_case("202400001A")
    submission = service.build_submission_input(case, provider_mode="SANDBOX")

    service._start_incremental_execution(  # noqa: SLF001 - adversarial retained-state setup
        submission,
        search_resolution=target.GoldTierSearchResolution.EXACT_MATCH,
        selected_party_id="99999",
    )
    with pytest.raises(ValueError, match="Only one uncertain Shell"):
        service.recover_uncertain_shell_from_provider(
            submission_input=submission,
            recovered_party_id="12345",
            legal_name=case.entity.legal_name,
            registration_number=case.requested_uen,
            country_of_incorporation=case.entity.country_of_incorporation,
            actor_id="director-test",
            origin=target.GoldTierRecoveryOrigin.UNCERTAIN_DURABLE_LEDGER,
        )
    assert transport.calls == []


def test_goldtier_first_exact_match_reuses_verified_target_state_and_skips_shell() -> None:
    module = importlib.import_module("app.connectors.goldtier_xpi")
    target = importlib.import_module("app.domain.target_submission")
    transport = FakeXpiTransport(
        [
            module.GoldTierXpiHttpResponse(status_code=200, body=[]),
            module.GoldTierXpiHttpResponse(status_code=200, body={"goldTierId": 12345}),
            module.GoldTierXpiHttpResponse(status_code=200, body={}),
            module.GoldTierXpiHttpResponse(status_code=200, body={}),
            module.GoldTierXpiHttpResponse(status_code=200, body=[{"goldTierId": 12345}]),
            module.GoldTierXpiHttpResponse(
                status_code=200,
                body=[
                    {
                        "goldTierId": 12345,
                        "legalName": "MERLION CIRCULAR LABS PTE. LTD.",
                    }
                ],
            ),
            module.GoldTierXpiHttpResponse(status_code=200, body={}),
            module.GoldTierXpiHttpResponse(status_code=200, body=[{"goldTierId": 12345}]),
        ]
    )
    service = _xpi_onboarding_service(transport)
    first = service.create_staged_case("202400001A")
    first_submission = service.build_submission_input(first, provider_mode="SANDBOX")
    _confirm_service_submission(service, first_submission)
    assert service.execute_submission_input(first_submission).classification == "SUCCESS"

    second = service.create_staged_case_with_identity(
        UUID("00000000-0000-4000-8000-000000000101"),
        UUID("00000000-0000-4000-8000-000000000102"),
        "202400001A",
        "SG",
        legal_name="MERLION CIRCULAR LABS PTE. LTD.",
    )

    assert second.state == "VALIDATED"
    assert second.registry_acquisition is not None
    assert second.entity == second.registry_acquisition.entity_profile
    assert second.existing_target_state is not None
    assert second.existing_target_state.target_party_id == "12345"
    assert second.initial_target_search is not None
    assert second.initial_target_search.disposition == "EXACT_MATCH"
    second_submission = service.build_submission_input(second, provider_mode="SANDBOX")
    _confirm_service_submission(service, second_submission)
    assert (
        service.advance_incremental_submission_input(
            second_submission,
            search_resolution=target.GoldTierSearchResolution.EXACT_MATCH,
            selected_party_id="12345",
        )
        is None
    )
    receipt = service.advance_incremental_submission_input(
        second_submission,
        search_resolution=target.GoldTierSearchResolution.EXACT_MATCH,
        selected_party_id="12345",
    )

    assert receipt is not None and receipt.classification == "SUCCESS"
    assert receipt.result is not None and receipt.result.party_id == "12345"
    assert receipt.result.policy_id is None
    assert receipt.result.policy_status is None
    assert service.get_attempted_target_operations(second_submission.submission_id) == (
        "SEARCH",
        "AMEND",
        "READBACK",
    )
    second_target_calls = transport.calls[-3:]
    assert [call["method"] for call in second_target_calls] == ["GET", "POST", "GET"]
    assert not any(
        call["url"].endswith(("/customers/create", "/customers/createPolicy"))
        for call in second_target_calls
    )


@pytest.mark.parametrize(
    ("search_body", "expected_state", "expected_acra_calls"),
    [
        ([], "VALIDATED", 4),
        (
            [
                {"goldTierId": 12345, "legalName": "GARDEN BUSINESS"},
                {"goldTierId": 67890, "legalName": "GARDEN BUSINESS"},
            ],
            "VALIDATED",
            4,
        ),
    ],
    ids=["no-match-acra", "ambiguous-no-acra"],
)
def test_goldtier_first_branch_controls_acra_bootstrap(
    search_body: list[dict[str, object]],
    expected_state: str,
    expected_acra_calls: int,
) -> None:
    module = importlib.import_module("app.connectors.goldtier_xpi")
    mock_acra = importlib.import_module("app.connectors.mock_acra")

    class CountingAcra(mock_acra.MockAcraConnector):
        def __init__(self) -> None:
            super().__init__()
            self.calls = 0

        def fetch_company(self, uen: str) -> object:
            self.calls += 1
            return super().fetch_company(uen)

        def fetch_officers(self, uen: str) -> object:
            self.calls += 1
            return super().fetch_officers(uen)

        def fetch_ownership_parties(self, uen: str) -> object:
            self.calls += 1
            return super().fetch_ownership_parties(uen)

        def fetch_relationships(self, uen: str) -> object:
            self.calls += 1
            return super().fetch_relationships(uen)

    acra = CountingAcra()
    transport = FakeXpiTransport(
        [module.GoldTierXpiHttpResponse(status_code=200, body=search_body)]
    )
    service = _xpi_onboarding_service(transport, acra_connector=acra)

    case = service.create_staged_case_with_identity(
        UUID("00000000-0000-4000-8000-000000000201"),
        UUID("00000000-0000-4000-8000-000000000202"),
        "11111999A",
        "SG",
        legal_name="GARDEN BUSINESS",
    )

    assert case.state == expected_state
    assert acra.calls == expected_acra_calls
    if len(search_body) > 1:
        assert case.initial_target_search is not None
        assert case.initial_target_search.disposition == "REVIEW_REQUIRED"
    assert [call["method"] for call in transport.calls] == ["GET"]
    if expected_state == "REVIEW_REQUIRED":
        assert service.get_attempted_target_operations(case.case_id) == ()


@pytest.mark.parametrize(
    ("stage", "responses", "expected_operations"),
    [
        (
            "SHELL",
            [],
            ("SEARCH", "SHELL"),
        ),
        (
            "POLICY",
            ["SHELL_SUCCESS"],
            ("SEARCH", "SHELL", "POLICY"),
        ),
        (
            "AMEND",
            ["SHELL_SUCCESS", "POLICY_SUCCESS"],
            ("SEARCH", "SHELL", "POLICY", "AMEND"),
        ),
    ],
)
def test_oversized_post_dispatch_mutation_response_is_uncertain_and_non_replayable(
    stage: str,
    responses: list[str],
    expected_operations: tuple[str, ...],
) -> None:
    del stage
    module = importlib.import_module("app.connectors.goldtier_xpi")
    transport_responses: list[object] = [
        module.GoldTierXpiHttpResponse(status_code=200, body=[]),
    ]
    for response in responses:
        if response == "SHELL_SUCCESS":
            transport_responses.append(
                module.GoldTierXpiHttpResponse(status_code=200, body={"goldTierId": 12345})
            )
        else:
            transport_responses.append(module.GoldTierXpiHttpResponse(status_code=200, body={}))
    transport_responses.append(module.GoldTierXpiResponseTooLargeError())
    transport = FakeXpiTransport(transport_responses)
    service = _xpi_onboarding_service(transport)
    case = service.create_staged_case("202400001A")
    submission = service.build_submission_input(case, provider_mode="SANDBOX")

    _confirm_service_submission(service, submission)
    with pytest.raises(Exception, match="uncertain"):
        service.execute_submission_input(submission)
    call_count = len(transport.calls)
    with pytest.raises(RuntimeError, match="already in progress"):
        service.execute_submission_input(submission)

    assert service.get_execution_state(submission.submission_id) == "IN_PROGRESS"
    assert service.is_execution_outcome_uncertain(submission.submission_id) is True
    assert service.get_attempted_target_operations(submission.submission_id) == expected_operations
    assert len(transport.calls) == call_count


def test_ambiguous_shell_response_identifier_is_uncertain_and_non_replayable() -> None:
    module = importlib.import_module("app.connectors.goldtier_xpi")
    transport = FakeXpiTransport(
        [
            module.GoldTierXpiHttpResponse(status_code=200, body=[]),
            module.GoldTierXpiHttpResponse(
                status_code=200,
                body={"goldTierId": "12345", "nested": {"goldTierID": "67890"}},
            ),
        ]
    )
    service = _xpi_onboarding_service(transport)
    case = service.create_staged_case("202400001A")
    submission = service.build_submission_input(case, provider_mode="SANDBOX")

    _confirm_service_submission(service, submission)
    with pytest.raises(Exception, match="uncertain"):
        service.execute_submission_input(submission)
    call_count = len(transport.calls)
    with pytest.raises(RuntimeError, match="already in progress"):
        service.execute_submission_input(submission)

    assert service.get_execution_state(submission.submission_id) == "IN_PROGRESS"
    assert service.is_execution_outcome_uncertain(submission.submission_id) is True
    assert service.get_attempted_target_operations(submission.submission_id) == (
        "SEARCH",
        "SHELL",
    )
    assert len(transport.calls) == call_count


@pytest.mark.parametrize("stage", ["SHELL", "POLICY", "AMEND"])
@pytest.mark.parametrize("status_code", [302, 500, 503])
def test_unconfirmed_mutation_http_failure_stops_without_definitive_outcome_or_replay(
    stage: str,
    status_code: int,
) -> None:
    module = importlib.import_module("app.connectors.goldtier_xpi")
    responses = [module.GoldTierXpiHttpResponse(status_code=200, body=[])]
    operations = ["SEARCH", "SHELL"]
    if stage != "SHELL":
        responses.append(
            module.GoldTierXpiHttpResponse(status_code=200, body={"goldTierId": 12345})
        )
        operations.append("POLICY")
    if stage == "AMEND":
        responses.append(module.GoldTierXpiHttpResponse(status_code=200, body={}))
        operations.append("AMEND")
    responses.append(
        module.GoldTierXpiHttpResponse(status_code=status_code, body={"private": "detail"})
    )
    transport = FakeXpiTransport(responses)
    service = _xpi_onboarding_service(transport)
    case = service.create_staged_case("202400001A")
    submission = service.build_submission_input(case, provider_mode="SANDBOX")
    _confirm_service_submission(service, submission)
    with pytest.raises(module.GoldTierMutationOutcomeUncertainError):
        service.execute_submission_input(submission)
    call_count = len(transport.calls)
    with pytest.raises(RuntimeError, match="already in progress"):
        service.execute_submission_input(submission)
    assert service.get_execution_state(submission.submission_id) == "IN_PROGRESS"
    assert service.is_execution_outcome_uncertain(submission.submission_id) is True
    assert service.get_attempted_target_operations(submission.submission_id) == tuple(operations)
    assert len(transport.calls) == call_count


def test_fresh_sandbox_customer_without_enrichment_skips_amend_and_retains_submission() -> None:
    module = importlib.import_module("app.connectors.goldtier_xpi")
    transport = FakeXpiTransport(
        [
            module.GoldTierXpiHttpResponse(status_code=200, body=[]),
            module.GoldTierXpiHttpResponse(status_code=200, body={"goldTierId": 12345}),
            module.GoldTierXpiHttpResponse(status_code=200, body={}),
            module.GoldTierXpiHttpResponse(status_code=200, body=[{"goldTierId": 12345}]),
        ]
    )
    service = _xpi_onboarding_service(transport, reviewed_test_enrichment=False)
    case = service.create_staged_case("202400001A")
    submission = service.build_submission_input(case, provider_mode="SANDBOX")
    _confirm_service_submission(service, submission)
    receipt = service.execute_submission_input(submission)
    assert receipt.classification == "SUCCESS"
    assert receipt.result.amend_status == "AMEND_NOT_REQUIRED"
    assert service.get_attempted_target_operations(submission.submission_id) == (
        "SEARCH",
        "SHELL",
        "POLICY",
        "READBACK",
    )
    assert not any(str(c["url"]).endswith("/amendCustomer") for c in transport.calls)
    assert service.execute_submission_input(submission) == receipt
    assert len(transport.calls) == 4


def test_sandbox_preview_omits_amend_without_supported_enrichment() -> None:
    mapper = importlib.import_module("app.mappers.goldtier_xpi").GoldTierXpiRequestMapper()
    submission = _sandbox_submission()
    assert mapper.build_amend_request(submission, "12345").anzsic is None
    assert [op.operation for op in mapper.build_preview(submission).operations] == [
        "SEARCH",
        "SHELL",
        "POLICY",
        "READBACK",
    ]


@pytest.mark.parametrize(
    "returned",
    [
        {"legalName": "DIFFERENT CUSTOMER"},
        {"registrationNumber": "202499999Z"},
        {"countryOfIncorporation": "AU"},
        {"legalForm": "DIFFERENT FORM"},
        {"legalRegisteredAddress": "DIFFERENT ADDRESS"},
    ],
)
def test_same_id_readback_rejects_available_identity_mismatch(returned) -> None:
    module = importlib.import_module("app.connectors.goldtier_xpi")
    transport = FakeXpiTransport(
        [
            module.GoldTierXpiHttpResponse(status_code=200, body=[]),
            module.GoldTierXpiHttpResponse(status_code=200, body={"goldTierId": 12345}),
            module.GoldTierXpiHttpResponse(status_code=200, body={}),
            module.GoldTierXpiHttpResponse(
                status_code=200,
                body=[
                    {"goldTierId": 12345, **returned},
                ],
            ),
        ]
    )
    service = _xpi_onboarding_service(transport, reviewed_test_enrichment=False)
    case = service.create_staged_case("202400001A")
    submission = service.build_submission_input(case, provider_mode="SANDBOX")
    _confirm_service_submission(service, submission)
    receipt = service.execute_submission_input(submission)
    assert receipt.classification == "REVIEW_REQUIRED"
    assert receipt.error.code == "GT_READBACK_IDENTITY_REVIEW_REQUIRED"
    assert receipt.result.policy_status == "POLICY_CREATED"
    assert receipt.result.amend_status == "AMEND_NOT_REQUIRED"
    assert len(transport.calls) == 4


def test_reviewed_optional_enrichment_remains_bound_in_preview() -> None:
    service = _xpi_onboarding_service(FakeXpiTransport())
    case = service.create_staged_case("202400001A")
    submission = service.build_submission_input(case, provider_mode="SANDBOX")
    preview = service._goldtier_mapper.build_preview(submission)
    amend = next(item for item in preview.operations if item.operation == "AMEND")
    assert any(
        f.target_field == "groupCompanyName" and f.value == "SYNTHETIC TEST GROUP"
        for f in amend.fields
    )
    assert all(f.target_field != "ANZSIC" for f in amend.fields)


@pytest.mark.parametrize("existing", [False, True])
def test_incremental_submission_skips_unneeded_amend_and_existing_policy(existing) -> None:
    module = importlib.import_module("app.connectors.goldtier_xpi")
    responses = (
        []
        if existing
        else [
            module.GoldTierXpiHttpResponse(status_code=200, body={"goldTierId": 12345}),
            module.GoldTierXpiHttpResponse(status_code=200, body={}),
        ]
    )
    responses.append(
        module.GoldTierXpiHttpResponse(
            status_code=200,
            body=[{"goldTierId": 12345}],
        )
    )
    transport = FakeXpiTransport(responses)
    service = _xpi_onboarding_service(transport, reviewed_test_enrichment=False)
    case = service.create_staged_case("202400001A")
    submission = service.build_submission_input(case, provider_mode="SANDBOX")
    _confirm_service_submission(service, submission)
    receipt = None
    for _ in range(4):
        receipt = service.advance_incremental_submission_input(
            submission,
            search_resolution="EXACT_MATCH" if existing else "NO_MATCH",
            selected_party_id="12345" if existing else None,
        )
        if receipt is not None:
            break
    assert receipt.classification == "SUCCESS"
    assert receipt.result.amend_status == "AMEND_NOT_REQUIRED"
    expected = (
        ("SEARCH", "READBACK")
        if existing
        else (
            "SEARCH",
            "SHELL",
            "POLICY",
            "READBACK",
        )
    )
    assert service.get_attempted_target_operations(submission.submission_id) == expected
    assert len(transport.calls) == (1 if existing else 3)
