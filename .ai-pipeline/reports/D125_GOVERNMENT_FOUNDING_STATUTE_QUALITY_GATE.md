# D-125 Government founding statute: independent quality-gate report (R0)

- Reviewer: independent Claude subagent (did not author or remediate the reviewed content).
- Candidate: worktree `dd-clm-d125-government-statute`, branch `feat/d125-government-founding-statute`.
- Reviewed SHA: **9ae3afe** (tree `40138d0f7aa65de759f6aa7ac13fdddafae379ca`), local only, never pushed.
- Base: `origin/main` 4c1db49 (merged at 100bb5b). Reviewed range `git diff 4c1db49 HEAD`:
  55 paths, sha256 of the diff `f0f116e357276f0de3191fbb3c6bfd9010d993496a0ed15d6e452108bcf36886`.
- Working tree clean at review start and end (only this report added; it is not part of the reviewed content).
- Task spec: `.claude-prompts/12-government-founding-statute.md` (written as "D-120"; renumbered D-125 because D-120/D-124 were taken).

## 1. Executive Result

**FAIL**

The core feature is correct and well tested: the statute check runs after the evidence check
inside the case lock, a mismatch saves nothing (case, automation, CLM, events, target calls),
creator-only/document binding/concurrency/permission rechecks are unchanged, the schema 19 -> 20
migration is strict, and the `shownInline` suppression only hides `GOVERNMENT_STATUTE_MISMATCH`.

One medium defect blocks a PASS: the required migration behaviour "an old confirmation must be
confirmed again" does not work for a pre-D-125 Government case that has already moved past the
Government hold (the normal state after a D-101 confirmation). The panel offers the Confirm form,
but the server refuses it with `ZERO_TOUCH_GOVERNMENT_STATUS_NOT_ALLOWED` because the hold is no
longer open, and the browser has no control that re-raises the hold. The case stays fail-closed
(no GoldTier write), but DECISION_LOG D-125 G5, the UAT guide and the spec state a recovery path
that does not exist. That is an untrue user-visible/contract claim on a migration path, so it is
not a "minor fix".

## 2. Acceptance Checklist

| # | Requirement (prompt 12) | Result | Evidence |
|---|---|---|---|
| A1 | Request fields: statute strip 3-200, section <=40 optional, body type enum, extra=forbid, 422 | PASS | `main.py:480-495`; `test_government_statute_request_validation_gives_422` (13 cases incl. blank, newline, tab, extra field); ran myself |
| A2 | Compare after loading evidence; normalise rule; exact equality; pure function in `government_status.py` | PASS | `government_status.py:32-54`; check at `zero_touch_orchestration.py:1943` after evidence check `:1932`; normaliser unit tests; my probes (nested brackets, unclosed bracket, mid-name year, empty normal form) |
| A3 | Mismatch -> safe `GOVERNMENT_STATUTE_MISMATCH`, nothing saved, no event | PASS | raised before `confirm_government_status`/CLM refresh; `test_government_statute_mismatch_saves_nothing` compares case, automation and CLM records and target calls; ran myself |
| A4 | Stored fields on `GovernmentStatusConfirmation`, optional for old records; `government_status_confirmed` False when missing | PASS | `domain/models.py:1067-1090` (together-validator), `government_status.py:162-164` |
| A5 | Old confirmation must be re-confirmed (panel shows CONFIRMATION_REQUIRED again) | **FAIL** | Finding M1: re-confirmation refused once the hold is resolved; reproduced |
| A6 | Event message names statute and section; code unchanged | PASS | `onboarding.py:728-745`; two event tests |
| A7 | Statute not in evidence fingerprint; changed document invalidates | PASS | fingerprint untouched; `test_a_changed_document_still_invalidates_a_statute_confirmation` |
| A8 | Projection fields only when CONFIRMED; `types.ts` | PASS | `api_models.py:1613-1637`; legacy-shape test asserts nulls |
| A9 | Frontend form, disabled until valid, inline mismatch keeps inputs, confirmed `<dl>` | PASS | `GovernmentStatusPanel.tsx`; 12/12 vitest; E2E selector PASS |
| A10 | Out of scope respected (no UEN body-type inference, no routing/seed/extractor change) | PASS | diff path set |
| A11 | Docs: decision, BPD text, UAT guide | PASS (content), but G5 claim false until M1 fixed | `DECISION_LOG.md` D-125, `blocker_decision_policy.py`, regenerated guide, UAT guide |
| A12 | Persistence: strict V19 reader, <=19 reject new keys even null, schema 21 unsupported, old digests unchanged | PASS | `persistence/models.py:933-1175`, `mongo_case_store.py:97-732`; `test_government_statute_persistence.py`; real Mongo run |
| A13 | Teammate tests changed listed, none weakened | PASS | see section 4 |

