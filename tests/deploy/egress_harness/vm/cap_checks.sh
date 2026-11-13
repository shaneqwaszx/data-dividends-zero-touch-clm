#!/bin/bash
# R3 G2 capability proof (owner decision G2-LN, requirements 1-7). Harness VM only.
# Reads the live credentials of the guard (PID 1) and of the real child from /proc, then runs
# every tamper and escalation attempt as a process whose credentials are byte-identical to the
# child's (created with the guard's exact setpriv prefix; the identity is asserted, not assumed).
#   cap_checks.sh            (expects cap_rig.sh up)
set -uo pipefail
FAIL=0
check() { if [ "$2" = "$3" ] && { [ -n "$2" ] || [ "$4" = allow-empty ]; }; then echo "PASS $1: $2"; else echo "FAIL $1: got [$2] want [$3]"; FAIL=1; fi; }
creds() { grep -E '^(Uid|Gid|Groups|CapInh|CapPrm|CapEff|CapBnd|CapAmb|NoNewPrivs|Seccomp):' | tr -s '\t ' ' '; }
SETPRIV='setpriv --reuid=65532 --regid=65532 --clear-groups --inh-caps=-all --ambient-caps=-all --bounding-set=-all --no-new-privs --'

for C in ${CAP_CONTAINERS:-r3cap-egress r3cap-dns}; do
  echo "=== $C"
  case $C in *egress*) ROLE=proxy ;; *) ROLE=resolver ;; esac
  CHILD=$( [ $ROLE = proxy ] && echo smokescreen || echo coredns )
  HOSTPID=$(sudo docker inspect -f '{{.State.Pid}}' $C)
  CPID=$(pgrep -P "$HOSTPID" -x "$CHILD" || true)
  [ -z "$CPID" ] && CPID=$(sudo bash -c "for p in \$(pgrep -x $CHILD); do grep -q \"^PPid:.$HOSTPID\$\" /proc/\$p/status && echo \$p; done" | head -1)
  echo "guard host pid $HOSTPID; child $CHILD host pid $CPID"
  if [ -z "$CPID" ] || [ "$HOSTPID" = 0 ]; then echo "FAIL $C not running; cannot measure"; FAIL=1; continue; fi
  check "$C guard cmdline" "$(tr '\0' ' ' < /proc/$HOSTPID/cmdline)" "/usr/local/bin/python3 -I /opt/egress/goldtier_egress_guard.py "
  check "$C child parent is guard (1: supervision)" "$(awk '/^PPid:/{print $2}' /proc/$CPID/status)" "$HOSTPID"
  G=$(sudo cat /proc/$HOSTPID/status | creds)
  echo "guard creds: $G"
  check "$C guard CapEff (NET_ADMIN only after drop)" "$(sudo awk '/^CapEff:/{print $2}' /proc/$HOSTPID/status)" "0000000000001000"
  check "$C guard CapPrm" "$(sudo awk '/^CapPrm:/{print $2}' /proc/$HOSTPID/status)" "0000000000001000"
  check "$C guard CapBnd" "$(sudo awk '/^CapBnd:/{print $2}' /proc/$HOSTPID/status)" "0000000000001000"
  K=$(sudo cat /proc/$CPID/status | creds)
  echo "child creds: $K"
  for f in CapInh CapPrm CapEff CapBnd CapAmb; do
    check "$C child $f (4)" "$(sudo awk "/^$f:/{print \$2}" /proc/$CPID/status)" "0000000000000000"
  done
  check "$C child Uid (3)" "$(sudo awk '/^Uid:/{print $2,$3,$4,$5}' /proc/$CPID/status)" "65532 65532 65532 65532"
  check "$C child Gid (3)" "$(sudo awk '/^Gid:/{print $2,$3,$4,$5}' /proc/$CPID/status)" "65532 65532 65532 65532"
  check "$C child Groups" "$(sudo awk '/^Groups:/{print $2}' /proc/$CPID/status)" "" allow-empty
  check "$C child NoNewPrivs (5)" "$(sudo awk '/^NoNewPrivs:/{print $2}' /proc/$CPID/status)" "1"
  check "$C child Seccomp filter" "$(sudo awk '/^Seccomp:/{print $2}' /proc/$CPID/status)" "2"
  check "$C child env scrubbed" "$(sudo cat /proc/$CPID/environ | tr '\0' '\n' | cut -d= -f1 | sort | tr '\n' ' ')" \
        "$( [ $ROLE = proxy ] && echo 'PATH R3_EGRESS_FQDN ' || echo 'PATH ' )"
  # A process with the child's exact credentials, made by the guard's own setpriv prefix.
  T="sudo docker exec $C $SETPRIV"
  TWIN=$($T python3 -I -c "print(open('/proc/self/status').read())" | creds)
  check "$C twin credentials == child credentials" "$TWIN" "$K"
  # 6: tamper and escalation attempts, each must fail
  try() { local name=$1; shift; local out; out=$($T "$@" 2>&1); local rc=$?
          if [ $rc -ne 0 ]; then echo "PASS $C child cannot $name: rc=$rc ($(echo "$out" | tail -1 | cut -c1-110))"; else echo "FAIL $C child CAN $name: $out"; FAIL=1; fi; }
  try "list nft" nft list ruleset
  try "flush nft" nft flush ruleset
  try "delete Layer N" nft delete table inet clm_r3n
  try "open raw socket" python3 -I -c "import socket; socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)"
  try "open packet socket" python3 -I -c "import socket; socket.socket(socket.AF_PACKET, socket.SOCK_RAW)"
  try "add a route (SIOCADDRT)" python3 -I -c "
