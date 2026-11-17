import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import {
  COMPARISON_RESPONSE_KEYS,
  DECISION_RESPONSE_KEYS,
  GOVERNANCE_ERROR_CODES,
  GOVERNANCE_VIEW_KEYS,
  PERMANENT_OBLIGATION_WARNING,
  PROPOSAL_RESPONSE_KEYS,
  VALIDATION_REPORT_KEYS,
  type ComparisonResponse,
} from "./workflowGovernanceTypes";

// The same synthetic fixtures the backend contract test validates against the Pydantic models.
const FIXTURES = resolve(__dirname, "../../../docs/contracts/fixtures/workflow-governance");
const load = (name: string): Record<string, unknown> =>
  JSON.parse(readFileSync(resolve(FIXTURES, name), "utf-8")) as Record<string, unknown>;
const keys = (value: unknown) => Object.keys(value as object).sort();

describe("workflow governance contract (C0)", () => {
  it.each([
    ["proposal_draft.json", PROPOSAL_RESPONSE_KEYS],
    ["proposal_pending_director_view.json", PROPOSAL_RESPONSE_KEYS],
    ["comparison.json", COMPARISON_RESPONSE_KEYS],
    ["validation_report_valid.json", VALIDATION_REPORT_KEYS],
    ["validation_report_refused.json", VALIDATION_REPORT_KEYS],
    ["decision_response_approved.json", DECISION_RESPONSE_KEYS],
    ["workflow_governance_view.json", GOVERNANCE_VIEW_KEYS],
  ] as const)("%s has exactly the typed keys", (name, expected) => {
    expect(keys(load(name))).toEqual([...expected].sort());
  });

  it("nests typed proposals and the fixed warning text", () => {
    const comparison = load("comparison.json") as unknown as ComparisonResponse;
    expect(keys(comparison.proposal)).toEqual([...PROPOSAL_RESPONSE_KEYS].sort());
    expect(keys(comparison.validation)).toEqual([...VALIDATION_REPORT_KEYS].sort());
    expect(comparison.permanent_obligation_warning).toBe(PERMANENT_OBLIGATION_WARNING);
  });

  it("uses only frozen error codes", () => {
    for (const name of [
      "error_ratchet_removed.json",
      "error_acknowledgement_required.json",
      "error_self_decision.json",
      "error_history_unavailable.json",
    ]) {
      expect(GOVERNANCE_ERROR_CODES).toContain(load(name).code);
    }
  });
});
