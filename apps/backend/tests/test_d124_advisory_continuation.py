"""D-124: ACRA Marketplace Mock, advisory review, explicit continuation, GoldTier Sandbox.

A read never changes a held case. Only an authorized resume continues it, and only an explicit
confirmation writes. Recorded GoldTier transport, synthetic data, in memory.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from phase13_test_clients import RawTestClient
from phase13_test_credentials import TEST_PASSWORD
from scripts.seed_zero_touch_happy_path_companies import manage_fixtures
from test_goldtier_xpi_sandbox import _confirmation_arguments, _existing_candidate_system
from test_slice_b_registry_demo import confirm
from test_zero_touch_database_happy_path import NoAcra, RecordingTarget, sandbox_settings
from test_zero_touch_entity_types import (
    GAMMA,
    GAMMA_SHARES,
    agreement_with,
    gamma_at_ownership,
)

from app.domain.ownership import OwnershipAnalysisState
from app.domain.zero_touch import AutomationEventType, AutomationStage
from app.main import create_app
from app.persistence.composition import build_persistence_bundle
from app.services.clm_orchestration import ClmOrchestrationService
from app.services.ownership_analysis import OwnershipAnalysisService
from app.services.zero_touch_errors import ZeroTouchRequestError

ADVISORY = {"on": False}
TARGET_CONFIRMATION = ["TARGET_CONFIRMATION_REQUIRED"]


class Target(RecordingTarget):
    fail_get = False

    def request(self, method: str, url: str, **options: Any) -> Any:
        if method == "GET" and self.fail_get:
            self.calls.append((method, url, "FAILED"))
            raise RuntimeError("synthetic outage")
        return super().request(method, url, **options)


@pytest.fixture(autouse=True)
def review_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Off first, so a case is held as it was before its review became advisory."""

    ADVISORY["on"] = False
    monkeypatch.setattr(
        OwnershipAnalysisService,
        "review_is_advisory",
        lambda self, record: (
            ADVISORY["on"]
            and record.state == OwnershipAnalysisState.REVIEW_REQUIRED
            and self._current_for_readiness(record)  # noqa: SLF001
        ),
    )


@contextmanager
def lane() -> Iterator[tuple[TestClient, Target, Any]]:
    settings = sandbox_settings()
    bundle = build_persistence_bundle(settings)
    manage_fixtures(bundle.registry_snapshots, now=datetime.now(UTC), seed=True)
    target = Target(GAMMA.name, GAMMA.uen)
    with (
        patch("app.main.build_persistence_bundle", return_value=bundle),
        TestClient(
            create_app(settings, acra_connector=NoAcra(), goldtier_transport=target)
        ) as client,
    ):
        yield client, target, bundle


def signed_in(client: TestClient, user: str) -> tuple[Any, str]:
    other = RawTestClient(client.app)
    response = other.post("/api/auth/login", json={"user_id": user, "password": TEST_PASSWORD})
    assert response.status_code == 200, response.text
    return other, response.json()["csrf_token"]


def url(case_id: str, action: str = "") -> str:
    return f"/api/clm/zero-touch/cases/{case_id}{action}"


def read(client: Any, case_id: str) -> dict:
    response = client.get(url(case_id))
    assert response.status_code == 200, response.text
    return response.json()


def context(summary: dict) -> dict[str, str]:
    return {
        "X-Automation-Id": summary["automation_id"],
        "X-Automation-Version": str(summary["version"]),
        "X-Clm-Version": str(summary["clm"]["version"]),
        "X-Case-Event-Count": str(len(summary["case"]["events"])),
    }


def resume(client: Any, summary: dict, **headers: str) -> Any:
    return client.post(
        url(summary["case"]["case_id"], "/resume"), headers={**context(summary), **headers}
    )


def state(bundle: Any, case_id: str) -> tuple[int, int]:
    record = bundle.automation.get_for_case(UUID(case_id))
    return record.version, len(record.events)


