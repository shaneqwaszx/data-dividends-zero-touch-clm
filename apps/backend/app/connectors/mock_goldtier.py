"""Credential-free deterministic GoldTier connector for Phase 01."""

from app.connectors.errors import ConnectorError
from app.connectors.goldtier_models import (
    AmendPartyRequest,
    CreatePolicyRequest,
    CreateShellCustomerRequest,
    GoldTierOperationResult,
    GoldTierOutcome,
    GoldTierRequestMetadata,
    GoldTierSearchOutcome,
    GoldTierSearchResult,
    SearchPartyRequest,
)

CANONICAL_AMEND_ROUTE = "/v1/eds/parties/{partyId}/amend"


def _validate_context(source_case_id: str, metadata: GoldTierRequestMetadata) -> None:
    if source_case_id != metadata.source_case_id:
        raise ConnectorError("Mock request context failed validation")


class MockGoldTierConnector:
    """Simulate four EDS operations without HTTP or authentication."""

    def __init__(
        self,
        *,
        policy_validation_failure_keys: frozenset[str] = frozenset(),
        partial_amend_external_keys: frozenset[str] = frozenset(),
        match_found_external_keys: frozenset[str] = frozenset(),
    ) -> None:
        self._policy_validation_failure_keys = policy_validation_failure_keys
        self._partial_amend_external_keys = partial_amend_external_keys
        self._match_found_external_keys = match_found_external_keys
        self._external_key_by_party_id: dict[str, str] = {}

    def search_party(
        self, request: SearchPartyRequest, metadata: GoldTierRequestMetadata
    ) -> GoldTierSearchResult:
        del metadata
        if request.registration_number in self._match_found_external_keys:
            return GoldTierSearchResult(
                outcome=GoldTierSearchOutcome.MATCH_FOUND,
                status_code=200,
                matched_party_id=f"GT-MOCK-EXISTING-{request.registration_number}",
                message="An existing synthetic Mock party matched the registration number.",
            )
        return GoldTierSearchResult(
            outcome=GoldTierSearchOutcome.NO_MATCH,
            status_code=200,
            message=f"No mock party matched registration number {request.registration_number}.",
        )

    def create_shell_customer(
        self, request: CreateShellCustomerRequest, metadata: GoldTierRequestMetadata
    ) -> GoldTierOperationResult:
        _validate_context(request.source_context.source_case_id, metadata)
        party_id = f"GT-MOCK-{str(metadata.correlation_id)[:8].upper()}"
        return GoldTierOperationResult(
            outcome=GoldTierOutcome.SUCCESS,
            status_code=201,
            party_id=party_id,
            status="SHELL_CREATED",
            message="Mock shell customer created.",
        )

    def create_policy(
        self, request: CreatePolicyRequest, metadata: GoldTierRequestMetadata
    ) -> GoldTierOperationResult:
        _validate_context(request.source_context.source_case_id, metadata)
        if not request.customer_external_system or not request.customer_external_system_key:
            return GoldTierOperationResult(
                outcome=GoldTierOutcome.VALIDATION_FAILED,
                status_code=422,
                party_id=request.goldtier_id,
                status="VALIDATION_FAILED",
                error_code="GT_POLICY_EXTERNAL_REFERENCE_REQUIRED",
                message="Mock policy external reference validation failed.",
            )
        if request.customer_external_system_key in self._policy_validation_failure_keys:
            return GoldTierOperationResult(
                outcome=GoldTierOutcome.VALIDATION_FAILED,
                status_code=422,
                party_id=request.goldtier_id,
                status="VALIDATION_FAILED",
                error_code="GT_POLICY_VALIDATION_FAILED",
                message="Mock policy validation rejected this synthetic scenario.",
            )
        self._external_key_by_party_id[request.goldtier_id] = (
            request.customer_external_system_key
        )
        return GoldTierOperationResult(
            outcome=GoldTierOutcome.SUCCESS,
            status_code=201,
            party_id=request.goldtier_id,
            policy_id=f"POL-MOCK-{request.customer_external_system_key}",
            status="POLICY_CREATED",
            message="Mock Singapore policy created.",
        )

    def amend_party(
        self,
        party_id: str,
        request: AmendPartyRequest,
        metadata: GoldTierRequestMetadata,
    ) -> GoldTierOperationResult:
        _validate_context(request.source_context.source_case_id, metadata)
        external_key = self._external_key_by_party_id.get(party_id)
        if external_key in self._partial_amend_external_keys:
            return GoldTierOperationResult(
                outcome=GoldTierOutcome.PARTIAL_SUCCESS,
                status_code=207,
                party_id=party_id,
                status="PARTIALLY_ENRICHED",
                error_code="GT_OPTIONAL_SECTION_REVIEW",
                message="Core mock amendment committed; an optional section requires review.",
            )
        return GoldTierOperationResult(
            outcome=GoldTierOutcome.SUCCESS,
            status_code=200,
            party_id=party_id,
            status="ENRICHED",
            message="Mock party enriched.",
        )
