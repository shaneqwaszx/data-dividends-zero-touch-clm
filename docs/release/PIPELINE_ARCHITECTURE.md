# Release pipeline architecture

| Field | Value |
|---|---|
| Status | **Implemented and tested locally against mocks. Never run against the Lightsail host or GHCR.** Not installed anywhere. Changes no existing gate. An independent review of the first candidate returned **FAIL**; its findings were then addressed, and that remediation has **not** been independently re-reviewed (`TEST_EVIDENCE_AND_LIMITATIONS.md`) |
| Scope | One reusable, Windows-friendly release toolchain for the single-host AWS demo (`clm-staging` on one Lightsail instance). No Kubernetes, Terraform, other cloud or new infrastructure |
| Depends on GitHub Actions | No. Every step runs from this repository on the developer machine |
| Code | `tools/release/` (Python 3.12, standard library only), entry point `tools/release.ps1` |
| Tests | `tests/release/` (mock host, mock registry, throwaway Git repository) |

## 1. What it replaces

Releases so far were done by hand: a coordinator built images, wrote a release manifest in
Markdown, wrote one-off host scripts (`b1_precheck.sh`, `b5_b8_switch.sh`, a pull script), had
them reviewed, and the host operator ran them. Each release repeated the same reasoning. This
toolchain turns that reasoning into code with tests, and keeps the same safeguards.

## 2. What is reused and what is new

**Reused unchanged (read, never edited):**

| Existing material | How the toolchain uses it |
|---|---|
| `deploy/compose.yml`, `deploy/compose.mongo.yml`, `deploy/compose.goldtier-egress.yml`, `apps/assistant/deploy/compose.assistant.yml`, `apps/assistant/deploy/compose.assistant-provider.yml` | Rendered offline; hashed into the manifest; applied on the host only through the runbook wrappers |
| `deploy/LIGHTSAIL_RUNTIME.md` (`dc`, `dca`, `dcg`, overlay order, "never `down`", stop order) | `catalog.py` encodes the wrappers and order; `host.py` builds exactly those commands |
| `deploy/README.md` ("stop ingress and the old backend before starting the new one"; one writer) | The backend sequence in `deploy.py` |
| `apps/assistant/deploy/RELEASE_HANDOFF.md`, the H5 addendum | Assistant-only flow, its rollback caution and acceptance rows |
| `deploy/egress/host/verify_host_firewall.sh`, `apps/assistant/deploy/egress/verify_assistant_egress.sh` | Run in preflight when the matching overlay is active. They change no firewall, container or configuration state; `verify_host_firewall.sh` writes and removes one scratch file, `/tmp/.clm_r3_check`, so "read-only" here means "changes nothing that matters", not "writes nothing" |
| `.github/workflows/ci.yml` | The job list mirrored by `release.ps1 checks`; a test fails if the workflow gains a job the mirror does not know |
| `scripts/check_*.py`, `scripts/pre_pr_check.py`, `tests/deploy/**` | Run as they are by `release.ps1 checks` |
| `ai_assistant.model_qualification.qualification_basis()` | Computed inside the assistant image with networking disabled |
| `render_combined.py` and `tests/deploy/test_goldtier_egress_compose.py` (offline `docker compose config` with placeholders, no `.env`) | The approach of `render.py` |
| Approval B scripts (sole-operator check, `compose.env` backup and one-line change, config-hash comparison, per-service `up`, RB-1) and the throwaway-configuration pull | The steps of `deploy.py` and the pull script in `registry.py` |
| The tag convention `rc-<commit12>-<config12>` and "publish as built, never rebuild" | `manifest.release_tag`, `registry.publish` |

**New:**

- a versioned JSON release manifest with a JSON Schema, and an approval record bound to its hash;
- one execution gate that makes plan-only and dry-run unable to write;
- a reviewed baseline of the effective Compose configuration and a rule that refuses anything
  undeclared;
- per-service rollback eligibility, including the schema-19 rule;
- a credential store wrapper (Windows Credential Manager) with separate publish and pull identities;
- a local controller that stops at "promotion ready".

