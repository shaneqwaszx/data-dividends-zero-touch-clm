#!/bin/bash
# R2.2 assistant egress check (D-129 PROPOSED, E1 LOCAL DESIGN CANDIDATE). Read-only. Run on the
# host BEFORE starting the assistant with compose.assistant-provider.yml and after every change.
#   verify_assistant_egress.sh <compose.env> [vars file] [table file]
# Prints one PASS/FAIL line per check and exits non-zero on any FAIL. Never prints a secret: only
# the pinned address, interface names and the table hash are shown.
set -uo pipefail
ENV_FILE=${1:?compose.env path required}
VARS=${2:-/etc/clm/r22/clm_r22.vars}
TABLE=${3:-/etc/clm/r22/clm_r22.nft}
fail=0
ok() { echo "PASS $1"; }
no() { echo "FAIL $1"; fail=1; }
val() { grep -E "^$1=" "$2" | tail -1 | cut -d= -f2-; }

PIN=$(val ANTHROPIC_DST_V4 "$VARS")
ENV_PIN=$(val ASSISTANT_ANTHROPIC_PINNED_V4 "$ENV_FILE" | tr -d '"')
UPLINK=$(val UPLINK_IF "$VARS")
[ -n "$PIN" ] && [ "$PIN" = "$ENV_PIN" ] && ok "pin equal in vars and compose.env ($PIN)" || no "pin differs between vars and compose.env"
grep -q "elements = { $PIN }" "$TABLE" && ok "table pins exactly $PIN" || no "table does not pin exactly the vars address"
python3 -I - "$PIN" <<'PY' && ok "pin inside Anthropic's published inbound IPv4 ranges" || no "pin outside Anthropic's published ranges"
import ipaddress, sys
a = ipaddress.ip_address(sys.argv[1])
sys.exit(0 if a.version == 4 and any(a in ipaddress.ip_network(n) for n in ("160.79.104.0/23", "153.61.224.0/22")) else 1)
PY
# The host's own view of the name (through its configured resolver); any difference stops the run.
RESOLVED=$(getent ahostsv4 api.anthropic.com | awk '{print $1}' | sort -u | tr '\n' ' ' | sed 's/ $//')
[ "$RESOLVED" = "$PIN" ] && ok "api.anthropic.com resolves to the pin only" || no "api.anthropic.com resolves to '$RESOLVED', not the pin"
ip link show "$UPLINK" >/dev/null 2>&1 && ok "uplink interface $UPLINK present" || no "uplink interface $UPLINK absent"
grep -q "\"$UPLINK\"" "$TABLE" && ok "table names the uplink interface" || no "table does not name $UPLINK"
if sudo nft list table inet clm_r22 >/dev/null 2>&1; then
  ok "table inet clm_r22 loaded"
  sudo python3 -I /usr/local/lib/clm-r22/clm_r22_watch.py --table-file "$TABLE" --containers clm-staging-assistant --check-only >/dev/null \
    && ok "live table equals the reviewed file" || no "live table differs from the reviewed file"
else
  no "table inet clm_r22 not loaded"
fi
for unit in clm-r22-assistant-firewall.service clm-r22-firewall-watch.service; do
  systemctl is-active -q "$unit" && ok "$unit active" || no "$unit not active"
done
# P2-1: only the start gate starts the assistant, and Docker does not translate the bridge.
systemctl is-enabled -q clm-r22-assistant.service && ok "clm-r22-assistant.service enabled" || no "clm-r22-assistant.service not enabled"
# QG N4: the live state, not only the configuration. The gate must have started the assistant
# (active), the watcher must be running, and the container must be running and healthy.
systemctl is-active -q clm-r22-assistant.service && ok "clm-r22-assistant.service active" || no "clm-r22-assistant.service not active (the gate did not start the assistant)"
[ "$(systemctl show -p SubState --value clm-r22-firewall-watch.service)" = running ] && ok "watcher process running" || no "watcher process not running"
STATE=$(sudo docker inspect -f '{{.State.Status}}/{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' clm-staging-assistant 2>/dev/null)
[ "$STATE" = "running/healthy" ] && ok "assistant running and healthy" || no "assistant state is '$STATE', not running/healthy"
POLICY=$(sudo docker inspect -f '{{.HostConfig.RestartPolicy.Name}}' clm-staging-assistant 2>/dev/null)
[ "$POLICY" = "no" ] && ok "assistant restart policy is no" || no "assistant restart policy is '$POLICY', not no"
NET=$(sudo docker network ls --filter driver=bridge -q | xargs -r sudo docker network inspect -f '{{index .Options "com.docker.network.bridge.name"}} {{index .Options "com.docker.network.bridge.enable_ip_masquerade"}}' 2>/dev/null | awk '$1=="clm-as-up"{print $2}')
[ "$NET" = "false" ] && ok "Docker does not masquerade clm-as-up" || no "Docker masquerade on clm-as-up is '$NET'"
sudo nft list ruleset 2>/dev/null | grep -q 'flush ruleset' && no "a flush ruleset is present" || true
exit $fail
