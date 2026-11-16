# D-141 advisory ownership review display: quality gate

Reviewer: independent Claude Code reviewer subagent. It did not author or fix any reviewed content.
Date: 2026-11-16. Scope: bounded change D-141 (PROPOSED, amends D-121 display only).

## Reviewed content (frozen)

- Worktree `/Users/tasha/Documents/GitHub/dd-clm-advisory-review`, branch `fix/advisory-review-status`, HEAD `e34a5a7562c2425deb670f61948bb2047e14db37`.
- Base: `origin/main` `49ac458a07dd412863cef68db1fc56057902b0e0`. `git ls-remote` shows that this is still the remote main, and it is an ancestor of HEAD (ahead 5, behind 0).
- 18 paths reviewed (`git diff --name-status 49ac458 HEAD`). Assistant: `briefing.py`, `claims.py`, `context.py`, `guardrails.py`, `guide.py`, `synthetic_boundary.json`, and the new `tests/test_advisory_review.py`. Backend: `app/api_models.py`, `app/main.py`, and the new `tests/test_advisory_review_node_flag.py`. Frontend: the new `e2e/advisory-review-status.e2e.ts`, `src/design-system.css`, `src/pages/CaseDetail.tsx`, `src/pages/CaseStatePanels.tsx`, `src/pages/CaseStatePanels.test.tsx`, `src/stageDisplay.ts` and `src/types.ts`. Docs: `docs/decisions/DECISION_LOG.md`.
- The working tree was clean at the start of the gate. The only write made during the gate is this report, which is untracked and not committed.

## 1. Executive result

**PASS WITH MINOR FIXES.** The backend flag is correctly limited. It cannot be true unless the node is `COMPLETE`, readiness references the current analysis, `review_is_advisory` holds and `poc_basis_accepted` does not. Node status, readiness, D-121/D-124 behaviour, the audit code and blocking mode are untouched. The frontend shows amber "Review advised" with words in all three places and keeps green Complete and red Review required unchanged. The exact-line catalog gains one line, offered only in the new state. No guardrail, maker-checker or permission recheck is weakened; the copilot change only adds a new drop rule. One bounded correction remains: the new copilot rule misses the common phrasing "has already/now been completed", so D-141 A4 is slightly overstated (M1).

## 2. Acceptance checklist

| # | Requirement | Result | Evidence |
| --- | --- | --- | --- |
| 1 | `advisory_review` is optional, defaults to None and appears only on OWNERSHIP_UBO | Met | `api_models.py:1455`, `api_models.py:2742-2749`; `test_the_flag_is_optional_and_defaults_to_none`, `other_flags == {None}` |
| 2 | True only when the node is COMPLETE, readiness reference_id equals the current analysis_id, and the record is advisory and not accepted | Met | The flag uses the same `readiness_status(...)` expression as the node `status` (`api_models.py:2737`/`2746`), so the two cannot disagree. Caller is `main.py:1406-1413`, and `project_processing_pipeline` has only this one caller. Tests cover stale, superseded, accepted, non-qualifying lane, blocking mode and parametrised non-COMPLETE readiness. |
| 3 | No change to status, readiness rule, D-121/D-124, poc_basis_accepted, the audit code or blocking mode | Met | The diff touches no service, readiness or audit code. `test_d124_advisory_continuation.py` and the partnership/entity-type/projection suites pass (below). |
| 4 | Frontend shows amber "Review advised" with words, the subtitle, green only with no open review, and blocking unchanged | Met | `stageDisplay.ts:110-120`, `CaseStatePanels.tsx:66-76,174-175,589-604`, `CaseDetail.tsx:1343-1346`. Vitest has 4 new cases; E2E `advisory-review-status:76` passes. Amber reuses `#8a5a00`/`#fdf0d8`/`#d49a2b`, and text contrast is about 5:1 or better. |
| 5 | Assistant: step "review advised", readiness REVIEW_ADVISED, `_OWNERSHIP_INCOMPLETE`, one catalog line, copilot drops "ownership complete" | Met with a gap (M1) | `context.py:102-123,348-352`, `guardrails.py:123-163,324-325`, `guide.py:251-259`, `claims.py:530-537,710-713`. Probes are listed in section 4. |
| 6 | Safety controls unchanged or only tightened | Met | Compared with main, `claims.py` adds a rule only. The removal of `settled\|verified` in e34a5a7 affects only this branch's own new regex, so "Ownership is verified." is still dropped as `authority_claim` (probe). The catalog addition is conditional and owner-gated by D-141 (PROPOSED). Permissions and RBAC are unchanged. The endpoint stays the same authorised GET. |
| 7 | No existing assertion changed or removed; no teammate test edited | Verified | The only `-` line in the test diff is the vitest import (`vi` added). Every other test change is a new file or the appended describe block. `tests/test_copilot.py` is not in the diff. |
| 8 | Decision recorded | Met | `DECISION_LOG.md` D-141 A1-A5, PROPOSED, needs Shane's acceptance. |

## 3. Contract and integration findings

- **No blocking findings.** The API change is additive and optional on `BrowserProcessingNode` and is mirrored in `types.ts:1215`. pre_pr gave the expected hotspot/API warnings only.
- Evidence class: Mock (official Mock lane, D-121). Nothing is presented as Live.
- Owner dependency, separate from code readiness: D-141 is PROPOSED and needs Shane's acceptance. That covers the new catalog line `OWNERSHIP_REVIEW_ADVISED`, because the catalog is owner-controlled.
- Observation (not required): the GoldTier readiness tile grid (`CaseDetail.tsx:1733-1742`) still shows Ownership "Ready" in the green tone in the advisory state. This is truthful for "ready to send to GoldTier" and is outside the three surfaces D-141 A3 names, but Shane may want it noted in the PR.

