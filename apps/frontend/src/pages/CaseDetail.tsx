import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import {
  ApiError,
  deleteZeroTouchCase,
  fetchDocuments,
  fetchIntelligence,
  fetchOwnership,
  fetchZeroTouchCase,
  replaceZeroTouchDocument,
  reviewDocument,
  resolveReconciliationDiscrepancy,
  resolveZeroTouchException,
  resumeZeroTouchCase,
  retryZeroTouchIntakeDocument,
  updateCasePriority,
} from "../api";
import { startAutomationPolling } from "../automationPolling";
import {
  caseDeletedEffect,
  caseDetailQueryOptions,
  caseSummaryMutationEffect,
  caseSupportingMutationEffect,
  documentQueryOptions,
  intelligenceQueryOptions,
  ownershipQueryOptions,
  priorityMutationEffect,
} from "../caseQueries";
import { formatTimestamp, shouldPollAutomation, targetOutcomeLabel } from "../shared";
import type {
  DocumentProcessingRecord,
  AuthenticatedProfile,
  ExceptionResolutionAction,
  OwnershipAnalysisRecord,
  ZeroTouchCaseSummary,
  ZeroTouchException,
} from "../types";
import {
  CompletedOverview,
  ConfirmDetailsPanel,
  DetailedProcessingInspector,
  OperationalTiming,
  PipelineRail,
  RegistryStatePanel,
} from "./CaseStatePanels";
import CaseStateExplanationPanel, { type EvidenceFocusTarget } from "./CaseStateExplanationPanel";
import PriorityControl, { PriorityBadge } from "./PriorityControl";
import DeleteCaseDialog from "./DeleteCaseDialog";
import DocumentEvidencePanel, { type DocumentReviewRequest } from "./DocumentEvidencePanel";
import OwnershipPathExplorer from "./OwnershipPathExplorer";
import IntelligencePanel from "./IntelligencePanel";
import GoldTierRequestPreview from "./GoldTierRequestPreview";
import RegistryProvenancePanel from "./RegistryProvenancePanel";

const ACTION_LABELS: Record<ExceptionResolutionAction, string> = {
  KEEP_REGISTRY_VALUE: "Keep registry values",
  USE_DOCUMENT_VALUE: "Use document value",
  REQUEST_ADDITIONAL_INFORMATION: "Request additional information",
};

const EVIDENCE_TARGET_IDS: Record<EvidenceFocusTarget, string> = {
  registry: "case-evidence-registry",
  documents: "case-evidence-documents",
  reconciliation: "case-evidence-reconciliation",
  ownership: "case-evidence-ownership",
  recovery: "case-evidence-recovery",
};

interface CaseActionIdentity {
  readonly generation: number;
  readonly caseId: string;
  readonly actorUserId: string;
}

interface EvidenceFocusNotice {
  readonly identity: string;
  readonly message: string;
}

export function shouldRefreshAfterMutationError(error: unknown): boolean {
  return error instanceof TypeError || (error instanceof ApiError && [409, 503].includes(error.status));
}

