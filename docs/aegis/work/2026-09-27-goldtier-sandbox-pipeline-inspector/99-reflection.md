# GoldTier sandbox pipeline inspector reflection

## Current outcome (2026-09-28)

The authorized recovery and architecture work is implemented without rewriting the
provider chronology. The durable ledger retains Search as definitive, Shell as one
uncertain attempt, and a separate exact provider recovery of Garden ID `143878` with
`replayed=false`. GoldTier-first orchestration now branches before optional ACRA:
exact verified existing customers skip ACRA/Shell/new Policy and Amend the same ID;
no-match customers alone bootstrap from ACRA and use Shell/Policy/Amend; ambiguity
stops before either provider mutation path.

The current external stop is new and narrower than the historical lost-ledger problem.
The recovered first case durably attempted Create Customer Policy exactly once, but its
network outcome is uncertain. Automatic replay is correctly blocked. Read-only portal
verification requires human reauthentication; only that provider-side evidence can
determine whether the one Policy request committed. No Amend or second external Garden
case may proceed until the outcome is resolved safely.

## Current next authorized action

Human reauthenticates the existing portal tab; Codex then inspects only bounded Garden
policy/audit evidence. Do not replay Policy. If exact provider evidence supplies a
lawful resolution path, retain it through the existing ledger owner before continuing
Amend/read-back and the second Garden acceptance. Otherwise report a genuine new
external blocker. Freeze and independently gate only after the external lifecycle and
full regression matrix complete.

## Historical outcome before D-058 recovery authority

The bounded source, configuration, and UI work includes exact sponsor vocabularies,
fixed Singapore values, case-scoped KYC/segment selection, and strict post-Amend
read-back. The human supplied Garden-only classification authority and one Shell was
attempted through the ledger. Its outcome became uncertain, so no replay occurred.
The later authenticated portal investigation proves that ID `143878` is exact Garden:
the ID, legal name, UEN, Singapore country, DSD cross-reference, shell state, and aligned
creation audit are visible. The original acceptance harness nevertheless used a
process-local in-memory target ledger and exited on uncertainty. Its checkpoint no
longer exists to recover. Policy, Amend, and completed same-ID lifecycle proof therefore
remain blocked without replaying or reconstructing history.

## Historical key judgment

The safe stopping point remains after the one uncertain Shell attempt. Identity is now
exact, but evidence of an attempt is not a recoverable ledger record. Recreating the
checkpoint from prose or substituting `143878` into new persistence would violate the
explicit no-reset, no-recreation, no-manual-substitution boundary just as surely as a
second Shell would violate no-replay.

## Preserved boundaries

- Official ACRA Marketplace Mock remains the configured registry source; Garden stays
  `REVIEW_REQUIRED` / `PARTIAL` with no fabricated ownership evidence.
- GoldTier XPI sandbox is the configured target; local GoldTier Mock remains available
  only to isolated tests and is not a configured-runtime fallback.
- Search uses the existing connector and entity resolver. The one attempted Shell used
  the existing orchestration plan and target ledger; no alternate execution owner exists.
- The browser receives a safe backend-authored projection, not raw provider payloads or
  a frontend-owned reconstruction of business state.
- Related-party, hierarchy, Production, PingFed, and final-approval behavior remain
  outside scope.

## Complexity closure

- Budget status: within-budget for the bounded projection and inspector change.
- Governed now: one backend projector owns the recursive safe processing tree; the
  frontend only renders server order/status. Optional XPI compatibility is limited to
  two named fields and documented as sandbox-observed, not production vocabulary.
- Deferred follow-up: none for duplicate ownership or fallback retirement. The existing
  Mock connectors remain intentionally retained for isolated deterministic tests.
- Completion impact: the implementation slice has focused and broad verification. The
  requested external lifecycle is blocked because the uncertain Shell's original
  process-local ledger entry no longer exists; a fresh independent re-gate is still
  required for the changed candidate.

## Historical next authorized action

Do not retry Shell. Provider identity is proved; the remaining prerequisite is the
original uncertain ledger entry or explicit authority to replace the current
no-recreation/no-manual-substitution constraint. Portal evidence cannot recreate
process-local application state or retroactively make the Shell response definitive.
The GoldTier-first flow is authorized for this POC but remains unimplemented at this
stop. Run any fresh independent gate against this truthful hard stop; do not commit
without exact `PASS`.

## First-gate learning

The first independent gate correctly separated the genuine external blocker from a
local correctness defect. A safe backend projection must preserve historical execution
order as well as current order; a `NOT_REACHED` v2 stage is still false when that stage
did not exist in a terminal v1 workflow. The remediation now keys the presentation
order from the persisted stage-order version and keeps Search under the historical
target sequence for v1.

The first re-gate then exposed a second presentation edge: transport evidence does not
exist during the interval after the automation enters Search but before the checkpoint
is retained. Defaulting that interval to `NOT_ATTEMPTED` hid active work. The fix reuses
the automation stage owner only for that precise interval; it does not infer a Search
result, synthesize checkpoint evidence, or add a frontend state owner.

A final adversarial read also separated identity provenance inside the tree. A later
Shell-created ID is a retained target fact, but it is not a Search result when Search
returned no match. The Search node now carries an ID only for exact-match reuse; the
target path remains the owner of IDs created after no-match.

QG-03 showed that projection truth is a coherent view, not only an enum. For the
pre-checkpoint interval, status, text, timestamp, blocker, count, branches, and identity
must all describe the same retained facts. The final repair closes that whole view:
automation owns stage state, CLM events own the available Search timestamp, and only a
checkpoint may supply candidates, disposition, or matched identity.

The post-mutation gate reinforced that the no-replay boundary must be truthful in both
runtime state and durable prose. The reconciliation now distinguishes attempted from
completed operations and treats ID `143878` only as incomplete recovery evidence. It
also exposed a compatibility edge in browser projection: legacy cases without a
GoldTier target policy must remain visible but non-editable, matching the backend owner
instead of offering a mutation that can only fail.
