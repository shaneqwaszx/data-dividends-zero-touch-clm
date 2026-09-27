from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validate_acra_marketplace_mock_evidence.py"
SPEC = importlib.util.spec_from_file_location("acra_mock_evidence_validator", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load ACRA Mock evidence validator")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class AcraMarketplaceMockEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.current = json.loads(
            (ROOT / VALIDATOR.DEFAULT_EVIDENCE).read_text(encoding="utf-8")
        )
        schema = json.loads(
            (ROOT / "docs/contracts/acra_api_marketplace_mock_evidence.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.schema = Draft202012Validator(schema)

    def _assert_rejected(self, candidate: dict[str, object]) -> None:
        self.assertTrue(VALIDATOR.validate_records([candidate]))
        self.assertTrue(list(self.schema.iter_errors([candidate])))

    def test_current_receipt_passes(self) -> None:
        self.assertEqual(VALIDATOR.validate_records(self.current), [])
        self.assertEqual(list(self.schema.iter_errors(self.current)), [])

    def test_rejects_extra_field_or_production_endpoint(self) -> None:
        extra = [{**self.current[0], "token": "forbidden"}]
        self.assertTrue(VALIDATOR.validate_records(extra))

        production = [
            {
                **self.current[0],
                "safe_endpoint": (
                    "https://api.bizfile.gov.sg/api/acra/"
                    "entityQuery/entityBasicInformation"
                ),
            }
        ]
        self.assertTrue(VALIDATOR.validate_records(production))

    def test_rejects_invalid_size_status_timestamp_and_boolean(self) -> None:
        candidate = [
            {
                **self.current[0],
                "http_status": True,
                "bounded_response_bytes": 262_145,
                "timestamp_utc": "2026-02-30T00:00:00Z",
                "returned_requested_uen_equal": "true",
            }
        ]
        failures = VALIDATOR.validate_records(candidate)
        self.assertGreaterEqual(len(failures), 4)

    def test_rejects_contradictory_success_and_failure_outcomes(self) -> None:
        contradictions = (
            {
                **self.current[0],
                "http_status": 500,
                "returned_requested_uen_equal": False,
            },
            {
                **self.current[0],
                "strict_schema_validation": "FAIL",
            },
            {
                **self.current[0],
                "result_classification": "FAILURE",
            },
        )
        for candidate in contradictions:
            with self.subTest(candidate=candidate):
                self.assertTrue(VALIDATOR.validate_records([candidate]))

    def test_accepts_only_bound_empty_and_schema_observation_outcomes(self) -> None:
        empty = self.current[2]
        observed = self.current[3]
        for candidate in (empty, observed):
            with self.subTest(outcome=candidate["result_classification"]):
                self.assertEqual(VALIDATOR.validate_records([candidate]), [])

    def test_rejects_cross_operation_outcomes_and_endpoint_mismatch(self) -> None:
        capital_as_strict_success = {
            **self.current[3],
            "strict_schema_validation": "PASS",
            "result_classification": "SUCCESS",
        }
        entity_as_schema_only = {
            **self.current[0],
            "strict_schema_validation": "SCHEMA_OBSERVED_ONLY",
            "result_classification": "SUCCESS_SCHEMA_ONLY",
        }
        entity_with_shareholder_endpoint = {
            **self.current[0],
            "safe_endpoint": VALIDATOR.ENDPOINTS["coShareholdersDetails"],
        }
        for candidate in (
            capital_as_strict_success,
            entity_as_schema_only,
            entity_with_shareholder_endpoint,
        ):
            with self.subTest(operation=candidate["operation_name"]):
                self._assert_rejected(candidate)


if __name__ == "__main__":
    unittest.main()
