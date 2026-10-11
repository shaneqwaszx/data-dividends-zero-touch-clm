import { useState, type FormEvent } from "react";

import type { OnboardingCase } from "../types";

export interface IdentityCorrectionValues {
  legal_name: string;
  registration_number: string;
  country_of_incorporation: "SG";
  choice?: "ENTERED" | "DOCUMENT" | "OTHER";
  document_id?: string;
  expected_document_event_count?: number;
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
  const [editing, setEditing] = useState(!registryRecovery || !initial?.legal_name);
  const [validationError, setValidationError] = useState<string | null>(null);

  function choose(uen: string, choice: "ENTERED" | "DOCUMENT", documentId?: string, eventCount?: number): void {
    if (disabled || !legalNameValue) return;
    onSubmit({ legal_name: legalNameValue, registration_number: uen, country_of_incorporation: "SG",
      choice, document_id: documentId, expected_document_event_count: eventCount });
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
      ...(registryRecovery ? { choice: "OTHER" as const } : {}),
    });
  }

  return (
    <section className="identity-correction" aria-labelledby="identity-correction-title">
      <p className="card-kicker">Corrective action · same case</p>
      <h2 id="identity-correction-title">{registryRecovery ? "Registry identity" : "Complete company details"}</h2>
      {registryRecovery && <>
        <p>Original entered UEN: <strong>{originalUen}</strong></p>
        {originalUen !== onboardingCase.requested_uen && <p>Current corrected UEN: <strong>{onboardingCase.requested_uen}</strong></p>}
      </>}
      {registryRecovery && onboardingCase.error &&
        (onboardingCase.error.code.startsWith("ACRA_") ||
         onboardingCase.error.code.startsWith("REGISTRY_")) &&
        <p role="status">Registry verification could not verify this UEN.</p>}
      {registryRecovery && documentCandidates.length > 0 && <section aria-label="UEN identity choices">
        <h3>Entity identity requires confirmation</h3>
        <p>Use the current entered identity: <strong>{onboardingCase.requested_uen}</strong></p>
        <button type="button" className="btn btn-secondary" disabled={disabled || !legalNameValue} onClick={() => choose(onboardingCase.requested_uen, "ENTERED")}>Use entered UEN</button>
        {documentCandidates.map((candidate) => <div key={candidate.documentId}>
          <p>Document-detected UEN: <strong>{candidate.uen}</strong></p>
          <button type="button" className="btn btn-secondary" disabled={disabled || !legalNameValue} onClick={() => choose(candidate.uen, "DOCUMENT", candidate.documentId, candidate.eventCount)}>Use document UEN</button>
        </div>)}
        <button type="button" className="btn btn-secondary" disabled={disabled} onClick={() => setEditing(true)}>Enter another UEN</button>
      </section>}
      {registryRecovery && !editing && <button type="button" className="btn btn-secondary" disabled={disabled} onClick={() => setEditing(true)}>Edit UEN</button>}
      {(!registryRecovery || editing) && <>
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
