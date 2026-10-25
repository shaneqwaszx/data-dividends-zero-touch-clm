# Re-QG 2: entity effective interests (N1 remediation)

**Verdict: PASS**

The verdict covers tree `1b4b382ea294cf828d323818c8924bb78e0dd7bb`. This was a read-only, independent review of the N1 remediation delta only.

## 1. Tree

- **Worktree:** `C:\Users\shane\Desktop\claude-worktrees\generalized-poc-acceptance-int-20261025`
- **HEAD = origin/main:** `5de7f24c2dbf678bbb9de02ad627be777bc2f28c`
- **Method:**
  - Copied the real index from `git rev-parse --git-path index` to `reqg2-entity\index_copy`.
  - Ran `GIT_INDEX_FILE=<copy> git add --pathspec-from-file=candidate_paths_int5.txt` (48 paths), then `git write-tree`.
- **Result:** `1b4b382ea294cf828d323818c8924bb78e0dd7bb`, which **equals the claim**.
- **Real index:** not touched. The worktree status count was 49 before and after; that is 48 listed paths plus the untracked `.ai-pipeline/reports/GENERALIZED_POC_ACCEPTANCE_D085_D086_REPORT.md`, which is outside the candidate list as before.

## 2. Delta from `2dba7843273772c18fedce70f63b00d0a6af0d6b`

`git diff --stat` and `git diff --stat --ignore-cr-at-eol` are identical:

| File | Change |
|---|---|
| `apps/backend/tests/test_simulation_calculation_status.py` | +40/−5 |
| `docs/decisions/DECISION_LOG.md` | +4/−5 |
| **Total** | **2 files, +44/−10** |

- **No product code change:** no file under `app/` differs.
- **No EOL churn:** both blobs have 0 CR bytes, old and new.
- `git diff --check`: clean.

## 3. Mutation proof

Each run used scratch copies of `apps/backend` (`base`, `over`, `cycle`) under `reqg2-entity\`, never the worktree.

**Setup**
- Repo venv Python.
- `PYTHONPATH=<copy>;<worktree root>`
- `PHASE12_MONGO_URI` unset, `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider`.
- `app.__file__` resolved to each copy's `app\__init__.py`, or for the last row, to the worktree's.

**Results**

| Variant | Mutation in `OwnershipAnalysisService.entity_effective_interests` | Result |
|---|---|---|
| base copy | none | 26 passed |
| over | `> Decimal("100")` becomes `> Decimal("100") and False` (over-100 rule disabled) | **1 failed, 25 passed: KILLED**. Failure at line 353, `entity_effective_interests(over) == {}`. The service returned 5 entities. The oracle assertions before it (L2 = 140, no PATH/DEPTH/CYCLE issue) passed, so the graph now really reaches the over-100 rule. |
| cycle | `CYCLE_DETECTED` removed from the issue-code set | **1 failed, 25 passed: KILLED**. Failure at line 344, `entity_effective_interests(cyclic) == {}`. The oracle assertion `CYCLE_DETECTED in codes` passed first. |
| unmodified worktree | none | **26 passed** (`worktree.xml`) |

**Other checks**
- `ruff check --no-cache` and `ruff format --check` on the test file: clean.
- **Previous N1 is resolved.**
  - `_extra_edge` now goes through `model_validate` with the safe ID `SYNTHETIC-EXTRA-EDGE`, so a bad edge would raise in the test rather than be silently caught.
  - The oracle (`_entity_totals`) calls the same `build_ownership_graph` and `calculate_ownership_paths(include_entity_paths=True)` path.
  - Its hard-coded limits 8/64/256 equal the `config.py` defaults.

## 4. Doc reflow

- **Meaning kept:** after collapsing whitespace, the old and new `DECISION_LOG.md` are byte-identical (same md5). Only line breaks moved, so the meaning is unchanged.
- **N4 resolved:** the ragged "only: never a candidate," line is gone, and every line is 91 characters or fewer.
- **Matches the code** at `ownership_analysis.py:1060-1109`. The service fails closed on:
  - a path limit, a depth limit or a cycle (issue-code set);
  - any entity total above 100;
  - an `OwnershipGraphError`, `ValidationError` or `KeyError` during the build;
  - a non-analysed state, or no root or relationships.

## 5. Notes (no P0, P1 or P2)

- **P3, optional:** the oracle hard-codes 8/64/256 instead of reading the service's limits. If the five-layer test settings ever changed these limits, the oracle could diverge from the service. Today they match.
- **Carried from the previous re-QG, unchanged:** N2 (no direct deep-chain test) and N3 (an issuer whose holders total more than 100 while every entity total stays at or below 100 is still shown). Both are documented and P3.

## 6. Not executed by this gate

- the full backend suite (running separately in the worktree);
- frontend (vitest, tsc), because there is no frontend delta;
- Playwright;
- physical Mongo.

Everything here is Mock or Local evidence; nothing is Live. Publication requires explicit owner authorization.
