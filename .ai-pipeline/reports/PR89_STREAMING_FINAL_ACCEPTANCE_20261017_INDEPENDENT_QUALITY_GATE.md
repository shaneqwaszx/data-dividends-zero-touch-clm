# PR89 final acceptance recovery — independent Quality Gate

**Verdict: PASS** for the frozen corrected streaming candidate and the owner-authorized successful-diagnostic acceptance route. No required source correction or unverified current local acceptance criterion remains. This is local acceptance, with publication authorization and hosted release checks still pending.

Finalized: 2026-10-17T21:33:50+08:00 (Singapore). Reviewer: `independent_final_recovery_gate`, a fresh independent reviewer that did not implement this candidate. Source, tests, configuration and ordinary documentation remained read-only throughout this review; only this assigned ignored report and `gate/` audit receipts were written. No test, AM18, control, browser campaign or remediation was launched by this reviewer.

## Reviewed identity and authority

- Worktree: `C:/Users/shane/.codex-clean2/worktrees/pr89-streaming-resource-p2-20261017/data-dividends-zero-touch-clm`.
- Branch: `codex/pr89-streaming-resource-p2-20261017`.
- HEAD / published PR89: `2790d23dacc89ddb0039aee5878f99ff706bcc28`.
- BASE_SHA / merge base / origin/main / directly observed remote main: `12ba994b8128a4777e12fcc764bafc8f39b9292a`.
- Exact reviewed and tested raw identity: **`e91aeb84f2c12621ec630f1c820809eff581b0962c036031c7bfa9072859cdf8`**, **2,126 paths / 13 changed paths**. HEAD alone does not identify these intentionally uncommitted corrections.
- Identity method: SHA256 over compact ASCII JSON of the sorted `{path,sha256}` entries, with inner hashes over raw file bytes. `FROZEN_CONTENT.json` is the complete authoritative path/hash manifest.
- Independent initial and final audits recomputed every raw hash and the complete tracked/untracked nonignored path inventory, with no mismatches, added paths or missing paths. Index empty; tracked diff and every changed/new file whitespace-clean. `gate/initial-independent-audit.json` and `gate/final-independent-audit.json` retain the observations.

Authority is the owner brief in attachment `cb85790c-90df-4bbb-ba52-b9238b3da7b9`, AGENTS.md, the task plan, current source/tests and canonical workflow. Applied `fyp-quality-gate`, integration-security, frontend-state/cache and POC-regression review instructions. Current architecture/provider context and open sponsor authority were inspected without promoting stale historical documentation above current source.

Complete changed-path set:

- `apps/assistant/README.md`
- `apps/assistant/ai_assistant/guardrails.py`
- `apps/assistant/ai_assistant/llm.py`
- `apps/assistant/ai_assistant/main.py`
- `apps/assistant/tests/test_ai_assistant.py`
- `apps/assistant/tests/test_required_p2.py`
- `apps/assistant/tests/test_speed.py`
- `apps/assistant/tests/test_streaming_resources.py`
- `apps/assistant/tests/test_warm_up_security.py`
- `apps/frontend/e2e/assistant-streaming.e2e.ts`
- `apps/frontend/src/aiAssistant.errors.test.ts`
- `apps/frontend/src/aiAssistant.streaming.test.ts`
- `apps/frontend/src/aiAssistant.ts`

The preceding continuation FAIL and original evidence were preserved. This review re-evaluates the unchanged candidate using the newly authorized complete campaign; it does not rewrite an earlier failed run.

## Streaming, contract, security and architecture review

