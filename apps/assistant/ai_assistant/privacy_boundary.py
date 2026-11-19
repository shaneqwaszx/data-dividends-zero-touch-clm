"""D-142 (proposed): the privacy boundary on every call to an external model.

Every prompt that leaves for an external model provider (Claude through Anthropic, GPT-OSS
through OpenRouter, a model IT configured on an endpoint that is not literal loopback) passes
through ``outbound`` inside that model's own ``complete``/``stream``, so no caller (case chat,
general chat, Support chat, "Try with this change", dashboard insights, qualification) can skip
it. The reply passes through ``Protected.restore_*`` before the caller sees it, so the existing
claim and safety checks (guardrails.py, claims.py) run unchanged on the real values.

Admission (R1, P1-2)
    The caller that builds the messages (main.py, support_chat.py, the connection probe) calls
    ``admit``: one request-scoped, single-use admission binding the exact messages (by content
    digest), the case's known identities and the caller. It returns the messages as an
    ``AdmittedMessages`` list that carries only an opaque admission id. ``outbound`` consumes the
    admission exactly once, before anything is reserved or sent: missing, consumed, expired,
    evicted or mismatched (the messages changed since) fails closed (PrivacyRefused). A retry
    needs a new admission; it never continues with an empty identity map. Two concurrent
    requests with identical messages hold two admissions and two independent identity maps.
    ``outbound`` then opens one provider call (``ProtectedMessages`` with its call id) whose
    clearance the adapter consumes once, by call id and digest, never by digest alone.

What changes on the way out
    canonical form     NFKC; invisible format characters (zero-width, bidi) removed; literal
                       escape or encoding sequences (\\u0041, \\x41, &#65;, %41%42) refused
                       (ENCODED_INPUT): nothing ambiguous is classified
    known identities   every name and identifier of the case (company, UEN, address, officers,
                       ownership parties, GoldTier id, document names, the user) is replaced
                       with a typed placeholder whatever its length, case or vocabulary status
                       ([COMPANY-A], [PERSON-B], [ID-A], [ADDRESS-A]); each distinctive word of
                       a known name or address is replaced too ("Garden" alone, "tan" alone)
    everything else    a word is kept only when it is in the reviewed privacy vocabulary
                       (privacy_vocabulary.json, the service's own wording minus person-name
                       words). A capitalised word in mid-sentence, and any word in capitals, is
                       kept only when it is one of the service's own terms (GoldTier, ACRA); a
                       capitalised word at the start of a sentence that is also a common first
                       name ("Will", "Mark") is replaced. Any token with more than a small
                       number in it (an NRIC, UEN, phone, postcode, year, a grouped number such
                       as 1,234), any email or web address, and every word not kept is replaced
                       with [TEXT-A] or [ID-A]. Decimals with up to three whole digits and six
                       decimals (the ownership contract's precision: 1.123456) are kept
    validation         before any reservation, ticket or call the final messages are checked
                       again by separate rules: no known value left, no identifier pattern, no
                       token the vocabulary rules would replace, only this call's placeholders.
                       Any failure sends nothing (PrivacyRefused, the case-data answer follows)
    the wire           the adapters (Anthropic, OpenRouter, and an IT adapter once wrapped by
                       BoundedModel) hand the exact serialised HTTP body to ``verify_wire``
                       before sending: every text in it is scanned again with this call's own
                       rules (by role). R2 (D-2): only a call its caller cleared, not yet sent,
                       for exactly its messages, passes, once; anything else is refused
                       R3: the wire also refuses any history and repeats the controlled query
    name words (R2)    every word of a known person's name (two letters or more, except a
                       particle or honorific) is protected too: every occurrence in what a
                       person wrote and in service-built text, only name-like uses in trusted
                       wording (D-3)
    origin (R3)        trusted (fixed wording registered at import, ``trusted_text``), service
                       (any other system text, service-built data) or person (the final user
                       turn): established where a message is built, never by its role
    entities (R2, R3)  distinct ownership parties or registry officers that share a name are
                       written per entity in the external facts, by the backend's party and
                       officer ids, so each has its own placeholder; an officer whose identity
                       cannot be established is omitted, never merged; no model receives an id

What changes on the way back
    Only placeholders that this call actually sent can be restored. A line holding any other
    placeholder (allocated but never sent, invented, from another call), anything shaped like
    one that is not exact ("ID-Z", "[[PERSON-A]]", "PERSON A"), is dropped. Then each placeholder
    becomes its real value, line by line (a streamed line is restored only once complete; a
    cancelled stream discards its unfinished line).

The mapping lives in this process for one call only. It is never sent, logged, stored or put in
telemetry. The ownership figures are the application's own (the backend's Decimal engine): they
are numbers, so they are kept exactly, and the model only explains them.

OD-3 (owner decision of 2026-11-17: ambiguous personal information leakage is not accepted) and
R4 (R3-1, owner Option A of 2026-11-17): nothing a person wrote ever leaves. Every external prompt
is service-built: a case question is recognised locally as one supported intent and sent as its
fixed canonical question (controlled_intents); the admission of any person-written text, or of
text a person wrote placed inside a system message, is refused (PERSON_TEXT), and the wire check
refuses it again (WIRE_PERSON_TEXT). Chat history is never forwarded (``forwarded``).

Residual: in trusted wording, a known name's ordinary word that starts a sentence, is written in
lower case or is a service term is kept. Numbers of up to three digits are kept. This is limited
pseudonymisation, not anonymisation.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import threading
import time
import unicodedata
from collections.abc import AsyncGenerator, AsyncIterator, Iterable, Mapping
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path
from typing import Any

from .llm import LlmUnavailableError, ModelAnswer, Piece, message_bytes

VOCABULARY_FILE = Path(__file__).with_name("privacy_vocabulary.json")

# D-142 Q3: each hosted provider's data-handling policy. synthetic_only is the D-139 R3 check
# (verified synthetic cases only), the default and the rollback; pseudonymised admits an
# authorised case whose data the trusted POC admission classifies as synthetic or Mock POC data
# (synthetic_eligibility.poc_check) and whose prompt passes this boundary.
SYNTHETIC_ONLY = "synthetic_only"
PSEUDONYMISED = "pseudonymised"
DATA_POLICIES = (SYNTHETIC_ONLY, PSEUDONYMISED)
SCHEMA = "clm-assistant-privacy-vocabulary/1"

KINDS = ("COMPANY", "PERSON", "ID", "ADDRESS", "TEXT")
ALIAS = re.compile(r"\[(COMPANY|PERSON|ID|ADDRESS|TEXT)-([A-Z]{1,3})\]")
# Anything a model might write for a placeholder that is not exactly one: a bracket holding a
# kind word in any case, a kind word in capitals followed by letters ("PERSON A", "TEXT_B",
# "ID-Z"), or a placeholder inside a second pair of brackets ("[[PERSON-A]]").
_ALIAS_LIKE_STRICT = re.compile(
    r"\[\s*(?:company|person|id|address|text)\b[^\]\n]{0,16}\]", re.IGNORECASE
)
_ALIAS_LIKE_BARE = re.compile(
    r"\b(?:COMPANY|PERSON|ADDRESS|TEXT)[\s_-]?[A-Z]{1,3}\b|\bID[_-][A-Z]{1,3}\b"
)
_ALIAS_WRAPPED = re.compile(
    r"\[\s*\[(?:COMPANY|PERSON|ID|ADDRESS|TEXT)-[A-Z]{1,3}\]|"
    r"\[(?:COMPANY|PERSON|ID|ADDRESS|TEXT)-[A-Z]{1,3}\]\s*\]"
)

# Literal escape or encoding sequences: refused, never classified (R1 P1-1).
_ENCODED = re.compile(
    r"\\(?:u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}|x[0-9a-fA-F]{2}|N\{|[0-7]{3})"
    r"|&#[xX]?[0-9a-fA-F]+;?|&[a-zA-Z]{2,8};"
    r"|(?:%[0-9a-fA-F]{2}){2,}"
)

_TOKEN = re.compile(
    r"(?P<alias>\[(?:COMPANY|PERSON|ID|ADDRESS|TEXT)-[A-Z]{1,3}\])"
    r"|(?P<contact>[^\s\"'<>()\[\]{},;]+@[^\s\"'<>()\[\]{},;]+"
    r"|https?://[^\s\"'<>()\[\]{}]+|www\.[^\s\"'<>()\[\]{}]+)"
    r"|(?P<grouped>\d{1,3}(?:,\d{3})+(?:\.\d+)?)"
    r"|(?P<word>[^\W_]+(?:[_'’.\-/][^\W_]+)*)"
)
_PART = re.compile(r"[^\W_]+")
# Up to three whole digits and up to six decimals: percentages and the ownership contract's
# precision (docs/contracts/OWNERSHIP_UBO_PROFILE.md: six decimal places).
_SMALL_NUMBER = re.compile(r"\d{1,3}(?:[.,]\d{1,6})?")
# A knowledge tag the service writes (G1, P2).
_TAG = re.compile(r"[A-Z]\d{1,2}")
_INITIAL_BEFORE = frozenset('.!?:;\n"([{•*>-—')

# Independent identifier patterns for validation (after placeholders are removed).
_EMAIL = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")
_URL = re.compile(r"https?://|www\.", re.IGNORECASE)
_NRIC = re.compile(r"(?<![A-Za-z0-9])[STFGM]\d{7}[A-Z](?![A-Za-z0-9])", re.IGNORECASE)
_UEN = re.compile(r"(?<![A-Za-z0-9])\d{8,10}[A-Z](?![A-Za-z0-9])", re.IGNORECASE)
# Four or more digits in a row, unless they are the decimal part of a number (1.1234).
_LONG_DIGITS = re.compile(r"(?<![\d.,])\d{4,}")
_PHONE = re.compile(r"\+?\d[\d -]{6,}\d")
_GROUPED = re.compile(r"\d{1,3}(?:,\d{3})+")

# Words that never identify on their own: kept even inside a known name or address.
_COMPONENT_STOP = frozenset(
    [
        "a",
        "an",
        "and",
        "at",
        "by",
        "de",
        "del",
        "der",
        "for",
        "in",
        "la",
        "le",
        "of",
        "on",
        "or",
        "the",
        "to",
        "van",
        "von",
        "pte",
        "ltd",
        "limited",
        "private",
        "plc",
        "inc",
        "llc",
        "llp",
        "lp",
        "co",
        "corp",
        "company",
        "corporation",
        "holdings",
        "group",
        "bhd",
        "sdn",
        "berhad",
        "gmbh",
        "ag",
        "sa",
        "nv",
        "bv",
        "pty",
        "road",
        "rd",
        "street",
        "st",
        "avenue",
        "ave",
        "drive",
        "dr",
        "lane",
        "ln",
        "crescent",
        "cres",
        "place",
        "pl",
        "way",
        "walk",
        "park",
        "central",
        "north",
        "south",
        "east",
        "west",
        "new",
        "blk",
        "block",
        "unit",
        "level",
        "floor",
        "building",
        "tower",
        "centre",
        "center",
        "singapore",
        "mr",
        "mrs",
        "ms",
        "madam",
        "sir",
        "bin",
        "binte",
        "bte",
    ]
)
# Common first names that are also ordinary words: at the start of a sentence, capitalised,
# they are replaced (in lower case they stay ordinary words; that residual is OD-3).
_NAME_LIKE = frozenset(
    [
        "will",
        "mark",
        "may",
        "june",
        "april",
        "august",
        "hope",
        "grace",
        "faith",
        "joy",
        "rose",
        "dawn",
        "ray",
        "bill",
        "frank",
        "victor",
        "pat",
        "sue",
        "jean",
        "gene",
        "dean",
        "rob",
        "ben",
        "art",
        "chase",
        "cliff",
        "dale",
        "glen",
        "hunter",
        "miles",
        "page",
        "reed",
        "wade",
        "young",
        "long",
        "rich",
        "king",
        "prince",
        "earl",
        "guy",
        "sterling",
        "summer",
        "autumn",
        "sky",
        "angel",
        "pearl",
        "ruby",
        "amber",
    ]
)

# Closed-class words a sentence starts with (question words, auxiliaries, pronouns, determiners,
# conjunctions, prepositions, polite openers, request verbs). They are never names, so they are
# kept capitalised at the start of a sentence even when the service never writes them so. A
# first name that is also one of these ("Will", "May") is on _NAME_LIKE and is not here.
_SENTENCE_OPENERS = frozenset(
    [
        "who",
        "whom",
        "whose",
        "what",
        "which",
        "when",
        "where",
        "why",
        "how",
        "whether",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "am",
        "do",
        "does",
        "did",
        "done",
        "can",
        "could",
        "would",
        "should",
        "shall",
        "might",
        "must",
        "have",
        "has",
        "had",
        "i",
        "we",
        "you",
        "they",
        "he",
        "she",
        "it",
        "its",
        "me",
        "us",
        "them",
        "my",
        "our",
        "your",
        "their",
        "his",
        "her",
        "this",
        "that",
        "these",
        "those",
        "there",
        "here",
        "the",
        "a",
        "an",
        "any",
        "all",
        "each",
        "every",
        "some",
        "no",
        "none",
        "not",
        "and",
        "or",
        "but",
        "so",
        "then",
        "also",
        "if",
        "because",
        "since",
        "while",
        "after",
        "before",
        "until",
        "in",
        "on",
        "at",
        "for",
        "to",
        "from",
        "by",
        "with",
        "about",
        "of",
        "as",
        "into",
        "over",
        "under",
        "between",
        "please",
        "thanks",
        "thank",
        "hi",
        "hello",
        "yes",
        "ok",
        "okay",
        "tell",
        "show",
        "give",
        "list",
        "explain",
        "summarise",
        "summarize",
        "describe",
        "check",
        "confirm",
        "compare",
        "find",
        "help",
        "let",
        "suppose",
        "assume",
        "next",
        "now",
        "still",
        "only",
        "just",
        "even",
        "already",
        "again",
    ]
)

# R2 (D-3): the particles and honorifics of a person's name. They never identify on their own,
# so they are the only words of a known person's name that are not protected alone.
_NAME_PARTICLES = frozenset(
    [
        "al",
        "bin",
        "binte",
        "bte",
        "da",
        "de",
        "del",
        "der",
        "di",
        "du",
        "el",
        "la",
        "le",
        "van",
        "von",
        "mr",
        "mrs",
        "ms",
        "madam",
        "dr",
        "sir",
    ]
)

# R2 (D-4): the external facts write a name that several distinct entities share (by their
# authoritative identifiers) as "<name> entity-<n>", so each entity gets its own placeholder.
ENTITY_REF_KEYS = ("party_ref", "holder_ref", "held_ref")
RELATIONSHIP_REFS = "relationship_refs"

ADMISSION_SECONDS = 120.0
_MAX_ADMISSIONS = 512
_MAX_CALLS = 512


class PrivacyRefused(LlmUnavailableError):
    """Nothing was sent: the prompt could not be made safe for an external provider."""

    def __init__(self, code: str) -> None:
        super().__init__(f"privacy boundary: {code}")
        self.code = code


@dataclass(frozen=True)
class Vocabulary:
    words: frozenset[str]
    terms: frozenset[str]


@lru_cache(maxsize=1)
def vocabulary(path: Path = VOCABULARY_FILE) -> Vocabulary:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        raise ValueError("privacy vocabulary schema")
    return Vocabulary(frozenset(data["words"]), frozenset(data["terms"]))


# ---------------------------------------------------------------- known identities (structured)


def _strings(value: Any) -> list[str]:
    return [value] if isinstance(value, str) and value.strip() else []


# A known identity: (kind, value) or, for an entity-qualified name (R2, D-4), (kind, value,
# display): the value is what the external facts write, the display what a reply restores.
Identity = tuple[str, ...]


def _name_key(name: Any) -> str:
    if not name:
        return ""
    return " ".join(_PART.findall(unicodedata.normalize("NFKC", str(name)).casefold()))


PARTY, OFFICER = "party", "officer"


def _entity_refs(facts: Mapping[str, Any]) -> list[tuple[str, str, str | None]]:
    """(family, name, authoritative reference) for every named entity the facts hold: the
    ownership analysis's parties (the backend's party ids, copilot.ownership_facts) and the
    registry officers (the backend's officer ids, context._registry_officer_records). A
    reference may be None (not established)."""

    found: list[tuple[str, str, str | None]] = []
    ownership = facts.get("ownership")
    if isinstance(ownership, Mapping):
        for person in ownership.get("people") or []:
            if not isinstance(person, Mapping):
                continue
            if isinstance(person.get("name"), str):
                ref = person.get("party_ref")
                found.append((PARTY, person["name"], str(ref) if ref else None))
            for path in person.get("paths") or []:
                for link in (path.get("links") if isinstance(path, Mapping) else None) or []:
                    if not isinstance(link, Mapping):
                        continue
                    for name_key, ref_key in (("holder", "holder_ref"), ("held", "held_ref")):
                        if isinstance(link.get(name_key), str):
                            ref = link.get(ref_key)
                            found.append((PARTY, link[name_key], str(ref) if ref else None))
    for record in facts.get("registry_officer_records") or []:
        if isinstance(record, Mapping) and isinstance(record.get("name"), str):
            ref = record.get("officer_ref")
            found.append((OFFICER, record["name"], str(ref) if ref else None))
    return found


def shared_names(facts: Mapping[str, Any] | None) -> dict[str, list[tuple[str, str]]]:
    """R2/R3 (D-4, officer identity): each name (normalised) that two or more distinct entities
    of one family share, by their authoritative references, with those (family, reference)
    pairs in first-seen order. A name is never the identity: entities with one name stay
    distinct, one entity under one reference stays one."""

    refs: dict[str, list[tuple[str, str]]] = {}
    for family, name, ref in _entity_refs(facts if isinstance(facts, Mapping) else {}):
        key = _name_key(name)
        if key and ref is not None and (family, ref) not in refs.setdefault(key, []):
            refs[key].append((family, ref))
    return {
        key: items
        for key, items in refs.items()
        if any(sum(1 for f, _ in items if f == family) > 1 for family in (PARTY, OFFICER))
    }


def unresolved_officer_names(facts: Mapping[str, Any] | None) -> frozenset[str]:
    """R3 (owner decision: officer identity): the officer names whose identity cannot be
    established safely, so their officer records are omitted from an external prompt rather
    than merged: two or more officer records of one name where any lacks its officer id, and
    an officer whose name is also an ownership party's (no verified structural link joins the
    two families)."""

    if not isinstance(facts, Mapping):
        return frozenset()
    officers: dict[str, list[str | None]] = {}
    parties: set[str] = set()
    for family, name, ref in _entity_refs(facts):
        key = _name_key(name)
        if family == OFFICER:
            officers.setdefault(key, []).append(ref)
        else:
            parties.add(key)
    return frozenset(
        key
        for key, refs in officers.items()
        if key in parties or (len(refs) > 1 and any(ref is None for ref in refs))
    )


def entity_label(
    name: str, ref: str | None, shared: Mapping[str, list[tuple[str, str]]], family: str = PARTY
) -> str:
    """The name as the external facts write it: qualified by entity when it is shared."""

    items = shared.get(_name_key(name))
    if not items or ref is None or (family, ref) not in items:
        return name
    return f"{name} entity-{items.index((family, ref)) + 1}"


def strip_entity_refs(facts: Mapping[str, Any]) -> dict[str, Any]:
    """The facts without the entity references (no model ever receives a party or officer
    id)."""

    out = dict(facts)
    records = facts.get("registry_officer_records")
    if isinstance(records, list):
        out["registry_officer_records"] = [
            {k: v for k, v in record.items() if k != "officer_ref"}
            if isinstance(record, Mapping)
            else record
            for record in records
        ]
    ownership = facts.get("ownership")
    if not isinstance(ownership, Mapping):
        return out
    kept = {key: value for key, value in ownership.items() if key != RELATIONSHIP_REFS}
    people = []
    for person in ownership.get("people") or []:
        if not isinstance(person, Mapping):
            people.append(person)
            continue
        item = {key: value for key, value in person.items() if key not in ENTITY_REF_KEYS}
        paths = []
        for path in person.get("paths") or []:
            if isinstance(path, Mapping):
                path = {
                    **path,
                    "links": [
                        {k: v for k, v in link.items() if k not in ENTITY_REF_KEYS}
                        if isinstance(link, Mapping)
                        else link
                        for link in path.get("links") or []
                    ],
                }
            paths.append(path)
        if "paths" in person:
            item["paths"] = paths
        people.append(item)
    if "people" in ownership:
        kept["people"] = people
    out["ownership"] = kept
    return out


def qualify_entities(facts: Mapping[str, Any]) -> dict[str, Any]:
    """R2/R3 (D-4, officer identity): the facts with every shared name written per entity
    (where the authoritative reference is known), officers of unresolved identity omitted, a
    shared name with no reference at its place left out, then without the references."""

    shared = shared_names(facts)
    unresolved = unresolved_officer_names(facts)
    qualified: dict[str, Any] = dict(facts)
    records = facts.get("registry_officer_records")
    if isinstance(records, list):
        qualified["registry_officer_records"] = [
            {
                **record,
                "name": entity_label(record["name"], record.get("officer_ref"), shared, OFFICER),
            }
            for record in records
            if isinstance(record, Mapping)
            and isinstance(record.get("name"), str)
            and _name_key(record["name"]) not in unresolved
        ]
    ownership = facts.get("ownership")
    if not shared or not isinstance(ownership, Mapping):
        return strip_entity_refs(qualified)
    people = []
    for person in ownership.get("people") or []:
        if not isinstance(person, Mapping):
            people.append(person)
            continue
        item = dict(person)
        if isinstance(person.get("name"), str):
            item["name"] = entity_label(person["name"], person.get("party_ref"), shared)
        paths = []
        for path in person.get("paths") or []:
            if isinstance(path, Mapping):
                links = []
                for link in path.get("links") or []:
                    if isinstance(link, Mapping):
                        link = dict(link)
                        for name_key, ref_key in (("holder", "holder_ref"), ("held", "held_ref")):
                            if isinstance(link.get(name_key), str):
                                link[name_key] = entity_label(
                                    link[name_key], link.get(ref_key), shared
                                )
                    links.append(link)
                path = {**path, "links": links}
            paths.append(path)
        if "paths" in person:
            item["paths"] = paths
        people.append(item)
    relationships = list(ownership.get("relationships") or [])
    refs = ownership.get(RELATIONSHIP_REFS)
    if isinstance(refs, list) and len(refs) == len(relationships):
        rewritten = []
        for text, ref in zip(relationships, refs, strict=True):
            if isinstance(text, str) and isinstance(ref, Mapping):
                for name_key, ref_key in (("holder", "holder_ref"), ("held", "held_ref")):
                    name = ref.get(name_key)
                    if isinstance(name, str) and name and _name_key(name) in shared:
                        label = entity_label(name, ref.get(ref_key), shared)
                        text = (
                            label + text[len(name) :]
                            if name_key == "holder" and text.startswith(name)
                            else text[: -len(name)] + label
                            if name_key == "held" and text.endswith(name)
                            else text
                        )
            rewritten.append(text)
        relationships = rewritten
    elif any(isinstance(text, str) and _names_in(text, shared) for text in relationships):
        # A relationship line naming a shared name with no reference cannot be bound to one
        # entity: it is left out rather than merged.
        relationships = [
            text
            for text in relationships
            if not (isinstance(text, str) and _names_in(text, shared))
        ]
    qualified["ownership"] = {**ownership, "people": people}
    if "relationships" in ownership:
        qualified["ownership"]["relationships"] = relationships
    return strip_entity_refs(qualified)


def _names_in(text: str, shared: Mapping[str, list[tuple[str, str]]]) -> list[str]:
    folded = _name_key(text)
    return [key for key in shared if f" {key} " in f" {folded} "]


def entity_identities(facts: Mapping[str, Any] | None) -> list[Identity]:
    """The entity-qualified forms of every shared name, each its own identity (R2, D-4)."""

    found: list[Identity] = []
    if not isinstance(facts, Mapping):
        return found
    shared = shared_names(facts)
    ownership = facts.get("ownership")
    persons = {
        _name_key(person.get("name"))
        for person in ((ownership.get("people") if isinstance(ownership, Mapping) else None) or [])
        if isinstance(person, Mapping)
    }
    seen: set[tuple[str, str, str]] = set()
    for family, name, ref in _entity_refs(facts):
        key = _name_key(name)
        if ref is None or key not in shared or (family, key, ref) in seen:
            continue
        seen.add((family, key, ref))
        kind = "PERSON" if family == OFFICER or key in persons else "COMPANY"
        found.append((kind, entity_label(name, ref, shared, family), name))
    return found


def identities_from_facts(
    facts: Mapping[str, Any] | None, *, people: Iterable[Any] = ()
) -> list[Identity]:
    """Every name and identifier the case facts hold, with its placeholder kind."""

    found: list[Identity] = list(entity_identities(facts))
    if not isinstance(facts, Mapping):
        facts = {}
    company = facts.get("company") or {}
    legal = company.get("legal_name") if isinstance(company, Mapping) else None
    if isinstance(company, Mapping):
        found += [("COMPANY", item) for item in _strings(company.get("legal_name"))]
        found += [("ID", item) for item in _strings(company.get("uen"))]
        found += [("ADDRESS", item) for item in _strings(company.get("registered_address"))]
    goldtier = facts.get("goldtier") or {}
    if isinstance(goldtier, Mapping):
        found += [("ID", item) for item in _strings(goldtier.get("goldtier_id"))]
    for record in facts.get("registry_officer_records") or []:
        if isinstance(record, Mapping):
            found += [("PERSON", item) for item in _strings(record.get("name"))]
    ownership = facts.get("ownership") or {}
    persons: set[str] = set()
    if isinstance(ownership, Mapping):
        for person in ownership.get("people") or []:
            if isinstance(person, Mapping):
                for name in _strings(person.get("name")):
                    persons.add(name.casefold())
                    found.append(("PERSON", name))
        for person in ownership.get("people") or []:
            if not isinstance(person, Mapping):
                continue
            for path in person.get("paths") or []:
                for link in (path.get("links") if isinstance(path, Mapping) else None) or []:
                    if not isinstance(link, Mapping):
                        continue
                    for key in ("holder", "held"):
                        for name in _strings(link.get(key)):
                            kind = "PERSON" if name.casefold() in persons else "COMPANY"
                            found.append((kind, name))
        # I-4: the relationships cover every link of a path, the links only the first few.
        for link in ownership.get(RELATIONSHIP_REFS) or []:
            if isinstance(link, Mapping):
                for key in ("holder", "held"):
                    for name in _strings(link.get(key)):
                        kind = "PERSON" if name.casefold() in persons else "COMPANY"
                        found.append((kind, name))
    for document in facts.get("documents") or []:
        if not isinstance(document, Mapping):
            continue
        found += [("ID", item) for item in _strings(document.get("name"))]
        for item in document.get("fields") or []:
            if isinstance(item, Mapping):
                found += _field_identity(item.get("field"), item.get("value_read_from_document"))
    # I-4: the case facts hold a blocker's rows under "differences" (context._evidence_for);
    # "evidence" is still read for any caller that supplies it.
    for blocker in facts.get("blockers") or []:
        if not isinstance(blocker, Mapping):
            continue
        for rows in (blocker.get("differences"), blocker.get("evidence")):
            for item in rows if isinstance(rows, list) else []:
                if isinstance(item, Mapping):
                    for key in ("registry_value", "document_value"):
                        found += _field_identity(item.get("field"), item.get(key))
    for item in facts.get("discrepancies") or []:
        if isinstance(item, Mapping):
            for key in ("registry_value", "document_value", "registry", "document"):
                found += _field_identity(item.get("field"), item.get(key))
            # I-4: each source's value and the decided value (context._discrepancies).
            for value in item.get("values") or []:
                if isinstance(value, Mapping):
                    found += _field_identity(item.get("field"), value.get("value"))
            found += _field_identity(item.get("field"), item.get("decided_value"))
    # I-4: the fields to review, their values and the document each is in.
    review = facts.get("document_field_review")
    for item in (review.get("fields") if isinstance(review, Mapping) else None) or []:
        if isinstance(item, Mapping):
            found += [("ID", name) for name in _strings(item.get("document"))]
            for key in ("document_value", "acra_value"):
                found += _field_identity(item.get("field"), item.get(key))
    viewer = facts.get("viewer") or {}
    if isinstance(viewer, Mapping):
        found += [("PERSON", item) for item in _strings(viewer.get("name"))]
    for item in people:
        found += [("PERSON", value) for value in _strings(item)]
    if legal:
        # A link to the company itself is the company.
        found = [
            ("COMPANY", *item[1:]) if item[1].casefold() == str(legal).casefold() else item
            for item in found
        ]
    return found


def _field_identity(label: Any, value: Any) -> list[tuple[str, str]]:
    if not isinstance(value, str) or not value.strip():
        return []
    text = str(label or "").casefold()
    if "address" in text:
        return [("ADDRESS", value)]
    if "name" in text or "director" in text or "officer" in text or "shareholder" in text:
        return [("PERSON", value)]
    if any(word in text for word in ("number", "uen", "registration", "identifier", " id")):
        return [("ID", value)]
    return []


# ---------------------------------------------------------------------- field table (minimise)

# D-142 field table: what an external model receives of each case fact. Keys not listed under a
# section are dropped. "keep" values still pass the vocabulary rules and placeholders.
COMPANY_FIELDS = ("legal_name", "uen", "country", "entity_status", "registered_address", "source")
DOCUMENT_FIELDS = ("detected_type", "state", "fields")
DOCUMENT_VALUE_FIELDS = (
    "field",
    "value_read_from_document",
    "confidence",
    "compared_with_registry",
    "review_status",
)
# The ownership projection (copilot.ownership_facts, or the withheld/absent note): its top-level
# keys, explicitly. U-4 (2026-11-19) adds poc_basis_accepted, the backend's accepted POC
# acceptance (a boolean, no personal data). Party ids are already removed (strip_entity_refs).
OWNERSHIP_FIELDS = (
    "available",
    "note",
    "basis",
    "analysis_state",
    "source_environment",
    "threshold_percent",
    "threshold_rule",
    "relationships",
    "people",
    "people_not_shown",
    "issues",
    "manual_review_recorded",
    "poc_basis_accepted",
)
# D-145 (F-6): per-person ownership keys that only the service uses (its own threshold lines and
# admission); removed from every person before any model receives the facts. The top-level
# review_advisory flag is local only too: it is not in OWNERSHIP_FIELDS.
OWNERSHIP_LOCAL_PERSON_FIELDS = ("assumed_basis_threshold_result",)


def minimise_facts(facts: Mapping[str, Any], *, known_labels: frozenset[str]) -> dict[str, Any]:
    """The case facts an external model may receive (the D-142 field table).

    Q1: the registration date (and year) is omitted. Q2: a document field whose label is not a
    reviewed field label is dropped; a document's file name is replaced by its detected type."""

    # R2 (D-4): a name that distinct entities share is written per entity (then the references
    # are removed: no model receives a party id).
    out = qualify_entities(facts)
    company = facts.get("company")
    if isinstance(company, Mapping):
        out["company"] = {key: company.get(key) for key in COMPANY_FIELDS if key in company}
    documents = []
    aliases: dict[str, str] = {}
    for number, document in enumerate(facts.get("documents") or [], start=1):
        if not isinstance(document, Mapping):
            continue
        kept = {key: document.get(key) for key in DOCUMENT_FIELDS if key in document}
        kept["fields"] = [
            {key: item.get(key) for key in DOCUMENT_VALUE_FIELDS if key in item}
            for item in document.get("fields") or []
            if isinstance(item, Mapping) and item.get("field") in known_labels
        ]
        label = f"document {number} ({document.get('detected_type') or 'unclassified'})"
        kept["name"] = label
        if isinstance(document.get("name"), str):
            aliases[document["name"]] = label
        documents.append({"name": kept.pop("name"), **kept})
    if "documents" in facts:
        out["documents"] = documents
    ownership = out.get("ownership")
    if isinstance(ownership, Mapping):
        kept = {key: ownership[key] for key in OWNERSHIP_FIELDS if key in ownership}
        if isinstance(kept.get("people"), list):
            kept["people"] = [
                {
                    key: value
                    for key, value in person.items()
                    if key not in OWNERSHIP_LOCAL_PERSON_FIELDS
                }
                if isinstance(person, Mapping)
                else person
                for person in kept["people"]
            ]
        out["ownership"] = kept
    if "case_id" in out:
        out["case_id"] = None
    return _without_backend_text(_document_names(out, aliases))


