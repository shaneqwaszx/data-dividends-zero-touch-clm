# Phase 07 Sponsor UAT Catalogue

## Purpose and acceptance boundary

This catalogue is the reproducible acceptance checklist for the Singapore NTB Mock
POC. All inputs are fictional. `PASS` below records automated local evidence on the
Phase 07 worktree; a sponsor may record a separate observed result and evidence-file
name during UAT.

The accepted terminal success is `COMPLETED / MOCK_GOLDTIER_SUBMITTED`. It is not
customer approval, Ready-for-Approval, a legal UBO decision, or live interoperability.
Document/readiness and UBO rules remain project-provisional.

Safe evidence for an integrated preset is available from:

`GET /api/demo/clm/zero-touch/cases/{case_id}/uat-evidence`

The export is demo-gated and excludes PDF bytes, raw provider/target payloads, private
fingerprints, endpoints, authorization material, and exception internals.

## Standard execution

1. Start the POC with `scripts/start_demo_windows.bat`.
2. Open `http://127.0.0.1:5173` and expand **Demo/Test Controls**.
3. Select the stated integrated preset and a fixture from
   `apps/backend/tests/fixtures/uat/`.
4. Enter `202400001A` unless the case below states that the preset binds another
   synthetic UEN.
5. Start onboarding, observe the server-authored summary/timeline, perform only the
   listed action, and export safe UAT evidence.
6. Use `scripts/reset_demo_windows.bat` between formal runs when a clean process-local
   state is required.

Local timings are observations only; no SLA is claimed. Each run should contain
nonnegative stage/total durations with nondecreasing UTC event timestamps.

## UAT-01 — Straight-through onboarding

- Business purpose: prove the clean exception-free flow.
- Initial inputs: `202400001A`; `clean-company-profile.pdf`.
- Mock profile: `STRAIGHT_THROUGH`; all four environments explicitly Mock.
- Automated stages: Registry → Document Verification → Ownership & UBO → Readiness →
  Mock GoldTier.
- Human interactions after Start: `0`.
- Expected blockers: none.
- Expected target calls: `SEARCH, SHELL, POLICY, AMEND`, once and in order.
- Terminal state: `COMPLETED / MOCK_GOLDTIER_SUBMITTED`.
- Expected metrics: 5 completed processing stages, 0 interventions, 0 unresolved
  exceptions, bounded local timing.
- Warning/claim: Mock/provisional only; not Ready-for-Approval.
- Automated result: **PASS** — `test_straight_through_reaches_mock_target_with_zero_human_interventions`
  and `test_uat_evidence_is_whitelisted_and_demo_gated`.
- Evidence location: exported `UAT-01-<case-id>.json` plus backend test result.

## UAT-02 — Document source discrepancy

- Business purpose: prove exception-only HITL and automatic resume.
- Inputs: `202400001A`; `legal-name-mismatch.pdf`.
- Mock profile: `DOCUMENT_DISCREPANCY`.
- Automated stages: Registry → Document pause; after resolution, Document → Ownership
  → Readiness → Mock GoldTier.
- Human interactions: exactly `1` using server-advertised `KEEP_REGISTRY_VALUE`.
- Blocker: `DOCUMENT_SOURCE_CONFLICT`; both registry and document values remain visible.
- Target calls: none before resolution; then `SEARCH, SHELL, POLICY, AMEND` once.
- Terminal state: `COMPLETED / MOCK_GOLDTIER_SUBMITTED` after auto-resume.
- Timeline: review-required event precedes exception-resolved and later target events.
- Expected metrics: 1 intervention, 1 resolved exception.
- Warning: registry retention is D-025 provisional policy, not sponsor-confirmed source
  authority.
- Automated result: **PASS** — `test_document_source_conflict_resolution_is_one_intervention_and_auto_resumes`.
- Evidence location: exported `UAT-02-<case-id>.json` after resolution.

## UAT-03 — Low-confidence evidence

