# AI Assistant explanations (D-090, ADR-012 Amendment 2) - independent quality gate, recheck R4

Reviewer: fresh independent QG subagent. It did not author or remediate the reviewed content
and did not run the first gate, R1, R2 or R3. Date: 2026-10-26. Skill:
`.agents/skills/fyp-quality-gate/SKILL.md` and `references/report-template.md`, read in full;
AGENTS.md section headings and the review/verification sections read. Earlier reports read:
first gate (FAIL on `a49db57`), R1 (PASS), R2 (PASS on `30b3e7f`), R3 (PASS WITH MINOR FIXES on
`70a97e2`: M1 stale eval snapshots, M2 `_shown` trusted `added_lines`; notes N10, N11).

## Reviewed content identity

| Item | Value |
| --- | --- |
| Checkout | `/Users/tasha/Documents/GitHub/dd-clm-qg-explanations`, detached, clean at start |
| HEAD | `445dd8fa3cb638f676c717150f2b9b7de5737437` |
| Tree | `f8baaa2ae223b7ca4f10b38071ebf07807494b7d` |
| Base | `origin/main` `769c14939491de47ea5438923cf9ac5548e60bd6` (#115) |
| Recheck delta | `git diff 70a97e2 445dd8f`: `assistant_eval/runner.py` (+5/-6), `tests/test_explanations.py` (+11, addition only), `tests/fixtures/eval/snapshots.json`, `tests/fixtures/eval/gold.json` (1 line), ADR-012 Amendment 2 Change 4 (+6/-2), and the committed R3 report |
| Whole-branch diff | `git diff 769c149...445dd8f`: 25 files, +2656/-163. No backend, E2E, script, config or production frontend path |

## 1. Executive result

**PASS WITH MINOR FIXES.** Both R3 minors are fixed in code and data: `_shown` now counts every
non-offered line as unmapped wherever it is (hostile `added_lines` cannot hide one), and #115's
snapshots and stubs were regenerated faithfully with the harness's own commands (I reproduced
both byte for byte; only new catalog lines and the prompt version changed; `gold.json` changed
only its hash and stays 84 unlabelled stubs). The R3 delta does not touch any runtime path, so G6,
the 6/8 limits and never-remove-streamed stand as R3 verified them. One bounded documentation
fix remains: the new N10 sentence in ADR-012 (and the matching PR-draft line) says the harness
scores the model's selection *before* the 6/8 trim, which is the opposite of what the harness
does.

## 2. Acceptance checklist

| Claim | Result | Evidence |
| --- | --- | --- |
| M2: every non-offered line counted as unmapped wherever it is | VERIFIED | `runner.py:166-178`: `line not in by_text` -> `unmapped += 1` before any `added` test. Probe (section 4): blank lines, surrounding whitespace, CRLF, duplicates, negative / out-of-range / string positions, "every position added", near-miss text: non-offered lines counted in every case. |
| M2: only offered lines at added positions left out of the selection | VERIFIED | `runner.py:175-177` (`elif index not in added`). Positions match: the service builds `added_lines` from `validation.text.splitlines()` (`main.py:239-241`) and the runner enumerates `done["answer"].splitlines()` on the same string (`runner.py:276-279`). |
| M2 test | VERIFIED | `test_explanations.py:842-850`: a non-offered line at a claimed-added position is counted (`(("a",), 1)`), and without `added` both offered lines are shown. Passes. |
| M1: fixtures rebuilt with the harness's own commands | VERIFIED | Re-running `snapshot` and `stubs` on `445dd8f` reproduced `snapshots.json` byte-identically (`cmp`) and left `gold.json` unchanged. |
| M1: regeneration faithful to #115 | VERIFIED | Against `769c149`: same 84 turn keys; per turn only `offered`, `part_chars`, `prompt_fingerprint` change; `built_with` changes only `prompt_version` (3100a3d5 -> e5ae1c2d); `lines` gains 18 `C-` catalog lines, none removed or altered; every `K-` knowledge line and every turn's knowledge offering unchanged. `scenarios.json` unchanged. |
| M1: `gold.json` only `snapshot_sha256`, all stubs | VERIFIED | `git diff 769c149 445dd8f -- .../gold.json`: one line (`9341411d...` -> `1421eedb...`); 84 turns, status `stub`, 0 with any label or `labelled_by`. |
| `evaluate_answers.py check` current | VERIFIED | `snapshots are current (84 turns, sha256 1421eedb7fd536ea)` |
| Self-test runs | VERIFIED | Section 4: `self-test-perfect` 84 scored, P/R/F1 1.0, unsafe 0, drift 0; `-injection`, `-prose` identical to the same runs on `769c149`; `-random` differs only because more lines are offered. |
| N10/N11 wording (ADR-012 Amendment 2 Change 4) | **N11 VERIFIED; N10 INACCURATE (R4-M1)** | Section 5. |
| G6, 6/8 limits, never-remove-streamed, content-free telemetry | VERIFIED (unchanged since R3) | `git diff 70a97e2 445dd8f` touches no `ai_assistant/` file; `with_required_lines` (`guardrails.py:729-767`), `main.py`, `telemetry.py` identical to R3's reviewed tree, so R3's probes (366 answers, 0 non-allowed lines) and R2's 12,000-case unit probe stand. |
| #115's tests unchanged | VERIFIED | `git diff 769c149 445dd8f -- tests/test_eval_harness.py tests/test_telemetry.py assistant_eval/ (except runner.py) scripts/ ai_assistant/telemetry.py`: empty. |
| PR draft lists runner change, fixture refresh, N1/N4/N5/N8-N11 | VERIFIED, with R4-M1 | `scratchpad/pr-body.md:21-39`. Line 39 repeats the N10 inaccuracy. |

