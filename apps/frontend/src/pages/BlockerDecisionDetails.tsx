import type { BlockerDecisionRecord } from "../types";

export function decisionLabel(value: string): string {
  return value
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/^./, (letter) => letter.toUpperCase());
}

export function uniqueValues(values: readonly string[]): string[] {
  return [...new Set(values)];
}

export function uniqueDecisions(decisions: readonly BlockerDecisionRecord[]): BlockerDecisionRecord[] {
  const seen = new Set<string>();
  return decisions.filter((decision) => {
    if (seen.has(decision.decision_id)) return false;
    seen.add(decision.decision_id);
    return true;
  });
}

function ValueList({ values, empty }: { values: readonly string[]; empty: string }) {
  const unique = uniqueValues(values);
  return unique.length > 0
    ? <ul>{unique.map((value) => <li key={value}>{decisionLabel(value)}</li>)}</ul>
    : <span>{empty}</span>;
}

export default function BlockerDecisionDetails({
  decisions,
}: {
  decisions: readonly BlockerDecisionRecord[];
}) {
  const retained = uniqueDecisions(decisions);
  if (retained.length === 0) return null;

  return (
    <section className="blocker-decision-list" aria-label="Retained blocker decision policy">
      {retained.map((decision) => {
        const { metadata } = decision;
        const unknowns = uniqueValues(metadata.unknowns).filter(
          (unknown) => unknown !== metadata.blocker_code,
        );
        const unavailable = metadata.currently_available_actions.length === 0;
        const externalOrStop = metadata.classification === "EXTERNAL_DEPENDENCY"
          || metadata.classification === "HARD_STOP";
        return (
          <article
            key={decision.decision_id}
            className={`blocker-decision blocker-decision--${metadata.classification.toLowerCase()}`}
          >
            <header>
              <strong>{decisionLabel(metadata.classification)}</strong>
              <span>{metadata.policy_version} · rule {metadata.rule_version}</span>
            </header>
            <dl>
              <div><dt>Blocker code</dt><dd><code>{metadata.blocker_code}</code></dd></div>
              <div><dt>Policy owner</dt><dd>{decisionLabel(metadata.owner)}</dd></div>
              <div><dt>Minimum inputs</dt><dd><ValueList values={metadata.minimum_inputs} empty="No additional minimum input recorded" /></dd></div>
              <div><dt>Permitted actions</dt><dd><ValueList values={metadata.permitted_actions} empty="No permitted action recorded" /></dd></div>
              <div><dt>Currently available</dt><dd><ValueList values={metadata.currently_available_actions} empty="No action currently available" /></dd></div>
              <div>
                <dt>Resume transition</dt>
                <dd>
                  {decisionLabel(metadata.resume_transition)}
                  {metadata.resume_stage ? ` from ${decisionLabel(metadata.resume_stage)}` : ""}
                  {` · ${metadata.resume_ready ? "ready when server conditions hold" : "not currently resume-ready"}`}
                </dd>
              </div>
              <div><dt>Invalidated dependencies</dt><dd><ValueList values={metadata.invalidated_dependencies} empty="None" /></dd></div>
            </dl>
            <p className="blocker-decision__explanation">{metadata.explanation}</p>
            {unknowns.length > 0 && (
              <p className="blocker-decision__unknowns">
                <strong>Retained unknowns:</strong>{" "}
                {unknowns.map((unknown) => <code key={unknown}>{unknown}</code>)}
              </p>
            )}
            {(externalOrStop || unavailable) && (
              <p className="control-help blocker-decision__boundary">
                {metadata.classification === "EXTERNAL_DEPENDENCY"
                  ? "This dependency remains with the retained owner; the browser cannot complete it."
                  : metadata.classification === "HARD_STOP"
                    ? "This is a retained hard stop; this metadata does not create a browser action."
                    : "A permitted policy action is not currently available; no browser action was created."}
              </p>
            )}
            <p className="blocker-decision__provenance">
              Decision {decision.decision_id} · evidence {decision.evidence_version}
              {` · automation version ${decision.automation_version} · recorded ${new Date(decision.recorded_at).toLocaleString()}`}
            </p>
          </article>
        );
      })}
    </section>
  );
}
