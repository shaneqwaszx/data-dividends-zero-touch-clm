import { useState } from "react";
import { AiAssistantError, type AnswerRecord, fetchGapAnswer, fetchGapEarlierAnswer } from "../aiAssistant";

const FALLBACK_REASONS: Record<NonNullable<AnswerRecord["result"]["fallback_reason"]>, string> = {
  model_unavailable: "The AI model was not available, so the answer came from the case data.",
  nothing_allowed: "None of the model's lines was an allowed line, so the answer came from the case data.",
  cut_short: "The answer was cut short.",
};

function errorText(reason: unknown): string {
  return reason instanceof AiAssistantError ? reason.message : "Could not load what happened.";
}

function Lines({ lines, empty }: { lines: string[]; empty: string }) {
  if (!lines.length) return <p className="knowledge-review-meta">{empty}</p>;
  return (
    <ul className="what-happened-lines">
      {lines.map((line, index) => <li key={`${index}-${line}`}>{line}</li>)}
    </ul>
  );
}

/** One answer record: the question, what the AI was given, and what it kept and left out. */
function RecordView({ record }: { record: AnswerRecord }) {
  const { result, knowledge } = record;
  const dropped = record.dropped_lines.length || result.left_out;
  // The catalog-gap signal: the model tried to answer, but none of its lines was allowed.
  const noLineMatched = result.fallback_reason === "nothing_allowed";
  return (
    <div className="what-happened-record">
      {noLineMatched && (
        <p className="what-happened-gap" role="alert">
          <strong>No allowed line matched.</strong> The AI's answer was left out because none of its lines is an
          allowed line. The line the RM needed may be missing from the allowed lines.
        </p>
      )}
      {!noLineMatched && dropped > 0 && (
        <p className="what-happened-gap">
          {dropped === 1 ? "1 line didn't" : `${dropped} lines didn't`} match an allowed line.
        </p>
      )}
      <dl className="what-happened-facts">
        <dt>Question</dt>
        <dd>{record.question}</dd>
        <dt>Answered by</dt>
        <dd>
          {result.answered_by === "model" ? `the AI model (${result.model ?? "unknown"})` : "the case data"}
          {` in ${(result.elapsed_ms / 1000).toFixed(1)} s`}
        </dd>
        <dt>Fallback</dt>
        <dd>{result.fallback_reason ? FALLBACK_REASONS[result.fallback_reason] : "None: a full model answer."}</dd>
        <dt>Knowledge used</dt>
        <dd>
          {knowledge.entries.length
            ? knowledge.entries.map((entry) => `[${entry.tag}] ${entry.entry_id} v${entry.version} (score ${entry.score})`).join(", ")
            : "None"}
          {knowledge.confidence && ` · confidence ${knowledge.confidence}`}
          {knowledge.degraded && " · keyword search only"}
        </dd>
      </dl>
      <h4>Lines shown to the RM</h4>
      <Lines lines={record.chosen_lines} empty="None." />
      <h4>Lines left out</h4>
      <Lines lines={record.dropped_lines} empty="None." />
      <details>
        <summary>Allowed lines ({record.allowed_lines.length})</summary>
        <Lines lines={record.allowed_lines} empty="No allowed lines." />
      </details>
    </div>
  );
}

/**
 * "What happened" on an enhancement request: the server's record of the answer the RM rated,
 * loaded only when opened (every view is logged), with the earlier answers of that chat.
 */
export default function WhatHappened({ feedbackId }: { feedbackId: number }) {
  const [record, setRecord] = useState<AnswerRecord | null>(null);
  const [earlier, setEarlier] = useState<Record<string, AnswerRecord>>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function load(): void {
    if (record || loading) return;
    setLoading(true);
    fetchGapAnswer(feedbackId)
      .then(setRecord)
      .catch((reason: unknown) => setError(errorText(reason)))
      .finally(() => setLoading(false));
  }

  function loadEarlier(answerId: string): void {
    fetchGapEarlierAnswer(feedbackId, answerId)
      .then((found) => setEarlier((all) => ({ ...all, [answerId]: found })))
      .catch((reason: unknown) => setError(errorText(reason)));
  }

  return (
    <details className="what-happened" onToggle={(event) => event.currentTarget.open && load()}>
      <summary>What happened</summary>
      {loading && <p className="ai-assistant-hint">Loading…</p>}
      {error && <p className="ai-assistant-error" role="alert">{error}</p>}
      {record && <RecordView record={record} />}
      {record && record.earlier_answer_ids.length > 0 && (
        <div className="what-happened-earlier">
          <h4>Earlier answers in this chat</h4>
          {record.earlier_answer_ids.map((answerId, index) =>
            earlier[answerId] ? (
              <RecordView key={answerId} record={earlier[answerId]} />
            ) : (
              <button key={answerId} type="button" className="btn" onClick={() => loadEarlier(answerId)}>
                Show earlier answer {index + 1}
              </button>
            ),
          )}
        </div>
      )}
    </details>
  );
}
