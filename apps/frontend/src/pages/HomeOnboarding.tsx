import { useRef, useState, type DragEvent, type FormEvent } from "react";

import type {
  ExceptionResolutionAction,
  ReconciliationDecisionAction,
  ReconciliationDiscrepancy,
  ProcessingNode,
  SimulationProfile,
  ZeroTouchCaseSummary,
  ZeroTouchException,
} from "../types";
import { CompletedOverview, ConfirmDetailsPanel, DetailedProcessingInspector, OnboardingProgressPanel, PipelineRail, RegistryStatePanel } from "./CaseStatePanels";
import HumanInterventionPanel from "./HumanInterventionPanel";
import { PriorityBadge } from "./PriorityControl";

export type JurisdictionSelection = "" | "SG" | "AU" | "MY" | "HK";

export function openCaseDetailAtStage(
  openCaseDetail: (caseId: string, focusNodeId?: string) => void,
  caseId: string,
  node: ProcessingNode,
): void {
  openCaseDetail(caseId, node.node_id);
}

const ACCEPTED_DOCUMENTS = "application/pdf,.pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,.docx,text/plain,.txt";
const FOLDER_INPUT_ATTRIBUTES = { webkitdirectory: "", directory: "" } as Record<string, string>;

export function mergeSelectedFiles(current: File[], incoming: File[]): File[] {
  const result = [...current];
  const known = new Set(current.map((file) => `${file.name}\u0000${file.size}\u0000${file.lastModified}`));
  for (const file of incoming) {
    const key = `${file.name}\u0000${file.size}\u0000${file.lastModified}`;
    if (!known.has(key)) { known.add(key); result.push(file); }
  }
  return result;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function CheckIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--color-accent)" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

