"""Offline-only Mongo recovery drill. All Docker targets are generated here."""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

MONGO = "mongo@sha256:b6421fd6d1c5ded6377b397d8983e2f82e2100dc5123332dcfda2065a472be5b"
BASE = "671882a9ef2f60c1da5a79139eacb572c87cc2f4"
FIXTURE = Path(__file__).with_name("recovery_fixture.py")
ROOT = FIXTURE.resolve().parents[2]
CANDIDATE_PATHS = (
    "deploy/recovery/README.md",
    "deploy/recovery/offline_drill.py",
    "deploy/recovery/recovery_fixture.py",
)
BACKEND = (
    "ghcr.io/shaneqwaszx/clm-aws-demo-backend@"
    "sha256:313e882248e3b72e9237bf4419a497a02ad32251ff9d597226c47d9732d40733"
)


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def output(*args, **kwargs):
    return run(*args, stdout=subprocess.PIPE, **kwargs).stdout.decode().rstrip("\r\n")


def digest(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def source_provenance():
    def git(*args):
        return output("git", "-C", ROOT, "--work-tree=.", *args)

    head = git("rev-parse", "HEAD")
    if head != BASE:
        raise RuntimeError("Approved source revision required")
    status = git(
        "status", "--porcelain=v1", "--untracked-files=all", "--ignore-submodules=none",
    )
    changes = {}
    for line in status.splitlines():
        state, path = line[:2], line[3:]
        if path not in CANDIDATE_PATHS or state not in {"??", " M", "M ", "MM", "A ", "AM"}:
            raise RuntimeError("Unexpected worktree changes outside the recovery candidate")
        changes[path] = state
    app = "apps/backend/app"
    if git("ls-files", "--others", "--ignored", "--exclude-standard", "--", app):
        raise RuntimeError("Unexpected ignored files in the mounted application tree")
    if any(not line.startswith("H ") for line in git("ls-files", "-v", "--", app).splitlines()):
        raise RuntimeError("Application source contains hidden index entries")
    return {
        "source_commit": head,
        "application_tree_clean": True,
        "worktree_clean": not changes,
        "candidate_files": {
            path: {"git_status": changes.get(path, "  "), "sha256": digest(ROOT / path)}
            for path in CANDIDATE_PATHS
        },
    }


def verify(path, manifest):
    if path.stat().st_size != manifest["bytes"] or digest(path) != manifest["sha256"]:
        raise ValueError("Ciphertext length or SHA-256 mismatch")


def export(openssl, source, database, certificate, archive):
    dump = [
        "docker", "exec", source, "mongodump", "--db", database, "--gzip", "--archive"
    ]
    with subprocess.Popen(dump, stdout=subprocess.PIPE) as producer:
        try:
            run(
                openssl, "cms", "-encrypt", "-binary", "-stream", "-aes-256-gcm",
                "-outform", "DER", "-out", archive, certificate,
                stdin=producer.stdout,
            )
        finally:
            producer.stdout.close()
        if producer.wait() != 0:
            raise RuntimeError("mongodump failed")


def mongo_ready(name):
    for _ in range(60):
        probe = subprocess.run(
            ["docker", "exec", name, "mongosh", "--quiet", "--eval",
             "if (!db.adminCommand({ping:1}).ok) quit(1)"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
        )
        if probe.returncode == 0:
            return
        time.sleep(1)
    raise RuntimeError("Disposable Mongo did not become ready")


def fixture(network, image, mongo, database, action, *, baseline=False):
    args = ["docker", "run", "--rm", "-i", "--pull=never", "--network", network]
    if baseline:
        app = ROOT / "apps" / "backend" / "app"
        args += ["--mount", f"type=bind,source={app},target=/phase1/apps/backend/app,readonly",
                 "-e", "PYTHONPATH=/phase1/apps/backend"]
    return json.loads(output(
        *args, "--entrypoint", "python", image, "-", mongo, database, action,
        input=FIXTURE.read_bytes(),
    ))


def drill(openssl, fixture_image, qualify):
    provenance = source_provenance()
    if os.environ.get("DOCKER_HOST") or os.environ.get("DOCKER_CONTEXT"):
        raise RuntimeError("Unset Docker endpoint overrides before this local drill")
    endpoint = output("docker", "context", "inspect", "-f", "{{.Endpoints.docker.Host}}")
    if endpoint not in {
        "unix:///var/run/docker.sock",
        "npipe:////./pipe/docker_engine",
        "npipe:////./pipe/dockerDesktopLinuxEngine",
    }:
        raise RuntimeError("A supported local Docker endpoint is required")
    fixture_image = output("docker", "image", "inspect", "-f", "{{.Id}}", fixture_image)
    suffix = uuid4().hex
    database = f"clm_recovery_{suffix}"
    if not re.fullmatch(r"clm_recovery_[0-9a-f]{32}", database):
        raise RuntimeError("Disposable database allowlist failed")
    source, target = (f"{database}-{role}" for role in ("source", "restore"))
    resources = []
    network = database
    try:
        run("docker", "network", "create", "--internal", network, stdout=subprocess.DEVNULL)
        resources.append(("network", "rm", network))
        if output("docker", "network", "inspect", "-f", "{{.Internal}}", network) != "true":
            raise RuntimeError("Expected an internal Docker network")
        for name in (source, target):
            volume = f"{name}-data"
            run("docker", "volume", "create", volume, stdout=subprocess.DEVNULL)
            resources.append(("volume", "rm", volume))
            run("docker", "create", "--pull=never", "--name", name, "--network", network,
                "--mount", f"type=volume,source={volume},target=/data/db", MONGO,
                stdout=subprocess.DEVNULL)
            resources.append(("container", "rm", "-f", "-v", name))
            run("docker", "start", name, stdout=subprocess.DEVNULL)
            mongo_ready(name)

        original = fixture(network, fixture_image, source, database, "seed", baseline=True)
        mongo = json.loads(output(
            "docker", "exec", source, "mongosh", "--quiet", "--eval",
            "JSON.stringify({version:db.version(),fcv:db.adminCommand("
            "{getParameter:1,featureCompatibilityVersion:1}).featureCompatibilityVersion.version})",
        ))
        with tempfile.TemporaryDirectory(prefix="clm-recovery-") as directory:
            root = Path(directory)
            key, cert = root / "key.pem", root / "recipient.pem"
            archive, download = root / "backup.cms", root / "download.cms"
            config = root / "openssl.cnf"
            config.write_text("[req]\ndistinguished_name=dn\n[dn]\n", encoding="ascii")
            run(openssl, "req", "-config", config, "-x509", "-newkey", "rsa:3072", "-noenc",
                "-sha256",
                "-days", "1", "-subj", "/CN=Disposable Recovery Drill", "-keyout", key,
                "-out", cert, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

            start = time.monotonic()
            boundary = datetime.now(UTC).isoformat()
            export(openssl, source, database, cert, archive)
            manifest = {
                "format": "mongo-gzip-archive/cms-aes-256-gcm/v1",
                "baseline": provenance["source_commit"], "source_provenance": provenance,
                "boundary_utc": boundary, "database": database,
                "mongo_image": MONGO, "mongo": mongo, "schema_version": 20,
                "fixture_runtime_image_id": fixture_image,
                "recipient_certificate_sha256": digest(cert),
                "sha256": digest(archive), "bytes": archive.stat().st_size,
            }
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            backup_seconds = round(time.monotonic() - start, 2)

            # The filesystem copy models the transfer boundary; the drill uses no AWS.
            shutil.copyfile(archive, download)
            downloaded_manifest_path = root / "download.json"
            shutil.copyfile(manifest_path, downloaded_manifest_path)
            downloaded_manifest = json.loads(downloaded_manifest_path.read_text(encoding="utf-8"))
            with download.open("r+b") as file:
                file.seek(manifest["bytes"] // 2)
                byte = file.read(1)
                file.seek(-1, os.SEEK_CUR)
                file.write(bytes([byte[0] ^ 1]))
            try:
                verify(download, downloaded_manifest)
            except ValueError:
                print("Corrupted download rejected before decrypt and restore", flush=True)
            else:
                raise RuntimeError("Corruption check failed")
            corrupted_decrypt = subprocess.run(
                [openssl, "cms", "-decrypt", "-binary", "-inform", "DER", "-in",
                 download, "-recip", cert, "-inkey", key],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
            )
            if corrupted_decrypt.returncode == 0:
                raise RuntimeError("Authenticated decryption accepted corrupted ciphertext")
            print("CMS authentication independently rejected the corrupt copy", flush=True)
            shutil.copyfile(archive, download)

            start = time.monotonic()
            verify(download, downloaded_manifest)
            # Authenticate all bytes before allowing mongorestore to change the destination.
            plaintext = root / "authenticated.archive.gz"
            with plaintext.open("xb") as file:
                run(openssl, "cms", "-decrypt", "-binary", "-inform", "DER",
                    "-in", download, "-recip", cert, "-inkey", key, stdout=file)
            run("docker", "exec", target, "mongosh", "--quiet", database, "--eval",
                "if (db.getCollectionNames().length !== 0) quit(1)")
            with plaintext.open("rb") as file:
                run("docker", "exec", "-i", target, "mongorestore", "--gzip", "--archive",
                    "--nsInclude", f"{database}.*", "--stopOnError", stdin=file)
            plaintext.unlink()
            restored = fixture(network, fixture_image, target, database, "inspect", baseline=True)
            if original != restored:
                raise RuntimeError("Restored data or indexes differ")
            restore_seconds = round(time.monotonic() - start, 2)
            if not qualify:
                regression = fixture(
                    network, fixture_image, target, database, "regression", baseline=True,
                )
                print(json.dumps({"baseline_cas_regression": regression["cas"]}), flush=True)
            if source_provenance() != provenance:
                raise RuntimeError("Source or candidate changed during the rehearsal")
            print(json.dumps({
                "manifest": manifest, "validated": restored["summary"],
                "backup_seconds": backup_seconds,
                "restore_and_validation_seconds": restore_seconds,
            }), flush=True)
            if qualify:
                print(f"Qualifying cached backend {BACKEND}", flush=True)
                result = fixture(network, BACKEND, target, database, "qualify")
                print(json.dumps({"backend": BACKEND, "compatibility": result}), flush=True)
    finally:
        cleanup_failed = False
        for resource in reversed(resources):
            cleanup_failed |= subprocess.run(
                ["docker", *resource], stdout=subprocess.DEVNULL, check=False,
            ).returncode != 0
        if cleanup_failed:
            raise RuntimeError(f"Disposable resource cleanup failed for {database}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openssl", default="openssl")
    parser.add_argument("--fixture-image", required=True, help="Local Python/backend runtime")
    parser.add_argument("--qualify-cached-backend", action="store_true")
    arguments = parser.parse_args()
    drill(arguments.openssl, arguments.fixture_image, arguments.qualify_cached_backend)
