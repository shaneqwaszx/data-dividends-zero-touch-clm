# PR81 V4 diagnostic-only boundary
Owner authorization: attachment 2d31071c-a460-42ea-8fe9-b370354a7483.
Worktree: blocker-resolution-idp-ux/data-dividends-zero-touch-clm.
Branch feat/blocker-resolution-idp-ux-optimization; HEAD dd8c36c8a911f4b5f3b80e7441d049f1aa976599; cached main/base e799d74063678bb0eccbea445d5ab3c8628dd2c0.
CI_TOOLING. Runtime PowerShell 7.6.5 x64 and Python 3.12.10; ordinary medium-integrity token. Sandbox access approval does not elevate Windows. No ports/database reserved or needed. Privileged capture remains unexecuted.
Decision: code-change, task-owned diagnostic helpers only. The existing V3 controller/native wrapper own the missing state; documentation cannot recover it. Reuse those owners in a separate V4 copy; no application architecture/owner change. No product repair is justified; historical abort remains UNKNOWN.
1. Preserve explicit prior manifests and source25, exact V3 bundle.
2. Add numeric/Boolean/null stages, returned limits and comparisons, watchdog observations, native wrapper progress and exception HRESULT. Keep all capture decisions, provider/filter/security/cleanup/deadlines unchanged.
3. Exercise shared V4 operations with synthetic failure injection; never call Start/Enable/Stop ETW in tests.
4. Freeze bundle, schema, stage table, SOP and receipts; independent reviewer writes only its assigned report.
5. Final preservation check and handoff; stop before capture. No commit/publication.
Diagnostic logging is best-effort, bounded, nonthrowing and never an input to capture authorization. A write failure is separately numeric, cannot replace original failure or bypass cleanup. No unrestricted exception text, raw buffers/pointers, host identity or HTTP content in diagnostics. null means UNKNOWN.
Unchanged runner and sanitizer are byte-for-byte copied. The fixed profile and event schema are reused. V3 and historical FAIL records retained for evidence, never executed again by this task.
Required evidence: synthetic query/each bound/watchdog/enable stages/assignment/abort/cleanup/write failure; existing sanitizer adversaries; script/schema/layout/bundle and source bindings; Ruff copied Python, secret scanner/tests, project-state/architecture checks and explicit untracked whitespace.
No full business/backend/frontend/lifecycle/Mongo/publication gate: those owners are untouched and fixture execution is explicitly forbidden.
