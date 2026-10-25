import type { OwnershipAnalysisRecord, OwnershipCandidate, OwnershipParty, OwnershipRelationship } from "../types";

type Basis = OwnershipCandidate["synthetic_basis_threshold_result"];

// Hybrid-lane analyses shaped like the backend's responses: every candidate stays formally
// REVIEW_REQUIRED/INDETERMINATE and carries the separate assumed-basis comparison.
function hybridRecord(
  parties: OwnershipParty[],
  relationships: OwnershipRelationship[],
  people: Array<[partyId: string, aggregated: string, edgeIds: string[], basis: Basis]>,
): OwnershipAnalysisRecord {
  const name = (id: string) => parties.find(party => party.party_id === id)!.display_name;
  const candidates: OwnershipCandidate[] = people.map(([partyId, aggregated, edgeIds, basis]) => {
    const edges = edgeIds.map(id => relationships.find(edge => edge.relationship_id === id)!);
    return {
      party: parties.find(party => party.party_id === partyId)!,
      direct_ownership_percent: edges.length === 1 ? aggregated : "0",
      indirect_ownership_percent: edges.length === 1 ? "0" : aggregated,
      aggregated_ownership_percent: aggregated,
      threshold_percent: "25.000000",
      threshold_comparator: "GREATER_THAN_OR_EQUAL_TO",
      threshold_result: "INDETERMINATE",
      classification: "REVIEW_REQUIRED",
      synthetic_basis_threshold_result: basis,
      paths: [{
        path_id: `path-${partyId}`, is_direct: edges.length === 1, effective_ownership_percent: aggregated,
        calculation: `${edges.map(edge => `${edge.ownership_percent}%`).join(" x ")} = ${aggregated}%`,
        edges: edges.map(edge => ({ ...edge, parent_display_name: name(edge.parent_party_id), child_display_name: name(edge.child_party_id) })),
      }],
    };
  });
  return {
    version: 5, case_id: "case-hybrid", analysis_id: "analysis-hybrid", correlation_id: "correlation-hybrid",
    root_party_id: parties[0].party_id, provider_name: "ACRA_REGISTRY_ACQUISITION", provider_environment: "MOCK",
    source_classification: "OFFICIAL_MOCK_PLUS_LOCAL_DIRECT_OVERLAY" as unknown as OwnershipAnalysisRecord["source_classification"],
    state: "REVIEW_REQUIRED", parties, relationships, candidates,
    issues: [
      { code: "OWNERSHIP_DENOMINATOR_REQUIRED", message: "Percentages shown assume equal POC units, not an ACRA denominator.", affected_party_ids: [] },
      { code: "SYNTHETIC_OWNERSHIP_EVIDENCE", message: "Ownership links are local declarations or POC estimates.", affected_party_ids: [] },
    ],
    threshold_percent: "25.000000", threshold_comparator: "GREATER_THAN_OR_EQUAL_TO", events: [], error: null,
    created_at: "now", loaded_at: "now", analyzed_at: "now", updated_at: "now",
  } as OwnershipAnalysisRecord;
}

const link = (id: string, parent: string, child: string, percent: string, provider: string): OwnershipRelationship => ({
  relationship_id: id, parent_party_id: parent, child_party_id: child, ownership_percent: percent,
  relationship_type: "OWNERSHIP", basis: "SHARE_OWNERSHIP",
  provenance: { provider, environment: "LOCAL", sourced_at: "2026-10-24T00:00:00Z" },
});
const company = (id: string, name: string): OwnershipParty => ({ party_id: id, display_name: name, party_type: "LEGAL_ENTITY", country: "SG", registration_number: null });
const person = (id: string, name: string): OwnershipParty => ({ party_id: id, display_name: name, party_type: "NATURAL_PERSON", country: null, registration_number: null });

/** Garden -> SIM LIM under the D-081 POC equal-unit assumption (values as the backend returns them). */
export function gardenAssumedBasisFixture(): OwnershipAnalysisRecord {
  const parties = [
    company("ENTITY_11111999A", "GARDEN BUSINESS"), company("SIMLIM", "SIM LIM PTE. LTD."),
    person("ABCD", "ABCD123"), person("TAN", "TAN WEI LING"), person("EFGH", "EFGH2345"), person("LIM", "LIM CHOON HUAT"),
  ];
  const overlay = "LOCAL_SYNTHETIC_RELATIONSHIP"; const poc = "LOCAL_POC_ASSUMED_EQUAL_UNITS";
  const relationships = [
    link("g-sim", "ENTITY_11111999A", "SIMLIM", "62.500000", overlay), link("g-lim", "ENTITY_11111999A", "LIM", "37.500000", overlay),
    link("s-abcd", "SIMLIM", "ABCD", "81.818182", poc), link("s-tan", "SIMLIM", "TAN", "9.090909", poc), link("s-efgh", "SIMLIM", "EFGH", "9.090909", poc),
  ];
  return hybridRecord(parties, relationships, [
    ["ABCD", "51.13636375000000", ["g-sim", "s-abcd"], "MET"],
    ["TAN", "5.68181812500000", ["g-sim", "s-tan"], "NOT_MET"],
    ["EFGH", "5.68181812500000", ["g-sim", "s-efgh"], "NOT_MET"],
    ["LIM", "37.500000", ["g-lim"], "MET"],
  ]);
}

