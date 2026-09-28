"""Run the bounded Garden GoldTier recovery acceptance with durable Mongo ownership.

The runner emits only safe identifiers, classifications, operation names, and counts.
It never prints provider payloads, credentials, headers, or the Mongo URI. The selected
database must use the repository's allowlisted disposable-database naming convention,
but it is deliberately retained after the run as restart evidence.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from app.composition import (
    build_acra_connector,
    build_document_processing_service,
    build_onboarding_service,
    build_reconciliation_service,
)
from app.config import Settings
from app.connectors.acra import (
    AcraCompanyPayload,
    AcraConnector,
    AcraOfficersPayload,
    AcraOwnershipPartiesPayload,
    AcraRelationshipsPayload,
)
from app.connectors.goldtier_xpi import (
    GoldTierXpiHttpResponse,
    GoldTierXpiHttpTransport,
    GoldTierXpiSandboxConnector,
    HttpxGoldTierXpiTransport,
)
from app.connectors.goldtier_xpi_models import XpiCustomerSearchRequest
from app.domain.documents import ReviewDecision
from app.domain.reconciliation import (
    ReconciliationDecisionAction,
    ReconciliationField,
)
from app.domain.target_preparation import TargetFieldAuthority, TargetFieldValidation
from app.domain.target_submission import (
    GoldTierExecutionClassification,
    GoldTierOperationMarker,
    GoldTierProviderFailureStatus,
    GoldTierProviderMode,
    GoldTierRecoveryOrigin,
    GoldTierSearchResolution,
)
from app.persistence.composition import PersistenceBundle, build_persistence_bundle
from app.services.onboarding import OnboardingService
from app.services.policy_management import PolicyManagementService

from scripts.mongo_test_safety import require_ephemeral_mongo_database

GARDEN_NAME = "GARDEN BUSINESS"
GARDEN_UEN = "11111999A"
GARDEN_COUNTRY = "SG"
GARDEN_ID = "143878"
GARDEN_KYC = "Partnership - Unregulated"
GARDEN_SEGMENT = "Commercial SBB (Small Business Banking)"
UPDATED_GARDEN_NAME = "GARDEN BUSINESS POC UPDATE"
GARDEN_POLICY = "Singapore"
GARDEN_ENVIRONMENT = "anz-nutmeg"
FIRST_GARDEN_CASE_ID = UUID("45cd8ddd-b053-4146-a5a0-82a118e164cd")
FIRST_GARDEN_SUBMISSION_ID = UUID("8da7f6fb-17aa-42da-8a71-617c8b469935")


@dataclass
class CountingAcraConnector:
    delegate: AcraConnector
    calls: list[str] = field(default_factory=list)

    def fetch_company(self, uen: str) -> AcraCompanyPayload | None:
        self.calls.append("ENTITY_PROFILE")
        return self.delegate.fetch_company(uen)

    def fetch_officers(self, uen: str) -> AcraOfficersPayload:
        self.calls.append("OFFICERS")
        return self.delegate.fetch_officers(uen)

    def fetch_ownership_parties(self, uen: str) -> AcraOwnershipPartiesPayload:
        self.calls.append("OWNERSHIP_PARTIES")
        return self.delegate.fetch_ownership_parties(uen)

    def fetch_relationships(self, uen: str) -> AcraRelationshipsPayload:
        self.calls.append("RELATIONSHIPS")
        return self.delegate.fetch_relationships(uen)


@dataclass
class CountingGoldTierTransport:
    delegate: GoldTierXpiHttpTransport = field(
        default_factory=HttpxGoldTierXpiTransport
    )
    calls: list[tuple[str, str]] = field(default_factory=list)

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        json_body: object | None,
        timeout_seconds: float,
        max_response_bytes: int,
    ) -> GoldTierXpiHttpResponse:
        self.calls.append((method.upper(), urlsplit(url).path))
        return self.delegate.request(
            method,
            url,
            headers=headers,
            json_body=json_body,
            timeout_seconds=timeout_seconds,
            max_response_bytes=max_response_bytes,
        )

    def count_path(self, suffix: str) -> int:
        return sum(path.endswith(suffix) for _, path in self.calls)


@dataclass
class Runtime:
    bundle: PersistenceBundle
    onboarding: OnboardingService
    acra: CountingAcraConnector

    def close(self) -> None:
        self.bundle.close()


def _settings(database: str) -> Settings:
    require_ephemeral_mongo_database(database)
    settings = Settings(
        clm_persistence_mode="mongo",
        mongo_database=database,
        registry_cache_mode="disabled",
    )
    if (
        settings.mongo_uri is None
        or settings.acra_connector_mode != "api_marketplace_mock"
        or settings.goldtier_connector_mode != "sandbox"
        or not settings.goldtier_sandbox_allow_writes
        or settings.idp_connector_mode != "local_pdf_text"
        or settings.goldtier_sandbox_environment != GARDEN_ENVIRONMENT
    ):
        raise RuntimeError("Configured external acceptance providers are unavailable")
    return settings


def _open_runtime(
    settings: Settings,
    goldtier_transport: CountingGoldTierTransport,
) -> Runtime:
    bundle = build_persistence_bundle(settings)
    policy = PolicyManagementService(bundle.policies)
    acra = CountingAcraConnector(build_acra_connector(settings))
    onboarding = build_onboarding_service(
        settings=settings,
        acra_connector=acra,
        repository=bundle.onboarding,
        target_execution_repository=bundle.target_executions,
        policy_snapshot_provider=policy.case_snapshot,
        registry_snapshot_repository=bundle.registry_snapshots,
        goldtier_transport=goldtier_transport,
    )
    return Runtime(bundle=bundle, onboarding=onboarding, acra=acra)


def _assert_policy_recovery_checkpoint(entry: Any) -> None:
    shell = entry.provider_verified_recovery
    policy = entry.provider_verified_policy_recovery
    if (
        entry.resolved_party_id != GARDEN_ID
        or entry.attempted_operations
        != (
            GoldTierOperationMarker.SEARCH,
            GoldTierOperationMarker.SHELL,
            GoldTierOperationMarker.POLICY,
        )
        or entry.definitively_completed_operations != (GoldTierOperationMarker.SEARCH,)
        or entry.lifecycle_resolved_operations != entry.attempted_operations
        or shell is None
        or shell.replayed
        or policy is None
        or policy.operation != GoldTierOperationMarker.POLICY
        or policy.recovered_party_id != GARDEN_ID
        or policy.provider_policy != GARDEN_POLICY
        or policy.provider_policy_status != "Requested"
        or policy.replayed
        or GoldTierOperationMarker.AMEND in entry.attempted_operations
    ):
        raise RuntimeError("Recovered Policy checkpoint is not exact")


def _assert_pre_amend_safety(
    runtime: Runtime,
    settings: Settings,
    submission: Any,
) -> None:
    connector = runtime.onboarding._goldtier
    if type(connector) is not GoldTierXpiSandboxConnector:
        raise RuntimeError(
            "Configured target provider is not GoldTierXpiSandboxConnector"
        )
    if (
        settings.goldtier_sandbox_environment != GARDEN_ENVIRONMENT
        or runtime.onboarding.target_provider_mode != GoldTierProviderMode.SANDBOX
    ):
        raise RuntimeError(
            "Configured GoldTier environment is not the authorized sandbox"
        )
    checkpoint = runtime.bundle.target_executions.get(submission.submission_id)
    if checkpoint is None:
        raise RuntimeError("Recovered target checkpoint is unavailable")
    _assert_policy_recovery_checkpoint(checkpoint)
    case = runtime.onboarding.get_case(submission.case_id)
    if (
        case is None
        or case.goldtier_result is None
        or case.goldtier_result.party_id != GARDEN_ID
    ):
        raise RuntimeError("Case does not retain the authorized GoldTier identity")
    policy = submission.target_policy
    if (
        policy is None
        or policy.kyc_customer_type.value != GARDEN_KYC
        or policy.kyc_customer_type.authority.value != "USER_AUTHORIZED_POC"
        or policy.client_segment.value != GARDEN_SEGMENT
        or policy.client_segment.authority.value != "USER_AUTHORIZED_POC"
        or policy.policy.value != GARDEN_POLICY
    ):
        raise RuntimeError("Garden case classifications are not the authorized values")
    preview = runtime.onboarding.build_request_preview(
        case,
        provider_mode=GoldTierProviderMode.SANDBOX,
    )
    amend = next(
        (item for item in preview.operations if item.operation == "AMEND"), None
    )
    if (
        not preview.dispatch_ready
        or amend is None
        or amend.validation != TargetFieldValidation.VALID
        or amend.missing_fields
        or {field.target_field for field in amend.fields} != {"goldTierId", "policy"}
        or any(
            field.authority
            not in {
                TargetFieldAuthority.PROJECT_DERIVED_POC,
                TargetFieldAuthority.PROJECT_DEFINED_PROVISIONAL,
                TargetFieldAuthority.SPONSOR_SUPPLIED,
                TargetFieldAuthority.SPONSOR_DOCUMENTED,
                TargetFieldAuthority.USER_AUTHORIZED_POC,
            }
            for field in amend.fields
        )
    ):
        raise RuntimeError("Sanitized Amend preview is not dispatch-ready and bounded")


def _advance_to_receipt(
    service: OnboardingService,
    submission: Any,
    *,
    search_resolution: GoldTierSearchResolution,
    selected_party_id: str | None,
) -> Any:
    for _ in range(4):
        receipt = service.advance_incremental_submission_input(
            submission,
            search_resolution=search_resolution,
            selected_party_id=selected_party_id,
        )
        if receipt is not None:
            return receipt
    raise RuntimeError("Target lifecycle did not reach a terminal receipt")


def reconcile_amend_failure(database: str, *, verify_only: bool) -> int:
    """Record or independently reload the one provider-verified Garden Amend failure."""

    settings = _settings(database)
    transport = CountingGoldTierTransport()
    runtime: Runtime | None = None
    restarted: Runtime | None = None
    try:
        runtime = _open_runtime(settings, transport)
        entry = runtime.bundle.target_executions.get(FIRST_GARDEN_SUBMISSION_ID)
        if (
            entry is None
            or entry.submission_input.case_id != FIRST_GARDEN_CASE_ID
            or entry.resolved_party_id != GARDEN_ID
        ):
            raise RuntimeError("The exact retained Garden Amend ledger is unavailable")
        if not verify_only:
            entry = runtime.onboarding.recover_uncertain_amend_failure_from_provider(
                submission_input=entry.submission_input,
                recovered_party_id=GARDEN_ID,
                provider_status=(
                    GoldTierProviderFailureStatus.PROVIDER_VALIDATION_FAILED
                ),
                provider_status_evidence="Valdiation Failed",
                actor_id="provider-portal-reconciliation",
                origin=GoldTierRecoveryOrigin.UNCERTAIN_DURABLE_LEDGER,
            )
        failure = entry.provider_verified_amend_failure
        if (
            failure is None
            or failure.operation != GoldTierOperationMarker.AMEND
            or failure.provider_status
            != GoldTierProviderFailureStatus.PROVIDER_VALIDATION_FAILED
            or failure.provider_status_evidence != "Valdiation Failed"
            or not failure.original_outcome_uncertain
            or failure.replayed
            or GoldTierOperationMarker.AMEND in entry.lifecycle_resolved_operations
            or GoldTierOperationMarker.AMEND in entry.definitively_completed_operations
            or transport.calls
        ):
            raise RuntimeError("Retained Amend provider failure is not exact")
        amend_request = runtime.onboarding._goldtier_mapper.build_amend_request(
            entry.submission_input, GARDEN_ID
        )
        amend_payload = amend_request.model_dump(by_alias=True, exclude_none=True)
        if amend_payload != {"goldTierId": GARDEN_ID, "policy": GARDEN_POLICY}:
            raise RuntimeError("Sanitized Amend reconstruction is not exact")
        runtime.close()
        runtime = None

        restart_transport = CountingGoldTierTransport()
        restarted = _open_runtime(settings, restart_transport)
        reloaded = restarted.bundle.target_executions.get(FIRST_GARDEN_SUBMISSION_ID)
        if (
            reloaded is None
            or reloaded.provider_verified_amend_failure != failure
            or restart_transport.calls
        ):
            raise RuntimeError("Amend provider failure did not survive restart")
        print("AMEND_PROVIDER_RECONCILIATION=PROVIDER_VERIFIED_FAILURE")
        print("AMEND_ORIGINAL_OUTCOME=UNCERTAIN")
        print("AMEND_PROVIDER_STATUS=PROVIDER_VALIDATION_FAILED")
        print("AMEND_PROVIDER_STATUS_EVIDENCE=Valdiation Failed")
        print("AMEND_COMPLETED=false")
        print("AMEND_REPLAYED=false")
        print("AMEND_FIELD_goldTierId=present:143878")
        print("AMEND_FIELD_policy=present:Singapore")
        print("AMEND_FIELD_anzsic=omitted")
        print("AMEND_FIELD_groupCompanyName=omitted")
        print("AMEND_EMPTY_FIELDS=0")
        print("NETWORK_CALLS=0")
        print("RESTART_RECOVERY=PASS")
        return 0
    except Exception as exc:  # noqa: BLE001 - safe reconciliation boundary
        print("AMEND_FAILURE_RECONCILIATION=FAIL")
        print(f"ERROR_TYPE={type(exc).__name__}")
        return 1
    finally:
        if runtime is not None:
            runtime.close()
        if restarted is not None:
            restarted.close()


def run(
    database: str,
    *,
    stop_after_policy_recovery: bool = False,
    stop_before_amend: bool = False,
) -> int:
    settings = _settings(database)
    target_transport = CountingGoldTierTransport()
    stage = "INITIALIZE"
    runtime: Runtime | None = None
    first_case_id: UUID | None = None
    second_case_id: UUID | None = None
    first_submission: Any = None
    first_acra_calls = 0
    second_acra_calls = 0
    second_call_offset = 0
    try:
        stage = "FRESH_REAL_SEARCH"
        runtime = _open_runtime(settings, target_transport)
        preflight = runtime.onboarding.search_sandbox_target(
            XpiCustomerSearchRequest(
                legal_name=GARDEN_NAME,
                country_of_incorporation=GARDEN_COUNTRY,
            ),
            correlation_id=uuid4(),
        )
        candidates = preflight.result.candidates
        if (
            len(candidates) != 1
            or candidates[0].party_id != GARDEN_ID
            or candidates[0].legal_name != GARDEN_NAME
        ):
            raise RuntimeError(
                "Fresh GoldTier Search did not return exact Garden identity"
            )

        stage = "RECOVERY_CASE_CANONICAL_INPUT"
        snapshots = (
            runtime.bundle.mongo_store.list() if runtime.bundle.mongo_store else []
        )
        retained_recoveries = [
            (snapshot.onboarding, entry)
            for snapshot in snapshots
            for entry in snapshot.target_executions
            if entry.provider_verified_recovery is not None
            and entry.provider_verified_recovery.origin
            == GoldTierRecoveryOrigin.HISTORICAL_LOCAL_LEDGER_LOST
        ]
        if len(retained_recoveries) > 1:
            raise RuntimeError(
                "Acceptance database contains conflicting recovery cases"
            )
        if retained_recoveries:
            first_case, retained = retained_recoveries[0]
            first_submission = retained.submission_input
            first_case_id = first_case.case_id
            first_acra_calls = (
                len(first_case.registry_acquisition.operation_results)
                if first_case.registry_acquisition is not None
                else 0
            )
        else:
            first_case = runtime.onboarding.create_staged_case(
                GARDEN_UEN, GARDEN_COUNTRY
            )
            first_acra_calls = len(runtime.acra.calls)
            entity = first_case.entity
            if (
                entity is None
                or entity.registration_number != GARDEN_UEN
                or entity.legal_name != GARDEN_NAME
                or entity.country_of_incorporation != GARDEN_COUNTRY
            ):
                raise RuntimeError(
                    "Official ACRA Mock did not supply exact Garden canonical input"
                )
            first_case = runtime.onboarding.bind_goldtier_case_classification(
                case_id=first_case.case_id,
                kyc_customer_type=GARDEN_KYC,
                client_segment=GARDEN_SEGMENT,
            )
            first_case_id = first_case.case_id
            first_submission = runtime.onboarding.build_submission_input(
                first_case,
                provider_mode=GoldTierProviderMode.SANDBOX,
            )

        stage = "SHELL_RECOVERY_RELOAD"
        recovered = runtime.onboarding.recover_uncertain_shell_from_provider(
            submission_input=first_submission,
            recovered_party_id=GARDEN_ID,
            legal_name=GARDEN_NAME,
            registration_number=GARDEN_UEN,
            country_of_incorporation=GARDEN_COUNTRY,
            actor_id="director-provider-recovery",
            origin=GoldTierRecoveryOrigin.HISTORICAL_LOCAL_LEDGER_LOST,
        )
        if (
            recovered.resolved_party_id != GARDEN_ID
            or recovered.provider_verified_recovery is None
            or recovered.provider_verified_recovery.replayed
            or recovered.provider_verified_recovery.operation
            != GoldTierOperationMarker.SHELL
            or recovered.provider_verified_recovery.recovered_party_id != GARDEN_ID
            or GoldTierOperationMarker.SHELL not in recovered.attempted_operations
            or GoldTierOperationMarker.SHELL
            not in recovered.lifecycle_resolved_operations
            or GoldTierOperationMarker.SHELL
            in recovered.definitively_completed_operations
            or GoldTierOperationMarker.AMEND in recovered.attempted_operations
        ):
            raise RuntimeError("Recovery ledger chronology is not exact")
        if target_transport.count_path("/customers/create") != 0:
            raise RuntimeError("Recovery attempted a forbidden Shell replay")

        stage = "POLICY_PROVIDER_VERIFIED_RECOVERY"
        before_policy_recovery_calls = len(target_transport.calls)
        before_policy_recovery = runtime.bundle.target_executions.get(
            first_submission.submission_id
        )
        if before_policy_recovery is None:
            raise RuntimeError("Original uncertain Policy checkpoint is unavailable")
        if before_policy_recovery.provider_verified_policy_recovery is None:
            if (
                before_policy_recovery.attempted_operations
                != (
                    GoldTierOperationMarker.SEARCH,
                    GoldTierOperationMarker.SHELL,
                    GoldTierOperationMarker.POLICY,
                )
                or before_policy_recovery.definitively_completed_operations
                != (GoldTierOperationMarker.SEARCH,)
                or before_policy_recovery.lifecycle_resolved_operations
                != (GoldTierOperationMarker.SEARCH, GoldTierOperationMarker.SHELL)
                or before_policy_recovery.provider_verified_recovery is None
                or GoldTierOperationMarker.AMEND
                in before_policy_recovery.attempted_operations
            ):
                raise RuntimeError("Original uncertain Policy chronology is not exact")
            policy_recovered = (
                runtime.onboarding.recover_uncertain_policy_from_provider(
                    submission_input=first_submission,
                    recovered_party_id=GARDEN_ID,
                    legal_name=GARDEN_NAME,
                    registration_number=GARDEN_UEN,
                    country_of_incorporation=GARDEN_COUNTRY,
                    provider_policy=GARDEN_POLICY,
                    provider_policy_status="Requested",
                    actor_id="director-provider-recovery",
                    origin=GoldTierRecoveryOrigin.UNCERTAIN_DURABLE_LEDGER,
                )
            )
        else:
            policy_recovered = before_policy_recovery
        _assert_policy_recovery_checkpoint(policy_recovered)
        if (
            len(target_transport.calls) != before_policy_recovery_calls
            or target_transport.count_path("/customers/createPolicy") != 0
        ):
            raise RuntimeError("Policy recovery made a forbidden provider call")
        runtime.close()
        runtime = None
        if stop_after_policy_recovery:
            print("ACCEPTANCE_CHECKPOINT=POLICY_RECOVERY_RECORDED")
            print(f"DATABASE={database}")
            print(f"FIRST_CASE_ID={first_case_id}")
            print(f"RECOVERED_GOLDTIER_ID={GARDEN_ID}")
            print("ORIGINAL_POLICY_OUTCOME=UNCERTAIN")
            print("POLICY_RECOVERY_AUTHORITY=PROVIDER_VERIFIED_RECOVERY")
            print("POLICY_PROVIDER_STATUS=Requested")
            print("POLICY_REPLAYED=false")
            return 0

        stage = "POLICY_RECOVERY_DURABILITY"
        runtime = _open_runtime(settings, target_transport)
        checkpoint = runtime.bundle.target_executions.get(
            first_submission.submission_id
        )
        if checkpoint is None:
            raise RuntimeError("Recovered Policy ledger did not survive restart")
        _assert_policy_recovery_checkpoint(checkpoint)

        stage = "PRE_AMEND_SAFETY"
        _assert_pre_amend_safety(runtime, settings, first_submission)
        if stop_before_amend:
            runtime.close()
            runtime = None
            print("ACCEPTANCE_CHECKPOINT=PRE_AMEND_SAFE")
            print(f"DATABASE={database}")
            print(f"FIRST_CASE_ID={first_case_id}")
            print(f"RECOVERED_GOLDTIER_ID={GARDEN_ID}")
            print("DURABLE_RESTART_PROOF=PASS")
            print("NEXT_ALLOWED_OPERATION=AMEND")
            print("PROVIDER_CONNECTOR=GoldTierXpiSandboxConnector")
            print(f"PROVIDER_ENVIRONMENT={GARDEN_ENVIRONMENT}")
            print("SANITIZED_AMEND_PREVIEW=VALID")
            print("AMEND_ATTEMPTED=false")
            return 0
        before_amend_calls = len(target_transport.calls)
        before_amend_count = target_transport.count_path("/customers/amendCustomer")
        before_shell_count = target_transport.count_path("/customers/create")
        before_policy_count = target_transport.count_path("/customers/createPolicy")

        stage = "EXACTLY_ONE_AMEND"
        amend_receipt = runtime.onboarding.advance_incremental_submission_input(
            first_submission,
            search_resolution=GoldTierSearchResolution.NO_MATCH,
            selected_party_id=None,
        )
        if amend_receipt is not None:
            raise RuntimeError(
                "Amend checkpoint unexpectedly terminated before read-back"
            )
        after_amend = runtime.bundle.target_executions.get(
            first_submission.submission_id
        )
        if (
            after_amend is None
            or after_amend.attempted_operations
            != (
                GoldTierOperationMarker.SEARCH,
                GoldTierOperationMarker.SHELL,
                GoldTierOperationMarker.POLICY,
                GoldTierOperationMarker.AMEND,
            )
            or after_amend.lifecycle_resolved_operations
            != after_amend.attempted_operations
            or target_transport.count_path("/customers/amendCustomer")
            != before_amend_count + 1
            or len(target_transport.calls) != before_amend_calls + 1
            or target_transport.count_path("/customers/create") != before_shell_count
            or target_transport.count_path("/customers/createPolicy")
            != before_policy_count
        ):
            raise RuntimeError("Exactly-one Amend proof failed")
        runtime.close()
        runtime = None

        stage = "POST_AMEND_DURABILITY"
        runtime = _open_runtime(settings, target_transport)
        checkpoint = runtime.bundle.target_executions.get(
            first_submission.submission_id
        )
        if (
            checkpoint is None
            or GoldTierOperationMarker.AMEND
            not in checkpoint.lifecycle_resolved_operations
            or checkpoint.provider_verified_policy_recovery is None
            or checkpoint.resolved_party_id != GARDEN_ID
        ):
            raise RuntimeError("Policy checkpoint did not survive restart")
        stage = "POST_AMEND_READBACK_AFTER_RESTART"
        before_readback_count = target_transport.count_path("/customers/search")
        first_receipt = checkpoint.receipt
        if first_receipt is None:
            first_receipt = runtime.onboarding.advance_incremental_submission_input(
                first_submission,
                search_resolution=GoldTierSearchResolution.NO_MATCH,
                selected_party_id=None,
            )
        if (
            first_receipt is None
            or first_receipt.classification != GoldTierExecutionClassification.SUCCESS
            or first_receipt.result is None
            or first_receipt.result.party_id != GARDEN_ID
            or first_receipt.result.readback_party_id != GARDEN_ID
            or target_transport.count_path("/customers/search")
            != before_readback_count + 1
        ):
            raise RuntimeError(
                "Recovered lifecycle did not complete exact same-ID read-back"
            )
        first_final = runtime.bundle.target_executions.get(
            first_submission.submission_id
        )
        if (
            first_final is None
            or first_final.provider_verified_recovery is None
            or first_final.provider_verified_policy_recovery is None
            or first_final.resolved_party_id != GARDEN_ID
            or first_final.readback_party_id != GARDEN_ID
        ):
            raise RuntimeError("Final recovery evidence was not durable")
        runtime.close()
        runtime = None

        stage = "SECOND_GARDEN_GOLDTIER_FIRST"
        runtime = _open_runtime(settings, target_transport)
        second_call_offset = len(target_transport.calls)
        second_case = runtime.onboarding.create_staged_case(
            GARDEN_UEN,
            GARDEN_COUNTRY,
            legal_name=GARDEN_NAME,
        )
        second_case_id = second_case.case_id
        second_acra_calls = len(runtime.acra.calls)
        second_initial_calls = target_transport.calls[second_call_offset:]
        if (
            first_case_id == second_case_id
            or second_case.existing_target_state is None
            or second_case.existing_target_state.target_party_id != GARDEN_ID
            or second_case.registry_acquisition is not None
            or second_case.initial_target_search is None
            or second_case.initial_target_search.disposition != "EXACT_MATCH"
            or not second_initial_calls
            or not second_initial_calls[0][1].endswith("/customers/search")
        ):
            raise RuntimeError(
                "Second Garden case did not use the exact existing-target branch"
            )
        second_case = runtime.onboarding.bind_goldtier_case_classification(
            case_id=second_case.case_id,
            kyc_customer_type=GARDEN_KYC,
            client_segment=GARDEN_SEGMENT,
        )

        stage = "SECOND_GARDEN_DOCUMENT_RECONCILIATION"
        documents = build_document_processing_service(
            runtime.onboarding,
            settings,
            repository=runtime.bundle.documents,
        )
        reconciliation = build_reconciliation_service(
            runtime.onboarding,
            documents,
            repository=runtime.bundle.reconciliation,
            unit_of_work=runtime.bundle.reconciliation_unit_of_work,
        )
        document = documents.create_document(
            case_id=second_case.case_id,
            display_name="garden-poc-update.txt",
            content_type="text/plain",
            content=(
                f"Legal Name: {UPDATED_GARDEN_NAME}\n"
                f"UEN: {GARDEN_UEN}\n"
                "Registered Address: 18 GARDEN WALK, #01-01, 018919, SG\n"
                f"Country: {GARDEN_COUNTRY}\n"
            ).encode(),
        )
        for field_value in document.fields:
            document = documents.review_field(
                case_id=second_case.case_id,
                document_id=document.document_id,
                field_key=field_value.field_key,
                decision=ReviewDecision.ACCEPTED,
            )
        reconciled = reconciliation.reconcile_current(case_id=second_case.case_id)
        legal_name_discrepancies = tuple(
            item
            for item in reconciled.open_discrepancies
            if item.field_name == ReconciliationField.LEGAL_NAME
        )
        if len(legal_name_discrepancies) != 1:
            raise RuntimeError(
                "Synthetic legal-name update did not produce one discrepancy"
            )
        discrepancy = legal_name_discrepancies[0]
        reconciled = reconciliation.resolve_discrepancy(
            case_id=second_case.case_id,
            discrepancy_id=discrepancy.discrepancy_id,
            action=ReconciliationDecisionAction.USE_DOCUMENT_VALUE,
            expected_version=reconciled.version,
            evidence_fingerprint=discrepancy.evidence_fingerprint,
        )
        second_case = runtime.onboarding.get_case(second_case.case_id)
        if (
            second_case is None
            or second_case.entity is None
            or second_case.entity.legal_name != UPDATED_GARDEN_NAME
            or not reconciled.semantically_cleared
        ):
            raise RuntimeError(
                "Document update was not reconciled into canonical state"
            )

        stage = "SECOND_GARDEN_SAME_ID_AMEND_READBACK"
        second_submission = runtime.onboarding.build_submission_input(
            second_case,
            provider_mode=GoldTierProviderMode.SANDBOX,
        )
        second_receipt = _advance_to_receipt(
            runtime.onboarding,
            second_submission,
            search_resolution=GoldTierSearchResolution.EXACT_MATCH,
            selected_party_id=GARDEN_ID,
        )
        if (
            second_receipt.classification != GoldTierExecutionClassification.SUCCESS
            or second_receipt.result is None
            or second_receipt.result.party_id != GARDEN_ID
            or second_receipt.result.readback_party_id != GARDEN_ID
        ):
            raise RuntimeError(
                "Second Garden lifecycle did not finish same-ID read-back"
            )
        second_operations = runtime.onboarding.get_attempted_target_operations(
            second_submission.submission_id
        )
        second_transport_calls = target_transport.calls[second_call_offset:]
        second_shell_calls = sum(
            path.endswith("/customers/create") for _, path in second_transport_calls
        )
        second_policy_calls = sum(
            path.endswith("/customers/createPolicy")
            for _, path in second_transport_calls
        )
        second_amend_calls = sum(
            path.endswith("/customers/amendCustomer")
            for _, path in second_transport_calls
        )
        if (
            GoldTierOperationMarker.SHELL in second_operations
            or GoldTierOperationMarker.POLICY in second_operations
            or second_acra_calls != 0
            or second_shell_calls != 0
            or second_policy_calls != 0
            or second_amend_calls != 1
        ):
            raise RuntimeError(
                "Existing-target branch performed a forbidden bootstrap call"
            )
        runtime.close()
        runtime = None

        print("ACCEPTANCE_RESULT=PASS")
        print(f"DATABASE={database}")
        print(f"FIRST_CASE_ID={first_case_id}")
        print(f"SECOND_CASE_ID={second_case_id}")
        print(f"RECOVERED_GOLDTIER_ID={GARDEN_ID}")
        print("SHELL_RECOVERY_AUTHORITY=PROVIDER_VERIFIED_RECOVERY")
        print("SHELL_RECOVERY_ORIGIN=HISTORICAL_LOCAL_LEDGER_LOST")
        print("ORIGINAL_SHELL_OUTCOME=UNCERTAIN")
        print("SHELL_REPLAYED=false")
        print("POLICY_RECOVERY_AUTHORITY=PROVIDER_VERIFIED_RECOVERY")
        print("POLICY_RECOVERY_ORIGIN=UNCERTAIN_DURABLE_LEDGER")
        print("ORIGINAL_POLICY_OUTCOME=UNCERTAIN")
        print("POLICY_PROVIDER_STATUS=Requested")
        print("POLICY_REPLAYED=false")
        print("PROVIDER_CONNECTOR=GoldTierXpiSandboxConnector")
        print(f"PROVIDER_ENVIRONMENT={GARDEN_ENVIRONMENT}")
        print("SANITIZED_AMEND_PREVIEW=VALID")
        print("FIRST_POLICY=PROVIDER_VERIFIED_REQUESTED")
        print("FIRST_AMEND=SUCCESS")
        print("FIRST_AMEND_NETWORK_CALLS=1")
        print("FIRST_READBACK_ID=143878")
        print(f"FIRST_ACRA_OPERATION_CALLS={first_acra_calls}")
        print("SECOND_INITIAL_SEARCH=EXACT_MATCH")
        print("SECOND_INITIAL_OPERATION=GOLDTIER_SEARCH")
        print("SECOND_EXISTING_TARGET_STATE=REUSED")
        print(f"SECOND_ACRA_OPERATION_CALLS={second_acra_calls}")
        print(f"SECOND_SHELL_NETWORK_CALLS={second_shell_calls}")
        print(f"SECOND_POLICY_NETWORK_CALLS={second_policy_calls}")
        print("SECOND_DOCUMENT_RECONCILIATION=RESOLVED")
        print(f"SECOND_DOCUMENT_SELECTED_LEGAL_NAME={UPDATED_GARDEN_NAME}")
        print("SECOND_AMEND=SUCCESS")
        print(f"SECOND_AMEND_NETWORK_CALLS={second_amend_calls}")
        print("SECOND_READBACK_ID=143878")
        print("PERSISTENCE=MONGO_BACKED_DURABLE_POC")
        return 0
    except Exception as exc:  # noqa: BLE001 - safe acceptance boundary
        print("ACCEPTANCE_RESULT=FAIL")
        print(f"DATABASE={database}")
        print(f"FAILED_STAGE={stage}")
        print(f"ERROR_TYPE={type(exc).__name__}")
        return 1
    finally:
        if runtime is not None:
            runtime.close()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True)
    parser.add_argument("--stop-after-policy-recovery", action="store_true")
    parser.add_argument("--stop-before-amend", action="store_true")
    parser.add_argument("--record-amend-failure", action="store_true")
    parser.add_argument("--verify-amend-failure-only", action="store_true")
    args = parser.parse_args(argv)
    selected_modes = sum(
        bool(item)
        for item in (
            args.stop_after_policy_recovery,
            args.stop_before_amend,
            args.record_amend_failure,
            args.verify_amend_failure_only,
        )
    )
    if selected_modes > 1:
        parser.error("choose only one bounded stop checkpoint or reconciliation mode")
    if args.record_amend_failure or args.verify_amend_failure_only:
        return reconcile_amend_failure(
            args.database, verify_only=args.verify_amend_failure_only
        )
    return run(
        args.database,
        stop_after_policy_recovery=args.stop_after_policy_recovery,
        stop_before_amend=args.stop_before_amend,
    )


if __name__ == "__main__":
    raise SystemExit(main())
