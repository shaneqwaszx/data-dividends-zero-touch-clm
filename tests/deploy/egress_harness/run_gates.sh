#!/bin/bash
# R3 G2 S2: Smokescreen and DNS hard gates (P-1..P-10, D-1/D-2/D-7 in the gate rig).
# Harness side (root, WSL2), with the sealed VM up and outside.py running in clmr3out.
#   HARNESS=/root/clm-r3-harness VSSH="<cmd that runs a VM shell command>" run_gates.sh <outdir>
set -uo pipefail
OUT=$1; mkdir -p "$OUT"
H=${HARNESS:-/root/clm-r3-harness}
VSSH=${VSSH:-$H/bin/vssh.sh net}
FQDN=goldtier.r3-harness.invalid
GATE_IMAGE=${GATE_IMAGE:-clm-r3-egress:g2c-gate}
# QG P3-4: gate_rig.sh refuses to start unless the image's smokescreen has this exact hash.
EXPECTED_SMOKESCREEN_SHA256=${EXPECTED_SMOKESCREEN_SHA256:-3651c1cfa070a2c9929ad275d943881f99b4bdc84a46e322038ffae00be271b4}
GT=34.120.0.10
ZONE=$H/run/zone.json
EV=$H/sink/outside-events.jsonl
v() { $VSSH "$@"; }
zone() { printf '%s\n' "$1" > "$ZONE"; }
client() { v "sudo docker exec r3gate-client python3 /r3/gate_client.py $(printf '%q ' "$@")"; }
mark() { date +%s.%N > "$OUT/t_$1"; }
events_between() { python3 - "$EV" "$(cat "$OUT/t_$1")" "$(cat "$OUT/t_$2")" <<'PY'
import json, sys
path, a, b = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
for line in open(path):
    try:
        r = json.loads(line)
    except ValueError:
        continue
    if a <= r.get("t", 0) <= b:
        print(json.dumps(r, sort_keys=True))
PY
}
cap_start() {  # capture every packet the proxy and resolver namespaces emit or receive
  v "sudo systemctl stop r3cap-proxy r3cap-dns 2>/dev/null; sudo rm -f /tmp/r3cap-*.pcap
     for c in proxy dns; do P=\$(sudo docker inspect -f '{{.State.Pid}}' r3gate-\$c)
       sudo systemd-run -q --unit r3cap-\$c nsenter -t \$P -n tcpdump -i any -nn -s 160 -U -w /tmp/r3cap-\$c.pcap; done; sleep 1"
}
cap_stop() {
  v "sleep 1; sudo systemctl stop r3cap-proxy r3cap-dns; for c in proxy dns; do sudo tcpdump -nn -tttt -r /tmp/r3cap-\$c.pcap 2>/dev/null; done" > "$OUT/$1.cap.txt"
}

echo "== rig up"
zone "{\"fqdn\":\"$FQDN\",\"mode\":\"static\",\"a\":[\"$GT\"],\"ttl\":0}"
v "GATE_IMAGE=$GATE_IMAGE EXPECTED_SMOKESCREEN_SHA256=$EXPECTED_SMOKESCREEN_SHA256 R3_SRC=\$HOME/r3 bash ~/r3/tests/deploy/egress_harness/vm/gate_rig.sh up $FQDN" | tee "$OUT/rig.txt"
v "sudo docker inspect r3gate-proxy --format '{{json .Config.Entrypoint}} {{json .Args}} {{json .Config.Env}} {{.HostConfig.CapDrop}} {{.HostConfig.CapAdd}} {{.Config.User}} image={{.Image}}'" > "$OUT/P-8.argv.txt"
cap_start

echo "== P-1 / D-1"
mark p1a; client p1 $FQDN /r3/ca.pem | tee "$OUT/P-1.jsonl"; mark p1b
events_between p1a p1b > "$OUT/P-1.events.jsonl"

echo "== P-2"
mark p2a; client p2 $FQDN | tee "$OUT/P-2.jsonl"; mark p2b
events_between p2a p2b > "$OUT/P-2.events.jsonl"

echo "== P-3"
mark p3a; client p3 $FQDN | tee "$OUT/P-3.jsonl"; mark p3b
events_between p3a p3b > "$OUT/P-3.events.jsonl"

echo "== P-2b (QG P3-3): a second, non-exact head after a refused exact CONNECT"
# First answer of each burst prohibited (so the exact CONNECT is refused); any re-query within 2 s
# would get the ALLOWED answer, so a processed second request would tunnel. It must never be.
zone "{\"fqdn\":\"$FQDN\",\"mode\":\"then_allowed\",\"a\":[\"$GT\"],\"prohibited\":[\"169.254.169.254\"],\"window\":2.0,\"ttl\":0}"
mark p2ba; client p2b $FQDN | tee "$OUT/P-2b.jsonl"; mark p2bb
events_between p2ba p2bb > "$OUT/P-2b.events.jsonl"
zone "{\"fqdn\":\"$FQDN\",\"mode\":\"static\",\"a\":[\"$GT\"],\"ttl\":0}"

echo "== P-4 (A answers in prohibited space, through DNS-2)"
: > "$OUT/P-4.jsonl"; mark p4a
for ip in 0.0.0.1 10.0.0.1 100.64.0.1 127.0.0.1 169.254.169.254 169.254.169.253 172.16.0.1 172.26.0.1 \
          172.26.0.2 172.26.4.119 172.30.241.1 172.30.241.3 172.30.242.1 192.0.0.8 192.0.2.1 \
          192.88.99.1 192.168.1.1 198.18.0.1 198.51.100.1 203.0.113.1 224.0.0.1 239.255.255.250 \
          240.0.0.1 255.255.255.255; do
  zone "{\"fqdn\":\"$FQDN\",\"mode\":\"static\",\"a\":[\"$ip\"],\"ttl\":0}"
  client p1 $FQDN /r3/ca.pem | sed "s/^{/{\"answer\":\"$ip\",/" >> "$OUT/P-4.jsonl"
