import { useEffect, useState, type FormEvent } from "react";

import {
  analyzeOwnership,
  createOnboardingCase,
  fetchDocuments,
  fetchMockScenarios,
  fetchOnboardingCase,
  fetchOwnership,
  loadMockOwnership,
  reviewDocument,
  uploadDocument,
} from "./api";
import type {
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
} from "./types";

const DEFAULT_UEN = "202400001A";

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

function DocumentPanel({
  caseData,
  threshold,
}: {
  caseData: OnboardingCase;
  threshold: number;
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
      replaceDocument(await uploadDocument(caseData.case_id, file, scenario));
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
        await reviewDocument(
          caseData.case_id,
          activeDocument.document_id,
          fieldKey,
          decision,
          correctedValue,
          note,
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

function OwnershipPanel({
  caseData,
  configuredThreshold,
}: {
  caseData: OnboardingCase;
  configuredThreshold: string;
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
      setRecord(await loadMockOwnership(caseData.case_id, scenario));
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
      setRecord(await analyzeOwnership(caseData.case_id));
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
        This state covers the accepted registry and Mock GoldTier stages only. It does not
        include document review or Ready-for-Approval.
        Ownership analysis is an independent provisional sub-workflow.
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

export default function App() {
  const [uen, setUen] = useState(DEFAULT_UEN);
  const [caseId, setCaseId] = useState("");
  const [scenarios, setScenarios] = useState<MockScenario[]>([]);
  const [simulationProfile, setSimulationProfile] = useState<SimulationProfile | null>(null);
  const [caseData, setCaseData] = useState<OnboardingCase | null>(null);
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
    try {
      setCaseData(await createOnboardingCase(uen));
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
    try {
      setCaseData(await fetchOnboardingCase(caseId.trim()));
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "Unable to open the case.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="page-shell">
      <header className="hero">
        <SimulationBanner profile={simulationProfile} />
        <p className="eyebrow">Data Dividends | Phase 04</p>
        <h1>Singapore onboarding, with explainable ownership.</h1>
        <p className="summary">
          Open a case, review document candidates, map fictional related parties, and inspect
          deterministic ownership-only provisional UBO calculations.
        </p>
      </header>

      <section className="launch-card" aria-labelledby="launch-heading">
        <div>
          <p className="section-label">Case access</p>
          <h2 id="launch-heading">Start or reopen an onboarding case</h2>
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
          />
          <OwnershipPanel
            key={`ownership-${caseData.case_id}`}
            caseData={caseData}
            configuredThreshold={
              simulationProfile?.ubo_ownership_threshold_percent ?? "25"
            }
          />
        </>
      )}
    </main>
  );
}
