# AM-03 Search-stage workspace correction

Owner-assigned bounded task, 2026-10-14 (Asia/Singapore). Candidate starts from
freshly fetched main `a497793be2615306bc7cfbd3104fd4352dead96d` in
`C:/Users/shane/Desktop/FYP/am03-1014-2214`, branch
`feat/am03-search-stage-20261014-2214`. This is an unmerged local candidate;
acceptance belongs to its fresh independent gate, not this implementer document.

## Scope and owner

Change class: FRONTEND_UI. CaseDetail owns stage placement and view focus. The
reported source grouped REGISTRY and GOLDTIER_SEARCH interventions under Registry
verification. Decision: code-change; the workspace owner must separate that grouping.
The owner assignment is the implementation plan. RED/GREEN is explicitly required.
No architecture review/ADR is required: owners and dependency direction are unchanged.

Only CaseDetail.tsx, the new AM03SearchStage.test.tsx, this document, and the assigned
independent gate report are intended tracked changes. Existing tests, shared.ts,
CaseStatePanels.tsx, design-system.css, ManualOwnershipEvidenceForm,
BlockerDecisionReview, existing E2E files, and tests/test_run_e2e.py remain read-only.
The primary checkout and PR85 worktree are not implementation locations.

## Behavior

Existing-customer search is a separately labelled workspace region with an h2. It uses
existing card/focus styling and stays visible; this adds no progressive-disclosure
redesign. Search-owned interventions and the existing read-only Search diagnostic move
here. Registry interventions, acquisition, corporate particulars and provenance remain
in Registry verification. The seven existing disclosures and their order are retained.

The single identity editor follows projected IDENTITY ownership and OPEN exceptions.
A genuine Registry correction, Registry-owned identity action or document UEN conflict
keeps it in Registry. A Search-owned identity action can place it in Search. A Search
navigation control reaches a Registry-owned recheck/correction when appropriate.
Endpoint selection is the existing identitySearchRecheck predicate, unchanged.
Automation/CLM/event versions, document binding/choices, cache effects, authorization,
submission freezing and existing-customer rationale/target identity are unchanged.

Search attention and pipeline navigation use the existing guarded focus owner. Candidate
confirmation reaches its rationale; declared identity actions reach the single editor.
The accepted failed-Search pipeline can still reach Registry correction. Denied or
missing inputs retain truthful feedback. Navigation, expansion and focus never submit.
The compact Search summary reports retained checkpoint status, or explicitly says no
result is retained. Missing evidence does not imply a match, absence or permission.

Changes: frontend rendering, accessibility and view focus/runtime placement only.
API/shared types, durable schema, connectors, configuration/dependencies, business rules,
mappings, auth/security semantics, architecture owners, provider status and backend
runtime behavior are unchanged. Mock/Local/Partial remain distinct from Live.

## Verification and resource preflight

Python 3.12.10, Node 22.23.3, npm 10.9.9; locked frontend dependencies installed in this
worktree, with task-owned npm cache. Vitest 3.2.4, Vite 7.1.11 and Playwright 1.56.1 are
from the existing lockfile. No lockfile or dependency definition changes.
Filesystem writes to this sibling require tool-reviewed escalation, which was granted.
Relevant process inventory and free ports 8893/4293 were inspected before probes.

The three original focused grouping tests failed on main due to the absent Search
heading, then passed with the correction. A separate failed-Search focus regression
caught and corrected a candidate change from UEN focus to diagnostic focus. Task tests
cover coexistence/single editor, endpoint/version payloads, four wrong-UEN codes,
EXISTING_REUSED rationale, direct/attention/pipeline focus, denied authority, absent/
failed/completed evidence, completed case, actor/case/version cancellation and refresh.
The existing 47-test EvidenceWorkbenchIsolation suite preserves affected PR82/83/84
navigation/document/currentness behavior. Final fresh commands/results are recorded in
the independent gate and ignored `tmp/am03/` logs.

Three temporary authenticated Playwright probes executed on distinct owned processes:
wrong-UEN Registry, offline existing-customer candidate and initial-identity Search
recheck. They use the configured Playwright settings/network containment, overriding
only test discovery to the task-owned ignored probe directory. The tracked canonical
inventory, selector budgets, runner, CI counts and tags are untouched.
The harness reuses tracked process/port/readiness utilities with exact owned-PID cleanup;
it does not invoke an unfiltered E2E runner. Real HTTP/auth is used with memory and
synthetic Mock/offline protocol fixtures; no external calls, Docker or Mongo.
Desktop 1280px and mobile 360px, native Enter, headings/regions, Registry disclosure,
Search candidate placement, rationale, reload equality of retained case/versions/
exceptions/target ledger, and absence of navigation mutations are checked. Observation
times naturally advance on GET and are excluded from durable-state equality.
Deliberate customer confirmation makes no target call; initial-identity recheck calls
the unchanged version-bound endpoint with non-Search target rows NOT_ATTEMPTED.

Ignored probe artifacts: apps/frontend/tmp/am03-probe/, tmp/am03/probe.py, logs under
tmp/am03/, screenshots under tmp/browser-evidence/. These are local evidence, not new
permanent Playwright selectors. Earlier probe failures were observation/setup defects
(dynamic GET timing, clean document with no pending fields, repeated disclosure toggle);
only the final successful runs supply browser evidence. Existing React act/flushSync and
production chunk-size warnings remain disclosed, not suppressed.

## Independent review and integration boundary

Fresh review must read exact base, full diff/new files, evidence and adverse paths, run
focused checks, and write only .ai-pipeline/reports/AM03_SEARCH_STAGE_QUALITY_GATE.md.
No self-approval. Exact independent PASS plus all required local checks is the condition
for the authorized scoped local commit and clean committed pre-PR check.

No push, PR, merge, publication, PR85 integration or next AM feature is authorized now.
After PR85 is manually merged, the next owner/planner assignment must authorize latest-
main integration, reconcile browser inventory, add durable authenticated AM-03 coverage,
rerun affected evidence and independently accept the changed integrated content.
Future browser regression should retain: stage ownership/coexistence, shared-editor
endpoint/evidence binding, candidate rationale and same target ID, Search recheck versus
Registry correction, denied authority, navigation with zero target/review mutations,
refresh/case/actor stale-focus safeguards, keyboard/disclosure and narrow-width layout.

Full backend, physical Mongo, unfiltered E2E, production hosting and external provider
interoperability are not executed/certified by this bounded frontend task. PR85's release
verification remains independently owned. Preserve this worktree until separately
authorized integration/publication and human merge; do not remove other artifacts.
