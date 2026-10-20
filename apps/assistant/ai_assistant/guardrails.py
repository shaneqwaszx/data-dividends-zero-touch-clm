"""Exact output policy over current backend actions, reviewed explanations and approved knowledge.

Generated prose is untrusted, including paraphrases. Only whole model lines that exactly equal
an allowed line may be displayed (the owner's G6 direction, ADR-012). The allowed lines are:

1. the catalog (``allowed_guidance``): trusted templates filled only from this request's
   backend projection;
2. knowledge lines (``knowledge_lines``): each sentence of an approved knowledge entry that
   retrieval returned for this user and case, verbatim and followed by its tag
   ("<sentence> [G1]"), and only when the sentence passes the sentence checks below against
   this case's facts.

Document/company values, history, free model prose and paraphrases never extend the allowed
lines. The deterministic case-data answer handles unsupported responses. This is bounded
statement selection, not general semantic verification.

For knowledge, two-person approval of every version is the robust control. The sentence
checks are a secondary, best-effort filter on approved knowledge text (sentences, and the
titles and follow-up questions shown with it, see ``checked_texts``), never a replacement for
the catalog. They catch plain phrasings only; ADR-012 lists what they miss. A knowledge
sentence is not offered when (fail closed):

- it contains a character outside printable ASCII and the typographic quotes, dashes,
  ellipsis and bullet (this refuses tabs, non-breaking and invisible spaces, and look-alike
  letters from other scripts);
- grounding: a UEN or NRIC/FIN, postal code, unit number, decimal or number of three or more
  digits is not in the case facts; "N of M steps" does not match the case; a quoted button,
  screen or label, one of the listed contact phrases, an e-mail address or web address, or a
  "(section: ...)" is not in the case facts; it carries a citation tag of its own;
- policy: it uses one of the listed action phrasings for an action this RM is not offered on
  this case, or one of the listed authority phrasings (legal UBO verification, KYC/regulatory
  approval, one source automatically winning). Only a negation that directly governs the
  action or claim cancels it (see ``_negated``);
- disclosures: it calls a mock, local or sandbox system live in one of the listed ways, or
  presents a document value that differs from ACRA as confirmed.

Short numbers and percentages, people's names, and wording outside the listed phrasings are
not recognised.
"""

import bisect
import json
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
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


# --- sentence checks (knowledge sentences only) -----------------------------------------

# A label in double quotes, or in single quotes that are not apostrophes ("ACRA's", "it's").
_QUOTED = re.compile(
    r"[\"“”]([^\"“”\n]{2,60})[\"“”]|(?<![A-Za-z])['‘]([^'’\n]{2,60})['’](?![A-Za-z])"
)
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
_SECTION_REF = re.compile(r"\(section: ?([^)]{1,80})\)", re.IGNORECASE)
_CITATION = re.compile(r"\[[GP]\d+\]")
_SPACES = re.compile(" {2,}")
# Printable ASCII plus typographic quotes, dashes, ellipsis and bullet. Anything else
# (tabs, non-breaking or invisible spaces, letters from other scripts that look like Latin
# ones) is refused rather than normalised.
_UNSUPPORTED_CHARACTER = re.compile("[^\x20-\x7e\u2018\u2019\u201c\u201d\u2013\u2014\u2026\u2022]")
# E-mail and web addresses. An e-mail match starts only at the start of a word, so a long
# word without an @ is scanned once.
_ADDRESS = re.compile(r"(?<![\w.+-])[\w.+-]++@[\w-]+(?:\.[\w-]+)+|\bhttps?://\S+|\bwww\.\S+")

# Actions the app can offer, and the wording used for them. The labels are the ones the case
# page shows (backend api_models._INTERVENTION_ACTIONS and the review panel in
# BlockerDecisionReview.tsx). "Approve" and "submit to GoldTier" are never offered by the AI
# Assistant in Phase 1: final approval is a human gate outside the chat.
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
# Parts of one sentence that can say opposite things ("you cannot X, but you can Y").
_CLAUSE = re.compile(r",? but |; ?|, ?however,? ?| whereas |, ?while ")

