// Director workflow approvals client (WS-D, ADR-017 §1, frozen contract docs/contracts/WORKFLOW_GOVERNANCE_API.md).
// Backend-authoritative: the can_* flags in responses only shape the UI. A decision is never retried.

import { API_BASE_URL, ApiError, authenticatedFetch, parseResponse } from "./api";
import type { AuthenticatedProfile } from "./types";
import type {
  ApprovalInboxResponse,
  ComparisonResponse,
  DecisionOutcome,
  DecisionRequest,
  DecisionResponse,
  GovernanceErrorCode,
  ValidationIssue,
} from "./workflowGovernanceTypes";

export const DECISION_REASON_MIN = 10;
export const DECISION_REASON_MAX = 240;

const segment = (value: string) => encodeURIComponent(value);

/** Null means workflow approvals are not available on this server (404). */
export async function fetchApprovalInbox(signal?: AbortSignal): Promise<ApprovalInboxResponse | null> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/workflow-approvals`, { signal });
  if (response.status === 404) return null;
  return parseResponse<ApprovalInboxResponse>(response);
}

export async function fetchProposalComparison(
  workflowId: string,
  proposalId: string,
  signal?: AbortSignal,
): Promise<ComparisonResponse> {
  return parseResponse(await authenticatedFetch(
    `${API_BASE_URL}/api/workflows/${segment(workflowId)}/proposals/${segment(proposalId)}/comparison`,
    { signal },
  ));
}

export async function decideProposal(
  workflowId: string,
  proposalId: string,
  body: DecisionRequest,
): Promise<DecisionResponse> {
  return parseResponse(await authenticatedFetch(
    `${API_BASE_URL}/api/workflows/${segment(workflowId)}/proposals/${segment(proposalId)}/decision`,
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) },
  ));
}

export function trimmedReasonLength(reason: string): number {
  return reason.trim().length;
}

export function decisionReasonValid(reason: string): boolean {
  const length = trimmedReasonLength(reason);
  return length >= DECISION_REASON_MIN && length <= DECISION_REASON_MAX;
}

/**
 * Builds the request from the comparison the Director reviewed: its revisions and content hash,
 * and on APPROVE exactly the comparison's permanent-obligation keys (REJECT sends none).
 */
export function buildDecisionRequest(
  comparison: ComparisonResponse,
  outcome: DecisionOutcome,
  reason: string,
): DecisionRequest {
  return {
    outcome,
    reason: reason.trim(),
    expected_workflow_revision: comparison.workflow_revision,
    expected_proposal_revision: comparison.proposal.revision,
    // A pending proposal always carries its frozen hash; the page blocks a decision without one.
    content_hash: comparison.proposal.content_hash ?? "",
    acknowledged_permanent_obligations: outcome === "APPROVE"
      ? comparison.permanent_obligations.map(item => ({ stage_id: item.key.stage_id, field_id: item.key.field_id }))
      : [],
  };
}

export interface ApprovalErrorView {
  message: string;
  /** The page must be reloaded before another decision can be attempted. */
  reload: boolean;
  /** The server refused this Director for this proposal; offer no decision. */
  refused: boolean;
  /** Nothing changed and the same decision can simply be tried again later (409 RUN_CONFIRMATION_IN_PROGRESS). */
  retryLater: boolean;
  issues: ValidationIssue[];
}

const APPROVAL_ERROR_MESSAGES: Partial<Record<GovernanceErrorCode | "WORKFLOW_CONFLICT" | "WORKFLOW_FORBIDDEN" | "WORKFLOW_NOT_FOUND" | "WORKFLOW_UNAVAILABLE", string>> = {
  WORKFLOW_SELF_DECISION_REFUSED:
    "You authored this proposal, so you cannot decide it. Another Director must approve or reject it. Nothing was changed.",
  WORKFLOW_FORBIDDEN: "You are not allowed to decide this proposal. Nothing was changed.",
  WORKFLOW_PERMANENT_OBLIGATION_ACKNOWLEDGEMENT_REQUIRED:
    "The permanent obligations to confirm no longer match this proposal. Reload the comparison, review them and confirm again. Nothing was changed.",
  WORKFLOW_PROPOSAL_STALE:
    "Another version was published first, so this proposal is now stale and cannot be approved. Reload to see its current state. Nothing was changed.",
  WORKFLOW_PROPOSAL_CONTENT_CHANGED:
    "The proposal content no longer matches what you reviewed. Reload the comparison and review it again. Nothing was changed.",
  WORKFLOW_CONFLICT:
    "This workflow or proposal changed while you were reviewing it. Reload the comparison before deciding. Nothing was changed.",
  WORKFLOW_PROPOSAL_STATE_INVALID:
    "This proposal is no longer awaiting a decision. Reload to see its current state. Nothing was changed.",
  WORKFLOW_HISTORY_UNAVAILABLE: "Workflow history is unavailable right now. Nothing was changed. Try again later.",
  WORKFLOW_GOVERNANCE_NOT_MIGRATED: "Workflow approval governance is not enabled on this server yet. Nothing was changed.",
  WORKFLOW_UNAVAILABLE: "Workflows are unavailable right now. Nothing was changed. Try again later.",
  WORKFLOW_PROPOSAL_NOT_FOUND: "This proposal is not available.",
  WORKFLOW_NOT_FOUND: "This proposal is not available.",
  WORKFLOW_REQUIRED_OBLIGATION_REMOVED:
    "Approval was refused: a required step or field would be removed or made optional. Nothing was changed.",
  WORKFLOW_REQUIRED_OBLIGATION_WEAKENED:
    "Approval was refused: a required step or field would be weakened. Nothing was changed.",
  WORKFLOW_PROPOSAL_INVALID: "Approval was refused: the proposal is no longer valid. Nothing was changed.",
  WORKFLOW_PROPOSAL_TOO_LARGE: "Approval was refused: the proposal is too large. Nothing was changed.",
  WORKFLOW_RUN_CONFIRMATION_IN_PROGRESS:
    "A case is confirming a required step on this workflow right now, so it can't be deactivated yet. Nothing was changed. Try again in a moment.",
  WORKFLOW_PROPOSAL_KIND_NOT_AVAILABLE:
    "That kind of proposal is not available for this workflow (for example, onboarding can't be deactivated). Nothing was changed.",
};

/** 409 codes that change nothing and are fixed by waiting, not by reloading. */
const RETRY_LATER_CODES = new Set<string>(["WORKFLOW_RUN_CONFIRMATION_IN_PROGRESS"]);

const RELOAD_CODES = new Set<string>([
  "WORKFLOW_PERMANENT_OBLIGATION_ACKNOWLEDGEMENT_REQUIRED",
  "WORKFLOW_PROPOSAL_STALE",
  "WORKFLOW_PROPOSAL_CONTENT_CHANGED",
  "WORKFLOW_CONFLICT",
  "WORKFLOW_PROPOSAL_STATE_INVALID",
  // Decision-time ratchet and content refusals repeat until the comparison is reloaded.
  "WORKFLOW_REQUIRED_OBLIGATION_REMOVED",
  "WORKFLOW_REQUIRED_OBLIGATION_WEAKENED",
  "WORKFLOW_PROPOSAL_INVALID",
  "WORKFLOW_PROPOSAL_TOO_LARGE",
]);

function errorIssues(error: ApiError): ValidationIssue[] {
  const issues = (error.detail as { issues?: unknown } | null)?.issues;
  if (!Array.isArray(issues)) return [];
  return issues.filter((item): item is ValidationIssue =>
    typeof item === "object" && item !== null && typeof (item as ValidationIssue).message === "string");
}

export function approvalErrorView(error: unknown): ApprovalErrorView {
  if (!(error instanceof ApiError)) {
    return { message: "That did not work. Nothing was changed. Please try again.", reload: false, refused: false, retryLater: false, issues: [] };
  }
  const code = error.code ?? "";
  const known = APPROVAL_ERROR_MESSAGES[code as keyof typeof APPROVAL_ERROR_MESSAGES];
  const fallback = error.status === 409
    ? APPROVAL_ERROR_MESSAGES.WORKFLOW_CONFLICT!
    : error.status === 503
      ? "The service is unavailable right now. Nothing was changed. Try again later."
      : error.status === 404
        ? "This proposal is not available."
        : error.message;
  const retryLater = RETRY_LATER_CODES.has(code);
  return {
    message: known ?? fallback,
    reload: RELOAD_CODES.has(code) || (error.status === 409 && !retryLater),
    refused: code === "WORKFLOW_SELF_DECISION_REFUSED" || error.status === 403,
    retryLater,
    issues: errorIssues(error),
  };
}

/** User-scoped keys: identity and role lead every key so one user's results never serve another. */
export const workflowApprovalQueryKeys = {
  all: (actor: Pick<AuthenticatedProfile, "user_id" | "role">) => ["auth", actor.user_id, actor.role, "workflow-approvals"] as const,
  inbox: (actor: Pick<AuthenticatedProfile, "user_id" | "role">) =>
    [...workflowApprovalQueryKeys.all(actor), "inbox"] as const,
  comparison: (actor: Pick<AuthenticatedProfile, "user_id" | "role">, workflowId: string, proposalId: string) =>
    [...workflowApprovalQueryKeys.all(actor), "comparison", workflowId, proposalId] as const,
};
