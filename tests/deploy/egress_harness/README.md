# R3 G2 egress harness (Linux only; never Docker Desktop)

Netfilter, proxy and DNS evidence for D-127 comes only from a real Linux host with the same
Docker version and firewall backend as the target host. This directory holds the harness tools.
Nothing here runs in CI, and none of it touches a real host, AWS or GoldTier.

## Topology

- **Harness VM.** QEMU/KVM (inside WSL2 on the developer machine), Ubuntu 24.04, kernel
  `7.0.0-1012-aws`, Docker 29.9.3 with the `iptables` backend on `iptables v1.8.10 (nf_tables)`,
  no `daemon.json`, `br_netfilter` absent, forwarding 1/0, `live-restore=false`. Its only NIC is
  `ens5` (172.26.4.119/20).
- **Sealed outside world** (`outside/outside_net.sh`, `outside/outside.py`). A network namespace
  holding the VM's tap and nothing else. It simulates the VPC gateway and resolver (scriptable
  test zone, TTL 0), IMDS, and a fake GoldTier TLS 1.3 server on a throwaway test CA
  (`outside/mkpki.sh`). Every other address answers locally, so leaks are observed; a full
  packet capture of `ens5` is the sink.

## Runs

| Script | Rows |
|---|---|
| `run_gates.sh` + `analyse_gates.py` | S2 hard gates P-1 to P-10, D-1/D-2/D-7 (gate rig, no firewall) |
| `vm/cap_rig.sh` + `vm/cap_checks.sh` | G2-LN capability proof (guard and child credentials, tamper attempts) |
| `vm/stack.sh` | Integrated stack: `compose.yml` + `compose.mongo.yml` + egress overlay + harness override |
| `run_matrix_a.sh` | X1-X13 with `inet clm_r3` counters (both layers, host-only, Layer-N-only), AC-1, D-rows, U-1, X11, FA-15/17/18 |
| `run_matrix_b.sh` | Amendment A RL-1 to RL-12 (+FA-16, FA-B1, FA-B2) |
| `vm/e_client.py` | E-rows through Caddy -> backend -> proxy -> fake GoldTier |
| `sink_report.py` | Classifies every packet past `ens5` in a window (O-1, O-2, R-1, disallowed) |

Synthetic values only: `.invalid` names, a per-run test credential that is never printed, and a
test CA whose key never leaves the harness.
