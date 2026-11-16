#!/bin/bash
# Hosted GPT-OSS egress check (D-138 A1 PROPOSED, LOCAL DESIGN CANDIDATE). Read-only. Run on the
# host BEFORE the first GPT-OSS call with compose.assistant-openrouter.yml and after every change.
#   verify_openrouter_egress.sh [vars file] [table file]
# Prints one PASS/FAIL line per check and exits non-zero on any FAIL. Never prints a secret: only
# interface names, addresses, unit states and container states are shown.
set -uo pipefail
VARS=${1:-/etc/clm/r22o/clm_r22o.vars}
TABLE=${2:-/etc/clm/r22o/clm_r22o.nft}
CONTAINERS="clm-staging-openrouter-egress,clm-staging-openrouter-dns"
fail=0
ok() { echo "PASS $1"; }
no() { echo "FAIL $1"; fail=1; }
val() { grep -E "^$1=" "$2" | tail -1 | cut -d= -f2-; }

UPLINK=$(val UPLINK_IF "$VARS")
ip link show "$UPLINK" >/dev/null 2>&1 && ok "uplink interface $UPLINK present" || no "uplink interface $UPLINK absent"
grep -q "\"$UPLINK\"" "$TABLE" && ok "table names the uplink interface" || no "table does not name $UPLINK"
# The table never pins or allows any other source, and never a port other than 443 and 53.
grep -q 'ip saddr 172.30.247.2 oifname "'"$UPLINK"'" tcp dport 443 counter accept' "$TABLE" \
  && ok "table allows the proxy to tcp/443 only" || no "table proxy rule differs"
if sudo nft list table inet clm_r22o >/dev/null 2>&1; then
  ok "table inet clm_r22o loaded"
  sudo python3 -I /usr/local/lib/clm-r22o/clm_r22o_watch.py --table-file "$TABLE" --containers "$CONTAINERS" --check-only >/dev/null \
    && ok "live table equals the reviewed file" || no "live table differs from the reviewed file"
else
  no "table inet clm_r22o not loaded"
fi
# The other lanes' tables are untouched (present when installed; never this check's business).
for other in clm_r22 clm_r3; do
  sudo nft list table inet "$other" >/dev/null 2>&1 && ok "table inet $other still present" || echo "INFO table inet $other not loaded"
done
for unit in clm-r22o-egress-firewall.service clm-r22o-firewall-watch.service; do
  systemctl is-active -q "$unit" && ok "$unit active" || no "$unit not active"
done
systemctl is-enabled -q clm-r22o-egress.service && ok "clm-r22o-egress.service enabled" || no "clm-r22o-egress.service not enabled"
systemctl is-active -q clm-r22o-egress.service && ok "clm-r22o-egress.service active" || no "clm-r22o-egress.service not active (the gate did not start the egress)"
[ "$(systemctl show -p SubState --value clm-r22o-firewall-watch.service)" = running ] && ok "watcher process running" || no "watcher process not running"
for c in clm-staging-openrouter-egress clm-staging-openrouter-dns; do
  STATE=$(sudo docker inspect -f '{{.State.Status}}/{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$c" 2>/dev/null)
  [ "$STATE" = "running/healthy" ] && ok "$c running and healthy" || no "$c state is '$STATE', not running/healthy"
  POLICY=$(sudo docker inspect -f '{{.HostConfig.RestartPolicy.Name}}' "$c" 2>/dev/null)
  [ "$POLICY" = "no" ] && ok "$c restart policy is no" || no "$c restart policy is '$POLICY', not no"
done
NET=$(sudo docker network ls --filter driver=bridge -q | xargs -r sudo docker network inspect -f '{{index .Options "com.docker.network.bridge.name"}} {{index .Options "com.docker.network.bridge.enable_ip_masquerade"}}' 2>/dev/null | awk '$1=="clm-ao-up"{print $2}')
[ "$NET" = "false" ] && ok "Docker does not masquerade clm-ao-up" || no "Docker masquerade on clm-ao-up is '$NET'"
INTERNAL=$(sudo docker network ls --filter driver=bridge -q | xargs -r sudo docker network inspect -f '{{index .Options "com.docker.network.bridge.name"}} {{.Internal}}' 2>/dev/null | awk '$1=="clm-ao-ctl"{print $2}')
[ "$INTERNAL" = "true" ] && ok "clm-ao-ctl is an internal network" || no "clm-ao-ctl internal is '$INTERNAL'"
# The assistant: on the control network at .3, and openrouter.ai does not resolve inside it.
A=${ASSISTANT_CONTAINER:-clm-staging-assistant}
NETS=$(sudo docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{$v.IPAddress}} {{end}}' "$A" 2>/dev/null)
echo "$NETS" | grep -qw 172.30.246.3 && ok "assistant on clm-ao-ctl at 172.30.246.3" || no "assistant not at 172.30.246.3"
echo "$NETS" | grep -qw 172.30.247.2 && no "assistant is on the uplink" || ok "assistant is not on the uplink"
sudo docker exec "$A" python -I -c "import socket,sys
try: socket.getaddrinfo('openrouter.ai', 443)
except OSError: sys.exit(0)
sys.exit(1)" && ok "openrouter.ai does not resolve inside the assistant" || no "openrouter.ai resolves inside the assistant"
# The proxy refuses another host (403 from the gate; no lookup, nothing leaves).
CODE=$(sudo docker exec "$A" python -I -c "import socket
s=socket.create_connection(('172.30.246.2',4750),5)
s.sendall(b'CONNECT example.com:443 HTTP/1.1\r\nHost: example.com:443\r\n\r\n')
print(s.recv(64).split(b' ')[1].decode())" 2>/dev/null)
[ "$CODE" = "403" ] && ok "proxy refuses CONNECT example.com:443" || no "proxy answered '$CODE' to another host"
# As R3 (verify_host_firewall.sh): the control bridge's forward drops and intra-bridge isolation
# rely on br_netfilter staying unloaded; ICC must not be disabled on clm-ao-ctl (that loads it).
lsmod | grep -q '^br_netfilter' && no "br_netfilter loaded" || ok "br_netfilter not loaded"
ICC=$(sudo docker network ls --filter driver=bridge -q | xargs -r sudo docker network inspect -f '{{index .Options "com.docker.network.bridge.name"}} {{index .Options "com.docker.network.bridge.enable_icc"}}' 2>/dev/null | awk '$1=="clm-ao-ctl"{print $2}')
[ "$ICC" != false ] && ok "clm-ao-ctl ICC not disabled" || no "clm-ao-ctl enable_icc=false (would load br_netfilter host-wide)"
exit $fail
