# Case Evidence & Explainability Workbench — independent quality gate

Date: 2026-09-21

Reviewer role: fresh independent final re-quality-gate reviewer; report-only writer

## Executive result

**PASS**

The complete frozen Case Evidence & Explainability Workbench candidate satisfies
EW-01 through EW-17. The first independent gate's required finding, EW-QG-001, is
preserved below and is now resolved: evidence focus wrappers remount at the actor/case
identity boundary, and an unavailable-evidence notice is rendered only for the identity
that created it. Fresh integration execution proves that old focused nodes detach and
old notices disappear synchronously for both case and actor changes, with no request.

The minimized registry projection, backend-authored Decimal ownership explorer, typed
state explanation, authorized access boundary, no-call/no-write behavior, guarded real
browser journey, privacy minimization, and Mock/Local claim boundaries are acceptable.
No current defect, missing required local evidence, false-success claim, or scope breach
remains. This exact candidate is eligible for the separately authorized publication
stage; this verdict does not itself stage, commit, push, create a PR, start CI, merge, or
authorize another phase.

## Reviewed identity and write boundary

- Task: unnumbered Case Evidence & Explainability Workbench.
- Worktree:
  `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-postmerge-fix`.
- Branch: `feature/evidence-explainability-workbench`.
- `BASE_SHA`, current `HEAD`, examined `origin/main`, and merge base:
  `6625835e6ca8b7e531c25b3078c3ff58ee4df843`.
- Source revision: the branch remains at the base commit; the candidate is the unstaged
  working-tree content identified below.
- Behavioral evidence revision: the same 20-path normalized content manifest below.
  Tests and browser execution did not change any reviewed source blob.
- Independently reviewed content: the same 20 paths, including the implementation
  report. The quality-gate report is excluded from its own identity.
- Index: empty. No implementation file was staged or committed during this re-gate.
- Reviewer write boundary: exactly this report. No implementation, test,
  configuration, ordinary documentation, Git index, branch, remote, PR, or CI state was
  changed.
- Preflight available in this session: Python 3.12.10 and the repository `.venv`, Node
  22.23.2/npm 10.9.8, installed frontend dependencies, local Playwright Chromium,
  PowerShell process control, and the guarded loopback runner. No database/container was
  needed because the candidate changes no persistence boundary.

### Frozen reviewed paths and normalized Git blob identities

All 20 values were recomputed with `git hash-object --path=<path> <path>` before and
after independent execution. They matched the implementation manifest, except that the
implementation report is intentionally hashed independently here.

