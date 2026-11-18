"""D-139 (proposed): two separate eligibility decisions on the hosted assistant.

D-132 (RD-1) served only an owner-approved list of case references created before a cutoff, and
refused every other case with 403, model-free guidance included. That list was a temporary
qualification restriction. D-139 replaces it with two decisions:

    guidance             model-free, deterministic answers from the case data: every case the
                         backend lets this user read. The backend's RBAC, team scope, 401 and
                         safe 404 decide; the assistant adds no case list
    external inference   whether this answer's case content may go to an external model
                         provider. Decided per answer, for the provider about to be called, by
                         the provider's data-handling policy. For both hosted providers (Claude
                         through Anthropic under D-129, GPT-OSS through OpenRouter under its
                         amendment) the policy is verified synthetic data, by provenance: the
                         reviewed D-095 check (synthetic_eligibility.check). It needs an approved
                         synthetic company from ACRA in MOCK mode, every document a tracked
                         synthetic fixture by the backend's own digest, typed values grounded in
                         those sources, a seeded viewer, approved knowledge and a screened
                         question. A Mock ACRA or Marketplace Mock case qualifies once its data
                         is eligible. Anything else gets the case-data answer with a notice; no
                         call is made and nothing is reserved

This module holds the hosted policy object (installed by harden as ``app.state.case_gate``, the
name main.py's hosted checks already use) and its refusal counts. The check itself runs in
main.py's remote_gate and Try with this change, on the exact messages, before any call.

The D-132 settings (ASSISTANT_HOSTING_ELIGIBLE_CASE_REFS and ..._CREATED_BEFORE) are retired: a
service that still has either refuses to start (CASE_ALLOWLIST_RETIRED), so nobody believes a
list still applies. The reason a case is not sent is logged with the case reference and a closed
code only, never a name or value.
"""

import hashlib
import logging
import threading
from collections import Counter
from collections.abc import Mapping
from uuid import UUID

from ai_assistant import config as assistant_config
from ai_assistant.privacy_boundary import DATA_POLICIES, PSEUDONYMISED, SYNTHETIC_ONLY

RETIRED_VARIABLES = (
    "ASSISTANT_HOSTING_ELIGIBLE_CASE_REFS",
    "ASSISTANT_HOSTING_ELIGIBLE_CREATED_BEFORE",
)
RETIRED = "CASE_ALLOWLIST_RETIRED"
# D-142 Q3: each hosted provider's data-handling policy (privacy_boundary.DATA_POLICIES).
# Unset is synthetic_only, the D-139 R3 check. pseudonymised starts only once the owner's D-142
# adoption is recorded in config.HOSTED_PRIVACY_DECISION.
DATA_POLICY_VARIABLES = {
    "anthropic": "ASSISTANT_HOSTING_ANTHROPIC_DATA_POLICY",
    "openrouter": "ASSISTANT_HOSTING_OPENROUTER_DATA_POLICY",
}
DATA_POLICY_INVALID = "DATA_POLICY_INVALID"
PRIVACY_DECISION_REQUIRED = "PRIVACY_DECISION_REQUIRED"
# The fifth path (dashboard insights) reads many cases at once and has no per-answer check, so
# it admits no case until its own eligibility design is reviewed (HOSTED_INSIGHTS_DECISION is
# None and the guard refuses the route as well).
INSIGHTS_REFUSAL = "INSIGHTS_NOT_ELIGIBLE"

log = logging.getLogger("assistant_hosting.eligibility")


def case_ref(case_id: UUID) -> str:
    return hashlib.sha256(str(case_id).encode("ascii")).hexdigest()[:12]


class CasePolicy:
    """The hosted service's external-inference policy marker and its refusal counts.

    ``record`` is called by main.py when a case's content is not sent; calling the object (the
    D-132 gate's shape, kept for the insights path) admits no case."""

    refs: frozenset[str] = frozenset()

    def __init__(self, policies: Mapping[str, str] | None = None) -> None:
        self._lock = threading.Lock()
        self._refusals: Counter[tuple[str, str]] = Counter()
        self._policies = dict(policies or {})

    @classmethod
    def from_env(cls, environ: Mapping[str, str]) -> "CasePolicy":
        if any((environ.get(name) or "").strip() for name in RETIRED_VARIABLES):
            raise ValueError(RETIRED)
        return cls(_policies(environ))

    def data_policy(self, provider: str) -> str:
        """This provider's data-handling policy (synthetic_only unless set)."""

        return self._policies.get(provider, SYNTHETIC_ONLY)

    def record(self, case_id: UUID, reason: str) -> None:
        ref = case_ref(case_id)
        with self._lock:
            self._refusals[(ref, reason)] += 1
        log.info("external inference not used: ref=%s reason=%s", ref, reason)

    def refusals(self) -> dict[str, int]:
        """Cases not sent so far, by reason code (no case or user is named)."""

        with self._lock:
            counts: Counter[str] = Counter()
            for (_, reason), count in self._refusals.items():
                counts[reason] += count
            return dict(counts)

    def __call__(self, case_id: UUID, summary: object) -> str | None:
        return INSIGHTS_REFUSAL


def _policies(environ: Mapping[str, str]) -> dict[str, str]:
    found: dict[str, str] = {}
    for provider, name in DATA_POLICY_VARIABLES.items():
        value = (environ.get(name) or "").strip()
        if not value:
            continue
        if value not in DATA_POLICIES:
            raise ValueError(DATA_POLICY_INVALID)
        if value == PSEUDONYMISED and assistant_config.HOSTED_PRIVACY_DECISION is None:
            raise ValueError(PRIVACY_DECISION_REQUIRED)
        found[provider] = value
    return found


def config_codes(environ: Mapping[str, str]) -> list[str]:
    """The startup refusal for retired D-132 settings or an unusable D-142 data policy, if any
    (for profile.refusals)."""

    try:
        CasePolicy.from_env(environ)
    except ValueError as error:
        return [str(error)]
    return []
