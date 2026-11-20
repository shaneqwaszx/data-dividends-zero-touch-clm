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

import copy
import hashlib
import json
import re
import threading
import time
from collections.abc import Iterable
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
from typing import Any

from .clm_client import CaseSnapshot
from .knowledge.models import Entry
from .privacy_boundary import is_trusted_text
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
    viewer: bool = True,
) -> str | None:
    """None when the question may go to the remote model (the messages then hold a ticket);
    otherwise a closed reason. ``digests``: the backend's document-digests reply for this case
    (None when it could not be read). ``viewer=False``: D-139, only for the hosted Try with this
    change, where D-130 decides who may ask (the Support capability and team scope) and the
    viewer is removed from the prompt (OD-G8); every other rule still applies."""

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
    if viewer and str(_dict(facts.get("viewer")).get("name") or "") not in approved.viewers:
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


# --- D-142 R1 (proposed): the trusted POC admission for the pseudonymised policy ----------------

POC_DECISION_ID = "D-142"
# The backend's own source environments (apps/backend/app/domain/models.py SourceEnvironment):
# MOCK is synthetic by construction; SANDBOX is a sponsor or registry test environment whose
# records are not the project's synthetic data and so are treated as sponsor data.
_SPONSOR_ENVIRONMENTS = frozenset({"SANDBOX"})
# Operation statuses under which nothing was acquired (apps/backend RegistryOperationStatus).
_ABSENT_STATUSES = frozenset({"FAILED", "NOT_ATTEMPTED", "UNSUPPORTED"})


def _provenance_problem(provenance: Any, approved: Manifest) -> str | None:
    data = _dict(provenance)
    if data.get("environment") in _SPONSOR_ENVIRONMENTS:
        return "POC_SPONSOR_DATA"
    if (
        data.get("provider") != approved.source_system
        or data.get("environment") not in approved.environments
    ):
        return "POC_PROVENANCE_UNKNOWN"
    return None


def _poc_registry_problem(snapshot: CaseSnapshot, approved: Manifest) -> str | None:
    """The registry part of the POC admission, by the backend's recorded provenance: the
    company's details came from the approved registry in MOCK mode, for the identifier the case
    requested. No company list: any company a Mock registry returned qualifies."""

    case = _dict(snapshot.summary.get("case"))
    entity = _dict(case.get("entity"))
    source = _dict(entity.get("source"))
    environment = source.get("environment")
    if environment in _SPONSOR_ENVIRONMENTS:
        return "POC_SPONSOR_DATA"
    if (
        not entity
        or source.get("source_system") != approved.source_system
        or environment not in approved.environments
    ):
        return "POC_PROVENANCE_UNKNOWN"
    uen = str(entity.get("registration_number") or "").strip().upper()
    if not uen or not str(entity.get("legal_name") or "").strip():
        return "POC_PROVENANCE_UNKNOWN"
    # R2/R3: every record family the registry acquisition holds carries the same approved
    # provenance (ACRA in MOCK mode: the ACRA Mock and the Marketplace Mock alike). A SANDBOX
    # record is sponsor data, a record of unknown or missing provenance is uncertain.
    acquisition = _dict(case.get("registry_acquisition"))
    for family in ("ownership_parties", "officers", "relationships"):
        for record in _list(acquisition.get(family)):
            refusal = _provenance_problem(_dict(record).get("provenance"), approved)
            if refusal is not None:
                return refusal
    # An operation result says what the registry returned for one operation. With provenance,
    # it must be the approved one. Without, it is authoritative absence only when nothing was
    # acquired (FAILED, NOT_ATTEMPTED or UNSUPPORTED with no records); any other result without
    # provenance (COMPLETE, EMPTY, or records counted) is a claim of unknown provenance.
    for result in _list(acquisition.get("operation_results")):
        data = _dict(result)
        if data.get("provenance") is not None:
            refusal = _provenance_problem(data.get("provenance"), approved)
            if refusal is not None:
                return refusal
        elif data.get("status") not in _ABSENT_STATUSES or data.get("record_count") not in (0,):
            return "POC_PROVENANCE_UNKNOWN"
    requested = case.get("requested_uen")
    acquired = _dict(case.get("registry_acquisition")).get("requested_identifier")
    if (requested is not None and str(requested).strip().upper() != uen) or (
        acquired is not None and str(acquired).strip().upper() != uen
    ):
        return "POC_PROVENANCE_UNKNOWN"
    return None