# R4 (R3-1, Option A): the backend's own free text (its descriptions of exceptions, the step
# results and the timeline messages) is not sent to an external model; the structured codes,
# statuses and values stay, and so does the assistant's own reviewed wording (plain_explanation
# is a RULE_PLAIN template, still_needed_before_goldtier a READINESS_NEEDS one).
_BLOCKER_TEXT = (
    "title",
    "app_explanation",
    "expected_next_step",
    "resolution_condition",
    "why_no_action",
)


def _without_backend_text(out: dict[str, Any]) -> dict[str, Any]:
    problem = out.get("system_problem")
    if isinstance(problem, Mapping):
        out["system_problem"] = {"code": problem.get("code")}
    blockers = []
    for blocker in out.get("blockers") or []:
        if not isinstance(blocker, Mapping):
            continue
        item = {**blocker, **{key: None for key in _BLOCKER_TEXT if key in blocker}}
        if "what_is_needed" in item:
            item["what_is_needed"] = []
        if isinstance(item.get("actions_available_to_this_user"), list):
            item["actions_available_to_this_user"] = [
                {**action, "meaning": None} if isinstance(action, Mapping) else action
                for action in item["actions_available_to_this_user"]
            ]
        blockers.append(item)
    if "blockers" in out:
        out["blockers"] = blockers
    for key, text in (("steps", "result"), ("timeline", "what")):
        if isinstance(out.get(key), list):
            out[key] = [
                {**row, text: None} if isinstance(row, Mapping) and text in row else row
                for row in out[key]
            ]
    return out


