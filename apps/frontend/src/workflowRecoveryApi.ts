// M2 workflow recovery and administration client (ADR-017 §1.2, §1.4, §4; contract CC-4).
// Backend-authoritative: every route reauthorizes the actor, and the helpers below only shape the
// UI. Restore and reset never send stages: the backend computes the safe target
// (base ∪ required_baseline). Nothing here decides who may do what.

import { API_BASE_URL, authenticatedFetch, parseResponse } from "./api";
import type { WorkflowStage } from "./workflowApi";
import {
  DRAFT_RELEASE_AFTER_DAYS,
  type AcknowledgeNoticeRequest,
  type ApplicabilityEscalationRequest,
  type CopyProposalRequest,
  type DecidedProposalSummary,
  type EmergencyFallbackRequest,
  type EmergencyFallbackResponse,
  type NoticeListResponse,
  type ProposalKind,
  type ProposalResponse,
  type ReleaseDraftRequest,
  type VersionProvenance,
  type WorkflowVersionResponse,
} from "./workflowGovernanceTypes";

export const FALLBACK_REASON_MIN = 10;
export const FALLBACK_REASON_MAX = 240;
/** ReleaseDraftRequest.reason is ShortText: 1-240 characters after trimming. */
export const RELEASE_REASON_MAX = 240;
export const NOTE_MAX = 240;

const segment = (value: string) => encodeURIComponent(value);
const workflowUrl = (workflowId: string) => `${API_BASE_URL}/api/workflows/${segment(workflowId)}`;
const proposalUrl = (workflowId: string, proposalId: string) => `${workflowUrl(workflowId)}/proposals/${segment(proposalId)}`;

function jsonRequest(method: string, body: unknown, signal?: AbortSignal): RequestInit {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal };
}

/** The M2 proposal kinds created through POST /workflows/{wid}/proposals. Only REACTIVATE carries stages. */
export type RecoveryProposalRequest =
  | { kind: "RESTORE_VERSION"; expected_workflow_revision: number; restore_target_version: number; note?: string }
  | { kind: "RESET_TO_DEFAULT"; expected_workflow_revision: number; note?: string }
  | { kind: "DEACTIVATE"; expected_workflow_revision: number; note?: string }
  | { kind: "REACTIVATE"; expected_workflow_revision: number; stages: WorkflowStage[]; note?: string };

function withNote<T extends object>(body: T, note?: string | null): T & { note?: string } {
  const trimmed = note?.trim();
  return trimmed ? { ...body, note: trimmed } : body;
}

export function restoreVersionRequest(workflowRevision: number, version: number, note?: string | null): RecoveryProposalRequest {
  return withNote({ kind: "RESTORE_VERSION" as const, expected_workflow_revision: workflowRevision, restore_target_version: version }, note);
}

export function resetToDefaultRequest(workflowRevision: number, note?: string | null): RecoveryProposalRequest {
  return withNote({ kind: "RESET_TO_DEFAULT" as const, expected_workflow_revision: workflowRevision }, note);
}

export function deactivateRequest(workflowRevision: number, note?: string | null): RecoveryProposalRequest {
  return withNote({ kind: "DEACTIVATE" as const, expected_workflow_revision: workflowRevision }, note);
}

export function reactivateRequest(workflowRevision: number, stages: WorkflowStage[], note?: string | null): RecoveryProposalRequest {
  return withNote({ kind: "REACTIVATE" as const, expected_workflow_revision: workflowRevision, stages }, note);
}

/** POST /workflows/{wid}/proposals (201) with an M2 kind. */
export async function createRecoveryProposal(workflowId: string, body: RecoveryProposalRequest): Promise<ProposalResponse> {
  return parseResponse(await authenticatedFetch(`${workflowUrl(workflowId)}/proposals`, jsonRequest("POST", body)));
}

export function emergencyFallbackRequest(
  workflowRevision: number, reason: string, target: { version: number } | "DEFAULT",
): EmergencyFallbackRequest {
  return target === "DEFAULT"
    ? { reason: reason.trim(), expected_workflow_revision: workflowRevision, target: "DEFAULT" }
    : { reason: reason.trim(), expected_workflow_revision: workflowRevision, target: "VERSION", target_version: target.version };
}

/** POST /workflows/{wid}/emergency-fallback: the Director's single-actor exception. Never retried. */
export async function emergencyFallback(workflowId: string, body: EmergencyFallbackRequest): Promise<EmergencyFallbackResponse> {
  return parseResponse(await authenticatedFetch(`${workflowUrl(workflowId)}/emergency-fallback`, jsonRequest("POST", body)));
}

/** POST /workflows/{wid}/proposals/{pid}/release: the draft becomes WITHDRAWN; its content is kept. */
export async function releaseDraft(workflowId: string, proposalId: string, body: ReleaseDraftRequest): Promise<ProposalResponse> {
  return parseResponse(await authenticatedFetch(`${proposalUrl(workflowId, proposalId)}/release`, jsonRequest("POST", body)));
}

/** POST /workflows/{wid}/proposals/{pid}/copy: a new DRAFT authored by the copier. */
export async function copyProposal(workflowId: string, proposalId: string, body: CopyProposalRequest): Promise<ProposalResponse> {
  return parseResponse(await authenticatedFetch(`${proposalUrl(workflowId, proposalId)}/copy`, jsonRequest("POST", body)));
}

/** GET /workflows/{wid}/versions/{n}: hot, then cold. */
export async function fetchWorkflowVersion(workflowId: string, version: number, signal?: AbortSignal): Promise<WorkflowVersionResponse> {
  return parseResponse(await authenticatedFetch(`${workflowUrl(workflowId)}/versions/${version}`, { signal }));
}

