# Phase 07 Final Lifecycle Remediation Report

**Remediation date:** 2026-08-15

**Branch:** `phase/07-sponsor-uat-integration`

**Base HEAD:** `400d4e63ab86c7764b5e1fcfe548313124565d22` plus the intentionally unstaged Phase 07 worktree

**Implementation-side result:** READY FOR FINAL INDEPENDENT PHASE 07 CLOSURE GATE

**Independent gate authority:** `PHASE_07_QUALITY_GATE.md` remains the historical
**FAIL**. This report neither edits nor supersedes that gate and does not claim an
independent PASS.

## P07-QG-001 disposition

The final bounded remediation makes lifecycle state completeness a pre-termination
invariant. A `RUNNING` session is valid only with exactly two records: one lowercase
`backend` and one lowercase `frontend`. Missing, duplicate, differently cased, or
unknown roles raise `DEMO_RUNTIME_STATE_INCOMPLETE` during state read, before process
identity checks or any `taskkill` call. Stop returns nonzero, retains the state, does
not print session-wide success, and does not infer ownership from port occupation.

`STARTING` is modeled separately. It may contain backend only or exactly backend plus
frontend. Its partial state cannot satisfy the `RUNNING` invariant. Both state writes
and reads apply the status-specific structural validation.

For a complete `RUNNING` session, Stop still validates both recorded launcher/listener
identities using PID, creation time, executable, fixed role command evidence,
descendant relationship, and expected port before terminating either tree. It then
waits for both owned trees and listeners and requires both expected ports to be free
before deleting metadata or reporting backend/frontend success. A fully stale complete
record may clear only when both recorded identities are absent and both ports are free.

Reset remains verified Stop followed by Start. Any incomplete/corrupt-state Stop
failure returns nonzero, retains the same session metadata, and prevents replacement
backend/frontend launch.

## Executed Windows evidence

The final Windows lifecycle suite passed **13 tests in 144.301 seconds**. Repository
discovery reran the same cases and passed **71 tests in 145.219 seconds**. The matrix
covered:

- normal healthy Start and verified Stop;
- normal process-local reset, new session, and old-case `200 -> 404`;
- unrelated Python, Node, and differently titled cmd survival;
- occupied backend and frontend ports, both nonzero with occupants preserved;
- complete-state ownership mismatch, nonzero with metadata retained and no reset start;
- complete state with fully nonexistent PIDs, safely cleared when both ports were free;
- missing frontend and missing backend Stop, both rejected before termination;
- missing frontend and missing backend Reset, both rejected without a new session;
- duplicate backend, duplicate frontend, backend+frontend+unknown, and unknown-only role
  sets, all rejected before process selection;
- backend-only `STARTING` state handled as partial startup rather than valid `RUNNING`;
- `START -> STOP -> START -> RESET -> STOP`, all expected exits `0`.

The two exact manual gate reproductions each started a healthy two-role session, removed
only one role, and ran Stop. Missing frontend and missing backend both produced:

`STOP_EXIT=1`, `RETAINED=True`, `SESSION_UNCHANGED=True`, backend `200`, frontend `200`,
and `DEMO_RUNTIME_STATE_INCOMPLETE` with no false success. Exact original metadata was
then restored and normal Stop removed both launcher-owned trees.

The manual normal sequence also passed:

- first Start/Stop: exits `0/0`, both endpoints `200` before Stop;
- second Start: session `c03bc388-f19d-44a2-b23a-96d2d785e45d`;
- Reset: exit `0`, new session `123a11dd-4e9a-44dc-935e-15a000bb1c50`;
- synthetic case before/after Reset: HTTP `200/404`;
- final Stop: exit `0`.

Final runtime audit found no state file and no listener on ports 8000 or 5173.

## Preserved closures and functional behavior

P07-QG-002 remains closed: all server-provided blocker codes render in first-seen server
order, including UAT-04 before and after narrow resolution. P07-QG-003 remains closed:
`APP_NAME=Zero-Touch CLM API` matches settings, `.env.example`, and the configuration
reference. Launcher Python/Node/npm/import/Vite/dependency preflight remains enforced.

Explicit UAT smoke passed four tests:

- UAT-01: `COMPLETED / MOCK_GOLDTIER_SUBMITTED`, interventions `0`, target sequence
  `SEARCH -> SHELL -> POLICY -> AMEND` once;
- UAT-02: source conflict paused, one permitted intervention auto-resumed, interventions
  `1`, same target sequence once;
- UAT-04: source conflict plus low confidence remained visible and target calls were
  empty; frontend regressions preserve order and the post-resolution low-confidence-only
  state;
- UAT-11: `RECOVERY_PENDING` finalized with the unchanged target-call prefix and no
  replay.

No orchestration, provider contract, document/ownership rule, Phase 05 recovery,
evidence export, live connector, approval behavior, or later phase changed.

## Complete validation

- full backend: **494 passed** (one upstream Starlette/httpx deprecation warning);
- focused Phase 01–07: **28 / 81 / 59 / 77 / 61 / 179 / 16 passed**;
- explicit UAT-01/UAT-02/UAT-04/UAT-11 smoke: **4 passed**;
- Windows lifecycle: **13 passed**; repository discovery: **71 passed**;
- contract discovery: **44 passed**;
- frontend typecheck, **35 tests**, production build (29 modules), and `npm ls --all`
  passed; only expected platform/feature optional packages were absent;
- Ruff, strict mypy (54 source files), and `pip check` passed;
- secret tests **5 passed**, standalone secret scan passed, and no tracked private file;
- GoldTier validator tests **5 passed**; classification remained 19 valid / 19
  invalid-quarantined / 48 not validated; strict mode returned expected exit `1`;
- PowerShell parser, tracked/cached whitespace, explicit untracked whitespace/final
  newline, and final runtime checks passed.

## Dependencies and next action

No sponsor question changed. Q-001–Q-014 and D-018/D-023–D-026 remain applicable.
They block live/final policy claims, not this bounded Mock lifecycle correction.

Recommended next human action: run the final independent Phase 07 closure gate with
the exact missing-frontend/backend Stop and Reset reproductions. Do not begin another
phase. No file was staged, committed, pushed, or merged.
