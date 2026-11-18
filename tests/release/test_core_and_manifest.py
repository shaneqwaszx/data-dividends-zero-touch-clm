"""Gate, secrets, manifest rules, overlays and approvals (no host, no registry, no Docker)."""

from __future__ import annotations

import copy
import json
from datetime import timedelta
from pathlib import Path

import pytest

from tools.release import approval as approvals
from tools.release import catalog
from tools.release import manifest as manifests
from tools.release.core import (
    AuditLog,
    Command,
    Effect,
    Gate,
    Mode,
    ReleaseError,
    Result,
    Secret,
    StopCondition,
    assert_remote_allowed,
    read_json,
    redact,
)

from .fakes import NOW, SAMPLE, Clock, make_approval, make_manifest, sentinel_token


class Recorder:
    def __init__(self) -> None:
        self.seen: list[Command] = []

    def run(self, command: Command) -> Result:
        self.seen.append(command)
        return Result(0, "ok")


def gate(mode: Mode, **kwargs: object) -> tuple[Gate, Recorder, AuditLog]:
    runner, log = Recorder(), AuditLog()
    return Gate(runner, mode, log, **kwargs), runner, log  # type: ignore[arg-type]


# -- secrets ---------------------------------------------------------------------------------


def test_secret_cannot_be_printed_formatted_or_pickled() -> None:
    import pickle

    token = sentinel_token()
    secret = Secret(token)
    assert token not in repr(secret) + str(secret) + f"{secret}" + f"{secret!r}"
    with pytest.raises(TypeError):
        pickle.dumps(secret)


def test_redaction_removes_registered_and_patterned_secrets() -> None:
    token = sentinel_token("redact")
    Secret(token)
    import base64

    encoded = base64.b64encode(token.encode()).decode()
    database = "mongodb" + "://user:" + "pw" + "@mongo/clm"
    text = redact(
        f"login {token} auth {encoded} uri {database} " + "Authori" + "zation: Bearer abc.def"
    )
    assert token not in text and encoded not in text
    assert "user:" not in text and "abc.def" not in text


def test_gate_refuses_secret_in_argument_or_environment() -> None:
    token = sentinel_token("argv")
    Secret(token)
    g, runner, _ = gate(Mode.EXECUTE)
    with pytest.raises(StopCondition) as argument:
        g.run(Command(("docker", "login", "-p", token), Effect.REGISTRY_WRITE, "bad"))
    assert argument.value.code == "SECRET_IN_ARGUMENT"
    with pytest.raises(StopCondition) as environment:
        g.run(Command(("docker", "push"), Effect.REGISTRY_WRITE, "bad", env={"X": token}))
    assert environment.value.code == "SECRET_IN_ENVIRONMENT"
    assert runner.seen == []
    assert token not in str(argument.value) + str(environment.value)


def test_audit_log_never_holds_a_secret(tmp_path: Path) -> None:
    token = sentinel_token("log")
    secret = Secret(token)

    class Leaky:
        def run(self, command: Command) -> Result:
            return Result(1, f"echo {token}", f"failed with {token}")

    log = AuditLog(path=tmp_path / "audit.jsonl")
    g = Gate(Leaky(), Mode.EXECUTE, log)
    result = g.run(Command(("docker", "login"), Effect.REGISTRY_WRITE, "login", stdin=secret))
    log.event("note", value=secret, nested={"k": [token]})
    written = (tmp_path / "audit.jsonl").read_text(encoding="utf-8")
    assert token not in written + result.stdout + result.stderr + json.dumps(log.events)


# -- modes -----------------------------------------------------------------------------------

WRITES = (Effect.HOST_WRITE, Effect.REGISTRY_WRITE)


@pytest.mark.parametrize("mode", [Mode.PLAN_ONLY, Mode.DRY_RUN, Mode.LOCAL])
def test_non_executing_modes_never_issue_a_host_or_registry_write(mode: Mode) -> None:
    g, runner, _ = gate(mode)
    for effect in WRITES:
        result = g.run(Command(("ssh", "h", "--", "true"), effect, "write"))
        assert result.skipped and not result.ok
    assert runner.seen == []
    assert [c.effect for c in g.skipped] == list(WRITES)