## 3. Components

```text
tools/release.ps1                PowerShell wrapper: python -m tools.release from the repo root
tools/release/
  core.py                Secret, redaction, Command/Effect, Gate (modes), audit log
  catalog.py             services, overlay sets and order, wrappers, risk, host profile
  manifest.py            schema validation, release rules, manifest hash, risk floor
  approval.py            approval record: hash, services, window, single use
  source.py              exact commit / clean state; local mirror of the CI jobs
  images.py              accept by image id or build; in-image equality; fingerprint
  render.py              offline effective configuration; invariants; baseline comparison
  effective_summary.py   secret-free summary (the same source runs on the host)
  credstore.py           publish / pull identities; temporary Docker configuration
  registry.py            publish by digest; host pull; archive transfer
  host.py                SSH transport and the only Compose command builder
  deploy.py              plan, preflight, apply, verify, rollback, acceptance
  records.py             results, known-good pointer, used approvals, local lock
  controller.py          request -> promotion-ready record; never promotes
  cli.py                 sub-commands
  schema/                release-manifest.schema.json, approval-record.schema.json
  policy/                effective-baseline.json (reviewed render of every overlay set)
```

### 3.1 The gate

Every external action is a `Command` with a declared `Effect`. One `Gate` decides whether it
may run:

| Mode | local read | local write (build, checks) | host read | host write | registry read | registry write | provider call |
|---|---|---|---|---|---|---|---|
| `plan-only` | yes | no | no | no | no | no | never |
| `dry-run` | yes | no | yes (or none with `--offline`) | no | yes | no | never |
| `local` (preparation, controller) | yes | yes | no | no | no | no | never |
| `execute` | yes | yes | yes | yes | yes | yes | never |

A skipped command is recorded as "would issue" and returns no output. The gate also refuses a
command whose argument or environment contains a registered credential, refuses a fixed list
of host commands (`down`, `-v`, `--remove-orphans`, volume removal, `compose rm`, `--scale`,
`up` without `--no-deps` or `--no-build`, anything naming `mongo` as a target, direct
`docker rm|stop|exec`, firewall and power commands), and checks the approval deadline before
every host or registry write. The deny-list is a backstop, matched on text with quoting
removed; the real control is that the command builders in `host.py` cannot produce those
commands. Two housekeeping writes are exempt from the deadline, so an expired window never
leaves the host half-configured or locked: restoring `compose.env` to its pre-run content
(no container is touched) and releasing the host lock. The toolchain has no code path that calls an AI provider; the effect exists
so the tests can prove it is refused.

### 3.2 Release manifest

`tools/release/schema/release-manifest.schema.json`; sample
`docs/release/samples/release-manifest.d0142d8.sample.json`. It records: source commit and
tree; per image the local id, config digest, registry manifest digest (null until published),
in-image file-equality result, the assistant fingerprint computed in the image and, for the
backend, the case-snapshot schema version read from the commit; Compose file hashes; the
host's active overlays and the overlay order; evidence paths and quality-gate verdicts; risk
class and the reasons; the services that change and those that must not; per service the
rollback target, whether rollback is data-compatible (`true`, `false` or `"unproven"`), whether
it may be automatic and its stop conditions. **"Compatible" is a declaration**: a person
states it in the manifest from evidence and the owner approves it; the tool cannot inspect
what an image writes. It only refuses declarations that contradict themselves or the known
schema-19 line; public smoke expectations; and the previous
known-good manifest.

The manifest hash is the SHA-256 of its canonical JSON. Publication fills in the registry
digests, so the published manifest has a new hash and records the candidate's hash in
`candidate_manifest_sha256`. **The deploy approval is given for the published manifest.**

### 3.3 Approval record

`tools/release/schema/approval-record.schema.json`. Bound to one manifest hash, one exact
service list, one risk class, the actions (`publish`, `deploy`, `rollback`), a start time and
an expiry.
Rules enforced in code:

- wrong manifest, wrong services, wrong action or wrong risk class: refused;
- before the start or at/after the expiry: refused; a window longer than 24 hours: refused;
- expiry is checked again before every host or registry write. An expired window stops the run
  before the next change; it is never extended, and no automatic rollback runs after expiry.
  If it expires after `compose.env` was edited but before any container changed, the file is
  restored (housekeeping) and the result is `FAILED_NO_CHANGE`;
- an owner-requested rollback needs its own record with the `rollback` action; the deploy
  record cannot be reused for it;
- a deployment does not start unless enough of the window is left to finish and verify;
- single use: once a run begins changing the host's configuration the approval cannot start
  another run. A stop before that point (failed preflight, failed pull) leaves it usable;
- `approve` refuses to run without an interactive terminal and makes the owner type the first
  12 characters of the manifest hash. This is a procedural control, not a cryptographic
  signature (see limitations).

### 3.4 Effective configuration check

`render.py` renders a supported overlay set offline with placeholder values and reduces it to
a summary holding no secret. Two checks follow.

**Invariants** no manifest can relax: only the frontend publishes ports, and only 80 and 443;
each service's networks stay inside a fixed ceiling (Mongo: `database` only; the backend never
on a network with an internet route; the assistant on `proxy`, plus `assistant-uplink` only
with the provider overlay; the GoldTier containers on their two networks only); `proxy`,
`database` and `goldtier-control` stay internal; `GOLDTIER_SANDBOX_ALLOW_WRITES` is the literal
`false`; without the provider overlay the assistant's model client points at the closed local
port and no provider variable exists; no credential variable in the assistant's Compose
environment; no privileged mode, host namespaces, devices, replicas, Docker socket or writable
host bind, or `volumes_from`; capabilities dropped and a read-only root for backend, assistant
and the egress containers; no added capability except the four the R3 guard needs, on the two
GoldTier services only; no security option other than `no-new-privileges`; the Mongo and
assistant data volumes stay `external` (so Compose can never remove them). The Docker socket
is recognised by a bind mount's source as well as its target.

**Baseline comparison.** `policy/effective-baseline.json` is the reviewed render of every
supported set at the current Compose files. A render that has a network, port, environment
variable or setting the baseline lacks is refused unless the manifest declares it in
`declared_config_changes`, and a declaration raises the risk class (a network, port or setting:
HIGH). A test fails when the Compose files and the baseline disagree, so a Compose change
forces a reviewed baseline update (`release.ps1 baseline --write`, then review the diff).

**What the summary covers, and what it does not.** Covered per service: networks and fixed
addresses, published ports, environment variable *names*, the values of 14 non-secret safety
switches, volumes (type, named source, target, mode), whether each bind source is an
interpolated path or a literal one, `extra_hosts` *names*, `depends_on`, command, entrypoint,
health-check command, tmpfs, capabilities, security options, read-only root, restart policy,
user, DNS, sysctls, devices, memory and process limits, container name and platform; plus the
`internal` and `external` flags of top-level networks and volumes. **Not covered:** other
environment values (they hold secrets, so they are never read), the actual host paths behind
interpolated bind sources, the addresses in `extra_hosts`, labels, network aliases, CPU
limits, logging, and health-check timing. A Compose change confined to those fields does not
move the baseline. The Compose files are still hashed into the manifest and reviewed as
source; the summary is an additional automatic check, not a replacement for that review.
On the host, the changed service's networks and ports are compared with the baseline and the
invariants are re-run; environment names are compared offline only, because the host's
environment includes the backend's runtime file.

Supported overlay sets, in the only supported order:

| Set | Files | Host wrapper |
|---|---|---|
| `base` | compose.yml, compose.mongo.yml | `dc` |
| `assistant` | base + compose.assistant.yml | `dca` |
| `assistant-provider` | assistant + compose.assistant-provider.yml | `dca` with the provider overlay (R2.2; not approved for AWS) |
| `goldtier` | base + compose.goldtier-egress.yml | `dcg` |
| `full-assistant-goldtier`, `full-provider-goldtier` | whole stack | validation only; never applied |

Any other combination, a wrong order, a duplicate or an unknown file is refused.

