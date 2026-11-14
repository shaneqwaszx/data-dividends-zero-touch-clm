# Closing check of the fix for F-1 and F-2 (commit ed38d16)

Checker: fresh, independent; did not write the code; fixed nothing. Date: 2026-11-15.
Everything below was observed on the mock host (`tests/release/fakes.py`) only. No host, AWS,
SSH, registry or network contact; `.env` not read; no tracked file edited; nothing committed.
Probes, the random driver and the scratch copy for mutants lived in a temporary directory
outside the repository.

## 1. Identity and exact command results

| Item | Value |
|---|---|
| Worktree | `.claude/worktrees/release-pipeline-local-controller-bf1647` |
| `git rev-parse HEAD` | `ed38d160c224aa4e6326ae15a0adfdb8e8d15ca2` |
| `HEAD^{tree}` | `419b08f1deac6669961c420be97dc525ccd1d8a8` |
| `git status --short` (start and end) | `?? outputs/` only |
| Previously checked | `6bcf1423717ddd1f21e269c0394d8d0104345b23` (verdict FAIL, conditional) |
| Delta `6bcf142..ed38d16` | 8 files, +587 / -17 (`tools/release/deploy.py`, `tools/release/records.py`, `tests/release/test_rollback_interruption.py`, 5 documents under `docs/release/`, one of them the unedited copy of the previous report) |

`CLM_RELEASE_STATE_DIR` pointed at a new empty directory outside the repository (still empty
afterwards).

| Command | Result |
|---|---|
| `python -m pytest tests/release -q -p no:cacheprovider`, run 1 | 321 passed, 1 skipped in 23.76s |
| run 2 | 321 passed, 1 skipped in 25.10s |
| `python -m pytest tests/deploy -q -p no:cacheprovider` | 116 passed, 1 skipped in 11.13s |
| `python -m ruff check --select E,F,I,UP,B,SIM --line-length 100 --target-version py312 tools/release tests/release` | All checks passed! |
| `python -m mypy --strict -p tools.release` | Success: no issues found in 19 source files |
| `python scripts/check_secrets.py` | Secret scan passed: no supported secret patterns found. (exit 0) |

## 2. Verdict

**PASS WITH NOTES**

Counts: P0 0, P1 0, P2 1, P3 6.

F-2 is fixed. The rule "within one deployment a failed acceptance can never become
`ACCEPTED`" held in every probe and in 3,300 random sequences (0 hits). The one P2 is a
statement in the architecture document that the code does not deliver (N-1 below); it does not
weaken a safeguard. The open owner decision on redeploying a release that once failed
acceptance is still open and is correctly recorded as open; this verdict does not settle it.

## 3. F-2 and F-1

### F-2 (P2): FIXED

Fix: `tools/release/deploy.py:686-705` (`_record` reads the standing record; an outcome in
`FAILED_NO_CHANGE` or `DRY_RUN_OK` is written with `standing=False` when the standing record's
state is in `records.LIVE`), `tools/release/records.py:36-45` (`LIVE`), `:70-83`
(`write_result(..., standing=)`).

My own probe, the three rows of the earlier table plus a held record with no rollback block,
each in execute and dry-run (8 cases). In all 8: the second run ended `FAILED_NO_CHANGE` /
`PREFLIGHT_FAILED`, the standing record was byte-for-byte the same before and after, exactly
one numbered file was added (it carries `standing_record_kept: <state>`), 0 host writes
reached the mock, both locks were released.

```
standing record before                              second run (execute and dry-run)   standing after   then
DEPLOYED_AWAITING_ACCEPTANCE                        FAILED_NO_CHANGE, kept             identical        accept pass -> ACCEPTED, pointer moved; (fresh copy) rollback -> ROLLED_BACK, pins previous; recover -> RECOVERY_NOT_APPLICABLE (correct: no unfinished rollback)
ACCEPTANCE_FAILED (acceptance_failed true)          FAILED_NO_CHANGE, kept             identical, flag kept   accept pass -> ACCEPTANCE_NOT_PENDING; rollback -> ROLLED_BACK with acceptance_failed carried; accept pass afterwards -> ACCEPTANCE_NOT_PENDING
FAILED_HELD / RECOVERED_ON_RELEASE_NOT_ACCEPTABLE   FAILED_NO_CHANGE, kept             identical, stop code SMOKE_FAILED and rollback block kept   accept pass -> ACCEPTANCE_NOT_PENDING; rollback -> ROLLED_BACK; accept pass afterwards refused; pointer None
FAILED_HELD, no rollback block (assistant unhealthy) FAILED_NO_CHANGE, kept            identical        accept pass refused; recover -> RECOVERY_NOT_APPLICABLE; rollback reaches the eligibility rules (ROLLBACK_REFUSED: assistant data compatibility unproven), no longer ROLLBACK_NOT_APPLICABLE
```

