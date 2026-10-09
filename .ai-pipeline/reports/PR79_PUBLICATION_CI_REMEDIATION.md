# PR 79 publication CI remediation: document-review preparation

Date: 2026-10-09 (Singapore). Scope: the owner's bounded selector-10 publication remediation; no next product phase or Claude adaptation.

## Identity and authority

Repository: shaneqwaszx/data-dividends-zero-touch-clm. Worktree: C:/Users/shane/.codex-clean2/worktrees/performance-computational-optimization/data-dividends-zero-touch-clm. Branch: feat/performance-computational-throughput-optimization. Frozen published diagnosis HEAD: 2bba565d9eadf816bffda5657c7291d50d8b888f; tree: fffb9b59d24c29a3e3fb5b12f6e240ab917ce181. BASE, fetched main and merge-base at diagnosis: 198341b059ebf500252ce93d72eb099d2585c60b. Index, tracked and nonignored untracked state were clean before diagnosis. The detached baseline-control worktree is at exactly BASE and remains retained. The unrelated default checkout and other worktrees were preserved.

The owner's remediation assignment requires a fresh independent PASS before commit/publication, a clean committed canonical pre-PR gate, a normal push to existing PR [79](https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/pull/79), and all seven lanes green in both new push and PR runs. This implementation report supplies no independent verdict or merge authority. Final committed/remote identities and CI receipts must be returned separately after publication; this report is not retrospectively rewritten to claim future results.

## Preserved remote and historical evidence

Original push [37863251402](https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/actions/runs/37863251402) and PR [37863275749](https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/actions/runs/37863275749), attempt 1, failed only E2E. Both passed backend, frontend, local-ocr, phase12-mongo, security and demo-lifecycle-windows. Both E2E lanes passed nine selectors, killed selector 10 at its unchanged 60-second individual lifecycle deadline (approximately 66.38/66.44 seconds including shutdown), and left 62 undispatched. No assertion traceback was emitted. Push checkout was 2bba565d9eadf816bffda5657c7291d50d8b888f; PR checkout was merge preview 92530e49691069de1d9d35b0a07797f6aa312020; both trees were fffb9b59d24c29a3e3fb5b12f6e240ab917ce181. Neither old run was manually rerun.

The original PERFORMANCE_OPTIMIZATION_QUALITY_GATE.md remains byte-identical. Its earlier selector-10 and held-response-52 timeout causes remain historically unlocalized. Its Garden-53 failure was an assertion (one document expected, zero observed), despite the owner's chronology shorthand calling it a timeout. Its focused passes and final local 72 PASS remain evidence of those earlier revisions/windows, not proof that every historical timeout was fixed here.

## Matched reproduction and causal localization

Windows primary reproduction used the exact original selector and product bytes, the feature worktree's Python 3.12.10 environment, Node 22.23.3, npm 10.9.9 and Playwright 1.56.1; same host/dependencies, sequential task ports 28801..28805/42801..42805, diagnostics, normal Mock/memory composition and 60-second lifecycle. The baseline server imported its own source root, not the default checkout. A node_modules junction supplied identical frontend dependencies without modifying baseline tracked files.

Playwright grep includes its fully qualified title. The owner's literal ^title$ selected zero tests; that discovery probe is excluded. The verified expression (^| )current document review progresses authoritatively and keeps superseded history read-only$ selects exactly one test.

| Unmodified lane | Attempt 1 | Attempt 2 | Attempt 3 | Attempt 4 | Attempt 5 |
| --- | --- | --- | --- | --- | --- |
| Candidate | FAIL 66.375s | PASS 16.250s | PASS 16.157s | PASS 16.453s | PASS 16.406s |
| Exact baseline | PASS 17.265s | PASS 16.204s | PASS 16.203s | PASS 16.047s | PASS 16.422s |

This 4/5 versus 5/5 comparison alone does not identify an optimization regression. Safe descendant-process observations contain role/PID/state only; no arguments, environment or payloads. The failed candidate's service, frontend and Playwright were alive near the deadline; native service work had completed. Backend intake scheduling uses the existing AnyIO worker owner and case RLock; the trace does not establish pool starvation or a lock defect. Mongo-only read/traversal changes are not composed in this memory lane.

Temporary observation-only milestones added no sleeps, retry, await, acceptance change or request ordering. The first observed timeout reached authoritative review POST/GET, REVIEWED and 4/4 rendering, then replacement focus/setInputFiles returned before target confirmation stalled. Existing upload/proxy diagnostics cover initial intake only; their silence cannot establish that replacement was undispatched. A temporary disabled-control/admission hypothesis was not established and was retired. CaseDetail.tsx and DocumentEvidencePanel.tsx were restored to exact original bytes.

A later synchronous requestfailed/intake-dispatch probe produced four passes and one 26.656-second failure: the initial browser upload failed with normalized net::ERR_ABORTED and no /intake/complete dispatch. Every passing probe consumed initial upload 201 and dispatched intake completion. App.tsx's current intake operation awaits intakeZeroTouchDocument before completeZeroTouchIntake; hard navigation invalidates/abandons that browser operation. A document stored and readable by a separate GET is insufficient evidence that the browser consumed its upload response and completed the handoff.

