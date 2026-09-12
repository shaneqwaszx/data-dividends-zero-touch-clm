from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier

import pytest
from phase13_test_clients import RawTestClient
from phase13_test_credentials import TEST_PASSWORD
from phase13_test_settings import ordinary_test_settings
from pydantic import SecretStr, ValidationError
from pymongo.errors import DuplicateKeyError

from app.domain.access import AuthenticatedActor, Role, TeamId, UserProfile
from app.domain.administration import TeamRecord, UserAccountRecord, normalize_display_name
from app.main import create_app
from app.persistence.errors import PersistenceDataInvalidError
from app.persistence.mongo_admin_store import MongoTeamRepository, _decode, _encode
from app.services.admin_repository import (
    AdministrationConflictError,
    InMemoryPolicyRepository,
    InMemoryProfileRepository,
    InMemoryTeamRepository,
    bootstrap_administration,
)
from app.services.administration import AdministrationService, AdministrationValidationError
from app.services.authentication import generate_scrypt_password_hash
from app.services.policy_management import PolicyManagementService


def _repositories():
    teams = InMemoryTeamRepository()
    profiles = InMemoryProfileRepository()
    policies = InMemoryPolicyRepository()
    encoded = SecretStr(generate_scrypt_password_hash("runtime-only test password"))
    hashes = {
        user_id: encoded
        for user_id in (
            "maya-lim",
            "ethan-tan",
            "sophia-ng",
            "ryan-lee",
            "olivia-koh",
            "hr-admin",
        )
    }
    bootstrap_administration(teams, profiles, hashes)
    PolicyManagementService(policies)
    return teams, profiles, policies


def _hr() -> AuthenticatedActor:
    return AuthenticatedActor(
        profile=UserProfile(
            user_id="hr-admin",
            display_name="POC HR Administrator",
            role=Role.HR,
            team_id=None,
        )
    )


def test_seed_teams_and_profiles_preserve_ids_with_alpha_beta() -> None:
    teams, profiles, _ = _repositories()

    assert [(item.team_id, item.display_name) for item in teams.list()] == [
        (TeamId.TEAM_A, "Alpha"),
        (TeamId.TEAM_B, "Beta"),
    ]
    assert [item.normalized_client_scope_label for item in teams.list()] == ["alpha", "beta"]
    assert [item.user_id for item in profiles.list()] == [
        "ethan-tan",
        "hr-admin",
        "maya-lim",
        "olivia-koh",
        "ryan-lee",
        "sophia-ng",
    ]


def test_dynamic_team_id_and_server_generation() -> None:
    teams, profiles, _ = _repositories()
    service = AdministrationService(teams, profiles)
    created = service.create_team(
        _hr(), display_name="Gamma", client_scope_label=" Outdoors ", description=None
    )

    assert str(created.team_id).startswith("TEAM_")
    assert len(str(created.team_id)) == 29
    assert created.display_name == "Gamma"
    assert created.client_scope_label == "Outdoors"
    assert created.normalized_client_scope_label == "outdoors"
    assert teams.get(created.team_id) == created


def test_normalized_duplicate_team_name_fails() -> None:
    teams, profiles, _ = _repositories()
    service = AdministrationService(teams, profiles)
    service.create_team(
        _hr(), display_name="Gamma Team", client_scope_label="Gamma", description=None
    )
    with pytest.raises(AdministrationConflictError):
        service.create_team(
            _hr(), display_name="  GAMMA   team ", client_scope_label="Other", description=None
        )


@pytest.mark.parametrize(
    "duplicate_scope",
    [" gamma   coverage ", "GAMMA COVERAGE", "Ｇａｍｍａ Ｃｏｖｅｒａｇｅ"],
)
def test_normalized_duplicate_team_coverage_fails(duplicate_scope: str) -> None:
    teams, profiles, _ = _repositories()
    service = AdministrationService(teams, profiles)
    service.create_team(
        _hr(), display_name="Gamma", client_scope_label="Gamma Coverage", description=None
    )

    with pytest.raises(AdministrationConflictError):
        service.create_team(
            _hr(), display_name="Delta", client_scope_label=duplicate_scope, description=None
        )


