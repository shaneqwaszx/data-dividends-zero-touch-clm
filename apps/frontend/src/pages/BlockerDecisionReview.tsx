import { forwardRef, useImperativeHandle, useState } from "react";
import type { DocumentProcessingRecord, ReviewDecisionBatch, ReconciliationDecisionAction, ReviewDecision, ZeroTouchCaseSummary } from "../types";

export interface ReviewDraftHandle {
  openDecision: (destination: { discrepancyId?: string; documentId?: string; fieldKey?: string }) => boolean;
  selectSourceDecision: (id: string, action: ReconciliationDecisionAction) => boolean;
}
interface Draft { decision: string; correction: string; note: string }
interface ReviewDraftState {
  choices: Record<string, Draft>;
  bindings: Record<string, string>;
  bulkResult: { filled: number; skipped: number; remaining: number } | null;
}

// Every field and discrepancy needs an explicit reviewer choice; nothing is pre-selected.
// Submitted values stay the backend ReviewDecision / ReconciliationDecisionAction enums.
const DECISION_NAMES: Record<string, string> = {
  ACCEPTED: "Suggestion accepted", REJECTED: "Suggestion rejected", CORRECTED: "Correction recorded",
  KEEP_REGISTRY_VALUE: "Keep registry value", USE_DOCUMENT_VALUE: "Use document value",
};
const EMPTY_DRAFT: Draft = { decision: "", correction: "", note: "" };

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
  const bindings: Record<string, string> = Object.fromEntries([
    ...fields.map(({ id, doc }) => [id, JSON.stringify([doc.review_source_fingerprint, doc.events.length, doc.document_version])]),
    ...sources.map(item => [item.discrepancy_id, JSON.stringify([reconciliation?.reconciliation_id, reconciliation?.version, item.evidence_fingerprint, item.allowed_actions])]),
  ]);
  const [draftState, setDraftState] = useState<ReviewDraftState>({ choices: {}, bindings, bulkResult: null });
  const drafts = draftState.choices;
  const [saved, setSaved] = useState(false);
  // Notes are optional, so their box opens on request; a typed note keeps it open.
  const [openNotes, setOpenNotes] = useState<Set<string>>(new Set());
  // Reconcile before rendering or confirming: retire only changed/removed evidence.
  // Version expectations still come from the current backend projection in confirm().
  if (Object.keys(bindings).length !== Object.keys(draftState.bindings).length
    || Object.keys(bindings).some(id => bindings[id] !== draftState.bindings[id])) {
    setDraftState({ bindings, bulkResult: null, choices: Object.fromEntries(
      Object.entries(draftState.choices).filter(([id]) => bindings[id] !== undefined && bindings[id] === draftState.bindings[id]),
    ) });
    setSaved(false);
  }
  const disabled = busy || summary.evidence_decision_authorized !== true;
  const items = family === "document" ? fields.map(item => item.id) : sources.map(item => item.discrepancy_id);
  const selected = items.filter(id => drafts[id]?.decision).length;
  const invalid = family === "document" && fields.some(({ id }) => drafts[id]?.decision === "CORRECTED" && !drafts[id].correction.trim());
  const complete = selected === items.length && items.length > 0 && !invalid;

  function change(id: string, update: Partial<Draft>) {
    setDraftState(current => ({ ...current, choices: { ...current.choices,
      [id]: { ...(current.choices[id] ?? EMPTY_DRAFT), ...update } }, bulkResult: null }));
    setSaved(false);
  }
  // Fill only undecided eligible fields; existing choices, corrections and notes are kept.
  function fillUndecided(decision: "ACCEPTED" | "REJECTED") {
    if (disabled || family !== "document") return;
    setDraftState(current => {
      const choices = { ...current.choices };
      let filled = 0;
      let skipped = 0;
      for (const { id, field } of fields) {
        const draft = choices[id];
        if (draft?.decision || draft?.correction.trim()
          || (decision === "ACCEPTED" && field.original_extracted_value == null)) {
          skipped += 1;
        } else {
          choices[id] = { decision, correction: "", note: draft?.note ?? "" };
          filled += 1;
        }
      }
      return { choices, bindings: current.bindings, bulkResult: { filled, skipped,
        remaining: fields.filter(({ id }) => !choices[id]?.decision).length } };
    });
    setSaved(false);
  }
  useImperativeHandle(ref, () => ({
    openDecision(destination) {
      if (destination.discrepancyId && sources.some(item => item.discrepancy_id === destination.discrepancyId)) {
        setFamily("source"); return true;
      }
      if (fields.some(item => item.doc.document_id === destination.documentId && item.field.field_key === destination.fieldKey)) {
        setFamily("document"); return true;
      }
      return false;
    },
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
  const threshold = Number(summary.case.policy_snapshot?.idp_review_confidence_threshold);
  return <section id="case-blocker-review" className="blocker-review card" aria-labelledby="blocker-review-heading">
    <header className="blocker-review__header">
      <div>
        <p className="card-kicker">Document verification</p>
        <h3 id="blocker-review-heading">Review blocker decisions</h3>
        <p className="blocker-review__lede">Select all choices, review them, then confirm. Selecting a choice does not process the case.</p>
      </div>
    </header>
    {fields.length > 0 && sources.length > 0 && <label className="blocker-review__group">Decision group
      <select aria-label="Decision group" value={family} disabled={disabled} onChange={event => { setFamily(event.target.value as typeof family); setSaved(false); setDraftState(current => ({ ...current, bulkResult: null })); }}>
        <option value="source">Compare registry and document values</option>
        <option value="document">Review extracted document fields</option>
      </select>
    </label>}
    {family === "document" && <div className="blocker-review__bulk">
      <p>Fill undecided eligible document drafts only. Existing choices, corrections and notes are kept; Confirm is still required.</p>
      <div className="document-card__actions">
        <button type="button" className="btn btn-secondary" disabled={disabled} onClick={() => fillUndecided("ACCEPTED")}>Accept all eligible undecided suggestions</button>
        <button type="button" className="btn btn-secondary" disabled={disabled} onClick={() => fillUndecided("REJECTED")}>Reject all undecided suggestions</button>
      </div>
      {draftState.bulkResult && <p role="status">{draftState.bulkResult.filled} filled · {draftState.bulkResult.skipped} skipped · {draftState.bulkResult.remaining} remaining</p>}
    </div>}
    <div className="blocker-review__cards">
    {family === "document" ? fields.map(({ doc, field, id }) => {
      const label = field.field_key.replaceAll("_", " ");
      const decision = drafts[id]?.decision ?? "";
      const correction = drafts[id]?.correction ?? "";
      const weak = field.original_extracted_value === null || field.confidence < threshold;
      const option = (value: string, title: string) => ({
        type: "radio" as const, name: `review:${id}`, value, checked: decision === value, disabled,
        "data-review-field": field.field_key, "data-document-id": doc.document_id,
        "aria-label": `${title} for ${label}`,
        onChange: () => change(id, { decision: value }),
      });
      return <fieldset key={id} className={`comparison-card review-item${decision ? " is-decided" : ""}`}>
        <legend className="review-item__title"><span className="review-item__field">{label}</span><span className="review-item__doc">{doc.display_name}</span></legend>
        <div className="review-item__badges">
          <span className={`review-pill${decision ? " review-pill--done" : ""}`}>{decision ? DECISION_NAMES[decision] : "Decision needed"}</span>
          {weak && field.original_extracted_value !== null && <span className="review-pill review-pill--warn">Low confidence</span>}
        </div>
        <p className="review-item__reference">Registry value <strong>{field.canonical_value ?? "Missing"}</strong></p>
        <div className="review-options" role="radiogroup" aria-label={`Decision for ${label}`}>
          <label className={`review-option${decision === "ACCEPTED" ? " is-chosen" : ""}${field.original_extracted_value == null ? " is-unavailable" : ""}`}>
            <input {...option("ACCEPTED", "Accept document suggestion")} disabled={disabled || field.original_extracted_value == null} />
            <span className="review-option__label">Accept document suggestion</span>
            {field.original_extracted_value == null ? <span className="review-option__missing">Not found in document</span> : <strong className="review-option__value">{field.original_extracted_value}</strong>}
          </label>
          <label className={`review-option${decision === "REJECTED" ? " is-chosen" : ""}`}>
            <input {...option("REJECTED", "Reject document suggestion")} />
            <span className="review-option__label">Reject document suggestion</span>
            <span className="review-option__missing">The value read from the document is not used</span>
          </label>
          <div className={`review-option review-option--manual${decision === "CORRECTED" ? " is-chosen" : ""}`}
            onClick={event => { if (disabled || (event.target as HTMLInputElement).type === "text") return; change(id, { decision: "CORRECTED" }); event.currentTarget.querySelector<HTMLInputElement>("input[type=text]")?.focus(); }}>
            <label className="review-option__label"><input {...option("CORRECTED", "Record correction")} /> Record correction</label>
            <input type="text" className="review-option__input" maxLength={512} value={correction} disabled={disabled}
              placeholder="Type what the document shows" aria-label={`Correction for ${label}`}
              onChange={event => change(id, { decision: "CORRECTED", correction: event.target.value })} />
          </div>
        </div>
        {openNotes.has(id) || drafts[id]?.note
          ? <div className="review-item__note-row">
            <label className="review-item__note">Optional note for {label}
              <input maxLength={240} value={drafts[id]?.note ?? ""} disabled={disabled} autoFocus={openNotes.has(id) && !drafts[id]?.note} onChange={event => change(id, { note: event.target.value })} />
            </label>
            <button type="button" className="btn btn-ghost review-item__remove-note" disabled={disabled} aria-label={`Remove note for ${label}`}
              onClick={() => { setOpenNotes(current => { const next = new Set(current); next.delete(id); return next; }); if (drafts[id]?.note) change(id, { note: "" }); }}>Remove note</button>
          </div>
          : <button type="button" className="btn btn-ghost review-item__add-note" disabled={disabled} aria-label={`Add note for ${label}`}
            onClick={() => setOpenNotes(current => new Set(current).add(id))}>+ Add note</button>}
        {decision === "CORRECTED" && !correction.trim() && <p className="control-help review-item__error">Type the corrected value before confirming.</p>}
        {weak && <p className="control-help">A review decision does not replace missing or low-confidence evidence. Replacement may still be required.</p>}
        {decision && <p className="control-help">Draft: {decision.toLowerCase()}{decision === "CORRECTED" ? ` · ${correction || "Correction needed"}` : ""}</p>}
      </fieldset>;
    }) : sources.map(item => {
      const label = item.field_name.replaceAll("_", " ");
      const decision = drafts[item.discrepancy_id]?.decision ?? "";
      const value = (kind: string) => item.observations.filter(obs => obs.source_kind === kind && obs.normalized_value != null).map(obs => obs.normalized_value).join(" · ");
      const choice = (action: ReconciliationDecisionAction, title: string, kind: string) => {
        const allowed = item.allowed_actions.includes(action);
        return <label className={`review-option${decision === action ? " is-chosen" : ""}${allowed ? "" : " is-unavailable"}`}>
          <input type="radio" name={`source:${item.discrepancy_id}`} value={action} checked={decision === action} disabled={disabled || !allowed}
            data-reconciliation-field={item.field_name} data-discrepancy-id={item.discrepancy_id}
            aria-label={`${title} for ${label}`}
            onChange={() => change(item.discrepancy_id, { decision: action })} />
          <span className="review-option__label">{title}</span>
          {value(kind) ? <strong className="review-option__value">{value(kind)}</strong> : <span className="review-option__missing">{kind === "REGISTRY" ? "Not in registry" : "Not found in document"}</span>}
          {!allowed && <span className="review-option__missing">Not offered for this field</span>}
        </label>;
      };
      return <fieldset key={item.discrepancy_id} className={`comparison-card review-item${decision ? " is-decided" : ""}`}>
        <legend className="review-item__title"><span className="review-item__field">{label}</span><span className="review-item__doc">Registry vs document</span></legend>
        <div className="review-item__badges"><span className={`review-pill${decision ? " review-pill--done" : ""}`}>{decision ? DECISION_NAMES[decision] : "Decision needed"}</span></div>
        <div className="review-options review-options--two" role="radiogroup" aria-label={`Source decision for ${label}`}>
          {choice("KEEP_REGISTRY_VALUE", "Keep registry value", "REGISTRY")}
          {choice("USE_DOCUMENT_VALUE", "Use document value", "DOCUMENT_IDP")}
        </div>
        {decision && <p className="control-help">Draft: {decision.replaceAll("_", " ").toLowerCase()}</p>}
      </fieldset>;
    })}
    </div>
    <footer className="blocker-review__footer">
      <p role="status" className="blocker-review__status">{selected} selected / {items.length} required · {items.length - selected} remaining · {saved ? "Draft saved in this tab" : "Draft not saved"}</p>
      {!complete && <p id="batch-confirm-disabled" className="blocker-review__hint">{invalid ? "Enter each correction before confirming." : "Select all required decisions before confirming."}</p>}
      <div className="document-card__actions">
        <button type="button" className="btn btn-secondary" disabled={disabled || selected === 0} onClick={() => setSaved(true)}>Save draft in this tab</button>
        <button type="button" className="btn btn-ghost" disabled={disabled || selected === 0} onClick={() => { setDraftState({ choices: {}, bindings, bulkResult: null }); setSaved(false); }}>Clear draft</button>
        <button type="button" className="btn btn-primary blocker-review-confirm" disabled={disabled || !complete} aria-describedby={!complete ? "batch-confirm-disabled" : undefined} onClick={confirm}>Confirm decisions & continue onboarding</button>
      </div>
      <details className="blocker-review__about">
        <summary>How drafts work</summary>
        <p>Your selections are a draft. The onboarding system has not processed them yet. Drafts stay in this tab while this case is open. Leaving the case, reloading the page, changing session or receiving changed review evidence clears this batch. An unchanged in-app refresh retains your choices.</p>
        <p>Confirming applies these decisions and continues the onboarding workflow. GoldTier Review & Send is a separate confirmation.</p>
      </details>
    </footer>
  </section>;
});
export default BlockerDecisionReview;
