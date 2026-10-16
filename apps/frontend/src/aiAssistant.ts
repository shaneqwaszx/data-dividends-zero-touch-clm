// Client for the separate AI Assistant service (apps/assistant), reached at
// /api/assistant so the browser includes the session cookie (which is scoped to /api).
// The browser's own session cookie goes with each call; the AI assistant forwards it to the
// CLM backend, which stays the authority for what this user may see.

import { authenticatedFetch } from "./api";

const AI_ASSISTANT_BASE_URL = import.meta.env.VITE_AI_ASSISTANT_BASE_URL ?? "";

export interface AiAssistantBrief {
  company: string | null;
  message: string;
  suggested_questions: string[];
  blocker_count: number;
  steps_done: number;
  steps_total: number;
}

export interface AiAssistantTurn {
  role: "user" | "assistant";
  content: string;
}

export interface AiAssistantAnswer {
  answer: string;
  answered_by: "model" | "case_data";
  model: string | null;
  notice: string | null;
  suggested_questions: string[];
  /** Model answers only: why sentences were left out (reason codes) and disclosures added. */
  checks?: { removed: string[]; disclosures: string[] } | null;
}

export class AiAssistantError extends Error {
  constructor(message: string, readonly status: number | null = null) {
    super(message);
  }
}

async function send(path: string, body: unknown | undefined, signal?: AbortSignal): Promise<Response> {
  let response: Response;
  try {
    response = await authenticatedFetch(`${AI_ASSISTANT_BASE_URL}/api/assistant${path}`, body === undefined
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
    throw new AiAssistantError("The AI assistant service is not running.");
  }
  if (!response.ok) {
    let message = "The AI assistant could not answer right now.";
    try {
      const detail = (await response.json())?.detail;
      if (detail && typeof detail.message === "string") message = detail.message;
    } catch {
      // keep the generic message
    }
    throw new AiAssistantError(message, response.status);
  }
  return response;
}

async function request<T>(path: string, body: unknown | undefined, signal?: AbortSignal): Promise<T> {
  return (await (await send(path, body, signal)).json()) as T;
}

export function fetchAiAssistantBrief(caseId: string, signal?: AbortSignal): Promise<AiAssistantBrief> {
  return request<AiAssistantBrief>(`/cases/${encodeURIComponent(caseId)}/brief`, undefined, signal);
}

export function askAiAssistant(
  caseId: string,
  message: string,
  history: AiAssistantTurn[],
  signal?: AbortSignal,
): Promise<AiAssistantAnswer> {
  return request<AiAssistantAnswer>(
    `/cases/${encodeURIComponent(caseId)}/chat`,
    { message, history },
    signal,
  );
}

type StreamEvent = { type: "text"; text: string } | ({ type: "done" } & AiAssistantAnswer);

/**
 * Ask a question and show the answer while it is being written. The service sends one JSON
 * object per line: "text" events carry the checked answer so far (replace, don't append),
 * and a final "done" event carries the full answer, like askAiAssistant.
 */
export async function askAiAssistantStreaming(
  caseId: string,
  message: string,
  history: AiAssistantTurn[],
  onText: (textSoFar: string) => void,
  signal?: AbortSignal,
): Promise<AiAssistantAnswer> {
  const response = await send(`/cases/${encodeURIComponent(caseId)}/chat/stream`, { message, history }, signal);
  const isStream = (response.headers.get("Content-Type") ?? "").includes("ndjson");
  if (!isStream || !response.body) {
    const text = await response.text();
    const lines = text.split("\n").filter((line) => line.trim());
    const last = lines.length ? (JSON.parse(lines[lines.length - 1]) as Partial<StreamEvent>) : null;
    if (last && "answer" in last) return last as AiAssistantAnswer;
    throw new AiAssistantError("The AI assistant could not answer right now.");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    let newline = buffer.indexOf("\n");
    while (newline >= 0) {
      const line = buffer.slice(0, newline).trim();
      buffer = buffer.slice(newline + 1);
      if (line) {
        const event = JSON.parse(line) as StreamEvent;
        if (event.type === "text") onText(event.text);
        else if (event.type === "done") {
          const { type: _type, ...answer } = event;
          return answer;
        }
      }
      newline = buffer.indexOf("\n");
    }
    if (done) break;
  }
  throw new AiAssistantError("The AI assistant stopped before finishing its answer.");
}
