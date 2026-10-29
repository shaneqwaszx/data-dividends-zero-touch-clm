import { formatOwnershipPercent, formatOwnershipCalculation } from "../ownershipDisplay";
import { useEffect, useMemo, useState, type CSSProperties } from "react";
import type { OwnershipAnalysisRecord, OwnershipRelationship } from "../types";

const ROW_LIMIT = 200;
const DEPTH_LIMIT = 32;
interface Row { key: string; partyId: string; path: OwnershipRelationship[]; cycle: boolean; unlinked?: boolean }

function occurrenceKey(rootPartyId: string | null, path: OwnershipRelationship[]) {
  return path.length
    ? JSON.stringify(["path", rootPartyId, path.map(edge => edge.relationship_id)])
    : JSON.stringify(["client", rootPartyId]);
}

// Arrange retained edges only. Percentages and classifications remain backend-owned.
function retainedRows(record: OwnershipAnalysisRecord) {
  const rows: Row[] = [];
  const reached = new Set<string>();
  let limited = false;
  const children = new Map<string, OwnershipRelationship[]>();
  for (const edge of record.relationships) children.set(edge.parent_party_id, [...(children.get(edge.parent_party_id) ?? []), edge]);
  function visit(partyId: string, path: OwnershipRelationship[], ancestors: Set<string>) {
    if (rows.length >= ROW_LIMIT) { limited = true; return; }
    const cycle = ancestors.has(partyId);
    rows.push({ partyId, path, cycle, key: occurrenceKey(record.root_party_id, path) });
    reached.add(partyId);
    if (cycle) return;
    if (path.length >= DEPTH_LIMIT) { limited ||= Boolean(children.get(partyId)?.length); return; }
    const next = new Set(ancestors).add(partyId);
    for (const edge of children.get(partyId) ?? []) visit(edge.child_party_id, [...path, edge], next);
  }
  if (record.root_party_id) visit(record.root_party_id, [], new Set());
  for (const party of record.parties) if (!reached.has(party.party_id)) {
    if (rows.length >= ROW_LIMIT) { limited = true; break; }
    rows.push({ key: JSON.stringify(["unlinked", party.party_id]), partyId: party.party_id, path: [], cycle: false, unlinked: true });
  }
  return { rows, limited };
}

// D-086: an intermediate entity's engine path products and aggregate, from the backend only.
function entityInterest(record: OwnershipAnalysisRecord, partyId: string | undefined) {
  return record.entity_effective_interests?.find(item => item.party_id === partyId) ?? null;
}

function retainedPath(record: OwnershipAnalysisRecord, row: Row) {
  if (row.cycle || row.unlinked || !row.path.length) return null;
  const paths = record.candidates.find(item => item.party.party_id === row.partyId)?.paths
    ?? entityInterest(record, row.partyId)?.paths;
  return paths?.find(path => path.edges.length === row.path.length
    && path.edges.every((edge, index) => edge.relationship_id === row.path[index].relationship_id)) ?? null;
}

function pathPercent(record: OwnershipAnalysisRecord, row: Row) { return retainedPath(record, row)?.effective_ownership_percent ?? null; }

// Presentation only: a company's own interest is never calculated here. When the backend
// supplies the engine's entity path products (D-086), rows show those instead; otherwise
// the client is the root and a single direct holding is the retained relationship itself.
function entityLabel(record: OwnershipAnalysisRecord, rows: Row[], row: Row): string | null {
  if (row.unlinked || row.cycle || pathPercent(record, row) !== null) return null;
  if (!row.path.length) return "Root entity — N/A";
  if (record.parties.find(party => party.party_id === row.partyId)?.party_type !== "LEGAL_ENTITY") return null;
  if (rows.filter(item => item.partyId === row.partyId && !item.unlinked).length > 1) return "Not calculated — held through multiple paths";
  return row.path.length === 1
    ? `${formatOwnershipPercent(row.path[0].ownership_percent)} — direct holding in client`
    : "Not calculated for indirect corporate holders";
}

