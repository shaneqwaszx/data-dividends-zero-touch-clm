#!/bin/bash
# HARNESS ONLY (RL-9/RL-10): from boot, keep pushing disallowed traffic from inside each R3
# container as soon as it exists, as the child uid and as root, for 120 s. Installed as a
# transient unit by run_matrix_b.sh before a reboot; never part of the deliverable host set.
LG=/home/ubuntu/r3/tests/deploy/egress_harness/vm/loadgen.py
OUT=/var/log/r3-boot-load; mkdir -p $OUT
end=$(( $(date +%s) + 120 ))
echo "boot-load start $(date +%s.%N)" >> $OUT/log
while [ "$(date +%s)" -lt $end ]; do
  for c in clm-staging-goldtier-egress clm-staging-goldtier-dns; do
    role=$([ $c = clm-staging-goldtier-egress ] && echo proxy || echo resolver)
    if [ "$(docker inspect -f '{{.State.Running}}' $c 2>/dev/null)" = true ]; then
      for u in "-u 65532:65532" ""; do
        timeout 6 docker exec -i $u $c python3 -I - loadgen $role 4 < $LG >> $OUT/$c.json 2>&1 &
      done
    fi
  done
  wait   # one generator per uid per container at a time (pids_limit 64)
  sleep 0.5
done
wait
echo "boot-load end $(date +%s.%N)" >> $OUT/log
