#!/bin/bash
# R3 host enforcement: READ-ONLY verification (D-127 E4). Changes nothing on the host.
# Never runs iptables-legacy or ip6tables-legacy (facts lesson SE-1: they autoload modules);
# legacy-table presence is read from /proc/net/ip_tables_names only.
#   sudo R3_REVIEWED_MANIFEST=<manifest> verify_host_firewall.sh [/etc/clm/r3/clm_r3.nft]
set -u
TABLE_FILE=${1:-/etc/clm/r3/clm_r3.nft}
RC=0
ok() { echo "PASS $*"; }
bad() { echo "FAIL $*"; RC=1; }

# QG P3-5 / DQ-1: the complete installed R3 host file set (G3a deployment specification). The
# reviewed manifest must list exactly these six paths, once each. Fixed here on purpose: there is
# no environment override of the paths.
R3_INSTALLED_FILES=(
  /etc/clm/r3/clm_r3.nft
  /usr/local/lib/clm-r3/clm_r3_watch.py
  /usr/local/lib/clm-r3/clm_r3_stop_containers.sh
  /usr/local/lib/clm-r3/verify_host_firewall.sh
  /etc/systemd/system/clm-r3-egress-firewall.service
  /etc/systemd/system/clm-r3-firewall-watch.service
)

# check_manifest <manifest> <required path>... : prints one reason line and returns 0 only if
# every line is exactly "<64 lowercase hex sha256><two spaces><path>", the listed paths are
# exactly the required set (no partial, duplicate or unexpected path), every listed file is a
# readable regular file (not a symlink), and `sha256sum --strict -c` verifies every hash.
# Anything it cannot read or run fails closed. Read-only: it writes nothing.
check_manifest() {
  local manifest=$1
  shift
  local -a required=("$@")
  local -A want=() seen=()
  local p line path out n=0
  [ "${#required[@]}" -gt 0 ] || { echo "no required paths given"; return 1; }
  for p in "${required[@]}"; do want[$p]=1; done
  [ -n "$manifest" ] || { echo "R3_REVIEWED_MANIFEST not set (required)"; return 1; }
  if [ ! -f "$manifest" ] || [ ! -r "$manifest" ]; then
    echo "manifest missing or unreadable: $manifest"; return 1
  fi
  command -v sha256sum >/dev/null 2>&1 || { echo "sha256sum not available"; return 1; }
  while IFS= read -r line || [ -n "$line" ]; do
    n=$((n + 1))
    # The path may not start with "*" (sha256sum's binary-mode marker): text-mode lines only.
    if [[ ! $line =~ ^([0-9a-f]{64})\ \ ([^[:space:]*][^[:space:]]*)$ ]]; then
      echo "malformed manifest line $n"; return 1
    fi
    path=${BASH_REMATCH[2]}
    [ -n "${want[$path]:-}" ] || { echo "unexpected path on manifest line $n: $path"; return 1; }
    [ -z "${seen[$path]:-}" ] || { echo "duplicate path on manifest line $n: $path"; return 1; }
    seen[$path]=1
    if [ ! -f "$path" ] || [ -L "$path" ] || [ ! -r "$path" ]; then
      echo "listed file missing, unreadable or not a regular file: $path"; return 1
    fi
  done < "$manifest"
  for p in "${required[@]}"; do
    [ -n "${seen[$p]:-}" ] || { echo "manifest incomplete (${#seen[@]} of ${#required[@]}): missing $p"; return 1; }
  done
  [ "${#seen[@]}" -eq "${#required[@]}" ] || { echo "manifest path count mismatch"; return 1; }
  if ! out=$(sha256sum --strict --quiet -c "$manifest" 2>&1); then
    echo "hash verification failed: $(printf '%s' "$out" | tr '\n' ' ')"; return 1
  fi
  echo "${#seen[@]} of ${#required[@]} required files listed and matching"
  return 0
}