def _document_names(value: Any, aliases: dict[str, str]) -> Any:
    """R4: a document's file name (written by whoever uploaded it) is replaced by its
    detected-type label everywhere in the external facts, as in the document list; a document
    observation's source that is not a current document's name becomes "a document"."""

    if isinstance(value, list):
        return [_document_names(item, aliases) for item in value]
    if isinstance(value, Mapping):
        out = {key: _document_names(item, aliases) for key, item in value.items()}
        if str(out.get("source_kind") or "").startswith("DOCUMENT") and "from" in out:
            source = value.get("from")
            out["from"] = aliases.get(source, "a document") if isinstance(source, str) else None
        return out
    if isinstance(value, str) and value in aliases:
        return aliases[value]
    return value


# ------------------------------------------------------------------------------- the shield


def _letters(index: int) -> str:
    letters = ""
    index += 1
    while index:
        index, rest = divmod(index - 1, 26)
        letters = chr(ord("A") + rest) + letters
    return letters


def canonical(text: str) -> str:
    """NFKC with invisible format characters removed; refuses encoded or escaped input."""

    text = unicodedata.normalize("NFKC", text)
    text = "".join(
        char for char in text if char in "\n\t" or unicodedata.category(char) not in ("Cf", "Cc")
    )
    if _ENCODED.search(text):
        raise PrivacyRefused("ENCODED_INPUT")
    return text


