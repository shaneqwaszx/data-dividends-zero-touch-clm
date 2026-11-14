"""Rollback under interruption, failure and repeat invocation (re-review findings N1 and N2).

Mock host only. The rules under test: a rollback-in-progress record is on disk before the
first rollback step; an interrupted, failed or unverifiable rollback is never recorded as
rolled back and never leaves an acceptable deployment; ``accept`` refuses until the read-only
``recover`` step has verified the host; evidence of every attempt is kept.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from tools.release import deploy, records, render
from tools.release.core import Command, Effect, Mode, Result, StopCondition

from .fakes import (
    OLD,
    FakeWorld,
    make_approval,
    make_context,
    make_manifest,
    new_reference,
    sentinel_token,
)


@pytest.fixture(autouse=True)
def offline_render(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(render, "validate_release_config", lambda gate, root, manifest: ["stub"])


class Killed(BaseException):
    """Stands for anything that is not an ordinary error: a kill signal turned into an
    exception, a defect deep in a library, Ctrl-C."""


def restore_command(command: Command) -> bool:
    return "cp -p /etc/clm/compose.env.pre-" in command.argv[-1]


def in_rollback(world: FakeWorld) -> bool:
    return bool(getattr(world, "restored", False))


def interrupt(
    world: FakeWorld, when: Callable[[Command], bool], error: type[BaseException]
) -> None:
    def hook(command: Command) -> None:
        if when(command):
            world.on_command = None
            raise error()

    world.on_command = hook


def failing_release(
    tmp_path: Path, services: list[str], **manifest_kwargs: Any
) -> tuple[Any, FakeWorld, dict[str, Any]]:
    """A release whose smoke check fails after every service was applied, so an automatic
    rollback of all of them starts."""

    manifest = make_manifest(services, automatic={"backend": True}, **manifest_kwargs)
    world = FakeWorld(manifest)
    world.smoke = {"/": "502"}
    ctx, world = make_context(manifest, tmp_path, world=world)
    return ctx, world, manifest


def latest(ctx: Any, manifest: dict[str, Any]) -> dict[str, Any]:
    record = ctx.store.read_result(manifest["release_id"])
    assert record is not None
    return record


def journal(ctx: Any, manifest: dict[str, Any]) -> list[str]:
    path = ctx.store.release_dir(manifest["release_id"]) / "rollback-journal.jsonl"
    return [json.loads(line)["step"] for line in path.read_text(encoding="utf-8").splitlines()]


def result_states(ctx: Any, manifest: dict[str, Any]) -> list[str]:
    directory = ctx.store.release_dir(manifest["release_id"])
    return [
        json.loads(p.read_text(encoding="utf-8"))["state"]
        for p in sorted(directory.glob("result-*.json"))
    ]


def deployed(tmp_path: Path, services: list[str]) -> tuple[Any, FakeWorld, dict[str, Any]]:
    manifest = make_manifest(services, automatic={"backend": True})
    ctx, world = make_context(manifest, tmp_path)
    assert deploy.run(ctx)["state"] == records.DEPLOYED_AWAITING_ACCEPTANCE
    return ctx, world, manifest


def rollback_approval(manifest: dict[str, Any], issued: str) -> dict[str, Any]:
    return make_approval(manifest, actions=("rollback",), auto_rollback=False, issued=issued)


def reader(ctx: Any, world: FakeWorld, tmp_path: Path, *, host_reads: bool = True) -> Any:
    """A read-only context on the same state directory and host, as the recover command uses."""

    return make_context(
        ctx.manifest, tmp_path, mode=Mode.DRY_RUN, world=world, approval=None, host_reads=host_reads
    )[0]


# -- 1. before the first rollback step --------------------------------------------------------


def test_in_progress_record_is_on_disk_before_the_first_rollback_step(tmp_path: Path) -> None:
    ctx, world, manifest = failing_release(tmp_path, ["backend", "frontend"])
    seen: dict[str, Any] = {}

    def snapshot_at_first_rollback_command(command: Command) -> None:
        if restore_command(command) and not seen:
            seen["record"] = latest(ctx, manifest)
            seen["journal"] = journal(ctx, manifest)
            seen["stopped_or_replaced"] = [
                c.argv[-1].split()[-3:-1]
                for c in world.effects(Effect.HOST_WRITE)
                if "docker compose" in c.argv[-1]
            ][4:]

    world.on_command = snapshot_at_first_rollback_command
    assert deploy.run(ctx)["state"] == records.ROLLED_BACK
    record = seen["record"]
    assert record["state"] == records.ROLLBACK_IN_PROGRESS
    assert (
        record["rollback"]["status"] == "IN_PROGRESS" and record["rollback"]["kind"] == "automatic"
    )
    assert record["rollback"]["host_state"] == "unknown"
    assert "UNKNOWN" in record["held_reason"] and record["stop_code"] == "SMOKE_FAILED"
    assert seen["journal"] == ["restore compose.env from the backup"]
    assert seen["stopped_or_replaced"] == [], "nothing was stopped or replaced before the record"


@pytest.mark.parametrize("error", [KeyboardInterrupt, RuntimeError, Killed])
def test_interrupt_before_any_rollback_step_is_never_reported_as_rolled_back(
    tmp_path: Path, error: type[BaseException]
) -> None:
    ctx, world, manifest = failing_release(tmp_path, ["backend", "frontend"])
    interrupt(world, restore_command, error)
    with pytest.raises(error):
        deploy.run(ctx)
    record = latest(ctx, manifest)
    assert record["state"] == records.ROLLBACK_INTERRUPTED
    assert (
        record["rollback"]["status"] == "INTERRUPTED"
        and record["rollback"]["host_state"] == "unknown"
    )
    assert record["interrupted_by"] == error.__name__
    assert "UNKNOWN" in record["held_reason"] and "restored" in record["held_reason"]
    assert world.env["BACKEND_IMAGE"] == new_reference(manifest, "backend"), "nothing was undone"
    assert world.host_lock is False and not (ctx.store.root / "release.lock").exists()


def test_a_process_that_dies_without_any_handler_leaves_the_in_progress_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SIGKILL or power loss: no handler runs. Simulated by making the handler itself die."""

    ctx, world, manifest = failing_release(tmp_path, ["backend", "frontend"])
    interrupt(world, lambda c: in_rollback(world) and " up " in c.argv[-1], Killed)

    def no_handler(state: Any, crash: BaseException) -> dict[str, Any]:
        raise Killed()

    monkeypatch.setattr(deploy, "_interrupted", no_handler)
    with pytest.raises(Killed):
        deploy.run(ctx)
    record = latest(ctx, manifest)
    assert record["state"] == records.ROLLBACK_IN_PROGRESS, "the last durable record is truthful"
    assert record["rollback"]["ingress_may_be_stopped"] is True
    last = record["rollback"]["steps"][-1]
    assert last == {"step": "recreate backend on its previous image", "status": "STARTED"}
    with pytest.raises(StopCondition) as refused:
        deploy.accept(ctx.store, manifest, passed=True, accepted_by="owner", interactive=True)
    assert refused.value.code == "ROLLBACK_INCOMPLETE"


# -- 2. after ingress is stopped --------------------------------------------------------------


def test_interrupt_after_ingress_is_stopped_records_that_the_site_may_be_down(
    tmp_path: Path,
) -> None:
    ctx, world, manifest = failing_release(tmp_path, ["backend", "frontend"])
    interrupt(
        world,
        lambda c: in_rollback(world) and c.argv[-1].endswith("stop backend </dev/null"),
        KeyboardInterrupt,
    )
    with pytest.raises(KeyboardInterrupt):
        deploy.run(ctx)
    record = latest(ctx, manifest)
    assert record["state"] == records.ROLLBACK_INTERRUPTED and record["ingress_stopped"] is True
    assert record["rollback"]["ingress_may_be_stopped"] is True
    steps = record["rollback"]["steps"]
    assert {"step": "stop ingress", "status": "DONE"} in steps
    assert steps[-1] == {"step": "stop the backend", "status": "STARTED"}
    assert world.containers["frontend"].running is False, "the mock agrees: the site is down"
    assert journal(ctx, manifest)[-1] == "stop the backend"


