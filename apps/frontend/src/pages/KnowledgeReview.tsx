import { useEffect, useRef, useState } from "react";
import {
  AiAssistantError,
  closeKnowledgeGap,
  decideKnowledgeEntry,
  draftFromKnowledgeGap,
  editKnowledgeEntry,
  fetchApprovedEntries,
  fetchKnowledgeAccess,
  fetchKnowledgeReviews,
  fetchKnowledgeStats,
  type KnowledgeEntry,
  type KnowledgeFix,
  type KnowledgeGap,
  type KnowledgeReviewQueue,
  type KnowledgeStats,
} from "../aiAssistant";
import RequestPage from "./RequestPage";

/** The fix a Director is writing for an enhancement request. */
interface FixDraft {
  kind: "resolution" | "guidance";
  title: string;
  body: string;
  followUps: string;
  sourceRef: string;
  /** Guidance only: the existing guidance entry to change ("" for new guidance). */
  changes: string;
}

const EMPTY_FIX: FixDraft = { kind: "resolution", title: "", body: "", followUps: "", sourceRef: "", changes: "" };

function fixOf(draft: FixDraft): KnowledgeFix {
  if (draft.kind === "resolution") {
    const followUps = draft.followUps.split("\n").map((line) => line.trim()).filter(Boolean);
    return { kind: "resolution", title: draft.title.trim(), body: draft.body.trim(), follow_ups: followUps };
  }
  return {
    kind: "guidance",
    title: draft.title.trim(),
    body: draft.body.trim(),
    source_ref: draft.sourceRef.trim(),
    ...(draft.changes ? { entry_id: draft.changes } : {}),
  };
}

function fixReady(draft: FixDraft): boolean {
  const ready = draft.title.trim().length >= 3 && draft.body.trim().length >= 10;
  return draft.kind === "resolution" ? ready : ready && draft.sourceRef.trim().length >= 3;
}

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
 * Director review of the knowledge loop: entries waiting for a decision, and enhancement
 * requests (an RM's "Not helpful" note), for which a Director writes the fix (a past case or a
 * guidance change, saved for review) or which they close with a reason. Publishing always
 * shows the final text and asks for confirmation first. In the POC's single-reviewer mode
 * (D-083) a Director may publish an entry they wrote; the Review window lists those. Shown only
 * to users the backend reports as able to review; every action is checked again by the backend.
 */
