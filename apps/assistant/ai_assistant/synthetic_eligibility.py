"""D-095 development synthetic eligibility: which cases the remote test model may answer.

D-094 (synthetic_boundary.py) admits one fixed case and checks every value and every word
against lists generated from that case. D-095 replaces the lists with provenance, for the
owner's local development set-up only (``mode``): a case is eligible when the backend's own
reply shows that everything the prompt carries came from approved synthetic sources. Any doubt
fails closed: the RM gets the deterministic case-data answer and nothing is sent.

    case        the company's (UEN, legal name) is an approved synthetic company (the backend's
                Mock ACRA fixtures and the project's synthetic company packs), its registry
                details came from ACRA in MOCK mode, and the requested UEN and the registry
                acquisition are for that company. A Mock flag alone is not enough, and neither
                is a name or a UEN alone.
    documents   the document list and the backend's document digests were both read, and they
                name the same documents (id and version). Every document on the case is a
                verified synthetic fixture: the SHA-256 the backend computed from its uploaded
                bytes at upload (stored on the document record, served by the case-scoped
                document-digests route) is the digest of a synthetic fixture file the
                repository tracks, with that file's media type and byte size. Anything else
                (another file, a renamed real document, one altered byte, a record stored
                before the backend kept digests, an unreadable digest list) makes the whole
                case ineligible, and so does a document the summary names that is not one of
                the verified ones.
    values      values a person typed (case-creation input, manual decisions, review entries)
                must equal a value the trusted sources hold (the Mock registry record, a
                verified document's extraction, an approved company identity); values from
                those sources need no list. A GoldTier id must be one the Mock GoldTier connector
                issues (GT-MOCK-...) or the synthetic fixture id.
    viewer      the viewer is a seeded POC user
    knowledge   only unchanged repository guidance and the synthetic seed (as in D-094)
    text        every message: printable ASCII, line breaks, tabs and the named typographic marks
                only. The question and history may use any words, but not personal or account
                identifiers the case does not already hold: e-mail addresses, NRIC/FIN or
                UEN-shaped ids, dates, or a run of five or more digits (also when split by
                spaces, dashes, dots or brackets).

The text screen guards against accidental entry; it cannot recognise a person's name or
details spelled out in words, so the owner must still not type real customer details.

The checked messages get a single-use ticket (``approve``); the remote model refuses a call
whose exact messages hold no ticket and do not pass the D-094 text check (``admitted``), so
no caller can skip the case check.
"""

import hashlib
import json
import re
import threading
import time
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from .clm_client import CaseSnapshot
from .knowledge.models import Entry
from .synthetic_boundary import (
    _TIMESTAMP,
    _dict,
    _list,
    _unchecked_characters,
    approved_entry,
    data_values,
    normalize,
)

ELIGIBILITY_FILE = Path(__file__).with_name("synthetic_eligibility.json")
SCHEMA = "clm-assistant-synthetic-eligibility/2"
DECISION_ID = "D-095"
# Ids the backend's Mock GoldTier connector issues, and the synthetic fixture id.
_MOCK_GOLDTIER_ID = re.compile(r"GT-MOCK-[A-Z0-9-]{1,80}|GT-SYNTHETIC-[0-9]{4}")
# A ticket is used once, within this many seconds (the answer starts right after the check).
TICKET_SECONDS = 120.0
_MAX_TICKETS = 256
_SHA256 = re.compile(r"[0-9a-f]{64}")

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_NRIC = re.compile(r"\b[STFGM]\d{7}[A-Z]\b", re.IGNORECASE)
_UEN = re.compile(r"\b(?:\d{8,9}[A-Z]|[TSR]\d{2}[A-Z]{2}\d{4}[A-Z])\b", re.IGNORECASE)
_MONTHS = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*"
_DATE = re.compile(
    r"\b\d{1,4}[/.-]\d{1,2}[/.-]\d{1,4}\b"
    rf"|\b\d{{1,2}}(?:st|nd|rd|th)? {_MONTHS},? \d{{2,4}}\b"
    rf"|\b{_MONTHS} \d{{1,2}}(?:st|nd|rd|th)?,? \d{{2,4}}\b",
    re.IGNORECASE,
)
# Digits that may be split by spaces, dashes, dots, slashes or brackets (a phone, account or
# card number typed in pieces).
_DIGIT_RUN = re.compile(r"\d(?:[\d\s().+/-]*\d)?")
_MAX_FREE_DIGITS = 4