# Fail closed: an action the RM is not offered, or an authority claim, counts unless a
# negation directly governs it. Only these fixed constructions count, written immediately
# before the phrase (allowing a few listed filler words):
#   action: a negated modal or "never"           "You cannot approve the case", "Do not resend"
#   claim:  no / not / never / without, a negated "is", or a negated denial verb
#           "This is not KYC approval", "does not establish KYC approval"
# and only when nothing earlier in the same phrase is negated too ("There's no reason you
# shouldn't resend it" affirms). The single other exemption is the action phrase itself as
# the subject of "is not available/allowed/possible/offered". Anything else ("Do not wait to
# approve the case", "No issues remain and the UBOs are verified") counts. Some genuine
# negations are over-dropped; that is the safe side. Known limit: wording around a governed
# action can still reverse it ("Previously you couldn't approve the case, but now you can.");
# such a sentence reaches a user only as part of approved knowledge (ADR-012 residual risks).
_PHRASE_BREAK = re.compile(r"[,:;()–—]| - ")
_ACTION_GOVERNOR = re.compile(
    r"\b(?:cannot|can not|can't|could not|couldn't|do not|don't|does not|doesn't|did not"
    r"|didn't|will not|won't|would not|wouldn't|should not|shouldn't|must not|mustn't"
    r"|may not|might not|shall not|never) (?:(?:be|directly|yet|ever|then) )?$"
)
_CLAIM_GOVERNOR = re.compile(
    r"(?:\b(?:no|not|never|without|is not|are not|was not|were not|isn't|aren't|wasn't"
    r"|weren't)|\b(?:does not|doesn't|do not|don't|did not|didn't|will not|won't|cannot"
    r"|can't) (?:mean|establish|imply|constitute|guarantee|give|grant|confirm|prove))"
    r" (?:(?:a|an|the|any|full|final|yet|be|directly) )*$"
)
_ANY_NEGATION = re.compile(
    r"\b(?:no|not|never|none|nothing|nobody|neither|nor|without|cannot)\b|\b\w+n't\b"
)
_SUBJECT_UNAVAILABLE = re.compile(
    r" (?:is|are)(?: not|n't) (?:available|allowed|possible|offered)\b"
)
# How far before an action or claim its governing negation may start; a governor further
# away is not found, so the action or claim counts (fail closed).
_GOVERNOR_REACH = 80


def _negated(
    clause: str, start: int, end: int, breaks: list[int], negations: list[int], *, claim: bool
) -> bool:
    """True when a negation directly governs the action or claim at ``start:end``.

    ``breaks`` (phrase-break ends) and ``negations`` (negation-word starts) are found once
    per clause, so each match costs a bounded amount of work.
    """

    index = bisect.bisect_right(breaks, start)
    phrase = breaks[index - 1] if index else 0
    if not claim and start - phrase <= 5 and clause[phrase:start].strip() in ("", "the", "a", "an"):
        return bool(_SUBJECT_UNAVAILABLE.match(clause, end))
    governor = (_CLAIM_GOVERNOR if claim else _ACTION_GOVERNOR).search(
        clause, max(phrase, start - _GOVERNOR_REACH), start
    )
    if governor is None:
        return False
    # A second negation earlier in the phrase turns the whole thing back into advice.
    first = bisect.bisect_left(negations, phrase)
    return not (first < len(negations) and negations[first] < governor.start())


def _asserted(pattern: re.Pattern[str], clause: str, *, claim: bool = False) -> bool:
    """True when ``pattern`` occurs in ``clause`` without a negation governing it."""

    matches = list(pattern.finditer(clause))
    if not matches:
        return False
    breaks = [m.end() for m in _PHRASE_BREAK.finditer(clause)]
    negations = [m.start() for m in _ANY_NEGATION.finditer(clause)]
    return any(
        not _negated(clause, m.start(), m.end(), breaks, negations, claim=claim) for m in matches
    )


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


