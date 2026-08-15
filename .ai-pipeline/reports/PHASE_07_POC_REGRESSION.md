# Phase 07 POC Regression Check — Final Lifecycle Remediation

**Check date:** 2026-08-15

**Result:** PASS

**Scope:** implementation-side regression rerun after the independent Phase 07 Quality
Gate **FAIL**. This is not an independent re-gate.

## Lifecycle regression matrix

| Scenario | Actual result | Prohibited behavior verified |
|---|---|---|
| Healthy Start | complete `RUNNING` role set; backend/frontend 200 before exit 0 | no incomplete promotion or premature success |
| Normal Stop | both exact trees/listeners gone, ports free, metadata removed, exit 0 | no window-title/name/port-owner kill |
| Normal Reset | session changed; old case 200 then 404; new endpoints 200, exit 0 | no file deletion or retained process-local case |
| Missing frontend record | `DEMO_RUNTIME_STATE_INCOMPLETE`, exit 1, same metadata/session, both endpoints 200 | no partial kill, metadata deletion, false success, or port guess |
| Missing backend record | symmetric exit 1/retention/both endpoints 200 | no partial kill, metadata deletion, false success, or port guess |
| Reset missing frontend/backend | Stop stage exit 1; same session/state; no replacement launch | no Start after failed Stop |
| Duplicate/unknown roles | duplicate backend, duplicate frontend, complete+unknown, and unknown-only rejected | no process selection before structural validation |
| Partial `STARTING` | backend-only stale startup state handled separately | no treatment as complete `RUNNING` session |
| Ownership mismatch | exit 1; unrelated Python survives; metadata retained | no kill and no reset start |
| Fully stale complete state | nonexistent PIDs and free ports clear safely | no arbitrary process selection |
| Occupied 8000/5173 | Start exit nonzero; each owner survives; no state created | no port-owner termination or false session |
| Unrelated processes | Python, Node, and differently titled cmd survive normal Stop | no broad process selection |
| Repeated lifecycle | `START -> STOP -> START -> RESET -> STOP` all exit 0 | no stale metadata, listener, or orphan |

The executed Windows suite passed **13 tests**; repository discovery passed **71 tests**.
The exact manual missing-role reproductions matched the independent gate sequence and
returned exit `1` while retaining both healthy services until exact-metadata cleanup.

## Functional/UAT catalogue

All accepted Phase 01–06 and Phase 07 UAT outcomes remain unchanged. Explicit smoke:

| UAT | Actual terminal behavior | Calls/interventions |
|---|---|---|
| UAT-01 | `COMPLETED / MOCK_GOLDTIER_SUBMITTED` | search/shell/policy/amend once; interventions 0 |
| UAT-02 | source conflict pauses, permitted registry retention auto-resumes to completion | same target sequence once; interventions 1 |
| UAT-04 | source conflict plus low confidence retained; after narrow resolution only low confidence remains | zero target calls while blocked; no unsupported action |
| UAT-11 | `RECOVERY_PENDING` then completed reconciliation | target prefix unchanged; no replay |

Required-stage failures still stop downstream connectors; only explicit GoldTier
`NO_MATCH` permits shell creation; business review, technical failure, partial target
outcomes, and completion remain separate. `COMPLETED / MOCK_GOLDTIER_SUBMITTED` remains
a credential-free synthetic POC result, never approval, Ready-for-Approval, or live
interoperability. Evidence export, profile labels, demo gating, provider seams, and case
isolation remain unchanged.

P07-QG-002 is preserved by the 35-test frontend suite: every server blocker is rendered
in first-seen server order before and after narrow UAT-04 resolution. P07-QG-003 and
launcher preflight are preserved by delivery/configuration tests and real Start output.

## Verification evidence

- backend 494; focused Phase 01–07: 28 / 81 / 59 / 77 / 61 / 179 / 16;
- explicit UAT smoke 4; contract discovery 44;
- Windows lifecycle 13; repository discovery 71;
- frontend typecheck, 35 tests, production build, and dependency tree passed;
- Ruff, strict mypy, `pip check`, secret tests/scanner, GoldTier validator/classification,
  PowerShell parse, whitespace, private-file, and final runtime checks passed.

The canonical catalogue was evolved only for the assigned and executed complete-role
`RUNNING` invariant and missing/duplicate/unknown-role fail-closed behavior. No UAT
business outcome, sponsor contract, provider behavior, open question, or live claim was
changed. The independent Phase 07 Quality Gate remains historical **FAIL** pending a
separate final closure gate.
