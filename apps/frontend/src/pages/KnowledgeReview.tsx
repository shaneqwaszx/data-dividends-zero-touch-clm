import { useEffect, useRef, useState } from "react";
import {
  AiAssistantError,
  closeKnowledgeGap,
  decideKnowledgeEntry,
  editKnowledgeEntry,
  fetchApprovedResolutions,
  fetchKnowledgeReviews,
  fetchKnowledgeStats,
  type KnowledgeEntry,
  type KnowledgeReviewQueue,
  type KnowledgeStats,
} from "../aiAssistant";

interface Draft {
  title: string;
  body: string;
  followUps: string;
  teams: string;
  replaces: string;
  notes: string;
}

function draftOf(entry: KnowledgeEntry): Draft {
  return {
    title: entry.title,
    body: entry.body,
    followUps: entry.follow_ups.join("\n"),
    teams: entry.visibility.teams.join(", "),
    replaces: entry.replaces ?? "",
    notes: "",
  };
}

function message(error: unknown): string {
  return error instanceof AiAssistantError ? error.message : "Something went wrong. Please try again.";
}

const FOCUSABLE = "button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled])";

/**
 * Director review of the knowledge loop: drafted past resolutions waiting for a decision,
 * and gaps flagged as "Not helpful". Shown only to users the backend reports as able to
 * review; every action is checked again by the backend (and the author can never decide
 * their own entry).
 */
