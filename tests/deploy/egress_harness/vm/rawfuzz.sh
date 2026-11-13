#!/bin/bash
# R3 G2 AC-1 raw fuzz from inside one container's network namespace, as HOST root (nsenter).
# This sender is stronger than anything inside an R3 container (it has CAP_NET_RAW; the
# containers do not), so it also exercises the host table on its own. Harness VM only.
#   rawfuzz.sh <container> <role>
set -u
C=$1; ROLE=$2
P=$(sudo docker inspect -f '{{.State.Pid}}' "$C")
N="sudo nsenter -t $P -n"
SRC=$([ "$ROLE" = proxy ] && echo 172.30.242.2 || echo 172.30.242.3)
# TCP SYN sweeps (raw IP sockets traverse the netns OUTPUT hook)
for dst in 1.1.1.1 34.120.0.10 169.254.169.254 172.26.0.2 172.26.5.5 172.26.4.119 172.30.242.1 10.0.0.1; do
  $N timeout 20 hping3 -q -S -c 40 -i u2000 -p ++20 "$dst" >/dev/null 2>&1
done
# UDP and ICMP
for dst in 1.1.1.1 172.26.0.2 169.254.169.253 34.120.0.10; do
  $N timeout 10 hping3 -q -2 -c 20 -i u2000 -p ++50 "$dst" >/dev/null 2>&1
  $N timeout 5 hping3 -q -1 -c 5 -i u2000 "$dst" >/dev/null 2>&1
done
# L2 frame injection with spoofed and genuine sources (packet sockets BYPASS the netns OUTPUT
# hook, so only the host table can stop these)
IF=$($N ip -o -4 addr | awk -v s="$SRC/" '$0 ~ s {print $2}' | cut -d@ -f1)
GWMAC=$($N sh -c "ping -c1 -W1 172.30.242.1 >/dev/null 2>&1; ip neigh show 172.30.242.1" | awk '{print $5}')
$N python3 - "$IF" "$GWMAC" "$SRC" <<'PY'
import sys
from scapy.all import Ether, IP, IPv6, TCP, UDP, ICMP, sendp, get_if_hwaddr, conf
conf.verb = 0
iface, gw, own = sys.argv[1], sys.argv[2], sys.argv[3]
mac = get_if_hwaddr(iface)
frames = []
for src in (own, "172.30.242.5", "172.30.242.3" if own.endswith(".2") else "172.30.242.2", "172.26.4.119", "10.9.9.9"):
    for dst, port in (("1.1.1.1", 80), ("1.1.1.1", 443), ("34.120.0.10", 22), ("169.254.169.254", 80),
                      ("172.26.0.2", 53), ("172.26.5.5", 22)):
        frames.append(Ether(src=mac, dst=gw) / IP(src=src, dst=dst) / TCP(sport=41000, dport=port, flags="S"))
        frames.append(Ether(src=mac, dst=gw) / IP(src=src, dst=dst) / UDP(sport=41000, dport=port) / b"r3")
    frames.append(Ether(src=mac, dst=gw) / IP(src=src, dst="1.1.1.1") / ICMP())
frames.append(Ether(src=mac, dst=gw) / IPv6(src="fe80::bad", dst="2001:db8::9") / TCP(dport=443, flags="S"))
frames.append(Ether(src=mac, dst="33:33:00:00:00:01") / IPv6(src="fe80::bad", dst="ff02::1") / UDP(dport=53))
sendp(frames, iface=iface, count=3)
print(f"raw frames sent: {len(frames) * 3}")
PY
echo "rawfuzz $C done"
