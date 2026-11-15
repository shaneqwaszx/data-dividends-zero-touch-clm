"""D4 (D-086a) repository-side ACRA ownership overlay contract.

`deploy/compose.acra-ownership.yml` only sets the two synthetic-ownership variables on the
backend. It is applied by the operator after the host-installed Marketplace overlay and is
never part of the Mock baseline file set. Static checks need only PyYAML; the render checks
use `docker compose config` offline (no daemon, network or image pull) with placeholder
values, and are skipped when the Docker CLI with Compose is unavailable.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "deploy"
OVERLAY = DEPLOY / "compose.acra-ownership.yml"
BASE = (DEPLOY / "compose.yml", DEPLOY / "compose.mongo.yml")
EXPECTED = {
    "ACRA_MARKETPLACE_OWNERSHIP_OVERLAY": "hybrid_direct_overlay",
    "ACRA_MARKETPLACE_OPQ_SCENARIO": "${CLM_ACRA_OPQ_SCENARIO:-garden_sim_lim_chain}",
}
# Never let the developer's own environment leak into an interpolated value.
INTERPOLATED_PREFIXES = (
    "BACKEND_",
    "FRONTEND_",
    "ASSISTANT_",
    "GOLDTIER_",
    "CLM_",
    "MONGO_",
    "ACRA_",
    "HTTP_BIND",
    "HTTPS_BIND",
    "COMPOSE_",
)


def _load(path: Path) -> dict:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_the_overlay_parses_and_sets_only_the_two_backend_variables() -> None:
    overlay = _load(OVERLAY)
    assert set(overlay) == {"services"}
    assert set(overlay["services"]) == {"backend"}
    backend = overlay["services"]["backend"]
    # No networks, images, ports, volumes, env_file or other keys.
    assert set(backend) == {"environment"}
    assert backend["environment"] == EXPECTED


def test_the_mock_baseline_never_enables_the_ownership_overlay() -> None:
    for path in BASE:
        text = path.read_text(encoding="utf-8")
        assert "ACRA_MARKETPLACE_OWNERSHIP_OVERLAY" not in text
        assert "ACRA_MARKETPLACE_OPQ_SCENARIO" not in text


def test_the_overlay_carries_no_secret_host_or_address() -> None:
    text = OVERLAY.read_text(encoding="utf-8")
    for forbidden in ("://", "SECRET", "PASSWORD", "TOKEN", "KEY", "MONGO_URI"):
        assert forbidden not in text.upper()


# --- Offline render (Docker CLI with Compose only) --------------------------------------

docker = pytest.mark.skipif(
    shutil.which("docker") is None, reason="Docker CLI with Compose not available"
)


@pytest.fixture()
def env(tmp_path: Path) -> dict[str, str]:
    for name in ("backend.env", "mongo-ca.pem", "mongo-server.pem", "empty.env"):
        (tmp_path / name).write_text("", encoding="ascii")
    inherited = {
        k: v for k, v in os.environ.items() if not k.upper().startswith(INTERPOLATED_PREFIXES)
    }
    return inherited | {
        "D086A_TEST_EMPTY_ENV_FILE": str(tmp_path / "empty.env"),
        "BACKEND_IMAGE": "example.invalid/backend@sha256:" + "0" * 64,
        "FRONTEND_IMAGE": "example.invalid/frontend@sha256:" + "1" * 64,
        "BACKEND_ENV_FILE": str(tmp_path / "backend.env"),
        "CLM_SITE": "clm.example.invalid",
        "MONGO_URI": "mongodb://placeholder.invalid/?tls=true",
        "MONGO_CA_FILE": str(tmp_path / "mongo-ca.pem"),
        "MONGO_SERVER_PEM": str(tmp_path / "mongo-server.pem"),
        "MONGO_DATA_VOLUME": "clm-d086a-test-mongo",
    }


def _compose(env: dict[str, str], *files: Path) -> list[str]:
    # --env-file points at an empty file so no project .env is ever read.
    args = [
        "docker",
        "compose",
        "--env-file",
        env["D086A_TEST_EMPTY_ENV_FILE"],
        "--project-name",
        "clm-staging",
    ]
    for path in files:
        args += ["-f", str(path)]
    return args


def _run(env: dict[str, str], args: list[str]) -> str:
    result = subprocess.run(
        args, capture_output=True, text=True, env=env, cwd=ROOT, timeout=60, check=False
    )
    if result.returncode != 0 and "is not a docker command" in result.stderr:
        pytest.skip("Docker Compose plugin not available")
    assert result.returncode == 0, result.stderr
    return result.stdout


def _render(env: dict[str, str], *files: Path) -> dict:
    out = _run(env, _compose(env, *files) + ["config", "--format", "json", "--no-path-resolution"])
    rendered = json.loads(out)
    assert isinstance(rendered, dict)
    return rendered


def _backend_hash(env: dict[str, str], *files: Path) -> str:
    return _run(env, _compose(env, *files) + ["config", "--hash", "backend"]).strip()


@docker
def test_the_baseline_backend_render_is_unchanged_by_the_new_file(env: dict[str, str]) -> None:
    before = _backend_hash(env, *BASE)
    base = _render(env, *BASE)
    environment = base["services"]["backend"].get("environment", {})
    assert not set(EXPECTED) & set(environment)
    # The new file is opt-in: the baseline file set never picks it up.
    assert _backend_hash(env, *BASE) == before
    with_overlay = _render(env, *BASE, OVERLAY)
    assert _backend_hash(env, *BASE, OVERLAY) != before
    # Only the two variables differ; every other backend key is identical.
    merged = with_overlay["services"]["backend"]
    stripped = {
        **merged,
        "environment": {k: v for k, v in merged["environment"].items() if k not in EXPECTED},
    }
    assert stripped == base["services"]["backend"]
    assert set(with_overlay["services"]) == set(base["services"])


@docker
@pytest.mark.parametrize(
    ("selected", "expected"),
    [(None, "garden_sim_lim_chain"), ("five_layer_simulation", "five_layer_simulation")],
)
def test_the_render_carries_both_variables_and_the_default(
    env: dict[str, str], selected: str | None, expected: str
) -> None:
    if selected is not None:
        env = env | {"CLM_ACRA_OPQ_SCENARIO": selected}
    environment = _render(env, *BASE, OVERLAY)["services"]["backend"]["environment"]
    assert environment["ACRA_MARKETPLACE_OWNERSHIP_OVERLAY"] == "hybrid_direct_overlay"
    assert environment["ACRA_MARKETPLACE_OPQ_SCENARIO"] == expected
