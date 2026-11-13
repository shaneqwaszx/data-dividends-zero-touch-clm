#!/bin/bash
# R3 G2 harness: build or tear down the sealed "outside world" namespace `clmr3out`.
#
# Harness side only (WSL2 Linux). Never run on a real host. The namespace has no link to the
# harness machine's own network: the only interface is the VM's tap (r3tap0), so nothing the
# VM sends can reach a real network.
#
#   outside_net.sh up     create clmr3out (the VM is then started with its NIC in it)
#   outside_net.sh addr   configure r3tap0 after QEMU has created it
#   outside_net.sh down   delete the namespace
set -euo pipefail
NS=clmr3out
case "${1:-}" in
  up)
    ip netns list | grep -qw "$NS" || ip netns add "$NS"
    ip -n "$NS" link set lo up
    # Every IPv4/IPv6 destination is local here (AnyIP), including the rest of the simulated
    # VPC (so ARP for any VPC address is answered and the packet is observed). Only the VM's own
    # addresses stay on-link so replies reach it.
    # The routes sit in the `local` table (replies need the source to be a local address);
    # `throw` routes carve the VM's own addresses back out to the main table.
    ip -n "$NS" addr add 169.254.169.254/32 dev lo 2>/dev/null || true
    ip -n "$NS" route replace local 0.0.0.0/1 dev lo table local
    ip -n "$NS" route replace local 128.0.0.0/1 dev lo table local
    ip -n "$NS" route replace throw 172.26.4.119/32 table local
    ip -n "$NS" -6 route replace local ::/1 dev lo table local
    ip -n "$NS" -6 route replace local 8000::/2 dev lo table local
    ip -n "$NS" -6 route replace local c000::/3 dev lo table local
    ip -n "$NS" -6 route replace throw 2001:db8:26::4:119/128 table local
    # Any custom rule stops the kernel merging the local and main tables; with merged tables a
    # `throw` in local resolves to "unreachable" instead of falling through to main.
    ip -n "$NS" rule show | grep -q '^32000:' || ip -n "$NS" rule add pref 32000 lookup main
    ip -n "$NS" -6 rule show | grep -q '^32000:' || ip -n "$NS" -6 rule add pref 32000 lookup main
    ip netns exec "$NS" sysctl -qw net.ipv4.ip_forward=0 net.ipv6.conf.all.forwarding=0
    echo "namespace $NS ready"
    ;;
  addr)
    for _ in $(seq 1 50); do ip -n "$NS" link show r3tap0 >/dev/null 2>&1 && break; sleep 0.2; done
    ip -n "$NS" link set r3tap0 up
    ip -n "$NS" addr replace 172.26.0.1/20 dev r3tap0
    ip -n "$NS" addr replace 172.26.0.2/20 dev r3tap0
    ip -n "$NS" -6 addr replace 2001:db8:26::1/64 dev r3tap0 nodad
    ip -n "$NS" -br addr
    ;;
  down)
    ip netns del "$NS" 2>/dev/null || true
    ;;
  *) echo "usage: $0 up|addr|down" >&2; exit 2 ;;
esac
