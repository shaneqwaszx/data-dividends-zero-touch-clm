"""Validate the strict sanitized official ACRA Mock evidence receipt."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = Path("docs/evidence/acra_api_marketplace_mock_2026-09-26.json")
FIELDS = {
    "provider",
    "classification",
    "timestamp_utc",
    "operation_name",
    "safe_endpoint",
    "http_status",
    "response_content_type",
    "bounded_response_bytes",
    "returned_requested_uen_equal",
    "strict_schema_validation",
    "result_classification",
}
ENDPOINTS = {
    "entityBasicInformation": (
        "https://api-sandbox.bizfile.gov.sg/api/acra/entityQuery/entityBasicInformation"
    ),
    "coShareholdersDetails": (
        "https://api-sandbox.bizfile.gov.sg/api/acra/entityQuery/coShareholdersDetails"
    ),
    "coCapitalDetails": (
        "https://api-sandbox.bizfile.gov.sg/api/acra/entityQuery/coCapitalDetails"
    ),
}
SCHEMA_RESULTS = {"PASS", "FAIL", "SCHEMA_OBSERVED_ONLY"}
OUTCOMES = {"SUCCESS", "EMPTY", "SUCCESS_SCHEMA_ONLY", "FAILURE"}
SUCCESS_BINDINGS = {
    "SUCCESS": ("PASS", True),
    "EMPTY": ("PASS", False),
    "SUCCESS_SCHEMA_ONLY": ("SCHEMA_OBSERVED_ONLY", True),
}
OPERATION_OUTCOMES = {
    "entityBasicInformation": {"SUCCESS", "EMPTY", "FAILURE"},
    "coShareholdersDetails": {"SUCCESS", "EMPTY", "FAILURE"},
    "coCapitalDetails": {"SUCCESS_SCHEMA_ONLY", "FAILURE"},
}
TIMESTAMP = re.compile(
    r"^(?![\s\S]*[\r\n])[0-9]{4}-[0-9]{2}-[0-9]{2}T"
    r"[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z$"
)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def validate(path: Path) -> list[str]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return ["evidence is unavailable or invalid JSON"]
    return validate_records(value)


def validate_records(value: object) -> list[str]:
    if not isinstance(value, list) or not 1 <= len(value) <= 8:
        return ["evidence must contain between one and eight records"]
    failures: list[str] = []
    for index, record in enumerate(value):
        label = f"records[{index}]"
        if not isinstance(record, dict) or set(record) != FIELDS:
            failures.append(f"{label} fields do not match the strict receipt")
            continue
        operation = record.get("operation_name")
        if (
            record.get("provider") != "ACRA_API_MARKETPLACE_MOCK"
            or record.get("classification") != "MOCK"
        ):
            failures.append(f"{label} provider classification is invalid")
        if not isinstance(operation, str) or operation not in ENDPOINTS:
            failures.append(f"{label} operation is invalid")
        elif record.get("safe_endpoint") != ENDPOINTS[operation]:
            failures.append(f"{label} endpoint is incompatible with the operation")
        timestamp = record.get("timestamp_utc")
        if not isinstance(timestamp, str) or TIMESTAMP.fullmatch(timestamp) is None:
            failures.append(f"{label} timestamp is invalid")
        else:
            try:
                datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError:
                failures.append(f"{label} timestamp is invalid")
        status = record.get("http_status")
        if type(status) is not int or not 100 <= status <= 599:
            failures.append(f"{label} HTTP status is invalid")
        size = record.get("bounded_response_bytes")
        if type(size) is not int or not 0 <= size <= 262_144:
            failures.append(f"{label} response byte length is invalid")
        if record.get("response_content_type") != "application/json":
            failures.append(f"{label} content type is invalid")
        if type(record.get("returned_requested_uen_equal")) is not bool:
            failures.append(f"{label} UEN equality result is invalid")
        if record.get("strict_schema_validation") not in SCHEMA_RESULTS:
            failures.append(f"{label} schema result is invalid")
        outcome = record.get("result_classification")
        if outcome not in OUTCOMES:
            failures.append(f"{label} operation result is invalid")
        elif (
            isinstance(operation, str)
            and operation in OPERATION_OUTCOMES
            and outcome not in OPERATION_OUTCOMES[operation]
        ):
            failures.append(f"{label} outcome is incompatible with the operation")
        elif outcome in SUCCESS_BINDINGS:
            expected_schema, expected_identity = SUCCESS_BINDINGS[outcome]
            if (
                status != 200
                or record.get("strict_schema_validation") != expected_schema
                or record.get("returned_requested_uen_equal") is not expected_identity
            ):
                failures.append(f"{label} successful outcome fields are contradictory")
        elif record.get("strict_schema_validation") != "FAIL":
            failures.append(f"{label} failure outcome requires failed schema validation")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default=str(DEFAULT_EVIDENCE))
    args = parser.parse_args()
    failures = validate(ROOT / args.path)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("ACRA Marketplace Mock evidence: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
