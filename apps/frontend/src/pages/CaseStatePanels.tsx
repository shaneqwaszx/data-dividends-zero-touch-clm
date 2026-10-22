import { useEffect, useId, useState, type CSSProperties, type ReactNode } from "react";

import { displayTimestamp, formatDuration, formatTimestamp, registryReuseDescription } from "../shared";
import { documentFieldKeyFor, registryChoiceFields } from "./BlockerDecisionReview";
import type {
  DocumentProcessingRecord,
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

export const GOLDTIER_DETAILS_STAGE_LABEL = "GoldTier Details & Status";
const GOLDTIER_DETAILS_NODE_IDS = ["READINESS", "GOLDTIER_TARGET"];

/**
 * Presentation: all twelve backend stages stay visible, each with its own name and status.
 * The case page groups READINESS and GOLDTIER_TARGET into one section, labelled with both stage names.
 */
export function businessStagePipeline(backendPipeline: ProcessingNode[]): ProcessingNode[] {
  return backendPipeline;
}

/** The stage names the grouped "GoldTier Details & Status" case section covers, in pipeline order. */
export function goldTierDetailsStageNames(backendPipeline: ProcessingNode[]): string[] {
  return backendPipeline.filter(node => GOLDTIER_DETAILS_NODE_IDS.includes(node.node_id)).map(node => node.label);
}

export interface StageStatus { tone: "attention" | "current" | "done" | "pending"; label: string }

/** Summarise the backend status of the pipeline nodes behind one case section. */
export function stageStatusFor(summary: ZeroTouchCaseSummary, nodeIds: string[]): StageStatus | undefined {
  const nodes = (summary.processing_pipeline ?? []).filter(node => nodeIds.includes(node.node_id));
  if (!nodes.length) return undefined;
  const attention = nodes.find(node => pipelineRailState(node.status) === "attention");
  if (attention) return { tone: "attention", label: PROGRESS_STATUS_LABELS[attention.status] };
  const current = nodes.find(node => node.status === "IN_PROGRESS");
  if (current) return { tone: "current", label: PROGRESS_STATUS_LABELS[current.status] };
  if (nodes.every(node => pipelineRailState(node.status) === "done")) return { tone: "done", label: PROGRESS_STATUS_LABELS[nodes[0].status] };
  return { tone: "pending", label: PROGRESS_STATUS_LABELS[nodes.find(node => pipelineRailState(node.status) !== "done")!.status] };
}

export function PipelineRail({ summary, onStageActivate, renderAttention }: {
  summary: ZeroTouchCaseSummary; onStageActivate?: (node: ProcessingNode) => void;
  /** Optional per-step content, rendered after the step status. */
  renderAttention?: (node: ProcessingNode) => ReactNode;
}) {
  const pipeline = businessStagePipeline(summary.processing_pipeline ?? []);
  return (
    <div className="ds-stage-rail" aria-label="Backend workflow stages">
      {pipeline.map((node, index) => {
        const state = pipelineRailState(node.status);
        return (
          <div className="ds-stage" key={node.node_id} data-node-id={node.node_id} data-status={node.status}>
            <div className="ds-stage-marker">
              <span className={`ds-stage-node ${state}`}>
                {state === "done" ? "✓" : index + 1}
              </span>
              {index < pipeline.length - 1 && (
                <span className={`ds-stage-line ${state === "done" ? "done" : ""}`} />
              )}
            </div>
            <div className="ds-stage-copy">
              <details>
                <summary>{node.label}</summary>
                <ProcessingStageFacts node={node} />
                {onStageActivate && <button type="button" className="btn btn-ghost" onClick={() => onStageActivate(node)}>Open case stage details</button>}
              </details>
              {node.node_id === "ADVISORY" && <p className="control-help">Bounded POC advisory</p>}
              <div className="text-muted">{PROGRESS_STATUS_LABELS[node.status]}</div>
              {renderAttention?.(node)}
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
  if (nodeId === "FINAL_REVIEW_SEND") return node.status === "REVIEW_REQUIRED" ? "case-review-and-send" : "case-target-blocker";
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

function ProcessingExplanation({ node, children, showCode = true }: { node: ProcessingNode; children: string; showCode?: boolean }) {
  return (
    <>
      <p><strong>Status:</strong> {PROGRESS_STATUS_LABELS[node.status]}</p>
      {showCode && node.blocker_code && <p><strong>Safe blocker code:</strong> {node.blocker_code}</p>}
      {node.safe_result && <p>{node.safe_result}</p>}
      <p className="control-help">{children}</p>
    </>
  );
}

export function ProcessingBlockerPanels({ summary, stage, searchPart = "all" }: {
  summary: ZeroTouchCaseSummary; stage?: "REGISTRY" | "TARGET"; searchPart?: "all" | "main" | "more" | "technical";
}) {
  const pipeline = summary.processing_pipeline ?? [];
  const search = findProcessingNode(pipeline, "GOLDTIER_SEARCH");
  const finalReview = findProcessingNode(pipeline, "FINAL_REVIEW_SEND");
  const target = finalReview && NAVIGABLE_PROCESSING_STATUSES.has(finalReview.status)
    ? finalReview : findProcessingNode(pipeline, "GOLDTIER_TARGET");

  const searchWarning = "A failed Search does not prove that the customer is absent. A bounded read-only Search recheck may be available through Registry identity under the current case state. Target mutation remains prohibited until authoritative prerequisites are met. A recheck confirms identity only when its result satisfies the existing resolver rules.";
  if (searchPart === "main") return search && NAVIGABLE_PROCESSING_STATUSES.has(search.status) ? <div className="ds-banner ds-banner-warn">
    <strong>Search: {PROGRESS_STATUS_LABELS[search.status]}</strong>
    {search.safe_result && <p>{search.safe_result}</p>}
    <p className="control-help">{searchWarning}</p>
  </div> : summary.clm.target_search_checkpoint?.status === "FAILED" ? <p className="control-help">{searchWarning}</p> : null;
  if (searchPart === "more") return search?.children.length ? <ol aria-label="Retained Search result steps">{search.children.map(child => <ProcessingPipelineNodeView key={child.node_id} node={child} businessOnly />)}</ol> : null;

  return (
    <>
      {stage !== "TARGET" && search && NAVIGABLE_PROCESSING_STATUSES.has(search.status) && (
        <section id="case-search-diagnostic" className="card evidence-focus-target" tabIndex={-1} aria-labelledby="case-search-diagnostic-heading">
          <p className="card-kicker">Read-only diagnostic</p>
          <h2 id="case-search-diagnostic-heading">GoldTier Search</h2>
          <ProcessingExplanation node={search}>{searchWarning}</ProcessingExplanation>
          {searchPart === "technical" && <dl>
            <div><dt>Processing node</dt><dd>{search.node_id}</dd></div>
            <div><dt>Backend stage</dt><dd>{search.backend_stage ?? "Not recorded"}</dd></div>
            <div><dt>Operation</dt><dd>{search.operation ?? "Not recorded"}</dd></div>
            <div><dt>Provider</dt><dd>{search.provider ?? "Not recorded"} · {search.environment ?? "Not recorded"}</dd></div>
            <div><dt>Recorded at</dt><dd>{displayTimestamp(search.timestamp)}</dd></div>
            <div><dt>Record count</dt><dd>{search.record_count ?? "Not recorded"}</dd></div>
          </dl>}
          {searchPart === "technical" && search.children.length > 0 && <ol aria-label="Search operation details">{search.children.map(child => <ProcessingPipelineNodeView key={child.node_id} node={child} />)}</ol>}
        </section>
      )}
      {stage !== "REGISTRY" && target && NAVIGABLE_PROCESSING_STATUSES.has(target.status) && (
        <section id="case-target-blocker" className="card evidence-focus-target" tabIndex={-1} aria-labelledby="case-target-blocker-heading">
          <p className="card-kicker">Target safety boundary</p>
          <h2 id="case-target-blocker-heading">GoldTier target operations</h2>
          <ProcessingExplanation node={target} showCode={false}>
            The retained target ledger controls each operation and stops unsafe downstream work. This explanation does not provide a bypass or replay action.
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
  initialFocusNodeId,
}: {
  summary: ZeroTouchCaseSummary;
  onStageActivate?: (node: ProcessingNode) => void;
  availableFocusTargets?: ReadonlySet<string>;
  initialFocusNodeId?: string;
}) {
  const backendPipeline = summary.processing_pipeline ?? [];
  const retainedPipeline = businessStagePipeline(backendPipeline);
  const [inspected, setInspected] = useState<{ caseId: string; nodeId: string } | null>(null);
  useEffect(() => {
    if (initialFocusNodeId) setInspected({ caseId: summary.case.case_id, nodeId: initialFocusNodeId });
  }, [initialFocusNodeId, summary.case.case_id]);
  const identityIncomplete = summary.active_exceptions.some(
    (exception) => exception.blocker_code === "INITIAL_IDENTITY_INCOMPLETE",
  );
  const hasTopLevelIdentity = retainedPipeline.some((node) => node.node_id === "INITIAL_IDENTITY");
  const identityCorrectionNode: ProcessingNode = {
        node_id: "INITIAL_IDENTITY",
        label: "Initial identity",
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
  const inspectedNode = inspected?.caseId === summary.case.case_id
    ? findProcessingNode(pipeline, inspected.nodeId) ?? findProcessingNode(backendPipeline, inspected.nodeId)
    : null;
  const completed = pipeline.filter((node) =>
    node.status === "COMPLETE" || node.status === "EMPTY" || node.status === "SKIPPED"
  ).length;
  const current = currentProcessingNode(pipeline);
  const maximum = Math.max(pipeline.length, 1);
  const percentage = summary.status === "COMPLETED" ? 100 : Math.round((completed / maximum) * 100);
  const activeIssues = summary.status === "COMPLETED" ? 0 : summary.active_exceptions.filter(
    (item) => item.exception_type !== "TARGET_CONFIRMATION_REQUIRED",
  ).length + (summary.technical_failure ? 1 : 0);
  const finalConfirmationOnly = activeIssues === 0 && summary.current_stage === "READINESS"
    && summary.active_exceptions.some((item) => item.exception_type === "TARGET_CONFIRMATION_REQUIRED");
  const nextAction = summary.status === "COMPLETED" ? "Submitted — no action required."
    : finalConfirmationOnly ? "Review and confirm submission"
    : summary.interventions?.[0]?.evidence_actions?.[0]?.label
      ?? summary.interventions?.[0]?.expected_next_step
      ?? (summary.status === "PENDING_INPUTS" ? "Provide the required documents."
        : summary.status === "TECHNICAL_FAILURE"
          ? (summary.current_stage === "REGISTRY" ? "Review registry identity and edit the UEN."
            : "Review the stopped stage.")
          : "Wait for the current backend stage.");
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
        <p className="onboarding-progress__percent" aria-hidden="true">
          <strong>{percentage}%</strong>
          <span>{completed} of {pipeline.length} stages done</span>
        </p>
      </div>
      <div
        className="onboarding-progress__bar"
        role="progressbar"
        aria-labelledby="onboarding-progress-heading"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percentage}
        aria-valuetext={summary.status === "COMPLETED"
          ? "100% — reviewed POC submission complete; retained target outcome remains authoritative."
          : `${percentage}%; ${completed} of ${pipeline.length} stages complete or skipped; current: ${currentText}`}
      >
        <span style={{ "--onboarding-progress": `${percentage}%` } as CSSProperties} />
      </div>
      {/* Visible labels drop the colon; the hidden text keeps "Label: value" for assistive tech. */}
      <dl className="onboarding-progress__facts">
        <div className="onboarding-progress__current"><dt>Current<span className="sr-only">: </span></dt><dd>{currentText}</dd></div>
        <div className={activeIssues ? "is-attention" : undefined}><dt>Active issues<span className="sr-only">: </span></dt><dd>{activeIssues}</dd></div>
        <div><dt>Next action<span className="sr-only">: </span></dt><dd>{nextAction}</dd></div>
      </dl>
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
              {node.node_id === "ADVISORY" && <span className="control-help">Bounded POC advisory</span>}
              <span className="onboarding-progress__stage-action">{navigable && node.status === "REVIEW_REQUIRED" ? "Review" : navigable && ["BLOCKED", "FAILED"].includes(node.status) ? "Resolve issue" : "View details"}</span>
            </>;
            return (
              <li
                key={node.node_id}
                className="onboarding-progress__stage onboarding-progress__stage--actionable"
                data-status={node.status}
              >
                <button type="button" onClick={() => {
                  setInspected({ caseId: summary.case.case_id, nodeId: node.node_id });
                  if (navigable) onStageActivate?.(node);
                }} aria-label={`Open details for ${node.label}`} aria-expanded={inspectedNode?.node_id === node.node_id} aria-controls="processing-stage-details">
                  {content}
                </button>
              </li>
            );
          })}
        </ol>
      ) : (
        <p className="empty-copy">The backend has not reported a processing route yet.</p>
      )}
      {/* Collapsed by default; a new stage starts collapsed again (keyed by node). */}
      {inspectedNode && <details key={inspectedNode.node_id} id="processing-stage-details" className="card evidence-focus-target stage-details" tabIndex={-1} aria-label={`${inspectedNode.label} details`}>
        <summary>Stage details — {inspectedNode.label}</summary>
        <ProcessingStageFacts node={inspectedNode} nextAction={summary.interventions?.find((item) => (
          NAVIGABLE_PROCESSING_STATUSES.has(inspectedNode.status) && (
            (inspectedNode.blocker_code && item.blocker_code === inspectedNode.blocker_code)
            || (inspectedNode.backend_stage && item.owning_stage === inspectedNode.backend_stage)
          )
        ))?.expected_next_step} />
        {inspectedNode.children.length > 0 && <ol>{inspectedNode.children.map((child) => <ProcessingPipelineNodeView key={child.node_id} node={child} />)}</ol>}
      </details>}
      <p className="onboarding-progress__updated"><strong>Last updated:</strong> {formatTimestamp(summary.updated_at)}</p>
    </section>
  );
}

function ProcessingStageFacts({ node, nextAction }: { node: ProcessingNode; nextAction?: string }) {
  return <>
    <p><strong>Status:</strong> {PROGRESS_STATUS_LABELS[node.status]}</p>
    {node.safe_result ? <p><strong>Outcome:</strong> {node.safe_result}</p> : <p className="control-help">The backend has not reported an outcome or explanation for this stage.</p>}
    {node.provider && <p><strong>Provider:</strong> {node.provider}</p>}
    {node.environment && <p><strong>Environment:</strong> {node.environment}</p>}
    {node.operation && <p><strong>Operation:</strong> {node.operation.replaceAll("_", " ")}</p>}
    {node.timestamp && <p><strong>Recorded at:</strong> {formatTimestamp(node.timestamp)}</p>}
    {node.blocker_code && <p><strong>Blocker:</strong> {node.blocker_code}</p>}
    {nextAction && <p><strong>Required next action:</strong> {nextAction}</p>}
    {node.record_count != null && <p><strong>Records:</strong> {node.record_count}</p>}
    {node.retained_goldtier_id && <p><strong>Retained GoldTier ID:</strong> {node.retained_goldtier_id}</p>}
    {node.node_id === "ADVISORY" && <p className="control-help">Bounded POC advisory assessment; not production AML/KYC risk.</p>}
  </>;
}

function processingStatusLabel(status: ProcessingNodeStatus): string {
  return status.replaceAll("_", " ");
}

function ProcessingPipelineNodeView({ node, businessOnly = false }: { node: ProcessingNode; businessOnly?: boolean }) {
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
  ].filter((item): item is { label: string; value: string } => Boolean(item))
    .filter(item => !businessOnly || item.label === "Record count");

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
            <ProcessingPipelineNodeView key={child.node_id} node={child} businessOnly={businessOnly} />
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
  const registryTechnicalFailure = summary.current_stage === "REGISTRY"
    ? summary.technical_failure
    : null;
  const code = registryException?.blocker_code
    ?? registryTechnicalFailure?.code
    ?? issue?.code
    ?? operationError?.code
    ?? routeCode
    ?? jurisdictionCode;
  const message = registryException?.explanation
    ?? registryTechnicalFailure?.message
    ?? issue?.message
    ?? operationError?.message
    ?? (jurisdictionCode ? "Jurisdiction must be resolved before a registry route can be selected." : null);
  const provider = registryProviderLabel(providerMode, summary.case.registry_route?.provider ?? undefined);
  const entity = summary.case.entity?.legal_name ?? "Not retrieved";
  const entityRetrieved = Boolean(summary.case.entity)
    || acquisition?.operation_results.some(
      (operation) => operation.operation === "ENTITY_PROFILE" && operation.status === "COMPLETE",
    ) === true;

  if (!registryException && !registryTechnicalFailure
    && summary.case.registry_evidence_binding?.disposition === "CACHE_HIT") {
    return {
      heading: "Registry evidence reused",
      description: registryReuseDescription(acquisition, summary.case.registry_evidence_binding),
      tag: "CACHE_HIT",
      provider,
      connection: "No ACRA request required",
      entity,
      issue: "None reported",
      action: "Continue workflow",
      attention: false,
      code: null,
      message: null,
    };
  }

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

  if (registryTechnicalFailure) {
    return {
      heading: "Registry technical failure",
      description: "Registry processing stopped after a technical failure reported by the backend.",
      tag: "Technical failure",
      provider,
      connection: "Not confirmed",
      entity,
      issue: "Registry technical failure",
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
    tag: acquisition?.status ?? registryNode?.status ?? "Not reached",
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
  compact = false,
}: {
  summary: ZeroTouchCaseSummary;
  registryProviderMode?: RegistryProviderMode;
  compact?: boolean;
}) {
  const resolution = summary.case.jurisdiction_resolution;
  const route = summary.case.registry_route;
  const acquisition = summary.case.registry_acquisition;
  const jurisdictionState = jurisdictionProgressState(resolution?.status);
  const routeState = registryRouteProgressState(route?.status);
  const presentation = registryPresentation(summary, registryProviderMode);
  const identityCompleteness = resolution?.status === "CONFLICT"
    ? "CONFLICTING"
    : summary.case.entity
      ? "AVAILABLE"
      : presentation.attention
        ? "REQUIRED_BUT_UNAVAILABLE"
        : "MISSING";

  const registryNode = (summary.processing_pipeline ?? []).find(item => item.node_id === "ACRA_REGISTRY");
  const showState = summary.current_stage === "REGISTRY" || presentation.attention || registryNode?.status === "NOT_REACHED";
  if (!compact && !showState) return null;

  return (
    <section className="state-composition" aria-label={compact && !showState ? "Retained registry state" : undefined} aria-labelledby={showState ? "registry-state-heading" : undefined}>
      <div className="state-composition__header">
        <div>
          <p className="card-kicker">Registry acquisition</p>
          {showState ? <h2 id="registry-state-heading">{presentation.heading}</h2> : <h3>Retained registry state</h3>}
          <p className="text-muted">{showState ? presentation.description : acquisition ? presentation.description : "Registry acquisition is not retained. Completion and provider activity cannot be inferred."}</p>
        </div>
        <span className={presentation.attention ? "tag tag-outline" : "tag tag-accent-2"}>
          {!showState && !acquisition ? registryNode?.status ?? "Not recorded" : presentation.tag}
        </span>
      </div>

      {presentation.attention && (
        <div className="ds-banner ds-banner-warn registry-stop">
          <strong>{presentation.code ?? "REGISTRY_REVIEW"}</strong>
          <span>{presentation.message ?? "Registry processing requires review in the current POC state."}</span>
        </div>
      )}

      <div className="state-grid state-grid--registry">
        {!compact && <div className="card progress-card">
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
                    {operation.status === "UNSUPPORTED" ? " · Connector capability not implemented; no provider call occurred. Case evidence completeness is evaluated separately." : ""}
                    {operation.provenance ? ` · ${operation.provenance.provider} ${operation.provenance.environment}` : ""}
                  </span>
                </li>
              );
            })}
          </ol>
        </div>}
        <aside className="card registry-policy-card">
          <p className="card-kicker">Registry boundary</p>
          <div className="kv-row"><span className="kv-label">This case's registry identity evidence</span><span className="kv-value">{identityCompleteness}</span></div>
          <p className="control-help">This describes retained case identity and its backend blocker. Unsupported connector operations describe capability limits separately.</p>
          <div className="kv-row"><span className="kv-label">Jurisdiction</span><span className="kv-value">{resolution?.resolved_jurisdiction ?? "Not resolved"} · {resolution?.status ?? "Not evaluated"}</span></div>
          <div className="kv-row"><span className="kv-label">Registry route</span><span className="kv-value">{route?.status ?? "Not selected"} · {route?.provider ?? "No provider"} · {route?.jurisdiction ?? "Not recorded"}</span></div>
          <div className="kv-row"><span className="kv-label">{compact ? "Configured provider" : "Provider"}</span><span className="kv-value">{presentation.provider}</span></div>
          <div className="kv-row"><span className="kv-label">Connection</span><span className="kv-value">{!showState && !acquisition ? "Not recorded" : presentation.connection}</span></div>
          <div className="kv-row"><span className="kv-label">Entity</span><span className="kv-value">{presentation.entity}</span></div>
          <div className="kv-row"><span className="kv-label">Environment</span><span className="kv-value">{summary.case.entity?.source?.environment ?? acquisition?.operation_results.find((item) => item.provenance)?.provenance?.environment ?? "—"}</span></div>
          <div className="kv-row"><span className="kv-label">Acquisition</span><span className="kv-value">{acquisition?.status ?? "Not recorded"}</span></div>
          <div className="kv-row"><span className="kv-label">Issue</span><span className="kv-value">{presentation.issue}</span></div>
          <div className="kv-row"><span className="kv-label">Action</span><span className="kv-value">{!showState && !acquisition ? "Follow the current backend workflow action" : presentation.action}</span></div>
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
  presentation = "full",
  isBusy = false,
  onResolve,
  embedded = false,
  documents,
}: {
  summary: ZeroTouchCaseSummary;
  /** Current document records: the document's own read value, confidence and the reviewer's choice. */
  documents?: DocumentProcessingRecord[];
  isBusy?: boolean;
  presentation?: "full" | "main" | "technical";
  /** Rendered inside the combined document card, which supplies the heading. */
  embedded?: boolean;
  onResolve?: (discrepancy: ReconciliationDiscrepancy, action: ReconciliationDecisionAction) => void;
}) {
  const reconciliation = summary.reconciliation;
  // Embedded in the document card, the comparison (and the reviewer's choice) stays visible after the document stage.
  if (!reconciliation || (presentation !== "technical" && !embedded && summary.current_stage !== "DOCUMENT")) return null;
  const discrepancies = new Map(reconciliation.discrepancies.map((item) => [item.discrepancy_id, item]));
  if (presentation === "technical") return <section aria-label="Reconciliation provenance">
    <h3>Reconciliation provenance</h3>
    <dl className="document-field__evidence">
      <div><dt>Reconciliation status / version</dt><dd>{reconciliation.status} / {reconciliation.version}</dd></div>
      <div><dt>Reconciliation reference</dt><dd>{reconciliation.reconciliation_id}</dd></div>
      <div><dt>Updated at</dt><dd>{displayTimestamp(reconciliation.updated_at)}</dd></div>
      <div><dt>Source document bindings</dt><dd>{reconciliation.source_document_ids.map((id, index) => `${id} · event count ${reconciliation.source_document_event_counts[index] ?? "Not recorded"}`).join("; ") || "None recorded"}</dd></div>
    </dl>
    {reconciliation.fields.map(field => <section key={field.field_name}>
      <h4>{field.field_name.replaceAll("_", " ")} · {field.outcome}</h4>
      {field.observations.map(observation => <p key={observation.observation_id}>{observation.source_kind} · {observation.source_system ?? "—"} {observation.environment ?? "—"} · {observation.evidence_reference ?? "safe reference unavailable"}</p>)}
      <p>Decision: {field.discrepancy_id ? discrepancies.get(field.discrepancy_id)?.decision?.action ?? discrepancies.get(field.discrepancy_id)?.status ?? "Not required" : "Not required"}</p>
    </section>)}
  </section>;
  const outcomes = (["MATCH", "REGISTRY_ONLY", "CONFLICT", "MISSING_IN_SOURCE", "UNVERIFIABLE", "INVALID"] as const)
    .map((outcome) => ({ outcome, count: reconciliation.fields.filter((field) => field.outcome === outcome).length }))
    .filter((item) => item.count > 0);
  const openDiscrepancies = reconciliation.fields
    .map((field) => (field.discrepancy_id ? discrepancies.get(field.discrepancy_id) : undefined))
    .filter((item): item is ReconciliationDiscrepancy => item?.status === "OPEN");
  const replacementNeeded = openDiscrepancies.filter((item) => item.allowed_actions.length === 0).length;
  const documentRecords = (documents ?? []).filter((item) => item.superseded_by_document_id == null);
  const intents = registryChoiceFields(summary.case.case_id);
  const decisionElsewhere = !onResolve && openDiscrepancies.some((item) => item.allowed_actions.length > 0);
  return (
    <section className={`state-composition confirm-details${embedded ? " confirm-details--embedded" : ""}`} aria-labelledby={embedded ? undefined : "confirm-details-heading"} aria-label={embedded ? "Registry and document comparison" : undefined}>
      <div className="state-composition__header">
        {!embedded && <div>
          <p className="card-kicker">Source-neutral reconciliation</p>
          <h2 id="confirm-details-heading">Confirm details</h2>
          <p className="text-muted">Registry and document values side by side. No source wins automatically.</p>
        </div>}
        <div className="confirm-details__meta">
          <div className="reconciliation-summary" aria-label="Reconciliation outcomes">
            {outcomes.map(({ outcome, count }) => (
              <span className={`confirm-outcome outcome-${outcome.toLowerCase()}`} key={outcome}>
                <strong>{count}</strong> {outcome.replaceAll("_", " ").toLowerCase()}
              </span>
            ))}
          </div>
          <span className="tag tag-accent-2">{reconciliation.status.replaceAll("_", " ")}</span>
        </div>
      </div>
      <div className="confirm-table" role="table" aria-label="Registry and document comparison">
        <div className="confirm-table__row confirm-table__head" role="row">
          <span role="columnheader">Field</span><span role="columnheader">Registry value</span>
          <span role="columnheader">Document value</span><span role="columnheader">Your choice</span>
        </div>
        {reconciliation.fields.map((field) => {
          const discrepancy = field.discrepancy_id ? discrepancies.get(field.discrepancy_id) : undefined;
          const registry = field.observations.filter((item) => item.source_kind === "REGISTRY");
          const documents = field.observations.filter((item) => item.source_kind === "DOCUMENT_IDP");
          const documentField = currentDocumentField(documentRecords, field.field_name);
          const decided = reconciliation.discrepancies.find((item) => item.field_name === field.field_name && item.decision)?.decision?.action;
          const choice = reviewerChoice(documentField, decided, intents.has(documentFieldKeyFor(field.field_name)));
          const chosen = choiceKind(choice);
          const actions = discrepancy?.status === "OPEN" && discrepancy.allowed_actions.length > 0 && onResolve;
          return (
            <div className={`confirm-table__row outcome-${field.outcome.toLowerCase()}`} role="row" key={field.field_name}>
              <span role="cell" className="confirm-table__field">{field.field_name.replaceAll("_", " ")}</span>
              <span role="cell" data-label="Registry value" className={chosen === "registry" ? "is-chosen" : undefined}><ObservationValue observations={registry} /></span>
              {/* The document's own read value stays visible even after a review decision changes the comparison. */}
              <span role="cell" data-label="Document value" className={chosen === "document" ? "is-chosen" : undefined}>{documentField?.original_extracted_value != null
                ? <span className="confirm-value">{documentField.original_extracted_value}{documentField.confidence != null && <small> · {Math.round(documentField.confidence * 100)}% confidence</small>}</span>
                : <ObservationValue observations={documents} showConfidence />}</span>
              <span role="cell" data-label="Your choice" className={chosen === "manual" ? "is-chosen" : undefined}>
                <strong className="confirm-choice">{choice}</strong>
                {decided
                  ? <span className="confirm-outcome outcome-match">resolved</span>
                  : <span className={`confirm-outcome outcome-${field.outcome.toLowerCase()}`}>{field.outcome.replaceAll("_", " ").toLowerCase()}</span>}
                {discrepancy?.status === "OPEN" && discrepancy.allowed_actions.length === 0 && <small className="confirm-table__note">Needs replacement evidence</small>}
              </span>
              {(actions || presentation === "full") && <div className="confirm-table__extra">
                {actions && <div className="comparison-actions">
                  {discrepancy.allowed_actions.map((action) => (
                    <button className="btn btn-primary" type="button" disabled={isBusy} key={action} onClick={() => onResolve(discrepancy, action)}>
                      {action === "KEEP_REGISTRY_VALUE" ? "Keep registry value" : "Use document value"}
                    </button>
                  ))}
                </div>}
                {presentation === "full" && <details>
                  <summary>Provenance and decision state</summary>
                  {field.observations.map((observation) => (
                    <p key={observation.observation_id}>
                      {observation.source_kind} · {observation.source_system ?? "—"} {observation.environment ?? "—"} · {observation.evidence_reference ?? "safe reference unavailable"}
                    </p>
                  ))}
                  <p>Decision: {discrepancy?.decision?.action.replaceAll("_", " ") ?? discrepancy?.status ?? "Not required"}</p>
                </details>}
              </div>}
            </div>
          );
        })}
      </div>
      {(replacementNeeded > 0 || decisionElsewhere) && <div className="confirm-details__notes">
        {replacementNeeded > 0 && <p className="control-help">Replacement evidence is required for {replacementNeeded} field{replacementNeeded === 1 ? "" : "s"}; no value-selection action is allowed.</p>}
        {decisionElsewhere && <p className="control-help">Record each decision with the actions in this section.</p>}
      </div>}
    </section>
  );
}

