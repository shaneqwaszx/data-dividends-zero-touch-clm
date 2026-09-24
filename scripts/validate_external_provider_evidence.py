"""Validate sanitized external-provider evidence without network access."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from check_external_provider_readiness import _load_json as _load_registry

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = Path("docs/contracts/external_provider_evidence.schema.json")
REGISTRY_PATH = Path("docs/contracts/external_provider_readiness_registry.json")
SCHEMA_VERSION = 2
ALLOWED_PROVIDERS = {
    "ACRA_MOCK", "ACRA_GENERIC_SANDBOX", "ACRA_BIZFILE", "IDP_LOCAL_PDF_TEXT",
    "VENDOR_IDP_FUTURE", "OWNERSHIP_LOCAL_ENGINE", "OWNERSHIP_HIERARCHY_FUTURE",
    "GOLDTIER_MOCK", "GOLDTIER_XPI", "GOLDTIER_REAL", "PINGFED_AUTH",
}
REQUIRED_FIELDS = {
    "schema_version", "provider_id", "mode", "classification", "operation",
    "observed_at", "safe_test_case_reference", "correlation_identifier",
    "http_outcome_category", "contract_reference", "certificate_verification_result",
    "auth_mechanism_label", "mapping_reference", "sanitized_result_category",
    "call_order_result", "redaction_check_result",
}
ENUMS = {
    "provider_id": ALLOWED_PROVIDERS,
    "mode": {"mock", "local", "sandbox", "live"},
    "classification": {"MOCK", "LOCAL", "PARTIAL", "DORMANT", "NOT_IMPLEMENTED", "SANDBOX_VERIFIED", "LIVE_VERIFIED"},
    "http_outcome_category": {"SUCCESS", "NOT_FOUND", "PARTIAL", "AUTH_FAILURE", "TIMEOUT", "VALIDATION_FAILURE", "SERVER_FAILURE", "NOT_APPLICABLE"},
    "certificate_verification_result": {"VERIFIED", "NOT_APPLICABLE", "NOT_RUN"},
    "auth_mechanism_label": {"NONE", "BACKEND_INJECTED", "OAUTH2_BEARER", "MTLS", "NOT_APPLICABLE"},
    "sanitized_result_category": {"EXPECTED_SUCCESS", "EXPECTED_NOT_FOUND", "EXPECTED_PARTIAL", "EXPECTED_FAILURE", "STOPPED_FAIL_CLOSED", "NOT_APPLICABLE"},
    "call_order_result": {"EXPECTED", "STOPPED_ON_FAILURE", "NOT_APPLICABLE"},
    "operation": {
        "entity_profile", "officers", "ownership_parties", "relationships",
        "extract_document", "analyze_ownership", "search_party",
        "create_shell_customer", "create_policy", "amend_party",
        "create_related_party", "retrieve_party", "get_policy",
        "request_access_token",
    },
    "contract_reference": {
        *(f"Q-{number:03d}" for number in range(1, 19)),
        "D-009", "D-018", "EXTERNAL_PROVIDER_ACTIVATION_CONTRACT",
    },
    "mapping_reference": {
        "NOT_APPLICABLE", "ACRA_CANONICAL_MAPPING", "IDP_CANONICAL_MAPPING",
        "OWNERSHIP_CANONICAL_MAPPING", "GOLDTIER_CANONICAL_MAPPING",
    },
}
PATTERN_TEXT = {
    "observed_at": (
        r"^(?![\s\S]*[\r\n])(?:"
        r"(?:(?!0000)[0-9]{4})-(?:(?:0[13578]|1[02])-(?:0[1-9]|[12][0-9]|3[01])|"
        r"(?:0[469]|11)-(?:0[1-9]|[12][0-9]|30)|02-(?:0[1-9]|1[0-9]|2[0-8]))|"
        r"(?:(?!0000)(?:[0-9]{2}(?:0[48]|[2468][048]|[13579][26])|"
        r"(?:[02468][048]|[13579][26])00))-02-29)"
        r"T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](?:\.[0-9]{1,6})?Z$"
    ),
    "safe_test_case_reference": (
        r"^(?![\s\S]*[\r\n])(?:SYNTHETIC|AUTHORIZED)-[0-9a-f]{8}-[0-9a-f]{4}-"
        r"[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    ),
    "correlation_identifier": (
        r"^(?![\s\S]*[\r\n])[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
        r"[0-9a-f]{4}-[0-9a-f]{12}$"
    ),
}
TEXT_PATTERNS = {field: re.compile(pattern) for field, pattern in PATTERN_TEXT.items()}
PROVIDER_PROFILE_FIELDS = {
    "mode", "classification", "operation", "http_outcome_category",
    "contract_reference", "certificate_verification_result",
    "auth_mechanism_label", "mapping_reference", "call_order_result",
}
PROVIDER_PROFILES = {
    "ACRA_MOCK": {
        "mode": {"mock"},
        "classification": {"MOCK"},
        "operation": {"entity_profile", "officers", "ownership_parties", "relationships"},
        "http_outcome_category": {"NOT_APPLICABLE"},
        "contract_reference": {"EXTERNAL_PROVIDER_ACTIVATION_CONTRACT"},
        "certificate_verification_result": {"NOT_APPLICABLE"},
        "auth_mechanism_label": {"NONE"},
        "mapping_reference": {"ACRA_CANONICAL_MAPPING"},
        "call_order_result": {"EXPECTED", "STOPPED_ON_FAILURE"},
    },
    "IDP_LOCAL_PDF_TEXT": {
        "mode": {"local"},
        "classification": {"LOCAL"},
        "operation": {"extract_document"},
        "http_outcome_category": {"NOT_APPLICABLE"},
        "contract_reference": {"EXTERNAL_PROVIDER_ACTIVATION_CONTRACT"},
        "certificate_verification_result": {"NOT_APPLICABLE"},
        "auth_mechanism_label": {"NONE"},
        "mapping_reference": {"IDP_CANONICAL_MAPPING"},
        "call_order_result": {"NOT_APPLICABLE"},
    },
    "OWNERSHIP_LOCAL_ENGINE": {
        "mode": {"local"},
        "classification": {"LOCAL"},
        "operation": {"analyze_ownership"},
        "http_outcome_category": {"NOT_APPLICABLE"},
        "contract_reference": {"EXTERNAL_PROVIDER_ACTIVATION_CONTRACT"},
        "certificate_verification_result": {"NOT_APPLICABLE"},
        "auth_mechanism_label": {"NONE"},
        "mapping_reference": {"OWNERSHIP_CANONICAL_MAPPING"},
        "call_order_result": {"NOT_APPLICABLE"},
    },
    "GOLDTIER_MOCK": {
        "mode": {"mock"},
        "classification": {"MOCK"},
        "operation": {"search_party", "create_shell_customer", "create_policy", "amend_party"},
        "http_outcome_category": {"NOT_APPLICABLE"},
        "contract_reference": {"EXTERNAL_PROVIDER_ACTIVATION_CONTRACT"},
        "certificate_verification_result": {"NOT_APPLICABLE"},
        "auth_mechanism_label": {"NONE"},
        "mapping_reference": {"GOLDTIER_CANONICAL_MAPPING"},
        "call_order_result": {"EXPECTED", "STOPPED_ON_FAILURE"},
    },
}
CURRENT_TEST_CASE_PATTERN = (
    r"^(?![\s\S]*[\r\n])SYNTHETIC-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12}$"
)
CURRENT_TEST_CASE_RE = re.compile(CURRENT_TEST_CASE_PATTERN)
EVIDENCE_MODES = {
    "mock": {"mock"},
    "sandbox": {"sandbox"},
    "local": {"local"},
    "local_pdf_text": {"local"},
    "dormant": set(),
    "not_implemented": {"sandbox", "live"},
}


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)
    if not isinstance(value, dict):
        raise TypeError("JSON root must be an object")
    return value


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def validate_schema_definition(root: Path) -> list[str]:
    """Keep the hand-written validator contract synchronized with the JSON profile."""

    try:
        schema = _load_json(root / SCHEMA_PATH)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return [f"Evidence schema is unavailable or invalid: {exc}"]
    failures: list[str] = []
    if set(schema.get("required", [])) != REQUIRED_FIELDS:
        failures.append("Evidence schema required fields diverge from the validator")
    properties = schema.get("properties")
    if not isinstance(properties, dict) or set(properties) != REQUIRED_FIELDS:
        failures.append("Evidence schema properties diverge from the validator")
    for field, allowed in ENUMS.items():
        schema_values = set(properties.get(field, {}).get("enum", [])) if isinstance(properties, dict) else set()
        if schema_values != allowed:
            failures.append(f"Evidence schema enum diverges for {field}")
    for field, pattern in PATTERN_TEXT.items():
        schema_pattern = properties.get(field, {}).get("pattern") if isinstance(properties, dict) else None
        if schema_pattern != pattern:
            failures.append(f"Evidence schema positive grammar diverges for {field}")
    if not isinstance(properties, dict) or properties.get("schema_version", {}).get("const") != SCHEMA_VERSION:
        failures.append(f"Evidence schema schema_version must be const {SCHEMA_VERSION}")
    if not isinstance(properties, dict) or properties.get("redaction_check_result", {}).get("const") != "PASS":
        failures.append("Evidence schema redaction_check_result must be const PASS")
    if not isinstance(properties, dict) or properties.get("observed_at", {}).get("format") != "date-time":
        failures.append("Evidence schema observed_at must declare date-time format")
    if isinstance(properties, dict):
        for field in REQUIRED_FIELDS - {"schema_version"}:
            if properties.get(field, {}).get("type") != "string":
                failures.append(f"Evidence schema {field} must be a string scalar")
    if not isinstance(schema.get("additionalProperties"), bool) or schema["additionalProperties"] is not False:
        failures.append("Evidence schema must reject unknown fields")
    schema_profiles = schema.get("oneOf")
    if not isinstance(schema_profiles, list):
        failures.append("Evidence schema must define provider evidence profiles")
        return failures
    profiles_by_provider: dict[str, Any] = {}
    for profile in schema_profiles:
        profile_properties = profile.get("properties") if isinstance(profile, dict) else None
        provider = profile_properties.get("provider_id", {}).get("const") if isinstance(profile_properties, dict) else None
        if not isinstance(provider, str) or provider in profiles_by_provider:
            failures.append("Evidence schema provider profiles must have unique provider constants")
            continue
        profiles_by_provider[provider] = profile_properties
    if set(profiles_by_provider) != set(PROVIDER_PROFILES):
        failures.append("Evidence schema provider profile inventory diverges from the validator")
    for provider, expected_profile in PROVIDER_PROFILES.items():
        profile_properties = profiles_by_provider.get(provider)
        if not isinstance(profile_properties, dict):
            continue
        expected_fields = PROVIDER_PROFILE_FIELDS | {"provider_id", "safe_test_case_reference"}
        if set(profile_properties) != expected_fields:
            failures.append(f"Evidence schema provider profile fields diverge for {provider}")
            continue
        for field, allowed in expected_profile.items():
            if set(profile_properties.get(field, {}).get("enum", [])) != allowed:
                failures.append(f"Evidence schema provider profile diverges for {provider}.{field}")
        if profile_properties.get("safe_test_case_reference", {}).get("pattern") != CURRENT_TEST_CASE_PATTERN:
            failures.append(f"Evidence schema provider profile diverges for {provider}.safe_test_case_reference")
    return failures


def validate_provider_profile(evidence: dict[str, Any]) -> list[str]:
    """Bind every accepted observation to one current credential-free provider profile."""

    provider_id = evidence.get("provider_id")
    profile = PROVIDER_PROFILES.get(provider_id) if isinstance(provider_id, str) else None
    if profile is None:
        return ["provider_id has no current provider evidence profile"]
    failures: list[str] = []
    for field, allowed in profile.items():
        value = evidence.get(field)
        if not isinstance(value, str) or value not in allowed:
            failures.append(f"{field} is incompatible with the provider evidence profile")
    test_reference = evidence.get("safe_test_case_reference")
    if not isinstance(test_reference, str) or CURRENT_TEST_CASE_RE.fullmatch(test_reference) is None:
        failures.append("safe_test_case_reference is incompatible with the provider evidence profile")
    return failures


def validate_document(root: Path, path: Path) -> list[str]:
    failures: list[str] = []
    failures.extend(validate_schema_definition(root))
    try:
        evidence = _load_json(path)
        registry = _load_registry(root / REGISTRY_PATH)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return [f"Evidence or registry is unavailable or invalid: {exc}"]

    if set(evidence) != REQUIRED_FIELDS:
        failures.append("Evidence fields do not match the strict schema")
    if evidence.get("schema_version") != SCHEMA_VERSION or isinstance(evidence.get("schema_version"), bool):
        failures.append(f"schema_version must be {SCHEMA_VERSION}")
    provider_id = evidence.get("provider_id")
    if not isinstance(provider_id, str) or provider_id not in ALLOWED_PROVIDERS:
        failures.append("provider_id is not supported")
    providers = registry.get("providers", [])
    entry = next(
        (item for item in providers if isinstance(item, dict) and item.get("provider_id") == provider_id),
        None,
    ) if isinstance(provider_id, str) else None
    if entry is None:
        failures.append("provider_id is absent from the readiness registry")
    for field, allowed in ENUMS.items():
        value = evidence.get(field)
        if not isinstance(value, str) or value not in allowed:
            failures.append(f"{field} is unsupported")
    for field, pattern in TEXT_PATTERNS.items():
        value = evidence.get(field)
        if not isinstance(value, str) or pattern.fullmatch(value) is None:
            failures.append(f"{field} has an invalid format")
    observed_at = evidence.get("observed_at")
    if isinstance(observed_at, str) and TEXT_PATTERNS["observed_at"].fullmatch(observed_at):
        try:
            datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
        except ValueError:
            failures.append("observed_at is not a valid timestamp")
    if evidence.get("redaction_check_result") != "PASS":
        failures.append("redaction_check_result must be PASS")
    failures.extend(validate_provider_profile(evidence))
    if isinstance(entry, dict):
        state = entry.get("activation_state")
        classification = evidence.get("classification")
        runtime_mode = entry.get("runtime_mode")
        mode = evidence.get("mode")
        if not isinstance(mode, str) or mode not in EVIDENCE_MODES.get(runtime_mode, set()):
            failures.append("evidence mode does not match the provider runtime mode")
        if (
            isinstance(classification, str)
            and classification in {"MOCK", "LOCAL", "PARTIAL", "DORMANT", "NOT_IMPLEMENTED"}
            and classification != entry.get("current_classification")
        ):
            failures.append("provider classification does not match the readiness registry")
        if classification == "LIVE_VERIFIED" and state != "LIVE_VERIFIED":
            failures.append("Live evidence requires registry activation_state LIVE_VERIFIED")
        if classification == "SANDBOX_VERIFIED" and state not in {"SANDBOX_VERIFIED", "LIVE_VERIFIED"}:
            failures.append("sandbox evidence requires a sandbox-verified registry state")
        if mode == "live" and classification != "LIVE_VERIFIED":
            failures.append("live mode requires LIVE_VERIFIED classification")
        if mode == "sandbox" and classification == "LIVE_VERIFIED":
            failures.append("sandbox mode cannot be Live-verified")
        if mode == "sandbox":
            if state not in {"READY_FOR_AUTHORIZED_SANDBOX_PROOF", "SANDBOX_VERIFIED", "LIVE_VERIFIED"}:
                failures.append("sandbox evidence requires an eligible readiness state")
            if entry.get("authorized_sandbox_access") is not True:
                failures.append("sandbox evidence requires authorized sandbox access")
        if (
            mode == "live"
            and (state != "LIVE_VERIFIED" or entry.get("authorized_live_evidence_present") is not True)
        ):
            failures.append("live evidence requires separate authorized Live evidence")
        if state == "LIVE_VERIFIED" and entry.get("authorized_live_evidence_present") is not True:
            failures.append("registry does not contain separate authorized Live evidence")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    failures = validate_document(args.root.resolve(), args.path.resolve())
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        print("EXTERNAL PROVIDER EVIDENCE VALIDATOR: FAIL")
        return 1
    print("EXTERNAL PROVIDER EVIDENCE VALIDATOR: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
