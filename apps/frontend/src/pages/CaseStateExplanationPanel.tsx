import type { AutomationStage, AutomationStatus, ReadinessStageStatus, ZeroTouchCaseSummary } from "../types";

export type EvidenceFocusTarget = "registry" | "documents" | "reconciliation" | "ownership" | "recovery";

const STATUS_WORDING: Record<AutomationStatus, string> = {
  PENDING_INPUTS: "The workflow is waiting for required inputs.",
  RUNNING: "The workflow is processing retained evidence.",
  WAITING_FOR_REVIEW: "The workflow is waiting for human review.",
  RESUMING: "The workflow is resuming from retained state.",
  RECOVERY_PENDING: "The workflow has retained recovery work pending.",
  COMPLETED: "The Mock workflow completed; this is not approval.",
  TECHNICAL_FAILURE: "The workflow stopped after a technical failure.",
};

const STAGE_WORDING: Record<AutomationStage, string> = {
  REGISTRY: "Registry evidence stage",
  DOCUMENT: "Document evidence and reconciliation stage",
  OWNERSHIP: "Ownership analysis stage",
  READINESS: "Readiness evaluation stage",
  MOCK_GOLDTIER: "Mock GoldTier target stage",
  COMPLETE: "Mock workflow completion stage",
};

const STAGE_TARGET: Partial<Record<AutomationStage, EvidenceFocusTarget>> = {
  REGISTRY: "registry",
  DOCUMENT: "documents",
  OWNERSHIP: "ownership",
  MOCK_GOLDTIER: "recovery",
};

const CODE_TARGET: Record<string, EvidenceFocusTarget> = {
  DOCUMENT_SOURCE_CONFLICT: "reconciliation",
  DOCUMENT_LOW_CONFIDENCE: "documents",
  DOCUMENT_REQUIRED_FIELD_MISSING: "documents",
  DOCUMENT_REVIEW_REQUIRED: "documents",
  DOCUMENT_TEXT_UNAVAILABLE: "documents",
  DOCUMENT_REUPLOAD_REQUIRED: "documents",
  OWNERSHIP_CYCLE: "ownership",
  OWNERSHIP_INCOMPLETE: "ownership",
  OWNERSHIP_REVIEW_REQUIRED: "ownership",
  MOCK_FINALIZATION_RECOVERY_PENDING: "recovery",
  TARGET_OPERATION_RECOVERY_PENDING: "recovery",
  CLM_TARGET_OUTCOME_UNCERTAIN: "recovery",
};

const READINESS_STATUSES = new Set<ReadinessStageStatus>([
  "READY",
  "MISSING",
  "IN_PROGRESS",
  "REVIEW_REQUIRED",
  "FAILED",
  "BLOCKED",
  "NOT_SUBMITTED",
  "SUBMITTED",
]);

const TARGET_OPERATIONS = new Set(["SEARCH", "SHELL", "POLICY", "AMEND"]);
const TARGET_OPERATION_STATUSES = new Set([
  "NOT_ATTEMPTED",
  "IN_PROGRESS",
  "NO_MATCH",
  "MATCH_FOUND",
  "CREATED",
  "SUCCESS",
  "FAILED",
]);

function wording<T extends string>(value: T, map: Partial<Record<T, string>>, kind: string) {
  return map[value] ?? `Unknown ${kind} value “${value}”; no interpretation is available.`;
}

function readinessStatus(value: string) {
  return READINESS_STATUSES.has(value as ReadinessStageStatus)
    ? value
    : `Unknown readiness status “${value}”; no interpretation is available.`;
}

function targetOperation(value: string) {
  return TARGET_OPERATIONS.has(value)
    ? value
    : `Unknown target operation “${value}”; no interpretation is available.`;
}

function targetOperationStatus(value: string) {
  return TARGET_OPERATION_STATUSES.has(value)
    ? value
    : `Unknown target operation status “${value}”; no interpretation is available.`;
}

