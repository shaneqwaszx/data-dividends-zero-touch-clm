"""Classify every packet the harness VM sent past ens5 in a time window (harness side).

  python3 -I sink_report.py <pcap-dir> <t_start> <t_end> <events.jsonl> [--r1]

--r1 is for windows in which ONLY the proxy role is fuzzed: both enforcement layers deliberately
let the proxy reach any public IPv4 on TCP 443 at L3 (G1 residual R-1; the exact FQDN is
enforced at L7 by Smokescreen), so such packets are reported as R1-public443 and not counted
as disallowed. Without --r1, any non-GoldTier 443 packet is disallowed.

Amendment C: the only permitted off-host flows are
  O-1  proxy -> GoldTier IP 34.120.0.10 TCP 443   (seen masqueraded as 172.26.4.119)
  O-2  resolver -> VPC resolver 172.26.0.2 UDP/TCP 53, exact-name `A <FQDN>` only
Also excluded as harness plumbing: SSH replies from the VM (sport 22) to the operator at
172.26.0.1, and ARP / IPv6 neighbour discovery. Everything else is DISALLOWED and listed.
DNS: every query the simulated VPC resolver logged in the window must be `A <FQDN>`; any other
name is listed (it would be host-own or a side channel and must be explained).
"""

from __future__ import annotations

import collections
import glob
import ipaddress
import json
import re
import subprocess
import sys

VM = {"172.26.4.119", "2001:db8:26::4:119", "fe80::5054:ff:fe26:477"}
R3_RAW = {"172.30.242.2", "172.30.242.3", "172.30.241.2", "172.30.241.3", "172.30.241.4"}
FQDN = "goldtier.r3-harness.invalid."
NO_EGRESS = [
    ipaddress.ip_network(n)
    for n in (
        "0.0.0.0/8",
        "10.0.0.0/8",
        "100.64.0.0/10",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "172.16.0.0/12",
        "192.0.0.0/24",
        "192.0.2.0/24",
        "192.88.99.0/24",
        "192.168.0.0/16",
        "198.18.0.0/15",
        "198.51.100.0/24",
        "203.0.113.0/24",
        "224.0.0.0/4",
        "240.0.0.0/4",
    )
]


def public_v4(addr: str) -> bool:
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return False
    return ip.version == 4 and not any(ip in n for n in NO_EGRESS)


LINE = re.compile(r"^(\d+\.\d+) (IP6?) (\S+?)(?:\.(\d+))? > (\S+?)(?:\.(\d+))?: (.*)$")


def packets(pcap_dir: str, a: float, b: float):
    for pcap in sorted(glob.glob(f"{pcap_dir}/sink-*.pcap")):
        out = subprocess.run(
            ["tcpdump", "-nn", "-tt", "-r", pcap], capture_output=True, text=True
        ).stdout
        for line in out.splitlines():
            m = LINE.match(line)
            if not m:
                continue
            t = float(m.group(1))
            if a <= t <= b:
                yield t, m.groups()[1:]


def classify(fam, src, sport, dst, dport, rest):
    proto = "tcp" if "Flags [" in rest else ("icmp" if "ICMP" in rest else "udp")
    if src not in VM and src not in R3_RAW:
        return None  # from the outside world toward the VM
    if src == "172.26.4.119" and sport == "22" and dst == "172.26.0.1":
        return "MGMT"
    if (
        "ICMP6, neighbor" in rest
        or "ICMP6, router solicitation" in rest
        or ("multicast listener report" in rest and src.startswith("fe80::5054:ff:fe26:477"))
    ):
        return "ND"
    if dst == "34.120.0.10" and dport == "443" and proto == "tcp":
        return "O-1" if src == "172.26.4.119" else "O-1-unmasqueraded"
    if dport == "443" and proto == "tcp" and public_v4(dst) and src == "172.26.4.119":
        return "R1-public443"
    if dst == "172.26.0.2" and dport == "53":
        return "O-2" if src == "172.26.4.119" else "O-2-unmasqueraded"
    return "DISALLOWED"


def main() -> int:
    pcap_dir, a, b, events = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
    r1 = "--r1" in sys.argv[5:]
    counts: collections.Counter = collections.Counter()
    disallowed: collections.Counter = collections.Counter()
    for _t, (fam, src, sport, dst, dport, rest) in packets(pcap_dir, a, b):
        c = classify(fam, src, sport, dst, dport, rest)
        if c is None:
            continue
        counts[c] += 1
        # O-1/O-2 "unmasqueraded": a permitted flow to its permitted destination that left
        # without Docker's MASQUERADE (only after Docker's own NAT was flushed, RL-4). Reported,
        # not counted as an escape: destination, port and protocol are the Amendment C ones.
        if c == "DISALLOWED" or (c == "R1-public443" and not r1):
            disallowed[f"{src}:{sport} > {dst}:{dport} {rest[:40]}"] += 1
    names: collections.Counter = collections.Counter()
    leaks: collections.Counter = collections.Counter()
    with open(events) as handle:
        event_lines = handle.readlines()
    for line in event_lines:
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if not a <= r.get("t", 0) <= b:
            continue
        if r["kind"] == "dns_query":
            names[(r["qname"], r["qtype"])] += 1
        elif r["kind"] in ("LEAK_tcp", "LEAK_udp", "imds_hit", "dns_error"):
            leaks[(r["kind"], r.get("dst"), r.get("dport"))] += 1
    other_names = {f"{k[0]}/{k[1]}": v for k, v in names.items() if k != (FQDN, 1)}
    verdict = not disallowed and not other_names and not leaks
    print(
        json.dumps(
            {
                "window": [a, b],
                "classes": dict(counts),
                "disallowed_packets": sum(disallowed.values()),
                "disallowed_detail": dict(disallowed.most_common(25)),
                "upstream_dns": {f"{k[0]}/{k[1]}": v for k, v in names.items()},
                "non_fqdn_dns": other_names,
                "sink_leak_events": {f"{k[0]} {k[1]}:{k[2]}": v for k, v in leaks.items()},
                "zero_disallowed": verdict,
            },
            sort_keys=True,
        )
    )
    return 0 if verdict else 1


if __name__ == "__main__":
    raise SystemExit(main())
