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

**Backend from `main` `50fac7c7` or later (ADR-017 P2-0 writer).** Before such a backend first
starts against a store, the one-time P2-0 backfill must have been run against that store. Each
step needs its own owner approval: the read-only inventory, then the dry run, then the apply in an
approved window (`scripts/adr017_backfill.py`, ADR-017 section 3.5). If the dispatch fence is
unavailable, every first GoldTier write is refused and affected cases pause: go to section 7,
"When the dispatch fence is unavailable".

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

An approval covers a rollback only if it names the `rollback` action; each action of an
approval is single use. An owner who wants the rollback to be a separate decision gives a
separate approval. `rollback` works only before acceptance (`DEPLOYED_AWAITING_ACCEPTANCE`,
`ACCEPTANCE_FAILED`, `FAILED_HELD`, or an unfinished rollback). An `ACCEPTED` release is
reverted by a new release that deploys the previous image.
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
  `/health` 200. The approval is used; a new attempt needs a new approval. **If this release
  failed acceptance, no new attempt is permitted for now: see "Deploying again after a failed
  acceptance: PROHIBITED for now" below.**
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

- **Nothing had changed** (`applied` is empty **and** every container still runs its previous
  image): the host operator copies the backup over `compose.env` if they differ. A new attempt
  needs a new approval if the old one was used.
- **Roll back**: if the record is `ROLLBACK_INTERRUPTED`, a stale `ROLLBACK_IN_PROGRESS`, or
  `FAILED_HELD` **with a non-empty `applied` list or `ingress_stopped: true`**,
  `release.ps1 rollback` with a **new** `rollback` approval, subject to the usual eligibility.
  If `applied` is empty and `ingress_stopped` is false, the tool refuses
  (`ROLLBACK_NOT_APPLICABLE`) even when a container
  was being recreated at the moment of the interrupt: check each container's image on the
  host. Restore by hand following `deploy/LIGHTSAIL_RUNTIME.md` (copy the backup named in
  `env_backup` over `compose.env`, then the service's own wrapper, `dc` for the frontend or
  backend (`dcg` for the backend when the GoldTier overlay is active), `dca` for the assistant:
  `up -d --no-build --no-deps --wait <service>`). `recover` does not apply to this record; it
  stays `FAILED_HELD` until a later run changes the host.
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
   the current rollback episode began, and that has not failed acceptance.

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
     are repeated and verified. If the rollback stops with "the container is not running its
     previous image" for a service that was never applied, someone started that service by
     hand on the release image: the host operator recreates it by hand on the previous image
     (the service's own wrapper from `deploy/LIGHTSAIL_RUNTIME.md`: `dc` for the frontend or
     backend (`dcg` for the backend when the GoldTier overlay is active), `dca` for the
     assistant; `up -d --no-build --no-deps --wait <service>`, with the
     line already changed back),
     then runs `recover`.
   - **Recover by hand** following `deploy/LIGHTSAIL_RUNTIME.md` (start order: Mongo, backend,
     assistant, frontend; never `down`, never a volume removal), then run `recover` again so
     the record reflects what was verified.
5. For a backend: before ingress is started again, the owner decides from the target ledger
   whether the backend that is about to serve is the right one. The tool cannot judge that.

What the tool cannot do: record anything after a kill or power loss, tell whether a remote
command it lost contact with is still running, or verify data written by a backend that ran
briefly.


### Deploying again after a failed acceptance: PROHIBITED for now

Owner decision, 2026-11-15, exact words: "A release that previously failed acceptance MAY be redeployed under the same release_id, but only as a new, independently identifiable and authorised deployment attempt. The same release_id identifies the qualified release; the new attempt must have its own immutable attempt_id."

`release_id` is the qualified release; `attempt_id` is one deployment attempt of it; a retry
keeps the `release_id` and gets a new `attempt_id`. **`attempt_id` does not exist in the tool
today**, and the tool does not fully enforce four of the decision's six requirements (history
preservation, attempt identity, an approval issued after the failure for that attempt, and
re-verification of source, images, host and rollback readiness): one is not enforced at all
and three only partly (`PIPELINE_ARCHITECTURE.md` section 3.8).

