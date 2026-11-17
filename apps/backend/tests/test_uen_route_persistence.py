"""D-114 schema 18: the system-set UEN route, strict schema-17 reads and stable dumps."""

from copy import deepcopy
from datetime import UTC, datetime
from uuid import UUID

import pytest
from s2_legacy_schema_fixtures import drop_uen_route
from scripts.zero_touch_happy_path_fixtures import COMPANIES, GOVERNMENT
from test_zero_touch_entity_types import create, government_at_status, lane

from app.domain.uen_route import UenRoute
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
        cid = UUID(start(client)["case"]["case_id"])
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
    """An older envelope: no D-114 key (the store writes every declared field)."""
    legacy = deepcopy(raw)
    legacy["schema_version"] = 17
    legacy["onboarding"] = drop_uen_route(legacy["onboarding"])
    return legacy


@pytest.fixture(scope="module")
def government() -> DurableCaseSnapshot:
    return snapshot(GOVERNMENT, government_at_status)


@pytest.fixture(scope="module")
def company() -> DurableCaseSnapshot:
    return snapshot(ALPHA, lambda client: create(client, ALPHA))


def test_schema_18_round_trip_keeps_the_system_route(government):
    assert CASE_SNAPSHOT_SCHEMA_VERSION == 21
    raw = CODEC._encode(government)  # noqa: SLF001
    assert raw["schema_version"] == 21
    assert raw["onboarding"]["uen_route"]["route"] == "GOVERNMENT_REGISTER"
    assert raw["onboarding"]["uen_route"]["pq_code"] == "GB"
    decoded = CODEC._decode(raw)  # noqa: SLF001
    assert decoded.onboarding.uen_route is not None
    assert decoded.onboarding.uen_route.route == UenRoute.GOVERNMENT_REGISTER
    assert decoded.onboarding.uen_route == government.onboarding.uen_route


@pytest.mark.parametrize("value", ["route", None], ids=["route", "null"])
def test_a_schema_17_envelope_cannot_carry_a_uen_route_even_if_null(company, value):
    raw = as_schema_17(CODEC._encode(company))  # noqa: SLF001
    current = CODEC._encode(company)["onboarding"]["uen_route"]  # noqa: SLF001
    raw["onboarding"]["uen_route"] = current if value == "route" else None
    with pytest.raises(PersistenceDataInvalidError):
        CODEC._decode(raw)  # noqa: SLF001
    with pytest.raises(ValueError):
        DurableCaseSnapshotV17.model_validate(raw)


def test_a_schema_17_case_reads_without_a_route_and_is_not_rewritten(company):
    raw = as_schema_17(CODEC._encode(company))  # noqa: SLF001
    before = deepcopy(raw)
    decoded = CODEC._decode(raw)  # noqa: SLF001
    assert decoded.schema_version == 21
    assert decoded.onboarding.uen_route is None
    assert raw == before


def test_a_case_without_a_route_dumps_as_before(company):
    # Fingerprints and API projections use model_dump, which omits an unset route.
    unrouted = company.onboarding.model_copy(update={"uen_route": None})
    assert "uen_route" not in unrouted.model_dump()
    assert company.onboarding.uen_route is not None
    assert company.onboarding.uen_route.route == UenRoute.ACRA