# Specific values that could be wrong for this case: UENs, postal codes, unit numbers,
# decimals, any number of three or more digits, and the NRIC/FIN and T/S/R-format UEN shapes
# that redaction.py recognises (matched on lower-case text). Short counts and percentages
# ("2 documents", "25%") are not checked here.
_VALUE = re.compile(
    r"#\d+(?:-\d+)+|\b\d+\.\d+\b|\b\d{3,}[A-Za-z]?\b"
    r"|\b[stfgm]\d{7}[a-z]\b|\b[tsr]\d{2}[a-z]{2}\d{4}[a-z]\b"
)
_STEPS = re.compile(r"\b(\d+) ?(?:of|out of|/) ?(\d+) ?(?:onboarding )?steps?\b")
_LIVE = re.compile(
    r"\b(?:live|production|real) (?:acra|registry|goldtier|system|environment|integration"
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


class Context:
    """This case's facts, worked out once for all sentence checks of one request."""

    def __init__(self, facts: dict[str, Any]) -> None:
        # Values, labels and contacts must come from the case facts; knowledge text never
        # vouches for itself.
        self.known = json.dumps(facts, ensure_ascii=False, default=str).lower()
        self.allowed = allowed_actions(facts)
        self.sections = {str(name) for name in facts.get("case_page_sections") or []}
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
    """The reason this sentence must not be offered, or None when it passes."""

    if _UNSUPPORTED_CHARACTER.search(sentence):
        return "unsupported_character"
    text = _SPACES.sub(" ", sentence)
    lowered = text.lower().replace("\u2019", "'")
    # 1. Grounding
    if _CITATION.search(text):
        return "invented_source"
    for phrase in _CONTACTS:
        if phrase in lowered and phrase not in ctx.known:
            return "invented_contact"
    for address in _ADDRESS.findall(lowered):
        if address.rstrip(".,;:!?)") not in ctx.known:
            return "invented_contact"
    for double, single in _QUOTED.findall(text):
        label = (double or single).strip().lower()
        if label and label not in ctx.known and not any(ch.isdigit() for ch in label):
            return "invented_label"
    for name in _SECTION_REF.findall(text):
        if name.strip() not in ctx.sections:
            return "unknown_section"
    for value in _VALUE.findall(lowered):
        if value not in ctx.known:
            return "unsupported_value"
    for done, total in _STEPS.findall(lowered):
        if (int(done), int(total)) != ctx.steps:
            return "wrong_step_count"
    clauses = _CLAUSE.split(lowered)
    # 2. Policy
    for clause in clauses:
        for label, pattern in _ACTION_PHRASES:
            if label not in ctx.allowed and _asserted(pattern, clause):
                return "action_not_allowed"
    for clause in clauses:
        if _asserted(_AUTHORITY, clause, claim=True):
            return "authority_claim"
    # 3. Disclosures
    if _LIVE.search(lowered) and "status" not in lowered:
        return "live_claim"
    for clause in clauses:
        if (
            _asserted(_CONFIRMED, clause, claim=True)
            and not re.search(r"\b(?:acra|registry)\b", clause)
            and any(value in clause for value in ctx.unconfirmed_document_values)
        ):
            return "document_value_as_fact"
    return None


def sentence_problem(sentence: str, facts: dict[str, Any]) -> str | None:
    """Why ``sentence`` could not be offered as a knowledge line on this case (None: it can)."""

    return _check(sentence, Context(facts))


# Knowledge shown in one answer is bounded, so a stream of selected lines (each update
# re-sends the answer so far) stays small even for pathological approved entries.
MAX_LINES_PER_ENTRY = 20
MAX_KNOWLEDGE_LINES = 48
MAX_KNOWLEDGE_BYTES = 8 * 1024
# A title or follow-up question longer than this is not shown.
MAX_KNOWLEDGE_LABEL = 200

_SENTENCE = re.compile(r"(?<=[.!?]) ")
_LIST_MARKER = re.compile(r"(?:[-*•]|\d{1,3}[.)]) ")


def knowledge_lines(facts: dict[str, Any], knowledge: Iterable[tuple[str, str]]) -> list[str]:
    """The lines approved knowledge adds: "<sentence> [tag]" for each sentence that passes.

    ``knowledge`` is (tag, body) for each retrieved entry that is approved and visible to this
    user, in ranking order (see knowledge_answers.approved_knowledge). Each body line loses a
    leading list marker and is split into sentences; runs of spaces become one space.
    Everything else is kept exactly as approved. At most MAX_LINES_PER_ENTRY lines per entry
    and MAX_KNOWLEDGE_LINES lines of MAX_KNOWLEDGE_BYTES (UTF-8) in all are offered; lines
    past the limits are not.
    """

    ctx = Context(facts)
    lines: dict[str, None] = {}
    size = 0
    for tag, body in knowledge:
        own = 0
        for raw in body.splitlines():
            text = _SPACES.sub(" ", raw.strip())
            marker = _LIST_MARKER.match(text)
            if marker:
                text = text[marker.end() :]
            for sentence in _SENTENCE.split(text):
                if own >= MAX_LINES_PER_ENTRY or len(lines) >= MAX_KNOWLEDGE_LINES:
                    break
                line = f"{sentence} [{tag}]"
                cost = len(line.encode("utf-8")) + 1
                if (
                    line in lines
                    or size + cost > MAX_KNOWLEDGE_BYTES
                    or not sentence.strip(" -*•.")
                    or _check(sentence, ctx) is not None
                ):
                    continue
                lines[line] = None
                size += cost
                own += 1
    return list(lines)


def checked_texts(facts: dict[str, Any], texts: Iterable[str]) -> list[str]:
    """The texts that pass the sentence checks on this case, in order.

    For the other knowledge text the RM can see: entry titles (source chips and the no-model
    answer) and follow-up questions (suggested questions). A text longer than
    MAX_KNOWLEDGE_LABEL characters never passes.
    """

    ctx = Context(facts)
    return [
        text for text in texts if len(text) <= MAX_KNOWLEDGE_LABEL and _check(text, ctx) is None
    ]


# --- what the RM sees -----------------------------------------------------------------

LEFT_OUT_REASON = "not_an_allowed_line"
REMOVED_NOTICE = "I left out {count} that I could not check against the case data."


@dataclass(frozen=True)
class Validation:
    text: str
    # How many non-empty model lines were not allowed lines and so were left out.
    left_out: int = 0
    # Short notices the RM should see with the answer.
    disclosures: tuple[str, ...] = ()

    def notice(self) -> str | None:
        parts = list(self.disclosures)
        if self.left_out:
            noun = "1 statement" if self.left_out == 1 else f"{self.left_out} statements"
            parts.append(REMOVED_NOTICE.format(count=noun))
        return " ".join(parts) or None


def _disclosures(text: str, facts: dict[str, Any]) -> tuple[str, ...]:
    """A note when the shown answer relies on registry data from a registry that is not live."""

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


def _allowed(facts: dict[str, Any], knowledge_lines: Sequence[str]) -> set[str]:
    return {*allowed_guidance(facts), *knowledge_lines}


def validate_answer(
    answer: str, facts: dict[str, Any], *, knowledge_lines: Sequence[str] = ()
) -> Validation:
    """Select exact allowed lines; unknown wording cannot become operational advice.

    ``knowledge_lines`` must come from ``knowledge_lines()`` for this request.
    """

    allowed = _allowed(facts, knowledge_lines)
    kept: dict[str, None] = {}
    left_out = 0
    for line in answer.splitlines():
        line = line.strip()
        if line in allowed:
            kept[line] = None
        elif line:
            left_out += 1
    text = "\n".join(kept)
    return Validation(text=text, left_out=left_out, disclosures=_disclosures(text, facts))


def guard_answer(answer: str, facts: dict[str, Any], *, knowledge_lines: Sequence[str] = ()) -> str:
    """The selected allowed lines only (see validate_answer)."""

    return validate_answer(answer, facts, knowledge_lines=knowledge_lines).text


MAX_MODEL_TEXT_BYTES = 64 * 1024
# Everything str.splitlines() ends a line at, so streaming splits exactly like the batch check.
_LINE_ENDS = frozenset("\n\r\v\f\x1c\x1d\x1e\x85  ")


class StreamingGuard:
    """Select new complete allowed lines once; bound even newline-free model output.

    Only the new text is split into lines, a complete line is looked up once and then
    dropped from the buffer (never parsed again), and an unfinished line is never shown.
    The result equals ``validate_answer`` on the whole text.
    """

    def __init__(self, facts: dict[str, Any], *, knowledge_lines: Sequence[str] = ()) -> None:
        self._facts = facts
        self._allowed = _allowed(facts, knowledge_lines)
        self._pending: list[str] = []  # the unfinished line, in pieces
        self._accepted: dict[str, None] = {}
        self._left_out = 0
        self._total_bytes = 0

    @property
    def _raw(self) -> str:
        """Model text held but not yet looked up (bounded by MAX_MODEL_TEXT_BYTES)."""

        return "".join(self._pending)

    def _accept(self, line: str) -> None:
        line = line.strip()
        if line in self._allowed:
            self._accepted[line] = None
        elif line:
            self._left_out += 1

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
        before = len(self._accepted)
        for part in text.splitlines(keepends=True):
            if part[-1] in _LINE_ENDS:
                self._accept("".join(self._pending) + part)
                self._pending = []
            else:
                self._pending.append(part)
        return self.text if len(self._accepted) != before else None

    @property
    def text(self) -> str:
        return "\n".join(self._accepted)

    def finish(self) -> str:
        """Look up the last line (it may end without a line break) and return the answer."""

        if self._pending:
            self._accept("".join(self._pending))
            self._pending = []
        return self.text

    def validation(self) -> Validation:
        """The answer so far, how many model lines were left out, and its disclosures."""

        text = self.text
        return Validation(
            text=text, left_out=self._left_out, disclosures=_disclosures(text, self._facts)
        )