@dataclass(frozen=True)
class Manifest:
    source_system: str
    environments: frozenset[str]
    companies: frozenset[tuple[str, str]]
    # Approved fixture digest -> (media type, size in bytes).
    documents: dict[str, tuple[str, int]]
    viewers: frozenset[str]


@lru_cache(maxsize=1)
def manifest(path: Path = ELIGIBILITY_FILE) -> Manifest:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        raise ValueError("unknown synthetic eligibility schema")
    return Manifest(
        source_system=str(data["registry"]["source_system"]),
        environments=frozenset(str(item) for item in data["registry"]["environments"]),
        companies=frozenset(
            (str(item["uen"]), str(item["legal_name"])) for item in data["companies"]
        ),
        documents={
            str(item["sha256"]): (str(item["media_type"]), int(item["size_bytes"]))
            for item in data["documents"]
        },
        viewers=frozenset(str(item) for item in data["viewers"]),
    )


def _fold(value: object) -> str:
    return normalize(str(value)).casefold()


def _document_key(document: dict[str, Any]) -> tuple[str, object]:
    return str(document.get("document_id")), document.get("document_version")


def _verify_documents(
    documents: list[dict[str, Any]],
    digests: list[dict[str, Any]] | None,
    approved: Manifest,
) -> tuple[str | None, set[str]]:
    """(refusal or None, display names of the verified documents). The digest list must name
    exactly the listed documents; each digest must be an approved fixture's, with that
    fixture's media type and size."""

    if not documents:
        return None, set()
    if digests is None:
        return "SYNTHETIC_DOCUMENT_DIGEST_UNAVAILABLE", set()
    by_key: dict[tuple[str, object], object] = {}
    for item in digests:
        key = _document_key(_dict(item))
        if key in by_key:
            return "SYNTHETIC_DOCUMENT_DIGEST_UNAVAILABLE", set()
        by_key[key] = _dict(item).get("content_sha256")
    if set(by_key) != {_document_key(document) for document in documents}:
        return "SYNTHETIC_DOCUMENT_DIGEST_UNAVAILABLE", set()
    verified: set[str] = set()
    for document in documents:
        digest = by_key[_document_key(document)]
        if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
            return "SYNTHETIC_DOCUMENT_DIGEST_UNAVAILABLE", set()
        fixture = approved.documents.get(digest)
        if fixture is None or fixture != (document.get("media_type"), document.get("size_bytes")):
            return "SYNTHETIC_DOCUMENT_NOT_VERIFIED", set()
        verified.add(str(document.get("display_name") or ""))
    return None, verified


def _company_problem(snapshot: CaseSnapshot, approved: Manifest) -> bool:
    case = _dict(snapshot.summary.get("case"))
    entity = _dict(case.get("entity"))
    source = _dict(entity.get("source"))
    uen = str(entity.get("registration_number") or "")
    name = str(entity.get("legal_name") or "")
    requested = case.get("requested_uen")
    acquisition = _dict(case.get("registry_acquisition"))
    acquired = acquisition.get("requested_identifier")
    return (
        (uen, name) not in approved.companies
        or (requested is not None and str(requested).strip().upper() != uen)
        or (acquired is not None and str(acquired).strip().upper() != uen)
        or source.get("source_system") != approved.source_system
        or source.get("environment") not in approved.environments
    )


