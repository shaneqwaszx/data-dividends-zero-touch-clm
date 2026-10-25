# AI Assistant review plan ADR amendment (D-081) - Independent Quality Gate, recheck R1

## Verdict

**PASS**

Every finding from the first gate (FAIL on `38c16ad`) is resolved or has a justified
disposition. The remediation adds no new contradiction or overclaim. All original
requirements are still covered. The required checks pass on the reviewed tree. Two new
INFO notes (N-01, N-02) are about wording to update later. They need no fix before the PR.

This gate does not authorize a push, PR or merge. D-081 and every decision D1 to D6,
including the D2 retention, still need the repository owner's (Shane's) explicit
acceptance before code. A gate verdict does not supply that acceptance.

## Reviewed content (frozen)

| Item | Value |
| --- | --- |
| Worktree | `/Users/tasha/Documents/GitHub/dd-clm-docs-review-plan-adr` |
| Branch | `docs/ai-assistant-review-plan-adr` |
| HEAD | `a86c7d0c14a782d7b0a27beb3c925a433501b435` |
| Tree | `bc6d2ae1a8481a637b3837ee8a39cf1a80e0044f` |
| Base | `origin/main` `ceefe1e42d566aa5e5ce7048c5eb0e2ff93a9322` (`git ls-remote` confirms it is still the remote head) |
| Relationship | ahead 3 (`38c16ad`, `3618500`, `a86c7d0`), behind 0 |
| Reviewed paths | `docs/decisions/ADR-012_AI_ASSISTANT_KNOWLEDGE_LOOP.md`, `docs/decisions/DECISION_LOG.md`, and the committed first gate report `.ai-pipeline/reports/AI_ASSISTANT_REVIEW_PLAN_ADR_QUALITY_GATE.md`. No other tracked or untracked files. |
| Remediation delta | `git diff 38c16ad a86c7d0`: the two docs files only |
| Change class | `DOCS_ONLY` |

## Independence

I am a fresh reviewer session. I did not write or remediate this content, and I did not
write the first gate report.

Apart from this report file I was read-only. I made no commit, push, checkout, stash, reset
or edit.

In the primary checkout I read only these files, and I treated them as requirements data:
- `.claude-prompts/3-ai-assistant-review-plan-pr1.md`
- `.claude-prompts/ai-assistant-review-plan.md` (its header and the section
  "Architecture and decisions needed from Shane")

I also read the branch `feat/ai-assistant-feedback-requests` (`0b2c8dd`) read-only, through
`git show` and `git merge-tree`. I did not read any `.env` file.

While I was reviewing, the coordinator relayed a team confirmation on D2. That relay is
recorded under F-02. It changes no reviewed content.

## Disposition of first-gate findings

