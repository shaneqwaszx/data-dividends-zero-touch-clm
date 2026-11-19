"""Match complete case questions to service-written questions for external models."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .guardrails import registry_source_line, ubo_completion_not_offered
from .guide import FIELD_LABEL
from .prompts import UBO_CALCULATION_QUESTION, _ownership_required, topic_plan

BLOCKERS = "BLOCKERS"
READINESS = "READINESS"
APPROVE = "APPROVE"
CONTACT = "CONTACT"
DOCUMENT_REVIEW = "DOCUMENT_REVIEW"
OWNERSHIP_EVIDENCE = "OWNERSHIP_EVIDENCE"
DIFFERENCE = "DIFFERENCE"
DIRECTORS = "DIRECTORS"
DIRECTOR_DIFFERENCE = "DIRECTOR_DIFFERENCE"
OWNERS = "OWNERS"
UBO_COMPLETION = "UBO_COMPLETION"
REGISTRY_SOURCE = "REGISTRY_SOURCE"
UEN = "UEN"
ENTITY_STATUS = "ENTITY_STATUS"
GOLDTIER_HANDOFF = "GOLDTIER_HANDOFF"
# Pre-demo enhancement: an explanation of the application's own ownership calculation. Admitted
# only when the ownership projection (copilot.ownership_facts) is in the facts and complete
# (ubo_calculation_ready); the exact-line case facts never carry it, so there it is unsupported.
UBO_CALCULATION = "UBO_CALCULATION"

# The fixed, service-written canonical question of each intent. DIFFERENCE takes its validated
# field names; no other intent takes a binding.
CANONICAL: dict[str, str] = {
    BLOCKERS: "Why is this case blocked, and what should be done next?",
    READINESS: "Is this case ready to be sent to GoldTier, and what is still needed?",
    APPROVE: "Can I approve this case?",
    CONTACT: "Who resolves the open items on this case?",
    DOCUMENT_REVIEW: "What does the document review on this case still need?",
    OWNERSHIP_EVIDENCE: "What ownership evidence does this case still need?",
    DIFFERENCE: "Explain the {fields} difference between the document and the registry record.",
    DIRECTORS: "Who are the company's directors in the registry record?",
    DIRECTOR_DIFFERENCE: "Why do the company's directors differ from the document?",
    OWNERS: "Who are the ultimate beneficial owners?",
    UBO_COMPLETION: "Can I mark the UBO check as complete?",
    REGISTRY_SOURCE: "Which registry did the company details come from, and is it live?",
    UEN: "What is the UEN, and where did the company details come from?",
    ENTITY_STATUS: "Is the company's entity status live?",
    GOLDTIER_HANDOFF: "What happens when this case is sent to GoldTier?",
    UBO_CALCULATION: UBO_CALCULATION_QUESTION,
}

# Complete variants of the same supported request. The local topic matchers are intentionally
# broader and cannot be used as external admission evidence. The one reviewed exception is
# classify_ubo_calculation (UBO_CALCULATION only; owner decisions U-1/U-2).
QUESTION_VARIANTS = {
    BLOCKERS: (
        "Why is this case blocked?",
        "What is blocking this case?",
        "What is blocking this case right now?",
        "What should I do next?",
        "What is the next step?",
        "What is blocking this case right now, and what should I do next?",
    ),
    READINESS: (
        "Is this case ready for GoldTier?",
        "Is this case ready to be sent to GoldTier?",
    ),
    APPROVE: ("Can I approve the case?",),
    DIRECTORS: (
        "Who are the directors of this company?",
        "Who are the directors of this company according to ACRA?",
    ),
    OWNERS: ("Who are the ultimate beneficial owners of this company?",),
    REGISTRY_SOURCE: ("Which registry was used for this company, and is that registry live?",),
    UEN: ("What does this case's UEN tell me, and where did the company details come from?",),
    GOLDTIER_HANDOFF: (
        "What happens when the case is handed off to GoldTier?",
        "What happens after it is sent to GoldTier?",
    ),
    UBO_CALCULATION: (
        "Explain the UBO calculation",
        "How are the UBO percentages calculated?",
        "Who are the UBO candidates?",
        "Who are the provisional UBO candidates?",
        "How was the UBO calculation done?",
        "Explain how the UBO percentages were calculated",
        "How is the effective ownership calculated?",
    ),
}

_REVIEWED_FIELDS = frozenset(FIELD_LABEL.values())
_DIFFERENCE_QUESTION = re.compile(
    r"explain the (.+) difference(?: between the document and the registry record)?"
)


def _normalise(question: str) -> str:
    return " ".join(question.lower().split()).removesuffix("?").removesuffix(".")


_QUESTIONS = {
    kind: frozenset(
        _normalise(variant) for variant in (canonical, *QUESTION_VARIANTS.get(kind, ()))
    )
    for kind, canonical in CANONICAL.items()
    if kind != DIFFERENCE
}


# --- UBO_CALCULATION: the reviewed local classifier (D-142 amendment U-1/U-2) -----------------
#
# The one reviewed exception to "local topic matchers are never external admission evidence"
# (owner decisions U-1 and U-2, 2026-11-19; project-defined, not sponsor-confirmed). It only
# decides whether a question asks for UBO_CALCULATION; what an external model receives is
# still the fixed canonical question, never the words typed. It denies first: anything outside
# its closed vocabulary, any deny word, a digit or symbol, a second sentence, a capitalised word
# that could be a name, a yes/no question or a "who" question without "candidate" is not
# admitted (the deterministic case-data answer follows). No other intent has a classifier.


def _words(*text: str) -> frozenset[str]:
    return frozenset(" ".join(text).split())


# Polite openings removed before the shape checks ("Can you explain ...").
_UBO_POLITE = re.compile(
    r"^(?:(?:can|could|would) you (?:please )?|please |tell me |show me |help me understand "
    r"|i (?:want|would like) to (?:know|understand) |i'd like to (?:know|understand) )+"
)
_UBO_CONTRACTIONS = {"who's": "who is", "what's": "what is", "how's": "how is"}
# A yes/no question asks for a judgement ("Is the calculation correct?"), never admitted.
_UBO_YES_NO = _words(
    "is are was were do does did can could would should will has have had may might must shall"
)
# Explicit deny words: legal or formal determinations, instructions and injection, documents,
# identifiers and personal data, other cases, judgements and actions.
_UBO_DENY = _words(
    "legal legally official officially formal formally final finally "
    "finalize finalised finalized determination determine determined determines verify "
    "verified verification certified confirm confirmed confirmation approve "
    "approved approval submit send ignore override forget "
    "system prompt instruction instructions rule rules developer raw payload json "
    "document documents upload uploaded file files register registry nric fin passport id "
    "identifier identity address phone email uen another other others "
    "else correct wrong accurate valid right should decide change edit update set "
    "mark complete also then"
)
# The closed vocabulary a UBO_CALCULATION question may use (every word must be here).
_UBO_WORDS = _words(
    # function words
    "a an the this that these those of for in on to from by with at as and is are was were "
    "be been being do does did has have had it its they them their each every who whom "
    "whose which what how why me my i i'd we our you can could would please tell show "
    "help understand know want like let us here case case's company company's"
    # explanation and calculation
    " explain explained explaining explanation describe walk through get got arrive "
    "arrived derive derived calculate calculated calculating calculation calculations "
    "compute computed computing computation work worked working workings out figure "
    "figured come came up reach reached break breakdown down math maths arithmetic method "
    "methodology logic steps step process done application app app's engine behind end"
    # ownership domain
    " ubo ubos ubo's ultimate beneficial owner owners ownership shareholding shareholdings "
    "shareholder shareholders share shares percentage percentages percent effective direct "
    "indirect directly indirectly aggregate aggregated total interest interests candidate "
    "candidates provisional potential possible path paths chain chains link links "
    "threshold thresholds result results met meet meets meeting above below people person "
    "persons individual individuals holder holders holding holdings layer layers "
    "multiplied combined added counted identified listed named shown considered classified "
    "classification"
)
# The question is about ownership (one of these is required).
_UBO_ANCHOR = _words(
    "ubo ubos ubo's beneficial ownership shareholding shareholdings shareholder shareholders"
)
# How it was calculated, or who the provisional candidates are (one is required).
_UBO_CUE = _words(
    "how why explain explained explaining explanation describe calculate calculated "
    "calculating calculation calculations compute computed computing computation derive "
    "derived arrive arrived workings breakdown math maths arithmetic method methodology "
    "logic steps"
)
_UBO_CANDIDATE = frozenset({"candidate", "candidates"})
# Acronyms and words that may be capitalised anywhere ("UBO", "I").
_UBO_CAPITALS = frozenset({"ubo", "ubos", "ubo's", "i", "i'd"})
_UBO_TEXT = re.compile(r"[A-Za-z' -]+")
MAX_UBO_WORDS = 25
MAX_UBO_REPEATS = 3
_UBO_ARTICLES = frozenset({"the", "a", "an", "of", "and", "in", "to"})


def classify_ubo_calculation(question: str) -> bool:
    """True when the question, as typed, asks how the application calculated UBO or ownership
    percentages, effective ownership, paths or threshold results, or who the provisional UBO
    candidates are; False for anything else or anything ambiguous (deny first)."""

    text = question.replace("’", "'").strip()
    if text.endswith(("?", ".")):
        text = text[:-1].rstrip()
    # One sentence of letters only: no digit, symbol, second sentence or line break.
    if not text or not _UBO_TEXT.fullmatch(text):
        return False
    raw = text.split()
    if not 3 <= len(raw) <= MAX_UBO_WORDS:
        return False
    # A capitalised word after the first may be a name or a section: not admitted.
    if any(
        word != word.lower() and word.lower() not in _UBO_CAPITALS and index > 0
        for index, word in enumerate(raw)
    ):
        return False
    lowered = [_UBO_CONTRACTIONS.get(word, word) for word in " ".join(raw).lower().split()]
    words = [word.strip("'-") for word in " ".join(lowered).split()]
    if any(not word or word in _UBO_DENY or word not in _UBO_WORDS for word in words):
        return False
    rest = _UBO_POLITE.sub("", " ".join(words)).split()
    if not rest or rest[0] in _UBO_YES_NO:
        return False
    found = set(words)
    if any(words.count(word) > MAX_UBO_REPEATS for word in found - _UBO_ARTICLES):
        return False  # padding or a repeated request, not a question
    if not found & _UBO_ANCHOR:
        return False
    if "who" in found and not found & _UBO_CANDIDATE:
        return False  # "Who are the UBOs?" asks for a determination (OWNERS), not this
    return bool(found & _UBO_CUE) or bool(
        found & _UBO_CANDIDATE and found & {"who", "which", "what"}
    )


def _exact_other_intent(question: str) -> bool:
    text = _normalise(question)
    return any(
        text in questions for kind, questions in _QUESTIONS.items() if kind != UBO_CALCULATION
    )


def asks_ubo_calculation(question: str) -> bool:
    """The question asks for UBO_CALCULATION (whatever the facts): one of its exact phrasings,
    or admitted by the reviewed classifier when it is no other intent's exact question."""

    if _normalise(question) in _QUESTIONS[UBO_CALCULATION]:
        return True
    return not _exact_other_intent(question) and classify_ubo_calculation(question)


