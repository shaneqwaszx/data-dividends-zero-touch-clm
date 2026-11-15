# Independent check of the fix for N-1, N-2 and N-3 (commit 6bcf142)

Checker: fresh, independent; did not write the code; fixed nothing. Date: 2026-11-15.
Everything below was observed on the mock host (`tests/release/fakes.py`) only. No host, AWS,
SSH, registry or network contact; `.env` not read; no tracked file edited; nothing committed.
Probes and the scratch copy for mutants lived in a temporary directory outside the repository.

## 1. Identity and exact command results

| Item | Value |
|---|---|
| Worktree | `.claude/worktrees/release-pipeline-local-controller-bf1647` |
| `git rev-parse HEAD` | `6bcf1423717ddd1f21e269c0394d8d0104345b23` |
| `HEAD^{tree}` | `69e9f7b79663d8e00a8c4f9814ef8c7712d1b8a2` |
| `git status --short` (start and end) | `?? outputs/` only |
| Previously checked | `84706a97fe57d51ce9098518136181276d5d8080` (verdict FAIL) |
| Delta `84706a9..6bcf142` | 7 files, +645 / -18 (`tools/release/deploy.py`, `tools/release/cli.py`, `tests/release/test_rollback_interruption.py`, 4 documents under `docs/release/`) |

`CLM_RELEASE_STATE_DIR` pointed at a new empty directory outside the repository.

| Command | Result |
|---|---|
| `python -m pytest tests/release -q -p no:cacheprovider`, run 1 | 312 passed, 1 skipped in 21.82s |
| run 2 | 312 passed, 1 skipped in 21.32s |
| run 3 | 312 passed, 1 skipped in 22.00s |
| `python -m pytest tests/deploy -q -p no:cacheprovider` | 116 passed, 1 skipped in 9.69s |
| `python -m ruff check --select E,F,I,UP,B,SIM --line-length 100 --target-version py312 tools/release tests/release` | All checks passed! |
| `python -m mypy --strict -p tools.release` | Success: no issues found in 19 source files |
| `python scripts/check_secrets.py` | Secret scan passed: no supported secret patterns found. (exit 0) |

## 2. Verdict

**FAIL**

The exact N-1 sequence, and every route through `recover` that I could construct or generate,
is now closed. N-2 is fixed. N-3 is fixed for the record it named. The verdict is FAIL because
of one thing: the rule this fix states, that a failed acceptance is permanent for a release,
does not hold. A new `run` of the same release starts a record without the `acceptance_failed`
flag, and an ordinary command sequence then reaches `ACCEPTED` (finding F-1). In every such
case a complete new deployment passed its own verification under a new owner approval before
the acceptance, so this is much narrower than the original N-1; but the stated rule is
absolute ("EVER", "permanent", "whatever the state says") and it is not met.

Counts: P0 0, P1 1, P2 1, P3 3.

If the owner's intent is that a fresh, fully verified deployment of the same release after a
verified rollback may be accepted even though an earlier attempt failed acceptance, then F-1
becomes a wrong sentence in two documents and one code comment (P2), and the verdict would be
PASS WITH NOTES. I did not assume that intent, because the brief and the architecture
document both state the rule without that exception.

## 3. N-1, N-2, N-3

### N-1 (P1): PARTIALLY FIXED (the reported route is closed; the stated permanence rule is not met, see F-1)

Fix: `tools/release/deploy.py:1196-1212` (`_origin_for_new_attempt`: the origin is inherited
only while the previous record is an unfinished or failed rollback), `:1215-1223`
(`_may_return_to_acceptance`: origin awaiting acceptance, no `acceptance_failed`, no
`stop_code`), `:1724` (used by `recover`), `:1831-1835` (`accept` refuses
`ACCEPTANCE_ALREADY_FAILED`), `:1841-1842` (flag set on a failed acceptance), `:1570`.

The exact original sequence, my own probe, frontend-only release, both rollbacks interrupted at
their first `sed`:

```
deploy                      -> DEPLOYED_AWAITING_ACCEPTANCE
owner rollback #1 (Ctrl-C)  -> ROLLBACK_INTERRUPTED  sbr=DEPLOYED_AWAITING_ACCEPTANCE
  accept --result pass      -> REFUSED ROLLBACK_INCOMPLETE
recover                     -> DEPLOYED_AWAITING_ACCEPTANCE / RECOVERED_VERIFIED_ON_RELEASE
accept --result fail        -> ACCEPTANCE_FAILED     acceptance_failed=True
  accept --result pass      -> REFUSED ACCEPTANCE_NOT_PENDING
owner rollback #2 (Ctrl-C)  -> ROLLBACK_INTERRUPTED  sbr=ACCEPTANCE_FAILED  acceptance_failed=True
recover                     -> FAILED_HELD / RECOVERED_ON_RELEASE_NOT_ACCEPTABLE   (0 host writes)
accept --result pass        -> REFUSED ACCEPTANCE_NOT_PENDING
recover again               -> REFUSED RECOVERY_NOT_APPLICABLE
accept --result pass        -> REFUSED ACCEPTANCE_NOT_PENDING
known-good pointer: None
result files: DEPLOYED_AWAITING_ACCEPTANCE, ROLLBACK_IN_PROGRESS, ROLLBACK_INTERRUPTED, DEPLOYED_AWAITING_ACCEPTANCE,
              ACCEPTANCE_FAILED, ROLLBACK_IN_PROGRESS, ROLLBACK_INTERRUPTED, FAILED_HELD
```

The earlier checker's variant (backend+frontend; rollback #1 FAILED at the ingress stop and the
operator re-pinned by hand; rollback #2 failed at the `up` and the operator re-pinned by hand)
gives the same: second `recover` -> `FAILED_HELD`, `accept` pass refused, pointer not moved.

The intended positive path still works (rollback interrupted at its first write, then `recover`,
then `accept` pass), for frontend-only, backend+frontend and all three services:

```
DEPLOYED_AWAITING_ACCEPTANCE -> KeyboardInterrupt -> accept REFUSED ROLLBACK_INCOMPLETE
 -> recover DEPLOYED_AWAITING_ACCEPTANCE -> accept ACCEPTED, known-good moved
files: DEPLOYED_AWAITING_ACCEPTANCE, ROLLBACK_IN_PROGRESS, ROLLBACK_INTERRUPTED, DEPLOYED_AWAITING_ACCEPTANCE, ACCEPTED
```

Search. A randomised driver ran 4,500 call sequences (300 unguided, 4,200 weighted by the
current state so that rollbacks, recoveries and acceptances are actually reached), 6 to 22
steps each, over five service sets. Operations: `run` execute and dry-run, `accept` pass and
fail, `manual_rollback`, `recover`; interrupts (`KeyboardInterrupt`, `RuntimeError`, a
non-`Exception` kill, and a kill with the handler disabled to leave a stale in-progress
record) at a random host command or host write; mock faults (`up` fails, stop fails, unhealthy,
restore fails, wrong image, smoke 502, extra backend); hand changes to the mock between steps
(pins, container images, a hand `up`, everything set to the release or to the previous
images, host lock cleared). Totals for the 4,200 guided sequences:

```
operations: run 13,618  dry-run 2,873  rollback 10,098  recover 6,443  accept pass 5,363  accept fail 3,173
accept pass -> ACCEPTED 506 (380 with no earlier stop code or failed acceptance)
recover -> DEPLOYED_AWAITING_ACCEPTANCE 249   -> FAILED_HELD 320   -> ROLLED_BACK 406   -> ROLLBACK_INTERRUPTED 1,973
accept (pass or fail) called while a rollback was unfinished: 1,266 refused ROLLBACK_INCOMPLETE, 0 succeeded

hits, release ACCEPTED or pointer moved with:
  (c) an unfinished rollback in the latest record ............................ 0
  (a) a stop code recorded since the last fully verified deployment .......... 0
  (b) a failed acceptance since the last fully verified deployment ........... 0
  recover returned a release with a stop code or failed acceptance to awaiting  0
  the flag or the stop code lost by a manual_rollback or recover record ...... 0
  (a) a stop code earlier, then a NEW fully verified run, then accepted ...... 105  (re-run after ROLLED_BACK / FAILED_NO_CHANGE; documented in runbook section 7)
  (b) a failed acceptance earlier, then a NEW fully verified run, accepted ... 37   <- finding F-1
```

