"""F-9: the ADR-017 durability probe needs only the application's own readWrite privileges.

Unit tests with fake driver objects: every outcome, and that ``serverStatus`` (a cluster-wide
privilege the staging user does not hold) is never called.
"""

from typing import Any

import pytest
from pymongo.errors import OperationFailure, ServerSelectionTimeoutError

from app.persistence.mongo_case_store import MongoCaseStore

STANDALONE = {"isWritablePrimary": True}
WIRED_TIGER = [{"storageStats": {"wiredTiger": {"metadata": {"formatVersion": 1}}}}]


class FakeAdmin:
    def __init__(self, hello: dict[str, Any] | Exception, calls: list[str]) -> None:
        self._hello = hello
        self._calls = calls

    def command(self, name: str, **_: Any) -> dict[str, Any]:
        self._calls.append(name)
        if name == "serverStatus":
            raise OperationFailure("not authorized", code=13)
        if isinstance(self._hello, Exception):
            raise self._hello
        return self._hello


class FakeClient:
    def __init__(self, hello: Any, version: str | Exception, calls: list[str]) -> None:
        self.admin = FakeAdmin(hello, calls)
        self._version = version

    def server_info(self) -> dict[str, Any]:
        if isinstance(self._version, Exception):
            raise self._version
        return {"version": self._version}


class FakeCollection:
    def __init__(self, result: list[dict[str, Any]] | Exception, pipelines: list[Any]) -> None:
        self._result = result
        self._pipelines = pipelines

    def aggregate(self, pipeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self._pipelines.append(pipeline)
        if isinstance(self._result, Exception):
            raise self._result
        return list(self._result)


def probe(
    *,
    hello: Any = STANDALONE,
    version: str | Exception = "7.0.40",
    storage: list[dict[str, Any]] | Exception = WIRED_TIGER,
    clearing_incomplete: bool = False,
) -> tuple[tuple[bool, str | None], list[str], list[Any]]:
    calls: list[str] = []
    pipelines: list[Any] = []
    store = MongoCaseStore.__new__(MongoCaseStore)
    store._client = FakeClient(hello, version, calls)  # type: ignore[attr-defined]
    store._collection = FakeCollection(storage, pipelines)  # type: ignore[attr-defined]
    if clearing_incomplete:
        store._claim_clearing_incomplete = True  # type: ignore[attr-defined]
    return store.probe_durability(), calls, pipelines


def test_wired_tiger_standalone_on_major_7_is_durable_with_least_privilege() -> None:
    result, calls, pipelines = probe()
    assert result == (True, None)
    assert "serverStatus" not in calls
    assert pipelines == [[{"$collStats": {"storageStats": {}}}]]


def test_replica_set_primary_is_durable() -> None:
    result, _, _ = probe(hello={"setName": "rs0", "isWritablePrimary": True})
    assert result == (True, None)


@pytest.mark.parametrize(
    ("kwargs", "reason"),
    [
        # Permission and driver failures fail closed.
        ({"storage": OperationFailure("not authorized on clm to execute command", code=13)},
         "PROBE_FAILED"),
        ({"hello": ServerSelectionTimeoutError("down")}, "PROBE_FAILED"),
        ({"version": OperationFailure("buildInfo refused", code=13)}, "PROBE_FAILED"),
        # Missing or unexpected storage engine information.
        ({"storage": []}, "JOURNALING_UNVERIFIED"),
        ({"storage": [{}]}, "JOURNALING_UNVERIFIED"),
        ({"storage": [{"storageStats": {}}]}, "JOURNALING_UNVERIFIED"),
        ({"storage": [{"storageStats": None}]}, "JOURNALING_UNVERIFIED"),
        ({"storage": [{"storageStats": {"wiredTiger": "yes"}}]}, "JOURNALING_UNVERIFIED"),
        ({"storage": [{"storageStats": {"inMemory": {}}}]}, "JOURNALING_UNVERIFIED"),
        ({"storage": WIRED_TIGER + WIRED_TIGER}, "JOURNALING_UNVERIFIED"),
        # Unsupported topology.
        ({"hello": {"msg": "isdbgrid", "isWritablePrimary": True}}, "SHARDED_UNSUPPORTED"),
        ({"hello": {"setName": "rs0", "isWritablePrimary": False}}, "NOT_PRIMARY"),
        ({"hello": {"isWritablePrimary": False}}, "TOPOLOGY_UNIDENTIFIED"),
        ({"hello": {}}, "TOPOLOGY_UNIDENTIFIED"),
        # Unverified server version.
        ({"version": "6.0.20"}, "SERVER_VERSION_UNVERIFIED"),
        ({"version": "8.0.1"}, "SERVER_VERSION_UNVERIFIED"),
        ({"version": ""}, "SERVER_VERSION_UNVERIFIED"),
    ],
)
def test_every_unverified_condition_refuses(kwargs: dict[str, Any], reason: str) -> None:
    result, calls, _ = probe(**kwargs)
    assert result == (False, reason)
    assert "serverStatus" not in calls


def test_incomplete_startup_claim_clearing_still_refuses_first() -> None:
    result, calls, pipelines = probe(clearing_incomplete=True)
    assert result == (False, "STARTUP_CLAIM_CLEARING_INCOMPLETE")
    assert calls == [] and pipelines == []