def exceptions(summary: dict) -> list[str]:
    return [item["exception_type"] for item in summary["active_exceptions"]]


def codes(bundle: Any, case_id: str) -> list[str]:
    return [event.code for event in bundle.automation.get_for_case(UUID(case_id)).events]


def writes(target: Target) -> list[str]:
    return [call[0] for call in target.calls if call[0] != "GET"]


def reads(target: Target) -> int:
    return len([call for call in target.calls if call[0] == "GET"])


def held(client: TestClient) -> str:
    """A case held at Ownership, whose review has since become advisory."""

    case_id = gamma_at_ownership(client)["case"]["case_id"]
    ADVISORY["on"] = True
    return case_id


def continued(client: TestClient) -> tuple[str, dict]:
    case_id = held(client)
    response = resume(client, read(client, case_id))
    assert response.status_code == 200, response.text
    return case_id, response.json()


def legacy(bundle: Any, case_id: str) -> None:
    """A stage-order-1 record held at Ownership with no retained Search."""

    identity = UUID(case_id)

    def rewrite(repository: Any, change: Any) -> None:
        for store in vars(repository).values():
            if isinstance(store, dict):
                for key, value in list(store.items()):
                    if getattr(value, "case_id", None) == identity or key == identity:
                        store[key] = change(value)

    rewrite(bundle.automation, lambda record: record.model_copy(update={
        "stage_order_version": 1,
        "completed_stages": tuple(
            stage for stage in record.completed_stages
            if stage != AutomationStage.GOLDTIER_SEARCH
        ),
    }))
    rewrite(bundle.clm, lambda record: record.model_copy(
        update={"target_search_checkpoint": None}
    ))
    rewrite(bundle.onboarding, lambda record: record.model_copy(
        update={"initial_target_search": None}
    ))


# 1, 2: reads are read-only --------------------------------------------------------------------


def test_support_opens_a_held_case_and_nothing_changes() -> None:
    with lane() as (client, target, bundle):
        case_id = held(client)
        before, calls = state(bundle, case_id), len(target.calls)
        support, _ = signed_in(client, "support-user")
        summary = read(support, case_id)
        assert state(bundle, case_id) == before and len(target.calls) == calls
        assert summary["current_stage"] == "OWNERSHIP"
        assert summary["advisory_continuation"] == {"can_resume": False}


def test_the_rm_opens_a_held_case_and_it_stays_held() -> None:
    with lane() as (client, target, bundle):
        case_id = held(client)
        before, calls = state(bundle, case_id), len(target.calls)
        first, second = read(client, case_id), read(client, case_id)
        assert state(bundle, case_id) == before and len(target.calls) == calls
        assert first["current_stage"] == second["current_stage"] == "OWNERSHIP"
        assert first["advisory_continuation"] == {"can_resume": True}


# 3: authorized continuation -------------------------------------------------------------------


def test_the_rm_resumes_and_the_case_waits_for_confirmation() -> None:
    with lane() as (client, target, bundle):
        case_id, summary = continued(client)
        assert exceptions(summary) == TARGET_CONFIRMATION
        assert summary["clm"]["readiness"]["blockers"] == []
        assert summary["advisory_continuation"] is None
        assert "ADVISORY_CONTINUATION_REQUESTED" in codes(bundle, case_id)
        assert "OWNERSHIP_REVIEW_ADVISORY" in codes(bundle, case_id)
        assert writes(target) == []


def test_only_the_creator_with_current_versions_can_continue() -> None:
    with lane() as (client, target, bundle):
        case_id = held(client)
        summary = read(client, case_id)
        before = state(bundle, case_id)
        teammate, teammate_csrf = signed_in(client, "ethan-tan")
        support, support_csrf = signed_in(client, "support-user")
        assert resume(teammate, summary, **{"X-CSRF-Token": teammate_csrf}).status_code == 403
        assert resume(support, summary, **{"X-CSRF-Token": support_csrf}).status_code in {403, 404}
        assert client.post(url(case_id, "/resume")).status_code == 409  # no version context
        assert state(bundle, case_id) == before and writes(target) == []


