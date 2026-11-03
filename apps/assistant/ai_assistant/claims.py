"""Structured claims in a free-form answer, checked against the application's own records.

D-115 (proposed), refinement 2. Model-independent: the same checks apply whichever model wrote
the answer. Used by the copilot guard (copilot.py), which runs with a local model only.

    relationships    "X holds N% of Y" (or "Y is N% owned by X") must be a link or an interest
                     in the application's ownership calculation, in that direction; a path
                     named with "via"/"through" must run through that party
    classifications  a person said to be a UBO (candidate) or to meet the threshold, or said
                     not to be one or to be below it, must agree with the application's result
    negations        a whole sentence of a closed form ("The UBO has not been officially
                     verified.", "Neither source automatically wins.", "The case remains
                     blocked until ownership is confirmed.") asserts no authority

Every check here only removes a sentence, except ``negated_sentence``: it lets the guard keep a
sentence the shared checks removed for an authority or Live claim, only when the whole sentence
is one of a few fixed forms with a fixed subject and nothing else. Nothing here recalculates a
figure.
"""

from __future__ import annotations

import re
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

    words = [re.sub(r"'S?$", "", word) for word in re.findall(r"[A-Z0-9&']+", text.upper())]
    return " ".join(SUFFIX_FORMS.get(word, word) for word in words if word)


def _alias_pattern(alias: str) -> str:
    parts = []
    for word in alias.split():
        spellings = [word, *(long for long, short in SUFFIX_FORMS.items() if short == word)]
        parts.append("(?:" + "|".join(re.escape(s) for s in spellings) + r")\.?")
    # A possessive ("PRIYA NAIR's") is the same party.
    return r"(?<![\w'])" + r"[\s,]+".join(parts) + r"(?!\w)(?!['’](?![sS]\b))"


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
    r"|stake|interest)\b|'s?\b",
    re.I,
)
_OF_IN = re.compile(r"\b(?:of|in)\b", re.I)
_PASSIVE_BY = re.compile(r"\b(?:owned|held|controlled)\s+by\s*$", re.I)
_BY = re.compile(r"\s*by\s*", re.I)
_OWNED_BY_NO_FIGURE = re.compile(
    r"['’]s?\s+(?:whole\s+|entire\s+)?(?:stake|interest|holding|shareholding|shares)\s+"
    r"(?:belongs?\s+to|(?:is|are)\s+(?:held|owned)\s+by)\s+",
    re.I,
)
# A second clause with its subject left out ("... of GARDEN and indirectly holds 10% ...").
_ELIDED = re.compile(r"\s*,?\s*(?:and|but|while|whereas)\b", re.I)
_BELONGS = re.compile(
    r"\s*(?:stake|interest|holding|shareholding)?\s*(?:belongs to|is held by|is owned by)\s*",
    re.I,
)
_PASSIVE_VERB = re.compile(r"\b(?:owned|held|controlled)\b", re.I)
_PASSIVE_AFTER = re.compile(
    # "50% of GARDEN is held by ALPHA", "KESTREL's 50% stake in GARDEN belongs to DANIEL"
    r"^\s*(?:(?:is|are|was|were)?\s*(?:owned|held|controlled)\s+by|belongs?\s+to)\s+",
    re.I,
)
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
        # "PRIYA's stake belongs to AISHA" (no figure): that holding must exist, that way round.
        for first, second in zip(mentions, mentions[1:], strict=False):
            if _OWNED_BY_NO_FIGURE.fullmatch(part[first.end : second.start]) and not (
                graph.edges.get((second.key, first.key))
                or graph.allowed(second.key, first.key)
            ):
                return "unsupported_relationship"
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
            subject = before[-1] if before else None
            if (
                subject is not None
                and len(before) > 1
                and _ELIDED.match(part[subject.end : match.start()])
            ):
                subject = before[-2]  # "NG holds 15% of GARDEN and holds 10% via BETA"
            passive_before = (
                bool(before)
                and _BY.fullmatch(gap) is not None
                and _PASSIVE_VERB.search(part[before[-1].end : match.start()]) is not None
            )
            if before and _BELONGS.fullmatch(gap):
                # "MERIDIAN's 100% stake belongs to PRIYA": PRIYA holds 100% of MERIDIAN.
                holder, held = first_after.key, before[-1].key
            elif _PASSIVE_BY.search(gap) or passive_before:
                # "GARDEN is 50% owned by ALPHA", "GARDEN is owned 50% by ALPHA"
                holder = first_after.key
                held = before[-1].key if before else None
            elif _OF_IN.search(gap):
                tail = part[first_after.end :]
                passive = _PASSIVE_AFTER.match(tail)
                if passive and len(after) > 1:  # "50% of GARDEN is held by ALPHA"
                    holder, held = after[1].key, first_after.key
                elif subject is not None:  # "ALPHA holds 50% of GARDEN"
                    between = part[subject.end : match.start()]
                    if _HOLDING_VERB.search(between) and not _CONTRASTED.search(between):
                        holder, held = subject.key, first_after.key
            elif subject is not None and _VIA_GAP.fullmatch(gap):
                # "PRIYA holds 20% through MERIDIAN": an interest in the company, by that path.
                between = part[subject.end : match.start()]
                if _HOLDING_VERB.search(between) and not _CONTRASTED.search(between):
                    holder, held = subject.key, graph.root
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
    # not "the UBO status is ...", "the UBO check is ...": those are about the check
    r"(?!\s+(?:status|check|checks|threshold|analysis|result|section|review|rules?)\b)"
    r"(?:\s*:|\b[^.;]{0,60}?\b(?:are|is|include|includes|would be"
    r"|(?:appear|appears|seem|seems) to be)\b)",
    re.I,
)
_SEGMENT = re.compile(
    r",?\s*\b(?:but|however|whereas|while|although|unlike|except|excluding)\b|,\s*not\b"
    r"|\band not\b",
    re.I,
)


