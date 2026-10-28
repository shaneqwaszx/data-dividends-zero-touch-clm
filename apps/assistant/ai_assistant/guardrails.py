"""Exact output policy over current backend actions, reviewed explanations and approved knowledge.

Generated prose is untrusted, including paraphrases. Only allowed lines may be displayed, in
their own words (the owner's G6 direction, ADR-012). A model line is matched ignoring
formatting only, and may be several allowed lines in a row; otherwise it is dropped whole
(see ``_Catalog``, D-090, PROPOSED). The allowed lines are:

1. the catalog (``allowed_guidance``): trusted templates filled only from this request's
   backend projection, and reviewed explanation sentences for the fields and readiness items
   on this case (guide.py);
2. knowledge lines (``knowledge_lines``): each sentence of an approved knowledge entry that
   retrieval returned for this user and case, verbatim and followed by its tag
   ("<sentence> [G1]"), and only when the sentence passes the sentence checks below against
   this case's facts.

Document/company values, history, free model prose and paraphrases never extend the allowed
lines, except that each difference on a blocker is offered in one fixed template with both
values quoted (``difference_value_lines``, D-090, PROPOSED). The deterministic case-data
answer handles unsupported responses. This is bounded statement selection, not general
semantic verification.

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
  screen or label, one of the listed contact phrases, an e-mail address, a web address
  written with http://, https:// or www., or a "(section: ...)" is not in the case facts; it
  carries a citation tag of its own;
- policy: it uses one of the listed action phrasings for an action this RM is not offered on
  this case, or one of the listed authority phrasings (legal UBO verification, KYC/regulatory
  approval, one source automatically winning). Only a negation that directly governs the
  action or claim cancels it (see ``_negated``);
- disclosures: it calls a mock, local or sandbox system live in one of the listed ways, or
  presents a document value that differs from ACRA as confirmed.

Short numbers and percentages, people's names, bare domains, and wording outside the listed
phrasings are not recognised.
"""

import bisect
import dataclasses
import json
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from .context import SELECTION_ONLY_FACTS
from .guide import (
    APPROVAL_NOT_OFFERED,
    CASE_PAGE_SECTIONS,
    DIRECTOR_DIFFERENCE_CHECK,
    DIRECTOR_DIFFERENCE_REASONS,
    DIRECTORS_NOT_READ,
    DOCUMENT_REVIEW_CHOICES,
    ENTITY_STATUS_LIVE,
    MOCK_NOT_LIVE,
    NO_CONTACT,
    NOT_READY,
    OFFICERS_NOT_RETRIEVED,
    OUT_OF_SCOPE,
    OWNER,
    READINESS_EXPLANATIONS,
    READINESS_NEEDS,
    RULE_PLAIN,
    SEND_BEFORE_SUBMISSION,
    SENDING_IS_NOT_APPROVAL,
    SUBMISSION_RESULT_KEPT,
    UBO_CHECK_NOT_RUN,
    UBO_COMPLETION_NOT_OFFERED,
    UEN_MEANING,
    difference_explanations,
    difference_line,
    officer_record_line,
    officers_empty_line,
    who_resolves_line,
)
from .llm import LlmUnavailableError


def difference_fields(facts: dict[str, Any]) -> list[str]:
    """Fields (as labelled in the facts) where a blocker shows a document value unlike ACRA's."""

    fields: dict[str, None] = {}
    for blocker in facts.get("blockers") or []:
        for row in blocker.get("differences") or []:
            if row.get("field") and (row.get("registry_value") or row.get("document_value")):
                fields[str(row["field"])] = None
    return list(fields)


def not_ready(facts: dict[str, Any]) -> bool:
    """The readiness facts say the case cannot go to GoldTier yet."""

    if (facts.get("overall") or {}).get("status") == "completed":
        return False
    readiness = facts.get("readiness") or {}
    return bool(readiness.get("blockers") or facts.get("blockers"))


def ubo_check_not_run(facts: dict[str, Any]) -> bool:
    """No ownership analysis exists for the case, so there is no UBO result. The backend
    readiness check lists OWNERSHIP_REQUIRED and sets ownership to MISSING together, only when
    the case has no ownership analysis (backend services/clm_orchestration.py); both must hold."""

    needs = facts.get("still_needed_before_goldtier") or []
    required = any(need.get("code") == "OWNERSHIP_REQUIRED" for need in needs)
    sections = (facts.get("readiness") or {}).get("sections") or {}
    return required and sections.get("ownership") == "MISSING"


