# Provider-verified Policy recovery

Owner-authorized remediation candidate, 2026-10-06, based on main
`529efea3966fb561027973e6d932cecb0e8f6bb8`. Independent gate evidence is recorded
separately; this document does not authorize real case mutation or provider calls.

## Evidence and accepted shapes

Read-only Delta portal evidence established an exact customer/UEN and Singapore
Requested Policy created within the original unresolved attempt window. It does
not establish the original HTTP response, timeout cause, approval or completed KYC.
Implementation/testing uses synthetic memory fixtures and generated disposable Mongo
only; the real UAT database is outside this task's access boundary.

The existing Policy recovery owner accepts only IN_PROGRESS with exactly attempted
SEARCH/SHELL/POLICY, resolved SEARCH/SHELL, no terminal outcome/receipt, and either:

- definitive SEARCH/SHELL with original SHELL_CREATED and no Shell-recovery fact; or
- definitive SEARCH and separately provider-recovered Shell, preserving that evidence.

The current canonical identity, frozen target input/policy/catalogue, case GoldTier ID,
ledger ID and provider evidence must match. Only Requested is accepted. Conflicting
evidence, unattempted/resolved Policy without the matching prior recovery, later
attempts and terminal outcomes are rejected. Identical recorded evidence is locally
idempotent and can repair an interrupted case/automation checkpoint without calls.

## Operator/API boundary

There is no provider-verification browser form. An actor with existing TARGET_RECOVERY
and case access may use the existing
`POST /api/clm/zero-touch/cases/{case_id}/target-recovery` API with operation POLICY,
verified recovered_party_id, legal_name, registration_number, country_of_incorporation,
provider_policy, provider_policy_status=Requested and origin=UNCERTAIN_DURABLE_LEDGER.
Evidence must come from an independently authorized provider inspection. Customer
Search alone never proves Policy creation. HR has no case-access exception.
The same existing API remains available to manual CLM submissions without an
automation record. It records case/ledger evidence and creates no automation; their
existing CLM submit action owns explicit continuation.

This records operation=POLICY, authority=PROVIDER_VERIFIED_RECOVERY,
original_outcome_uncertain=true and replayed=false. Policy status becomes
PROVIDER_VERIFIED_REQUESTED; Policy ID stays unknown. Normal Shell status and all
original chronology stay intact. No target HTTP call occurs during Policy recovery.

The existing orchestrator reconciles only CLM_TARGET_OUTCOME_UNCERTAIN at the target
stage. It preserves the technical-failure event, clears only that current failure and
retains RECOVERY_PENDING through legal local transitions. It does not automatically
run the target. A separately authorized explicit resume continues the same immutable
submission and existing final confirmation: Amend once if the frozen plan requires
it, otherwise no Amend, then exact-ID readback. Never repeat Final Review & Send,
Shell or Policy. Unrelated technical failures cannot be cleared by Policy evidence.

## Sanitized diagnostics and compatibility

Future incremental mutation uncertainty records a controlled existing event code:
GT_TARGET_OUTCOME_UNCERTAIN followed by TIMEOUT, TRANSPORT, RESPONSE_DECODE,
RESPONSE_TOO_LARGE, UNEXPECTED_STATUS or UNKNOWN. Repeated blocked advancement does
not replace the original reason. No exception text, request/response body, headers,
credentials or provider-private detail is retained. Reasons are observational only:
the ledger still prevents replay. Historical attempts remain unknown; no Delta cause
is retrospectively inferred. The ten-second configured default is unchanged.

No public recovery request/response field, envelope schema/version, mapping, permission,
provider classification, production authority or Live claim changes. Fake/physical
evidence covers both prefixes, identity/authorization negatives, same intent and
confirmation, no replay, continuation, local fault retry and restart/read-without-rewrite.
