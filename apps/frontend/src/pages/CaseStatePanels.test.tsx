import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { ProcessingNode, ZeroTouchCaseSummary } from "../types";
import {
  CompletedOverview,
  DetailedProcessingInspector,
  OnboardingProgressPanel,
  PipelineRail,
  ProcessingBlockerPanels,
  processingNodeFocusTarget,
  RegistryStatePanel,
  registryPresentation,
} from "./CaseStatePanels";

function processingNode(
  nodeId: string,
  label: string,
  status: ProcessingNode["status"],
): ProcessingNode {
  return { node_id: nodeId, label, status, children: [] };
}

function summaryWithPipeline(nodes: ProcessingNode[]): ZeroTouchCaseSummary {
  return {
    case: {
      case_id: "00000000-0000-4000-8000-000000000001",
      requested_uen: "11111999A",
      registry_route: { status: "SELECTED", jurisdiction: "SG", provider: "ACRA", decided_at: "2026-09-28T00:00:00Z" },
      registry_acquisition: null,
      entity: null,
    },
    clm: { submission_plan: { environment: "SANDBOX" } },
    automation_id: "00000000-0000-4000-8000-000000000002",
    version: 3,
    status: "RUNNING",
    current_stage: "GOLDTIER_SEARCH",
    completed_stages: ["REGISTRY"],
    active_exceptions: [],
    reconciliation: null,
    technical_failure: null,
    metrics: {
      automated_stages_completed: 1,
      human_interventions: 0,
      exceptions_resolved: 0,
      total_duration_ms: null,
      final_outcome: null,
      stage_durations_ms: {},
    },
    target_operations: [],
    stage_order_version: 2,
    processing_pipeline: nodes,
    timeline: [],
    created_at: "2026-09-28T00:00:00Z",
    updated_at: "2026-09-28T00:00:02Z",
    timing: {
      observed_at: "2026-09-28T00:00:02Z",
      case_elapsed_ms: 2000,
      time_since_last_update_ms: 0,
      automation_elapsed_ms: 2000,
      recorded_total_duration_ms: null,
    },
  } as unknown as ZeroTouchCaseSummary;
}

