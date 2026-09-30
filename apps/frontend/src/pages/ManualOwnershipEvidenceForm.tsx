import { useMemo, useState, type FormEvent } from "react";

import type { DocumentProcessingRecord } from "../types";

const MAX_OWNER_COUNT = 20;
const DECIMAL_SCALE = 1_000_000n;
const PERCENT_PATTERN = /^(?:0|[1-9]\d?|100)(?:\.\d{1,6})?$/;
const SAFE_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$/;
const COUNTRY_PATTERN = /^[A-Z]{2,3}$/;

export interface ManualOwnerValues {
  relationship_id: string;
  party_id: string;
  display_name: string;
  party_type: "LEGAL_ENTITY" | "NATURAL_PERSON";
  registration_number: string;
  country: string;
  ownership_percent: string;
}

export interface ManualOwnershipEvidenceValues {
  evidence_document_id: string;
  evidence_document_version: number;
  as_of_date: string;
  rationale: string;
  root_party_id: string;
  root_display_name: string;
  owners: ManualOwnerValues[];
}

function scaledPercent(value: string): bigint | null {
  const normalized = value.trim();
  if (!PERCENT_PATTERN.test(normalized)) return null;
  const [whole, decimal = ""] = normalized.split(".");
  const scaled = BigInt(whole) * DECIMAL_SCALE + BigInt(decimal.padEnd(6, "0"));
  return scaled > 0n && scaled <= 100n * DECIMAL_SCALE ? scaled : null;
}

export function ownershipTotalIsExactly100(values: string[]): boolean {
  const scaled = values.map(scaledPercent);
  return scaled.length > 0
    && scaled.every((value): value is bigint => value !== null)
    && scaled.reduce((total, value) => total + value, 0n) === 100n * DECIMAL_SCALE;
}

export function shouldShowManualOwnershipEvidence(action: string | null | undefined): boolean {
  return action === "MANUAL_OWNERSHIP_EVIDENCE";
}

function emptyOwner(index: number): ManualOwnerValues {
  return {
    relationship_id: `DIRECT_OWNER_${index + 1}`,
    party_id: `OWNER_${index + 1}`,
    display_name: "",
    party_type: "NATURAL_PERSON",
    registration_number: "",
    country: "SG",
    ownership_percent: index === 0 ? "60" : "40",
  };
}

