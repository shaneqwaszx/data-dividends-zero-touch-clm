# Case Evidence & Explainability Workbench — implementation evidence

## Candidate identity and scope

- Task: the unnumbered Case Evidence & Explainability Workbench increment governed by
  `.ai-pipeline/001_planner/OVERNIGHT_EVIDENCE_WORKBENCH_BRIEF.md`.
- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-postmerge-fix`.
- Branch: `feature/evidence-explainability-workbench`.
- `BASE_SHA`, task-start HEAD, and examined/fetched `origin/main`:
  `6625835e6ca8b7e531c25b3078c3ff58ee4df843`.
- Current source revision: the branch still points to the base commit; the candidate is
  the unstaged working-tree content identified by the canonical Git blob manifest below.
- Tested revision: that frozen working-tree content after the final text-wrapping and
  independent-gate focus-identity remediations. The final report and QG report are
  evidence additions, not runtime code.
- Change classes: `BACKEND_API`, `FRONTEND_UI`, `FRONTEND_STATE_CACHE`, and
  `AUTH_RBAC_SECURITY` (public projection/privacy boundary). No backend-domain,
  persistence/schema, external-provider, architecture-refactor, dependency, or CI
  tooling change was made.

## Implemented capabilities

1. The authorized case response has one additive nullable seven-field projection of the
   retained registry binding. It exposes disposition, case binding time, computed
   expiry, and the fixed Mock policy ID/version/duration/comparator. It fails closed for
   non-Mock binding provenance and excludes cache identity, keys, revisions, anchor/write
   times, fingerprints, endpoints, references, repository details, and raw payloads.
2. The case page presents original registry operation provenance separately from the
   case-use binding. A missing binding is explicitly unknown/unrecorded; it never implies
   a miss, disabled cache, provider fetch, freshness, or current validity.
3. The ownership explorer uses only the existing backend Decimal analysis. It preserves
   exact percentage/calculation/classification/issue strings, renders retained edges in
   the domain's owned-entity-to-owner direction, caps the selected visual, discloses any
   hidden boundary, paginates retained paths, and labels partial/limited results as
   non-definitive rather than complete or legal UBO conclusions.
4. The state explanation panel reads only current typed workflow, readiness, exception,
   technical-failure, and ordered target-ledger state. It renders server blocker/warning
   strings safely, applies wording only to closed enums, labels unknown runtime values,
   and uses fixed evidence-section mappings with a visible unavailable fallback.
5. Candidate/path state is browser-local, query-free, storage-free, and remounts on
   actor, case, or ownership-analysis identity. Evidence focus targets remount and their
   unavailable notice is synchronously identity-filtered on actor/case changes. The
   existing explicit refresh remains the same three authorized GETs. Existing
   document/reconciliation/recovery/priority/delete controls, backend RBAC/team scope,
   query owners, and target no-replay ledger remain the sole owners.

## Changed owners and files

- API projection owner: `apps/backend/app/api_models.py`; focused proof in
  `apps/backend/tests/test_evidence_workbench_registry_projection.py`.
- Shared frontend contract: `apps/frontend/src/types.ts`.
- New prop-only presentation owners and tests:
  `RegistryProvenancePanel`, `OwnershipPathExplorer`, and
  `CaseStateExplanationPanel` under `apps/frontend/src/pages/`.
- Existing case-detail composition and presentation only:
  `apps/frontend/src/pages/CaseDetail.tsx` and `apps/frontend/src/styles.css`.
- Cross-owner adverse coverage: `apps/frontend/src/EvidenceWorkbenchIsolation.test.tsx`
  and the existing guarded `apps/frontend/e2e/authenticated-zero-touch.e2e.ts` journey.
- Canonical context: `docs/PROJECT_STATE.md`, `docs/ARCHITECTURE.md`, and
  `docs/contracts/REGISTRY_CACHE_FRESHNESS_PROFILE.md`.
- Demo and governance evidence: `docs/demo/EVIDENCE_WORKBENCH_DEMO.md`, the supplied
  governing brief, the execution plan, this report, and the separately owned final QG
  report.

The old static ownership/readiness presentation inside `CaseDetail` was retired. The
canonical ownership engine, readiness owner, target-operation ledger, case API, query
keys, transport, auth policy, persistence model, and all supported mutation controls
were not retired or duplicated.

## Explicit non-changes

- API/model/type: one additive nullable browser field and its exact TypeScript mirror;
  existing response fields/endpoints are unchanged.
- Schema/persistence: no case-envelope/cache schema, repository, CAS, migration, index,
  or read-repair change.
- Connector/configuration/provider: no connector, call order, cache behavior/default,
  environment variable, runtime composition, or provider classification change.
- Business rule/mapping: no freshness, source-precedence, ownership, readiness,
  risk/SLA, approval, retention, or sponsor-policy rule was added.
- Auth/security: no capability, role, team-scope, session, CSRF, route, or safe-404 owner
  changed. The public projection was deliberately minimized and Mock-only.
- Architecture/runtime: no new endpoint/query/service, graph engine, workflow action,
  target replay, Camunda runtime, Live integration, or dependency was added.

## Review and remediation history

- Parallel read-only backend/API and frontend/acceptance discovery completed before the
  interface was frozen.
- A fresh High architecture/privacy plan reviewer returned two `REVISE` rounds; the plan
  minimized the binding from internal cache detail to seven public fields, made
  zero-call/ledger-read proofs explicit, classified the security boundary, froze typed
  explanation sources, and clarified bounded ownership direction/completeness. Final
  plan verdict: `PROCEED`.
- Independent backend slice review: `PASS` with no findings.
- Independent frontend slice review: `REVISE` for unknown readiness/target values and a
  same-analysis pagination-clamp defect. Both were repaired and the reviewer returned
  `PASS` on recheck.
- A separate adversarial test author added four integration tests without editing
  production code.
- A fresh supplemental High integration-security reader returned `PASS` with no active
  findings after inspecting the public projection, RBAC/safe-404 boundary, browser
  state/network/storage behavior, target no-replay boundary, labels, and diagnostic
  hygiene. Its selected evidence was 8 backend and 21 frontend tests plus the secret
  scanner; heavy suites remained coordinator evidence.
- First guarded browser acceptance failed the new 480px root-width assertion at 749px;
  the document-review journey did not run after fail-fast. A controlled diagnostic
  identified wide table/text surfaces. The first bounded grid min-width repair reduced
  the root to 536px. A second header-wrap attempt did not change it and was removed.
  After the two-attempt convergence limit, a fresh High layout analyst identified the
  unbreakable retained path ID outside the intentional table scroller. The materially
  different owner-level `overflow-wrap: anywhere` repair passed focused tests and all
  three real browser journeys while separately proving internal table scrolling.
- No test timeout, security control, assertion, or source classification was weakened.
  The initial failures remain recorded here and are not counted as passing evidence.
- The first final independent quality gate returned `FAIL` on EW-QG-001: focusable
  evidence wrappers could be reused and their unavailable notice was cleared only in a
  post-commit effect across an actor/case identity transition. The bounded remediation
  keys each focus wrapper to actor/case identity and stores the notice with that identity,
  so stale focus is removed by DOM remount and stale text is never rendered under the
  replacement identity. A new integration regression proves both case and actor changes
  detach the old focused node, suppress the old notice synchronously, and issue no
  request. No timeout, focus stealing, routing/auth refactor, or persistence was added.

## Verification evidence

| Layer | Command/evidence | Result |
|---|---|---|
| Context | `.venv\Scripts\python.exe scripts\dev_context.py` | PASS at startup |
| Backend focused | `pytest apps/backend/tests/test_evidence_workbench_registry_projection.py -q` | 6 passed; two dependency deprecation warnings |
| Backend lint | from `apps/backend`: `ruff check .` | PASS |
| Backend types | from `apps/backend`: `mypy app` | PASS; 94 source files |
| Backend full | from `apps/backend`: `pytest tests -q` | exit 0; 1,064 collected; 1,042 executed/passed and 22 environment-gated physical skips |
| Contracts | `unittest discover -s tests\contract -p "test_*.py"` | 44 passed |
| Delivery assets | `unittest discover -s tests -p "test_phase_07_delivery_assets.py"` | 4 passed |
| Frontend focused/integration | workbench isolation and Phase 15C navigation after EW-QG-001 remediation | 41 passed; identity regression included |
| Frontend full | `npm.cmd --prefix apps\frontend test` | final 15 files, 234 tests passed; existing SSR `useLayoutEffect` warnings only |
| Frontend types | `npm.cmd --prefix apps\frontend run typecheck` | PASS after identity remediation |
| Frontend build | `npm.cmd --prefix apps\frontend run build` | PASS; 112 modules transformed |
| Browser collection | `npm.cmd --prefix apps\frontend run e2e:list` | 3 tests in the preserved file |
| Guarded browser | `scripts\run_e2e.py --backend-port 8871 --frontend-port 4281` | final 3/3 passed in 9.6s after identity remediation; real login/local APIs/network guard |
| Windows lifecycle | `unittest ... test_demo_lifecycle_windows.py -v` | 23 passed in 317.503s; real start/stop/reset/login paths |
| Governance | `check_project_state.py`, `check_architecture.py`, `check_tooling_config.py` | all PASS |
| Security hygiene | `scripts\check_secrets.py` | PASS |
| Mongo parity | local physical runner | not applicable: no persistence/schema/CAS/read compatibility change; standard hosted CI physical lane remains required and will be reported |

The initial sandboxed Vitest attempt failed before collection because local esbuild
process creation returned `spawn EPERM`; the same focused command passed through the
supported approval path. This was an environment precondition failure, not product
evidence. Backend/full-suite skips are the existing explicitly environment-gated
physical tests; the new projection tests executed with no skip.

## EW-01 through EW-17 evidence map

- EW-01/13: full existing backend/frontend/contract/delivery/lifecycle suites and all
  three preserved guarded browser tests; no duplicate mutation owner.
- EW-02/03/04: focused provider-fetch/cache-hit/null/fail-closed/old-case immutability
  projection tests and panel fixtures.
- EW-05: unchanged centralized route policy plus full RBAC/safe-404 tests; detailed read
  remains the existing authorized route.
- EW-06/11: backend spies forbid provider/cache/business writes and execution/replay;
  adversarial composition proves local exploration makes zero request/storage changes
  and an explicit refresh remains exactly three GETs with no retry/mutation.
- EW-07/08: exact Decimal, classification, calculation, multiple-path, cycle, long-path,
  hidden-boundary, pagination, shrink, empty, and non-definitive component proofs.
- EW-09: actor/case/analysis-keyed candidate/path remount and selected-ID disappearance
  tests; actor/case-keyed focus-wrapper remount plus synchronously identity-filtered
  notice tests; existing Phase 15C stale-action/query isolation remains green.
- EW-10: closed status/stage/readiness/target mappings, safe verbatim blockers/warnings,
  and unknown-value uncertainty tests.
- EW-12: native keyboard buttons/focus, table alternative, bounded visual, inherited
  identifier wrapping, internal table scroll, and 480px real-browser root-width proof.
- EW-14: actual created clean and review cases under real local login/API/network guard;
  the clean journey operates candidate, path, and explanation focus controls.
- EW-15: no persistence change; ordinary projection checks execute. Local physical Mongo
  is not applicable, while the existing hosted five-suite lane remains acceptance
  evidence after publication.
- EW-16: recursive direct/CLM/zero-touch negative-field/value tests plus separate
  security/privacy review.
- EW-17: current docs identify main `6625835e…`, Phase 16 as merged, this branch as a
  candidate, Camunda as not implemented, and policy/provider questions as unchanged.

## Frozen candidate Git blob manifest

These are canonical Git blob IDs from `git hash-object --path=<path> <path>` in stable
path order. Repository attributes/clean filters are therefore applied; the Windows
working tree reports expected LF-to-CRLF checkout warnings, while the IDs below describe
the normalized content that will be staged. This implementation report is excluded to
avoid a self-referential hash, and the independent reviewer owns/excludes its later QG
report.

```text
d5955a38b845b0ca06d80c4df7d96a57c89c4fd7  .ai-pipeline/001_planner/EVIDENCE_WORKBENCH_PLAN.md
6a928a2825642038197e1d44baaa1d93dfb5a29f  .ai-pipeline/001_planner/OVERNIGHT_EVIDENCE_WORKBENCH_BRIEF.md
bc96318dadd5481028c13676ad2961af73cf3193  apps/backend/app/api_models.py
e4f39eb43e894aa01c6ff3985235e0b3e6779c12  apps/backend/tests/test_evidence_workbench_registry_projection.py
c6037b8f8bc7f6100ae3be7d4b8f528836c66802  apps/frontend/e2e/authenticated-zero-touch.e2e.ts
004a8a58c993ca96de2e595a3c528dd0fb8ddd40  apps/frontend/src/EvidenceWorkbenchIsolation.test.tsx
c8f6cb2f2488ef1b4f0daeef9af3527da231a1df  apps/frontend/src/pages/CaseDetail.tsx
c2226e18e8dfb8c8762f7abc7401b4630cc342c9  apps/frontend/src/pages/CaseStateExplanationPanel.test.tsx
8feb94a854185ed2970f263f25ef7594b03829ff  apps/frontend/src/pages/CaseStateExplanationPanel.tsx
f028f8105d29e088b9043e67db8d4175ca3b79c2  apps/frontend/src/pages/OwnershipPathExplorer.test.tsx
174464898f26bc7277f714a78325eb28cf3e7c79  apps/frontend/src/pages/OwnershipPathExplorer.tsx
48c2244c9ad126dd70ce3ba73167136f3f7387b1  apps/frontend/src/pages/RegistryProvenancePanel.test.tsx
678b3e8c5a6fb5fceda4e79112c37e964cf4b123  apps/frontend/src/pages/RegistryProvenancePanel.tsx
0c75ad18cd23e80a66458c9513487113a8f52fb0  apps/frontend/src/styles.css
511a40fb374b9792935038ca84be308f276b876a  apps/frontend/src/types.ts
280d6afd95af1ca4a5458ec43f1b87cff52950f5  docs/ARCHITECTURE.md
981cd6d2c257fc71e017651b74310efdbd94f285  docs/PROJECT_STATE.md
dff0ebe4308e77ca15b8f53b8257f07c81b3c6bf  docs/contracts/REGISTRY_CACHE_FRESHNESS_PROFILE.md
fdc44a7d4e9659fb4c0ffd29268d5dc7d4319314  docs/demo/EVIDENCE_WORKBENCH_DEMO.md
```

## Evidence limitations and next authorized action

The real browser runner uses its supported default-disabled registry cache composition,
so it truthfully demonstrates the unknown/unrecorded browser state. Provider-fetch and
cache-hit projections are proved at the real service/API and frontend contract layers;
the runner was not modified to enable cache fault/setup behavior. No local physical
Mongo run was required because this increment changes no persistence boundary. Hosted
CI is not yet available because publication must wait for exact independent `PASS`.

Next: submit the remediated frozen content and retained first-gate finding to a fresh
independent quality-gate reviewer, remediate only concrete in-scope findings if any,
then transfer Git ownership to the separate publisher after exact `PASS`. No merge or
next phase is authorized.