def test_plan_only_reads_nothing_remote_and_local_mode_never_leaves_this_machine() -> None:
    for mode in (Mode.PLAN_ONLY, Mode.LOCAL):
        g, runner, _ = gate(mode)
        for effect in (Effect.HOST_READ, Effect.REGISTRY_READ, Effect.PUBLIC_READ):
            assert g.run(Command(("ssh", "h", "--", "true"), effect, "read")).skipped
        assert runner.seen == []


def test_dry_run_offline_skips_host_reads() -> None:
    g, runner, _ = gate(Mode.DRY_RUN, host_reads=False)
    assert g.run(Command(("ssh", "h", "--", "true"), Effect.HOST_READ, "read")).skipped
    assert runner.seen == []


@pytest.mark.parametrize("mode", list(Mode))
def test_provider_call_is_refused_in_every_mode(mode: Mode) -> None:
    g, runner, _ = gate(mode)
    with pytest.raises(StopCondition) as refused:
        g.run(Command(("curl", "https://api.anthropic.com"), Effect.PROVIDER_CALL, "inference"))
    assert refused.value.code == "PROVIDER_CALL_REFUSED" and runner.seen == []


@pytest.mark.parametrize(
    "remote",
    [
        "cd /opt/clm && sudo -n docker compose -f deploy/compose.yml down",
        "sudo -n docker compose -f a.yml up -d --remove-orphans frontend",
        "sudo -n docker compose -f a.yml down -v",
        "sudo -n docker compose -f a.yml up -d -v frontend",
        "sudo -n docker volume rm clm-mongo-data",
        "sudo -n docker volume prune -f",
        "sudo -n docker system prune -af",
        "sudo -n docker compose -f a.yml up -d --scale backend=2 backend",
        "sudo -n docker compose -f a.yml run backend sh",
        "sudo -n docker compose -f a.yml rm -s -f assistant",
        "sudo -n docker compose -f a.yml build",
        "sudo -n docker rm -f clm-staging-backend",
        "sudo -n docker run --rm alpine",
        "mongodump --archive=/tmp/x",
        "sudo nft flush ruleset",
        "sudo iptables -F",
        "sudo systemctl restart docker",
        "sudo reboot",
    ],
)
def test_forbidden_host_commands_are_refused_before_they_run(remote: str) -> None:
    g, runner, _ = gate(Mode.EXECUTE)
    with pytest.raises(StopCondition) as refused:
        g.run(Command(("ssh", "host", "--", remote), Effect.HOST_WRITE, "forbidden"))
    assert refused.value.code == "FORBIDDEN_HOST_COMMAND" and runner.seen == []
    with pytest.raises(StopCondition):
        assert_remote_allowed(remote)


def test_expired_deadline_stops_the_next_write_but_not_housekeeping() -> None:
    clock = Clock()
    manifest = make_manifest(["frontend"])
    record = make_approval(manifest)
    g, runner, _ = gate(Mode.EXECUTE)
    g.set_deadline(approvals.deadline(record, clock))
    assert g.run(Command(("ssh", "h", "--", "true"), Effect.HOST_WRITE, "ok")).ok
    clock.advance(hours=3)
    with pytest.raises(StopCondition) as expired:
        g.run(Command(("ssh", "h", "--", "true"), Effect.HOST_WRITE, "late"))
    assert expired.value.code == "APPROVAL_EXPIRED"
    unlock = Command(("ssh", "h", "--", "true"), Effect.HOST_WRITE, "unlock", housekeeping=True)
    assert g.run(unlock).ok and len(runner.seen) == 2


# -- manifest --------------------------------------------------------------------------------


