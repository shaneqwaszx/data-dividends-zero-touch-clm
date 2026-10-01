# Garden ownership trace and recovery truth

Bounded continuation, 2026-10-01. Branch `fix/demo-happy-path-stabilization`;
HEAD/base/local `origin/main` `efc31f450f0103766fa812bc0aa80754f801dbe9`.
The accepted uncommitted candidate and preceding reports were retained. Index empty;
no branch, worktree or Git metadata mutation. Configured session model, no escalation;
the provider's exact model identifier is not exposed by the available tools.

## Root cause and boundaries

Garden has **explicitly empty upstream ownership** in the accepted offline Marketplace
protocol, not decoding, mapping or API loss. The existing frontend described absent
candidates generically and lacked a clear registry-gap explanation and recovered-party
table. A separate adverse check found domain declaration validation escaping the API as
a server error; the request-conversion boundary now returns a fixed, sanitized 422.

Reproduction preceded edits through the normal authenticated application, memory
persistence, offline Marketplace and local PDF intake. No direct database shortcut.
`tmp/GARDEN_OWNERSHIP_TRACE_REPRODUCTION.json` preserves the original trace;
`tmp/GARDEN_OWNERSHIP_TRACE_FINAL_PROOF.json` adds the intelligence/frontend evidence
and corrects the original trace's imprecise blocker-family label.

| Boundary | Result | One-line evidence |
|---|---|---|
| Offline Marketplace response | EXPLICIT_EMPTY | HTTP 200 with explicit `entities: []` for shareholders. |
| Connector transport | EXPLICIT_EMPTY | Injected offline transport returns the empty response without external HTTP. |
| Connector decoder | EXPLICIT_EMPTY | Strict decoding succeeds with zero ownership parties, not an error. |
| Source DTO | EXPLICIT_EMPTY | Empty ownership tuple retains MOCK provenance and retrieval time. |
| Canonical registry evidence | EXPLICIT_EMPTY | `OWNERSHIP_PARTIES: EMPTY`, count 0; identity retained, no fabricated edges. |
| Registry ownership provider | EXPLICIT_EMPTY | Retains root legal entity only, with no owner relationships. |
| OwnershipAnalysisService | PRESENT | `REVIEW_REQUIRED`, `INCOMPLETE_LEGAL_ENTITY`, threshold 25, error null. |
| Orchestrator/readiness | PRESENT | Active `OWNERSHIP_INCOMPLETE`; CLM `OWNERSHIP_REQUIRED` family remains actionable. |
| Case/ownership API | PRESENT | Normal GETs preserve EMPTY operation and the ownership analysis record. |
| Intelligence API | PRESENT | Authenticated projection has no UBO advice when retained candidates are empty. |
| Frontend query/cache | PRESENT | Browser reads authoritative ownership/intelligence; guarded publication tests pass. |
| Garden ownership UI | PRESENT | Before: generic candidate absence; after: clear gap and LOCAL recovery table. |
| Registry relationship acquisition | NOT_APPLICABLE | Marketplace relationship route is unsupported; no dispatch or inferred percentages. |

The named prior authorized observation in
`OFFICIAL_ACRA_GARDEN_VERIFICATION_REPORT.md`, section 6, also records HTTP 200/EMPTY
shareholders. That historical observation is not a fresh external call and does not
prove complete ownership, no UBOs, or current Live capability.

## Result and provenance

Registry availability now says identity retrieved and ownership unavailable from current
registry evidence. Failed, unsupported, unattempted and missing states remain distinct.
The active intervention explains the current ACRA ownership gap and retains the existing
structured-details/upload actions and owning validation.

After valid 60/40 input, the existing owner persists bound LOCAL manual evidence, runs
the existing Decimal engine, classifies both candidates at the frozen >=25 threshold,
resolves the ownership exception into history and automatically advances to the next
genuine blocker. The same screen shows owned entity, owner, supplied identifier, exact
direct percentage, source and UBO analysis. Client evidence explicitly says LOCAL,
not ACRA-derived and not independently verified. Original registry EMPTY remains a
neutral source fact; the active ownership-required banner disappears. No reload,
Analyze button, generic Continue or new mutation/cache owner was introduced.

## Delta and change classes

Current-task source/test delta: nine paths, recorded against the task-start accepted
candidate in `tmp/GARDEN_OWNERSHIP_TRACE_DELTA.diff`:

- Backend `app/api_models.py`, `app/main.py`,
  `tests/test_zero_touch_exception_remediation.py`.