- Purpose: prove confidence never becomes approval or a click-through shortcut.
- Inputs: `202400001A`; `low-confidence.pdf`.
- Mock profile: `LOW_CONFIDENCE` (legacy alias `LOW_CONFIDENCE_DOCUMENT` remains accepted).
- Automated stages: Registry → Document pause.
- Human interactions: `0`; no action is advertised.
- Blocker: `DOCUMENT_LOW_CONFIDENCE`.
- Target calls: none.
- Terminal state: `WAITING_FOR_REVIEW`.
- Metrics/timeline: one exception raised; document review required; bounded timing.
- Warning: final threshold/reviewer policy is not sponsor-confirmed under Q-014.
- Automated result: **PASS** — Phase 07 preset test plus Phase 06 no-action regression.
- Evidence: `UAT-03-<case-id>.json`.

## UAT-04 — Multiple document blockers

- Purpose: prove one action cannot erase independent evidence problems.
- Inputs: `202400001A`; `legal-name-mismatch.pdf`.
- Mock profile: `MULTIPLE_DOCUMENT_BLOCKERS`.
- Automated stages: Registry → Document pause.
- Human interactions: initially `0`; registry retention may resolve only the source
  conflict and increments the metric once.
- Blockers: `DOCUMENT_SOURCE_CONFLICT` and `DOCUMENT_LOW_CONFIDENCE` retained together.
- Target calls: none before or after the narrow conflict resolution while low confidence
  remains.
- Terminal state: `WAITING_FOR_REVIEW`.
- Timeline/metrics: blockers retain deterministic insertion order; no premature target
  event.
- Warning: no sponsor-approved low-confidence resolution action exists.
- Automated result: **PASS** — `test_multiple_document_blockers_remain_visible_and_stop_target`
  plus Phase 06 blocker-specific resolution regression.
- Evidence: `UAT-04-<case-id>.json`.

## UAT-05 — Ownership cycle

- Purpose: prove cyclic ownership cannot create a definitive UBO.
- Inputs: clean synthetic PDF.
- Mock profile: `OWNERSHIP_CYCLE` (legacy alias `OWNERSHIP_EXCEPTION`).
- Automated stages: Registry → Document → Ownership pause.
- Human interactions: `0`; no click-through action.
- Blocker: `OWNERSHIP_CYCLE` with bounded diagnostic evidence.
- Target calls: none.
- Terminal state: `WAITING_FOR_REVIEW`.
- Warning: replacement hierarchy/reviewer policy remains unconfirmed.
- Automated result: **PASS** — Phase 07 preset test and Phase 04 cycle regressions.
- Evidence: `UAT-05-<case-id>.json`.

## UAT-06 — Incomplete ownership

- Purpose: prove unresolved legal-entity chains cannot yield false completion.
- Inputs: clean synthetic PDF.
- Mock profile: `OWNERSHIP_INCOMPLETE`.
- Automated stages: Registry → Document → Ownership pause.
- Human interactions: `0`; no action advertised.
- Blocker: `OWNERSHIP_INCOMPLETE`.
- Target calls: none.
- Terminal state: `WAITING_FOR_REVIEW`.
- Warning: live hierarchy contract is blocked by Q-002.
- Automated result: **PASS** — existing Phase 06 integrated regression.
- Evidence: `UAT-06-<case-id>.json`.

## UAT-07 — Multiple ownership paths

- Purpose: prove direct and indirect paths aggregate once using Decimal arithmetic.
- Inputs: clean synthetic PDF.
- Mock profile: `MULTIPLE_OWNERSHIP_PATHS`.
- Automated stages: full straight-through flow.
- Human interactions: `0`.
- Expected ownership: Person A direct 20% + indirect 20% = aggregate 40%; one
  project-provisional candidate.
- Target calls: `SEARCH, SHELL, POLICY, AMEND` once.
- Terminal state: `COMPLETED / MOCK_GOLDTIER_SUBMITTED`.
- Warning: arithmetic is deterministic; the threshold/legal determination is not
  sponsor-approved.
- Automated result: **PASS** — `test_multiple_ownership_paths_complete_with_server_authored_candidate_summary`
  and Phase 04 path evidence tests.
- Evidence: `UAT-07-<case-id>.json` plus detailed Phase 04 ownership API evidence.

## UAT-08 — Existing GoldTier party

