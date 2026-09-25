# PRE-PHASE 22 — Provider Orchestration & Sandbox Testing
# Fourth Final Independent Quality-Gate Report

## 1. Executive Result

**FAIL**

The exact frozen candidate was reviewed and its identity matches the assigned manifest.
All five previously reported findings are closed, including the genuine continuation
failure behind `PP22-FQG-001`. However, one new **High** persistence-integrity defect
remains: the Mongo read boundary parses a durable zero-touch automation aggregate but
does not run its cross-field invariant validator. Explicit current-v2 and legacy-v1
stage-order tampering is therefore accepted at decode/startup even though
`validate_automation_record` rejects the same aggregate. This is a material fail-open
condition at the durable source-of-truth boundary, so PRE-PHASE 22 is not ready to close
and Phase 22 remains held.

## 2. Candidate Identity and Fingerprint

| Item | Independently observed value |
|---|---|
| Repository | `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm` |
| Branch | `feature/pre-phase22-provider-orchestration` |
| `BASE_SHA` | `5f71b4d4d4dcf11ccf4d742446a0fec67aac7da3` |
| `HEAD` | `5f71b4d4d4dcf11ccf4d742446a0fec67aac7da3` |
| `origin/main` | `5f71b4d4d4dcf11ccf4d742446a0fec67aac7da3` |
| merge-base | `5f71b4d4d4dcf11ccf4d742446a0fec67aac7da3` |
| Staged paths | `0` |
| Candidate paths | `95` |
| Candidate SHA-256 | `917df3133084f5e0326244047e19a889727e2d30da66b4c8054acbe92345418a` |

The inventory was recomputed as the ordinal-sorted union of tracked
`git diff --name-only` and untracked `git ls-files --others --exclude-standard`, excluding
only this report. Each row was `path<TAB>git hash-object`, joined by LF with no trailing
LF, and SHA-256 hashed as UTF-8. A final recomputation immediately before report writing
again returned exactly 95 paths and the assigned digest. There is no candidate drift.

## 3. Phase Acceptance Checklist

| Acceptance/adverse surface | Result | Direct evidence |
|---|---|---|
| Identity-bound GoldTier Search occurs before later target work | PASS | Current stage order places `GOLDTIER_SEARCH` after Registry; focused orchestration and persistence suites passed. |
| Exact/no-match/ambiguous/failure routing and Shell skip | PASS | Source and focused tests show exact match reuses the resolved party and skips Shell; no-match creates Shell; ambiguity and technical failure stop safely. |
| Incremental durable Shell → Policy → Amend ledger, CAS, restart, no replay | PASS | Single ledger owns attempted/completed operations; focused persistence/orchestration checks passed, including uncertain target activity. |
| Sandbox/write and related-party `childId` blockers | PASS | Write readiness and unresolved related-party child-ID authority remain explicit blockers; no unsupported relationship creation is enabled. |
| HR-only `PROVIDER_SANDBOX_TEST`, without `CASE_ACCESS` | PASS | API returns safe fixed denial outside the capability; focused backend/frontend tests passed. |
| Progress/cache scope | PASS | Provider-console query data is identity-scoped and capability-driven; no case cache access is required. |
| ACRA local Mock / API Marketplace Mock / generic sandbox / Live truth | PASS | Explicit API Marketplace Mock is recognized but fails closed pending authorized auth; local Mock remains Mock; generic sandbox is partial; no Live claim is made. |
| COI optional address, mismatch, and legacy-required behavior | PASS | Optional address is bounded to the current COI profile, mismatch still reviews, and the legacy profile still blocks absence. |
| Provisional `accountEntityType` and provider truth | PASS | Provisional status remains documented; Mock and sandbox classifications are not promoted to Live. |
| Security, logging, secrets, architecture, source-of-truth | **FAIL** | Secret/governance checks pass, but the durable Mongo read boundary accepts cross-field-invalid automation aggregates; see `PP22-4QG-001`. |
| Persistence/schema compatibility | **FAIL** | Valid base-v5 legacy compatibility is repaired, but invalid explicit stage-order metadata is not rejected on decode/startup. |
| Q-016 deferred; Phase 22 held | PASS | Q-016 remains deferred and no Phase 22 authorization is claimed. |

## 4. Closure of Prior Findings