def test_no_other_route_releases_a_hold_or_reaches_a_sandbox_write() -> None:
    with lane() as (client, target, bundle):
        case_id = held(client)
        legacy(bundle, case_id)
        searches = reads(target)
        teammate, csrf = signed_in(client, "ethan-tan")
        for route, body in (("/start", None), ("/intake/complete", {"expected_document_count": 2})):
            for caller, headers in ((teammate, {"X-CSRF-Token": csrf}), (client, {})):
                caller.post(url(case_id, route), json=body, headers=headers)
        summary = read(client, case_id)
        assert summary["current_stage"] == "OWNERSHIP"
        assert "TARGET_CONFIRMATION_REQUIRED" not in exceptions(summary)
        assert summary["advisory_continuation"] == {"can_resume": True}
        assert "ADVISORY_CONTINUATION_REQUESTED" not in codes(bundle, case_id)
        assert reads(target) == searches  # no Search either
        refused = teammate.post(
            url(case_id, "/target-confirmation"),
            headers={"X-CSRF-Token": csrf},
            json={
                "expected_automation_version": summary["version"],
                "expected_clm_version": summary["clm"]["version"],
                "expected_case_event_count": len(summary["case"]["events"]),
            },
        )
        assert refused.status_code >= 400
        assert writes(target) == []


def direct_target_routes(client: Any, case_id: str, summary: dict, csrf: str) -> list[int]:
    headers = {"X-CSRF-Token": csrf}
    confirmation = client.post(
        f"/api/clm/cases/{case_id}/target-confirmation",
        headers=headers,
        json={
            "expected_clm_version": summary["clm"]["version"],
            "expected_case_event_count": len(summary["case"]["events"]),
        },
    )
    submission = client.post(f"/api/clm/cases/{case_id}/submit", headers=headers)
    return [confirmation.status_code, submission.status_code]


def test_the_direct_clm_routes_cannot_pass_a_held_case() -> None:
    with lane() as (client, target, bundle):
        case_id = held(client)
        summary = read(client, case_id)
        before = state(bundle, case_id)
        teammate, csrf = signed_in(client, "ethan-tan")
        assert direct_target_routes(teammate, case_id, summary, csrf) == [409, 409]
        assert writes(target) == []
        assert state(bundle, case_id) == before
        assert bundle.onboarding.get(UUID(case_id)).target_dispatch_confirmation is None


def test_the_direct_clm_routes_cannot_pass_a_failed_continuation() -> None:
    with lane() as (client, target, _):
        case_id = held(client)
        with patch.object(
            ClmOrchestrationService, "evaluate", side_effect=RuntimeError("synthetic fault")
        ):
            resume(client, read(client, case_id))
        summary = read(client, case_id)
        assert summary["status"] == "TECHNICAL_FAILURE"
        teammate, csrf = signed_in(client, "ethan-tan")
        assert direct_target_routes(teammate, case_id, summary, csrf) == [409, 409]
        assert writes(target) == []


def test_a_retained_identity_decision_is_applied_by_resume_never_by_a_read() -> None:
    zero, _, _, transport, created = _existing_candidate_system()
    arguments = _confirmation_arguments(zero, created)
    arguments.pop("expected_automation_version")
    zero._clm.confirm_existing_customer(**arguments)  # noqa: SLF001 (the interrupted write)
    before = zero._repository.get_for_case(created.case_id)  # noqa: SLF001
    calls = len(transport.calls)
    assert zero.advisory_continuation_pending(before)
    assert zero.get(case_id=created.case_id).version == before.version
    clm = zero._clm.get(case_id=created.case_id)  # noqa: SLF001
    case = zero._cases.get_case(created.case_id)  # noqa: SLF001
    applied = zero.start(
        case_id=created.case_id,
        refresh_document_checkpoint=True,
        expected_automation_id=before.automation_id,
        expected_automation_version=before.version,
        expected_clm_version=clm.version,
        expected_case_event_count=len(case.events),
    )
    assert applied.version > before.version
    assert applied.events[-1].code == "EXISTING_GOLDTIER_CUSTOMER_CONFIRMED"
    assert len(transport.calls) == calls


