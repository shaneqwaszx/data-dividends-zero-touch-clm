"""Source verification, check selection, image identity and the effective Compose configuration.

Git tests use a throwaway repository in ``tmp_path``. Render tests that need the Docker CLI are
skipped without it; the policy tests run on summaries and need nothing.
"""

from __future__ import annotations

import copy
import io
import json
import re
import shutil
import subprocess
import tarfile
from pathlib import Path
from typing import Any

import pytest

from tools.release import catalog, controller, images, render, source
from tools.release.core import (
    AuditLog,
    Command,
    Effect,
    Gate,
    Mode,
    ReleaseError,
    Result,
    StopCondition,
    SubprocessRunner,
    sha256_bytes,
)
from tools.release.effective_summary import summarise
from tools.release.records import StateStore

from .fakes import REPO, make_manifest

needs_docker = pytest.mark.skipif(shutil.which("docker") is None, reason="Docker CLI not available")


def local_gate(mode: Mode = Mode.LOCAL) -> Gate:
    return Gate(SubprocessRunner(), mode, AuditLog())


# -- source ----------------------------------------------------------------------------------


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        [
            "git",
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.invalid",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout.strip()


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    git(path, "init", "-q", "-b", "main")
    (path / "a.txt").write_text("one\n", encoding="utf-8")
    git(path, "add", "a.txt")
    git(path, "commit", "-q", "-m", "one")
    git(path, "update-ref", "refs/remotes/origin/main", "HEAD")
    return path


def test_exact_commit_in_a_clean_checkout_is_accepted(repo: Path) -> None:
    head, tree = git(repo, "rev-parse", "HEAD"), git(repo, "rev-parse", "HEAD^{tree}")
    state = source.verify_source(local_gate(), repo, commit=head, tree=tree)
    assert (state.commit, state.tree) == (head, tree)


def test_wrong_commit_tree_or_abbreviated_commit_is_refused(repo: Path) -> None:
    head = git(repo, "rev-parse", "HEAD")
    for commit, tree, code in (
        ("0" * 40, None, "WRONG_COMMIT"),
        (head[:12], None, "COMMIT_NOT_EXACT"),
        ("origin/main", None, "COMMIT_NOT_EXACT"),
        (head, "1" * 40, "WRONG_TREE"),
    ):
        with pytest.raises(StopCondition) as refused:
            source.verify_source(local_gate(), repo, commit=commit, tree=tree)
        assert refused.value.code == code


def test_dirty_or_untracked_state_is_refused_unless_explicitly_allowed(repo: Path) -> None:
    head = git(repo, "rev-parse", "HEAD")
    (repo / "a.txt").write_text("changed\n", encoding="utf-8")
    with pytest.raises(StopCondition) as modified:
        source.verify_source(local_gate(), repo, commit=head)
    assert modified.value.code == "SOURCE_NOT_CLEAN"
    git(repo, "checkout", "-q", "--", "a.txt")
    (repo / "outputs").mkdir()
    (repo / "outputs" / "note.md").write_text("x\n", encoding="utf-8")
    with pytest.raises(StopCondition) as untracked:
        source.verify_source(local_gate(), repo, commit=head)
    assert untracked.value.code == "SOURCE_NOT_CLEAN"
    source.verify_source(local_gate(), repo, commit=head, allow_untracked=("outputs/",))


def test_commit_that_is_not_on_the_integration_baseline_is_refused(repo: Path) -> None:
    (repo / "b.txt").write_text("two\n", encoding="utf-8")
    git(repo, "add", "b.txt")
    git(repo, "commit", "-q", "-m", "unmerged")
    with pytest.raises(StopCondition) as refused:
        source.verify_source(local_gate(), repo, commit=git(repo, "rev-parse", "HEAD"))
    assert refused.value.code == "COMMIT_NOT_ON_BASE"


# -- T-1: an allow-listed release branch as the source base ----------------------------------

READER_BRANCH = "origin/release/n7a-reader-20261117"


def release_commit(repo: Path, *, push: bool = True) -> tuple[str, str]:
    """A one-commit release branch on top of origin/main, optionally 'pushed' (the
    remote-tracking ref exists); returns (commit, tree) and leaves it checked out."""

    (repo / "reader.txt").write_text("reader\n", encoding="utf-8")
    git(repo, "add", "reader.txt")
    git(repo, "commit", "-q", "-m", "reader release")
    head, tree = git(repo, "rev-parse", "HEAD"), git(repo, "rev-parse", "HEAD^{tree}")
    if push:
        git(repo, "update-ref", f"refs/remotes/{READER_BRANCH}", head)
    return head, tree


def test_the_default_base_is_unchanged(repo: Path) -> None:
    head, tree = git(repo, "rev-parse", "HEAD"), git(repo, "rev-parse", "HEAD^{tree}")
    state = source.verify_source(local_gate(), repo, commit=head, tree=tree)
    assert state.tree == tree
    assert (state.base_ref, state.base_reason) == ("origin/main", "INTEGRATION_BASELINE")
    explicit = source.verify_source(local_gate(), repo, commit=head, base_ref="origin/main")
    assert explicit == source.verify_source(local_gate(), repo, commit=head)


def test_an_allow_listed_release_branch_tip_with_its_tree_is_accepted(repo: Path) -> None:
    head, tree = release_commit(repo)
    state = source.verify_source(
        local_gate(), repo, commit=head, tree=tree, base_ref=READER_BRANCH
    )
    assert state.base_ref == READER_BRANCH and state.base_reason == "N7A_READER_LINEAGE"
    assert (state.commit, state.tree) == (head, tree)
    # The same commit is still refused against the integration baseline.
    with pytest.raises(StopCondition) as main:
        source.verify_source(local_gate(), repo, commit=head, tree=tree)
    assert main.value.code == "COMMIT_NOT_ON_BASE"


@pytest.mark.parametrize(
    "base",
    [
        "origin/release/c9-20261116",
        "release/n7a-reader-20261117",
        "refs/remotes/origin/release/n7a-reader-20261117",
        "origin/release/n7a-reader-2026111",
        "origin/release/n7a-reader-20261117-x",
        "origin/release/n7a-reader-20261117/../main",
        "origin/feature/anything",
        "upstream/main",
        "",
    ],
)
def test_any_other_base_is_refused_before_anything_is_read(repo: Path, base: str) -> None:
    head, tree = release_commit(repo)
    gate = local_gate()
    with pytest.raises(StopCondition) as refused:
        source.verify_source(gate, repo, commit=head, tree=tree, base_ref=base)
    assert refused.value.code == "BASE_REF_NOT_ALLOWED"
    assert gate.issued == []


def test_a_release_branch_base_requires_the_approved_tree(repo: Path) -> None:
    head, tree = release_commit(repo)
    with pytest.raises(StopCondition) as missing:
        source.verify_source(local_gate(), repo, commit=head, base_ref=READER_BRANCH)
    assert missing.value.code == "TREE_REQUIRED"
    with pytest.raises(StopCondition) as wrong:
        source.verify_source(
            local_gate(), repo, commit=head, tree="1" * 40, base_ref=READER_BRANCH
        )
    assert wrong.value.code == "WRONG_TREE"
    exact = source.verify_source(
        local_gate(), repo, commit=head, tree=tree, base_ref=READER_BRANCH
    )
    assert exact.tree == tree


def test_a_local_branch_of_the_same_name_is_not_enough(repo: Path) -> None:
    head, tree = release_commit(repo, push=False)
    git(repo, "branch", "origin/release/n7a-reader-20261117", head)  # a local look-alike
    with pytest.raises(ReleaseError) as refused:
        source.verify_source(
            local_gate(), repo, commit=head, tree=tree, base_ref=READER_BRANCH
        )
    assert refused.value.code == "GIT_FAILED"


@pytest.mark.parametrize("namespace", [None, "tags", "heads"])
def test_reader_release_requires_the_exact_remote_ref(repo: Path, namespace: str | None) -> None:
    head, tree = release_commit(repo, push=False)
    if namespace is not None:
        git(repo, "update-ref", f"refs/{namespace}/refs/remotes/{READER_BRANCH}", head)
    with pytest.raises(ReleaseError) as refused:
        source.verify_source(local_gate(), repo, commit=head, tree=tree, base_ref=READER_BRANCH)
    assert refused.value.code == "GIT_FAILED"


@pytest.mark.parametrize("namespace", [None, "tags", "heads"])
@pytest.mark.parametrize("reader", [False, True])
def test_main_requires_the_exact_remote_ref(
    repo: Path, namespace: str | None, reader: bool
) -> None:
    git(repo, "update-ref", "-d", "refs/remotes/origin/main")
    if namespace is not None:
        git(repo, "update-ref", f"refs/{namespace}/origin/main", "HEAD")
        git(repo, "update-ref", f"refs/{namespace}/refs/remotes/origin/main", "HEAD")
    base_ref = READER_BRANCH if reader else "origin/main"
    head, tree = release_commit(repo) if reader else (
        git(repo, "rev-parse", "HEAD"),
        git(repo, "rev-parse", "HEAD^{tree}"),
    )
    with pytest.raises(ReleaseError) as refused:
        source.verify_source(local_gate(), repo, commit=head, tree=tree, base_ref=base_ref)
    assert refused.value.code == "GIT_FAILED"


@pytest.mark.parametrize("base_ref", ["origin/main", READER_BRANCH])
def test_remote_tracking_ref_must_point_to_a_commit(repo: Path, base_ref: str) -> None:
    head, tree = release_commit(repo) if base_ref == READER_BRANCH else (
        git(repo, "rev-parse", "HEAD"),
        git(repo, "rev-parse", "HEAD^{tree}"),
    )
    git(repo, "tag", "-a", "annotated", "-m", "tag object", head)
    git(repo, "update-ref", f"refs/remotes/{base_ref}", "refs/tags/annotated")
    with pytest.raises(ReleaseError) as refused:
        source.verify_source(local_gate(), repo, commit=head, tree=tree, base_ref=base_ref)
    assert refused.value.code == "GIT_FAILED"


@pytest.mark.parametrize("chained", [False, True], ids=["symbolic", "chained"])
@pytest.mark.parametrize("entry", ["reader-tip", "reader-parent", "default", "notice"])
def test_symbolic_remote_tracking_refs_are_refused(
    repo: Path, tmp_path: Path, chained: bool, entry: str
) -> None:
    if entry == "reader-tip":
        head, tree = release_commit(repo, push=False)
        git(repo, "branch", "local-lineage", head)
        ref = READER_BRANCH
    else:
        git(repo, "commit", "-q", "--allow-empty", "-m", "local-only commit")
        git(repo, "branch", "local-lineage", "HEAD")
        if entry == "reader-parent":
            head, tree = release_commit(repo)
        else:
            head = git(repo, "rev-parse", "HEAD")
            tree = git(repo, "rev-parse", "HEAD^{tree}")
        ref = "origin/main"

    target = "refs/heads/local-lineage"
    if chained:
        intermediate = "refs/remotes/origin/intermediate"
        git(repo, "symbolic-ref", intermediate, target)
        target = intermediate
    git(repo, "symbolic-ref", f"refs/remotes/{ref}", target)

    gate = local_gate()
    if entry == "notice":
        state_dir = tmp_path / "controller-state"
        watcher = controller.Controller(gate, repo, StateStore(state_dir))
        assert watcher.detect_new_commit() is None
        assert not (state_dir / "seen-main.json").exists()
        return

    kwargs = {"base_ref": READER_BRANCH} if entry.startswith("reader-") else {}
    with pytest.raises(ReleaseError, match="symbolic") as refused:
        source.verify_source(gate, repo, commit=head, tree=tree, **kwargs)
    assert refused.value.code == "GIT_FAILED"


def test_a_ref_below_the_exact_reader_name_is_not_a_substitute(repo: Path) -> None:
    head, tree = release_commit(repo, push=False)
    git(repo, "update-ref", f"refs/remotes/{READER_BRANCH}/descendant", head)
    with pytest.raises(ReleaseError) as refused:
        source.verify_source(local_gate(), repo, commit=head, tree=tree, base_ref=READER_BRANCH)
    assert refused.value.code == "GIT_FAILED"


def test_a_main_tag_cannot_override_the_exact_parent_check(repo: Path) -> None:
    git(repo, "commit", "-q", "--allow-empty", "-m", "unmerged parent")
    git(repo, "tag", "origin/main", "HEAD")
    head, tree = release_commit(repo)
    with pytest.raises(StopCondition) as refused:
        source.verify_source(local_gate(), repo, commit=head, tree=tree, base_ref=READER_BRANCH)
    assert refused.value.code == "PARENT_NOT_ON_BASE"


def test_the_commit_must_be_the_release_branch_tip(repo: Path) -> None:
    head, tree = release_commit(repo)
    (repo / "later.txt").write_text("later\n", encoding="utf-8")
    git(repo, "add", "later.txt")
    git(repo, "commit", "-q", "-m", "later")
    later = git(repo, "rev-parse", "HEAD")
    git(repo, "update-ref", f"refs/remotes/{READER_BRANCH}", later)
    git(repo, "checkout", "-q", head)
    with pytest.raises(StopCondition) as refused:
        source.verify_source(local_gate(), repo, commit=head, tree=tree, base_ref=READER_BRANCH)
    assert refused.value.code == "COMMIT_NOT_BRANCH_TIP"


def test_the_release_commit_parent_must_be_on_the_integration_baseline(repo: Path) -> None:
    (repo / "unmerged.txt").write_text("not on main\n", encoding="utf-8")
    git(repo, "add", "unmerged.txt")
    git(repo, "commit", "-q", "-m", "unmerged parent")
    head, tree = release_commit(repo)
    with pytest.raises(StopCondition) as refused:
        source.verify_source(local_gate(), repo, commit=head, tree=tree, base_ref=READER_BRANCH)
    assert refused.value.code == "PARENT_NOT_ON_BASE"


def test_a_merge_commit_is_not_a_release_branch_commit(repo: Path) -> None:
    main = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-q", "-b", "side")
    (repo / "side.txt").write_text("side\n", encoding="utf-8")
    git(repo, "add", "side.txt")
    git(repo, "commit", "-q", "-m", "side")
    git(repo, "checkout", "-q", "-b", "rel", main)
    git(repo, "merge", "-q", "--no-ff", "-m", "merge", "side")
    head, tree = git(repo, "rev-parse", "HEAD"), git(repo, "rev-parse", "HEAD^{tree}")
    git(repo, "update-ref", f"refs/remotes/{READER_BRANCH}", head)
    with pytest.raises(StopCondition) as refused:
        source.verify_source(local_gate(), repo, commit=head, tree=tree, base_ref=READER_BRANCH)
    assert refused.value.code == "RELEASE_COMMIT_SHAPE"


def test_the_release_checks_stay_clean_and_exact_on_a_release_branch(repo: Path) -> None:
    head, tree = release_commit(repo)
    (repo / "stray.txt").write_text("x\n", encoding="utf-8")
    with pytest.raises(StopCondition) as dirty:
        source.verify_source(local_gate(), repo, commit=head, tree=tree, base_ref=READER_BRANCH)
    assert dirty.value.code == "SOURCE_NOT_CLEAN"
    (repo / "stray.txt").unlink()
    with pytest.raises(StopCondition) as short:
        source.verify_source(local_gate(), repo, commit=head[:12], tree=tree, base_ref=READER_BRANCH)
    assert short.value.code == "COMMIT_NOT_EXACT"


def test_compose_hashes_come_from_the_commit_not_the_work_tree(repo: Path) -> None:
    head = git(repo, "rev-parse", "HEAD")
    (repo / "a.txt").write_bytes(b"one\r\n")  # a CRLF checkout must not change the hash
    hashes = source.compose_file_hashes(local_gate(), repo, head, ("a.txt",))
    assert hashes == [{"path": "a.txt", "sha256": sha256_bytes(b"one\n")}]
    with pytest.raises(ReleaseError):
        source.compose_file_hashes(local_gate(), repo, head, ("missing.yml",))


def test_check_selection_mirrors_the_ci_jobs_per_change_class() -> None:
    frontend = source.select_checks(["FRONTEND_UI"])
    assert {"frontend-typecheck", "frontend-test", "frontend-build"} <= set(frontend)
    assert "backend-pytest" not in frontend
    backend = source.select_checks(["BACKEND_DOMAIN"])
    assert {"backend-ruff", "backend-mypy", "backend-pytest", "contract-tests"} <= set(backend)
    tooling = source.select_checks(["CI_TOOLING"])
    assert {"release-ruff", "release-mypy", "release-pytest", "check_secrets"} <= set(tooling)
    for chosen in (frontend, backend, tooling, source.select_checks(["DOCS_ONLY"])):
        assert {"check_secrets", "check_architecture", "deploy-pytest", "pre-pr-check"} <= set(
            chosen
        )
        assert len(chosen) == len(set(chosen))
    union = source.select_checks(["FRONTEND_UI", "ASSISTANT"], ("backend-ruff",))
    assert {"assistant-pytest", "frontend-build", "backend-ruff"} <= set(union)
    for bad in ([], ["NOT_A_CLASS"]):
        with pytest.raises(ReleaseError):
            source.select_checks(bad)
    with pytest.raises(ReleaseError):
        source.select_checks(["DOCS_ONLY"], ("no-such-check",))


def test_every_ci_job_is_mirrored_or_listed_as_not_run() -> None:
    workflow = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    jobs = {
        line.strip().rstrip(":")
        for line in workflow.split("jobs:", 1)[1].splitlines()
        if line.startswith("  ") and not line.startswith("   ") and line.strip().endswith(":")
    }
    mirrored = {check.ci_job for check in source.CHECKS.values() if check.ci_job}
    manual = set(source.MANUAL_CI_JOBS) | {"e2e-shards"}  # e2e-shards is the body of the e2e job
    assert jobs == mirrored | manual, "ci.yml changed: update the local mirror"


def test_checks_record_pass_fail_and_not_run_honestly(tmp_path: Path) -> None:
    class Scripted:
        def run(self, command: Command) -> Result:
            return (
                Result(1, "boom\nlast line")
                if "check_secrets" in " ".join(command.argv)
                else Result(0)
            )

    names = ["check_secrets", "check_architecture"]
    executed = source.run_checks(Gate(Scripted(), Mode.LOCAL, AuditLog()), REPO, names)
    by_name = {r["name"]: r for r in executed}
    assert (
        by_name["check_secrets"]["status"] == "FAIL"
        and "last line" in by_name["check_secrets"]["detail"]
    )
    assert by_name["check_architecture"]["status"] == "PASS"
    for job in source.MANUAL_CI_JOBS:
        assert by_name[f"ci-job:{job}"]["status"] == "NOT_RUN"

    class Unreachable:
        def run(self, command: Command) -> Result:
            raise AssertionError("plan-only must not run a check")

    for mode in (Mode.PLAN_ONLY, Mode.DRY_RUN):
        planned = source.run_checks(Gate(Unreachable(), mode, AuditLog()), REPO, names)
        assert all(r["status"] == "NOT_RUN" for r in planned), "an unexecuted check is never a pass"


# -- images ----------------------------------------------------------------------------------


class LocalDocker:
    """Answers ``docker image inspect`` and in-image hashing without Docker."""

    def __init__(self, image_id: str, files: dict[str, bytes], arch: str = "amd64") -> None:
        self.image_id, self.files, self.arch = image_id, files, arch
        self.seen: list[Command] = []

    def run(self, command: Command) -> Result:
        self.seen.append(command)
        argv = command.argv
        if argv[:3] == ("docker", "image", "inspect"):
            info = {"Id": self.image_id, "Os": "linux", "Architecture": self.arch}
            return Result(0, json.dumps(info))
        if argv[:2] == ("docker", "run"):
            lines = [f"{sha256_bytes(data)}  ./{name}" for name, data in self.files.items()]
            return Result(0, "\n".join(lines) + "\n")
        if argv[:2] == ("git", "ls-tree"):
            records = [f"100644 blob {name}\tsrc/{name}" for name in ("a.py", "b.py")]
            return Result(0, "\0".join(records) + "\0")
        if argv[:2] == ("git", "cat-file"):
            return Result(0, raw=f"content of {argv[-1]}".encode())
        return Result(1, "", "unexpected")


def test_existing_candidate_is_accepted_only_by_its_exact_image_id() -> None:
    wanted = "sha256:" + "a" * 64
    docker = LocalDocker(wanted, {})
    gate = Gate(docker, Mode.LOCAL, AuditLog())
    assert images.accept_existing(gate, "clm-rc-frontend:x", wanted)["Id"] == wanted
    for bad, code in (("sha256:" + "b" * 64, "WRONG_IMAGE_ID"), ("a" * 12, "IMAGE_ID_NOT_EXACT")):
        with pytest.raises(StopCondition) as refused:
            images.accept_existing(gate, "clm-rc-frontend:x", bad)
        assert refused.value.code == code
    arm = Gate(LocalDocker(wanted, {}, arch="arm64"), Mode.LOCAL, AuditLog())
    with pytest.raises(StopCondition) as platform:
        images.accept_existing(arm, "clm-rc-frontend:x", wanted)
    assert platform.value.code == "WRONG_PLATFORM"
    assert not [c for c in docker.seen if c.argv[:2] == ("docker", "build")], "never rebuilt"


def test_in_image_file_equality_detects_changed_missing_and_extra_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        catalog.SERVICES,
        "frontend",
        catalog.Service(
            "frontend",
            "FRONTEND_IMAGE",
            "r",
            "c",
            "LOW",
            False,
            True,
            in_image_paths=(("src", "/app/src"),),
        ),
    )
    same = {"a.py": b"content of a.py", "b.py": b"content of b.py"}
    cases: list[tuple[dict[str, bytes], str, int]] = [
        (same, "PASS", 0),
        ({**same, "a.py": b"tampered"}, "FAIL", 1),
        ({"a.py": same["a.py"]}, "FAIL", 1),
        ({**same, "extra.py": b"unreviewed"}, "FAIL", 1),
    ]
    for files, status, mismatches in cases:
        gate = Gate(LocalDocker("sha256:" + "a" * 64, files), Mode.LOCAL, AuditLog())
        result = images.file_equality(gate, REPO, "c" * 40, "frontend", "img")
        assert (result["status"], result["mismatches"]) == (status, mismatches)
    planned = Gate(LocalDocker("sha256:" + "a" * 64, same), Mode.PLAN_ONLY, AuditLog())
    assert images.file_equality(planned, REPO, "c" * 40, "frontend", "img")["status"] == "NOT_RUN"