- Frontend `src/pages/CaseDetail.tsx`, `OwnershipPathExplorer.tsx` and its test,
  `RegistryProvenancePanel.tsx` and its test; `e2e/zero-touch-exception.e2e.ts`.

Classes: BACKEND_API and FRONTEND_UI, plus this documentation. API error/projection
text and frontend component prop changed; shared JSON types/statuses unchanged.
Runtime presentation and invalid-input response changed. Schema, repository/CAS,
connector, configuration, business rules, target mapping, auth/RBAC, architecture,
provider classification and Decimal engine unchanged. Existing cache publication,
session isolation, revision guards and no-retry semantics retained.

## Verification evidence

Failing-first logs preserve absent UI/explanation assertions, and the later duplicate
declaration server-error reproduction. Those failures are resolved by the named owning
boundaries, not weakened validation. Rejected percentages, duplicates and missing
rationale return 422; duplicate/metadata errors do not echo party names and do not
change automation version, active/history exceptions or current stage.

| Lane | Current result | Evidence under `tmp/` |
|---|---|---|
| Normal-path trace | PASS; 0 external/0 Mongo calls | `GARDEN_OWNERSHIP_TRACE_FINAL_PROOF.json` |
| Ownership/registry/orchestration/readiness backend | 346 passed, 1 existing warning | `GARDEN_OWNERSHIP_TRACE_BACKEND_FINAL.log` |
| All frontend, including held/stale publication | 392 passed / 33 files | `GARDEN_OWNERSHIP_TRACE_FRONTEND_ALL.log` |
| Garden clean and conflict browser | 2 passed; focus, busy, immediate replacement/history | `GARDEN_OWNERSHIP_TRACE_BROWSER_FINAL.log` |
| Golden browser | 1 passed; 0 exception interventions, 1 confirmation, COMPLETED | `GARDEN_OWNERSHIP_TRACE_GOLDEN_FINAL.log` |
| Contracts | 44 passed | `GARDEN_OWNERSHIP_TRACE_CONTRACTS.log` |
| Ruff | PASS, backend/scripts/tests | `GARDEN_OWNERSHIP_TRACE_RUFF_FINAL.log` |
| Strict mypy | PASS, 112 source files | `GARDEN_OWNERSHIP_TRACE_MYPY.log` |
| Frontend typecheck/build | PASS | `GARDEN_OWNERSHIP_TRACE_TYPECHECK.log`, `GARDEN_OWNERSHIP_TRACE_BUILD.log` |
| Architecture/secrets | PASS | `GARDEN_OWNERSHIP_TRACE_ARCHITECTURE.log`, `GARDEN_OWNERSHIP_TRACE_SECRETS.log` |
| Project state | Existing baseline FAIL: verified SHA unreachable from local origin/main | `GARDEN_OWNERSHIP_TRACE_PROJECT_STATE.log` |
| Retained GoldTier fresh-process read | PASS; unchanged raw document hash, 0 mutations | `GARDEN_OWNERSHIP_TRACE_LEDGER_PROOF.json` |

Garden screenshots are retained under `tmp/zero-touch-browser/1790836137078`.
One ownership POST plus three dependent evidence GETs; focus alone makes zero requests.
Golden remains its existing Mock STP demonstration. Neither browser claims external
provider approval or Sandbox acceptance.

## Preservation, limits and independent gate

External ACRA/GoldTier/PingFed/Production calls: **0**. No `.env` dump, Atlas access,
normal-database access, cleanup, retained database write, provider deletion or lifecycle.
The exact retained Mongo service remains running. Fresh read confirms ID 143880,
`PROVIDER_VERIFIED_RECOVERY`, original Shell uncertain, replayed false, Policy/Amend
not executed. Before/after retained raw-document SHA-256:
`fb11ed2085b234ae83eaba4d97247b994f6e48617f4ee6b2224e184883a7574f`.

No new physical persistence claim is made: this delta changes no persistence owner.
The earlier physical-Mongo acceptance requirement remains pending its authorized CI
mongo:7 lane; it is not weakened or converted to PASS. Existing project-state provenance
failure remains disclosed. LOCAL evidence is not independently verified ownership;
external/current Live ownership availability was not retested.

Independent gate is a separate report-only run on the exact current-task freeze:
`tmp/GARDEN_OWNERSHIP_TRACE_REVIEW_MANIFEST.json`, report
`GARDEN_OWNERSHIP_TRACE_QUALITY_GATE.md`. P0/P1/P2 means FAIL; maximum two bounded
remediation rounds, preserving every failed report. No gate verdict is supplied by this
implementation report. Next authorized action is independent review only; no commit,
push, PR, merge or next phase.
