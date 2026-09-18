from __future__ import annotations

import importlib.util
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "check_secrets.py"
SPEC = importlib.util.spec_from_file_location("check_secrets_under_test", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load the secret scanner")
CHECK_SECRETS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CHECK_SECRETS
SPEC.loader.exec_module(CHECK_SECRETS)


class SecretScannerTests(unittest.TestCase):
    fixture_directory = ROOT / "tmp" / "secret-scanner-tests"

    def setUp(self) -> None:
        self.fixture_directory.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        for path in self.fixture_directory.iterdir():
            path.unlink()
        self.fixture_directory.rmdir()

    def _temporary_file(self, name: str, contents: str = "") -> Path:
        path = self.fixture_directory / name
        path.write_text(contents, encoding="utf-8")
        return path

    def test_detects_safe_fake_assignment_without_returning_value(self) -> None:
        fake_value = "fixture_not_a_real_value_123456"
        path = self._temporary_file("settings.txt", "client_" + "secret=" + fake_value)

        findings = CHECK_SECRETS.scan_file(path)

        self.assertEqual(findings, [("sensitive-assignment", 1)])
        self.assertNotIn(fake_value, repr(findings))

    def test_detects_safe_fake_bearer_without_returning_value(self) -> None:
        fake_value = "fixture_not_a_real_bearer_123456"
        path = self._temporary_file(
            "request.txt", "Author" + "ization: Bearer " + fake_value
        )

        findings = CHECK_SECRETS.scan_file(path)

        self.assertEqual(findings, [("bearer-authorization", 1)])
        self.assertNotIn(fake_value, repr(findings))

    def test_allows_explicit_placeholders(self) -> None:
        path = self._temporary_file("example.env", "client_" + "secret=<redacted>")

        self.assertEqual(CHECK_SECRETS.scan_file(path), [])

    def test_allows_runtime_sensitive_field_forwarding_in_source_code(self) -> None:
        path = self._temporary_file(
            "handler.py", "pass" + "word = request.password\npass" + "word: str\n"
        )

        self.assertEqual(CHECK_SECRETS.scan_file(path), [])

    def test_detects_literal_password_assignment(self) -> None:
        path = self._temporary_file(
            "settings.py", "pass" + "word = \"literal_not_allowed\"\n"
        )

        self.assertEqual(CHECK_SECRETS.scan_file(path), [("sensitive-assignment", 1)])

    def test_detects_credential_bearing_connection_uri(self) -> None:
        path = self._temporary_file(
            "settings.txt",
            "connection_uri=" + "mongo" + "db://user:credential@host/database\n",
        )

        self.assertEqual(CHECK_SECRETS.scan_file(path), [("credential-uri", 1)])

    def test_flags_sensitive_certificate_or_keystore_file_type(self) -> None:
        path = self._temporary_file("safe-fake.jks")

        self.assertEqual(CHECK_SECRETS.scan_file(path), [("sensitive-file-type", 0)])

    def test_main_suppresses_matched_value_in_output(self) -> None:
        fake_value = "fixture_not_a_real_value_654321"
        path = self._temporary_file("local.txt", "api_" + "key=" + fake_value)
        output = io.StringIO()

        with (
            patch.object(CHECK_SECRETS, "candidate_files", return_value=[path]),
            redirect_stdout(output),
        ):
            result = CHECK_SECRETS.main()

        self.assertEqual(result, 1)
        self.assertNotIn(fake_value, output.getvalue())
        self.assertIn("[sensitive-assignment]", output.getvalue())


if __name__ == "__main__":
    unittest.main()
