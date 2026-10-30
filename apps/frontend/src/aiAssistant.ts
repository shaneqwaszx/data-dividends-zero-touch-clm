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
  /** The conversation the answer joined (D-105); End conversation rates it. */
  conversation_id?: string | null;
  /** A fixed small-talk reply, which never has a record. */
  small_talk?: boolean;
}

/** The question body, with the ids of earlier answers in this chat and the conversation it
 * continues (the server checks both). */
const chatBody = (
  message: string,
  history: AiAssistantTurn[],
  earlierAnswerIds: string[],
  conversationId: string | null = null,
) => ({
  message,
  history,
  ...(earlierAnswerIds.length ? { earlier_answer_ids: earlierAnswerIds } : {}),
  ...(conversationId ? { conversation_id: conversationId } : {}),
});

export class AiAssistantError extends Error {
  constructor(message: string, readonly status: number | null = null) {
    super(message);
  }
}

async function send(
  path: string,
  body: unknown | undefined,
  signal?: AbortSignal,
  method: "GET" | "POST" | "PUT" | "DELETE" = body === undefined ? "GET" : "POST",
): Promise<Response> {
  let response: Response;
  try {
    response = await authenticatedFetch(`${AI_ASSISTANT_BASE_URL}/api/assistant${path}`, body === undefined
      ? { method, credentials: "include", signal }
      : {
          method,
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
  // Data access policy.
  "External models (OpenRouter and Anthropic) are restricted to verified synthetic cases on this deployment; this setting cannot change that. Nothing changed.",
  "The data access policy could not be read, so local models are restricted to verified synthetic cases until IT repairs it. Nothing changed.",
  "The data access policy changed since this view. Refresh and try again.",
  "Too many data access policy changes. Wait a few minutes and try again.",
  "Confirm that the local model may answer every case you are authorised to see. Nothing changed.",
  "No such entry.",
  "You cannot approve or reject an entry you wrote or edited.",
  "This entry has changed or was already decided. Refresh and try again.",
  "This change is not allowed.",
  "No such enhancement request.",
  "This request was already handled. Refresh and try again.",
  "Confirm that you are publishing this entry as its only reviewer.",
  // D-105: conversations.
  "No such conversation.",
  // Fixed model-management messages (apps/assistant/ai_assistant/model_admin.py).
  "Model management is not configured on this server.",
  "No such model profile.",
  "This model profile is not available for use.",
  "Remote models are not authorised for use in the CLM.",
  "The AI model is switched off on this server.",
  "Only a local loopback model can be qualified.",
  "The model could not be prepared on the server.",
  "Another qualification is running. Wait for it to finish.",
  "No such qualification run.",
  "The model settings changed since this view. Refresh and try again.",
  "This model has no passing qualification for the current configuration.",
  "Confirm that answer quality is not scored before activating.",
  "The model did not pass the connection test.",
  "There is no earlier model to roll back to.",
  "This model is already active.",
  "The paid qualification's question list and count are not configured on the server.",
  "Qualification is not available on this server.",
  // D-098: paid qualification confirmation, budget and escalation.
  "Confirm the number of paid calls this qualification may make. Nothing started.",
  "The spending limits do not leave room for every paid call this qualification may make. Nothing started.",
  "Paid calls are stopped until an operator reconciles the spending ledger. Nothing started.",
  "Run Test connection first so the OpenRouter key's own limit is checked. Nothing started.",
  "Run Test connection first so the Anthropic workspace and model are checked (a free model read). Nothing started.",
  "The OpenRouter key's own spending limit has no room. Only the key's owner can raise it at OpenRouter; it is not an HR setting. Nothing started.",
  "This configuration failed on answer quality. A developer or IT must change it before it is qualified again. Nothing started.",
  "A later qualification of this configuration failed on answer quality.",
  // D-095: the OpenRouter key (never echoed back).
  "That is not an OpenRouter API key. Nothing was saved.",
  "The OpenRouter key is set on the server (environment or .env) and cannot be changed here.",
  "There is no key entered here to clear.",
  "Too many key changes. Wait a few minutes and try again.",
  "This change must come from the AI Models page.",
  // D-096: HR spending controls (apps/assistant/ai_assistant/model_admin.py).
  "The daily limit must be a non-negative US$ amount and the call limit 1 to 200. Nothing changed.",
  "Confirm the new daily limit to raise it. Nothing changed.",
  "The OpenRouter key must have its own finite spending limit that never resets before the app's spending limits can be raised. Nothing changed.",
  "The spending limits changed since this view. Refresh and try again.",
  "Too many spending changes. Wait a few minutes and try again.",
  "The spending ledger is missing or not usable. Nothing changed.",
  "The lifetime limit cannot be below the key's opening usage. Nothing changed.",
  "Confirm the new lifetime limit to raise it. Nothing changed.",
  "The ledger must be reconciled with OpenRouter (no open call, no stop, usage accounted for) before the lifetime limit can be raised. Nothing changed.",
  "The OpenRouter key could not be checked. Nothing changed.",
  // D-102: Claude spending refusals.
  "Claude's daily limit must be more than US$0.00 and at most US$5.00, and its call limit 1 to 20. Nothing changed.",
  "Claude's lifetime limit must be above the workspace's opening usage and at most the lower of US$30.00 and the attested workspace limit. Nothing changed.",
  "Claude's ledger must be reconciled with the Anthropic Console's usage within the last day (no open call, no stop) before a Claude limit can be raised. Nothing changed.",
  "Claude is not fully configured on this server, so its limits can only be lowered. Nothing changed.",
  "Confirm the new call limit to raise it. Nothing changed.",
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

async function request<T>(
  path: string,
  body: unknown | undefined,
  signal?: AbortSignal,
  method?: "PUT" | "DELETE",
): Promise<T> {
  return await readJsonBody(await send(path, body, signal, method), MAX_JSON_BODY_BYTES, signal) as T;
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
 * ``onConnected`` runs when the service starts its reply: it sends that only after it has read
 * the case and prepared the question (the model has not been asked yet).
 */
export async function askAiAssistantStreaming(
  caseId: string,
  message: string,
  history: AiAssistantTurn[],
  onText: (textSoFar: string) => void,
  signal?: AbortSignal,
  earlierAnswerIds: string[] = [],
  onConnected?: () => void,
  conversationId: string | null = null,
): Promise<AiAssistantAnswer> {
  const response = await send(
    `/cases/${encodeURIComponent(caseId)}/chat/stream`,
    chatBody(message, history, earlierAnswerIds, conversationId),
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
  // After the reader exists, so an abort still cancels the body (the loop below throws).
  if (!signal?.aborted) onConnected?.();

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

/** Support's question without a case (D-105): answered from the approved rules and policy. */
export function askSupportAssistant(
  message: string,
  history: AiAssistantTurn[],
  signal?: AbortSignal,
): Promise<AiAssistantAnswer> {
  return request<AiAssistantAnswer>("/support/chat", { message, history }, signal);
}

// --- Conversations (D-105): End conversation, history and Support's review list ------------

export type Satisfaction = "very_satisfied" | "satisfied" | "neutral" | "unsatisfied" | "very_unsatisfied";
export type ConversationPriority = "high" | "medium" | "low";
export type ReviewStatus =
  | "open"
  | "no_review"
  | "draft"
  | "not_reviewed"
  | "awaiting_publish"
  | "fixed"
  | "closed";

export const SATISFACTION_LABELS: Record<Satisfaction, string> = {
  very_satisfied: "Very satisfied",
  satisfied: "Satisfied",
  neutral: "Neutral",
  unsatisfied: "Unsatisfied",
  very_unsatisfied: "Very unsatisfied",
};
/** What the form offers after "Was this issue resolved?" (the service checks it too). */
export const SATISFACTION_IF_RESOLVED: Satisfaction[] = ["very_satisfied", "satisfied", "neutral"];
export const SATISFACTION_IF_NOT_RESOLVED: Satisfaction[] = ["neutral", "unsatisfied", "very_unsatisfied"];

export interface ConversationSummary {
  conversation_id: string;
  case_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  ended_at: string | null;
  resolved: boolean | null;
  satisfaction: Satisfaction | null;
  priority: ConversationPriority | null;
  review_status: ReviewStatus;
  answers: number;
  team: string | null;
  user_id: string;
}

export interface ConversationTurn {
  answer_id: string;
  created_at: string;
  question: string;
  /** The answer as shown, with client details replaced by placeholders. */
  answer: string;
  notices: string[];
  answered_by: "model" | "case_data" | null;
}

export interface ConversationPage {
  items: ConversationSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface ConversationDetail extends ConversationSummary {
  comment: string | null;
  turns: ConversationTurn[];
}

/** Support's unsaved fix, kept on the conversation until it is saved or the request closed. */
export interface ConversationDraft {
  kind: "resolution" | "guidance";
  title: string;
  body: string;
  follow_ups: string[];
  entry_id: string | null;
  source_ref: string;
  /** When a guidance change applies (blank: the request's case topics). */
  blocker_codes?: string[];
  fields?: string[];
  stages?: string[];
}

/** Support's preview of an unsaved rule change on the conversation's question (D-105). */
export interface RuleTrial {
  question: string;
  answer: string;
  answered_by: "model" | "case_data";
  notice: string | null;
  tag: string | null;
  /** The change's sentences the AI may use on this case (they passed the checks). */
  offered_lines: string[];
  used: boolean;
}

export interface ReviewConversation extends ConversationDetail {
  close_reason: string | null;
  /** The enhancement request behind a conversation with a priority. */
  request: KnowledgeGap | null;
  draft: ConversationDraft | null;
  draft_by: string | null;
  draft_at: string | null;
}

export interface ReviewFilters {
  page: number;
  resolved?: boolean;
  satisfaction?: Satisfaction;
  status?: ReviewStatus;
}

const conversationPath = (conversationId: string) => `/conversations/${encodeURIComponent(conversationId)}`;

export const endConversation = (
  conversationId: string,
  rating: { resolved: boolean; satisfaction: Satisfaction; comment: string },
) => request<{ conversation_id: string; message: string }>(`${conversationPath(conversationId)}/end`, rating);
export const fetchMyConversations = (page: number, signal?: AbortSignal) =>
  request<ConversationPage>(`/conversations?page=${page}`, undefined, signal);
export const fetchMyConversation = (conversationId: string, signal?: AbortSignal) =>
  request<ConversationDetail>(conversationPath(conversationId), undefined, signal);

export function fetchReviewConversations(filters: ReviewFilters, signal?: AbortSignal): Promise<ConversationPage> {
  const query = new URLSearchParams({ page: String(filters.page) });
  if (filters.resolved !== undefined) query.set("resolved", String(filters.resolved));
  if (filters.satisfaction) query.set("satisfaction", filters.satisfaction);
  if (filters.status) query.set("status", filters.status);
  return request<ConversationPage>(`/knowledge/conversations?${query.toString()}`, undefined, signal);
}
export const fetchReviewConversation = (conversationId: string, signal?: AbortSignal) =>
  request<ReviewConversation>(`/knowledge${conversationPath(conversationId)}`, undefined, signal);
export const saveConversationDraft = (conversationId: string, draft: ConversationDraft) =>
  request<{ status: string; draft: ConversationDraft }>(
    `/knowledge${conversationPath(conversationId)}/draft`,
    draft,
    undefined,
    "PUT",
  );
export const tryRuleChange = (
  conversationId: string,
  change: {
    kind: "guidance" | "resolution";
    title: string;
    body: string;
    entry_id?: string | null;
    blocker_codes?: string[];
    fields?: string[];
    stages?: string[];
    question?: string;
  },
) => request<RuleTrial>(`/knowledge${conversationPath(conversationId)}/try`, change);
export const discardConversationDraft = (conversationId: string) =>
  request<{ status: string }>(`/knowledge${conversationPath(conversationId)}/draft`, undefined, undefined, "DELETE");

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
  /** The fix saved for this request, while it waits to be published. */
  entry_id?: string | null;
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
  | {
      kind: "guidance";
      title: string;
      body: string;
      source_ref: string;
      entry_id?: string;
      blocker_codes?: string[];
      fields?: string[];
      stages?: string[];
    }
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

// --- AI model management (D-093; HR with MODEL_CONFIG_MANAGE; local loopback models only) ---
// The browser names a profile id only: it never sends a URL, model, key or parameter.

export type ModelStatus = "selectable" | "unavailable" | "pending_authorisation" | "disabled";

export interface ModelGate {
  gate: string;
  rule: string;
  value: unknown;
  passed: boolean;
  /** False for a measure that is reported but never blocks activation (G-5). */
  gating: boolean;
}

export interface ModelConnectionTest {
  outcome: "passed" | "failed";
  code: string | null;
  listed: boolean | null;
  complete_ms: number | null;
  stream_ms: number | null;
  first_piece_ms: number | null;
  at?: string;
  by_user?: string;
}

export interface ModelQualification {
  qualification_id: string;
  status: "running" | "passed" | "failed" | "cancelled" | "error";
  code: string | null;
  started_at: string;
  started_by: string;
  finished_at: string | null;
  done_turns: number;
  total_turns: number;
  cancel_requested: boolean;
  /** False when the profile or the answer code changed since this run (qualify again). */
  current: boolean;
  gates: ModelGate[] | null;
  metrics: Record<string, unknown> | null;
  lines: Record<string, number> | null;
  capacity: Record<string, unknown> | null;
  connection: ModelConnectionTest | null;
  quality: { status: "SCORED" | "NOT_SCORED"; reason: string | null } | null;
  reproducibility: Record<string, unknown> | null;
  /** D-098: what the outcome means, as closed codes (absent from older servers). */
  diagnosis?: ModelDiagnosis;
}

/** D-098: a qualification outcome classified for HR recovery. */
export interface ModelDiagnosis {
  category: "passed" | "running" | "cancelled" | "technical" | "budget" | "configuration" | "quality" | "billing_uncertain";
  cause: string;
  action: "NONE" | "WAIT" | "RUN_AGAIN" | "RETRY_LATER" | "TEST_CONNECTION" | "REVIEW_SPENDING" | "ESCALATE_IT" | "ESCALATE_DEVELOPER" | "ESCALATE_OPERATOR" | "ESCALATE_KEY_OWNER";
  /** A retry is worth making now, without another change. */
  retryable: boolean;
  /** A genuine quality failure: an earlier pass of this configuration no longer counts. */
  supersedes_pass: boolean;
}

/** D-098: what a paid qualification may spend, against the strictest applicable limit. */
export interface ModelPaidQualification {
  calls: number | null;
  reservation_micro_usd: number | null;
  estimate_micro_usd: number | null;
  effective_remaining_micro_usd: number | null;
  refusal: string | null;
  sufficient: boolean;
}

export interface ModelProfileView {
  profile_id: string;
  display_name: string;
  source: "environment" | "file" | "code";
  deployment: string;
  model_id: string | null;
  model_version: string | null;
  endpoint: string | null;
  context_window_tokens: number | null;
  max_answer_tokens: number | null;
  temperature: number | null;
  timeout_seconds: number | null;
  streaming: boolean;
  fingerprint: string;
  status: ModelStatus;
  reason: string | null;
  /** Remote configurations only: closed codes and plain values the page names (see AiModelManagement). */
  details?: Record<string, string> | null;
  active: boolean;
  connection_test: ModelConnectionTest | null;
  qualification: ModelQualification | null;
  activation_blockers: string[];
  /** D-098: the passing run Activate would use (may be older than the latest run). */
  eligible_qualification?: { qualification_id: string; finished_at: string | null; is_latest: boolean } | null;
  /** D-098: remote configurations only. */
  paid_qualification?: ModelPaidQualification | null;
}

export interface ModelOverview {
  configured: boolean;
  file_status: "not_configured" | "ok" | "missing" | "invalid";
  file_errors: string[];
  model_enabled: boolean;
  revision: number;
  active: {
    profile_id: string;
    display_name: string;
    model_id: string | null;
    prompt_limit: number | null;
    qualification_id: string | null;
    changed_at: string | null;
    changed_by: string | null;
    config_changed: boolean;
    reverted: string | null;
    /** D-098: no model answers (a GPT-OSS configuration stopped being usable). */
    unavailable?: boolean;
  };
  last_good: { profile_id: string; display_name: string } | null;
  quality: { status: "SCORED" | "NOT_SCORED"; reason: string | null };
  basis: string;
  running: { qualification_id: string; profile_id: string; done_turns: number; total_turns: number; started_by: string } | null;
  profiles: ModelProfileView[];
  /** D-095: the remote profile's spending view (null unless the remote test mode is configured). */
  budget?: ModelBudgetStatus | null;
  /** The data access policy in force on the server (absent from older servers). */
  data_access?: ModelDataAccess;
}

/** "Restrict AI to verified synthetic cases", per provider class, as the server enforces it. */
export interface ModelDataAccess {
  /** default: never set (local models answer every authorised case); unavailable: unreadable (local restricted). */
  status: "default" | "stored" | "unavailable" | "not_managed";
  revision: number | null;
  changed_at: string | null;
  /** it_configured: an endpoint IT configured that is not on this machine (locked, restricted). */
  classes: Array<{ provider_class: "openrouter" | "anthropic" | "it_configured" | "local_internal"; restricted: boolean; locked: boolean }>;
  active_class: "openrouter" | "anthropic" | "it_configured" | "local_internal" | null;
  active_restricted: boolean;
  /** The shared synthetic check in force: D-095 provenance, or the D-094 fixed fixture. */
  verification: "D-095" | "D-094";
}

/** D-095 addendum: where the OpenRouter key comes from. Never the key, nor any part of it. */
export interface ModelCredentialStatus {
  source: "environment" | "env_file" | "hr_memory" | "none";
  status: "configured" | "missing" | "invalid";
  hr_editable: boolean;
  persistence: "memory_only" | "server";
  set_at: number | null;
  set_by: string | null;
}

/** D-095: read-only spending view. Amounts are micro-USD integers with USD strings beside. */
export interface ModelBudgetStatus {
  configured: boolean;
  mode: "D-094" | "D-095";
  timezone: string;
  /** D-098: the default daily limit (US$1.00), not a ceiling. */
  daily_cap_default_micro_usd: number;
  daily_cap_micro_usd: number;
  next_reset_at: string;
  credential: ModelCredentialStatus;
  provider: {
    checked_at: string;
    passed: boolean;
    remaining_micro_usd: number | null;
    remaining_usd: string | null;
    /** D-098: the key's own limit, usage and reset policy (absent from older servers). */
    limit_micro_usd?: number | null;
    limit_usd?: string | null;
    usage_micro_usd?: number | null;
    usage_usd?: string | null;
    limit_reset?: string | null;
    /** Account credits are never read: always null. */
    account_credits?: null;
    checks: { check: string; ok: boolean; detail: string }[];
  } | null;
  ledger: {
    cap_micro_usd: number;
    committed_micro_usd: number;
    headroom_micro_usd: number;
    headroom_usd: string;
    open_calls: number;
    breaker_open: boolean;
    breaker_code: string | null;
  } | null;
  daily: {
    cap_micro_usd: number;
    settled_today_micro_usd: number;
    settled_today_usd: string;
    in_flight_micro_usd: number;
    in_flight_usd: string;
    in_flight_calls: number;
    remaining_micro_usd: number;
    remaining_usd: string;
    day_started_at: string;
  } | null;
  effective_remaining_micro_usd: number;
  effective_remaining_usd: string;
  reservation_micro_usd?: number | null;
  refusal: string | null;
  /** D-096: the HR spending controls that apply (absent from older servers). */
  controls?: ModelSpendingControls;
  /** D-102: Claude's own spending view and HR controls (absent from older servers). */
  claude?: ModelClaudeBudget;
}

/** D-102: Claude's spending (its separate Anthropic ledger), with its own HR controls. */
export interface ModelClaudeBudget {
  configured: boolean;
  timezone: string;
  daily_cap_micro_usd: number;
  /** The owner-attested Anthropic workspace monthly limit (0: not attested). */
  workspace_limit_micro_usd: number;
  lifetime_ceiling_micro_usd: number;
  next_reset_at: string;
  preflight: { checked_at: string; passed: boolean } | null;
  ledger: {
    profile_ok: boolean;
    cap_micro_usd: number;
    committed_micro_usd: number;
    headroom_micro_usd: number;
    headroom_usd: string;
    open_calls: number;
    breaker_open: boolean;
    breaker_code: string | null;
    reconciled_at: string | null;
  } | null;
  daily: {
    cap_micro_usd: number;
    settled_today_micro_usd: number;
    in_flight_micro_usd: number;
    remaining_micro_usd: number;
    remaining_usd: string;
  } | null;
  effective_remaining_micro_usd: number;
  effective_remaining_usd: string;
  reservation_micro_usd?: number | null;
  refusal: string | null;
  controls: ModelClaudeSpendingControls;
}

/** D-102: Claude's HR controls. "environment" means HR has not set the value yet. */
export interface ModelClaudeSpendingControls {
  revision: number | null;
  readable: boolean;
  daily_cap_micro_usd: number;
  daily_cap_range: [number, number];
  daily_cap_default_micro_usd: number;
  raise_requires: string[];
  daily_cap_source: "hr" | "environment";
  max_calls: number;
  max_calls_range: [number, number];
  max_calls_source: "hr" | "environment";
  /** Calls the active Claude configuration made since its activation or the service's start. */
  calls_used: number | null;
  calls_remaining: number | null;
  changed_at: string | null;
  changed_by: string | null;
  lifetime: {
    opening_usage_micro_usd: number;
    cap_micro_usd: number;
    /** The lower of US$30.00 and the attested workspace limit. */
    max_cap_micro_usd: number;
    committed_micro_usd: number;
  } | null;
}

/** D-096: HR spending controls. "environment" means HR has not set the value yet. */
export interface ModelSpendingControls {
  revision: number | null;
  readable: boolean;
  daily_cap_micro_usd: number;
  /** D-098: only the ledger's technical bound (no US$1 ceiling). */
  daily_cap_max_micro_usd: number;
  daily_cap_default_micro_usd?: number;
  /** D-098: what raising either limit needs, as closed codes. */
  raise_requires?: string[];
  daily_cap_source: "hr" | "environment";
  max_calls: number;
  max_calls_range: [number, number];
  max_calls_source: "hr" | "environment";
  /** Calls the active remote model made since its activation or the service's start. */
  calls_used: number | null;
  calls_remaining: number | null;
  changed_at: string | null;
  changed_by: string | null;
  lifetime: {
    opening_usage_micro_usd: number;
    cap_micro_usd: number;
    max_cap_micro_usd: number;
    committed_micro_usd: number;
  } | null;
}

export interface ModelAuditEvent {
  seq: number;
  at: string;
  actor: string;
  role: string | null;
  action: string;
  profile_id: string | null;
  fingerprint: string | null;
  outcome: string;
  code: string | null;
  revision: number | null;
}

const modelPath = (profileId: string) => `/admin/models/${encodeURIComponent(profileId)}`;

export const fetchModelOverview = (signal?: AbortSignal) =>
  request<ModelOverview>("/admin/models", undefined, signal);
/** How many of the most recent audit events the page asks for (newest first). */
export const MODEL_AUDIT_LIMIT = 100;
export const fetchModelAudit = (signal?: AbortSignal) =>
  request<{ events: ModelAuditEvent[] }>(`/admin/models/audit?limit=${MODEL_AUDIT_LIMIT}`, undefined, signal);
export const testModelConnection = (profileId: string) =>
  request<ModelConnectionTest>(`${modelPath(profileId)}/connection-test`, {});
// D-098: a paid (remote) run is sent with the number of paid calls HR confirmed.
export const startModelQualification = (profileId: string, confirmPaidCalls?: number) =>
  request<{ qualification_id: string }>(
    `${modelPath(profileId)}/qualifications`,
    confirmPaidCalls === undefined ? {} : { confirm_paid_calls: confirmPaidCalls },
  );
export const fetchModelQualification = (qualificationId: string, signal?: AbortSignal) =>
  request<ModelQualification>(`/admin/models/qualifications/${encodeURIComponent(qualificationId)}`, undefined, signal);
export const cancelModelQualification = (qualificationId: string) =>
  request<{ cancel_requested: boolean }>(`/admin/models/qualifications/${encodeURIComponent(qualificationId)}/cancel`, {});
export const activateModel = (profileId: string, expectedRevision: number, acknowledgeQualityUnscored: boolean) =>
  request<ModelOverview>(`${modelPath(profileId)}/activate`, {
    expected_revision: expectedRevision,
    acknowledge_quality_unscored: acknowledgeQualityUnscored,
  });
export const rollbackModel = (expectedRevision: number, acknowledgeQualityUnscored: boolean) =>
  request<ModelOverview>("/admin/models/rollback", {
    expected_revision: expectedRevision,
    acknowledge_quality_unscored: acknowledgeQualityUnscored,
  });
// The key goes to the server once and is never returned; the page keeps no copy.
export const fetchModelCredential = (signal?: AbortSignal) =>
  request<ModelCredentialStatus>("/admin/models/credential", undefined, signal);
export const saveModelCredential = (apiKey: string) =>
  request<ModelCredentialStatus>("/admin/models/credential", { api_key: apiKey }, undefined, "PUT");
export const clearModelCredential = () =>
  request<ModelCredentialStatus>("/admin/models/credential", undefined, undefined, "DELETE");
// D-096: HR spending controls. Amounts are whole micro-USD; the server checks every bound.
// D-098: raising the daily limit sends the same amount again as the HR confirmation.
export const saveSpendingControls = (
  expectedRevision: number,
  dailyCapMicroUsd: number,
  maxCalls: number,
  confirmDailyCapMicroUsd: number | null = null,
) =>
  request<ModelBudgetStatus>("/admin/models/budget/controls", {
    expected_revision: expectedRevision,
    daily_cap_micro_usd: dailyCapMicroUsd,
    max_calls: maxCalls,
    ...(confirmDailyCapMicroUsd === null ? {} : { confirm_daily_cap_micro_usd: confirmDailyCapMicroUsd }),
  }, undefined, "PUT");
// A raise sends the same amount again as the HR confirmation; a decrease needs none.
// D-098 (F1): the cap the page showed is sent too, so a change made in between is refused.
export const saveLifetimeCap = (capMicroUsd: number, confirmCapMicroUsd: number | null, expectedCapMicroUsd: number) =>
  request<ModelBudgetStatus>("/admin/models/budget/lifetime-cap", {
    cap_micro_usd: capMicroUsd,
    confirm_cap_micro_usd: confirmCapMicroUsd,
    expected_cap_micro_usd: expectedCapMicroUsd,
  }, undefined, "PUT");
// D-102: Claude's own limits, on its own routes (never the GPT-OSS ones). A raise sends the
// same value again as HR's confirmation (the daily limit, and the call limit too, QG L1); the
// lifetime cap sends the cap the page showed.
export const saveClaudeSpendingControls = (
  expectedRevision: number,
  dailyCapMicroUsd: number,
  maxCalls: number,
  confirmDailyCapMicroUsd: number | null = null,
  confirmMaxCalls: number | null = null,
) =>
  request<ModelBudgetStatus>("/admin/models/budget/claude/controls", {
    expected_revision: expectedRevision,
    daily_cap_micro_usd: dailyCapMicroUsd,
    max_calls: maxCalls,
    ...(confirmDailyCapMicroUsd === null ? {} : { confirm_daily_cap_micro_usd: confirmDailyCapMicroUsd }),
    ...(confirmMaxCalls === null ? {} : { confirm_max_calls: confirmMaxCalls }),
  }, undefined, "PUT");
/** External providers stay restricted: the server refuses anything else. */
export const saveDataAccessPolicy = (expectedRevision: number, restrictLocal: boolean, confirmWiden: boolean) =>
  request<ModelDataAccess>("/admin/models/data-access", {
    expected_revision: expectedRevision,
    restrict_external: true,
    restrict_local: restrictLocal,
    confirm_widen: confirmWiden,
  }, undefined, "PUT");
export const saveClaudeLifetimeCap = (capMicroUsd: number, confirmCapMicroUsd: number | null, expectedCapMicroUsd: number) =>
  request<ModelBudgetStatus>("/admin/models/budget/claude/lifetime-cap", {
    cap_micro_usd: capMicroUsd,
    confirm_cap_micro_usd: confirmCapMicroUsd,
    expected_cap_micro_usd: expectedCapMicroUsd,
  }, undefined, "PUT");
// Read-only: the free preflight reads the key's OpenRouter limit; nothing is changed.
export const refreshProviderLimits = () =>
  request<ModelBudgetStatus>("/admin/models/budget/provider-refresh", {});
