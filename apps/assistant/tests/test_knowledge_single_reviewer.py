"""D-076 (proposed): Directors handle enhancement requests end to end, and the POC's
single-reviewer setting (``knowledge_single_reviewer``, on by default because the synthetic
users have one Director) lets a reviewer publish an entry they wrote or edited once they
confirm it. Each such decision is marked single-reviewer. With the setting off, the
two-person rule applies unchanged. Retiring an entry always takes two reviewers."""

from typing import Any

import httpx

from ai_assistant.config import AiAssistantSettings
from ai_assistant.knowledge.models import EntryKind, EntryStatus
from ai_assistant.knowledge.service import KnowledgeBase
from tests.test_knowledge_review import (  # noqa: F401 - kb is a pytest fixture
    client,
    drafted,
    edit,
    fix,
    kb,
    not_helpful,
    shown_hash,
)

CONFIRM_MESSAGE = "Confirm that you are publishing this entry as its only reviewer."


def decide(
    kb: KnowledgeBase,  # noqa: F811
    session: str,
    entry_id: str,
    version: int,
    *,
    approve: bool = True,
    confirm: bool = False,
    single_reviewer: bool = True,
) -> httpx.Response:
    return client(kb, session, single_reviewer=single_reviewer).post(
        f"/assistant/knowledge/entries/{entry_id}/versions/{version}/decision",
        json={
            "approve": approve,
            "content_hash": shown_hash(kb, entry_id, version),
            "confirm_single_reviewer": confirm,
        },
    )


def history(kb: KnowledgeBase, entry_id: str) -> list[tuple[str, str, bool]]:  # noqa: F811
    return [
        (r["reviewer"], r["decision"], r["single_reviewer"]) for r in kb.store.reviews(entry_id)
    ]


def test_single_reviewer_mode_is_on_by_default_for_the_poc() -> None:
    settings = AiAssistantSettings(_env_file=None)  # type: ignore[call-arg]
    assert settings.knowledge_single_reviewer is True


def test_the_ui_is_told_which_mode_applies(kb: KnowledgeBase) -> None:  # noqa: F811
    for mode in (True, False):
        me = client(kb, "director-session", single_reviewer=mode).get("/assistant/knowledge/me")
        assert me.json()["single_reviewer"] is mode


