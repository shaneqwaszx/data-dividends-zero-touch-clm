// Read-only case page for a fixed dashboard sample case. Sample cases exist only in the
// frontend (see mockDashboards/onboardingSample.ts): there is no backend record, document,
// ownership graph or audit trail behind them, so this page has no actions. By request the page
// does not label itself as sample data; it is reached at /cases/<id> like any other case.

import { useMemo, type ReactNode } from "react";
import { Link } from "react-router";

import { paths } from "../navigation";
import { formatDateNoSeconds, formatDuration, targetOutcomeLabel } from "../shared";
import { BUSINESS_EXCEPTION_TYPE_LABELS, type AuthenticatedProfile } from "../types";
import { JURISDICTION_LABELS, STAGE_LABELS } from "./Dashboard";
import { sampleCaseDetail, type SampleStepState } from "./mockDashboards/onboardingSample";

const STEP_STATE_LABELS: Record<SampleStepState, string> = {
  done: "Done",
  review: "Stopped for review",
  in_progress: "In progress",
  waiting_inputs: "Waiting for inputs",
  not_started: "Not started",
};

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="kv-row">
      <span className="kv-label">{label}</span>
      <span className="kv-value">{children}</span>
    </div>
  );
}

export default function SampleCaseDetail({
  sampleCaseId,
  actor,
}: {
  sampleCaseId: string;
  actor: AuthenticatedProfile;
}) {
  // Dates are placed relative to when the page opened, like the dashboard does.
  const detail = useMemo(() => sampleCaseDetail(sampleCaseId, actor), [sampleCaseId, actor]);

  if (!detail) {
    return (
      <section className="ds-root ds-page">
        <Link className="btn btn-ghost" to={paths.cases}>← Cases</Link>
        <h1>Case not found</h1>
        <p className="text-muted">There is no case with this ID.</p>
      </section>
    );
  }

  const completed = detail.status === "COMPLETED";
  return (
    <section className="ds-root ds-page readonly-case-detail" aria-label={`Case ${detail.legal_name}`}>
      <header className="ds-page-header">
        <div>
          <Link className="btn btn-ghost" to={paths.cases}>← Cases</Link>
          <h1>{detail.legal_name}</h1>
        </div>
      </header>

      <div className="ds-two-col">
        <article className="card" style={{ flex: 1 }}>
          <h2>Summary</h2>
          <Row label="Registration ID">{detail.requested_uen}</Row>
          <Row label="Jurisdiction">{JURISDICTION_LABELS[detail.jurisdiction]}</Row>
          <Row label="Status">{detail.status.replaceAll("_", " ")}</Row>
          <Row label="Current step">
            {completed && detail.final_outcome ? targetOutcomeLabel(detail.final_outcome) : STAGE_LABELS[detail.current_stage]}
          </Row>
          <Row label="Owner">{detail.created_by_display_name}</Row>
          <Row label="Priority">{detail.priority ?? "Not set"}</Row>
          <Row label="Created">{formatDateNoSeconds(detail.created_at)}</Row>
          {detail.completed_at
            ? <Row label="Completed">{formatDateNoSeconds(detail.completed_at)}</Row>
            : <Row label="Updated">{formatDateNoSeconds(detail.updated_at)}</Row>}
          <Row label={completed ? "Case duration" : "Case age"}>{formatDuration(detail.case_elapsed_ms)}</Row>
          {detail.delay_note && <Row label="Note">{detail.delay_note}</Row>}
        </article>

        <article className="card" style={{ flex: 1 }}>
          <h2>Steps</h2>
          <table className="table" aria-label="Case steps">
            <thead>
              <tr><th>Step</th><th>State</th><th style={{ textAlign: "right" }}>Processing time</th></tr>
            </thead>
            <tbody>
              {detail.steps.map((step) => (
                <tr key={step.stage}>
                  <td>{STAGE_LABELS[step.stage]}</td>
                  <td>{STEP_STATE_LABELS[step.state]}</td>
                  <td style={{ textAlign: "right" }}>{step.duration_ms === null ? "—" : formatDuration(step.duration_ms)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>
      </div>

      <article className="card">
        <h2>Blockers</h2>
        {detail.blockers.length === 0 ? (
          <p className="text-muted">{completed ? "None. This case completed zero-touch." : "None raised so far."}</p>
        ) : (
          <table className="table" aria-label="Case blockers">
            <thead>
              <tr><th>Blocker</th><th>Step</th><th>State</th><th>Time to fix</th><th>Resolved by</th></tr>
            </thead>
            <tbody>
              {detail.blockers.map((blocker, index) => (
                <tr key={`${blocker.type}-${index}`}>
                  <td>{BUSINESS_EXCEPTION_TYPE_LABELS[blocker.type]}</td>
                  <td>{STAGE_LABELS[blocker.stage]}</td>
                  <td>{blocker.resolved ? "Resolved" : "Open"}</td>
                  <td>{blocker.fix_ms === null ? "—" : formatDuration(blocker.fix_ms)}</td>
                  <td>{blocker.resolved_by ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </article>
    </section>
  );
}