def test_sample_manifest_is_valid_and_matches_the_json_schema_package() -> None:
    sample = read_json(SAMPLE)
    manifests.validate_manifest(sample)
    assert sample["images"]["backend"]["snapshot_schema_writes"] == 20
    assert all(i["registry_manifest_digest"] is None for i in sample["images"].values())
    jsonschema = pytest.importorskip("jsonschema")
    schema = read_json(manifests.MANIFEST_SCHEMA)
    jsonschema.Draft202012Validator(schema).validate(sample)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda m: m.pop("rollback"),
        lambda m: m.__setitem__("risk_class", "TRIVIAL"),
        lambda m: m["source"].__setitem__("commit", "d0142d8"),
        lambda m: m["source"].__setitem__("clean", False),
        lambda m: m["images"]["frontend"].__setitem__("platform", "linux/arm64"),
        lambda m: m["images"]["frontend"]["build"].__setitem__("rebuilt_after_qualification", True),
        lambda m: m.__setitem__("unexpected", 1),
        lambda m: m["images"]["backend"].__setitem__("local_image_id", "sha256:abc"),
        lambda m: m.__setitem__("services_changed", []),
        lambda m: m["rollback"]["frontend"].__setitem__("stop_conditions", []),
    ],
)
def test_built_in_validator_agrees_with_jsonschema_on_invalid_documents(mutate: object) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = read_json(manifests.MANIFEST_SCHEMA)
    document = read_json(SAMPLE)
    mutate(document)  # type: ignore[operator]
    ours = manifests.schema_errors(document, schema, schema)
    theirs = list(jsonschema.Draft202012Validator(schema).iter_errors(document))
    assert ours and theirs
    with pytest.raises(ReleaseError):
        manifests.validate_manifest(document)


def test_manifest_hash_is_stable_and_changes_with_content() -> None:
    first = make_manifest(["frontend"])
    second = json.loads(json.dumps(first))
    assert manifests.manifest_hash(first) == manifests.manifest_hash(second)
    second["images"]["frontend"]["local_image_id"] = "sha256:" + "0" * 64
    assert manifests.manifest_hash(first) != manifests.manifest_hash(second)


def test_risk_class_cannot_be_declared_below_the_content() -> None:
    for services, floor in (
        (["frontend"], "LOW"),
        (["assistant"], "MEDIUM"),
        (["backend"], "HIGH"),
    ):
        assert manifests.minimum_risk(make_manifest(services))[0] == floor
    low_backend = make_manifest(["backend"])
    low_backend["risk_class"] = "LOW"
    with pytest.raises(StopCondition) as refused:
        manifests.validate_manifest(low_backend)
    assert refused.value.code == "RISK_CLASS_TOO_LOW"


@pytest.mark.parametrize(
    ("delta", "expected"),
    [
        ({"networks": ["assistant-uplink"]}, "HIGH"),
        ({"ports": ["8100:8100/tcp"]}, "HIGH"),
        ({"environment": ["ASSISTANT_HOSTING_PROVIDER"]}, "HIGH"),
        ({"environment": ["ASSISTANT_NEW_LIMIT"]}, "MEDIUM"),
        ({"settings": ["restart"]}, "HIGH"),
    ],
)
def test_declared_config_changes_raise_the_risk_class(delta: dict, expected: str) -> None:
    manifest = make_manifest(["assistant"], risk="HIGH")
    manifest["declared_config_changes"] = {"assistant": delta}
    assert manifests.minimum_risk(manifest)[0] == expected


def test_assistant_with_provider_overlay_and_sensitive_change_classes_are_high() -> None:
    hosted = make_manifest(["assistant"], risk="HIGH", active=("assistant", "assistant-provider"))
    hosted["overlay"]["validation_set"] = "assistant-provider"
    hosted["overlay"]["order"] = list(catalog.overlay_files("assistant-provider"))
    assert manifests.minimum_risk(hosted)[0] == "HIGH"
    persistence = make_manifest(["frontend"], risk="HIGH")
    persistence["change_classes"] = ["PERSISTENCE"]
    assert manifests.minimum_risk(persistence)[0] == "HIGH"


