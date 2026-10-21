"""Second independent gate on 79621fe: two-person retirement (G2), atomic status changes under
concurrency (M5), legacy in-place editors after migration (L7), role widening (I1) and
team-scoped stats (L8)."""

import sqlite3
import threading
import time
from collections.abc import Callable
from pathlib import Path

import pytest

from ai_assistant.knowledge.models import Entry, EntryKind, EntryStatus
from ai_assistant.knowledge.service import KnowledgeBase
from ai_assistant.knowledge.store import (
    ContentChangedError,
    KnowledgeError,
    KnowledgeRuleError,
    KnowledgeStore,
    MakerCheckerError,
)
from tests.test_knowledge_review import client, decide, edit, kb, solved  # noqa: F401

GUIDANCE = "guidance.address-mismatch"
RETIRE = f"/assistant/knowledge/entries/{GUIDANCE}/retire"


# --- G2: retiring official guidance takes two people ------------------------------------


def test_one_director_alone_cannot_retire_official_guidance(kb: KnowledgeBase) -> None:  # noqa: F811
    """The reviewer's probe: a TEAM_B Director retires org-wide guidance alone."""

    other = client(kb, "director-b-session")
    first = other.post(RETIRE, json={"notes": "not needed"})
    assert first.status_code == 200 and first.json()["retirement"] == "requested"
    assert kb.store.current(GUIDANCE) is not None
    again = other.post(RETIRE, json={"notes": "still not needed"})
    assert again.status_code == 403 and again.json()["detail"]["code"] == "SECOND_REVIEWER"
    assert kb.store.current(GUIDANCE) is not None
    assert [r["decision"] for r in kb.store.reviews(GUIDANCE)] == ["approve"]


def test_a_second_director_confirms_and_both_are_recorded(kb: KnowledgeBase) -> None:  # noqa: F811
    client(kb, "director-b-session").post(RETIRE, json={"notes": "rule withdrawn"})
    done = client(kb, "director-session").post(RETIRE, json={"notes": "confirmed"})
    assert done.status_code == 200 and done.json()["retirement"] == "done"
    assert kb.store.current(GUIDANCE) is None
    last = kb.store.reviews(GUIDANCE)[-1]
    assert (last["reviewer"], last["decision"]) == ("director-dan", "retire")
    assert "asked by director-bea" in last["notes"]
    assert kb.store.retirement_request(GUIDANCE) is None


def test_a_retirement_request_does_not_carry_over_to_a_new_version(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path / "k.sqlite3")
    entry = Entry(
        entry_id="guidance.rule",
        kind=EntryKind.GUIDANCE,
        title="Rule",
        body="A rule for the demo.",
        author="hr-hana",
    )
    v1 = store.add_version(entry)
    store.decide(v1.entry_id, 1, reviewer="director-dan", approve=True)
    store.request_retirement("guidance.rule", by="director-dan", notes="old")
    v2 = store.add_version(entry.with_changes(body="A newer rule for the demo."))
    store.decide(v2.entry_id, 2, reviewer="director-dee", approve=True)
    current, retired = store.request_retirement("guidance.rule", by="director-dee", notes="new")
    assert not retired and current.version == 2
    assert store.current("guidance.rule") is not None


def test_a_resolution_in_another_team_cannot_even_be_asked_to_retire(
    kb: KnowledgeBase,  # noqa: F811
) -> None:
    entry_id = solved(kb)
    decide(kb, "director-session", entry_id, 1)
    other = client(kb, "director-b-session").post(
        f"/assistant/knowledge/entries/{entry_id}/retire", json={"notes": "not mine"}
    )
    assert other.status_code == 404
    assert kb.store.retirement_request(entry_id) is None


# --- M5: status changes are atomic --------------------------------------------------------


def _race(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *calls: Callable[[KnowledgeStore, str], object]
) -> tuple[list[str], KnowledgeStore]:
    """Run ``calls`` concurrently, each pausing inside its transaction after the checks
    (the reviewer's probe_race fault injection), and report each outcome."""

    path = tmp_path / "race.sqlite3"
    store = KnowledgeStore(path)
    entry = store.add_version(
        Entry(
            entry_id="resolution.r",
            kind=EntryKind.RESOLUTION,
            title="T",
            body="Body text here.",
            author="maya-lim",
        )
    )
    real = KnowledgeStore._check_replaces

    def slow(self: KnowledgeStore, db: sqlite3.Connection, item: Entry) -> None:
        time.sleep(0.4)
        real(self, db, item)

    monkeypatch.setattr(KnowledgeStore, "_check_replaces", slow)
    outcomes: list[str] = []

    def run(call: Callable[[KnowledgeStore, str], object]) -> None:
        try:
            call(KnowledgeStore(path), entry.content_hash())
            outcomes.append("ok")
        except KnowledgeError as exc:
            outcomes.append(type(exc).__name__)
        except Exception as exc:  # noqa: BLE001 - any other error is the failure under test
            outcomes.append(f"CRASH {type(exc).__name__}")

    threads = [threading.Thread(target=run, args=(call,)) for call in calls]
    for thread in threads:
        thread.start()
        time.sleep(0.05)
    for thread in threads:
        thread.join(timeout=30)
    monkeypatch.setattr(KnowledgeStore, "_check_replaces", real)
    return outcomes, KnowledgeStore(path)


