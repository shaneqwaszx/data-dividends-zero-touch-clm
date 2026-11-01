import { useState, type FormEvent } from "react";

import type { EntityCategory, OnboardingCase } from "../types";

export interface IdentityCorrectionValues {
  legal_name: string;
  registration_number: string;
  country_of_incorporation: "SG";
  choice?: "ENTERED" | "DOCUMENT" | "OTHER";
  document_id?: string;
  expected_document_event_count?: number;
  /** D-114: the entity type to verify; GOVERNMENT is read only from the government register. */
  entity_category?: EntityCategory;
}

export default function IdentityCorrectionForm({
  onboardingCase,
  disabled,
  onSubmit,
  registryRecovery = false,
  documentCandidates = [],
  error = null,
}: {
  onboardingCase: OnboardingCase;
  disabled: boolean;
  onSubmit: (values: IdentityCorrectionValues) => void;
  registryRecovery?: boolean;
  error?: string | null;
  documentCandidates?: Array<{ uen: string; documentId: string; eventCount: number }>;
}) {
  const initial = onboardingCase.initial_identity;
  const originalUen = onboardingCase.identity_corrections?.[0]?.previous_identity?.registration_number
    ?? onboardingCase.requested_uen;
  const [legalName, setLegalName] = useState(initial?.legal_name ?? "");
  const [registrationNumber, setRegistrationNumber] = useState(
    initial?.registration_number ?? onboardingCase.requested_uen ?? "",
  );
  const legalNameValue = legalName.trim();
  const registrationNumberValue = registrationNumber.trim().toUpperCase();
  const complete = legalNameValue.length > 0 && registrationNumberValue.length > 0;
  const [entityCategory, setEntityCategory] = useState<EntityCategory>(initial?.entity_category ?? "COMPANY");
  // D-114: a government register stop is corrected by the UEN or the entity type.
  const governmentRegisterStop = ["GOVERNMENT_IDENTITY_NOT_FOUND", "ENTITY_CATEGORY_MISMATCH"]
    .includes(onboardingCase.error?.code ?? "");
  // Sent only when changed: an omitted category keeps the case's current one.
  const categoryChange = entityCategory !== (initial?.entity_category ?? "COMPANY")
    ? { entity_category: entityCategory } : {};
  const [editing, setEditing] = useState(!registryRecovery || !initial?.legal_name);
  const [validationError, setValidationError] = useState<string | null>(null);
  // UEN mismatch: one choice ("ENTERED", a document id, or "OTHER") and one confirm button.
  const conflict = registryRecovery && documentCandidates.length > 0;
  const [selection, setSelection] = useState<string>("");

  function choose(uen: string, choice: "ENTERED" | "DOCUMENT", documentId?: string, eventCount?: number): void {
    if (disabled || !legalNameValue) return;
    onSubmit({ legal_name: legalNameValue, registration_number: uen, country_of_incorporation: "SG",
      choice, document_id: documentId, expected_document_event_count: eventCount, ...categoryChange });
  }

  function confirmChoice(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    if (disabled || !legalNameValue) return;
    if (selection === "ENTERED") { choose(onboardingCase.requested_uen, "ENTERED"); return; }
    const candidate = documentCandidates.find(item => item.documentId === selection);
    if (candidate) { choose(candidate.uen, "DOCUMENT", candidate.documentId, candidate.eventCount); return; }
    if (selection === "OTHER") submit(event);
  }

  function submit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    if (disabled || !complete) return;
    if (!/^(?:[0-9]{8}[A-Z]|[0-9]{9}[A-Z]|[TSR][0-9]{2}[A-Z]{2}[0-9]{4}[A-Z])$/.test(registrationNumberValue)) {
      setValidationError("Enter a Singapore UEN in the supported format before verification.");
      return;
    }
    setValidationError(null);
    onSubmit({
      legal_name: legalNameValue,
      registration_number: registrationNumberValue,
      country_of_incorporation: "SG",
      ...categoryChange,
      ...(registryRecovery ? { choice: "OTHER" as const } : {}),
    });
  }

  return (
    <section className="identity-correction" aria-labelledby="identity-correction-title">
      <p className="card-kicker">Corrective action · same case</p>
      <h2 id="identity-correction-title">{registryRecovery ? "Registry identity" : "Complete company details"}</h2>
      {registryRecovery && !conflict && <>
        <p>Original entered UEN: <strong>{originalUen}</strong></p>
        {originalUen !== onboardingCase.requested_uen && <p>Current corrected UEN: <strong>{onboardingCase.requested_uen}</strong></p>}
      </>}
      {registryRecovery && onboardingCase.error &&
        (onboardingCase.error.code.startsWith("ACRA_") ||
         onboardingCase.error.code.startsWith("REGISTRY_")) &&
        <p role="status">Registry verification could not verify this UEN.</p>}
      {registryRecovery && governmentRegisterStop && <p role="status">{onboardingCase.error?.message}</p>}
      {conflict && <form className="identity-choice" aria-label="UEN identity choices" onSubmit={confirmChoice}>
        <h3>Entity identity requires confirmation</h3>
        <p className="control-help">The UEN you entered and the UEN found in the document don't match. Choose the one to verify; the backend re-checks the registry and resumes the case.</p>
        {(validationError || error) && <p role="alert" className="ds-banner ds-banner-warn">{validationError || error}</p>}
        <div className="identity-choice__options" role="radiogroup" aria-label="UEN to verify">
          <label className={`identity-choice__option${selection === "ENTERED" ? " is-chosen" : ""}`}>
            <input type="radio" name="uen-choice" value="ENTERED" checked={selection === "ENTERED"} disabled={disabled} onChange={() => setSelection("ENTERED")} />
            <span className="identity-choice__label">Entered UEN</span>
            <strong className="identity-choice__value">{onboardingCase.requested_uen}</strong>
            {originalUen !== onboardingCase.requested_uen && <small className="control-help">Originally entered: {originalUen}</small>}
          </label>
          {documentCandidates.map((candidate) => (
            <label key={candidate.documentId} className={`identity-choice__option${selection === candidate.documentId ? " is-chosen" : ""}`}>
              <input type="radio" name="uen-choice" value={candidate.documentId} checked={selection === candidate.documentId} disabled={disabled} onChange={() => setSelection(candidate.documentId)} />
              <span className="identity-choice__label">Document UEN</span>
              <strong className="identity-choice__value">{candidate.uen}</strong>
            </label>
          ))}
          <label className={`identity-choice__option${selection === "OTHER" ? " is-chosen" : ""}`}>
            <input type="radio" name="uen-choice" value="OTHER" checked={selection === "OTHER"} disabled={disabled} onChange={() => setSelection("OTHER")} />
            <span className="identity-choice__label">Another UEN</span>
            <input id="identity-registration-number" className="input" aria-label="Singapore UEN" value={registrationNumber} maxLength={32}
              autoCapitalize="characters" disabled={disabled}
              onFocus={() => setSelection("OTHER")}
              onChange={(event) => { setSelection("OTHER"); setRegistrationNumber(event.target.value.toUpperCase()); }} />
          </label>
        </div>
        {(!initial?.legal_name || selection === "OTHER") && <div className="identity-choice__name">
          <label htmlFor="identity-legal-name">Legal company name</label>
          <input id="identity-legal-name" className="input" value={legalName} maxLength={160} autoComplete="organization"
            disabled={disabled} onChange={(event) => setLegalName(event.target.value)} required />
        </div>}
        <div className="identity-choice__name">
          <label htmlFor="identity-choice-entity-category">Entity type</label>
          <select id="identity-choice-entity-category" className="input" value={entityCategory} disabled={disabled}
            onChange={(event) => setEntityCategory(event.target.value as EntityCategory)}>
            <option value="COMPANY">Company</option>
            <option value="PARTNERSHIP">Partnership</option>
            <option value="GOVERNMENT">Government body</option>
          </select>
        </div>
        <div className="identity-choice__actions">
          <button type="submit" className="btn btn-primary"
            disabled={disabled || !selection || !legalNameValue || (selection === "OTHER" && !registrationNumberValue)}>Confirm UEN and resume</button>
        </div>
      </form>}
      {!conflict && registryRecovery && !editing && <button type="button" className="btn btn-secondary" disabled={disabled} onClick={() => setEditing(true)}>{governmentRegisterStop ? "Edit UEN or entity type" : "Edit UEN"}</button>}
      {!conflict && (!registryRecovery || editing) && <>
      <p>{registryRecovery ? "Verify the proposed UEN through the existing registry acquisition path. The backend retains the correction, re-evaluates documents and resumes dependent processing." : <>
        Enter the company identity to run another read-only GoldTier Search for this case.
        These proposed values are not authoritative registry evidence; the backend retains the
        correction and decides the resulting workflow state.
      </>}</p>
      <form onSubmit={submit}>
        {(validationError || error) && <p role="alert" className="ds-banner ds-banner-warn">{validationError || error}</p>}
        <div className="identity-correction__fields">
          <div>
            <label htmlFor="identity-legal-name">Legal company name</label>
            <input
              id="identity-legal-name"
              className="input"
              value={legalName}
              maxLength={160}
              autoComplete="organization"
              disabled={disabled}
              onChange={(event) => setLegalName(event.target.value)}
              required
            />
          </div>
          <div>
            <label htmlFor="identity-registration-number">Singapore UEN</label>
            <input
              id="identity-registration-number"
              className="input"
              value={registrationNumber}
              maxLength={32}
              autoCapitalize="characters"
              disabled={disabled}
              onChange={(event) => setRegistrationNumber(event.target.value.toUpperCase())}
              required
            />
          </div>
          <div>
            <label htmlFor="identity-country">Country of incorporation</label>
            <input id="identity-country" className="input" value="SG" readOnly aria-readonly="true" />
          </div>
          <div>
            <label htmlFor="identity-entity-category">Entity type</label>
            <select id="identity-entity-category" className="input" value={entityCategory} disabled={disabled}
              onChange={(event) => setEntityCategory(event.target.value as EntityCategory)}>
              <option value="COMPANY">Company</option>
              <option value="PARTNERSHIP">Partnership</option>
              <option value="GOVERNMENT">Government body</option>
            </select>
          </div>
        </div>
        <p className="control-help">
          SG is explicit and fixed for this implemented ACRA route. A successful Search does not
          establish registry truth, customer approval, or Ready-for-Approval status.
        </p>
        <button type="submit" className="btn btn-primary" disabled={disabled || !complete}>
          {registryRecovery ? "Verify UEN and resume" : "Save details and recheck Search"}
        </button>
      </form>
      </>}
    </section>
  );
}