The second part of the earlier F-1 (a dry-run removed `acceptance_failed` from the latest
record) is closed by the same change: row 2.

Random driver: 5,773 no-change runs met a LIVE standing record; the record was identical
afterwards in all 5,773 and each numbered result carried the right `standing_record_kept`.
8,282 no-change runs met a non-LIVE or absent record; all replaced it and none carried the
field.

### F-1: assessment

What holds (probes and driver, section 5): inside one deployment nothing turns a failed
acceptance into `ACCEPTED`. After `accept` fail: `accept` pass, `recover`, an owner rollback,
`accept` pass again, a `run --execute` with the original approval (`APPROVAL_ALREADY_USED`),
a dry-run, `accept` pass again are all refused or leave the release unacceptable. In 3,300
sequences `ACCEPTED` was never reached, and the pointer never moved, without an execute `run`
that itself ended `DEPLOYED_AWAITING_ACCEPTANCE` after the last failed acceptance or stop.

The kept path behaves as documented:

```
deploy -> accept fail -> owner rollback ROLLED_BACK (acceptance_failed true)
run --execute, new approval -> DEPLOYED_AWAITING_ACCEPTANCE  previously_failed_acceptance=True, no acceptance_failed
accept pass -> ACCEPTED  previously_failed_acceptance=True, pointer moved
numbered files: DEPLOYED_AWAITING_ACCEPTANCE, ACCEPTANCE_FAILED, ROLLBACK_IN_PROGRESS, ROLLED_BACK, FAILED_NO_CHANGE, DRY_RUN_OK,
                DEPLOYED_AWAITING_ACCEPTANCE, ACCEPTED   (the four written before the new run: unchanged, compared field by field)
```

Driver: 322 complete deployments followed an earlier failed acceptance; all 322 records
carried `previously_failed_acceptance: true` and no `acceptance_failed`. 49 were then accepted;
all 49 `ACCEPTED` records carried the flag and the `ACCEPTANCE_FAILED` file was still present.

My own view, on the merits: keeping the path is consistent with "no change to deployment
approval policy", and I would not block it in this remediation. It needs a new, unused owner
deploy approval bound to the manifest hash, a preflight that finds the host healthy on the
rollback target, the whole apply and verification, and then an interactive owner pass.
Blocking it would add a new policy rule (one failed browser acceptance retires a release id
for good) that nobody asked for, and an acceptance can fail for a reason outside the images.
The narrowed sentence ("permanent for that deployment") is the accurate one. Three things the
owner should know before deciding the open question:

1. The owner is not shown the history when recording acceptance (N-1, P2).
2. The path is wider than the documents say: it does not need a verified `ROLLED_BACK`
   (N-4, P3).
3. A deploy approval carries nothing that says "I know this release failed acceptance
   before"; the new approval is an ordinary one. Whether that is enough is the owner's call.

## 4. New findings

### N-1. P2: the document says the owner sees the acceptance history at acceptance time; the accept path does not show it

`docs/release/PIPELINE_ARCHITECTURE.md:312-313`: "The new record carries
`previously_failed_acceptance: true` so the owner sees the history at acceptance time".
`tools/release/cli.py:303-313` (`cmd_accept` prints only `state` and `known_good`),
`tools/release/deploy.py:1793-1821` (the browser acceptance runsheet has no such line),
`tools/release/cli.py:355-372` (`status` prints states only). The flag is read nowhere except
`_record` (`deploy.py:688-694`).

Observed by reading the CLI, not run: the flag is in the stored record and in the full JSON
the `deploy` command prints (one key among about twenty). Nothing at `accept` reads it or
prints it, and the runsheet written for the owner does not mention it. The runbook does not
mention the field at all.

Why it matters: the decision to keep the F-1 path leans on this sentence. As built, an owner
who follows the runsheet and types `accept --result pass` is told nothing about the earlier
failure unless they open the JSON. Either the sentence should say where the flag actually is,
or `accept` and the runsheet should show it. No safeguard is weakened; the claim is wider than
the code.

