"""Static Phase 05 API, security, and truthfulness contract checks."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "apps" / "backend" / "app"


class Phase05ClmContractTests(unittest.TestCase):
    def test_staged_and_legacy_paths_share_one_onboarding_implementation(self) -> None:
        source = (BACKEND / "services" / "onboarding.py").read_text(encoding="utf-8")
        self.assertIn("create_staged_case", source)
        self.assertIn("submit_staged_case", source)
        self.assertIn("complete_legacy_flow=True", source)

    def test_clm_runtime_has_no_real_http_or_pingfed_dependency(self) -> None:
        source = (BACKEND / "services" / "clm_orchestration.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("httpx", source)
        self.assertNotIn("PingFed", source)
        self.assertNotIn("Authorization", source)
        self.assertNotIn("create_related_party", source)

    def test_snapshot_model_excludes_raw_evidence_and_credentials(self) -> None:
        clm_source = (BACKEND / "domain" / "clm.py").read_text(encoding="utf-8")
        target_source = (BACKEND / "domain" / "target_submission.py").read_text(
            encoding="utf-8"
        )
        snapshot = clm_source[clm_source.index("class ClmSubmissionSnapshot") :]
        snapshot += target_source
        for prohibited in (
            "pdf_bytes",
            "document_text",
            "raw_acra",
            "raw_ownership",
            "access_token",
            "client_secret",
            "private_endpoint",
        ):
            self.assertNotIn(prohibited, snapshot.lower())

    def test_one_canonical_validator_governs_onboarding_and_clm(self) -> None:
        onboarding = (BACKEND / "services" / "onboarding.py").read_text(
            encoding="utf-8"
        )
        clm = (BACKEND / "services" / "clm_orchestration.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("from app.services.canonical_validation import validate_entity", onboarding)
        self.assertIn("from app.services.canonical_validation import validate_entity", clm)
        self.assertIn("CANONICAL_DATA_INVALID", clm)

    def test_snapshot_target_input_and_execution_receipt_are_bound(self) -> None:
        clm = (BACKEND / "services" / "clm_orchestration.py").read_text(
            encoding="utf-8"
        )
        domain = (BACKEND / "domain" / "clm.py").read_text(encoding="utf-8")
        self.assertIn("execute_submission_input(snapshot.target_input)", clm)
        self.assertIn("execution_receipt: GoldTierExecutionReceipt", domain)
        self.assertIn("input_fingerprint", clm)

    def test_target_outcome_is_retained_before_rich_receipt_mapping(self) -> None:
        onboarding = (BACKEND / "services" / "onboarding.py").read_text(
            encoding="utf-8"
        )
        target = (BACKEND / "domain" / "target_submission.py").read_text(
            encoding="utf-8"
        )
        frontend = (ROOT / "apps/frontend/src/types.ts").read_text(encoding="utf-8")
        self.assertIn("class GoldTierTargetOutcome", target)
        self.assertIn("TARGET_OUTCOME_RECORDED", target)
        self.assertIn("self._record_target_outcome(", onboarding)
        self.assertIn("self._build_execution_receipt(submission_input, outcome)", onboarding)
        self.assertNotIn("GoldTierTargetOutcome", frontend)
        self.assertNotIn("execution_receipt", frontend)

    def test_target_responses_cross_one_bounded_validation_boundary(self) -> None:
        onboarding = (BACKEND / "services" / "onboarding.py").read_text(
            encoding="utf-8"
        )
        validator = (
            BACKEND / "services" / "target_response_validation.py"
        ).read_text(encoding="utf-8")
        safety = (BACKEND / "domain" / "target_safety.py").read_text(
            encoding="utf-8"
        )
        connector = (BACKEND / "connectors" / "goldtier_models.py").read_text(
            encoding="utf-8"
        )
        target = (BACKEND / "domain" / "target_submission.py").read_text(
            encoding="utf-8"
        )
        for validation_call in (
            "validate_search_response(untrusted_search)",
            "validate_shell_response(untrusted_shell)",
            "validate_policy_response(",
            "validate_amend_response(",
        ):
            self.assertIn(validation_call, onboarding)
        self.assertIn('code=MALFORMED_TARGET_RESPONSE_CODE', onboarding)
        self.assertIn("_ensure_execution_owner_exit", onboarding)
        self.assertIn("response_type.model_validate(payload)", validator)
        self.assertIn("max_length=96", safety)
        self.assertIn("max_length=64", safety)
        self.assertIn("max_length=200", safety)
        self.assertIn("SafeTargetIdentifier", connector)
        self.assertIn("SafeTargetIdentifier", target)

    def test_frontend_invalidates_and_refreshes_after_evidence_mutation(self) -> None:
        frontend = (ROOT / "apps/frontend/src/App.tsx").read_text(encoding="utf-8")
        self.assertIn("runEvidenceMutation", frontend)
        self.assertIn("invalidateClmReadiness", frontend)
        self.assertIn("refreshClmSummary", frontend)
        self.assertIn("ClmRefreshingState", frontend)

    def test_frontend_cannot_control_readiness(self) -> None:
        main = (BACKEND / "main.py").read_text(encoding="utf-8")
        self.assertIn('/readiness/evaluate"', main)
        self.assertNotIn("readiness: ClmReadinessAssessment", main)


if __name__ == "__main__":
    unittest.main()