// D-081: only the declared POC/synthetic basis and review notes are open. Any unresolved,
// conflicting or structural issue keeps the general warning.
const POC_VERIFICATION_ISSUES = new Set(["OWNERSHIP_DENOMINATOR_REQUIRED", "SYNTHETIC_OWNERSHIP_EVIDENCE", "UBO_REVIEW_REQUIRED"]);
// The graph node type LEGAL_ENTITY is not a legal form: show a non-company registry form
// (from the root or the issuer's own official profile) truthfully, never as "Company".
const NON_COMPANY_FORMS: Record<string, string> = { BUSINESS_PARTNERSHIP: "Business partnership", LLP: "LLP", LP: "LP" };
function entityTypeLabel(record: OwnershipAnalysisRecord, partyId: string): string {
  const party = record.parties.find(item => item.party_id === partyId);
  const form = partyId === record.root_party_id ? record.legal_form
    : record.discovery?.records.find(item => item.party_id === partyId
      || (party?.registration_number && item.registration_number === party.registration_number))?.official_legal_form;
  return (form && NON_COMPANY_FORMS[form]) ?? "Company";
}
// D-086: an owner-declared relationship percentage is marked technically and visibly;
// D-088: an issued-capital link names the official Mock business profile it derives from.
function sourceLabel(edge: OwnershipRelationship): string {
  const declared = edge.provenance.owner_declared_percentage === true;
  const issued = edge.provenance.provider === "LOCAL_POC_ISSUED_CAPITAL_BASIS";
  return `${edge.provenance.provider} · ${edge.provenance.environment}${declared ? " · owner-declared percentage" : ""}${issued ? " · from ACRA Mock business profile" : ""}`;
}

const LAYER_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"];
function layerWord(layers: number) { return `${LAYER_WORDS[layers] ?? layers}-layer`; }

function calculatedForVerification(record: OwnershipAnalysisRecord): boolean {
  return record.state === "REVIEW_REQUIRED"
    && record.relationships.some(edge => edge.provenance.provider === "LOCAL_POC_ASSUMED_EQUAL_UNITS")
    && record.issues.length > 0 && record.issues.every(issue => POC_VERIFICATION_ISSUES.has(issue.code));
}

