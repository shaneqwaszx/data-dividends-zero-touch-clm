import { describe, expect, it } from "vitest";
import { governanceFixtures, rawGovernanceFixtures } from "./test-fixtures/workflowGovernance";
import {
  COMPARISON_RESPONSE_KEYS,
  DECISION_RESPONSE_KEYS,
  GOVERNANCE_ERROR_CODES,
  GOVERNANCE_VIEW_KEYS,
  PERMANENT_OBLIGATION_WARNING,
  PROPOSAL_RESPONSE_KEYS,
  VALIDATION_REPORT_KEYS,
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

  it("hands out independent copies", () => {
    const first = governanceFixtures.comparison();
    first.proposal.revision = 999;
    expect(governanceFixtures.comparison().proposal.revision).not.toBe(999);
  });
});