def test_schema_19_backend_is_never_an_eligible_rollback_target() -> None:
    manifest = make_manifest(["backend"])
    entry = manifest["rollback"]["backend"]
    entry.update(target_source_commit="4c1db49", automatic=False)
    with pytest.raises(StopCondition) as by_commit:
        manifests.validate_manifest(manifest)
    assert by_commit.value.code == "ROLLBACK_SCHEMA_INCOMPATIBLE"
    entry.update(target_source_commit="149c11e", target_snapshot_schema_writes=19)
    with pytest.raises(StopCondition) as by_version:
        manifests.validate_manifest(manifest)
    assert by_version.value.code == "ROLLBACK_SCHEMA_INCOMPATIBLE"
    entry["data_compatible"] = False
    manifests.validate_manifest(manifest)
    assert manifests.rollback_eligibility(manifest, "backend")[0] is False


def test_automatic_rollback_needs_proof() -> None:
    unproven = make_manifest(["assistant"])
    unproven["rollback"]["assistant"].update(automatic=True, data_compatible="unproven")
    with pytest.raises(StopCondition) as refused:
        manifests.validate_manifest(unproven)
    assert refused.value.code == "ROLLBACK_NOT_PROVEN"
    backend = make_manifest(["backend"])
    backend["rollback"]["backend"].update(automatic=True, target_confirmed_on_host=False)
    with pytest.raises(StopCondition):
        manifests.validate_manifest(backend)
    backend["rollback"]["backend"].update(target_snapshot_schema_writes=None)
    with pytest.raises(StopCondition):
        manifests.validate_manifest(backend)
    assert manifests.rollback_eligibility(make_manifest(["frontend"]), "frontend")[0] is True
    assert manifests.rollback_eligibility(make_manifest(["assistant"]), "assistant")[0] is False


def test_floating_rollback_target_and_mongo_release_are_refused() -> None:
    floating = make_manifest(["frontend"])
    floating["rollback"]["frontend"]["target_image"] = (
        "ghcr.io/shaneqwaszx/clm-aws-demo-frontend:latest"
    )
    with pytest.raises(StopCondition) as tag:
        manifests.validate_manifest(floating)
    assert tag.value.code == "FLOATING_REFERENCE"
    mongo = make_manifest(["frontend"], risk="HIGH")
    mongo["services_changed"] = ["mongo"]
    mongo["services_unchanged"] = ["frontend", "backend", "assistant"]
    with pytest.raises(StopCondition) as never:
        manifests.validate_manifest(mongo)
    assert never.value.code == "SERVICE_NOT_RELEASABLE"


def test_new_frontend_without_its_backend_is_refused() -> None:
    manifest = make_manifest(["frontend"])
    manifest["coupling"] = [
        {
            "service": "frontend",
            "requires": "backend",
            "satisfied_by": "this-release",
            "reason": "x",
        }
    ]
    with pytest.raises(StopCondition) as refused:
        manifests.validate_manifest(manifest)
    assert refused.value.code == "COUPLED_SERVICE_MISSING"


def test_image_that_differs_from_the_commit_or_is_unreviewed_cannot_be_published() -> None:
    manifest = make_manifest(["frontend"])
    manifest["images"]["frontend"]["file_equality"]["status"] = "FAIL"
    with pytest.raises(StopCondition) as differs:
        manifests.validate_manifest(manifest)
    assert differs.value.code == "IMAGE_CONTENT_MISMATCH"
    for verdict in ("FAIL", "NOT RUN"):
        unreviewed = make_manifest(["frontend"])
        unreviewed["quality_gates"][0]["verdict"] = verdict
        with pytest.raises(StopCondition) as gate_stop:
            manifests.require_publishable(unreviewed, ["frontend"])
        assert gate_stop.value.code == "QG_NOT_PASSED"
    unpublished = make_manifest(["frontend"], published=False)
    with pytest.raises(StopCondition) as digest_stop:
        manifests.require_deployable(unpublished, transfer="pull")
    assert digest_stop.value.code == "REGISTRY_DIGEST_UNKNOWN"