## 3. Contract and Integration Findings

- No connector, mapping or GoldTier payload change; the statute never reaches the target mapping
  (`founding_statute` appears only in domain, persistence, projection and the confirm path).
- Evidence authority: the Founding Instrument stays the document-derived value; the RM text is
  compared, never substituted. The body type is RM-asserted and documented as unverified (G6).
- Authority labels: `USER_AUTHORIZED_POC / PROJECT_DEFINED_PROVISIONAL`, candidate, Shane to
  confirm. No sponsor-confirmation overclaim.
- Architecture invariants (AGENTS.md): none touched. Reauthorization still runs first inside the
  case lock; creator-only, open-hold, pre-submission and evidence-binding checks are unchanged
  and precede the statute check.
- **M1 (Medium, contract/migration):** see section 7.

## 4. Tester and Adversarial Findings

Checks I ran myself on 9ae3afe (macOS, local; not hosted CI):

| Check | Result |
|---|---|
| `pytest` targeted: entity types, statute normalisation, statute persistence, entity-types persistence, slice_a legacy, phase12 persistence, poc ownership acceptance, official shareholder evidence, uen route persistence, document digests, blocker decision policy | 516 passed, 0 failed |
| Physical Mongo (`PHASE12_MONGO_URI=mongodb://127.0.0.1:27185`): `test_zero_touch_entity_types_real_mongo.py`, `test_entity_types_persistence.py`, `test_government_statute_persistence.py`, `test_phase12_real_mongo.py` | 50 passed, 0 skipped |
| `vitest` `GovernmentStatusPanel.test.tsx` + `CaseDetailGovernmentStatute.test.tsx` | 12/12 passed |
| `tsc -b --noEmit` | exit 0 |
| `ruff check app tests`, `mypy app` | pass / no issues (139 files) |
| `scripts/check_project_state.py` | PASS |
| `apps/assistant scripts/build_synthetic_boundary.py --check` | current |
| `git diff --check 4c1db49 HEAD` | clean |
| E2E `scripts/run_e2e.py --selectors-file` (`e2e/database-classification.e2e.ts:234`), results `scratchpad/qg/e2e_qg_r0_results.json` | 1/1 PASS, cleanup VERIFIED |

Not re-run (implementer evidence accepted as consistent with the frozen content; 9ae3afe only
changes one frontend string and two tests): full backend (3756 pass, 6 known macOS OCR
failures), full real-Mongo set (201), full vitest (1401 + 1 known macOS ViteHistoryFallback).

Adversarial probes (scratch tests outside the repo):

1. **Legacy confirmation past the hold (M1).** Confirm with a statute, overwrite the stored
   confirmation with the schema-19 shape, GET the case: panel `CONFIRMATION_REQUIRED`, automation
   blockers still `['TARGET_CONFIRMATION_REQUIRED']`, CLM readiness `['GOVERNMENT_STATUS_REQUIRED']`.
   Re-confirm -> `409 ZERO_TOUCH_GOVERNMENT_STATUS_NOT_ALLOWED`. Target confirmation ->
   `409 CLM_NOT_READY`, target calls `['GET','GET']` (fail-closed, no write). Only an API `/resume`
   re-raises `GOVERNMENT_STATUS_REQUIRED`; the CaseDetail page offers no such control in this state.
2. Bracketed free text: `"Demo Parks FYP Test Authority Act (note: S1234567A see me)"` is
   accepted and stored/projected verbatim and written into the event message (L1).
3. Normaliser: NFC `"Café Act"` vs NFD `"Café Act"` do not match (fail-closed, L2);
   `"Act 1970"` equals `"Act 1971"` (spec-defined, L3); fullwidth letters are not folded; zero-width
   space and Arabic-Indic digits are handled; `"(x)"` vs `"(y)"` never matches.
4. Mismatch path saves nothing: confirmed by the authored test (case/automation/CLM equality and
   target calls) and by code reading (raise precedes every write and the CLM refresh).

Teammate tests changed (reviewed every changed line outside the new D-125 tests): all are schema
pins `19 -> 20`, `range(1, 20) -> range(1, 21)`, and "unsupported version" probes `20 -> 21`;
`test_zero_touch_entity_types.py` and `GovernmentStatusPanel.test.tsx` add the required statute
payload and extend assertions (one assertion strengthened with an error-code check). **No
assertion removed, weakened or redefined.**

## 5. Code and Architecture Review

- Check order is safe: reauthorize -> stale revisions -> creator -> open hold / pre-submission ->
  evidence binding -> statute -> save. Statute errors cannot leak evidence existence beyond what
  the panel already projects.
