import { useId, useState, type CSSProperties } from "react";

import { formatDuration, formatTimestamp } from "../shared";
import type {
  ReconciliationDecisionAction,
  ReconciliationDiscrepancy,
  ReconciliationObservation,
  ProcessingNode,
  ProcessingNodeStatus,
  SimulationProfile,
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
  status: "COMPLETE" | "EMPTY" | "FAILED" | "NOT_ATTEMPTED" | "UNSUPPORTED",
): RegistryProgressState {
  if (status === "COMPLETE" || status === "EMPTY") return "SUCCESS";
  if (status === "FAILED") return "FAILED";
  if (status === "UNSUPPORTED") return "UNAVAILABLE";
  return "NOT_SELECTED";
}

function progressStateLabel(state: RegistryProgressState): string {
  return state.replaceAll("_", " ").toLowerCase();
}

function pipelineRailState(status: ProcessingNodeStatus): "done" | "now" | "attention" | "" {
  if (status === "COMPLETE" || status === "EMPTY" || status === "SKIPPED") return "done";
  if (status === "IN_PROGRESS") return "now";
  if (status === "REVIEW_REQUIRED" || status === "BLOCKED" || status === "FAILED") return "attention";
  return "";
}

export function PipelineRail({ summary }: { summary: ZeroTouchCaseSummary }) {
  const pipeline = summary.processing_pipeline ?? [];
  return (
    <div className="ds-stage-rail" aria-label="Backend workflow stages">
      {pipeline.map((node, index) => {
        const state = pipelineRailState(node.status);
        return (
          <div className="ds-stage" key={node.node_id} data-status={node.status}>
            <div className="ds-stage-marker">
              <span className={`ds-stage-node ${state}`}>
                {state === "done" ? "✓" : index + 1}
              </span>
              {index < pipeline.length - 1 && (
                <span className={`ds-stage-line ${state === "done" ? "done" : ""}`} />
              )}
            </div>
            <div className="ds-stage-copy">
              <div>{node.label}</div>
              <div className="text-muted">{PROGRESS_STATUS_LABELS[node.status]}</div>
            </div>
          </div>
        );
      })}
      {pipeline.length === 0 && <p className="empty-copy">Backend pipeline not reported yet.</p>}
    </div>
  );
}

