"""Image candidates: accept an existing exact image by id, or build one, then prove its content.

A qualified image is published as built. Nothing here rebuilds an accepted image, because the
backend and frontend Dockerfiles use floating base tags and a rebuild could differ.
"""

from __future__ import annotations

import hashlib
import json
import re
import tarfile
from pathlib import Path
from typing import IO, Any

from . import catalog
from .core import Command, Effect, Gate, ReleaseError, StopCondition, sha256_bytes

DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
DOCKERFILES = {
    "frontend": ("deploy/frontend.Dockerfile", True),
    "backend": ("deploy/backend.Dockerfile", True),
    "assistant": ("apps/assistant/deploy/assistant.Dockerfile", False),
    "goldtier-egress": ("deploy/egress/Dockerfile", False),
}
FINGERPRINT_CODE = (
    "from ai_assistant.model_qualification import qualification_basis; print(qualification_basis())"
)


def inspect_image(gate: Gate, reference: str) -> dict[str, Any]:
    result = gate.run(
        Command(
            ("docker", "image", "inspect", "--format", "{{json .}}", reference),
            Effect.LOCAL_READ,
            f"inspect local image {reference}",
            quiet=True,
        )
    )
    if result.returncode != 0:
        raise StopCondition("IMAGE_MISSING", f"local image {reference} not found")
    return json.loads(result.stdout)  # type: ignore[no-any-return]


def accept_existing(gate: Gate, reference: str, expected_id: str) -> dict[str, Any]:
    """Accept a local candidate only if its image id is exactly the expected one."""

    if not DIGEST.match(expected_id):
        raise StopCondition("IMAGE_ID_NOT_EXACT", "give the full sha256 image id")
    info = inspect_image(gate, reference)
    if info.get("Id") != expected_id:
        raise StopCondition(
            "WRONG_IMAGE_ID", f"{reference} is not the expected image; it was not rebuilt"
        )
    platform = f"{info.get('Os')}/{info.get('Architecture')}"
    if platform != catalog.PLATFORM:
        raise StopCondition("WRONG_PLATFORM", f"{reference} is {platform}, not {catalog.PLATFORM}")
    return info


def export_context(gate: Gate, root: Path, commit: str, destination: Path) -> Path:
    """Export the exact commit, with no line-ending conversion, as the build context."""

    if destination.exists() and any(destination.iterdir()):
        raise StopCondition("CONTEXT_NOT_EMPTY", "the build context directory must be empty")
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination.parent / f"{destination.name}.tar"
    result = gate.run(
        Command(
            (
                "git",
                "-c",
                "core.autocrlf=false",
                "-c",
                "core.eol=lf",
                "archive",
                "--format=tar",
                "-o",
                str(archive),
                commit,
            ),
            Effect.LOCAL_WRITE,
            "export the approved commit as a build context",
            cwd=str(root),
        )
    )
    if result.skipped:
        return destination
    if result.returncode != 0:
        raise ReleaseError("GIT_FAILED", "git archive failed")
    with tarfile.open(archive) as bundle:
        bundle.extractall(destination, filter="data")
    archive.unlink()
    return destination


def build(gate: Gate, context: Path, service: str, tag: str) -> None:
    """Build one linux/amd64 image from an exported commit. Never used for an accepted image."""

    if service not in DOCKERFILES:
        raise ReleaseError("SERVICE_UNKNOWN", f"no Dockerfile for {service}")
    dockerfile, _ = DOCKERFILES[service]
    result = gate.run(
        Command(
            ("docker", "build", "--platform", catalog.PLATFORM, "-f", dockerfile, "-t", tag, "."),
            Effect.LOCAL_WRITE,
            f"build {service} image for {catalog.PLATFORM}",
            cwd=str(context),
            timeout=3600,
        )
    )
    if not result.skipped and result.returncode != 0:
        raise StopCondition("BUILD_FAILED", f"{service} image build failed")


