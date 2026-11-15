"""D-130 OD-G8: no user identifier in what is sent to Anthropic.

The signed-in user's identity stays with the service (the backend session, RBAC, team scope,
conversation ownership and the answer records are unchanged). What a Claude-bound prompt may
say about a user is their role only. The identifiers removed are the caller's user id and
display name and, on "Try with this change", the conversation owner's user id. A backend user
id is the display name in lower case with hyphens ("maya-lim" for "Maya Lim"), and the match
ignores letter case and the separator, so the owner's display name is removed too
(test_hosted_claude_payloads checks the backend's profiles keep that form).

Only data is changed, never the service's own text:

- ``provider_facts``: the case facts, with the viewer reduced to ``{"role": ...}`` and every
  identifier removed from their text (a backend timeline line can name a user);
- ``scrub``: the user and assistant turns (the question and the chat history, which the user
  or the browser wrote); system messages are left as built, because they hold the fixed
  instructions, the allowed lines and approved knowledge, built from ``provider_facts``;
- ``scrub_text``: one piece of user-written text that goes into a system message (Support's
  unsaved rule on "Try").

Deterministic matching cannot remove arbitrary personal information a person types (a first
name alone, someone else's name): synthetic-only input stays mandatory (D-129).

Used only for models that send to Anthropic (``anthropic_bound``) and, D-134 (proposed), for
GPT-OSS on its registered hosted deployment (``provider_bound``); every other model's prompt is
unchanged.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

REPLACEMENT = "the user"
# Shorter values are not distinctive enough to remove from free text without harming it.
MIN_IDENTIFIER_CHARS = 3
# The turns a person or the browser wrote. System messages are the service's own text.
WRITTEN_ROLES = frozenset({"user", "assistant"})


def anthropic_bound(model: object) -> bool:
    return getattr(model, "anthropic_bound", False) is True


def provider_bound(model: object) -> bool:
    # A model whose prompt leaves for a hosted provider: Claude, or hosted GPT-OSS (D-134).
    return anthropic_bound(model) or getattr(model, "provider_bound", False) is True


def identities(*profiles: Mapping[str, Any] | None, extra: Iterable[Any] = ()) -> tuple[str, ...]:
    """The identifiers to keep out of a Claude-bound prompt, longest first."""

    found: set[str] = set()
    for profile in profiles:
        for key in ("user_id", "display_name"):
            value = (profile or {}).get(key)
            if isinstance(value, str) and len(value.strip()) >= MIN_IDENTIFIER_CHARS:
                found.add(value.strip())
    for value in extra:
        if isinstance(value, str) and len(value.strip()) >= MIN_IDENTIFIER_CHARS:
            found.add(value.strip())
    return tuple(sorted(found, key=lambda item: (-len(item), item)))


def _pattern(names: tuple[str, ...]) -> re.Pattern[str] | None:
    parts = []
    for name in names:
        # "maya-lim" also matches "Maya Lim", "maya_lim" and "MAYA.LIM".
        words = [re.escape(word) for word in re.split(r"[\s_.-]+", name) if word]
        if words:
            parts.append(r"[\s_.-]+".join(words))
    if not parts:
        return None
    return re.compile(r"(?<![A-Za-z0-9])(?:" + "|".join(parts) + r")(?![A-Za-z0-9])", re.I)


def scrub_text(text: str, names: tuple[str, ...]) -> str:
    pattern = _pattern(names)
    return text if pattern is None else pattern.sub(REPLACEMENT, text)


def provider_facts(facts: dict[str, Any], names: tuple[str, ...] = ()) -> dict[str, Any]:
    pattern = _pattern(names)

    def clean(value: Any) -> Any:
        if isinstance(value, str):
            return value if pattern is None else pattern.sub(REPLACEMENT, value)
        if isinstance(value, dict):
            return {key: clean(item) for key, item in value.items()}
        if isinstance(value, list):
            return [clean(item) for item in value]
        return value

    cleaned = {key: clean(value) for key, value in facts.items() if key != "viewer"}
    viewer = facts.get("viewer")
    if isinstance(viewer, dict):
        cleaned["viewer"] = {"role": viewer.get("role")}
    elif "viewer" in facts:
        cleaned["viewer"] = viewer
    return {key: cleaned[key] for key in facts}


def scrub(messages: list[dict[str, str]], names: tuple[str, ...]) -> list[dict[str, str]]:
    pattern = _pattern(names)
    return [
        {**message, "content": pattern.sub(REPLACEMENT, str(message.get("content", "")))}
        if pattern is not None and message.get("role") in WRITTEN_ROLES
        else dict(message)
        for message in messages
    ]