def test_the_author_publishes_their_own_fix_only_after_confirming(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    entry_id = drafted(kb, session="director-session")
    before = kb.store.get(entry_id, 1)
    unconfirmed = decide(kb, "director-session", entry_id, 1)
    assert unconfirmed.status_code == 403
    assert unconfirmed.json()["detail"] == {
        "code": "CONFIRM_SINGLE_REVIEWER",
        "message": CONFIRM_MESSAGE,
    }
    assert kb.store.get(entry_id, 1) == before and history(kb, entry_id) == []
    assert kb.store.feedback()[0]["status"] == "drafted"

    published = decide(kb, "director-session", entry_id, 1, confirm=True)
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "approved"
    assert published.json()["approver"] == published.json()["author"] == "director-dan"
    assert published.json()["single_reviewer"] is True
    assert history(kb, entry_id) == [("director-dan", "approve", True)]
    assert kb.store.feedback()[0]["status"] == "resolved"
    assert kb.index.keys(EntryKind.RESOLUTION) == {f"{entry_id}@v1"}
    # The Review window lists it as published by a single reviewer.
    director = client(kb, "director-session", single_reviewer=True)
    listed = director.get("/assistant/knowledge/entries?kind=resolution").json()
    assert [(e["entry_id"], e["single_reviewer"]) for e in listed] == [(entry_id, True)]
    full = director.get(f"/assistant/knowledge/entries/{entry_id}").json()
    assert [v["single_reviewer"] for v in full["versions"]] == [True]
    assert [r["single_reviewer"] for r in full["reviews"]] == [True]


def test_an_editor_may_publish_their_own_edit_in_single_reviewer_mode(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    entry_id = drafted(kb)  # written by director-drew
    assert (
        edit(kb, "director-session", entry_id, 1, title="Tidied by the Director").status_code == 200
    )
    published = decide(kb, "director-session", entry_id, 2, confirm=True)
    assert published.status_code == 200 and published.json()["single_reviewer"] is True
    assert history(kb, entry_id)[-1] == ("director-dan", "approve", True)


def test_a_second_reviewer_is_never_marked_single_reviewer(kb: KnowledgeBase) -> None:  # noqa: F811
    entry_id = drafted(kb)  # written by director-drew
    approved = decide(kb, "director-session", entry_id, 1, confirm=True)
    assert approved.status_code == 200 and approved.json()["single_reviewer"] is False
    assert history(kb, entry_id) == [("director-dan", "approve", False)]
    assert kb.store.single_reviewer_approvals() == set()


def test_an_author_may_reject_their_own_fix_and_the_request_opens_again(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    entry_id = drafted(kb, session="director-session")
    rejected = decide(kb, "director-session", entry_id, 1, approve=False)
    assert rejected.status_code == 200 and rejected.json()["status"] == "rejected"
    assert history(kb, entry_id) == [("director-dan", "reject", True)]
    assert kb.store.feedback()[0]["status"] == "open"
    assert kb.store.single_reviewer_approvals() == set()


def test_with_the_setting_off_the_two_person_rule_is_unchanged(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    entry_id = drafted(kb, session="director-session")
    for confirm in (False, True):
        refused = decide(
            kb, "director-session", entry_id, 1, confirm=confirm, single_reviewer=False
        )
        assert refused.status_code == 403 and refused.json()["detail"]["code"] == "MAKER_CHECKER"
    assert kb.store.get(entry_id, 1).status == EntryStatus.PENDING_REVIEW
    assert history(kb, entry_id) == []
    approved = decide(kb, "director-2-session", entry_id, 1, single_reviewer=False)
    assert approved.status_code == 200 and approved.json()["single_reviewer"] is False
    assert kb.store.feedback()[0]["status"] == "resolved"


def test_retiring_still_takes_two_reviewers_in_single_reviewer_mode(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    director = client(kb, "director-session", single_reviewer=True)
    retire = "/assistant/knowledge/entries/guidance.environments/retire"
    assert director.post(retire, json={"notes": "outdated"}).json()["retirement"] == "requested"
    again = director.post(retire, json={"notes": "outdated, really"})
    assert again.status_code == 403 and again.json()["detail"]["code"] == "SECOND_REVIEWER"
    assert kb.store.current("guidance.environments") is not None


def guidance_fix(**changes: Any) -> dict[str, Any]:
    return {
        "kind": "guidance",
        "title": "Ask for a tenancy agreement when the office moved",
        "body": "When the registered office moved, ask for the tenancy agreement first.",
        "source_ref": "docs/decisions/DECISION_LOG.md#D-030",
        **changes,
    }


def test_a_director_writes_a_new_guidance_entry_for_a_request(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    feedback_id = not_helpful(kb)
    director = client(kb, "director-session", single_reviewer=True)
    body = guidance_fix(body="When GARDEN BUSINESS moved, ask ops@client.example for the lease.")
    reply = director.post(f"/assistant/knowledge/feedback/{feedback_id}/draft", json=body)
    assert reply.status_code == 200, reply.text
    entry = reply.json()
    assert entry["kind"] == "guidance" and entry["status"] == "pending_review"
    assert entry["entry_id"] == "guidance.ask-for-a-tenancy-agreement-when-the-office-moved"
    assert entry["author"] == "director-dan" and entry["visibility"] == {"roles": [], "teams": []}
    assert "DOCUMENT_SOURCE_CONFLICT" in entry["blocker_codes"]  # from the request
    assert "GARDEN BUSINESS" not in entry["body"] and "ops@client.example" not in entry["body"]
    assert kb.store.feedback()[0]["entry_id"] == entry["entry_id"]
    published = decide(kb, "director-session", entry["entry_id"], 1, confirm=True)
    assert published.status_code == 200 and published.json()["single_reviewer"] is True
    assert kb.store.feedback()[0]["status"] == "resolved"


def test_a_director_writes_a_new_version_of_existing_guidance_for_a_request(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    current = kb.store.current("guidance.address-mismatch")
    assert current is not None
    feedback_id = not_helpful(kb)
    director = client(kb, "director-session", single_reviewer=True)
    reply = director.post(
        f"/assistant/knowledge/feedback/{feedback_id}/draft",
        json=guidance_fix(entry_id="guidance.address-mismatch"),
    )
    assert reply.status_code == 200, reply.text
    version = reply.json()["version"]
    assert version == current.version + 1
    # Visibility is the current version's unless the Director sets it.
    assert reply.json()["visibility"] == {
        "roles": list(current.visibility.roles),
        "teams": list(current.visibility.teams),
    }
    assert (
        decide(kb, "director-session", "guidance.address-mismatch", version, confirm=True).json()[
            "status"
        ]
        == "approved"
    )
    assert kb.store.current("guidance.address-mismatch").version == version
    assert kb.store.get("guidance.address-mismatch", current.version).status == EntryStatus.RETIRED
    assert kb.store.feedback()[0]["status"] == "resolved"


def test_a_fix_must_fit_its_kind(kb: KnowledgeBase) -> None:  # noqa: F811
    feedback_id = not_helpful(kb)
    director = client(kb, "director-session", single_reviewer=True)
    path = f"/assistant/knowledge/feedback/{feedback_id}/draft"
    for body in (
        {k: v for k, v in guidance_fix().items() if k != "source_ref"},
        guidance_fix(follow_ups=["Anything else?"]),
        {**fix(), "entry_id": "guidance.address-mismatch"},
        {**fix(), "source_ref": "somewhere"},
        {**fix(), "fields": ["registered address"]},
        {**fix(), "stages": ["documents"]},
        {**fix(), "kind": "note"},
        {**fix(), "body": "short"},
        {"kind": "resolution", "title": "No body"},
    ):
        assert director.post(path, json=body).status_code == 422, body
    assert kb.store.feedback()[0]["status"] == "open"
    assert kb.store.entries(status=EntryStatus.PENDING_REVIEW) == []
