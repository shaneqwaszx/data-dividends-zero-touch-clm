import { describe, expect, it } from "vitest";

import { isWaitingForEarlierSteps } from "./stageDisplay";
import type { ProcessingNode, ZeroTouchCaseSummary } from "./types";

function node(overrides: Partial<ProcessingNode> = {}): ProcessingNode {
  return { node_id: "OWNERSHIP_UBO", label: "Ownership & UBO", status: "BLOCKED", backend_stage: "OWNERSHIP", blocker_code: null, children: [], ...overrides };
}

/** A case at the Document stage waiting for uploads: Registry and Search are complete. */
function summary(overrides: Record<string, unknown> = {}): ZeroTouchCaseSummary {
  return {
    status: "PENDING_INPUTS",
    current_stage: "DOCUMENT",
    completed_stages: ["REGISTRY", "GOLDTIER_SEARCH"],
    active_exceptions: [],
    interventions: [],
    technical_failure: null,
    stage_order_version: 2,
    processing_pipeline: [],
    clm: { readiness: { blockers: ["DOCUMENT_REQUIRED", "OWNERSHIP_REQUIRED"] } },
    ...overrides,
  } as unknown as ZeroTouchCaseSummary;
}

function exception(stage: string, blocker_code = "DOCUMENT_LOW_CONFIDENCE", blocker_codes: string[] = [blocker_code]) {
  return { exception_id: `ex-${stage}`, stage, status: "OPEN", blocker_code, blocker_codes, exception_type: "DOCUMENT_LOW_CONFIDENCE" };
}

function intervention(owning_stage: string, blocker_code = "DOCUMENT_LOW_CONFIDENCE") {
  return { owning_stage, owning_stage_label: owning_stage, blocker_code, expected_next_step: "Review" };
}

