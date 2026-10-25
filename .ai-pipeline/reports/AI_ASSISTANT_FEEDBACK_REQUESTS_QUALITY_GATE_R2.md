# AI Assistant feedback, enhancement requests and single-reviewer mode: independent Quality Gate R2 (recheck)

This is a focused Stage 3 recheck under `fyp-quality-gate`. It reviews the delta that
corrected R1-F1, and reruns the evidence that delta invalidated. Evidence for unchanged
content is reused from R1 and Stage 2, as listed in section 4.

- **Change class of the corrected delta:** PERSISTENCE (assistant SQLite migration dispatch),
  plus its test and one ADR sentence.
- **Independence:** I did not write or remediate this change. I wrote only this report, and
  I did not read `.env`. Probes and code exports are only in the session scratchpad.

## 1. Executive result

**Verdict: PASS.**

- R1-F1 is fixed for both branch-only shapes (`6d090a7` and `81a59c2`). I checked this with
  stores built by those commits' own code, not only with the simulated shapes in the test.
- On a store that is already complete, the v4 step now runs on every open but only adds two
  `PRAGMA table_info` reads. It writes nothing and does not rebuild any table.
- Upgrades from main v3, v2 and v1 still pass.
- Nothing else in the reviewed content changed since `0ed9055`.
- No R1 informational note became a required fix. I add three informational notes (I6–I8).
  None of them is required.
- This verdict does not authorize commit, push, PR or merge. **D-076 still needs Shane's
  explicit acceptance before merge.**

## 2. Reviewed identity (frozen)

- **Repository:** `/Users/tasha/Documents/GitHub/data-dividends-zero-touch-clm`, branch
  `feat/ai-assistant-feedback-requests`.
- **Reviewed candidate:** HEAD `d5dd81f4b4426a46898668e38606b57422a96cd4`, tree
  `9c27f7198fb6cf5daad9ec062e9f3f08b9be0e08`. The working tree was clean at the start.