So: no route through `recover`, interrupts, failures, stale records or hand changes reached
`ACCEPTED` for a failed or unfinished release. The only hits are the ones that pass through a
new `run`. For (a) that is the documented retry of a release. For (b) it contradicts the rule
this fix added (F-1).

### N-2 (P2): FIXED

Fix: `tools/release/deploy.py:1414-1432` (`_pins_restored`: for every service of the release,
previous pin in `compose.env` and container on the previous image id), called at `:1505` in
the final verification of both rollback paths.

The original scenario (backend+frontend, backend unhealthy so only it was applied, the frontend
then started by hand while still pinned to the release, then the owner rollback):

```
deploy: FAILED_HELD HEALTH_CHECK_FAILED applied ['backend']  pins {backend NEW, frontend NEW}  images {backend NEW, frontend OLD}
after hand `up frontend`: images {backend NEW, frontend NEW}
owner rollback -> FAILED_HELD  rollback.status FAILED  host_state unverified
   failure: ROLLBACK_FAILED "frontend: the container is not running its previous image"
   pins {backend OLD, frontend OLD}  images {backend OLD, frontend NEW}  ROLLED_BACK in result files: False
   accept pass: REFUSED ROLLBACK_INCOMPLETE     recover: ROLLBACK_INTERRUPTED (unknown)
after a hand `up frontend` on the restored pin, owner retry -> ROLLED_BACK, pins and images all OLD
```

The same hand `up` injected during an automatic rollback (three service sets): `FAILED_HELD`,
same failure text, never `ROLLED_BACK`.

A correct rollback is not made to fail by the new check:

```
automatic, all applied, smoke fails:   frontend | backend | backend+frontend | all three | assistant  -> ROLLED_BACK / COMPLETED_VERIFIED, pins and images OLD (5 of 5)
owner-requested from awaiting:         same five sets                                                 -> ROLLED_BACK (5 of 5)
owner-requested from ACCEPTANCE_FAILED: same five sets                                                -> ROLLED_BACK (5 of 5), acceptance_failed kept
partly applied, automatic:  backend+frontend (backend unhealthy); all three (backend unhealthy); all three (assistant unhealthy) -> ROLLED_BACK (3 of 3)
partly applied, owner:      the same three                                                           -> ROLLED_BACK (3 of 3)
```

In the 4,200 guided sequences 4,238 records said `ROLLED_BACK` (649 automatic, 3,183 owner-requested,
406 by `recover`); in every one each service of the release had its previous pin and its
container on the previous image id (0 exceptions).

### N-3 (P2): FIXED for the record it named (an unfinished or failed rollback); the same replacement still happens for three other records, see F-2

Fix: `tools/release/deploy.py:636` (first statement under the local lock in `run`),
`:649-663` (`_refuse_over_unfinished_rollback`).

```
mode     latest record before                         result                 record  result files  commands reaching the mock  other state files  audit log  local lock  approval
dry-run  FAILED_HELD / rollback FAILED (the original) REFUSED ROLLBACK_INCOMPLETE  same  +0  +0  unchanged  +0 bytes  released  not consumed
dry-run  ROLLBACK_INTERRUPTED (automatic)             REFUSED ROLLBACK_INCOMPLETE  same  +0  +0  unchanged  +0 bytes  released  not consumed
dry-run  ROLLBACK_IN_PROGRESS (stale, no handler)     REFUSED ROLLBACK_INCOMPLETE  same  +0  +0  unchanged  +0 bytes  released  not consumed
dry-run  ROLLBACK_INTERRUPTED (owner-requested)       REFUSED ROLLBACK_INCOMPLETE  same  +0  +0  unchanged  +0 bytes  released  not consumed
execute  (the same four)                              identical in all four
```

