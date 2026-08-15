import { useEffect, useRef, useState, type FormEvent } from "react";

import {
  analyzeOwnership,
  ApiError,
  attachZeroTouchDocument,
  createClmCase,
  evaluateClmReadiness,
  fetchClmCase,
  fetchDocuments,
  fetchMockScenarios,
  fetchExecutionProfile,
  fetchOwnership,
  fetchUatEvidence,
  fetchZeroTouchCase,
  loadMockOwnership,
  reviewDocument,
  resolveZeroTouchException,
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
  SimulationProfile,
  ExceptionResolutionAction,
  ZeroTouchCaseSummary,
  ZeroTouchDemoScenario,
  ZeroTouchException,
} from "./types";

const DEFAULT_UEN = "202400001A";

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

function titleCaseEnvironment(value: "MOCK" | "SANDBOX"): string {
  return value === "MOCK" ? "Mock" : "Sandbox";
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

export function SimulationBanner({ profile }: { profile: SimulationProfile | null }) {
  const sourceLabel = profile
    ? `${profile.registry_system} ${titleCaseEnvironment(profile.registry_environment)}`
    : null;
  return (
    <div className="environment-banner" role="status">
      <span aria-hidden="true" />
      {profile
        ? `${sourceLabel} | GoldTier Mock | IDP Mock | Ownership Mock | External access is backend-managed`
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
          {documentError}
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
          <strong>Human review required — calculation is not definitive.</strong>
          <ul>
            {record.issues.map((issue) => (
              <li key={`${issue.code}-${issue.affected_party_ids.join("-")}`}>
                {issue.code}: {issue.message}
              </li>
            ))}
          </ul>
        </div>
      )}

      {record.relationships.length > 0 && (
        <div className="ownership-relationships">
          <h4>Ownership structure</h4>
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

export function SponsorCaseSummary({ summary }: { summary: ZeroTouchCaseSummary }) {
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
    </section>
  );
}

export function HumanReviewPanel({
  exception,
  isResolving,
  onResolve,
}: {
  exception: ZeroTouchException;
  isResolving: boolean;
  onResolve: (action: ExceptionResolutionAction) => void;
}) {
  return (
    <section className="human-review-card" aria-labelledby="review-required-heading">
      <p className="section-label">Human review required</p>
      <h2 id="review-required-heading">{exception.stage.replaceAll("_", " ")}</h2>
      <div className="review-reason">
        <span>Current blockers</span>
        <ol className="blocker-list">
          {exception.blocker_codes.map((blockerCode) => (
            <li key={blockerCode}>
              <span>{blockerCode.replaceAll("_", " ")}</span>
              <code>{blockerCode}</code>
            </li>
          ))}
        </ol>
      </div>
      <p>{exception.explanation}</p>
      {exception.evidence.map((evidence, index) => (
        <article className="exception-evidence" key={`${evidence.field_key ?? "evidence"}-${index}`}>
          <h3>{fieldLabel(evidence.field_key ?? "Evidence")}</h3>
          <dl>
            <div><dt>Registry</dt><dd>{evidence.registry_value ?? "Not available"}</dd></div>
            <div><dt>Document</dt><dd>{evidence.document_value ?? "Not available"}</dd></div>
            {evidence.confidence !== null && (
              <div><dt>Confidence</dt><dd>{confidencePercent(evidence.confidence)}</dd></div>
            )}
          </dl>
        </article>
      ))}
      <div className="exception-actions">
        {exception.available_actions.map((action) => (
          <button key={action} type="button" disabled={isResolving} onClick={() => onResolve(action)}>
            {action === "KEEP_REGISTRY_VALUE" ? "Keep registry values" : "Request more information"}
          </button>
        ))}
        {exception.available_actions.length === 0 && (
          <p>Corrected or replacement evidence is required; automatic target replay is disabled.</p>
        )}
      </div>
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
  const [uen, setUen] = useState(DEFAULT_UEN);
  const [documentFile, setDocumentFile] = useState<File | null>(null);
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

  useEffect(() => {
    void fetchExecutionProfile()
      .then(setSimulationProfile)
      .catch(() => setRequestError("Connector profile discovery is unavailable."));
  }, []);

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

  async function handleStart(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (resolutionActive.current) return;
    if (!documentFile) {
      setRequestError("Select the required synthetic PDF before starting onboarding.");
      return;
    }
    setIsSubmitting(true);
    journeyGeneration.current += 1;
    setRequestError(null);
    setSummary(null);
    let created: ZeroTouchCaseSummary | null = null;
    try {
      created = await createZeroTouchCase(
        uen,
        demoControlsEnabled ? demoScenario : undefined,
      );
      setSummary(created);
      const completed = await attachZeroTouchDocument(
        created.case.case_id,
        documentFile,
        demoControlsEnabled,
      );
      setSummary(completed);
    } catch (error) {
      if (created) {
        try {
          setSummary(await fetchZeroTouchCase(created.case.case_id));
        } catch {
          // The safe original error remains the operator-facing result.
        }
      }
      setRequestError(error instanceof Error ? error.message : "Unable to start onboarding.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleOpenCase(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (resolutionActive.current) return;
    const generation = ++journeyGeneration.current;
    setIsSubmitting(true);
    setRequestError(null);
    setPollingWarning(null);
    setSummary(null);
    try {
      const opened = await fetchZeroTouchCase(caseId.trim());
      if (generation === journeyGeneration.current) setSummary(opened);
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "Unable to open the case.");
    } finally {
      setIsSubmitting(false);
    }
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
        <h1>Onboarding that moves by itself—and pauses when judgment matters.</h1>
        <p className="summary">
          Supply the initial registry identity and supporting document once. Deterministic
          verification, ownership analysis, readiness, and Mock submission then progress
          automatically.
        </p>
      </header>

      <section className="launch-card zero-touch-launch" aria-labelledby="onboarding-heading">
        <div>
          <p className="section-label">Corporate onboarding</p>
          <h2 id="onboarding-heading">Start onboarding</h2>
          <p>Only fictional, synthetic PDF evidence is permitted in this local POC.</p>
        </div>
        <form onSubmit={(event) => void handleStart(event)} className="zero-touch-form">
          <label htmlFor="zero-touch-uen">Singapore UEN</label>
          <input
            id="zero-touch-uen"
            value={uen}
            onChange={(event) => setUen(event.target.value.toUpperCase())}
            maxLength={10}
            required
          />
          <label htmlFor="zero-touch-document">Supporting PDF</label>
          <input
            id="zero-touch-document"
            type="file"
            accept="application/pdf,.pdf"
            onChange={(event) => setDocumentFile(event.target.files?.[0] ?? null)}
            required
          />
          <button type="submit" disabled={isSubmitting || isResolving}>
            {isSubmitting ? "Starting onboarding…" : "Start onboarding"}
          </button>
        </form>
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

      {demoControlsEnabled && (
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
          <details className="legacy-controls">
            <summary>Legacy manual diagnostics</summary>
            <LegacyApp />
          </details>
        </details>
      )}

      {requestError && <div className="request-error" role="alert">{requestError}</div>}
      {pollingWarning && <div className="polling-warning" role="status">{pollingWarning}</div>}
      {summary && (
        <>
          <OnboardingProgress summary={summary} />
          <SponsorCaseSummary summary={summary} />
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
          {summary.status === "WAITING_FOR_REVIEW" && summary.active_exceptions.map((exception) => (
            <HumanReviewPanel
              key={exception.exception_id}
              exception={exception}
              isResolving={isResolving}
              onResolve={(action) => void handleResolution(exception, action)}
            />
          ))}
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
    </main>
  );
}
