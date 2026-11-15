"""R3 Compose overlay contract (D-127; G2 rows C-1 to C-5, extended).

Renders the stack offline with `docker compose config` (no daemon, no network, no image pull)
and asserts the merged model. Skipped when the Docker CLI with Compose is unavailable.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "deploy"
ASSISTANT = ROOT / "apps" / "assistant" / "deploy" / "compose.assistant.yml"
OVERLAY = DEPLOY / "compose.goldtier-egress.yml"
R3_SERVICES = {"goldtier-egress", "goldtier-dns"}
R3_CAPS = ["NET_ADMIN", "SETGID", "SETPCAP", "SETUID"]
# Never let the developer's own environment leak into an interpolated value.
INTERPOLATED_PREFIXES = (
    "BACKEND_",
    "FRONTEND_",
    "ASSISTANT_",
    "GOLDTIER_",
    "CLM_",
    "MONGO_",
    "HTTP_BIND",
    "HTTPS_BIND",
    "COMPOSE_",
)

pytestmark = pytest.mark.skipif(shutil.which("docker") is None, reason="Docker CLI not available")


@pytest.fixture()
def env(tmp_path: Path) -> dict[str, str]:
    for name in ("backend.env", "mongo-ca.pem", "mongo-server.pem", "empty.env"):
        (tmp_path / name).write_text("", encoding="ascii")
    inherited = {
        k: v for k, v in os.environ.items() if not k.upper().startswith(INTERPOLATED_PREFIXES)
    }
    return inherited | {
        "R3_TEST_EMPTY_ENV_FILE": str(tmp_path / "empty.env"),
        "BACKEND_IMAGE": "example.invalid/backend@sha256:" + "0" * 64,
        "FRONTEND_IMAGE": "example.invalid/frontend@sha256:" + "1" * 64,
        "ASSISTANT_IMAGE": "example.invalid/assistant@sha256:" + "2" * 64,
        "GOLDTIER_EGRESS_IMAGE": "example.invalid/egress@sha256:" + "3" * 64,
        "BACKEND_ENV_FILE": str(tmp_path / "backend.env"),
        "CLM_SITE": "clm.example.invalid",
        "MONGO_URI": "mongodb://placeholder.invalid/?tls=true",
        "MONGO_CA_FILE": str(tmp_path / "mongo-ca.pem"),
        "MONGO_SERVER_PEM": str(tmp_path / "mongo-server.pem"),
        "MONGO_DATA_VOLUME": "clm-r3-test-mongo",
        "ASSISTANT_DATA_VOLUME": "clm-r3-test-assistant",
        "ASSISTANT_BROWSER_ORIGIN": "https://clm.example.invalid",
        "ASSISTANT_ELIGIBLE_CASE_REFS": "000000000000",
        "ASSISTANT_ELIGIBLE_CREATED_BEFORE": "2099-01-01T00:00:00Z",
        "CLM_GOLDTIER_EGRESS_FQDN": "goldtier.r3-test.invalid",
        "CLM_GOLDTIER_EGRESS_DST_V4": "34.120.0.10",
    }


def render(env: dict[str, str], *files: Path, expect_ok: bool = True) -> dict:
    # --env-file points at an empty file so no project .env is ever read.
    args = [
        "docker",
        "compose",
        "--env-file",
        env["R3_TEST_EMPTY_ENV_FILE"],
        "--project-name",
        "clm-staging",
    ]
    for f in files:
        args += ["-f", str(f)]
    result = subprocess.run(
        args + ["config", "--format", "json", "--no-path-resolution"],
        capture_output=True,
        text=True,
        env=env,
        cwd=ROOT,
        timeout=60,
    )
    if not expect_ok:
        assert result.returncode != 0, "render unexpectedly succeeded"
        return {"stderr": result.stderr}
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


BASE = (DEPLOY / "compose.yml", DEPLOY / "compose.mongo.yml")


def full(env: dict[str, str], *, assistant: bool = False) -> dict:
    files = BASE + ((ASSISTANT,) if assistant else ()) + (OVERLAY,)
    return render(env, *files)


@pytest.mark.parametrize("assistant", [False, True])
def test_c1_network_sets_per_service(env: dict[str, str], assistant: bool) -> None:
    services = full(env, assistant=assistant)["services"]
    nets = {name: set(svc.get("networks", {})) for name, svc in services.items()}
    assert nets["backend"] == {"proxy", "database", "goldtier-control"}
    assert nets["mongo"] == {"database"}
    assert nets["frontend"] == {"default", "proxy"}
    assert nets["goldtier-egress"] == {"goldtier-control", "goldtier-uplink"}
    assert nets["goldtier-dns"] == {"goldtier-control", "goldtier-uplink"}
    if assistant:
        assert nets["assistant"] == {"proxy"}
    addresses = {
        (name, net): cfg.get("ipv4_address")
        for name, svc in services.items()
        for net, cfg in svc.get("networks", {}).items()
        if net.startswith("goldtier")
    }
    assert addresses == {
        ("backend", "goldtier-control"): "172.30.241.3",
        ("goldtier-egress", "goldtier-control"): "172.30.241.2",
        ("goldtier-egress", "goldtier-uplink"): "172.30.242.2",
        ("goldtier-dns", "goldtier-control"): "172.30.241.4",
        ("goldtier-dns", "goldtier-uplink"): "172.30.242.3",
    }


def test_c2_network_definitions(env: dict[str, str]) -> None:
    networks = full(env)["networks"]
    control, uplink = networks["goldtier-control"], networks["goldtier-uplink"]
    assert control.get("internal") is True and not uplink.get("internal")
    assert control["driver_opts"] == {"com.docker.network.bridge.name": "clm-gt-ctl"}
    assert uplink["driver_opts"] == {"com.docker.network.bridge.name": "clm-gt-up"}
    for net, subnet in ((control, "172.30.241.0/29"), (uplink, "172.30.242.0/29")):
        assert net.get("enable_ipv6") is False
        assert net["ipam"]["config"][0]["subnet"] == subnet
    for net in networks.values():
        assert "com.docker.network.bridge.enable_icc" not in net.get("driver_opts", {})


def test_c3_mode_defaults_to_mock_and_writes_stay_false(env: dict[str, str]) -> None:
    backend = full(env)["services"]["backend"]["environment"]
    assert backend["GOLDTIER_CONNECTOR_MODE"] == "mock"
    assert backend["GOLDTIER_SANDBOX_ALLOW_WRITES"] == "false"
    assert backend["GOLDTIER_SANDBOX_EGRESS_PROXY_URL"] == "http://clm-goldtier-egress:4750"
    assert backend["GOLDTIER_SANDBOX_EGRESS_FQDN"] == "goldtier.r3-test.invalid"
    assert "GOLDTIER_SANDBOX_TLS_CA_FILE" not in backend
    selected = full(env | {"CLM_GOLDTIER_CONNECTOR_MODE": "sandbox"})["services"]["backend"][
        "environment"
    ]
    assert selected["GOLDTIER_CONNECTOR_MODE"] == "sandbox"
    assert selected["GOLDTIER_SANDBOX_ALLOW_WRITES"] == "false"


def test_c4_hardening_capabilities_ports_and_dns(env: dict[str, str]) -> None:
    services = full(env, assistant=True)["services"]
    for name, svc in services.items():
        if name in R3_SERVICES:
            assert sorted(svc["cap_add"]) == R3_CAPS
            assert svc["cap_drop"] == ["ALL"]
            assert svc["read_only"] is True
            assert svc["security_opt"] == ["no-new-privileges:true"]
            assert "ports" not in svc and "expose" not in svc
            assert svc["restart"] == "unless-stopped"
            assert svc["logging"]["options"] == {"max-size": "10m", "max-file": "3"}
            assert svc.get("init") in (None, False)  # the guard itself is PID 1
            assert svc["pids_limit"] == 64
        else:
            assert "cap_add" not in svc, f"{name} gained capabilities"
    assert services["goldtier-egress"]["dns"] == ["172.30.241.4"]
    assert services["goldtier-dns"]["dns"] == ["172.30.241.4"]
    assert services["goldtier-dns"]["sysctls"] == {"net.ipv4.ip_unprivileged_port_start": "53"}
    assert services["goldtier-egress"]["environment"]["CLM_EGRESS_ROLE"] == "proxy"
    # R-1 pin: only the proxy carries the pinned set, and only from the required variable
    assert services["goldtier-egress"]["environment"]["CLM_EGRESS_DST_V4"] == "34.120.0.10"
    assert "CLM_EGRESS_DST_V4" not in services["goldtier-dns"]["environment"]
    assert not any("DST_V4" in k for k in services["backend"]["environment"])
    assert services["goldtier-dns"]["environment"]["CLM_EGRESS_ROLE"] == "resolver"
    assert services["goldtier-egress"]["container_name"] == "clm-staging-goldtier-egress"
    assert services["goldtier-dns"]["container_name"] == "clm-staging-goldtier-dns"


@pytest.mark.parametrize(
    "missing", ["CLM_GOLDTIER_EGRESS_FQDN", "CLM_GOLDTIER_EGRESS_DST_V4", "GOLDTIER_EGRESS_IMAGE"]
)
def test_c5_required_values_fail_closed(env: dict[str, str], missing: str) -> None:
    trimmed = {k: v for k, v in env.items() if k != missing}
    out = render(trimmed, *BASE, OVERLAY, expect_ok=False)
    assert missing in out["stderr"]


def test_c5_base_and_mongo_render_is_untouched_by_r3(env: dict[str, str]) -> None:
    r3_only = {"CLM_GOLDTIER_EGRESS_FQDN", "CLM_GOLDTIER_EGRESS_DST_V4"}
    base = render({k: v for k, v in env.items() if k not in r3_only}, *BASE)
    assert set(base["services"]) == {"backend", "frontend", "mongo"}
    assert set(base["networks"]) == {"proxy", "database", "default"}
    backend = base["services"]["backend"]
    assert set(backend["networks"]) == {"proxy", "database"}
    assert backend["environment"]["GOLDTIER_CONNECTOR_MODE"] == "mock"
    assert not any(k.startswith("GOLDTIER_SANDBOX_EGRESS") for k in backend["environment"])
    text = json.dumps(base)
    assert "goldtier-egress" not in text and "clm-gt-" not in text


# D-137 write window overlay (deploy/compose.goldtier-write-window.yml). Never part of dc, dca or
# dcg; applied only for an owner-authorised window, after the R3 overlay.
WINDOW = DEPLOY / "compose.goldtier-write-window.yml"
WINDOW_VALUES = {
    "CLM_GOLDTIER_WRITE_OPERATIONS": "SHELL",
    "CLM_GOLDTIER_WRITE_CASE_REFERENCES": "case-w1-synthetic",
    "CLM_GOLDTIER_WRITES_NOT_AFTER": "2099-01-01T00:00:00+00:00",
}
WINDOW_KEYS = {
    "GOLDTIER_SANDBOX_ALLOW_WRITES": "true",
    "GOLDTIER_SANDBOX_WRITE_OPERATIONS": "SHELL",
    "GOLDTIER_SANDBOX_WRITE_CASE_REFERENCES": "case-w1-synthetic",
    "GOLDTIER_SANDBOX_WRITES_NOT_AFTER": "2099-01-01T00:00:00+00:00",
}


def test_w1_window_changes_only_four_backend_values(env: dict[str, str]) -> None:
    closed = render(env | WINDOW_VALUES, *BASE, OVERLAY)
    opened = render(env | WINDOW_VALUES, *BASE, OVERLAY, WINDOW)
    assert opened["networks"] == closed["networks"]
    assert opened.get("volumes") == closed.get("volumes")
    assert set(opened["services"]) == set(closed["services"])
    for name, svc in opened["services"].items():
        if name != "backend":
            assert svc == closed["services"][name], name
    before, after = closed["services"]["backend"], opened["services"]["backend"]
    assert {k: v for k, v in after.items() if k != "environment"} == {
        k: v for k, v in before.items() if k != "environment"
    }
    changed = {
        k: v for k, v in after["environment"].items() if before["environment"].get(k) != v
    }
    assert changed == WINDOW_KEYS
    assert before["environment"]["GOLDTIER_SANDBOX_ALLOW_WRITES"] == "false"
    assert not any(k.startswith("GOLDTIER_SANDBOX_WRITE") for k in before["environment"]
                   if k != "GOLDTIER_SANDBOX_ALLOW_WRITES")


@pytest.mark.parametrize("missing", sorted(WINDOW_VALUES))
def test_w2_window_values_are_required(env: dict[str, str], missing: str) -> None:
    values = {k: v for k, v in WINDOW_VALUES.items() if k != missing}
    out = render(env | values, *BASE, OVERLAY, WINDOW, expect_ok=False)
    assert missing in out["stderr"]


def test_w3_window_overlay_is_in_no_standing_helper() -> None:
    runtime = (DEPLOY / "LIGHTSAIL_RUNTIME.md").read_text(encoding="utf-8")
    for helper in ("dc() {", "dca() {", "dcg() {"):
        start = runtime.index(helper)
        body = runtime[start : runtime.index("}", start)]
        assert "write-window" not in body, helper
    for name in ("compose.yml", "compose.mongo.yml", "compose.goldtier-egress.yml"):
        assert "write-window" not in (DEPLOY / name).read_text(encoding="utf-8")
