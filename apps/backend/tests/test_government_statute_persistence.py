"""D-125 schema 20: the founding statute on the Government confirmation, strict schema-19 reads."""

from copy import deepcopy

import pytest
from test_entity_types_persistence import CODEC, confirmed_government_snapshot

from app.persistence.errors import PersistenceDataInvalidError
from app.persistence.models import (
    CASE_SNAPSHOT_SCHEMA_VERSION,
    DurableCaseSnapshot,
    reject_government_statute_legacy_fields,
)
from app.persistence.mongo_case_store import _SUPPORTED_SCHEMA_VERSIONS
from app.services.government_status import government_status_confirmed

STATUTE_FIELDS = ("founding_statute", "statute_section", "government_body_type", "statute_match")


@pytest.fixture(scope="module")
def government() -> DurableCaseSnapshot:
    return confirmed_government_snapshot()


def as_schema_19(raw: dict) -> dict:
    """A schema-19 envelope: the confirmation without any D-125 key."""
    legacy = deepcopy(raw)
    legacy["schema_version"] = 19
    for name in STATUTE_FIELDS:
        legacy["onboarding"]["government_status_confirmation"].pop(name, None)
    return legacy


def confirmed(snapshot: DurableCaseSnapshot) -> bool:
    return government_status_confirmed(
        snapshot.onboarding,
        [item for item in snapshot.documents if item.is_current_evidence],
        confidence_threshold=float(
            snapshot.onboarding.policy_snapshot.idp_review_confidence_threshold
        ),
    )


def test_schema_20_round_trip_keeps_the_founding_statute(government):
    assert CASE_SNAPSHOT_SCHEMA_VERSION == 21
    assert _SUPPORTED_SCHEMA_VERSIONS[-3:] == [19, 20, 21]
    confirmation = government.onboarding.government_status_confirmation
    assert confirmation is not None
    assert confirmation.founding_statute == "Demo Parks FYP Test Authority Act"
    assert confirmation.government_body_type == "STATUTORY_BOARD"
    assert confirmation.statute_match == "MATCHED_AFTER_NORMALISATION"
    raw = CODEC._encode(government)  # noqa: SLF001
    assert raw["schema_version"] == 21
    stored = raw["onboarding"]["government_status_confirmation"]
    assert stored["founding_statute"] == "Demo Parks FYP Test Authority Act"
    assert stored["statute_section"] is None  # the store writes every declared field
    decoded = CODEC._decode(raw)  # noqa: SLF001
    assert decoded.onboarding.government_status_confirmation == confirmation
    assert CODEC._encode(decoded) == raw  # noqa: SLF001
    assert confirmed(decoded)


def test_a_schema_19_confirmation_loads_unchanged_but_must_be_confirmed_again(government):
    raw = CODEC._encode(government)  # noqa: SLF001
    legacy = as_schema_19(raw)
    original = deepcopy(legacy)
    decoded = CODEC._decode(legacy)  # noqa: SLF001
    assert legacy == original  # the read never rewrites the stored envelope
    assert decoded.schema_version == 21
    confirmation = decoded.onboarding.government_status_confirmation
    assert confirmation is not None
    assert all(getattr(confirmation, name) is None for name in STATUTE_FIELDS)
    original_confirmation = government.onboarding.government_status_confirmation
    assert confirmation.document_id == original_confirmation.document_id
    assert not confirmed(decoded)
    # Re-encoded as schema 20: every other field kept, the D-125 keys written as null.
    expected = deepcopy(original)
    expected["schema_version"] = 21
    expected["onboarding"]["government_status_confirmation"].update(
        dict.fromkeys(STATUTE_FIELDS)
    )
    assert CODEC._encode(decoded) == expected  # noqa: SLF001
    # The domain dump (used by digests) of an old confirmation has no D-125 keys.
    assert not set(STATUTE_FIELDS) & set(confirmation.model_dump())


@pytest.mark.parametrize("name", STATUTE_FIELDS)
@pytest.mark.parametrize("value", ["present", "null"])
def test_a_schema_19_envelope_cannot_carry_a_statute_field_even_if_null(government, name, value):
    raw = CODEC._encode(government)  # noqa: SLF001
    legacy = as_schema_19(raw)
    legacy["onboarding"]["government_status_confirmation"][name] = (
        None if value == "null" else {
            "founding_statute": "Demo Parks FYP Test Authority Act",
            "statute_section": "s 3",
            "government_body_type": "STATUTORY_BOARD",
            "statute_match": "MATCHED_AFTER_NORMALISATION",
        }[name]
    )
    with pytest.raises(PersistenceDataInvalidError):
        CODEC._decode(legacy)  # noqa: SLF001


@pytest.mark.parametrize("version", [17, 18])
def test_older_envelopes_cannot_carry_a_statute_field(government, version):
    with pytest.raises(ValueError, match="D-125"):
        reject_government_statute_legacy_fields(
            {"schema_version": version, "onboarding": {"government_status_confirmation": {
                "founding_statute": "Demo Parks FYP Test Authority Act"}}}
        )
    reject_government_statute_legacy_fields(
        {"schema_version": version, "onboarding": {"government_status_confirmation": None}}
    )
    reject_government_statute_legacy_fields({"schema_version": version, "onboarding": {}})


def test_a_schema_20_half_recorded_statute_is_refused(government):
    raw = CODEC._encode(government)  # noqa: SLF001
    raw["onboarding"]["government_status_confirmation"].pop("statute_match")
    with pytest.raises(PersistenceDataInvalidError):
        CODEC._decode(raw)  # noqa: SLF001


def test_schema_22_is_unsupported(government):
    from app.persistence.errors import PersistenceSchemaUnsupportedError

    raw = CODEC._encode(government)  # noqa: SLF001
    raw["schema_version"] = 22
    with pytest.raises((PersistenceSchemaUnsupportedError, PersistenceDataInvalidError)):
        CODEC._decode(raw)  # noqa: SLF001
