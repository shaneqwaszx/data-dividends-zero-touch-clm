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

    # The AI assistant's credential names (D-091, proposed). Names and key-shaped values are
    # assembled at run time so this file itself holds no assignment or key-shaped literal.
    REMOTE = "OPENROUTER_" + "API_KEY"
    LOCAL = "AI_ASSISTANT_LLM_" + "API_KEY"

    def test_detects_assistant_credential_assignments_in_every_form(self) -> None:
        fake_value = "fixture_not_a_real_value_" + "778899"
        for name in (self.REMOTE, self.LOCAL):
            lines = [
                f"{name}={fake_value}",
                f"export {name}={fake_value}",
                f"set {name}={fake_value}",
                f'$env:{name} = "{fake_value}"',
                f"{name}: {fake_value}",
                f'  {name}: "{fake_value}"',
                f'{{"{name}": "{fake_value}"}}',
            ]
            path = self._temporary_file("credentials.txt", "\n".join(lines))

            findings = CHECK_SECRETS.scan_file(path)

            self.assertEqual(sorted(line for _, line in findings), list(range(1, 8)), name)
            self.assertNotIn(fake_value, repr(findings))

    def test_detects_an_openrouter_shaped_key_without_a_name(self) -> None:
        key_shaped = "sk-" + "or-" + "v1-" + "0" * 64
        path = self._temporary_file("notes.md", f"pasted by mistake: {key_shaped}\n")

        findings = CHECK_SECRETS.scan_file(path)

        self.assertEqual(findings, [("openrouter-key", 1)])
        self.assertNotIn(key_shaped, repr(findings))

    def test_allows_documented_credential_placeholders_and_references(self) -> None:
        lines = [
            f"{self.REMOTE}=",
            f"{self.REMOTE}=<credential>",
            f"{self.REMOTE}=${{{self.REMOTE}}}",
            f"{self.REMOTE}=%{self.REMOTE}%",
            f"{self.REMOTE}=test_sentinel_value",
            f"{self.LOCAL}=ollama",
            f"The {self.REMOTE} variable is read from the process environment only.",
            f"| `{self.REMOTE}` | process environment |",
        ]
        path = self._temporary_file("example.env", "\n".join(lines))

        self.assertEqual(CHECK_SECRETS.scan_file(path), [])

    def test_the_local_placeholder_is_accepted_only_for_its_own_variable(self) -> None:
        path = self._temporary_file("example.env", f"{self.REMOTE}=ollama\n")

        self.assertEqual(CHECK_SECRETS.scan_file(path), [("assistant-credential-assignment", 1)])

    def test_allows_runtime_credential_references_in_source_code(self) -> None:
        lines = [
            f"{self.REMOTE} = settings.remote_key",
            f'environ = {{"{self.REMOTE}": SENTINEL}}',
            f'CREDENTIAL_VARIABLE = "{self.REMOTE}"',
        ]
        path = self._temporary_file("factory.py", "\n".join(lines))

        self.assertEqual(CHECK_SECRETS.scan_file(path), [])

    def test_detects_a_literal_credential_in_source_code(self) -> None:
        fake_value = "fixture_not_a_real_value_" + "445566"
        path = self._temporary_file("factory.py", f'environ = {{"{self.REMOTE}": "{fake_value}"}}')

        self.assertEqual(CHECK_SECRETS.scan_file(path), [("assistant-credential-mapping", 1)])

    def test_bearer_placeholders_in_documentation_are_not_findings(self) -> None:
        header = "Author" + "ization: Bearer "
        path = self._temporary_file(
            "guide.md", f"| Headers | `{header}<key>`, JSON |\nSend `{header}<credential>`.\n"
        )

        self.assertEqual(CHECK_SECRETS.scan_file(path), [])

    def test_a_real_looking_bearer_value_is_still_a_finding(self) -> None:
        fake_value = "fixture_not_a_real_bearer_" + "998877"
        path = self._temporary_file("guide.md", f"`{'Author' + 'ization: Bearer '}{fake_value}`,\n")

        self.assertEqual(CHECK_SECRETS.scan_file(path), [("bearer-authorization", 1)])

    def test_detects_a_literal_credential_assigned_through_a_subscript(self) -> None:
        """QG F-5 (a): the os.environ / mapping subscript form in source code."""

        fake_value = "fixture_not_a_real_value_" + "667788"
        lines = [
            f'os.environ["{self.REMOTE}"] = "{fake_value}"',
            f"settings['{self.LOCAL}'] = '{fake_value}'",
        ]
        path = self._temporary_file("setup_env.py", "\n".join(lines))

        findings = CHECK_SECRETS.scan_file(path)

        self.assertEqual(findings, [("assistant-credential-subscript", 1), ("assistant-credential-subscript", 2)])
        self.assertNotIn(fake_value, repr(findings))

    def test_allows_runtime_references_through_a_subscript(self) -> None:
        lines = [
            f'os.environ["{self.REMOTE}"] = settings.remote_key',
            f'value = os.environ["{self.REMOTE}"]',
        ]
        path = self._temporary_file("setup_env.py", "\n".join(lines))

        self.assertEqual(CHECK_SECRETS.scan_file(path), [])

    def test_allows_angle_placeholders_that_contain_spaces(self) -> None:
        """QG F-5 (b): a documented placeholder such as <your key> is not a finding."""

        lines = [
            f"{self.REMOTE}=<your key>",
            f'{self.REMOTE}: "<paste the key here>"',
            f'os.environ["{self.REMOTE}"] = "<your key>"',
        ]
        path = self._temporary_file("example.env", "\n".join(lines))

        self.assertEqual(CHECK_SECRETS.scan_file(path), [])

    def test_main_never_prints_an_assistant_credential_value(self) -> None:
        fake_value = "fixture_not_a_real_value_" + "112233"
        path = self._temporary_file("local.env", f"{self.REMOTE}={fake_value}\n")
        output = io.StringIO()

        with (
            patch.object(CHECK_SECRETS, "candidate_files", return_value=[path]),
            redirect_stdout(output),
        ):
            result = CHECK_SECRETS.main()

        self.assertEqual(result, 1)
        self.assertNotIn(fake_value, output.getvalue())
        self.assertIn("[assistant-credential-assignment]", output.getvalue())


if __name__ == "__main__":
    unittest.main()
