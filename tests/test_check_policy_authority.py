from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "check_policy_authority.py"
SPEC = importlib.util.spec_from_file_location("check_policy_authority_under_test", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load check_policy_authority")
CHECK = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CHECK
SPEC.loader.exec_module(CHECK)


class PolicyAuthorityCheckerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = json.loads((ROOT / CHECK.REGISTRY_PATH).read_text(encoding="utf-8"))
        cls.questions = (ROOT / CHECK.QUESTIONS_PATH).read_text(encoding="utf-8")

    def _fixture(self, registry: dict[str, object]) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "tmp")
        root = Path(temporary.name)
        registry_path = root / CHECK.REGISTRY_PATH
        registry_path.parent.mkdir(parents=True)
        registry_path.write_text(json.dumps(registry), encoding="utf-8")
        questions_path = root / CHECK.QUESTIONS_PATH
        questions_path.parent.mkdir(parents=True)
        questions_path.write_text(self.questions, encoding="utf-8")
        for relative_path in CHECK.GOVERNED_DOCS:
            source = ROOT / relative_path
            destination = root / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        return temporary, root

    def _mutate(self, policy_id: str, **changes: object) -> list[str]:
        registry = copy.deepcopy(self.registry)
        policies = registry["policies"]
        assert isinstance(policies, list)
        entry = next(item for item in policies if item["policy_id"] == policy_id)
        entry.update(changes)
        temporary, root = self._fixture(registry)
        try:
            return CHECK.validate(root)
        finally:
            temporary.cleanup()

    def test_current_repository_registry_passes(self) -> None:
        self.assertEqual(CHECK.validate(ROOT), [])

    def test_rejects_provisional_runtime_activation(self) -> None:
        failures = self._mutate("PRIORITY_VOCABULARY_AND_ORDER", runtime_enabled=True)
        self.assertTrue(any("cannot enable provisional" in item for item in failures))

    def test_rejects_unresolved_risk_as_sponsor_confirmed(self) -> None:
        failures = self._mutate(
            "SUPPLIED_RISK_INPUT_AND_WORKFLOW", authority_status="SPONSOR_CONFIRMED"
        )
        self.assertTrue(any("Q-017 is open" in item for item in failures))

    def test_rejects_ready_for_approval_activation_while_q001_is_open(self) -> None:
        failures = self._mutate(
            "READY_FOR_APPROVAL_TRANSITION",
            authority_status="SPONSOR_CONFIRMED",
            runtime_enabled=True,
        )
        self.assertTrue(any("Q-001 is open" in item for item in failures))

    def test_rejects_removing_required_review_question_gate(self) -> None:
        failures = self._mutate("REVIEW_AUTHORITY", blocking_sponsor_question=None)
        self.assertIn("REVIEW_AUTHORITY must remain blocked by Q-014", failures)

    def test_rejects_q003_document_scope_blocker_removal_and_activation(self) -> None:
        failures = self._mutate(
            "DOCUMENT_SCOPE",
            blocking_sponsor_question=None,
            authority_status="SPONSOR_CONFIRMED",
            runtime_enabled=True,
        )
        self.assertIn("DOCUMENT_SCOPE must remain blocked by Q-003", failures)

    def test_rejects_q004_ubo_blocker_removal_and_activation(self) -> None:
        failures = self._mutate(
            "FINAL_LEGAL_UBO_RULE",
            blocking_sponsor_question=None,
            authority_status="SPONSOR_CONFIRMED",
            runtime_enabled=True,
        )
        self.assertIn("FINAL_LEGAL_UBO_RULE must remain blocked by Q-004", failures)

    def test_rejects_q005_validation_blocker_removal_and_activation(self) -> None:
        failures = self._mutate(
            "VALIDATION_RESPONSIBILITY_SPLIT",
            blocking_sponsor_question=None,
            authority_status="SPONSOR_CONFIRMED",
            runtime_enabled=True,
        )
        self.assertIn(
            "VALIDATION_RESPONSIBILITY_SPLIT must remain blocked by Q-005", failures
        )

    def test_rejects_missing_required_policy(self) -> None:
        registry = copy.deepcopy(self.registry)
        policies = registry["policies"]
        assert isinstance(policies, list)
        registry["policies"] = [
            item for item in policies if item["policy_id"] != "PRODUCTION_IDENTITY_AND_RBAC"
        ]
        temporary, root = self._fixture(registry)
        try:
            failures = CHECK.validate(root)
        finally:
            temporary.cleanup()
        self.assertTrue(any("Missing required policy gates" in item for item in failures))

    def test_rejects_duplicate_policy_identifier(self) -> None:
        registry = copy.deepcopy(self.registry)
        policies = registry["policies"]
        assert isinstance(policies, list)
        policies.append(copy.deepcopy(policies[0]))
        temporary, root = self._fixture(registry)
        try:
            failures = CHECK.validate(root)
        finally:
            temporary.cleanup()
        self.assertTrue(any("Duplicate policy_id" in item for item in failures))

    def test_rejects_unsupported_status_and_extra_fields(self) -> None:
        registry = copy.deepcopy(self.registry)
        policies = registry["policies"]
        assert isinstance(policies, list)
        policies[0]["authority_status"] = "LIKELY_CONFIRMED"
        policies[0]["note"] = "not allowed"
        temporary, root = self._fixture(registry)
        try:
            failures = CHECK.validate(root)
        finally:
            temporary.cleanup()
        self.assertTrue(any("strict schema" in item for item in failures))

    def test_rejects_false_ready_for_approval_prose_claim(self) -> None:
        registry = copy.deepcopy(self.registry)
        temporary, root = self._fixture(registry)
        try:
            matrix = root / "docs/contracts/POLICY_AUTHORITY_MATRIX.md"
            matrix.write_text(
                matrix.read_text(encoding="utf-8")
                + "\nMOCK_GOLDTIER_SUBMITTED is Ready-for-Approval.\n",
                encoding="utf-8",
            )
            failures = CHECK.validate(root)
        finally:
            temporary.cleanup()
        self.assertTrue(any("Ready-for-Approval or approval" in item for item in failures))

    def test_rejects_false_production_role_and_mock_live_claims(self) -> None:
        registry = copy.deepcopy(self.registry)
        temporary, root = self._fixture(registry)
        try:
            packet = root / "docs/sponsor-questions/PHASE_20_POLICY_DECISION_PACKET.md"
            packet.write_text(
                packet.read_text(encoding="utf-8")
                + "\nCurrent local roles are production RBAC. Mock GoldTier is Live.\n",
                encoding="utf-8",
            )
            failures = CHECK.validate(root)
        finally:
            temporary.cleanup()
        self.assertTrue(any("local roles" in item for item in failures))
        self.assertTrue(any("Mock GoldTier" in item for item in failures))

    def test_rejects_stale_policy_and_activity_contract_claims(self) -> None:
        registry = copy.deepcopy(self.registry)
        temporary, root = self._fixture(registry)
        try:
            policy_profile = root / "docs/contracts/POLICY_TEAM_IDENTITY_ADMIN_PROFILE.md"
            policy_profile.write_text(
                policy_profile.read_text(encoding="utf-8").replace(
                    "The current catalogue has 39 seed rules",
                    "The eight seed rules are:",
                ),
                encoding="utf-8",
            )
            activity_profile = root / "docs/contracts/CASE_ACTIVITY_QUERY_PROFILE.md"
            activity_profile.write_text(
                activity_profile.read_text(encoding="utf-8").replace(
                    "Supported case envelopes v1-v5 remain readable without rewrite.",
                    "Supported case envelopes v1-v4 remain readable without rewrite.",
                ),
                encoding="utf-8",
            )
            failures = CHECK.validate(root)
        finally:
            temporary.cleanup()
        self.assertTrue(any("39-rule policy catalogue" in item for item in failures))
        self.assertTrue(any("schema-v5 activity" in item for item in failures))


if __name__ == "__main__":
    unittest.main()
