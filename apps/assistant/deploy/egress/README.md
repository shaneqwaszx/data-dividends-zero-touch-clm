# R2.2 assistant egress (E1): LOCAL DESIGN CANDIDATE

Status: D-129 **PROPOSED**. E1 is approved as a local design candidate only (OD-P7 is open). Nothing
here may be installed on AWS without the owner's production egress approval and the sole AWS
release lead.

## What it does

Hosted Claude Sonnet 5.5 (`compose.assistant-provider.yml`) needs exactly one outbound flow:

    clm-staging-assistant (172.30.243.2) -> 160.79.104.10:443 (api.anthropic.com, pinned)

- **Network.** The assistant joins one extra bridge, `clm-as-up` (172.30.243.0/29, IPv4 only). Docker
  itself accepts everything from that bridge, so **the host table is the only control.**
- **Host table `inet clm_r22`** (`clm_r22.nft`). It only drops, at forward/input priority
  `filter - 10`. It allows the assistant's address to the pinned IPv4 on tcp/443 plus established
  replies, and drops everything else entering or leaving the bridge: IPv6, invalid packets, other
  source addresses, other destinations (including other addresses in Anthropic's ranges), DNS,
  IMDS, the host and its gateway. It is separate from R3's `inet clm_r3` and from Docker's tables.
- **Name.** `api.anthropic.com` comes only from the container's hosts file (`extra_hosts`). The
  container's DNS server is `192.0.2.53` (TEST-NET-1), so Docker's embedded resolver forwards any
  other lookup to an address the table drops. Container names on the internal proxy network still
  resolve.
- **TLS.** Unchanged. The Claude adapter verifies the chain (certifi) and the name
  `api.anthropic.com`, with `trust_env=False`, no proxy and no redirects. The pin only chooses
  where the connection goes.
- **Boot fails closed (P2-1).** Docker never starts the assistant (`restart: "no"`). Only
  `clm-r22-assistant.service` does, after `clm-r22-assistant-firewall` loaded the table,
  `clm-r22-firewall-watch` is running and the live table equals the reviewed file. A broken
  table file, a missing `nft`, or a masked or failed unit leaves the assistant stopped. Docker
  also does not masquerade `clm-as-up`; the table's single NAT rule (assistant to the pin on 443)
  is the only translation, so without the table the uplink gives no internet path even to a
  container someone started by hand.
- **Fail closed.** The service refuses to start unless `api.anthropic.com` resolves only to an IPv4
  inside Anthropic's published inbound ranges (`PROVIDER_PIN_REQUIRED`).
  `clm-r22-firewall-watch.service` stops the assistant within about 0.3 s if the table is
  removed or changed, or if the watcher itself stops. Stopping the firewall unit stops the
  assistant before it removes the table. Nothing restarts the assistant automatically.

## Install (release lead only, after OD-P7)

1. Run the host preflight. `UPLINK_IF` must be the host's uplink (`ens5` on the Lightsail host).
   Re-resolve `api.anthropic.com` through the VPC resolver; it must equal `ANTHROPIC_DST_V4`.
2. Copy `clm_r22.nft` and `clm_r22.vars` to `/etc/clm/r22/` (root, 0600). Copy
   `clm_r22_watch.py` and `clm_r22_stop_assistant.sh` to `/usr/local/lib/clm-r22/` (0755). Copy
   the three units to `/etc/systemd/system/`.
3. Run `systemctl daemon-reload`, then `systemctl enable --now clm-r22-assistant-firewall`,
   `systemctl enable --now clm-r22-firewall-watch` and `systemctl enable clm-r22-assistant`.
4. Add `ASSISTANT_CLAUDE_LIFETIME_CAP_MICRO_USD` (OD-P4) and `ASSISTANT_ANTHROPIC_PINNED_V4` to
   `compose.env`. No key, decision or workspace value goes there.
5. Create the assistant with the overlay applied last, without starting it:
   `compose.yml`, `compose.mongo.yml`, `compose.assistant.yml`, `compose.assistant-provider.yml`,
   `up -d --no-start` for the assistant. Then `systemctl start clm-r22-assistant`.
6. Run `verify_assistant_egress.sh <compose.env>`; every line must be PASS.

In the commands below, `dca` means `docker compose --env-file compose.env` with the four files
of step 5 in that order. Never `up` or `start` the assistant directly: only
`clm-r22-assistant` starts it (the gate checks the table first).

## Upgrade from R2.2

R2.2 created `clm-as-up` with Docker masquerade on and the assistant with `unless-stopped`.
Docker applies those options only when it creates the network or the container, so both must
be recreated.

1. `systemctl stop clm-r22-assistant` (if installed), then `dca stop assistant` and
   `dca rm -f assistant`.
2. Remove the old uplink network: `docker network rm clm-staging_assistant-uplink`. Nothing
   else uses it.
3. Install the new files (Install step 2: the table, `clm-r22-assistant.service` and the
   updated watcher unit), then `systemctl daemon-reload`.
4. `systemctl restart clm-r22-assistant-firewall clm-r22-firewall-watch`, then
   `systemctl enable clm-r22-assistant`.
5. `dca up -d --no-start assistant` (this recreates the network without masquerade and the
   container with restart `no`), then `systemctl restart clm-r22-assistant`.
6. `verify_assistant_egress.sh <compose.env>`: every line PASS, including "Docker does not
   masquerade clm-as-up", "assistant restart policy is no", "clm-r22-assistant.service active"
   and "assistant running and healthy".

## Pin maintenance

`api.anthropic.com` is pinned to one IPv4 (`ANTHROPIC_DST_V4`). Check it before every start and
at least daily: `verify_assistant_egress.sh` fails "resolves to ..., not the pin" when the name
moved. Until it is re-pinned, Claude calls time out and users get the labelled fallback.

To re-pin, all in one change, with the new address inside Anthropic's published ranges (the
script and the service both refuse anything else; never widen the set to a range):

