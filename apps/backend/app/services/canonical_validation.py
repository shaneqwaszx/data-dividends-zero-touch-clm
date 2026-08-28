"""Shared source-neutral canonical minimum policy for onboarding and CLM."""

from app.domain.jurisdiction import is_eligible_singapore_uen
from app.domain.models import CanonicalLegalEntity
from app.domain.target_submission import SubmissionCanonicalEntity


def validate_entity(
    entity: CanonicalLegalEntity | SubmissionCanonicalEntity,
) -> list[str]:
    """Return every accepted Phase 01 canonical minimum violation."""

    errors: list[str] = []
    if not is_eligible_singapore_uen(entity.registration_number):
        errors.append("registration number is not in the Phase 01 synthetic UEN format")
    if entity.legal_name is None or not entity.legal_name.strip():
        errors.append("legal name is missing")
    if entity.country_of_incorporation != "SG":
        errors.append("country of incorporation must be SG for this phase")
    if entity.party_type is None or not entity.party_type.strip():
        errors.append("party type is missing")
    if entity.registered_address is None:
        errors.append("registered address is missing")
    else:
        address = entity.registered_address
        if not address.address_line_1.strip():
            errors.append("registered address line 1 is missing")
        if not address.postal_code.strip():
            errors.append("registered address postal code is missing")
        if not address.country_code.strip():
            errors.append("registered address country is missing")
    return errors
