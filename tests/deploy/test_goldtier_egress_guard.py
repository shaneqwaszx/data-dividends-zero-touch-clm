"""R3 egress guard, Layer N and host-table contract (D-127; G2 rows G-1 to G-8).

Pure-function tests that run on any platform. Behaviour that needs a Linux network namespace
(Layer N enforcement, the child's capability sets, fail-closed supervision) is proven in the
harness (tests/deploy/egress_harness: cap_checks.sh and the RL rows), not inferred here.
"""

from __future__ import annotations

import importlib.util
import io
import json
import re
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EGRESS = ROOT / "deploy" / "egress"
HOST = EGRESS / "host"
FQDN = "goldtier.r3-test.invalid"
DST = "34.120.0.10"  # the harness fake GoldTier address (public, non-reserved)
PROXY_ENV = {"CLM_EGRESS_ROLE": "proxy", "CLM_EGRESS_FQDN": FQDN, "CLM_EGRESS_DST_V4": DST}


def _load(name: str, path: Path):  # type: ignore[no-untyped-def]
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


guard = _load("r3_guard", EGRESS / "goldtier_egress_guard.py")
watch = _load("r3_watch", HOST / "clm_r3_watch.py")


# --- G-1 --------------------------------------------------------------------------------------


def test_g1_valid_environment() -> None:
    cfg = guard.validate_env(PROXY_ENV)
    assert (cfg.role, cfg.fqdn, cfg.dst_v4) == ("proxy", FQDN, (DST,))
    assert (
        guard.validate_env({"CLM_EGRESS_ROLE": "resolver", "CLM_EGRESS_FQDN": FQDN}).role
        == "resolver"
    )


@pytest.mark.parametrize(
    "env",
    [
        {},
        {"CLM_EGRESS_ROLE": "proxy"},
        {"CLM_EGRESS_ROLE": "router", "CLM_EGRESS_FQDN": FQDN},
        {"CLM_EGRESS_ROLE": "proxy", "CLM_EGRESS_FQDN": FQDN.upper()},
        {"CLM_EGRESS_ROLE": "proxy", "CLM_EGRESS_FQDN": FQDN + "."},
        {"CLM_EGRESS_ROLE": "proxy", "CLM_EGRESS_FQDN": "*." + FQDN},
        {"CLM_EGRESS_ROLE": "proxy", "CLM_EGRESS_FQDN": "34.120.0.10"},
        {"CLM_EGRESS_ROLE": "proxy", "CLM_EGRESS_FQDN": "localhost"},
        {"CLM_EGRESS_ROLE": "proxy", "CLM_EGRESS_FQDN": "api.localhost"},
        {"CLM_EGRESS_ROLE": "proxy", "CLM_EGRESS_FQDN": "goldtier．r3-test.invalid"},
        {"CLM_EGRESS_ROLE": "proxy", "CLM_EGRESS_FQDN": FQDN + "\n- evil.invalid"},
        {"CLM_EGRESS_ROLE": "proxy", "CLM_EGRESS_FQDN": "a" * 64 + ".invalid"},
        # R-1 pin: the proxy never starts without a valid pinned set, and the resolver never has one
        {"CLM_EGRESS_ROLE": "proxy", "CLM_EGRESS_FQDN": FQDN},
        {"CLM_EGRESS_ROLE": "proxy", "CLM_EGRESS_FQDN": FQDN, "CLM_EGRESS_DST_V4": ""},
        {"CLM_EGRESS_ROLE": "resolver", "CLM_EGRESS_FQDN": FQDN, "CLM_EGRESS_DST_V4": DST},
    ],
)
def test_g1_invalid_environment_refuses_to_start(env: dict[str, str]) -> None:
    with pytest.raises(guard.GuardError):
        guard.validate_env(env)


# --- G-2 --------------------------------------------------------------------------------------


def test_g2_acl_has_one_exact_domain_and_a_closed_default() -> None:
    acl = guard.render_acl(FQDN)
    assert acl.count("allowed_domains") == 1
    assert re.findall(r"^\s+- (\S+)$", acl, re.M) == [FQDN]
    assert "*" not in acl and "open" not in acl and "report" not in acl
    assert acl.endswith("default:\n  project: r3\n  action: enforce\n")
    assert "global_allow" not in acl and "external_proxy" not in acl