- Purpose: prove explicit match prevents duplicate writes.
- Inputs: clean PDF; preset binds synthetic `202400005E`.
- Mock profile: `EXISTING_PARTY` / search `MATCH_FOUND`.
- Automated stages: through readiness, then Mock search only.
- Human interactions: `0`; no unconfirmed selection/amend action.
- Blocker: `GT_EXISTING_PARTY_REVIEW_REQUIRED`.
- Target calls: `SEARCH` only; no shell, policy, or amend.
- Terminal state: `WAITING_FOR_REVIEW`.
- Warning: sponsor existing-party semantics are absent.
- Automated result: **PASS** — `test_existing_party_stops_after_search_and_creates_unresolvable_review`.
- Evidence: `UAT-08-<case-id>.json`.

## UAT-09 — GoldTier policy failure

- Purpose: prove technical failure and call stopping.
- Inputs: clean PDF; preset binds synthetic `202400003C`.
- Mock profile: `TARGET_FAILURE`.
- Automated stages: through Mock search, shell, and policy.
- Human interactions: `0`; technical failure is not reviewer work.
- Blocker/error: `GT_POLICY_VALIDATION_FAILED`.
- Target calls: `SEARCH, SHELL, POLICY`; no amend.
- Terminal state: `TECHNICAL_FAILURE`.
- Warning: synthetic target behavior only.
- Automated result: **PASS** — existing Phase 06 target-failure regression.
- Evidence: `UAT-09-<case-id>.json`.

## UAT-10 — Partial amend

- Purpose: prove a partial target result cannot become false success.
- Inputs: clean PDF; preset binds synthetic `202400004D`.
- Mock profile: `PARTIAL_AMEND`.
- Automated stages: full target sequence.
- Human interactions: `0`; no click-through continuation.
- Blocker: `GT_OPTIONAL_SECTION_REVIEW`.
- Target calls: `SEARCH, SHELL, POLICY, AMEND` once.
- Terminal state: `WAITING_FOR_REVIEW`, never `MOCK_GOLDTIER_SUBMITTED`.
- Warning: continuation semantics require sponsor direction.
- Automated result: **PASS** — Phase 07 presenter-preset test and Phase 05 regression.
- Evidence: `UAT-10-<case-id>.json`.

## UAT-11 — Recovery after target-finalization fault

- Purpose: prove retained-outcome reconciliation without target replay.
- Inputs: clean PDF.
- Mock profile: `RECOVERY`.
- Automated stages: target sequence executes; synthetic demo-only receipt finalization
  fails twice and persists `RECOVERY_PENDING`.
- Human interactions: `0`; presenter selects **Complete safe recovery**.
- Blocker/error: nonterminal retained-outcome recovery; no business exception.
- Target calls: `SEARCH, SHELL, POLICY, AMEND` exactly once before and after resume.
- Terminal state: first `RECOVERY_PENDING`, then `COMPLETED / MOCK_GOLDTIER_SUBMITTED`.
- Timeline/metrics: retained recovery event precedes later completion; submission identity
  and target prefix stay unchanged.
- Warning: process-local Mock recovery, not production exactly-once delivery.
- Automated result: **PASS** — `test_recovery_preset_is_pending_then_finalizes_without_target_replay`
  plus Phase 05/06 fault matrices.
- Evidence: export once pending and once complete; both report the same target calls.

## UAT-12 — Invalid registry response

- Purpose: prove external identity/shape/provenance is untrusted.
- Inputs: wrong returned UEN, malformed/control-bearing provider text, or unsafe HTTP/
  query-bearing provenance through local adapter-conformance tests.
- Mock profile: no presenter preset; this adversarial boundary requires injected test
  adapters and is intentionally not a normal sponsor data selector.
- Automated stages: Registry only.
- Human interactions: `0`.
- Error: `ACRA_RESPONSE_IDENTITY_MISMATCH` or `ACRA_RESPONSE_INVALID`.
- Target calls: none; no document, ownership, readiness, or canonical progression.
- Terminal state: `TECHNICAL_FAILURE`.
- Warning: tests prove the adapter contract, not live ACRA interoperability.
- Automated result: **PASS** — `test_phase06_provider_conformance.py` identity,
  reconstruction, original-control, and provenance matrices.
- Evidence: focused test output; no raw invalid provider value is exported.

## Browser E2E decision

Playwright was not added. The POC already has sponsor-observable FastAPI UAT journeys,
35 focused React/Vitest tests, polling/navigation regressions, and a production build.
Adding a new browser runtime/download dependency during delivery hardening would add
more setup risk than coverage for this bounded local handoff. The independent Phase 07
quality gate may require a manual browser walkthrough using this catalogue.
