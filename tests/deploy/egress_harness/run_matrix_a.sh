#!/bin/bash
# R3 G2 S4 phase A (harness side, root): FA path table X1-X13 with counters under three layer
# configurations, AC-1 fuzz, D-rows (incl. U-1/D-6), X11 inbound, FA-11/13/14/15/17/18.
# Requires: sealed VM up, `stack.sh host-install` done, `stack.sh up sandbox` healthy.
#   HARNESS=/root/clm-r3-harness VSSH="<vm shell>" run_matrix_a.sh <outdir>
set -uo pipefail
OUT=$1; mkdir -p "$OUT"
H=${HARNESS:-/root/clm-r3-harness}
VSSH=${VSSH:-$H/bin/vssh.sh net}
T=$(cd "$(dirname "$0")" && pwd)
VM='~/r3/tests/deploy/egress_harness/vm'
EV=$H/sink/outside-events.jsonl
v() { $VSSH "$@"; }
now() { date +%s.%N; }
sink() {  # sink <name> <t_a> <t_b> [--r1]
  python3 -I "$T/sink_report.py" "$H/sink" "$2" "$3" "$EV" ${4:-} > "$OUT/$1.sink.json"
  echo "  sink $1: $(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print('zero_disallowed=%s classes=%s disallowed=%s non_fqdn_dns=%s leaks=%s' % (d['zero_disallowed'], d['classes'], d['disallowed_packets'], d['non_fqdn_dns'], d['sink_leak_events']))" "$OUT/$1.sink.json")"
}
xprobe() { v "sudo python3 -I $VM/xprobe.py $1 $2 $3" > "$OUT/X-$3.jsonl" 2>&1; }
fuzz_in() {  # fuzz_in <container> <role>: socket fuzz as child uid and as container root
  v "sudo docker exec -i -u 65532:65532 $1 python3 -I - fuzz $2 < $VM/loadgen.py; sudo docker exec -i $1 python3 -I - fuzz $2 < $VM/loadgen.py"
}
search() { v "sudo python3 -I $VM/e_client.py search"; }
echo "== rows: parity + verify"
v "bash $VM/rlvm.sh state" > "$OUT/state-start.txt" 2>&1
v "sudo /usr/local/lib/clm-r3/verify_host_firewall.sh" > "$OUT/verify_host_firewall.txt" 2>&1; echo "  verify rc=$?"
v "lsmod | grep -c '^br_netfilter' ; cat /proc/net/ip_tables_names | tr '\n' ' '" > "$OUT/FA-18.txt" 2>&1

echo "== FA-17: unit start/stop never touches Docker's tables"
v "strip() { sudo nft list ruleset | awk '/^table inet clm_r3 /{s=1} s&&/^}/{s=0;next} !s' | sed -E 's/counter packets [0-9]+ bytes [0-9]+//'; }
   sudo docker stop -t 2 clm-staging-goldtier-egress clm-staging-goldtier-dns >/dev/null
   strip > /tmp/fa17-a; sudo systemctl stop clm-r3-egress-firewall; strip > /tmp/fa17-b
   sudo nft list tables | grep -c 'inet clm_r3' ; sudo systemctl start clm-r3-egress-firewall; strip > /tmp/fa17-c
   echo diff-a-b:; diff /tmp/fa17-a /tmp/fa17-b && echo EMPTY; echo diff-a-c:; diff /tmp/fa17-a /tmp/fa17-c && echo EMPTY
   bash ~/r3/tests/deploy/egress_harness/vm/rlvm.sh recover" > "$OUT/FA-17.txt" 2>&1
grep -A1 'diff-' "$OUT/FA-17.txt" | tr '\n' ' '; echo

echo "== config BOTH layers: X1-X13, AC-1 fuzz (proxy window, resolver window), raw fuzz"
a=$(now); xprobe clm-staging-goldtier-egress clm-staging-goldtier-dns both; b=$(now); sink X-both "$a" "$b" --r1
a=$(now); fuzz_in clm-staging-goldtier-egress proxy > "$OUT/AC1-both-proxy.fuzz.txt" 2>&1; b=$(now); sink AC1-both-proxy "$a" "$b" --r1
a=$(now); fuzz_in clm-staging-goldtier-dns resolver > "$OUT/AC1-both-resolver.fuzz.txt" 2>&1; b=$(now); sink AC1-both-resolver "$a" "$b"
a=$(now); v "bash $VM/rawfuzz.sh clm-staging-goldtier-egress proxy" > "$OUT/AC1-both-proxy.raw.txt" 2>&1; b=$(now); sink AC1-both-proxy-raw "$a" "$b" --r1
a=$(now); v "bash $VM/rawfuzz.sh clm-staging-goldtier-dns resolver" > "$OUT/AC1-both-resolver.raw.txt" 2>&1; b=$(now); sink AC1-both-resolver-raw "$a" "$b"
search > "$OUT/E-health-after-both.txt"