def commit_file_hashes(gate: Gate, root: Path, commit: str, path: str) -> dict[str, str]:
    """SHA-256 of every blob under ``path`` in the commit, read from Git, not the work tree."""

    listing = gate.run(
        Command(
            ("git", "ls-tree", "-r", "-z", commit, "--", path),
            Effect.LOCAL_READ,
            f"list {path} in the commit",
            cwd=str(root),
            quiet=True,
        )
    )
    if listing.returncode != 0:
        raise ReleaseError("GIT_FAILED", "git ls-tree failed")
    hashes: dict[str, str] = {}
    for record in listing.stdout.split("\0"):
        if not record:
            continue
        meta, name = record.split("\t", 1)
        blob = meta.split()[2]
        content = gate.run(
            Command(
                ("git", "cat-file", "blob", blob),
                Effect.LOCAL_READ,
                "read a blob",
                cwd=str(root),
                quiet=True,
                binary=True,
            )
        )
        if content.returncode != 0:
            raise ReleaseError("GIT_FAILED", "git cat-file failed")
        relative = name[len(path) :].lstrip("/")
        hashes[relative] = sha256_bytes(content.raw)
    return hashes


def image_file_hashes(gate: Gate, reference: str, path: str) -> dict[str, str]:
    """SHA-256 of every file under ``path`` inside the image, read with networking disabled."""

    script = (
        f'if [ -d "{path}" ]; then cd "{path}" && find . -type f ! -name "*.pyc" '
        f'-exec sha256sum {{}} +; else sha256sum "{path}"; fi'
    )
    result = gate.run(
        Command(
            (
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--read-only",
                "--entrypoint",
                "sh",
                reference,
                "-c",
                script,
            ),
            Effect.LOCAL_WRITE,
            f"hash {path} inside {reference}",
            timeout=300,
            quiet=True,
        )
    )
    if result.skipped:
        return {}
    if result.returncode != 0:
        raise StopCondition("IMAGE_READ_FAILED", f"could not read {path} from the image")
    hashes: dict[str, str] = {}
    for line in result.stdout.splitlines():
        digest, _, name = line.partition("  ")
        name = name.strip()
        relative = "" if name == path else name.removeprefix("./")
        hashes[relative] = digest.strip()
    return hashes


def file_equality(
    gate: Gate, root: Path, commit: str, service: str, reference: str
) -> dict[str, Any]:
    """Compare the reviewed source files in the image with the commit, in both directions."""

    compared = mismatches = 0
    details: list[str] = []
    for source_path, image_path in catalog.service(service).in_image_paths:
        expected = commit_file_hashes(gate, root, commit, source_path)
        actual = image_file_hashes(gate, reference, image_path)
        if not actual:
            return {
                "status": "NOT_RUN",
                "files_compared": 0,
                "mismatches": 0,
                "detail": "not executed in this mode",
            }
        for name in sorted(set(expected) | set(actual)):
            compared += 1
            if expected.get(name) != actual.get(name):
                mismatches += 1
                if len(details) < 5:
                    details.append(f"{source_path}/{name}".rstrip("/"))
    status = "PASS" if compared and not mismatches else "FAIL"
    detail = (
        "byte-identical to the commit" if status == "PASS" else "differs: " + ", ".join(details)
    )
    return {
        "status": status,
        "files_compared": compared,
        "mismatches": mismatches,
        "detail": detail,
    }


def assistant_fingerprint(gate: Gate, reference: str) -> str | None:
    """``qualification_basis()`` computed inside the image, with networking disabled."""

    result = gate.run(
        Command(
            (
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--read-only",
                "--tmpfs",
                "/tmp",
                "--entrypoint",
                "python",
                reference,
                "-c",
                FINGERPRINT_CODE,
            ),
            Effect.LOCAL_WRITE,
            "compute the assistant qualification fingerprint in the image",
            timeout=300,
        )
    )
    if result.skipped:
        return None
    value = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
    if result.returncode != 0 or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise StopCondition("FINGERPRINT_FAILED", "the image did not return a fingerprint")
    return value


