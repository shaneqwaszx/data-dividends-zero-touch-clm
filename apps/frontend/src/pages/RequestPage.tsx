import { type ReactNode, useEffect, useRef, useState } from "react";
import {
  AiAssistantError,
  type AllowedLineSource,
  type AnswerRecord,
  fetchGapAnswer,
  fetchGapEarlierAnswer,
  type KnowledgeGap,
} from "../aiAssistant";

const SOURCE_LABELS: Record<AllowedLineSource, string> = {
  policy: "Policy",
  case: "Case",
  knowledge: "Knowledge",
};

const FALLBACK_REASONS: Record<NonNullable<AnswerRecord["result"]["fallback_reason"]>, string> = {
  model_unavailable: "The AI model was not available, so the answer came from the case data.",
  nothing_allowed: "None of the AI's lines was an allowed line, so the answer came from the case data.",
  cut_short: "The answer was cut short.",
};

export interface SuggestedCause {
  title: string;
  explanation: string;
}

/**
 * A first guess at why the answer missed, from three simple rules (in this order). It is a
 * hint for the Director, not a verdict. No rule applies when the model was not available.
 */
export function suggestedCause(record: AnswerRecord): SuggestedCause | null {
  if (record.result.fallback_reason === "model_unavailable") return null;
  const dropped = Math.max(record.result.left_out, record.dropped_lines.length);
  if (dropped > 0 && record.chosen_lines.length === 0) {
    return {
      title: "Catalog gap: no allowed line matched",
      explanation:
        "Every line the AI wrote was left out, because none is an allowed line. The line the RM needed may be missing from the allowed lines.",
    };
  }
  if (record.knowledge.entries.length === 0) {
    return {
      title: "No knowledge found",
      explanation: "No guidance or past case scored above its threshold for this question.",
    };
  }
  if (dropped > 0) {
    return {
      title: "Missing knowledge",
      explanation:
        "Knowledge was used, but some of the AI's lines were left out: the knowledge may not cover what the RM asked.",
    };
  }
  return null;
}

/** An allowed line with its source; the earliest records kept plain lines with none. */
function allowedLine(line: AnswerRecord["allowed_lines"][number]): { text: string; source?: AllowedLineSource } {
  return typeof line === "string" ? { text: line } : line;
}

function errorText(reason: unknown): string {
  return reason instanceof AiAssistantError ? reason.message : "Could not load this request.";
}

function SourceTag({ source }: { source: AllowedLineSource | undefined }) {
  if (!source) return null;
  return <span className={`request-page-tag request-page-tag-${source}`}>{SOURCE_LABELS[source]}</span>;
}

/** The question and the answer exactly as the RM saw them. */
function Exchange({ record }: { record: AnswerRecord }) {
  return (
    <div className="request-page-exchange">
      <p className="request-page-bubble request-page-question">{record.question}</p>
      <div className="request-page-bubble request-page-answer">
        <p className="request-page-answer-text">{record.shown_answer || "The answer text was not kept for this record."}</p>
        {record.result.notices.map((notice) => <p key={notice} className="request-page-notice">{notice}</p>)}
      </div>
    </div>
  );
}

/** An earlier exchange: loaded (and so logged as a view), gone, or still loading. */
type Earlier = { record: AnswerRecord } | { missing: true } | { error: string };

const MISSING_EARLIER = "This earlier answer is no longer available.";

/**
 * The earlier exchanges of the chat (at most two, which the service keeps with the request),
 * folded and closed by default. Each is fetched, and so logged as a view, only when opened.
 */
function EarlierInThisChat({ gap, answerIds }: { gap: KnowledgeGap; answerIds: string[] }) {
  const [earlier, setEarlier] = useState<Record<string, Earlier>>({});
  const loaded = useRef(false);

  function open(): void {
    if (loaded.current) return;
    loaded.current = true;
    for (const answerId of answerIds) {
      fetchGapEarlierAnswer(gap.id, answerId)
        .then((found) => setEarlier((all) => ({ ...all, [answerId]: { record: found } })))
        .catch((reason: unknown) =>
          setEarlier((all) => ({
            ...all,
            // Deleted or never kept: say so rather than show the service's error code.
            [answerId]: reason instanceof AiAssistantError && reason.status === 404 ? { missing: true } : { error: errorText(reason) },
          })),
        );
    }
  }

  return (
    <details className="request-page-earlier" onToggle={(event) => event.currentTarget.open && open()}>
      <summary>Earlier in this chat ({answerIds.length})</summary>
      {answerIds.map((answerId) => {
        const item = earlier[answerId];
        if (!item) return <p key={answerId} className="ai-assistant-hint">Loading…</p>;
        if ("record" in item) return <Exchange key={answerId} record={item.record} />;
        if ("missing" in item) return <p key={answerId} className="knowledge-review-meta">{MISSING_EARLIER}</p>;
        return <p key={answerId} className="ai-assistant-error" role="alert">{item.error}</p>;
      })}
    </details>
  );
}