def _trusted_values(
    snapshot: CaseSnapshot, facts: dict[str, Any], verified: set[str], approved: Manifest
) -> set[str]:
    """Values from the trusted sources, folded: the Mock registry record, the extraction of a
    verified document, the approved company identities and the backend's source label."""

    entity = _dict(_dict(snapshot.summary.get("case")).get("entity"))
    company = _dict(facts.get("company"))
    trusted: list[Any] = [
        entity.get("legal_name"),
        entity.get("registration_number"),
        entity.get("country_of_incorporation"),
        entity.get("entity_status"),
        entity.get("registration_date"),
        company.get("registered_address"),
        company.get("source"),
        *_dict(entity.get("registered_address")).values(),
        *verified,
    ]
    for uen, name in approved.companies:
        trusted += [uen, name]
    for document in snapshot.documents:
        if str(_dict(document).get("display_name") or "") not in verified:
            continue
        for field in _list(_dict(document).get("fields")):
            data = _dict(field)
            trusted += [
                data.get(key)
                for key in ("original_extracted_value", "normalized_value", "canonical_value")
            ]
            trusted += [_dict(item).get("value") for item in _list(data.get("candidates"))]
    # Reconciliation observations whose own source is the Mock registry, or the extraction of
    # a verified document on this case (by its id). A reviewer's correction is also reported as
    # a DOCUMENT_IDP observation (source HUMAN_REVIEW, evidence DOCUMENT_REVIEW_*): it is typed
    # text, so it is never trusted here and must equal a trusted value like any typed value.
    verified_ids = {
        str(_dict(document).get("document_id"))
        for document in snapshot.documents
        if str(_dict(document).get("display_name") or "") in verified
    }
    for item in _list(_dict(snapshot.summary.get("reconciliation")).get("discrepancies")):
        for observation in _list(_dict(item).get("observations")):
            data = _dict(observation)
            registry = (
                data.get("source_kind") == "REGISTRY"
                and data.get("source_system") == approved.source_system
                and data.get("environment") in approved.environments
            )
            extraction = (
                data.get("source_kind") == "DOCUMENT_IDP"
                and str(data.get("document_id")) in verified_ids
                and str(data.get("document_display_name") or "") in verified
                and data.get("source_system") not in (None, "HUMAN_REVIEW")
                and not str(data.get("evidence_reference") or "").startswith("DOCUMENT_REVIEW")
            )
            if registry or extraction:
                trusted.append(data.get("normalized_value"))
    return {_fold(value) for value in trusted if value not in (None, "")}


def _identifiers(facts: dict[str, Any], approved: Manifest) -> list[str]:
    """Identifier-like strings the case already holds (longest first), which a question may
    quote back: its UEN, postal code, unit numbers, the approved companies' UENs."""

    text = json.dumps(facts, ensure_ascii=True, default=str)
    found = set(re.findall(r"[#A-Za-z0-9-]*\d[A-Za-z0-9-]*", text))
    found |= {uen for uen, _ in approved.companies}
    # Short numbers are never removed, so they cannot hide part of a date or a longer id.
    return sorted((item for item in found if len(item) >= 5), key=len, reverse=True)


def _personal_identifier(text: str, allowed: list[str]) -> bool:
    for item in allowed:
        # Whole identifiers only: "123456" must not hide part of "S1234567D".
        text = re.sub(
            rf"(?<![A-Za-z0-9]){re.escape(item)}(?![A-Za-z0-9])", " ", text, flags=re.IGNORECASE
        )
    if _EMAIL.search(text) or _NRIC.search(text) or _UEN.search(text) or _DATE.search(text):
        return True
    return any(
        sum(char.isdigit() for char in run) > _MAX_FREE_DIGITS for run in _DIGIT_RUN.findall(text)
    )


