// TEMPORARY dev-only ownership preview with made-up data. Rendered only on the local
// dev server when a case URL has ?ownershipPreview=1. Delete after the design review.
import OwnershipPathExplorer from "../pages/OwnershipPathExplorer";
import type { OwnershipAnalysisRecord, OwnershipParty, OwnershipRelationship } from "../types";

const parties: OwnershipParty[] = [
  { party_id: "client", display_name: "Merlion Circular Labs Pte. Ltd.", party_type: "LEGAL_ENTITY", country: "SG", registration_number: "202400001A" },
  { party_id: "harbour", display_name: "Harbour Holdings Pte. Ltd.", party_type: "LEGAL_ENTITY", country: "SG", registration_number: "201900123K" },
  { party_id: "family", display_name: "Tan Family Investments Ltd.", party_type: "LEGAL_ENTITY", country: "HK", registration_number: null },
  { party_id: "avery", display_name: "Avery Tan", party_type: "NATURAL_PERSON", country: "SG", registration_number: null },
  { party_id: "priya", display_name: "Priya Nair", party_type: "NATURAL_PERSON", country: "MY", registration_number: null },
];
const name = (id: string) => parties.find(party => party.party_id === id)!.display_name;
const edge = (id: string, parent: string, child: string, percent: string): OwnershipRelationship => ({
  relationship_id: id, parent_party_id: parent, child_party_id: child, ownership_percent: percent,
  relationship_type: "OWNERSHIP", basis: "SHARE_OWNERSHIP",
  provenance: { provider: "PREVIEW_MOCK", environment: "LOCAL", sourced_at: "2026-10-19T00:00:00Z" },
});
const relationships = [
  edge("r1", "client", "harbour", "60"), edge("r2", "client", "avery", "40"),
  edge("r3", "harbour", "family", "70"), edge("r4", "harbour", "priya", "30"),
  edge("r5", "family", "avery", "100"),
];
const pathEdges = (...ids: string[]) => ids.map(id => {
  const item = relationships.find(rel => rel.relationship_id === id)!;
  return { ...item, parent_display_name: name(item.parent_party_id), child_display_name: name(item.child_party_id) };
});
const record = {
  version: 1, case_id: "preview", analysis_id: "preview", correlation_id: "preview", root_party_id: "client",
  provider_name: "PREVIEW_MOCK", provider_environment: "LOCAL", source_classification: null, state: "ANALYZED",
  parties, relationships, issues: [], events: [], error: null,
  threshold_percent: "25", threshold_comparator: "GREATER_THAN_OR_EQUAL_TO",
  created_at: "now", loaded_at: "now", analyzed_at: "now", updated_at: "now",
  candidates: [
    { party: parties[3], direct_ownership_percent: "40", indirect_ownership_percent: "42", aggregated_ownership_percent: "82",
      threshold_percent: "25", threshold_comparator: "GREATER_THAN_OR_EQUAL_TO", threshold_result: "MET", classification: "PROVISIONAL_UBO_CANDIDATE",
      paths: [
        { path_id: "avery-direct", is_direct: true, calculation: "40", effective_ownership_percent: "40", edges: pathEdges("r2") },
        { path_id: "avery-indirect", is_direct: false, calculation: "60 × 70 × 100 / 10000 = 42", effective_ownership_percent: "42", edges: pathEdges("r1", "r3", "r5") },
      ] },
    { party: parties[4], direct_ownership_percent: "0", indirect_ownership_percent: "18", aggregated_ownership_percent: "18",
      threshold_percent: "25", threshold_comparator: "GREATER_THAN_OR_EQUAL_TO", threshold_result: "NOT_MET", classification: "BELOW_PROVISIONAL_THRESHOLD",
      paths: [{ path_id: "priya-indirect", is_direct: false, calculation: "60 × 30 / 100 = 18", effective_ownership_percent: "18", edges: pathEdges("r1", "r4") }] },
  ],
} as unknown as OwnershipAnalysisRecord;


// Opening any case once with ?ownershipPreview=1 keeps the preview on for this browser tab session.
export function ownershipPreviewEnabled(): boolean {
  if (!import.meta.env.DEV) return false;
  try {
    if (new URLSearchParams(window.location.search).has("ownershipPreview")) sessionStorage.setItem("dev-ownership-preview", "1");
    return sessionStorage.getItem("dev-ownership-preview") === "1";
  } catch {
    return new URLSearchParams(window.location.search).has("ownershipPreview");
  }
}

export default function OwnershipPreviewMock() {
  return <>
    <p className="ds-banner ds-banner-warn" role="note"><strong>Preview only — made-up mock data.</strong> Not this case's ownership evidence; shown because ?ownershipPreview was opened in this tab on the local dev server.</p>
    <OwnershipPathExplorer record={record} presentation="main" />
  </>;
}