### N-2. P3: a `FAILED_NO_CHANGE` record can follow a real pin change (older behaviour), and the kept standing record then does not show it

`tools/release/deploy.py:923-927` (`env_changed` is set after the `sed` returns),
`:736-739` (`_interrupted` decides "no change" from the flags), `:698-705`.

This is the only way I found for a no-change record to hide a change. An interrupt that
arrives after the first `sed` took effect but before the flag is set:

```
[no standing record]  run, interrupted right after the first sed -> FAILED_NO_CHANGE / INTERRUPTED; compose.env: BACKEND_IMAGE now the release pin; containers unchanged
[standing DEPLOYED_AWAITING_ACCEPTANCE, host put back by hand]   same -> FAILED_NO_CHANGE, standing_record_kept, standing record unchanged; same pin change
```

Driver: 26 of 617 after-effect interrupts that produced `FAILED_NO_CHANGE` left one pin
changed (2 with the standing record kept); no container differed in any of them. The lag
itself predates this delta and is stated in `PIPELINE_ARCHITECTURE.md` ("The deployment path
before any rollback still sets its flags after a command returns"), and the runbook tells the
operator to compare `compose.env` with the backup after any interrupt. What is new: with a
LIVE standing record, `status` keeps showing that record and gives no sign of the interrupted
attempt; only the last numbered file does. The committed tests cannot see this window because
the mock's hook fires before a command takes effect.

The other three sources named in the brief are clean: `_resume_previous` after a failed
backend or ingress stop (pins restored, same container ids, running), a restored
`compose.env` after expiry (identical), and a failed restore (`FAILED_HELD`, which replaces
the standing record). Dry-runs: 0 host writes in 7,213.

### N-3. P3: the kept record is not always "the record that describes the host"

`PIPELINE_ARCHITECTURE.md:322-324`; `deploy.py:698-701`. A run can only get past preflight
when the host is on the previous images. If the standing record is LIVE at that moment (the
host was put back by hand, or a `FAILED_HELD` was repaired by hand as its own
`manual_next_step` tells the operator), a dry-run ends `DRY_RUN_OK` and the stale record is
kept (419 times in the driver):

```
DEPLOYED_AWAITING_ACCEPTANCE, host put back by hand -> dry-run DRY_RUN_OK, standing_record_kept -> accept pass -> ACCEPTED, pointer moved
the same without the dry-run                         -> accept pass -> ACCEPTED
```

So nothing new becomes possible: `accept` never looked at the host. But before this delta
that dry-run would have replaced the record and `accept` would have refused; and a
`FAILED_HELD` repaired by hand now stays `FAILED_HELD` until a run changes something. The
sentence should say the record is kept, not that it describes the host.

### N-4. P3: the documents describe the kept F-1 path as narrower than the code allows

`PIPELINE_ARCHITECTURE.md:308-311` and `TEST_EVIDENCE_AND_LIMITATIONS.md` section 4.5 say
"after a verified `ROLLED_BACK`". The code needs no rollback record: any execute run that
passes preflight starts a new deployment. Probe: standing `ACCEPTANCE_FAILED`, host put back
by hand, `run --execute` with a new approval -> `DEPLOYED_AWAITING_ACCEPTANCE`
(`previously_failed_acceptance: true`) -> acceptable. Driver: a new
`DEPLOYED_AWAITING_ACCEPTANCE` record replaced a standing `ACCEPTANCE_FAILED` 44 times, a
standing `ACCEPTED` 59 times and a standing `FAILED_HELD` 75 times, each after a hand change
to the mock. Every one was a complete verified deployment under a new approval, so the rule
in section 3 holds; the wording is what is off.

### N-5. P3: `_record` now reads the standing record before every write, with no retry

`deploy.py:687`, `tools/release/core.py:476-482`. The write path retries a Windows sharing
violation for about two seconds; the new read does not. Probe, one `PermissionError` on that
read:

```
at the final record of a successful deploy        -> the error propagates; no record at all; host on the release
at the in-progress record before an automatic rollback -> FAILED_HELD "automatic rollback was not started: ROLLBACK_NOT_RECORDED"; host on the release
at the final record after an automatic rollback   -> the error propagates; record stays ROLLBACK_IN_PROGRESS
```

All three fail closed (nothing acceptable is recorded). A failed write at the same places
already behaved this way; this adds one unretried file operation ahead of each.

### N-6. P3: test gaps (mutation check, section 5)

No discriminating test for: a non-LIVE standing record being replaced by a no-change run
(M02); a dry-run that ends `DRY_RUN_OK` over a LIVE record (M03; the committed dry-run cases
all stop at preflight); `ACCEPTED` in `LIVE` (M09); the history flag carried from
`previously_failed_acceptance` to a later record (M12). My probes and the driver show the code
is right in all four.

### N-7. P3: wording

- The previous check's F-5 items are unchanged and section 4.5 does not list them:
  `PIPELINE_ARCHITECTURE.md:289` ("FIRST rollback"), `deploy.py:616-618`,
  `RELEASE_AUTOMATION_RUNBOOK.md:245-246` ("when its first rollback began"),
  `deploy.py:1210` (`SETTLED_BEFORE_ROLLBACK` unused), `ACCEPTANCE_ALREADY_FAILED` in no
  document. Section 4.5's "P3 test gaps" row names the two tests added and is silent on the
  other two gaps (previous M11, M15).
- `standing_record_kept` and `previously_failed_acceptance` appear in no runbook section. An
  operator who sees exit code 2 from a refused run is not told that `status` still shows the
  earlier state on purpose.
- `RELEASE_AUTOMATION_RUNBOOK.md:261-265` (new): the hand command is given as `dc up ...
  <service>`. Per `deploy/LIGHTSAIL_RUNTIME.md:59` `dc` cannot start the assistant; for that
  service it would be `dca`. By reading, not run.
- `TEST_EVIDENCE_AND_LIMITATIONS.md:222`: `@@CHECK6@@` placeholder present (expected).

## 5. What I checked and found sound

- **Random driver.** 3,300 sequences (300 unguided, 3,000 weighted by the current state), 6 to
  22 steps, five service sets. Operations: `run` execute 13,192, dry-run 7,213, `accept` pass
  6,940, `accept` fail 3,328, `manual_rollback` 8,855, `recover` 6,960. Injected: an interrupt
  before a command (`KeyboardInterrupt`, `RuntimeError`, a non-`Exception` kill), an interrupt
  after a host write took effect, approval expiry mid-run, mock faults (`up` fails, stop
  fails, unhealthy, restore fails, smoke 502, wrong image, extra backend, pull fails, wrong
  diff count), hand changes to the mock between steps. Results:

  ```
  accept pass -> ACCEPTED 597; complete verified execute deployments 2,709
  ACCEPTED, or pointer moved, without a complete verified execute deployment since the last failed acceptance or stop ... 0
  pointer moved by anything other than a successful accept ......................... 0
  recover returned a not-clean deployment to DEPLOYED_AWAITING_ACCEPTANCE ............ 0  (13 returns, all clean)
  recover issued a host write or changed the mock .................................... 0 of 6,960
  accept (pass or fail) over an unfinished rollback: 937 + 356 refused ROLLBACK_INCOMPLETE, 0 succeeded
  ROLLED_BACK written while a service was not on its previous pin and image .......... 0  (2,415 records)
  LIVE standing record replaced by a no-change run ................................... 0 of 5,773
  a run that changed something did not become the standing record .................... 0
       (LIVE record replaced by DEPLOYED_AWAITING_ACCEPTANCE 192, FAILED_HELD 148, ROLLED_BACK 23)
  standing_record_kept in the standing record, or on a record that is not no-change .. 0
  standing_record_kept missing, wrong, or present over a non-LIVE record ............. 0
  acceptance history missing from a standing record after a failed acceptance ........ 0
  an acceptance-failure flag with no failed acceptance ............................... 0
  an earlier numbered record changed; a local lock left behind ...................... 0; 0
  run or dry-run over an unfinished rollback: 1,286 refused, nothing written
  host differs after a no-change record .............................................. 26 (N-2)
  ```

- **`previously_failed_acceptance`.** Set by `_record` from the standing record; survives an
  automatic rollback (the in-progress record is written through `_record`, so the final record
  still finds it), a `FAILED_NO_CHANGE`, a `FAILED_HELD`, a second failed acceptance and a
  third deployment (probe). Not set on a record that itself has `acceptance_failed`. It blocks
  nothing: `accept`, `recover` and `manual_rollback` do not read it.
- **`standing_record_kept`.** Only on numbered `FAILED_NO_CHANGE` / `DRY_RUN_OK` results over
  a LIVE record. It cannot reach `accept`, `manual_rollback` or `recover`, which copy the
  standing record, because a kept result is never the standing record.
- **Nothing removed.** The delta deletes no command, field or test; `write_result` keeps its
  default.
- **Mutation check.** 17 mutants on lines this delta changed or that its tests target, scratch
  copy from `git archive ed38d16`, `tests/release` with the one git-dependent test deselected
  (baseline 320 passed, 1 skipped; same after restoring; both source files hash-equal to the
  commit afterwards, ignoring line endings). **13 killed, 4 survived.**

  | Mutant | Result | Killed by |
  |---|---|---|
  | M01 standing record always replaced | killed | `test_a_run_that_changes_nothing_...[awaiting-EXECUTE]` |
  | M02 any standing record kept (LIVE ignored) | **survived** | (N-6) |
  | M03 `DRY_RUN_OK` not treated as no-change | **survived** | (N-6) |
  | M04 `FAILED_NO_CHANGE` not treated as no-change | killed | same test |
  | M05 a `FAILED_HELD` outcome also kept out | killed | `test_repeated_rollback_after_a_failed_automatic_one_...` |
  | M06 `LIVE` without `FAILED_HELD` | killed | `...[held-EXECUTE]` |
  | M07 `LIVE` without `ACCEPTANCE_FAILED` | killed | `...[acceptance-failed-EXECUTE]` |
  | M08 `LIVE` without `DEPLOYED_AWAITING_ACCEPTANCE` | killed | `...[awaiting-EXECUTE]` |
  | M09 `LIVE` without `ACCEPTED` | **survived** | (N-6) |
  | M10 `standing_record_kept` not written | killed | same test |
  | M11 `previously_failed_acceptance` never set | killed | `test_a_new_verified_deployment_after_a_verified_rollback_carries_the_acceptance_history` |
  | M12 history not carried from `previously_failed_acceptance` | **survived** | (N-6) |
  | M13 `standing=False` drops the numbered file too | killed | `test_a_run_that_changes_nothing_...` |
  | M14 `write_result` ignores `standing` | killed | same test |
  | M15 the history flag blocks `accept` | killed | the F-1 test |
  | M16 run refusal ignores the rollback-block status | killed | `test_a_new_run_is_refused_over_a_held_record_whose_rollback_failed` |
  | M17 `recover` ignores the episode origin | killed | `test_recover_needs_the_awaiting_acceptance_origin_even_without_other_marks` |

  Each of the four tests added in this delta fails when its own safeguard is removed.
- **Documents.**
  - `docs/release/N1_N2_FINAL_CHECK_20261114.md` is byte-identical to
    `outputs/release-pipeline-20261114/N1_N2_FINAL_CHECK.md` (sha256
    `f5b56e67fd95cf8e821a9eeed82ed4d8a07b768a8c58242a7cecda0cb958286e`, working copy and
    committed blob).
  - `TEST_EVIDENCE_AND_LIMITATIONS.md` line 12: "321 passed, 1 skipped", "6 test files",
    "212 test functions" all match (32 + 41 + 25 + 35 + 55 + 24). Section 4.5: commit, tree,
    verdict and summary match the previous report; every test named exists and passes; the
    F-2, F-3 and "second part" rows match the code. Off: "after a verified `ROLLED_BACK`"
    (N-4); the P3 row (N-7).
  - `PIPELINE_ARCHITECTURE.md` 3.7: "permanent for that deployment", the list of live states
    (equal to `records.LIVE`) and "kept as a numbered result but never replaces the standing
    record" match the code. Off: "so the owner sees the history at acceptance time" (N-1);
    "the record that describes the host" (N-3); "after a verified `ROLLED_BACK`" (N-4).
  - `RELEASE_AUTOMATION_RUNBOOK.md` section 7: the added paragraph matches the code's failure
    text; `dc` for the assistant (N-7).
  - `README.md`: the new row is accurate.

## 6. What rests only on the mock

- Every result here. The mock's `sed`, `cp`, `stop`, `start` and `up` are atomic and instant.
- "Interrupt after the command took effect" is my wrapper around the mock's runner; on a real
  host it stands for a Ctrl-C or a dropped SSH session after the remote command completed.
- "Host put back by hand" and the other hand changes are edits to the mock's state.
- The read failure in N-5 is a patched `read_result`; whether a real Windows scanner can make
  that read fail was not tested.
- No CLI-level run (`release.ps1`) was made. `deploy.*` functions were called as the tests call
  them, with `render.validate_release_config` stubbed. N-1 was established by reading
  `cli.py`, not by running it.
