# ADR-007 — Recoverable onboarding and final target confirmation

## Status

Proposed implementation candidate; independent quality gate pending

## Date

2026-09-29

## Context

The accepted flow retained truthful GoldTier Search and target-ledger evidence, but an
operator could not safely correct the initial identity on the same case, recheck Search,
repair bounded policy drift, replace incomplete ownership with reviewed local evidence,
or inspect and confirm the exact final target payload before the first business
mutation. Ambiguous Search also stopped independent evidence acquisition even though it
did not invalidate ACRA or supplied-document facts. The owner explicitly authorized a
bounded POC recovery and confirmation package without authorizing Live integration,
provider writes during development, a new policy owner, or autonomous approval.

## Decision

Schema v7 extends the one case envelope and existing orchestration owners. Exact
schema-v1 through schema-v6 records remain readable without persistence rewrite.
This decision supersedes only D-060's ambiguous-Search stop-before-ACRA and no-late-
recheck limitations; its distinction between failure and no-match and its target-write
prohibition remain in force.

An authorized operator may correct bounded initial legal name and UEN on the retained
case and request a fresh read-only GoldTier Search. Every attempt receives a fresh
request identity and durable REQUESTED/COMPLETED evidence. A changed identity
invalidates dependent Search, registry, canonical, confirmation, and automation facts;
an unchanged identity preserves them. Exact-target reuse still requires prior durable
same-ID verified evidence. Ambiguous, malformed, timed-out, and failed Search retain
their true disposition while independent eligible ACRA, document, reconciliation, and
ownership evidence may continue. Target identity stays unresolved and every target
mutation remains blocked.

The current GoldTier Search response does not provide sufficient registration-number
and jurisdiction evidence for a new operator-attested exact binding. Name-only
candidates therefore remain review-required under the existing identity-review owner,
with explicit missing evidence and the same-case recheck resume route. User-entered
identity correction is labelled `USER_SUPPLIED_CORRECTION_POC`, not provider-verified
or target-identity verification. A future authoritative contract may supply the exact
evidence required by the existing resolver, but this decision does not invent it.

The existing case policy owner may rebind only the fixed D-056 Singapore target fields
to the current accepted values. Rebinding preserves operator-selected KYC type and
client segment, thresholds, intelligence, and unrelated optional fields. It retains a
bounded history of the prior snapshot and invalidates any earlier target confirmation.
KYC type and client segment remain editable only before final confirmation and target
dispatch.

A reviewed local declaration may replace only an incomplete, review-required ownership
result before confirmation. It is labelled
`USER_SUPPLIED_DECLARATION / LOCAL / MANUAL_DECLARATION_POC`, binds the current case,
UEN, reviewed document/version, as-of date, rationale, parties, and exact Decimal
percentages, and uses the one ownership engine's structural and 100-percent checks. It
never becomes ACRA evidence or legal/final UBO authority. The superseded terminal
analysis remains retained and independent blockers remain open.

Every new blocker receives immutable, evidence/version-bound decision metadata from one
versioned policy: classification, owner, minimum inputs, permitted actions, resume
conditions, invalidations, explanation, dependencies, and unknowns. This metadata is
explanatory only. It cannot resolve, cancel, resume, authorize, or advance workflow;
unknown or mismatched blockers fail closed as `HARD_STOP`.
Proved normalized document-value equivalence receives an
`AUTO_RESOLVED_WITH_NOTE` record only after the document owner has already established
equivalence; existing readiness-authorized optional limitations retain
`CONTINUE_WITH_WARNING`. Neither classification is a general override.

Before Shell, Policy, or Amend, the operator reviews the current server-authored target
projection and explicitly confirms it with expected automation, CLM, and event
versions. The durable confirmation retains actor, time, event count, CLM version,
destination, warnings, review digest, and provider classification. Any relevant change
invalidates it. Confirmation first performs one forced read-only Search recheck. If the
target path changes, the refreshed summary remains unconfirmed and no mutation occurs;
an unchanged result binds the new CLM version. The exact mapper preview and immutable
dispatch snapshot use the case-acceptance timestamp as their shared source-context
`acceptedAt`; every transmitted preview field, including that timestamp, is covered by
the review digest. Every target-write path, including direct
submission, reauthorizes and revalidates the current confirmation inside the owning
lock. The existing target ledger
continues to own ordering, intent, outcomes, no-replay recovery, and provider calls.

The review also presents legal form and owning team and exposes section actions for
identity, classification, and documents. It exposes ownership editing only when the
server's typed recovery projection authorizes `MANUAL_OWNERSHIP_EVIDENCE`; otherwise it
states that the ownership source is review-only. Authorized actions navigate to the
existing backend-validated correction/evidence owners; they do not create a frontend
mutation owner. Identity correction remains available only while the case is
unconfirmed and no submission snapshot exists. It cancels stale confirmation state,
runs a fresh read-only Search, and invalidates dependent evidence before the case can
become eligible again. Confirmed projections expose no edit controls.

HR may use a separate read-only ACRA diagnostic API under its existing
`PROVIDER_SANDBOX_TEST` capability. It uses the exact composed connector, fixed safe
hosts, bounded lookup, explicit unsupported-operation results, and safe presence-only
configuration/status. It has no case access, case mutation, provider write, or runtime
composition authority.

## Alternatives considered

- Create a replacement case after correction: rejected because it loses same-case
  chronology and encourages duplicate state.
- Treat ambiguous/failed Search as no-match: rejected because it invents target absence.
- Add a second recovery or target ledger: rejected because it would split replay and
  ordering authority.
- Accept arbitrary policy editing or free-form ownership overrides: rejected because it
  invents sponsor rules and bypasses the existing typed owners.
- Rely on a frontend confirmation checkbox: rejected because every write path must be
  enforced by backend state under lock/CAS.

## Consequences

- New writes use schema v7; strict schema-v1 through schema-v6 compatibility remains.
- A retained case can recover through bounded identity, policy, ownership, and
  pre-confirm classification actions without rewriting source evidence.
- Final confirmation is a technical dispatch gate, not customer approval,
  Ready-for-Approval, or sponsor authorization.
- ACRA remains Mock/Partial and GoldTier remains Mock or `SANDBOX_PARTIAL`; no Live or
  production-interoperability claim follows.
- Provider writes remain disabled unless separately authorized and configured. Related
  parties, hierarchy creation, autonomous approval, and a full Exception Workbench stay
  out of scope.
- Locking and CAS guarantees remain process-local except for the tested Mongo revision
  boundary; distributed exactly-once execution is not claimed.