def test_g2_corefile_forwards_one_exact_question() -> None:
    text = guard.render_corefile(FQDN, (EGRESS / "Corefile.template").read_text())
    assert f"expr name() == '{FQDN}.' && type() == 'A' && class() == 'IN'" in text
    assert text.count("forward . 172.26.0.2:53") == 1
    assert "block" in text and "cache" not in text.replace("no cache", "")
    assert "@" not in text and "bind 172.30.241.4" in text


# --- G-3 --------------------------------------------------------------------------------------


def _accepts(ruleset: str) -> list[str]:
    return [line.strip() for line in ruleset.splitlines() if line.strip().endswith("accept")]


def test_g3_proxy_layer_n_permits_only_amendment_c_flows() -> None:
    rules = guard.render_layer_n("proxy", "eth0", "eth1", (DST,))
    assert _accepts(rules) == [
        "ct state established,related counter accept",
        'iifname "eth0" ip saddr 172.30.241.3 ip daddr 172.30.241.2 tcp dport 4750 ct state new counter accept',  # noqa: E501
        "ct state established,related counter accept",
        'oifname "eth0" ip saddr 172.30.241.2 ip daddr 172.30.241.4 meta l4proto { udp, tcp } th dport 53 ct state new counter accept',  # noqa: E501
        'oifname "eth1" ip saddr 172.30.242.2 ip daddr != @no_egress_v4 ip daddr @goldtier_dst_v4 tcp dport 443 ct state new counter accept',  # noqa: E501
    ]
    assert "  set goldtier_dst_v4 { type ipv4_addr; elements = { 34.120.0.10 } }\n" in rules
    assert rules.count("policy drop;") == 3
    assert rules.count("meta nfproto ipv6 counter drop") == 2


def test_g3_resolver_layer_n_permits_only_amendment_c_flows() -> None:
    rules = guard.render_layer_n("resolver", "eth1", "eth0")
    assert "goldtier_dst_v4" not in rules
    assert _accepts(rules) == [
        "ct state established,related counter accept",
        'iifname "eth1" ip saddr 172.30.241.2 ip daddr 172.30.241.4 meta l4proto { udp, tcp } th dport 53 ct state new counter accept',  # noqa: E501
        "ct state established,related counter accept",
        'oifname "eth0" ip saddr 172.30.242.3 ip daddr 172.26.0.2 meta l4proto { udp, tcp } th dport 53 ct state new counter accept',  # noqa: E501
    ]


@pytest.mark.parametrize("name", ['eth0"; accept', "a b", "", "x" * 16])
def test_g3_interface_names_are_never_injected(name: str) -> None:
    with pytest.raises(guard.GuardError):
        guard.render_layer_n("proxy", name, "eth1", (DST,))


# --- R-1 pin (fast-track A2) -----------------------------------------------------------------


def test_r1_pin_valid_sets_are_canonical_and_sorted() -> None:
    assert guard.validate_dst_v4("34.120.0.10") == ("34.120.0.10",)
    assert guard.validate_dst_v4("18.135.200.6,13.42.220.164") == ("13.42.220.164", "18.135.200.6")
    eight = ",".join(f"34.120.0.{i}" for i in range(1, 9))
    assert len(guard.validate_dst_v4(eight)) == 8


