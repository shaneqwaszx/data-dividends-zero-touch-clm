"""RD-1 (R2.1): the cases the hosted assistant may serve.

A bounded proof-of-concept rule, not a general source-provenance check. The case summary the
backend serves to a browser cannot tell a Mock ACRA case from an ACRA Marketplace Mock case:
both say ACRA in MOCK, and the data-set name that differs is left out of the browser view. So
the hosted assistant serves only an exact owner-approved list of existing synthetic cases,
created before a fixed time, and refuses every other case. All must hold:

    backend    the backend already let this user read the case (its 401 and 404 are unchanged;
               this check runs only on a summary it returned)
    identity   the summary's own case id is the requested one, and the first 12 hex characters
               of the SHA-256 of that id are on the approved list
    created    the summary's creation time is timezone-aware and strictly before the cutoff
    source     the registry source is ACRA in MOCK
    marker     the summary holds no Marketplace token. The absence of a token is not taken as
               proof of anything; the list and the cutoff are what admit a case

The registry evidence binding and its freshness policy are not used: either lane can produce
them, and a Mock ACRA case can have no binding at all.

Anything missing, malformed or unexpected refuses. The reason is logged with the case reference
only, never a name or value, and is never shown to the user.
"""

import hashlib
import json
import logging
import re
import threading
from collections import Counter
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

REFS_VARIABLE = "ASSISTANT_HOSTING_ELIGIBLE_CASE_REFS"
CUTOFF_VARIABLE = "ASSISTANT_HOSTING_ELIGIBLE_CREATED_BEFORE"
REQUIRED = "CASE_ELIGIBILITY_REQUIRED"
INVALID = "CASE_ELIGIBILITY_INVALID"
# Exact tokens only: the ACRA Marketplace Mock data set and connector mode names.
MARKETPLACE_TOKENS = ("ACRA_API_MARKETPLACE_MOCK", "api_marketplace_mock")
_REF = re.compile(r"[0-9a-f]{12}")

log = logging.getLogger("assistant_hosting.eligibility")


class EligibilityConfigError(ValueError):
    """The hosted eligibility settings are missing or malformed (a closed code, no value)."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def case_ref(case_id: UUID) -> str:
    return hashlib.sha256(str(case_id).encode("ascii")).hexdigest()[:12]


def _aware(value: object) -> datetime | None:
    """A timezone-aware time from an ISO 8601 string, or None."""

    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def _dict(value: object) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


class CaseGate:
    """Callable on (requested case id, backend summary): None admits, a reason code refuses."""

    def __init__(self, refs: frozenset[str], created_before: datetime) -> None:
        if not refs or not all(_REF.fullmatch(ref) for ref in refs):
            raise EligibilityConfigError(INVALID)
        if created_before.tzinfo is None:
            raise EligibilityConfigError(INVALID)
        self.refs = refs
        self.created_before = created_before
        self._lock = threading.Lock()
        self._refusals: Counter[tuple[str, str]] = Counter()

    @classmethod
    def from_env(cls, environ: Mapping[str, str]) -> "CaseGate":
        raw_refs = (environ.get(REFS_VARIABLE) or "").strip()
        raw_cutoff = (environ.get(CUTOFF_VARIABLE) or "").strip()
        if not raw_refs or not raw_cutoff:
            raise EligibilityConfigError(REQUIRED)
        items = [item.strip() for item in raw_refs.split(",")]
        if any(not _REF.fullmatch(item) for item in items) or len(set(items)) != len(items):
            raise EligibilityConfigError(INVALID)
        cutoff = _aware(raw_cutoff)
        # The cutoff is written in UTC, so an operator cannot misread it.
        if cutoff is None or cutoff.utcoffset() != timedelta(0):
            raise EligibilityConfigError(INVALID)
        return cls(frozenset(items), cutoff)

    def refusals(self) -> dict[str, int]:
        """Refusals so far, by reason code (the audit count; no case or user is named)."""

        with self._lock:
            counts: Counter[str] = Counter()
            for (_, reason), count in self._refusals.items():
                counts[reason] += count
            return dict(counts)

    def __call__(self, case_id: UUID, summary: object) -> str | None:
        try:
            reason = self._reason(case_id, summary)
        except Exception:  # anything unexpected is uncertain, so it refuses
            reason = "SUMMARY_MALFORMED"
        if reason is not None:
            ref = case_ref(case_id)
            with self._lock:
                self._refusals[(ref, reason)] += 1
            log.warning("assistant case refused: ref=%s reason=%s", ref, reason)
        return reason

    def _reason(self, case_id: UUID, summary: object) -> str | None:
        top = _dict(summary)
        case = _dict(top.get("case")) if top is not None else None
        if case is None:
            return "SUMMARY_MALFORMED"
        try:
            server_id = UUID(str(case.get("case_id")))
        except ValueError:
            return "CASE_ID_MISMATCH"
        if server_id != case_id:
            return "CASE_ID_MISMATCH"
        if case_ref(server_id) not in self.refs:
            return "CASE_NOT_LISTED"
        created = _aware(case.get("created_at"))
        if created is None:
            return "CREATED_AT_UNCERTAIN"
        if not created < self.created_before:
            return "CREATED_AFTER_CUTOFF"
        entity = _dict(case.get("entity"))
        source = _dict(entity.get("source")) if entity is not None else None
        if (
            source is None
            or source.get("source_system") != "ACRA"
            or source.get("environment") != "MOCK"
        ):
            return "SOURCE_NOT_MOCK_ACRA"
        text = json.dumps(summary, ensure_ascii=False)
        if any(token in text for token in MARKETPLACE_TOKENS):
            return "MARKETPLACE_MARKER"
        return None


def config_codes(environ: Mapping[str, str]) -> list[str]:
    """The startup refusal for the eligibility settings, if any (for profile.refusals)."""

    try:
        CaseGate.from_env(environ)
    except EligibilityConfigError as exc:
        return [exc.code]
    return []
