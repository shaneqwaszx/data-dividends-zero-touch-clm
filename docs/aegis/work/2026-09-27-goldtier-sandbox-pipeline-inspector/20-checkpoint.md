# GoldTier sandbox pipeline inspector checkpoint

## TaskStartSnapshot

- Repository: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm`
- Branch: `feat/goldtier-sandbox-pipeline-inspector`
- Base/current-main/HEAD: `463ecdcb4357bb44618cdd5b277671766543dbfc`
- Initial state: clean; `.env` and `private/` ignored and untracked.
- Runtime: Python 3.12.10, Node 22.23.3, npm 10.9.9, Playwright 1.56.1,
  Git and Poppler available; ports 8000 and 5173 initially unused.
- UI capability: Chrome computer-use connection is available, including an existing
  authorized GoldTier portal tab; any credential entry remains a human handoff.
- External authority: bounded Search/Shell/Policy/Amend and read-back are authorized
  only against `portal.gt.deltacapita.net` environment `anz-nutmeg` with synthetic data.
- Coordination: one coordinator owns all writes and external actions; three read-only
  discovery specialists inspected sponsor contract, backend gaps, and frontend gaps.

## Current continuation checkpoint (2026-09-28)

- D-058/ADR-006 authorizes explicit `PROVIDER_VERIFIED_RECOVERY`. Schema v6 now retains
  the original uncertain Shell attempt separately from exact provider recovery ID
  `143878`; the recovered fact and case projection survive Mongo restart, are
  idempotent, and perform zero Shell calls.
- GoldTier-first orchestration is implemented. Bounded initial identity and SG
  eligibility precede Search. Exact verified prior state skips ACRA, Shell, and new
  Policy creation; no match alone acquires ACRA and may execute Shell then Policy;
  ambiguity stops before ACRA and all mutation. Documents can reconcile a supported
  change and Amend/read back the same retained ID.
- The first real Policy intent was durably persisted and sent exactly once. Its network
  outcome remains uncertain. Authenticated read-only portal evidence later proved one
  Singapore Policy request on ID `143878`, status `Requested`. D-059 now permits the
  original ledger to retain that provider-verified recovery without replay; it does not
  interpret `Requested` as approval, completion, or activation.
- The Policy recovery is now recorded through the existing ledger owner with operation
  `POLICY`, authority `PROVIDER_VERIFIED_RECOVERY`, origin
  `UNCERTAIN_DURABLE_LEDGER`, Policy `Singapore`, status `Requested`, and
  `replayed=false`. A separate-process Mongo reload proved ID `143878`, both Shell and
  Policy recoveries, attempted `SEARCH,SHELL,POLICY`, definitive `SEARCH`, lifecycle-
  resolved `SEARCH,SHELL,POLICY`, and no Amend attempt all survive restart.
- The pre-Amend checkpoint passed with the actual `GoldTierXpiSandboxConnector`,
  environment `anz-nutmeg`, target ID `143878`, the two recovery facts, no earlier Amend,
  and a valid bounded sanitized preview. The runner stopped with `AMEND_ATTEMPTED=false`.
  Exactly one Amend was then attempted through orchestration. Its transport outcome was
  uncertain, so the runner stopped with attempted `SEARCH,SHELL,POLICY,AMEND`, definitive
  `SEARCH`, lifecycle-resolved `SEARCH,SHELL,POLICY`, and no replay.
- Read-only audit on the same portal record shows one API-connect Amendment sequence:
  `Created` at 08:47:48 followed by `Valdiation Failed` at 08:47:49 on 2026-09-28. The
  Overview still binds ID `143878`, `GARDEN BUSINESS`, UEN `11111999A`, Singapore, the
  Garden KYC type, and exactly one Singapore Policy with status `Requested`. This is a
  provider-side failed outcome, not Amend success. No same-ID read-back, second Garden
  case, candidate freeze, independent Quality Gate, or local commit is authorized while
  this external failure remains unresolved.
- The same canonical ledger now retains an Amend `PROVIDER_VERIFIED_FAILURE` fact with
  normalized `PROVIDER_VALIDATION_FAILED`, original provider spelling as sanitized
  evidence, original transport uncertainty, and `replayed=false`. Amend remains attempted
  but non-complete and non-lifecycle-resolved. A zero-network record run and an independent
  process reload both passed against retained database class `clm_p12_*`.
- The exact reconstructed Amend request was `goldTierId=143878`, `policy=Singapore`, with
  `anzsic` and `groupCompanyName` omitted and no empty fields. Portal task detail exposed
  `KYC Edit Pool`, "Amendment requires a KYC user", zero document/requirement dependencies,
  and blank audit Reason/Output. It exposed no failed field or validation rule. Diagnosis
  is exactly `E. INSUFFICIENT_EVIDENCE`; no mapper remediation or external retry is
  authorized.
- Focused verification for this diagnosis slice passes: 161 backend tests, Ruff, strict
  configured mypy over 108 sources, frontend typecheck, 5/5 focused frontend tests,
  governance/security checks, whitespace hygiene, and a final zero-network Mongo restart
  verification. The full matrix and independent gate were not run in this diagnosis-only
  slice.
- Current local evidence after the exact-existing Policy-skip correction includes
  backend `1,416 passed / 36 skipped`, Ruff, strict mypy over 108 source files,
  frontend `291/291` tests across 24 files, typecheck, a 117-module production build,
  44/44 contract tests, 14/14 isolated Playwright lifecycles, and 36/36 tests across all
  nine physical Mongo suites. Architecture, project-state, provider-readiness,
  policy-authority, and secret checks pass. The disposable Mongo 7 container used for
  the final physical run was stopped and removed.
- No commit, push, PR, or merge has occurred.

## Historical checkpoint before authorized recovery

- S1 contract/baseline/capability preflight: complete.
- S2 reconcile XPI optional policy fields and configured provider enforcement: complete.
- S3 add factual backend-authored pipeline projection and accessible frontend tree: complete.
- S4 focused and broad deterministic verification: complete after the Singapore
  continuation; the affected backend, frontend, build, governance/security, contract,
  and isolated browser suites pass.
- S5 configure the local ignored `.env` and prove real Search through runtime connector: complete.
- S6 execute at most one ledger-owned sandbox onboarding and read-back: stopped safely
  after exactly one Shell attempt returned an uncertain outcome. Garden's authorized
  case classifications were bound before execution. Attempted operations are
  `SEARCH, SHELL`; only `SEARCH` is definitively completed. No replay, Policy, Amend,
  or post-Amend read-back occurred.
- S7 verify the retained customer in the portal without disclosing credentials/data:
  complete in the later continuation. The existing authenticated `anz-nutmeg` session
  exposed one bounded Garden record. ID `143878`, `GARDEN BUSINESS`, UEN `11111999A`,
  Singapore, `Shell Record`, the Garden KYC type, a DSD cross-reference, and a single
  creation-time `Requested` audit event were verified read-only. Lifecycle audit was
  empty. Singapore policy scaffolding had no status/request flags and is not application
  Policy-call evidence. Registration type and booking entity were not independently
  visible.
- S7a recover the uncertain Shell through the original ledger: blocked. Portal identity
  is `EXACT_RECOVERY_PROVED`, but the acceptance harness used an in-memory ledger and
  exited on uncertainty. Its entry no longer exists outside sanitized prose. Recreating
  it or inserting the recovered ID into new persistence is explicitly prohibited. No
  Shell replay, Policy, Amend, read-back, or second Garden case occurred.
- S7b GoldTier-first implementation: authorized for this POC but not started after the
  original-ledger hard stop. Current runtime remains ACRA-first; no zero-call/existing-
  customer behavior is claimed.
- S8 security/regression/hygiene review and freeze candidate: complete.
- S9 independent QG and bounded remediation/re-QG until exact PASS or genuine external blocker:
  the first gate returned `FAIL` for the required external evidence and found QG-01,
  a historical v1 pipeline-order defect. QG-01 is remediated and locally verified;
  the first re-gate verified QG-01 closed and found QG-02, an active Search status
  projection defect. QG-02 is remediated and locally verified; a second fresh
  independent re-gate is pending. The former registration/policy vocabulary and Garden
  case-selection blockers are resolved; the external lifecycle remains blocked at the
  uncertain-Shell/no-replay boundary.
  The Singapore-continuation gate found no implementation/security defect and confirmed
  that stop, but found QG-SG-01: the reconciliation prose counted six Searches while its
  table recorded seven and called the last three configured-service calls the last two.
  The owning record is corrected; a fresh report-only re-gate is required.
  That re-gate closed QG-SG-01 and found QG-SG-02, a low test-inventory accounting
  mismatch. Reproduction proved the repository-defined `.venv` inventory is
  `1,353 passed / 35 skipped`; the earlier 1,401 count came from non-canonical system
  Python with a different Pydantic patch version. The evidence record is corrected;
  one final report-only re-gate is required for this changed record.

## Historical ResumeStateHint

Resume by reading `10-intent.md`, this checkpoint, current Git status, and the exact
current connector/mapper/policy/API/UI files. Do not resume from historical reports.
Do not retry Shell. Portal evidence proves ID `143878` is exact Garden, but continuation
still requires the original uncertain ledger entry or explicit authority to replace the
current no-recreation/no-manual-substitution boundary. A newly constructed ledger is
not the original checkpoint.

## Historical DriftCheckDraft

- Original intent: aligned.
- Compatibility boundary: aligned; no fallback or new owner introduced.
- Retirement boundary: local Mock remains isolated-test compatible but is not permitted
  in the configured demonstration path.
- Evidence status: implementation, focused and broad continuation regressions,
  governance/security, contract, physical-Mongo, build, and 14/14 isolated browser
  evidence are current. The complete backend suite exits zero over a separately
  collected 1,392-test inventory. External lifecycle evidence now records the explicit
  uncertain-Shell/no-replay hard stop below; the subsequent fresh independent gate
  remains `needs-verification` for the changed candidate.
- Decision: retain the user-authorized Garden-only Partnership/segment values on that
  case; do not generalize them, invent another value, or replay Shell.
- First-gate remediation: historical terminal v1 records omit the v2 early-Search node
  and retain Search under the target sequence; v2 records retain early Search. The
  frontend continues to render the exact backend-provided order for both versions.
- First re-gate remediation: when Search is the current automation stage and no
  checkpoint/transport attempt is retained yet, its displayed state now comes from the
  authoritative automation stage owner (`IN_PROGRESS`, `REVIEW_REQUIRED`, `BLOCKED`,
  or `FAILED`) rather than the default `NOT_ATTEMPTED` projection.
- Final pre-review adversarial correction: a no-match Search never displays an ID later
  created by Shell. The Search node carries a retained ID only for an exact-match
  checkpoint; later-created IDs stay on the target operation path.
- Final re-gate remediation: checkpoint-absent Search now derives status, safe result,
  timestamp, and blocker from the same automation/CLM owners. Active/review/blocked/
  failed Search can no longer pair a real state with `Search not reached` or discard an
  available Search-stage timestamp.
- Historical pre-selection evidence, superseded by the final authorized acceptance: a
  same-entity SIM LIM probe found shareholder counts
  but no provider-backed entity profile/address or compatible capital denominator, so
  no ownership percentages were derived. A fresh configured application-service Search
  for the official-Mock Garden SG identity reached real XPI and returned `NO_MATCH / 0`.
  That earlier run stopped before ledger reservation and before Shell because its then-
  unresolved business fields had no authority. It is not the current execution state.
- Final authorized acceptance supersedes that pre-selection stop. Garden-only KYC and
  segment values were bound as `USER_AUTHORIZED_POC`; corrected preflight passed and a
  fresh real Search returned `NO_MATCH`. The ledger then attempted exactly one Shell,
  whose outcome was uncertain. No replay was sent. Read-only Search now finds one
  `GARDEN BUSINESS` candidate, ID `143878`; the API response omits UEN/country/address.
  The later authenticated portal continuation proves the exact UEN/Singapore identity
  and DSD linkage, but the original in-memory ledger entry had already been destroyed
  on process exit. Policy and Amend were not sent. This is the task's explicit
  uncertain-mutation/no-replay/no-recreation hard stop.
- The post-mutation independent gate returned `FAIL`. Its two local findings are now
  remediated: the reconciliation records the one uncertain Shell and subsequent
  read-only recovery evidence, and legacy cases without a GoldTier target policy are
  projected non-editable with regression coverage. Focused verification passes. A
  fresh re-gate closed both, then found QG-PM-RQ-01: older active checkpoint/reflection
  text still described the superseded pre-Shell state. Those active sections now state
  the uncertain attempt and recovery boundary consistently. The external no-replay
  blocker remains, and one final fresh independent re-gate is required.

## Current local-continuation checkpoint — 2026-09-28

- Official ACRA API Marketplace Mock smoke is complete and read-only: Garden entity
  basic information returned HTTP 200 with matching identity; Garden shareholders
  returned a valid empty result; SIM LIM returned four shareholder observations; the
  separate capital sample supplies no same-entity denominator. No ownership percentage
  was derived and no local Mock fallback occurred.
- The primary case workspace now renders the exact backend `processing_pipeline` near
  the top with explicit accessible status/progress semantics. The retained create
  response is published immediately, and the existing polling owner remains active
  during retained intake. The detailed technical inspector stays collapsed.
- Registry presentation now distinguishes expected missing evidence, provider
  unavailability/timeouts, malformed responses, and successful empty operations.
  `REGISTRY_EXPECTED_DATA_MISSING` is presented as `Registry data incomplete`.
- `scripts/dev_preflight.py` diagnoses memory/Mongo and ACRA composition using only
  sanitized presence/reachability facts. Focused backend tests, full frontend tests,
  frontend typecheck/build, and all 16 isolated browser lifecycles pass.
- The first independent local-continuation Quality Gate returned `PASS WITH MINOR
  FIXES` for QG-LC-01 only: three legacy visible projections still imposed a fixed
  five-stage order. The rail and completed table now render the exact backend
  `processing_pipeline`; the list projection no longer invents an `N of 5` position.
  Focused v1/v2, missing-pipeline, full frontend, build, and browser regressions pass.
  The remediated candidate requires a fresh independent re-gate before exact PASS.
- Zero GoldTier calls have been made in this continuation.
