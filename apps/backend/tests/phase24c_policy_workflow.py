"""Synthetic test helpers exercise the real four-eyes workflow, never direct activation."""

from app.domain.access import AuthenticatedActor, Role, UserProfile
from app.domain.policy import PolicyValue
from app.services.policy_management import PolicyManagementService


def approve_business_change(service: PolicyManagementService, policy_id: str, value: PolicyValue):
    hr = AuthenticatedActor(
        profile=UserProfile(
            user_id="hr-proposer", display_name="Synthetic proposer", role=Role.HR, team_id=None
        )
    )
    director = AuthenticatedActor(
        profile=UserProfile(
            user_id="director-decider",
            display_name="Synthetic decider",
            role=Role.DIRECTOR,
            team_id=None,
        )
    )
    c = service.create_proposal(
        hr,
        expected_catalogue_version=service.catalogue().version,
        changes={policy_id: value},
        reason="Synthetic runtime regression proposal",
    )
    p = c.proposals[-1]
    c = service.submit_proposal(
        hr, p.proposal_id, expected_catalogue_version=c.version, expected_proposal_version=p.version
    )
    p = c.proposals[-1]
    return service.decide_proposal(
        director,
        p.proposal_id,
        approve=True,
        expected_catalogue_version=c.version,
        expected_proposal_version=p.version,
        reason="Independent synthetic regression approval",
    )


def approve_http_policy(app, changes, reset_ids=()):
    from phase13_test_clients import RawTestClient
    from phase13_test_credentials import TEST_PASSWORD

    hr, director = RawTestClient(app), RawTestClient(app)
    try:
        for client, user in ((hr, "hr-admin"), (director, "olivia-koh")):
            result = client.post(
                "/api/auth/login", json={"user_id": user, "password": TEST_PASSWORD}
            )
            assert result.status_code == 200
            client.headers["X-CSRF-Token"] = result.json()["csrf_token"]
        c = hr.get("/api/policies").json()
        result = hr.post(
            "/api/policies/proposals",
            json={
                "expected_catalogue_version": c["version"],
                "changes": changes,
                "reset_ids": list(reset_ids),
                "reason": "Synthetic integration regression proposal",
            },
        )
        assert result.status_code == 201, result.text
        c = result.json()
        p = c["proposals"][-1]
        result = hr.post(
            f"/api/policies/proposals/{p['proposal_id']}/submit",
            json={
                "expected_catalogue_version": c["version"],
                "expected_proposal_version": p["version"],
            },
        )
        assert result.status_code == 200, result.text
        c = result.json()
        p = c["proposals"][-1]
        result = director.post(
            f"/api/policies/proposals/{p['proposal_id']}/decision",
            json={
                "expected_catalogue_version": c["version"],
                "expected_proposal_version": p["version"],
                "approve": True,
                "reason": "Independent synthetic integration approval",
            },
        )
        assert result.status_code == 200, result.text
        return result.json()

    finally:
        hr.close()
        director.close()
