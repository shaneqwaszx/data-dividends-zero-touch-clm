# Slice C C-QG-004 additional diagnostic round

Date: 2026-10-03 (Asia/Singapore).
Authority: user's explicit ONE additional C-QG-004-only round, beyond the prior 2/2 limit.
This is round 3 overall and 1/1 of the additional authorization.

The exact historical empty text/plain 500 was **not reproduced in 10 fresh instrumented address lifecycles**. Supported bounded classification: **NON_REPRODUCED**. Historical incident origin remains **UNCLASSIFIED**. No confirmed defect owner, deterministic failing-first mechanism, repair, or Slice-C PASS is claimed.

## Frozen source and scope

- Worktree: C:/Users/shane/.codex-clean2/worktrees/post-phase24-stability-provider-hardening/data-dividends-zero-touch-clm
- Branch: feat/post-phase24-stability-provider-hardening
- BASE_SHA / HEAD / observed local origin/main: 707765b1d51172c64b851c9e46e68b3c23006789.
- No fetch; no remote-main freshness claim.
- Previous and restored runtime/source candidate: 16bcc9893db74a949331de8f569560d5cb7dfc1123d74dffe499717addd4b8cf.
- Previous manifest SHA256: fe2abc3e838f484b99bb36da4a66b83ecd0181971b2ed906e0a3eea91fea0be5.
- Previous FAIL gate SHA256: 891085050fcb9fd9a2a097544a0bdc4c5cc1a0a45d434060a9deba6502fe425c.
- All 66 original frozen entries were verified before instrumentation and after byte-for-byte restoration. Original manifest and gate are preserved unchanged.
- New candidate is a separate diagnostic-report/evidence identity, not a new product fix. Its complete path/hash set is in POST_PHASE24_SLICE_C_QG004_CANDIDATE.json.
- Coordinator route assigned by user: GPT-6.1 Sol / Extra High. Reviewer requested GPT-6.1 Sol / Extra High. This session exposes no speed-setting API; 1.5x is not independently verified.
- Task classification after restoration: DOCS_ONLY. CI_TOOLING instrumentation was temporary. FRONTEND_STATE_CACHE and BACKEND_API were traced without lasting changes.

Preflight confirmed correct worktree/branch/base, empty index, clean original main checkout, matching candidate hashes and absence of old task Mongo/container/ports. No Git mutation occurred. No protected configuration or sponsor artefact was accessed.

## Exact request and ownership trace

The historical failing request is the direct Playwright API-context summary poll in apps/frontend/e2e/slice-c-recovery.e2e.ts, after document-owned address resolution, classification and target confirmation:

`GET http://127.0.0.1:5208/api/clm/zero-touch/cases/{case_id}`

The case identifier is synthetic and redacted here. This helper uses page.request.get; it does not use the React Query AbortSignal.

```text
address resolution POST (KEEP_REGISTRY)
 -> backend owning case lock + reauthorization
 -> reconciliation unit of work commits canonical/reconciliation state
 -> automation evidence/history/checkpoint save and advancement
 -> mutation returns summary; UI publishes it
 -> supporting queries cancel/invalidate
 -> document classification and target-confirmation POST
 -> direct test summary GET during completion polling
 -> Vite /api proxy -> loopback FastAPI :8038
 -> auth boundary authenticates actor and authorizes case scope
 -> active ZeroTouchOrchestrator.get
 -> automation / canonical case / CLM / target ledger / reconciliation / ownership reads
 -> pipeline projection + ZeroTouchCaseSummaryResponse.from_domain
 -> HTTP response -> proxy -> Playwright assertion
```

Owning files inspected: apps/backend/app/main.py; app/api_auth.py; services/zero_touch_orchestration.py; reconciliation.py; reconciliation_repository.py; zero_touch_repository.py; repository.py; clm_repository.py; ownership_repository.py; target_execution_repository.py; apps/frontend/src/api.ts; query owner/effect modules; pages/CaseDetail.tsx; apps/frontend/vite.config.ts; scripts/e2e_backend_server.py; scripts/run_e2e.py.

