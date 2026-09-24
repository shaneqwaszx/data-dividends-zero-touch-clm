import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { intelligenceQueryOptions } from "./caseQueries";
import IntelligencePanel from "./pages/IntelligencePanel";
import type { OnboardingIntelligenceRecord } from "./types";

const CASE_ID = "00000000-0000-4000-8000-000000000901";

const record: OnboardingIntelligenceRecord = {
  case_id: CASE_ID,
  version: 1,
  input_fingerprint: `sha256:${"a".repeat(64)}`,
  policy_catalogue_version: 2,
  model_bundle_version: "onboarding-intelligence-v1",
  entity_resolution: {
    outcome: "REVIEW_REQUIRED",
    selected_candidate_id: null,
    source_reference: "CASE_CANONICAL_ENTITY",
    candidates: [{
      candidate_id: "SYNTHETIC-AMBIGUOUS-1",
      probability: "0.910000",
      assessed_weight: "0.450000",
      corroborating_feature_count: 3,
      features: [],
      top_contributing_features: ["LEGAL_NAME_SIMILARITY", "REGISTERED_ADDRESS_SIMILARITY"],
      source_reference: "SYNTHETIC_DEMO_CANDIDATE",
    }],
    reason_codes: ["AMBIGUOUS_TOP_CANDIDATES"],
    model_version: "entity-resolution-linear-v1",
    assistance_label: "ML_ASSISTED",
    disclaimer: "NOT_IDENTITY_AUTHORITY",
  },
  ubo_advice: [{
    party_id: "PERSON-1",
    probability: "0.800000",
    label: "LIKELY_UBO",
    authoritative_ownership_percent: "40",
    reason_codes: ["CONSUMES_DETERMINISTIC_OWNERSHIP_RESULT"],
    model_version: "ubo-advisory-linear-v1",
    assistance_label: "ML_ASSISTED",
    disclaimer: "NOT_LEGAL_UBO_DETERMINATION",
  }],
  mock_risk: {
    score: 65,
    band: "HIGH",
    signal_assessments: { entity_resolution: "35", document: "30", ownership: "NOT_ASSESSED" },
    reason_codes: ["ENTITY_REVIEW_REQUIRED"],
    not_assessed_signals: ["pep", "sanctions", "adverse_media"],
    model_version: "mock-advisory-risk-rules-v1",
    label: "MOCK_ADVISORY_RISK",
    disclaimer: "NOT_COMPLIANCE_DECISION",
    blocks_readiness: false,
  },
  evaluated_at: "2026-09-23T00:00:00Z",
};

afterEach(() => vi.restoreAllMocks());

describe("pre-Phase 22 intelligence projection", () => {
  it("keeps query identity user and case scoped and forwards cancellation", async () => {
    const signal = new AbortController().signal;
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(record), { status: 200, headers: { "Content-Type": "application/json" } }),
    );
    const first = intelligenceQueryOptions("maya-lim", CASE_ID);
    const second = intelligenceQueryOptions("sophia-ng", CASE_ID);

    expect(first.queryKey).not.toEqual(second.queryKey);
    await first.queryFn({ signal });

    expect(fetchMock).toHaveBeenCalledWith(
      `/api/clm/zero-touch/cases/${CASE_ID}/intelligence`,
      expect.objectContaining({ signal }),
    );
  });

  it("renders permanent advisory labels and explicit unassessed signals", () => {
    const html = renderToStaticMarkup(<IntelligencePanel record={record} />);

    expect(html).toContain("ML assisted");
    expect(html).toContain("Not legal UBO determination");
    expect(html).toContain("Mock advisory risk");
    expect(html).toContain("Not compliance decision");
    expect(html).toContain("pep");
    expect(html).toContain("SYNTHETIC-AMBIGUOUS-1");
    expect(html).toContain("0.910000");
    expect(html).toContain("Legal name similarity");
    expect(html).not.toContain("MERLION CIRCULAR LABS");
  });
});
