#!/bin/bash
# R3 G2 integrated stack (harness VM only). Real deploy/compose.yml + compose.mongo.yml +
# compose.goldtier-egress.yml, plus a harness-only override for synthetic Mongo TLS (no auth),
# the test CA and per-run credentials. Project name clm-staging, so container names match the host.
#   stack.sh host-install          install the R3 host units and table (harness host only)
#   stack.sh up mock|sandbox       (re)create the stack and wait for health
#   stack.sh down
#   stack.sh dcg <compose args>    run compose with the same files
set -euo pipefail
R3=${R3_SRC:-$HOME/r3}
W=/var/lib/clm-r3-harness
FQDN=goldtier.r3-harness.invalid
sudo mkdir -p "$W"; sudo chmod 700 "$W"

files() {
  echo -f "$R3/deploy/compose.yml" -f "$R3/deploy/compose.mongo.yml" -f "$R3/deploy/compose.goldtier-egress.yml" -f "$W/harness.override.yml"
}
dcg() {
  sudo env BACKEND_IMAGE="${R3_BACKEND_IMAGE:-clm-r3-backend:g2}" FRONTEND_IMAGE=clm-r3-frontend:g2 GOLDTIER_EGRESS_IMAGE="${R3_EGRESS_IMAGE:-clm-r3-egress:g2c}" \
    BACKEND_ENV_FILE="$W/backend.env" CLM_SITE=localhost \
    MONGO_URI="mongodb://mongo:27017/?tls=true&tlsCAFile=/run/clm/mongo-ca.pem" \
    MONGO_CA_FILE="$W/mongo-ca.pem" MONGO_SERVER_PEM="$W/mongo-server.pem" MONGO_DATA_VOLUME=clm-r3-harness-mongo \
    CLM_GOLDTIER_EGRESS_FQDN=$FQDN CLM_GOLDTIER_EGRESS_DST_V4="${GT_DST:-34.120.0.10}" CLM_GOLDTIER_CONNECTOR_MODE="${MODE:-mock}" \
    docker compose --env-file /dev/null -p clm-staging $(files) "$@"
}

case "${1:-}" in
  host-install)
    sudo install -d -m 0700 /etc/clm /etc/clm/r3
    # R-1 pin: the sealed harness has no real GoldTier, so the reviewed table is installed with
    # its pinned set replaced by the harness GoldTier address (GT_DST). Nothing else changes.
    sed "s/elements = { 13.42.220.164, 18.135.200.6 }/elements = { ${GT_DST:-34.120.0.10} }/" \
      "$R3/deploy/egress/host/clm_r3.nft" | sudo tee "$W/clm_r3.harness.nft" >/dev/null
    sudo grep -q "elements = { ${GT_DST:-34.120.0.10} }" "$W/clm_r3.harness.nft" || { echo "pin substitution failed" >&2; exit 3; }
    sudo install -m 0600 "$W/clm_r3.harness.nft" /etc/clm/r3/clm_r3.nft
    sudo install -d -m 0755 /usr/local/lib/clm-r3
    sudo install -m 0644 "$R3/deploy/egress/host/clm_r3_watch.py" /usr/local/lib/clm-r3/clm_r3_watch.py
    sudo install -m 0755 "$R3/deploy/egress/host/clm_r3_stop_containers.sh" /usr/local/lib/clm-r3/clm_r3_stop_containers.sh
    sudo install -m 0755 "$R3/deploy/egress/host/verify_host_firewall.sh" /usr/local/lib/clm-r3/verify_host_firewall.sh
    sudo install -m 0644 "$R3/deploy/egress/host/clm-r3-egress-firewall.service" "$R3/deploy/egress/host/clm-r3-firewall-watch.service" /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable --now clm-r3-egress-firewall.service clm-r3-firewall-watch.service
    sudo systemctl restart clm-r3-egress-firewall.service  # load a changed table (stack is down)
    sudo systemctl restart clm-r3-firewall-watch.service   # pick up a changed watcher
    systemctl is-active clm-r3-egress-firewall clm-r3-firewall-watch
    ;;
  up)
    MODE=$2
    if ! sudo test -f "$W/mongo-server.pem"; then
      sudo openssl req -x509 -nodes -newkey rsa:2048 -days 30 -subj /CN=mongo \
        -addext subjectAltName=DNS:mongo,DNS:localhost -keyout "$W/mongo.key" -out "$W/mongo-ca.pem" 2>/dev/null
      sudo sh -c "cat '$W/mongo.key' '$W/mongo-ca.pem' > '$W/mongo-server.pem'; rm '$W/mongo.key'; chown 999:999 '$W/mongo-server.pem'; chmod 600 '$W/mongo-server.pem'; chmod 644 '$W/mongo-ca.pem'"
    fi
    sudo install -m 0644 "$R3/pki/ca.pem" "$W/r3-test-ca.pem"
    sudo docker volume inspect clm-r3-harness-mongo >/dev/null 2>&1 || sudo docker volume create clm-r3-harness-mongo >/dev/null
    if ! sudo test -f "$W/credential"; then
      sudo sh -c "head -c 24 /dev/urandom | base64 | tr -d '/+=' > '$W/credential'; chmod 600 '$W/credential'"
    fi
    HASH=$(sudo cat "$W/credential" | sudo docker run --rm --network none -i clm-r3-backend:g2 python -c \
      "from app.services.authentication import generate_scrypt_password_hash as make; print(make(input()))")
    {
      echo "PHASE13_BROWSER_ORIGIN=https://localhost"
      for k in PHASE13_MAYA_LIM PHASE13_ETHAN_TAN PHASE13_SOPHIA_NG PHASE13_RYAN_LEE PHASE13_OLIVIA_KOH PHASE14_5_HR_ADMIN PHASE13_SUPPORT_USER; do
        echo "${k}_PASSWORD_HASH=$HASH"; done
      echo "GOLDTIER_SANDBOX_BASE_URL=https://$FQDN"
      echo "GOLDTIER_SANDBOX_ENVIRONMENT=harness"
      echo "GOLDTIER_SANDBOX_USER_ID=synthetic-r3-harness-user"
    } | sudo tee "$W/backend.env" >/dev/null
    sudo chmod 600 "$W/backend.env"
    sudo tee "$W/harness.override.yml" >/dev/null <<'YML'
# Harness only: synthetic Mongo without auth, and the R3 test CA as the explicit GoldTier trust store.
services:
  backend:
    environment:
      GOLDTIER_SANDBOX_TLS_CA_FILE: /run/clm/r3-test-ca.pem
    volumes:
      - type: bind
        source: /var/lib/clm-r3-harness/r3-test-ca.pem
        target: /run/clm/r3-test-ca.pem
        read_only: true
  mongo:
    image: clm-r3-mongo-pinned:g2
    command: [mongod, --bind_ip_all, --tlsMode, requireTLS, --tlsCertificateKeyFile, /run/clm/mongo-server.pem,
              --tlsCAFile, /run/clm/mongo-ca.pem, --tlsAllowConnectionsWithoutCertificates]
YML
    dcg up -d --no-build --wait --wait-timeout 180 >/dev/null
    sudo docker ps --format '{{.Names}} {{.Status}}' | sort
    ;;
  down) MODE=mock dcg down --remove-orphans >/dev/null 2>&1 || true ;;
  dcg) shift; MODE=${MODE:-mock} dcg "$@" ;;
  *) echo "usage: $0 host-install|up mock|sandbox|down|dcg ..." >&2; exit 2 ;;
esac