def test_interrupt_during_the_ingress_stop_itself_is_not_under_reported(tmp_path: Path) -> None:
    ctx, world, manifest = failing_release(tmp_path, ["backend", "frontend"])
    interrupt(
        world,
        lambda c: in_rollback(world) and c.argv[-1].endswith("stop frontend </dev/null"),
        KeyboardInterrupt,
    )
    with pytest.raises(KeyboardInterrupt):
        deploy.run(ctx)
    record = latest(ctx, manifest)
    assert (
        record["rollback"]["ingress_may_be_stopped"] is True and record["ingress_stopped"] is True
    )
    assert record["rollback"]["steps"][-1] == {"step": "stop ingress", "status": "STARTED"}


# -- 3. during service replacement ------------------------------------------------------------


@pytest.mark.parametrize("error", [KeyboardInterrupt, RuntimeError])
def test_interrupt_during_service_replacement(tmp_path: Path, error: type[BaseException]) -> None:
    ctx, world, manifest = failing_release(tmp_path, ["backend", "frontend"])
    interrupt(world, lambda c: in_rollback(world) and " up " in c.argv[-1], error)
    with pytest.raises(error):
        deploy.run(ctx)
    record = latest(ctx, manifest)
    assert record["state"] == records.ROLLBACK_INTERRUPTED
    assert record["rollback"]["steps"][-1]["step"] == "recreate backend on its previous image"
    assert record["rollback"]["steps"][-1]["status"] == "STARTED"
    assert record["stop_code"] == "SMOKE_FAILED", "the original failure is kept"
    assert "rolled back" not in " ".join(record["events"][-3:]).lower()
    assert records.ROLLED_BACK not in result_states(ctx, manifest)


# -- 4. a rollback command fails --------------------------------------------------------------


@pytest.mark.parametrize(
    ("knob", "value", "expected_step"),
    [
        ("up_fails", {"backend"}, "recreate backend on its previous image"),
        ("stop_fails", {"backend"}, "stop the backend"),
        ("stop_fails", {"frontend"}, "stop ingress"),
        ("rollback_runs_wrong_image", True, "recreate backend on its previous image"),
    ],
)
def test_failed_rollback_command_is_held_and_never_claims_restoration(
    tmp_path: Path, knob: str, value: Any, expected_step: str
) -> None:
    ctx, world, manifest = failing_release(tmp_path, ["backend", "frontend"])

    def break_the_rollback(command: Command) -> None:
        if restore_command(command):
            setattr(world, knob, value)

    world.on_command = break_the_rollback
    outcome = deploy.run(ctx)
    assert outcome["state"] == records.FAILED_HELD
    assert outcome["rollback"]["status"] == "FAILED"
    assert outcome["rollback"]["failure"]["code"] == "ROLLBACK_FAILED"
    assert outcome["rollback"]["host_state"] == "unverified"
    assert outcome["rollback"]["steps"][-1] == {"step": expected_step, "status": "STARTED"}
    assert "NOT confirmed restored" in outcome["held_reason"]
    assert outcome["ingress_stopped"] is True
    assert records.ROLLED_BACK not in result_states(ctx, manifest)
    with pytest.raises(StopCondition) as refused:
        deploy.accept(ctx.store, manifest, passed=True, accepted_by="owner", interactive=True)
    assert refused.value.code == "ROLLBACK_INCOMPLETE"


@pytest.mark.parametrize("failure", ["public-health", "another-service"])
def test_rollback_is_not_complete_until_everything_is_healthy_and_the_site_answers(
    tmp_path: Path, failure: str
) -> None:
    ctx, world, manifest = failing_release(tmp_path, ["backend", "frontend"])

    def break_the_final_check(command: Command) -> None:
        if not in_rollback(world):
            return
        if failure == "public-health":
            world.smoke["/health"] = "503"
        elif command.argv[-1].endswith("frontend </dev/null") and " up " in command.argv[-1]:
            world.containers["assistant"].health = "unhealthy"

    world.on_command = break_the_final_check
    outcome = deploy.run(ctx)
    assert outcome["state"] == records.FAILED_HELD and outcome["rollback"]["status"] == "FAILED"
    last = outcome["rollback"]["steps"][-1]
    assert last == {"step": "verify every service and the public health check", "status": "STARTED"}
    assert world.env["BACKEND_IMAGE"] == OLD["backend"], "the images did go back"
    assert "rollback verified" not in " ".join(outcome["events"])


# -- 5 / 8. recovery ---------------------------------------------------------------------------


def test_recover_verifies_a_rollback_that_finished_but_was_interrupted_before_its_record(
    tmp_path: Path,
) -> None:
    ctx, world, manifest = failing_release(tmp_path, ["backend", "frontend"])
    interrupt(world, lambda c: in_rollback(world) and c.argv[0] == "curl", Killed)
    with pytest.raises(Killed):
        deploy.run(ctx)
    assert latest(ctx, manifest)["state"] == records.ROLLBACK_INTERRUPTED
    world.smoke.clear()
    recovered = deploy.recover(
        reader(ctx, world, tmp_path),
        manifest["release_id"],
        recovered_by="operator",
        interactive=True,
    )
    assert recovered["state"] == records.ROLLED_BACK
    assert recovered["rollback"]["status"] == "RECOVERED_VERIFIED_PREVIOUS"
    assert recovered["recovery_attempts"][-1]["conclusion"] == "verified on the previous images"
    assert world.effects(Effect.HOST_WRITE)[-1].purpose == "release the host release lock"


def test_recover_returns_an_untouched_release_to_awaiting_acceptance_only_after_verifying(
    tmp_path: Path,
) -> None:
    ctx, world, manifest = deployed(tmp_path, ["frontend"])
    ctx.approval = rollback_approval(manifest, "110000")
    interrupt(world, lambda c: " sed -i " in c.argv[-1], KeyboardInterrupt)
    with pytest.raises(KeyboardInterrupt):
        deploy.manual_rollback(ctx, manifest["release_id"])
    assert latest(ctx, manifest)["state"] == records.ROLLBACK_INTERRUPTED
    with pytest.raises(StopCondition) as refused:
        deploy.accept(ctx.store, manifest, passed=True, accepted_by="owner", interactive=True)
    assert refused.value.code == "ROLLBACK_INCOMPLETE" and ctx.store.known_good() is None
    writes = len(world.effects(Effect.HOST_WRITE))
    recovered = deploy.recover(
        reader(ctx, world, tmp_path),
        manifest["release_id"],
        recovered_by="operator",
        interactive=True,
    )
    assert recovered["state"] == records.DEPLOYED_AWAITING_ACCEPTANCE
    assert recovered["rollback"]["status"] == "RECOVERED_VERIFIED_ON_RELEASE"
    assert len(world.effects(Effect.HOST_WRITE)) == writes, "recovery reads only"
    accepted = deploy.accept(
        ctx.store, manifest, passed=True, accepted_by="owner", interactive=True
    )
    assert accepted["state"] == records.ACCEPTED and accepted["rollback"]["kind"] == "manual"


def test_incomplete_recovery_stays_unknown_and_acceptance_stays_refused(tmp_path: Path) -> None:
    ctx, world, manifest = failing_release(tmp_path, ["backend", "frontend"])
    interrupt(world, lambda c: in_rollback(world) and " up " in c.argv[-1], KeyboardInterrupt)
    with pytest.raises(KeyboardInterrupt):
        deploy.run(ctx)
    world.smoke.clear()
    for attempt in (1, 2):
        outcome = deploy.recover(
            reader(ctx, world, tmp_path),
            manifest["release_id"],
            recovered_by="operator",
            interactive=True,
        )
        assert outcome["state"] == records.ROLLBACK_INTERRUPTED
        assert outcome["rollback"]["host_state"] == "unknown"
        assert len(outcome["recovery_attempts"]) == attempt
        assert (
            outcome["recovery_attempts"][-1]["conclusion"] == "host state could not be established"
        )
        assert outcome["recovery_attempts"][-1]["services"]["backend"]["position"] == "unknown"
    with pytest.raises(StopCondition) as refused:
        deploy.accept(ctx.store, manifest, passed=True, accepted_by="owner", interactive=True)
    assert refused.value.code == "ROLLBACK_INCOMPLETE"


