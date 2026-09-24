import type { OnboardingIntelligenceRecord } from "../types";

function displayLabel(value: string): string {
  return value.toLowerCase().replaceAll("_", " ").replace(/^./, (item) => item.toUpperCase());
}

export default function IntelligencePanel({ record }: { record: OnboardingIntelligenceRecord }) {
  return (
    <section className="readiness-panel" aria-label="Advisory intelligence">
      <div className="section-heading">
        <div><p className="eyebrow">Explainable advisory evidence</p><h3>Onboarding intelligence</h3></div>
        <span className="status-badge status-info">ML assisted</span>
      </div>
      {record.entity_resolution && <div>
        <h4>Entity resolution</h4>
        <p><strong>{displayLabel(record.entity_resolution.outcome)}</strong> · {displayLabel(record.entity_resolution.disclaimer)}</p>
        <p className="control-help">{record.entity_resolution.reason_codes.map(displayLabel).join(" · ")}</p>
        {record.entity_resolution.candidates.length > 0 && <div className="table-card table-scroll">
          <table className="table">
            <thead><tr><th>Candidate</th><th>POC match probability</th><th>Top contributions</th><th>Safe source</th></tr></thead>
            <tbody>{record.entity_resolution.candidates.map((candidate) => <tr key={candidate.candidate_id}>
              <td>{candidate.candidate_id}</td>
              <td>{candidate.probability}</td>
              <td>{candidate.top_contributing_features.map(displayLabel).join(" · ") || "Not assessed"}</td>
              <td>{candidate.source_reference ?? "Not supplied"}</td>
            </tr>)}</tbody>
          </table>
        </div>}
        <p className="control-help">Project-defined deterministic probability proxy; not calibrated production identity evidence.</p>
      </div>}
      <div>
        <h4>UBO assistance</h4>
        {record.ubo_advice.length === 0 ? <p className="text-muted">No deterministic UBO candidate is available.</p> : record.ubo_advice.map((item) => <div className="kv-row" key={item.party_id}><span className="kv-label">{item.party_id}</span><span className="kv-value">{displayLabel(item.label)} · {item.probability ?? "not assessed"}</span></div>)}
        <p className="control-help">Not legal UBO determination.</p>
      </div>
      {record.mock_risk && <div><h4>Mock advisory risk</h4><p><strong>{displayLabel(record.mock_risk.band)}</strong> · score {record.mock_risk.score ?? "not assessed"}</p><p className="control-help">Not compliance decision. Missing signals are not treated as low risk.</p><p className="control-help">Not assessed: {record.mock_risk.not_assessed_signals.join(", ") || "none"}</p></div>}
    </section>
  );
}
