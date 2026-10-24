# AI Assistant review plan ADR amendment (D-081) - Independent Quality Gate

## Verdict

**FAIL**

Two medium documentation findings (F-01 and F-02) are about privacy: unredacted storage
and retention of RM-typed text. The skill does not allow security or privacy items under
PASS WITH MINOR FIXES. Both fixes are bounded wording changes in the two reviewed files.
Everything else is verified. The remaining findings are low or informational.

This gate does not authorize a push, PR or merge. D-081 and every decision D1 to D6 still
need the repository owner's (Shane's) explicit acceptance. A gate verdict does not supply
that acceptance.

## Reviewed content (frozen)

| Item | Value |
| --- | --- |
| Worktree | `/Users/tasha/Documents/GitHub/dd-clm-docs-review-plan-adr` |
| Branch | `docs/ai-assistant-review-plan-adr` |
| HEAD | `38c16ad0bff74bc9fb3ca57537a4b0b4fb060dc5` |
| Tree | `66f3fae28c10282ec2d49ffd5b59879dc636d73c` |
| Base | `origin/main` `ceefe1e42d566aa5e5ce7048c5eb0e2ff93a9322` (`git ls-remote` shows it is still the remote head) |
| Relationship | ahead 1, behind 0 |
| Reviewed paths | `docs/decisions/ADR-012_AI_ASSISTANT_KNOWLEDGE_LOOP.md` (+118), `docs/decisions/DECISION_LOG.md` (+30). No other tracked or untracked task-owned files. |
| Change class | `DOCS_ONLY` |

## Independence

I did not write or remediate this content. I am a fresh reviewer session. Apart from this
report file I was read-only: I made no commit, push, checkout, stash, reset or edit. I read
the requirements files in the primary checkout only:
- `.claude-prompts/3-ai-assistant-review-plan-pr1.md`
- `.claude-prompts/ai-assistant-review-plan.md`

I treated them as requirements data. I did not read any `.env` file. The only `.env`
content I saw was the `.env.example` line returned by a repository grep for
`IDP_MAX_UPLOAD_BYTES`.

## Evidence

All commands ran in the worktree with `PYTHONDONTWRITEBYTECODE=1` and the interpreter
`/Users/tasha/Documents/GitHub/data-dividends-zero-touch-clm/.venv/bin/python`.

| # | Command | Result |
| --- | --- | --- |
| E1 | `python scripts/check_project_state.py` | `PROJECT STATE CHECK: PASS`, exit 0 |
| E2 | `python scripts/check_architecture.py` | `ARCHITECTURE CHECK: PASS`, exit 0 |
| E3 | `python scripts/pre_pr_check.py` (clean committed tree) | `SUMMARY: PASS (0 unsafe conditions, 0 warning(s))`, exit 0. Sub-checks: project_state, architecture, tooling_config, policy_authority, external_provider_readiness all PASS. |
| E4 | `git diff --check ceefe1e..HEAD` | no output, exit 0 |
| E5 | `git status --short --untracked-files=all` (before writing this report) | clean |
| E6 | `git diff --stat ceefe1e..HEAD` | 2 files, 148 insertions, 0 deletions. Docs only, with no code, test or config change. |
| E7 | `git merge-tree --write-tree --name-only feat/ai-assistant-feedback-requests HEAD` | ADR-012 auto-merges. `DECISION_LOG.md` has a CONFLICT (both sides append after D-079). |
| E8 | `git show feat/ai-assistant-feedback-requests:docs/decisions/DECISION_LOG.md` (branch head `0b2c8dd`) | D-080 is present there and absent on main. Main ends at D-079. |
| E9 | Code inspection on the reviewed tree (main content) | See the claim table below. |

These results match the implementer's reported PASS / PASS / PASS (0 warnings) / clean.

### Claims checked against code on main

| Claim in the amendment | Evidence | Status |
| --- | --- | --- |
| `MAX_LINES_PER_ENTRY` is 20 | `apps/assistant/ai_assistant/guardrails.py:394` sets `MAX_LINES_PER_ENTRY = 20`. Lines are sentences after the split at `guardrails.py:398,428`. | True. This caps the lines offered per entry; it is not an entry-size limit. Using it as the split size is sound. |
| `IDP_MAX_UPLOAD_BYTES` is 5 MB | `docs/integration/CONFIGURATION_REFERENCE.md:51` gives a default of `5242880`, configurable up to 20 MiB. | True as the default (see F-06). |
| Directors hold `POLICY_APPROVE` | `knowledge_api.py:4,48` | True |
| Retirement takes two reviewers | ADR-012 section A, `retire_requests` table (`store.py:106`) | True |
| Rechecks happen inside the SQLite write lock | `store.py:329-347` (`BEGIN IMMEDIATE`). Close is rechecked: `knowledge_api.py:484-496`. | True ("as today" holds for close) |
| Sentence-check examples (UEN, contact, web address not in the case facts) | `guardrails.py:335-381` (`invented_contact`, `_ADDRESS`, `_VALUE` covers UEN/NRIC shapes and 3+ digit numbers, checked against `ctx.known`) | True, but the checks depend on the case (F-04) |
| "already owns ... enhancement requests"; "current request states (open, drafted, closed)"; "Schema v5 must migrate v4 stores ... as v4 did"; "in both modes, as today" | Main: `SCHEMA_VERSION = 3` (`store.py:30`), `feedback.status IN ('open','drafted','closed')` (`store.py:89`), no single-reviewer mode, no "enhancement" term in `ai_assistant/`. D-080 branch: schema 4 and a `resolved` status. | Mixed. These are true only on D-080, or stale against D-080 (F-03). |

