# GoldTier Sandbox readiness for AWS staging

Status: offline preparation. No genuine Sandbox call, GoldTier write or new customer was
made. `GOLDTIER_XPI` stays `PARTIAL / SANDBOX_PARTIAL`. This is not Live evidence. The
decision records are D-126 and D-137 (the bounded write window, owner-approved 2026-11-15, not
active).

## What staging does

| Condition | Behaviour |
|---|---|
| `GOLDTIER_CONNECTOR_MODE=mock` (default) | Unchanged |
| `sandbox`, writes off | Search and exact-ID readback run. Final Review & Send is refused with `CLM_TARGET_WRITES_DISABLED` |
| `GOLDTIER_SANDBOX_ALLOW_WRITES=true` in `APP_ENV=staging` without a complete D-137 window | The backend refuses to start |
| A complete D-137 window: listed operations, 1 to 10 exact case references, an end time at most 24 h ahead | Only those operations, for those cases, until the end time. Everything else is refused before the ledger with `CLM_TARGET_WRITES_DISABLED`, and an ending window pauses in `RECOVERY_PENDING`. The window is applied only through `deploy/compose.goldtier-write-window.yml` (`dcgw`) |
| `sandbox`, identity has no evidence from an accepted source | No provider request is made, for Search or mutation. The case records a failed Search with `CLM_TARGET_REGISTRY_PROVENANCE_UNSUPPORTED`, or `REGISTRY_PROVENANCE_UNSUPPORTED` on a recheck. Existing-customer confirmation and Send are refused |

`ACRA_CONNECTOR_MODE` and `GOLDTIER_CONNECTOR_MODE` stay independent. With local ACRA Mock
and GoldTier Sandbox, the backend starts, but no case makes a Sandbox request.

Read-only requests disclose information too, so a typed name is treated as unverified:

- At case creation the typed name is not sent. Once accepted evidence exists, Search runs
  on the registry identity instead.
- A recheck makes a request only when the case then holds accepted evidence, and it sends
  the accepted identity, never the typed name. A changed name clears that evidence, so it
  is refused; use the registry-verified correction instead.
- The HR console accepts only an exact GoldTier ID, which it does not check against a
  retained record. Typed names are refused with `GOLDTIER_SANDBOX_SEARCH_IDENTITY_UNVERIFIED`.

A typed name that differs from the registry is not flagged. The registry identity is simply
what is used.

## Identity evidence policy

The rule depends on evidence provenance, never on entity type, UEN, case or company name.
`TargetIdentityEvidencePolicy` lists the reviewed sources a target accepts, each with its
provider, environment and reference boundary. An empty list accepts nothing.

A source label alone is not enough. The case's legal name, registration number and country
must still equal what the accepted source returned. A document-selected legal name
therefore stops Sandbox requests for that case, even though the entity keeps its label. A
registry-verified correction restores the registry identity and recovers the case.

The official ACRA Marketplace Mock is the only source reviewed today. It is not the
authority for every legal-entity type. A future source joins through its own reviewed
provider contract as one more entry, which leaves existing checks unchanged.

Government identities are not excluded as a category. The current Government register is
local synthetic data, so it has no accepted source and stays unsupported for Sandbox until
an authoritative pathway is independently reviewed. Seeded identities are refused the same
way. Neither is ever promoted to official provenance.

This applies only to staging Sandbox. Local Mock onboarding and Mock GoldTier keep working
for Government and seeded cases, and local and test Sandbox lanes are unchanged. These
controls are target-provider controls and do not limit what the AI Assistant may discuss.

## Backend-only configuration

`deploy/compose.yml` pins `GOLDTIER_CONNECTOR_MODE: mock`, so the runtime file alone cannot
select Sandbox. The release change to Compose comes first.

Provide these in the protected runtime file, never in Git, a frontend variable or a log:

