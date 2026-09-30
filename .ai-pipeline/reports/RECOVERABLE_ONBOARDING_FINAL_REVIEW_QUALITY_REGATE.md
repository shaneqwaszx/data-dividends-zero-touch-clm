# Recoverable Onboarding and Final Review - Independent Re-Quality Gate

## 1. Executive Result

**FAIL**

The first gate's two findings are closed on the frozen post-remediation bytes:
the reviewed Mock operation projection is value-for-value equal to the immutable
submission snapshot, including every `sourceContext.acceptedAt`, and the stale render
directories are gone. A new material S6 acceptance failure remains, however. The
RM-facing Review and Send projection and its six-page print artifact omit the owning
team, and the review component has no section-level Edit controls. The user explicitly
required both as part of the editable final-review surface before confirmation.

This omission makes the mandatory local final-review acceptance incomplete. Governance
and publication readiness remain blocked. No implementation, test, configuration,
ordinary documentation, generated artifact, external provider, or database state was
changed by this review. This report is the only authorized write.

## 2. Frozen Reviewed-Content Identity

- Branch: `feat/recoverable-onboarding-final-review`
- Base / `HEAD` / inspected `origin/main` / merge base:
  `3d6e7b560b8062daeb93c31cf91b0df957797e9c`
- Staged paths: 0
- Tracked working-tree changes: 61 paths
- Untracked paths before this report: 37 paths
- Complete reviewed path count excluding this report: 98
- Deterministic identity: SHA-256 over sorted
  `SHA256(file bytes)<TAB>repository-relative path` entries:
  `c4f8a0fcb5a44b92019df2fb52af7563985751351d9a10b49899b4584b0e1de0`
- Scope: all modified and untracked backend, frontend, tests, contracts, decisions,
  work records, the preserved failed first-gate report, and current files under
  `apps/frontend/test-artifacts/operator-route/` reported by Git at the freeze point.

The identity was computed before review and reproduced immediately before this report.
No implementation content changed during the gate.

## 3. Acceptance Checklist

| Requirement | Result | Independent evidence |
|---|---|---|
| QG-001: exact preview/snapshot/digest binding | **PASS** | Six focused tests passed. A separate Mock-only probe proved Search/Shell/Policy/Amend presence, `reviewed_preview == mapper.build_preview(snapshot.target_input)`, snapshot `accepted_at == case.created_at`, identical Shell/Policy/Amend `acceptedAt`, digest change from an `acceptedAt`-only mutation, two Search calls, and zero write calls. |
| QG-002: current artifact set | **PASS** | The operator-route directory contains ten files and zero subdirectories; neither rejected render directory remains. `pdfinfo` reports six A4 pages and 138090 bytes. Every page has extractable content and a page number; Search/Shell/Policy/Amend and three identical `acceptedAt` values are present. Current 1440, 320-focus-context, and 360-hover captures were visually inspected. |
| S1-S5 recovery, recheck, policy, blocker/manual evidence | REVIEWED, NO NEW MATERIAL FINDING BEFORE STOP | Source, schemas, route ownership, changed tests, D-061/ADR-007, v7 compatibility, manual-evidence binding, blocker decision metadata, missing-input v2 ordering, and provider-readonly boundaries were inspected. The material S6 defect stopped further gate execution. |
| S6 exact final review and confirmation | **FAIL** | Exact transmitted-field projection and confirmation integrity pass, but QRG-001 below leaves the mandatory final-review content/editability incomplete. |
| No Shell/Policy/Amend before confirmation | PASS FOR FOCUSED PATHS | Focused confirmation tests and the independent probe produced only `search,search` before confirmation; material preview drift blocked submission with zero writes. Source inspection found guards in both legacy and incremental dispatch paths. |
| Confirmation-time Search recheck and changed-result stop | PASS FOR FOCUSED PATHS | Focused tests passed; changed Search returned a revised unconfirmed review with no snapshot or writes. |
| Stale/double-confirm/restart/no-replay | REVIEWED IN PART | Double-confirm/idempotence and stale/canonical-drift paths were included in focused source/test inspection. Schema-v7 restart and existing ledger no-replay tests were inspected, but the independent broad/physical reruns were not completed after the material S6 stop. |
| S7 HR ACRA console | REVIEWED IN PART | Routes use the existing `PROVIDER_SANDBOX_TEST` capability, exact composed connector, fixed server-owned host/configuration, bounded operation/UEN inputs, safe receipt projection, local rate/concurrency bounds, and no case/ledger owner. No external call was made in this gate. |
| S8 supplied pack/screenshots | NOT AVAILABLE | The original Garden pack and supplied screenshots remain absent. Current generated app artifacts do not substitute for those missing bytes. |
| S9 responsive/print usability | PARTIAL | Current responsive captures are readable and the six-page A4 artifact has meaningful page content, but the final review itself fails required content/edit controls. |
| S10 independent completion | **FAIL** | A mandatory local final-review requirement remains unimplemented. |

