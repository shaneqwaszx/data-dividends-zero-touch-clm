# Independent review: Actions-independent release toolchain

Reviewer: independent session (did not write the code). Date: 2026-11-14.
Nothing was fixed, committed, pushed or contacted. No host, AWS, SSH, GHCR or registry call
was made; no `.env` file was read; no image was built.

## 1. Reviewed identity and what was run

| Item | Value |
|---|---|
| Worktree branch | `claude/release-pipeline-local-controller-bf1647` |
| Commit | `728cf1ecda53ec81849329475cfc0ae3c72fdda7` (confirmed) |
| Tree | `c77a707565d45ccf00f3a0e071f43f287b34f4fb` (confirmed) |
| Base | `d0142d8e8d74ea8002a72ec63bad8bbaf0f59410` = `origin/main` = `HEAD~1` (confirmed) |
| `git status --short` | clean before and after the review (the report folder is the only new path) |
| `git diff --name-status d0142d8 HEAD` | 39 files, all `A` (added); 11,286 insertions, 0 deletions. Only `tools/__init__.py`, `tools/release.ps1`, `tools/release/**`, `tests/release/**`, `docs/release/**`. No existing file modified |
| Tracked secret-like files in the diff | none (`.env`, `.pem`, `.key`, `.crt` patterns: no match in the diff; the two pre-existing `.env.example` files are not part of it) |

Commands (Python 3.12 from the project `.venv`, Git Bash, `CLM_RELEASE_STATE_DIR` set to a
scratch directory outside the repository):

| Command | Result |
|---|---|
| `python -m pytest tests/release -q -p no:cacheprovider` | **179 passed, 1 skipped** (10.5 s) |
| `python -m ruff check --select E,F,I,UP,B,SIM --line-length 100 --target-version py312 tools/release tests/release` | **All checks passed** |
| `python -m mypy --strict -p tools.release` | **Success: no issues found in 19 source files** |
| `python scripts/check_secrets.py` | **Secret scan passed** (exit 0) |
| `python -m pytest tests/deploy -q -p no:cacheprovider` (Git Bash) | **116 passed, 1 skipped** |
| `python -m tools.release baseline` | `{"baseline_matches_compose_files": true}`, exit 0 (a fresh offline render equals the tracked baseline) |
| `python -m tools.release plan --manifest docs/release/samples/release-manifest.d0142d8.sample.json` | exit 0; manifest hash `9d3fe8f5...c5ce`, HIGH, deploy order backend, assistant, frontend; must-not-change `mongo`; 15 host steps |
| `deploy ... --approval <sample> --dry-run --offline` | exit 2, `APPROVAL_EXPIRED` (the sample approval is refused, as documented) |
| `deploy ... --execute --offline` (no operator config) | exit 3, `OPERATOR_CONFIG_MISSING` |

Note on the state directory: the first `baseline`/`plan` run used a scratch folder that
already held files from the authoring session (the scratch area is shared). I repeated both
with a newly created empty directory; the results were identical and are the ones above.

Probes (throwaway scripts outside the repository, importing `tools.release` and
`tests/release/fakes.py`): rollback and expiry paths, offline/dry-run effects, 39 deny-list
variants, effective-summary acceptance and blind spots, a 6,619-mutant differential between
the built-in validator and `jsonschema`, approval binding, crash handling, secret leakage, and
a 48-mutant mutation run of `tests/release` in a scratch mirror exported with `git archive`.

## 2. Verdict

**FAIL**

Three P1 findings: two failure-handling paths do not do what the documents state (one leaves
the site down while reporting `ROLLED_BACK`; one leaves `compose.env` pinned to the new image
with no result record), and one stated configuration invariant does not hold. No P0: I found
no path that leaks a credential, no host or registry write in plan-only or dry-run, no way to
run with a wrong, expired or reused approval for a deployment, and no path that rolls a
backend or assistant back without the manifest declaring compatibility.

Counts: P0 = 0, P1 = 3, P2 = 7, P3 = 9.

## 3. Findings

### F1 (P1) Rollback of a release that changes both backend and frontend ends with ingress stopped, and is reported as `ROLLED_BACK`

`tools/release/deploy.py:1101-1136` (`rollback`), specifically 1108-1118 and 1131-1135.