| Finding | Status | Fourth-gate evidence |
|---|---|---|
| `PP22-QG-001` — generic restart skipped Search | **CLOSED** | Current ordering and restart tests run Search before Document/later target stages. |
| `PP22-QG-002` — Mock mislabeled `SANDBOX_PARTIAL` | **CLOSED** | Mock status now reports `mode=MOCK`, `classification=MOCK`, and `write_enabled=false`; sandbox remains `SANDBOX_PARTIAL`. |
| `PP22-QG-003` — HR Search returned `NOT_ASSESSED` | **CLOSED** | HR provider Search delegates to the existing identity-bound resolver and returns its real bounded disposition. |
| `PP22-RQG-001` — optional COI address still blocked | **CLOSED** | Current COI optional-address omission no longer blocks; mismatch and legacy-required profiles retain their adverse behavior. |
| `PP22-FQG-001` — schema-v5 stage-order continuation | **CLOSED** | The prior direct probe was malformed because `model_dump` omitted the excluded backend-only `ownership_provider_binding_id`. A canonical `_encode` base-v5 raw shape decodes; absent metadata is interpreted as legacy v1 on a copy without mutating raw. Safe pending and review continuations CAS-rebase to v2, then perform an actual Search before later target writes. Interrupted documents do not fabricate Search completion; current and legacy uncertain target activity remains no-replay; historical terminal state remains terminal without a retroactive Search event. |

`PP22-FQG-001` is not reopened by the new finding. The repaired missing-metadata
compatibility path is valid. The new failure concerns **explicitly present but internally
inconsistent/tampered metadata** crossing the persistence read boundary without aggregate
validation.

## 5. Contract and Integration Findings

No new sponsor-contract contradiction was found. The reviewed candidate preserves the
recorded provider truth: ACRA local deterministic Mock is the default, ACRA API
Marketplace Mock has no invented OAuth contract, generic sandbox support is partial,
BizFile is dormant, GoldTier is Mock only, and no Live interoperability is claimed.
Related-party dispatch remains blocked until the sponsor-defined `childId` lifecycle is
proved. Q-016 remains deferred.

No external provider was called and no provider state was mutated. Passing mock, contract,
and schema checks are not external interoperability evidence.

## 6. Tester and Adversarial Findings

### Independently observed passing evidence

- Focused backend acceptance/regression suite: **274 passed** across persistence,
  zero-touch orchestration, CLM orchestration, provider sandbox API, ACRA modes,
  GoldTier XPI sandbox, and reconciliation.
- Focused frontend provider/navigation/integration suite: **3 files / 79 tests passed**.
  The first sandboxed launch hit environment `spawn EPERM`; the approved rerun passed.
  React SSR `useLayoutEffect` warnings were known non-product warnings.
- Contract suite: **44 passed** with the repository contract helper on `PYTHONPATH`.
- Focused Ruff over the reviewed backend owners/tests: **PASS**.
- Direct governance checks: project state, architecture, policy authority, external
  provider readiness, and supported secret patterns: **PASS**.
- `git diff --check`: **PASS**; Git emitted only line-ending conversion warnings.

### Independent adversarial persistence reproducer

Using the same codec and model types as the persistence tests:

1. A raw record produced from `model_dump(mode="json")` was correctly rejected as
   malformed because it omitted the excluded backend-only binding field. This confirms
   the earlier failed gate's probe shape was not canonical.
2. A canonical `_encode` base-v5 raw record with `stage_order_version` removed decoded as
   v1, retained the legacy Registry prefix, and left the caller's raw object unchanged.
3. An explicit v2 raw aggregate carrying a v1-shaped prefix/status decoded successfully,
   while direct `validate_automation_record(decoded.automation)` rejected it.
4. The inverse explicit v1 aggregate carrying a v2-shaped prefix also decoded
   successfully, while the aggregate validator rejected it.
5. For the explicit v2 pending inconsistency, `_recover_interrupted` returned the invalid
   snapshot unchanged (`RECOVERY_CHANGED=False`).
6. A direct v2 → v1 write transition was correctly rejected, showing the write-side
   downgrade guard exists but does not close the read-side gap.

### Unavailable/relied-on evidence

Physical Mongo was not run. `docker version --format '{{.Server.Os}}'` failed because
`//./pipe/dockerDesktopLinuxEngine` does not exist. No Mongo URI was accessed, printed,
or mutated. Therefore this gate does not claim physical restart evidence.

The fresh implementer evidence was reviewed but not represented as independently rerun:
backend **1369 collected = 1334 passed / 35 skipped** with three known malformed-fixture
warnings; frontend **23 files / 286 tests**; Ruff; strict Mypy over 106 files; TypeScript
and build over 116 files; contracts 44; delivery 4; expanded governance/security 242;
intelligence 17/3/5; GoldTier 19 valid / 19 quarantined invalid / 48 not validated;
Playwright 14; Windows lifecycle 23; and direct governance, secret, dependency, and
whitespace checks green. These broad results do not override the independently reproduced
uncaught durable-invariant defect.

