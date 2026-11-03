import type { ReactNode } from "react";
import { Link } from "react-router";

import { paths } from "../../navigation";
import {
  GTC_CLASSIFICATION,
  GTC_FOLLOW_UPS,
  GTC_KPIS,
  GTC_RESIDENCY,
  MOCK_DATA_AS_OF,
  REVIEW_CYCLE,
  REVIEW_KPIS,
  REVIEW_RISK_TIERS,
  REVIEW_ROWS,
  REVIEWS_DUE_BY_MONTH,
  type GtcFollowUpStatus,
  type MockBar,
  type MockKpi,
  type ReviewStatus,
} from "./mockDashboardData";
import "./mockDashboards.css";

const MOCK_CATEGORIES = [
  {
    n: "02",
    title: "Global Tax Compliance (GTC)",
    description: "FATCA and CRS tax residency self-certification, indicia checks and TIN capture",
    to: paths.gtcDashboard,
  },
  {
    n: "03",
    title: "Periodic Review / KYC Refresh",
    description: "Risk-based review cycles, upcoming and overdue customer reviews",
    to: paths.periodicReviewDashboard,
  },
];

/** Landing-page cards for the two mock categories; shown after the Onboarding card. */
export function MockCategoryCards() {
  return <>
    {MOCK_CATEGORIES.map((category) => (
      <Link key={category.n} className="card category-card category-card--mock" to={category.to}>
        <div className="category-card-top"><span className="dashboard-kicker">{category.n}</span><span className="tag tag-neutral">Mock data</span></div>
        <h2>{category.title}</h2>
        <p className="text-muted">{category.description}</p>
        <div className="category-card-foot">
          <span className="text-muted">Mock data</span>
          <span className="category-card-cta">View dashboard →</span>
        </div>
      </Link>
    ))}
  </>;
}

function MockDashboardPage({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="ds-root ds-page dashboard-page">
      <header className="ds-page-header dashboard-header">
        <div>
          <Link className="mock-dashboard-back" to={paths.dashboard}>← All categories</Link>
          <div className="mock-dashboard-title"><h1>{title}</h1><span className="tag tag-neutral">Mock data</span></div>
        </div>
        <div className="dashboard-as-of"><span>Data as of</span><strong>{MOCK_DATA_AS_OF}</strong><span>· Fixed sample figures for demonstration</span></div>
      </header>
      {children}
    </section>
  );
}

function KpiRow({ kpis, label }: { kpis: MockKpi[]; label: string }) {
  return (
    <div className="dashboard-kpis dashboard-kpis--5" aria-label={label}>
      {kpis.map((kpi) => (
        <article key={kpi.label} className={kpi.warn ? "dashboard-kpi dashboard-kpi--warn" : "dashboard-kpi"}>
          <span>{kpi.label}</span><strong>{kpi.value}</strong>
          {kpi.note && <p className="text-muted">{kpi.note}</p>}
        </article>
      ))}
    </div>
  );
}

function HorizontalBars({ title, bars, footnote }: { title: string; bars: MockBar[]; footnote?: string }) {
  const max = Math.max(1, ...bars.map((bar) => bar.value));
  const total = bars.reduce((sum, bar) => sum + bar.value, 0);
  return (
    <article className="card" style={{ flex: 1 }}>
      <h2>{title} · {total}</h2>
      <div className="dashboard-bars">
        {bars.map((bar) => (
          <div className="dashboard-bar" key={bar.label}>
            <span>{bar.label}</span>
            <div><i style={{ width: `${(bar.value / max) * 100}%` }} /></div>
            <strong>{bar.value}</strong>
            {bar.note && <p className="mock-bar-note">{bar.note}</p>}
          </div>
        ))}
      </div>
      {footnote && <p className="text-muted" style={{ fontSize: 10.5, margin: "12px 0 0" }}>{footnote}</p>}
    </article>
  );
}

