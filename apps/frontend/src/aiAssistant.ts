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

/** A retrieved knowledge entry the answer could use; `cited` = the answer names its tag. */
export interface AiAssistantSource {
  tag: string;
  kind: "guidance" | "resolution";
  version: number;
  /** The checked entry title, or a neutral label such as "Guidance G1". */
  title: string;
  approved_at: string | null;
  illustrative: boolean;
  fallback: boolean;
  cited: boolean;
}

export interface AiAssistantAnswer {
  answer: string;
  answered_by: "model" | "case_data";
  model: string | null;
  notice: string | null;
  suggested_questions: string[];
  /** Model answers only: why sentences were left out (reason codes) and disclosures added. */
  checks?: { removed: string[]; disclosures: string[] } | null;
  /** Retrieved guidance [G] and past cases [P]. */
  sources?: AiAssistantSource[];
  knowledge?: { confidence: "high" | "low" | "none"; degraded: boolean } | null;
  /** The server's record of this answer; feedback sends it back (none for small talk). */
  answer_id?: string | null;
  /** A fixed small-talk reply, which never has a record. */
  small_talk?: boolean;
}

/** The question body, with the ids of earlier answers in this chat (the server checks them). */
const chatBody = (message: string, history: AiAssistantTurn[], earlierAnswerIds: string[]) =>
  earlierAnswerIds.length ? { message, history, earlier_answer_ids: earlierAnswerIds } : { message, history };

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
    let message = httpErrorMessage(response.status);
    try {
      const payload = await readJsonBody(response, MAX_ERROR_BODY_BYTES, signal);
      const detail = payload && typeof payload === "object" && "detail" in payload
        ? payload.detail : null;
      const candidate = detail && typeof detail === "object" && "message" in detail
        ? detail.message : null;
      // Only fixed messages emitted by this read-only service are trusted for display.
      // A length cap alone cannot sanitize provider diagnostics or proxy error pages.
      if (typeof candidate === "string" && candidate.length <= 256
        && SAFE_ERROR_MESSAGES.has(candidate)) message = candidate;
    } catch {
      signal?.throwIfAborted();
      // Keep the safe status-specific fallback, never the body or parser exception.
    }
    throw new AiAssistantError(message, response.status);
  }
  return response;
}

// Error payloads contain only a code/message pair. Budget bytes before UTF-8/JSON
// decoding, independently of Content-Length. Brief/chat JSON uses the existing
// compatibility line budget; both finite JSON reads have a 5s post-header deadline.
const MAX_ERROR_BODY_BYTES = 16 * 1024;
const MAX_JSON_BODY_BYTES = 128 * 1024;
const JSON_BODY_DEADLINE_MS = 5000;
const SAFE_ERROR_MESSAGES = new Set([
  "Please sign in again.",
  "This case was not found.",
  "Request origin not allowed.",
  "The onboarding app could not be reached.",
  "The onboarding app could not provide this case.",
  "The onboarding app returned an unreadable reply.",
  "The onboarding app returned an unexpected reply.",
  // Fixed knowledge-review messages (apps/assistant/ai_assistant/knowledge_api.py).
  "You are not allowed to do this.",
  "No such entry.",
  "You cannot approve or reject an entry you wrote or edited.",
  "This entry has changed or was already decided. Refresh and try again.",
  "This change is not allowed.",
  "No such enhancement request.",
  "This request was already handled. Refresh and try again.",
  "Confirm that you are publishing this entry as its only reviewer.",
]);

function httpErrorMessage(status: number): string {
  switch (status) {
    case 401: return "Please sign in again.";
    case 403: return "The AI assistant request was not allowed.";
    case 404: return "This case was not found.";
    case 502: return "The onboarding app could not be reached.";
    case 503: return "The AI assistant service is unavailable right now.";
    default: return "The AI assistant could not answer right now.";
  }
}

