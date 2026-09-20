from __future__ import annotations

import importlib.util
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "check_tooling_config.py"
SPEC = importlib.util.spec_from_file_location("check_tooling_config_under_test", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load check_tooling_config")
CHECKER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CHECKER
SPEC.loader.exec_module(CHECKER)

CONFIG_PATH = ROOT / ".codex" / "config.toml"


class ToolingConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = CONFIG_PATH.read_text(encoding="utf-8")

    def test_current_project_configuration_passes(self) -> None:
        self.assertEqual(CHECKER.validate_text(self.text), [])

    def test_malformed_toml_fails_closed(self) -> None:
        errors = CHECKER.validate_text(self.text + "\n[broken\n")
        self.assertTrue(any("valid TOML" in error for error in errors))

    def test_wrong_types_and_required_startup_fail(self) -> None:
        changed = self.text.replace("required = false", 'required = "false"', 1)
        errors = CHECKER.validate_text(changed)
        self.assertTrue(any("required" in error for error in errors))

    def test_docs_endpoint_and_tool_expansion_fail(self) -> None:
        changed = self.text.replace(
            'url = "https://camunda-docs.mcp.kapa.ai"',
            'url = "https://unapproved.example/mcp"',
        ).replace(
            'enabled_tools = ["search_camunda_knowledge_sources"]',
            'enabled_tools = ["search_camunda_knowledge_sources", "writeSomething"]',
        )
        errors = CHECKER.validate_text(changed)
        self.assertTrue(any("endpoint" in error for error in errors))
        self.assertTrue(any("enabled_tools" in error for error in errors))

    def test_cluster_activation_or_command_drift_fails(self) -> None:
        changed = self.text.replace(
            '[mcp_servers.camunda_cluster]\ncommand = "c8"',
            '[mcp_servers.camunda_cluster]\ncommand = "npx"',
        ).replace(
            'command = "npx"\nargs = ["mcp-proxy", "--profile", "fyp-camunda"]\nenabled = false',
            'command = "npx"\nargs = ["mcp-proxy", "--profile", "fyp-camunda"]\nenabled = true',
        )
        errors = CHECKER.validate_text(changed)
        self.assertTrue(any("command" in error for error in errors))
        self.assertTrue(any("enabled" in error for error in errors))

    def test_secret_or_environment_forwarding_fields_fail(self) -> None:
        changed = self.text.replace(
            'tool_timeout_sec = 30',
            'tool_timeout_sec = 30\nenv = { CAMUNDA_CLIENT_SECRET = "placeholder" }',
        )
        errors = CHECKER.validate_text(changed)
        self.assertTrue(any("unapproved keys" in error for error in errors))

    def test_missing_or_hidden_per_tool_prompt_fails(self) -> None:
        missing = self.text.replace(
            "\n[mcp_servers.camunda_cluster.tools.getTopology]\napproval_mode = \"prompt\"\n",
            "\n",
        )
        auto = self.text.replace(
            '[mcp_servers.camunda_docs.tools.search_camunda_knowledge_sources]\napproval_mode = "prompt"',
            '[mcp_servers.camunda_docs.tools.search_camunda_knowledge_sources]\napproval_mode = "auto"',
        )
        self.assertTrue(any("approved tools" in error for error in CHECKER.validate_text(missing)))
        self.assertTrue(any("prompt approval" in error for error in CHECKER.validate_text(auto)))

    def test_extra_top_level_configuration_fails(self) -> None:
        changed = self.text.replace(
            f"{CHECKER.SCHEMA_COMMENT}\n",
            f'{CHECKER.SCHEMA_COMMENT}\nmodel = "gpt-example"\n',
            1,
        )
        errors = CHECKER.validate_text(changed)
        self.assertTrue(any("top-level" in error for error in errors))

    def test_ci_retains_existing_jobs_and_wires_new_checks(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        jobs_section = workflow.split("\njobs:\n", maxsplit=1)[1]
        jobs = set(re.findall(r"^  ([a-z0-9-]+):$", jobs_section, flags=re.MULTILINE))
        self.assertEqual(
            jobs,
            {"backend", "frontend", "phase12-mongo", "e2e", "demo-lifecycle-windows", "security"},
        )
        for command in (
            "npm run e2e:list",
            "python ../../scripts/run_physical_mongo_tests.py",
            "python scripts/run_e2e.py",
            "python scripts/check_tooling_config.py",
        ):
            self.assertIn(command, workflow)

    def test_pre_pr_checker_owns_project_tooling_validation(self) -> None:
        checker = (ROOT / "scripts" / "pre_pr_check.py").read_text(encoding="utf-8")
        self.assertIn('_run_governance_check(root, report, "check_tooling_config.py")', checker)


if __name__ == "__main__":
    unittest.main()
