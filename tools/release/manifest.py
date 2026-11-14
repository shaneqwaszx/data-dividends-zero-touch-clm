"""The release manifest: structural validation, release rules and the hash approvals bind to."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import catalog
from .core import ReleaseError, StopCondition, canonical_hash, read_json

SCHEMA_DIR = Path(__file__).resolve().parent / "schema"
MANIFEST_SCHEMA = SCHEMA_DIR / "release-manifest.schema.json"
APPROVAL_SCHEMA = SCHEMA_DIR / "approval-record.schema.json"

Manifest = dict[str, Any]

_TYPES: dict[str, tuple[type, ...]] = {
    "object": (dict,),
    "array": (list,),
    "string": (str,),
    "integer": (int,),
    "boolean": (bool,),
    "null": (type(None),),
}


def _is_type(value: Any, name: str) -> bool:
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    return isinstance(value, _TYPES[name])


def schema_errors(value: Any, schema: Mapping[str, Any], root: Mapping[str, Any]) -> list[str]:
    """Validate against the subset of JSON Schema 2020-12 the two release schemas use.

    Dependency-free on purpose: the release path must not need a package install. The tests
    cross-check this validator against the ``jsonschema`` package when it is installed.
    """

    return _validate(value, schema, root, "$")


def _validate(value: Any, schema: Mapping[str, Any], root: Mapping[str, Any], at: str) -> list[str]:
    if "$ref" in schema:
        target: Any = root
        for part in schema["$ref"].removeprefix("#/").split("/"):
            target = target[part]
        return _validate(value, target, root, at)
    errors: list[str] = []
    if "anyOf" in schema:
        if not any(not _validate(value, option, root, at) for option in schema["anyOf"]):
            errors.append(f"{at}: matches none of the allowed forms")
        return errors
    if "const" in schema and (value != schema["const"] or type(value) is not type(schema["const"])):
        errors.append(f"{at}: must be {schema['const']!r}")
    if "enum" in schema and not any(
        value == option and type(value) is type(option) for option in schema["enum"]
    ):
        errors.append(f"{at}: not one of the allowed values")
    if "type" in schema:
        names = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_is_type(value, name) for name in names):
            return [*errors, f"{at}: wrong type, expected {'/'.join(names)}"]
    if isinstance(value, str) and "pattern" in schema and not re.search(schema["pattern"], value):
        errors.append(f"{at}: does not match the required pattern")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{at}: too few items")
        if schema.get("uniqueItems") and len({repr(v) for v in value}) != len(value):
            errors.append(f"{at}: items are not unique")
        if "items" in schema:
            for index, item in enumerate(value):
                errors += _validate(item, schema["items"], root, f"{at}[{index}]")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        patterns = schema.get("patternProperties", {})
        for name in schema.get("required", []):
            if name not in value:
                errors.append(f"{at}: missing {name}")
        for key, item in value.items():
            if key in properties:
                errors += _validate(item, properties[key], root, f"{at}.{key}")
                continue
            matched = [sub for pattern, sub in patterns.items() if re.search(pattern, key)]
            if matched:
                for sub in matched:
                    errors += _validate(item, sub, root, f"{at}.{key}")
                continue
            extra = schema.get("additionalProperties", True)
            if extra is False:
                errors.append(f"{at}: unexpected field {key}")
            elif isinstance(extra, dict):
                errors += _validate(item, extra, root, f"{at}.{key}")
    return errors


def manifest_hash(manifest: Manifest) -> str:
    return canonical_hash(manifest)


def load_manifest(path: Path) -> Manifest:
    manifest = read_json(path)
    validate_manifest(manifest)
    return manifest  # type: ignore[no-any-return]


def minimum_risk(manifest: Manifest) -> tuple[str, list[str]]:
    """The lowest class this content may be given, with the reason for each raise."""

    risk = catalog.LOW
    reasons: list[str] = []

    def raise_to(level: str, why: str) -> None:
        nonlocal risk
        if catalog.RISK_ORDER[level] > catalog.RISK_ORDER[risk]:
            risk = level
        if level != catalog.LOW:
            reasons.append(f"{level}: {why}")

    for name in manifest["services_changed"]:
        raise_to(catalog.service(name).base_risk, f"service {name}")
    active = manifest["overlay"]["active_host_overlays"]
    if "assistant" in manifest["services_changed"] and "assistant-provider" in active:
        raise_to(catalog.HIGH, "assistant with the hosted provider overlay (paid inference)")
    for name, delta in manifest["declared_config_changes"].items():
        if delta.get("networks"):
            raise_to(catalog.HIGH, f"{name} gains a network")
        if delta.get("ports"):
            raise_to(catalog.HIGH, f"{name} gains a published port")
        if delta.get("settings"):
            raise_to(catalog.HIGH, f"{name} changes a container setting")
        if delta.get("environment"):
            sensitive = [
                v
                for v in delta["environment"]
                if re.search(r"KEY|TOKEN|SECRET|PROVIDER|EGRESS|GOLDTIER|ACRA|ANTHROPIC|WRITES", v)
            ]
            raise_to(
                catalog.HIGH if sensitive else catalog.MEDIUM,
                f"{name} gains environment variables",
            )
    high_classes = {"PERSISTENCE", "EXTERNAL_PROVIDER", "AUTH_RBAC_SECURITY"}
    for change_class in manifest["change_classes"]:
        if change_class in high_classes:
            raise_to(catalog.HIGH, f"change class {change_class}")
    return risk, reasons


def validate_manifest(manifest: Any) -> None:
    """Structure first, then the release rules. Any failure refuses the manifest."""

    schema = read_json(MANIFEST_SCHEMA)
    errors = schema_errors(manifest, schema, schema)
    if errors:
        raise ReleaseError("MANIFEST_INVALID", "; ".join(errors[:8]))
    changed: list[str] = manifest["services_changed"]
    unchanged: list[str] = manifest["services_unchanged"]
    if set(changed) & set(unchanged):
        raise ReleaseError("MANIFEST_INVALID", "a service is listed as both changed and unchanged")
    active = tuple(manifest["overlay"]["active_host_overlays"])
    order = tuple(manifest["overlay"]["order"])
    if catalog.resolve_overlay_files(order) != manifest["overlay"]["validation_set"]:
        raise StopCondition("OVERLAY_SET_UNSUPPORTED", "validation set does not match its files")
    listed = {entry["path"] for entry in manifest["compose_files"]}
    if listed != set(order):
        raise ReleaseError("MANIFEST_INVALID", "compose_files must hash exactly the overlay order")
    for name in changed:
        svc = catalog.service(name)
        catalog.wrapper_set_for(name, active)  # refuses an overlay the host does not have
        if svc.image_variable is None:
            raise StopCondition("SERVICE_NOT_RELEASABLE", f"{name} is never changed by a release")
        key = "goldtier-egress" if name.startswith("goldtier") else name
        if key not in manifest["images"]:
            raise ReleaseError("MANIFEST_INVALID", f"no image recorded for {name}")
        if key not in manifest["rollback"]:
            raise ReleaseError("MANIFEST_INVALID", f"no rollback entry for {name}")
        if manifest["images"][key]["repository"] != svc.repository:
            raise ReleaseError(
                "MANIFEST_INVALID", f"{name} image repository is not the approved one"
            )
        if manifest["images"][key]["file_equality"]["status"] == "FAIL":
            raise StopCondition("IMAGE_CONTENT_MISMATCH", f"{name} image differs from the commit")
    floor, _ = minimum_risk(manifest)
    if catalog.RISK_ORDER[manifest["risk_class"]] < catalog.RISK_ORDER[floor]:
        raise StopCondition(
            "RISK_CLASS_TOO_LOW", f"declared {manifest['risk_class']} but the content is {floor}"
        )
    for link in manifest["coupling"]:
        if link["service"] not in changed:
            raise ReleaseError("MANIFEST_INVALID", "coupling names a service that does not change")
        if link["satisfied_by"] == "this-release" and link["requires"] not in changed:
            raise StopCondition(
                "COUPLED_SERVICE_MISSING",
                f"{link['service']} needs the {link['requires']} from this release",
            )
        if link["satisfied_by"] == "already-deployed" and not link.get("deployed_image"):
            raise ReleaseError("MANIFEST_INVALID", "already-deployed coupling needs deployed_image")
    for name, entry in manifest["rollback"].items():
        _validate_rollback(name, entry, manifest["images"].get(name))


def _validate_rollback(
    name: str, entry: Mapping[str, Any], image: Mapping[str, Any] | None
) -> None:
    compatible = entry["data_compatible"]
    if entry["automatic"] and compatible is not True:
        raise StopCondition(
            "ROLLBACK_NOT_PROVEN", f"{name}: automatic rollback needs proven data compatibility"
        )
    target = entry.get("target_image")
    if target is not None and "@sha256:" not in target:
        raise StopCondition("FLOATING_REFERENCE", f"{name}: rollback target must be a digest")
    if name != "backend":
        return
    commit = entry.get("target_source_commit") or ""
    target_schema = entry.get("target_snapshot_schema_writes")
    new_schema = (image or {}).get("snapshot_schema_writes")
    schema_19 = any(commit.startswith(prefix) for prefix in catalog.SCHEMA_19_BACKEND_COMMITS)
    older = target_schema is not None and new_schema is not None and target_schema < new_schema
    if (schema_19 or older) and compatible is not False:
        raise StopCondition(
            "ROLLBACK_SCHEMA_INCOMPATIBLE",
            "backend: the rollback target writes an older case-snapshot schema; "
            "data_compatible must be false",
        )
    if compatible is True and (target_schema is None or new_schema is None):
        raise StopCondition(
            "ROLLBACK_NOT_PROVEN", "backend: compatibility claimed without both schema versions"
        )
    if entry["automatic"] and not entry.get("target_confirmed_on_host", False):
        raise StopCondition(
            "ROLLBACK_NOT_PROVEN",
            "backend: automatic rollback needs the target confirmed on the host",
        )


def rollback_eligibility(manifest: Manifest, name: str) -> tuple[bool, str]:
    """Whether the applier may roll ``name`` back by itself, and why."""

    entry = manifest["rollback"].get(name)
    if entry is None:
        return False, "no rollback entry"
    if entry["data_compatible"] is not True:
        return False, f"data compatibility is {entry['data_compatible']!r}: owner decision needed"
    if not entry["automatic"]:
        return False, "the manifest does not allow automatic rollback"
    if entry.get("target_image") is None:
        return False, "the rollback image is not recorded"
    return True, entry["basis"]


def require_publishable(manifest: Manifest, services: list[str]) -> None:
    """Refuse publication unless the exact images were reviewed and match the commit."""

    verdicts = [gate["verdict"] for gate in manifest["quality_gates"]]
    if not verdicts or any(v in {"FAIL", "NOT RUN"} for v in verdicts):
        raise StopCondition("QG_NOT_PASSED", "a required quality gate has not passed")
    if any(check["status"] == "FAIL" for check in manifest["checks"]):
        raise StopCondition("CHECK_FAILED", "a recorded check failed")
    for name in services:
        image = manifest["images"][name]
        if image["file_equality"]["status"] != "PASS":
            raise StopCondition("IMAGE_NOT_VERIFIED", f"{name}: in-image file equality not proven")
        if image["config_digest"] is None:
            raise StopCondition("IMAGE_NOT_VERIFIED", f"{name}: config digest not recorded")


def require_deployable(manifest: Manifest, *, transfer: str) -> None:
    """Refuse deployment when an image identity is still unknown."""

    require_publishable(manifest, list(manifest["images"]))
    for name in manifest["services_changed"]:
        key = "goldtier-egress" if name.startswith("goldtier") else name
        image = manifest["images"][key]
        if transfer == "pull" and image["registry_manifest_digest"] is None:
            raise StopCondition(
                "REGISTRY_DIGEST_UNKNOWN", f"{name}: publish first; the registry digest is unknown"
            )


def image_reference(manifest: Manifest, name: str, *, transfer: str) -> str:
    """The exact, non-floating reference compose.env will hold for ``name``."""

    image = manifest["images"][name]
    if transfer == "pull":
        digest = image["registry_manifest_digest"]
        if digest is None:
            raise StopCondition("REGISTRY_DIGEST_UNKNOWN", f"{name}: registry digest unknown")
        return f"{image['repository']}@{digest}"
    return f"{image['repository']}:{release_tag(manifest, name)}"


def release_tag(manifest: Manifest, name: str) -> str:
    """``rc-<commit12>-<config12>``, the tag convention of the earlier manual releases."""

    image = manifest["images"][name]
    config = image["config_digest"] or image["local_image_id"]
    return f"rc-{manifest['source']['commit'][:12]}-{config.removeprefix('sha256:')[:12]}"