echo "== D rows"
a=$(now)
v "P=\$(sudo docker inspect -f '{{.State.Pid}}' clm-staging-goldtier-egress)
   for q in 'goldtier.r3-harness.invalid A' 'r3-fa11-\$RANDOM.invalid A' 'x.goldtier.r3-harness.invalid A' 'goldtier.r3-harness.invalid AAAA' 'goldtier.r3-harness.invalid TXT' 'goldtier.r3-harness.invalid ANY' 'example.com A'; do
     set -- \$q; printf 'D-2 %s %s -> ' \$1 \$2; sudo nsenter -t \$P -n dig +time=2 +tries=1 @172.30.241.4 \$1 \$2 | grep -o 'status: [A-Z]*' || echo no-answer; done
   printf 'D-3 proxy raw dig @172.26.0.2 -> '; sudo nsenter -t \$P -n dig +time=2 +tries=1 @172.26.0.2 example.com | grep -o 'status: [A-Z]*' || echo blocked
   printf 'D-3 proxy raw dig @1.1.1.1 -> '; sudo nsenter -t \$P -n dig +time=2 +tries=1 @1.1.1.1 example.com | grep -o 'status: [A-Z]*' || echo blocked
   R=\$(sudo docker inspect -f '{{.State.Pid}}' clm-staging-goldtier-dns)
   printf 'D-3 resolver embedded DNS 127.0.0.11 -> '; sudo nsenter -t \$R -n dig +time=2 +tries=1 @127.0.0.11 example.com | grep -o 'status: [A-Z]*' || echo blocked
   printf 'D-3 proxy embedded DNS 127.0.0.11 -> '; sudo nsenter -t \$P -n dig +time=2 +tries=1 @127.0.0.11 example.com | grep -o 'status: [A-Z]*' || echo blocked
   for n in example.com goldtier.r3-harness.invalid r3-fa11-\$RANDOM.invalid; do printf 'D-5/FA-11 backend getaddrinfo(%s) -> ' \$n
     sudo docker exec clm-staging-backend python -c \"import socket,sys
try: print(socket.getaddrinfo(sys.argv[1],443)[0][4])
except OSError as e: print('FAIL', type(e).__name__, e.errno)\" \$n; done" > "$OUT/D-rows.txt" 2>&1
b=$(now); sink D-rows "$a" "$b"
cat "$OUT/D-rows.txt"

echo "== D-6 / U-1: embedded-DNS forward namespace on Docker 29.9.3 (non-internal network)"
a=$(now)
v "for mode in nodns dns; do
     n=r3-u1-\$mode-\$RANDOM.example
     extra=\$([ \$mode = dns ] && echo '--dns 172.30.241.4' || true)
     sudo timeout 12 tcpdump -i clm-gt-up -nn -U -w /tmp/u1-\$mode.pcap udp port 53 >/dev/null 2>&1 &
     sleep 1
     sudo docker run --rm --name r3-u1-probe --network clm-staging_goldtier-uplink --ip 172.30.242.5 \$extra --entrypoint python3 clm-r3-egress:g2c -c \"import socket,sys
try: print(socket.getaddrinfo(sys.argv[1],443)[0][4])
except OSError as e: print('lookup failed', e.errno)\" \$n
     wait; echo \"mode=\$mode name=\$n bridge-capture:\"; sudo tcpdump -nn -r /tmp/u1-\$mode.pcap 2>/dev/null | head -6
   done" > "$OUT/D-6.txt" 2>&1
b=$(now); python3 -I "$T/sink_report.py" "$H/sink" "$a" "$b" "$EV" > "$OUT/D-6.sink.json"
cat "$OUT/D-6.txt"; python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print('D-6 upstream names at VPC resolver:', d['upstream_dns'])" "$OUT/D-6.sink.json"

echo "== X11: inbound from outside to the R3 bridges"
a=$(now)
# The outside namespace treats every address as local (AnyIP); carve the R3 subnets out of the
# local table for this row so the SYNs really go to the VM.
ip netns exec clmr3out ip route replace throw 172.30.240.0/22 table local
ip netns exec clmr3out ip route replace 172.30.242.0/29 via 172.26.4.119
ip netns exec clmr3out ip route replace 172.30.241.0/29 via 172.26.4.119
ip netns exec clmr3out ip route get 172.30.242.2 > "$OUT/X11.route.txt" 2>&1
v "sudo nft list table inet clm_r3 | grep -E 'oifname \"clm-gt-(up|ctl)\" counter'" > "$OUT/X11.before.txt"
for t in 172.30.242.2:4750 172.30.242.2:443 172.30.242.3:53 172.30.241.2:4750 172.30.241.3:8000; do
  printf 'X11 outside -> %s : ' "$t"; ip netns exec clmr3out timeout 3 python3 -I -c "import socket,sys; h,p=sys.argv[1].rsplit(':',1); s=socket.socket(); s.settimeout(2)
