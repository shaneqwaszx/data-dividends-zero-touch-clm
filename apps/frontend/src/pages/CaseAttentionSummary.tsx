import type { HumanInterventionProjection, ZeroTouchCaseSummary, ZeroTouchException } from "../types";

export type AttentionDestination =
  | { kind: "exception"; exception: ZeroTouchException }
  | { kind: "evidence"; target: NonNullable<HumanInterventionProjection["evidence_actions"]>[number]["target"] }
  | { kind: "technical" }
  | { kind: "intervention"; interventionId: string }
  | { kind: "final" };

export default function CaseAttentionSummary({ summary, onNavigate }: {
  summary: ZeroTouchCaseSummary; onNavigate: (destination: AttentionDestination) => void;
}) {
  const active = summary.active_exceptions.filter(item => item.status === "OPEN");
  const exceptionIds = new Set(summary.active_exceptions.map(item => item.exception_id));
  const interventions = summary.interventions ?? [];
  // The projection ID is the exception ID for linked records. Codes are not identities.
  const items: Array<{ exception?: ZeroTouchException; intervention?: HumanInterventionProjection }> = [
    ...active.map(exception => ({ exception, intervention: interventions.find(item => item.intervention_id === exception.exception_id) })),
    ...interventions.filter(item => !exceptionIds.has(item.intervention_id)).map(intervention => ({ intervention })),
  ];
  const isFinal = (item: typeof items[number]) => item.exception?.exception_type === "TARGET_CONFIRMATION_REQUIRED"
    || item.intervention?.blocker_code === "TARGET_CONFIRMATION_REQUIRED";
  const blockers = items.filter(item => !isFinal(item) && item.intervention?.blocker_class !== "WARNING");
  const technical = summary.technical_failure;
  return <section className="case-attention" aria-label="Attention required">
    <h4>Attention required</h4>
    <p>{blockers.length + (technical ? 1 : 0)} active blocker{blockers.length + (technical ? 1 : 0) === 1 ? "" : "s"}</p>
    {!blockers.length && !technical && <p className="text-muted">No immediate blockers</p>}
    <ul>
      {items.map(item => {
        const { exception, intervention } = item;
        const primaryAction = intervention?.evidence_actions?.[0];
        return <li key={exception?.exception_id ?? intervention!.intervention_id}>
          <button type="button" className="btn btn-ghost" onClick={() => onNavigate(isFinal(item) ? { kind: "final" }
            : exception ? { kind: "exception", exception }
            : primaryAction ? { kind: "evidence", target: primaryAction.target }
            : { kind: "intervention", interventionId: intervention!.intervention_id })}>
            {isFinal(item) ? "Action: Review and send" : `${intervention?.blocker_class === "WARNING" ? "Attention" : "Blocker"}: ${intervention?.title ?? exception!.blocker_code.replaceAll("_", " ")}`}
          </button>
          {intervention?.evidence_actions?.filter(action => action.target !== "REVIEW_SEND" || !isFinal(item)).map(action => <button type="button" className="btn btn-ghost" key={action.target} onClick={() => onNavigate({ kind: "evidence", target: action.target })}>Action: {action.label}</button>)}
        </li>;
      })}
      {summary.status === "PENDING_INPUTS" && summary.current_stage === "DOCUMENT" && !items.some(item => (item.exception?.stage ?? item.intervention?.owning_stage) === "DOCUMENT") && <li><button type="button" className="btn btn-ghost" onClick={() => onNavigate({ kind: "evidence", target: "DOCUMENTS" })}>Action: Complete document intake</button></li>}
      {technical && <li><button type="button" className="btn btn-ghost" onClick={() => onNavigate({ kind: "technical" })}>Technical failure: {technical.code}</button></li>}
    </ul>
  </section>;
}
