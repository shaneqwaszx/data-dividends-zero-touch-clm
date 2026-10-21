import { formatOwnershipPercent, formatOwnershipCalculation } from "../ownershipDisplay";
import type { OwnershipAnalysisRecord } from "../types";

export default function UboSummary({ record }: { record: OwnershipAnalysisRecord | null }) {
  const qualified = record?.candidates.filter(candidate => candidate.party.party_type === "NATURAL_PERSON"
    && candidate.classification === "PROVISIONAL_UBO_CANDIDATE" && candidate.threshold_result === "MET") ?? [];
  const title = "Identified UBO candidates — effective ownership ≥ current policy threshold";
  return <section className="ubo-summary" aria-label={title}>
    <header className="ubo-summary__header">
      <h5>Identified UBO candidates</h5>
      {record && <span className="ubo-summary__threshold">Threshold ≥ {formatOwnershipPercent(record.threshold_percent)}</span>}
    </header>
    <p className="control-help">Provisional UBO candidates from the retained POC ownership analysis, not a legal UBO determination. Percentages are rounded for display; threshold results use full backend precision.</p>
    {qualified.length ? <ul className="ubo-summary__list">{qualified.map(candidate => <li key={candidate.party.party_id} className="ubo-card">
      <strong className="ubo-card__name">{candidate.party.display_name}</strong>
      <span className="ubo-card__effective"><b>{formatOwnershipPercent(candidate.aggregated_ownership_percent)}</b> effective</span>
      <dl className="ubo-card__figures">
        <div><dt>Direct</dt><dd>{formatOwnershipPercent(candidate.direct_ownership_percent)}</dd></div>
        <div><dt>Indirect</dt><dd>{formatOwnershipPercent(candidate.indirect_ownership_percent)}</dd></div>
        <div><dt>Threshold</dt><dd><span className="ubo-card__met">{candidate.threshold_comparator} {formatOwnershipPercent(candidate.threshold_percent)} → {candidate.threshold_result}</span></dd></div>
      </dl>
      <details className="ubo-card__details"><summary>How this was determined · {candidate.paths.length} ownership path{candidate.paths.length === 1 ? "" : "s"}</summary>
        <p>Why: this natural person's backend-calculated aggregate meets the case threshold; classification {candidate.classification}.</p>
        <p>Analysis provider: {record?.provider_name ?? "Not supplied"} · {record?.provider_environment ?? "Not supplied"} · {record?.source_classification ?? "SINGLE_SOURCE"}. Review {record?.state === "ANALYZED" ? "not outstanding in this analysis" : "outstanding for current evidence"}.</p>
        <p>Ownership evidence sources: {[...new Set(record?.relationships.filter(edge => candidate.paths.some(path => path.edges.some(item => item.relationship_id === edge.relationship_id))).map(edge => `${edge.provenance.provider} · ${edge.provenance.environment}`))].join("; ") || "Not retained"}</p>
        <div className="ubo-card__paths">
          {candidate.paths.slice(0, 20).map(path => <p key={path.path_id}>{path.edges.map(edge => `${edge.parent_display_name} → ${edge.child_display_name} (${formatOwnershipPercent(edge.ownership_percent)})`).join("; ")} · {formatOwnershipCalculation(path.calculation)} · {formatOwnershipPercent(path.effective_ownership_percent)} effective on path</p>)}
        </div>
        {candidate.paths.length > 20 && <p>Showing 20 retained paths. Inspect all paths in technical calculations.</p>}
      </details>
    </li>)}</ul> : <p className="ubo-summary__empty">{record ? "No qualifying natural person is identified by the current retained classification." : "Ownership analysis is not available."}</p>}
    {record && record.state !== "ANALYZED" && <p className="ubo-summary__warning">UBO determination requires review. Ownership evidence is incomplete or disputed; the current result is non-definitive.</p>}
    {record?.source_classification === "OFFICIAL_MOCK_PLUS_LOCAL_SUPPLEMENT" && <p className="control-help">Official Marketplace Mock facts and local synthetic ownership evidence remain distinct. LOCAL_SYNTHETIC_SUPPLEMENT percentages are not official ACRA ownership values.</p>}
  </section>;
}