@pytest.mark.parametrize(
    "value",
    [
        "",
        ",",
        "34.120.0.10,",
        "34.120.0.10,34.120.0.10",  # duplicate
        ",".join(f"34.120.0.{i}" for i in range(1, 10)),  # nine: above the stop rule
        "34.120.0.0/24",  # CIDR
        "34.120.0.10:443",
        " 34.120.0.10",
        "034.120.0.10",  # leading zero
        "34.120.0.10\n- 1.2.3.4",
        "0.0.0.0",
        "10.0.0.1",
        "100.64.0.1",
        "127.0.0.1",
        "169.254.169.254",  # IMDS
        "172.26.0.2",  # VPC resolver
        "172.30.242.1",  # uplink gateway
        "192.168.1.1",
        "192.0.2.1",
        "198.18.0.1",
        "224.0.0.1",
        "240.0.0.1",
        "255.255.255.255",
        "::1",
        "2001:db8::1",
        "goldtier.r3-test.invalid",
        "*",
    ],
)
def test_r1_pin_rejects_every_unsafe_or_malformed_set(value: str) -> None:
    with pytest.raises(guard.GuardError):
        guard.validate_dst_v4(value)
    with pytest.raises(guard.GuardError):
        guard.validate_env({**PROXY_ENV, "CLM_EGRESS_DST_V4": value})


def test_r1_pin_has_no_unpinned_proxy_rendering() -> None:
    with pytest.raises(guard.GuardError):
        guard.render_layer_n("proxy", "eth0", "eth1")
    with pytest.raises(guard.GuardError):
        guard.render_layer_n("proxy", "eth0", "eth1", ("10.0.0.1",))
    with pytest.raises(guard.GuardError):
        guard.render_layer_n("resolver", "eth1", "eth0", (DST,))
    rules = guard.render_layer_n("proxy", "eth0", "eth1", ("18.135.200.6", "13.42.220.164"))
    assert "elements = { 13.42.220.164, 18.135.200.6 }" in rules
    # The only 443 accept is bounded by the pinned set; nothing accepts "any public address".
    port443 = [line for line in _accepts(rules) if "dport 443" in line]
    assert len(port443) == 1 and "ip daddr @goldtier_dst_v4" in port443[0]


def _host_pin() -> tuple[str, ...]:
    text = (HOST / "clm_r3.nft").read_text()
    block = text[text.index("set goldtier_dst_v4 {") :]
    body = block[block.index("elements = {") + len("elements = {") : block.index("}")]
    return tuple(item.strip() for item in body.split(","))


def test_r1_pin_host_table_vars_and_guard_agree() -> None:
    vars_ = dict(
        line.split("=", 1)
        for line in (HOST / "clm_r3.vars").read_text().splitlines()
        if line and not line.startswith("#")
    )
    pinned = guard.validate_dst_v4(vars_["GOLDTIER_DST_V4"])
    assert _host_pin() == pinned
    assert len(pinned) <= guard.MAX_DST_V4


def _host_set() -> set[str]:
    text = (HOST / "clm_r3.nft").read_text()
    body = text[
        text.index("elements = {") + len("elements = {") : text.index(
            "}", text.index("elements = {")
        )
    ]
    return {item.strip() for item in body.replace("\n", " ").split(",")}


def test_g3_layer_n_host_table_and_smokescreen_deny_set_are_one_list() -> None:
    assert _host_set() == set(guard.NO_EGRESS_V4)
    assert set(guard.SMOKESCREEN_DENY_RANGES) == set(guard.NO_EGRESS_V4) | {"::/0"}


def test_host_table_matches_its_variables_and_never_flushes() -> None:
    nft = (HOST / "clm_r3.nft").read_text()
    code = "\n".join(line for line in nft.splitlines() if not line.lstrip().startswith("#"))
    vars_ = dict(
        line.split("=", 1)
        for line in (HOST / "clm_r3.vars").read_text().splitlines()
        if line and not line.startswith("#")
    )
    assert "flush" not in code
    assert code.count("table inet clm_r3") == 3 and "delete table inet clm_r3" in code
    assert "priority filter - 10; policy accept;" in code
    for key in (
        "UPLINK_IF",
        "UPLINK_BRIDGE",
        "CONTROL_BRIDGE",
        "PROXY_UPLINK_IP",
        "RESOLVER_UPLINK_IP",
        "VPC_RESOLVER_IP",
    ):
        assert vars_[key] in code, key
    assert vars_["PROXY_UPLINK_IP"] == guard.PROXY_UP_IP
    assert vars_["RESOLVER_UPLINK_IP"] == guard.RESOLVER_UP_IP
    assert vars_["VPC_RESOLVER_IP"] == guard.VPC_RESOLVER_IP
    accepts = [line.strip() for line in code.splitlines() if line.strip().endswith("accept")]
    assert accepts == [
        'oifname "clm-gt-up" ct state established,related counter accept',
        'iifname "clm-gt-up" ip saddr 172.30.242.3 ip daddr 172.26.0.2 meta l4proto { udp, tcp } th dport 53 oifname "ens5" counter accept',  # noqa: E501
        'iifname "clm-gt-up" ip saddr 172.30.242.2 ip daddr @goldtier_dst_v4 oifname "ens5" tcp dport 443 counter accept',  # noqa: E501
        'iifname { "clm-gt-up", "clm-gt-ctl" } ct state established,related counter accept',
    ]


