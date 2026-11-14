#!/bin/sh
# Stop the assistant (fail closed). Used by both R2.2 host units. Install: /usr/local/lib/clm-r22/.
# During a system shutdown this does nothing: Docker stops its containers itself, and a manual
# stop here would keep the assistant down after a clean reboot. Every other stop (systemctl
# stop, a killed or crashed watcher) stops it, and it stays stopped (its restart policy is "no",
# P2-1) until clm-r22-assistant.service starts it again. Never fails, so the table removal that
# follows runs.
state=$(systemctl is-system-running 2>/dev/null)
if [ "$state" = "stopping" ]; then
  echo "clm-r22: $1 during shutdown; leaving the assistant stop to Docker"
  exit 0
fi
timeout 20 docker stop --time 0 clm-staging-assistant >/dev/null 2>&1
echo "{\"event\":\"CLM_R22_ASSISTANT_STOPPED\",\"trigger\":\"$1\",\"t\":$(date +%s.%N)}"
exit 0
