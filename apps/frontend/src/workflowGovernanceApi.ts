// HR workflow-governance client (ADR-017, frozen contract docs/contracts/WORKFLOW_GOVERNANCE_API.md).
// The backend is authoritative: every route reauthorizes the actor, and the can_* flags in the
// responses only shape the UI. Nothing here decides who may do what.

import { API_BASE_URL, ApiError, authenticatedFetch, parseResponse } from "./api";
import type {
  CreateProposalRequest,
  GovernanceErrorBody,
  GovernanceErrorCode,
  ProposalResponse,
  RatchetRule,
  SimulateProposalRequest,
  SimulationResult,
  SimulationScenario,
  SubmitProposalRequest,
  UpdateProposalRequest,
  ValidateProposalRequest,
  ValidationIssue,
  ValidationReport,
  WithdrawProposalRequest,
} from "./workflowGovernanceTypes";

function jsonRequest(method: string, body: unknown, signal?: AbortSignal): RequestInit {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal };
}

const proposalsUrl = (workflowId: string) =>
  `${API_BASE_URL}/api/workflows/${encodeURIComponent(workflowId)}/proposals`;
const proposalUrl = (workflowId: string, proposalId: string) =>
  `${proposalsUrl(workflowId)}/${encodeURIComponent(proposalId)}`;

/** POST /workflows/{wid}/proposals (201). M1 accepts CHANGE only. */
export async function createProposal(workflowId: string, body: CreateProposalRequest): Promise<ProposalResponse> {
  return parseResponse(await authenticatedFetch(proposalsUrl(workflowId), jsonRequest("POST", body)));
}

/** PUT /workflows/{wid}/proposals/{pid}: DRAFT only, author only, with both expected revisions. */
export async function updateProposal(workflowId: string, proposalId: string, body: UpdateProposalRequest): Promise<ProposalResponse> {
  return parseResponse(await authenticatedFetch(proposalUrl(workflowId, proposalId), jsonRequest("PUT", body)));
}

/** Read-only: writes nothing. `stages` validates unsaved editor content. */
export async function validateProposal(
  workflowId: string, proposalId: string, body: ValidateProposalRequest, signal?: AbortSignal,
): Promise<ValidationReport> {
  return parseResponse(await authenticatedFetch(`${proposalUrl(workflowId, proposalId)}/validate`, jsonRequest("POST", body, signal)));
}

/** Read-only and synthetic only: no case read, no provider call, no write. */
export async function simulateProposal(
  workflowId: string, proposalId: string, body: SimulateProposalRequest, signal?: AbortSignal,
): Promise<SimulationResult> {
  return parseResponse(await authenticatedFetch(`${proposalUrl(workflowId, proposalId)}/simulate`, jsonRequest("POST", body, signal)));
}

export async function fetchSimulationScenarios(signal?: AbortSignal): Promise<SimulationScenario[]> {
  return parseResponse(await authenticatedFetch(`${API_BASE_URL}/api/workflows/simulation-scenarios`, { signal }));
}

/** The content_hash must be the one from the latest successful validation. */
export async function submitProposal(workflowId: string, proposalId: string, body: SubmitProposalRequest): Promise<ProposalResponse> {
  return parseResponse(await authenticatedFetch(`${proposalUrl(workflowId, proposalId)}/submit`, jsonRequest("POST", body)));
}

export async function withdrawProposal(workflowId: string, proposalId: string, body: WithdrawProposalRequest): Promise<ProposalResponse> {
  return parseResponse(await authenticatedFetch(`${proposalUrl(workflowId, proposalId)}/withdraw`, jsonRequest("POST", body)));
}

export const workflowGovernanceQueryKeys = {
  scenarios: (userId: string) => ["auth", userId, "workflows", "simulation-scenarios"] as const,
};

/** Plain explanations of the required-obligation ratchet (ADR-017 §2). */
export const RATCHET_RULE_EXPLANATIONS: Record<RatchetRule, string> = {
  "RR-1": "A required step cannot be removed.",
  "RR-2": "A required step must keep holding the send until it is confirmed.",
  "RR-3": "A required field cannot be removed or made optional.",
  "RR-4": "A required field's type cannot change.",
  "RR-5": "A required field's wording can only change at typo level. Add a new field instead.",
  "RR-6": "A required choice cannot gain options. Options can be removed, never added.",
  "RR-7": "A required field cannot start being prefilled from case data.",
  "RR-8": "Where a required step or field applies cannot be narrowed.",
  "RR-9": "The built-in mandatory stages and their order cannot be changed.",
  "RR-10": "A required step's name cannot change.",
};

const EXISTING_WORKFLOW_MESSAGES: Record<string, string> = {
  WORKFLOW_FORBIDDEN: "You don't have permission to do that.",
  WORKFLOW_NOT_FOUND: "This workflow is not available.",
  WORKFLOW_CONFLICT: "Someone else changed this workflow. Nothing was changed. Use Reload to load the latest version, then try again.",
  WORKFLOW_UNAVAILABLE: "Workflows are unavailable right now. Nothing was changed.",
};