| Current criterion | Independent assessment |
|---|---|
| Server memory bounds | PASS. Raw SSE is bounded before decoding/framing: 64 KiB frame/line and 1 MiB cumulative bytes, including comments/empty deltas. The guard independently limits generated UTF8 text to 64 KiB, retires complete lines and retains only pending/distinct approved lines. No token-budget assumption supplies these bounds. |
| Server elapsed bounds/framing | PASS. The configured absolute deadline covers connection, writes, headers and every pending raw body read through remaining-time cancellation. Strict UTF8, fragmented multibyte input, LF/CRLF/CR, BOM and multiline data are handled. Compressed SSE is rejected before body reads. EOF cannot supply a missing complete event terminator. |
| Truthful terminal/partial/fallback | PASS. DONE/stop/length must arrive in a complete valid frame; malformed/EOF/limit/deadline paths cannot manufacture ordinary completion. Already approved partial text retains the cut-short notice; otherwise the deterministic case-data answer is used. Unknown generated advice does not enter the approved catalogue. |
| Actual server cancellation | PASS. Async model reads are cancellable; route `aclosing`, adapter response/client cleanup and shielded connection closure retain ownership. Pending-read and ASGI-disconnect tests assert provider closure without a manufactured done. Adapted existing tests preserve assertions while using the async protocol. |
| Browser success/error/finite JSON bounds | PASS. All non-2xx bodies pass through the 16 KiB reader; brief/explicit-chat success JSON through the 128 KiB reader. Limits apply before UTF8/JSON decoding, independently of Content-Length. Finite JSON/error bodies have an absolute five-second post-header deadline. NDJSON and compatibility consumption retain 128 KiB line / 2 MiB cumulative limits and strict incremental decode/event validation. No unbounded Response body-helper bypass remains in this Assistant client. |
| Browser cleanup/status/error projection | PASS. Finite-body cleanup clears timer/listener, initiates cancellation and releases the lock without awaiting a hostile cancel promise. Streaming abort/completion/error cancels/releases its reader; pre-aborted, pending-read and queued-late-callback paths are covered. HTTP status survives; only seven fixed trusted service messages or fixed local fallbacks reach error rendering. Raw diagnostics/parser text do not. |
| P1 implicit warm-up | PASS. Both brief and actual model destination require unambiguous literal loopback. Remote/ambiguous URLs cannot implicitly build/send a case prompt; warm transport disables environment proxies and redirects. Explicit questions remain a separate existing boundary. |
| R1–R4 and backend authority | PASS. Search guidance targets Existing-customer search; EOF/malformed events are owned failures; unverified operational/source-precedence/legal-UBO/Live/KYC/resend claims are rejected. Guidance consumes current backend-authorized actions and fixed templates. The Assistant only GETs the authorized backend with the actor session and creates no case/target mutation or business-rule owner. |
| Session/cache and isolation | PASS for the affected surface. Shared authenticated transport/session-generation-aware401 handling, AuthProvider remount/clearing, scoped query owners, safe404 thread clearing and panel case/unmount aborts remain unchanged. New client reads preserve AbortSignal and old-session/case callbacks cannot publish a completion after cancellation. No persistent case cache or mutation retry was added. |
| Scope/architecture/provider truth | PASS. Existing owners and dependency direction retained; no second persistence/auth/ownership/ledger owner or new provider composition. No assertion/retry/lifecycle relaxation, sponsor rule, mapping or Live claim was introduced. |

Independent inspection included all thirteen changed files, adjacent unchanged authority/session/cache owners and AM18 route/projection/confirmation/ledger boundaries. The preserved native resource evidence includes original >3 MiB error bypass RED and corrected GREEN: bounded synthetic reads/cancel/unlock, actual finite HTTP containment and actual trickle/stall TCP closure near five seconds. These are inspected prior execution receipts on the exact unchanged source, not claimed as newly rerun probes. Focused real Chromium exercises the actual unchanged panel with chunked HTTP, safe HTTP503 containment, normal/partial output and case/actor cancellation; the same selector passed again in the fresh canonical campaign.

Finite JSON's five-second deadline is post-header. Successful NDJSON has the retained server deadline plus explicit abort, not that finite-body five-second client deadline. One transport chunk can arrive before an over-budget chunk is rejected. Those are documented boundaries, not claims of socket-level byte prevention. Server nonstream transport redesign is outside this streaming correction.

## AM18 forensic decision

The one authorized targeted candidate selector `e2e/am-wave1.e2e.ts:125` passed: one actual Chromium record, 10.2 seconds native / 14.032 seconds lifecycle, original 60-second lifecycle and retries0. Independent audit found 59 request starts/statuses/ends, 18 projection enter/return pairs, zero exceptions and ten case GET200 responses. The setup confirmation and subsequent GET retained COMPLETED automation v15 / CLM v11, case event count10, FINALIZED/SUBMISSION_CONFIRMED and SEARCH/SHELL/POLICY/AMEND/READBACK. The available case event count is not an invented scalar case revision. All130 captured runtime modules independently matched current source bytes; three owned processes stopped and targeted ports were freed.

The exact production backend, AM18 and fixture/runner paths match current main after checkout normalization. This supplies source provenance, **not causal main-versus-PR89 attribution**. No matching main control was necessary on the explicitly authorized successful-diagnostic branch and none was run. No product correction or RED/GREEN claim arose in this recovery session.

**Historical AM18 GET500 root cause remains UNKNOWN/OPEN; main-versus-PR89 attribution remains UNPROVEN.** Its original missing exception/first throwing operation/state boundary cannot be reconstructed from a new passing diagnostic. Disposable observation can alter timing; its success does not explain the old failure. The original incident and FAIL/NOT_RUN records remain preserved. The owner explicitly permits a complete fresh campaign to support current acceptance in this branch, which is the basis of this PASS.

## Fresh complete canonical campaign

The coordinator executed exactly one fresh pair, sequential shard1 then shard2, through the original canonical runner with task-owned payload-free observation/reporter wrappers. Fresh discovery is 108 selectors and 137 actual Chromium records. Independent reconciliation matched exact ordered partitions, discovery multiplicity, begin/end test identities and all native terminal receipts:

| Shard | Selectors | Chromium records | Native exit | Lifecycle campaign duration |
|---|---:|---:|---:|---:|
| 1/2 | 54 PASS | 60 PASS | 0 | 670.281 seconds |
| 2/2 | 54 PASS | 77 PASS | 0 | 719.594 seconds |