def make_archive(config: bytes, name: str | None = None, entries: int = 1) -> bytes:
    digest = sha256_bytes(config)
    path = f"blobs/sha256/{name or digest}"
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as bundle:
        for member, data in (
            (path, config),
            ("manifest.json", json.dumps([{"Config": path}] * entries).encode()),
        ):
            info = tarfile.TarInfo(member)
            info.size = len(data)
            bundle.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def test_archive_identity_is_the_config_digest_and_refuses_a_damaged_archive() -> None:
    config = b'{"architecture":"amd64"}'
    data = make_archive(config)
    digest, archive_hash = images.archive_identity(io.BytesIO(data))
    assert digest == "sha256:" + sha256_bytes(config) and archive_hash == sha256_bytes(data)
    for broken in (make_archive(config, name="f" * 64), make_archive(config, entries=2)):
        with pytest.raises(StopCondition) as refused:
            images.archive_identity(io.BytesIO(broken))
        assert refused.value.code == "ARCHIVE_INVALID"


# Real commits on main whose case-snapshot schema is fixed history: the C9 release (#189) and
# the parent of #195 write schema 20; #195 introduced schema 21. The repository needs full
# history (the release tool already reads commits by id); no network is used.
SCHEMA_HISTORY = (
    ("db669caa67b7c4095703ad682fd6d3b7d5ca3793", 20),
    ("68125abf9107cad18c1aa8796064cdccc904a1c4", 20),
    ("8e1f87aada2866537fda1d6f950dd2e3382188d8", 21),
)


