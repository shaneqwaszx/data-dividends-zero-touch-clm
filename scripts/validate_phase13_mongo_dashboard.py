"""Validate a disposable Phase 13 Mongo dashboard portfolio."""

from __future__ import annotations

import secrets
import socket
import sys
import time
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from threading import Thread
from typing import Any
from unittest.mock import patch
from uuid import UUID

import httpx
import uvicorn

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "apps" / "backend"
for import_root in (ROOT, BACKEND_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from app import composition
from app.config import Settings
from app.connectors.local_pdf_idp import LocalPdfTextIdpProvider
from app.connectors.mock_acra import MockAcraConnector
from app.connectors.mock_goldtier import MockGoldTierConnector
from app.connectors.registry_ownership import RegistryAcquisitionOwnershipProvider
from app.domain.access import SYNTHETIC_USER_PROFILES
from app.main import create_app
from app.mongo import create_mongo_client
from app.services.authentication import (
    AuthenticationService,
    generate_scrypt_password_hash,
)

from scripts.mongo_test_safety import (
    cleanup_ephemeral_mongo_database,
    require_ephemeral_mongo_database,
)
from scripts.seed_phase13_demo import SEED_PRIORITIES, SEED_UENS, HttpSeedApi, seed_demo

_VALIDATION_SETTINGS: Settings | None = None


def _free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


@contextmanager
def _running_server(application: Any) -> Iterator[str]:
    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(application, host="127.0.0.1", port=port, log_level="critical")
    )
    thread = Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 15
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.05)
    if not server.started:
        raise RuntimeError("local validation application did not start")
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=15)
        if thread.is_alive():
            raise RuntimeError("local validation application did not stop")


def _login(base_url: str, user_id: str, credential: str) -> tuple[httpx.Client, str]:
    client = httpx.Client(base_url=base_url, timeout=20)
    response = client.post(
        "/api/auth/login", json={"user_id": user_id, "password": credential}
    )
    if response.status_code != 200:
        client.close()
        raise RuntimeError("runtime authentication failed")
    csrf = response.json().get("csrf_token")
    if not isinstance(csrf, str) or not csrf:
        client.close()
        raise RuntimeError("runtime authentication response was invalid")
    return client, csrf


