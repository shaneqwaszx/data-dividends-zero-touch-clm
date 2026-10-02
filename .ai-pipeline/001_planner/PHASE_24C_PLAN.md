# Phase 24C registry, policy and UX hardening

Authority: explicit task attachment, conditional continuation satisfied by the fresh
Stage Recovery round-1 independent MINI PASS. Accepted content identity:
`93534f0e7fe7ccc5b1ec68342dff7a2b6aaa2154bb2135880f02a5421bb928c6`;
report SHA-256 `a456cee308b781a61d9389b26618e3fda2a18348b09dcf9e3dfb5b4994900d86`.
Stage recovery used one of its own two remediation rounds. Preserve every prior report.

Worktree: existing phase24-registry-identity-ownership-ubo checkout. Branch:
`feat/phase24-registry-identity-ownership-ubo`. HEAD/base/inspected origin/main:
`039101b69772c4c9ae4ca7b4a7ca3e4c19b03f4c`. Index empty; 96 inherited changed/new
paths at entry. No remote-freshness claim. No commit/push/PR/merge/Phase25.
Coordinator is the sole implementation writer. Fresh independent final combined gate
is mandatory, with a distinct two-round Phase24C remediation budget.

## Architecture review: PROCEED

Existence check: extend RegistryAcquisitionCoordinator/RegistrySnapshotRepository and
AcraRegistryProviderAdapter for normalized operation reuse; extend PolicyManagementService,
PolicyCatalogue and existing memory/Mongo singleton repositories for proposal/activation.
Extend the existing OwnershipEvidenceTagger for parameterized semantic labels. Decimal
quantification stays exclusively in OwnershipAnalysisService. Existing CaseDetail and
StageDisclosure own the seven stages. PolicyRules owns the policy view. No new framework,
database owner, router, arithmetic, auth, query client, or target execution owner.

Dependency direction remains routes -> services -> domain/repository ports -> adapters.
Registry DTO -> canonical operation evidence -> cache/case; never raw payload persistence.
Backend capability owner determines HR proposal and Director decision authority.
Reauthorize in the policy mutation lock; persist under existing singleton CAS.
Existing case snapshots remain frozen. Policy proposals never silently activate.
GoldTier exact-UEN Search is unsupported by inspected XPI contract: record
GOLDTIER_SEARCH_SKIPPED_UNSUPPORTED_IDENTIFIER; no invented search or target history read.

## Persistence review: PROCEED

Registry schema1 remains strict complete-only. Explicit schema2 permits normalized
operation prefixes and definitive NOT_FOUND, with exact provider/key/revision binding,
UTC timestamps and CAS. Failed operations never count as reusable evidence; uncertain
failures never count as negative hits. Complete-only case binding remains unchanged.
Policy historical catalogues are explicitly interpreted as historical active rules;
new aggregate retains bounded proposals and superseded rule versions under existing CAS.
No read-time case rewrite, upsert, retention/TTL deletion, or silent fallback.
New case snapshot fields are optional for historical readers; None retains exact legacy
behavior rather than applying newly active policy. Current snapshots freeze approved
registry TTL and semantic classifier parameters alongside existing runtime thresholds.

ADR-002 and policy/admin/cache profiles will receive dated scope supersession sections.
The old direct policy activation path is retired by this phase; historical evidence is
retained. Provider mode remains Mock/Partial/Local as currently proved, never Live.

## Acceptance and evidence

All 24 explicit Phase24C deliverables and their adverse/count/viewport matrices in the
owner task apply. Focused offline provider/policy/classifier tests precede broad backend,
frontend tests/typecheck/build, contracts/governance/security/Ruff/mypy, physical Mongo,
actual browser QA at 320/360/768/1280/1440/1920 and 200% zoom, developer adversarial
self-remedy, exact freeze and fresh independent combined gate. No normal ACRA calls.
Physical tests use only freshly generated allowlisted databases on the coordinator-owned
mongo:7 container clm-stage-recovery-20261002, loopback27025; cleanup absence required.
No retained database, Atlas, clm_poc, protected payload or historical GoldTier access.

Tools observed this session: shell/file, independent review agents, browser CUA and repo
browser harness. Python runtime reuses executable/dependencies only from Desktop .venv;
imports are worktree-owned. Worktree writes require narrow escalation. No additional
package/lockfile churn is planned. Current/tested/reviewed content identities stay distinct.

## Authorization checkpoint

The first policy schema/RBAC write was rejected by automatic approval review. Its stated
reason was that the trusted transcript did not explicitly authorize the exact schema,
authorization and activation changes. No source write from that command executed.
An explicit approval question is pending. Do not retry that rejected write or implement
it indirectly until owner approval resolves the review rejection. PROCEED above is the
architecture assessment, not evidence of an executed implementation or permission waiver.
Unaffected offline baseline checks and read-only call-count measurements are completed.
See PHASE_24C_AUTHORIZATION_CHECKPOINT_HANDOFF.md for evidence and remaining scope.
The Stage Recovery exact 94-entry candidate and fresh MINI report remain unchanged.
The completed stage-recovery disposable Mongo resource was safely removed; provision a
new task-owned server and fresh allowlisted databases for subsequent physical work.

## Explicit owner authorization resolved

Owner attachment 7b0e25bf-53cf-4aaf-b937-6876db5c0173 was read in full on this
continuation. It explicitly authorizes persistent proposal/version/approval/activation,
HR proposal/Director decision RBAC, four-eyes checks with reauthorization inside the
owning lock, runtime business parameters, safe simulation, frozen case policy,
related registry/UI/testing and the independent gate. The prior approval blocker is
resolved. No publication, Phase25, Live call, new case-policy-rebind feature or security
parameter editing is authorized. Existing Role.DIRECTOR is the only current director
role; do not invent a higher role. Inherited explicit SG target-only rebind remains
separate and cannot rebind frozen business/classifier/cache parameters.

## Case envelope compatibility delta

Current writes use explicit case schema8 for approved registry/classifier parameters and
version2 classifier evidence. Schemas1..7 remain strict in-memory reads without a
read-time database rewrite or global-policy lookup. An old envelope containing new
approved parameters or version2 semantic tags is invalid; old absent/null fields retain
legacy behavior. Schema7 retains all accepted Stage Recovery fields. Existing CAS,
identity validation, portfolio schema allowlists and update-only persistence remain.

## Mock cache composition delta

The normalized cache remains explicitly enabled and permits the existing synthetic
Mock and official API Marketplace Mock modes. The latter receives a distinct exact
data-set namespace; Sandbox and Live remain prohibited. All normal verification uses
fake transports, with no remote ACRA request. Physical Phase24C uses the newly owned
mongo:7 container clm-phase24c-20261002, label clm.task=phase24c, loopback27025 and
fresh generated p145/p16 (plus existing regression-lane prefixes) databases only.
The prior Stage Recovery container is absent. No retained application resource is used.

## Governance checker alignment

CI_TOOLING additionally applies to the bounded policy-authority current-catalogue
claim assertion and its regression fixture: the authorized catalogue has35 seeds,
retaining13 intelligence bindings. This does not activate the separate sponsor-policy
production registry or close any sponsor question. All existing authority gates remain.