1. `systemctl stop clm-r22-assistant`.
2. Set the new address in `/etc/clm/r22/clm_r22.vars`, in the table file's
   `anthropic_dst_v4` set (`/etc/clm/r22/clm_r22.nft`) and as `ASSISTANT_ANTHROPIC_PINNED_V4`
   in `compose.env`.
3. `systemctl restart clm-r22-assistant-firewall clm-r22-firewall-watch`. The firewall unit is a
   oneshot, so a restart (not a reload) loads the new table, and the watcher restart takes the
   new reviewed hash. The restart reaches the gate too (Requires/BindsTo); it may start the
   old container, which the new table no longer lets reach anything.
4. `dca up -d --no-start assistant` (the hosts file entry changes, so the container is
   recreated, stopped), then `systemctl restart clm-r22-assistant` (a restart, so the gate's
   checks run again and it starts the new container).
5. `verify_assistant_egress.sh <compose.env>`: every line PASS.

## Recovery

The assistant never comes back on its own after a fail-closed stop. Find the cause first:
`journalctl -u clm-r22-assistant-firewall -u clm-r22-firewall-watch -u clm-r22-assistant`
(look for `CLM_R22_FIREWALL_LOSS` and `CLM_R22_ASSISTANT_STOPPED`) and
`nft list table inet clm_r22`.

| State | Recovery |
|---|---|
| Table missing or changed (watcher stopped the assistant) | Reinstall the reviewed table file if it changed, `systemctl restart clm-r22-assistant-firewall clm-r22-firewall-watch`, then `systemctl restart clm-r22-assistant`. |
| Firewall unit failed at boot (broken file, no `nft`) | Fix the cause (`nft -c -f /etc/clm/r22/clm_r22.nft` must pass), then the same three restarts. |
| Watcher crashed or was killed (it restarts itself; each exit stopped the assistant) | `systemctl restart clm-r22-assistant`. The gate is still "active (exited)" but the container is down; `verify` reports it. |
| Docker restarted | Nothing: the gate restarts with Docker and starts the assistant after its checks. |
| Gate failed ("dependency failed" or the table check failed) | Fix the firewall or watcher unit first; the gate never starts the assistant without both. |

After any recovery, run `verify_assistant_egress.sh <compose.env>`; every line must be PASS.

## Evidence

The R2.2 local harness VM ran Docker 29.9.3, iptables-nft and kernel 7.0.0-1012-aws, with R3's
table loaded alongside. The rows are in the R2.2 QG handoff (matrix A connectivity and matrix B
robustness) and the D-130 QG handoff (matrix C boot rows and the start-gate rows).
