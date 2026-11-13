#!/bin/sh
# Stop the R3 containers (fail closed). Used by both host units. Install: /usr/local/lib/clm-r3/.
#
# During a system shutdown this does nothing: Docker stops its containers itself, and a
# `docker stop` here would mark them manually stopped, so they would not return after a clean
# reboot. Every other stop (systemctl stop, a killed or crashed watcher) stops them, and they stay
# stopped (`unless-stopped` honours a manual stop) until an operator restarts them.
# Never fails: an absent Docker daemon or container must not block the table removal that follows.
state=$(systemctl is-system-running 2>/dev/null)
if [ "$state" = "stopping" ]; then
  echo "clm-r3: $1 during shutdown; leaving container stop to Docker"
  exit 0
fi
timeout 20 docker stop --time 0 clm-staging-goldtier-egress clm-staging-goldtier-dns >/dev/null 2>&1
echo "{\"event\":\"CLM_R3_CONTAINERS_STOPPED\",\"trigger\":\"$1\",\"t\":$(date +%s.%N)}"
exit 0