def test_recovery_with_an_unreadable_host_records_unknown_never_success(tmp_path: Path) -> None:
    ctx, world, manifest = failing_release(tmp_path, ["frontend"])
    interrupt(world, lambda c: in_rollback(world) and " up " in c.argv[-1], Killed)
    with pytest.raises(Killed):
        deploy.run(ctx)
    received = len(world.received)
    outcome = deploy.recover(
        reader(ctx, world, tmp_path, host_reads=False),
        manifest["release_id"],
        recovered_by="operator",
        interactive=True,
    )
    assert len(world.received) == received, "the host could not be read at all"
    assert outcome["state"] == records.ROLLBACK_INTERRUPTED
    assert outcome["rollback"]["host_state"] == "unknown"
    assert outcome["recovery_attempts"][-1]["public_health_200"] is False
    assert "UNKNOWN" in outcome["held_reason"]


def test_recover_is_owner_run_read_only_and_only_for_an_unfinished_rollback(tmp_path: Path) -> None:
    ctx, world, manifest = deployed(tmp_path, ["frontend"])
    with pytest.raises(StopCondition) as not_applicable:
        deploy.recover(ctx, manifest["release_id"], recovered_by="operator", interactive=True)
    assert not_applicable.value.code == "RECOVERY_NOT_APPLICABLE"
    with pytest.raises(StopCondition) as automated:
        deploy.recover(ctx, manifest["release_id"], recovered_by="agent", interactive=False)
    assert automated.value.code == "RECOVERY_NEEDS_OWNER"


def test_recover_does_not_accept_a_site_that_is_on_the_release_but_failing(tmp_path: Path) -> None:
    ctx, world, manifest = failing_release(tmp_path, ["frontend"])
    interrupt(world, restore_command, Killed)
    with pytest.raises(Killed):
        deploy.run(ctx)
    outcome = deploy.recover(
        reader(ctx, world, tmp_path),
        manifest["release_id"],
        recovered_by="operator",
        interactive=True,
    )
    assert outcome["recovery_attempts"][-1]["services"]["frontend"]["position"] == "release"
    assert outcome["state"] == records.ROLLBACK_INTERRUPTED, "the smoke request still fails"


# -- 6. repeated attempts ---------------------------------------------------------------------


def test_repeated_rollback_after_a_failed_automatic_one_succeeds_and_keeps_both_attempts(
    tmp_path: Path,
) -> None:
    ctx, world, manifest = failing_release(tmp_path, ["backend", "frontend"])

    def backend_fails_once(command: Command) -> None:
        if restore_command(command):
            world.up_fails = {"backend"}

    world.on_command = backend_fails_once
    first = deploy.run(ctx)
    assert first["state"] == records.FAILED_HELD and first["rollback"]["attempt"] == 1
    world.on_command, world.up_fails = None, set()
    world.smoke.clear()
    deploy_approval_id = ctx.approval["approval_id"]
    ctx.approval = rollback_approval(manifest, "111000")
    second = deploy.manual_rollback(ctx, manifest["release_id"])
    assert second["state"] == records.ROLLED_BACK
    assert second["rollback"]["attempt"] == 2 and second["rollback"]["kind"] == "manual"
    assert second["rollback"]["status"] == "COMPLETED_VERIFIED"
    assert [a["status"] for a in second["rollback_history"]] == ["FAILED"]
    assert second["rollback_history"][0]["kind"] == "automatic"
    assert second["approval_id"] == deploy_approval_id, "the deploy approval id is preserved"
    assert second["rollback_approval_id"] == ctx.approval["approval_id"]
    assert all(c.running and c.health == "healthy" for c in world.containers.values())
    assert world.containers["backend"].image == world.images[OLD["backend"]]
    with pytest.raises(StopCondition) as done:
        deploy.manual_rollback(ctx, manifest["release_id"])
    assert done.value.code in {"ROLLBACK_NOT_APPLICABLE", "APPROVAL_ALREADY_USED"}


def test_repeated_manual_rollback_after_an_interrupted_one(tmp_path: Path) -> None:
    ctx, world, manifest = deployed(tmp_path, ["backend", "frontend"])
    ctx.approval = rollback_approval(manifest, "112000")
    interrupt(world, lambda c: " up " in c.argv[-1], KeyboardInterrupt)
    with pytest.raises(KeyboardInterrupt):
        deploy.manual_rollback(ctx, manifest["release_id"])
    interrupted = latest(ctx, manifest)
    assert interrupted["state"] == records.ROLLBACK_INTERRUPTED and interrupted["ingress_stopped"]
    assert world.env["BACKEND_IMAGE"] == OLD["backend"], "the pins were already changed back"
    assert not world.containers["frontend"].running
    with pytest.raises(StopCondition) as used:
        deploy.manual_rollback(ctx, manifest["release_id"])
    assert used.value.code == "APPROVAL_ALREADY_USED", "each attempt needs its own approval"
    ctx.approval = rollback_approval(manifest, "112500")
    retried = deploy.manual_rollback(ctx, manifest["release_id"])
    assert retried["state"] == records.ROLLED_BACK and retried["rollback"]["attempt"] == 2
    assert retried["rollback_history"][0]["status"] == "INTERRUPTED"
    assert all(c.running and c.health == "healthy" for c in world.containers.values())
    assert result_states(ctx, manifest) == [
        records.DEPLOYED_AWAITING_ACCEPTANCE,
        records.ROLLBACK_IN_PROGRESS,
        records.ROLLBACK_INTERRUPTED,
        records.ROLLBACK_IN_PROGRESS,
        records.ROLLED_BACK,
    ]


def test_first_manual_attempt_still_refuses_a_host_that_has_moved_on(tmp_path: Path) -> None:
    ctx, world, manifest = deployed(tmp_path, ["frontend"])
    world.env["FRONTEND_IMAGE"] = OLD["frontend"]  # reverted by hand, outside the tool
    ctx.approval = rollback_approval(manifest, "113000")
    with pytest.raises(StopCondition) as refused:
        deploy.manual_rollback(ctx, manifest["release_id"])
    assert refused.value.code == "HOST_STATE_UNEXPECTED"
    assert latest(ctx, manifest)["state"] == records.DEPLOYED_AWAITING_ACCEPTANCE
    assert ctx.store.consumed_approvals() == frozenset(
        {f"{make_approval(manifest)['approval_id']}:deploy"}
    )


# -- 7. accept after an interrupted owner-requested rollback (N2) -----------------------------


@pytest.mark.parametrize(
    "when",
    [
        lambda c: " sed -i " in c.argv[-1],
        lambda c: c.argv[-1].endswith("stop frontend </dev/null"),
        lambda c: " up " in c.argv[-1],
        lambda c: c.argv[0] == "curl",
    ],
    ids=["at-the-unpin", "at-the-ingress-stop", "during-replacement", "at-final-verification"],
)
def test_accept_is_refused_after_an_interrupted_owner_requested_rollback(
    tmp_path: Path, when: Callable[[Command], bool]
) -> None:
    ctx, world, manifest = deployed(tmp_path, ["backend", "frontend"])
    ctx.approval = rollback_approval(manifest, "114000")
    interrupt(world, when, KeyboardInterrupt)
    with pytest.raises(KeyboardInterrupt):
        deploy.manual_rollback(ctx, manifest["release_id"])
    record = latest(ctx, manifest)
    assert record["state"] == records.ROLLBACK_INTERRUPTED
    assert record["state"] != records.DEPLOYED_AWAITING_ACCEPTANCE
    for passed in (True, False):
        with pytest.raises(StopCondition) as refused:
            deploy.accept(ctx.store, manifest, passed=passed, accepted_by="owner", interactive=True)
        assert refused.value.code == "ROLLBACK_INCOMPLETE"
    assert ctx.store.known_good() is None, "the known-good pointer did not move"
    assert world.host_lock is False