## 4. Tester and adversarial findings

All Python runs used the worktree venv. `import app, ai_assistant` resolves inside `dd-clm-advisory-review`.

- Backend targeted (reviewer run): `test_advisory_review_node_flag.py`, `test_marketplace_mock_partnerships.py`, `test_s1_pipeline_projection.py`, `test_zero_touch_entity_types.py` and `test_d124_advisory_continuation.py`. **248 passed, 0 failed.** The run uses blocking-mode and real Mock-lane API reads, not only projection unit tests.
- Assistant (reviewer run): `test_advisory_review.py`, `test_copilot.py`, `test_guardrails.py` and `test_claims.py` together. **247 passed.** `scripts/build_synthetic_boundary.py --check` reports "synthetic boundary is current".
- Frontend (reviewer run): `vitest run src/pages/CaseStatePanels.test.tsx` gives **69/69 passed**. `tsc -b --noEmit` passes. The tree was still clean afterwards.
- Reused Stage 2 evidence. I checked that it matches HEAD e34a5a7:
  - The E2E JSON records `head` e34a5a7, status PASS, complete, 10/10 selectors.
  - The pre-PR log records HEAD SHA e34a5a7, a clean tree and SUMMARY PASS with 2 warnings.
  - The assistant TSV covers 86/86 test files with no failures or errors; the skips are pre-existing skip markers.
  - The backend log has no final pytest summary line. Counting progress characters gives 4099 `.`, 7 `F` and 190 `s`, which matches the claim. All 7 FAILED entries are the known macOS-only ones (6 × `test_s2_local_ocr`, 1 × `__CF_USER_TEXT_ENCODING`).
- Adversarial: false-success through the flag.
  - Readiness REVIEW_REQUIRED/FAILED/IN_PROGRESS/MISSING with the caller verdict true gives None.
  - A superseded reference_id gives None.
  - In the assistant, a flag on a non-OWNERSHIP node or a non-COMPLETE node is ignored, and a string `"true"` is ignored (`is True`). A flag with readiness REVIEW_REQUIRED keeps REVIEW_REQUIRED, and the advised line is not offered.
- Adversarial: copilot sentences on an advisory case.
  - Correctly kept: negated ("Ownership is not complete yet.", "isn't finished") and conditional ("Once ownership is complete…", "If the UBO check is done…") sentences, and the catalog line itself.
  - Correctly dropped as `unsupported_status`: "has been completed", "fully resolved", "was already done", "UBOs are all cleared", "Ownership & UBO is complete", "Ownership and UBO have been completed".
  - Unchanged on a confirmed case, where all are kept.
  - **Missed, still kept:** "The UBO check has now been completed." and "Ownership has already been completed." The pattern allows adverbs only after the whole auxiliary, not between `has/have` and `been`. Lower-value misses: "Ownership: complete.", "…step shows Complete.", "…and the check is complete."
- E2E limitation (accepted): the harness runs blocking mode, so the browser spec injects the flag through route interception. The real flag on the Mock lane is proven by the backend API tests with TestClient, not end-to-end through a browser.
- Not run by the reviewer: the full E2E suite (not required), physical Mongo (no persistence change), and the full backend and assistant suites (valid Stage 2 evidence reused).

## 5. Code and architecture review

- Low (recommended, not required): the frontend `isAdvisoryReview` (`stageDisplay.ts:118-120`) trusts the flag without checking `node.status === "COMPLETE"`. A malformed payload with the flag on a REVIEW_REQUIRED node would therefore show amber instead of red. The backend makes this impossible, and the assistant already checks status (`context.py:102-109`); the same check here would give matching defence in depth.
- `ownership_advised` (`briefing.py:114`) duplicates `guardrails.ownership_review_advised`. This is minor duplication.
- Scope is tight. There is no service, readiness or persistence change and no new owner.

## 6. Security review

There are no findings. The flag is a boolean and carries no PII or KYC data. It is projected only by the existing authorised case-detail GET, so RBAC and team scope are unchanged. No secrets were added. The assistant still reads by GET only.

## 7. Required fixes

1. **M1 (minor, bounded):** `apps/assistant/ai_assistant/claims.py:533-537`. `_OWNERSHIP_DONE` misses an adverb between the auxiliary and `been`, as in "has already been completed" and "has now been completed". Allow forms such as `(?:has|have) (?:now |already |fully )*been`, alongside the existing forms. Add those two sentences to `CLAIMS` in `apps/assistant/tests/test_advisory_review.py:22` as new cases. Do not change existing assertions. This makes D-141 A4 accurate.

Not required: the frontend status check (section 5), and the GoldTier readiness tile observation (section 3).

## 8. Readiness

- The bounded D-141 change is ready for the PR once M1 is fixed. A recheck needs to cover only the `claims.py` regex delta and the assistant test files it affects (`test_advisory_review.py`, `test_copilot.py`, `test_claims.py`) plus a pre-PR rerun. Backend, frontend and E2E evidence stay valid.
- Owner dependency: Shane's acceptance of D-141, including the new catalog line.
- Live ACRA and real GoldTier readiness are not affected and not claimed. CI is billing-blocked, all evidence is local, and none of it is hosted CI.

## 9. Git status

Branch `fix/advisory-review-status`, HEAD e34a5a7, nothing staged. The only change made is this untracked report. The reviewer made no implementation, test or configuration edit, no commit, push or merge, and did not start another phase.