export function DetailedProcessingInspector({ summary }: { summary: ZeroTouchCaseSummary }) {
  const [expanded, setExpanded] = useState(false);
  const contentId = useId();
  const registryOperations = (summary.case.registry_acquisition?.operation_results ?? [])
    .filter((operation) => operation.status !== "NOT_ATTEMPTED");
  const targetOperations = (summary.target_operations ?? [])
    .filter((operation) => operation.status !== "NOT_ATTEMPTED");
  const timeline = summary.timeline ?? [];
  const processingPipeline = summary.processing_pipeline ?? [];

  return (
      <section className="card processing-inspector" aria-labelledby="processing-inspector-heading">
      <div className="state-composition__header">
        <div>
          <p className="card-kicker">Backend-authored processing record</p>
          <h2 id="processing-inspector-heading">Detailed processing</h2>
          <p className="text-muted">The ordered steps and statuses below come from the backend processing record.</p>
        </div>
        <button
          type="button"
          className="btn btn-secondary"
          aria-expanded={expanded}
          aria-controls={contentId}
          onClick={() => setExpanded((current) => !current)}
        >
          {expanded ? "Hide processing details" : "Show processing details"}
        </button>
      </div>

      <div id={contentId} hidden={!expanded}>
        {processingPipeline.length ? (
          <ol className="processing-pipeline" aria-label="Backend processing pipeline">
            {processingPipeline.map((node) => (
              <ProcessingPipelineNodeView key={node.node_id} node={node} />
            ))}
          </ol>
        ) : (
          <p className="empty-copy">No processing pipeline has been reported yet.</p>
        )}

        <details className="processing-inspector__technical-details">
          <summary>Technical details</summary>
          <div className="processing-inspector__technical-content">
            <dl>
              <div><dt>Current stage</dt><dd>{summary.current_stage.replaceAll("_", " ")}</dd></div>
              <div><dt>Case status</dt><dd>{summary.status.replaceAll("_", " ")}</dd></div>
              <div><dt>Last backend update</dt><dd>{formatTimestamp(summary.updated_at)}</dd></div>
            </dl>

            {registryOperations.length > 0 && (
              <div className="table-scroll" tabIndex={0} aria-label="Occurred registry operations">
                <table className="table">
                  <thead><tr><th>Provider</th><th>Operation</th><th>Status</th><th>Safe result</th></tr></thead>
                  <tbody>
                    {registryOperations.map((operation) => (
                      <tr key={operation.operation}>
                        <td>{operation.provenance ? `${operation.provenance.provider} ${operation.provenance.environment}` : "Registry provider"}</td>
                        <td>{operation.operation.replaceAll("_", " ")}</td>
                        <td>{operation.status.replaceAll("_", " ")}</td>
                        <td>{operation.error ? `${operation.error.code}: ${operation.error.message}` : `${operation.record_count} record(s)`}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {targetOperations.length > 0 && (
              <div className="table-scroll" tabIndex={0} aria-label="Occurred GoldTier operations">
                <table className="table">
                  <thead><tr><th>Provider</th><th>Operation</th><th>Status</th></tr></thead>
                  <tbody>
                    {targetOperations.map((operation) => (
                      <tr key={operation.operation}>
                        <td>GoldTier {summary.clm.submission_plan.environment}</td>
                        <td>{operation.operation.replaceAll("_", " ")}</td>
                        <td>{operation.status.replaceAll("_", " ")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {timeline.length > 0 && (
              <div className="table-scroll" tabIndex={0} aria-label="Occurred automation events">
                <table className="table">
                  <thead><tr><th>Timestamp</th><th>Stage</th><th>Status</th><th>Safe event</th></tr></thead>
                  <tbody>
                    {timeline.map((event) => (
                      <tr key={event.sequence}>
                        <td>{formatTimestamp(event.timestamp)}</td>
                        <td>{event.stage.replaceAll("_", " ")}</td>
                        <td>{event.status.replaceAll("_", " ")}</td>
                        <td>{event.code ?? event.event_type}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {registryOperations.length === 0 && targetOperations.length === 0 && timeline.length === 0 && (
              <p className="empty-copy">No processing event has been reported yet.</p>
            )}
            <p className="control-help">Credentials, raw provider payloads, document contents, and internal exceptions are excluded.</p>
          </div>
        </details>
      </div>
    </section>
  );
}

const PROGRESS_STATUS_LABELS: Record<ProcessingNodeStatus, string> = {
  UNSUPPORTED: "Unsupported",
  COMPLETE: "Complete",
  IN_PROGRESS: "In progress",
  EMPTY: "Complete — no records",
  SKIPPED: "Skipped",
  REVIEW_REQUIRED: "Review required",
  BLOCKED: "Blocked",
  FAILED: "Failed",
  NOT_REACHED: "Not reached",
};

const PROGRESS_STATUS_SYMBOLS: Record<ProcessingNodeStatus, string> = {
  UNSUPPORTED: "—",
  COMPLETE: "✓",
  IN_PROGRESS: "●",
  EMPTY: "✓",
  SKIPPED: "↷",
  REVIEW_REQUIRED: "!",
  BLOCKED: "■",
  FAILED: "×",
  NOT_REACHED: "○",
};

function currentProcessingNode(nodes: ProcessingNode[]): ProcessingNode | undefined {
  const node = nodes.find((item) =>
    ["IN_PROGRESS", "REVIEW_REQUIRED", "BLOCKED", "FAILED"].includes(item.status)
  );
  if (node) return node;
  return nodes.find((item) => item.status === "NOT_REACHED") ?? nodes.at(-1);
}

const NAVIGABLE_PROCESSING_STATUSES = new Set<ProcessingNodeStatus>([
  "REVIEW_REQUIRED",
  "BLOCKED",
  "FAILED",
]);

export function processingNodeFocusTarget(node: ProcessingNode): string | null {
  const nodeId = node.node_id;
  if (nodeId === "INITIAL_IDENTITY") return "case-identity-correction";
  if (!NAVIGABLE_PROCESSING_STATUSES.has(node.status)) return null;
  if (nodeId === "ACRA_REGISTRY" || nodeId.startsWith("ACRA_")) return "case-evidence-registry";
  if (nodeId === "DOCUMENT_IDP") return "case-evidence-documents";
  if (nodeId === "RECONCILIATION") return "case-evidence-reconciliation";
  if (nodeId === "OWNERSHIP_UBO") return "case-evidence-ownership";
  if ([
    "TARGET_CLASSIFICATION_REGISTRATION_TYPE",
    "TARGET_CLASSIFICATION_CUSTOMER_EXTERNAL_SYSTEM",
    "TARGET_CLASSIFICATION_POLICY",
    "TARGET_CLASSIFICATION_BOOKING_ENTITY",
  ].includes(nodeId)) return "case-policy-rebind";
  if (nodeId === "TARGET_CLASSIFICATION" || nodeId.startsWith("TARGET_CLASSIFICATION_")) return "case-target-classification";
  if (nodeId === "GOLDTIER_SEARCH" || nodeId.startsWith("GOLDTIER_SEARCH_")) return "case-search-diagnostic";
  if (nodeId === "GOLDTIER_TARGET" || nodeId.startsWith("GOLDTIER_")) return "case-target-blocker";
  if (nodeId === "HUMAN_APPROVAL") return "case-human-approval-boundary";
  return null;
}

export function findProcessingNode(nodes: ProcessingNode[], nodeId: string): ProcessingNode | null {
  for (const node of nodes) {
    if (node.node_id === nodeId) return node;
    const nested = findProcessingNode(node.children, nodeId);
    if (nested) return nested;
  }
  return null;
}

function ProcessingExplanation({ node, children }: { node: ProcessingNode; children: string }) {
  return (
    <>
      <p><strong>Status:</strong> {PROGRESS_STATUS_LABELS[node.status]}</p>
      {node.blocker_code && <p><strong>Safe blocker code:</strong> {node.blocker_code}</p>}
      {node.safe_result && <p>{node.safe_result}</p>}
      <p className="control-help">{children}</p>
    </>
  );
}

export function ProcessingBlockerPanels({ summary }: { summary: ZeroTouchCaseSummary }) {
  const pipeline = summary.processing_pipeline ?? [];
  const search = findProcessingNode(pipeline, "GOLDTIER_SEARCH");
  const target = findProcessingNode(pipeline, "GOLDTIER_TARGET");
  const approval = findProcessingNode(pipeline, "HUMAN_APPROVAL");
  return (
    <>
      {search && NAVIGABLE_PROCESSING_STATUSES.has(search.status) && (
        <section id="case-search-diagnostic" className="card evidence-focus-target" tabIndex={-1} aria-labelledby="case-search-diagnostic-heading">
          <p className="card-kicker">Read-only diagnostic</p>
          <h2 id="case-search-diagnostic-heading">GoldTier Search</h2>
          <ProcessingExplanation node={search}>
            A failed Search does not prove that the customer is absent. Target identity remains unresolved, so no target mutation or browser retry is available.
          </ProcessingExplanation>
        </section>
      )}
      {target && NAVIGABLE_PROCESSING_STATUSES.has(target.status) && (
        <section id="case-target-blocker" className="card evidence-focus-target" tabIndex={-1} aria-labelledby="case-target-blocker-heading">
          <p className="card-kicker">Target safety boundary</p>
          <h2 id="case-target-blocker-heading">GoldTier target operations</h2>
          <ProcessingExplanation node={target}>
            The server has blocked Shell, Policy, Amend, and downstream target work. This explanation does not provide a bypass or replay action.
          </ProcessingExplanation>
        </section>
      )}
      {approval && NAVIGABLE_PROCESSING_STATUSES.has(approval.status) && (
        <section id="case-human-approval-boundary" className="card evidence-focus-target" tabIndex={-1} aria-labelledby="case-human-approval-heading">
          <p className="card-kicker">POC boundary</p>
          <h2 id="case-human-approval-heading">Human approval</h2>
          <ProcessingExplanation node={approval}>
            Final approval is unresolved and remains outside this POC. Any available case action is shown separately from this read-only boundary.
          </ProcessingExplanation>
        </section>
      )}
    </>
  );
}

export function OnboardingProgressPanel({
  summary,
  onStageActivate,
  availableFocusTargets,
}: {
  summary: ZeroTouchCaseSummary;
  onStageActivate?: (node: ProcessingNode) => void;
  availableFocusTargets?: ReadonlySet<string>;
}) {
  const retainedPipeline = summary.processing_pipeline ?? [];
  const identityIncomplete = summary.active_exceptions.some(
    (exception) => exception.blocker_code === "INITIAL_IDENTITY_INCOMPLETE",
  );
  const hasTopLevelIdentity = retainedPipeline.some((node) => node.node_id === "INITIAL_IDENTITY");
  const identityCorrectionNode: ProcessingNode = {
        node_id: "INITIAL_IDENTITY",
        label: "Initial identity correction required for a retained Singapore case",
        status: "REVIEW_REQUIRED",
        backend_stage: null,
        timestamp: summary.updated_at,
        safe_result: "Complete legal name, Singapore UEN, and jurisdiction before Search resumes.",
        blocker_code: "INITIAL_IDENTITY_INCOMPLETE",
        children: [],
      };
  const pipeline: ProcessingNode[] = identityIncomplete
    ? hasTopLevelIdentity
      ? retainedPipeline.map((node) => (
          node.node_id === "INITIAL_IDENTITY"
            ? { ...node, ...identityCorrectionNode }
            : node
        ))
      : [identityCorrectionNode, ...retainedPipeline]
    : retainedPipeline;
  const completed = pipeline.filter((node) =>
    node.status === "COMPLETE" || node.status === "EMPTY" || node.status === "SKIPPED"
  ).length;
  const current = currentProcessingNode(pipeline);
  const maximum = Math.max(pipeline.length, 1);
  const percentage = Math.round((completed / maximum) * 100);
  const currentText = current
    ? `${current.label} — ${PROGRESS_STATUS_LABELS[current.status]}`
    : "Waiting for backend processing state";

  return (
    <section className="card onboarding-progress" aria-labelledby="onboarding-progress-heading" aria-live="polite">
      <div className="state-composition__header">
        <div>
          <p className="card-kicker">Live backend state</p>
          <h2 id="onboarding-progress-heading">Onboarding progress</h2>
        </div>
        <span className="processing-pipeline__status" data-status={current?.status ?? "NOT_REACHED"}>
          {current ? PROGRESS_STATUS_LABELS[current.status] : "Not reached"}
        </span>
      </div>
      <div
        className="onboarding-progress__bar"
        role="progressbar"
        aria-labelledby="onboarding-progress-heading"
        aria-valuemin={0}
        aria-valuemax={pipeline.length}
        aria-valuenow={completed}
        aria-valuetext={`${completed} of ${pipeline.length} stages complete or skipped; current: ${currentText}`}
      >
        <span style={{ "--onboarding-progress": `${percentage}%` } as CSSProperties} />
      </div>
      <p className="onboarding-progress__current"><strong>Current:</strong> {currentText}</p>
      {pipeline.length > 0 ? (
        <ol className="onboarding-progress__stages" aria-label="Onboarding stages">
          {pipeline.map((node) => {
            const target = processingNodeFocusTarget(node);
            const navigable = Boolean(
              onStageActivate
              && target
              && (!availableFocusTargets || availableFocusTargets.has(target)),
            );
            const content = <>
              <span className="onboarding-progress__title-row">
                <span className="onboarding-progress__symbol" aria-hidden="true">{PROGRESS_STATUS_SYMBOLS[node.status]}</span>
                <span className="onboarding-progress__stage-label">{node.label}</span>
              </span>
              <span className="onboarding-progress__stage-status">{PROGRESS_STATUS_LABELS[node.status]}</span>
              {navigable && <span className="onboarding-progress__stage-action">Review details</span>}
            </>;
            return (
              <li
                key={node.node_id}
                className={navigable ? "onboarding-progress__stage onboarding-progress__stage--actionable" : "onboarding-progress__stage"}
                data-status={node.status}
              >
                {navigable ? (
                  <button type="button" onClick={() => onStageActivate?.(node)} aria-label={`Open details for ${node.label}`}>
                    {content}
                  </button>
                ) : <div className="onboarding-progress__stage-content">{content}</div>}
              </li>
            );
          })}
        </ol>
      ) : (
        <p className="empty-copy">The backend has not reported a processing route yet.</p>
      )}
      <p className="onboarding-progress__updated"><strong>Last updated:</strong> {formatTimestamp(summary.updated_at)}</p>
    </section>
  );
}

function processingStatusLabel(status: ProcessingNodeStatus): string {
  return status.replaceAll("_", " ");
}

function ProcessingPipelineNodeView({ node }: { node: ProcessingNode }) {
  const safeDetails = [
    node.provider && { label: "Provider", value: node.provider },
    node.environment && { label: "Environment", value: node.environment },
    node.operation && { label: "Operation", value: node.operation.replaceAll("_", " ") },
    node.backend_stage && { label: "Backend stage", value: node.backend_stage.replaceAll("_", " ") },
    node.timestamp && { label: "Recorded at", value: formatTimestamp(node.timestamp) },
    node.record_count !== null && node.record_count !== undefined && {
      label: "Record count",
      value: String(node.record_count),
    },
    node.blocker_code && { label: "Blocker code", value: node.blocker_code },
    node.retained_goldtier_id && { label: "Retained GoldTier ID", value: node.retained_goldtier_id },
  ].filter((item): item is { label: string; value: string } => Boolean(item));

  return (
    <li className="processing-pipeline__node" data-status={node.status}>
      <div className="processing-pipeline__node-heading">
        <span className="processing-pipeline__node-title">{node.label}</span>
        <span
          className="processing-pipeline__status"
          data-status={node.status}
          aria-label={`Status: ${processingStatusLabel(node.status)}`}
        >
          {processingStatusLabel(node.status)}
        </span>
      </div>
      {node.safe_result && <p className="processing-pipeline__result">{node.safe_result}</p>}
      {safeDetails.length > 0 && (
        <dl className="processing-pipeline__details">
          {safeDetails.map((item) => (
            <div key={item.label}><dt>{item.label}</dt><dd>{item.value}</dd></div>
          ))}
        </dl>
      )}
      {node.children.length > 0 && (
        <ol className="processing-pipeline__children" aria-label={`${node.label} steps`}>
          {node.children.map((child) => (
            <ProcessingPipelineNodeView key={child.node_id} node={child} />
          ))}
        </ol>
      )}
    </li>
  );
}

export function OperationalTiming({ summary }: { summary: ZeroTouchCaseSummary }) {
  const stages = Object.entries(summary.metrics.stage_durations_ms);
  return (
    <section className="card operational-timing" aria-labelledby="operational-timing-heading">
      <p className="card-kicker">Factual observation</p>
      <h2 id="operational-timing-heading">Operational timing</h2>
      <p className="text-muted">
        Timing observed at {formatTimestamp(summary.timing.observed_at)}. Values remain fixed until the case is refreshed.
      </p>
      <div className="operational-timing__facts">
        <div className="kv-row">
          <span className="kv-label">{summary.status === "COMPLETED" ? "Case duration" : "Case age"}</span>
          <span className="kv-value">{formatDuration(summary.timing.case_elapsed_ms)}</span>
        </div>
        <div className="kv-row">
          <span className="kv-label">Last updated</span>
          <span className="kv-value">{formatDuration(summary.timing.time_since_last_update_ms)} ago</span>
        </div>
        <div className="kv-row">
          <span className="kv-label">Automation elapsed</span>
          <span className="kv-value">
            {summary.timing.automation_elapsed_ms === null
              ? "Not started"
              : formatDuration(summary.timing.automation_elapsed_ms)}
          </span>
        </div>
        <div className="kv-row">
          <span className="kv-label">Recorded total automation duration</span>
          <span className="kv-value">
            {summary.timing.recorded_total_duration_ms === null
              ? "Not recorded"
              : formatDuration(summary.timing.recorded_total_duration_ms)}
          </span>
        </div>
      </div>
      {stages.length > 0 && (
        <div className="table-scroll" tabIndex={0} aria-label="Recorded automated-stage processing durations">
          <table className="table">
            <thead><tr><th>Automated stage</th><th>Recorded automated-stage processing duration</th></tr></thead>
            <tbody>
              {stages.map(([stage, duration]) => (
                <tr key={stage}>
                  <td>{stage.replaceAll("_", " ")}</td>
                  <td>{formatDuration(duration)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="control-help">
        Stage values cover completed automated processing attempts only. They do not represent human waiting time or complete time in a stage.
      </p>
    </section>
  );
}

function observationText(observation: ReconciliationObservation): string {
  const confidence = observation.confidence === null
    ? "confidence —"
    : `${Math.round(observation.confidence * 100)}% confidence`;
  return `${observation.normalized_value ?? "—"} · ${observation.validity} · ${confidence}`;
}

type RegistryProviderMode = SimulationProfile["registry_provider_mode"];

export interface RegistryPresentation {
  heading: string;
  description: string;
  tag: string;
  provider: string;
  connection: string;
  entity: string;
  issue: string;
  action: string;
  attention: boolean;
  code: string | null;
  message: string | null;
}

const REGISTRY_UNAVAILABLE_CODES = new Set([
  "REGISTRY_OPERATION_TIMEOUT",
  "REGISTRY_OPERATION_UNAVAILABLE",
  "REGISTRY_PROVIDER_NOT_IMPLEMENTED",
]);

const REGISTRY_MALFORMED_CODES = new Set([
  "REGISTRY_OPERATION_MALFORMED_RESPONSE",
  "ACRA_RESPONSE_INVALID",
  "ACRA_MALFORMED_RESPONSE",
]);

function registryProviderLabel(mode: RegistryProviderMode, fallback?: string): string {
  if (mode === "API_MARKETPLACE_PROTOCOL_TEST") return "ACRA Marketplace protocol · synthetic offline test evidence";
  if (mode === "API_MARKETPLACE_MOCK") return "Official ACRA API Marketplace Mock";
  if (mode === "LOCAL_MOCK") return "Synthetic local ACRA Mock";
  if (mode === "GENERIC_SANDBOX") return "Generic ACRA sandbox";
  return fallback ?? "Not selected";
}

export function registryPresentation(
  summary: ZeroTouchCaseSummary,
  providerMode?: RegistryProviderMode,
): RegistryPresentation {
  const acquisition = summary.case.registry_acquisition;
  const registryNode = (summary.processing_pipeline ?? [])
    .find((item) => item.node_id === "ACRA_REGISTRY");
  const registryException = summary.active_exceptions.find((item) => item.stage === "REGISTRY");
  const issue = acquisition?.issues[0];
  const operationError = acquisition?.operation_results.find((item) => item.error)?.error;
  const routeCode = summary.case.registry_route?.status === "PROVIDER_NOT_IMPLEMENTED"
    ? "REGISTRY_PROVIDER_NOT_IMPLEMENTED"
    : null;
  const jurisdictionCode = summary.case.jurisdiction_resolution?.status === "CONFLICT"
    ? "JURISDICTION_CONFLICT"
    : summary.case.jurisdiction_resolution?.status === "UNRESOLVED"
      ? "JURISDICTION_UNRESOLVED"
      : null;
  const code = registryException?.blocker_code
    ?? summary.technical_failure?.code
    ?? issue?.code
    ?? operationError?.code
    ?? routeCode
    ?? jurisdictionCode;
  const message = registryException?.explanation
    ?? summary.technical_failure?.message
    ?? issue?.message
    ?? operationError?.message
    ?? (jurisdictionCode ? "Jurisdiction must be resolved before a registry route can be selected." : null);
  const provider = registryProviderLabel(providerMode, summary.case.registry_route?.provider ?? undefined);
  const entity = summary.case.entity?.legal_name ?? "Not retrieved";
  const entityRetrieved = Boolean(summary.case.entity)
    || acquisition?.operation_results.some(
      (operation) => operation.operation === "ENTITY_PROFILE" && operation.status === "COMPLETE",
    ) === true;

  if (!acquisition && registryNode?.status === "NOT_REACHED") {
    return {
      heading: "ACRA not reached",
      description: registryNode.safe_result ?? "The backend reports that registry acquisition has not started.",
      tag: "Not reached",
      provider,
      connection: "No ACRA call occurred",
      entity,
      issue: registryNode.blocker_code ? "Blocked by prior backend review" : "Not started",
      action: "Resolve the prior backend-authored blocker",
      attention: false,
      code: registryNode.blocker_code ?? null,
      message: registryNode.safe_result ?? null,
    };
  }

  if (code === "REGISTRY_EXPECTED_DATA_MISSING") {
    if (!registryException && summary.completed_stages.includes("REGISTRY")) {
      return {
        heading: "Registry identity validated",
        description: "Canonical identity is validated; source ownership evidence remains incomplete. Ownership evidence and current actions are handled by the backend workflow.",
        tag: "Identity validated · partial source",
        provider,
        connection: "Successful / data retrieved",
        entity,
        issue: "Source ownership evidence incomplete",
        action: "Follow the current workflow action",
        attention: false,
        code,
        message,
      };
    }
    return {
      heading: "Registry data incomplete",
      description: "The registry connection succeeded, but expected ownership evidence was not returned. The case requires review.",
      tag: "Review required",
      provider,
      connection: entityRetrieved ? "Successful / data retrieved" : "Partial response",
      entity,
      issue: "Ownership evidence incomplete",
      action: "Review required",
      attention: true,
      code,
      message,
    };
  }

  if (code && REGISTRY_MALFORMED_CODES.has(code)) {
    return {
      heading: "Registry response could not be validated",
      description: "The provider returned a response that did not pass the bounded registry contract. No browser-side interpretation is applied.",
      tag: "Attention required",
      provider,
      connection: "Response rejected",
      entity,
      issue: "Malformed or invalid provider response",
      action: "Operator review required",
      attention: true,
      code,
      message,
    };
  }

  if (code && REGISTRY_UNAVAILABLE_CODES.has(code)) {
    return {
      heading: "Registry unavailable",
      description: "The registry provider could not complete the requested operation. No retry or source decision is invented by the browser.",
      tag: "Attention required",
      provider,
      connection: "Unavailable",
      entity,
      issue: "Provider operation unavailable",
      action: "Operator review required",
      attention: true,
      code,
      message,
    };
  }

  if (code) {
    return {
      heading: "Registry review required",
      description: "Backend registry state requires review. The browser preserves the reported code and does not infer a provider failure.",
      tag: "Review required",
      provider,
      connection: entityRetrieved ? "Successful / data retrieved" : "Not confirmed",
      entity,
      issue: "Registry review condition",
      action: "Review required",
      attention: true,
      code,
      message,
    };
  }

  return {
    heading: summary.current_stage === "REGISTRY" && summary.status === "RUNNING"
      ? "Reading the registry"
      : acquisition
        ? "Registry data acquired"
        : "Reading the registry",
    description: "Jurisdiction routing and bounded ACRA acquisition operations are reported from backend state.",
    tag: summary.status.replaceAll("_", " "),
    provider,
    connection: acquisition ? "Successful / data retrieved" : "In progress",
    entity,
    issue: "None reported",
    action: acquisition ? "Continue workflow" : "Wait for backend state",
    attention: false,
    code: null,
    message: null,
  };
}

export function RegistryStatePanel({
  summary,
  registryProviderMode,
}: {
  summary: ZeroTouchCaseSummary;
  registryProviderMode?: RegistryProviderMode;
}) {
  const resolution = summary.case.jurisdiction_resolution;
  const route = summary.case.registry_route;
  const acquisition = summary.case.registry_acquisition;
  const jurisdictionState = jurisdictionProgressState(resolution?.status);
  const routeState = registryRouteProgressState(route?.status);
  const presentation = registryPresentation(summary, registryProviderMode);

  const registryNode = (summary.processing_pipeline ?? [])
    .find((item) => item.node_id === "ACRA_REGISTRY");
  if (
    summary.current_stage !== "REGISTRY"
    && !presentation.attention
    && registryNode?.status !== "NOT_REACHED"
  ) return null;

  return (
    <section className="state-composition" aria-labelledby="registry-state-heading">
      <div className="state-composition__header">
        <div>
          <p className="card-kicker">Registry acquisition</p>
          <h2 id="registry-state-heading">{presentation.heading}</h2>
          <p className="text-muted">{presentation.description}</p>
        </div>
        <span className={presentation.attention ? "tag tag-outline" : "tag tag-accent-2"}>
          {presentation.tag}
        </span>
      </div>

      {presentation.attention && (
        <div className="ds-banner ds-banner-warn registry-stop">
          <strong>{presentation.code ?? "REGISTRY_REVIEW"}</strong>
          <span>{presentation.message ?? "Registry processing requires review in the current POC state."}</span>
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
          <div className="kv-row"><span className="kv-label">Provider</span><span className="kv-value">{presentation.provider}</span></div>
          <div className="kv-row"><span className="kv-label">Connection</span><span className="kv-value">{presentation.connection}</span></div>
          <div className="kv-row"><span className="kv-label">Entity</span><span className="kv-value">{presentation.entity}</span></div>
          <div className="kv-row"><span className="kv-label">Environment</span><span className="kv-value">{summary.case.entity?.source?.environment ?? acquisition?.operation_results.find((item) => item.provenance)?.provenance?.environment ?? "—"}</span></div>
          <div className="kv-row"><span className="kv-label">Acquisition</span><span className="kv-value">{acquisition?.status ?? "Not started"}</span></div>
          <div className="kv-row"><span className="kv-label">Issue</span><span className="kv-value">{presentation.issue}</span></div>
          <div className="kv-row"><span className="kv-label">Action</span><span className="kv-value">{presentation.action}</span></div>
          <div className="kv-row"><span className="kv-label">Access</span><span className="kv-value">Backend-managed</span></div>
          <p className="control-help">
            {registryProviderMode === "API_MARKETPLACE_PROTOCOL_TEST"
              ? "Synthetic offline protocol test evidence. No external ACRA request or network interoperability is demonstrated."
              : registryProviderMode === "API_MARKETPLACE_MOCK"
              ? "Official Marketplace Mock is non-production. Production/Live ACRA is not integrated."
              : "Provider classification follows the configured backend execution profile. Foreign providers are not implemented."}
          </p>
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
        {(["MATCH", "REGISTRY_ONLY", "CONFLICT", "MISSING_IN_SOURCE", "UNVERIFIABLE", "INVALID"] as const).map((outcome) => (
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
              {discrepancy?.status === "OPEN"
                && discrepancy.allowed_actions.length > 0
                && !onResolve && (
                <p className="control-help">
                  Use the backend-authorized Action required panel to record this decision.
                </p>
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
  const pipeline = summary.processing_pipeline ?? [];
  return (
    <section className="state-composition completed-overview" aria-labelledby="completed-heading">
      <div className="state-composition__header">
        <div>
          <p className="card-kicker">Completed POC workflow</p>
          <h2 id="completed-heading">{summary.case.entity?.legal_name ?? summary.case.requested_uen} is onboarded</h2>
          <p className="text-muted">Completed zero-touch POC workflow on {formatTimestamp(completedAt)}. This is not production approval or Ready-for-Approval.</p>
          {summary.clm?.submission_plan.environment === "SANDBOX" && (
            <p className="text-muted">GoldTier Sandbox customer/profile submission completed. Policy initiates GoldTier KYC activity where documented. This does not establish KYC completion, sanctions or PEP clearance, adverse-media clearance, risk approval, regulatory approval or Production onboarding.</p>
          )}
        </div>
      </div>
      <div className="state-grid completed-grid">
        <div className="card">
          <p className="card-kicker">Stage record</p>
          <div className="table-scroll" tabIndex={0}>
            <table className="table">
              <thead><tr><th>Stage</th><th>Outcome</th><th>Method</th><th>Cleared</th></tr></thead>
              <tbody>
                {pipeline.map((node) => (
                  <tr key={node.node_id}>
                    <td>{node.label}</td>
                    <td>{PROGRESS_STATUS_LABELS[node.status]}</td>
                    <td>Backend projection</td>
                    <td>{node.timestamp ? formatTimestamp(node.timestamp) : "—"}</td>
                  </tr>
                ))}
                {pipeline.length === 0 && (
                  <tr><td colSpan={4}>Backend pipeline not reported for this completed case.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
        <aside className="card">
          <p className="card-kicker">POC client record</p>
          <div className="kv-row"><span className="kv-label">GoldTier party ID</span><span className="kv-value">{targetId ?? "—"}</span></div>
          <div className="kv-row"><span className="kv-label">Risk rating</span><span className="kv-value">—</span></div>
          <div className="kv-row"><span className="kv-label">Next review</span><span className="kv-value">—</span></div>
          <div className="kv-row"><span className="kv-label">Human touches</span><span className="kv-value">{summary.metrics.human_interventions}</span></div>
          <div className="kv-row"><span className="kv-label">Recorded total automation duration</span><span className="kv-value">{summary.metrics.total_duration_ms === null ? "—" : formatDuration(summary.metrics.total_duration_ms)}</span></div>
          {onViewOnboarded && <button className="btn btn-secondary btn-block" type="button" onClick={() => onViewOnboarded(summary.case.case_id)}>View in Onboarded</button>}
          {onViewAudit && <button className="btn btn-secondary btn-block" type="button" onClick={() => onViewAudit(summary.case.case_id)}>View audit trail</button>}
          <button className="btn btn-secondary btn-block" type="button" disabled title="Audit export is not available in current POC">Download audit trail</button>
        </aside>
      </div>
    </section>
  );
}
