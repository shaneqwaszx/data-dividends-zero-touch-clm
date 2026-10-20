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

from .llm import LlmUnavailableError

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
_APPROVE = r"(?:approv(?:e|es|ed|ing)|authori[sz](?:e|es|ed|ing))"
_SUBMIT = r"(?:submit|submits|submitted|submitting|send|sends|sent|sending)"
_RESEND = r"(?:resend|resends|resending|resubmit|resubmits|resubmitting|re-send|re-submit)"
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
            # Uncertain or frozen GoldTier submissions are never resent from the chat.
            rf"|\b{_RESEND}\b"
        ),
    ),
)
_NEGATION = re.compile(
    r"\b(?:cannot|can't|can not|not|no|never|neither|nor|isn't|aren't|doesn't|unavailable)\b"
)
# Parts of one sentence that can say opposite things ("you cannot X, but you can Y").
_CLAUSE = re.compile(r",?\s+but\s+|;\s*|,\s*however,?\s*|\s+whereas\s+|,\s*while\s+")

# A negation only cancels the action or claim it is attached to. It must come shortly before
# the phrase, in the same part of the clause ("You cannot approve the case"), or say right
# after it that the action is not available ("Keep registry value is not available here").
# "Do not wait, approve the case" and "No need to wait: approve the case" still tell the RM
# to approve: the negation belongs to a different phrase.
_NEGATION_WINDOW_WORDS = 6
_PHRASE_BREAK = re.compile(r"[,:;()–—]|\s-\s")
# Wording that contains a negation word but affirms ("no doubt", "do not hesitate to").
_AFFIRMING_NEGATION = re.compile(
    r"\b(?:no|without|beyond) (?:doubt|question)\b|\bnot in (?:doubt|question)\b"
    r"|\bno need to\b|\bno reason not to\b|\b(?:do not|don't) hesitate to\b"
    r"|\bnothing (?:stops|prevents) you\b|\bthere is nothing to stop\b"
)
_UNAVAILABLE_AFTER = re.compile(
    r"^[^.]{0,40}?\b(?:is|are|was|were)(?: not|n't) (?:available|offered|allowed|possible)\b"
    r"|^[^.]{0,40}?\b(?:unavailable|cannot be (?:used|chosen|done))\b"
)


def _negated(clause: str, start: int, end: int) -> bool:
    """True when a negation in ``clause`` applies to the phrase at ``start:end``."""

    before = _PHRASE_BREAK.split(clause[:start])[-1]
    before = _AFFIRMING_NEGATION.sub(" ", before)
    words = before.split()[-_NEGATION_WINDOW_WORDS:]
    # "no reason not to resend" or "never not approve" cancel out: an odd count negates.
    if len(_NEGATION.findall(" ".join(words))) % 2 == 1:
        return True
    after = _PHRASE_BREAK.split(clause[end:])[0]
    return bool(_UNAVAILABLE_AFTER.search(after))


