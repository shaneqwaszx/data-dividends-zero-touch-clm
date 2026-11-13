#!/bin/bash
# R3 G2 Amendment A runtime-loss helpers (harness VM only). Every timestamp is VM-clock epoch.
#   rlvm.sh monitors-start | monitors-stop        timestamped nft monitor + docker events
#   rlvm.sh load-start <secs> | load-collect      disallowed-target load, child uid AND root, both containers
#   rlvm.sh tunnel-start | tunnel-collect         an established tunnel through the proxy (backend side)
#   rlvm.sh fault <RL-id>                          inject one fault; prints "FAULT <id> <t>"
#   rlvm.sh recover                               operator recovery: table, watcher, containers, health
#   rlvm.sh state                                 table/watcher/container state summary
set -uo pipefail
R3=${R3_SRC:-$HOME/r3}
H=$R3/tests/deploy/egress_harness/vm
EG=clm-staging-goldtier-egress; DNS=clm-staging-goldtier-dns
now() { date +%s.%N; }
case "$1" in
  monitors-start)
    sudo pkill -f 'nft monitor' 2>/dev/null; sudo pkill -f 'docker events' 2>/dev/null
    sudo rm -f /tmp/r3-nftmon.txt /tmp/r3-dev.txt
    sudo setsid bash -c 'nft monitor | while IFS= read -r l; do echo "$(date +%s.%N) $l"; done >> /tmp/r3-nftmon.txt' </dev/null >/dev/null 2>&1 &
    sudo setsid bash -c "docker events --filter container=$EG --filter container=$DNS --format '{{.TimeNano}} {{.Action}} {{.Actor.Attributes.name}} exit={{.Actor.Attributes.exitCode}}' >> /tmp/r3-dev.txt" </dev/null >/dev/null 2>&1 &
    sleep 1; echo monitors started ;;
  monitors-stop)
    sudo pkill -f 'nft monitor'; sudo pkill -f 'docker events'; sleep 0.5
    echo "--- nft monitor"; sudo cat /tmp/r3-nftmon.txt | grep -E 'table inet clm_r3|delete|add rule inet clm_r3|add element inet clm_r3|flush' | cut -c1-200
    echo "--- docker events"; sudo cat /tmp/r3-dev.txt ;;
  load-start)
    S=$2; sudo rm -f /tmp/r3-lg-*.json
    for c in $EG $DNS; do role=$([ $c = $EG ] && echo proxy || echo resolver)
      for who in child root; do U=$([ $who = child ] && echo "-u 65532:65532" || echo "")
        sudo setsid bash -c "docker exec -i $U $c python3 -I - loadgen $role $S < $H/loadgen.py > /tmp/r3-lg-$c-$who.json 2>&1" </dev/null >/dev/null 2>&1 &
      done; done; sleep 0.5; echo "load started $(now)" ;;
  load-collect)
    # last line per generator, plus totals across its streamed lines (a killed generator still counts)
    for f in /tmp/r3-lg-*.json; do echo "$(basename $f): lines=$(sudo grep -c '^{' $f) last=$(sudo grep '^{' $f | tail -1) errors=$(sudo grep -vc '^{' $f)"; done ;;
  tunnel-start)
    sudo rm -f /tmp/r3-tunnel.txt
    sudo setsid bash -c "docker exec -i clm-staging-backend python3 -I - > /tmp/r3-tunnel.txt 2>&1 <<'PY'
import socket, ssl, time
s = socket.create_connection(('172.30.241.2', 4750), timeout=5)
s.sendall(b'CONNECT goldtier.r3-harness.invalid:443 HTTP/1.1\r\nHost: goldtier.r3-harness.invalid:443\r\n\r\n')
print('connect', s.recv(256).split(b'\r\n')[0].decode(), flush=True)
ctx = ssl.create_default_context(cafile='/run/clm/r3-test-ca.pem')
t = ctx.wrap_socket(s, server_hostname='goldtier.r3-harness.invalid'); t.settimeout(30)
t.sendall(b'GET /harness/hold HTTP/1.1\r\nHost: goldtier.r3-harness.invalid\r\n\r\n')
last = time.time(); n = 0
try:
    while True:
        b = t.recv(64)
        if not b: break
        n += len(b); last = time.time()
    print('tunnel_end eof', round(last, 3), 'bytes', n, flush=True)
