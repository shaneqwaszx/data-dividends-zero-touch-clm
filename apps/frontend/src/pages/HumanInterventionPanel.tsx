import type {
  ExceptionResolutionAction,
  HumanInterventionProjection,
  ZeroTouchCaseSummary,
  ZeroTouchException,
} from "../types";
import BlockerDecisionDetails from "./BlockerDecisionDetails";

export default function HumanInterventionPanel({
  summary,
  isBusy,
  onResolve,
  onEvidenceAction,
  stages,
  historyOnly = false,
}: {
  summary: ZeroTouchCaseSummary;
  isBusy: boolean;
  onResolve: (exception: ZeroTouchException, action: ExceptionResolutionAction) => void;
  onEvidenceAction?: (target: NonNullable<HumanInterventionProjection["evidence_actions"]>[number]["target"]) => void;
  stages?: readonly string[];
  historyOnly?: boolean;
}) {
  const interventions = historyOnly ? [] : (summary.interventions ?? []).filter(
    (item) => !stages || stages.includes(item.owning_stage),
  );
  const history = historyOnly || !stages ? summary.historical_exceptions ?? [] : [];
  if (interventions.length === 0 && history.length === 0) return null;

  const exceptionById = new Map(
    summary.active_exceptions.map((exception) => [exception.exception_id, exception]),
  );

  return (
    <section className="intervention-stack" aria-label="Case interventions and history">
      {interventions.length > 0 && <div className="state-composition__header">
        <div>
          <p className="card-kicker">Backend-authorized intervention</p>
          <h3>Action required</h3>
        </div>
      </div>}
      {interventions.map((intervention) => (
        <InterventionCard
          key={intervention.intervention_id}
          intervention={intervention}
          exception={exceptionById.get(intervention.intervention_id)}
          isBusy={isBusy}
          onResolve={onResolve}
          onEvidenceAction={onEvidenceAction}
        />
      ))}
      {history.length > 0 && <details className="card intervention-history">
        <summary>Intervention history ({history.length})</summary>
        {history.map((item) => <article key={item.exception_id}>
          <h3>{item.blocker_code} - {item.status}</h3>
          <p>{item.explanation}</p>
          <p>Result: {item.resolution ?? item.status} - evidence {item.evidence_version}
            {item.resolved_at ? ` - ${new Date(item.resolved_at).toLocaleString()}` : ""}</p>
          <BlockerDecisionDetails decisions={item.decisions ?? []} />
        </article>)}
      </details>}
    </section>
  );
}

function InterventionCard({
  intervention,
  exception,
  isBusy,
  onResolve,
  onEvidenceAction,
}: {
  intervention: HumanInterventionProjection;
  exception: ZeroTouchException | undefined;
  isBusy: boolean;
  onResolve: (exception: ZeroTouchException, action: ExceptionResolutionAction) => void;
  onEvidenceAction?: (target: NonNullable<HumanInterventionProjection["evidence_actions"]>[number]["target"]) => void;
}) {
  const decisions = intervention.decisions?.length
    ? intervention.decisions
    : exception?.decisions ?? [];
  return (
    <article className="card intervention-card" aria-labelledby={`intervention-${intervention.intervention_id}`}>
      <div className="intervention-card__heading">
        <div>
          <p className="card-kicker">{intervention.owning_stage_label}</p>
          <h3 id={`intervention-${intervention.intervention_id}`}>{intervention.title}</h3>
        </div>
      </div>
      <p>{intervention.explanation}</p>

      {intervention.candidate_summaries.length > 0 && (
        <div className="table-scroll" tabIndex={0} aria-label="Safe GoldTier candidate summary">
          <table className="table">
            <thead><tr><th>GoldTier ID</th><th>Legal name</th><th>Registration</th><th>Country</th><th>Legal form</th></tr></thead>
            <tbody>
              {intervention.candidate_summaries.map((candidate) => (
                <tr key={candidate.party_id}>
                  <td>{candidate.party_id}</td>
                  <td>{candidate.legal_name ?? "Not provided"}</td>
                  <td>{candidate.registration_number ?? "Not provided"}</td>
                  <td>{candidate.country ?? "Not provided"}</td>
                  <td>{candidate.legal_form ?? "Not provided"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <details className="evidence-details"><summary>Why is this blocked?</summary>
      <code>{intervention.blocker_code}</code>
      {intervention.blocker_class && <p>{intervention.blocker_class.replaceAll("_", " ")}</p>}
      <dl className="intervention-card__details">
        <div>
          <dt>Required evidence or input</dt>
          <dd>{intervention.required_evidence_or_input.join(" ")}</dd>
        </div>
        <div>
          <dt>Expected next step</dt>
          <dd>{intervention.expected_next_step}</dd>
        </div>
        {intervention.dependent_stages?.length ? <div><dt>Dependent stages</dt><dd>{intervention.dependent_stages.join(", ")}</dd></div> : null}
        {intervention.resolution_condition && <div><dt>Resolution condition</dt><dd>{intervention.resolution_condition}</dd></div>}
      </dl>

      <BlockerDecisionDetails decisions={decisions} />
      </details>
      {onEvidenceAction && intervention.evidence_actions?.map((action) => (
        <button key={action.target} type="button" className="btn btn-primary" disabled={isBusy}
          onClick={() => onEvidenceAction(action.target)}>{action.label}</button>
      ))}

      {intervention.authorized_actions.length > 0 ? (
        <div className="intervention-card__actions" aria-label="Backend-authorized actions">
          {intervention.authorized_actions.map((authorized) => (
            <div key={authorized.action}>
              <button
                type="button"
                className="btn btn-primary"
                disabled={isBusy || !exception}
                onClick={() => exception && onResolve(exception, authorized.action)}
              >
                {authorized.label}
              </button>
              <p className="control-help">{authorized.description}</p>
            </div>
          ))}
        </div>
      ) : intervention.no_action_reason ? (
        <div className="ds-banner ds-banner-warn intervention-card__no-action" role="status">
          <strong>No action available</strong>
          <span>{intervention.no_action_reason}</span>
        </div>
      ) : null}
    </article>
  );
}
