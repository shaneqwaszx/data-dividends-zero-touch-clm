"""Regression tests for the independent review of 2026-11-14 (findings F1 to F18).

Each test fails on the reviewed candidate (commit 728cf1e) or kills a safeguard-removal mutant
the review found surviving. They run against the same mock host as the rest of the suite.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from tools.release import catalog, cli, controller, deploy, records, render
from tools.release import manifest as manifests
from tools.release.core import (
    AuditLog,
    Command,
    Effect,
    Gate,
    Mode,
    ReleaseError,
    Result,
    StopCondition,
    assert_remote_allowed,
)
from tools.release.effective_summary import summarise
from tools.release.host import Host, SshTarget

from .fakes import OLD, SAMPLE, FakeWorld, make_approval, make_context, make_manifest
from .test_registry_creds_controller import prepared  # noqa: F401  (fixture)


@pytest.fixture(autouse=True)
def offline_render(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(render, "validate_release_config", lambda gate, root, manifest: ["stub"])


def serving(world: FakeWorld) -> bool:
    return all(c.running and c.health == "healthy" for c in world.containers.values())


# -- F1: a rollback that touches backend and frontend must leave the site serving -------------


def test_f1_automatic_rollback_of_backend_and_frontend_leaves_ingress_running(
    tmp_path: Path,
) -> None:
    manifest = make_manifest(["backend", "frontend"], automatic={"backend": True})
    world = FakeWorld(manifest)
    world.smoke = {"/": "502"}
    ctx, world = make_context(manifest, tmp_path, world=world)
    outcome = deploy.run(ctx)
    assert outcome["state"] == records.ROLLED_BACK and outcome["stop_code"] == "SMOKE_FAILED"
    assert world.containers["frontend"].running, "ingress must be serving after a rollback"
    assert serving(world)
    assert world.env["BACKEND_IMAGE"] == OLD["backend"]
    assert world.env["FRONTEND_IMAGE"] == OLD["frontend"]
    for name in ("backend", "frontend"):
        assert world.containers[name].image == world.images[OLD[name]]
    verbs = [
        tuple(c.argv[-1].split()[-3:-1])
        for c in world.effects(Effect.HOST_WRITE)
        if "docker compose" in c.argv[-1]
    ]
    rollback_part = verbs[verbs.index(("180", "frontend")) + 1 :]
    assert [v[1] for v in rollback_part] == ["frontend", "backend", "backend", "frontend"]
    assert rollback_part[0][0] == "frontend" or rollback_part[0] == ("stop", "frontend")
    assert "rollback verified" in outcome["events"][-1]


def test_f1_owner_requested_rollback_of_backend_and_frontend_leaves_ingress_running(
    tmp_path: Path,
) -> None:
    manifest = make_manifest(["backend", "frontend"], automatic={"backend": True})
    ctx, world = make_context(manifest, tmp_path)
    assert deploy.run(ctx)["state"] == records.DEPLOYED_AWAITING_ACCEPTANCE
    ctx.approval = make_approval(manifest, actions=("rollback",), issued="103000")
    rolled = deploy.manual_rollback(ctx, manifest["release_id"])
    assert rolled["state"] == records.ROLLED_BACK and serving(world)
    assert world.env["BACKEND_IMAGE"] == OLD["backend"]


def test_f1_rollback_checks_every_step_and_never_reports_success_with_a_service_down(
    tmp_path: Path,
) -> None:
    manifest = make_manifest(["backend"], automatic={"backend": True})
    world = FakeWorld(manifest)
    world.unhealthy_after_up = {"backend"}
    ctx, world = make_context(manifest, tmp_path, world=world)

    def fail_ingress_stop_during_rollback(command: Any) -> None:
        if "cp -p /etc/clm/compose.env.pre-" in command.argv[-1]:
            world.stop_fails = {"frontend"}

    world.on_command = fail_ingress_stop_during_rollback
    outcome = deploy.run(ctx)
    assert outcome["state"] == records.FAILED_HELD
    assert "ROLLBACK_FAILED" in outcome["held_reason"]


def test_m38_rollback_onto_the_wrong_image_is_not_reported_as_rolled_back(tmp_path: Path) -> None:
    manifest = make_manifest(["frontend"])
    world = FakeWorld(manifest)
    world.smoke = {"/": "502"}
    world.rollback_runs_wrong_image = True
    outcome, world = deploy.run(make_context(manifest, tmp_path, world=world)[0]), world
    assert outcome["state"] == records.FAILED_HELD
    assert "ROLLBACK_FAILED" in outcome["held_reason"]


# -- F2: expiry between the pin and the first container change --------------------------------


def test_f2_expiry_after_the_pin_restores_compose_env_and_records_the_result(
    tmp_path: Path,
) -> None:
    manifest = make_manifest(["frontend"])
    ctx, world = make_context(manifest, tmp_path)

    def expire_at_the_pin(command: Any) -> None:
        if " sed -i " in command.argv[-1]:
            world.clock.advance(hours=3)

    world.on_command = expire_at_the_pin
    outcome = deploy.run(ctx)
    assert outcome["stop_code"] == "APPROVAL_EXPIRED"
    assert outcome["state"] == records.FAILED_NO_CHANGE
    assert world.env["FRONTEND_IMAGE"] == OLD["frontend"], "compose.env is back on the old pin"
    assert world.recreated() == []
    assert not [c for c in world.effects(Effect.HOST_WRITE) if " up " in c.argv[-1]]
    assert ctx.store.read_result(manifest["release_id"])["state"] == records.FAILED_NO_CHANGE
    assert world.host_lock is False


def test_f2_a_stop_while_handling_a_stop_is_still_recorded(tmp_path: Path) -> None:
    manifest = make_manifest(["frontend"])
    world = FakeWorld(manifest)
    world.restore_fails = True
    ctx, world = make_context(manifest, tmp_path, world=world)
    original = world._hash
    world._hash = lambda name: (  # type: ignore[method-assign]
        "surprise"
        if name == "backend" and world.env["FRONTEND_IMAGE"] != OLD["frontend"]
        else original(name)
    )
    outcome = deploy.run(ctx)
    assert outcome["state"] == records.FAILED_HELD
    assert "compose.env could not be restored" in outcome["held_reason"]
    assert "cp -p" in outcome["manual_next_step"]
    assert ctx.store.read_result(manifest["release_id"]) is not None


# -- F8: an interrupted run always leaves a record --------------------------------------------


@pytest.mark.parametrize("crash", [KeyboardInterrupt, RuntimeError])
def test_f8_interrupted_run_writes_a_held_record_and_can_be_rolled_back(
    tmp_path: Path, crash: type[BaseException]
) -> None:
    manifest = make_manifest(["frontend"])
    ctx, world = make_context(manifest, tmp_path)

    def interrupt_after_up(command: Any) -> None:
        if command.effect is Effect.HOST_READ and world.recreated():
            raise crash()

    world.on_command = interrupt_after_up
    with pytest.raises(crash):
        deploy.run(ctx)
    record = ctx.store.read_result(manifest["release_id"])
    assert record["state"] == records.FAILED_HELD and record["stop_code"] == "INTERRUPTED"
    assert record["applied"] == ["frontend"] and record["env_backup"]
    assert "interrupted" in record["held_reason"]
    assert world.host_lock is False and not (ctx.store.root / "release.lock").exists()
    world.on_command = None
    ctx.approval = make_approval(manifest, actions=("rollback",), issued="104000")
    assert deploy.manual_rollback(ctx, manifest["release_id"])["state"] == records.ROLLED_BACK
    assert world.env["FRONTEND_IMAGE"] == OLD["frontend"] and serving(world)


def test_f8_interrupt_before_any_host_change_is_recorded_as_no_change(tmp_path: Path) -> None:
    manifest = make_manifest(["frontend"])
    ctx, world = make_context(manifest, tmp_path)

    def interrupt_in_preflight(command: Any) -> None:
        if "MemAvailable" in command.argv[-1]:
            raise KeyboardInterrupt()

    world.on_command = interrupt_in_preflight
    with pytest.raises(KeyboardInterrupt):
        deploy.run(ctx)
    assert ctx.store.read_result(manifest["release_id"])["state"] == records.FAILED_NO_CHANGE


# -- F6 / F7: owner-requested rollback ------------------------------------------------------


def test_f6_manual_rollback_changes_only_its_own_line_and_keeps_later_edits(
    tmp_path: Path,
) -> None:
    manifest = make_manifest(["frontend"])
    ctx, world = make_context(manifest, tmp_path)
    deploy.run(ctx)
    world.env["ASSISTANT_ELIGIBLE_CASE_REFS"] = "aaaaaaaaaaaa"  # a later, unrelated edit
    ctx.approval = make_approval(manifest, actions=("rollback",), issued="105000")
    assert deploy.manual_rollback(ctx, manifest["release_id"])["state"] == records.ROLLED_BACK
    assert world.env["ASSISTANT_ELIGIBLE_CASE_REFS"] == "aaaaaaaaaaaa"
    assert world.env["FRONTEND_IMAGE"] == OLD["frontend"]
    assert not [c for c in world.received if "cp -p /etc/clm/compose.env.pre-" in c.argv[-1]]


def test_f6_manual_rollback_refuses_when_the_host_has_moved_on(tmp_path: Path) -> None:
    manifest = make_manifest(["frontend"])
    ctx, world = make_context(manifest, tmp_path)
    deploy.run(ctx)
    later = OLD["frontend"][:-4] + "beef"
    world.env["FRONTEND_IMAGE"] = later  # another release pinned the frontend afterwards
    world.containers["frontend"].label_hash = world._hash("frontend")
    writes = len(world.effects(Effect.HOST_WRITE))
    ctx.approval = make_approval(manifest, actions=("rollback",), issued="105100")
    with pytest.raises(StopCondition) as refused:
        deploy.manual_rollback(ctx, manifest["release_id"])
    assert refused.value.code == "HOST_STATE_UNEXPECTED"
    assert world.env["FRONTEND_IMAGE"] == later
    assert len(world.effects(Effect.HOST_WRITE)) == writes, "nothing was written"
    assert ctx.store.read_result(manifest["release_id"])["state"] == (
        records.DEPLOYED_AWAITING_ACCEPTANCE
    )
    assert f"{ctx.approval['approval_id']}:rollback" not in ctx.store.consumed_approvals()


def test_f7_rollback_needs_its_own_single_use_approval_and_takes_the_host_lock(
    tmp_path: Path,
) -> None:
    manifest = make_manifest(["frontend"])
    ctx, world = make_context(manifest, tmp_path)
    deploy.run(ctx)
    world.host_lock = True
    ctx.approval = make_approval(manifest, actions=("rollback",), issued="105200")
    with pytest.raises(StopCondition) as busy:
        deploy.manual_rollback(ctx, manifest["release_id"])
    assert (
        busy.value.code == "RELEASE_IN_PROGRESS" and world.env["FRONTEND_IMAGE"] != OLD["frontend"]
    )
    world.host_lock = False
    assert deploy.manual_rollback(ctx, manifest["release_id"])["state"] == records.ROLLED_BACK
    assert f"{ctx.approval['approval_id']}:rollback" in ctx.store.consumed_approvals()


# -- F5: schema-19 and "compatible" claims ----------------------------------------------------


@pytest.mark.parametrize("commit", [None, "", "4C1DB49", " 4c1db49", "4c1db49", "main", "xyz1234"])
def test_f5_compatible_backend_target_needs_a_well_formed_commit_that_is_not_schema_19(
    commit: str | None,
) -> None:
    manifest = make_manifest(["backend"], automatic={"backend": True})
    manifest["rollback"]["backend"]["target_source_commit"] = commit
    with pytest.raises(ReleaseError) as refused:
        manifests.validate_manifest(manifest)
    assert refused.value.code in {
        "ROLLBACK_NOT_PROVEN",
        "ROLLBACK_SCHEMA_INCOMPATIBLE",
        "MANIFEST_INVALID",
    }


# -- F3 / F4: what the effective-configuration summary can see --------------------------------


def document(volumes: list[dict[str, Any]], **service: Any) -> dict[str, Any]:
    body = {"image": "x", "volumes": volumes, "networks": {"proxy": None}, **service}
    return {"name": "clm-staging", "services": {"backend": body}}


def test_f3_docker_socket_is_seen_whatever_target_it_is_mounted_on() -> None:
    hidden = document(
        [
            {
                "type": "bind",
                "source": "/var/run/docker.sock",
                "target": "/run/clm/mongo-ca.pem",
                "read_only": True,
            }
        ]
    )
    summary = render.normalise(summarise(hidden), "/scratch")
    assert any("docker" in v for v in summary["services"]["backend"]["volumes"])
    full = copy.deepcopy(render.load_baseline()["base"])
    full["services"]["backend"]["volumes"] = summary["services"]["backend"]["volumes"]
    full["services"]["backend"]["bind_sources"] = summary["services"]["backend"]["bind_sources"]
    declared = {"backend": {"settings": ["volumes", "bind_sources"]}}
    with pytest.raises(StopCondition) as refused:
        render.check_summary("base", full, declared)
    assert (
        refused.value.code == "EFFECTIVE_CONFIG_INVARIANT"
        and "Docker socket" in refused.value.message
    )


def test_f3_literal_bind_source_differs_from_the_interpolated_baseline() -> None:
    literal = document(
        [
            {
                "type": "bind",
                "source": "/etc/shadow",
                "target": "/run/clm/mongo-ca.pem",
                "read_only": True,
            }
        ]
    )
    interpolated = document(
        [
            {
                "type": "bind",
                "source": "/scratch/mongo-ca.pem",
                "target": "/run/clm/mongo-ca.pem",
                "read_only": True,
            }
        ]
    )
    a = render.normalise(summarise(literal), "/scratch")["services"]["backend"]["bind_sources"]
    b = render.normalise(summarise(interpolated), "/scratch")["services"]["backend"]["bind_sources"]
    assert a == ["literal:/etc/shadow"] and b == ["interpolated"]
    changed = copy.deepcopy(render.load_baseline()["base"])
    changed["services"]["backend"]["bind_sources"] = a
    with pytest.raises(StopCondition) as refused:
        render.check_summary("base", changed, {})
    assert "bind_sources" in refused.value.message


@pytest.mark.parametrize(
    ("setting", "value"),
    [
        ("cap_add", ["ALL"]),
        ("cap_add", ["NET_ADMIN"]),
        ("security_opt", ["no-new-privileges:true", "seccomp=unconfined"]),
        ("volumes_from", ["mongo"]),
    ],
)
def test_f4_capabilities_and_security_options_cannot_be_declared_away(
    setting: str, value: list[str]
) -> None:
    summary = copy.deepcopy(render.load_baseline()["base"])
    summary["services"]["backend"]["settings"][setting] = value
    with pytest.raises(StopCondition) as refused:
        render.check_summary("base", summary, {"backend": {"settings": [setting]}})
    assert refused.value.code == "EFFECTIVE_CONFIG_INVARIANT"


@pytest.mark.parametrize(
    "change",
    [
        {"command": ["mongod", "--noauth"]},
        {"entrypoint": ["sh", "-c", "sleep 1"]},
        {"healthcheck": {"test": ["CMD", "true"]}},
        {"tmpfs": ["/tmp:exec"]},
        {"mem_limit": "4g"},
    ],
)
def test_f4_command_entrypoint_healthcheck_and_tmpfs_changes_are_visible(change: dict) -> None:
    before = summarise(document([]))
    after = summarise(document([], **change))
    assert before != after
    reordered = summarise(document([], command=["b", "a"])) != summarise(
        document([], command=["a", "b"])
    )
    assert reordered, "argument order is kept"


def test_f4_goldtier_guard_keeps_exactly_its_reviewed_capabilities() -> None:
    summary = copy.deepcopy(render.load_baseline()["goldtier"])
    assert summary["services"]["goldtier-egress"]["settings"]["cap_add"] == render.R3_CAPS
    summary["services"]["goldtier-egress"]["settings"]["cap_add"] = [*render.R3_CAPS, "SYS_ADMIN"]
    with pytest.raises(StopCondition):
        render.check_summary("goldtier", summary, {"goldtier-egress": {"settings": ["cap_add"]}})


# -- F10: mutants the review found surviving --------------------------------------------------


def test_m33_host_render_with_an_undeclared_network_inside_the_ceiling_is_refused(
    tmp_path: Path,
) -> None:
    manifest = make_manifest(["backend"])
    world = FakeWorld(manifest)
    world.host_summary_extra_network = "goldtier-control"  # allowed by the ceiling, not declared
    ctx, world = make_context(manifest, tmp_path, world=world)
    outcome = deploy.run(ctx)
    assert outcome["stop_code"] == "EFFECTIVE_CONFIG_UNDECLARED"
    assert "undeclared networks entry goldtier-control" in outcome["stop_message"]
    assert outcome["state"] == records.FAILED_NO_CHANGE and world.recreated() == []
    assert world.env["BACKEND_IMAGE"] == OLD["backend"]


def test_m29_compose_env_must_differ_by_exactly_one_line_per_service(tmp_path: Path) -> None:
    manifest = make_manifest(["frontend"])
    world = FakeWorld(manifest)
    world.diff_lines = 4
    outcome = deploy.run(make_context(manifest, tmp_path, world=world)[0])
    assert (
        outcome["stop_code"] == "ENV_EDIT_UNEXPECTED"
        and outcome["state"] == records.FAILED_NO_CHANGE
    )
    assert world.env["FRONTEND_IMAGE"] == OLD["frontend"] and world.recreated() == []


@pytest.mark.parametrize(
    ("knob", "value", "check"),
    [
        ("clock_skew", 900, "clock"),
        ("compose_version", "2.20.3", "compose"),
        ("proxy_internal", False, "network-boundaries"),
    ],
)
def test_m39_m47_m48_clock_compose_version_and_proxy_network_preflight(
    tmp_path: Path, knob: str, value: Any, check: str
) -> None:
    manifest = make_manifest(["frontend"])
    world = FakeWorld(manifest)
    setattr(world, knob, value)
    outcome = deploy.run(make_context(manifest, tmp_path, world=world)[0])
    assert outcome["stop_code"] == "PREFLIGHT_FAILED" and outcome["stop_message"].startswith(check)
    assert world.effects(Effect.HOST_WRITE) == []


def test_m34_floating_current_pin_fails_preflight(tmp_path: Path) -> None:
    manifest = make_manifest(["frontend"])
    floating = "ghcr.io/shaneqwaszx/clm-aws-demo-frontend:latest"
    manifest["rollback"]["frontend"]["target_image"] = None
    world = FakeWorld(manifest)
    world.env["FRONTEND_IMAGE"] = floating
    world.images[floating] = world.images[OLD["frontend"]]
    world.containers["frontend"].label_hash = world._hash("frontend")
    outcome = deploy.run(make_context(manifest, tmp_path, world=world)[0])
    assert outcome["stop_code"] == "PREFLIGHT_FAILED" and "floating" in outcome["stop_message"]


def test_m44_a_restart_after_the_change_is_a_health_failure(tmp_path: Path) -> None:
    manifest = make_manifest(["assistant"])
    world = FakeWorld(manifest)
    world.restarts_after_up = 2
    outcome = deploy.run(make_context(manifest, tmp_path, world=world)[0])
    assert outcome["stop_code"] == "HEALTH_CHECK_FAILED" and outcome["state"] == records.FAILED_HELD


@pytest.mark.parametrize("active", [("assistant", "goldtier"), ("assistant", "assistant-provider")])
def test_m42_firewall_verify_script_must_pass_when_its_overlay_is_active(
    tmp_path: Path, active: tuple[str, ...]
) -> None:
    manifest = make_manifest(["frontend"], active=active)
    manifest["overlay"]["validation_set"] = "assistant"
    world = FakeWorld(manifest, active=active)
    world.verify_exit = 1
    outcome = deploy.run(make_context(manifest, tmp_path, world=world)[0])
    assert outcome["stop_code"] == "PREFLIGHT_FAILED" and "did not pass" in outcome["stop_message"]
    script = "verify_host_firewall.sh" if "goldtier" in active else "verify_assistant_egress.sh"
    assert script in world.remote_text() and world.effects(Effect.HOST_WRITE) == []
    passing = FakeWorld(manifest, active=active)
    result = deploy.run(make_context(manifest, tmp_path / "ok", world=passing)[0])
    assert result["state"] == records.DEPLOYED_AWAITING_ACCEPTANCE
    assert set(passing.recreated()) == {"frontend"}


def test_m28_proxy_network_identity_change_stops_the_run(tmp_path: Path) -> None:
    manifest = make_manifest(["frontend"])
    ctx, world = make_context(
        manifest, tmp_path, approval=make_approval(manifest, auto_rollback=False)
    )
    original = world._remote

    def recreated_network(text: str) -> Result:
        if "docker network inspect" in text and "{{.Internal}}" not in text:
            return Result(0, "proxy-net-2\n")
        return original(text)

    world._remote = recreated_network  # type: ignore[method-assign]
    outcome = deploy.run(ctx)
    assert (
        outcome["stop_code"] == "NETWORK_IDENTITY_CHANGED"
        and outcome["state"] == records.FAILED_HELD
    )


def test_m06_m25_another_container_changing_is_caught_at_apply_and_at_post_verification(
    tmp_path: Path,
) -> None:
    manifest = make_manifest(["frontend"])
    at_apply = make_context(
        manifest, tmp_path / "a", approval=make_approval(manifest, auto_rollback=False)
    )
    ctx, world = at_apply

    def backend_restarts_with_the_frontend(command: Any) -> None:
        if command.effect is Effect.HOST_WRITE and " up " in command.argv[-1]:
            world.containers["backend"].started = "2026-11-14T10:00:40Z"

    world.on_command = backend_restarts_with_the_frontend
    outcome = deploy.run(ctx)
    assert (
        outcome["stop_code"] == "UNAUTHORISED_SERVICE_CHANGE"
        and "backend" in outcome["stop_message"]
    )

    ctx2, world2 = make_context(
        manifest, tmp_path / "b", approval=make_approval(manifest, auto_rollback=False)
    )

    def assistant_restarts_during_smoke(command: Any) -> None:
        if command.argv[0] == "curl" and world2.recreated():
            world2.containers["assistant"].container_id = "assistant-c9"

    world2.on_command = assistant_restarts_during_smoke
    late = deploy.run(ctx2)
    assert (
        late["stop_code"] == "UNAUTHORISED_SERVICE_CHANGE" and "assistant" in late["stop_message"]
    )


def test_m23_ssh_never_accepts_an_unknown_host_key_or_an_option_like_destination(
    tmp_path: Path,
) -> None:
    ctx, world = make_context(make_manifest(["frontend"]), tmp_path)
    ctx.host.read("true", "probe")
    argv = world.received[-1].argv
    assert "StrictHostKeyChecking=yes" in argv and "BatchMode=yes" in argv and argv[-2] == "--"
    for bad in ("-Fevil", "", "host name", "host;id"):
        config = tmp_path / "operator.json"
        config.write_text(json.dumps({"ssh_destination": bad}), encoding="utf-8")
        with pytest.raises(ReleaseError):
            SshTarget.load(config)


# -- F11: deny-list ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "remote",
    [
        'sudo -n docker compose -f a.yml "down"',
        "sudo -n docker compose -f a.yml do''wn",
        "sudo -n docker compose -f a.yml up -d --remove-orph''ans frontend",
        "sudo -n docker compose -f a.yml up -dV --no-build --no-deps frontend",
        "sudo -n docker compose -f a.yml up -d --no-build --no-deps --renew-anon-volumes frontend",
        "sudo -n docker compose -f a.yml up -d --no-build --no-deps --force-recreate frontend",
        "sudo -n docker compose -f a.yml up -d --no-build backend",
        "sudo -n docker compose -f a.yml up -d --no-deps backend",
        "sudo -n docker compose -f a.yml up -d --no-build --no-deps --wait mongo",
        "sudo -n docker compose -f a.yml stop mongo",
        "sudo -n docker compose -f a.yml exec backend sh",
        "sudo -n docker container rm -f clm-staging-backend",
        "sudo -n docker stop clm-staging-mongo-1",
        "sudo -n docker network rm clm-staging_proxy",
        "sudo -n docker image rm abc",
        "sudo -n docker exec clm-staging-mongo-1 sh",
    ],
)
def test_f11_deny_list_variants_are_refused(remote: str) -> None:
    with pytest.raises(StopCondition):
        assert_remote_allowed(remote)


def test_f11_deny_list_blocks_none_of_the_commands_the_tool_generates(tmp_path: Path) -> None:
    for index, services in enumerate((["frontend"], ["assistant"], ["backend", "frontend"])):
        manifest = make_manifest(services, automatic={"backend": True})
        world = FakeWorld(manifest)
        world.smoke = {"/": "502"}  # also exercise every rollback command
        outcome = deploy.run(make_context(manifest, tmp_path / str(index), world=world)[0])
        assert outcome["state"] in {records.ROLLED_BACK, records.FAILED_HELD}
        assert outcome["stop_code"] == "SMOKE_FAILED"
    gate = Gate(FakeWorld(make_manifest(["frontend"])), Mode.EXECUTE, AuditLog())
    host = Host(gate, SshTarget("operator@host.test.invalid"), catalog.HostProfile())
    for set_name in ("base", "assistant", "assistant-provider", "goldtier"):
        assert_remote_allowed(host.compose_summary(set_name))
        assert_remote_allowed(host.compose_hashes(set_name))


# -- F12 / F13 / F9: command line and controller ----------------------------------------------


def test_f12_offline_cannot_be_combined_with_execute(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = cli.main(
        [
            "--state-dir",
            str(tmp_path),
            "deploy",
            "--manifest",
            str(SAMPLE),
            "--execute",
            "--offline",
        ]
    )
    assert code == 3 and "--offline cannot be combined with --execute" in capsys.readouterr().err


def test_f12_execute_refuses_a_preflight_check_that_could_not_be_read(tmp_path: Path) -> None:
    manifest = make_manifest(["frontend"])
    ctx, world = make_context(manifest, tmp_path, host_reads=False)
    outcome = deploy.run(ctx)
    assert (
        outcome["stop_code"] == "PREFLIGHT_FAILED" and outcome["state"] == records.FAILED_NO_CHANGE
    )
    assert world.received == []


def test_f9_execute_needs_the_host_paths_confirmed_in_the_operator_configuration(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = tmp_path / "operator.json"
    config.write_text(
        json.dumps({"ssh_destination": "operator@host.test.invalid"}), encoding="utf-8"
    )
    argv = [
        "--state-dir",
        str(tmp_path / "s"),
        "deploy",
        "--manifest",
        str(SAMPLE),
        "--operator-config",
        str(config),
        "--execute",
    ]
    assert cli.main(argv) == 3 and "mongo_uri_file must be confirmed" in capsys.readouterr().err
    config.write_text(
        json.dumps({"ssh_destination": "operator@host.test.invalid", "mongo_uri_file": "/x; rm"}),
        encoding="utf-8",
    )
    assert cli.main(argv) == 3 and "unsafe characters" in capsys.readouterr().err


def test_f9_host_paths_come_from_the_operator_configuration(tmp_path: Path) -> None:
    profile = catalog.HostProfile(mongo_uri_file="/srv/secure/clm.uri", workdir="/srv/clm")
    host = Host(
        Gate(FakeWorld(make_manifest(["frontend"])), Mode.DRY_RUN, AuditLog()),
        SshTarget("operator@host.test.invalid"),
        profile,
    )
    command = host.compose_config_quiet("base")
    assert "cat /srv/secure/clm.uri" in command and command.startswith("cd /srv/clm ")
    assert "/etc/clm/mongo.uri" not in command


def test_f13_skipped_checks_are_recorded_as_not_run(
    prepared: tuple[controller.Controller, FakeWorld, Path],  # noqa: F811
) -> None:
    instance, _, _ = prepared
    handled = instance.tick(run_checks=False)
    manifest = json.loads(Path(handled[0]["manifest"]).read_text(encoding="utf-8"))
    statuses = {c["name"]: c["status"] for c in manifest["checks"]}
    assert statuses["check_secrets"] == "NOT_RUN" and statuses["assistant-pytest"] == "NOT_RUN"
    assert statuses["ci-job:e2e"] == "NOT_RUN"
    assert "check_secrets" in handled[0]["not_run"]


def test_f17_host_state_directory_is_not_a_quoted_tilde() -> None:
    assert not catalog.HostProfile().state_dir.startswith("~")


def test_commands_carry_honest_effects_for_restore_and_lock_release(tmp_path: Path) -> None:
    """Housekeeping is limited to restoring compose.env and releasing the lock."""

    manifest = make_manifest(["frontend"])
    world = FakeWorld(manifest)
    world.smoke = {"/": "502"}
    ctx, world = make_context(manifest, tmp_path, world=world)
    deploy.run(ctx)
    housekeeping = {c.purpose for c in world.received if c.housekeeping}
    assert housekeeping == {"restore compose.env from the backup", "release the host release lock"}
    assert all(c.effect is Effect.HOST_WRITE for c in world.received if c.housekeeping)
    assert not [
        c for c in world.received if isinstance(c, Command) and c.effect is Effect.PROVIDER_CALL
    ]