try: s.connect((h,int(p))); print('CONNECTED')
except OSError as e: print('FAILED', type(e).__name__)" "$t"
done > "$OUT/X11.txt" 2>&1
ip netns exec clmr3out ip route del 172.30.242.0/29 2>/dev/null; ip netns exec clmr3out ip route del 172.30.241.0/29 2>/dev/null
ip netns exec clmr3out ip route del throw 172.30.240.0/22 table local 2>/dev/null
v "sudo nft list table inet clm_r3 | grep -E 'oifname \"clm-gt-(up|ctl)\" counter'" > "$OUT/X11.after.txt"
b=$(now); cat "$OUT/X11.txt"

echo "== config HOST-ONLY: stand-ins with the R3 addresses and NO Layer N"
v "sudo docker stop -t 2 clm-staging-goldtier-egress clm-staging-goldtier-dns >/dev/null
   for r in proxy:172.30.241.2:172.30.242.2 dns:172.30.241.4:172.30.242.3; do IFS=: read n c u <<< \$r
     sudo docker create --name r3probe-\$n --network clm-staging_goldtier-control --ip \$c --cap-drop ALL --entrypoint /bin/sleep clm-r3-egress:g2c infinity >/dev/null
     sudo docker network connect --ip \$u clm-staging_goldtier-uplink r3probe-\$n; sudo docker start r3probe-\$n >/dev/null; done
   sudo docker ps --filter name=r3probe --format '{{.Names}} {{.Status}}'"
a=$(now); xprobe r3probe-proxy r3probe-dns host-only; b=$(now); sink X-host-only "$a" "$b" --r1
a=$(now); fuzz_in r3probe-proxy proxy > "$OUT/AC1-hostonly-proxy.fuzz.txt" 2>&1; v "bash $VM/rawfuzz.sh r3probe-proxy proxy" >> "$OUT/AC1-hostonly-proxy.fuzz.txt" 2>&1; b=$(now); sink AC1-hostonly-proxy "$a" "$b" --r1
a=$(now); fuzz_in r3probe-dns resolver > "$OUT/AC1-hostonly-resolver.fuzz.txt" 2>&1; v "bash $VM/rawfuzz.sh r3probe-dns resolver" >> "$OUT/AC1-hostonly-resolver.fuzz.txt" 2>&1; b=$(now); sink AC1-hostonly-resolver "$a" "$b"

echo "== FA-15: the same host-only probes with the empty legacy xtables tables loaded (SE-1 parity)"
v "for t in filter nat raw mangle; do sudo iptables-legacy -t \$t -S >/dev/null 2>&1; sudo ip6tables-legacy -t \$t -S >/dev/null 2>&1; done; echo legacy: \$(sudo cat /proc/net/ip_tables_names | tr '\n' ' ') modules: \$(lsmod | grep -oE '^(iptable|ip6table)_[a-z]+' | tr '\n' ' ')" > "$OUT/FA-15.legacy.txt"
a=$(now); xprobe r3probe-proxy r3probe-dns host-only-legacy; b=$(now); sink X-host-only-legacy "$a" "$b" --r1
v "sudo docker rm -f r3probe-proxy r3probe-dns >/dev/null; bash ~/r3/tests/deploy/egress_harness/vm/rlvm.sh recover" > "$OUT/recover-after-hostonly.txt" 2>&1
a=$(now); xprobe clm-staging-goldtier-egress clm-staging-goldtier-dns both-legacy; b=$(now); sink X-both-legacy "$a" "$b" --r1

echo "== config LAYER-N-ONLY: host table removed with the watcher frozen (harness construct)"
v "sudo systemctl kill -s STOP clm-r3-firewall-watch; sudo nft delete table inet clm_r3; sudo nft list tables"
a=$(now); fuzz_in clm-staging-goldtier-egress proxy > "$OUT/AC1-layerN-proxy.fuzz.txt" 2>&1; b=$(now); sink AC1-layerN-proxy "$a" "$b" --r1
a=$(now); fuzz_in clm-staging-goldtier-dns resolver > "$OUT/AC1-layerN-resolver.fuzz.txt" 2>&1; b=$(now); sink AC1-layerN-resolver "$a" "$b"
a=$(now); xprobe clm-staging-goldtier-egress clm-staging-goldtier-dns layerN-only; b=$(now); sink X-layerN-only "$a" "$b" --r1
v "sudo systemctl start clm-r3-egress-firewall; sudo systemctl restart clm-r3-egress-firewall; sudo systemctl kill -s CONT clm-r3-firewall-watch; sleep 3; bash ~/r3/tests/deploy/egress_harness/vm/rlvm.sh recover" > "$OUT/recover-after-layerN.txt" 2>&1
search > "$OUT/E-health-end.txt"; cat "$OUT/E-health-end.txt"
v "sudo journalctl -u clm-r3-firewall-watch -o cat --no-pager | tail -40" > "$OUT/watcher.journal.txt"
echo "done: $OUT"
