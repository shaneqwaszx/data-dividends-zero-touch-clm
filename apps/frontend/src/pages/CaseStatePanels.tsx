import { formatTimestamp, STAGE_BANDS } from "../shared";
import type {
  AutomationStage,
  ReconciliationDecisionAction,
  ReconciliationDiscrepancy,
  ReconciliationObservation,
  ZeroTouchCaseSummary,
} from "../types";

export type RegistryProgressState =
  | "SUCCESS"
  | "PENDING"
  | "ATTENTION"
  | "UNAVAILABLE"
  | "NOT_SELECTED"
  | "FAILED";

export function jurisdictionProgressState(
  status: "RESOLVED" | "UNRESOLVED" | "CONFLICT" | undefined,
): RegistryProgressState {
  if (status === "RESOLVED") return "SUCCESS";
  if (status === "CONFLICT" || status === "UNRESOLVED") return "ATTENTION";
  return "PENDING";
}

export function registryRouteProgressState(
  status: "SELECTED" | "PROVIDER_NOT_IMPLEMENTED" | undefined,
): RegistryProgressState {
  if (status === "SELECTED") return "SUCCESS";
  if (status === "PROVIDER_NOT_IMPLEMENTED") return "UNAVAILABLE";
  return "NOT_SELECTED";
}

export function registryOperationProgressState(
  status: "COMPLETE" | "EMPTY" | "FAILED" | "NOT_ATTEMPTED",
): RegistryProgressState {
  if (status === "COMPLETE" || status === "EMPTY") return "SUCCESS";
  if (status === "FAILED") return "FAILED";
  return "NOT_SELECTED";
}

function progressStateLabel(state: RegistryProgressState): string {
  return state.replaceAll("_", " ").toLowerCase();
}

export function stageBandState(
  summary: ZeroTouchCaseSummary,
  stages: AutomationStage[],
): "done" | "now" | "attention" | "" {
  if (summary.status === "COMPLETED") return "done";
  if (stages.every((stage) => summary.completed_stages.includes(stage))) return "done";
  if (stages.includes(summary.current_stage)) {
    return summary.status === "WAITING_FOR_REVIEW" || summary.status === "TECHNICAL_FAILURE"
      ? "attention"
      : "now";
  }
  return "";
}

