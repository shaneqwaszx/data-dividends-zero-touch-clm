# Release pipeline: independent check of the documents-only delta `b97fa59..1cfa9bd`

## 1. Identity, scope and command results

| Field | Value |
|---|---|
| Checker | Fresh session; did not write the delta or the code. Check only; nothing fixed |
| Date | 2026-11-15 |
| Evidence class | **Mock and Local only.** Reading, plus one probe on `tests/release/fakes.py`. No host, AWS, SSH, registry, network, `.env` or `--execute` against anything real |
| Base | `b97fa598626e3f6be185e7ea65e7125cbb0fa9c0` |
| Checked | `1cfa9bd2ded24081d6ba4f8410023c5381bfcb9b`, tree `6fb569429b7d323c1accf9d2af8b1d1ab4f3e28f` (confirmed with `git rev-parse HEAD HEAD^{tree}`) |
| Worktree | `git status --short` before and after: only `?? outputs/` |
| Review answered | `outputs/integration-release-lead-20261114/PIPELINE_FINAL_DELTA_REVIEW.md` (main checkout), Parts A.3, C, D |

Scope: `git diff --stat b97fa59 1cfa9bd` lists six files, all under `docs/release/`
(checklist, architecture, how-to, README, runbook, evidence; 139 insertions, 42 deletions).
`git diff b97fa59 1cfa9bd -- . ':!docs'` is empty. **No code, test, schema or sample changed.**

| Command (run once, at `1cfa9bd`) | Result |
|---|---|
| `python -m pytest tests/release -q -p no:cacheprovider` (`CLM_RELEASE_STATE_DIR` set to a new empty temp directory) | **321 passed, 1 skipped** (28 s) |
| `python scripts/check_secrets.py` | **Secret scan passed** |

## 2. Verdict

**PASS WITH NOTES** (P1 0, P2 1, P3 7).

The four instructions were carried out. The A-1 correction in the runbook is true against the
code and the hand-recovery step is safe. The owner decision is quoted verbatim, with the six
requirements and the six statuses exactly as instructed, and nothing claims more enforcement
than the code has. The one P2 is in two sentences the delta added beyond the instructions
(architecture limitation 4h and one checklist row): they say `rollback` refuses every
`FAILED_HELD` record left by an interrupt during `up`, which is not so for a backend. I do not
rate it a FAIL: the runbook procedure itself states the condition correctly, the sentences are
true for the first-use scope (one frontend or assistant), and the error is on the cautious
side (trying `rollback` is harmless). It should still be corrected.

## 3. Rows A-1 to A-13

| Row | Applied | True against the code | Document location | Code checked |
|---|---|---|---|---|
| A-1 (P2) | Yes, reviewer's wording, both bullets | **True.** Probe (section 3.1): frontend-only and assistant-only, interrupt during `up` before and after effect, give `FAILED_HELD`, `applied: []`, `ingress_stopped: false`, no rollback block; `rollback` gives `ROLLBACK_NOT_APPLICABLE`, `recover` gives `RECOVERY_NOT_APPLICABLE`, the record stays `FAILED_HELD`. One sentence is imprecise (finding 2) | `RELEASE_AUTOMATION_RUNBOOK.md:209-220` | `deploy.py:1039-1047` (flag after the command), `736-750`, `1349-1350`, `1596-1597`, `1675-1681` |
| A-2 | Yes, verbatim, both places | True as worded; "six" now disagrees with the README's "seven" (finding 5) | `PIPELINE_HOW_TO_USE_AND_MAINTAIN.md:10-13`, `:124-126` | evidence document 4.7, 4.8 |
| A-3 | Yes, verbatim; table header "(not re-reviewed)" also removed | True | `TEST_EVIDENCE_AND_LIMITATIONS.md:82`, `:91-92`, `:94` | n/a |
| A-4 | Yes, verbatim | True | `PIPELINE_HOW_TO_USE_AND_MAINTAIN.md:110-113` | `deploy.py:1530-1538`, `1730-1749` |
| A-5 | Yes, verbatim | True: on the owner path `_begin_rollback` raises before the approval is consumed and nothing is recorded | `PIPELINE_ARCHITECTURE.md:341-344` | `deploy.py:1178-1185`, `1278-1285`, `1616-1620` |
| A-6 | Yes, verbatim | True | `PIPELINE_ARCHITECTURE.md:312-315` | `deploy.py:538`, `814-815`, `919-920` |
| A-7 | Yes, verbatim | True | `RELEASE_AUTOMATION_RUNBOOK.md:161-163` | `approval.py:63-64`, `83-84`; `records.py:143-145`; `cli.py` `approve --action` is repeatable |
| A-8 | Yes, verbatim | True | `RELEASE_AUTOMATION_RUNBOOK.md:273-275` | `catalog.py` wrapper selection (`goldtier` for the backend when that overlay is active); `deploy/LIGHTSAIL_RUNTIME.md:131-137` |
| A-9 | Yes: diagram and runbook now say "the current rollback episode"; the N-7 row is extended; the three names are now in the runbook | True. The runbook adds "and that has not failed acceptance", which is correct. The N-7 row was adapted, correctly, to say the items are corrected in this pass | `PIPELINE_ARCHITECTURE.md:288-290`; `RELEASE_AUTOMATION_RUNBOOK.md:254-255`, `:301-303`; evidence `:243` | `deploy.py:1215-1242`, `698-705`, `1850-1854` |
| A-10 | (a) verbatim; (b) verbatim; (c) applied as step E1a, deliberately stronger than the reviewer's wording ("stop", as instruction 4 requires) | True: the flag is in the standing record and the `deploy` output; `accept`, the runsheet and `status` do not print it | `FIRST_AUTOMATED_RELEASE_CHECKLIST.md:58`, `:68`, `:71` | `deploy.py:688-694`, `1793-1821`; `cli.py` `cmd_deploy`, `cmd_accept`, `cmd_status` |
| A-11 | Yes, verbatim | True | `RELEASE_AUTOMATION_RUNBOOK.md:163-165` | `deploy.py:1530-1538`, `1555-1556` |
| A-12 | Yes: section 3.8, runbook subsection, evidence 4.8, 4.5 and 4.6 text, how-to known gaps | See section 4. One index line still says "open owner decision" (finding 4) | `PIPELINE_ARCHITECTURE.md:321-323`, `:385-406`; `RELEASE_AUTOMATION_RUNBOOK.md:289-303`; evidence `:214`, `:228`, `:280-287` | section 4 |
| A-13 | Yes, verbatim | True: `accept` takes the store and the manifest only and issues no host command | `PIPELINE_ARCHITECTURE.md:330-333` | `deploy.py:1824-1868` |