async function readJsonBody(response: Response, maxBytes: number, signal?: AbortSignal): Promise<unknown> {
  if (!response.body) throw new AiAssistantError("The AI assistant could not read its answer.", response.status);
  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8", { fatal: true });
  const parts: string[] = [];
  let totalBytes = 0;
  let timedOut = false;
  const deadline = performance.now() + JSON_BODY_DEADLINE_MS;
  const cancel = () => { void reader.cancel().catch(() => undefined); };
  const timeout = setTimeout(() => { timedOut = true; cancel(); }, JSON_BODY_DEADLINE_MS);
  signal?.addEventListener("abort", cancel, { once: true });
  try {
    for (;;) {
      signal?.throwIfAborted();
      if (timedOut || performance.now() >= deadline) throw new Error("body deadline");
      const { value, done } = await reader.read();
      signal?.throwIfAborted();
      if (timedOut || performance.now() >= deadline) throw new Error("body deadline");
      if (done) return JSON.parse(parts.join("") + decoder.decode()) as unknown;
      totalBytes += value.byteLength;
      if (totalBytes > maxBytes) {
        throw new AiAssistantError("The AI assistant response limit was exceeded.", response.status);
      }
      parts.push(decoder.decode(value, { stream: true }));
    }
  } catch (error) {
    signal?.throwIfAborted();
    if (error instanceof AiAssistantError) throw error;
    throw new AiAssistantError("The AI assistant could not read its answer.", response.status);
  } finally {
    clearTimeout(timeout);
    signal?.removeEventListener("abort", cancel);
    // Cancellation is initiated before unlocking, but an uncooperative source's
    // cancel promise cannot keep completion/abort/deadline indefinitely pending.
    cancel();
    reader.releaseLock();
  }
}

async function request<T>(path: string, body: unknown | undefined, signal?: AbortSignal): Promise<T> {
  return await readJsonBody(await send(path, body, signal), MAX_JSON_BODY_BYTES, signal) as T;
}

export function fetchAiAssistantBrief(caseId: string, signal?: AbortSignal): Promise<AiAssistantBrief> {
  return request<AiAssistantBrief>(`/cases/${encodeURIComponent(caseId)}/brief`, undefined, signal);
}