function ColumnChart({ title, bars, footnote }: { title: string; bars: MockBar[]; footnote: string }) {
  const max = Math.max(1, ...bars.map((bar) => bar.value));
  return (
    <article className="card mock-review-chart" style={{ flex: 1.25 }}>
      <h2>{title}</h2>
      <div className="weekly-chart">
        {bars.map((bar) => (
          <div className="weekly-chart-bar" key={bar.label} style={{ height: `${Math.max(4, (bar.value / max) * 100)}%` }}>
            <span className="weekly-chart-count">{bar.value}</span>
            <div className="weekly-chart-seg" style={{ height: "100%" }} title={`${bar.label}: ${bar.value}`} />
          </div>
        ))}
      </div>
      <div className="weekly-chart-axis">{bars.map((bar) => <span key={bar.label} className="weekly-chart-label">{bar.label}</span>)}</div>
      <p className="text-muted" style={{ fontSize: 10.5, margin: "8px 0 0" }}>{footnote}</p>
    </article>
  );
}

const GTC_STATUS_TAG: Record<GtcFollowUpStatus, string> = {
  "Awaiting client": "tag tag-warn",
  "Reminder sent": "tag tag-warn",
  "Under review": "tag tag-accent",
};

export function GtcDashboard() {
  return (
    <MockDashboardPage title="Global Tax Compliance Dashboard">
      <KpiRow kpis={GTC_KPIS} label="Global Tax Compliance totals" />
      <div className="dashboard-grid dashboard-grid--distributions">
        <HorizontalBars title="Tax residency by country" bars={GTC_RESIDENCY} footnote="Declared tax residency on the self-certification, or registry country where pending." />
        <HorizontalBars title="Classification split" bars={GTC_CLASSIFICATION} footnote="FATCA and CRS reporting classification for cases in scope." />
      </div>
      <article className="card">
        <h2>Cases needing follow-up</h2>
        <div className="table-scroll">
          <table className="table">
            <thead>
              <tr><th scope="col">Entity</th><th scope="col">Issue</th><th scope="col">Jurisdiction</th><th scope="col">Status</th><th scope="col" style={{ textAlign: "right" }}>Days open</th></tr>
            </thead>
            <tbody>
              {GTC_FOLLOW_UPS.map((row) => (
                <tr key={row.entity}>
                  <td><strong>{row.entity}</strong></td>
                  <td>{row.issue}</td>
                  <td>{row.jurisdiction}</td>
                  <td><span className={GTC_STATUS_TAG[row.status]}>{row.status}</span></td>
                  <td style={{ textAlign: "right" }}>{row.daysOpen}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>
    </MockDashboardPage>
  );
}

const REVIEW_STATUS_TAG: Record<ReviewStatus, string> = {
  Overdue: "tag tag-warn",
  "Due soon": "tag tag-accent",
  "On track": "tag tag-neutral",
};

export function PeriodicReviewDashboard() {
  return (
    <MockDashboardPage title="Periodic Review / KYC Refresh Dashboard">
      <KpiRow kpis={REVIEW_KPIS} label="Periodic review totals" />
      <div className="dashboard-grid dashboard-grid--distributions">
        <ColumnChart title="Reviews due by month" bars={REVIEWS_DUE_BY_MONTH} footnote="Scheduled periodic reviews by due month, November to April." />
        <HorizontalBars
          title="Customers by risk tier"
          bars={REVIEW_RISK_TIERS}
          footnote={`Review cycle: High = ${REVIEW_CYCLE.High}, Medium = ${REVIEW_CYCLE.Medium}, Low = ${REVIEW_CYCLE.Low}.`}
        />
      </div>
      <article className="card">
        <h2>Upcoming and overdue reviews</h2>
        <div className="table-scroll">
          <table className="table">
            <thead>
              <tr><th scope="col">Entity</th><th scope="col">Risk tier</th><th scope="col">Last review</th><th scope="col">Next review due</th><th scope="col">Status</th></tr>
            </thead>
            <tbody>
              {REVIEW_ROWS.map((row) => (
                <tr key={row.entity}>
                  <td><strong>{row.entity}</strong></td>
                  <td>{row.riskTier}</td>
                  <td>{row.lastReview}</td>
                  <td>{row.status === "Overdue" ? <strong style={{ color: "#8c3a2e" }}>{row.nextDue}</strong> : row.nextDue}</td>
                  <td><span className={REVIEW_STATUS_TAG[row.status]}>{row.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>
    </MockDashboardPage>
  );
}
