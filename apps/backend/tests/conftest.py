"""Provision runtime-only auth credentials and authenticated legacy API clients."""

import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY_ROOT))

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