export function askAiAssistant(
  caseId: string,
  message: string,
  history: AiAssistantTurn[],
  signal?: AbortSignal,
  earlierAnswerIds: string[] = [],
): Promise<AiAssistantAnswer> {
  return request<AiAssistantAnswer>(
    `/cases/${encodeURIComponent(caseId)}/chat`,
    chatBody(message, history, earlierAnswerIds),
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
  earlierAnswerIds: string[] = [],
): Promise<AiAssistantAnswer> {
  const response = await send(
    `/cases/${encodeURIComponent(caseId)}/chat/stream`,
    chatBody(message, history, earlierAnswerIds),
    signal,
  );
  const isStream = (response.headers.get("Content-Type") ?? "").includes("ndjson");
  if (!response.body) throw new AiAssistantError("The AI assistant could not answer right now.");
  // Additional browser containment above the service's 64 KiB model text cap.
  const maxLineBytes = 128 * 1024;
  const maxResponseBytes = 2 * 1024 * 1024;
  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8", { fatal: true });
  let parts: string[] = [];
  let lineBytes = 0;
  let totalBytes = 0;
  const aborted = () => { void reader.cancel().catch(() => undefined); };
  signal?.addEventListener("abort", aborted, { once: true });

  function parseLine(line: string): AiAssistantAnswer | null {
    signal?.throwIfAborted();
    if (!line.trim()) return null;
    const event = JSON.parse(line) as StreamEvent;
    if (!event || typeof event !== "object") throw new Error("invalid event");
    if (event.type === "text" && typeof event.text === "string") {
      signal?.throwIfAborted();
      onText(event.text);
      return null;
    }
    if ((event.type === "done" || !isStream) && "answer" in event
      && typeof event.answer === "string"
      && ["model", "case_data"].includes(event.answered_by)
      && (event.model === null || typeof event.model === "string")
      && (event.notice === null || typeof event.notice === "string")
      && (event.answer_id == null || typeof event.answer_id === "string")
      && (event.small_talk === undefined || typeof event.small_talk === "boolean")
      && Array.isArray(event.suggested_questions)
      && event.suggested_questions.every((question) => typeof question === "string")) {
      const { type: _type, ...answer } = event;
      return answer;
    }
    throw new Error("invalid event");
  }

  try {
    for (;;) {
      signal?.throwIfAborted();
      const { value, done } = await reader.read();
      signal?.throwIfAborted();
      if (done) {
        const tail = decoder.decode();
        if (!isStream && (lineBytes || tail)) {
          const answer = parseLine(parts.join("") + tail);
          if (answer) return answer;
        }
        throw new AiAssistantError("The AI assistant stopped before finishing its answer.");
      }
      totalBytes += value.byteLength;
      if (totalBytes > maxResponseBytes) {
        throw new AiAssistantError("The AI assistant response limit was exceeded.");
      }
      // Scan incoming bytes once, including one-byte fragments of a retained line.
      let start = 0;
      while (start < value.byteLength) {
        const newline = value.indexOf(10, start);
        const end = newline < 0 ? value.byteLength : newline + 1;
        lineBytes += end - start;
        if (lineBytes > maxLineBytes) {
          throw new AiAssistantError("The AI assistant response line limit was exceeded.");
        }
        parts.push(decoder.decode(value.subarray(start, end), { stream: true }));
        if (newline >= 0) {
          const answer = parseLine(parts.join("") + decoder.decode());
          parts = [];
          lineBytes = 0;
          if (answer) return answer;
        }
        start = end;
      }
    }
  } catch (error) {
    signal?.throwIfAborted();
    if (error instanceof AiAssistantError) throw error;
    throw new AiAssistantError("The AI assistant could not read its answer.");
  } finally {
    signal?.removeEventListener("abort", aborted);
    await reader.cancel().catch(() => undefined);
    reader.releaseLock();
  }
}

// --- Knowledge loop: RM feedback and Director review --------------------------------------
// Permissions are decided by the backend on every call; these only carry the request.

export interface AiAssistantFeedbackResult {
  feedback_id: number;
  message: string;
}

/**
 * "Yes, helpful" records the rating; "Not helpful" needs a note (the backend refuses an empty
 * one) and becomes an enhancement request for a Director. Both send the answer's `answer_id`
 * when the answer has a record; without one the Director sees only the note.
 */
export function sendAiAssistantFeedback(
  caseId: string,
  feedback: { helpful: boolean; note: string; answer_id?: string },
  signal?: AbortSignal,
): Promise<AiAssistantFeedbackResult> {
  return request<AiAssistantFeedbackResult>(`/cases/${encodeURIComponent(caseId)}/feedback`, feedback, signal);
}

export interface KnowledgeAccess {
  user_id: string | null;
  can_review: boolean;
  can_edit_guidance: boolean;
  /** POC single-reviewer mode (D-083): a reviewer may publish an entry they wrote, once confirmed. */
  single_reviewer?: boolean;
}

export interface KnowledgeEntry {
  entry_id: string;
  key: string;
  version: number;
  kind: "guidance" | "resolution";
  status: "draft" | "pending_review" | "approved" | "rejected" | "retired";
  title: string;
  body: string;
  blocker_codes: string[];
  fields: string[];
  stages: string[];
  follow_ups: string[];
  visibility: { roles: string[]; teams: string[] };
  replaces: string | null;
  /** The version a reviewer's edit was made from (null for an original). */
  revises: number | null;
  author: string;
  approver: string | null;
  approved_at: string | null;
  created_at: string | null;
  source_ref: string | null;
  illustrative: boolean;
  /** What this version says; edits and decisions send it back so they apply to it only. */
  content_hash: string;
  /** Approved by someone who wrote or edited it (single-reviewer mode, D-083). */
  single_reviewer: boolean;
  /** A Director's fix whose text was started from the request's answer record. */
  started_from_answer?: boolean;
}

/** An enhancement request: an RM's "Not helpful" note, redacted, with its case context. */
export interface KnowledgeGap {
  id: number;
  note: string;
  blocker_codes: string[];
  fields: string[];
  stages: string[];
  created_at: string;
  /** The record of the answer the RM rated (none when it could not be saved, or from before
   * answer records), and the question asked. */
  answer_id?: string | null;
  question?: string | null;
}

/** Where an allowed line comes from: a fixed catalog line, one filled from the case, or knowledge. */
export type AllowedLineSource = "policy" | "case" | "knowledge";

/** The server's record of one answer: what the AI was given, chose and left out. */
export interface AnswerRecord {
  answer_id: string;
  case_id: string;
  created_at: string;
  /** The question as the service used it. */
  question: string;
  earlier_answer_ids: string[];
  case_snapshot: {
    blocker_codes: string[];
    stage: string | null;
    steps_done: number | null;
    steps_total: number | null;
    facts_hash: string;
  };
  knowledge: {
    confidence: "high" | "low" | "none" | null;
    degraded: boolean | null;
    /** The minimum score an entry of each kind needs to be used (missing on the earliest records). */
    thresholds?: { guidance: number; resolution: number };
    entries: {
      tag: string;
      kind: "guidance" | "resolution";
      entry_id: string;
      version: number;
      score: number;
      parts: Record<string, number>;
      fallback: boolean;
    }[];
  };
  /** Each allowed line and where it comes from (the earliest records kept plain lines). */
  allowed_lines: ({ text: string; source: AllowedLineSource } | string)[];
  chosen_lines: string[];
  dropped_lines: string[];
  /** The answer as the RM saw it (a case-data answer with names and identifiers removed). */
  shown_answer: string;
  result: {
    answered_by: "model" | "case_data";
    notices: string[];
    fallback_reason: "model_unavailable" | "nothing_allowed" | "cut_short" | null;
    left_out: number;
    model: string | null;
    elapsed_ms: number;
  };
  rated: boolean;
}

export interface KnowledgeReviewQueue {
  pending: KnowledgeEntry[];
  gaps: KnowledgeGap[];
}

export interface KnowledgeStats {
  entries: Record<string, number>;
  feedback: {
    total: number;
    helpful: number;
    not_helpful: number;
    helpful_rate: number | null;
    open_gaps: number;
  };
  /** Confidence by topic: helpful and not-helpful ratings per blocker code. */
  by_topic: Record<string, { helpful: number; not_helpful: number }>;
}

/** A reviewer's edit; `replaces: null` clears what the version replaces, leaving it out keeps it. */
export type KnowledgeEdit = Partial<
  Pick<KnowledgeEntry, "title" | "body" | "follow_ups" | "replaces"> & { visibility: KnowledgeEntry["visibility"] }
>;

const entryPath = (entryId: string, version: number) =>
  `/knowledge/entries/${encodeURIComponent(entryId)}/versions/${version}`;

export const fetchKnowledgeAccess = (signal?: AbortSignal) =>
  request<KnowledgeAccess>("/knowledge/me", undefined, signal);
export const fetchKnowledgeReviews = (signal?: AbortSignal) =>
  request<KnowledgeReviewQueue>("/knowledge/reviews", undefined, signal);
export const fetchKnowledgeStats = (signal?: AbortSignal) =>
  request<KnowledgeStats>("/knowledge/stats", undefined, signal);
/** Every approved entry the reviewer may see (guidance and past resolutions). */
export const fetchApprovedEntries = (signal?: AbortSignal) =>
  request<KnowledgeEntry[]>("/knowledge/entries", undefined, signal);
// An edit is saved as a new version that a different reviewer must approve.
export const editKnowledgeEntry = (entry: KnowledgeEntry, edit: KnowledgeEdit) =>
  request<KnowledgeEntry>(`${entryPath(entry.entry_id, entry.version)}/edit`, {
    content_hash: entry.content_hash,
    ...edit,
  });
// Approve and Reject apply to exactly the content shown (its hash). `confirmed`: the reviewer
// saw the final text and confirmed publishing it; in single-reviewer mode the backend needs
// it before an author or editor can publish their own entry.
export const decideKnowledgeEntry = (entry: KnowledgeEntry, approve: boolean, notes: string, confirmed = false) =>
  request<KnowledgeEntry>(`${entryPath(entry.entry_id, entry.version)}/decision`, {
    approve,
    content_hash: entry.content_hash,
    notes,
    confirm_single_reviewer: confirmed,
  });
/** A Director's fix for an enhancement request: a past case or a guidance change. */
export type KnowledgeFix = (
  | { kind: "resolution"; title: string; body: string; follow_ups: string[] }
  | { kind: "guidance"; title: string; body: string; source_ref: string; entry_id?: string }
) & { started_from_answer?: boolean };

/** Where a fix can start: a title from the blocker type and the AI's left-out lines, redacted. */
export interface KnowledgeFixStart {
  title: string;
  lines: string[];
}

// Read only (a logged view of the record); "not found" for a request without one.
export const fetchFixStart = (feedbackId: number, signal?: AbortSignal) =>
  request<KnowledgeFixStart>(`/knowledge/feedback/${feedbackId}/fix-start`, undefined, signal);

// Saves the fix, linked to the request, for review like any other entry: publishing it
// resolves the request, rejecting it opens the request again.
export const draftFromKnowledgeGap = (feedbackId: number, fix: KnowledgeFix) =>
  request<KnowledgeEntry>(`/knowledge/feedback/${feedbackId}/draft`, fix);
export const closeKnowledgeGap = (feedbackId: number, reason: string) =>
  request<{ status: string }>(`/knowledge/feedback/${feedbackId}/close`, { reason });
// "What happened": the record linked to a request, or one of the earlier answers it names.
// Every view is logged by the service.
export const fetchGapAnswer = (feedbackId: number, signal?: AbortSignal) =>
  request<AnswerRecord>(`/knowledge/feedback/${feedbackId}/answer`, undefined, signal);
export const fetchGapEarlierAnswer = (feedbackId: number, answerId: string, signal?: AbortSignal) =>
  request<AnswerRecord>(
    `/knowledge/feedback/${feedbackId}/answers/${encodeURIComponent(answerId)}`,
    undefined,
    signal,
  );
