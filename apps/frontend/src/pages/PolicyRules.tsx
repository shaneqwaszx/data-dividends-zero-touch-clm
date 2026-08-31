import { useEffect, useState } from "react";

import { ApiError, fetchPolicy } from "../api";
import type { PolicyResponse } from "../types";

export default function PolicyRules() {
  const [policy, setPolicy] = useState<PolicyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetchPolicy()
      .then((value) => {
        setPolicy(value);
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
        Read at run time, not compiled in. Country logic sits behind the jurisdiction
        parameter so ACRA and other registries can diverge without touching the screens.
      </p>
      {error && <div className="ds-banner ds-banner-warn">{error}</div>}
      {!error && !policy && <p className="text-muted">Loading policy…</p>}
      {policy && (
        <div className="ds-two-col">
          <div style={{ flex: 1 }}>
            <h4>Jurisdiction rules</h4>
            <div className="table-card">
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
                      <td>{rule.implemented ? "Yes" : "Not implemented"}</td>
                      <td>{rule.id_label ?? "—"}</td>
                      <td>{rule.registry ?? "—"}</td>
                      <td>{rule.ubo_threshold_percent ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div style={{ width: 360 }}>
            <div className="card">
              <p className="card-kicker">Pipeline policy</p>
              <table className="table">
                <tbody>
                  <tr><td>Stages</td><td>{policy.pipeline.stages.length}</td></tr>
                  <tr>
                    <td>Screening auto-clear</td>
                    <td>{policy.pipeline.screening_auto_clear_threshold}</td>
                  </tr>
                  <tr>
                    <td>Document confidence</td>
                    <td>{policy.pipeline.idp_review_confidence_threshold}</td>
                  </tr>
                  <tr>
                    <td>Snapshot staleness limit</td>
                    <td>{policy.pipeline.registry_snapshot_staleness_limit_days} days</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div className="card" style={{ marginTop: 16 }}>
              <p className="card-kicker">Roles</p>
              <table className="table">
                <tbody>
                  <tr><td>Reviewers</td><td>{policy.roles.reviewer_count}</td></tr>
                  <tr>
                    <td>Self-review blocked</td>
                    <td>{policy.roles.self_review_blocked ? "Yes" : "No"}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div className="card" style={{ marginTop: 16 }}>
              <p className="card-kicker">Scheduler</p>
              <table className="table">
                <tbody>
                  <tr><td>Next review · low risk</td><td>{policy.scheduler.next_review_months_low} months</td></tr>
                  <tr><td>Next review · medium</td><td>{policy.scheduler.next_review_months_medium} months</td></tr>
                  <tr><td>Next review · high</td><td>{policy.scheduler.next_review_months_high} months</td></tr>
                  <tr><td>Re-screening</td><td>Every {policy.scheduler.rescreening_cadence_months} month(s)</td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
