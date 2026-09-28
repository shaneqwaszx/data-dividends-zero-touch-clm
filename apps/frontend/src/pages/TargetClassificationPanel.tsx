import { useState, type FormEvent } from "react";

import type { GoldTierTargetClassification } from "../types";

interface TargetClassificationInput {
  kyc_customer_type: string;
  client_segment: string;
}

function authorityLabel(authority: string | null): string {
  return authority ? authority.replaceAll("_", " ") : "Not recorded";
}

export default function TargetClassificationPanel({
  classification,
  disabled,
  onSubmit,
}: {
  classification: GoldTierTargetClassification;
  disabled: boolean;
  onSubmit: (input: TargetClassificationInput) => Promise<void>;
}) {
  const [kycCustomerType, setKycCustomerType] = useState(
    classification.kyc_customer_type.selected_value ?? "",
  );
  const [clientSegment, setClientSegment] = useState(
    classification.client_segment.selected_value ?? "",
  );
  const unresolved = classification.kyc_customer_type.selected_value === null
    || classification.client_segment.selected_value === null;
  const canEdit = classification.editable && unresolved;

  function submit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    if (!kycCustomerType || !clientSegment || disabled) return;
    void onSubmit({
      kyc_customer_type: kycCustomerType,
      client_segment: clientSegment,
    });
  }

  return (
    <section className="card" aria-labelledby="goldtier-target-classification-heading" style={{ marginBottom: 16 }}>
      <p className="section-label">GoldTier target input</p>
      <h3 id="goldtier-target-classification-heading">Target classification</h3>
      <p className="control-help">
        Vocabulary {classification.vocabulary_version}. Values are selected by a POC operator from
        backend-owned sponsor vocabulary and retained with the case. This is not autonomous
        classification, compliance approval, or Ready-for-Approval.
      </p>

      {canEdit ? (
        <form onSubmit={submit}>
          <div className="ds-two-col">
            <label style={{ flex: 1 }}>
              KYC customer type
              <select
                aria-label="KYC customer type"
                required={classification.kyc_customer_type.required}
                value={kycCustomerType}
                disabled={disabled}
                onChange={(event) => setKycCustomerType(event.target.value)}
              >
                <option value="">Select a sponsor-documented value</option>
                {classification.kyc_customer_type.allowed_values.map((value) => (
                  <option key={value} value={value}>{value}</option>
                ))}
              </select>
            </label>
            <label style={{ flex: 1 }}>
              Client segment
              <select
                aria-label="Client segment"
                required={classification.client_segment.required}
                value={clientSegment}
                disabled={disabled}
                onChange={(event) => setClientSegment(event.target.value)}
              >
                <option value="">Select a sponsor-documented value</option>
                {classification.client_segment.allowed_values.map((value) => (
                  <option key={value} value={value}>{value}</option>
                ))}
              </select>
            </label>
          </div>
          <button
            type="submit"
            className="btn btn-primary"
            style={{ marginTop: 12 }}
            disabled={disabled || !kycCustomerType || !clientSegment}
          >
            Save target classification
          </button>
        </form>
      ) : (
        <div aria-label="Retained GoldTier target classification">
          <div className="kv-row">
            <span className="kv-label">KYC customer type</span>
            <span className="kv-value">
              {classification.kyc_customer_type.selected_value ?? "Unresolved"}
              {` · ${authorityLabel(classification.kyc_customer_type.authority)}`}
            </span>
          </div>
          <div className="kv-row">
            <span className="kv-label">Client segment</span>
            <span className="kv-value">
              {classification.client_segment.selected_value ?? "Unresolved"}
              {` · ${authorityLabel(classification.client_segment.authority)}`}
            </span>
          </div>
          {unresolved && (
            <p className="control-help">This case cannot accept a target-classification change.</p>
          )}
        </div>
      )}
    </section>
  );
}
