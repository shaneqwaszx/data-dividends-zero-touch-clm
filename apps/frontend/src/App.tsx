import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";

import {
  analyzeOwnership,
  ApiError,
  completeZeroTouchIntake,
  createClmCase,
  evaluateClmReadiness,
  fetchClmCase,
  fetchDocuments,
  fetchMockScenarios,
  fetchExecutionProfile,
  fetchOwnership,
  fetchUatEvidence,
  fetchZeroTouchCase,
  fetchZeroTouchCases,
  intakeZeroTouchDocument,
  loadMockOwnership,
  reviewDocument,
  resolveReconciliationDiscrepancy,
  resolveZeroTouchException,
  replaceZeroTouchDocument,
  retryZeroTouchIntakeDocument,
  resumeZeroTouchCase,
  submitClmCase,
  uploadDocument,
  createZeroTouchCase,
} from "./api";
import { startAutomationPolling } from "./automationPolling";
import type {
  ClmCaseSummary,
  DocumentFieldKey,
  DocumentProcessingRecord,
  MockIdpScenario,
  MockOwnershipScenario,
  MockScenario,
  OnboardingCase,
  OwnershipAnalysisRecord,
  OwnershipCandidate,
  ReviewDecision,
  ReconciliationDecisionAction,
  ReconciliationDiscrepancy,
  SimulationProfile,
  ExceptionResolutionAction,
  ZeroTouchCaseSummary,
  ZeroTouchCaseListItem,
  ZeroTouchDemoScenario,
  ZeroTouchException,
} from "./types";

const DEFAULT_UEN = "202400001A";
const MAX_INTAKE_FILES = 20;
const MAX_FILE_BYTES = 5 * 1024 * 1024;
const MAX_TOTAL_INTAKE_BYTES = 25 * 1024 * 1024;
const DOCUMENT_TYPES: Record<string, string> = {
  ".pdf": "application/pdf",
  ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  ".txt": "text/plain",
};
const SAFE_DOCUMENT_NAME = /^[A-Za-z0-9][A-Za-z0-9._ -]{0,94}\.(pdf|docx|txt)$/i;

type StartProgressStage =
  | "idle"
  | "creating"
  | "uploading"
  | "starting"
  | "processing"
  | "waiting"
  | "completed"
  | "failed";

export interface StartProgress {
  stage: StartProgressStage;
  message: string;
  failedFile: string | null;
}

function selectedFileKey(file: File): string {
  return `${file.name}:${file.size}:${file.lastModified}`;
}

export function validateSelectedDocuments(files: File[]): {
  accepted: File[];
  errors: string[];
} {
  const accepted: File[] = [];
  const errors: string[] = [];
  const seen = new Set<string>();
  let totalBytes = 0;
  for (const file of files) {
    const key = selectedFileKey(file);
    if (seen.has(key)) continue;
    seen.add(key);
    const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    const expectedType = DOCUMENT_TYPES[extension];
    if (!SAFE_DOCUMENT_NAME.test(file.name) || !expectedType || file.type !== expectedType) {
      errors.push(`${file.name}: only matching PDF, DOCX, and UTF-8 TXT files are supported.`);
      continue;
    }
    if (file.size <= 0 || file.size > MAX_FILE_BYTES) {
      errors.push(`${file.name}: file must be non-empty and no larger than 5 MiB.`);
      continue;
    }
    if (accepted.length >= MAX_INTAKE_FILES) {
      errors.push(`${file.name}: the 20-file POC limit has been reached.`);
      continue;
    }
    if (totalBytes + file.size > MAX_TOTAL_INTAKE_BYTES) {
      errors.push(`${file.name}: the 25 MiB total intake limit would be exceeded.`);
      continue;
    }
    accepted.push(file);
    totalBytes += file.size;
  }
  return { accepted, errors };
}

export function selectedDocumentTotalBytes(files: File[]): number {
  return files.reduce((total, file) => total + file.size, 0);
}

export function formatDocumentBytes(bytes: number): string {
  if (bytes >= 1024 * 1024) {
    const mebibytes = bytes / (1024 * 1024);
    return `${Number.isInteger(mebibytes) ? mebibytes : mebibytes.toFixed(1)} MiB`;
  }
  if (bytes >= 1024) {
    const kibibytes = bytes / 1024;
    return `${Number.isInteger(kibibytes) ? kibibytes : kibibytes.toFixed(1)} KiB`;
  }
  return `${bytes} B`;
}

export function selectedDocumentSummary(files: File[]): string {
  const label = files.length === 1 ? "document" : "documents";
  return `${files.length} ${label} selected · ${formatDocumentBytes(selectedDocumentTotalBytes(files))} / ${formatDocumentBytes(MAX_TOTAL_INTAKE_BYTES)}`;
}

export async function runEvidenceMutation<T>(
  onStart: () => void,
  operation: () => Promise<T>,
  onSettled: () => Promise<void>,
): Promise<T> {
  onStart();
  try {
    return await operation();
  } finally {
    await onSettled();
  }
}

function formatTimestamp(value: string): string {
  return new Intl.DateTimeFormat("en-SG", {
    dateStyle: "medium",
    timeStyle: "medium",
    timeZone: "Asia/Singapore",
  }).format(new Date(value));
}

function formatAddress(caseData: OnboardingCase): string {
  const address = caseData.entity?.registered_address;
  if (!address) return "Not available";
  return [
    address.address_line_1,
    address.address_line_2,
    address.postal_code,
    address.country_code,
  ]
    .filter(Boolean)
    .join(", ");
}

function titleCaseEnvironment(value: "MOCK" | "SANDBOX" | "LOCAL"): string {
  return value === "MOCK" ? "Mock" : value === "LOCAL" ? "Local POC" : "Sandbox";
}

function confidencePercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function ownershipPercent(value: string): string {
  const match = /^([+-]?)(\d+)(?:\.(\d+))?$/.exec(value.trim());
  if (!match) return "Invalid";
  const sign = match[1] === "-" ? "-" : "";
  const integer = match[2].replace(/^0+(?=\d)/, "");
  const fraction = (match[3] ?? "").replace(/0+$/, "");
  return `${sign}${integer}${fraction ? `.${fraction}` : ""}%`;
}

function fieldLabel(value: string): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

// Enhanced error message mapper
function friendlyErrorMessage(code: string | null, defaultMessage: string): string {
  const messages: Record<string, string> = {
    "DOCUMENT_TOO_LARGE": "PDF file is too large. Maximum size is 5 MiB.",
    "DOCUMENT_MEDIA_TYPE_UNSUPPORTED": "File type not supported. Please upload a PDF.",
    "OWNERSHIP_CYCLE": "Ownership graph contains circular relationships. Please review the ownership structure.",
    "OWNERSHIP_INCOMPLETE": "Incomplete ownership data detected. Some legal entities have no disclosed owners.",
    "DOCUMENT_LOW_CONFIDENCE": "Document extraction confidence below threshold. Please review or upload a clearer document.",
    "DOCUMENT_FIELD_MISMATCH": "Extracted data does not match registry records. Please verify or provide corrections.",
    "GT_EXISTING_PARTY_REVIEW_REQUIRED": "Party already exists in target system. Please review the matching record.",
    "REGISTRY_REVIEW_REQUIRED": "Registry data requires human review before proceeding.",
    "JURISDICTION_UNRESOLVED": "Jurisdiction must be resolved before registry retrieval can begin.",
    "JURISDICTION_CONFLICT": "Jurisdiction evidence conflicts and requires review before registry retrieval.",
    "REGISTRY_PROVIDER_NOT_IMPLEMENTED": "This jurisdiction is recognised, but its registry provider is not implemented.",
  };
  return messages[code ?? ""] || defaultMessage;
}

// Blocker explanation helper
function blockerExplanation(blockerCode: string): string {
  const explanations: Record<string, string> = {
    "DOCUMENT_LOW_CONFIDENCE": "One or more fields were extracted from the document with confidence below the configured threshold (85%). Please review the extracted values.",
    "DOCUMENT_FIELD_MISMATCH": "Extracted document data does not match the registry records. Please review and correct the mismatched fields.",
    "DOCUMENT_REQUIRED_FIELD_MISSING": "A required field is missing from the document extraction. Please provide additional documentation.",
    "OWNERSHIP_CYCLE": "Circular ownership relationships detected in the ownership graph. This prevents UBO calculation. Please verify the ownership structure.",
    "OWNERSHIP_INCOMPLETE": "Incomplete ownership chain: some legal entities have no disclosed owners. Cannot complete UBO analysis without this information.",
    "EXISTING_PARTY_REVIEW_REQUIRED": "A party with similar details already exists in the target system. Please review the match before proceeding.",
    "REGISTRY_REVIEW_REQUIRED": "Registry data validation requires human review. Please check the entity details.",
    "JURISDICTION_UNRESOLVED": "No authoritative jurisdiction observation is available. Registry retrieval has not started.",
    "JURISDICTION_CONFLICT": "Jurisdiction observations disagree. No registry provider was selected and review is required.",
    "REGISTRY_PROVIDER_NOT_IMPLEMENTED": "The jurisdiction is recognised, but this Singapore-only POC has no provider implementation for it.",
  };
  return explanations[blockerCode] || blockerCode.replaceAll("_", " ");
}

export function SimulationBanner({ profile }: { profile: SimulationProfile | null }) {
  const sourceLabel = profile
    ? `${profile.registry_system} ${titleCaseEnvironment(profile.registry_environment)}`
    : null;
  return (
    <div className="environment-banner" role="status">
      <span aria-hidden="true" />
      {profile
        ? `${sourceLabel} | GoldTier Mock | IDP ${titleCaseEnvironment(profile.idp_environment)} (${profile.idp_provider}) | Ownership Mock | External access is backend-managed`
        : "Loading backend connector profile..."}
    </div>
  );
}
type FieldCandidate = DocumentProcessingRecord["fields"][number];

function FieldReviewCard({
  field,
  threshold,
  isDeciding,
  onDecision,
}: {
  field: FieldCandidate;
  threshold: number;
  isDeciding: boolean;
  onDecision: (
    fieldKey: DocumentFieldKey,
    decision: ReviewDecision,
    correctedValue?: string,
    note?: string,
  ) => void;
}) {
  const [correctedValue, setCorrectedValue] = useState("");
  const [note, setNote] = useState("");
  const needsAttention =
    field.confidence < threshold || field.comparison_status !== "MATCH";

  return (
    <article
      className={`document-field ${needsAttention ? "document-field--attention" : ""}`}
      data-comparison={field.comparison_status}
    >
      <header className="document-field__heading">
        <div>
          <h4>{fieldLabel(field.field_key)}</h4>
          <span className={`comparison-badge comparison-badge--${field.comparison_status}`}>
            {field.comparison_status}
          </span>
        </div>
        <strong className={field.confidence < threshold ? "confidence-low" : ""}>
          {confidencePercent(field.confidence)} confidence
        </strong>
      </header>

      <div className="comparison-grid">
        <div>
          <span>IDP suggested</span>
          <strong>{field.original_extracted_value ?? "Missing from document"}</strong>
        </div>
        <div>
          <span>ACRA / canonical</span>
          <strong>{field.canonical_value ?? "Missing from registry"}</strong>
        </div>
        <div>
          <span>Normalized suggestion</span>
          <strong>{field.normalized_value ?? "Not available"}</strong>
        </div>
        <div>
          <span>Provenance</span>
          <strong>
            {field.provenance.provider} / {field.provenance.environment}
            {field.provenance.page_number ? ` / page ${field.provenance.page_number}` : ""}
          </strong>
        </div>
      </div>

      {field.review_status === "PENDING" ? (
        <div className="field-review-controls">
          <label>
            Optional safe note
            <input
              value={note}
              maxLength={240}
              onChange={(event) => setNote(event.target.value)}
              placeholder="No sensitive document text"
            />
          </label>
          <div className="review-actions">
            <button
              type="button"
              disabled={isDeciding || field.original_extracted_value === null}
              onClick={() => onDecision(field.field_key, "ACCEPTED", undefined, note)}
            >
              Accept
            </button>
            <button
              className="button-secondary"
              type="button"
              disabled={isDeciding}
              onClick={() => onDecision(field.field_key, "REJECTED", undefined, note)}
            >
              Reject
            </button>
          </div>
          <div className="correction-row">
            <label>
              Corrected value
              <input
                value={correctedValue}
                maxLength={512}
                onChange={(event) => setCorrectedValue(event.target.value)}
                placeholder="Enter the human-reviewed value"
              />
            </label>
            <button
              type="button"
              disabled={isDeciding || !correctedValue.trim()}
              onClick={() =>
                onDecision(field.field_key, "CORRECTED", correctedValue, note)
              }
            >
              Save correction
            </button>
          </div>
        </div>
      ) : (
        <div className={`reviewed-field reviewed-field--${field.review_status}`}>
          <strong>Human review: {field.review_status}</strong>
          <span>
            Human-confirmed value: {field.reviewed_value ?? "No value retained"}
          </span>
          {field.review_note && <span>Note: {field.review_note}</span>}
        </div>
      )}
    </article>
  );
}