- `exclude_if` on the new fields matches existing precedent (`government_status_confirmation`,
  `uen_route`, document digests), so domain dumps and digests of old cases are unchanged; the
  Mongo codec writes the four keys as null on schema 20 and the schema-20 reader accepts that.
- `DurableCaseSnapshotV19.to_current` copies attributes (keeps backend-only excluded evidence),
  consistent with V18.
- `shownInline` is an optional predicate evaluated only in the catch path after the
  current-action check; the only caller returns true solely for
  `ApiError.code === "GOVERNMENT_STATUTE_MISMATCH"`. A CaseDetail test proves another code still
  reaches the page banner. No other `runMutation` caller passes it.
- **M1** is the only code defect. L4/L5 are consequences of the same "old confirmations no
  longer count" rule in other states.

## 6. Security Review

- No secrets, auth or TLS change. Inputs are bounded (length, no C0/DEL control characters,
  consistent with existing `target_safety` patterns); React renders the values as text.
- **L1 (Low, advisory):** because bracketed text is ignored by the match, an RM can store up to
  ~200 characters of arbitrary text (including PII) inside the "matched" statute; it is projected
  next to "Matched to document: Yes" and written into a case event message (timeline, audit and
  the AI Assistant's event context, which is still filtered by the exact-line catalog). This
  follows the spec's rule literally; flag it for Shane in the PR (optionally store the statute
  with bracketed text removed, or reject brackets not present in the document).

## 7. Required Fixes

1. **M1 (Medium) - a pre-D-125 confirmation past the hold cannot be re-confirmed.**
   - Where: `apps/backend/app/services/zero_touch_orchestration.py:1900-1919` (open-hold
     requirement in `confirm_government_status`) together with `government_status.py:162-164`
     (old confirmations no longer count) and `_recover_obsolete_registry_ownership_locked`
     (`:3310-3360`), which re-raises the hold only on start/advance/document refresh.
   - Scenario: a schema-19 Government case confirmed under D-101 waits at
     `TARGET_CONFIRMATION_REQUIRED`. After upgrade the panel shows the statute form; the RM
     submits a correct statute and gets "Government status is confirmed only for a current
     pre-submission Government case."; target confirmation fails `CLM_NOT_READY`. The case is
     stuck for browser users (only an API `/resume` recovers it). D-125 G5 and the UAT guide say
     the RM simply confirms again.
   - Required fix: make the re-confirmation reachable without weakening any check, e.g. run the
     existing revocation (`_recover_obsolete_registry_ownership_locked`, or the same
     `government_revoked` restoration) inside the lock before the open-hold check so a revoked
     Government checkpoint re-opens `GOVERNMENT_STATUS_REQUIRED` and the confirmation proceeds
     with the normal concurrency checks; or surface an explicit server-authorised Continue
     control for this state. Add a backend test: legacy-shape confirmation on a case at
     `TARGET_CONFIRMATION_REQUIRED` -> re-confirm with statute succeeds (or the documented control
     re-raises the hold) and no target write occurs before it. Correct D-125 G5/UAT text if the
     behaviour differs.

Not required (advisory, record in the PR for Shane):
- L1 bracketed free text stored and echoed (section 6).
- L2 no Unicode normalisation (NFC/NFKC) before comparison; fails closed only.
- L3 a different trailing year matches (spec-defined rule).
- L4 a schema-19 case frozen before its first GoldTier write is refused at dispatch
  (`CLM_TARGET_CONFIRMATION_REQUIRED`, `clm_orchestration.py:646-656`) and cannot be re-confirmed
  while the snapshot exists; fail-closed, edge case, document as a migration limitation.
- L5 submitted/completed legacy Government cases now display "confirmation required" in the
  panel (history display), `api_models.py:1617-1621`.
- Info: inline mismatch wording uses `: "<instrument>".` instead of the spec's `(<instrument>)`
  (deliberate in 9ae3afe; Tasha to accept).

## 8. Readiness

Not ready for pre-PR / push until M1 is remediated and a recheck (R1) reviews the corrected
delta. The recheck can reuse the unchanged evidence above and needs only the changed backend
scope, the new test, the affected persistence/entity-type suites and the E2E selector if the UI
changes. No live ACRA or real GoldTier claim is made or affected (Mock/Local only). Readiness
does not authorise starting another task.

## 9. Git Status

- Branch `feat/d125-government-founding-statute`, HEAD 9ae3afe, upstream unset, not pushed.
- Tracked/staged changes: none. Untracked: only this report.
- Scratch files (probes, E2E selector/results/log) are in the session scratchpad `qg/` folder,
  outside the repository.
- No implementation fix, test change, commit, push, merge, rebase, reset, stash or branch change
  was made by the reviewer. `.env` was not read.