/** A reduced five-layer overlay (D-077): only LOCAL_SYNTHETIC_RELATIONSHIP links. */
export function fiveLayerAssumedBasisFixture(): OwnershipAnalysisRecord {
  const parties = [
    company("ROOT", "OPQ PTE. LTD."), company("L2", "FIVE LAYER L2 HOLDINGS (SYNTHETIC)"),
    person("ALEX", "ALEX TAN (SYNTHETIC PERSON)"), person("BEATRICE", "BEATRICE LIM (SYNTHETIC PERSON)"), person("DIANA", "DIANA KOH (SYNTHETIC PERSON)"),
  ];
  const overlay = "LOCAL_SYNTHETIC_RELATIONSHIP";
  const relationships = [
    link("r-l2", "ROOT", "L2", "80", overlay), link("r-alex", "ROOT", "ALEX", "20", overlay),
    link("l2-beatrice", "L2", "BEATRICE", "46.875", overlay), link("l2-diana", "L2", "DIANA", "31.25", overlay),
  ];
  return hybridRecord(parties, relationships, [
    ["ALEX", "20", ["r-alex"], "NOT_MET"],
    ["BEATRICE", "37.5", ["r-l2", "l2-beatrice"], "MET"],
    ["DIANA", "25", ["r-l2", "l2-diana"], "MET"],
  ]);
}

/** D-086: OPQ -> GARDEN BUSINESS (owner-declared 100%) -> SIM LIM, values as the backend returns them. */
export function opqGardenSimLimFixture(): OwnershipAnalysisRecord {
  const parties = [
    company("ENTITY_201511222D", "OPQ PTE. LTD."), { ...company("11111999A", "GARDEN BUSINESS"), registration_number: "11111999A" },
    company("SIMLIM", "SIM LIM PTE. LTD."),
    person("ABCD", "ABCD123"), person("TAN", "TAN WEI LING"), person("EFGH", "EFGH2345"), person("LIM", "LIM CHOON HUAT"),
  ];
  const overlay = "LOCAL_SYNTHETIC_RELATIONSHIP"; const poc = "LOCAL_POC_ASSUMED_EQUAL_UNITS";
  const declared = { ...link("o-g", "ENTITY_201511222D", "11111999A", "100.000000", overlay) };
  declared.provenance = { ...declared.provenance, owner_declared_percentage: true };
  const relationships = [
    declared,
    link("g-sim", "11111999A", "SIMLIM", "62.500000", overlay), link("g-lim", "11111999A", "LIM", "37.500000", overlay),
    link("s-abcd", "SIMLIM", "ABCD", "81.818182", poc), link("s-tan", "SIMLIM", "TAN", "9.090909", poc), link("s-efgh", "SIMLIM", "EFGH", "9.090909", poc),
  ];
  const record = hybridRecord(parties, relationships, [
    ["ABCD", "51.13636375000000", ["o-g", "g-sim", "s-abcd"], "MET"],
    ["TAN", "5.68181812500000", ["o-g", "g-sim", "s-tan"], "NOT_MET"],
    ["EFGH", "5.68181812500000", ["o-g", "g-sim", "s-efgh"], "NOT_MET"],
    ["LIM", "37.500000", ["o-g", "g-lim"], "MET"],
  ]);
  record.legal_form = "OTHER";
  record.discovery = {
    method: "REGISTRY_CORPORATE_DISCOVERY_V1", trace_threshold_percent: "10.000000", ubo_threshold_percent: "25.000000",
    max_corporate_depth: 5, call_budget_enabled: false, call_budget_max: 10, graph_complete: false,
    classification_certainty: "UNCERTAIN", registry_lookups: 2, provider_backed_lookups: 2, cache_hits: 0,
    records: [
      { party_id: "11111999A", display_name: "GARDEN BUSINESS", registration_number: "11111999A", depth: 1, outcome: "LOCAL_SYNTHETIC_OVERLAY" as never, identity_basis: "OFFICIAL_MOCK_ENTITY_PROFILE", official_legal_form: "BUSINESS_PARTNERSHIP" },
      { party_id: "SIMLIM", display_name: "SIM LIM PTE. LTD.", registration_number: "111111111M", depth: 2, outcome: "PROVIDER_PARTIAL", reason_code: "OFFICIAL_SHAREHOLDERS_POC_EQUAL_UNITS" },
    ],
    unresolved_person_party_ids: [], overlay_scenario_id: "OPQ_GARDEN_SIM_LIM_V1", topology_complete: true,
  };
  return record;
}
