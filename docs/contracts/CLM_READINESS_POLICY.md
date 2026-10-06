# Phase 05 CLM Readiness Policy

## Status and claim boundary

This policy governs credential-free Phase 05 Mock submission only. It is not a legal,
compliance, customer-approval, production GoldTier, or four-eye policy. The integrated
sequence is a **PROJECT-DEFINED / PROVISIONAL** POC decision pending Q-003, Q-004,
Q-005, Q-006, Q-007, Q-013, and Q-014 where noted.

`READY_FOR_MOCK_SUBMISSION` means only that the deterministic local Phase 05
prerequisites are satisfied. `MOCK_GOLDTIER_SUBMITTED` means only that the accepted
Mock base operations completed. Neither status is Ready-for-Approval.

## Evidence classification

| Policy area | Rule | Classification |
|---|---|---|
| Registry scope | ACRA is the POC corporate registry and canonical business source. | **SPONSOR-CONFIRMED** (D-001/D-002) |
| Registry prerequisite | A staged case must have a current canonical entity that passes the shared source-neutral canonical minimum validator on every evaluation and immediately before snapshot creation; historical `VALIDATED` state alone is insufficient. | **PROJECT-CONFIRMED TECHNICAL CONTROL** applying the accepted Phase 01/02 provisional minimums |
| Document prerequisite | At least one document is `REVIEWED`; none may be `PROCESSING`, `REVIEW_REQUIRED`, or `FAILED`. | **PROJECT-DEFINED / PROVISIONAL**, pending Q-003/Q-005/Q-014 |
| Document agreement | Every human-reviewed retained value must deterministically agree with the current canonical registry value for automatic Mock submission. Original extraction, provider provenance, and human decisions remain retained evidence. Under D-066/ADR-007, accepted identity correction refreshes current canonical comparison values and comparison statuses from retained observations, without provider replay or document replacement. | **PROJECT-DEFINED / PROVISIONAL** conservative rule; owner-authorized comparison refresh |
| Source conflict | A rejected value, accepted mismatch, or correction that does not agree with canonical ACRA data yields `SOURCE_CONFLICT_REQUIRES_POLICY`; canonical data is not overwritten. | **PROJECT-DEFINED / PROVISIONAL** containment pending Q-005/Q-014 |
| Ownership prerequisite | The latest case-linked Phase 04 analysis must be `ANALYZED`. `REVIEW_REQUIRED`, `FAILED`, unloaded, loading, loaded-only, or analyzing results block. | **PROJECT-DEFINED / PROVISIONAL** sequencing |
| Ownership calculation | Decimal path calculation and the configured Phase 04 threshold are used as supporting provisional evidence only. | Technical calculation is project-confirmed; D-062 confirms the bounded inclusive >=25% default. Complete legal/control and production UBO policy remain **UNRESOLVED** under Q-004 |
| Mock GoldTier sequence | Search, shell only on `NO_MATCH`, policy, and amend reuse the accepted Mock behavior. | Mock contract implementation under confirmed/provisional baseline |
| Related-party write | No related-party payload or write is executed. | **UNRESOLVED** under Q-006/Q-007; `PENDING_SPONSOR_CONFIRMATION` |
| External integration and approval | Production/Live GoldTier/PingFed, external hierarchy, and provider-internal approval remain unverified. Review & Send is the application's final human approval under D-066/ADR-007; bounded XPI Sandbox evidence is classified separately. | External production/hierarchy dependencies remain **UNRESOLVED** under Q-001/Q-002/Q-008; local final approval is owner-authorized |

Current amendment: the Phase05 base-sequence/history descriptions below are historical.
Current submission additionally requires exact Review & Send confirmation and ledger-owned
same-ID readback. D2 Mock requires Amend; D-063 permits conditional AMEND_NOT_REQUIRED only
for the separately labelled XPI Sandbox lane. Mongo durability does not establish distributed
idempotency or approval.

