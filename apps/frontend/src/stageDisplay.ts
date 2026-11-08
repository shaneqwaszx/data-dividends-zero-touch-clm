import type { AutomationStage, AutomationStatus, ProcessingNode, ProcessingNodeStatus, ZeroTouchCaseSummary } from "./types";

/*
 * Presentation only. The backend reports a later stage as BLOCKED when its prerequisites are
 * missing (for example "no documents yet" or "ownership not analysed yet"). Shown as a red
 * blocker, that looks like work for the RM. This module decides, conservatively, when such a
 * stage is only waiting for earlier steps. It never changes the backend status, `data-status`,
 * stage counts, completion figures or navigation, and any doubt keeps today's display.
 */

/** The current (v2) automation stage order, from apps/backend/app/domain/zero_touch.py. */
const STAGE_ORDER_V2: readonly AutomationStage[] = ["REGISTRY", "GOLDTIER_SEARCH", "DOCUMENT", "OWNERSHIP", "READINESS", "MOCK_GOLDTIER"];

/** Case states in which the automation is actively working through, or waiting at, an earlier stage. */
const ELIGIBLE_CASE_STATUSES: ReadonlySet<AutomationStatus> = new Set<AutomationStatus>([
  "RUNNING", "RESUMING", "WAITING_FOR_REVIEW", "PENDING_INPUTS",
]);

/**
 * Readiness blocker codes that only say an earlier stage is unfinished, with the stage that owns
 * them. A failed, stale, invalid or classification code is never treated as waiting.
 */
const PREREQUISITE_BLOCKER_STAGES: Readonly<Record<string, AutomationStage>> = {
  REGISTRY_NOT_READY: "REGISTRY",
  GOLDTIER_SEARCH_REQUIRED: "GOLDTIER_SEARCH",
  GOLDTIER_SEARCH_REVIEW_REQUIRED: "GOLDTIER_SEARCH",
  DOCUMENT_REQUIRED: "DOCUMENT",
  DOCUMENT_PROCESSING: "DOCUMENT",
  DOCUMENT_REVIEW_INCOMPLETE: "DOCUMENT",
  OWNERSHIP_REQUIRED: "OWNERSHIP",
  OWNERSHIP_ANALYSIS_INCOMPLETE: "OWNERSHIP",
  OWNERSHIP_REVIEW_REQUIRED: "OWNERSHIP",
  GOVERNMENT_STATUS_REQUIRED: "OWNERSHIP",
};

/**
 * Backend stages whose pipeline nodes take their reason from the CLM readiness blocker list
 * (READINESS, GOLDTIER_TARGET and FINAL_REVIEW_SEND carry only its first code; api_models.py).
 */
const READINESS_DERIVED_STAGES: ReadonlySet<AutomationStage> = new Set<AutomationStage>(["READINESS", "MOCK_GOLDTIER"]);

/** Child statuses that need no attention; any other child status keeps the parent as reported. */
const QUIET_CHILD_STATUSES: ReadonlySet<ProcessingNodeStatus> = new Set<ProcessingNodeStatus>([
  "COMPLETE", "EMPTY", "SKIPPED", "NOT_REACHED",
]);

function stageIndex(stage: string | null | undefined): number {
  return stage ? STAGE_ORDER_V2.indexOf(stage as AutomationStage) : -1;
}

/**
 * True only when a backend-BLOCKED stage is merely waiting for an earlier step. Every condition
 * must hold; incomplete, unknown or inconsistent information returns false.
 */
export function isWaitingForEarlierSteps(node: ProcessingNode, summary: ZeroTouchCaseSummary): boolean {
  if (node.status !== "BLOCKED") return false;
  // Only the current stage order is understood; legacy or unknown orders keep the backend display.
  if (summary.stage_order_version !== 2) return false;
  if (!ELIGIBLE_CASE_STATUSES.has(summary.status) || summary.technical_failure) return false;

  const nodeIndex = stageIndex(node.backend_stage);
  const currentIndex = stageIndex(summary.current_stage);
  // The stage must be strictly later than where the automation currently is.
  if (nodeIndex < 0 || currentIndex < 0 || nodeIndex <= currentIndex) return false;
  // Missing collections are unknown information, not "nothing open".
  if (!Array.isArray(summary.completed_stages) || !Array.isArray(summary.active_exceptions)) return false;
  if (summary.interventions != null && !Array.isArray(summary.interventions)) return false;
  // A later stage already recorded as completed but reported BLOCKED is inconsistent.
  const completed = summary.completed_stages;
  if (completed.includes(node.backend_stage as AutomationStage)) return false;
  // The current stage must itself be unfinished, otherwise nothing earlier is holding this one.
  if (completed.includes(summary.current_stage)) return false;

  // Never hide an RM action: every open exception and intervention must belong to an earlier
  // stage, and none may carry this stage's blocker code. Those earlier blockers stay visible.
  for (const exception of summary.active_exceptions) {
    const index = stageIndex(exception.stage);
    if (index < 0 || index >= nodeIndex) return false;
    if (node.blocker_code && (exception.blocker_code === node.blocker_code || exception.blocker_codes?.includes(node.blocker_code))) return false;
  }
  for (const intervention of summary.interventions ?? []) {
    const index = stageIndex(intervention.owning_stage);
    if (index < 0 || index >= nodeIndex) return false;
    if (node.blocker_code && intervention.blocker_code === node.blocker_code) return false;
  }

  // The stage's own reason must be an earlier stage's unfinished prerequisite (or absent).
  const isEarlierPrerequisite = (code: unknown) => {
    const owner = typeof code === "string" ? PREREQUISITE_BLOCKER_STAGES[code] : undefined;
    return owner !== undefined && stageIndex(owner) < nodeIndex;
  };
  if (node.blocker_code && !isEarlierPrerequisite(node.blocker_code)) return false;
  // A readiness-derived stage shows only the first readiness blocker, so every retained
  // readiness blocker (for example a later GOLDTIER_CLASSIFICATION_REQUIRED) must also be an
  // earlier prerequisite. Missing readiness information keeps the backend display.
  if (READINESS_DERIVED_STAGES.has(node.backend_stage as AutomationStage)) {
    const blockers = summary.clm?.readiness?.blockers;
    if (!Array.isArray(blockers) || !blockers.every(isEarlierPrerequisite)) return false;
  }
  // Any sub-step that needs attention (for example a target classification) keeps the stage as reported.
  if ((node.children ?? []).some(child => !QUIET_CHILD_STATUSES.has(child.status))) return false;
  return true;
}

export const WAITING_STAGE_LABEL = "Waiting for earlier steps";
