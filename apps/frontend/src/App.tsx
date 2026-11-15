import { useEffect, useRef, useState, type FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router";

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
  intakeZeroTouchDocument,
  loadMockOwnership,
  reviewDocument,
  resolveReconciliationDiscrepancy,
  resolveZeroTouchException,
  replaceZeroTouchDocument,
  resumeZeroTouchCase,
  retryZeroTouchIntakeDocument,
  submitClmCase,
  uploadDocument,
  createZeroTouchCase,
  deleteZeroTouchCase,
  fetchTeamOptions,
} from "./api";
import { type IntakeUploadFailure, type UploadRejection, uploadRejectionPresentation } from "./uploadRejection";
import {
  MAX_CASE_UPLOAD_BYTES,
  MAX_UPLOAD_FILE_BYTES,
  UPLOAD_ACCEPT,
  UPLOAD_DOCUMENT_TYPES,
  UPLOAD_ERRORS,
  UPLOAD_ERROR_BY_CODE,
  UPLOAD_HELP_TEXT,
} from "./uploadLimits";
import { startAutomationPolling } from "./automationPolling";
import {
  caseCreatedEffect,
  caseDeletedEffect,
  caseSummaryMutationEffect,
  caseSupportingMutationEffect,
  executionProfileQueryOptions,
} from "./caseQueries";
import AuditTrail from "./pages/AuditTrail";
import CaseDetail from "./pages/CaseDetail";
import SampleCaseDetail from "./pages/SampleCaseDetail";
import { sampleCaseIdFromUrlId } from "./pages/mockDashboards/onboardingSample";
import AiAssistantPanel from "./pages/AiAssistantPanel";
import { aiAssistantContextFor } from "./pages/aiAssistantContext";
import CaseQueue, { DEFAULT_CASE_QUEUE_PRESENTATION } from "./pages/CaseQueue";
import type { CaseQueuePresentationState } from "./pages/CaseQueue";
import Dashboard from "./pages/Dashboard";
import { GtcDashboard, PeriodicReviewDashboard } from "./pages/mockDashboards/MockDashboards";
import HomeOnboarding from "./pages/HomeOnboarding";
import DeleteCaseDialog from "./pages/DeleteCaseDialog";
import GoldTierRequestPreview from "./pages/GoldTierRequestPreview";
import PolicyRules from "./pages/PolicyRules";
import KnowledgeReview from "./pages/KnowledgeReview";
import AdminTeams from "./pages/AdminTeams";
import AdminUsers from "./pages/AdminUsers";
import GoldTierSandbox from "./pages/GoldTierSandbox";
import AcraDiagnostics from "./pages/AcraDiagnostics";
import AiModelManagement from "./pages/AiModelManagement";
import WorkflowManager from "./pages/WorkflowManager";
import WorkflowDesigner from "./pages/WorkflowDesigner";
import WorkflowTab, { WorkflowCasesPage, WorkflowRunPage } from "./pages/WorkflowTab";
import RetainedIntakeRecovery from "./pages/RetainedIntakeRecovery";
import { paths, requiredCapabilityForPath, WorkspaceRoutes, WorkspaceTabs } from "./navigation";
import {
  formatTimestamp,
  goldTierJourneyLabel,
  shouldMaintainLiveProgress,
  shouldPollAutomation,
  targetOutcomeLabel,
} from "./shared";
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
  AuthenticatedProfile,
  TeamId,
  AuthenticatedTeam,
} from "./types";

export const MAX_INTAKE_FILE_COUNT = 20;
// The limits live in uploadLimits.ts (kept in sync with the backend); these names remain for callers.
export const MAX_INTAKE_FILE_BYTES = MAX_UPLOAD_FILE_BYTES;
export const MAX_INTAKE_TOTAL_BYTES = MAX_CASE_UPLOAD_BYTES;

export function intakeFileKey(file: File): string {
  return `${file.name}\u0000${file.size}\u0000${file.lastModified}`;
}

export function validateIntakeFiles(files: File[]): string | null {
  if (files.length === 0) return "Select at least one supporting document before starting onboarding.";
  if (files.length > MAX_INTAKE_FILE_COUNT) return `Select no more than ${MAX_INTAKE_FILE_COUNT} files.`;
  let total = 0;
  for (const file of files) {
    const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    const expectedType = DOCUMENT_TYPES[extension];
    if (!SAFE_DOCUMENT_NAME.test(file.name) || !expectedType || file.type !== expectedType) {
      return `${file.name}: ${UPLOAD_ERRORS.unsupportedType}`;
    }
    if (file.size <= 0) return `${file.name}: this file is empty.`;
    if (file.size > MAX_INTAKE_FILE_BYTES) return `${file.name}: ${UPLOAD_ERRORS.fileTooLarge}`;
    total += file.size;
  }
  if (total > MAX_INTAKE_TOTAL_BYTES) return UPLOAD_ERRORS.caseTotalTooLarge;
  return null;
}

// Registry stops that still let the RM add evidence to the retained case (D-114 adds the
// three UEN-route stops).
const RETAINED_INTAKE_REGISTRY_CODES = [
  "REGISTRY_EXPECTED_DATA_MISSING", "INITIAL_IDENTITY_INCOMPLETE", "ACRA_ENTITY_NOT_FOUND",
  "GOVERNMENT_IDENTITY_NOT_FOUND", "ENTITY_CATEGORY_MISMATCH", "UEN_ENTITY_TYPE_UNSUPPORTED",
];

export function isRegistryIntakeUnavailable(summary: ZeroTouchCaseSummary): boolean {
  const resolution = summary.case.jurisdiction_resolution;
  const route = summary.case.registry_route;
  const acquisition = summary.case.registry_acquisition;
  const registryExceptions = summary.active_exceptions
    .filter((exception) => exception.stage === "REGISTRY");
  const evidenceIntakeCanContinue = registryExceptions.length > 0
    && registryExceptions.every(
      (exception) => RETAINED_INTAKE_REGISTRY_CODES
        .includes(exception.blocker_code),
    );
  return (
    registryExceptions.some(
      (exception) => !RETAINED_INTAKE_REGISTRY_CODES
        .includes(exception.blocker_code),
    )
    || resolution?.status === "CONFLICT"
    || resolution?.status === "UNRESOLVED"
    || route?.status === "PROVIDER_NOT_IMPLEMENTED"
    || (acquisition?.status === "FAILED" && !evidenceIntakeCanContinue)
    || (
      summary.current_stage === "REGISTRY"
      && (summary.status === "WAITING_FOR_REVIEW" || summary.status === "TECHNICAL_FAILURE")
      && !evidenceIntakeCanContinue
    )
  );
}