import fcntl,socket,struct
s=socket.socket(); rt=bytearray(120); struct.pack_into('=HH14s',rt,8,2,0,bytes(14)); struct.pack_into('=HH4s8s',rt,24,2,0,socket.inet_aton('10.9.9.9'),bytes(8))
fcntl.ioctl(s.fileno(),0x890B,bytes(rt))"
  try "change an interface address (SIOCSIFADDR)" python3 -I -c "
import fcntl,socket,struct
s=socket.socket(); fcntl.ioctl(s.fileno(),0x8916,struct.pack('16sHH4s8s',b'eth0',2,0,socket.inet_aton('10.9.9.9'),bytes(8)))"
  try "write a sysctl" sh -c 'echo 1 > /proc/sys/net/ipv4/ip_forward'
  try "setuid(0)" python3 -I -c "import os; os.setuid(0)"
  try "raise a capability (capset)" python3 -I -c "
import ctypes; l=ctypes.CDLL(None,use_errno=True)
class H(ctypes.Structure): _fields_=[('v',ctypes.c_uint32),('p',ctypes.c_int)]
class D(ctypes.Structure): _fields_=[('e',ctypes.c_uint32),('pm',ctypes.c_uint32),('i',ctypes.c_uint32)]
d=(D*2)(D(4096,4096,0),D(0,0,0)); r=l.capset(ctypes.byref(H(0x20080522,0)),d); raise SystemExit(0 if r==0 else 1)"
  try "ptrace the guard" python3 -I -c "
import ctypes; l=ctypes.CDLL(None,use_errno=True); raise SystemExit(0 if l.ptrace(16,1,0,0)==0 else 1)"
  try "signal the guard" python3 -I -c "import os,signal; os.kill(1, signal.SIGTERM)"
  try "rewrite the rendered config" sh -c 'echo x >> /run/r3/$(ls /run/r3 | grep -v health | head -1)'
  try "write the root filesystem" sh -c 'echo x > /opt/egress/x'
  try "create a user namespace" python3 -I -c "import os; os.unshare(os.CLONE_NEWUSER)"
  try "create a network namespace" python3 -I -c "import os; os.unshare(os.CLONE_NEWNET)"
  SUID=$(sudo docker exec $C sh -c 'find / -xdev -perm -4000 -type f 2>/dev/null | tr "\n" " "')
  echo "setuid binaries in image: [$SUID]"
  for b in $SUID; do try "gain root via $b" sh -c "$b -c id 2>&1 | grep -q 'uid=0' && exit 0 || exit 1"; done
  # 6: the child cannot escape its network permissions (Layer N output policy drop)
  DSTS="169.254.169.254:80 172.30.242.1:22 172.30.241.1:22 10.0.0.1:443 1.1.1.1:80 1.1.1.1:53 34.120.0.10:80 172.30.241.3:8000"
  if [ $ROLE = proxy ]; then DSTS="$DSTS 172.26.0.2:53"; ALLOWED=34.120.0.10:443; else DSTS="$DSTS 34.120.0.10:443"; ALLOWED=172.26.0.2:53; fi
  for dst in $DSTS; do
    try "connect to $dst" python3 -I -c "import socket; socket.create_connection(('${dst%:*}', ${dst#*:}), timeout=2)"
  done
  if $T python3 -I -c "import socket; socket.create_connection(('${ALLOWED%:*}', ${ALLOWED#*:}), timeout=3).close()" 2>/dev/null; then
    echo "PASS $C child can still use its one permitted outbound flow $ALLOWED"; else echo "FAIL $C permitted flow $ALLOWED blocked"; FAIL=1; fi
done
echo "=== Layer N rulesets"
for C in ${CAP_CONTAINERS:-r3cap-egress r3cap-dns}; do echo "--- $C"; sudo nsenter -t "$(sudo docker inspect -f '{{.State.Pid}}' $C)" -n nft list table inet clm_r3n; done
echo "=== guard logs"
for C in ${CAP_CONTAINERS:-r3cap-egress r3cap-dns}; do sudo docker logs $C 2>&1 | grep r3-egress-guard; done
echo "=== end-to-end through the guarded proxy"
[ -z "${CAP_CONTAINERS:-}" ] && sudo docker exec r3cap-client python3 /r3/gate_client.py p1 goldtier.r3-harness.invalid /r3/ca.pem
[ $FAIL = 0 ] && echo "CAPABILITY PROOF: ALL PASS" || echo "CAPABILITY PROOF: FAILURES PRESENT"
exit $FAIL
