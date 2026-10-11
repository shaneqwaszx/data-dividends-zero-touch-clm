"""Final-review edits retain lineage, refresh confirmation and never dispatch."""

from unittest.mock import patch
from uuid import UUID

import pytest
from test_zero_touch_orchestration import PDF, build_system, policy_rebind_snapshots, start_demo

from app.connectors.mock_idp import MockIdpProvider, MockIdpScenario
from app.services.zero_touch_errors import ZeroTouchRequestError


def final_review(*, with_policy=False):
    _, policy = policy_rebind_snapshots()
    client, zero, documents, target, _ = build_system(
        require_confirmation=True,
        policy_snapshot_provider=(lambda: policy) if with_policy else None,
    )
    summary = start_demo(client, "STRAIGHT_THROUGH", confirm_if_required=False)
    case_id = UUID(summary["case"]["case_id"])
    document = documents.list_documents(case_id=case_id)[0]
    return client, zero, documents, target, summary, case_id, document


def replacement_arguments(summary, case_id, document):
    return {
        "case_id": case_id,
        "document_id": document.document_id,
        "expected_document_event_count": len(document.events),
        "expected_automation_version": summary["version"],
        "expected_clm_version": summary["clm"]["version"],
        "expected_case_event_count": len(summary["case"]["events"]),
        "display_name": "final-review-replacement.pdf",
        "content_type": "application/pdf",
        "content": PDF,
    }


def confirmation_versions(summary):
    return {
        "expected_automation_version": summary["version"],
        "expected_clm_version": summary["clm"]["version"],
        "expected_case_event_count": len(summary["case"]["events"]),
    }


def test_final_review_replacement_refreshes_lineage_and_requires_fresh_confirmation():
    client, zero, documents, target, before, case_id, document = final_review()
    previous_exception = before["active_exceptions"][0]["exception_id"]
    edited = zero.replace_document(**replacement_arguments(before, case_id, document))
    after = client.get(f"/api/clm/zero-touch/cases/{case_id}").json()

    assert edited.status == "WAITING_FOR_REVIEW"
    assert edited.current_stage == "READINESS"
    assert after["clm"]["version"] > before["clm"]["version"]
    assert after["clm"]["readiness"]["blockers"] == []
    assert after["case"]["target_dispatch_confirmation"] is None
    assert after["clm"]["submission"] is None
    assert target.calls == ["search"]
    history = documents.list_documents(case_id=case_id)
    assert len(history) == 2
    retained = next(item for item in history if item.document_id == document.document_id)
    current = next(item for item in history if item.is_current_evidence)
    assert not retained.is_current_evidence
    assert current.document_id != retained.document_id
    assert current.state == "REVIEWED"
    assert any(
        str(item.exception_id) == previous_exception and item.status == "CANCELLED"
        for item in edited.exceptions
    )
    assert (
        client.post(
            f"/api/clm/zero-touch/cases/{case_id}/target-confirmation",
            json=confirmation_versions(before),
        ).status_code
        == 409
    )
    assert target.calls == ["search"]
    confirmed = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/target-confirmation",
        json=confirmation_versions(after),
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "COMPLETED"
    assert (
        target.calls.count("shell")
        == target.calls.count("policy")
        == target.calls.count("amend")
        == 1
    )
    zero.start(case_id=case_id)
    assert (
        target.calls.count("shell")
        == target.calls.count("policy")
        == target.calls.count("amend")
        == 1
    )


def test_final_review_replacement_exposes_new_source_conflict_instead_of_old_preview():
    _, zero, _, target, before, case_id, document = final_review()
    edited = zero.replace_document(
        **replacement_arguments(before, case_id, document),
        idp_provider=MockIdpProvider(MockIdpScenario.FIELD_MISMATCH),
    )
    assert edited.status == "WAITING_FOR_REVIEW"
    assert edited.current_stage == "DOCUMENT"
    assert all(
        item.blocker_code != "TARGET_CONFIRMATION_REQUIRED" for item in edited.active_exceptions
    )
    assert target.calls == ["search"]


@pytest.mark.parametrize(
    "version", ["expected_automation_version", "expected_clm_version", "expected_case_event_count"]
)
def test_final_review_replacement_rejects_stale_context_before_document_write(version):
    _, zero, documents, target, before, case_id, document = final_review()
    arguments = replacement_arguments(before, case_id, document)
    arguments[version] -= 1
    with pytest.raises(ZeroTouchRequestError, match="changed"):
        zero.replace_document(**arguments)
    assert len(documents.list_documents(case_id=case_id)) == 1
    assert target.calls == ["search"]


def test_final_review_replacement_reauthorizes_inside_case_lock_before_write():
    _, zero, documents, target, before, case_id, document = final_review()

    def rejected():
        raise PermissionError("Evidence decision unavailable")

    with (
        pytest.raises(PermissionError),
        patch.object(documents, "replace_document", wraps=documents.replace_document) as replace,
    ):
        zero.replace_document(
            **replacement_arguments(before, case_id, document), reauthorize=rejected
        )
    replace.assert_not_called()
    assert target.calls == ["search"]


def test_final_review_replacement_rejects_retained_target_execution_before_write():
    _, zero, documents, target, before, case_id, document = final_review()
    with (
        patch.object(zero._cases, "has_retained_target_execution", return_value=True),  # noqa: SLF001
        pytest.raises(ZeroTouchRequestError, match="frozen"),
    ):
        zero.replace_document(**replacement_arguments(before, case_id, document))
    assert len(documents.list_documents(case_id=case_id)) == 1
    assert target.calls == ["search"]


def test_final_classification_edit_rebinds_confirmation_to_current_clm_version():
    _, zero, _, target, before, case_id, _ = final_review(with_policy=True)
    edited = zero.bind_target_classification(
        case_id=case_id,
        kyc_customer_type="Company - Private",
        client_segment="Corporate",
        expected_automation_version=before["version"],
        expected_case_event_count=len(before["case"]["events"]),
        actor_id="synthetic-reviewer",
    )
    clm = zero._clm.get(case_id=case_id)  # noqa: SLF001
    case = zero._cases.get_case(case_id)  # noqa: SLF001
    assert clm is not None and case is not None
    assert edited.version > before["version"]
    assert len(edited.active_exceptions) == 1
    assert (
        edited.active_exceptions[0].evidence_version
        == f"target-confirmation:{clm.version}:{len(case.events)}"
    )
    assert target.calls == ["search"]