# Per-person results of a completed calculation; REVIEW_REQUIRED and INDETERMINATE are not.
_CALCULATED = frozenset({"PROVISIONAL_UBO_CANDIDATE", "BELOW_PROVISIONAL_THRESHOLD"})
# UBO-R1 (owner decision U-3): under accepted POC basis a person may also be under review.
# INDETERMINATE is never admitted.
_REVIEWED = _CALCULATED | {"REVIEW_REQUIRED"}
# copilot.ownership_facts bounds (kept equal there): a list at its bound may have been cut.
MAX_PATHS = 6
MAX_ISSUES = 10


def _complete_person(person: Any, allowed: frozenset[str]) -> bool:
    """Every figure and path of this person is present and nothing was cut."""

    if not isinstance(person, dict) or person.get("classification") not in allowed:
        return False
    figures = ("aggregated_percent", "direct_percent", "indirect_percent")
    if any(person.get(key) is None for key in figures):
        return False
    paths = person.get("paths")
    return (
        isinstance(paths, list)
        and 0 < len(paths) < MAX_PATHS
        and all(
            isinstance(path, dict)
            and not path.get("links_not_shown")
            and (path.get("calculation") or path.get("effective_percent") is not None)
            for path in paths
        )
    )


def ubo_review_admission(facts: dict[str, Any]) -> bool:
    """UBO-R1: the analysis is REVIEW_REQUIRED and the backend reports that it accepts the POC basis
    (``poc_basis_accepted``, never inferred here)."""

    ownership = facts.get("ownership")
    return (
        isinstance(ownership, dict)
        and ownership.get("analysis_state") == "REVIEW_REQUIRED"
        and ownership.get("poc_basis_accepted") is True
    )


