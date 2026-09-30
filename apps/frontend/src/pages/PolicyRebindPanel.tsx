import { useState, type FormEvent } from "react";

import type { PolicyRebindMetadata } from "../types";

const ACCEPTED_CONFIGURATION_FIELDS = [
  "customerExternalSystem",
  "registrationType",
  "policy",
  "bookingEntity",
] as const;

const FIELD_LABELS: Record<string, string> = {
  customerExternalSystem: "Customer external system",
  registrationType: "Registration type",
  policy: "Policy",
  bookingEntity: "Booking entity",
  kycCustomerType: "KYC customer type",
  clientSegment: "Client segment",
  registrationNumber: "Registration number",
  accountEntityType: "Account entity type",
  productType: "Product type",
};

function fieldLabel(field: string): string {
  return FIELD_LABELS[field] ?? field.replace(/([a-z])([A-Z])/g, "$1 $2").replace(/^./, (value) => value.toUpperCase());
}

export default function PolicyRebindPanel({
  metadata,
  registrationNumber,
  disabled,
  onSubmit,
  onFocusClassification,
}: {
  metadata: PolicyRebindMetadata;
  registrationNumber: string;
  disabled: boolean;
  onSubmit: (rationale: string) => void;
  onFocusClassification: () => void;
}) {
  const [rationale, setRationale] = useState("");
  const requiresRebind = metadata.configuration_status === "REQUIRES_REBIND";
  const accepted = new Set(metadata.accepted_poc_fields);
  const rationaleValue = rationale.trim();

  function submit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    if (disabled || !requiresRebind || rationaleValue.length < 10) return;
    onSubmit(rationaleValue);
  }

  return (
    <section id="case-policy-rebind" className="policy-rebind evidence-focus-target" tabIndex={-1} aria-labelledby="policy-rebind-title">
      <p className="card-kicker">Case-bound target configuration</p>
      <h2 id="policy-rebind-title">Singapore POC configuration authority</h2>
      <p>
        Rebinding updates only the accepted system configuration. It preserves operator-selected
        KYC and segment choices and retained history; it is not a wholesale reset, sponsor
        approval, compliance approval, or Ready-for-Approval.
      </p>

      <div className="policy-rebind__categories">
        <section aria-labelledby="policy-rebind-accepted">
          <h3 id="policy-rebind-accepted">Accepted system configuration</h3>
          <p className="control-help">Accepted Singapore POC constants owned by current system configuration.</p>
          <ul>
            {ACCEPTED_CONFIGURATION_FIELDS.map((field) => (
              <li key={field}>
                {fieldLabel(field)} · {accepted.has(field) ? "accepted for this case" : "requires rebind"}
              </li>
            ))}
          </ul>
        </section>

        <section aria-labelledby="policy-rebind-editable">
          <h3 id="policy-rebind-editable">Editable operator choices</h3>
          <p className="control-help">These remain separate case controls and are not overwritten by rebind.</p>
          <ul>{metadata.editable_fields.map((field) => <li key={field}>{fieldLabel(field)} · User-authorized POC choice</li>)}</ul>
          <button type="button" className="btn btn-ghost" onClick={onFocusClassification}>
            Focus editable KYC and segment
          </button>
        </section>

        <section aria-labelledby="policy-rebind-upstream">
          <h3 id="policy-rebind-upstream">Upstream identity field</h3>
          <ul>{metadata.upstream_fields.map((field) => (
            <li key={field}>{fieldLabel(field)} · {field === "registrationNumber" ? registrationNumber : "Supplied upstream"}</li>
          ))}</ul>
        </section>

        <section aria-labelledby="policy-rebind-unavailable">
          <h3 id="policy-rebind-unavailable">Unavailable fields</h3>
          {metadata.unavailable_fields.length ? (
            <ul>{metadata.unavailable_fields.map((field) => <li key={field}>{fieldLabel(field)} · unavailable pending sponsor authority</li>)}</ul>
          ) : <p>No unavailable fields are projected.</p>}
        </section>
      </div>

      <footer className="policy-rebind__receipt">
        <p><strong>Policy snapshot revision:</strong> {metadata.revision}</p>
        <p><strong>Configuration status:</strong> {requiresRebind ? "Requires rebind" : "Current accepted POC"}</p>
        {!requiresRebind && metadata.last_rebound_by && metadata.last_rebound_at && (
          <div aria-label="Latest policy rebind receipt">
            <p><strong>Last rebound by:</strong> {metadata.last_rebound_by}</p>
            <p><strong>Last rebound at:</strong> {new Date(metadata.last_rebound_at).toLocaleString()}</p>
            <p><strong>Rationale:</strong> {metadata.last_rationale ?? "Not retained"}</p>
            <p><strong>Changed accepted fields:</strong> {metadata.last_changed_fields.map(fieldLabel).join(", ") || "None"}</p>
          </div>
        )}
      </footer>

      {requiresRebind && (
        <form onSubmit={submit}>
          <label htmlFor="policy-rebind-rationale">Rebind rationale</label>
          <textarea
            id="policy-rebind-rationale"
            className="input"
            minLength={10}
            maxLength={240}
            required
            disabled={disabled}
            value={rationale}
            onChange={(event) => setRationale(event.target.value)}
          />
          <p className="control-help">The backend applies current accepted Singapore POC constants and rechecks every retained version.</p>
          <button type="submit" className="btn btn-primary" disabled={disabled || rationaleValue.length < 10}>
            Rebind accepted Singapore POC configuration
          </button>
        </form>
      )}
    </section>
  );
}
