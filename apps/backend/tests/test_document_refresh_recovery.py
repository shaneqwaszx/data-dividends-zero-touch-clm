"""A saved replacement refresh failure must expose safe owner recovery."""

from unittest.mock import patch
from uuid import uuid4

import pytest
from test_final_review_editing import final_review, replacement_arguments
from test_zero_touch_orchestration import PDF

from app.services.clm_errors import ClmInfrastructureError


def normal_final_review():
    from uuid import UUID

    from fastapi.testclient import TestClient
    from phase13_test_settings import ordinary_test_settings
    from test_zero_touch_orchestration import RecordingMockGoldTier, start_demo

    from app import main

    captured = []
    builder = main.build_zero_touch_orchestrator

    def capture(*args, **kwargs):
        zero = builder(*args, **kwargs)
        captured.append(zero)
        return zero

    target = RecordingMockGoldTier()
    with (
        patch("app.composition.MockGoldTierConnector", lambda **_: target),
        patch.object(main, "build_zero_touch_orchestrator", side_effect=capture),
    ):
        app = main.create_app(ordinary_test_settings(demo_controls_enabled=True))
    client = TestClient(app)
    before = start_demo(client, "STRAIGHT_THROUGH", confirm_if_required=False)
    zero = captured[0]
    cid = UUID(before["case"]["case_id"])
    documents = zero._documents
    original = documents.list_documents(case_id=cid)[0]
    return client, zero, documents, target, before, cid, original


def fail_replacement(*, normal_composition=False):
    client, zero, documents, target, before, cid, original = (
        normal_final_review() if normal_composition else final_review()
    )
    arguments = replacement_arguments(before, cid, original)
    headers = {
        "Content-Type": "application/pdf",
        "X-Document-Name": "synthetic-refresh-replacement.pdf",
        "X-Document-Event-Count": str(arguments["expected_document_event_count"]),
        "X-Automation-Version": str(before["version"]),
        "X-Clm-Version": str(before["clm"]["version"]),
        "X-Case-Event-Count": str(len(before["case"]["events"])),
    }
    with patch.object(
        zero._clm,
        "refresh_pre_submission_evidence",
        side_effect=ClmInfrastructureError(
            case_id=cid,
            orchestration_id=uuid4(),
            correlation_id=uuid4(),
            code="CLM_PERSISTENCE_UNAVAILABLE",
            message="Synthetic refresh unavailable.",
        ),
    ):
        failed = client.post(
            f"/api/clm/zero-touch/cases/{cid}/documents/{original.document_id}/replacement",
            headers=headers,
            content=PDF,
        )
    assert failed.status_code == 503
    current = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
    assert current["status"] == "RESUMING" and current["current_stage"] == "DOCUMENT"
    assert current["active_exceptions"] == [] and current["technical_failure"] is None
    assert current["timeline"][-1]["code"] == "DOCUMENT_REPLACEMENT_ACCEPTED"
    assert len(documents.list_documents(case_id=cid)) == 2
    assert target.calls == ["search"]
    return client, zero, documents, target, current, cid, original


def test_partial_refresh_get_exposes_recovery_instead_of_indefinite_processing():
    client, zero, documents, target, current, cid, original = fail_replacement()
    assert current["document_refresh_recovery"] == {"can_resume": True}
    retained = zero.get(case_id=cid).model_dump(mode="json")
    reload = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
    assert reload["document_refresh_recovery"] == current["document_refresh_recovery"]
    assert zero.get(case_id=cid).model_dump(mode="json") == retained
    history = documents.list_documents(case_id=cid)
    assert next(
        d for d in history if d.document_id == original.document_id
    ).superseded_by_document_id
    assert sum(d.is_current_evidence for d in history) == 1
    assert target.calls == ["search"]


def recovery_headers(summary):
    return {
        "X-Automation-Id": summary["automation_id"],
        "X-Automation-Version": str(summary["version"]),
        "X-Clm-Version": str(summary["clm"]["version"]),
        "X-Case-Event-Count": str(len(summary["case"]["events"])),
    }


