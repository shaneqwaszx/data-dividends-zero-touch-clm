import { useEffect, useRef, useState } from "react";
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
import { ConversationHistory, EndConversationForm } from "./ConversationFeedback";
import {
  AiAssistantError,
  type AiAssistantSource,
  type ConversationDetail,
  type AiAssistantTurn,
  askAiAssistantStreaming,
  askGeneralAssistantStreaming,
  askSupportAssistant,
  closeAssistantContext,
  CONTEXT_ENDED_CODES,
  fetchAiAssistantBrief,
  fetchAssistantHealth,
  openAssistantContext,
} from "../aiAssistant";

interface ChatMessage extends AiAssistantTurn {
  id: string;
  note?: string | null;
  /** The opening summary, which is refreshed in place rather than appended. */
  brief?: boolean;
  /** An answer that is still being written. */
  streaming?: boolean;
  sources?: AiAssistantSource[];
  /** The service's record of this answer (none for small talk). */
  answerId?: string | null;
  /** A small-talk reply: it never has a record, so nothing failed when answerId is missing. */
  smallTalk?: boolean;
  /** How the finished answer was produced, as the service reported it. */
  answeredBy?: "model" | "case_data";
}

/** What the page has actually observed of a question in progress (no estimate, no percentage). */
interface Activity {
  startedAt: number;
  /** The service started its reply: it has read the case and prepared the question. */
  connected: boolean;
}

interface Thread {
  company: string | null;
  messages: ChatMessage[];
  suggestions: string[];
  badge: number;
  /** The service's conversation for this chat (D-105); End conversation rates it. */
  conversationId: string | null;
  /** Shown above a chat reopened from History. */
  resumedNote?: string | null;
}

interface AiAssistantPanelProps {
  /** The case to explain: a case page under Cases, or the case being onboarded. */
  caseId: string | null;
  /** True on New onboarding before its case has been created. */
  onboardingWithoutCase?: boolean;
  /** Opens the Cases list, offered when no case has been opened yet. */
  onOpenCases: () => void;
  /** Support (D-105): with no case open, chat about the approved rules and the policy. */
  canChatWithoutCase?: boolean;
  /** Opens a case page, to continue a past chat about another case from History. */
  onOpenCase?: (caseId: string) => void;
  /** D-105: Support asked about this case from a Knowledge Review page: open on it, with the
   * user's question offered first. A new ``nonce`` opens it again. */
  askAbout?: { caseId: string; question: string; nonce: number } | null;
  /** D-115: a case user may use the general onboarding chat when no case is open (when the
   * service offers it). */
  canGeneralChat?: boolean;
}

const EMPTY_THREAD: Thread = { company: null, messages: [], suggestions: [], badge: 0, conversationId: null };
// Support's chat without a case has its own thread.
const SUPPORT_THREAD = "support";
// D-115: the general onboarding chat (no case) has its own thread and chat context.
const GENERAL_THREAD = "general";
const GENERAL_WELCOME =
  "Ask me about corporate onboarding: KYC, ACRA records, entity types, ownership and UBOs, documents, blockers or GoldTier. No case is open, so I answer in general terms.";
const CONTEXT_ENDED = "This chat ended, so its memory was cleared. Ask again to start a new chat.";
const SUPPORT_WELCOME =
  "Ask me about the approved rules (official guidance and past resolutions) or the active policy settings.";

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
        answeredBy: message.answeredBy ?? null,
        smallTalk: Boolean(message.smallTalk),
      },
    },
  };
}

export function seconds(ms: number): string {
  return `${(ms / 1000).toFixed(ms < 10_000 ? 1 : 0)} s`;
}

/**
 * The stages of a question as the page observes them: each finished stage is shown only after
 * the event that ends it (the reply starting, the first checked line), and the current one says
 * what is being waited for. No percentage, no estimate, nothing the model wrote but did not
 * pass the check.
 */