def _alnum(value: str) -> str:
    return "".join(_PART.findall(value))


def _protectable(value: str) -> bool:
    """A known value is protected whatever its length, except a single letter (it would
    replace every "a" and "I"); a single digit or longer is always protected."""

    core = _alnum(value)
    return bool(core) and (len(core) >= 2 or core.isdigit())


def _known_pattern(value: str) -> re.Pattern[str] | None:
    words = [re.escape(word) for word in _PART.findall(value)]
    if not words or not _protectable(value):
        return None
    return re.compile(r"(?<![^\W_])" + r"[\W_]+".join(words) + r"(?![^\W_])", re.IGNORECASE)


def _components(kind: str, value: str, vocab: Vocabulary) -> list[str]:
    """The distinctive words of a known name or address, each protected on its own: not a
    generic word (_COMPONENT_STOP), not a number, not shorter than three letters, and not one
    of the service's own terms (OFFICIAL, MOCK, BUSINESS: the service writes them, so alone they
    identify nobody). Every other word is protected whether or not it is an ordinary word
    ("Garden", "Grace", "Orchard")."""

    if kind not in ("PERSON", "COMPANY", "ADDRESS"):
        return []
    parts = _PART.findall(value)
    if len(parts) < 2:
        return []
    return [
        part
        for part in parts
        if len(part) >= 3
        and not any(char.isdigit() for char in part)
        and part.casefold() not in _COMPONENT_STOP
        and not any(
            form in vocab.terms for form in (part, part.upper(), part.capitalize(), part.lower())
        )
    ]


