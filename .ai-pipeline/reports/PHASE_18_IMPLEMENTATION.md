# Phase 18 — Case Portfolio Search & Pagination implementation record

## Identity and status

- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-postmerge-fix`.
- Branch: `phase/18-case-portfolio-search-pagination`.
- `BASE_SHA`, task-start source, and verified task-start `origin/main`:
  `94af55ab03391dd6e4a24f6b8db6096d9c56f69b`.
- Released Phase 17 branch was inspected at the expected
  `187f73710e70b0792b0999290d25a6429850e376` feature head before branching.
- Current status: three independent gates returned exact `FAIL`: the first on optional
  source-container erasure and full-fold search divergence, the second on remaining
  dotted/dotless-I regex-engine divergence, and the third on the portfolio route's
  persistence-error projection. All findings are remediated with focused, physical, and
  broad regression evidence; fresh independent re-review and publication are pending.
- The current uncommitted candidate is identified by
  `.ai-pipeline/reports/PHASE_18_CANDIDATE_MANIFEST.txt`. Independent reviewed content,
  eventual publication commit/tree, and remote CI identities remain distinct.

## Delivered behavior and owners

- Preserved `GET /api/clm/zero-touch/cases` and its array response. Added
  `GET /api/clm/zero-touch/case-portfolio` under existing `CASE_PORTFOLIO` access,
  returning `{items, offset, limit, has_more}` with no total.
- Added frozen `CasePortfolioQuery`/`CasePortfolioPage` contracts and shared exact filter
  and ordering functions in `domain/case_management.py`. `CaseQueryService` still owns
  scope/query composition; existing memory/Mongo portfolio adapters still own reads.
- Composed status, priority filter/order, Director team semantics, correlated OPEN
  attention type, exact jurisdiction, and literal ASCII-case-insensitive registration/
  legal name/canonical UUID search. Search trims to absence and is bounded to 128
  characters. A shared pattern expands ASCII letters to paired character classes and
  escapes all other code points, so memory and Mongo do not delegate semantics to
  different Unicode case-folding engines.
- Preserved the accepted order: prioritised before unset; selected numeric direction;
  equal priority by `updated_at` descending then canonical UUID string descending; unset
  uses the same ties at the tail. All predicates precede offset and `limit + 1`.
- Memory scopes before content projection. Mongo uses one scoped read-only aggregation,
  `re.escape`, strict projected-record validation, correlated `$elemMatch`, deterministic
  sort, skip, and lookahead. It transfers no full envelope, performs no row-detail read,
  writes nothing, adds no index, and never falls back to memory. It records the validity
  of projected optional source containers before projection can erase their type, then
  combines that marker with strict projected validation. In-scope projected corruption
  fails closed; out-of-scope corruption is excluded before validation.
- Migrated the existing Cases page to the page endpoint with fixed size 50, synchronous
  page reset for every presentation input, exactly 300 ms search debounce, truthful
  ranges/no-total copy, Previous/Next, offset-cap narrowing copy, native Open links,
  priority update, deletion, and focusable horizontal scrolling.
- The default authenticated session prefetch now uses the bounded portfolio page rather
  than the compatible unbounded list. Query identity contains user plus every server
  filter/sort/search/page dimension and retains `AbortSignal`.
- Existing summary mutation effects invalidate the entire authenticated case-list
  family. Deletion cancels first, removes the case from both legacy arrays and page
  envelopes, clears incompatible supporting caches, and refetches active pages.
- The guarded E2E application has a test-mode-only, 1..250 bounded fixture parameter;
  the runner seeds 105 Team Alpha cases through `ZeroTouchOrchestrator`, not a raw
  repository. Non-test applications cannot enable it.

## Changed paths and classification

Canonical backend owners:

- `apps/backend/app/domain/case_management.py`
- `apps/backend/app/services/case_query.py`
- `apps/backend/app/services/case_portfolio_repository.py`
- `apps/backend/app/persistence/mongo_case_store.py`
- `apps/backend/app/persistence/repositories.py`
- `apps/backend/app/api_models.py`
- `apps/backend/app/main.py`
- `apps/backend/app/services/authorization.py`

Frontend/cache owners:

- `apps/frontend/src/api.ts`, `types.ts`, `caseQueries.ts`
- `apps/frontend/src/pages/CaseQueue.tsx`
- affected accepted/focused frontend and Playwright tests

Supporting tests/tooling/docs:

- Phase 18 backend/frontend/real-Mongo suites; route/safety/runner tests
- guarded E2E runner grep support and 105-case test fixture composition
- Phase 18 plan, contract, demo, implementation/evidence records
- `PROJECT_STATE.md` Phase 17 closeout and Phase 18 pending-candidate status
- `ARCHITECTURE.md` established portfolio/cache-owner detail

Applicable classes: `DOCS_ONLY`, `FRONTEND_UI`, `FRONTEND_STATE_CACHE`,
`BACKEND_DOMAIN`, `BACKEND_API`, `AUTH_RBAC_SECURITY`, `PERSISTENCE`, `CI_TOOLING`.

## Acceptance evidence

All successes below are from the final owned content or from explicitly identified
unchanged lanes carried forward after the route-boundary-only remediation.

- Focused backend Phase 18 plus accepted Cases/Attention/Activity regressions: **61/61**.
- Focused frontend Phase 18/Phase 14/Attention: **22/22**.
- Full backend final remediation rerun: **1088 passed**, 27 expected environment/physical
  skips, 0 failed, 5 existing warnings, in 83.96 seconds.
- Ruff over backend, backend tests, scripts, and root tests: PASS. Strict backend mypy:
  **94 source files**, no issues.
- Full frontend: **252/252**; typecheck PASS; production build PASS with 113 transformed
  modules; Playwright inventory exactly 6 tests.
- Complete root contracts/governance/runner/scanner/lifecycle suite before the bounded
  route-only repair: **231/231** on the approved host with the required contract-support
  path. Direct project-state, architecture, tooling, and secret checks were rerun after
  the final repair and pass.
- The full backend rerun subsumes the previously explicit accepted POC regression
  catalogue slice (**591/591** before remediation). Straight-through Mock
  completion, review/technical separation, exact downstream stopping, jurisdiction
  gating, current-evidence reconciliation, recovery/no replay, case isolation, and
  truthful provider labels remain unchanged. The catalogue required no update.
- Windows lifecycle remediation rerun: **23/23** in 291.81 seconds. Ports 8000, 5173,
  8875, 4285, 8765,
  and 4173 and task-owned Python/Node processes were clear afterward.
- Guarded Chromium final unfiltered run: **6/6** in 17.3 seconds. Phase 18 covers one
  unique bounded default page shape, no legacy unbounded prefetch, no row-detail fan-out,
  105-case paging, literal search, jurisdiction/priority composition, native route,
  logout/login user scope, priority refresh, deletion anti-resurrection, keyboard focus,
  and 480 px internal scrolling.
- Synthetic API inventories of 1, 25, and 105 cases prove bounded replies at page sizes
  1, 25, and 100. Guarded browser uses 105. Physical Mongo uses 105 and proves the
  100/5 page boundary.
- Physical MongoDB 7 guarded remediation runner:
  `SUITES=7; COLLECTED=27; PASSED=27; FAILED=0; ERRORS=0; SKIPPED=0`.
  The exact loopback-only `mongo:7` container was verified, every generated `clm_p18_*`
  database was absent after test cleanup, and the container/anonymous volumes were then
  removed and confirmed absent.
- Final TypeScript validation, route-policy inventory, conflict scan, and tracked
  whitespace check were rerun after browser evidence changes. Candidate-manifest hygiene
  covers every task-owned new file separately.

## Preserved failure and remediation history

1. The first physical run passed 24 of 25 but rejected the newly generated `p18`
   database name. The safety owner did not yet allow Phase 18. The allowlist and its
   adverse tests were extended; 12/12 focused safety/physical tests and then all 26
   physical tests passed. No Mongo query behavior was weakened.
2. Focused frontend runs exposed stale accepted fixtures that still seeded the old array
   key. Phase 14, Attention, and Phase 15C fixtures were migrated to the exact page
   envelope/key; focused and full suites passed.
3. A first browser corpus used 55 authenticated case creations and exceeded the browser
   budget at the protected write boundary. The corpus moved to the bounded test-only app
   fixture through the canonical orchestrator; the browser now exercises 105 records in
   seconds while all product interactions remain real authenticated HTTP/DOM behavior.
4. Self-review found session prefetch still called the compatible unbounded list. It was
   changed to the bounded default page and covered by unit/browser assertions. No legacy
   API removal occurred.
5. Full backend found the deliberate route-cardinality/count assertion stale after the
   new classified route (59 total; 4 `CASE_PORTFOLIO`). Both inventory and counts now
   pass.
6. Full frontend found one Phase 15C real-link fixture on the old key. The test was
   migrated without changing navigation behavior; 252/252 passed.
7. Guarded-browser diagnosis found development StrictMode can cancel/replay an identical
   initial request. Evidence therefore asserts one unique bounded page shape plus no
   legacy/fan-out reads; cancellation remains intact. Accepted document/attention/
   activity tests were made response/state-bound where asynchronous route replacement
   had been flaky. No assertion weakening, product fallback, or permanent timeout
   expansion was used in the final repair.
8. One sandboxed Vitest attempt could not spawn local `esbuild`, and one root contract
   attempt lacked its explicit support path. Approved host reruns with unchanged content
   passed. These were infrastructure/setup failures, not product successes.
9. The first fresh independent gate found that projecting `onboarding.entity.legal_name`
   could erase an in-scope scalar `entity` before validation. The single aggregation now
   computes optional source-container validity before projection and carries that marker
   into both validation facets. The new real-Mongo regression rejects the scalar while
   preserving out-of-scope isolation.
10. The same gate found Python full `casefold()` matched `STRAẞE` for `strasse` while
    Mongo's case-insensitive regex did not. The first repair replaced full folding with a
    shared escaped regex and excluded multi-code-point fold expansion; the later repair
    in item 12 supersedes that engine-owned case-insensitive execution.
11. A remediation static rerun exposed that moving `PriorityFilter`/`PrioritySort` to the
    domain stopped mypy from recognizing the service's compatibility re-export. Explicit
    aliases restored that public boundary; strict mypy over all 94 source files and the
    focused 56-test backend slice pass. A sandboxed 208-test root run could not create
    temporary Git repositories; the unchanged approved-host rerun passed 208/208.
12. The next fresh re-gate proved Python `re.IGNORECASE` equated `i` with `İ`/`ı` while
    Mongo PCRE did not. The shared pattern owner now encodes ASCII case pairs explicitly,
    escapes every non-ASCII code point, and both adapters execute the resulting pattern
    case-sensitively. Unit and real-Mongo regressions cover dotted/dotless I and retain
    the `ß`/`ss` non-equivalence. Full backend 1085/1085, physical 27/27, focused browser
    1/1, Ruff, and strict mypy passed afterward.
13. The next whole-phase gate closed both earlier classes but found that expected
    portfolio persistence failures reached FastAPI's generic 500 boundary. The route now
    maps corrupt data, unsupported schema, and unavailable persistence to fixed sanitized
    HTTP 503 detail `CASE_PORTFOLIO_UNAVAILABLE` without exception text or fallback.
    Route-level regressions cover all three errors; the focused slice passed 61/61 and
    the complete backend suite passed 1088 with 27 expected skips.

## Contract and risk disclosures

- API/model/types: one additive page route and page/query DTOs; old endpoint unchanged.
- Persistence schema/migration/index: unchanged; case envelope remains v4; no migration
  or index.
- Connector/provider/configuration: no provider or connector behavior/status change, no
  dependency/lockfile change, no runtime mode, credential, or persisted configuration
  change. The E2E seed is an in-process test-app factory argument only.
- Business/workflow/mapping/readiness/target behavior: unchanged. Jurisdiction filtering
  observes stored labels and does not activate AU/MY/HK providers.
- Auth/security: no role/capability owner change; the additive route uses existing
  `CASE_PORTFOLIO`, scope is resolved before data-dependent validation, and ordinary team
  actors cannot override it.
- Architecture/ADR: established owners are extended; no new service, repository, state
  owner, dependency direction, persistence strategy, or ADR trigger.
- Sponsor authority: no question status changes. Q-016 and all recorded production
  policy/integration blockers remain open.

## Honest limitations

- Pages are a live offset view, not snapshot isolation; concurrent changes can move rows.
- There is no total, export, assignment, SLA, risk, approval, escalation, notification,
  retention/archive, analytics, or global search service.
- The Mongo reply is bounded, but scan cost can still grow with the collection. No index,
  constant-time claim, production scale, or performance SLA is established.
- Search is literal ASCII-case-insensitive substring matching with exact non-ASCII code
  points; it is not fuzzy, semantic, locale-aware, or a Unicode fold search.
- Memory remains default and Mongo remains an explicit single-instance durable POC mode.
- Provider classifications remain ACRA Mock/default, generic ACRA sandbox Partial,
  BizFile Dormant, IDP Local/Mock, ownership Local, GoldTier Mock only; nothing is Live.

## Five-minute demo and next action

Use `docs/demo/PHASE_18_CASE_PORTFOLIO_DEMO.md`: show one bounded no-total page, literal
search, composed filters, Previous/Next, native Open, priority refresh, deletion, and
480 px keyboard/scroll behavior while narrating the live-view and provider limits.

Next authorized action: freeze this candidate manifest, obtain a genuinely fresh Sol
High independent verdict in the reviewer-owned Phase 18 quality-gate report, and publish
only after exact `PASS`. Do not merge and do not start Phase 19.