def test_backend_schema_version_is_read_from_the_commit() -> None:
    def show(spec: str) -> str:
        done = subprocess.run(
            ["git", "show", spec], cwd=REPO, capture_output=True, text=True, check=False
        )
        assert done.returncode == 0, f"{spec} is not available in this clone"
        return done.stdout

    gate = local_gate()
    for commit, expected in SCHEMA_HISTORY:
        assert images.backend_snapshot_schema(gate, REPO, commit) == expected, commit
    # HEAD's expectation comes from the type annotation at that commit, not a stale constant.
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.strip()
    annotated = re.search(
        r"^CASE_SNAPSHOT_SCHEMA_VERSION: Literal\[(\d+)\]",
        show(f"{head}:{images.SCHEMA_SOURCE}"),
        re.MULTILINE,
    )
    assert annotated, "the schema constant at HEAD has no Literal annotation"
    assert int(annotated.group(1)) >= 21
    assert images.backend_snapshot_schema(gate, REPO, head) == int(annotated.group(1))


# -- effective configuration: policy ---------------------------------------------------------


def baseline(set_name: str) -> dict[str, Any]:
    return copy.deepcopy(render.load_baseline()[set_name])


def refuse(
    set_name: str, summary: dict[str, Any], declared: dict[str, Any] | None = None
) -> StopCondition:
    with pytest.raises(StopCondition) as refused:
        render.check_summary(set_name, summary, declared or {})
    return refused.value


