"""ST-7 standing GoldTier Sandbox read: a server-side daily read budget (synthetic only).

Reads are claimed before anything leaves; an exhausted or unavailable budget sends
nothing and surfaces as a recoverable rate-limit-class Search failure. Writes are not
counted and stay governed by the D-137 window.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier, Thread
from typing import Any

import pytest
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError
from scripts.mongo_test_safety import (
    cleanup_ephemeral_mongo_database,
    generate_ephemeral_mongo_database,
)
from test_aws_goldtier_sandbox_readiness import (
    NAME,
    UEN,
    OfficialSourceAcra,
    ok,
    retained_search,
    staging_settings,
)
from test_goldtier_xpi_sandbox import (
    FakeXpiTransport,
    _metadata,
    _sandbox_zero_touch_system,
    _xpi_connector,
)

from app.composition import STAGING_SANDBOX_IDENTITY_POLICY
from app.connectors.goldtier_read_budget import (
    InMemoryGoldTierReadBudget,
    UnlimitedGoldTierReadBudget,
    budget_day,
)
from app.connectors.goldtier_xpi import (
    GoldTierXpiRateLimitedError,
    GoldTierXpiReadBudgetExhaustedError,
    GoldTierXpiReadBudgetUnavailableError,
    public_goldtier_xpi_search_error,
)
from app.connectors.goldtier_xpi_models import XpiCustomerSearchRequest
from app.persistence.composition import build_goldtier_read_budget
from app.persistence.errors import PersistenceUnavailableError
from app.persistence.mongo_goldtier_read_budget import MongoGoldTierReadBudget

NOW = datetime(2026, 11, 16, 23, 30, tzinfo=UTC)


def test_the_budget_counts_per_utc_day_and_refuses_at_the_limit() -> None:
    budget = InMemoryGoldTierReadBudget(2)
    assert [budget.claim(NOW) for _ in range(3)] == [True, True, False]
    assert budget.used(NOW) == 2
    assert budget.claim(NOW + timedelta(hours=1))  # next UTC day
    assert budget_day(datetime(2026, 11, 16, 23, 30, tzinfo=UTC)) == "2026-11-16"
    with pytest.raises(ValueError):
        budget_day(datetime(2026, 11, 16))


def test_concurrent_claims_never_exceed_the_limit() -> None:
    budget = InMemoryGoldTierReadBudget(1)
    barrier = Barrier(8)
    results: list[bool] = []

    def claim() -> None:
        barrier.wait()
        results.append(budget.claim(NOW))

    threads = [Thread(target=claim) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert results.count(True) == 1


def _read(connector: Any) -> Any:
    return connector.search_party(XpiCustomerSearchRequest(goldtier_id="143887"), _metadata())


def test_an_exhausted_budget_sends_nothing() -> None:
    transport = FakeXpiTransport([ok([])])
    connector = _xpi_connector(transport)
    connector._read_budget = InMemoryGoldTierReadBudget(0)  # noqa: SLF001
    with pytest.raises(GoldTierXpiReadBudgetExhaustedError) as error:
        _read(connector)
    assert transport.calls == []
    assert isinstance(error.value, GoldTierXpiRateLimitedError)
    assert public_goldtier_xpi_search_error(error.value).code == "GT_XPI_READ_BUDGET_EXHAUSTED"


def test_an_unavailable_budget_refuses_the_read() -> None:
    class Broken:
        limit = 5

        def claim(self, now: datetime) -> bool:
            raise PersistenceUnavailableError

        def used(self, now: datetime) -> int:
            raise PersistenceUnavailableError

    transport = FakeXpiTransport([ok([])])
    connector = _xpi_connector(transport)
    connector._read_budget = Broken()  # noqa: SLF001
    with pytest.raises(GoldTierXpiReadBudgetUnavailableError) as error:
        _read(connector)
    assert transport.calls == []
    assert public_goldtier_xpi_search_error(error.value).code == "GT_XPI_READ_BUDGET_UNAVAILABLE"


def test_a_claimed_read_is_sent_and_counted() -> None:
    transport = FakeXpiTransport([ok([]), ok([])])
    connector = _xpi_connector(transport)
    budget = InMemoryGoldTierReadBudget(1)
    connector._read_budget = budget  # noqa: SLF001
    _read(connector)
    assert len(transport.calls) == 1 and budget.used(datetime.now(UTC)) == 1
    with pytest.raises(GoldTierXpiReadBudgetExhaustedError):
        _read(connector)
    assert len(transport.calls) == 1


def test_writes_are_not_counted_and_stay_window_governed() -> None:
    from app.connectors.goldtier_xpi_models import XpiCreateCustomerRequest  # noqa: F401

    transport = FakeXpiTransport([ok({"goldTierId": 12345})])
    connector = _xpi_connector(transport, allow_writes=True)
    connector._read_budget = InMemoryGoldTierReadBudget(0)  # noqa: SLF001
    # A mutation never consults the read budget: the connector's write gate alone decides.
    response = connector._request(  # noqa: SLF001
        "POST",
        connector._connection.operation_endpoint("SHELL"),  # noqa: SLF001
        metadata=_metadata(),
        body={},
        mutation=True,
        operation="SHELL",
    )
    assert response.status_code == 200 and len(transport.calls) == 1


def test_effective_limit_is_zero_in_staging_until_set() -> None:
    assert staging_settings().goldtier_sandbox_effective_read_limit() == 0
    assert (
        staging_settings(
            goldtier_sandbox_daily_read_limit=50
        ).goldtier_sandbox_effective_read_limit()
        == 50
    )
    with pytest.raises(ValueError):
        staging_settings(goldtier_sandbox_daily_read_limit=501)


def test_build_binds_no_budget_for_mock_and_memory_budget_for_sandbox() -> None:
    assert (
        build_goldtier_read_budget(staging_settings(goldtier_connector_mode="mock")).budget is None
    )
    sandbox_memory = staging_settings(
        app_env="test",
        clm_persistence_mode="memory",
        mongo_uri=None,
        goldtier_sandbox_daily_read_limit=3,
    )
    binding = build_goldtier_read_budget(sandbox_memory)
    assert isinstance(binding.budget, InMemoryGoldTierReadBudget) and binding.budget.limit == 3


class FakeCollection:
    """The two find_one_and_update shapes the store uses, with Mongo's upsert semantics."""

    def __init__(self, *, fail: bool = False) -> None:
        self.docs: dict[str, dict[str, Any]] = {}
        self.fail = fail

    def find_one_and_update(
        self, query: dict[str, Any], update: dict[str, Any], upsert: bool = False, **_: Any
    ) -> dict[str, Any] | None:
        if self.fail:
            raise PyMongoError("unavailable")
        doc = self.docs.get(query["_id"])
        if doc is not None and doc["count"] < query["count"]["$lt"]:
            doc["count"] += update["$inc"]["count"]
            return doc
        if doc is None and upsert:
            self.docs[query["_id"]] = {"_id": query["_id"], "count": 1}
            return self.docs[query["_id"]]
        if doc is not None and upsert:
            raise DuplicateKeyError("E11000")
        return None

    def find_one(self, query: dict[str, Any]) -> dict[str, Any] | None:
        if self.fail:
            raise PyMongoError("unavailable")
        return self.docs.get(query["_id"])


