from __future__ import annotations

import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "check_external_provider_readiness.py"
SPEC = importlib.util.spec_from_file_location(
    "readiness_checker_under_test", MODULE_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load readiness checker")
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


class ExternalProviderReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(dir=ROOT)
        self.root = Path(self.temp.name)
        for relative in (
            CHECKER.REGISTRY_PATH,
            CHECKER.QUESTIONS_PATH,
            CHECKER.CONFIG_PATH,
        ):
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _registry(self) -> dict:
        path = self.root / CHECKER.REGISTRY_PATH
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_registry(self, value: dict) -> None:
        (self.root / CHECKER.REGISTRY_PATH).write_text(
            json.dumps(value, indent=2) + "\n", encoding="utf-8"
        )

    def test_current_registry_passes(self) -> None:
        self.assertEqual(CHECKER.validate(self.root), [])

    def test_rejects_live_acra_while_q012_is_open(self) -> None:
        value = self._registry()
        entry = next(
            item
            for item in value["providers"]
            if item["provider_id"] == "ACRA_GENERIC_SANDBOX"
        )
        entry["activation_state"] = "LIVE_VERIFIED"
        entry["runtime_activation_enabled"] = True
        self._write_registry(value)
        failures = CHECKER.validate(self.root)
        self.assertTrue(
            any("ACRA_GENERIC_SANDBOX" in item for item in failures), failures
        )
        self.assertTrue(
            any("required sponsor questions remain open" in item for item in failures),
            failures,
        )

    def test_rejects_api_marketplace_return_to_blocked_runtime_state(
        self,
    ) -> None:
        value = self._registry()
        entry = next(
            item
            for item in value["providers"]
            if item["provider_id"] == "ACRA_API_MARKETPLACE_MOCK"
        )
        entry["activation_state"] = "BLOCKED_AUTHORITY"
        entry["runtime_activation_enabled"] = False
        entry["secret_delivery_ready"] = False
        self._write_registry(value)

        failures = CHECKER.validate(self.root)

        self.assertTrue(
            any("ACRA_API_MARKETPLACE_MOCK" in item for item in failures), failures
        )

    def test_rejects_missing_api_marketplace_auth_failure_evidence(self) -> None:
        value = self._registry()
        entry = next(
            item
            for item in value["providers"]
            if item["provider_id"] == "ACRA_API_MARKETPLACE_MOCK"
        )
        entry["sanitized_evidence_present"] = False
        self._write_registry(value)

        failures = CHECKER.validate(self.root)

        self.assertTrue(
            any("sanitized_evidence_present must be true" in item for item in failures),
            failures,
        )

    def test_rejects_bizfile_activation_or_reclassification(self) -> None:
        value = self._registry()
        entry = next(
            item for item in value["providers"] if item["provider_id"] == "ACRA_BIZFILE"
        )
        entry["current_classification"] = "MOCK"
        entry["runtime_activation_enabled"] = True
        self._write_registry(value)

        failures = CHECKER.validate(self.root)

        self.assertTrue(any("ACRA_BIZFILE" in item for item in failures), failures)

    def test_rejects_removed_required_sponsor_gate(self) -> None:
        value = self._registry()
        entry = next(
            item
            for item in value["providers"]
            if item["provider_id"] == "GOLDTIER_REAL"
        )
        entry["required_questions"].remove("Q-008")
        self._write_registry(value)
        failures = CHECKER.validate(self.root)
        self.assertTrue(
            any("removed required sponsor gate" in item for item in failures), failures
        )

    def test_rejects_authority_complete_while_q012_is_open(self) -> None:
        value = self._registry()
        entry = next(
            item
            for item in value["providers"]
            if item["provider_id"] == "ACRA_GENERIC_SANDBOX"
        )
        entry["contract_authority_complete"] = True
        self._write_registry(value)
        failures = CHECKER.validate(self.root)
        self.assertTrue(
            any("Q-012 authority complete" in item for item in failures), failures
        )

    def test_rejects_sandbox_access_proof_while_scaffold_is_blocked(self) -> None:
        value = self._registry()
        entry = next(
            item
            for item in value["providers"]
            if item["provider_id"] == "ACRA_GENERIC_SANDBOX"
        )
        entry["authorized_sandbox_access"] = True
        self._write_registry(value)
        failures = CHECKER.validate(self.root)
        self.assertTrue(
            any("authorized_sandbox_access must be false" in item for item in failures),
            failures,
        )

    def test_rejects_secret_delivery_proof_while_goldtier_is_blocked(self) -> None:
        value = self._registry()
        entry = next(
            item
            for item in value["providers"]
            if item["provider_id"] == "GOLDTIER_REAL"
        )
        entry["secret_delivery_ready"] = True
        self._write_registry(value)
        failures = CHECKER.validate(self.root)
        self.assertTrue(
            any("secret_delivery_ready must be false" in item for item in failures),
            failures,
        )

    def test_rejects_goldtier_real_runtime_activation(self) -> None:
        value = self._registry()
        entry = next(
            item
            for item in value["providers"]
            if item["provider_id"] == "GOLDTIER_REAL"
        )
        entry["runtime_activation_enabled"] = True
        self._write_registry(value)
        failures = CHECKER.validate(self.root)
        self.assertTrue(any("GOLDTIER_REAL" in item for item in failures), failures)

    def test_rejects_goldtier_xpi_runtime_deactivation(self) -> None:
        value = self._registry()
        entry = next(
            item for item in value["providers"] if item["provider_id"] == "GOLDTIER_XPI"
        )
        entry["runtime_activation_enabled"] = False
        self._write_registry(value)
        failures = CHECKER.validate(self.root)
        self.assertTrue(
            any("GOLDTIER_XPI runtime_activation_enabled" in item for item in failures),
            failures,
        )

    def test_rejects_live_goldtier_mode_in_settings(self) -> None:
        config = self.root / CHECKER.CONFIG_PATH
        config.write_text(
            config.read_text(encoding="utf-8").replace(
                'goldtier_connector_mode: Literal["mock", "sandbox"] = "mock"',
                'goldtier_connector_mode: Literal["mock", "sandbox", "live"] = "mock"',
            ),
            encoding="utf-8",
        )
        failures = CHECKER.validate(self.root)
        self.assertTrue(any("GoldTier Settings" in item for item in failures), failures)

    def test_rejects_historical_bizfile_mock_alias_in_acra_settings(self) -> None:
        config = self.root / CHECKER.CONFIG_PATH
        config.write_text(
            config.read_text(encoding="utf-8").replace(
                'Literal["mock", "api_marketplace_mock", "sandbox"]',
                'Literal["mock", "api_marketplace_mock", "bizfile_mock", "sandbox"]',
            ),
            encoding="utf-8",
        )

        failures = CHECKER.validate(self.root)

        self.assertTrue(any("ACRA Settings" in item for item in failures), failures)

    def test_rejects_api_marketplace_mock_as_acra_default(self) -> None:
        config = self.root / CHECKER.CONFIG_PATH
        config.write_text(
            config.read_text(encoding="utf-8").replace(
                'acra_connector_mode: Literal["mock", "api_marketplace_mock", "sandbox"] = "mock"',
                'acra_connector_mode: Literal["mock", "api_marketplace_mock", "sandbox"] = "api_marketplace_mock"',
            ),
            encoding="utf-8",
        )

        failures = CHECKER.validate(self.root)

        self.assertTrue(any("ACRA Settings" in item for item in failures), failures)

    def test_rejects_sandbox_as_goldtier_default(self) -> None:
        config = self.root / CHECKER.CONFIG_PATH
        config.write_text(
            config.read_text(encoding="utf-8").replace(
                'goldtier_connector_mode: Literal["mock", "sandbox"] = "mock"',
                'goldtier_connector_mode: Literal["mock", "sandbox"] = "sandbox"',
            ),
            encoding="utf-8",
        )
        failures = CHECKER.validate(self.root)
        self.assertTrue(any("GoldTier Settings" in item for item in failures), failures)

    def test_rejects_local_idp_as_vendor_ocr(self) -> None:
        value = self._registry()
        entry = next(
            item
            for item in value["providers"]
            if item["provider_id"] == "IDP_LOCAL_PDF_TEXT"
        )
        entry["current_classification"] = "PARTIAL"
        self._write_registry(value)
        failures = CHECKER.validate(self.root)
        self.assertTrue(
            any("IDP_LOCAL_PDF_TEXT classification" in item for item in failures),
            failures,
        )

    def test_rejects_runtime_activation_with_incomplete_gate(self) -> None:
        value = self._registry()
        entry = next(
            item
            for item in value["providers"]
            if item["provider_id"] == "ACRA_GENERIC_SANDBOX"
        )
        entry["runtime_activation_enabled"] = True
        self._write_registry(value)
        failures = CHECKER.validate(self.root)
        self.assertTrue(
            any(
                "blocked/scaffold state" in item or "incomplete authority gate" in item
                for item in failures
            ),
            failures,
        )

    def test_rejects_unknown_entry_field(self) -> None:
        value = self._registry()
        value["providers"][0]["secret"] = "must not exist"
        self._write_registry(value)
        failures = CHECKER.validate(self.root)
        self.assertTrue(any("strict schema" in item for item in failures), failures)

    def test_duplicate_key_diagnostics_do_not_echo_untrusted_key(self) -> None:
        canary = "arbitrary" + "?" + "access_" + "token=opaque"
        registry_path = self.root / CHECKER.REGISTRY_PATH
        registry_path.write_text(
            '{"' + canary + '": 1, "' + canary + '": 2}\n',
            encoding="utf-8",
        )
        failures = CHECKER.validate(self.root)
        self.assertTrue(
            any("duplicate JSON key" in item for item in failures), failures
        )
        self.assertNotIn(canary, "\n".join(failures))

        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = CHECKER.main(["--root", str(self.root)])
        self.assertEqual(exit_code, 1)
        self.assertNotIn(canary, output.getvalue())


if __name__ == "__main__":
    unittest.main()
