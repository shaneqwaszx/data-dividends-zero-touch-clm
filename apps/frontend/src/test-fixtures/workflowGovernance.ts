// The shared synthetic workflow-governance fixtures (C0), generated from the backend models by
// scripts/generate_workflow_governance_fixtures.py and validated by both contract tests.
// Static JSON imports keep the browser tsconfig free of Node ambient types.

import approvalsInbox from "../../../../docs/contracts/fixtures/workflow-governance/approvals_inbox.json";
import comparison from "../../../../docs/contracts/fixtures/workflow-governance/comparison.json";
import decisionRequestApprove from "../../../../docs/contracts/fixtures/workflow-governance/decision_request_approve.json";
import decisionResponseApproved from "../../../../docs/contracts/fixtures/workflow-governance/decision_response_approved.json";
import errorAcknowledgementRequired from "../../../../docs/contracts/fixtures/workflow-governance/error_acknowledgement_required.json";
import errorHistoryUnavailable from "../../../../docs/contracts/fixtures/workflow-governance/error_history_unavailable.json";
import errorRatchetRemoved from "../../../../docs/contracts/fixtures/workflow-governance/error_ratchet_removed.json";
import errorSelfDecision from "../../../../docs/contracts/fixtures/workflow-governance/error_self_decision.json";
import proposalDraft from "../../../../docs/contracts/fixtures/workflow-governance/proposal_draft.json";
import proposalPendingDirectorView from "../../../../docs/contracts/fixtures/workflow-governance/proposal_pending_director_view.json";
import simulationResult from "../../../../docs/contracts/fixtures/workflow-governance/simulation_result.json";
import simulationScenarios from "../../../../docs/contracts/fixtures/workflow-governance/simulation_scenarios.json";
import validationReportRefused from "../../../../docs/contracts/fixtures/workflow-governance/validation_report_refused.json";
import validationReportValid from "../../../../docs/contracts/fixtures/workflow-governance/validation_report_valid.json";
import workflowGovernanceView from "../../../../docs/contracts/fixtures/workflow-governance/workflow_governance_view.json";
import type {
  ApprovalInboxResponse,
  ComparisonResponse,
  DecisionRequest,
  DecisionResponse,
  GovernanceErrorBody,
  ProposalResponse,
  SimulationResult,
  SimulationScenario,
  ValidationReport,
  WorkflowGovernanceView,
} from "../workflowGovernanceTypes";

// Returns a fresh deep copy each call, so a test can never mutate another test's fixture.
const copy = <T>(value: unknown): T => structuredClone(value) as T;

export const governanceFixtures = {
  approvalsInbox: () => copy<ApprovalInboxResponse>(approvalsInbox),
  comparison: () => copy<ComparisonResponse>(comparison),
  decisionRequestApprove: () => copy<DecisionRequest>(decisionRequestApprove),
  decisionResponseApproved: () => copy<DecisionResponse>(decisionResponseApproved),
  errorAcknowledgementRequired: () => copy<GovernanceErrorBody>(errorAcknowledgementRequired),
  errorHistoryUnavailable: () => copy<GovernanceErrorBody>(errorHistoryUnavailable),
  errorRatchetRemoved: () => copy<GovernanceErrorBody>(errorRatchetRemoved),
  errorSelfDecision: () => copy<GovernanceErrorBody>(errorSelfDecision),
  proposalDraft: () => copy<ProposalResponse>(proposalDraft),
  proposalPendingDirectorView: () => copy<ProposalResponse>(proposalPendingDirectorView),
  simulationResult: () => copy<SimulationResult>(simulationResult),
  simulationScenarios: () => copy<SimulationScenario[]>(simulationScenarios),
  validationReportRefused: () => copy<ValidationReport>(validationReportRefused),
  validationReportValid: () => copy<ValidationReport>(validationReportValid),
  workflowGovernanceView: () => copy<WorkflowGovernanceView>(workflowGovernanceView),
};

// The raw JSON, for exact key-set checks.
export const rawGovernanceFixtures: Record<string, unknown> = {
  "approvals_inbox.json": approvalsInbox,
  "comparison.json": comparison,
  "decision_request_approve.json": decisionRequestApprove,
  "decision_response_approved.json": decisionResponseApproved,
  "error_acknowledgement_required.json": errorAcknowledgementRequired,
  "error_history_unavailable.json": errorHistoryUnavailable,
  "error_ratchet_removed.json": errorRatchetRemoved,
  "error_self_decision.json": errorSelfDecision,
  "proposal_draft.json": proposalDraft,
  "proposal_pending_director_view.json": proposalPendingDirectorView,
  "simulation_result.json": simulationResult,
  "simulation_scenarios.json": simulationScenarios,
  "validation_report_refused.json": validationReportRefused,
  "validation_report_valid.json": validationReportValid,
  "workflow_governance_view.json": workflowGovernanceView,
};