def registry_provenance_problem(summary: object) -> str | None:
    """D-146 C11-2 (owner decision 2, synthetic-only aggregates): the registry provenance rule
    above (``_poc_registry_problem``) on one case summary, with the approved manifest. None only
    when the company and every registry record family came from ACRA in MOCK mode; SANDBOX,
    unknown or missing provenance, an unreadable summary or manifest is a closed reason."""

    if not isinstance(summary, dict):
        return "POC_PROVENANCE_UNKNOWN"
    try:
        approved = manifest()
    except (OSError, ValueError, KeyError, TypeError):
        return "POC_ELIGIBILITY_UNAVAILABLE"
    return _poc_registry_problem(CaseSnapshot(summary=summary, documents=[], actor={}), approved)


def poc_check(
    snapshot: CaseSnapshot,
    facts: dict[str, Any],
    entries: Iterable[Entry],
    *,
    digests: list[dict[str, Any]] | None = None,
) -> str | None:
    """D-142 R1 (P1-3): None when the case's data is classified as synthetic or Mock POC data by
    authoritative provenance, independent of the D-095 company and viewer lists; otherwise a
    closed reason. RBAC and team scope have already decided that the user may read the case.

        registry    the company came from the approved registry in MOCK mode for the requested
                    identifier (any company; no list). SANDBOX data is sponsor data: refused
        documents   every document is a tracked synthetic fixture by the backend's own digest.
                    The data contract holds no other authoritative provenance for an upload, so
                    any other upload is uncertain and refused (owner decision OD-1)
        target      a GoldTier id the Mock connector issued, or none (a Sandbox id: sponsor data)
        values      every value a person typed equals a value the trusted sources hold
        knowledge   only unchanged repository guidance and the synthetic seed

    The question and history are user-entered text: the privacy boundary transforms and
    validates them on every call. Nothing here infers safety from the deployment, from the
    viewer's access, or from an upload being unfamiliar."""

    try:
        approved = manifest()
    except (OSError, ValueError, KeyError, TypeError):
        return "POC_ELIGIBILITY_UNAVAILABLE"
    refusal = _poc_registry_problem(snapshot, approved)
    if refusal is not None:
        return refusal
    if not snapshot.documents_loaded:
        return "POC_DOCUMENTS_UNAVAILABLE"
    problem, verified = _verify_documents(
        [_dict(document) for document in snapshot.documents], digests, approved
    )
    if problem is not None:
        return "POC_DOCUMENT_PROVENANCE_UNKNOWN"
    # R3: an observation is bound to its document by id (and version), never by file name:
    # every document-sourced observation must name a verified document of this case.
    verified_ids = {_document_key(_dict(document)) for document in snapshot.documents}
    for item in _list(_dict(snapshot.summary.get("reconciliation")).get("discrepancies")):
        for observation in _list(_dict(item).get("observations")):
            data = _dict(observation)
            if data.get("document_id") is None:
                if data.get("document_display_name") not in (None, "") or str(
                    data.get("source_kind") or ""
                ).startswith("DOCUMENT"):
                    return "POC_DOCUMENT_PROVENANCE_UNKNOWN"
                continue
            document_id = str(data.get("document_id"))
            version = data.get("document_version")
            if not any(
                key == document_id and (version is None or version == kept)
                for key, kept in verified_ids
            ):
                return "POC_DOCUMENT_PROVENANCE_UNKNOWN"
    goldtier_id = _dict(facts.get("goldtier")).get("goldtier_id")
    if goldtier_id not in (None, "") and not _MOCK_GOLDTIER_ID.fullmatch(str(goldtier_id)):
        return "POC_SPONSOR_DATA"
    trusted = _trusted_values(snapshot, facts, verified, approved)
    if goldtier_id not in (None, ""):
        trusted.add(_fold(goldtier_id))
    if any(value.casefold() not in trusted for value in data_values(facts)):
        return "POC_VALUE_NOT_GROUNDED"
    if any(not approved_entry(entry) for entry in entries):
        return "POC_KNOWLEDGE_NOT_APPROVED"
    return None


# --- D-142 R2 (owner direction): unverified uploads are withheld, not the whole case ------------


