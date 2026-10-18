# PR95-R5 independent combined Quality Gate

## Outcome

**FAIL. Local acceptance and local commits are blocked.** One required P2-06
implementation-conformance gap remains: the captured Mongo batch silently treats an
unexpected raw result outside its captured authorized set as an ordinary excluded row.
The approved independent interface preflight explicitly requires an internal query-integrity
failure for that condition. No implementation fix was made by this reviewer.

This is not an observed Mongo authorization bypass, foreign-record decode, disclosure,
or driver/server failure. The real finite Mongo predicate normally excludes those rows.
The defect is failure to implement an explicit mandatory approved interface guarantee;
passing ordinary and physical suites cannot substitute for that guarantee.

The complete ordinary backend run is still **PENDING at this verdict**, and the remaining
final-review runtime lanes were not started after this confirmed blocker. A later exact
PASS requires remediation, a new content freeze, fresh comprehensive adversarial
re-review and a distinct independent acceptance re-gate. This FAIL report is immutable
history and must not be overwritten to report the corrected candidate.

## Independence, authority and exact input

Reviewer role: final combined Quality Gate only. The reviewer did not implement the
candidate, perform its interface preflight or author its preceding adversarial assessment.
The sole tracked write is this assigned report. The coordinator owns source changes,
Git, runtime scheduling, remote identity checks and local commit/pre-PR work.

- Worktree: `C:/Users/shane/.codex-clean2/worktrees/pr95-dashboard-remediation-20261018/data-dividends-zero-touch-clm`.
- Branch: `codex/pr95-dashboard-remediation-20261018`.
- Committed/published baseline HEAD: `e970a0b31fe2cf2c1617dcc759c9d2131433ba68`.
- Committed baseline tree: `8abb0de47de69a24f88550f3ddece82c03b7a626`.
  These committed identities exclude the uncommitted R4/R5 corrections reviewed here.
- Comparison base/local origin/main: `4a280da473dcdbeb345ffdfa79aaa4c001e75f62`.
- Frozen input: `.runtime/pr95-r5-scoped-final-qg-frozen.json`, all60 raw path hashes.
- Compact sorted path/hash map SHA256:
  `485e4b702cd795ec6769c2c9c7fa38f9a973ddefc3a04a8b164dace040254c97`.
- Frozen tracked binary-diff SHA256 against main:
  `d0a582c04360a97ad90e66525c558b26a212ca9445dce393c30e80db4dd30162`.
- Independent full-PR adversarial prerequisite report SHA256:
  `9cfd0aa2548593559722542bce5fd2a3895fa437d930fdf5125d229cfec72842`.
  Its PASS/CLEAR verdict is a separate preceding assessment and is not final acceptance.
- Interface preflight SHA256:
  `443a25ec606b42195460d702b11c2299ac6a43c827b45869a7e9e01f4b28fa32`.
- Approved interface plan SHA256:
  `337ca8bc724ebb76d1905434ce81da6030a1a8466c364a77fe7c1869db12f43f`.
- Immutable R4 FAIL SHA256:
  `3334134fbeef63ae2a30fe934e1fee43e9168a1d17ab5e82979d786e1292d6ee`.
- All60 hashes were checked at review entry and after the independent probe. The index
  remained empty. This report is the sole additional supporting path, outside its own
  self-referential manifest. No reviewed source/test/configuration/contract was changed.

Authority inspected: complete owner's R5 attachment; root/backend/frontend AGENTS;
canonical quality-gate/report template, persistence, architecture, security/checklist,
frontend state/cache, integration and POC regression instructions; workflow, merge
protocol and coordination rules; dev_context union for BACKEND_DOMAIN, BACKEND_API,
PERSISTENCE, AUTH_RBAC_SECURITY, FRONTEND_UI, FRONTEND_STATE_CACHE and CI_TOOLING;
current architecture/provider/project state and sponsor constraints; case access, timing,
persistence and activity owners; approved plan/preflight; R4 handoff/design/FAIL, R2/R3
attributed historical gates, current implementation/adversarial reports; accumulated
product/test/report inventory against main and owning code/test evidence.

