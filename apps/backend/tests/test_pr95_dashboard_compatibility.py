"""PR95 creator projection, scope and historical compatibility regressions."""

import pytest
from test_phase17_case_activity import _ActivityCollection
from test_phase18_case_portfolio import _mongo_portfolio_row

from app.domain.access import TeamId
from app.domain.case_management import CaseActivityQuery, CasePortfolioScope, PortfolioScopeKind
from app.persistence.errors import PersistenceDataInvalidError
from app.persistence.mongo_case_store import MongoCaseStore


@pytest.mark.parametrize("version", [9, 10])
def test_mongo_portfolio_decodes_validated_creator(version):
    raw = _mongo_portfolio_row()
    raw["schema_version"] = version
    raw["onboarding"]["created_by_actor_id"] = "maya-lim"
    store = object.__new__(MongoCaseStore)
    assert store._decode_portfolio(raw).created_by_actor_id == "maya-lim"


@pytest.mark.parametrize("value", [123, True, {}, "INVALID", "", "x" * 33])
def test_mongo_portfolio_rejects_invalid_creator(value):
    raw = _mongo_portfolio_row()
    raw["schema_version"] = 10
    raw["onboarding"]["created_by_actor_id"] = value
    with pytest.raises(PersistenceDataInvalidError):
        object.__new__(MongoCaseStore)._decode_portfolio(raw)


def test_mongo_portfolio_legacy_creator_stays_unknown_and_rejects_later_field():
    raw = _mongo_portfolio_row()
    store = object.__new__(MongoCaseStore)
    assert store._decode_portfolio(raw).created_by_actor_id is None
    raw["onboarding"]["created_by_actor_id"] = None
    with pytest.raises(PersistenceDataInvalidError):
        store._decode_portfolio(raw)


def test_mongo_activity_intersects_creator_with_authorized_scope_before_paging():
    collection = _ActivityCollection([{"invalid": [], "rows": []}])
    store = object.__new__(MongoCaseStore)
    store._collection = collection
    store.list_activity(CaseActivityQuery(
        scope=CasePortfolioScope(kind=PortfolioScopeKind.TEAM, team_id=TeamId.TEAM_A),
        created_by="sophia-ng", limit=1,
    ))
    pipeline, _ = collection.calls[0]
    assert pipeline[0]["$match"]["onboarding.team_id"] == "TEAM_A"
    assert "onboarding.created_by_actor_id" in repr(pipeline)
    assert "sophia-ng" in repr(pipeline)