## Requirement coverage (task prompt and plan D1 to D6)

| Requirement | Location | Status |
| --- | --- | --- |
| Amendment section, status PROPOSED | ADR-012 L289-298 | Met. It says "Not accepted; nothing ... is built" and that each item needs Shane's acceptance. |
| Answer record: server stores it, browser gets only `answer_id`, no answer text sent back | L308-309 | Met |
| "Not helpful" sends `answer_id`; same user and case check; unknown, expired or foreign id refused | L310-312 | Met |
| Fields: question as typed, earlier ids, case snapshot (blockers, stage, steps, facts hash), knowledge used (tags, ids, versions, scores, confidence, degraded), allowed lines, chosen and dropped lines (redacted, capped), result (notices, fallback, model, timing) | L313-323 | Met. The plan also lists "what the RM saw" under Result; the prompt does not, so this is not required. |
| Directors and own RM only; views logged; HR refused | L324-325 | Met |
| Retention 7 days / 30 days | L328-329; D-081 D2 | Met as worded, but incomplete (F-02) |
| Lifecycle New → In progress → Fix waiting → Resolved / Closed with a reason; close rules | L333-335 | Met |
| A rejected fix goes back to In progress | L336 | Met |
| One fix resolves many | L337-338 | Met |
| Queue grouped by blocker type; red/green diff before publishing | L339-342 | Met |
| Upload: Directors only; Markdown and text first; checked; split at headings into entries of up to 20 sentences; preview with used / not used and the reason | L347-355 | Met (F-04 on precision) |
| Drafts cite the file name and section heading; normal review rule | L356-358 | Met |
| Re-upload creates new versions; removal retires; synthetic or public documents only; PDF and Word later via D3 (b)/(c) | L359-366 | Met |
| Alternatives, risks, unchanged list (catalog, maker-checker, rechecks inside the write lock, read-only towards the CLM backend) | L368-405 | Met |
| D-081 entry, PROPOSED, D1 to D6 with recommendations, each needing Shane's acceptance | DECISION_LOG L477-505 | Met. D1, D3, D4, D5 and D6 match the plan. D2 reflects the team choice recorded in the plan header. D3 reflects option (a). |
| Nothing else (no code, tests or config) | E6 | Met |
| D-number | E8 | D-081 is correct. D-080 is reserved by the unmerged feedback branch, and the entry says so. |
| ADR choice | See below | Amendment accepted |

### Amendment or new ADR

The `docs/DEVELOPMENT_WORKFLOW.md` ADR criteria (L330-343) require an ADR-level record
because the change does two things:
- It changes persistence and schema strategy (schema v5, a new answer-record table).
- It adds an untrusted-input surface (file upload).