# 4, 5: legacy records and failed continuation -------------------------------------------------


def test_a_legacy_held_case_makes_no_hidden_search_on_read() -> None:
    with lane() as (client, target, bundle):
        case_id = held(client)
        legacy(bundle, case_id)
        before, searches = state(bundle, case_id), reads(target)
        support, _ = signed_in(client, "support-user")
        read(support, case_id)
        summary = read(client, case_id)
        assert state(bundle, case_id) == before and reads(target) == searches
        response = resume(client, summary)
        assert response.status_code == 200, response.text
        assert reads(target) > searches  # the Search runs on the explicit request
        assert exceptions(response.json()) == TARGET_CONFIRMATION
        assert writes(target) == []


def test_a_failed_search_during_continuation_can_be_retried() -> None:
    with lane() as (client, target, bundle):
        case_id = held(client)
        legacy(bundle, case_id)
        target.fail_get = True
        failed = resume(client, read(client, case_id)).json()
        assert failed["status"] == "TECHNICAL_FAILURE"
        assert failed["advisory_continuation"] == {"can_resume": True}
        target.fail_get = False
        retried = resume(client, read(client, case_id))
        assert retried.status_code == 200, retried.text
        assert exceptions(retried.json()) == TARGET_CONFIRMATION
        assert retried.json()["technical_failure"] is None
        assert writes(target) == []


def test_an_unexpected_fault_during_continuation_can_be_retried() -> None:
    with lane() as (client, target, _):
        case_id = held(client)
        with patch.object(
            ClmOrchestrationService, "evaluate", side_effect=RuntimeError("synthetic fault")
        ):
            failed = resume(client, read(client, case_id))
        assert failed.status_code >= 500
        summary = read(client, case_id)
        assert summary["status"] == "TECHNICAL_FAILURE"
        assert summary["advisory_continuation"] == {"can_resume": True}
        retried = resume(client, summary)
        assert retried.status_code == 200, retried.text
        assert exceptions(retried.json()) == TARGET_CONFIRMATION
        assert writes(target) == []


def test_a_failure_after_the_attempt_got_further_offers_no_retry() -> None:
    with lane() as (client, _, bundle):
        case_id, _ = continued(client)  # finished: it raised the target confirmation
        identity = UUID(case_id)
        for store in vars(bundle.automation).values():
            if isinstance(store, dict):
                for key, value in list(store.items()):
                    if getattr(value, "case_id", None) == identity:
                        failure = value.events[-1].model_copy(update={
                            "sequence": len(value.events) + 1,
                            "event_type": AutomationEventType.AUTOMATION_TECHNICAL_FAILURE,
                        })
                        store[key] = value.model_copy(update={
                            "status": "TECHNICAL_FAILURE",
                            "technical_failure": {"code": "OTHER", "message": "Other."},
                            "events": [*value.events, failure],
                        })
        assert read(client, case_id).get("advisory_continuation") is None


def test_a_failure_that_was_not_a_continuation_offers_no_retry() -> None:
    with lane() as (client, _, bundle):
        case_id = held(client)
        identity = UUID(case_id)
        for store in vars(bundle.automation).values():
            if isinstance(store, dict):
                for key, value in list(store.items()):
                    if getattr(value, "case_id", None) == identity:
                        store[key] = value.model_copy(update={
                            "status": "TECHNICAL_FAILURE",
                            "technical_failure": {"code": "OTHER", "message": "Other."},
                        })
        assert read(client, case_id).get("advisory_continuation") is None


# 6, 7, 8: confirmation -------------------------------------------------------------------------


