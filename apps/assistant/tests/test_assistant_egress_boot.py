"""P2-1 (R2.2 code QG): the hosted assistant's boot fails closed (E1 local design candidate).

Static checks of the reviewed files; the behaviour (reboots with a broken table file, a missing
nft, masked units, a Docker restart) is exercised in the E1 harness VM (matrix C).
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

DEPLOY = Path(__file__).resolve().parents[1] / "deploy"
EGRESS = DEPLOY / "egress"


def _code(path: Path) -> str:
    return "\n".join(
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("#")
    )


def _unit(name: str) -> dict[str, list[str]]:
    values: dict[str, list[str]] = {}
    for line in _code(EGRESS / name).splitlines():
        if "=" in line and not line.startswith("["):
            key, value = line.split("=", 1)
            values.setdefault(key.strip(), []).append(value.strip())
    return values


def test_docker_never_starts_the_assistant_and_never_translates_its_uplink() -> None:
    overlay = yaml.safe_load((DEPLOY / "compose.assistant-provider.yml").read_text("utf-8"))
    assert overlay["services"]["assistant"]["restart"] == "no"
    options = overlay["networks"]["assistant-uplink"]["driver_opts"]
    assert options["com.docker.network.bridge.name"] == "clm-as-up"
    assert options["com.docker.network.bridge.enable_ip_masquerade"] == "false"


def test_the_table_holds_the_only_translation_and_only_for_the_allowed_flow() -> None:
    table = _code(EGRESS / "clm_r22.nft")
    nat = re.search(r"chain postrouting \{(.*?)\n  \}", table, re.S)
    assert nat is not None
    rules = [line.strip() for line in nat.group(1).splitlines() if line.strip()]
    assert rules == [
        "type nat hook postrouting priority srcnat; policy accept;",
        'ip saddr 172.30.243.2 ip daddr @anthropic_dst_v4 oifname "ens5" tcp dport 443 '
        "counter masquerade",
    ]
    # No other NAT anywhere in the table (no snat, dnat or redirect).
    assert table.count("masquerade") == 1
    assert not re.search(r"\b(?:snat|dnat|redirect)\b", table)


def test_only_the_start_gate_starts_the_assistant_and_only_behind_the_verified_table() -> None:
    gate = _unit("clm-r22-assistant.service")
    required = gate["Requires"][0].split()
    assert set(required) == {
        "clm-r22-assistant-firewall.service",
        "clm-r22-firewall-watch.service",
        "docker.service",
    }
    assert gate["BindsTo"] == ["clm-r22-assistant-firewall.service"]
    assert set(gate["After"][0].split()) == set(required)
    assert gate["Type"] == ["oneshot"] and gate["RemainAfterExit"] == ["yes"]
    pre = gate["ExecStartPre"]
    assert pre[0].endswith(
        "clm_r22_watch.py --table-file /etc/clm/r22/clm_r22.nft "
        "--containers clm-staging-assistant --check-only"
    )
    assert "is-active -q clm-r22-firewall-watch.service" in pre[1]
    assert gate["ExecStart"] == ["/usr/bin/docker start clm-staging-assistant"]
    assert gate["ExecStop"] == ["/usr/local/lib/clm-r22/clm_r22_stop_assistant.sh gate-stop"]
    assert gate["WantedBy"] == ["multi-user.target"]
    # Nothing else in the deployment starts it.
    for name in ("clm-r22-assistant-firewall.service", "clm-r22-firewall-watch.service"):
        assert "docker start" not in _code(EGRESS / name)
    watcher = _code(EGRESS / "clm_r22_watch.py")
    assert '"start"' not in re.sub(r'check\("start"\)', "", watcher)


def test_the_firewall_unit_fails_when_the_table_cannot_load() -> None:
    firewall = _unit("clm-r22-assistant-firewall.service")
    # A oneshot whose only start command is the load: a broken file or no nft fails the unit,
    # and the gate (Requires/BindsTo) then never starts.
    assert firewall["Type"] == ["oneshot"]
    assert firewall["ExecStart"] == ["/usr/sbin/nft -f /etc/clm/r22/clm_r22.nft"]
    assert "ExecStartPost" not in firewall and "SuccessExitStatus" not in firewall


def test_the_host_check_covers_the_gate_policy_and_translation() -> None:
    verify = (EGRESS / "verify_assistant_egress.sh").read_text("utf-8")
    assert "clm-r22-assistant.service enabled" in verify
    assert "assistant restart policy is no" in verify
    assert "Docker does not masquerade clm-as-up" in verify
    # QG N4: the live state, not only the configuration.
    assert "systemctl is-active -q clm-r22-assistant.service" in verify
    assert "SubState --value clm-r22-firewall-watch.service" in verify
    assert '"running/healthy"' in verify


def test_the_readme_has_the_upgrade_pin_and_recovery_procedures() -> None:
    readme = (EGRESS / "README.md").read_text("utf-8")
    for heading in ("## Upgrade from R2.2", "## Pin maintenance", "## Recovery"):
        assert heading in readme
    # Never start the assistant outside the gate; recreate the R2.2 network and container.
    assert "docker network rm clm-staging_assistant-uplink" in readme
    assert "systemctl restart clm-r22-assistant" in readme
    assert "reload the firewall" not in readme


def test_the_install_steps_create_without_starting_and_start_through_the_gate() -> None:
    readme = (EGRESS / "README.md").read_text("utf-8")
    assert "up -d --no-start" in readme and "systemctl start clm-r22-assistant" in readme
    assert "systemctl enable clm-r22-assistant" in readme


def test_the_watcher_never_stops_restarting_and_each_exit_stops_the_assistant() -> None:
    watch = _unit("clm-r22-firewall-watch.service")
    assert watch["StartLimitIntervalSec"] == ["0"]
    assert watch["Restart"] == ["always"] and watch["RestartSec"] == ["1"]
    assert watch["ExecStopPost"] == [
        "/usr/local/lib/clm-r22/clm_r22_stop_assistant.sh watcher-stop"
    ]
