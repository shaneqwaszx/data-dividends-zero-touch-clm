#!/bin/bash
# R3 G2 S4 phase B (harness side, root): Amendment A runtime-loss suite RL-1..RL-12 (+FA-16,
# FA-B1, FA-B2). Every row runs a disallowed-destination load from inside both R3 containers (as
# the child uid and as root) across the fault, records the sink, the watcher/guard logs, Docker
# events (stop latency), the established tunnel's fate and backend health/Search, then recovers.
#   HARNESS=/root/clm-r3-harness VSSH="<vm shell>" run_matrix_b.sh <outdir> [rows...]
set -uo pipefail
OUT=$1; shift; mkdir -p "$OUT"
ROWS=${*:-RL-1 RL-2 RL-3a RL-3b RL-3c RL-4 RL-5a RL-5b RL-6 RL-7a RL-7b RL-7c RL-8 RL-11 RL-12 RL-9 RL-10}
H=${HARNESS:-/root/clm-r3-harness}
VSSH=${VSSH:-$H/bin/vssh.sh net}
T=$(cd "$(dirname "$0")" && pwd)
VM='~/r3/tests/deploy/egress_harness/vm'
EV=$H/sink/outside-events.jsonl
v() { $VSSH "$@"; }
now() { date +%s.%N; }
rl() { v "bash $VM/rlvm.sh $*"; }
checks() {  # backend health, Sandbox Search and the Mock onboarding lane
  v "sudo python3 -I $VM/e_client.py health; sudo python3 -I $VM/e_client.py search; sudo python3 -I $VM/e_client.py mockcase" 2>&1 | grep '^{' || echo '{"row":"checks","error":"client failed"}'
}
logs_since() {  # logs_since <vm-epoch>
  local since=${1%.*}
  v "sudo journalctl -u clm-r3-firewall-watch -u clm-r3-egress-firewall -o short-unix --since @$since --no-pager | grep -E 'CLM_R3|Stopp|Start|Deactivat|Main process' | cut -c1-260
     for c in clm-staging-goldtier-egress clm-staging-goldtier-dns; do sudo docker logs --since $since \$c 2>&1 | grep r3-egress-guard | grep -v canaries_passed | cut -c1-220; done" 2>/dev/null
}
row() {  # row <id> <seconds-after-fault>
  local id=$1 wait=$2 d="$OUT/$1"; mkdir -p "$d"
  echo "== $id"
  rl state > "$d/state-before.txt" 2>&1
  rl monitors-start >/dev/null
  rl tunnel-start > "$d/tunnel-start.txt" 2>&1
  local a; a=$(now)
  rl load-start $((wait + 8)) > "$d/load-start.txt"
  sleep 3
  case $id in
    RL-6) v "CAP_CONTAINERS='clm-staging-goldtier-egress clm-staging-goldtier-dns' bash $VM/cap_checks.sh" > "$d/cap_checks.txt" 2>&1
          echo "FAULT RL-6 $(v 'date +%s.%N') (child-uid tamper suite; see cap_checks.txt)" > "$d/fault.txt" ;;
    RL-11) v "sudo systemctl kill -s STOP clm-r3-firewall-watch; T=\$(date +%s.%N); sudo nft delete table inet clm_r3
              for i in 1 2 3; do sudo docker restart -t 2 clm-staging-goldtier-egress >/dev/null; sudo docker restart -t 2 clm-staging-goldtier-dns >/dev/null; sleep 4; done
              C=\$(date +%s.%N); sudo systemctl kill -s CONT clm-r3-firewall-watch; echo \"FAULT RL-11 \$T watcher_resumed \$C\"" > "$d/fault.txt" ;;
    RL-12) v "sudo docker rm -f clm-staging-goldtier-egress >/dev/null
              sudo docker create --name clm-staging-goldtier-egress --cap-drop ALL --network clm-staging_goldtier-control --ip 172.30.241.2                 --entrypoint /bin/sleep clm-r3-egress:g2c 300 >/dev/null
              sudo docker network connect --ip 172.30.242.2 clm-staging_goldtier-uplink clm-staging-goldtier-egress
              sudo docker start clm-staging-goldtier-egress >/dev/null; sleep 1
              sudo setsid bash -c 'docker exec -i clm-staging-goldtier-egress python3 -I - loadgen proxy 12 < /home/ubuntu/r3/tests/deploy/egress_harness/vm/loadgen.py > /tmp/r3-rl12-load.json 2>&1' </dev/null >/dev/null 2>&1 &
              sleep 1; T=\$(date +%s.%N); sudo nft delete table inet clm_r3; echo \"FAULT RL-12 \$T (both layers absent: unguarded construct with the proxy addresses, no Layer N, host table deleted)\"" > "$d/fault.txt" ;;
    RL-9|RL-10)
          v "sudo install -m 0755 $VM/r3-boot-load.sh /usr/local/sbin/r3-boot-load.sh
             printf '[Unit]\nAfter=docker.service\n[Service]\nType=oneshot\nExecStart=/usr/local/sbin/r3-boot-load.sh\n[Install]\nWantedBy=multi-user.target\n' | sudo tee /etc/systemd/system/r3-boot-load.service >/dev/null
             sudo rm -rf /var/log/r3-boot-load; sudo systemctl daemon-reload; sudo systemctl enable r3-boot-load.service >/dev/null 2>&1
             if [ $id = RL-10 ]; then sudo mkdir -p /etc/systemd/system/clm-r3-egress-firewall.service.d
               printf '[Service]\nExecStart=\nExecStart=/bin/false\n' | sudo tee /etc/systemd/system/clm-r3-egress-firewall.service.d/zz-harness-fail.conf >/dev/null; sudo systemctl daemon-reload; fi
             echo \"FAULT $id \$(date +%s.%N) reboot\"; sudo systemctl reboot" > "$d/fault.txt" 2>&1
          sleep 15; $H/bin/waitssh.sh net 300 >> "$d/fault.txt" ;;
    *) rl fault "$id" > "$d/fault.txt" 2>&1 ;;
  esac
  sleep "$wait"
  checks > "$d/checks-during.jsonl"
  [ $id = RL-9 ] || [ $id = RL-10 ] && sleep 100
  local b; b=$(now)
  sleep 2
  rl load-collect > "$d/load.txt" 2>&1
  [ $id = RL-12 ] && v "sudo cat /tmp/r3-rl12-load.json" >> "$d/load.txt" 2>&1
  [ $id = RL-9 ] || [ $id = RL-10 ] && v "for f in /var/log/r3-boot-load/*.json; do echo \"\$f progress_lines=\$(grep -c progress \$f) escape_lines=\$(grep progress \$f | grep -vc '\"escapes\": {}') first=\$(grep -m1 progress \$f | cut -c1-60) errors=\$(grep -vc '^{' \$f)\"; done; sudo cat /var/log/r3-boot-load/log
     sudo journalctl -b -o short-unix --no-pager -u clm-r3-egress-firewall -u docker -u clm-r3-firewall-watch -u containerd | grep -E 'Started|Starting|Finished|Failed|failed|CLM_R3|API listen' | head -30
     sudo systemctl disable r3-boot-load.service >/dev/null 2>&1; sudo rm -f /etc/systemd/system/r3-boot-load.service /etc/systemd/system/clm-r3-egress-firewall.service.d/zz-harness-fail.conf; sudo systemctl daemon-reload" > "$d/boot.txt" 2>&1
  rl tunnel-collect > "$d/tunnel.txt" 2>&1
  rl monitors-stop > "$d/monitors.txt" 2>&1
  local ft; ft=$(awk '/^FAULT/{print $3; exit}' "$d/fault.txt")
  logs_since "${ft:-$(v 'date +%s')}" > "$d/logs.txt"
  rl state > "$d/state-after-fault.txt" 2>&1
  python3 -I "$T/sink_report.py" "$H/sink" "$a" "$b" "$EV" > "$d/sink.json"
  if [ $id = RL-12 ]; then v "sudo docker rm -f clm-staging-goldtier-egress >/dev/null 2>&1; bash $VM/stack.sh dcg up -d --no-build goldtier-egress >/dev/null 2>&1"; fi
  rl recover > "$d/recover.txt" 2>&1
  checks > "$d/checks-after.jsonl"
  python3 - "$d" <<'PY'