export function AnswerActivity({ activity, writing, now }: { activity: Activity; writing: boolean; now: number }) {
  const stages: { label: string; done: boolean }[] = [{ label: "Preparing case information", done: activity.connected }];
  if (activity.connected) stages.push({ label: "Checking model readiness and waiting for the answer", done: writing });
  if (writing) stages.push({ label: "Showing lines that passed the check", done: false });
  const current = stages.find((stage) => !stage.done);
  return (
    <div className="ai-assistant-activity">
      <ol aria-label="Answer progress">
        {stages.map((stage) => (
          <li key={stage.label} className={stage.done ? "is-done" : "is-current"}>
            <span aria-hidden="true">{stage.done ? "✓" : "…"}</span> {stage.label}
          </li>
        ))}
      </ol>
      <span className="ai-assistant-activity-time" aria-hidden="true">{seconds(Math.max(0, now - activity.startedAt))}</span>
      <span className="sr-only" role="status">{current?.label ?? ""}</span>
    </div>
  );
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

/**
 * The AI assistant only discusses a case the system has already replied on: a case page under
 * Cases, or the case being onboarded on New onboarding. The button is on every page so it is
 * always within reach; elsewhere it explains what to do first (or, D-115, offers the general
 * onboarding chat). A chat lives only while its case is open: leaving the case clears its
 * memory here and on the service, and coming back starts afresh (D-115). It only reads and
 * requests nothing while closed.
 *
 * The chat window is built from assistant-ui primitives over this component's own state
 * (an external store), so per-case threads, cancellation and access handling stay here.
 */
export default function AiAssistantPanel({
  caseId,
  onboardingWithoutCase = false,
  onOpenCases,
  canChatWithoutCase = false,
  onOpenCase,
  askAbout = null,
  canGeneralChat = false,
}: AiAssistantPanelProps) {
  const activeCaseId = caseId;
  // Support's chat without a case (D-105), when no case is open.
  const supportChat = !activeCaseId && canChatWithoutCase;
  // D-115: the service says whether it offers the general chat (copilot mode only).
  const [generalOffered, setGeneralOffered] = useState(false);
  const generalChat = !activeCaseId && !supportChat && canGeneralChat && generalOffered;
  const threadKey = activeCaseId ?? (supportChat ? SUPPORT_THREAD : generalChat ? GENERAL_THREAD : null);
  const [open, setOpen] = useState(false);
  const [threads, setThreads] = useState<Record<string, Thread>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshTick, setRefreshTick] = useState(0);
  // The chat, the End conversation form, or the user's past chats.
  const [view, setView] = useState<"chat" | "end" | "history">("chat");
  const [endedNotice, setEndedNotice] = useState<string | null>(null);
  const pending = useRef<AbortController | null>(null);
  const [activity, setActivity] = useState<Activity | null>(null);
  const [now, setNow] = useState(() => performance.now());
  const briefRequest = useRef<AbortController | null>(null);
  // D-115 case memory: one server-held chat context per thread, opened on the first question
  // and closed (its turns dropped) when the chat is left, the panel unmounts (sign-out, user
  // change) or the page is hidden for good. Never shared between threads.
  const contextIds = useRef<Record<string, string>>({});
  const contextRequests = useRef<Record<string, Promise<string | null>>>({});
  const liveKey = useRef<string | null>(threadKey);

  const thread = (threadKey && threads[threadKey]) || EMPTY_THREAD;
  // The question Support asked about, offered first while the panel is on its case.
  const askedQuestion = askAbout && askAbout.caseId === activeCaseId ? askAbout.question : null;
  const suggestions = askedQuestion
    ? [askedQuestion, ...thread.suggestions.filter((question) => question !== askedQuestion)]
    : thread.suggestions;

  // Asking about a case from Knowledge Review opens the panel on it.
  useEffect(() => {
    if (askAbout) {
      setOpen(true);
      setView("chat");
    }
  }, [askAbout?.nonce]);

  function updateThread(key: string, change: (current: Thread) => Thread): void {
    setThreads((all) => ({ ...all, [key]: change(all[key] ?? EMPTY_THREAD) }));
  }

  /** Only for the chat on screen: a late reply for a chat that was left changes nothing. */
  function updateLive(key: string, change: (current: Thread) => Thread): void {
    if (liveKey.current === key) updateThread(key, change);
  }

  function closeContext(key: string): void {
    const id = contextIds.current[key];
    if (id) closeAssistantContext(id);
    delete contextIds.current[key];
    delete contextRequests.current[key];
  }

  /** The chat's context, opened once; null when the service has none (an older service). */
  function contextFor(key: string): Promise<string | null> {
    if (key === SUPPORT_THREAD) return Promise.resolve(null);
    const known = contextIds.current[key];
    if (known) return Promise.resolve(known);
    const pendingOpen = contextRequests.current[key];
    if (pendingOpen) return pendingOpen;
    const opening = openAssistantContext(key === GENERAL_THREAD ? null : key)
      .then((handle) => {
        if (liveKey.current !== key || contextRequests.current[key] !== opening) {
          closeAssistantContext(handle.context_id);  // the chat was left while it opened
          return null;
        }
        contextIds.current[key] = handle.context_id;
        return handle.context_id;
      })
      .catch(() => null)
      .finally(() => {
        if (contextRequests.current[key] === opening) delete contextRequests.current[key];
      });
    contextRequests.current[key] = opening;
    return opening;
  }

  // Leaving a chat (another case, no case, the general chat) clears its memory: the service
  // drops the context's turns and this page forgets the thread. Coming back starts afresh.
  useEffect(() => {
    const previous = liveKey.current;
    liveKey.current = threadKey;
    if (previous && previous !== threadKey && previous !== SUPPORT_THREAD) {
      closeContext(previous);
      setThreads((all) => {
        const { [previous]: _left, ...rest } = all;
        return rest;
      });
    }
  }, [threadKey]);

  useEffect(() => {
    const closeAll = () => Object.keys(contextIds.current).forEach(closeContext);
    window.addEventListener("pagehide", closeAll);
    return () => {
      window.removeEventListener("pagehide", closeAll);
      closeAll();
    };
  }, []);

  // Whether the service offers the general chat: asked once, only for case users with no case open.
  useEffect(() => {
    if (!open || activeCaseId || supportChat || !canGeneralChat) return undefined;
    const controller = new AbortController();
    fetchAssistantHealth(controller.signal)
      .then((health) => setGeneralOffered(Boolean(health.general_chat)))
      .catch(() => undefined);
    return () => controller.abort();
  }, [open, activeCaseId, supportChat, canGeneralChat]);

  function clearInaccessibleThread(key: string): void {
    pending.current?.abort();
    pending.current = null;
    briefRequest.current?.abort();
    briefRequest.current = null;
    updateThread(key, () => EMPTY_THREAD);
    setBusy(false);
    setActivity(null);
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
          ...current,
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

  // A question in flight belongs to the case it was asked about.
  useEffect(() => {
    pending.current?.abort();
    pending.current = null;
    setBusy(false);
    setActivity(null);
    setView("chat");
    setEndedNotice(null);
  }, [activeCaseId]);

  // The elapsed time beside the progress stages: one tick a second, only while a question runs.
  useEffect(() => {
    if (!activity) return undefined;
    const timer = window.setInterval(() => setNow(performance.now()), 1000);
    return () => window.clearInterval(timer);
  }, [activity]);

  useEffect(() => () => pending.current?.abort(), []);

  function ask(question: string): void {
    const text = question.trim();
    if (!text || busy || !threadKey) return;
    const key = threadKey;
    setEndedNotice(null);
    // The opening summary repeats the case facts the service sends anyway, so it is not
    // sent back as history: a shorter prompt is a faster answer.
    const history: AiAssistantTurn[] = thread.messages
      .filter((item) => !item.brief && !item.streaming)
      .map(({ role, content }) => ({ role, content }));
    // Only the ids of earlier answers: the service keeps its own records of what it said.
    const earlierAnswerIds = thread.messages.flatMap((item) => (item.answerId ? [item.answerId] : []));
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
    const startedAt = performance.now();
    setActivity({ startedAt, connected: false });
    setNow(startedAt);
    const controller = new AbortController();
    pending.current = controller;
    const withoutDraft = (messages: ChatMessage[]) => messages.filter((item) => !item.streaming);
    const onText = (soFar: string) => {
      if (controller.signal.aborted) return;
      updateLive(key, (current) => ({
        ...current,
        messages: current.messages.map((item) => (item.streaming ? { ...item, content: soFar } : item)),
      }));
    };
    const onConnected = () => {
      if (!controller.signal.aborted) setActivity((current) => current && { ...current, connected: true });
    };
    const answer = supportChat
      ? askSupportAssistant(text, history, controller.signal)
      : contextFor(key).then((contextId) => {
        controller.signal.throwIfAborted();
        if (key === GENERAL_THREAD) {
          if (!contextId) throw new AiAssistantError("The general chat is not available right now.");
          return askGeneralAssistantStreaming(text, contextId, onText, controller.signal, onConnected);
        }
        return askAiAssistantStreaming(
          key, text, history, onText, controller.signal, earlierAnswerIds, onConnected,
          thread.conversationId, contextId,
        );
      });
    answer
      .then((reply) => {
        if (controller.signal.aborted) return;
        updateLive(key, (current) => ({
          ...current,
          messages: [
            ...withoutDraft(current.messages),
            {
              id: draftId,
              role: "assistant",
              content: reply.answer,
              note: reply.notice,
              sources: reply.sources ?? [],
              answerId: reply.answer_id ?? null,
              smallTalk: reply.small_talk === true,
              answeredBy: reply.answered_by,
            },
          ],
          suggestions: reply.suggested_questions,
          conversationId: reply.conversation_id ?? current.conversationId,
        }));
      })
      .catch((reason: unknown) => {
        updateLive(key, (current) => ({ ...current, messages: withoutDraft(current.messages) }));
        if (controller.signal.aborted || isAbort(reason)) return;
        if (reason instanceof AiAssistantError && reason.code && CONTEXT_ENDED_CODES.has(reason.code)) {
          // The service ended this chat (timed out or closed): start again with an empty memory.
          closeContext(key);
          updateLive(key, () => EMPTY_THREAD);
          setError(CONTEXT_ENDED);
          return;
        }
        if (reason instanceof AiAssistantError && reason.status === 404) {
          closeContext(key);
          clearInaccessibleThread(key);
        }
        setError(errorText(reason));
      })
      .finally(() => {
        if (pending.current === controller) {
          pending.current = null;
          setBusy(false);
          setActivity(null);
        }
      });
  }

  /**
   * From History: the past chat continues in this chat window. An open conversation goes on as
   * itself; a rated one cannot take more answers, so new questions start a new conversation
   * with the past exchange as context. A chat about another case opens that case's page.
   */
  function resumeConversation(past: ConversationDetail): void {
    const messages: ChatMessage[] = past.turns.flatMap((turn) => [
      { id: newId(), role: "user" as const, content: turn.question },
      {
        id: newId(),
        role: "assistant" as const,
        content: turn.answer,
        answerId: turn.answer_id,
        answeredBy: turn.answered_by ?? undefined,
        note: turn.notices.join(" ") || null,
      },
    ]);
    updateThread(past.case_id, (current) => ({
      ...current,
      messages: [...current.messages.filter((item) => item.brief), ...messages],
      conversationId: past.ended_at ? null : past.conversation_id,
      resumedNote: past.ended_at
        ? "You rated this chat. New questions continue it as a new conversation."
        : "Continuing your earlier chat.",
    }));
    setEndedNotice(null);
    setView("chat");
    if (past.case_id !== activeCaseId) onOpenCase?.(past.case_id);
  }

  /** After End conversation: the chat starts again (its summary stays), with a thank-you. */
  function conversationEnded(message: string): void {
    if (threadKey) {
      updateThread(threadKey, (current) => ({
        ...current,
        messages: current.messages.filter((item) => item.brief),
        conversationId: null,
        resumedNote: null,
      }));
    }
    setEndedNotice(message);
    setView("chat");
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

  if (!threadKey) {
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

  const subtitle = supportChat
    ? "Approved rules and policy · read-only"
    : generalChat ? "General onboarding help · read-only" : `${thread.company ?? "This case"} · read-only`;
  // Ending rates the conversation: only a case chat with at least one recorded answer.
  const canEnd = !supportChat && !generalChat && thread.conversationId !== null && !busy;
  const writing = thread.messages.some((item) => item.streaming && item.content);

  return (
    <aside className="ai-assistant-panel" aria-label="AI Assistant">
      <header className="ai-assistant-header">
        <div>
          <strong>AI Assistant</strong>
          <span className="ai-assistant-subtitle">{subtitle}</span>
        </div>
        <div className="ai-assistant-header-actions">
          {canEnd && view === "chat" && (
            <button type="button" className="btn btn-ghost ai-assistant-end-open" onClick={() => setView("end")}>
              End conversation
            </button>
          )}
          {!supportChat && !generalChat && !canChatWithoutCase && (
            <button
              type="button"
              className="btn btn-ghost ai-assistant-history-open"
              onClick={() => setView(view === "history" ? "chat" : "history")}
              aria-pressed={view === "history"}
            >
              History
            </button>
          )}
          {!supportChat && !generalChat && (
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => setRefreshTick((tick) => tick + 1)}
              aria-label="Refresh the summary"
              title="Refresh"
            >
              ↻
            </button>
          )}
          <button type="button" className="btn btn-ghost" onClick={() => setOpen(false)} aria-label="Close AI assistant">
            ✕
          </button>
        </div>
      </header>

      {view === "end" && thread.conversationId && (
        <EndConversationForm conversationId={thread.conversationId} onDone={conversationEnded} onCancel={() => setView("chat")} />
      )}
      {view === "history" && <ConversationHistory onClose={() => setView("chat")} onOpen={resumeConversation} />}
      {view === "chat" && (
      <AssistantRuntimeProvider runtime={runtime}>
        <ThreadPrimitive.Root className="ai-assistant-thread">
          <ThreadPrimitive.Viewport className="ai-assistant-messages" aria-live="polite">
            {endedNotice && <p className="ai-assistant-feedback-done" role="status">{endedNotice}</p>}
            {thread.resumedNote && <p className="ai-assistant-hint" role="note">{thread.resumedNote}</p>}
            {thread.messages.length === 0 && !error && (
              <p className="ai-assistant-hint">{supportChat ? SUPPORT_WELCOME : generalChat ? GENERAL_WELCOME : "Reading this case…"}</p>
            )}
            <ThreadPrimitive.Messages>
              {({ message }) => {
                const custom = (message.metadata?.custom ?? {}) as {
                  note?: string | null;
                  brief?: boolean;
                  streaming?: boolean;
                  sources?: AiAssistantSource[];
                  answeredBy?: "model" | "case_data" | null;
                  smallTalk?: boolean;
                };
                const text = message.content.map((part) => (part.type === "text" ? part.text : "")).join("");
                if (custom.streaming && !text) return null;
                const finished = message.role === "assistant" && !custom.brief && !custom.streaming;
                return (
                  <div
                    className={`ai-assistant-message ai-assistant-${message.role}`}
                    aria-busy={custom.streaming || undefined}
                  >
                    {/* D-098: an answer no AI model wrote is labelled where it is read, not only in the details below. */}
                    {finished && custom.answeredBy === "case_data" && !custom.smallTalk && (
                      <p className="ai-assistant-guidance-label" data-testid="case-data-label">
                        {supportChat ? (
                          <><strong>Approved wording, not AI-generated.</strong> The AI model did not write this answer; it lists the matching approved rules and policy.</>
                        ) : (
                          <><strong>Case-data guidance, not AI-generated.</strong> The AI model did not write this answer; it comes from this case's data and any approved guidance cited.</>
                        )}
                      </p>
                    )}
                    {message.role === "assistant" ? <AiAssistantText text={text} onSection={goToSection} /> : <p>{text}</p>}
                    {custom.note && <span className="ai-assistant-note">{custom.note}</span>}
                    {finished && <SourceChips sources={custom.sources ?? []} />}
                  </div>
                );
              }}
            </ThreadPrimitive.Messages>
            {busy && activity && <AnswerActivity activity={activity} writing={writing} now={now} />}
            {error && <p className="ai-assistant-error" role="alert">{error}</p>}
          </ThreadPrimitive.Viewport>

          {suggestions.length > 0 && (
            <div className="ai-assistant-suggestions">
              {suggestions.slice(0, 3).map((question) => (
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
              placeholder={supportChat ? "Ask about the rules or the policy…" : generalChat ? "Ask about corporate onboarding…" : "Ask about this case…"}
              aria-label={supportChat ? "Ask the AI assistant about the rules or the policy" : generalChat ? "Ask the AI assistant about corporate onboarding" : "Ask the AI assistant about this case"}
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
      )}
      {supportChat && (
        <p className="ai-assistant-disclaimer">AI answers can be wrong. The Policy tab and the approved rules are the source of truth.</p>
      )}
    </aside>
  );
}
