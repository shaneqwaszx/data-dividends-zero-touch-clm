import { useState, type FormEvent } from "react";

import type { GoldTierTargetClassification, PolicyRebindMetadata } from "../types";

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
  classification,
  registrationNumber,
  disabled,
  onSubmit,
  onFocusClassification,
}: {
  metadata: PolicyRebindMetadata;
  classification?: GoldTierTargetClassification;
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
      <h2 id="policy-rebind-title">GoldTier submission settings</h2>
      <p>
        Shows the case-bound values that will be used to prepare this Singapore GoldTier submission.
        Submission preparation is separate from GoldTier KYC and four-eye approval.
      </p>

      <div className="policy-rebind__categories">
        <section aria-labelledby="policy-rebind-accepted">
          <h3 id="policy-rebind-accepted">System-set Singapore values</h3>
          <p className="control-help">System-set Singapore values remain unchanged by uploaded documents.</p>
          <ul>
            {ACCEPTED_CONFIGURATION_FIELDS.map((field) => (
              <li key={field}>
                {fieldLabel(field)} · {accepted.has(field) ? ({ customerExternalSystem: "DSD", registrationType: "ACRA", policy: "Singapore", bookingEntity: "ANZBGL (Singapore Branch)" }[field]) : "requires rebind"}
              </li>
            ))}
          </ul>
        </section>

        <section aria-labelledby="policy-rebind-automatic">
          <h3 id="policy-rebind-automatic">Automatically classified from evidence</h3>
          <ul>{classification && [classification.kyc_customer_type, classification.client_segment].filter((field) => field.selection?.source === "DOCUMENT").map((field, index) => <li key={index}>{field.selected_value} · Automatically classified from document</li>)}</ul>
        </section>
        <section aria-labelledby="policy-rebind-editable">
          <h3 id="policy-rebind-editable">User input required</h3>
          <p className="control-help">Only when automation cannot safely determine a value. Retained user choices remain separate from system values.</p>
          <ul>{metadata.editable_fields.filter((field) => !classification || (field === "kycCustomerType" ? classification.kyc_customer_type : classification.client_segment).selection?.source !== "DOCUMENT").map((field) => <li key={field}>{fieldLabel(field)}</li>)}</ul>
          {(!classification || !classification.kyc_customer_type.selected_value || !classification.client_segment.selected_value) && <button type="button" className="btn btn-ghost" onClick={onFocusClassification}>Focus editable KYC and segment</button>}
        </section>

        <section aria-labelledby="policy-rebind-unavailable">
          <h3 id="policy-rebind-unavailable">Unavailable / not transmitted</h3>
          {metadata.unavailable_fields.length ? (
            <ul>{metadata.unavailable_fields.map((field) => <li key={field}>{fieldLabel(field)} · Unavailable / not transmitted</li>)}</ul>
          ) : <p>No unavailable fields are projected.</p>}
        </section>
      </div>

      <details><summary>Technical authority and policy history</summary>
      <footer className="policy-rebind__receipt">
        <p>Registration number · {registrationNumber}</p>
        <p>Updating system values preserves retained classifications and history.</p>
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
      </details>

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
            Update system-set Singapore values
          </button>
        </form>
      )}
    </section>
  );
}
