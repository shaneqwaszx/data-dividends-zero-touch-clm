# Policy Activation Contract

## Gate

A future runtime policy may be activated only when all of the following exist:

1. an explicit sponsor-backed decision for the exact behavior;
2. a closed or superseded blocking question with a durable source reference;
3. an updated registry entry classified `SPONSOR_CONFIRMED`;
4. bounded runtime owners, API/schema/security/persistence impacts, and adverse cases;
5. implementation tests, affected regression, and fresh independent acceptance.

`OBSERVED` describes a fact. `PROJECT_DEFINED_PROVISIONAL` permits only the labelled POC
behavior. `UNKNOWN_BLOCKED` permits no activation. Public regulation, convention, a
prototype, a Mock success, or a local role never substitutes for sponsor authority.

## Supplied risk

Before adding a risk field or reaction, Q-017 must identify the authoritative producer,
accepted vocabulary, validation and rejection rules, provenance, update authority,
retained evidence, readiness effect, workflow reaction, EDD/reviewer action, and
approval implications. A supplied value must stay distinct from calculated risk. Until
then there is no risk score, risk engine, readiness block, EDD route, or risk-based
priority/SLA/escalation.

## Review authority

Before changing review behavior, Q-014/Q-015 must identify eligible role/capability,
self-review rule, separation-of-duties model, permitted dispositions, reject/rework/
resume authority, retained reviewer evidence, source/conflict authority, and final
approval owner. D-009 authorizes human exceptions only; it does not answer those items.

## Assignment

Before assignment/reassignment, Q-016 must identify who assigns and reassigns, whether
one or multiple teams may own/share a case, the required reason/history, visibility,
mutation authority, concurrency semantics, and authorization failure behavior.

## Priority

Before changing P1–P10, Q-016 must define allowed values, which direction is highest,
who may mutate, and whether priority is ordering-only or affects routing, SLA, deadlines,
escalation, notification, assignment, or risk. Current P1–P10 ordering-only behavior is
project-defined provisional and must not be migrated or reinterpreted without an
authorized compatibility plan.

## Ready-for-Approval

Before any Ready-for-Approval state or action, Q-001 must define prerequisites, internal
versus GoldTier state, transition owner, automated versus human responsibility, target
operation/API, failure/idempotency/recovery behavior, evidence, and relationship to final
approval. `COMPLETED / MOCK_GOLDTIER_SUBMITTED` remains distinct from
Ready-for-Approval.

## Related dependencies

Activation must also account for Q-003 document scope, Q-004 final legal UBO policy,
Q-005 validation ownership, Q-013 privacy/retention/access, Q-018 production handoff,
and Q-002/Q-006/Q-007/Q-009/Q-010/Q-011 where hierarchy or GoldTier contract details
affect the chosen behavior. A decision in one domain does not silently resolve another.

## Phase24C owner-authorized POC control plane — 2026-10-02

D-064 supersedes this contract's sponsor-activation prerequisites only for the bounded
owner-authorized business parameters already consumed by current POC runtime owners.
HR (POLICY_MUTATE) creates/edits their own draft, provides a reason, stages reset defaults
and submits. Director (POLICY_APPROVE) decides a submitted current-base proposal with a
reason; proposer and decider must differ. Reauthorization occurs inside the owning
PolicyManagementService lock and persistence uses singleton CAS. RM and onboarder view.
No role directly activates through legacy update/reset/showcase endpoints (safe 403).
Only approval creates a new ACTIVE version; rejection keeps ACTIVE unchanged. The
baseline is DEFAULT, and previous active value sets are SUPERSEDED. Bounded history
retains proposal/base/decision/effective metadata and deterministic active SHA-256.
New cases bind ACTIVE values. Existing in-flight/completed cases remain frozen, including
registry TTL and semantic classifier parameters. Existing D-056 target-only rebind must
preserve frozen business policy identity/version/time. No new rebind feature is added.
Security/provider/target contract invariants are fixed. This is USER_AUTHORIZED_POC,
not sponsor/production RBAC or regulatory approval. Q-001/Q-004/Q-014/Q-015/Q-016/Q-017
remain open for their separate production, legal, source, reviewer and risk questions.

