"""Validate the strict, network-free external-provider readiness registry."""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = Path("docs/contracts/external_provider_readiness_registry.json")
QUESTIONS_PATH = Path("docs/sponsor-questions/OPEN_QUESTIONS.md")
CONFIG_PATH = Path("apps/backend/app/config.py")

CLASSIFICATION_VALUES = ["MOCK", "LOCAL", "PARTIAL", "DORMANT", "NOT_IMPLEMENTED"]
CLASSIFICATIONS = set(CLASSIFICATION_VALUES)
ACTIVATION_STATE_VALUES = [
    "INTERNAL_POC_ONLY",
    "BLOCKED",
    "PARTIAL_SCAFFOLD_ONLY",
    "SANDBOX_PARTIAL",
    "READY_FOR_AUTHORIZED_SANDBOX_PROOF",
    "SANDBOX_VERIFIED",
    "LIVE_VERIFIED",
]
ACTIVATION_STATES = set(ACTIVATION_STATE_VALUES)
QUESTION_ID = re.compile(r"Q-\d{3}\Z")
QUESTION_HEADING = re.compile(r"^###\s+(Q-\d{3})\b", re.MULTILINE)
PROVIDER_ID = re.compile(r"^[A-Z][A-Z0-9_]{2,63}\Z")

ENTRY_FIELDS = {
    "provider_id",
    "current_classification",
    "activation_state",
    "runtime_mode",
    "required_questions",
    "contract_authority_complete",
    "auth_authority_complete",
    "tls_authority_complete",
    "mapping_authority_complete",
    "secret_delivery_ready",
    "authorized_sandbox_access",
    "sanitized_evidence_present",
    "authorized_live_evidence_present",
    "runtime_activation_enabled",
}
ROOT_FIELDS = {
    "schema_version",
    "current_classification_values",
    "activation_state_values",
    "providers",
}

EXPECTED = {
    "ACRA_MOCK": ("MOCK", "INTERNAL_POC_ONLY", "mock", True),
    "ACRA_GENERIC_SANDBOX": ("PARTIAL", "PARTIAL_SCAFFOLD_ONLY", "sandbox", False),
    "ACRA_BIZFILE": ("DORMANT", "BLOCKED", "dormant", False),
    "IDP_LOCAL_PDF_TEXT": ("LOCAL", "INTERNAL_POC_ONLY", "local_pdf_text", True),
    "VENDOR_IDP_FUTURE": ("NOT_IMPLEMENTED", "BLOCKED", "not_implemented", False),
    "OWNERSHIP_LOCAL_ENGINE": ("LOCAL", "INTERNAL_POC_ONLY", "local", True),
    "OWNERSHIP_HIERARCHY_FUTURE": ("NOT_IMPLEMENTED", "BLOCKED", "not_implemented", False),
    "GOLDTIER_MOCK": ("MOCK", "INTERNAL_POC_ONLY", "mock", True),
    "GOLDTIER_XPI": ("PARTIAL", "SANDBOX_PARTIAL", "sandbox", True),
    "GOLDTIER_REAL": ("NOT_IMPLEMENTED", "BLOCKED", "not_implemented", False),
    "PINGFED_AUTH": ("NOT_IMPLEMENTED", "BLOCKED", "not_implemented", False),
}

REQUIRED_QUESTIONS = {
    "ACRA_GENERIC_SANDBOX": {"Q-012"},
    "ACRA_BIZFILE": {"Q-012"},
    "VENDOR_IDP_FUTURE": {"Q-003", "Q-005", "Q-013", "Q-014"},
    "OWNERSHIP_HIERARCHY_FUTURE": {"Q-002", "Q-004", "Q-006", "Q-007"},
    "GOLDTIER_XPI": {"Q-001", "Q-007", "Q-009", "Q-010", "Q-011", "Q-018"},
    "GOLDTIER_REAL": {"Q-001", "Q-007", "Q-008", "Q-009", "Q-010", "Q-011", "Q-018"},
    "PINGFED_AUTH": {"Q-008", "Q-018"},
}
QUESTION_GATE_FIELDS = {
    "Q-001": {"contract_authority_complete"},
    "Q-002": {"contract_authority_complete", "mapping_authority_complete"},
    "Q-003": {"contract_authority_complete", "mapping_authority_complete"},
    "Q-004": {"contract_authority_complete", "mapping_authority_complete"},
    "Q-005": {"contract_authority_complete", "mapping_authority_complete"},
    "Q-006": {"contract_authority_complete", "mapping_authority_complete"},
    "Q-007": {"contract_authority_complete", "mapping_authority_complete"},
    "Q-008": {"auth_authority_complete"},
    "Q-009": {"contract_authority_complete", "mapping_authority_complete"},
    "Q-010": {"contract_authority_complete", "mapping_authority_complete"},
    "Q-011": {"contract_authority_complete", "mapping_authority_complete"},
    "Q-012": {"contract_authority_complete", "auth_authority_complete", "tls_authority_complete"},
    "Q-013": {"contract_authority_complete", "mapping_authority_complete"},
    "Q-014": {"contract_authority_complete", "mapping_authority_complete"},
    "Q-018": {"contract_authority_complete"},
}