describe("OnboardingProgressPanel", () => {
  it("renders the backend order, current text, and accessible bounded progress before terminal state", () => {
    const summary = summaryWithPipeline([
      processingNode("INITIAL_IDENTITY", "Initial identity", "COMPLETE"),
      processingNode("GOLDTIER_SEARCH", "GoldTier search", "IN_PROGRESS"),
      processingNode("ACRA_REGISTRY", "ACRA registry", "NOT_REACHED"),
      processingNode("DOCUMENT_IDP", "Document and IDP", "NOT_REACHED"),
    ]);

    const markup = renderToStaticMarkup(<OnboardingProgressPanel summary={summary} />);

    expect(markup).toContain("Onboarding progress");
    expect(markup).toContain('role="progressbar"');
    expect(markup).toContain('aria-valuemin="0"');
    expect(markup).toContain('aria-valuemax="4"');
    expect(markup).toContain('aria-valuenow="1"');
    expect(markup).toContain("current: GoldTier search — In progress");
    const stagesMarkup = markup.slice(markup.indexOf('aria-label="Onboarding stages"'));
    expect(stagesMarkup.indexOf("Initial identity")).toBeLessThan(stagesMarkup.indexOf("GoldTier search"));
    expect(stagesMarkup.indexOf("GoldTier search")).toBeLessThan(stagesMarkup.indexOf("ACRA registry"));
    expect(markup).toContain("Last updated:");
  });

  it("shows every backend status explicitly without treating review, blocked, or failure as complete", () => {
    const statuses: ProcessingNode["status"][] = [
      "COMPLETE",
      "IN_PROGRESS",
      "SKIPPED",
      "REVIEW_REQUIRED",
      "BLOCKED",
      "FAILED",
      "NOT_REACHED",
    ];
    const summary = summaryWithPipeline(
      statuses.map((status, index) => processingNode(`NODE_${index}`, `Stage ${index}`, status)),
    );

    const markup = renderToStaticMarkup(<OnboardingProgressPanel summary={summary} />);

    for (const label of ["Complete", "In progress", "Skipped", "Review required", "Blocked", "Failed", "Not reached"]) {
      expect(markup).toContain(label);
    }
    expect(markup).toContain('aria-valuemax="7"');
    expect(markup).toContain('aria-valuenow="2"');
  });

  it("uses the earliest actionable backend node and exposes only problem stages as buttons", () => {
    const summary = summaryWithPipeline([
      processingNode("GOLDTIER_SEARCH", "GoldTier search", "FAILED"),
      processingNode("ACRA_REGISTRY", "ACRA registry", "COMPLETE"),
      processingNode("TARGET_CLASSIFICATION", "Target classification", "REVIEW_REQUIRED"),
    ]);

    const markup = renderToStaticMarkup(
      <OnboardingProgressPanel summary={summary} onStageActivate={() => undefined} />,
    );

    expect(markup).toContain("current: GoldTier search — Failed");
    expect(markup).toContain('aria-label="Open details for GoldTier search"');
    expect(markup).toContain('aria-label="Open details for Target classification"');
    expect(markup).not.toContain('aria-label="Open details for ACRA registry"');
    expect(markup.match(/<button/g)).toHaveLength(2);
  });

  it("maps only actionable stable backend nodes to specific existing panels", () => {
    expect(processingNodeFocusTarget(processingNode("GOLDTIER_SEARCH", "Search", "FAILED"))).toBe("case-search-diagnostic");
    expect(processingNodeFocusTarget(processingNode("ACRA_REGISTRY", "ACRA", "REVIEW_REQUIRED"))).toBe("case-evidence-registry");
    expect(processingNodeFocusTarget(processingNode("DOCUMENT_IDP", "Document", "BLOCKED"))).toBe("case-evidence-documents");
    expect(processingNodeFocusTarget(processingNode("TARGET_CLASSIFICATION_CLIENT_SEGMENT", "Classification", "REVIEW_REQUIRED"))).toBe(
      "case-target-classification",
    );
    expect(processingNodeFocusTarget(processingNode("GOLDTIER_TARGET", "Target", "BLOCKED"))).toBe("case-target-blocker");
    expect(processingNodeFocusTarget(processingNode("HUMAN_APPROVAL", "Approval", "REVIEW_REQUIRED"))).toBe("case-human-approval-boundary");
    expect(processingNodeFocusTarget(processingNode("ACRA_REGISTRY", "ACRA", "COMPLETE"))).toBeNull();
    expect(processingNodeFocusTarget(processingNode("UNRECOGNISED_NODE", "Unknown", "FAILED"))).toBeNull();
  });

  it("renders dedicated read-only destinations for Search, target, and approval blockers", () => {
    const search = {
      ...processingNode("GOLDTIER_SEARCH", "GoldTier search", "FAILED"),
      blocker_code: "SEARCH_TIMEOUT",
      safe_result: "Customer existence remains unresolved.",
    };
    const target = {
      ...processingNode("GOLDTIER_TARGET", "GoldTier target", "BLOCKED"),
      blocker_code: "GOLDTIER_SEARCH_FAILED",
    };
    const approval = processingNode("HUMAN_APPROVAL", "Human approval", "REVIEW_REQUIRED");

    const markup = renderToStaticMarkup(
      <ProcessingBlockerPanels summary={summaryWithPipeline([search, target, approval])} />,
    );

    expect(markup).toContain('id="case-search-diagnostic"');
    expect(markup).toContain("does not prove that the customer is absent");
    expect(markup).toContain('id="case-target-blocker"');
    expect(markup).toContain("does not provide a bypass or replay action");
    expect(markup).toContain('id="case-human-approval-boundary"');
    expect(markup).toContain("Final approval is unresolved");
  });

  it("does not advertise a stage when its otherwise-valid destination is unavailable", () => {
    const summary = summaryWithPipeline([
      processingNode("TARGET_CLASSIFICATION", "Target classification", "REVIEW_REQUIRED"),
    ]);
    const markup = renderToStaticMarkup(
      <OnboardingProgressPanel
        summary={summary}
        onStageActivate={() => undefined}
        availableFocusTargets={new Set(["case-search-diagnostic"])}
      />,
    );

    expect(markup).not.toContain("<button");
  });

  it("keeps the technical inspector collapsed independently of primary progress", () => {
    const summary = summaryWithPipeline([
      processingNode("GOLDTIER_SEARCH", "GoldTier search", "IN_PROGRESS"),
    ]);

    const markup = renderToStaticMarkup(<DetailedProcessingInspector summary={summary} />);

    expect(markup).toContain("Detailed processing");
    expect(markup).toContain('aria-expanded="false"');
    expect(markup).toContain("hidden");
  });
});

