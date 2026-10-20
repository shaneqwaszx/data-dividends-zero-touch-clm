"""Grounding and policy validation: code checks every model answer before the RM sees it.

Small local models do not always follow the prompt rules, so each sentence of an answer is
checked against the case facts (the same facts the backend gave the AI Assistant). A
sentence that fails a check is left out, and the RM is told how many were left out.

1. Grounding (factual claims)
   - a UEN, postal code, unit number, score or other specific value must appear in the facts;
   - "N of M steps" must match the case's real progress;
   - a button, screen or label named in quotes must exist in the facts;
   - a person or team to contact must be named in the facts;
   - a cited knowledge entry ([G1], [P2] ...) must be one that was actually retrieved.
2. Policy (action permissions)
   - an action the answer tells the RM to take (keep the registry value, use the document
     value, accept or reject a document suggestion, approve, submit ...) must be one this RM
     is allowed to take on this case. Saying an action is NOT available is fine.
3. Disclosures
   - never call a mock, local or sandbox system "live" or "production";
   - never present a value read from a document as confirmed when it differs from ACRA;
   - when the answer relies on registry data from a non-live registry, say so in a notice.

Clean-up (not a failure): internal field names (``who_resolves``) and generic example lists
("e.g., business licence") are removed, and numbered steps are renumbered.

Facts sent to the model are also stripped of empty values, so the model is not prompted to
fill gaps such as an empty ``who_resolves``.
"""

import json
import re
from dataclasses import dataclass
from typing import Any

_SNAKE = re.compile(r"\s*\(?`?\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b`?\)?")
# A label in double quotes, or in single quotes that are not apostrophes ("ACRA's", "it's").
_QUOTED = re.compile(
    r"[\"“”]([^\"“”\n]{2,60})[\"“”]|(?<![A-Za-z])['‘]([^'’\n]{2,60})['’](?![A-Za-z])"
)
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


# --- what the case allows -----------------------------------------------------------

# Actions the app can offer, and the wording a model uses for them. The labels are the ones
# the case page shows (backend api_models._INTERVENTION_ACTIONS and the review panel in
# BlockerDecisionReview.tsx). "Approve" and "submit to GoldTier" are never offered by the
# AI Assistant in Phase 1: final approval is a human gate outside the chat.
_NEVER_OFFERED = "(final approval or submission)"
_KEEP = r"(?:keep|keeps|kept|keeping)"
_USE = r"(?:use|uses|used|using)"
_REPLACE = r"(?:replace|replaces|replaced|override|overrides|overrode|overridden)"
_REQUEST = r"(?:request|requests|requested|requesting)"
_ACCEPT = r"(?:accept|accepts|accepted|accepting)"
_REJECT = r"(?:reject|rejects|rejected|rejecting)"
_RECORD = r"(?:record|records|recorded|recording)"
_APPROVE = r"(?:approve|approves|approved|approving)"
_SUBMIT = r"(?:submit|submits|submitted|submitting|send|sends|sent|sending)"
# Any tense counts: a past case described as "they used the document value" is still an
# action this case may not offer.
_ACTION_PHRASES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "keep registry value",
        re.compile(
            rf"\b{_KEEP} (?:the )?(?:registry|acra)(?:'s)?(?: value| address| record| name)?\b"
        ),
    ),
    (
        "use document value",
        re.compile(
            rf"\b{_USE} (?:the )?document(?:'s)? (?:value|address|name)\b"
            rf"|\buse document value\b|\b{_REPLACE} (?:the )?(?:acra|registry)(?:'s)?\b"
        ),
    ),
    (
        "request additional information",
        re.compile(rf"\b{_REQUEST} (?:additional|more) (?:information|evidence|documents?)\b"),
    ),
    (
        "accept document suggestion",
        re.compile(
            rf"\b{_ACCEPT} (?:the |all )?(?:eligible )?(?:undecided )?"
            r"(?:document(?:'s)? )?suggestions?\b"
        ),
    ),
    (
        "reject document suggestion",
        re.compile(
            rf"\b{_REJECT} (?:the |all )?(?:undecided )?document(?:'s)?"
            r"(?: suggestions?| values?)?\b"
        ),
    ),
    ("record correction", re.compile(rf"\b{_RECORD} (?:a )?correction\b")),
    (
        _NEVER_OFFERED,
        re.compile(
            rf"\b{_APPROVE} (?:the |this )?(?:case|onboarding|client|company)\b"
            rf"|\b{_SUBMIT} (?:it |the case |this case )?to goldtier\b"
        ),
    ),
)
_NEGATION = re.compile(r"\b(?:cannot|can't|can not|not|no|never|isn't|aren't|unavailable)\b")
# Parts of one sentence that can say opposite things ("you cannot X, but you can Y").
_CLAUSE = re.compile(r",?\s+but\s+|;\s*|,\s*however,?\s*|\s+whereas\s+|,\s*while\s+")