# Ownership states in which the UBO check is not complete (backend ReadinessStageStatus for
# the ownership stage; READY means the analysis is complete or POC-accepted, D-082).
_OWNERSHIP_INCOMPLETE = frozenset({"MISSING", "IN_PROGRESS", "REVIEW_REQUIRED", "FAILED"})
# An offered action that would complete or accept ownership (none exists today; fail closed).
_UBO_COMPLETION_LABEL = re.compile(
    r"\b(?:mark|accept|confirm|complete|approve|sign off|finali[sz]e|close|finish|resolve"
    r"|override|set)\w*\b[^.]{0,40}\b(?:ubos?|beneficial owners?|ownership|poc basis)\b"
    r"|\b(?:ubos?|beneficial owners?|ownership)\b[^.]{0,40}"
    r"\b(?:complete|completed|accepted|confirmed|approved|resolved|closed|finished|ready)\b"
)


def ubo_completion_not_offered(facts: dict[str, Any]) -> bool:
    """The UBO check is not complete and this RM is offered nothing that would complete it.
    The backend completes ownership itself (analysis finished, or the ownership owner's POC
    acceptance); no RM action marks it complete. Missing readiness data means False."""

    sections = (facts.get("readiness") or {}).get("sections") or {}
    if sections.get("ownership") not in _OWNERSHIP_INCOMPLETE:
        return False
    return not any(_UBO_COMPLETION_LABEL.search(label) for label in allowed_actions(facts))


def officers_line(facts: dict[str, Any]) -> str | None:
    """The officer (director) lookup line (D-092 P12), from the status of the registry officer
    lookup on this case (context._registry_officers), else None. "No records" only while the
    registry stage is READY and the company details come from a named non-live ACRA environment.
    """

    status = facts.get("registry_officers")
    if status in ("FAILED", "NOT_ATTEMPTED", "UNSUPPORTED"):
        return OFFICERS_NOT_RETRIEVED
    if status != "EMPTY":
        return None
    sections = (facts.get("readiness") or {}).get("sections") or {}
    environment = _NOT_LIVE_SOURCE.search(registry_source_line(facts, acra_only=True) or "")
    if sections.get("registry") != "READY" or environment is None:
        return None
    return officers_empty_line(environment.group(1))


def officer_record_lines(facts: dict[str, Any]) -> list[str]:
    """One line per current officer from the case's own non-live ACRA officer lookup (D-095,
    context._registry_officer_records), only while the registry stage is READY; each name is
    checked like a template value and the whole line passes the sentence checks."""

    records = facts.get("registry_officer_records") or []
    sections = (facts.get("readiness") or {}).get("sections") or {}
    environment = _NOT_LIVE_SOURCE.search(registry_source_line(facts, acra_only=True) or "")
    if not records or sections.get("registry") != "READY" or environment is None:
        return []
    lines: list[str] = []
    ctx = Context(facts)
    for record in records:
        name, role = record.get("name"), record.get("role")
        if not _safe_template_text(name) or not isinstance(role, str):
            continue
        line = officer_record_line(environment.group(1), str(name), role)
        if _check(line, ctx) is None:
            lines.append(line)
    return list(dict.fromkeys(lines))


def entity_status_live(facts: dict[str, Any]) -> bool:
    """The registry record's entity status is LIVE while the source is a non-live ACRA (P13)."""

    company = facts.get("company") or {}
    return (
        company.get("entity_status") == "LIVE"
        and registry_source_line(facts, acra_only=True) is not None
    )


def uen_explained(facts: dict[str, Any]) -> bool:
    """The case has a Singapore company with a UEN (P13)."""

    company = facts.get("company") or {}
    return bool(company.get("uen")) and company.get("country") == "SG"


def submission_result_kept(facts: dict[str, Any]) -> bool:
    """The backend confirms the GoldTier submission and its customer readback succeeded (P14)."""

    goldtier = facts.get("goldtier") or {}
    return (
        goldtier.get("state") == "SUBMISSION_CONFIRMED"
        and facts.get("goldtier_readback") == "SUCCESS"
    )


def approval_offered(facts: dict[str, Any]) -> bool:
    """An approve-type action is among the actions this RM is offered on this case."""

    return any(_APPROVE_LABEL.search(label) for label in allowed_actions(facts))


def approval_not_offered(facts: dict[str, Any]) -> bool:
    """Approving is not open to this RM: the case is not ready and no approve-type action is
    offered. A ready case reaches Review & Send, whose Send is the app's final human approval,
    so the "not offered" line is never offered there (QG F2)."""

    return not_ready(facts) and not approval_offered(facts)


