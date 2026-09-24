"""Provider-neutral GoldTier connector and request-mapper protocols."""

from typing import Any, Protocol

from app.connectors.goldtier_models import (
    AmendPartyRequest,
    CreatePolicyRequest,
    CreateShellCustomerRequest,
    GoldTierOperationResult,
    GoldTierRequestMetadata,
    GoldTierSearchResult,
    SearchPartyRequest,
)
from app.connectors.goldtier_xpi_models import (
    XpiAmendCustomerRequest,
    XpiCreateCustomerPolicyRequest,
    XpiCreateCustomerRequest,
    XpiCustomerSearchRequest,
)
from app.domain.target_preparation import GoldTierRequestPreview
from app.domain.target_submission import GoldTierProviderMode, GoldTierSubmissionInput

GoldTierSearchRequest = SearchPartyRequest | XpiCustomerSearchRequest
GoldTierShellRequest = CreateShellCustomerRequest | XpiCreateCustomerRequest
GoldTierPolicyRequest = CreatePolicyRequest | XpiCreateCustomerPolicyRequest
GoldTierAmendRequest = AmendPartyRequest | XpiAmendCustomerRequest


class GoldTierRequestMapper(Protocol):
    """Own one target dialect without becoming an orchestration owner."""

    environment: GoldTierProviderMode

    def build_search_request(
        self, submission: GoldTierSubmissionInput
    ) -> GoldTierSearchRequest: ...

    def build_shell_request(
        self, submission: GoldTierSubmissionInput
    ) -> GoldTierShellRequest: ...

    def build_policy_request(
        self, submission: GoldTierSubmissionInput, party_id: str
    ) -> GoldTierPolicyRequest: ...

    def build_amend_request(
        self, submission: GoldTierSubmissionInput, party_id: str
    ) -> GoldTierAmendRequest: ...

    def build_preview(self, submission: GoldTierSubmissionInput) -> GoldTierRequestPreview: ...

    def validate_pre_dispatch(self, submission: GoldTierSubmissionInput) -> None: ...


class GoldTierConnector(Protocol):
    """Target boundary; real and mock implementations share this interface."""

    environment: GoldTierProviderMode

    def search_party(
        self, request: Any, metadata: GoldTierRequestMetadata
    ) -> GoldTierSearchResult: ...

    def create_shell_customer(
        self, request: Any, metadata: GoldTierRequestMetadata
    ) -> GoldTierOperationResult: ...

    def create_policy(
        self, request: Any, metadata: GoldTierRequestMetadata
    ) -> GoldTierOperationResult: ...

    def amend_party(
        self,
        party_id: str,
        request: Any,
        metadata: GoldTierRequestMetadata,
    ) -> GoldTierOperationResult: ...