export default function OwnershipStructure({ record, selectedPartyId, onSelectPerson, unlinkedHint = null }: {
  record: OwnershipAnalysisRecord; selectedPartyId: string | null; onSelectPerson: (partyId: string) => void;
  /** D-101: why an unlinked partner has no path yet (partnership awaiting RM confirmation). */
  unlinkedHint?: string | null;
}) {
  const { rows, limited } = useMemo(() => retainedRows(record), [record]);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  useEffect(() => { setCollapsed(new Set()); }, [record.analysis_id]);
  useEffect(() => { setSelectedKey(current => rows.some(row => row.key === current && row.partyId === selectedPartyId)
    ? current : rows.find(row => row.partyId === selectedPartyId)?.key ?? rows[0]?.key ?? null); }, [record.analysis_id, selectedPartyId]);
  useEffect(() => {
    const currentKeys = new Set(rows.map(row => row.key));
    setCollapsed(current => new Set([...current].filter(key => currentKeys.has(key))));
    setSelectedKey(current => currentKeys.has(current ?? "") ? current
      : rows.find(row => row.partyId === selectedPartyId)?.key ?? rows[0]?.key ?? null);
  }, [rows]);
  const selected = rows.find(row => row.key === selectedKey) ?? rows.find(row => row.partyId === selectedPartyId) ?? rows[0];
  const partyById = new Map(record.parties.map(party => [party.party_id, party]));
  const holder = selected ? partyById.get(selected.partyId) ?? record.candidates.find(item => item.party.party_id === selected.partyId)?.party : null;
  const candidate = record.candidates.find(item => item.party.party_id === selected?.partyId);
  const selectedEntity = entityInterest(record, selected?.partyId);
  function partyName(id: string) { return partyById.get(id)?.display_name ?? id; }
  const visibleRows = rows.filter(row => row.unlinked || !row.path.length
    || row.path.every((_, index) => !collapsed.has(occurrenceKey(record.root_party_id, row.path.slice(0, index)))));
  const layers = rows.reduce((deepest, row) => Math.max(deepest, row.path.length), 0);
  const uboCount = record.candidates.filter(item => item.classification === "PROVISIONAL_UBO_CANDIDATE" && item.threshold_result === "MET").length;
  return <section className="ownership-structure" aria-label="Hierarchical ownership structure">
    <header className="ownership-structure__header">
      <h4>Ownership structure</h4>
      <ul className="ownership-structure__stats" aria-label="Hierarchy summary">
        <li><strong>{layers}</strong> {layers === 1 ? "layer" : "layers"}</li>
        <li><strong>{record.parties.length}</strong> {record.parties.length === 1 ? "party" : "parties"}</li>
        <li className={uboCount ? "is-ubo" : undefined}><strong>{uboCount}</strong> provisional {uboCount === 1 ? "UBO" : "UBOs"}</li>
      </ul>
    </header>
    <details className="ownership-structure__about">
      <summary>What these values mean</summary>
      <p className="control-help">Follow each owned entity to its holders. Direct percentages belong to the immediate owned entity. Displayed percentages are rounded to at most two decimals. Threshold comparisons and classifications use full backend precision. Effective percentages are retained backend path results; intermediate interests are not inferred.</p>
      <dl className="ownership-structure__legend"><div><dt>Direct interest</dt><dd>Holding in the immediate owned entity.</dd></div><div><dt>Indirect interest</dt><dd>Holding through intermediate entities.</dd></div><div><dt>Effective interest</dt><dd>Backend-calculated path value; candidate aggregate combines retained paths.</dd></div><div><dt>Ownership evidence source</dt><dd>Original provider and environment on each relationship.</dd></div><div><dt>Provisional UBO candidate</dt><dd>Natural person classified as qualifying by the backend.</dd></div><div><dt>Review/incomplete status</dt><dd>Unresolved evidence is not a final determination.</dd></div></dl>
    </details>
    {record.state !== "ANALYZED" && (record.poc_basis_accepted
      // D-085: shown only from the backend's current acceptance authority.
      ? <div className="ds-banner" role="note"><strong>Ownership calculated — POC basis accepted</strong>
        <p>Ownership percentages use retained ACRA Marketplace Mock shareholder quantities and the declared POC assumptions of this whitelisted demonstration scenario, accepted for readiness by the opt-in POC acceptance policy. Official share denominators and share-class rights remain unverified.</p>
        <p>This is not verified ownership or a legal UBO determination. Target confirmation is still required before any GoldTier send.</p>
        {record.poc_acceptance?.accepted_assumptions?.includes("UNCLASSIFIED_LEGAL_FORM")
          && <p>The registry legal form has no supported formal UBO method; the declared POC arithmetic is shown without a formal classification.</p>}
        {record.poc_acceptance && record.poc_acceptance.descriptive_current_role_count + record.poc_acceptance.descriptive_ceased_role_count > 0
          && <p>The official Marketplace Mock officer ownership role records ({record.poc_acceptance.descriptive_current_role_count} current, {record.poc_acceptance.descriptive_ceased_role_count} ceased) are retained unchanged as descriptive context only. They do not corroborate the synthetic shareholder relationships.</p>}
        {record.poc_acceptance && (record.poc_acceptance.descriptive_intermediate_current_role_count ?? 0) + (record.poc_acceptance.descriptive_intermediate_ceased_role_count ?? 0) > 0
          && <p>An intermediate entity's official Marketplace Mock officer ownership role records ({record.poc_acceptance.descriptive_intermediate_current_role_count ?? 0} current, {record.poc_acceptance.descriptive_intermediate_ceased_role_count ?? 0} ceased) are retained unchanged as descriptive context only. They are not shareholdings and do not corroborate the synthetic relationships.</p>}
        {record.poc_acceptance?.accepted_assumptions?.includes("ISSUED_CAPITAL_DENOMINATOR")
          && <p>An issuer's holder percentages use its official ACRA Marketplace Mock business profile share quantities over its issued share capital. The profile returned no holder status; treating the holding as current is a declared POC assumption.</p>}
        {record.relationships.some(edge => edge.provenance.owner_declared_percentage)
          && <p>Ownership calculations are accepted for this demonstration using ACRA Marketplace Mock observations and explicitly declared synthetic relationships, including an owner-declared percentage. This is not a verified legal UBO determination.</p>}</div>
      : calculatedForVerification(record)
      ? <div className="ds-banner ds-banner-warn" role="note"><strong>Ownership calculated — verification required</strong>
        <p>Ownership percentages use retained ACRA Marketplace Mock shareholder quantities and declared POC assumptions. Official share denominators and share-class rights remain unverified.</p>
        <p>Legal UBO determination and ownership readiness remain subject to review.</p></div>
      : record.simulation_calculated
      // Presentation only, from the backend: arithmetic completed on declared synthetic
      // links. Readiness, issues and classifications are unchanged.
      ? <div className="ds-banner" role="note"><strong>Multi-layer ownership simulation calculated</strong>
        <p>The {layerWord(layers)} ownership structure and effective interests have been calculated using declared synthetic relationships and the existing Decimal engine. This demonstrates recursive ownership tracing and aggregation, not verified ACRA ownership.</p>
        <p>The formal UBO classification and ownership readiness remain review-required: these relationships and any locally named entities are demonstration inputs, not ACRA evidence.</p>
        {record.issues.some(issue => issue.code === "OWNERSHIP_METHOD_UNSUPPORTED")
          && <p>The root's registry legal form has no supported formal UBO method.</p>}</div>
      : <p className="ds-banner ds-banner-warn">Partial or disputed ownership evidence — review required.</p>)}
    <div className="ownership-structure__layout">
      <div className="ownership-structure__rows" tabIndex={0} role="table" aria-label="Ownership hierarchy">
        <div className="ownership-structure__row ownership-structure__head" role="row"><span role="columnheader">Holder</span><span role="columnheader">Type</span><span role="columnheader">Country</span><span role="columnheader">Direct/Indirect %</span><span role="columnheader">Effective on path %</span><span role="columnheader">Evidence source</span></div>
        {visibleRows.map(row => {
          const party = partyById.get(row.partyId) ?? record.candidates.find(item => item.party.party_id === row.partyId)?.party;
          const result = record.candidates.find(item => item.party.party_id === row.partyId);
          const qualifies = result?.classification === "PROVISIONAL_UBO_CANDIDATE" && result.threshold_result === "MET";
          const person = party?.party_type === "NATURAL_PERSON";
          const isClient = !row.unlinked && !row.path.length;
          const ownedName = row.path.length ? partyName(row.path[row.path.length - 1].parent_party_id) : null;
          const depth = Math.min(row.path.length, 8);
          return <div key={row.key} role="row" style={{ "--depth": depth } as CSSProperties}
            className={`ownership-structure__row${qualifies ? " is-ubo" : ""}${selected?.key === row.key ? " is-selected" : ""}${isClient ? " is-client" : ""}`}>
            <div role="cell" className="ownership-structure__holder">
              {!row.cycle && !row.unlinked && record.relationships.some(edge => edge.parent_party_id === row.partyId)
                ? <button type="button" className="ownership-structure__toggle" aria-label={`${collapsed.has(row.key) ? "Expand" : "Collapse"} holders of ${party?.display_name ?? row.partyId}`} aria-expanded={!collapsed.has(row.key)} onClick={() => { setCollapsed(current => { const next = new Set(current); if (next.has(row.key)) next.delete(row.key); else next.add(row.key); return next; }); setSelectedKey(row.key); }}>{collapsed.has(row.key) ? "+" : "−"}</button>
                : <span className="ownership-structure__toggle-spacer" aria-hidden="true" />}
              <span className={`ownership-node__icon ${person ? "is-person" : "is-company"}`} aria-hidden="true">{person ? "P" : "C"}</span>
              <span className="ownership-node__body">
                <button type="button" aria-pressed={selected?.key === row.key} onClick={() => { setSelectedKey(row.key); if (result) onSelectPerson(row.partyId); }}>{party?.display_name ?? row.partyId}</button>
                <span className="ownership-node__context">
                  {isClient && <span className="tag tag-neutral">Client</span>}
                  {ownedName && <small>Holds {formatOwnershipPercent(row.path[row.path.length - 1].ownership_percent)} of {ownedName}</small>}
                  {qualifies && <span className="tag tag-warn">Provisional UBO</span>}
                  {row.cycle && <span className="tag tag-neutral">Cycle — traversal stopped</span>}
                  {row.unlinked && <span className="tag tag-neutral">No retained root path</span>}
                  {row.unlinked && unlinkedHint && <small>{unlinkedHint}</small>}
                  {row.path.length > 8 && <small>Layer {row.path.length} from root</small>}
                </span>
              </span>
            </div>
            <span role="cell" data-label="Type">{person ? "Individual" : party?.party_type === "LEGAL_ENTITY" ? entityTypeLabel(record, row.partyId) : "Unknown"}</span>
            <span role="cell" data-label="Country">{party?.country ?? "Not supplied"}</span>
            <span role="cell" data-label="Direct/Indirect">{row.path.length ? formatOwnershipPercent(row.path[row.path.length - 1].ownership_percent) : "—"}</span>
            <span role="cell" data-label="Effective">{pathPercent(record, row) !== null ? formatOwnershipPercent(pathPercent(record, row)) : entityLabel(record, rows, row) ?? "Not retained"}</span>
            <span role="cell" data-label="Source">{row.path.length ? sourceLabel(row.path[row.path.length - 1]) : `${record.provider_name ?? "Not supplied"} · ${record.provider_environment ?? "Not supplied"}`}</span>
          </div>;
        })}
        {!rows.length && <p>No retained hierarchy is available.</p>}
      </div>
      <aside className="ownership-structure__detail" aria-label="Selected holder">
        <p className="card-kicker">Selected holder</p><h5>{holder?.display_name ?? selected?.partyId ?? "No holder selected"}</h5>
        {selected && <>
          <p>{holder?.party_type.replaceAll("_", " ") ?? "Unknown type"} · {holder?.country ?? "Country not supplied"}</p>
          <dl><div><dt>Direct holding in immediate entity</dt><dd>{selected.path.length ? formatOwnershipPercent(selected.path[selected.path.length - 1].ownership_percent) : selected.unlinked ? "Not retained" : "Root entity — N/A"}</dd></div>
            <div><dt>Effective on selected path</dt><dd>{pathPercent(record, selected) !== null ? formatOwnershipPercent(pathPercent(record, selected)) : entityLabel(record, rows, selected) ?? "Not calculated by retained analysis"}</dd></div>
            {!candidate && selectedEntity && <div><dt>Aggregate effective in root (all retained paths)</dt><dd>{formatOwnershipPercent(selectedEntity.effective_ownership_percent)} (calculated interest; not a UBO classification)</dd></div>}
            {candidate && <><div><dt>Aggregate effective in root (all retained paths)</dt><dd>{formatOwnershipPercent(candidate.aggregated_ownership_percent)}</dd></div><div><dt>Threshold comparison</dt><dd>{candidate.threshold_comparator} {formatOwnershipPercent(candidate.threshold_percent)} → {candidate.threshold_result}</dd></div>{candidate.synthetic_basis_threshold_result != null && <div><dt>Assumed-basis comparison</dt><dd>{candidate.threshold_comparator} {formatOwnershipPercent(candidate.threshold_percent)} → {candidate.synthetic_basis_threshold_result} (not a classification)</dd></div>}<div><dt>Classification</dt><dd>{candidate.classification}</dd></div></>}
          </dl>
          <h6>Path from client to holder</h6>
          {selected.unlinked ? <p>No retained root path is available.</p> : <ol className="ownership-structure__path"><li>{partyName(record.root_party_id ?? selected.partyId)} · client</li>{selected.path.map(edge => <li key={edge.relationship_id}>{partyName(edge.child_party_id)} holds {formatOwnershipPercent(edge.ownership_percent)} of {partyName(edge.parent_party_id)}</li>)}</ol>}
          {selected.path.length > 0 && <p className="control-help">Source: {sourceLabel(selected.path[selected.path.length - 1])}</p>}
          {retainedPath(record, selected) && <p>Calculation: {formatOwnershipCalculation(retainedPath(record, selected)!.calculation)}</p>}
          {!candidate && selectedEntity && selectedEntity.paths.length > 1 && <p>{selectedEntity.paths.length} retained paths reach this entity. The highlighted occurrence shows one path; the aggregate covers all retained paths.</p>}
          {candidate && candidate.paths.length > 1 && <p>{candidate.paths.length} retained paths reach this person. The highlighted occurrence shows one path; the aggregate covers all retained paths. Inspect other paths in technical calculations.</p>}
          {selected.cycle && <p>Cycle detected; this path is non-definitive.</p>}
        </>}
      </aside>
    </div>
    {limited && <p role="note">Hierarchy display limited to {ROW_LIMIT} rows / {DEPTH_LIMIT} layers. Inspect the retained relationships in technical calculations for further evidence.</p>}
    <p className="control-help">This displays retained evidence only. It does not establish complete tracing, screening, control without ownership, or legal beneficial ownership.</p>
  </section>;
}
