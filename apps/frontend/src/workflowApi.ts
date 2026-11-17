import { API_BASE_URL, ApiError, authenticatedFetch, parseResponse } from "./api";

export type WorkflowCaseSource = "EXISTING_CASE" | "NEW_CASE";

export type WorkflowFieldKind = "TEXT" | "DATE" | "NUMBER" | "YES_NO" | "CHOICE";

export interface WorkflowField {
  field_id: string;
  label: string;
  kind: WorkflowFieldKind;
  required: boolean;
  options: string[];
  autofill: boolean;
  document_label: string | null;
  case_data_key?: string | null;
}

export interface WorkflowStage {
  stage_id: string;
  name: string;
  fields: WorkflowField[];
  after_node_id: string | null;
}

export interface WorkflowDetail {
  workflow_id: string;
  name: string;
  use_case: string;
  country: string;
  case_source: WorkflowCaseSource;
  revision: number;
  is_onboarding: boolean;
  status: "ACTIVE" | "DRAFT";
  active_version: number | null;
  draft_stages: WorkflowStage[];
  audit: Array<{ occurred_at: string; actor_id: string; action: string; summary: string }>;
  locked_stages: Array<{ node_id: string; label: string }>;
}

export interface WorkflowRunField {
  field_id: string;
  label: string;
  kind: WorkflowFieldKind;
  required: boolean;
  options: string[];
  value: string | null;
  source: "MANUAL" | "DOCUMENT" | "CASE" | null;
  page_number: number | null;
}

export interface WorkflowRunStage {
  stage_id: string;
  name: string;
  after_node_id: string | null;
  status: "COMPLETE" | "OPEN" | "LOCKED";
  blocks_send: boolean;
  confirmed_by: string | null;
  confirmed_at: string | null;
  fields: WorkflowRunField[];
}

export interface WorkflowRun {
  run_id: string;
  case_id: string | null;
  workflow_id: string;
  workflow_name: string;
  use_case: string;
  workflow_version: number;
  revision: number;
  is_onboarding: boolean;
  is_complete: boolean;
  stages: WorkflowRunStage[];
}

export interface StartableWorkflow {
  workflow_id: string;
  name: string;
  case_source: WorkflowCaseSource;
}

export interface WorkflowRunItem {
  case_id: string | null;
  company: string;
  registration_id: string;
  run: WorkflowRun;
}

export interface CaseWorkflows {
  onboarding: WorkflowRun | null;
  runs: WorkflowRun[];
}

function jsonRequest(method: string, body: unknown): RequestInit {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}

/** Null means workflow management is switched off on this server. */
export async function fetchWorkflows(signal?: AbortSignal): Promise<WorkflowDetail[] | null> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/workflows`, { signal });
  if (response.status === 404) return null;
  return parseResponse<WorkflowDetail[]>(response);
}

export async function createWorkflow(body: { name: string; use_case: string; country: string; case_source: WorkflowCaseSource }): Promise<WorkflowDetail> {
  return parseResponse(await authenticatedFetch(`${API_BASE_URL}/api/workflows`, jsonRequest("POST", body)));
}

export async function saveWorkflowDraft(workflow: WorkflowDetail, stages: WorkflowStage[]): Promise<WorkflowDetail> {
  return parseResponse(await authenticatedFetch(
    `${API_BASE_URL}/api/workflows/${workflow.workflow_id}/draft`,
    jsonRequest("PUT", { expected_revision: workflow.revision, stages }),
  ));
}

export async function fetchStartableWorkflows(signal?: AbortSignal): Promise<StartableWorkflow[]> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/workflows/startable`, { signal });
  if (response.status === 404) return [];
  return parseResponse<StartableWorkflow[]>(response);
}

export async function fetchWorkflowRuns(workflowId: string, signal?: AbortSignal): Promise<WorkflowRunItem[]> {
  return parseResponse(await authenticatedFetch(`${API_BASE_URL}/api/workflows/${workflowId}/runs`, { signal }));
}

export async function createWorkflowCase(workflowId: string, body: {
  legal_name: string; registration_id: string; jurisdiction: string | null; priority: number | null;
}): Promise<WorkflowRunItem> {
  return parseResponse(await authenticatedFetch(`${API_BASE_URL}/api/workflows/${workflowId}/new-cases`, jsonRequest("POST", body)));
}

/** Read for autofill suggestions only; the document is not kept. */
export async function uploadWorkflowCaseDocument(run: WorkflowRun, file: File): Promise<WorkflowRun> {
  return parseResponse(await authenticatedFetch(`${API_BASE_URL}/api/workflows/${run.workflow_id}/runs/${run.run_id}/documents`, {
    method: "POST",
    headers: { "Content-Type": file.type || "application/octet-stream", "X-Document-Name": file.name },
    body: file,
  }));
}

export async function deleteWorkflowCase(run: WorkflowRun): Promise<void> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/workflows/${run.workflow_id}/runs/${run.run_id}`, { method: "DELETE" });
  if (!response.ok) await parseResponse(response);
}

export async function startWorkflowRun(workflowId: string, caseId: string): Promise<WorkflowRun> {
  return parseResponse(await authenticatedFetch(
    `${API_BASE_URL}/api/workflows/${workflowId}/runs`,
    jsonRequest("POST", { case_id: caseId }),
  ));
}

/** Null means the feature is off or the case is unavailable; the case page then shows nothing extra. */
export async function fetchCaseWorkflows(caseId: string, signal?: AbortSignal): Promise<CaseWorkflows | null> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/clm/zero-touch/cases/${caseId}/workflows`, { signal });
  if (response.status === 404) return null;
  return parseResponse<CaseWorkflows>(response);
}

function stageUrl(caseId: string | null, run: WorkflowRun, stageId: string, action: string): string {
  const base = caseId === null
    ? `${API_BASE_URL}/api/workflows/${run.workflow_id}/runs/${run.run_id}`
    : `${API_BASE_URL}/api/clm/zero-touch/cases/${caseId}/workflows/runs/${run.run_id}`;
  return `${base}/stages/${stageId}/${action}`;
}

export async function saveStageAnswers(caseId: string | null, run: WorkflowRun, stageId: string, values: Record<string, string>): Promise<WorkflowRun> {
  return parseResponse(await authenticatedFetch(
    stageUrl(caseId, run, stageId, "answers"),
    jsonRequest("PUT", { expected_revision: run.revision, values }),
  ));
}

export async function confirmStage(caseId: string | null, run: WorkflowRun, stageId: string): Promise<WorkflowRun> {
  return parseResponse(await authenticatedFetch(
    stageUrl(caseId, run, stageId, "confirm"),
    jsonRequest("POST", { expected_revision: run.revision }),
  ));
}

const WORKFLOW_ERROR_MESSAGES: Record<string, string> = {
  WORKFLOW_PUBLICATION_FROZEN:
    "Publishing is paused while approval governance is introduced. Your draft is kept.",
};

export function workflowErrorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return "That did not work. Please try again.";
  return (error.code && WORKFLOW_ERROR_MESSAGES[error.code]) || error.message;
}

export const workflowQueryKeys = {
  list: (userId: string) => ["auth", userId, "workflows"] as const,
  startable: (userId: string) => ["auth", userId, "workflows", "startable"] as const,
  tabCases: (userId: string) => ["auth", userId, "workflows", "tab-cases"] as const,
  runs: (userId: string, workflowId: string) => ["auth", userId, "workflows", "runs", workflowId] as const,
  caseRuns: (userId: string, caseId: string) => ["auth", userId, "workflows", "case", caseId] as const,
};
