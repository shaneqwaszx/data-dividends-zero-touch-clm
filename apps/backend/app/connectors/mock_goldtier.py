"""Bounded, process-local GoldTier EDS Mock; no HTTP or authentication."""

from dataclasses import dataclass, replace
from threading import RLock

from pydantic import ValidationError

from app.connectors.errors import ConnectorError
from app.connectors.goldtier_models import (
    AmendPartyRequest,
    CreatePolicyRequest,
    CreateShellCustomerRequest,
    GoldTierOperationResult,
    GoldTierOutcome,
    GoldTierRequestMetadata,
    GoldTierSearchCandidate,
    GoldTierSearchOutcome,
    GoldTierSearchResult,
    SearchPartyRequest,
)
from app.domain.target_submission import GoldTierProviderMode

CANONICAL_AMEND_ROUTE = "/v1/eds/parties/{partyId}/amend"


def _validate_context(source_case_id: str, metadata: GoldTierRequestMetadata) -> None:
    if source_case_id != metadata.source_case_id:
        raise ConnectorError("Mock request context failed validation")


@dataclass(frozen=True)
class _MockCustomer:
    """Provider facts only. Case state, history and execution belong to the ledger."""

    identity: GoldTierSearchCandidate
    party_role: str | None = None
    party_type: str | None = None
    external_system: str | None = None
    policy_id: str | None = None
    policy_status: str | None = None
    amend_status: str | None = None


def _identity(**values: str | None) -> GoldTierSearchCandidate:
    try:
        return GoldTierSearchCandidate.model_validate(values)
    except ValidationError:
        raise ConnectorError("Mock identity cannot be represented safely") from None


def _bounded_text(value: str) -> str:
    if not value or len(value) > 160 or any(ord(char) < 32 for char in value):
        raise ConnectorError("Mock field cannot be represented safely")
    return value


def _failure(party_id: str | None, code: str) -> GoldTierOperationResult:
    return GoldTierOperationResult(
        outcome=GoldTierOutcome.VALIDATION_FAILED,
        status_code=422,
        party_id=party_id,
        status="VALIDATION_FAILED",
        error_code=code,
        message="The local Mock operation could not be applied.",
    )


