import { useId, useState } from "react";

import type { HumanInterventionProjection, ProcessingNode, ZeroTouchCaseSummary, ZeroTouchException } from "../types";
import { businessStageIdFor, PipelineRail } from "./CaseStatePanels";

export type AttentionDestination =
  | { kind: "exception"; exception: ZeroTouchException }
  | { kind: "evidence"; target: NonNullable<HumanInterventionProjection["evidence_actions"]>[number]["target"] }
  | { kind: "technical" }
  | { kind: "intervention"; interventionId: string }
  | { kind: "final" };

interface AttentionItem { exception?: ZeroTouchException; intervention?: HumanInterventionProjection }
type Navigate = (destination: AttentionDestination) => void;

function isFinal(item: AttentionItem) {
  return item.exception?.exception_type === "TARGET_CONFIRMATION_REQUIRED"
    || item.intervention?.blocker_code === "TARGET_CONFIRMATION_REQUIRED";
}

/** Backend exception/projection union; the projection ID is the exception ID for linked records. */
function attentionModel(summary: ZeroTouchCaseSummary) {
  const active = summary.active_exceptions.filter(item => item.status === "OPEN");
  const exceptionIds = new Set(summary.active_exceptions.map(item => item.exception_id));
  const interventions = summary.interventions ?? [];
  // Codes are not identities.
  const items: AttentionItem[] = [
    ...active.map(exception => ({ exception, intervention: interventions.find(item => item.intervention_id === exception.exception_id) })),
    ...interventions.filter(item => !exceptionIds.has(item.intervention_id)).map(intervention => ({ intervention })),
  ];
  const blockers = items.filter(item => !isFinal(item) && item.intervention?.blocker_class !== "WARNING");
  const technical = summary.technical_failure;
  const intakePending = summary.status === "PENDING_INPUTS" && summary.current_stage === "DOCUMENT"
    && !items.some(item => (item.exception?.stage ?? item.intervention?.owning_stage) === "DOCUMENT");
  return { items, blockers, technical, intakePending, blockerCount: blockers.length + (technical ? 1 : 0) };
}

function AttentionButtons({ item, onNavigate }: { item: AttentionItem; onNavigate: Navigate }) {
  const { exception, intervention } = item;
  const primaryAction = intervention?.evidence_actions?.[0];
  return <>
    <button type="button" className="btn btn-ghost" onClick={() => onNavigate(isFinal(item) ? { kind: "final" }
      : exception ? { kind: "exception", exception }
      : primaryAction ? { kind: "evidence", target: primaryAction.target }
      : { kind: "intervention", interventionId: intervention!.intervention_id })}>
      {isFinal(item) ? "Action: Review and send" : `${intervention?.blocker_class === "WARNING" ? "Attention" : "Blocker"}: ${intervention?.title ?? exception!.blocker_code.replaceAll("_", " ")}`}
    </button>
    {intervention?.evidence_actions?.filter(action => action.target !== "REVIEW_SEND" || !isFinal(item)).map(action => <button type="button" className="btn btn-ghost" key={action.target} onClick={() => onNavigate({ kind: "evidence", target: action.target })}>Action: {action.label}</button>)}
  </>;
}

/**
 * One row per item: the problem, with its fix underneath. A single click goes to the
 * item's most specific destination; any further backend actions stay as extra links.
 */
function AttentionLine({ item, onNavigate }: { item: AttentionItem; onNavigate: Navigate }) {
  const { exception, intervention } = item;
  const final = isFinal(item);
  const actions = intervention?.evidence_actions?.filter(action => action.target !== "REVIEW_SEND" || !final) ?? [];
  const kind = final ? "Action" : intervention?.blocker_class === "WARNING" ? "Attention" : "Blocker";
  const title = final ? "Review and send" : intervention?.title ?? exception!.blocker_code.replaceAll("_", " ");
  const fix = final ? undefined : actions[0];
  // Name the field(s) the backend exception is about, so similar rows stay distinguishable.
  const fields = [...new Set((exception?.evidence ?? []).map(entry => entry.field_key).filter((key): key is string => Boolean(key)))]
    .map(key => key.replaceAll("_", " ")).join(", ");
  // The field list is shown and announced as a description, so the accessible name stays "<kind>: <title>".
  const fieldId = useId();
  return <>
    <button type="button" className={`btn btn-ghost attention-line attention-line--${kind.toLowerCase()}`} aria-describedby={fields ? fieldId : undefined} onClick={() => onNavigate(final ? { kind: "final" }
      : exception ? { kind: "exception", exception }
      : fix ? { kind: "evidence", target: fix.target }
      : { kind: "intervention", interventionId: intervention!.intervention_id })}>
      <span className="sr-only">{kind}: </span>
      <span className="attention-line__title">{title}</span>
      {fields && <span id={fieldId} className="attention-line__field" aria-hidden="true">{fields}</span>}
      {fix && <span className="attention-line__fix">{fix.label} →</span>}
    </button>
    {actions.slice(fix ? 1 : 0).map(action => <button type="button" className="btn btn-ghost attention-line__extra" key={action.target} onClick={() => onNavigate({ kind: "evidence", target: action.target })}>Action: {action.label}</button>)}
  </>;
}

function itemKey(item: AttentionItem) { return item.exception?.exception_id ?? item.intervention!.intervention_id; }
function countLabel(count: number) { return `${count} active blocker${count === 1 ? "" : "s"}`; }