def test_runtime_reference_is_a_digest_never_a_floating_tag() -> None:
    manifest = make_manifest(["frontend"])
    reference = manifests.image_reference(manifest, "frontend", transfer="pull")
    assert "@sha256:" in reference and ":latest" not in reference
    tag = manifests.release_tag(manifest, "frontend")
    assert tag.startswith("rc-d0142d8e8d74-") and len(tag) == 28


# -- overlays --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("files", "code"),
    [
        ((catalog.COMPOSE_BASE,), "OVERLAY_SET_UNSUPPORTED"),
        ((catalog.COMPOSE_BASE, catalog.COMPOSE_ASSISTANT), "OVERLAY_SET_UNSUPPORTED"),
        ((catalog.COMPOSE_MONGO, catalog.COMPOSE_BASE), "OVERLAY_ORDER"),
        (
            (catalog.COMPOSE_BASE, catalog.COMPOSE_MONGO, catalog.COMPOSE_PROVIDER),
            "OVERLAY_SET_UNSUPPORTED",
        ),
        (
            (
                catalog.COMPOSE_BASE,
                catalog.COMPOSE_MONGO,
                catalog.COMPOSE_PROVIDER,
                catalog.COMPOSE_ASSISTANT,
            ),
            "OVERLAY_ORDER",
        ),
        (
            (
                catalog.COMPOSE_BASE,
                catalog.COMPOSE_MONGO,
                catalog.COMPOSE_GOLDTIER,
                catalog.COMPOSE_ASSISTANT,
            ),
            "OVERLAY_ORDER",
        ),
        ((catalog.COMPOSE_BASE, catalog.COMPOSE_MONGO, catalog.COMPOSE_MONGO), "OVERLAY_DUPLICATE"),
        (
            (catalog.COMPOSE_BASE, catalog.COMPOSE_MONGO, "deploy/compose.extra.yml"),
            "OVERLAY_UNKNOWN_FILE",
        ),
    ],
)
def test_unsupported_overlay_combinations_are_refused(files: tuple[str, ...], code: str) -> None:
    with pytest.raises(StopCondition) as refused:
        catalog.resolve_overlay_files(files)
    assert refused.value.code == code


def test_wrappers_follow_the_runbook_and_refuse_absent_overlays() -> None:
    assert catalog.wrapper_set_for("frontend", ("assistant", "goldtier")) == "base"
    assert catalog.wrapper_set_for("assistant", ("assistant", "goldtier")) == "assistant"
    assert catalog.wrapper_set_for("backend", ("assistant", "goldtier")) == "goldtier"
    assert catalog.wrapper_set_for("backend", ("assistant",)) == "base"
    for service, active in (
        ("assistant", ()),
        ("assistant", ("assistant-provider",)),
        ("goldtier-egress", ("assistant",)),
        ("frontend", ("kubernetes",)),
    ):
        with pytest.raises(StopCondition):
            catalog.wrapper_set_for(service, active)
    manifest = make_manifest(["assistant"], active=())
    with pytest.raises(StopCondition):
        manifests.validate_manifest(manifest)


def test_manifest_overlay_order_must_be_the_supported_one() -> None:
    manifest = make_manifest(["frontend"])
    manifest["overlay"]["order"] = list(reversed(manifest["overlay"]["order"]))
    with pytest.raises(StopCondition):
        manifests.validate_manifest(manifest)


# -- approvals -------------------------------------------------------------------------------


def check(manifest: dict, record: dict, clock: Clock, **kwargs: object) -> None:
    approvals.check_approval(
        record,
        manifest,
        action=kwargs.pop("action", "deploy"),  # type: ignore[arg-type]
        services=kwargs.pop("services", manifest["services_changed"]),  # type: ignore[arg-type]
        clock=clock,
        **kwargs,  # type: ignore[arg-type]
    )


def test_valid_approval_is_accepted() -> None:
    manifest = make_manifest(["frontend"])
    check(manifest, make_approval(manifest), Clock())