def check_text(messages: list[dict[str, str]], facts: dict[str, Any], approved: Manifest) -> bool:
    """True when every message passes the character screen, and what a person wrote (the
    question and history) holds no personal or account identifier the case does not hold."""

    allowed = _identifiers(facts, approved)
    for message in messages:
        content = message.get("content") or ""
        if _unchecked_characters(content):
            return False
        role = message.get("role")
        if role == "system":
            continue  # built by the service from the checked facts and approved knowledge
        if role == "assistant":
            content = _TIMESTAMP.sub(" ", content)  # the service's own case-data timestamps
        if _personal_identifier(content, allowed):
            return False
    return True


def check(
    snapshot: CaseSnapshot,
    facts: dict[str, Any],
    messages: list[dict[str, str]],
    entries: Iterable[Entry],
    *,
    digests: list[dict[str, Any]] | None = None,
) -> str | None:
    """None when the question may go to the remote model (the messages then hold a ticket);
    otherwise a closed reason. ``digests``: the backend's document-digests reply for this case
    (None when it could not be read)."""

    try:
        approved = manifest()
    except (OSError, ValueError, KeyError, TypeError):
        return "SYNTHETIC_ELIGIBILITY_UNAVAILABLE"
    if _company_problem(snapshot, approved):
        return "SYNTHETIC_CASE_NOT_APPROVED"
    if not snapshot.documents_loaded:
        return "SYNTHETIC_DOCUMENTS_UNAVAILABLE"
    refusal, verified = _verify_documents(
        [_dict(document) for document in snapshot.documents], digests, approved
    )
    if refusal is not None:
        return refusal
    if any(
        _dict(observation).get("document_display_name") not in (None, "")
        and str(_dict(observation).get("document_display_name")) not in verified
        for item in _list(_dict(snapshot.summary.get("reconciliation")).get("discrepancies"))
        for observation in _list(_dict(item).get("observations"))
    ):
        return "SYNTHETIC_DOCUMENT_NOT_VERIFIED"
    if str(_dict(facts.get("viewer")).get("name") or "") not in approved.viewers:
        return "SYNTHETIC_VIEWER_NOT_APPROVED"
    goldtier_id = _dict(facts.get("goldtier")).get("goldtier_id")
    if goldtier_id not in (None, "") and not _MOCK_GOLDTIER_ID.fullmatch(str(goldtier_id)):
        return "SYNTHETIC_TARGET_NOT_VERIFIED"
    trusted = _trusted_values(snapshot, facts, verified, approved)
    if goldtier_id not in (None, ""):
        trusted.add(_fold(goldtier_id))
    if any(value.casefold() not in trusted for value in data_values(facts)):
        return "SYNTHETIC_VALUE_NOT_GROUNDED"
    if any(not approved_entry(entry) for entry in entries):
        return "SYNTHETIC_KNOWLEDGE_NOT_APPROVED"
    if not check_text(messages, facts, approved):
        return "SYNTHETIC_TEXT_NOT_APPROVED"
    approve(messages)
    return None


# --- tickets: the remote model sends only messages that passed ``check`` ----------------------

_tickets: dict[str, float] = {}
_tickets_lock = threading.Lock()


def _digest(messages: list[dict[str, str]]) -> str:
    return hashlib.sha256(
        json.dumps(messages, sort_keys=True, ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def approve(messages: list[dict[str, str]]) -> None:
    now = time.monotonic()
    with _tickets_lock:
        for digest in [key for key, at in _tickets.items() if now - at > TICKET_SECONDS]:
            del _tickets[digest]
        if len(_tickets) >= _MAX_TICKETS:
            del _tickets[min(_tickets, key=_tickets.__getitem__)]
        _tickets[_digest(messages)] = now


def admitted(messages: list[dict[str, str]]) -> bool:
    """Use the ticket for exactly these messages, if one is still valid."""

    digest = _digest(messages)
    with _tickets_lock:
        at = _tickets.pop(digest, None)
    return at is not None and time.monotonic() - at <= TICKET_SECONDS


def mode(settings: Any) -> bool:
    """D-095 is named, on top of a ready D-094 local test mode (remote_test.readiness)."""

    from .remote_test import readiness

    return settings.synthetic_dev_decision == DECISION_ID and readiness(settings) is None
