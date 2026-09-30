# Recoverable Onboarding and Final Review - Independent Quality Gate

## 1. Executive Result

**FAIL**

The mandatory local final-review contract is not met on the frozen reviewed bytes. The
screen and six-page PDF present a concrete Mock `sourceContext.acceptedAt` value as part
of the exact request, but confirmation constructs the dispatch snapshot later with a
different timestamp. The confirmation digest deliberately excludes every
`.acceptedAt` field. An operator can therefore confirm a review whose displayed value is
not the value retained for dispatch. This is a material contract/false-review defect;
publication readiness is blocked and a fresh independent gate is required after repair.

No implementation, test, configuration, ordinary documentation, or artifact was
changed by this review. This report is the only authorized write.

## 2. Frozen Reviewed-Content Identity

- Branch: `feat/recoverable-onboarding-final-review`
- Base / `HEAD` / inspected `origin/main` / merge base:
  `3d6e7b560b8062daeb93c31cf91b0df957797e9c`
- Staged paths: 0
- Tracked working-tree changes: 61 paths
- Task-owned untracked paths excluding this report: 57 paths
- Complete reviewed path count excluding this report: 118
- Deterministic identity: SHA-256 over sorted
  `SHA256(file bytes)<TAB>repository-relative path` entries:
  `283e3757f3eb10641ae657bdb6cf0887b966ea4ed8c3c864686b9c1a707e2eb3`
- Scope: all modified and untracked backend, frontend, tests, contracts, decisions,
  Aegis work records, and `apps/frontend/test-artifacts/operator-route/` files reported
  by Git at the freeze point.

The identity was recomputed immediately before this report and matched the initial
freeze. Generated caches ignored by Git are not part of the reviewed content.

## 3. Acceptance Checklist

| Requirement | Result | Independent evidence |
|---|---|---|
| S1-S5 recovery, policy, blockers, and manual ownership | REVIEWED IN PART | Source, changed tests, architecture, D-061/ADR-007, schema-v7 compatibility, identity-recheck, policy-rebind, blocker-policy, and manual-ownership owners were inspected. No separate material finding was recorded before the gate-stopping S6 defect. |
| S6 exact editable final review and explicit confirmation | **FAIL** | High-severity finding QG-001 below. The reviewed field and actual snapshot field differ, and the digest omits the differing field. |
| Search/Shell/Policy/Amend projection presence | PASS FOR PRESENCE ONLY | Current PDF text contains all four operations, and the focused mapper test passed. This does not cure QG-001 because value parity with the actual frozen snapshot fails. |
| Confirmation enforcement, Search recheck, and zero-write stop | PASS FOR INSPECTED PATHS | Focused confirmation tests passed 4/4; the adversarial reproduction made only two Mock Search calls and no Shell/Policy/Amend call. Full completion cannot be granted while the confirmation binds a non-exact review. |
| S7 HR ACRA console | REVIEWED IN PART | Composition, capability gate, safe-host/presence-only projection, bounds, read-only service, and zero-case/ledger-mutation tests were inspected. No external call was made in this gate. |
| S8 supplied Garden pack/screenshots | NOT AVAILABLE | The task records truthfully state that the supplied Garden pack and screenshots were absent. Their original bytes and claimed parser/PDF behavior remain unverified; generated app artifacts are not substitutes. |
| S9 responsive UI and print artifact | PARTIAL | The 320 keyboard-focus context, 360 hover tile, and 1440 final-review capture were visually inspected. The current PDF is A4 and six pages and contains the four operation sections. A final usability verdict was not issued after the material S6 stop. |
| S10 verification and independent gate | **FAIL** | Independent adversarial evidence found a mandatory local acceptance failure. |

## 4. Contract and Integration Findings

### QG-001 - HIGH - The confirmed dispatch snapshot is not the exact reviewed payload

Evidence:

- `apps/frontend/src/pages/ReviewAndSend.tsx:82` tells the operator: “Review exactly
  what this case will send.”
- `apps/backend/app/services/onboarding.py:1652` builds the displayed request preview
  with `accepted_at=case.updated_at`.
- `apps/backend/app/services/clm_orchestration.py:1249` creates the actual
  `ClmSubmissionSnapshot.target_input` later with `accepted_at=self._clock()`.
- `apps/backend/app/services/onboarding.py:479` excludes fields ending in
  `.acceptedAt` from the confirmation digest.
- The current six-page PDF exposes the concrete value
  `2026-09-28T21:54:04.782343Z` for Shell, Policy, and Amend `sourceContext.acceptedAt`.
- A local Mock-only reproduction on the frozen bytes produced:

  ```text
  PREVIEW_ACCEPTED_AT=2026-09-28T22:03:39.082386Z
  SNAPSHOT_ACCEPTED_AT=2026-09-28T22:03:39.099411Z
  MATCH=False
  TARGET_CALLS=search,search
  ```

Impact:

The user authorizes a concrete value that is neither retained in the dispatch snapshot
nor covered by the digest. The mismatch exists before any mutation and applies to a
field projected as actually transmitted in Shell, Policy, and Amend. This violates the
explicit exact-review and canonical-plan-digest requirements and makes the local
confirmation claim materially false even though mutation call stopping works.

Required repair:

Freeze the actual `ClmSubmissionSnapshot.target_input` before presenting the
confirmable review, derive every displayed operation/value from that same immutable
input, and bind every transmitted value (including `acceptedAt`) into the canonical
digest. If a field is intentionally generated only at dispatch, do not present a false
concrete value as exact; the accepted design still must satisfy the user's exact-field
requirement. Add a value-for-value parity test between the displayed operation preview
and the retained dispatch snapshot, then test stale/double-confirm/restart and zero-write
behavior again.

### QG-002 - LOW - Stale rejected render directories remain in the task-owned artifact tree

`apps/frontend/test-artifacts/operator-route/pdf-render/` contains the rejected
18-page attempt and `pdf-render-final/` contains the earlier three-page attempt. The
current source PDF is six pages. These directories are untracked but included in the
task-owned tree, so they are ambiguous publication evidence. Remove or clearly exclude
them from the intended handoff artifact set during remediation; do not mistake them for
the current PDF.

## 5. Tester and Adversarial Findings

Commands and results:

- Focused backend tests, with bytecode and pytest cache writes disabled:

  ```text
  python -m pytest -p no:cacheprovider \
    tests/test_clm_orchestration.py::test_mock_request_preview_exactly_projects_all_mapper_request_fields \
    tests/test_clm_orchestration.py::test_target_mutation_requires_durable_cas_bound_confirmation \
    tests/test_clm_orchestration.py::test_material_request_preview_change_invalidates_confirmation_without_writes \
    tests/test_clm_orchestration.py::test_confirmation_rechecks_search_and_returns_revised_summary_without_writes -q
  4 passed
  ```

- The separate Mock-only adversarial probe compared the value in
  `submission_plan.request_preview` with the value in the confirmation-created
  `submission_snapshot.target_input`; it returned `MATCH=False` and only
  `search,search` calls.
- `git diff --check`: passed (line-ending conversion warnings only).
- Six task-owned untracked Markdown files were checked explicitly for trailing
  whitespace; no violation was found.
- PDF metadata: 6 pages, A4 (`594.96 x 841.92 pt`), PDF 1.4, 138174 bytes.
- PDF text inspection found Search, Shell, Policy, and Amend and the concrete differing
  `acceptedAt` values. Visual inspection covered the current 1440 full-page review and
  representative 320 focus / 360 hover captures.

The reviewer did not click confirmation and made no provider call. Broader backend,
frontend, build, Playwright, physical-Mongo, or external-read suites were not repeated
after QG-001 because the quality-gate contract requires stopping on a material finding.
Prior implementer evidence is context, not independent PASS evidence for this verdict.

## 6. Code and Architecture Review

The inspected design generally preserves the existing case repository, Decimal
ownership engine, policy owner, zero-touch orchestrator, and target ledger. Schema v7
adds bounded facts and strict v1-v6 readers rather than a second persistence owner.
Search recheck remains read-only, and the inspected confirmation paths stop before
target mutation when confirmation is absent or Search changes.

QG-001 is nevertheless an architecture/contract break between the review projection
owner and the immutable submission snapshot owner: they are derived at different times
from different `accepted_at` values. Excluding the divergence from the digest hides it
instead of establishing one source of truth.

## 7. Security Review

No secret was accessed or printed, no external endpoint was called, and no provider
write was attempted. The inspected ACRA console routes require the existing
`PROVIDER_SANDBOX_TEST` capability, accept no caller-controlled host, project only
credential-presence booleans, and use the composed connector. No separate security
finding was recorded before the material contract stop.

The missing exact-payload binding is not classified as a credential/confidentiality
issue, but it is a high-integrity authorization defect: the actor's confirmation does
not cover one of the concrete values shown as transmitted.

## 8. Evidence Authority and External Status

- **LOCAL WORKFLOW / RECOVERY / CONFIRMATION: FAIL** because the exact reviewed payload
  is not the retained dispatch payload.
- **OFFICIAL MOCK DEMO SAMPLE COVERAGE:** not independently re-executed. The candidate
  handoff reports ACRA 12/12 bounded reads, GoldTier Search 4/6, zero writes, Garden
  basic profile only, and OPQ/RRR not happy-path ready. Those claims remain separate
  from this failed local gate.
- **EXTERNAL GOLDTIER SUBMISSION: NOT EXECUTED.** No Shell, Policy, Amend, related-party,
  portal, replay, or other external mutation was authorized or performed.
- Missing Garden pack and supplied screenshots remain missing-input limitations, not
  implementation PASS evidence.

## 9. Required Fixes and Readiness

1. Fix QG-001 so the confirmable review, digest, and immutable dispatch snapshot are the
   same value-for-value source, including `acceptedAt`.
2. Add an adverse parity test that would fail on the reproduced timestamp divergence.
3. Re-run the affected confirmation, mapper, zero-write, restart/durability, frontend,
   print/PDF, and ordinary-RM browser evidence.
4. Resolve QG-002 in the intended artifact handoff set.
5. Freeze the changed bytes and commission a fresh independent quality gate.

Governance/publication readiness: **NOT READY**. This verdict does not authorize a
commit, push, PR, merge, external write, or another phase.

## 10. Git Status and Reviewer Boundary

At the freeze point the branch had 61 modified tracked paths, 57 task-owned untracked
paths, and no staged paths. `HEAD` remained the requested base. The reviewer made no
implementation fix, commit, push, PR, merge, provider call, database reset, or next-
phase change. Only this assigned report was added after the frozen identity was
recorded.