Summary GET is not one aggregate case-lock snapshot. InMemory repositories use their own locks and defensive copies. Canonical/reconciliation publication uses the process-local shared transaction boundary; later automation/ledger checkpoints are sequential. A read can therefore fall between aggregate checkpoints. Inspection and successful runs did not establish an invalid intermediate state or a projection crash. Exhaustive controlled interleaving proof was not obtained. Strict validators/decoders were not relaxed; current lifecycle uses explicit Memory mode.

Centralized frontend mutation effects cancel owned queries and publish the returned summary. Supporting document/ownership/intelligence/list/activity queries are invalidated; this effect does not independently invalidate the detail summary after publishing it. Target confirmation also cancels/publishes owned detail state. Identity/session keys and cancellation owners remain unchanged. Existing query retry defaults are unchanged; no retry was added to the direct summary helper. No recorded summary requestfailure, route disposal or abort was tied to this run's final poll. Earlier historical cancellation/navigation causality is unknown.

The guarded E2E Vite agent retains keepAlive=true and maxFreeSockets=1. Normal Vite composition is unchanged. Installed Vite's proxy error fallback can send status500, text/plain and an empty body; that shape alone does not prove which event produced the historical response. Socket reuse, backend keep-alive closure, pending FIN, ECONNRESET, proxy defect and process failure remain unproven hypotheses.

## Temporary diagnostics and removal

Only the address-only --diagnostics lifecycle was instrumented. Synthetic UUID correlation connected browser, proxy and backend milestones. Observations included method/path families, monotonic clocks, safe status/content type/byte lengths, allowlisted error classes, request/proxy/endpoint/read/projection completion, process health and socket lifecycle facts.

No body, cookie, auth header, CSRF value, token, password, Mongo URI, provider credential, document content or raw provider payload was logged/persisted. Error messages were not emitted. Diagnostic code allowed bounded class/category labels only.

Temporarily edited paths:
- apps/frontend/e2e/slice-c-recovery.e2e.ts
- apps/frontend/vite.config.ts
- scripts/e2e_backend_server.py

An ignored task-owned tmp/slice_c_qg004/backend_trace.py supplied gated ASGI/service/repository tracing. A safe wrapper retained only parsed E2E_DIAG JSON from the existing bounded process capture and health booleans.

Runs1-5 used initial socket observations. Runs6-10 additionally captured response socket state before the end callback to avoid losing idle-age observations. This observational refinement changed no test assertion, flow, agent option, timeout or retry behavior. These are two instrumentation versions, neither a repair.

All three edited files were restored to exact preflight bytes before freeze. All original 66 entries match the preserved previous manifest. Ignored diagnostic receipts/backups remain available for independent readback and are explicitly hashed separately in the diagnostic manifest. They are task-owned local evidence, not maintained source.

Limitations:
- Existing process capture retains a bounded 64KiB tail. Early backend mutation traces were truncated, so complete correlated commit-order traces are unavailable.
- Every run's final summary GET has the full recorded browser/proxy/backend chain. This does not imply complete end-to-end traces for all earlier GETs.
- Observational logging/headers can affect timing. The run cannot exclude a rarer fault or an instrumentation-sensitive interleaving.
- The recorded patch excerpt and backend tracing module aid audit; complete snapshots of both temporary instrumentation versions were not retained.
- No trace was captured for the historical failing request. A generic controlled500 would not establish its actual mechanism.

## Fresh reproduction evidence

Command for each fresh lifecycle:

```text
python -B scripts/run_e2e.py --backend-port 8038 --frontend-port 5208 --grep "Slice C address discrepancy" --timeout-seconds 60 --diagnostics
```

Ten serial, fresh isolated lifecycles; no retry within a test. No concurrent frontend unit/build/browser lane. Each resolution and target confirmation returned200. Each final summary returned200 application/json. Both owned child processes were alive before normal cleanup. No recorded proxy error or backend outer exception. Post-cleanup task ports were absent.