done; mark p4b
events_between p4a p4b > "$OUT/P-4.events.jsonl"

echo "== P-5 rebinding: TTL 0, alternating allowed and prohibited, 200 attempts each"
for bad in 169.254.169.254 127.0.0.1; do
  zone "{\"fqdn\":\"$FQDN\",\"mode\":\"alternate\",\"a\":[\"$GT\"],\"prohibited\":[\"$bad\"],\"ttl\":0}"
  mark "p5a_$bad"; client loop $FQDN /r3/ca.pem 200 0 > "$OUT/P-5.$bad.jsonl"; mark "p5b_$bad"
  events_between "p5a_$bad" "p5b_$bad" > "$OUT/P-5.$bad.events.jsonl"
done

echo "== P-6 DNS-to-connect race: first answer allowed, any re-resolution within 0.5 s prohibited"
zone "{\"fqdn\":\"$FQDN\",\"mode\":\"first_then\",\"a\":[\"$GT\"],\"prohibited\":[\"169.254.169.254\"],\"window\":0.5,\"ttl\":0}"
mark p6a; client loop $FQDN /r3/ca.pem 200 0.7 > "$OUT/P-6.jsonl"; mark p6b
events_between p6a p6b > "$OUT/P-6.events.jsonl"

echo "== P-7 mixed answers (both orders)"
: > "$OUT/P-7.jsonl"; mark p7a
for order in "\"169.254.169.254\",\"$GT\"" "\"$GT\",\"169.254.169.254\"" "\"10.0.0.1\",\"$GT\",\"127.0.0.1\""; do
  zone "{\"fqdn\":\"$FQDN\",\"mode\":\"static\",\"a\":[$order],\"ttl\":0}"
  for i in 1 2 3 4 5; do client p1 $FQDN /r3/ca.pem | sed "s/^{/{\"answers\":\"$(echo $order | tr -d '\"')\",/" >> "$OUT/P-7.jsonl"; done
done; mark p7b
events_between p7a p7b > "$OUT/P-7.events.jsonl"
zone "{\"fqdn\":\"$FQDN\",\"mode\":\"static\",\"a\":[\"$GT\"],\"ttl\":0}"

echo "== D-2 resolver refusals (queried directly from the proxy namespace)"
v "P=\$(sudo docker inspect -f '{{.State.Pid}}' r3gate-proxy); for q in '$FQDN A' 'random-$RANDOM.invalid A' 'x.$FQDN A' '$FQDN AAAA' '$FQDN TXT' '$FQDN ANY' 'example.com A' '$FQDN MX'; do set -- \$q; printf '%s %s -> ' \$1 \$2; sudo nsenter -t \$P -n dig +time=2 +tries=1 @172.30.241.4 \$1 \$2 | grep -o 'status: [A-Z]*'; done; printf 'tcp %s A -> ' $FQDN; sudo nsenter -t \$P -n dig +tcp +time=2 +tries=1 @172.30.241.4 $FQDN A | grep -o 'status: [A-Z]*'" | tee "$OUT/D-2.txt"
mark d2b

echo "== P-10 / D-7: stop the resolver; lookups must fail with no fallback"
v "sudo docker stop -t 1 r3gate-dns >/dev/null"
mark p10a; client p1 $FQDN /r3/ca.pem | tee "$OUT/P-10.jsonl"; mark p10b
events_between p10a p10b > "$OUT/P-10.events.jsonl"
v "sudo docker start r3gate-dns >/dev/null; sleep 2"
cap_stop gates
v "sudo docker logs r3gate-proxy 2>&1" > "$OUT/smokescreen.log"
v "sudo docker logs r3gate-dns 2>&1" > "$OUT/coredns.log"

echo "== P-8: hostile proxy environment (the guard strips it in production; this tests the binary)"
v "GATE_IMAGE=$GATE_IMAGE EXPECTED_SMOKESCREEN_SHA256=$EXPECTED_SMOKESCREEN_SHA256 R3_SRC=\$HOME/r3 bash ~/r3/tests/deploy/egress_harness/vm/gate_rig.sh up $FQDN hostile" >> "$OUT/rig.txt"
cap_start
mark p8a; client p1 $FQDN /r3/ca.pem | tee "$OUT/P-8.hostile.jsonl"
client raw "GET http://$FQDN:443/ HTTP/1.1" "$FQDN:443" | tee -a "$OUT/P-8.hostile.jsonl"
client raw "CONNECT 169.254.169.254:443 HTTP/1.1" | tee -a "$OUT/P-8.hostile.jsonl"; mark p8b
events_between p8a p8b > "$OUT/P-8.events.jsonl"
cap_stop p8
v "sudo docker logs r3gate-proxy 2>&1" > "$OUT/smokescreen-hostile.log"
v "sudo docker exec r3gate-proxy smokescreen --help" > "$OUT/P-8.help.txt" 2>&1
v "GATE_IMAGE=$GATE_IMAGE EXPECTED_SMOKESCREEN_SHA256=$EXPECTED_SMOKESCREEN_SHA256 R3_SRC=\$HOME/r3 bash ~/r3/tests/deploy/egress_harness/vm/gate_rig.sh down"
echo "done: $OUT"
