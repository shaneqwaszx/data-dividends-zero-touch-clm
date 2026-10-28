# D-095 AI Assistant — independent Quality Gate, rounds R1 to R3

Branch `claude/gracious-lovelace-bjvh2z`, base `origin/main` `7119905`. Each round was run by
an independent, read-only reviewer agent (no edits, no network calls to OpenRouter or any
external host). The reports are reproduced as delivered, lightly reflowed; scratch paths are
the reviewer's own temporary files. A later round's report covers the owner-review correction
(`D095_AI_ASSISTANT_QUALITY_GATE_R4.md`).

| Round | Reviewed SHA | Verdict | Required findings | Fixed in |
| --- | --- | --- | --- | --- |
| R1 | `5068e022fd2642d763ef3d0d02123d995a2e5e0b` | FAIL | F1, F2, F3 (F4, F5 optional) | `951e7e9` |
| R2 | `951e7e9f41ecbb69abe3c8cb52fa7713eaf52eaa` | FAIL | R2-1 | `1f18ce1` |
| R3 | `1f18ce1ca90338033a81eda4a04767111984377b` | PASS | none | — |

## R1 — `origin/main..5068e02` (one commit, 32 files): FAIL

- **F1 — BLOCKER, REQUIRED.** `apps/assistant/ai_assistant/credentials.py` was not in the
  commit: `.gitignore:14` (`credentials*`) ignores it, yet `model_admin.py`, `model_factory.py`
  and `remote_test.py` import it. A clean checkout fails with `ImportError`; every passing test
  passed only because the ignored local file was present (false success). Fix: commit the
  module without weakening the ignore rule.
- **F2 — MAJOR, REQUIRED.** `synthetic_eligibility._trusted_values` trusted every
  `DOCUMENT_IDP` reconciliation observation on a verified document, but the backend reports a
  reviewer's typed correction as a `DOCUMENT_IDP` observation (`source_system=HUMAN_REVIEW`,
  `evidence_reference=DOCUMENT_REVIEW_*`). A typed value such as `"WONG KAH WEI, 7 REAL HOME
  ROAD"` therefore passed `SYNTHETIC_VALUE_NOT_GROUNDED` and was sent (reproduced). Fix: never
  trust review corrections; trust only extraction observations of a verified document.
- **F3 — MAJOR, REQUIRED.** The committed `synthetic_boundary.json` was stale
  (`test_the_boundary_file_is_current` failed; code vocabulary `command`, `inherited`,
  `minutes`). Fix: regenerate.
- **F4 — MINOR, OPTIONAL.** Documents were checked by name, media type and size only; the
  docstring wrongly said an edited document is refused (a same-size edit passes).
- **F5 — MINOR, OPTIONAL.** A race between the key the preflight checks and the key the chat
  call uses if HR changes the key between the two reads.
- **F6 — ADVISORY.** Provider limit shown after a key change may be another key's; daily cap
  0 labelled invalid; CLI ignores `.env` cap; reconcile drift not counted in the day (breaker
  covers drift above US$0.05); identical concurrent messages share one ticket (second fails
  closed); assistant history may use any words (documented).
- **No defect found in:** D-094 without the flag; ticket bypass; daily cap atomicity,
  open-call counting, setting bounds, coverage of every reservation path, preflight and
  effective minimum; credential routes (HR capability plus re-check, Origin required, rate
  limit, hand-parsed body, env/.env keys protected, no key in responses, audit, logs or browser
  storage); officer lines (Mock ACRA provenance only, topic-only, template-checked).
- **Ran:** full assistant suite 2,530 passed / 2 failed (root-only
  `test_a_read_only_ledger_fails_closed`; F3); focused files 298 passed / 1 failed (F3); clean
  `git archive` import (ImportError, F1); boundary `--check` stale (F3); eligibility `--check`
  current; F2 reproduction confirmed; frontend AiModelManagement 18/18; `tsc` exit 0;
  `git diff --check` clean; secret scan passed.

## R2 — `5068e02..951e7e9`: FAIL

- F1 fixed (module renamed `key_sources.py`, tracked, not ignored; clean-archive import
  works). F2 fixed without over-refusal (genuine extraction observation with the verified
  document id still eligible; `HUMAN_REVIEW` correction refused; matching on `document_id` is
  correct because the backend projects `document_id=source_record_id`). F3 fixed. F4 fixed.
  F5 fixed (`_pinned()` reads the key once for rebuild and preflight; `forget_provider()` on
  key change and after HR PUT/DELETE).
- **R2-1 — MINOR, REQUIRED.** `docs/PROJECT_STATE.md`'s 724 CRLF lines were rewritten to LF
  for a one-word change (formatting churn on a shared state file). Fix: restore the bytes and
  reapply only the edit.
- **Ran:** full assistant suite 2,534 passed / 1 failed (root-only); frontend 18/18;
  clean-archive import and both `--check` scripts OK; F2 reproductions; `git diff --check`
  clean; secret scan passed.

## R3 — `951e7e9..1f18ce1`: PASS

- Only `docs/PROJECT_STATE.md` changed; 724 CRLF lines as on main; against main the file adds
  only the D-095 section (+22 lines). No other file changed its CRLF count.
  `git diff --check 7119905..1f18ce1` clean. No code changed since R2, so its results carry
  over.
- `QG VERDICT: PASS` — reviewed SHA `1f18ce1ca90338033a81eda4a04767111984377b`.