In the random search 788 `run`/dry-run calls met an unfinished or failed rollback; all 788 were
refused with the record, the result files and the mock's command count unchanged, and the
local lock file was absent after every operation.

Not blocked: a first deploy with no record; a dry-run then execute; a re-run after
`FAILED_NO_CHANGE`; a re-run after an automatic `ROLLED_BACK`; after an owner-requested
`ROLLED_BACK`; after `recover` recorded `ROLLED_BACK` (`RECOVERED_VERIFIED_PREVIOUS`). Each
reached `DEPLOYED_AWAITING_ACCEPTANCE`.

## 4. New findings

### F-1. P1: a failed acceptance is not permanent; a new `run` drops the flag and the release can be accepted

`tools/release/deploy.py:637` (`run` starts a fresh `RunState()`), `:666-687` (`_record` writes
no `acceptance_failed`; nothing reads the previous record), `:1831` (`accept` looks only at the
latest record), `:1842` (comment "permanent for this release").
`docs/release/PIPELINE_ARCHITECTURE.md:302-303`: "A failed acceptance is permanent for a
release (`acceptance_failed`): `accept` refuses it afterwards whatever the state says."
`docs/release/TEST_EVIDENCE_AND_LIMITATIONS.md` section 4.4, N-1 row: "A failed acceptance is
recorded permanently and `accept` refuses it afterwards."

Observed, tool commands only, no interrupt and no hand change:

```
deploy                        -> DEPLOYED_AWAITING_ACCEPTANCE
accept --result fail          -> ACCEPTANCE_FAILED  acceptance_failed=True
owner rollback                -> ROLLED_BACK        acceptance_failed=True  sbr=ACCEPTANCE_FAILED
run --execute (new approval)  -> DEPLOYED_AWAITING_ACCEPTANCE  acceptance_failed absent  sbr=None  rollback=None
accept --result pass          -> ACCEPTED, known-good pointer moved
result files: DEPLOYED_AWAITING_ACCEPTANCE, ACCEPTANCE_FAILED, ROLLBACK_IN_PROGRESS, ROLLED_BACK, DEPLOYED_AWAITING_ACCEPTANCE, ACCEPTED
```

A second route, where a read-only command removes the flag from the latest record:

```
deploy -> accept fail -> ACCEPTANCE_FAILED acceptance_failed=True
run (dry-run)  -> FAILED_NO_CHANGE PREFLIGHT_FAILED "the host is not at the rollback target"; latest record has no acceptance_failed
   rollback: REFUSED ROLLBACK_NOT_APPLICABLE     accept pass: REFUSED ACCEPTANCE_NOT_PENDING
(host put back on the previous image by hand, the only way left)
run --execute  -> DEPLOYED_AWAITING_ACCEPTANCE -> accept pass -> ACCEPTED
```

The random search hit this 37 times in 4,200 sequences; the flag was absent from the record
written by a new `run` in 968 operations.

Why it matters: the brief for this fix requires that a release whose acceptance ever failed
can never reach `ACCEPTED`, and the architecture document now says so in those words. It does
not hold. What limits it: reusing the original deploy approval is refused (probe:
`FAILED_NO_CHANGE`), so every hit needed a new owner deploy approval, a complete new deployment
that passed its own verification, and then an owner `pass`; all steps stay in the numbered
result files. The mechanism (a new `run` does not look at earlier records) predates this
delta; the permanence claim is new in it. Either the flag has to survive a new `run` of the
same release, or the documents and the comment have to say that it lasts only until the
release is deployed again. Not decided here.

Not covered by any committed test: all four new N-1 tests stay within one deployment.

### F-2. P2: a second `run`, including a dry-run, still replaces other live records and leaves the tool with no rollback or acceptance for a host that is on the release