@dataclass(frozen=True)
class PocView:
    """The case as external inference may receive it under the pseudonymised policy.

        snapshot           the same case without every uploaded document that is not a tracked
                           synthetic fixture by the backend's own digest (bound to its document
                           id, version and digest, never to its file name), and without what
                           was derived from one: every record naming that document id is
                           removed, and document-read values in exception evidence (which name
                           no document) are blanked
        digests            the digests of the documents kept (all verified)
        withheld           how many documents were withheld
        withheld_documents (document id, version, digest) of each withheld document
        withheld_values    the text values read from a withheld document and its name (folded,
                           two or more characters)
        withheld_numbers   every number read from a withheld document, whatever its length (R3:
                           a short or numeric value is still upload-derived content)

    The boundary's backstop (``withheld_present``) refuses a prompt that still holds a withheld
    value or number unless the independently authorised facts hold it too. Nothing is
    persisted and nothing in the data contract changes: this is a view."""

    snapshot: CaseSnapshot
    digests: list[dict[str, Any]]
    withheld: int
    withheld_values: frozenset[str]
    withheld_documents: frozenset[tuple[str, object, str | None]] = frozenset()
    withheld_numbers: frozenset[Decimal] = frozenset()


_DOCUMENT_READ_KEYS = frozenset(
    {"document_value", "original_extracted_value", "reviewed_value", "review_note"}
)
# R4 (R3-2): free text the backend derives from case events (timeline messages, exception
# explanations, step results, notes). Its source lineage is not recorded, so while any upload is
# withheld it is withheld from the external view; structured codes and values stay.
_DERIVED_TEXT_KEYS = frozenset({"explanation", "safe_result", "message", "note", "detail"})
# The value-bearing keys of a record that names a withheld document (an observation, a
# reviewer correction, a field): what it carried is upload-derived, whatever its text.
_RECORD_VALUE_KEYS = frozenset(
    {
        "normalized_value",
        "selected_value",
        "reviewed_value",
        "original_extracted_value",
        "value",
        "document_value",
        "display_name",
        "document_display_name",
    }
)
_NUMBER = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?![\w])")


def _numbers(text: str) -> set[Decimal]:
    found: set[Decimal] = set()
    for match in _NUMBER.finditer(re.sub(r"(?<=\d),(?=\d{3}\b)", "", text)):
        try:
            found.add(Decimal(match.group(0)).normalize())
        except InvalidOperation:
            continue
    return found


def _names_withheld(item: dict[str, Any], withheld: frozenset[tuple[str, object]]) -> bool:
    if item.get("document_id") is None:
        return False
    key = str(item.get("document_id"))
    version = item.get("document_version")
    return (key, version) in withheld or (
        version is None and any(key == doc for doc, _ in withheld)
    )


