# Single-host Lightsail demo runtime

Use the base Compose file and the same-host Mongo overlay together. The overlay adds a TLS-only MongoDB service on an internal Docker network with no published ports. Only Caddy publishes ports. Mongo uses a pre-created external named volume, so Compose fails if that volume is absent and does not remove it on teardown. The app still runs as one staging writer with Mock ACRA and GoldTier, Sandbox writes disabled, and local OCR. Use synthetic data only.

## Host and files

After owner authorization, use one Sydney Ubuntu 24.04 AMD64 Lightsail host. Install Docker Engine and the Compose plugin from Docker's signed Ubuntu APT repository. Confirm `dpkg --print-architecture` reports `amd64`, Docker is enabled on boot, and Compose is at least v2.30. Limit Docker and sudo access to the designated operator. [Docker Ubuntu installation](https://docs.docker.com/engine/install/ubuntu/)

Attach the approved static IPv4. Point the approved hostname's A record at it. Permit TCP 80 and 443 for Caddy and TCP 22 only from the approved operator CIDR and public key. Check the IPv6 firewall separately if enabled. Leave ports 8000 and 27017 unpublished. Verify DNS and public HTTPS before the demo. [Lightsail firewall guidance](https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-firewall-and-port-mappings-in-amazon-lightsail.html)

Keep the reviewed Compose files under `/opt/clm`. Put the non-secret interpolation file at `/etc/clm/compose.env`. Set `BACKEND_IMAGE` and `FRONTEND_IMAGE` to the approved AMD64 registry digests, `CLM_SITE` to the approved hostname, `BACKEND_ENV_FILE` to the protected external runtime file, and `MONGO_CA_FILE`, `MONGO_SERVER_PEM`, and `MONGO_DATA_VOLUME` to the designated host paths and volume name. Authenticate to the approved registry with least-privilege pull access. Keep the exact HTTPS origin and temporary synthetic scrypt hashes in the protected backend file. Inject `MONGO_URI` into the operator process from the approved secret source. Use the restricted app user, host `mongo`, database and authentication source `clm_staging`, TLS enabled, and CA path `/run/clm/mongo-ca.pem`. Percent-encode credentials and keep the connection setting out of command arguments and logs. Use `config --quiet` for validation.

