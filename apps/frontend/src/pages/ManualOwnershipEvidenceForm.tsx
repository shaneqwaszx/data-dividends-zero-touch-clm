import { singaporeCalendarDate } from "../shared";
import { formatOwnershipPercent } from "../ownershipDisplay";
import { UPLOAD_ACCEPT, UPLOAD_HELP_TEXT } from "../uploadLimits";
import { useMemo, useState, type FormEvent } from "react";

import type { DocumentOwnershipObservation, DocumentProcessingRecord, OwnershipAnalysisRecord, OwnershipDocumentBinding, OwnershipParty } from "../types";

const MAX_OWNER_COUNT = 200;
const DECIMAL_SCALE = 1_000_000n;
const PERCENT_PATTERN = /^(?:0|[1-9]\d?|100)(?:\.\d{1,6})?$/;
const SAFE_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$/;
const COUNTRY_PATTERN = /^[A-Z]{2,3}$/;
type SourceSelection = "USER_SUPPLIED_DECLARATION" | "CURRENT_EVIDENCE" | "DOCUMENT_OBSERVATIONS";

export interface ManualOwnerValues {
  relationship_id: string;
  parent_party_id: string;
  party_id: string;
  display_name: string;
  party_type: "LEGAL_ENTITY" | "NATURAL_PERSON";
  registration_number: string;
  country: string;
  ownership_percent: string;
}
type OwnerDraft = Omit<ManualOwnerValues, "party_type"> & { party_type: ManualOwnerValues["party_type"] | "" };

export interface ManualOwnershipEvidenceValues {
  evidence_document_id: string;
  evidence_document_version: number;
  source_selection: SourceSelection;
  observed_document_versions: OwnershipDocumentBinding[];
  selected_observation_ids: string[];
  as_of_date: string;
  rationale: string | null;
  root_party_id: string;
  root_display_name: string;
  parties: OwnershipParty[];
  owners: ManualOwnerValues[];
}

function scaledPercent(value: string): bigint | null {
  const normalized = value.trim();
  if (!PERCENT_PATTERN.test(normalized)) return null;
  const [whole, decimal = ""] = normalized.split(".");
  const scaled = BigInt(whole) * DECIMAL_SCALE + BigInt(decimal.padEnd(6, "0"));
  return scaled > 0n && scaled <= 100n * DECIMAL_SCALE ? scaled : null;
}

// Exact input validation only. Effective ownership and UBO results come from the server.
export function ownershipTotalIsExactly100(values: string[]): boolean {
  const scaled = values.map(scaledPercent);
  return scaled.length > 0 && scaled.every((value): value is bigint => value !== null)
    && scaled.reduce((total, value) => total + value, 0n) === 100n * DECIMAL_SCALE;
}

export function shouldShowManualOwnershipEvidence(action: string | null | undefined): boolean {
  return action === "MANUAL_OWNERSHIP_EVIDENCE";
}

function emptyOwner(index: number, rootId: string): OwnerDraft {
  return { relationship_id: `DECLARED_EDGE_${index + 1}`, parent_party_id: rootId, party_id: `OWNER_${index + 1}`,
    display_name: "", party_type: "", registration_number: "", country: "", ownership_percent: "" };
}

function currentOwners(record: OwnershipAnalysisRecord | null | undefined): OwnerDraft[] {
  return record?.relationships.flatMap((edge) => {
    const owner = record.parties.find((party) => party.party_id === edge.child_party_id);
    return owner ? [{ ...owner, registration_number: owner.registration_number ?? "", country: owner.country ?? "",
      relationship_id: edge.relationship_id, parent_party_id: edge.parent_party_id, ownership_percent: edge.ownership_percent }] : [];
  }) ?? [];
}