export default function KnowledgeReview({ onClose }: { onClose: () => void }) {
  const [queue, setQueue] = useState<KnowledgeReviewQueue | null>(null);
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [approved, setApproved] = useState<KnowledgeEntry[]>([]);
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const [reasons, setReasons] = useState<Record<number, string>>({});
  const [fixes, setFixes] = useState<Record<number, FixDraft>>({});
  // The entry whose final text is shown for confirmation before it is published.
  const [confirming, setConfirming] = useState<KnowledgeEntry | null>(null);
  // Whether the backend runs the POC's single-reviewer mode (D-083).
  const [singleReviewer, setSingleReviewer] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const dialog = useRef<HTMLDivElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  // The enhancement request open as a full-width page, and the one to return focus to.
  const [openRequest, setOpenRequest] = useState<KnowledgeGap | null>(null);
  const openRequestRef = useRef<KnowledgeGap | null>(null);
  openRequestRef.current = openRequest;
  const returnTo = useRef<number | null>(null);

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
        // On a request page, Escape goes back to the review window first.
        if (openRequestRef.current) setOpenRequest(null);
        else onClose();
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

  // Back from a request page: focus returns to the button that opened it.
  useEffect(() => {
    if (openRequest || returnTo.current === null) return;
    dialog.current?.querySelector<HTMLElement>(`[data-open-request="${returnTo.current}"]`)?.focus();
    returnTo.current = null;
  }, [openRequest]);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      fetchKnowledgeReviews(controller.signal),
      fetchKnowledgeStats(controller.signal),
      fetchApprovedEntries(controller.signal),
      fetchKnowledgeAccess(controller.signal),
    ])
      .then(([reviews, numbers, resolutions, access]) => {
        if (controller.signal.aborted) return;
        setSingleReviewer(access.single_reviewer === true);
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
  // Approving publishes, so it only follows the confirmation step (see `confirming`).
  async function decide(entry: KnowledgeEntry, approve: boolean): Promise<void> {
    const draft = drafts[entry.key];
    setBusy(entry.key);
    setError(null);
    try {
      const decided = await decideKnowledgeEntry(entry, approve, draft.notes, approve);
      setConfirming(null);
      setNotice(
        !approve
          ? "Rejected: it will not be used."
          : decided.single_reviewer
            ? "Published as the only reviewer: recorded as a single-reviewer decision."
            : "Approved: it can now help answer similar questions.",
      );
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
        // Always sent: null ("Does not replace one") clears a target the version had.
        replaces: draft.replaces || null,
      });
      setNotice("Changes saved as a new version. Another reviewer must approve it.");
      setTick((value) => value + 1);
    } catch (reason) {
      setError(message(reason));
    } finally {
      setBusy(null);
    }
  }

  function changeFix(id: number, update: Partial<FixDraft>): void {
    setFixes((all) => ({ ...all, [id]: { ...(all[id] ?? EMPTY_FIX), ...update } }));
  }

  // The fix is saved for review like any other entry; publishing it resolves the request.
  async function draftFrom(id: number): Promise<void> {
    const fix = fixes[id];
    if (!fix || !fixReady(fix)) return;
    setBusy(`gap-${id}`);
    setError(null);
    try {
      await draftFromKnowledgeGap(id, fixOf(fix));
      setNotice("Fix saved for review. Check it under Waiting for review, then publish it.");
      setFixes(({ [id]: _saved, ...rest }) => rest);
      setTick((value) => value + 1);
    } catch (reason) {
      setError(message(reason));
    } finally {
      setBusy(null);
    }
  }

  async function close(id: number): Promise<void> {
    const why = (reasons[id] ?? "").trim();
    if (!why) return;
    setBusy(`gap-${id}`);
    setError(null);
    try {
      await closeKnowledgeGap(id, why);
      setNotice("Request closed.");
      setReasons(({ [id]: _closed, ...rest }) => rest);
      setTick((value) => value + 1);
    } catch (reason) {
      setError(message(reason));
    } finally {
      setBusy(null);
    }
  }

  if (openRequest) {
    return (
      <div
        ref={dialog}
        className="knowledge-review-backdrop knowledge-review-backdrop-page"
        role="dialog"
        aria-modal="true"
        aria-labelledby="knowledge-review-title"
      >
        <section className="knowledge-review knowledge-review-page">
          <RequestPage gap={openRequest} onBack={() => setOpenRequest(null)} />
        </section>
      </div>
    );
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
          Approved entries help the AI Assistant answer similar questions. Check that no client details remain
          before publishing: you always see the final text and confirm it first. Saving changes creates a new version
          to review.
        </p>
        {stats && (
          <>
            <p className="knowledge-review-stats">
              {stats.feedback.total} feedback · {stats.feedback.helpful} helpful · {stats.feedback.not_helpful} not helpful
              {stats.feedback.helpful_rate !== null ? ` · ${Math.round(stats.feedback.helpful_rate * 100)}% helpful` : ""}
            </p>
            {Object.keys(stats.by_topic).length > 0 && (
              <ul className="knowledge-review-stats" aria-label="Confidence by topic">
                {Object.entries(stats.by_topic).map(([code, counts]) => (
                  <li key={code}>
                    {code}: {counts.helpful} helpful · {counts.not_helpful} not helpful
                  </li>
                ))}
              </ul>
            )}
          </>
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
                          {approved.filter((older) => older.kind === "resolution").map((older) => (
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
                  {confirming?.key === entry.key ? (
                    <section className="knowledge-review-confirm" aria-label="Confirm publishing">
                      <p className="knowledge-review-meta">
                        This exact text goes live for{" "}
                        {entry.visibility.teams.length ? `teams ${entry.visibility.teams.join(", ")}` : "every team"}
                        {entry.visibility.roles.length ? ` (roles ${entry.visibility.roles.join(", ")})` : ""}.
                        {singleReviewer ? " If you wrote or edited it, publishing is recorded as a single-reviewer decision." : ""}
                      </p>
                      <p><strong>{entry.title}</strong></p>
                      <p className="knowledge-review-final">{entry.body}</p>
                      {entry.follow_ups.length > 0 && (
                        <ul aria-label="Follow-up questions">
                          {entry.follow_ups.map((question) => <li key={question}>{question}</li>)}
                        </ul>
                      )}
                      <div className="knowledge-review-actions">
                        <button type="button" className="btn btn-primary" disabled={disabled} onClick={() => void decide(entry, true)}>
                          Confirm and publish
                        </button>
                        <button type="button" className="btn btn-ghost" disabled={disabled} onClick={() => setConfirming(null)}>
                          Back
                        </button>
                      </div>
                    </section>
                  ) : (
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
                        <button type="button" className="btn btn-primary" disabled={disabled} onClick={() => setConfirming(entry)}>
                          Approve
                        </button>
                        <button type="button" className="btn btn-secondary" disabled={disabled} onClick={() => void decide(entry, false)}>
                          Reject
                        </button>
                      </>
                    )}
                  </div>
                  )}
                </article>
              );
            })}

            <h3>Enhancement requests ({queue.gaps.length})</h3>
            {queue.gaps.length === 0 && <p className="ai-assistant-hint">No open enhancement requests.</p>}
            {queue.gaps.map((gap) => {
              const why = reasons[gap.id] ?? "";
              const fix = fixes[gap.id] ?? EMPTY_FIX;
              const disabled = busy !== null;
              return (
                <article key={gap.id} className="knowledge-review-entry" aria-label={`Enhancement request ${gap.id}`}>
                  <p className="knowledge-review-meta">{gap.blocker_codes.join(", ") || "General"}</p>
                  <p>{gap.note || "No note given."}</p>
                  <button
                    type="button"
                    className="btn"
                    data-open-request={gap.id}
                    onClick={() => {
                      returnTo.current = gap.id;
                      setOpenRequest(gap);
                    }}
                  >
                    Open request page
                  </button>
                  <fieldset className="knowledge-review-fix">
                    <legend>Write the fix</legend>
                    <label>
                      Fix as
                      <select value={fix.kind} disabled={disabled} onChange={(event) => changeFix(gap.id, { kind: event.target.value as FixDraft["kind"] })}>
                        <option value="resolution">Past case</option>
                        <option value="guidance">Guidance change</option>
                      </select>
                    </label>
                    {fix.kind === "guidance" && (
                      <label>
                        Guidance to change
                        <select value={fix.changes} disabled={disabled} onChange={(event) => changeFix(gap.id, { changes: event.target.value })}>
                          <option value="">New guidance</option>
                          {approved.filter((entry) => entry.kind === "guidance").map((entry) => (
                            <option key={entry.entry_id} value={entry.entry_id}>
                              {entry.title}
                            </option>
                          ))}
                        </select>
                      </label>
                    )}
                    <label>
                      Title
                      <input value={fix.title} maxLength={200} disabled={disabled} onChange={(event) => changeFix(gap.id, { title: event.target.value })} />
                    </label>
                    <label>
                      {fix.kind === "guidance" ? "Guidance text" : "What resolves it"} (no names, UENs or addresses)
                      <textarea rows={4} maxLength={4000} value={fix.body} disabled={disabled} onChange={(event) => changeFix(gap.id, { body: event.target.value })} />
                    </label>
                    {fix.kind === "guidance" ? (
                      <label>
                        Source reference
                        <input value={fix.sourceRef} maxLength={300} disabled={disabled} onChange={(event) => changeFix(gap.id, { sourceRef: event.target.value })} />
                      </label>
                    ) : (
                      <label>
                        Follow-up questions (one per line)
                        <textarea rows={2} value={fix.followUps} disabled={disabled} onChange={(event) => changeFix(gap.id, { followUps: event.target.value })} />
                      </label>
                    )}
                    <button type="button" className="btn btn-primary" disabled={disabled || !fixReady(fix)} onClick={() => void draftFrom(gap.id)}>
                      Save the fix for review
                    </button>
                  </fieldset>
                  <label>
                    Reason for closing
                    <input
                      value={why}
                      maxLength={1000}
                      disabled={busy !== null}
                      onChange={(event) => setReasons((all) => ({ ...all, [gap.id]: event.target.value }))}
                    />
                  </label>
                  <div className="knowledge-review-actions">
                    <button
                      type="button"
                      className="btn btn-ghost"
                      disabled={busy !== null || !why.trim()}
                      onClick={() => void close(gap.id)}
                    >
                      Close with reason
                    </button>
                  </div>
                </article>
              );
            })}

            {(() => {
              const single = approved.filter((entry) => entry.single_reviewer);
              return (
                <>
                  {/* Currently published entries only; the review history of each entry records every
                      single-reviewer decision, including rejections and later-replaced versions. */}
                  <h3>Published by a single reviewer ({single.length})</h3>
                  {single.length === 0 ? (
                    <p className="ai-assistant-hint">None.</p>
                  ) : (
                    <ul className="knowledge-review-stats" aria-label="Published by a single reviewer">
                      {single.map((entry) => (
                        <li key={entry.key}>
                          {entry.kind === "guidance" ? "Guidance" : "Past resolution"}: {entry.title} · version {entry.version} ·
                          approved by {entry.approver}, who wrote or edited it
                          {entry.approved_at ? ` · ${entry.approved_at}` : ""}
                        </li>
                      ))}
                    </ul>
                  )}
                </>
              );
            })()}
          </>
        )}
      </section>
    </div>
  );
}