export function DocumentReviewSummary({
  record,
  threshold = 0.85,
  onDecision,
  isDeciding = false,
}: {
  record: DocumentProcessingRecord;
  threshold?: number;
  onDecision?: (
    fieldKey: DocumentFieldKey,
    decision: ReviewDecision,
    correctedValue?: string,
    note?: string,
  ) => void;
  isDeciding?: boolean;
}) {
  return (
    <article className="document-result" aria-live="polite">
      <div className="document-result__heading">
        <div>
          <p className="section-label">Project-defined provisional profile</p>
          <h3>{record.display_name}</h3>
          <span>{record.profile}</span>
        </div>
        <strong>{record.state}</strong>
      </div>
      <p className="synthetic-notice">
        Values are deterministic Mock IDP candidates, not OCR output from this file and
        not Delta Capita-approved fields. Human review does not mean Ready-for-Approval.
      </p>

      {record.error && (
        <div className="request-error" role="alert">
          {record.error.code}: {record.error.message}
        </div>
      )}

      <div className="document-fields">
        {record.fields.map((field) => (
          <FieldReviewCard
            key={field.field_key}
            field={field}
            threshold={threshold}
            isDeciding={isDeciding}
            onDecision={
              onDecision ?? (() => undefined)
            }
          />
        ))}
      </div>

      {record.state === "REVIEWED" && (
        <p className="decision-notice">
          Document field review completed by an unauthenticated local POC operator.
          Original IDP suggestions remain retained alongside human-reviewed values.
        </p>
      )}
    </article>
  );
}

export function DocumentPanel({
  caseData,
  threshold,
  onMutationStart,
  onMutationSettled,
}: {
  caseData: OnboardingCase;
  threshold: number;
  onMutationStart: () => void;
  onMutationSettled: () => Promise<void>;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [scenario, setScenario] = useState<MockIdpScenario>("ALL_FIELDS_MATCH");
  const [documents, setDocuments] = useState<DocumentProcessingRecord[]>([]);
  const [activeDocument, setActiveDocument] = useState<DocumentProcessingRecord | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isDeciding, setIsDeciding] = useState(false);
  const [documentError, setDocumentError] = useState<string | null>(null);

  useEffect(() => {
    void fetchDocuments(caseData.case_id)
      .then((items) => {
        setDocuments(items);
        setActiveDocument(items.at(-1) ?? null);
      })
      .catch(() => setDocumentError("Document list is unavailable."));
  }, [caseData.case_id]);

  function replaceDocument(record: DocumentProcessingRecord) {
    setDocuments((current) => {
      const withoutRecord = current.filter((item) => item.document_id !== record.document_id);
      return [...withoutRecord, record];
    });
    setActiveDocument(record);
  }

  async function handleDocumentSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;
    setIsProcessing(true);
    setDocumentError(null);
    try {
      replaceDocument(
        await runEvidenceMutation(
          onMutationStart,
          () => uploadDocument(caseData.case_id, file, scenario),
          onMutationSettled,
        ),
      );
    } catch (error) {
      setDocumentError(error instanceof Error ? error.message : "Document processing failed.");
      try {
        const refreshed = await fetchDocuments(caseData.case_id);
        setDocuments(refreshed);
        setActiveDocument(refreshed.at(-1) ?? null);
      } catch {
        // Keep the sanitized processing error visible if refresh is unavailable.
      }
    } finally {
      setIsProcessing(false);
    }
  }

  async function handleDecision(
    fieldKey: DocumentFieldKey,
    decision: ReviewDecision,
    correctedValue?: string,
    note?: string,
  ) {
    if (!activeDocument) return;
    setIsDeciding(true);
    setDocumentError(null);
    try {
      replaceDocument(
        await runEvidenceMutation(
          onMutationStart,
          () =>
            reviewDocument(
              caseData.case_id,
              activeDocument.document_id,
              fieldKey,
              decision,
              correctedValue,
              note,
            ),
          onMutationSettled,
        ),
      );
    } catch (error) {
      setDocumentError(error instanceof Error ? error.message : "Field review failed.");
    } finally {
      setIsDeciding(false);
    }
  }

  return (
    <section className="document-card" aria-labelledby="document-heading">
      <div>
        <p className="section-label">Phase 03 document sub-workflow</p>
        <h2 id="document-heading">Document review</h2>
        <p>
          PDFs are bounded and transient. Mock IDP candidates are compared with the
          existing canonical entity and never overwrite it.
        </p>
      </div>
      <form onSubmit={(event) => void handleDocumentSubmit(event)}>
        <label htmlFor="document-file">PDF document</label>
        <input
          id="document-file"
          type="file"
          accept="application/pdf,.pdf"
          required
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
        <label htmlFor="idp-scenario">Synthetic Mock IDP scenario</label>
        <select
          id="idp-scenario"
          value={scenario}
          onChange={(event) => setScenario(event.target.value as MockIdpScenario)}
        >
          <option value="ALL_FIELDS_MATCH">All fields match registry</option>
          <option value="FIELD_MISMATCH">One field mismatch</option>
          <option value="LOW_CONFIDENCE">Low-confidence field</option>
          <option value="MISSING_FIELD">Missing document field</option>
          <option value="PROCESSOR_FAILURE">Processor failure</option>
        </select>
        <button type="submit" disabled={isProcessing || !file}>
          {isProcessing ? "Processing transient PDF..." : "Upload and run Mock IDP"}
        </button>
        <p className="input-help">
          Development review threshold: {confidencePercent(threshold)} — provisional,
          not sponsor-approved.
        </p>
      </form>

      {documents.length > 0 && (
        <nav className="document-list" aria-label="Case documents">
          {documents.map((document) => (
            <button
              className={
                document.document_id === activeDocument?.document_id
                  ? "document-list__active"
                  : "button-secondary"
              }
              type="button"
              key={document.document_id}
              onClick={() => setActiveDocument(document)}
            >
              {document.display_name} · {document.state}
            </button>
          ))}
        </nav>
      )}

      {documentError && (
        <div className="request-error" role="alert">
          ❌ {friendlyErrorMessage(null, documentError)}
        </div>
      )}
      {activeDocument && (
        <DocumentReviewSummary
          record={activeDocument}
          threshold={threshold}
          onDecision={(...args) => void handleDecision(...args)}
          isDeciding={isDeciding}
        />
      )}
    </section>
  );
}

function OwnershipCandidateCard({ candidate }: { candidate: OwnershipCandidate }) {
  return (
    <article
      className={`ownership-candidate ownership-candidate--${candidate.classification}`}
    >
      <header className="ownership-candidate__heading">
        <div>
          <h3>{candidate.party.display_name}</h3>
          <span>{candidate.party.party_id}</span>
        </div>
        <strong>{fieldLabel(candidate.classification)}</strong>
      </header>
      <dl className="ownership-totals">
        <div>
          <dt>Direct ownership</dt>
          <dd>{ownershipPercent(candidate.direct_ownership_percent)}</dd>
        </div>
        <div>
          <dt>Indirect ownership</dt>
          <dd>{ownershipPercent(candidate.indirect_ownership_percent)}</dd>
        </div>
        <div>
          <dt>Aggregated ownership</dt>
          <dd>{ownershipPercent(candidate.aggregated_ownership_percent)}</dd>
        </div>
        <div>
          <dt>Threshold result</dt>
          <dd>{candidate.threshold_result}</dd>
        </div>
      </dl>
      <div className="ownership-paths">
        <h4>Deterministic calculation evidence</h4>
        {candidate.paths.map((path) => (
          <div className="ownership-path" key={path.path_id}>
            <ol>
              {path.edges.map((edge) => (
                <li key={edge.relationship_id}>
                  <strong>{edge.parent_display_name}</strong>
                  <span>{ownershipPercent(edge.ownership_percent)} →</span>
                  <strong>{edge.child_display_name}</strong>
                </li>
              ))}
            </ol>
            <p>{path.calculation}</p>
            <span>{path.is_direct ? "Direct path" : "Indirect path"}</span>
          </div>
        ))}
      </div>
    </article>
  );
}

