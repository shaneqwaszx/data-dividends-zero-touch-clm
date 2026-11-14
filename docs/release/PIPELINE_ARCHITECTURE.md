# Release pipeline architecture

| Field | Value |
|---|---|
| Status | **Implemented and tested locally against mocks. Never run against the Lightsail host or GHCR.** Not installed anywhere. Changes no existing gate |
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
| `deploy/egress/host/verify_host_firewall.sh`, `apps/assistant/deploy/egress/verify_assistant_egress.sh` | Run read-only in preflight when the matching overlay is active |
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
`docker rm`, firewall and power commands), and checks the approval deadline before every host
or registry write. The toolchain has no code path that calls an AI provider; the effect exists
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
it may be automatic and its stop conditions; public smoke expectations; and the previous
known-good manifest.

The manifest hash is the SHA-256 of its canonical JSON. Publication fills in the registry
digests, so the published manifest has a new hash and records the candidate's hash in
`candidate_manifest_sha256`. **The deploy approval is given for the published manifest.**

### 3.3 Approval record

`tools/release/schema/approval-record.schema.json`. Bound to one manifest hash, one exact
service list, one risk class, the actions (`publish`, `deploy`), a start time and an expiry.
Rules enforced in code:

- wrong manifest, wrong services, wrong action or wrong risk class: refused;
- before the start or at/after the expiry: refused; a window longer than 24 hours: refused;
- expiry is checked again before every host or registry write. An expired window stops the run
  before the next change; it is never extended, and no automatic rollback runs after expiry;
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
host bind; capabilities dropped and a read-only root for backend, assistant and the egress
containers; the Mongo and assistant data volumes stay `external` (so Compose can never remove
them).

**Baseline comparison.** `policy/effective-baseline.json` is the reviewed render of every
supported set at the current Compose files. A render that has a network, port, environment
variable or setting the baseline lacks is refused unless the manifest declares it in
`declared_config_changes`, and a declaration raises the risk class (a network, port or setting:
HIGH). A test fails when the Compose files and the baseline disagree, so a Compose change
forces a reviewed baseline update (`release.ps1 baseline --write`, then review the diff).

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
| After a container changed, rollback eligible and approved | `ROLLED_BACK` | `compose.env` restored; services recreated on their previous image, frontend first; verified |
| After a container changed, rollback not eligible | `FAILED_HELD` | **Nothing further is changed.** The record says exactly what is running, and whether ingress is stopped |
| Approval expired during the run | `FAILED_HELD` | Stopped before the next change; no rollback |

Automatic rollback needs all of: the owner approved it in the approval record; the manifest
says `data_compatible: true` and `automatic: true` for every touched service; the previous pin
was recorded. For a backend it additionally needs both schema versions and the target
confirmed on the host. A rollback target that writes an older case-snapshot schema (the
`4c1db49` line, schema 19) can never be marked compatible: the manifest is refused.

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
5. The backup check counts recent files in a configured directory; it does not verify an
   archive's content.
6. The backend sequence stops ingress during the swap, so the site is briefly down. Whether
   the assistant should also be stopped during a backend swap is not stated in the runbooks;
   the toolchain leaves it running. Owner decision before the first backend release.
7. Smoke requests are unauthenticated status checks. Signed-in checks stay in the owner's
   browser acceptance.