def assert_retained_history(before, after):
    """Dependent field reviews can advance; insertion and source rewriting cannot."""
    before = [d.model_dump(mode="json") if hasattr(d, "model_dump") else d for d in before]
    after = [d.model_dump(mode="json") if hasattr(d, "model_dump") else d for d in after]
    assert len(after) == len(before)
    by_id = {d["document_id"]: d for d in after}
    assert set(by_id) == {d["document_id"] for d in before}
    for old in before:
        current = by_id[old["document_id"]]
        if old["superseded_by_document_id"] is not None:
            assert current == old  # Historical evidence is immutable.
        else:
            for key in (
                "case_id",
                "document_id",
                "document_version",
                "correlation_id",
                "display_name",
                "media_type",
                "size_bytes",
                "profile",
                "provider_environment",
                "created_at",
                "processed_at",
                "supersedes_document_id",
                "superseded_by_document_id",
                "pages",
                "ownership_observations",
                "classification_observations",
            ):
                assert current.get(key) == old.get(key), key
            assert current["events"][: len(old["events"])] == old["events"]
            assert len(current["fields"]) == len(old["fields"])
            for left, right in zip(old["fields"], current["fields"], strict=True):
                for key in (
                    "field_key",
                    "original_extracted_value",
                    "normalized_value",
                    "confidence",
                    "provenance",
                    "candidates",
                ):
                    assert left.get(key) == right.get(key), key


def test_recovery_refreshes_once_retains_documents_and_retry_is_idempotent():
    client, zero, documents, target, current, cid, _ = fail_replacement()
    history = documents.list_documents(case_id=cid)
    with patch.object(
        zero._clm,
        "refresh_pre_submission_evidence",
        wraps=zero._clm.refresh_pre_submission_evidence,
    ) as refresh:
        resumed = client.post(
            f"/api/clm/zero-touch/cases/{cid}/resume", headers=recovery_headers(current)
        )
        assert resumed.status_code == 200
        assert refresh.call_count == 1 and refresh.call_args.kwargs["document_revision"] is True
        after = resumed.json()
        assert after["document_refresh_recovery"] is None
        assert after["status"] == "WAITING_FOR_REVIEW" and after["current_stage"] == "READINESS"
        assert after["clm"]["version"] > current["clm"]["version"]
        assert [e["blocker_code"] for e in after["active_exceptions"]] == [
            "TARGET_CONFIRMATION_REQUIRED"
        ]
        assert_retained_history(history, documents.list_documents(case_id=cid))
        retained = zero.get(case_id=cid).model_dump(mode="json")
        assert (
            client.post(
                f"/api/clm/zero-touch/cases/{cid}/resume", headers=recovery_headers(after)
            ).status_code
            == 200
        )
        assert zero.get(case_id=cid).model_dump(mode="json") == retained
        assert refresh.call_count == 1
    assert target.calls == ["search"]


@pytest.mark.parametrize(
    "header",
    [None, "X-Automation-Id", "X-Automation-Version", "X-Clm-Version", "X-Case-Event-Count"],
)
def test_recovery_missing_or_stale_identity_versions_reject_before_write(header):
    client, zero, documents, target, current, cid, _ = fail_replacement()
    headers = recovery_headers(current) if header else {}
    if header:
        headers[header] = (
            str(uuid4()) if header == "X-Automation-Id" else str(int(headers[header]) + 1)
        )
    before = zero.get(case_id=cid).model_dump(mode="json")
    history = documents.list_documents(case_id=cid)
    with patch.object(zero._clm, "refresh_pre_submission_evidence") as refresh:
        assert (
            client.post(f"/api/clm/zero-touch/cases/{cid}/resume", headers=headers).status_code
            == 409
        )
        refresh.assert_not_called()
    assert zero.get(case_id=cid).model_dump(mode="json") == before
    assert documents.list_documents(case_id=cid) == history and target.calls == ["search"]


def test_concurrent_recovery_accepts_one_current_request_without_replay():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    client, zero, documents, target, current, cid, _ = fail_replacement()
    headers = recovery_headers(current)
    history = documents.list_documents(case_id=cid)
    barrier = Barrier(2)

    def resume():
        barrier.wait(timeout=10)
        return client.post(f"/api/clm/zero-touch/cases/{cid}/resume", headers=headers).status_code

    with (
        patch.object(
            zero._clm,
            "refresh_pre_submission_evidence",
            wraps=zero._clm.refresh_pre_submission_evidence,
        ) as refresh,
        ThreadPoolExecutor(max_workers=2) as pool,
    ):
        assert sorted(pool.map(lambda _: resume(), range(2))) == [200, 409]
        assert refresh.call_count == 1
    assert_retained_history(history, documents.list_documents(case_id=cid))
    assert target.calls == ["search"]


def test_recovery_reauthorizes_inside_lock_before_refresh():
    from uuid import UUID

    from app.services.zero_touch_errors import ZeroTouchRequestError

    _, zero, _, target, current, cid, _ = fail_replacement()

    def rejected():
        raise PermissionError("Creator permission was revoked.")

    with patch.object(zero._clm, "refresh_pre_submission_evidence") as refresh:
        with pytest.raises(PermissionError):
            zero.start(case_id=cid, reauthorize_document_recovery=rejected)
        refresh.assert_not_called()
        with pytest.raises(ZeroTouchRequestError, match="changed"):
            zero.start(case_id=cid, expected_automation_id=UUID(current["automation_id"]))
    assert target.calls == ["search"]


