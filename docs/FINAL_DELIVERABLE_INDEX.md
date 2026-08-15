# Final Deliverable Index

## Start here

- [Project README](../README.md)
- [Sponsor demo runbook](demo/DEMO_RUNBOOK.md)
- [Sponsor demo script](demo/SPONSOR_DEMO_SCRIPT.md)
- [Phase 07 UAT catalogue](uat/PHASE_07_UAT_CATALOGUE.md)

## Architecture and policy

- [Final POC architecture](architecture/FINAL_POC_ARCHITECTURE.md)
- [Zero-touch architecture](architecture/PHASE_06_ZERO_TOUCH_ORCHESTRATION.md)
- [Zero-touch policy](contracts/ZERO_TOUCH_AUTOMATION_POLICY.md)
- [Integration adapter contracts](contracts/INTEGRATION_ADAPTER_CONTRACTS.md)
- [CLM readiness policy](contracts/CLM_READINESS_POLICY.md)

## Integration handoff

- [Integration handoff](integration/INTEGRATION_HANDOFF.md)
- [Provider replacement guide](integration/PROVIDER_REPLACEMENT_GUIDE.md)
- [Adapter conformance checklist](integration/ADAPTER_CONFORMANCE_CHECKLIST.md)
- [API handoff](integration/API_HANDOFF.md)
- [Configuration reference](integration/CONFIGURATION_REFERENCE.md)
- [Failure/recovery guide](integration/FAILURE_RECOVERY_GUIDE.md)
- [POC security boundaries](security/POC_SECURITY_BOUNDARIES.md)

## Sponsor state

- [Phase 07 sponsor dependency matrix](sponsor-questions/PHASE_07_SPONSOR_DEPENDENCY_MATRIX.md)
- [Open questions](sponsor-questions/OPEN_QUESTIONS.md)
- [Decision log](decisions/DECISION_LOG.md)
- [GoldTier baseline](contracts/GOLDTIER_CONTRACT_BASELINE.md)
- [Contract discrepancy catalogue](contracts/GOLDTIER_CONTRACT_DISCREPANCIES.md)

## Verification and gates

- [Phase 06 final quality gate — PASS](../.ai-pipeline/reports/PHASE_06_QUALITY_GATE.md)
- [Phase 07 integration-security review](../.ai-pipeline/reports/PHASE_07_INTEGRATION_SECURITY_REVIEW.md)
- [Phase 07 POC regression](../.ai-pipeline/reports/PHASE_07_POC_REGRESSION.md)
- [Phase 07 remediation report](../.ai-pipeline/reports/PHASE_07_REMEDIATION_REPORT.md)
- [Phase 07 independent quality gate — historical FAIL pending re-gate](../.ai-pipeline/reports/PHASE_07_QUALITY_GATE.md)
- Independent Phase 07 re-gate: still required; implementation-side remediation and
  supporting reviews do not replace the historical FAIL or issue a new gate result.

## Synthetic evidence

- `apps/backend/tests/fixtures/uat/` — clearly marked fictional document pack.
- `apps/backend/tests/test_phase_07_uat.py` — sponsor-observable UAT automation.
- Demo-gated JSON export: `/api/demo/clm/zero-touch/cases/{case_id}/uat-evidence`.
