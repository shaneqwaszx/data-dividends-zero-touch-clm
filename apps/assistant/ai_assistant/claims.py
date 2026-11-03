"""Structured claims in a free-form answer, checked against the application's own records.

D-115 (proposed), refinement 2. Model-independent: the same checks apply whichever model wrote
the answer. Used by the copilot guard (copilot.py), which runs with a local model only.

    relationships    "X holds N% of Y" (or "Y is N% owned by X") must be a link or an interest
                     in the application's ownership calculation, in that direction; a path
                     named with "via"/"through" must run through that party
    classifications  a person said to be a UBO (candidate) or to meet the threshold, or said
                     not to be one or to be below it, must agree with the application's result
    negations        a clause that only says something has NOT been verified, confirmed or
                     approved (present tense, nothing after it), "neither source automatically
                     wins", or a condition still to be met ("blocked until ownership is
                     confirmed") asserts no authority; the rest of the sentence is checked whole

Every check here only removes a sentence, except ``negated_clauses_only``: it lets the guard
keep a sentence the shared checks removed for an authority or Live claim, and only when every
such claim sits in a clause proven to be one of those forms, no time or exception word
appears anywhere ("until today", "now", "anyone but"), and the sentence without those clauses
passes every check. Nothing here recalculates a figure.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

# --- names ----------------------------------------------------------------------------------

# Spellings of the same recognised company suffix. Only these, punctuation, spacing and
# capitals are treated as presentation: "Example Pte. Ltd." and "EXAMPLE PRIVATE LIMITED" are
# one name; "ACME HOLDING" and "ACME HOLDINGS" are not. No fuzzy matching.
SUFFIX_FORMS = {
    "PRIVATE": "PTE",
    "LIMITED": "LTD",
    "BERHAD": "BHD",
    "INCORPORATED": "INC",
    "CORPORATION": "CORP",
}
SUFFIXES = frozenset({"PTE", "LTD", "LLP", "LLC", "INC", "BHD", "CORP"})
# First words too common to stand for a company on their own.
_COMMON_FIRST = frozenset(
    {
        "THE", "ASIA", "GLOBAL", "GROUP", "HOLDINGS", "INTERNATIONAL", "NEW", "FIRST",
        "UNITED", "GENERAL", "CAPITAL", "TRADING", "PACIFIC", "SINGAPORE", "COMPANY",
    }
)


def canonical_name(text: str) -> str:
    """A name with capitals, punctuation, spacing and suffix spelling set aside, for an exact
    comparison of the words that remain (never a similarity score)."""

    words = [re.sub(r"'S$", "", word) for word in re.findall(r"[A-Z0-9&']+", text.upper())]
    return " ".join(SUFFIX_FORMS.get(word, word) for word in words if word)


def _alias_pattern(alias: str) -> str:
    parts = []
    for word in alias.split():
        spellings = [word, *(long for long, short in SUFFIX_FORMS.items() if short == word)]
        parts.append("(?:" + "|".join(re.escape(s) for s in spellings) + r")\.?")
    return r"(?<![\w'])" + r"[\s,]+".join(parts) + r"(?![\w'])"


# --- the ownership graph ----------------------------------------------------------------------


def _number(value: Any) -> Decimal | None:
    with suppress(InvalidOperation, TypeError, ValueError):
        number = Decimal(str(value)).normalize()
        return number if number.is_finite() else None
    return None


@dataclass(frozen=True)
class Mention:
    start: int
    end: int
    key: str


class OwnershipGraph:
    """Who holds what, as the application calculated it (copilot ``ownership_facts``)."""

    def __init__(self, ownership: Any, company_name: str | None) -> None:
        self.edges: dict[tuple[str, str], set[Decimal]] = {}
        self.interests: dict[str, set[Decimal]] = {}
        self.paths: dict[str, set[str]] = {}  # person -> every party on their paths
        self.results: dict[str, str] = {}  # person -> "MET", "NOT_MET" or "UNDETERMINED"
        self.persons: set[str] = set()
        names: dict[str, str] = {}  # key -> display name
        people = ownership.get("people") if isinstance(ownership, dict) else None
        for person in people or []:
            if not isinstance(person, dict) or not person.get("name"):
                continue
            key = canonical_name(str(person["name"]))
            names[key] = str(person["name"])
            self.persons.add(key)
            values = {
                _number(person.get(field))
                for field in ("direct_percent", "indirect_percent", "aggregated_percent")
            }
            on_path: set[str] = set()
            for path in person.get("paths") or []:
                values.add(_number(path.get("effective_percent")))
                for link in path.get("links") or []:
                    holder = canonical_name(str(link.get("holder") or ""))
                    held = canonical_name(str(link.get("held") or ""))
                    percent = _number(link.get("ownership_percent"))
                    if holder and held and percent is not None:
                        self.edges.setdefault((holder, held), set()).add(percent)
                        names.setdefault(holder, str(link.get("holder")))
                        names.setdefault(held, str(link.get("held")))
                        on_path |= {holder, held}
            self.interests[key] = {value for value in values if value is not None}
            self.paths[key] = on_path
            met = person.get("threshold_result")
            provisional = person.get("classification") == "PROVISIONAL_UBO_CANDIDATE"
            self.results[key] = (
                "MET" if met == "MET" and provisional else "NOT_MET" if met == "NOT_MET"
                else "UNDETERMINED"
            )
        holders = {holder for holder, _ in self.edges}
        roots = {held for _, held in self.edges} - holders
        company = canonical_name(company_name or "")
        self.root = company if company in roots or not roots else sorted(roots)[0]
        if company and company not in names:
            names[company] = company_name or company
        self._patterns: list[tuple[re.Pattern[str], str]] = []
        firsts: dict[str, int] = {}
        for key in names:
            if key not in self.persons:
                firsts[key.split()[0]] = firsts.get(key.split()[0], 0) + 1
        aliases: list[tuple[str, str]] = []
        for key in names:
            aliases.append((key, key))
            if key in self.persons:
                continue
            bare = " ".join(w for w in key.split() if w not in SUFFIXES)
            if bare and bare != key:
                aliases.append((bare, key))
            first = key.split()[0]
            if len(first) >= 4 and first not in _COMMON_FIRST and firsts.get(first) == 1:
                aliases.append((first, key))
        if company:
            aliases.append(("THE COMPANY", self.root))
            if company != self.root:
                aliases.append((company, self.root))
        for alias, key in sorted(aliases, key=lambda item: -len(item[0])):
            self._patterns.append((re.compile(_alias_pattern(alias), re.I), key))

    @property
    def empty(self) -> bool:
        return not self.edges and not self.persons

    def mentions(self, text: str) -> list[Mention]:
        """Every party named in ``text``, longest name first, without overlaps."""

        found: list[Mention] = []
        for pattern, key in self._patterns:
            for match in pattern.finditer(text):
                if all(match.end() <= m.start or match.start() >= m.end for m in found):
                    found.append(Mention(match.start(), match.end(), key))
        return sorted(found, key=lambda m: m.start)

    def allowed(self, holder: str, held: str) -> set[Decimal]:
        values = set(self.edges.get((holder, held), ()))
        if held == self.root and holder in self.persons:
            values |= self.interests.get(holder, set())
        return values


# --- P1: relationships --------------------------------------------------------------------------

_PERCENT = re.compile(r"(\d{1,3}(?:\.\d+)?)\s?(?:%|per ?cent\b)", re.I)
_HOLDING_VERB = re.compile(
    r"\b(?:hold|holds|holding|held|own|owns|owning|has|have|having|with|controls?|controlling"
    r"|stake|interest)\b|'s?\b|[(:]",
    re.I,
)
_OF_IN = re.compile(r"\b(?:of|in)\b", re.I)
_PASSIVE_BY = re.compile(r"\b(?:owned|held|controlled)\s+by\s*$", re.I)
_PASSIVE_AFTER = re.compile(r"^\s*(?:is|are|was|were)?\s*(?:owned|held|controlled)\s+by\s+", re.I)
_VIA = re.compile(r"\b(?:via|through)\s+$", re.I)
_VIA_GAP = re.compile(r"\s*(?:\w+ly\s+)?(?:via|through)\s+", re.I)
_CONTRASTED = re.compile(r"\b(?:unlike|except|not|rather than|whereas|instead of)\b", re.I)


def relationship_problem(sentence: str, graph: OwnershipGraph) -> str | None:
    """Why a stated holding is not the application's, if it is not ("ALPHA holds 80% of
    ALPHA", "ALPHA owns 80% of LIM", "TAN holds 10% of ALPHA", or a path through a party
    that is not on it)."""

    for part in sentence.split(";"):
        mentions = graph.mentions(part)
        if not mentions:
            continue
        percents = list(_PERCENT.finditer(part))
        for match in percents:
            value = _number(match.group(1))
            before = [m for m in mentions if m.end <= match.start()]
            after = [m for m in mentions if m.start >= match.end()]
            if not after or value is None:
                continue
            first_after = after[0]
            gap = part[match.end() : first_after.start]
            if _PERCENT.search(gap) or len(gap.split()) > 6:
                continue
            holder = held = None
            if _PASSIVE_BY.search(gap):  # "GARDEN is 50% owned by ALPHA"
                holder = first_after.key
                held = before[-1].key if before else None
            elif _OF_IN.search(gap):
                tail = part[first_after.end :]
                passive = _PASSIVE_AFTER.match(tail)
                if passive and len(after) > 1:  # "50% of GARDEN is held by ALPHA"
                    holder, held = after[1].key, first_after.key
                elif before:  # "ALPHA holds 50% of GARDEN"
                    between = part[before[-1].end : match.start()]
                    if _HOLDING_VERB.search(between) and not _CONTRASTED.search(between):
                        holder, held = before[-1].key, first_after.key
            elif before and _VIA_GAP.fullmatch(gap):
                # "PRIYA holds 20% through MERIDIAN": an interest in the company, by that path.
                between = part[before[-1].end : match.start()]
                if _HOLDING_VERB.search(between) and not _CONTRASTED.search(between):
                    holder, held = before[-1].key, graph.root
                    if holder in graph.persons and first_after.key not in graph.paths.get(
                        holder, set()
                    ):
                        return "unsupported_relationship"
            if holder is None or held is None:
                continue
            if holder == held or value not in graph.allowed(holder, held):
                return "unsupported_relationship"
            # "... through ALPHA": the named party must be on the holder's paths (up to the
            # next person named, who starts a statement of their own).
            for mention in after[1:]:
                if mention.key in graph.persons:
                    break
                if (
                    _VIA.search(part[: mention.start])
                    and holder in graph.persons
                    and mention.key not in graph.paths.get(holder, set())
                ):
                    return "unsupported_relationship"
    return None


# --- P2: classifications ------------------------------------------------------------------------

# Said of the person named before it ("LIM is a provisional UBO candidate", "NG meets the
# threshold") or, for a list, of the people named after it ("The UBOs are LIM and NG").
_POSITIVE = re.compile(
    r"\b(?:is|are|be|as|being)\b(?:\s+(?!not\b|never\b|no\b)[\w'-]+){0,3}?\s+(?:a |an |the )?"
    r"(?:provisional |likely |possible |potential )?(?:ubos?|ultimate beneficial owners?"
    r"|beneficial owners?)\b"
    r"|\b(?:meets?|meeting|met|exceeds?|exceeding|reach(?:es|ing)?|satisf(?:y|ies|ying)"
    r"|at or above|above|over)\b[^.;]{0,25}\bthreshold\b"
    r"|\bqualif(?:y|ies|ying)\b|\bprovisional (?:ubo )?candidates?\b|\bubo candidates?\b",
    re.I,
)
# Said not to be a UBO (candidate). For a person whose result could not be determined this is
# true, not a contradiction; only a threshold claim (_BELOW) contradicts that result.
_NOT_A_UBO = re.compile(
    r"\bnot (?:a |an |the |one of the )?(?:provisional )?(?:ubos?|ultimate beneficial owners?"
    r"|beneficial owners?|candidates?)\b"
    r"|\b(?:isn't|aren't|is not|are not) (?:considered |treated as |classified as |counted as )?"
    r"(?:a |an |the )?(?:provisional )?(?:ubo|beneficial owner|candidate)"
    r"|\b(?:does not|doesn't|do not|don't|did not|would not|wouldn't|cannot|can't|never)"
    r" (?:count|counts|qualify|rank|serve)\b"
    r"|\bnot (?:counted|considered|treated|classified|regarded)\b",
    re.I,
)
_BELOW = re.compile(
    r"\b(?:below|under|less than|short of|beneath)\b(?: the)?(?: \d+(?:\.\d+)?\s?%)?"
    r"(?: provisional| configured| inclusive| ubo)? threshold\b"
    r"|\b(?:does not|doesn't|do not|don't|did not|fails? to|falls? short of) "
    r"(?:meet|reach|exceed|satisfy)\b|\bfalls? below\b",
    re.I,
)
_LIST = re.compile(
    r"\b(?:ubos?|ultimate beneficial owners?|beneficial owners?)(?: candidates?)?"
    r"(?:\s*:|\b[^.;]{0,60}?\b(?:are|is|include|includes|would be"
    r"|(?:appear|appears|seem|seems) to be)\b)",
    re.I,
)
_SEGMENT = re.compile(
    r",?\s*\b(?:but|however|whereas|while|although|unlike|except|excluding)\b|,\s*not\b"
    r"|\band not\b",
    re.I,
)


# Only a conjunction between two people: they share one claim.
_JOINED = re.compile(r"\s*(?:,|and|or|as well as|&)?\s*(?:,\s*)?(?:and|or)?\s*", re.I)


def _segments(clause: str) -> list[str]:
    # "not only/just X but (also) Y" lists both: no split at that "but".
    if re.search(r"\bnot (?:only|just)\b", clause, re.I):
        clause = re.sub(r"\bbut( also)?\b", "and", clause, flags=re.I)
    return _SEGMENT.split(clause)


def classification_problem(sentence: str, graph: OwnershipGraph) -> str | None:
    """A person said to be a UBO or to meet the threshold whom the application found below
    it (or could not determine), or said to be below it whom the application found to meet
    it, whatever the sentence order."""

    for clause in sentence.split(";"):
        for segment in _segments(clause):
            people = [m for m in graph.mentions(segment) if m.key in graph.persons]
            if not people:
                continue
            listed = _LIST.search(segment)
            claims: list[str | None] = [None] * len(people)
            # Right to left: each person takes the nearest claim before the next person; in
            # "TAN and LIM meet the threshold" TAN shares LIM's claim.
            for index in range(len(people) - 1, -1, -1):
                person = people[index]
                following = people[index + 1] if index + 1 < len(people) else None
                rest = segment[person.end : following.start if following else len(segment)]
                found = [
                    (match.start(), claim)
                    for claim, match in (
                        ("positive", _POSITIVE.search(rest)),
                        ("below", _BELOW.search(rest)),
                        ("not_a_ubo", _NOT_A_UBO.search(rest)),
                    )
                    if match
                ]
                if found:
                    # The first claim after the person; a negation before a positive phrase
                    # ("does not count as a provisional UBO") is the claim.
                    claims[index] = min(found)[1]
                elif following is not None and _JOINED.fullmatch(rest):
                    claims[index] = claims[index + 1]
                elif listed and listed.end() <= person.start:
                    claims[index] = "positive"
            for person, claim in zip(people, claims, strict=True):
                result = graph.results.get(person.key)
                if claim == "positive" and result in ("NOT_MET", "UNDETERMINED"):
                    return "ubo_contradicts_calculation"
                if claim == "below" and result in ("MET", "UNDETERMINED"):
                    return "ubo_contradicts_calculation"
                if claim == "not_a_ubo" and result == "MET":
                    return "ubo_contradicts_calculation"
    return None


# --- P3: negations and conditions --------------------------------------------------------------

_AUTHORITY_WORD = r"(?:verified|confirmed|approved|certified|cleared)"
_NEGATED_FORMS = (
    # "The UBO has not been officially verified." (present tense; nothing after it)
    re.compile(
        r"^(?:[\w'.&-]+ ){0,8}?(?:has|have|is|are)(?: not|n't)(?: yet)?(?: been)?"
        rf"(?: (?:officially|legally|formally|independently))? {_AUTHORITY_WORD}(?: yet)?$"
    ),
    # "It does not mean she is officially verified or approved."
    re.compile(
        r"^(?:it |this |that )?(?:does not|doesn't) (?:mean|imply|show) (?:that )?"
        r"(?:[\w'-]+ ){0,4}?(?:is|are|has been|have been) (?:officially |legally |formally )?"
        rf"{_AUTHORITY_WORD}(?: or {_AUTHORITY_WORD})?$"
    ),
    # "It is not a final KYC or regulatory approval."
    re.compile(
        r"^(?:it |this |that |the result |the analysis )?(?:is|are) not (?:a |an )?"
        r"(?:final |formal |official |legal )?(?:kyc|regulatory|compliance|legal)"
        r"(?: or (?:kyc|regulatory|compliance|legal))? (?:approval|clearance|verification)$"
    ),
    # "Neither source automatically wins."
    re.compile(
        r"^(?:neither|no) (?:source|value|record|side|one|of them|[\w-]+ nor (?:the )?[\w-]+)? ?"
        r"(?:automatically |simply )?(?:wins|overrides|takes precedence|replaces)"
        r"(?: the other)?$"
    ),
    # "Neither is officially verified."
    re.compile(
        r"^neither(?: of them| candidate| one| result)? (?:is|are) (?:yet )?"
        rf"(?:officially |formally |legally )?{_AUTHORITY_WORD}(?: yet)?$"
    ),
    # "The check has not run in a live environment." / "This is not live data."
    re.compile(
        r"^(?:[\w'.-]+ ){0,8}?(?:is|are|has|have|does|do)(?: not|n't)(?: been)?"
        r"(?: (?:run|connected|used|tested|sent|submitted))?(?: (?:in|to|on|with|against))?"
        r" (?:a |an |the )?(?:live|production|real) (?:acra|registry|goldtier|system"
        r"|environment|integration|connection|api|data)$"
    ),
)
# "The case remains blocked until ownership is confirmed." The condition ends the clause.
_CONDITION = re.compile(
    r"^.*?\b(?:blocked|cannot|can't|remains?|stays?|must|needs?|requires?|will not|won't"
    r"|pending|waiting|paused|on hold)\b.*? (?:until|unless|before|once|if|when) "
    rf"(?:[\w'.-]+ ){{1,6}}?(?:is|are|has been|have been|gets?) (?:officially |formally "
    rf"|legally |properly )?{_AUTHORITY_WORD}$"
)
# Time and exception words: a "not ... until today" or "by anyone but X" says the opposite.
_VETO = re.compile(
    r"\b(?:now|today|yesterday|tomorrow|tonight|currently|anymore|any longer|no longer"
    r"|already|since|previously|earlier|recently|finally|later|then|again|just|only"
    r"|except|other than|apart from|anyone but|anybody but|no one but|nobody but|someone)\b",
    re.I,
)
_CLAUSE_BREAK = re.compile(r"\s*(?:[;,:—–]|\s-\s|\bbut\b|\band\b)\s*", re.I)
_LEAD = re.compile(r"^(?:no|yes|so|and|but|also),?\s+", re.I)
_NEUTRAL = (
    (re.compile(r"\b(?:officially|legally|formally|independently)\s+", re.I), ""),
    (re.compile(rf"\b{_AUTHORITY_WORD}\b", re.I), "reviewed"),
    (re.compile(r"\b(?:automatically|simply) (?:wins|overrides|takes precedence|replaces)", re.I),
     "applies"),
    (re.compile(r"\b(?:live|production|real)\b", re.I), "test"),
    (re.compile(r"\b(?:kyc|regulatory|compliance|legal) (?:approval|clearance)\b", re.I),
     "review"),
)


def _form(clause: str) -> bool:
    lowered = _LEAD.sub("", " ".join(clause.lower().split()).strip(" .!"))
    return any(form.match(lowered) for form in _NEGATED_FORMS) or bool(_CONDITION.match(lowered))


def negated_clauses_only(sentence: str, check: Callable[[str], str | None]) -> bool:
    """True when every authority or Live claim the checks found sits in a clause proven to
    assert none (see the module notes): the sentence then stays. ``check`` is the guard's own
    full check of a text (None: it passes)."""

    if _VETO.search(sentence):
        return False
    body = sentence.strip()
    spans = []
    start = 0
    for brk in [*_CLAUSE_BREAK.finditer(body), None]:
        end = brk.start() if brk else len(body)
        spans.append((start, end))
        start = brk.end() if brk else len(body)
    proven = [(a, b) for a, b in spans if body[a:b].strip() and _form(body[a:b])]
    if not proven:
        return False
    for a, b in proven:  # the clause's other content (values, labels, contacts) still passes
        neutral = body[a:b]
        for pattern, replacement in _NEUTRAL:
            neutral = pattern.sub(replacement, neutral)
        if check(neutral) is not None:
            return False
    remainder = body
    for a, b in reversed(proven):
        remainder = remainder[:a] + remainder[b:]
    remainder = remainder.strip(" ,;:.—–-")
    return not remainder or check(remainder) is None
