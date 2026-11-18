import { describe, expect, it } from "vitest";
import proposalConditionalDraft from "../../../docs/contracts/fixtures/workflow-governance/proposal_conditional_draft.json";
import runApplicabilityView from "../../../docs/contracts/fixtures/workflow-governance/run_applicability_view.json";
import { governanceFixtures, rawGovernanceFixtures } from "./test-fixtures/workflowGovernance";
import type { WorkflowStage } from "./workflowApi";
import {
  CONDITIONAL_LEGAL_FORMS,
  COMPARISON_RESPONSE_KEYS,
  DECISION_RESPONSE_KEYS,
  GOVERNANCE_ERROR_CODES,
  GOVERNANCE_VIEW_KEYS,
  PERMANENT_OBLIGATION_WARNING,
  PROPOSAL_RESPONSE_KEYS,
  RUN_APPLICABILITY_VIEW_KEYS,
  VALIDATION_REPORT_KEYS,
  type ProposalResponse,
  type RunApplicabilityView,
} from "./workflowGovernanceTypes";

// The same synthetic fixtures the backend contract test validates against the Pydantic models.
const keys = (value: unknown) => Object.keys(value as object).sort();

describe("workflow governance contract (C0)", () => {
  it("covers every generated fixture", () => {
    expect(Object.keys(rawGovernanceFixtures)).toHaveLength(15);
  });

  it.each([
    ["proposal_draft.json", PROPOSAL_RESPONSE_KEYS],
    ["proposal_pending_director_view.json", PROPOSAL_RESPONSE_KEYS],
    ["comparison.json", COMPARISON_RESPONSE_KEYS],
    ["validation_report_valid.json", VALIDATION_REPORT_KEYS],
    ["validation_report_refused.json", VALIDATION_REPORT_KEYS],
    ["decision_response_approved.json", DECISION_RESPONSE_KEYS],
    ["workflow_governance_view.json", GOVERNANCE_VIEW_KEYS],
  ] as const)("%s has exactly the typed keys", (name, expected) => {
    expect(keys(rawGovernanceFixtures[name])).toEqual([...expected].sort());
  });

  it("nests typed proposals and the fixed warning text", () => {
    const comparison = governanceFixtures.comparison();
    expect(keys(comparison.proposal)).toEqual([...PROPOSAL_RESPONSE_KEYS].sort());
    expect(keys(comparison.validation)).toEqual([...VALIDATION_REPORT_KEYS].sort());
    expect(comparison.permanent_obligation_warning).toBe(PERMANENT_OBLIGATION_WARNING);
  });

  it("uses only frozen error codes", () => {
    for (const body of [
      governanceFixtures.errorRatchetRemoved(),
      governanceFixtures.errorAcknowledgementRequired(),
      governanceFixtures.errorSelfDecision(),
      governanceFixtures.errorHistoryUnavailable(),
    ]) {
      expect(GOVERNANCE_ERROR_CODES).toContain(body.code);
    }
  });

  it("types the CC-8 conditional fixtures (ADR-018)", () => {
    const proposal = proposalConditionalDraft as unknown as ProposalResponse;
    expect(keys(proposal)).toEqual([...PROPOSAL_RESPONSE_KEYS].sort());
    const stage = (proposal as unknown as { stages: WorkflowStage[] }).stages[0];
    expect(stage.applies_to).toEqual(["LLP", "LP"]);
    for (const form of [...(stage.applies_to ?? []), ...stage.fields.flatMap((f) => f.applies_to ?? [])]) {
      expect(CONDITIONAL_LEGAL_FORMS).toContain(form);
    }
    expect(stage.fields[0]).not.toHaveProperty("applies_to");
    const view = runApplicabilityView as unknown as RunApplicabilityView;
    expect(keys(view)).toEqual([...RUN_APPLICABILITY_VIEW_KEYS].sort());
    expect(view.effective_legal_form).toBeNull();
  });

  it("keeps M1 stages unconditional (no applies_to key)", () => {
    const draft = governanceFixtures.proposalDraft() as unknown as { stages: WorkflowStage[] };
    for (const stage of draft.stages) {
      expect(stage).not.toHaveProperty("applies_to");
      for (const field of stage.fields) expect(field).not.toHaveProperty("applies_to");
    }
  });

  it("hands out independent copies", () => {
    const first = governanceFixtures.comparison();
    first.proposal.revision = 999;
    expect(governanceFixtures.comparison().proposal.revision).not.toBe(999);
  });
});
