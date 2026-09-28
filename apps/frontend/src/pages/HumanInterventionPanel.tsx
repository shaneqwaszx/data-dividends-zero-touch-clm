import type {
  ExceptionResolutionAction,
  HumanInterventionProjection,
  ZeroTouchCaseSummary,
  ZeroTouchException,
} from "../types";

export default function HumanInterventionPanel({
  summary,
  isBusy,
  onResolve,
}: {
  summary: ZeroTouchCaseSummary;
  isBusy: boolean;
  onResolve: (exception: ZeroTouchException, action: ExceptionResolutionAction) => void;
}) {
  const interventions = summary.interventions ?? [];
  if (interventions.length === 0) return null;

  const exceptionById = new Map(
    summary.active_exceptions.map((exception) => [exception.exception_id, exception]),
  );

  return (
    <section className="intervention-stack" aria-labelledby="intervention-heading">
      <div className="state-composition__header">
        <div>
          <p className="card-kicker">Backend-authorized intervention</p>
          <h2 id="intervention-heading">Action required</h2>
        </div>
      </div>
      {interventions.map((intervention) => (
        <InterventionCard
          key={intervention.intervention_id}
          intervention={intervention}
          exception={exceptionById.get(intervention.intervention_id)}
          isBusy={isBusy}
          onResolve={onResolve}
        />
      ))}
    </section>
  );
}

function InterventionCard({
  intervention,
  exception,
  isBusy,
  onResolve,
}: {
  intervention: HumanInterventionProjection;
  exception: ZeroTouchException | undefined;
  isBusy: boolean;
  onResolve: (exception: ZeroTouchException, action: ExceptionResolutionAction) => void;
}) {
  return (
    <article className="card intervention-card" aria-labelledby={`intervention-${intervention.intervention_id}`}>
      <div className="intervention-card__heading">
        <div>
          <p className="card-kicker">{intervention.owning_stage_label}</p>
          <h3 id={`intervention-${intervention.intervention_id}`}>{intervention.title}</h3>
        </div>
        <code>{intervention.blocker_code}</code>
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

      <dl className="intervention-card__details">
        <div>
          <dt>Required evidence or input</dt>
          <dd>{intervention.required_evidence_or_input.join(" ")}</dd>
        </div>
        <div>
          <dt>Expected next step</dt>
          <dd>{intervention.expected_next_step}</dd>
        </div>
      </dl>

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
      ) : (
        <div className="ds-banner ds-banner-warn intervention-card__no-action" role="status">
          <strong>No action available</strong>
          <span>{intervention.no_action_reason}</span>
        </div>
      )}
    </article>
  );
}
