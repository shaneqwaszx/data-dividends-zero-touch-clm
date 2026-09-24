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
from app.services.policy_management import PolicyManagementService

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
        policy.PolicyAuthority.SPONSOR_SUPPLIED
        if ready
        else policy.PolicyAuthority.TBD_SPONSOR
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
            module.GoldTierXpiHttpResponse(status_code=200, body={"goldTierId": 12345}),
            module.GoldTierXpiHttpResponse(status_code=200, body={}),
            module.GoldTierXpiHttpResponse(status_code=200, body={}),
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


def test_target_enrichments_are_editable_authority_labelled_and_immutable_per_case() -> None:
    policy = importlib.import_module("app.domain.policy")
    service = PolicyManagementService(InMemoryPolicyRepository())
    before = service.case_snapshot()
    rule = service.get(policy.GOLDTIER_KYC_CUSTOMER_TYPE_ID)

    assert rule.value == policy.StringPolicyValue(value="TBD_SPONSOR")
    assert rule.authority == policy.PolicyAuthority.TBD_SPONSOR
    assert before.goldtier_target.kyc_customer_type.value == "TBD_SPONSOR"
    assert before.goldtier_target.kyc_customer_type.authority == "TBD_SPONSOR"
    assert before.goldtier_target.dispatch_ready is False

    service.update(
        _director(),
        rule.policy_id,
        expected_catalogue_version=service.catalogue().version,
        expected_rule_version=rule.version,
        value=policy.StringPolicyValue(value="SPONSOR VALUE"),
        authority=policy.PolicyAuthority.SPONSOR_SUPPLIED,
    )
    after = service.case_snapshot()

    assert before.goldtier_target.kyc_customer_type.value == "TBD_SPONSOR"
    assert after.goldtier_target.kyc_customer_type.value == "SPONSOR VALUE"
    assert after.goldtier_target.kyc_customer_type.authority == "SPONSOR_SUPPLIED"
    assert before.catalogue_version != after.catalogue_version


def test_target_policy_reset_restores_the_tbd_value_and_authority() -> None:
    policy = importlib.import_module("app.domain.policy")
    service = PolicyManagementService(InMemoryPolicyRepository())
    original = service.get(policy.GOLDTIER_POLICY_ID)
    updated_catalogue = service.update(
        _director(),
        original.policy_id,
        expected_catalogue_version=service.catalogue().version,
        expected_rule_version=original.version,
        value=policy.StringPolicyValue(value="SPONSOR VALUE"),
        authority=policy.PolicyAuthority.SPONSOR_SUPPLIED,
    )
    updated = updated_catalogue.rule(original.policy_id)
    assert updated is not None

    reset_catalogue = service.reset_one(
        _director(),
        original.policy_id,
        expected_catalogue_version=updated_catalogue.version,
        expected_rule_version=updated.version,
    )
    reset = reset_catalogue.rule(original.policy_id)

    assert reset is not None
    assert reset.value == policy.StringPolicyValue(value="TBD_SPONSOR")
    assert reset.authority == policy.PolicyAuthority.TBD_SPONSOR


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
        "accountEntityType",
        "productType",
    )


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
    assert fields["legalName"].provenance == "REGISTRY"
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
) -> object:
    onboarding = importlib.import_module("app.services.onboarding")
    intelligence = importlib.import_module("app.services.onboarding_intelligence")
    mock_acra = importlib.import_module("app.connectors.mock_acra")
    repository = importlib.import_module("app.services.repository")
    mapper = importlib.import_module("app.mappers.goldtier_xpi").GoldTierXpiRequestMapper()
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
        acra=mock_acra.MockAcraConnector(),
        goldtier=_xpi_connector(transport),
        goldtier_mapper=mapper,
        entity_resolver=intelligence.OnboardingIntelligenceService(),
        repository=repository.InMemoryOnboardingCaseRepository(),
        policy_snapshot_provider=lambda: snapshot,
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

    shell = connector.create_shell_customer(
        mapper.build_shell_request(submission), _metadata()
    )
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
        ]
    )
    service = _xpi_onboarding_service(transport)
    case = service.create_staged_case("202400001A")
    submission = service.build_submission_input(case, provider_mode="SANDBOX")

    receipt = service.execute_submission_input(submission)
    repeated = service.execute_submission_input(submission)

    assert receipt.classification == "SUCCESS"
    assert receipt.result.party_id == "12345"
    assert service.get_attempted_target_operations(submission.submission_id) == (
        "SEARCH",
        "SHELL",
        "POLICY",
        "AMEND",
    )
    assert repeated == receipt
    assert len(transport.calls) == 4


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
            module.GoldTierXpiHttpResponse(status_code=200, body={}),
        ]
    )
    service = _xpi_onboarding_service(transport)
    case = service.create_staged_case("202400001A")
    submission = service.build_submission_input(case, provider_mode="SANDBOX")

    receipt = service.execute_submission_input(submission)

    assert receipt.classification == "SUCCESS"
    assert receipt.result.party_id == "12345"
    assert receipt.result.shell_status == "EXISTING_PARTY_REUSED"
    assert service.get_attempted_target_operations(submission.submission_id) == (
        "SEARCH",
        "POLICY",
        "AMEND",
    )
    assert not any(call["url"].endswith("/customers/create") for call in transport.calls)


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
    transport = FakeXpiTransport(
        [module.GoldTierXpiHttpResponse(status_code=200, body=candidates)]
    )
    service = _xpi_onboarding_service(transport)
    case = service.create_staged_case("202400001A")
    submission = service.build_submission_input(case, provider_mode="SANDBOX")

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


def test_corrupted_case_bound_target_policy_blocks_preview_and_execution_before_dispatch() -> None:
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
    case = service.create_staged_case("202400001A")
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

    with pytest.raises(Exception, match="uncertain"):
        service.execute_submission_input(submission)
    call_count = len(transport.calls)
    with pytest.raises(RuntimeError, match="already in progress") as replay:
        service.execute_submission_input(submission)

    assert service.get_execution_state(submission.submission_id) == "IN_PROGRESS"
    assert service.is_execution_outcome_uncertain(submission.submission_id) is True
    assert len(transport.calls) == call_count
    _assert_no_mock_provider_claim([str(replay.value)])


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
            transport_responses.append(
                module.GoldTierXpiHttpResponse(status_code=200, body={})
            )
    transport_responses.append(module.GoldTierXpiResponseTooLargeError())
    transport = FakeXpiTransport(transport_responses)
    service = _xpi_onboarding_service(transport)
    case = service.create_staged_case("202400001A")
    submission = service.build_submission_input(case, provider_mode="SANDBOX")

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
