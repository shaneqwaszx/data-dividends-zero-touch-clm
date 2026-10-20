import { type ReactNode, useEffect, useRef, useState } from "react";
import {
  type AppendMessage,
  AssistantRuntimeProvider,
  ComposerPrimitive,
  type ThreadMessageLike,
  ThreadPrimitive,
  useExternalStoreRuntime,
} from "@assistant-ui/react";
import "./AiAssistantPanel.css";
import { AiAssistantText } from "./aiAssistantText";
import { goToCaseSection } from "./caseSections";
import KnowledgeReview from "./KnowledgeReview";
import {
  AiAssistantError,
  type AiAssistantSource,
  type AiAssistantTurn,
  askAiAssistantStreaming,
  fetchAiAssistantBrief,
  fetchKnowledgeAccess,
  sendAiAssistantFeedback,
} from "../aiAssistant";

interface ChatMessage extends AiAssistantTurn {
  id: string;
  note?: string | null;
  /** The opening summary, which is refreshed in place rather than appended. */
  brief?: boolean;
  /** An answer that is still being written. */
  streaming?: boolean;
  sources?: AiAssistantSource[];
}

interface Thread {
  company: string | null;
  messages: ChatMessage[];
  suggestions: string[];
  badge: number;
}

/** Feedback on one answer: choosing (with an optional note), sent, or failed. */
interface FeedbackState {
  helpful: boolean;
  stage: "note" | "sending" | "sent" | "error";
  note: string;
  message?: string;
}

interface AiAssistantPanelProps {
  /** The case to explain: a case page under Cases, or the case being onboarded. */
  caseId: string | null;
  /** True on New onboarding before its case has been created. */
  onboardingWithoutCase?: boolean;
  /** Opens the Cases list, offered when no case has been opened yet. */
  onOpenCases: () => void;
}

const EMPTY_THREAD: Thread = { company: null, messages: [], suggestions: [], badge: 0 };

let nextId = 0;
const newId = () => `m${(nextId += 1)}`;

function errorText(error: unknown): string {
  return error instanceof AiAssistantError ? error.message : "The AI assistant could not answer right now.";
}

function isAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

function messageText(message: AppendMessage): string {
  return message.content
    .map((part) => (part.type === "text" ? part.text : ""))
    .join("")
    .trim();
}

function toThreadMessage(message: ChatMessage): ThreadMessageLike {
  return {
    id: message.id,
    role: message.role,
    content: message.content,
    status:
      message.role === "assistant"
        ? message.streaming
          ? { type: "running" }
          : { type: "complete", reason: "stop" }
        : undefined,
    metadata: {
      custom: {
        note: message.note ?? null,
        brief: Boolean(message.brief),
        streaming: Boolean(message.streaming),
        sources: (message.sources ?? []) as unknown as Record<string, unknown>[],
      },
    },
  };
}

function AiAssistantIcon() {
  return (
    <svg className="ai-assistant-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M4 5.5A2.5 2.5 0 0 1 6.5 3h11A2.5 2.5 0 0 1 20 5.5v8a2.5 2.5 0 0 1-2.5 2.5H10l-4.2 3.6c-.5.4-1.3.1-1.3-.6V16A2.5 2.5 0 0 1 4 13.5z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      <path d="M8.5 9.5h.01M12 9.5h.01M15.5 9.5h.01" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
    </svg>
  );
}

function sourceLabel(source: AiAssistantSource): string {
  return source.kind === "guidance" ? `Guidance v${source.version}` : "Approved past case";
}