def test_retained_target_intent_or_uncertainty_freezes_recovery():
    client, zero, _, target, current, cid, _ = fail_replacement()
    before = zero.get(case_id=cid).model_dump(mode="json")
    with (
        patch.object(zero._cases, "has_retained_target_execution", return_value=True),
        patch.object(zero._clm, "refresh_pre_submission_evidence") as refresh,
    ):
        assert client.get(f"/api/clm/zero-touch/cases/{cid}").json()[
            "document_refresh_recovery"
        ] == {"can_resume": False}
        response = client.post(
            f"/api/clm/zero-touch/cases/{cid}/resume", headers=recovery_headers(current)
        )
        assert (
            response.status_code == 409
            and response.json()["detail"]["code"] == "ZERO_TOUCH_DOCUMENT_REFRESH_FROZEN"
        )
        refresh.assert_not_called()
    assert zero.get(case_id=cid).model_dump(mode="json") == before and target.calls == ["search"]


def test_http_recovery_creator_team_session_authority():
    from phase13_test_clients import RawTestClient
    from phase13_test_credentials import TEST_PASSWORD
    from test_phase13_auth_rbac import _login

    client, zero, documents, target, current, cid, _ = fail_replacement()
    path = f"/api/clm/zero-touch/cases/{cid}/resume"
    retained = zero.get(case_id=cid).model_dump(mode="json")
    history = documents.list_documents(case_id=cid)
    anonymous = RawTestClient(client.app)
    assert anonymous.post(path, headers=recovery_headers(current)).status_code == 401
    for actor, expected in [("ethan-tan", 403), ("olivia-koh", 403), ("sophia-ng", 404)]:
        other = RawTestClient(client.app)
        csrf = _login(other, actor, TEST_PASSWORD)
        projection = other.get(f"/api/clm/zero-touch/cases/{cid}")
        assert projection.status_code == (404 if expected == 404 else 200)
        if projection.status_code == 200:
            assert projection.json()["document_refresh_recovery"] == {"can_resume": False}
        assert (
            other.post(
                path, headers={**recovery_headers(current), "X-CSRF-Token": csrf}
            ).status_code
            == expected
        )
    assert zero.get(case_id=cid).model_dump(mode="json") == retained
    assert documents.list_documents(case_id=cid) == history and target.calls == ["search"]


def test_repeated_refresh_failure_retains_actionable_checkpoint_without_false_completion():
    client, zero, documents, target, current, cid, _ = fail_replacement()
    retained = zero.get(case_id=cid).model_dump(mode="json")
    history = documents.list_documents(case_id=cid)
    with patch.object(
        zero._clm,
        "refresh_pre_submission_evidence",
        side_effect=ClmInfrastructureError(
            case_id=cid,
            orchestration_id=uuid4(),
            correlation_id=uuid4(),
            code="CLM_PERSISTENCE_UNAVAILABLE",
            message="Synthetic refresh unavailable.",
        ),
    ):
        assert (
            client.post(
                f"/api/clm/zero-touch/cases/{cid}/resume", headers=recovery_headers(current)
            ).status_code
            == 503
        )
    assert zero.get(case_id=cid).model_dump(mode="json") == retained
    assert client.get(f"/api/clm/zero-touch/cases/{cid}").json()["document_refresh_recovery"] == {
        "can_resume": True
    }
    assert documents.list_documents(case_id=cid) == history and target.calls == ["search"]


def test_deleted_case_recovery_cannot_resurrect_any_evidence():
    from phase13_test_clients import RawTestClient
    from phase13_test_credentials import TEST_PASSWORD
    from test_phase13_auth_rbac import _login

    client, zero, documents, target, current, cid, _ = fail_replacement(normal_composition=True)
    manager = RawTestClient(client.app)
    csrf = _login(manager, "ethan-tan", TEST_PASSWORD)
    assert (
        manager.delete(
            f"/api/clm/zero-touch/cases/{cid}", headers={"X-CSRF-Token": csrf}
        ).status_code
        == 204
    )
    with patch.object(zero._clm, "refresh_pre_submission_evidence") as refresh:
        assert (
            client.post(
                f"/api/clm/zero-touch/cases/{cid}/resume", headers=recovery_headers(current)
            ).status_code
            == 404
        )
        refresh.assert_not_called()
    assert zero._cases.get_case(cid) is None and zero._clm.get(case_id=cid) is None
    assert documents._repository.list_for_case(cid) == [] and target.calls == ["search"]
