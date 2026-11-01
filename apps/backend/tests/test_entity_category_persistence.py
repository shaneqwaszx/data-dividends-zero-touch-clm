"""D-114 schema 18: the entity category, strict schema-17 reads and stable Company dumps."""

from copy import deepcopy
from datetime import UTC, datetime
from uuid import UUID

import pytest
from scripts.zero_touch_happy_path_fixtures import COMPANIES, GOVERNMENT
from test_zero_touch_entity_types import create, government_at_status, lane

from app.domain.models import EntityCategory
from app.persistence.errors import PersistenceDataInvalidError
from app.persistence.models import (
    CASE_SNAPSHOT_SCHEMA_VERSION,
    DurableCaseSnapshot,
    DurableCaseSnapshotV17,
)
from app.persistence.mongo_case_store import MongoCaseStore

CODEC = object.__new__(MongoCaseStore)
ALPHA = COMPANIES[0]


def snapshot(company, start) -> DurableCaseSnapshot:
    with lane(company) as (client, _, _, bundle):
        current = start(client)
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


def as_schema_17(raw: dict) -> dict:
    """An older envelope: no D-114 key anywhere (the store writes every declared field)."""

    def strip(item):
        if isinstance(item, dict):
            item.pop("entity_category", None)
            for child in item.values():
                strip(child)
        elif isinstance(item, list):
            for child in item:
                strip(child)

    legacy = deepcopy(raw)
    legacy["schema_version"] = 17
    strip(legacy["onboarding"])
    return legacy


@pytest.fixture(scope="module")
def government() -> DurableCaseSnapshot:
    return snapshot(GOVERNMENT, government_at_status)


@pytest.fixture(scope="module")
def company() -> DurableCaseSnapshot:
    return snapshot(ALPHA, lambda client: create(client, ALPHA))


def test_schema_18_round_trip_keeps_the_government_category(government):
    assert CASE_SNAPSHOT_SCHEMA_VERSION == 18
    raw = CODEC._encode(government)  # noqa: SLF001
    assert raw["schema_version"] == 18
    assert raw["onboarding"]["initial_identity"]["entity_category"] == "GOVERNMENT"
    decoded = CODEC._decode(raw)  # noqa: SLF001
    assert decoded.onboarding.initial_identity is not None
    assert decoded.onboarding.initial_identity.entity_category == EntityCategory.GOVERNMENT


@pytest.mark.parametrize("value", ["GOVERNMENT", "COMPANY"])
def test_a_schema_17_envelope_cannot_carry_an_entity_category_even_company(company, value):
    raw = as_schema_17(CODEC._encode(company))  # noqa: SLF001
    raw["onboarding"]["initial_identity"]["entity_category"] = value
    with pytest.raises(PersistenceDataInvalidError):
        CODEC._decode(raw)  # noqa: SLF001
    with pytest.raises(ValueError):
        DurableCaseSnapshotV17.model_validate(raw)


def test_a_nested_category_in_an_older_envelope_is_also_rejected(company):
    raw = as_schema_17(CODEC._encode(company))  # noqa: SLF001
    raw["onboarding"]["initial_target_search_attempts"] = [
        {"identity": {**raw["onboarding"]["initial_identity"], "entity_category": "GOVERNMENT"}}
    ]
    with pytest.raises(PersistenceDataInvalidError):
        CODEC._decode(raw)  # noqa: SLF001


def test_a_schema_17_case_reads_as_company_and_is_not_rewritten(company):
    raw = as_schema_17(CODEC._encode(company))  # noqa: SLF001
    before = deepcopy(raw)
    decoded = CODEC._decode(raw)  # noqa: SLF001
    assert decoded.schema_version == 18
    assert decoded.onboarding.initial_identity is not None
    assert decoded.onboarding.initial_identity.entity_category == EntityCategory.COMPANY
    assert raw == before


def test_company_dumps_carry_no_category_so_fingerprints_are_stable(company):
    # Fingerprints and API projections use model_dump, which omits the COMPANY default; the
    # schema-18 Mongo document stores every declared field, the category included.
    assert "entity_category" not in company.onboarding.model_dump_json()
    raw = CODEC._encode(company)  # noqa: SLF001
    assert raw["onboarding"]["initial_identity"]["entity_category"] == "COMPANY"
