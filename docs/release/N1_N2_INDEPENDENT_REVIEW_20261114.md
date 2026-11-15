# Independent review: N1 and N2 remediation (rollback interruption)

Reviewer: fresh independent reviewer, no part in the implementation. Date: 2026-11-14.
Scope: the delta `git diff 7fa9146 37f3aa6` only, and what it touches. Mock host only. No host,
AWS, SSH, registry or network contact; no `.env` read; no tracked file edited; nothing committed.

## 1. Reviewed identity and exact command results

| Item | Value |
|---|---|
| Worktree / branch | `.claude/worktrees/release-pipeline-local-controller-bf1647`, `claude/release-pipeline-local-controller-bf1647` |
| Previously reviewed head | `7fa914637c452ada392739e818f06282afeb496e` |
| Candidate (`git rev-parse HEAD`) | `37f3aa6835c894d6efbe3fbff0a9bbf9a863008c` |
| Tree (`HEAD^{tree}`) | `7dcf54de74e1e8e7c402ad413cc9da435fdb791e` |
| `git status --short` | `?? outputs/` only (before and after the review) |
| `git diff --stat 7fa9146 37f3aa6` | 11 files, 1365 insertions, 63 deletions; 10 modified, 1 added (`tests/release/test_rollback_interruption.py`), none deleted |

Commands (venv Python, `CLM_RELEASE_STATE_DIR` pointing at a new empty temp directory outside the
repository, which stayed empty):

| Command | Result |
|---|---|
| `python -m pytest tests/release -q -p no:cacheprovider` | **283 passed, 1 skipped** in 18.91s (first run). **Not stable on this machine: see finding 2** |
| `python -m pytest tests/deploy -q -p no:cacheprovider` | 116 passed, 1 skipped in 9.72s |
| `python -m ruff check --select E,F,I,UP,B,SIM --line-length 100 --target-version py312 tools/release tests/release` | All checks passed |
| `python -m mypy --strict -p tools.release` | Success: no issues found in 19 source files |
| `python scripts/check_secrets.py` | Secret scan passed, exit 0 |
| `python -m tools.release --help` | 17 commands; the 16 earlier ones are all present, `recover` is added |
| Tests removed by the delta | 0 (`git diff ... -- tests` removes no `def test_` line); no file deleted |
| Test functions in `tests/release` | 184, as the evidence document states |

Repeat runs: `tests/release/test_rollback_interruption.py + test_deploy.py + test_review_findings.py`
run 25 times in a row from the worktree: **22 runs 155 passed, 3 runs 1 failed** (a different test
each time). Details in finding 2.

## 2. Verdict

**FAIL**

N1 and N2 themselves are fixed, and the new in-progress record, journal, `accept` refusal and
`recover` conditions behave as described under every interruption I could construct. The verdict
is FAIL because of one new P1 (finding 1): the new `recover` command opens a path to `ACCEPTED`
for a release whose deployment stopped on a stop condition (for example `SECOND_BACKEND` or
`VOLUME_IDENTITY_CHANGED`) or whose owner acceptance failed. That path did not exist at
`7fa9146`. It takes two deliberate owner-run steps (`recover`, then `accept`), and the fix is
small; the caller may weigh that, but by the stated rule a P1 is a FAIL.

## 3. N1 and N2

### N1 (interrupt or error during automatic rollback left no record): FIXED

Evidence in the code:

- `tools/release/deploy.py:1165-1203` `_begin_rollback` writes `ROLLBACK_IN_PROGRESS` through
  `_record` -> `StateStore.write_result` (`records.py:57-65`) -> `write_json` with `flush` +
  `os.fsync` (`core.py:484-491`) before `rollback()` is entered (`deploy.py:1133-1145`). If the
  write raises `OSError` the rollback does not start (`deploy.py:1195-1202`, `1136-1143`).
- `deploy.py:1206-1218` `_intent` journals each step (`records.py:67-84`, append + fsync, then
  the latest `result.json` is refreshed) before the command is issued.
- `deploy.py:633-640` and `674-693`: any `BaseException` during failure handling or rollback is
  recorded as `ROLLBACK_INTERRUPTED`, `rollback.status INTERRUPTED`, `host_state unknown`, then
  re-raised. Failure handling now runs inside the host-lock section (`deploy.py:781-789`).

