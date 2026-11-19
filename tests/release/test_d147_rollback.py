"""D-147 P1 remediation: rolling a backend back while standing GoldTier Sandbox writes are on.

A pre-D-147 backend refuses to start with Sandbox writes on and no D-137 window, so the
rollback must first make compose.env compatible (writes off, GoldTier mode kept, ACRA lease
closed) and must refuse, before the running backend is touched, when it cannot.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tools.release import deploy, records, render
from tools.release.core import Effect

from .fakes import OLD, FakeWorld, make_approval, make_context, make_manifest


@pytest.fixture(autouse=True)
def _offline_render(monkeypatch: pytest.MonkeyPatch) -> None:
    # As in test_deploy.py: the offline source render is covered by the render tests.
    monkeypatch.setattr(render, "validate_release_config", lambda gate, root, manifest: ["stub"])

STANDING = {
    "CLM_GOLDTIER_CONNECTOR_MODE": "sandbox",
    "CLM_GOLDTIER_SANDBOX_ALLOW_WRITES": "true",
    "CLM_GOLDTIER_SANDBOX_WRITE_SCOPE": "standing",
    "CLM_GOLDTIER_SANDBOX_WRITE_OPERATIONS": "SHELL,POLICY,AMEND",
}
ACTIVE = ("assistant", "goldtier")


def standing_world(services: list[str], **knobs: Any) -> tuple[dict[str, Any], FakeWorld]:
    manifest = make_manifest(services, automatic={s: True for s in services}, active=ACTIVE)
    world = FakeWorld(manifest, active=ACTIVE)
    world.env.update(STANDING)
    world.old_backend_pre_d147 = True
    for name, value in knobs.items():
        setattr(world, name, value)
    return manifest, world


def host_commands(world: FakeWorld) -> list[str]:
    return [c.argv[-1] for c in world.effects(Effect.HOST_WRITE)]


def switch_off_index(commands: list[str]) -> int:
    return next(
        i for i, c in enumerate(commands) if "CLM_GOLDTIER_SANDBOX_ALLOW_WRITES=false" in c
    )


def is_backend_stop(command: str) -> bool:
    return "docker compose" in command and " stop backend" in command


def backend_stop_index(commands: list[str]) -> int:
    return next(i for i, c in enumerate(commands) if is_backend_stop(c))


def failed_deploy(tmp_path: Path, **knobs: Any) -> tuple[dict[str, Any], FakeWorld, Any]:
    manifest, world = standing_world(["backend"], **knobs)
    world.smoke = {"/": "502"}  # the new release fails its smoke check -> automatic rollback
    ctx, world = make_context(manifest, tmp_path, world=world)
    return manifest, world, ctx


def test_automatic_backend_rollback_switches_writes_off_keeps_sandbox_and_restores(
    tmp_path: Path,
) -> None:
    _, world, ctx = failed_deploy(tmp_path)
    outcome = deploy.run(ctx)

    assert outcome["state"] == records.ROLLED_BACK
    assert world.env["CLM_GOLDTIER_SANDBOX_ALLOW_WRITES"] == "false"
    assert world.env["CLM_GOLDTIER_CONNECTOR_MODE"] == "sandbox"  # never reverted to Mock
    assert world.env["CLM_GOLDTIER_SANDBOX_WRITE_SCOPE"] == "standing"  # nothing else edited
    assert world.env["BACKEND_IMAGE"] == OLD["backend"]
    backend = world.containers["backend"]
    assert backend.running and backend.health == "healthy"
    assert backend.image == world.images[OLD["backend"]]
    commands = host_commands(world)
    # The switch goes off before the rollback stops the (new) backend.
    assert switch_off_index(commands) < max(i for i, c in enumerate(commands) if is_backend_stop(c))
    assert any("standing writes switched off" in e for e in outcome["events"])


def test_owner_requested_backend_rollback_does_the_same(tmp_path: Path) -> None:
    manifest, world = standing_world(["backend"])
    ctx, world = make_context(manifest, tmp_path, world=world)
    assert deploy.run(ctx)["state"] == records.DEPLOYED_AWAITING_ACCEPTANCE
    assert world.env["CLM_GOLDTIER_SANDBOX_ALLOW_WRITES"] == "true"  # normal deploy keeps it on

    ctx.approval = make_approval(manifest, actions=("rollback",), issued="103000")
    rolled = deploy.manual_rollback(ctx, manifest["release_id"])

    assert rolled["state"] == records.ROLLED_BACK
    assert world.env["CLM_GOLDTIER_SANDBOX_ALLOW_WRITES"] == "false"
    assert world.env["CLM_GOLDTIER_CONNECTOR_MODE"] == "sandbox"
    assert world.containers["backend"].image == world.images[OLD["backend"]]
    commands = host_commands(world)
    assert switch_off_index(commands) < backend_stop_index(commands[switch_off_index(commands):]) + \
        switch_off_index(commands)


@pytest.mark.parametrize(
    ("knobs", "reason"),
    [
        ({"acra_lease_open": True}, "the ACRA lease is open"),
        ({"acra_lease_open": None}, "lease state could not be confirmed"),
        ({"acra_lease_open": "denied"}, "lease state could not be confirmed"),
        ({"switch_edit_ignored": True}, "could not be switched off"),
    ],
    ids=["lease-open", "lease-unknown", "lease-permission-denied", "switch-not-written"],
)
def test_rollback_is_refused_before_the_backend_is_touched(
    tmp_path: Path, knobs: dict[str, Any], reason: str
) -> None:
    _, world, ctx = failed_deploy(tmp_path, **knobs)
    outcome = deploy.run(ctx)

    assert outcome["state"] == records.FAILED_HELD
    assert outcome["rollback"]["failure"]["code"] == "ROLLBACK_INCOMPATIBLE"
    assert reason in outcome["rollback"]["failure"]["message"]
    commands = host_commands(world)
    rollback_part = commands[next(
        i for i, c in enumerate(commands) if "cp -p /etc/clm/compose.env.pre-" in c
        and c.endswith("/etc/clm/compose.env")
    ):]
    assert not any(is_backend_stop(c) for c in rollback_part)
    assert world.containers["backend"].running  # the running backend was left in place
    assert world.env["CLM_GOLDTIER_CONNECTOR_MODE"] == "sandbox"
    if "lease" in reason:
        assert world.env["CLM_GOLDTIER_SANDBOX_ALLOW_WRITES"] == "true"  # nothing was changed


def test_an_unexpected_switch_value_is_refused(tmp_path: Path) -> None:
    _, world, ctx = failed_deploy(tmp_path)

    def odd_value_in_the_restored_file(command: Any) -> None:
        if "cp -p /etc/clm/compose.env.pre-" in command.argv[-1] and command.argv[-1].endswith(
            "/etc/clm/compose.env"
        ):
            for backup in world.backups_store.values():
                backup["CLM_GOLDTIER_SANDBOX_ALLOW_WRITES"] = "TRUE"

    world.on_command = odd_value_in_the_restored_file
    outcome = deploy.run(ctx)

    assert outcome["state"] == records.FAILED_HELD
    assert outcome["rollback"]["failure"]["code"] == "ROLLBACK_INCOMPATIBLE"
    assert "not a single plain setting" in outcome["rollback"]["failure"]["message"]
    assert world.env["CLM_GOLDTIER_SANDBOX_ALLOW_WRITES"] == "TRUE"
    assert world.containers["backend"].running


def test_writes_already_off_is_still_verified_but_not_edited(tmp_path: Path) -> None:
    _, world, ctx = failed_deploy(tmp_path)
    world.env["CLM_GOLDTIER_SANDBOX_ALLOW_WRITES"] = "false"
    outcome = deploy.run(ctx)

    assert outcome["state"] == records.ROLLED_BACK
    assert not any("CLM_GOLDTIER_SANDBOX_ALLOW_WRITES" in c for c in host_commands(world))
    assert any("compatibility verified" in e for e in outcome["events"])


def test_a_frontend_only_rollback_leaves_standing_writes_on(tmp_path: Path) -> None:
    manifest, world = standing_world(["frontend"])
    world.smoke = {"/": "502"}
    ctx, world = make_context(manifest, tmp_path, world=world)
    outcome = deploy.run(ctx)

    assert outcome["state"] == records.ROLLED_BACK
    assert world.env["CLM_GOLDTIER_SANDBOX_ALLOW_WRITES"] == "true"
    assert not any("CLM_GOLDTIER_SANDBOX_ALLOW_WRITES" in c for c in host_commands(world))


# -- R2: always verify (writes already off, retries) and strict settings, both routes ---------


def manual_after_deploy(tmp_path: Path, **knobs: Any) -> tuple[dict[str, Any], FakeWorld, Any]:
    manifest, world = standing_world(["backend"])
    ctx, world = make_context(manifest, tmp_path, world=world)
    assert deploy.run(ctx)["state"] == records.DEPLOYED_AWAITING_ACCEPTANCE
    for name, value in knobs.items():
        setattr(world, name, value)
    ctx.approval = make_approval(manifest, actions=("rollback",), issued="103000")
    return manifest, world, ctx


@pytest.mark.parametrize("lease", [True, None, "denied"], ids=["open", "unknown", "denied"])
def test_r2_writes_already_off_still_needs_a_confirmed_closed_lease_automatic(
    tmp_path: Path, lease: Any
) -> None:
    _, world, ctx = failed_deploy(tmp_path, acra_lease_open=lease)
    world.env["CLM_GOLDTIER_SANDBOX_ALLOW_WRITES"] = "false"
    outcome = deploy.run(ctx)

    assert outcome["state"] == records.FAILED_HELD
    assert outcome["rollback"]["failure"]["code"] == "ROLLBACK_INCOMPATIBLE"
    assert world.containers["backend"].running
    assert world.containers["backend"].image != world.images[OLD["backend"]]


@pytest.mark.parametrize("lease", [True, None, "denied"], ids=["open", "unknown", "denied"])
def test_r2_writes_already_off_still_needs_a_confirmed_closed_lease_manual(
    tmp_path: Path, lease: Any
) -> None:
    manifest, world, ctx = manual_after_deploy(tmp_path, acra_lease_open=lease)
    world.env["CLM_GOLDTIER_SANDBOX_ALLOW_WRITES"] = "false"
    rolled = deploy.manual_rollback(ctx, manifest["release_id"])

    assert rolled["state"] != records.ROLLED_BACK
    assert rolled["rollback"]["failure"]["code"] == "ROLLBACK_INCOMPATIBLE"
    assert world.containers["backend"].running
    assert world.containers["backend"].image != world.images[OLD["backend"]]


@pytest.mark.parametrize(
    ("variable", "extra"),
    [
        ("CLM_GOLDTIER_SANDBOX_ALLOW_WRITES", ["CLM_GOLDTIER_SANDBOX_ALLOW_WRITES=false"]),
        ("CLM_GOLDTIER_SANDBOX_ALLOW_WRITES", ["export CLM_GOLDTIER_SANDBOX_ALLOW_WRITES=true"]),
        ("CLM_GOLDTIER_CONNECTOR_MODE", ["CLM_GOLDTIER_CONNECTOR_MODE=mock"]),
    ],
    ids=["duplicate-switch", "export-duplicate", "duplicate-mode"],
)
@pytest.mark.parametrize("route", ["automatic", "manual"])
def test_r2_duplicate_or_ambiguous_settings_are_refused(
    tmp_path: Path, route: str, variable: str, extra: list[str]
) -> None:
    if route == "automatic":
        _, world, ctx = failed_deploy(tmp_path)
        world.extra_setting_lines = {variable: extra}
        outcome = deploy.run(ctx)
    else:
        manifest, world, ctx = manual_after_deploy(tmp_path, extra_setting_lines={variable: extra})
        outcome = deploy.manual_rollback(ctx, manifest["release_id"])
    assert outcome["rollback"]["failure"]["code"] == "ROLLBACK_INCOMPATIBLE"
    assert "set more than once" in outcome["rollback"]["failure"]["message"]
    assert world.containers["backend"].running
    assert world.env["CLM_GOLDTIER_CONNECTOR_MODE"] == "sandbox"


@pytest.mark.parametrize("route", ["automatic", "manual"])
def test_r2_unreadable_settings_are_refused(tmp_path: Path, route: str) -> None:
    if route == "automatic":
        _, world, ctx = failed_deploy(tmp_path, settings_unreadable=True)
        outcome = deploy.run(ctx)
    else:
        manifest, world, ctx = manual_after_deploy(tmp_path, settings_unreadable=True)
        outcome = deploy.manual_rollback(ctx, manifest["release_id"])
    assert outcome["rollback"]["failure"]["code"] == "ROLLBACK_INCOMPATIBLE"
    assert "could not be read" in outcome["rollback"]["failure"]["message"]
    assert world.containers["backend"].running


def test_r2_a_spaced_setting_is_refused(tmp_path: Path) -> None:
    _, world, ctx = failed_deploy(tmp_path)

    def spaced_line_in_the_restored_file(command: Any) -> None:
        if "cp -p /etc/clm/compose.env.pre-" in command.argv[-1] and command.argv[-1].endswith(
            "/etc/clm/compose.env"
        ):
            for backup in world.backups_store.values():
                backup.pop("CLM_GOLDTIER_SANDBOX_ALLOW_WRITES", None)
            world.extra_setting_lines = {
                "CLM_GOLDTIER_SANDBOX_ALLOW_WRITES": ["CLM_GOLDTIER_SANDBOX_ALLOW_WRITES = true"]
            }

    world.on_command = spaced_line_in_the_restored_file
    outcome = deploy.run(ctx)
    assert outcome["rollback"]["failure"]["code"] == "ROLLBACK_INCOMPATIBLE"
    assert "not a single plain setting" in outcome["rollback"]["failure"]["message"]
    assert world.containers["backend"].running


def test_r2_missing_mode_line_on_the_goldtier_wrapper_is_refused(tmp_path: Path) -> None:
    _, world, ctx = failed_deploy(tmp_path)

    def drop_mode_from_the_restored_file(command: Any) -> None:
        if "cp -p /etc/clm/compose.env.pre-" in command.argv[-1] and command.argv[-1].endswith(
            "/etc/clm/compose.env"
        ):
            for backup in world.backups_store.values():
                backup.pop("CLM_GOLDTIER_CONNECTOR_MODE", None)

    world.on_command = drop_mode_from_the_restored_file
    outcome = deploy.run(ctx)
    assert outcome["rollback"]["failure"]["code"] == "ROLLBACK_INCOMPATIBLE"
    assert "CLM_GOLDTIER_CONNECTOR_MODE is not set" in outcome["rollback"]["failure"]["message"]
    assert world.containers["backend"].running


def test_r2_a_retry_after_a_partial_rollback_is_verified_again(tmp_path: Path) -> None:
    manifest, world, ctx = failed_deploy(tmp_path)

    def backend_fails_once(command: Any) -> None:
        if "cp -p /etc/clm/compose.env.pre-" in command.argv[-1] and command.argv[-1].endswith(
            "/etc/clm/compose.env"
        ):
            world.up_fails = {"backend"}

    world.on_command = backend_fails_once
    first = deploy.run(ctx)
    assert first["state"] == records.FAILED_HELD
    assert world.env["CLM_GOLDTIER_SANDBOX_ALLOW_WRITES"] == "false"  # switched off, then failed
    world.on_command, world.up_fails = None, set()
    world.smoke.clear()

    world.acra_lease_open = True  # the lease was reopened in between: the retry must refuse
    ctx.approval = make_approval(manifest, actions=("rollback",), issued="111000")
    second = deploy.manual_rollback(ctx, manifest["release_id"])
    assert second["rollback"]["failure"]["code"] == "ROLLBACK_INCOMPATIBLE"
    assert "lease is open" in second["rollback"]["failure"]["message"]

    world.acra_lease_open = False
    ctx.approval = make_approval(manifest, actions=("rollback",), issued="112000")
    third = deploy.manual_rollback(ctx, manifest["release_id"])
    assert third["state"] == records.ROLLED_BACK
    assert any("compatibility verified" in e for e in third["events"])
    assert world.env["CLM_GOLDTIER_CONNECTOR_MODE"] == "sandbox"
    assert world.containers["backend"].image == world.images[OLD["backend"]]


# -- R3: the GoldTier mode must be one the backend Settings support ---------------------------


def test_r3_supported_modes_equal_the_backend_settings_literal() -> None:
    import ast

    from .fakes import REPO

    tree = ast.parse((REPO / "apps/backend/app/config.py").read_text(encoding="utf-8"))
    field = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "goldtier_connector_mode"
    )
    assert isinstance(field.annotation, ast.Subscript)
    literal = field.annotation.slice
    values = literal.elts if isinstance(literal, ast.Tuple) else [literal]
    assert {ast.literal_eval(v) for v in values} == deploy.SUPPORTED_GOLDTIER_MODES


def set_mode_on_restore(world: FakeWorld, mode: str, writes: str) -> None:
    def hook(command: Any) -> None:
        if "cp -p /etc/clm/compose.env.pre-" in command.argv[-1] and command.argv[-1].endswith(
            "/etc/clm/compose.env"
        ):
            for backup in world.backups_store.values():
                backup["CLM_GOLDTIER_CONNECTOR_MODE"] = mode
                backup["CLM_GOLDTIER_SANDBOX_ALLOW_WRITES"] = writes

    world.on_command = hook


@pytest.mark.parametrize("writes", ["true", "false"], ids=["writes-on", "writes-already-off"])
@pytest.mark.parametrize("mode", ["live", "production", "Sandbox"])
def test_r3_unsupported_matching_mode_is_refused_automatic(
    tmp_path: Path, writes: str, mode: str
) -> None:
    _, world, ctx = failed_deploy(tmp_path)
    set_mode_on_restore(world, mode, writes)
    outcome = deploy.run(ctx)

    assert outcome["state"] == records.FAILED_HELD
    assert outcome["rollback"]["failure"]["code"] == "ROLLBACK_INCOMPATIBLE"
    assert any(  # "Sandbox" is already refused by the strict plain-setting read
        reason in outcome["rollback"]["failure"]["message"]
        for reason in ("not a mode the backend supports", "not a single plain setting")
    )
    assert world.env["CLM_GOLDTIER_SANDBOX_ALLOW_WRITES"] == writes  # nothing was edited
    assert world.containers["backend"].running
    assert world.containers["backend"].image != world.images[OLD["backend"]]


@pytest.mark.parametrize("writes", ["true", "false"], ids=["writes-on", "writes-already-off"])
@pytest.mark.parametrize("mode", ["live", "production", "Sandbox"])
def test_r3_unsupported_matching_mode_is_refused_manual(
    tmp_path: Path, writes: str, mode: str
) -> None:
    manifest, world, ctx = manual_after_deploy(tmp_path)
    world.env["CLM_GOLDTIER_CONNECTOR_MODE"] = mode
    world.env["CLM_GOLDTIER_SANDBOX_ALLOW_WRITES"] = writes
    rolled = deploy.manual_rollback(ctx, manifest["release_id"])

    assert rolled["state"] != records.ROLLED_BACK
    assert rolled["rollback"]["failure"]["code"] == "ROLLBACK_INCOMPATIBLE"
    assert any(  # "Sandbox" is already refused by the strict plain-setting read
        reason in rolled["rollback"]["failure"]["message"]
        for reason in ("not a mode the backend supports", "not a single plain setting")
    )
    assert world.env["CLM_GOLDTIER_SANDBOX_ALLOW_WRITES"] == writes
    assert world.containers["backend"].running
    assert world.containers["backend"].image != world.images[OLD["backend"]]


def test_r3_an_unsupported_rendered_mode_is_refused_on_the_base_wrapper(tmp_path: Path) -> None:
    manifest = make_manifest(["backend"], automatic={"backend": True})  # no R3 overlay
    world = FakeWorld(manifest)
    world.smoke = {"/": "502"}
    original = world._summary

    def odd_render(text: str) -> dict[str, Any]:
        summary = original(text)
        summary["services"]["backend"]["safe_values"]["GOLDTIER_CONNECTOR_MODE"] = "live"
        return summary

    world._summary = odd_render  # type: ignore[method-assign]
    ctx, world = make_context(manifest, tmp_path, world=world)
    outcome = deploy.run(ctx)

    assert outcome["rollback"]["failure"]["code"] == "ROLLBACK_INCOMPATIBLE"
    assert "rendered GoldTier mode is not one the backend supports" in (
        outcome["rollback"]["failure"]["message"]
    )
    assert world.containers["backend"].running


@pytest.mark.parametrize("writes", ["true", "false"], ids=["writes-on", "writes-already-off"])
def test_r3_supported_sandbox_mode_still_rolls_back_and_stays_sandbox(
    tmp_path: Path, writes: str
) -> None:
    _, world, ctx = failed_deploy(tmp_path)
    set_mode_on_restore(world, "sandbox", writes)
    outcome = deploy.run(ctx)

    assert outcome["state"] == records.ROLLED_BACK
    assert world.env["CLM_GOLDTIER_CONNECTOR_MODE"] == "sandbox"
    assert world.env["CLM_GOLDTIER_SANDBOX_ALLOW_WRITES"] == "false"