def _record_values(value: Any, out: list[Any]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in _RECORD_VALUE_KEYS and isinstance(item, (str, int, float, Decimal)):
                out.append(item)
            else:
                _record_values(item, out)
    elif isinstance(value, list):
        for item in value:
            _record_values(item, out)


def _without(
    value: Any, withheld: frozenset[tuple[str, object]], removed: list[dict[str, Any]]
) -> Any:
    """``value`` without every record that names a withheld document (by id and version; a
    record that names the id with no version is removed too, and collected in ``removed``),
    with document-read values and backend-derived free text blanked."""

    if isinstance(value, list):
        kept = []
        for item in value:
            if isinstance(item, dict) and _names_withheld(item, withheld):
                removed.append(item)
                continue
            kept.append(_without(item, withheld, removed))
        return kept
    if isinstance(value, dict):
        return {
            key: None
            if key in _DOCUMENT_READ_KEYS or key in _DERIVED_TEXT_KEYS
            else _without(item, withheld, removed)
            for key, item in value.items()
        }
    return value


def _walk(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


def _registry_observation(item: dict[str, Any], approved: Manifest | None) -> dict[str, Any]:
    for observation in _list(item.get("observations")):
        data = _dict(observation)
        if (
            approved is not None
            and data.get("source_kind") == "REGISTRY"
            and data.get("source_system") == approved.source_system
            and data.get("environment") in approved.environments
        ):
            return data
    return {}


def _upload_decisions(
    summary: dict[str, Any], withheld_ids: set[str], approved: Manifest | None
) -> list[tuple[str, str, str | None]]:
    """(field, selected value, independent registry value or None) for every reconciliation
    decision that selected an observation from a withheld upload: by the recorded selected
    observation id (its lineage), never by comparing text."""

    found: list[tuple[str, str, str | None]] = []
    for item in _walk(summary):
        if "observations" not in item or not isinstance(item.get("decision"), dict):
            continue
        decision = item["decision"]
        selected = str(decision.get("selected_observation_id") or "")
        value = decision.get("selected_value")
        if selected and selected in withheld_ids and isinstance(value, str):
            registry = _registry_observation(item, approved).get("normalized_value")
            found.append(
                (
                    str(item.get("field_name") or ""),
                    decision["selected_value"],
                    registry if isinstance(registry, str) and registry.strip() else None,
                )
            )
    return found


def _restore_canonical(summary: Any, decisions: list[tuple[str, str, str | None]]) -> Any:
    """The canonical values an upload-derived decision promoted (the backend promotes only the
    legal name) replaced by the independent registry observation's value, or withheld (None)
    when the registry holds none; the decision's selected value is withheld too."""

    promoted = {
        (field, _fold(selected)): registry
        for field, selected, registry in decisions
        if field == "legal_name"
    }
    for item in _walk(summary):
        if isinstance(item.get("decision"), dict) and item["decision"].get("selected_value") in {
            selected for _, selected, _ in decisions
        }:
            item["decision"] = {
                **item["decision"],
                "selected_value": None,
                "selected_observation_id": None,
            }
        name = item.get("legal_name")
        if isinstance(name, str) and ("legal_name", _fold(name)) in promoted:
            item["legal_name"] = promoted[("legal_name", _fold(name))]
    return summary


def poc_view(snapshot: CaseSnapshot, digests: list[dict[str, Any]] | None) -> PocView:
    """The external view of this case (see PocView). ``digests`` None: the digest list could
    not be read, so no document is verified and every one is withheld."""

    try:
        approved: Manifest | None = manifest()
    except (OSError, ValueError, KeyError, TypeError):
        approved = None
    documents = [_dict(document) for document in snapshot.documents]
    by_key: dict[tuple[str, object], dict[str, Any]] = {}
    unusable = digests is None or approved is None
    for item in digests or []:
        key = _document_key(_dict(item))
        if key in by_key:
            unusable = True  # an ambiguous digest list verifies nothing
        by_key[key] = _dict(item)
    kept: list[dict[str, Any]] = []
    kept_digests: list[dict[str, Any]] = []
    withheld: list[tuple[dict[str, Any], str | None]] = []
    for document in documents:
        found = None if unusable else by_key.get(_document_key(document))
        digest = (found or {}).get("content_sha256")
        verified = (
            approved is not None
            and isinstance(digest, str)
            and bool(_SHA256.fullmatch(digest))
            and approved.documents.get(digest)
            == (document.get("media_type"), document.get("size_bytes"))
        )
        if verified and found is not None:
            kept.append(document)
            kept_digests.append(found)
        else:
            withheld.append((document, digest if isinstance(digest, str) else None))
    if not withheld:
        return PocView(snapshot, kept_digests, 0, frozenset())
    keys = frozenset(_document_key(document) for document, _ in withheld)
    values: list[Any] = [document.get("display_name") for document, _ in withheld]
    for document, _ in withheld:
        for field in _list(document.get("fields")):
            data = _dict(field)
            values += [
                data.get(key)
                for key in ("original_extracted_value", "normalized_value", "reviewed_value")
            ]
            values += [_dict(item).get("value") for item in _list(data.get("candidates"))]
    # R4 (R3-2): lineage. Every record naming a withheld document is removed, and what it
    # carried is upload-derived (reviewer corrections and HUMAN_REVIEW observations included).
    # A decision that selected such an observation is upload-derived too, and so is the
    # canonical value it promoted: replaced by the independent registry value, or withheld.
    summary = copy.deepcopy(snapshot.summary)
    withheld_ids = {
        str(item.get("observation_id"))
        for item in _walk(summary)
        if item.get("observation_id") is not None and _names_withheld(item, keys)
    }
    decisions = _upload_decisions(summary, withheld_ids, approved)
    values += [selected for _, selected, _ in decisions]
    summary = _restore_canonical(summary, decisions)
    removed: list[dict[str, Any]] = []
    summary = _without(summary, keys, removed)
    _record_values(removed, values)
    texts = [str(value) for value in values if isinstance(value, (str, int, float, Decimal))]
    view = replace(snapshot, documents=kept, summary=summary)
    return PocView(
        view,
        kept_digests,
        len(withheld),
        frozenset(
            _fold(text)
            for text in texts
            if len(_ALNUM.sub("", text)) >= 2 and not _NUMBER.fullmatch(text.strip())
        ),
        frozenset(
            (key, version, digest)
            for (key, version), (_, digest) in zip(
                [_document_key(document) for document, _ in withheld], withheld, strict=True
            )
        ),
        frozenset(number for text in texts for number in _numbers(text)),
    )


_ALNUM = re.compile(r"[\W_]+")
_ADDRESS_KEYS = frozenset({"address_line_1", "address_line_2", "postal_code", "unit", "street"})


def _lineage_numbers(snapshot: CaseSnapshot, verified: set[str]) -> set[Decimal]:
    """Numbers with an authorised source lineage: the Mock registry records the view keeps
    (entity fields, ownership parties, officers, relationships) and verified documents."""

    case = _dict(snapshot.summary.get("case"))
    found: set[Decimal] = set()
    for source in (case.get("entity"), case.get("registry_acquisition")):
        for item in _walk(source):
            for key, value in item.items():
                # Value fields only: never timestamps, ids, counts or evidence references.
                if (
                    isinstance(value, bool)
                    or value is None
                    or str(key).endswith(("_at", "_id", "_reference"))
                    or key in ("record_count", "version", "operation", "evidence_reference")
                ):
                    continue
                if isinstance(value, (int, float, Decimal)):
                    found.add(Decimal(str(value)).normalize())
                elif isinstance(value, str) and (
                    _NUMBER.fullmatch(value.strip()) or key in _ADDRESS_KEYS
                ):
                    found |= _numbers(value)
    for document in snapshot.documents:
        if str(_dict(document).get("display_name") or "") not in verified:
            continue
        for field in _list(_dict(document).get("fields")):
            for key in ("original_extracted_value", "normalized_value", "canonical_value"):
                value = _dict(field).get(key)
                if isinstance(value, str):
                    found |= _numbers(value)
    return found


def withheld_present(view: PocView, messages: list[dict[str, str]], facts: dict[str, Any]) -> bool:
    """The backstop: whether any value or number read from a withheld document is still in the
    text of these messages, unless an authorised source lineage holds it independently (R4,
    R3-2: the Mock registry records the view keeps, verified documents and the approved
    companies; never a value merely because some fact happens to hold the same text).

    Text values are looked for in every message but the service's fixed wording. Numbers are
    looked for in what a person wrote (the user turn): the structured facts are built from the
    view, where upload-derived values were removed by lineage."""

    if not view.withheld_values and not view.withheld_numbers:
        return False
    try:
        approved = manifest()
    except (OSError, ValueError, KeyError, TypeError):
        return True
    verified = {
        str(_dict(document).get("display_name") or "") for document in view.snapshot.documents
    }
    trusted = _trusted_values(view.snapshot, facts, verified, approved)
    risky = [value for value in view.withheld_values if value not in trusted]
    risky_numbers = view.withheld_numbers - _lineage_numbers(view.snapshot, verified)
    for message in messages:
        content = str(message.get("content", ""))
        if message.get("role") == "system" and is_trusted_text(content):
            continue
        text = _fold(content)
        if any(
            re.search(r"(?<![^\W_])" + re.escape(value) + r"(?![^\W_])", text) for value in risky
        ):
            return True
        if message.get("role") != "system" and risky_numbers & _numbers(content):
            return True
    return False


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


def shared_mode(settings: Any) -> bool:
    # D-104 A1: D-095 mode for any provider. D-095 is named on top of the shared remote
    # interlocks (the D-094, D-091 and D-092 decisions, the model switched on) on a development
    # machine (literal loopback CLM backend, local http browser origins). Nothing here is a
    # provider's own control: each runtime still checks its own readiness, attestations, key,
    # ledger and preflight before every call (remote_test.readiness for GPT-OSS,
    # anthropic_runtime.readiness for Claude), and the eligibility check and its ticket are the
    # same for every provider. Comments, not docstrings: every string constant in this package
    # feeds the synthetic boundary's code vocabulary.
    from .llm import is_local_model_url
    from .model_profiles import LIVE_DECISION_ID, REMOTE_DECISION_ID
    from .remote_test import TEST_DECISION_ID, _local_origin

    return (
        settings.synthetic_dev_decision == DECISION_ID
        and settings.llm_enabled
        and settings.local_api_test_decision == TEST_DECISION_ID
        and settings.remote_inference_decision == REMOTE_DECISION_ID
        and settings.remote_live_decision == LIVE_DECISION_ID
        and is_local_model_url(settings.clm_backend_url)
        and bool(settings.allowed_origins)
        and all(map(_local_origin, settings.allowed_origins))
    )


def mode(settings: Any) -> bool:
    """D-095 is named, on top of a ready D-094 local test mode (remote_test.readiness)."""

    from .remote_test import readiness

    # GPT-OSS, unchanged: readiness holds every shared_mode condition and OpenRouter's own.
    return shared_mode(settings) and readiness(settings) is None