### 3.1 Probe for A-1

Method: `tests/release/fakes.py`, `render.validate_release_config` stubbed as the tests do,
`KeyboardInterrupt` raised on the Nth `up -d` command, before it takes effect and after. Then
`manual_rollback` with a new `rollback` approval, `recover`, `accept`. Kept outside the
repository.

| Release | Interrupt | Record | `rollback` | `recover` |
|---|---|---|---|---|
| frontend | during `up`, before and after effect | `FAILED_HELD`, `applied: []`, `ingress_stopped: false` | `ROLLBACK_NOT_APPLICABLE` | `RECOVERY_NOT_APPLICABLE` |
| assistant | same | same | `ROLLBACK_NOT_APPLICABLE` | `RECOVERY_NOT_APPLICABLE` |
| backend | during backend `up`, before and after effect | `FAILED_HELD`, `applied: []`, **`ingress_stopped: true`** | **runs, `ROLLED_BACK`** | n/a |
| backend + frontend | during backend `up` | as backend | **runs, `ROLLED_BACK`** | n/a |
| backend + frontend | during frontend `up`, before effect | `FAILED_HELD`, `applied: ["backend"]` | runs, `ROLLED_BACK` | n/a |
| backend + frontend | during frontend `up`, after effect | `FAILED_HELD`, `applied: ["backend"]` | runs, ends `FAILED_HELD` (the never-applied frontend runs the release image; known F-3, covered by runbook section 7 step 4) | then applies |

In every "after effect" row the container already ran the release image while `applied` did
not name it. `accept` refused in all ten cases.

