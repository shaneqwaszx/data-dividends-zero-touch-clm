# Wrong-Document Warning and Shared Upload Wording: Independent Quality Gate

Reviewer: independent QG. I did not write or fix this content. This was a review only: nothing tracked was edited, staged or committed. This report is the only file written in the worktree.
Date: 2026-10-30

## Reviewed identity

- Worktree: `/Users/tasha/Documents/GitHub/dd-clm-wrong-document`, branch `feat/wrong-document-warning`.
- HEAD `72d7fdb02e86b27052da8fa7844d4591de6aab43`, tree `ac6fc5c863ff9d948406ac60300c5fae3ddffc8d`. The working tree was clean (`git status --porcelain` empty) before this report was written.
- Base: `origin/main` = `2911b54fb78b2503e80511c0cc3fc54eae37e37f` (#133, re-fetched, has not moved). It is merged in at 72d7fdb.
- Feature commit `03a5a9e`. Earlier merge `89f8e17` (base d90ab6a), which an interrupted earlier pass of this gate inspected.
- Reviewed diff `git diff origin/main...HEAD`: 14 files, +618/-39. New files: `uploadLimits.ts`, `uploadLimits.test.ts`, `pages/DocumentIdentityWarning.tsx`, `pages/DocumentIdentityWarning.test.tsx`, `e2e/wrong-document-warning.e2e.ts`. Changed files: `App.tsx`, `App.test.tsx`, `UiV2Integration.test.tsx`, `api.ts`, `design-system.css`, `CaseDetail.tsx`, `DocumentEvidencePanel.tsx`, `HomeOnboarding.tsx`, `ManualOwnershipEvidenceForm.tsx`. There are no backend, docs or script changes.
- Auto-merge integrity: the feature's added and removed lines in `git diff 2911b54 72d7fdb` are byte-identical to those in `git diff d90ab6a 89f8e17` (FEATURE-DELTA-IDENTICAL). The #133 removals are intact (`onViewOnboarded`, `OnboardedClients`, `ClientDetail`: no remaining references). Both sides' intent is kept.

## Change classes

`FRONTEND_UI`: card rendering, accessibility and upload wording. There is also a small client error-message mapping in `api.ts`. It is not a backend contract change, because codes and statuses are unchanged and only local fixed text replaces the message. No `AUTH_RBAC_SECURITY` change: every permission gate reuses the existing flags.

## Evidence matrix

| Check | Identity | Source | Result |
|---|---|---|---|
| HEAD/tree/clean, origin/main | 72d7fdb / ac6fc5c / 2911b54 | rerun | match, clean |
| `git diff --check origin/main...HEAD` | 72d7fdb | rerun | clean |
| CRLF/LF: `--numstat` == `--numstat --ignore-cr-at-eol` | 72d7fdb | rerun | equal |
| `tsc -b --pretty false` | 89f8e17 (rerun by me, exit 0); 72d7fdb (implementer) | reused for 72d7fdb: the feature delta is identical, and #133 is green on main | pass |
| Focused Vitest (uploadLimits, DocumentIdentityWarning, App, UiV2Integration) | 72d7fdb | rerun | 4 files, 125/125 |
| Full Vitest `wd-vitest-2911.log` | 72d7fdb | reused | 1231/1232; the only failure is ViteHistoryFallback (documented macOS-only) |
| `npm run build` `wd-build-2911.log` | 72d7fdb | reused | built |
| Affected E2E `wd-e2e-affected-72d7fdb.json` | head/tree/clean/origin_main recorded = 72d7fdb/ac6fc5c/false/2911b54 | reused | 12/12 PASS, including wrong-document-warning:22 |
| Full E2E keep-going `wd-e2e-full-89f8e17.json` | 89f8e17 | reused as historical only | 108/117. The 9 failures are the same selectors and error types as clean main 90115e4 (`main-90115e4-known9.json`), e.g. the same `GOLDTIER_SEARCH` stage-button timeouts. Validity for 72d7fdb: #133 changed four e2e specs and the Cases/navigation surfaces, so the 89f8e17 full run does not cover the integrated tree. The affected set reran on 72d7fdb and covers authenticated-zero-touch, garden, responsive-layout and s1-workspace. A full run at final acceptance is still owed. Not blocking this gate's verdict. |
| `check_project_state.py` / `check_architecture.py` | 72d7fdb | rerun | PASS / PASS |
| Backend suites | n/a | not required | no backend diff |
| Adversarial probe of `documentIdentityWarning` with the backend's real discrepancy shape (`qg-wd/probe.ts`, output `qg-wd/probe-output-72d7fdb.txt` in the session scratchpad) | 72d7fdb | new | reproduces F-1 and F-2 |
| `pre_pr_check.py` | n/a | not run | owed after the verdict |

## Changed existing test assertions

| File:line | Before | After | Judgement |
|---|---|---|---|
| `apps/frontend/src/App.test.tsx` (onboarding help-line pin) | `"PDF, DOCX, UTF-8 TXT, PNG, JPEG, and TIFF"` | the full approved help line `"… · up to 5 MB per file, 25 MB per case · up to 20 files"` | Superseded by the approved Change 2 wording. Stricter, not weakened. List it in the PR. |
| `apps/frontend/src/UiV2Integration.test.tsx:194` | `toContain("5 MiB")` | `toContain("This file is larger than 5 MB")` | Superseded by the approved wording (owner accepted "5 MB"). Same check, stricter text. List it in the PR. |
| `apps/frontend/src/UiV2Integration.test.tsx:196` | `toContain("25 MiB")` | `toContain("These files add up to more than 25 MB for this case")` | Same as above. |

No assertion was removed. The new tests (13 card tests, 9 upload-limit tests and one E2E) are additive.

## What verified correctly

- No auto-resolution or auto-correction: the card only reads `summary.reconciliation` and has no mutation. "Replace document" clicks the card's own existing `.document-upload-input`, which calls `handleFile(..., false)` and then `onReplace`, which calls CaseDetail's `handleReplacement`: a new version with the old one superseded. The E2E confirms the original stays in history with `superseded_by_document_id` set.
- Permissions: the button is disabled through the existing `controlsDisabled`, which includes `evidence_decision_authorized !== true`, mutation-blocked and post-submission states. It is hidden (`replaceDisabled === null`) when neither reupload nor replacement is permitted. Both behaviours are tested.
- Resolved, historical and superseded scoping: only `status === "OPEN"`; `essential && !historical && isCurrentDocument`. Tested.
- Accessibility: a real `<button type="button">` with clear labels. `role="alert"` is set only the first time a given key (document id plus discrepancy evidence fingerprints) appears in the session, and changed evidence is announced again. Tested.
- "Review the difference" is offered only when the reconciliation target exists (`summary.reconciliation && current_stage === "DOCUMENT"`, matching `availableFocusTargets`). "The details I entered are wrong" is offered only under `identityIncomplete || identityEditable`, the same condition as `identityEditor`.
- CaseDetail banner narrowing: the "Action needed" banner remains for other fields that have no permitted action (country, address). That is acceptable, because the requirement covers name and UEN only, and those fields now get the card.
- Sync test: it parses `config.py` defaults and `SUPPORTED_EXTENSIONS` through `?raw` and fails loudly if a pattern is missing. It also covers the `api.ts` code-to-message mapping and keeps `ApiError.code`. It is adequately robust. The help-text numbers are pinned by the wording test, not derived from the constant (acceptable, low).
- `no-text.pdf` gap: a document with no extractable text ends FAILED and is never reconciled, so the existing "Retry affected document" flow handles it. Documents that are readable but have low-confidence, missing, invalid or ambiguous name or UEN do reach reconciliation and get the "couldn't read" card. Because the requirement bases detection on reconciliation results, this is an acceptable disclosed limitation (F-5). It is not a defect, but it must be stated in the PR.

## Findings

| ID | Severity | File:line | Finding | Required / recommended |
|---|---|---|---|---|
| F-1 | High (false warning) | `apps/frontend/src/pages/DocumentIdentityWarning.tsx:44-50` | The backend builds one discrepancy per field, with an observation from every current document (`apps/backend/app/services/reconciliation.py:553`, `for document in documents`; a case can hold up to 20 current documents, `idp_max_files_per_case`). The card classifies with the discrepancy's overall `outcome` and only checks that this document has an observation. It never checks whether this document's own value differs from the case value. Reproduced: with a correct document (name and UEN equal to the registry) plus a wrong-company document, both cards say "This document looks like it belongs to a different company". The correct one shows "On this document: MERLION CIRCULAR LABS PTE. LTD. / This case: MERLION CIRCULAR LABS PTE. LTD." and invites replacing the correct file. This is the "warning on another document's observation" risk. The unit fixtures build one discrepancy per document, which the backend never produces, so the suite misses it. | Required: treat it as a mismatch only when this document's own VALID `normalized_value` differs from the case (registry/baseline) value. Add a test with the real shared multi-document discrepancy shape. No new matching rule or threshold is needed: it compares the existing normalized values. |
| F-2 | High (false warning) | `apps/frontend/src/pages/DocumentIdentityWarning.tsx:51-53` | Every non-CONFLICT OPEN outcome is labelled "We couldn't read the … from this document". But `INVALID`, `UNVERIFIABLE` and `MISSING_IN_SOURCE` are case-wide outcomes (`apps/backend/app/domain/reconciliation.py:93-117`). They can come from another document's low-confidence value, or from the baseline side: an invalid `requested_uen` (USER_INPUT), or a missing registry value. Reproduced: a good document with a VALID matching name is told its name couldn't be read because a second document was low-confidence. The same happens when only the USER_INPUT UEN is INVALID. This attributes unreadability to the wrong document or source. | Required: say "couldn't read" only when this document's own observation validity is not VALID. If the problem is on the baseline side, don't show the card (or leave it to the existing banner or identity correction). Add tests. |
| F-3 | Medium (requirement gap) | `apps/frontend/src/pages/CaseDetail.tsx:1485` (import at :98 unused) | The "Upload required document" control (PENDING_INPUTS) has no help line, although the requirement says every upload control shows it. `UPLOAD_HELP_TEXT` is imported but never rendered. With no current document, no help text appears anywhere near this control. | Required: render `UPLOAD_HELP_TEXT` beside this control. |
| F-4 | Low | `apps/frontend/src/pages/DocumentEvidencePanel.tsx:383` | The help line renders on every current document card's actions, even when no upload control is shown (no reupload or replacement permitted). | Recommended: show it only next to an actual control. |
| F-5 | Low (disclose) | n/a | `no-text.pdf` (no text at all) ends FAILED and uses the existing Retry flow, not the "couldn't read" card (see above). | Recommended: state it in the PR as a known limitation for the owner. |
| F-6 | Info | `DocumentIdentityWarning.tsx:31`; `DocumentEvidencePanel.tsx:243` | (a) A DOCUMENT_IDP observation without `document_id` matches every document. The API always projects `source_record_id`, so this affects legacy records only. (b) When `reuploadRequired`, "Replace document" opens the Retry input, not the replacement input. That cannot normally happen together with a reconciliation discrepancy. With an EXISTING_CASE baseline, "This case" falls back to USER_INPUT or "Not available". | Note only. |
| F-7 | Info | n/a | The full E2E on the integrated 72d7fdb tree is outstanding. The 89f8e17 run is historical, and #133 changed e2e specs since then. | Run once at final acceptance. |

Security: no secrets, no new routes, no new browser projection beyond values already in the summary, and backend error bodies are still not shown (fixed local strings). Architecture: frontend presentation only, and the checks pass. Docs: none required for a UI wording and presentation change. A decision-log entry is at the owner's discretion.

## Verdict

F-1 and F-2 are reproducible false-warning defects in the core detection: a correct document can be told it belongs to a different company, or that its name couldn't be read. Both are listed as FAIL conditions in the gate focus. F-3 leaves one upload control without the required help line. Everything else verified: permissions, no auto-resolution, the replacement lineage, alert-once behaviour, the sync test, superseded rather than weakened assertions, line endings, and the merge integrity with #133. Remediation needs to fix only the classification in `documentIdentityWarning` (plus realistic multi-document tests) and the CaseDetail help line. A recheck should rerun the focused Vitest, wrong-document-warning:22 and the affected set, and can reuse the other evidence.

Readiness: not ready for PR. `pre_pr_check.py` is not run.

VERDICT: FAIL