def allowed_actions(facts: dict[str, Any]) -> set[str]:
    """Lower-case labels of every action and screen this RM is offered on this case."""

    allowed: set[str] = set()
    for blocker in facts.get("blockers") or []:
        for action in blocker.get("actions_available_to_this_user") or []:
            if action.get("label"):
                allowed.add(str(action["label"]).lower())
        for screen in blocker.get("screens_to_open") or []:
            allowed.add(str(screen).lower())
    review = facts.get("document_field_review") or {}
    for row in review.get("fields") or []:
        for choice in row.get("choices") or []:
            allowed.add(str(choice).lower())
    return allowed


# --- one sentence --------------------------------------------------------------------

# Specific values a model could get wrong: UENs, postal codes, unit numbers, decimals, and
# any number of three or more digits. Short counts ("2 documents") are not checked here.
_VALUE = re.compile(r"#\d+(?:-\d+)+|\b\d+\.\d+\b|\b\d{3,}[A-Za-z]?\b")
_STEPS = re.compile(r"\b(\d+)\s*(?:of|out of|/)\s*(\d+)\s*(?:onboarding\s+)?steps?\b")
_LIVE = re.compile(
    r"\b(?:live|production|real)\s+(?:acra|registry|goldtier|system|environment|integration"
    r"|connection|api|data)\b|\b(?:acra|goldtier|registry|system)\b[^.]{0,30}\b(?:is|are) live\b"
)
_CONFIRMED = re.compile(r"\b(?:confirmed|verified|official|is correct|are correct)\b")


_CITATION = re.compile(r"\[([GP]\d+)\]")


class Context:
    """Everything the checks need, worked out once per answer."""

    def __init__(
        self,
        facts: dict[str, Any],
        *,
        knowledge_text: str = "",
        knowledge_tags: frozenset[str] = frozenset(),
    ) -> None:
        self.facts = facts
        # Values and labels may come from the case facts or from retrieved knowledge entries;
        # allowed actions still come only from the case facts (the backend).
        self.known = (
            json.dumps(facts, ensure_ascii=False, default=str) + "\n" + knowledge_text
        ).lower()
        self.knowledge_tags = knowledge_tags
        self.allowed = allowed_actions(facts)
        overall = facts.get("overall") or {}
        self.steps = (overall.get("steps_done"), overall.get("steps_total"))
        self.unconfirmed_document_values = {
            str(field.get("value_read_from_document")).lower()
            for document in facts.get("documents") or []
            for field in document.get("fields") or []
            if field.get("value_read_from_document")
            and field.get("compared_with_registry") in {"MISMATCH", "CONFLICT"}
        }


def _check(sentence: str, ctx: Context) -> str | None:
    """The reason this sentence must be left out, or None when it passes."""

    lowered = sentence.lower()
    # 1. Grounding
    for tag in _CITATION.findall(sentence):
        if tag not in ctx.knowledge_tags:
            return "invented_source"
    for phrase in _CONTACTS:
        if phrase in lowered and phrase not in ctx.known:
            return "invented_contact"
    for double, single in _QUOTED.findall(sentence):
        label = (double or single).strip().lower()
        if label and label not in ctx.known and not any(ch.isdigit() for ch in label):
            return "invented_label"
    for value in _VALUE.findall(lowered):
        if value not in ctx.known:
            return "unsupported_value"
    for done, total in _STEPS.findall(lowered):
        if (int(done), int(total)) != ctx.steps:
            return "wrong_step_count"
    clauses = _CLAUSE.split(lowered)
    # 2. Policy
    for clause in clauses:
        if _NEGATION.search(clause):
            continue
        for label, pattern in _ACTION_PHRASES:
            if pattern.search(clause) and label not in ctx.allowed:
                return "action_not_allowed"
    # 3. Disclosures
    if _LIVE.search(lowered) and "status" not in lowered:
        return "live_claim"
    for clause in clauses:
        if (
            _CONFIRMED.search(clause)
            and not _NEGATION.search(clause)
            and not re.search(r"\b(?:acra|registry)\b", clause)
            and any(value in clause for value in ctx.unconfirmed_document_values)
        ):
            return "document_value_as_fact"
    return None