_DECIDED = frozenset({"MET", "NOT_MET"})


def ubo_advisory_admission(facts: dict[str, Any]) -> bool:
    """D-145 (F-6): the analysis is REVIEW_REQUIRED, not POC-accepted, and the
    backend's own D-121 advisory verdict holds for this same analysis: ``review_advisory``
    (copilot.advisory_review_current, which matches the readiness ``reference_id`` to the
    ``analysis_id``) and readiness showing ownership as REVIEW_ADVISED (D-141). Both are read,
    never inferred; every person must also carry a decided threshold comparison from the backend
    (the formal result, else the assumed-POC-basis one), so indeterminate ownership stays out."""

    ownership = facts.get("ownership")
    readiness = facts.get("readiness")
    sections = readiness.get("sections") if isinstance(readiness, dict) else None
    people = ownership.get("people") if isinstance(ownership, dict) else None
    return (
        isinstance(ownership, dict)
        and ownership.get("analysis_state") == "REVIEW_REQUIRED"
        and ownership.get("poc_basis_accepted") is not True
        and ownership.get("review_advisory") is True
        and isinstance(sections, dict)
        and sections.get("ownership") == "REVIEW_ADVISED"
        and isinstance(people, list)
        and all(
            isinstance(person, dict)
            and (
                person.get("threshold_result") in _DECIDED
                or person.get("assumed_basis_threshold_result") in _DECIDED
            )
            for person in people
        )
    )