@pytest.mark.parametrize("set_name", sorted(catalog.OVERLAY_SETS))
def test_reviewed_baseline_passes_its_own_policy(set_name: str) -> None:
    render.check_summary(set_name, baseline(set_name), {})


def test_undeclared_network_port_or_variable_is_refused() -> None:
    for kind, value in (
        ("networks", "database"),
        ("ports", "8443:8443/tcp"),
        ("environment", "CLM_NEW_SETTING"),
    ):
        summary = baseline("base")
        summary["services"]["frontend"][kind].append(value)
        stop = refuse("base", summary)
        assert stop.code in {"EFFECTIVE_CONFIG_UNDECLARED", "EFFECTIVE_CONFIG_INVARIANT"}
    summary = baseline("assistant")
    summary["services"]["assistant"]["environment"].append("ASSISTANT_NEW_LIMIT")
    assert refuse("assistant", summary).code == "EFFECTIVE_CONFIG_UNDECLARED"
    render.check_summary(
        "assistant", summary, {"assistant": {"environment": ["ASSISTANT_NEW_LIMIT"]}}
    )


def test_new_service_removed_variable_and_changed_setting_are_refused() -> None:
    extra = baseline("base")
    extra["services"]["frontend"]["environment"].remove("CLM_SITE")
    assert "removal" in refuse("base", extra).message
    changed = baseline("assistant")
    changed["services"]["assistant"]["settings"]["restart"] = "always"
    assert refuse("assistant", changed).code == "EFFECTIVE_CONFIG_UNDECLARED"
    render.check_summary("assistant", changed, {"assistant": {"settings": ["restart"]}})
    sidecar = baseline("base")
    sidecar["services"]["sidecar"] = copy.deepcopy(sidecar["services"]["frontend"])
    assert refuse("base", sidecar).code == "EFFECTIVE_CONFIG_INVARIANT"