`ROLLBACK_ORDER` is frontend, assistant, backend. The frontend is recreated first (running).
The backend step then runs `compose stop frontend` (1115-1117), stops and recreates the
backend. The only restart of ingress is guarded by
`if "backend" in touched and "frontend" not in touched` (1131). When the frontend is also in
`touched` nothing starts it again, `state.ingress_stopped` is set to `False` (1135),
`_others_unchanged` exempts the frontend, and no final health or smoke check runs.

Probe (fake host, backend + frontend, both `automatic: true`, approval with auto rollback,
smoke fails after both are applied):

```text
state: ROLLED_BACK SMOKE_FAILED None ingress_stopped= None
   frontend frontend-c3 running= False
   backend backend-c4 running= True
events tail: [... 'frontend: rolled back to the previous image and healthy',
              'backend: rolled back to the previous image and healthy']
```

The same happens through `manual_rollback` for a deployed backend + frontend release
(`rollback: ROLLED_BACK`, `frontend ... running= False`).

Why it matters: `PIPELINE_ARCHITECTURE.md` 3.6 says `ROLLED_BACK` means "services recreated on
their previous image, frontend first; verified", and the checklist says "The previous image is
serving". Here the public site is down and the record says the opposite. The tracked sample
manifest is exactly this shape (backend, assistant, frontend). No test covers a rollback that
touches both services (`test_backend_with_proven_compatibility...` is backend-only). Also in
the same function: the return codes of the two `compose stop` calls (1115-1118) are ignored.

### F2 (P1) Approval expiry between the `compose.env` pin and the first container change escapes as an unhandled exception: `compose.env` is left on the new image, no result record is written

`tools/release/deploy.py:991-1014` (`_stopped`), `1093-1098` (`_restore_env`),
`tools/release/core.py:396-398` (deadline check), `deploy.py:613-641` (`run`).

`_restore_env` is an ordinary `host.write`, not `housekeeping`. When the stop being handled is
`APPROVAL_EXPIRED` and no container has changed yet, `_stopped` calls `_restore_env`, the gate
calls the deadline again, and a second `StopCondition` is raised from inside `_stopped`.
`run()` only wraps `_run_locked`, so the exception leaves `run()` before
`store.write_result`.

Probe (frontend-only, clock advanced past expiry when the `sed` pin is issued):

```text
UNCAUGHT: StopCondition APPROVAL_EXPIRED: the approval window ended during execution; ...
  FRONTEND_IMAGE still old pin: False | recreated: []
  result record: None
  host lock held: False | local lock: False | consumed: ['apr-93f62ae5e401-...:deploy']
```

Why it matters: the documents state "Approval expired during the run: `FAILED_HELD`" and
"`compose.env` edit or host config validation: `compose.env` restored from its backup". In
this window neither holds. The host is left with `compose.env` naming the new image while the
old container runs, so any later `dc up` by hand would move the service onto an image whose
approval has expired; nothing is recorded (requirement 13); the CLI exits 3, which the runbook
and checklist describe as "refused before starting ... nothing was contacted". The existing
expiry test advances the clock after the first `up`, so it never reaches this window. The
window is short (a few SSH round trips after the pin), but a slow image transfer is exactly
what uses up an approval window.

### F3 (P1) The "no Docker socket" invariant does not hold: bind-mount sources are dropped from the summary

`tools/release/effective_summary.py:63-67`, `tools/release/render.py:173-176`.

For a bind mount the summary keeps only `bind::<target>:<mode>`; the source path is
discarded. The invariant then tests `"docker.sock" in v`, which can only ever match the
target path.

Probe:

```text
INVISIBLE docker.sock bound read-only at an existing target      (summary identical)
INVISIBLE bind SOURCE changed (/etc/clm/ca.pem -> /etc/shadow)   (summary identical)
ACCEPTED  docker.sock ro bind at /tmp/x on backend, 'volumes' declared
refused   docker.sock bind at /var/run/docker.sock, 'volumes' declared
```

