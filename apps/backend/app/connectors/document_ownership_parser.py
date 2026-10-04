"""Explicit labelled declarations/table rows become proposals, never graph arithmetic."""

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from pydantic import ValidationError

from app.connectors.idp import LocalDocumentProcessingError
from app.domain.documents import (
    DocumentPageEvidence,
    ExtractionQuality,
    OwnershipObservationValues,
)

_LABELS = {
    "shareholder": "owner_name",
    "owner": "owner_name",
    "shareholder name": "owner_name",
    "owner name": "owner_name",
    "type": "owner_type",
    "owner type": "owner_type",
    "registration identifier": "owner_registration_identifier",
    "owner registration identifier": "owner_registration_identifier",
    "shareholder registration identifier": "owner_registration_identifier",
    "shares": "share_count",
    "share count": "share_count",
    "percentage": "explicit_percentage",
    "ownership percentage": "explicit_percentage",
    "share class": "share_class",
    "owned entity": "owned_entity_name",
    "owned entity name": "owned_entity_name",
    "owned entity registration number": "owned_entity_registration_identifier",
    "owned entity registration identifier": "owned_entity_registration_identifier",
    "as of": "as_of_date",
    "as-of": "as_of_date",
    "as of date": "as_of_date",
    "total shares": "explicit_total_shares",
    "total issued shares": "explicit_total_shares",
}
_DECIMAL = re.compile(r"^(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d{1,6})?$")


def _key(label: str) -> str | None:
    return _LABELS.get(" ".join(label.casefold().strip().split()))


def _observation(
    values: dict[str, str],
    *,
    page: DocumentPageEvidence,
    row: int,
    evidence_score: float,
    ambiguous: bool,
) -> OwnershipObservationValues | None:
    if not values.get("owner_name"):
        return None
    normalized: dict[str, object] = dict(values)
    for key in ("share_count", "explicit_percentage", "explicit_total_shares"):
        value = values.get(key)
        if value is None:
            continue
        numeric = value.removesuffix("%").strip() if key == "explicit_percentage" else value
        if not _DECIMAL.fullmatch(numeric):
            return None
        try:
            normalized[key] = Decimal(numeric.replace(",", ""))
        except InvalidOperation:
            return None
    if "as_of_date" in normalized:
        try:
            normalized["as_of_date"] = date.fromisoformat(values["as_of_date"])
        except ValueError:
            return None
    if values.get("owner_type") not in {None, "NATURAL_PERSON", "LEGAL_ENTITY"}:
        return None
    try:
        return OwnershipObservationValues.model_validate(
            {
                **page.model_dump(exclude={"page_number", "source_reference"}),
                **normalized,
                "page_number": page.page_number,
                "source_reference": f"PAGE_{page.page_number}_OWNERSHIP_ROW_{row}",
                "evidence_score": min(evidence_score, 0.4) if ambiguous else evidence_score,
                "extraction_quality": ExtractionQuality.AMBIGUOUS
                if ambiguous
                else page.extraction_quality,
            }
        )
    except ValidationError:
        return None


def parse_ownership_observations(
    text: str,
    *,
    page: DocumentPageEvidence,
    evidence_score: float,
) -> tuple[OwnershipObservationValues, ...]:
    """Pipe-separated labelled rows, owner blocks, or explicitly headed pipe tables.

    Types use the exact source-neutral enum; dates are ISO. No inference from names,
    legal names, holder totals, percentages, registration patterns, or roles occurs.
    """

    rows: list[tuple[dict[str, str], int, bool]] = []
    current: dict[str, str] = {}
    variants: list[dict[str, str]] = []
    current_row = 0
    duplicate = False
    headers: list[str | None] | None = None

    def finish() -> None:
        nonlocal current, duplicate, variants
        if current:
            rows.extend((value, current_row, duplicate) for value in [*variants, current])
        if len(rows) > 128:
            raise LocalDocumentProcessingError("DOCUMENT_OUTPUT_LIMIT_EXCEEDED")
        current, duplicate, variants = {}, False, []

    for number, line in enumerate(text.splitlines(), 1):
        cells = [cell.strip() for cell in line.split("|")]
        potential_headers = [_key(cell) for cell in cells]
        if len(cells) > 1 and "owner_name" in potential_headers and all(potential_headers):
            finish()
            headers = potential_headers
            continue
        if headers is not None and len(cells) == len(headers) and ":" not in cells[0]:
            mapped: dict[str, str] = {}
            table_variants: list[dict[str, str]] = []
            for key, value in zip(headers, cells, strict=True):
                if key is None or not value:
                    continue
                if key in mapped and mapped[key] != value:
                    table_variants.append(dict(mapped))
                    if len(rows) + len(table_variants) + 1 > 128:
                        raise LocalDocumentProcessingError("DOCUMENT_OUTPUT_LIMIT_EXCEEDED")
                else:
                    for prior in table_variants:
                        if key not in prior:
                            prior[key] = value
                mapped[key] = value
            ambiguous_headers = len(set(headers)) != len(headers)
            rows.extend((value, number, ambiguous_headers) for value in [*table_variants, mapped])
            if len(rows) > 128:
                raise LocalDocumentProcessingError("DOCUMENT_OUTPUT_LIMIT_EXCEEDED")
            continue
        headers = None
        labelled: list[tuple[str, str]] = []
        for cell in cells:
            label, separator, value = cell.partition(":")
            key = _key(label)
            if separator and key is not None and value.strip():
                labelled.append((key, value.strip()))
        if not labelled:
            finish()
            continue
        if any(key == "owner_name" for key, _ in labelled):
            finish()
            current_row = number
        if not current and not any(key == "owner_name" for key, _ in labelled):
            continue
        for key, value in labelled:
            conflicting = key in current and current[key] != value
            if conflicting:
                variants.append(dict(current))
                if len(variants) > 128:
                    raise LocalDocumentProcessingError("DOCUMENT_OUTPUT_LIMIT_EXCEEDED")
            else:
                for prior in variants:
                    if key not in prior:
                        prior[key] = value
            duplicate |= conflicting
            current[key] = value
    finish()
    observations = [
        result
        for values, row, ambiguous in rows
        if (
            result := _observation(
                values, page=page, row=row, evidence_score=evidence_score, ambiguous=ambiguous
            )
        )
        is not None
    ]
    # Preserve distinct proposals. Conflicting repeated owners are visibly ambiguous.
    owner_bindings: dict[tuple[str, str | None, str | None], set[str]] = {}
    for item in observations:
        binding = (
            item.owner_name.casefold(),
            item.owner_registration_identifier,
            item.owned_entity_registration_identifier or item.owned_entity_name,
        )
        semantic = item.model_dump_json(exclude={"source_reference", "page_number"})
        owner_bindings.setdefault(binding, set()).add(semantic)
    return tuple(
        item.model_copy(
            update={
                "extraction_quality": ExtractionQuality.AMBIGUOUS,
                "evidence_score": min(item.evidence_score, 0.4),
            }
        )
        if len(
            owner_bindings[
                (
                    item.owner_name.casefold(),
                    item.owner_registration_identifier,
                    item.owned_entity_registration_identifier or item.owned_entity_name,
                )
            ]
        )
        > 1
        else item
        for item in observations
    )