`tools/release/deploy.py:649-663` (the guard covers only `ROLLBACK_IN_PROGRESS`,
`ROLLBACK_INTERRUPTED` and a rollback block `IN_PROGRESS` / `INTERRUPTED` / `FAILED`),
`:1536` (`manual_rollback` refuses `FAILED_NO_CHANGE`). `PIPELINE_ARCHITECTURE.md:307-309`:
"so a later run cannot bury that record".

```
latest record before                                    then                 latest record after                       accept pass              rollback                    recover                 host
DEPLOYED_AWAITING_ACCEPTANCE                            dry-run or execute   FAILED_NO_CHANGE PREFLIGHT_FAILED         ACCEPTANCE_NOT_PENDING   ROLLBACK_NOT_APPLICABLE     n/a                     release image
ACCEPTANCE_FAILED                                       dry-run or execute   FAILED_NO_CHANGE (acceptance_failed gone)  ACCEPTANCE_NOT_PENDING   ROLLBACK_NOT_APPLICABLE     n/a                     release image
FAILED_HELD / RECOVERED_ON_RELEASE_NOT_ACCEPTABLE       dry-run or execute   FAILED_NO_CHANGE (stop code SMOKE_FAILED and the rollback block gone; 15 commands reached the mock, 1 new result file)  ACCEPTANCE_NOT_PENDING  ROLLBACK_NOT_APPLICABLE  RECOVERY_NOT_APPLICABLE  release image
```

The third row is the state `recover` leaves straight after the original N-3 scenario, and its
own `held_reason` tells the owner to choose "a new rollback attempt or a new release"; one
dry-run removes the first option. In the first row a dry-run of a release that is waiting for
acceptance makes both `accept` and `rollback` refuse. Nothing becomes acceptable (the outcome
is always refusal), the numbered result files keep the earlier records, and no host write is
issued; but the latest record reads "no change" for a host running the release, and the only
way forward is by hand. Rows 1 and 2 predate this delta (the earlier checker's N-3 named only
the unfinished-rollback record). By reading, not run: a `FAILED_HELD` record with no rollback
block (deployment stopped, no automatic rollback approved) is not covered by the guard either.

### F-3. P3: after the new N-2 check fails, the tool cannot finish that rollback by itself

`deploy.py:1471-1473` (only touched services are recreated), `:1414-1432`. In the N-2 scenario
the retry succeeded only after the frontend was recreated by hand on the restored pin (probe in
section 3). By reading, not run: a retry without that hand step would pin nothing, recreate
only the backend and fail on the same check again. The reason is in `rollback.failure.message`;
the top-level `held_reason` says only `ROLLBACK_FAILED`. The runbook's "Try the rollback again"
paragraph does not mention this case.

### F-4. P3: test gaps (mutation check, section 5)

No discriminating test for: the run refusal on a `FAILED_HELD` record whose rollback block is
`FAILED`, which is the state of the original N-3 report (M02; the committed test uses an
interrupted rollback); the episode-origin test inside `_may_return_to_acceptance` once the two
flags are present (M09); a previous image id that cannot be read in `_pins_restored` (M11); the
CLI change (M15; no test calls `cmd_recover`). My probes show the code is right in the first
case; the other three I checked by reading only.

### F-5. P3: wording left behind by this delta

- `PIPELINE_ARCHITECTURE.md:289` (diagram): "was the release awaiting acceptance when its FIRST
  rollback began?" The text below it and the code now say the current rollback episode, no
  stop code and never failed acceptance.
- `tools/release/deploy.py:616-618` (comment on `state_before_rollback`): still "when its
  FIRST rollback attempt began".
- `RELEASE_AUTOMATION_RUNBOOK.md:244-245` (not changed in this delta): "only possible for a
  release that was awaiting acceptance when its first rollback began".
- `deploy.py:1191-1193`: `SETTLED_BEFORE_ROLLBACK` is defined and used nowhere.
- The new stop code `ACCEPTANCE_ALREADY_FAILED` appears in no document.
- `TEST_EVIDENCE_AND_LIMITATIONS.md:202`: `@@CHECK5@@` placeholder present (expected).