**Interim rule. Until those four requirements are implemented, tested and independently
reviewed, a release that failed acceptance must not be deployed again with this tool, under
the same or any attempt.** The tool does **not** block it today, so this is a procedural rule
that the operator and the owner must keep:

- Do not run `deploy --execute` for a release whose records show a failed acceptance
  (`acceptance_failed: true` in any numbered result, or state `ACCEPTANCE_FAILED`).
- Before any `accept`, open the release's `result.json` (or read the `deploy` output). If
  `previously_failed_acceptance` is `true`, an earlier deployment of this release failed
  acceptance: **stop, do not accept**, tell the owner, and roll the release back under a new
  `rollback` approval. `accept`, the runsheet and `status` do not show this flag.
- The only permitted route for now is a **new release**: a new `release_id` and manifest, taken
  through the full preparation, checks and independent review (sections 1 to 5). This is an
  interim rule, not the owner's eventual model, which is a retry of the same `release_id`
  under a new `attempt_id`.
- Owner, 2026-11-15: **"Do not use a new release_id as a shortcut to bypass unresolved host or
  rollback safety conditions."**

Names you may meet: `accept` refuses with `ACCEPTANCE_ALREADY_FAILED` for a record whose
acceptance failed; a run that changed nothing while a release was live carries
`standing_record_kept` in its numbered result and leaves `result.json` as it was.

### When the dispatch fence is unavailable (ADR-017 P2-0)

Applies to a backend from `main` `50fac7c7` or later. The fence guards every first GoldTier write.
When it is unavailable, that write is refused (`WORKFLOW_STAGE_CHECK_UNAVAILABLE`) and a
zero-touch case pauses in `RECOVERY_PENDING`. Reads and case work continue, nothing is written to
GoldTier, and no case fails because of this.

**Two kinds of unavailability.**

| Kind | How to tell | Clears |
|---|---|---|
| **At startup** | The backend log has the warning `dispatch fence unavailable at startup` | **Only at the next backend start**, after the cause is fixed. It stays unavailable even after the cause is gone |
| **At run time** | Sends are refused, but no startup warning is logged | Without a restart: the fence re-probes the store on each use and recovers once MongoDB is a journaled standalone or replica-set primary again. Fix the store or connectivity |

**The log does not show the reason.** The startup warning carries its reason only as a structured
field that the default backend logging does not print. **Do not guess the cause, and do not run
any write to find out.**

**Steps.**

1. **Stop and tell the owner.** Record the time of the warning and the release and attempt
   identifiers. Run no release command, backfill or correction until the owner decides.
