import { useEffect, useRef, useState } from "react";
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

function WhatTheRmSaw({ gap, record }: { gap: KnowledgeGap; record: AnswerRecord }) {
  const [earlier, setEarlier] = useState<Record<string, AnswerRecord>>({});
  const [error, setError] = useState<string | null>(null);

  function load(answerId: string): void {
    fetchGapEarlierAnswer(gap.id, answerId)
      .then((found) => setEarlier((all) => ({ ...all, [answerId]: found })))
      .catch((reason: unknown) => setError(errorText(reason)));
  }

  return (
    <section className="request-page-column" aria-labelledby="request-page-saw">
      <h3 id="request-page-saw">What the RM saw</h3>
      {record.earlier_answer_ids.length > 0 && (
        <div className="request-page-earlier">
          <h4>Earlier in this chat</h4>
          {record.earlier_answer_ids.map((answerId, index) =>
            earlier[answerId] ? (
              <Exchange key={answerId} record={earlier[answerId]} />
            ) : (
              <button key={answerId} type="button" className="btn" onClick={() => load(answerId)}>
                Show earlier answer {index + 1}
              </button>
            ),
          )}
          {error && <p className="ai-assistant-error" role="alert">{error}</p>}
        </div>
      )}
      <h4>The question and answer</h4>
      <Exchange record={record} />
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
  const sources = new Map(record.allowed_lines.map((line) => [line.text, line.source]));
  const { knowledge, result, case_snapshot: snapshot } = record;
  return (
    <section className="request-page-column" aria-labelledby="request-page-why">
      <h3 id="request-page-why">Why the AI answered this way</h3>
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
      <dl className="request-page-facts">
        <dt>Answered by</dt>
        <dd>
          {result.answered_by === "model" ? `the AI model (${result.model ?? "unknown"})` : "the case data"}
          {` in ${(result.elapsed_ms / 1000).toFixed(1)} s`}
        </dd>
        <dt>Fallback</dt>
        <dd>{result.fallback_reason ? FALLBACK_REASONS[result.fallback_reason] : "None: a full model answer."}</dd>
      </dl>

      <h4>Lines shown to the RM</h4>
      {record.chosen_lines.length ? (
        <ul className="request-page-lines">
          {record.chosen_lines.map((line) => (
            <li key={line}><SourceTag source={sources.get(line)} /> {line}</li>
          ))}
        </ul>
      ) : (
        <p className="knowledge-review-meta">None of the AI's lines was shown.</p>
      )}

      <h4>Lines left out</h4>
      {record.dropped_lines.length ? (
        <ul className="request-page-lines">
          {record.dropped_lines.map((line, index) => (
            <li key={`${index}-${line}`}>
              <del>{line}</del>
              <span className="request-page-reason">Not an allowed line: only exact allowed lines are shown.</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="knowledge-review-meta">None.</p>
      )}

      <h4>Knowledge searched</h4>
      <p className="knowledge-review-meta">
        Thresholds: guidance {knowledge.thresholds.guidance}, past cases {knowledge.thresholds.resolution}
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
                <td>{entry.kind === "guidance" ? knowledge.thresholds.guidance : knowledge.thresholds.resolution}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="knowledge-review-meta">No entry scored above its threshold.</p>
      )}

      <details className="request-page-allowed">
        <summary>All allowed lines ({record.allowed_lines.length})</summary>
        <ul className="request-page-lines">
          {record.allowed_lines.map((line) => (
            <li key={line.text}><SourceTag source={line.source} /> {line.text}</li>
          ))}
        </ul>
      </details>

      <h4>The case at the time</h4>
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
    </section>
  );
}

/**
 * The full-width page for one enhancement request: what the RM saw and why the AI answered
 * that way, from the service's answer record (opening it is a logged view). Fixes, similar
 * requests and the grouped queue come later.
 */
export default function RequestPage({ gap, onBack }: { gap: KnowledgeGap; onBack: () => void }) {
  const [record, setRecord] = useState<AnswerRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const heading = useRef<HTMLHeadingElement>(null);

  const hasRecord = Boolean(gap.answer_id);

  useEffect(() => {
    // Focus the title without scrolling past the Back button above it.
    heading.current?.focus({ preventScroll: true });
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
      <header className="request-page-header">
        <button type="button" className="btn" onClick={onBack}>← Back to Knowledge review</button>
        <h2 id="knowledge-review-title" ref={heading} tabIndex={-1}>Enhancement request {gap.id}</h2>
        <p className="knowledge-review-meta">{gap.blocker_codes.join(", ") || "General"}</p>
      </header>
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
    </div>
  );
}
