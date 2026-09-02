import { useEffect, useState } from "react";

import { ApiError, fetchExecutionProfile } from "../api";
import type { ClassifiedPolicyValue, PolicyClassification, PolicyView } from "../viewModels";
import { mapExecutionProfileToPolicy } from "../viewModels";

export function PolicyClassificationBadge({ classification }: { classification: PolicyClassification }) {
  return <span className={`policy-classification policy-classification--${classification.toLowerCase().replaceAll(" ", "-")}`}>{classification}</span>;
}

function PolicyValue({ item, format }: { item: ClassifiedPolicyValue<unknown>; format?: (value: unknown) => string }) {
  const value = format ? format(item.value) : String(item.value);
  return <span className="policy-value"><span>{value}</span><PolicyClassificationBadge classification={item.classification} /></span>;
}

export default function PolicyRules() {
  const [policy, setPolicy] = useState<PolicyView | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetchExecutionProfile()
      .then((value) => {
        setPolicy(mapExecutionProfileToPolicy(value));
        setError(null);
      })
      .catch((requestError) => {
        setError(
          requestError instanceof ApiError ? requestError.message : "Policy is unavailable.",
        );
      });
  }, []);

  return (
    <div className="ds-root ds-page">
      <h1>Policy and rules</h1>
      <p className="text-muted">
        Read-only POC policy. Every applicable value is classified as REAL, DERIVED,
        PENDING SPONSOR CONFIRMATION, or UNAVAILABLE.
      </p>
      <div className="ds-banner policy-open-questions">
        <strong>Open sponsor questions</strong>
        {(policy?.open_questions ?? []).map((question) => (
          <span className="policy-question" key={question.value}>
            <span>{question.value}</span>
            <PolicyClassificationBadge classification={question.classification} />
          </span>
        ))}
      </div>
      {error && <div className="ds-banner ds-banner-warn">{error}</div>}
      {!error && !policy && <p className="text-muted">Loading policy…</p>}
      {policy && (
        <div className="ds-two-col">
          <div style={{ flex: 1 }}>
            <h4>Jurisdiction rules</h4>
            <div className="table-card table-scroll" tabIndex={0}>
              <table className="table">
                <thead>
                  <tr>
                    <th>Jurisdiction</th>
                    <th>Implemented</th>
                    <th>ID label</th>
                    <th>Registry</th>
                    <th>UBO threshold</th>
                  </tr>
                </thead>
                <tbody>
                  {policy.jurisdiction_rules.map((rule) => (
                    <tr key={rule.jurisdiction}>
                      <td>{rule.jurisdiction}</td>
                      <td><PolicyValue item={rule.implemented} format={(value) => value ? "Yes" : "Not implemented"} /></td>
                      <td><PolicyValue item={rule.id_label} /></td>
                      <td><PolicyValue item={rule.registry} /></td>
                      <td><PolicyValue item={rule.ubo_threshold_percent} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className="policy-card-rail">
            <div className="card">
              <p className="card-kicker">Pipeline policy</p>
              <table className="table">
                <tbody>
                  <tr><td>Stages</td><td><PolicyValue item={policy.pipeline.stages} format={(value) => String((value as unknown[]).length)} /></td></tr>
                  <tr>
                    <td>Screening auto-clear</td>
                    <td><PolicyValue item={policy.pipeline.screening_auto_clear_threshold} /></td>
                  </tr>
                  <tr>
                    <td>Document confidence</td>
                    <td><PolicyValue item={policy.pipeline.idp_review_confidence_threshold} /></td>
                  </tr>
                  <tr>
                    <td>Snapshot staleness limit</td>
                    <td><PolicyValue item={policy.pipeline.registry_snapshot_staleness_limit_days} /></td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div className="card" style={{ marginTop: 16 }}>
              <p className="card-kicker">Roles</p>
              <table className="table">
                <tbody>
                  <tr><td>Reviewers</td><td><PolicyValue item={policy.roles.reviewer_count} /></td></tr>
                  <tr>
                    <td>Self-review blocked</td>
                    <td><PolicyValue item={policy.roles.self_review_blocked} /></td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div className="card" style={{ marginTop: 16 }}>
              <p className="card-kicker">Scheduler</p>
              <table className="table">
                <tbody>
                  <tr><td>Next review · low risk</td><td><PolicyValue item={policy.scheduler.next_review_months_low} /></td></tr>
                  <tr><td>Next review · medium</td><td><PolicyValue item={policy.scheduler.next_review_months_medium} /></td></tr>
                  <tr><td>Next review · high</td><td><PolicyValue item={policy.scheduler.next_review_months_high} /></td></tr>
                  <tr><td>Re-screening</td><td><PolicyValue item={policy.scheduler.rescreening_cadence_months} /></td></tr>
                </tbody>
              </table>
            </div>
            <div className="card" style={{ marginTop: 16 }}>
              <p className="card-kicker">Execution profile</p>
              <table className="table"><tbody>
                <tr><td>Registry</td><td><PolicyValue item={policy.execution.registry} /></td></tr>
                <tr><td>IDP</td><td><PolicyValue item={policy.execution.idp} /></td></tr>
                <tr><td>Ownership</td><td><PolicyValue item={policy.execution.ownership} /></td></tr>
                <tr><td>Target</td><td><PolicyValue item={policy.execution.target} /></td></tr>
                <tr><td>Persistence</td><td><PolicyValue item={policy.execution.persistence} /></td></tr>
              </tbody></table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