def test_units_order_and_fail_closed_stop() -> None:
    fw = (HOST / "clm-r3-egress-firewall.service").read_text()
    wt = (HOST / "clm-r3-firewall-watch.service").read_text()
    fw_code = "\n".join(line for line in fw.splitlines() if not line.startswith("#"))
    assert (
        "Before=docker.service" in fw_code
        and "DefaultDependencies=no" in fw_code
        and "Requires=" not in fw_code
    )
    stops = [line for line in fw.splitlines() if line.startswith("ExecStop=")]
    assert stops[0].endswith("clm_r3_stop_containers.sh firewall-stop")
    assert stops[1] == "ExecStop=/usr/sbin/nft delete table inet clm_r3"
    assert "nftables" not in fw_code and "ufw" not in fw_code
    assert (
        "Restart=always" in wt
        and "ExecStopPost=" in wt
        and "After=clm-r3-egress-firewall.service docker.service" in wt
    )
    helper = (HOST / "clm_r3_stop_containers.sh").read_text()
    assert (
        "clm-staging-goldtier-egress clm-staging-goldtier-dns" in helper and '"stopping"' in helper
    )


def test_verify_script_is_read_only_and_never_touches_legacy_iptables() -> None:
    script = (HOST / "verify_host_firewall.sh").read_text()
    code = "\n".join(line for line in script.splitlines() if not line.lstrip().startswith("#"))
    assert "iptables-legacy" not in code and "ip6tables-legacy" not in code
    assert "/proc/net/ip_tables_names" in code
    assert "LiveRestoreEnabled" in code and "R3_REVIEWED_MANIFEST" in code  # QG P3-5, P3-7
    for verb in (
        "nft add",
        "nft delete",
        "nft flush",
        "nft -f",
        "systemctl start",
        "systemctl stop",
        "systemctl enable",
        "docker stop",
        "docker rm",
        "modprobe",
        "rmmod",
        "sysctl -w",
    ):
        assert verb not in code, verb


# --- G-4 --------------------------------------------------------------------------------------


def test_g4_child_is_unprivileged_with_a_scrubbed_environment() -> None:
    prefix = guard.setpriv_prefix()
    assert prefix == [
        "/usr/bin/setpriv",
        "--reuid=65532",
        "--regid=65532",
        "--clear-groups",
        "--inh-caps=-all",
        "--ambient-caps=-all",
        "--bounding-set=-all",
        "--no-new-privs",
        "--",
    ]
    proxy = guard.GuardConfig("proxy", FQDN)
    assert guard.child_env(proxy) == {"PATH": guard.CHILD_PATH, "R3_EGRESS_FQDN": FQDN}
    assert guard.child_env(guard.GuardConfig("resolver", FQDN)) == {"PATH": guard.CHILD_PATH}


def test_g4_smokescreen_argv_has_no_danger_or_bypass_flag() -> None:
    argv = guard.smokescreen_argv(guard.GuardConfig("proxy", FQDN))
    joined = " ".join(argv)
    for flag in (
        "unsafe",
        "allow-range",
        "allow-address",
        "upstream",
        "allow-self",
        "disable-acl",
        "prometheus",
        "proxy-protocol",
        "tls-",
    ):
        assert flag not in joined, flag
    assert argv[argv.index("--resolver-address") + 1] == "172.30.241.4:53"
    assert argv[argv.index("--listen-ip") + 1] == "172.30.241.2"
    assert [argv[i + 1] for i, a in enumerate(argv) if a == "--deny-range"] == list(
        guard.SMOKESCREEN_DENY_RANGES
    )