So a Compose change that mounts `/var/run/docker.sock` onto any existing bind target is not
seen at all (no declaration needed, the baseline test does not fail), and at a new target it
passes once `volumes` is declared. `PIPELINE_ARCHITECTURE.md` 3.4 lists "Docker socket" among
the invariants "no manifest can relax". Mitigation that exists: such a change would still have
to be in a reviewed Compose file whose hash is in the manifest. The stated automatic safeguard
itself does not work.

### F4 (P2) The effective-configuration summary is too coarse for the claims made about it

`tools/release/effective_summary.py:29-96`, `render.py:140-243`, `deploy.py:843-867`.

Shown by comparing `summarise()` of two documents (identical summary = invisible): environment
**values** (other than 14 listed switches), bind sources, `extra_hosts` addresses (only names
are kept, so a changed pinned destination is invisible), `command`, `entrypoint`,
`healthcheck`, `tmpfs`, `secrets`, `labels`, `mem_limit`, `volumes_from`, network aliases and
`group_add` are all invisible. Consequences:

- "A test fails when the Compose files and the baseline disagree, so a Compose change forces a
  reviewed baseline update" is true only for the summarised fields.
- "capabilities dropped ... no manifest can relax": `cap_add: [ALL]` next to `cap_drop: [ALL]`
  is accepted once `cap_add` is declared; `security_opt: [seccomp=unconfined]` likewise.
  (`ACCEPTED backend cap_add ALL (cap_drop ALL kept), declared`.)
- On the host (`_validate_on_host`) only networks and ports of the changed service are
  compared with the baseline; environment names are not compared there (they are offline).

The literal requirement (refuse a service gaining a network, port or variable the plan did not
declare) is met offline: an undeclared network, port, variable name, volume change, lost
`read_only`, non-external data volume and non-internal network were all refused in the probe.
The documents should say what the summary does not cover, or the summary should cover it.

### F5 (P2) The schema-19 rule and "proven" backend compatibility rest on optional, self-declared, unnormalised manifest fields

`tools/release/manifest.py:204-236`, schema `rollback.target_source_commit` (optional,
`string|null`, no pattern).

Probe:

```text
refused   commit 4c1db49..., data_compatible true, schemas 20/20: ROLLBACK_SCHEMA_INCOMPATIBLE
ACCEPTED  no target commit, target schema 20 claimed, compatible true; auto-eligible=True
ACCEPTED  commit 4C1DB49 upper-case, schema 20 claimed; auto-eligible=True
ACCEPTED  commit ' 4c1db49' leading space, schema 20 claimed; auto-eligible=True
```

The tool cannot tell what a rollback image actually writes: it trusts the commit string, the
two schema integers and `target_confirmed_on_host`, all typed by a person into the request.
Omitting the commit, or writing it in another case, bypasses the only schema-19 check. Nothing
ties `target_image` (a digest) to the declared commit, and no known schema-19 image digest is
denied. The words "proves"/"proved" in the runbook and architecture document mean "declared in
the manifest and approved by the owner"; they should say so. At minimum the commit should be
required and pattern-checked for a backend entry with `data_compatible: true`.

### F6 (P2) Owner-requested rollback restores the whole `compose.env` from the release's backup and does not check what the host is running now

`tools/release/deploy.py:1139-1175`, `1093-1098`.

`manual_rollback` rebuilds its state from the local result file and copies the pre-release
backup over `compose.env`. It does not verify that the host is still at the release's pins,
does not take the host lock, ignores the return values of `_volumes` and `_boundaries`, and
treats every service of the release as applied.

Probe (frontend release deployed, then two later edits to `compose.env`, then rollback):

```text
rollback: ROLLED_BACK None
ASSISTANT_IMAGE reverted to pre-release value: True | later key still present: False
```

