#!/bin/sh
# Stop the hosted GPT-OSS egress proxy and resolver (fail closed). Used by the three clm-r22o
# units. Install: /usr/local/lib/clm-r22o/. As E1's clm_r22_stop_assistant.sh: during a system
# shutdown this does nothing (Docker stops its containers itself); every other stop stops them,
# and they stay stopped (restart "no") until clm-r22o-egress.service starts them again. Never
# fails, so the table removal that follows runs. The assistant keeps running: without the proxy
# a GPT-OSS call fails and the answer comes from the case data.
state=$(systemctl is-system-running 2>/dev/null)
if [ "$state" = "stopping" ]; then
  echo "clm-r22o: $1 during shutdown; leaving the egress stop to Docker"
  exit 0
fi
timeout 20 docker stop --time 0 clm-staging-openrouter-egress clm-staging-openrouter-dns >/dev/null 2>&1
echo "{\"event\":\"CLM_R22O_EGRESS_STOPPED\",\"trigger\":\"$1\",\"t\":$(date +%s.%N)}"
exit 0