const normalizedName = (name: string) => name.toUpperCase().replace(/[^A-Z0-9]+/g, " ").trim();
export function ownersFromDocumentObservations(observations: DocumentOwnershipObservation[], parties: OwnershipParty[]): OwnerDraft[] {
  const nodes: Array<Omit<OwnershipParty, "party_type"> & { party_type: OwnershipParty["party_type"] | null }> = [...parties];
  function match(name: string | null, registration: string | null) {
    const matches = nodes.filter((party) => registration ? party.registration_number === registration
      : name !== null && normalizedName(party.display_name) === normalizedName(name));
    return matches.length === 1 ? matches[0] : undefined;
  }
  const ownerNodes = observations.map((observation, index) => {
    const existing = match(observation.owner_name, observation.owner_registration_identifier);
    if (existing) return existing;
    const node = { party_id: `DOC_OWNER_${index + 1}`, display_name: observation.owner_name,
      party_type: observation.owner_type, registration_number: observation.owner_registration_identifier, country: null };
    nodes.push(node);
    return node;
  });
  return observations.map((observation, index) => ({
    relationship_id: `DOCUMENT_EDGE_${index + 1}`,
    parent_party_id: match(observation.owned_entity_name, observation.owned_entity_registration_identifier)?.party_id ?? "",
    party_id: ownerNodes[index].party_id, display_name: observation.owner_name,
    party_type: observation.owner_type ?? "", registration_number: observation.owner_registration_identifier ?? "",
    country: ownerNodes[index].country ?? "", ownership_percent: observation.explicit_percentage ?? "",
  }));
}

