"""R3 G2 path-table re-proof (X1-X13) with `inet clm_r3` counter deltas. Harness VM host, root.

  python3 -I xprobe.py <proxy-container> <resolver-container> <label>

Each probe runs inside a container's network namespace (nsenter) as host root, which is a
stronger sender than anything inside the container. For every probe it records the observed
result and which host-table rules counted packets. One JSON line per probe on stdout.
The outside sink capture (harness side) is the authority on what left the host.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time

CONNECT = """
import socket, sys
fam = socket.AF_INET6 if ':' in sys.argv[1] else socket.AF_INET
s = socket.socket(fam, socket.SOCK_STREAM if sys.argv[3] == 'tcp' else socket.SOCK_DGRAM)
s.settimeout(1.5)
try:
    if sys.argv[3] == 'tcp':
        s.connect((sys.argv[1], int(sys.argv[2])))
        print('CONNECTED')
    else:
        s.sendto(b'r3-probe', (sys.argv[1], int(sys.argv[2])))
        try:
            s.recvfrom(64); print('REPLY')
        except OSError:
            print('NO_REPLY')
except OSError as e:
    print('FAILED:' + type(e).__name__ + ':' + str(e.errno))
"""
SPOOF = """
import sys
from scapy.all import Ether, IP, TCP, sendp, get_if_hwaddr, conf
conf.verb = 0
iface, src, dst, port = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
gw_mac = sys.argv[5]
frame = Ether(src=get_if_hwaddr(iface), dst=gw_mac) / IP(src=src, dst=dst)
sendp(frame / TCP(sport=40404, dport=port, flags='S'), iface=iface, count=3)
print('SENT_SPOOFED_FRAMES')
"""


def sh(*args: str, check: bool = False) -> str:
    return subprocess.run(
        list(args), capture_output=True, text=True, check=check, timeout=60
    ).stdout


def pid(container: str) -> str:
    return sh("docker", "inspect", "-f", "{{.State.Pid}}", container).strip()


def counters() -> dict[str, int]:
    out: dict[str, int] = {}
    for line in sh("nft", "list", "table", "inet", "clm_r3").splitlines():
        m = re.search(r"counter packets (\d+) bytes \d+", line)
        if m:
            key = re.sub(r"\s+", " ", line.replace(m.group(0), "").strip())
            out[key] = out.get(key, 0) + int(m.group(1))
    return out


def delta(before: dict[str, int], after: dict[str, int]) -> dict[str, int]:
    return {
        k: after.get(k, 0) - before.get(k, 0) for k in after if after.get(k, 0) - before.get(k, 0)
    }


def in_ns(p: str, *cmd: str) -> str:
    return sh("nsenter", "-t", p, "-n", *cmd).strip()


def iface_for(p: str, ip: str) -> str:
    for line in in_ns(p, "ip", "-o", "-4", "addr").splitlines():
        if f" {ip}/" in line:
            return line.split()[1].split("@")[0]
    return ""


def main() -> int:
    proxy, resolver, label = sys.argv[1], sys.argv[2], sys.argv[3]
    pp, rp = pid(proxy), pid(resolver)
    backend = pid("clm-staging-backend")
    frontend = pid("clm-staging-frontend-1")
    up_if = iface_for(pp, "172.30.242.2")
    gw_mac = (
        in_ns(
            pp,
            "sh",
            "-c",
            "ping -c1 -W1 172.30.242.1 >/dev/null 2>&1; ip neigh show 172.30.242.1 | awk '{print $5}'",  # noqa: E501
        )
        or "ff:ff:ff:ff:ff:ff"
    )
    probes = [
        # (row, from_pid, dst, port, proto, expectation)
        ("X1 proxy->GT:443", pp, "34.120.0.10", 443, "tcp", "ALLOW"),
        ("X2 proxy->public:80", pp, "1.1.1.1", 80, "tcp", "DROP"),
        ("X2 proxy->public:8443", pp, "1.1.1.1", 8443, "tcp", "DROP"),
        ("X2 proxy->GT:80", pp, "34.120.0.10", 80, "tcp", "DROP"),
        ("X2 proxy->public udp/53", pp, "1.1.1.1", 53, "udp", "DROP"),
        ("X2 proxy->public udp/123", pp, "1.1.1.1", 123, "udp", "DROP"),
        ("X3 proxy->IMDS:80", pp, "169.254.169.254", 80, "tcp", "DROP"),
        ("X3 proxy->169.254.169.253 udp/53", pp, "169.254.169.253", 53, "udp", "DROP"),
        ("X3 proxy->169.254.169.123 udp/123", pp, "169.254.169.123", 123, "udp", "DROP"),
        ("X4 proxy->VPC resolver udp/53", pp, "172.26.0.2", 53, "udp", "DROP"),
        ("X4 proxy->VPC resolver tcp/53", pp, "172.26.0.2", 53, "tcp", "DROP"),
        ("X4 proxy->VPC host:22", pp, "172.26.5.5", 22, "tcp", "DROP"),
        ("X4 proxy->10/8:443", pp, "10.0.0.1", 443, "tcp", "DROP"),
        ("X4 proxy->CGNAT:443", pp, "100.64.0.1", 443, "tcp", "DROP"),
        ("X4 proxy->docker0 gw:443", pp, "172.17.0.1", 443, "tcp", "DROP"),
        ("X4 proxy->host-local :443 (DNAT to Caddy)", pp, "172.26.4.119", 443, "tcp", "DROP"),
        ("X4 proxy->host-local :80 (DNAT to Caddy)", pp, "172.26.4.119", 80, "tcp", "DROP"),
        ("X5 proxy->uplink gw:22", pp, "172.30.242.1", 22, "tcp", "DROP"),
        ("X5 proxy->control gw:22", pp, "172.30.241.1", 22, "tcp", "DROP"),
        ("X5 proxy->host :22", pp, "172.26.4.119", 22, "tcp", "DROP"),
        ("X6 proxy->IPv6 public:443", pp, "2001:db8::9", 443, "tcp", "DROP"),
        ("X9 resolver->VPC resolver udp/53", rp, "172.26.0.2", 53, "udp", "ALLOW"),
        ("X9 resolver->VPC resolver tcp/53", rp, "172.26.0.2", 53, "tcp", "ALLOW"),
        ("X9 resolver->public udp/53", rp, "1.1.1.1", 53, "udp", "DROP"),
        ("X9 resolver->GT:443", rp, "34.120.0.10", 443, "tcp", "DROP"),
        ("X9 resolver->IMDS:80", rp, "169.254.169.254", 80, "tcp", "DROP"),
        ("X9 resolver->uplink gw:22", rp, "172.30.242.1", 22, "tcp", "DROP"),
        ("X8 backend->public:443", backend, "1.1.1.1", 443, "tcp", "DROP"),
        ("X8 backend->GT:443", backend, "34.120.0.10", 443, "tcp", "DROP"),
        ("X8 backend->control gw:22", backend, "172.30.241.1", 22, "tcp", "DROP"),
        ("X8 backend->proxy:4751", backend, "172.30.241.2", 4751, "tcp", "DROP"),
        ("X12 frontend->proxy:4750", frontend, "172.30.241.2", 4750, "tcp", "DROP"),
        ("X12 frontend->resolver udp/53", frontend, "172.30.241.4", 53, "udp", "DROP"),
        ("X12 frontend->proxy uplink:4750", frontend, "172.30.242.2", 4750, "tcp", "DROP"),
    ]
    for row, p, dst, port, proto, expect in probes:
        before = counters()
        result = in_ns(p, "python3", "-I", "-c", CONNECT, dst, str(port), proto)
        time.sleep(0.3)
        print(
            json.dumps(
                {
                    "set": label,
                    "probe": row,
                    "expect": expect,
                    "result": result,
                    "clm_r3_counter_delta": delta(before, counters()),
                },
                sort_keys=True,
            ),
            flush=True,
        )
    for row, src in (
        ("X7 spoofed src 172.30.242.5 ->GT:443 (L2 frames)", "172.30.242.5"),
        ("X7 spoofed resolver src .3 ->GT:443 (L2 frames)", "172.30.242.3"),
    ):
        before = counters()
        result = in_ns(pp, "python3", "-c", SPOOF, up_if, src, "34.120.0.10", "443", gw_mac)
        time.sleep(0.5)
        print(
            json.dumps(
                {
                    "set": label,
                    "probe": row,
                    "expect": "DROP",
                    "result": result,
                    "clm_r3_counter_delta": delta(before, counters()),
                },
                sort_keys=True,
            ),
            flush=True,
        )
    for row, cmd in (
        ("X13 proxy netns ip_forward", ["cat", "/proc/sys/net/ipv4/ip_forward"]),
        ("X13 backend default route", ["ip", "route", "show", "default"]),
        ("X6 proxy IPv6 addresses", ["ip", "-6", "-o", "addr"]),
        ("X6 proxy disable_ipv6", ["cat", "/proc/sys/net/ipv6/conf/all/disable_ipv6"]),
    ):
        target = backend if "backend" in row else pp
        print(
            json.dumps({"set": label, "probe": row, "result": in_ns(target, *cmd) or "(none)"}),
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