# Straight and typographic double quotes: matching treats them alike, so either one inside a
# filled-in value could close the template's own quotes (QG F1).
_TEMPLATE_QUOTES = ('"', "\u201c", "\u201d")


def _safe_template_text(value: object) -> bool:
    return (
        isinstance(value, str)
        and 0 < len(value) <= MAX_DIFFERENCE_VALUE
        and not any(quote in value for quote in _TEMPLATE_QUOTES)
        and not _UNSUPPORTED_CHARACTER.search(value)
    )


def who_resolves_lines(facts: dict[str, Any]) -> list[str]:
    """'<blocker title>: this is for <owner>.' for each blocker whose owner the policy names."""

    lines: list[str] = []
    ctx: Context | None = None
    for blocker in facts.get("blockers") or []:
        title, who = blocker.get("title"), blocker.get("who_resolves")
        if who not in OWNER.values() or not _safe_template_text(title):
            continue
        line = who_resolves_line(str(title), str(who))
        ctx = ctx or Context(facts)
        if _check(line, ctx) is None:
            lines.append(line)
    return list(dict.fromkeys(lines))


# A document value is untrusted text (D-090, PROPOSED): it may appear only inside the
# difference template, in quotes it cannot close, on one line, short, and when the whole line
# passes the sentence checks. Those catch only the phrasings they list (actions not offered,
# the listed authority and Live claims); other wording, such as "approved" or "verified by
# ACRA", stays inside the quotes as the document's value.
MAX_DIFFERENCE_VALUE = 120


def difference_value_lines(facts: dict[str, Any]) -> list[str]:
    """'<Field>: ACRA says "<value>", the document says "<value>".' for each difference."""

    lines: list[str] = []
    ctx: Context | None = None
    for blocker in facts.get("blockers") or []:
        for row in blocker.get("differences") or []:
            values = (row.get("registry_value"), row.get("document_value"))
            if not row.get("field") or not all(_safe_template_text(value) for value in values):
                continue
            line = difference_line(row)
            ctx = ctx or Context(facts)
            if _check(line, ctx) is None:
                lines.append(line)
    return lines


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
        MOCK_NOT_LIVE,
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
        allowed.extend(READINESS_EXPLANATIONS.get(str(need.get("code")), ()))
    if ubo_check_not_run(facts):
        allowed.append(UBO_CHECK_NOT_RUN)
    if ubo_completion_not_offered(facts):
        allowed.append(UBO_COMPLETION_NOT_OFFERED)
    # The non-live registry source, only when the backend's own source says ACRA (<env>).
    source_line = registry_source_line(facts, acra_only=True)
    if source_line is not None:
        allowed.append(source_line)
    # Topic-only catalog lines (D-092 P12 to P14), each under its condition.
    allowed.extend([DIRECTORS_NOT_READ, DIRECTOR_DIFFERENCE_CHECK, DIRECTOR_DIFFERENCE_REASONS])
    officers = officers_line(facts)
    if officers is not None:
        allowed.append(officers)
    allowed.extend(officer_record_lines(facts))
    if entity_status_live(facts):
        allowed.append(ENTITY_STATUS_LIVE)
    if uen_explained(facts):
        allowed.append(UEN_MEANING)
    allowed.append(SEND_BEFORE_SUBMISSION)
    if submission_result_kept(facts):
        allowed.append(SUBMISSION_RESULT_KEPT)
    allowed.append(SENDING_IS_NOT_APPROVAL)
    allowed.extend(difference_value_lines(facts))
    for field in difference_fields(facts):
        reasons, checks = difference_explanations(field)
        allowed.extend([*reasons, *checks])
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
    if not_ready(facts):
        allowed.append(NOT_READY)
    if approval_not_offered(facts):
        allowed.append(APPROVAL_NOT_OFFERED)
    allowed.extend(who_resolves_lines(facts) or [NO_CONTACT])
    allowed.append(OUT_OF_SCOPE)
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
# E-mail addresses, and web addresses written with http://, https:// or www. (bare domains
# and other schemes are not recognised). An e-mail match starts only at the start of a word,
# so a long word without an @ is scanned once.
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
_APPROVE_LABEL = re.compile(rf"\b{_APPROVE}\b")
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
        # vouches for itself. Selection-only facts are not grounding.
        grounding = {key: value for key, value in facts.items() if key not in SELECTION_ONLY_FACTS}
        self.known = json.dumps(grounding, ensure_ascii=False, default=str).lower()
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
    # The left-out lines themselves, for the answer record only (never shown to the RM).
    # A read-only record of what was not kept: it takes no part in selecting lines.
    dropped: tuple[str, ...] = dataclasses.field(default=(), compare=False, repr=False)

    def notice(self) -> str | None:
        parts = list(self.disclosures)
        if self.left_out:
            noun = "1 statement" if self.left_out == 1 else f"{self.left_out} statements"
            parts.append(REMOVED_NOTICE.format(count=noun))
        return " ".join(parts) or None