def _ambiguous_parts(kind: str, value: str, vocab: Vocabulary) -> list[str]:
    """R2 (D-3): the words of a known name that _components leaves out but that can still
    identify: for a person, every word of two or more letters except a particle or honorific
    ("Do", "An", "Ng", "Will", "Mark"); for a company or an address, a two-letter word that is
    neither generic nor a service term. They are ordinary words too, so where they stand decides
    (Shield.protect_text): in free text (questions, history) every occurrence is replaced; in
    the service's own text (system messages) a name-like use (capitalised, not starting a
    sentence, and not one of the service's own terms as the service writes it: "Support"
    there is the service's wording) is replaced."""

    if kind not in ("PERSON", "COMPANY", "ADDRESS"):
        return []
    parts = _PART.findall(value)
    if len(parts) < 2:
        return []
    distinct = {part.casefold() for part in _components(kind, value, vocab)}
    found: list[str] = []
    for part in parts:
        folded = part.casefold()
        if len(part) < 2 or any(char.isdigit() for char in part) or folded in distinct:
            continue
        if kind == "PERSON":
            if folded in _NAME_PARTICLES:
                continue
        elif (
            len(part) != 2
            or folded in _COMPONENT_STOP
            or any(form in vocab.terms for form in (part, part.upper(), part.capitalize()))
        ):
            continue
        found.append(part)
    return found


def _ambiguous_pattern(part: str) -> re.Pattern[str]:
    return re.compile(r"(?<![^\W_])" + re.escape(part) + r"(?![^\W_])", re.IGNORECASE)


# R3 (finding P2 "a system role does not establish trusted text origin"): text origin is
# established where a message is built, never inferred from its role.
#
#     trusted   fixed service wording, registered once at import by the module that owns it
#               (``trusted_text``): the service's own instructions and probes. Ordinary words
#               of a known name are replaced only where they are used as a name
#     service   any other system text, and data the service built itself (case facts,
#               knowledge, topic lines, Try's rule, dashboard metrics): every ordinary word of a
#               known name is replaced wherever it stands; unknown words become placeholders
#     person    what a person wrote (the final user turn, unless its builder declares the
#               message service-built): the controlled query below
_TRUSTED: set[str] = set()
_TRUSTED_LOCK = threading.Lock()


def _text_digest(text: str) -> str:
    return hashlib.sha256(
        unicodedata.normalize("NFKC", text).replace("\r\n", "\n").encode("utf-8")
    ).hexdigest()


def trusted_text(text: str) -> str:
    """Registers fixed service wording as trusted (call it on module constants only, at import)
    and returns it unchanged."""

    with _TRUSTED_LOCK:
        _TRUSTED.add(_text_digest(text))
    return text


def is_trusted_text(text: str) -> bool:
    with _TRUSTED_LOCK:
        return _text_digest(text) in _TRUSTED


TRUSTED, SERVICE, PERSON = "trusted", "service", "person"


def _name_use(found: re.Match[str], mode: str, vocab: Vocabulary) -> bool:
    """Whether this occurrence of an ambiguous word of a known name is replaced: everywhere,
    except in trusted wording, where only a name-like use is (capitalised, not starting a
    sentence, not written exactly as one of the service's own terms)."""

    if mode != TRUSTED:
        return True
    word = found.group(0)
    return (
        word[0].isupper() and word not in vocab.terms and not _initial(found.string, found.start())
    )


# R3 (OD-3, owner decision of 2026-11-17: ambiguous personal information leakage is not accepted).
# What a person wrote leaves only as a controlled, positively classified query: after the known
# identities become placeholders, every remaining word must be a word of the reviewed service
# vocabulary that is not name-capable, a service term, a small number or a knowledge tag, and
# every placeholder must stand for a known case identity. Anything else (a word outside the
# vocabulary, an identifier the text rules would replace, a name-capable ordinary word) means
# the text cannot be safely classified: nothing is sent and the deterministic case-data answer
# follows (FREE_TEXT_UNCLASSIFIED). Chat history is never forwarded to an external model.
#
# _NAME_CAPABLE: the words of the reviewed service vocabulary that are also given names or
# surnames (reviewed against common English given names and surnames and romanised Singapore
# surnames), except a few core service words whose use as a name is negligible (case, day,
# read, price, the compass points, small, strong, long).
_NAME_CAPABLE = frozenset(
    [
        "al",
        "amber",
        "angel",
        "april",
        "art",
        "august",
        "autumn",
        "banks",
        "ben",
        "bill",
        "chase",
        "cliff",
        "cook",
        "dale",
        "dawn",
        "dean",
        "don",
        "earl",
        "ed",
        "faith",
        "gene",
        "glen",
        "grant",
        "guy",
        "hope",
        "hunter",
        "jean",
        "joy",
        "june",
        "king",
        "lane",
        "low",
        "mark",
        "max",
        "may",
        "miles",
        "page",
        "park",
        "pat",
        "pearl",
        "prince",
        "rain",
        "ray",
        "red",
        "reed",
        "rich",
        "rob",
        "rose",
        "ruby",
        "sky",
        "sterling",
        "sue",
        "summer",
        "wade",
        "will",
        "young",
    ]
)
# The reviewed document-type words (scripts/build_privacy_vocabulary.py DOCUMENT_TERMS: "a
# recent utility bill") stay ordinary words, so a document rule keeps its meaning (residual).
_DOCUMENT_WORDS = frozenset(["bill"])
NAME_CAPABLE = (_NAME_CAPABLE | _NAME_LIKE) - _DOCUMENT_WORDS


def _initial(text: str, start: int) -> bool:
    index = start - 1
    while index >= 0 and text[index] in " \t":
        index -= 1
    return index < 0 or text[index] in _INITIAL_BEFORE


def _part_kept(part: str, *, initial: bool, vocab: Vocabulary, sentence_case: bool = False) -> bool:
    if any(char.isdigit() for char in part):
        return bool(_SMALL_NUMBER.fullmatch(part) or _TAG.fullmatch(part))
    if len(part) == 1:
        return True
    if part.casefold() not in vocab.words:
        return False
    if part[0].isupper() or any(char.isupper() for char in part[1:]):
        # R1 (P1-1): a capitalised, capitals or mixed-case word is kept only in a form the
        # service itself writes (a term), wherever it stands. A distinctive word that is also in
        # the vocabulary ("Merlion", "Grace") is replaced at the start of a sentence too, and a
        # first name that is also an ordinary word ("Will asked") even when it is a term.
        if initial and part.casefold() in _NAME_LIKE:
            return False
        if part in vocab.terms:
            return True
        # R3: in person-written text, the capital that starts a sentence is sentence case
        # ("Approve this case"): an ordinary vocabulary word that is not name-capable is kept.
        if (
            sentence_case
            and initial
            and part[0].isupper()
            and part[1:].islower()
            and part.casefold() not in NAME_CAPABLE
        ):
            return True
        # An ordinary sentence opener ("Who are ...?") keeps its meaning; nothing else does.
        return (
            initial
            and part[0].isupper()
            and part[1:].islower()
            and (part.casefold() in _SENTENCE_OPENERS)
        )
    return True


def token_kept(
    token: str, *, initial: bool, vocab: Vocabulary, sentence_case: bool = False
) -> bool:
    """Whether one word-like token may go to an external model as written."""

    if _SMALL_NUMBER.fullmatch(token) or _TAG.fullmatch(token):
        return True
    parts = _PART.findall(token)
    if "_" in token and token.isupper() and all(not part.isdigit() for part in parts):
        # A service code (CERTIFICATE_OF_INCORPORATION_POC): every word must be vocabulary.
        return all(len(part) == 1 or part.casefold() in vocab.words for part in parts)
    return bool(parts) and all(
        _part_kept(part, initial=initial and number == 0, vocab=vocab, sentence_case=sentence_case)
        for number, part in enumerate(parts)
    )


