# Wrong-Document Warning and Shared Upload Wording: Independent Quality Gate (re-review R1)

Reviewer: a fresh independent QG reviewer. I did not write the change, the remediation or the R0 review. This was a review only: nothing tracked was edited, staged or committed, and this report is the only file I wrote in the worktree.
Date: 2026-10-30

## Reviewed identity

- Worktree: `/Users/tasha/Documents/GitHub/dd-clm-wrong-document`, branch `feat/wrong-document-warning`.
- HEAD `638252cb79e6cce5d2ba98cff2c15c5c67bf9c95`, tree `7c9d212814a06fcba57ef6f8da8ba52c4727e62c`. The tree was clean (`git status --porcelain` empty) before this report was written, and still clean after my checks.
- Base: `origin/main` = `2911b54fb78b2503e80511c0cc3fc54eae37e37f`. I re-fetched it and it has not moved. It is merged in at `72d7fdb` (the tree R0 reviewed).
- Remediation delta reviewed: `git diff 72d7fdb 638252c`, 5 files. Four are code or test files: `DocumentIdentityWarning.tsx` (+15/-9), `DocumentIdentityWarning.test.tsx` (+49), `DocumentEvidencePanel.tsx` (1 line), `CaseDetail.tsx` (+2). The fifth is the committed R0 report.
- Full task diff `origin/main...HEAD`: 15 files, +755/-39. That is R0's 14 files plus the R0 report.
- Change class: `FRONTEND_UI`, unchanged from R0. There is no backend, contract, auth or persistence change.

## R0 finding dispositions

| R0 ID | Severity | Disposition | Evidence |
|---|---|---|---|
| F-1 | High | **Closed.** | Each document is now judged by its own `DOCUMENT_IDP` observation (`DocumentIdentityWarning.tsx:50-56`). A mismatch is raised only when this document's own VALID `normalized_value` differs from the case's VALID value. My probe uses the backend's real shared shape: one discrepancy per field, with observations from every document. A correct document beside a wrong-company document now gets no card (A1). The wrong document still gets "different company" with both values (A2). The unit test "with one correct and one wrong-company document, warns only on the wrong one" covers this. |
| F-2 | High | **Closed.** | "Couldn't read" now depends only on this document's own validity (`:52`). A good document gets no card when another document is low-confidence (B1). It also gets no card when the problem is on the case side: an INVALID USER_INPUT UEN (C1), a MISSING registry value (C2), or a user UEN that conflicts while the document matches the registry (C3). Tests cover the other-document and unusable-case-value paths. |
| F-3 | Medium | **Closed.** | `CaseDetail.tsx:1494-1495` renders `UPLOAD_HELP_TEXT` under exactly the same condition as the "Upload required document" control (`:1484`). I checked this by reading the code. No unit test pins it (see N-2). |
| F-4 | Low | **Closed.** | `DocumentEvidencePanel.tsx:383` shows the help line only when a Retry or Replace control is rendered (`reuploadRequired \|\| replaceAllowed`, the same branches as `:371-382`). |
| F-5 | Low (disclose) | **Still open: disclose in the PR.** | No code change was expected. A `no-text.pdf` ends FAILED and uses the existing Retry flow. This must be stated in the PR as a known limitation. |
| F-6 | Info | **(a) Closed. (b) Unchanged, info.** | (a) An observation with a null `document_id` no longer matches any card (`:31-35`; probe H1; test "never attributes an observation without a document id"). (b) The Replace-opens-Retry note is unchanged and still unreachable in normal flows. The EXISTING_CASE part of this note now behaves differently; see N-1. |
| F-7 | Info | **Still open, not gate-blocking.** | The full E2E on 638252c was still running when I wrote this (22/117 lifecycles, no failures so far). See the evidence matrix and the verdict. |

## Is strict equality on reconciliation's normalized values "new matching logic"?

No. I read `apps/backend/app/domain/reconciliation.py` (`derive_reconciliation_outcome`) and `apps/backend/app/services/reconciliation.py` (`_observations_for_field` and `_normalize`).

- The backend normalizes the baseline, the USER_INPUT and every document value with the same `normalize_document_value` function. MATCH versus CONFLICT is decided by the size of the set of VALID `normalized_value`s (`len(values) == 1`), which is exact string equality.
- The card compares the same projected `normalized_value` strings (`api_models.py:1323`) with `!==`. No new normalization, similarity rule or threshold is introduced. Validity, including the confidence threshold, comes only from the backend.
- **Can it report a mismatch where reconciliation would say MATCH?** No. If this document's VALID value differs from the VALID baseline value, the set holds at least two values, so the outcome cannot be MATCH. A MATCH or REGISTRY_ONLY outcome also never creates a discrepancy (`services/reconciliation.py:442`), so no card can come from it.
- When a third observation is INVALID or UNVERIFIABLE, the outcome becomes INVALID or UNVERIFIABLE, but the card can still show this document's real difference (probe D1). That is truthful: without the third observation the outcome would be CONFLICT.
- **Can it miss a real mismatch?**
  - With a REGISTRY baseline (the normal path), it does not: any document value that differs is flagged.
  - When the user-entered UEN differs from the registry but the document matches the registry, there is no card (C3). That is correct: the document is not the problem, and the existing banner or identity correction handles it.
  - The one gap is the EXISTING_CASE baseline (N-1).
- Name and UEN are required document fields for every profile (`required_document_fields`). So a document's own MISSING value (an absent or rejected value) is correctly shown as "couldn't read" (E1).

