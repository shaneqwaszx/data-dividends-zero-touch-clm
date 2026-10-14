# AM Wave 1 execution plan

Start: 2026-10-14 01:32 SGT (first execution clock receipt 01:32:54).
Ceiling: approximately 07:32 SGT; feature cutoff 05:32, release reserve at least 120 minutes.
Task: owner pasted replacement brief v2; downloaded prompt is supporting context, not separate authority.

## Baseline and ownership

- Repository: shaneqwaszx/data-dividends-zero-touch-clm.
- Initial BASE_SHA / HEAD / fetched origin/main: a497793be2615306bc7cfbd3104fd4352dead96d.
- Initial tree: 8845949f4f76400678a5ebb041629dc8b96dde26.
- Worktree: C:/Users/shane/Desktop/FYP/am-w1-1014-0132.
- Branch: feat/am-wave1-20261014-0132; clean on creation; zero open PRs observed.
- Owner main and all existing worktrees/untracked paths remain untouched.
- Root agent: sole planner/implementation writer and Git coordinator; sequential role boundaries.
- Independent reviewer: fresh High subagent after final candidate freeze; report only at .ai-pipeline/reports/AM_WAVE1_INDEPENDENT_QUALITY_GATE.md. No application/Git writes.
- Root model is host-selected GPT-6-family; exact model/effort not exposed here. No persistent settings/speed change.

## Scope and owners

1. AM-18 first: authenticated offline browser reproduction of classification, balanced ownership correction, currentness/readiness/final review. Fix only a proved defect with baseline failing-first regression. Domain/API owners: zero_touch_orchestration, clm_orchestration, ownership_analysis, case classification, existing transition model/repositories. UI owners: CaseDetail and caseQueries. Primary case must remain NOT_SUBMITTED.
2. B independently if capacity remains: AM-05 registry SGT display with raw ISO audit detail/invalid handling; AM-14 new declaration Singapore calendar default preserving source dates/drafts; AM-15 regression.
3. C independently if release reserve remains: AM-09 actual decision cards responsive layout; AM-10 DOCUMENT-only eligible undecided draft prefills preserving manual choices and requiring existing Confirm.

Potential classes routed before implementation: BACKEND_DOMAIN, BACKEND_API, FRONTEND_UI, FRONTEND_STATE_CACHE. Final classes follow actual edits; add PERSISTENCE/security only if triggered. No architecture/new owner/schema/provider/source-policy changes authorized. AM-03 and all other AM implementation deferred. Source-action authority, >=25%, final Send/ledger no-replay, count-bound intake, replacement lineage, actor/currentness remain unchanged.

## Capability/resource preflight

- GitHub fetch/open-PR reads succeeded with sandbox escalation. Normal publication authorized after exact independent PASS.
- Python 3.12.10; Node 22.23.3; npm 10.9.9. Existing pinned Python toolchain inspected (pytest 8.4.2, FastAPI 0.141.1, uvicorn 0.52.1, Ruff 0.16.2, mypy 1.20.2, pymongo 4.15.1).
- Task-owned frontend locked dependencies installed; no dependency/lockfile edit. Python commands use existing interpreter with task source imports.
- Canonical scripts/run_e2e.py owns explicit offline settings, ephemeral credentials, loopback processes/network policy and output directories. Reserve requested starting ports 18765/14173; runner verifies/allocates owned ports. Browser/HTTP execution pending early probe.
- Subagent tool available; fresh gate availability to be established at freeze.
- Physical Mongo prerequisite pending if retained-state/CAS/restart changes trigger it; only canonical runner with new allowlisted disposable test DB allowed. No .env or owner database access.
- Sibling writes need sandbox escalation; explicit task authorization covers task-owned files.

## Verification and stop rules

