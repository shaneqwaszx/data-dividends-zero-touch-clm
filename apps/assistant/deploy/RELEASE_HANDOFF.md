# AI Assistant Stage A: release owner handoff

Stage A hosts the existing assistant as a private service with no model and no paid
dependency. It is a deployment candidate, not a deployment. Nothing here has run on AWS, and
Stage B (remote models) is a separate decision, not approved and not part of this candidate.

Evidence class: Local (Docker on a development machine, Mock ACRA and Mock GoldTier).

## Architecture

```
Browser ──HTTPS──▶ Caddy ──▶ forward_auth ──▶ backend GET /api/auth/me
                     │          (401 stops here)
                     │  /api/assistant/* → /assistant/*
                     ▼
              assistant:8100 ──GET, user's own session──▶ backend
              (proxy network only: no published port, no route to the internet)
                     │
                     ▼
              /data volume: knowledge SQLite, Chroma, model state and audit
```

| Layer | Control |
|---|---|
| Caddy | Caps the request body at 512,000 bytes before anything else (Caddy's `512KB` is decimal), needs a live session (`forward_auth`), streams without buffering, and returns a fixed 503 when the assistant is down |
| `HostedGuard` | Serves only `/assistant/*`, keeps `/internal/*` to loopback, needs a session cookie, needs one allowed Origin on unsafe methods, and refuses provider and paid console actions before reading the body |
| Backend | The only authority on identity, role, team and case access. The assistant forwards the user's own session and only sends `GET` |
| Docker | Non-root, read-only root filesystem, all capabilities dropped, one internal network, and CPU, memory, PID and log limits |
| `refusals()` | The service will not start if any remote decision, provider key, proxy setting, `.env` file, loopback backend URL or local origin is present, or if the RD-1 case list or cutoff is missing or malformed |
| RD-1 case gate (R2.1) | Serves only an exact owner-approved list of existing synthetic Mock ACRA cases, created before a fixed UTC cutoff. It runs after the backend has allowed the read, so 401 and 404 are unchanged. Any other case gets `403 ASSISTANT_CASE_NOT_ELIGIBLE` before anything is written. This is a bounded POC rule, not a general provenance check: the browser summary cannot tell Mock ACRA from ACRA Marketplace Mock |

No model means every question gets the deterministic case-data answer. The baseline points at
the container's own discard port, so model calls fail at once and the existing fallback
answers. Model management needs a baseline to open its state and audit store.

**A working deterministic assistant is not an LLM-powered assistant.** In this candidate every
answer is `answered_by=case_data` with `model=null` and the notice "The AI model is not available,
so this answer comes straight from the case data." Hosted health reports `llm_enabled=false` and
`model=null`. LLM inference is disabled and has not been verified in any form. The smoke's
"mock provider" step is a scripted local HTTP server inside the container. It exercises the
output checks; it is not inference, and its reply was rejected.

## Phase A1 local evidence

Evidence class: **Local**. Docker on a development machine (32 CPUs, 15.5 GiB for Docker), the
release-line images built from `149c11e`, Mock ACRA and Mock GoldTier, synthetic users, a
throwaway Mongo. **AWS deployment is not authorised and has not been verified.** Nothing here
has run on Lightsail.

| Check | Result |
|---|---|
| Docker smoke (`smoke_hosted.py`) | 16 of 16 steps pass, including the corrected body-limit step below |
| Real browser through Caddy (Chromium, Playwright) | 13 of 13 checks pass: the RM panel streams a case-data answer with the notice, another team's RM gets a 404 that names no company, and the HR console loads with no "not configured" banner, `configured=true`, file status `ok`, the baseline active and every other profile not selectable |
| `tests/test_hosting.py` | 158 tests: 155 pass, 3 skipped (the two backup symlink cases need symlink privilege on Windows, and the read-only-destination case needs POSIX permissions; the same cases pass inside the Linux image). This includes 24 backup-integrity and body-limit tests, 8 backup-path tests, 13 staged-restore tests with injected copy, promotion and rollback failures, and 8 restore exit-code tests (staging folder not created, I/O error in the final check with and without a working rollback) |
| Full assistant suite | 3,740 passed, 26 skipped, 16 failed. 14 failures are this Windows host running out of file handles (`Errno 24`); their files pass when run alone. 1 (`test_the_boundary_file_is_current`) also fails on an untouched copy of `149c11e`, so it is a defect already on `main` and reads no file in this candidate. 1 (`test_retrieval.py::test_an_entry_the_user_may_not_see_is_never_retrieved`) was a Chroma "Nothing found on disk" error seen only in this run; the file passed 3 of 3 runs alone and reads no candidate file. Two skips are the backup symlink cases, which need symlink privilege on Windows |
| Backup and restore in the image (Linux) | 19 of 19 checks: backups under folders named `stores` verify and restore, a moved backup verifies and a tampered one is refused. Restore succeeds and leaves no staging folder; staging is mode 0700. A source changed after verification, a copy error, a failed first promotion and a failed later promotion each leave the volume empty. A failed rollback reports `INCOMPLETE`, keeps the partial contents, and a retry refuses it. An entry that appears during promotion is never overwritten. Stale staging, a non-empty volume, a symlink in the backup, a symlinked destination and a traversing manifest are refused. The earlier 14 integrity checks still pass. 6 of 6 exit-code checks: a real read-only volume is refused with exit 2 and no traceback (also through the command line), an I/O error in the final check is rolled back with exit 2, the same with a failed rollback gives exit 3 and keeps the contents, a final-check mismatch is kept with exit 3, and a normal restore still succeeds |

**Body limit.** Earlier smoke runs sent a 600,000-character message and accepted any non-200
outcome. The assistant refuses messages over 4,000 characters with its own 422, so that step
passed with or without Caddy's cap. **No earlier run is valid evidence for the body limit.** The
corrected step sends a short valid question plus an unknown field, padded to an exact size,
and requires all of the following. Any other outcome, connection error or timeout fails it:

| Request | Required result |
|---|---|
| 512,000 bytes through Caddy, declared length and chunked | The assistant's own 422 for the unknown field, so the body passed Caddy |
| 512,001 bytes through Caddy, declared length (`Expect: 100-continue`) | 413 from Caddy before any body byte is sent, with no assistant reply |
| 512,001 bytes through Caddy, chunked | 413, with no assistant reply |
| 512,001 bytes sent straight to the assistant inside its container | The assistant's own 422, never 413, so the 413 can only be Caddy's |

With the cap removed from the Caddyfile, or raised to 1 MB, the step fails ("expected 413, got
422"). `test_hosting.py` also pins `max_size 512KB`, its place before `forward_auth`, and the
smoke's 512,000-byte constant.

**Load** (`load.py`, client pinned to IPv4: on Windows a `localhost` connection otherwise pays
about 2 s for a refused `::1` attempt). Every answer was `case_data` with no model.

| Concurrent requests | Requests | Answered | p50 | p95 |
|---|---|---|---|---|
| 1 | 10 | 10 | 0.22 s | 0.24 s |
| 8 | 120 | 120 | 1.91 s | 2.73 s |
| 32 | 160 | 87, 73 refused with 503 at the concurrency cap | 12.9 s | 13.4 s |

During the run the assistant peaked at 198 MiB of its 512 MiB and at 96% CPU against its 0.75
limit. The four containers together peaked at 979 MiB (Caddy 37, backend 200, Mongo 578,
assistant 198). No container restarted or was killed for memory. At 32 concurrent requests the
CPU limit, not memory, is the bottleneck, and refusals start before 32 client requests.

## Changes to shared files

Apply these in a release assignment. None of them is made here.

### `deploy/Caddyfile`

Replace the `@assistant` handler and add `handle_errors`. A test holds
[Caddyfile.candidate](Caddyfile.candidate) equal to the shared file apart from these lines.

```diff
     @assistant path /api/assistant /api/assistant/*
     handle @assistant {
-        respond "Assistant service is unavailable in this deployment." 503
+        route {
+            request_body {
+                max_size 512KB
+            }
+            forward_auth clm-backend-proxy:8000 {
+                uri /api/auth/me
+            }
+            uri strip_prefix /api
+            reverse_proxy clm-assistant-proxy:8100 {
+                flush_interval -1
+            }
+        }
     }

+    handle_errors 502 503 504 {
+        @assistant_down path /api/assistant /api/assistant/*
+        respond @assistant_down "Assistant service is unavailable in this deployment." 503
+    }
+
     @api path /api /api/* /health
```

- The `route` block fixes the order. Without it Caddy's default directive order applies.
- `flush_interval -1` is required. Answers stream as NDJSON, which Caddy does not flush by
  default.
- Caddy resolves the upstream per request, so this file is safe to ship before the assistant
  exists. Requests then return the same 503 as today, for signed-in users.
- Signed-out `/api/assistant/*` requests change from 503 to 401.
- `handle_errors` with status arguments needs Caddy 2.8 or later. The smoke ran on v2.11.9.
  `deploy/frontend.Dockerfile` uses the floating `caddy:2-alpine` tag, so pin the tested version.

### `deploy/compose.yml`

No change needed. The `/29` proxy subnet has room for `172.30.240.4`. If you changed
`CLM_PROXY_SUBNET`, set `CLM_ASSISTANT_PROXY_IPV4` in the same interpolation file.

### Documents

| File | Change |
|---|---|
| `deploy/README.md` | Drop "The AI Assistant is excluded" and link here |
| `deploy/README.md` | "keep the proxy network exclusive to Caddy and the backend" must now include the assistant. Forwarded headers stay trusted only from Caddy's address |
| `deploy/LIGHTSAIL_RUNTIME.md` | Keep the `dc()` helper unchanged and add a separate `dca()` assistant helper, the separately approved startup and route activation, and the ordered stop, backup, restart and rollback steps |
| `docs/PROJECT_STATE.md` | Record the hosted assistant only once it has actually been deployed |

`deploy/smoke.py` needs no change: it signs in before asserting the 503, which still holds with
no assistant running.

### CI

`.github/workflows` runs Ruff and mypy on `ai_assistant assistant_eval tests scripts`. Add
`assistant_hosting` to both commands. `tests/test_hosting.py` is already collected.

## Build

From the repository root, with BuildKit, which reads
`assistant.Dockerfile.dockerignore` instead of the shared `.dockerignore`:

```sh
docker build --platform linux/amd64 -f apps/assistant/deploy/assistant.Dockerfile -t clm-assistant:RELEASE .
```

The base image is pinned by digest and every dependency by `requirements.lock`. The image is
586 MB. Push it to the approved registry and record its digest.

## Host preparation

Add to `/etc/clm/compose.env`:

```sh
ASSISTANT_IMAGE=<registry>/clm-assistant@sha256:<digest>
ASSISTANT_BROWSER_ORIGIN=https://<approved hostname>
ASSISTANT_DATA_VOLUME=clm-staging-assistant-data
ASSISTANT_ELIGIBLE_CASE_REFS=<comma list of approved 12-hex case references>
ASSISTANT_ELIGIBLE_CREATED_BEFORE=<approved UTC cutoff, for example 2026-11-12T05:07:25Z>
```

A case reference is the first 12 hex characters of the SHA-256 of the server case id (lowercase,
hyphenated UUID). The cutoff must end in `Z` or `+00:00`. Both values are required, with no
fallback value. Use only values the owner approved for the release, after the historical ACRA
mode and the creation boundary are verified on the host.

`ASSISTANT_BROWSER_ORIGIN` must equal the backend's `PHASE13_BROWSER_ORIGIN` exactly. Optional
values and their defaults are `ASSISTANT_CPUS=0.75`, `ASSISTANT_MEM_LIMIT=512m`,
`ASSISTANT_DATA_QUOTA_MB=2048` and `ASSISTANT_SEED_SYNTHETIC=false`.

A plain Docker volume has no size limit. To make the storage bound hard, back the volume with a
fixed-size file. Size it to the quota:

```sh
sudo install -d -m 0755 /var/lib/clm
sudo truncate -s 2G /var/lib/clm/assistant-data.img
sudo mkfs.ext4 -q /var/lib/clm/assistant-data.img
sudo install -d /mnt/clm-assistant-data
echo '/var/lib/clm/assistant-data.img /mnt/clm-assistant-data ext4 loop,nodev,nosuid,noexec 0 2' | sudo tee -a /etc/fstab
sudo mount /mnt/clm-assistant-data
sudo chown 10001:10001 /mnt/clm-assistant-data
docker volume create --driver local --opt type=none --opt o=bind --opt device=/mnt/clm-assistant-data clm-staging-assistant-data
```

These loop-mount steps were not run in the local smoke, which used a plain named volume.
Rehearse them on the host. For a plain volume, use `docker volume create
clm-staging-assistant-data`. Compose fails if the volume is absent and never removes it.

## Deploy

Keep the runbook's `dc()` helper unchanged. Follow **Optional AI Assistant** in
`deploy/LIGHTSAIL_RUNTIME.md`: preflight, then assistant startup and route activation as two
separately approved operations. Every assistant command in this handoff uses its `dca()` helper.

```sh
dca() {
  dc -f apps/assistant/deploy/compose.assistant.yml "$@"
}
dc config --quiet
dca config --quiet
dca pull assistant
dca up -d --no-build --no-deps --wait assistant   # approval A; the OP-4 frontend still returns 503
# approval B, after data eligibility: set FRONTEND_IMAGE to the R2 frontend digest
dc up -d --no-build --no-deps --wait frontend
```

Expect one `BOOTSTRAP` line in the logs and `guidance_added: 9` on a new volume.

### Exit codes

| Code | Meaning | Action |
|---|---|---|
| 78 | `REFUSED <codes>`: configuration refused | Fix the named setting. Never add a key or decision to get past it. `CASE_ELIGIBILITY_REQUIRED` and `CASE_ELIGIBILITY_INVALID` name the RD-1 list and cutoff |
| 75 | `REFUSED DATA_ROOT_IN_USE`: another writer holds the volume | Stop the other container |
| 70 | `REFUSED STORE_DAMAGED <store>` | Restore from a backup. Nothing is repaired automatically |

Dashboard AI insights (PR #178): On the hosted AWS deployment the assistant refuses this route (503 `DASHBOARD_INSIGHTS_UNAVAILABLE`, at the hosting boundary and in the route), so no model writes insights there and the panel stays hidden. After deployment, check that `POST /api/assistant/dashboard/insights` answers 503 `DASHBOARD_INSIGHTS_UNAVAILABLE`.

## Verify after deployment

1. `dca exec assistant python -c "import urllib.request as u; print(u.urlopen('http://127.0.0.1:8100/internal/ready').read().decode())"` shows every check `ok`.
2. `ss -tlnp` shows only Caddy's ports, and `dca port assistant 8100` shows no mapping.
3. Signed out, `curl -i https://<host>/api/assistant/health` returns 401.
4. Run the isolation matrix below with synthetic users.
5. In a browser, open the panel on a case and confirm an answer streams with the "model is not
   available" notice. This passed locally in Phase A1 (13 of 13 checks through Caddy); repeat
   it on the host, because local evidence does not cover the deployed path.
6. Sign in as HR, open **AI Models**, and confirm state and audit load. Provider setup actions
   are refused with `HOSTED_REMOTE_DISABLED`. The page does not yet explain that message.

### Auth and case-isolation matrix

| Actor | Action | Expected | Smoke | `test_hosting.py` |
|---|---|---|---|---|
| Signed out | Any assistant route | 401 at Caddy, assistant not reached | Yes | Yes (guard) |
| Expired or revoked session | Case route | 401 | No | Yes |
| RM, own team | Brief, chat, stream | 200, case-data answer | Yes | Yes |
| RM, other team | Brief, chat | Safe 404, no case name | Yes | Yes |
| RM, other team | Another user's answer record | 404 | Yes | Yes |
| HR | Case brief | 404 | Yes | No |
| HR | AI Models, audit | 200 | Yes | Yes |
| RM | AI Models | 403, audited | Yes | Yes |
| HR | Save a provider key | 403, body unread, audited, no key held | Yes | Yes |
| HR | Activate or test a remote model | Refused by existing gates, audited | No | Yes |
| Any | POST with no Origin or another Origin | 403 | Yes | Yes |
| Any | `/internal/*`, `/docs`, `/openapi.json` | 404 | Yes | Yes |
| Any | Body over 512,000 bytes | 413 at Caddy, assistant not reached | Yes | Yes (configuration pinned) |

Add one hosted-only check before release: revoke a session in the backend and confirm the next
assistant call returns 401. The in-process test covers the logic, not the deployed path.

## Persistence and recovery

| Store | Path under `/data` | Source of truth | Recovery |
|---|---|---|---|
| Knowledge, reviews, answer records, conversations | `knowledge/knowledge.sqlite3` | Yes | Backup |
| Chroma index | `knowledge/chroma/` | No, rebuilt from SQLite | Backup, or rebuild once embeddings exist |
| Model state and audit | `models/model_admin.sqlite3` | Yes | Backup |
| Chat contexts, tickets | Memory only | No | Lost on restart by design (D-115). The panel starts a new chat |

Stage A has no ledgers. Answer records expire after 7 days, or 30 days after their request
closes, and audit rows are capped per class, so the data set stays small: about 1.5 MB after the
smoke's 120 answers.

| Failure | Behaviour | Tested |
|---|---|---|
| Restart | Stores kept, guidance not duplicated | Yes |
| Worker crash | Restart policy brings it back | Yes |
| Worker hang | The probe kills it after 9 failed checks, about 90 seconds | Yes |
| Second writer | Exit 75 | Yes |
| Damaged store | Exit 70, file left alone | Offline only |
| Backend down | Readiness reports `clm_backend`, users get a backend error | Offline only |
| Assistant down | Caddy returns the fixed 503, onboarding unaffected | Yes |

Docker keeps retrying a container that exits 70 or 78. Watch for a restart loop after any
change. It costs little, and Caddy returns 503 throughout.

### Backup and restore

Run with the assistant stopped. The tool refuses a store left with a WAL file, which can follow
a crash. Start and cleanly stop the service once to clear it.

```sh
dca stop assistant
dca run --rm --no-deps --user 0:0 -v /var/backups/clm-assistant:/backup assistant \
  python -m assistant_hosting.backup create /data /backup/$(date +%Y%m%dT%H%M%S)
dca up -d --no-build --no-deps --wait assistant
```

`dca run` cannot run while the service holds its fixed address, so stop it first.

`verify` and `restore` accept a backup only if `stores/` holds exactly the files its manifest
names, each with the manifest's recorded size and SHA-256, and every SQLite copy passes an
integrity check. They refuse a missing, extra, changed or substituted file, a symbolic link, a
path that leaves `stores/`, and a malformed or incomplete manifest. Windows directory junctions
are not detected as links, but production runs on Linux and every file is still hash-checked.
The manifest format is unchanged.

**Backup paths.** The manifest records each copy's absolute path at the time of the backup. A
backup folder may since have moved, and folders named `stores` may appear above it, in its own
name or inside the data root. `verify` therefore tries every `.../stores/` cut that all
entries share, and uses the one whose relative paths are exactly the files found under this
backup's own `stores/` folder. Only one cut can match. If none matches, the backup is refused.

**Restore steps.** `restore` writes only into an existing, empty folder: the recovery volume's
mount point.

1. Verify the whole backup.
2. Refuse a destination that is not empty. Hidden leftovers of an earlier attempt count, and
   are never removed automatically.
3. Copy into a new, private (mode 0700), randomly named `.restore-staging-*` folder inside the
   destination, which is on the same filesystem.
4. Check the staged file set, sizes and SHA-256 independently of the source.
5. Promote each top-level entry with a same-filesystem rename, never over an existing entry.
6. Check the destination against the manifest again, then remove the empty staging folder.

`RESTORED` is printed, with exit code 0, only after both pass.

| Outcome | Exit | Destination afterwards |
|---|---|---|
| `RESTORED n files` | 0 | Exactly the backup's files |
| `REFUSED ...` | 2 | As it was before (empty, re-checked), after a controlled failure: a bad backup, a non-empty destination, a staging folder that could not be created (for example a read-only volume), a source changed after verification, a failed staging copy or check, or a promotion or final-check I/O error that was rolled back |
| `INCOMPLETE ...` | 3 | May hold partial contents and the staging folder. Cleanup or rollback could not finish, the destination could not be confirmed empty, the final check found different contents (kept for inspection, not rolled back), or something else wrote into the destination |

OS errors are reported by their errno name only (for example `EACCES`, `EIO`). Any other
unexpected error is not caught: it ends with a traceback and a non-zero exit other than 0, 2
or 3, never with `RESTORED`, and the volume must be inspected as for `INCOMPLETE`.

**Not crash-atomic.** The empty-destination guarantee covers controlled error paths only. A
process or host crash during staging can leave a `.restore-staging-*` folder. A crash during
promotion can leave some entries promoted and the rest in staging. After an `INCOMPLETE` result,
or any interrupted restore, inspect the recovery volume before retrying. A retry refuses a
non-empty volume. Discard that volume and restore into a new one rather than editing it.
Nothing else may write to the recovery volume during a restore.

To restore, never into the existing volume:

```sh
docker volume create clm-staging-assistant-recovery
dca run --rm --no-deps --user 0:0 -v /var/backups/clm-assistant:/backup \
  -v clm-staging-assistant-recovery:/restore assistant \
  python -m assistant_hosting.backup restore /backup/<folder> /restore
docker run --rm --user 0:0 --network none -v clm-staging-assistant-recovery:/restore \
  --entrypoint chown "$ASSISTANT_IMAGE" -R 10001:10001 /restore
```

Run the `chown` step and start the service only after the restore printed `RESTORED`. Set
`ASSISTANT_DATA_VOLUME` to the recovery volume, then run `dca up -d --no-build --no-deps --wait
assistant`. Keep the original volume until the restore is accepted.

## R2.1 assistant update (RD-1 case gate)

A separate owner approval, after approval B. It changes only the assistant image and the two
RD-1 values; the frontend, backend, Mongo and Caddy stay as they are.

1. Back up `/etc/clm/compose.env`. Add the two RD-1 values and set `ASSISTANT_IMAGE` to the
   reviewed R2.1 digest.
2. Install the reviewed overlay, keeping the previous one for rollback. `dca config --quiet` must
   pass. Confirm the frontend, backend and Mongo configuration is unchanged.
3. `dca pull assistant`, then `dca up -d --no-build --no-deps --wait assistant` (same volume).
4. Accept: no `REFUSED` line and readiness `ready`; frontend, backend and Mongo container IDs and
   assistant store row counts unchanged; an approved case answers; an unlisted or newly created
   case shows the not-available message (403 `ASSISTANT_CASE_NOT_ELIGIBLE`); another team still
   gets a 404.

Rollback: restore the `compose.env` backup (the previous `ASSISTANT_IMAGE`) and the previous
overlay, then `dca up -d --no-build --no-deps --wait assistant`. Or stop it: `dca stop assistant`.
The volume is never removed.

## Rollback

1. `dca stop assistant`. Onboarding keeps working and the panel shows the fixed 503.
2. To remove the route, redeploy the previous frontend digest.
3. Keep the volume. A newer image may have upgraded a store, so check compatibility before
   pointing an older image at it.

## Resources

Measured on the local Docker host with the production limits applied: 0.75 CPU, 512 MiB, no
container swap, 128 PIDs. The load figures are in **Phase A1 local evidence** above.

| Measure | Result |
|---|---|
| Assistant idle memory | 88 to 108 MiB |
| Assistant peak memory | 161 MiB at 8 concurrent streams (smoke); 198 MiB at 32 (load) |
| Peak CPU | 80 to 96% of one core as reported by Docker, against the 0.75 limit |
| One answer through Caddy | 0.20 to 0.30 s |
| 120 answers at concurrency 8 (smoke) | p50 1.88 s, p95 2.80 s |
| Cold start to healthy | 23 s for the whole stack |
| Image size | 586 MB |
| Data after the smoke | 1.5 MB |

Those were 32-core host numbers with a CPU quota. Lightsail's burstable 2 vCPU is not the same
hardware, so treat latency as indicative and re-measure on the host.

**O4 checks still open before any deployment** (owner condition; none of these has run):

1. Read current Lightsail RAM, available memory and CPU capacity.
2. Measure combined memory with Caddy, backend, Mongo and the assistant all running.
3. Measure latency and resource use under representative concurrent requests on the host.
4. Confirm a safe memory margin under that load. Less than 500 MiB available is a stop
   condition, not proof that capacity is enough.
5. Confirm the resource limits cause no regression or unexpected termination.

The Mongo cache cap, backend memory limit and host swap file below are planned changes owned by
the release workstream, not part of this candidate. Upgrading the Lightsail bundle needs a
separate owner decision.

Expected memory on the 4 GiB host:

| Component | Measured here | Plan for |
|---|---|---|
| Caddy | 26 MiB | 50 MiB |
| Backend | 145 MiB, no OCR in this run | 512 MiB or more, because Tesseract spikes |
| Mongo | 651 MiB with a small data set | Up to about 1.7 GiB by default |
| Assistant | 165 MiB | 512 MiB hard limit |
| OS and Docker | Not measured | 400 MiB |

That totals about 3.2 GiB against 3.8 GiB usable. It fits, but the margin depends on Mongo.
Mongo sizes its cache from host memory, 50% of (RAM − 1 GiB), and neither Mongo nor the backend
has a memory limit in the shared Compose files. **Recommended for the release owner:** set
`--wiredTigerCacheSizeGB 0.75`, give the backend a `mem_limit`, and add a 1 GiB swap file. Check
live usage with `docker stats` before and after, because the current Lightsail figures were not
read here.

Stage A adds no model or provider cost. The added cost is storage inside the existing bundle and
registry space for one image. Whether it fits the existing instance is decided by the O4 checks
above, on the host.

Local large models do not fit: an 8B model needs about 5 to 6 GiB at Q4 on top of this stack,
and has no GPU here. Local embeddings (`nomic-embed-text`) might fit, but they are out of scope.
Until then, retrieval runs on keywords and case context and reports `degraded`, and the Chroma
index stays empty. This is the same mode the offline evaluation uses.

## Known limits

- **No rate limit per user.** The assistant caps concurrency at 32 and the CPU at 0.75 cores.
  Callers past the cap get a 503. Locally, refusals began before 32 concurrent client requests,
  and at 32 the accepted answers took about 13 s. Each answer also costs the backend about four
  reads, so a heavy assistant user competes with onboarding for the single backend worker.
- **`forward_auth` adds one backend call per request.** That cost is in the figures above.
- **Stored text.** Answer records and rated conversations hold redacted text on an unencrypted
  volume. That is acceptable for synthetic data only.
- **`AI_ASSISTANT_KNOWLEDGE_SINGLE_REVIEWER`** stays at its POC default of `true` (D-083).
- **Qualification is unavailable in this image.** It has no `scripts/qualify_model.py` or
  `assistant_eval`, so the console refuses it. That is deliberate for Stage A.
