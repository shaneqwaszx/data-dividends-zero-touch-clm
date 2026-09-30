# Recoverable Onboarding and Final Review - Independent Re-Quality Gate 2

## 1. Executive Result

**FAIL**

The first gate's QG-001/QG-002 repairs remain closed. The second gate's legal-form,
owning-team, identity-edit, classification-edit, document-navigation, and frozen-state
repairs are present on the frozen bytes. The six-page A4 review is current, readable,
and contains the exact Mock Search/Shell/Policy/Amend projection with one stable
`acceptedAt` value.

QRG-001 is not fully closed, however. The final review presents an unconditional
**Edit ownership** action, but that action focuses only the read-only Ownership Path
Explorer. The actual backend-authorized manual ownership editor is conditionally
rendered elsewhere only while the workflow is at an ownership-review blocker, and it
is absent on the eligible final-review path. This is the false navigation-only
rectification that the user explicitly disallowed. A mandatory local editable-final-
review requirement therefore remains unmet.

Governance/publication readiness is blocked. No implementation, test, configuration,
ordinary documentation, generated artifact, provider, or database state was changed
by this review. This report is the only repository write.

## 2. Frozen Reviewed-Content Identity

- Branch: `feat/recoverable-onboarding-final-review`
- Base / `HEAD` / inspected `origin/main` / merge base:
  `3d6e7b560b8062daeb93c31cf91b0df957797e9c`
- Staged paths: 0
- Modified tracked paths: 61
- Untracked reviewed paths before this report: 39
- Complete reviewed path count excluding this report: 100
- Deterministic content identity: SHA-256 over sorted
  `SHA256(file bytes)<TAB>repository-relative path` entries:
  `ac7332c36bf007f6281a9100a93508c71d77a0b00e62db1f303fda011e0328c4`
- Complete path-set definition: the sorted union of `git diff --name-only` and
  `git ls-files --others --exclude-standard`, excluding only
  `.ai-pipeline/reports/RECOVERABLE_ONBOARDING_FINAL_REVIEW_QUALITY_REGATE_2.md`.
  This includes all 61 modified tracked files, both immutable prior gate reports, all
  new backend/frontend source and tests, the 11 current operator-route artifacts, the
  plan and four work records, ADR-007, and all other task-owned untracked files.

The identity was computed before review and reproduced unchanged immediately before
writing this report. Test caches and PDF render intermediates were disabled or kept
outside the repository and removed after inspection.

## 3. Acceptance Checklist

| Requirement | Result | Independent evidence |
|---|---|---|
| First-gate QG-001: exact preview/snapshot/digest binding | **PASS** | Six confirmation/preview tests plus source inspection passed. `build_request_preview` and the immutable snapshot use `case.created_at`; all projected fields remain digest-bound. Search/Shell/Policy/Amend and three identical `acceptedAt` values are present in the current PDF. |
| First-gate QG-002: no stale render artifacts | **PASS** | `apps/frontend/test-artifacts/operator-route/` contains 11 files and zero subdirectories. The rejected 18-page and superseded three-page render directories are absent. |
| Second-gate QRG-001: legal form and owning team | **PASS** | The component, 1440 review capture, and PDF show `Legal form`, the resolved legal form, `Owning team`, and `TEAM_A`. |
| Second-gate QRG-001: section edit actions reach real owners | **FAIL** | Identity, classification, and document actions reach their existing correction/evidence surfaces. **Edit ownership** reaches a read-only explorer, not an authorized ownership correction surface; QRG2-001 below. |
| Edit controls hidden after confirmation | **PASS** | Component source gates edits on `!projectionFrozen`; the focused frozen-projection test asserts all four labels are absent after confirmation. |
| Confirmation eligibility is withheld while readiness blockers remain | **PASS** | `eligibleForConfirmation` requires the target-confirmation exception, a dispatch-ready preview, and zero readiness blockers. |
| Same-case pre-confirmation identity edit invalidates stale state | **PASS** | Focused backend test proved the same case ID, changed UEN/entity, cancelled old confirmation exception, cleared confirmation/submission, exposed the document conflict, and performed only `search,search`. |
| No Shell/Policy/Amend before confirmation | **PASS FOR FOCUSED PATHS** | Eight focused backend tests passed; the identity-edit path retained Shell/Policy/Amend as `NOT_ATTEMPTED`, and confirmation-drift tests recorded zero writes. Source guards remain in direct and incremental dispatch paths. |
| Confirmation-time Search recheck and changed-result stop | **PASS FOR FOCUSED PATHS** | Focused tests passed for changed Search and hidden canonical drift; revised state remained unconfirmed with no target write. |
| Six-page review/PDF fidelity | **PASS** | `pdfinfo` reports six A4 pages, PDF 1.4, unencrypted, 138836 bytes. All six pages were independently rendered and visually inspected; they are readable, nonblank, numbered, and unclipped. Legal form/team, operations, warnings, provenance, and digest text are present. |
| Responsive tile evidence | **PASS WITH A MINOR ARTIFACT LIMITATION** | All ten screenshots were inspected and remain readable. The 320 default/hover/focus sequence is distinct. The 360 default/hover captures retain focus from the preceding 320 loop; QRG2-002 below. |
| S1-S5/S7-S9 broader behavior | REVIEWED, NO NEW MATERIAL FINDING BEFORE STOP | Current source/tests, ADR-007/D-061, schema-v7 compatibility, provider/read-only boundaries, and retained rendered evidence were inspected. Broad reruns stopped after QRG2-001 was established. |
| S10 independent completion | **FAIL** | A mandatory editable-final-review action remains misleading/non-functional. |

