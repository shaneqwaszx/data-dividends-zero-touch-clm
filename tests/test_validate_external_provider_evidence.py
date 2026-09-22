from __future__ import annotations

import importlib.util
import io
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
READINESS_PATH = ROOT / "scripts" / "check_external_provider_readiness.py"
READINESS_SPEC = importlib.util.spec_from_file_location("check_external_provider_readiness", READINESS_PATH)
if READINESS_SPEC is None or READINESS_SPEC.loader is None:
    raise RuntimeError("Unable to load readiness checker")
READINESS = importlib.util.module_from_spec(READINESS_SPEC)
sys.modules[READINESS_SPEC.name] = READINESS
READINESS_SPEC.loader.exec_module(READINESS)
MODULE_PATH = ROOT / "scripts" / "validate_external_provider_evidence.py"
SPEC = importlib.util.spec_from_file_location("evidence_validator_under_test", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load evidence validator")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


VALID = {
    "schema_version": 2,
    "provider_id": "ACRA_MOCK",
    "mode": "mock",
    "classification": "MOCK",
    "operation": "entity_profile",
    "observed_at": "2026-09-21T12:00:00Z",
    "safe_test_case_reference": "SYNTHETIC-123e4567-e89b-42d3-a456-426614174000",
    "correlation_identifier": "123e4567-e89b-42d3-a456-426614174001",
    "http_outcome_category": "NOT_APPLICABLE",
    "contract_reference": "EXTERNAL_PROVIDER_ACTIVATION_CONTRACT",
    "certificate_verification_result": "NOT_APPLICABLE",
    "auth_mechanism_label": "NONE",
    "mapping_reference": "ACRA_CANONICAL_MAPPING",
    "sanitized_result_category": "EXPECTED_SUCCESS",
    "call_order_result": "EXPECTED",
    "redaction_check_result": "PASS",
}


class ExternalProviderEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "evidence.json"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _write(self, value: dict) -> None:
        self.path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def _assert_rejected_without_echo(self, field: str, hostile_value: object) -> None:
        candidate = {**VALID, field: hostile_value}
        self._write(candidate)
        failures = VALIDATOR.validate_document(ROOT, self.path)
        self.assertTrue(failures, (field, hostile_value))
        rendered = "\n".join(failures)
        self.assertIn(field, rendered)
        if isinstance(hostile_value, str):
            self.assertNotIn(hostile_value, rendered)

    def test_valid_sanitized_profile_passes(self) -> None:
        self._write(VALID)
        self.assertEqual(VALIDATOR.validate_document(ROOT, self.path), [])

    def test_schema_and_validator_contracts_are_synchronized(self) -> None:
        self.assertEqual(VALIDATOR.validate_schema_definition(ROOT), [])

    def test_json_schema_and_python_reject_control_and_impossible_dates(self) -> None:
        schema = json.loads((ROOT / VALIDATOR.SCHEMA_PATH).read_text(encoding="utf-8"))
        schema_validator = Draft202012Validator(schema)
        self.assertEqual(list(schema_validator.iter_errors(VALID)), [])

        adverse_values = (
            ("observed_at", VALID["observed_at"] + "\n"),
            ("safe_test_case_reference", VALID["safe_test_case_reference"] + "\n"),
            ("correlation_identifier", VALID["correlation_identifier"] + "\n"),
            ("observed_at", "2026-02-30T12:00:00Z"),
            ("observed_at", "1900-02-29T12:00:00Z"),
        )
        for field, value in adverse_values:
            with self.subTest(field=field, value=value):
                candidate = {**VALID, field: value}
                self.assertTrue(list(schema_validator.iter_errors(candidate)))
                self._write(candidate)
                failures = VALIDATOR.validate_document(ROOT, self.path)
                self.assertTrue(any(field in item for item in failures), failures)

    def test_registry_duplicate_key_is_not_echoed_by_evidence_validator(self) -> None:
        canary = "arbitrary" + "?" + "access_" + "token=opaque"
        disposable_root = Path(self.temp.name) / "root"
        schema_path = disposable_root / VALIDATOR.SCHEMA_PATH
        registry_path = disposable_root / VALIDATOR.REGISTRY_PATH
        schema_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / VALIDATOR.SCHEMA_PATH, schema_path)
        registry_path.write_text(
            '{"' + canary + '": 1, "' + canary + '": 2}\n',
            encoding="utf-8",
        )
        self._write(VALID)

        failures = VALIDATOR.validate_document(disposable_root, self.path)
        self.assertTrue(any("duplicate JSON key" in item for item in failures), failures)
        self.assertNotIn(canary, "\n".join(failures))

        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = VALIDATOR.main(
                [str(self.path), "--root", str(disposable_root)]
            )
        self.assertEqual(exit_code, 1)
        self.assertNotIn(canary, output.getvalue())

    def test_rejects_unknown_credential_field(self) -> None:
        value = {**VALID, "access_token": "redacted"}
        self._write(value)
        failures = VALIDATOR.validate_document(ROOT, self.path)
        self.assertTrue(any("strict schema" in item for item in failures), failures)

    def test_rejects_unknown_generic_field(self) -> None:
        value = {**VALID, "notes": "synthetic observation"}
        self._write(value)
        failures = VALIDATOR.validate_document(ROOT, self.path)
        self.assertTrue(any("strict schema" in item for item in failures), failures)

    def test_rejects_raw_body_and_suspicious_value(self) -> None:
        value = {**VALID, "raw_provider_body": "customer payload"}
        self._write(value)
        failures = VALIDATOR.validate_document(ROOT, self.path)
        self.assertTrue(any("strict schema" in item for item in failures), failures)

    def test_rejects_non_utc_timestamp(self) -> None:
        value = {**VALID, "observed_at": "2026-09-21T20:00:00+08:00"}
        self._write(value)
        failures = VALIDATOR.validate_document(ROOT, self.path)
        self.assertTrue(any("observed_at" in item for item in failures), failures)

    def test_rejects_live_classification_without_registry_state(self) -> None:
        value = {**VALID, "mode": "live", "classification": "LIVE_VERIFIED"}
        self._write(value)
        failures = VALIDATOR.validate_document(ROOT, self.path)
        self.assertTrue(any("LIVE_VERIFIED" in item for item in failures), failures)

    def test_rejects_provider_mismatch(self) -> None:
        value = {**VALID, "provider_id": "PINGFED_AUTH"}
        self._write(value)
        failures = VALIDATOR.validate_document(ROOT, self.path)
        self.assertTrue(any("sandbox evidence" in item or "provider" in item for item in failures), failures)

    def test_rejects_mode_mismatch(self) -> None:
        value = {**VALID, "mode": "local"}
        self._write(value)
        failures = VALIDATOR.validate_document(ROOT, self.path)
        self.assertTrue(any("mode does not match" in item for item in failures), failures)

    def test_rejects_unauthorized_sandbox_success(self) -> None:
        value = {
            **VALID,
            "provider_id": "ACRA_GENERIC_SANDBOX",
            "mode": "sandbox",
            "classification": "PARTIAL",
            "safe_test_case_reference": "AUTHORIZED-123e4567-e89b-42d3-a456-426614174002",
            "certificate_verification_result": "VERIFIED",
            "auth_mechanism_label": "BACKEND_INJECTED",
            "mapping_reference": "ACRA_CANONICAL_MAPPING",
        }
        self._write(value)
        failures = VALIDATOR.validate_document(ROOT, self.path)
        self.assertTrue(any("eligible readiness state" in item for item in failures), failures)
        self.assertTrue(any("authorized sandbox access" in item for item in failures), failures)

    def test_rejects_duplicate_json_keys(self) -> None:
        canary = "arbitrary" + "?" + "access_" + "token=opaque"
        self.path.write_text(
            '{"' + canary + '": 1, "' + canary + '": 2}\n',
            encoding="utf-8",
        )
        failures = VALIDATOR.validate_document(ROOT, self.path)
        self.assertTrue(any("unavailable or invalid" in item for item in failures), failures)
        self.assertNotIn(canary, "\n".join(failures))

        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = VALIDATOR.main([str(self.path), "--root", str(ROOT)])
        self.assertEqual(exit_code, 1)
        self.assertNotIn(canary, output.getvalue())

    def test_rejects_cross_provider_category_combination(self) -> None:
        value = {
            **VALID,
            "operation": "request_access_token",
            "contract_reference": "D-018",
            "certificate_verification_result": "VERIFIED",
            "auth_mechanism_label": "OAUTH2_BEARER",
            "mapping_reference": "GOLDTIER_CANONICAL_MAPPING",
        }
        self._write(value)
        failures = VALIDATOR.validate_document(ROOT, self.path)
        self.assertTrue(any("provider evidence profile" in item for item in failures), failures)

    def test_provider_profiles_reject_every_cross_provider_enum_value(self) -> None:
        for provider_id, profile in VALIDATOR.PROVIDER_PROFILES.items():
            representative = {**VALID, "provider_id": provider_id}
            for field, allowed in profile.items():
                representative[field] = min(allowed)
            self.assertEqual(VALIDATOR.validate_provider_profile(representative), [])

            for field in VALIDATOR.PROVIDER_PROFILE_FIELDS:
                for disallowed in VALIDATOR.ENUMS[field] - profile[field]:
                    with self.subTest(provider_id=provider_id, field=field, value=disallowed):
                        candidate = {**representative, field: disallowed}
                        failures = VALIDATOR.validate_provider_profile(candidate)
                        self.assertTrue(any(field in item for item in failures), failures)

        blocked_profiles = VALIDATOR.ALLOWED_PROVIDERS - set(VALIDATOR.PROVIDER_PROFILES)
        for provider_id in blocked_profiles:
            with self.subTest(blocked_provider_id=provider_id):
                candidate = {**VALID, "provider_id": provider_id}
                failures = VALIDATOR.validate_provider_profile(candidate)
                self.assertTrue(any("no current provider evidence profile" in item for item in failures), failures)

    def test_positive_policy_rejects_hostile_text_in_every_string_field(self) -> None:
        string_fields = tuple(field for field, value in VALID.items() if isinstance(value, str))
        hostile_values = (
            "client.secret",
            "client;secret",
            "client=secret",
            "client|secret",
            "client,secret",
            "client/secret",
            "client\\secret",
            "client secret",
            "client\tsecret",
            "client：secret",
            "client\u2028secret",
            "https://example.invalid/path?token=opaque",
            "Authori" + "zation: " + "Be" + "arer opaque",
            "key=value",
            "query?access_token=opaque",
            "C:\\secrets\\token.txt",
            "embedded_access_token_material",
            "x" * 512,
            "value\x00control",
            "first\nsecond",
        )
        for field in string_fields:
            for hostile_value in hostile_values:
                with self.subTest(field=field, hostile_value=hostile_value):
                    self._assert_rejected_without_echo(field, hostile_value)

    def test_positive_policy_rejects_non_scalar_values_in_every_scalar_field(self) -> None:
        for field in VALID:
            for hostile_value in ({"value": "nested"}, ["array"]):
                with self.subTest(field=field, hostile_type=type(hostile_value).__name__):
                    self._assert_rejected_without_echo(field, hostile_value)


if __name__ == "__main__":
    unittest.main()