On the host the same summary source runs behind a pipe (`config --format json | python3 -I -c
...`), so the full rendered configuration, which contains the database connection setting,
never leaves the host and is never printed.

### 3.5 Deployment sequence

```text
local lock -> manifest + approval checks -> offline effective-config validation
-> preflight (read-only) -> host lock -> transfer images + verify identity
-> back up compose.env, replace one line per service, verify the diff
-> host config validation: only the approved services' config hashes differ
-> per service, in order backend, assistant, frontend:
     up -d --no-build --no-deps --wait --wait-timeout 180 <service>
     verify: recreated, approved image, healthy, 0 restarts, every other container,
             data volume and the proxy network unchanged, exactly one backend
-> public smoke -> post-deploy verification -> release host lock
-> DEPLOYED_AWAITING_ACCEPTANCE: browser runsheet; the pipeline waits for the owner
-> owner records pass: known-good pointer moves. Fail: recorded, nothing rolls back by itself
```

Backend only: ingress (`frontend`) is stopped, then the old backend, then the new backend is
started, then ingress is started again (or recreated, if it also changes). That is the
sequence in `deploy/README.md` and it keeps exactly one writer.

Preflight checks: sole operator (one SSH session, no other Docker or dump process); no host
lock; clock drift; free memory and disk; Compose version and no `COMPOSE_*` variable; installed
Compose files equal the manifest's hashes; every container healthy; no drift (each running
container's config hash equals what its wrapper renders now); data volumes present and mounted;
a recent backup (required when a stateful service changes; the location comes from the operator
configuration and a stateful release is refused without it); the current pin is the rollback
target the manifest names and that image is cached; for a backend change the running backend's
identity is recorded as confirmed; the proxy network is internal and only ports 22, 80 and 443
listen on a public address; the firewall verify scripts pass where their overlay is active;
public `/health` returns 200.

### 3.6 Failure handling

| Where it fails | Result | What happened on the host |
|---|---|---|
| Approval, manifest, offline render, preflight, image transfer | `FAILED_NO_CHANGE` | Nothing changed (an image may be cached) |
| `compose.env` edit or host config validation | `FAILED_NO_CHANGE` | `compose.env` restored from its backup; no container changed |
| Old backend stopped but the new one never started | `FAILED_NO_CHANGE` | The untouched old backend and ingress are started again |
| After a container changed, rollback eligible and approved | `ROLLED_BACK` | `compose.env` restored; services recreated on their previous image; then every service is confirmed healthy and public `/health` returns 200. Without a backend the frontend goes first. With a backend, ingress is stopped first and started (or recreated) last |
| After a container changed, rollback not eligible | `FAILED_HELD` | **Nothing further is changed.** The record says exactly what is running, and whether ingress is stopped |
| Approval expired after a container changed | `FAILED_HELD` | Stopped before the next change; no rollback |
| Approval expired after the `compose.env` edit, before any container changed | `FAILED_NO_CHANGE` | `compose.env` restored |
| Deployment interrupted by something Python can catch (Ctrl-C, an unexpected error), outside a rollback | `FAILED_HELD` if the host was touched, else `FAILED_NO_CHANGE`; the error is re-raised | Unverified. The record holds the backup path, the previous pins and the services already applied |
| Rollback interrupted (automatic or owner-requested), by anything Python can catch | `ROLLBACK_INTERRUPTED`, host state `unknown`; the error is re-raised. In three narrow windows (while the interrupted record itself is being written, or on the lock-release command after the last step) the record instead stays `ROLLBACK_IN_PROGRESS`, or is `FAILED_HELD`; none of these is acceptable and none says "rolled back" | Unknown. The journal names the step that was running. Never reported as rolled back |
| The tool dies during a rollback with no handler (kill, power loss) | The record already on disk: `ROLLBACK_IN_PROGRESS` | Unknown. Treated exactly like `ROLLBACK_INTERRUPTED` |
| A rollback step fails, or its final verification fails | `FAILED_HELD` with `rollback.status: FAILED` | Whatever the failed step left; `ingress_stopped` says whether the site may be down. The previous service is **not** confirmed restored |

