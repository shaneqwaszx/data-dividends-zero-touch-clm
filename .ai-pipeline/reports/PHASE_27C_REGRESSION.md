# Phase27C final proportional regression

Date:2026-10-05. Implementer execution, not independent acceptance.
Branch:`feat/phase27-final-delivery-closeout`; BASE_SHA/source HEAD/observed local
origin/main:`4ee8819d7404d6442e064fd60dcee03ccc84cf11` (PR70).
Worktree:`C:/Users/shane/.codex-clean2/worktrees/phase27-final-delivery-closeout/data-dividends-zero-touch-clm`.
Fresh [BarrierB exact PASS](PHASE_27B_QUALITY_GATE.md), P0/P1/P2/P3=0/0/0/0,
released27C. Its frozen18-path manifest SHA256 is
34ec477546f89cc45e42a21a974a8b95592d1cf80806f68ee47a73d7eef47d02.
No product/test/config change follows it. Final prose receipts are separately frozen
for the final independent gate; HEAD alone is not the tested uncommitted candidate.

## Scope and exact product identity

Actual classes DOCS_ONLY/FRONTEND_UI. Minimal product delta: CaseDetail supplies its
existing upload callback only for backend-declared OWNERSHIP_UPLOAD; body min-width
320px ->0; three focused action true/false/absent regression cases. No API/type,
schema, connector, config, business rule, mapping, auth/security, cache ownership,
architecture owner/dependency or provider classification changed. Backend rules
remain authoritative. Product1/2 remediation rounds; two P2 defects visibly retested.

| Product path | Normalized Git blob / raw SHA256 |
|---|---|
| apps/frontend/src/pages/CaseDetail.tsx | c4c9fe57b1abe89489b361b04aca8611c0ba59a2 /4de94f5864f7234d3fa8be7545ffb08696bd6727c0f761ebc49c46d588198b63 |
| apps/frontend/src/styles.css |14177d3cf617c9bffceb5dac21479a9925593797 /f52980276cbfac049b84c38bb22b1cb252172b719d5e787c666a38cc3309f960 |
| apps/frontend/src/EvidenceWorkbenchIsolation.test.tsx |3974fc72e892c405be56d4a9214a0a62d7446173 /3f03f4651530f06c58a1626f10960aaa20e4ecfa9790ce6716a030062f6e4c00 |

These match the independently tested27A product and frozen27B bytes. Backend remains
baseline PR70. Full frontend is justified by shared body layout/all-role rendering;
full backend is not required for a frontend-only product delta. Focused backend
covers affected projection/intake/current binding and stop/no-replay owner contracts.
Physical Mongo/OCR are not triggered by this delta, not substitute passed mocks.

## Fresh executed results

All Python commands use the existing pinned `.venv` runtime, `-B`, worktree source,
normal configured pytest/unittest guards. No dependency or test/guard/deadline edit.
Runtime receipts/logs are ignored `.runtime/phase27/final-*.json/.log`.