export async function createRetainedCaseBeforeDocumentIntake({
  createCase,
  onCreated,
  onRegistryStop,
  onDocumentIntake,
}: {
  createCase: () => Promise<ZeroTouchCaseSummary>;
  onCreated: (created: ZeroTouchCaseSummary) => void;
  onRegistryStop: (created: ZeroTouchCaseSummary) => void;
  onDocumentIntake: (created: ZeroTouchCaseSummary) => Promise<void>;
}): Promise<{ created: ZeroTouchCaseSummary; intakeAttempted: boolean }> {
  const created = await createCase();
  onCreated(created);
  if (isRegistryIntakeUnavailable(created)) {
    onRegistryStop(created);
    return { created, intakeAttempted: false };
  }
  await onDocumentIntake(created);
  return { created, intakeAttempted: true };
}

export function resetNewCasePresentation({
  clearSummary,
  clearRetainedSummary,
  clearDocuments,
  clearOpenedCaseId,
  resetUen,
  resetJurisdiction,
  clearRequestError,
  clearPollingWarning,
  clearIntakeProgress,
  clearSubmitting,
  clearResolving,
}: {
  clearSummary: () => void;
  clearRetainedSummary: () => void;
  clearDocuments: () => void;
  clearOpenedCaseId: () => void;
  resetUen: () => void;
  resetJurisdiction: () => void;
  clearRequestError: () => void;
  clearPollingWarning: () => void;
  clearIntakeProgress: () => void;
  clearSubmitting: () => void;
  clearResolving: () => void;
}) {
  clearSummary();
  clearRetainedSummary();
  clearDocuments();
  clearOpenedCaseId();
  resetUen();
  resetJurisdiction();
  clearRequestError();
  clearPollingWarning();
  clearIntakeProgress();
  clearSubmitting();
  clearResolving();
}

export function targetedIntakeFailurePresentation(caseId: string, failures: string[]) {
  return {
    progress: "Targeted retry required",
    message: `Case ${caseId} was retained. Retry the same selection to continue: ${failures.join(" ")}`,
  };
}

const DOCUMENT_TYPES = UPLOAD_DOCUMENT_TYPES;
const SAFE_DOCUMENT_NAME = /^[A-Za-z0-9][A-Za-z0-9._ -]{0,94}\.(pdf|docx|txt|png|jpe?g|tiff?)$/i;

export function validateSelectedDocuments(files: File[]): { accepted: File[]; errors: string[] } {
  const accepted: File[] = [];
  const errors: string[] = [];
  const seen = new Set<string>();
  let totalBytes = 0;
  for (const file of files) {
    const key = intakeFileKey(file);
    if (seen.has(key)) continue;
    seen.add(key);
    const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    const expectedType = DOCUMENT_TYPES[extension];
    if (!SAFE_DOCUMENT_NAME.test(file.name) || !expectedType || file.type !== expectedType) {
      errors.push(`${file.name}: ${UPLOAD_ERRORS.unsupportedType}`);
      continue;
    }
    if (file.size <= 0) {
      errors.push(`${file.name}: this file is empty.`);
      continue;
    }
    if (file.size > MAX_INTAKE_FILE_BYTES) {
      errors.push(`${file.name}: ${UPLOAD_ERRORS.fileTooLarge}`);
      continue;
    }
    if (accepted.length >= MAX_INTAKE_FILE_COUNT) {
      errors.push(`${file.name}: the 20-file POC limit has been reached.`);
      continue;
    }
    if (totalBytes + file.size > MAX_INTAKE_TOTAL_BYTES) {
      errors.push(`${file.name}: ${UPLOAD_ERRORS.caseTotalTooLarge}`);
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
    const value = bytes / (1024 * 1024);
    return `${Number.isInteger(value) ? value : value.toFixed(1)} MiB`;
  }
  if (bytes >= 1024) {
    const value = bytes / 1024;
    return `${Number.isInteger(value) ? value : value.toFixed(1)} KiB`;
  }
  return `${bytes} B`;
}

export function selectedDocumentSummary(files: File[]): string {
  return `${files.length} ${files.length === 1 ? "document" : "documents"} selected · ${formatDocumentBytes(selectedDocumentTotalBytes(files))} / ${formatDocumentBytes(MAX_INTAKE_TOTAL_BYTES)}`;
}

type StartProgressStage = "idle" | "creating" | "uploading" | "starting" | "processing" | "waiting" | "completed" | "failed";
export interface StartProgress { stage: StartProgressStage; message: string; failedFile: string | null; }

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

export { formatTimestamp, shouldMaintainLiveProgress, shouldPollAutomation };

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
  return value.toFixed(2);
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
    ...UPLOAD_ERROR_BY_CODE,
    "OWNERSHIP_CYCLE": "Ownership graph contains circular relationships. Please review the ownership structure.",
    "OWNERSHIP_INCOMPLETE": "Incomplete ownership data detected. Some legal entities have no disclosed owners.",
    "DOCUMENT_LOW_CONFIDENCE": "Document extraction evidence score below threshold. Please review or upload a clearer document.",
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
    "DOCUMENT_LOW_CONFIDENCE": "One or more fields were extracted from the document with an extraction evidence score below the case-bound threshold. Please review the extracted values.",
    "DOCUMENT_FIELD_MISMATCH": "Extracted document data does not match the registry records. Please review and correct the mismatched fields.",
    "DOCUMENT_REQUIRED_FIELD_MISSING": "A required field is missing from the document extraction. Please provide additional documentation.",
    "OWNERSHIP_CYCLE": "Circular ownership relationships detected in the ownership graph. This prevents UBO calculation. Please verify the ownership structure.",
    "OWNERSHIP_INCOMPLETE": "Incomplete ownership chain: some legal entities have no disclosed owners. Cannot complete UBO analysis without this information.",
    "GOVERNMENT_STATUS_REQUIRED": "A Singapore Government entity needs a reviewed status document and an explicit RM confirmation instead of an ownership and UBO analysis.",
    "EXISTING_PARTY_REVIEW_REQUIRED": "A party with similar details already exists in the target system. Please review the match before proceeding.",
    "REGISTRY_REVIEW_REQUIRED": "Registry data validation requires human review. Please check the entity details.",
    "JURISDICTION_UNRESOLVED": "No authoritative jurisdiction observation is available. Registry retrieval has not started.",
    "JURISDICTION_CONFLICT": "Jurisdiction observations disagree. No registry provider was selected and review is required.",
    "REGISTRY_PROVIDER_NOT_IMPLEMENTED": "The jurisdiction is recognised, but this Singapore-only POC has no provider implementation for it.",
  };
  return explanations[blockerCode] || blockerCode.replaceAll("_", " ");
}

