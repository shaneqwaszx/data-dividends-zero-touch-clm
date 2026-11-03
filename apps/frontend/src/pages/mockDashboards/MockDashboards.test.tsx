import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";

import {
  GTC_CLASSIFICATION,
  GTC_FOLLOW_UPS,
  GTC_KPIS,
  GTC_RESIDENCY,
  REVIEW_KPIS,
  REVIEW_RISK_TIERS,
  REVIEW_ROWS,
  REVIEWS_DUE_BY_MONTH,
} from "./mockDashboardData";
import { GtcDashboard, MockCategoryCards, PeriodicReviewDashboard } from "./MockDashboards";

const sum = (values: Array<{ value: number }>) => values.reduce((total, item) => total + item.value, 0);
const kpi = (kpis: Array<{ label: string; value: number }>, label: string) => kpis.find((item) => item.label === label)!.value;
const render = (node: JSX.Element) => renderToStaticMarkup(<MemoryRouter>{node}</MemoryRouter>);

describe("mock dashboard data", () => {
  it("keeps the GTC figures internally consistent", () => {
    const inScope = kpi(GTC_KPIS, "Cases in scope");
    expect(inScope).toBe(48);
    expect(kpi(GTC_KPIS, "Self-certification received") + kpi(GTC_KPIS, "Pending self-certification")).toBe(inScope);
    expect(sum(GTC_CLASSIFICATION)).toBe(inScope);
    expect(sum(GTC_RESIDENCY)).toBe(inScope);
    expect(GTC_FOLLOW_UPS).toHaveLength(5);
  });

  it("keeps the periodic review figures internally consistent", () => {
    expect(sum(REVIEW_RISK_TIERS)).toBe(kpi(REVIEW_KPIS, "Customers under periodic review"));
    expect(REVIEWS_DUE_BY_MONTH[0].value).toBe(kpi(REVIEW_KPIS, "Due in 30 days"));
    expect(sum(REVIEWS_DUE_BY_MONTH.slice(0, 3))).toBe(kpi(REVIEW_KPIS, "Due in 90 days"));
    expect(REVIEW_ROWS).toHaveLength(6);
  });

  it("derives each next-review date from the risk-tier cycle and flags overdue rows", () => {
    const asOf = Date.parse("2 Nov 2026 UTC");
    const allowedYears = { High: [1], Medium: [2, 3], Low: [3, 4, 5] } as const;
    for (const row of REVIEW_ROWS) {
      const last = new Date(`${row.lastReview} UTC`);
      const next = new Date(`${row.nextDue} UTC`);
      expect(next.getUTCDate()).toBe(last.getUTCDate());
      expect(next.getUTCMonth()).toBe(last.getUTCMonth());
      expect(allowedYears[row.riskTier]).toContain(next.getUTCFullYear() - last.getUTCFullYear());
      const daysToDue = (next.getTime() - asOf) / 86_400_000;
      const expected = daysToDue < 0 ? "Overdue" : daysToDue <= 30 ? "Due soon" : "On track";
      expect(row.status).toBe(expected);
    }
  });
});

describe("mock dashboards", () => {
  it("renders the two category cards linking to their own dashboards", () => {
    const markup = render(<MockCategoryCards />);
    expect(markup).toContain('href="/dashboard/gtc"');
    expect(markup).toContain('href="/dashboard/periodic-review"');
    expect(markup).toContain("FATCA and CRS tax residency self-certification, indicia checks and TIN capture");
    expect(markup).toContain("Risk-based review cycles, upcoming and overdue customer reviews");
    expect(markup).toContain("View dashboard");
    expect(markup).not.toContain("category-card--live");
  });

  it.each([
    ["GTC", <GtcDashboard />, "Cases needing follow-up"],
    ["Periodic Review", <PeriodicReviewDashboard />, "Upcoming and overdue reviews"],
  ])("labels the %s dashboard as mock data with a back link", (_name, node, tableTitle) => {
    const markup = render(node);
    expect(markup).toContain("Mock data");
    expect(markup).toContain('href="/dashboard"');
    expect(markup).toContain("All categories");
    expect(markup).toContain(tableTitle);
  });
});