The runtime hold was respected while the coordinator's full backend ran. The coordinator
released only a tiny object-only no-database/no-API/no-pytest probe, which this reviewer
executed. No browser, Mongo server, provider, dotenv or protected data was accessed by
that probe. No claim of independently executing the other reported runtimes is made.

## Required finding R5-QG-01

**P2 -- implement the approved captured-result integrity failure.**

Owner: existing MongoCaseStore captured read boundary.
Location: `apps/backend/app/persistence/mongo_case_store.py`,
`CapturedCaseBatch.read_selected`, especially the raw-key branch at lines109-111.
The current code checks raw `_id` membership only in the final selected subset:

```python
key = raw.get("_id")
if type(key) is not str or key not in selected:
    continue
```

The handle retains its original authorized set, but never distinguishes an authorized
out-of-cohort raw key from a wholly foreign or malformed query result. The approved
preflight's mandatory "Duplicates and inconsistent identities" row states:
"An unexpected foreign query result is an internal query-integrity failure, never data
to publish." The implementation silently succeeds instead of detecting that failure.

Independent reproducer:
`.runtime/pr95-r5-scoped-qg-query-integrity.py`, output
`.runtime/pr95-r5-scoped-qg-query-integrity.log`.
Using the actual CapturedCaseBatch class with synthetic UUIDs and no database:

1. An authorized selected record is decoded while an authorized excluded record is not.
2. A batch authorized only for A contains an unexpected raw row keyed by foreign B.
3. `read_selected({A})` returns an empty successful list with zero decoder calls.
4. Consumed batch references are cleared; no foreign data is decoded or published.

Observed safe diagnostic: `CONFIRMED_GAP unexpected foreign raw result silently returns
empty success; decoder_calls=0`. The probe deliberately does not claim a Mongo server
can violate its actual `_id/$in` predicate. Existing real-driver scope/query proof remains
useful and does not exercise this internal conformance condition.

Required bounded correction: distinguish raw routing-key integrity against the original
captured authorized set from final selected-subset membership, and use the existing safe
persistence error owner for an impossible foreign/inconsistent captured result. Continue
skipping full decoding for valid authorized-but-excluded IDs. Do not validate excluded
nested/schema contents, expand selection, weaken the codec, log raw rows, add a fallback,
introduce another clock/query or move authorization into the repository.

Required regression: a controlled unexpected-result cursor/batch must fail closed with
fixed safe error and clear all references; ordinary authorized excluded rows still avoid
full decode; selected rows remain strict; existing HTTP safe503, final-clock, finite query,
subset, lifetime and physical parity proofs remain. This fits the owner's existing P2-06
and mandatory preflight authorization; it does not require inventing a new architecture
or broader product rule. Implementation is coordinator-owned, after this gate closes.

No additional required product defect was established in this review. This is not a
waiver for unexecuted final-review lanes.

## Acceptance assessment

