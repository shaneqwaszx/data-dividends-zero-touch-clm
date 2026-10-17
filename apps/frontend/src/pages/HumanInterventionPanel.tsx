import { useState } from "react";
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
  onConfirmExisting,
  stages,
  historyOnly = false,
}: {
  summary: ZeroTouchCaseSummary;
  isBusy: boolean;
  onResolve: (exception: ZeroTouchException, action: ExceptionResolutionAction) => void;
  onEvidenceAction?: (target: NonNullable<HumanInterventionProjection["evidence_actions"]>[number]["target"]) => void;
  onConfirmExisting?: (rationale: string) => void;
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
  const evidenceActionOwners = new Map<string, string>();
  for (const intervention of interventions) {
    for (const action of intervention.evidence_actions ?? []) {
      if (!evidenceActionOwners.has(action.target)) evidenceActionOwners.set(action.target, intervention.intervention_id);
    }
  }
  // Only informational summaries may share a card. Each retained evidence record
  // stays separate below; resolution and customer-confirmation authorities never merge.
  const groups: HumanInterventionProjection[][] = [];
  const informationalGroups = new Map<string, HumanInterventionProjection[]>();
  for (const intervention of interventions) {
    const informational = intervention.authorized_actions.length === 0
      && !intervention.existing_customer_confirmation_action
      && intervention.candidate_summaries.length === 0;
    const key = JSON.stringify([
      intervention.owning_stage, intervention.owning_stage_label, intervention.title,
      intervention.explanation, intervention.blocker_class, intervention.no_action_reason,
    ]);
    const existing = informational ? informationalGroups.get(key) : undefined;
    if (existing) existing.push(intervention);
    else {
      const group = [intervention];
      groups.push(group);
      if (informational) informationalGroups.set(key, group);
    }
  }

  return (
    <section className="intervention-stack" aria-label="Case interventions and history">
      {interventions.length > 0 && <div className="state-composition__header">
        <div>
          <p className="card-kicker">Backend-authorized intervention</p>
          <h3>Action required</h3>
        </div>
      </div>}
      {groups.map(([intervention, ...related]) => (
        <InterventionCard
          key={intervention.intervention_id}
          intervention={{ ...intervention, evidence_actions: [intervention, ...related].flatMap(
            item => (item.evidence_actions ?? []).filter(
              action => evidenceActionOwners.get(action.target) === item.intervention_id,
            ),
          ) }}
          exception={exceptionById.get(intervention.intervention_id)}
          relatedEvidence={related.map(item => ({ intervention: item, exception: exceptionById.get(item.intervention_id) }))}
          isBusy={isBusy}
          onResolve={onResolve}
          onEvidenceAction={onEvidenceAction}
          onConfirmExisting={summary.evidence_decision_authorized ? onConfirmExisting : undefined}
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
  onConfirmExisting,
  relatedEvidence = [],
}: {
  intervention: HumanInterventionProjection;
  exception: ZeroTouchException | undefined;
  isBusy: boolean;
  onResolve: (exception: ZeroTouchException, action: ExceptionResolutionAction) => void;
  onEvidenceAction?: (target: NonNullable<HumanInterventionProjection["evidence_actions"]>[number]["target"]) => void;
  onConfirmExisting?: (rationale: string) => void;
  relatedEvidence?: Array<{ intervention: HumanInterventionProjection; exception: ZeroTouchException | undefined }>;
}) {
  const [rationale, setRationale] = useState("");
  const evidenceRecords = [{ intervention, exception }, ...relatedEvidence];
  return (
    <article id={`case-intervention-${intervention.intervention_id}`} className="card intervention-card" aria-labelledby={`intervention-${intervention.intervention_id}`}>
      <div className="intervention-card__heading">
        <div>
          <p className="card-kicker">{intervention.owning_stage_label}</p>
          <h3 id={`intervention-${intervention.intervention_id}`}>{intervention.title}</h3>
        </div>
      </div>
      <p>{intervention.explanation}</p>
      {relatedEvidence.length > 0 && <p className="control-help">{evidenceRecords.length} related blockers</p>}

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

      {evidenceRecords.map(record => relatedEvidence.length > 0 ? (
        <article className="intervention-evidence-record" data-intervention-id={record.intervention.intervention_id}
          key={record.intervention.intervention_id}>
          <InterventionRequirements intervention={record.intervention} />
        </article>
      ) : <InterventionRequirements key={record.intervention.intervention_id} intervention={record.intervention} />)}
      <details className="evidence-details"><summary>Why is this blocked?</summary>
      {evidenceRecords.map(record => relatedEvidence.length > 0 ? (
        <article key={record.intervention.intervention_id} data-diagnostic-intervention-id={record.intervention.intervention_id}
          aria-label={`Diagnostics for ${record.intervention.blocker_code}`}>
          <InterventionEvidenceDetails {...record} />
        </article>
      ) : <InterventionEvidenceDetails key={record.intervention.intervention_id} {...record} />)}
      </details>
      {onEvidenceAction && intervention.evidence_actions?.map((action) => (
        <button key={action.target} type="button" className="btn btn-primary" disabled={isBusy}
          onClick={() => onEvidenceAction(action.target)}>{action.label}</button>
      ))}

      {intervention.existing_customer_confirmation_action && onConfirmExisting && (
        <form id="existing-customer-confirmation-form" onSubmit={(event) => {
          event.preventDefault();
          if (!isBusy && rationale.trim().length >= 3) onConfirmExisting(rationale.trim());
        }}>
          <p>Confirm this retained customer after comparing the identity evidence.
            This records your decision and makes no GoldTier call.</p>
          <label>Existing customer confirmation rationale
            <input id="existing-customer-confirmation-rationale" value={rationale} maxLength={240} disabled={isBusy}
              onChange={(event) => setRationale(event.target.value)} />
          </label>
          <button className="btn btn-primary" type="submit"
            disabled={isBusy || rationale.trim().length < 3}>
            Confirm existing GoldTier customer
          </button>
        </form>
      )}
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

function InterventionEvidenceDetails({ intervention, exception }: {
  intervention: HumanInterventionProjection;
  exception: ZeroTouchException | undefined;
}) {
  const decisions = intervention.decisions?.length ? intervention.decisions : exception?.decisions ?? [];
  return <>
      <code>{intervention.blocker_code}</code>
      {intervention.blocker_class && <p>{intervention.blocker_class.replaceAll("_", " ")}</p>}
      {intervention.dependent_stages?.length ? <p>Dependent stages: {intervention.dependent_stages.join(", ")}</p> : null}

      <BlockerDecisionDetails decisions={decisions} />
  </>;
}

function InterventionRequirements({ intervention }: { intervention: HumanInterventionProjection }) {
  return (
      <dl className="intervention-card__details">
        <div>
          <dt>Required evidence or input</dt>
          <dd>{intervention.required_evidence_or_input.join(" ")}</dd>
        </div>
        <div>
          <dt>Expected next step</dt>
          <dd>{intervention.expected_next_step}</dd>
        </div>
        {intervention.resolution_condition && <div><dt>Resolution condition</dt><dd>{intervention.resolution_condition}</dd></div>}
      </dl>
  );
}
