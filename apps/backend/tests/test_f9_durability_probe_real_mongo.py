"""F-9 on physical MongoDB: the probe passes as a staging-equivalent least-privilege user.

Staging's backend user holds exactly one role, ``readWrite`` on its database, and cannot run
``serverStatus`` (AWS lane read-only check, 2026-11-17). Each test creates such a user on a newly
generated, allowlisted disposable database, never ``clm_poc``, and removes it afterwards.

On a server started with authentication, the denial of ``serverStatus`` is also asserted. On a
server without authentication (where every user can do everything) that one assertion is
reported as skipped, and the probe itself still runs.
"""

import contextlib
import secrets
from collections.abc import Iterator
from typing import Any

import pytest
from pymongo import MongoClient
from pymongo.errors import OperationFailure
from pymongo.uri_parser import parse_uri
from scripts.mongo_test_safety import (
    cleanup_ephemeral_mongo_database,
    generate_ephemeral_mongo_database,
    require_ephemeral_mongo_database,
)
from test_synthetic_company_pack_real_mongo import MONGO_URI, pytestmark  # noqa: F401

from app.persistence.mongo_case_store import MongoCaseStore

CASES = "clm_case_snapshots"
_CREDENTIAL_OPTIONS = {"authsource", "authmechanism", "authmechanismproperties"}


def _client_as(user: str, password: str, database: str) -> MongoClient[dict[str, Any]]:
    """The same server and transport options as ``PHASE12_MONGO_URI``, authenticated as ``user``."""

    parsed = parse_uri(MONGO_URI)
    options = {
        key: value
        for key, value in parsed["options"].items()
        if key.lower() not in _CREDENTIAL_OPTIONS
    }
    return MongoClient(
        [f"{host}:{port}" for host, port in parsed["nodelist"]],
        username=user,
        password=password,
        authSource=database,
        serverSelectionTimeoutMS=5000,
        **options,
    )


@pytest.fixture
def least_privilege() -> Iterator[tuple[MongoClient[dict[str, Any]], str]]:
    name = require_ephemeral_mongo_database(generate_ephemeral_mongo_database("p12"))
    admin: MongoClient[dict[str, Any]] = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    user, password = f"f9_{secrets.token_hex(6)}", secrets.token_urlsafe(24)
    client = None
    try:
        admin[name].command(
            "createUser", user, pwd=password, roles=[{"role": "readWrite", "db": name}]
        )
        client = _client_as(user, password, name)
        yield client, name
    finally:
        if client is not None:
            client.close()
        with contextlib.suppress(OperationFailure):
            admin[name].command("dropUser", user)
        cleanup_ephemeral_mongo_database(admin, name)
        assert name not in admin.list_database_names()
        admin.close()


def test_physical_probe_passes_with_only_the_readwrite_role(least_privilege) -> None:
    client, name = least_privilege
    store = MongoCaseStore(client, database=name, collection=CASES)
    store.initialize()
    assert store.probe_durability() == (True, None)


def test_physical_least_privilege_user_cannot_run_server_status(least_privilege) -> None:
    client, _ = least_privilege
    try:
        client.admin.command("serverStatus")
    except OperationFailure as error:
        assert error.code == 13  # Unauthorized: the probe must not depend on it
        return
    pytest.skip("server runs without authentication; the denial cannot be shown here")


def test_physical_probe_refuses_when_storage_statistics_are_denied(least_privilege) -> None:
    client, name = least_privilege
    # A collection the user has no privilege on: the probe must fail closed, never pass.
    other = require_ephemeral_mongo_database(generate_ephemeral_mongo_database("p12"))
    store = MongoCaseStore(client, database=other, collection=CASES)
    try:
        client.admin.command("serverStatus")
        auth_enforced = False
    except OperationFailure:
        auth_enforced = True
    if not auth_enforced:
        pytest.skip("server runs without authentication; a denial cannot be produced here")
    assert store.probe_durability() == (False, "PROBE_FAILED")
