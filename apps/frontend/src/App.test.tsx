import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import App, { CaseSummary, DocumentReviewSummary, SimulationBanner } from "./App";
import {
  createOnboardingCase,
  fetchDocuments,
  fetchMockScenarios,
  fetchOnboardingCase,
  reviewDocument,
  uploadDocument,
} from "./api";
import type { DocumentProcessingRecord, OnboardingCase, WorkflowState } from "./types";

const timestamp = "2026-08-10T02:00:00Z";

function makeDocument(state: "REVIEW_REQUIRED" | "REVIEWED" = "REVIEW_REQUIRED") {
  const record: DocumentProcessingRecord = {
    case_id: "00000000-0000-4000-8000-000000000001",
    document_id: "00000000-0000-4000-8000-000000000010",
    correlation_id: "00000000-0000-4000-8000-000000000011",
    display_name: "synthetic-profile.pdf",
    media_type: "application/pdf",
    profile: "PROVISIONAL_CORPORATE",
    provider_environment: "MOCK",
    state,
    fields: [
      {
        field_key: "legal_name",
        original_extracted_value: "Synthetic Suggested Name",
        normalized_value: "SYNTHETIC SUGGESTED NAME",
        confidence: 0.61,
        provenance: {
          provider: "MOCK_IDP",
          environment: "MOCK",
          page_number: 1,
          source_reference: "SYNTHETIC_PAGE_1",
        },
        canonical_value: "SYNTHETIC CANONICAL NAME",
        comparison_status: "MISMATCH",
        review_status: state === "REVIEWED" ? "CORRECTED" : "PENDING",
        reviewed_value: state === "REVIEWED" ? "Human Corrected Name" : null,
        reviewed_at: state === "REVIEWED" ? timestamp : null,
        review_note: state === "REVIEWED" ? "Synthetic note" : null,
      },
    ],
    events: [],
    error: null,
    created_at: timestamp,
    processed_at: timestamp,
    reviewed_at: state === "REVIEWED" ? timestamp : null,
    updated_at: timestamp,
  };
  return record;
}

function makeCase(state: WorkflowState): OnboardingCase {
  const stages: WorkflowState[] =
    state === "COMPLETED"
      ? [
          "REQUESTED",
          "REGISTRY_FETCHED",
          "VALIDATED",
          "GT_SEARCHED",
          "GT_SHELL_CREATED",
          "GT_POLICY_CREATED",
          "GT_ENRICHED",
          "COMPLETED",
        ]
      : ["REQUESTED", "REGISTRY_FETCHED", state];
  return {
    case_id: "00000000-0000-4000-8000-000000000001",
    source_case_id: "CASE-202400001A-00000000",
    correlation_id: "00000000-0000-4000-8000-000000000002",
    requested_uen: "202400001A",
    state,
    entity: {
      registration_number: "202400001A",
      legal_name: "MERLION CIRCULAR LABS PTE. LTD.",
      country_of_incorporation: "SG",
      party_type: "PRIVATE_COMPANY_LIMITED_BY_SHARES",
      registration_date: "2024-01-02",
      entity_status: "LIVE",
      registered_address: {
        address_line_1: "18 INNOVATION WAY",
        address_line_2: "#04-01",
        postal_code: "018956",
        country_code: "SG",
      },
      source: { source_system: "ACRA", environment: "MOCK", retrieved_at: timestamp },
    },
    goldtier_result:
      state === "COMPLETED"
        ? {
            party_id: "GT-MOCK-00000001",
            shell_status: "SHELL_CREATED",
            policy_id: "POL-MOCK-202400001A",
            policy_status: "POLICY_CREATED",
            amend_status: "ENRICHED",
          }
        : null,
    events: stages.map((stage, index) => ({
      sequence: index + 1,
      stage,
      outcome:
        stage === "FAILED"
          ? "FAILED"
          : stage === "REVIEW_REQUIRED"
            ? "REVIEW_REQUIRED"
            : "SUCCEEDED",
      timestamp,
      case_id: "00000000-0000-4000-8000-000000000001",
      correlation_id: "00000000-0000-4000-8000-000000000002",
      code: null,
      message: `${stage} mock event`,
    })),
    error: null,
    created_at: timestamp,
    updated_at: timestamp,
  };
}

const simulation = {
  is_simulated: true as const,
  registry_system: "ACRA" as const,
  registry_environment: "MOCK" as const,
  target_system: "GOLDTIER" as const,
  target_environment: "MOCK" as const,
  idp_system: "IDP" as const,
  idp_environment: "MOCK" as const,
  idp_review_confidence_threshold: 0.85,
};

