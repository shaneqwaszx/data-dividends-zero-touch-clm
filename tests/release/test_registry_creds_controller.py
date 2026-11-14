"""Publication, credentials, image transfer, the local controller and the command line.

The registry and the credential store are in-memory fakes. Sentinel tokens are built by
concatenation and must never appear in an argument, an environment, a log or a record.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import sys
import uuid
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from tools.release import cli, controller, credstore, images, registry, render, source
from tools.release.core import AuditLog, Command, Effect, Gate, Mode, Result, Secret, StopCondition
from tools.release.host import Host, SshTarget
from tools.release.manifest import manifest_hash
from tools.release.records import StateStore

from .fakes import NOW, REPO, SAMPLE, Clock, FakeWorld, make_context, make_manifest, sentinel_token
from .test_source_images_render import make_archive

STAMP = "%Y-%m-%dT%H:%M:%SZ"
SOON = (NOW + timedelta(days=30)).strftime(STAMP)


def credential(label: str = "publish") -> credstore.StoredCredential:
    return credstore.StoredCredential("release-bot", Secret(sentinel_token(label)), "", SOON)


def publish_world(mode: Mode, tmp_path: Path) -> tuple[Gate, FakeWorld, dict[str, Any], AuditLog]:
    manifest = make_manifest(["frontend"], published=False)
    world = FakeWorld(manifest)
    log = AuditLog(path=tmp_path / "audit.jsonl")
    return Gate(world, mode, log), world, manifest, log


def everything(world: FakeWorld, tmp_path: Path, *extra: Any) -> str:
    parts = [json.dumps(extra, default=str)]
    for command in world.received:
        parts.append(" ".join(command.argv))
        parts.append(json.dumps(dict(command.env or {})))
    parts += [
        p.read_text(encoding="utf-8", errors="replace") for p in tmp_path.rglob("*") if p.is_file()
    ]
    return "\n".join(parts)


# -- publication -----------------------------------------------------------------------------


def test_publish_pushes_the_qualified_image_by_digest_without_exposing_the_token(
    tmp_path: Path,
) -> None:
    gate, world, manifest, log = publish_world(Mode.EXECUTE, tmp_path)
    published = registry.publish(gate, manifest, ["frontend"], credential())
    image = published["images"]["frontend"]
    assert image["registry_manifest_digest"].startswith("sha256:")
    assert (
        image["registry_tag"].startswith("rc-d0142d8e8d74-")
        and "latest" not in image["registry_tag"]
    )
    assert published["candidate_manifest_sha256"] == manifest_hash(manifest)
    assert manifest["images"]["frontend"]["registry_manifest_digest"] is None, "input not mutated"
    token = sentinel_token("publish")
    assert world.stdin_seen == [token]
    assert token not in everything(world, tmp_path, published, log.events)
    verbs = [c.argv[1] for c in world.received if c.argv[0] == "docker"]
    assert (
        "build" not in verbs
        and verbs[-1] == "logout"
        and verbs.index("login") < verbs.index("push")
    )
    configs = {(c.env or {}).get("DOCKER_CONFIG") for c in world.effects(Effect.REGISTRY_WRITE)}
    assert len(configs) == 1 and None not in configs
    assert not Path(configs.pop()).exists(), "the throwaway Docker configuration is removed"


@pytest.mark.parametrize("mode", [Mode.PLAN_ONLY, Mode.DRY_RUN])
def test_publish_dry_run_issues_no_registry_write_and_reads_no_credential(
    mode: Mode, tmp_path: Path
) -> None:
    gate, world, manifest, _ = publish_world(mode, tmp_path)
    published = registry.publish(gate, manifest, ["frontend"], credential("dryrun"))
    assert world.effects(Effect.REGISTRY_WRITE, Effect.HOST_WRITE, Effect.PROVIDER_CALL) == []
    assert world.stdin_seen == [] and world.registry == {}
    assert published["images"]["frontend"]["registry_manifest_digest"] is None
    assert {c.effect for c in gate.skipped} >= {Effect.REGISTRY_WRITE}


def test_registry_content_that_is_not_the_qualified_image_is_refused(tmp_path: Path) -> None:
    gate, world, manifest, _ = publish_world(Mode.EXECUTE, tmp_path)
    world.push_wrong_config = True
    with pytest.raises(StopCondition) as refused:
        registry.publish(gate, manifest, ["frontend"], credential())
    assert refused.value.code == "WRONG_DIGEST"
    assert world.received[-1].argv[1] == "logout", "logged out even on failure"
    config = (world.received[-1].env or {})["DOCKER_CONFIG"]
    assert not Path(config).exists()
    assert sentinel_token("publish") not in everything(world, tmp_path, str(refused.value))


def test_push_failure_and_existing_tag_with_other_content_are_refused(tmp_path: Path) -> None:
    gate, world, manifest, _ = publish_world(Mode.EXECUTE, tmp_path)
    world.push_ok = False
    with pytest.raises(StopCondition) as failed:
        registry.publish(gate, manifest, ["frontend"], credential())
    assert failed.value.code == "PUSH_FAILED"
    gate2, world2, manifest2, _ = publish_world(Mode.EXECUTE, tmp_path / "b")
    repository = manifest2["images"]["frontend"]["repository"]
    tag = f"{repository}:{registry.release_tag(manifest2, 'frontend')}"
    world2.registry[tag] = {
        "raw": json.dumps({"config": {"digest": "sha256:" + "e" * 64}}).encode()
    }
    with pytest.raises(StopCondition) as exists:
        registry.publish(gate2, manifest2, ["frontend"], credential())
    assert exists.value.code == "TAG_EXISTS"
    assert not [c for c in world2.received if c.argv[:2] == ("docker", "push")]


def test_a_local_image_that_changed_since_qualification_is_never_published(tmp_path: Path) -> None:
    gate, world, manifest, _ = publish_world(Mode.EXECUTE, tmp_path)
    stale = json.loads(json.dumps(manifest))
    stale["images"]["frontend"]["local_image_id"] = (
        "sha256:" + "d" * 64
    )  # the tag now points elsewhere
    with pytest.raises(StopCondition) as refused:
        registry.publish(gate, stale, ["frontend"], credential())
    assert refused.value.code == "WRONG_IMAGE_ID"
    assert not [c for c in world.received if c.argv[1] in {"push", "build", "tag"}]


def test_already_published_identical_image_is_accepted_without_a_second_push(
    tmp_path: Path,
) -> None:
    gate, world, manifest, _ = publish_world(Mode.EXECUTE, tmp_path)
    first = registry.publish(gate, manifest, ["frontend"], credential())
    pushes = len([c for c in world.received if c.argv[:2] == ("docker", "push")])
    second = registry.publish(gate, manifest, ["frontend"], credential())
    assert len([c for c in world.received if c.argv[:2] == ("docker", "push")]) == pushes == 1
    assert (
        second["images"]["frontend"]["registry_manifest_digest"]
        == (first["images"]["frontend"]["registry_manifest_digest"])
    )


# -- transfer by archive ---------------------------------------------------------------------


class ArchiveWorld:
    """Local ``docker save`` writes a synthetic archive; the host stores and hashes it."""

    def __init__(self, archive: bytes, image_id: str, corrupt: bool = False) -> None:
        self.archive, self.image_id, self.corrupt = archive, image_id, corrupt
        self.received: list[Command] = []
        self.loaded: str | None = None
        self.host_bytes = b""

    def run(self, command: Command) -> Result:
        self.received.append(command)
        argv = command.argv
        if argv[:3] == ("docker", "image", "inspect"):
            return Result(
                0, json.dumps({"Id": self.image_id, "Os": "linux", "Architecture": "amd64"})
            )
        if argv[:2] == ("docker", "save"):
            assert command.stdout_file is not None
            Path(command.stdout_file).write_bytes(self.archive)
            return Result(0)
        text = argv[-1]
        if "cat > " in text:
            assert command.stdin_file is not None
            self.host_bytes = Path(command.stdin_file).read_bytes()
            return Result(0)
        if text.startswith("sha256sum"):
            import hashlib

            data = self.host_bytes + (b"x" if self.corrupt else b"")
            return Result(0, hashlib.sha256(data).hexdigest() + "\n")
        if "docker load" in text:
            self.loaded = text
            return Result(0)
        if "docker image inspect -f" in text:
            return Result(0, f"{self.image_id} linux/amd64\n" if self.loaded else "ABSENT\n")
        if text.startswith("rm -f"):
            return Result(0)
        return Result(1, "", "unexpected")


def archive_setup(corrupt: bool = False) -> tuple[Gate, Host, ArchiveWorld, dict[str, Any]]:
    from tools.release import catalog
    from tools.release.core import sha256_bytes

    config = b'{"architecture":"amd64","os":"linux"}'
    image_id = "sha256:" + sha256_bytes(config)
    manifest = make_manifest(["frontend"], published=False)
    manifest["images"]["frontend"].update(local_image_id=image_id, config_digest=image_id)
    world = ArchiveWorld(make_archive(config), image_id, corrupt)
    gate = Gate(world, Mode.EXECUTE, AuditLog())
    return (
        gate,
        Host(gate, SshTarget("operator@host.test.invalid"), catalog.HostProfile()),
        world,
        manifest,
    )


def test_archive_transfer_verifies_the_copy_and_the_loaded_image_identity() -> None:
    gate, host, world, manifest = archive_setup()
    reference = registry.host_load(gate, host, manifest, "frontend")
    assert (
        reference.endswith(registry.release_tag(manifest, "frontend"))
        and ":latest" not in reference
    )
    assert (
        world.loaded is not None and manifest["images"]["frontend"]["config_digest"] in world.loaded
    )
    assert not [c for c in world.received if c.stdin is not None], (
        "no credential is involved at all"
    )


def test_archive_damaged_in_transit_is_refused_and_never_loaded() -> None:
    gate, host, world, manifest = archive_setup(corrupt=True)
    with pytest.raises(StopCondition) as refused:
        registry.host_load(gate, host, manifest, "frontend")
    assert refused.value.code == "WRONG_DIGEST" and world.loaded is None
    assert world.received[-1].argv[-1].startswith("rm -f")


def test_archive_of_a_different_image_is_refused_before_anything_is_copied() -> None:
    gate, host, world, manifest = archive_setup()
    manifest["images"]["frontend"]["config_digest"] = "sha256:" + "c" * 64
    with pytest.raises(StopCondition) as refused:
        registry.host_load(gate, host, manifest, "frontend")
    assert refused.value.code == "WRONG_DIGEST"
    assert not [c for c in world.received if c.effect is Effect.HOST_WRITE]


# -- credentials -----------------------------------------------------------------------------


def bootstrap(
    store: credstore.CredentialStore, identity: str, token: str, **kwargs: Any
) -> dict[str, str]:
    arguments: dict[str, Any] = dict(
        username="release-bot",
        expires_at=SOON,
        prompt=lambda _: token,
        interactive=True,
        clock=Clock(),
    )
    arguments.update(kwargs)
    return credstore.bootstrap(store, identity, **arguments)


def test_bootstrap_stores_the_token_and_returns_only_metadata() -> None:
    store = credstore.MemoryStore()
    token = sentinel_token("bootstrap")
    metadata = bootstrap(store, "pull", token)
    assert token not in json.dumps(metadata) and metadata["identity"] == "pull"
    assert token not in json.dumps(credstore.status(store, Clock()))
    assert store.items["clm-release/ghcr-pull"][1] == token
    assert token not in store.items["clm-release/ghcr-pull"][0], "metadata never holds the value"
    fetched = credstore.fetch(store, "pull", Clock())
    assert fetched.secret.reveal() == token and token not in repr(fetched)


def test_bootstrap_refuses_automation_bad_input_and_a_shared_token() -> None:
    store = credstore.MemoryStore()
    token = sentinel_token("shared")
    with pytest.raises(StopCondition) as automated:
        bootstrap(store, "pull", token, interactive=False)
    assert automated.value.code == "CREDENTIAL_NEEDS_OWNER" and store.items == {}
    for bad in ("", "two words"):
        with pytest.raises(StopCondition) as invalid:
            bootstrap(store, "pull", bad)
        assert invalid.value.code in {"CREDENTIAL_INVALID", "SECRET_EMPTY"}
    with pytest.raises(StopCondition) as past:
        bootstrap(store, "pull", token, expires_at=(NOW - timedelta(days=1)).strftime(STAMP))
    assert past.value.code == "CREDENTIAL_EXPIRED"
    with pytest.raises(StopCondition) as long_lived:
        bootstrap(store, "pull", token, expires_at=(NOW + timedelta(days=365)).strftime(STAMP))
    assert long_lived.value.code == "CREDENTIAL_LIFETIME"
    assert store.items == {}
    bootstrap(store, "publish", token)
    with pytest.raises(StopCondition) as shared:
        bootstrap(store, "pull", token)
    assert shared.value.code == "CREDENTIAL_NOT_SEPARATE"
    with pytest.raises(StopCondition) as exists:
        bootstrap(store, "publish", sentinel_token("other"))
    assert exists.value.code == "CREDENTIAL_EXISTS"


def test_expired_or_missing_token_stops_the_release_and_rotation_replaces_it() -> None:
    store = credstore.MemoryStore()
    old, new = sentinel_token("old"), sentinel_token("new")
    with pytest.raises(StopCondition) as missing:
        credstore.fetch(store, "pull", Clock())
    assert missing.value.code == "CREDENTIAL_MISSING"
    bootstrap(store, "pull", old)
    with pytest.raises(StopCondition) as expired:
        credstore.fetch(store, "pull", Clock(NOW + timedelta(days=31)))
    assert expired.value.code == "CREDENTIAL_EXPIRED"
    assert credstore.status(store, Clock(NOW + timedelta(days=31)))[1]["state"] == "expired"
    assert credstore.status(store, Clock(NOW + timedelta(days=25)))[1]["state"] == "expires-soon"
    arguments: dict[str, Any] = dict(
        username="release-bot", expires_at=SOON, interactive=True, clock=Clock()
    )
    with pytest.raises(StopCondition) as same:
        credstore.rotate(store, "pull", prompt=lambda _: old, **arguments)
    assert same.value.code == "CREDENTIAL_NOT_ROTATED"
    credstore.rotate(store, "pull", prompt=lambda _: new, **arguments)
    assert credstore.fetch(store, "pull", Clock()).secret.reveal() == new
    with pytest.raises(StopCondition):
        credstore.rotate(store, "publish", prompt=lambda _: new, **arguments)
    assert (
        credstore.revoke_local(store, "pull") is True
        and credstore.revoke_local(store, "pull") is False
    )
    assert credstore.status(store, Clock())[1] == {"identity": "pull", "state": "absent"}


def test_temporary_docker_config_is_removed_even_when_the_work_fails() -> None:
    world = FakeWorld(make_manifest(["frontend"]))
    gate = Gate(world, Mode.EXECUTE, AuditLog())
    seen: list[Path] = []
    with pytest.raises(RuntimeError), credstore.temporary_docker_config(gate) as env:
        directory = Path(env["DOCKER_CONFIG"])
        seen.append(directory)
        assert directory.is_dir() and json.loads((directory / "config.json").read_text()) == {
            "auths": {}
        }
        assert env["DOCKER_HOST"].startswith("npipe:")
        (directory / "config.json").write_text('{"auths": {"ghcr.io": {"auth": "x"}}}')
        raise RuntimeError("push failed")
    assert not seen[0].exists()
    assert seen[0] != Path.home() / ".docker", "the user's own Docker configuration is never used"


@pytest.mark.skipif(
    sys.platform != "win32" or os.environ.get("CLM_RELEASE_WINCRED_SELFTEST") != "1",
    reason="opt-in: writes and removes one throwaway entry in the Windows Credential Manager",
)
def test_windows_credential_manager_round_trip_with_a_sentinel() -> None:
    store = credstore.WindowsCredentialStore()
    target = f"clm-release/selftest-{uuid.uuid4().hex}"
    value = sentinel_token("wincred")
    try:
        assert store.read(target) is None
        store.write(target, '{"k": "v"}', value)
        assert store.read(target) == ('{"k": "v"}', value)
    finally:
        assert store.delete(target) is True
    assert store.read(target) is None and store.delete(target) is False


def test_pull_script_never_stores_the_token_and_removes_its_configuration(tmp_path: Path) -> None:
    script = registry.PULL_SCRIPT
    assert "--password-stdin" in script and "mktemp -d /run/clm-ghcr." in script
    assert script.index("logout ghcr.io") < script.index("rmdir") < script.index("auth_dirs_left")
    assert "~/.docker" not in script and "docker login ghcr.io -p" not in script
    manifest = make_manifest(["frontend"])
    ctx, world = make_context(manifest, tmp_path, mode=Mode.EXECUTE)
    registry.host_pull(ctx.host, manifest, "frontend", credential("pull"))
    sent = world.received[0]
    assert isinstance(sent.stdin, Secret) and sentinel_token("pull") not in sent.argv[-1]
    with pytest.raises(StopCondition):
        registry.host_pull(
            ctx.host,
            manifest,
            "frontend",
            credstore.StoredCredential("bad user;", sent.stdin, "", ""),
        )


# -- controller ------------------------------------------------------------------------------


@pytest.fixture()
def prepared(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> tuple[controller.Controller, FakeWorld, Path]:
    """A controller whose git, Docker and render calls are replaced by canned answers."""

    sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
    monkeypatch.setattr(
        source,
        "verify_source",
        lambda gate, root, **kw: source.SourceState(
            kw["commit"], sample["source"]["tree"], "origin/main"
        ),
    )
    monkeypatch.setattr(
        source, "compose_file_hashes", lambda gate, root, commit, files: sample["compose_files"]
    )
    monkeypatch.setattr(
        images, "accept_existing", lambda gate, reference, expected: {"Id": expected}
    )
    monkeypatch.setattr(
        images,
        "describe_candidate",
        lambda gate, root, commit, service, reference, mode: dict(sample["images"][service]),
    )
    monkeypatch.setattr(
        render, "validate_release_config", lambda gate, root, manifest: ["assistant"]
    )
    world = FakeWorld(sample)
    world._local = lambda command: Result(0, sample["source"]["commit"] + "\n")  # type: ignore[method-assign]
    store = StateStore(tmp_path / "state", Clock())
    gate = Gate(world, Mode.LOCAL, AuditLog(path=tmp_path / "audit.jsonl"))
    instance = controller.Controller(gate, REPO, store, Clock())
    instance.inbox.mkdir(parents=True)
    shutil.copy(
        SAMPLE.with_name("release-request.assistant-only.sample.json"), instance.inbox / "one.json"
    )
    return instance, world, tmp_path


def test_controller_prepares_a_promotion_ready_record_and_stops_there(
    prepared: tuple[controller.Controller, FakeWorld, Path],
) -> None:
    instance, world, tmp_path = prepared
    handled = instance.tick()
    assert len(handled) == 1 and handled[0]["state"] == controller.PROMOTION_READY
    assert handled[0]["services"] == ["assistant"] and handled[0]["risk_class"] == "MEDIUM"
    manifest = json.loads(Path(handled[0]["manifest"]).read_text(encoding="utf-8"))
    assert manifest_hash(manifest) == handled[0]["manifest_sha256"]
    assert manifest["images"]["assistant"]["registry_manifest_digest"] is None
    assert any(n.startswith("ci-job:") for n in handled[0]["not_run"]), (
        "manual jobs are never a pass"
    )
    assert "approve" in handled[0]["next"]
    forbidden = world.effects(
        Effect.HOST_READ,
        Effect.HOST_WRITE,
        Effect.REGISTRY_READ,
        Effect.REGISTRY_WRITE,
        Effect.PUBLIC_READ,
        Effect.PROVIDER_CALL,
    )
    assert forbidden == [], "preparation never leaves this machine (works with Actions blocked)"
    assert instance.store.known_good() is None
    assert not list((tmp_path / "state").rglob("apr-*.json")), "the controller never approves"
    assert instance.tick() == [], "a processed request is not processed again"
    assert (
        json.loads((tmp_path / "state" / "seen-main.json").read_text())["commit"]
        == manifest["source"]["commit"]
    )


def test_controller_mode_cannot_publish_or_deploy_even_if_asked(
    prepared: tuple[controller.Controller, FakeWorld, Path],
) -> None:
    instance, world, _ = prepared
    manifest = make_manifest(["frontend"], published=False)
    registry.publish(instance.gate, manifest, ["frontend"], credential("ctl"))
    assert world.effects(Effect.REGISTRY_WRITE, Effect.HOST_WRITE) == [] and world.stdin_seen == []


def test_failed_request_is_recorded_and_retried_only_on_request(
    prepared: tuple[controller.Controller, FakeWorld, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    instance, _, _ = prepared

    def wrong_commit(gate: Gate, root: Path, **kwargs: Any) -> Any:
        raise StopCondition("WRONG_COMMIT", "checkout is at another commit")

    working = source.verify_source
    monkeypatch.setattr(source, "verify_source", wrong_commit)
    failed = instance.tick()
    assert failed[0]["state"] == controller.FAILED and failed[0]["code"] == "WRONG_COMMIT"
    monkeypatch.setattr(source, "verify_source", working)
    assert instance.tick() == [], "never retried silently"
    assert instance.retry("req-assistant-only-example") is True
    assert instance.tick()[0]["state"] == controller.PROMOTION_READY
    with pytest.raises(StopCondition):
        instance.retry("req-assistant-only-example")
    assert len(instance.status()) == 1


def test_failed_check_and_malformed_request_do_not_become_promotion_ready(
    prepared: tuple[controller.Controller, FakeWorld, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    instance, _, _ = prepared
    monkeypatch.setattr(
        source,
        "run_checks",
        lambda gate, root, names: [{"name": "check_secrets", "status": "FAIL", "detail": "exit 1"}],
    )
    (instance.inbox / "bad.json").write_text('{"request_id": "x", "surprise": 1}', encoding="utf-8")
    handled = {h.get("request_id", h.get("request")): h for h in instance.tick()}
    assert handled["bad.json"]["state"] == controller.FAILED
    assert handled["req-assistant-only-example"]["code"] == "CHECK_FAILED"


def test_controller_refuses_to_run_beside_another_release_operation(
    prepared: tuple[controller.Controller, FakeWorld, Path],
) -> None:
    instance, _, _ = prepared
    with instance.store.lock("rel-deploying-20261114-01"):
        handled = instance.tick()
    assert handled[0]["state"] == controller.FAILED and handled[0]["code"] == "RELEASE_IN_PROGRESS"


# -- command line ----------------------------------------------------------------------------


def run_cli(tmp_path: Path, *argv: str, capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = cli.main(["--state-dir", str(tmp_path / "state"), *argv])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_cli_plan_of_the_tracked_sample(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run_cli(tmp_path, "plan", "--manifest", str(SAMPLE), capsys=capsys)
    plan = json.loads(out)
    assert code == 0 and plan["deploy_order"] == ["backend", "assistant", "frontend"]
    assert plan["services_must_not_change"] == ["mongo"] and plan["risk_class"] == "HIGH"
    assert all("unknown until published" in s["new_reference"] for s in plan["services_change"])
    assert plan["services_change"][0]["automatic_rollback_eligible"] is False


def test_cli_refuses_to_execute_without_operator_config_or_approval(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    code, _, err = run_cli(
        tmp_path, "deploy", "--manifest", str(SAMPLE), "--execute", capsys=capsys
    )
    assert code == 3 and "OPERATOR_CONFIG_MISSING" in err
    expired = str(SAMPLE.with_name("approval-record.sample.json"))
    monkeypatch.setattr(render, "validate_release_config", lambda gate, root, manifest: ["stub"])
    code, out, _ = run_cli(
        tmp_path,
        "deploy",
        "--manifest",
        str(SAMPLE),
        "--approval",
        expired,
        "--offline",
        capsys=capsys,
    )
    assert code == 2 and json.loads(out)["stop_code"] == "APPROVAL_EXPIRED"


def test_cli_offline_dry_run_of_the_sample_contacts_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    issued: list[Command] = []

    class Recording:
        def run(self, command: Command) -> Result:
            issued.append(command)
            return Result(0, "{}")

    monkeypatch.setattr(cli, "SubprocessRunner", Recording)
    monkeypatch.setattr(render, "validate_release_config", lambda gate, root, manifest: ["stub"])
    frontend_only = tmp_path / "frontend.json"
    frontend_only.write_text(
        json.dumps(make_manifest(["frontend"], published=False)), encoding="utf-8"
    )
    code, out, _ = run_cli(
        tmp_path, "deploy", "--manifest", str(frontend_only), "--dry-run", capsys=capsys
    )
    outcome = json.loads(out)
    assert code == 0 and outcome["state"] == "DRY_RUN_OK" and issued == []
    effects = {c["effect"] for c in outcome["would_issue"]}
    assert "host-write" in effects and effects <= {"host-write", "host-read", "public-read"}
    # The three-service sample changes stateful services: with no backup location configured the
    # dry run reports that instead of pretending the release could proceed.
    code, out, _ = run_cli(
        tmp_path, "deploy", "--manifest", str(SAMPLE), "--dry-run", capsys=capsys
    )
    outcome = json.loads(out)
    assert (
        code == 2
        and outcome["stop_code"] == "PREFLIGHT_FAILED"
        and "backup" in outcome["stop_message"]
    )
    assert issued == []


def test_cli_owner_only_commands_refuse_a_non_interactive_caller(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    for argv, code_name in (
        (
            (
                "approve",
                "--manifest",
                str(SAMPLE),
                "--service",
                "frontend",
                "--service",
                "backend",
                "--service",
                "assistant",
                "--action",
                "deploy",
                "--not-before",
                "2026-11-14T10:00:00Z",
                "--expires-at",
                "2026-11-14T12:00:00Z",
                "--approved-by",
                "agent",
            ),
            "APPROVAL_NEEDS_OWNER",
        ),
        (
            ("accept", "--manifest", str(SAMPLE), "--result", "pass", "--accepted-by", "agent"),
            "ACCEPTANCE_NEEDS_OWNER",
        ),
        (("unlock",), "UNLOCK_NEEDS_OWNER"),
    ):
        code, _, err = run_cli(tmp_path, *argv, capsys=capsys)
        assert code == 3 and code_name in err
    assert not list((tmp_path / "state").rglob("apr-*.json"))


def test_cli_status_and_publish_plan(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run_cli(tmp_path, "status", capsys=capsys)
    assert code == 0 and json.loads(out)["known_good"] is None
    code, out, _ = run_cli(
        tmp_path, "publish", "--manifest", str(SAMPLE), "--plan-only", capsys=capsys
    )
    planned = json.loads(out)["would_publish"]
    assert code == 0 and set(planned) == {"frontend", "backend", "assistant"}
    assert all(":rc-d0142d8e8d74-" in reference for reference in planned.values())
    code, _, err = run_cli(
        tmp_path, "publish", "--manifest", str(SAMPLE), "--execute", capsys=capsys
    )
    assert code == 3 and "APPROVAL_MISSING" in err