def test_manual_rollback_record_is_unacceptable_from_before_its_first_step(tmp_path: Path) -> None:
    ctx, world, manifest = deployed(tmp_path, ["frontend"])
    ctx.approval = rollback_approval(manifest, "115000")
    seen: list[str] = []

    def state_at_first_write(command: Command) -> None:
        if " sed -i " in command.argv[-1] and not seen:
            seen.append(latest(ctx, manifest)["state"])

    world.on_command = state_at_first_write
    assert deploy.manual_rollback(ctx, manifest["release_id"])["state"] == records.ROLLED_BACK
    assert seen == [records.ROLLBACK_IN_PROGRESS]


def test_manual_rollback_never_runs_outside_execute_mode(tmp_path: Path) -> None:
    ctx, world, manifest = deployed(tmp_path, ["frontend"])
    dry = reader(ctx, world, tmp_path)
    dry.approval = rollback_approval(manifest, "115500")
    with pytest.raises(Exception) as refused:
        deploy.manual_rollback(dry, manifest["release_id"])
    assert "only runs with --execute" in str(refused.value)
    assert latest(ctx, manifest)["state"] == records.DEPLOYED_AWAITING_ACCEPTANCE
    assert not any(k.endswith(":rollback") for k in ctx.store.consumed_approvals())


# -- 9. identity is preserved ------------------------------------------------------------------


def test_previous_manifest_and_rollback_identity_survive_an_interrupted_rollback(
    tmp_path: Path,
) -> None:
    manifest = make_manifest(["backend", "frontend"], automatic={"backend": True})
    manifest["previous_known_good"] = {
        "release_id": "rel-0000000-20261101-01",
        "manifest_sha256": "a" * 64,
    }
    world = FakeWorld(manifest)
    world.smoke = {"/": "502"}
    ctx, world = make_context(manifest, tmp_path, world=world)
    interrupt(world, lambda c: in_rollback(world) and " up " in c.argv[-1], KeyboardInterrupt)
    with pytest.raises(KeyboardInterrupt):
        deploy.run(ctx)
    record = latest(ctx, manifest)
    from tools.release.manifest import manifest_hash

    assert record["manifest_sha256"] == manifest_hash(manifest)
    assert record["previous_known_good"] == manifest["previous_known_good"]
    assert record["pins_before"] == {"backend": OLD["backend"], "frontend": OLD["frontend"]}
    assert record["references"]["backend"] == new_reference(manifest, "backend")
    assert record["env_backup"].startswith("/etc/clm/compose.env.pre-rel-")
    assert record["approval_id"] == ctx.approval["approval_id"]
    block = record["rollback"]
    assert block["target_images"] == record["pins_before"]
    assert block["from_images"] == record["references"]
    assert (
        block["services"] == ["backend", "frontend"] and block["env_backup"] == record["env_backup"]
    )
    assert block["approval_id"] == ctx.approval["approval_id"] and block["started_at"]
    assert ctx.store.known_good() is None


# -- 10. audit trail ---------------------------------------------------------------------------


def test_audit_records_after_a_failed_then_interrupted_rollback_are_complete_and_clean(
    tmp_path: Path,
) -> None:
    ctx, world, manifest = failing_release(tmp_path, ["backend", "frontend"])

    def backend_fails(command: Command) -> None:
        if restore_command(command):
            world.up_fails = {"backend"}

    world.on_command = backend_fails
    deploy.run(ctx)
    world.up_fails = set()
    ctx.approval = rollback_approval(manifest, "120000")
    interrupt(world, lambda c: " up " in c.argv[-1], KeyboardInterrupt)
    with pytest.raises(KeyboardInterrupt):
        deploy.manual_rollback(ctx, manifest["release_id"])
    assert result_states(ctx, manifest) == [
        records.ROLLBACK_IN_PROGRESS,
        records.FAILED_HELD,
        records.ROLLBACK_IN_PROGRESS,
        records.ROLLBACK_INTERRUPTED,
    ], "every state is its own numbered file; none was overwritten"
    record = latest(ctx, manifest)
    events = " | ".join(record["events"])
    assert "STOP SMOKE_FAILED" in events and "ROLLBACK STOP ROLLBACK_FAILED" in events
    assert "INTERRUPTED by KeyboardInterrupt" in events
    assert events.count("recorded as in progress before its first step") == 2
    assert record["rollback_history"][0]["failure"]["code"] == "ROLLBACK_FAILED"
    steps = journal(ctx, manifest)
    assert steps[0] == "restore compose.env from the backup" and "stop ingress" in steps
    assert steps.count("recreate backend on its previous image") == 2
    audit = (tmp_path / "audit.jsonl").read_text(encoding="utf-8")
    assert '"purpose": "roll backend back to its previous image"' in audit
    everything = audit + "".join(
        p.read_text(encoding="utf-8") for p in (tmp_path / "state").rglob("*") if p.is_file()
    )
    assert sentinel_token("pull") not in everything and "mongodb" not in everything


# -- re-review N6: safeguards that had no discriminating test ---------------------------------


def test_a_rollback_approval_cannot_be_used_twice(tmp_path: Path) -> None:
    ctx, world, manifest = deployed(tmp_path, ["frontend"])
    ctx.approval = rollback_approval(manifest, "121000")
    interrupt(world, lambda c: " up " in c.argv[-1], KeyboardInterrupt)
    with pytest.raises(KeyboardInterrupt):
        deploy.manual_rollback(ctx, manifest["release_id"])
    writes = len(world.effects(Effect.HOST_WRITE))
    with pytest.raises(StopCondition) as reused:
        deploy.manual_rollback(ctx, manifest["release_id"])
    assert reused.value.code == "APPROVAL_ALREADY_USED"
    assert len(world.effects(Effect.HOST_WRITE)) == writes


def test_execute_stops_when_a_single_preflight_check_could_not_be_read(tmp_path: Path) -> None:
    manifest = make_manifest(["frontend"])
    ctx, world = make_context(manifest, tmp_path)
    real_run = ctx.gate.run

    def clock_unreadable(command: Command) -> Result:
        if command.argv[-1] == "date -u +%s":
            return Result(0, "", "", skipped=True)
        return real_run(command)

    ctx.gate.run = clock_unreadable  # type: ignore[method-assign]
    outcome = deploy.run(ctx)
    assert outcome["stop_code"] == "PREFLIGHT_FAILED"
    assert outcome["stop_message"] == "clock: the check could not be read"
    assert world.effects(Effect.HOST_WRITE) == [] and world.recreated() == []


