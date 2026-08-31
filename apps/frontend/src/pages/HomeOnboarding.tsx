import { useRef, useState, type DragEvent, type FormEvent } from "react";

import { formatTimestamp } from "../shared";
import type {
  AutomationStage,
  ExceptionResolutionAction,
  ZeroTouchCaseSummary,
  ZeroTouchException,
} from "../types";
import AssignReviewerDialog from "./AssignReviewerDialog";
import ReturnForReworkDialog from "./ReturnForReworkDialog";

export type JurisdictionSelection = "" | "SG" | "AU" | "MY" | "HK";

const STAGE_BANDS: Array<{ label: string; stages: AutomationStage[] }> = [
  { label: "Registry verification", stages: ["REGISTRY"] },
  { label: "Document and data check", stages: ["DOCUMENT", "OWNERSHIP"] },
  { label: "Readiness and approval", stages: ["READINESS", "MOCK_GOLDTIER"] },
];

function bandState(summary: ZeroTouchCaseSummary, stages: AutomationStage[]): "done" | "now" | "" {
  if (stages.every((stage) => summary.completed_stages.includes(stage))) return "done";
  if (stages.includes(summary.current_stage)) return "now";
  return "";
}

const ACTION_LABELS: Partial<Record<ExceptionResolutionAction, string>> = {
  KEEP_REGISTRY_VALUE: "Keep registry values",
  REQUEST_ADDITIONAL_INFORMATION: "Request additional information",
  ASSIGN_REVIEWER: "Assign reviewer",
  RETURN_FOR_REWORK: "Return for rework",
  CLEAR_AS_FALSE_POSITIVE: "Clear as false positive",
};

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
  countryOfIncorporation,
  onCountryChange,
  documentFiles,
  onDocumentFilesChange,
  isSubmitting,
  isResolving,
  requestError,
  pollingWarning,
  onStart,
  onResolve,
  onReplace,
  onRecovery,
  onStartNewCase,
  onSummaryUpdate,
}: {
  summary: ZeroTouchCaseSummary | null;
  uen: string;
  onUenChange: (value: string) => void;
  countryOfIncorporation: JurisdictionSelection;
  onCountryChange: (value: JurisdictionSelection) => void;
  documentFiles: File[];
  onDocumentFilesChange: (files: File[]) => void;
  isSubmitting: boolean;
  isResolving: boolean;
  requestError: string | null;
  pollingWarning: string | null;
  onStart: (event: FormEvent<HTMLFormElement>) => void;
  onResolve: (exception: ZeroTouchException, action: ExceptionResolutionAction) => void;
  onReplace: (documentId: string, eventCount: number, file: File) => void;
  onRecovery: () => void;
  onStartNewCase: () => void;
  onSummaryUpdate: (summary: ZeroTouchCaseSummary) => void;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [dialogException, setDialogException] = useState<{
    exception: ZeroTouchException;
    kind: "assign" | "rework";
  } | null>(null);

  function addFiles(incoming: FileList | null) {
    if (!incoming || incoming.length === 0) return;
    onDocumentFilesChange([...documentFiles, ...Array.from(incoming)]);
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
              Enter the registration ID and attach the corporate documents. Onboarding pulls
              the registry record, fills the case, and progresses automatically once every
              required field is complete.
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
                  Drop files here, or <span className="drop-browse">browse</span>
                </span>
                <span className="text-muted" style={{ fontSize: 11, marginTop: 5 }}>
                  Constitution, director identity documents, proof of address
                </span>
                <input
                  id="home-document"
                  ref={fileInputRef}
                  type="file"
                  accept="application/pdf,.pdf"
                  multiple
                  onChange={(event) => {
                    addFiles(event.target.files);
                    event.target.value = "";
                  }}
                  hidden
                />
              </div>

              {documentFiles.length > 0 && (
                <div style={{ display: "flex", flexDirection: "column", gap: 7, marginTop: 12 }}>
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
            <button type="submit" className="btn btn-primary" disabled={isSubmitting || isResolving}>
              {isSubmitting ? "Starting onboarding…" : "Create onboarding"}
            </button>
          </div>
        </form>
      </div>
    );
  }

  const entity = summary.case.entity;
  const acquisition = summary.case.registry_acquisition;

  return (
    <div className="ds-root" style={{ display: "flex", alignItems: "stretch" }}>
      <div className="side-panel">
        <h4 style={{ marginTop: 0 }}>Pipeline</h4>
        <div className="ds-stage-rail">
          {STAGE_BANDS.map((band, index) => {
            const state = bandState(summary, band.stages);
            return (
              <div className="ds-stage" key={band.label}>
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                  <span className={`ds-stage-node ${state}`}>{state === "done" ? "✓" : index + 1}</span>
                  {index < STAGE_BANDS.length - 1 && (
                    <span className={`ds-stage-line ${state === "done" ? "done" : ""}`} />
                  )}
                </div>
                <div style={{ paddingBottom: 14 }}>
                  <div style={{ fontSize: 12.5 }}>{band.label}</div>
                  <div className="text-muted" style={{ fontSize: 11 }}>
                    {state === "done" ? "Cleared" : state === "now" ? "In progress" : "Pending"}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
        <hr className="hr" />
        <button type="button" className="btn btn-ghost" style={{ justifyContent: "flex-start", paddingLeft: 0 }} onClick={onStartNewCase}>
          Start a new case
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
          <span className="tag tag-accent-2">{summary.status.replaceAll("_", " ")}</span>
        </div>

        {requestError && <div className="ds-banner ds-banner-warn" style={{ marginBottom: 16 }}>{requestError}</div>}
        {pollingWarning && <div className="ds-banner ds-banner-warn" style={{ marginBottom: 16 }}>{pollingWarning}</div>}

        {summary.active_exceptions.map((exception) => (
        <div className="ds-banner ds-banner-warn" key={exception.exception_id} style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
            <h3 style={{ margin: 0 }}>{exception.exception_type.replaceAll("_", " ")}</h3>
            <span className="text-muted" style={{ fontSize: 11 }}>{formatTimestamp(exception.created_at)}</span>
          </div>
          <p style={{ marginTop: 8, fontSize: 12.5 }}>{exception.explanation}</p>
          <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
            {exception.available_actions.map((action) => (
              <button
                key={action}
                type="button"
                className={action === "RETURN_FOR_REWORK" ? "btn btn-secondary" : "btn btn-primary"}
                disabled={isResolving}
                onClick={() => {
                  if (action === "ASSIGN_REVIEWER") {
                    setDialogException({ exception, kind: "assign" });
                  } else if (action === "RETURN_FOR_REWORK") {
                    setDialogException({ exception, kind: "rework" });
                  } else {
                    onResolve(exception, action);
                  }
                }}
              >
                {ACTION_LABELS[action] ?? action.replaceAll("_", " ")}
              </button>
            ))}
            {exception.available_actions.length === 0 && (
              <span className="text-muted" style={{ fontSize: 12 }}>
                No backend-authorized action is currently available. Replacement evidence may be required.
              </span>
            )}
          </div>
        </div>
      ))}

      {summary.status === "RECOVERY_PENDING" && (
        <div className="ds-banner" style={{ marginBottom: 16 }}>
          <p style={{ margin: 0, fontSize: 12.5 }}>
            Mock target outcome retained; finalization recovery is pending without target replay.
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

      {summary.status === "COMPLETED" && (
        <div className="ds-banner" style={{ marginBottom: 16 }}>
          <strong>Mock submission completed</strong>
          <p style={{ margin: "6px 0 0", fontSize: 12.5 }}>
            {summary.metrics.human_interventions} human intervention(s) · not a legal or
            sponsor-approved determination.
          </p>
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
            <h4>Directors</h4>
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

      {dialogException?.kind === "assign" && (
        <AssignReviewerDialog
          summary={summary}
          exception={dialogException.exception}
          onClose={() => setDialogException(null)}
          onAssigned={(updated) => {
            onSummaryUpdate(updated);
            setDialogException(null);
          }}
        />
      )}
      {dialogException?.kind === "rework" && (
        <ReturnForReworkDialog
          summary={summary}
          exception={dialogException.exception}
          onClose={() => setDialogException(null)}
          onReturned={(updated) => {
            onSummaryUpdate(updated);
            setDialogException(null);
          }}
        />
      )}
    </div>
  );
}