import json, os, re, sys
d = sys.argv[1]
sink = json.load(open(os.path.join(d, "sink.json")))
fault = open(os.path.join(d, "fault.txt")).read().split()
ft = float(fault[2]) if len(fault) > 2 and re.match(r"^\d+\.\d+$", fault[2]) else None
dies = {}
for line in open(os.path.join(d, "monitors.txt")):
    p = line.split()
    if len(p) >= 3 and p[1] == "die" and p[0].isdigit() and (ft is None or int(p[0]) / 1e9 >= ft):
        dies.setdefault(p[2], int(p[0]) / 1e9)
lat = {k: round(v - ft, 3) for k, v in dies.items()} if ft else {}
during = [json.loads(l) for l in open(os.path.join(d, "checks-during.jsonl")) if l.startswith("{")]
after = [json.loads(l) for l in open(os.path.join(d, "checks-after.jsonl")) if l.startswith("{")]
tunnel = open(os.path.join(d, "tunnel.txt")).read().strip().replace("\n", " | ")
print(f"  sink zero_disallowed={sink['zero_disallowed']} classes={sink['classes']} disallowed={sink['disallowed_packets']} non_fqdn_dns={sink['non_fqdn_dns']} leaks={sink['sink_leak_events']}")
print(f"  stop latency from fault (s): {lat}")
print(f"  during: {[(c.get('row'), c.get('http'), c.get('status') or c.get('environment') or c.get('case_created'), c.get('error_code')) for c in during]}")
print(f"  after : {[(c.get('row'), c.get('http'), c.get('status') or c.get('environment') or c.get('case_created')) for c in after]}")
print(f"  tunnel: {tunnel[:220]}")
json.dump({"row": os.path.basename(d), "sink": sink, "stop_latency_s": lat, "during": during, "after": after, "tunnel": tunnel},
          open(os.path.join(d, "summary.json"), "w"), indent=1, sort_keys=True)
PY
}
for r in $ROWS; do
  case $r in
    RL-1|RL-2|RL-3a|RL-3b|RL-3c|RL-4|RL-5a|RL-5b|RL-7a|RL-7b|RL-7c|RL-12) row "$r" 10 ;;
    RL-6) row RL-6 2 ;;
    RL-8) row RL-8 25 ;;
    RL-11) row RL-11 6 ;;
    RL-9|RL-10) row "$r" 5 ;;
  esac
done
echo "done: $OUT"