| Requirement | Disposition at this failed gate |
| --- | --- |
| P2-06 scoped raw capture and final selected decoding | MOST IMPLEMENTED, REQUIRED GAP ABOVE. Existing service resolves authorized IDs, eagerly captures once, reads one final clock, derives Singapore cohort, then selects before strict decode. Missing explicit foreign-result integrity rejection blocks exact acceptance. |
| Encapsulation, subset/lifetime and memory parity | Source review supports existing-owner opaque abstraction; finite UUID sets, one-shot selection, context cleanup, defensive memory models and stable ordering. Independent object probe confirms selected/excluded routing and cleanup; complete final independent runtime acceptance remains incomplete. |
| R4-A1 negative stage values | Implemented narrow Dashboard CaseTimingDataInvalidError guard before DTO projection across the full selected cohort. Existing API returns safe503; no global validator change, clamping or blanket Pydantic handling. Attributed focused and real-Mongo tests pass. |
| R4-A2 capped case presentation | All cases/Your cases/Blocked cases disclose loaded prefix, authoritative cohort total, local-filter/pager limits and Cases navigation. Empty capped claims are local only; creator-only mine semantics and200cap remain. Component0/1/200/201/250 and real205-case evidence inspected. |
| R4-V1 browser inventory | Exact109-to110 expectation reconciliation only; shards55/55 cover complete disjoint union, unchanged9960-second launcher and234-minute outer budget. Governance passes; discovery is not110 executed browser tests. |
| R4-M1 empty pagination | Truthful0of0 and disabled Prev/Next; ordinary page clamping/ranges retained. |
| R4-M2 date selector | Explicit accessible name Dashboard date range; unchanged four options,30d initial request and cache identity. |
| Preserved P2-07 Recent Activity | Ten-item server pages, offset/has_more, live-boundary text, cap/Audit link, Prev/refresh/retry, safe empty/error/loading handling, actor-role/team/creator/page identity and cancellation retained. No invented total or unbounded UI accumulation. |
| Preserved P2-08 disclosure | Six native buttons, stable labelled hidden regions, aria-expanded/controls, sorting and keyboard/focus retained. Actual browser evidence inspected. |
| Five prior R2 fixes | Creator validity before activity filter, canonical resolution chronology, all-cohort validation before200cap, truthful age/duration labels and native sortable headers remain in source/regressions. Relevant current execution receipts pass. |
| Fifteen R3 Ruff fixes/BLE001 | Seven script bytes remain the previously accepted hashes; narrow sampler containment annotation, exact source barrier, Decimal/import/fixture safeguards retained. Current broad/configured Ruff and performance/fixture evidence pass. |
| Legacy API and metrics | All-history default and original30-day UTC historical_trend retained;30d UI is explicit; Singapore created-date cohorts, creator cases/resolver fixes and integer means remain. Descriptive project metrics add no sponsor SLA/compliance/performance authority. |
| Main/Assistant/auth/cache | Accumulated App delta preserves accepted Assistant/authenticated transport; existing AuthProvider/QueryClient own identity/logout/401 clearing and cancellation. Root actual8-browser regression receipt includes Assistant and auth/navigation. |
| Persistence and provider boundaries | Existing strict schema1..10, identity/CAS/create/update/delete/restart/ledger owners retained; no route-to-Mongo, schema/index/migration, provider call, configuration or production grant added. |
| Full backend/current independent acceptance | PENDING at verdict; independent final runtime lanes not executed after required finding. No stale baseline substituted. |
| Exact local commit/pre-PR readiness | BLOCKED. No implementation commit and no actual pre_pr_check.py execution is permitted from this FAIL. |

## Current evidence, attribution and limitations

The following coordinator/adversarial results belong to the frozen current implementation
input, not the historical R3 baseline. They were inspected as evidence; they do not become
this final reviewer's independent executions by attribution.

