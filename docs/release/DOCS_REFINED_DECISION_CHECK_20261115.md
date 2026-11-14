# Release pipeline: independent check of the documents-only delta `1cfa9bd..d5193ba`

## 1. Identity, scope and command results

| Field | Value |
|---|---|
| Checker | Fresh session; did not write the delta or the code. Check only; nothing fixed |
| Date | 2026-11-15 |
| Evidence class | **Mock and Local only.** Reading of documents and code, one local test run. No host, AWS, SSH, registry, network, `.env` or `--execute` against anything real |
| Base | `1cfa9bd2ded24081d6ba4f8410023c5381bfcb9b` |
| Checked | `d5193baa19c0f4551b34793686f2390e2a60c58d`, tree `3c05c08825b70b31e51b6c6488413555552abb57` (confirmed with `git rev-parse HEAD HEAD^{tree}`) |
| Worktree | `git status --short` before and after: only `?? outputs/` |
| Enforcement source | `outputs/integration-release-lead-20261114/PIPELINE_FINAL_DELTA_REVIEW.md` (main checkout), Part C |

Scope: `git diff --stat 1cfa9bd d5193ba` lists seven files, all under `docs/release/`
(300 insertions, 57 deletions): the checklist, architecture, how-to, README, runbook, evidence
document, and the new `DOCS_FINAL_CHECK_20261115.md`. `git diff 1cfa9bd d5193ba -- . ':!docs'`
is empty. **No code, test, schema or sample changed.** `git diff --check` is clean.

| Command (run once, at `d5193ba`) | Result |
|---|---|
| `python -m pytest tests/release -q -p no:cacheprovider` (`CLM_RELEASE_STATE_DIR` set to a new empty temp directory outside the repository) | **321 passed, 1 skipped** (22 s) |
| `python scripts/check_secrets.py` | **Secret scan passed** |
| `diff` of `docs/release/DOCS_FINAL_CHECK_20261115.md` against `outputs/release-pipeline-20261114/DOCS_FINAL_CHECK.md`, carriage returns removed | **Identical** |

## 2. Verdict

**PASS WITH NOTES** (P1 0, P2 1, P3 7).

The decision is quoted character for character in all four places instructed. The
`release_id` / `attempt_id` model is stated correctly and "`attempt_id` does not exist in the
tool today" is true. The six requirements carry the owner's wording and the six statuses
exactly as instructed, and every addition beyond Part C is accurate and presented as a gap.
The interim prohibition is unambiguous in the runbook subsection and in checklist step E1b,
with all four required elements. No sentence claims enforcement the code does not have. No
non-document change.

The one P2 is in text the delta did **not** change but that now sits beside the new rule: the
state-keyed `ROLLED_BACK` entries (runbook section 7 and checklist section F) still say only
"a new attempt needs a new approval". `ROLLED_BACK` is also the state an operator reaches
after `accept --result fail` and a rollback, which is exactly the point at which the
procedural rule must be remembered, and the tool will not stop them. I do not rate it a FAIL:
the prohibition itself is present, bold and unambiguous in the same runbook section, in the
checklist, the README and the architecture; the old sentence is true for the case it was
written for (a rollback after a failed deployment). It should be corrected because the rule
is procedural only.

## 3. Results B to H

### B. Instruction 1: the decision verbatim

Compared by program against the exact string (line wrapping and `>` removed):

| Place | Line | Exact |
|---|---|---|
| `PIPELINE_ARCHITECTURE.md` section 3.8 | `:390` (blockquote) | Yes |
| `TEST_EVIDENCE_AND_LIMITATIONS.md` section 4.9 | `:303` | Yes |
| `RELEASE_AUTOMATION_RUNBOOK.md` section 7 subsection | `:293` | Yes |
| `PIPELINE_HOW_TO_USE_AND_MAINTAIN.md` | `:125` | Yes |