A supplemental governance-unit invocation was invalid in this restricted environment:
Python temporary directories were redirected into the workspace and became
permission-inaccessible, causing setup/teardown failures rather than product assertions.
It is recorded as an execution-environment failure, not a candidate failure or pass. The
coordinator was notified to remove only those task-created temporary directories under
separate authority; they are not among the 95 candidate paths.

## 7. Code and Architecture Review

### `PP22-4QG-001` — High — Mongo decode accepts invalid zero-touch aggregate invariants

**Evidence**

- `apps/backend/app/persistence/mongo_case_store.py:489-498` injects legacy v1 only when
  stage-order metadata is absent. That compatibility conversion is correct and does not
  mutate the caller's raw object.
- `apps/backend/app/persistence/mongo_case_store.py:517-523` runs Pydantic parsing and
  unknown-field rejection, then returns the snapshot without calling
  `validate_automation_record`.
- `apps/backend/app/domain/zero_touch.py:285-315` contains the required cross-field
  aggregate validation, including stage-order prefix and pending-status consistency.
- `apps/backend/app/persistence/mongo_case_store.py:710-849` validates only a particular
  document-recovery mutation; when no recovery mutation applies it returns the decoded
  snapshot unchanged.
- The independent reproducer accepted both v2-with-v1-shape and v1-with-v2-shape raw
  records at `_decode`, while the domain validator rejected them. A current-v2 pending
  inconsistency also survived `_recover_interrupted` unchanged.

**Impact**

The durable repository is a source-of-truth and trust boundary. A malformed, stale,
partially migrated, or tampered Mongo row can be admitted as a valid current aggregate
despite violating the stage-order/version and status/prefix rules. Terminal records may
be returned before advancement, and non-terminal records are trusted until a later save
path happens to validate them. The system therefore does not fail closed at startup/read
and cannot claim strict Mongo schema/invariant enforcement for the new v1/v2 workflow.

**Required remediation**

After schema conversion, model validation, unknown-field rejection, and `_id` identity
verification, `_decode` must call `validate_automation_record(snapshot.automation)` when
automation is present and translate its `ValueError` to `PersistenceDataInvalidError`.
Add raw persistence tests covering at least explicit v2 with a v1 prefix/status, explicit
v1 with a v2 prefix/status, malformed current-v2 terminal state, and downgrade/tamper
combinations. Preserve the passing canonical missing-field base-v5 behavior: decode as
legacy v1 on a copy, no raw mutation, CAS rebase before Search, and no replay for terminal
or uncertain target activity. Rerun focused persistence/orchestration checks and the
independent gate; run physical Mongo when infrastructure is available.

No second architecture owner, provider bypass, frontend authorization owner, direct
ACRA-to-GoldTier mapping, or competing target ledger was found.

## 8. Security Review

Capability enforcement, safe fixed denials, cache identity scope, secret-pattern checks,
sanitized provider responses, and absence of Live claims passed review. No `.env`, private
sponsor artefact, credential, external provider, or database was accessed.

`PP22-4QG-001` is also a security/integrity concern: explicit durable metadata tampering
is accepted rather than quarantined at the repository boundary. No secret exposure was
observed, but the fail-open decode is unacceptable for trusted workflow state.

## 9. Required Fixes and Residual Limitations

Current blocker:

1. Fix and regression-test `PP22-4QG-001`, then obtain a fresh independent quality gate
   against a newly frozen exact candidate.

Residual limitations that are not defects in this bounded POC:

- Physical Mongo evidence is unavailable until a disposable allowlisted database can be
  started; no claim is made for physical restart behavior in this gate.
- ACRA API Marketplace authentication remains unresolved and fails closed.
- GoldTier remains Mock only; real PingFed/TLS/runtime interoperability is not proved.
- Related-party write remains blocked by unresolved `childId` lifecycle authority.
- Q-016 remains deferred; Phase 22 remains held.

## 10. Readiness

PRE-PHASE 22 is **not ready to close** because one High durable-state validation defect
remains. Phase 22 is **not authorized** by this report.

Live ACRA verification: **not ready / not proved**.
Real GoldTier integration: **not ready / not proved**.

## 11. Git Status and Review Separation

The review used branch `feature/pre-phase22-provider-orchestration` at the SHA recorded
above. No implementation code, tests, documentation, configuration, Git metadata,
commit, push, PR, merge, provider state, or database state was changed by this reviewer.
The only permitted candidate write is this report. The task-created inaccessible
temporary test directories are explicitly excluded from the candidate inventory and
were handed to the coordinator for authorized cleanup. No implementation remediation or
next phase was started.

## 12. Final Verdict

**FAIL**