class MockGoldTierConnector:
    """Retain accepted synthetic provider facts in this instance only.

    A fresh instance starts without prior runtime customers. Constructor matches are
    explicit synthetic fixtures, never prior-case, Policy or verified-readback proof.
    No idempotency, retry, workflow, persistence, seed or reset API is owned here.
    """

    environment = GoldTierProviderMode.MOCK

    def __init__(
        self,
        *,
        policy_validation_failure_keys: frozenset[str] = frozenset(),
        partial_amend_external_keys: frozenset[str] = frozenset(),
        match_found_external_keys: frozenset[str] = frozenset(),
        amend_validation_failure_keys: frozenset[str] = frozenset(),
        max_customers: int = 1000,
    ) -> None:
        if type(max_customers) is not int or not 1 <= max_customers <= 10000:
            raise ValueError("Mock customer capacity is invalid")
        if any(
            len(keys) > max_customers
            for keys in (
                policy_validation_failure_keys,
                partial_amend_external_keys,
                match_found_external_keys,
                amend_validation_failure_keys,
            )
        ):
            raise ValueError("Mock fixtures exceed local capacity")
        self._policy_validation_failure_keys = policy_validation_failure_keys
        self._partial_amend_external_keys = partial_amend_external_keys
        self._amend_validation_failure_keys = amend_validation_failure_keys
        self._max_customers = max_customers
        self._lock = RLock()
        self._customers = {
            f"GT-MOCK-EXISTING-{key}": _MockCustomer(
                identity=_identity(
                    party_id=f"GT-MOCK-EXISTING-{key}",
                    registration_number=key,
                    country="SG",
                ),
                external_system="ACRA",
            )
            for key in sorted(match_found_external_keys)
        }

    def search_party(
        self, request: SearchPartyRequest, metadata: GoldTierRequestMetadata
    ) -> GoldTierSearchResult:
        del metadata
        if not isinstance(request, SearchPartyRequest):
            raise ConnectorError("Mock Search request dialect is unsupported")
        with self._lock:
            candidates = tuple(
                customer.identity
                for customer in self._customers.values()
                if customer.external_system == "ACRA"
                and customer.identity.registration_number == request.registration_number
            )
        if len(candidates) > 25:
            return GoldTierSearchResult(
                outcome=GoldTierSearchOutcome.FAILURE,
                status_code=422,
                error_code="GT_SEARCH_FAILED",
                message="Mock Search exceeds the safe result bound.",
            )
        if candidates:
            unique = len(candidates) == 1
            return GoldTierSearchResult(
                outcome=GoldTierSearchOutcome.MATCH_FOUND
                if unique
                else GoldTierSearchOutcome.MULTIPLE_MATCHES,
                status_code=200,
                matched_party_id=candidates[0].party_id if unique else None,
                candidates=candidates,
                message="Synthetic Mock customers matched the exact registration number.",
            )
        return GoldTierSearchResult(
            outcome=GoldTierSearchOutcome.NO_MATCH,
            status_code=200,
            message="No mock party matched the exact registration number.",
        )

    def create_shell_customer(
        self, request: CreateShellCustomerRequest, metadata: GoldTierRequestMetadata
    ) -> GoldTierOperationResult:
        _validate_context(request.source_context.source_case_id, metadata)
        # Use the complete accepted synthetic correlation identity, not a truncated prefix.
        party_id = f"GT-MOCK-{metadata.correlation_id.hex.upper()}"
        customer = _MockCustomer(
            identity=_identity(
                party_id=party_id,
                legal_name=request.party.names.legal_name,
                country=request.party.non_individual_profile.country_of_incorporation,
            ),
            party_role=_bounded_text(request.party.party_role),
            party_type=_bounded_text(request.party.party_type),
        )
        with self._lock:
            if party_id in self._customers or len(self._customers) >= self._max_customers:
                return _failure(None, "GT_SHELL_FAILED")
            self._customers[party_id] = customer
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
            return _failure(request.goldtier_id, "GT_POLICY_EXTERNAL_REFERENCE_REQUIRED")
        if request.customer_external_system_key in self._policy_validation_failure_keys:
            return _failure(request.goldtier_id, "GT_POLICY_VALIDATION_FAILED")
        external_system = _bounded_text(request.customer_external_system)
        external_key = _bounded_text(request.customer_external_system_key)
        policy_id = f"POL-MOCK-{external_key}"
        result = GoldTierOperationResult(
            outcome=GoldTierOutcome.SUCCESS,
            status_code=201,
            party_id=request.goldtier_id,
            policy_id=policy_id,
            status="POLICY_CREATED",
            message="Mock Singapore policy created.",
        )
        with self._lock:
            customer = self._customers.get(request.goldtier_id)
            if customer is None:
                return _failure(request.goldtier_id, "GT_POLICY_VALIDATION_FAILED")
            registration = external_key if external_system == "ACRA" else None
            if customer.identity.registration_number is not None and (
                customer.identity.registration_number != registration
                or customer.external_system != external_system
            ):
                return _failure(request.goldtier_id, "GT_POLICY_VALIDATION_FAILED")
            identity = _identity(
                **{**customer.identity.model_dump(), "registration_number": registration},
            )
            self._customers[request.goldtier_id] = replace(
                customer,
                identity=identity,
                external_system=external_system,
                policy_id=policy_id,
                policy_status=result.status,
            )
        return result

    def amend_party(
        self,
        party_id: str,
        request: AmendPartyRequest,
        metadata: GoldTierRequestMetadata,
    ) -> GoldTierOperationResult:
        _validate_context(request.source_context.source_case_id, metadata)
        with self._lock:
            customer = self._customers.get(party_id)
            if customer is None:
                return _failure(party_id, "GT_AMEND_FAILED")
            external_key = customer.identity.registration_number
            if external_key in self._amend_validation_failure_keys:
                return _failure(party_id, "GT_AMEND_FAILED")
            if external_key in self._partial_amend_external_keys:
                self._customers[party_id] = replace(customer, amend_status="PARTIALLY_ENRICHED")
                return GoldTierOperationResult(
                    outcome=GoldTierOutcome.PARTIAL_SUCCESS,
                    status_code=207,
                    party_id=party_id,
                    status="PARTIALLY_ENRICHED",
                    error_code="GT_OPTIONAL_SECTION_REVIEW",
                    message="Core mock amendment committed; an optional section requires review.",
                )
            # The accepted mapper supplies one registered address. Other shapes are not
            # interpreted as a primary address or hidden enrichment.
            address = request.party.addresses[0] if len(request.party.addresses) == 1 else None
            address_text = (
                ", ".join(
                    item
                    for item in (
                        address.address_line_1,
                        address.address_line_2,
                        address.postal_code,
                        address.country,
                    )
                    if item
                )
                if address is not None
                else None
            )
            identity = _identity(
                **{
                    **customer.identity.model_dump(),
                    "legal_name": request.party.names.legal_name,
                    "registered_address": address_text,
                },
            )
            self._customers[party_id] = replace(
                customer,
                identity=identity,
                party_type=_bounded_text(request.party_type),
                amend_status="ENRICHED",
            )
        return GoldTierOperationResult(
            outcome=GoldTierOutcome.SUCCESS,
            status_code=200,
            party_id=party_id,
            status="ENRICHED",
            message="Mock party enriched.",
        )