export function PipelineRail({ summary }: { summary: ZeroTouchCaseSummary }) {
  return (
    <div className="ds-stage-rail" aria-label="Backend workflow stages">
      {STAGE_BANDS.map((band, index) => {
        const state = stageBandState(summary, band.stages);
        return (
          <div className="ds-stage" key={band.label}>
            <div className="ds-stage-marker">
              <span className={`ds-stage-node ${state}`}>
                {state === "done" ? "✓" : index + 1}
              </span>
              {index < STAGE_BANDS.length - 1 && (
                <span className={`ds-stage-line ${state === "done" ? "done" : ""}`} />
              )}
            </div>
            <div className="ds-stage-copy">
              <div>{band.label}</div>
              <div className="text-muted">
                {state === "done"
                  ? "Cleared"
                  : state === "now"
                    ? "In progress"
                    : state === "attention"
                      ? "Attention required"
                      : "Pending"}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function observationText(observation: ReconciliationObservation): string {
  const confidence = observation.confidence === null
    ? "confidence —"
    : `${Math.round(observation.confidence * 100)}% confidence`;
  return `${observation.normalized_value ?? "—"} · ${observation.validity} · ${confidence}`;
}

export function RegistryStatePanel({ summary }: { summary: ZeroTouchCaseSummary }) {
  const resolution = summary.case.jurisdiction_resolution;
  const route = summary.case.registry_route;
  const acquisition = summary.case.registry_acquisition;
  const registryException = summary.active_exceptions.find((item) => item.stage === "REGISTRY");
  const jurisdictionState = jurisdictionProgressState(resolution?.status);
  const routeState = registryRouteProgressState(route?.status);
  const attention = Boolean(registryException)
    || (summary.current_stage === "REGISTRY" && summary.status === "TECHNICAL_FAILURE")
    || resolution?.status === "UNRESOLVED"
    || resolution?.status === "CONFLICT"
    || route?.status === "PROVIDER_NOT_IMPLEMENTED"
    || acquisition?.status === "FAILED";

  if (summary.current_stage !== "REGISTRY" && !attention) return null;

  return (
    <section className="state-composition" aria-labelledby="registry-state-heading">
      <div className="state-composition__header">
        <div>
          <p className="card-kicker">Registry acquisition</p>
          <h2 id="registry-state-heading">{attention ? "Registry unavailable" : "Reading the registry"}</h2>
          <p className="text-muted">
            {attention
              ? "The workflow stopped at the registry boundary. No provider, retry, or source decision is invented by the browser."
              : "Jurisdiction routing and the bounded ACRA acquisition operations are reported from backend state."}
          </p>
        </div>
        <span className={attention ? "tag tag-outline" : "tag tag-accent-2"}>
          {attention ? "Attention required" : summary.status.replaceAll("_", " ")}
        </span>
      </div>

      {attention && (
        <div className="ds-banner ds-banner-warn registry-stop">
          <strong>{registryException?.blocker_code ?? summary.technical_failure?.code ?? acquisition?.issues[0]?.code ?? "REGISTRY_STOP"}</strong>
          <span>{registryException?.explanation ?? summary.technical_failure?.message ?? acquisition?.issues[0]?.message ?? "Registry processing cannot continue in the current POC state."}</span>
        </div>
      )}

      <div className="state-grid state-grid--registry">
        <div className="card progress-card">
          <p className="card-kicker">Progress</p>
          <ol className="progress-list">
            <li data-state={jurisdictionState} aria-label={`Jurisdiction status: ${progressStateLabel(jurisdictionState)}`}>
              <strong>Jurisdiction {resolution?.status?.toLowerCase() ?? "not evaluated"}</strong>
              <span>Status: {progressStateLabel(jurisdictionState)} · {resolution?.resolved_jurisdiction ?? "—"} · {resolution?.observations.length ?? 0} observation(s)</span>
            </li>
            <li data-state={routeState} aria-label={`Registry route status: ${progressStateLabel(routeState)}`}>
              <strong>Registry route {route?.status?.toLowerCase().replaceAll("_", " ") ?? "not selected"}</strong>
              <span>Status: {progressStateLabel(routeState)} · {route?.provider ?? "No provider"} · {route?.jurisdiction ?? "—"}</span>
            </li>
            {(acquisition?.operation_results ?? []).map((operation) => {
              const operationState = registryOperationProgressState(operation.status);
              return (
                <li key={operation.operation} data-state={operationState} aria-label={`${operation.operation.replaceAll("_", " ")} status: ${progressStateLabel(operationState)}`}>
                  <strong>{operation.operation.replaceAll("_", " ").toLowerCase()}</strong>
                  <span>
                    Status: {progressStateLabel(operationState)} · {operation.status} · {operation.record_count} record(s)
                    {operation.provenance ? ` · ${operation.provenance.provider} ${operation.provenance.environment}` : ""}
                  </span>
                </li>
              );
            })}
          </ol>
        </div>
        <aside className="card registry-policy-card">
          <p className="card-kicker">Registry boundary</p>
          <div className="kv-row"><span className="kv-label">Provider</span><span className="kv-value">{route?.provider ?? "—"}</span></div>
          <div className="kv-row"><span className="kv-label">Environment</span><span className="kv-value">{summary.case.entity?.source.environment ?? acquisition?.operation_results.find((item) => item.provenance)?.provenance?.environment ?? "—"}</span></div>
          <div className="kv-row"><span className="kv-label">Acquisition</span><span className="kv-value">{acquisition?.status ?? "Not started"}</span></div>
          <div className="kv-row"><span className="kv-label">Access</span><span className="kv-value">Backend-managed</span></div>
          <p className="control-help">Live ACRA binding remains pending Q-012. Foreign providers are not implemented.</p>
        </aside>
      </div>

      {acquisition && acquisition.issues.length > 0 && (
        <div className="issue-list" aria-label="Registry issues">
          {acquisition.issues.map((issue) => <p key={issue.code}><strong>{issue.code}</strong> · {issue.message}</p>)}
        </div>
      )}
    </section>
  );
}

export function ConfirmDetailsPanel({
  summary,
  isBusy = false,
  onResolve,
}: {
  summary: ZeroTouchCaseSummary;
  isBusy?: boolean;
  onResolve?: (discrepancy: ReconciliationDiscrepancy, action: ReconciliationDecisionAction) => void;
}) {
  const reconciliation = summary.reconciliation;
  if (!reconciliation || summary.current_stage !== "DOCUMENT") return null;
  const discrepancies = new Map(reconciliation.discrepancies.map((item) => [item.discrepancy_id, item]));
  return (
    <section className="state-composition confirm-details" aria-labelledby="confirm-details-heading">
      <div className="state-composition__header">
        <div>
          <p className="card-kicker">Source-neutral reconciliation</p>
          <h2 id="confirm-details-heading">Confirm details</h2>
          <p className="text-muted">Registry and document observations remain separate. No source wins automatically.</p>
        </div>
        <span className="tag tag-accent-2">{reconciliation.status.replaceAll("_", " ")}</span>
      </div>
      <div className="reconciliation-summary" aria-label="Reconciliation outcomes">
        {(["MATCH", "CONFLICT", "MISSING_IN_SOURCE", "UNVERIFIABLE", "INVALID"] as const).map((outcome) => (
          <span className={`tag outcome-${outcome.toLowerCase()}`} key={outcome}>
            {reconciliation.fields.filter((field) => field.outcome === outcome).length} {outcome.replaceAll("_", " ").toLowerCase()}
          </span>
        ))}
      </div>
      <div className="confirm-grid">
        {reconciliation.fields.map((field) => {
          const discrepancy = field.discrepancy_id ? discrepancies.get(field.discrepancy_id) : undefined;
          const registry = field.observations.filter((item) => item.source_kind === "REGISTRY");
          const documents = field.observations.filter((item) => item.source_kind === "DOCUMENT_IDP");
          return (
            <article className={`comparison-card outcome-${field.outcome.toLowerCase()}`} key={field.field_name}>
              <header>
                <h3>{field.field_name.replaceAll("_", " ")}</h3>
                <span className="tag tag-neutral">{field.outcome.replaceAll("_", " ")}</span>
              </header>
              <div className="comparison-sources">
                <div><span>Registry observation</span><strong>{registry.length ? registry.map(observationText).join(" · ") : "Not observed"}</strong></div>
                <div><span>Document observation</span><strong>{documents.length ? documents.map(observationText).join(" · ") : "Not observed"}</strong></div>
              </div>
              <details>
                <summary>Provenance and decision state</summary>
                {field.observations.map((observation) => (
                  <p key={observation.observation_id}>
                    {observation.source_kind} · {observation.source_system ?? "—"} {observation.environment ?? "—"} · {observation.evidence_reference ?? "safe reference unavailable"}
                  </p>
                ))}
                <p>Decision: {discrepancy?.decision?.action.replaceAll("_", " ") ?? discrepancy?.status ?? "Not required"}</p>
              </details>
              {discrepancy?.status === "OPEN" && discrepancy.allowed_actions.length > 0 && onResolve && (
                <div className="comparison-actions">
                  {discrepancy.allowed_actions.map((action) => (
                    <button className="btn btn-primary" type="button" disabled={isBusy} key={action} onClick={() => onResolve(discrepancy, action)}>
                      {action === "KEEP_REGISTRY_VALUE" ? "Keep registry value" : "Use document value"}
                    </button>
                  ))}
                </div>
              )}
              {discrepancy?.status === "OPEN" && discrepancy.allowed_actions.length === 0 && (
                <p className="control-help">Replacement evidence is required; no value-selection action is allowed.</p>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}

export function CompletedOverview({
  summary,
  onViewOnboarded,
  onViewAudit,
}: {
  summary: ZeroTouchCaseSummary;
  onViewOnboarded?: (caseId: string) => void;
  onViewAudit?: (caseId: string) => void;
}) {
  if (summary.status !== "COMPLETED") return null;
  const completedAt = [...summary.timeline].reverse().find((item) => item.event_type === "MOCK_SUBMISSION_COMPLETED")?.timestamp ?? summary.updated_at;
  const targetId = summary.case.goldtier_result?.party_id;
  return (
    <section className="state-composition completed-overview" aria-labelledby="completed-heading">
      <div className="state-composition__header">
        <div>
          <p className="card-kicker">Completed Mock workflow</p>
          <h2 id="completed-heading">{summary.case.entity?.legal_name ?? summary.case.requested_uen} is onboarded</h2>
          <p className="text-muted">Completed zero-touch Mock workflow on {formatTimestamp(completedAt)}. This is not production approval or Ready-for-Approval.</p>
        </div>
      </div>
      <div className="state-grid completed-grid">
        <div className="card">
          <p className="card-kicker">Stage record</p>
          <div className="table-scroll" tabIndex={0}>
            <table className="table">
              <thead><tr><th>Stage</th><th>Outcome</th><th>Method</th><th>Cleared</th></tr></thead>
              <tbody>
                {STAGE_BANDS.map((band) => {
                  const timestamp = [...summary.timeline].reverse().find((item) => band.stages.includes(item.stage) && item.outcome === "SUCCEEDED")?.timestamp;
                  return <tr key={band.label}><td>{band.label}</td><td>Cleared</td><td>Backend automation</td><td>{timestamp ? formatTimestamp(timestamp) : "—"}</td></tr>;
                })}
              </tbody>
            </table>
          </div>
        </div>
        <aside className="card">
          <p className="card-kicker">Mock client record</p>
          <div className="kv-row"><span className="kv-label">Mock GoldTier party ID</span><span className="kv-value">{targetId ?? "—"}</span></div>
          <div className="kv-row"><span className="kv-label">Risk rating</span><span className="kv-value">—</span></div>
          <div className="kv-row"><span className="kv-label">Next review</span><span className="kv-value">—</span></div>
          <div className="kv-row"><span className="kv-label">Human touches</span><span className="kv-value">{summary.metrics.human_interventions}</span></div>
          <div className="kv-row"><span className="kv-label">Elapsed</span><span className="kv-value">{summary.metrics.total_duration_ms === null ? "—" : `${summary.metrics.total_duration_ms} ms`}</span></div>
          {onViewOnboarded && <button className="btn btn-secondary btn-block" type="button" onClick={() => onViewOnboarded(summary.case.case_id)}>View in Onboarded</button>}
          {onViewAudit && <button className="btn btn-secondary btn-block" type="button" onClick={() => onViewAudit(summary.case.case_id)}>View audit trail</button>}
          <button className="btn btn-secondary btn-block" type="button" disabled title="Audit export is not available in current POC">Download audit trail</button>
        </aside>
      </div>
    </section>
  );
}