/** The guidance and past cases an answer cited: one line, expandable to the full list. */
function SourceChips({ sources }: { sources: AiAssistantSource[] }) {
  const shown = sources.filter((source) => source.cited);
  if (!shown.length) return null;
  const first = shown[0];
  return (
    <details className="ai-assistant-sources">
      <summary>
        <span className="ai-assistant-sources-first">
          <BookIcon />
          <span className="ai-assistant-sources-first-text">
            Source: {first.title} ({sourceLabel(first)})
          </span>
        </span>
        <span className="ai-assistant-sources-toggle">View sources ({shown.length})</span>
      </summary>
      <ul aria-label="Sources">
        {shown.map((source) => (
          <li key={source.tag} className={`ai-assistant-source ai-assistant-source-${source.kind}`}>
            <span className="ai-assistant-source-tag">{source.tag}</span>
            <span className="ai-assistant-source-title">{source.title}</span>
            <span className="ai-assistant-source-kind">
              {sourceLabel(source)}
              {source.illustrative ? " · illustrative" : ""}
            </span>
          </li>
        ))}
      </ul>
    </details>
  );
}

function BookIcon() {
  return (
    <svg className="ai-assistant-icon-small" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5v-15Z" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      <path d="M4 20.5A2.5 2.5 0 0 0 6.5 23H20v-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
    </svg>
  );
}