def _approve(reviewer: str) -> Callable[[KnowledgeStore, str], object]:
    return lambda store, h: store.decide(
        "resolution.r", 1, reviewer=reviewer, approve=True, expected_hash=h
    )


def _reject(reviewer: str) -> Callable[[KnowledgeStore, str], object]:
    return lambda store, h: store.decide(
        "resolution.r", 1, reviewer=reviewer, approve=False, expected_hash=h
    )


def _edit(editor: str, body: str) -> Callable[[KnowledgeStore, str], object]:
    return lambda store, h: store.revise_pending(
        "resolution.r", 1, editor=editor, expected_hash=h, body=body
    )


@pytest.mark.parametrize(
    "calls",
    [
        (_approve("director-dee"), _reject("director-dov")),
        (_approve("director-dee"), _approve("director-dov")),
        (_edit("director-dan", "Edited body text."), _approve("director-dee")),
        (_edit("director-dan", "Edited body one."), _edit("director-dee", "Edited body two.")),
    ],
    ids=["approve-vs-reject", "approve-vs-approve", "edit-vs-approve", "edit-vs-edit"],
)
def test_concurrent_decisions_and_edits_have_exactly_one_winner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, calls: tuple[Callable[..., object], ...]
) -> None:
    outcomes, store = _race(tmp_path, monkeypatch, *calls)
    assert len(outcomes) == 2 and outcomes.count("ok") == 1
    assert not any(o.startswith("CRASH") for o in outcomes)
    loser = next(o for o in outcomes if o != "ok")
    assert loser in {"KnowledgeError", "ContentChangedError"}
    v1 = store.get("resolution.r", 1)
    decisions = [r["decision"] for r in store.reviews("resolution.r") if r["version"] == 1]
    # One outcome only: never both approve and reject, never two approvals.
    assert len([d for d in decisions if d in ("approve", "reject")]) <= 1
    if v1.status == EntryStatus.RETIRED:
        assert decisions == ["edit"] and store.get("resolution.r", 2) is not None
    else:
        assert v1.status in (EntryStatus.APPROVED, EntryStatus.REJECTED)
        assert store.get("resolution.r", 2) is None


def test_a_concurrent_edit_is_a_clean_409_through_the_api(
    kb: KnowledgeBase,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entry_id = solved(kb)

    def conflict(*args: object, **kwargs: object) -> None:
        raise ContentChangedError("a concurrent change came first")

    monkeypatch.setattr(kb.store, "revise_pending", conflict)
    reply = edit(kb, "director-session", entry_id, 1, title="Edited at the same time")
    assert reply.status_code == 409 and reply.json()["detail"]["code"] == "CHANGED"


def test_an_integrity_error_inside_a_write_becomes_a_stale_request(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path / "k.sqlite3")
    with pytest.raises(ContentChangedError), store._write() as db:
        db.execute(
            "INSERT INTO meta (key, value) VALUES ('schema_version', '3')"
        )  # duplicate primary key
    assert store.entries() == []


# --- L7: an editor from before schema v3 stays barred -----------------------------------


def test_a_v2_in_place_editor_cannot_decide_after_migration(tmp_path: Path) -> None:
    path = tmp_path / "k.sqlite3"
    store = KnowledgeStore(path)
    draft = store.add_version(
        Entry(
            entry_id="resolution.old",
            kind=EntryKind.RESOLUTION,
            title="Old",
            body="Old draft body.",
            author="maya-lim",
        )
    )
    # What a v2 store held after an in-place edit: the same pending version, an 'edit' row.
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO reviews (entry_id, version, reviewer, decision, notes, created_at) "
            "VALUES ('resolution.old', 1, 'director-dan', 'edit', 'body', '2026-10-01')"
        )
    with pytest.raises(MakerCheckerError):
        store.decide(
            "resolution.old",
            1,
            reviewer="director-dan",
            approve=True,
            expected_hash=draft.content_hash(),
        )
    approved = store.decide(
        "resolution.old",
        1,
        reviewer="director-dee",
        approve=True,
        expected_hash=draft.content_hash(),
    )
    assert approved.status == EntryStatus.APPROVED


# --- I1 and L8 ----------------------------------------------------------------------------


def test_an_edit_cannot_widen_role_visibility(tmp_path: Path) -> None:
    from ai_assistant.knowledge.models import Visibility

    store = KnowledgeStore(tmp_path / "k.sqlite3")
    store.add_version(
        Entry(
            entry_id="resolution.r",
            kind=EntryKind.RESOLUTION,
            title="T",
            body="Body text.",
            author="maya-lim",
            visibility=Visibility(roles=("CLIENT_ONBOARDER",)),
        )
    )
    with pytest.raises(KnowledgeRuleError):
        store.revise_pending("resolution.r", 1, editor="director-dan", visibility=Visibility())


def test_stats_count_only_the_callers_team(kb: KnowledgeBase) -> None:  # noqa: F811
    solved(kb)
    own = client(kb, "director-session").get("/assistant/knowledge/stats").json()
    other = client(kb, "director-b-session").get("/assistant/knowledge/stats").json()
    assert own["entries"].get("resolution_pending_review") == 1
    assert "resolution_pending_review" not in other["entries"]
    assert other["feedback"]["total"] == 0
    # Organisation-wide guidance counts for every team.
    assert own["entries"]["guidance_approved"] == other["entries"]["guidance_approved"]
