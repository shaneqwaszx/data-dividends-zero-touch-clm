"""Publish approved images to GHCR by digest, and move the exact images to the host.

Publication pushes the image that was qualified, as built. It never builds, and it refuses a
local image whose id is no longer the one in the manifest. Every registry command runs with a
throwaway Docker configuration; the token reaches Docker on stdin only.

Two ways to move an image to the host are implemented:

* ``pull``  - the host pulls by registry digest with the read-only token streamed over SSH into
  a temporary Docker configuration under ``/run`` that is removed in the same command (the
  pattern reviewed for Approval B). This is the default.
* ``load``  - ``docker save`` here, copy over SSH, verify the archive hash, ``docker load`` and
  verify the image configuration digest. No registry credential is involved at all.
"""

from __future__ import annotations

import copy
import json
import re
import shlex
import tempfile
from pathlib import Path
from typing import Any

from . import catalog, credstore, images
from .core import Command, Effect, Gate, Secret, StopCondition, sha256_bytes, sha256_file
from .host import Host, safe
from .manifest import Manifest, release_tag

PUSH_DIGEST = re.compile(r"digest:\s*(sha256:[0-9a-f]{64})")
SINGLE_MANIFEST_TYPES = (
    "application/vnd.docker.distribution.manifest.v2+json",
    "application/vnd.oci.image.manifest.v1+json",
)


def _registry(
    gate: Gate,
    env: dict[str, str],
    *argv: str,
    purpose: str,
    write: bool,
    stdin: Secret | None = None,
    timeout: float = 1800,
) -> Any:
    return gate.run(
        Command(
            ("docker", *argv),
            Effect.REGISTRY_WRITE if write else Effect.REGISTRY_READ,
            purpose,
            stdin=stdin,
            env=env,
            timeout=timeout,
        )
    )


def remote_manifest(
    gate: Gate, env: dict[str, str], reference: str
) -> tuple[str, dict[str, Any]] | None:
    """The registry's manifest for ``reference`` and its digest, or None when it is absent."""

    result = gate.run(
        Command(
            ("docker", "buildx", "imagetools", "inspect", "--raw", reference),
            Effect.REGISTRY_READ,
            f"read the registry manifest of {reference}",
            env=env,
            binary=True,
            timeout=120,
        )
    )
    if result.skipped or result.returncode != 0:
        return None
    try:
        document = json.loads(result.raw)
    except ValueError as exc:
        raise StopCondition(
            "REGISTRY_MANIFEST_INVALID", "the registry returned no manifest"
        ) from exc
    return f"sha256:{sha256_bytes(result.raw)}", document


def publish(
    gate: Gate,
    manifest: Manifest,
    services: list[str],
    credential: credstore.StoredCredential,
) -> Manifest:
    """Push each approved image and return a new manifest with the registry digests filled in.

    The caller has already checked the owner approval for the ``publish`` action.
    """

    published = copy.deepcopy(manifest)
    with credstore.temporary_docker_config(gate) as env:
        login = _registry(
            gate,
            env,
            "login",
            catalog.REGISTRY_HOST,
            "--username",
            credential.username,
            "--password-stdin",
            purpose="log in to GHCR with the publish identity",
            write=True,
            stdin=credential.secret,
            timeout=60,
        )
        if not login.skipped and login.returncode != 0:
            raise StopCondition("REGISTRY_LOGIN_FAILED", "GHCR did not accept the publish token")
        try:
            for name in services:
                _publish_one(gate, env, published, name)
        finally:
            _registry(
                gate,
                env,
                "logout",
                catalog.REGISTRY_HOST,
                purpose="log out of GHCR",
                write=True,
                timeout=30,
            )
    published["candidate_manifest_sha256"] = _hash(manifest)
    return published


def _hash(manifest: Manifest) -> str:
    from .manifest import manifest_hash

    return manifest_hash(manifest)


