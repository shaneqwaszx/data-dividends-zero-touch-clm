"""Exact output policy over current backend actions and reviewed explanations.

Generated prose is untrusted, including paraphrases. Only whole catalog lines may
be displayed. Document/company values, history and model output never extend the
catalog. The deterministic case-data answer handles unsupported responses.
This is bounded statement selection, not general semantic verification.
"""

from typing import Any

from .guide import CASE_PAGE_SECTIONS, DOCUMENT_REVIEW_CHOICES, READINESS_NEEDS, RULE_PLAIN
from .llm import LlmUnavailableError


def compact_facts(value: Any) -> Any:
    """Drop None, empty strings, lists and dicts so the model sees only real facts."""

    if isinstance(value, dict):
        out = {k: compact_facts(v) for k, v in value.items()}
        return {k: v for k, v in out.items() if v not in (None, "", [], {})}
    if isinstance(value, list):
        out_list = [compact_facts(v) for v in value]
        return [v for v in out_list if v not in (None, "", [], {})]
    return value


def allowed_guidance(facts: dict[str, Any]) -> list[str]:
    """Build advice only from trusted templates and this request's backend projection."""

    allowed = [
        "Ownership and UBO analysis is provisional; it does not establish legal verification.",
        "Mock, Local and Sandbox evidence do not establish Live integration or KYC approval.",
        "Successful mock submission does not establish GoldTier-internal "
        "or regulatory/KYC approval.",
        "Registry and document differences require the current case decision; neither source "
        "automatically overrides the other.",
        "For uncertain or frozen GoldTier submissions, use only the recovery actions currently "
        "offered by the case; do not resend.",
        "The seven case page stages are distinct from the backend processing steps.",
    ]
    for need in facts.get("still_needed_before_goldtier") or []:
        for what, where in READINESS_NEEDS.values():
            if need.get("what") == what and need.get("where_on_the_case_page") == where:
                allowed.append(f"{what} (section: {where})")
    for blocker in facts.get("blockers") or []:
        explanation = blocker.get("plain_explanation")
        if explanation in RULE_PLAIN.values():
            allowed.append(explanation)
        # Labels originate only in authorized_actions, never document evidence.
        for action in blocker.get("actions_available_to_this_user") or []:
            label = action.get("label")
            if isinstance(label, str) and label and not any(c in label for c in "\n\r"):
                allowed.append(f'The current case offers "{label}".')
        if blocker.get("why_no_action"):
            allowed.append("No action is currently available to you for this blocker.")
    review = facts.get("document_field_review") or {}
    for field in review.get("fields") or []:
        for choice in field.get("choices") or []:
            if choice in DOCUMENT_REVIEW_CHOICES:
                allowed.append(
                    f'Document verification offers "{choice}" to review the extracted field; '
                    "this does not decide registry/document precedence."
                )
    for section in CASE_PAGE_SECTIONS:
        allowed.append(f'Open the "{section}" section to inspect the current case evidence.')
    return list(dict.fromkeys(allowed))


def guard_answer(answer: str, facts: dict[str, Any]) -> str:
    """Select exact approved lines; unknown wording cannot become operational advice."""

    allowed = set(allowed_guidance(facts))
    return "\n".join(
        dict.fromkeys(line.strip() for line in answer.splitlines() if line.strip() in allowed)
    )


MAX_MODEL_TEXT_BYTES = 64 * 1024


class StreamingGuard:
    """Select new complete catalog lines once; bound even newline-free model output."""

    def __init__(self, facts: dict[str, Any]) -> None:
        self._allowed = set(allowed_guidance(facts))
        self._raw = ""
        self._accepted: dict[str, None] = {}
        self._shown = ""
        self._total_bytes = 0

    def _accept(self, text: str) -> None:
        for line in text.splitlines():
            line = line.strip()
            if line in self._allowed:
                self._accepted[line] = None
        self._shown = "\n".join(self._accepted)

    def feed(self, text: str) -> str | None:
        if self._total_bytes + len(text) > MAX_MODEL_TEXT_BYTES:
            raise LlmUnavailableError("model text limit exceeded")
        try:
            size = len(text.encode("utf-8"))
        except UnicodeError:
            raise LlmUnavailableError("unreadable model reply") from None
        if self._total_bytes + size > MAX_MODEL_TEXT_BYTES:
            raise LlmUnavailableError("model text limit exceeded")
        self._total_bytes += size
        self._raw += text
        boundary = self._raw.rfind("\n")
        if boundary < 0:
            return None
        previous = self._shown
        self._accept(self._raw[:boundary])
        self._raw = self._raw[boundary + 1 :]
        return self._shown if self._shown != previous else None

    def finish(self) -> str:
        self._accept(self._raw)
        self._raw = ""
        return self._shown
