import { useCallback, useEffect, useRef, useState } from "react";

import {
  ApiError,
  fetchDocuments,
  fetchOwnership,
  fetchZeroTouchCase,
  replaceZeroTouchDocument,
  resolveReconciliationDiscrepancy,
  resolveZeroTouchException,
  resumeZeroTouchCase,
  retryZeroTouchIntakeDocument,
} from "../api";
import { startAutomationPolling } from "../automationPolling";
import { formatTimestamp, shouldPollAutomation } from "../shared";
import type {
  DocumentProcessingRecord,
  ExceptionResolutionAction,
  OwnershipAnalysisRecord,
  ZeroTouchCaseSummary,
  ZeroTouchException,
} from "../types";
import AssignReviewerDialog from "./AssignReviewerDialog";
import { CompletedOverview, ConfirmDetailsPanel, PipelineRail, RegistryStatePanel } from "./CaseStatePanels";
import ReturnForReworkDialog from "./ReturnForReworkDialog";

const ACCEPTED_DOCUMENTS = "application/pdf,.pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,.docx,text/plain,.txt";

const ACTION_LABELS: Record<ExceptionResolutionAction, string> = {
  KEEP_REGISTRY_VALUE: "Keep registry values",
  USE_DOCUMENT_VALUE: "Use document value",
  REQUEST_ADDITIONAL_INFORMATION: "Request additional information",
};

export function shouldRefreshAfterMutationError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 409;
}

export function isDocumentReuploadRequired(document: DocumentProcessingRecord): boolean {
  return document.state === "FAILED" && document.error?.code === "DOCUMENT_REUPLOAD_REQUIRED";
}