@dataclass
class Shield:
    """One call's placeholders: built from the known identities, extended by the text rules."""

    known: list[Identity] = field(default_factory=list)
    vocab: Vocabulary = field(default_factory=vocabulary)
    originals: dict[str, str] = field(default_factory=dict)  # placeholder -> real value
    _by_key: dict[tuple[str, str], str] = field(default_factory=dict)
    _counts: dict[str, int] = field(default_factory=dict)
    _patterns: list[tuple[re.Pattern[str], str]] = field(default_factory=list)
    # R2 (D-3): short or ordinary words of known names, replaced where they are name-like.
    _ambiguous: list[tuple[re.Pattern[str], str]] = field(default_factory=list)
    replaced_text: int = 0  # words replaced by the text rules (not known identities)
    # R3: the placeholders that stand for known case identities (not the text rules' ones).
    known_aliases: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        # R2 (D-4): a value is keyed by itself (an entity-qualified name is its own value), so
        # entities that share a name keep one placeholder each; the display is what a reply
        # restores (the name as the case writes it).
        seen: dict[str, tuple[str, str, str]] = {}
        for item in self.known:
            kind, value = item[0], item[1]
            display = item[2] if len(item) > 2 else value
            key = _name_key(value)
            if kind in KINDS and key and key not in seen and _protectable(value):
                seen[key] = (kind, canonical(value).strip(), canonical(display).strip())
        ordered = sorted(seen.values(), key=lambda item: (-len(item[1]), item[1]))
        for kind, value, display in ordered:
            pattern = _known_pattern(value)
            if pattern is not None:
                self._patterns.append((pattern, self._alias(kind, value, display)))
        # Then each distinctive word of a known name or address on its own (after the whole
        # values, so a whole value is always one placeholder).
        words: dict[str, tuple[str, str]] = {}
        loose: dict[str, tuple[str, str]] = {}
        for kind, _value, display in ordered:
            for part in _components(kind, display, self.vocab):
                words.setdefault(part.casefold(), (kind, part))
            for part in _ambiguous_parts(kind, display, self.vocab):
                loose.setdefault(part.casefold(), (kind, part))
        for word, (kind, part) in sorted(words.items(), key=lambda item: (-len(item[0]), item[0])):
            if word in seen:
                continue
            pattern = _known_pattern(part)
            if pattern is not None:
                self._patterns.append((pattern, self._alias(kind, part)))
        for word, (kind, part) in sorted(loose.items(), key=lambda item: (-len(item[0]), item[0])):
            if word in seen or word in words:
                continue
            self._ambiguous.append((_ambiguous_pattern(part), self._alias(kind, part)))
        self.known_aliases = frozenset(self.originals)

    def _alias(self, kind: str, value: str, display: str | None = None) -> str:
        key = (kind, value.casefold())
        alias = self._by_key.get(key)
        if alias is None:
            count = self._counts.get(kind, 0)
            self._counts[kind] = count + 1
            alias = f"[{kind}-{_letters(count)}]"
            self._by_key[key] = alias
            self.originals[alias] = value if display is None else display
        return alias

    def protect_text(self, text: str, mode: str = PERSON) -> str:
        text = canonical(text)
        # The service never writes a placeholder: one in any text is neutralised first.
        text = ALIAS.sub(lambda found: f"({found.group(1)} {found.group(2)})", text)
        for pattern, alias in self._patterns:
            text = pattern.sub(alias, text)
        for pattern, alias in self._ambiguous:

            def name_or_word(found: re.Match[str], alias: str = alias) -> str:
                return alias if _name_use(found, mode, self.vocab) else found.group(0)

            text = pattern.sub(name_or_word, text)
        spans: list[tuple[int, int]] = []
        for found in _TOKEN.finditer(text):
            if found.group("alias"):
                continue
            if found.group("contact") or found.group("grouped"):
                spans.append(found.span())
                continue
            token = found.group("word")
            if not token_kept(
                token,
                initial=_initial(text, found.start()),
                vocab=self.vocab,
                sentence_case=mode == PERSON,
            ):
                spans.append(found.span())
        if not spans:
            return text
        self.replaced_text += len(spans)  # words, before neighbours are merged
        merged: list[list[int]] = []
        for start, end in spans:
            if merged and text[merged[-1][1] : start] in (" ", "-"):
                merged[-1][1] = end
            else:
                merged.append([start, end])
        out: list[str] = []
        last = 0
        for start, end in merged:
            original = text[start:end]
            kind = "ID" if any(char.isdigit() or char == "@" for char in original) else "TEXT"
            out.append(text[last:start])
            out.append(self._alias(kind, original))
            last = end
        out.append(text[last:])
        return "".join(out)


def _scan_residual(
    text: str, shield: Shield, *, issued: frozenset[str] | None = None, mode: str = PERSON
) -> str | None:
    """Independent re-check of protected text; the failing rule's code, or None."""

    if _ENCODED.search(text):
        return "ENCODED"
    for pattern, _ in shield._patterns:
        if pattern.search(text):
            return "KNOWN_VALUE"
    for pattern, _ in shield._ambiguous:
        if any(_name_use(found, mode, shield.vocab) for found in pattern.finditer(text)):
            return "KNOWN_VALUE"
    allowed = shield.originals if issued is None else issued
    for found in ALIAS.finditer(text):
        if found.group(0) not in allowed:
            return "ALIAS"
    bare = ALIAS.sub(" ", text)
    if (
        _EMAIL.search(bare)
        or _URL.search(bare)
        or _NRIC.search(bare)
        or _UEN.search(bare)
        or _LONG_DIGITS.search(bare)
        or _PHONE.search(bare)
        or _GROUPED.search(bare)
    ):
        return "PATTERN"
    for found in _TOKEN.finditer(text):
        if found.group("alias"):
            continue
        if found.group("contact") or found.group("grouped"):
            return "RESIDUAL"
        if not token_kept(
            found.group("word"),
            initial=_initial(text, found.start()),
            vocab=shield.vocab,
            sentence_case=mode == PERSON,
        ):
            return "RESIDUAL"
    return None


def _question_words(text: str) -> int:
    return sum(1 for found in _TOKEN.finditer(text) if found.group("word") or found.group("alias"))


class ProtectedMessages(list):  # type: ignore[type-arg]
    """The protected messages of one provider call, carrying that call's id."""

    __slots__ = ("call_id",)

    def __init__(self, items: Iterable[dict[str, str]], call_id: str) -> None:
        super().__init__(items)
        self.call_id = call_id


@dataclass
class Protected:
    messages: list[dict[str, str]]
    shield: Shield
    dropped_lines: int = 0
    # The placeholders that actually appear in what is sent: the only ones restorable.
    emitted: frozenset[str] = frozenset()
    call_id: str | None = None
    # R3: the origin of each sent text (by its protected content), for the wire check.
    trusted: frozenset[str] = frozenset()
    person: frozenset[str] = frozenset()

    def restore_line(self, line: str) -> str | None:
        """The line with its placeholders restored, or None when it must be dropped: it holds a
        placeholder this call did not send, or something shaped like one that is not exact."""

        if _ALIAS_WRAPPED.search(line):
            return None
        for found in ALIAS.finditer(line):
            if found.group(0) not in self.emitted:
                return None
        rest = ALIAS.sub(" ", line)
        if _ALIAS_LIKE_STRICT.search(rest) or _ALIAS_LIKE_BARE.search(rest):
            return None
        return ALIAS.sub(lambda found: self.shield.originals[found.group(0)], line)

    def restore_text(self, text: str) -> str:
        kept: list[str] = []
        for line in text.splitlines(keepends=True):
            restored = self.restore_line(line)
            if restored is None:
                self.dropped_lines += 1
                continue
            kept.append(restored)
        return "".join(kept)

    def restore_answer(self, answer: ModelAnswer) -> ModelAnswer:
        return replace(answer, text=self.restore_text(answer.text))

    async def restore_stream(self, source: AsyncIterator[Piece]) -> AsyncGenerator[Piece, None]:
        """Restored pieces: each complete line once it ends; the rest with the last piece. A
        stream that ends without its last piece (cancelled, interrupted) discards its
        unfinished line: a partial placeholder is never restored late."""

        pending = ""
        async for piece in source:
            pending += piece.text
            final = (
                piece.cut_short
                or piece.usage is not None
                or piece.finish_reason is not None
                or piece.budget is not None
            )
            if "\n" in pending and not final:
                head, _, pending = pending.rpartition("\n")
                restored = self.restore_text(head + "\n")
                if restored:
                    yield Piece(text=restored)
            if final:
                restored = self.restore_text(pending)
                pending = ""
                yield replace(piece, text=restored)
        if pending:
            restored = self.restore_text(pending)
            if restored:
                yield Piece(text=restored)


def _mode(message: Mapping[str, Any], person_written: bool) -> str:
    if message.get("role") == "system":
        return TRUSTED if is_trusted_text(str(message.get("content", ""))) else SERVICE
    return PERSON if person_written else SERVICE


