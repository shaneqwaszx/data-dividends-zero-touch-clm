#!/bin/bash
# R3 G2 S4 E-rows (harness side, root): E-1 to E-4 through the real product path.
#   E-1 HR Sandbox Search -> proxy -> fake GoldTier (test CA): MATCH_FOUND, TLS 1.3, SNI = FQDN
#   E-2 upstream presents a valid-chain certificate for a DIFFERENT name: controlled failure,
#       no retry outside the proxy
#   E-3 proxy outage and recovery with no backend restart
#   E-4 deploy/smoke.py and apps/assistant/deploy/smoke_hosted.py, unchanged, on the same images
#   HARNESS=/root/clm-r3-harness VSSH="<vm shell>" run_matrix_e.sh <outdir>
set -uo pipefail
OUT=$1; mkdir -p "$OUT"
H=${HARNESS:-/root/clm-r3-harness}
VSSH=${VSSH:-$H/bin/vssh.sh net}
T=$(cd "$(dirname "$0")" && pwd)
VM='~/r3/tests/deploy/egress_harness/vm'
EV=$H/sink/outside-events.jsonl
ZONE=$H/run/zone.json
v() { $VSSH "$@"; }
now() { date +%s.%N; }
zone() { printf '%s\n' "$1" > "$ZONE"; }
ev() { python3 - "$EV" "$1" "$2" <<'PY'
import json, sys
a, b = float(sys.argv[2]), float(sys.argv[3])
for line in open(sys.argv[1]):
    r = json.loads(line)
    if a <= r["t"] <= b and r["kind"] in ("gt_request", "gt_tls_fail", "dns_query", "LEAK_tcp", "LEAK_udp"):
        print(json.dumps(r, sort_keys=True))
PY
}
GOOD='{"fqdn":"goldtier.r3-harness.invalid","mode":"static","a":["34.120.0.10"],"ttl":0}'
WRONG='{"fqdn":"goldtier.r3-harness.invalid","mode":"static","a":["34.120.0.11"],"ttl":0}'

echo "== E-1"; zone "$GOOD"
a=$(now); v "sudo python3 -I $VM/e_client.py search" | tee "$OUT/E-1.jsonl"; b=$(now)
ev "$a" "$b" > "$OUT/E-1.events.jsonl"; cat "$OUT/E-1.events.jsonl"
v "sudo docker logs --since 30s clm-staging-goldtier-egress 2>&1 | grep CANONICAL-PROXY-DECISION | tail -1 | cut -c1-400" > "$OUT/E-1.proxy-decision.txt"

echo "== E-2 wrong certificate name at the resolved address"; zone "$WRONG"
a=$(now); v "sudo python3 -I $VM/e_client.py search" | tee "$OUT/E-2.jsonl"; b=$(now); zone "$GOOD"
ev "$a" "$b" > "$OUT/E-2.events.jsonl"; cat "$OUT/E-2.events.jsonl"
python3 -I "$T/sink_report.py" "$H/sink" "$a" "$b" "$EV" --r1 > "$OUT/E-2.sink.json"; cat "$OUT/E-2.sink.json"

echo "== E-3 proxy outage and recovery (no backend restart)"
B0=$(v "sudo docker inspect -f '{{.State.StartedAt}}' clm-staging-backend")
v "sudo docker stop -t 0 clm-staging-goldtier-egress >/dev/null; sudo python3 -I $VM/e_client.py search; sudo python3 -I $VM/e_client.py health
   sudo docker start clm-staging-goldtier-egress >/dev/null
   for i in \$(seq 1 60); do [ \"\$(sudo docker inspect -f '{{.State.Health.Status}}' clm-staging-goldtier-egress)\" = healthy ] && break; sleep 1; done
   sudo python3 -I $VM/e_client.py search" | tee "$OUT/E-3.jsonl"
B1=$(v "sudo docker inspect -f '{{.State.StartedAt}}' clm-staging-backend")
echo "backend StartedAt before=$B0 after=$B1 restarted=$([ "$B0" = "$B1" ] && echo no || echo YES)" | tee -a "$OUT/E-3.jsonl"

echo "== E-4 unchanged smokes (stack down first: they create their own projects)"
v "bash $VM/stack.sh down; cd ~/r3 && sudo python3 -B deploy/smoke.py clm-r3-backend:g2 clm-r3-frontend:g2" > "$OUT/E-4.smoke.txt" 2>&1; echo "deploy/smoke.py rc=$?" | tee -a "$OUT/E-4.smoke.txt"
grep -E '^(PASS|FAIL)|Traceback|Error' "$OUT/E-4.smoke.txt" | head -20
v "cd ~/r3 && sudo python3 -B apps/assistant/deploy/smoke_hosted.py clm-r3-backend:g2 clm-r3-frontend:g2 clm-r3-assistant:g2 /tmp/r3-smoke-hosted.json; echo rc=\$?; sudo cat /tmp/r3-smoke-hosted.json" > "$OUT/E-4.smoke_hosted.txt" 2>&1
grep -E 'rc=|passed|PASS|FAIL|"result"|"passed"|16' "$OUT/E-4.smoke_hosted.txt" | head -12
v "bash $VM/stack.sh up sandbox | tail -6"
echo "done: $OUT"
