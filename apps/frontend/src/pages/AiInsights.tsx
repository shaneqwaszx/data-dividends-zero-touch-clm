// ADR-015 / D-128: the read-only "AI insights" panel on the Onboarding Dashboard Manager view.
// Shows a loading placeholder while waiting, then the checked insights; hidden on any
// failure. Severity, evidence and case links come from the fixed rules, never from the model.
//
// D-130 amendment draft (fifth hosted Claude path): when the service reports mode "generate"
// (the hosted deployment), nothing is asked on load. The panel shows the external-AI notice and
// a "Generate AI Insights" button; the service derives the figures itself from the eligible
// cases and returns them with the reply, so this view sends no dashboard data. "off" hides it.

import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router";

import { AiAssistantError, generateDashboardInsights, type DashboardInsights, type InsightFinding } from "../aiAssistant";
import {
  caseQueryKeys, dashboardInsightsModeQueryOptions, dashboardInsightsQueryOptions, dashboardQueryOptions, policyCatalogueQueryOptions,
} from "../caseQueries";
import { paths } from "../navigation";
import type { AuthenticatedProfile, AutomationStage, DashboardSnapshot } from "../types";
import { buildInsightFindings, proposalsAwaitingDecision, type InsightFindingView } from "./aiInsightFindings";
import ExternalAiNotice from "./ExternalAiNotice";
import { isSampleCaseId, withOnboardingSample } from "./mockDashboards/onboardingSample";

const SEVERITY_CLASS: Record<InsightFindingView["severity"], string> = {
  CRITICAL: "ai-dot ai-dot--critical",
  WARNING: "ai-dot ai-dot--warning",
  INFO: "ai-dot ai-dot--info",
};
const SEVERITY_LABEL: Record<InsightFindingView["severity"], string> = { CRITICAL: "Critical", WARNING: "Warning", INFO: "Note" };

type Item = { id: string; text: string };

/** Keeps only well-formed items for findings this panel built; anything else is ignored. */
function usable(reply: unknown, views: Record<string, unknown>): { summary: string; notes: Item[]; actions: Item[] } | null {
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

/** The figures behind a hosted finding, as the service derived them (labels and counts only). */
function factsText(finding: InsightFinding): string {
  return Object.entries(finding.facts).map(([key, value]) => `${key.replace(/_/g, " ")} ${value}`).join(" · ");
}

const NOTICE_ID = "ai-insights-external-notice";

/** Hosted mode: one explicit, user-triggered request; never on load and never retried. */
function HostedAiInsights({ actor, remaining }: { actor: AuthenticatedProfile; remaining: number | null }) {
  const client = useQueryClient();
  const generate = useMutation({
    mutationFn: generateDashboardInsights,
    retry: false,
    onSettled: () => client.invalidateQueries({ queryKey: caseQueryKeys.dashboardInsightsMode(actor.user_id) }),
  });
  const findings = Object.fromEntries((generate.data?.findings ?? []).map((item) => [item.id, item]));
  const reply = generate.data ? usable(generate.data.insights, findings) : null;
  const limited = generate.error instanceof AiAssistantError && generate.error.status === 429;
  const exhausted = remaining !== null && remaining <= 0;
  return (
    <section className="card ai-insights" aria-label="AI insights" aria-busy={generate.isPending}>
      <div className="ai-insights-head">
        <h2>AI insights</h2>
      </div>
      <ExternalAiNotice surface="insights" id={NOTICE_ID} />
      <p>
        <button
          type="button"
          className="btn btn-secondary"
          aria-describedby={NOTICE_ID}
          disabled={generate.isPending || exhausted}
          onClick={() => generate.mutate()}
        >
          {generate.isPending ? "Generating…" : "Generate AI Insights"}
        </button>
        {remaining !== null && <span className="text-muted"> {remaining} left today</span>}
      </p>
      {generate.isError && (
        <p className="text-muted" role="status">
          {limited ? "The daily limit for AI insights has been reached. Try again tomorrow." : "AI insights are unavailable right now."}
        </p>
      )}
      {generate.isSuccess && !reply && <p className="text-muted" role="status">AI insights are unavailable right now.</p>}
      {reply && (
        <>
          {reply.summary && <p className="ai-summary">{reply.summary}</p>}
          <div className="ai-columns">
            <div>
              <h3 className="ai-heading">What to note</h3>
              <ul className="ai-list">
                {reply.notes.map((note) => (
                  <li key={note.id}>
                    <i className={SEVERITY_CLASS[findings[note.id].severity]} aria-label={SEVERITY_LABEL[findings[note.id].severity]} role="img" />
                    <div>{note.text}<span className="ai-evidence">{factsText(findings[note.id])}</span></div>
                  </li>
                ))}
              </ul>
            </div>
            {reply.actions.length > 0 && (
              <div>
                <h3 className="ai-heading">What to do</h3>
                <ol className="ai-list">
                  {reply.actions.map((action, index) => (
                    <li key={action.id}>
                      <span className="ai-number">{index + 1}</span>
                      <div>{action.text}<span className="ai-evidence">{factsText(findings[action.id])}</span></div>
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </div>
        </>
      )}
    </section>
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
  // The service says how insights are offered (c2r1, P3-3: fail closed). The check validates the
  // answer, so `mode.data` is always a recognised mode. Only a current, successful "auto" runs the
  // merged automatic panel. A failed, timed-out, malformed or unrecognised check never falls back
  // to it: it shows a controlled unavailable state with a retry and sends nothing else. A confirmed
  // "generate" or "off" stays in force if a later re-check fails (nothing is sent automatically).
  const mode = useQuery(dashboardInsightsModeQueryOptions(actor.user_id));
  const known = mode.data?.mode;
  if (known === "off") return null;
  if (known === "generate") return <HostedAiInsights actor={actor} remaining={mode.data?.remaining_user ?? null} />;
  if (mode.isSuccess && known === "auto") {
    return <AutomaticAiInsights dashboard={dashboard} actor={actor} dateRange={dateRange} teamFilter={teamFilter} stageLabels={stageLabels} />;
  }
  if (mode.isError) return <AiInsightsUnavailable retrying={mode.isFetching} onRetry={() => void mode.refetch()} />;
  return <AiInsightsLoading />;
}

/** The mode check failed: nothing is generated or sent; the user may check again. */
function AiInsightsUnavailable({ retrying, onRetry }: { retrying: boolean; onRetry: () => void }) {
  return (
    <section className="card ai-insights" aria-label="AI insights">
      <div className="ai-insights-head">
        <h2>AI insights</h2>
      </div>
      <p className="text-muted" role="status">AI insights are unavailable right now.</p>
      <p>
        <button type="button" className="btn btn-secondary" disabled={retrying} onClick={onRetry}>
          {retrying ? "Checking…" : "Try again"}
        </button>
      </p>
    </section>
  );
}

function AutomaticAiInsights({ dashboard, actor, dateRange, teamFilter, stageLabels }: {
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
    // Mounted only after the service confirmed "auto" (see AiInsights).
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
