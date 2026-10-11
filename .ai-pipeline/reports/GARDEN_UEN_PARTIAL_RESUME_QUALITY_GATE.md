# Garden UEN PARTIAL resume - independent Quality Gate

## Executive Result

**PASS. P0=0, P1=0, P2=0. No required fix remains in this bounded hotfix.**
Fresh independent hygiene re-gate retains exact PASS after the terminal blank-line
correction described below. The current worktree and staged identities are separately
recorded; the original verdict's frozen digest is superseded.
Independent source inspection, focused execution, failure injection, authenticated
browser journeys and physical Mongo restart checks verify the assigned Garden recovery
criteria. This is acceptance of the frozen candidate below, not a completed publication
gate, real external UAT, or acceptance of an unrelated sponsor-demo expansion.

## Reviewed identity and authority

Review date: 2026-10-11. Reviewer is independent of implementation and made no
implementation, test, configuration, ordinary documentation or Git mutation.

| Identity | Verified value |
|---|---|
| Worktree | `C:/Users/shane/Desktop/FYP/data-dividends-zero-touch-clm/.garden-hotfix` |
| Branch | `fix/garden-uen-partial-resume` |
| BASE_SHA / HEAD / observed origin/main | `40c530dde5edc0c714beae764fc760c741a5fdbf` |
| Reviewed state | Intentionally uncommitted candidate; 18 task-owned paths staged before report refresh |
| Frozen paths | 15, individually checked for raw-byte size and SHA256 |
| Reviewed worktree content SHA256 | `c951c08a93c0d98024c1184e76fd955d05528056a9d313f493dc5d19d1728880` |
| Reviewed staged 15-path content SHA256 | `8a17c00729060c8def09a05f5da6c972c21e207c23ba74e469c4d44015cea949` |
| Manifest | `GARDEN_UEN_PARTIAL_RESUME_MANIFEST.json` in this report directory |

Content identity is SHA256 of the manifest's path-sorted entries serialized with
`json.dumps(entries, sort_keys=True, separators=(',', ':'))`, without a final newline.
All entries and that digest matched on entry to the final 15-path scope and again at
verdict. An initial 12-path scope was superseded before verdict by the bounded test
inventory support correction; production bytes remained identical. The new support
diff and all affected harness tests were independently reviewed and executed.

The complete frozen path set is:

- `.ai-pipeline/001_planner/GARDEN_UEN_PARTIAL_RESUME_PLAN.md`
- `.github/workflows/ci.yml`
- `apps/backend/app/services/clm_orchestration.py`
- `apps/backend/app/services/onboarding.py`
- `apps/backend/tests/test_garden_uen_partial_resume.py`
- `apps/backend/tests/test_garden_uen_partial_resume_real_mongo.py`
- `apps/frontend/e2e/garden-uen-partial-resume.e2e.ts`
- `apps/frontend/src/pages/CaseDetail.tsx`
- `apps/frontend/src/pages/IdentityCorrectionForm.test.tsx`
- `apps/frontend/src/pages/IdentityCorrectionForm.tsx`
- `docs/integration/GARDEN_UEN_PARTIAL_RESUME.md`
- `scripts/e2e_backend_server.py`
- `scripts/run_physical_mongo_tests.py`
- `scripts/slice_b_registry_fixture.py`
- `tests/test_run_e2e.py`

The manifest, this report and the implementation receipt are explicitly excluded from
that content digest. Current source revision, tested production content and reviewed
content are distinguished; a later implementation change requires a fresh gate.
The staged digest uses the same algorithm over actual `git show :path` blob bytes.
Seven staged blobs differ from worktree bytes solely by standard CRLF/LF normalization;
normalized byte equality was independently proved for every frozen path. No non-newline
content changed at staging.

Authority read: AGENTS, canonical workflow/context/architecture/state, task planner,
FYP gate skill/template and reviewer/security roles, owning source/tests, ACRA Mock and
canonical mapping contracts, GoldTier baseline/current existing-customer family note,
current decisions/open questions, and relevant prior blocker/sponsor-demo gate context.
`dev_context.py` covered BACKEND_DOMAIN, BACKEND_API, FRONTEND_UI and CI_TOOLING.
Security and regression skill checklists informed this review. Prior gate results are
context only and do not supply this verdict.