## 5. What I checked and found sound

- **`_origin_for_new_attempt`.** Direct calls: awaiting with no rollback -> awaiting; awaiting
  after a recovered rollback -> awaiting; `ACCEPTANCE_FAILED` after a recovered rollback ->
  `ACCEPTANCE_FAILED`; `FAILED_HELD` with rollback `FAILED` and origin awaiting -> awaiting
  (same episode); `FAILED_HELD` / `RECOVERED_ON_RELEASE_NOT_ACCEPTABLE` -> `FAILED_HELD`;
  `FAILED_HELD` with no rollback -> `FAILED_HELD`; unfinished record with no stored origin
  (older record) -> its own state, never acceptable; stale `ROLLBACK_IN_PROGRESS` -> stored
  origin.
- **`acceptance_failed` through later records.** After a failed acceptance: a failed owner
  rollback, `recover`, an interrupted one, `recover`, one killed with no handler (stale
  in-progress record), `recover`, then a successful one. All 11 records written carried
  `acceptance_failed: true` and `state_before_rollback: ACCEPTANCE_FAILED`. `manual_rollback`
  carries every key of the previous record except five named ones (`deploy.py:1555-1559`),
  `_begin_rollback` and `_interrupted` spread `state.carried`, and `recover` copies the previous
  record. It is lost only by a new `run` (F-1).
- **`_refuse_over_unfinished_rollback`.** Runs under the local lock before `RunState()`; raises
  before any read or write of the host; the lock is released by the context manager; the
  approval is not consumed; identical in execute and dry-run (section 3, N-3).
- **Broadened `_pins_restored`.** Section 3, N-2. One extra read-only `container_states` call
  and one `image_id` read per service; no write.
- **CLI change** (`tools/release/cli.py:348-349`). By reading: `held_reason` is printed for
  every outcome (`None` when `recover` verified and moved it to `held_reason_before_recovery`),
  plus the original stop code; output goes through the existing redaction in `_emit`; exit
  codes unchanged (0 only for `ROLLED_BACK` or `DEPLOYED_AWAITING_ACCEPTANCE`). Not run.
- **Earlier behaviour, interruption matrix.** Backend+frontend rollback interrupted at every
  host command after the in-progress record, automatic and owner-requested, Ctrl-C and killed
  with no handler: 22 + 22 + 27 + 27 = 98 cases. A record was on disk at every interrupt
  point (`ROLLBACK_IN_PROGRESS` 50, `ROLLBACK_INTERRUPTED` 47, and 1 `FAILED_HELD` with
  `COMPLETED_VERIFIED`, the lock-release window already recorded in architecture 3.6). No
  result file said `ROLLED_BACK`; `accept` pass was refused in all 98
  (`ROLLBACK_INCOMPLETE` in 97); a second dry-run was refused in the 97 unfinished cases;
  the pointer never moved; `recover` issued 0 host writes, said `ROLLED_BACK` only with pins
  and images on the previous values (51), returned to awaiting only on the owner-requested
  path (6) and never for the failed deployment.