No other quotation of the decision exists under `docs/release/` outside the unedited reports
(`README.md` and the checklist paraphrase the rule and do not quote). The earlier wording
survives once, at evidence `:282-284` (section 4.8), explicitly as history ("recorded in that
pass with the wording the owner first gave ... The owner refined the decision the same day").
Nothing presents the earlier wording as current.

### C. Instructions 2 and 3: model, statuses, table

| Check | Result |
|---|---|
| Model stated | Yes: `PIPELINE_ARCHITECTURE.md:392-397`, runbook `:295-296`, how-to `:127-128`. Correct against the owner's words |
| "`attempt_id` does not exist in the tool today" | **True.** No `attempt_id` in `tools/release/`. The word "attempt" appears only as a retry loop counter (`core.py:495-508`, `records.py:92-102`), the rollback block's own counter (`deploy.py:1258`, the number of the rollback within one record, not a deployment identity), `recovery_attempts` (`deploy.py:1720-1728`) and comments. `approval.py` has no attempt field. The known-good pointer holds release id, manifest hash, time, previous (`records.py:128-133`) |
| Six requirements, owner's wording | Yes, in order: architecture `:417-422`; evidence `:305-310` |
| Six statuses | (1) PARTLY, (2) NOT ENFORCED, (3) PARTLY, (4) PARTLY, (5) ENFORCED, (6) ENFORCED in the table and at evidence `:310-311`. Exactly as instructed |

Cells against Part C and the code:

| # | Faithful to Part C | Added beyond Part C | Accurate, and shown as a gap? |
|---|---|---|---|
| 1 | Yes ("Immutable" became "Preserved by convention only") | Nothing | `records.py:79-80`: `len(glob) + 1`, non-exclusive write. True |
| 2 | Yes | "Non-reusable additionally needs the allocation to be checked against every earlier attempt of the release" | In the gap column. Accurate: nothing allocates or checks anything today |
| 3 | Yes ("New" became "Fresh") | "Nothing in an approval names an attempt"; "Specifically authorising the new attempt additionally needs the approval record to name the `attempt_id` (depends on requirement 2)" | In the gap column. True: `approval.py:57-84` checks manifest, release, action, services, risk, window, used; `approved_at` is written (`:155`) and never compared |
| 4 | Yes. The reviewer's "whether a redeploy must re-verify source is an owner question" is dropped, correctly: the refined wording answers it | "(including that the rollback image is cached on the host)" in "what holds"; "Rollback readiness:" label on gap (ii) | The "holds" addition is true (`deploy.py:543`). Gap (ii) true (`deploy.py:538`: a null target is not compared) |
| 5 | Yes | "and a record marked `acceptance_failed`" moved here from row 6 | True (`deploy.py:1850-1854`), and it belongs with this requirement |
| 6 | Yes, less the sentence moved to row 5 | Nothing | True (`deploy.py:667-685`: the new record is built without acceptance state) |

No sentence in the delta claims more enforcement than the code has. One small imprecision,
not an overclaim: `:396-397` says two attempts can be told apart "only by their approval id,
their timestamps and the number of the result file"; row 2 of the table adds the boolean
`previously_failed_acceptance` (finding 6).

### D. Instruction 4: the interim prohibition

| Element | Runbook (`:291-316`) | Checklist E1b (`:59`) |
|---|---|---|
| Must not be deployed again with this tool | `:302-304`, bold | Yes |
| "under the same or any attempt" | `:303-304` | Yes |
| "implemented, tested and independently reviewed" | `:302-303` | Yes |
| The tool does not block it today | `:304` | "The tool does not block this" |
| Procedural | `:304-305` | Yes |
| New release (new `release_id`), full preparation and review, is the only permitted route for now | `:313-314` | Yes |
| Explicitly not the owner's eventual model | `:314-316` | Not said ("for now" only): finding 5 |

Operator instructions, against the code:

| Instruction | Can it be followed, and is it safe? |
|---|---|
| "Do not run `deploy --execute` for a release whose records show a failed acceptance (`acceptance_failed: true` in any numbered result, or state `ACCEPTANCE_FAILED`)" (`:307-308`) | Yes. `accept --result fail` writes `acceptance_failed: true` to a numbered result and the standing record (`deploy.py:1857-1867`, `records.py:77-83`); a later rollback carries it (`deploy.py:1573-1577`) |
| If `previously_failed_acceptance` is true: stop, do not accept, tell the owner, roll back under a new `rollback` approval (`:309-312`; E1a `:58`) | Yes. The flag is set by `_record` (`deploy.py:687-694`). A record awaiting acceptance is in `MANUAL_ROLLBACK_FROM` (`deploy.py:1530-1538`), so `rollback` is available, with a `rollback` approval, subject to eligibility (runbook section 6, which E1a cites). It returns the host to the previous pins; safe. `accept` itself does **not** refuse on this flag (`deploy.py:1850` tests `acceptance_failed` only), so "the tool does not block it" is accurate |
| New release with a new `release_id` and manifest through sections 1 to 5 | Sections 1 to 5 exist (prepare, independent review, publish, deploy, acceptance). Possible |

Left in the documents that could mislead: the `ROLLED_BACK` entries, runbook `:178-180` and
checklist `:70` (finding 1). The architecture 3.7 paragraph (`:309-324`) still describes the
code path ("What can still be accepted afterwards is a new, complete deployment of the same
release") but now ends with the bold prohibition and says the tool does not block it: clear.

### E. Instruction 5: the heading

`PIPELINE_ARCHITECTURE.md:399`: "MANDATORY FOLLOW-UP ENGINEERING BEFORE ANY RETRY AFTER A
FAILED ACCEPTANCE", a level-2 heading in a blockquote, capitals; the box (`:401-407`) states
the prohibition, the three conditions and that the tool does not block. Requirements 1 to 4
follow in the table (`:417-420`) whose last column is headed "Gap, and the smallest change
proposed (mandatory follow-up)", each with the reviewer's smallest change. It cannot be
missed, and the README (`:9-11`), how-to (`:128-133`, `:137-142`) and evidence (`:313-318`)
all point to it. Two notes: the box cites checklist step E1a only (finding 2), and a level-2
heading inside a level-3 section (finding 3).

### F. The eight notes from `DOCS_FINAL_CHECK.md`

| Note | Applied | Resulting sentence true? |
|---|---|---|
| 1 (P2) limitation 4h; checklist row | Yes, checker's wording: architecture `:471-477`; checklist `:73` title | Yes (`deploy.py:1033`, `1349-1350`, `1596-1597`; the earlier probe) |
| 2 runbook condition | Yes, `:215-216` | Yes |
| 3 evidence stale lines | Yes: `:232-233`; table rows for `b97fa59`, `1cfa9bd` and head (`:255-257`) | Yes |
| 4 README "open owner decision" | Yes, own wording, `README.md:26` | Yes |
| 5 "six" against "seven" | Applied differently: both now say "several" (how-to `:10-12`, README `:5`); how-to points to sections 4.7 to 4.9 | Yes, and it no longer needs recounting |
| 6 "four of the six" | Yes, `:296-300` ("does not fully enforce four ... one is not enforced at all and three only partly") | Yes |
| 7 next step when the flag is true | Yes, in both (E1a `:58`; runbook `:309-312`), narrower than suggested: rollback directly, without the `accept --result fail` option | Yes; see D |
| 8 wrapper names | Yes, `:219-220` | Yes (`dc`, `dcg`, `dca` as in runbook `:273-275`) |

### G. Consistency

- References: architecture 3.7 and 3.8, evidence 4.8 and 4.9, checklist E1a and E1b,
  limitation 4h, runbook sections 1 to 5, 6 and 7 all exist and hold what is said of them.
- Nothing calls the decision open. Evidence `:228` "was open at that time (decided on
  2026-11-15, section 4.8)" is historical and correct; 4.8 leads on to 4.9.
- Review counts: "several" in the README and how-to; evidence 4.8 keeps "a seventh
  independent review" for the review of `b97fa59`. No contradiction.
- `@@CHECK8@@` is present once, evidence `:322`, as expected. No `@@CHECK7@@` remains.
- Minor: findings 2, 4, 7.

### H. Changes not covered by the instructions

| Change | Accurate? |
|---|---|
| `README.md:9-11` new paragraph: redeploy after failed acceptance prohibited; tool does not block; procedural (runbook 7; E1a, E1b) | Yes |
| `README.md:5` "seven" became "several"; `:28` new index row for `DOCS_FINAL_CHECK_20261115.md` (PASS WITH NOTES, evidence 4.9) | Yes |
| `PIPELINE_ARCHITECTURE.md:322-324` bold sentence in 3.7 | Yes |
| How-to `:130-133`: "do not build that retry path as a side effect of other work" | Guidance, consistent with the owner's "implemented, tested and independently reviewed" |
| Evidence 4.9 summary of the previous check (tree `6fb5694`, six documents, P1 0 / P2 1 / P3 7; "All thirteen wording rows are applied and true against the code") | Matches the report; "true" is slightly generous for A-1, whose one imprecise sentence that report raised as its finding 2, and the P2 is described in the next paragraph |
| Evidence `:282-284`: 4.8 now refers to the first wording as superseded | Yes |
| Checklist E1b placed as a step in section E | Accurate content; placement note, finding 4 |

## 4. Findings

| # | Sev | Where | What is wrong | Replacement wording |
|---|---|---|---|---|
| 1 | **P2** | `RELEASE_AUTOMATION_RUNBOOK.md:178-180`; `FIRST_AUTOMATED_RELEASE_CHECKLIST.md:70` (both unchanged by the delta) | The `ROLLED_BACK` entries say only "a new attempt needs a new approval". `ROLLED_BACK` is also the state after `accept --result fail` and a rollback. An operator who looks up the state they are in is told a new approval is enough, at the one moment the procedural rule applies, and the tool will not stop them (`deploy.py:687-694` flags, does not refuse). Misleading by omission now that the rule exists | Runbook: "- `ROLLED_BACK`: the tool verified every service healthy on the previous images and public `/health` 200. The approval is used; a new attempt needs a new approval. **If this release failed acceptance, no new attempt is permitted for now: see "Deploying again after a failed acceptance: PROHIBITED for now" below.**" Checklist row: "... Stop; investigate; a new attempt needs a new approval. **If the release failed acceptance, it must not be deployed again (step E1b)**" |
| 2 | P3 | `PIPELINE_ARCHITECTURE.md:406` | The box cites "checklist step E1a"; the interim rule is step E1b (README and evidence cite both) | "rule: runbook section 7 and checklist steps E1a and E1b." |
| 3 | P3 | `PIPELINE_ARCHITECTURE.md:399` | A level-2 heading inside a blockquote inside the level-3 section 3.8; a generated outline shows it as a sibling of "3. Components". Conspicuous, as instructed; structure only | Keep, or use `> #### MANDATORY FOLLOW-UP ENGINEERING ...` |
| 4 | P3 | `FIRST_AUTOMATED_RELEASE_CHECKLIST.md:59` | E1b sits between E1a and E2 (after the deployment) while its pass condition is "Acknowledged ... before the window". A checklist worked top to bottom reaches it after the window opened | Keep E1b, and add to section D before the deploy step: "`[owner]` `[operator]` Read step E1b (interim rule on a release that failed acceptance) / Acknowledged by both" |
| 5 | P3 | `FIRST_AUTOMATED_RELEASE_CHECKLIST.md:59` | E1b says "for now" but not that the new-release route is not the owner's eventual model (the runbook and architecture do) | Append: "This is an interim rule, not the owner's eventual model (a retry of the same `release_id` under a new `attempt_id`)" |
| 6 | P3 | `PIPELINE_ARCHITECTURE.md:396-397` | "told apart only by their approval id, their timestamps and the number of the result file" omits the boolean `previously_failed_acceptance` that row 2 names | "... only by their approval id, their timestamps, the number of the result file and the boolean `previously_failed_acceptance`." |
| 7 | P3 | `TEST_EVIDENCE_AND_LIMITATIONS.md:214`, `:228`, `:264` | "decided on 2026-11-15 (section 4.8)" now reaches the current wording only through 4.8's pointer; the 4.8 heading says "the last documents-only pass", which it no longer is | `:214`, `:228`: "(sections 4.8 and 4.9)". `:264`: "... and the documents-only pass that followed" |
| 8 | P3 | `RELEASE_AUTOMATION_RUNBOOK.md:309-312`; checklist `:58` | "roll the release back" assumes the record is awaiting acceptance. The flag can also sit on a record in another state (for example `FAILED_HELD` from the second deployment), where section 7's rule for that state governs, and `rollback` is always subject to eligibility | After "under a new `rollback` approval" add: "(section 6; subject to the usual eligibility. If the record is not `DEPLOYED_AWAITING_ACCEPTANCE`, follow the entry for its state in this section first)" |

No P1. No unsafe or impossible instruction. No statement that the tool enforces something it
does not.

## 5. Not checked

- Anything on a real host, registry, shell or credential store.
- `tests/deploy`, ruff, mypy and the governance scripts: not run.
- No probe was run. Statements about interrupts during `up` (note 1, limitation 4h) rest on
  the previous check's probe and on my reading of `deploy.py`; rollback availability when
  `previously_failed_acceptance` is true rests on reading `MANUAL_ROLLBACK_FROM` and
  `manual_rollback`, not on an executed sequence.
- Part C's evidence counts and test references: compared as text, not reproduced.
- Whether the tool refuses a different manifest under an existing `release_id` (the model
  sentence "one manifest" was read as a description of the model, not as an enforcement claim).
- The owner's decision text itself: taken from the instruction given to me, not from an
  owner-held record.
- Documents under `docs/release/` not changed by this delta, and unchanged passages of the
  changed documents, beyond a search for "attempt", "redeploy", "deploy again" and
  failed-acceptance phrases (which produced finding 1).
- `deploy/LIGHTSAIL_RUNTIME.md` was not re-read; the wrapper names were compared with the
  runbook's own section 6.