def _asserted(pattern: re.Pattern[str], clause: str) -> bool:
    """True when ``pattern`` occurs in ``clause`` without a negation attached to it."""

    return any(not _negated(clause, m.start(), m.end()) for m in pattern.finditer(clause))


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
    r"|\b(?:case|client|company|it|this)\b[^.]{0,20}\b(?:is|are) live\b"
)
# Claims only people or other systems can make: legal UBO verification, KYC or regulatory
# approval, official verification, or one source automatically winning over the other.
_AUTHORITY = re.compile(
    r"\blegally (?:verified|confirmed|established)\b"
    r"|\b(?:ubos?|beneficial owners?|ownership)\b[^.]{0,30}\b(?:are|is) (?:verified|confirmed)\b"
    r"|\b(?:kyc|regulatory|compliance)(?:/kyc)? (?:approval|approved|clearance|cleared)\b"
    r"|\bofficially (?:verified|approved|confirmed)\b"
    r"|\b(?:always|automatically) (?:overrides?|wins?|takes? precedence|replaces?)\b"
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
    # 2. Policy. A negation elsewhere in the clause does not cancel an action or claim; only
    # one attached to the phrase does (see _negated).
    for clause in clauses:
        for label, pattern in _ACTION_PHRASES:
            if label not in ctx.allowed and _asserted(pattern, clause):
                return "action_not_allowed"
    for clause in clauses:
        if _asserted(_AUTHORITY, clause):
            return "authority_claim"
    # 3. Disclosures
    if _LIVE.search(lowered) and "status" not in lowered:
        return "live_claim"
    for clause in clauses:
        if (
            _asserted(_CONFIRMED, clause)
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


_SECTION_REF = re.compile(r"\s*\(section:\s*([^)\n]{1,80})\)", re.IGNORECASE)


def _fix_section_names(answer: str, facts: dict[str, Any]) -> str:
    """Keep "(section: X)" only when X is a real case page section.

    A wrong one (a blocker title, a backend stage name) is dropped rather than shown, so
    the RM is never sent to a section that does not exist. Formatting around the name
    ("*Ownership & UBO*") is removed so the panel can link it.
    """

    sections = {str(name).lower(): str(name) for name in facts.get("case_page_sections") or []}

    def repair(match: re.Match[str]) -> str:
        name = match.group(1).strip().strip("*_`\"' ").strip()
        real = sections.get(name.lower())
        return f" (section: {real})" if real else ""

    return _SECTION_REF.sub(repair, answer)


_LIST_PREFIX = re.compile(r"^(\s*(?:[-*•]|\d+[.)])\s+)")
# The start of a line that may still become a list marker when more text arrives.
_MAYBE_LIST_PREFIX = re.compile(r"^\s*(?:[-*•]|\d+[.)]?)?\s*$")
_NUMBERED = re.compile(r"^(\s*)\d+([.)])\s+")
# Only a new heading ("Next steps:") starts a new list; an explanation under a step,
# indented or not, keeps the count going (1, 2 rather than 1, 1).
_HEADING = re.compile(r"^\s*(?:#|\**[^\s].{0,60}:\**\s*$)")
_TRAILING_HEADING = re.compile(r"^\s*\**[A-Za-z ]{2,30}:\**\s*$")


class _Answer:
    """Builds the checked answer line by line. Each sentence is checked exactly once, so
    checking a streamed answer costs the same as checking the finished one."""

    def __init__(
        self,
        facts: dict[str, Any],
        *,
        knowledge_text: str = "",
        knowledge_tags: frozenset[str] = frozenset(),
    ) -> None:
        self._facts = facts
        self._ctx = Context(facts, knowledge_text=knowledge_text, knowledge_tags=knowledge_tags)
        self._lines: list[str] = []  # finished output lines, already numbered
        self._number = 0
        self._removed: list[str] = []
        self._prefix = ""  # the current line's list marker
        self._current = ""  # the current line's kept sentences
        self.changes = 0  # bumped whenever the answer may read differently

    def blank_line(self) -> None:
        # Runs of blank lines become one, and the answer never starts with one.
        if self._lines and self._lines[-1] != "":
            self._lines.append("")
            self.changes += 1

    def start_line(self, prefix: str) -> None:
        self._prefix = prefix
        self._current = ""

    def sentence(self, sentence: str, *, first: bool) -> None:
        sentence = _fix_section_names(sentence, self._facts)
        if not first:
            sentence = sentence.lstrip()
        reason = _check(sentence, self._ctx)
        if reason is not None:
            self._removed.append(reason)
            return
        tidy = _tidy(sentence)
        if tidy:
            self._current = f"{self._current} {tidy}" if self._current else tidy
            self.changes += 1

    def _numbered(self, line: str, number: int) -> str | None:
        match = _NUMBERED.match(line)
        if not match:
            return None
        return f"{match.group(1)}{number}{match.group(2)} {line[match.end() :]}"

    def end_line(self) -> None:
        if self._current:
            line = self._prefix + self._current
            numbered = self._numbered(line, self._number + 1)
            if numbered is not None:
                self._number += 1
                line = numbered
            elif _HEADING.match(line):
                self._number = 0
            self._lines.append(line)
            self.changes += 1
        self._prefix = ""
        self._current = ""

    def text(self) -> str:
        lines = self._lines
        if self._current:
            line = self._prefix + self._current
            lines = [*lines, self._numbered(line, self._number + 1) or line]
        text = "\n".join(lines).strip()
        head, _, last = text.rpartition("\n")
        # Drop a heading left with nothing under it (e.g. "Next steps:" at the end).
        if _TRAILING_HEADING.match(last):
            text = head.strip()
        return text

    def validation(self) -> Validation:
        text = self.text()
        return Validation(
            text=text, removed=tuple(self._removed), disclosures=_disclosures(text, self._facts)
        )


def _add_line(answer: _Answer, line: str) -> None:
    if not line.strip():
        answer.blank_line()
        return
    match = _LIST_PREFIX.match(line)
    prefix = match.group(1) if match else ""
    answer.start_line(prefix)
    for index, sentence in enumerate(_SENTENCE.split(line[len(prefix) :])):
        answer.sentence(sentence, first=index == 0)
    answer.end_line()


def validate_answer(
    answer: str,
    facts: dict[str, Any],
    *,
    knowledge_text: str = "",
    knowledge_tags: frozenset[str] = frozenset(),
) -> Validation:
    """Check an answer sentence by sentence; keep only what passes."""

    built = _Answer(facts, knowledge_text=knowledge_text, knowledge_tags=knowledge_tags)
    for line in answer.replace("\r", "").split("\n"):
        _add_line(built, line)
    return built.validation()


def guard_answer(answer: str, facts: dict[str, Any]) -> str:
    """The checked answer text only (see validate_answer for what was left out and why)."""

    return validate_answer(answer, facts).text


# A runaway or hostile stream cannot grow without bound (also when it never ends a sentence).
MAX_MODEL_TEXT_BYTES = 64 * 1024


class StreamingGuard:
    """Checks a streamed answer one finished sentence (or line) at a time.

    Only finished sentences are checked and shown, so a sentence that the guardrails would
    drop is never displayed, not even briefly. Checking is incremental: a finished sentence
    is checked once and never parsed again, so the cost grows with the answer's length, not
    with its square. Each update is the whole checked answer so far (not just the new part),
    because removing a sentence can renumber the list below it.
    """

    def __init__(
        self,
        facts: dict[str, Any],
        *,
        knowledge_text: str = "",
        knowledge_tags: frozenset[str] = frozenset(),
    ) -> None:
        self._answer = _Answer(facts, knowledge_text=knowledge_text, knowledge_tags=knowledge_tags)
        self._total_bytes = 0
        self._line = ""  # unchecked text of the current line (all of it until it starts)
        self._started = False  # the current line's list marker is known
        self._first = True  # the next sentence is the first of its line
        self._scanned = 0  # how much of self._line was already searched for a sentence end
        self._shown = ""

    @property
    def _raw(self) -> str:
        """Model text held but not yet checked (bounded by MAX_MODEL_TEXT_BYTES)."""

        return self._line

    def feed(self, text: str) -> str | None:
        """Add new model text; return the checked answer so far if it changed."""

        try:
            size = len(text.encode("utf-8"))
        except UnicodeError:
            raise LlmUnavailableError("unreadable model reply") from None
        if self._total_bytes + size > MAX_MODEL_TEXT_BYTES:
            raise LlmUnavailableError("model text limit exceeded")
        self._total_bytes += size
        before = self._answer.changes
        parts = text.replace("\r", "").split("\n")
        for index, part in enumerate(parts):
            self._line += part
            if index < len(parts) - 1:
                self._end_line()
            else:
                self._advance()
        if self._answer.changes == before:
            return None
        shown = self._answer.text()
        if shown == self._shown:
            return None
        self._shown = shown
        return shown

    def _start(self, *, line_ended: bool = False) -> bool:
        if self._started:
            return True
        if not line_ended and _MAYBE_LIST_PREFIX.match(self._line):
            return False
        match = _LIST_PREFIX.match(self._line)
        prefix = match.group(1) if match else ""
        self._answer.start_line(prefix)
        self._line = self._line[len(prefix) :]
        self._started = True
        self._first = True
        self._scanned = 0
        return True

    def _advance(self) -> None:
        """Check every sentence of the current line that has ended."""

        if not self._start():
            return
        position = 0
        # A sentence ends at ., ! or ? followed by whitespace; only new text can hold one.
        for match in _SENTENCE.finditer(self._line, max(0, self._scanned - 1)):
            self._answer.sentence(self._line[position : match.start()], first=self._first)
            self._first = False
            position = match.end()
        self._line = self._line[position:]
        self._scanned = len(self._line)

    def _end_line(self) -> None:
        if not self._started:
            if not self._line.strip():
                self._answer.blank_line()
                self._reset_line()
                return
            self._start(line_ended=True)
        self._advance()
        if self._line.strip() or self._first:
            self._answer.sentence(self._line, first=self._first)
        self._answer.end_line()
        self._reset_line()

    def _reset_line(self) -> None:
        self._line = ""
        self._started = False
        self._first = True
        self._scanned = 0

    def partial(self) -> Validation:
        """What was already checked and shown, for when the stream fails part-way.

        The unfinished last sentence is never included: it was not checked as a whole.
        """

        return self._answer.validation()

    def finish(self) -> Validation:
        """The final check, including a last sentence without a full stop."""

        if self._started or self._line.strip():
            self._end_line()
        validation = self._answer.validation()
        self._shown = validation.text
        return validation
