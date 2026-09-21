# Phase 18 — Case Portfolio Search & Pagination plan

## Scope and identity

- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-postmerge-fix`.
- Branch: `phase/18-case-portfolio-search-pagination`.
- `BASE_SHA`, task-start HEAD, and verified task-start `origin/main`:
  `94af55ab03391dd6e4a24f6b8db6096d9c56f69b`.
- Assigned contract: the user-supplied Phase 18 single-session brief.
- Change classes: `DOCS_ONLY`, `FRONTEND_UI`, `FRONTEND_STATE_CACHE`,
  `BACKEND_DOMAIN`, `BACKEND_API`, `AUTH_RBAC_SECURITY`, `PERSISTENCE`, and
  `CI_TOOLING`.
- No provider, durable schema, migration, index, dependency, new owner, or ADR change.
  Current source, tested content, independently reviewed content, and published commit
  remain distinct identities.

## Contract and canonical owners

- Preserve `GET /api/clm/zero-touch/cases` and its array response unchanged.
- Add `GET /api/clm/zero-touch/case-portfolio`, classified by the existing
  `CASE_PORTFOLIO` policy, returning `{items, offset, limit, has_more}` with the existing
  list-item projection.
- Add frozen typed `CasePortfolioQuery` and page result contracts to
  `domain/case_management.py`; extend only the existing `CaseQueryService` and
  `CasePortfolioRepository` owners.
- Inputs: optional exact `status`, existing `priority_filter`, `priority_sort`, existing
  Director-only `team_filter`, optional exact `attention_type`, optional exact
  `JurisdictionCode`, trimmed literal `search` bounded to 128 characters, `limit` 1..100
  default 50, and `offset` 0..10000 default 0. Filters intersect; UI All omits the
  parameter. Generic FastAPI validation remains data-independent.
- Scope is resolved before repository inspection. Team actors cannot override it; no
  inaccessible case may influence result contents or data-dependent errors.

## Query, ordering, and persistence semantics

- Memory order: authorized scope → status → priority → correlated OPEN attention type →
  jurisdiction → literal case-insensitive search over requested registration ID, legal
  name, and canonical UUID → deterministic sort → offset → `limit + 1`.
- Canonical sort from current source: prioritised rows before unset rows; selected
  numeric priority direction for non-null values; equal-priority ties use `updated_at`
  descending then canonical case UUID string descending; unset rows use the same tie
  order after all prioritised rows.
- Search is trimmed once by the typed query, case-insensitive and literal. The shared
  pattern owner expands ASCII letters into explicit two-code-point classes such as
  `[aA]` and escapes every other code point literally. Both adapters use that exact
  case-sensitive pattern, so engine-specific Unicode folding cannot diverge. The search
  is not locale-aware and does not equate `ß` with `ss` or `i` with `İ`/`ı`. User text
  never becomes Mongo syntax or a field name.
- Mongo performs one aggregation per page: server-authored scope `$match` first, exact
  filters, strict projected-candidate validation, correlated exception `$elemMatch`,
  escaped search, deterministic sort keys, `$skip`, `$limit: limit + 1`, and the existing
  bounded portfolio projection. It transfers no full envelopes, makes no detail fan-out,
  writes nothing, uses no `$out`/`$merge`, and never falls back to memory. Malformed
  in-scope projected data fails safely; out-of-scope corruption is excluded before the
  validation facet. A source-container validity marker is computed before projection so
  a malformed optional object cannot be erased into a false missing value. Supported
  v1-v4 records remain readable.
- Bounded output does not imply constant scan cost. Paging is a live view, not snapshot
  isolation. At offset 10000 with lookahead, the UI disables further traversal and asks
  the user to narrow filters.

## Frontend and cache model

- Keep `CaseQueue`. Move jurisdiction and search to the new page request; keep fixed
  page size 50. Normalize search by trimming; whitespace-only search is omitted.
- Debounce search for exactly 300 ms. Every status, priority filter/sort, team,
  attention, jurisdiction, and debounced search change resets offset to zero.
- Page query identity begins with authenticated user and includes status, priority
  filter, priority sort, team, attention type, jurisdiction, normalized search, offset,
  and limit. GETs retain `AbortSignal`; no previous-key placeholder bridge may display
  old-filter/page data under a new label. Same-key refresh may retain its own data with
  explicit refresh/error copy.
- Existing user-scoped case-list family remains the common invalidation prefix. Creation,
  priority, supporting/review/resume, and other summary mutations invalidate every
  page/filter variant. Deletion cancels the family before cache mutation, removes the
  deleted row from page envelopes, clears exact resources/dashboard/activity, and
  invalidates active portfolio pages so short pages refill. Existing logout, 401, and
  identity/session replacement clearing remains unchanged.
- Add accessible Previous/Next controls and truthful `Showing X–Y`/page wording without
  a total. Preserve Open, priority update, deletion, keyboard operation, and horizontal
  table scrolling.

## Expected paths

- Backend: `domain/case_management.py`, `services/case_query.py`,
  `services/case_portfolio_repository.py`, `persistence/repositories.py`,
  `persistence/mongo_case_store.py`, `api_models.py`, `main.py`, and
  `services/authorization.py`.
- Frontend: `api.ts`, `types.ts`, `caseQueries.ts`, `pages/CaseQueue.tsx`, narrow styles,
  and affected tests/E2E.
- Evidence: focused Phase 18 backend/frontend/real-Mongo tests, physical runner only if
  required to register the owned suite, Phase 17 closeout in `PROJECT_STATE.md`, Phase
  18 contract/demo/report files, and independent quality-gate report.
- Hotspots (`main.py`, shared API/types) receive only additive wiring. No lockfile or
  dependency manifest change is planned.

## Verification and acceptance

- Focused tests cover P18-01..P18-17: old endpoint compatibility, route policy, filter
  intersections, literal/regex-hostile search and 128 bound, UUID/case-insensitivity,
  scope-before-content, memory/Mongo parity, deterministic ties/unset ordering,
  limits/lookahead/cap, one aggregation/no fan-out, strict corruption isolation and a
  fixed sanitized 503 projection for expected persistence failures,
  correlated OPEN attention, zero side effects, exact query identity, session races,
  invalidation, and deletion anti-resurrection/refill.
- Synthetic inventories of 1, 25, and 100+ cases record one page request/query and
  bounded result size, without an SLA or constant-time claim.
- Broad evidence: affected Phase 14/Attention/RBAC/API/security suites, full backend,
  Ruff, mypy, full frontend, typecheck, build, guarded Chromium, all current physical
  Mongo suites with zero skips, POC regression, Windows lifecycle where the matrix
  requires it, governance/tooling/secrets/hygiene, and clean-tree pre-PR checks.
- Phase 17 closeout sets `verified_main_sha` to the inspected `94af55ab...` baseline and
  records its accepted retained-event limitations. Phase 18 remains candidate/pending.
- A fresh independent Sol High reviewer owns only
  `.ai-pipeline/reports/PHASE_18_QUALITY_GATE.md` and must return exact `PASS` across
  P18-01..P18-22 before publication. Findings return to this implementation owner and
  require a fresh re-review.

## Capability/resource preflight and stop conditions

- Available: scoped filesystem edits, PowerShell/Git/Python/Node/npm, collaboration for
  the later independent reviewer, and remote Git after explicit host approval. Python
  3.12.10 and pip check are clean; `.venv`, frontend dependencies, Node 22.23.2, npm
  10.9.8, Playwright 1.56.1, and pinned Chromium 1194 are present. Ports 5173, 8000,
  8875, and 4285 had no listener at task start.
- Docker CLI exists, but the sandbox cannot currently access Docker Desktop. Physical
  Mongo acceptance remains a required gate and will use only the guarded MongoDB 7
  runner, a generated allowlisted database, process-only URI, and verified cleanup after
  approved host access. Browser/Mongo/lifecycle runs are serialized.
- Stop dependent work for baseline drift, ambiguous canonical ownership, an unexpected
  schema/index/migration/dependency need, authorization ambiguity, inability to isolate
  corrupt out-of-scope data, unsafe database/process ownership, unavailable mandatory
  physical/browser evidence, or two unsuccessful repairs of one design mechanism. Do
  not weaken assertions, add fallbacks, fabricate totals, or broaden business/provider
  scope.