## Lifecycle

| Status | Meaning |
|---|---|
| `COLLECTING_EVIDENCE` | Required local evidence is missing or still in a nonterminal collection/analysis state. |
| `REVIEW_REQUIRED` | Registry, document, ownership, source-conflict, or Mock target outcome needs a human/policy decision. |
| `READY_FOR_MOCK_SUBMISSION` | Current authoritative local evidence satisfies this policy. |
| `SUBMITTING` | One serialized Mock base submission owns the case transition. |
| `MOCK_GOLDTIER_SUBMITTED` | The accepted Mock search/shell/policy/amend base path completed. |
| `FAILED` | Registry intake or Mock submission reached a safe terminal failure. |

## Typed Mock-submission blockers

| Code | Meaning |
|---|---|
| `REGISTRY_NOT_READY` | Canonical registry evidence requires review or is incomplete. |
| `REGISTRY_FAILED` | Registry intake failed. |
| `CANONICAL_DATA_INVALID` | The current canonical entity no longer satisfies the shared minimum validation rules. |
| `DOCUMENT_REQUIRED` | No case-linked document exists. |
| `DOCUMENT_PROCESSING` | A case-linked document is still processing. |
| `DOCUMENT_REVIEW_INCOMPLETE` | No reviewed document exists or a review remains unresolved. |
| `DOCUMENT_PROCESSING_FAILED` | A document processing record failed. |
| `SOURCE_CONFLICT_REQUIRES_POLICY` | Reviewed document evidence conflicts with canonical ACRA data. |
| `OWNERSHIP_REQUIRED` | No case-linked ownership record exists. |
| `OWNERSHIP_ANALYSIS_INCOMPLETE` | Ownership has not reached a supported terminal analyzed state. |
| `OWNERSHIP_REVIEW_REQUIRED` | Cycle, incomplete chain, graph limit, or another issue makes ownership indeterminate. |
| `OWNERSHIP_ANALYSIS_FAILED` | Ownership processing failed. |

All applicable blockers are returned together. A valid candidate on one ownership path
does not cancel a graph-wide cycle, incompleteness, or limit issue.

## Real-integration warnings

- `IDP_PROFILE_PROVISIONAL`
- `UBO_POLICY_NOT_SPONSOR_CONFIRMED`
- `LIVE_HIERARCHY_UNAVAILABLE`
- `RELATED_PARTY_MAPPING_PENDING`
- `REAL_GOLDTIER_NOT_CONFIGURED`
- `READY_FOR_APPROVAL_UNAVAILABLE`

These do not block a bounded Mock happy path, but remain visible and distinct.

## Stale-readiness and finality policy

The server ignores client-authored readiness. Submission re-reads the current case,
document, and ownership records inside a per-case serialized boundary and re-runs the
shared canonical validator. It creates the immutable minimized snapshot only after that
revalidation. An earlier ready evaluation or historical `VALIDATED` state cannot
authorize submission after evidence changes.

One process-local case lock permits one accepted Mock execution. The snapshot is the
mapper input. A minimal safe target outcome is retained before fallible rich receipt or
CLM terminal translation, allowing duplicate, simultaneous, or recovery requests to
finalize the existing submission without repeating business operations. Repository
versions prevent stale orchestration writes. This is process-local Mock idempotency;
durable or multi-process deployment still requires transactional/distributed
equivalents.

## Sandbox submission observation

The current owner-authorized program uses the same immutable confirmation and target
ledger for Sandbox XPI. Final Review & Send is the final application approval.
The additive `target_submission` projection distinguishes NOT_SUBMITTED, SENDING,
SUBMISSION_CONFIRMED, SUBMISSION_FAILED, SUBMISSION_OUTCOME_UNCERTAIN and
FINALIZATION_PENDING. The last state includes a nonempty fully lifecycle-resolved
retained operation prefix awaiting existing manual safe recovery, or a retained
successful outcome awaiting local finalization. It does not claim provider completion
for unattempted operations. Existing resume authorization/lock/CAS/no-replay guards
remain authoritative; a truly unresolved operation cannot expose this manual action.
Confirmed Sandbox completion requires retained successful
required operations, exact customer readback, receipt and final application completion.
Policy technical success does not prove provider KYC or approval.