export function SimulationBanner({ profile }: { profile: SimulationProfile | null }) {
  if (import.meta.env.VITE_E2E_RECOVERY_DEMO === "document-refresh") {
    return <div className="environment-banner" role="status">
      <span className="environment-banner__label">
        Synthetic offline document refresh recovery fixture · Local document evidence and Mock target.
        Zero external provider calls; no interoperability is demonstrated.
      </span>
    </div>;
  }
  if (import.meta.env.VITE_E2E_RECOVERY_DEMO) {
    return (
      <div className="environment-banner" role="status">
        <span className="environment-banner__label">
          Slice C synthetic offline recovery fixture · zero external provider calls.
          Local registry/document evidence and inert XPI transport; no interoperability is demonstrated.
        </span>
      </div>
    );
  }
  const sourceLabel = profile
    ? profile.registry_provider_mode === "API_MARKETPLACE_PROTOCOL_TEST"
      ? "ACRA Marketplace protocol · synthetic offline test evidence"
      : profile.registry_provider_mode === "API_MARKETPLACE_MOCK"
      ? "ACRA API Marketplace Mock"
      : profile.registry_provider_mode === "LOCAL_MOCK"
        ? "ACRA Local Mock"
        : profile.registry_provider_mode === "GENERIC_SANDBOX"
          ? "ACRA Sandbox"
          : `${profile.registry_system} ${titleCaseEnvironment(profile.registry_environment)}`
    : null;
  const fullLabel = profile
    ? `${sourceLabel} | GoldTier ${titleCaseEnvironment(profile.target_environment)}${profile.target_environment === "SANDBOX" ? ` (${profile.target_provider_classification})` : ""} | IDP ${titleCaseEnvironment(profile.idp_environment)} (${profile.idp_provider}) | Ownership POC · Decimal engine | External access is backend-managed`
    : "Loading backend connector profile...";
  return (
    <div className="environment-banner" role="status" title={fullLabel}>
      <span className="environment-banner__dot" aria-hidden="true" />
      <span className="environment-banner__label">
        {profile ? `${sourceLabel} · GoldTier ${titleCaseEnvironment(profile.target_environment)}${profile.target_environment === "SANDBOX" ? ` (${profile.target_provider_classification})` : ""} · ${profile.persistence}` : "Loading profile…"}
      </span>
      <span className="sr-only">{fullLabel}</span>
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
          {confidencePercent(field.confidence)} evidence score (not probability)
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
  const targetLabel = goldTierJourneyLabel(summary.submission_plan.environment);
  const stages = [
    ["Registry", summary.readiness.registry.status],
    ["Document Review", summary.readiness.document.status],
    ["Ownership & UBO", summary.readiness.ownership.status],
    ["Readiness", summary.status],
    [targetLabel, summary.readiness.goldtier.status],
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
            the serialized {targetLabel} submission.
          </p>
        </div>
        <strong className={`clm-overall clm-overall--${summary.status}`}>
          {targetOutcomeLabel(summary.status, summary.submission_plan.environment)}
        </strong>
      </div>

      <ol className="clm-stepper" aria-label="CLM stages">
        {stages.map(([label, stageStatus], index) => (
          <li key={label} data-stage-status={stageStatus}>
            <span>{index + 1}</span>
            <div><strong>{label}</strong><small>{targetOutcomeLabel(stageStatus, summary.submission_plan.environment)}</small></div>
          </li>
        ))}
      </ol>

      <div className="clm-grid">
        <article>
          <h3>Target-submission blockers</h3>
          {summary.readiness.blockers.length ? (
            <ul className="clm-list clm-list--blockers">
              {summary.readiness.blockers.map((blocker) => <li key={blocker}>{blocker}</li>)}
            </ul>
          ) : <p className="ready-copy">No current target-submission blockers.</p>}
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
      {summary.submission_plan.request_preview && (
        <GoldTierRequestPreview preview={summary.submission_plan.request_preview} />
      )}

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
            ? `${targetLabel} submitted`
            : `Submit to ${targetLabel}`}
        </button>
      </div>

      {clmError && <div className="request-error" role="alert">{clmError}</div>}
      {summary.submission && (
        <div className="mock-submission-result" role="status">
          <strong>{targetOutcomeLabel(summary.status, summary.submission_plan.environment)}</strong>
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
      <button type="button" disabled>Submit to configured GoldTier</button>
    </section>
  );
}

export function invalidateClmReadiness(
  setSummary: (summary: ClmCaseSummary | null) => void,
  setRefreshing: (refreshing: boolean) => void,
) {
  setSummary(null);
  setRefreshing(true);
}

export async function refreshClmSummary(
  caseId: string,
  setSummary: (summary: ClmCaseSummary) => void,
  setRefreshing: (refreshing: boolean) => void,
) {
  try {
    setSummary(await fetchClmCase(caseId));
  } finally {
    setRefreshing(false);
  }
}

const AUTOMATION_STAGES = [
  ["REGISTRY", "Registry"],
  ["DOCUMENT", "Document verification"],
  ["OWNERSHIP", "Ownership & UBO"],
  ["READINESS", "Readiness"],
  ["MOCK_GOLDTIER", "GoldTier target"],
] as const;

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
          <strong>GoldTier submission completed</strong>
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
        <div><dt>{goldTierJourneyLabel(summary.clm.submission_plan.environment)} outcome</dt><dd>{targetOutcomeLabel(targetOutcome, summary.clm.submission_plan.environment)}</dd></div>
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

export function OperatorAccount({
  profile,
  onLogout,
}: {
  profile: AuthenticatedProfile;
  onLogout: () => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="operator-account">
      <span className="operator-account__prefix">Signed in as</span>
      <button
        type="button"
        className="operator-account__button"
        aria-expanded={open}
        aria-controls="operator-account-disclosure"
        onClick={() => setOpen((current) => !current)}
      >
        <span className="operator-account__identity">
          <span>{profile.display_name}</span>
          <span className="operator-account__metadata">
            {profile.role.replaceAll("_", " ")} · {profile.team_display_name ?? "Global scope"} · {profile.team_id ? `Coverage: ${profile.client_scope_label}` : profile.team_description}
          </span>
        </span>
        <span aria-hidden="true" className="operator-account__chevron">⌄</span>
      </button>
      {open && (
        <div id="operator-account-disclosure" className="operator-account__disclosure">
          <strong>{profile.role.replaceAll("_", " ")}</strong>
          <span>{profile.team_display_name ?? "Global scope"}</span>
          <span>{profile.team_description}</span>
          <button type="button" className="btn btn-ghost" onClick={onLogout}>Sign out</button>
        </div>
      )}
    </div>
  );
}

export function CasePortfolio({ cases, onOpen, persistence = "Process-local" }: {
  cases: ZeroTouchCaseListItem[];
  onOpen: (caseId: string) => void;
  persistence?: SimulationProfile["persistence"];
}) {
  const durable = persistence === "Mongo-backed durable POC";
  return <section className="case-portfolio"><p className="section-label">{durable ? "Durable case history" : "Process-local case history"}</p><h2>Recent CLM cases</h2><p>{durable ? "Mongo-backed durable POC — cases survive backend restart. This is not a production audit repository." : "Cases are retained only for the current backend process. Restarting the local POC clears this history."}</p>{cases.map((item) => <button type="button" key={item.case_id} onClick={() => onOpen(item.case_id)}>{item.legal_name ?? item.requested_uen} · {item.status}</button>)}</section>;
}

export function ReviewQueue({ cases, selectedCaseId, onOpen, persistence = "Process-local" }: {
  cases: ZeroTouchCaseListItem[];
  selectedCaseId?: string;
  onOpen: (caseId: string) => void;
  persistence?: SimulationProfile["persistence"];
}) {
  const durable = persistence === "Mongo-backed durable POC";
  return <section className="review-queue"><p className="section-label">Backend-authored {durable ? "durable" : "process-local"} queue</p><h2>Cases waiting for review</h2><p>{durable ? "Queue status survives backend restart; assignment remains session-only." : "Queue status is authoritative for the current backend process only; assignment remains session-only."}</p>{cases.map((item) => <button type="button" key={item.case_id} className={selectedCaseId === item.case_id ? "review-queue__item--active" : ""} onClick={() => onOpen(item.case_id)}>{item.legal_name ?? item.requested_uen} · {item.active_exception_count} active blocker(s)</button>)}</section>;
}

export function StartProgressPanel({ progress, summary, isSubmitting, onViewCase, onOpenReview, onRetry, onStartAnother }: {
  progress: StartProgress;
  summary: ZeroTouchCaseSummary | null;
  isSubmitting: boolean;
  onViewCase: () => void;
  onOpenReview: () => void;
  onRetry: () => void;
  onStartAnother: () => void;
}) {
  if (progress.stage === "idle") return null;
  return <section className={`start-progress start-progress--${progress.stage}`} role="status" aria-live="polite"><strong>{progress.message}</strong>{summary && <><h3>CLM onboarding created</h3><dl><div><dt>Case ID</dt><dd>{summary.case.case_id}</dd></div><div><dt>UEN</dt><dd>{summary.case.requested_uen}</dd></div><div><dt>Status</dt><dd>{summary.status}</dd></div></dl>{progress.failedFile && <p>Upload failed safely for {progress.failedFile}. Successfully received documents remain attached.</p>}<div><button type="button" onClick={onViewCase}>View case</button>{summary.status === "WAITING_FOR_REVIEW" && <button type="button" onClick={onOpenReview}>Open Review</button>}{progress.stage === "failed" && summary.status === "PENDING_INPUTS" && <button type="button" disabled={isSubmitting} onClick={onRetry}>Retry this case</button>}{(progress.stage === "completed" || progress.stage === "waiting") && <button type="button" disabled={isSubmitting} onClick={onStartAnother}>Start another case</button>}</div></>}</section>;
}

function reconciliationSourceValue(discrepancy: ReconciliationDiscrepancy, source: "REGISTRY" | "DOCUMENT_IDP"): string {
  const values = discrepancy.observations.filter((item) => item.source_kind === source).map((item) => item.normalized_value ?? "Not available");
  return values.length ? values.join(" · ") : "Not observed";
}

export function ReconciliationPanel({ summary, isResolving = false, onResolve }: {
  summary: ZeroTouchCaseSummary;
  isResolving?: boolean;
  onResolve?: (discrepancy: ReconciliationDiscrepancy, action: ReconciliationDecisionAction) => void;
  onReplace?: (documentId: string, eventCount: number, file: File) => void;
}) {
  const reconciliation = summary.reconciliation;
  if (!reconciliation) return null;
  const discrepancies = new Map(reconciliation.discrepancies.map((item) => [item.discrepancy_id, item]));
  return <section className="reconciliation-panel"><p className="section-label">Multi-source reconciliation</p><h2>Registry and document observations</h2><strong>{reconciliation.status}</strong><p>Neither source is authoritative by default. Values remain separate until an explicitly advertised backend action records a decision.</p>{reconciliation.fields.map((field) => { const discrepancy = field.discrepancy_id ? discrepancies.get(field.discrepancy_id) : undefined; const registry = field.observations.filter((item) => item.source_kind === "REGISTRY").map((item) => item.normalized_value ?? "Not available").join(" · "); const document = field.observations.filter((item) => item.source_kind === "DOCUMENT_IDP").map((item) => item.normalized_value ?? "Not available").join(" · "); return <div key={field.field_name}><strong>{fieldLabel(field.field_name)}</strong><span> Registry observation: {registry || "Not observed"}</span><span> Document observation: {document || "Not observed"}</span><span> {field.outcome}</span>{discrepancy?.decision && <small>Decision: {discrepancy.decision.action.replaceAll("_", " ")}</small>}</div>; })}{reconciliation.discrepancies.filter((item) => item.status !== "CANCELLED").map((discrepancy) => <article key={discrepancy.discrepancy_id}><p>Registry: {reconciliationSourceValue(discrepancy, "REGISTRY")} · Document: {reconciliationSourceValue(discrepancy, "DOCUMENT_IDP")}</p>{discrepancy.status === "OPEN" && onResolve && discrepancy.allowed_actions.map((action) => <button type="button" key={action} disabled={isResolving} onClick={() => onResolve(discrepancy, action)}>{action === "KEEP_REGISTRY_VALUE" ? "Keep registry value" : "Use document value"}</button>)}{discrepancy.decision && <p>Resolved by explicit POC operator action: {discrepancy.decision.action.replaceAll("_", " ")}. No reviewer identity or compliance authority is claimed.</p>}</article>)}</section>;
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
      <h2 id="document-evidence-heading">What the supplied PDF caused</h2>
      {documents.map((document) => (
        <details key={document.document_id} open={!document.superseded_by_document_id}>
          <summary>{document.display_name} — {document.superseded_by_document_id ? "SUPERSEDED" : "CURRENT"} — {document.state.replaceAll("_", " ")}</summary>
          <p>Deterministic extraction evidence score; not a calibrated probability. Quality, source agreement and verification are separate.</p>
          <div className="evidence-comparison" role="table" aria-label={`${document.display_name} document comparison`}>
            {document.fields.map((field) => (
              <div key={field.field_key} role="row" className={field.comparison_status === "MATCH" ? "" : "evidence-comparison--attention"}>
                <strong role="cell">{fieldLabel(field.field_key)}</strong>
                <span role="cell"><small>Registry</small>{field.canonical_value ?? "Not available"}</span>
                <span role="cell"><small>Document</small>{field.original_extracted_value ?? "Not extracted"}</span>
                <span role="cell"><small>Extraction evidence score (not probability)</small>{confidencePercent(field.confidence)} · {field.comparison_status.replaceAll("_", " ")}</span>
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
  return <section className="document-evidence-card" aria-labelledby="target-evidence-heading"><p className="section-label">{goldTierJourneyLabel(summary.clm.submission_plan.environment)} stage evidence</p><h2 id="target-evidence-heading">Server-authored target operations</h2><ol>{summary.target_operations.map((operation) => <li key={operation.operation}>{operation.operation} — {operation.status}</li>)}</ol></section>;
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
                      <dt>Extraction evidence score (not probability)</dt>
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
          <p>Upload a replacement to supersede the current document.</p>
          <p className="control-help">{UPLOAD_HELP_TEXT}</p>
          <label htmlFor={`replacement-${exception.exception_id}`}>Select replacement file</label>
          <input
            id={`replacement-${exception.exception_id}`}
            type="file"
            accept={UPLOAD_ACCEPT}
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
        This underlying case state is not an approval claim. Phase 05 readiness and
        GoldTier target submission are reported separately by the unified orchestration summary.
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
          <p className="section-label">GoldTier result</p>
          {caseData.goldtier_result ? (
            <dl>
              <div><dt>Party ID</dt><dd>{caseData.goldtier_result.party_id}</dd></div>
              <div><dt>Shell</dt><dd>{caseData.goldtier_result.shell_status}</dd></div>
              <div><dt>Policy</dt><dd>{caseData.goldtier_result.policy_status ?? "Not created"}</dd></div>
              <div><dt>Amend</dt><dd>{caseData.goldtier_result.amend_status ?? "Not attempted"}</dd></div>
            </dl>
          ) : (
            <p className="empty-copy">No GoldTier customer result is retained.</p>
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

export interface AppProps {
  demoControlsEnabled?: boolean;
  actor: AuthenticatedProfile;
  onLogout: () => void;
}

interface LiveIntakeOperation {
  readonly generation: number;
  readonly actorUserId: string;
  readonly caseId: string | null;
  readonly demo: boolean;
  readonly files: readonly File[];
}

export default function App({
  demoControlsEnabled = import.meta.env.VITE_DEMO_CONTROLS_ENABLED === "true",
  actor,
  onLogout,
}: AppProps) {
  const [caseQueuePresentation, setCaseQueuePresentation] =
    useState<CaseQueuePresentationState>(DEFAULT_CASE_QUEUE_PRESENTATION);
  const [uen, setUen] = useState("");
  const [legalName, setLegalName] = useState("");
  const [countryOfIncorporation, setCountryOfIncorporation] =
    useState<JurisdictionSelection>("");
  const [documentFiles, setDocumentFiles] = useState<File[]>([]);
  const [demoScenario, setDemoScenario] = useState<ZeroTouchDemoScenario>("STRAIGHT_THROUGH");
  const [directorTeamId, setDirectorTeamId] = useState<TeamId | "">("");
  const [teamOptions, setTeamOptions] = useState<AuthenticatedTeam[]>([]);
  const [casePriority, setCasePriority] = useState<number | "">("");
  const [deleteCurrentCaseOpen, setDeleteCurrentCaseOpen] = useState(false);
  // D-105: the case Support asked the AI Assistant about from a Knowledge Review page.
  const [askedAbout, setAskedAbout] = useState<{ caseId: string; question: string; nonce: number } | null>(null);
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const location = useLocation();
  const routeCapability = requiredCapabilityForPath(location.pathname);
  const routeCanLoadWorkspace = routeCapability !== null
    && actor.capabilities.includes(routeCapability);
  const profileQuery = useQuery({
    ...executionProfileQueryOptions(actor.user_id),
    enabled: routeCanLoadWorkspace,
  });
  const simulationProfile = profileQuery.data ?? null;
  const [summary, setSummary] = useState<ZeroTouchCaseSummary | null>(null);
  const [retainedCreatedSummary, setRetainedCreatedSummary] = useState<ZeroTouchCaseSummary | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isResolving, setIsResolving] = useState(false);
  const [requestError, setRequestError] = useState<string | null>(null);
  // Structured form of the latest upload failure; used only while requestError still shows it.
  const [uploadRejection, setUploadRejection] = useState<UploadRejection | null>(null);
  const [intakeProgress, setIntakeProgress] = useState<string | null>(null);
  const [pollingWarning, setPollingWarning] = useState<string | null>(null);
  const journeyGeneration = useRef(0);
  const mounted = useRef(true);
  const actorUserId = useRef(actor.user_id);
  const locationPathname = useRef(location.pathname);
  locationPathname.current = location.pathname;
  const resolutionActive = useRef(false);
  const intakePending = useRef<LiveIntakeOperation | null>(null);
  const intakeCaseRef = useRef<LiveIntakeOperation | null>(null);
  const successfulIntakeFilesRef = useRef(new Set<string>());
  const failedIntakeDocumentsRef = useRef(new Map<string, string>());

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      journeyGeneration.current += 1;
      resolutionActive.current = false;
      intakePending.current = null;
      intakeCaseRef.current = null;
      successfulIntakeFilesRef.current.clear();
      failedIntakeDocumentsRef.current.clear();
    };
  }, []);

  useEffect(() => {
    if (actorUserId.current === actor.user_id) return;
    actorUserId.current = actor.user_id;
    journeyGeneration.current += 1;
    resolutionActive.current = false;
    intakePending.current = null;
    intakeCaseRef.current = null;
    successfulIntakeFilesRef.current.clear();
    failedIntakeDocumentsRef.current.clear();
    setSummary(null);
    setRetainedCreatedSummary(null);
    setDocumentFiles([]);
    setUen("");
    setCountryOfIncorporation("");
    setCasePriority("");
    setDemoScenario("STRAIGHT_THROUGH");
    setLegalName("");
    setDirectorTeamId("");
    setTeamOptions([]);
    setDeleteCurrentCaseOpen(false);
    setRequestError(null);
    setPollingWarning(null);
    setIntakeProgress(null);
    setIsSubmitting(false);
    setIsResolving(false);
  }, [actor.user_id]);

  function isCurrentIntakeOperation(operation: LiveIntakeOperation): boolean {
    return mounted.current
      && actorUserId.current === operation.actorUserId
      && journeyGeneration.current === operation.generation
      && intakeCaseRef.current?.generation === operation.generation;
  }

  useEffect(() => {
    if (profileQuery.isError) setRequestError("Connector profile discovery is unavailable.");
  }, [profileQuery.isError]);

  useEffect(() => {
    if (
      actor.role === "DIRECTOR"
      && routeCanLoadWorkspace
      && location.pathname.startsWith(paths.newOnboarding)
    ) {
      void fetchTeamOptions().then(setTeamOptions).catch(() => setTeamOptions([]));
    }
  }, [actor.role, actor.user_id, location.pathname, routeCanLoadWorkspace]);

  useEffect(() => {
    const intakeActive = isSubmitting && Boolean(intakeCaseRef.current?.caseId);
    if (!summary || !shouldMaintainLiveProgress(summary.status, intakeActive)) return;
    const generation = journeyGeneration.current;
    const activeCaseId = summary.case.case_id;
    return startAutomationPolling({
      caseId: activeCaseId,
      generation,
      currentGeneration: () => journeyGeneration.current,
      fetchCase: fetchZeroTouchCase,
      onUpdate: (latest) => {
        setSummary(latest);
        caseSummaryMutationEffect(queryClient, actor.user_id, latest);
      },
      onWarning: setPollingWarning,
      shouldContinue: (status) => shouldMaintainLiveProgress(status, intakeActive),
    });
  }, [actor.user_id, isSubmitting, queryClient, summary?.case.case_id, summary?.status, summary?.version]);

  async function beginJourney(demoScenario?: ZeroTouchDemoScenario) {
    if (resolutionActive.current || intakePending.current) return;
    if (actor.role === "DIRECTOR" && !directorTeamId) {
      setRequestError("Select a team before creating the case.");
      return;
    }
    const validationError = validateIntakeFiles(documentFiles);
    if (validationError) { setRequestError(validationError); return; }
    const generation = ++journeyGeneration.current;
    const previousOperation = intakeCaseRef.current;
    const operation: LiveIntakeOperation = {
      generation,
      actorUserId: actor.user_id,
      caseId: previousOperation?.caseId ?? null,
      demo: previousOperation?.demo ?? demoScenario !== undefined,
      files: [...documentFiles],
    };
    intakeCaseRef.current = operation;
    intakePending.current = operation;
    setIsSubmitting(true);
    setRequestError(null);
    setIntakeProgress(operation.caseId ? "Retrying retained intake…" : "Creating case…");
    if (!operation.caseId) setSummary(null);

    const processDocumentIntake = async (
      intakeCase: LiveIntakeOperation & { caseId: string },
    ): Promise<boolean> => {
      const failures: string[] = [];
      const uploadFailures: IntakeUploadFailure[] = [];
      for (const [index, file] of intakeCase.files.entries()) {
        if (!isCurrentIntakeOperation(intakeCase)) return false;
        setIntakeProgress(`Uploading document ${index + 1} of ${intakeCase.files.length}…`);
        const key = intakeFileKey(file);
        if (successfulIntakeFilesRef.current.has(key)) continue;
        try {
          const failedDocumentId = failedIntakeDocumentsRef.current.get(key);
          const record = failedDocumentId
            ? await retryZeroTouchIntakeDocument(intakeCase.caseId, failedDocumentId, file, intakeCase.demo)
            : await intakeZeroTouchDocument(intakeCase.caseId, file, intakeCase.demo);
          if (!isCurrentIntakeOperation(intakeCase)) return false;
          if (record.state === "FAILED") {
            failedIntakeDocumentsRef.current.set(key, record.document_id);
            failures.push(`${file.name}: ${record.error?.message ?? "processing failed"}`);
            uploadFailures.push({ fileName: file.name, message: record.error?.message ?? "processing failed", code: record.error?.code ?? null, rejectedBeforeStorage: false });
          } else {
            failedIntakeDocumentsRef.current.delete(key);
            successfulIntakeFilesRef.current.add(key);
          }
        } catch (uploadError) {
          if (!isCurrentIntakeOperation(intakeCase)) return false;
          if (uploadError instanceof ApiError && uploadError.detail?.document_id) {
            failedIntakeDocumentsRef.current.set(key, uploadError.detail.document_id);
          }
          failures.push(`${file.name}: ${uploadError instanceof Error ? uploadError.message : "upload failed"}`);
          uploadFailures.push({
            fileName: file.name,
            message: uploadError instanceof Error ? uploadError.message : "upload failed",
            code: uploadError instanceof ApiError ? uploadError.code : null,
            // A stored failed document keeps its existing retry/replace flow.
            rejectedBeforeStorage: uploadError instanceof ApiError && !failedIntakeDocumentsRef.current.has(key),
          });
        }
      }
      if (!isCurrentIntakeOperation(intakeCase)) return false;
      if (failures.length > 0) {
        const failurePresentation = targetedIntakeFailurePresentation(intakeCase.caseId, failures);
        setIntakeProgress(failurePresentation.progress);
        setUploadRejection(uploadRejectionPresentation(failurePresentation.message, uploadFailures));
        setRequestError(failurePresentation.message);
        return false;
      }
      setIntakeProgress("Completing intake…");
      const completed = await completeZeroTouchIntake(
        intakeCase.caseId,
        intakeCase.files.length,
        intakeCase.demo,
      );
      if (!isCurrentIntakeOperation(intakeCase)) return false;
      setSummary(completed);
      await caseSupportingMutationEffect(queryClient, actor.user_id, completed);
      if (!isCurrentIntakeOperation(intakeCase)) return false;
      setIntakeProgress(completed.status === "COMPLETED" ? "Completed" : "Processing case…");
      return true;
    };

    try {
      if (!operation.caseId) {
        let retainedOperation: (LiveIntakeOperation & { caseId: string }) | null = null;
        let intakeCompleted = false;
        await createRetainedCaseBeforeDocumentIntake({
          createCase: () => createZeroTouchCase(
            uen,
            demoScenario,
            countryOfIncorporation || undefined,
            actor.role === "DIRECTOR" ? directorTeamId || undefined : undefined,
            casePriority === "" ? undefined : casePriority,
            legalName || undefined,
          ),
          onCreated: (created) => {
            if (!isCurrentIntakeOperation(operation)) return;
            retainedOperation = {
              ...operation,
              caseId: created.case.case_id,
            };
            intakeCaseRef.current = retainedOperation;
            caseCreatedEffect(queryClient, actor.user_id, created);
            setSummary(created);
            setRetainedCreatedSummary(created);
            if (locationPathname.current === paths.newOnboarding) {
              navigate(paths.caseDetail(created.case.case_id), { replace: true });
            }
          },
          onRegistryStop: (created) => {
            if (!retainedOperation || !isCurrentIntakeOperation(retainedOperation)) return;
            setSummary(created);
            caseSummaryMutationEffect(queryClient, actor.user_id, created);
            setIntakeProgress(null);
          },
          onDocumentIntake: async () => {
            if (retainedOperation && isCurrentIntakeOperation(retainedOperation)) {
              intakeCompleted = await processDocumentIntake(retainedOperation);
            }
          },
        });
        // Once every selected document is in, the case page owns the case and New onboarding
        // returns to a blank form. Otherwise (registry stop, failed upload) the files stay
        // pending so the case page can offer "Upload now" after the issue is fixed.
        if (isCurrentIntakeOperation(operation) && (intakeCompleted || operation.files.length === 0)) resetOnboardingForm();
        return;
      }
      const retryCompleted = await processDocumentIntake({ ...operation, caseId: operation.caseId });
      if (isCurrentIntakeOperation(operation) && retryCompleted) resetOnboardingForm();
    } catch (error) {
      if (!isCurrentIntakeOperation(operation)) return;
      const retainedCase = intakeCaseRef.current?.caseId;
      setRequestError(`${retainedCase ? `Case ${retainedCase} was retained. ` : ""}${error instanceof Error ? error.message : "Unable to start onboarding."}`);
      setIntakeProgress("Onboarding paused");
      if (!retainedCase) {
        setIsSubmitting(false);
        intakeCaseRef.current = null;
      }
    } finally {
      if (intakePending.current === operation) intakePending.current = null;
      if (isCurrentIntakeOperation(operation)) setIsSubmitting(false);
    }
  }

  function handleStart(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void beginJourney();
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
      if (generation === journeyGeneration.current) {
        await caseSupportingMutationEffect(queryClient, actor.user_id, updated);
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        try {
          const refreshed = await fetchZeroTouchCase(activeCaseId);
          if (generation === journeyGeneration.current) {
            setSummary(refreshed);
            await caseSupportingMutationEffect(queryClient, actor.user_id, refreshed);
          }
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

  async function handleReconciliation(
    discrepancy: ReconciliationDiscrepancy,
    action: ReconciliationDecisionAction,
  ) {
    if (!summary || !summary.reconciliation || resolutionActive.current) return;
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
      if (generation === journeyGeneration.current) {
        setSummary(updated);
        await caseSupportingMutationEffect(queryClient, actor.user_id, updated);
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        try {
          const refreshed = await fetchZeroTouchCase(activeCaseId);
          if (generation === journeyGeneration.current) {
            setSummary(refreshed);
            await caseSupportingMutationEffect(queryClient, actor.user_id, refreshed);
          }
        } catch {
          // Preserve the safe stale-decision message returned by the original request.
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

  async function handleReplacement(documentId: string, eventCount: number, file: File) {
    if (!summary || resolutionActive.current) return;
    resolutionActive.current = true;
    setIsResolving(true);
    setRequestError(null);
    try {
      const updated = await replaceZeroTouchDocument(summary.case.case_id, documentId, eventCount, file);
      setSummary(updated);
      await caseSupportingMutationEffect(queryClient, actor.user_id, updated);
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "Replacement evidence failed.");
    } finally {
      resolutionActive.current = false;
      setIsResolving(false);
    }
  }

  async function handleRecovery() {
    if (!summary || isSubmitting || isResolving) return;
    setIsSubmitting(true);
    setRequestError(null);
    try {
      const updated = await resumeZeroTouchCase(summary.case.case_id);
      setSummary(updated);
      await caseSupportingMutationEffect(queryClient, actor.user_id, updated);
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "Finalization recovery failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleStartNewCase() {
    resetOnboardingForm();
    navigate(paths.newOnboarding, { replace: true });
  }

  function resetOnboardingForm() {
    journeyGeneration.current += 1;
    resolutionActive.current = false;
    intakePending.current = null;
    resetNewCasePresentation({
      clearSummary: () => setSummary(null),
      clearRetainedSummary: () => setRetainedCreatedSummary(null),
      clearDocuments: () => setDocumentFiles([]),
      clearOpenedCaseId: () => undefined,
      resetUen: () => setUen(""),
      resetJurisdiction: () => setCountryOfIncorporation(""),
      clearRequestError: () => setRequestError(null),
      clearPollingWarning: () => setPollingWarning(null),
      clearIntakeProgress: () => setIntakeProgress(null),
      clearSubmitting: () => setIsSubmitting(false),
      clearResolving: () => setIsResolving(false),
    });
    setCasePriority("");
    setDemoScenario("STRAIGHT_THROUGH");
    setLegalName("");
    setDirectorTeamId("");
    setDeleteCurrentCaseOpen(false);
    setUploadRejection(null);
    intakeCaseRef.current = null;
    successfulIntakeFilesRef.current.clear();
    failedIntakeDocumentsRef.current.clear();
  }

  async function handleDeleteCurrentCase() {
    if (!summary) return;
    const caseId = summary.case.case_id;
    const generation = ++journeyGeneration.current;
    await deleteZeroTouchCase(caseId);
    if (!mounted.current || generation !== journeyGeneration.current) return;
    await caseDeletedEffect(queryClient, actor.user_id, caseId);
    if (!mounted.current || generation !== journeyGeneration.current) return;
    handleStartNewCase();
  }

  function handleDocumentFilesChange(files: File[]) {
    if (intakeCaseRef.current) {
      setRequestError(`Case ${intakeCaseRef.current.caseId} already exists. Retry the same selection or start a new case before changing files.`);
      return;
    }
    const validationError = validateIntakeFiles(files);
    if (validationError && files.length > 0) { setRequestError(validationError); return; }
    setRequestError(null);
    setDocumentFiles(files);
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

  const retainedIntakeCaseId = retainedCreatedSummary?.case.case_id ?? null;
  const aiAssistantContext = aiAssistantContextFor(location.pathname, retainedIntakeCaseId);
  // D-105: on a Knowledge Review page, Support opens the AI Assistant on the conversation's case;
  // it goes back to the rules chat once Support leaves that page.
  const assistantFocus = location.pathname === paths.knowledgeReview ? askedAbout : null;
  const liveOnboarding = (
    <>
      <HomeOnboarding
        summary={summary}
        uen={uen}
        onUenChange={setUen}
        legalName={legalName}
        onLegalNameChange={setLegalName}
        countryOfIncorporation={countryOfIncorporation}
        onCountryChange={setCountryOfIncorporation}
        documentFiles={documentFiles}
        onDocumentFilesChange={handleDocumentFilesChange}
        caseTeamDisplayName={actor.team_display_name ?? "Team unavailable"}
        creationTeamSelection={actor.role === "DIRECTOR" ? {
          teamId: directorTeamId,
          options: teamOptions,
          onChange: setDirectorTeamId,
        } : undefined}
        priority={casePriority}
        onPriorityChange={setCasePriority}
        isSubmitting={isSubmitting}
        isResolving={isResolving}
        creationDisabled={actor.role === "DIRECTOR" && !directorTeamId}
        requestError={requestError}
        pollingWarning={pollingWarning}
        intakeProgress={intakeProgress}
        onStart={handleStart}
        onResolve={(exception, action) => void handleResolution(exception, action)}
        onReconcile={(discrepancy, action) => void handleReconciliation(discrepancy, action)}
        onReplace={(documentId, eventCount, file) => void handleReplacement(documentId, eventCount, file)}
        onRecovery={() => void handleRecovery()}
        onStartNewCase={handleStartNewCase}
        onOpenCaseDetail={(caseId, focusNodeId) => navigate(
          focusNodeId
            ? `${paths.caseDetail(caseId)}?focus=${encodeURIComponent(focusNodeId)}`
            : paths.caseDetail(caseId),
        )}
        canDeleteCurrentCase={actor.role === "DIRECTOR" || actor.role === "RELATIONSHIP_MANAGER"}
        onDeleteCurrentCase={() => setDeleteCurrentCaseOpen(true)}
        onViewAudit={(caseId) => navigate(paths.auditCase(caseId))}
        registryProviderMode={simulationProfile?.registry_provider_mode}
        onRetryIntake={() => void beginJourney()}
      />
      {demoControlsEnabled && !summary && (
        <section className="ds-root ds-page" aria-label="Demo/Test Controls">
          <div className="card">
            <p className="card-kicker">Demo/Test Controls</p>
            <label htmlFor="demo-scenario">Integrated synthetic scenario</label>
            <select id="demo-scenario" className="input" value={demoScenario} onChange={(event) => setDemoScenario(event.target.value as ZeroTouchDemoScenario)}>
              <option value="SME_STRAIGHT_THROUGH">SME straight through with advisory intelligence</option>
              <option value="SME_AMBIGUOUS_ENTITY">SME ambiguous entity review</option>
              <option value="STRAIGHT_THROUGH">Straight through</option>
              <option value="DOCUMENT_DISCREPANCY">Document discrepancy</option>
              <option value="LOW_CONFIDENCE_DOCUMENT">Low confidence</option>
              <option value="OWNERSHIP_CYCLE">Ownership cycle</option>
              <option value="RECOVERY">Recovery</option>
              <option value="TECHNICAL_FAILURE">Technical failure</option>
            </select>
            <button type="button" className="btn btn-secondary" disabled={isSubmitting || (actor.role === "DIRECTOR" && !directorTeamId)} onClick={() => void beginJourney(demoScenario)}>Run selected demo</button>
          </div>
        </section>
      )}
      {deleteCurrentCaseOpen && summary && (
        <DeleteCaseDialog
          caseId={summary.case.case_id}
          companyName={summary.case.entity?.legal_name ?? summary.case.requested_uen}
          requestedUen={summary.case.requested_uen}
          mutationDisabled={isSubmitting || isResolving}
          onCancel={() => setDeleteCurrentCaseOpen(false)}
          onConfirm={handleDeleteCurrentCase}
        />
      )}
    </>
  );

  return (
    <main className="ds-root ds-shell">
      <WorkspaceTabs
        actor={actor}
        retainedIntakeCaseId={retainedIntakeCaseId}
        trailing={
          <>
            <SimulationBanner profile={simulationProfile} />
            <OperatorAccount profile={actor} onLogout={onLogout} />
          </>
        }
      />
      <div className="ds-content">
        <WorkspaceRoutes
          actor={actor}
          retainedIntakeCaseId={retainedIntakeCaseId}
          dashboard={<Dashboard actor={actor} />}
          gtcDashboard={<GtcDashboard />}
          periodicReviewDashboard={<PeriodicReviewDashboard />}
          newOnboarding={(routeCaseId) => (
            routeCaseId && routeCaseId !== retainedIntakeCaseId
              ? <RetainedIntakeRecovery actor={actor} caseId={routeCaseId} onStartFresh={handleStartNewCase} />
              : liveOnboarding
          )}
          cases={(
            <CaseQueue
              actor={actor}
              presentation={caseQueuePresentation}
              onPresentationChange={setCaseQueuePresentation}
            />
          )}
          caseDetail={(caseId) => sampleCaseIdFromUrlId(caseId) ? (
            <SampleCaseDetail sampleCaseId={sampleCaseIdFromUrlId(caseId)!} actor={actor} />
          ) : (
            <CaseDetail
              caseId={caseId}
              actor={actor}
              onBack={() => navigate(paths.cases)}
              onViewAudit={(auditCaseId) => navigate(paths.auditCase(auditCaseId))}
              registryProviderMode={simulationProfile?.registry_provider_mode}
              initialFocusNodeId={new URLSearchParams(location.search).get("focus") ?? undefined}
              // Deleting the case New onboarding is still holding returns New onboarding to a blank form.
              onDeleted={(deletedCaseId) => { if (deletedCaseId === retainedIntakeCaseId) resetOnboardingForm(); }}
              pendingDocuments={caseId === retainedIntakeCaseId && documentFiles.length > 0 ? {
                fileNames: documentFiles.map(file => file.name),
                busy: isSubmitting,
                progress: intakeProgress,
                error: requestError,
                rejection: uploadRejection && uploadRejection.forMessage === requestError ? uploadRejection : null,
                onUpload: () => void beginJourney(),
                onDiscard: resetOnboardingForm,
              } : undefined}
            />
          )}
          audit={(caseId) => <AuditTrail actor={actor} caseId={caseId} />}
          policy={<PolicyRules actor={actor} />}
          workflowDesigner={<WorkflowDesigner key={actor.user_id} actor={actor} />}
          adminUsers={<AdminUsers />}
          adminTeams={<AdminTeams />}
          goldtierSandbox={<GoldTierSandbox key={actor.user_id} actor={actor} />}
          acraDiagnostics={<AcraDiagnostics key={actor.user_id} actor={actor} />}
          aiModels={<AiModelManagement key={actor.user_id} actor={actor} />}
          workflows={<WorkflowManager key={actor.user_id} actor={actor} />}
          workflowTab={(workflowId) => <WorkflowTab key={workflowId} actor={actor} workflowId={workflowId} onOpenRun={(runId) => navigate(paths.workflowRun(workflowId, runId))} />}
          workflowCases={(workflowId) => <WorkflowCasesPage key={workflowId} actor={actor} workflowId={workflowId} onOpenRun={(runId) => navigate(paths.workflowRun(workflowId, runId))} />}
          workflowRun={(workflowId, runId) => <WorkflowRunPage key={runId} actor={actor} workflowId={workflowId} runId={runId} onBack={() => navigate(paths.workflowCases(workflowId))} />}
          knowledgeReview={
            <KnowledgeReview
              key={actor.user_id}
              onAskAboutCase={(caseId, question) =>
                setAskedAbout((current) => ({ caseId, question, nonce: (current?.nonce ?? 0) + 1 }))}
              onLeaveCase={() => setAskedAbout(null)}
            />
          }
        />
      </div>
      {/* Only for users who can use it: case users, and Support (D-105). HR has neither. */}
      {(actor.capabilities.includes("CASE_ACCESS") || actor.capabilities.includes("KNOWLEDGE_REVIEW")) && (
        <AiAssistantPanel
          key={actor.user_id}
          caseId={assistantFocus?.caseId ?? aiAssistantContext.caseId}
          askAbout={assistantFocus}
          onboardingWithoutCase={aiAssistantContext.onboardingWithoutCase}
          onOpenCases={() => navigate(paths.cases)}
          onOpenCase={(id) => navigate(paths.caseDetail(id))}
          canChatWithoutCase={actor.capabilities.includes("KNOWLEDGE_REVIEW") && !actor.capabilities.includes("CASE_ACCESS")}
          canGeneralChat={actor.capabilities.includes("CASE_ACCESS")}
        />
      )}
    </main>
  );
}