# R-1 pin. pinned_from_table <table file>: prints the goldtier_dst_v4 elements, sorted, one per
# line; returns 1 if the set is missing or empty. normalise_dst_list <a,b,...>: the same form.
pinned_from_table() {
  local out
  out=$(awk '/^[[:space:]]*set goldtier_dst_v4[[:space:]]*\{/ {inset=1; next}
             inset && /elements = \{/ {sub(/.*elements = \{/, ""); sub(/\}.*/, ""); print; exit}
             inset && /^[[:space:]]*\}/ {exit}' "$1" 2>/dev/null | tr ',' '\n' | tr -d ' \t' | grep -v '^$' | sort -t. -k1,1n -k2,2n -k3,3n -k4,4n)
  [ -n "$out" ] || return 1
  printf '%s\n' "$out"
}
normalise_dst_list() {
  printf '%s' "$1" | tr ',' '\n' | tr -d ' \t' | grep -v '^$' | sort -t. -k1,1n -k2,2n -k3,3n -k4,4n
}

# Sourced (by the regression tests): define the functions only, run nothing.
[ "${BASH_SOURCE[0]}" = "$0" ] || return 0

[ "$(id -u)" = 0 ] || { echo "run as root (read-only)"; exit 2; }

if python3 -I /usr/local/lib/clm-r3/clm_r3_watch.py --table-file "$TABLE_FILE" --containers none --check-only >/tmp/.clm_r3_check 2>&1; then
  ok "inet clm_r3 present and identical to $TABLE_FILE"; else bad "inet clm_r3 absent or changed: $(cat /tmp/.clm_r3_check)"; fi
rm -f /tmp/.clm_r3_check
for unit in clm-r3-egress-firewall clm-r3-firewall-watch; do
  [ "$(systemctl is-active $unit)" = active ] && ok "$unit active" || bad "$unit not active"
  [ "$(systemctl is-enabled $unit 2>/dev/null)" = enabled ] && ok "$unit enabled" || bad "$unit not enabled"
done
[ "$(systemctl is-enabled nftables 2>/dev/null)" != enabled ] && ok "nftables.service not enabled" || bad "nftables.service enabled (flushes Docker rules)"
ufw status 2>/dev/null | grep -q 'Status: inactive' && ok "ufw inactive" || bad "ufw active or unknown"
lsmod | grep -q '^br_netfilter' && bad "br_netfilter loaded" || ok "br_netfilter not loaded"
[ "$(sysctl -n net.ipv6.conf.all.forwarding)" = 0 ] && ok "IPv6 forwarding 0" || bad "IPv6 forwarding not 0"
[ "$(sysctl -n net.ipv4.ip_forward)" = 1 ] && ok "IPv4 forwarding 1" || bad "IPv4 forwarding not 1"
docker info --format '{{.FirewallBackend.Driver}}' 2>/dev/null | grep -qx iptables && ok "Docker firewall backend iptables" || bad "Docker firewall backend changed"
# QG P3-7: the watcher and stop helper rely on live-restore=false (a daemon restart stops containers)
[ "$(docker info --format '{{.LiveRestoreEnabled}}' 2>/dev/null)" = false ] && ok "Docker live-restore=false" || bad "Docker live-restore is not false"
# QG P3-5 / DQ-1: REQUIRED reviewed manifest, produced at G3a preflight from the reviewed commit.
if manifest_reason=$(check_manifest "${R3_REVIEWED_MANIFEST:-}" "${R3_INSTALLED_FILES[@]}"); then
  ok "installed host files match the reviewed manifest ($manifest_reason)"
else
  bad "reviewed manifest check: $manifest_reason"
fi
[ -e /etc/docker/daemon.json ] && echo "NOTE daemon.json present (was absent in the facts baseline)" || ok "no daemon.json"
echo "INFO legacy xtables tables: [$(tr '\n' ' ' < /proc/net/ip_tables_names 2>/dev/null)]"
for br in clm-gt-up clm-gt-ctl; do
  ip link show "$br" >/dev/null 2>&1 && ok "bridge $br present" || echo "INFO bridge $br not present (R3 network not created yet)"
done
for n in $(docker network ls --format '{{.Name}}' | grep -E 'goldtier-(control|uplink)$'); do
  icc=$(docker network inspect "$n" --format '{{index .Options "com.docker.network.bridge.enable_icc"}}')
  v6=$(docker network inspect "$n" --format '{{.EnableIPv6}}')
  [ "$icc" != false ] && ok "$n ICC not disabled" || bad "$n enable_icc=false (would load br_netfilter host-wide)"
  [ "$v6" = false ] && ok "$n IPv6 off" || bad "$n IPv6 on"
done
for c in clm-staging-goldtier-egress clm-staging-goldtier-dns; do
  docker inspect "$c" >/dev/null 2>&1 || { echo "INFO $c not created"; continue; }
  caps=$(docker inspect "$c" --format '{{range .HostConfig.CapAdd}}{{.}} {{end}}')
  echo "INFO $c cap_add: $caps"
done
# R-1 pin: the host set is present and non-empty, and the proxy container (if created) carries the
# identical set. The table file itself is already covered by the manifest and the live-table check.
if host_pin=$(pinned_from_table "$TABLE_FILE"); then
  ok "host goldtier_dst_v4 pinned: $(printf '%s' "$host_pin" | tr '\n' ' ')"
  if docker inspect clm-staging-goldtier-egress >/dev/null 2>&1; then
    c_pin=$(docker inspect clm-staging-goldtier-egress --format '{{range .Config.Env}}{{println .}}{{end}}' | sed -n 's/^CLM_EGRESS_DST_V4=//p')
    [ -n "$c_pin" ] && [ "$(normalise_dst_list "$c_pin")" = "$host_pin" ] \
      && ok "proxy CLM_EGRESS_DST_V4 equals the host set" || bad "proxy CLM_EGRESS_DST_V4 differs from the host set"
  fi
else
  bad "host goldtier_dst_v4 set missing or empty in $TABLE_FILE"
fi
exit $RC