Probe (my own, `FakeWorld` runner wrapped): `KeyboardInterrupt`, `RuntimeError` and a bare
`BaseException` subclass raised at every host command of an automatic rollback, both before the
mock applied the command and after it applied it, for frontend-only, backend-only,
backend+frontend and backend+frontend+assistant: 11 + 14 + 17 + 21 command positions x 3 errors
x 2 timings = 378 cases.

```
(('frontend',), 'auto')  11 commands  {ROLLBACK_INTERRUPTED/INTERRUPTED: 59, ROLLBACK_IN_PROGRESS/IN_PROGRESS: 1, FAILED_HELD/COMPLETED_VERIFIED: 6}
(('backend',), 'auto')   14 commands  {ROLLBACK_INTERRUPTED/INTERRUPTED: 78, FAILED_HELD/COMPLETED_VERIFIED: 6}
(('backend','frontend'), 'auto') 17   {ROLLBACK_INTERRUPTED/INTERRUPTED: 96, FAILED_HELD/COMPLETED_VERIFIED: 6}
(('backend','frontend','assistant'), 'auto') 21 {ROLLBACK_INTERRUPTED/INTERRUPTED: 118, FAILED_HELD/FAILED: 2, FAILED_HELD/COMPLETED_VERIFIED: 6}
```

In every case a record was on disk, `accept` was refused, no record had state `ROLLED_BACK`, the
local lock was released, and the host lock was released except when the interrupt landed on the
lock-release command itself. Whenever the mock showed the frontend stopped, the record had
`ingress_stopped` or `rollback.ingress_may_be_stopped` true. The odd rows are explained in
findings 2 (the two `FAILED`, the one `IN_PROGRESS`) and 6 (`FAILED_HELD/COMPLETED_VERIFIED`).

No-handler view (what a SIGKILL would leave): at each of the 174 host commands of a clean
automatic and manual rollback (four service sets) I read `result.json` from disk at the moment
the command reached the runner. At every mutating host write the on-disk state was
`ROLLBACK_IN_PROGRESS` and the last on-disk step was the one being issued, `STARTED`. The only
mismatch was the ingress flag on a frontend-only rollback (finding 4).

### N2 (interrupted owner-requested rollback left an acceptable record): FIXED

Evidence in the code:

- `deploy.py:1501-1509`: host lock, then `_begin_rollback(ctx, state, "manual")`, then the
  approval is consumed, then the first step. Nothing is stopped, replaced or re-pinned before the
  record; `_unpin`'s first `sed` is itself journalled first (`deploy.py:1333-1337`).
- `deploy.py:1523-1525`: an interrupt is recorded as `ROLLBACK_INTERRUPTED`.
- `deploy.py:1700-1710`: `accept` refuses with `ROLLBACK_INCOMPLETE` when the state is
  `ROLLBACK_IN_PROGRESS` / `ROLLBACK_INTERRUPTED` or the rollback block is `IN_PROGRESS`,
  `INTERRUPTED` or `FAILED`.

Probe: the same matrix on `manual_rollback` (20 + 23 + 30 + 38 command positions, 666 cases).

```
(('frontend',), 'manual') 20 {DEPLOYED_AWAITING_ACCEPTANCE/None: 42, ROLLBACK_INTERRUPTED/INTERRUPTED: 72, ROLLBACK_IN_PROGRESS/IN_PROGRESS: 6}
(('backend',), 'manual')  23 {DEPLOYED_AWAITING_ACCEPTANCE/None: 42, ROLLBACK_INTERRUPTED/INTERRUPTED: 90, ROLLBACK_IN_PROGRESS/IN_PROGRESS: 6}
(('backend','frontend'), 'manual') 30 {DEPLOYED_AWAITING_ACCEPTANCE/None: 48, ROLLBACK_INTERRUPTED/INTERRUPTED: 126, ROLLBACK_IN_PROGRESS/IN_PROGRESS: 6}
(('backend','frontend','assistant'), 'manual') 38 {DEPLOYED_AWAITING_ACCEPTANCE/None: 54, ROLLBACK_INTERRUPTED/INTERRUPTED: 167, FAILED_HELD/FAILED: 1, ROLLBACK_IN_PROGRESS/IN_PROGRESS: 6}
```

