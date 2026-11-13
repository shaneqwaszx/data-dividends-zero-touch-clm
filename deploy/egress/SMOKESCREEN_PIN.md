# R3 egress image pins and update policy (D-127 E2)

| Component | Pin | Verification |
|---|---|---|
| Smokescreen | `stripe/smokescreen` commit `bb9ed1bbe75b59821f881dd0c1411c79dd7abdbe` (2026-11-11), built with the vendored modules (`-mod=vendor -trimpath`, `CGO_ENABLED=0`) | Commit SHA in the Dockerfile `ADD`; binaries reproduce byte-for-byte across builds |
| R3 entrypoint | `smokescreen-main/main.go`, compiled inside the pinned module; its unit tests (`main_test.go`) run in the build and fail it | Reviewed source in this repository |
| CoreDNS | v1.15.0 release `coredns_1.15.0_linux_amd64.tgz` | `ADD --checksum=sha256:2495c5b8f3fab6d0a336c397f1227b75406d86e6ec7125744a29df9e936ab8cd` (matches the published `.sha256`) |
| Go builder | `golang:1.26-bookworm@sha256:dc40a13b61304647ed7e5d581d246b86413dfc29d63c6d018310feb93cd98fc0` | Digest |
| Runtime base | `python:3.12-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df` (the repository's reviewed digest) plus `nftables=1.0.6-2+deb12u2`; `setpriv` from util-linux 2.38.1 | Digest and exact package version |

Licences: Smokescreen MIT (`LICENSE.txt`), CoreDNS Apache-2.0.

## Why this commit

It is the last commit before the v1.0.0 breaking refactor (v2 ACL engine, slog logging, module
path `/v2`) that landed as one batch on 2026-11-12. It includes the NAT64 local-use (#326) and
self-connection (#328) denial fixes, which the last tag `v0.1.0` predates. Moving to v1.x needs
its own review and a full gate re-run.

## What the R3 entrypoint changes

Upstream's `main` takes the role from a TLS client certificate and has no flag for a missing
role, so it cannot serve a plain-HTTP backend. The R3 entrypoint differs in three ways, and each
can only refuse more, never allow more:

1. a fixed role (`goldtier-backend`). There is no authentication in either build; the ACL gives
   that role one exact domain and the default rule allows nothing;
2. a raw request-head gate before Go's HTTP parser: exactly `CONNECT <fqdn>:443 HTTP/1.1`, one
   exact `Host`, printable ASCII, allowlisted header names (owner decision G2-P2, option B);
3. a post-decision re-check of the parsed request (method, `RequestURI`, `Host`, no userinfo).

Smokescreen's ACL, private-range denial and the guard's `--deny-range` set (the G1
`no_egress_v4` list plus `::/0`, needed because Smokescreen's own default treats several
reserved IPv4 ranges as public) remain independent enforcement. No `--unsafe-*` flag is used.

## Update policy

- Track upstream security advisories and releases. Review any new commit's diff in the
  resolver, dialer, IP classification, hostport and ACL code before moving the pin.
- Any change to a pin, the entrypoint, the Corefile template or the guard requires: a rebuild,
  the full S2 gate suite (`tests/deploy/egress_harness/run_gates.sh`, all hard gates PASS), the
  capability proof (`vm/cap_checks.sh`), the affected FA/RL rows, and an independent QG.
- A failed hard gate means STOP and a separate owner decision. There is no automatic fallback.