describe("backend-authored stage ordering", () => {
  it("renders the v2 rail in the exact backend order", () => {
    const summary = summaryWithPipeline([
      processingNode("INITIAL_IDENTITY", "Initial identity", "COMPLETE"),
      processingNode("GOLDTIER_SEARCH", "GoldTier search", "COMPLETE"),
      processingNode("ACRA_REGISTRY", "ACRA registry", "IN_PROGRESS"),
    ]);

    const markup = renderToStaticMarkup(<PipelineRail summary={summary} />);

    expect(markup.indexOf("Initial identity")).toBeLessThan(markup.indexOf("GoldTier search"));
    expect(markup.indexOf("GoldTier search")).toBeLessThan(markup.indexOf("ACRA registry"));
  });

  it("preserves the backend v1 order instead of projecting the v2 sequence", () => {
    const summary = summaryWithPipeline([
      processingNode("ACRA_REGISTRY", "ACRA registry", "COMPLETE"),
      processingNode("DOCUMENT_IDP", "Document and IDP", "COMPLETE"),
      processingNode("GOLDTIER_TARGET", "GoldTier target", "IN_PROGRESS"),
    ]);
    summary.stage_order_version = 1;

    const markup = renderToStaticMarkup(<PipelineRail summary={summary} />);

    expect(markup.indexOf("ACRA registry")).toBeLessThan(markup.indexOf("Document and IDP"));
    expect(markup.indexOf("Document and IDP")).toBeLessThan(markup.indexOf("GoldTier target"));
  });

  it("uses backend order and outcomes for the completed-stage record", () => {
    const summary = summaryWithPipeline([
      processingNode("GOLDTIER_SEARCH", "GoldTier search", "COMPLETE"),
      processingNode("ACRA_REGISTRY", "ACRA registry", "EMPTY"),
      processingNode("DOCUMENT_IDP", "Document and IDP", "SKIPPED"),
    ]);
    summary.status = "COMPLETED";

    const markup = renderToStaticMarkup(<CompletedOverview summary={summary} />);

    expect(markup.indexOf("GoldTier search")).toBeLessThan(markup.indexOf("ACRA registry"));
    expect(markup.indexOf("ACRA registry")).toBeLessThan(markup.indexOf("Document and IDP"));
    expect(markup).toContain("Complete — no records");
    expect(markup).toContain("Skipped");
  });

  it("does not invent a completed-stage record when an older response has no pipeline", () => {
    const summary = summaryWithPipeline([]);
    summary.status = "COMPLETED";
    summary.processing_pipeline = undefined as unknown as ProcessingNode[];

    const markup = renderToStaticMarkup(<CompletedOverview summary={summary} />);

    expect(markup).toContain("Backend pipeline not reported for this completed case");
    expect(markup).not.toContain("Registry verification");
  });
});