Every case that left `DEPLOYED_AWAITING_ACCEPTANCE` was an interrupt during the read-only
pre-checks or the host-lock `mkdir`; in all of them the mock host's `compose.env` and containers
were byte-for-byte what they were before the call, so the record was true and `accept` passing
is correct. In no case was the state acceptable after any service was stopped, replaced or
re-pinned. In no case did `accept` pass with a rollback block present. The known-good pointer
never moved.

Ordering checks on `manual_rollback`:

- Interrupt or `OSError` in `consume_approval` (between the record and the first step): record
  `ROLLBACK_IN_PROGRESS`, no step, host unchanged, `accept` refused, approval not consumed and
  usable for the next attempt (which ran as attempt 2 with history `['IN_PROGRESS']`).
- `_begin_rollback` cannot write: `ROLLBACK_NOT_RECORDED`, no host change, record stays
  `DEPLOYED_AWAITING_ACCEPTANCE` (true), approval not consumed, both locks released.

## 4. New findings

### 1. P1: `recover` can make a failed deployment, or a failed acceptance, acceptable

`tools/release/deploy.py:1562-1569` (applicability), `1626-1633` (release branch), `1689-1723`
(`accept`).

`recover` applies to any record with an unfinished rollback, whatever the release's state was
before the rollback began, and its "on the release" branch writes
`DEPLOYED_AWAITING_ACCEPTANCE` with `rollback.status RECOVERED_VERIFIED_ON_RELEASE`. `accept`
then passes. `recover` checks pins, image ids, health, public `/health` and the smoke requests.
It does not re-check what the deployment's own verification checks (`_apply_service`,
`_verify_stable`, `_others_unchanged`: exactly one backend container, data-volume identity,
proxy-network identity, other services unchanged, zero restarts), and it does not look at the
`stop_code` already in the record.

Observed on the mock (my probe; ingress started by hand between the two steps, as runbook
section 7 step 4 describes):

```
extra_backend            deploy -> FAILED_HELD SECOND_BACKEND          rollback FAILED
    recover: DEPLOYED_AWAITING_ACCEPTANCE / RECOVERED_VERIFIED_ON_RELEASE   accept: ACCEPTED  (host still has extra_backend = True)
restarts_after_up        deploy -> FAILED_HELD HEALTH_CHECK_FAILED     rollback FAILED
    recover: DEPLOYED_AWAITING_ACCEPTANCE / RECOVERED_VERIFIED_ON_RELEASE   accept: ACCEPTED  (restarts = 3)
volume_changes_after_up  deploy -> FAILED_HELD VOLUME_IDENTITY_CHANGED rollback FAILED
    recover: DEPLOYED_AWAITING_ACCEPTANCE / RECOVERED_VERIFIED_ON_RELEASE   accept: ACCEPTED
ACCEPTANCE_FAILED -> rollback interrupted at its first sed -> recover: DEPLOYED_AWAITING_ACCEPTANCE -> accept(pass): ACCEPTED, known-good moved
   result files: DEPLOYED_AWAITING_ACCEPTANCE, ACCEPTANCE_FAILED, ROLLBACK_IN_PROGRESS, ROLLBACK_INTERRUPTED, DEPLOYED_AWAITING_ACCEPTANCE, ACCEPTED
```

(In the first three the automatic rollback was made to fail at its first step, `restore_fails`.
An interrupt at that step, an expired approval, or the journal write failure of finding 2 gives
the same starting point.)

