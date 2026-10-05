# ADR-007 — Recoverable onboarding and final target confirmation

## Status

The 2026-10-05 post-closeout amendment below adds bounded creator confirmation and
independent review in the existing owners; its unmerged content requires a fresh gate.

Original recovery/confirmation package accepted on main through PR #65 and included
in inspected PR #68. The 2026-10-04 Session 1 extension below is an implementation
candidate pending its own independent quality gate.

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

- The original package used schema v7 with strict schema-v1 through schema-v6 compatibility.
  Current writes use schema v8 under D-064; historical facts remain readable without rewrite.
- A retained case can recover through bounded identity, policy, ownership, and
  pre-confirm classification actions without rewriting source evidence.
- Under D-062, Review & Send is final local human approval for the reviewed submission
  and a retained technical dispatch gate. It is not regulatory approval,
  GoldTier-internal approval, Ready-for-Approval, or external-write authorization.
- ACRA remains Mock/Partial and GoldTier remains Mock or `SANDBOX_PARTIAL`; no Live or
  production-interoperability claim follows.
- Provider writes remain disabled unless separately authorized and configured. Related
  parties, hierarchy creation, autonomous approval, and a full Exception Workbench stay
  out of scope.
- Locking and CAS guarantees remain process-local except for the tested Mongo revision
  boundary; distributed exactly-once execution is not claimed.

## Amendment - 2026-10-01 Garden operator recovery

The owner-authorized Garden stabilization task separates canonical registry identity
validation from ownership completeness within the existing owners. A strictly validated
partial acquisition retains its actual empty/unsupported ownership evidence. Canonical
identity requirements still apply; technical acquisition failure still stops. Actual
incomplete graph evidence reaches the one Decimal engine and requires structured
document-bound manual review before readiness. No shareholder, percentage or relationship
is inferred. Unsupported official-Mock Relationships has no call or result provenance.
Historical stored empty results remain readable without a read-time rewrite.

An operator who resolves reconciliation before finishing document review can still
review pending current fields during pre-confirmation incomplete ownership. Existing
current-evidence authorization, lock/version and confirmation/submission guards apply;
document review re-evaluates reconciliation and returns to the retained ownership blocker.
This is bounded POC recovery, not new source precedence or sponsor reviewer policy.

The complete primary demo uses Mock GoldTier. Name-only Sandbox candidates remain
ambiguous under this decision. Offline browser acceptance exercises the official-Mock
protocol adapter with explicitly synthetic input and a distinct test-only execution
label; it does not establish a new official network observation or production mode.

## Amendment - 2026-10-01 zero-touch exception remediation

The owner explicitly authorizes automatic finalization of current pending document
fields when their extracted and current canonical values match, confidence meets the
case-bound inclusive threshold, and no contradictory current evidence or prior operator
decision exists. Machine events remain distinct from operator review events. Cached
reconciliation is not a reason to omit this bounded progression.

A current, exact document/event-version-bound resolved reconciliation is also a
completed document checkpoint. Manual ownership validation may consume that checkpoint
through the existing reconciliation reader. It rechecks current case identity, current
document/version, cleared fingerprint and UTC completion time during provider load.
Original extraction and field review records remain unchanged; the browser receives
explicit semantic completion rather than a fabricated persisted REVIEWED state. This
supersedes the earlier requirement for duplicate field Accept clicks after reconciliation.

Blocker class, direct evidence actions, dependencies and resolution conditions are
derived browser metadata. Historical resolved/superseded exceptions are separate from
active interventions. Existing schema v7, repositories, atomic reconciliation decisions,
Decimal engine, target ledger and uncertain-operation no-replay rules remain unchanged.
The explicit final dispatch confirmation is measured separately from exception
interventions. No sponsor policy, external lifecycle or Live authority is added.

## Amendment - 2026-10-04 post-merge Session 1 candidate

The explicit owner program builds from merged PR #68 at
`1d426e0ceddc32d80b0aaec293c62fb761f2fecf`. Its Session 1 extension is pending a fresh
independent gate; the original PR #65/68 acceptance does not certify the new content.

Same-case identity correction retains structured document extraction and provenance.
The existing document owner recomputes canonical comparisons from the original retained
observations, preserving human decisions and recording changed comparisons. Existing
reconciliation and zero-touch owners then recompute dependent state and auto-resume to
the next authoritative blocker. The comparison refresh requires no retained file bytes,
extraction replay or provider call. It creates no replacement document or recovery owner
and permits no target mutation replay.

D-062's workflow clarification and the current owner instruction make Review & Send
the final human approval in this application. The visible pipeline ends at Final review
& send; there is no second local unresolved human approval stage. Subsequent target
status and GoldTier-internal approvals remain separate retained facts and authority.
Regulatory approval, legal UBO certification, OCR and current-program external Sandbox
delivery are not established by this Session 1 amendment.

## Amendment — 2026-10-05 existing-customer remediation

The current explicit owner/sponsor clarification permits a creator decision bound to
one retained incomplete XPI candidate, independent matching canonical identity, Search
UUID/current versions and a retained actor/time/rationale receipt. It is labelled
CONFIRMED_EXISTING, not provider EXACT_MATCH. No caller target-ID entry, provider call,
target mutation or duplicate Shell/Policy occurs during confirmation. Existing CLM
owns the receipt and the same zero-touch owner repairs an interrupted stage projection.
Provider-supported singleton UEN/country equality can produce Sandbox EXACT_MATCH
without the former prior-local-case prerequisite; accepted Mock finalized-proof reuse
remains unchanged. Current registry acquisition remains mandatory.

Document/reconciliation review is independent of unresolved Search. It retains the
earliest Search blocker and target write prohibition until identity resolution.
Final Review & Send and the target ledger still own dispatch/order/no-replay.
Schema9 retains additive candidate identity fields and the optional receipt/new explicit
disposition; absent historical fields mean unknown, never inferred confirmation.
No migration, read rewrite, repository owner or provider family is introduced.
The [family reconciliation](../integration/GOLDTIER_EXISTING_CUSTOMER_RESOLUTION.md)
keeps XPI aliases separate from supplied EDS registration/external-key Search. EDS
replacement requires a separately assigned provider/architecture delta.