export default function CaseDetail({
  caseId,
  onBack,
  onViewOnboarded,
  onViewAudit,
}: {
  caseId: string;
  onBack: () => void;
  onViewOnboarded: (caseId: string) => void;
  onViewAudit: (caseId: string) => void;
}) {
  const [summary, setSummary] = useState<ZeroTouchCaseSummary | null>(null);
  const [documents, setDocuments] = useState<DocumentProcessingRecord[]>([]);
  const [ownership, setOwnership] = useState<OwnershipAnalysisRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);
  const [dialogException, setDialogException] = useState<{ exception: ZeroTouchException; kind: "assign" | "rework" } | null>(null);
  const generation = useRef(0);

  const refreshEvidence = useCallback(async () => {
    const [latest, latestDocuments, latestOwnership] = await Promise.all([
      fetchZeroTouchCase(caseId),
      fetchDocuments(caseId),
      fetchOwnership(caseId),
    ]);
    setSummary(latest);
    setDocuments(latestDocuments);
    setOwnership(latestOwnership);
    return latest;
  }, [caseId]);

  useEffect(() => {
    generation.current += 1;
    const current = generation.current;
    setSummary(null);
    setError(null);
    void refreshEvidence().catch((requestError) => {
      if (current !== generation.current) return;
      setError(requestError instanceof ApiError ? requestError.message : "The case is unavailable.");
    });
  }, [refreshEvidence]);

  useEffect(() => {
    if (!summary || !shouldPollAutomation(summary.status)) return;
    const activeGeneration = generation.current;
    return startAutomationPolling({
      caseId,
      generation: activeGeneration,
      currentGeneration: () => generation.current,
      fetchCase: fetchZeroTouchCase,
      onUpdate: (latest) => {
        setSummary(latest);
        void Promise.all([fetchDocuments(caseId), fetchOwnership(caseId)]).then(([docs, owner]) => {
          if (activeGeneration === generation.current) { setDocuments(docs); setOwnership(owner); }
        });
      },
      onWarning: (warning) => setError(warning),
      shouldContinue: shouldPollAutomation,
    });
  }, [caseId, summary?.status, summary?.version]);

  async function runMutation(operation: () => Promise<ZeroTouchCaseSummary>) {
    setIsBusy(true);
    setError(null);
    try {
      setSummary(await operation());
      await refreshEvidence();
    } catch (mutationError) {
      if (shouldRefreshAfterMutationError(mutationError)) {
        await refreshEvidence().catch(() => undefined);
      }
      setError(mutationError instanceof Error ? mutationError.message : "The case action failed.");
    } finally {
      setIsBusy(false);
    }
  }

  if (error && !summary) return <div className="ds-root ds-page"><button type="button" className="btn btn-ghost" onClick={onBack}>← Back to Cases</button><div className="ds-banner ds-banner-warn">{error}</div></div>;
  if (!summary) return <div className="ds-root ds-page"><p className="text-muted">Loading case…</p></div>;

  const entity = summary.case.entity;
  const acquisition = summary.case.registry_acquisition;

  return (
    <div className="ds-root detail-layout">
      <div className="side-panel case-pipeline-panel">
        <button type="button" className="btn btn-ghost" onClick={onBack} style={{ paddingLeft: 0 }}>← Back to Cases</button>
        <h4 style={{ marginTop: 16 }}>Pipeline</h4>
        <PipelineRail summary={summary} />
        <hr className="hr" />
        <div className="text-muted" style={{ fontSize: 11.5 }}>
          Loop —
        </div>
      </div>

      <div className="ds-page" style={{ flex: 1 }}>
        <div className="ds-page-header"><div><p className="card-kicker">{summary.case.requested_uen} · {summary.case.jurisdiction_resolution?.resolved_jurisdiction ?? "—"}</p><h1>{entity?.legal_name ?? summary.case.requested_uen}</h1></div><span className="tag tag-accent-2">{summary.status.replaceAll("_", " ")}</span></div>
        {error && <div className="ds-banner ds-banner-warn" style={{ marginBottom: 16 }}>{error}</div>}

        {summary.active_exceptions.filter((exception) => exception.stage !== "REGISTRY").map((exception) => (
          <div className="ds-banner ds-banner-warn" key={exception.exception_id} style={{ marginBottom: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}><h3 style={{ margin: 0 }}>{exception.exception_type.replaceAll("_", " ")}</h3><span className="text-muted" style={{ fontSize: 11 }}>{formatTimestamp(exception.created_at)}</span></div>
            <p style={{ marginTop: 8, fontSize: 12.5 }}>{exception.explanation}</p>
            <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
              {exception.available_actions.map((action) => <button key={action} type="button" className="btn btn-primary" disabled={isBusy} onClick={() => void runMutation(() => resolveZeroTouchException(summary, exception.exception_id, action, exception.evidence_version))}>{ACTION_LABELS[action]}</button>)}
              <button type="button" className="btn btn-secondary disclosure-action" aria-description="Disclosure only; assignment is unavailable" onClick={() => setDialogException({ exception, kind: "assign" })}>Assign reviewer</button>
              <button type="button" className="btn btn-secondary disclosure-action" aria-description="Disclosure only; return for rework is unavailable" onClick={() => setDialogException({ exception, kind: "rework" })}>Return for rework</button>
            </div>
          </div>
        ))}

        {summary.status === "RECOVERY_PENDING" && <div className="ds-banner" style={{ marginBottom: 16 }}><p style={{ margin: 0, fontSize: 12.5 }}>Backend recovery is pending; target operations will not be replayed by the browser.</p><button type="button" className="btn btn-primary" style={{ marginTop: 10 }} disabled={isBusy} onClick={() => void runMutation(() => resumeZeroTouchCase(caseId))}>Complete safe recovery</button></div>}
        {summary.status === "TECHNICAL_FAILURE" && summary.technical_failure && <div className="ds-banner ds-banner-warn" style={{ marginBottom: 16 }}><h3 style={{ marginTop: 0 }}>Automation stopped safely</h3><strong>{summary.technical_failure.code}</strong><p style={{ marginBottom: 0 }}>{summary.technical_failure.message}</p></div>}
        <RegistryStatePanel summary={summary} />
        <ConfirmDetailsPanel summary={summary} isBusy={isBusy} onResolve={(discrepancy, action) => void runMutation(() => resolveReconciliationDiscrepancy(summary, discrepancy.discrepancy_id, action, summary.reconciliation!.version, discrepancy.evidence_fingerprint))} />
        <CompletedOverview summary={summary} onViewOnboarded={onViewOnboarded} onViewAudit={onViewAudit} />

        <div className="ds-two-col"><div style={{ flex: 1 }}><h4>Corporate particulars</h4><div>
          <div className="kv-row"><span className="kv-label">Company name</span><span className="kv-value">{entity?.legal_name ?? "—"}</span></div><div className="kv-row"><span className="kv-label">Registration ID</span><span className="kv-value">{entity?.registration_number ?? summary.case.requested_uen}</span></div><div className="kv-row"><span className="kv-label">Entity type</span><span className="kv-value">{entity?.party_type ?? "—"}</span></div><div className="kv-row"><span className="kv-label">Registry status</span><span className="kv-value">{entity?.entity_status ?? "—"}</span></div><div className="kv-row"><span className="kv-label">Registration date</span><span className="kv-value">{entity?.registration_date ?? "—"}</span></div>
        </div></div><div style={{ width: 330 }}><h4>Directors</h4>{acquisition && acquisition.officers.length > 0 ? <div className="table-card"><table className="table"><tbody>{acquisition.officers.map((officer) => <tr key={officer.officer_id}><td>{officer.name}</td><td>{officer.role}</td></tr>)}</tbody></table></div> : <p className="text-muted" style={{ fontSize: 12 }}>Not available.</p>}</div></div>

        {acquisition && (
          <details className="evidence-details registry-evidence-details">
            <summary>Registry operation results, issues, and safe provenance</summary>
            {acquisition.operation_results.map((operation) => (
              <p key={operation.operation}><strong>{operation.operation.replaceAll("_", " ")}</strong> · {operation.status} · {operation.record_count} record(s) · {operation.provenance ? `${operation.provenance.provider} ${operation.provenance.environment} · ${operation.provenance.evidence_reference}` : "provenance —"}{operation.error ? ` · ${operation.error.code}: ${operation.error.message}` : ""}</p>
            ))}
            {acquisition.issues.map((issue) => <p key={issue.code}><strong>{issue.code}</strong> · {issue.message}</p>)}
          </details>
        )}

        <section className="evidence-section-block" aria-labelledby="documents-heading">
          <h4 id="documents-heading">Documents and field evidence</h4>
          {documents.some(isDocumentReuploadRequired) && (
            <div className="ds-banner ds-banner-warn interruption-banner">
              <strong>Document re-upload required</strong>
              <span>Processing was interrupted before structured evidence was retained. Retry only the affected document on this same case.</span>
            </div>
          )}
          <div className="table-card table-scroll" tabIndex={0} style={{ marginBottom: 20 }}>
            <table className="table">
              <thead><tr><th>Name</th><th>Type</th><th>State</th><th>Evidence</th><th>Action</th></tr></thead>
              <tbody>
                {documents.length === 0 && <tr><td colSpan={5}>No document records available.</td></tr>}
                {documents.map((document) => (
                  <tr key={document.document_id}>
                    <td>{document.display_name}<span className="cell-note">{document.provider_environment ?? "—"} · {document.size_bytes ? `${document.size_bytes} bytes` : "size unavailable"}</span></td>
                    <td>{document.media_type}</td>
                    <td>{document.state}{document.error && <span className="cell-note cell-note--attention">{document.error.code}</span>}</td>
                    <td>
                      <details className="table-details">
                        <summary>{document.superseded_by_document_id ? "Superseded" : "Current"} · {document.fields.length} field(s)</summary>
                        {document.fields.map((field) => (
                          <p key={field.field_key}>
                            <strong>{field.field_key.replaceAll("_", " ")}</strong> · {field.comparison_status} · {Math.round(field.confidence * 100)}% · {field.provenance.provider} {field.provenance.environment} · {field.provenance.source_reference}
                          </p>
                        ))}
                        <p>Events: {document.events.length} · {document.supersedes_document_id ? `replaces ${document.supersedes_document_id}` : "original evidence"}</p>
                      </details>
                    </td>
                    <td>
                      {!document.superseded_by_document_id && (
                        <label className="btn btn-ghost">
                          {document.state === "FAILED" ? "Retry affected document" : "Replace"}
                          <input hidden type="file" accept={ACCEPTED_DOCUMENTS} onChange={(event) => {
                            const file = event.target.files?.[0];
                            event.target.value = "";
                            if (!file) return;
                            if (document.state === "FAILED") {
                              setIsBusy(true);
                              void retryZeroTouchIntakeDocument(caseId, document.document_id, file, false)
                                .then(() => refreshEvidence())
                                .catch((retryError) => setError(retryError instanceof Error ? retryError.message : "Retry failed."))
                                .finally(() => setIsBusy(false));
                            } else {
                              void runMutation(() => replaceZeroTouchDocument(caseId, document.document_id, document.events.length, file));
                            }
                          }} />
                        </label>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <div className="ds-two-col evidence-columns">
          <section style={{ flex: 1 }} aria-labelledby="ownership-heading">
            <h4 id="ownership-heading">Ownership / provisional UBO</h4>
            <p className="control-help">
              {ownership ? `${ownership.provider_name ?? "—"} ${ownership.provider_environment ?? "—"} · threshold ${ownership.threshold_comparator.replaceAll("_", " ").toLowerCase()} ${ownership.threshold_percent}%` : "Ownership evidence is not yet available."}
            </p>
            <div className="table-card table-scroll" tabIndex={0}>
              <table className="table">
                <thead><tr><th>Party</th><th>Direct</th><th>Indirect</th><th>Effective</th><th>Classification</th></tr></thead>
                <tbody>
                  {!ownership && <tr><td colSpan={5}>Not available in current POC state.</td></tr>}
                  {ownership?.candidates.map((candidate) => (
                    <tr key={candidate.party.party_id}>
                      <td>{candidate.party.display_name}<span className="cell-note">{candidate.party.party_type} · {candidate.party.country ?? "country —"}</span></td>
                      <td>{candidate.direct_ownership_percent}%</td>
                      <td>{candidate.indirect_ownership_percent}%</td>
                      <td>{candidate.aggregated_ownership_percent}%</td>
                      <td>{candidate.classification}<span className="cell-note">{candidate.paths.map((path) => path.calculation).join("; ") || "No completed path"}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {ownership && (
              <details className="evidence-details">
                <summary>{ownership.parties.length} parties · {ownership.relationships.length} relationships · calculation paths</summary>
                {ownership.relationships.map((relationship) => (
                  <p key={relationship.relationship_id}>{relationship.parent_party_id} → {relationship.child_party_id} · {relationship.ownership_percent}% · {relationship.provenance.provider} {relationship.provenance.environment} · {formatTimestamp(relationship.provenance.sourced_at)}</p>
                ))}
              </details>
            )}
            {ownership?.issues.map((issue) => <p className="ds-banner ds-banner-warn" key={issue.code}>{issue.code}: {issue.message}</p>)}
          </section>
          <aside className="readiness-panel">
            <h4>Readiness</h4>
            {Object.entries(summary.clm.readiness).filter(([key]) => ["registry", "document", "ownership", "goldtier"].includes(key)).map(([key, value]) => <div className="kv-row" key={key}><span className="kv-label">{key}</span><span className="kv-value">{typeof value === "object" && value && "status" in value ? String(value.status) : "—"}</span></div>)}
            <div className="readiness-notes">
              <strong>Blockers</strong><span>{summary.clm.readiness.blockers.length ? summary.clm.readiness.blockers.join(" · ") : "None"}</span>
              <strong>Warnings</strong><span>{summary.clm.readiness.warnings.length ? summary.clm.readiness.warnings.join(" · ") : "None"}</span>
            </div>
            <h4>Submission plan</h4>
            <p className="control-help">{summary.clm.submission_plan.environment} · {summary.clm.submission_plan.base_operations.join(" → ")}</p>
            <p className="control-help">Ready-for-Approval: {summary.clm.submission_plan.real_ready_for_approval.replaceAll("_", " ")}</p>
            <h4>Target execution</h4>
            {summary.target_operations.map((operation) => <div className="kv-row" key={operation.operation}><span className="kv-label">{operation.operation}</span><span className="kv-value">{operation.status}</span></div>)}
            <div className="kv-row"><span className="kv-label">Mock GoldTier party ID</span><span className="kv-value">{summary.case.goldtier_result?.party_id ?? "—"}</span></div>
            <h4>Run metrics</h4>
            <div className="kv-row"><span className="kv-label">Automated stages</span><span className="kv-value">{summary.metrics.automated_stages_completed}</span></div>
            <div className="kv-row"><span className="kv-label">Human interventions</span><span className="kv-value">{summary.metrics.human_interventions}</span></div>
            <div className="kv-row"><span className="kv-label">Exceptions</span><span className="kv-value">{summary.metrics.exceptions_resolved}/{summary.metrics.exceptions_raised} resolved</span></div>
            <div className="kv-row"><span className="kv-label">Final outcome</span><span className="kv-value">{summary.metrics.final_outcome ?? "—"}</span></div>
          </aside>
        </div>

        <h4 style={{ marginTop: 24 }}>Automation timeline</h4><div className="table-card"><table className="table"><thead><tr><th>Timestamp</th><th>Stage</th><th>Event</th><th>Outcome</th></tr></thead><tbody>{summary.timeline.map((event) => <tr key={event.sequence}><td>{formatTimestamp(event.timestamp)}</td><td>{event.stage}</td><td>{event.message}</td><td>{event.outcome}</td></tr>)}</tbody></table></div>
      </div>

      {dialogException?.kind === "assign" && <AssignReviewerDialog summary={summary} exception={dialogException.exception} onClose={() => setDialogException(null)} onAssigned={(updated) => { setSummary(updated); setDialogException(null); }} />}
      {dialogException?.kind === "rework" && <ReturnForReworkDialog summary={summary} exception={dialogException.exception} onClose={() => setDialogException(null)} onReturned={(updated) => { setSummary(updated); setDialogException(null); }} />}
    </div>
  );
}
