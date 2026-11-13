#!/bin/bash
# R3 G2 S2 gate rig (harness VM only). Runs the pinned Smokescreen build and the DNS-2 CoreDNS
# resolver on the real R3 networks, with NO firewall layer, so every gate result is
# attributable to Smokescreen/CoreDNS alone.
#   gate_rig.sh up <fqdn> [hostile-env]    gate_rig.sh down
set -euo pipefail
IMG=${GATE_IMAGE:-clm-r3-egress:g2c-gate}
WANT=${EXPECTED_SMOKESCREEN_SHA256:-3651c1cfa070a2c9929ad275d943881f99b4bdc84a46e322038ffae00be271b4}
W=/tmp/r3gate
down() {
  for c in r3gate-client r3gate-proxy r3gate-dns; do sudo docker rm -f "$c" >/dev/null 2>&1 || true; done
  for n in clm-gt-ctl clm-gt-up; do sudo docker network rm "$n" >/dev/null 2>&1 || true; done
}
case "${1:-}" in
  down) down; exit 0 ;;
  up) ;;
  *) echo "usage: $0 up <fqdn> [hostile-env] | down" >&2; exit 2 ;;
esac
FQDN=$2; HOSTILE=${3:-}
# QG P3-4: the executable under test must be the reviewed binary, whatever the tag says.
GOT=$(sudo docker run --rm --network none --entrypoint sha256sum "$IMG" /usr/local/bin/smokescreen | cut -d' ' -f1)
if [ "$GOT" != "$WANT" ]; then echo "REFUSED: $IMG smokescreen sha256 $GOT != expected $WANT" >&2; exit 3; fi
echo "image $IMG $(sudo docker image inspect -f '{{.Id}}' "$IMG") smokescreen sha256 $GOT (expected)"
down
mkdir -p "$W"; chmod 755 "$W"
sed -e "s/@FQDN@/$FQDN/" -e "s/@LISTEN@/172.30.241.4/" -e "s/@UPSTREAM@/172.26.0.2/" \
  "${R3_SRC:-$HOME/r3}/deploy/egress/Corefile.template" > "$W/Corefile"
cat > "$W/acl.yaml" <<ACL
---
version: v1
services:
  - name: goldtier-backend
    project: r3
    action: enforce
    allowed_domains:
      - $FQDN
default:
  project: r3
  action: enforce
ACL
cp "${R3_SRC:-$HOME/r3}/tests/deploy/egress_harness/vm/gate_client.py" "${R3_SRC:-$HOME/r3}/pki/ca.pem" "$W/"
chmod 644 "$W"/*
sudo docker network create --driver bridge --internal --subnet 172.30.241.0/29 --gateway 172.30.241.1 \
  -o com.docker.network.bridge.name=clm-gt-ctl clm-gt-ctl >/dev/null
sudo docker network create --driver bridge --subnet 172.30.242.0/29 --gateway 172.30.242.1 \
  -o com.docker.network.bridge.name=clm-gt-up clm-gt-up >/dev/null
HARD="--user 65532:65532 --cap-drop ALL --read-only --security-opt no-new-privileges:true"
sudo docker create --name r3gate-dns $HARD --sysctl net.ipv4.ip_unprivileged_port_start=53 \
  --network clm-gt-ctl --ip 172.30.241.4 -v "$W/Corefile:/etc/r3/Corefile:ro" \
  --entrypoint /usr/local/bin/coredns "$IMG" -conf /etc/r3/Corefile >/dev/null
sudo docker network connect --ip 172.30.242.3 clm-gt-up r3gate-dns
DENY=""
for r in 0.0.0.0/8 10.0.0.0/8 100.64.0.0/10 127.0.0.0/8 169.254.0.0/16 172.16.0.0/12 192.0.0.0/24 \
         192.0.2.0/24 192.88.99.0/24 192.168.0.0/16 198.18.0.0/15 198.51.100.0/24 203.0.113.0/24 \
         224.0.0.0/4 240.0.0.0/4 ::/0; do DENY="$DENY --deny-range $r"; done
ENV=()
if [ -n "$HOSTILE" ]; then
  ENV=(-e HTTPS_PROXY=http://172.26.0.2:3128 -e https_proxy=http://172.26.0.2:3128
       -e HTTP_PROXY=http://172.26.0.2:3128 -e http_proxy=http://172.26.0.2:3128
       -e ALL_PROXY=http://172.26.0.2:3128 -e NO_PROXY='*' -e GODEBUG=netdns=cgo)
fi
sudo docker create --name r3gate-proxy $HARD "${ENV[@]}" -e R3_EGRESS_FQDN="$FQDN" --network clm-gt-ctl --ip 172.30.241.2 \
  -v "$W/acl.yaml:/etc/r3/acl.yaml:ro" --entrypoint /usr/local/bin/smokescreen "$IMG" \
  --listen-ip 172.30.241.2 --listen-port 4750 --egress-acl-file /etc/r3/acl.yaml \
  --resolver-address 172.30.241.4:53 $DENY >/dev/null
sudo docker network connect --ip 172.30.242.2 clm-gt-up r3gate-proxy
sudo docker create --name r3gate-client $HARD --network clm-gt-ctl --ip 172.30.241.3 \
  -v "$W:/r3:ro" --entrypoint /bin/sleep "$IMG" infinity >/dev/null
sudo docker start r3gate-dns r3gate-proxy r3gate-client >/dev/null
sleep 2
sudo docker ps --filter name=r3gate --format '{{.Names}} {{.Status}}'
