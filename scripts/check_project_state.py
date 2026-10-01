"""Conservatively validate structured project-state facts against current source."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_BLOCK = re.compile(r"```json project-state\s*\n(?P<body>.*?)\n```", re.DOTALL)
SHA = re.compile(r"^[0-9a-f]{40}$")
REQUIRED_SECTIONS = {
    "# Current Project State",
    "## Verification metadata",
    "## Current status",
    "## Current runtime pipeline",
    "## Current External Integration Truth",
    "## Persistence modes",
    "## Authentication, authorization and administration",
    "## Major current capabilities",
    "## Current explicit non-capabilities",
    "## Current open sponsor blockers",
    "## Current architectural debt",
    "## Next candidate work packages",
}
PROJECT_STATE_SCHEMA_VERSION = 1
EXPECTED_PROVIDERS = {
    "registry": {"name": "ACRA", "mode": "mock", "classification": "MOCK"},
    "registry_api_marketplace_mock": {
        "name": "ACRA_API_MARKETPLACE_MOCK",
        "mode": "api_marketplace_mock",
        "classification": "MOCK",
    },
    "registry_sandbox": {
        "name": "ACRA_GENERIC_SANDBOX",
        "mode": "sandbox",
        "classification": "PARTIAL",
    },
    "registry_bizfile": {
        "name": "ACRA_BIZFILE",
        "mode": "dormant",
        "classification": "DORMANT",
    },
    "idp": {
        "name": "LOCAL_PDF_TEXT",
        "mode": "local_pdf_text",
        "classification": "LOCAL",
    },
    "idp_fault": {"name": "MOCK_IDP", "mode": "mock", "classification": "MOCK"},
    "ownership": {
        "name": "DECIMAL_GRAPH_ENGINE",
        "mode": "local",
        "classification": "LOCAL",
    },
    "target": {"name": "GOLDTIER", "mode": "mock", "classification": "MOCK"},
    "target_sandbox": {
        "name": "GOLDTIER_XPI",
        "mode": "sandbox",
        "classification": "PARTIAL",
    },
}
EXPECTED_IDENTITY = {
    "account_source": "bootstrap_repositories",
    "session_store": "process_local",
    "production_sso": "not_implemented",
}


def _is_camunda_runtime_path(path: str) -> bool:
    # Backend test-tree contracts are governance evidence, not application runtime.
    return (
        path.startswith("apps/")
        and not path.startswith("apps/backend/tests/")
        and "camunda" in path.lower()
    )


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
    )


def _literal_modes(config_text: str) -> dict[str, tuple[set[str], object]]:
    tree = ast.parse(config_text)
    modes: dict[str, tuple[set[str], object]] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != "Settings":
            continue
        for item in node.body:
            if not isinstance(item, ast.AnnAssign) or not isinstance(
                item.target, ast.Name
            ):
                continue
            annotation = item.annotation
            if not isinstance(annotation, ast.Subscript) or not (
                isinstance(annotation.value, ast.Name)
                and annotation.value.id == "Literal"
            ):
                continue
            values = (
                annotation.slice.elts
                if isinstance(annotation.slice, ast.Tuple)
                else [annotation.slice]
            )
            allowed = {
                value.value
                for value in values
                if isinstance(value, ast.Constant) and isinstance(value.value, str)
            }
            default = item.value.value if isinstance(item.value, ast.Constant) else None
            modes[item.target.id] = (allowed, default)
    return modes


def _integer_constant(source: str, name: str) -> int | None:
    tree = ast.parse(source)
    for node in tree.body:
        target: ast.expr | None = None
        value: ast.expr | None = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign):
            target, value = node.target, node.value
        if (
            isinstance(target, ast.Name)
            and target.id == name
            and isinstance(value, ast.Constant)
            and type(value.value) is int
        ):
            return value.value
    return None


def _has_process_local_sessions(source: str) -> bool:
    tree = ast.parse(source)
    return any(
        isinstance(node, (ast.Assign, ast.AnnAssign))
        and any(
            isinstance(target, ast.Attribute) and target.attr == "_sessions"
            for target in (
                node.targets if isinstance(node, ast.Assign) else [node.target]
            )
        )
        and isinstance(node.value, ast.Dict)
        for node in ast.walk(tree)
    )


def _calls(source: str, function_name: str) -> bool:
    tree = ast.parse(source)
    return any(
        isinstance(node, ast.Call)
        and (
            isinstance(node.func, ast.Name)
            and node.func.id == function_name
            or isinstance(node.func, ast.Attribute)
            and node.func.attr == function_name
        )
        for node in ast.walk(tree)
    )


def validate(root: Path) -> list[str]:
    failures: list[str] = []
    state_path = root / "docs" / "PROJECT_STATE.md"
    try:
        text = _read_text(state_path)
    except OSError:
        return ["PROJECT_STATE.md is unavailable"]
    for section in sorted(REQUIRED_SECTIONS):
        if section not in text:
            failures.append(f"Missing required section: {section}")
    match = STATE_BLOCK.search(text)
    if match is None:
        return failures + ["Missing structured project-state metadata block"]
    try:
        state = json.loads(match.group("body"))
    except json.JSONDecodeError:
        return failures + ["Invalid project-state JSON metadata"]
    if not isinstance(state, dict):
        return failures + ["Project-state metadata is not an object"]

    if state.get("schema_version") != PROJECT_STATE_SCHEMA_VERSION:
        failures.append(
            f"schema_version must be {PROJECT_STATE_SCHEMA_VERSION} for this metadata format"
        )
    if state.get("verification_status") != "verified-against-main":
        failures.append("verification_status must be verified-against-main")

    baseline = state.get("verified_main_sha")
    baseline_exists = False
    if not isinstance(baseline, str) or SHA.fullmatch(baseline) is None:
        failures.append("verified_main_sha must be a lowercase 40-hex commit")
    else:
        exists = _git(root, "cat-file", "-e", f"{baseline}^{{commit}}")
        ancestor = _git(root, "merge-base", "--is-ancestor", baseline, "origin/main")
        baseline_exists = exists.returncode == 0
        if not baseline_exists or ancestor.returncode != 0:
            failures.append(
                "verified_main_sha must exist and be reachable from origin/main"
            )

    verified_date: date | None = None
    raw_date = state.get("verified_date")
    if (
        not isinstance(raw_date, str)
        or re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_date) is None
    ):
        failures.append("verified_date must be an ISO date in YYYY-MM-DD form")
    else:
        try:
            verified_date = date.fromisoformat(raw_date)
        except ValueError:
            failures.append("verified_date must be a valid ISO calendar date")
    if baseline_exists and verified_date is not None and isinstance(baseline, str):
        commit_date_result = _git(root, "show", "-s", "--format=%cs", baseline)
        try:
            baseline_date = date.fromisoformat(commit_date_result.stdout.strip())
        except ValueError:
            failures.append("Unable to determine verified_main_sha commit date")
        else:
            if verified_date < baseline_date - timedelta(days=1):
                failures.append("verified_date materially predates the baseline commit")

    providers = state.get("providers")
    if not isinstance(providers, dict):
        failures.append("providers metadata must be an object")
        providers = {}
    for key, expected_provider in EXPECTED_PROVIDERS.items():
        if providers.get(key) != expected_provider:
            failures.append(
                f"Provider {key} ({expected_provider['name']}) metadata does not match "
                "current mode/classification"
            )
    extra_providers = sorted(set(providers) - set(EXPECTED_PROVIDERS))
    if extra_providers:
        failures.append("Unexpected provider metadata: " + ", ".join(extra_providers))

    try:
        config_text = _read_text(root / "apps" / "backend" / "app" / "config.py")
        composition = _read_text(root / "apps" / "backend" / "app" / "composition.py")
        persistence_models = _read_text(
            root / "apps" / "backend" / "app" / "persistence" / "models.py"
        )
        persistence_composition = _read_text(
            root / "apps" / "backend" / "app" / "persistence" / "composition.py"
        )
        authentication = _read_text(
            root / "apps" / "backend" / "app" / "services" / "authentication.py"
        )
        modes = _literal_modes(config_text)
    except (OSError, SyntaxError):
        return failures + ["Unable to inspect backend config/composition"]

    source_schema_version = _integer_constant(
        persistence_models, "CASE_SNAPSHOT_SCHEMA_VERSION"
    )
    documented_schema_version = state.get("case_envelope_schema_version")
    if source_schema_version is None:
        failures.append("Unable to determine canonical case envelope schema version")
    elif documented_schema_version != source_schema_version:
        failures.append(
            "Documented case envelope schema version does not match persistence source"
        )

    expected = {
        "acra_connector_mode": providers.get("registry", {}).get("mode")
        if isinstance(providers.get("registry"), dict)
        else None,
        "goldtier_connector_mode": providers.get("target", {}).get("mode")
        if isinstance(providers.get("target"), dict)
        else None,
        "idp_connector_mode": providers.get("idp", {}).get("mode")
        if isinstance(providers.get("idp"), dict)
        else None,
    }
    for setting, documented in expected.items():
        allowed_default = modes.get(setting)
        if (
            allowed_default is None
            or documented != allowed_default[1]
            or documented not in allowed_default[0]
        ):
            failures.append(f"Documented default for {setting} does not match Settings")
    if modes.get("goldtier_connector_mode") != ({"mock", "sandbox"}, "mock"):
        failures.append(
            "GoldTier Settings must expose only explicit mock/sandbox modes with Mock default"
        )
    persistence = state.get("persistence")
    persistence_mode = modes.get("clm_persistence_mode")
    if not isinstance(persistence, dict):
        failures.append("persistence metadata must be an object")
    elif persistence_mode is None:
        failures.append("Unable to determine persistence modes from Settings")
    else:
        supported, default = persistence_mode
        if persistence.get("default") != default:
            failures.append("Documented persistence default does not match Settings")
        documented_supported = persistence.get("supported")
        if (
            not isinstance(documented_supported, list)
            or set(documented_supported) != supported
            or any(not isinstance(item, str) for item in documented_supported)
        ):
            failures.append(
                "Documented supported persistence modes do not match Settings"
            )

    identity = state.get("identity")
    if identity != EXPECTED_IDENTITY:
        failures.append("Documented identity classification does not match current POC")
    if not _calls(persistence_composition, "bootstrap_administration"):
        failures.append("Current composition no longer proves bootstrap identities")
    if not _has_process_local_sessions(authentication):
        failures.append(
            "Current authentication no longer proves process-local sessions"
        )

    if "MockGoldTierConnector" not in composition:
        failures.append("Current composition no longer proves Mock GoldTier")
    if "GoldTierXpiSandboxConnector" not in composition:
        failures.append("Current composition no longer proves explicit GoldTier XPI sandbox")
    workflow = state.get("workflow_engine", {})
    if not isinstance(workflow, dict) or workflow.get("camunda") != "not_implemented":
        failures.append(
            "Camunda must remain documented not_implemented without a runtime adapter"
        )
    tracked = _git(root, "ls-files").stdout.splitlines()
    runtime_camunda = [path for path in tracked if _is_camunda_runtime_path(path)]
    if runtime_camunda:
        failures.append(
            "Camunda runtime files exist but PROJECT_STATE says not_implemented"
        )
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    failures = validate(args.root.resolve())
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        print("PROJECT STATE CHECK: FAIL")
        return 1
    print("PROJECT STATE CHECK: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