_NOT_LIVE_SOURCE = re.compile(r"\((MOCK|LOCAL|SANDBOX|PARTIAL|DORMANT)\)")


def registry_source_line(facts: dict[str, Any], *, acra_only: bool = False) -> str | None:
    """ "Registry data in this case comes from ACRA (<environment>), not the live ACRA
    service." when the backend's company source names an environment that is not live, else
    None. The source is the backend's ``case.entity.source`` (context._source_label), never
    document evidence. ``acra_only``: also require that the source system is ACRA."""

    source = str((facts.get("company") or {}).get("source") or "")
    environment = _NOT_LIVE_SOURCE.search(source)
    if environment is None:
        return None
    if acra_only and not source.startswith(f"ACRA ({environment.group(1)})"):
        return None
    return (
        f"Registry data in this case comes from ACRA ({environment.group(1)}), "
        "not the live ACRA service."
    )


def _disclosures(text: str, facts: dict[str, Any]) -> tuple[str, ...]:
    """A note when the shown answer relies on registry data from a registry that is not live."""

    line = registry_source_line(facts)
    environment = _NOT_LIVE_SOURCE.search(line or "")
    lowered = text.lower()
    if line is None or environment is None or environment.group(1).lower() in lowered:
        return ()
    company = facts.get("company") or {}
    registry_values = [
        str(company[key]).lower()
        for key in ("uen", "registered_address", "registration_date")
        if company.get(key)
    ]
    if re.search(r"\bacra\b", lowered) or any(value in lowered for value in registry_values):
        return (line,)
    return ()


# --- matching model lines to allowed lines (D-090, PROPOSED) -----------------------------
#
# A model line is compared in a normal form that ignores formatting only: case (ASCII letters
# only, so look-alike letters from other scripts never fold into Latin ones), runs of spaces,
# straight or curly quotes, Markdown emphasis and backticks, a leading list marker and a
# trailing full stop. What is shown is always the allowed line's own text, never the model's.

_ASCII_LOWER = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")
_CURLY_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'})
_MODEL_LIST_MARKER = re.compile(r"^(?:[-*•]|\d{1,3}[.)]) +")
_STRONG = re.compile(r"\*\*|__|`")
# A single * or _ that opens or closes emphasis (not one inside a word, like snake_case).
_EMPHASIS = re.compile(r"(?<![\w*])[*_](?=\S)|(?<=\S)[*_](?![\w*])")
# Sentence ends, and ")" so a "(section: ...)" line can be followed by another line.
_MODEL_SENTENCE = re.compile(r"(?<=[.!?)]) ")
_OFFERED = re.compile(r'^The current case offers "(.+)"\.$')
_TAGGED = re.compile(r"^(.+) \[[GP]\d+\]$")


def _plain(text: str) -> str:
    """``text`` without formatting, keeping its final full stop (sentences are re-joined)."""

    text = text.strip().translate(_CURLY_QUOTES)
    text = _EMPHASIS.sub("", _STRONG.sub("", text))
    text = _MODEL_LIST_MARKER.sub("", text.strip())
    return _SPACES.sub(" ", text).strip().translate(_ASCII_LOWER)


def _key(plain: str) -> str:
    return plain[:-1] if plain.endswith(".") else plain