AUTHORITY_STATES = {
    "READY_FOR_AUTHORIZED_SANDBOX_PROOF",
    "SANDBOX_VERIFIED",
    "LIVE_VERIFIED",
}
BOOLEAN_FIELDS = {
    "contract_authority_complete",
    "auth_authority_complete",
    "tls_authority_complete",
    "mapping_authority_complete",
    "secret_delivery_ready",
    "authorized_sandbox_access",
    "sanitized_evidence_present",
    "authorized_live_evidence_present",
    "runtime_activation_enabled",
}
PROOF_FIELDS = {
    "secret_delivery_ready",
    "authorized_sandbox_access",
    "sanitized_evidence_present",
    "authorized_live_evidence_present",
}


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)
    if not isinstance(value, dict):
        raise TypeError("JSON root must be an object")
    return value


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


def validate(root: Path) -> list[str]:
    failures: list[str] = []
    try:
        registry = _load_json(root / REGISTRY_PATH)
        question_text = (root / QUESTIONS_PATH).read_text(encoding="utf-8")
        config_text = (root / CONFIG_PATH).read_text(encoding="utf-8")
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return [f"Readiness inputs are unavailable or invalid: {exc}"]

    if set(registry) != ROOT_FIELDS:
        failures.append("Registry root fields do not match the strict schema")
    if registry.get("schema_version") != 1:
        failures.append("schema_version must be 1")
    if registry.get("current_classification_values") != CLASSIFICATION_VALUES:
        failures.append("current_classification_values must match the strict vocabulary")
    if registry.get("activation_state_values") != ACTIVATION_STATE_VALUES:
        failures.append("activation_state_values must match the strict vocabulary")

    open_questions = set(QUESTION_HEADING.findall(question_text))
    providers = registry.get("providers")
    if not isinstance(providers, list):
        return failures + ["providers must be an array"]

    seen: set[str] = set()
    entries: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(providers):
        label = f"providers[{index}]"
        if not isinstance(entry, dict):
            failures.append(f"{label} must be an object")
            continue
        if set(entry) != ENTRY_FIELDS:
            failures.append(f"{label} fields do not match the strict schema")
            continue
        provider_id = entry.get("provider_id")
        if not isinstance(provider_id, str) or PROVIDER_ID.fullmatch(provider_id) is None:
            failures.append(f"{label}.provider_id is invalid")
            continue
        if provider_id in seen:
            failures.append(f"Duplicate provider_id: {provider_id}")
        seen.add(provider_id)
        entries[provider_id] = entry
        classification = entry.get("current_classification")
        state = entry.get("activation_state")
        if classification not in CLASSIFICATIONS:
            failures.append(f"{provider_id} has unsupported current_classification")
        if state not in ACTIVATION_STATES:
            failures.append(f"{provider_id} has unsupported activation_state")
        if not isinstance(entry.get("runtime_mode"), str) or not entry["runtime_mode"]:
            failures.append(f"{provider_id}.runtime_mode must be non-empty")
        questions = entry.get("required_questions")
        if not isinstance(questions, list) or any(
            not isinstance(question, str) or QUESTION_ID.fullmatch(question) is None
            for question in questions
        ) or len(set(questions)) != len(questions):
            failures.append(f"{provider_id}.required_questions is invalid")
        else:
            missing_open_reference = sorted(set(questions) - open_questions)
            if missing_open_reference:
                failures.append(
                    f"{provider_id} references non-open sponsor question(s): "
                    + ", ".join(missing_open_reference)
                )
        for field in BOOLEAN_FIELDS:
            if type(entry.get(field)) is not bool:
                failures.append(f"{provider_id}.{field} must be boolean")

    missing = sorted(set(EXPECTED) - seen)
    extra = sorted(seen - set(EXPECTED))
    if missing:
        failures.append("Missing required providers: " + ", ".join(missing))
    if extra:
        failures.append("Unexpected providers: " + ", ".join(extra))

    for provider_id, (classification, state, mode, runtime_enabled) in EXPECTED.items():
        entry = entries.get(provider_id)
        if entry is None:
            continue
        if entry.get("current_classification") != classification:
            failures.append(f"{provider_id} classification contradicts current project truth")
        if entry.get("activation_state") != state:
            failures.append(f"{provider_id} activation_state contradicts current project truth")
        if entry.get("runtime_mode") != mode:
            failures.append(f"{provider_id} runtime_mode contradicts current project truth")
        if entry.get("runtime_activation_enabled") is not runtime_enabled:
            failures.append(f"{provider_id} runtime_activation_enabled contradicts current composition")
        required = REQUIRED_QUESTIONS.get(provider_id, set())
        actual = set(entry.get("required_questions", []))
        if not required <= actual:
            failures.append(
                f"{provider_id} removed required sponsor gate(s): "
                + ", ".join(sorted(required - actual))
            )
        if entry.get("activation_state") in AUTHORITY_STATES and actual & open_questions:
            failures.append(
                f"{provider_id} is ready/verified while required sponsor questions remain open: "
                + ", ".join(sorted(actual & open_questions))
            )
        for question in sorted(actual & open_questions):
            complete_fields = sorted(
                field
                for field in QUESTION_GATE_FIELDS.get(question, set())
                if entry.get(field) is True
            )
            if complete_fields:
                failures.append(
                    f"{provider_id} declares {question} authority complete while it remains open: "
                    + ", ".join(complete_fields)
                )

        if state in AUTHORITY_STATES:
            gate_fields = [
                "contract_authority_complete",
                "auth_authority_complete",
                "tls_authority_complete",
                "mapping_authority_complete",
            ]
            if any(entry.get(field) is not True for field in gate_fields):
                failures.append(f"{provider_id} is ready/verified with an incomplete authority gate")
            if state in {"SANDBOX_VERIFIED", "LIVE_VERIFIED"} and entry.get("sanitized_evidence_present") is not True:
                failures.append(f"{provider_id} is verified without sanitized evidence")
            if state in {"SANDBOX_VERIFIED", "LIVE_VERIFIED"} and entry.get("authorized_sandbox_access") is not True:
                failures.append(f"{provider_id} is verified without authorized sandbox access")
            if state == "LIVE_VERIFIED" and entry.get("authorized_live_evidence_present") is not True:
                failures.append(f"{provider_id} is Live-verified without separate Live evidence")
            if entry.get("runtime_activation_enabled") is not True:
                failures.append(f"{provider_id} is ready/verified while runtime activation is disabled")

        expected_proof = {
            "INTERNAL_POC_ONLY": set(),
            "BLOCKED": set(),
            "PARTIAL_SCAFFOLD_ONLY": set(),
            "SANDBOX_PARTIAL": {
                "authorized_sandbox_access",
                "sanitized_evidence_present",
            },
            "READY_FOR_AUTHORIZED_SANDBOX_PROOF": {"secret_delivery_ready", "authorized_sandbox_access"},
            "SANDBOX_VERIFIED": {"secret_delivery_ready", "authorized_sandbox_access", "sanitized_evidence_present"},
            "LIVE_VERIFIED": PROOF_FIELDS,
        }.get(state, set())
        for proof_field in PROOF_FIELDS:
            actual = entry.get(proof_field) is True
            if actual != (proof_field in expected_proof):
                expected = "true" if proof_field in expected_proof else "false"
                failures.append(
                    f"{provider_id}.{proof_field} must be {expected} for activation_state {state}"
                )

        if entry.get("runtime_activation_enabled") is True and state not in {
            "INTERNAL_POC_ONLY",
            "SANDBOX_PARTIAL",
            "SANDBOX_VERIFIED",
            "LIVE_VERIFIED",
        }:
            failures.append(f"{provider_id} runtime activation is true for a blocked/scaffold state")
        if (
            entry.get("runtime_activation_enabled") is True
            and state in {"SANDBOX_VERIFIED", "LIVE_VERIFIED"}
            and any(entry.get(field) is not True for field in (
                "contract_authority_complete",
                "auth_authority_complete",
                "tls_authority_complete",
                "mapping_authority_complete",
            ))
        ):
            failures.append(f"{provider_id} runtime activation bypasses a required gate")

    try:
        goldtier_setting = _literal_setting(config_text, "goldtier_connector_mode")
    except SyntaxError:
        goldtier_setting = None
    if goldtier_setting != ({"mock", "sandbox"}, "mock"):
        failures.append(
            "Current GoldTier Settings must expose only explicit mock/sandbox modes with Mock default"
        )
    if entries.get("GOLDTIER_REAL", {}).get("runtime_activation_enabled") is True:
        failures.append("GOLDTIER_REAL cannot be runtime enabled while Q-008/D-018 is unresolved")
    if entries.get("PINGFED_AUTH", {}).get("current_classification") != "NOT_IMPLEMENTED":
        failures.append("PingFed must remain not implemented")
    if entries.get("VENDOR_IDP_FUTURE", {}).get("current_classification") != "NOT_IMPLEMENTED":
        failures.append("Vendor IDP/OCR must remain not implemented")
    if entries.get("OWNERSHIP_LOCAL_ENGINE", {}).get("runtime_mode") == "external":
        failures.append("Local ownership engine cannot be labelled external")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    failures = validate(args.root.resolve())
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        print("EXTERNAL PROVIDER READINESS CHECK: FAIL")
        return 1
    print("EXTERNAL PROVIDER READINESS CHECK: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
