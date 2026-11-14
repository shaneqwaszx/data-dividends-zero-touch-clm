import { type ReactNode, useEffect, useRef, useState } from "react";
import {
  AiAssistantError,
  closeKnowledgeGap,
  type ConversationDraft,
  type ConversationPage,
  type ConversationPriority,
  type ConversationSummary,
  type ConversationTurn,
  decideKnowledgeEntry,
  discardConversationDraft,
  draftFromKnowledgeGap,
  editKnowledgeEntry,
  fetchApprovedEntries,
  fetchFixStart,
  fetchKnowledgeAccess,
  fetchKnowledgeReviews,
  fetchReviewConversation,
  fetchReviewConversations,
  type RuleTrial,
  type KnowledgeEntry,
  type KnowledgeFix,
  type KnowledgeGap,
  type KnowledgeReviewQueue,
  type ReviewConversation,
  type ReviewFilters,
  type ReviewStatus,
  SATISFACTION_LABELS,
  type Satisfaction,
  saveConversationDraft,
  tryRuleChange,
} from "../aiAssistant";
import RequestPage from "./RequestPage";
import "./AiAssistantPanel.css";
import ExternalAiNotice from "./ExternalAiNotice";

/** The fix Support is writing for a conversation's request. */
interface FixDraft {
  kind: "resolution" | "guidance";
  title: string;
  body: string;
  followUps: string;
  sourceRef: string;
  /** Guidance only: the existing guidance entry to change ("" for new guidance). */
  changes: string;
  /** "Edit a rule" was chosen: a rule must be picked before it can be saved. */
  editing: boolean;
  /** Guidance only: when it applies, comma-separated (blank: the request's case topics). */
  blockerCodes: string;
  fieldTags: string;
  stageTags: string;
  /** The AI's left-out lines the form was started from (empty when started blank or cleared). */
  startLines: string[];
  /** The title it was started with (from the blocker type), for a past case or new guidance. */
  startTitle: string;
  /** The title and text the form last filled in itself: only those are replaced on a change
   * of "Fix as" or of the guidance, never what the reviewer wrote. */
  autoTitle: string;
  autoBody: string;
}

const EMPTY_FIX: FixDraft = {
  kind: "guidance", title: "", body: "", followUps: "", sourceRef: "", changes: "", editing: false, blockerCodes: "", fieldTags: "", stageTags: "",
  startLines: [], startTitle: "", autoTitle: "", autoBody: "",
};

const tags = (text: string) => text.split(",").map((item) => item.trim()).filter(Boolean);

/** Guidance only: the "When it applies" tags that were given (none means the request's). */
function appliesTo(draft: FixDraft): { blocker_codes?: string[]; fields?: string[]; stages?: string[] } {
  if (draft.kind !== "guidance") return {};
  const [codes, fields, stages] = [tags(draft.blockerCodes), tags(draft.fieldTags), tags(draft.stageTags)];
  return {
    ...(codes.length ? { blocker_codes: codes } : {}),
    ...(fields.length ? { fields } : {}),
    ...(stages.length ? { stages } : {}),
  };
}

/** The title and text to fill in, unless the reviewer already changed what was filled in. */
function refill(draft: FixDraft, title: string, body: string): Partial<FixDraft> {
  return {
    ...(draft.title === draft.autoTitle ? { title, autoTitle: title } : {}),
    ...(draft.body === draft.autoBody ? { body, autoBody: body } : {}),
  };
}

// A redaction placeholder ([ADDRESS], [COMPANY] or any [UPPERCASE] token the Redactor makes;
// knowledge tags like [G1] have digits). The service refuses a fix that keeps one.
const PLACEHOLDER = /\[[A-Z][A-Z_]*\]/g;

/** The placeholders still in a fix, in order, each once (follow-ups only for a past case,
 * the only kind that has them). */
function placeholdersIn(draft: FixDraft): string[] {
  const texts = draft.kind === "resolution" ? [draft.title, draft.body, draft.followUps] : [draft.title, draft.body];
  return [...new Set(texts.flatMap((text) => text.match(PLACEHOLDER) ?? []))];
}

/** The body a fix starts with: a guidance change starts from its current approved text. */
function startingBody(startLines: string[], current?: KnowledgeEntry): string {
  return [current?.body ?? "", ...startLines].filter(Boolean).join("\n");
}