Provision a CA-signed Mongo server certificate with DNS SANs `mongo` and `localhost` for app and operator connections. Keep the CA signing key offline. Mount the public CA and the server certificate/key bundle from outside the checkout. Restrict the server bundle to the Mongo process (UID 999 for the pinned image, mode 0600). Make only the public CA readable by the backend. The server requires TLS and uses SCRAM password authentication over it. Client certificates are optional, and server certificate and hostname validation remain required. [MongoDB TLS configuration](https://www.mongodb.com/docs/manual/core/tls/configure-server-tls-tutorial/)

## Initial provisioning and startup

Create the designated external volume once for a new installation with `docker volume create` and the approved name, and record its name and inspect its identity before each startup. If an expected volume is absent, stop and recover it. Preserve the external volume and Caddy volumes on app replacement. Use the same Compose project on the single designated host.

```sh
cd /opt/clm
dc() {
  docker compose --env-file /etc/clm/compose.env -f deploy/compose.yml -f deploy/compose.mongo.yml "$@"
}
dc config --quiet
dc pull
dc up -d --no-build --wait mongo
dc exec mongo mongosh --quiet --host localhost --tls --tlsCAFile /run/clm/mongo-ca.pem
```

On a confirmed fresh volume, use the localhost exception once in that shell to create a credential-management user in `admin` with `userAdminAnyDatabase` on `admin` for credential provisioning only. Use `passwordPrompt()` and approved secret handling. Authenticate as that user and create the separate `clm_app` identity in `clm_staging` with only `readWrite` on that database. The backend uses the app identity. Existing volumes retain users and data across restart. A failed login on an existing volume calls for checking the selected volume and credentials before any bootstrap step. The localhost exception closes when the first user is created. [MongoDB localhost exception](https://www.mongodb.com/docs/manual/core/localhost-exception/)

Run `dc up -d --no-build --wait` after user provisioning. Verify only the approved Caddy ports are bound, one backend is running, the staging profile and HTTPS login work, and a synthetic case reaches its expected status. For a controlled shutdown run `dc stop frontend`, then `dc stop backend`, then `dc stop mongo`, keeping the volumes. For app replacement stop ingress and the old backend before starting the new one. On the authorized host, rehearse a VM restart and confirm Mongo retains the case and target ledger, exactly one backend resumes, and RM login works again. Use the accepted digest pair and compatible config for rollback.

## Quiesced export and recovery

For a bounded synthetic-demo backup, stop ingress and the backend before exporting so the database and target ledger are at one point in time. Use a protected host backup directory and a timestamped archive. With the scoped database account and password prompt, run:

On the gated staging host, close any ACRA lease first (see "Gated staging host" below).

```sh
dc stop frontend backend
dc exec mongo mongodump --host localhost --ssl --sslCAFile /run/clm/mongo-ca.pem \
  --username clm_app --authenticationDatabase clm_staging --db clm_staging \
  --gzip --archive=/tmp/clm-demo.archive.gz
```

Copy the archive out with `dc cp` to the protected directory, restrict its permissions, record a SHA-256, and remove the temporary container copy. Keep the latest verified archive and the previous known-good one. Start the app only after the export and its verification are complete.

For recovery, keep ingress and the backend stopped and run `dc stop mongo`. Preserve the original volume. Set `MONGO_DATA_VOLUME` to a newly created external recovery volume and run `dc up -d --no-build --wait mongo`. Confirm the mounted volume, bootstrap its users, and verify that it has no case or ledger data before import. Verify the archive checksum and that no target operations occurred after its backup boundary. If that boundary cannot be proved, keep the app stopped pending ledger reconciliation. Using the credential-management account on the recovery volume, create a temporary operator in `admin` with the built-in `restore` role. Copy the archive to the Mongo container and run the restore against the recovery volume.

```sh
dc exec mongo mongorestore --host localhost --ssl --sslCAFile /run/clm/mongo-ca.pem \
  --username clm_restore --authenticationDatabase admin --nsInclude 'clm_staging.*' \
  --gzip --archive=/tmp/clm-demo.archive.gz --stopOnError
```

Remove the container copy and drop the temporary restore user after import. Check the recovered case status and ledger before resuming the demo. Retain the original volume until the recovery is accepted. The export contains synthetic case data and excludes users. Keep the identity provisioning material separate. [MongoDB Database Tools](https://www.mongodb.com/docs/database-tools/mongodump/)

## Optional AI Assistant

The assistant is an optional, private, model-free service defined in the separate overlay `apps/assistant/deploy/compose.assistant.yml`. Remote inference stays disabled: the overlay points the model client at a closed local port and no provider key is configured. The `dc()` helper above never includes the overlay. `dc config`, `dc up`, `dc stop` and the recovery commands therefore behave exactly as in the OP-4 baseline, and no `dc` command can create or start the assistant. Only the frontend image decides whether the route exists. Use the separate `dca()` helper only for the assistant commands below, always naming the `assistant` service.

```sh
dca() {
  dc -f apps/assistant/deploy/compose.assistant.yml "$@"
}
```

Dashboard AI insights (PR #178) are refused by the hosted assistant (503 `DASHBOARD_INSIGHTS_UNAVAILABLE`); no model writes them on this host. c2 (D-130 amendment, DRAFT, disabled): a fifth hosted Claude path for insights is prepared but off (`config.HOSTED_INSIGHTS_DECISION = None`); while it is off every insights route stays refused. When a reviewed change enables it, only `GET .../insights/mode` and an explicit `POST .../insights/generate` (server-derived counts and labels from R2.1-eligible cases, 3 per user and 10 site-wide per Singapore day) are allowed; the merged route stays refused.

Users reach the assistant only when two things are both true: the assistant is running, and the frontend image's Caddyfile routes `/api/assistant/*` to it. The OP-4 frontend answers every assistant route with a fixed 503. The R2 frontend returns the same 503 while the assistant is absent or stopped. Assistant startup and route activation are separate operations, and each needs its own owner approval.

### Preflight (no service change)

Do this after the reviewed files are on the host and before any other `dca` command.

1. Append `ASSISTANT_IMAGE` (the approved AMD64 registry digest), `ASSISTANT_BROWSER_ORIGIN` (equal to the backend's `PHASE13_BROWSER_ORIGIN`) and `ASSISTANT_DATA_VOLUME` to `/etc/clm/compose.env`. Leave `FRONTEND_IMAGE` at the OP-4 digest. `dc` ignores these values.
2. Create the assistant volume once with `docker volume create` and the approved name, then run `docker volume inspect` on it. Compose validation does not check that an external volume exists.
3. Run `dc config --quiet` and then `dca config --quiet`. Both must pass. `dca config` fails until all three values are set. From the R2.1 overlay on, it also needs the RD-1 values `ASSISTANT_ELIGIBLE_CASE_REFS` and `ASSISTANT_ELIGIBLE_CREATED_BEFORE` (see `apps/assistant/deploy/RELEASE_HANDOFF.md`).
4. Confirm that `dca config` shows the assistant on the `proxy` network only, at `CLM_ASSISTANT_PROXY_IPV4`, with no published port.
5. Run `dca pull assistant`.

### Assistant startup (owner approval A)

Confirm with `dc ps` that the backend is healthy. With the OP-4 frontend still serving, run the
following. This is the first install, before the assistant gate; on the gated staging host see
"Gated staging host" below.

```sh
dca up -d --no-build --no-deps --wait assistant
```

`--no-deps` leaves Mongo, the backend and Caddy untouched; confirm their container IDs are unchanged. Compose attaches the assistant to the existing `proxy` network without recreating it, so the Caddy and backend addresses and the forwarded-header trust stay as they are. Users still receive the fixed 503, because the OP-4 Caddyfile has no assistant route. Check readiness and isolation as described in `apps/assistant/deploy/RELEASE_HANDOFF.md`.

### Route activation (owner approval B)

Request this approval only after the owner has confirmed that every hosted case is eligible for the assistant and the idle resource check has passed. Set `FRONTEND_IMAGE` to the reviewed R2 frontend digest and run:

```sh
dc up -d --no-build --no-deps --wait frontend
```

This is the only user-visible change. Run the load and acceptance checks afterwards.

### R2.1 assistant update (separate owner approval)

On the gated staging host, every assistant stop, start and recreate below follows "Gated staging
host" instead.

The RD-1 case gate limits the assistant to an exact owner-approved list of existing synthetic Mock ACRA cases created before a fixed UTC cutoff; every other case gets a 403 before anything is written. It is an assistant-only change: back up `compose.env`, add the two RD-1 values, set `ASSISTANT_IMAGE` to the reviewed R2.1 digest, install the reviewed overlay (keep the previous one), run `dca config --quiet`, then `dca up -d --no-build --no-deps --wait assistant`. The steps, acceptance and rollback are in `apps/assistant/deploy/RELEASE_HANDOFF.md`. Do not run an ACRA window that can create cases before R2.1 is accepted; if one must run, stop the assistant for the whole window.

### Operating alongside the CLM stack

- Once the assistant is running, `dc` reports it as an orphan container. That is expected. Never pass `--remove-orphans` to `dc`, and never run `dc down` or `dca down`. Use `stop`.
- **On the gated staging host, the next two items are superseded by "Gated staging host" below.** There the assistant is stopped and started only through its gate, Docker never restarts it, and any ACRA lease is closed first.
- For a controlled shutdown run `dc stop frontend`, then `dca stop assistant`, then `dc stop backend`, then `dc stop mongo`. Start in the reverse order: Mongo, the backend, `dca start assistant` after the backend is healthy (only if the assistant was approved and running), then the frontend. Without the gate's provider overlay the restart policy is `unless-stopped`: Docker restarts a running assistant after a host reboot, and a stopped assistant stays stopped.
- For the Mongo export above, run `dca stop assistant` before stopping the backend. Start the assistant again only after the backend is healthy.
- The assistant's own backup, restore and acceptance steps are in `apps/assistant/deploy/RELEASE_HANDOFF.md` and also use `dca`.

### Rollback

Each step keeps the OP-4 baseline and the assistant volume. On the gated staging host, stop
and recreate the assistant only as "Gated staging host" below says: never a bare `dca stop`,
and never `dca rm -s -f` followed by a plain `up`.

1. Fastest: `dca stop assistant`. Every assistant route returns the fixed 503, and onboarding is unaffected.
2. Remove the route: set `FRONTEND_IMAGE` back to the OP-4 digest and run `dc up -d --no-build --no-deps --wait frontend`.
3. Remove the container: `dca rm -s -f assistant`. Compose never removes an external volume. Never run `docker volume rm` on it or `down -v`. A newer image may have upgraded a store, so check compatibility before pointing an older image at the volume.

The `ASSISTANT_*` values may stay in `compose.env`, because `dc` ignores them. The `dc()` helper is never changed.

## Gated staging host: restarts with the assistant gate and the ACRA lease

On the staging host, two controls change how services may be stopped, started and recreated.
**This section governs wherever it differs from any other command in this file (above or below) or in other runbooks**, including the `dca` assistant operations named after the G3b cutover below.
- The exact host wrapper definitions and lease controller commands are held by the host operator
  (AWS lane), not in this repository.
- Every host change needs the owner's dated written authorisation, given directly to that operator.

**The assistant gate (R2.2, `apps/assistant/deploy/egress/README.md`).**
- **Restart policy.** The assistant's restart policy is `no`. It is set by
  `compose.assistant-provider.yml`, which overrides `unless-stopped` in `compose.assistant.yml`.
  - Any assistant wrapper on this host must include the provider overlay, plus the OpenRouter
    and combined (`compose.assistant-both.yml`) overlays where they are installed.
  - The plain `dca()` above includes neither.
- **Stop** only with `systemctl stop clm-r22-assistant`.
- **Start** only with `systemctl restart clm-r22-assistant`. A `start` on the active oneshot gate
  does nothing.
- **Never** `dca stop`, `dca start`, `docker start`, or any `up` that starts the assistant.
- **Recreate** with the assistant's host wrapper: `up -d --no-build --no-deps --no-start
  --force-recreate assistant`, then `systemctl restart clm-r22-assistant`. Never use `rm -s -f`
  followed by a plain `up`.
- **Every stop drops the in-memory provider session keys,** and HR enters them again. Do not stop
  the assistant for a backend restart.
- **After a host reboot** the enabled gate unit starts the assistant. Docker does not.

**The ACRA lease.**
- **While a lease is open, the lease controller owns the backend** and adds the ACRA overlay.
  While it is open, never stop, recreate, release or roll back the backend, and never recreate the
  assistant. Any of these trips the lease watcher, which closes the lease, and the close's
  container check can then fail.
- **Close the lease first**, through the lease controller, before any of these:
  - a backend stop, recreate, release, rollback or by-hand restore
  - an assistant recreate
  - a D-137 write window

  Reopen it afterwards only through its own procedure. The close and the reopen each recreate the
  backend, so its container id changes.
- **With the lease closed**, restore the backend with either the lease controller's own backend
  command (the base, Mongo, assistant and GoldTier egress files) or `dcg`. The host operator
  verified on 2026-11-17 that both render an identical backend service, and that `dcgw`
  matches the controller's command plus the write-window file.
  - **Never use `dc`.** It lacks the GoldTier egress overlay.
  - **Never pass `--remove-orphans`.** A `dcg` `up` reports the assistant as an orphan.
  - **Re-verify the equivalence** (render the backend service with each file set) after any
    change to a host compose file.
- **D-137 GoldTier write windows and ACRA leases are mutually exclusive.** This is the
  owner-approved operating rule of 2026-11-17. Close the lease before opening a window, and
  reopen it only after the window has closed. No wrapper combines the write overlay with the
  ACRA overlay.

**Recover-by-hand start order:**
1. Close the lease.
2. Start Mongo.
3. Start the GoldTier DNS and egress sidecars, then run the R3 firewall verifier.
4. Start the backend, with the lease controller's backend command or `dcg`. Never use `dc`.
5. Start the assistant through its gate. Its firewall and watch units must be active.
6. Start the frontend, with `dc`.
7. Reopen the lease last.

## Cost and release gate

Confirm the exact bundle and credit eligibility immediately before launch, set an approved cost alert, and check available credit and usage during the demo. Record a teardown date and confirm that the instance and any detached static IP are accounted for. This overlay requires applicable acceptance and independent review. Follow the separate source and image publication approvals before transferring digest-pinned images or launching the host.

## R3 GoldTier secure egress (D-127; G3 only, not yet authorised)

The egress overlay is never part of `dc()` or `dca()`. A separate helper applies it last:

```sh
dcg() {
  dc -f deploy/compose.goldtier-egress.yml "$@"
}
```

After the G3b cutover, backend and egress operations use `dcg`; assistant operations keep
`dca ... --no-deps assistant`. Prerequisites (G3a): `/etc/clm/r3/clm_r3.nft`, the two units in
`deploy/egress/host/`, and `verify_host_firewall.sh` passing. `compose.env` must set
`CLM_GOLDTIER_EGRESS_FQDN` and `CLM_GOLDTIER_EGRESS_DST_V4`, the R-1 pinned IPv4 set. The second
must equal `GOLDTIER_DST_V4` in `/etc/clm/r3/clm_r3.vars`; the verify script compares it with
the running proxy. Never enable `nftables.service`
or ufw, and never run `iptables-legacy` on the host (facts SE-1). The R3 containers stay stopped
after the watcher acts; start them only after the table is restored and verified.

## D-137 GoldTier Sandbox write window (PROPOSED; each window needs owner authorisation)

The window overlay is never part of `dc()`, `dca()` or `dcg()`. It is applied only for one
owner-authorised window, after the R3 overlay, through its own helper:

```sh
dcgw() {
  docker compose --env-file /etc/clm/compose.env --env-file /etc/clm/goldtier-write-window.env \
    -f deploy/compose.yml -f deploy/compose.mongo.yml \
    -f deploy/compose.goldtier-egress.yml -f deploy/compose.goldtier-write-window.yml "$@"
}
```

`/etc/clm/goldtier-write-window.env` (root-owned, mode 600, created for the window and removed
when it closes) holds exactly three lines:
`CLM_GOLDTIER_WRITE_OPERATIONS`, `CLM_GOLDTIER_WRITE_CASE_REFERENCES` (exact `source_case_id`
values) and `CLM_GOLDTIER_WRITES_NOT_AFTER` (time-zoned, at most 24 hours ahead). It holds no
secret. The overlay changes only the backend's four write values. No other service, network,
port, volume or image changes.

Preconditions: GoldTier mode is Sandbox (`CLM_GOLDTIER_CONNECTOR_MODE`), `verify_host_firewall.sh`
passes, every item D-137 lists before a window is met, and **no ACRA lease is open**. No wrapper
combines the write overlay with the ACRA overlay, so close the lease first and reopen it only
after the window has closed ("Gated staging host" above). Write windows and ACRA leases are
mutually exclusive: this is the owner-approved operating rule of 2026-11-17.

- Open: confirm `grep -c '^CLM_GOLDTIER_WRITE_' /etc/clm/compose.env` prints `0` and the shell
  exports no `CLM_GOLDTIER_WRITE_*` variable. Then run `dcgw config --quiet` and
  `dcgw up -d --no-build --no-deps --wait backend`. The HR console status must show
  `writes_enabled: true`. Confirm the three window values from the backend container's
  environment filtered to `^GOLDTIER_SANDBOX_WRITE` only, never a full environment or `config`
  render. The backend refuses to start on an incomplete window.
- Close (also at the end time, and after any stop condition):
  `dcg up -d --no-build --no-deps --wait backend`, then remove the window env file. The HR
  console status must show writes disabled. Record each write's ledger outcome and readback.
- Never use `dc` or `dca` for the backend. While a window is open, the release pipeline's drift
  check refuses any deployment, so run no pipeline release until the window is closed.

## ST-7 GoldTier Sandbox daily read budget

An unset `GOLDTIER_SANDBOX_DAILY_READ_LIMIT` means no application read limit
in any environment. Provider limits still apply. An explicit setting from 0 to
500 caps reads per UTC day. A claim consumes one slot before an outbound Search,
including exact-ID readback and recheck. Failed outbound requests still consume
that slot. Mongo stores the count across restarts only when a cap is configured.
An exhausted or unavailable configured budget refuses outbound reads. For configured
Sandbox, null limit and usage fields in the HR status mean no application read limit.

This limit governs the existing Sandbox read path under D-126 provenance
checks and D-131 egress controls. D-137 continues to govern writes and their
ledger ordering. A staging limit above zero requires separate owner
authorization. ST-7 implementation tests use synthetic transport.
