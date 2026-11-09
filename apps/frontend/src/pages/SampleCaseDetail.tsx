// Read-only case page for a fixed dashboard sample case. Sample cases exist only in the
// frontend (see mockDashboards/onboardingSample.ts): there is no backend record, document,
// ownership graph or audit trail behind them, so this page has no actions. By request the page
// does not label itself as sample data; it is reached at /cases/<id> like any other case.
// It uses the real case page's layout, Pipeline rail, Onboarding progress panel and stage
// sections, fed by `sampleCaseSummary`. Clicking a step opens and scrolls to its section.

import { useMemo, useRef, type ReactNode } from "react";
import { Link } from "react-router";

import { paths } from "../navigation";
import { formatDateNoSeconds, formatDuration, targetOutcomeLabel } from "../shared";
import { BUSINESS_EXCEPTION_TYPE_LABELS, type AuthenticatedProfile, type ProcessingNode, type ZeroTouchCaseSummary } from "../types";
import { JURISDICTION_LABELS, STAGE_LABELS } from "./Dashboard";
import { sampleCaseDetail, type SampleCaseDetail as SampleCaseData, type SampleStepState } from "./mockDashboards/onboardingSample";
import { sampleCaseSummary } from "./mockDashboards/sampleCaseSummary";
import { CasePipelineAttention } from "./CaseAttentionSummary";
import { businessStageIdFor, businessStageMembers, businessStagePipeline, OnboardingProgressPanel, stageStatusFor } from "./CaseStatePanels";
import StageDisclosure from "./StageDisclosure";

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

// The page shows one case, so a step id is unique on the page.
function stageSectionId(nodeId: string): string {
  return `case-stage-${businessStageIdFor(nodeId)}`;
}

/** Open a step's section and bring it into view, like a step click on a live case. */
function openStageSection(node: ProcessingNode): void {
  const section = document.getElementById(stageSectionId(node.node_id));
  if (!section) return;
  // StageDisclosure opens itself on this event.
  section.querySelector(".stage-disclosure")?.dispatchEvent(new Event("reveal-stage"));
  section.scrollIntoView?.({ behavior: "smooth", block: "start" });
}

/** One collapsible section per pipeline step, holding what is known about that step. */
function StageSections({ detail, summary }: { detail: SampleCaseData; summary: ZeroTouchCaseSummary }) {
  const backend = summary.processing_pipeline ?? [];
  // Stage time and blockers are shown once per backend stage, on its first step.
  const firstOfStage = (node: ProcessingNode) => Boolean(node.backend_stage)
    && backend.find((item) => item.backend_stage === node.backend_stage) === node;
  return <>
    {businessStagePipeline(backend).map((step) => {
      const members = businessStageMembers(backend, step);
      const status = stageStatusFor(summary, members.map((member) => member.node_id));
      return (
        <div key={step.node_id} id={stageSectionId(step.node_id)} className="evidence-focus-target">
          <StageDisclosure title={step.label} status={status} active={status?.tone === "attention" || status?.tone === "current"}
            summary={[...new Set(members.map((member) => member.safe_result).filter(Boolean))].join(" · ")}>
            {members.map((member) => {
              const stepData = member.backend_stage ? detail.steps.find((item) => item.stage === member.backend_stage) : undefined;
              const blockers = firstOfStage(member) ? detail.blockers.filter((blocker) => blocker.stage === member.backend_stage) : [];
              return (
                <div key={member.node_id} className="stage-facts__member">
                  {members.length > 1 && <h4>{member.label}</h4>}
                  <Row label="Status">{stageStatusFor(summary, [member.node_id])?.label ?? "—"}</Row>
                  {member.safe_result && <Row label="Outcome">{member.safe_result}</Row>}
                  {member.provider && <Row label="Provider">{member.provider}</Row>}
                  {firstOfStage(member) && <Row label="Processing time">{stepData?.duration_ms == null ? "—" : formatDuration(stepData.duration_ms)}</Row>}
                  {blockers.map((blocker, index) => (
                    <Row key={`${blocker.type}-${index}`} label={blocker.resolved ? "Resolved blocker" : "Open blocker"}>
                      {BUSINESS_EXCEPTION_TYPE_LABELS[blocker.type]}
                      {blocker.resolved && blocker.fix_ms !== null ? ` · fixed in ${formatDuration(blocker.fix_ms)}` : ""}
                      {blocker.resolved_by ? ` by ${blocker.resolved_by}` : ""}
                    </Row>
                  ))}
                </div>
              );
            })}
          </StageDisclosure>
        </div>
      );
    })}
  </>;
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
  const summary = useMemo(() => (detail ? sampleCaseSummary(detail) : null), [detail]);
  const blockersRef = useRef<HTMLElement>(null);

  if (!detail || !summary) {
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
    <div className="ds-root detail-layout readonly-case-detail">
      <div className="side-panel case-pipeline-panel">
        <Link className="btn btn-ghost" to={paths.cases} style={{ paddingLeft: 0 }}>← Back to Cases</Link>
        {/* Blocker links scroll to the Blockers table; there are no actions on a sample case. */}
        <CasePipelineAttention summary={summary} onNavigate={() => blockersRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })}
          onStageActivate={openStageSection} />
      </div>

    <section className="ds-page" style={{ flex: 1 }} aria-label={`Case ${detail.legal_name}`}>
      <header className="ds-page-header">
        <div>
          <p className="card-kicker case-header-meta"><span>{detail.requested_uen} · {detail.jurisdiction} · {detail.team_display_name ?? "—"}</span></p>
          <h1>{detail.legal_name}</h1>
        </div>
        <div className="case-header-actions">
          <span className="tag tag-accent-2 case-header-status">{detail.status.replaceAll("_", " ")}</span>
        </div>
      </header>

      <OnboardingProgressPanel summary={summary} onStageActivate={openStageSection} />

      <StageSections detail={detail} summary={summary} />

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
          <Row label="Team">{detail.team_display_name ?? "—"}</Row>
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

      <article className="card" ref={blockersRef}>
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
    </div>
  );
}