function fixOf(draft: FixDraft): KnowledgeFix {
  // Sent only when the fix was started from the AI's answer (the server checks it has one).
  const started = draft.startLines.length > 0 ? { started_from_answer: true } : {};
  if (draft.kind === "resolution") {
    const followUps = draft.followUps.split("\n").map((line) => line.trim()).filter(Boolean);
    return { kind: "resolution", title: draft.title.trim(), body: draft.body.trim(), follow_ups: followUps, ...started };
  }
  return {
    kind: "guidance",
    title: draft.title.trim(),
    body: draft.body.trim(),
    source_ref: draft.sourceRef.trim(),
    ...(draft.changes ? { entry_id: draft.changes } : {}),
    ...appliesTo(draft),
    ...started,
  };
}

function fixReady(draft: FixDraft): boolean {
  const ready = draft.title.trim().length >= 3 && draft.body.trim().length >= 10 && placeholdersIn(draft).length === 0;
  if (draft.kind === "resolution") return ready;
  return ready && draft.sourceRef.trim().length >= 3 && (!draft.editing || draft.changes !== "");
}

/** What the fix does: edit an existing rule or add a new one (D-105: every fix is a rule). */
type FixMode = "edit" | "new";

function modeOf(draft: FixDraft): FixMode {
  return draft.editing || draft.changes ? "edit" : "new";
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

/** How long ago a request was made, in whole days. */
export function age(createdAt: string, now: number = Date.now()): string {
  const made = Date.parse(createdAt);
  if (Number.isNaN(made)) return "age unknown";
  const days = Math.max(0, Math.floor((now - made) / 86_400_000));
  return days === 0 ? "today" : days === 1 ? "1 day ago" : `${days} days ago`;
}

function message(error: unknown): string {
  return error instanceof AiAssistantError ? error.message : "Something went wrong. Please try again.";
}

/** The fix form's state as a draft the service keeps (D-105), and back. */
function draftToSave(fix: FixDraft): ConversationDraft {
  return {
    kind: fix.kind,
    title: fix.title,
    body: fix.body,
    follow_ups: fix.followUps.split("\n").map((line) => line.trim()).filter(Boolean),
    entry_id: fix.changes || null,
    source_ref: fix.sourceRef,
    blocker_codes: tags(fix.blockerCodes),
    fields: tags(fix.fieldTags),
    stages: tags(fix.stageTags),
  };
}

function fixFromSaved(draft: ConversationDraft): FixDraft {
  return {
    ...EMPTY_FIX,
    // Every fix is a rule now; an older worked-example draft opens as a new rule.
    kind: "guidance",
    title: draft.title,
    body: draft.body,
    followUps: draft.follow_ups.join("\n"),
    sourceRef: draft.source_ref,
    changes: draft.entry_id ?? "",
    editing: draft.kind === "guidance" && Boolean(draft.entry_id),
    blockerCodes: (draft.blocker_codes ?? []).join(", "),
    fieldTags: (draft.fields ?? []).join(", "),
    stageTags: (draft.stages ?? []).join(", "),
  };
}

export const PRIORITY_LABELS: Record<ConversationPriority, string> = { high: "High", medium: "Medium", low: "Low" };
export const STATUS_LABELS: Record<ReviewStatus, string> = {
  open: "Open",
  no_review: "No review needed",
  draft: "Saved as draft",
  not_reviewed: "Not reviewed",
  awaiting_publish: "Fix awaiting publish",
  fixed: "Fixed",
  closed: "Closed",
};
const FILTER_STATUSES: ReviewStatus[] = ["not_reviewed", "draft", "awaiting_publish", "fixed", "closed", "no_review"];

/** The table's action: a conversation with a priority is reviewed (or its draft edited) until
 * it is fixed or closed; everything else is viewed. */
export function actionFor(item: Pick<ConversationSummary, "priority" | "review_status">): "Review" | "Edit draft" | "View" {
  if (item.priority === null) return "View";
  if (item.review_status === "draft") return "Edit draft";
  if (item.review_status === "not_reviewed" || item.review_status === "awaiting_publish") return "Review";
  return "View";
}

function when(iso: string | null): string {
  if (!iso) return "—";
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleString();
}

function Transcript({ turns }: { turns: ConversationTurn[] }) {
  return (
    <ol className="knowledge-review-transcript">
      {turns.map((turn) => (
        <li key={turn.answer_id}>
          <p className="knowledge-review-transcript-question"><strong>Asked:</strong> {turn.question}</p>
          <p className="knowledge-review-transcript-answer">{turn.answer}</p>
          {turn.notices.map((notice) => <p key={notice} className="knowledge-review-meta">{notice}</p>)}
        </li>
      ))}
    </ol>
  );
}

function RatingSummary({ conversation }: { conversation: ReviewConversation }) {
  return (
    <dl className="knowledge-review-rating">
      <dt>Resolved</dt>
      <dd>{conversation.resolved === null ? "—" : conversation.resolved ? "Yes" : "No"}</dd>
      <dt>Satisfaction</dt>
      <dd>{conversation.satisfaction ? SATISFACTION_LABELS[conversation.satisfaction] : "—"}</dd>
      <dt>Priority</dt>
      <dd>{conversation.priority ? PRIORITY_LABELS[conversation.priority] : "None"}</dd>
      <dt>Review status</dt>
      <dd>{STATUS_LABELS[conversation.review_status]}</dd>
      <dt>{conversation.resolved ? "Additional comments" : "How it should be improved"}</dt>
      <dd>{conversation.comment || "—"}</dd>
      {conversation.close_reason && (
        <>
          <dt>Closed because</dt>
          <dd>{conversation.close_reason}</dd>
        </>
      )}
    </dl>
  );
}

/**
 * Support's Knowledge Review tab (D-103, D-105): every rated conversation, 10 a page, filtered by
 * resolved, satisfaction and review status, ordered high, medium, low, then no priority.
 * Neutral is low, unsatisfied medium and very unsatisfied high priority; satisfied or better has
 * none. A conversation with a priority is reviewed: its request page shows what happened, and
 * Support writes the fix (saved as a draft, or saved and published after seeing the final text)
 * or closes it with a reason. Support is the single reviewer (D-083). Pending knowledge from
 * elsewhere (for example HR's guidance proposals) is listed only when there is any. Every
 * action is checked again by the backend.
 */
export default function KnowledgeReview({
  onAskAboutCase,
  onLeaveCase,
}: {
  /** Opens the AI Assistant on the conversation's case, with the user's question (D-105). */
  onAskAboutCase?: (caseId: string, question: string) => void;
  /** The conversation page closed: the AI Assistant goes back to the rules chat. */
  onLeaveCase?: () => void;
} = {}) {
  const [filters, setFilters] = useState<ReviewFilters>({ page: 1 });
  const [list, setList] = useState<ConversationPage | null>(null);
  const [queue, setQueue] = useState<KnowledgeReviewQueue | null>(null);
  const [approved, setApproved] = useState<KnowledgeEntry[]>([]);
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const [reasons, setReasons] = useState<Record<number, string>>({});
  // The latest "Try with this change" preview, per request.
  const [trials, setTrials] = useState<Record<number, RuleTrial>>({});
  const [fixes, setFixes] = useState<Record<number, FixDraft>>({});
  // The entry whose final text is shown for confirmation before it is published.
  const [confirming, setConfirming] = useState<KnowledgeEntry | null>(null);
  // Whether the backend runs the POC's single-reviewer mode (D-083).
  const [singleReviewer, setSingleReviewer] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const page = useRef<HTMLElement>(null);
  // The conversation open as a page, and the row to return focus to.
  const [openConversation, setOpenConversation] = useState<ReviewConversation | null>(null);
  const openRef = useRef<ReviewConversation | null>(null);
  openRef.current = openConversation;
  const returnTo = useRef<string | null>(null);
  const openRequest = openConversation?.request ?? null;

  const leaveRef = useRef(onLeaveCase);
  leaveRef.current = onLeaveCase;

  // On a conversation page, Escape goes back to the list.
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent): void {
      if (event.key !== "Escape" || !openRef.current) return;
      event.preventDefault();
      leaveRef.current?.();
      setOpenConversation(null);
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  // Back from a conversation page: focus returns to the button that opened it.
  useEffect(() => {
    if (openConversation || returnTo.current === null) return;
    page.current?.querySelector<HTMLElement>(`[data-open-conversation="${returnTo.current}"]`)?.focus();
    returnTo.current = null;
  }, [openConversation]);

  // Opening a request: its saved draft, or else the AI's left-out lines from its answer record,
  // unless the reviewer already wrote something. Nothing is saved until Save.
  useEffect(() => {
    if (!openConversation || !openRequest || fixes[openRequest.id]) return undefined;
    const id = openRequest.id;
    if (openConversation.draft) {
      setFixes((all) => (all[id] ? all : { ...all, [id]: fixFromSaved(openConversation.draft as ConversationDraft) }));
      return undefined;
    }
    if (!openRequest.answer_id || openConversation.review_status !== "not_reviewed") return undefined;
    const controller = new AbortController();
    fetchFixStart(id, controller.signal)
      .then((start) => {
        if (controller.signal.aborted || start.lines.length === 0) return;
        setFixes((all) =>
          all[id]
            ? all
            : {
                ...all,
                [id]: {
                  ...EMPTY_FIX,
                  title: start.title,
                  body: startingBody(start.lines),
                  startLines: start.lines,
                  startTitle: start.title,
                  autoTitle: start.title,
                  autoBody: startingBody(start.lines),
                },
              },
        );
      })
      .catch(() => undefined); // the form simply starts empty
    return () => controller.abort();
    // Runs when a conversation page opens, not on every keystroke in its form.
  }, [openConversation]);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      fetchReviewConversations(filters, controller.signal),
      fetchKnowledgeReviews(controller.signal),
      fetchApprovedEntries(controller.signal),
      fetchKnowledgeAccess(controller.signal),
    ])
      .then(([conversations, reviews, entries, access]) => {
        if (controller.signal.aborted) return;
        setSingleReviewer(access.single_reviewer === true);
        setList(conversations);
        setQueue(reviews);
        setApproved(entries);
        setDrafts(Object.fromEntries(reviews.pending.map((entry) => [entry.key, draftOf(entry)])));
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) setError(message(reason));
      });
    return () => controller.abort();
  }, [tick, filters]);

  function filter(update: Partial<ReviewFilters>): void {
    setFilters((current) => ({ ...current, ...update, page: update.page ?? 1 }));
  }

  async function open(item: ConversationSummary): Promise<void> {
    setBusy(`open-${item.conversation_id}`);
    setError(null);
    setNotice(null);
    try {
      const detail = await fetchReviewConversation(item.conversation_id);
      returnTo.current = item.conversation_id;
      setConfirming(null);
      setOpenConversation(detail);
    } catch (reason) {
      setError(message(reason));
    } finally {
      setBusy(null);
    }
  }

  function backToList(text?: string): void {
    onLeaveCase?.();
    setOpenConversation(null);
    setConfirming(null);
    if (text) setNotice(text);
    setTick((value) => value + 1);
  }

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

  // Approve and Reject apply to exactly the content shown. Approving publishes, so it only
  // follows the confirmation step (see `confirming`).
  async function decide(entry: KnowledgeEntry, approve: boolean, notes = ""): Promise<void> {
    setBusy(entry.key);
    setError(null);
    try {
      const decided = await decideKnowledgeEntry(entry, approve, notes, approve);
      const text = !approve
        ? "Rejected: it will not be used."
        : decided.single_reviewer
          ? "Published as the only reviewer: recorded as a single-reviewer decision."
          : "Approved: it can now help answer similar questions.";
      if (openRef.current) {
        backToList(text);
      } else {
        setConfirming(null);
        setNotice(text);
        setTick((value) => value + 1);
      }
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
      setNotice("Changes saved as a new version to review.");
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

  // Save as draft: kept on the conversation (redacted), not knowledge yet.
  async function saveDraft(conversation: ReviewConversation, gap: KnowledgeGap): Promise<void> {
    const fix = fixes[gap.id] ?? EMPTY_FIX;
    setBusy(`gap-${gap.id}`);
    setError(null);
    try {
      await saveConversationDraft(conversation.conversation_id, draftToSave(fix));
      setFixes(({ [gap.id]: _saved, ...rest }) => rest);
      backToList("Saved as draft. Edit draft from the list to continue.");
    } catch (reason) {
      setError(message(reason));
    } finally {
      setBusy(null);
    }
  }

  async function discardDraft(conversation: ReviewConversation, gap: KnowledgeGap): Promise<void> {
    setBusy(`gap-${gap.id}`);
    setError(null);
    try {
      await discardConversationDraft(conversation.conversation_id);
      setFixes(({ [gap.id]: _dropped, ...rest }) => rest);
      backToList("Draft discarded.");
    } catch (reason) {
      setError(message(reason));
    } finally {
      setBusy(null);
    }
  }

  // Save and publish: the fix is saved (pending), then its final text is shown to confirm.
  async function saveAndConfirm(id: number): Promise<void> {
    const fix = fixes[id];
    if (!fix || !fixReady(fix)) return;
    setBusy(`gap-${id}`);
    setError(null);
    try {
      const entry = await draftFromKnowledgeGap(id, fixOf(fix));
      setFixes(({ [id]: _saved, ...rest }) => rest);
      setConfirming(entry);
    } catch (reason) {
      setError(message(reason));
    } finally {
      setBusy(null);
    }
  }

  // Try with this change: the user's question answered with the unsaved change (only Support
  // sees it; nothing is saved or published).
  async function tryChange(conversation: ReviewConversation, gap: KnowledgeGap): Promise<void> {
    const fix = fixes[gap.id] ?? EMPTY_FIX;
    if (!fix.body.trim()) return;
    setBusy(`try-${gap.id}`);
    setError(null);
    try {
      const trial = await tryRuleChange(conversation.conversation_id, {
        kind: fix.kind,
        title: fix.title,
        body: fix.body,
        entry_id: fix.kind === "guidance" && fix.changes ? fix.changes : null,
        ...appliesTo(fix),
      });
      setTrials((all) => ({ ...all, [gap.id]: trial }));
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
      setReasons(({ [id]: _closed, ...rest }) => rest);
      backToList("Closed with a reason.");
    } catch (reason) {
      setError(message(reason));
    } finally {
      setBusy(null);
    }
  }

  // The final text of a fix, confirmed before it goes live.
  function confirmBlock(entry: KnowledgeEntry): ReactNode {
    const disabled = busy !== null;
    return (
      <section className="knowledge-review-confirm" aria-label="Confirm publishing">
        <p className="knowledge-review-meta">
          This exact text goes live for{" "}
          {entry.visibility.teams.length ? `teams ${entry.visibility.teams.join(", ")}` : "every team"}
          {entry.visibility.roles.length ? ` (roles ${entry.visibility.roles.join(", ")})` : ""}.
          {singleReviewer ? " You are its only reviewer: publishing is recorded as a single-reviewer decision." : ""}
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
    );
  }

  // The fix for one conversation's request, written on its page below what happened.
  function requestFix(conversation: ReviewConversation, gap: KnowledgeGap): ReactNode {
    const why = reasons[gap.id] ?? "";
    const fix = fixes[gap.id] ?? EMPTY_FIX;
    const disabled = busy !== null;
    if (confirming) return confirmBlock(confirming);
    if (conversation.review_status === "awaiting_publish") {
      // Saved earlier but not published yet: its final text is confirmed here.
      const pending = queue?.pending.find((entry) => entry.entry_id === gap.entry_id);
      return pending ? (
        <section className="knowledge-review-entry request-page-fix" aria-labelledby="request-page-fix">
          <h3 id="request-page-fix">Publish the saved fix</h3>
          {error && <p className="ai-assistant-error" role="alert">{error}</p>}
          <button type="button" className="btn btn-primary" disabled={disabled} onClick={() => setConfirming(pending)}>
            Check and publish
          </button>
        </section>
      ) : null;
    }
    return (
      <section className="knowledge-review-entry request-page-fix" aria-labelledby="request-page-fix">
        <h3 id="request-page-fix">Edit how the AI should respond</h3>
        <p className="knowledge-review-meta knowledge-review-scope">
          You are only changing the approved rules the AI Assistant may use. No case, case data or onboarding logic is changed.
        </p>
        {error && <p className="ai-assistant-error" role="alert">{error}</p>}
        <fieldset className="knowledge-review-fix">
          <legend>Write the fix</legend>
          {conversation.draft && (
            <p className="knowledge-review-meta" role="note">
              Draft saved by {conversation.draft_by ?? "a reviewer"} {when(conversation.draft_at)}.
            </p>
          )}
          {fix.startLines.length > 0 && (
            <div className="knowledge-review-started" role="note">
              <p>Started from the AI's answer. Rewrite it as general guidance and remove anything specific to this client.</p>
              <button type="button" className="btn btn-ghost" disabled={disabled} onClick={() => setFixes((all) => ({ ...all, [gap.id]: EMPTY_FIX }))}>
                Clear
              </button>
            </div>
          )}
          <label>
            Fix as
            <select
              value={modeOf(fix)}
              disabled={disabled}
              onChange={(event) => {
                const mode = event.target.value as FixMode;
                // A new rule starts from what the fix was started with; an edit starts once its
                // rule is chosen.
                changeFix(gap.id, {
                  kind: "guidance",
                  editing: mode === "edit",
                  changes: "",
                  ...(mode !== "edit" && fix.startLines.length ? refill(fix, fix.startTitle, startingBody(fix.startLines)) : {}),
                });
              }}
            >
              <option value="edit">Edit a rule</option>
              <option value="new">Add a new rule</option>
            </select>
          </label>
          {modeOf(fix) === "edit" && (
            <label>
              Rule to edit
              <select
                value={fix.changes}
                disabled={disabled}
                onChange={(event) => {
                  const current = approved.find((entry) => entry.entry_id === event.target.value);
                  // Editing starts from the rule's current title and approved text, the AI's
                  // left-out lines below it.
                  changeFix(gap.id, {
                    changes: event.target.value,
                    ...(current ? refill(fix, current.title, startingBody(fix.startLines, current)) : {}),
                  });
                }}
              >
                <option value="">Choose a rule…</option>
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
            {fix.kind === "guidance" ? "Guidance text" : "What resolves it"}
            <textarea rows={4} maxLength={4000} value={fix.body} disabled={disabled} onChange={(event) => changeFix(gap.id, { body: event.target.value })} />
          </label>
          {(() => {
            const placeholders = placeholdersIn(fix);
            // Publishing stays disabled until every placeholder is rewritten in general terms.
            return placeholders.length > 0 ? (
              <p className="knowledge-review-placeholders" role="status">
                Rewrite{" "}
                {placeholders.map((placeholder, index) => (
                  <span key={placeholder}>
                    {index > 0 && ", "}
                    <mark>{placeholder}</mark>
                  </span>
                ))}{" "}
                in general terms before saving.
              </p>
            ) : null;
          })()}
          {fix.kind === "guidance" ? (
            <>
              <label>
                Source reference
                <input value={fix.sourceRef} maxLength={300} disabled={disabled} onChange={(event) => changeFix(gap.id, { sourceRef: event.target.value })} />
              </label>
              <fieldset className="knowledge-review-applies">
                <legend>When it applies (comma-separated; blank uses this case's topics)</legend>
                <label>
                  Blocker codes
                  <input value={fix.blockerCodes} placeholder={gap.blocker_codes.join(", ")} disabled={disabled} onChange={(event) => changeFix(gap.id, { blockerCodes: event.target.value })} />
                </label>
                <label>
                  Fields
                  <input value={fix.fieldTags} placeholder={gap.fields.join(", ")} disabled={disabled} onChange={(event) => changeFix(gap.id, { fieldTags: event.target.value })} />
                </label>
                <label>
                  Stages
                  <input value={fix.stageTags} placeholder={gap.stages.join(", ")} disabled={disabled} onChange={(event) => changeFix(gap.id, { stageTags: event.target.value })} />
                </label>
              </fieldset>
            </>
          ) : null}
          {(() => {
            const trial = trials[gap.id];
            if (!trial) return null;
            const before = conversation.turns[0]?.answer ?? "";
            return (
              <section className="knowledge-review-trial" aria-label="Try with this change">
                <p className="knowledge-review-meta">Preview only you can see. Nothing was saved or published.</p>
                <div className="knowledge-review-trial-columns">
                  <div>
                    <h4>Before (what the user saw)</h4>
                    <p className="knowledge-review-final">{before}</p>
                  </div>
                  <div>
                    <h4>After (with this change)</h4>
                    <p className="knowledge-review-final">{trial.answer}</p>
                    {trial.notice && <p className="knowledge-review-meta">{trial.notice}</p>}
                  </div>
                </div>
                <p className="knowledge-review-meta">
                  {trial.offered_lines.length === 0
                    ? "None of this change's sentences passed the checks on this case, so the AI cannot use them."
                    : trial.used
                      ? `The answer used this change (${trial.offered_lines.length} sentence${trial.offered_lines.length === 1 ? "" : "s"} offered).`
                      : `The AI was offered ${trial.offered_lines.length} sentence${trial.offered_lines.length === 1 ? "" : "s"} of this change but did not use them.`}
                </p>
              </section>
            );
          })()}
          {/* P2-3: the external-data notice, before the change is tried. */}
          <ExternalAiNotice id={`knowledge-review-try-notice-${gap.id}`} surface="try" />
          <div className="knowledge-review-actions">
            <button
              type="button"
              className="btn btn-secondary"
              aria-describedby={`knowledge-review-try-notice-${gap.id}`}
              disabled={disabled || !fix.body.trim()}
              onClick={() => void tryChange(conversation, gap)}
            >
              Try with this change
            </button>
            <button type="button" className="btn btn-secondary" disabled={disabled} onClick={() => void saveDraft(conversation, gap)}>
              Save as draft
            </button>
            <button type="button" className="btn btn-primary" disabled={disabled || !fixReady(fix)} onClick={() => void saveAndConfirm(gap.id)}>
              Save and publish
            </button>
            {conversation.draft && (
              <button type="button" className="btn btn-ghost" disabled={disabled} onClick={() => void discardDraft(conversation, gap)}>
                Discard draft
              </button>
            )}
          </div>
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
      </section>
    );
  }

  if (openConversation) {
    const reviewing = actionFor(openConversation) !== "View" && openRequest !== null;
    return (
      <section ref={page} className="ds-root ds-page knowledge-review knowledge-review-page" aria-labelledby="conversation-title">
        <button type="button" className="btn btn-ghost" onClick={() => backToList()}>
          ← Back to all conversations
        </button>
        <h1 id="conversation-title">{reviewing ? "Review conversation" : "View conversation"}</h1>
        <p className="knowledge-review-meta">
          {openConversation.title} · rated {when(openConversation.ended_at)} · {openConversation.answers}{" "}
          {openConversation.answers === 1 ? "answer" : "answers"}
        </p>
        <RatingSummary conversation={openConversation} />
        <details className="knowledge-review-whole">
          <summary>The whole conversation ({openConversation.turns.length})</summary>
          <Transcript turns={openConversation.turns} />
        </details>
        {reviewing && openRequest ? (
          <>
            {onAskAboutCase && (
              <div className="knowledge-review-actions">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => onAskAboutCase(openConversation.case_id, openConversation.title)}
                >
                  Ask the AI Assistant about this case
                </button>
                <span className="knowledge-review-meta">Read-only: asking does not change the case.</span>
              </div>
            )}
            <RequestPage gap={openRequest} onBack={() => backToList()} embedded />
            {requestFix(openConversation, openRequest)}
          </>
        ) : null}
      </section>
    );
  }

  const pages = list ? Math.max(1, Math.ceil(list.total / list.page_size)) : 1;
  const pending = queue?.pending ?? [];
  return (
    <section ref={page} className="ds-root ds-page knowledge-review" aria-labelledby="knowledge-review-title">
      <header className="knowledge-review-header">
        <h1 id="knowledge-review-title">Knowledge review</h1>
      </header>
      <p className="knowledge-review-intro">
        Conversations users rated with End conversation. Neutral is low, unsatisfied medium and very unsatisfied high
        priority; satisfied or better needs no review. Fixes change how the AI Assistant answers (its approved rules),
        never a case.
      </p>
      {notice && <p className="knowledge-review-notice" role="status">{notice}</p>}
      {error && <p className="ai-assistant-error" role="alert">{error}</p>}

      <div className="knowledge-review-filters" role="group" aria-label="Filters">
        <label>
          Resolved
          <select
            value={filters.resolved === undefined ? "" : String(filters.resolved)}
            onChange={(event) => filter({ resolved: event.target.value === "" ? undefined : event.target.value === "true" })}
          >
            <option value="">All</option>
            <option value="true">Yes</option>
            <option value="false">No</option>
          </select>
        </label>
        <label>
          How satisfied
          <select
            value={filters.satisfaction ?? ""}
            onChange={(event) => filter({ satisfaction: (event.target.value || undefined) as Satisfaction | undefined })}
          >
            <option value="">All</option>
            {(Object.keys(SATISFACTION_LABELS) as Satisfaction[]).map((value) => (
              <option key={value} value={value}>{SATISFACTION_LABELS[value]}</option>
            ))}
          </select>
        </label>
        <label>
          Review status
          <select
            value={filters.status ?? ""}
            onChange={(event) => filter({ status: (event.target.value || undefined) as ReviewStatus | undefined })}
          >
            <option value="">All</option>
            {FILTER_STATUSES.map((value) => (
              <option key={value} value={value}>{STATUS_LABELS[value]}</option>
            ))}
          </select>
        </label>
      </div>

      {!list && !error && <p className="ai-assistant-hint">Loading…</p>}
      {list && list.items.length === 0 && <p className="ai-assistant-hint">No rated conversations match.</p>}
      {list && list.items.length > 0 && (
        <div className="table-card table-scroll" tabIndex={0}>
          <table className="table knowledge-review-table">
            <thead>
              <tr>
                <th>Question</th>
                <th>Rated</th>
                <th>Resolved</th>
                <th>How satisfied</th>
                <th>Priority</th>
                <th>Review status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {list.items.map((item) => {
                const action = actionFor(item);
                return (
                  <tr key={item.conversation_id}>
                    <td>{item.title}</td>
                    <td>{when(item.ended_at)}</td>
                    <td>{item.resolved === null ? "—" : item.resolved ? "Yes" : "No"}</td>
                    <td>{item.satisfaction ? SATISFACTION_LABELS[item.satisfaction] : "—"}</td>
                    <td>
                      {item.priority ? (
                        <span className={`knowledge-review-priority knowledge-review-priority-${item.priority}`}>{PRIORITY_LABELS[item.priority]}</span>
                      ) : (
                        "None"
                      )}
                    </td>
                    <td>{STATUS_LABELS[item.review_status]}</td>
                    <td>
                      <button
                        type="button"
                        className={action === "View" ? "btn btn-ghost" : "btn btn-primary"}
                        data-open-conversation={item.conversation_id}
                        disabled={busy !== null}
                        onClick={() => void open(item)}
                      >
                        {action}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {list && pages > 1 && (
        <div className="knowledge-review-actions" aria-label="Pages">
          <button type="button" className="btn btn-ghost" disabled={filters.page <= 1} onClick={() => filter({ page: filters.page - 1 })}>
            Previous
          </button>
          <span className="knowledge-review-meta">Page {filters.page} of {pages} · {list.total} conversations</span>
          <button type="button" className="btn btn-ghost" disabled={filters.page >= pages} onClick={() => filter({ page: filters.page + 1 })}>
            Next
          </button>
        </div>
      )}

      {pending.length > 0 && (
        <details className="knowledge-review-pending">
          <summary>Pending knowledge ({pending.length})</summary>
          {pending.map((entry) => {
            const draft = drafts[entry.key] ?? draftOf(entry);
            const disabled = busy !== null;
            const { edited } = changes(entry, draft);
            return (
              <article key={entry.key} className="knowledge-review-entry" aria-label={`Review ${entry.title}`}>
                <p className="knowledge-review-meta">
                  {entry.kind === "guidance" ? "Guidance" : "Past resolution"} · by {entry.author}
                  {entry.revises !== null ? ` · edited from version ${entry.revises}` : ""}
                  {entry.started_from_answer ? " · started from the AI's answer" : ""}
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
                  confirmBlock(entry)
                ) : (
                  <div className="knowledge-review-actions">
                    {edited ? (
                      <>
                        <button type="button" className="btn btn-primary" disabled={disabled} onClick={() => void saveChanges(entry)}>
                          Save changes as a new version
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
                        <button type="button" className="btn btn-secondary" disabled={disabled} onClick={() => void decide(entry, false, draft.notes)}>
                          Reject
                        </button>
                      </>
                    )}
                  </div>
                )}
              </article>
            );
          })}
        </details>
      )}
    </section>
  );
}
