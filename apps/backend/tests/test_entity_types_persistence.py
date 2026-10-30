"""D-101 schema 17: Government status evidence, strict schema-16 reads and stable dumps."""

from copy import deepcopy
from datetime import UTC, datetime
from uuid import UUID

import pytest
from scripts.zero_touch_happy_path_fixtures import GOVERNMENT
from test_zero_touch_entity_types import confirm_government, government_at_status, lane

from app.persistence.errors import PersistenceDataInvalidError
from app.persistence.models import CASE_SNAPSHOT_SCHEMA_VERSION, DurableCaseSnapshot
from app.persistence.mongo_case_store import MongoCaseStore

CODEC = object.__new__(MongoCaseStore)


def confirmed_government_snapshot() -> DurableCaseSnapshot:
    with lane(GOVERNMENT) as (client, _, _, bundle):
        current = confirm_government(client, government_at_status(client)).json()
        cid = UUID(current["case"]["case_id"])
        return DurableCaseSnapshot(
            case_id=cid,
            revision=0,
            onboarding=bundle.onboarding.get(cid),
            documents=tuple(bundle.documents.list_for_case(cid)),
            ownership=bundle.ownership.get_for_case(cid),
            clm=bundle.clm.get_for_case(cid),
            automation=bundle.automation.get_for_case(cid),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )


@pytest.fixture(scope="module")
def government() -> DurableCaseSnapshot:
    return confirmed_government_snapshot()


def as_schema_16(raw: dict) -> dict:
    """An older envelope: none of the D-101 keys (the store writes every declared field)."""
    legacy = deepcopy(raw)
    legacy["schema_version"] = 16
    legacy["onboarding"].pop("government_status_confirmation")
    for document in legacy["documents"]:
        document.pop("government_status_observations")
    return legacy


def test_schema_17_round_trip_keeps_the_government_evidence(government):
    assert CASE_SNAPSHOT_SCHEMA_VERSION == 17
    assert government.onboarding.government_status_confirmation is not None
    assert government.documents[0].government_status_observations
    assert government.ownership is not None and government.ownership.legal_form == "GOVERNMENT"
    raw = CODEC._encode(government)  # noqa: SLF001
    assert raw["schema_version"] == 17
    decoded = CODEC._decode(raw)  # noqa: SLF001
    assert decoded.onboarding.government_status_confirmation == (
        government.onboarding.government_status_confirmation
    )
    assert decoded.documents == government.documents
    assert CODEC._encode(decoded) == raw  # noqa: SLF001


@pytest.mark.parametrize(
    "later",
    ["confirmation", "confirmation_null", "observations", "observations_empty",
     "legal_form", "hold", "blocker"],
)
def test_a_schema_16_envelope_cannot_carry_d101_evidence_even_if_null(government, later):
    raw = CODEC._encode(government)  # noqa: SLF001
    legacy = as_schema_16(raw)
    if later == "confirmation":
        legacy["onboarding"]["government_status_confirmation"] = raw["onboarding"][
            "government_status_confirmation"
        ]
    elif later == "confirmation_null":
        legacy["onboarding"]["government_status_confirmation"] = None
    elif later == "observations":
        legacy["documents"][0]["government_status_observations"] = raw["documents"][0][
            "government_status_observations"
        ]
    elif later == "observations_empty":
        legacy["documents"][0]["government_status_observations"] = []
    elif later == "legal_form":
        assert legacy["ownership"]["legal_form"] == "GOVERNMENT"
    elif later == "hold":
        legacy["ownership"]["legal_form"] = "OTHER"
        assert any(
            item["exception_type"] == "GOVERNMENT_STATUS_REQUIRED"
            for item in legacy["automation"]["exceptions"]
        )
    else:
        legacy["ownership"]["legal_form"] = "OTHER"
        legacy["automation"]["exceptions"] = []
        legacy["clm"]["readiness"]["blockers"] = ["GOVERNMENT_STATUS_REQUIRED"]
    with pytest.raises(PersistenceDataInvalidError):
        CODEC._decode(legacy)  # noqa: SLF001


def test_a_schema_16_case_upgrades_without_d101_evidence_and_is_not_rewritten():
    from test_slice_a_legacy_compatibility import rich_v7_snapshot

    source = rich_v7_snapshot("RECONCILIATION")
    raw = CODEC._encode(source)  # noqa: SLF001
    legacy = as_schema_16(raw)
    original = deepcopy(legacy)
    decoded = CODEC._decode(legacy)  # noqa: SLF001
    assert legacy == original  # the read never rewrites the stored envelope
    assert decoded.schema_version == 17
    assert decoded.onboarding.government_status_confirmation is None
    assert all(not item.government_status_observations for item in decoded.documents)
    assert CODEC._encode(decoded) == raw  # noqa: SLF001 - every other field retained


def test_d101_fields_do_not_change_dumps_of_cases_without_them(government):
    """Fingerprints and review digests built from model_dump stay stable for older cases."""
    from test_slice_a_legacy_compatibility import rich_v7_snapshot

    source = rich_v7_snapshot("RECONCILIATION")
    assert "government_status_confirmation" not in source.onboarding.model_dump()
    assert all(
        "government_status_observations" not in item.model_dump() for item in source.documents
    )
    assert "government_status_confirmation" in government.onboarding.model_dump()
    assert "government_status_observations" in government.documents[0].model_dump()


def test_a_schema_16_envelope_cannot_carry_a_partnership_agreement_share():
    from app.persistence.models import reject_entity_type_legacy_fields

    def legacy(reason: str) -> dict:
        discrepancies = [{"reason_code": reason}]
        return {"onboarding": {}, "ownership": {"document_discrepancies": discrepancies}}

    reject_entity_type_legacy_fields(legacy("OWNERSHIP_DOCUMENT_CONFLICT"))
    with pytest.raises(ValueError):
        reject_entity_type_legacy_fields(legacy("PARTNERSHIP_AGREEMENT_SHARE"))