function WhatTheRmSaw({ gap, record }: { gap: KnowledgeGap; record: AnswerRecord }) {
  return (
    <section className="request-page-column" aria-labelledby="request-page-saw">
      <h3 id="request-page-saw">What the RM saw</h3>
      <h4>The question and answer</h4>
      <Exchange record={record} />
      {record.earlier_answer_ids.length > 0 && <EarlierInThisChat gap={gap} answerIds={record.earlier_answer_ids} />}
      {record.result.answered_by === "case_data" && (
        <p className="knowledge-review-meta">Answered from the case data: names, UENs and addresses are removed here.</p>
      )}
      <h4>The RM's note</h4>
      <blockquote className="request-page-note">{gap.note || "No note given."}</blockquote>
    </section>
  );
}

function WhyItAnsweredThisWay({ record }: { record: AnswerRecord }) {
  const cause = suggestedCause(record);
  const allowed = record.allowed_lines.map(allowedLine);
  const sources = new Map(allowed.map((line) => [line.text, line.source]));
  const { knowledge, result, case_snapshot: snapshot } = record;
  const thresholds = knowledge.thresholds;
  return (
    <section className="request-page-column" aria-labelledby="request-page-why">
      {/* D-105: what the AI had to work with, each part folded until opened. */}
      <h3 id="request-page-why">Information / rules used</h3>
      <div className="request-page-cause" role="note" aria-label="Suggested cause">
        <p className="request-page-cause-label">Rule-based hint, not a verdict</p>
        {cause ? (
          <>
            <p className="request-page-cause-title">{cause.title}</p>
            <p>{cause.explanation}</p>
          </>
        ) : (
          <p className="request-page-cause-title">
            {result.fallback_reason === "model_unavailable"
              ? "No hint: the AI model was not available."
              : "No rule matched."}
          </p>
        )}
      </div>
      <details className="request-page-part">
      <summary>How it was answered</summary>
      <dl className="request-page-facts">
        <dt>Answered by</dt>
        <dd>
          {result.answered_by === "model" ? `the AI model (${result.model ?? "unknown"})` : "the case data"}
          {` in ${(result.elapsed_ms / 1000).toFixed(1)} s`}
        </dd>
        <dt>Fallback</dt>
        <dd>{result.fallback_reason ? FALLBACK_REASONS[result.fallback_reason] : "None: a full model answer."}</dd>
      </dl>
      </details>

      <details className="request-page-part">
      <summary>Lines shown to the user ({record.chosen_lines.length})</summary>
      {record.chosen_lines.length ? (
        <ul className="request-page-lines">
          {record.chosen_lines.map((line) => (
            <li key={line}><SourceTag source={sources.get(line)} /> {line}</li>
          ))}
        </ul>
      ) : (
        <p className="knowledge-review-meta">None of the AI's lines was shown.</p>
      )}
      </details>

      <details className="request-page-part">
      <summary>Lines the guard left out ({record.dropped_lines.length})</summary>
      {record.dropped_lines.length ? (
        <ul className="request-page-lines">
          {record.dropped_lines.map((line, index) => (
            <li key={`${index}-${line}`}>
              <del>{line}</del>
              <span className="request-page-reason">Not an allowed line: only allowed lines are shown, in the catalog's own words.</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="knowledge-review-meta">None.</p>
      )}
      </details>

      <details className="request-page-part">
      <summary>Knowledge found ({knowledge.entries.length})</summary>
      <p className="knowledge-review-meta">
        {thresholds ? `Thresholds: guidance ${thresholds.guidance}, past cases ${thresholds.resolution}` : "Thresholds: not recorded"}
        {knowledge.confidence && ` · confidence ${knowledge.confidence}`}
        {knowledge.degraded && " · keyword search only (the embedding model was down)"}
      </p>
      {knowledge.entries.length ? (
        <table className="request-page-table">
          <thead>
            <tr><th scope="col">Tag</th><th scope="col">Entry</th><th scope="col">Score</th><th scope="col">Threshold</th></tr>
          </thead>
          <tbody>
            {knowledge.entries.map((entry) => (
              <tr key={entry.tag}>
                <td>{entry.tag}</td>
                <td>{entry.entry_id} v{entry.version}{entry.fallback ? " (stage guidance)" : ""}</td>
                <td>{entry.score}</td>
                <td>{thresholds ? (entry.kind === "guidance" ? thresholds.guidance : thresholds.resolution) : "–"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="knowledge-review-meta">No entry scored above its threshold.</p>
      )}
      </details>

      <details className="request-page-allowed request-page-part">
        <summary>All rules offered ({allowed.length})</summary>
        <ul className="request-page-lines">
          {allowed.map((line) => (
            <li key={line.text}><SourceTag source={line.source} /> {line.text}</li>
          ))}
        </ul>
      </details>

      <details className="request-page-part">
      <summary>The case at the time</summary>
      <dl className="request-page-facts">
        <dt>Blockers</dt>
        <dd>{snapshot.blocker_codes.join(", ") || "None"}</dd>
        <dt>Stage</dt>
        <dd>{snapshot.stage ?? "Unknown"}</dd>
        <dt>Steps</dt>
        <dd>{snapshot.steps_done ?? "?"} of {snapshot.steps_total ?? "?"} done</dd>
        <dt>Facts</dt>
        <dd title={snapshot.facts_hash}>fingerprint {snapshot.facts_hash.slice(0, 12)}</dd>
      </dl>
      </details>
    </section>
  );
}

/**
 * The full-width page for one enhancement request: what the RM saw and why the AI answered
 * that way, from the service's answer record (opening it is a logged view), then the
 * Director's fix (``children``). Similar requests and the grouped queue come later.
 */
export default function RequestPage({
  gap,
  onBack,
  children,
  embedded = false,
}: {
  gap: KnowledgeGap;
  onBack: () => void;
  children?: ReactNode;
  /** Inside a conversation page (D-105), which has its own heading and Back button. */
  embedded?: boolean;
}) {
  const [record, setRecord] = useState<AnswerRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const heading = useRef<HTMLHeadingElement>(null);

  const hasRecord = Boolean(gap.answer_id);

  useEffect(() => {
    // Focus the title without scrolling past the Back button above it.
    if (!embedded) heading.current?.focus({ preventScroll: true });
    // A note sent when the answer record could not be saved: nothing to load (or log).
    if (!hasRecord) return;
    const controller = new AbortController();
    fetchGapAnswer(gap.id, controller.signal)
      .then(setRecord)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) setError(errorText(reason));
      });
    return () => controller.abort();
  }, [gap.id, hasRecord]);

  return (
    <div className="request-page">
      {embedded ? (
        <p className="knowledge-review-meta">Case topics: {gap.blocker_codes.join(", ") || "General"}</p>
      ) : (
        <header className="request-page-header">
          <button type="button" className="btn" onClick={onBack}>← Back to Knowledge review</button>
          <h2 id="knowledge-review-title" ref={heading} tabIndex={-1}>Enhancement request {gap.id}</h2>
          <p className="knowledge-review-meta">{gap.blocker_codes.join(", ") || "General"}</p>
        </header>
      )}
      {!hasRecord && (
        <section className="request-page-column" aria-labelledby="request-page-no-record">
          <h3 id="request-page-no-record">No answer record for this request</h3>
          <p className="knowledge-review-meta">
            The details of the answer could not be saved, so only the RM's note is shown.
          </p>
          <h4>The RM's note</h4>
          <blockquote className="request-page-note">{gap.note || "No note given."}</blockquote>
        </section>
      )}
      {error && <p className="ai-assistant-error" role="alert">{error}</p>}
      {hasRecord && !record && !error && <p className="ai-assistant-hint">Loading…</p>}
      {record && (
        <div className="request-page-columns">
          <WhatTheRmSaw gap={gap} record={record} />
          <WhyItAnsweredThisWay record={record} />
        </div>
      )}
      {children}
    </div>
  );
}