def test_assistant_networking_is_protected_even_when_declared() -> None:
    uplink = baseline("assistant")
    uplink["services"]["assistant"]["networks"].append("assistant-uplink")
    declared = {"assistant": {"networks": ["assistant-uplink", "default"]}}
    assert (
        "uplink network without the provider overlay"
        in refuse("assistant", uplink, declared).message
    )
    internet = baseline("assistant")
    internet["services"]["assistant"]["networks"].append("default")
    assert refuse("assistant", internet, declared).code == "EFFECTIVE_CONFIG_INVARIANT"
    published = baseline("assistant")
    published["services"]["assistant"]["ports"].append("8100:8100/tcp")
    assert (
        "only the frontend"
        in refuse("assistant", published, {"assistant": {"ports": ["8100:8100/tcp"]}}).message
    )
    model = baseline("assistant")
    model["services"]["assistant"]["safe_values"]["AI_ASSISTANT_LLM_BASE_URL"] = (
        "https://api.example.invalid/v1"
    )
    assert "closed local port" in refuse("assistant", model).message
    provider = baseline("assistant")
    provider["services"]["assistant"]["environment"].append("ASSISTANT_HOSTING_PROVIDER")
    assert "provider configured" in refuse("assistant", provider).message
    key = baseline("assistant-provider")
    key["services"]["assistant"]["environment"].append("AI_ASSISTANT_ANTHROPIC_API_KEY")
    assert "credential variable" in refuse("assistant-provider", key).message