def test_missing_approval_is_refused(tmp_path: Path) -> None:
    for path in (None, tmp_path / "absent.json"):
        with pytest.raises(StopCondition) as missing:
            approvals.load_approval(path)
        assert missing.value.code == "APPROVAL_MISSING"
    broken = tmp_path / "broken.json"
    broken.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
    with pytest.raises(StopCondition) as invalid:
        approvals.load_approval(broken)
    assert invalid.value.code == "APPROVAL_INVALID"


def test_expired_and_not_yet_valid_approvals_are_refused() -> None:
    manifest = make_manifest(["frontend"])
    record = make_approval(manifest)
    late = Clock(NOW + timedelta(hours=2))
    with pytest.raises(StopCondition) as expired:
        check(manifest, record, late)
    assert expired.value.code == "APPROVAL_EXPIRED" and "never extended" in expired.value.message
    with pytest.raises(StopCondition) as early:
        check(manifest, record, Clock(NOW - timedelta(hours=1)))
    assert early.value.code == "APPROVAL_NOT_YET_VALID"


def test_tracked_sample_approval_is_already_expired() -> None:
    sample = approvals.load_approval(SAMPLE.with_name("approval-record.sample.json"))
    manifest = read_json(SAMPLE)
    with pytest.raises(StopCondition) as expired:
        approvals.check_approval(
            sample, manifest, action="deploy", services=sorted(manifest["services_changed"])
        )
    assert expired.value.code == "APPROVAL_EXPIRED"


def test_approval_is_bound_to_manifest_services_action_and_risk() -> None:
    manifest = make_manifest(["frontend"])
    record = make_approval(manifest)
    clock = Clock()
    other = copy.deepcopy(manifest)
    other["images"]["frontend"]["local_image_id"] = "sha256:" + "1" * 64
    with pytest.raises(StopCondition) as wrong_manifest:
        check(other, record, clock)
    assert wrong_manifest.value.code == "APPROVAL_MANIFEST_MISMATCH"
    with pytest.raises(StopCondition) as wrong_services:
        check(manifest, record, clock, services=["frontend", "backend"])
    assert wrong_services.value.code == "APPROVAL_SERVICE_MISMATCH"
    with pytest.raises(StopCondition) as wrong_action:
        check(manifest, record, clock, action="publish")
    assert wrong_action.value.code == "APPROVAL_ACTION"
    record["risk_class"] = "HIGH"
    with pytest.raises(StopCondition) as wrong_risk:
        check(manifest, record, clock)
    assert wrong_risk.value.code == "APPROVAL_RISK_MISMATCH"


def test_approval_window_is_capped_and_single_use() -> None:
    manifest = make_manifest(["frontend"])
    long_window = make_approval(manifest, end=NOW + timedelta(hours=30))
    with pytest.raises(StopCondition) as too_long:
        check(manifest, long_window, Clock())
    assert too_long.value.code == "APPROVAL_WINDOW_INVALID"
    record = make_approval(manifest)
    used = frozenset({f"{record['approval_id']}:deploy"})
    with pytest.raises(StopCondition) as reused:
        check(manifest, record, Clock(), consumed=used)
    assert reused.value.code == "APPROVAL_ALREADY_USED"


def test_only_the_owner_at_a_terminal_can_create_an_approval(tmp_path: Path) -> None:
    manifest = make_manifest(["frontend"])
    arguments = dict(
        services=["frontend"],
        actions=["deploy"],
        auto_rollback=True,
        not_before="2026-11-14T10:00:00Z",
        expires_at="2026-11-14T12:00:00Z",
        approved_by="owner",
        clock=Clock(),
    )
    with pytest.raises(StopCondition) as automated:
        approvals.create_approval(manifest, confirm=lambda _: "", interactive=False, **arguments)  # type: ignore[arg-type]
    assert automated.value.code == "APPROVAL_NEEDS_OWNER"
    with pytest.raises(StopCondition) as mistyped:
        approvals.create_approval(
            manifest, confirm=lambda _: "wrong", interactive=True, **arguments
        )  # type: ignore[arg-type]
    assert mistyped.value.code == "APPROVAL_NOT_CONFIRMED"
    with pytest.raises(StopCondition) as other_services:
        approvals.create_approval(
            manifest,
            confirm=lambda _: "",
            interactive=True,
            **{**arguments, "services": ["backend"]},  # type: ignore[arg-type]
        )
    assert other_services.value.code == "APPROVAL_SERVICE_MISMATCH"
    prefix = manifests.manifest_hash(manifest)[:12]
    record = approvals.create_approval(
        manifest, confirm=lambda _: prefix, interactive=True, **arguments
    )  # type: ignore[arg-type]
    path = tmp_path / "approval.json"
    approvals.save_approval(path, record)
    assert approvals.load_approval(path) == record
    check(manifest, record, Clock(NOW + timedelta(minutes=1)))
    with pytest.raises(StopCondition):
        approvals.save_approval(path, record)