def test_every_sandbox_write_follows_the_explicit_confirmation() -> None:
    with lane() as (client, target, _):
        case_id, summary = continued(client)
        read(client, case_id)
        assert writes(target) == []
        assert confirm(client, summary)["status"] == "COMPLETED"
        assert writes(target) == ["POST", "POST"]


def test_support_and_other_teams_cannot_confirm() -> None:
    with lane() as (client, target, _):
        case_id, summary = continued(client)
        body = {
            "expected_automation_version": summary["version"],
            "expected_clm_version": summary["clm"]["version"],
            "expected_case_event_count": len(summary["case"]["events"]),
        }
        for user in ("support-user", "sophia-ng"):
            other, csrf = signed_in(client, user)
            refused = other.post(
                url(case_id, "/target-confirmation"), json=body, headers={"X-CSRF-Token": csrf}
            )
            assert refused.status_code in {403, 404}, (user, refused.text)
        assert writes(target) == []


def test_repeated_resume_and_confirmation_never_duplicate_a_write() -> None:
    with lane() as (client, target, bundle):
        case_id = held(client)
        stale = read(client, case_id)
        summary = resume(client, stale).json()
        assert resume(client, stale).status_code == 409  # a repeat of the same click
        at_rest = state(bundle, case_id)
        assert resume(client, read(client, case_id)).status_code == 200
        assert state(bundle, case_id) == at_rest
        assert confirm(client, summary)["status"] == "COMPLETED"
        sent = writes(target)
        again = client.post(url(case_id, "/target-confirmation"), json={
            "expected_automation_version": summary["version"],
            "expected_clm_version": summary["clm"]["version"],
            "expected_case_event_count": len(summary["case"]["events"]),
        })
        assert again.status_code >= 400
        assert client.post(url(case_id, "/resume")).status_code == 200
        assert writes(target) == sent


# 9: protections --------------------------------------------------------------------------------


def test_a_stale_analysis_is_not_offered_and_does_not_release() -> None:
    with (
        lane() as (client, target, _),
        patch.object(OwnershipAnalysisService, "_current_for_readiness", return_value=False),
    ):
        case_id = held(client)
        summary = read(client, case_id)
        assert summary["advisory_continuation"] is None
        assert "OWNERSHIP_REVIEW_REQUIRED" in summary["clm"]["readiness"]["blockers"]
        assert writes(target) == []


def test_a_failed_analysis_is_not_offered_and_cannot_be_sent() -> None:
    with lane() as (client, target, bundle):
        case_id = held(client)
        identity = UUID(case_id)
        for store in vars(bundle.ownership).values():
            if isinstance(store, dict):
                for key, value in list(store.items()):
                    if getattr(value, "case_id", None) == identity:
                        store[key] = value.model_copy(
                            update={"state": OwnershipAnalysisState.FAILED}
                        )
        assert read(client, case_id)["advisory_continuation"] is None
        assert writes(target) == []


# 10, 11: partnership warnings and the visible review --------------------------------------------


def test_a_partnership_share_problem_stays_advisory_through_to_sandbox() -> None:
    ADVISORY["on"] = True
    with lane() as (client, target, _):
        shares = [("DEMO GAMMA PERSON P1", "29"), *GAMMA_SHARES[1:]]  # totals 99
        current = gamma_at_ownership(client, agreement_with(shares))
        case_id = current["case"]["case_id"]
        assert exceptions(current) == TARGET_CONFIRMATION
        ownership = client.get(f"/api/onboarding/cases/{case_id}/ownership").json()
        assert ownership["state"] == "REVIEW_REQUIRED"
        assert writes(target) == []
        assert confirm(client, read(client, case_id))["status"] == "COMPLETED"
        assert writes(target) == ["POST", "POST"]


