import { useState, type FormEvent } from "react";

import type { GoldTierTargetClassification } from "../types";

interface TargetClassificationInput {
  kyc_customer_type: string;
  client_segment: string;
  expected_classification_evidence_fingerprint?: string | null;
}

function authorityLabel(authority: string | null): string {
  return authority ? authority.replaceAll("_", " ") : "Not recorded";
}

export default function TargetClassificationPanel({
  classification,
  disabled,
  onSubmit,
  reviewRequested = false,
}: {
  classification: GoldTierTargetClassification;
  disabled: boolean;
  onSubmit: (input: TargetClassificationInput) => Promise<void>;
  reviewRequested?: boolean;
}) {
  const [kycCustomerType, setKycCustomerType] = useState(
    classification.kyc_customer_type.selected_value ?? "",
  );
  const [clientSegment, setClientSegment] = useState(
    classification.client_segment.selected_value ?? "",
  );
  const unresolved = classification.kyc_customer_type.selected_value === null
    || classification.client_segment.selected_value === null;
  const automaticKyc = !reviewRequested && classification.current !== false && classification.kyc_customer_type.selection?.source === "DOCUMENT";
  const automaticSegment = !reviewRequested && classification.current !== false && classification.client_segment.selection?.source === "DOCUMENT";
  const canEdit = classification.editable && !(automaticKyc && automaticSegment);
  const effectiveKyc = automaticKyc ? classification.kyc_customer_type.selected_value ?? "" : kycCustomerType;
  const effectiveSegment = automaticSegment ? classification.client_segment.selected_value ?? "" : clientSegment;
  const prominentTypes = ["Company - Private", "Partnership - Unregulated", "Government"];
  const kycOptions = [...prominentTypes.filter((value) => classification.kyc_customer_type.allowed_values.includes(value)),
    ...classification.kyc_customer_type.allowed_values.filter((value) => !prominentTypes.includes(value))];

  function submit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    if (!effectiveKyc || !effectiveSegment || disabled) return;
    void onSubmit({
      kyc_customer_type: effectiveKyc,
      client_segment: effectiveSegment,
      ...(classification.evidence_fingerprint
        ? { expected_classification_evidence_fingerprint: classification.evidence_fingerprint } : {}),
    });
  }

  return (
    <section className="card" aria-labelledby="goldtier-target-classification-heading" style={{ marginBottom: 16 }}>
      <p className="section-label">GoldTier target input</p>
      <h3 id="goldtier-target-classification-heading">{classification.evidence_state === "CONFLICT" && classification.current === false
        ? "Target classification — conflicting evidence" : "Target classification"}</h3>
      {classification.evidence_state === "CONFLICT" && classification.current === false && (
        <p role="status">Current trusted documents contain different target-classification values. Review the
          evidence and select the value to use for this case.</p>
      )}
      {classification.current === false && classification.evidence_state !== "CONFLICT" && (
        <p role="status">Classification evidence changed. Review the current evidence and select the values to use.</p>
      )}
      {classification.evidence_state === "CONFLICT" && classification.current === true && (
        <p role="status">The current conflicting evidence has an explicit classification review for this case.</p>
      )}
      <p className="control-help">
        Current trusted document labels are classified automatically. User selection is required
        only when evidence is missing, uncertain or conflicting. These values prepare the
        submission; GoldTier KYC and four-eye approval remain separate.
      </p>
      {reviewRequested && <p className="control-help">Review the current values explicitly. The backend checks the selected vocabulary and current document evidence again before preparing a new submission.</p>}

      {classification.evidence_values && (
        <div aria-label="Current trusted classification values">
          <p>Current trusted KYC customer types: {classification.evidence_values.kyc_customer_type?.join("; ") || "None"}</p>
          <p>Current trusted client segments: {classification.evidence_values.client_segment?.join("; ") || "None"}</p>
        </div>
      )}
      <div aria-label="Classification source">
        {[classification.kyc_customer_type, classification.client_segment].map((field, index) => (
          <div key={index}>
            <p><strong>{index === 0 ? "KYC customer type" : "Client segment"}:</strong> {field.selected_value ?? "Unresolved"}
              {field.selection?.source === "DOCUMENT" ? " · Automatically classified from document" : field.selection?.source === "USER" ? " · Selected by user" : field.selected_value ? " · Retained selection; source not recorded" : " · User selection required"}</p>
            {field.selection && <details><summary>Selection evidence and technical authority</summary>
              <p>Policy version {field.selection.policy_version} · Vocabulary {field.selection.vocabulary_version} · {authorityLabel(field.authority)}</p>
              <p>Classified at {field.selection.classified_at}</p>
              {field.selection.document_evidence && <p>Document {field.selection.document_evidence.document_id} · version {field.selection.document_evidence.document_version}
                {" · event "}{field.selection.document_evidence.document_event_count}{" · page "}{field.selection.document_evidence.page_number}
                {" · "}{field.selection.document_evidence.source_reference}{" · "}{field.selection.document_evidence.extraction_method}
                {" · "}{field.selection.document_evidence.extraction_quality}{" · score "}{field.selection.document_evidence.evidence_score}
                {" · extracted value: "}{field.selection.document_evidence.extracted_exact_value}</p>}
            </details>}
          </div>
        ))}
      </div>
      {canEdit ? (
        <form onSubmit={submit}>
          {!unresolved && (
            <p className="control-help">
              Review the unresolved evidence before selecting a fallback value.
            </p>
          )}
          <div className="ds-two-col">
            <label style={{ flex: 1 }}>
              KYC customer type
              <select
                aria-label="KYC customer type"
                required={classification.kyc_customer_type.required}
                value={effectiveKyc}
                disabled={disabled || automaticKyc}
                onChange={(event) => setKycCustomerType(event.target.value)}
              >
                <option value="">Select a sponsor-documented value</option>
                {kycOptions.map((value) => (
                  <option key={value} value={value}>{value}</option>
                ))}
              </select>
            </label>
            <label style={{ flex: 1 }}>
              Client segment
              <select
                aria-label="Client segment"
                required={classification.client_segment.required}
                value={effectiveSegment}
                disabled={disabled || automaticSegment}
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
            disabled={disabled || !effectiveKyc || !effectiveSegment}
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

            </span>
          </div>
          <div className="kv-row">
            <span className="kv-label">Client segment</span>
            <span className="kv-value">
              {classification.client_segment.selected_value ?? "Unresolved"}

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
