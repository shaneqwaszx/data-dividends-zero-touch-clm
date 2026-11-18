import type { AutomationStage, AutomationStatus, ProcessingNode, ProcessingNodeStatus, StagePresentation, StagePresentationState, ZeroTouchCaseSummary } from "./types";

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
  // An open final-confirmation request is raised at READINESS but answered on Final review & send,
  // so while it is open no readiness-or-later stage is ever shown as merely waiting.
  const confirmationOpen = summary.active_exceptions.some(exception => exception.exception_type === "TARGET_CONFIRMATION_REQUIRED");
  if (confirmationOpen && nodeIndex >= stageIndex("READINESS")) return false;
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

/**
 * D-141 (amends D-121 display only): a stage that is complete for readiness while an advisory
 * ownership review stays open. Shown amber, never as green "Complete"; the backend status is unchanged.
 */
export const ADVISED_STAGE_LABEL = "Review advised";
export const ADVISED_STAGE_SUMMARY = "Not blocking. Review ownership before Review & Send.";

export function isAdvisoryReview(node: ProcessingNode): boolean {
  return node.advisory_review === true;
}

/*
 * OPQ S2: one shared rendering of the backend presentation verdict (OPQ S1) for every surface
 * (pipeline sidebar, section headers, progress tiles and counters). The frontend only renders the
 * backend verdict; it derives no state of its own and never changes send availability. A node
 * without a recognised verdict (an older backend, a child or a presentation-only step) keeps the
 * legacy rendering exactly.
 */

/** Rail marker class; "" is the neutral not-started marker. */
export type RailState = "done" | "now" | "attention" | "advised" | "";

export interface PresentationDisplay {
  state: StagePresentationState;
  rail: RailState;
  label: string;
  /** Text marker shown beside the label; colour is never the only signal. */
  symbol: string;
  /** Plain reason line, when the backend reason needs one. */
  note?: string;
  waiting: boolean;
  advised: boolean;
}

const PRESENTATION_STATES: ReadonlySet<StagePresentationState> = new Set<StagePresentationState>([
  "NOT_STARTED", "RUNNING", "COMPLETE", "REVIEW_ADVISED", "ACTION_REQUIRED", "BLOCKED", "FAILED", "SKIPPED",
]);

/** A3: wording for the reason an action is required; any other code is shown in plain words. */
const ACTION_REASON_TEXT: Readonly<Record<string, string>> = {
  IDENTITY_CONFIRMATION_REQUIRED: "confirm UEN",
  FINAL_CONFIRMATION_REQUIRED: "review and confirm",
};
const SILENT_ACTION_REASONS: ReadonlySet<string> = new Set(["OPEN_EXCEPTION"]);

/** Reason lines; zero-UBO (a valid result) and absent evidence (review advised) stay distinct. */
const REASON_NOTES: Readonly<Record<string, string>> = {
  NO_QUALIFYING_UBO: "No qualifying UBOs identified.",
  EVIDENCE_ABSENT: "No ownership evidence was available to analyse.",
  REVIEW_ISSUES: "Ownership review items remain open.",
  OWNERSHIP_SOURCE_PARTIAL: "Identity validated; the registry ownership source was partial.",
  VERIFIED_GOLDTIER_MATCH: "Skipped after a verified GoldTier match.",
  EARLIER_STAGE_BLOCKERS: "Held by issues in earlier stages.",
};

const PRESENTATION_SYMBOLS: Readonly<Record<StagePresentationState, string>> = {
  NOT_STARTED: "○",
  RUNNING: "●",
  COMPLETE: "✓",
  SKIPPED: "↷",
  REVIEW_ADVISED: "!",
  ACTION_REQUIRED: "!",
  BLOCKED: "■",
  FAILED: "×",
};

function plainReason(code: string): string {
  return code.replaceAll("_", " ").toLowerCase();
}

/** The node's backend verdict when it is well formed; otherwise null (legacy rendering). */
export function stagePresentation(node: ProcessingNode): StagePresentation | null {
  const presentation = node.presentation;
  if (!presentation || typeof presentation !== "object") return null;
  if (!PRESENTATION_STATES.has(presentation.state)) return null;
  if (!Array.isArray(presentation.owned_exception_ids) || !Array.isArray(presentation.linked_exception_ids)) return null;
  if (typeof presentation.counts_as_done !== "boolean") return null;
  return presentation;
}

/** The single state to colour, label and marker mapping for a backend verdict. */
export function presentationDisplay(presentation: StagePresentation): PresentationDisplay {
  const { state } = presentation;
  const reason = typeof presentation.reason_code === "string" && /^[A-Z0-9_]{1,64}$/.test(presentation.reason_code)
    ? presentation.reason_code : null;
  const waiting = state === "NOT_STARTED" && reason === "WAITING_FOR_EARLIER_STEPS";
  const note = reason ? REASON_NOTES[reason] : undefined;
  let label: string;
  let rail: RailState;
  switch (state) {
    case "NOT_STARTED": label = waiting ? WAITING_STAGE_LABEL : "Not started yet"; rail = ""; break;
    case "RUNNING": label = "In progress"; rail = "now"; break;
    case "COMPLETE": label = reason === "NO_RECORDS" ? "Complete — no records" : "Complete"; rail = "done"; break;
    case "SKIPPED": label = "Skipped"; rail = "done"; break;
    case "REVIEW_ADVISED": label = ADVISED_STAGE_LABEL; rail = "advised"; break;
    case "ACTION_REQUIRED": {
      const text = reason && !SILENT_ACTION_REASONS.has(reason) ? ACTION_REASON_TEXT[reason] ?? plainReason(reason) : null;
      label = text ? `Action required — ${text}` : "Action required";
      rail = "attention";
      break;
    }
    case "BLOCKED": label = "Blocked"; rail = "attention"; break;
    case "FAILED": label = "Failed"; rail = "attention"; break;
  }
  return { state, rail, label, symbol: PRESENTATION_SYMBOLS[state], note, waiting, advised: state === "REVIEW_ADVISED" };
}

/** Every top-level backend stage carries a verdict, so counters may use it. */
function pipelineHasPresentation(pipeline: readonly ProcessingNode[]): boolean {
  return pipeline.length > 0 && pipeline.every(node => stagePresentation(node) !== null);
}

/**
 * Open-issue count from the verdicts: each owned exception id once. Linked ids are display links
 * owned by another stage and are never counted. Null when any stage lacks a verdict (legacy count).
 */
export function presentationIssueCount(summary: ZeroTouchCaseSummary): number | null {
  const pipeline = summary.processing_pipeline ?? [];
  if (!pipelineHasPresentation(pipeline)) return null;
  const owned = new Set(pipeline.flatMap(node => stagePresentation(node)!.owned_exception_ids));
  return owned.size + (summary.technical_failure ? 1 : 0);
}

/** The stage that owns an exception id, for a linked-issue reference. */
export function exceptionOwnerNode(pipeline: readonly ProcessingNode[], exceptionId: string): ProcessingNode | undefined {
  return pipeline.find(node => stagePresentation(node)?.owned_exception_ids.includes(exceptionId));
}