def test_goldtier_and_backend_networking_is_protected_even_when_declared() -> None:
    writes = baseline("goldtier")
    writes["services"]["backend"]["safe_values"]["GOLDTIER_SANDBOX_ALLOW_WRITES"] = "true"
    assert (
        "writes are not refused"
        in refuse("goldtier", writes, {"backend": {"settings": ["safe_values"]}}).message
    )
    routed = baseline("goldtier")
    routed["services"]["backend"]["networks"].append("goldtier-uplink")
    assert (
        "forbidden network"
        in refuse("goldtier", routed, {"backend": {"networks": ["goldtier-uplink"]}}).message
    )
    internet = baseline("base")
    internet["services"]["backend"]["networks"].append("default")
    assert (
        refuse("base", internet, {"backend": {"networks": ["default"]}}).code
        == "EFFECTIVE_CONFIG_INVARIANT"
    )
    opened = baseline("goldtier")
    opened["networks"]["goldtier-control"]["internal"] = False
    assert "must be internal" in refuse("goldtier", opened).message
    proxy = baseline("goldtier")
    proxy["services"]["goldtier-egress"]["networks"].append("proxy")
    assert "forbidden network" in refuse("goldtier", proxy).message
    capable = baseline("base")
    capable["services"]["backend"]["settings"]["cap_drop"] = []
    assert "capabilities" in refuse("base", capable).message