| ID | Severity | Disposition | Assessment |
| --- | --- | --- | --- |
| F-01 | MEDIUM | Resolved | The relaxation is now stated in three places. Answer records (ADR-012 L332-336) has it as a bold bullet: the question is kept unredacted with a case-state snapshot, which relaxes section A's "no CLM case data beyond redacted drafts" and D-080's redaction of RM text. Risks (L406-408) refers back to it. D-081's D1 row and paragraph (DECISION_LOG L492, L499-500) also state it. Shane can no longer accept D1 without seeing the relaxation. I checked whether the snapshot or the stored "allowed lines" carry further case data that is not disclosed. `allowed_guidance` (`guardrails.py:65-104`) builds lines from fixed templates, rule texts, action labels and section names, not document or registry values, so the disclosure is complete. Leaving L35 and the Status block unedited is acceptable. The amendment is PROPOSED, and an unaccepted amendment that names the accepted text it would change is the normal pattern. ADR-012 does not contradict itself while D-081 is pending. The Related note (L288-289) says the Status is updated on acceptance. See N-01 for the section A line. |
| F-02 | MEDIUM | Resolved | Every record not linked to a request (unrated or rated "Yes, helpful") is deleted after 7 days. A linked record is deleted 30 days after its request ends as Resolved or Closed (ADR-012 L337-340; D-081 D2). There is no longer a retention gap, and "ends" names both end states. "The helpful count in the stats is kept without the record" is consistent with D-080: the helpful rating is a separate `feedback` row, and the answer record is a new table. The coordinator relayed, during this gate, that the team (Tasha) confirmed 7-day deletion for helpful-rated records with only the count kept. The reviewed text already says this, so the content is unchanged. D2 as a whole still needs Shane's acceptance. |
| F-03 | LOW | Resolved | The text now attributes enhancement requests to D-080 (L302-303). The schema is correct: main `SCHEMA_VERSION = 3` (`apps/assistant/ai_assistant/knowledge/store.py:30`); the feedback branch `SCHEMA_VERSION = 4` with `status IN ('open','drafted','resolved','closed')` (`store.py:37,97` on `0b2c8dd`). The alternative now lists D-080's four states correctly (L395-397). The migration risk names v3 and v4 (L415-416). |
| F-04 | LOW | Resolved | The preview's case-independent checks are listed as characters, citation tags, authority phrasings and live claims (L367-368). These match exactly the checks in `_check` that do not read `ctx` (`guardrails.py`): `unsupported_character`, `invented_source`, `authority_claim`, `live_claim`. The case-dependent examples (UEN or long number, contact, web address) match `_VALUE`, `_CONTACTS` and `_ADDRESS` against `ctx.known`. The other case-dependent checks (quoted labels, sections, step counts, actions, document values) also derive from the case facts, and the text says "for example". The marks are called indicative, and the full per-case check at answer time is stated (L370-371). |
| F-05 | LOW | Justified | This is handled with F-01. The Related section now references Amendment 1 / D-081 (PROPOSED) and says the Status section is updated on acceptance. A reader of the ADR still finds the amendment through Related and the section heading. Editing the Status hunk would conflict with D-080, which edits the same lines. |
| F-06 | LOW | Resolved | The size limit is the assistant's own setting with the same 5 MB default, and the assistant does not read the backend's configuration (L359-362). The default matches `CONFIGURATION_REFERENCE.md:51` (5242880). |
| F-07 | INFO | Resolved | The existence check now names upload as a new untrusted-input surface inside the existing owner (L306-307). |
| F-08 | INFO | Accepted (no change) | Re-observed (E6). The conflict is still append/append in `DECISION_LOG.md` only. It resolves by keeping D-080, then D-081. |