| Lane | Actual result and evidence |
| --- | --- |
| This independent reviewer: object-only adverse probe | CONFIRMED required conformance gap; selected/excluded routing and post-consumption cleanup pass. qg-query-integrity.py/log. No DB/API/browser/provider request. |
| Independent preceding full-PR backend |94 passing items, no failure/skip markers; audit-backend.log. |
| Independent preceding Dashboard/cache |41 PASS,2files; audit-ui.log. |
| Independent preceding additional adverse |7 PASS; audit-probe.py/log: snapshot updates, cleanup, schemas and negative sample after200 rows. |
| Independent preceding actual configured browser |2 PASS,25.7s; audit-browser.log, real guarded local HTTP/Mock behavior. |
| Independent preceding complete guarded Mongo |24 suites,165 collected/165 PASS,0fail/errors/skips; audit-physical-full.log, canonical guarded runner. |
| Coordinator full frontend |955 PASS/57files,12.45s; frontend-full.log. Existing React test warnings remain. |
| Coordinator typecheck/build/npm tree |PASS; typecheck.log/build.log/npm-ls.log. Existing680.40kB Vite bundle warning remains. |
| Coordinator API contracts |44 PASS,3.16s; contract.log. |
| Coordinator governance/performance |244 PASS,88.041s; governance.log. Injected runner-failure output belongs to passing harness tests. |
| Coordinator broad/configured backend Ruff |PASS; ruff-broad2.log/ruff-backend2.log. |
| Coordinator configured mypy |PASS,127sourcefiles; mypy-configured.log. |
| Coordinator six static/security checks |PASS; static.log. Project state, architecture, tooling, policy authority, external-provider readiness and secrets. |
| Coordinator dependency integrity |pip check PASS; pip-check.log. |
| Coordinator broader actual browser |8 PASS,35.0s; browser-broad.log: Assistant, auth, RM/Director, portfolio/activity, responsive containers and logout/role reset. |
| Coordinator focused physical |13 PASS; physical-focused-final.log. Supplemental to the complete165 run. |
| Coordinator full ordinary backend |PENDING at this FAIL verdict, active session59746; backend-full.log. No predicted pass/count/skip attribution. |
| This reviewer's remaining runtime checks |NOT_EXECUTED after confirmed required failure. No independent final acceptance claim. |
| Actual clean committed pre-PR |NOT_RUN; candidate intentionally uncommitted and exact independent PASS prerequisite unmet. |

All short log references above have prefix `.runtime/pr95-r5-scoped-`.
Physical execution by the preceding independent reviewer verified the owned mongo:7
container `6dd114f17e0d0a02114a0d627e3a68be4653e1284f3a360ad70c664e31419046`,
loopback27029, canonical generated allowlisted databases and cleanup. No protected
clm_poc operation or URI disclosure is claimed or performed by this reviewer.

Preserved failures are part of the evidence, not erased by passing reruns: original
UI6RED/backend8RED, test-double and browser fixture assumptions, full physical164PASS/
1FAIL and focused12PASS/1FAIL query-spy signature errors, corrected spy/full165PASS,
noncanonical root type/lint invocation failures and R4 FAIL. The spy repair retains query
count/predicate assertions and changes no product behavior. Configured backend-CWD type/
lint runs are distinguished from unsuccessful root invocations.

Prior R3 full-backend2799PASS/164SKIP and physical158PASS are historical only. Optional
native OCR availability is not proved in this gate. Historical GitHub billing-refused
jobs remain NOT_EXECUTED; no new hosted review/CI was requested or approved. Actual
relevant browser2+8 execution is narrower than all110 discovered selectors. Existing
Vite/SSR/test-render warnings and inherited global mobile overflow remain explicitly
limited; contained table scrolling does not claim whole-document overflow freedom.

## Architecture, security and readiness

The chosen interface extends the existing automation repository/store owner rather than
creating a new authority. Its preflight no-ADR decision remains valid for that bounded
shape, but its mandatory guarantees must actually be implemented. Raw data stays private,
backend scope remains authoritative, errors remain sanitized for established selected
failures, and no new connector/mapping/schema/configuration/business-policy/provider
classification or durable-write change was found. The internal read port/lifecycle and
frontend presentation/runtime behavior change as authorized.

Current required fixes: **R5-QG-01 only**, plus completion and independent assessment of
the required current runtime evidence on the corrected freeze. Production sponsor
questions, actual external interoperability and optional native OCR are separate limits;
none is silently solved by this Dashboard review.

Recommendation: **BLOCKED**. The coordinator may perform only the already authorized
bounded P2-06 conformance remediation, then fresh review stages. No local implementation
commit, pre-PR readiness claim, push, new/replacement PR, hosted review/thread action,
PR96 modification, merge or next phase is authorized by this verdict. Main, teammate
history, unrelated worktrees, dotenv, databases and prior evaluation artifacts remain
preserved. This review performed no Git or external mutation.