Automatic rollback needs all of: the owner approved it in the approval record; the manifest
declares `data_compatible: true` and `automatic: true` for every touched service; the previous
pin was recorded. For a backend it additionally needs the target's source commit (7 to 40
lower-case hex characters), both schema versions and the target recorded as confirmed on the
host. A target whose declared commit is on the `4c1db49` line, or whose declared schema is
older than the new backend's, cannot be marked compatible: the manifest is refused. These are
checks on what the manifest declares. Nothing ties the target digest to the declared commit,
so the declaration must come from the host lane's record, not from memory.

An owner-requested rollback (`release.ps1 rollback`) uses the same eligibility rules, needs a
`rollback` approval, takes the host lock, and changes only this release's lines in
`compose.env`, and only if they still show this release's pins. If the host has moved on it
changes nothing.

## 3.7 Result states and rollback

```text
                        deploy --execute
                               |
        +----------------------+-----------------------+
        | stopped before any   | deployed and verified | stopped after a container changed
        | container changed    |                       |
        v                      v                       v
 FAILED_NO_CHANGE   DEPLOYED_AWAITING_ACCEPTANCE   rollback eligible and approved?
                       |        |        |            | no                 | yes
               accept pass   accept    rollback       v                    v
                       |      fail    --execute   FAILED_HELD     ROLLBACK_IN_PROGRESS  <-- written to disk
                       v        |        |            |             (automatic)             BEFORE the first step
                   ACCEPTED     v        |            | rollback        |
                     ACCEPTANCE_FAILED   |            | --execute       |
                                |        v            v                 |
                                +--> ROLLBACK_IN_PROGRESS (manual) <----+ (a later attempt)
                                              |
            +---------------------------------+----------------------------------+
            | every step done and verified    | a step failed        | interrupted, crashed,
            v                                 v                      v or the tool died
        ROLLED_BACK                      FAILED_HELD          ROLLBACK_INTERRUPTED
     (rollback.status                 (rollback.status        (rollback.status INTERRUPTED,
      COMPLETED_VERIFIED)              FAILED)                 host_state unknown)
                                              |                      |
                                              +----------+-----------+   a record left at
                                                         |               ROLLBACK_IN_PROGRESS with
                                                recover (read-only)      no command running is
                                                         |               treated the same way
            +--------------------------------+-----------+---------------------+
            | verified on previous images    | verified on release images      | anything else,
            v                                v and smoke as expected           v or host unreadable
        ROLLED_BACK              was the release awaiting acceptance    ROLLBACK_INTERRUPTED
                                 when its FIRST rollback began?         (unknown stays unknown)
                                   | yes                    | no (its deployment stopped on a
                                   v                        v  failure, or acceptance failed)
                     DEPLOYED_AWAITING_ACCEPTANCE       FAILED_HELD
                     (acceptance still required)        (never acceptable; rollback again
                                                         or a new release)
```

`DEPLOYED_AWAITING_ACCEPTANCE` is reached only by a deployment that passed its own full
post-deploy verification. `recover` can return a release to it only if the release was in that
state when the current rollback episode began (`state_before_rollback`: kept across repeated
attempts of one episode; a rollback that starts later, from `DEPLOYED_AWAITING_ACCEPTANCE` or
`ACCEPTANCE_FAILED`, starts a new episode with that state as its origin), carries no stop
code, and has not failed acceptance. A failed acceptance is permanent for **that
deployment** (`acceptance_failed`): no rollback, `recover` or later `accept` can undo it, and
`accept` refuses it whatever the state says. A deployment that stopped on a stop condition, or
whose acceptance failed, can never become acceptable through `recover`, however healthy the
host looks.