- **Integrated `origin/main`:** `9e47b4fc000426d2609ba5310e0e9bb0b66fb5e4` (PR #101).
  - `git merge-base HEAD origin/main` equals it, and the branch is 0 behind and 8 ahead.
  - I used the local `origin/main` ref and did not fetch.
- **Previous candidate:** `0ed9055` (R1: PASS WITH MINOR FIXES, R1-F1).
- **Corrected delta:** `git diff 0ed9055 d5dd81f` touches five files.
  - **Report-only commits (confirmed):**
    - `51b7a2f` (parent `0ed9055`) adds only
      `.ai-pipeline/reports/AI_ASSISTANT_FEEDBACK_REQUESTS_QUALITY_GATE.md`.
    - `3565394` (parent `51b7a2f`) adds only `…_QUALITY_GATE_R1.md`.
    - `git diff --name-only 0ed9055 3565394` lists only those two reports.
  - **`d5dd81f` (parent `3565394`):**
    - `apps/assistant/ai_assistant/knowledge/store.py`: +3/−1. The dispatch at `:335` is now
      `<= 4`, with a two-line comment at `:333-334`.
    - `apps/assistant/tests/test_knowledge_review.py`: the reset-to-'3' test is replaced by
      `test_a_branch_only_v4_store_gains_its_missing_columns`, which is parametrized over
      `6d090a7` and `81a59c2`.
    - `docs/decisions/ADR-012_AI_ASSISTANT_KNOWLEDGE_LOOP.md`: one added sentence at `:302-303`.
  - `_migrate_to_4` itself is unchanged since `0ed9055`. Only when it is called changed.

## 3. R1-F1 verification

**Real schemas of the branch-only commits.** I compared the `_SCHEMA` DDL of each commit with
HEAD's DDL. Apart from these columns, the DDL is identical:

| Commit | `reviews.single_reviewer` | `feedback.close_reason` | `feedback.entry_version` | Stamp | v4 dispatch |
|---|---|---|---|---|---|
| `6d090a7` | missing | present | missing | 4 | `< 4` |
| `81a59c2` | present | present | missing | 4 | `< 4` |
| HEAD `d5dd81f` | present | present | present | 4 | `<= 4` |

The test's `EARLY_V4_SHAPES` drop exactly these columns, so the test models the real shapes.

**Stores built by the old code, then opened by HEAD (scratchpad probe).** For each commit I
used its exported code to build a store with four "Not helpful" requests:

- one whose fix a second reviewer approved (`resolved`);
- one with a pending fix (`drafted`);
- one closed with a reason;
- one left open.

I then opened each store with the code exported from `d5dd81f`:

| Check | `6d090a7` store | `81a59c2` store |
|---|---|---|
| Missing columns added; stamp stays `'4'` | yes | yes |
| `feedback`, `reviews` and `entries` row counts kept, old values kept in order | 4/1/2 kept | 4/1/2 kept |
| `reviews()` and `single_reviewer_approvals()` | work; the old approval reads as `single_reviewer=False` | same |
| New fix on the open request, then a confirmed self-approval | request `resolved`; `{'resolution.c@v1'}` | same |
| Two further reopens | every table byte-for-byte unchanged | same |
| Same store opened by `0ed9055` code (control) | columns not added; `KeyError: 'entry_version'` | same |

**The new test against the old dispatch.** I copied the `0ed9055` code into the scratchpad and
added HEAD's `test_knowledge_review.py`. Both cases fail there:

- `test_a_branch_only_v4_store_gains_its_missing_columns[6d090a7]`: FAILED;
- `test_a_branch_only_v4_store_gains_its_missing_columns[81a59c2]`: FAILED.

Both fail on the column assertion. At HEAD both pass. This confirms the implementer's claim.

**Idempotence and safety of running the v4 step on every open.** I traced every SQL statement
on a reopen of a current v4 store, with the same harness for `0ed9055` and `d5dd81f`. The
`CREATE … IF NOT EXISTS` lines are the same in both and are omitted below:

- **`0ed9055`:** `PRAGMA foreign_keys`, the `sqlite_master` and `meta` reads, then `BEGIN`,
  `INSERT OR REPLACE INTO meta`, `COMMIT`.
- **`d5dd81f`:** the same statements plus only `PRAGMA table_info(reviews)` and
  `PRAGMA table_info(feedback)`.
  - No `ALTER`, no rebuild and no `commit()` from `_migrate_to_4` runs.
  - Every table's data is unchanged.
  - The meta write is the same as before; it is not new.

**Commit behaviour inside `__init__`.**

- `_migrate_to_4` can only reach its `ALTER` or its rebuild when a column is missing.
- When a column is missing:
  - each `ALTER … ADD COLUMN` is committed on its own;
  - the rebuild is one explicit `BEGIN … COMMIT` script.
- This code is unchanged since R1, which accepted it.

**Upgrades from older stores.**

- **Main v3:** I built a store with the exported `9e47b4f` code, then opened it with HEAD,
  twice. The result is stamp `'4'`; `close_reason`, `entry_version` and `single_reviewer` are
  added; the rows are kept; the CHECK constraint includes `resolved`.
- **Tests at HEAD:** these pass:
  - `test_a_store_from_before_this_change_is_migrated`;
  - `test_a_version_2_store_gains_the_revision_column_and_keeps_its_entries`;
  - `test_a_version_3_store_gains_request_statuses_and_close_reasons`;
  - `test_a_v2_in_place_editor_cannot_decide_after_migration`.

**Busy and concurrent stores.**

- **Busy store:** another connection held `BEGIN IMMEDIATE` for 1 s while a current v4 store
  was opened. The open succeeded after 1.1 s, the same as `0ed9055`. The added PRAGMA reads
  run under a reserved lock.
- **Concurrent first opens (30 trials of 4 processes each):**
  - On a branch-only store, 3 of the 4 processes in each trial fail with
    `OperationalError: duplicate column name`.
  - In every trial the store ends fully repaired with all rows kept, and the next open
    succeeds.
  - The same race already exists at `0ed9055` on the main v3→v4 upgrade (89 of 120 opens).
  - See I6.

**The local ignored development store** (`apps/assistant/data/knowledge/knowledge.sqlite3`,
which R1 found in the `6d090a7` shape). I opened it read-only (`mode=ro`) and read only the
schema and aggregate status counts:

- It is now stamped 4 and has `entry_version` and `single_reviewer`, so it has already been
  repaired.
- Its only `drafted` rows are `helpful=1` ratings, which the request flow ignores.
- I6 and I7 therefore do not affect the demo store.

**Conclusion:** R1-F1 is **fixed**.

## 4. Checks

**Rerun by me on `d5dd81f`** (the repo `.venv`, Python 3.12.14, macOS; the backend checks were
run from `apps/assistant`).

| Check | Result |
|---|---|
| `../../.venv/bin/python -m pytest -p no:cacheprovider` | **1189 passed** in 30.95s, exit 0 (R1: 1188; +1 net from the parametrized test replacing one test) |
| `ruff check ai_assistant tests --no-cache` | All checks passed! |
| `ruff format --check ai_assistant tests --no-cache` | 60 files already formatted |
| `mypy ai_assistant` | Success: no issues found in 26 source files |
| Focused migration tests (`-k "branch_only_v4 or version_3_store or version_1 or version_2 or migrat or old_store or older"`) | 11 passed, including both new cases |
| The new test against the `0ed9055` code (scratchpad) | 2 failed, as expected |
| Old-commit stores, SQL trace, busy-store and concurrent-open probes | As described in section 3 |
| `git diff --check origin/main...d5dd81f` and `git diff --check 0ed9055 d5dd81f` | clean |
| `python3 scripts/pre_pr_check.py` on clean HEAD `d5dd81f` (before this report existed) | **SUMMARY: PASS (0 unsafe conditions, 1 warning(s))**. The warning is "API/config/shared type files changed: apps/assistant/ai_assistant/config.py", the expected new setting. |
| `python3 scripts/check_architecture.py` | ARCHITECTURE CHECK: PASS |
| `python3 scripts/check_project_state.py` | PROJECT STATE CHECK: PASS |
| Whitespace in this report (`grep -n ' $'`) | none |

**Reused, not rerun.** No frontend or E2E file changed since the evidence below was run:
`git diff --name-only 0ed9055 d5dd81f` lists no `apps/frontend` path.

| Check | Source | Result |
|---|---|---|
| Focused vitest (`KnowledgeReview.test.tsx`, `AiAssistantPanel.test.tsx`) | R1 on `0ed9055` | 2 files, 29 passed |
| `npm run typecheck` | R1 on `0ed9055` | exit 0 |
| `npm test` | Stage 2 on `e8ec522` | 1013 tests: 1012 passed, 1 failed. The failure is the pre-existing `ViteHistoryFallback.test.ts` baseline failure, which also fails on `origin/main`. |
| `npm run build` | Stage 2 on `e8ec522` | ok |
| E2E `--grep "PR89 streaming"` | Stage 2 on `e8ec522` | 1 passed |

The review of authorization, redaction, single-reviewer control, CAS and acceptance criteria
(R1, sections 6–9) is reused unchanged, because none of that code changed.

## 5. Findings

**Required findings: none.**

**R1 informational notes I1–I5:** none of them became required. They concern
`docs/ARCHITECTURE.md` wording, `knowledge_api.py` error order, helpful-rating status, the
`illustrative` flag on guidance fixes and the Review window history. The corrected delta
touches none of these, and they stand as R1 recorded them.

**New informational notes (no fix required):**

- **I6: concurrent first open of a store that needs a column.**
  - **Where:** `store.py:335` with `_migrate_to_4` at `:979-990`.
  - **Behaviour:** if several processes open a store that needs a column at the same moment,
    all but one can fail with `duplicate column name`. Each of them reads the table columns
    before the first `ALTER` commits.
  - **Why it is not required:**
    - The failure is loud, nothing is lost, the store ends fully repaired and the next open
      succeeds.
    - The same race already exists on the main v3→v4 upgrade at `0ed9055`.
    - At runtime the store is built once per process (`knowledge/factory.py:22`), and the
      documented run is a single uvicorn process.
  - **Possible hardening (optional):** treat `duplicate column name` as success in those
    `ALTER`s, or take `BEGIN IMMEDIATE` around the migration block.
- **I7: requests already `drafted` in a branch-only store stay linked only by entry id.**
  - **Behaviour:**
    - Earlier builds linked a "Not helpful" request to its draft by entry id only. After the
      repair, `entry_version` on those rows is `NULL`.
    - The version-exact matches at `store.py:598-602` and `:615-619` therefore never match
      them. When their pending draft is approved or rejected, the request stays `drafted`.
    - A `drafted` request cannot be redrafted or closed, because only open requests can.
    - I reproduced this with a `6d090a7` store and an `81a59c2` store.
  - **Why it is not required:**
    - It affects only data written by unmerged branch builds. It never applies to `main`,
      where only `helpful=1` rows are ever `drafted`, and those are outside the request flow.
    - No data is lost.
    - The demo store has no such rows (section 3).
    - The new test seeds only an open request, so it does not cover this case.
  - **Possible remedy if wanted:** backfill `entry_version` during the repair for
    `helpful=0 AND status='drafted'` rows whose linked entry has one pending version. Or the
    owner records that branch-era stores with pending request drafts should be recreated.
- **I8: one unwrapped ADR line.**
  - **Where:** `docs/decisions/ADR-012_AI_ASSISTANT_KNOWLEDGE_LOOP.md:303` is 104 characters,
    while its neighbours wrap at about 90. The text itself is accurate.
  - **Why it is not required:** it is cosmetic, and no check enforces a line length.

## 6. Remaining preconditions for publication

1. **D-076 owner acceptance:** Shane must explicitly accept D-076 (single-reviewer mode, on by
   default, relaxing D-074's two-person rule) before merge, whatever this verdict says.
2. **Unchanged content:** the reviewed content must stay `d5dd81f`'s tree, plus this report
   only. Any further change to code, tests or docs needs a fresh independent recheck.
3. **Explicit owner authorization** is needed for commit (of this report), push and PR
   creation. A repository-owner human merges.
4. **Pre-PR state:** before the PR, `integration-safe-development` and `pre_pr_check.py` must
   run on the final committed state, including this report's commit. Fetch the latest `main`
   and reassess; I did not fetch.
5. **Residual risks carried from R1:**
   - no browser E2E for the feedback note, the Review window or the confirm step;
   - redaction is limited to case-supplied values and patterns;
   - POLICY_APPROVE stays PROJECT_DEFINED_PROVISIONAL and Q-014 stays UNKNOWN_BLOCKED;
   - the pre-existing `ViteHistoryFallback.test.ts` baseline failure.

## 7. What changed and Git status

- **Changed by the corrected delta:**
  - persistence (SQLite) migration behaviour: the v4 column repair now also runs on stores
    stamped 4;
  - the matching test;
  - one ADR sentence.
- **Not changed by the delta:** API and types, the configuration surface, business rules,
  mappings, connectors, auth and security, architecture ownership and provider status.
- **Git:** branch `feat/ai-assistant-feedback-requests` at HEAD `d5dd81f`. Nothing is staged
  and there are no tracked modifications. The only untracked file is this report.
- **No other changes:** I made no implementation fix, commit, push, stash, reset, PR or merge,
  and started no other phase.

**Verdict: PASS**
