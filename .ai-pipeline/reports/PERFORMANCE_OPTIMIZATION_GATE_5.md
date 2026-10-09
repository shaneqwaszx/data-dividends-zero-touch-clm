# Gate 5 - actual browser requests and cache measurements

Frozen candidate pending exact independent review. No frontend/API product optimization retained: measured warm navigation already makes zero API requests, while cold development duplication is explained by current session/StrictMode lifecycle.

Base/origin main `198341b059ebf500252ce93d72eb099d2585c60b`; parent checkpoint `a3f4d17a920bc19fbf7f3807c1fe494453c692ee`; branch `feat/performance-computational-throughput-optimization`.
Only maintained delta is `apps/frontend/e2e/performance-browser.e2e.ts`, current method SHA256 `e8f6fda4ff88b36fd41ac25b2d60b6a9fa523b17688dded43959ffdbba4cc19b`; measured original SHA256 `1310bf487ce69024a4080a04b1b59e7aea9bfaa86eead27e3291613cf1a9dcc8`.
Product backend/frontend source trees remain exact checkpoint bytes. Raw160 interactions plus check/pilot receipts are preserved under ignored `.runtime/performance-optimization/gate5/manifest.json`.

## Protocol and scope

Guarded Chromium/Playwright1.56.1, real local HTTP through Vite7.1.11 development proxy to explicit Mock/memory backend. Authenticated desktop1440 and narrow360, each in a fresh owned lifecycle with105 canonical synthetic portfolio seeds and one UI-created native-document case. Cases page displays50 rows. Same user/session; mandatory Playwright routing disables HTTP cache;20 measured samples per kind/width/arm plus2 warmups. Cold means query cache reset by page reload; warm means Cases -> same case within that loaded session, before45s query staleness. It does not measure a fresh browser, production bundle, network capacity or real provider latency.

UI elapsed includes reload/navigation until the case displays12 stages. A fixed500ms accounting tail outside timing lets completed/cancelled fetches appear in Resource Timing. Request attempts include cancelled requests; completed HTTP responses are counted separately. decodedBodySize is payload observation, not header/wire bytes. Browser CPU/memory and React rerenders are not separately instrumented. Layout containment, 2xx completed responses, cancelled-only failures, exact resource/attempt count, local network policy and zero target-confirmation requests are asserted.

|Width/kind|Before p50/p95 ms|After p50/p95 ms|Attempts/completed/cancelled|Before/after decoded bytes p50|
|---|---:|---:|---:|---:|
|1440 cold_client_cache|731.10/918.77|716.76/891.82|14/9/5|110108/110108|
|1440 warm_navigation|278.88/295.97|281.01/297.58|0/0/0|0/0|
|360 cold_client_cache|717.40/920.31|710.16/901.66|14/9/5|110108/110108|
|360 warm_navigation|279.44/294.96|279.66/295.24|0/0/0|0/0|

All before/after request signatures equal. Warm navigation0 attempts/bytes; cold14 attempts,9 completed,5 cancelled in every sample. Two auth/me responses occur under React development StrictMode. Each case/document/ownership/intelligence/execution-profile endpoint has one cancelled attempt and one completed response; dashboard/portfolio each complete once. Source reads of main.tsx/auth.tsx/queryClient.tsx/caseQueries.ts support the lifecycle explanation: obsolete effect/session scopes are discarded; accepting a session clears/cancels incompatible queries and prefetches authorized dashboard/portfolio. Those guards are security/currentness behavior. This development-only duplication does not justify a new global session promise/cache owner or changing auth boundaries for marginal cold-page cost.

Existing bounded backend projection measurements remain approximately13ms case detail and18ms physical portfolio; physical50-row projection uses its accepted bounded query/index. This gate supplies no causal frontend speed gain: source is identical in both arms and timing differences are noise/descriptive host windows. No response field was removed, stale time increased, invalidation narrowed, polling disabled, cache scope merged or source assertion weakened.

## Verification and bounded pilot remediation

Four fresh real-HTTP browser lifecycles PASS (desktop/narrow before/after,20+2 of each kind). Full frontend560 tests in47 files PASS, typecheckPASS, buildPASS. Existing574KB minified chunk warning remains; no dependency/chunk-limit change. Full backend/product checks from Gate4 cover unchanged product bytes; complete cumulative suite remains Gate7.

Pilot1 incorrectly equated cancelled Resource Timing entries with completed-response events. Corrected measurement separately counts attempts/completions/cancellations and still requires exact attempt/resource equality and safe outcomes. Pilot2 assumed an unseeded single-row portfolio; current canonical E2E has105 seeds. Corrected to the actual50-row page and exact created-case href. Explicit test declarations give distinct isolated-suite selectors. No accepted data uses either pilot or mixed method. The frontend-test command passed; its wrapper then failed printing a Unicode checkmark on cp1252. The captured exit0/test log was retained, stdout fixed to UTF-8, and remaining typecheck/build ran successfully. No tests skipped/replaced, timeout raised or product assertion weakened.

## Review correction and measured provenance

Initial independent review FAIL identified false assets-warm metadata. Installed Playwright1.56.1 types and Chromium network manager explicitly disable HTTP cache whenever routing/interception is enabled. The guard remains mandatory. Corrected two measured-method strings only: the reload comment and assets_cache output written after all timing windows. Undoing those exact byte replacements reconstructs the preserved original1310bf... source. Timing, requests, assertions, waits, selectors and routing logic are byte-for-byte unchanged. Original before/after data remains untouched and bound to1310bf...; its assets-warm field is explicitly superseded by the correction receipt. Companion JSON separately binds corrected candidate and actually measured source. No asset-cache, production bundle or frontend speed-gain claim remains. Independent recheck is required; complete cumulative E2E will execute the corrected metadata generator.

## Flags and next action

API/type, schema, connector, configuration, business rule, mapping, auth/security, architecture, provider classifications and functional runtime unchanged. Maintained browser measurement/tooling and bounded evidence reports added only. .env/shared clm_poc/external providers untouched. No sponsor decision or Live/production/SLA claim. Independent PASS is required before the local checkpoint and Gate6 shared-application load validation.