The disjoint union covers every discovered selector exactly once, with no missing/duplicate test IDs, skipped selectors or retries. Original definitions/assertions, original60-second lifecycle, real Chromium and Mock target/network restrictions remain unchanged. Canonical shard2's first AM18 record independently passed at retry0 in8877ms. Task-only Tesseract exposure supplied actual OCR prerequisites without a permanent configuration change.

Independent terminal audit verified all5,944 request starts have exactly one corresponding status/end, all1,480 projection enter/return pairs match, all13,797 loaded-module hash samples match current files, and diagnostic-capture-error count is zero. No HTTP500 occurred. Eight captured HTTPExceptions correlate with409 stale target-confirmation assertions in unchanged `sponsor-demo-journeys.e2e.ts:109-110`, which also preserve unchanged target call counts. All three503s correlate with the unchanged `blocker-simulation.e2e.ts:233` native-document adverse selector: initial intake, failed retry and saved replacement/dependent-refresh failure each explicitly assert503 before their verified recovery paths. These expected adverse observations are not unexplained campaign failures.

Cleanup: **324 created/stopped owned process records match exactly**, all with terminal metadata and the expected backend/frontend/Playwright roles. **13 freshly generated allowlisted fixture databases** have exact verified cleanup receipts. The exact task-labelled fresh Mongo container was independently confirmed absent after its ownership-checked cleanup showed only system databases; no fixture remains. Independent bind checks confirmed28765/24173/27195 free. No retained database or `clm_poc` was used. `campaign-reconciliation.json`, `observation-audit.json`, `expected-exceptions.json`, `mongo-cleanup.json` and the independent final audit receipt preserve these results.

## Preserved full verification and limitations

The reviewer inspected native logs, commands, exits, provenance and exact raw identity for the already accepted lanes; these unchanged broad suites were intentionally not repeated:

| Source-bound lane | Verified recorded result |
|---|---|
| Full Assistant |229 PASS; existing deprecation warning retained |
| Full frontend |920 PASS /56 files; focused client/panel60 PASS |
| Full backend |2707 PASS /158 SKIPPED /4 existing warnings |
| Contracts |44 PASS |
| Security/governance |120 PASS; supported secret/project-state/architecture/tooling/policy/provider checks PASS |
| Types/static/build/dependencies |Frontend typecheck/build, Assistant/backend Ruff and strict mypy, dependency checks and hygiene PASS |
| Native focused Chromium |PASS; streaming selector also freshly PASS within the complete campaign |

Receipts remain in `tmp/pr89-streaming-resource-p2-20261017/continuation`. The158 opt-in physical Mongo/local-OCR skips are unexecuted, never PASS. No persistence/OCR owner change makes those full opt-in suites newly mandatory; browser fixture execution is bounded evidence, not a claim that skipped suites ran. Earlier885PASS/1timeout frontend and incomplete backend records, old canonical shard2 failure and53NOT_RUN remain historical failures/incomplete evidence. They are not retroactively relabelled.

No newly tracked/staged secret, raw sponsor artifact, confidential provider/document body or private exception detail was found in the reviewed delta. Observation is limited to safe identifiers/statuses/whitelisted state/structural frames and file hashes. The reviewer did not access.env or credentials, make external target/model calls or connect a database.

## Scope effects, remaining publication blockers and STOP

Recovery-session source effects: **none** across API/type, schema, connector, configuration, business rule, mapping, auth/security, architecture, provider status or product runtime. The retained thirteen-path candidate does change the internal model stream protocol to async, model SSE transport containment and browser success/error/finite-body resource/security behavior. Public HTTP schemas/shared types, durable schema/persistence, ACRA/GoldTier/IDP connectors/mappings, configuration fields/defaults, business authority and canonical owners remain unchanged. Provider classifications are unchanged; this is not Live, sponsor interoperability, production compliance, KYC/approval or deployment evidence.

Current local acceptance has exact independent **PASS** with no required fix. Historical AM18 causation stays open under the owner's explicit acceptance route. This report does not waive hosted checks, close review threads, certify publication readiness or start another phase.

`final-published-status.json` directly records PR89 OPEN, published head2790d23, main12ba994, merge state BLOCKED and failed hosted checks. Captured account payment/spending-limit startup evidence remains unresolved. The corrected candidate is still uncommitted/unpublished; no corrected-content hosted CI exists. `pre_pr_check.py` is intentionally NOT_RUN on this uncommitted handoff. No commit, push, PR edit, review resolution, CI waiver or merge occurred.

Next action: coordinator writes the final acceptance-PASS / publication-authorization-pending handoff and stops. A separately authorized publisher must preserve this exact reviewed content, assess latest main, obtain a clean committed pre-PR result and resolve hosted CI/review requirements. Changed integration content requires fresh independent review; repository-owner humans merge. No real-provider readiness or next-phase readiness is granted.