```text
d5955a38b845b0ca06d80c4df7d96a57c89c4fd7  .ai-pipeline/001_planner/EVIDENCE_WORKBENCH_PLAN.md
6a928a2825642038197e1d44baaa1d93dfb5a29f  .ai-pipeline/001_planner/OVERNIGHT_EVIDENCE_WORKBENCH_BRIEF.md
f13e889993e79a4872457fa5f27b808c2032c154  .ai-pipeline/reports/EVIDENCE_WORKBENCH_IMPLEMENTATION.md
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

Expected Windows LF-to-CRLF checkout warnings do not change these normalized Git blob
identities.

## Preserved first-gate FAIL and remediation history

The first fresh independent gate reviewed the pre-remediation content and returned
**FAIL**. Its two subsequently changed source blobs were:

```text
9cbdeb970a7b4d7cc8ab490f4ab59e28fbd8cb9b  apps/frontend/src/EvidenceWorkbenchIsolation.test.tsx
a9482c7086e818e0037b253971a0f1a63d710ceb  apps/frontend/src/pages/CaseDetail.tsx
```

Finding **EW-QG-001 — case focus identity is not remounted (medium, required)** stated
that the focusable evidence wrappers were reused across case identity, so an element
focused in case A could remain the active element when case B rendered. The
unavailable-evidence notice was cleared only in a post-commit effect and could therefore
appear once under the replacement identity. The first gate classified this as an
EW-09/frozen-plan violation and publication blocker, while explicitly noting that it
was not a backend data leak. All other EW criteria passed that first gate.

The bounded remediation changed only `CaseDetail.tsx` and
`EvidenceWorkbenchIsolation.test.tsx`:

- every registry, document, reconciliation, ownership, and recovery focus wrapper now
  has a key derived from actor/case identity, so a case or actor change causes React to
  unmount the old DOM node rather than reuse it;
- the unavailable notice carries the actor/case identity that created it and is not
  rendered unless it equals the currently rendered identity; and
- the new integration regression focuses case A, creates its unavailable notice, then
  renders case B and actor B, proving the old nodes are detached, focus does not remain
  on the old evidence target, stale notices are absent synchronously, and `fetch` is not
  called.

The remediation does not use a timeout, steal focus on an ordinary same-case update,
change routing/auth/query ownership, persist browser state, add a request, or broaden
the product scope. The current normalized blobs are `c8f6cb2f...` and `004a8a58...`, as
recorded in the frozen manifest.

## EW-01 through EW-17 acceptance checklist

| ID | Result | Direct evidence |
|---|---|---|
| EW-01 | PASS | `CaseDetail` retains existing document, reconciliation, recovery, priority, deletion, submission-plan, metrics, and timeline owners. The guarded three-journey browser suite and full frontend suite pass. |
| EW-02 | PASS | The explicit seven-field provider-fetch/cache-hit projection and registry panel preserve retained dispositions and exact timestamps. Focused backend and panel tests pass. |
| EW-03 | PASS | A null binding remains null/unknown and causes no cache lookup or persistence rewrite; focused source and execution verify this. |
| EW-04 | PASS | The backend regression proves a later shared cache refresh does not alter the earlier case projection. |
| EW-05 | PASS | Existing backend authorization and safe-404 owners are unchanged; the two selected cross-team/absent tests pass. |
| EW-06 | PASS | Detailed-GET spies prohibit provider/cache/business writes and execution/replay. Local exploration and focus tests issue no request or storage change; the browser request delta is empty. |
| EW-07 | PASS | Decimal percentages, calculation, threshold/comparator/result, classifications, and issues are rendered unchanged from backend strings, with no frontend ownership arithmetic. |
| EW-08 | PASS | Multiple/long paths, bounded prefix/suffix, hidden-edge disclosure, pagination, cycles/incomplete/limit warnings, and non-completeness wording are source-confirmed and tested. |
| EW-09 | PASS | Actor/case keys remount all focus wrappers; analysis identity remounts explorer selection. The new regression proves case and actor changes detach old focused nodes and suppress old notices synchronously with zero requests. Phase 15C stale callback/query isolation remains green. |
| EW-10 | PASS | Typed automation/stage/readiness/target wording, escaped server-authored blockers/warnings, retained operation order, and visible unknown fallbacks pass focused tests. |
| EW-11 | PASS | Explicit refresh remains exactly the three existing GETs with no automatic retry/mutation and truthful unconfirmed-refresh wording. |
| EW-12 | PASS | Native buttons and focus targets, table alternative, bounded visual, 20-row pagination, 480 px layout, and internal table scrolling pass focused/browser checks. |
| EW-13 | PASS | Full frontend 234/234, selected RBAC/backend tests, 44/44 contracts, 4/4 delivery checks, and all three guarded login/onboarding/review/routing journeys pass. Frozen implementation evidence also records backend 1,042/1,042 executed and lifecycle 23/23. |
| EW-14 | PASS | Fresh guarded execution used Chromium, real local login, local APIs, Vite proxy, tracked synthetic fixtures, and the network guard; 3/3 passed in 9.4 seconds. |
| EW-15 | PASS / locally not applicable | No persistence model/schema/CAS/read-compatibility path changed. New projection tests execute without skip. A new local physical Mongo run is not required; the standard hosted five-suite lane remains a post-publication CI obligation. |
| EW-16 | PASS | Recursive direct/CLM/zero-touch negative assertions exclude forbidden cache/internal fields and values. The independent secret scan passes, and the UI creates no links or raw HTML surface. |
| EW-17 | PASS | Current docs distinguish main `6625835e...`, accepted Phase 16, this unaccepted feature candidate, no Camunda runtime, unchanged provider classifications, and unresolved Q-001 through Q-018. |

## Contract and integration findings

No active contract or integration finding remains.

The API change is one additive nullable projection on the existing authorized case
response. It is constructed explicitly, is limited to seven fields, and fails closed
for a non-Mock retained binding. It does not expose cache IDs/keys/digests, revisions,
write/anchor times, dataset/contract identity, fingerprints, endpoints, repository
details, raw payloads, or new arbitrary links. Existing registry operation provenance
remains separate from case-use evidence. Null means unknown/unrecorded; it does not mean
miss, disabled cache, provider fetch, freshness, or current validity.

The UI does not evaluate freshness against the current clock, query shared cache state,
call a provider, reassess an older case, or turn the 7,776,000-second provisional Mock
interval into ACRA/compliance validity. Ownership uses only retained backend paths and
the domain's owned-entity-to-owner direction. It performs no multiplication,
aggregation, threshold comparison, cycle resolution, or candidate selection. Target
status remains ordered and ledger-authored, with no replay or new action owner.

No endpoint, case/cache schema, repository, persistence mode, connector, provider mode,
business mapping, sponsor decision, dependency, Camunda runtime, Live integration, or
production identity claim changes.

Current later dependencies remain separate from this gate: Q-001 through Q-018 remain
open as documented; real ACRA/GoldTier/PingFed, production OCR/SSO, legal UBO authority,
Ready-for-Approval, and production retention/reviewer policy remain unimplemented or
unconfirmed. They do not block this bounded read-only Mock/Local POC increment.

## Tester and adversarial findings

Fresh independent commands on the frozen content:

- `.venv\Scripts\python.exe scripts\dev_context.py` — PASS; branch, HEAD, main,
  provider classifications, and current tracked/untracked set matched the handoff.
- `git hash-object --path=<path> <path>` over the 20 reviewed paths — PASS, 20/20,
  before and after execution. The implementation report independently hashes to
  `f13e889993e79a4872457fa5f27b808c2032c154`.
- Focused backend projection plus the two safe-404/RBAC selectors — 8 passed; only two
  dependency deprecation warnings.
- First sandboxed focused Vitest launch — failed before collection with `spawn EPERM`
  while starting the pinned esbuild helper. The identical command through the supported
  process-approval path passed. This is recorded as an environment precondition failure,
  not product evidence.
- Workbench isolation plus Phase 15C navigation — 41/41 passed across two files.
- Registry, ownership, and state-explanation component tests — 17/17 passed across
  three files.
- Full frontend suite — 15 files, 234/234 passed; existing React Router SSR
  `useLayoutEffect` warnings only.
- Frontend typecheck — PASS.
- Frontend production build — PASS; 112 modules transformed.
- Focused Ruff — PASS. Backend mypy — PASS across 94 source files.
- Contract suite — 44/44 passed. Delivery-asset suite — 4/4 passed.
- `check_project_state.py`, `check_architecture.py`, `check_tooling_config.py`, and
  `check_secrets.py` — PASS.
- Guarded browser runner on ports 8871/4281 — 3/3 passed in 9.4 seconds. The successful
  journey uses real local login/API calls and tracked synthetic fixtures, exercises
  candidate/path/explanation controls, checks no interaction request/storage delta,
  verifies focus, and verifies the 480 px layout and internal table scroller.
- `git diff --check` — PASS. Every task-owned new file checked has a final LF, no
  trailing whitespace, and no conflict marker.

The re-gate did not repeat the full backend suite, Windows lifecycle suite, or physical
Mongo runner. The implementation report records, against the same frozen candidate
apart from the later frontend-only EW-QG-001 remediation, backend 1,042 executed/passed
with 22 explicit physical-test skips and lifecycle 23/23. The final remediation was
then covered by fresh focused/full frontend, typecheck, build, and real-browser
execution. Physical Mongo is not applicable locally because neither the original
candidate nor remediation changes persistence/schema/CAS/read compatibility. Hosted CI
does not exist before publication and remains a later publisher/CI evidence lane.

## Code and architecture review

No active code or architecture finding remains.

The implementation stays within the existing response, query, authorization,
ownership, workflow, and target-ledger owners. Three prop-only presentation components
and one explicit browser projection are a bounded split. The selected-path visual is
bounded and does not reconstruct a graph or perform domain arithmetic. Existing
mutation controls remain their sole owners.

EW-QG-001 is correctly repaired by React identity semantics: changing the actor or case
changes each wrapper's sibling key, causing React to remove the old DOM node and mount a
new one. The browser therefore cannot retain the old focused element. The notice is
tagged with the same identity and the render condition excludes it under a replacement
identity before any effect is needed. Analysis changes remount only the local ownership
explorer, so they reset candidate/path selection without stealing section focus or
remounting the entire case page. The regression directly exercises both case and actor
changes and retains the no-request assertion.

The former static ownership/readiness presentation is coherently replaced. No second
calculation, readiness, authorization, persistence, workflow, cache, or target-action
owner is introduced. No ADR is required because no canonical owner or dependency
direction changes.

## Security review

No active security or privacy finding remains.

The new projection contains only browser-required case-use facts and fixed provisional
policy metadata. Credentials, tokens, headers, private endpoints, raw provider bodies,
raw document content, cache identity/key/revision/write/anchor/fingerprint details,
repository details, and ownership source references are not newly projected. React
text escaping is used; there is no `dangerouslySetInnerHTML`, arbitrary source link,
new export, persistent browser storage, service worker, QueryClient, or frontend
authorization owner.

The selected backend tests retain indistinguishable inaccessible/absent 404 behavior.
Detailed-GET spies and frontend request/storage assertions support no-write/no-provider-
call/no-analysis-execution/no-target-replay claims. EW-QG-001 was interaction-state
isolation rather than a server-data disclosure; its corrected actor/case remount closes
that accessibility and identity boundary without changing authentication or routing.

Mock, Local, Partial, Dormant, and not-implemented labels remain explicit. No result is
presented as Live, legal UBO identification, compliance approval, customer approval, or
Ready-for-Approval.

## Findings and required fixes

- Historical finding EW-QG-001: **resolved** by the bounded remediation and fresh
  re-execution described above.
- Current findings: none.
- Required fixes before publication: none.
- Accepted limitations: browser acceptance uses the default-disabled registry cache and
  therefore shows unknown/unrecorded binding; provider-fetch/cache-hit projection is
  proved at backend/API and frontend contract layers. No production host history
  fallback, Live provider, or hosted CI evidence is claimed.

## Readiness

Publication readiness: **READY FOR THE SEPARATE PUBLISHER** for this exact 20-path
reviewed candidate plus this report. The publisher must independently verify the
accepted blob identities, stage only task-owned paths, fetch and assess latest-main
drift, run the clean committed-tree pre-PR check/checklist, push, create or update the
single PR, and report both push and pull-request CI. Any implementation-content change
or material integration change requires a fresh independent check. Human owners retain
merge authority.

No next product phase is authorized. This PASS does not establish Live ACRA, PingFed,
GoldTier, vendor OCR, production SSO, Camunda runtime, legal UBO determination,
compliance approval, Ready-for-Approval, production cache/retention policy, or sponsor
resolution of Q-001 through Q-018.

## Git and resource status

At re-gate completion, branch `feature/evidence-explainability-workbench`, `HEAD`, and
`origin/main` remain at `6625835e6ca8b7e531c25b3078c3ff58ee4df843`. The candidate is
unstaged and uncommitted; the index is empty. No fetch, branch switch, merge, rebase,
reset, stash, clean, commit, push, PR edit, CI action, implementation remediation, or
next-phase action occurred during this review. The reviewer changed only this report.

The guarded backend, frontend, and Chromium processes were cleaned up. Ports 8871,
4281, 8000, and 5173 were all free at closeout. The ignored `.runtime` directory
contains pre-existing `.log` artifacts only and no active runtime manifest. No task
container or disposable database was created.

## Final verdict

**PASS**