function currentDocumentField(records: DocumentProcessingRecord[], reconciliationField: string) {
  const key = documentFieldKeyFor(reconciliationField);
  for (const record of records) {
    const match = record.fields.find((item) => item.field_key === key);
    if (match) return match;
  }
  return undefined;
}

/**
 * What the reviewer selected, in their terms: registry value, document value, or manual input.
 * A backend REJECTED field review is shown as the rejected suggestion it is.
 */
function reviewerChoice(
  documentField: DocumentProcessingRecord["fields"][number] | undefined,
  decided: ReconciliationDecisionAction | undefined,
  registryIntent: boolean,
): string {
  if (decided === "KEEP_REGISTRY_VALUE") return "Registry value";
  if (decided === "USE_DOCUMENT_VALUE") return "Document value";
  if (!documentField) return "—";
  if (documentField.review_status === "CORRECTED") return `Manual input: ${documentField.reviewed_value ?? "—"}`;
  if (documentField.review_status === "REJECTED") return "Suggestion rejected";
  if (documentField.review_status === "ACCEPTED") return registryIntent ? "Registry value" : "Document value";
  return "Not chosen yet";
}

/** Which column holds the reviewer's chosen value, for highlighting. */
function choiceKind(choice: string): "registry" | "document" | "manual" | null {
  if (choice === "Registry value") return "registry";
  if (choice === "Document value") return "document";
  return choice.startsWith("Manual input") ? "manual" : null;
}

/** One source's value for a field; validity is shown only when it is not VALID. */
function ObservationValue({ observations, showConfidence = false }: { observations: ReconciliationObservation[]; showConfidence?: boolean }) {
  if (!observations.length) return <span className="confirm-value is-empty">Not observed</span>;
  return <>{observations.map((observation) => {
    const valid = observation.validity === "VALID";
    return <span className={`confirm-value${valid ? "" : " is-empty"}`} key={observation.observation_id}>
      {observation.normalized_value ?? (valid ? "—" : observation.validity.toLowerCase())}
      {observation.normalized_value != null && !valid && <small> · {observation.validity.toLowerCase()}</small>}
      {showConfidence && valid && observation.confidence !== null && <small> · {Math.round(observation.confidence * 100)}% confidence</small>}
    </span>;
  })}</>;
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
