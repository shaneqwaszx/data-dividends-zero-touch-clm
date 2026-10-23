import { useState, type FormEvent } from "react";

import { displayTimestamp, formatTimestamp } from "../shared";
import type { GoldTierTargetClassification, GoldTierTargetClassificationField } from "../types";

interface TargetClassificationInput {
  kyc_customer_type: string;
  client_segment: string;
  expected_classification_evidence_fingerprint?: string | null;
}

function authorityLabel(authority: string | null): string {
  return authority ? authority.replaceAll("_", " ") : "Not recorded";
}

function selectionSourceLabel(field: GoldTierTargetClassificationField): string {
  if (field.selection?.source === "DOCUMENT") return "Automatically classified from document";
  if (field.selection?.source === "USER") return "Selected by user";
  return field.selected_value ? "Retained selection; source not recorded" : "User selection required";
}

export default function TargetClassificationPanel({
  classification,
  disabled,
  onSubmit,
  reviewRequested = false,
  presentation = "full",
}: {
  classification: GoldTierTargetClassification;
  disabled: boolean;
  onSubmit: (input: TargetClassificationInput) => Promise<void>;
  reviewRequested?: boolean;
  presentation?: "full" | "main";
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

      {/* Main view shows the dropdowns only; trusted values and source live in More details, */}
      {/* except that conflicting evidence stays visible while the reviewer must choose between it. */}
      {presentation !== "full" && classification.evidence_state === "CONFLICT" && classification.current === false
        && <ClassificationEvidenceValues classification={classification} />}
      {presentation === "full" && <>
        <ClassificationEvidenceValues classification={classification} />
        <div aria-label="Classification source">
          {[classification.kyc_customer_type, classification.client_segment].map((field, index) => (
            <div key={index}>
              <p><strong>{index === 0 ? "KYC customer type" : "Client segment"}:</strong> {field.selected_value ?? "Unresolved"} · {selectionSourceLabel(field)}</p>
              {field.selection && <details><summary>Selection evidence and technical authority</summary>
                <ClassificationSelectionAuthority field={field} />
              </details>}
            </div>
          ))}
        </div>
      </>}
      {canEdit ? (
        <form className="classification-form" onSubmit={submit}>
          {!unresolved && (
            <p className="control-help">
              Review the unresolved evidence before selecting a fallback value.
            </p>
          )}
          <div className="classification-form__fields">
            <label className="classification-form__field">
              <span>KYC customer type</span>
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
              <small className="classification-form__hint">{selectionSourceLabel(classification.kyc_customer_type)}</small>
            </label>
            <label className="classification-form__field">
              <span>Client segment</span>
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
              <small className="classification-form__hint">{selectionSourceLabel(classification.client_segment)}</small>
            </label>
          </div>
          <div className="classification-form__actions">
            <button
              type="submit"
              className="btn btn-primary"
              disabled={disabled || !effectiveKyc || !effectiveSegment}
            >
              Save target classification
            </button>
          </div>
          <SavedClassificationTable classification={classification} />
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

/** Read-only classification context; editable state stays in the Main panel. */
export function TargetClassificationDetails({ classification, presentation }: {
  classification: GoldTierTargetClassification; presentation: "more" | "technical";
}) {
  return <section className="classification-support-panel">
    <h4>{presentation === "more" ? "Supporting classification evidence" : "Classification authority metadata"}</h4>
    {presentation === "more" ? <>
      <p>Trusted document classification and retained user choices remain distinct. GoldTier KYC and four-eye approval remain separate.</p>
      <ClassificationEvidenceValues classification={classification} />
      {[classification.kyc_customer_type, classification.client_segment].map((field, index) => <p key={index}>{index === 0 ? "KYC customer type" : "Client segment"}: {field.selected_value ?? "Unresolved"} · {field.selection?.source ?? "Source not recorded"}</p>)}
    </> : <>
      <p>Evidence fingerprint: {classification.evidence_fingerprint ?? "Not recorded"}</p>
      <p>Vocabulary: {classification.vocabulary_version} · Currentness: {classification.current == null ? "Not recorded" : String(classification.current)} · Evidence state: {classification.evidence_state ?? "Not recorded"}</p>
      {[classification.kyc_customer_type, classification.client_segment].map((field, index) => <section key={index}>
        <h5>{index === 0 ? "KYC customer type" : "Client segment"}</h5>
        <p>Source {field.selection?.source ?? "Not recorded"} · Authority {authorityLabel(field.authority)}</p>
        <ClassificationSelectionAuthority field={field} />
      </section>)}
    </>}
  </section>;
}

/** Read-only view of the values the backend has retained for this case. */
function SavedClassificationTable({ classification }: { classification: GoldTierTargetClassification }) {
  const rows = ([["KYC customer type", classification.kyc_customer_type], ["Client segment", classification.client_segment]] as const)
    .filter(([, field]) => field.selected_value !== null);
  if (rows.length === 0) return null;
  return (
    <div className="table-card classification-saved">
      <table className="table" aria-label="Saved target classification">
        <thead><tr><th>Field</th><th>Saved value</th><th>Source</th><th>Saved at</th></tr></thead>
        <tbody>
          {rows.map(([label, field]) => (
            <tr key={label}>
              <td>{label}</td>
              <td>{field.selected_value}</td>
              <td>{field.selection?.source === "USER" ? "Selected by user" : field.selection?.source === "DOCUMENT" ? "From document" : "Not recorded"}</td>
              <td>{field.selection?.classified_at ? formatTimestamp(field.selection.classified_at) : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ClassificationEvidenceValues({ classification }: { classification: GoldTierTargetClassification }) {
  return <>
      {classification.evidence_values && (
        <div aria-label="Current trusted classification values">
          <p>Current trusted KYC customer types: {classification.evidence_values.kyc_customer_type?.join("; ") || "None"}</p>
          <p>Current trusted client segments: {classification.evidence_values.client_segment?.join("; ") || "None"}</p>
        </div>
      )}

  </>;
}

function ClassificationSelectionAuthority({ field }: { field: GoldTierTargetClassificationField }) {
  if (!field.selection) return null;
  return <>
              <p>Policy version {field.selection.policy_version} · Vocabulary {field.selection.vocabulary_version} · {authorityLabel(field.authority)}</p>
              <p>Classified at {displayTimestamp(field.selection.classified_at)}</p>
              {field.selection.document_evidence && <p>Document {field.selection.document_evidence.document_id} · version {field.selection.document_evidence.document_version}
                {" · event "}{field.selection.document_evidence.document_event_count}{" · page "}{field.selection.document_evidence.page_number}
                {" · "}{field.selection.document_evidence.source_reference}{" · "}{field.selection.document_evidence.extraction_method}
                {" · "}{field.selection.document_evidence.extraction_quality}{" · score "}{field.selection.document_evidence.evidence_score}
                {" · extracted value: "}{field.selection.document_evidence.extracted_exact_value}</p>}
  </>;
}