def test_the_open_review_stays_visible_through_confirmation() -> None:
    with lane() as (client, _, bundle):
        case_id, summary = continued(client)
        done = confirm(client, summary)
        ownership = client.get(f"/api/onboarding/cases/{case_id}/ownership").json()
        assert done["status"] == "COMPLETED"
        assert ownership["state"] == "REVIEW_REQUIRED"
        assert ownership["poc_basis_accepted"] is False
        assert ownership["issues"]
        confirmation = bundle.onboarding.get(UUID(case_id)).target_dispatch_confirmation
        assert "OWNERSHIP_REVIEW_ADVISORY" in confirmation.warnings


# Rollback: what `blocking` actually does (D-124 S8) ---------------------------------------------


def test_rollback_a_new_case_holds_at_ownership() -> None:
    with lane() as (client, target, _):
        current = gamma_at_ownership(client)
        assert current["current_stage"] == "OWNERSHIP"
        assert "OWNERSHIP_REVIEW_REQUIRED" in current["clm"]["readiness"]["blockers"]
        assert writes(target) == []


def test_rollback_a_held_case_stays_held_with_no_continuation() -> None:
    with lane() as (client, target, bundle):
        case_id = held(client)
        ADVISORY["on"] = False
        summary = read(client, case_id)
        assert summary["advisory_continuation"] is None
        assert client.post(url(case_id, "/resume")).status_code == 200
        assert read(client, case_id)["current_stage"] == "OWNERSHIP"
        assert "ADVISORY_CONTINUATION_REQUESTED" not in codes(bundle, case_id)
        assert writes(target) == []


def test_rollback_a_failed_continuation_retries_back_to_the_hold_without_writing() -> None:
    with lane() as (client, target, _):
        case_id = held(client)
        with patch.object(
            ClmOrchestrationService, "evaluate", side_effect=RuntimeError("synthetic fault")
        ):
            resume(client, read(client, case_id))
        ADVISORY["on"] = False
        summary = read(client, case_id)
        assert summary["advisory_continuation"] == {"can_resume": True}
        retried = resume(client, summary)
        assert retried.status_code == 200, retried.text
        assert "OWNERSHIP_REVIEW_REQUIRED" in retried.json()["clm"]["readiness"]["blockers"]
        assert writes(target) == []


def test_rollback_a_case_waiting_for_confirmation_cannot_be_sent() -> None:
    with lane() as (client, target, _):
        case_id, summary = continued(client)
        ADVISORY["on"] = False
        refused = client.post(url(case_id, "/target-confirmation"), json={
            "expected_automation_version": summary["version"],
            "expected_clm_version": summary["clm"]["version"],
            "expected_case_event_count": len(summary["case"]["events"]),
        })
        assert refused.status_code == 409
        assert writes(target) == []


def interrupted(fail_on_call: int) -> Any:
    original = ClmOrchestrationService.submit
    calls = {"count": 0}

    def submit(self: Any, **options: Any) -> Any:
        calls["count"] += 1
        if calls["count"] == fail_on_call:
            raise ZeroTouchRequestError(code="SYNTHETIC_STOP", message="Synthetic stop.")
        return original(self, **options)

    return patch.object(ClmOrchestrationService, "submit", submit)


def test_rollback_a_confirmed_case_with_no_write_fails_without_writing() -> None:
    with lane() as (client, target, _):
        case_id, summary = continued(client)
        with interrupted(1), pytest.raises(AssertionError):
            confirm(client, summary)
        assert writes(target) == []
        ADVISORY["on"] = False
        client.post(url(case_id, "/resume"))
        assert read(client, case_id)["status"] == "TECHNICAL_FAILURE"
        assert writes(target) == []


def test_rollback_after_create_still_completes_the_policy_without_repeating_create() -> None:
    with lane() as (client, target, _):
        case_id, summary = continued(client)
        with interrupted(2), pytest.raises(AssertionError):
            confirm(client, summary)
        assert writes(target) == ["POST"]
        ADVISORY["on"] = False
        client.post(url(case_id, "/resume"))
        assert writes(target) == ["POST", "POST"]