def test_distinct_team_display_and_coverage_succeeds() -> None:
    teams, profiles, _ = _repositories()
    service = AdministrationService(teams, profiles)

    created = service.create_team(
        _hr(), display_name="Delta", client_scope_label="Regional Coverage", description=None
    )

    assert created.normalized_display_name == "delta"
    assert created.normalized_client_scope_label == "regional coverage"


def test_team_update_rejects_normalized_coverage_collision() -> None:
    teams, profiles, _ = _repositories()
    service = AdministrationService(teams, profiles)
    gamma = service.create_team(
        _hr(), display_name="Gamma", client_scope_label="Gamma Coverage", description=None
    )
    delta = service.create_team(
        _hr(), display_name="Delta", client_scope_label="Delta Coverage", description=None
    )

    with pytest.raises(AdministrationConflictError):
        service.update_team(
            _hr(),
            delta.team_id,
            expected_version=delta.version,
            client_scope_label=" GAMMA   COVERAGE ",
        )

    assert teams.get(gamma.team_id) == gamma
    assert teams.get(delta.team_id) == delta


def test_team_id_validation_rejects_noncanonical_values() -> None:
    for value in ("TEAM_C", "team_a", "TEAM_123", "TEAM_abcdefabcdefabcdefabcdef"):
        with pytest.raises((ValueError, ValidationError)):
            TeamRecord(
                team_id=value,
                display_name="Gamma",
                normalized_display_name=normalize_display_name("Gamma"),
                client_scope_label="Gamma",
                normalized_client_scope_label=normalize_display_name("Gamma"),
                version=1,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                created_by="hr-admin",
                updated_by="hr-admin",
                audit_events=(),
            )


def test_bootstrap_never_overwrites_existing_hash() -> None:
    teams, profiles, policies = _repositories()
    before = profiles.get("maya-lim")
    assert before is not None
    replacement = SecretStr(generate_scrypt_password_hash("different runtime test password"))
    bootstrap_administration(
        teams,
        profiles,
        {item.user_id: replacement for item in profiles.list()},
    )
    after = profiles.get("maya-lim")
    assert after is not None
    assert after.credential_hash.get_secret_value() == before.credential_hash.get_secret_value()
    assert policies.get() is not None


def test_profile_mongo_codec_round_trips_seeded_roles_and_new_profile() -> None:
    teams, profiles, _ = _repositories()
    created = AdministrationService(teams, profiles).create_profile(
        _hr(),
        user_id="gamma-rm",
        display_name="Gamma RM",
        role=Role.RELATIONSHIP_MANAGER,
        team_id=TeamId.TEAM_B,
        password="runtime-only Gamma password",
    )
    selected_ids = ("maya-lim", "ethan-tan", "olivia-koh", "hr-admin")
    selected = [profiles.get(user_id) for user_id in selected_ids]
    assert all(record is not None for record in selected)

    source_records = [record for record in selected if record is not None]
    source_records.append(created)
    assert [record.role for record in source_records] == [
        Role.CLIENT_ONBOARDER,
        Role.RELATIONSHIP_MANAGER,
        Role.DIRECTOR,
        Role.HR,
        Role.RELATIONSHIP_MANAGER,
    ]

    for source in source_records:
        raw = _encode(source, source.user_id)
        decoded = _decode(raw, UserAccountRecord)

        assert decoded.user_id == source.user_id
        assert decoded.role == source.role
        assert decoded.team_id == source.team_id
        assert decoded.security_version == source.security_version
        credential_matches = (
            decoded.credential_hash.get_secret_value() == source.credential_hash.get_secret_value()
        )
        assert credential_matches


def test_profile_mongo_codec_rejects_corrupt_unknown_and_mismatched_documents() -> None:
    _, profiles, _ = _repositories()
    source = profiles.get("maya-lim")
    assert source is not None
    raw = _encode(source, source.user_id)

    corrupt = dict(raw)
    corrupt["security_version"] = 0
    unknown = dict(raw)
    unknown["unexpected"] = "not permitted"
    mismatched = dict(raw)
    mismatched["_id"] = "other-user"

    for document in (corrupt, unknown, mismatched):
        with pytest.raises(PersistenceDataInvalidError):
            _decode(document, UserAccountRecord)


def _login(client: RawTestClient, user_id: str) -> str:
    response = client.post("/api/auth/login", json={"user_id": user_id, "password": TEST_PASSWORD})
    assert response.status_code == 200
    return response.json()["csrf_token"]


