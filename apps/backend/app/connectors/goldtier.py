"""GoldTier connector protocol for the Phase 01 operation subset."""

from typing import Protocol

from app.connectors.goldtier_models import (
    AmendPartyRequest,
    CreatePolicyRequest,
    CreateShellCustomerRequest,
    GoldTierOperationResult,
    GoldTierRequestMetadata,
    GoldTierSearchResult,
    SearchPartyRequest,
)


class GoldTierConnector(Protocol):
    """Target boundary; real and mock implementations share this interface."""

    def search_party(
        self, request: SearchPartyRequest, metadata: GoldTierRequestMetadata
    ) -> GoldTierSearchResult: ...

    def create_shell_customer(
        self, request: CreateShellCustomerRequest, metadata: GoldTierRequestMetadata
    ) -> GoldTierOperationResult: ...

    def create_policy(
        self, request: CreatePolicyRequest, metadata: GoldTierRequestMetadata
    ) -> GoldTierOperationResult: ...

    def amend_party(
        self,
        party_id: str,
        request: AmendPartyRequest,
        metadata: GoldTierRequestMetadata,
    ) -> GoldTierOperationResult: ...
