// Client for the separate Onboarding Copilot service (apps/assistant), reached at
// /api/assistant so the browser includes the session cookie (which is scoped to /api).
// The browser's own session cookie goes with each call; the copilot forwards it to the
// CLM backend, which stays the authority for what this user may see.

const COPILOT_BASE_URL = import.meta.env.VITE_COPILOT_BASE_URL ?? "";

export interface CopilotBrief {
  company: string | null;
  message: string;
  suggested_questions: string[];
  blocker_count: number;
  steps_done: number;
  steps_total: number;
}

export interface CopilotTurn {
  role: "user" | "assistant";
  content: string;
}

export interface CopilotAnswer {
  answer: string;
  answered_by: "model" | "case_data";
  model: string | null;
  notice: string | null;
  suggested_questions: string[];
}

export class CopilotError extends Error {}

async function request<T>(path: string, body: unknown | undefined, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await globalThis.fetch(`${COPILOT_BASE_URL}/api/assistant${path}`, body === undefined
      ? { method: "GET", credentials: "include", signal }
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
          credentials: "include",
          signal,
        });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new CopilotError("The copilot service is not running.");
  }
  if (!response.ok) {
    let message = "The copilot could not answer right now.";
    try {
      const detail = (await response.json())?.detail;
      if (detail && typeof detail.message === "string") message = detail.message;
    } catch {
      // keep the generic message
    }
    throw new CopilotError(message);
  }
  return (await response.json()) as T;
}

export function fetchCopilotBrief(caseId: string, signal?: AbortSignal): Promise<CopilotBrief> {
  return request<CopilotBrief>(`/cases/${encodeURIComponent(caseId)}/brief`, undefined, signal);
}

export function askCopilot(
  caseId: string,
  message: string,
  history: CopilotTurn[],
  signal?: AbortSignal,
): Promise<CopilotAnswer> {
  return request<CopilotAnswer>(
    `/cases/${encodeURIComponent(caseId)}/chat`,
    { message, history },
    signal,
  );
}