def test_hr_admin_api_creates_dynamic_team_and_safe_profile() -> None:
    client = RawTestClient(create_app(ordinary_test_settings()))
    csrf = _login(client, "hr-admin")
    teams = client.get("/api/admin/teams")
    profiles = client.get("/api/admin/profiles")

    assert teams.status_code == 200
    assert [(item["team_id"], item["display_name"]) for item in teams.json()] == [
        ("TEAM_A", "Alpha"),
        ("TEAM_B", "Beta"),
    ]
    assert profiles.status_code == 200
    assert len(profiles.json()) == 6
    assert "credential_hash" not in profiles.text

    created_team = client.post(
        "/api/admin/teams",
        headers={"X-CSRF-Token": csrf},
        json={
            "display_name": "Gamma",
            "client_scope_label": "Gamma",
            "description": "Synthetic third team",
        },
    )
    assert created_team.status_code == 201
    gamma_id = created_team.json()["team_id"]
    assert gamma_id.startswith("TEAM_") and len(gamma_id) == 29

    password = "runtime-only Gamma password"
    created_profile = client.post(
        "/api/admin/profiles",
        headers={"X-CSRF-Token": csrf},
        json={
            "user_id": "gamma-rm",
            "display_name": "Gamma RM",
            "role": "RELATIONSHIP_MANAGER",
            "team_id": gamma_id,
            "password": password,
        },
    )
    assert created_profile.status_code == 201
    assert password not in created_profile.text
    assert "credential" not in created_profile.text

    gamma_client = RawTestClient(client.app)
    login = gamma_client.post("/api/auth/login", json={"user_id": "gamma-rm", "password": password})
    assert login.status_code == 200
    assert login.json()["profile"]["team_id"] == gamma_id
    assert gamma_client.get("/api/clm/zero-touch/cases").json() == []

    director = RawTestClient(client.app)
    _login(director, "olivia-koh")
    options = director.get("/api/teams/options")
    assert options.status_code == 200
    assert any(item["team_id"] == gamma_id for item in options.json())
    assert director.get(f"/api/clm/zero-touch/cases?team_filter={gamma_id}").json() == []
    gamma_dashboard = director.get(f"/api/clm/zero-touch/dashboard?team_filter={gamma_id}")
    assert gamma_dashboard.status_code == 200
    assert gamma_dashboard.json()["totals"]["total_cases"] == 0


def test_team_api_rejects_browser_authored_normalized_coverage() -> None:
    client = RawTestClient(create_app(ordinary_test_settings()))
    csrf = _login(client, "hr-admin")

    response = client.post(
        "/api/admin/teams",
        headers={"X-CSRF-Token": csrf},
        json={
            "display_name": "Gamma",
            "client_scope_label": "Gamma Coverage",
            "normalized_client_scope_label": "gamma coverage",
        },
    )

    assert response.status_code == 422


def test_non_hr_is_denied_admin_and_hr_is_denied_cases() -> None:
    client = RawTestClient(create_app(ordinary_test_settings()))
    rm_csrf = _login(client, "ethan-tan")
    denied = client.post(
        "/api/admin/teams",
        headers={"X-CSRF-Token": rm_csrf},
        json={"display_name": "Gamma", "client_scope_label": "Gamma"},
    )
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "ADMINISTRATION_FORBIDDEN"
    assert client.get("/api/clm/zero-touch/cases?team_filter=TEAM_A").status_code == 403

    hr_client = RawTestClient(client.app)
    _login(hr_client, "hr-admin")
    assert hr_client.get("/api/clm/zero-touch/cases").status_code == 403
    assert hr_client.get("/api/clm/zero-touch/dashboard").status_code == 403


def test_hr_authority_change_revokes_existing_session() -> None:
    client = RawTestClient(create_app(ordinary_test_settings()))
    rm_csrf = _login(client, "ethan-tan")
    assert client.get("/api/auth/me").status_code == 200

    hr_client = RawTestClient(client.app)
    hr_csrf = _login(hr_client, "hr-admin")
    profiles = hr_client.get("/api/admin/profiles").json()
    ethan = next(item for item in profiles if item["user_id"] == "ethan-tan")
    changed = hr_client.patch(
        "/api/admin/profiles/ethan-tan",
        headers={"X-CSRF-Token": hr_csrf},
        json={"expected_version": ethan["version"], "team_id": "TEAM_B"},
    )
    assert changed.status_code == 200
    assert changed.json()["team_id"] == "TEAM_B"
    assert client.get("/api/auth/me").status_code == 401

    relogin = client.post(
        "/api/auth/login", json={"user_id": "ethan-tan", "password": TEST_PASSWORD}
    )
    assert relogin.status_code == 200
    assert relogin.json()["profile"]["team_id"] == "TEAM_B"
    assert rm_csrf not in relogin.text