## Acceptance Checklist

| Assigned criterion | Result and direct evidence |
|---|---|
| Actual wrong Garden UEN to corrected `11111999A` on the same case | PASS: strict offline Marketplace Mock partnership decoder and ordinary XPI name-only candidate exercised through real HTTP in both browser choices and focused API tests. |
| Enter another UEN / Verify UEN and resume, and Use entered UEN | PASS: both browser journeys execute the actual controls; entered choice uses the currently retained corrected identity. Original/current/document labels remain distinct. |
| Retain original document and provenance | PASS: API, browser and Mongo checks preserve document ID, creation identity, original extraction and provenance; recomputation does not replace the document. |
| Truthful official-Mock PARTIAL evidence | PASS: COMPLETE profile/officers, UNSUPPORTED ownership/relationships, empty official ownership collections and absent COMPLETE cache binding remain unchanged. No fabricated percentage or completeness upgrade. |
| Superseded blockers remain history; next genuine action/blocker is current | PASS: obsolete ACRA_ENTITY_NOT_FOUND becomes CANCELLED history. Incomplete Search retains GT_SEARCH_IDENTITY_REVIEW_REQUIRED plus provider MATCH_FOUND and the existing customer-confirmation action; no-match reaches readiness. Independent Search503 injection retains a FAILED Search checkpoint at GOLDTIER_SEARCH. |
| No implicit target dispatch or replay | PASS: Search-only call counters and browser network guard show zero Shell/Policy/Amend, no dispatch confirmation and no COMPLETED result. Repeated stale requests and GET/reload cause no further provider work. |
| Invalid, stale, unauthorized, wrong-choice and frozen requests remain safe | PASS: focused Garden/identity tests cover invalid UEN, mismatched entered choice, stale versions/document bindings, history limit and completed freeze; four revoked/cross-team locked-reauthorization tests pass. Guards execute before the changed acquisition branch. |
| Memory/Mongo boundaries and reload | PASS: 12 Garden combinations exercise memory/Mongo envelope adapters and three choices with Search review/no-match; two real-driver Mongo tests verify corrected-state restart, stale rejection, no replay and disposable-database cleanup. Browser reload preserves current summary. |
| Affected verification and hygiene | PASS: independent focused/browser/physical/harness/Ruff/security/governance checks, supplied completed broad checks, complete diff/new-file inspection and all frozen-file whitespace checks. |

## Contract and Integration Findings

No required contract finding. The fix uses already verified retained registry evidence
through the existing acquisition/canonical-validation owner after Search review or
failure. It does not refetch during rebind, change PARTIAL semantics, infer official
ownership, switch XPI to EDS, or confirm a name-only target candidate automatically.
The CLM checkpoint now uses the existing typed identity-review blocker code while
preserving the provider outcome separately.

The wrong-UEN absence is a fictional allowlisted offline protocol fixture, not a new
claim about authoritative ACRA not-found schemas. Existing official Mock, LOCAL
supplement, and XPI SANDBOX_PARTIAL classifications remain distinct. Invalid/quarantined
sponsor examples were not promoted. Broader partnership/denominator, Production,
PingFed, related-party/file-transfer, legal UBO and RFA questions remain later scope.

## Tester and Adversarial Findings

Independent execution used observed Python3.12.10 / Node22.23.3 and the task-owned
pinned runtime. These checks completed with exit0:

| Check | Exact scope/result |
|---|---|
| Focused backend | `python -m pytest -p no:cacheprovider ...test_garden_uen_partial_resume.py ...test_phase24_identity.py ...test_slice_b_registry_demo.py ...test_target_reliability_recovery_ux.py -q`: 58 collected/executed, PASS. |
| Locked authorization | `python -m pytest -p no:cacheprovider apps/backend/tests/test_phase13_auth_rbac.py -k identity_recheck_reauthorizes -q`: 4 PASS. |
| Physical Mongo | `python -m pytest -p no:cacheprovider apps/backend/tests/test_garden_uen_partial_resume_real_mongo.py -q`: 2 PASS, owned loopback19417, newly generated allowlisted p12 databases and cleanup assertions; no protected database access. |
| Actual browser/HTTP | `python scripts/run_e2e.py --sandbox-demo garden-existing-customer --grep 'Garden PARTIAL wrong UEN' --backend-port 18865 --frontend-port 14873 --timeout-seconds 60`: 2 PASS in9.4s; offline allowlists, zero external calls/target writes and no browser-policy violations. |
| Independent failure injection | Transient in-memory offline Search503 response on correction: same case corrected/PARTIAL, Search checkpoint FAILED, obsolete registry blocker cancelled, stable GET reload, zero target writes. No test/source file edited. |
| Changed harness | `python -m pytest -p no:cacheprovider -o addopts='' tests/test_run_e2e.py tests/test_run_physical_mongo_tests.py -q`: 67 PASS. |
| Static/security/governance | Touched Python Ruff `--no-cache`; `check_secrets.py`; `check_project_state.py`; `check_architecture.py`; `check_tooling_config.py`; `check_policy_authority.py`; `check_external_provider_readiness.py`: PASS. |
| Identity/hygiene | Complete tracked/staged diff and task-owned new files inspected; current `git diff --cached --check`, `git diff --check`, raw-byte manifest digest and staged/worktree content equivalence: PASS. Original trailing-space inspection omitted the EOF blank-line rule; the fresh re-gate below closes it. |

Initial sandbox physical attempts failed before database mutation with WinError10013;
ordinary PDF-worker runs did not progress and were interrupted. Approved runtime/socket
execution then passed. These attempts are infrastructure observations, not product
defects or passing evidence. A reviewer probe initially queried a deliberately private
case field; the corrected public CLM-checkpoint probe passed.

Completed broader evidence was executed by the implementer and inspected in the
excluded implementation receipt; it is not mislabelled as independently rerun:

- Full backend: `../../.venv/Scripts/python.exe -m pytest` from `apps/backend`:
  **2668 passed,151 skipped,4 warnings, exit0,1246.68s**. Collection began before the new
  physical test file and later harness inventory support. Exercised production and
  production bytes match the frozen content. The only later ordinary-test byte change
  removes four terminal newline bytes, independently proved AST-identical; this run is
  not relabelled as a new execution after that hygiene correction. The new physical2
  and harness67 have separate fresh executions. The151 skipped tests are not
  passing/executed evidence.
- Full frontend: `npm test -- --reporter=dot`: **583 passed/50 files, exit0**;
  `npm run typecheck`, `npm run build`, `npm ls --all`: exit0.
- Backend Ruff, configured mypy `app` (127 source files), `pip check`: PASS.
  Contract unittest44, scanner unittest8 and delivery asset unittest4: PASS.

Existing Starlette TestClient deprecation, deliberate malformed-Pydantic fixture
warnings, React act/SSR warnings and unchanged installed npm advisory are not introduced
by this patch. No skipped OCR/physical lane is converted to a pass. Real external UAT and
the full unrelated browser campaign were not executed or claimed by this narrow gate.

## Code and Architecture Review

No required code/architecture finding. The five-line Onboarding delta restores the
normal retained-registry validation ordering; the two-line CLM delta repairs blocker
projection. ZeroTouchOrchestrator is unchanged, preserving its existing confirmation
guard and stage/exception APIs. UI changes consume current server evidence; they add
neither authorization nor a cache owner. Route creator/team reauthorization, owning
case locks, version/CAS guards, history bounds and target freezes remain intact.

Supporting browser discovery rises91 to92 with46/46 shards; only the exact count
assertion and CI comment change. Deadlines/commands are unchanged. The existing physical
runner now includes the new Garden suite. No dependency/lockfile, durable schema,
canonical owner or dependency-direction change, and no ADR requirement is introduced.