| Setting | Class | Requirement |
|---|---|---|
| `GOLDTIER_SANDBOX_BASE_URL` | Non-secret | HTTPS origin only, no path, query or credentials |
| `GOLDTIER_SANDBOX_ENVIRONMENT` | Non-secret | The route segment for the supplied XPI environment |
| `GOLDTIER_SANDBOX_USER_ID` | Secret | The supplied `user_id` header. Rotate it if it is exposed |
| `GOLDTIER_SANDBOX_TIMEOUT_SECONDS` | Optional | At most 30 |
| `GOLDTIER_SANDBOX_MAX_RESPONSE_BYTES` | Optional | At most 1 MiB |

Do not set `GOLDTIER_SANDBOX_ALLOW_WRITES` for staging outside a separately authorised D-137
window, and then only through the window overlay. The future `PINGFED_*` and
`GOLDTIER_CLIENT_*` placeholders are not used by this adapter.

## Read-only readiness

Use the HR-only console under `/api/admin/goldtier-sandbox`:

1. `GET /status` shows mode `SANDBOX`, classification `SANDBOX_PARTIAL`, the safe host and
   `writes_enabled=false`, with blocker `GOLDTIER_SANDBOX_WRITES_DISABLED`.
2. `POST /search` with an already known `goldtier_id` is the exact-ID readback check. Use
   a retained synthetic ID from an earlier authorized run. Do not create one for this.
3. Name Search is exercised by a case holding accepted evidence, not by the console.

Any genuine call here needs explicit owner approval first.

## Existing customers

Existing-customer behaviour is unchanged. An exact match reuses the party. A candidate
that is not exact needs the creator's explicit confirmation of the retained Search.
Multiple or conflicting candidates stop for review. No path creates a Shell over a
candidate. With writes off, these steps can be reviewed but Send remains refused.

A recheck that ends in review waits for review. The case stays in review, so existing-
customer confirmation is refused until a registry-verified correction returns it to
validated. A further recheck is safe and clears only if the provider answer changes.

Paused wording: a paused case shows the existing `RECOVERY_PENDING` text about finalization,
which does not describe a refused write. Under D-137 W4, staging reaches this state when a
window ends or the next operation is outside it. The owner accepted the current wording for
the staging qualification (2026-11-15). A clearer message stays a follow-up.

Status of these items under D-137 (2026-11-15):
- Paused wording, the void read model, and the recovery exception: the owner accepted them
  under the stated staging limitations.
- Prior-case ledger proof: closed by D-137 W6. Reuse now needs a finalized, verified ledger
  entry for the current mode.

The items as originally recorded:

- `_find_verified_target_case` reuses a prior case in Sandbox without proving its ledger
  or provider mode. Under the policy a prior case without accepted evidence is ignored, but
  the ledger proof remains open. It predates the staging work.
- After a void, `case.initial_target_search` keeps its original disposition, and the
  workflow values derived from it can still read as an existing customer.
- `check_uncertain_target_status` and `verify_completed_target` have no policy check. They
  read a retained Sandbox ledger entry, and staging has none while writes are refused.
  Decide whether to keep this as a deliberate recovery exception before writes are
  qualified. Provider-verified Shell and Policy recovery do refuse a Mock submission or
  refused evidence.

## Failures and uncertain outcomes

| Event | Result |
|---|---|
| Search timeout, 5xx, 401, 403, 429, malformed body | Controlled failure with a fixed code and the observed status only. Nothing is retained as customer truth |
| Mutation 400 | Definitive failure recorded in the ledger |
| Mutation timeout, transport error, undecodable or oversized body, unexpected status | Uncertain outcome. The attempt stays in the ledger and replay is blocked |
| Uncertain recovery | Existing `TARGET_RECOVERY` path, using provider-verified evidence only |
| Writes turned off after some steps | The next mutation is refused before the ledger marks it. Nothing is failed or replayed. Automation pauses in `RECOVERY_PENDING`, and the same submission continues once writes return. Pending readback still runs |

A refused Send records nothing on the case or ledger. Before this change the same Send
marked the Shell attempted and terminated the case as `FAILED`.

## Write qualification

Writes stay off in staging until all of these hold:

1. Written owner approval names the run, its synthetic case and its call limit.
2. A separately reviewed change lifts the staging refusal and the Compose pin.
3. Read-only Search and exact-ID readback have passed on the same host and image digest.
4. Backend, Mongo and ledger are the single designated writer, with no overlapping backend.
5. Mongo backups or snapshots for `clm_staging` are confirmed before the run.
6. The case identity is official Mock evidence and the entity is approved synthetic data.
7. Q-001, Q-007, Q-009, Q-010, Q-011 and Q-018 are accepted as open for this bounded run.
8. The operator knows the recovery runbook and who may perform provider inspection.

Search before any write. A provider customer cannot be deleted by this adapter, so a
created Sandbox customer is permanent and is recorded as run evidence.

## Rollback

Roll back by returning to the reviewed read-only release:

- Stop on any uncertain outcome, unexpected status, identity mismatch, or a call count
  beyond the approved limit.
- Drain and stop the backend, then restart with writes off. Do not delete or edit ledger
  rows, and do not retry a mutation manually.
- Mode changes do not rewrite retained cases. A case frozen for one target mode stops with
  `CLM_TARGET_PROVIDER_CONTEXT_MISMATCH` under another.
- Resolve retained uncertainty only through provider-verified recovery.
- Rotate `GOLDTIER_SANDBOX_USER_ID` if a secret exposure is suspected.

## R3 egress path (D-131, drafted as D-127; G2 local candidate)

Staging reaches the Sandbox only through the R3 egress overlay, applied last
(`compose.yml` -> `compose.mongo.yml` -> [`compose.assistant.yml`] -> `compose.goldtier-egress.yml`).
The mode stays Mock unless `CLM_GOLDTIER_CONNECTOR_MODE=sandbox`; writes stay `"false"`.
`CLM_GOLDTIER_EGRESS_FQDN` is required and has no default; it must be the sponsor-confirmed
FQDN (Q-020 part 1, still UNCONFIRMED). The host must have `clm-r3-egress-firewall.service`
and `clm-r3-firewall-watch.service` active, verified with
`deploy/egress/host/verify_host_firewall.sh` (read-only). If the host table is lost or changed,
the watcher stops both R3 containers; Sandbox Search then fails closed (`503`) while Mock
onboarding and `/health` continue. Recovery is an operator action: restore the table with the
unit, confirm the verify script, then start `goldtier-dns` and `goldtier-egress`.
None of this is authorised on the host before G3a/G3b/G3c.

G3a preflight (from the G2 QG; each item is asserted on the live host, read-only first):
`clm_r3.vars` values against the host; installed host files hashed against a manifest built from
the reviewed commit (`R3_REVIEWED_MANIFEST=... verify_host_firewall.sh`); Docker
`live-restore=false`, firewall backend `iptables`, Docker and runc versions; U-1 behaviour
re-observed on the host's Docker (embedded DNS with and without `dns:`); and the `certifi` trust
store: the backend image's `certifi` version and bundle hash recorded. `certifi` is now declared
and pinned in `apps/backend/pyproject.toml` (fast-track D-cert), at the version in the tested G2
backend image.

R-1 destination pin (fast-track A2). `CLM_GOLDTIER_EGRESS_DST_V4` is also required and has no
default. It is the comma-separated GoldTier IPv4 set (1 to 8 public addresses), and it must equal
`GOLDTIER_DST_V4` in `/etc/clm/r3/clm_r3.vars` and the `goldtier_dst_v4` set in the installed
`clm_r3.nft`. The proxy refuses to start without a valid set. The host table and Layer N then
accept O-1 only toward those addresses, never toward any public IPv4. Preflight re-resolves the FQDN
on the host through the VPC resolver: any difference from the pinned set, more than 8 addresses or
answers that change between samples is a STOP. If GoldTier moves to an address that is not pinned,
Sandbox Search fails closed (`503`); re-pinning is a reviewed edit of all three values, followed
by a reload of the unit and a restart of the R3 containers. R-1b (shared virtual hosts on the
pinned addresses) is accepted by the owner only for the temporary read-only FYP staging
demonstration, under the D-131 A3 conditions. Reusing the local Sandbox credential from AWS is the owner's
authorisation (D-131 FT-CRED); sponsor permission for hosted access is unverified.