def ubo_calculation_ready(facts: dict[str, Any]) -> bool:
    """The ownership projection holds a complete calculation to explain: available (not absent
    or withheld, D-142 R2); ANALYZED, or REVIEW_REQUIRED under the backend's accepted POC
    acceptance (UBO-R1) or its D-121 advisory verdict for the same analysis (D-145); with its
    threshold; at least one person and nobody left out; every person with an aggregated, direct
    and indirect percentage and at least one complete path, no list cut at its bound, and nobody
    INDETERMINATE. Under ANALYZED every person is a provisional candidate or below the
    threshold; under UBO-R1 or D-145 a person may be under review."""

    ownership = facts.get("ownership")
    if not isinstance(ownership, dict) or ownership.get("available") is not True:
        return False
    if ownership.get("analysis_state") == "ANALYZED":
        allowed = _CALCULATED
    elif ubo_review_admission(facts) or ubo_advisory_admission(facts):
        allowed = _REVIEWED
    else:
        return False
    people = ownership.get("people")
    issues = ownership.get("issues")
    return (
        ownership.get("threshold_percent") is not None
        and not ownership.get("people_not_shown")
        and (issues is None or (isinstance(issues, list) and len(issues) < MAX_ISSUES))
        and isinstance(people, list)
        and bool(people)
        and all(_complete_person(person, allowed) for person in people)
    )