API/shared type shapes, schema, connector interfaces, configuration, business/ownership
rules, mappings, auth/security policy, architecture and provider status: **unchanged**.
Runtime correction ordering, safe blocker-code projection and UI presentation:
**changed**. Test/physical inventory support: **changed**.

## Security Review

No required security finding. Creator-only evidence authority is rechecked within the
case lock; revoked and cross-team requests fail safely before mutation. The new fixture
is offline, token/host/path/identity allowlisted and uses fictional data. Changed/new
files contain no newly disclosed protected data, raw document body or provider payload.
The repository secret scan passed; untracked task-owned additions were also manually
inspected, and publication must scan the exact staged/committed additions.
No private dotenv, sponsor credentials, external provider HTTP/write or protected
database was accessed. Generated Mongo test databases were cleaned; container lifecycle
cleanup remains the coordinator's task. No claim of volume-free resources is made.

## Required Fixes and Readiness

Required fixes: **none**. No current scope blocker remains. Later sponsor dependencies
and single-process persistence limitations are unchanged.

This exact candidate is eligible for the separately authorized publication workflow:
preserve reviewed bytes, stage only task-owned reviewed content/evidence, commit, fetch
and assess main, complete the clean committed `pre_pr_check.py` and required checklist,
then publish only if those conditions pass. Pre-PR PASS and PR readiness are **not yet
claimed**. Human owners merge. No next phase is assigned or authorized by this gate.
Real ACRA/GoldTier/Production readiness and real Sandbox UAT remain unchanged/unverified.

## Git Status and Reviewer Write Boundary

At the original verdict, ten tracked paths were modified and five frozen paths plus
three excluded evidence files were new, with no staging. At this fresh re-gate,
**18 explicitly task-owned paths are staged** by the coordinator; branch/base/HEAD/
origin/main remain as recorded. Report refresh creates only an unstaged report delta,
which the coordinator must explicitly restage before publication.
At final readback, the coordinator's excluded implementation receipt also has an
unstaged evidence delta; those two evidence files require scoped restaging.

The reviewer wrote **only this assigned report** in both runs and made no implementation
fix, commit, push, PR, merge, staging, branch/worktree mutation or next-phase change.
Implementation receipt changes remain excluded evidence. End-of-review path hashes,
both content identities, staged/full whitespace, secret scan and report readback were
independently verified. Publication still requires a clean committed pre-PR PASS.

## Fresh EOF Hygiene Re-gate

The coordinator's first staged whitespace check found a new blank line at EOF in
`apps/backend/tests/test_garden_uen_partial_resume.py:259`. The original review checked
trailing spaces on untracked files but missed Git's EOF blank-line rule; that original
hygiene evidence was incomplete. The coordinator removed only terminal blank lines.

Independent reconstruction proves the complete old file is exactly the new file plus
`b'\r\n\r\n'`: old size10848 / SHA256
`cbd4e52c7c6cba0aeeaa3c7849650a5afe95c734f6b7e605137c62dbc592899d`;
new size10844 / SHA256
`06ac92c8d4e8a7e9a373aeecf66dfce3230d0ef23b78a0e66c8414ee86fdaf9a`.
Replacing only that entry in the current manifest recreates the prior content digest
`81099256ca250a3610abea04188ab5fdbcb2a0ce29c4ee7ea7a38687ce944175`,
cryptographically proving all other14 frozen paths unchanged. Current manifest entries
and digest match actual files; the test's old/new Python ASTs are equal.

Fresh `git diff --cached --check`, `git diff --check` and `check_secrets.py` all pass.
Every staged frozen blob was compared with reviewed worktree bytes; seven normal
CRLF/LF-only transformations account for the separately recorded staged digest.
Staged scope is the same15 reviewed paths plus the three excluded evidence files.
No runtime, contract, assertion, fixture, provider, owner or policy content changed.
No focused Garden13, physical or browser rerun was required for this terminal whitespace
correction: their existing behavioral evidence remains explicitly attributed to its
original execution, with semantic continuity proved independently here. No test was
skipped and then reported as newly executed. Required hygiene finding: **closed**.
Fresh bounded re-gate result: **PASS**.
