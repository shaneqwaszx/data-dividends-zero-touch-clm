"""Explicit historical synthetic shapes; never a runtime migration or decoder."""

from typing import Any

from app.persistence.models import DurableCaseSnapshot
from app.persistence.mongo_case_store import MongoCaseStore


def drop_entity_category(value: Any) -> Any:
    """A copy without any D-114 (schema 18) entity category, for an older envelope."""
    if isinstance(value, dict):
        return {key: drop_entity_category(item) for key, item in value.items()
                if key != "entity_category"}
    if isinstance(value, list):
        return [drop_entity_category(item) for item in value]
    return value


def without_d101_fields(raw: dict[str, Any]) -> dict[str, Any]:
    """A copy without the schema-17 D-101 and schema-18 D-114 keys, for an older envelope."""
    legacy = {**raw, "onboarding": drop_entity_category(dict(raw["onboarding"]))}
    legacy["onboarding"].pop("government_status_confirmation", None)
    legacy["documents"] = [
        {key: value for key, value in document.items() if key != "government_status_observations"}
        for document in raw.get("documents", ())
    ]
    return legacy


def omit_session2_fields(raw: dict[str, Any]) -> None:
    """Remove only later-version fields while building an older test fixture."""
    raw["onboarding"].pop("created_by_actor_id", None)
    raw["onboarding"].pop("target_classification_selections", None)
    raw["onboarding"].pop("government_status_confirmation", None)  # D-101 (schema 17)
    raw["onboarding"] = drop_entity_category(raw["onboarding"])  # D-114 (schema 18)
    metadata = (
        "extraction_method", "extraction_quality", "score_kind", "score_formula",
        "raw_ocr_mean_confidence", "raw_ocr_word_count", "candidates",
    )
    for document in raw.get("documents", ()):
        for name in (
            "document_version", "pages", "ownership_observations", "classification_observations",
            "content_sha256", "government_status_observations",
        ):
            document.pop(name, None)
        for field in document.get("fields", ()):
            for name in metadata:
                field.pop(name, None)
    ownership = raw.get("ownership")
    if ownership is None:
        return
    for index, record in enumerate((ownership, *ownership.get("prior_analyses", ()))):
        for name in (
            "document_observations", "document_bindings", "document_discrepancies",
            "source_classification", "supplemental_parties", "supplemental_relationships",
            "supplemental_evidence",
        ):
            record.pop(name, None)
        if index:
            record.pop("manual_review_receipt", None)
        receipt = record.get("manual_review_receipt")
        if receipt is not None:
            for name in (
                "source_selection", "observed_document_versions", "selected_observation_ids",
                "replaced_analysis_id", "replaced_ownership_version",
            ):
                receipt.pop(name, None)


def assert_retained_legacy_content(
    actual: DurableCaseSnapshot, source: DurableCaseSnapshot
) -> None:
    """Compare all durable historical content, including excluded persistence proof."""
    codec = object.__new__(MongoCaseStore)
    actual_raw = codec._encode(actual)  # noqa: SLF001 - explicit synthetic fixture boundary
    source_raw = codec._encode(source)  # noqa: SLF001
    omit_session2_fields(actual_raw)
    omit_session2_fields(source_raw)
    assert actual_raw == source_raw
    assert actual.onboarding.created_by_actor_id is None
    assert all(document.document_version is None for document in actual.documents)
    assert all(
        field.extraction_method == "UNKNOWN" and field.score_kind == "LEGACY_UNSPECIFIED"
        for document in actual.documents for field in document.fields
    )
