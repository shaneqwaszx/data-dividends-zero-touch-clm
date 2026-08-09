from __future__ import annotations

import importlib.util
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any
from unittest.mock import patch

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validate_goldtier_examples.py"
SPEC = importlib.util.spec_from_file_location("goldtier_validator_under_test", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load the GoldTier contract validator")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


def synthetic_openapi() -> dict[str, Any]:
    return {
        "openapi": "3.1.0",
        "paths": {
            "/v1/synthetic/items": {
                "post": {
                    "operationId": "createSyntheticItem",
                    "parameters": [
                        {
                            "name": "X-Correlation-Id",
                            "in": "header",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                        {
                            "name": "X-Source-Case-Id",
                            "in": "header",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                        {
                            "name": "Idempotency-Key",
                            "in": "header",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": ["payloadKind", "sourceContext"],
                                    "properties": {
                                        "payloadKind": {
                                            "type": "string",
                                            "enum": ["SYNTHETIC"],
                                        },
                                        "sourceContext": {
                                            "type": "object",
                                            "additionalProperties": False,
                                            "required": ["sourceCaseId"],
                                            "properties": {
                                                "sourceCaseId": {"type": "string"}
                                            },
                                        },
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "201": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "required": ["itemId"],
                                        "properties": {"itemId": {"type": "string"}},
                                    }
                                }
                            }
                        },
                        "422": {
                            "content": {
                                "application/problem+json": {
                                    "schema": {"type": "object"}
                                }
                            }
                        },
                    },
                }
            }
        },
    }


def synthetic_request() -> dict[str, Any]:
    return {
        "method": "POST",
        "endpoint": "/v1/synthetic/items",
        "headers": {
            "Authorization": "placeholder-auth",
            "Content-Type": "application/json",
            "Idempotency-Key": "synthetic-idempotency",
            "X-Correlation-Id": "synthetic-correlation",
            "X-Source-Case-Id": "synthetic-case",
        },
        "body": {
            "payloadKind": "SYNTHETIC",
            "sourceContext": {"sourceCaseId": "synthetic-case"},
        },
    }


class GoldTierContractValidatorTests(unittest.TestCase):
    fixture_directory = ROOT / "tmp" / "contract-validator-tests"

    def setUp(self) -> None:
        self.fixture_directory.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        for path in self.fixture_directory.iterdir():
            path.unlink()
        self.fixture_directory.rmdir()

    def classify(self, filename: str, example: dict[str, Any]):
        return VALIDATOR._classify_example(
            filename,
            example,
            synthetic_openapi(),
            Draft202012Validator,
            FormatChecker,
        )

    def test_request_and_response_binding_classify_valid_examples(self) -> None:
        request_result = self.classify("full_request.json", synthetic_request())
        response_result = self.classify("response_success.json", {"itemId": "synthetic"})

        self.assertEqual(request_result.status, VALIDATOR.VALID)
        self.assertEqual(response_result.status, VALIDATOR.VALID)

    def test_schema_failure_is_invalid_and_quarantined(self) -> None:
        request = synthetic_request()
        request["body"]["payloadKind"] = "OUTSIDE_SYNTHETIC_ENUM"

        result = self.classify("full_request.json", request)

        self.assertEqual(result.status, VALIDATOR.INVALID)
        self.assertIn("enum", {issue.rule for issue in result.issues})

    def test_source_case_header_must_equal_body(self) -> None:
        request = synthetic_request()
        request["body"]["sourceContext"]["sourceCaseId"] = "different-synthetic-case"

        result = self.classify("full_request.json", request)

        self.assertEqual(result.status, VALIDATOR.INVALID)
        self.assertIn("matchesHeader", {issue.rule for issue in result.issues})

    def test_strict_mode_fails_when_invalid_result_exists(self) -> None:
        openapi_path = self.fixture_directory / "synthetic-openapi.zip"
        examples_path = self.fixture_directory / "synthetic-examples.zip"
        openapi_path.touch()
        examples_path.touch()
        invalid_result = VALIDATOR.Result(
            "synthetic/full_request.json",
            VALIDATOR.INVALID,
            (VALIDATOR.Issue("body", "/payloadKind", "enum"),),
        )

        with (
            patch.object(
                sys,
                "argv",
                [
                    "validate_goldtier_examples.py",
                    "--openapi-zip",
                    str(openapi_path),
                    "--examples-zip",
                    str(examples_path),
                    "--fail-on-invalid",
                ],
            ),
            patch.object(VALIDATOR, "validate_archives", return_value=[invalid_result]),
            redirect_stdout(io.StringIO()),
        ):
            result = VALIDATOR.main()

        self.assertEqual(result, 1)

    def test_output_does_not_reproduce_invalid_value(self) -> None:
        sensitive_test_value = "synthetic-sensitive-" + "value-123456"
        request = synthetic_request()
        request["body"]["payloadKind"] = sensitive_test_value
        result = self.classify("full_request.json", request)
        output = io.StringIO()

        with redirect_stdout(output):
            VALIDATOR._print_results([result])

        self.assertEqual(result.status, VALIDATOR.INVALID)
        self.assertNotIn(sensitive_test_value, output.getvalue())
        self.assertIn("[enum]", output.getvalue())


if __name__ == "__main__":
    unittest.main()
