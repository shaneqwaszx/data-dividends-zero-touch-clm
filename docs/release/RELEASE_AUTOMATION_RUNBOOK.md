# Release automation runbook

| Field | Value |
|---|---|
| Status | Tooling implemented and tested locally. **This runbook authorises nothing.** Every existing owner gate stays in force until the owner approves a revised procedure (`RISK_BASED_APPROVAL_PROPOSAL.md`) |
| Who runs it | Preparation: any engineering session on the Windows machine. Publication and deployment: only the session that owns the host, in an owner-approved window |
| Entry point | `.\tools\release.ps1 <command>` from the repository root (PowerShell 7). From Git Bash: `python -m tools.release <command>` |

Commands that could change something take `--plan-only`, `--dry-run` (the default) or
`--execute`. Without `--execute` and an approval record nothing is written to the host or the
registry.

## 1. Prepare (no approval needed; nothing leaves this machine)

1. Fetch and check out the exact approved commit in a clean checkout.

   ```powershell
   git fetch origin
   .\tools\release.ps1 verify-source --commit <40-character commit> --tree <40-character tree>
   ```

   Refused: an abbreviated commit, another `HEAD`, another tree, any uncommitted or untracked
   file (allow a known path with `--allow-untracked outputs/`), or a commit that is not in
   `origin/main` as last fetched.

2. Run the local mirror of the CI jobs for the change classes of the release.

   ```powershell
   .\tools\release.ps1 checks --change-class FRONTEND_UI --list     # see what would run
   .\tools\release.ps1 checks --change-class FRONTEND_UI
   ```

   Classes are those of `docs/DEVELOPMENT_WORKFLOW.md`, plus `ASSISTANT` for the assistant
   job. `tests/deploy` is launched through Git Bash automatically. The CI jobs with no
   automatic mirror (`local-ocr`, `phase12-mongo`, `e2e`, `demo-lifecycle-windows`) are always
   listed as `NOT_RUN`; run them by hand when the class needs them and attach the evidence.

3. Accept the existing image candidates by id, or build.

   ```powershell
   .\tools\release.ps1 image --service frontend --commit <commit> `
       --reference clm-rc-frontend:d0142d8 --image-id sha256:<64 hex>
   ```

   The image is accepted only if its id is exactly that value and it is `linux/amd64`. The
   command then compares the reviewed source files inside the image with the commit and, for
   the assistant, computes the qualification fingerprint in the image (networking disabled).
   `--build` exports the commit with `git archive` and builds from that export. **Never build
   again after an image has been qualified:** the backend and frontend base images float.

4. Write a release request (see `samples/release-request.assistant-only.sample.json`) and
   assemble the manifest. The request states what a person must decide: services, change
   classes, risk class, rollback target and compatibility per service, coupling, smoke
   expectations, quality-gate verdicts, evidence.

   ```powershell
   .\tools\release.ps1 manifest --request <request.json>
   .\tools\release.ps1 validate --manifest <manifest.json>
   ```

   Or drop the request in `<state-dir>\inbox\` and run `.\tools\release.ps1 controller tick`
   (`LOCAL_RELEASE_CONTROLLER.md`).

5. Read the plan. It lists exactly which services change, which must not, the host commands
   in order, the rollback order and the stop conditions.

   ```powershell
   .\tools\release.ps1 plan --manifest <manifest.json>
   ```

## 2. Independent review

The manifest, the plan and the image evidence go to an independent Quality Gate, as today.
Record its verdict in the request (`quality_gates`). Publication is refused while a gate is
`FAIL` or `NOT RUN`, while a recorded check is `FAIL`, or while an image's file equality is not
`PASS`.

## 3. Publish (owner approval; registry write)

```powershell
.\tools\release.ps1 approve --manifest <manifest.json> --service frontend --action publish `
    --not-before 2026-11-20T02:00:00Z --expires-at 2026-11-20T04:00:00Z --approved-by <owner>
.\tools\release.ps1 publish --manifest <manifest.json> --approval <approval.json> --dry-run
.\tools\release.ps1 publish --manifest <manifest.json> --approval <approval.json> --execute
```

`approve` is typed by the owner at an interactive terminal. `publish --execute` reads the
publish token from the Windows Credential Manager, logs in with a throwaway Docker
configuration, pushes each image under `rc-<commit12>-<config12>` (never `latest`), reads the
registry manifest back, checks that its config digest is the qualified image and that the
manifest hashes to the pushed digest, logs out and removes the configuration. It writes
`manifest.published.json`. **Use that file from here on.**

## 4. Deploy (owner approval; host change)

Operator configuration is a JSON file outside the repository, for example
`%LOCALAPPDATA%\DataDividendsCLM\release-operator.json`:

```json
{"ssh_destination": "<user@host alias>", "identity_file": "<path to the operator key>",
 "port": 22, "backup_dir": "<host directory holding the Mongo archives>",
 "mongo_uri_file": "<host file the operator's Compose wrapper reads the connection setting from>"}
```

