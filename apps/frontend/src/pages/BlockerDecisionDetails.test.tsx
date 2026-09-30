import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import type {
  BlockerDecisionClassification,
  BlockerDecisionRecord,
  HumanInterventionProjection,
  ZeroTouchCaseSummary,
  ZeroTouchException,
} from "../types";
import BlockerDecisionDetails from "./BlockerDecisionDetails";
import CaseStateExplanationPanel from "./CaseStateExplanationPanel";
import HumanInterventionPanel from "./HumanInterventionPanel";

function decision(
  classification: BlockerDecisionClassification,
  overrides: Partial<BlockerDecisionRecord["metadata"]> = {},
): BlockerDecisionRecord {
  return {
    decision_id: `decision-${classification}`,
    case_id: "case-1",
    exception_id: classification === "CONTINUE_WITH_WARNING" ? null : "exception-1",
    evidence_version: "case:7",
    automation_version: 7,
    recorded_at: "2026-09-29T02:00:00Z",
    metadata: {
      blocker_code: "DOCUMENT_REVIEW_REQUIRED",
      exception_type: "DOCUMENT_REVIEW_REQUIRED",
      classification,
      policy_version: "BLOCKER_DECISION_POC_V1",
      rule_version: "DOCUMENT_REVIEW_REQUIRED_V1",
      owner: "DOCUMENT_REVIEW_OWNER",
      minimum_inputs: ["CURRENT_DOCUMENT_EVIDENCE", "CURRENT_DOCUMENT_REVIEW"],
      permitted_actions: ["COMPLETE_DOCUMENT_REVIEW"],
      currently_available_actions: ["COMPLETE_DOCUMENT_REVIEW"],
      resume_stage: "DOCUMENT",
      resume_transition: "RECHECK_FROM_STAGE",
      resume_ready: true,
      invalidated_dependencies: ["TARGET_PLAN", "TARGET_PLAN", "TARGET_MUTATIONS"],
      explanation: "Retained policy explains the bounded document review decision.",
      unknowns: [],
      ...overrides,
    },
    actor_id: null,
    reviewer_id: null,
  };
}

function exception(record: BlockerDecisionRecord): ZeroTouchException {
  return {
    exception_id: "exception-1",
    case_id: "case-1",
    exception_type: "DOCUMENT_REVIEW_REQUIRED",
    stage: "DOCUMENT",
    status: "OPEN",
    blocker_code: record.metadata.blocker_code,
    blocker_codes: [record.metadata.blocker_code, record.metadata.blocker_code],
    explanation: "The retained document requires review.",
    evidence_version: "case:7",
    automation_version: 7,
    evidence: [],
    available_actions: [],
    decisions: [record, record],
    created_at: "2026-09-29T02:00:00Z",
    resolved_at: null,
    resolution: null,
  };
}

function intervention(record: BlockerDecisionRecord, withAction = false): HumanInterventionProjection {
  return {
    intervention_id: "exception-1",
    owning_stage: "DOCUMENT",
    owning_stage_label: "Documents / reconciliation",
    title: "Document review required",
    blocker_code: record.metadata.blocker_code,
    explanation: "The retained document requires review.",
    required_evidence_or_input: ["Review the retained document."],
    authorized_actions: withAction ? [{
      action: "KEEP_REGISTRY_VALUE",
      label: "Keep registry value",
      description: "Retain the current registry observation.",
    }] : [],
    no_action_reason: withAction ? null : "No exception resolution action is available.",
    expected_next_step: "Use the existing evidence surface when an action is available.",
    candidate_summaries: [],
    decisions: [record, record],
  };
}

function summary(record: BlockerDecisionRecord, withIntervention: boolean): ZeroTouchCaseSummary {
  const activeException = exception(record);
  return {
    status: "WAITING_FOR_REVIEW",
    current_stage: "DOCUMENT",
    clm: {
      readiness: {
        registry: { status: "READY" },
        document: { status: "REVIEW_REQUIRED" },
        ownership: { status: "BLOCKED" },
        goldtier: { status: "NOT_SUBMITTED" },
        blockers: [record.metadata.blocker_code],
        warnings: [],
      },
    },
    active_exceptions: [activeException],
    interventions: withIntervention ? [intervention(record)] : [],
    target_operations: [],
    technical_failure: null,
  } as unknown as ZeroTouchCaseSummary;
}

