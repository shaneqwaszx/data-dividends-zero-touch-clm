"""Provision runtime-only auth credentials and authenticated legacy API clients."""

import sys
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY_ROOT))

from phase13_test_settings import enforce_ordinary_test_environment  # noqa: E402

enforce_ordinary_test_environment()

import fastapi.testclient  # noqa: E402
import httpx  # noqa: E402
from phase13_test_clients import (  # noqa: E402
    AuthenticatedAsyncClient,
    AuthenticatedTestClient,
)
from phase13_test_credentials import provision_test_hash_environment  # noqa: E402

provision_test_hash_environment()
httpx.AsyncClient = AuthenticatedAsyncClient
fastapi.testclient.TestClient = AuthenticatedTestClient


@pytest.fixture(autouse=True)
def _isolate_ordinary_test_environment() -> None:
    enforce_ordinary_test_environment()


@pytest.fixture
def blocking_ubo_review(monkeypatch: pytest.MonkeyPatch) -> None:
    """D-121: a test of the blocking review, the rollback of the advisory default."""

    monkeypatch.setenv("ACRA_MARKETPLACE_UBO_REVIEW_MODE", "blocking")