```powershell
.\tools\release.ps1 approve --manifest <manifest.published.json> --service frontend `
    --action deploy --auto-rollback `
    --not-before 2026-11-20T05:00:00Z --expires-at 2026-11-20T07:00:00Z --approved-by <owner>

.\tools\release.ps1 deploy --manifest <manifest.published.json> --approval <approval.json> `
    --operator-config <operator.json> --dry-run      # read-only preflight, no change
.\tools\release.ps1 deploy --manifest <manifest.published.json> --approval <approval.json> `
    --operator-config <operator.json> --execute
```

The file holds no secret. `mongo_uri_file` is required for `--execute`: the host operator
confirms the path that already exists on the host (the Approval B script read
`/etc/clm/mongo.uri`). The tool only reads it on the host, inside the Compose command; it never
creates it. Optional overrides: `workdir`, `compose_env`, `site`, `lock_dir`.

`--auto-rollback` is the owner's consent to roll back automatically; it only has effect for a
service the manifest declares compatible. One approval covers the whole mechanical run: preflight,
transfer, apply, verification. No further decision is asked per command.

Exit code 0: `DEPLOYED_AWAITING_ACCEPTANCE` (or `DRY_RUN_OK`). Exit code 2: stopped; read
`state`, `stop_code` and `events` in the output. Exit code 3: refused. For `deploy` that is
before any host contact; for `rollback` it can follow read-only host checks. Any other exit
code, or a Python traceback: the run was interrupted; go to section 7.

## 5. Browser acceptance (owner)

The run writes `BROWSER_ACCEPTANCE_RUNSHEET.md` in the release's state folder and stops. The
owner works through it, then:

```powershell
.\tools\release.ps1 accept --manifest <manifest.published.json> --result pass --accepted-by <owner>
```

`pass` moves the known-good pointer and records the previous one. `fail` records the failure
and changes nothing on the host.

## 6. Rollback and stop conditions per service

| Service | Automatic rollback | Manual / owner-requested | Stop conditions |
|---|---|---|---|
| frontend | Yes, when approved: stateless. `compose.env` restored, `dc up ... frontend` on the previous image, verified | `release.ps1 rollback --manifest ... --approval <rollback approval> --operator-config ... --execute` | Roll the frontend back first, or together with the backend: a new frontend with an older backend breaks the Dashboard |
| assistant | Only if the manifest declares the stores compatible, from evidence. Default: **held** | Fastest safe action is `dca stop assistant` (every assistant route then returns the fixed 503). Pointing an older image at the volume needs a store-compatibility check first | Never remove the assistant data volume |
| backend | Only with both schema versions equal, the target confirmed on the host, and owner consent. Default: **held**, ingress stopped | Owner decision after reading the target ledger state. Never a schema-19 build after a schema-20 backend has written | Exactly one backend writer. Never roll back blindly |
| mongo, goldtier-egress, goldtier-dns | Never touched by the toolchain | Their own runbooks | A release naming them is refused |

`release.ps1 rollback` applies the same eligibility rules as the automatic path. It needs its
own approval:

```powershell
.\tools\release.ps1 approve --manifest <manifest.published.json> --service <service> `
    --action rollback --not-before <utc> --expires-at <utc> --approved-by <owner>
.\tools\release.ps1 rollback --manifest <manifest.published.json> --approval <rollback approval> `
    --operator-config <operator.json> --execute
```

The deploy approval cannot be reused for a rollback, and a rollback approval is single use.
The command refuses an ineligible service and says why; it takes the host lock; it changes
back only this release's image lines in `compose.env`, and only if they still show this
release's pins. If another change has been made since, it changes nothing and reports
`HOST_STATE_UNEXPECTED`. It ends by confirming every service is healthy and public `/health`
returns 200; if not, the result is `FAILED_HELD`, never `ROLLED_BACK`.

Explicit stop conditions for every run are printed in the plan (`stop_conditions`).

## 7. After a stop

- `FAILED_NO_CHANGE`: fix the cause, then run again. If the stop came before any host change
  the same approval is still usable inside its window.
- `ROLLED_BACK`: the tool verified every service healthy on the previous images and public
  `/health` 200. The approval is used; a new attempt needs
  a new approval.
- `ROLLBACK_IN_PROGRESS` or `ROLLBACK_INTERRUPTED`: a rollback started and has no verified
  outcome. **The host state is unknown.** Go to "After an interrupted or failed rollback"
  below. `accept` is refused in these states.
- `FAILED_HELD`: **do not run anything else.** Read `held_reason`. If it says ingress is
  stopped, the site is down until the owner decides between a rollback and a forward fix.
- A stale local lock after a crash: confirm on the host that nothing is running, then
  `.\tools\release.ps1 unlock`.

### After an interrupted run (Ctrl-C, a crash, a dropped SSH session, a killed tool)

For an interrupt Python can catch (Ctrl-C, an unexpected error), the tool writes a record and
then re-raises the error: `stop_code: INTERRUPTED` during the deployment, or state
`ROLLBACK_INTERRUPTED` during a rollback. If the process was killed outright or the machine
lost power, **no handler ran**: the last record on disk stands. During a rollback that is
`ROLLBACK_IN_PROGRESS`; during the deployment itself it is the previous result, or none. In
every case the host state is **unverified**. Stop and tell the owner. The host operator then
checks, read-only:

1. `release.ps1 status` and the last `result-NNN.json` in the release's state folder: `events`,
   `applied`, `env_backup`, `pins_before`, `ingress_stopped`.
2. On the host: is any `docker compose` command still running; which image each container
   runs; whether `compose.env` differs from the backup named in `env_backup`; whether
   `/run/lock/clm-release.lock` exists.
3. If no record was written at all (the machine lost power), the backup is the newest
   `/etc/clm/compose.env.pre-<release id>-<utc>`.

Then the owner decides one of:

- **Nothing had changed** (`applied` is empty, containers as before): the host operator copies
  the backup over `compose.env` if they differ. A new attempt needs a new approval if the old
  one was used.
- **Roll back**: if the record is `FAILED_HELD`, `ROLLBACK_INTERRUPTED` or a stale
  `ROLLBACK_IN_PROGRESS`, `release.ps1 rollback` with a **new** `rollback`
  approval, subject to the usual eligibility. Otherwise by hand, following
  `deploy/LIGHTSAIL_RUNTIME.md`.
- **Go forward**: fix the cause and run a new release with a new approval. Preflight will
  refuse while `compose.env` and the running containers disagree (`no-drift`), so the host
  must first be brought back to a consistent state.

A stale **host** lock is an empty directory. After confirming no release command is running,
the host operator removes it with `rmdir /run/lock/clm-release.lock`. The tool never removes a
lock it did not take.

### After an interrupted or failed rollback

Signs: state `ROLLBACK_IN_PROGRESS` with no release command running, `ROLLBACK_INTERRUPTED`, or
`FAILED_HELD` whose `rollback.status` is `FAILED`. The site may be down
(`rollback.ingress_may_be_stopped`). Nothing in such a record means the previous service is
back. `accept` refuses until the state is verified.

1. Read the latest `result-NNN.json` and `rollback-journal.jsonl` in the release's state
   folder. The last journal line is the step that was running or about to run. `rollback`
   holds this attempt (services, the images it was moving from and to, the `compose.env`
   backup, the approval id); `rollback_history` holds earlier attempts.
2. Confirm on the host that no `docker compose` command from the tool is still running. If the
   local lock is stale, remove it with `release.ps1 unlock`; a stale host lock with
   `rmdir /run/lock/clm-release.lock`.
3. Establish the state, read-only:

   ```powershell
   .\tools\release.ps1 recover --manifest <manifest.published.json> `
       --operator-config <operator.json> --recovered-by <name>
   ```

   It changes nothing on the host. Exit code 0 means it verified one of two things:
   `ROLLED_BACK` (every service healthy on its previous image, public `/health` 200) or
   `DEPLOYED_AWAITING_ACCEPTANCE` (every service healthy on this release's image, `/health`
   200 and the release's smoke requests as expected; owner browser acceptance is still
   required). The second is only possible for a release that was awaiting acceptance when
   its first rollback began.

   Exit code 2 means one of:
   - the state could not be established: the record becomes (or stays)
     `ROLLBACK_INTERRUPTED`, host state `unknown`. Unknown is never turned into success;
   - the host is healthy on this release's images, but the release's own deployment had
     stopped on a failure, or its acceptance had failed: the record is `FAILED_HELD`
     (`rollback.status: RECOVERED_ON_RELEASE_NOT_ACCEPTABLE`). **Read the original
     `stop_code` in the record.** Such a release cannot be accepted, whatever `recover`
     sees. The owner chooses another rollback attempt or a new release.
4. If it stays unknown or held, the owner chooses:
   - **Try the rollback again**: a new `rollback` approval (each attempt needs its own), then
     `release.ps1 rollback ... --execute`. A line of `compose.env` that already shows the
     previous pin is accepted; a line still on the release is changed back for every service
     of the release, including one that was pinned but never applied; the stops and recreates
     are repeated and verified.
   - **Recover by hand** following `deploy/LIGHTSAIL_RUNTIME.md` (start order: Mongo, backend,
     assistant, frontend; never `down`, never a volume removal), then run `recover` again so
     the record reflects what was verified.
5. For a backend: before ingress is started again, the owner decides from the target ledger
   whether the backend that is about to serve is the right one. The tool cannot judge that.

What the tool cannot do: record anything after a kill or power loss, tell whether a remote
command it lost contact with is still running, or verify data written by a backend that ran
briefly.


## 8. Never

`compose down`, `-v` / `--volumes`, `--remove-orphans`, volume removal, `compose rm`, a second
backend, a rebuild after qualification, a floating runtime tag, a credential on a command line
or in a file, a build or an untrusted workflow on the production host. The toolchain cannot
express the first six; do not work around it by hand.

## 9. Status

```powershell
.\tools\release.ps1 status          # known-good release, lock, result of each release
.\tools\release.ps1 recover ...     # read-only: host state after an unfinished rollback
.\tools\release.ps1 creds status    # identities, expiry (never a token)
.\tools\release.ps1 baseline        # does the reviewed baseline still match the Compose files?
```