- **Dry-run.** 2,873 dry-runs in the guided random search issued 0 host writes. Plan-only was not re-probed (`run` rejects it; untouched by this delta).
- **Nothing removed.** The delta deletes no command, schema field or test.
- **Mutation check.** 16 mutants on lines this delta changed, scratch copy from
  `git archive 6bcf142`, `tests/release` with the one git-dependent test deselected (baseline
  311 passed, 1 skipped; restored and re-run afterwards, same result; the copy's two source
  files hash-equal to the commit after the run, ignoring line endings). **11 killed, 5
  survived.**

  | Mutant | Result | Killed by |
  |---|---|---|
  | M01 refusal call removed from `run` | killed | `test_a_new_run_never_replaces_...[EXECUTE]` |
  | M02 refusal ignores the rollback-block status | **survived** | (F-4) |
  | M03 refusal ignores the record state | **survived** | equivalent for records this code writes (an unfinished state always has such a block) |
  | M04 refusal for execute only | killed | `test_a_new_run_never_replaces_...[DRY_RUN]` |
  | M05 origin inherited across episodes (the `84706a9` behaviour) | killed | `test_a_failed_acceptance_is_permanent_across_rollback_episodes` |
  | M06 origin reset on every attempt | killed | `test_the_origin_state_survives_repeated_attempts` |
  | M07 `recover` ignores `acceptance_failed` | killed | `test_recover_does_not_return_a_release_marked_as_failed_acceptance_to_acceptance` |
  | M08 `recover` ignores `stop_code` | killed | `test_recover_does_not_return_a_release_with_a_recorded_stop_code_to_acceptance` |
  | M09 `recover` ignores the episode origin | **survived** | (F-4) |
  | M10 container image check removed | killed | `test_rollback_is_not_verified_while_a_never_applied_service_runs_the_release_image` |
  | M11 unreadable previous image id passes | **survived** | (F-4) |
  | M12 pin check removed | killed | `test_rollback_is_not_verified_while_any_release_pin_remains` |
  | M13 `ACCEPTANCE_ALREADY_FAILED` check removed | killed | `test_accept_refuses_a_release_that_already_failed_acceptance_whatever_its_state` |
  | M14 failed acceptance does not set the flag | killed | `test_a_failed_acceptance_is_permanent_across_rollback_episodes` |
  | M15 CLI change reverted | **survived** | (F-4) |
  | M16 refusal moved to after the run | killed | `test_frontend_health_failure_rolls_back_automatically` |

  Each test added for N-1, N-2 and N-3 fails when its own safeguard is removed.
- **Documents.**
  - `docs/release/N1_N2_FIX_CHECK_20261114.md` is byte-identical to
    `outputs/release-pipeline-20261114/N1_N2_FIX_CHECK.md` (sha256
    `3972ed3c632f0b31c3ede1f82ead159c89a2db3b2c4fb88c6fa971de3a1006f3`, working copy and
    committed blob).
  - `TEST_EVIDENCE_AND_LIMITATIONS.md` line 12: "312 passed, 1 skipped", "6 test files" and
    "208 test functions" all match (`grep -c "def test_"`: 32 + 41 + 25 + 35 + 51 + 24 = 208).
  - Section 4.4: the checked commit and tree, the verdict and the summary of the earlier check
    match that report; every test named exists and passes; the N-2 and N-3 rows match the
    code; the "P3 not changed" row is accurate. Not matching: the N-1 row's "recorded
    permanently" (F-1). The implementer's "10 mutants, 10 killed" is their own check; I did
    not repeat it as such.
  - `PIPELINE_ARCHITECTURE.md` 3.7: the episode-origin paragraph, the `run` refusal sentence
    (for the records it names), the persistent-write-failure wording and the `ROLLED_BACK`
    bullet (pin and image of every service) match the code. Not matching: "A failed
    acceptance is permanent for a release" (F-1); the diagram label (F-5).
  - `README.md`: the new row and the reworded review sentence are accurate.

## 6. What rests only on the mock

- Every result here. The mock's `up`, `stop`, `sed` and `cp` are atomic and instant; a real
  `docker compose up --wait` that is killed or times out can leave states the mock never shows.
- The new N-2 check compares `docker inspect` image ids with `docker image inspect` ids of the
  previous pin. On the mock these are the same string by construction. Whether the two real
  commands return comparable ids for a digest-pinned image on the host is unverified; if they
  did not, every real rollback would end `FAILED_HELD` (safe, but never `ROLLED_BACK`).
- The hand changes in the N-2 probe, in F-1's second route and in the random search are edits
  to the mock's state standing in for what an operator might do on the host.
- "Nothing was contacted" for the N-3 refusal means no command reached the mock runner and
  the audit log did not grow; there is no real SSH layer under it.
- No CLI-level run (`release.ps1`) was made; `deploy.*` functions were called as the tests call
  them, with `render.validate_release_config` stubbed. The `cli.py` change was read, not run.
