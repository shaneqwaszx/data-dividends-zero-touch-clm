import { useEffect, useRef, useState, type ChangeEvent, type KeyboardEvent } from "react";

import type {
  DocumentFieldKey,
  DocumentProcessingRecord,
  ReviewDecision,
  ZeroTouchCaseSummary,
} from "../types";

const ACCEPTED_DOCUMENTS = "application/pdf,.pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,.docx,text/plain,.txt";

type DocumentField = DocumentProcessingRecord["fields"][number];

export interface DocumentReviewRequest {
  fieldKey: DocumentFieldKey;
  decision: ReviewDecision;
  correctedValue?: string;
  note?: string;
}

export function isCurrentDocument(document: DocumentProcessingRecord): boolean {
  return document.superseded_by_document_id == null;
}

export function isDocumentReuploadRequired(document: DocumentProcessingRecord): boolean {
  return isCurrentDocument(document)
    && document.state === "FAILED"
    && document.error?.code === "DOCUMENT_REUPLOAD_REQUIRED";
}

export function exactSavedReviewRequest(field: DocumentField): DocumentReviewRequest | null {
  if (field.review_status === "PENDING") return null;
  if (field.review_status === "CORRECTED") {
    if (!field.reviewed_value?.trim()) return null;
    return {
      fieldKey: field.field_key,
      decision: "CORRECTED",
      correctedValue: field.reviewed_value,
      ...(field.review_note !== null ? { note: field.review_note } : {}),
    };
  }
  return {
    fieldKey: field.field_key,
    decision: field.review_status,
    ...(field.review_note !== null ? { note: field.review_note } : {}),
  };
}

export function canRetrySavedReviewCheckpoint(
  summary: ZeroTouchCaseSummary,
  document: DocumentProcessingRecord,
): boolean {
  return isCurrentDocument(document)
    && document.state === "REVIEWED"
    && document.fields.length > 0
    && document.fields.every((field) => exactSavedReviewRequest(field) !== null)
    && summary.status === "WAITING_FOR_REVIEW"
    && summary.current_stage === "DOCUMENT";
}

export function canContinueRecoveredIntake(
  summary: ZeroTouchCaseSummary,
  documents: DocumentProcessingRecord[],
): boolean {
  if (summary.status !== "PENDING_INPUTS" || summary.current_stage !== "DOCUMENT") return false;
  if (documents.some((document) => isCurrentDocument(document) && document.state === "FAILED")) return false;
  const latestEvent = summary.timeline.at(-1);
  if (latestEvent?.event_type !== "DOCUMENT_REUPLOAD_REQUIRED") return false;
  const byId = new Map(documents.map((document) => [document.document_id, document]));
  return documents.some((current) => {
    if (!isCurrentDocument(current) || current.state === "FAILED" || !current.supersedes_document_id) return false;
    const failed = byId.get(current.supersedes_document_id);
    return failed !== undefined
      && failed.error?.code === "DOCUMENT_REUPLOAD_REQUIRED"
      && failed.superseded_by_document_id === current.document_id;
  });
}

function fieldLabel(fieldKey: DocumentFieldKey): string {
  return fieldKey.replaceAll("_", " ");
}

function evidenceValue(value: string | null): string {
  return value ?? "Not available";
}

function correctionStillRequiresReplacement(field: DocumentField, summary: ZeroTouchCaseSummary): boolean {
  if (field.review_status !== "CORRECTED") return false;
  if (field.original_extracted_value === null) return true;
  const threshold = Number(summary.case.policy_snapshot?.idp_review_confidence_threshold);
  return Number.isFinite(threshold) && field.confidence < threshold;
}

