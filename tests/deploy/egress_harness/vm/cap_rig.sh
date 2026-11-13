#!/bin/bash
# R3 G2 capability rig (harness VM only): the final egress image under its guard, with the
# owner-approved G2-LOCAL capability set, on the real R3 networks. Mirrors the overlay's
# container settings so capability claims are measured, not inferred from Compose.
#   cap_rig.sh up <image> <fqdn>     cap_rig.sh down
set -euo pipefail
down() {
  for c in r3cap-client r3cap-egress r3cap-dns; do sudo docker rm -f "$c" >/dev/null 2>&1 || true; done
  for n in clm-gt-ctl clm-gt-up; do sudo docker network rm "$n" >/dev/null 2>&1 || true; done
}
[ "${1:-}" = down ] && { down; exit 0; }
IMG=$2; FQDN=$3
WANT=${EXPECTED_SMOKESCREEN_SHA256:-3651c1cfa070a2c9929ad275d943881f99b4bdc84a46e322038ffae00be271b4}
GOT=$(sudo docker run --rm --network none --entrypoint sha256sum "$IMG" /usr/local/bin/smokescreen | cut -d' ' -f1)
if [ "$GOT" != "$WANT" ]; then echo "REFUSED: $IMG smokescreen sha256 $GOT != expected $WANT" >&2; exit 3; fi
down
sudo docker network create --driver bridge --internal --subnet 172.30.241.0/29 --gateway 172.30.241.1 \
  -o com.docker.network.bridge.name=clm-gt-ctl clm-gt-ctl >/dev/null
sudo docker network create --driver bridge --subnet 172.30.242.0/29 --gateway 172.30.242.1 \
  -o com.docker.network.bridge.name=clm-gt-up clm-gt-up >/dev/null
GUARD="--cap-drop ALL --cap-add NET_ADMIN --cap-add SETUID --cap-add SETGID --cap-add SETPCAP
  --read-only --tmpfs /run/r3:rw,nosuid,nodev,noexec,mode=0755,size=1m --security-opt no-new-privileges:true
  --pids-limit 64 --memory 128m -e CLM_EGRESS_FQDN=$FQDN"
sudo docker create --name r3cap-dns $GUARD -e CLM_EGRESS_ROLE=resolver \
  --sysctl net.ipv4.ip_unprivileged_port_start=53 --network clm-gt-ctl --ip 172.30.241.4 "$IMG" >/dev/null
sudo docker network connect --ip 172.30.242.3 clm-gt-up r3cap-dns
sudo docker create --name r3cap-egress $GUARD -e CLM_EGRESS_ROLE=proxy -e CLM_EGRESS_DST_V4=34.120.0.10 \
  --network clm-gt-ctl --ip 172.30.241.2 "$IMG" >/dev/null
sudo docker network connect --ip 172.30.242.2 clm-gt-up r3cap-egress
sudo docker create --name r3cap-client --user 65532:65532 --cap-drop ALL --read-only \
  --network clm-gt-ctl --ip 172.30.241.3 -v /tmp/r3gate:/r3:ro --entrypoint /bin/sleep "$IMG" infinity >/dev/null
sudo docker start r3cap-dns >/dev/null; sleep 2
sudo docker start r3cap-egress r3cap-client >/dev/null; sleep 4
sudo docker ps -a --filter name=r3cap --format '{{.Names}} {{.Status}}'