export default function KnowledgeReview({ onClose }: { onClose: () => void }) {
  const [queue, setQueue] = useState<KnowledgeReviewQueue | null>(null);
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [approved, setApproved] = useState<KnowledgeEntry[]>([]);
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const dialog = useRef<HTMLDivElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);

  // A modal dialog: focus moves into it when it opens and back to what opened it on close.
  useEffect(() => {
    const opener = document.activeElement;
    heading.current?.focus();
    return () => {
      if (opener instanceof HTMLElement && opener.isConnected) opener.focus();
    };
  }, []);

  // Escape closes it; Tab and Shift+Tab wrap around its controls instead of leaving it.
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent): void {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== "Tab" || !dialog.current) return;
      const controls = [...dialog.current.querySelectorAll<HTMLElement>(FOCUSABLE)];
      if (controls.length === 0) return;
      const active = document.activeElement;
      const index = controls.findIndex((control) => control === active);
      if (event.shiftKey && index <= 0) {
        event.preventDefault();
        controls[controls.length - 1].focus();
      } else if (!event.shiftKey && (index === controls.length - 1 || !dialog.current.contains(active))) {
        event.preventDefault();
        controls[0].focus();
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      fetchKnowledgeReviews(controller.signal),
      fetchKnowledgeStats(controller.signal),
      fetchApprovedResolutions(controller.signal),
    ])
      .then(([reviews, numbers, resolutions]) => {
        if (controller.signal.aborted) return;
        setQueue(reviews);
        setStats(numbers);
        setApproved(resolutions);
        setDrafts(Object.fromEntries(reviews.pending.map((entry) => [entry.key, draftOf(entry)])));
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) setError(message(reason));
      });
    return () => controller.abort();
  }, [tick]);

  function change(key: string, update: Partial<Draft>): void {
    setDrafts((all) => ({ ...all, [key]: { ...all[key], ...update } }));
  }

  function changes(entry: KnowledgeEntry, draft: Draft) {
    const teams = draft.teams.split(",").map((team) => team.trim()).filter(Boolean);
    const followUps = draft.followUps.split("\n").map((line) => line.trim()).filter(Boolean);
    const edited =
      draft.title !== entry.title ||
      draft.body !== entry.body ||
      followUps.join("\n") !== entry.follow_ups.join("\n") ||
      teams.join(",") !== entry.visibility.teams.join(",") ||
      (draft.replaces || null) !== entry.replaces;
    return { teams, followUps, edited };
  }

  // Approve and Reject apply to exactly the content shown. Changes are saved as a new version
  // that another reviewer must approve: whoever edits an entry can never decide it.
  async function decide(entry: KnowledgeEntry, approve: boolean): Promise<void> {
    const draft = drafts[entry.key];
    setBusy(entry.key);
    setError(null);
    try {
      await decideKnowledgeEntry(entry, approve, draft.notes);
      setNotice(approve ? "Approved: it can now help answer similar questions." : "Rejected: it will not be used.");
      setTick((value) => value + 1);
    } catch (reason) {
      setError(message(reason));
    } finally {
      setBusy(null);
    }
  }

  async function saveChanges(entry: KnowledgeEntry): Promise<void> {
    const draft = drafts[entry.key];
    const { teams, followUps } = changes(entry, draft);
    setBusy(entry.key);
    setError(null);
    try {
      await editKnowledgeEntry(entry, {
        title: draft.title,
        body: draft.body,
        follow_ups: followUps,
        visibility: { roles: entry.visibility.roles, teams },
        ...(draft.replaces ? { replaces: draft.replaces } : {}),
      });
      setNotice("Changes saved as a new version. Another reviewer must approve it.");
      setTick((value) => value + 1);
    } catch (reason) {
      setError(message(reason));
    } finally {
      setBusy(null);
    }
  }

  async function close(id: number): Promise<void> {
    setBusy(`gap-${id}`);
    try {
      await closeKnowledgeGap(id);
      setTick((value) => value + 1);
    } catch (reason) {
      setError(message(reason));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div ref={dialog} className="knowledge-review-backdrop" role="dialog" aria-modal="true" aria-labelledby="knowledge-review-title">
      <section className="knowledge-review">
        <header className="knowledge-review-header">
          <h2 id="knowledge-review-title" ref={heading} tabIndex={-1}>Knowledge review</h2>
          <button type="button" className="btn btn-ghost" onClick={onClose} aria-label="Close knowledge review">
            ✕
          </button>
        </header>
        <p className="knowledge-review-intro">
          Approved resolutions help the AI Assistant answer similar questions. Check that no client details remain
          before approving. You cannot approve an entry you wrote or edited: saving changes creates a new version for
          another reviewer.
        </p>
        {stats && (
          <p className="knowledge-review-stats">
            {stats.feedback.total} feedback · {stats.feedback.helpful} solved · {stats.feedback.not_helpful} not helpful
            {stats.feedback.helpful_rate !== null ? ` · ${Math.round(stats.feedback.helpful_rate * 100)}% helpful` : ""}
          </p>
        )}
        {notice && <p className="knowledge-review-notice" role="status">{notice}</p>}
        {error && <p className="ai-assistant-error" role="alert">{error}</p>}
        {!queue && !error && <p className="ai-assistant-hint">Loading…</p>}

        {queue && (
          <>
            <h3>Waiting for review ({queue.pending.length})</h3>
            {queue.pending.length === 0 && <p className="ai-assistant-hint">Nothing to review.</p>}
            {queue.pending.map((entry) => {
              const draft = drafts[entry.key] ?? draftOf(entry);
              const disabled = busy !== null;
              const { edited } = changes(entry, draft);
              return (
                <article key={entry.key} className="knowledge-review-entry" aria-label={`Review ${entry.title}`}>
                  <p className="knowledge-review-meta">
                    {entry.kind === "guidance" ? "Guidance" : "Past resolution"} · by {entry.author}
                    {entry.revises !== null ? ` · edited from version ${entry.revises}` : ""}
                    {entry.blocker_codes.length ? ` · ${entry.blocker_codes.join(", ")}` : ""}
                  </p>
                  <label>
                    Title
                    <input value={draft.title} disabled={disabled} onChange={(event) => change(entry.key, { title: event.target.value })} />
                  </label>
                  <label>
                    Summary (shared across clients: no names, UENs or addresses)
                    <textarea rows={5} value={draft.body} disabled={disabled} onChange={(event) => change(entry.key, { body: event.target.value })} />
                  </label>
                  {entry.kind === "resolution" && (
                    <>
                      <label>
                        Follow-up questions (one per line)
                        <textarea
                          rows={2}
                          value={draft.followUps}
                          disabled={disabled}
                          onChange={(event) => change(entry.key, { followUps: event.target.value })}
                        />
                      </label>
                      <label>
                        Replaces an older resolution (optional)
                        <select value={draft.replaces} disabled={disabled} onChange={(event) => change(entry.key, { replaces: event.target.value })}>
                          <option value="">Does not replace one</option>
                          {approved.map((older) => (
                            <option key={older.entry_id} value={older.entry_id}>
                              {older.title}
                            </option>
                          ))}
                        </select>
                      </label>
                    </>
                  )}
                  <label>
                    Visible to teams (comma-separated; can only be narrowed)
                    <input value={draft.teams} disabled={disabled} onChange={(event) => change(entry.key, { teams: event.target.value })} />
                  </label>
                  <label>
                    Review notes
                    <input value={draft.notes} disabled={disabled} onChange={(event) => change(entry.key, { notes: event.target.value })} />
                  </label>
                  <div className="knowledge-review-actions">
                    {edited ? (
                      <>
                        <button type="button" className="btn btn-primary" disabled={disabled} onClick={() => void saveChanges(entry)}>
                          Save changes for another reviewer
                        </button>
                        <button type="button" className="btn btn-ghost" disabled={disabled} onClick={() => change(entry.key, draftOf(entry))}>
                          Discard changes
                        </button>
                      </>
                    ) : (
                      <>
                        <button type="button" className="btn btn-primary" disabled={disabled} onClick={() => void decide(entry, true)}>
                          Approve
                        </button>
                        <button type="button" className="btn btn-secondary" disabled={disabled} onClick={() => void decide(entry, false)}>
                          Reject
                        </button>
                      </>
                    )}
                  </div>
                </article>
              );
            })}

            <h3>Gaps flagged as not helpful ({queue.gaps.length})</h3>
            {queue.gaps.length === 0 && <p className="ai-assistant-hint">No open gaps.</p>}
            {queue.gaps.map((gap) => (
              <article key={gap.id} className="knowledge-review-entry">
                <p className="knowledge-review-meta">{gap.blocker_codes.join(", ") || "General"}</p>
                <p>{gap.note || "No note given."}</p>
                <button type="button" className="btn btn-ghost" disabled={busy !== null} onClick={() => void close(gap.id)}>
                  Mark as handled
                </button>
              </article>
            ))}
          </>
        )}
      </section>
    </div>
  );
}