| Run | PASS / seconds | Resolve ms / status | Confirm ms / status | Direct GETs | Final status / bytes | Final chain |
|---|---|---|---|---|---|---|
| 1 | PASS / 20.83 | 2213.9 / 200 | 2812.6 / 200 | 8 | 200 / 66560 | Complete |
| 2 | PASS / 18.16 | 2485.8 / 200 | 3035.7 / 200 | 9 | 200 / 66560 | Complete |
| 3 | PASS / 18.02 | 2373.5 / 200 | 2855.8 / 200 | 9 | 200 / 66559 | Complete |
| 4 | PASS / 18.16 | 2468.3 / 200 | 3068.6 / 200 | 9 | 200 / 66560 | Complete |
| 5 | PASS / 17.44 | 2226.0 / 200 | 2707.7 / 200 | 9 | 200 / 66560 | Complete |
| 6 | PASS / 17.91 | 2294.6 / 200 | 2745.7 / 200 | 9 | 200 / 66559 | Complete |
| 7 | PASS / 17.84 | 2235.4 / 200 | 2687.2 / 200 | 8 | 200 / 66561 | Complete |
| 8 | PASS / 17.73 | 2276.8 / 200 | 2825.4 / 200 | 9 | 200 / 66560 | Complete |
| 9 | PASS / 18.03 | 2382.7 / 200 | 2933.6 / 200 | 9 | 200 / 66559 | Complete |
| 10 | PASS / 18.30 | 2353.0 / 200 | 2955.6 / 200 | 9 | 200 / 66560 | Complete |

Resolution/confirmation times are browser monotonic milliseconds from that run's origin. Durations are whole lifecycle wall seconds. Direct summary-read counts total88; these are existing polling reads, not retries of a failed GET.

For the final poll in each run, the same request correlation records SUMMARY_START, VITE_PROXY_REQUEST_ACCEPTED, VITE_PROXY_UPSTREAM_COMPLETE, REQUEST_ENTERED, ENDPOINT_START, PIPELINE_BUILD_END, SUMMARY_BUILD_END, RESPONSE_COMPLETE, VITE_PROXY_RESPONSE_COMPLETE and SUMMARY_FINISH.

The historical independent matrix reported5PASS /1FAIL /16not run. Its row6 address failure remains historical evidence, not overturned by this bounded10PASS run.

## Classification and no-change decision

Decision tree H applies: the exact failure was not reproduced after the instrumented fresh runs. A-G cannot be established without a correlated failure. Historical incident origin stays UNCLASSIFIED; the supported new observation is NON_REPRODUCED in this bounded environment.

Failing-first proof: none for an actual confirmed mechanism. No confirmed mechanism exists to test/fix. No speculative source change, transport accommodation or new fallback was made. Timeout remains60s; no retry, sleep, reload, skipped address assertion, swallowed500, default summary, test reordering or assertion weakening was added.

C-QG-001/002/003 remain CLOSED as independently recorded on the unchanged16bcc candidate. No direct root-cause evidence justified reopening them. Accepted A/B manifests/gates and source paths remain byte-identical. Prior A/B and C tests remain attributed evidence, not fresh executions in this diagnostic round.

## Verification scope and next boundary

Fresh evidence: 10/10 instrumented address PASS, 0/10 historical failures reproduced; safe receipt consistency; restored66-file raw hashes; prior manifest/gate preserved; whitespace and explicit task-path hygiene checks; task process/resource absence.

Not rerun in this round: focused neighboring recovery journeys, final22-row browser matrix, backend owner/full suite, full frontend suite, physical Mongo, A/B regression suite, Ruff, configured mypy, typecheck/build, broad governance/security/provider-readiness and guide equality. The user's sequence requires narrow PASS before final re-gate. Earlier passing lanes remain revision-attributed in POST_PHASE24_SLICE_C_MINI_GATE.md; they are not relabeled fresh.

No backend product source changed in this additional round. No API/type, schema, connector, configuration, business rule, mapping, auth/security, architecture, provider status or runtime behavior change remains. No new package/lockfile/generated product artefact. No new durable architecture decision.

External call budget: ACRA0; GoldTier Sandbox0; GoldTier Production0; other0. The exact selected fixture route composes local Mock providers and explicit Memory persistence. No Mongo was started or contacted during this round.

Original checkout remains clean; task checkout intentionally retains cumulative A+B+C uncommitted work. Index empty. No commit/push/PR/merge, new phase, portal or policy-advisor action.

Independent narrow review is pending at freeze in POST_PHASE24_SLICE_C_QG004_NARROW_GATE.md. Review must distinguish a truthful NON_REPRODUCED diagnostic from proof that the actual incident is explained/closed. On narrow FAIL, STOP; no fourth remediation round or final matrix is authorized automatically. On narrow PASS only, the user's conditional final re-gate sequence applies. This report does not issue a Slice-C verdict.
