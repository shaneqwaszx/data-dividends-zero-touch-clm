import { useEffect, useState } from "react";
import type { DocumentProcessingRecord, ReconciliationDiscrepancy, ReconciliationObservation, ZeroTouchCaseSummary } from "../types";

/**
 * Reads the existing registry-vs-document reconciliation for one document's company name and UEN.
 * Reconciliation keeps one discrepancy per field with an observation from every current document,
 * so each document is judged only by its own observation: its own non-VALID value means it could
 * not be read, and its own VALID normalized value differing from the case's VALID value is a
 * mismatch. It adds no matching rules or thresholds, and the warning lasts only while the
 * discrepancy stays OPEN; nothing here resolves it.
 */
export type IdentityField = "legal_name" | "registration_identifier";

export interface IdentityWarningRow {
  field: IdentityField;
  documentValue: string | null;
  caseValue: string | null;
}

export interface DocumentIdentityWarning {
  kind: "DIFFERENT_COMPANY" | "FIELD_MISMATCH" | "UNREADABLE";
  mismatches: IdentityWarningRow[];
  unreadable: IdentityField[];
  /** Changes when the underlying evidence changes, so a new warning is announced again. */
  key: string;
}

const IDENTITY_FIELDS: readonly IdentityField[] = ["legal_name", "registration_identifier"];
const FIELD_LABELS: Record<IdentityField, string> = { legal_name: "company name", registration_identifier: "UEN" };

function documentObservation(discrepancy: ReconciliationDiscrepancy, documentId: string): ReconciliationObservation | null {
  // Observations without a document id cannot be attributed to one card, so they never warn.
  return discrepancy.observations.find((item) => item.source_kind === "DOCUMENT_IDP"
    && item.document_id === documentId) ?? null;
}

function caseObservation(discrepancy: ReconciliationDiscrepancy): ReconciliationObservation | null {
  return discrepancy.observations.find((item) => item.source_kind === "REGISTRY")
    ?? discrepancy.observations.find((item) => item.source_kind === "USER_INPUT") ?? null;
}

export function documentIdentityWarning(document: DocumentProcessingRecord, summary: ZeroTouchCaseSummary): DocumentIdentityWarning | null {
  const mismatches: IdentityWarningRow[] = [];
  const unreadable: IdentityField[] = [];
  const fingerprints: string[] = [];
  for (const field of IDENTITY_FIELDS) {
    const discrepancy = (summary.reconciliation?.discrepancies ?? []).find((item) => item.status === "OPEN"
      && item.field_name === field && documentObservation(item, document.document_id));
    if (!discrepancy) continue;
    const observation = documentObservation(discrepancy, document.document_id)!;
    const reference = caseObservation(discrepancy);
    if (observation.validity !== "VALID" || !observation.normalized_value) {
      unreadable.push(field);
    } else if (reference?.validity === "VALID" && reference.normalized_value
      && observation.normalized_value !== reference.normalized_value) {
      mismatches.push({ field, documentValue: observation.normalized_value, caseValue: reference.normalized_value });
    } else {
      // This document agrees with the case (or the case value itself is unusable): not its problem.
      continue;
    }
    fingerprints.push(discrepancy.evidence_fingerprint);
  }
  if (!mismatches.length && !unreadable.length) return null;
  const kind = mismatches.length === IDENTITY_FIELDS.length ? "DIFFERENT_COMPANY" : mismatches.length ? "FIELD_MISMATCH" : "UNREADABLE";
  return { kind, mismatches, unreadable, key: `${document.document_id}:${fingerprints.join(":")}` };
}

function unreadableText(fields: IdentityField[]): string {
  return fields.map((field) => FIELD_LABELS[field]).join(" and ");
}

function warningTitle(warning: DocumentIdentityWarning): string {
  if (warning.kind === "DIFFERENT_COMPANY") return "This document looks like it belongs to a different company";
  if (warning.kind === "UNREADABLE") return `We couldn't read the ${unreadableText(warning.unreadable)} from this document`;
  const label = FIELD_LABELS[warning.mismatches[0].field];
  return `The ${label} on this document doesn't match this case`;
}

/** Warnings already announced in this browser session; repeats render as plain text. */
const announcedWarnings = new Set<string>();

export function DocumentIdentityWarningCard({ warning, replaceDisabled, onReplace, onReviewDifference, onCorrectIdentity }: {
  warning: DocumentIdentityWarning;
  /** Null when this document has no permitted replacement control. */
  replaceDisabled: boolean | null;
  onReplace: () => void;
  onReviewDifference?: () => void;
  onCorrectIdentity?: () => void;
}) {
  const [announce] = useState(() => !announcedWarnings.has(warning.key));
  useEffect(() => { announcedWarnings.add(warning.key); }, [warning.key]);
  const title = warningTitle(warning);
  return (
    <div className="ds-banner ds-banner-warn document-identity-warning" role={announce ? "alert" : undefined} data-warning-kind={warning.kind}>
      <strong>{title}</strong>
      {warning.mismatches.length > 0 && <dl className="document-identity-warning__values">
        {warning.mismatches.map((row) => <div key={row.field}>
          <dt>{FIELD_LABELS[row.field] === "UEN" ? "UEN" : "Company name"}</dt>
          <dd><span>On this document: <strong>{row.documentValue}</strong></span><span>This case: <strong>{row.caseValue ?? "Not available"}</strong></span></dd>
        </div>)}
      </dl>}
      {warning.kind === "UNREADABLE"
        ? <span>The value is missing, unclear or below the confidence needed. Upload a clearer or complete copy of the document.</span>
        : warning.kind === "FIELD_MISMATCH" && warning.unreadable.length > 0
          ? <span>We also couldn't read the {unreadableText(warning.unreadable)} from this document.</span>
          : null}
      {warning.kind === "DIFFERENT_COMPANY" && <span>Check that you uploaded the right file, then replace it. The current file stays in the document history.</span>}
      <div className="document-identity-warning__actions">
        {replaceDisabled !== null && <button type="button" className="btn btn-primary" disabled={replaceDisabled} onClick={onReplace}>Replace document</button>}
        {warning.kind === "FIELD_MISMATCH" && onReviewDifference && <button type="button" className="btn btn-ghost" onClick={onReviewDifference}>Review the difference</button>}
        {warning.kind === "FIELD_MISMATCH" && onCorrectIdentity && <button type="button" className="btn btn-ghost" onClick={onCorrectIdentity}>The details I entered are wrong</button>}
      </div>
    </div>
  );
}