def forwarded(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """R3 (OD-3): what an external model may receive of a built prompt: its system messages and
    its final user turn. Chat history (earlier user turns, assistant turns, any other role) is
    never forwarded."""

    last = max((i for i, m in enumerate(messages) if m.get("role") == "user"), default=None)
    return [m for i, m in enumerate(messages) if m.get("role") == "system" or i == last]


def protect(
    messages: list[dict[str, str]],
    known: Iterable[Identity] = (),
    *,
    person_written: bool = True,
    controlled: Iterable[str] = (),
) -> Protected:
    """The messages as an external model may receive them; raises PrivacyRefused.

    ``person_written`` False: the builder declared its user turn service-built data (dashboard
    metrics), so it takes the service rules, not the controlled query. ``controlled``: texts a
    person wrote that the builder placed inside a system message (Try's unsaved rule); each must
    pass the controlled query on its own."""

    shield = Shield(known=list(known))
    kept = forwarded(messages)
    modes = [_mode(message, person_written) for message in kept]
    # R4 (R3-1): no person-written text is ever admitted to an external model.
    if PERSON in modes or any(text for text in controlled):
        raise PrivacyRefused("PERSON_TEXT")
    out = [
        {**message, "content": shield.protect_text(str(message.get("content", "")), mode)}
        for message, mode in zip(kept, modes, strict=True)
    ]
    for message, mode in zip(out, modes, strict=True):
        code = _scan_residual(message["content"], shield, mode=mode)
        if code is not None:
            raise PrivacyRefused(code)
    emitted = frozenset(
        found.group(0) for message in out for found in ALIAS.finditer(message["content"])
    )
    return Protected(
        messages=out,
        shield=shield,
        emitted=emitted,
        trusted=frozenset(
            m["content"] for m, mode in zip(out, modes, strict=True) if mode == TRUSTED
        ),
        person=frozenset(
            m["content"] for m, mode in zip(out, modes, strict=True) if mode == PERSON
        ),
    )


# ------------------------------------------------------------- admissions and provider calls


def _digest(messages: list[dict[str, str]]) -> str:
    return hashlib.sha256(
        json.dumps(list(messages), sort_keys=True, ensure_ascii=True).encode("utf-8")
    ).hexdigest()


@dataclass
class _Admission:
    digest: str
    known: tuple[Identity, ...]
    source: str
    created: float
    person_written: bool = True
    controlled: tuple[str, ...] = ()


@dataclass
class _Call:
    digest: str
    shield: Shield
    emitted: frozenset[str]
    created: float
    cleared: bool = False  # the caller took its clearance (before any reservation)
    sent: bool = False  # the wire check passed once
    trusted: frozenset[str] = frozenset()
    person: frozenset[str] = frozenset()
    person_written: bool = True
    # R4 (R3-3): the exact ordered projection this call may send: (role, text) per message.
    projection: tuple[tuple[str, str], ...] = ()


def _projection(messages: Iterable[Mapping[str, Any]]) -> tuple[tuple[str, str], ...]:
    return tuple((str(m.get("role", "")), str(m.get("content", ""))) for m in messages)


class AdmittedMessages(list):  # type: ignore[type-arg]
    """Messages with their single-use privacy admission (an opaque id only)."""

    __slots__ = ("admission_id",)

    def __init__(self, items: Iterable[dict[str, str]], admission_id: str) -> None:
        super().__init__(items)
        self.admission_id = admission_id


_admissions: dict[str, _Admission] = {}
_calls: dict[str, _Call] = {}
_lock = threading.Lock()
_clock = time.monotonic


def _prune(now: float) -> None:
    for key in [key for key, item in _admissions.items() if now - item.created > ADMISSION_SECONDS]:
        del _admissions[key]
    for key in [key for key, item in _calls.items() if now - item.created > ADMISSION_SECONDS]:
        del _calls[key]
    while len(_admissions) >= _MAX_ADMISSIONS:
        del _admissions[min(_admissions, key=lambda key: _admissions[key].created)]
    while len(_calls) >= _MAX_CALLS:
        del _calls[min(_calls, key=lambda key: _calls[key].created)]


def admit(
    messages: list[dict[str, str]],
    known: Iterable[Identity] = (),
    *,
    source: str = "service",
    person_written: bool = True,
    controlled: Iterable[str] = (),
) -> AdmittedMessages:
    """One single-use admission for exactly these messages and this case's known identities
    (memory only). Returns the messages carrying its id; any copy of them carries none. The
    builder states the origin of what it built here (``protect``: ``person_written``,
    ``controlled``); a system role alone never makes text trusted."""

    items = [dict(message) for message in messages]
    admission_id = secrets.token_hex(16)
    now = _clock()
    entry = _Admission(
        _digest(items),
        tuple(known),
        source,
        now,
        person_written=person_written,
        controlled=tuple(str(text) for text in controlled if text),
    )
    with _lock:
        _prune(now)
        _admissions[admission_id] = entry
    return AdmittedMessages(items, admission_id)


def _peek(messages: list[dict[str, str]]) -> _Admission:
    admission_id = getattr(messages, "admission_id", None)
    if admission_id is None:
        raise PrivacyRefused("ADMISSION_MISSING")
    with _lock:
        entry = _admissions.get(admission_id)
    if entry is None:
        raise PrivacyRefused("ADMISSION_UNAVAILABLE")
    if _clock() - entry.created > ADMISSION_SECONDS:
        raise PrivacyRefused("ADMISSION_EXPIRED")
    if _digest(messages) != entry.digest:
        raise PrivacyRefused("ADMISSION_MISMATCH")
    return entry


def outbound(messages: list[dict[str, str]]) -> Protected:
    """Called by each external model right after its own admission check (the ticket or the
    D-094 text check, on the messages as built) and before anything is reserved or sent:
    consumes the privacy admission once and returns the protected messages, which are the only
    thing sent, as one provider call. Raises PrivacyRefused."""

    admission_id = getattr(messages, "admission_id", None)
    if admission_id is None:
        raise PrivacyRefused("ADMISSION_MISSING")
    with _lock:
        entry = _admissions.pop(admission_id, None)
    if entry is None:
        raise PrivacyRefused("ADMISSION_UNAVAILABLE")  # never issued, consumed or evicted
    now = _clock()
    if now - entry.created > ADMISSION_SECONDS:
        raise PrivacyRefused("ADMISSION_EXPIRED")
    if _digest(messages) != entry.digest:
        raise PrivacyRefused("ADMISSION_MISMATCH")
    protected = protect(
        list(messages),
        entry.known,
        person_written=entry.person_written,
        controlled=entry.controlled,
    )
    call_id = secrets.token_hex(16)
    sent = ProtectedMessages(protected.messages, call_id)
    with _lock:
        _prune(now)
        _calls[call_id] = _Call(
            _digest(sent),
            protected.shield,
            protected.emitted,
            now,
            trusted=protected.trusted,
            person=protected.person,
            person_written=entry.person_written,
            projection=_projection(sent),
        )
    return replace(protected, messages=sent, call_id=call_id)


def clear_call(messages: list[dict[str, str]]) -> bool:
    """The adapter's single-use clearance for exactly this provider call (by its id and the
    digest of what it is about to send). False when missing, used, expired or altered."""

    call_id = getattr(messages, "call_id", None)
    if call_id is None:
        return False
    with _lock:
        call = _calls.get(call_id)
        if call is None or call.cleared or _clock() - call.created > ADMISSION_SECONDS:
            return False
        if _digest(messages) != call.digest:
            return False
        call.cleared = True
    return True


def call_cleared(messages: list[dict[str, str]]) -> bool:
    """R3: whether this provider call is live, was cleared by its caller and is not yet sent,
    for exactly these messages (an adapter's own admission check; nothing is consumed)."""

    call_id = getattr(messages, "call_id", None)
    if call_id is None:
        return False
    with _lock:
        call = _calls.get(call_id)
        return (
            call is not None
            and call.cleared
            and not call.sent
            and _clock() - call.created <= ADMISSION_SECONDS
            and _digest(messages) == call.digest
        )


def _wire_texts(value: Any, key: str | None = None) -> Iterable[str]:
    if isinstance(value, str):
        if key not in ("role", "type", "cache_control"):
            yield value
    elif isinstance(value, Mapping):
        for name, item in value.items():
            yield from _wire_texts(item, str(name))
    elif isinstance(value, list):
        for item in value:
            yield from _wire_texts(item, key)


def _wire_items(data: Mapping[str, Any]) -> list[tuple[str, str]]:
    """(role, text) for every text under ``system`` and ``messages`` of a request body. The
    role decides the rules a text passes again (a text under an unknown role is free text)."""

    items = [("system", text) for text in _wire_texts(data.get("system"), "system")]
    messages = data.get("messages")
    for message in messages if isinstance(messages, list) else [messages]:
        if isinstance(message, Mapping):
            role = message.get("role")
            rest = {key: value for key, value in message.items() if key != "role"}
            items += [
                (role if isinstance(role, str) else "user", text) for text in _wire_texts(rest)
            ]
        else:
            items += [("user", text) for text in _wire_texts(message, "messages")]
    return items


# R4 (R3-3): what a request body may hold besides its prompt. Top-level keys of the three
# adapters (anthropic_chat.payload, openrouter.payload, llm._payload), and the only places a
# string may stand outside the prompt: the model id and fixed configuration values.
_BODY_KEYS = frozenset(
    {
        "model",
        "max_tokens",
        "thinking",
        "output_config",
        "system",
        "messages",
        "stream",
        "temperature",
        "reasoning",
        "provider",
    }
)
_STRING_PATHS = frozenset(
    {
        ("model",),
        ("thinking", "type"),
        ("output_config", "effort"),
        ("reasoning", "effort"),
        ("provider", "order", "*"),
        ("provider", "only", "*"),
        ("provider", "data_collection"),
        ("provider", "quantizations", "*"),
    }
)


def _unapproved_strings(value: Any, path: tuple[str, ...]) -> bool:
    if isinstance(value, str):
        return path not in _STRING_PATHS
    if isinstance(value, Mapping):
        return any(_unapproved_strings(item, (*path, str(key))) for key, item in value.items())
    if isinstance(value, list):
        return any(_unapproved_strings(item, (*path, "*")) for item in value)
    return False


def _block_text(content: Any) -> str | None:
    """A message's text: a string, or exactly one ``{"type": "text", "text": ...}`` block."""

    if isinstance(content, str):
        return content
    if (
        isinstance(content, list)
        and len(content) == 1
        and isinstance(content[0], Mapping)
        and set(content[0]) == {"type", "text"}
        and content[0].get("type") == "text"
        and isinstance(content[0].get("text"), str)
    ):
        return str(content[0]["text"])
    return None


def wire_projection(data: Mapping[str, Any]) -> tuple[tuple[str, str], ...] | None:
    """The ordered (role, text) projection of a request body in either supported shape: the
    Anthropic one (top-level ``system`` blocks, then ``messages``) or the OpenAI one (every turn
    in ``messages``). None for anything else: an unknown key, a string outside the prompt that is
    not a fixed configuration value, or a block or message of any other shape."""

    if not set(data) <= _BODY_KEYS:
        return None
    if any(
        _unapproved_strings(value, (str(key),))
        for key, value in data.items()
        if key not in ("system", "messages")
    ):
        return None
    out: list[tuple[str, str]] = []
    system = data.get("system")
    if system is not None:
        if not isinstance(system, list):
            return None
        for block in system:
            text = _block_text([block]) if isinstance(block, Mapping) else None
            if text is None:
                return None
            out.append(("system", text))
    messages = data.get("messages")
    if not isinstance(messages, list) or not messages:
        return None
    for message in messages:
        if not isinstance(message, Mapping) or set(message) != {"role", "content"}:
            return None
        role, text = message.get("role"), _block_text(message.get("content"))
        if not isinstance(role, str) or text is None:
            return None
        if system is not None and role == "system":
            return None  # the Anthropic shape carries system text only at the top
        out.append((role, text))
    return tuple(out)


def verify_wire(messages: list[dict[str, str]], body: bytes) -> None:
    """The exact serialised HTTP body of one provider call, just before it is sent: every text
    under ``system`` and ``messages`` must pass this call's rules again (by its role).

    R2 (D-2): only a live provider call that its caller has cleared (``clear_call``, which runs
    before any budget is reserved) and has not yet sent, for exactly these messages (the call's
    digest), passes; it then cannot pass again. R4 (R3-3): the body's ordered (role, text)
    projection must equal exactly the cleared call's protected messages, in either supported
    body shape (``wire_projection``): no duplicated, substituted, reordered or added prompt
    text, exactly the one authorised final user turn, and no other text-bearing field.
    Anything else is refused (PrivacyRefused)."""

    call_id = getattr(messages, "call_id", None)
    if call_id is None:
        raise PrivacyRefused("WIRE_UNADMITTED")
    with _lock:
        call = _calls.get(call_id)
        if (
            call is None
            or not call.cleared
            or call.sent
            or _clock() - call.created > ADMISSION_SECONDS
            or _digest(messages) != call.digest
        ):
            raise PrivacyRefused("WIRE_UNCLEARED")
        call.sent = True
    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise PrivacyRefused("WIRE_UNREADABLE") from None
    if not isinstance(data, Mapping):
        raise PrivacyRefused("WIRE_UNREADABLE")
    projection = wire_projection(data)
    if projection is None:
        raise PrivacyRefused("WIRE_UNAPPROVED_SHAPE")
    items = list(projection)
    # R3: no history on the wire: system texts and one user turn only.
    if any(role not in ("system", "user") for role, _ in items) or (
        sum(1 for role, _ in items if role == "user") != 1 or items[-1][0] != "user"
    ):
        raise PrivacyRefused("WIRE_HISTORY")
    # R4 (R3-3): exactly the cleared call's protected messages, in order.
    if projection != call.projection:
        raise PrivacyRefused("WIRE_PROJECTION")
    for role, text in items:
        if role == "system":
            mode = TRUSTED if text in call.trusted else SERVICE
        else:
            mode = PERSON if call.person_written else SERVICE
        if mode == PERSON:
            raise PrivacyRefused("WIRE_PERSON_TEXT")  # R4 (R3-1): never person-written text
        code = _scan_residual(text, call.shield, issued=call.emitted, mode=mode)
        if code is not None:
            raise PrivacyRefused(f"WIRE_{code}")


def remeasure(protected: Protected, header: list[dict[str, str]]) -> Protected:
    """R2 (D-1): a capacity measurement of a payload this boundary already protected: a new,
    single-use provider call sending ``header`` (fixed text, protected with the same rules and
    placeholders) followed by exactly the protected messages, checked again before anything is
    sent. The caller clears and releases it like any other call."""

    shield = protected.shield
    head = [
        {**message, "content": shield.protect_text(str(message.get("content", "")), SERVICE)}
        for message in header
    ]
    out = [*head, *(dict(message) for message in protected.messages)]
    for message in out:
        content = message["content"]
        mode = (
            TRUSTED
            if content in protected.trusted
            else PERSON
            if content in protected.person
            else SERVICE
        )
        code = _scan_residual(content, shield, mode=mode)
        if code is not None:
            raise PrivacyRefused(code)
    emitted = frozenset(
        found.group(0) for message in out for found in ALIAS.finditer(message["content"])
    )
    call_id = secrets.token_hex(16)
    sent = ProtectedMessages(out, call_id)
    now = _clock()
    with _lock:
        _prune(now)
        _calls[call_id] = _Call(
            _digest(sent),
            shield,
            emitted,
            now,
            trusted=protected.trusted,
            person=protected.person,
            # R4: the origin of the re-sent turn is the protected payload's (never person text,
            # which is not admitted); the call record's default stays fail-closed.
            person_written=bool(protected.person),
            projection=_projection(sent),
        )
    return Protected(
        messages=sent,
        shield=shield,
        emitted=emitted,
        call_id=call_id,
        trusted=protected.trusted,
        person=protected.person,
    )


def release(protected: Protected | None) -> None:
    """Forget one provider call (its mapping stays only in the caller's Protected)."""

    if protected is not None and protected.call_id is not None:
        with _lock:
            _calls.pop(protected.call_id, None)


def preview(messages: list[dict[str, str]]) -> str | None:
    """The refusal code these admitted messages would get at the boundary, or None. Nothing is
    sent and the admission is not consumed."""

    try:
        entry = _peek(messages)
        protect(
            list(messages),
            entry.known,
            person_written=entry.person_written,
            controlled=entry.controlled,
        )
    except PrivacyRefused as refused:
        return f"PRIVACY_{refused.code}"
    return None


def pending() -> tuple[int, int]:
    """(open admissions, open provider calls): for resource checks in tests."""

    with _lock:
        return len(_admissions), len(_calls)


# R3 (P3 "IT metadata request"): what BoundedModel passes through to the model it wraps.
# Only non-callable attributes (configuration, flags, ``_url`` for classification) and nothing
# private except ``_url``; every method it offers is its own. ``inner`` stays reachable for
# classification (data_access.model_class); its adapter is bound to ``verify_wire``, so a
# direct prompt-bearing call on it is refused (WIRE_UNADMITTED).
_PASSED_PRIVATE = frozenset({"_url"})


class BoundedModel:
    """A model IT configured on an endpoint that is not literal loopback (an external
    provider): every call passes the privacy boundary, as the built-in external models do.

    R2 (D-1): that includes token counting (``prompt_tokens``, ``measure``), so a qualification
    and its capacity check send only protected payloads, exactly as the activated model does;
    the adapter's own request internals are not reachable through this wrapper. With
    ``retain_largest`` (a qualification only) it keeps the largest protected payload it sent,
    in memory, for the capacity check (``measure_largest``), until ``forget``. Everything else
    is the wrapped model's (data_access.model_class unwraps it)."""

    def __init__(self, inner: Any, *, retain_largest: bool = False) -> None:
        self.inner = inner
        self._retain = retain_largest
        self._largest: Protected | None = None
        self.largest_bytes = 0
        self.largest_messages = 0
        # The adapter at the bottom of the stack (through the prompt-size bound and the
        # qualification watcher) checks every request body it builds against this boundary.
        target = inner
        for _ in range(8):
            bind = getattr(type(target), "bind_wire_check", None)
            if callable(bind):
                bind(target, verify_wire)
                break
            fields = getattr(target, "__dict__", {})
            target = fields.get("_inner", fields.get("inner"))
            if target is None:
                break

    def __getattr__(self, name: str) -> Any:
        if name == "inner" or (name.startswith("_") and name not in _PASSED_PRIVATE):
            raise AttributeError(name)
        value = getattr(self.inner, name)
        if callable(value):
            raise AttributeError(name)  # every method this wrapper offers is its own
        return value

    def listed_models(self) -> list[str] | None:
        """The one case-data-free request (D-142 R3, documented exception): an authenticated,
        bodyless ``GET /models`` that sends no prompt, message or case value, only the
        configured credential. Used by the connection test to confirm the model id."""

        listed = getattr(self.inner, "listed_models", None)
        return listed() if callable(listed) else None

    @property
    def name(self) -> str:
        return str(self.inner.name)

    def _seen(self, protected: Protected) -> None:
        if not self._retain:
            return
        size = message_bytes(protected.messages)
        if size > self.largest_bytes or self._largest is None:
            self._largest = protected
            self.largest_bytes = size
            self.largest_messages = len(protected.messages)

    def complete(self, messages: list[dict[str, str]]) -> ModelAnswer:
        protected = outbound(messages)
        try:
            if not clear_call(protected.messages):
                raise PrivacyRefused("CALL_UNCLEARED")
            self._seen(protected)
            return protected.restore_answer(self.inner.complete(protected.messages))
        finally:
            release(protected)

    async def stream(self, messages: list[dict[str, str]]) -> AsyncGenerator[Piece, None]:
        from contextlib import aclosing

        protected = outbound(messages)
        try:
            if not clear_call(protected.messages):
                raise PrivacyRefused("CALL_UNCLEARED")
            self._seen(protected)
            async with (
                aclosing(self.inner.stream(protected.messages)) as source,
                aclosing(protected.restore_stream(source)) as restored,
            ):
                async for piece in restored:
                    yield piece
        finally:
            release(protected)

    def _count(self, protected: Protected) -> tuple[int | None, list[dict[str, str]]]:
        try:
            if not clear_call(protected.messages):
                raise PrivacyRefused("CALL_UNCLEARED")
            return self.inner.prompt_tokens(protected.messages), list(protected.messages)
        finally:
            release(protected)

    def measure(self, messages: list[dict[str, str]]) -> tuple[int | None, list[dict[str, str]]]:
        """The server's prompt-token count for these admitted messages as the boundary sends
        them, and the messages actually sent (so a byte bound is taken on the real payload)."""

        return self._count(outbound(messages))

    def prompt_tokens(self, messages: list[dict[str, str]]) -> int | None:
        return self.measure(messages)[0]

    def measure_largest(
        self, header: list[dict[str, str]]
    ) -> tuple[int | None, list[dict[str, str]]] | None:
        """The count for ``header`` plus the largest protected payload this model sent (None
        when it kept none), and the messages actually sent."""

        if self._largest is None:
            return None
        return self._count(remeasure(self._largest, header))

    def forget(self) -> None:
        self._largest = None

    def warm(self, messages: list[dict[str, str]]) -> None:
        return None  # a warm-up would send case text outside the boundary
