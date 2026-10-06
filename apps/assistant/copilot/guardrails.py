"""Code-level safety net for model answers.

Small local models do not always follow the prompt rules, so answers are checked
against the case facts before they reach the RM:

- internal field names (snake_case keys such as ``who_resolves``) are removed;
- a sentence that names a button, screen or label in quotes that does not exist in
  the case facts is dropped (the model must not invent UI);
- a sentence that sends the RM to a person or team the facts never mention
  ("contact the support team") is dropped;
- generic example lists in brackets ("e.g., business licence") are removed, and
  numbered steps are renumbered after any removal.

Facts sent to the model are also stripped of empty values, so the model is not
prompted to fill gaps such as an empty ``who_resolves``.
"""

import json
import re
from typing import Any

_SNAKE = re.compile(r"\s*\(?`?\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b`?\)?")
_QUOTED = re.compile(r"[\"“”']([^\"“”'\n]{2,60})[\"“”']")
_OR_SIMILAR = re.compile(r"\s*\((?:or similar|if available[^)]*)\)", re.IGNORECASE)
# Generic example lists the model adds from its own knowledge, e.g. "(e.g., business licence)".
_EXAMPLES = re.compile(r"\s*\((?:e\.g\.|eg\.|for example|such as|like)[^)]*\)", re.IGNORECASE)
_CONTACTS = (
    "support team",
    "help desk",
    "helpdesk",
    "it team",
    "compliance team",
    "your manager",
    "your supervisor",
    "case owner",
    "administrator",
    "contact support",
)
_SENTENCE = re.compile(r"(?<=[.!?])\s+")


def compact_facts(value: Any) -> Any:
    """Drop None, empty strings, lists and dicts so the model sees only real facts."""

    if isinstance(value, dict):
        out = {k: compact_facts(v) for k, v in value.items()}
        return {k: v for k, v in out.items() if v not in (None, "", [], {})}
    if isinstance(value, list):
        out_list = [compact_facts(v) for v in value]
        return [v for v in out_list if v not in (None, "", [], {})]
    return value


def _clean_sentence(sentence: str, known: str) -> str | None:
    lowered = sentence.lower()
    for phrase in _CONTACTS:
        if phrase in lowered and phrase not in known:
            return None
    for quoted in _QUOTED.findall(sentence):
        label = quoted.strip().lower()
        if label and label not in known and not any(ch.isdigit() for ch in label):
            return None
    cleaned = _EXAMPLES.sub("", _OR_SIMILAR.sub("", sentence))
    cleaned = _SNAKE.sub("", cleaned)
    cleaned = re.sub(r"\(\s*\)", "", cleaned)
    cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned if cleaned.strip(" -*•.") else None


def guard_answer(answer: str, facts: dict[str, Any]) -> str:
    """Remove internal names, invented UI labels and invented contacts from an answer."""

    known = json.dumps(facts, ensure_ascii=False, default=str).lower()
    lines_out: list[str] = []
    for line in answer.splitlines():
        if not line.strip():
            lines_out.append("")
            continue
        prefix_match = re.match(r"^(\s*(?:[-*•]|\d+[.)])\s+)", line)
        prefix = prefix_match.group(1) if prefix_match else ""
        body = line[len(prefix) :]
        kept = [s for s in (_clean_sentence(p, known) for p in _SENTENCE.split(body)) if s]
        if kept:
            lines_out.append(prefix + " ".join(kept))
    # Renumber ordered lists so dropped steps leave no gaps.
    number = 0
    for i, line in enumerate(lines_out):
        m = re.match(r"^(\s*)\d+([.)])\s+(.*)$", line)
        if m:
            number += 1
            lines_out[i] = f"{m.group(1)}{number}{m.group(2)} {m.group(3)}"
        elif line.strip():
            number = 0
    text = "\n".join(lines_out)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    # Drop a heading left with nothing under it (e.g. "Next steps:" at the end).
    text = re.sub(r"(?:\n|^)\s*\**[A-Za-z ]{2,30}:\**\s*$", "", text).strip()
    return text