## Slice E prospective synthetic impact candidate — 2026-10-03

PolicyManagementService remains the sole proposal/activation owner. Its existing
GET /api/policies/proposals/{proposal_id}/impact now uses a pure PolicyImpactAdvisor
helper and strict PolicyImpactResponse. No new endpoint, repository, durable monitor,
background job, provider call, case scan or approval capability is introduced.
Comparison resolves the exact proposal base from ACTIVE or bounded retained history;
missing history fails closed. Stale proposals remain stale and existing submission/
decision CAS rejects them. Before/after evaluate identical controlled inputs.

The response retains before/after classifier and runtime fields and current/default/
proposed changes; adds base values, proposal/catalogue revisions, comparison identity,
direction, stages, named scenarios, materiality, coupling, reason codes, bounded
counts/deltas and explicit unknowns. Positive ownership legacy Boolean outcomes remain
compatible. For zero, ownership_numeric_candidates widens to three nullable outcomes:
null means NOT_ASSESSED, never false or zero candidates. This is an explicit type
widening for an existing contract disagreement: policy catalogue accepts zero while
the ownership engine/current/prior/candidate types and OWNERSHIP_UBO_PROFILE require
(0,100]. Slice E does not reconcile or activate a new zero-threshold runtime behavior.

SYNTHETIC_POLICY_IMPACT_V1 contains at most64 named scenarios: document semantic
confidence/boundaries and blockers; registry and definitive-negative ages/strict expiry;
Decimal direct/boundary/multipath/incomplete/synthetic60/40 ownership; the existing
14-example SYNTHETIC_SEMANTIC_V1 classifier. Dynamic boundary inputs are constructed
once for both policies. SHA-256 binds the exact controlled input definitions; benchmark
hash/rule identity remains owned by OwnershipEvidenceTagger. No raw inputs are projected.

HIGH describes document action, provisional candidate or freshness transitions;
MODERATE describes semantic labels or definitive-negative cache transitions; LOW
describes classifier score changes without label changes; NO_OBSERVED_CHANGE means
no supplied outcome/score transition. NOT_ASSESSED means an unsupported/unmodelled
effect, including the13 active intelligence parameters and unsupported zero ownership.
These categories never assess compliance. Counts are stage-specific supplied scenarios,
including coincident boundary inputs; they are not production-volume forecasts.
Registry permissiveness compares configured windows without predicting ACRA traffic.
Classifier macro/micro precision/recall/F1 retain current14-example authority, with no
trained-model, legal or workflow-approval claim. Legal UBO, Ready-for-Approval, sanctions/
PEP, production volume/load/retry and GoldTier approval remain NOT_ASSESSED.

Bounds: existing64-rule catalogue/change maximum,64 projected scenarios,14 classifier
examples and262144 UTF-8 response bytes. No real case population is evaluated. Existing
HR proposal/edit/submit and independent Director approve/reject remain unchanged;
impact never changes eligibility or cases. Existing cases keep frozen snapshots, new
cases bind ACTIVE. Frontend comparison is session-memory only, aborts replaced requests,
and validates proposal/catalogue identity before rendering. No query-client/auth owner
or mutation retry changes.

Slice E received independent PASS for its exact frozen branch candidate;
cumulative G acceptance and publication remain separately gated. It establishes no sponsor policy,
production interoperability or final publication readiness.

Classifier policy-version context is explicit: before uses the actual ACTIVE/retained
base; an unapproved proposal uses the next aggregate version as PROSPECTIVE_UNRESERVED
(no reservation or activation guarantee). An approved proposal uses its retained actual
activated_version as ACTIVATED_PROPOSAL. Numeric outcomes never grant activation.