describe("isWaitingForEarlierSteps", () => {
  it("treats a later backend-BLOCKED stage with no reason of its own as waiting", () => {
    expect(isWaitingForEarlierSteps(node(), summary())).toBe(true);
  });

  it("treats a later stage blocked only by an earlier stage's prerequisite code as waiting", () => {
    for (const [code, stage] of [["DOCUMENT_REQUIRED", "READINESS"], ["OWNERSHIP_REQUIRED", "READINESS"], ["DOCUMENT_PROCESSING", "MOCK_GOLDTIER"], ["GOVERNMENT_STATUS_REQUIRED", "READINESS"]] as const) {
      expect(isWaitingForEarlierSteps(node({ node_id: "READINESS", backend_stage: stage, blocker_code: code }), summary())).toBe(true);
    }
  });

  it("keeps a stage blocked when the stage is current or already passed", () => {
    expect(isWaitingForEarlierSteps(node({ node_id: "DOCUMENT_IDP", backend_stage: "DOCUMENT" }), summary())).toBe(false);
    expect(isWaitingForEarlierSteps(node({ node_id: "ACRA_REGISTRY", backend_stage: "REGISTRY" }), summary())).toBe(false);
  });

  it("only reinterprets BLOCKED; every other backend status is shown as reported", () => {
    for (const status of ["REVIEW_REQUIRED", "FAILED", "IN_PROGRESS", "NOT_REACHED", "COMPLETE", "UNSUPPORTED"] as const) {
      expect(isWaitingForEarlierSteps(node({ status }), summary())).toBe(false);
    }
  });

  describe("earlier-stage blockers", () => {
    it("lets a later stage wait while an exception is open on an earlier stage", () => {
      const reviewAtDocument = summary({ status: "WAITING_FOR_REVIEW", active_exceptions: [exception("DOCUMENT")], interventions: [intervention("DOCUMENT")] });
      expect(isWaitingForEarlierSteps(node(), reviewAtDocument)).toBe(true);
      // The earlier blocker itself is never reinterpreted.
      expect(isWaitingForEarlierSteps(node({ node_id: "DOCUMENT_IDP", backend_stage: "DOCUMENT", blocker_code: "DOCUMENT_LOW_CONFIDENCE" }), reviewAtDocument)).toBe(false);
    });

    it("keeps a later stage blocked when it carries the same blocker code as the open exception", () => {
      const open = summary({ status: "WAITING_FOR_REVIEW", active_exceptions: [exception("DOCUMENT", "DOCUMENT_REQUIRED")] });
      expect(isWaitingForEarlierSteps(node({ node_id: "READINESS", backend_stage: "READINESS", blocker_code: "DOCUMENT_REQUIRED" }), open)).toBe(false);
      const listed = summary({ status: "WAITING_FOR_REVIEW", active_exceptions: [exception("DOCUMENT", "OTHER", ["OTHER", "DOCUMENT_REQUIRED"])] });
      expect(isWaitingForEarlierSteps(node({ node_id: "READINESS", backend_stage: "READINESS", blocker_code: "DOCUMENT_REQUIRED" }), listed)).toBe(false);
    });

    it("keeps a later stage blocked when an earlier intervention names its blocker code", () => {
      const withAction = summary({ interventions: [intervention("DOCUMENT", "DOCUMENT_REQUIRED")] });
      expect(isWaitingForEarlierSteps(node({ node_id: "READINESS", backend_stage: "READINESS", blocker_code: "DOCUMENT_REQUIRED" }), withAction)).toBe(false);
    });
  });

  describe("never hides an RM action", () => {
    it("keeps the stage blocked when an exception is open on that stage or a later one", () => {
      expect(isWaitingForEarlierSteps(node(), summary({ active_exceptions: [exception("OWNERSHIP")] }))).toBe(false);
      expect(isWaitingForEarlierSteps(node(), summary({ active_exceptions: [exception("READINESS")] }))).toBe(false);
    });

    it("keeps the stage blocked when an intervention is owned by that stage or a later one", () => {
      expect(isWaitingForEarlierSteps(node(), summary({ interventions: [intervention("OWNERSHIP")] }))).toBe(false);
      expect(isWaitingForEarlierSteps(node(), summary({ interventions: [intervention("MOCK_GOLDTIER")] }))).toBe(false);
    });

    it("keeps the stage blocked when its own reason is not an earlier prerequisite", () => {
      for (const code of ["GOLDTIER_CLASSIFICATION_REQUIRED", "DOCUMENT_PROCESSING_FAILED", "OWNERSHIP_ANALYSIS_FAILED", "GOLDTIER_SEARCH_STALE", "CANONICAL_DATA_INVALID", "UNKNOWN_CODE"]) {
        expect(isWaitingForEarlierSteps(node({ node_id: "READINESS", backend_stage: "READINESS", blocker_code: code }), summary())).toBe(false);
      }
      // A prerequisite code owned by the stage itself is that stage's own blocker.
      expect(isWaitingForEarlierSteps(node({ blocker_code: "OWNERSHIP_REQUIRED" }), summary())).toBe(false);
    });

    it("keeps a readiness-derived stage blocked when any retained readiness blocker is not an earlier prerequisite", () => {
      // The node carries only the first readiness blocker; a later classification code must still count.
      const withClassification = summary({ clm: { readiness: { blockers: ["DOCUMENT_REQUIRED", "GOLDTIER_CLASSIFICATION_REQUIRED"] } } });
      for (const [id, stage] of [["READINESS", "READINESS"], ["GOLDTIER_TARGET", "READINESS"], ["FINAL_REVIEW_SEND", "MOCK_GOLDTIER"]] as const) {
        expect(isWaitingForEarlierSteps(node({ node_id: id, backend_stage: stage, blocker_code: "DOCUMENT_REQUIRED" }), withClassification), id).toBe(false);
      }
      const withSearch = summary({ clm: { readiness: { blockers: ["DOCUMENT_REQUIRED", "GOLDTIER_SEARCH_STALE"] } } });
      expect(isWaitingForEarlierSteps(node({ node_id: "READINESS", backend_stage: "READINESS", blocker_code: "DOCUMENT_REQUIRED" }), withSearch)).toBe(false);
      // A readiness blocker owned by the readiness stage's own position or later is not a prerequisite either.
      expect(isWaitingForEarlierSteps(node({ node_id: "READINESS", backend_stage: "READINESS", blocker_code: "DOCUMENT_REQUIRED" }),
        summary({ clm: { readiness: { blockers: ["DOCUMENT_REQUIRED", "UNKNOWN_CODE"] } } }))).toBe(false);
      // Only earlier prerequisites: waiting.
      expect(isWaitingForEarlierSteps(node({ node_id: "READINESS", backend_stage: "READINESS", blocker_code: "DOCUMENT_REQUIRED" }), summary())).toBe(true);
    });

    it("does not apply the readiness list to stages that do not derive from it", () => {
      const withClassification = summary({ clm: { readiness: { blockers: ["GOLDTIER_CLASSIFICATION_REQUIRED"] } } });
      expect(isWaitingForEarlierSteps(node(), withClassification)).toBe(true);
    });

    it("keeps the stage blocked when a sub-step needs attention", () => {
      const classification = { node_id: "TARGET_CLASSIFICATION", label: "Target classification", status: "REVIEW_REQUIRED" as const, children: [] };
      expect(isWaitingForEarlierSteps(node({ node_id: "READINESS", backend_stage: "READINESS", children: [classification] }), summary())).toBe(false);
      const quiet = { ...classification, status: "NOT_REACHED" as const };
      expect(isWaitingForEarlierSteps(node({ node_id: "READINESS", backend_stage: "READINESS", children: [quiet] }), summary())).toBe(true);
    });
  });

  describe("ambiguous, unknown or inconsistent information keeps the backend display", () => {
    it("in recovery, technical failure, completion or an unknown case status", () => {
      for (const status of ["RECOVERY_PENDING", "TECHNICAL_FAILURE", "COMPLETED", "SOMETHING_NEW"]) {
        expect(isWaitingForEarlierSteps(node(), summary({ status }))).toBe(false);
      }
      expect(isWaitingForEarlierSteps(node(), summary({ status: "RUNNING", technical_failure: { code: "X", message: "Y" } }))).toBe(false);
    });

    it("for a legacy or unknown stage order", () => {
      expect(isWaitingForEarlierSteps(node(), summary({ stage_order_version: 1 }))).toBe(false);
      expect(isWaitingForEarlierSteps(node(), summary({ stage_order_version: undefined }))).toBe(false);
    });

    it("for a missing or unknown stage", () => {
      expect(isWaitingForEarlierSteps(node({ backend_stage: null }), summary())).toBe(false);
      expect(isWaitingForEarlierSteps(node({ backend_stage: undefined }), summary())).toBe(false);
      expect(isWaitingForEarlierSteps(node({ backend_stage: "NEW_STAGE" as never }), summary())).toBe(false);
      expect(isWaitingForEarlierSteps(node(), summary({ current_stage: "NEW_STAGE" }))).toBe(false);
      expect(isWaitingForEarlierSteps(node(), summary({ current_stage: "COMPLETE" }))).toBe(false);
      expect(isWaitingForEarlierSteps(node(), summary({ active_exceptions: [exception("NEW_STAGE")] }))).toBe(false);
      expect(isWaitingForEarlierSteps(node(), summary({ interventions: [intervention("NEW_STAGE")] }))).toBe(false);
    });

    it("when the stage is recorded as completed, or the current stage is already completed", () => {
      expect(isWaitingForEarlierSteps(node(), summary({ completed_stages: ["REGISTRY", "GOLDTIER_SEARCH", "OWNERSHIP"] }))).toBe(false);
      expect(isWaitingForEarlierSteps(node(), summary({ completed_stages: ["REGISTRY", "GOLDTIER_SEARCH", "DOCUMENT"] }))).toBe(false);
    });

    it("when readiness information is missing for a readiness-derived stage", () => {
      const readiness = node({ node_id: "READINESS", backend_stage: "READINESS", blocker_code: "DOCUMENT_REQUIRED" });
      expect(isWaitingForEarlierSteps(readiness, summary({ clm: undefined }))).toBe(false);
      expect(isWaitingForEarlierSteps(readiness, summary({ clm: { readiness: {} } }))).toBe(false);
      expect(isWaitingForEarlierSteps(readiness, summary({ clm: { readiness: { blockers: "DOCUMENT_REQUIRED" } } }))).toBe(false);
      expect(isWaitingForEarlierSteps(readiness, summary({ clm: { readiness: { blockers: [42] } } }))).toBe(false);
    });

    it("when exception, completion or intervention lists are missing or malformed", () => {
      expect(isWaitingForEarlierSteps(node(), summary({ active_exceptions: undefined }))).toBe(false);
      expect(isWaitingForEarlierSteps(node(), summary({ completed_stages: undefined }))).toBe(false);
      expect(isWaitingForEarlierSteps(node(), summary({ interventions: "not-a-list" }))).toBe(false);
      // Interventions are optional in the API; their absence alone is not ambiguous.
      expect(isWaitingForEarlierSteps(node(), summary({ interventions: undefined }))).toBe(true);
    });
  });

  it("never changes the node or the summary", () => {
    const value = node({ blocker_code: null }); const state = summary({ active_exceptions: [exception("DOCUMENT")] });
    const before = JSON.stringify([value, state]);
    isWaitingForEarlierSteps(value, state);
    expect(JSON.stringify([value, state])).toBe(before);
  });
});
