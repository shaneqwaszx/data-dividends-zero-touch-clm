"""Validate the sponsor-policy authority registry and activation invariants."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = Path("docs/contracts/policy_authority_registry.json")
QUESTIONS_PATH = Path("docs/sponsor-questions/OPEN_QUESTIONS.md")
AUTHORITY_STATUSES = {
    "OBSERVED",
    "PROJECT_DEFINED_PROVISIONAL",
    "SPONSOR_CONFIRMED",
    "UNKNOWN_BLOCKED",
}
ENTRY_FIELDS = {
    "policy_id",
    "authority_status",
    "source_reference",
    "blocking_sponsor_question",
    "runtime_enabled",
}
REQUIRED_POLICY_GATES = {
    "SUPPLIED_RISK_INPUT_AND_WORKFLOW": "Q-017",
    "REVIEW_AUTHORITY": "Q-014",
    "REVIEWER_SEPARATION_OF_DUTIES": "Q-014",
    "ASSIGNMENT_AND_REASSIGNMENT": "Q-016",
    "PRODUCTION_IDENTITY_AND_RBAC": "Q-016",
    "PRIORITY_VOCABULARY_AND_ORDER": "Q-016",
    "PRIORITY_WORKFLOW_EFFECT": "Q-016",
    "SOURCE_PRECEDENCE": "Q-015",
    "CONFLICT_DISPOSITION_AUTHORITY": "Q-015",
    "VALIDATION_RESPONSIBILITY_SPLIT": "Q-005",
    "READY_FOR_APPROVAL_TRANSITION": "Q-001",
    "FINAL_APPROVAL_OWNER": "Q-001",
    "DOCUMENT_SCOPE": "Q-003",
    "FINAL_LEGAL_UBO_RULE": "Q-004",
    "RETENTION_DEPENDENT_REVIEW_AND_AUDIT": "Q-013",
    "PRODUCTION_HANDOFF_OWNERSHIP": "Q-018",
}
REQUIRED_POLICY_IDS = set(REQUIRED_POLICY_GATES) | {
    "HUMAN_EXCEPTION_REVIEW_ALLOWED",
}
QUESTION_HEADING = re.compile(r"^### (Q-\d{3})\b", re.MULTILINE)
POLICY_ID = re.compile(r"^[A-Z][A-Z0-9_]*$")
QUESTION_ID = re.compile(r"^Q-\d{3}$")
GOVERNED_DOCS = (
    Path("docs/PROJECT_STATE.md"),
    Path("docs/contracts/POLICY_AUTHORITY_MATRIX.md"),
    Path("docs/contracts/POLICY_ACTIVATION_CONTRACT.md"),
    Path("docs/sponsor-questions/PHASE_20_POLICY_DECISION_PACKET.md"),
)
FORBIDDEN_CLAIMS = {
    "Mock submission presented as Ready-for-Approval or approval": re.compile(
        r"\bMOCK_GOLDTIER_SUBMITTED\s+(?:is|means|achieves|equals)\s+"
        r"(?:an?\s+)?(?:Ready-for-Approval|approval)\b",
        re.IGNORECASE,
    ),
    "Mock GoldTier presented as Live or production approval": re.compile(
        r"\bMock GoldTier\s+is\s+(?:Live|production approval)\b", re.IGNORECASE
    ),
    "P1-P10 presented as sponsor-approved": re.compile(
        r"\bP1[-–]P10\s+is\s+sponsor-approved\b", re.IGNORECASE
    ),
    "local roles presented as production policy": re.compile(
        r"\bcurrent local roles\s+are\s+(?:the\s+)?production (?:policy|RBAC)\b",
        re.IGNORECASE,
    ),
    "current review presented as sponsor-approved": re.compile(
        r"\bcurrent review (?:rules|controls)\s+are\s+sponsor-approved\b",
        re.IGNORECASE,
    ),
}


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_registry(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
    )
    if not isinstance(value, dict):
        raise TypeError("registry root must be an object")
    return value


def validate(root: Path) -> list[str]:
    failures: list[str] = []
    try:
        registry = _load_registry(root / REGISTRY_PATH)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return [f"Policy authority registry is unavailable or invalid: {exc}"]
    try:
        question_text = (root / QUESTIONS_PATH).read_text(encoding="utf-8")
    except OSError:
        return ["OPEN_QUESTIONS.md is unavailable"]

    expected_root_fields = {
        "schema_version",
        "activation_scope",
        "authority_status_values",
        "policies",
    }
    if set(registry) != expected_root_fields:
        failures.append("Registry root fields do not match the strict schema")
    if registry.get("schema_version") != 1:
        failures.append("schema_version must be 1")
    if registry.get("activation_scope") != "SPONSOR_POLICY_PRODUCTION":
        failures.append("activation_scope must be SPONSOR_POLICY_PRODUCTION")
    status_values = registry.get("authority_status_values")
    if not isinstance(status_values, list) or set(status_values) != AUTHORITY_STATUSES:
        failures.append("authority_status_values must contain the exact strict vocabulary")

    policies = registry.get("policies")
    if not isinstance(policies, list):
        return failures + ["policies must be an array"]

    open_questions = set(QUESTION_HEADING.findall(question_text))
    seen_ids: set[str] = set()
    entries: dict[str, dict[str, Any]] = {}
    for index, raw_entry in enumerate(policies):
        label = f"policies[{index}]"
        if not isinstance(raw_entry, dict):
            failures.append(f"{label} must be an object")
            continue
        if set(raw_entry) != ENTRY_FIELDS:
            failures.append(f"{label} fields do not match the strict schema")
            continue
        policy_id = raw_entry.get("policy_id")
        status = raw_entry.get("authority_status")
        source = raw_entry.get("source_reference")
        question = raw_entry.get("blocking_sponsor_question")
        enabled = raw_entry.get("runtime_enabled")

        if not isinstance(policy_id, str) or POLICY_ID.fullmatch(policy_id) is None:
            failures.append(f"{label}.policy_id must use uppercase snake case")
            continue
        if policy_id in seen_ids:
            failures.append(f"Duplicate policy_id: {policy_id}")
        seen_ids.add(policy_id)
        entries[policy_id] = raw_entry

        if status not in AUTHORITY_STATUSES:
            failures.append(f"{policy_id} has unsupported authority_status")
        if (
            not isinstance(source, str)
            or not source.startswith("docs/")
            or "private/" in source.lower()
        ):
            failures.append(f"{policy_id} source_reference must be a safe docs/ path")
        if type(enabled) is not bool:
            failures.append(f"{policy_id} runtime_enabled must be boolean")
        if question is not None and (
            not isinstance(question, str) or QUESTION_ID.fullmatch(question) is None
        ):
            failures.append(f"{policy_id} blocking_sponsor_question is invalid")
        if isinstance(question, str) and question not in open_questions:
            failures.append(f"{policy_id} references non-open sponsor question {question}")
        if status in {"UNKNOWN_BLOCKED", "PROJECT_DEFINED_PROVISIONAL"} and enabled is True:
            failures.append(f"{policy_id} cannot enable provisional or blocked policy")
        if enabled is True and status != "SPONSOR_CONFIRMED":
            failures.append(f"{policy_id} runtime activation requires SPONSOR_CONFIRMED")
        if isinstance(question, str) and status == "SPONSOR_CONFIRMED":
            failures.append(f"{policy_id} cannot be sponsor-confirmed while {question} is open")
        if isinstance(question, str) and enabled is True:
            failures.append(f"{policy_id} cannot be runtime-enabled while {question} is open")

    missing = sorted(REQUIRED_POLICY_IDS - seen_ids)
    if missing:
        failures.append("Missing required policy gates: " + ", ".join(missing))
    for policy_id, expected_question in REQUIRED_POLICY_GATES.items():
        entry = entries.get(policy_id)
        if entry is not None and entry.get("blocking_sponsor_question") != expected_question:
            failures.append(f"{policy_id} must remain blocked by {expected_question}")

    for relative_path in GOVERNED_DOCS:
        try:
            text = (root / relative_path).read_text(encoding="utf-8")
        except OSError:
            failures.append(f"Governed policy document is unavailable: {relative_path}")
            continue
        for description, pattern in FORBIDDEN_CLAIMS.items():
            if pattern.search(text):
                failures.append(f"{relative_path}: {description}")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    failures = validate(args.root.resolve())
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        print("POLICY AUTHORITY CHECK: FAIL")
        return 1
    print("POLICY AUTHORITY CHECK: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