describe("registry presentation taxonomy", () => {
  it("classifies expected missing ownership evidence as partial data, not provider unavailability", () => {
    const summary = summaryWithPipeline([]);
    summary.status = "WAITING_FOR_REVIEW";
    summary.current_stage = "REGISTRY";
    summary.active_exceptions = [{
      exception_id: "00000000-0000-4000-8000-000000000003",
      case_id: summary.case.case_id,
      exception_type: "REGISTRY_REVIEW_REQUIRED",
      stage: "REGISTRY",
      status: "OPEN",
      blocker_code: "REGISTRY_EXPECTED_DATA_MISSING",
      blocker_codes: ["REGISTRY_EXPECTED_DATA_MISSING"],
      explanation: "Expected registry ownership evidence was not returned.",
      evidence_version: "registry:1",
      automation_version: 3,
      evidence: [],
      available_actions: [],
      created_at: "2026-09-28T00:00:01Z",
      resolved_at: null,
      resolution: null,
    }];
    summary.case.entity = { legal_name: "GARDEN BUSINESS" } as ZeroTouchCaseSummary["case"]["entity"];
    summary.case.registry_acquisition = {
      requested_identifier: "11111999A",
      status: "PARTIAL",
      officers: [],
      ownership_parties: [],
      relationships: [],
      operation_results: [
        {
          operation: "ENTITY_PROFILE",
          status: "COMPLETE",
          record_count: 1,
          provenance: { provider: "ACRA", environment: "MOCK", operation: "ENTITY_PROFILE", retrieved_at: "2026-09-28T00:00:01Z", evidence_reference: "safe:entity" },
          error: null,
        },
        {
          operation: "OWNERSHIP_PARTIES",
          status: "EMPTY",
          record_count: 0,
          provenance: { provider: "ACRA", environment: "MOCK", operation: "OWNERSHIP_PARTIES", retrieved_at: "2026-09-28T00:00:01Z", evidence_reference: "safe:owners" },
          error: null,
        },
      ],
      issues: [{ code: "REGISTRY_EXPECTED_DATA_MISSING", message: "Expected registry ownership evidence was not returned." }],
      retrieved_at: "2026-09-28T00:00:01Z",
    };

    const presentation = registryPresentation(summary, "API_MARKETPLACE_MOCK");
    const markup = renderToStaticMarkup(
      <RegistryStatePanel summary={summary} registryProviderMode="API_MARKETPLACE_MOCK" />,
    );

    expect(presentation.heading).toBe("Registry data incomplete");
    expect(presentation.connection).toBe("Successful / data retrieved");
    expect(presentation.issue).toBe("Ownership evidence incomplete");
    expect(markup).toContain("Official ACRA API Marketplace Mock");
    expect(markup).toContain("GARDEN BUSINESS");
    expect(markup).toContain("Registry data incomplete");
    expect(markup).toContain("Review required");
    expect(markup).not.toContain("Registry unavailable");
  });

  it.each([
    ["REGISTRY_OPERATION_TIMEOUT", "Registry unavailable"],
    ["REGISTRY_OPERATION_UNAVAILABLE", "Registry unavailable"],
    ["REGISTRY_OPERATION_MALFORMED_RESPONSE", "Registry response could not be validated"],
  ])("maps %s to its semantic heading", (code, expectedHeading) => {
    const summary = summaryWithPipeline([]);
    summary.status = "TECHNICAL_FAILURE";
    summary.current_stage = "REGISTRY";
    summary.technical_failure = { code, message: "Safe registry stop." };

    expect(registryPresentation(summary).heading).toBe(expectedHeading);
  });

  it("shows ACRA as not reached while initial GoldTier identity is ambiguous", () => {
    const summary = summaryWithPipeline([
      processingNode("INITIAL_IDENTITY", "Initial identity", "COMPLETE"),
      {
        ...processingNode("GOLDTIER_SEARCH", "GoldTier search", "REVIEW_REQUIRED"),
        blocker_code: "GT_SEARCH_IDENTITY_REVIEW_REQUIRED",
      },
      {
        ...processingNode("ACRA_REGISTRY", "ACRA registry", "NOT_REACHED"),
        safe_result: "Waiting for GoldTier customer identity resolution",
        blocker_code: "GT_SEARCH_IDENTITY_REVIEW_REQUIRED",
      },
    ]);
    summary.status = "WAITING_FOR_REVIEW";
    summary.current_stage = "GOLDTIER_SEARCH";
    summary.completed_stages = [];

    const presentation = registryPresentation(summary);
    const markup = renderToStaticMarkup(<RegistryStatePanel summary={summary} />);

    expect(presentation.heading).toBe("ACRA not reached");
    expect(presentation.connection).toBe("No ACRA call occurred");
    expect(markup).toContain("Waiting for GoldTier customer identity resolution");
    expect(markup).not.toContain("Registry unavailable");
  });
});
