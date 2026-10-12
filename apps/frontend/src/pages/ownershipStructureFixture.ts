import type { OwnershipAnalysisRecord, OwnershipParty, OwnershipRelationship } from "../types";

export function ownershipStructureFixture(): OwnershipAnalysisRecord {
  const parties: OwnershipParty[] = [
    { party_id: "root", display_name: "Synthetic client", party_type: "LEGAL_ENTITY", country: "SG", registration_number: "202400001A" },
    { party_id: "holding", display_name: "Synthetic holding", party_type: "LEGAL_ENTITY", country: "GB", registration_number: null },
    { party_id: "person", display_name: "Synthetic qualifying person", party_type: "NATURAL_PERSON", country: "SG", registration_number: null },
    { party_id: "zero", display_name: "Synthetic below-threshold person", party_type: "NATURAL_PERSON", country: null, registration_number: null },
  ];
  const edge = (id: string, parent: string, child: string, percent: string): OwnershipRelationship => ({ relationship_id: id, parent_party_id: parent, child_party_id: child, ownership_percent: percent, relationship_type: "OWNERSHIP", basis: "SHARE_OWNERSHIP", provenance: { provider: "LOCAL_SYNTHETIC_SUPPLEMENT", environment: "LOCAL", sourced_at: "2026-10-12T00:00:00Z" } });
  const relationships = [edge("first", "root", "holding", "50"), edge("second", "holding", "person", "50"), edge("direct", "root", "person", "0.000000000000000001"), edge("below", "root", "zero", "0")];
  return {
    version: 1, case_id: "case", analysis_id: "analysis", correlation_id: "correlation", root_party_id: "root", provider_name: "ACRA_REGISTRY_ACQUISITION", provider_environment: "MOCK", source_classification: "OFFICIAL_MOCK_PLUS_LOCAL_SUPPLEMENT", state: "ANALYZED", parties, relationships,
    candidates: [{ party: parties[2], direct_ownership_percent: "0.000000000000000001", indirect_ownership_percent: "25", aggregated_ownership_percent: "25.000000000000000001", threshold_percent: "25", threshold_comparator: "GREATER_THAN_OR_EQUAL_TO", threshold_result: "MET", classification: "PROVISIONAL_UBO_CANDIDATE", paths: [
      { path_id: "indirect", is_direct: false, calculation: "50 × 50 / 100 = 25", effective_ownership_percent: "25", edges: relationships.slice(0, 2).map(e => ({ ...e, parent_display_name: parties.find(p => p.party_id === e.parent_party_id)!.display_name, child_display_name: parties.find(p => p.party_id === e.child_party_id)!.display_name })) },
      { path_id: "direct", is_direct: true, calculation: "0.000000000000000001", effective_ownership_percent: "0.000000000000000001", edges: [{ ...relationships[2], parent_display_name: parties[0].display_name, child_display_name: parties[2].display_name }] },
    ] }, { party: parties[3], direct_ownership_percent: "0", indirect_ownership_percent: "0", aggregated_ownership_percent: "0", threshold_percent: "25", threshold_comparator: "GREATER_THAN_OR_EQUAL_TO", threshold_result: "NOT_MET", classification: "BELOW_PROVISIONAL_THRESHOLD", paths: [] }],
    issues: [], threshold_percent: "25", threshold_comparator: "GREATER_THAN_OR_EQUAL_TO", events: [], error: null, created_at: "now", loaded_at: "now", analyzed_at: "now", updated_at: "now",
  };
}
