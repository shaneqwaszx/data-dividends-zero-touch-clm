# Phase 19 factual case timing - Intent

## TaskIntentDraft

- Requested outcome: Implement Phase 19 factual backend-authored case and automation timing through bounded portfolio/detail projections, UI, verification, and implementation reporting.
- Goal: Expose factual non-judgmental timing with one UTC portfolio observation while preserving Phase 18 compatibility.
- Success evidence:
- Focused and broad backend/frontend checks, guarded browser, physical Mongo 7 with zero skips, POC/governance/security evidence, frozen candidate hashes.
- Stop condition: Done after milestones A-H and frozen candidate evidence; blocked on ambiguous timing authority, unsafe persistence, or unavailable mandatory evidence; never self-approve or publish.
- Non-goals:
- SLA, due date, risk, escalation, thresholds, current-stage age, scheduler, TTL, provider/workflow action.
- Scope: Single-writer Phase 19 implementation and remediation only.
- Change kinds:
- feature
- Risk hints:
- Cross-layer API/read-model projection with strict Mongo validation and time chronology.

## BaselineReadSetHint

- AGENTS.md; docs/PROJECT_STATE.md; docs/ARCHITECTURE.md; docs/DEVELOPMENT_WORKFLOW.md; docs/contracts/CASE_PORTFOLIO_QUERY_PROFILE.md; Phase 19 brief; accepted Phase 18 evidence.

## BaselineUsageDraft

- Required baseline refs:
- AGENTS.md
- docs/PROJECT_STATE.md
- docs/ARCHITECTURE.md
- docs/DEVELOPMENT_WORKFLOW.md
- docs/contracts/CASE_PORTFOLIO_QUERY_PROFILE.md
- Phase 19 brief
- .ai-pipeline/reports/PHASE_18_QUALITY_GATE.md
- Delivered context refs:
- none
- Acknowledged before plan:
- AGENTS.md
- docs/PROJECT_STATE.md
- docs/ARCHITECTURE.md
- docs/DEVELOPMENT_WORKFLOW.md
- docs/contracts/CASE_PORTFOLIO_QUERY_PROFILE.md
- Phase 19 brief
- .ai-pipeline/reports/PHASE_18_QUALITY_GATE.md
- Cited in plan:
- .ai-pipeline/001_planner/PHASE_19_PLAN.md
- Missing refs:
- none
- Advisory decision: continue

## ImpactStatementDraft

- Compatibility boundary: Phase 18 query/filter/order/cache/deletion/session behavior and v1-v4 projected reads remain.
- Affected layers:
- backend domain/API, read-only persistence projection, frontend presentation, contracts/docs/tooling tests
- Owners:
- domain/case_management.py and CaseQueryService; existing Mongo and frontend view owners
- Invariants:
- One response-level UTC observed_at; non-negative deterministic facts; one Mongo operation; no SLA/polling/write/N+1; legacy DTO unchanged.
- Non-goals:
- SLA, due date, risk, escalation, thresholds, current-stage age, scheduler, TTL, provider/workflow action.

These records are Method Pack drafts / hints, not authoritative runtime decisions.
