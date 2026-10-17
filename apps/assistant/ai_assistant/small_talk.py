"""Instant replies to greetings and small talk, without the AI model.

"hi" or "thanks" should not wait a minute for the model. Only a message made up entirely
of small talk is answered here. Anything with a real question in it ("hi, why is this
blocked?") still goes to the model as normal.
"""

import re
from typing import Any

from .briefing import progress_line

GREETINGS = {
    "hi",
    "hello",
    "hey",
    "hiya",
    "yo",
    "morning",
    "afternoon",
    "evening",
    "good morning",
    "good afternoon",
    "good evening",
    "hi there",
    "hello there",
    "hey there",
}
THANKS = {"thanks", "thank you", "thx", "ty", "cheers", "thanks a lot", "thank you so much"}
ACKS = {"ok", "okay", "k", "cool", "great", "nice", "got it", "alright", "noted", "sure"}
BYES = {"bye", "goodbye", "see you", "see ya", "later"}
ABOUT = {
    "who are you",
    "what are you",
    "what can you do",
    "help",
    "what do you do",
    "how can you help",
    "what can i ask",
    "what can i ask you",
}
FILLER = {"ai assistant", "assistant", "there", "again", "so", "much", "a lot", "lot", "please"}

ASK_EXAMPLES = 'For example: "Why is this case blocked?" or "What should I do next?"'


def _normalise(message: str) -> str:
    text = re.sub(r"[^a-z' ]+", " ", message.lower().replace("’", "'"))
    return " ".join(text.split())


def _strip(text: str, phrases: set[str]) -> str:
    """Remove known phrases from the start, repeatedly ("hi hello thanks")."""

    changed = True
    while text and changed:
        changed = False
        for phrase in sorted(phrases | FILLER, key=len, reverse=True):
            if text == phrase or text.startswith(phrase + " "):
                text = text[len(phrase) :].strip()
                changed = True
                break
    return text


def _status(facts: dict[str, Any]) -> str:
    company = facts["company"].get("legal_name") or "this case"
    count = len(facts["blockers"])
    if facts["overall"]["status"] == "completed":
        return f"Onboarding of {company} is complete."
    if count:
        noun = "issue" if count == 1 else "issues"
        return f"{company} has {count} {noun} to look at. {progress_line(facts)}"
    return f"{company} has no blockers right now. {progress_line(facts)}"


def small_talk_reply(message: str, facts: dict[str, Any]) -> str | None:
    """A reply when the whole message is small talk, otherwise None."""

    text = _normalise(message)
    if not text or len(text.split()) > 6:
        return None
    name = (facts.get("viewer") or {}).get("name")
    first = str(name).split()[0] if name else None
    hello = f"Hi {first}!" if first else "Hi!"

    if text in ABOUT:
        return (
            "I'm the AI Assistant. I explain where this case stands, why it is blocked "
            f"and what to do next, using the case data. {ASK_EXAMPLES}"
        )
    for group in (GREETINGS, THANKS, ACKS, BYES):
        if _strip(text, group) == "":
            if group is GREETINGS:
                return (
                    f"{hello} {_status(facts)}\n\nAsk me anything about this case. {ASK_EXAMPLES}"
                )
            if group is THANKS:
                return "You're welcome. Ask me if anything else on this case is unclear."
            if group is ACKS:
                return f"Okay. {ASK_EXAMPLES}"
            return "Bye for now. I'll be here when you open the AI Assistant again."
    if _strip(text, GREETINGS | THANKS | ACKS | BYES) == "":
        # Mixed small talk ("okay thanks", "thanks bye"): answer what it ends the
        # conversation with, not a fresh greeting.
        groups = _groups(text)
        if BYES in groups:
            return "Bye for now. I'll be here when you open the AI Assistant again."
        if THANKS in groups:
            return "You're welcome. Ask me if anything else on this case is unclear."
        if GREETINGS in groups:
            return f"{hello} {ASK_EXAMPLES}"
        return f"Okay. {ASK_EXAMPLES}"
    return None


def _groups(text: str) -> list[set[str]]:
    """Which small-talk groups appear in a message made only of small talk."""

    found: list[set[str]] = []
    phrases = sorted(GREETINGS | THANKS | ACKS | BYES | FILLER, key=len, reverse=True)
    while text:
        for phrase in phrases:
            if text == phrase or text.startswith(phrase + " "):
                for group in (GREETINGS, THANKS, ACKS, BYES):
                    if phrase in group and group not in found:
                        found.append(group)
                text = text[len(phrase) :].strip()
                break
        else:
            break
    return found
