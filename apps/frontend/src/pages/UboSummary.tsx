import type { OwnershipAnalysisRecord } from "../types";

export default function UboSummary({ record }: { record: OwnershipAnalysisRecord | null }) {
  const qualified = record?.candidates.filter(candidate => candidate.party.party_type === "NATURAL_PERSON"
    && candidate.classification === "PROVISIONAL_UBO_CANDIDATE" && candidate.threshold_result === "MET") ?? [];
  const title = "Identified UBO candidates — effective ownership ≥ current policy threshold";
  return <section className="ubo-summary" aria-label={title}>
    <h5>{title}</h5>
    {record && <p>Current policy threshold: ≥ {record.threshold_percent}%</p>}
    <p className="control-help">Identified by the retained POC ownership analysis. These are provisional UBO candidates, not a legal UBO determination.</p>
    {qualified.length ? <ul>{qualified.map(candidate => <li key={candidate.party.party_id}>
      <strong>{candidate.party.display_name}</strong> <span>{candidate.aggregated_ownership_percent}% effective</span>
      <p>Direct: {candidate.direct_ownership_percent}% · indirect: {candidate.indirect_ownership_percent}%</p>
      <p>Threshold comparison: {candidate.threshold_comparator} {candidate.threshold_percent}% → {candidate.threshold_result}.</p>
      <p>Why: this natural person's backend-calculated aggregate meets the case threshold; classification {candidate.classification}.</p>
      <p>Analysis provider: {record?.provider_name ?? "Not supplied"} · {record?.provider_environment ?? "Not supplied"} · {record?.source_classification ?? "SINGLE_SOURCE"}. Review {record?.state === "ANALYZED" ? "not outstanding in this analysis" : "outstanding for current evidence"}.</p>
      <p>Ownership evidence sources: {[...new Set(record?.relationships.filter(edge => candidate.paths.some(path => path.edges.some(item => item.relationship_id === edge.relationship_id))).map(edge => `${edge.provenance.provider} · ${edge.provenance.environment}`))].join("; ") || "Not retained"}</p>
      <details><summary>Supporting ownership paths ({candidate.paths.length})</summary>
        {candidate.paths.slice(0, 20).map(path => <p key={path.path_id}>{path.edges.map(edge => `${edge.parent_display_name} → ${edge.child_display_name} (${edge.ownership_percent}%)`).join("; ")} · {path.calculation} · {path.effective_ownership_percent}% effective on path</p>)}
        {candidate.paths.length > 20 && <p>Showing 20 retained paths. Inspect all paths in technical calculations.</p>}
      </details>
    </li>)}</ul> : <p>{record ? "No qualifying natural person is identified by the current retained classification." : "Ownership analysis is not available."}</p>}
    {record && record.state !== "ANALYZED" && <p>UBO determination requires review. Ownership evidence is incomplete or disputed; the current result is non-definitive.</p>}
    {record?.source_classification === "OFFICIAL_MOCK_PLUS_LOCAL_SUPPLEMENT" && <p>Official Marketplace Mock facts and local synthetic ownership evidence remain distinct. LOCAL_SYNTHETIC_SUPPLEMENT percentages are not official ACRA ownership values.</p>}
  </section>;
}