SCHEMA_SOURCE = "apps/backend/app/persistence/models.py"
SCHEMA_LINE = re.compile(r"^CASE_SNAPSHOT_SCHEMA_VERSION\b[^=\n]*=\s*(\d+)\s*$", re.MULTILINE)


def backend_snapshot_schema(gate: Gate, root: Path, commit: str) -> int | None:
    """The case-snapshot schema a backend built from ``commit`` writes, read from the commit."""

    result = gate.run(
        Command(
            ("git", "show", f"{commit}:{SCHEMA_SOURCE}"),
            Effect.LOCAL_READ,
            "read the case-snapshot schema version from the commit",
            cwd=str(root),
            quiet=True,
        )
    )
    match = SCHEMA_LINE.search(result.stdout) if result.returncode == 0 else None
    return int(match.group(1)) if match else None


def archive_identity(stream: IO[bytes]) -> tuple[str, str]:
    """Read a ``docker save`` archive once and return ``(config digest, archive sha256)``.

    The config digest identifies an image independently of the image store in use, so it is
    the value compared on both sides of a transfer.
    """

    hasher = hashlib.sha256()

    class _Tee:
        def read(self, size: int = -1) -> bytes:
            block = stream.read(size)
            hasher.update(block)
            return block

    config_name: str | None = None
    blobs: dict[str, str] = {}
    with tarfile.open(fileobj=_Tee(), mode="r|") as bundle:  # type: ignore[call-overload]
        for member in bundle:
            if not member.isfile():
                continue
            handle = bundle.extractfile(member)
            if handle is None:
                continue
            if member.name == "manifest.json":
                entries = json.loads(handle.read())
                if len(entries) != 1:
                    raise StopCondition("ARCHIVE_INVALID", "archive must hold exactly one image")
                config_name = entries[0]["Config"]
            elif member.size < 4 * 1024 * 1024:
                blobs[member.name] = sha256_bytes(handle.read())
    while stream.read(1 << 20):  # drain any trailing padding so the hash covers every byte
        pass
    if config_name is None or config_name not in blobs:
        raise StopCondition("ARCHIVE_INVALID", "archive has no readable image configuration")
    digest = blobs[config_name]
    named = Path(config_name).name.removesuffix(".json")
    if re.fullmatch(r"[0-9a-f]{64}", named) and named != digest:
        raise StopCondition("ARCHIVE_INVALID", "image configuration does not match its name")
    return f"sha256:{digest}", hasher.hexdigest()


def describe_candidate(
    gate: Gate, root: Path, commit: str, service: str, reference: str, *, mode: str
) -> dict[str, Any]:
    """The manifest ``images`` entry for one local candidate."""

    info = inspect_image(gate, reference)
    svc = catalog.service(service)
    dockerfile, floating = DOCKERFILES[service]
    # With the classic image store the id is the config digest. With the containerd store it
    # is a manifest digest, so the config digest stays unknown until an archive is read.
    classic = not any("@" in d for d in info.get("RepoDigests") or []) and "Descriptor" not in info
    entry: dict[str, Any] = {
        "repository": svc.repository,
        "local_ref": reference,
        "local_image_id": info["Id"],
        "config_digest": info["Id"] if classic else None,
        "registry_manifest_digest": None,
        "registry_tag": None,
        "platform": f"{info.get('Os')}/{info.get('Architecture')}",
        "build": {
            "mode": mode,
            "dockerfile": dockerfile,
            "floating_base": floating,
            "rebuilt_after_qualification": False,
        },
        "file_equality": file_equality(gate, root, commit, service, reference),
        "assistant_fingerprint": (
            assistant_fingerprint(gate, reference) if service == "assistant" else None
        ),
        "snapshot_schema_writes": (
            backend_snapshot_schema(gate, root, commit) if service == "backend" else None
        ),
    }
    return entry