afterEach(() => vi.unstubAllGlobals());

describe("Phase 03 onboarding and document review UI", () => {
  it("renders create and reopen case controls", () => {
    const markup = renderToStaticMarkup(<App />);
    expect(markup).toContain("Create from Singapore UEN");
    expect(markup).toContain("Open existing case ID");
    expect(markup).toContain("Loading backend connector profile");
  });

  it("renders backend-provided mock environments", () => {
    const markup = renderToStaticMarkup(<SimulationBanner profile={simulation} />);
    expect(markup).toContain("ACRA Mock | GoldTier Mock | IDP Mock");
  });

  it("loads discovery metadata including the provisional threshold", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ simulation, scenarios: [] }), { status: 200 }),
      ),
    );
    const result = await fetchMockScenarios();
    expect(result.simulation.idp_review_confidence_threshold).toBe(0.85);
  });

  it("creates and reopens cases through the backend", async () => {
    const completed = makeCase("COMPLETED");
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(completed), { status: 201 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(completed), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    expect((await createOnboardingCase("202400001A")).state).toBe("COMPLETED");
    expect((await fetchOnboardingCase(completed.case_id)).case_id).toBe(completed.case_id);
    expect(fetchMock).toHaveBeenLastCalledWith(`/api/onboarding/cases/${completed.case_id}`);
  });

  it("uploads a PDF with an explicit synthetic scenario", async () => {
    const document = makeDocument();
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(document), { status: 201 }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const file = new File(["%PDF-1.4\n%%EOF"], "synthetic.pdf", {
      type: "application/pdf",
    });

    await uploadDocument(document.case_id, file, "FIELD_MISMATCH");
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/demo/onboarding/cases/${document.case_id}/documents`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/pdf",
          "X-Document-Name": "synthetic.pdf",
          "X-Mock-IDP-Scenario": "FIELD_MISMATCH",
        },
        body: file,
      },
    );
  });

  it("lists case documents", async () => {
    const document = makeDocument();
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify([document]), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);
    expect(await fetchDocuments(document.case_id)).toEqual([document]);
  });

  it("submits a bounded corrected field decision", async () => {
    const reviewed = makeDocument("REVIEWED");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(reviewed), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await reviewDocument(
      reviewed.case_id,
      reviewed.document_id,
      "legal_name",
      "CORRECTED",
      "Human Corrected Name",
      "Synthetic note",
    );
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/onboarding/cases/${reviewed.case_id}/documents/${reviewed.document_id}/reviews`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          field_key: "legal_name",
          decision: "CORRECTED",
          corrected_value: "Human Corrected Name",
          note: "Synthetic note",
        }),
      },
    );
  });

  it("renders canonical workflow and truthful completion boundary", () => {
    const markup = renderToStaticMarkup(<CaseSummary caseData={makeCase("COMPLETED")} />);
    expect(markup).toContain("GT-MOCK-00000001");
    expect(markup).toContain("does not include document review or Ready-for-Approval");
    expect(markup).toContain("18 INNOVATION WAY, #04-01, 018956, SG");
  });

  it("makes mismatch and low confidence visually explicit with all field actions", () => {
    const markup = renderToStaticMarkup(
      <DocumentReviewSummary record={makeDocument()} threshold={0.85} onDecision={() => {}} />,
    );
    expect(markup).toContain("MISMATCH");
    expect(markup).toContain("61% confidence");
    expect(markup).toContain("IDP suggested");
    expect(markup).toContain("ACRA / canonical");
    expect(markup).toContain("MOCK_IDP / MOCK / page 1");
    expect(markup).toContain("Accept");
    expect(markup).toContain("Reject");
    expect(markup).toContain("Save correction");
  });

  it("renders original and human-reviewed values separately after correction", () => {
    const markup = renderToStaticMarkup(
      <DocumentReviewSummary record={makeDocument("REVIEWED")} />,
    );
    expect(markup).toContain("Synthetic Suggested Name");
    expect(markup).toContain("Human-confirmed value: Human Corrected Name");
    expect(markup).toContain("Original IDP suggestions remain retained");
    expect(markup).toContain("unauthenticated local POC operator");
  });

  it("labels profile and output as provisional rather than sponsor-approved OCR", () => {
    const markup = renderToStaticMarkup(<DocumentReviewSummary record={makeDocument()} />);
    expect(markup).toContain("Project-defined provisional profile");
    expect(markup).toContain("not OCR output from this file");
    expect(markup).toContain("not Delta Capita-approved fields");
  });
});