Focused RED/GREEN first; frozen combined candidate gets union of applicable checks. Exact commands:
- Existing Python interpreter -m pytest apps/backend/tests (when domain/API applies); -m ruff check apps/backend scripts tests; -m mypy apps/backend/app; contract unittest inventory and affected security/lifecycle suites.
- apps/frontend: npm test; npm run typecheck; npm run build; focused Vitest selections.
- Canonical browser runner: python scripts/run_e2e.py --backend-port 18765 --frontend-port 14173 --timeout-seconds 60, focused --grep plus existing offline fixture when appropriate.
- AM-18 backend repair additionally requires complete discovered inventory via --shard 1/2 and --shard 2/2, unchanged 60-second lifecycle budget.
- PERSISTENCE trigger requires physical safe runner; no mock substitute. Relevant UI release requires actual authenticated browser and responsive screenshots.
- Governance/secret/whitespace checks include every task-owned new path; final path inventory raw SHA256 and Git blob/tree identities freeze before independent gate.
- At most two post-gate corrective cycles, each fresh independent re-gate. Exact PASS only; no self-approval.
- After PASS: fetch latest main, inspect drift/overlap, safe authorized integration, affected rechecks/review; explicit staging and normal commit; clean committed pre_pr_check and checklist; normal push and one PR; attach PR; bounded push and PR CI/review observation. Human merge only.
- Missing required evidence blocks dependent slice. Stop AM-18 at about 120 investigative minutes if unresolved, preserve exact classification. No provider network calls, protected inputs, time inflation, bypass fixtures, hidden skips, broadened scope or final approval.

## Checkpoint

Preflight baseline/isolation and locked frontend setup complete. AM-18 reproduction next. Included candidate: none yet. Required checks pending; no acceptance/publication claim.


## Milestone A / B-C boundary (01:46 SGT)

AM-18 NOT_REPRODUCED: exact authenticated new and prior-verified existing-customer
60/40 -> 55/45 journeys pass on unchanged product baseline, including current
classification, regenerated ownership, refreshed final review and reload; primary
cases NOT_SUBMITTED. Initial probe field assertions were setup-only failures, retained
in ignored logs, not product-failing-first evidence. Existing S2 browser passes too.
No AM-18 implementation change. B/C independent implementation selected.

AM-14 producer/consumer boundary: baseline date-only future validation used UTC day,
rejecting today's explicit Singapore date between midnight and 08:00 SGT. Two deterministic
baseline regressions prove this. Existing no-future-date rule now uses the requested
Singapore calendar day; review instants remain UTC. This is a bounded BACKEND_DOMAIN
edit within the existing manual evidence owner, no new rule/schema/owner/CAS behavior.
Final required union: BACKEND_DOMAIN + FRONTEND_UI + DOCS_ONLY; no shared cache change.
Full backend/Ruff/mypy and relevant security/lifecycle regressions therefore required.
AM-18 full-shard addendum is not triggered by an AM-18 repair (none); full discovered
E2E remains optional extra evidence subject to safe disposable prerequisites.

Change Necessity: code-change for the explicit B/C requirements; no-change for AM-18.
Minimality/owner fit: shared date formatting and existing declaration/date validator,
review draft state and existing responsive grid; edit-in-place, no competing state owner.
TDD Mode off: new tests are diagnostic failing-first evidence; no strict route inferred.
B/C RED: frontend 10 failed/31 passed; backend midnight 2 failed/3 passed/21 deselected.
Checks still required: focused GREEN, broad union, actual UI date/bulk/responsive flows,
independent exact PASS, latest-main/clean committed pre-PR, publication/remote observation.

## Combined candidate / release reserve

Features A investigation and B/C implementation are closed for this candidate.
AM-18 remains open with exact NOT_REPRODUCED boundary; only B/C is shipped scope.
Required classes BACKEND_DOMAIN/FRONTEND_UI/DOCS_ONLY. Final source/tests and ordinary
docs freeze under tmp/am-wave1/frozen.json before a fresh independent High gate.
No more feature work. Source bytes remain fixed while the reviewer checks important
adverse behavior and final broad current-byte evidence. At least 120 minutes remain.
Publication role begins only after exact PASS and required receipts; zero corrective
cycles consumed. Remote checks/review and clean committed pre-PR remain pending.