def test_mongo_volume_must_stay_external_and_mongo_stays_private() -> None:
    owned = baseline("base")
    owned["volumes"]["mongo-data"]["external"] = False
    assert "must be external" in refuse("base", owned).message
    exposed = baseline("base")
    exposed["services"]["mongo"]["ports"].append("27017:27017/tcp")
    assert "only the frontend" in refuse("base", exposed).message
    bridged = baseline("base")
    bridged["services"]["mongo"]["networks"].append("proxy")
    assert "forbidden network" in refuse("base", bridged).message
    for setting, value in (("privileged", True), ("network_mode", "host"), ("replicas", 2)):
        risky = baseline("base")
        risky["services"]["backend"]["settings"][setting] = value
        assert refuse("base", risky).code == "EFFECTIVE_CONFIG_INVARIANT"
    socket = baseline("base")
    socket["services"]["frontend"]["volumes"].append("bind::/var/run/docker.sock:rw")
    assert refuse("base", socket).code == "EFFECTIVE_CONFIG_INVARIANT"


def test_summary_drops_every_environment_value_except_the_safe_switches() -> None:
    document = {
        "name": "clm-staging",
        "services": {
            "backend": {
                "image": "x",
                "environment": {
                    "MONGO_URI": "placeholder-connection-setting-with-a-secret",
                    "PHASE13_SUPPORT_USER_PASSWORD_HASH": "scrypt-value",
                    "GOLDTIER_SANDBOX_ALLOW_WRITES": "false",
                },
                "networks": {"proxy": {"ipv4_address": "172.30.240.3"}, "database": None},
            }
        },
    }
    text = json.dumps(summarise(document))
    assert "connection-setting" not in text and "scrypt-value" not in text
    assert '"GOLDTIER_SANDBOX_ALLOW_WRITES": "false"' in text and "MONGO_URI" in text


# -- effective configuration: real offline render --------------------------------------------


@needs_docker
def test_baseline_is_exactly_what_the_compose_files_render_today() -> None:
    fresh = render.build_baseline(local_gate(Mode.PLAN_ONLY), REPO)
    assert fresh == render.load_baseline(), "Compose files changed: review and rewrite the baseline"


@needs_docker
def test_real_render_keeps_goldtier_and_assistant_boundaries() -> None:
    gate = local_gate(Mode.PLAN_ONLY)
    full = render.render_set(gate, REPO, "full-provider-goldtier")
    services = full["services"]
    assert services["assistant"]["networks"] == ["assistant-uplink", "proxy"]
    assert services["backend"]["networks"] == ["database", "goldtier-control", "proxy"]
    assert services["backend"]["safe_values"]["GOLDTIER_SANDBOX_ALLOW_WRITES"] == "false"
    assert services["mongo"]["networks"] == ["database"]
    assert [n for n, s in services.items() if s["ports"]] == ["frontend"]
    assert (
        full["volumes"]["mongo-data"]["external"] and full["volumes"]["assistant-data"]["external"]
    )
    model_free = render.render_set(gate, REPO, "assistant")["services"]["assistant"]
    assert model_free["networks"] == ["proxy"]
    assert model_free["safe_values"]["AI_ASSISTANT_LLM_BASE_URL"] == render.MODEL_FREE_BASE_URL