Why it matters: at `7fa9146` only a deployment that passed its full post-deploy verification
could ever be `DEPLOYED_AWAITING_ACCEPTANCE`, so only such a deployment could be accepted and
become known-good. The diagram in `PIPELINE_ARCHITECTURE.md` 3.7 still labels that state
"deployed and verified". After this change, a deployment that stopped on a listed stop
condition ("more than one backend container exists", "a data volume or the proxy network
changes identity") can reach `ACCEPTED` with the condition still present, and the tool tells
the owner "verified on this release's images; acceptance still needed" with exit code 0. The
runbook sends the operator of a `FAILED_HELD` + `rollback.status FAILED` record straight to
`recover` and says nothing about the original stop. This is a change to what can be accepted,
which requirement 8 excludes, and it weakens the single-backend-writer and volume-identity
stops. It needs an interactive `recover` and an interactive `accept`, both by a person; the
original `stop_code` stays in the record.

The narrowest repair I can see from the code: `recover` should return a release to
`DEPLOYED_AWAITING_ACCEPTANCE` only if that was its state when the first rollback attempt
began; from a failed deployment or `ACCEPTANCE_FAILED` the "on the release" outcome should be a
held state, not an acceptable one. (Not applied; I fix nothing.)

### 2. P2: a transient Windows "Access is denied" on the state file aborts a rollback mid-way, and makes the test suite unstable

`tools/release/core.py:491` (`temporary.replace(path)`), `tools/release/records.py:80-84`,
`tools/release/deploy.py:1213-1218`.

`write_json` replaces `result.json` by rename. On this Windows machine that rename
intermittently raises `PermissionError(13, 'Access is denied')` (most likely another process
holding the just-written file open; I did not identify which). The delta adds a `result.json`
rewrite before every rollback step and turns a failed write into `ROLLBACK_NOT_RECORDED`, which
ends the rollback as `FAILED_HELD`. There is no retry.

Observed:

- `write_json` to one file 4000 times in a loop: 8 failures, all `PermissionError(13)`.
- Interruption matrix: 5 of 1044 cases ended differently from the injected fault because of it,
  for example `failure={'code': 'ROLLBACK_NOT_RECORDED', 'message': "could not journal the step
  'recreate backend on its previous image'; it was not taken"}` (ingress and backend already
  stopped at that point).
- The committed tests: 3 of 25 consecutive runs failed one test each:
  `test_repeated_manual_rollback_after_an_interrupted_one` (`'FAILED_HELD' == 'ROLLED_BACK'`),
  `test_f1_automatic_rollback_of_backend_and_frontend_leaves_ingress_running` (same), and
  `test_recover_returns_an_untouched_release_...` (`PermissionError: [WinError 5] Access is
  denied: '...result.json.tmp' -> '...result.json'`). The 25 runs overlapped with my mutation
  run, so the rate under no load may be lower; the single-process loop above shows it is not
  zero. A scratch-copy baseline run also failed
  `test_accept_is_refused_after_an_interrupted_owner_requested_rollback[during-replacement]` once.

Why it matters: it fails safe (held, truthful, `accept` refused), but a rollback that would have
succeeded stops with the site down because of a local file-system hiccup on the controller, at
the moment the tool matters most. The state directory in real use is under `%LOCALAPPDATA%` on
the same kind of machine. It also means "283 passed" is not reproducible on every run here.
Injected deterministically (`journal` raising at step k of a backend+frontend automatic
rollback): steps 2 to 4 leave the frontend stopped, step 3 leaves the backend stopped too.

### 3. P2: an owner-requested rollback of a partly applied release ends `ROLLED_BACK` with `compose.env` still pinning an unapplied service to the release

`tools/release/deploy.py:1265-1267` (`_touched`), `1359` (`_unpin` on touched services only),
`1486-1496` (pre-check on touched services only), `1234` (`host_state
"verified-on-previous-images"`).

Probe: release of backend+frontend; the backend comes up unhealthy, so only the backend was
applied while both lines of `compose.env` were already pinned to the release. The automatic
rollback is interrupted at its first step (or fails there). The owner then runs `rollback`:

```
after: ROLLBACK_INTERRUPTED applied ['backend'] services ['backend','frontend'] pins {backend: NEW, frontend: NEW}
manual retry -> ROLLED_BACK COMPLETED_VERIFIED rolled services ['backend']
              pins now {backend: OLD, frontend: NEW}   containers {backend: OLD, frontend: OLD}
recover: RECOVERY_NOT_APPLICABLE
```

The record says `ROLLED_BACK`, `rollback.host_state: verified-on-previous-images`, and the
runbook now defines `ROLLED_BACK` as "the tool verified every service healthy on the previous
images". The containers are; `FRONTEND_IMAGE` in `compose.env` is not. Any later
`docker compose up` of the frontend would start the release image that was never applied, and
the next release's preflight would stop on `no-drift` or the rollback-target check. The
touched-only logic predates this delta (owner rollback from `FAILED_HELD` existed at
`7fa9146`); the delta adds the retry path that reaches it after an unfinished automatic
rollback and adds the stronger "verified" wording. The automatic path restores the whole file
and is not affected.

### 4. P2 (misleading claim): the ingress flag under-reports when the frontend itself is being replaced

`tools/release/deploy.py:1387` (`_intent(... f"recreate {name} ...")` without `ingress=True`),
`1156`, `1521`, `692`. `docs/release/PIPELINE_ARCHITECTURE.md` 3.7: "A step that may stop
ingress sets `ingress_may_be_stopped` before the command is sent. So the record never
under-reports by a step." Section 3.6 and the runbook tell the operator that `ingress_stopped`
/ `rollback.ingress_may_be_stopped` says whether the site may be down.

In a frontend-only rollback the frontend, which is the ingress, is recreated with
`ingress_may_be_stopped: false` on disk at the moment the `up` is issued (no-handler probe, both
paths), and a failed frontend recreate is recorded with `ingress_stopped: False`:

```
frontend-only, up fails during automatic rollback:
  FAILED_HELD  rollback FAILED  ingress_stopped False  ingress_may_be_stopped False
```

The mock's `up` is atomic, so the mock never shows a stopped frontend here; on a real host a
killed or failed `up --wait` of the ingress container can leave the site down. The state and
`host_state` are still correct (`unverified` / `unknown`); only the flag and the sentence in the
document are wrong for this case. The same is true of the frontend recreate at the end of a
backend rollback only in theory: there the flag is already true.

### 5. P3: `recover` leaves stale failure text in a verified record

`deploy.py:1615` (`outcome = dict(previous)`), `1625`, `1633`. After `recover` writes
`ROLLED_BACK` the record still has `held_reason: "recovery could not verify the host ... the
host state is UNKNOWN. Nothing here says the previous service was restored ..."` and
`interrupted_by`. The same fields ride into `DEPLOYED_AWAITING_ACCEPTANCE` and `ACCEPTED`. The
CLI hides `held_reason` unless the state is `ROLLBACK_INTERRUPTED`, but `status` and the files
show a state and a reason that contradict each other.

### 6. P3: three catchable interrupt windows do not end as `ROLLBACK_INTERRUPTED`

All conservative (never acceptable, never "rolled back"), but section 3.6 says a rollback
interrupted "by anything Python can catch" is `ROLLBACK_INTERRUPTED`:

- `deploy.py:1506-1508`: an interrupt or `OSError` in `consume_approval` is outside the inner
  `try`; the record stays `ROLLBACK_IN_PROGRESS` with no `interrupted_by`.
- `deploy.py:1529-1534`: an interrupt on the lock-release command after a finished manual
  rollback leaves `ROLLBACK_IN_PROGRESS` (host lock held); `recover` then gives `ROLLED_BACK`.
- `deploy.py:784-789` with `674-709`: the same instant in an automatic run gives `FAILED_HELD`
  with `rollback.status COMPLETED_VERIFIED` and the event "rollback verified", plus "the host
  state is not verified". `recover` is `RECOVERY_NOT_APPLICABLE` for that record, so the way out
  is another approved rollback or by hand.
- When the interrupted record itself cannot be written (seen once, finding 2) the original
  exception is replaced by the `PermissionError` and the record stays `ROLLBACK_IN_PROGRESS`.

### 7. P3: the host lock is leaked if the interrupt lands just after `mkdir` succeeded

`deploy.py:1501-1504` (and `764-767`, older): the lock is taken before the `try/finally` that
releases it. Probe: interrupt after the mock applied `mkdir`: host lock held, record unchanged
and true. The runbook's stale-host-lock step covers it.

### 8. P3: when the approval has already expired as an automatic rollback begins, `compose.env` is still restored and then the rollback stops

`deploy.py:1252` (only a stop whose own code is `APPROVAL_EXPIRED` blocks), `1302-1306`
(`_restore_env` is housekeeping, exempt from the deadline), `1361`. Probe: smoke fails, the
window ends, rollback starts: step 1 `restore compose.env` `DONE` after expiry, step 2 refused
with `APPROVAL_EXPIRED`; `compose.env` on the previous pin, container on the release image,
record `FAILED_HELD` / `FAILED` with both steps shown. The exemption predates this delta and the
record is truthful; the pin/container disagreement is what the operator inherits. No other
rollback write is exempt: the manual re-pin, stops, recreates and ingress start all stopped on
expiry in my probes, each recorded `FAILED_HELD` / `FAILED` / `APPROVAL_EXPIRED` with the refused
step left `STARTED`.

### 9. P3: `recover` and `manual_rollback` read the previous record before taking the local lock; `recover` does not look at the host lock

`deploy.py:1562` vs `1573`, `1443` vs `1480`. Only matters if two operator commands overlap.
`recover` with a stale local lock is refused (`RELEASE_IN_PROGRESS`); with a stale host lock it
runs.

### 10. P3: wording

Runbook section 7 step 3: "Exit code 2 ... the record stays `ROLLBACK_INTERRUPTED`". From
`FAILED_HELD` + `rollback.status FAILED` the state changes to `ROLLBACK_INTERRUPTED` while
`rollback.status` stays `FAILED` (probe: `('ROLLBACK_INTERRUPTED', 'FAILED', 'unknown')`).

### 11. P3: test gaps (targeted mutation check)

34 mutants on the new code in a scratch copy (`git archive 37f3aa6`), `tests/release` with one
git-dependent test deselected, each failure confirmed by a second run because of finding 2:
**19 killed, 15 survived.**

Survived and equivalent or not testable on a mock (6): accept's state test when the block test
is kept (M06), the per-container "serving" test in `recover` (covered by the all-healthy test,
M14), `_unpin`'s retry guard (the pre-check guards the same thing, M17), `fsync` in `journal`
and `write_json` (M20, M30), `recover` run through the CLI in execute mode (M26, it issues no
write anyway).

Survived and real gaps (9):

| Mutant | Safeguard with no discriminating test |
|---|---|
| M07 | approval consumed before the in-progress record (ordering) |
| M10 | `recover` -> `ROLLED_BACK` without checking the other containers |
| M11 | `recover` -> `ROLLED_BACK` without the public health check |
| M13 | `recover` comparing only the `compose.env` pin, not the container's image |
| M21 | a stop raised while handling a stop marks the rollback block `FAILED` |
| M22 | `recover` applicable to a `FAILED` rollback |
| M24 | retry allowed from a stale `ROLLBACK_IN_PROGRESS` |
| M25 | `recover` "unknown" sets the state to `ROLLBACK_INTERRUPTED` |
| M33 | `ingress_stopped` on a failed owner-requested rollback |

My probes show the code is right for M10, M11, M13, M22, M24 and M25; the tests would not
notice if it stopped being right. `test_recover_verifies_a_rollback_that_finished_...` is a
positive test only. The evidence document's "16 of 16 killed ... both `recover` conditions" is
the implementer's own check and I could not reproduce it for the previous-images branch.
All killed mutants: in-progress record, journalling, early ingress flag, interrupt recording on
both paths, `accept` on a `FAILED` block, smoke in `recover`, interactive-only `recover`,
first-attempt host-moved-on refusal, journal refresh of `result.json`, lock scope, execute-only
rollback, both final verifications, `STARTED` before issue.

## 5. Checked and found sound

- Requirement 1: the in-progress record and each step are on disk before the command reaches the
  runner (174 commands inspected from disk). `journal` appends and fsyncs the line, then rewrites
  `result.json` through the fsynced `write_json`.
- Requirement 2: no interrupted, failed or unverifiable rollback produced `ROLLED_BACK`,
  `COMPLETED_VERIFIED` or "rollback verified" except the lock-release instant in finding 6, where
  the rollback really had completed. `rollback()` returns only after all containers are healthy
  and `/health` is 200.
- Requirement 3: `accept` passes only from `DEPLOYED_AWAITING_ACCEPTANCE` with no rollback block
  or a `RECOVERED_VERIFIED_ON_RELEASE` block. It never passed after an interrupted, failed or
  unknown rollback, nor after `recover` returned unknown, nor from `ROLLED_BACK`. The record
  cannot return to `DEPLOYED_AWAITING_ACCEPTANCE` except through `recover` (subject to finding 1).
- `recover`: issued 0 host writes in every probe; refused when non-interactive
  (`RECOVERY_NEEDS_OWNER`, checked before any read; the CLI needs both stdin and stdout to be a
  terminal); `RECOVERY_NOT_APPLICABLE` on `DEPLOYED_AWAITING_ACCEPTANCE`, `ACCEPTANCE_FAILED`,
  and an already recovered `ROLLED_BACK`. It returned unknown for: containers stopped; only
  `compose.env` on the previous pins with containers on the release images; backend previous
  with frontend on the release; Mongo down; the assistant (not in the release) unhealthy;
  `/health` 503; `host_reads=False`; smoke failing on the release. It returned `ROLLED_BACK`
  only with every service of the release on its previous pin and image, everything healthy and
  `/health` 200. Each attempt is appended to `recovery_attempts` and gets its own numbered file.
- Requirement 5: `manifest_sha256`, `previous_known_good`, `pins_before`, `references`,
  `env_backup`, the deploy `approval_id`, the rollback block (services, from/target images,
  approval id, steps) and `rollback_history` survive interruption, failure, retry and recovery.
  Numbered result files are never overwritten; `rollback-journal.jsonl` only grows (7 then 12
  lines across two attempts).
- Requirement 6: a second call with the same rollback approval is `APPROVAL_ALREADY_USED` with no
  host write; a retry with a new approval after a failed automatic or interrupted manual
  rollback completes as attempt 2 with the earlier attempt in `rollback_history`; a retry after a
  rollback that had in fact finished repeats the stops and recreates and does not re-issue the
  `sed`; a first attempt on a host that moved on, and a retry on a host that is on neither pin,
  are `HOST_STATE_UNEXPECTED` with 0 host writes, the record unchanged and the approval not
  consumed; rollback from `ROLLED_BACK` is `ROLLBACK_NOT_APPLICABLE`.
- Requirement 8: no command, schema field or test removed; `accept`, `deploy`, `rollback`
  signatures unchanged apart from the keyword-only `retry` and `need_consent`. No `down`, `-v`,
  `--remove-orphans`, volume removal, Mongo target or second backend in the new code; the
  rollback issues only `sed` on one line, `stop`, `up -d --no-build --no-deps --wait <service>`
  and `start`. No credential in the journal or records (the existing sentinel test covers the
  new files).
- Regressions: deploy happy paths, dry-run purity, `FAILED_NO_CHANGE` paths and the F1/F2/F8
  tests pass. Moving stop handling inside the host-lock section changes neither which stops are
  handled (pre-lock stops still reach `run()`'s handler) nor the dry-run result; both locks were
  released in every case except an interrupt on the release command itself.
- Documents: the SIGKILL / power-loss / machine-failure limits are stated in architecture 3.7,
  limitation 4b, the runbook and evidence section "0."; the stale in-progress procedure exists
  and its order (unlock before `recover`) matches the code; `/tmp/.clm_r3_check` matches
  `deploy/egress/host/verify_host_firewall.sh:86-88`; "every exit path Python can catch" is now
  qualified (remaining exceptions in finding 6). The state diagram matches the code, including
  the `recover` branch that finding 1 objects to.

## 6. What rests only on the mock or cannot be assessed without a real host

- Everything about host behaviour: `compose stop/up/start` semantics, a half-finished
  `up --wait`, what a killed SSH session leaves running, real image ids and health states.
  `FakeWorld` applies each command atomically.
- Durability: that `flush` + `fsync` + rename survives a real power loss on NTFS was not tested
  (no kill was performed; the directory entry is not synced). Removing either `fsync` is not
  detected by any test.
- A real SIGKILL was not sent. The no-handler claim rests on reading the files from disk at each
  command, and on the test that makes the handler die.
- Finding 4's consequence (site down with the flag false) is argued from the code and from what
  `compose up` does on a real host; the mock cannot show it.
- Finding 2's rate is specific to this machine and to load; the mechanism is real.
- `recover` through the real CLI (`_context`, operator configuration, SSH reads) was not run;
  only `deploy.recover` against the mock.
- The implementer's "16 of 16 mutants killed" was not reproduced.