## 3. Contract and integration findings

- The runner change and the fixture refresh are both in #115 (Shane's) area and are disclosed
  for him in the PR draft (`pr-body.md:34-38`). The refresh is the documented path
  (`apps/assistant/README.md` "Offline evaluation") and is reproducible; no owner label was
  touched or invented.
- No backend, schema, connector or configuration change; no live ACRA, GoldTier or sponsor claim.

## 4. Tester and adversarial findings

Run by this reviewer on HEAD `445dd8f` / tree `f8baaa2`, local macOS, repository venv,
`PYTHONDONTWRITEBYTECODE=1`, caches disabled or in the scratchpad:

| Check | Result |
| --- | --- |
| `cd apps/assistant && python -m pytest -q -o addopts="" -p no:cacheprovider` | **1462 passed** in 54 s |
| `ruff check --no-cache .`; `ruff format --check --no-cache .` | All checks passed; 78 files already formatted |
| `mypy ai_assistant`; `mypy assistant_eval` (cache in scratchpad) | no issues in 27 files; no issues in 9 files |
| `git diff --check 769c149...445dd8f` | clean |
| `scripts/check_architecture.py`; `scripts/check_secrets.py` | PASS; no supported secret patterns |
| `evaluate_answers.py check` | snapshots are current (84 turns, sha256 1421eedb7fd536ea) |
| `snapshot` (to its default `data/eval/`), `stubs` | output byte-identical to the committed fixtures; `git status` clean |
| `run --model self-test-perfect` | turns_scored 84, drift 0, validity 1.0, unsafe 0, P/R/F1 1.0, primary 1.0, must_not 0, citation_turns 77 (same as main) |
| `run --model self-test-injection` | validity 0.2, unsafe 0, P 1.0, R 0.5, F1 0.6667, must_not 0 (identical to `769c149`) |
| `run --model self-test-prose` | validity 0.0, unsafe 0, F1 0.0 (identical to `769c149`) |
| `run --model self-test-random` | validity 1.0, unsafe 0, F1 0.0345, must_not 3 (`769c149`: 0.0714 F1, 10 must_not; the random draw differs because more catalog lines are offered) |
| `_shown` hostile probe (7 cases) | every non-offered line counted; `added` only ever removes offered lines from `shown` |

Run outputs: `scratchpad/qg-r4/run-*` and `scratchpad/qg-r4/main-run-*` (main from a
`git archive` copy). Hygiene note: `snapshot` and the `run` commands also create the ignored
`apps/assistant/data/` (default snapshot output and the module-level knowledge store); the
reviewer created it in the checkout and removed it again; nothing tracked was written.