export default function ManualOwnershipEvidenceForm({
  canonicalRootUen,
  initialRootLegalName,
  documents,
  disabled,
  onSubmit,
}: {
  canonicalRootUen: string;
  initialRootLegalName: string;
  documents: DocumentProcessingRecord[];
  disabled: boolean;
  onSubmit: (values: ManualOwnershipEvidenceValues) => void;
}) {
  const reviewedDocuments = useMemo(
    () => documents.filter(
      (document) => document.state === "REVIEWED" && !document.superseded_by_document_id,
    ),
    [documents],
  );
  const [documentId, setDocumentId] = useState(reviewedDocuments[0]?.document_id ?? "");
  const [asOfDate, setAsOfDate] = useState(new Date().toISOString().slice(0, 10));
  const [rationale, setRationale] = useState("");
  const [rootPartyId, setRootPartyId] = useState(`ROOT_${canonicalRootUen}`);
  const [rootDisplayName, setRootDisplayName] = useState(initialRootLegalName);
  const [owners, setOwners] = useState<ManualOwnerValues[]>([emptyOwner(0), emptyOwner(1)]);
  const [validationError, setValidationError] = useState<string | null>(null);

  function updateOwner(index: number, field: keyof ManualOwnerValues, value: string): void {
    setOwners((current) => current.map((owner, ownerIndex) => (
      ownerIndex === index ? { ...owner, [field]: value } : owner
    )));
  }

  function submit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    const selectedDocument = reviewedDocuments.find((document) => document.document_id === documentId);
    if (disabled || !selectedDocument) return;
    if (!ownershipTotalIsExactly100(owners.map((owner) => owner.ownership_percent))) {
      setValidationError("Direct economic-interest percentages must total exactly 100.");
      return;
    }
    const requiredValues = [rootPartyId, rootDisplayName, asOfDate, rationale, ...owners.flatMap(
      (owner) => [owner.relationship_id, owner.party_id, owner.display_name, owner.country],
    )];
    if (rationale.trim().length < 10 || requiredValues.some((value) => !value.trim())) {
      setValidationError("Complete all required fields; the rationale must be at least 10 characters.");
      return;
    }
    const ownerIds = owners.map((owner) => owner.party_id.trim());
    const relationshipIds = owners.map((owner) => owner.relationship_id.trim());
    if (
      !SAFE_ID_PATTERN.test(rootPartyId.trim())
      || ownerIds.some((value) => !SAFE_ID_PATTERN.test(value))
      || relationshipIds.some((value) => !SAFE_ID_PATTERN.test(value))
    ) {
      setValidationError("Root, owner, and relationship IDs must use 1–64 safe letters, numbers, dots, underscores, colons, or hyphens.");
      return;
    }
    if (
      new Set(ownerIds).size !== ownerIds.length
      || new Set(relationshipIds).size !== relationshipIds.length
      || ownerIds.includes(rootPartyId.trim())
    ) {
      setValidationError("Root, owner, and relationship IDs must be distinct.");
      return;
    }
    if (owners.some((owner) => !COUNTRY_PATTERN.test(owner.country.trim().toUpperCase()))) {
      setValidationError("Each owner country must be a 2–3 letter uppercase country code.");
      return;
    }
    setValidationError(null);
    onSubmit({
      evidence_document_id: selectedDocument.document_id,
      evidence_document_version: selectedDocument.events.length,
      as_of_date: asOfDate,
      rationale: rationale.trim(),
      root_party_id: rootPartyId.trim(),
      root_display_name: rootDisplayName.trim(),
      owners: owners.map((owner) => ({
        ...owner,
        relationship_id: owner.relationship_id.trim(),
        party_id: owner.party_id.trim(),
        display_name: owner.display_name.trim(),
        registration_number: owner.registration_number.trim(),
        country: owner.country.trim().toUpperCase(),
        ownership_percent: owner.ownership_percent.trim(),
      })),
    });
  }

  return (
    <section className="manual-ownership" aria-labelledby="manual-ownership-title">
      <p className="card-kicker">Ownership recovery · local proof of concept</p>
      <h2 id="manual-ownership-title">Provide reviewed ownership declaration</h2>
      <p className="manual-ownership__source">
        User-supplied declaration · LOCAL · MANUAL_DECLARATION_POC
      </p>
      <p>
        This declaration is not ACRA evidence or verified ownership. It replaces only the
        ownership evidence for this case; independent blockers remain authoritative.
      </p>

      {reviewedDocuments.length === 0 ? (
        <p className="ds-banner ds-banner-warn" role="status">
          No current reviewed document is available. Review a current document before supplying
          manual ownership evidence.
        </p>
      ) : (
        <form onSubmit={submit} noValidate>
          <div className="manual-ownership__fields">
            <label>
              Evidence document
              <select className="input" value={documentId} disabled={disabled} onChange={(event) => setDocumentId(event.target.value)}>
                {reviewedDocuments.map((document) => (
                  <option key={document.document_id} value={document.document_id}>
                    {document.display_name} · version {document.events.length}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Canonical root UEN
              <input className="input" value={canonicalRootUen} readOnly aria-readonly="true" />
            </label>
            <label>
              As-of date
              <input className="input" type="date" value={asOfDate} disabled={disabled} onChange={(event) => setAsOfDate(event.target.value)} />
            </label>
            <label>
              Root legal-entity ID
              <input className="input" name="root_party_id" value={rootPartyId} maxLength={64} disabled={disabled} onChange={(event) => setRootPartyId(event.target.value)} />
            </label>
            <label>
              Root legal-entity name
              <input className="input" name="root_display_name" value={rootDisplayName} maxLength={160} disabled={disabled} onChange={(event) => setRootDisplayName(event.target.value)} />
            </label>
            <label>
              Root country
              <input className="input" value="SG" readOnly aria-readonly="true" />
            </label>
          </div>

          <label className="manual-ownership__rationale">
            Review rationale
            <textarea className="input" name="rationale" value={rationale} minLength={10} maxLength={240} disabled={disabled} onChange={(event) => setRationale(event.target.value)} />
          </label>

          <fieldset className="manual-ownership__owners">
            <legend>Direct economic-interest owners</legend>
            {owners.map((owner, index) => (
              <div className="manual-ownership__owner" key={index}>
                <h3>Owner {index + 1}</h3>
                <div className="manual-ownership__fields">
                  <label>Relationship ID<input className="input" name={`relationship_id_${index}`} value={owner.relationship_id} maxLength={64} disabled={disabled} onChange={(event) => updateOwner(index, "relationship_id", event.target.value)} /></label>
                  <label>Owner ID<input className="input" name={`party_id_${index}`} value={owner.party_id} maxLength={64} disabled={disabled} onChange={(event) => updateOwner(index, "party_id", event.target.value)} /></label>
                  <label>Owner name<input className="input" name={`display_name_${index}`} value={owner.display_name} maxLength={160} disabled={disabled} onChange={(event) => updateOwner(index, "display_name", event.target.value)} /></label>
                  <label>Owner type<select className="input" value={owner.party_type} disabled={disabled} onChange={(event) => updateOwner(index, "party_type", event.target.value)}><option value="NATURAL_PERSON">Natural person</option><option value="LEGAL_ENTITY">Legal entity</option></select></label>
                  <label>Registration number (optional)<input className="input" value={owner.registration_number} maxLength={64} disabled={disabled} onChange={(event) => updateOwner(index, "registration_number", event.target.value)} /></label>
                  <label>Country<input className="input" value={owner.country} minLength={2} maxLength={3} disabled={disabled} onChange={(event) => updateOwner(index, "country", event.target.value.toUpperCase())} /></label>
                  <label>Economic interest %<input className="input" name={`ownership_percent_${index}`} inputMode="decimal" value={owner.ownership_percent} disabled={disabled} onChange={(event) => updateOwner(index, "ownership_percent", event.target.value)} /></label>
                </div>
                {owners.length > 1 && <button type="button" className="btn btn-ghost" disabled={disabled} onClick={() => setOwners((current) => current.filter((_, ownerIndex) => ownerIndex !== index))}>Remove owner {index + 1}</button>}
              </div>
            ))}
            {owners.length < MAX_OWNER_COUNT && <button type="button" className="btn btn-secondary" disabled={disabled} onClick={() => setOwners((current) => [...current, emptyOwner(current.length)])}>Add owner</button>}
          </fieldset>

          <p className="control-help">Each percentage is sent as an exact decimal string (up to 6 decimal places). The server revalidates the declaration and all version checks.</p>
          {validationError && <p className="ds-banner ds-banner-warn" role="alert">{validationError}</p>}
          <button type="submit" className="btn btn-primary" disabled={disabled}>
            Submit manual ownership evidence
          </button>
        </form>
      )}
    </section>
  );
}