export default function ManualOwnershipEvidenceForm({ canonicalRootUen, initialRootLegalName, documents, ownership, disabled, onSubmit, onUploadEvidence }: {
  canonicalRootUen: string;
  initialRootLegalName: string;
  documents: DocumentProcessingRecord[];
  ownership?: OwnershipAnalysisRecord | null;
  disabled: boolean;
  onSubmit: (values: ManualOwnershipEvidenceValues) => void;
  onUploadEvidence?: (file: File) => void;
}) {
  const currentDocuments = useMemo(() => documents.filter((document) => !document.superseded_by_document_id), [documents]);
  const reviewedDocuments = currentDocuments.filter((document) => document.state === "REVIEWED" || document.semantic_completion === "RECONCILIATION_RESOLVED");
  const observations = currentDocuments.flatMap((document) => document.ownership_observations ?? []);
  const bindings = currentDocuments.filter((document) => document.ownership_observations?.length)
    .map((document) => ({ document_id: document.document_id, event_count: document.events.length }))
    .sort((a, b) => a.document_id.localeCompare(b.document_id));
  const initialRoot = ownership?.parties.find((party) => party.party_id === ownership.root_party_id);
  const [documentId, setDocumentId] = useState(reviewedDocuments[0]?.document_id ?? "");
  const selectedDocument = reviewedDocuments.find((document) => document.document_id === documentId) ?? reviewedDocuments[0];
  const [sourceSelection, setSourceSelection] = useState<SourceSelection>("USER_SUPPLIED_DECLARATION");
  const [selectedObservationIds, setSelectedObservationIds] = useState<string[]>([]);
  const [asOfDates, setAsOfDates] = useState<Record<SourceSelection, string>>(() => ({
    USER_SUPPLIED_DECLARATION: ownership?.manual_review_receipt?.as_of_date ?? singaporeCalendarDate(),
    CURRENT_EVIDENCE: "", DOCUMENT_OBSERVATIONS: "",
  }));
  const selectedObservations = observations.filter(item => selectedObservationIds.includes(item.observation_id));
  const documentDates = new Set(selectedObservations.map(item => item.as_of_date));
  const sourceDate = sourceSelection === "CURRENT_EVIDENCE" ? ownership?.manual_review_receipt?.as_of_date ?? null
    : sourceSelection === "DOCUMENT_OBSERVATIONS" && documentDates.size === 1 ? [...documentDates][0] ?? null : null;
  const asOfDate = sourceDate ?? asOfDates[sourceSelection];
  const [rationale, setRationale] = useState("");
  const [rootPartyId, setRootPartyId] = useState(ownership?.root_party_id ?? `ROOT_${canonicalRootUen}`);
  const [rootDisplayName, setRootDisplayName] = useState(initialRoot?.display_name ?? initialRootLegalName);
  const [owners, setOwners] = useState<OwnerDraft[]>(() => currentOwners(ownership).length ? currentOwners(ownership) : [emptyOwner(0, ownership?.root_party_id ?? `ROOT_${canonicalRootUen}`), emptyOwner(1, ownership?.root_party_id ?? `ROOT_${canonicalRootUen}`)]);
  const [validationError, setValidationError] = useState<string | null>(null);
  const graphDisabled = disabled || sourceSelection !== "USER_SUPPLIED_DECLARATION";
  const parentOptions = [{ party_id: rootPartyId, display_name: rootDisplayName }, ...owners.filter((owner) => owner.party_type === "LEGAL_ENTITY")]
    .filter((party, index, all) => all.findIndex((item) => item.party_id === party.party_id) === index);

  function changeSource(value: SourceSelection): void {
    setSourceSelection(value);
    setValidationError(null);
    setSelectedObservationIds([]);
    if (value === "CURRENT_EVIDENCE") {
      setRootPartyId(ownership?.root_party_id ?? rootPartyId);
      setRootDisplayName(initialRoot?.display_name ?? rootDisplayName);
      setOwners(currentOwners(ownership));
    } else if (value === "DOCUMENT_OBSERVATIONS") {
      setOwners([]);
    }
  }
  function selectObservation(id: string, checked: boolean): void {
    const ids = checked ? [...selectedObservationIds, id] : selectedObservationIds.filter((item) => item !== id);
    setSelectedObservationIds(ids);
    if (checked && !selectedObservationIds.length) {
      const sourceDocumentId = observations.find((item) => item.observation_id === id)?.document_id;
      if (reviewedDocuments.some((document) => document.document_id === sourceDocumentId)) setDocumentId(sourceDocumentId!);
    }
    const selected = observations.filter((item) => ids.includes(item.observation_id));
    setOwners(ownersFromDocumentObservations(selected, [{ party_id: rootPartyId, display_name: rootDisplayName, party_type: "LEGAL_ENTITY", registration_number: canonicalRootUen, country: initialRoot?.country ?? "SG" }, ...(ownership?.parties.filter((party) => party.party_id !== rootPartyId) ?? [])]));
  }
  function updateOwner(index: number, field: keyof OwnerDraft, value: string): void {
    setOwners((current) => current.map((owner, ownerIndex) => ownerIndex === index ? { ...owner, [field]: value } : owner));
  }
  function changeRootId(value: string): void {
    setOwners((current) => current.map((owner) => owner.parent_party_id === rootPartyId ? { ...owner, parent_party_id: value } : owner));
    setRootPartyId(value);
  }
  function submit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    if (disabled || !selectedDocument) return;
    const totals = new Map<string, string[]>();
    owners.forEach((owner) => totals.set(owner.parent_party_id.trim(), [...(totals.get(owner.parent_party_id.trim()) ?? []), owner.ownership_percent]));
    if (!owners.length || (sourceSelection !== "CURRENT_EVIDENCE" && [...totals.values()].some((values) => !ownershipTotalIsExactly100(values)))) {
      setValidationError("Declared direct economic-interest percentages for each owned entity must total exactly 100. Supply explicit percentages; share counts do not imply a denominator."); return;
    }
    if (!asOfDate || (rationale.trim().length > 0 && rationale.trim().length < 10) || !rootDisplayName.trim() || owners.some((owner) => !owner.display_name.trim() || !owner.party_type || !owner.parent_party_id.trim())) {
      setValidationError("Complete all required fields; a supplied reviewer note must be at least 10 characters."); return;
    }
    const ids = [rootPartyId, ...owners.flatMap((owner) => [owner.party_id, owner.parent_party_id, owner.relationship_id])];
    if (ids.some((value) => !SAFE_ID_PATTERN.test(value.trim()))) {
      setValidationError("Root, owner, owned-entity, and relationship IDs must use 1–64 safe letters, numbers, dots, underscores, colons, or hyphens."); return;
    }
    if (owners.some((owner) => owner.party_id.trim() === rootPartyId.trim() || owner.party_id.trim() === owner.parent_party_id.trim())
      || new Set(owners.map((owner) => owner.relationship_id.trim())).size !== owners.length
      || new Set(owners.map((owner) => `${owner.parent_party_id.trim()}:${owner.party_id.trim()}`)).size !== owners.length) {
      setValidationError("Use unique relationships and distinct owner/owned-entity endpoints."); return;
    }
    if (owners.some((owner) => owner.country.trim() && !COUNTRY_PATTERN.test(owner.country.trim().toUpperCase()))) {
      setValidationError("Each supplied country must be a 2–3 letter uppercase country code."); return;
    }
    const cleanOwners = owners.map((owner) => ({ ...owner, party_type: owner.party_type as ManualOwnerValues["party_type"],
      relationship_id: owner.relationship_id.trim(), parent_party_id: owner.parent_party_id.trim(), party_id: owner.party_id.trim(), display_name: owner.display_name.trim(),
      registration_number: owner.registration_number.trim(), country: owner.country.trim().toUpperCase(), ownership_percent: owner.ownership_percent.trim() }));
    const partyMap = new Map<string, OwnershipParty>();
    partyMap.set(rootPartyId.trim(), { party_id: rootPartyId.trim(), display_name: rootDisplayName.trim(), party_type: "LEGAL_ENTITY", registration_number: canonicalRootUen, country: initialRoot?.country ?? "SG" });
    for (const owner of cleanOwners) {
      const party: OwnershipParty = { party_id: owner.party_id, display_name: owner.display_name, party_type: owner.party_type, registration_number: owner.registration_number || null, country: owner.country || null };
      const existing = partyMap.get(party.party_id);
      if (existing && JSON.stringify(existing) !== JSON.stringify(party)) { setValidationError("A repeated owner ID must retain the same name, type, registration, and country on every path."); return; }
      partyMap.set(party.party_id, party);
    }
    if ([...totals.keys()].some((id) => partyMap.get(id)?.party_type !== "LEGAL_ENTITY")) { setValidationError("Every owned entity must be a declared legal entity."); return; }
    if (sourceSelection === "DOCUMENT_OBSERVATIONS" && !selectedObservationIds.length) { setValidationError("Select current document observations before choosing document evidence."); return; }
    setValidationError(null);
    onSubmit({ evidence_document_id: selectedDocument.document_id, evidence_document_version: selectedDocument.events.length,
      source_selection: sourceSelection, observed_document_versions: bindings, selected_observation_ids: sourceSelection === "DOCUMENT_OBSERVATIONS" ? selectedObservationIds : [],
      as_of_date: asOfDate, rationale: rationale.trim() || null, root_party_id: rootPartyId.trim(), root_display_name: rootDisplayName.trim(),
      parties: sourceSelection === "CURRENT_EVIDENCE" && ownership ? ownership.parties : [...partyMap.values()], owners: cleanOwners });
  }

  return <section className="manual-ownership" aria-labelledby="manual-ownership-title">
    <p className="card-kicker">Ownership evidence decision · local proof of concept</p>
    <h2 id="manual-ownership-title">Review or edit ownership evidence</h2>
    <p className="manual-ownership__source">Supplementary client-supplied evidence · operator review · LOCAL · MANUAL_DECLARATION_POC · {sourceSelection}</p>
    <p>This declaration is not ACRA evidence or verified ownership. Original graphs, document proposals and review receipts are retained; independent blockers remain authoritative.</p>
    {onUploadEvidence && <label id="case-ownership-evidence-upload" tabIndex={-1}>Upload ownership evidence
      <input className="input" type="file" accept={UPLOAD_ACCEPT} disabled={disabled} onChange={(event) => { const file = event.target.files?.[0]; event.target.value = ""; if (file) onUploadEvidence(file); }} />
      <span className="control-help">{UPLOAD_HELP_TEXT}. Review uploaded evidence before deciding. Share counts never imply a denominator.</span>
    </label>}
    {!reviewedDocuments.length ? <p className="ds-banner ds-banner-warn" role="status">No current reviewed document is available. Review a current document before supplying manual ownership evidence.</p> : <form onSubmit={submit} noValidate>
      <div className="manual-ownership__fields">
        <label>Ownership source decision<select className="input" name="source_selection" aria-label="Ownership source decision" value={sourceSelection} disabled={disabled} onChange={(event) => changeSource(event.target.value as SourceSelection)}>
          <option value="USER_SUPPLIED_DECLARATION">Edit a reviewed manual declaration</option>
          <option value="CURRENT_EVIDENCE" disabled={!ownership?.relationships.length}>Keep current ownership evidence</option>
          <option value="DOCUMENT_OBSERVATIONS" disabled={!observations.length}>Choose proposed document observations</option>
        </select></label>
        <label>Evidence document<select className="input" aria-label="Evidence document" value={selectedDocument?.document_id ?? ""} disabled={disabled} onChange={(event) => setDocumentId(event.target.value)}>{reviewedDocuments.map((document) => <option key={document.document_id} value={document.document_id}>{document.display_name} · review revision {document.events.length}</option>)}</select></label>
        <label>Canonical root UEN<input className="input" value={canonicalRootUen} readOnly aria-readonly="true" /></label>
        <label>As-of date<input className="input" name="as_of_date" type="date" value={asOfDate} readOnly={sourceDate !== null} disabled={disabled} onChange={(event) => setAsOfDates(current => ({ ...current, [sourceSelection]: event.target.value }))} /></label>
        <label>Root legal-entity ID<input className="input" name="root_party_id" value={rootPartyId} maxLength={64} disabled={graphDisabled} onChange={(event) => changeRootId(event.target.value)} /></label>
        <label>Root legal-entity name<input className="input" name="root_display_name" value={rootDisplayName} maxLength={160} disabled={graphDisabled} onChange={(event) => setRootDisplayName(event.target.value)} /></label>
      </div>
      <p className="control-help">Declaration dates use the Singapore calendar (SGT). A new manual declaration defaults to today; retained and selected source dates stay historical. {sourceDate !== null ? "The displayed date is retained from the selected evidence." : sourceSelection !== "USER_SUPPLIED_DECLARATION" ? "A single source date is not recorded; supply an explicit date for this review decision. Original source dates remain unchanged." : ""}</p>
      <p className="control-help">Current observation bindings: {bindings.length ? bindings.map((binding) => `${binding.document_id} · review revision ${binding.event_count}`).join("; ") : "No proposed ownership observations"}. Each proposal keeps its immutable document version and page reference.</p>
      {sourceSelection === "DOCUMENT_OBSERVATIONS" && <fieldset><legend>Select proposed observations for this decision</legend>{observations.map((observation) => <label className="s2-observation-choice" key={observation.observation_id}>
        <input type="checkbox" checked={selectedObservationIds.includes(observation.observation_id)} disabled={disabled} onChange={(event) => selectObservation(observation.observation_id, event.target.checked)} />
        {observation.owner_name} → {observation.owned_entity_name ?? observation.owned_entity_registration_identifier ?? "Owned entity unknown"} · {observation.explicit_percentage !== null ? `${formatOwnershipPercent(observation.explicit_percentage)} explicit` : "Percentage not supplied"} · {observation.share_count ?? "No"} share units · denominator {observation.explicit_total_shares ?? "not supplied"} · page {observation.page_number} · {observation.source_reference} · {observation.extraction_quality ?? "UNKNOWN"} · PROPOSED
      </label>)}<p className="control-help">Missing types, ambiguous values and absent percentages need a reviewed manual declaration. The server checks selected observations against the declared graph.</p></fieldset>}
      <label className="manual-ownership__rationale">Reviewer note (optional)<textarea className="input" name="rationale" value={rationale} minLength={10} maxLength={240} disabled={disabled} onChange={(event) => setRationale(event.target.value)} /></label>
      <fieldset className="manual-ownership__owners"><legend>Declared ownership relationships</legend>
        {owners.map((owner, index) => <div className="manual-ownership__owner" key={index}><h3>Owner {index + 1}</h3><div className="manual-ownership__fields">
          <label>Relationship ID<input className="input" name={`relationship_id_${index}`} value={owner.relationship_id} maxLength={64} disabled={graphDisabled} onChange={(event) => updateOwner(index, "relationship_id", event.target.value)} /></label>
          <label>Owned legal entity<select className="input" name={`parent_party_id_${index}`} aria-label="Owned legal entity" value={owner.parent_party_id} disabled={graphDisabled} onChange={(event) => updateOwner(index, "parent_party_id", event.target.value)}><option value="">Select owned entity</option>{parentOptions.map((party) => <option key={party.party_id} value={party.party_id}>{party.display_name || party.party_id} · {party.party_id}</option>)}</select></label>
          <label>Owner ID<input className="input" name={`party_id_${index}`} value={owner.party_id} maxLength={64} disabled={graphDisabled} onChange={(event) => updateOwner(index, "party_id", event.target.value)} /></label>
          <label>Owner name<input className="input" name={`display_name_${index}`} value={owner.display_name} maxLength={160} disabled={graphDisabled} onChange={(event) => updateOwner(index, "display_name", event.target.value)} /></label>
          <label>Owner type<select className="input" name={`party_type_${index}`} aria-label="Owner type" value={owner.party_type} disabled={graphDisabled} onChange={(event) => updateOwner(index, "party_type", event.target.value)}><option value="">Select explicit type</option><option value="NATURAL_PERSON">Natural person</option><option value="LEGAL_ENTITY">Legal entity</option></select></label>
          <label>Registration number (optional)<input className="input" name={`registration_number_${index}`} value={owner.registration_number} maxLength={64} disabled={graphDisabled} onChange={(event) => updateOwner(index, "registration_number", event.target.value)} /></label>
          <label>Country (optional)<input className="input" name={`country_${index}`} value={owner.country} maxLength={3} disabled={graphDisabled} onChange={(event) => updateOwner(index, "country", event.target.value.toUpperCase())} /></label>
          <label>Economic interest %<input className="input" name={`ownership_percent_${index}`} inputMode="decimal" value={owner.ownership_percent} disabled={graphDisabled} onChange={(event) => updateOwner(index, "ownership_percent", event.target.value)} /></label>
        </div>{owners.length > 1 && <button type="button" className="btn btn-ghost" disabled={graphDisabled} onClick={() => setOwners((current) => current.filter((_, ownerIndex) => ownerIndex !== index))}>Remove owner {index + 1}</button>}</div>)}
        {owners.length < MAX_OWNER_COUNT && <button type="button" className="btn btn-secondary" disabled={graphDisabled} onClick={() => setOwners((current) => { let next = current.length; while (current.some((item) => item.party_id === `OWNER_${next + 1}` || item.relationship_id === `DECLARED_EDGE_${next + 1}`)) next += 1; return [...current, emptyOwner(next, rootPartyId)]; })}>Add owner</button>}
      </fieldset>
      <p className="control-help">Current evidence retains its exact known percentages, including partial ownership. Edited declarations and chosen document observations must total 100 for each declared owned entity. Reuse an owner ID for multiple paths with the same party details. Exact decimal strings go to the server's single calculator; effective ownership is never calculated here. A successful edit refreshes readiness and requires a new submission confirmation.</p>
      {validationError && <p className="ds-banner ds-banner-warn" role="alert">{validationError}</p>}
      <button type="submit" className="btn btn-primary" disabled={disabled}>Submit manual ownership evidence</button>
    </form>}
  </section>;
}