export default function HomeOnboarding({
  summary,
  uen,
  onUenChange,
  legalName = "",
  onLegalNameChange = () => undefined,
  countryOfIncorporation,
  onCountryChange,
  documentFiles,
  onDocumentFilesChange,
  caseTeamDisplayName,
  priority,
  onPriorityChange,
  isSubmitting,
  isResolving,
  creationDisabled = false,
  requestError,
  pollingWarning,
  intakeProgress,
  onStart,
  onResolve,
  onReconcile,
  onReplace,
  onRecovery,
  onStartNewCase,
  onOpenCaseDetail = () => undefined,
  canDeleteCurrentCase = false,
  onDeleteCurrentCase = () => undefined,
  onViewOnboarded,
  onViewAudit,
  registryProviderMode,
  onRetryIntake = () => undefined,
}: {
  summary: ZeroTouchCaseSummary | null;
  uen: string;
  onUenChange: (value: string) => void;
  legalName?: string;
  onLegalNameChange?: (value: string) => void;
  countryOfIncorporation: JurisdictionSelection;
  onCountryChange: (value: JurisdictionSelection) => void;
  documentFiles: File[];
  onDocumentFilesChange: (files: File[]) => void;
  caseTeamDisplayName: string;
  priority: number | "";
  onPriorityChange: (value: number | "") => void;
  isSubmitting: boolean;
  isResolving: boolean;
  creationDisabled?: boolean;
  requestError: string | null;
  pollingWarning: string | null;
  intakeProgress: string | null;
  onStart: (event: FormEvent<HTMLFormElement>) => void;
  onResolve: (exception: ZeroTouchException, action: ExceptionResolutionAction) => void;
  onReconcile: (discrepancy: ReconciliationDiscrepancy, action: ReconciliationDecisionAction) => void;
  onReplace: (documentId: string, eventCount: number, file: File) => void;
  onRecovery: () => void;
  onStartNewCase: () => void;
  onOpenCaseDetail?: (caseId: string, focusNodeId?: string) => void;
  canDeleteCurrentCase?: boolean;
  onDeleteCurrentCase?: () => void;
  onViewOnboarded: (caseId: string) => void;
  onViewAudit: (caseId: string) => void;
  registryProviderMode?: SimulationProfile["registry_provider_mode"];
  onRetryIntake?: () => void;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  function addFiles(incoming: FileList | null) {
    if (!incoming || incoming.length === 0) return;
    onDocumentFilesChange(mergeSelectedFiles(documentFiles, Array.from(incoming)));
  }

  function removeFile(index: number) {
    onDocumentFilesChange(documentFiles.filter((_, i) => i !== index));
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragOver(false);
    addFiles(event.dataTransfer.files);
  }

  if (!summary) {
    return (
      <div className="ds-root ds-page">
        <div className="ds-page-header">
          <div>
            <h1>Start onboarding</h1>
            <p className="text-muted">
              Provide the onboarding package available to you: the registration ID and
              supporting corporate documents. This POC begins processing after the package
              is supplied; it does not solicit or collect documents from upstream systems.
            </p>
          </div>
        </div>

        {requestError && <div className="ds-banner ds-banner-warn" style={{ marginBottom: 16 }}>{requestError}</div>}

        <form onSubmit={onStart}>
          <div className="ds-two-col" style={{ alignItems: "stretch" }}>
            <div className="card" style={{ width: 420, flex: "none" }}>
              <div className="field">
                <label htmlFor="home-country">Jurisdiction</label>
                <select
                  id="home-country"
                  className="input"
                  value={countryOfIncorporation}
                  onChange={(event) => onCountryChange(event.target.value as JurisdictionSelection)}
                >
                  <option value="">Not specified</option>
                  <option value="SG">Singapore</option>
                  <option value="AU">Australia — provider not implemented</option>
                  <option value="MY">Malaysia — provider not implemented</option>
                  <option value="HK">Hong Kong — provider not implemented</option>
                </select>
                <p className="text-muted" style={{ fontSize: 11, marginTop: 4 }}>
                  Singapore routes to ACRA. Other recognised jurisdictions stop safely in this POC.
                </p>
              </div>
              <div className="field">
                <label htmlFor="home-legal-name">Legal name</label>
                <input
                  id="home-legal-name"
                  className="input"
                  value={legalName}
                  onChange={(event) => onLegalNameChange(event.target.value)}
                  maxLength={160}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="home-uen">Registration ID / UEN</label>
                <input
                  id="home-uen"
                  className="input"
                  value={uen}
                  onChange={(event) => onUenChange(event.target.value.toUpperCase())}
                  maxLength={32}
                  required
                />
              </div>
              <div className="field">
                <span className="control-label">Team</span>
                <strong>{caseTeamDisplayName}</strong>
              </div>
              <div className="field">
                <label htmlFor="home-priority">Case priority</label>
                <select
                  id="home-priority"
                  className="input"
                  value={priority}
                  onChange={(event) => {
                    onPriorityChange(event.target.value === "" ? "" : Number(event.target.value));
                  }}
                >
                  <option value="">Unset</option>
                  <option value={1}>Low</option>
                  <option value={5}>Medium</option>
                  <option value={10}>High</option>
                </select>
                <p className="control-help">Optional ordering label only; it does not imply risk, SLA, or approval treatment.</p>
              </div>
            </div>

            <div className="card" style={{ flex: 1, minWidth: 380 }}>
              <p className="card-kicker">Documents</p>
              <div
                className="drop"
                onClick={() => fileInputRef.current?.click()}
                onDragOver={(event) => {
                  event.preventDefault();
                  setIsDragOver(true);
                }}
                onDragLeave={() => setIsDragOver(false)}
                onDrop={handleDrop}
                style={{
                  marginTop: 10,
                  minHeight: 130,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  ...(isDragOver ? { borderColor: "var(--color-accent)" } : {}),
                }}
              >
                <span>
                  Drop files here, <span className="drop-browse">browse</span>, or{" "}
                  <button type="button" className="btn btn-ghost" onClick={(event) => { event.stopPropagation(); folderInputRef.current?.click(); }}>select folder</button>
                </span>
                <span className="text-muted" style={{ fontSize: 11, marginTop: 5 }}>
                  PDF, DOCX, and UTF-8 TXT · up to 20 files
                </span>
                <input
                  id="home-document"
                  ref={fileInputRef}
                  type="file"
                  accept={ACCEPTED_DOCUMENTS}
                  multiple
                  onChange={(event) => {
                    addFiles(event.target.files);
                    event.target.value = "";
                  }}
                  hidden
                />
                <input
                  ref={folderInputRef}
                  type="file"
                  accept={ACCEPTED_DOCUMENTS}
                  multiple
                  {...FOLDER_INPUT_ATTRIBUTES}
                  onChange={(event) => { addFiles(event.target.files); event.target.value = ""; }}
                  hidden
                />
              </div>

              {documentFiles.length > 0 && (
                <div style={{ display: "flex", flexDirection: "column", gap: 7, marginTop: 12 }}>
                  <span className="text-muted" style={{ fontSize: 11 }}>
                    {documentFiles.length} file(s) · {formatFileSize(documentFiles.reduce((total, file) => total + file.size, 0))} selected
                  </span>
                  {documentFiles.map((file, index) => (
                    <div
                      key={`${file.name}-${index}`}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 9,
                        paddingBottom: 7,
                        borderBottom:
                          index < documentFiles.length - 1 ? "1px solid var(--color-divider)" : "none",
                      }}
                    >
                      <CheckIcon />
                      <span style={{ flex: 1, fontSize: 12.5 }}>{file.name}</span>
                      <span className="text-muted" style={{ fontSize: 11 }}>{formatFileSize(file.size)}</span>
                      <button type="button" className="btn btn-ghost" onClick={() => removeFile(index)}>
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div style={{ marginTop: 24 }}>
            <button type="submit" className="btn btn-primary" disabled={isSubmitting || isResolving || creationDisabled}>
              {isSubmitting ? intakeProgress ?? "Starting onboarding…" : "Create onboarding"}
            </button>
            {intakeProgress && <span className="intake-progress" role="status">{intakeProgress}</span>}
          </div>
        </form>
      </div>
    );
  }

  const entity = summary.case.entity;
  const acquisition = summary.case.registry_acquisition;

  return (
    <div className="ds-root detail-layout">
      <div className="side-panel">
        <h4 style={{ marginTop: 0 }}>Pipeline</h4>
        <PipelineRail summary={summary} />
        <hr className="hr" />
        <button
          type="button"
          className="btn btn-primary btn-block new-case-cta"
          aria-label="Start a new case"
          onClick={onStartNewCase}
        >
          + Start a new case
        </button>
      </div>

      <div className="ds-page" style={{ flex: 1 }}>
        <div className="ds-page-header">
          <div>
            <p className="card-kicker">
              {summary.case.requested_uen}
              {summary.case.jurisdiction_resolution?.resolved_jurisdiction
                ? ` · ${summary.case.jurisdiction_resolution.resolved_jurisdiction}`
                : ""}
            </p>
            <h1>{entity?.legal_name ?? summary.case.requested_uen}</h1>
          </div>
          <div className="case-header-actions">
            <PriorityBadge priority={summary.case.priority} />
            <span className="tag tag-accent-2">{summary.status.replaceAll("_", " ")}</span>
            <button type="button" className="btn btn-secondary" onClick={() => onOpenCaseDetail(summary.case.case_id)}>
              Open full case
            </button>
            {canDeleteCurrentCase && (
              <button type="button" className="btn btn-danger" onClick={onDeleteCurrentCase}>
                Delete case
              </button>
            )}
          </div>
        </div>

        {requestError && <div className="ds-banner ds-banner-warn" style={{ marginBottom: 16 }}>{requestError}</div>}
        {pollingWarning && <div className="ds-banner ds-banner-warn" style={{ marginBottom: 16 }}>{pollingWarning}</div>}

        {documentFiles.length > 0 && (
          <section className="card" aria-label="Retained intake package" style={{ marginBottom: 16 }}>
            <p className="card-kicker">Retained intake package</p>
            {documentFiles.map((file) => <p key={`${file.name}:${file.size}:${file.lastModified}`}>{file.name}</p>)}
          </section>
        )}

        {requestError && summary.status === "PENDING_INPUTS" && !isSubmitting && (
          <button type="button" className="btn btn-primary" style={{ marginBottom: 16 }} onClick={onRetryIntake}>
            Retry retained intake
          </button>
        )}

        <OnboardingProgressPanel
          summary={summary}
          onStageActivate={(node) => openCaseDetailAtStage(
            onOpenCaseDetail,
            summary.case.case_id,
            node,
          )}
        />

        <DetailedProcessingInspector key={`${summary.case.case_id}:${summary.automation_id}`} summary={summary} />

        <RegistryStatePanel summary={summary} registryProviderMode={registryProviderMode} />
        <ConfirmDetailsPanel summary={summary} isBusy={isResolving} />
        <CompletedOverview summary={summary} onViewOnboarded={onViewOnboarded} onViewAudit={onViewAudit} />

        <HumanInterventionPanel
          summary={summary}
          isBusy={isResolving}
          onResolve={onResolve}
        />

      {summary.status === "RECOVERY_PENDING" && (
        <div className="ds-banner" style={{ marginBottom: 16 }}>
          <p style={{ margin: 0, fontSize: 12.5 }}>
            Target outcome retained; finalization recovery is pending without target replay.
          </p>
          <button type="button" className="btn btn-primary" style={{ marginTop: 10 }} disabled={isSubmitting} onClick={onRecovery}>
            Complete safe recovery
          </button>
        </div>
      )}

      {summary.status === "TECHNICAL_FAILURE" && summary.technical_failure && (
        <div className="ds-banner ds-banner-warn" style={{ marginBottom: 16 }}>
          <h3 style={{ marginTop: 0 }}>Automation stopped safely</h3>
          <strong>{summary.technical_failure.code}</strong>
          <p style={{ marginBottom: 0 }}>{summary.technical_failure.message}</p>
        </div>
      )}

        <div className="ds-two-col">
          <div style={{ flex: 1 }}>
            <h4>Corporate particulars</h4>
            <div>
              <div className="kv-row"><span className="kv-label">Company name</span><span className="kv-value">{entity?.legal_name ?? "—"}</span></div>
              <div className="kv-row"><span className="kv-label">Registration ID</span><span className="kv-value">{entity?.registration_number ?? summary.case.requested_uen}</span></div>
              <div className="kv-row"><span className="kv-label">Entity type</span><span className="kv-value">{entity?.party_type ?? "—"}</span></div>
              <div className="kv-row"><span className="kv-label">Registry status</span><span className="kv-value">{entity?.entity_status ?? "—"}</span></div>
              <div className="kv-row"><span className="kv-label">Registration date</span><span className="kv-value">{entity?.registration_date ?? "—"}</span></div>
            </div>
          </div>
          <div style={{ width: 320 }}>
            <h4>Registry officers and roles</h4>
            {acquisition && acquisition.officers.length > 0 ? (
              <div className="table-card">
                <table className="table">
                  <tbody>
                    {acquisition.officers.map((officer) => (
                      <tr key={officer.officer_id}><td>{officer.name}</td><td>{officer.role}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-muted" style={{ fontSize: 12 }}>Not available.</p>
            )}
          </div>
        </div>

        <p className="text-muted" style={{ fontSize: 11, marginTop: 24 }}>
          Mock and provisional POC only. This is not Ready-for-Approval, legal UBO determination,
          customer approval, or evidence of live ACRA/GoldTier interoperability.
        </p>
      </div>

    </div>
  );
}