/** Every frozen governance code has an HR-facing message (the Record type enforces completeness). */
export const GOVERNANCE_ERROR_MESSAGES: Record<GovernanceErrorCode, string> = {
  WORKFLOW_PROPOSAL_OPEN: "This workflow already has an open proposal. Only one proposal can be open at a time.",
  WORKFLOW_PROPOSAL_STALE: "Another change was published first, so this proposal is out of date. Withdraw it and propose the change again.",
  WORKFLOW_PROPOSAL_NOT_FOUND: "This proposal is no longer available. Use Reload to load the latest version.",
  WORKFLOW_PROPOSAL_STATE_INVALID: "This proposal can't be changed in its current state. Use Reload to load the latest version.",
  WORKFLOW_PROPOSAL_CONTENT_CHANGED: "The proposal changed after it was validated. Validate it again before submitting.",
  WORKFLOW_PROPOSAL_KIND_NOT_AVAILABLE: "That kind of proposal is not available yet.",
  WORKFLOW_PROPOSAL_INVALID: "The proposal has problems to fix before it can continue.",
  WORKFLOW_PROPOSAL_EMPTY: "Add at least one step, each with at least one field, before this can continue.",
  WORKFLOW_REQUIRED_OBLIGATION_REMOVED: "A required step or field cannot be removed or made optional.",
  WORKFLOW_REQUIRED_OBLIGATION_WEAKENED: "A required step or field cannot be weakened.",
  WORKFLOW_PERMANENT_OBLIGATION_ACKNOWLEDGEMENT_REQUIRED: "The new permanent requirements must be acknowledged before approval.",
  WORKFLOW_SELF_DECISION_REFUSED: "The author of a proposal cannot decide it.",
  WORKFLOW_PROPOSAL_TOO_LARGE: "The proposal is too large. Remove some steps or fields and try again.",
  WORKFLOW_HISTORY_UNAVAILABLE: "Workflow history is unavailable right now. Nothing was changed.",
  WORKFLOW_GOVERNANCE_NOT_MIGRATED: "Workflow governance is not yet enabled on this server. Nothing was changed.",
  WORKFLOW_DRAFT_NOT_RELEASABLE: "This draft can't be released yet.",
  WORKFLOW_RUN_CONFIRMATION_IN_PROGRESS: "A case is being confirmed against this workflow. Try again in a moment.",
  WORKFLOW_NOTICES_UNACKNOWLEDGED: "There are workflow notices to acknowledge first.",
  WORKFLOW_ROUTE_RETIRED: "That action has been retired. Changes now go through proposals and Director approval.",
};

export interface GovernanceRefusal {
  code: string | null;
  message: string;
  rule: RatchetRule | null;
  issues: ValidationIssue[];
}

/** A safe, HR-facing view of a failed request; never projects anything beyond the fixed body. */
export function governanceRefusal(error: unknown): GovernanceRefusal {
  if (!(error instanceof ApiError)) {
    return { code: null, message: "That did not work. Please try again.", rule: null, issues: [] };
  }
  const body = (error.detail ?? {}) as Partial<GovernanceErrorBody>;
  const code = error.code;
  const message = (code && (GOVERNANCE_ERROR_MESSAGES as Record<string, string>)[code])
    || (code && EXISTING_WORKFLOW_MESSAGES[code])
    || error.message;
  return {
    code,
    message,
    rule: typeof body.rule === "string" ? body.rule : null,
    issues: Array.isArray(body.issues) ? body.issues : [],
  };
}

/** Refusals caused by out-of-date local state; the editor offers a Reload for these. */
export const RELOADABLE_CODES: ReadonlySet<string> = new Set([
  "WORKFLOW_CONFLICT", "WORKFLOW_PROPOSAL_NOT_FOUND", "WORKFLOW_PROPOSAL_STATE_INVALID", "WORKFLOW_PROPOSAL_STALE",
]);

export function governanceErrorMessage(error: unknown): string {
  return governanceRefusal(error).message;
}

/** Issues grouped by rule in RR order; issues without a rule (structure) come last. */
export function issuesByRule(issues: ValidationIssue[]): Array<{ rule: RatchetRule | null; issues: ValidationIssue[] }> {
  const order = Object.keys(RATCHET_RULE_EXPLANATIONS) as RatchetRule[];
  const groups = new Map<RatchetRule | null, ValidationIssue[]>();
  for (const issue of issues) groups.set(issue.rule, [...(groups.get(issue.rule) ?? []), issue]);
  return [...groups.entries()]
    .sort(([a], [b]) => (a === null ? order.length : order.indexOf(a)) - (b === null ? order.length : order.indexOf(b)))
    .map(([rule, items]) => ({ rule, issues: items }));
}
