import { useState, type FormEvent } from "react";

import type { OnboardingCase } from "../types";

export interface IdentityCorrectionValues {
  legal_name: string;
  registration_number: string;
  country_of_incorporation: "SG";
}

export default function IdentityCorrectionForm({
  onboardingCase,
  disabled,
  onSubmit,
}: {
  onboardingCase: OnboardingCase;
  disabled: boolean;
  onSubmit: (values: IdentityCorrectionValues) => void;
}) {
  const initial = onboardingCase.initial_identity;
  const [legalName, setLegalName] = useState(initial?.legal_name ?? "");
  const [registrationNumber, setRegistrationNumber] = useState(
    initial?.registration_number ?? onboardingCase.requested_uen ?? "",
  );
  const legalNameValue = legalName.trim();
  const registrationNumberValue = registrationNumber.trim().toUpperCase();
  const complete = legalNameValue.length > 0 && registrationNumberValue.length > 0;

  function submit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    if (disabled || !complete) return;
    onSubmit({
      legal_name: legalNameValue,
      registration_number: registrationNumberValue,
      country_of_incorporation: "SG",
    });
  }

  return (
    <section className="identity-correction" aria-labelledby="identity-correction-title">
      <p className="card-kicker">Corrective action · same case</p>
      <h2 id="identity-correction-title">Complete company details</h2>
      <p>
        Enter the company identity to run another read-only GoldTier Search for this case.
        These proposed values are not authoritative registry evidence; the backend retains the
        correction and decides the resulting workflow state.
      </p>
      <form onSubmit={submit}>
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
          Save details and recheck Search
        </button>
      </form>
    </section>
  );
}
