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

/*
 * "Use registry value" is two backend steps: the document field is accepted (it was read
 * correctly), then the registry-vs-document conflict is decided with KEEP_REGISTRY_VALUE.
 * The backend's REJECTED decision is NOT used for it: rejecting removes the document value
 * and leaves the field missing. The reviewer's registry choice is remembered in memory only
 * (never browser storage) and pre-selects step two, which still needs an explicit confirm.
 */
type SourceIntent = "REGISTRY" | "DOCUMENT";
const sourceIntents = new Map<string, Map<string, SourceIntent>>();
const RECONCILIATION_FIELD_KEYS: Record<string, string> = { registration_identifier: "registration_number" };
export function documentFieldKeyFor(reconciliationField: string): string {
  return RECONCILIATION_FIELD_KEYS[reconciliationField] ?? reconciliationField;
}
function intentsFor(caseId: string): ReadonlyMap<string, SourceIntent> {
  return sourceIntents.get(caseId) ?? new Map();
}
export function registryChoiceFields(caseId: string): ReadonlySet<string> {
  return new Set([...intentsFor(caseId)].filter(([, intent]) => intent === "REGISTRY").map(([field]) => field));
}
export function clearSourceIntents(caseId: string): void {
  sourceIntents.delete(caseId);
}
function intentAction(intent: SourceIntent | undefined): ReconciliationDecisionAction | null {
  return intent === "REGISTRY" ? "KEEP_REGISTRY_VALUE" : intent === "DOCUMENT" ? "USE_DOCUMENT_VALUE" : null;
}

/**
 * After a confirmed field review, the registry-vs-document step applies the same choices the
 * reviewer already made, so one Confirm finishes both steps. Returns null (the panel stays,
 * pre-filled) unless every open decision maps to a choice the backend permits.
 */
export function followUpSourceDecisions(summary: ZeroTouchCaseSummary): ReviewDecisionBatch | null {
  const intents = intentsFor(summary.case.case_id);
  const reconciliation = summary.reconciliation;
  if (!intents.size || !reconciliation) return null;
  const active = new Set(summary.active_exceptions.map(item => item.exception_id));
  const open = reconciliation.discrepancies.filter(item => item.status === "OPEN" && item.allowed_actions.length > 0 && active.has(item.discrepancy_id));
  if (!open.length) return null;
  const choices = open.map(item => {
    const action = intentAction(intents.get(documentFieldKeyFor(item.field_name)));
    return action && item.allowed_actions.includes(action)
      ? { discrepancy_id: item.discrepancy_id, action, evidence_fingerprint: item.evidence_fingerprint } : null;
  });
  if (choices.some(choice => choice === null)) return null;
  return { expected_automation_version: summary.version, expected_case_event_count: summary.case.events.length,
    expected_reconciliation_version: reconciliation.version,
    reconciliation: choices as NonNullable<ReviewDecisionBatch["reconciliation"]> };
}

// Every field and discrepancy needs an explicit reviewer choice; only a remembered registry choice is pre-selected.
// Submitted values stay the backend ReviewDecision / ReconciliationDecisionAction enums.
/** Plain explanation when the backend does not offer a source for this field. */
function unavailableReason(action: ReconciliationDecisionAction, hasValue: boolean): string {
  if (action === "USE_DOCUMENT_VALUE") {
    return hasValue
      ? "Shown for comparison only — this field can't be updated from the document"
      : "No document value can be applied to this field";
  }
  return "The registry value can't be kept for this field";
}

const DECISION_NAMES: Record<string, string> = {
  ACCEPTED: "Document suggestion", REGISTRY: "Registry value", REJECTED: "Registry value", CORRECTED: "Manual input",
  KEEP_REGISTRY_VALUE: "Registry value", USE_DOCUMENT_VALUE: "Document value",
};
const EMPTY_DRAFT: Draft = { decision: "", correction: "", note: "" };

/** Registry-vs-document discrepancies this panel currently offers a decision for. */
export function reviewableSourceDiscrepancies(summary: ZeroTouchCaseSummary, documents: DocumentProcessingRecord[]) {
  const activeIds = new Set(summary.active_exceptions.map(item => item.exception_id));
  const currentDocuments = documents.filter(doc => doc.superseded_by_document_id == null);
  const reconciliation = summary.reconciliation;
  const currentSources = reconciliation?.source_document_ids?.length === currentDocuments.length
    && reconciliation?.source_document_ids?.every((id, index) => currentDocuments.some(doc => doc.document_id === id
      && doc.events.length === reconciliation.source_document_event_counts[index]));
  return currentSources ? reconciliation?.discrepancies.filter(item => item.status === "OPEN"
    && item.allowed_actions.length > 0 && activeIds.has(item.discrepancy_id)) ?? []
    : [];
}

