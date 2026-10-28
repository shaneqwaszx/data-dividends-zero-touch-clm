# AI Assistant D-094 post-merge docs closeout - Independent Quality Gate R2

Date: 2026-10-28. Reviewer: a fresh, independent QG recheck (round R2). This reviewer did
not author or remediate the reviewed content and did not run R1. Change class: DOCS_ONLY
(governance closeout). Scope: the corrected delta since R1
(`AI_ASSISTANT_D094_POSTMERGE_CLOSEOUT_QUALITY_GATE.md`, PASS WITH MINOR FIXES), plus
spot-checks of the R1 evidence this review reuses.

## Verdict

**PASS**

F-1 is closed, and the new wording matches the five committed D-094 gate verdicts. The A-2
rewording is accurate and neutral. Byte-level reconstruction proves that only these two
edits changed since R1. Every spot-checked fact matches primary evidence: merge topology,
tree equality, CI runs, ledger rows, cap and spend. A-1 is now better supported than R1
recorded: the shipped code attaches the D-094 notice to every answer the remote model
gives. Byte hygiene, the five checkers and the governance tests all pass. No required fix
remains.

## Frozen content identity

- Worktree `C:\Users\shane\Desktop\claude-worktrees\assistant-d094-closeout-20261028`, branch
  `docs/d094-postmerge-closeout-20261028`.
- HEAD = `origin/main` = `9a0dcd5f1af78214e987e38aab3b62f92a0cf168`. Uncommitted, nothing
  staged.
- Reviewed paths: `docs/PROJECT_STATE.md` and `docs/decisions/DECISION_LOG.md` (both ` M`).
  The only untracked file was the R1 report. No ignored or cache artefacts appeared outside
  `.venv`.
- Tracked diff sha256: `960fd930dc3d2273f6124e44c765e5f1e038173c23bcbf0a791e81ec92aef81c`.
- **CONTENT ID at START: `da77c0a725b89deefcdaf2ede4b6c057ec71acfc07b954bd73b5f6ecb06c82de`**
  (matches the expected value).
- **CONTENT ID at END: `da77c0a725b89deefcdaf2ede4b6c057ec71acfc07b954bd73b5f6ecb06c82de`**
  (unchanged; this report is the only file written).

## Delta since R1 (verified by reconstruction)

R1 recorded tracked diff sha256 `4434e7f9…f0de`. In a disposable scratch repository outside
the worktree, I rebuilt the HEAD blobs (`7a8cde5` and `34647eb`, identical to HEAD) and
replayed the current worktree files. That reproduced the current diff sha `960fd930…` exactly.
I then made exactly two substitutions in `docs/PROJECT_STATE.md` and changed nothing else:

- lines 1157-1158 replaced by
  `  - Independent Quality Gates R1 to R4 failed and were remediated; R5 passed. The pre-PR`
  / `    check passed.`
- line 1184 replaced by `  - Accept D-092.`

Those substitutions reproduce R1's diff sha `4434e7f9f8f9d9b2…` byte for byte. So the only
changes since R1 are the F-1 and A-2 lines; `DECISION_LOG.md` is unchanged since R1. The
diff stat is unchanged at 2 files, 71 insertions and 11 deletions.

## Remediation verification

| Item | Result | Evidence |
| --- | --- | --- |
| F-1 (`PROJECT_STATE.md:1157-1158`) "R1, R2 and R4 failed and R3 passed with minor fixes; each was remediated, and R5 passed." | **Closed** | Committed (tracked) verdict lines: R1 `…QUALITY_GATE.md:10` **FAIL**; R2 `…_R2.md:12` **FAIL**; R3 `…_R3.md:12` **PASS WITH MINOR FIXES**; R4 `…_R4.md:12` **FAIL**; R5 `…_R5.md:11` **PASS**. "Each was remediated" also holds for R3: R4's scope (`…_R4.md:5-7`) is the delta since R3, including the R3-1 docs fix and the R3-A2 and R3-A3 advisories. |
| A-2 (`PROJECT_STATE.md:1184`) "The owner's decision on D-092 (still PROPOSED)." | **Accurate, taken** | Neutral: it presumes no outcome. It is consistent with `PROJECT_STATE.md:1139` "D-092 is still PROPOSED" and `DECISION_LOG.md:1325` "D-092 stays PROPOSED". |

## Fact spot-checks (this session)