def _tidy(sentence: str) -> str | None:
    cleaned = _EXAMPLES.sub("", _OR_SIMILAR.sub("", sentence))
    cleaned = _SNAKE.sub("", cleaned)
    cleaned = re.sub(r"\(\s*\)", "", cleaned)
    cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned if cleaned.strip(" -*•.") else None


# --- whole answer --------------------------------------------------------------------

REMOVED_NOTICE = "I left out {count} that I could not check against the case data."


@dataclass(frozen=True)
class Validation:
    text: str
    # Why each left-out sentence failed (reason codes only, never the sentence itself).
    removed: tuple[str, ...] = ()
    # Short notices the RM should see with the answer.
    disclosures: tuple[str, ...] = ()

    def notice(self) -> str | None:
        parts = list(self.disclosures)
        if self.removed:
            count = len(self.removed)
            noun = "1 statement" if count == 1 else f"{count} statements"
            parts.append(REMOVED_NOTICE.format(count=noun))
        return " ".join(parts) or None


def _disclosures(text: str, facts: dict[str, Any]) -> tuple[str, ...]:
    """A note when the answer relies on registry data from a registry that is not live."""

    lowered = text.lower()
    company = facts.get("company") or {}
    environment = re.search(
        r"\((MOCK|LOCAL|SANDBOX|PARTIAL|DORMANT)\)", str(company.get("source") or "")
    )
    if not environment or environment.group(1).lower() in lowered:
        return ()
    registry_values = [
        str(company[key]).lower()
        for key in ("uen", "registered_address", "registration_date")
        if company.get(key)
    ]
    if re.search(r"\bacra\b", lowered) or any(value in lowered for value in registry_values):
        return (
            f"Registry data in this case comes from ACRA ({environment.group(1)}), "
            "not the live ACRA service.",
        )
    return ()


def validate_answer(
    answer: str,
    facts: dict[str, Any],
    *,
    knowledge_text: str = "",
    knowledge_tags: frozenset[str] = frozenset(),
) -> Validation:
    """Check an answer sentence by sentence; keep only what passes."""

    ctx = Context(facts, knowledge_text=knowledge_text, knowledge_tags=knowledge_tags)
    removed: list[str] = []
    lines_out: list[str] = []
    for line in answer.splitlines():
        if not line.strip():
            lines_out.append("")
            continue
        prefix_match = re.match(r"^(\s*(?:[-*•]|\d+[.)])\s+)", line)
        prefix = prefix_match.group(1) if prefix_match else ""
        body = line[len(prefix) :]
        kept: list[str] = []
        for sentence in _SENTENCE.split(body):
            reason = _check(sentence, ctx)
            if reason is not None:
                removed.append(reason)
                continue
            tidy = _tidy(sentence)
            if tidy:
                kept.append(tidy)
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
    return Validation(text=text, removed=tuple(removed), disclosures=_disclosures(text, facts))


def guard_answer(answer: str, facts: dict[str, Any]) -> str:
    """The checked answer text only (see validate_answer for what was left out and why)."""

    return validate_answer(answer, facts).text


_SAFE_END = re.compile(r"(?:\n|[.!?](?=\s))")


class StreamingGuard:
    """Checks a streamed answer one finished sentence (or line) at a time.

    Only text up to the last finished sentence is checked and shown, so a sentence that the
    guardrails would drop is never displayed, not even briefly. Each update is the whole
    checked answer so far (not just the new part), because removing a sentence can renumber
    the list below it.
    """

    def __init__(
        self,
        facts: dict[str, Any],
        *,
        knowledge_text: str = "",
        knowledge_tags: frozenset[str] = frozenset(),
    ) -> None:
        self._facts = facts
        self._knowledge_text = knowledge_text
        self._knowledge_tags = knowledge_tags
        self._raw = ""
        self._shown = ""

    def feed(self, text: str) -> str | None:
        """Add new model text; return the checked answer so far if it changed."""

        self._raw += text
        ends = [match.end() for match in _SAFE_END.finditer(self._raw)]
        if not ends:
            return None
        checked = validate_answer(
            self._raw[: ends[-1]],
            self._facts,
            knowledge_text=self._knowledge_text,
            knowledge_tags=self._knowledge_tags,
        ).text
        if checked == self._shown:
            return None
        self._shown = checked
        return checked

    def finish(self) -> Validation:
        """The final check, including a last sentence without a full stop."""

        validation = validate_answer(
            self._raw,
            self._facts,
            knowledge_text=self._knowledge_text,
            knowledge_tags=self._knowledge_tags,
        )
        self._shown = validation.text
        return validation
