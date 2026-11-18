"""D-142 R1, acceptance group X7 (its own module: it needs the Support-capable hosted backend
fixture of test_hosted_claude_paths). See test_privacy_r1.py for the other groups."""

from __future__ import annotations

from tests.test_conversational_external import scripted  # noqa: F401 (fixture)
from tests.test_hosted_claude import (
    Hosted,
    hosted_replies,  # noqa: F401 (fixture)
)
from tests.test_hosted_claude_paths import hosted, live  # noqa: F401 (fixtures)
from tests.test_hosted_privacy import leaked, sent_since


def test_x7_a_stored_title_reused_by_try_does_not_leak(live: Hosted) -> None:  # noqa: F811
    # Try with this change asks the conversation's stored title when no question is given. A
    # title holding a name and an identifier (as an RM may have typed it) never leaves.
    from tests.test_hosted_claude_paths import ended_conversation, hosted_knowledge, try_change

    site = live
    conversation = ended_conversation(site)
    title = "Priyanka Ramasamy (S1234567D) asks what is blocking this case right now?"
    with hosted_knowledge(site).store._write() as db:
        db.execute("UPDATE conversations SET title = ? WHERE id = ?", (title, conversation))
    before = len(site.claude.messages)
    reply = try_change(site, conversation, question=None)
    assert reply.status_code == 200, reply.text
    assert reply.json()["question"] == title
    assert leaked(sent_since(site, before), ["Priyanka", "Ramasamy", "S1234567D"]) == []