function ThumbIcon({ down = false }: { down?: boolean }) {
  return (
    <svg
      className="ai-assistant-icon-small"
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
      style={down ? { transform: "rotate(180deg)" } : undefined}
    >
      <path
        d="M7 10v11H4V10h3Zm0 0 4.5-7c1.4 0 2.5 1.1 2.5 2.5V9h5a2 2 0 0 1 2 2.3l-1.3 7.9A2 2 0 0 1 17.7 21H7"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/**
 * The AI assistant only discusses a case the system has already replied on: a case page under
 * Cases, or the case being onboarded on New onboarding. The button is on every page so it is
 * always within reach; elsewhere it explains what to do first. Conversations are kept per case
 * (coming back to a case shows its chat again). It only reads and requests nothing while closed.
 *
 * The chat window is built from assistant-ui primitives over this component's own state
 * (an external store), so per-case threads, cancellation and access handling stay here.
 */
export default function AiAssistantPanel({ caseId, onboardingWithoutCase = false, onOpenCases }: AiAssistantPanelProps) {
  const activeCaseId = caseId;
  const [open, setOpen] = useState(false);
  const [threads, setThreads] = useState<Record<string, Thread>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshTick, setRefreshTick] = useState(0);
  const [feedback, setFeedback] = useState<Record<string, FeedbackState>>({});
  const [canReview, setCanReview] = useState(false);
  const [reviewOpen, setReviewOpen] = useState(false);
  const pending = useRef<AbortController | null>(null);
  const briefRequest = useRef<AbortController | null>(null);

  const thread = (activeCaseId && threads[activeCaseId]) || EMPTY_THREAD;

  function updateThread(key: string, change: (current: Thread) => Thread): void {
    setThreads((all) => ({ ...all, [key]: change(all[key] ?? EMPTY_THREAD) }));
  }

  function clearInaccessibleThread(key: string): void {
    pending.current?.abort();
    pending.current = null;
    briefRequest.current?.abort();
    briefRequest.current = null;
    updateThread(key, () => EMPTY_THREAD);
    setBusy(false);
  }

  // Opening summary of the case, built from app data (no AI), so it is quick. Nothing is
  // requested while the AI assistant is closed; when open it refreshes on a case change or request.
  useEffect(() => {
    if (!open || !activeCaseId) return undefined;
    const key = activeCaseId;
    const controller = new AbortController();
    briefRequest.current = controller;
    setError(null);
    fetchAiAssistantBrief(key, controller.signal)
      .then((brief) => {
        if (controller.signal.aborted) return;
        updateThread(key, (current) => ({
          company: brief.company,
          messages: [
            { id: `brief-${key}`, role: "assistant", content: brief.message, brief: true },
            ...current.messages.filter((item) => !item.brief),
          ],
          suggestions: brief.suggested_questions,
          badge: brief.blocker_count,
        }));
      })
      .catch((reason: unknown) => {
        if (controller.signal.aborted || isAbort(reason)) return;
        if (reason instanceof AiAssistantError && reason.status === 404) {
          clearInaccessibleThread(key);
        }
        setError(errorText(reason));
      });
    return () => {
      controller.abort();
      if (briefRequest.current === controller) briefRequest.current = null;
    };
  }, [activeCaseId, open, refreshTick]);

  // Whether this user may review knowledge (usability only: the backend checks every call).
  useEffect(() => {
    if (!open) return undefined;
    const controller = new AbortController();
    fetchKnowledgeAccess(controller.signal)
      .then((access) => {
        if (!controller.signal.aborted) setCanReview(Boolean(access?.can_review));
      })
      .catch(() => {
        if (!controller.signal.aborted) setCanReview(false);
      });
    return () => controller.abort();
  }, [open]);

  // A question in flight belongs to the case it was asked about.
  useEffect(() => {
    pending.current?.abort();
    pending.current = null;
    setBusy(false);
  }, [activeCaseId]);

  useEffect(() => () => pending.current?.abort(), []);

  function ask(question: string): void {
    const text = question.trim();
    if (!text || busy || !activeCaseId) return;
    const key = activeCaseId;
    // The opening summary repeats the case facts the service sends anyway, so it is not
    // sent back as history: a shorter prompt is a faster answer.
    const history: AiAssistantTurn[] = thread.messages
      .filter((item) => !item.brief && !item.streaming)
      .map(({ role, content }) => ({ role, content }));
    const draftId = newId();
    updateThread(key, (current) => ({
      ...current,
      messages: [
        ...current.messages,
        { id: newId(), role: "user", content: text },
        { id: draftId, role: "assistant", content: "", streaming: true },
      ],
    }));
    setBusy(true);
    setError(null);
    const controller = new AbortController();
    pending.current = controller;
    const withoutDraft = (messages: ChatMessage[]) => messages.filter((item) => !item.streaming);
    askAiAssistantStreaming(
      key,
      text,
      history,
      (soFar) => {
        if (controller.signal.aborted) return;
        updateThread(key, (current) => ({
          ...current,
          messages: current.messages.map((item) => (item.streaming ? { ...item, content: soFar } : item)),
        }));
      },
      controller.signal,
    )
      .then((reply) => {
        if (controller.signal.aborted) return;
        updateThread(key, (current) => ({
          ...current,
          messages: [
            ...withoutDraft(current.messages),
            {
              id: draftId,
              role: "assistant",
              content: reply.answer,
              note: reply.notice,
              sources: reply.sources ?? [],
            },
          ],
          suggestions: reply.suggested_questions,
        }));
      })
      .catch((reason: unknown) => {
        updateThread(key, (current) => ({ ...current, messages: withoutDraft(current.messages) }));
        if (controller.signal.aborted || isAbort(reason)) return;
        if (reason instanceof AiAssistantError && reason.status === 404) {
          clearInaccessibleThread(key);
        }
        setError(errorText(reason));
      })
      .finally(() => {
        if (pending.current === controller) {
          pending.current = null;
          setBusy(false);
        }
      });
  }

  function startFeedback(messageId: string, helpful: boolean): void {
    // "Yes, helpful" is one click; only "Not helpful" asks what was missing.
    if (helpful) {
      sendFeedback(messageId, { helpful: true, stage: "note", note: "" });
      return;
    }
    setFeedback((all) => ({ ...all, [messageId]: { helpful, stage: "note", note: "" } }));
  }

  function sendFeedback(messageId: string, given?: FeedbackState): void {
    const state = given ?? feedback[messageId];
    if (!state || !activeCaseId) return;
    const key = activeCaseId;
    // Only the conversation up to the answer being rated, and never the opening summary.
    const upTo = thread.messages.findIndex((item) => item.id === messageId);
    const turns = thread.messages
      .slice(0, upTo + 1)
      .filter((item) => !item.brief && !item.streaming && item.content)
      .map(({ role, content }) => ({ role, content }));
    setFeedback((all) => ({ ...all, [messageId]: { ...state, stage: "sending" } }));
    sendAiAssistantFeedback(key, { helpful: state.helpful, note: state.note.trim(), turns })
      .then((result) =>
        setFeedback((all) => ({ ...all, [messageId]: { ...state, stage: "sent", message: result.message } })),
      )
      .catch((reason: unknown) =>
        setFeedback((all) => ({ ...all, [messageId]: { ...state, stage: "error", message: errorText(reason) } })),
      );
  }

  const runtime = useExternalStoreRuntime<ChatMessage>({
    messages: thread.messages,
    isRunning: busy,
    convertMessage: toThreadMessage,
    onNew: async (message: AppendMessage) => ask(messageText(message)),
  });

  function goToSection(title: string): void {
    // Scrolls the case page behind the panel; the panel stays open.
    goToCaseSection(title);
  }

  function feedbackControls(messageId: string): ReactNode {
    const state = feedback[messageId];
    if (!state) {
      return (
        <div className="ai-assistant-rate" role="group" aria-label="Was this answer helpful?">
          <span className="ai-assistant-rate-question">Was this answer helpful?</span>
          <span className="ai-assistant-rate-buttons">
            <button type="button" className="ai-assistant-feedback-button" onClick={() => startFeedback(messageId, true)}>
              <ThumbIcon /> Yes, helpful
            </button>
            <button type="button" className="ai-assistant-feedback-button" onClick={() => startFeedback(messageId, false)}>
              <ThumbIcon down /> Not helpful
            </button>
          </span>
        </div>
      );
    }
    if (state.stage === "sent" || state.stage === "error") {
      return (
        <p className={state.stage === "error" ? "ai-assistant-error" : "ai-assistant-feedback-done"} role="status">
          {state.message}
        </p>
      );
    }
    return (
      <div className="ai-assistant-feedback-form">
        <label>
          What was missing? (optional)
          <textarea
            rows={2}
            maxLength={1000}
            value={state.note}
            disabled={state.stage === "sending"}
            onChange={(event) => setFeedback((all) => ({ ...all, [messageId]: { ...state, note: event.target.value } }))}
          />
        </label>
        <p className="ai-assistant-hint">Client details are removed before a Director sees it.</p>
        <div className="ai-assistant-feedback">
          <button type="button" className="btn btn-primary" disabled={state.stage === "sending"} onClick={() => sendFeedback(messageId)}>
            Send
          </button>
          <button
            type="button"
            className="btn btn-ghost"
            disabled={state.stage === "sending"}
            onClick={() => setFeedback(({ [messageId]: _dropped, ...rest }) => rest)}
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  if (!open) {
    return (
      <button
        type="button"
        className="ai-assistant-launcher"
        onClick={() => setOpen(true)}
        aria-label={thread.badge ? `Ask AI Assistant (${thread.badge} to look at)` : "Ask AI Assistant"}
      >
        <AiAssistantIcon />
        <span className="ai-assistant-launcher-label">Ask AI Assistant</span>
        {thread.badge ? <span className="ai-assistant-badge">{thread.badge}</span> : null}
      </button>
    );
  }

  if (!activeCaseId) {
    // Nothing to explain yet: a small card instead of the full chat window.
    return (
      <aside className="ai-assistant-panel ai-assistant-panel-compact" aria-label="AI Assistant">
        <div className="ai-assistant-compact-body">
          <p>
            {onboardingWithoutCase ? (
              <>Enter the company's details to start. Once the case is created, I'll guide you through it.</>
            ) : (
              <>Open a case and I'll explain where it stands and what to do next.</>
            )}
          </p>
          {!onboardingWithoutCase && (
            <button type="button" className="btn btn-primary ai-assistant-open-cases" onClick={onOpenCases}>
              Go to Cases
            </button>
          )}
          {canReview && (
            <button type="button" className="btn btn-ghost ai-assistant-review-open" onClick={() => setReviewOpen(true)}>
              Knowledge review
            </button>
          )}
        </div>
        <button type="button" className="btn btn-ghost ai-assistant-compact-close" onClick={() => setOpen(false)} aria-label="Close AI assistant">
          ✕
        </button>
        {reviewOpen && <KnowledgeReview onClose={() => setReviewOpen(false)} />}
      </aside>
    );
  }

  const subtitle = `${thread.company ?? "This case"} · read-only`;
  const writing = thread.messages.some((item) => item.streaming && item.content);

  return (
    <aside className="ai-assistant-panel" aria-label="AI Assistant">
      <header className="ai-assistant-header">
        <div>
          <strong>AI Assistant</strong>
          <span className="ai-assistant-subtitle">{subtitle}</span>
        </div>
        <div className="ai-assistant-header-actions">
          {canReview && (
            <button
              type="button"
              className="btn btn-ghost ai-assistant-review-open"
              onClick={() => setReviewOpen(true)}
              title="Review knowledge"
            >
              Review
            </button>
          )}
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => setRefreshTick((tick) => tick + 1)}
            aria-label="Refresh the summary"
            title="Refresh"
          >
            ↻
          </button>
          <button type="button" className="btn btn-ghost" onClick={() => setOpen(false)} aria-label="Close AI assistant">
            ✕
          </button>
        </div>
      </header>

      <AssistantRuntimeProvider runtime={runtime}>
        <ThreadPrimitive.Root className="ai-assistant-thread">
          <ThreadPrimitive.Viewport className="ai-assistant-messages" aria-live="polite">
            {thread.messages.length === 0 && !error && <p className="ai-assistant-hint">Reading this case…</p>}
            <ThreadPrimitive.Messages>
              {({ message }) => {
                const custom = (message.metadata?.custom ?? {}) as {
                  note?: string | null;
                  brief?: boolean;
                  streaming?: boolean;
                  sources?: AiAssistantSource[];
                };
                const text = message.content.map((part) => (part.type === "text" ? part.text : "")).join("");
                if (custom.streaming && !text) return null;
                const finished = message.role === "assistant" && !custom.brief && !custom.streaming;
                return (
                  <div
                    className={`ai-assistant-message ai-assistant-${message.role}`}
                    aria-busy={custom.streaming || undefined}
                  >
                    {message.role === "assistant" ? <AiAssistantText text={text} onSection={goToSection} /> : <p>{text}</p>}
                    {custom.note && <span className="ai-assistant-note">{custom.note}</span>}
                    {finished && <SourceChips sources={custom.sources ?? []} />}
                    {finished && feedbackControls(message.id)}
                  </div>
                );
              }}
            </ThreadPrimitive.Messages>
            {busy && !writing && <p className="ai-assistant-hint">Thinking…</p>}
            {error && <p className="ai-assistant-error" role="alert">{error}</p>}
          </ThreadPrimitive.Viewport>

          {thread.suggestions.length > 0 && (
            <div className="ai-assistant-suggestions">
              {thread.suggestions.slice(0, 3).map((question) => (
                <button key={question} type="button" className="ai-assistant-chip" disabled={busy} onClick={() => ask(question)}>
                  {question}
                </button>
              ))}
            </div>
          )}

          <ComposerPrimitive.Root className="ai-assistant-input">
            <ComposerPrimitive.Input
              rows={1}
              maxRows={5}
              maxLength={600}
              placeholder="Ask about this case…"
              aria-label="Ask the AI assistant about this case"
              submitMode="enter"
            />
            <ComposerPrimitive.Send className="ai-assistant-send" disabled={busy} aria-label="Send" title="Send (Enter)">
              <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path d="M12 19V5M5.5 11.5 12 5l6.5 6.5" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </ComposerPrimitive.Send>
          </ComposerPrimitive.Root>
        </ThreadPrimitive.Root>
      </AssistantRuntimeProvider>
      <p className="ai-assistant-disclaimer">AI answers can be wrong. The case page is the source of truth.</p>
      {reviewOpen && <KnowledgeReview onClose={() => setReviewOpen(false)} />}
    </aside>
  );
}