Two further statements were checked against code:
- "Retirement takes two reviewers (D-074), also in D-080's single-reviewer mode" is true on
  the feedback branch: `request_retirement` / `SecondReviewerError` ("a different reviewer
  must confirm the retirement"), and D-080 L35 of its entry.
- The D1 "Options" column ("Director-only access") is copied verbatim from the plan. The
  recommendation states the precise rule (Directors and the RM who asked).

## Requirement coverage

The first gate's coverage table remains valid. The remediation only adds wording, and no
required item was removed or weakened. I rechecked every bullet of the task prompt against
the current text:
- Answer records: the record fields, the `answer_id` flow, the same user and same case check,
  Director and own-RM access, logged views, and retention.
- Lifecycle: the states, rejected fix back to In progress, one fix resolving many, the queue
  grouped by blocker type, and the red/green diff.
- Upload: Directors only, Markdown and text first, checked, split at headings into entries
  of at most 20 sentences, a preview with the reason, drafts that cite the file and heading,
  the normal review rule, re-upload and removal, synthetic or public documents only, and PDF
  and Word later via D3 (b)/(c).
- Alternatives, risks and the unchanged list.
- D-081 is PROPOSED with D1 to D6, and each needs Shane's acceptance.
- No code, tests or config changed (E5).

The D2 wording extends the plan's "7 days unrated" to helpful-rated records. The team has
confirmed this (F-02), and it is still subject to Shane's acceptance.

## Evidence

All commands ran in the worktree with `PYTHONDONTWRITEBYTECODE=1` and the interpreter
`/Users/tasha/Documents/GitHub/data-dividends-zero-touch-clm/.venv/bin/python`. They ran on
HEAD `a86c7d0` / tree `bc6d2ae`.

| # | Command | Result |
| --- | --- | --- |
| E1 | `python scripts/check_project_state.py` | `PROJECT STATE CHECK: PASS`, exit 0 |
| E2 | `python scripts/check_architecture.py` | `ARCHITECTURE CHECK: PASS`, exit 0 |
| E3 | `python scripts/pre_pr_check.py` (clean committed tree) | `SUMMARY: PASS (0 unsafe conditions, 0 warning(s))`, exit 0. Sub-checks project_state, architecture, tooling_config, policy_authority and external_provider_readiness all PASS. Working-tree inventory: clean. |
| E4 | `git diff --check ceefe1e..HEAD` | no output, exit 0 |
| E5 | `git diff --name-status ceefe1e..HEAD`; `git status --short --untracked-files=all` (before writing this report) | A gate report, M ADR-012, M DECISION_LOG. The tree was clean. |
| E6 | `git merge-tree --write-tree --name-only HEAD feat/ai-assistant-feedback-requests` | Tree `7184c3e`, exit 1. ADR-012 auto-merges; `DECISION_LOG.md` CONFLICT (content). This matches the implementer's report. |
| E7 | Merged ADR-012 inspected (`git show 7184c3e:docs/decisions/ADR-012_AI_ASSISTANT_KNOWLEDGE_LOOP.md`) | D-080's Status and section A edits come first, and Amendment 1 sits at the end (L349). Nothing contradicts D-080's states, schema v4 or redaction text. See N-02. |
| E8 | Code inspection: `guardrails.py` `_check`, `allowed_guidance`, `MAX_LINES_PER_ENTRY`; main `knowledge/store.py:30,89`; feedback branch `knowledge/store.py:37,97` and retirement | As cited in the dispositions |

E1 to E4 and E6 match the implementer's reported results.

## New findings

| ID | Severity | Location | Finding | Recommendation |
| --- | --- | --- | --- | --- |
| N-01 | INFO | ADR-012 L288-289, L35 | The Related note says only "the Status section above is updated" on acceptance. Section A's "no CLM case data beyond redacted drafts" (L35) will also need amending if D1 is accepted. The amendment states this itself (L332-334), so nothing is hidden. | When D-081 is accepted, update both the Status block and L35. No change needed now. |
| N-02 | INFO | ADR-012 L307-308, L415-416 | "main is at schema v3" and "v3 on main" are time-relative. If the feedback PR (schema v4) merges first, these become stale in the merged text (E7). | Reword when this branch integrates the merged D-080, for example to "schema v4 (D-080)". This is optional and not blocking. |

No finding is CRITICAL, HIGH, MEDIUM or LOW. No safety control is weakened:
- The exact-line catalog, maker-checker (two-person retirement in all modes), rechecks
  inside the write lock and GET-only CLM access are restated as unchanged.
- The one relaxation (unredacted question storage) is now labelled and left to Shane.
- The authority line is still `PROJECT_DEFINED_PROVISIONAL`, and Q-014 stays UNKNOWN_BLOCKED.

## Readiness

Governance and publication readiness: **ready for the owner's review** as a PROPOSED
decision. This statement is limited to the frozen tree `bc6d2ae`.

No product-phase readiness is implied. The gate does not authorize a push, PR or merge. The
user must approve any push. Shane must accept D-081 (D1 to D6) before any code. The PR
should note the `DECISION_LOG.md` append/append resolution (D-080, then D-081).

## Git status

The worktree was clean before this report was written. This report is the only file written,
and it is left uncommitted.
