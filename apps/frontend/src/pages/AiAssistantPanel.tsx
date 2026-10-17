import { type FormEvent, type KeyboardEvent, useEffect, useRef, useState } from "react";
import "./AiAssistantPanel.css";
import { AiAssistantText } from "./aiAssistantText";
import { AiAssistantError, type AiAssistantTurn, askAiAssistantStreaming, fetchAiAssistantBrief } from "../aiAssistant";

interface ChatMessage extends AiAssistantTurn {
  note?: string | null;
  /** The opening summary, which is refreshed in place rather than appended. */
  brief?: boolean;
  /** An answer that is still being written. */
  streaming?: boolean;
}

interface Thread {
  company: string | null;
  messages: ChatMessage[];
  suggestions: string[];
  badge: number;
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

function errorText(error: unknown): string {
  return error instanceof AiAssistantError ? error.message : "The AI assistant could not answer right now.";
}

function isAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
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

/**
 * The AI assistant only discusses a case the system has already replied on: a case page under
 * Cases, or the case being onboarded on New onboarding. The button is on every page so it is
 * always within reach; elsewhere it explains what to do first. Conversations are kept per case
 * (coming back to a case shows its chat again). It only reads and requests nothing while closed.
 */
export default function AiAssistantPanel({ caseId, onboardingWithoutCase = false, onOpenCases }: AiAssistantPanelProps) {
  const activeCaseId = caseId;
  const [open, setOpen] = useState(false);
  const [threads, setThreads] = useState<Record<string, Thread>>({});
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshTick, setRefreshTick] = useState(0);
  const endRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
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
            { role: "assistant", content: brief.message, brief: true },
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

  // A question in flight belongs to the case it was asked about.
  useEffect(() => {
    pending.current?.abort();
    pending.current = null;
    setBusy(false);
  }, [activeCaseId]);

  useEffect(() => () => pending.current?.abort(), []);

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ block: "end" });
  }, [thread.messages, busy, open]);

  // Grow the question box with its text (up to a few lines), so the whole question shows.
  useEffect(() => {
    const box = inputRef.current;
    if (!box) return;
    box.style.height = "auto";
    box.style.height = `${Math.min(box.scrollHeight, 132)}px`;
  }, [draft, open]);

  function ask(question: string): void {
    const text = question.trim();
    if (!text || busy || !activeCaseId) return;
    const key = activeCaseId;
    // The opening summary repeats the case facts the service sends anyway, so it is not
    // sent back as history: a shorter prompt is a faster answer.
    const history: AiAssistantTurn[] = thread.messages
      .filter((item) => !item.brief && !item.streaming)
      .map(({ role, content }) => ({ role, content }));
    updateThread(key, (current) => ({
      ...current,
      messages: [
        ...current.messages,
        { role: "user", content: text },
        { role: "assistant", content: "", streaming: true },
      ],
    }));
    setDraft("");
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
            { role: "assistant", content: reply.answer, note: reply.notice },
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

  function onInputKey(event: KeyboardEvent<HTMLTextAreaElement>): void {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      ask(draft);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    ask(draft);
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
        </div>
        <button type="button" className="btn btn-ghost ai-assistant-compact-close" onClick={() => setOpen(false)} aria-label="Close AI assistant">
          ✕
        </button>
      </aside>
    );
  }

  const subtitle = `${thread.company ?? "This case"} · read-only`;

  return (
    <aside className="ai-assistant-panel" aria-label="AI Assistant">
      <header className="ai-assistant-header">
        <div>
          <strong>AI Assistant</strong>
          <span className="ai-assistant-subtitle">{subtitle}</span>
        </div>
        <div className="ai-assistant-header-actions">
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

      <div className="ai-assistant-messages" aria-live="polite">
        {thread.messages.length === 0 && !error && <p className="ai-assistant-hint">Reading this case…</p>}
        {thread.messages.map((message, index) => message.streaming && !message.content ? null : (
          <div key={index} className={`ai-assistant-message ai-assistant-${message.role}`} aria-busy={message.streaming || undefined}>
            {message.role === "assistant" ? <AiAssistantText text={message.content} /> : <p>{message.content}</p>}
            {message.note && <span className="ai-assistant-note">{message.note}</span>}
          </div>
        ))}
        {busy && !thread.messages.some((item) => item.streaming && item.content) && (
          <p className="ai-assistant-hint">Thinking…</p>
        )}
        {error && <p className="ai-assistant-error" role="alert">{error}</p>}
        <div ref={endRef} />
      </div>

      {thread.suggestions.length > 0 && (
        <div className="ai-assistant-suggestions">
          {thread.suggestions.slice(0, 3).map((question) => (
            <button key={question} type="button" className="ai-assistant-chip" disabled={busy} onClick={() => ask(question)}>
              {question}
            </button>
          ))}
        </div>
      )}

      <form className="ai-assistant-input" onSubmit={submit}>
        <textarea
          ref={inputRef}
          rows={1}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={onInputKey}
          placeholder="Ask about this case…"
          maxLength={600}
          aria-label="Ask the AI assistant about this case"
        />
        <button
          type="submit"
          className="ai-assistant-send"
          disabled={busy || !draft.trim()}
          aria-label="Send"
          title="Send (Enter)"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path d="M12 19V5M5.5 11.5 12 5l6.5 6.5" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </form>
      <p className="ai-assistant-disclaimer">AI answers can be wrong. The case page is the source of truth.</p>
    </aside>
  );
}