# -- T-1: a release-branch source is recorded and shown at approval ------------------------


def _approval_arguments() -> dict[str, object]:
    return {
        "services": ["frontend"],
        "actions": ["deploy"],
        "auto_rollback": True,
        "not_before": "2026-11-14T10:00:00Z",
        "expires_at": "2026-11-14T12:00:00Z",
        "approved_by": "owner",
        "clock": Clock(),
    }


def test_the_manifest_records_only_known_base_reasons() -> None:
    manifest = make_manifest(["frontend"])
    manifests.validate_manifest(manifest)  # no base_reason: an older manifest stays valid
    manifest["source"]["base_reason"] = "N7A_READER_LINEAGE"
    manifest["source"]["base_ref"] = "origin/release/n7a-reader-20261117"
    manifests.validate_manifest(manifest)
    manifest["source"]["base_reason"] = "ANY_REASON"
    with pytest.raises(ReleaseError) as refused:
        manifests.validate_manifest(manifest)
    assert refused.value.code == "MANIFEST_INVALID"


@pytest.mark.parametrize(
    ("base_ref", "base_reason"),
    [
        ("origin/release/n7a-reader-20261117", None),
        ("origin/release/n7a-reader-20261117", "INTEGRATION_BASELINE"),
        ("origin/main", "N7A_READER_LINEAGE"),
        ("origin/release/n7a-reader-2026111", "N7A_READER_LINEAGE"),
        ("origin/other", None),
    ],
)
def test_manifest_refuses_inconsistent_or_unsupported_source_lineage(
    base_ref: str, base_reason: str | None
) -> None:
    manifest = make_manifest(["frontend"])
    manifest["source"]["base_ref"] = base_ref
    if base_reason is not None:
        manifest["source"]["base_reason"] = base_reason
    with pytest.raises(ReleaseError) as refused:
        manifests.validate_manifest(manifest)
    assert refused.value.code == "MANIFEST_INVALID"


def test_manifest_accepts_explicit_integration_base_reason() -> None:
    manifest = make_manifest(["frontend"])
    manifest["source"]["base_reason"] = "INTEGRATION_BASELINE"
    manifests.validate_manifest(manifest)


def test_the_approval_prompt_says_when_the_source_is_not_main() -> None:
    prompts: list[str] = []

    def confirm(text: str) -> str:
        prompts.append(text)
        return "wrong"

    plain = make_manifest(["frontend"])
    with pytest.raises(StopCondition):
        approvals.create_approval(plain, confirm=confirm, interactive=True, **_approval_arguments())  # type: ignore[arg-type]
    assert "NOT origin/main" not in prompts[-1]
    reader = make_manifest(["frontend"])
    reader["source"]["base_ref"] = "origin/release/n7a-reader-20261117"
    reader["source"]["base_reason"] = "N7A_READER_LINEAGE"
    with pytest.raises(StopCondition):
        approvals.create_approval(reader, confirm=confirm, interactive=True, **_approval_arguments())  # type: ignore[arg-type]
    assert (
        "SOURCE IS NOT origin/main: release branch origin/release/n7a-reader-20261117 "
        "(N7A_READER_LINEAGE)."
    ) in prompts[-1]


F2_PIN = (
    "8454370251e010d4dc93331263a61d3f57b1f1e0",
    "b2121b9976358ed7f43a54e87518982bb0dcdf0f",
)


