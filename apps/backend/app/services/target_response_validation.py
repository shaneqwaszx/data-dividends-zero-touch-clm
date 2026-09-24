"""Revalidate untrusted GoldTier connector responses before business use."""

from pydantic import BaseModel

from app.connectors.goldtier_models import (
    GoldTierOperationResult,
    GoldTierOutcome,
    GoldTierSearchOutcome,
    GoldTierSearchResult,
)


class InvalidTargetResponseError(Exception):
    """Internal trust-boundary signal that never carries connector data."""


def _revalidate[ResponseT: BaseModel](
    response: object, response_type: type[ResponseT]
) -> ResponseT:
    try:
        if not isinstance(response, BaseModel):
            raise TypeError
        payload = response.model_dump(mode="python")
        return response_type.model_validate(payload)
    except Exception:
        raise InvalidTargetResponseError from None


def validate_search_response(response: object) -> GoldTierSearchResult:
    trusted = _revalidate(response, GoldTierSearchResult)
    if trusted.outcome in {
        GoldTierSearchOutcome.NO_MATCH,
        GoldTierSearchOutcome.MATCH_FOUND,
        GoldTierSearchOutcome.MULTIPLE_MATCHES,
    }:
        valid = 200 <= trusted.status_code < 300 and (
            (
                trusted.outcome == GoldTierSearchOutcome.NO_MATCH
                and not trusted.candidates
            )
            or (
                trusted.outcome == GoldTierSearchOutcome.MATCH_FOUND
                and trusted.matched_party_id is not None
                and len(trusted.candidates) <= 1
            )
            or (
                trusted.outcome == GoldTierSearchOutcome.MULTIPLE_MATCHES
                and len(trusted.candidates) >= 2
            )
        )
    else:
        valid = trusted.status_code >= 400 and trusted.error_code is not None
    if not valid:
        raise InvalidTargetResponseError
    return trusted


def validate_shell_response(response: object) -> GoldTierOperationResult:
    trusted = _revalidate(response, GoldTierOperationResult)
    if trusted.outcome == GoldTierOutcome.SUCCESS:
        valid = (
            200 <= trusted.status_code < 300
            and trusted.party_id is not None
            and trusted.status == "SHELL_CREATED"
        )
    else:
        valid = (
            trusted.status_code >= 400
            and trusted.error_code is not None
            and trusted.status in {"SHELL_FAILED", "VALIDATION_FAILED"}
        )
    if not valid:
        raise InvalidTargetResponseError
    return trusted


def validate_policy_response(
    response: object, *, expected_party_id: str
) -> GoldTierOperationResult:
    trusted = _revalidate(response, GoldTierOperationResult)
    party_matches = trusted.party_id in {None, expected_party_id}
    if trusted.outcome == GoldTierOutcome.SUCCESS:
        valid = (
            200 <= trusted.status_code < 300
            and party_matches
            and trusted.status == "POLICY_CREATED"
        )
    else:
        valid = (
            trusted.status_code >= 400
            and party_matches
            and trusted.error_code is not None
            and trusted.status == "VALIDATION_FAILED"
        )
    if not valid:
        raise InvalidTargetResponseError
    return trusted


def validate_amend_response(
    response: object, *, expected_party_id: str
) -> GoldTierOperationResult:
    trusted = _revalidate(response, GoldTierOperationResult)
    party_matches = trusted.party_id in {None, expected_party_id}
    if trusted.outcome == GoldTierOutcome.SUCCESS:
        valid = (
            200 <= trusted.status_code < 300
            and party_matches
            and trusted.status == "ENRICHED"
        )
    elif trusted.outcome == GoldTierOutcome.PARTIAL_SUCCESS:
        valid = (
            200 <= trusted.status_code < 300
            and party_matches
            and trusted.error_code is not None
            and trusted.status == "PARTIALLY_ENRICHED"
        )
    else:
        valid = (
            trusted.status_code >= 400
            and party_matches
            and trusted.error_code is not None
            and trusted.status in {"AMEND_FAILED", "VALIDATION_FAILED"}
        )
    if not valid:
        raise InvalidTargetResponseError
    return trusted
