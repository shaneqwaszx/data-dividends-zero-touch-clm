// Fixed mock figures for the GTC and Periodic Review dashboards.
// Frontend-only demo data: no API, storage or randomness, so every viewer sees the same values.

export const MOCK_DATA_AS_OF = "2 Nov 2026";

export interface MockKpi {
  label: string;
  value: number;
  note?: string;
  warn?: boolean;
}

export interface MockBar {
  label: string;
  value: number;
  note?: string;
}

// ---- Global Tax Compliance (GTC) ----

export const GTC_KPIS: MockKpi[] = [
  { label: "Cases in scope", value: 48 },
  { label: "Self-certification received", value: 41 },
  { label: "Pending self-certification", value: 7, warn: true },
  { label: "Indicia conflicts", value: 6, warn: true },
  { label: "Missing TINs", value: 5, warn: true },
];

export const GTC_CLASSIFICATION: MockBar[] = [
  { label: "Not reportable", value: 29 },
  { label: "CRS reportable", value: 12 },
  { label: "FATCA reportable", value: 7 },
];

export const GTC_RESIDENCY: MockBar[] = [
  { label: "Singapore", value: 26 },
  { label: "Hong Kong", value: 8 },
  { label: "Malaysia", value: 6 },
  { label: "Australia", value: 4 },
  { label: "United States", value: 3 },
  { label: "Other", value: 1 },
];

export type GtcFollowUpStatus = "Awaiting client" | "Under review" | "Reminder sent";

export interface GtcFollowUpRow {
  entity: string;
  issue: string;
  jurisdiction: string;
  status: GtcFollowUpStatus;
  daysOpen: number;
}

export const GTC_FOLLOW_UPS: GtcFollowUpRow[] = [
  { entity: "Meridian Pacific Trading Pte. Ltd.", issue: "Mailing address in Hong Kong differs from declared Singapore tax residency", jurisdiction: "Singapore / Hong Kong", status: "Under review", daysOpen: 12 },
  { entity: "Blue Lantern Ventures Sdn. Bhd.", issue: "TIN missing for declared Malaysia tax residency", jurisdiction: "Malaysia", status: "Awaiting client", daysOpen: 9 },
  { entity: "Coralstone Properties Pte. Ltd.", issue: "Self-certification not received", jurisdiction: "Singapore", status: "Reminder sent", daysOpen: 21 },
  { entity: "Northgate Precision Pty Ltd", issue: "US telephone number on file; FATCA status not yet confirmed", jurisdiction: "Australia / United States", status: "Under review", daysOpen: 6 },
  { entity: "Jadeport Investments Limited", issue: "Self-certification not received", jurisdiction: "Hong Kong", status: "Awaiting client", daysOpen: 15 },
];

// ---- Periodic Review / KYC Refresh ----

export const REVIEW_KPIS: MockKpi[] = [
  { label: "Customers under periodic review", value: 120 },
  { label: "Overdue", value: 9, warn: true },
  { label: "Due in 30 days", value: 14 },
  { label: "Due in 90 days", value: 31 },
  { label: "Completed this quarter", value: 22 },
];

export type RiskTier = "High" | "Medium" | "Low";

export const REVIEW_CYCLE: Record<RiskTier, string> = {
  High: "annually",
  Medium: "every 2 to 3 years",
  Low: "every 3 to 5 years",
};

export const REVIEW_RISK_TIERS: MockBar[] = [
  { label: "High", value: 18, note: `Reviewed ${REVIEW_CYCLE.High}` },
  { label: "Medium", value: 52, note: `Reviewed ${REVIEW_CYCLE.Medium}` },
  { label: "Low", value: 50, note: `Reviewed ${REVIEW_CYCLE.Low}` },
];

export const REVIEWS_DUE_BY_MONTH: MockBar[] = [
  { label: "Nov", value: 14 },
  { label: "Dec", value: 11 },
  { label: "Jan", value: 6 },
  { label: "Feb", value: 8 },
  { label: "Mar", value: 5 },
  { label: "Apr", value: 7 },
];

export type ReviewStatus = "Overdue" | "Due soon" | "On track";

export interface ReviewRow {
  entity: string;
  riskTier: RiskTier;
  lastReview: string;
  nextDue: string;
  status: ReviewStatus;
}

// Next-due dates follow the tier cycle from the last review; status is relative to MOCK_DATA_AS_OF.
export const REVIEW_ROWS: ReviewRow[] = [
  { entity: "Halcyon Maritime Holdings Pte. Ltd.", riskTier: "High", lastReview: "15 Oct 2025", nextDue: "15 Oct 2026", status: "Overdue" },
  { entity: "Verdant Ridge Capital Pte. Ltd.", riskTier: "Medium", lastReview: "20 Sep 2023", nextDue: "20 Sep 2026", status: "Overdue" },
  { entity: "Lumina Biotech Asia Pte. Ltd.", riskTier: "High", lastReview: "24 Nov 2025", nextDue: "24 Nov 2026", status: "Due soon" },
  { entity: "Straits Harbour Logistics Pte. Ltd.", riskTier: "Medium", lastReview: "28 Nov 2024", nextDue: "28 Nov 2026", status: "Due soon" },
  { entity: "Kestrel Engineering Services Pte. Ltd.", riskTier: "Low", lastReview: "15 Apr 2024", nextDue: "15 Apr 2027", status: "On track" },
  { entity: "Orchid Bay Trading Co. Pte. Ltd.", riskTier: "Low", lastReview: "12 Feb 2022", nextDue: "12 Feb 2027", status: "On track" },
];

// ---- Onboarding dashboard: "Onboarded per week" chart ----
// Fixed mock weeks shown to every viewer instead of live counts. Illustrative only: Australia
// figures are mock data, not completions from an implemented registry route.

export const MOCK_WEEKLY_ONBOARDED: Array<{
  week_start: string;
  by_jurisdiction: { SG: number; AU?: number };
  unresolved_count: number;
}> = [
  { week_start: "2026-09-07", by_jurisdiction: { SG: 4, AU: 1 }, unresolved_count: 0 },
  { week_start: "2026-09-14", by_jurisdiction: { SG: 6, AU: 2 }, unresolved_count: 0 },
  { week_start: "2026-09-21", by_jurisdiction: { SG: 5, AU: 1 }, unresolved_count: 0 },
  { week_start: "2026-09-28", by_jurisdiction: { SG: 8, AU: 3 }, unresolved_count: 0 },
  { week_start: "2026-10-05", by_jurisdiction: { SG: 7, AU: 2 }, unresolved_count: 0 },
  { week_start: "2026-10-12", by_jurisdiction: { SG: 9, AU: 2 }, unresolved_count: 0 },
  { week_start: "2026-10-19", by_jurisdiction: { SG: 6, AU: 3 }, unresolved_count: 0 },
  { week_start: "2026-10-26", by_jurisdiction: { SG: 10, AU: 4 }, unresolved_count: 0 },
];