def _f2_manifest(services: list[str]) -> dict:
    manifest = make_manifest(services)
    manifest["source"]["base_ref"] = "origin/release/f2-ai-insights-notice-c5a1c7f4"
    manifest["source"]["base_reason"] = "F2_FRONTEND_LINEAGE"
    manifest["source"]["commit"], manifest["source"]["tree"] = F2_PIN
    return manifest


def test_f2_manifest_is_accepted_only_frontend_and_pinned() -> None:
    manifests.validate_manifest(_f2_manifest(["frontend"]))
    for services in (["backend"], ["frontend", "backend"], ["assistant"]):
        try:
            candidate = _f2_manifest(services)
        except Exception:  # make_manifest may refuse some combinations itself
            continue
        with pytest.raises(ReleaseError) as refused:
            manifests.validate_manifest(candidate)
        assert refused.value.code == "MANIFEST_INVALID"
    other = _f2_manifest(["frontend"])
    other["source"]["tree"] = "1" * 40
    with pytest.raises(ReleaseError) as wrong_tree:
        manifests.validate_manifest(other)
    assert wrong_tree.value.code == "MANIFEST_INVALID"


def test_the_approval_prompt_names_the_f2_lineage() -> None:
    prompts: list[str] = []

    def confirm(text: str) -> str:
        prompts.append(text)
        return "wrong"

    with pytest.raises(StopCondition):
        approvals.create_approval(_f2_manifest(["frontend"]), confirm=confirm, interactive=True, **_approval_arguments())  # type: ignore[arg-type]
    assert (
        "SOURCE IS NOT origin/main: release branch origin/release/f2-ai-insights-notice-c5a1c7f4 "
        "(F2_FRONTEND_LINEAGE)."
    ) in prompts[-1]


COMBINED_PINS = {
    "C10_OPQ_ASSISTANT_BACKEND_INSIGHTS_LINEAGE": (
        "origin/release/c10-opq-assistant-backend-insights-c5a1c7f4",
        "5ad86fb527f82c8c430af19ea2e2b1213d1b7407",
        "9be9b86015d503bab37ab5dee7d0c68596c1f573",
    ),
}


@pytest.mark.parametrize("reason", sorted(COMBINED_PINS))
def test_combined_lineages_are_pinned_and_assistant_backend_only(reason: str) -> None:
    base_ref, commit, tree = COMBINED_PINS[reason]

    def manifest_for(services: list[str]) -> dict:
        manifest = make_manifest(services)
        manifest["source"]["base_ref"] = base_ref
        manifest["source"]["base_reason"] = reason
        manifest["source"]["commit"], manifest["source"]["tree"] = commit, tree
        return manifest

    manifests.validate_manifest(manifest_for(["assistant", "backend"]))
    for services in (["frontend"], ["assistant"], ["assistant", "backend", "frontend"]):
        try:
            candidate = manifest_for(services)
        except Exception:
            continue
        with pytest.raises(ReleaseError) as refused:
            manifests.validate_manifest(candidate)
        assert refused.value.code == "MANIFEST_INVALID"
    wrong = manifest_for(["assistant", "backend"])
    wrong["source"]["commit"] = "1" * 40
    with pytest.raises(ReleaseError):
        manifests.validate_manifest(wrong)


def test_c11_fallback_frontend_lineage_is_pinned_and_frontend_only() -> None:
    manifest = make_manifest(["frontend"])
    manifest["source"]["base_ref"] = "origin/release/f2-c11-fallback-c5a1c7f4"
    manifest["source"]["base_reason"] = "F2_C11_FALLBACK_FRONTEND_LINEAGE"
    manifest["source"]["commit"] = "5dd4d3cf6026541c9f7e9221a23fc4ba8f1437be"
    manifest["source"]["tree"] = "7efa88622ef1bddb1a710feb97b25474321c06c2"
    manifests.validate_manifest(manifest)
    manifest["source"]["tree"] = "1" * 40
    with pytest.raises(ReleaseError):
        manifests.validate_manifest(manifest)
