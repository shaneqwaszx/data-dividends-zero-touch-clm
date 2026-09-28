# ADR-006 — GoldTier-first bootstrap and provider-verified recovery

## Status

Proposed

## Date

2026-09-28

## Context

The Garden sandbox Shell was attempted exactly once and its network outcome was
uncertain. The historical acceptance process used the process-local target repository,
so only sanitized chronology survived process exit. Later authenticated provider
evidence proved that GoldTier ID `143878` is the exact Garden record, but that evidence
did not turn the Shell response into a success response. The owner also clarified that
customer Search precedes ACRA bootstrap: exact existing customers skip ACRA/Shell,
no-match customers alone acquire ACRA, and ambiguous results stop.

## Decision

Schema v6 extends the existing case envelope and target ledger; it does not add a
recovery repository or alternate acceptance ledger. The ledger separately retains:

- definitive operation completion;
- lifecycle resolution;
- the original uncertain Shell attempt; and
- a `PROVIDER_VERIFIED_RECOVERY` fact with exact target ID, legal name, registration
  number, country, actor, timestamp, recovery origin, and `replayed=false`; and
- an optional `PROVIDER_VERIFIED_FAILURE` fact for an attempted, non-complete Amend
  whose original transport outcome was uncertain and whose later sanitized provider
  audit proves validation failure without replay.

Recovery is Sandbox-only, RBAC-protected at the API boundary, reauthorized inside the
case lock, exact-identity validated, idempotent, and incapable of calling Shell. It may
resolve either a retained uncertain Shell or the explicitly labelled
`HISTORICAL_LOCAL_LEDGER_LOST` Garden continuation. The recovered case projection says
the Shell outcome remained uncertain and the ID was later provider-verified. Mongo is
required for real external mutation acceptance; intent is persisted before each write
and uncertain/definitive result after it.

New case bootstrap retains bounded initial legal name, registration number and country,
validates Singapore eligibility, and performs GoldTier Search before ACRA. An exact
candidate is reusable only when it binds to a prior durable case whose canonical
identity and post-Amend same-ID read-back agree. Exact match hydrates that verified state
and skips ACRA, Shell, and new-policy creation. No-match proceeds to ACRA and may later
create Shell then Policy. Ambiguous/failed Search stops before ACRA and all target
mutation. Documents remain independent evidence and an authorized reconciliation
decision may amend the same retained ID before a same-ID read-back.

The same ledger mechanism may also resolve the one retained uncertain Garden Policy
attempt when read-only authenticated provider evidence proves exactly one Singapore
Policy request on GoldTier ID `143878`, with provider status `Requested`. That recovery
retains operation `POLICY`, the original uncertain transport outcome, provider policy
and status, `PROVIDER_VERIFIED_RECOVERY`, and `replayed=false`. `Requested` proves only
that the provider-side Policy request exists; it is not approval, completion, or active
policy status. This is an operator-attested, Garden-only recovery authority, not a
general automatic Policy read-back rule.

The same canonical ledger may reconcile the one retained Garden Amend as failed when
the authenticated provider audit proves `Created` followed by the provider-spelled
`Valdiation Failed`. The retained internal status is `PROVIDER_VALIDATION_FAILED`;
the provider spelling is evidence only. Amend is not added to definitive-completion or
lifecycle-resolution markers, no read-back becomes eligible, and the original uncertain
transport chronology remains unchanged.

The Garden KYC and segment values remain per-case `USER_AUTHORIZED_POC` inputs. The full
approved 17/23 vocabularies remain available; neither value becomes a global or ACRA-
derived default.

## Alternatives considered

- Recreate the historical row or say Shell returned `143878`: rejected as false history.
- Replay Shell: rejected by the durable no-replay boundary.
- Use an acceptance-only ledger: rejected because the application ledger already owns
  intent, outcomes, restart recovery, and replay decisions.
- Treat one name candidate as exact: rejected because exact case identity and prior
  same-ID read-back are required.
- Call ACRA merely to learn the legal name before Search: rejected because it violates
  the clarified bootstrap order.

## Consequences

- Schema v1-v5 remain readable; new writes use schema v6.
- Pipeline topology can truthfully show Initial Identity and GoldTier Search before ACRA,
  an explicit existing-target state, and skipped ACRA/Shell/new-policy nodes.
- Provider classifications remain Mock by default and `SANDBOX_PARTIAL` when explicitly
  configured. Nothing becomes Live or production-approved.
- Any other uncertain Policy and every uncertain Amend still stops without automatic
  replay. Garden Policy recovery and Amend-failure reconciliation are permitted only
  from their retained uncertain ledger and the bounded provider evidence above; neither
  fabricates a general API read-back, retry, or failure-reason contract.

## Security and verification

Reject wrong UEN/ID/case/Policy/status, name-only, multiple-candidate, definitively
failed, and conflicting-ID recovery. Retain no raw provider body, secret, header, portal
session, document body, or private customer data. Verify unit/adverse paths, real-Mongo
restart persistence, no Shell/Policy replay, GoldTier-first branch call counts, frontend
topology, full regression/security checks, and an independent Quality Gate before
acceptance.

## Related authority

- D-048/D-049 and ADR-004 remain the provider-security baseline.
- This decision supersedes the Registry-first ordering in D-051/ADR-005 and the
  statement in D-049 that schema v6 would not be introduced.
- D-056/D-057 remain the Singapore mapping and vocabulary owners.
- Phase 22, production policy, related parties, hierarchy and final approval remain out
  of scope.