# Why a question was not sent (content-free; recorded and shown as a closed reason code).
UNSUPPORTED = "INTENT_UNSUPPORTED"
AMBIGUOUS = "INTENT_AMBIGUOUS"


@dataclass(frozen=True)
class Intent:
    kind: str
    fields: tuple[str, ...] = ()

    @property
    def question(self) -> str:
        template = CANONICAL[self.kind]
        if self.kind == DIFFERENCE:
            return template.format(fields=" and ".join(self.fields))
        return template


@dataclass(frozen=True)
class Recognised:
    """The intent, or None with the closed reason (UNSUPPORTED or AMBIGUOUS)."""

    intent: Intent | None
    reason: str | None = None


def difference_fields(facts: dict[str, Any]) -> tuple[str, ...]:
    """The case's own closed set of difference fields (rows with a value on either side)."""

    found: list[str] = []
    for blocker in facts.get("blockers") or []:
        for row in blocker.get("differences") or []:
            if row.get("registry_value") or row.get("document_value"):
                field = str(row.get("field") or "")
                if field in _REVIEWED_FIELDS and field not in found:
                    found.append(field)
    return tuple(found)


def _match(facts: dict[str, Any], question: str) -> Recognised:
    text = _normalise(question)
    difference = _DIFFERENCE_QUESTION.fullmatch(text)
    if difference:
        bound = difference.group(1).split(" and ")
        fields = tuple(field for field in difference_fields(facts) if field.lower() in bound)
        if len(fields) == len(bound):
            return Recognised(Intent(DIFFERENCE, fields))
        return Recognised(None, UNSUPPORTED)

    kinds = {kind for kind, questions in _QUESTIONS.items() if text in questions}
    company = (facts.get("company") or {}).get("legal_name")
    if isinstance(company, str) and company and text == _normalise(f"Why is {company} blocked?"):
        kinds.add(BLOCKERS)
    if not kinds and classify_ubo_calculation(question):
        # U-1/U-2: the reviewed classifier, only for UBO_CALCULATION and only when no exact
        # question of any intent matched. Its canonical question is what is sent.
        kinds.add(UBO_CALCULATION)
    if len(kinds) != 1:
        return Recognised(None, AMBIGUOUS if kinds else UNSUPPORTED)

    kind = kinds.pop()
    if (
        (kind == BLOCKERS and not facts.get("blockers"))
        or (kind == OWNERS and not _ownership_required(facts))
        or (kind == UBO_COMPLETION and not ubo_completion_not_offered(facts))
        or (kind == REGISTRY_SOURCE and registry_source_line(facts, acra_only=True) is None)
        or (kind == UBO_CALCULATION and not ubo_calculation_ready(facts))
    ):
        return Recognised(None, UNSUPPORTED)
    return Recognised(Intent(kind))


def recognise(facts: dict[str, Any], question: str) -> Recognised:
    """The supported intent of this case question on these facts, or None with the reason.

    The intent is kept only when its canonical question is a fixed point (recognised again as
    the same intent) and the topic plan holds allowed lines for it."""

    found = _match(facts, question)
    intent = found.intent
    if intent is None:
        return found
    canonical = intent.question
    if _match(facts, canonical).intent != intent or topic_plan(facts, canonical) is None:
        return Recognised(None, UNSUPPORTED)
    return found


# Why a Try preview never goes to an external model (it carries Support's unsaved rule).
TRY_LOCAL = "TRY_LOCAL_ONLY"
# The fixed user turn of an external prompt that may not be sent (remote_gate refuses it first;
# the boundary would refuse anything else). It is service text, never the person's question.
NOT_SENT = "No question is sent."
