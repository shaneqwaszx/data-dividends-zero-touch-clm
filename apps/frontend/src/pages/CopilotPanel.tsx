import { type FormEvent, type KeyboardEvent, useEffect, useRef, useState } from "react";
import "./CopilotPanel.css";
import { CopilotText } from "./copilotText";
import { askCopilot, CopilotError, type CopilotTurn, fetchCopilotBrief } from "../copilot";

interface ChatMessage extends CopilotTurn {
  note?: string | null;
  /** The opening summary, which is refreshed in place rather than appended. */
  brief?: boolean;
}

interface Thread {
  company: string | null;
  messages: ChatMessage[];
  suggestions: string[];
  badge: number;
}

interface CopilotPanelProps {
  /** The case to explain: a case page under Cases, or the case being onboarded. */
  caseId: string | null;
  /** True on New onboarding before its case has been created. */
  onboardingWithoutCase?: boolean;
  /** Opens the Cases list, offered when no case has been opened yet. */
  onOpenCases: () => void;
}

const EMPTY_THREAD: Thread = { company: null, messages: [], suggestions: [], badge: 0 };

function errorText(error: unknown): string {
  return error instanceof CopilotError ? error.message : "The copilot could not answer right now.";
}

function isAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

function CopilotIcon() {
  return (
    <svg className="copilot-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
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
 * The copilot only discusses a case the system has already replied on: a case page under
 * Cases, or the case being onboarded on New onboarding. The button is on every page so it is
 * always within reach; elsewhere it explains what to do first. Conversations are kept per case
 * (coming back to a case shows its chat again). It only reads and requests nothing while closed.
 */
export default function CopilotPanel({ caseId, onboardingWithoutCase = false, onOpenCases }: CopilotPanelProps) {
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

  const thread = (activeCaseId && threads[activeCaseId]) || EMPTY_THREAD;

  function updateThread(key: string, change: (current: Thread) => Thread): void {
    setThreads((all) => ({ ...all, [key]: change(all[key] ?? EMPTY_THREAD) }));
  }

  // Opening summary of the case, built from app data (no AI), so it is quick. Nothing is
  // requested while the copilot is closed; when open it refreshes on a case change or request.
  useEffect(() => {
    if (!open || !activeCaseId) return undefined;
    const key = activeCaseId;
    const controller = new AbortController();
    setError(null);
    fetchCopilotBrief(key, controller.signal)
      .then((brief) => {
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
        if (isAbort(reason)) return;
        setError(errorText(reason));
      });
    return () => controller.abort();
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
  }, [thread.messages.length, busy, open]);

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
    const history: CopilotTurn[] = thread.messages.map(({ role, content }) => ({ role, content }));
    updateThread(key, (current) => ({
      ...current,
      messages: [...current.messages, { role: "user", content: text }],
    }));
    setDraft("");
    setBusy(true);
    setError(null);
    const controller = new AbortController();
    pending.current = controller;
    askCopilot(key, text, history, controller.signal)
      .then((reply) => {
        updateThread(key, (current) => ({
          ...current,
          messages: [...current.messages, { role: "assistant", content: reply.answer, note: reply.notice }],
          suggestions: reply.suggested_questions,
        }));
      })
      .catch((reason: unknown) => {
        if (isAbort(reason)) return;
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
        className="copilot-launcher"
        onClick={() => setOpen(true)}
        aria-label={thread.badge ? `Ask Copilot (${thread.badge} to look at)` : "Ask Copilot"}
      >
        <CopilotIcon />
        <span className="copilot-launcher-label">Ask Copilot</span>
        {thread.badge ? <span className="copilot-badge">{thread.badge}</span> : null}
      </button>
    );
  }

  if (!activeCaseId) {
    // Nothing to explain yet: a small card instead of the full chat window.
    return (
      <aside className="copilot-panel copilot-panel-compact" aria-label="Onboarding Copilot">
        <div className="copilot-compact-body">
          <p>
            {onboardingWithoutCase ? (
              <>Enter the company's details to start. Once the case is created, I'll guide you through it.</>
            ) : (
              <>Open a case and I'll explain where it stands and what to do next.</>
            )}
          </p>
          {!onboardingWithoutCase && (
            <button type="button" className="btn btn-primary copilot-open-cases" onClick={onOpenCases}>
              Go to Cases
            </button>
          )}
        </div>
        <button type="button" className="btn btn-ghost copilot-compact-close" onClick={() => setOpen(false)} aria-label="Close copilot">
          ✕
        </button>
      </aside>
    );
  }

  const subtitle = `${thread.company ?? "This case"} · read-only`;

  return (
    <aside className="copilot-panel" aria-label="Onboarding Copilot">
      <header className="copilot-header">
        <div>
          <strong>Onboarding Copilot</strong>
          <span className="copilot-subtitle">{subtitle}</span>
        </div>
        <div className="copilot-header-actions">
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => setRefreshTick((tick) => tick + 1)}
            aria-label="Refresh the summary"
            title="Refresh"
          >
            ↻
          </button>
          <button type="button" className="btn btn-ghost" onClick={() => setOpen(false)} aria-label="Close copilot">
            ✕
          </button>
        </div>
      </header>

      <div className="copilot-messages" aria-live="polite">
        {thread.messages.length === 0 && !error && <p className="copilot-hint">Reading this case…</p>}
        {thread.messages.map((message, index) => (
          <div key={index} className={`copilot-message copilot-${message.role}`}>
            {message.role === "assistant" ? <CopilotText text={message.content} /> : <p>{message.content}</p>}
            {message.note && <span className="copilot-note">{message.note}</span>}
          </div>
        ))}
        {busy && <p className="copilot-hint">Thinking…</p>}
        {error && <p className="copilot-error" role="alert">{error}</p>}
        <div ref={endRef} />
      </div>

      {thread.suggestions.length > 0 && (
        <div className="copilot-suggestions">
          {thread.suggestions.map((question) => (
            <button key={question} type="button" className="copilot-chip" disabled={busy} onClick={() => ask(question)}>
              {question}
            </button>
          ))}
        </div>
      )}

      <form className="copilot-input" onSubmit={submit}>
        <textarea
          ref={inputRef}
          rows={1}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={onInputKey}
          placeholder="Ask about this case… (Enter to send, Shift+Enter for a new line)"
          maxLength={600}
          aria-label="Ask the copilot about this case"
        />
        <button type="submit" className="btn btn-primary" disabled={busy || !draft.trim()}>
          Ask
        </button>
      </form>
      <p className="copilot-disclaimer">AI answers can be wrong. The case page is the source of truth.</p>
    </aside>
  );
}
