import { forwardRef, useImperativeHandle, useState } from "react";
import type { DocumentProcessingRecord, ReviewDecisionBatch, ReconciliationDecisionAction, ReviewDecision, ZeroTouchCaseSummary } from "../types";

export interface ReviewDraftHandle {
  selectSourceDecision: (id: string, action: ReconciliationDecisionAction) => boolean;
}
interface Draft { decision: string; correction: string; note: string }

const BlockerDecisionReview = forwardRef<ReviewDraftHandle, {
  summary: ZeroTouchCaseSummary;
  documents: DocumentProcessingRecord[];
  busy: boolean;
  onConfirm: (batch: ReviewDecisionBatch) => void;
}>(function BlockerDecisionReview({ summary, documents, busy, onConfirm }, ref) {
  const activeIds = new Set(summary.active_exceptions.map(item => item.exception_id));
  const currentDocuments = documents.filter(doc => doc.superseded_by_document_id == null);
  const reconciliation = summary.reconciliation;
  const currentSources = reconciliation?.source_document_ids?.length === currentDocuments.length
    && reconciliation?.source_document_ids?.every((id, index) => currentDocuments.some(doc => doc.document_id === id
      && doc.events.length === reconciliation.source_document_event_counts[index]));
  const sources = currentSources ? reconciliation?.discrepancies.filter(item => item.status === "OPEN"
    && item.allowed_actions.length > 0 && activeIds.has(item.discrepancy_id)) ?? []
    : [];
  const reviewable = documents.filter(doc => doc.superseded_by_document_id == null
    && doc.state === "REVIEW_REQUIRED" && !doc.semantic_completion && doc.review_source_fingerprint);
  const fields = reviewable.flatMap(doc => doc.fields.filter(field => field.review_status === "PENDING")
    .map(field => ({ doc, field, id: `${doc.document_id}:${field.field_key}` })));
  const [family, setFamily] = useState<"document" | "source">(fields.length ? "document" : "source");
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const [saved, setSaved] = useState(false);
  const disabled = busy || summary.evidence_decision_authorized !== true;
  const items = family === "document" ? fields.map(item => item.id) : sources.map(item => item.discrepancy_id);
  const selected = items.filter(id => drafts[id]?.decision).length;
  const invalid = family === "document" && fields.some(({ id }) => drafts[id]?.decision === "CORRECTED" && !drafts[id].correction.trim());
  const complete = selected === items.length && items.length > 0 && !invalid;

  function change(id: string, update: Partial<Draft>) {
    setDrafts(current => ({ ...current, [id]: { ...(current[id] ?? { decision: "", correction: "", note: "" }), ...update } }));
    setSaved(false);
  }
  useImperativeHandle(ref, () => ({
    selectSourceDecision(id, action) {
      if (disabled || !sources.some(item => item.discrepancy_id === id && item.allowed_actions.includes(action))) return false;
      setFamily("source");
      change(id, { decision: action });
      return true;
    },
  }));
  if (!fields.length && !sources.length) return null;

  function confirm() {
    if (disabled || !complete) return;
    const base = { expected_automation_version: summary.version, expected_case_event_count: summary.case.events.length };
    if (family === "source") {
      onConfirm({ ...base, expected_reconciliation_version: summary.reconciliation!.version,
        reconciliation: sources.map(item => ({ discrepancy_id: item.discrepancy_id,
          action: drafts[item.discrepancy_id].decision as ReconciliationDecisionAction,
          evidence_fingerprint: item.evidence_fingerprint })) });
    } else {
      onConfirm({ ...base, documents: reviewable.filter(doc => fields.some(item => item.doc.document_id === doc.document_id)).map(doc => ({
        document_id: doc.document_id, expected_event_count: doc.events.length, source_fingerprint: doc.review_source_fingerprint!,
        decisions: fields.filter(item => item.doc.document_id === doc.document_id).map(({ id, field }) => ({
          field_key: field.field_key, decision: drafts[id].decision as ReviewDecision,
          ...(drafts[id].decision === "CORRECTED" ? { corrected_value: drafts[id].correction.trim() } : {}),
          ...(drafts[id].note.trim() ? { note: drafts[id].note.trim() } : {}),
        })),
      })) });
    }
  }
  return <section id="case-blocker-review" className="blocker-review card" aria-labelledby="blocker-review-heading">
    <h3 id="blocker-review-heading">Review blocker decisions</h3>
    <p>Select all choices, review them, then confirm. Selecting a choice does not process the case.</p>
    {fields.length > 0 && sources.length > 0 && <label>Decision group
      <select aria-label="Decision group" value={family} disabled={disabled} onChange={event => { setFamily(event.target.value as typeof family); setSaved(false); }}>
        <option value="source">Compare registry and document values</option>
        <option value="document">Review extracted document fields</option>
      </select>
    </label>}
    {family === "document" ? fields.map(({ doc, field, id }) => <fieldset key={id} className="comparison-card">
      <legend>{field.field_key.replaceAll("_", " ")} · {doc.display_name}</legend>
      <div className="comparison-sources"><div>Document suggestion<strong>{field.original_extracted_value ?? "Missing"}</strong></div><div>Registry value<strong>{field.canonical_value ?? "Missing"}</strong></div></div>
      <label>Decision for {field.field_key.replaceAll("_", " ")}
        <select data-review-field={field.field_key} data-document-id={doc.document_id} disabled={disabled}
          value={drafts[id]?.decision ?? ""} onChange={event => change(id, { decision: event.target.value })}>
          <option value="">Select a draft decision</option>
          {field.original_extracted_value !== null && <option value="ACCEPTED">Accept document suggestion</option>}
          <option value="REJECTED">Reject document suggestion</option><option value="CORRECTED">Record correction</option>
        </select>
      </label>
      {drafts[id]?.decision === "CORRECTED" && <label>Correction for {field.field_key.replaceAll("_", " ")}
        <input maxLength={512} value={drafts[id].correction} disabled={disabled} onChange={event => change(id, { correction: event.target.value })} />
      </label>}
      <label>Optional note for {field.field_key.replaceAll("_", " ")}
        <input maxLength={240} value={drafts[id]?.note ?? ""} disabled={disabled} onChange={event => change(id, { note: event.target.value })} />
      </label>
      {(field.original_extracted_value === null || field.confidence < Number(summary.case.policy_snapshot?.idp_review_confidence_threshold))
        && <p className="control-help">A review decision does not replace missing or low-confidence evidence. Replacement may still be required.</p>}
      {drafts[id]?.decision && <p className="control-help">Draft: {drafts[id].decision.toLowerCase()}{drafts[id].decision === "CORRECTED" ? ` · ${drafts[id].correction || "Correction needed"}` : ""}</p>}
    </fieldset>) : sources.map(item => <fieldset key={item.discrepancy_id} className="comparison-card">
      <legend>{item.field_name.replaceAll("_", " ")}</legend>
      <div className="comparison-sources">{["REGISTRY", "DOCUMENT_IDP"].map(kind => <div key={kind}>
        {kind === "REGISTRY" ? "Registry value" : "Document value"}<strong>{item.observations.filter(obs => obs.source_kind === kind).map(obs => obs.normalized_value ?? "Missing").join(" · ") || "Missing"}</strong>
      </div>)}</div>
      <label>Source decision for {item.field_name.replaceAll("_", " ")}
        <select data-reconciliation-field={item.field_name} data-discrepancy-id={item.discrepancy_id} disabled={disabled}
          value={drafts[item.discrepancy_id]?.decision ?? ""} onChange={event => change(item.discrepancy_id, { decision: event.target.value })}>
          <option value="">Select a draft source decision</option>
          {item.allowed_actions.map(action => <option key={action} value={action}>{action === "KEEP_REGISTRY_VALUE" ? "Keep registry value" : "Use document value"}</option>)}
        </select>
      </label>
      {drafts[item.discrepancy_id]?.decision && <p className="control-help">Draft: {drafts[item.discrepancy_id].decision.replaceAll("_", " ").toLowerCase()}</p>}
    </fieldset>)}
    <footer className="blocker-review__footer">
      <p role="status">{selected} selected / {items.length} required · {items.length - selected} remaining · {saved ? "Draft saved in this tab" : "Draft not saved"}</p>
      <p>Your selections are a draft. The onboarding system has not processed them yet. Drafts stay in this tab while this case is open and are cleared when you leave the case, refresh, change session or receive changed evidence.</p>
      <p>Confirming applies these decisions and continues the onboarding workflow. GoldTier Review & Send is a separate confirmation.</p>
      {!complete && <p id="batch-confirm-disabled">{invalid ? "Enter each correction before confirming." : "Select all required decisions before confirming."}</p>}
      <div className="document-card__actions">
        <button type="button" className="btn btn-secondary" disabled={disabled || selected === 0} onClick={() => setSaved(true)}>Save draft in this tab</button>
        <button type="button" className="btn btn-ghost" disabled={disabled || selected === 0} onClick={() => { setDrafts({}); setSaved(false); }}>Clear draft</button>
        <button type="button" className="btn btn-primary blocker-review-confirm" disabled={disabled || !complete} aria-describedby={!complete ? "batch-confirm-disabled" : undefined} onClick={confirm}>Confirm decisions & continue onboarding</button>
      </div>
    </footer>
  </section>;
});
export default BlockerDecisionReview;
