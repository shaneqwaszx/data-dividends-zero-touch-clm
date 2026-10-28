# AI Assistant D-094 post-merge docs closeout - Independent Quality Gate

Date: 2026-10-28. Reviewer: a fresh, independent QG. This reviewer did not author or
remediate the reviewed content. Change class: DOCS_ONLY (governance closeout). Scope: record
that PR #123 merged as `9a0dcd5` and record the owner-approved paid smoke-test result.

## Verdict

**PASS WITH MINOR FIXES**

Every merge, CI, ledger and smoke-test fact checks out against primary evidence. Byte
hygiene, scope and authority labels are clean, and all checks pass. One durable factual
error must be corrected (F-1, Low): PROJECT_STATE says Quality Gates R1 to R4 all failed,
but R3's committed verdict is PASS WITH MINOR FIXES. The rest are advisories.

Required minor fix:
- F-1: `docs/PROJECT_STATE.md:1157` - replace "R1 to R4 failed and were remediated" with
  wording that matches the committed reports. For example: "R1, R2 and R4 failed and R3
  passed with minor fixes; each was remediated; R5 passed."

The fix changes reviewed content, so the corrected delta needs a fresh independent recheck.
That recheck can reuse every other piece of evidence below.

## Frozen content identity

- Worktree `C:\Users\shane\Desktop\claude-worktrees\assistant-d094-closeout-20261028`, branch
  `docs/d094-postmerge-closeout-20261028`.
- HEAD = `origin/main` = `9a0dcd5f1af78214e987e38aab3b62f92a0cf168`. Uncommitted, nothing
  staged.
- Reviewed paths: `docs/PROJECT_STATE.md` and `docs/decisions/DECISION_LOG.md` (both ` M`).
  No other modified or untracked file, and no ignored files appeared.
- Tracked diff sha256: `4434e7f9f8f9d9b2f1f8e858b44805e61c5c19080af293f62daea811f959f0de`.
- **CONTENT ID at START: `71929971596407107f852c9bee3fb4fb80b402ecd8ad2dfae0c47141eda5ea59`**
  (matches the expected value).
- **CONTENT ID at END: `71929971596407107f852c9bee3fb4fb80b402ecd8ad2dfae0c47141eda5ea59`**
  (unchanged; this report is the only new file).

## Fact verification

| Claim | Result | Primary evidence |
| --- | --- | --- |
| Merged as `9a0dcd5…577` by `shaneqwaszx` on 2026-10-28 | Verified | `gh pr view 123`: state `MERGED`, mergeCommit `9a0dcd5f…`, mergedBy `shaneqwaszx`, mergedAt `2026-10-28T01:14:16Z` (09:14 +08:00) |
| Squash merge with a single parent, `c36b8af` | Verified | `git rev-list --parents -n1 9a0dcd5` shows one parent `c36b8aff…`. The PR's two commits (`71e4654`, `0f6e081`) collapse into one commit |
| Tree `57f59a2` equals head `0f6e081`; product commit `71e4654` plus a report-only commit | Verified | `9a0dcd5^{tree}` = `0f6e081^{tree}` = `57f59a2a…`. `git diff --stat 71e4654 0f6e081` changes only the six D-094 QG and pre-PR reports. `headRefOid` = `0f6e081` |
| `verified_main_sha` unchanged (`8fb5a43`) | Verified | `PROJECT_STATE.md:113` unchanged; the diff touches only lines 1131 onward |
| Hosted CI: push run 40609162932 and `pull_request` run 40609235296, 9 jobs, 0 steps, billing-blocked | Verified | `gh api …/runs/<id>`: both on head `0f6e081`, `completed`/`failure`. `…/jobs`: total_count 9, 0 steps in total, all `failure`. A check-run annotation reads "The job was not started because recent account payments have failed…" |
| Owner accepted a temporary CI exception | Supported, not independently observable | The committed pre-PR report says "The owner holds the manual-CI exception". The PR body records the exception request, and the owner then merged. There are no PR comments or reviews on GitHub. See A-3 |
| 2,442 tests, 14 failed, all Errno 24, the same 14 IDs fail on main `c36b8af`, they pass in isolation | Verified | QG R5 (`…QUALITY_GATE_R5.md:91`): 2,442 tests, 14 Errno 24, 4 files pass in isolation (288). Pre-PR "Errno 24 baseline": main 2,375 tests, 14 failed, ID sets **identical** |
| Frontend 1,123 tests passed | Verified (as reused evidence) | Pre-PR line 83: 65 files, 1,123 tests, tsc clean (implementer, reused by R4/R5) |
| QG "R1 to R4 failed … R5 passed" | **Inaccurate (F-1)** | Committed verdicts: R1 **FAIL**, R2 **FAIL**, R3 **PASS WITH MINOR FIXES**, R4 **FAIL**, R5 **PASS** |
| Pre-PR check passed | Verified | Pre-PR line 85: `pre_pr_check.py` on clean `71e4654`, **PASS** |
| Real-stack browser E2E with a mocked OpenRouter | Verified (PR record) | PR #123 body, Evidence table |
| Smoke test: owner-approved, head `0f6e081`, memory backend with ACRA MOCK, Vite, `openai/gpt-oss-120b` on `deepinfra/bf16` | Verified (PR record) | PR body "Paid smoke test: RUN 2026-10-28, PASS (owner-approved exactly as proposed below)" |
| T7 approval contents: endpoint only `deepinfra/bf16`, `P01#1,P02#0` (2) plus four listed questions, at most 6 calls, cap committed + US$0.10 | Verified (PR record) | PR body "The approved proposal" |
| Connection test passed; qualification passed G-1 to G-8 with G-8 2/2; activation; four answers from GPT-OSS; directors question declined with the quoted text; negative control `SYNTHETIC_TEXT_NOT_APPROVED`, nothing sent; rollback to `ministral-3:8b` | Verified (PR record) | PR body results table. Q3 is not explicitly recorded as carrying the D-094 notice (A-1) |
| 6 calls, rows 29 to 34, all settled and verified, `deepinfra/bf16`, US$0.001076 | Verified | Ledger opened read-only (`?mode=ro`): rows 29 to 34 are `settled`/`verified`/`deepinfra/bf16`, anomaly 0, no error. Charged 182+225+191+109+149+220 = **1076** micro-USD. Max id 34, so there are no later rows. Created between 08:58:00 and 09:00:29 +08:00, before the 09:14 merge |
| Committed spend US$0.006960; cap lowered to US$0.105884 | Verified | `ledger_meta`: baseline 309 + local charged 6651 = **6960**, open reserved 0, breaker closed, `cap_micro_usd` **105884**. `operator_events` #5 is `cap_lowered` 105884 at 08:48:54 +08:00, before row 29. 105884 = 5884 (committed before the run) + 100000 |
| Open item: six QG advisories R5-A1, R4-A1, R4-A2, R4-A3, R3-A1, R2-5 | Verified | PR body "Outstanding findings" |