For causal falsification, separate task-owned source exports of exact baseline and candidate held only the synthetic initial HTTP upload response until after the original document-count-based hard navigation. This is an intentional response-barrier experiment, not observation-only evidence. Original assertions and lifecycle remained. Both arms aborted initial upload, dispatched no intake completion, reached reviewed rendering/replacement selection, then timed out awaiting target readiness: baseline 66.531s, candidate 66.563s. Thus the missing test preparation dependency is reproducible without the performance optimizations. The exact remote timeouts have no equivalent browser-cancellation trace, so this local causal result explains a compatible failure class without claiming direct observation of every old remote/historical cause. No local Linux execution is claimed; prepared unused Docker/source-export evidence is retained.

## Bounded correction and invariants

Only apps/frontend/e2e/authenticated-zero-touch.e2e.ts changes: 15 additive lines in selector 10. Register initial POST upload/completion response waits before Create; require upload 201 and completion 200/WAITING_FOR_REVIEW before the existing document-count poll and hard navigation. Require the replacement input enabled and current-case replacement POST 200 before target confirmation. These are positive synchronization/assertion requirements; no synthetic extra POST or retry is introduced.

Removing the recorded additions reconstructs the entire original test file byte-for-byte (original SHA256 ac308eb20acd3e2cc92846d9bec01e7d7cbe308939cac201a6c36b234e5140cd). Corrected raw file SHA256: e3cb00424ad2bc9d80fbbc5499fbd37f875af1f6af483b550bbe25ea0b29e7f2. All original assertions, awaits, review/double-click/supersession/currentness/no-replay checks, selector order/tags, 60-second execution, 120-second cleanup and discovery/derived-suite budgets remain unchanged. Temporary observation code was removed. The only additional tracked artifacts are this bounded report and the assigned fresh independent gate report.

This remediation changes test synchronization only. API/request-response/shared types, schema, connectors, product configuration/dependencies, business rules, mappings, auth/security, architecture, provider classifications and product runtime behavior do not change. The original feature's independently accepted in-lock reauthorization, existing-pool scheduling and Mongo work reductions remain disclosed in the original report; they are not undone or newly extended here. Real-user cancellation semantics, backend authority, document/reconciliation ownership and ledger-owned GoldTier no-replay remain intact.

## Current-content verification

| Check | Observed result |
| --- | --- |
| Corrected exact selector, five consecutive 60-second lifecycles | PASS: 15.734 /15.516 /15.265 /15.735 /15.313s |
| Review-ready/current-review/wrong-UEN resume/ambiguous replacement/missing-field replacement neighbors | All five PASS: 11.578 /15.563 /12.359 /16.093 /16.125s |
| Backend performance intake-concurrency/read-ownership/strict-traversal focus | 32 passed |
| Launcher and performance-method root units | 47 passed |
| Contract units | 44 passed |
| Frontend tests/typecheck/build | 560 tests in 47 files PASS; typecheck/build PASS |
| Six current governance/security scripts | Each PASS, including secret scan |
| Canonical complete isolated E2E | 72/72 PASS; canonical elapsed 1074.109s (command wall 1074.265s); slowest 57.390s; execution60/cleanup120/discovery60 unchanged |

Exact commands, logs and receipts are retained under .runtime/performance-optimization/pr79-remediation/checks, windows-remediated and neighbors. Tests use the worktree venv and safe test composition, not the system Python editable checkout. No new tests or broader product refactors are added. Existing bundle warning and six dependency audit vulnerabilities are unchanged and not claimed remediated.

The first corrected-content full-suite attempt passed 52, then Garden 53 returned upload 503 instead of required 201 (11.407s lifecycle); 19 later selectors were undispatched. The shell could not discover Tesseract, though C:/Program Files/Tesseract-OCR/tesseract.exe exists. TesseractOcrAdapter explicitly fails unavailable discovery; the original final verification used an OCR child PATH and CI explicitly installs Tesseract. This was a missing local runtime prerequisite, not a selector-10 fix or an assertion/deadline change. A first focused OCR probe omitted the offline Garden fixture mode and failed the stage assertion; it is excluded from matched regression evidence. With both the verified Tesseract v5.4.0.20240606 child PATH and canonical garden-existing-customer composition, unchanged Garden passed in 15.000s. The complete suite then passed 72 with that prerequisite, including selector10 15.063s, held52 19.485s and Garden53 15.031s, keeping failed runs preserved. A separate direct adapter probe confirmed OCR_RUNTIME_UNAVAILABLE without starting a native child or reading a document.

Full-suite generated screenshots are retained under ignored evidence before restoring only the eight known tracked task-generated PNG paths to their saved exact HEAD bytes. The existing task-owned mongo:7 container is loopback-only on 27185 with no host bind mounts; canonical classification tests create guarded allowlisted disposable clm_p16 databases. Shared clm_poc is never used. No private .env, real provider or confidential artifact is accessed. Network guards and no-external-call assertions remain; fake Sandbox transport is offline evidence, not Live/Sandbox interoperability.

## Performance provenance and publication boundary

All 40 original independent-review manifest path hashes and the original gate report remain unchanged. No product performance code or measurement method changed; affected paired remeasurement is not applicable. The original validator median -15.78%, physical case-read median -11.42%, and five-case intake makespan -75.80% retain only their original source-bound local/synthetic scopes, samples and limitations. No new speed, capacity, production or Linux claim is made from these browser runs.

Fresh independent review, clean committed pre-PR procedure, latest-main check and both fresh seven-lane CI runs remain publication dependencies. No remediation commit/push or merge has occurred at this report's preparation point. Human owner retains merge authority; all worktrees, branches and evidence remain retained. Current full verification is complete. Next authorized action is the assigned independent re-quality gate, not another product phase.