export default function CaseStateExplanationPanel({
  summary,
  onNavigate,
}: {
  summary: ZeroTouchCaseSummary;
  onNavigate: (target: EvidenceFocusTarget) => void;
}) {
  const stageTarget = STAGE_TARGET[summary.current_stage];
  const stageReadiness = summary.clm.readiness;
  return (
    <section className="evidence-section-block" aria-labelledby="case-state-explanation-heading">
      <p className="card-kicker">Observed workflow evidence · read only</p>
      <h4 id="case-state-explanation-heading">Why this case is in its current state</h4>
      <p><strong>{summary.status}</strong> — {wording(summary.status, STATUS_WORDING, "automation state")}</p>
      <p><strong>{summary.current_stage}</strong> — {wording(summary.current_stage, STAGE_WORDING, "automation stage")}</p>
      <button type="button" className="btn btn-secondary" onClick={() => onNavigate("registry")}>Focus registry evidence</button>
      {stageTarget && <button type="button" className="btn btn-secondary" onClick={() => onNavigate(stageTarget)}>Focus {stageTarget} evidence</button>}

      <h5>Stage readiness</h5>
      <dl>
        <div><dt>Registry</dt><dd>{readinessStatus(stageReadiness.registry.status)}</dd></div>
        <div><dt>Document</dt><dd>{readinessStatus(stageReadiness.document.status)}</dd></div>
        <div><dt>Ownership</dt><dd>{readinessStatus(stageReadiness.ownership.status)}</dd></div>
        <div><dt>GoldTier</dt><dd>{readinessStatus(stageReadiness.goldtier.status)}</dd></div>
      </dl>

      <h5>Blockers</h5>
      {stageReadiness.blockers.length ? <ul aria-label="Active blockers">{stageReadiness.blockers.map((blocker, index) => <li key={`${index}-${blocker}`}>{blocker}</li>)}</ul> : <p className="text-muted">No blockers are recorded in the retained readiness result.</p>}
      <h5>Warnings</h5>
      {stageReadiness.warnings.length ? <ul aria-label="Warnings">{stageReadiness.warnings.map((warning, index) => <li key={`${index}-${warning}`}>{warning}</li>)}</ul> : <p className="text-muted">No warnings are recorded in the retained readiness result.</p>}

      {summary.active_exceptions.length > 0 && <div><h5>Retained exception context</h5>{summary.active_exceptions.map((exception) => {
        const target = CODE_TARGET[exception.blocker_code] ?? STAGE_TARGET[exception.stage];
        return <article key={exception.exception_id}><p><strong>{exception.stage} · {exception.blocker_code}</strong></p><p>{exception.explanation}</p>{target ? <button type="button" className="btn btn-ghost" onClick={() => onNavigate(target)}>Focus evidence for {exception.blocker_code}</button> : <p className="text-muted">No fixed evidence destination is available for this retained exception.</p>}</article>;
      })}</div>}

      <h5>Target operations in retained order</h5>
      {summary.target_operations.length ? <ol aria-label="Target operations">{summary.target_operations.map((operation, index) => <li key={`${index}-${operation.operation}`}>{targetOperation(operation.operation)}: {targetOperationStatus(operation.status)}</li>)}</ol> : <p className="text-muted">No target operations are retained. Their absence does not mean success, skipped, or retryable.</p>}
      <p className="control-help">Mock target success is not customer, compliance, legal, or Ready-for-Approval approval.</p>

      {summary.technical_failure && <div className="ds-banner ds-banner-warn"><strong>{summary.technical_failure.code}</strong><span>{summary.technical_failure.message}</span>{CODE_TARGET[summary.technical_failure.code] && <button type="button" className="btn btn-ghost" onClick={() => onNavigate(CODE_TARGET[summary.technical_failure!.code])}>Focus recovery evidence</button>}</div>}
    </section>
  );
}