describe("BlockerDecisionDetails", () => {
  it("renders USER_ACTION_REQUIRED policy metadata once without turning permitted metadata into buttons", () => {
    const record = decision("USER_ACTION_REQUIRED");
    const interventionSummary = summary(record, true);
    interventionSummary.interventions = [intervention(record, true)];
    const markup = renderToStaticMarkup(
      <HumanInterventionPanel summary={interventionSummary} isBusy={false} onResolve={vi.fn()} />,
    );
    expect(markup).toContain("User action required");
    expect(markup).toContain("BLOCKER_DECISION_POC_V1 · rule DOCUMENT_REVIEW_REQUIRED_V1");
    expect(markup).toContain("Document review owner");
    expect(markup).toContain("Current document evidence");
    expect(markup).toContain("Complete document review");
    expect(markup).toContain("Recheck from stage from Document");
    expect(markup.match(/Target plan/g)).toHaveLength(1);
    expect(markup.match(/class="blocker-decision /g)).toHaveLength(1);
    expect(markup.match(/<button/g)).toHaveLength(1);
    expect(markup).toContain("Keep registry value");
  });

  it("renders the identity review owner, missing inputs, and same-case Search resume once", () => {
    const record = decision("USER_ACTION_REQUIRED", {
      blocker_code: "INITIAL_IDENTITY_INCOMPLETE",
      exception_type: "REGISTRY_REVIEW_REQUIRED",
      rule_version: "BPD-IDENTITY-1",
      owner: "IDENTITY_REVIEW_OWNER",
      minimum_inputs: ["CURRENT_CASE_VERSION", "CORRECTED_IDENTITY_WITH_RATIONALE"],
      permitted_actions: ["CORRECT_INITIAL_IDENTITY"],
      currently_available_actions: ["CORRECT_INITIAL_IDENTITY"],
      resume_stage: "GOLDTIER_SEARCH",
      resume_transition: "RECHECK_FROM_STAGE",
      invalidated_dependencies: ["INITIAL_TARGET_SEARCH", "INITIAL_TARGET_SEARCH"],
      explanation: "Correct the same-case identity before the authorized read-only Search recheck.",
    });
    const markup = renderToStaticMarkup(<BlockerDecisionDetails decisions={[record, record]} />);

    expect(markup.match(/Identity review owner/g)).toHaveLength(1);
    expect(markup.match(/Corrected identity with rationale/g)).toHaveLength(1);
    expect(markup.match(/Correct initial identity/g)).toHaveLength(2);
    expect(markup.match(/Recheck from stage from Goldtier search/g)).toHaveLength(1);
    expect(markup.match(/Initial target search/g)).toHaveLength(1);
    expect(markup).not.toContain("<button");
  });

  it("renders EXTERNAL_DEPENDENCY as an owner boundary with no invented action", () => {
    const record = decision("EXTERNAL_DEPENDENCY", {
      blocker_code: "SEARCH_SERVICE_UNAVAILABLE",
      exception_type: "TARGET_PARTIAL_REVIEW_REQUIRED",
      owner: "TARGET_PROVIDER_OWNER",
      permitted_actions: ["RUN_READ_ONLY_SEARCH_RECHECK"],
      currently_available_actions: [],
      resume_ready: false,
      explanation: "Search depends on the retained target provider state.",
    });
    const markup = renderToStaticMarkup(
      <HumanInterventionPanel summary={summary(record, true)} isBusy={false} onResolve={vi.fn()} />,
    );
    expect(markup).toContain("External dependency");
    expect(markup).toContain("Target provider owner");
    expect(markup).toContain("No action currently available");
    expect(markup).toContain("the browser cannot complete it");
    expect(markup).not.toContain("<button");
  });

  it("renders an unknown HARD_STOP compactly, deduplicates unknowns, and creates no action", () => {
    const record = decision("HARD_STOP", {
      blocker_code: "FUTURE_UNKNOWN_BLOCKER",
      exception_type: null,
      owner: "POLICY_OWNER",
      permitted_actions: ["ESCALATE_TO_OWNER"],
      currently_available_actions: ["ESCALATE_TO_OWNER"],
      resume_stage: null,
      resume_transition: "NO_AUTOMATIC_RESUME",
      resume_ready: false,
      explanation: "No current blocker decision rule matches this retained code.",
      unknowns: ["FUTURE_UNKNOWN_BLOCKER", "SECONDARY_UNKNOWN", "SECONDARY_UNKNOWN"],
    });
    const markup = renderToStaticMarkup(<BlockerDecisionDetails decisions={[record, record]} />);
    expect(markup).toContain("Hard stop");
    expect(markup).toContain("No current blocker decision rule matches");
    expect(markup.match(/<code>FUTURE_UNKNOWN_BLOCKER<\/code>/g)).toHaveLength(1);
    expect(markup.match(/<code>SECONDARY_UNKNOWN<\/code>/g)).toHaveLength(1);
    expect(markup).toContain("metadata does not create a browser action");
    expect(markup).not.toContain("<button");
  });

  it("renders exception decision details in one surface when an intervention exists", () => {
    const record = decision("USER_ACTION_REQUIRED");
    const value = summary(record, true);
    const stateMarkup = renderToStaticMarkup(<CaseStateExplanationPanel summary={value} onNavigate={() => undefined} />);
    const interventionMarkup = renderToStaticMarkup(<HumanInterventionPanel summary={value} isBusy={false} onResolve={() => undefined} />);
    expect(stateMarkup).toContain("shown once in Action required");
    expect(stateMarkup).not.toContain("Retained policy explains the bounded document review decision.");
    expect(interventionMarkup.match(/Retained policy explains the bounded document review decision\./g)).toHaveLength(1);
  });
});
