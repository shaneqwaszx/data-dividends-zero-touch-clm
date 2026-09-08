import { useEffect, useState } from "react";

import { fetchDashboard } from "../api";
import { formatDateNoSeconds } from "../shared";
import type { AuthenticatedProfile, DashboardCaseItem, DashboardSnapshot } from "../types";

export function CaseTable({
  cases,
  actor,
  onOpenCase,
  empty,
}: {
  cases: DashboardCaseItem[];
  actor: AuthenticatedProfile;
  onOpenCase: (caseId: string) => void;
  empty: string;
}) {
  if (cases.length === 0) return <p className="empty-copy">{empty}</p>;
  return (
    <div className="table-scroll">
      <table className="table dashboard-table">
        <thead><tr><th>Client / UEN</th>{actor.role === "DIRECTOR" && <th>Team</th>}<th>Priority</th><th>Status</th><th>Updated</th><th>Action</th></tr></thead>
        <tbody>
          {cases.map((item) => (
            <tr key={item.case_id}>
              <td><strong>{item.legal_name ?? item.requested_uen}</strong><span className="cell-note">{item.requested_uen}</span></td>
              {actor.role === "DIRECTOR" && <td>{item.team_display_name ?? "Unassigned legacy case"}</td>}
              <td>{item.priority ?? "Unset"}</td>
              <td>{item.status.replaceAll("_", " ")}</td>
              <td>{formatDateNoSeconds(item.completed_at ?? item.updated_at)}</td>
              <td><button className="btn btn-ghost" type="button" onClick={() => onOpenCase(item.case_id)}>Open</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function DashboardView({
  actor,
  dashboard,
  onOpenCase,
  onRefresh,
}: {
  actor: AuthenticatedProfile;
  dashboard: DashboardSnapshot;
  onOpenCase: (caseId: string) => void;
  onRefresh: () => void;
}) {
  const totals = dashboard.totals;
  const kpis = [
    [totals.total_cases, "Total cases"],
    [totals.completed_cases, "Completed"],
    [`${(totals.completion_rate * 100).toFixed(0)}%`, "Completion rate"],
    [totals.non_completed_cases, "Active / Non-completed"],
    [totals.prioritised_cases, "Prioritised"],
    [totals.unprioritised_cases, "Unprioritised"],
  ];
  const trendMax = Math.max(1, ...dashboard.historical_trend.flatMap((item) => [item.created_count, item.completed_count]));

  return (
    <section className="ds-root ds-page dashboard-page">
      <header className="ds-page-header dashboard-header">
        <div><p className="section-label">Historical CLM overview</p><h1>Dashboard</h1><p>{dashboard.scope.team_display_name ?? "Global / cross-team"} · {dashboard.scope.client_scope_label}</p></div>
        <div className="dashboard-as-of"><span>Data as of</span><strong>{formatDateNoSeconds(dashboard.data_as_of)}</strong><button className="btn btn-ghost" type="button" onClick={onRefresh}>Refresh</button></div>
      </header>

      <div className="dashboard-kpis" aria-label="Dashboard totals">
        {kpis.map(([value, label]) => <article className="card dashboard-kpi" key={label}><strong>{value}</strong><span>{label}</span></article>)}
      </div>

      {totals.total_cases === 0 && <div className="ds-banner">No onboarding cases are available for your current scope.</div>}

      <div className="dashboard-grid dashboard-grid--distributions">
        <article className="card"><p className="section-label">Exact workflow states</p><h2>Status overview</h2><div className="dashboard-bars">{dashboard.status_breakdown.map((item) => <div className="dashboard-bar" key={item.status}><span>{item.status.replaceAll("_", " ")}</span><div><i style={{ width: `${totals.total_cases ? (item.count / totals.total_cases) * 100 : 0}%` }} /></div><strong>{item.count}</strong></div>)}</div></article>
        <article className="card"><p className="section-label">Canonical priority</p><h2>Priority distribution</h2><div className="priority-distribution">{dashboard.priority_breakdown.map((item) => <div key={item.priority ?? "unset"}><span>{item.priority ?? "Unset"}</span><strong>{item.count}</strong></div>)}</div></article>
      </div>

      <article className="card"><p className="section-label">Authorized portfolio</p><h2>Team portfolio</h2><div className="team-portfolio">{dashboard.team_breakdown.map((item) => <div key={item.team_id}><span>{item.team_display_name}</span><small>{item.client_scope_label}</small><strong>{item.count}</strong></div>)}</div></article>

      <article className="card"><p className="section-label">Canonical priority order</p><h2>Highest-priority active cases</h2><CaseTable cases={dashboard.top_active_cases} actor={actor} onOpenCase={onOpenCase} empty="No active cases are available for your current scope." /></article>

      <article className="card"><p className="section-label">Latest authorized history</p><h2>Recent cases</h2><CaseTable cases={dashboard.recent_cases} actor={actor} onOpenCase={onOpenCase} empty="No recent cases are available for your current scope." /></article>

      {dashboard.historical_trend.length > 0 && <article className="card"><p className="section-label">30-day UTC history</p><h2>Created and completed</h2><div className="dashboard-trend" role="list" aria-label="30-day case trend">{dashboard.historical_trend.map((item) => <div key={item.day} role="listitem" title={`${item.day}: ${item.created_count} created, ${item.completed_count} completed`}><span className="trend-bars"><i className="trend-created" style={{ height: `${(item.created_count / trendMax) * 100}%` }} /><i className="trend-completed" style={{ height: `${(item.completed_count / trendMax) * 100}%` }} /></span><time dateTime={item.day}>{item.day.slice(5)}</time><span className="sr-only">{item.created_count} created, {item.completed_count} completed</span></div>)}</div><p className="control-help">Factual case counts only; completion rate is not a regulatory or SLA KPI.</p></article>}
    </section>
  );
}

export default function Dashboard({
  actor,
  onOpenCase,
}: {
  actor: AuthenticatedProfile;
  onOpenCase: (caseId: string) => void;
}) {
  const [dashboard, setDashboard] = useState<DashboardSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setDashboard(await fetchDashboard());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Dashboard data is unavailable.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  if (loading) return <section className="ds-root ds-page"><p className="text-muted">Loading dashboard…</p></section>;
  if (error) return <section className="ds-root ds-page"><div className="ds-banner ds-banner-warn" role="alert">{error}</div><button className="btn btn-secondary" type="button" onClick={() => void load()}>Try again</button></section>;
  if (!dashboard) return null;

  return <DashboardView actor={actor} dashboard={dashboard} onOpenCase={onOpenCase} onRefresh={() => void load()} />;
}