## 4. Contract and Integration Findings

### Closed - QG-001 exact review/snapshot parity

Current source uses the stable case-acceptance timestamp for both the displayed mapper
preview and the immutable target snapshot. The digest covers every displayed operation
field. The focused suite passed preview parity, durable confirmation, exact snapshot
equality, material-preview invalidation, confirmation-time Search recheck, and hidden
canonical-drift rejection. The current PDF contains Search, Shell, Policy, and Amend,
with the same `2026-09-28T22:47:35.351731Z` value in all three mutating operation source
contexts.

### Closed - QG-002 artifact hygiene

The operator-route artifact directory contains the current ten PNGs and one six-page
PDF, with no subdirectory. No stale 18-page or three-page render output remains.

### QRG2-001 - HIGH - “Edit ownership” is a false final-review correction action

Evidence:

- `ReviewAndSend.tsx:63` defines `canEditReview` only from case access and the absence
  of a frozen projection. `ReviewAndSend.tsx:166-169` therefore renders **Edit
  ownership** for every unconfirmed review, without checking whether an ownership
  action is available.
- `CaseDetail.tsx:741` wires that callback to `focusEvidence("ownership")`.
  The mapped target is `case-evidence-ownership` (`CaseDetail.tsx:79`), whose content
  at `CaseDetail.tsx:775-776` is only `OwnershipPathExplorer`.
- `OwnershipPathExplorer.tsx` is a read-only retained-result inspector. Its controls
  select a candidate/path for display; it has no evidence mutation, correction form,
  or backend action.
- The actual `ManualOwnershipEvidenceForm` is rendered at
  `CaseDetail.tsx:673-719` only when `manual_evidence_action` equals
  `MANUAL_OWNERSHIP_EVIDENCE`. The backend exposes that action only when ownership is
  `REVIEW_REQUIRED` **and** the automation is currently at the OWNERSHIP stage
  (`api_models.py:1172-1176`). It is consequently absent from the ordinary eligible
  final-review path, and it has no focus target connected to the review action.
- The ordinary-RM E2E assertion at
  `authenticated-zero-touch.e2e.ts:426-427` proves only that the read-only wrapper got
  focus. It does not prove an editor, a permitted action, a mutation, or an unavailable
  reason. The component test likewise proves only that the label is present.

Impact:

An RM reviewing the authorization boundary is told ownership is editable, but clicking
the action cannot edit or correct ownership and gives no explanation that the source
is immutable or that no manual-evidence action is currently authorized. This violates
S5's rule that navigation alone is not rectification, S6's section-level Edit
requirement, and the requirement that ownership edits be backend-validated and
evidence-linked. It also leaves the second gate's explicit “real ownership correction
surface or unavailable reason” repair incomplete.

Required repair:

1. Make the review action reflect the backend-authored ownership capability. When
   `MANUAL_OWNERSHIP_EVIDENCE` is available, navigate/focus the actual manual evidence
   form and verify its backend mutation/version binding. Otherwise do not present a
   working-looking **Edit ownership** button: expose a truthful review-only label or a
   disabled/unavailable reason explaining the current immutable/provider-evidence
   boundary.
2. Add component and ordinary-RM E2E assertions for both permitted and unavailable
   ownership states. A focus assertion on the explorer wrapper is insufficient.
3. Regenerate the current screenshots/PDF only if the visible final review changes,
   rerun affected frontend/backend/browser evidence, freeze the new bytes, and obtain a
   fresh independent gate.

### QRG2-002 - LOW - 360 “default” and “hover” screenshots retain focus state

The screenshot loop captures 320 default/hover/focus, leaves the stage button focused,
then immediately captures the 360 “default” before blurring. Visual inspection confirms
that `360-long-label-default.png` and `360-long-label-hover.png` retain the blue focus
outline. The images remain readable, and the 320 captures independently show the three
distinct states, so this does not create the material verdict. The artifact names are
nevertheless not exact evidence of their stated 360 states. Blur/reset focus before
each viewport's default capture and regenerate the two affected images during the next
authorized remediation.

## 5. Tester and Adversarial Findings

Independent commands/results on the frozen bytes:

```text
python -m pytest -p no:cacheprovider \
  six focused preview/confirmation tests \
  two focused final-review identity/Search tests -q
8 passed

npm.cmd test -- --run src/pages/ReviewAndSend.test.tsx
10 tests passed

PYTHONPATH=<repository-root> python -m unittest discover \
  -s ../../tests/contract -p "test_*.py"
44 tests passed

python scripts/check_architecture.py
ARCHITECTURE CHECK: PASS

python scripts/check_project_state.py
PROJECT STATE CHECK: PASS

python scripts/check_policy_authority.py
POLICY AUTHORITY CHECK: PASS

python scripts/check_external_provider_readiness.py
EXTERNAL PROVIDER READINESS CHECK: PASS

python scripts/check_secrets.py
Secret scan passed
```

The first sandboxed Vitest attempt could not spawn its bundled esbuild helper
(`EPERM`); the same local command was rerun with approved process-spawn permission and
passed 10/10. An initial direct `pytest tests/contract` invocation was not the
repository's configured contract runner and failed collection on the discover-directory
helper import; the canonical CI-equivalent `unittest discover` command then passed all
44 tests. Neither transient runner issue is reported as product evidence.

Additional evidence:

- `git diff --check`: passed; only line-ending conversion warnings were emitted.
- Eight untracked Markdown files: zero trailing-whitespace violations.
- PDF: six A4 pages; nonblank extracted-line counts `31,22,20,26,52,17`; all pages
  visually inspected at rendered resolution, including a higher-resolution page-four
  check.
- Artifact directory: 11 files, zero directories.
- All ten PNG screenshots were visually inspected.
- No external provider request, target write, confirmation click, database mutation,
  secret/configuration read, or environment-file read occurred.

The full backend suite, full frontend suite/typecheck/build, Playwright journey, and
physical-Mongo suite were not independently rerun after QRG2-001 was established.
Prior implementer evidence remains context, not fresh independent PASS evidence for
this failed gate.

## 6. Code, Architecture, Persistence, and Security Review

The inspected remediation preserves the existing case repository, schema-v7 envelope,
CLM snapshot, mapper, target ledger, Decimal ownership engine, authorization service,
provider connectors, and React Query owners. Identity correction remains same-case,
version-bound, and pre-submission; it invalidates dependent evidence and performs only
Search. The reviewed target projection remains server-authored, confirmation-gated,
and hidden from repeat edit controls after freeze.

No secret, raw provider payload, document body, credential, or private exception detail
was accessed or printed. The HR ACRA surface remains capability-gated and read-only in
the inspected source. Provider classifications remain Mock/Local/Sandbox Partial/
Dormant; no Live claim was introduced.

QRG2-001 is a UI/authorization-truthfulness defect, not a new persistence owner or
credential leak. The browser advertises an edit capability that the backend has not
granted for the current stage and routes it to a non-mutating viewer. Backend authority
itself remains fail-closed.

## 7. Evidence Authority and External Status

- **LOCAL WORKFLOW / RECOVERY / CONFIRMATION: FAIL.** Confirmation integrity and
  identity-edit recovery pass the focused review, but the final review still contains
  one false ownership-edit affordance.
- **OFFICIAL MOCK DEMO SAMPLE COVERAGE:** not re-executed because this gate prohibited
  external calls. Frozen task evidence reports ACRA 12/12 authorized reads, GoldTier
  Search 4/6, and zero writes; Garden is basic-profile-only `PROFILE_VERIFIED`, while
  OPQ and RRR are `NOT_HAPPY_PATH_READY`. This gate does not upgrade those results.
- **EXTERNAL GOLDTIER SUBMISSION: NOT EXECUTED.** No Shell, Policy, Amend,
  related-party, portal, replay, or other external mutation occurred.
- The original Garden pack and supplied screenshots remain unavailable. Current
  generated app screenshots/PDF do not verify those missing bytes.

## 8. Required Fixes and Readiness

1. Close QRG2-001 with capability-aware ownership navigation to a real authorized form
   or a truthful unavailable/read-only explanation.
2. Strengthen component/E2E coverage so ownership correction capability—not wrapper
   focus—is asserted.
3. Correct the minor 360 screenshot state labelling while regenerating affected visual
   evidence.
4. Rerun affected verification, freeze the changed bytes, and commission another fresh
   independent gate.

Governance/publication readiness: **NOT READY**. This verdict does not authorize a
commit, push, PR, merge, external write, database reset, or another phase.

## 9. Git Status and Reviewer Boundary

At the freeze point the branch had 61 modified tracked paths, 39 untracked reviewed
paths, and no staged paths. `HEAD` remained the requested base. Both earlier failed
reports were preserved unchanged. The reviewer made no implementation/test/
configuration/ordinary-documentation fix, artifact regeneration, commit, push, PR,
merge, provider call, database mutation, confirmation click, or next-phase change.
Only this assigned report was added after the reviewed identity was recorded.
