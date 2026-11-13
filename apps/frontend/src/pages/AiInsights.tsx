// ADR-015 / D-128: the read-only "AI insights" panel on the Onboarding Dashboard Manager view.
// Shows a loading placeholder while waiting, then the checked insights; hidden on any
// failure. Severity, evidence and case links come from the fixed rules, never from the model.

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";

import type { DashboardInsights } from "../aiAssistant";
import { dashboardInsightsQueryOptions, dashboardQueryOptions, policyCatalogueQueryOptions } from "../caseQueries";
import { paths } from "../navigation";
import type { AuthenticatedProfile, AutomationStage, DashboardSnapshot } from "../types";
import { buildInsightFindings, proposalsAwaitingDecision, type InsightFindingView } from "./aiInsightFindings";
import { isSampleCaseId, withOnboardingSample } from "./mockDashboards/onboardingSample";

const SEVERITY_CLASS: Record<InsightFindingView["severity"], string> = {
  CRITICAL: "ai-dot ai-dot--critical",
  WARNING: "ai-dot ai-dot--warning",
  INFO: "ai-dot ai-dot--info",
};
const SEVERITY_LABEL: Record<InsightFindingView["severity"], string> = { CRITICAL: "Critical", WARNING: "Warning", INFO: "Note" };

type Item = { id: string; text: string };

/** Keeps only well-formed items for findings this panel built; anything else is ignored. */
function usable(reply: unknown, views: Record<string, InsightFindingView>): { summary: string; notes: Item[]; actions: Item[] } | null {
  if (!reply || typeof reply !== "object") return null;
  const value = reply as Partial<DashboardInsights>;
  const items = (list: unknown): Item[] => (Array.isArray(list) ? list : [])
    .filter((item): item is Item => Boolean(item) && typeof item.id === "string" && typeof item.text === "string" && item.id in views && item.text.length > 0);
  const summary = typeof value.summary === "string" ? value.summary : "";
  const notes = items(value.notes);
  if (!notes.length) return null;
  return { summary, notes, actions: items(value.actions) };
}

function CaseLinks({ view }: { view: InsightFindingView }) {
  if (!view.cases.length) return null;
  return (
    <span className="ai-case-links">
      {view.cases.map((item, index) => (
        <span key={item.case_id}>
          {index > 0 && " · "}
          <Link to={isSampleCaseId(item.case_id) ? paths.sampleCaseDetail(item.case_id) : paths.caseDetail(item.case_id)}>{item.name}</Link>
        </span>
      ))}
    </span>
  );
}

function AiInsightsLoading() {
  return (
    <section className="card ai-insights ai-insights--loading" aria-label="AI insights" aria-busy="true">
      <div className="ai-insights-head">
        <h2>AI insights</h2>
      </div>
      <p className="text-muted ai-loading-text" role="status">Loading insights…</p>
      <div className="ai-skeleton" aria-hidden="true">
        <span /><span /><span />
      </div>
    </section>
  );
}

export default function AiInsights({ dashboard, actor, dateRange, teamFilter, stageLabels }: {
  dashboard: DashboardSnapshot;
  actor: AuthenticatedProfile;
  dateRange: string;
  teamFilter: string;
  stageLabels: Record<AutomationStage, string>;
}) {
  // Insights always cover all the data in the viewer's scope, whatever date range is shown.
  // With "All time" selected the dashboard on screen is reused; otherwise it is read once more.
  const allTime = useQuery({
    ...dashboardQueryOptions(actor.user_id, teamFilter, "team", "all"),
    enabled: dateRange !== "all",
  });
  const source = useMemo(
    () => (dateRange === "all" ? dashboard : allTime.data ? withOnboardingSample(allTime.data, actor) : null),
    [dateRange, dashboard, allTime.data, actor],
  );
  // A Director's insights include policy changes waiting for them; wait for that count (or its
  // failure) so the model is asked once, not again when the count arrives.
  const isDirector = actor.role === "DIRECTOR";
  const canApprove = isDirector && actor.capabilities.includes("POLICY_APPROVE");
  const policies = useQuery({ ...policyCatalogueQueryOptions(actor.user_id), enabled: canApprove });
  const policiesSettled = !canApprove || !policies.isPending;
  const pendingPolicyChanges = canApprove && policies.data ? proposalsAwaitingDecision(policies.data, actor).length : null;
  const findings = useMemo(
    () => (source && policiesSettled
      ? buildInsightFindings(source, { isDirector, dateRange: "all", stageLabels, pendingPolicyChanges })
      : null),
    [source, policiesSettled, isDirector, stageLabels, pendingPolicyChanges],
  );
  const query = useQuery({
    ...dashboardInsightsQueryOptions(actor.user_id, findings?.request ?? { period: "", findings: [] }),
    enabled: findings !== null,
  });
  const insights = findings && query.isSuccess ? usable(query.data, findings.views) : null;
  // A placeholder while the figures or the model's reply are on their way; nothing on failure.
  const loading = !insights && (
    (dateRange !== "all" && allTime.isPending)
    || (canApprove && policies.isPending)
    || (findings !== null && query.isPending)
  );
  if (loading) return <AiInsightsLoading />;
  if (!findings || !insights) return null;

  return (
    <section className="card ai-insights" aria-label="AI insights">
      <div className="ai-insights-head">
        <h2>AI insights</h2>
      </div>
      {insights.summary && <p className="ai-summary">{insights.summary}</p>}
      <div className="ai-columns">
        <div>
          <h3 className="ai-heading">What to note</h3>
          <ul className="ai-list">
            {insights.notes.map((note) => {
              const view = findings.views[note.id];
              return (
                <li key={note.id}>
                  <i className={SEVERITY_CLASS[view.severity]} aria-label={SEVERITY_LABEL[view.severity]} role="img" />
                  <div>{note.text}<span className="ai-evidence">{view.evidence}</span></div>
                </li>
              );
            })}
          </ul>
        </div>
        {insights.actions.length > 0 && (
          <div>
            <h3 className="ai-heading">What to do</h3>
            <ol className="ai-list">
              {insights.actions.map((action, index) => {
                const view = findings.views[action.id];
                return (
                  <li key={action.id}>
                    <span className="ai-number">{index + 1}</span>
                    <div>{action.text}<CaseLinks view={view} /><span className="ai-evidence">{view.evidence}</span></div>
                  </li>
                );
              })}
            </ol>
          </div>
        )}
      </div>
    </section>
  );
}