function DocumentCard({
  document,
  summary,
  historical,
  busy,
  mutationBlocked,
  onReview,
  onReplace,
  onRetry,
}: {
  document: DocumentProcessingRecord;
  summary: ZeroTouchCaseSummary;
  historical: boolean;
  busy: boolean;
  mutationBlocked: boolean;
  onReview: (document: DocumentProcessingRecord, request: DocumentReviewRequest, repair: boolean) => void;
  onReplace: (document: DocumentProcessingRecord, file: File) => void;
  onRetry: (document: DocumentProcessingRecord, file: File) => void;
}) {
  const [editingField, setEditingField] = useState<DocumentFieldKey | null>(null);
  const [correctedValue, setCorrectedValue] = useState("");
  const [note, setNote] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);
  const correctionInput = useRef<HTMLInputElement>(null);
  const correctionTrigger = useRef<HTMLButtonElement | null>(null);
  const pendingCount = document.fields.filter((field) => field.review_status === "PENDING").length;
  const finalCount = document.fields.length - pendingCount;
  const controlsDisabled = busy || mutationBlocked;

  useEffect(() => {
    if (editingField) correctionInput.current?.focus();
  }, [editingField]);

  function closeCorrection() {
    setEditingField(null);
    setCorrectedValue("");
    setNote("");
    setValidationError(null);
    queueMicrotask(() => correctionTrigger.current?.focus());
  }

  function submitCorrection(field: DocumentField) {
    const normalized = correctedValue.trim();
    if (!normalized) {
      setValidationError("Enter a correction before saving.");
      return;
    }
    if (normalized.length > 512) {
      setValidationError("Correction must be 512 characters or fewer.");
      return;
    }
    if (note.length > 240) {
      setValidationError("Note must be 240 characters or fewer.");
      return;
    }
    onReview(document, {
      fieldKey: field.field_key,
      decision: "CORRECTED",
      correctedValue: normalized,
      ...(note ? { note } : {}),
    }, false);
  }

  function handleFile(event: ChangeEvent<HTMLInputElement>, retry: boolean) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || controlsDisabled) return;
    if (retry) onRetry(document, file);
    else onReplace(document, file);
  }

  return (
    <article className={`document-card${historical ? " document-card--history" : ""}`} aria-busy={busy}>
      <header className="document-card__header">
        <div>
          <p className="card-kicker">{historical ? "Historical evidence" : "Current evidence"}</p>
          <h5>{document.display_name}</h5>
        </div>
        <span className="tag tag-neutral">{(document.semantic_completion ?? document.state).replaceAll("_", " ")}</span>
      </header>
      <p className="control-help">
        {document.provider_environment ?? "Provider unavailable"} · {finalCount} {document.semantic_completion ? "source field reviews final" : "final"} / {document.fields.length} fields
        {document.supersedes_document_id ? ` · replaces ${document.supersedes_document_id}` : ""}
        {document.superseded_by_document_id ? ` · replaced by ${document.superseded_by_document_id}` : ""}
      </p>
      {document.semantic_completion && <p className="control-help">Document checkpoint completed by the retained operator reconciliation decisions. Original extraction and field review evidence is preserved.</p>}
      {!historical && !document.semantic_completion && pendingCount > 0 && (
        <div className="ds-banner">
          {pendingCount} field{pendingCount === 1 ? " remains" : "s remain"} for review. Independent readiness blockers remain authoritative until the refreshed case clears them.
        </div>
      )}
      {document.error && <div className="ds-banner ds-banner-warn"><strong>{document.error.code}</strong><span>{document.error.message}</span></div>}

      <div className="document-fields">
        {document.fields.map((field) => {
          const label = fieldLabel(field.field_key);
          const autoConfirmed = document.events.some((event) => event.code === "DOCUMENT_FIELD_AUTO_CONFIRMED" && event.field_key === field.field_key)
            && !document.events.some((event) => event.field_key === field.field_key && ["DOCUMENT_FIELD_ACCEPTED", "DOCUMENT_FIELD_REJECTED", "DOCUMENT_FIELD_CORRECTED"].includes(event.event_type));
          const isPending = field.review_status === "PENDING";
          const canDecide = !document.semantic_completion && !historical && isCurrentDocument(document) && document.state === "REVIEW_REQUIRED" && isPending;
          const savedRequest = exactSavedReviewRequest(field);
          const canRepair = !document.semantic_completion && !autoConfirmed && !historical && savedRequest !== null && canRetrySavedReviewCheckpoint(summary, document);
          return (
            <section className="document-field" key={field.field_key} aria-labelledby={`${document.document_id}-${field.field_key}`}>
              <div className="document-field__heading">
                <h6 id={`${document.document_id}-${field.field_key}`}>{label}</h6>
                <span className="tag tag-neutral">{document.semantic_completion && isPending ? "OPERATOR RESOLVED" : autoConfirmed ? "AUTO CONFIRMED" : field.review_status.replaceAll("_", " ")}</span>
              </div>
              <dl className="document-field__evidence">
                <div><dt>Suggestion</dt><dd>{evidenceValue(field.original_extracted_value)}</dd></div>
                <div><dt>Canonical</dt><dd>{evidenceValue(field.canonical_value)}</dd></div>
                <div><dt>Comparison</dt><dd>{field.comparison_status.replaceAll("_", " ")}</dd></div>
                <div><dt>Confidence</dt><dd>{Math.round(field.confidence * 100)}%</dd></div>
                <div><dt>Provenance</dt><dd>{field.provenance.provider} {field.provenance.environment} · {field.provenance.source_reference}</dd></div>
                {!isPending && <div><dt>Final value</dt><dd>{field.review_status === "CORRECTED" ? evidenceValue(field.reviewed_value) : field.review_status}</dd></div>}
                {field.review_note && <div><dt>Review note</dt><dd>{field.review_note}</dd></div>}
              </dl>
              {correctionStillRequiresReplacement(field, summary) && (
                <p className="ds-banner ds-banner-warn">Correction retained, but replacement evidence is still required because the original suggestion was missing or below the case-bound confidence threshold.</p>
              )}
              {canDecide && (
                <div className="document-field__actions">
                  {field.original_extracted_value !== null && <button type="button" className="btn btn-primary" disabled={controlsDisabled} onClick={() => onReview(document, { fieldKey: field.field_key, decision: "ACCEPTED" }, false)}>Accept {label} suggestion</button>}
                  <button type="button" className="btn btn-secondary" disabled={controlsDisabled} onClick={() => onReview(document, { fieldKey: field.field_key, decision: "REJECTED" }, false)}>Reject {label} suggestion</button>
                  <button type="button" className="btn btn-secondary" disabled={controlsDisabled} ref={(element) => { if (editingField === field.field_key) correctionTrigger.current = element; }} onClick={(event) => { correctionTrigger.current = event.currentTarget; setEditingField(field.field_key); setCorrectedValue(field.reviewed_value ?? field.original_extracted_value ?? ""); setNote(field.review_note ?? ""); setValidationError(null); }}>Record {label} correction</button>
                </div>
              )}
              {editingField === field.field_key && canDecide && (
                <fieldset className="document-correction" onKeyDown={(event: KeyboardEvent<HTMLFieldSetElement>) => { if (event.key === "Escape") closeCorrection(); }}>
                  <legend>Correct {label}</legend>
                  <label>Correction<input ref={correctionInput} className="input" value={correctedValue} maxLength={512} onChange={(event) => setCorrectedValue(event.target.value)} /></label>
                  <label>Note — optional<textarea className="input" value={note} maxLength={240} onChange={(event) => setNote(event.target.value)} /></label>
                  {validationError && <p className="field-error" role="alert">{validationError}</p>}
                  <div className="document-field__actions"><button type="button" className="btn btn-primary" disabled={controlsDisabled} onClick={() => submitCorrection(field)}>Save {label} correction</button><button type="button" className="btn btn-ghost" onClick={closeCorrection}>Cancel</button></div>
                </fieldset>
              )}
              {canRepair && (
                <div className="document-checkpoint-repair">
                  <p className="control-help">This final decision is read-only. Repeating the exact saved request can repair an interrupted review checkpoint; it cannot change the decision.</p>
                  <button type="button" className="btn btn-secondary" disabled={controlsDisabled} onClick={() => onReview(document, savedRequest, true)}>Retry saved {label} review checkpoint</button>
                </div>
              )}
              {!historical && !isPending && !canRepair && <p className="control-help">Final decision is read-only.</p>}
            </section>
          );
        })}
      </div>

      {!historical && isCurrentDocument(document) && (
        <div className="document-card__actions">
          {isDocumentReuploadRequired(document) ? (
            <label className={`btn btn-primary document-upload-control${controlsDisabled ? " is-disabled" : ""}`}>
              Retry affected document
              <input className="sr-only document-upload-input" type="file" accept={ACCEPTED_DOCUMENTS} disabled={controlsDisabled} onChange={(event) => handleFile(event, true)} />
            </label>
          ) : document.state !== "FAILED" ? (
            <label className={`btn btn-ghost document-upload-control${controlsDisabled ? " is-disabled" : ""}`}>
              Replace current document
              <input className="sr-only document-upload-input" type="file" accept={ACCEPTED_DOCUMENTS} disabled={controlsDisabled} onChange={(event) => handleFile(event, false)} />
            </label>
          ) : null}
        </div>
      )}
    </article>
  );
}

