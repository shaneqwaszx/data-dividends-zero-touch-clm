"""Vocabulary consistency check for the AI Assistant's generated vocabularies.

The assistant ships generated vocabulary files, each built from repository sources by its own
generator (``build() -> str``):

- ``ai_assistant/synthetic_boundary.json`` (D-094), from the backend and assistant sources
- ``ai_assistant/privacy_vocabulary.json`` (D-142, when present), from the stored D-094 file and
  the sources

A change that adds or removes source strings makes a stored file stale. A change that edits a
file widens or narrows what the assistant may send, and needs an independent vocabulary review.

For each artifact present, this check compares the drift (generated minus stored) on the
candidate with the drift on the base. The overall outcome is the worst artifact outcome. It is
read-only: it never writes a vocabulary file and never opens a runtime store.

Outcomes, printed as one JSON object on stdout:

- ``CURRENT``: the stored file equals the generated file.
- ``REVIEW_REQUIRED``: the candidate changes the stored file and leaves it current. The word
  delta must be independently reviewed against the D-094 rules.
- ``PRE_EXISTING_DRIFT``: the stored file is stale, but by exactly the drift already on the base.
  The candidate adds none. It is reconciled separately (VR-1).
- ``FAIL_NEW_DRIFT``: the candidate changes the generated vocabulary without updating the file.
- ``FAIL_CHANGED_NOT_CURRENT``: the candidate edits the file but leaves it stale.
- ``FAIL_UNVERIFIABLE``: a build failed, or a stored vocabulary has no generator, so consistency
  cannot be shown (fail closed).
- ``FAIL_GENERATOR_REMOVED``: a generator present on the base is missing from the candidate (a
  rename or deletion must not turn the check off).

Exit code 0 for ``CURRENT``, ``REVIEW_REQUIRED`` and ``PRE_EXISTING_DRIFT``; 1 for any failure.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

BOUNDARY_FILE = "apps/assistant/ai_assistant/synthetic_boundary.json"
GENERATOR = "apps/assistant/scripts/build_synthetic_boundary.py"
# (stored file, generator), checked in this order. An artifact whose generator is absent from
# the candidate is skipped; the D-094 boundary generator must exist for the check to apply.
ARTIFACTS = (
    (BOUNDARY_FILE, GENERATOR),
    (
        "apps/assistant/ai_assistant/privacy_vocabulary.json",
        "apps/assistant/scripts/build_privacy_vocabulary.py",
    ),
)
# Worst first: the overall outcome is the first status here that any artifact has.
SEVERITY = (
    "FAIL_GENERATOR_REMOVED",
    "FAIL_UNVERIFIABLE",
    "FAIL_CHANGED_NOT_CURRENT",
    "FAIL_NEW_DRIFT",
    "REVIEW_REQUIRED",
    "PRE_EXISTING_DRIFT",
    "CURRENT",
)
# Paths the generator reads. The base is exported from these only, so nothing else is unpacked.
GENERATOR_INPUTS = (
    "apps/assistant",
    "apps/backend/app",
    "apps/backend/tests/fixtures/uat",
    "scripts/generate_garden_demo_pdfs.py",
)
BUILD_TIMEOUT_SECONDS = 300

_BUILD_SNIPPET = (
    "import importlib.util, sys\n"
    "spec = importlib.util.spec_from_file_location('boundary_builder', sys.argv[1])\n"
    "module = importlib.util.module_from_spec(spec)\n"
    "spec.loader.exec_module(module)\n"
    "sys.stdout.write(module.build())\n"
)

Drift = dict[str, Any]


def drift(stored: Mapping[str, Any], generated: Mapping[str, Any]) -> Drift:
    """Per key: words the generator adds and removes, or ``"changed"`` for other values."""

    result: Drift = {}
    for key in sorted(set(stored) | set(generated)):
        old, new = stored.get(key), generated.get(key)
        if old == new:
            continue
        # A word list on one side only (a new or removed file or key) counts against empty.
        if old is None and _is_word_list(new):
            old = []
        if new is None and _is_word_list(old):
            new = []
        if _is_word_list(old) and _is_word_list(new):
            result[key] = {
                "added": sorted(set(new) - set(old)),
                "removed": sorted(set(old) - set(new)),
            }
        else:
            # A fingerprint of the generated value, so a further change to an already stale
            # non-list key (for example ``knowledge``) is new drift, never hidden by the base.
            encoded = json.dumps(new, sort_keys=True, ensure_ascii=False).encode("utf-8")
            result[key] = {"changed_to": hashlib.sha256(encoded).hexdigest()[:16]}
    return result


def classify(
    *,
    head_drift: Drift | None,
    base_drift: Drift | None,
    boundary_changed: bool,
) -> str:
    """Pure decision. ``None`` drift means the build could not run."""

    if head_drift is None:
        return "FAIL_UNVERIFIABLE"
    if not head_drift:
        return "REVIEW_REQUIRED" if boundary_changed else "CURRENT"
    if boundary_changed:
        return "FAIL_CHANGED_NOT_CURRENT"
    if base_drift is None:
        return "FAIL_UNVERIFIABLE"
    return "PRE_EXISTING_DRIFT" if head_drift == base_drift else "FAIL_NEW_DRIFT"


def _is_word_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _git(root: Path, *args: str, binary: bool = False) -> subprocess.CompletedProcess:
    environment = os.environ.copy()
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=not binary,
        encoding=None if binary else "utf-8",
        env=environment,
        shell=False,
    )


def _build(tree: Path, generator_path: str = GENERATOR) -> dict[str, Any] | None:
    """Run the tree's own generator in a subprocess; ``None`` if it cannot build."""

    generator = tree / generator_path
    if not generator.is_file():
        return None
    assistant = tree / "apps" / "assistant"
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(assistant)
    # The vocabularies hold non-ASCII text; never let a console code page encode the output.
    environment["PYTHONIOENCODING"] = "utf-8"
    environment["PYTHONUTF8"] = "1"
    try:
        result = subprocess.run(
            [sys.executable, "-c", _BUILD_SNIPPET, str(generator)],
            cwd=assistant,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=environment,
            timeout=BUILD_TIMEOUT_SECONDS,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        return None
    if result.returncode != 0:
        return None
    try:
        loaded = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else None


def _stored(tree: Path, stored_path: str = BOUNDARY_FILE) -> dict[str, Any] | None:
    try:
        loaded = json.loads((tree / stored_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, dict) else None


def _stored_at(
    root: Path, ref: str, stored_path: str = BOUNDARY_FILE
) -> dict[str, Any] | None:
    shown = _git(root, "show", f"{ref}:{stored_path}")
    if shown.returncode != 0:
        return None
    try:
        loaded = json.loads(shown.stdout)
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else None


def _tree_drift(
    tree: Path, stored_path: str = BOUNDARY_FILE, generator_path: str = GENERATOR
) -> Drift | None:
    stored, generated = _stored(tree, stored_path), _build(tree, generator_path)
    if stored is None or generated is None:
        return None
    return drift(stored, generated)


def _base_drift(
    root: Path, base: str, stored_path: str = BOUNDARY_FILE, generator_path: str = GENERATOR
) -> Drift | None:
    if _git(root, "cat-file", "-e", f"{base}:{generator_path}").returncode != 0:
        return None
    present = [
        path for path in GENERATOR_INPUTS
        if _git(root, "cat-file", "-e", f"{base}:{path}").returncode == 0
    ]
    archive = _git(root, "archive", "--format=tar", base, "--", *present, binary=True)
    if archive.returncode != 0:
        return None
    with tempfile.TemporaryDirectory(prefix="boundary-base-") as scratch:
        with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as bundle:
            bundle.extractall(scratch, filter="data")
        return _tree_drift(Path(scratch), stored_path, generator_path)


def _boundary_changed(root: Path, base: str, stored_path: str = BOUNDARY_FILE) -> bool:
    committed = _git(root, "diff", "--name-only", f"{base}...HEAD", "--", stored_path)
    working = _git(root, "status", "--porcelain", "--", stored_path)
    return bool(committed.stdout.strip()) or bool(working.stdout.strip())


def _summary(value: Drift | None) -> dict[str, dict[str, int]] | None:
    if value is None:
        return None
    return {
        key: (
            {"added": len(change["added"]), "removed": len(change["removed"])}
            if "added" in change
            else {"added": 0, "removed": 0, "other": 1}
        )
        for key, change in value.items()
    }


def word_delta(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, dict[str, int]]:
    """Counts of words added and removed between two stored files, for the review summary."""

    return _summary(drift(before, after)) or {}


def _evaluate_artifact(
    root: Path, base: str, stored_path: str, generator_path: str
) -> dict[str, Any]:
    head_drift = _tree_drift(root, stored_path, generator_path)
    changed = _boundary_changed(root, base, stored_path)
    base_drift = (
        _base_drift(root, base, stored_path, generator_path)
        if head_drift and not changed
        else None
    )
    status = classify(head_drift=head_drift, base_drift=base_drift, boundary_changed=changed)
    report: dict[str, Any] = {
        "status": status,
        "changed": changed,
        "head_drift": _summary(head_drift),
        "base_drift": _summary(base_drift),
    }
    if changed:
        before, after = _stored_at(root, base, stored_path), _stored(root, stored_path)
        if after is not None:
            report["file_word_delta"] = word_delta(before or {}, after)
    return report


def _missing_generator(root: Path, base: str, stored_path: str, generator_path: str) -> str | None:
    """Outcome for an artifact whose generator is absent from the candidate, or None to skip.

    A generator that exists on the base and is gone from the candidate is never a pass: a rename
    or deletion would otherwise let an unreviewed vocabulary through. A stored vocabulary with no
    generator cannot be verified either.
    """

    if _git(root, "cat-file", "-e", f"{base}:{generator_path}").returncode == 0:
        return "FAIL_GENERATOR_REMOVED"
    if (root / stored_path).exists():
        return "FAIL_UNVERIFIABLE"
    return None


def evaluate(root: Path, base: str) -> dict[str, Any]:
    artifacts: dict[str, dict[str, Any]] = {}
    for stored_path, generator_path in ARTIFACTS:
        if (root / generator_path).is_file():
            artifacts[stored_path] = _evaluate_artifact(root, base, stored_path, generator_path)
            continue
        missing = _missing_generator(root, base, stored_path, generator_path)
        if missing is not None:
            artifacts[stored_path] = {"status": missing, "generator": generator_path}
    if not artifacts:
        # Neither generator exists here nor on the base: history before the D-094 boundary.
        return {"status": "CURRENT", "base": base, "artifacts": {},
                "message": "No assistant vocabulary generator here or on the base."}
    statuses = {item["status"] for item in artifacts.values()}
    status = next(name for name in SEVERITY if name in statuses)
    primary = artifacts.get(BOUNDARY_FILE, {})
    report: dict[str, Any] = {
        "status": status,
        "base": base,
        "artifacts": artifacts,
        # The D-094 boundary's own fields, kept at the top level for one-line summaries.
        "boundary_changed": primary.get("changed", False),
        "head_drift": primary.get("head_drift"),
        "base_drift": primary.get("base_drift"),
    }
    if "file_word_delta" in primary:
        report["file_word_delta"] = primary["file_word_delta"]
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--base", default="origin/main")
    args = parser.parse_args(argv)
    report = evaluate(args.root.resolve(), args.base)
    sys.stdout.write(json.dumps(report, sort_keys=True) + "\n")
    return 1 if report["status"].startswith("FAIL") else 0


if __name__ == "__main__":
    raise SystemExit(main())