| Claim | Result | Primary evidence |
| --- | --- | --- |
| Merge `9a0dcd5`, single parent `c36b8af`, by `shaneqwaszx` on 2026-10-28 | Verified | `git rev-list --parents -n1 9a0dcd5` gives `9a0dcd5… c36b8aff…`. `gh pr view 123` gives MERGED, `9a0dcd5`, `shaneqwaszx`, `2026-10-28T01:14:16Z`, headRefOid `0f6e081` |
| Tree `57f59a2` equals `0f6e081`; `71e4654` product commit plus report-only commit | Verified | `9a0dcd5^{tree}` = `0f6e081^{tree}` = `57f59a2ab32f…`. `0f6e081` "docs(reports): D-094 quality-gate R1-R5 and pre-PR checklist"; `71e4654` "feat(assistant): D-094 …" |
| CI runs 40609162932 (push) and 40609235296 (`pull_request`), 9 jobs, 0 steps, billing-blocked | Verified | `gh api …/runs/<id>`: both on head `0f6e081`, `completed`/`failure`. `…/jobs`: total_count 9, steps 0, all `failure`. The billing annotation is reused from R1 |
| Ledger rows 29-34: 6 calls, settled, verified, `deepinfra/bf16`, US$0.001076 | Verified | Opened read-only (`file:…?mode=ro`): rows 29-34 are `settled`/`verified`/`deepinfra/bf16`, error None, anomaly 0. Charged 182+225+191+109+149+220 = **1076** micro-USD. Max id 34 |
| Committed spend US$0.006960; cap US$0.105884 | Verified | `ledger_meta`: baseline 309 + local charged 6651 = 6960, open reserved 0, breaker closed, cap 105884. `operator_events` #5 `cap_lowered` 105884 |
| Other R1-verified facts (test counts, pre-PR, T7 approval contents, smoke-test steps, open advisories) | Reused | The text is unchanged since R1 (proven above), and R1's evidence table covers it |

## A-1 reassessment (the D-094 notice on all four chat answers)

Claims: `PROJECT_STATE.md:1164-1165` "all four RM questions were answered by the model with
the D-094 notice"; `DECISION_LOG.md:1318` "with the T5 notice".

- The PR #123 body states the notice explicitly for Q1, Q2 and Q4. For Q3 it records
  "GPT-OSS: … plus the Mock/Live disclaimer" without naming the D-094 notice.
- The shipped code (tree `57f59a2` = `9a0dcd5`, the code that ran) enforces it structurally.
  `remote_gate` (`apps/assistant/ai_assistant/main.py:664-680`) returns `REMOTE_NOTICE`
  whenever the remote test model is used. `_model_reply` (`main.py:349-351`) always puts
  `lead_notice` first, followed by `validation.notice()`, which carries the Mock/Live
  disclosure (`guardrails.py:710-715`). Both the non-streamed path (`main.py:711`) and the
  streamed paths (`main.py:814`, `835`) pass `lead=REMOTE_NOTICE`. A model-answered Q3 can
  therefore carry the disclaimer only after the D-094 notice. The only exit without the
  notice is the case-data fallback, which is not "answered by GPT-OSS".
- The ledger shows 4 verified chat calls after the 2 qualification calls. The PR record
  attributes the Q3 answer to GPT-OSS. The implementer also reports the Q3 run output with
  the exact `REMOTE_NOTICE` text. (I could not observe that run output directly.)
- `DECISION_LOG.md:1277` defines T5 as exactly that notice, so "the T5 notice" is the
  correct cross-reference.

Assessment: adequately supported and not an overclaim. The residual gap is evidentiary:
the PR text does not spell out the Q3 notice. It does not undermine the claim. A-1 remains
**Advisory**, with lower concern than in R1.

## Overclaim and authority review

There is no new text beyond the two lines above. The R1 findings stand and I re-read the
changed regions:

- Live: "synthetic external evaluation on the owner's machine, never Live CLM behaviour"
  (`PROJECT_STATE.md:1173`). No provider classification changes.
- CI: `HOSTED_CI_NOT_EXECUTED - BILLING/INFRASTRUCTURE BLOCKED` (`PROJECT_STATE.md:1175`)
  and "not executed … that is not a pass" (`DECISION_LOG.md:1321`). Neither presents CI as
  passing.
- D-092: PROPOSED everywhere. The A-2 rewording removes the last presumptive phrasing.
- Sponsor: no sponsor approval is claimed. D-094 authority stays owner-authorised, local
  development only. The DECISION_LOG record is append-only ("records events only").

## Findings