`apps/assistant/scripts/budget_ledger.py status` was not run. Its side effects were not
inspected, so the direct read-only SQLite query was used instead.

## Overclaim and authority review

- Live: the smoke test is called "synthetic external evaluation on the owner's machine,
  never Live CLM behaviour" (`PROJECT_STATE.md:1173`). This matches D-094's last paragraph,
  and no provider classification changes.
- Hosted CI is called `HOSTED_CI_NOT_EXECUTED - BILLING/INFRASTRUCTURE BLOCKED`
  (PROJECT_STATE), and "not executed … that is not a pass" (DECISION_LOG). Neither presents
  it as passing.
- D-092 is "still PROPOSED" (`PROJECT_STATE.md:1139`) and "stays PROPOSED"
  (`DECISION_LOG.md:1325`).
- Nothing presents the smoke test as sponsor approval. The D-094 authority stays
  "owner-authorised, local development scope only", consistent with
  `USER_AUTHORIZED_POC / PROJECT_DEFINED_PROVISIONAL`.
- The DECISION_LOG change is append-only: one hunk at `@@ -1300,3 +1300,26 @@` with no
  removed lines. The D-091, D-092, D-093 and D-094 decision text is byte-unchanged, and the
  record says "This records events only; the decision text above is unchanged."
- The Known-limit restatement in PROJECT_STATE is consistent with the D-094 "Known limits"
  text. Its "number groups spread over several requests" item is a faithful addition taken
  from D-094.

## Findings