export default function CaseAttentionSummary({ summary, onNavigate }: {
  summary: ZeroTouchCaseSummary; onNavigate: Navigate;
}) {
  const { items, blockers, technical, intakePending, blockerCount } = attentionModel(summary);
  return <section className="case-attention" aria-label="Attention required">
    <h4>Attention required</h4>
    <p>{countLabel(blockerCount)}</p>
    {!blockers.length && !technical && <p className="text-muted">No immediate blockers</p>}
    <ul>
      {items.map(item => <li key={itemKey(item)}><AttentionButtons item={item} onNavigate={onNavigate} /></li>)}
      {intakePending && <li><button type="button" className="btn btn-ghost" onClick={() => onNavigate({ kind: "evidence", target: "DOCUMENTS" })}>Action: Complete document intake</button></li>}
      {technical && <li><button type="button" className="btn btn-ghost" onClick={() => onNavigate({ kind: "technical" })}>Technical failure: {technical.code}</button></li>}
    </ul>
  </section>;
}

/**
 * Pipeline steps with their attention items nested underneath. Each step's items
 * collapse independently; items that belong to no step stay visible at the top.
 */
export function CasePipelineAttention({ summary, onNavigate, onStageActivate }: {
  summary: ZeroTouchCaseSummary; onNavigate: Navigate; onStageActivate?: (node: ProcessingNode) => void;
}) {
  const { items, blockers, technical, intakePending, blockerCount } = attentionModel(summary);
  const listId = useId();
  const [open, setOpen] = useState<Set<string>>(new Set());
  const pipeline = summary.processing_pipeline ?? [];
  // Place each item on the first step owning its backend stage, preferring a step that needs attention;
  // a backend stage shown inside a grouped business step places its items on that step.
  function nodeFor(stage: string | undefined) {
    const owners = pipeline.filter(node => node.backend_stage === stage);
    const owner = (owners.find(node => ["REVIEW_REQUIRED", "BLOCKED", "FAILED"].includes(node.status)) ?? owners[0])?.node_id;
    return owner && businessStageIdFor(owner);
  }
  const grouped = new Map<string, AttentionItem[]>();
  const general: AttentionItem[] = [];
  for (const item of items) {
    const nodeId = nodeFor(item.exception?.stage ?? item.intervention?.owning_stage);
    if (nodeId) grouped.set(nodeId, [...(grouped.get(nodeId) ?? []), item]);
    else general.push(item);
  }
  const intakeNode = intakePending ? nodeFor("DOCUMENT") : undefined;
  const groupIds = [...grouped.keys(), ...(intakeNode && !grouped.has(intakeNode) ? [intakeNode] : [])];
  const allOpen = groupIds.length > 0 && groupIds.every(id => open.has(id));
  const toggle = (nodeId: string) => setOpen(current => {
    const next = new Set(current);
    if (next.has(nodeId)) next.delete(nodeId); else next.add(nodeId);
    return next;
  });

  function renderAttention(node: ProcessingNode) {
    const nodeItems = grouped.get(node.node_id) ?? [];
    const intake = intakeNode === node.node_id;
    if (!nodeItems.length && !intake) return null;
    const blocking = nodeItems.filter(item => blockers.includes(item)).length;
    const count = nodeItems.length + (intake ? 1 : 0);
    const expanded = open.has(node.node_id);
    const id = `${listId}-${node.node_id}`;
    return <div className="stage-attention">
      <button type="button" className={`stage-attention__toggle${blocking ? " is-blocking" : ""}`} aria-expanded={expanded} aria-controls={id}
        onClick={() => toggle(node.node_id)}>
        {blocking ? `${blocking} blocker${blocking === 1 ? "" : "s"}` : `${count} item${count === 1 ? "" : "s"}`}
      </button>
      <ul id={id} hidden={!expanded} className="stage-attention__list">
        {nodeItems.map(item => <li key={itemKey(item)}><AttentionLine item={item} onNavigate={onNavigate} /></li>)}
        {intake && <li><button type="button" className="btn btn-ghost" onClick={() => onNavigate({ kind: "evidence", target: "DOCUMENTS" })}>Action: Complete document intake</button></li>}
      </ul>
    </div>;
  }

  return <section className="case-attention case-attention--pipeline" aria-label="Attention required">
    <div className="case-attention__head">
      <h4>Pipeline</h4>
      <p className={blockerCount ? "case-attention__count is-blocking" : "case-attention__count"}>{countLabel(blockerCount)}</p>
    </div>
    {!blockers.length && !technical && <p className="text-muted">No immediate blockers</p>}
    {groupIds.length > 0 && <button type="button" className="btn btn-secondary case-attention__toggle-all" aria-expanded={allOpen}
      onClick={() => setOpen(allOpen ? new Set() : new Set(groupIds))}>{allOpen ? "Hide all issues" : "Show all issues"}</button>}
    {(general.length > 0 || technical) && <ul className="case-attention__general">
      {general.map(item => <li key={itemKey(item)}><AttentionLine item={item} onNavigate={onNavigate} /></li>)}
      {technical && <li><button type="button" className="btn btn-ghost" onClick={() => onNavigate({ kind: "technical" })}>Technical failure: {technical.code}</button></li>}
    </ul>}
    <PipelineRail summary={summary} onStageActivate={onStageActivate} renderAttention={renderAttention} />
  </section>;
}