/** GET /workflows/notices. Null means notices are not available on this server (404). */
export async function fetchNotices(signal?: AbortSignal): Promise<NoticeListResponse | null> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/workflows/notices`, { signal });
  if (response.status === 404) return null;
  return parseResponse<NoticeListResponse>(response);
}

/** POST /workflows/notices/{id}/acknowledge (HR only). The response body is not needed by the UI. */
export async function acknowledgeNotice(noticeId: string, body: AcknowledgeNoticeRequest): Promise<unknown> {
  return parseResponse(await authenticatedFetch(
    `${API_BASE_URL}/api/workflows/notices/${segment(noticeId)}/acknowledge`, jsonRequest("POST", body),
  ));
}

/** User-scoped keys under the workflow list key, so a workflow refresh also refreshes these. */
export const workflowRecoveryQueryKeys = {
  notices: (userId: string) => ["auth", userId, "workflows", "notices"] as const,
  version: (userId: string, workflowId: string, version: number) =>
    ["auth", userId, "workflows", "version", workflowId, version] as const,
};

export function fallbackReasonValid(reason: string): boolean {
  const length = reason.trim().length;
  return length >= FALLBACK_REASON_MIN && length <= FALLBACK_REASON_MAX;
}

export function releaseReasonValid(reason: string): boolean {
  const length = reason.trim().length;
  return length >= 1 && length <= RELEASE_REASON_MAX;
}

const DAY_MS = 24 * 60 * 60 * 1000;

/** Whole days since the draft's last activity (UI shaping only). */
export function daysSinceActivity(proposal: Pick<ProposalResponse, "last_activity_at">, now: number = Date.now()): number {
  const at = Date.parse(proposal.last_activity_at);
  return Number.isNaN(at) ? 0 : Math.floor((now - at) / DAY_MS);
}

/**
 * UI shaping only: offer Release to an HR user who is not the author once the draft has been idle for
 * 14 days. The backend decides (it also releases drafts whose author's account is gone).
 */
export function offerDraftRelease(
  proposal: Pick<ProposalResponse, "state" | "author_id" | "last_activity_at">,
  actor: { user_id: string; capabilities: readonly string[] },
  now: number = Date.now(),
): boolean {
  return proposal.state === "DRAFT"
    && actor.capabilities.includes("POLICY_MUTATE")
    && proposal.author_id !== actor.user_id
    && daysSinceActivity(proposal, now) >= DRAFT_RELEASE_AFTER_DAYS;
}

/** Withdrawn (including released), stale and legacy drafts can be copied into a new draft. */
export function copyableProposal(item: Pick<DecidedProposalSummary, "state" | "origin">): boolean {
  return item.state === "WITHDRAWN" || item.state === "STALE" || item.origin === "PRE_GOVERNANCE_DRAFT";
}

/** Recovery kinds have backend-computed content and are never edited in the UI. */
export function fixedContentKind(kind: ProposalKind): boolean {
  return kind === "RESTORE_VERSION" || kind === "RESET_TO_DEFAULT" || kind === "DEACTIVATE";
}

export const PROPOSAL_KIND_LABEL: Record<ProposalKind, string> = {
  CHANGE: "Change",
  RESTORE_VERSION: "Restore an earlier version",
  RESET_TO_DEFAULT: "Reset to default",
  DEACTIVATE: "Deactivate",
  REACTIVATE: "Reactivate",
};

export const SAFE_TARGET_EXPLANATION =
  "What gets published is the safe target: the chosen content plus every required step and field already in force. No required obligation is dropped.";

export const PROPOSAL_KIND_EXPLANATION: Record<ProposalKind, string> = {
  CHANGE: "Edits the workflow's stages and fields.",
  RESTORE_VERSION: `Brings back an earlier published version. ${SAFE_TARGET_EXPLANATION} One Director must approve it.`,
  RESET_TO_DEFAULT: `Returns the workflow to its default content. ${SAFE_TARGET_EXPLANATION} One Director must approve it.`,
  DEACTIVATE:
    "Stops new runs of this workflow. Existing runs keep their stages and stay completable (answer, confirm and view). The required baseline is kept. One Director must approve it.",
  REACTIVATE:
    "Publishes a new version so new runs can start again. Its stages must keep every required step and field. One Director must approve it.",
};

/** Plain provenance wording. Only a governed approval is ever called approved (ADR-017 §1.4). */
export function provenanceText(item: VersionProvenance): string {
  switch (item.origin) {
    case "GOVERNED_APPROVAL":
      return `Proposed by ${item.author_id ?? "unknown"} · approved by ${item.approved_by ?? "unknown"}`;
    case "PRE_GOVERNANCE_DIRECTOR_ACTIVATION":
      return `Pre-governance · activated by ${item.activated_by ?? "unknown"}`;
    case "EMERGENCY_FALLBACK":
      return `Emergency fallback by ${item.activated_by ?? "a Director"} — not approved`;
  }
}

/**
 * POST /api/clm/cases/{case_id}/workflow/applicability-escalation (ADR-018 §3.5 F6): the audited
 * "Apply all conditional steps". Add-only; the backend reauthorizes inside the case lock. Never retried.
 */
export async function escalateApplicability(caseId: string, body: ApplicabilityEscalationRequest): Promise<unknown> {
  return parseResponse(await authenticatedFetch(
    `${API_BASE_URL}/api/clm/cases/${segment(caseId)}/workflow/applicability-escalation`, jsonRequest("POST", body),
  ));
}

export const ESCALATION_REASON_MIN = 10;
export const ESCALATION_REASON_MAX = 240;