The hand-recovery instruction (copy the backup named in `env_backup` over `compose.env`, then
the service's own wrapper `up -d --no-build --no-deps --wait <service>`) matches
`deploy/LIGHTSAIL_RUNTIME.md:86`, `:96`, `:117`, and uses none of `down`, `-v`,
`--remove-orphans` or a volume removal (`LIGHTSAIL_RUNTIME.md:107`, `:118`). The copy is the
same command the tool itself records as `manual_next_step` (`deploy.py:1143-1145`). Step 2 of
the same procedure already has the operator confirm no `docker compose` command is still
running first. Safe.

## 4. The owner decision

| Check | Result |
|---|---|
| Quoted verbatim | Yes, in `PIPELINE_ARCHITECTURE.md:387-388` and evidence `:280-281`: "A release that previously failed acceptance MAY be deployed again, but only as a NEW release attempt." The runbook (`:291-292`) paraphrases and points to 3.8 |
| Six requirements | As instructed, in order (`PIPELINE_ARCHITECTURE.md:397-402`) |
| Six statuses | (1) PARTLY, (2) NOT ENFORCED, (3) PARTLY, (4) PARTLY, (5) ENFORCED, (6) ENFORCED: exactly as instructed, in 3.8 and in evidence `:283-284` |
| "Requirements 1 to 4 are NOT fully implemented" stated plainly | Yes: `PIPELINE_ARCHITECTURE.md:392`, evidence `:284`, how-to known gaps, runbook `:292-293` (wording note, finding 6) |
| Nothing implemented | Stated (`:392-393`, evidence `:285`, `:289`) and true: the non-document diff is empty |
| "What holds today" and "gap / smallest change" against Part C | Faithful for all six rows. Dropped: the reviewer's evidence counts, line references and line-count estimates only. Nothing added or softened. The two behaviours the owner is asked to confirm (row 5) and the two "to know" items (row 6) are kept |
| Section references | 3.8, 4.8, runbook section 7 and E1a all exist |

Spot-check of requirements 1 to 4 against the code:

| # | Document says | Code |
|---|---|---|
| 1 | Next file number is "count + 1"; a hand-removed numbered file makes the next write overwrite the newest | `records.py:79-80`: `len(glob("result-*.json")) + 1`, then `write_json` (not exclusive). True |
| 2 | No attempt identifier; the pointer names release id and manifest hash only | No `attempt_id` anywhere in `tools/release`; `records.py:128-133` (release id, manifest hash, time, previous). True |
| 3 | "New" means "unused"; nothing compares the approval time with the failure | `approval.py:57-84` checks manifest, release, action, services, risk, window, used; `approved_at` is written (`:155`) and never read. True |
| 4 | With `rollback.target_image: null`, preflight does not compare the current pin | `deploy.py:538`. True. `deploy` does not re-run `verify-source` (`deploy.py:770-802`). True |

No sentence claims more enforcement than the code has. The instruction "do not redeploy the
same release ... prepare a new release (a new release id and manifest)" can be followed: a
release id is any `rel-...` name (`records.py:62`).

## 5. Findings

| # | Sev | Where | What is wrong | Wording I would use |
|---|---|---|---|---|
| 1 | **P2** | `PIPELINE_ARCHITECTURE.md:455-458` (limitation 4h); `FIRST_AUTOMATED_RELEASE_CHECKLIST.md:71` | Over-general. (a) "`applied` is empty" holds only when no earlier service was applied. (b) "`rollback` and `recover` both refuse that record" is false for a backend: ingress was stopped before the `up`, so the record has `ingress_stopped: true`, `_touched` returns the backend (`deploy.py:1033`, `1349`) and `rollback` runs (probe: `ROLLED_BACK`). True for a frontend or assistant going first, which is the first-use scope. Not requested by the instructions (section 6) | 4h: "An interrupt during a service's `up` is recorded `FAILED_HELD` without that service in `applied` (the flag is set after the command returns), while its container may already run the release image. When `applied` is empty and `ingress_stopped` is false (a frontend or assistant that goes first), `rollback` refuses the record (`ROLLBACK_NOT_APPLICABLE`), `recover` refuses it (`RECOVERY_NOT_APPLICABLE`) and recovery is by hand (runbook section 7). For a backend, ingress was already stopped, so `ingress_stopped` is true and `rollback` stays available under a new approval." Checklist row title: "`FAILED_HELD` with an empty `applied` list and `ingress_stopped: false` after an interrupt" |
| 2 | P3 | `RELEASE_AUTOMATION_RUNBOOK.md:215` | "If `applied` is empty, the tool refuses" drops the second half of the condition stated one sentence earlier (reviewer's own wording) | "If `applied` is empty and `ingress_stopped` is false, the tool refuses (`ROLLBACK_NOT_APPLICABLE`) ..." |
| 3 | P3 | `TEST_EVIDENCE_AND_LIMITATIONS.md:232-233`, `:255` | Stale against the new 4.8: "The commit after it ... was not itself reviewed", and the 4.7 row "head, documents only, after `ed38d16`: not reviewed". `b97fa59` was reviewed (4.8), and the head is now a later commit. The how-to (`:11`) points to 4.7 alone | `:232-233`: "... changes documents only and was reviewed afterwards (section 4.8)." Table: replace the last row with "`b97fa59`, documents only: PASS WITH NOTES (seventh review, 4.8)" and add "`1cfa9bd`, documents only: see 4.8" |
| 4 | P3 | `README.md:22` | Still says "the open owner decision"; the decision was made (evidence 4.5, 4.8) | "What was done about it, and the owner decision that followed: evidence document sections 4.5 and 4.8" |
| 5 | P3 | `PIPELINE_HOW_TO_USE_AND_MAINTAIN.md:10-11` | "six independent reviews and checks ... (section 4.7)" against `README.md:5` "seven" and evidence 4.8 "a seventh independent review". The reviewer's wording was right when written | "It has been through seven independent reviews and checks; the latest on code, at the last code commit, is PASS WITH NOTES (`TEST_EVIDENCE_AND_LIMITATIONS.md` sections 4.7 and 4.8)." |
| 6 | P3 | `RELEASE_AUTOMATION_RUNBOOK.md:292-293` | "does not yet enforce four of the six requirements": three of the four are partly enforced | "The tool does not yet fully enforce requirements 1 to 4 of that decision (three partly, one not at all)." |
| 7 | P3 | `FIRST_AUTOMATED_RELEASE_CHECKLIST.md:58` (E1a); `RELEASE_AUTOMATION_RUNBOOK.md:297-299` | E1a says "stop. Do not accept" but names no next step while the release is live and awaiting acceptance; the runbook bullet says what the flag means but not what to do | Add to both: "Do not accept. Tell the owner; the owner decides between `accept --result fail` followed by a rollback under a new `rollback` approval (section 6), or a rollback directly." |
| 8 | P3 | `RELEASE_AUTOMATION_RUNBOOK.md:217-219` | The hand-restore step says "the service's own wrapper" without naming it; the names are 55 lines later (`:273-275`). With the hosted provider overlay active the tool uses a fourth wrapper set (`catalog.py`, `assistant-provider`) that `deploy/LIGHTSAIL_RUNTIME.md` does not define as a helper. Out of first-use scope (checklist G) | After "the service's own wrapper": "(`dc` for the frontend or backend, `dcg` for the backend when the GoldTier overlay is active, `dca` for the assistant)" |

No P1. No unsafe or impossible instruction found. Nothing in the delta weakens a safeguard in
`deploy/LIGHTSAIL_RUNTIME.md`; runbook section 8 ("Never") is unchanged.

Other consistency checks that came back clean: no remaining "FIRST rollback" in the diagram or
runbook; no remaining "not re-reviewed"; limitation labels 4g and 4h are new and unique (the
existing order 4b, 4d, 4e, 4f, 4c was already non-alphabetical); `@@CHECK7@@` is present once,
at evidence `:291`, as expected.

## 6. Changes not covered by instructions 1 to 4

| Change | Accurate? |
|---|---|
| `PIPELINE_ARCHITECTURE.md:5` status line rewritten (several reviews; latest on code PASS WITH NOTES; not cleared) | Yes. The old line was stale in the same way as A-2 |
| `README.md:5-6` "seven"; `:19` first-review row now points to sections 4.1 to 4.8 | Yes (but see finding 4 for `:22`) |
| `PIPELINE_ARCHITECTURE.md:452-454` limitation 4g (audit log gets a line only after a command returns) | Yes: `core.py` logs the `command` event after `runner.run` returns. This is the reviewer's A.5 remark |
| `PIPELINE_ARCHITECTURE.md:455-458` limitation 4h | Over-general: finding 1 |
| `FIRST_AUTOMATED_RELEASE_CHECKLIST.md:71` new row for `FAILED_HELD` with empty `applied` | True for the checklist's scope; condition incomplete: finding 1 |
| `PIPELINE_HOW_TO_USE_AND_MAINTAIN.md:124-126` known gaps: the owner's rule is only partly enforced | Yes |
| `RELEASE_AUTOMATION_RUNBOOK.md:254-255` adds "and that has not failed acceptance" | Yes (`deploy.py:1238-1242`) |
| Evidence 4.8 summary of the seventh review (counts 1,422 / 486 / 700, "all seven claims hold", 1 P2 and 12 P3) | Matches the review text. The coordinator's re-run figures for `tests/deploy`, ruff and mypy are taken on trust |

## 7. Not checked

- Anything on a real host, registry, shell or credential store.
- `tests/deploy`, ruff, mypy and the governance scripts: not run by me. The evidence
  document's statement that the coordinator re-ran them on `b97fa59` is taken on trust.
- The review's Part B figures: compared with the review text only, not reproduced.
- `deploy/LIGHTSAIL_RUNTIME.md`: read by search for the wrappers, `up` forms and "never"
  rules, not end to end.
- The CLI as a process: `cmd_accept`, `cmd_status`, `cmd_deploy` were read, not run.
- The documents in `docs/release/` that this delta did not change, and unchanged passages of
  the six changed documents beyond a search for stale phrases.
- The probe used `KeyboardInterrupt` on the `up` command only, five service sets, two timings;
  it is not a repeat of the reviewer's interruption sweep.