2. **Diagnose with owner approval only.**
   - **Definitions** (backfill, re-verification, P2-1 content): the read-only **dry run** of
     `scripts/adr017_backfill.py` changes nothing and prints:
     - the workflows still to backfill (`to_backfill`, the `NOT_BACKFILLED` case)
     - each refused workflow with its re-verification reason, where a P2-1-migrated document shows
       as `P2_1_MIGRATED`

     Running it against a deployed database needs a separate owner approval and the read-only
     inventory first (the script's own header).
   - **Store** (topology, journaling, version, primary): the host operator checks MongoDB read-only
     and reports.
   - Reasons the dry run cannot show: `ONBOARDING_PROVISIONING_FAILED` and
     `STARTUP_CLAIM_CLEARING_INCOMPLETE`. They show up as a store that cannot be written durably.
3. **Fix the cause the owner approves** (table below). A fix that writes data, such as the backfill
   or a reviewed correction, needs its own owner approval and window.
4. **Startup kind only: restart the backend process. The host operator (AWS lane) performs this,
   only with the owner's dated written authorisation given directly to that operator.**

   The host decides how the backend is created, so never pick a Compose wrapper from this runbook.
   On the staging host, the ACRA lease controller creates the backend with its own overlays.
   A `dc`, `dcg` or `dcgw` `up` would recreate it without them. Follow the operator's host
   procedure, in this order:

   1. Check the preconditions: no D-137 write window is open, no release is running, and it is not
      the ACRA lease renewal window.
   2. Record the backend container id, the lease state and the start time.
   3. **Close the ACRA lease** through the lease controller. Never stop the backend while the
      lease is open: the lease watcher treats that as a fault and closes the lease on its own.
      The close recreates the backend without the ACRA overlay, so the container id changes.
      That is already a new backend process: run the Confirm step below against its start
      time.
   4. **Only if the fence is still unavailable** after the cause is fixed, stop and then start that
      same container in place. Never use `up`, a recreate, `dc`, `dcg` or `dcgw`. On an unchanged
      service, `up -d` alone does not restart the process.
   5. **Reopen the lease** through the lease controller's own procedure, if the owner wants it
      open. It recreates the backend with the ACRA overlay, and the container id changes again.
      Repeat the Confirm step below.
   6. After the final backend change (the reopen, or step 3 or 4 if the lease stays closed), the
      operator runs the host's post-checks: the R3 firewall verifier, the GoldTier egress pin
      with Sandbox mode and writes disabled, and the assistant egress checks.

   **Never stop, start or recreate the AI Assistant for this.** It has no restart policy. It starts
   only through its systemd gate, and stopping it drops the in-memory provider session keys, which
   HR must then enter again. A backend restart resets process-local sessions and the login
   limiter, so users sign in again.
5. **Confirm.** The restarted backend logs no `dispatch fence unavailable at startup` warning. Count
   the lines; never print the log. If it does log one, close the lease again if it was reopened,
   and go back to step 1.
6. **Explicitly resume each paused case** (`RECOVERY_PENDING`) from its case page, one at a time.
   Nothing resumes on its own. Each case continues the same submission and never replays a write
   that was already attempted.

**Startup reasons, as the code defines them, and what each needs.**

| `reason` | Cause | Fix |
|---|---|---|
| `NOT_BACKFILLED` | A definition has no `active_version` or `latest_version` | The P2-0 backfill: dry run, then apply, in an owner-approved window |
| `ACTIVE_NOT_ZERO_OR_LATEST`, `LAST_VERSION_NOT_LATEST`, `VERSIONS_NOT_STRICTLY_INCREASING`, `VERSION_ABOVE_LATEST`, `ONBOARDING_NOT_ACTIVE`, `DEFINITION_INVALID` | A definition fails startup re-verification | The owner decides on a separately reviewed correction (ADR-017 section 3.5), **never** a backfill re-run |
| `P2_1_CONTENT_NOT_SUPPORTED_BY_P2_0` | A P2-0 backend was started against a store already migrated by P2-1, for example after a rollback | The owner decides. Never strip P2-1 content, and never run the P2-0 backfill or reverse migration on it (both refuse) |
| `VERIFICATION_FAILED` | The definitions could not be read for verification | Fix store availability, then restart |
| `ONBOARDING_PROVISIONING_FAILED` | The onboarding definition could not be provisioned | Fix store availability or write access, then restart |
| `JOURNALING_UNVERIFIED`, `NOT_PRIMARY`, `TOPOLOGY_UNIDENTIFIED`, `SHARDED_UNSUPPORTED`, `SERVER_VERSION_UNVERIFIED`, `PROBE_FAILED`, `PROBE_UNSUPPORTED`, `DURABILITY_UNAVAILABLE` | The store is not a journaled standalone or replica-set primary on the verified major version, or could not be probed | Fix the MongoDB topology or connectivity, then restart. Do not change the probe |
| `STARTUP_CLAIM_CLEARING_INCOMPLETE` | Startup could not clear every dispatch claim that has no write attempt marker | Fix store availability, then restart. Clearing runs again at startup |

**Never:**

- run the P2-0 backfill after P2-1 has been deployed
- edit case ledgers, claims or workflow definitions by hand
- run more than one backend process against a store
- bypass or disable the fence to clear a queue

**Known gap.** The reason is not visible in the default log. Making it visible is a separate
backend follow-up, not part of this runbook change.

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
