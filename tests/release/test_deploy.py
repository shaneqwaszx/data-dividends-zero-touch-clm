"""Plan, preflight, apply, verification and rollback against the mock host. No live host."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from tools.release import catalog, deploy, records, render
from tools.release.core import Effect, Mode, StopCondition

from .fakes import (
    NOW,
    OLD,
    FakeWorld,
    make_approval,
    make_context,
    make_manifest,
    new_reference,
    sentinel_token,
)

WRITE_EFFECTS = (Effect.HOST_WRITE, Effect.REGISTRY_WRITE, Effect.PROVIDER_CALL)
FORBIDDEN_WORDS = (
    " down",
    "--remove-orphans",
    "--volumes",
    " -v ",
    "volume rm",
    "volume prune",
    "--scale",
    "compose rm",
    " rm -s",
    "docker rm",
    "prune",
    "docker build",
)


@pytest.fixture(autouse=True)
def offline_render(monkeypatch: pytest.MonkeyPatch) -> None:
    """The offline Compose render has its own tests; here it is replaced so no Docker is needed."""

    monkeypatch.setattr(render, "validate_release_config", lambda gate, root, manifest: ["stub"])


def run(
    manifest: dict[str, Any], tmp_path: Path, **kwargs: Any
) -> tuple[dict[str, Any], FakeWorld, Any]:
    ctx, world = make_context(manifest, tmp_path, **kwargs)
    return deploy.run(ctx), world, ctx


def state_text(tmp_path: Path) -> str:
    return "\n".join(
        p.read_text(encoding="utf-8", errors="replace") for p in tmp_path.rglob("*") if p.is_file()
    )


# -- plan ------------------------------------------------------------------------------------


def test_plan_names_exactly_what_changes_and_what_must_not() -> None:
    manifest = make_manifest(["frontend"])
    plan = deploy.build_plan(manifest, transfer="pull", profile=catalog.HostProfile())
    assert [s["service"] for s in plan["services_change"]] == ["frontend"]
    assert plan["services_must_not_change"] == ["backend", "mongo", "assistant"]
    assert plan["ingress_interruption"] is False
    applied = [s["command"] for s in plan["host_steps"] if s["step"].startswith("apply")]
    assert len(applied) == 1
    assert applied[0].endswith(
        "up -d --no-build --no-deps --wait --wait-timeout 180 frontend </dev/null"
    )
    assert "compose.assistant.yml" not in applied[0] and "goldtier" not in applied[0]
    text = json.dumps(plan["host_steps"])
    assert not any(word in text for word in FORBIDDEN_WORDS)
    assert plan["services_change"][0]["automatic_rollback_eligible"] is True


def test_plan_orders_backend_first_and_rolls_the_frontend_back_first() -> None:
    manifest = make_manifest(["frontend", "backend", "assistant"])
    plan = deploy.build_plan(manifest, transfer="pull", profile=catalog.HostProfile())
    assert plan["deploy_order"] == ["backend", "assistant", "frontend"]
    assert plan["rollback_order"] == ["frontend", "assistant", "backend"]
    assert plan["ingress_interruption"] is True
    steps = [s["step"] for s in plan["host_steps"]]
    assert (
        steps.index("stop ingress") < steps.index("stop old backend") < steps.index("apply backend")
    )
    assistant = next(s for s in plan["host_steps"] if s["step"] == "apply assistant")["command"]
    assert "compose.assistant.yml" in assistant and assistant.rstrip().endswith(
        "assistant </dev/null"
    )


def test_plan_only_and_validation_sets_never_reach_the_host(tmp_path: Path) -> None:
    manifest = make_manifest(["frontend"])
    ctx, world = make_context(manifest, tmp_path, mode=Mode.PLAN_ONLY)
    deploy.build_plan(manifest, transfer="pull", profile=ctx.host.profile)
    assert world.received == []
    with pytest.raises(StopCondition):
        ctx.host.compose("full-provider-goldtier", "config", "--quiet")
    with pytest.raises(StopCondition):
        ctx.host.compose_up("goldtier", "goldtier-egress")
    with pytest.raises(StopCondition):
        ctx.host.compose_up("base", "mongo")


# -- dry run ---------------------------------------------------------------------------------


@pytest.mark.parametrize("services", [["frontend"], ["assistant"], ["backend", "frontend"]])
def test_dry_run_issues_no_host_write_no_registry_write_and_no_provider_call(
    tmp_path: Path, services: list[str]
) -> None:
    manifest = make_manifest(services)
    outcome, world, ctx = run(manifest, tmp_path, mode=Mode.DRY_RUN)
    assert outcome["state"] == records.DRY_RUN_OK
    assert world.effects(*WRITE_EFFECTS) == []
    assert world.effects(Effect.HOST_READ), (
        "a dry run with a host still performs its read-only preflight"
    )
    assert world.recreated() == [] and world.env["FRONTEND_IMAGE"] == OLD["frontend"]
    assert world.stdin_seen == [], "no credential is read or sent in a dry run"
    assert {c["effect"] for c in outcome["would_issue"]} == {"host-write"}
    assert ctx.store.consumed_approvals() == frozenset()


def test_offline_dry_run_contacts_nothing_at_all(tmp_path: Path) -> None:
    manifest = make_manifest(["frontend"], published=False)
    outcome, world, _ = run(manifest, tmp_path, mode=Mode.DRY_RUN, host_reads=False, approval=None)
    assert outcome["state"] == records.DRY_RUN_OK
    assert world.received == []
    assert all(c["status"] == "SKIPPED" for c in outcome["preflight"])


# -- execute: approvals ----------------------------------------------------------------------


def test_execute_without_an_approval_is_refused_before_any_contact(tmp_path: Path) -> None:
    outcome, world, _ = run(make_manifest(["frontend"]), tmp_path, approval=None)
    assert (
        outcome["state"] == records.FAILED_NO_CHANGE and outcome["stop_code"] == "APPROVAL_MISSING"
    )
    assert world.received == []


def test_expired_approval_is_refused_before_any_contact(tmp_path: Path) -> None:
    manifest = make_manifest(["frontend"])
    expired = make_approval(manifest, start=NOW - timedelta(hours=3), end=NOW - timedelta(hours=1))
    outcome, world, _ = run(manifest, tmp_path, approval=expired)
    assert outcome["stop_code"] == "APPROVAL_EXPIRED" and world.received == []


def test_approval_for_other_services_is_refused(tmp_path: Path) -> None:
    manifest = make_manifest(["frontend"])
    wider = make_approval(manifest, services=["frontend", "backend"])
    outcome, world, _ = run(manifest, tmp_path, approval=wider)
    assert outcome["stop_code"] == "APPROVAL_SERVICE_MISMATCH" and world.received == []


def test_window_too_short_to_finish_is_refused_before_any_change(tmp_path: Path) -> None:
    manifest = make_manifest(["frontend"])
    short = make_approval(manifest, end=NOW + timedelta(minutes=5))
    outcome, world, _ = run(manifest, tmp_path, approval=short)
    assert outcome["stop_code"] == "APPROVAL_WINDOW_TOO_SHORT"
    assert world.effects(Effect.HOST_WRITE) == []


def test_expiry_during_the_run_stops_before_the_next_change_and_does_not_roll_back(
    tmp_path: Path,
) -> None:
    manifest = make_manifest(["assistant", "frontend"], automatic={"assistant": True})
    ctx, world = make_context(manifest, tmp_path)

    def expire_after_assistant(command: Any) -> None:
        if command.effect is Effect.HOST_WRITE and command.argv[-1].endswith(
            "assistant </dev/null"
        ):
            world.clock.advance(hours=3)

    world.on_command = expire_after_assistant
    outcome = deploy.run(ctx)
    assert outcome["state"] == records.FAILED_HELD and outcome["stop_code"] == "APPROVAL_EXPIRED"
    assert "never extended" in outcome["held_reason"]
    assert world.recreated() == ["assistant"], "the frontend was never touched after expiry"
    after = [c for c in world.effects(Effect.HOST_WRITE) if "frontend" in c.argv[-1].split()[-2:]]
    assert after == []
    assert world.host_lock is False, "the host lock is still released (housekeeping)"


def test_an_approval_cannot_be_used_twice(tmp_path: Path) -> None:
    manifest = make_manifest(["frontend"])
    ctx, world = make_context(manifest, tmp_path)
    assert deploy.run(ctx)["state"] == records.DEPLOYED_AWAITING_ACCEPTANCE
    writes = len(world.effects(Effect.HOST_WRITE))
    again = deploy.run(ctx)
    assert again["stop_code"] == "APPROVAL_ALREADY_USED"
    assert len(world.effects(Effect.HOST_WRITE)) == writes


# -- execute: happy paths --------------------------------------------------------------------


def test_frontend_only_release_changes_only_the_frontend(tmp_path: Path) -> None:
    manifest = make_manifest(["frontend"])
    outcome, world, ctx = run(manifest, tmp_path)
    assert outcome["state"] == records.DEPLOYED_AWAITING_ACCEPTANCE
    assert world.recreated() == ["frontend"]
    assert world.env["FRONTEND_IMAGE"] == new_reference(manifest, "frontend")
    assert (
        world.env["BACKEND_IMAGE"] == OLD["backend"]
        and world.env["ASSISTANT_IMAGE"] == OLD["assistant"]
    )
    ups = [c.argv[-1] for c in world.effects(Effect.HOST_WRITE) if " up " in c.argv[-1]]
    assert (
        len(ups) == 1
        and "--no-build --no-deps --wait" in ups[0]
        and ups[0].split()[-2] == "frontend"
    )
    remote = world.remote_text()
    assert not any(word in remote for word in FORBIDDEN_WORDS)
    assert world.host_lock is False
    assert outcome["pins_before"] == {"frontend": OLD["frontend"]}
    assert ctx.store.known_good() is None, "known-good moves only after owner acceptance"


def test_assistant_only_release_uses_the_assistant_wrapper_and_touches_nothing_else(
    tmp_path: Path,
) -> None:
    manifest = make_manifest(["assistant"])
    outcome, world, _ = run(manifest, tmp_path)
    assert outcome["state"] == records.DEPLOYED_AWAITING_ACCEPTANCE
    assert world.recreated() == ["assistant"]
    up = next(c.argv[-1] for c in world.effects(Effect.HOST_WRITE) if " up " in c.argv[-1])
    assert "-f apps/assistant/deploy/compose.assistant.yml" in up
    assert "compose.goldtier-egress.yml" not in world.remote_text()


def test_backend_release_keeps_exactly_one_writer_and_restores_ingress(tmp_path: Path) -> None:
    manifest = make_manifest(["backend"])
    outcome, world, _ = run(manifest, tmp_path)
    assert outcome["state"] == records.DEPLOYED_AWAITING_ACCEPTANCE
    verbs = [
        (c.argv[-1].split()[-3], c.argv[-1].split()[-2])
        for c in world.effects(Effect.HOST_WRITE)
        if "docker compose" in c.argv[-1]
    ]
    assert verbs == [
        ("stop", "frontend"),
        ("stop", "backend"),
        ("180", "backend"),
        ("start", "frontend"),
    ]
    assert world.recreated() == ["backend"]
    assert (
        world.containers["frontend"].running
        and world.containers["frontend"].container_id == "frontend-c0"
    )


def test_pull_token_travels_only_on_stdin_and_reaches_no_log_or_record(tmp_path: Path) -> None:
    manifest = make_manifest(["frontend"])
    outcome, world, _ = run(manifest, tmp_path)
    token = sentinel_token("pull")
    assert world.stdin_seen == [token], "exactly one credential, the read-only one, was streamed"
    assert sentinel_token("publish") not in world.stdin_seen
    for command in world.received:
        assert token not in " ".join(command.argv)
        assert token not in json.dumps(dict(command.env or {}))
    assert token not in state_text(tmp_path) and token not in json.dumps(outcome)
    pull = next(c for c in world.received if "clm-ghcr" in c.argv[-1])
    assert "/run/clm-ghcr." in pull.argv[-1] and "logout ghcr.io" in pull.argv[-1]
    assert "rmdir" in pull.argv[-1] and "@sha256:" in pull.argv[-1]


# -- execute: preflight failures -------------------------------------------------------------


@pytest.mark.parametrize(
    ("knob", "value", "check"),
    [
        ("ssh_sessions", 2, "sole-operator"),
        ("host_lock", True, "no-overlapping-release"),
        ("mem_available", 900_000, "capacity"),
        ("disk_free", 100_000, "capacity"),
        ("listening", ("0.0.0.0:80", "0.0.0.0:443", "0.0.0.0:27017"), "network-boundaries"),
        ("listening", ("0.0.0.0:8000",), "network-boundaries"),
        ("drifted", {"backend"}, "no-drift"),
        ("compose_file_override", {"deploy/compose.yml": "0" * 64}, "compose-files"),
    ],
)
def test_failed_preflight_stops_with_nothing_changed(
    tmp_path: Path, knob: str, value: Any, check: str
) -> None:
    manifest = make_manifest(["frontend"])
    world = FakeWorld(manifest)
    setattr(world, knob, value)
    outcome, world, ctx = run(manifest, tmp_path, world=world)
    assert (
        outcome["state"] == records.FAILED_NO_CHANGE and outcome["stop_code"] == "PREFLIGHT_FAILED"
    )
    assert check in outcome["stop_message"]
    writes = [c for c in world.effects(Effect.HOST_WRITE)]
    assert writes == [], "a failed preflight must not write anything, not even the lock"
    assert world.recreated() == [] and world.env["FRONTEND_IMAGE"] == OLD["frontend"]
    assert ctx.store.consumed_approvals() == frozenset(), "the approval is still usable"


def test_unhealthy_container_and_missing_rollback_image_fail_preflight(tmp_path: Path) -> None:
    manifest = make_manifest(["frontend"])
    sick = FakeWorld(manifest)
    sick.containers["backend"].health = "unhealthy"
    assert "containers" in run(manifest, tmp_path / "a", world=sick)[0]["stop_message"]
    uncached = FakeWorld(manifest)
    del uncached.images[OLD["frontend"]]
    assert "rollback image" in run(manifest, tmp_path / "b", world=uncached)[0]["stop_message"]
    moved = FakeWorld(manifest)
    moved.env["FRONTEND_IMAGE"] = OLD["frontend"].replace("@sha256:", "@sha256:f")[:-1]
    moved.images[moved.env["FRONTEND_IMAGE"]] = "sha256:" + "7" * 64
    moved.containers["frontend"].label_hash = moved._hash("frontend")
    assert (
        "not at the rollback target"
        in run(manifest, tmp_path / "c", world=moved)[0]["stop_message"]
    )


def test_stateful_release_needs_a_recent_backup_and_a_configured_location(tmp_path: Path) -> None:
    manifest = make_manifest(["assistant"])
    stale = FakeWorld(manifest)
    stale.backups = 0
    outcome = run(manifest, tmp_path / "a", world=stale)[0]
    assert outcome["stop_code"] == "PREFLIGHT_FAILED" and "backups" in outcome["stop_message"]
    ctx, world = make_context(manifest, tmp_path / "b")
    ctx.host.profile = catalog.HostProfile(backup_glob=None)
    assert "not configured" in deploy.run(ctx)["stop_message"]
    frontend = make_manifest(["frontend"])
    none_needed = FakeWorld(frontend)
    none_needed.backups = 0
    assert (
        run(frontend, tmp_path / "c", world=none_needed)[0]["state"]
        == records.DEPLOYED_AWAITING_ACCEPTANCE
    )


def test_backend_release_needs_the_running_backend_confirmed_on_the_host(tmp_path: Path) -> None:
    manifest = make_manifest(["backend"])
    manifest["rollback"]["backend"]["target_confirmed_on_host"] = False
    outcome, world, _ = run(manifest, tmp_path)
    assert outcome["stop_code"] == "PREFLIGHT_FAILED" and "not confirmed" in outcome["stop_message"]
    assert world.effects(Effect.HOST_WRITE) == []


# -- execute: image transfer -----------------------------------------------------------------


def test_failed_image_pull_changes_nothing_and_leaves_the_approval_usable(tmp_path: Path) -> None:
    manifest = make_manifest(["frontend"])
    world = FakeWorld(manifest)
    world.pull_ok = False
    outcome, world, ctx = run(manifest, tmp_path, world=world)
    assert (
        outcome["state"] == records.FAILED_NO_CHANGE and outcome["stop_code"] == "IMAGE_PULL_FAILED"
    )
    assert world.recreated() == [] and world.env["FRONTEND_IMAGE"] == OLD["frontend"]
    assert world.host_lock is False and ctx.store.consumed_approvals() == frozenset()
    assert sentinel_token("pull") not in state_text(tmp_path) + json.dumps(outcome)


def test_wrong_digest_on_the_host_is_refused(tmp_path: Path) -> None:
    manifest = make_manifest(["frontend"])
    world = FakeWorld(manifest)
    world.pull_delivers[new_reference(manifest, "frontend")] = "sha256:" + "9" * 64
    outcome, world, _ = run(manifest, tmp_path, world=world)
    assert outcome["state"] == records.FAILED_NO_CHANGE and outcome["stop_code"] == "WRONG_DIGEST"
    assert world.recreated() == [] and world.env["FRONTEND_IMAGE"] == OLD["frontend"]


def test_unpublished_manifest_cannot_be_deployed_by_pull(tmp_path: Path) -> None:
    outcome, world, _ = run(make_manifest(["frontend"], published=False), tmp_path)
    assert outcome["stop_code"] == "REGISTRY_DIGEST_UNKNOWN" and world.received == []


# -- execute: unauthorised change ------------------------------------------------------------


def test_a_service_outside_the_approval_that_would_be_recreated_stops_the_run(
    tmp_path: Path,
) -> None:
    manifest = make_manifest(["frontend"])
    ctx, world = make_context(manifest, tmp_path)

    def drift_after_pin(command: Any) -> None:
        if " sed -i " in command.argv[-1]:
            world.env["BACKEND_IMAGE"] = OLD["backend"] + "0"

    world.on_command = drift_after_pin
    outcome = deploy.run(ctx)
    assert outcome["stop_code"] in {"UNAUTHORISED_SERVICE_CHANGE", "ENV_EDIT_UNEXPECTED"}
    assert outcome["state"] == records.FAILED_NO_CHANGE
    assert world.recreated() == [] and world.env["FRONTEND_IMAGE"] == OLD["frontend"]
    assert not [c for c in world.effects(Effect.HOST_WRITE) if " up " in c.argv[-1]]


def test_backend_hash_change_without_approval_is_named_as_unauthorised(tmp_path: Path) -> None:
    manifest = make_manifest(["frontend"])
    ctx, world = make_context(manifest, tmp_path)
    original = world._hash

    def hash_with_surprise(name: str) -> str:
        pinned = world.env["FRONTEND_IMAGE"] != OLD["frontend"]
        return "surprise" if name == "backend" and pinned else original(name)

    world._hash = hash_with_surprise  # type: ignore[method-assign]
    outcome = deploy.run(ctx)
    assert (
        outcome["stop_code"] == "UNAUTHORISED_SERVICE_CHANGE"
        and "backend" in outcome["stop_message"]
    )
    assert outcome["state"] == records.FAILED_NO_CHANGE
    assert world.recreated() == [] and world.env["FRONTEND_IMAGE"] == OLD["frontend"]


def test_host_render_with_an_undeclared_network_is_refused(tmp_path: Path) -> None:
    manifest = make_manifest(["assistant"])
    world = FakeWorld(manifest)
    world.host_summary_extra_network = "assistant-uplink"
    outcome, world, _ = run(manifest, tmp_path, world=world)
    assert outcome["stop_code"] == "EFFECTIVE_CONFIG_UNDECLARED"
    assert world.recreated() == [] and world.env["ASSISTANT_IMAGE"] == OLD["assistant"]


def test_services_the_applier_never_changes_are_refused() -> None:
    manifest = make_manifest(["frontend"], risk="HIGH", active=("assistant", "goldtier"))
    manifest["services_changed"] = ["goldtier-egress"]
    manifest["services_unchanged"] = ["frontend", "backend", "mongo", "assistant", "goldtier-dns"]
    manifest["images"] = {"goldtier-egress": dict(manifest["images"]["frontend"])}
    manifest["images"]["goldtier-egress"]["repository"] = catalog.SERVICES[
        "goldtier-egress"
    ].repository
    manifest["rollback"] = {"goldtier-egress": manifest["rollback"]["frontend"]}
    with pytest.raises(StopCondition) as refused:
        deploy.build_plan(manifest, transfer="pull", profile=catalog.HostProfile())
    assert refused.value.code == "SERVICE_NOT_AUTOMATED"


# -- locking ---------------------------------------------------------------------------------


def test_overlapping_deployment_is_refused_by_the_local_lock(tmp_path: Path) -> None:
    manifest = make_manifest(["frontend"])
    ctx, world = make_context(manifest, tmp_path)
    with ctx.store.lock("rel-other-20261114-01"), pytest.raises(StopCondition) as busy:
        deploy.run(ctx)
    assert busy.value.code == "RELEASE_IN_PROGRESS" and world.received == []
    assert deploy.run(ctx)["state"] == records.DEPLOYED_AWAITING_ACCEPTANCE


def test_stale_local_lock_is_never_stolen_silently(tmp_path: Path) -> None:
    manifest = make_manifest(["frontend"])
    ctx, world = make_context(manifest, tmp_path)
    ctx.store.root.mkdir(parents=True)
    (ctx.store.root / "release.lock").write_text('{"release_id": "rel-crashed"}', encoding="utf-8")
    with pytest.raises(StopCondition) as busy:
        deploy.run(ctx)
    assert "rel-crashed" in busy.value.message and world.received == []
    assert ctx.store.unlock() is True


# -- failures after a change -----------------------------------------------------------------


@pytest.mark.parametrize("failure", ["unhealthy_after_up", "up_fails"])
def test_frontend_health_failure_rolls_back_automatically(tmp_path: Path, failure: str) -> None:
    manifest = make_manifest(["frontend"])
    world = FakeWorld(manifest)
    setattr(world, failure, {"frontend"})
    ctx, world = make_context(manifest, tmp_path, world=world)

    def heal_on_restore(command: Any) -> None:
        if "cp -p /etc/clm/compose.env.pre-" in command.argv[-1]:
            getattr(world, failure).discard("frontend")

    world.on_command = heal_on_restore
    outcome = deploy.run(ctx)
    assert outcome["state"] == records.ROLLED_BACK
    assert outcome["stop_code"] in {"HEALTH_CHECK_FAILED", "APPLY_FAILED"}
    assert world.env["FRONTEND_IMAGE"] == OLD["frontend"]
    assert world.containers["frontend"].image == world.images[OLD["frontend"]]
    assert set(world.recreated()) == {"frontend"}
    assert ctx.store.known_good() is None


def test_smoke_failure_rolls_the_frontend_back(tmp_path: Path) -> None:
    manifest = make_manifest(["frontend"])
    world = FakeWorld(manifest)
    world.smoke = {"/": "502"}
    outcome, world, _ = run(manifest, tmp_path, world=world)
    assert outcome["state"] == records.ROLLED_BACK and outcome["stop_code"] == "SMOKE_FAILED"
    assert world.env["FRONTEND_IMAGE"] == OLD["frontend"]


def test_rollback_is_not_run_when_the_owner_did_not_approve_it(tmp_path: Path) -> None:
    manifest = make_manifest(["frontend"])
    world = FakeWorld(manifest)
    world.unhealthy_after_up = {"frontend"}
    no_auto = make_approval(manifest, auto_rollback=False)
    outcome, world, _ = run(manifest, tmp_path, world=world, approval=no_auto)
    assert outcome["state"] == records.FAILED_HELD
    assert "did not approve automatic rollback" in outcome["held_reason"]
    assert world.env["FRONTEND_IMAGE"] != OLD["frontend"], "held exactly as it failed"


def test_assistant_failure_is_held_because_store_compatibility_is_unproven(tmp_path: Path) -> None:
    manifest = make_manifest(["assistant"])
    world = FakeWorld(manifest)
    world.unhealthy_after_up = {"assistant"}
    outcome, world, _ = run(manifest, tmp_path, world=world)
    assert outcome["state"] == records.FAILED_HELD
    assert "unproven" in outcome["held_reason"]
    ups = [c for c in world.effects(Effect.HOST_WRITE) if " up " in c.argv[-1]]
    assert len(ups) == 1, "no second up: nothing was rolled back blindly"
    assert world.env["ASSISTANT_IMAGE"] != OLD["assistant"]


def test_stateful_backend_is_never_rolled_back_blindly(tmp_path: Path) -> None:
    manifest = make_manifest(["backend"])
    manifest["rollback"]["backend"].update(data_compatible="unproven")
    world = FakeWorld(manifest)
    world.unhealthy_after_up = {"backend"}
    outcome, world, _ = run(manifest, tmp_path, world=world)
    assert outcome["state"] == records.FAILED_HELD
    assert "backend" in outcome["held_reason"] and "INGRESS IS STOPPED" in outcome["held_reason"]
    assert outcome["ingress_stopped"] is True
    ups = [c for c in world.effects(Effect.HOST_WRITE) if " up " in c.argv[-1]]
    assert len(ups) == 1 and world.env["BACKEND_IMAGE"] != OLD["backend"]


def test_backend_with_proven_compatibility_and_owner_consent_rolls_back(tmp_path: Path) -> None:
    manifest = make_manifest(["backend"], automatic={"backend": True})
    world = FakeWorld(manifest)
    world.unhealthy_after_up = {"backend"}
    ctx, world = make_context(manifest, tmp_path, world=world)

    def heal_on_restore(command: Any) -> None:
        if "cp -p /etc/clm/compose.env.pre-" in command.argv[-1]:
            world.unhealthy_after_up.discard("backend")

    world.on_command = heal_on_restore
    outcome = deploy.run(ctx)
    assert outcome["state"] == records.ROLLED_BACK
    assert world.env["BACKEND_IMAGE"] == OLD["backend"]
    assert world.containers["backend"].image == world.images[OLD["backend"]]
    assert world.containers["frontend"].running


def test_old_backend_that_could_not_be_stopped_is_resumed_without_running_new_code(
    tmp_path: Path,
) -> None:
    manifest = make_manifest(["backend"])
    manifest["rollback"]["backend"].update(data_compatible="unproven")
    world = FakeWorld(manifest)
    world.stop_fails = {"backend"}
    outcome, world, _ = run(manifest, tmp_path, world=world)
    assert outcome["state"] == records.FAILED_NO_CHANGE and outcome["stop_code"] == "APPLY_FAILED"
    assert world.recreated() == [] and world.env["BACKEND_IMAGE"] == OLD["backend"]
    assert world.containers["frontend"].running and world.containers["backend"].running
    assert not [c for c in world.effects(Effect.HOST_WRITE) if " up " in c.argv[-1]]


def test_second_backend_container_is_a_stop_condition(tmp_path: Path) -> None:
    manifest = make_manifest(["backend"])
    manifest["rollback"]["backend"].update(data_compatible="unproven")
    world = FakeWorld(manifest)
    world.extra_backend = True
    outcome, _, _ = run(manifest, tmp_path, world=world)
    assert outcome["stop_code"] == "SECOND_BACKEND" and outcome["state"] == records.FAILED_HELD


def test_mongo_volume_identity_change_stops_the_run_and_volumes_are_never_removed(
    tmp_path: Path,
) -> None:
    manifest = make_manifest(["frontend"])
    world = FakeWorld(manifest)
    world.volume_changes_after_up = True
    no_auto = make_approval(manifest, auto_rollback=False)
    outcome, world, _ = run(manifest, tmp_path, world=world, approval=no_auto)
    assert (
        outcome["stop_code"] == "VOLUME_IDENTITY_CHANGED"
        and outcome["state"] == records.FAILED_HELD
    )
    remote = world.remote_text()
    assert "volume rm" not in remote and "volume prune" not in remote and " down" not in remote
    assert "mongo" not in [c.argv[-1].split()[-2] for c in world.effects(Effect.HOST_WRITE)]


def test_mongo_is_never_stopped_started_or_recreated_by_any_run(tmp_path: Path) -> None:
    for index, services in enumerate(
        (["frontend"], ["assistant"], ["backend"], ["backend", "frontend"])
    ):
        outcome, world, _ = run(make_manifest(services), tmp_path / str(index))
        assert outcome["state"] == records.DEPLOYED_AWAITING_ACCEPTANCE
        mongo = world.containers["mongo"]
        assert (
            mongo.container_id == "mongo-c0"
            and mongo.running
            and mongo.started == "2026-11-01T00:00:00Z"
        )
        for command in world.effects(Effect.HOST_WRITE):
            assert command.argv[-1].split()[-2] != "mongo"


# -- acceptance and manual rollback ----------------------------------------------------------


def test_owner_acceptance_moves_known_good_and_records_the_previous_one(tmp_path: Path) -> None:
    manifest = make_manifest(["frontend"])
    outcome, _, ctx = run(manifest, tmp_path)
    assert outcome["state"] == records.DEPLOYED_AWAITING_ACCEPTANCE
    with pytest.raises(StopCondition) as automated:
        deploy.accept(ctx.store, manifest, passed=True, accepted_by="agent", interactive=False)
    assert automated.value.code == "ACCEPTANCE_NEEDS_OWNER"
    accepted = deploy.accept(
        ctx.store, manifest, passed=True, accepted_by="owner", interactive=True
    )
    assert accepted["state"] == records.ACCEPTED
    assert ctx.store.known_good()["release_id"] == manifest["release_id"]
    with pytest.raises(StopCondition):
        deploy.accept(ctx.store, manifest, passed=True, accepted_by="owner", interactive=True)
    sheet = deploy.acceptance_runsheet(manifest, ctx.host.profile)
    assert "waits for the owner" in sheet
    results = sorted(
        p.name for p in ctx.store.release_dir(manifest["release_id"]).glob("result-*.json")
    )
    assert results == ["result-001.json", "result-002.json"], (
        "every result is kept, none overwritten"
    )


def test_failed_acceptance_never_rolls_back_by_itself_and_keeps_known_good(tmp_path: Path) -> None:
    manifest = make_manifest(["frontend"])
    _, world, ctx = run(manifest, tmp_path)
    writes = len(world.effects(Effect.HOST_WRITE))
    failed = deploy.accept(ctx.store, manifest, passed=False, accepted_by="owner", interactive=True)
    assert failed["state"] == records.ACCEPTANCE_FAILED and ctx.store.known_good() is None
    assert len(world.effects(Effect.HOST_WRITE)) == writes


def test_owner_requested_rollback_follows_the_same_eligibility_rules(tmp_path: Path) -> None:
    frontend = make_manifest(["frontend"])
    _, world, ctx = run(frontend, tmp_path / "a")
    deploy.accept(ctx.store, frontend, passed=False, accepted_by="owner", interactive=True)
    deploy_approval = ctx.approval
    with pytest.raises(StopCondition) as wrong_action:
        deploy.manual_rollback(ctx, frontend["release_id"])
    assert wrong_action.value.code == "APPROVAL_ACTION", "the deploy approval is not reusable"
    ctx.approval = make_approval(
        frontend, actions=("rollback",), auto_rollback=False, issued="101500"
    )
    rolled = deploy.manual_rollback(ctx, frontend["release_id"])
    assert rolled["state"] == records.ROLLED_BACK and world.env["FRONTEND_IMAGE"] == OLD["frontend"]
    assert rolled["rollback_approval_id"] != deploy_approval["approval_id"]
    assert world.host_lock is False
    with pytest.raises(StopCondition) as again:
        deploy.manual_rollback(ctx, frontend["release_id"])
    assert again.value.code == "ROLLBACK_NOT_APPLICABLE"

    assistant = make_manifest(["assistant"])
    _, world2, ctx2 = run(assistant, tmp_path / "b")
    ctx2.approval = make_approval(assistant, actions=("rollback",), issued="101600")
    with pytest.raises(StopCondition) as refused:
        deploy.manual_rollback(ctx2, assistant["release_id"])
    assert refused.value.code == "ROLLBACK_REFUSED" and "unproven" in refused.value.message
    assert world2.env["ASSISTANT_IMAGE"] != OLD["assistant"]
    assert ctx2.store.consumed_approvals() == frozenset(
        {f"{make_approval(assistant)['approval_id']}:deploy"}
    )
    ctx2.approval = None
    with pytest.raises(StopCondition) as unapproved:
        deploy.manual_rollback(ctx2, assistant["release_id"])
    assert unapproved.value.code == "APPROVAL_MISSING"