def test_a_stop_raised_inside_failure_handling_is_recorded_as_held(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = make_manifest(["frontend"])
    world = FakeWorld(manifest)
    world.smoke = {"/": "502"}
    ctx, world = make_context(manifest, tmp_path, world=world)

    def handling_stops(*args: Any) -> dict[str, Any]:
        raise StopCondition("APPROVAL_EXPIRED", "window ended while handling the failure")

    monkeypatch.setattr(deploy, "_stopped", handling_stops)
    outcome = deploy.run(ctx)
    assert outcome["state"] == records.FAILED_HELD and outcome["stop_code"] == "SMOKE_FAILED"
    assert outcome["held_reason"] == "failure handling was itself stopped: APPROVAL_EXPIRED"
    assert latest(ctx, manifest)["state"] == records.FAILED_HELD


def test_rollback_is_not_started_when_its_in_progress_record_cannot_be_written(
    tmp_path: Path,
) -> None:
    ctx, world, manifest = failing_release(tmp_path, ["frontend"])
    real_write = ctx.store.write_result
    calls: list[str] = []

    def disk_full_once(release_id: str, result: dict[str, Any], **kwargs: Any) -> Path:
        calls.append(result["state"])
        if result["state"] == records.ROLLBACK_IN_PROGRESS:
            raise OSError("no space left on device")
        return real_write(release_id, result, **kwargs)

    ctx.store.write_result = disk_full_once  # type: ignore[method-assign]
    outcome = deploy.run(ctx)
    assert outcome["state"] == records.FAILED_HELD
    assert outcome["held_reason"] == "automatic rollback was not started: ROLLBACK_NOT_RECORDED"
    assert outcome["rollback"] is None
    assert not [c for c in world.received if restore_command(c)], "no rollback step was taken"
    assert world.env["FRONTEND_IMAGE"] == new_reference(manifest, "frontend")


def test_automatic_rollback_runs_while_the_host_lock_is_still_held(tmp_path: Path) -> None:
    ctx, world, manifest = failing_release(tmp_path, ["frontend"])
    held: list[bool] = []

    def lock_during_rollback(command: Command) -> None:
        if in_rollback(world) and " up " in command.argv[-1]:
            held.append(world.host_lock)

    world.on_command = lock_during_rollback
    assert deploy.run(ctx)["state"] == records.ROLLED_BACK
    assert held == [True] and world.host_lock is False


# =============================================================================================
# Review of 37f3aa6 (N1_N2_INDEPENDENT_REVIEW.md): findings 1 to 4 and its uncovered mutants
# =============================================================================================


def recover_now(
    ctx: Any, world: FakeWorld, tmp_path: Path, manifest: dict[str, Any]
) -> dict[str, Any]:
    return deploy.recover(
        reader(ctx, world, tmp_path),
        manifest["release_id"],
        recovered_by="operator",
        interactive=True,
    )


def refuse_accept(ctx: Any, manifest: dict[str, Any]) -> str:
    with pytest.raises(StopCondition) as refused:
        deploy.accept(ctx.store, manifest, passed=True, accepted_by="owner", interactive=True)
    return refused.value.code


# -- finding 1 (P1): recover never makes a failed deployment or failed acceptance acceptable ---


@pytest.mark.parametrize(
    ("knob", "value", "stop_code"),
    [
        ("extra_backend", True, "SECOND_BACKEND"),
        ("volume_changes_after_up", True, "VOLUME_IDENTITY_CHANGED"),
        ("restarts_after_up", 3, "HEALTH_CHECK_FAILED"),
    ],
)
def test_recover_keeps_a_deployment_that_stopped_on_a_stop_condition_held(
    tmp_path: Path, knob: str, value: Any, stop_code: str
) -> None:
    manifest = make_manifest(["backend"], automatic={"backend": True})
    world = FakeWorld(manifest)
    setattr(world, knob, value)
    world.restore_fails = True  # the automatic rollback fails at its first step
    ctx, world = make_context(manifest, tmp_path, world=world)
    outcome = deploy.run(ctx)
    assert outcome["state"] == records.FAILED_HELD and outcome["stop_code"] == stop_code
    assert outcome["state_before_rollback"] == deploy.DEPLOYMENT_STOPPED
    world.containers["frontend"].running = True  # ingress started by hand, as the runbook allows
    world.containers["backend"].restarts = 0
    recovered = recover_now(ctx, world, tmp_path, manifest)
    assert recovered["recovery_attempts"][-1]["services"]["backend"]["position"] == "release"
    assert recovered["state"] == records.FAILED_HELD, "healthy on the release is not acceptable"
    assert recovered["rollback"]["status"] == "RECOVERED_ON_RELEASE_NOT_ACCEPTABLE"
    assert (
        stop_code in recovered["held_reason"] and "cannot be accepted" in recovered["held_reason"]
    )
    assert refuse_accept(ctx, manifest) == "ACCEPTANCE_NOT_PENDING"
    assert ctx.store.known_good() is None
    assert records.DEPLOYED_AWAITING_ACCEPTANCE not in result_states(ctx, manifest)


def test_recover_never_turns_a_failed_acceptance_into_an_acceptable_release(tmp_path: Path) -> None:
    ctx, world, manifest = deployed(tmp_path, ["frontend"])
    deploy.accept(ctx.store, manifest, passed=False, accepted_by="owner", interactive=True)
    ctx.approval = rollback_approval(manifest, "130000")
    interrupt(world, lambda c: " sed -i " in c.argv[-1], KeyboardInterrupt)
    with pytest.raises(KeyboardInterrupt):
        deploy.manual_rollback(ctx, manifest["release_id"])
    assert latest(ctx, manifest)["state_before_rollback"] == records.ACCEPTANCE_FAILED
    recovered = recover_now(ctx, world, tmp_path, manifest)
    assert recovered["state"] == records.FAILED_HELD
    assert "ACCEPTANCE_FAILED" in recovered["held_reason"]
    assert (
        refuse_accept(ctx, manifest) == "ACCEPTANCE_NOT_PENDING" and ctx.store.known_good() is None
    )
    ctx.approval = rollback_approval(manifest, "130500")
    assert deploy.manual_rollback(ctx, manifest["release_id"])["state"] == records.ROLLED_BACK


def test_the_origin_state_survives_repeated_attempts(tmp_path: Path) -> None:
    ctx, world, manifest = deployed(tmp_path, ["frontend"])
    for issued in ("131000", "131500"):
        ctx.approval = rollback_approval(manifest, issued)
        interrupt(world, lambda c: " up " in c.argv[-1], KeyboardInterrupt)
        with pytest.raises(KeyboardInterrupt):
            deploy.manual_rollback(ctx, manifest["release_id"])
        record = latest(ctx, manifest)
        assert record["state_before_rollback"] == records.DEPLOYED_AWAITING_ACCEPTANCE
    assert len(record["rollback_history"]) == 1 and record["rollback"]["attempt"] == 2


# -- finding 2 (P2): a transient sharing violation on the state file is retried ---------------


def test_state_file_rename_is_retried_after_a_transient_access_denied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tools.release import core

    real, failures = Path.replace, {"left": 3}

    def flaky(self: Path, target: Any) -> Any:
        if failures["left"]:
            failures["left"] -= 1
            raise PermissionError(13, "Access is denied")
        return real(self, target)

    monkeypatch.setattr(Path, "replace", flaky)
    monkeypatch.setattr(core.time, "sleep", lambda seconds: None)
    core.write_json(tmp_path / "result.json", {"state": "ok"})
    assert json.loads((tmp_path / "result.json").read_text(encoding="utf-8")) == {"state": "ok"}
    assert failures["left"] == 0
    failures["left"] = 10_000
    with pytest.raises(PermissionError):
        core.write_json(tmp_path / "result.json", {"state": "never"})
    assert json.loads((tmp_path / "result.json").read_text(encoding="utf-8")) == {"state": "ok"}


def test_a_rollback_survives_transient_state_file_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tools.release import core

    real, calls = Path.replace, {"n": 0}

    def every_third_fails(self: Path, target: Any) -> Any:
        calls["n"] += 1
        if calls["n"] % 3 == 0:
            raise PermissionError(13, "Access is denied")
        return real(self, target)

    ctx, world, manifest = failing_release(tmp_path, ["backend", "frontend"])
    monkeypatch.setattr(Path, "replace", every_third_fails)
    monkeypatch.setattr(core.time, "sleep", lambda seconds: None)
    outcome = deploy.run(ctx)
    assert outcome["state"] == records.ROLLED_BACK and calls["n"] > 6
    assert all(c.running and c.health == "healthy" for c in world.containers.values())


# -- finding 3 (P2): a service that was pinned but never applied is unpinned too --------------


def partly_applied(tmp_path: Path) -> tuple[Any, FakeWorld, dict[str, Any]]:
    """Backend + frontend release; the backend comes up unhealthy, so only it was applied while
    both lines of compose.env already pin the release. The automatic rollback then fails."""

    manifest = make_manifest(["backend", "frontend"], automatic={"backend": True})
    world = FakeWorld(manifest)
    world.unhealthy_after_up = {"backend"}
    world.restore_fails = True
    ctx, world = make_context(manifest, tmp_path, world=world)
    outcome = deploy.run(ctx)
    assert outcome["state"] == records.FAILED_HELD and outcome["applied"] == ["backend"]
    assert world.env["FRONTEND_IMAGE"] == new_reference(manifest, "frontend")
    world.unhealthy_after_up, world.restore_fails = set(), False
    return ctx, world, manifest


def test_owner_rollback_of_a_partly_applied_release_restores_every_pin(tmp_path: Path) -> None:
    ctx, world, manifest = partly_applied(tmp_path)
    ctx.approval = rollback_approval(manifest, "132000")
    rolled = deploy.manual_rollback(ctx, manifest["release_id"])
    assert rolled["state"] == records.ROLLED_BACK
    assert world.env["BACKEND_IMAGE"] == OLD["backend"]
    assert world.env["FRONTEND_IMAGE"] == OLD["frontend"], (
        "the never-applied service is unpinned too"
    )
    assert world.containers["frontend"].container_id == "frontend-c0", "and was not recreated"
    assert "pin frontend back to its previous image" in journal(ctx, manifest)
    assert all(c.running and c.health == "healthy" for c in world.containers.values())


def test_rollback_is_not_verified_while_any_release_pin_remains(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx, world, manifest = partly_applied(tmp_path)

    def unpin_the_backend_only(ctx_: Any, state: Any, touched: set[str], *, retry: bool) -> None:
        world.env["BACKEND_IMAGE"] = OLD["backend"]  # the frontend line is left on the release

    monkeypatch.setattr(deploy, "_unpin", unpin_the_backend_only)
    ctx.approval = rollback_approval(manifest, "132500")
    outcome = deploy.manual_rollback(ctx, manifest["release_id"])
    assert outcome["state"] == records.FAILED_HELD, (
        "a leftover release pin is not a verified rollback"
    )
    assert outcome["rollback"]["failure"]["message"] == (
        "frontend: compose.env does not show the previous image pin"
    )


# -- finding 4 (P2): recreating the frontend may stop ingress ----------------------------------


def test_frontend_recreate_is_flagged_as_possibly_stopping_ingress(tmp_path: Path) -> None:
    ctx, world, manifest = failing_release(tmp_path, ["frontend"])
    flags: list[bool] = []

    def flag_at_the_up(command: Command) -> None:
        if in_rollback(world) and " up " in command.argv[-1]:
            flags.append(latest(ctx, manifest)["rollback"]["ingress_may_be_stopped"])
            world.up_fails = {"frontend"}

    world.on_command = flag_at_the_up
    outcome = deploy.run(ctx)
    assert flags == [True], "on disk before the command is sent"
    assert outcome["state"] == records.FAILED_HELD and outcome["ingress_stopped"] is True
    assert outcome["rollback"]["ingress_may_be_stopped"] is True


def test_failed_owner_requested_rollback_reports_that_ingress_may_be_stopped(
    tmp_path: Path,
) -> None:
    ctx, world, manifest = deployed(tmp_path, ["backend"])
    ctx.approval = rollback_approval(manifest, "133000")
    world.up_fails = {"backend"}
    outcome = deploy.manual_rollback(ctx, manifest["release_id"])
    assert outcome["state"] == records.FAILED_HELD and outcome["ingress_stopped"] is True
    assert not world.containers["frontend"].running
    assert "NOT confirmed restored" in outcome["held_reason"]


# -- uncovered mutants named by the review -----------------------------------------------------


def rolled_back_but_unrecorded(tmp_path: Path) -> tuple[Any, FakeWorld, dict[str, Any]]:
    ctx, world, manifest = failing_release(tmp_path, ["backend", "frontend"])
    interrupt(world, lambda c: in_rollback(world) and c.argv[0] == "curl", Killed)
    with pytest.raises(Killed):
        deploy.run(ctx)
    world.smoke.clear()
    return ctx, world, manifest


@pytest.mark.parametrize("fault", ["other-container-down", "public-health", "pin-only"])
def test_recover_does_not_report_rolled_back_unless_everything_is_verified(
    tmp_path: Path, fault: str
) -> None:
    ctx, world, manifest = rolled_back_but_unrecorded(tmp_path)
    if fault == "other-container-down":
        world.containers["assistant"].running = False
    elif fault == "public-health":
        world.smoke["/health"] = "503"
    else:  # compose.env shows the previous pin but the container still runs the release image
        world.containers["backend"].image = world.images[new_reference(manifest, "backend")]
    outcome = recover_now(ctx, world, tmp_path, manifest)
    assert outcome["state"] == records.ROLLBACK_INTERRUPTED
    assert outcome["rollback"]["host_state"] == "unknown"
    assert refuse_accept(ctx, manifest) == "ROLLBACK_INCOMPLETE"


def test_recover_applies_to_a_failed_rollback_and_unknown_becomes_interrupted(
    tmp_path: Path,
) -> None:
    ctx, world, manifest = failing_release(tmp_path, ["backend", "frontend"])

    def backend_fails(command: Command) -> None:
        if restore_command(command):
            world.up_fails = {"backend"}

    world.on_command = backend_fails
    held = deploy.run(ctx)
    assert held["state"] == records.FAILED_HELD and held["rollback"]["status"] == "FAILED"
    outcome = recover_now(ctx, world, tmp_path, manifest)
    assert outcome["state"] == records.ROLLBACK_INTERRUPTED, "unknown is its own recorded state"
    assert (
        outcome["rollback"]["status"] == "FAILED" and outcome["rollback"]["host_state"] == "unknown"
    )


def test_retry_is_allowed_from_a_stale_in_progress_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx, world, manifest = failing_release(tmp_path, ["frontend"])
    interrupt(world, lambda c: in_rollback(world) and " up " in c.argv[-1], Killed)
    real = deploy._interrupted

    def no_handler(state: Any, crash: BaseException) -> dict[str, Any]:
        raise Killed()

    monkeypatch.setattr(deploy, "_interrupted", no_handler)
    with pytest.raises(Killed):
        deploy.run(ctx)
    monkeypatch.setattr(deploy, "_interrupted", real)
    assert latest(ctx, manifest)["state"] == records.ROLLBACK_IN_PROGRESS
    world.smoke.clear()
    ctx.approval = rollback_approval(manifest, "134000")
    retried = deploy.manual_rollback(ctx, manifest["release_id"])
    assert retried["state"] == records.ROLLED_BACK and retried["rollback"]["attempt"] == 2
    assert retried["rollback_history"][0]["status"] == "IN_PROGRESS", "the stale attempt is kept"


def test_a_stop_while_handling_a_stop_marks_the_running_rollback_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx, world, manifest = failing_release(tmp_path, ["frontend"])

    def begin_then_escape(ctx_: Any, state: Any, stop: StopCondition) -> dict[str, Any]:
        deploy._begin_rollback(ctx_, state, "automatic")
        raise StopCondition("APPROVAL_EXPIRED", "window ended while rolling back")

    monkeypatch.setattr(deploy, "_stopped", begin_then_escape)
    outcome = deploy.run(ctx)
    assert outcome["state"] == records.FAILED_HELD
    assert outcome["rollback"]["status"] == "FAILED"
    assert outcome["rollback"]["failure"]["code"] == "APPROVAL_EXPIRED"
    assert refuse_accept(ctx, manifest) == "ROLLBACK_INCOMPLETE"


def test_the_in_progress_record_exists_before_the_rollback_approval_is_consumed(
    tmp_path: Path,
) -> None:
    ctx, world, manifest = deployed(tmp_path, ["frontend"])
    ctx.approval = rollback_approval(manifest, "135000")
    seen: list[str] = []
    real_consume = ctx.store.consume_approval

    def consume(approval_id: str, action: str) -> None:
        seen.append(latest(ctx, manifest)["state"])
        raise KeyboardInterrupt()

    ctx.store.consume_approval = consume  # type: ignore[method-assign]
    with pytest.raises(KeyboardInterrupt):
        deploy.manual_rollback(ctx, manifest["release_id"])
    ctx.store.consume_approval = real_consume  # type: ignore[method-assign]
    assert seen == [records.ROLLBACK_IN_PROGRESS]
    record = latest(ctx, manifest)
    assert record["state"] == records.ROLLBACK_INTERRUPTED, "recorded, not left in progress"
    assert world.host_lock is False and world.env["FRONTEND_IMAGE"] != OLD["frontend"]


def test_recovered_record_does_not_keep_a_contradicting_failure_text(tmp_path: Path) -> None:
    ctx, world, manifest = rolled_back_but_unrecorded(tmp_path)
    recovered = recover_now(ctx, world, tmp_path, manifest)
    assert recovered["state"] == records.ROLLED_BACK and "held_reason" not in recovered
    assert "UNKNOWN" in recovered["held_reason_before_recovery"], "kept as evidence, relabelled"


# =============================================================================================
# Fix-check of 84706a9 (N1_N2_FIX_CHECK.md): N-1, N-2, N-3 and its test gaps
# =============================================================================================


def test_a_failed_acceptance_is_permanent_across_rollback_episodes(tmp_path: Path) -> None:
    """deploy, rollback interrupted, recover, accept FAIL, rollback interrupted, recover:
    the release must not come back as acceptable, and accept(pass) must not succeed."""

    ctx, world, manifest = deployed(tmp_path, ["frontend"])
    ctx.approval = rollback_approval(manifest, "140000")
    interrupt(world, lambda c: " sed -i " in c.argv[-1], KeyboardInterrupt)
    with pytest.raises(KeyboardInterrupt):
        deploy.manual_rollback(ctx, manifest["release_id"])
    assert (
        recover_now(ctx, world, tmp_path, manifest)["state"] == records.DEPLOYED_AWAITING_ACCEPTANCE
    )
    failed = deploy.accept(ctx.store, manifest, passed=False, accepted_by="owner", interactive=True)
    assert failed["state"] == records.ACCEPTANCE_FAILED and failed["acceptance_failed"] is True
    ctx.approval = rollback_approval(manifest, "140500")
    interrupt(world, lambda c: " sed -i " in c.argv[-1], KeyboardInterrupt)
    with pytest.raises(KeyboardInterrupt):
        deploy.manual_rollback(ctx, manifest["release_id"])
    second = latest(ctx, manifest)
    assert second["state_before_rollback"] == records.ACCEPTANCE_FAILED, (
        "a new episode, a new origin"
    )
    recovered = recover_now(ctx, world, tmp_path, manifest)
    assert recovered["state"] == records.FAILED_HELD
    assert recovered["rollback"]["status"] == "RECOVERED_ON_RELEASE_NOT_ACCEPTABLE"
    assert refuse_accept(ctx, manifest) in {"ACCEPTANCE_NOT_PENDING", "ACCEPTANCE_ALREADY_FAILED"}
    assert ctx.store.known_good() is None
    assert records.ACCEPTED not in result_states(ctx, manifest)


def test_accept_refuses_a_release_that_already_failed_acceptance_whatever_its_state(
    tmp_path: Path,
) -> None:
    ctx, world, manifest = deployed(tmp_path, ["frontend"])
    deploy.accept(ctx.store, manifest, passed=False, accepted_by="owner", interactive=True)
    record = latest(ctx, manifest)
    forged = {**record, "state": records.DEPLOYED_AWAITING_ACCEPTANCE}
    forged.pop("recorded_at", None)
    ctx.store.write_result(manifest["release_id"], forged)
    assert refuse_accept(ctx, manifest) == "ACCEPTANCE_ALREADY_FAILED"
    assert ctx.store.known_good() is None


def test_recover_does_not_return_a_release_with_a_recorded_stop_code_to_acceptance(
    tmp_path: Path,
) -> None:
    ctx, world, manifest = deployed(tmp_path, ["frontend"])
    ctx.approval = rollback_approval(manifest, "141000")
    interrupt(world, lambda c: " sed -i " in c.argv[-1], KeyboardInterrupt)
    with pytest.raises(KeyboardInterrupt):
        deploy.manual_rollback(ctx, manifest["release_id"])
    record = latest(ctx, manifest)
    record.pop("recorded_at", None)
    ctx.store.write_result(manifest["release_id"], {**record, "stop_code": "SMOKE_FAILED"})
    assert recover_now(ctx, world, tmp_path, manifest)["state"] == records.FAILED_HELD


def test_rollback_is_not_verified_while_a_never_applied_service_runs_the_release_image(
    tmp_path: Path,
) -> None:
    ctx, world, manifest = partly_applied(tmp_path)
    # Someone ran `docker compose up frontend` by hand while the file still pinned the release.
    world.containers["frontend"].image = world.images.setdefault(
        new_reference(manifest, "frontend"), "sha256:" + "5" * 64
    )
    ctx.approval = rollback_approval(manifest, "142000")
    outcome = deploy.manual_rollback(ctx, manifest["release_id"])
    assert outcome["state"] == records.FAILED_HELD
    assert outcome["rollback"]["failure"]["message"] == (
        "frontend: the container is not running its previous image"
    )
    assert records.ROLLED_BACK not in result_states(ctx, manifest)


@pytest.mark.parametrize("mode", [Mode.EXECUTE, Mode.DRY_RUN])
def test_a_new_run_never_replaces_the_record_of_an_unfinished_rollback(
    tmp_path: Path, mode: Mode
) -> None:
    ctx, world, manifest = failing_release(tmp_path, ["frontend"])
    interrupt(world, lambda c: in_rollback(world) and " up " in c.argv[-1], KeyboardInterrupt)
    with pytest.raises(KeyboardInterrupt):
        deploy.run(ctx)
    before = latest(ctx, manifest)
    files = result_states(ctx, manifest)
    received = len(world.received)
    again = make_context(
        manifest,
        tmp_path,
        mode=mode,
        world=world,
        approval=make_approval(manifest, issued="143000"),
    )[0]
    with pytest.raises(StopCondition) as refused:
        deploy.run(again)
    assert refused.value.code == "ROLLBACK_INCOMPLETE"
    assert latest(ctx, manifest) == before and result_states(ctx, manifest) == files
    assert len(world.received) == received, "nothing was contacted"
    assert not (ctx.store.root / "release.lock").exists()
    assert recover_now(ctx, world, tmp_path, manifest)["state"] == records.ROLLBACK_INTERRUPTED


def test_first_attempt_accepts_the_previous_pin_only_for_a_never_applied_service(
    tmp_path: Path,
) -> None:
    ctx, world, manifest = partly_applied(tmp_path)
    world.env["FRONTEND_IMAGE"] = OLD["frontend"]  # never applied, already put back by hand
    world.containers["frontend"].label_hash = world._hash("frontend")
    ctx.approval = rollback_approval(manifest, "144000")
    assert deploy.manual_rollback(ctx, manifest["release_id"])["state"] == records.ROLLED_BACK
    assert "pin frontend back to its previous image" not in journal(ctx, manifest)


def test_a_never_applied_service_on_neither_pin_refuses_the_rollback(tmp_path: Path) -> None:
    ctx, world, manifest = partly_applied(tmp_path)
    world.env["FRONTEND_IMAGE"] = OLD["frontend"][:-4] + "cafe"  # another release pinned it
    writes = len(world.effects(Effect.HOST_WRITE))
    ctx.approval = rollback_approval(manifest, "144500")
    with pytest.raises(StopCondition) as refused:
        deploy.manual_rollback(ctx, manifest["release_id"])
    assert refused.value.code == "HOST_STATE_UNEXPECTED" and "frontend" in refused.value.message
    assert len(world.effects(Effect.HOST_WRITE)) == writes


def test_journal_append_is_retried_after_a_transient_access_denied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import builtins

    from tools.release import records as records_module

    store = records_module.StateStore(tmp_path / "state")
    store.write_result("rel-0000000-20261114-01", {"state": "ROLLBACK_IN_PROGRESS"})
    real_open, failures = Path.open, {"left": 2}

    def flaky_open(self: Path, *args: Any, **kwargs: Any) -> Any:
        if self.name == "rollback-journal.jsonl" and failures["left"]:
            failures["left"] -= 1
            raise PermissionError(13, "Access is denied")
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", flaky_open)
    monkeypatch.setattr(records_module.time, "sleep", lambda seconds: None)
    store.journal("rel-0000000-20261114-01", {"step": "stop ingress"}, {"status": "IN_PROGRESS"})
    assert failures["left"] == 0 and builtins is not None
    lines = (
        (store.release_dir("rel-0000000-20261114-01") / "rollback-journal.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    assert len(lines) == 1 and json.loads(lines[0])["step"] == "stop ingress"
    failures["left"] = 10_000
    with pytest.raises(PermissionError):
        store.journal("rel-0000000-20261114-01", {"step": "never"}, {"status": "IN_PROGRESS"})


def test_recover_does_not_return_a_release_marked_as_failed_acceptance_to_acceptance(
    tmp_path: Path,
) -> None:
    """Belt and braces: even if the episode origin said "awaiting acceptance", a recorded
    failed acceptance keeps the release held."""

    ctx, world, manifest = deployed(tmp_path, ["frontend"])
    ctx.approval = rollback_approval(manifest, "145000")
    interrupt(world, lambda c: " sed -i " in c.argv[-1], KeyboardInterrupt)
    with pytest.raises(KeyboardInterrupt):
        deploy.manual_rollback(ctx, manifest["release_id"])
    record = latest(ctx, manifest)
    assert record["state_before_rollback"] == records.DEPLOYED_AWAITING_ACCEPTANCE
    record.pop("recorded_at", None)
    ctx.store.write_result(manifest["release_id"], {**record, "acceptance_failed": True})
    recovered = recover_now(ctx, world, tmp_path, manifest)
    assert recovered["state"] == records.FAILED_HELD
    assert recovered["rollback"]["status"] == "RECOVERED_ON_RELEASE_NOT_ACCEPTABLE"


# =============================================================================================
# Final check of 6bcf142 (N1_N2_FINAL_CHECK.md): F-1, F-2 and its test gaps
# =============================================================================================


def test_a_new_verified_deployment_after_a_verified_rollback_carries_the_acceptance_history(
    tmp_path: Path,
) -> None:
    """A failed acceptance is permanent for that deployment. A new, complete, verified
    deployment under a new owner approval is a new deployment: it may be accepted, and its
    record says that an earlier deployment of this release failed acceptance."""

    ctx, world, manifest = deployed(tmp_path, ["frontend"])
    deploy.accept(ctx.store, manifest, passed=False, accepted_by="owner", interactive=True)
    ctx.approval = rollback_approval(manifest, "150000")
    assert deploy.manual_rollback(ctx, manifest["release_id"])["state"] == records.ROLLED_BACK
    refusal = refuse_accept(ctx, manifest)  # rolled back: nothing is awaiting acceptance
    assert refusal in {"ACCEPTANCE_NOT_PENDING", "ACCEPTANCE_ALREADY_FAILED"}
    ctx.approval = make_approval(manifest, issued="151000")  # a new owner deploy approval
    again = deploy.run(ctx)
    assert again["state"] == records.DEPLOYED_AWAITING_ACCEPTANCE
    assert again["previously_failed_acceptance"] is True and "acceptance_failed" not in again
    accepted = deploy.accept(
        ctx.store, manifest, passed=True, accepted_by="owner", interactive=True
    )
    assert (
        accepted["state"] == records.ACCEPTED and accepted["previously_failed_acceptance"] is True
    )
    assert records.ACCEPTANCE_FAILED in result_states(ctx, manifest), "the history is kept"


@pytest.mark.parametrize("mode", [Mode.EXECUTE, Mode.DRY_RUN])
@pytest.mark.parametrize("standing", ["awaiting", "acceptance-failed", "held"])
def test_a_run_that_changes_nothing_never_replaces_the_standing_record_of_a_live_release(
    tmp_path: Path, mode: Mode, standing: str
) -> None:
    if standing == "held":
        manifest = make_manifest(["assistant"])
        world = FakeWorld(manifest)
        world.unhealthy_after_up = {"assistant"}
        ctx, world = make_context(manifest, tmp_path, world=world)
        assert deploy.run(ctx)["state"] == records.FAILED_HELD
        world.unhealthy_after_up = set()
    else:
        ctx, world, manifest = deployed(tmp_path, ["frontend"])
        if standing == "acceptance-failed":
            deploy.accept(ctx.store, manifest, passed=False, accepted_by="owner", interactive=True)
    before = latest(ctx, manifest)
    files = len(result_states(ctx, manifest))
    writes = len(world.effects(Effect.HOST_WRITE))
    again = make_context(
        manifest,
        tmp_path,
        mode=mode,
        world=world,
        approval=make_approval(manifest, issued="152000"),
    )[0]
    outcome = deploy.run(again)
    assert outcome["state"] in {records.FAILED_NO_CHANGE, records.DRY_RUN_OK}
    assert outcome["standing_record_kept"] == before["state"]
    assert latest(ctx, manifest) == before, "the standing record still describes the host"
    assert len(result_states(ctx, manifest)) == files + 1, "the attempt itself is kept"
    assert [c for c in world.effects(Effect.HOST_WRITE)[writes:] if " up " in c.argv[-1]] == []
    if standing == "awaiting":
        accepted = deploy.accept(
            ctx.store, manifest, passed=True, accepted_by="owner", interactive=True
        )
        assert accepted["state"] == records.ACCEPTED
    elif standing == "acceptance-failed":
        assert latest(ctx, manifest)["acceptance_failed"] is True
        ctx.approval = rollback_approval(manifest, "153000")
        assert deploy.manual_rollback(ctx, manifest["release_id"])["state"] == records.ROLLED_BACK


def test_a_new_run_is_refused_over_a_held_record_whose_rollback_failed(tmp_path: Path) -> None:
    ctx, world, manifest = failing_release(tmp_path, ["frontend"])

    def frontend_fails(command: Command) -> None:
        if restore_command(command):
            world.up_fails = {"frontend"}

    world.on_command = frontend_fails
    held = deploy.run(ctx)
    assert held["state"] == records.FAILED_HELD and held["rollback"]["status"] == "FAILED"
    world.on_command = None
    received = len(world.received)
    with pytest.raises(StopCondition) as refused:
        deploy.run(reader(ctx, world, tmp_path))
    assert refused.value.code == "ROLLBACK_INCOMPLETE" and len(world.received) == received
    assert latest(ctx, manifest)["state"] == records.FAILED_HELD


def test_recover_needs_the_awaiting_acceptance_origin_even_without_other_marks(
    tmp_path: Path,
) -> None:
    ctx, world, manifest = deployed(tmp_path, ["frontend"])
    ctx.approval = rollback_approval(manifest, "154000")
    interrupt(world, lambda c: " sed -i " in c.argv[-1], KeyboardInterrupt)
    with pytest.raises(KeyboardInterrupt):
        deploy.manual_rollback(ctx, manifest["release_id"])
    record = latest(ctx, manifest)
    record.pop("recorded_at", None)
    assert not record.get("stop_code") and not record.get("acceptance_failed")
    ctx.store.write_result(
        manifest["release_id"], {**record, "state_before_rollback": "FAILED_HELD"}
    )
    assert recover_now(ctx, world, tmp_path, manifest)["state"] == records.FAILED_HELD