class _Catalog:
    """The allowed lines of one request, looked up by normal form (one dict, built once)."""

    def __init__(self, facts: dict[str, Any], knowledge_lines: Sequence[str]) -> None:
        guidance = allowed_guidance(facts)
        self.lines: dict[str, str] = {}
        for line in [*guidance, *knowledge_lines]:
            self.lines.setdefault(_key(_plain(line)), line)
        # A bare action label stands for the catalog's line offering that action, which
        # exists only when this RM is offered it on this case.
        for line in guidance:
            offered = _OFFERED.match(line)
            if offered:
                self.lines.setdefault(_key(_plain(offered.group(1))), line)
        # A knowledge sentence without its tag stands for the first offered line (by ranking)
        # with that sentence; it is shown with the tag.
        for line in knowledge_lines:
            tagged = _TAGGED.match(line)
            if tagged:
                self.lines.setdefault(_key(_plain(tagged.group(1))), line)
        # The most sentences one allowed line has, so a model line is split in bounded work.
        self.max_parts = max(
            (len(_MODEL_SENTENCE.split(_plain(line))) for line in self.lines.values()), default=1
        )

    def select(self, line: str) -> list[str] | None:
        """The allowed lines a model line stands for, or None when any part is not allowed.

        A line that is several allowed lines is split at sentence ends; from each sentence the
        longest run (up to ``max_parts`` sentences) that is an allowed line is taken.
        """

        parts = _MODEL_SENTENCE.split(_plain(line))
        found: list[str] = []
        start = 0
        while start < len(parts):
            for end in range(min(len(parts), start + self.max_parts), start, -1):
                match = self.lines.get(_key(" ".join(parts[start:end])))
                if match is not None:
                    found.append(match)
                    start = end
                    break
            else:
                return None
        return found


def validate_answer(
    answer: str, facts: dict[str, Any], *, knowledge_lines: Sequence[str] = ()
) -> Validation:
    """Select allowed lines (see _Catalog); unknown wording cannot become operational advice.

    ``knowledge_lines`` must come from ``knowledge_lines()`` for this request.
    """

    catalog = _Catalog(facts, knowledge_lines)
    kept: dict[str, None] = {}
    left_out = 0
    dropped: list[str] = []
    for line in answer.splitlines():
        if not line.strip():
            continue
        selected = catalog.select(line)
        if selected is None:
            left_out += 1
            dropped.append(line.strip())
        else:
            kept.update(dict.fromkeys(selected))
    text = "\n".join(kept)
    return Validation(
        text=text,
        left_out=left_out,
        disclosures=_disclosures(text, facts),
        dropped=tuple(dropped),
    )


MAX_ANSWER_LINES = 6
# Required lines may take an answer past MAX_ANSWER_LINES, up to this many lines.
MAX_ANSWER_LINES_WITH_REQUIRED = 8


def with_required_lines(
    validation: Validation,
    facts: dict[str, Any],
    *,
    order: Sequence[str],
    required: Sequence[str],
    streamed: Sequence[str] = (),
) -> Validation:
    """Add the topic's required lines the model left out (D-090, PROPOSED).

    Only allowed lines are added, in the catalog's words. When any is missing, the answer is put
    in the topic's ``order`` (other lines after, in the model's order). Lines the RM has not
    seen yet are then dropped from the end: lines that are not required until the answer has
    MAX_ANSWER_LINES, then required ones until it has MAX_ANSWER_LINES_WITH_REQUIRED. A line
    already ``streamed`` to the RM is never removed. An empty answer stays empty: the case-data
    answer is used instead.
    """

    allowed = set(allowed_guidance(facts))
    shown = validation.text.splitlines()
    needed = [line for line in dict.fromkeys(required) if line in allowed]
    missing = [line for line in needed if line not in shown]
    if not shown or not missing:
        return validation
    position = {line: index for index, line in enumerate(order)}
    lines = sorted([*shown, *missing], key=lambda line: position.get(line, len(position)))
    seen = set(streamed)
    for limit, keep in (
        (MAX_ANSWER_LINES, {*needed, *seen}),
        (MAX_ANSWER_LINES_WITH_REQUIRED, seen),
    ):
        # Indices from the end, so popping one never shifts the next.
        droppable = [index for index, line in enumerate(lines) if line not in keep]
        while len(lines) > limit and droppable:
            lines.pop(droppable.pop())
    text = "\n".join(lines)
    return Validation(
        text=text,
        left_out=validation.left_out,
        disclosures=_disclosures(text, facts),
        dropped=validation.dropped,
    )


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
        self._catalog = _Catalog(facts, knowledge_lines)
        self._pending: list[str] = []  # the unfinished line, in pieces
        self._accepted: dict[str, None] = {}
        self._left_out = 0
        self._dropped: list[str] = []
        self._total_bytes = 0

    @property
    def _raw(self) -> str:
        """Model text held but not yet looked up (bounded by MAX_MODEL_TEXT_BYTES)."""

        return "".join(self._pending)

    def _accept(self, line: str) -> None:
        if not line.strip():
            return
        selected = self._catalog.select(line)
        if selected is None:
            self._left_out += 1
            self._dropped.append(line.strip())
        else:
            self._accepted.update(dict.fromkeys(selected))

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
            text=text,
            left_out=self._left_out,
            disclosures=_disclosures(text, self._facts),
            dropped=tuple(self._dropped),
        )