# --- G-5 --------------------------------------------------------------------------------------

SAMPLE = {
    "nftables": [
        {"metainfo": {"version": "1.0.6", "json_schema_version": 1}},
        {"table": {"family": "inet", "name": "clm_r3n", "handle": 3}},
        {
            "rule": {
                "family": "inet",
                "table": "clm_r3n",
                "chain": "output",
                "handle": 9,
                "expr": [{"counter": {"packets": 4, "bytes": 240}}, {"drop": None}],
            }
        },
    ]
}


@pytest.mark.parametrize("hasher", [guard.normalised_ruleset_hash, watch.normalised_hash])
def test_g5_hash_ignores_counters_and_handles_but_not_rules(hasher) -> None:  # type: ignore[no-untyped-def]
    base = hasher(json.dumps(SAMPLE))
    bumped = json.loads(json.dumps(SAMPLE))
    bumped["nftables"][2]["rule"]["expr"][0]["counter"] = {"packets": 99, "bytes": 9999}
    bumped["nftables"][2]["rule"]["handle"] = 77
    bumped["nftables"][0]["metainfo"]["version"] = "9"
    assert hasher(json.dumps(bumped)) == base
    changed = json.loads(json.dumps(SAMPLE))
    changed["nftables"][2]["rule"]["expr"][1] = {"accept": None}
    assert hasher(json.dumps(changed)) != base


def test_g5_guard_and_watcher_hash_identically() -> None:
    assert guard.normalised_ruleset_hash(json.dumps(SAMPLE)) == watch.normalised_hash(
        json.dumps(SAMPLE)
    )


# --- G-6 --------------------------------------------------------------------------------------


def test_g6_canaries_report_every_reachable_target(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(guard, "tcp_blocked", lambda ip, port, timeout=0.5: False)
    monkeypatch.setattr(guard, "dns_rcode", lambda server, name, timeout=1.5: 0)
    assert guard.canaries(guard.GuardConfig("proxy", FQDN)) == [
        "imds_reachable",
        "uplink_gateway_reachable",
        "random_name_not_refused",
    ]
    assert guard.canaries(guard.GuardConfig("resolver", FQDN)) == [
        "imds_reachable",
        "uplink_gateway_reachable",
    ]


def test_g6_canaries_pass_only_when_blocked_and_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, int]] = []
    monkeypatch.setattr(
        guard, "tcp_blocked", lambda ip, port, timeout=0.5: calls.append((ip, port)) or True
    )
    monkeypatch.setattr(
        guard,
        "dns_rcode",
        lambda server, name, timeout=1.5: (
            5 if server == "172.30.241.4" and name.endswith(".invalid") else 0
        ),
    )
    assert guard.canaries(guard.GuardConfig("proxy", FQDN)) == []
    assert calls == [("169.254.169.254", 80), ("172.30.242.1", 22)]


def test_g6_dns_query_is_a_plain_recursive_a_question() -> None:
    q = guard.dns_query("r3-canary-1.invalid")
    assert q[2:4] == b"\x01\x00" and q.endswith(b"\x07invalid\x00\x00\x01\x00\x01")


# --- G-7 --------------------------------------------------------------------------------------


def test_g7_supervision_cadence() -> None:
    assert guard.HASH_INTERVAL <= 0.5
    assert guard.CANARY_INTERVAL <= 2.0
    assert guard.CANARY_TIMEOUT * 2 < guard.CANARY_INTERVAL
    assert guard.CANARY_STALL < 10


# --- G-8 --------------------------------------------------------------------------------------


def test_g8_guard_logs_are_single_line_json_with_no_payload() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        guard.log("child_started", pid=7, uid=65532)
    record = json.loads(buf.getvalue())
    assert set(record) == {"t", "component", "event", "pid", "uid"}
    source = (EGRESS / "goldtier_egress_guard.py").read_text()
    for call in re.findall(r"log\(([^)]*)\)", source):
        assert "environ" not in call and "argv" not in call and "stdout" not in call