_OPEN_QUESTION = re.compile(r"\b(?:whether|if)\b(?:\W+\w+){0,3}\W*$", re.I)
# Only a conjunction between two people: they share one claim.
_JOINED = re.compile(
    r"\s*,?\s*(?:and|or|as well as|&|like|just like|along with|together with)?\s*,?\s*"
    r"(?:and|or)?\s*",
    re.I,
)
# "Unlike TAN, LIM is ...", "LIM and NG, except TAN, ...": the contrasted name is left out.
_CONTRASTED_PHRASE = re.compile(
    r"\b(?:unlike|except(?: for)?|excluding|rather than|other than)\b([^,;]*)", re.I
)
_NEITHER_NOR = re.compile(r"^\W*neither\b.*\bnor\b", re.I)


def _segments(clause: str) -> list[str]:
    # "not only/just X but (also) Y" lists both: no split at that "but".
    if re.search(r"\bnot (?:only|just)\b", clause, re.I):
        clause = re.sub(r"\bbut( also)?\b", "and", clause, flags=re.I)
    # A contrasted phrase is a segment of its own: a claim inside it is still judged, and the
    # name in it is not joined to the next ("Unlike TAN, LIM is ...").
    chunks = _CONTRASTED_PHRASE.sub(lambda m: "\x00" + m.group(1) + "\x00", clause).split("\x00")
    return [segment for chunk in chunks for segment in _SEGMENT.split(chunk)]


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
                if _NEITHER_NOR.match(segment):
                    # "Neither X nor Y is a UBO candidate": not a UBO; "Neither X nor Y is
                    # below the threshold" (or "fails to meet it"): both meet it.
                    if _BELOW.search(segment):
                        claims[index] = "positive"
                    elif _POSITIVE.search(segment):
                        claims[index] = "not_a_ubo"
                elif _OPEN_QUESTION.search(segment[: person.start][-40:]):
                    claims[index] = None  # "whether OMAR is a UBO" asks; it claims nothing
                elif found:
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