except OSError as e:
    print('tunnel_end', type(e).__name__, round(last, 3), 'bytes', n, flush=True)
PY" </dev/null >/dev/null 2>&1 &
    sleep 2; sudo cat /tmp/r3-tunnel.txt ;;
  tunnel-collect) sudo cat /tmp/r3-tunnel.txt ;;
  fault)
    T=$(now)
    case "$2" in
      RL-1) sudo systemctl stop clm-r3-egress-firewall ;;
      RL-2) sudo nft delete table inet clm_r3 ;;
      RL-3a) h=$(sudo nft -a list chain inet clm_r3 forward | grep 'ip daddr @no_egress_v4 counter' | grep -o 'handle [0-9]*' | cut -d' ' -f2)
             sudo nft delete rule inet clm_r3 forward handle "$h" ;;
      RL-3b) sudo nft delete element inet clm_r3 no_egress_v4 '{ 169.254.0.0/16 }' ;;
      RL-3c) sudo nft insert rule inet clm_r3 forward iifname '"clm-gt-up"' accept ;;
      RL-4) sudo nft flush ruleset ;;
      RL-5a) sudo systemctl kill -s KILL clm-r3-firewall-watch ;;
      RL-5b) sudo systemctl stop clm-r3-firewall-watch ;;
      RL-7a) sudo docker exec $EG nft delete table inet clm_r3n ;;
      RL-7b) sudo docker exec $EG nft insert rule inet clm_r3n output accept ;;
      RL-7c) sudo docker exec $DNS nft flush table inet clm_r3n ;;
      RL-8) sudo systemctl restart docker ;;
      *) echo "unknown fault $2"; exit 2 ;;
    esac
    echo "FAULT $2 $T rc=$?" ;;
  recover)
    sudo systemctl kill -s CONT clm-r3-firewall-watch 2>/dev/null
    sudo systemctl is-active -q docker || sudo systemctl start docker
    # A flushed ruleset (RL-4) removes Docker's own NAT and filter chains; only a Docker restart
    # rebuilds them (site-level outage, outside R3 control).
    sudo nft list table ip nat >/dev/null 2>&1 || { echo "docker NAT missing: restarting docker"; sudo systemctl restart docker; sleep 5; }
    sudo systemctl restart clm-r3-egress-firewall
    sudo systemctl is-active -q clm-r3-firewall-watch || sudo systemctl start clm-r3-firewall-watch
    sleep 2
    sudo docker start $DNS >/dev/null 2>&1; sleep 3; sudo docker start $EG >/dev/null 2>&1
    for i in $(seq 1 60); do
      [ "$(sudo docker inspect -f '{{.State.Health.Status}}' $EG 2>/dev/null)" = healthy ] && \
      [ "$(sudo docker inspect -f '{{.State.Health.Status}}' $DNS 2>/dev/null)" = healthy ] && \
      [ "$(sudo docker inspect -f '{{.State.Health.Status}}' clm-staging-backend 2>/dev/null)" = healthy ] && break; sleep 1; done
    "$0" state ;;
  state)
    echo "table: $(sudo python3 -I /usr/local/lib/clm-r3/clm_r3_watch.py --table-file /etc/clm/r3/clm_r3.nft --containers x --check-only | tr -d '\n')"
    echo "units: fw=$(systemctl is-active clm-r3-egress-firewall) watch=$(systemctl is-active clm-r3-firewall-watch) docker=$(systemctl is-active docker)"
    sudo docker ps -a --format '{{.Names}} {{.Status}}' | grep -E 'goldtier|backend|frontend|mongo' | sort ;;
  *) echo "usage" >&2; exit 2 ;;
esac