What can still be accepted afterwards is a **new, complete deployment** of the same release:
a new `deploy --execute` with a new, unused owner deploy approval that passes the whole
preflight, apply and post-deploy verification produces a new `DEPLOYED_AWAITING_ACCEPTANCE`
record. In practice that follows a rollback, because preflight refuses while the host still
runs the release; the code does not require a `ROLLED_BACK` record as such. That path existed before this change and is left as it
is, because removing it would change what an owner approval can do. The new record carries
`previously_failed_acceptance: true`, and every earlier record stays in its numbered file.
**The flag is stored in the record and printed in the full `deploy` output only.** The
`accept` command, the browser runsheet and `status` do not show it today, so the owner must
read the record (or the numbered results) before accepting; surfacing it in those three
places is an open follow-up. Whether a release that once failed
acceptance should ever be redeployed under the same release id, rather than as a new release,
is an owner decision.

A `deploy` or dry-run of a release whose rollback has no verified outcome is refused
(`ROLLBACK_INCOMPLETE`) before anything is written or contacted. More generally, a run that
changes nothing (refused, stopped before any change, or a dry-run) is kept as a numbered
result but never replaces the standing record (`result.json`) of a release that is live on
the host (`DEPLOYED_AWAITING_ACCEPTANCE`, `ACCEPTED`, `ACCEPTANCE_FAILED`, `FAILED_HELD` or
an unfinished rollback), so `accept`, `rollback` and `recover` keep working from the last
record of a run that changed the host. That record can itself be out of date if the host was
changed by hand since; the tool does not notice that until `rollback` or `recover` reads the
host. One known gap: an interrupt at the instant the first `compose.env` pin is written is
recorded as `FAILED_NO_CHANGE` (the flag is set after the command returns), and when a live
standing record is kept, `status` shows no trace of that attempt; it is in the numbered
result and the audit log.

Rules the code enforces:

- `ROLLBACK_IN_PROGRESS` is written and flushed to disk **before** any service is stopped or
  replaced and before `compose.env` is touched for the rollback. If that record cannot be
  written, the rollback does not start (`FAILED_HELD`, "rollback was not started").
- Each rollback step is appended to `rollback-journal.jsonl` and to the latest record
  **before** it is issued (`STARTED`), then marked `DONE`. A step that may stop ingress
  (stopping it, starting it, or recreating the frontend, which is the ingress) sets
  `ingress_may_be_stopped` before the command is sent, so within a rollback the flag does not
  lag the host by a step. The deployment path before any rollback still sets its flags after a
  command returns.
- The state files are written by write-then-rename with a flush to disk. On Windows the
  rename can briefly fail with "Access is denied" while another process holds the file; it is
  retried for about two seconds. If it still fails, the step is not taken and the rollback
  stops; the result is `FAILED_HELD`, or, when the final record itself cannot be written, the
  record on disk stays `ROLLBACK_IN_PROGRESS`. Neither is acceptable.
- A rollback is `ROLLED_BACK` only after every service is confirmed healthy, every service
  of the release (including one that was pinned but never applied) shows its previous pin in
  `compose.env` **and** runs its previous image, and public `/health` returns 200. An interrupt, an unexpected error, a failed step or
  an unreadable host can never produce `ROLLED_BACK`, and no record says the previous service
  was restored unless that was verified.
- `accept` refuses (`ROLLBACK_INCOMPLETE`) while the latest record is `ROLLBACK_IN_PROGRESS` or
  `ROLLBACK_INTERRUPTED`, or carries a rollback that is in progress, interrupted or failed.
  The only way back to an acceptable state is `recover`, which is read-only (it runs in
  dry-run mode, so the gate cannot issue a host write), is run by a person, and changes the
  state only on what it verified.
- A further rollback attempt is allowed from `FAILED_HELD`, `ROLLBACK_INTERRUPTED` or a stale
  `ROLLBACK_IN_PROGRESS`, with a new single-use `rollback` approval per attempt. On a repeated
  attempt a `compose.env` line that already shows the previous pin is accepted as done.
- Every attempt is kept: `rollback` holds the latest, `rollback_history` the earlier ones, and
  `recovery_attempts` each recovery check. The record keeps the manifest hash, the previous
  known-good reference, the previous pins, this release's references, the `compose.env` backup
  path and both approval ids throughout.
- Automatic rollback runs while the host lock is still held.