Authenticated `POST /api/clm/zero-touch/cases/{case_id}/target-status-check` accepts
only the expected retained submission UUID. Normal CSRF, case scope and fresh
reauthorization inside the owning lock apply. It performs one bounded Search for
that frozen uncertain Sandbox identity. A stale UUID, changed identity or provider
mode mismatch fails closed before Search. The result is an observation only:
NO_MATCH, IDENTITY_UNVERIFIED, CUSTOMER_IDENTITY_VERIFIED, AMBIGUOUS or CHECK_FAILED.
It cannot establish Policy completion, adopt a discovered ID, finalize uncertainty,
resume execution or repeat a mutation. Independent provider-verified recovery remains
under its existing authorization and ledger owner. The browser automatically observes
once per user/session/case/submission and aborts publication on scope changes.

## Submission readiness presentation — 2026-10-05 continuation

Submission readiness means current authoritative evidence/ownership/identity/classification
and target inputs are complete/current enough to prepare a submission. It is not GoldTier
KYC/four-eye/Ready-for-Approval. No prerequisite blockers means the readiness node is Complete
even while final TARGET_CONFIRMATION_REQUIRED remains. Package is Prepared/Complete; final
Review & Send alone requires review. Twelve nodes and the explicit confirmation remain.
Document auto selections retain separate source evidence with PROJECT_DERIVED_POC policy
authority; user fallback uses separate USER selection evidence. Save/auto-bind perform
zero provider calls/target attempts. Current automatic source is checked again before
freezing. Any retained target execution freezes classification and evidence edits.
Actual unresolved Shell/Policy attempts remain uncertain/no-replay; empty intents are
not projected as uncertain. Original historical UAT cause is unknown without its ledger.

R1 currentness repair: a prior USER value that disagrees with a safely assessed current
explicit label requires classification review; neither source silently overrides the
other. The same currentness predicate governs preview, snapshot creation and retained
NOT_STARTED snapshot checks. Current prerequisites govern prepared package/final action
copy; stale confirmation exceptions cannot imply a prepared current package.

R2 mode clarification: retained classification currentness is required in every provider
mode. Explicit observations or selections make classification completeness a prerequisite
even in Mock mode; partial/incompatible profiles require review before snapshot or final
confirmation. Legacy Mock cases without observations or selections retain their existing
optional-classification behavior. The existing owners and final confirmation are unchanged.

## Owner-authorized current classification review — 2026-10-06

The existing document owner retains explicit NO_EVIDENCE/PARTIAL/SAFE_CANDIDATE/CONFLICT/
UNSAFE assessment. Contradictory trusted current observations are not absence. Current
USER and DOCUMENT decisions bind the deterministic trusted evidence fingerprint. A USER
choice made before newly trusted evidence is stale even when its text agrees. A fresh
same-value explicit review binds current evidence and may resolve conflict without
picking a source silently. A later trusted change invalidates that review again.
Raw evidence_state may remain CONFLICT after review; effective state is CURRENT only
when an explicit compatible current decision covers the conflict. Unresolved CONFLICT
or stale decisions block readiness/package/confirmation/snapshot/attempted mutations.
Final Review & Send remains required after local review; review performs provider calls0.
The browser sends its displayed evidence fingerprint; trusted review with a missing or
changed token is refused under the existing lock/reauthorization. Absent/unsafe evidence
remains distinct, and adding non-authoritative unsafe observations does not invalidate
a current USER decision. Existing stricter automatic safeguards remain. New pre-send
classification evidence uses existing intake only before any frozen target intent.