| ID | Severity | Location | Finding |
| --- | --- | --- | --- |
| F-1 | Closed | `docs/PROJECT_STATE.md:1157-1158` | Corrected; it matches the committed verdicts |
| A-2 | Closed (advisory taken) | `docs/PROJECT_STATE.md:1184` | Neutral wording |
| A-1 | Advisory | `docs/PROJECT_STATE.md:1164-1165`, `docs/decisions/DECISION_LOG.md:1318` | Supported by the code invariant and the run record; only the PR text omits the explicit Q3 notice. No change required |
| A-3 | Advisory (unchanged) | `docs/PROJECT_STATE.md:1176-1177`, `docs/decisions/DECISION_LOG.md:1322` | The owner's CI exception has no GitHub record; it rests on the committed pre-PR report and the owner's merge |
| A-4 | Advisory (unchanged) | `docs/PROJECT_STATE.md:1135`, `docs/decisions/DECISION_LOG.md:1308` | "reviewed head `0f6e081`" follows the existing convention; spelled out in PROJECT_STATE |
| A-5 | Advisory (out of scope, unchanged) | `docs/PROJECT_STATE.md:1096-1099` | The D-093 section is still titled "unmerged candidate"; leave it for a later closeout |

No Critical, High, Medium or Low findings remain open.

## Byte hygiene

| Check | Result |
| --- | --- |
| `git diff --stat` vs `git diff --ignore-cr-at-eol --stat` | Identical: 2 files, 71 insertions, 11 deletions |
| `git diff --check` | Clean (exit 0) |
| PROJECT_STATE prefix | Lines 1-1130 byte-identical to HEAD (the first differing line is 1131) |
| PROJECT_STATE tail EOL | 61 of 61 lines CRLF, 0 LF-only, final newline present. File: HEAD 680 CRLF / 474 LF; worktree 717 CRLF / 474 LF (LF count unchanged). `git ls-files --eol`: `i/mixed w/mixed` |
| DECISION_LOG EOL | `i/lf w/crlf` under `core.autocrlf=true` (system gitconfig). The CRLF-to-LF content hashes to `fa1f188`, which equals the `git diff` index id and `git hash-object`, and contains no CR. The stored blob stays all LF |
| Trailing whitespace / non-ASCII in changed regions / final newline | None / none / present (both files) |

## Checks run (this session, on CONTENT ID `da77c0a7…82de`)

| Check | Result |
| --- | --- |
| `scripts/check_project_state.py --root .` | PROJECT STATE CHECK: PASS (exit 0) |
| `scripts/check_architecture.py --root .` | ARCHITECTURE CHECK: PASS (exit 0) |
| `scripts/check_tooling_config.py --root .` | TOOLING_CONFIG=PASS (exit 0) |
| `scripts/check_policy_authority.py --root .` | POLICY AUTHORITY CHECK: PASS (exit 0) |
| `scripts/check_external_provider_readiness.py --root .` | EXTERNAL PROVIDER READINESS CHECK: PASS (exit 0) |
| `pytest -q -p no:cacheprovider tests/test_dev_context.py tests/test_check_project_state.py tests/test_check_policy_authority.py` | **51 passed** in 27.86s |
| R1-to-R2 delta reconstruction (scratch repository outside the worktree) | As above; R1 diff sha reproduced exactly |
| `gh pr view 123`, `gh api` runs and jobs (read-only) | As in the spot-check table |
| Ledger read-only (`sqlite3` URI `?mode=ro`) | As in the spot-check table; no write |
| Scope (`git status --porcelain -uall --ignored`) | Only the two reviewed files modified, nothing staged, no new artefacts |

The checkers ran with `PYTHONDONTWRITEBYTECODE=1`. Not run: `pre_pr_check.py`, because
this is an intentionally uncommitted handoff (AGENTS.md). No `.env` was read, Mongo was not
touched, and no paid or OpenRouter call was made.

## Readiness

Governance and publication readiness only. This DOCS_ONLY closeout passes independent
review for exactly CONTENT ID `da77c0a7…82de`. Any change to the reviewed content requires
a fresh review. Commit, push and PR still need explicit owner authorisation, and
`pre_pr_check.py` must run on the committed state before a PR. Nothing changed in API/type,
schema, connector, configuration, business rule, mapping, auth/security, architecture,
provider status or runtime behaviour.

## Git status

Branch `docs/d094-postmerge-closeout-20261028`, HEAD `9a0dcd5`. Tracked: two unstaged
modifications (the reviewed files). Untracked: the R1 report and this R2 report. This
reviewer wrote only this report. No fix, staging, commit, push, PR, merge or next phase
occurred.