## 4. Contract and Integration Findings

### Closed - First-gate QG-001

Current source uses `case.created_at` for both the case-scoped request preview and
`ClmSubmissionSnapshot.target_input`. The digest serializes every projected operation
field instead of excluding `.acceptedAt`. The independent probe returned:

```text
OPS=SEARCH,SHELL,POLICY,AMEND
PREVIEW_EQUALS_SNAPSHOT=True
SNAPSHOT_ACCEPTED_EQUALS_CASE_CREATED=True
ALL_ACCEPTED_AT_EQUAL=True
ACCEPTED_AT_DIGEST_BOUND=True
CALLS=search,search
WRITE_CALLS=
```

The reviewed preview and retained snapshot therefore share one source for all exact
Mock fields, including `acceptedAt`. A changed `acceptedAt` invalidates the confirmation
digest before target intent or mutation.

### Closed - First-gate QG-002

`apps/frontend/test-artifacts/operator-route/` has no subdirectories. Only the current
responsive screenshots and `review-and-send-a4.pdf` remain. The PDF is Chromium-generated
PDF 1.4, unencrypted, six pages, and A4 (`594.96 x 841.92 pt`). Its pages contain 28,
22, 20, 26, 52, and 17 nonblank extracted lines respectively, each ending with its
page number. Search, Shell, Policy, and Amend appear, and the three extracted
`Source context.accepted at` values are identical.

No blocked local-file browser workaround was attempted after the browser security policy
rejected a `file:` URL. Inspection instead used the existing artifacts, PDF metadata,
page text, and responsive screenshots without generating new render files.

### QRG-001 - HIGH - Final review omits the owning team and section-level Edit controls

Evidence:

- The user-required S6 final-review content includes “company identity, country, legal
  form and owning team” and requires section-level Edit controls.
- `apps/frontend/src/pages/ReviewAndSend.tsx:103-122` renders Customer identity as legal
  name, registration number, country, and existing party, plus a separate KYC/segment
  section. It never renders `onboardingCase.team_id`, the browser-safe team label, or an
  owning-team field.
- `apps/frontend/src/pages/ReviewAndSend.tsx:74-225` exposes Print and the terminal
  Confirm/Save draft/Review outstanding items controls. It accepts no edit callbacks and
  contains no section-level Edit control for identity, classification, documents, or
  ownership.
- The exact current six-page PDF contains no `Owning team`, `TEAM_A`, or other team
  identifier. The print CSS intentionally emits only `.review-and-send`, so a team label
  elsewhere on the case page cannot satisfy the printable final-summary requirement.
- `apps/frontend/src/pages/ReviewAndSend.test.tsx:76-90` checks mapping presence,
  destination wording, print, and confirmation, but has no assertion for owning team,
  legal-form presentation, or section-level edit navigation.

Impact:

An RM asked to approve the frozen submission cannot see which team owns the case in the
final review or printable approval record, and cannot navigate from the relevant review
section directly to the requested correction surface. This is not a cosmetic issue: it
violates an explicit mandatory S6 review-content and editability criterion at the final
authorization boundary.

Required repair:

1. Render the backend-authored owning team (and an explicit legal-form/party-type label)
   in Review and Send and in the print artifact.
2. Add section-level Edit controls that focus or navigate to the existing authorized
   identity, classification, document, and ownership correction surfaces without
   performing a mutation.
3. Add component and ordinary-RM Playwright assertions for those fields/controls,
   regenerate the six-page-or-equivalent A4 artifact, visually inspect it, and obtain a
   fresh independent re-gate on the changed bytes.

## 5. Tester and Adversarial Findings

Executed independently on the frozen bytes:

```text
python -m pytest -p no:cacheprovider \
  test_mock_request_preview_exactly_projects_all_mapper_request_fields \
  test_target_mutation_requires_durable_cas_bound_confirmation \
  test_confirmed_snapshot_exactly_matches_reviewed_request_preview \
  test_material_request_preview_change_invalidates_confirmation_without_writes \
  test_confirmation_rechecks_search_and_returns_revised_summary_without_writes \
  test_confirmed_submit_blocks_hidden_canonical_drift_without_writes -q
6 passed
```

