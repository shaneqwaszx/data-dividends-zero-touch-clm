"""Match complete case questions to service-written questions for external models."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .guardrails import registry_source_line, ubo_completion_not_offered
from .guide import FIELD_LABEL
from .prompts import _ownership_required, topic_plan

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
}

# Complete variants of the same supported request. The local topic matchers are intentionally
# broader and cannot be used as external admission evidence.
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
    if len(kinds) != 1:
        return Recognised(None, AMBIGUOUS if kinds else UNSUPPORTED)

    kind = kinds.pop()
    if (
        (kind == BLOCKERS and not facts.get("blockers"))
        or (kind == OWNERS and not _ownership_required(facts))
        or (kind == UBO_COMPLETION and not ubo_completion_not_offered(facts))
        or (kind == REGISTRY_SOURCE and registry_source_line(facts, acra_only=True) is None)
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
