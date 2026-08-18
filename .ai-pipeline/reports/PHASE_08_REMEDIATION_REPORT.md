# Phase 08 Remediation Report

**Branch:** `phase/08-evidence-driven-demo`
**Scope:** P08-QG-001, P08-QG-002, P08-QG-003 and directly associated Medium findings only
**Date:** 2026-08-18

## Outcome

- **P08-QG-001: CLOSED.** Root cause: the supported Windows launcher overrode the
  application default with `IDP_CONNECTOR_MODE=mock`, selecting a provider that ignored
  uploaded bytes. The launcher now selects `local_pdf_text`; application defaults,
  execution-profile API, launcher output, frontend banner, configuration, and sponsor
  documents agree on `LOCAL_PDF_TEXT` / Local POC.
- **P08-QG-002: CLOSED.** Root cause: sponsor document evidence depended only on case
  ID although initial attachment and replacement retain that ID. It now refreshes from
  the authoritative summary case/version/updated timestamp, retains supersession
  history, and renders current versus superseded evidence.
- **P08-QG-003: CLOSED.** Root cause: `Path`/`PATH` collisions made `Start-Process`
  reject the child environment. The launcher now normalizes PATH case-insensitively in
  its own process, preserves the effective inherited path, and adds a bindability check
  so an occupied unowned port fails before child creation. The Windows lifecycle
  implementation also handles the venv Python listener handoff when CIM inspection is
  unavailable, while retaining exact recorded PID, creation-time, executable, port,
  and role checks.

## Implemented remediation

- Supported sponsor composition: ACRA Mock, Local PDF Text IDP, input-driven synthetic
  ownership, and GoldTier Mock. Developer Mock IDP/fault scenarios remain isolated to
  gated demo routes.
- Added supported-composition causality coverage: clean, mismatch, and ambiguous PDF
  bytes for the same UEN produce their content-derived outcomes; misleading filenames
  do not affect assessment.
- Sponsor document evidence now displays safe registry/document values, POC confidence,
  comparison status, and explicit `CURRENT` / `SUPERSEDED` history through replacement
  chains.
- Added bounded ownership evidence (parties, relationships, edges, percentages, path
  arithmetic, candidate classifications, and cycle/incomplete issues), server-authored
  Mock GoldTier operation status, and server-authored readiness status/blockers.
- Added `cycle-uen-clean.pdf`; updated the Phase 07 fixture manifest so the intentional
  textless `no-text.pdf` is explicitly allowed without adding visible text to it.
- Reconciled README, sponsor script/runbook, UAT, integration/configuration, provider,
  and security documentation around UEN + actual PDF + Start as the normal journey.

## Validation

| Check | Result |
|---|---|
| Full backend | PASS — 502 tests |
| Phase 01–08 focused backend groups | PASS |
| Supported PDF causality / filename independence / cycle fixture | PASS |
| Phase 07 delivery fixture invariant | PASS |
| Contract discovery | PASS — 44 tests |
| Ruff | PASS |
| Strict mypy | PASS — 56 files |
| pip check | PASS |
| Secret tests/scanner | PASS — 5 tests / scanner clean |
| GoldTier validator | PASS normal (`19 valid / 19 quarantined / 48 not validated`); strict invalid exit expected |
| Frontend typecheck | PASS |
| Vitest | PASS — 40 tests |
| Frontend production build | PASS |
| npm ls --all | PASS (platform optional-dependency notices only) |
| Windows lifecycle suite | PASS — clean start/health/stop verified; runner leaves no state or listeners |

## Security and regression review

The focused integration-security review found no Critical/High defect in changed paths:
the parser remains bounded and no raw PDF/full text or provider payload is projected.
Evidence refresh remains case-scoped, Developer/Test controls remain gated, provider
labels are truthful, runtime metadata remains Git-ignored, and lifecycle handling does
not kill unrelated processes. The POC regression catalogue is unchanged; accepted
Phase 01–07 behavior is covered by the passed backend/contract/delivery checks.

## Status summary

| Item | Status |
|---|---|
| Supported sponsor IDP | **LOCAL_PDF_TEXT** |
| Input-driven sponsor flow | **READY** |
| Actual PDF-derived assessment | **READY** |
| Document exception HITL | **READY** |
| Replacement remediation | **READY** |
| Automatic resume | **READY** |
| Ownership evidence visibility | **READY** |
| GoldTier evidence visibility | **READY** |
| Windows lifecycle | **PASS** |
| Repository regression | **PASS** |
| Sponsor-facing demo | **READY** |
| Independent Phase 08 re-gate | **READY** |
| Sponsor-approved IDP policy | **NOT CONFIRMED** |
| Sponsor-approved UBO policy | **NOT CONFIRMED** |
| Live ACRA | **BLOCKED** |
| Real GoldTier | **NOT READY** |
| Ready-for-Approval | **NOT CONFIRMED** |

## Remaining sponsor dependencies

Q-001 to Q-008 and Q-012 to Q-014 remain as documented. This remediation does not add
OCR, live ACRA, real GoldTier/PingFed, production persistence/RBAC, Ready-for-Approval,
or final sponsor IDP/UBO policy.

## Required next step

Run the independent Phase 08 quality gate against this remediation. Its re-gate should
confirm the launcher, evidence, and repository-regression results independently.