# Whole sentences only, from a closed vocabulary: a fixed subject, a negated or conditional
# authority phrase, nothing else. No clause is split off, nothing is rewritten and no remainder
# is judged on its own (two earlier designs that did so let a current claim through: "had not
# been verified until today", "Compliance has verified the UBO so the case cannot proceed until
# the address is confirmed"). Anything else stays left out (fail closed).
_SUBJECT = (
    r"(?:the |this |that |its |their |his |her )?(?:ubo|ubos|ubo status|ubo result|ubo check"
    r"|beneficial ownership|ownership|ownership result|ownership analysis|analysis|result"
    r"|calculation|case|record|registry record|document|address|registered address"
    # No negative subject ("no UBO status"): with the form's own "not" it would say the
    # opposite ("No UBO status has not been verified" claims every one is verified).
    r"|candidate|candidates)"
)
_AUTHORITY_WORD = r"(?:verified|confirmed|approved|certified)"
_OFFICIALLY = r"(?: (?:officially|legally|formally|independently))?"
_NEGATED_SENTENCES = tuple(
    re.compile(pattern)
    for pattern in (
        # "No, the UBO has not been officially verified (yet)."
        rf"^{_SUBJECT} (?:has not|hasn't|have not|haven't|is not|isn't|are not|aren't)"
        rf"(?: yet)?(?: been)?{_OFFICIALLY} {_AUTHORITY_WORD}(?: yet)?$",
        # "No UBO status is verified yet."
        rf"^(?:no ubo status|no ubo|none of them|neither of them|neither candidate) (?:is|are)"
        rf"(?: yet)?{_OFFICIALLY} {_AUTHORITY_WORD}(?: yet)?$",
        # "Neither source automatically wins (over the other)."
        r"^neither (?:source|value|record|the registry nor the document|the document nor the "
        r"registry|the acra record nor the document) (?:automatically |simply )?(?:wins|overrides"
        r"|takes precedence)(?: over the other| the other)?$",
        # "It does not mean she is officially verified (or approved)."
        r"^(?:it|this|that) (?:does not|doesn't) (?:mean|imply) (?:that )?(?:she|he|they|it"
        rf"|the ubo|the person|the candidate|anyone) (?:is|are){_OFFICIALLY} {_AUTHORITY_WORD}"
        rf"(?: or {_AUTHORITY_WORD})?$",
        # "It is not a final KYC or regulatory approval."
        r"^(?:it|this|that|the result|the analysis) is not (?:a |an )?(?:final |formal "
        r"|official )?(?:kyc|regulatory|compliance)(?: or (?:kyc|regulatory|compliance))? "
        r"(?:approval|clearance)$",
        # "The case remains blocked until ownership is confirmed."
        r"^(?:the case|this case|it|the ubo check|the review|the submission|onboarding) (?:remains"
        r"|stays|is|will remain|cannot proceed|cannot move forward|cannot be acted on|cannot be"
        r" submitted)(?: blocked| paused| pending| on hold)? until (?:the )?(?:ownership"
        r"|ownership evidence|ubo|ubo check|address|registered address|document|documents"
        r"|ownership declaration) (?:is|are|has been|have been) (?:confirmed|verified|reviewed)$",
        # "The check has not run in a live environment."
        r"^(?:the check|the analysis|the case|the data|this data|the registry data|the result)"
        r" (?:has not|hasn't|is not|isn't|was not|wasn't) (?:run in|connected to|from|tested in)"
        r" (?:a |an |the )?(?:live|production) (?:environment|system|registry|acra registry"
        r"|connection|service)$",
    )
)
_LEAD = re.compile(r"^(?:no|so),\s+", re.I)


def negated_sentence(sentence: str) -> bool:
    """True when the whole sentence is one of the closed negated or conditional forms above,
    and so asserts no authority, verification, approval or Live claim."""

    text = _LEAD.sub("", " ".join(sentence.lower().replace("\u2019", "'").split()))
    text = text.strip().rstrip(".!")
    return any(form.fullmatch(text) for form in _NEGATED_SENTENCES)