export function SimpleOwnershipGraph({ record }: { record: OwnershipAnalysisRecord }) {
  const parties = new Map(record.parties.map((party) => [party.party_id, party]));
  const root = record.root_party_id ? parties.get(record.root_party_id) : null;
  const isNaturalPerson = (partyId: string) => parties.get(partyId)?.party_type === "NATURAL_PERSON";
  
  // Simple grid layout for ownership visualization
  const rows: string[][] = [];
  const visited = new Set<string>();
  const queue: [string, number][] = record.root_party_id ? [[record.root_party_id, 0]] : [];
  
  while (queue.length > 0) {
    const [partyId, depth] = queue.shift()!;
    if (visited.has(partyId)) continue;
    visited.add(partyId);
    
    if (!rows[depth]) rows[depth] = [];
    rows[depth].push(partyId);
    
    const children = record.relationships
      .filter(r => r.parent_party_id === partyId)
      .map(r => r.child_party_id);
    
    for (const child of children) {
      queue.push([child, depth + 1]);
    }
  }
  
  return (
    <div className="ownership-graph-viz">
      <p className="section-label">Ownership structure visualization</p>
      <div className="graph-container">
        {rows.map((rowParties, depth) => (
          <div key={`depth-${depth}`} className="graph-row">
            <div className="depth-label">Level {depth}</div>
            <div className="parties-row">
              {rowParties.map((partyId) => {
                const party = parties.get(partyId);
                const isUbo = record.candidates.some(c => c.party.party_id === partyId && c.classification === "PROVISIONAL_UBO_CANDIDATE");
                const ownedBy = record.relationships.filter(r => r.parent_party_id === partyId);
                
                return (
                  <article key={partyId} className={`graph-party ${isNaturalPerson(partyId) ? 'natural-person' : 'legal-entity'} ${isUbo ? 'is-ubo' : ''}`}>
                    <h4>{party?.display_name ?? partyId}</h4>
                    <span className="party-type">{party?.party_type}</span>
                    {isUbo && <span className="ubo-badge">🏆 UBO Candidate</span>}
                    {ownedBy.length > 0 && (
                      <div className="ownership-list">
                        {ownedBy.map(rel => (
                          <div key={rel.relationship_id} className="ownership-item">
                            → {ownershipPercent(rel.ownership_percent)}
                          </div>
                        ))}
                      </div>
                    )}
                  </article>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function OwnershipSummary({ record }: { record: OwnershipAnalysisRecord }) {
  const parties = new Map(record.parties.map((party) => [party.party_id, party]));
  const root = record.root_party_id ? parties.get(record.root_party_id) : null;
  return (
    <article className="ownership-result" aria-live="polite">
      <div className="ownership-result__heading">
        <div>
          <p className="section-label">Ownership-only provisional analysis</p>
          <h3>{root?.display_name ?? "Ownership source result"}</h3>
          <span>
            {record.provider_name ?? "Provider pending"} / {record.provider_environment ?? "Pending"}
          </span>
        </div>
        <strong>{record.state}</strong>
      </div>
      <p className="synthetic-notice">
        This Phase 04 result evaluates ownership only. It is not a legal/controller,
        compliance, GoldTier, or Ready-for-Approval determination.
      </p>
      <div className="provisional-threshold">
        <strong>
          {ownershipPercent(record.threshold_percent)} project-defined provisional threshold
        </strong>
        <span>Inclusive comparator: aggregated ownership ≥ threshold · PENDING Q-004</span>
      </div>

      {record.error && (
        <div className="request-error" role="alert">
          {record.error.code}: {record.error.message}
        </div>
      )}
      {record.issues.length > 0 && (
        <div className="ownership-warnings" role="alert">
          <strong>⚠️ Human review required — calculation is not definitive.</strong>
          <ul>
            {record.issues.map((issue) => (
              <li key={`${issue.code}-${issue.affected_party_ids.join("-")}`}>
                <strong>{issue.code}</strong> {issue.message}
              </li>
            ))}
          </ul>
        </div>
      )}

      {record.relationships.length > 0 && (
        <>
          <SimpleOwnershipGraph record={record} />
          
          <div className="ownership-relationships">
            <h4>Detailed ownership structure</h4>
            <div className="ownership-table" role="table" aria-label="Ownership relationships">
              {record.relationships.map((relationship) => (
                <div className="ownership-row" role="row" key={relationship.relationship_id}>
                  <div role="cell">
                    <strong>{parties.get(relationship.parent_party_id)?.display_name}</strong>
                    <span>Owned party</span>
                  </div>
                  <div className="ownership-edge" role="cell">
                    {ownershipPercent(relationship.ownership_percent)} →
                  </div>
                  <div role="cell">
                    <strong>{parties.get(relationship.child_party_id)?.display_name}</strong>
                    <span>
                      {parties.get(relationship.child_party_id)?.party_type === "NATURAL_PERSON"
                        ? "Natural-person owner"
                        : "Legal-entity owner"}
                    </span>
                  </div>
                  <div role="cell">
                    <strong>
                      {relationship.provenance.provider} / {relationship.provenance.environment}
                    </strong>
                    <span>Sourced {formatTimestamp(relationship.provenance.sourced_at)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {record.candidates.length > 0 && (
        <div className="ownership-candidates">
          <h4>Natural-person ownership threshold results</h4>
          {record.candidates.map((candidate) => (
            <OwnershipCandidateCard candidate={candidate} key={candidate.party.party_id} />
          ))}
        </div>
      )}
    </article>
  );
}

export function OwnershipPanel({
  caseData,
  configuredThreshold,
  onMutationStart,
  onMutationSettled,
}: {
  caseData: OnboardingCase;
  configuredThreshold: string;
  onMutationStart: () => void;
  onMutationSettled: () => Promise<void>;
}) {
  const [scenario, setScenario] = useState<MockOwnershipScenario>("DIRECT_OWNER");
  const [record, setRecord] = useState<OwnershipAnalysisRecord | null>(null);
  const [isBusy, setIsBusy] = useState(false);
  const [ownershipError, setOwnershipError] = useState<string | null>(null);

  useEffect(() => {
    void fetchOwnership(caseData.case_id)
      .then(setRecord)
      .catch(() => setOwnershipError("Ownership analysis is unavailable."));
  }, [caseData.case_id]);

  async function refreshAfterFailure() {
    try {
      setRecord(await fetchOwnership(caseData.case_id));
    } catch {
      // Keep the sanitized request failure visible when refresh is unavailable.
    }
  }

  async function handleLoad() {
    setIsBusy(true);
    setOwnershipError(null);
    try {
      setRecord(
        await runEvidenceMutation(
          onMutationStart,
          () => loadMockOwnership(caseData.case_id, scenario),
          onMutationSettled,
        ),
      );
    } catch (error) {
      setOwnershipError(error instanceof Error ? error.message : "Ownership loading failed.");
      await refreshAfterFailure();
    } finally {
      setIsBusy(false);
    }
  }

  async function handleAnalyze() {
    setIsBusy(true);
    setOwnershipError(null);
    try {
      setRecord(
        await runEvidenceMutation(
          onMutationStart,
          () => analyzeOwnership(caseData.case_id),
          onMutationSettled,
        ),
      );
    } catch (error) {
      setOwnershipError(error instanceof Error ? error.message : "Ownership analysis failed.");
      await refreshAfterFailure();
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <section className="ownership-card" aria-labelledby="ownership-heading">
      <div>
        <p className="section-label">Phase 04 case sub-workflow</p>
        <h2 id="ownership-heading">Ownership &amp; UBO</h2>
        <p>
          Load a fictional related-party graph, calculate direct and indirect paths, and
          review ownership-based provisional candidates without changing the onboarding case.
        </p>
      </div>
      {!record && (
        <div className="ownership-controls">
          <label htmlFor="ownership-scenario">Synthetic Mock ownership scenario</label>
          <select
            id="ownership-scenario"
            value={scenario}
            onChange={(event) => setScenario(event.target.value as MockOwnershipScenario)}
          >
            <option value="DIRECT_OWNER">Direct natural-person owners</option>
            <option value="INDIRECT_OWNER">Indirect owners through a holding company</option>
            <option value="MULTIPLE_PATHS">One person through multiple paths</option>
            <option value="BELOW_THRESHOLD">Owners below threshold</option>
            <option value="INCOMPLETE_CHAIN">Incomplete legal-entity chain</option>
            <option value="CYCLE">Circular ownership data</option>
            <option value="PROVIDER_FAILURE">Provider failure</option>
          </select>
          <button type="button" disabled={isBusy} onClick={() => void handleLoad()}>
            {isBusy ? "Loading ownership source..." : "Load synthetic ownership"}
          </button>
          <p className="input-help">
            Default threshold: {ownershipPercent(configuredThreshold)} — project-defined,
            inclusive, and pending sponsor confirmation Q-004.
          </p>
        </div>
      )}
      {record?.state === "LOADED" && (
        <div className="ownership-controls">
          <p>Source validation passed. Run the deterministic calculation engine.</p>
          <button type="button" disabled={isBusy} onClick={() => void handleAnalyze()}>
            {isBusy ? "Calculating bounded ownership paths..." : "Analyze ownership paths"}
          </button>
        </div>
      )}
      {ownershipError && (
        <div className="request-error" role="alert">
          {ownershipError}
        </div>
      )}
      {record && <OwnershipSummary record={record} />}
    </section>
  );
}

export function ClmJourney({
  summary,
  onUpdate,
  onRefresh,
}: {
  summary: ClmCaseSummary;
  onUpdate?: (summary: ClmCaseSummary) => void;
  onRefresh?: () => Promise<void>;
}) {
  const [isBusy, setIsBusy] = useState(false);
  const [clmError, setClmError] = useState<string | null>(null);
  const stages = [
    ["Registry", summary.readiness.registry.status],
    ["Document Review", summary.readiness.document.status],
    ["Ownership & UBO", summary.readiness.ownership.status],
    ["Readiness", summary.status],
    ["Mock GoldTier", summary.readiness.goldtier.status],
  ];

  async function run(
    operation: () => Promise<ClmCaseSummary>,
    refreshOnError = false,
  ) {
    setIsBusy(true);
    setClmError(null);
    try {
      onUpdate?.(await operation());
    } catch (error) {
      setClmError(error instanceof Error ? error.message : "CLM operation failed.");
      if (refreshOnError) await onRefresh?.();
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <section className="clm-card" aria-labelledby="clm-heading">
      <div className="clm-heading">
        <div>
          <p className="section-label">Phase 05 integrated orchestration</p>
          <h2 id="clm-heading">Unified CLM journey</h2>
          <p>
            Backend readiness is authoritative and is revalidated immediately before
            the serialized Mock GoldTier submission.
          </p>
        </div>
        <strong className={`clm-overall clm-overall--${summary.status}`}>
          {summary.status}
        </strong>
      </div>

      <ol className="clm-stepper" aria-label="CLM stages">
        {stages.map(([label, stageStatus], index) => (
          <li key={label} data-stage-status={stageStatus}>
            <span>{index + 1}</span>
            <div><strong>{label}</strong><small>{stageStatus}</small></div>
          </li>
        ))}
      </ol>

      <div className="clm-grid">
        <article>
          <h3>Mock-submission blockers</h3>
          {summary.readiness.blockers.length ? (
            <ul className="clm-list clm-list--blockers">
              {summary.readiness.blockers.map((blocker) => <li key={blocker}>{blocker}</li>)}
            </ul>
          ) : <p className="ready-copy">No current Mock-submission blockers.</p>}
        </article>
        <article>
          <h3>Real-integration warnings</h3>
          <ul className="clm-list clm-list--warnings">
            {summary.readiness.warnings.map((warning) => <li key={warning}>{warning}</li>)}
          </ul>
        </article>
      </div>

      <article className="submission-plan">
        <div>
          <p className="section-label">Safe pre-submission plan</p>
          <h3>GoldTier base operations · {summary.submission_plan.environment}</h3>
        </div>
        <ol>
          {summary.submission_plan.base_operations.map((operation) => (
            <li key={operation}>{operation}</li>
          ))}
        </ol>
        <dl>
          <div><dt>Existing match</dt><dd>{summary.submission_plan.match_found_behavior}</dd></div>
          <div><dt>Related-party integration</dt><dd>{summary.submission_plan.related_party_integration}</dd></div>
          <div><dt>Real approval transition</dt><dd>{summary.submission_plan.real_ready_for_approval}</dd></div>
        </dl>
      </article>

      <div className="clm-actions">
        <button
          className="button-secondary"
          type="button"
          disabled={isBusy || summary.submission !== null}
          onClick={() => void run(() => evaluateClmReadiness(summary.case.case_id))}
        >
          {isBusy ? "Checking authoritative evidence..." : "Evaluate current readiness"}
        </button>
        <button
          type="button"
          disabled={isBusy || summary.status !== "READY_FOR_MOCK_SUBMISSION"}
          onClick={() =>
            void run(() => submitClmCase(summary.case.case_id), true)
          }
        >
          {summary.status === "MOCK_GOLDTIER_SUBMITTED"
            ? "Mock GoldTier submitted"
            : "Submit to Mock GoldTier"}
        </button>
      </div>

      {clmError && <div className="request-error" role="alert">{clmError}</div>}
      {summary.submission && (
        <div className="mock-submission-result" role="status">
          <strong>{summary.status}</strong>
          <span>Submission {summary.submission.submission_id}</span>
          <span>{summary.submission.document_reference_count} reviewed document reference(s)</span>
          <span>
            Related-party write: {summary.related_party_preparation?.write_status ?? "NOT_PREPARED"}
          </span>
        </div>
      )}

      <article className="clm-timeline">
        <h3>Unified safe timeline</h3>
        <ol>
          {summary.timeline.map((event) => (
            <li key={event.sequence}>
              <strong>{event.event_type}</strong>
              <span>{event.status}</span>
              <p>{event.message}</p>
            </li>
          ))}
        </ol>
      </article>
    </section>
  );
}

export function ClmRefreshingState() {
  return (
    <section className="clm-card" aria-live="polite" aria-label="CLM readiness refresh">
      <p className="section-label">Phase 05 integrated orchestration</p>
      <h2>Refreshing authoritative CLM readiness</h2>
      <p>Evidence changed. Submission remains disabled until the backend summary returns.</p>
      <button type="button" disabled>Submit to Mock GoldTier</button>
    </section>
  );
}

const AUTOMATION_STAGES = [
  ["REGISTRY", "Registry"],
  ["DOCUMENT", "Document verification"],
  ["OWNERSHIP", "Ownership & UBO"],
  ["READINESS", "Readiness"],
  ["MOCK_GOLDTIER", "Mock GoldTier"],
] as const;

export function shouldPollAutomation(status: ZeroTouchCaseSummary["status"]): boolean {
  return status === "RUNNING" || status === "RESUMING";
}

export function automationStageState(
  summary: ZeroTouchCaseSummary,
  stage: (typeof AUTOMATION_STAGES)[number][0],
): string {
  if (summary.completed_stages.includes(stage)) return "Completed";
  if (summary.current_stage !== stage) return "Pending";
  if (summary.status === "PENDING_INPUTS") return "Awaiting input";
  if (summary.status === "WAITING_FOR_REVIEW") return "Review required";
  if (summary.status === "TECHNICAL_FAILURE") return "Failed";
  if (summary.status === "RESUMING") return "Resuming";
  if (summary.status === "RECOVERY_PENDING") return "Finalization recovery pending";
  return "Processing";
}

export function OnboardingProgress({ summary }: { summary: ZeroTouchCaseSummary }) {
  return (
    <section className="automation-card" aria-labelledby="progress-heading" aria-live="polite">
      <div className="automation-heading">
        <div>
          <p className="section-label">Onboarding progress</p>
          <h2 id="progress-heading">{summary.case.entity?.legal_name ?? summary.case.requested_uen}</h2>
        </div>
        <span className={`automation-status automation-status--${summary.status.toLowerCase()}`}>
          {summary.status.replaceAll("_", " ")}
        </span>
      </div>
      <JurisdictionDecision caseData={summary.case} />
      <RegistryAcquisitionPanel caseData={summary.case} />
      <ol className="automation-steps">
        {AUTOMATION_STAGES.map(([stage, label]) => {
          const complete = summary.completed_stages.includes(stage);
          const current = summary.current_stage === stage;
          const state = automationStageState(summary, stage);
          return (
            <li key={stage} className={complete ? "is-complete" : current ? "is-current" : ""}>
              <span aria-hidden="true" />
              <strong>{label}</strong>
              <small>{state}</small>
            </li>
          );
        })}
      </ol>
      <div className="touch-metrics" aria-label="Onboarding metrics">
        <div><strong>{summary.metrics.automated_stages_completed}</strong><span>Automated stages</span></div>
        <div><strong>{summary.metrics.human_interventions}</strong><span>Human interventions</span></div>
        <div><strong>{summary.metrics.exceptions_resolved}</strong><span>Exceptions resolved</span></div>
        <div>
          <strong>{summary.metrics.total_duration_ms === null ? "—" : `${summary.metrics.total_duration_ms} ms`}</strong>
          <span>Local run duration</span>
        </div>
      </div>
      {summary.status === "COMPLETED" && (
        <div className="automation-complete" role="status">
          <strong>Mock submission completed</strong>
          <span>Zero human interventions means deterministic processing only—not approval.</span>
        </div>
      )}
    </section>
  );
}

export function JurisdictionDecision({ caseData }: { caseData: OnboardingCase }) {
  const resolution = caseData.jurisdiction_resolution;
  const route = caseData.registry_route;
  if (!resolution) return null;
  return (
    <section className="jurisdiction-decision" aria-label="Jurisdiction and registry decision">
      <div>
        <span>Jurisdiction decision</span>
        <strong>
          {resolution.resolved_jurisdiction ?? resolution.status.replaceAll("_", " ")}
        </strong>
      </div>
      <div>
        <span>Registry provider</span>
        <strong>
          {route?.provider
            ?? (route?.status === "PROVIDER_NOT_IMPLEMENTED"
              ? "Provider not implemented"
              : "Not selected")}
        </strong>
      </div>
      <div className="jurisdiction-observations">
        <span>Source observations</span>
        {resolution.observations.length === 0 ? (
          <strong>None supplied or inferred</strong>
        ) : (
          <ul>
            {resolution.observations.map((observation, index) => (
              <li key={`${observation.source}-${index}`}>
                <strong>{observation.jurisdiction}</strong>
                <span>{observation.source.replaceAll("_", " ")}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

export function RegistryAcquisitionPanel({ caseData }: { caseData: OnboardingCase }) {
  const acquisition = caseData.registry_acquisition;
  if (!acquisition) return null;
  const environment = acquisition.operation_results.find(
    (result) => result.provenance !== null,
  )?.provenance?.environment ?? caseData.entity?.source.environment ?? "MOCK";
  const labels: Record<(typeof acquisition.operation_results)[number]["operation"], string> = {
    ENTITY_PROFILE: "Entity Profile",
    OFFICERS: "Officers",
    OWNERSHIP_PARTIES: "Ownership Parties",
    RELATIONSHIPS: "Relationships",
  };

  return (
    <section className="registry-acquisition" aria-label="ACRA registry acquisition">
      <div className="registry-acquisition__heading">
        <div>
          <span>ACRA Registry Acquisition</span>
          <strong>{acquisition.status}</strong>
        </div>
        <p>
          Project-owned synthetic {titleCaseEnvironment(environment)} contract — not
          verified live ACRA.
        </p>
      </div>
      <ul className="registry-acquisition__operations">
        {acquisition.operation_results.map((result) => (
          <li key={result.operation}>
            <span>{labels[result.operation]}</span>
            <strong>{result.status.replaceAll("_", " ")}</strong>
            <small>{result.record_count} record{result.record_count === 1 ? "" : "s"}</small>
            {result.error && <small>{result.error.code}</small>}
          </li>
        ))}
      </ul>
      {acquisition.issues.length > 0 && (
        <div className="registry-acquisition__issues" role="status">
          {acquisition.issues.map((issue) => (
            <p key={issue.code}><strong>{issue.code}</strong> — {issue.message}</p>
          ))}
        </div>
      )}
      {(acquisition.officers.length > 0 || acquisition.ownership_parties.length > 0) && (
        <div className="registry-acquisition__evidence">
          <div>
            <span>Normalized officers</span>
            <strong>{acquisition.officers.map((officer) => officer.name).join(", ") || "None"}</strong>
          </div>
          <div>
            <span>Normalized ownership parties</span>
            <strong>{acquisition.ownership_parties.map((party) => party.name).join(", ") || "None"}</strong>
          </div>
        </div>
      )}
    </section>
  );
}

export type JurisdictionSelection = "" | "SG" | "AU" | "MY" | "HK";

export function JurisdictionSelector({
  value,
  onChange,
}: {
  value: JurisdictionSelection;
  onChange: (value: JurisdictionSelection) => void;
}) {
  return (
    <>
      <label htmlFor="zero-touch-country">Country / jurisdiction (optional)</label>
      <select
        id="zero-touch-country"
        value={value}
        onChange={(event) => onChange(event.target.value as JurisdictionSelection)}
      >
        <option value="">Not specified</option>
        <option value="SG">Singapore</option>
        <option value="AU">Australia — provider not implemented</option>
        <option value="MY">Malaysia — provider not implemented</option>
        <option value="HK">Hong Kong — provider not implemented</option>
      </select>
      <p className="input-help">
        Singapore routes to ACRA. Other recognised jurisdictions stop safely in this POC.
      </p>
    </>
  );
}

export function SponsorCaseSummary({
  summary,
  onOpenReview,
}: {
  summary: ZeroTouchCaseSummary;
  onOpenReview?: () => void;
}) {
  const activeBlockers: string[] = [];
  const seenBlockers = new Set<string>();
  summary.active_exceptions.forEach((exception) => {
    exception.blocker_codes.forEach((blockerCode) => {
      if (!seenBlockers.has(blockerCode)) {
        seenBlockers.add(blockerCode);
        activeBlockers.push(blockerCode);
      }
    });
  });

  if (activeBlockers.length === 0 && summary.technical_failure) {
    activeBlockers.push(summary.technical_failure.code);
  }
  const ownershipCandidates = summary.clm.related_party_preparation?.provisional_candidate_count;
  const targetOutcome = summary.metrics.final_outcome
    ?? summary.clm.error?.code
    ?? (summary.current_stage === "MOCK_GOLDTIER" ? "In progress" : "Not reached");

  return (
    <section className="executive-summary" aria-labelledby="executive-summary-heading">
      <div className="automation-heading">
        <div>
          <p className="section-label">Sponsor case summary</p>
          <h2 id="executive-summary-heading">
            {summary.case.entity?.legal_name ?? summary.case.requested_uen}
          </h2>
        </div>
        <strong>{summary.status.replaceAll("_", " ")}</strong>
      </div>
      <dl className="executive-summary__grid">
        <div><dt>UEN</dt><dd>{summary.case.requested_uen}</dd></div>
        <div>
          <dt>Active blockers</dt>
          <dd>
            {activeBlockers.length === 0 ? "None" : (
              <ol className="blocker-list blocker-list--summary">
                {activeBlockers.map((blockerCode) => (
                  <li key={blockerCode}>
                    <span>{blockerCode.replaceAll("_", " ")}</span>
                    <code>{blockerCode}</code>
                  </li>
                ))}
              </ol>
            )}
          </dd>
        </div>
        <div><dt>Human interventions after Start</dt><dd>{summary.metrics.human_interventions}</dd></div>
        <div><dt>Provisional UBO candidates</dt><dd>{ownershipCandidates ?? "Pending"}</dd></div>
        <div><dt>Mock target outcome</dt><dd>{targetOutcome.replaceAll("_", " ")}</dd></div>
        <div>
          <dt>Elapsed local POC time</dt>
          <dd>{summary.metrics.total_duration_ms === null ? "In progress" : `${summary.metrics.total_duration_ms} ms`}</dd>
        </div>
      </dl>
      <div className="executive-summary__warnings">
        <strong>Outstanding warnings</strong>
        <ul>
          {summary.clm.readiness.warnings.map((warning) => (
            <li key={warning}>{warning.replaceAll("_", " ")}</li>
          ))}
        </ul>
      </div>
      {summary.status === "WAITING_FOR_REVIEW" && onOpenReview && (
        <button className="review-queue-link" type="button" onClick={onOpenReview}>
          Review {summary.active_exceptions.length} active exception{summary.active_exceptions.length === 1 ? "" : "s"}
        </button>
      )}
    </section>
  );
}

export function evidenceRevision(summary: ZeroTouchCaseSummary): string {
  return `${summary.case.case_id}:${summary.version}:${summary.updated_at}`;
}

export function LocalReviewerWorkbench({ summary }: { summary: ZeroTouchCaseSummary }) {
  const [note, setNote] = useState("");
  const [question, setQuestion] = useState("");
  const [questions, setQuestions] = useState<string[]>([]);
  const [assignedToMe, setAssignedToMe] = useState(false);
  const reviewRequired = summary.status === "WAITING_FOR_REVIEW";
  const queueLabel = reviewRequired
    ? "Needs review"
    : summary.status === "COMPLETED"
      ? "Complete"
      : summary.status.replaceAll("_", " ");

  function addQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion) return;
    setQuestions((current) => [...current, trimmedQuestion]);
    setQuestion("");
  }

  return (
    <section className="reviewer-workbench" aria-labelledby="reviewer-workbench-heading">
      <div className="reviewer-workbench__heading">
        <div>
          <p className="section-label">Local reviewer workbench</p>
          <h2 id="reviewer-workbench-heading">Review queue</h2>
          <p>Session-only queue for the currently open case. It is not an authenticated account or durable work queue.</p>
        </div>
        <span className={`queue-status queue-status--${reviewRequired ? "review" : "normal"}`}>
          {queueLabel}
        </span>
      </div>
      <div className="reviewer-workbench__grid">
        <article className="queue-item queue-item--active">
          <span>{assignedToMe ? "Assigned to you · this session" : "Unassigned current case"}</span>
          <h3>{summary.case.entity?.legal_name ?? summary.case.requested_uen}</h3>
          <dl>
            <div><dt>UEN</dt><dd>{summary.case.requested_uen}</dd></div>
            <div><dt>Current stage</dt><dd>{summary.current_stage.replaceAll("_", " ")}</dd></div>
            <div><dt>Last update</dt><dd>{formatTimestamp(summary.updated_at)}</dd></div>
          </dl>
          <button
            className="queue-assign-button"
            type="button"
            disabled={assignedToMe}
            onClick={() => setAssignedToMe(true)}
          >
            {assignedToMe ? "Assigned to you" : "Assign to me"}
          </button>
          <p className="input-help">Assignment is session-only in this local POC and is cleared on refresh.</p>
        </article>
        <article className="reviewer-notes">
          <h3>Reviewer workspace</h3>
          <label htmlFor="reviewer-note">Safe internal note</label>
          <textarea
            id="reviewer-note"
            value={note}
            maxLength={500}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Record a non-sensitive follow-up or decision rationale"
          />
          <span className="input-help">This note is held in memory and is cleared on refresh.</span>
        </article>
      </div>
      <div className="clarification-panel">
        <div>
          <h3>Client clarification questions</h3>
          <p>Use this draft list to capture missing information before a future client-response workflow is connected.</p>
        </div>
        <form onSubmit={addQuestion} className="form-row">
          <label className="sr-only" htmlFor="clarification-question">New clarification question</label>
          <input
            id="clarification-question"
            value={question}
            maxLength={240}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="What should the client clarify?"
          />
          <button type="submit" disabled={!question.trim()}>Add question</button>
        </form>
        {questions.length > 0 && (
          <ol className="clarification-list">
            {questions.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
          </ol>
        )}
      </div>
    </section>
  );
}

type AppTab = "dashboard" | "start" | "review" | "logs" | "account";

export function WorkspaceTabs({ activeTab, onChange }: { activeTab: AppTab; onChange: (tab: AppTab) => void }) {
  const tabs: Array<[AppTab, string]> = [
    ["dashboard", "Dashboard"],
    ["start", "Start onboarding"],
    ["review", "Review"],
    ["logs", "Logs"],
    ["account", "Account info"],
  ];
  return (
    <nav className="workspace-tabs" aria-label="Main workspace">
      {tabs.map(([tab, label]) => (
        <button
          key={tab}
          className={activeTab === tab ? "workspace-tab workspace-tab--active" : "workspace-tab"}
          type="button"
          aria-current={activeTab === tab ? "page" : undefined}
          onClick={() => onChange(tab)}
        >
          {label}
        </button>
      ))}
    </nav>
  );
}

export function DashboardSnapshot({ summary }: { summary: ZeroTouchCaseSummary | null }) {
  const metrics = summary
    ? [
        [summary.current_stage.replaceAll("_", " "), "Current stage"],
        [summary.active_exceptions.length, "Open exceptions"],
        [summary.metrics.human_interventions, "Human interventions"],
        [summary.metrics.total_duration_ms === null ? "In progress" : `${summary.metrics.total_duration_ms} ms`, "Local run time"],
      ]
    : [["—", "Current stage"], [0, "Open exceptions"], [0, "Human interventions"], ["—", "Local run time"]];
  return (
    <section className="dashboard-snapshot" aria-labelledby="dashboard-snapshot-heading">
      <div>
        <p className="section-label">Current session overview</p>
        <h2 id="dashboard-snapshot-heading">Work at a glance</h2>
        <p>Case health for the currently selected local case.</p>
      </div>
      <div className="dashboard-metrics">
        {metrics.map(([value, label]) => <div key={label}><strong>{value}</strong><span>{label}</span></div>)}
      </div>
    </section>
  );
}

export function CasePortfolio({
  cases,
  onOpen,
}: {
  cases: ZeroTouchCaseListItem[];
  onOpen: (caseId: string) => void;
}) {
  return (
    <section className="case-portfolio" aria-labelledby="case-portfolio-heading">
      <p className="section-label">Process-local case history</p>
      <h2 id="case-portfolio-heading">Recent CLM cases</h2>
      <p className="process-local-notice">
        Cases are retained only for the current backend process. Restarting the local
        POC clears this history.
      </p>
      {cases.length === 0 ? (
        <p>No CLM cases have been created in this backend process.</p>
      ) : (
        <div className="case-table" role="table" aria-label="Recent CLM cases">
          <div className="case-table__header" role="row">
            <strong role="columnheader">Company</strong>
            <strong role="columnheader">UEN</strong>
            <strong role="columnheader">Stage</strong>
            <strong role="columnheader">Status</strong>
            <strong role="columnheader">Updated</strong>
            <span role="columnheader">Action</span>
          </div>
          {cases.map((item) => (
            <div className="case-table__row" role="row" key={item.case_id}>
              <span role="cell">{item.legal_name ?? "Registry identity pending"}</span>
              <code role="cell">{item.requested_uen}</code>
              <span role="cell">{item.current_stage.replaceAll("_", " ")}</span>
              <span role="cell">{item.status.replaceAll("_", " ")}</span>
              <span role="cell">{formatTimestamp(item.updated_at)}</span>
              <button type="button" onClick={() => onOpen(item.case_id)}>View case</button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export function ReviewQueue({
  cases,
  selectedCaseId,
  onOpen,
}: {
  cases: ZeroTouchCaseListItem[];
  selectedCaseId?: string;
  onOpen: (caseId: string) => void;
}) {
  return (
    <section className="review-queue" aria-labelledby="review-queue-heading">
      <p className="section-label">Backend-authored process-local queue</p>
      <h2 id="review-queue-heading">Cases waiting for review</h2>
      <p>Queue status is authoritative for the current backend process only; assignment remains session-only.</p>
      {cases.length === 0 ? <p>No cases currently require review.</p> : (
        <div className="review-queue__items">
          {cases.map((item) => (
            <button
              type="button"
              key={item.case_id}
              className={selectedCaseId === item.case_id ? "review-queue__item review-queue__item--active" : "review-queue__item"}
              onClick={() => onOpen(item.case_id)}
            >
              <strong>{item.legal_name ?? item.requested_uen}</strong>
              <span>UEN {item.requested_uen}</span>
              <span>Case {item.case_id}</span>
              <span>{item.current_stage.replaceAll("_", " ")} · {item.active_exception_count} active blocker(s)</span>
              <span>Updated {formatTimestamp(item.updated_at)}</span>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

export function StartProgressPanel({
  progress,
  summary,
  isSubmitting,
  onViewCase,
  onOpenReview,
  onRetry,
  onStartAnother,
}: {
  progress: StartProgress;
  summary: ZeroTouchCaseSummary | null;
  isSubmitting: boolean;
  onViewCase: () => void;
  onOpenReview: () => void;
  onRetry: () => void;
  onStartAnother: () => void;
}) {
  if (progress.stage === "idle") return null;
  return (
    <section className={`start-progress start-progress--${progress.stage}`} role="status" aria-live="polite">
      <strong>{progress.message}</strong>
      {summary && (
        <>
          <h3>CLM onboarding created</h3>
          <dl>
            <div><dt>Case ID</dt><dd><code>{summary.case.case_id}</code></dd></div>
            <div><dt>UEN</dt><dd>{summary.case.requested_uen}</dd></div>
            <div><dt>Status</dt><dd>{summary.status.replaceAll("_", " ")}</dd></div>
          </dl>
          {progress.failedFile && <p>Upload failed safely for {progress.failedFile}. Successfully received documents remain attached.</p>}
          <div className="start-progress__actions">
            <button type="button" onClick={onViewCase}>View case</button>
            {summary.status === "WAITING_FOR_REVIEW" && (
              <button type="button" onClick={onOpenReview}>Open Review</button>
            )}
            {progress.stage === "failed" && summary.status === "PENDING_INPUTS" && (
              <button type="button" disabled={isSubmitting} onClick={onRetry}>Retry this case</button>
            )}
            {(progress.stage === "completed" || progress.stage === "waiting") && (
              <button type="button" disabled={isSubmitting} onClick={onStartAnother}>Start another case</button>
            )}
          </div>
        </>
      )}
    </section>
  );
}

export function CaseIdentityStrip({ summary }: { summary: ZeroTouchCaseSummary }) {
  return (
    <section className="case-identity-strip" aria-label="Current case identity">
      <div><span>Case</span><strong>{summary.case.entity?.legal_name ?? summary.case.requested_uen}</strong></div>
      <div><span>UEN</span><strong>{summary.case.requested_uen}</strong></div>
      <div><span>Last updated</span><strong>{formatTimestamp(summary.updated_at)}</strong></div>
      <div><span>Execution</span><strong>Local synthetic POC</strong></div>
    </section>
  );
}

export function AccountPlaceholder() {
  return (
    <section className="workspace-placeholder" aria-labelledby="account-heading">
      <p className="section-label">Account</p>
      <h2 id="account-heading">Local demo operator</h2>
      <p>Authentication, reviewer roles, profile management, and access controls are not connected yet.</p>
      <span className="placeholder-badge">Authentication pending</span>
    </section>
  );
}

export function SponsorDocumentEvidenceView({ documents }: { documents: DocumentProcessingRecord[] }) {
  if (documents.length === 0) return null;
  return (
    <section className="document-evidence-card" aria-labelledby="document-evidence-heading">
      <p className="section-label">Document stage evidence</p>
      <h2 id="document-evidence-heading">What each supplied document contributed</h2>
      {documents.map((document) => (
        <details key={document.document_id} open={!document.superseded_by_document_id}>
          <summary>{document.display_name} — {document.superseded_by_document_id ? "SUPERSEDED" : "CURRENT"} — {document.state.replaceAll("_", " ")}</summary>
          <p>Project-defined POC extraction confidence; not an AI or sponsor-approved score.</p>
          <div className="evidence-comparison" role="table" aria-label={`${document.display_name} document comparison`}>
            {document.fields.map((field) => (
              <div key={field.field_key} role="row" className={field.comparison_status === "MATCH" ? "" : "evidence-comparison--attention"}>
                <strong role="cell">{fieldLabel(field.field_key)}</strong>
                <span role="cell"><small>Registry</small>{field.canonical_value ?? "Not available"}</span>
                <span role="cell"><small>Document</small>{field.original_extracted_value ?? "Not extracted"}</span>
                <span role="cell"><small>POC confidence</small>{confidencePercent(field.confidence)} · {field.comparison_status.replaceAll("_", " ")}</span>
              </div>
            ))}
          </div>
        </details>
      ))}
    </section>
  );
}

export function SponsorDocumentEvidence({ summary }: { summary: ZeroTouchCaseSummary }) {
  const caseId = summary.case.case_id;
  const revision = evidenceRevision(summary);
  const [documents, setDocuments] = useState<DocumentProcessingRecord[]>([]);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    let current = true;
    void fetchDocuments(caseId)
      .then((records) => {
        if (current) {
          setUnavailable(false);
          setDocuments(records);
        }
      })
      .catch(() => {
        if (current) setUnavailable(true);
      });
    return () => { current = false; };
  }, [caseId, revision]);

  if (unavailable) return null;
  return <SponsorDocumentEvidenceView documents={documents} />;
}

function reconciliationSourceValue(
  discrepancy: ReconciliationDiscrepancy,
  source: "REGISTRY" | "DOCUMENT_IDP",
): string {
  const values = discrepancy.observations
    .filter((item) => item.source_kind === source)
    .map((item) => item.normalized_value ?? "Not available");
  return values.length ? values.join(" · ") : "Not observed";
}

export function ReconciliationPanel({
  summary,
  isResolving = false,
  onResolve,
  onReplace,
}: {
  summary: ZeroTouchCaseSummary;
  isResolving?: boolean;
  onResolve?: (
    discrepancy: ReconciliationDiscrepancy,
    action: ReconciliationDecisionAction,
  ) => void;
  onReplace?: (documentId: string, eventCount: number, file: File) => void;
}) {
  const reconciliation = summary.reconciliation;
  const [replacementFile, setReplacementFile] = useState<File | null>(null);
  const [replacementDocumentId, setReplacementDocumentId] = useState<string>("");
  if (!reconciliation) return null;
  const discrepancies = new Map(
    reconciliation.discrepancies.map((item) => [item.discrepancy_id, item]),
  );
  const selectedReplacementId = replacementDocumentId || reconciliation.source_document_ids.at(-1);
  const selectedReplacementIndex = selectedReplacementId
    ? reconciliation.source_document_ids.indexOf(selectedReplacementId)
    : -1;
  const currentDocumentVersion = selectedReplacementIndex >= 0
    ? reconciliation.source_document_event_counts[selectedReplacementIndex]
    : undefined;

  return (
    <section className="reconciliation-panel" aria-labelledby="reconciliation-heading">
      <p className="section-label">Multi-source reconciliation</p>
      <div className="reconciliation-heading-row">
        <h2 id="reconciliation-heading">Registry and document observations</h2>
        <span className={`reconciliation-status reconciliation-status--${reconciliation.status}`}>
          {reconciliation.status.replaceAll("_", " ")}
        </span>
      </div>
      <p>
        Neither source is authoritative by default. Values remain separate until an
        explicitly advertised backend action records a decision.
      </p>
      <div className="reconciliation-grid" role="table" aria-label="Field reconciliation">
        <div className="reconciliation-grid__header" role="row">
          <strong role="columnheader">Field</strong>
          <strong role="columnheader">Registry value</strong>
          <strong role="columnheader">Document value</strong>
          <strong role="columnheader">Outcome / decision</strong>
        </div>
        {reconciliation.fields.map((field) => {
          const discrepancy = field.discrepancy_id
            ? discrepancies.get(field.discrepancy_id)
            : undefined;
          const registry = field.observations
            .filter((item) => item.source_kind === "REGISTRY")
            .map((item) => item.normalized_value ?? "Not available")
            .join(" · ");
          const document = field.observations
            .filter((item) => item.source_kind === "DOCUMENT_IDP")
            .map((item) => item.normalized_value ?? "Not available")
            .join(" · ");
          return (
            <div className="reconciliation-grid__row" role="row" key={field.field_name}>
              <strong role="cell">{fieldLabel(field.field_name)}</strong>
              <span role="cell"><small>Registry observation</small>{registry || "Not observed"}</span>
              <span role="cell"><small>Document observation</small>{document || "Not observed"}</span>
              <span role="cell">
                <span className={`comparison-badge comparison-badge--${field.outcome}`}>
                  {field.outcome.replaceAll("_", " ")}
                </span>
                {discrepancy?.decision && (
                  <small>
                    Decision: {discrepancy.decision.action.replaceAll("_", " ")} · {formatTimestamp(discrepancy.decision.decided_at)}
                  </small>
                )}
              </span>
            </div>
          );
        })}
      </div>
      {reconciliation.discrepancies
        .filter((item) => item.status !== "CANCELLED")
        .map((discrepancy) => (
          <article className="reconciliation-discrepancy" key={discrepancy.discrepancy_id}>
            <h3>{fieldLabel(discrepancy.field_name)} — {discrepancy.outcome.replaceAll("_", " ")}</h3>
            <p>
              Registry: {reconciliationSourceValue(discrepancy, "REGISTRY")} · Document: {reconciliationSourceValue(discrepancy, "DOCUMENT_IDP")}
            </p>
            <p className="reconciliation-provenance">
              {discrepancy.observations.map((observation) => (
                <span key={observation.observation_id}>
                  {observation.document_display_name ?? observation.source_kind.replaceAll("_", " ")} · {observation.source_system ?? "Current case"} · {observation.environment ?? "Local"} · {observation.validity}
                </span>
              ))}
            </p>
            {discrepancy.status === "OPEN" && onResolve && (
              <div className="exception-actions">
                {discrepancy.allowed_actions.map((action) => (
                  <button
                    key={action}
                    type="button"
                    disabled={isResolving}
                    onClick={() => onResolve(discrepancy, action)}
                  >
                    {action === "KEEP_REGISTRY_VALUE" ? "Keep registry value" : "Use document value"}
                  </button>
                ))}
                {discrepancy.allowed_actions.length === 0 && (
                  <p className="warning-notice">Replacement evidence is required; no value-selection action is authorized.</p>
                )}
              </div>
            )}
            {discrepancy.decision && (
              <p className="decision-summary">
                Resolved by explicit POC operator action: {discrepancy.decision.action.replaceAll("_", " ")}. No reviewer identity or compliance authority is claimed.
              </p>
            )}
          </article>
        ))}
      {onReplace && selectedReplacementId && currentDocumentVersion && reconciliation.status === "REVIEW_REQUIRED" && (
        <div className="replacement-section">
          <h3>Replace current document evidence</h3>
          <label htmlFor="replacement-document-id">Document to replace</label>
          <select
            id="replacement-document-id"
            value={selectedReplacementId}
            onChange={(event) => setReplacementDocumentId(event.target.value)}
          >
            {reconciliation.source_document_ids.map((documentId) => {
              const observation = reconciliation.fields
                .flatMap((field) => field.observations)
                .find((item) => item.document_id === documentId);
              return <option value={documentId} key={documentId}>{observation?.document_display_name ?? documentId}</option>;
            })}
          </select>
          <input
            aria-label="Replacement reconciliation document"
            type="file"
            accept="application/pdf,.pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,.docx,text/plain,.txt"
            onChange={(event) => setReplacementFile(event.target.files?.[0] ?? null)}
          />
          <button
            type="button"
            disabled={isResolving || !replacementFile}
            onClick={() => replacementFile && onReplace(selectedReplacementId, currentDocumentVersion, replacementFile)}
          >
            Upload replacement and re-evaluate
          </button>
        </div>
      )}
    </section>
  );
}

export function SponsorOwnershipEvidenceView({ record }: { record: OwnershipAnalysisRecord | null }) {
  if (!record) return null;
  const names = new Map(record.parties.map((party) => [party.party_id, party.display_name]));
  return (
    <section className="document-evidence-card" aria-labelledby="ownership-evidence-heading">
      <p className="section-label">Ownership stage evidence</p>
      <h2 id="ownership-evidence-heading">How provisional ownership was calculated</h2>
      <p>{record.parties.length} parties · {record.relationships.length} relationships · {record.candidates.length} provisional candidate(s)</p>
      <ul>{record.relationships.map((relationship) => <li key={relationship.relationship_id}>{names.get(relationship.parent_party_id) ?? relationship.parent_party_id} → {names.get(relationship.child_party_id) ?? relationship.child_party_id}: {ownershipPercent(relationship.ownership_percent)}</li>)}</ul>
      {record.candidates.map((candidate) => <article key={candidate.party.party_id}><h3>{candidate.party.display_name} — {candidate.classification.replaceAll("_", " ")}</h3><p>Direct: {ownershipPercent(candidate.direct_ownership_percent)} | Indirect: {ownershipPercent(candidate.indirect_ownership_percent)} | Effective: {ownershipPercent(candidate.aggregated_ownership_percent)}</p><ul>{candidate.paths.map((path) => <li key={path.path_id}>{path.calculation}</li>)}</ul></article>)}
      {record.issues.length > 0 && <ul>{record.issues.map((issue) => <li key={issue.code}>{issue.code}: {issue.message}</li>)}</ul>}
    </section>
  );
}

export function SponsorOwnershipEvidence({ summary }: { summary: ZeroTouchCaseSummary }) {
  const [record, setRecord] = useState<OwnershipAnalysisRecord | null>(null);
  const caseId = summary.case.case_id;
  const revision = evidenceRevision(summary);
  useEffect(() => {
    let current = true;
    void fetchOwnership(caseId).then((value) => { if (current) setRecord(value); }).catch(() => { if (current) setRecord(null); });
    return () => { current = false; };
  }, [caseId, revision]);
  return <SponsorOwnershipEvidenceView record={record} />;
}

export function SponsorTargetEvidence({ summary }: { summary: ZeroTouchCaseSummary }) {
  if (!summary.target_operations.some((operation) => operation.status !== "NOT_ATTEMPTED")) return null;
  return <section className="document-evidence-card" aria-labelledby="target-evidence-heading"><p className="section-label">Mock GoldTier stage evidence</p><h2 id="target-evidence-heading">Server-authored target operations</h2><ol>{summary.target_operations.map((operation) => <li key={operation.operation}>{operation.operation} — {operation.status}</li>)}</ol></section>;
}

export function SponsorReadinessEvidence({ summary }: { summary: ZeroTouchCaseSummary }) {
  const readiness = summary.clm.readiness;
  return <section className="document-evidence-card" aria-labelledby="readiness-evidence-heading"><p className="section-label">Readiness evidence</p><h2 id="readiness-evidence-heading">Server-authored readiness</h2><dl><div><dt>Registry</dt><dd>{readiness.registry.status}</dd></div><div><dt>Documents</dt><dd>{readiness.document.status}</dd></div><div><dt>Ownership</dt><dd>{readiness.ownership.status}</dd></div><div><dt>Target readiness</dt><dd>{readiness.goldtier.status}</dd></div><div><dt>Active blockers</dt><dd>{readiness.blockers.length ? readiness.blockers.join(", ") : "None"}</dd></div></dl></section>;
}

export function HumanReviewPanel({
  exception,
  isResolving,
  onResolve,
  onReplace,
}: {
  exception: ZeroTouchException;
  isResolving: boolean;
  onResolve: (action: ExceptionResolutionAction) => void;
  onReplace?: (documentId: string, eventCount: number, file: File) => void;
}) {
  const [replacementFile, setReplacementFile] = useState<File | null>(null);
  const documentId = exception.evidence.find((item) => item.reference_id)?.reference_id;
  const eventCount = Number(exception.evidence_version.split(":")[2]);
  const replacementAvailable = exception.stage === "DOCUMENT"
    && typeof documentId === "string"
    && Number.isSafeInteger(eventCount)
    && eventCount > 0;
  
  return (
    <section className="human-review-card" aria-labelledby="review-required-heading">
      <div className="review-header">
        <p className="section-label">⚠️ Human review required</p>
        <h2 id="review-required-heading">{exception.stage.replaceAll("_", " ")} Stage</h2>
      </div>
      
      <div className="blocker-detail-section">
        <h3>Current issues</h3>
        <div className="blockers-grid">
          {exception.blocker_codes.map((blockerCode) => (
            <article key={blockerCode} className="blocker-card">
              <strong>{blockerCode.replaceAll("_", " ")}</strong>
              <p className="blocker-explanation">{blockerExplanation(blockerCode)}</p>
              <code>{blockerCode}</code>
            </article>
          ))}
        </div>
      </div>
      
      {exception.evidence.length > 0 && (
        <div className="evidence-section">
          <h3>Evidence details</h3>
          <div className="evidence-grid">
            {exception.evidence.map((evidence, index) => (
              <article className="exception-evidence-card" key={`${evidence.field_key ?? "evidence"}-${index}`}>
                <header>
                  <h4>{fieldLabel(evidence.field_key ?? "Evidence")}</h4>
                  {evidence.comparison && (
                    <span className={`comparison-badge comparison-badge--${evidence.comparison}`}>
                      {evidence.comparison}
                    </span>
                  )}
                </header>
                <dl>
                  {evidence.registry_value && (
                    <div>
                      <dt>Registry value</dt>
                      <dd><code>{evidence.registry_value}</code></dd>
                    </div>
                  )}
                  {evidence.document_value && (
                    <div>
                      <dt>Document value</dt>
                      <dd><code>{evidence.document_value}</code></dd>
                    </div>
                  )}
                  {evidence.confidence !== null && (
                    <div>
                      <dt>Confidence score</dt>
                      <dd>{confidencePercent(evidence.confidence)}</dd>
                    </div>
                  )}
                </dl>
              </article>
            ))}
          </div>
        </div>
      )}
      
      <div className="exception-actions">
        {exception.available_actions.map((action) => (
          <button key={action} type="button" disabled={isResolving} className="button-primary" onClick={() => onResolve(action)}>
            {action === "KEEP_REGISTRY_VALUE" ? "✓ Keep registry values" : "❓ Request additional information"}
          </button>
        ))}
        {exception.available_actions.length === 0 && (
          <p className="warning-notice">
            {replacementAvailable
              ? "⚠️ Replacement evidence is required to proceed."
              : "⚠️ No backend-authorized action is currently available."}
          </p>
        )}
      </div>
      
      {replacementAvailable && (
        <div className="replacement-section">
          <h3>Upload corrected document</h3>
          <p>Upload a replacement PDF to supersede the current evidence. The system will re-extract and re-evaluate.</p>
          <label htmlFor={`replacement-${exception.exception_id}`}>Select replacement document</label>
          <input
            id={`replacement-${exception.exception_id}`}
            type="file"
            accept="application/pdf,.pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,.docx,text/plain,.txt"
            onChange={(event) => setReplacementFile(event.target.files?.[0] ?? null)}
          />
          {replacementFile && <p className="file-selected">✓ {replacementFile.name}</p>}
          <button
            type="button"
            disabled={isResolving || !replacementFile}
            className="button-primary"
            onClick={() => replacementFile && onReplace?.(documentId, eventCount, replacementFile)}
          >
            Upload & Re-evaluate
          </button>
        </div>
      )}
    </section>
  );
}

export function AutomationTimeline({ summary }: { summary: ZeroTouchCaseSummary }) {
  return (
    <section className="automation-timeline">
      <p className="section-label">Safe automation history</p>
      <ol>
        {summary.timeline.map((event) => (
          <li key={event.sequence}>
            <strong>{event.event_type.replaceAll("_", " ")}</strong>
            <span>{event.message}</span>
            <time dateTime={event.timestamp}>{formatTimestamp(event.timestamp)}</time>
          </li>
        ))}
      </ol>
    </section>
  );
}

export function CaseSummary({ caseData }: { caseData: OnboardingCase }) {
  const terminalTone =
    caseData.state === "COMPLETED"
      ? "success"
      : caseData.state === "REVIEW_REQUIRED"
        ? "review"
        : caseData.state === "FAILED"
          ? "failed"
          : "active";

  return (
    <section className="result-panel" aria-live="polite" aria-labelledby="case-heading">
      <div className={`case-status case-status--${terminalTone}`}>
        <span>Current onboarding state</span>
        <strong>{caseData.state}</strong>
      </div>
      <p className="completion-boundary">
        This underlying case state is not an approval claim. Phase 05 readiness and Mock
        GoldTier submission are reported separately by the unified orchestration summary.
      </p>
      <JurisdictionDecision caseData={caseData} />
      <RegistryAcquisitionPanel caseData={caseData} />

      <div className="panel-grid">
        <article className="detail-card">
          <p className="section-label">Canonical company</p>
          <h2 id="case-heading">{caseData.entity?.legal_name ?? caseData.requested_uen}</h2>
          <dl>
            <div><dt>UEN</dt><dd>{caseData.entity?.registration_number ?? caseData.requested_uen}</dd></div>
            <div><dt>Country</dt><dd>{caseData.entity?.country_of_incorporation ?? "Not available"}</dd></div>
            <div><dt>Entity type</dt><dd>{caseData.entity?.party_type ?? "Not available"}</dd></div>
            <div><dt>Registration date</dt><dd>{caseData.entity?.registration_date ?? "Not available"}</dd></div>
            <div><dt>Registry status</dt><dd>{caseData.entity?.entity_status ?? "Not available"}</dd></div>
            <div><dt>Registered address</dt><dd>{formatAddress(caseData)}</dd></div>
            <div>
              <dt>Registry source</dt>
              <dd>
                {caseData.entity
                  ? `${caseData.entity.source.source_system} ${titleCaseEnvironment(caseData.entity.source.environment)}`
                  : "Not available"}
              </dd>
            </div>
          </dl>
        </article>

        <article className="detail-card">
          <p className="section-label">Mock GoldTier result</p>
          {caseData.goldtier_result ? (
            <dl>
              <div><dt>Party ID</dt><dd>{caseData.goldtier_result.party_id}</dd></div>
              <div><dt>Shell</dt><dd>{caseData.goldtier_result.shell_status}</dd></div>
              <div><dt>Policy</dt><dd>{caseData.goldtier_result.policy_status ?? "Not created"}</dd></div>
              <div><dt>Amend</dt><dd>{caseData.goldtier_result.amend_status ?? "Not attempted"}</dd></div>
            </dl>
          ) : (
            <p className="empty-copy">No mock GoldTier customer was created.</p>
          )}
        </article>
      </div>

      {caseData.error && (
        <div className={`outcome-message outcome-message--${terminalTone}`} role="status">
          <strong>{caseData.error.code}</strong>
          <span>{caseData.error.message}</span>
        </div>
      )}

      <article className="timeline-card">
        <div className="timeline-heading">
          <div><p className="section-label">Safe case history</p><h2>Workflow progression</h2></div>
          <span>{caseData.events.length} events</span>
        </div>
        <ol className="timeline">
          {caseData.events.map((event) => (
            <li key={event.sequence} className={`timeline-item timeline-item--${event.outcome}`}>
              <span className="timeline-marker" aria-hidden="true" />
              <div>
                <div className="timeline-state"><strong>{event.stage}</strong><span>{event.outcome}</span></div>
                <p>{event.message}</p>
                <time dateTime={event.timestamp}>{formatTimestamp(event.timestamp)}</time>
              </div>
            </li>
          ))}
        </ol>
      </article>
      <p className="case-identifiers">Case {caseData.case_id} | Correlation {caseData.correlation_id}</p>
    </section>
  );
}

export function LegacyApp() {
  const [uen, setUen] = useState(DEFAULT_UEN);
  const [caseId, setCaseId] = useState("");
  const [scenarios, setScenarios] = useState<MockScenario[]>([]);
  const [simulationProfile, setSimulationProfile] = useState<SimulationProfile | null>(null);
  const [caseData, setCaseData] = useState<OnboardingCase | null>(null);
  const [clmSummary, setClmSummary] = useState<ClmCaseSummary | null>(null);
  const [isClmRefreshing, setIsClmRefreshing] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [requestError, setRequestError] = useState<string | null>(null);

  useEffect(() => {
    void fetchMockScenarios()
      .then((discovery) => {
        setScenarios(discovery.scenarios);
        setSimulationProfile(discovery.simulation);
      })
      .catch(() => setRequestError("Connector profile discovery is unavailable."));
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setRequestError(null);
    setCaseData(null);
    setClmSummary(null);
    try {
      const created = await createClmCase(uen);
      setClmSummary(created);
      setCaseData(created.case);
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "Unable to start onboarding.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleOpenCase(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setRequestError(null);
    setCaseData(null);
    setClmSummary(null);
    try {
      const opened = await fetchClmCase(caseId.trim());
      setClmSummary(opened);
      setCaseData(opened.case);
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "Unable to open the case.");
    } finally {
      setIsSubmitting(false);
    }
  }

  function invalidateClmReadiness() {
    setClmSummary(null);
    setIsClmRefreshing(true);
  }

  async function refreshClmSummary() {
    if (!caseData) return;
    setClmSummary(null);
    setIsClmRefreshing(true);
    try {
      const refreshed = await fetchClmCase(caseData.case_id);
      setClmSummary(refreshed);
      setCaseData(refreshed.case);
    } catch {
      setRequestError("Authoritative CLM readiness could not be refreshed.");
    } finally {
      setIsClmRefreshing(false);
    }
  }

  return (
    <main className="page-shell">
      <header className="hero">
        <SimulationBanner profile={simulationProfile} />
        <p className="eyebrow">Data Dividends | Phase 05</p>
        <h1>One coherent, evidence-led CLM journey.</h1>
        <p className="summary">
          Stage registry intake, review synthetic document evidence, analyze ownership,
          evaluate typed blockers, and submit an eligible case to Mock GoldTier.
        </p>
      </header>

      <section className="launch-card" aria-labelledby="launch-heading">
        <div>
          <p className="section-label">Case access</p>
          <h2 id="launch-heading">Start or reopen a staged CLM case</h2>
          <p>All demo data is synthetic. Existing cases remain process-local.</p>
        </div>
        <div className="case-access-forms">
          <form onSubmit={(event) => void handleSubmit(event)}>
            <label htmlFor="uen">Create from Singapore UEN</label>
            <div className="form-row">
              <input
                id="uen"
                list="mock-uens"
                value={uen}
                onChange={(event) => setUen(event.target.value.toUpperCase())}
                maxLength={64}
                required
              />
              <datalist id="mock-uens">
                {scenarios.map((scenario) => (
                  <option key={scenario.uen} value={scenario.uen}>{scenario.label}</option>
                ))}
              </datalist>
              <button type="submit" disabled={isSubmitting}>Create case</button>
            </div>
          </form>
          <form onSubmit={(event) => void handleOpenCase(event)}>
            <label htmlFor="case-id">Open existing case ID</label>
            <div className="form-row">
              <input
                id="case-id"
                value={caseId}
                onChange={(event) => setCaseId(event.target.value)}
                placeholder="00000000-0000-4000-8000-000000000000"
                required
              />
              <button type="submit" disabled={isSubmitting}>Open case</button>
            </div>
          </form>
        </div>
      </section>

      {requestError && <div className="request-error" role="alert">{requestError}</div>}
      {caseData && (
        <>
          <CaseSummary caseData={caseData} />
          <DocumentPanel
            key={caseData.case_id}
            caseData={caseData}
            threshold={simulationProfile?.idp_review_confidence_threshold ?? 0.85}
            onMutationStart={invalidateClmReadiness}
            onMutationSettled={refreshClmSummary}
          />
          <OwnershipPanel
            key={`ownership-${caseData.case_id}`}
            caseData={caseData}
            configuredThreshold={
              simulationProfile?.ubo_ownership_threshold_percent ?? "25"
            }
            onMutationStart={invalidateClmReadiness}
            onMutationSettled={refreshClmSummary}
          />
          {isClmRefreshing ? (
            <ClmRefreshingState />
          ) : clmSummary && (
            <ClmJourney
              summary={clmSummary}
              onRefresh={refreshClmSummary}
              onUpdate={(updated) => {
                setClmSummary(updated);
                setCaseData(updated.case);
              }}
            />
          )}
        </>
      )}
    </main>
  );
}

export interface AppProps {
  demoControlsEnabled?: boolean;
}

export default function App({
  demoControlsEnabled = import.meta.env.VITE_DEMO_CONTROLS_ENABLED === "true",
}: AppProps = {}) {
  const [activeTab, setActiveTab] = useState<AppTab>("start");
  const [uen, setUen] = useState(DEFAULT_UEN);
  const [countryOfIncorporation, setCountryOfIncorporation] =
    useState<JurisdictionSelection>("");
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [fileValidationErrors, setFileValidationErrors] = useState<string[]>([]);
  const [caseList, setCaseList] = useState<ZeroTouchCaseListItem[]>([]);
  const [startProgress, setStartProgress] = useState<StartProgress>({
    stage: "idle",
    message: "",
    failedFile: null,
  });
  const [caseId, setCaseId] = useState("");
  const [demoScenario, setDemoScenario] = useState<ZeroTouchDemoScenario>("STRAIGHT_THROUGH");
  const [simulationProfile, setSimulationProfile] = useState<SimulationProfile | null>(null);
  const [summary, setSummary] = useState<ZeroTouchCaseSummary | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isResolving, setIsResolving] = useState(false);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [pollingWarning, setPollingWarning] = useState<string | null>(null);
  const journeyGeneration = useRef(0);
  const resolutionActive = useRef(false);
  const uploadedFileKeys = useRef(new Set<string>());
  const failedDocumentIds = useRef(new Map<string, string>());
  const activeJourneyUsesDemo = useRef(false);

  const refreshCaseList = useCallback(async () => {
    const records = await fetchZeroTouchCases();
    setCaseList(records);
  }, []);

  useEffect(() => {
    void fetchExecutionProfile()
      .then(setSimulationProfile)
      .catch(() => setRequestError("Connector profile discovery is unavailable."));
  }, []);

  useEffect(() => {
    if (activeTab === "dashboard" || activeTab === "review" || summary) {
      void refreshCaseList().catch(() => {
        // The selected case remains usable when the read-only portfolio is unavailable.
      });
    }
  }, [activeTab, refreshCaseList, summary?.case.case_id, summary?.version]);

  useEffect(() => {
    if (!summary || !shouldPollAutomation(summary.status)) return;
    const generation = journeyGeneration.current;
    const activeCaseId = summary.case.case_id;
    return startAutomationPolling({
      caseId: activeCaseId,
      generation,
      currentGeneration: () => journeyGeneration.current,
      fetchCase: fetchZeroTouchCase,
      onUpdate: setSummary,
      onWarning: setPollingWarning,
      shouldContinue: shouldPollAutomation,
    });
  }, [summary?.case.case_id, summary?.status, summary?.version]);

  useEffect(() => {
    if (!summary || startProgress.stage === "idle" || startProgress.stage === "failed") return;
    if (summary.status === "WAITING_FOR_REVIEW") {
      setStartProgress({ stage: "waiting", message: "Waiting for review", failedFile: null });
    } else if (summary.status === "COMPLETED") {
      setStartProgress({ stage: "completed", message: "Completed", failedFile: null });
    } else if (summary.status === "TECHNICAL_FAILURE") {
      setStartProgress({ stage: "failed", message: "Failed safely", failedFile: null });
    } else if (["RUNNING", "RESUMING", "RECOVERY_PENDING"].includes(summary.status)) {
      setStartProgress({ stage: "processing", message: "Processing…", failedFile: null });
    }
  }, [summary?.status, summary?.version, startProgress.stage]);

  function addSelectedDocuments(files: FileList | null) {
    if (!files) return;
    const validated = validateSelectedDocuments([...selectedFiles, ...Array.from(files)]);
    setSelectedFiles(validated.accepted);
    setFileValidationErrors(validated.errors);
  }

  function removeSelectedDocument(file: File) {
    const key = selectedFileKey(file);
    setSelectedFiles((current) => current.filter((item) => selectedFileKey(item) !== key));
    uploadedFileKeys.current.delete(key);
    failedDocumentIds.current.delete(key);
  }

  function resetStartWorkspace() {
    journeyGeneration.current += 1;
    setSelectedFiles([]);
    setFileValidationErrors([]);
    uploadedFileKeys.current = new Set();
    failedDocumentIds.current = new Map();
    setStartProgress({ stage: "idle", message: "", failedFile: null });
    setRequestError(null);
    setPollingWarning(null);
  }

  async function uploadRemainingDocuments(
    created: ZeroTouchCaseSummary,
    demo: boolean,
  ): Promise<ZeroTouchCaseSummary> {
    for (const [index, file] of selectedFiles.entries()) {
      const key = selectedFileKey(file);
      if (uploadedFileKeys.current.has(key)) continue;
      setStartProgress({
        stage: "uploading",
        message: `Uploading documents… (${index + 1}/${selectedFiles.length})`,
        failedFile: null,
      });
      try {
        const failedDocumentId = failedDocumentIds.current.get(key);
        if (failedDocumentId) {
          await retryZeroTouchIntakeDocument(
            created.case.case_id,
            failedDocumentId,
            file,
            demo,
          );
          failedDocumentIds.current.delete(key);
        } else {
          await intakeZeroTouchDocument(created.case.case_id, file, demo);
        }
        uploadedFileKeys.current.add(key);
      } catch (error) {
        if (error instanceof ApiError && error.detail?.document_id) {
          failedDocumentIds.current.set(key, error.detail.document_id);
        }
        setStartProgress({ stage: "failed", message: "Failed safely", failedFile: file.name });
        throw error;
      }
    }
    setStartProgress({ stage: "starting", message: "Starting analysis…", failedFile: null });
    return completeZeroTouchIntake(created.case.case_id, selectedFiles.length, demo);
  }

  async function beginJourney(demoScenario?: ZeroTouchDemoScenario) {
    if (resolutionActive.current || isSubmitting) return;
    if (selectedFiles.length === 0) {
      setRequestError("Select at least one valid PDF, DOCX, or UTF-8 TXT document.");
      return;
    }
    setIsSubmitting(true);
    journeyGeneration.current += 1;
    uploadedFileKeys.current = new Set();
    failedDocumentIds.current = new Map();
    activeJourneyUsesDemo.current = demoScenario !== undefined;
    setRequestError(null);
    setPollingWarning(null);
    setStartProgress({ stage: "creating", message: "Creating case…", failedFile: null });
    setSummary(null);
    let created: ZeroTouchCaseSummary | null = null;
    try {
      created = await createZeroTouchCase(
        uen,
        demoScenario,
        countryOfIncorporation || undefined,
      );
      setSummary(created);
      setCaseId(created.case.case_id);
      await refreshCaseList();
      if (created.status === "PENDING_INPUTS") {
        setSummary(await uploadRemainingDocuments(created, demoScenario !== undefined));
      }
    } catch (error) {
      if (created) {
        try {
          setSummary(await fetchZeroTouchCase(created.case.case_id));
        } catch {
          // The created case ID remains visible through the retained creation response.
          setSummary(created);
        }
      }
      setStartProgress((current) => ({
        stage: "failed",
        message: "Failed safely",
        failedFile: current.failedFile,
      }));
      setRequestError(error instanceof Error ? error.message : "Unable to start onboarding.");
    } finally {
      await refreshCaseList().catch(() => undefined);
      setIsSubmitting(false);
    }
  }

  async function retryCreatedCase() {
    if (!summary || summary.status !== "PENDING_INPUTS" || isSubmitting) return;
    setIsSubmitting(true);
    setRequestError(null);
    try {
      setSummary(await uploadRemainingDocuments(summary, activeJourneyUsesDemo.current));
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "Document intake retry failed.");
    } finally {
      await refreshCaseList().catch(() => undefined);
      setIsSubmitting(false);
    }
  }

  function handleStart(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void beginJourney();
  }

  async function openSelectedCase(selectedCaseId: string, destination?: AppTab) {
    if (resolutionActive.current) return;
    const generation = ++journeyGeneration.current;
    setIsSubmitting(true);
    setRequestError(null);
    setPollingWarning(null);
    setSummary(null);
    try {
      const opened = await fetchZeroTouchCase(selectedCaseId.trim());
      if (generation === journeyGeneration.current) {
        setSummary(opened);
        setCaseId(opened.case.case_id);
        if (destination) setActiveTab(destination);
      }
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "Unable to open the case.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleOpenCase(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await openSelectedCase(caseId);
  }

  async function handleResolution(
    exception: ZeroTouchException,
    action: ExceptionResolutionAction,
  ) {
    if (!summary || resolutionActive.current) return;
    const generation = journeyGeneration.current;
    const activeCaseId = summary.case.case_id;
    resolutionActive.current = true;
    setIsResolving(true);
    setRequestError(null);
    try {
      const updated = await resolveZeroTouchException(
        summary,
        exception.exception_id,
        action,
        exception.evidence_version,
      );
      if (
        generation === journeyGeneration.current
        && activeCaseId === updated.case.case_id
      ) setSummary(updated);
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        try {
          const refreshed = await fetchZeroTouchCase(activeCaseId);
          if (generation === journeyGeneration.current) setSummary(refreshed);
        } catch {
          // Keep the stable stale-resolution message below.
        }
      }
      if (generation === journeyGeneration.current) {
        setRequestError(error instanceof Error ? error.message : "Exception resolution failed.");
      }
    } finally {
      resolutionActive.current = false;
      if (generation === journeyGeneration.current) setIsResolving(false);
    }
  }

  async function handleReplacement(documentId: string, eventCount: number, file: File) {
    if (!summary || resolutionActive.current) return;
    resolutionActive.current = true;
    setIsResolving(true);
    setRequestError(null);
    try {
      setSummary(await replaceZeroTouchDocument(summary.case.case_id, documentId, eventCount, file));
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "Replacement evidence failed.");
    } finally {
      resolutionActive.current = false;
      setIsResolving(false);
    }
  }

  async function handleReconciliationResolution(
    discrepancy: ReconciliationDiscrepancy,
    action: ReconciliationDecisionAction,
  ) {
    if (!summary?.reconciliation || resolutionActive.current) return;
    const generation = journeyGeneration.current;
    const activeCaseId = summary.case.case_id;
    resolutionActive.current = true;
    setIsResolving(true);
    setRequestError(null);
    try {
      const updated = await resolveReconciliationDiscrepancy(
        summary,
        discrepancy.discrepancy_id,
        action,
        summary.reconciliation.version,
        discrepancy.evidence_fingerprint,
      );
      if (generation === journeyGeneration.current && activeCaseId === updated.case.case_id) {
        setSummary(updated);
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        try {
          const refreshed = await fetchZeroTouchCase(activeCaseId);
          if (generation === journeyGeneration.current) setSummary(refreshed);
        } catch {
          // Keep the stable stale-resolution message below.
        }
      }
      if (generation === journeyGeneration.current) {
        setRequestError(error instanceof Error ? error.message : "Reconciliation decision failed.");
      }
    } finally {
      resolutionActive.current = false;
      if (generation === journeyGeneration.current) setIsResolving(false);
    }
  }

  async function handleRecovery() {
    if (!summary || isSubmitting || isResolving) return;
    setIsSubmitting(true);
    setRequestError(null);
    try {
      setSummary(await resumeZeroTouchCase(summary.case.case_id));
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "Finalization recovery failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleEvidenceExport() {
    if (!summary) return;
    try {
      const evidence = await fetchUatEvidence(summary.case.case_id);
      const blob = new Blob([JSON.stringify(evidence, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${evidence.uat_case_id}-${evidence.case_id}.json`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "UAT evidence export failed.");
    }
  }

  return (
    <main className="page-shell sponsor-shell">
      <header className="hero sponsor-hero">
        <SimulationBanner profile={simulationProfile} />
        <p className="eyebrow">Data Dividends | Corporate onboarding</p>
        <h1>Client Lifecycle Management (CLM) Onboarding</h1>
        <p className="summary">
          Provide the corporate identity and supporting documents once. The workflow
          retrieves registry evidence, analyses each supplied document, reconciles
          differences, evaluates ownership, and progresses until review is required.
        </p>
      </header>

      <div className="workspace-layout">
        <WorkspaceTabs activeTab={activeTab} onChange={setActiveTab} />
        <div className="workspace-content">
          {(activeTab === "dashboard" || activeTab === "start") && (
            <>
      {activeTab === "dashboard" && (
        <div className="dashboard-primary-action">
          <button type="button" onClick={() => setActiveTab("start")}>Start onboarding</button>
        </div>
      )}
      {activeTab === "dashboard" && <DashboardSnapshot summary={summary} />}
      {activeTab === "dashboard" && (
        <CasePortfolio cases={caseList} onOpen={(id) => void openSelectedCase(id, "dashboard")} />
      )}
      {activeTab === "start" && (
      <section className="launch-card zero-touch-launch" aria-labelledby="onboarding-heading">
        <div>
          <p className="section-label">Corporate onboarding</p>
          <h2 id="onboarding-heading">Start onboarding</h2>
          <p>Only fictional, synthetic PDF, DOCX, and UTF-8 TXT evidence is permitted in this local POC.</p>
        </div>
        <form onSubmit={(event) => void handleStart(event)} className="zero-touch-form">
          <JurisdictionSelector
            value={countryOfIncorporation}
            onChange={setCountryOfIncorporation}
          />
          <label htmlFor="zero-touch-uen">Company registration identifier / UEN</label>
          <input
            id="zero-touch-uen"
            value={uen}
            onChange={(event) => setUen(event.target.value.toUpperCase())}
            maxLength={32}
            required
          />
          <label htmlFor="zero-touch-document">Supporting documents</label>
          <input
            id="zero-touch-document"
            type="file"
            multiple
            accept="application/pdf,.pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,.docx,text/plain,.txt"
            disabled={isSubmitting || startProgress.stage !== "idle"}
            onChange={(event) => addSelectedDocuments(event.target.files)}
          />
          <label htmlFor="zero-touch-folder">Select folder</label>
          <input
            id="zero-touch-folder"
            type="file"
            multiple
            accept="application/pdf,.pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,.docx,text/plain,.txt"
            disabled={isSubmitting || startProgress.stage !== "idle"}
            {...({ webkitdirectory: "", directory: "" } as Record<string, string>)}
            onChange={(event) => addSelectedDocuments(event.target.files)}
          />
          <p className="input-help">Maximum 20 files, 5 MiB each, 25 MiB total. ZIP, macros, images, and other formats are not accepted.</p>
          {selectedFiles.length > 0 && (
            <div className="selected-documents" aria-label="Selected supporting documents">
              <h3>Supporting documents</h3>
              <ul>
                {selectedFiles.map((file) => (
                  <li key={selectedFileKey(file)}>
                    <span>✓ {file.name}</span>
                    <button type="button" disabled={isSubmitting || startProgress.stage !== "idle"} onClick={() => removeSelectedDocument(file)}>Remove</button>
                  </li>
                ))}
              </ul>
              <strong>{selectedDocumentSummary(selectedFiles)}</strong>
            </div>
          )}
          {fileValidationErrors.length > 0 && (
            <ul className="file-validation-errors" role="alert">
              {fileValidationErrors.map((message) => <li key={message}>{message}</li>)}
            </ul>
          )}
          <button type="submit" disabled={isSubmitting || isResolving}>
            {isSubmitting ? "Starting CLM onboarding…" : "Start CLM onboarding"}
          </button>
        </form>
        <StartProgressPanel
          progress={startProgress}
          summary={summary}
          isSubmitting={isSubmitting}
          onViewCase={() => setActiveTab("dashboard")}
          onOpenReview={() => setActiveTab("review")}
          onRetry={() => void retryCreatedCase()}
          onStartAnother={resetStartWorkspace}
        />
        <form onSubmit={(event) => void handleOpenCase(event)} className="reopen-form">
          <label htmlFor="zero-touch-case-id">Reopen case ID</label>
          <div className="form-row">
            <input
              id="zero-touch-case-id"
              value={caseId}
              onChange={(event) => setCaseId(event.target.value)}
              placeholder="00000000-0000-4000-8000-000000000000"
              required
            />
            <button type="submit" disabled={isSubmitting || isResolving}>Open onboarding</button>
          </div>
        </form>
      </section>
      )}

      {activeTab === "start" && demoControlsEnabled && (
        <details className="demo-controls">
          <summary>Demo/Test Controls</summary>
          <p>These deterministic selectors are synthetic and are not part of normal operations.</p>
          <label htmlFor="zero-touch-scenario">Integrated synthetic scenario</label>
          <select
            id="zero-touch-scenario"
            value={demoScenario}
            onChange={(event) => setDemoScenario(event.target.value as ZeroTouchDemoScenario)}
          >
            <option value="STRAIGHT_THROUGH">Straight through</option>
            <option value="DOCUMENT_DISCREPANCY">Document discrepancy</option>
            <option value="MULTIPLE_DOCUMENT_BLOCKERS">Multiple document blockers</option>
            <option value="LOW_CONFIDENCE">Low-confidence document</option>
            <option value="OWNERSHIP_CYCLE">Ownership cycle</option>
            <option value="OWNERSHIP_INCOMPLETE">Incomplete ownership</option>
            <option value="MULTIPLE_OWNERSHIP_PATHS">Multiple ownership paths</option>
            <option value="EXISTING_PARTY">Existing Mock party</option>
            <option value="TARGET_FAILURE">Mock target failure</option>
            <option value="PARTIAL_AMEND">Partial amend</option>
            <option value="RECOVERY">Replay-free recovery</option>
            <option value="TECHNICAL_FAILURE">IDP technical failure</option>
          </select>
          <button type="button" disabled={isSubmitting || isResolving} onClick={() => void beginJourney(demoScenario)}>
            Run selected fault-injection case
          </button>
          <details className="legacy-controls">
            <summary>Legacy manual diagnostics</summary>
            <LegacyApp />
          </details>
        </details>
      )}

      {requestError && <div className="request-error" role="alert">{requestError}</div>}
      {pollingWarning && <div className="polling-warning" role="status">{pollingWarning}</div>}
      {summary && activeTab === "dashboard" && (
        <>
          <OnboardingProgress summary={summary} />
          <CaseIdentityStrip summary={summary} />
          <SponsorCaseSummary summary={summary} onOpenReview={() => setActiveTab("review")} />
          <details className="evidence-disclosure" open={summary.status === "WAITING_FOR_REVIEW"}>
            <summary>Evidence and readiness details</summary>
            <SponsorDocumentEvidence summary={summary} />
            <ReconciliationPanel summary={summary} />
            <SponsorOwnershipEvidence summary={summary} />
            <SponsorTargetEvidence summary={summary} />
            <SponsorReadinessEvidence summary={summary} />
          </details>
          {summary.status === "RESUMING" && (
            <div className="resuming-banner" role="status">Resuming onboarding…</div>
          )}
          {summary.status === "RECOVERY_PENDING" && (
            <div className="resuming-banner" role="status">
              <span>Mock target outcome retained; finalization recovery is pending without target replay.</span>
              <button type="button" disabled={isSubmitting} onClick={() => void handleRecovery()}>
                Complete safe recovery
              </button>
            </div>
          )}
          {summary.status === "TECHNICAL_FAILURE" && summary.technical_failure && (
            <section className="technical-failure-card" role="alert">
              <p className="section-label">Technical failure</p>
              <h2>Automation stopped safely</h2>
              <strong>{summary.technical_failure.code}</strong>
              <p>{summary.technical_failure.message}</p>
              <p>No business-review decision is requested for this technical outage.</p>
            </section>
          )}
          <AutomationTimeline summary={summary} />
          {demoControlsEnabled && (
            <button className="evidence-export" type="button" onClick={() => void handleEvidenceExport()}>
              Export safe UAT evidence
            </button>
          )}
          <p className="claim-boundary">
            Mock and provisional POC only. This is not Ready-for-Approval, legal UBO
            determination, customer approval, or evidence of live ACRA/GoldTier interoperability.
          </p>
        </>
      )}
        </>
          )}

          {activeTab === "review" && (
            <ReviewQueue
              cases={caseList.filter((item) => item.status === "WAITING_FOR_REVIEW")}
              selectedCaseId={summary?.case.case_id}
              onOpen={(id) => void openSelectedCase(id, "review")}
            />
          )}

          {activeTab === "review" && summary && (
            <>
          <LocalReviewerWorkbench summary={summary} />
          <ReconciliationPanel
            summary={summary}
            isResolving={isResolving}
            onResolve={(discrepancy, action) => void handleReconciliationResolution(discrepancy, action)}
            onReplace={(documentId, eventCount, file) => void handleReplacement(documentId, eventCount, file)}
          />
          {summary.status === "WAITING_FOR_REVIEW" && summary.active_exceptions
            .filter((exception) => !summary.reconciliation?.discrepancies.some(
              (discrepancy) => discrepancy.discrepancy_id === exception.exception_id,
            ))
            .map((exception) => (
            <HumanReviewPanel
              key={exception.exception_id}
              exception={exception}
              isResolving={isResolving}
              onResolve={(action) => void handleResolution(exception, action)}
              onReplace={(documentId, eventCount, file) => void handleReplacement(documentId, eventCount, file)}
            />
          ))}
            </>
          )}

          {activeTab === "review" && !summary && (
            <section className="workspace-placeholder" aria-labelledby="review-empty-heading">
              <p className="section-label">Review</p>
              <h2 id="review-empty-heading">Select a queued case</h2>
              <p>The backend-authored queue above contains every current process-local case waiting for review.</p>
            </section>
          )}

          {activeTab === "logs" && (
            summary ? <AutomationTimeline summary={summary} /> : (
          <section className="workspace-placeholder" aria-labelledby="logs-heading">
            <p className="section-label">Logs</p>
            <h2 id="logs-heading">No case selected</h2>
            <p>Open or start a case from the Dashboard to view its safe automation history.</p>
          </section>
        )
          )}

          {activeTab === "account" && <AccountPlaceholder />}
        </div>
      </div>
    </main>
  );
}
