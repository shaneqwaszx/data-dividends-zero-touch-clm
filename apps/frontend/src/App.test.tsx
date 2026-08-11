import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import App, {
  CaseSummary,
  ClmJourney,
  ClmRefreshingState,
  DocumentReviewSummary,
  OwnershipSummary,
  SimulationBanner,
  runEvidenceMutation,
} from "./App";
import {
  analyzeOwnership,
  createClmCase,
  createOnboardingCase,
  fetchDocuments,
  evaluateClmReadiness,
  fetchClmCase,
  fetchMockScenarios,
  fetchOnboardingCase,
  fetchOwnership,
  loadMockOwnership,
  reviewDocument,
  submitClmCase,
  uploadDocument,
} from "./api";
import type {
  ClmCaseSummary,
  DocumentProcessingRecord,
  OnboardingCase,
  OwnershipAnalysisRecord,
  WorkflowState,
} from "./types";

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

function makeOwnership(
  state: "ANALYZED" | "REVIEW_REQUIRED" | "FAILED" = "ANALYZED",
): OwnershipAnalysisRecord {
  const root = {
    party_id: "ROOT_ENTITY",
    display_name: "MERLION CIRCULAR LABS PTE. LTD.",
    party_type: "LEGAL_ENTITY" as const,
    registration_number: "202400001A",
    country: "SG",
  };
  const holding = {
    party_id: "HOLDING_B",
    display_name: "Harbour Holdings Pte. Ltd.",
    party_type: "LEGAL_ENTITY" as const,
    registration_number: "SYN-HOLDING_B",
    country: "SG",
  };
  const person = {
    party_id: "PERSON_C",
    display_name: "Casey Ong",
    party_type: "NATURAL_PERSON" as const,
    registration_number: null,
    country: null,
  };
  const relationships = [
    {
      relationship_id: "REL_ROOT_HOLDING",
      parent_party_id: root.party_id,
      child_party_id: holding.party_id,
      ownership_percent: "40",
      relationship_type: "OWNERSHIP" as const,
      basis: "SHARE_OWNERSHIP" as const,
      provenance: {
        provider: "MOCK_OWNERSHIP",
        environment: "MOCK" as const,
        sourced_at: timestamp,
      },
    },
    {
      relationship_id: "REL_HOLDING_C",
      parent_party_id: holding.party_id,
      child_party_id: person.party_id,
      ownership_percent: "75",
      relationship_type: "OWNERSHIP" as const,
      basis: "SHARE_OWNERSHIP" as const,
      provenance: {
        provider: "MOCK_OWNERSHIP",
        environment: "MOCK" as const,
        sourced_at: timestamp,
      },
    },
  ];
  return {
    case_id: "00000000-0000-4000-8000-000000000001",
    analysis_id: "00000000-0000-4000-8000-000000000020",
    correlation_id: "00000000-0000-4000-8000-000000000021",
    root_party_id: root.party_id,
    provider_name: "MOCK_OWNERSHIP",
    provider_environment: "MOCK",
    state,
    parties: [root, holding, person],
    relationships,
    candidates:
      state === "ANALYZED"
        ? [
            {
              party: person,
              direct_ownership_percent: "0",
              indirect_ownership_percent: "30.000",
              aggregated_ownership_percent: "30.000",
              threshold_percent: "25",
              threshold_comparator: "GREATER_THAN_OR_EQUAL_TO",
              threshold_result: "MET",
              classification: "PROVISIONAL_UBO_CANDIDATE",
              paths: [
                {
                  path_id: "REL_ROOT_HOLDING>REL_HOLDING_C",
                  edges: [
                    {
                      relationship_id: "REL_ROOT_HOLDING",
                      parent_party_id: root.party_id,
                      parent_display_name: root.display_name,
                      child_party_id: holding.party_id,
                      child_display_name: holding.display_name,
                      ownership_percent: "40",
                    },
                    {
                      relationship_id: "REL_HOLDING_C",
                      parent_party_id: holding.party_id,
                      parent_display_name: holding.display_name,
                      child_party_id: person.party_id,
                      child_display_name: person.display_name,
                      ownership_percent: "75",
                    },
                  ],
                  effective_ownership_percent: "30.000",
                  is_direct: false,
                  calculation: "40% x 75% = 30%",
                },
              ],
            },
          ]
        : [],
    issues:
      state === "REVIEW_REQUIRED"
        ? [
            {
              code: "CYCLE_DETECTED",
              message: "A circular ownership path was detected and excluded from calculation.",
              affected_party_ids: ["HOLDING_B", "ROOT_ENTITY"],
            },
          ]
        : [],
    threshold_percent: "25",
    threshold_comparator: "GREATER_THAN_OR_EQUAL_TO",
    events: [],
    error:
      state === "FAILED"
        ? {
            code: "OWNERSHIP_PROVIDER_FAILED",
            message: "Ownership source loading could not be completed.",
          }
        : null,
    created_at: timestamp,
    loaded_at: timestamp,
    analyzed_at: state === "ANALYZED" ? timestamp : null,
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
  ownership_system: "OWNERSHIP_PROVIDER" as const,
  ownership_environment: "MOCK" as const,
  ubo_ownership_threshold_percent: "25",
};

function makeClm(
  status: ClmCaseSummary["status"] = "COLLECTING_EVIDENCE",
): ClmCaseSummary {
  const ready = status === "READY_FOR_MOCK_SUBMISSION";
  const submitted = status === "MOCK_GOLDTIER_SUBMITTED";
  const caseData = makeCase(submitted ? "GT_ENRICHED" : "VALIDATED");
  return {
    case: caseData,
    orchestration_id: "00000000-0000-4000-8000-000000000030",
    correlation_id: "00000000-0000-4000-8000-000000000031",
    version: 4,
    status,
    readiness: {
      policy_version: "PHASE_05_POC_V1",
      registry: { status: "READY", reference_id: caseData.case_id },
      document: {
        status: ready || submitted ? "READY" : "MISSING",
        reference_id: ready || submitted ? "document-reference" : null,
      },
      ownership: {
        status: ready || submitted ? "READY" : "MISSING",
        reference_id: ready || submitted ? "ownership-reference" : null,
      },
      goldtier: {
        status: submitted ? "SUBMITTED" : ready ? "READY" : "BLOCKED",
        reference_id: submitted ? "submission-reference" : null,
      },
      blockers: ready || submitted ? [] : ["DOCUMENT_REQUIRED", "OWNERSHIP_REQUIRED"],
      warnings: [
        "IDP_PROFILE_PROVISIONAL",
        "UBO_POLICY_NOT_SPONSOR_CONFIRMED",
        "LIVE_HIERARCHY_UNAVAILABLE",
        "RELATED_PARTY_MAPPING_PENDING",
        "REAL_GOLDTIER_NOT_CONFIGURED",
        "READY_FOR_APPROVAL_UNAVAILABLE",
      ],
      evaluated_at: timestamp,
    },
    submission_plan: {
      environment: "MOCK",
      base_operations: [
        "searchParty",
        "createShellCustomer if NO_MATCH",
        "createPolicy",
        "amendParty",
      ],
      match_found_behavior: "REVIEW_REQUIRED_NO_WRITES",
      related_party_integration: "PENDING_SPONSOR_CONFIRMATION",
      real_ready_for_approval: "NOT_AVAILABLE",
    },
    related_party_preparation: submitted
      ? {
          provisional_candidate_count: 1,
          internal_party_ids: ["PERSON_A"],
          analysis_reference: "00000000-0000-4000-8000-000000000020",
          mapping_status: "PENDING_SPONSOR_CONFIRMATION",
          write_status: "RELATED_PARTY_WRITE_NOT_EXECUTED",
        }
      : null,
    submission: submitted
      ? {
          snapshot_id: "00000000-0000-4000-8000-000000000040",
          submission_id: "00000000-0000-4000-8000-000000000041",
          created_at: timestamp,
          readiness_policy_version: "PHASE_05_POC_V1",
          document_reference_count: 1,
          ownership_reference_id: "00000000-0000-4000-8000-000000000020",
        }
      : null,
    goldtier_result: submitted
      ? {
          party_id: "GT-MOCK-SYNTHETIC",
          shell_status: "SHELL_CREATED",
          policy_id: "POL-MOCK-SYNTHETIC",
          policy_status: "POLICY_CREATED",
          amend_status: "ENRICHED",
        }
      : null,
    timeline: [
      {
        sequence: 1,
        event_type: "CLM_CASE_CREATED",
        status: "COLLECTING_EVIDENCE",
        outcome: "SUCCEEDED",
        timestamp,
        case_id: caseData.case_id,
        orchestration_id: "00000000-0000-4000-8000-000000000030",
        correlation_id: "00000000-0000-4000-8000-000000000031",
        code: "CLM_CASE_CREATED",
        message: "Staged CLM orchestration record created.",
      },
    ],
    error: null,
    created_at: timestamp,
    updated_at: timestamp,
  };
}

afterEach(() => vi.unstubAllGlobals());

describe("Phase 04 onboarding, document review, and ownership UI", () => {
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
    expect(result.simulation.ubo_ownership_threshold_percent).toBe("25");
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
    expect(markup).toContain("underlying case state is not an approval claim");
    expect(markup).toContain("unified orchestration summary");
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

  it("loads, fetches, and analyzes a synthetic ownership record", async () => {
    const loaded = { ...makeOwnership(), state: "LOADED" as const, candidates: [] };
    const analyzed = makeOwnership();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(loaded), { status: 201 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(loaded), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(analyzed), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await loadMockOwnership(loaded.case_id, "INDIRECT_OWNER");
    await fetchOwnership(loaded.case_id);
    await analyzeOwnership(loaded.case_id);
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      `/api/demo/onboarding/cases/${loaded.case_id}/ownership/load`,
      {
        method: "POST",
        headers: { "X-Mock-Ownership-Scenario": "INDIRECT_OWNER" },
      },
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      `/api/onboarding/cases/${loaded.case_id}/ownership/analyze`,
      { method: "POST" },
    );
  });

  it("renders indirect calculation evidence and provisional candidate wording", () => {
    const markup = renderToStaticMarkup(<OwnershipSummary record={makeOwnership()} />);
    expect(markup).toContain("Casey Ong");
    expect(markup).toContain("PROVISIONAL UBO CANDIDATE");
    expect(markup).toContain("Aggregated ownership");
    expect(markup).toContain("30%");
    expect(markup).toContain("40% x 75% = 30%");
    expect(markup).toContain("PENDING Q-004");
    expect(markup).toContain("not a legal/controller");
  });

  it("renders authoritative Decimal strings exactly across threshold boundaries", () => {
    const below = makeOwnership();
    const belowCandidate = below.candidates[0];
    belowCandidate.indirect_ownership_percent = "24.9999995";
    belowCandidate.aggregated_ownership_percent = "24.9999995";
    belowCandidate.threshold_result = "NOT_MET";
    belowCandidate.classification = "BELOW_PROVISIONAL_THRESHOLD";
    belowCandidate.paths[0].effective_ownership_percent = "24.9999995";
    belowCandidate.paths[0].calculation = "49.999999% x 50% = 24.9999995%";

    const exact = makeOwnership();
    exact.candidates[0].aggregated_ownership_percent = "25.0000000";
    const above = makeOwnership();
    above.candidates[0].aggregated_ownership_percent = "25.0000001";
    const longIndirect = makeOwnership();
    longIndirect.candidates[0].indirect_ownership_percent = "12.345678901234";
    const multiplePath = makeOwnership();
    multiplePath.candidates[0].aggregated_ownership_percent = "40.000000000001";

    const belowMarkup = renderToStaticMarkup(<OwnershipSummary record={below} />);
    expect(belowMarkup).toContain("24.9999995%");
    expect(belowMarkup).toContain("49.999999% x 50% = 24.9999995%");
    expect(belowMarkup).toContain("NOT_MET");
    expect(belowMarkup).toContain("BELOW PROVISIONAL THRESHOLD");
    expect(renderToStaticMarkup(<OwnershipSummary record={exact} />)).toContain("25%");
    expect(renderToStaticMarkup(<OwnershipSummary record={above} />)).toContain(
      "25.0000001%",
    );
    expect(renderToStaticMarkup(<OwnershipSummary record={longIndirect} />)).toContain(
      "12.345678901234%",
    );
    expect(renderToStaticMarkup(<OwnershipSummary record={multiplePath} />)).toContain(
      "40.000000000001%",
    );
  });

  it("shows minimized ownership provenance without a source reference", () => {
    const markup = renderToStaticMarkup(<OwnershipSummary record={makeOwnership()} />);
    expect(markup).toContain("MOCK_OWNERSHIP / MOCK");
    expect(markup).toContain("Sourced");
    expect(markup).not.toContain("SYNTHETIC_REL_ROOT_HOLDING");
  });

  it("renders cycle review and provider failure without a false candidate", () => {
    const reviewMarkup = renderToStaticMarkup(
      <OwnershipSummary record={makeOwnership("REVIEW_REQUIRED")} />,
    );
    const failureMarkup = renderToStaticMarkup(
      <OwnershipSummary record={makeOwnership("FAILED")} />,
    );
    expect(reviewMarkup).toContain("CYCLE_DETECTED");
    expect(reviewMarkup).toContain("calculation is not definitive");
    expect(reviewMarkup).not.toContain("PROVISIONAL_UBO_CANDIDATE");
    expect(failureMarkup).toContain("OWNERSHIP_PROVIDER_FAILED");
  });
});

describe("Phase 05 unified CLM journey", () => {
  it("creates, retrieves, evaluates, and submits through the staged CLM API", async () => {
    const created = makeClm();
    const ready = makeClm("READY_FOR_MOCK_SUBMISSION");
    const submitted = makeClm("MOCK_GOLDTIER_SUBMITTED");
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(created), { status: 201 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(created), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(ready), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(submitted), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await createClmCase("202400001A");
    await fetchClmCase(created.case.case_id);
    await evaluateClmReadiness(created.case.case_id);
    await submitClmCase(created.case.case_id);

    expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/clm/cases", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ uen: "202400001A" }),
    });
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      `/api/clm/cases/${created.case.case_id}/readiness/evaluate`,
      { method: "POST" },
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      `/api/clm/cases/${created.case.case_id}/submit`,
      { method: "POST" },
    );
  });

  it("renders all stages, typed blockers, warnings, and a disabled blocked submit", () => {
    const markup = renderToStaticMarkup(<ClmJourney summary={makeClm()} />);
    expect(markup).toContain("Unified CLM journey");
    expect(markup).toContain("Registry");
    expect(markup).toContain("Document Review");
    expect(markup).toContain("Ownership &amp; UBO");
    expect(markup).toContain("Mock GoldTier");
    expect(markup).toContain("DOCUMENT_REQUIRED");
    expect(markup).toContain("REAL_GOLDTIER_NOT_CONFIGURED");
    expect(markup).toMatch(/<button[^>]*disabled=""[^>]*>Submit to Mock GoldTier<\/button>/);
  });

  it("enables submission only for backend-ready status and shows the safe plan", () => {
    const markup = renderToStaticMarkup(
      <ClmJourney summary={makeClm("READY_FOR_MOCK_SUBMISSION")} />,
    );
    expect(markup).toContain("READY_FOR_MOCK_SUBMISSION");
    expect(markup).toContain("createShellCustomer if NO_MATCH");
    expect(markup).toContain("PENDING_SPONSOR_CONFIRMATION");
    expect(markup).toContain("Real approval transition");
    expect(markup).toMatch(/<button type="button">Submit to Mock GoldTier<\/button>/);
  });

  it("shows Mock submission result and related-party write limitation truthfully", () => {
    const markup = renderToStaticMarkup(
      <ClmJourney summary={makeClm("MOCK_GOLDTIER_SUBMITTED")} />,
    );
    expect(markup).toContain("MOCK_GOLDTIER_SUBMITTED");
    expect(markup).toContain("RELATED_PARTY_WRITE_NOT_EXECUTED");
    expect(markup).toContain("1 reviewed document reference(s)");
    expect(markup).not.toContain("Real GoldTier submitted");
  });

  it("invalidates ready display immediately during a document mutation", async () => {
    let release: ((record: DocumentProcessingRecord) => void) | undefined;
    const operation = new Promise<DocumentProcessingRecord>((resolve) => {
      release = resolve;
    });
    let invalidated = false;
    let refreshed = false;

    const pending = runEvidenceMutation(
      () => { invalidated = true; },
      () => operation,
      async () => { refreshed = true; },
    );
    expect(invalidated).toBe(true);
    const refreshing = renderToStaticMarkup(<ClmRefreshingState />);
    expect(refreshing).not.toContain("READY_FOR_MOCK_SUBMISSION");
    expect(refreshing).toContain("Refreshing authoritative CLM readiness");
    expect(refreshing).toMatch(/<button[^>]*disabled=""[^>]*>Submit to Mock GoldTier/);

    release?.(makeDocument());
    await pending;
    expect(refreshed).toBe(true);
    const blocked = renderToStaticMarkup(<ClmJourney summary={makeClm()} />);
    expect(blocked).toContain("DOCUMENT_REQUIRED");
    expect(blocked).toMatch(/<button[^>]*disabled=""[^>]*>Submit to Mock GoldTier/);
  });

  it("invalidates ready display immediately during an ownership mutation", async () => {
    let release: ((record: OwnershipAnalysisRecord) => void) | undefined;
    const operation = new Promise<OwnershipAnalysisRecord>((resolve) => {
      release = resolve;
    });
    let invalidated = false;
    let refreshed = false;

    const pending = runEvidenceMutation(
      () => { invalidated = true; },
      () => operation,
      async () => { refreshed = true; },
    );
    expect(invalidated).toBe(true);
    const refreshing = renderToStaticMarkup(<ClmRefreshingState />);
    expect(refreshing).not.toContain("READY_FOR_MOCK_SUBMISSION");
    expect(refreshing).toContain("Submission remains disabled");

    release?.(makeOwnership("REVIEW_REQUIRED"));
    await pending;
    expect(refreshed).toBe(true);
    const blocked = renderToStaticMarkup(<ClmJourney summary={makeClm()} />);
    expect(blocked).toContain("OWNERSHIP_REQUIRED");
    expect(blocked).toMatch(/<button[^>]*disabled=""[^>]*>Submit to Mock GoldTier/);
  });
});