Any change made to `compose.env` after the release (another release's pin, a new RD-1 value)
is silently reverted in the file while those containers keep running, and the record says
`ROLLED_BACK`. The automatic path, which runs inside the same host lock straight after the
backup, does not have this problem.

### F7 (P2) Approval semantics for an owner-requested rollback are not what the runbook says

`tools/release/deploy.py:1149-1164`, `1061-1062`; runbook section 6.

- `manual_rollback` checks the approval for action `deploy` and passes no `consumed` set, so
  the already-used deploy approval is accepted for a rollback for the rest of its window
  (probe: deploy consumed `apr-...:deploy`, then `manual_rollback` with the same record
  returned `ROLLED_BACK`). There is no `rollback` action and the rollback never consumes
  anything.
- It is refused unless the record has `auto_rollback: true`
  (`ROLLBACK_REFUSED: the owner did not approve automatic rollback`), which the runbook does
  not state. An owner who follows the runbook's own `approve` example without
  `--auto-rollback` cannot roll back with the tool and must create a new **deploy** approval.
- A "new" approval made for a rollback is an unconsumed deploy approval for the same manifest.

Expiry itself is enforced on this path (deadline set at 1154). This is a design gap in a
moment of pressure, not a bypass of expiry.

### F8 (P2) An interrupted run after the approval is consumed leaves no record and cannot be resumed or rolled back by the tool

`tools/release/deploy.py:613-641`, `679-698`.

Only `StopCondition` is handled. Ctrl-C, a killed process, or any other exception after the
pin (including a non-stop `ReleaseError`) releases the host lock but writes no result, runs no
`_stopped` handling and leaves `compose.env` changed.

Probe (interrupt during the first `up`):

```text
result record: None | consumed: ['apr-...:deploy']
FRONTEND_IMAGE is new pin: True | recreated: []
manual rollback refused: ROLLBACK_NOT_APPLICABLE: this release is not in a deployed state
rerun with same approval: FAILED_NO_CHANGE APPROVAL_ALREADY_USED
rerun with a NEW approval: FAILED_NO_CHANGE PREFLIGHT_FAILED no-drift: frontend differs ...
```

The outcome is fail-closed (nothing further runs), which is right, but recovery is entirely
by hand and the runbook's "After a stop" section covers only a stale local lock. There is no
journal written before the first host change, and no documented procedure for a stale host
lock (`/run/lock/clm-release.lock`) either.

### F9 (P2) The toolchain assumes a host secret file `/etc/clm/mongo.uri` that no existing authority describes, and the host profile is not configurable

`tools/release/catalog.py:154`, `host.py:149-153`, `cli.py:78-80`.

Every Compose command starts with `MONGO_URI="$(sudo -n cat /etc/clm/mongo.uri)"`.
`deploy/LIGHTSAIL_RUNTIME.md` says only "Inject `MONGO_URI` into the operator process from the
approved secret source"; the path appears nowhere in the repository outside the new code
(`git grep` finds no other use). The operator configuration supplies only the SSH target and
`backup_dir`; `workdir`, `compose_env`, `mongo_uri_file`, the site URL and the thresholds are
constants. If the host keeps the connection setting elsewhere the tool fails closed, but the
obvious workaround is to create a new at-rest copy of the database credential on the host,
which is a security decision nobody has taken. Checklist step A5 asks the operator to confirm
the paths; it should be an explicit owner decision recorded before first use. Unverified: I
could not check whether the file exists on the host.

### F10 (P2) Several named safeguards have no test that fails when they are removed, and whole paths are untested

Mutation run in a scratch mirror (each mutant removes one safeguard; "survived" means all of
`tests/release` still pass). 35 of 48 were killed; 13 survived:

| Mutant | Safeguard removed |
|---|---|
| M29 | verification that `compose.env` differs from its backup by exactly one line per service (`deploy.py:804-808`) |
| M33 | on-host check for an undeclared network or port (`deploy.py:862-865`); the test named `test_host_render_with_an_undeclared_network_is_refused` passes through the network ceiling instead |
| M38 | verification that a rolled-back service runs its previous image and is healthy (`deploy.py:1128`) |
| M28 | proxy-network identity comparison |
| M48 | "proxy network is internal" preflight check |
| M34 | refusal of a floating current pin |
| M42 | result of the firewall verify scripts (no deploy test runs with the GoldTier or provider overlay active) |
| M44 | restart-count check after apply |
| M39, M47 | clock-drift and Compose-version preflight checks |
| M23 | `StrictHostKeyChecking=yes` on the SSH command |
| M06, M25 | per-apply and post-deploy "others unchanged" (each is covered only by the other) |

Untested behaviours: rollback touching two or more services (F1), expiry between pin and
first container change (F2), `manual_rollback` for a backend, any run with `goldtier` or
`assistant-provider` active, `--transfer load` through `deploy.run`, a crash mid-run.

Fidelity of `tests/release/fakes.py`: the fake matches remote commands by substring and
returns canned text. It never executes a shell, so quoting, `sudo` behaviour, `sed`, `diff`,
`pgrep`, `ss` and the real output formats are not exercised; `config --hash` and the container
label are the same invented function; `up` ignores its flags; the pull script is recognised by
one marker string and its body never runs. The following claims therefore rest only on the
mock: sole-operator detection, drift detection by config hash, the one-line `compose.env`
edit, image identity after pull on the containerd store, "exactly one backend", the pull
script leaving no auth directory, and every preflight parser. The documents do say the tool
has only run against mocks; "`tests/release` proves this" (credential guide section 2) and
"Proven on this host: Yes" for the pull path (section 7, which refers to the earlier manual
procedure, not to this script) are stronger than that evidence.

### P3 notes

- **F11 Deny-list is a weak backstop** (`core.py:285-299`). Passed in the probe:
  `docker compose "down"`, `'down'`, `do''wn`, `--remove-orph''ans`, `up -dV`,
  `--renew-anon-volumes`, `up --force-recreate mongo`, `up -d backend` (no `--no-deps`),
  `stop mongo`, `exec`, `docker container rm -f`, `docker stop`, `docker network rm`,
  `docker image rm`, `docker exec`. No injection path into a remote command was found, so this
  is defence in depth only; the architecture document's "`docker rm`" is narrower than it
  reads. It blocks none of the tool's own commands (full execute run of three services passed).
- **F12 `--offline` is accepted together with `--execute`** (`cli.py:64`, 490). Host reads are
  then skipped while host writes stay allowed. It fails closed today only because two checks
  (`volumes`, `images-and-rollback`) return FAIL on a skipped read in execute mode
  (probe: `PREFLIGHT_FAILED volumes: MONGO_DATA_VOLUME unset`, 0 writes). Preflight treats
  `SKIPPED` as non-blocking in every mode; execute should refuse any skipped check outright.
- **F13 `manifest --skip-checks` leaves no trace** (`controller.py:107-112`, 176-182). The
  manifest's `checks` then holds only `effective-compose-config: PASS`; no `NOT_RUN` entries.
  `require_publishable` blocks only on `FAIL`, so a manifest with no check executed is
  publishable if the request declares a passing QG verdict. Not reported as a pass, but not
  visibly "not run" either.
- **F14 Missing document.** `TEST_EVIDENCE_AND_LIMITATIONS.md` is referenced by
  `README.md:16` and twice by `PIPELINE_HOW_TO_USE_AND_MAINTAIN.md` ("what was run, the counts,
  the independent review") but is not in the commit.
- **F15 Exit code 3** is documented as "refused before starting / nothing was contacted". Any
  `StopCondition` that escapes `run()` (F2) and `manual_rollback` refusals also exit 3 after
  host contact.
- **F16 Host pull script has no `trap`** (`registry.py:189-203`). If the remote shell is
  killed between login and cleanup, `/run/clm-ghcr.*/config.json` (the read-only token,
  root-only, memory-backed) stays until reboot, and every later pull then fails on
  `auth_dirs_left`. Login failure and pull failure paths do clean up (by reading the script;
  not executable here). A client-side SSH timeout (600 s for a pull, wait-timeout + 120 s for
  `up`) is reported as a failure while the remote command keeps running.
- **F17 Archive transfer path uses a quoted `~`** (`catalog.py:165`, `registry.py:236-259`):
  `shlex.quote("~/clm-release/...")` gives `'~/clm-release/...'`, so a directory literally
  named `~` is created in the operator's home. Consistent, so it works, but it is not the
  intended path.
- **F18 `ssh_destination`** (`host.py:40`) may start with `-` (for example `-Fpath`), which
  `ssh` would read as an option because it precedes `--`. The file is operator-owned, so low
  risk; reject a leading `-`.
- **F19 Redaction covers the exact token and its two base64 forms only.** A token echoed
  hex-encoded, reversed or split was not redacted in the probe (expected for this design;
  noted so nobody reads "any text that contains it is redacted" more widely). Secrets shorter
  than 4 characters are not registered. `verify_host_firewall.sh`, run under a read label,
  writes and removes `/tmp/.clm_r3_check`; it changes nothing else.

## 4. Checked and found sound

- **Purely additive; nothing secret tracked.** 39 added files, no modification, no `.env`,
  key or certificate.
- **Plan-only and dry-run cannot write.** `plan` is pure (a `_NoRunner` that raises). A
  dry-run of all three services reached the runner with `host-read` and `public-read` only, no
  secret on stdin, 14 commands recorded as "would issue". Every `host.read(...)` call was read:
  none mutates container, image, volume, network or `compose.env` state (the one exception is
  the temp file in F19). Local Docker writes are `LOCAL_WRITE` and are skipped in dry-run.
  `PROVIDER_CALL` is refused in every mode and no code issues one.
- **Deployment approval binding.** Wrong manifest, wrong service list, publish-only action,
  expired, not yet valid and a 25-hour window were each refused with 0 host writes. Single-use
  consumption is placed after image transfer and before the first `compose.env` change, and a
  second run with the same record is refused. The deadline is checked before every
  non-housekeeping host or registry write; nothing extends it.
- **No blind stateful rollback.** `rollback_blockers` is shared by the automatic and manual
  paths; `data_compatible` other than `true`, `automatic: false`, a missing target, missing
  owner consent or an expired window each hold the run. A schema-19 commit prefix or an older
  declared schema with `data_compatible` not `false` refuses the manifest (subject to F5).
- **Unauthorised change.** Only `up -d --no-build --no-deps --wait --wait-timeout 180
  <service>` is generated, through the correct wrapper set; an unchanged service whose config
  hash would differ stops the run before any container changes; Mongo is never targeted.
- **Shell injection.** Every f-string that builds a remote command was read. Host-returned
  pins and volume names pass `safe()` (`[A-Za-z0-9._/:@-]`) before use, including the `old`
  value in the `sed` line; manifest and profile values are `shlex.quote`d or constants. I found
  no path for a manifest, operator-config or host value to reach a remote shell unquoted.
- **Secrets.** Token travels on stdin only; argv and environment are checked by the gate; a
  token echoed by a failing host command (raw and base64 `user:token`) did not appear in the
  result, audit log or state files; `Secret` cannot be printed, formatted or pickled; error
  messages carry codes, not command output.
- **Manifest validator.** Both schemas use only keywords the built-in validator implements.
  6,062 manifest mutants and 557 approval mutants: 0 accepted by the built-in validator and
  rejected by `jsonschema`. The reverse (47 cases) is only integral floats such as `1.0`,
  which the built-in validator rejects: stricter, fail-closed.
- **Baseline** equals a fresh render of all six overlay sets; unsupported overlay
  combinations, wrong order, duplicates and unknown files are refused.
- **Existing safeguards in `deploy/LIGHTSAIL_RUNTIME.md`** (wrapper order, never `down` /
  `--remove-orphans` / volume removal, stop ingress and the old backend first, one writer) are
  followed by the generated commands; I found no place where code or documents weaken them.
  The controller stops at `PROMOTION_READY` and has no publish, approve or deploy call.

## 5. Not assessable without a real host or registry

- Real output formats and behaviour of `docker compose config --hash '*'` against the
  container label, `docker inspect`, `ss`, `pgrep` for the SSH session count (newer OpenSSH
  names the process `sshd-session`), `stat`/`diff` counting, and image ids on the containerd
  image store after a pull or a load.
- Whether `sudo -n --preserve-env=MONGO_URI` is permitted by the host's sudoers, whether
  `/etc/clm/mongo.uri` exists (F9), and whether `/run/lock` is writable by the operator.
- The pull script end to end (login from SSH stdin through `sudo`, cleanup, the
  `auth_dirs_left` count) and GHCR behaviour (`imagetools inspect --raw` digest equality,
  push output format, token scopes).
- `--wait` with `--no-deps` on a stopped backend, real health timing against the 180 s
  timeout, and behaviour when the SSH client times out while the remote command continues.
- The Windows Credential Manager wrapper (`ctypes` calls) was read but not exercised: no
  credential was created or read.
- Both firewall verify scripts on the host, and any run with the GoldTier or provider overlay
  active.