export default function CaseDetail({
  caseId,
  actor,
  onBack,
  onViewOnboarded,
  onViewAudit,
}: {
  caseId: string;
  actor: AuthenticatedProfile;
  onBack: () => void;
  onViewOnboarded: (caseId: string) => void;
  onViewAudit: (caseId: string) => void;
}) {
  const queryClient = useQueryClient();
  const evidenceIdentity = `${actor.user_id}:${caseId}`;
  const detailQuery = useQuery(caseDetailQueryOptions(actor.user_id, caseId));
  const documentQuery = useQuery(documentQueryOptions(actor.user_id, caseId));
  const ownershipQuery = useQuery(ownershipQueryOptions(actor.user_id, caseId));
  const intelligenceQuery = useQuery(intelligenceQueryOptions(actor.user_id, caseId));
  const summary = detailQuery.data ?? null;
  const documents = documentQuery.data ?? [];
  const ownership = ownershipQuery.data ?? null;
  const intelligence = intelligenceQuery.data ?? null;
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);
  const [busyLabel, setBusyLabel] = useState<string | null>(null);
  const [mutationBlocked, setMutationBlocked] = useState(false);
  const [caseUnavailable, setCaseUnavailable] = useState(false);
  const [evidenceFocusNotice, setEvidenceFocusNotice] = useState<EvidenceFocusNotice | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState<CaseActionIdentity | null>(null);
  const generation = useRef(0);
  const mounted = useRef(false);
  const mutationPending = useRef<CaseActionIdentity | null>(null);
  const activeIdentity = useRef({ caseId, actorUserId: actor.user_id });
  activeIdentity.current = { caseId, actorUserId: actor.user_id };

  function captureCaseAction(): CaseActionIdentity {
    return { generation: generation.current, caseId, actorUserId: actor.user_id };
  }

  function isCurrentCaseAction(action: CaseActionIdentity): boolean {
    return mounted.current
      && generation.current === action.generation
      && activeIdentity.current.caseId === action.caseId
      && activeIdentity.current.actorUserId === action.actorUserId;
  }

  const refreshEvidence = useCallback(async (action: CaseActionIdentity) => {
    await Promise.all([
      queryClient.cancelQueries({
        queryKey: caseDetailQueryOptions(action.actorUserId, action.caseId).queryKey,
        exact: true,
      }),
      queryClient.cancelQueries({
        queryKey: documentQueryOptions(action.actorUserId, action.caseId).queryKey,
        exact: true,
      }),
      queryClient.cancelQueries({
        queryKey: ownershipQueryOptions(action.actorUserId, action.caseId).queryKey,
        exact: true,
      }),
      queryClient.cancelQueries({
        queryKey: intelligenceQueryOptions(action.actorUserId, action.caseId).queryKey,
        exact: true,
      }),
    ]);
    if (!isCurrentCaseAction(action)) {
      throw new Error("Case evidence refresh is no longer current.");
    }
    const latestCase = fetchZeroTouchCase(action.caseId).then((latest) => {
      if (isCurrentCaseAction(action)) {
        queryClient.setQueryData(
          caseDetailQueryOptions(action.actorUserId, action.caseId).queryKey,
          latest,
        );
      }
      return latest;
    });
    const latestDocuments = fetchDocuments(action.caseId).then((documents) => {
      if (isCurrentCaseAction(action)) {
        queryClient.setQueryData(
          documentQueryOptions(action.actorUserId, action.caseId).queryKey,
          documents,
        );
        if (import.meta.env.VITE_E2E_DIAGNOSTICS === "1") {
          const reviewedFieldCount = documents
            .find((document) => document.superseded_by_document_id === null)
            ?.fields.filter((field) => field.review_status !== "PENDING").length ?? 0;
          console.info("E2E_DIAG", JSON.stringify({
            milestone: "REVIEW_QUERY_DATA_PUBLISHED",
            case_id: action.caseId,
            reviewed_field_count: reviewedFieldCount,
            monotonic_ms: Math.round(performance.now()),
          }));
        }
      }
      return documents;
    });
    const latestOwnership = fetchOwnership(action.caseId).then((ownership) => {
      if (isCurrentCaseAction(action)) {
        queryClient.setQueryData(
          ownershipQueryOptions(action.actorUserId, action.caseId).queryKey,
          ownership,
        );
      }
      return ownership;
    });
    const latestIntelligence = fetchIntelligence(action.caseId).then((record) => {
      if (isCurrentCaseAction(action)) {
        queryClient.setQueryData(
          intelligenceQueryOptions(action.actorUserId, action.caseId).queryKey,
          record,
        );
      }
      return record;
    });
    const [latest] = await Promise.all([
      latestCase,
      latestDocuments,
      latestOwnership,
      latestIntelligence,
    ]);
    return latest;
  }, [queryClient]);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      generation.current += 1;
    };
  }, []);

  useEffect(() => {
    generation.current += 1;
    const current = generation.current;
    setError(null);
    setIsBusy(false);
    setBusyLabel(null);
    setMutationBlocked(false);
    setCaseUnavailable(false);
    setDeleteDialogOpen(null);
    mutationPending.current = null;
    return () => { generation.current = current + 1; };
  }, [actor.user_id, caseId]);

  useEffect(() => {
    if (!summary || !shouldPollAutomation(summary.status)) return;
    const activeGeneration = generation.current;
    return startAutomationPolling({
      caseId,
      generation: activeGeneration,
      currentGeneration: () => generation.current,
      fetchCase: fetchZeroTouchCase,
      onUpdate: (latest) => {
        caseSummaryMutationEffect(queryClient, actor.user_id, latest);
        void Promise.all([fetchDocuments(caseId), fetchOwnership(caseId)]).then(([docs, owner]) => {
          if (activeGeneration === generation.current) {
            queryClient.setQueryData(documentQueryOptions(actor.user_id, caseId).queryKey, docs);
            queryClient.setQueryData(ownershipQueryOptions(actor.user_id, caseId).queryKey, owner);
          }
        });
      },
      onWarning: (warning) => setError(warning),
      shouldContinue: shouldPollAutomation,
    });
  }, [actor.user_id, caseId, queryClient, summary?.status, summary?.version]);

  async function runMutation(operation: () => Promise<ZeroTouchCaseSummary>, label = "Saving case action…") {
    const action = captureCaseAction();
    if (mutationPending.current || mutationBlocked) return;
    mutationPending.current = action;
    setIsBusy(true);
    setBusyLabel(label);
    setError(null);
    try {
      const updated = await operation();
      if (!isCurrentCaseAction(action)) return;
      await caseSupportingMutationEffect(queryClient, action.actorUserId, updated);
    } catch (mutationError) {
      if (!isCurrentCaseAction(action)) return;
      if (shouldRefreshAfterMutationError(mutationError)) {
        await refreshEvidence(action).catch(() => undefined);
      }
      if (!isCurrentCaseAction(action)) return;
      setError(mutationError instanceof Error ? mutationError.message : "The case action failed.");
    } finally {
      if (mutationPending.current === action) mutationPending.current = null;
      if (isCurrentCaseAction(action)) {
        setIsBusy(false);
        setBusyLabel(null);
      }
    }
  }

  async function runPriorityMutation(priority: number | null): Promise<void> {
    const action = captureCaseAction();
    if (mutationPending.current || mutationBlocked) return;
    mutationPending.current = action;
    setIsBusy(true);
    setBusyLabel("Saving case priority…");
    setError(null);
    try {
      await updateCasePriority(action.caseId, priority);
      if (!isCurrentCaseAction(action)) return;
      await refreshEvidence(action);
      if (!isCurrentCaseAction(action)) return;
      await priorityMutationEffect(queryClient, action.actorUserId);
    } catch (priorityError) {
      if (!isCurrentCaseAction(action)) return;
      setError(priorityError instanceof Error ? priorityError.message : "Priority could not be updated.");
      throw priorityError;
    } finally {
      if (mutationPending.current === action) mutationPending.current = null;
      if (isCurrentCaseAction(action)) {
        setIsBusy(false);
        setBusyLabel(null);
      }
    }
  }

  async function settleEvidenceMutation(
    operation: () => Promise<unknown>,
    label: string,
    failureText: string,
  ): Promise<void> {
    const action = captureCaseAction();
    if (mutationPending.current || mutationBlocked) return;
    mutationPending.current = action;
    setIsBusy(true);
    setBusyLabel(label);
    setError(null);
    let mutationError: unknown = null;
    try {
      await operation();
    } catch (caught) {
      mutationError = caught;
    }
    if (!isCurrentCaseAction(action)) {
      if (mutationPending.current === action) mutationPending.current = null;
      return;
    }
    const mustRefresh = mutationError === null || shouldRefreshAfterMutationError(mutationError);
    if (mustRefresh) {
      try {
        await refreshEvidence(action);
        if (!isCurrentCaseAction(action)) return;
        setMutationBlocked(false);
        if (mutationError !== null) {
          setError(
            mutationError instanceof ApiError && mutationError.status === 409
              ? "The evidence changed before this action. Current case evidence was reloaded."
              : "The outcome could not be confirmed. Current case evidence was reloaded; check the field status before trying another action.",
          );
        }
      } catch (refreshError) {
        if (!isCurrentCaseAction(action)) return;
        if (refreshError instanceof ApiError && refreshError.status === 404) {
          setCaseUnavailable(true);
          setError(null);
        } else {
          setMutationBlocked(true);
          setError("The outcome and evidence reload could not be confirmed. Last-confirmed information is shown; refresh case evidence before another mutation.");
        }
      }
    } else if (mutationError !== null) {
      if (mutationError instanceof ApiError && mutationError.status === 404) {
        setCaseUnavailable(true);
        setError(null);
      } else {
        setError(mutationError instanceof Error ? mutationError.message : failureText);
      }
    }
    if (mutationPending.current === action) mutationPending.current = null;
    if (isCurrentCaseAction(action)) {
      setIsBusy(false);
      setBusyLabel(null);
    }
  }

  function handleDocumentReview(
    document: DocumentProcessingRecord,
    request: DocumentReviewRequest,
    repair: boolean,
  ) {
    const label = request.fieldKey.replaceAll("_", " ");
    void settleEvidenceMutation(
      () => reviewDocument(
        caseId,
        document.document_id,
        request.fieldKey,
        request.decision,
        request.correctedValue,
        request.note,
      ),
      repair ? `Retrying saved ${label} checkpoint…` : `Saving ${label} decision…`,
      "The document review could not be saved.",
    );
  }

  function handleReplacement(document: DocumentProcessingRecord, file: File) {
    void settleEvidenceMutation(
      () => replaceZeroTouchDocument(caseId, document.document_id, document.events.length, file),
      "Replacing current document…",
      "The replacement could not be saved.",
    );
  }

  function handleRetry(document: DocumentProcessingRecord, file: File) {
    void settleEvidenceMutation(
      () => retryZeroTouchIntakeDocument(caseId, document.document_id, file, false),
      "Retrying affected document…",
      "The document retry failed.",
    );
  }

  function handleContinueRecoveredIntake() {
    void settleEvidenceMutation(
      () => resumeZeroTouchCase(caseId),
      "Continuing recovered intake…",
      "Recovered intake could not continue.",
    );
  }

  async function handleReadOnlyRefresh() {
    const action = captureCaseAction();
    if (mutationPending.current) return;
    mutationPending.current = action;
    setIsBusy(true);
    setBusyLabel("Refreshing case evidence…");
    try {
      await refreshEvidence(action);
      if (!isCurrentCaseAction(action)) return;
      setMutationBlocked(false);
      setError(null);
    } catch (refreshError) {
      if (!isCurrentCaseAction(action)) return;
      if (refreshError instanceof ApiError && refreshError.status === 404) {
        setCaseUnavailable(true);
        setError(null);
      } else {
        setError("Case evidence could not be refreshed. Last-confirmed information is still shown.");
      }
    } finally {
      if (mutationPending.current === action) mutationPending.current = null;
      if (isCurrentCaseAction(action)) {
        setIsBusy(false);
        setBusyLabel(null);
      }
    }
  }

  function focusEvidence(target: EvidenceFocusTarget): void {
    const section = document.getElementById(EVIDENCE_TARGET_IDS[target]);
    if (!section) {
      setEvidenceFocusNotice({
        identity: evidenceIdentity,
        message: `${target.replaceAll("_", " ")} evidence is not available for this case.`,
      });
      return;
    }
    setEvidenceFocusNotice(null);
    section.focus({ preventScroll: true });
    section.scrollIntoView?.({ block: "start", behavior: "smooth" });
  }

  async function deleteCase(action: CaseActionIdentity): Promise<void> {
    if (!isCurrentCaseAction(action) || mutationPending.current || mutationBlocked) {
      throw new Error("Another case action is still pending.");
    }
    mutationPending.current = action;
    setIsBusy(true);
    setBusyLabel("Deleting case…");
    try {
      await deleteZeroTouchCase(action.caseId);
      if (!isCurrentCaseAction(action)) return;
      await caseDeletedEffect(queryClient, action.actorUserId, action.caseId);
      if (!isCurrentCaseAction(action)) return;
      setDeleteDialogOpen(null);
      onBack();
    } catch (deleteError) {
      if (isCurrentCaseAction(action)) throw deleteError;
    } finally {
      if (mutationPending.current === action) mutationPending.current = null;
      if (isCurrentCaseAction(action)) {
        setIsBusy(false);
        setBusyLabel(null);
      }
    }
  }

  const loadError = detailQuery.error ?? documentQuery.error ?? ownershipQuery.error;
  if (caseUnavailable) return <div className="ds-root ds-page"><button type="button" className="btn btn-ghost" onClick={onBack}>← Back to Cases</button><div className="ds-banner ds-banner-warn">The case is unavailable.</div></div>;
  if ((error || loadError) && !summary) return <div className="ds-root ds-page"><button type="button" className="btn btn-ghost" onClick={onBack}>← Back to Cases</button><div className="ds-banner ds-banner-warn">{error ?? (loadError instanceof Error ? loadError.message : "The case is unavailable.")}</div></div>;
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
        <div className="ds-page-header"><div><p className="card-kicker">{summary.case.requested_uen} · {summary.case.jurisdiction_resolution?.resolved_jurisdiction ?? "—"} · {summary.case.client_scope_label ?? "Legacy unassigned"}</p><h1>{entity?.legal_name ?? summary.case.requested_uen}</h1></div><div className="case-header-actions"><PriorityBadge priority={summary.case.priority} /><PriorityControl priority={summary.case.priority} disabled={isBusy || mutationBlocked} onSave={runPriorityMutation} />{(actor.role === "DIRECTOR" || actor.role === "RELATIONSHIP_MANAGER") && <button type="button" className="btn btn-danger" disabled={isBusy || mutationBlocked} onClick={() => { if (!mutationPending.current && !mutationBlocked) setDeleteDialogOpen(captureCaseAction()); }}>Delete case</button>}<span className="tag tag-accent-2">{summary.status.replaceAll("_", " ")}</span></div></div>
        {error && <div className="ds-banner ds-banner-warn" style={{ marginBottom: 16 }}>{error}</div>}

        {summary.active_exceptions.filter((exception) => exception.stage !== "REGISTRY").map((exception) => (
          <div className="ds-banner ds-banner-warn" key={exception.exception_id} style={{ marginBottom: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}><h3 style={{ margin: 0 }}>{exception.exception_type.replaceAll("_", " ")}</h3><span className="text-muted" style={{ fontSize: 11 }}>{formatTimestamp(exception.created_at)}</span></div>
            <p style={{ marginTop: 8, fontSize: 12.5 }}>{exception.explanation}</p>
            <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
              {exception.available_actions.map((action) => <button key={action} type="button" className="btn btn-primary" disabled={isBusy || mutationBlocked} onClick={() => void runMutation(() => resolveZeroTouchException(summary, exception.exception_id, action, exception.evidence_version))}>{ACTION_LABELS[action]}</button>)}
            </div>
          </div>
        ))}

        {summary.status === "RECOVERY_PENDING" && <div className="ds-banner" style={{ marginBottom: 16 }}><p style={{ margin: 0, fontSize: 12.5 }}>Backend recovery is pending; target operations will not be replayed by the browser.</p><button type="button" className="btn btn-primary" style={{ marginTop: 10 }} disabled={isBusy || mutationBlocked} onClick={() => void runMutation(() => resumeZeroTouchCase(caseId))}>Complete safe recovery</button></div>}
        {summary.status === "TECHNICAL_FAILURE" && summary.technical_failure && <div className="ds-banner ds-banner-warn" style={{ marginBottom: 16 }}><h3 style={{ marginTop: 0 }}>Automation stopped safely</h3><strong>{summary.technical_failure.code}</strong><p style={{ marginBottom: 0 }}>{summary.technical_failure.message}</p></div>}
        <DetailedProcessingInspector key={`${summary.case.case_id}:${summary.automation_id}`} summary={summary} />
        <RegistryStatePanel summary={summary} />
        <div key={`${evidenceIdentity}:registry`} id={EVIDENCE_TARGET_IDS.registry} className="evidence-focus-target" tabIndex={-1}>
          <RegistryProvenancePanel acquisition={acquisition} binding={summary.case.registry_evidence_binding} />
        </div>
        {summary.reconciliation && summary.current_stage === "DOCUMENT" && (
          <div key={`${evidenceIdentity}:reconciliation`} id={EVIDENCE_TARGET_IDS.reconciliation} className="evidence-focus-target" tabIndex={-1}>
            <ConfirmDetailsPanel summary={summary} isBusy={isBusy || mutationBlocked} onResolve={(discrepancy, action) => void runMutation(() => resolveReconciliationDiscrepancy(summary, discrepancy.discrepancy_id, action, summary.reconciliation!.version, discrepancy.evidence_fingerprint))} />
          </div>
        )}
        <CompletedOverview summary={summary} onViewOnboarded={onViewOnboarded} onViewAudit={onViewAudit} />
        <OperationalTiming summary={summary} />

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

        <div key={`${evidenceIdentity}:documents`} id={EVIDENCE_TARGET_IDS.documents} className="evidence-focus-target" tabIndex={-1}>
          <DocumentEvidencePanel key={evidenceIdentity} summary={summary} documents={documents} busy={isBusy} busyLabel={busyLabel} mutationBlocked={mutationBlocked} onReview={handleDocumentReview} onReplace={handleReplacement} onRetry={handleRetry} onContinue={handleContinueRecoveredIntake} onRefresh={() => void handleReadOnlyRefresh()} />
        </div>

        <div className="ds-two-col evidence-columns">
          <div key={`${evidenceIdentity}:ownership`} id={EVIDENCE_TARGET_IDS.ownership} className="evidence-focus-target evidence-workbench-column" tabIndex={-1}>
            <OwnershipPathExplorer key={`${evidenceIdentity}:${ownership?.analysis_id ?? "none"}`} record={ownership} />
          </div>
          <div key={`${evidenceIdentity}:recovery`} id={EVIDENCE_TARGET_IDS.recovery} className="evidence-focus-target evidence-workbench-column" tabIndex={-1}>
            <CaseStateExplanationPanel summary={summary} onNavigate={focusEvidence} />
            {evidenceFocusNotice?.identity === evidenceIdentity && <p className="ds-banner ds-banner-warn" role="status">{evidenceFocusNotice.message}</p>}
            <aside className="readiness-panel evidence-run-record" aria-label="Retained execution record">
            <h4>Submission plan</h4>
            <p className="control-help">{summary.clm.submission_plan.environment} · {summary.clm.submission_plan.base_operations.join(" → ")}</p>
            <p className="control-help">Ready-for-Approval: {summary.clm.submission_plan.real_ready_for_approval.replaceAll("_", " ")}</p>
            {summary.clm.submission_plan.request_preview && (
              <GoldTierRequestPreview preview={summary.clm.submission_plan.request_preview} />
            )}
            <div className="kv-row"><span className="kv-label">{summary.clm.submission_plan.environment === "MOCK" ? "Mock GoldTier" : "GoldTier Sandbox"} party ID</span><span className="kv-value">{summary.case.goldtier_result?.party_id ?? "—"}</span></div>
            <h4>Run metrics</h4>
            <div className="kv-row"><span className="kv-label">Automated stages</span><span className="kv-value">{summary.metrics.automated_stages_completed}</span></div>
            <div className="kv-row"><span className="kv-label">Human interventions</span><span className="kv-value">{summary.metrics.human_interventions}</span></div>
            <div className="kv-row"><span className="kv-label">Exceptions</span><span className="kv-value">{summary.metrics.exceptions_resolved}/{summary.metrics.exceptions_raised} resolved</span></div>
            <div className="kv-row"><span className="kv-label">Final outcome</span><span className="kv-value">{summary.metrics.final_outcome ? targetOutcomeLabel(summary.metrics.final_outcome, summary.clm.submission_plan.environment) : "—"}</span></div>
            </aside>
          </div>
        </div>

        {intelligence && <IntelligencePanel record={intelligence} />}

        <h4 style={{ marginTop: 24 }}>Automation timeline</h4><div className="table-card"><table className="table"><thead><tr><th>Timestamp</th><th>Stage</th><th>Event</th><th>Outcome</th></tr></thead><tbody>{summary.timeline.map((event) => <tr key={event.sequence}><td>{formatTimestamp(event.timestamp)}</td><td>{event.stage}</td><td>{event.message}</td><td>{event.outcome}</td></tr>)}</tbody></table></div>
      </div>

      {deleteDialogOpen && isCurrentCaseAction(deleteDialogOpen) && <DeleteCaseDialog caseId={deleteDialogOpen.caseId} companyName={entity?.legal_name ?? summary.case.requested_uen} requestedUen={summary.case.requested_uen} mutationDisabled={isBusy || mutationBlocked} onCancel={() => setDeleteDialogOpen(null)} onConfirm={() => deleteCase(deleteDialogOpen)} />}
    </div>
  );
}