def _mongo_budget(limit: int, collection: FakeCollection) -> MongoGoldTierReadBudget:
    class Client(dict):  # type: ignore[type-arg]
        def __getitem__(self, _name: str) -> Any:
            return {"budget": collection}

    return MongoGoldTierReadBudget(Client(), database="d", collection="budget", limit=limit)


def test_mongo_budget_claims_atomically_up_to_the_limit() -> None:
    collection = FakeCollection()
    budget = _mongo_budget(2, collection)
    assert [budget.claim(NOW) for _ in range(3)] == [True, True, False]
    assert budget.used(NOW) == 2
    assert collection.docs["2026-11-16"]["count"] == 2


def test_mongo_budget_zero_never_touches_the_store_and_failures_fail_closed() -> None:
    assert _mongo_budget(0, FakeCollection(fail=True)).claim(NOW) is False
    with pytest.raises(PersistenceUnavailableError):
        _mongo_budget(5, FakeCollection(fail=True)).claim(NOW)


@pytest.mark.skipif(
    not os.environ.get("PHASE12_MONGO_URI"), reason="PHASE12_MONGO_URI is not configured"
)
def test_physical_mongo_budget_holds_across_clients_and_restart() -> None:
    uri = os.environ["PHASE12_MONGO_URI"]
    database = generate_ephemeral_mongo_database("p12")
    collection = "clm_goldtier_read_budget"
    with MongoClient[dict[str, Any]](uri) as first, MongoClient[dict[str, Any]](uri) as second:
        budgets = [
            MongoGoldTierReadBudget(client, database=database, collection=collection, limit=3)
            for client in (first, second)
        ]
        try:
            with ThreadPoolExecutor(max_workers=8) as executor:
                claims = list(executor.map(lambda number: budgets[number % 2].claim(NOW), range(8)))
            assert claims.count(True) == 3
            with MongoClient[dict[str, Any]](uri) as restarted:
                budget = MongoGoldTierReadBudget(
                    restarted, database=database, collection=collection, limit=3
                )
                assert budget.used(NOW) == 3
                assert not budget.claim(NOW)
                next_day = NOW + timedelta(hours=1)
                assert budget.claim(next_day)
                assert budget.used(next_day) == 1
        finally:
            cleanup_ephemeral_mongo_database(first, database)


def _official_system(limit: int, responses: list[object]) -> tuple[Any, FakeXpiTransport]:
    transport = FakeXpiTransport(responses)
    zero, _, _ = _sandbox_zero_touch_system(
        transport, reviewed_test_enrichment=False, acra_connector=OfficialSourceAcra()
    )
    zero._cases._target_identity_policy = STAGING_SANDBOX_IDENTITY_POLICY  # noqa: SLF001
    zero._cases._goldtier._read_budget = InMemoryGoldTierReadBudget(limit)  # noqa: SLF001
    return zero, transport


def test_an_exhausted_budget_is_a_visible_recoverable_search_failure() -> None:
    zero, transport = _official_system(0, [ok([])])
    created = zero.create_case(UEN, "SG", legal_name=NAME)
    assert transport.calls == []
    result = retained_search(zero, created.case_id)
    assert result.status == "FAILED"
    assert zero._cases.target_read_budget_usage(datetime.now(UTC)) == (0, 0)  # noqa: SLF001


def test_a_budgeted_search_runs_and_reports_its_usage() -> None:
    zero, transport = _official_system(5, [ok([])])
    created = zero.create_case(UEN, "SG", legal_name=NAME)
    assert len(transport.calls) == 1
    assert retained_search(zero, created.case_id).status == "COMPLETED"
    assert zero._cases.target_read_budget_usage(datetime.now(UTC)) == (5, 1)  # noqa: SLF001


def test_unlimited_budget_reports_no_counts() -> None:
    assert UnlimitedGoldTierReadBudget().claim(NOW) is True
    zero, _ = _official_system(1, [ok([])])
    zero._cases._goldtier._read_budget = UnlimitedGoldTierReadBudget()  # noqa: SLF001
    assert zero._cases.target_read_budget_usage(NOW) == (None, None)  # noqa: SLF001
