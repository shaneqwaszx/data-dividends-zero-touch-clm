import { useEffect, useState } from "react";
import {
  AiAssistantError,
  type ConversationDetail,
  type ConversationPage,
  endConversation,
  fetchMyConversation,
  fetchMyConversations,
  SATISFACTION_IF_NOT_RESOLVED,
  SATISFACTION_IF_RESOLVED,
  SATISFACTION_LABELS,
  type Satisfaction,
} from "../aiAssistant";

function errorText(error: unknown): string {
  return error instanceof AiAssistantError ? error.message : "The AI assistant could not do this right now.";
}

function when(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleString();
}

/**
 * End conversation (D-104): "Was this issue resolved?" first, then how satisfied the user is
 * (Yes offers very satisfied to neutral, No offers neutral to very unsatisfied), then a comment:
 * optional "Additional comments" after Yes, required "How should it be improved?" after No.
 * The service checks the same rules.
 */
export function EndConversationForm({
  conversationId,
  onDone,
  onCancel,
}: {
  conversationId: string;
  onDone: (message: string) => void;
  onCancel: () => void;
}) {
  const [resolved, setResolved] = useState<boolean | null>(null);
  const [satisfaction, setSatisfaction] = useState<Satisfaction | null>(null);
  const [comment, setComment] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const offered = resolved === null ? [] : resolved ? SATISFACTION_IF_RESOLVED : SATISFACTION_IF_NOT_RESOLVED;
  const ready = resolved !== null && satisfaction !== null && (resolved || comment.trim().length > 0);

  function chooseResolved(value: boolean): void {
    setResolved(value);
    const allowed = value ? SATISFACTION_IF_RESOLVED : SATISFACTION_IF_NOT_RESOLVED;
    if (satisfaction && !allowed.includes(satisfaction)) setSatisfaction(null);
  }

  function submit(): void {
    if (!ready || resolved === null || satisfaction === null) return;
    setSending(true);
    setError(null);
    endConversation(conversationId, { resolved, satisfaction, comment: comment.trim() })
      .then((result) => onDone(result.message))
      .catch((reason: unknown) => {
        setError(errorText(reason));
        setSending(false);
      });
  }

  return (
    <form
      className="ai-assistant-end-form"
      aria-label="End conversation"
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
    >
      <fieldset disabled={sending}>
        <legend>Was this issue resolved?</legend>
        {[true, false].map((value) => (
          <label key={String(value)} className="ai-assistant-choice">
            <input type="radio" name="resolved" checked={resolved === value} onChange={() => chooseResolved(value)} />
            {value ? "Yes" : "No"}
          </label>
        ))}
      </fieldset>
      {resolved !== null && (
        <fieldset disabled={sending}>
          <legend>How satisfied are you with the answer?</legend>
          {offered.map((value) => (
            <label key={value} className="ai-assistant-choice">
              <input
                type="radio"
                name="satisfaction"
                checked={satisfaction === value}
                onChange={() => setSatisfaction(value)}
              />
              {SATISFACTION_LABELS[value]}
            </label>
          ))}
        </fieldset>
      )}
      {resolved !== null && (
        <label className="ai-assistant-end-comment">
          {resolved ? "Additional comments (optional)" : "How should it be improved?"}
          <textarea
            rows={3}
            maxLength={1000}
            required={!resolved}
            value={comment}
            disabled={sending}
            onChange={(event) => setComment(event.target.value)}
          />
        </label>
      )}
      {error && <p className="ai-assistant-error" role="alert">{error}</p>}
      <div className="ai-assistant-feedback">
        <button type="submit" className="btn btn-primary" disabled={!ready || sending}>
          Submit and end
        </button>
        <button type="button" className="btn btn-ghost" disabled={sending} onClick={onCancel}>
          Back to chat
        </button>
      </div>
    </form>
  );
}

function ratingLabel(item: { ended_at: string | null; satisfaction: Satisfaction | null }): string {
  if (!item.ended_at) return "Not ended";
  return item.satisfaction ? SATISFACTION_LABELS[item.satisfaction] : "Rated";
}

/** The user's past chats (D-104): newest first, 10 a page; one opens in the chat to continue. */
export function ConversationHistory({
  onClose,
  onOpen,
}: {
  onClose: () => void;
  onOpen: (conversation: ConversationDetail) => void;
}) {
  const [page, setPage] = useState(1);
  const [list, setList] = useState<ConversationPage | null>(null);
  const [opening, setOpening] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setError(null);
    fetchMyConversations(page, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) setList(result);
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) setError(errorText(reason));
      });
    return () => controller.abort();
  }, [page]);

  function openConversation(conversationId: string): void {
    setError(null);
    setOpening(conversationId);
    fetchMyConversation(conversationId)
      .then(onOpen)
      .catch((reason: unknown) => {
        setError(errorText(reason));
        setOpening(null);
      });
  }

  const pages = list ? Math.max(1, Math.ceil(list.total / list.page_size)) : 1;
  return (
    <section className="ai-assistant-history" aria-label="Chat history">
      <button type="button" className="btn btn-ghost" onClick={onClose}>
        ← Back to chat
      </button>
      {error && <p className="ai-assistant-error" role="alert">{error}</p>}
      {!list && !error && <p className="ai-assistant-hint">Loading…</p>}
      {list && list.items.length === 0 && <p className="ai-assistant-hint">No past chats yet.</p>}
      {list && list.items.length > 0 && (
        <ul className="ai-assistant-history-list">
          {list.items.map((item) => (
            <li key={item.conversation_id}>
              <button
                type="button"
                className="ai-assistant-history-item"
                disabled={opening !== null}
                onClick={() => openConversation(item.conversation_id)}
              >
                <span className="ai-assistant-history-title">{item.title}</span>
                <span className="ai-assistant-history-meta">
                  {when(item.updated_at)} · {item.answers} {item.answers === 1 ? "answer" : "answers"} · {ratingLabel(item)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {list && pages > 1 && (
        <div className="ai-assistant-feedback">
          <button type="button" className="btn btn-ghost" disabled={page <= 1} onClick={() => setPage(page - 1)}>
            Previous
          </button>
          <span className="ai-assistant-hint">Page {page} of {pages}</span>
          <button type="button" className="btn btn-ghost" disabled={page >= pages} onClick={() => setPage(page + 1)}>
            Next
          </button>
        </div>
      )}
    </section>
  );
}