const BlockerDecisionReview = forwardRef<ReviewDraftHandle, {
  summary: ZeroTouchCaseSummary;
  documents: DocumentProcessingRecord[];
  busy: boolean;
  onConfirm: (batch: ReviewDecisionBatch) => void;
  /** Opens the replace-document picker; a new document reopens field review, where manual input works. */
  onReplaceDocument?: () => void;
}>(function BlockerDecisionReview({ summary, documents, busy, onConfirm, onReplaceDocument }, ref) {
  const reconciliation = summary.reconciliation;
  const sources = reviewableSourceDiscrepancies(summary, documents);
  // Stale "pending" field flags can remain after the case has moved past documents; the
  // backend's active document-stage exception is what actually requires these decisions.
  const documentReviewActive = summary.active_exceptions.some(item => item.stage === "DOCUMENT");
  const reviewable = !documentReviewActive ? [] : documents.filter(doc => doc.superseded_by_document_id == null
    && doc.state === "REVIEW_REQUIRED" && !doc.semantic_completion && doc.review_source_fingerprint);
  const fields = reviewable.flatMap(doc => doc.fields.filter(field => field.review_status === "PENDING")
    .map(field => ({ doc, field, id: `${doc.document_id}:${field.field_key}` })));
  // No group switcher: document field reviews come first; registry-vs-document decisions follow once they are done.
  const family: "document" | "source" = fields.length ? "document" : "source";
  const bindings: Record<string, string> = Object.fromEntries([
    ...fields.map(({ id, doc }) => [id, JSON.stringify([doc.review_source_fingerprint, doc.events.length, doc.document_version])]),
    ...sources.map(item => [item.discrepancy_id, JSON.stringify([reconciliation?.reconciliation_id, reconciliation?.version, item.evidence_fingerprint, item.allowed_actions])]),
  ]);
  const intents = intentsFor(summary.case.case_id);
  const [draftState, setDraftState] = useState<ReviewDraftState>(() => ({ bindings, bulkResult: null, choices: family === "source"
    ? Object.fromEntries(sources.flatMap(item => {
      const action = intentAction(intents.get(documentFieldKeyFor(item.field_name)));
      return action && item.allowed_actions.includes(action) ? [[item.discrepancy_id, { decision: action, correction: "", note: "" }]] : [];
    }))
    : {} }));
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
  function fillUndecided(decision: "ACCEPTED" | "REGISTRY") {
    if (disabled || family !== "document") return;
    setDraftState(current => {
      const choices = { ...current.choices };
      let filled = 0;
      let skipped = 0;
      for (const { id, field } of fields) {
        const draft = choices[id];
        if (draft?.decision || draft?.correction.trim()
          || field.original_extracted_value == null
          || (decision === "REGISTRY" && field.canonical_value == null)) {
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
      if (destination.discrepancyId && family === "source" && sources.some(item => item.discrepancy_id === destination.discrepancyId)) return true;
      if (family === "document" && fields.some(item => item.doc.document_id === destination.documentId && item.field.field_key === destination.fieldKey)) return true;
      return false;
    },
    selectSourceDecision(id, action) {
      if (disabled || family !== "source" || !sources.some(item => item.discrepancy_id === id && item.allowed_actions.includes(action))) return false;
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
      clearSourceIntents(summary.case.case_id);
    } else {
      // Remember each choice for the registry-vs-document step: registry, or the document's (or manual) value.
      sourceIntents.set(summary.case.case_id, new Map(fields.map(({ id, field }) => [field.field_key,
        drafts[id].decision === "REGISTRY" ? "REGISTRY" as const : "DOCUMENT" as const])));
      onConfirm({ ...base, documents: reviewable.filter(doc => fields.some(item => item.doc.document_id === doc.document_id)).map(doc => ({
        document_id: doc.document_id, expected_event_count: doc.events.length, source_fingerprint: doc.review_source_fingerprint!,
        decisions: fields.filter(item => item.doc.document_id === doc.document_id).map(({ id, field }) => ({
          // Registry choice = accept the correctly read document value now; registry wins in step two.
          field_key: field.field_key, decision: (drafts[id].decision === "REGISTRY" ? "ACCEPTED" : drafts[id].decision) as ReviewDecision,
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
    {family === "document" && <div className="blocker-review__bulk">
      <p>Fill undecided eligible document drafts only. Existing choices, corrections and notes are kept; Confirm is still required.</p>
      <div className="document-card__actions">
        <button type="button" className="btn btn-secondary" disabled={disabled} onClick={() => fillUndecided("ACCEPTED")}>Use document suggestion for all undecided</button>
        <button type="button" className="btn btn-secondary" disabled={disabled} onClick={() => fillUndecided("REGISTRY")}>Use registry value for all undecided</button>
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
        {/* Three choices: registry value, document suggestion, or manual input. */}
        <div className="review-options" role="radiogroup" aria-label={`Decision for ${label}`}>
          <label className={`review-option${decision === "REGISTRY" ? " is-chosen" : ""}${field.canonical_value == null || field.original_extracted_value == null ? " is-unavailable" : ""}`}>
            <input {...option("REGISTRY", "Use registry value")} disabled={disabled || field.canonical_value == null || field.original_extracted_value == null} />
            <span className="review-option__label">Use registry value</span>
            {field.canonical_value == null ? <span className="review-option__missing">Not in registry</span> : <strong className="review-option__value">{field.canonical_value}</strong>}
            {field.canonical_value != null && field.original_extracted_value == null && <span className="review-option__missing">Document has no value here — enter it manually or replace the document</span>}
          </label>
          <label className={`review-option${decision === "ACCEPTED" ? " is-chosen" : ""}${field.original_extracted_value == null ? " is-unavailable" : ""}`}>
            <input {...option("ACCEPTED", "Use document suggestion")} disabled={disabled || field.original_extracted_value == null} />
            <span className="review-option__label">Use document suggestion</span>
            {field.original_extracted_value == null ? <span className="review-option__missing">Not found in document</span> : <strong className="review-option__value">{field.original_extracted_value}</strong>}
          </label>
          <div className={`review-option review-option--manual${decision === "CORRECTED" ? " is-chosen" : ""}`}
            onClick={event => { if (disabled || (event.target as HTMLInputElement).type === "text") return; change(id, { decision: "CORRECTED" }); event.currentTarget.querySelector<HTMLInputElement>("input[type=text]")?.focus(); }}>
            <label className="review-option__label"><input {...option("CORRECTED", "Enter manually")} /> Enter manually</label>
            <input type="text" className="review-option__input" maxLength={512} value={correction} disabled={disabled}
              placeholder="Type the correct value" aria-label={`Correction for ${label}`}
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
        {decision && <p className="control-help">Draft: {DECISION_NAMES[decision].toLowerCase()}{decision === "CORRECTED" ? ` · ${correction || "Value needed"}` : ""}</p>}
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
          {/* The backend decides which source can be applied; a shown value may be comparison-only. */}
          {!allowed && <span className="review-option__missing">{unavailableReason(action, Boolean(value(kind)))}</span>}
        </label>;
      };
      return <fieldset key={item.discrepancy_id} className={`comparison-card review-item${decision ? " is-decided" : ""}`}>
        <legend className="review-item__title"><span className="review-item__field">{label}</span><span className="review-item__doc">Registry vs document</span></legend>
        {(() => {
          const intent = intents.get(documentFieldKeyFor(item.field_name));
          const action = intentAction(intent);
          if (!action) return null;
          return item.allowed_actions.includes(action)
            ? <p className="control-help">Pre-selected from your choice in the previous step — confirm to apply it.</p>
            : <p className="control-help review-item__error">You chose the {intent === "REGISTRY" ? "registry" : "document"} value, but this field doesn't allow it here. Pick an available option or upload a replacement document.</p>;
        })()}
        <div className="review-item__badges"><span className={`review-pill${decision ? " review-pill--done" : ""}`}>{decision ? DECISION_NAMES[decision] : "Decision needed"}</span></div>
        <div className="review-options" role="radiogroup" aria-label={`Source decision for ${label}`}>
          {choice("KEEP_REGISTRY_VALUE", "Use registry value", "REGISTRY")}
          {choice("USE_DOCUMENT_VALUE", "Use document value", "DOCUMENT_IDP")}
          {/* The backend offers no manual value at this step; it exists only in document field review. */}
          <div className="review-option review-option--manual is-unavailable" aria-disabled="true">
            <span className="review-option__label">Enter manually</span>
            <span className="review-option__missing">Manual input is only available while reviewing the document fields.</span>
            {onReplaceDocument && <button type="button" className="btn btn-ghost review-option__link" disabled={disabled} onClick={onReplaceDocument}>Upload a replacement document to enter it manually</button>}
          </div>
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