def test_hr_cannot_self_demote() -> None:
    client = RawTestClient(create_app(ordinary_test_settings()))
    csrf = _login(client, "hr-admin")
    profile = next(
        item for item in client.get("/api/admin/profiles").json() if item["user_id"] == "hr-admin"
    )
    response = client.patch(
        "/api/admin/profiles/hr-admin",
        headers={"X-CSRF-Token": csrf},
        json={"expected_version": profile["version"], "role": "DIRECTOR"},
    )
    assert response.status_code == 422


def test_hr_cannot_self_demote_when_another_hr_exists() -> None:
    teams, profiles, _ = _repositories()
    service = AdministrationService(teams, profiles)
    service.create_profile(
        _hr(),
        user_id="hr-second",
        display_name="Second HR",
        role=Role.HR,
        team_id=None,
        password="runtime-only second HR password",
    )
    current = profiles.get("hr-admin")
    assert current is not None

    with pytest.raises(AdministrationValidationError):
        service.update_profile(
            _hr(),
            "hr-admin",
            expected_version=current.version,
            display_name=None,
            role=Role.DIRECTOR,
            role_supplied=True,
            team_id=None,
            team_supplied=False,
        )

    assert sum(item.role == Role.HR for item in profiles.list()) == 2


def test_concurrent_cross_demotion_atomically_preserves_exactly_one_hr() -> None:
    teams, profiles, _ = _repositories()
    service = AdministrationService(teams, profiles)
    service.create_profile(
        _hr(),
        user_id="hr-second",
        display_name="Second HR",
        role=Role.HR,
        team_id=None,
        password="runtime-only second HR password",
    )
    start = Barrier(3)
    actors = {
        "hr-admin": _hr(),
        "hr-second": AuthenticatedActor(
            profile=UserProfile(
                user_id="hr-second", display_name="Second HR", role=Role.HR, team_id=None
            )
        ),
    }

    def demote(actor_id: str, target_id: str) -> str:
        target = profiles.get(target_id)
        assert target is not None
        start.wait()
        try:
            service.update_profile(
                actors[actor_id],
                target_id,
                expected_version=target.version,
                display_name=None,
                role=Role.DIRECTOR,
                role_supplied=True,
                team_id=None,
                team_supplied=False,
            )
        except AdministrationValidationError:
            return "rejected"
        return "succeeded"

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(demote, "hr-admin", "hr-second")
        second = pool.submit(demote, "hr-second", "hr-admin")
        start.wait()
        outcomes = [first.result(), second.result()]

    assert sorted(outcomes) == ["rejected", "succeeded"]
    final = [profiles.get("hr-admin"), profiles.get("hr-second")]
    assert all(item is not None for item in final)
    records = [item for item in final if item is not None]
    assert sum(item.role == Role.HR for item in records) == 1
    assert sorted(item.version for item in records) == [1, 2]
    assert sorted(len(item.audit_events) for item in records) == [1, 2]
    assert all(type(item).model_validate(item) == item for item in records)


def test_mongo_team_duplicate_key_maps_to_bounded_conflict() -> None:
    class DuplicateCollection:
        def insert_one(self, document):
            raise DuplicateKeyError("driver detail must not escape")

    class Store:
        teams = DuplicateCollection()

    teams, _, _ = _repositories()
    source = teams.get(TeamId.TEAM_A)
    assert source is not None
    candidate = source.model_copy(
        update={
            "team_id": TeamId("TEAM_0123456789ABCDEF01234567"),
            "display_name": "Gamma",
            "normalized_display_name": "gamma",
            "client_scope_label": "Gamma Coverage",
            "normalized_client_scope_label": "gamma coverage",
            "audit_events": (),
        }
    )

    with pytest.raises(AdministrationConflictError) as captured:
        MongoTeamRepository(Store()).create(candidate)  # type: ignore[arg-type]

    assert str(captured.value) == ""
