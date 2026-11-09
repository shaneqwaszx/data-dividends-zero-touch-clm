// Shapes a fixed sample case like a backend case summary, so the sample case page can reuse the
// real case page's Pipeline rail and Onboarding progress panel. Frontend-only: no API calls.
// Only the fields those two panels read are filled; nothing here is sent anywhere.

import {
  BUSINESS_EXCEPTION_TYPE_LABELS,
  type AutomationStage,
  type HumanInterventionProjection,
  type ProcessingNode,
  type ProcessingNodeStatus,
  type ZeroTouchCaseSummary,
  type ZeroTouchException,
} from "../../types";
import type { SampleCaseDetail, SampleStepState } from "./onboardingSample";

interface NodeSpec {
  id: string;
  label: string;
  stage: AutomationStage | null;
  done: string;
  provider?: string;
  operation?: string;
}

// Same steps, labels and order of sample stages as the live case pipeline.
const NODES: readonly NodeSpec[] = [
  { id: "CASE_START", label: "Case created", stage: null, done: "Automation record created" },
  { id: "INITIAL_IDENTITY", label: "Initial identity", stage: null, done: "Legal name, registration ID, and country retained" },
  { id: "JURISDICTION", label: "Jurisdiction", stage: null, done: "Jurisdiction resolved" },
  { id: "ACRA_REGISTRY", label: "Registry verification", stage: "REGISTRY", done: "Registry acquisition retained", provider: "ACRA" },
  { id: "GOLDTIER_SEARCH", label: "Existing-customer search", stage: "GOLDTIER_SEARCH", done: "No existing customer found. Continuing as a new customer.", provider: "GOLDTIER", operation: "SEARCH" },
  { id: "DOCUMENT_IDP", label: "Document verification", stage: "DOCUMENT", done: "Documents verified" },
  { id: "RECONCILIATION", label: "Data reconciliation", stage: "DOCUMENT", done: "Registry and document data agree" },
  { id: "OWNERSHIP_UBO", label: "Ownership & UBO", stage: "OWNERSHIP", done: "Ownership and beneficial owners resolved" },
  { id: "ADVISORY", label: "Risk assessment", stage: "OWNERSHIP", done: "Bounded POC advisory assessment complete; not production AML/KYC risk" },
  { id: "READINESS", label: "Submission readiness", stage: "READINESS", done: "Ready for submission" },
  { id: "GOLDTIER_TARGET", label: "GoldTier submission package", stage: "READINESS", done: "Submission package prepared", provider: "GOLDTIER" },
  { id: "FINAL_REVIEW_SEND", label: "Final review & send", stage: "MOCK_GOLDTIER", done: "Submitted to GoldTier", provider: "GOLDTIER" },
];

const CURRENT_STATUS: Record<Exclude<SampleStepState, "done" | "not_started">, ProcessingNodeStatus> = {
  review: "REVIEW_REQUIRED",
  in_progress: "IN_PROGRESS",
  waiting_inputs: "BLOCKED",
};

function blockerLabel(type: SampleCaseDetail["blockers"][number]["type"]): string {
  return BUSINESS_EXCEPTION_TYPE_LABELS[type];
}

function pipeline(detail: SampleCaseDetail): ProcessingNode[] {
  const stateOf = (stage: AutomationStage) => detail.steps.find((step) => step.stage === stage)?.state ?? "not_started";
  const openBlocker = (stage: AutomationStage) => detail.blockers.find((blocker) => blocker.stage === stage && !blocker.resolved);
  return NODES.map((spec) => {
    const provider = spec.provider === "ACRA" && detail.jurisdiction !== "SG" ? null : spec.provider ?? null;
    const base = { node_id: spec.id, label: spec.label, backend_stage: spec.stage, provider, environment: null, operation: spec.operation ?? null, children: [] };
    const state = spec.stage ? stateOf(spec.stage) : "done";
    if (state === "done") {
      const resolved = spec.stage ? detail.blockers.filter((blocker) => blocker.stage === spec.stage && blocker.resolved) : [];
      const first = NODES.find((node) => node.stage === spec.stage) === spec;
      const notes = first ? resolved.map((blocker) => `Resolved: ${blockerLabel(blocker.type)}${blocker.resolved_by ? ` (by ${blocker.resolved_by})` : ""}`) : [];
      return { ...base, status: "COMPLETE", safe_result: [spec.done, ...notes].join(". ") };
    }
    // The current stage shows on its first step; later steps of the same stage wait for it.
    const first = NODES.find((node) => node.stage === spec.stage) === spec;
    if (state === "not_started" || !first) return { ...base, status: "NOT_REACHED", safe_result: "Waits for earlier steps" };
    const blocker = openBlocker(spec.stage!);
    const result = state === "review" ? `Review required: ${blocker ? blockerLabel(blocker.type) : spec.label}`
      : state === "waiting_inputs" ? "Waiting for the required documents"
      : "Processing";
    return { ...base, status: CURRENT_STATUS[state], safe_result: result, blocker_code: blocker?.type ?? null };
  });
}

/** A read-only case summary for one sample case, holding only what the pipeline panels read. */
export function sampleCaseSummary(detail: SampleCaseDetail): ZeroTouchCaseSummary {
  const open = detail.blockers.filter((blocker) => !blocker.resolved);
  const exceptions = open.map((blocker, index) => ({
    exception_id: `${detail.case_id}-blocker-${index + 1}`,
    case_id: detail.case_id,
    exception_type: blocker.type,
    stage: blocker.stage,
    status: "OPEN",
    blocker_code: blocker.type,
    blocker_codes: [blocker.type],
    explanation: blockerLabel(blocker.type),
  }) as unknown as ZeroTouchException);
  const interventions = exceptions.map((exception) => ({
    intervention_id: exception.exception_id,
    owning_stage: exception.stage,
    title: blockerLabel(exception.exception_type),
    blocker_code: exception.blocker_code,
    blocker_class: "HUMAN_DECISION",
    expected_next_step: `Review: ${blockerLabel(exception.exception_type)}`,
    evidence_actions: [],
  }) as unknown as HumanInterventionProjection);
  const summary = {
    case: { case_id: detail.case_id, requested_uen: detail.requested_uen, client_scope_label: detail.team_display_name },
    status: detail.status,
    current_stage: detail.current_stage,
    completed_stages: detail.steps.filter((step) => step.state === "done").map((step) => step.stage),
    active_exceptions: exceptions,
    interventions,
    technical_failure: null,
    // Not the live stage order: sample cases run Registry before Existing-customer search.
    stage_order_version: 1,
    processing_pipeline: pipeline(detail),
    clm: {},
    created_at: detail.created_at,
    updated_at: detail.updated_at,
  };
  return summary as unknown as ZeroTouchCaseSummary;
}