| ID | Severity | Location | Finding and evidence |
| --- | --- | --- | --- |
| F-1 | Low (required minor fix) | `docs/PROJECT_STATE.md:1157` | "Independent Quality Gates R1 to R4 failed and were remediated" misstates R3. `.ai-pipeline/reports/AI_ASSISTANT_D094_IN_APP_OPENROUTER_QUALITY_GATE_R3.md:12` is **PASS WITH MINOR FIXES**, and R4 (`…_R4.md:5`) cites it as such. The error understates rather than overclaims, but it is a durable factual record. (The PR #123 body has the same error; the committed reports are the authority.) |
| A-1 | Advisory | `docs/PROJECT_STATE.md:1164`, `docs/decisions/DECISION_LOG.md:1318` | "All four … with the D-094 notice" / "with the T5 notice". The PR record states the notice explicitly for Q1, Q2 and Q4. For Q3 it records only "GPT-OSS: … plus the Mock/Live disclaimer". This is probably right, but the source does not spell it out for Q3. |
| A-2 | Advisory | `docs/PROJECT_STATE.md:1184` | The open item "Accept D-092." reads as if acceptance were the planned outcome. Neutral wording, such as "owner decision on D-092 (PROPOSED)", would avoid presuming the decision. D-092 is correctly labelled PROPOSED elsewhere. |
| A-3 | Advisory | `docs/PROJECT_STATE.md:1176-1177`, `docs/decisions/DECISION_LOG.md:1322` | The owner's acceptance of the CI exception has no GitHub record (no PR comments or reviews). It rests on the committed pre-PR report and the owner's merge. This is acceptable for a closeout, noted for traceability. |
| A-4 | Advisory | `docs/PROJECT_STATE.md:1135`, `DECISION_LOG.md:1308` | "reviewed head `0f6e081`" / "independently reviewed head": the independent R5 review covered content `15dce753…`, committed as `71e4654`, and `0f6e081` adds only reports. PROJECT_STATE spells this out, and the wording follows the existing convention at `PROJECT_STATE.md:1062`. No change required. |
| A-5 | Advisory (out of scope) | `docs/PROJECT_STATE.md:1096-1099` | The D-093 section is still titled "unmerged candidate" and says "Not merged to main", although PR #121 merged as `c36b8af`. This closeout was correctly limited to D-094; a later closeout may refresh it. |

No Critical, High or Medium findings.

## Byte hygiene

| Check | Result |
| --- | --- |
| `git diff --stat` vs `git diff --ignore-cr-at-eol --stat` | Identical (2 files, 71 insertions, 11 deletions) |
| `git diff --check` | Clean (exit 0) |
| PROJECT_STATE outside the rewritten tail | Lines 1 to 1130 and the final terminator are byte-identical to HEAD. The diff region is new lines 1131 to 1191 |
| PROJECT_STATE rewritten tail EOL | 61 of 61 CRLF, 0 LF (the replaced region was 24 of 24 CRLF). File total: HEAD 680 CRLF / 474 LF; worktree 717 CRLF / 474 LF, so the LF count is unchanged |
| PROJECT_STATE blob on add | `git ls-files --eol`: `i/mixed w/mixed`. The index already holds CRLF, so `autocrlf=true` will not normalise it. `git diff` index id `e6f6545` = raw `hash-object --no-filters` |
| DECISION_LOG EOL | HEAD blob is all LF (`i/lf`); the worktree is CRLF via `core.autocrlf=true`. The clean-filtered blob `fa1f188` equals the CRLF-to-LF hash, so the stored blob stays all LF, consistent with the existing EOL |
| Trailing whitespace, final newline, non-ASCII in the changed regions | None, present, none |

## Checks run (this session, on CONTENT ID `71929971…ea59`)

| Check | Result |
| --- | --- |
| `scripts/check_project_state.py --root .` | PROJECT STATE CHECK: PASS (exit 0) |
| `scripts/check_architecture.py --root .` | ARCHITECTURE CHECK: PASS (exit 0) |
| `scripts/check_tooling_config.py --root .` | TOOLING_CONFIG=PASS (exit 0) |
| `scripts/check_policy_authority.py --root .` | POLICY AUTHORITY CHECK: PASS (exit 0) |
| `scripts/check_external_provider_readiness.py --root .` | EXTERNAL PROVIDER READINESS CHECK: PASS (exit 0) |
| `pytest -q -p no:cacheprovider tests/test_dev_context.py tests/test_check_project_state.py tests/test_check_policy_authority.py` | **51 passed** in 28.86s |
| `gh pr view 123`, `gh api` runs, jobs and annotations (read-only) | As in the fact table |
| Ledger read-only (`sqlite3` URI `?mode=ro`) | As in the fact table; no write was made |
| Scope (`git status --porcelain -uall`, `--ignored`, `--cached`) | Only the two reviewed files modified, nothing staged, and no ignored or cache artefacts created |

Not run: `pre_pr_check.py`, because this is an intentionally uncommitted handoff (AGENTS.md).
`budget_ledger.py status` was also not run, for the reason given above. No `.env` was read,
Mongo was not touched, and no paid or OpenRouter call was made.

## Readiness

Governance and publication readiness only. This DOCS_ONLY closeout is not ready to publish
until F-1 is corrected and a fresh independent recheck of the corrected delta passes. After
that, commit, push and PR still need explicit owner authorisation. No product, API, schema,
connector, configuration, business-rule, mapping, auth/security, architecture,
provider-status or runtime change is involved.