The separate probe results are recorded under the QG-001 closure above.

A full `apps/backend/tests` run reached 83% with no failure displayed and expected skips
visible, then emitted no additional progress for several minutes. Once QRG-001 was
confirmed, it was interrupted because the gate assignment requires stopping on a
material finding. It is not reported as a pass and supplies no completion count.

Additional evidence:

- `git diff --check`: passed; only line-ending conversion warnings were printed.
- Seven untracked Markdown files were checked explicitly for trailing whitespace; none
  was found.
- PDF metadata/text checks: six A4 pages, all nonblank, Search/Shell/Policy/Amend present,
  three identical `acceptedAt` values, page numbers 1-6.
- Artifact directory: ten files, zero subdirectories.
- No external provider request, target write, confirmation click, database mutation,
  secret read, or environment read occurred.

The independent ordinary-RM browser journey, frontend suite/build, full backend
completion, and physical-Mongo rerun were not repeated after QRG-001 because a material
finding ends this gate. Prior implementer evidence remains context rather than new
independent PASS evidence.

## 6. Code, Architecture, Persistence, and Security Review

The inspected remediation preserves the existing architecture owners: case repository,
schema-v7 envelope, CLM snapshot, target mapper, target ledger, Decimal ownership engine,
authorization service, and configured provider connectors. The exact Mock review now
comes from mapper DTOs, confirmation-time Search remains read-only, and Shell/Policy/
Amend paths retain confirmation guards before ledger start.

Schema v7 adds identity-correction attempts, rechecks, policy-rebind history, manual
ownership review evidence, blocker decisions, and dispatch confirmation while strict
schema-v6 decoding supplies bounded defaults and no read-time rewrite. The inspected HR
ACRA routes require the existing provider-diagnostic capability, accept no caller host,
project only presence booleans/safe summaries, and own no case or target-ledger access.

No secret or raw provider payload was accessed or printed. The new finding is an
authorization-review completeness defect, not a credential leak or provider-boundary
violation: the operator's final review omits a required ownership-context fact and the
specified edit navigation.

## 7. Evidence Authority and External Status

- **LOCAL WORKFLOW / RECOVERY / CONFIRMATION: FAIL.** QG-001's confirmation-integrity
  defect is repaired, but QRG-001 leaves the mandatory final-review surface incomplete.
- **OFFICIAL MOCK DEMO SAMPLE COVERAGE:** not re-executed in this no-external-call gate.
  The frozen task evidence reports ACRA 12/12 bounded reads, GoldTier Search 4/6, and
  zero writes; Garden is basic-profile-only `PROFILE_VERIFIED`, while OPQ and RRR are
  `NOT_HAPPY_PATH_READY`. No two additional complete happy paths and no entirely-official
  complete ownership profile were proved.
- **EXTERNAL GOLDTIER SUBMISSION: NOT EXECUTED.** No Shell, Policy, Amend, related-party,
  portal, replay, or other external mutation was authorized or performed.
- The Garden upload pack and supplied before screenshots remain missing-input
  limitations. Their bytes, parser behavior, and PDF agreement are unverified.
- Provider classifications remain Mock/Local/Sandbox Partial/Dormant as documented;
  no Live status follows from passing local tests or bounded reads.

## 8. Required Fixes and Readiness

1. Close QRG-001 by adding the backend-authored owning team and explicit legal form to
   the final review/print projection.
2. Add section-level Edit navigation for each editable review area, with disabled/
   unavailable reasons where appropriate and no browser-side authorization.
3. Add focused component and ordinary-RM browser assertions, regenerate and inspect the
   current A4 artifact, rerun affected verification, freeze the new bytes, and commission
   another fresh independent re-gate.

Governance/publication readiness: **NOT READY**. This verdict does not authorize a
commit, push, PR, merge, external write, database reset, or another phase.

## 9. Git Status and Reviewer Boundary

At the frozen point the branch had 61 modified tracked paths, 37 untracked paths, and no
staged paths. `HEAD` remained the requested base. The preserved failed first report was
not overwritten. The reviewer made no implementation/test/configuration/documentation
fix, artifact regeneration, commit, push, PR, merge, provider call, confirmation click,
or next-phase change. Only this assigned re-gate report was added after the frozen
identity was recorded.
