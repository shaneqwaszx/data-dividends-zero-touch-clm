"""Hosted GPT-OSS egress guard (D-138 A1, PROPOSED; LOCAL DESIGN CANDIDATE, not approved for AWS).
PID 1 of the openrouter-egress and openrouter-dns containers (compose.assistant-openrouter.yml).

Adapted from R3's deploy/egress/goldtier_egress_guard.py (D-127, reviewed in the R3 G2 QG). The
structure, the order of the steps and the fail-closed supervision are R3's; what differs is
listed here and nothing else:

- the addresses: the internal network openrouter-control (172.30.246.0/29: proxy .2, the
  assistant .3, resolver .4) and the uplink openrouter-uplink (172.30.247.0/29: proxy .2,
  resolver .3, gateway .1);
- the FQDN is a reviewed constant, openrouter.ai. The environment must name exactly it;
- there is NO destination address pin. OpenRouter publishes no fixed inbound range, and
  Cloudflare's ranges would admit any Cloudflare-fronted site, so the proxy's Layer N admits
  tcp/443 to a public IPv4 outside NO_EGRESS_V4. What it may reach is decided by the exact-host
  gate in front of Smokescreen (R3's smokescreen-main, unchanged: only `CONNECT openrouter.ai:443
  HTTP/1.1` with one exact Host header), Smokescreen's ACL (one domain) and the exact-name
  resolver (only `openrouter.ai. IN A` is forwarded). A CLM_EGRESS_DST_V4 value is refused;
- the table, run directory, log component and event names (clm_r22on, /run/r22o, CLM_R22O_*).

In order, the guard: validates its environment; renders the child's configuration into a
root-owned tmpfs (files 0444); installs Layer N, a default-deny nft table in this network
namespace that permits exactly its role's flows, and records the table's normalised hash; runs
the startup canaries (IMDS and the uplink gateway :22 blocked; for the proxy a random name must
be REFUSED by the resolver); starts the child through setpriv as 65532 with every capability set
empty and no_new_privs; drops SETUID, SETGID and SETPCAP, keeping NET_ADMIN to read nft; and
supervises (Layer N hash and rendered files every 0.5 s, canaries every 2 s). On any mismatch,
or if the child exits, it kills the child and exits non-zero. The container's restart policy is
"no", so the proxy then stays down until an operator starts it through clm-r22o-egress.service.

The guard logs only event names, states and safe identifiers. Stdlib only. Pure rendering and
validation functions are importable on any platform for unit tests.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
import secrets
import signal
import socket
import struct
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

# --- Reviewed constants (must match compose.assistant-openrouter.yml and clm_r22o.vars) -------
OPENROUTER_FQDN = "openrouter.ai"
PROXY_CTL_IP = "172.30.246.2"
CLIENT_CTL_IP = "172.30.246.3"  # the assistant
RESOLVER_CTL_IP = "172.30.246.4"
PROXY_UP_IP = "172.30.247.2"
RESOLVER_UP_IP = "172.30.247.3"
UPLINK_GATEWAY_IP = "172.30.247.1"
VPC_RESOLVER_IP = "172.26.0.2"
IMDS_IP = "169.254.169.254"
PROXY_PORT = 4750
CHILD_UID = 65532
NFT_TABLE = "clm_r22on"
# The fixed role R3's entrypoint (smokescreen-main/main.go) gives every request; the ACL must
# name it. Unchanged so the reviewed entrypoint is reused byte for byte.
ENTRYPOINT_ROLE = "goldtier-backend"
NO_EGRESS_V4 = (
    "0.0.0.0/8",
    "10.0.0.0/8",
    "100.64.0.0/10",
    "127.0.0.0/8",
    "169.254.0.0/16",
    "172.16.0.0/12",
    "192.0.0.0/24",
    "192.0.2.0/24",
    "192.88.99.0/24",
    "192.168.0.0/16",
    "198.18.0.0/15",
    "198.51.100.0/24",
    "203.0.113.0/24",
    "224.0.0.0/4",
    "240.0.0.0/4",
)
SMOKESCREEN_DENY_RANGES = NO_EGRESS_V4 + ("::/0",)
RUN_DIR = Path("/run/r22o")
COREFILE_TEMPLATE = Path("/opt/egress/Corefile.template")
HEALTH_FILE = RUN_DIR / "health.json"
CHILD_PATH = "/usr/local/bin:/usr/bin:/bin"
HASH_INTERVAL = 0.5
CANARY_INTERVAL = 2.0
CANARY_STALL = 8.0
CANARY_TIMEOUT = 0.5
_FQDN = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]{0,61}[a-z0-9]$")
_CAP = {"NET_ADMIN": 12, "SETGID": 6, "SETUID": 7, "SETPCAP": 8}


class GuardError(Exception):
    """A fail-closed condition. The message is a short, safe reason code."""


@dataclass(frozen=True)
class GuardConfig:
    role: str
    fqdn: str


def log(event: str, **fields: object) -> None:
    record = {
        "t": round(time.time(), 3),
        "component": "r22o-egress-guard",
        "event": event,
        **fields,
    }
    sys.stdout.write(json.dumps(record, sort_keys=True) + "\n")
    sys.stdout.flush()


# --- environment validation -------------------------------------------------------------------


def validate_fqdn(value: str) -> str:
    if (
        not value
        or len(value) > 253
        or not _FQDN.match(value)
        or value.endswith(".")
        or value.endswith(".localhost")
    ):
        raise GuardError("fqdn_invalid")
    try:
        ipaddress.ip_address(value)
    except ValueError:
        pass
    else:
        raise GuardError("fqdn_is_ip_literal")
    if value != OPENROUTER_FQDN:
        raise GuardError("fqdn_not_openrouter")
    return value


def validate_env(environ: dict[str, str]) -> GuardConfig:
    role = environ.get("CLM_EGRESS_ROLE", "")
    if role not in {"proxy", "resolver"}:
        raise GuardError("role_invalid")
    fqdn = validate_fqdn(environ.get("CLM_EGRESS_FQDN", ""))
    # There is no address pin in this lane; a value would suggest one and is refused.
    if "CLM_EGRESS_DST_V4" in environ:
        raise GuardError("dst_v4_not_supported")
    return GuardConfig(role=role, fqdn=fqdn)


# --- rendering --------------------------------------------------------------------------------


def render_acl(fqdn: str) -> str:
    validate_fqdn(fqdn)
    return (
        "---\nversion: v1\nservices:\n"
        f"  - name: {ENTRYPOINT_ROLE}\n    project: r22o\n    action: enforce\n"
        f"    allowed_domains:\n      - {fqdn}\n"
        "default:\n  project: r22o\n  action: enforce\n"
    )


def render_corefile(fqdn: str, template: str) -> str:
    validate_fqdn(fqdn)
    for marker in ("@FQDN@", "@LISTEN@", "@UPSTREAM@"):
        if marker not in template:
            raise GuardError("corefile_template_invalid")
    out = (
        template.replace("@FQDN@", fqdn)
        .replace("@LISTEN@", RESOLVER_CTL_IP)
        .replace("@UPSTREAM@", VPC_RESOLVER_IP)
    )
    if "@" in out.replace("{remote}", ""):
        raise GuardError("corefile_render_incomplete")
    return out


def smokescreen_argv(cfg: GuardConfig) -> list[str]:
    argv = [
        "/usr/local/bin/smokescreen",
        "--listen-ip",
        PROXY_CTL_IP,
        "--listen-port",
        str(PROXY_PORT),
        "--egress-acl-file",
        str(RUN_DIR / "acl.yaml"),
        "--resolver-address",
        f"{RESOLVER_CTL_IP}:53",
    ]
    for cidr in SMOKESCREEN_DENY_RANGES:
        argv += ["--deny-range", cidr]
    return argv


def coredns_argv() -> list[str]:
    return ["/usr/local/bin/coredns", "-conf", str(RUN_DIR / "Corefile")]


def child_env(cfg: GuardConfig) -> dict[str, str]:
    env = {"PATH": CHILD_PATH}
    if cfg.role == "proxy":
        env["R3_EGRESS_FQDN"] = cfg.fqdn  # the variable R3's entrypoint reads
    return env


def setpriv_prefix() -> list[str]:
    return [
        "/usr/bin/setpriv",
        f"--reuid={CHILD_UID}",
        f"--regid={CHILD_UID}",
        "--clear-groups",
        "--inh-caps=-all",
        "--ambient-caps=-all",
        "--bounding-set=-all",
        "--no-new-privs",
        "--",
    ]


# --- Layer N ----------------------------------------------------------------------------------


def _q(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.@-]{1,15}", name):
        raise GuardError("interface_name_invalid")
    return f'"{name}"'


def render_layer_n(role: str, ctl_if: str, up_if: str) -> str:
    ctl, up = _q(ctl_if), _q(up_if)
    elements = ", ".join(NO_EGRESS_V4)
    if role == "proxy":
        inbound = (
            f"iifname {ctl} ip saddr {CLIENT_CTL_IP} ip daddr {PROXY_CTL_IP} "
            f"tcp dport {PROXY_PORT} ct state new counter accept"
        )
        # No pin: tcp/443 to a public IPv4. The exact-host gate decides the host.
        outbound = (
            f"oifname {ctl} ip saddr {PROXY_CTL_IP} ip daddr {RESOLVER_CTL_IP} "
            "meta l4proto { udp, tcp } th dport 53 ct state new counter accept\n"
            f"    oifname {up} ip saddr {PROXY_UP_IP} ip daddr != @no_egress_v4 "
            "tcp dport 443 ct state new counter accept"
        )
    elif role == "resolver":
        inbound = (
            f"iifname {ctl} ip saddr {PROXY_CTL_IP} ip daddr {RESOLVER_CTL_IP} "
            "meta l4proto { udp, tcp } th dport 53 ct state new counter accept"
        )
        outbound = (
            f"oifname {up} ip saddr {RESOLVER_UP_IP} ip daddr {VPC_RESOLVER_IP} "
            "meta l4proto { udp, tcp } th dport 53 ct state new counter accept"
        )
    else:
        raise GuardError("role_invalid")
    return (
        f"table inet {NFT_TABLE} {{\n"
        f"  set no_egress_v4 {{ type ipv4_addr; flags interval; elements = {{ {elements} }} }}\n"
        "  chain input {\n"
        "    type filter hook input priority filter; policy drop;\n"
        "    ct state established,related counter accept\n"
        "    meta nfproto ipv6 counter drop\n"
        f"    {inbound}\n"
        "    counter drop\n"
        "  }\n"
        "  chain forward {\n"
        "    type filter hook forward priority filter; policy drop;\n"
        "    counter drop\n"
        "  }\n"
        "  chain output {\n"
        "    type filter hook output priority filter; policy drop;\n"
        "    ct state established,related counter accept\n"
        "    meta nfproto ipv6 counter drop\n"
        f"    {outbound}\n"
        "    counter drop\n"
        "  }\n"
        "}\n"
    )


def normalised_ruleset_hash(nft_json: str) -> str:
    """SHA-256 of `nft -j list table` output with handles and counter values removed."""

    def strip(node: object) -> object:
        if isinstance(node, dict):
            out = {}
            for key, value in node.items():
                if key == "handle":
                    continue
                if key == "counter" and isinstance(value, dict):
                    out[key] = {}
                    continue
                out[key] = strip(value)
            return out
        if isinstance(node, list):
            return [
                strip(item) for item in node if not (isinstance(item, dict) and "metainfo" in item)
            ]
        return node

    document = json.loads(nft_json)
    return hashlib.sha256(json.dumps(strip(document), sort_keys=True).encode()).hexdigest()


# --- canaries ---------------------------------------------------------------------------------


def tcp_blocked(ip: str, port: int, timeout: float = CANARY_TIMEOUT) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((ip, port))
    except OSError:
        return True
    finally:
        s.close()
    return False


def dns_query(name: str, qtype: int = 1) -> bytes:
    txid = secrets.randbits(16)
    question = b"".join(bytes([len(p)]) + p.encode("ascii") for p in name.split(".")) + b"\x00"
    return (
        struct.pack("!HHHHHH", txid, 0x0100, 1, 0, 0, 0) + question + struct.pack("!HH", qtype, 1)
    )


def dns_rcode(server: str, name: str, timeout: float = 1.5) -> int | None:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    try:
        query = dns_query(name)
        s.sendto(query, (server, 53))
        reply, _ = s.recvfrom(4096)
        if reply[:2] != query[:2]:
            return None
        return reply[3] & 0x0F
    except OSError:
        return None
    finally:
        s.close()


def canaries(cfg: GuardConfig) -> list[str]:
    failures = []
    if not tcp_blocked(IMDS_IP, 80):
        failures.append("imds_reachable")
    if not tcp_blocked(UPLINK_GATEWAY_IP, 22):
        failures.append("uplink_gateway_reachable")
    if cfg.role == "proxy":
        name = f"r22o-canary-{secrets.token_hex(6)}.invalid"
        if dns_rcode(RESOLVER_CTL_IP, name) != 5:
            failures.append("random_name_not_refused")
    return failures


# --- Linux-only helpers -----------------------------------------------------------------------


def interface_for(ip: str) -> str:
    import fcntl  # Linux only

    siocgifaddr = 0x8915
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        for _, name in socket.if_nameindex():
            try:
                raw = fcntl.ioctl(s.fileno(), siocgifaddr, struct.pack("256s", name.encode()[:15]))
            except OSError:
                continue
            if socket.inet_ntoa(raw[20:24]) == ip:
                return name
    finally:
        s.close()
    raise GuardError("interface_missing")


def nft(*args: str, stdin: str | None = None) -> str:
    result = subprocess.run(
        ["/usr/sbin/nft", *args],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=10,
        env={"PATH": CHILD_PATH},
    )
    if result.returncode != 0:
        raise GuardError("nft_failed")
    return result.stdout


def current_hash() -> str:
    return normalised_ruleset_hash(nft("-j", "list", "table", "inet", NFT_TABLE))


def drop_guard_privileges() -> None:
    """Keep only NET_ADMIN in the guard (bounding, then effective/permitted; no inheritable)."""
    import ctypes  # Linux only

    libc = ctypes.CDLL(None, use_errno=True)
    pr_capbset_drop = 24
    for name in ("SETUID", "SETGID", "SETPCAP"):
        if libc.prctl(pr_capbset_drop, _CAP[name], 0, 0, 0) != 0:
            raise GuardError("bounding_drop_failed")

    class Header(ctypes.Structure):
        _fields_ = [("version", ctypes.c_uint32), ("pid", ctypes.c_int)]

    class Data(ctypes.Structure):
        _fields_ = [
            ("effective", ctypes.c_uint32),
            ("permitted", ctypes.c_uint32),
            ("inheritable", ctypes.c_uint32),
        ]

    keep = 1 << _CAP["NET_ADMIN"]
    header = Header(0x20080522, 0)
    data = (Data * 2)(Data(keep, keep, 0), Data(0, 0, 0))
    if libc.capset(ctypes.byref(header), data) != 0:
        raise GuardError("capset_failed")
    pr_set_no_new_privs = 38
    if libc.prctl(pr_set_no_new_privs, 1, 0, 0, 0) != 0:
        raise GuardError("no_new_privs_failed")


def write_file(path: Path, text: str) -> str:
    path.write_text(text)
    os.chmod(path, 0o444)
    return hashlib.sha256(text.encode()).hexdigest()


def write_health(state: str, child_pid: int | None) -> None:
    tmp = HEALTH_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps({"t": time.time(), "state": state, "child_pid": child_pid}))
    os.replace(tmp, HEALTH_FILE)


def health() -> int:
    try:
        record = json.loads(HEALTH_FILE.read_text())
    except (OSError, ValueError):
        return 1
    fresh = time.time() - float(record.get("t", 0)) < 6
    return 0 if fresh and record.get("state") == "supervising" else 1


# --- main -------------------------------------------------------------------------------------


def run(environ: dict[str, str]) -> int:
    cfg = validate_env(environ)
    log("guard_start", role=cfg.role)
    if os.geteuid() != 0:
        raise GuardError("guard_not_root")
    RUN_DIR.mkdir(mode=0o755, exist_ok=True)
    os.chmod(RUN_DIR, 0o755)
    files: dict[Path, str] = {}
    if cfg.role == "proxy":
        files[RUN_DIR / "acl.yaml"] = write_file(RUN_DIR / "acl.yaml", render_acl(cfg.fqdn))
        argv = smokescreen_argv(cfg)
        ctl_ip, up_ip = PROXY_CTL_IP, PROXY_UP_IP
    else:
        text = render_corefile(cfg.fqdn, COREFILE_TEMPLATE.read_text())
        files[RUN_DIR / "Corefile"] = write_file(RUN_DIR / "Corefile", text)
        argv = coredns_argv()
        ctl_ip, up_ip = RESOLVER_CTL_IP, RESOLVER_UP_IP
    ctl_if, up_if = interface_for(ctl_ip), interface_for(up_ip)
    ruleset = render_layer_n(cfg.role, ctl_if, up_if)
    nft("-f", "-", stdin=ruleset)
    expected = current_hash()
    log("layer_n_applied", table=NFT_TABLE, sha256=expected, ctl_if=ctl_if, up_if=up_if)

    deadline = time.monotonic() + 30
    while failures := canaries(cfg):
        if time.monotonic() > deadline or failures != ["random_name_not_refused"]:
            raise GuardError("canary_failed:" + ",".join(failures))
        time.sleep(1)  # the resolver may still be starting
    log("canaries_passed")

    child = subprocess.Popen(setpriv_prefix() + argv, env=child_env(cfg), close_fds=True)
    log("child_started", pid=child.pid, uid=CHILD_UID)
    drop_guard_privileges()
    log("guard_privileges_dropped", kept="NET_ADMIN")

    stopping = {"flag": False}

    def on_term(signum: int, _frame: object) -> None:
        stopping["flag"] = True

    signal.signal(signal.SIGTERM, on_term)
    signal.signal(signal.SIGINT, on_term)
    probe: dict[str, object] = {"failures": [], "t": time.monotonic()}

    def canary_loop() -> None:
        while True:
            probe["failures"] = canaries(cfg)
            probe["t"] = time.monotonic()
            time.sleep(CANARY_INTERVAL)

    threading.Thread(target=canary_loop, name="r22o-canary", daemon=True).start()
    while True:
        if stopping["flag"]:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
            log("guard_stop", reason="signal")
            return 0
        reason = None
        if child.poll() is not None:
            reason = f"child_exited:{child.returncode}"
        else:
            try:
                if current_hash() != expected:
                    reason = "layer_n_hash_mismatch"
            except (GuardError, ValueError):
                reason = "layer_n_missing"
            for path, digest in files.items():
                try:
                    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                        reason = "rendered_config_changed"
                except OSError:
                    reason = "rendered_config_missing"
            failures = probe["failures"]
            if reason is None and failures:
                reason = "canary_failed:" + ",".join(failures)  # type: ignore[arg-type]
            if reason is None and time.monotonic() - float(probe["t"]) > CANARY_STALL:  # type: ignore[arg-type]
                reason = "canary_stalled"
        if reason is not None:
            if child.poll() is None:
                child.kill()
                child.wait()
            log("CLM_R22O_LAYER_N_FAIL_CLOSED", reason=reason)
            write_health("failed", None)
            return 1
        write_health("supervising", child.pid)
        time.sleep(HASH_INTERVAL)


def main(argv: list[str]) -> int:
    if argv[1:] == ["--health"]:
        return health()
    try:
        return run(dict(os.environ))
    except GuardError as exc:
        log("CLM_R22O_GUARD_REFUSED_START", reason=str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
