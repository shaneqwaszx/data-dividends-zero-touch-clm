"""Opt-in physical Mongo restart proof for Phase 14.5 global administration."""

from __future__ import annotations

import os
import secrets
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier
from typing import Any

import pytest
from phase13_test_clients import RawTestClient
from phase13_test_credentials import TEST_PASSWORD
from phase24c_policy_workflow import approve_http_policy
from pymongo import MongoClient
from scripts.mongo_test_safety import (
    cleanup_ephemeral_mongo_database,
    generate_ephemeral_mongo_database,
)

from app.config import Settings
from app.domain.access import Role
from app.main import create_app
from app.persistence.mongo_admin_store import MongoAdminStore, MongoProfileRepository
from app.services.admin_repository import AdministrationAuthorityInvariantError

MONGO_URI = os.environ.get("PHASE12_MONGO_URI")
pytestmark = pytest.mark.skipif(not MONGO_URI, reason="PHASE12_MONGO_URI is not configured")


def _login(client: RawTestClient, user_id: str, password: str = TEST_PASSWORD) -> str:
    response = client.post("/api/auth/login", json={"user_id": user_id, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["csrf_token"]


def test_real_mongo_restart_preserves_admin_policy_case_snapshot_and_gamma_scope() -> None:
    assert MONGO_URI is not None
    database = generate_ephemeral_mongo_database("p145")
    settings = Settings(
        _env_file=None,
        app_env="test",
        clm_persistence_mode="mongo",
        mongo_uri=MONGO_URI,
        mongo_database=database,
    )
    cleanup: MongoClient[dict[str, Any]] = MongoClient(MONGO_URI)
    gamma_password = secrets.token_urlsafe(24)
    try:
        with RawTestClient(create_app(settings)) as first:
            hr_csrf = _login(first, "hr-admin")
            gamma = first.post(
                "/api/admin/teams",
                headers={"X-CSRF-Token": hr_csrf},
                json={"display_name": "Gamma", "client_scope_label": "Gamma"},
            )
            assert gamma.status_code == 201
            gamma_id = gamma.json()["team_id"]
            duplicate_scope = first.post(
                "/api/admin/teams",
                headers={"X-CSRF-Token": hr_csrf},
                json={"display_name": "Delta", "client_scope_label": " gamma "},
            )
            assert duplicate_scope.status_code == 409
            profile = first.post(
                "/api/admin/profiles",
                headers={"X-CSRF-Token": hr_csrf},
                json={
                    "user_id": "gamma-rm",
                    "display_name": "Gamma RM",
                    "role": "RELATIONSHIP_MANAGER",
                    "team_id": gamma_id,
                    "password": gamma_password,
                },
            )
            assert profile.status_code == 201
            assert gamma_password not in profile.text

            director = RawTestClient(first.app)
            approve_http_policy(first.app, {
                "DOCUMENT_IDP_REVIEW_CONFIDENCE_THRESHOLD": {"type": "DECIMAL", "value": "0.90"}})
            director_csrf = _login(director, "olivia-koh")
            created = director.post(
                "/api/clm/zero-touch/cases",
                headers={"X-CSRF-Token": director_csrf},
                json={"uen": "202400001A", "team_id": gamma_id},
            )
            assert created.status_code == 201
            case_id = created.json()["case"]["case_id"]
            assert (
                created.json()["case"]["policy_snapshot"]["idp_review_confidence_threshold"]
                == "0.90"
            )

        with RawTestClient(create_app(settings)) as restarted:
            _login(restarted, "gamma-rm", gamma_password)
            assert restarted.get("/api/clm/zero-touch/cases").status_code == 200
            director = RawTestClient(restarted.app)
            _login(director, "olivia-koh")
            listed = director.get(f"/api/clm/zero-touch/cases?team_filter={gamma_id}")
            assert [item["case_id"] for item in listed.json()] == [case_id]
            assert (
                director.get(f"/api/clm/zero-touch/cases/{case_id}").json()["case"][
                    "policy_snapshot"
                ]["idp_review_confidence_threshold"]
                == "0.90"
            )

            hr = RawTestClient(restarted.app)
            hr_csrf = _login(hr, "hr-admin")
            assert any(item["team_id"] == gamma_id for item in hr.get("/api/admin/teams").json())
            profiles = hr.get("/api/admin/profiles")
            assert any(item["user_id"] == "gamma-rm" for item in profiles.json())
            assert "credential_hash" not in profiles.text
            assert gamma_password not in profiles.text

            second_hr_password = secrets.token_urlsafe(24)
            second_hr = hr.post(
                "/api/admin/profiles",
                headers={"X-CSRF-Token": hr_csrf},
                json={
                    "user_id": "hr-second",
                    "display_name": "Second HR",
                    "role": "HR",
                    "team_id": None,
                    "password": second_hr_password,
                },
            )
            assert second_hr.status_code == 201

            store = MongoAdminStore(
                cleanup,
                database=database,
                teams_collection=settings.mongo_admin_teams_collection,
                profiles_collection=settings.mongo_admin_profiles_collection,
                policies_collection=settings.mongo_admin_policies_collection,
            )
            repository = MongoProfileRepository(store)
            start = Barrier(3)

            def demote(actor_id: str, target_id: str) -> str:
                target = repository.get(target_id)
                assert target is not None
                start.wait()
                try:
                    repository.mutate_authority(
                        actor_user_id=actor_id,
                        user_id=target_id,
                        expected_version=target.version,
                        display_name=target.display_name,
                        role=Role.DIRECTOR,
                        team_id=None,
                        updated_at=datetime.now(UTC),
                    )
                except AdministrationAuthorityInvariantError:
                    return "rejected"
                return "succeeded"

            with ThreadPoolExecutor(max_workers=2) as pool:
                first_demotion = pool.submit(demote, "hr-admin", "hr-second")
                second_demotion = pool.submit(demote, "hr-second", "hr-admin")
                start.wait()
                outcomes = [first_demotion.result(), second_demotion.result()]
            assert sorted(outcomes) == ["rejected", "succeeded"]
            assert sum(item.role == Role.HR for item in repository.list()) == 1

        raw_case = cleanup[database][settings.mongo_case_collection].find_one({"_id": case_id})
        assert raw_case is not None and raw_case["schema_version"] == 14
        assert raw_case["onboarding"]["policy_snapshot"]["intelligence"] is not None
        assert "credential_hash" not in str(raw_case)
        assert "credential_hash" not in str(
            list(cleanup[database][settings.mongo_admin_teams_collection].find({}))
        )
        assert "credential_hash" not in str(
            list(cleanup[database][settings.mongo_admin_policies_collection].find({}))
        )
        team_indexes = cleanup[database][settings.mongo_admin_teams_collection].index_information()
        assert team_indexes["normalized_display_name_unique"]["unique"] is True
        assert team_indexes["normalized_client_scope_label_unique"]["unique"] is True
    finally:
        try:
            cleanup_ephemeral_mongo_database(cleanup, database)
        finally:
            cleanup.close()