def _publish_one(gate: Gate, env: dict[str, str], manifest: Manifest, name: str) -> None:
    image = manifest["images"][name]
    tag = release_tag(manifest, name)
    if tag in {"latest", ""} or not re.fullmatch(r"rc-[0-9a-f]{12}-[0-9a-f]{12}", tag):
        raise StopCondition("FLOATING_REFERENCE", "refusing a floating or malformed tag")
    reference = f"{image['repository']}:{tag}"
    # The image must still be the qualified one: same id, never rebuilt.
    images.accept_existing(gate, image["local_ref"], image["local_image_id"])
    existing = remote_manifest(gate, env, reference)
    if existing is not None:
        digest, document = existing
        if document.get("config", {}).get("digest") != image["config_digest"]:
            raise StopCondition("TAG_EXISTS", f"{reference} already exists with other content")
        image["registry_manifest_digest"], image["registry_tag"] = digest, tag
        return
    tagged = gate.run(
        Command(
            ("docker", "tag", image["local_image_id"], reference),
            Effect.LOCAL_WRITE,
            f"tag the qualified {name} image for publication",
            env=env,
        )
    )
    if not tagged.skipped and tagged.returncode != 0:
        raise StopCondition("TAG_FAILED", f"could not tag the {name} image")
    pushed = _registry(gate, env, "push", reference, purpose=f"push {name} to GHCR", write=True)
    if pushed.skipped:
        return
    found = PUSH_DIGEST.search(pushed.stdout)
    if pushed.returncode != 0 or found is None:
        raise StopCondition("PUSH_FAILED", f"the {name} image was not pushed")
    digest = found.group(1)
    remote = remote_manifest(gate, env, f"{image['repository']}@{digest}")
    if remote is None:
        raise StopCondition("PUSH_NOT_VERIFIED", f"{name}: the pushed digest cannot be read back")
    remote_digest, document = remote
    if remote_digest != digest:
        raise StopCondition(
            "WRONG_DIGEST", f"{name}: the registry manifest does not hash to {digest}"
        )
    if document.get("mediaType") not in SINGLE_MANIFEST_TYPES:
        raise StopCondition("WRONG_DIGEST", f"{name}: not a single-platform image manifest")
    if document.get("config", {}).get("digest") != image["config_digest"]:
        raise StopCondition(
            "WRONG_DIGEST", f"{name}: the registry image is not the qualified image configuration"
        )
    image["registry_manifest_digest"], image["registry_tag"] = digest, tag


# --------------------------------------------------------------------------------------------
# Moving the exact image to the host
# --------------------------------------------------------------------------------------------

PULL_SCRIPT = """set -u; umask 077
a="$(sudo -n mktemp -d /run/clm-ghcr.XXXXXXXX)" || exit 12
c() { sudo -n sh -c 'rm -f "$1/config.json"; rmdir "$1"' sh "$a" 2>/dev/null; }
trap c EXIT HUP INT TERM
printf '%s\\n' '{"auths":{"ghcr.io":{}}}' | sudo -n tee "$a/config.json" >/dev/null || exit 12
sudo -n docker --config "$a" login ghcr.io --username __USER__ --password-stdin \\
  >/dev/null 2>&1; l=$?
p=1
if [ "$l" = 0 ]; then
  sudo -n docker --config "$a" image pull --quiet --platform linux/amd64 __REF__ \\
    >/dev/null 2>&1; p=$?
fi
sudo -n docker --config "$a" logout ghcr.io >/dev/null 2>&1
sudo -n sh -c 'rm -f "$1/config.json"; rmdir "$1"' sh "$a"
left="$(sudo -n find /run -maxdepth 1 -name 'clm-ghcr.*' | wc -l)"
echo "login=$l pull=$p auth_dirs_left=$left"
[ "$l" = 0 ] && [ "$p" = 0 ] && [ "$left" = 0 ]"""


