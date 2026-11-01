import { formatOwnershipPercent } from "../ownershipDisplay";

import type { DocumentOwnershipObservation, DocumentProcessingRecord, OwnershipDocumentBinding } from "../types";

/** The exact selected total, or null while a selected share is not an exact decimal. */
export interface PartnerShareTotal { display: string; exactly100: boolean }

/**
 * D-101 partnership agreement confirmation (display only). The parent form owns every value
 * and builds the same submission as any document-observation decision; the server validates
 * the rows, the registry partners and the 100% total again and computes the UBOs.
 */
export default function ConfirmPartnerShares({
  legalName, uen, legalFormLabel, documents, documentId, onDocument, asOfDate, onAsOfDate,
  rows, selectedIds, onToggle, onToggleAll, total, rationale, onRationale, disabled,
  validationError, sourceLabel, rootPartyId, rootDisplayName, bindings, onEnterManually,
}: {
  legalName: string;
  uen: string;
  legalFormLabel?: string;
  documents: DocumentProcessingRecord[];
  documentId: string;
  onDocument: (documentId: string) => void;
  asOfDate: string;
  onAsOfDate: (value: string) => void;
  rows: DocumentOwnershipObservation[];
  selectedIds: string[];
  onToggle: (observationId: string, checked: boolean) => void;
  onToggleAll: (checked: boolean) => void;
  total: PartnerShareTotal | null;
  rationale: string;
  onRationale: (value: string) => void;
  disabled: boolean;
  validationError: string | null;
  sourceLabel: string;
  rootPartyId: string;
  rootDisplayName: string;
  bindings: OwnershipDocumentBinding[];
  onEnterManually: () => void;
}) {
  const selected = rows.filter((row) => selectedIds.includes(row.observation_id));
  const allSelected = rows.length > 0 && selected.length === rows.length;
  const totalState = !selected.length ? "empty" : total?.exactly100 ? "ok" : "warn";
  const hint = !asOfDate ? "Add the agreement date to continue."
    : !selected.length ? "Tick the partners whose shares you have checked."
    : !total?.exactly100 ? "Selected shares must add up to 100%." : "";
  return <div className="partner-shares">
    <div className="partner-shares__intro">
      <p className="partner-shares__eyebrow">Partnership · shares from the agreement</p>
      <h2 id="manual-ownership-title">Confirm partner shares from the partnership agreement</h2>
      <p>ACRA lists this firm's partners but not their shares. Check each share below against the agreement, then confirm. Nothing counts towards the UBO result until you do.</p>
    </div>
    <p className="partner-shares__summary" data-testid="partner-shares-summary">
      <strong>{legalName}</strong><span>UEN {uen}</span>{legalFormLabel && <span>{legalFormLabel}</span>}
    </p>
    <div className="partner-shares__fields">
      <label>Partnership agreement<select className="input" aria-label="Partnership agreement" value={documentId} disabled={disabled} onChange={(event) => onDocument(event.target.value)}>
        {documents.map((document) => <option key={document.document_id} value={document.document_id}>{document.display_name} · review revision {document.events.length}</option>)}
      </select></label>
      <label>Agreement date (as-of date)<input className="input" name="as_of_date" type="date" value={asOfDate} disabled={disabled} aria-describedby="partner-shares-date-hint" onChange={(event) => onAsOfDate(event.target.value)} />
        <span id="partner-shares-date-hint" className="control-help">Filled in from the agreement's own date. Change it if the agreement was amended.</span>
      </label>
    </div>
    <fieldset className="partner-shares__table">
      <legend className="sr-only">Partner shares from the agreement</legend>
      <div className="partner-shares__row partner-shares__row--head">
        <input type="checkbox" aria-label="Select all partners" checked={allSelected} disabled={disabled || !rows.length} onChange={(event) => onToggleAll(event.target.checked)} />
        <span aria-hidden="true">Partner</span><span aria-hidden="true">Share</span><span aria-hidden="true">Where it was found</span>
      </div>
      {rows.map((row) => {
        const checked = selectedIds.includes(row.observation_id);
        const share = formatOwnershipPercent(row.explicit_percentage);
        return <label key={row.observation_id} className={`partner-shares__row${checked ? " partner-shares__row--selected" : ""}`}>
          <input type="checkbox" checked={checked} disabled={disabled} aria-label={`Confirm ${row.owner_name} at ${share.replace("%", " percent")}`} onChange={(event) => onToggle(row.observation_id, event.target.checked)} />
          <span className="partner-shares__name">{row.owner_name}</span>
          <span className="partner-shares__share">{share}</span>
          <span className="partner-shares__where">Page {row.page_number} · {row.source_reference}</span>
        </label>;
      })}
      <div className={`partner-shares__total partner-shares__total--${totalState}`} role="status" data-testid="partner-shares-total">
        <span>Selected total: <strong>{total?.display ?? "—"}%</strong></span>
        <span className="partner-shares__total-message">{totalState === "ok" && <span aria-hidden="true">✓ </span>}
          {totalState === "ok" ? "Adds up to 100%" : totalState === "empty" ? "Nothing selected yet" : "Must add up to 100% for the partnership"}</span>
      </div>
    </fieldset>
    <p className="partner-shares__note"><strong>What happens when you confirm:</strong> the server works out the UBOs with the 25% rule (anyone with 25% or more), and checks again that the agreement's partners match ACRA's list and add up to 100%.</p>
    <label className="manual-ownership__rationale">Note for the reviewer (optional)<textarea className="input" name="rationale" value={rationale} minLength={10} maxLength={240} disabled={disabled} placeholder="e.g. Checked against the signed agreement." onChange={(event) => onRationale(event.target.value)} /></label>
    {validationError && <p className="ds-banner ds-banner-warn" role="alert">{validationError}</p>}
    <div className="partner-shares__actions">
      <button type="submit" className="btn btn-primary" disabled={disabled || !!hint} aria-describedby={hint ? "partner-shares-hint" : undefined}>Confirm partner shares</button>
      {hint && <span id="partner-shares-hint" className="control-help">{hint}</span>}
      <button type="button" className="btn btn-ghost partner-shares__manual" disabled={disabled} onClick={onEnterManually}>Shares not in the agreement? Enter them manually</button>
    </div>
    <details className="partner-shares__technical">
      <summary>Technical details</summary>
      <p className="manual-ownership__source">{sourceLabel}</p>
      <p>Root legal-entity ID: {rootPartyId} · Root legal-entity name: {rootDisplayName}</p>
      <p>Observation bindings: {bindings.length ? bindings.map((binding) => `${binding.document_id} · review revision ${binding.event_count}`).join("; ") : "No proposed ownership observations"}</p>
      <p>Rows: {rows.map((row) => `${row.source_reference} (${row.owner_name}) · ${row.extraction_quality ?? "UNKNOWN"} · ${row.extraction_method ?? "UNKNOWN"} · score ${row.evidence_score}`).join("; ")}</p>
      <p>This declaration is not ACRA evidence or verified ownership. Original graphs, document proposals and review receipts are retained; independent blockers remain authoritative. Exact decimal strings go to the server's single calculator; effective ownership is never calculated here. Declaration dates use the Singapore calendar (SGT).</p>
    </details>
  </div>;
}