export default function DocumentEvidencePanel({
  summary,
  documents,
  busy,
  busyLabel,
  mutationBlocked,
  onReview,
  onReplace,
  onRetry,
  onContinue,
  onRefresh,
}: {
  summary: ZeroTouchCaseSummary;
  documents: DocumentProcessingRecord[];
  busy: boolean;
  busyLabel: string | null;
  mutationBlocked: boolean;
  onReview: (document: DocumentProcessingRecord, request: DocumentReviewRequest, repair: boolean) => void;
  onReplace: (document: DocumentProcessingRecord, file: File) => void;
  onRetry: (document: DocumentProcessingRecord, file: File) => void;
  onContinue: () => void;
  onRefresh: () => void;
}) {
  const current = documents.filter(isCurrentDocument);
  const history = documents.filter((document) => !isCurrentDocument(document));
  const canContinue = canContinueRecoveredIntake(summary, documents);

  return (
    <section className="evidence-section-block document-evidence-panel" aria-labelledby="documents-heading" aria-busy={busy}>
      <div className="document-evidence-panel__title"><div><p className="card-kicker">Local/Mock evidence · not approval</p><h4 id="documents-heading">Document evidence and review</h4></div>{busyLabel && <span role="status">{busyLabel}</span>}</div>
      {mutationBlocked && <div className="ds-banner ds-banner-warn"><strong>Evidence reload could not be confirmed.</strong><span>Last-confirmed information remains visible. Refresh before attempting another case mutation.</span><button type="button" className="btn btn-secondary" disabled={busy} onClick={onRefresh}>Refresh case evidence</button></div>}
      {current.length === 0 && <p className="text-muted">No current document evidence is available.</p>}
      {current.map((document) => <DocumentCard key={document.document_id} document={document} summary={summary} historical={false} busy={busy} mutationBlocked={mutationBlocked} onReview={onReview} onReplace={onReplace} onRetry={onRetry} />)}
      {canContinue && <div className="ds-banner"><strong>Recovered intake is ready to be re-evaluated.</strong><span>The replacement lineage is current and the case remains at the document intake checkpoint.</span><button type="button" className="btn btn-primary" disabled={busy || mutationBlocked} onClick={onContinue}>Continue recovered intake</button></div>}
      {history.length > 0 && <details className="evidence-history"><summary>Evidence history ({history.length})</summary>{history.map((document) => <DocumentCard key={document.document_id} document={document} summary={summary} historical busy={busy} mutationBlocked={mutationBlocked} onReview={onReview} onReplace={onReplace} onRetry={onRetry} />)}</details>}
    </section>
  );
}