def host_pull(
    host: Host, manifest: Manifest, name: str, credential: credstore.StoredCredential
) -> str:
    """Pull one image by digest on the host. The token is never stored there."""

    image = manifest["images"][name]
    digest = image["registry_manifest_digest"]
    if digest is None:
        raise StopCondition("REGISTRY_DIGEST_UNKNOWN", f"{name}: publish before deploying")
    reference = f"{image['repository']}@{digest}"
    script = PULL_SCRIPT.replace("__USER__", shlex.quote(safe(credential.username))).replace(
        "__REF__", shlex.quote(safe(reference))
    )
    result = host.write(script, f"pull {name} by digest on the host", stdin=credential.secret)
    if result.skipped:
        return reference
    if result.returncode != 0 or "auth_dirs_left=0" not in result.stdout:
        raise StopCondition(
            "IMAGE_PULL_FAILED", f"{name}: the host could not pull the approved digest"
        )
    verify_host_image(host, manifest, name, reference)
    return reference


def host_load(gate: Gate, host: Host, manifest: Manifest, name: str) -> str:
    """Copy one image over SSH and load it, verifying the archive and the image identity."""

    image = manifest["images"][name]
    images.accept_existing(gate, image["local_ref"], image["local_image_id"])
    reference = f"{image['repository']}:{release_tag(manifest, name)}"
    incoming = f"{host.profile.state_dir}/incoming-{release_tag(manifest, name)}.tar"
    with tempfile.TemporaryDirectory(prefix="clm-image-") as scratch:
        archive = Path(scratch) / "image.tar"
        saved = gate.run(
            Command(
                ("docker", "save", image["local_image_id"]),
                Effect.LOCAL_WRITE,
                f"save the qualified {name} image",
                stdout_file=str(archive),
                timeout=1800,
            )
        )
        if saved.skipped:
            return reference
        if saved.returncode != 0:
            raise StopCondition("IMAGE_SAVE_FAILED", f"could not save the {name} image")
        with archive.open("rb") as stream:
            config_digest, _ = images.archive_identity(stream)
        if image["config_digest"] is not None and config_digest != image["config_digest"]:
            raise StopCondition("WRONG_DIGEST", f"{name}: saved image is not the qualified image")
        archive_hash = sha256_file(archive)
        target = shlex.quote(incoming)
        sent = host.write(
            f"umask 077 && mkdir -p {shlex.quote(host.profile.state_dir)} && cat > {target}",
            f"copy the {name} image archive to the host",
            stdin_file=str(archive),
            timeout=3600,
        )
        if sent.skipped:
            return reference
        if sent.returncode != 0:
            raise StopCondition("IMAGE_TRANSFER_FAILED", f"{name}: the archive was not copied")
    check = host.read(f"sha256sum {target} | cut -d' ' -f1", "hash the copied archive")
    if check.stdout.strip() != archive_hash:
        host.write(f"rm -f {target}", "remove the damaged archive")
        raise StopCondition("WRONG_DIGEST", f"{name}: the copied archive does not match")
    loaded = host.write(
        f"sudo -n docker load --quiet --input {target} >/dev/null && "
        f"sudo -n docker tag {shlex.quote(safe(config_digest))} {shlex.quote(safe(reference))}; "
        f"rc=$?; rm -f {target}; exit $rc",
        f"load the {name} image on the host",
    )
    if loaded.returncode != 0:
        raise StopCondition("IMAGE_LOAD_FAILED", f"{name}: the host could not load the image")
    manifest["images"][name]["config_digest"] = config_digest
    verify_host_image(host, manifest, name, reference)
    return reference


def verify_host_image(host: Host, manifest: Manifest, name: str, reference: str) -> str:
    """The image the host holds under ``reference`` must be the approved one."""

    image = manifest["images"][name]
    identity = host.image_id(reference)
    accepted = {image["config_digest"], image["registry_manifest_digest"]} - {None}
    if identity is None:
        raise StopCondition("IMAGE_PULL_FAILED", f"{name}: the image is not on the host")
    if identity not in accepted:
        raise StopCondition("WRONG_DIGEST", f"{name}: the host image is not the approved digest")
    return identity
