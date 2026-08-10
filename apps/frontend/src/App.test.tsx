import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import App, { CaseSummary, SimulationBanner } from "./App";
import { createOnboardingCase, fetchMockScenarios } from "./api";
import type { OnboardingCase, WorkflowState } from "./types";

const timestamp = "2026-08-10T02:00:00Z";

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
      registered_address:
        state === "REVIEW_REQUIRED"
          ? null
          : {
              address_line_1: "18 INNOVATION WAY",
              address_line_2: "#04-01",
              postal_code: "018956",
              country_code: "SG",
            },
      source: {
        source_system: "ACRA",
        environment: "MOCK",
        retrieved_at: timestamp,
      },
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
    error:
      state === "COMPLETED"
        ? null
        : {
            code: state === "FAILED" ? "ACRA_ENTITY_NOT_FOUND" : "CANONICAL_DATA_INCOMPLETE",
            message: state === "FAILED" ? "Synthetic entity not found." : "Human review required.",
          },
    created_at: timestamp,
    updated_at: timestamp,
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Phase 01 onboarding UI", () => {
  it("clearly labels all data and systems as simulated mocks", () => {
    const markup = renderToStaticMarkup(<App />);

    expect(markup).toContain("Loading backend connector profile");
    expect(markup).toContain("Start onboarding");
  });

  it("renders backend-provided simulation metadata", () => {
    const markup = renderToStaticMarkup(
      <SimulationBanner
        profile={{
          is_simulated: true,
          registry_system: "ACRA",
          registry_environment: "MOCK",
          target_system: "GOLDTIER",
          target_environment: "MOCK",
        }}
      />,
    );

    expect(markup).toContain("ACRA Mock | GoldTier Mock");
    expect(markup).toContain("Registry access is backend-managed");
  });

  it("loads simulation metadata through the backend discovery contract", async () => {
    const discovery = {
      simulation: {
        is_simulated: true as const,
        registry_system: "ACRA" as const,
        registry_environment: "MOCK" as const,
        target_system: "GOLDTIER" as const,
        target_environment: "MOCK" as const,
      },
      scenarios: [],
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(discovery), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    const result = await fetchMockScenarios();

    expect(result.simulation.registry_system).toBe("ACRA");
    expect(result.simulation.registry_environment).toBe("MOCK");
  });

  it("starts the onboarding happy path through the application-facing API", async () => {
    const completed = makeCase("COMPLETED");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(completed), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await createOnboardingCase("202400001A");

    expect(result.state).toBe("COMPLETED");
    expect(fetchMock).toHaveBeenCalledWith("/api/onboarding/cases", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ uen: "202400001A" }),
    });
  });

  it("renders every happy-path workflow stage and the mock GoldTier result", () => {
    const markup = renderToStaticMarkup(<CaseSummary caseData={makeCase("COMPLETED")} />);

    for (const stage of [
      "REQUESTED",
      "REGISTRY_FETCHED",
      "VALIDATED",
      "GT_SEARCHED",
      "GT_SHELL_CREATED",
      "GT_POLICY_CREATED",
      "GT_ENRICHED",
      "COMPLETED",
    ]) {
      expect(markup).toContain(stage);
    }
    expect(markup).toContain("GT-MOCK-00000001");
    expect(markup).toContain("MERLION CIRCULAR LABS PTE. LTD.");
    expect(markup).toContain("ACRA Mock");
    expect(markup).toContain("2024-01-02");
    expect(markup).toContain("LIVE");
  });

  it("renders ACRA Sandbox without exposing private configuration", () => {
    const markup = renderToStaticMarkup(
      <SimulationBanner
        profile={{
          is_simulated: true,
          registry_system: "ACRA",
          registry_environment: "SANDBOX",
          target_system: "GOLDTIER",
          target_environment: "MOCK",
        }}
      />,
    );

    expect(markup).toContain("ACRA Sandbox | GoldTier Mock");
    expect(markup.toLowerCase()).not.toContain("credential");
    expect(markup.toLowerCase()).not.toContain("authorization");
  });

  it.each([
    ["REVIEW_REQUIRED", "CANONICAL_DATA_INCOMPLETE", "Human review required."],
    ["FAILED", "ACRA_ENTITY_NOT_FOUND", "Synthetic entity not found."],
  ] as const)("renders the %s outcome", (state, code, message) => {
    const markup = renderToStaticMarkup(<CaseSummary caseData={makeCase(state)} />);

    expect(markup).toContain(state);
    expect(markup).toContain(code);
    expect(markup).toContain(message);
    expect(markup).toContain("No mock GoldTier customer was created.");
  });
});
