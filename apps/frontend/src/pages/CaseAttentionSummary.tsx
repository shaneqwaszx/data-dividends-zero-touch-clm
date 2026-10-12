import type { HumanInterventionProjection, ZeroTouchCaseSummary, ZeroTouchException } from "../types";

export type AttentionDestination =
  | { kind: "exception"; exception: ZeroTouchException }
  | { kind: "evidence"; target: NonNullable<HumanInterventionProjection["evidence_actions"]>[number]["target"] }
  | { kind: "technical" }
  | { kind: "final" };

export default function CaseAttentionSummary({ summary, onNavigate }: {
  summary: ZeroTouchCaseSummary; onNavigate: (destination: AttentionDestination) => void;
}) {
  const active = summary.active_exceptions.filter(item => item.status === "OPEN");
  const isFinal = (item: ZeroTouchException) => item.exception_type === "TARGET_CONFIRMATION_REQUIRED";
  const interventionFor = (item: ZeroTouchException) => summary.interventions?.find(value => value.intervention_id === item.exception_id);
  const blockers = active.filter(item => !isFinal(item) && interventionFor(item)?.blocker_class !== "WARNING");
  const technical = summary.technical_failure;
  return <section className="case-attention" aria-label="Attention required">
    <h4>Attention required</h4>
    <p>{blockers.length + (technical ? 1 : 0)} active blocker{blockers.length + (technical ? 1 : 0) === 1 ? "" : "s"}</p>
    {!blockers.length && !technical && <p className="text-muted">No immediate blockers</p>}
    <ul>
      {active.map(item => {
        const intervention = interventionFor(item);
        return <li key={item.exception_id}>
          <button type="button" className="btn btn-ghost" onClick={() => onNavigate(isFinal(item) ? { kind: "final" } : { kind: "exception", exception: item })}>
            {isFinal(item) ? "Action: Review and send" : `${intervention?.blocker_class === "WARNING" ? "Attention" : "Blocker"}: ${intervention?.title ?? item.blocker_code.replaceAll("_", " ")}`}
          </button>
          {intervention?.evidence_actions?.filter(action => action.target !== "REVIEW_SEND" || !isFinal(item)).map(action => <button type="button" className="btn btn-ghost" key={action.target} onClick={() => onNavigate({ kind: "evidence", target: action.target })}>Action: {action.label}</button>)}
        </li>;
      })}
      {summary.status === "PENDING_INPUTS" && summary.current_stage === "DOCUMENT" && !active.some(item => item.stage === "DOCUMENT") && <li><button type="button" className="btn btn-ghost" onClick={() => onNavigate({ kind: "evidence", target: "DOCUMENTS" })}>Action: Complete document intake</button></li>}
      {technical && <li><button type="button" className="btn btn-ghost" onClick={() => onNavigate({ kind: "technical" })}>Technical failure: {technical.code}</button></li>}
    </ul>
  </section>;
}
