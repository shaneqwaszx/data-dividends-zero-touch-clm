# Token-Efficiency Governance — Evidence

## Implementation slice

- State: first independent gate preserved as `FAIL`; remediation evidence green; fresh
  independent gate pending.
- Current source identity: uncommitted branch content based on
  `83f46e20a9ad36ae61aacb0f470c1404c4732d64`.
- Focused: `python -m unittest tests.test_dev_context -v` — PASS, 18/18 in 6.629s.
- Broad: affected governance/tooling unittest modules — PASS, 136/136 in 59.936s.
- Direct: project state, architecture, tooling config, policy authority, external
  provider readiness, and secret checks — six PASS.
- Static: Ruff for `scripts/dev_context.py` and `tests/test_dev_context.py` — PASS.
- Benchmark: 43.0% routine mean LF-normalized UTF-8-byte reduction; high-risk classes
  read the full current canonical set and triggered authority/skill references.
- Product suites: not run; no product/runtime surface changed under `DOCS_ONLY` and
  `CI_TOOLING` classification.

## Attempt history

- The intentional RED run proved all new selector APIs/CLI behaviors were absent.
- Existing temporary-Git fixture tests also hit sandbox permissions; the same tests ran
  successfully with managed permission. Nine exact task-created failed-run temp
  directories were verified under repository `tmp` and removed; older temp artefacts
  were untouched.
- One governance-surface assertion contained a literal `+` in its expected string;
  correction produced the final 17/17 result. No design repair cycle was consumed.
- First independent QG: `FAIL`; `--change-class " "` exited 0 because normalization
  filtered empty elements before validation and emitted a narrow manifest labeled
  `FULL`.
- Remediation TDD route: strict. The new API/CLI regression failed in all four empty and
  whitespace subcases before the repair, then passed after `select_context` rejected
  any explicitly supplied stripped-empty element. The invalid filter responsibility is
  retired; no fallback, second owner, or compatibility path remains.
- A sandboxed 18-test rerun again hit the known nested-Git permission boundary and made
  nine exact disposable fixture directories; they were verified within repository
  `tmp`, removed, and the managed rerun passed 18/18.

## Drift

- Scope, compatibility, authority, and Phase 22 boundaries remain aligned.
- No completion or publication authority is claimed by this evidence record.
