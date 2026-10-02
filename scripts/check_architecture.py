"""Run narrow, explainable architecture guards against tracked application source."""

from __future__ import annotations

import argparse
import ast
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Finding:
    rule: str
    path: str
    message: str


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _tracked(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
    )
    if result.returncode != 0:
        raise RuntimeError("git ls-files failed")
    normalized = (path.replace("\\", "/") for path in result.stdout.splitlines())
    return sorted(path for path in normalized if (root / path).is_file())


def _imports(text: str) -> set[str]:
    tree = ast.parse(text)
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
            found.update(f"{node.module}.{alias.name}" for alias in node.names)
    return found


def _is_scalar_ownership_evidence_model(text: str) -> bool:
    """Recognize the documented model carrier, never another ownership engine."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False
    classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    if not classes or any(
        len(node.bases) != 1
        or not isinstance(node.bases[0], ast.Name)
        or node.bases[0].id not in {"BaseModel", "StrEnum"}
        for node in classes
    ):
        return False
    model_methods = {
        id(member)
        for model in classes
        for member in model.body
        if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    return all(
        id(node) in model_methods
        and any(
            isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Name)
            and decorator.func.id in {"field_validator", "model_validator"}
            for decorator in node.decorator_list
        )
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )


def _instantiates_imported_symbol(text: str, qualified_name: str) -> bool:
    tree = ast.parse(text)
    bindings: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                bindings[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and bindings.get(node.func.id) == qualified_name
        for node in ast.walk(tree)
    )


def _literal_setting(text: str, name: str) -> tuple[set[str], object] | None:
    tree = ast.parse(text)
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != "Settings":
            continue
        for item in node.body:
            if (
                not isinstance(item, ast.AnnAssign)
                or not isinstance(item.target, ast.Name)
                or item.target.id != name
                or not isinstance(item.annotation, ast.Subscript)
                or not isinstance(item.annotation.value, ast.Name)
                or item.annotation.value.id != "Literal"
            ):
                continue
            values = (
                item.annotation.slice.elts
                if isinstance(item.annotation.slice, ast.Tuple)
                else [item.annotation.slice]
            )
            allowed = {
                value.value
                for value in values
                if isinstance(value, ast.Constant) and isinstance(value.value, str)
            }
            default = item.value.value if isinstance(item.value, ast.Constant) else None
            return allowed, default
    return None


def _without_javascript_comments(text: str) -> str:
    output: list[str] = []
    index = 0
    quote: str | None = None
    while index < len(text):
        char = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""
        if quote is not None:
            output.append(char)
            if char == "\\" and following:
                output.append(following)
                index += 2
                continue
            if char == quote:
                quote = None
            index += 1
            continue
        if char in {'"', "'", "`"}:
            quote = char
            output.append(char)
            index += 1
            continue
        if char == "/" and following == "/":
            while index < len(text) and text[index] != "\n":
                output.append(" ")
                index += 1
            continue
        if char == "/" and following == "*":
            output.extend((" ", " "))
            index += 2
            while index < len(text):
                if (
                    text[index] == "*"
                    and index + 1 < len(text)
                    and text[index + 1] == "/"
                ):
                    output.extend((" ", " "))
                    index += 2
                    break
                output.append("\n" if text[index] == "\n" else " ")
                index += 1
            continue
        output.append(char)
        index += 1
    return "".join(output)


FRONTEND_IMPORT = re.compile(
    r"^\s*import\b(?:\s+type)?(?:\s+.*?\s+from\s+|\s*)[\"'](?P<module>[^\"']+)[\"']",
    re.MULTILINE | re.DOTALL,
)


def _frontend_dependencies(text: str) -> set[str]:
    without_comments = _without_javascript_comments(text)
    return {
        match.group("module") for match in FRONTEND_IMPORT.finditer(without_comments)
    }


def _is_prohibited_frontend_dependency(module: str) -> bool:
    normalized = module.replace("\\", "/").lower()
    return (
        normalized in {"app.persistence", "pymongo"}
        or normalized.startswith(("app.persistence/", "pymongo/"))
        or "/backend/app/persistence" in normalized
    )


def _is_prohibited_api_import(name: str) -> bool:
    concrete_persistence = (
        "app.persistence.composition",
        "app.persistence.models",
        "app.persistence.mongo",
        "app.persistence.repositories",
    )
    return (
        name in {"app.mongo", "pymongo"}
        or name.startswith(("app.mongo.", "app.persistence.mongo_", "pymongo."))
        or any(
            name == prefix or name.startswith(f"{prefix}.")
            for prefix in concrete_persistence
        )
    )


def check(root: Path) -> list[Finding]:
    tracked = _tracked(root)
    findings: list[Finding] = []
    api_paths = [
        path
        for path in tracked
        if path.startswith("apps/backend/app/api") and path.endswith(".py")
    ]
    for path in api_paths:
        try:
            imports = _imports(_read_text(root / path))
        except (OSError, SyntaxError):
            findings.append(
                Finding("API_PERSISTENCE_BOUNDARY", path, "cannot inspect imports")
            )
            continue
        bad = sorted(name for name in imports if _is_prohibited_api_import(name))
        if bad:
            findings.append(
                Finding(
                    "API_PERSISTENCE_BOUNDARY",
                    path,
                    "direct concrete persistence import: " + ", ".join(bad),
                )
            )

    for path in tracked:
        if not path.startswith("apps/frontend/") or not path.endswith(
            (".ts", ".tsx", ".js", ".jsx")
        ):
            continue
        dependencies = _frontend_dependencies(_read_text(root / path))
        bad_dependencies = sorted(
            item for item in dependencies if _is_prohibited_frontend_dependency(item)
        )
        if bad_dependencies:
            findings.append(
                Finding(
                    "FRONTEND_BACKEND_BOUNDARY",
                    path,
                    "frontend imports backend persistence: "
                    + ", ".join(bad_dependencies),
                )
            )

    owner = "apps/backend/app/domain/ownership.py"
    if owner not in tracked:
        findings.append(
            Finding(
                "OWNERSHIP_CANONICAL_OWNER",
                owner,
                "canonical ownership owner is missing",
            )
        )
    for path in tracked:
        if (
            path.startswith("apps/backend/app/domain/")
            and path.endswith(".py")
            and "ownership" in Path(path).stem
            and path != owner
            and not (
                path == "apps/backend/app/domain/ownership_evidence.py"
                and _is_scalar_ownership_evidence_model(_read_text(root / path))
            )
        ):
            findings.append(
                Finding(
                    "OWNERSHIP_CANONICAL_OWNER",
                    path,
                    "second domain ownership implementation",
                )
            )

    composition_path = "apps/backend/app/composition.py"
    config_path = "apps/backend/app/config.py"
    if composition_path in tracked:
        composition = _read_text(root / composition_path)
        try:
            composition_imports = _imports(composition)
        except SyntaxError:
            findings.append(
                Finding(
                    "RUNTIME_COMPOSITION", composition_path, "cannot inspect imports"
                )
            )
            composition_imports = set()
        if any(
            "acra_bizfile_sandbox" in name.lower() or "acrabizfile" in name.lower()
            for name in composition_imports
        ):
            findings.append(
                Finding(
                    "DORMANT_BIZFILE",
                    composition_path,
                    "dormant BizFile entered runtime composition",
                )
            )
        mock_composed = any(
            name.endswith(".MockGoldTierConnector") for name in composition_imports
        ) and _instantiates_imported_symbol(
            composition, "app.connectors.mock_goldtier.MockGoldTierConnector"
        )
        sandbox_composed = any(
            name.endswith(".GoldTierXpiSandboxConnector")
            for name in composition_imports
        ) and _instantiates_imported_symbol(
            composition, "app.connectors.goldtier_xpi.GoldTierXpiSandboxConnector"
        )
        if not mock_composed or not sandbox_composed:
            findings.append(
                Finding(
                    "GOLDTIER_MODE_BOUNDARY",
                    composition_path,
                    "Mock-default and explicit XPI sandbox composition markers are required",
                )
            )
    if config_path in tracked:
        config = _read_text(root / config_path)
        try:
            goldtier_setting = _literal_setting(config, "goldtier_connector_mode")
        except SyntaxError:
            goldtier_setting = None
        if goldtier_setting != ({"mock", "sandbox"}, "mock"):
            findings.append(
                Finding(
                    "GOLDTIER_MODE_BOUNDARY",
                    config_path,
                    "GoldTier modes must be exactly mock/sandbox with Mock default",
                )
            )
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    try:
        findings = check(args.root.resolve())
    except (OSError, RuntimeError) as error:
        print(f"ARCHITECTURE CHECK ERROR: {type(error).__name__}")
        return 2
    if findings:
        for finding in findings:
            print(f"FAIL [{finding.rule}] {finding.path}: {finding.message}")
        print("ARCHITECTURE CHECK: FAIL")
        return 1
    print("ARCHITECTURE CHECK: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