| Check | Exact command / selection | Actual result |
|---|---|---|
| Focused backend | apps/backend: python -B -m pytest -o addopts='' -p no:cacheprovider --basetemp task-owned final-pytest -q tests/test_zero_touch_orchestration.py tests/test_s2_ownership_intelligence.py tests/test_manual_ownership_evidence.py tests/test_s1_pipeline_projection.py tests/test_s3_submission_status.py |135 passed,0 skips,1 existing Starlette/httpx deprecation warning;276.62s pytest;exit0 |
| Full frontend | apps/frontend: npm.cmd test -- --cache=false |505 passed/41files;exit0; existing React SSR/act warnings |
| Ruff | apps/backend: python -B -m ruff check . |All checks passed;exit0 |
| Strict mypy | apps/backend: python -B -m mypy app --cache-dir task-owned ignored path |No issues in124source files; strict=true configured;exit0 |
| Dependency integrity | python -B -m pip check |No broken requirements;exit0 |
| TypeScript | npm.cmd run typecheck |PASS;exit0 |
| Frontend build | npm.cmd run build |PASS;128modules;544.50kB JS,150.97kB gzip;existing >500kB advisory;exit0 |
| Contracts | apps/backend: python -B -m unittest discover -s ../../tests/contract -p test_*.py |44 passed;exit0; existing Starlette/httpx deprecation warning |
| Governance/security tests | python -B -m unittest tests.test_dev_context tests.test_check_project_state tests.test_check_architecture tests.test_check_policy_authority tests.test_check_external_provider_readiness tests.test_check_secrets tests.test_validate_external_provider_evidence tests.test_validate_goldtier_examples tests.test_phase_07_delivery_assets |124 passed;exit0 |
| Six configured scanners | check_project_state / check_architecture / check_policy_authority / check_external_provider_readiness / check_tooling_config / check_secrets |Each captured exit0/PASS |
| Guarded actual browser/HTTP | scripts/run_e2e.py --backend-port 8875 --frontend-port 4273 --garden-protocol --grep 'S2 document proposals require' --timeout-seconds 120 |1 passed;exit0; immutable proposal/source binding and existing upload review |
| Guarded actual browser/HTTP | Same owned ports/harness, --grep 'Phase24C policy approval and accessible layout 320' --timeout-seconds 120 |1 passed;exit0; policy/role narrow layout |
| Physical Mongo | No persistence/schema/Mongo-composition/runtime compatibility delta |NOT_RUN/not triggered; no DB connection |
| Actual OCR runtime | No OCR/runtime/media processing delta; Windows Tesseract absent |NOT_RUN/not triggered; safe absence UAT observation retained |
| Full backend | No changed backend owner/product rule |NOT_RUN/not justified; fresh135 affected owner plus prior301 bounded pre-UAT distinct |

The two browser runs use real owned backend/frontend/Chromium and HTTP, offline
Mock/LOCAL/explicit synthetic XPI where configured, generated ephemeral test identities
and unchanged network guards. Each fresh lifecycle stopped only owned processes.
Listener check: no5173/8000/8875/4273 at session end. They support regression, never UAT PASS.

## Harness failure and recovery

All three frontend child commands returned exit0 directly. After build, the ignored
runner failed while printing Vite's Unicode tick under Windows cp1252; its return1
is a TEST HARNESS console failure, not a passing wrapper or failed build. A first
readback probe repeated the same console issue. Explicit UTF-8 stdout/stderr and
ASCII-safe readback fixed the ignored runner. Complete saved test/type/build logs
were inspected:505/41, typecheck success,128module build and the advisory. Child
exit/duration receipts were recovered from directly captured tool results, annotated
as recovered; no successful suite was rerun or invented to hide the wrapper failure.
No tracked product/config/test correction resulted. Initial sandbox-only process
metadata query was unavailable; narrowly authorized owned-process metadata succeeded;
process then exited normally. This diagnostic affects no test verdict.

## UAT, security and acceptance boundary

AGENT_EXECUTED_UAT:21 rows assessed,16 PASS/0 FAIL/5 NOT_RUN; completed agent16,
human0. Actual normal5173 UI evidence and two product visible retests remain in
[results](../../docs/demo/PHASE_27_AGENT_UAT_RESULTS.md); OCR/Garden/numeric counter/
F-U fixture prerequisites explicitly unavailable. No automated or historical evidence
becomes UAT PASS. Safe source status, target IDs and dimensions only; no passwords,
hashes, .env, DB URI, raw provider/document body or private exception details tracked.
Phase27 external ACRA0/GoldTier0; original clm_poc NOT_ACCESSED/NOT_MUTATED.

Proportional27C required checks PASS on exact product bytes. Complete final diff,
all task-owned new Markdown UTF-8/whitespace/local links and six scanner readback
accompany final freeze. Fresh final independent SolHigh gate still required before
local commits. Documentation BarrierB rounds0/2; final remediation0/1 at this checkpoint.
No commit/push/PR/merge/new phase has occurred.