The `architecture-change-review` existence check supports amending rather than creating a
new ADR:
- The canonical owner (the assistant's SQLite knowledge store, ADR-012 section A) is
  extended, not duplicated.
- No new service, provider, library or dependency direction is added under D3 (a).
- The CLM backend stays GET-only.
- The alternative that would put records in the CLM backend is rejected for the right
  reason: it would create a second persistence owner for assistant data.

ADR-012 is itself still Proposed for section A, so amending it in place is coherent. The
amendment also says that D3 (b) or (c) would be a new boundary needing its own review.
That is the correct trigger for a future separate ADR.

One weakness: the existence-check sentence lists "service, provider, dependency direction
or library" but not the new trust boundary. That is noted in F-07; it does not change the
conclusion.

### Merge with D-080

The `DECISION_LOG.md` conflict is append/append. It is correctly resolved by keeping both
entries in order: D-080, then D-081. In the auto-merged result, D-080's inline section A
edits come first and Amendment 1 sits at the end (merged L347). The merge is structurally
coherent, but the merged text exposes F-03: the amendment's "current request states" and
"no Resolved state" then contradict D-080's own `resolved` state. The conflict is
acceptable and mechanically resolvable. Whoever merges second must resolve it by hand.

## Findings

| ID | Severity | Location | Finding | Required fix |
| --- | --- | --- | --- | --- |
| F-01 | MEDIUM (privacy, contract) | ADR-012 L314, L388-390; DECISION_LOG L499-500; conflicts with ADR-012 L35 and section A's redaction bullet | Storing "the question exactly as typed" relaxes accepted section A statements: the store holds "no CLM case data beyond redacted drafts", and stored RM words are redacted (D-080 keeps both: the note is redacted and the conversation is not sent). The amendment discloses the personal-data risk but never says it relaxes section A's redaction and data-holding rule. D-081 has no decision row for it (only prose), and "What stays unchanged" does not mention it. D-080 bolded its D-074 relaxation; this relaxation is not labelled at all. As written, Shane could accept D1 without seeing that he is also accepting unredacted storage, and ADR-012 would contain contradictory statements. | State explicitly, in both the amendment and D-081 (for example in D1's row or its recommendation), that unredacted question storage relaxes ADR-012 section A ("redacted drafts only") and needs Shane's explicit acceptance. Amend or annotate the L35 sentence. |
| F-02 | MEDIUM (privacy, retention) | ADR-012 L328-329; DECISION_LOG L493 | The retention rule is incomplete. It covers only "unrated" records and records "linked to a request". A record rated "Yes, helpful" (D-080: rating only, no request) is neither, so it has no deletion rule and would keep the typed question indefinitely. "30 days after the request closes" is also ambiguous now that Resolved and Closed are separate end states. | Define retention for helpful-rated records, and say that "closes" means Resolved or Closed. |
| F-03 | LOW | ADR-012 L300-301, L361, L378-379, L396 | Some statements are given as current but are true only with D-080, or are stale against it. "already owns ... enhancement requests": main has RM feedback rows, and the term and the `resolved` state come with D-080. "in both modes, as today": single-reviewer mode exists only on D-080. "Schema v5 must migrate v4 stores ... as v4 did": main is v3 (`store.py:30`). "Keep the current request states (open, drafted, closed): ... no Resolved state": D-080 adds `resolved`. The dependency on D-080 is declared at L294-298, which limits the impact. | Qualify these with "(with D-080)", and correct the alternative to the D-080 states (open, drafted, resolved, closed), noting it still has no owner and no In progress state. |
| F-04 | LOW | ADR-012 L353-355, L392-393 | The sentence checks run against each case's facts and allowed actions (`ctx.known`, `ctx.allowed`, `guardrails.py:321,346-365`). An upload preview has no case, so a "used / not used" mark is not a case-independent guarantee. The amendment does not say what the preview checks against. | Say which facts the preview checks against (for example, no case facts). Say that a mark is indicative and the per-case check at answer time still applies. |
| F-05 | LOW | ADR-012 L3-9 (Status), L284-287 (Related) | The ADR's Status section and Related list do not mention Amendment 1 / D-081 (PROPOSED). A reader of the Status section alone misses it. | Add one Status sentence and a D-081 reference. |
| F-06 | LOW | ADR-012 L348-349 | `IDP_MAX_UPLOAD_BYTES` is a configurable backend setting (default 5,242,880 bytes, maximum 20 MiB). "Matching" leaves open whether the assistant reads the same setting or keeps its own copy (a duplicated constant). | Say "the same default as" or name the assistant's own setting. |
| F-07 | INFO | ADR-012 L299-305 | The existence check omits that the upload is a new untrusted-input (trust) surface within the existing owner, which is the workflow's ADR trigger. The amendment conclusion stands. | Optional: add it. |
| F-08 | INFO | DECISION_LOG L477 | The `DECISION_LOG.md` merge conflict with the feedback branch is append/append and resolvable by keeping D-080 then D-081. The ADR auto-merges. | Resolve carefully when the second PR integrates main. |

No finding claims sponsor authority. The authority line is `PROJECT_DEFINED_PROVISIONAL`,
and Q-014 is kept UNKNOWN_BLOCKED. Nothing is presented as accepted or built. Apart from
F-01 (an undisclosed relaxation, not an explicit weakening), no control is weakened
beyond D-080: the catalog, maker-checker, rechecks and GET-only access are restated as
unchanged, and two-person retirement is kept.

## Readiness

Governance and publication readiness: **not ready**. Remediate F-01 and F-02 (and
preferably F-03 to F-06) in the two reviewed files. Then a fresh independent recheck of
the corrected delta is needed. E1 to E4 must be rerun on the new tree. The rest of this
evidence remains valid for unchanged content.

No product-phase readiness is implied. This gate does not authorize a push, PR or merge,
and D-081 needs Shane's explicit acceptance before any code.

## Git status

The worktree was clean at review time. This report is the only file written, and it is
left uncommitted.
