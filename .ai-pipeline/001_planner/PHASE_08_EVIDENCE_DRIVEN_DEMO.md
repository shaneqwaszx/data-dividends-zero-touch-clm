# Phase 08 — Evidence-Driven Onboarding & Demo Realism

## Goal

Make the normal sponsor journey input-driven: the supplied UEN selects independent
synthetic registry, ownership, and Mock GoldTier records, while actual text extracted
from the uploaded synthetic PDF drives document evidence, confidence, comparison, and
review outcomes. Preserve the accepted Phase 06 `ZeroTouchOrchestrator` flow:
Registry -> Document -> Ownership -> Readiness -> Target.

## In scope

- A bounded, deterministic, network-free local text-PDF IDP provider behind the
  existing provider interface.
- Deterministic labelled-field extraction, normalisation, validation, ambiguity and
  missing-field handling for the accepted POC document field profile.
- Project-defined POC extraction confidence derived from parser evidence, not a
  scenario, filename, UEN, or embedded confidence value.
- Explicit document replacement and supersession semantics, audited history, safe
  stale/cross-case/terminal rejection, fresh evaluation, and automatic resume where
  the replacement removes the active blocker.
- UEN-keyed synthetic Registry, Ownership, and GoldTier provider datasets and a
  sponsor-mode `INPUT_DRIVEN` execution composition which does not accept a scenario.
- Clearly separated, default-collapsed Demo/Test fault-injection controls which cannot
  alter an existing input-driven sponsor case.
- Safe sponsor UI/evidence/UAT export visibility; synthetic PDF fixture pack; focused
  backend/frontend tests; Phase 08 architecture, demo, UAT, README, integration, and
  provider-replacement documentation.
- Supporting integration-security and POC-regression reports and a Phase 08
  implementation report.

## Required acceptance criteria

1. Sponsor start accepts only UEN and PDF; no selected scenario determines its outcome.
2. Actual PDF text is read and its extracted values drive document assessment.
3. Same UEN plus differing PDFs produces clean, conflict, missing, low-confidence, or
   no-text/processing-limitation outcomes as supported by the content.
4. Different UENs independently select registry, ownership, and target mock state.
5. Clean inputs complete with zero post-start human interventions; blockers stop later
   stages/calls, and independent sequential exceptions compose.
6. Replacement evidence explicitly supersedes only the current replaceable document,
   preserves history, and safely re-evaluates/auto-resumes without an approval bypass.
7. Browser-safe views/export expose minimal derived evidence, never raw PDF bytes/text,
   parser internals, paths, or private errors.
8. Phase 01–07 accepted behavior remains green and all normal claims remain bounded to
   an input-driven synthetic Mock POC.

## Non-goals

No production OCR/IDP, cloud OCR, LLM/VLM extraction, live ACRA/GoldTier/PingFed,
hierarchy creation, final sponsor IDP/UBO/source-authority policy, Ready-for-Approval,
production persistence/RBAC/malware CDR, workflow-engine rewrite, analytics, or next
phase work.

## Dependencies and unresolved policy

Q-001 to Q-008 and Q-012 to Q-014 remain open as applicable. In particular, the POC
four-field document profile, 0.85 threshold, confidence method, UBO threshold, and
registry-authority conflict treatment remain project-defined/provisional. Phase 08 may
not represent them as sponsor-approved or production policy.

## Required verification

Run the full backend, focused Phase 01–08, parser, supersession, input-driven world,
provider-conformance, contract, repository, Ruff, strict mypy, pip, secret, GoldTier,
frontend typecheck/test/build, dependency, Windows lifecycle, whitespace, and diff
checks available in this repository. Run the Phase 08 integration-security review and
POC regression check. Do not stage, commit, push, merge, or start another phase.