Reused, not rerun (no frontend, backend, E2E or script path changed since `a49db57`): frontend
tsc OK, vitest 1084/1085 (known macOS-only `ViteHistoryFallback.test.ts`), build OK; official
full E2E on `a49db57` not green (31/115; diagnostic `--keep-going` 106 PASS / 9 FAIL, the same 9
on clean main); `assistant-streaming.e2e.ts:10` PASS on `70a97e2`. Keep-going is diagnostic, not
acceptance. No E2E run in this recheck. `pre_pr_check.py` not run (publication step). CI has no
`apps/assistant` job and is billing-blocked; all evidence is local, not hosted CI.

## 5. Code and architecture review

**R4-M1 (minor, documentation truthfulness) - the N10 sentence describes the harness wrongly.**
`docs/decisions/ADR-012_AI_ASSISTANT_KNOWLEDGE_LOOP.md:564-566`: "Both [the harness's scored
selection and `kept_lines`] describe the model's selection before unseen lines are trimmed to the
6/8 limits, so a model line counted there may not be in the final answer." That holds for
`kept_lines` (`main.py:203`, counted before `with_required_lines`), but not for the harness:
`_shown` reads the final `done["answer"]` (`runner.py:276-279`), so a model line trimmed by
`with_required_lines` (`guardrails.py:756-763`) is not in the answer and is never scored. R3's N10
said exactly this ("the model's selection minus lines the service trimmed"). The PR draft repeats
the error (`scratchpad/pr-body.md:39`). Fix: say `kept_lines` counts before the trim, and the
harness scores the model lines that remain in the final answer (after the trim). Two sentences;
no code.

Notes (no fix required):

- **N12:** the harness still trusts `added_lines` for *offered* lines: if a future service bug
  marked model-chosen lines as added, those lines would leave `shown`, and a model `must_not`
  violation could be hidden (probe "every position added": `shown` empty, unmapped still
  counted). Unsafe display can no longer be hidden, which was R3's concern. Optional hardening
  for Shane: accept an added position only when its line is one of `prep.plan.required`.
- **N11** wording is correct in substance; strictly, the harness skips a required line only when
  the service added it (a required line the model chose itself is scored). Optional precision.
- R1-R3 notes N1, N4, N5, N7 stand; N8, N9 closed in R3.

## 6. Security review

No secrets, `.env`, tokens or PII newly tracked; the fixture refresh contains only synthetic
scenario data, catalog text and hashes. No runtime path changed. M2's fix strengthens an offline
measurement. Findings: none blocking.

## 7. Required fixes

1. R4-M1: correct the N10 sentence in ADR-012 Amendment 2 Change 4 (`:564-566`) and in the PR
   draft (`pr-body.md:39`): the harness scores lines left after the trim; `kept_lines` counts
   before it.

Bounded, doc-only; a recheck needs only that diff (plus `git diff --check`).

## 8. Readiness

- Branch quality gate: **PASS WITH MINOR FIXES** on `445dd8f` / `f8baaa2` against `769c149`.
- Before a PR: R4-M1; Shane's acceptance of D-090 (incl. E2, which relaxes ADR-012 section C)
  and D-084; Shane's review of the `runner.py` change and the eval-fixture refresh; an owner
  decision on the not-green full E2E (pre-existing failures on main); Shane's manual-CI
  exception; `python scripts/pre_pr_check.py` on the clean committed tree.
- No live ACRA verification or real GoldTier integration readiness is claimed or affected.

## 9. Git status

- Checkout detached at `445dd8fa3cb638f676c717150f2b9b7de5737437`, tree
  `f8baaa2ae223b7ca4f10b38071ebf07807494b7d`; no staged or tracked modification; the only new
  file is this untracked report.
- No implementation, test or doc fix, commit, push, merge, rebase, reset or stash was made.

Reviewed HEAD: 445dd8fa3cb638f676c717150f2b9b7de5737437
Reviewed tree: f8baaa2ae223b7ca4f10b38071ebf07807494b7d

PASS WITH MINOR FIXES