## Evidence matrix

| Check | Identity | Source | Result |
|---|---|---|---|
| HEAD, tree, clean, origin/main | 638252c / 7c9d212 / clean / 2911b54 | rerun | match |
| `git diff --check origin/main...HEAD` | 638252c | rerun | clean |
| Line endings: `--numstat` equals `--numstat --ignore-cr-at-eol` | 638252c | rerun | equal |
| `tsc -b --pretty false --noEmit` | 638252c | rerun | exit 0 |
| Focused Vitest: DocumentIdentityWarning, uploadLimits, App, UiV2Integration | 638252c | rerun | 4 files, 130/130 (R0 had 125; +5 new tests) |
| Full Vitest `wd-vitest-638252c.log` | 638252c | reused | 1236/1237. The only failure is ViteHistoryFallback (documented as macOS-only). |
| `npm run build` `wd-build-638252c.log` | 638252c | reused | built |
| Affected E2E `wd-e2e-affected-fix.json` (selectors `wd-selectors.txt`, 12) | identity recorded in the JSON: head 638252c, tree 7c9d212, dirty false, origin_main 2911b54 | reused | PASS, complete, 12/12, including wrong-document-warning:22 |
| Adversarial probe: the real `documentIdentityWarning` bundled from source and run against backend-shaped discrepancies (scratchpad `qg-wd-r1/probe.mjs`, output `qg-wd-r1/probe-output-638252c.txt`) | 638252c | new | 16 cases (A1-H2). All are truthful apart from F1 (N-1). |
| `check_project_state.py` / `check_architecture.py` | 638252c | rerun | PASS / PASS |
| Full E2E keep-going `wd-e2e-full-638252c.json`/.log | 638252c | **in progress** (22/117, 0 failures so far) | not yet available. It is not a required check for `FRONTEND_UI` in the `DEVELOPMENT_WORKFLOW.md` change-class matrix. It is the owner's once-at-final-acceptance run. Expected result: only the 9 known main failures (`main-90115e4-known9.json`), with identical reasons. |
| Backend suites | n/a | not required | no backend diff |
| `pre_pr_check.py` | n/a | not run | owed on the clean committed tree before push |

## Changed existing test assertions

There are no new changes since R0. The remediation adds 5 unit tests and removes or weakens none. The three superseded assertions R0 listed (`App.test.tsx` help-line pin, and `UiV2Integration.test.tsx:194` and `:196`) still need to be listed in the PR.

## New findings

| ID | Severity | File:line | Finding | Required / recommended |
|---|---|---|---|---|
| N-1 | Low (missed warning, not a false one) | `apps/frontend/src/pages/DocumentIdentityWarning.tsx:37-40` | `caseObservation` looks for REGISTRY, and if that is absent it uses USER_INPUT. It ignores `EXISTING_CASE`, which the backend uses as the baseline when a case has no `registry_acquisition` (`services/reconciliation.py:499`). In that case the legal-name mismatch has no reference value, so it is silently skipped. A wrong-company document then shows only a UEN FIELD_MISMATCH, compared against the requested UEN (probe F1), instead of "different company". At R0 this was a "Not available" display quirk; the fix turned it into a missed name warning. The impact is bounded: the existing-target path still acquires registry evidence ("required registry evidence is acquired", `services/onboarding.py`), so the REGISTRY baseline is the normal one. The discrepancy stays OPEN and keeps blocking through the existing reconciliation flow, so nothing is falsely shown as passed. | Recommended follow-up: also treat `EXISTING_CASE` as the case value, before USER_INPUT, and add a test. Not gate-blocking. |
| N-2 | Low (test depth) | `apps/frontend/src/pages/CaseDetail.tsx:1494-1495`; `DocumentEvidencePanel.tsx:383` | The F-3 and F-4 fixes have no unit test. The help text is pinned by `uploadLimits.test.ts`, `App.test.tsx` and the E2E (`wrong-document-warning.e2e.ts:52`), but not on the "Upload required document" control or on a card without controls. I checked both by reading the code. Each is a one-condition render that mirrors its control's condition exactly. | Recommended: add a small render test. Not blocking. |

Security: unchanged from R0. There are no new routes, data or projections. The card reads only values already in the summary, and backend error bodies are still not shown. Architecture: frontend presentation only; the checks pass.

## Verdict

Both High findings (F-1, F-2) are fixed by judging each document only by its own reconciliation observation. The probe and the new tests use the backend's real shared multi-document shape, and they confirm that a correct document is never told it belongs to a different company or couldn't be read because of another document or the case value. Comparing reconciliation's own normalized values with strict equality adds no matching logic or threshold, because it is the same equality the backend uses for MATCH versus CONFLICT. It cannot contradict a MATCH outcome. F-3 and F-4 are fixed. The new findings are Low only: N-1 is a missed warning on a rare baseline path where the case stays blocked, and N-2 is test depth. Neither is a false success or a safety issue.

The full E2E on 638252c is not a required `FRONTEND_UI` check and is still running as the owner's final-acceptance step. If it shows any failure beyond the 9 known main failures (`main-90115e4-known9.json`, same reasons), this PASS no longer holds and a recheck is needed.

PR readiness, before push:
- Run `pre_pr_check.py` on the clean committed tree.
- In the PR, state F-5 (no-text PDF uses Retry) and N-1.
- List the three superseded assertions.
- Record that all evidence is local (hosted CI is billing-blocked).

VERDICT: PASS