**What cannot be handled, and what the operator does.** Interrupts and errors that Python can
see are caught and recorded. A process that dies with no handler (SIGKILL, Task Manager "End
task", power loss, machine failure, a full disk at the wrong moment) writes nothing more: the
last durable record stands. During a rollback that record is `ROLLBACK_IN_PROGRESS` and its
last journalled step is the one that was about to run or was running. During the deployment
itself, before any rollback, there is no in-progress record: the previous result (or none)
stands, as limitation 4b says. A stale local lock and possibly a stale host lock remain.
The operator's procedure is runbook section 7.


## 4. Local state

`%LOCALAPPDATA%\DataDividendsCLM\release-controller\` by default (`--state-dir` or
`CLM_RELEASE_STATE_DIR` to change): per-release manifest, approval, plan, numbered result
files (never overwritten), redacted audit log, browser runsheet; `known-good.json` with
history; `consumed-approvals.json`; `release.lock`. It holds no credential.

## 5. Limitations

1. **Never exercised against the real host or registry.** Host command output formats (for
   example `docker compose config --hash`, `ss`, the containerd image store's image ids) are
   modelled on the Approval B evidence, not observed by this toolchain.
2. The approval record is not signed. Anyone who can write files as the owner's Windows user
   could forge one. Hardening option: sign it with the owner's SSH key (`ssh-keygen -Y sign`)
   and verify before use.
3. Archive transfer (`--transfer load`) is tested only against a mock. On the host's
   containerd image store the loaded image id may not equal the config digest, in which case
   the tool stops. Use `pull` (the default) until one supervised trial has been observed.
4. Installing changed Compose files or host units on the host is not automated: preflight
   refuses when the installed files differ from the manifest. Mongo, GoldTier egress and
   firewall changes are plan-and-document only.
4a. Host paths (`/opt/clm`, `/etc/clm/compose.env`, `/etc/clm/mongo.uri`, `/run/lock`) are
   defaults taken from the Approval B scripts. No tracked runbook names `/etc/clm/mongo.uri`;
   `deploy/LIGHTSAIL_RUNTIME.md` says only that the connection setting is injected from the
   approved secret source. The operator configuration can override every path, and `--execute`
   refuses to start until it states `mongo_uri_file`. **The tool never creates that file. If
   the host does not have one, that is an owner decision about where a database credential may
   rest, not something to work around.**
4b. A record is written on every exit path Python can catch, including an interrupt during
   failure handling or rollback. It is **not** written when the process dies with no handler
   (SIGKILL, power loss, machine failure). During a rollback the `ROLLBACK_IN_PROGRESS` record
   is already on disk, so the last record is still truthful. During the deployment itself
   (before any rollback) such a death leaves the previous result, or none. Recovery is then by
   hand (runbook section 7).
4d. `recover` verifies only what the mock-tested reads can show: the pins in `compose.env`,
   each container's image id and health, and the public requests. It does not prove that a
   backend that was briefly replaced wrote nothing; that judgement stays with the owner.
4e. If the approval expires between the ingress stop and the backend recreate, the run ends
   `FAILED_HELD` with the site down and the old backend untouched: expiry stops execution and
   nothing restarts ingress. The start-of-run check that enough of the window is left makes
   this unlikely; the owner should know the window exists before a backend release.
4f. The Docker-socket invariant matches the text `docker.sock`. A bind of its parent directory
   or of another runtime socket is refused only as an undeclared change; an explicit
   declaration approved by the owner would let it through.
4c. A client-side SSH timeout is reported as a failure while the remote command may still be
   running. The record will say `FAILED_HELD` or `FAILED_NO_CHANGE` from what the tool saw;
   check the host before acting.
5. The backup check counts recent files in a configured directory; it does not verify an
   archive's content.
6. The backend sequence stops ingress during the swap, so the site is briefly down. Whether
   the assistant should also be stopped during a backend swap is not stated in the runbooks;
   the toolchain leaves it running. Owner decision before the first backend release.
7. Smoke requests are unauthenticated status checks. Signed-in checks stay in the owner's
   browser acceptance.