def _deterministic(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for team_id in ("TEAM_A", "TEAM_B"):
        for uen, priority in zip(SEED_UENS, SEED_PRIORITIES, strict=True):
            match = next(
                (
                    item
                    for item in items
                    if item.get("team_id") == team_id
                    and item.get("requested_uen") == uen
                    and item.get("priority") == priority
                    and item.get("status") == "COMPLETED"
                    and item.get("final_outcome") == "MOCK_GOLDTIER_SUBMITTED"
                ),
                None,
            )
            if match is not None:
                selected.append(match)
    return selected


@contextmanager
def _counting_connectors() -> Iterator[dict[str, int]]:
    counters = {name: 0 for name in ("registry", "idp", "ownership", "goldtier")}

    class CountingAcra(MockAcraConnector):
        def fetch_company(self, uen: str) -> object:
            counters["registry"] += 1
            return super().fetch_company(uen)

        def fetch_officers(self, uen: str) -> object:
            counters["registry"] += 1
            return super().fetch_officers(uen)

        def fetch_ownership_parties(self, uen: str) -> object:
            counters["registry"] += 1
            return super().fetch_ownership_parties(uen)

        def fetch_relationships(self, uen: str) -> object:
            counters["registry"] += 1
            return super().fetch_relationships(uen)

    class CountingIdp(LocalPdfTextIdpProvider):
        def process(self, document: object) -> object:
            counters["idp"] += 1
            return super().process(document)  # type: ignore[arg-type]

    class CountingOwnership(RegistryAcquisitionOwnershipProvider):
        def load(self, request: object) -> object:
            counters["ownership"] += 1
            return super().load(request)  # type: ignore[arg-type]

    class CountingGoldTier(MockGoldTierConnector):
        def search_party(self, request: object, metadata: object) -> object:
            counters["goldtier"] += 1
            return super().search_party(request, metadata)  # type: ignore[arg-type]

        def create_shell_customer(self, request: object, metadata: object) -> object:
            counters["goldtier"] += 1
            return super().create_shell_customer(request, metadata)  # type: ignore[arg-type]

        def create_policy(self, request: object, metadata: object) -> object:
            counters["goldtier"] += 1
            return super().create_policy(request, metadata)  # type: ignore[arg-type]

        def amend_party(
            self, party_id: str, request: object, metadata: object
        ) -> object:
            counters["goldtier"] += 1
            return super().amend_party(party_id, request, metadata)  # type: ignore[arg-type]

    with (
        patch.object(composition, "MockAcraConnector", CountingAcra),
        patch.object(composition, "LocalPdfTextIdpProvider", CountingIdp),
        patch.object(
            composition,
            "RegistryAcquisitionOwnershipProvider",
            CountingOwnership,
        ),
        patch.object(composition, "MockGoldTierConnector", CountingGoldTier),
    ):
        yield counters


def _authentication(credential: str) -> AuthenticationService:
    encoded = generate_scrypt_password_hash(credential)
    return AuthenticationService(
        {profile.user_id: encoded for profile in SYNTHETIC_USER_PROFILES}
    )


def _portfolio_evidence(base_url: str, credential: str) -> dict[str, Any]:
    evidence: dict[str, Any] = {}
    clients: list[httpx.Client] = []
    try:
        for user_id in ("maya-lim", "ethan-tan", "sophia-ng", "ryan-lee", "olivia-koh"):
            client, csrf = _login(base_url, user_id, credential)
            clients.append(client)
            items = _deterministic(client.get("/api/clm/zero-touch/cases").json())
            evidence[user_id] = len(items)
            if user_id in {"maya-lim", "sophia-ng"}:
                director, _ = _login(base_url, "olivia-koh", credential)
                clients.append(director)
                director_items = _deterministic(
                    director.get("/api/clm/zero-touch/cases").json()
                )
                inaccessible_team = "TEAM_B" if user_id == "maya-lim" else "TEAM_A"
                cross_id = next(
                    item["case_id"]
                    for item in director_items
                    if item["team_id"] == inaccessible_team
                )
                absent_id = "00000000-0000-4000-8000-000000000000"
                cross = client.get(f"/api/clm/zero-touch/cases/{cross_id}")
                absent = client.get(f"/api/clm/zero-touch/cases/{absent_id}")
                cross_mutation = client.patch(
                    f"/api/clm/zero-touch/cases/{cross_id}/priority",
                    json={"priority": 10},
                    headers={"X-CSRF-Token": csrf},
                )
                absent_mutation = client.patch(
                    f"/api/clm/zero-touch/cases/{absent_id}/priority",
                    json={"priority": 10},
                    headers={"X-CSRF-Token": csrf},
                )
                if not (
                    cross.status_code == absent.status_code == 404
                    and cross.json() == absent.json()
                    and cross_mutation.status_code == absent_mutation.status_code == 404
                    and cross_mutation.json() == absent_mutation.json()
                ):
                    raise RuntimeError("direct-ID non-enumeration failed")
                evidence[f"direct_id_{user_id}"] = "PASS"
        return evidence
    finally:
        for client in clients:
            client.close()


def main() -> int:
    global _VALIDATION_SETTINGS

    settings = Settings()
    if settings.mongo_uri is None or settings.clm_persistence_mode != "mongo":
        raise RuntimeError("Mongo persistence is not configured")
    require_ephemeral_mongo_database(settings.mongo_database)
    _VALIDATION_SETTINGS = settings
    settings = settings.model_copy(update={"demo_controls_enabled": True})
    credential = secrets.token_urlsafe(32)

    with _counting_connectors() as counters:
        first_app = create_app(
            settings, authentication_service=_authentication(credential)
        )
        with _running_server(first_app) as base_url:
            seeder = HttpSeedApi(base_url)
            first = seed_demo(seeder, credential)
            second = seed_demo(seeder, credential)
            director, _ = _login(base_url, "olivia-koh", credential)
            try:
                profile = director.get("/api/system/execution-profile")
                if (
                    profile.status_code != 200
                    or profile.json().get("persistence") != "Mongo-backed durable POC"
                ):
                    raise RuntimeError("running persistence profile was not Mongo")
                dashboard_before = director.get("/api/clm/zero-touch/dashboard").json()
            finally:
                director.close()
            portfolio_before = _portfolio_evidence(base_url, credential)
            provider_counts_before_reads = counters.copy()
            _portfolio_evidence(base_url, credential)
            if counters != provider_counts_before_reads:
                raise RuntimeError("historical reads invoked providers")

            maya, csrf = _login(base_url, "maya-lim", credential)
            try:
                existing_extra = next(
                    (
                        item
                        for item in maya.get("/api/clm/zero-touch/cases").json()
                        if item.get("requested_uen") == "202400005E"
                        and item.get("priority") == 10
                    ),
                    None,
                )
                if existing_extra is not None:
                    extra_case_id = existing_extra["case_id"]
                else:
                    created = maya.post(
                        "/api/clm/zero-touch/cases",
                        json={"uen": "202400005E", "priority": 10},
                        headers={"X-CSRF-Token": csrf},
                    )
                    if (
                        created.status_code != 201
                        or created.json()["case"].get("priority") != 10
                    ):
                        raise RuntimeError("atomic priority creation failed")
                    extra_case_id = created.json()["case"]["case_id"]
            finally:
                maya.close()

        mongo = create_mongo_client(settings)
        try:
            collection = mongo[settings.mongo_database][settings.mongo_case_collection]
            projected = list(
                collection.find(
                    {
                        "onboarding.team_id": {"$in": ["TEAM_A", "TEAM_B"]},
                        "onboarding.requested_uen": {"$in": list(SEED_UENS)},
                    },
                    {
                        "schema_version": 1,
                        "onboarding.team_id": 1,
                        "onboarding.priority": 1,
                        "onboarding.requested_uen": 1,
                        "automation.status": 1,
                        "automation.metrics.final_outcome": 1,
                    },
                )
            )
            selected: list[dict[str, Any]] = []
            for team in ("TEAM_A", "TEAM_B"):
                for uen, priority in zip(SEED_UENS, SEED_PRIORITIES, strict=True):
                    match = next(
                        (
                            item
                            for item in projected
                            if item["onboarding"]["team_id"] == team
                            and item["onboarding"]["requested_uen"] == uen
                            and item["onboarding"].get("priority") == priority
                            and item.get("automation", {}).get("status") == "COMPLETED"
                            and item.get("automation", {})
                            .get("metrics", {})
                            .get("final_outcome")
                            == "MOCK_GOLDTIER_SUBMITTED"
                        ),
                        None,
                    )
                    if match is None:
                        raise RuntimeError(
                            "deterministic physical portfolio count failed"
                        )
                    selected.append(match)
            by_team = Counter(item["onboarding"]["team_id"] for item in selected)
            physical_priorities = {
                team: sorted(
                    (
                        item["onboarding"].get("priority")
                        for item in selected
                        if item["onboarding"]["team_id"] == team
                    ),
                    key=lambda value: -1 if value is None else value,
                    reverse=True,
                )
                for team in ("TEAM_A", "TEAM_B")
            }
            if any(item.get("schema_version") != 2 for item in selected):
                raise RuntimeError("physical schema version failed")
            if any(
                item.get("automation", {}).get("status") != "COMPLETED"
                for item in selected
            ):
                raise RuntimeError("physical successful state failed")
            if any(
                item.get("automation", {}).get("metrics", {}).get("final_outcome")
                != "MOCK_GOLDTIER_SUBMITTED"
                for item in selected
            ):
                raise RuntimeError("physical target outcome failed")
            extra = collection.find_one(
                {"_id": extra_case_id},
                {"onboarding.team_id": 1, "onboarding.priority": 1},
            )
            if not extra or extra["onboarding"] != {
                "team_id": "TEAM_A",
                "priority": 10,
            }:
                raise RuntimeError("initial physical priority failed")
            index_names = {item["name"] for item in collection.list_indexes()}
            expected_indexes = {
                "_id_",
                "case_id_unique",
                "automation_status_updated_at",
                "target_submission_lookup",
                "document_id_lookup",
            }
            if not expected_indexes.issubset(index_names):
                raise RuntimeError("expected Mongo indexes are unavailable")
        finally:
            mongo.close()

        before_restart_reads = counters.copy()
        second_app = create_app(
            settings, authentication_service=_authentication(credential)
        )
        with _running_server(second_app) as base_url:
            portfolio_after = _portfolio_evidence(base_url, credential)
            director, _ = _login(base_url, "olivia-koh", credential)
            try:
                dashboard_after = director.get("/api/clm/zero-touch/dashboard").json()
                persisted_extra = director.get(
                    f"/api/clm/zero-touch/cases/{UUID(extra_case_id)}"
                )
                if persisted_extra.status_code != 200:
                    raise RuntimeError("restart case detail failed")
            finally:
                director.close()
        if counters != before_restart_reads:
            raise RuntimeError("restart historical reads invoked providers")

    print("RUNNING_APPLICATION_PERSISTENCE=MONGO")
    print(f"FIRST_SEED=created:{first.created},reused:{first.reused}")
    print(f"SECOND_SEED=created:{second.created},reused:{second.reused}")
    print(f"TEAM_A_PHYSICAL_COUNT={by_team['TEAM_A']}")
    print(f"TEAM_B_PHYSICAL_COUNT={by_team['TEAM_B']}")
    print(f"TEAM_A_PRIORITIES={physical_priorities['TEAM_A']}")
    print(f"TEAM_B_PRIORITIES={physical_priorities['TEAM_B']}")
    print(f"HISTORICAL_COLLISIONS_EXCLUDED={len(projected) - len(selected)}")
    print("SUCCESSFUL_STATE_PERSISTENCE=PASS")
    print(f"RBAC_BEFORE_RESTART={portfolio_before}")
    print(f"RBAC_AFTER_RESTART={portfolio_after}")
    print(f"DASHBOARD_BEFORE_TOTAL={dashboard_before['totals']['total_cases']}")
    print(f"DASHBOARD_AFTER_TOTAL={dashboard_after['totals']['total_cases']}")
    print("ATOMIC_PRIORITY_PERSISTENCE=PASS")
    print("PROVIDER_CALLS_DURING_HISTORICAL_READS=0")
    print("RESTART_DURABILITY=PASS")
    return 0


def _cleanup_validation_database() -> None:
    if _VALIDATION_SETTINGS is None:
        return
    client = create_mongo_client(_VALIDATION_SETTINGS)
    try:
        cleanup_ephemeral_mongo_database(
            client,
            _VALIDATION_SETTINGS.mongo_database,
        )
    finally:
        client.close()


if __name__ == "__main__":
    exit_code = 0
    try:
        exit_code = main()
    except RuntimeError as error:
        print(f"Phase 13 Mongo dashboard validation failed: {error}", file=sys.stderr)
        exit_code = 1
    except Exception as error:  # noqa: BLE001 - redact every unexpected remote error
        print(
            f"Phase 13 Mongo dashboard validation failed: {error.__class__.__name__}",
            file=sys.stderr,
        )
        exit_code = 1
    finally:
        try:
            _cleanup_validation_database()
        except Exception as error:  # noqa: BLE001 - redact every cleanup error
            print(
                f"Phase 13 Mongo dashboard cleanup failed: {error.__class__.__name__}",
                file=sys.stderr,
            )
            exit_code = 1
    raise SystemExit(exit_code)