@needs_docker
def test_release_validation_renders_every_wrapper_it_touches() -> None:
    manifest = make_manifest(["frontend", "assistant"])
    assert render.validate_release_config(local_gate(Mode.PLAN_ONLY), REPO, manifest) == [
        "assistant",
        "base",
    ]


@needs_docker
def test_render_refuses_a_compose_file_that_adds_a_network(tmp_path: Path) -> None:
    for relative in catalog.OVERLAY_ORDER:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO / relative, target)
    overlay = tmp_path / catalog.COMPOSE_ASSISTANT
    text = overlay.read_text(encoding="utf-8").replace(
        "        aliases: [clm-assistant-proxy]\n",
        "        aliases: [clm-assistant-proxy]\n      default: {}\n",
    )
    overlay.write_text(text, encoding="utf-8")
    gate = local_gate(Mode.PLAN_ONLY)
    with pytest.raises(StopCondition) as refused:
        render.validate_release_config(gate, tmp_path, make_manifest(["assistant"]))
    assert (
        refused.value.code == "EFFECTIVE_CONFIG_INVARIANT" and "assistant" in refused.value.message
    )
    # The whole-stack render is refused whichever service the release changes.
    with pytest.raises(StopCondition):
        render.validate_release_config(gate, tmp_path, make_manifest(["frontend"]))


def test_render_is_a_local_read_so_it_runs_in_plan_only_mode() -> None:
    seen: list[Command] = []

    class Capture:
        def run(self, command: Command) -> Result:
            seen.append(command)
            return Result(1, "", "stop here")

    with pytest.raises(StopCondition):
        render.render_set(Gate(Capture(), Mode.PLAN_ONLY, AuditLog()), REPO, "base")
    assert seen[0].effect is Effect.LOCAL_READ and "--no-path-resolution" in seen[0].argv
    assert "MONGO_URI" in (seen[0].env or {}) and "mongodb" not in (seen[0].env or {})["MONGO_URI"]


F2_BRANCH = "origin/release/f2-ai-insights-notice-c5a1c7f4"


def f2_commit(repo: Path) -> tuple[str, str]:
    (repo / "f2.txt").write_text("f2\n", encoding="utf-8")
    git(repo, "add", "f2.txt")
    git(repo, "commit", "-q", "-m", "f2 release")
    head, tree = git(repo, "rev-parse", "HEAD"), git(repo, "rev-parse", "HEAD^{tree}")
    git(repo, "update-ref", f"refs/remotes/{F2_BRANCH}", head)
    return head, tree


def test_f2_lineage_accepts_only_its_pinned_commit_and_tree(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    head, tree = f2_commit(repo)
    # The shipped pin names the real qualified commit, so a test commit is refused.
    with pytest.raises(StopCondition) as unpinned:
        source.verify_source(local_gate(), repo, commit=head, tree=tree, base_ref=F2_BRANCH)
    assert unpinned.value.code == "RELEASE_IDENTITY_NOT_PINNED"
    monkeypatch.setitem(source.PINNED_RELEASE_IDENTITIES, "F2_FRONTEND_LINEAGE", (head, tree))
    state = source.verify_source(local_gate(), repo, commit=head, tree=tree, base_ref=F2_BRANCH)
    assert (state.base_ref, state.base_reason) == (F2_BRANCH, "F2_FRONTEND_LINEAGE")
    # A later commit on the same branch is refused even with its own tree.
    (repo / "f2.txt").write_text("later\n", encoding="utf-8")
    git(repo, "commit", "-q", "-am", "later")
    later, later_tree = git(repo, "rev-parse", "HEAD"), git(repo, "rev-parse", "HEAD^{tree}")
    git(repo, "update-ref", f"refs/remotes/{F2_BRANCH}", later)
    with pytest.raises(StopCondition) as moved:
        source.verify_source(local_gate(), repo, commit=later, tree=later_tree, base_ref=F2_BRANCH)
    assert moved.value.code == "RELEASE_IDENTITY_NOT_PINNED"


@pytest.mark.parametrize(
    "base",
    [
        "origin/release/f2-ai-insights-c5a1c7f5",
        "origin/release/f2-ai-insights-notice-c5a1c7f4-2",
        "origin/release/f2-ai-insights-c5a1c7f4",
        "release/f2-ai-insights-c5a1c7f4",
    ],
)
def test_no_other_f2_like_base_is_allowed(base: str) -> None:
    with pytest.raises(StopCondition) as refused:
        source.release_base_reason(base)
    assert refused.value.code == "BASE_REF_NOT_ALLOWED"
