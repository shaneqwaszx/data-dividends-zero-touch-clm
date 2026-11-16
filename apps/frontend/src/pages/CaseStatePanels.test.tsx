import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import type {
  DocumentProcessingRecord, ProcessingNode, ZeroTouchCaseSummary } from "../types";
import {
  businessStageMembers,
  businessStagePipeline,
  CompletedOverview,
  ConfirmDetailsPanel,
  DetailedProcessingInspector,
  GOLDTIER_DETAILS_STEP_ID,
  OnboardingProgressPanel,
  PipelineRail,
  ProcessingBlockerPanels,
  processingNodeFocusTarget,
  RegistryStatePanel,
  registryPresentation,
  stageStatusFor,
} from "./CaseStatePanels";
import RegistryProvenancePanel from "./RegistryProvenancePanel";
import StageDisclosure from "./StageDisclosure";

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
  it("names the user-owned final confirmation and terminal next action", () => {
    const summary = summaryWithPipeline([]);
    summary.status = "WAITING_FOR_REVIEW";
    summary.current_stage = "READINESS";
    summary.interventions = [];
    summary.active_exceptions = [{ exception_type: "TARGET_CONFIRMATION_REQUIRED" }] as ZeroTouchCaseSummary["active_exceptions"];
    let markup = renderToStaticMarkup(<OnboardingProgressPanel summary={summary} />);
    expect(markup).toContain("Review and confirm submission");
    expect(markup).not.toContain("Wait for the current backend stage");
    summary.status = "COMPLETED";
    markup = renderToStaticMarkup(<OnboardingProgressPanel summary={summary} />);
    expect(markup).toContain("Submitted — no action required.");
    expect(markup).not.toContain("Review and confirm submission");
  });
  it("announces completed reviewed POC submission consistently", () => {
    const summary = summaryWithPipeline([
      processingNode("GOLDTIER_TARGET", "GoldTier target", "COMPLETE"),
      processingNode("FINAL_REVIEW_SEND", "Final review & send", "COMPLETE"),
    ]);
    summary.status = "COMPLETED";
    const markup = renderToStaticMarkup(<OnboardingProgressPanel summary={summary} />);
    expect(markup).toContain('aria-valuemax="100"');
    expect(markup).toContain('aria-valuenow="100"');
    expect(markup).toContain("reviewed POC submission complete");
    expect(markup).toContain("100%");
    expect(markup).toContain("Final review &amp; send");
    expect(markup).not.toContain("Human approval");
  });
  it("renders the backend order, current text, and accessible bounded progress before terminal state", () => {
    const summary = summaryWithPipeline([
      processingNode("CASE_CREATED", "Case created", "COMPLETE"),
      processingNode("GOLDTIER_SEARCH", "GoldTier search", "IN_PROGRESS"),
      processingNode("ACRA_REGISTRY", "ACRA registry", "NOT_REACHED"),
      processingNode("DOCUMENT_IDP", "Document and IDP", "NOT_REACHED"),
    ]);

    const markup = renderToStaticMarkup(<OnboardingProgressPanel summary={summary} />);

    expect(markup).toContain("Onboarding progress");
    expect(markup).toContain('role="progressbar"');
    expect(markup).toContain('aria-valuemin="0"');
    expect(markup).toContain('aria-valuemax="100"');
    expect(markup).toContain('aria-valuenow="25"');
    expect(markup).toContain("1 of 4 stages complete or skipped");
    expect(markup).toContain("current: GoldTier search — In progress");
    const stagesMarkup = markup.slice(markup.indexOf('aria-label="Onboarding stages"'));
    expect(stagesMarkup.indexOf("Case created")).toBeLessThan(stagesMarkup.indexOf("GoldTier search"));
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

    for (const label of ["Complete", "In progress", "Skipped", "Review required", "Blocked", "Failed", "Not started yet"]) {
      expect(markup).toContain(label);
    }
    expect(markup).toContain('aria-valuemax="100"');
    expect(markup).toContain('aria-valuenow="29"');
    expect(markup).toContain("2 of 7 stages complete or skipped");
  });

  it("uses the earliest actionable backend node and makes every stage inspectable", () => {
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
    expect(markup).toContain('aria-label="Open details for ACRA registry"');
    expect(markup.match(/onboarding-progress__title-row/g)).toHaveLength(3);
    expect(markup.match(/onboarding-progress__stage-status/g)).toHaveLength(3);
    expect(markup.match(/onboarding-progress__stage-action/g)).toHaveLength(3);
    expect(markup).toContain(">View details<");
    expect(markup).toContain(">Review<");
    expect(markup).toContain(">Resolve issue<");
    expect(markup.match(/<button/g)).toHaveLength(3);
  });

  it("keeps a long actionable title intact and labels navigation as non-mutating review", () => {
    const summary = summaryWithPipeline([
      processingNode(
        "TARGET_CLASSIFICATION_CLIENT_SEGMENT",
        "Target classification and client segment verification",
        "REVIEW_REQUIRED",
      ),
    ]);

    const markup = renderToStaticMarkup(
      <OnboardingProgressPanel summary={summary} onStageActivate={() => undefined} />,
    );

    expect(markup).toContain("Target classification and client segment verification");
    expect(markup).toContain('aria-label="Open details for Target classification and client segment verification"');
    expect(markup).toContain(">Review<");
    expect(markup).not.toContain("Resolve");
  });

  it("derives one actionable Initial identity stage from the retained blocker when the pipeline omitted it", () => {
    const summary = summaryWithPipeline([processingNode("DOCUMENT_IDP", "Document and IDP", "NOT_REACHED")]);
    summary.active_exceptions = [{
      exception_id: "legacy-identity",
      blocker_code: "INITIAL_IDENTITY_INCOMPLETE",
    }] as ZeroTouchCaseSummary["active_exceptions"];

    const markup = renderToStaticMarkup(
      <OnboardingProgressPanel
        summary={summary}
        onStageActivate={() => undefined}
        availableFocusTargets={new Set(["case-identity-correction"])}
      />,
    );

    expect(markup).toContain("Initial identity");
    expect(markup).toContain('aria-label="Open details for Initial identity"');
  });

  it("maps only actionable stable backend nodes to specific existing panels", () => {
    expect(processingNodeFocusTarget(processingNode("INITIAL_IDENTITY", "Identity", "REVIEW_REQUIRED"))).toBe(
      "case-identity-correction",
    );
    expect(processingNodeFocusTarget(processingNode("INITIAL_IDENTITY", "Identity", "NOT_REACHED"))).toBe(
      "case-identity-correction",
    );
    expect(processingNodeFocusTarget(processingNode("GOLDTIER_SEARCH", "Search", "FAILED"))).toBe("case-search-diagnostic");
    expect(processingNodeFocusTarget(processingNode("ACRA_REGISTRY", "ACRA", "REVIEW_REQUIRED"))).toBe("case-evidence-registry");
    expect(processingNodeFocusTarget(processingNode("DOCUMENT_IDP", "Document", "BLOCKED"))).toBe("case-evidence-documents");
    expect(processingNodeFocusTarget(processingNode("TARGET_CLASSIFICATION_CLIENT_SEGMENT", "Classification", "REVIEW_REQUIRED"))).toBe(
      "case-target-classification",
    );
    expect(processingNodeFocusTarget(processingNode("TARGET_CLASSIFICATION_KYC_CUSTOMER_TYPE", "KYC", "REVIEW_REQUIRED"))).toBe(
      "case-target-classification",
    );
    expect(processingNodeFocusTarget(processingNode("TARGET_CLASSIFICATION_REGISTRATION_TYPE", "Registration type", "REVIEW_REQUIRED"))).toBe(
      "case-policy-rebind",
    );
    expect(processingNodeFocusTarget(processingNode("TARGET_CLASSIFICATION_CUSTOMER_EXTERNAL_SYSTEM", "External system", "REVIEW_REQUIRED"))).toBe(
      "case-policy-rebind",
    );
    expect(processingNodeFocusTarget(processingNode("GOLDTIER_TARGET", "Target", "BLOCKED"))).toBe("case-target-blocker");
    expect(processingNodeFocusTarget(processingNode("FINAL_REVIEW_SEND", "Approval", "REVIEW_REQUIRED"))).toBe("case-review-and-send");
    expect(processingNodeFocusTarget(processingNode("ACRA_REGISTRY", "ACRA", "COMPLETE"))).toBeNull();
    expect(processingNodeFocusTarget(processingNode("UNRECOGNISED_NODE", "Unknown", "FAILED"))).toBeNull();
  });

  it("renders dedicated read-only destinations for Search and target blockers without a second approval", () => {
    const search = {
      ...processingNode("GOLDTIER_SEARCH", "GoldTier search", "FAILED"),
      blocker_code: "SEARCH_TIMEOUT",
      safe_result: "Customer existence remains unresolved.",
    };
    const target = {
      ...processingNode("GOLDTIER_TARGET", "GoldTier target", "BLOCKED"),
      blocker_code: "GOLDTIER_SEARCH_FAILED",
    };
    const approval = processingNode("FINAL_REVIEW_SEND", "Final review & send", "REVIEW_REQUIRED");

    const markup = renderToStaticMarkup(
      <ProcessingBlockerPanels summary={summaryWithPipeline([search, target, approval])} />,
    );

    expect(markup).toContain('id="case-search-diagnostic"');
    expect(markup).toContain("does not prove that the customer is absent");
    expect(markup).toContain('id="case-target-blocker"');
    expect(markup).toContain("does not provide a bypass or replay action");
    expect(markup).not.toContain("case-human-approval-boundary");
    expect(markup).not.toContain("Final approval is unresolved");
  });

  it("keeps details inspectable when an action destination is unavailable", () => {
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

    expect(markup).toContain("<button");
    expect(markup).toContain(">View details<");
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
      processingNode("INITIAL_IDENTITY", "Initial identity", "REVIEW_REQUIRED"),
      processingNode("GOLDTIER_SEARCH", "GoldTier search", "COMPLETE"),
      processingNode("ACRA_REGISTRY", "ACRA registry", "IN_PROGRESS"),
    ]);

    const markup = renderToStaticMarkup(<PipelineRail summary={summary} />);

    expect(markup.indexOf("Initial identity")).toBeGreaterThanOrEqual(0);
    expect(markup.indexOf("Initial identity")).toBeLessThan(markup.indexOf("GoldTier search"));
    expect(markup.indexOf("GoldTier search")).toBeLessThan(markup.indexOf("ACRA registry"));
  });
});

describe("ten business steps over the twelve backend stages", () => {
  const backend = (overrides: Partial<Record<string, ProcessingNode["status"]>> = {}) => [
    ["CASE_START", "Case created"], ["INITIAL_IDENTITY", "Initial identity"], ["JURISDICTION", "Jurisdiction"],
    ["GOLDTIER_SEARCH", "Existing-customer search"], ["ACRA_REGISTRY", "Registry verification"],
    ["DOCUMENT_IDP", "Document verification"], ["RECONCILIATION", "Data reconciliation"],
    ["OWNERSHIP_UBO", "Ownership & UBO"], ["ADVISORY", "Risk assessment"], ["READINESS", "Submission readiness"],
    ["GOLDTIER_TARGET", "GoldTier submission package"], ["FINAL_REVIEW_SEND", "Final review & send"],
  ].map(([id, label]) => processingNode(id, label, overrides[id] ?? "COMPLETE"));

  it("maps twelve backend stages to eleven steps, grouping readiness and the package", () => {
    const steps = businessStagePipeline(backend());
    expect(steps.map(step => step.label)).toEqual([
      "Case created", "Initial identity", "Jurisdiction", "Existing-customer search", "Registry verification", "Document verification",
      "Data reconciliation", "Ownership & UBO", "Risk assessment", "GoldTier Details & Status", "Final review & send",
    ]);
    const grouped = steps.find(step => step.node_id === GOLDTIER_DETAILS_STEP_ID)!;
    expect(businessStageMembers(backend(), grouped).map(member => member.node_id)).toEqual(["READINESS", "GOLDTIER_TARGET"]);
    expect(processingNodeFocusTarget(grouped)).toBe("case-target-blocker");
  });

  it.each(["REVIEW_REQUIRED", "BLOCKED", "FAILED", "IN_PROGRESS", "NOT_REACHED"] as const)(
    "shows Initial identity while it is %s", (status) => {
      expect(businessStagePipeline(backend({ INITIAL_IDENTITY: status })).map(step => step.node_id)).toContain("INITIAL_IDENTITY");
    },
  );

  it("always shows a completed Initial identity, so the count matches the full pipeline", () => {
    const summary = summaryWithPipeline(backend());
    expect(renderToStaticMarkup(<PipelineRail summary={summary} />)).toContain('data-node-id="INITIAL_IDENTITY"');
    expect(renderToStaticMarkup(<OnboardingProgressPanel summary={summary} />)).toContain("of 11 stages done");
  });

  it.each([
    [{ READINESS: "COMPLETE", GOLDTIER_TARGET: "COMPLETE" }, "COMPLETE"],
    [{ READINESS: "COMPLETE", GOLDTIER_TARGET: "NOT_REACHED" }, "NOT_REACHED"],
    [{ READINESS: "IN_PROGRESS", GOLDTIER_TARGET: "NOT_REACHED" }, "IN_PROGRESS"],
    [{ READINESS: "COMPLETE", GOLDTIER_TARGET: "FAILED" }, "FAILED"],
    [{ READINESS: "BLOCKED", GOLDTIER_TARGET: "IN_PROGRESS" }, "BLOCKED"],
  ] as const)("marks the grouped step %j as %s, never done before both members", (overrides, expected) => {
    const grouped = businessStagePipeline(backend(overrides)).find(step => step.node_id === GOLDTIER_DETAILS_STEP_ID)!;
    expect(grouped.status).toBe(expected);
  });

  it("counts business steps and names each member status when they differ", () => {
    const summary = summaryWithPipeline(backend({ GOLDTIER_TARGET: "NOT_REACHED", FINAL_REVIEW_SEND: "NOT_REACHED" }));
    const markup = renderToStaticMarkup(<OnboardingProgressPanel summary={summary} />);
    expect(markup).toContain("9 of 11 stages done");
    expect(markup).toContain("Submission readiness: Complete · GoldTier submission package: Not started yet");
    expect(markup).not.toContain("100%");
    // Readiness needing attention while the package is complete: the grouped step is not done.
    const differing = renderToStaticMarkup(<OnboardingProgressPanel summary={summaryWithPipeline(backend({ READINESS: "FAILED" }))} />);
    expect(differing).toContain("10 of 11 stages done");
    expect(differing).toContain("Submission readiness: Failed · GoldTier submission package: Complete");
    const identity = summaryWithPipeline(backend({ INITIAL_IDENTITY: "REVIEW_REQUIRED" }));
    expect(renderToStaticMarkup(<OnboardingProgressPanel summary={identity} />)).toContain("10 of 11 stages done");
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

  it("states Sandbox submission without claiming completed KYC or screening", () => {
    const summary = summaryWithPipeline([]);
    summary.status = "COMPLETED";
    summary.clm = { submission_plan: { environment: "SANDBOX" } } as ZeroTouchCaseSummary["clm"];
    const markup = renderToStaticMarkup(<CompletedOverview summary={summary} />);
    expect(markup).toContain("GoldTier Sandbox customer/profile submission completed");
    expect(markup).toContain("Policy initiates GoldTier KYC activity where documented");
    expect(markup).toContain("does not establish KYC completion");
    expect(markup).toContain("sanctions or PEP clearance");
    expect(markup).toContain("regulatory approval or Production onboarding");
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
  it.each(["WAITING_FOR_REVIEW", "COMPLETED"] as const)("retains partial source evidence without a stale registry action at %s", (status) => {
    const summary = summaryWithPipeline([processingNode("ACRA_REGISTRY", "ACRA registry", "COMPLETE")]);
    summary.status = status;
    summary.current_stage = status === "COMPLETED" ? "COMPLETE" : "READINESS";
    summary.case.entity = { legal_name: "GARDEN BUSINESS" } as ZeroTouchCaseSummary["case"]["entity"];
    summary.case.registry_acquisition = {
      status: "PARTIAL", operation_results: [],
      issues: [{ code: "REGISTRY_EXPECTED_DATA_MISSING", message: "Source ownership evidence incomplete." }],
    } as unknown as NonNullable<ZeroTouchCaseSummary["case"]["registry_acquisition"]>;
    const presentation = registryPresentation(summary);
    expect(presentation.heading).toBe("Registry identity validated");
    expect(presentation.attention).toBe(false);
    expect(presentation.description).toContain("source ownership evidence remains incomplete");
    expect(presentation.action).not.toContain("Review required");
  });

  it("renders an unsupported pipeline child with an explicit label", () => {
    const summary = summaryWithPipeline([processingNode("ACRA_RELATIONSHIPS", "Relationships", "UNSUPPORTED")]);
    expect(renderToStaticMarkup(<PipelineRail summary={summary} />)).toContain("Unsupported");
  });

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

it("projects retained CACHE_HIT as no request without inventing a connection result", () => {
  const summary = summaryWithPipeline([]);
  summary.case.registry_evidence_binding = {
    disposition: "CACHE_HIT", bound_to_case_at: "2026-10-02T00:00:00Z",
    expires_at: "2026-12-01T00:00:00Z", freshness_policy_id: "MOCK_ACRA_FIXED_90D",
    freshness_policy_version: 1, freshness_duration_seconds: 7776000,
    freshness_comparator: "EVALUATION_NOW_LT_EXPIRES_AT",
  };
  summary.case.registry_acquisition = {
    requested_identifier: "202400001A", status: "COMPLETE", officers: [],
    ownership_parties: [], relationships: [], operation_results: [], issues: [],
    retrieved_at: "2026-10-02T00:00:00Z",
  };
  const presentation = registryPresentation(summary, "LOCAL_MOCK");
  expect(presentation.heading).toBe("Registry evidence reused");
  expect(presentation.connection).toBe("No ACRA request required");
  expect(presentation.description).toBe("Reused fresh registry evidence — no ACRA request required.");
  expect(presentation.attention).toBe(false);
  expect(presentation.provider).toBe("Synthetic local ACRA Mock");
});

it("keeps CACHE_HIT acquisition truth when an independent target failure occurs later", () => {
  const summary = summaryWithPipeline([]);
  summary.case.registry_evidence_binding = {
    disposition: "CACHE_HIT", bound_to_case_at: "2026-10-02T00:00:00Z",
    expires_at: "2026-12-01T00:00:00Z", freshness_policy_id: "MOCK_ACRA_FIXED_90D",
    freshness_policy_version: 1, freshness_duration_seconds: 7776000,
    freshness_comparator: "EVALUATION_NOW_LT_EXPIRES_AT",
  };
  summary.status = "TECHNICAL_FAILURE";
  summary.current_stage = "MOCK_GOLDTIER";
  summary.technical_failure = { code: "GOLDTIER_SERVICE_UNAVAILABLE", message: "Target unavailable." };
  expect(registryPresentation(summary, "LOCAL_MOCK").connection).toBe("No ACRA request required");
});

it("describes the existing bounded read-only Search recheck without a mutation bypass", () => {
  const summary = summaryWithPipeline([processingNode("GOLDTIER_SEARCH", "GoldTier Search", "FAILED")]);
  const markup = renderToStaticMarkup(<ProcessingBlockerPanels summary={summary} stage="REGISTRY" />);
  expect(markup).toContain("bounded read-only Search recheck may be available");
  expect(markup).toContain("Registry identity");
  expect(markup).toContain("Target mutation remains prohibited");
  expect(markup).not.toContain("no target mutation or browser retry is available");
});


it.each([
  ["new customer NO_MATCH", ["COMPLETE", "COMPLETE", "NOT_REACHED", "NOT_REACHED"], 50],
  ["existing customer", ["COMPLETE", "SKIPPED", "SKIPPED", "REVIEW_REQUIRED"], 75],
  ["fresh cache reuse", ["COMPLETE", "COMPLETE", "REVIEW_REQUIRED", "NOT_REACHED"], 50],
  ["optional Amend", ["COMPLETE", "SKIPPED", "COMPLETE", "REVIEW_REQUIRED"], 75],
  ["Garden ownership review", ["COMPLETE", "COMPLETE", "REVIEW_REQUIRED", "BLOCKED"], 50],
  ["document review", ["COMPLETE", "REVIEW_REQUIRED", "BLOCKED", "NOT_REACHED"], 25],
  ["technical failure", ["COMPLETE", "FAILED", "BLOCKED", "NOT_REACHED"], 25],
] as const)("counts only satisfied stages for %s", (_scenario, statuses, expected) => {
  const summary = summaryWithPipeline(statuses.map((status, index) =>
    processingNode("SCENARIO_" + index, "Stage " + index, status)));
  const markup = renderToStaticMarkup(<OnboardingProgressPanel summary={summary} />);
  expect(markup).toContain('aria-valuenow="' + expected + '"');
});

it.each([
  ["MOCK_GOLDTIER", "GT_POLICY_VALIDATION_FAILED"],
  ["DOCUMENT", "IDP_PROCESSING_FAILED"],
] as const)("keeps fetched registry evidence neutral after unrelated %s failure", (stage, code) => {
  const summary = summaryWithPipeline([processingNode("ACRA_REGISTRY", "ACRA registry", "COMPLETE")]);
  summary.case.registry_acquisition = {
    requested_identifier: "202400001A", status: "COMPLETE", officers: [],
    ownership_parties: [], relationships: [], operation_results: [], issues: [],
    retrieved_at: "2026-10-02T00:00:00Z",
  };
  summary.status = "TECHNICAL_FAILURE";
  summary.current_stage = stage;
  summary.technical_failure = { code, message: "Safe unrelated technical failure." };
  const presentation = registryPresentation(summary, "LOCAL_MOCK");
  expect(presentation.heading).toBe("Registry data acquired");
  expect(presentation.tag).toBe("COMPLETE");
  expect(presentation.attention).toBe(false);
  expect(presentation.code).toBeNull();
  expect(presentation.message).toBeNull();
  expect(renderToStaticMarkup(<RegistryStatePanel summary={summary} />)).toBe("");
  expect(summary.technical_failure.code).toBe(code);
});

it("keeps an owning registry failure visible despite a retained cache binding", () => {
  const summary = summaryWithPipeline([processingNode("ACRA_REGISTRY", "ACRA registry", "FAILED")]);
  summary.case.registry_evidence_binding = {
    disposition: "CACHE_HIT", bound_to_case_at: "2026-10-02T00:00:00Z",
    expires_at: "2026-12-01T00:00:00Z", freshness_policy_id: "MOCK_ACRA_FIXED_90D",
    freshness_policy_version: 1, freshness_duration_seconds: 7776000,
    freshness_comparator: "EVALUATION_NOW_LT_EXPIRES_AT",
  };
  summary.status = "TECHNICAL_FAILURE";
  summary.current_stage = "REGISTRY";
  summary.technical_failure = { code: "REGISTRY_OPERATION_TIMEOUT", message: "Safe registry stop." };
  const presentation = registryPresentation(summary, "LOCAL_MOCK");
  expect(presentation.heading).toBe("Registry unavailable");
  expect(presentation.attention).toBe(true);
  expect(presentation.code).toBe("REGISTRY_OPERATION_TIMEOUT");
  expect(renderToStaticMarkup(<RegistryStatePanel summary={summary} />)).toContain("Registry unavailable");
});

it("keeps an unclassified registry-owned technical code technical", () => {
  const summary = summaryWithPipeline([processingNode("ACRA_REGISTRY", "ACRA registry", "FAILED")]);
  summary.status = "TECHNICAL_FAILURE";
  summary.current_stage = "REGISTRY";
  summary.technical_failure = { code: "ZERO_TOUCH_UNEXPECTED_FAILURE", message: "Safe unexpected stop." };
  const presentation = registryPresentation(summary, "LOCAL_MOCK");
  expect(presentation.heading).toBe("Registry technical failure");
  expect(presentation.tag).toBe("Technical failure");
  expect(presentation.attention).toBe(true);
  expect(presentation.code).toBe("ZERO_TOUCH_UNEXPECTED_FAILURE");
  expect(presentation.action).toBe("Operator review required");
});


it.each(["acquisition-missing", "acquisition-invalid", "binding-missing", "expiry-invalid", "operation-invalid"])(
  "never claims fresh registry reuse anywhere in the combined view with %s timestamps",
  (failure) => {
    const summary = summaryWithPipeline([]);
    summary.current_stage = "REGISTRY";
    summary.case.registry_acquisition = {
      requested_identifier: "202400001A", status: "COMPLETE", officers: [],
      ownership_parties: [], relationships: [], issues: [],
      retrieved_at: "2026-10-02T00:00:00Z",
      operation_results: [{ operation: "ENTITY_PROFILE", status: "COMPLETE", record_count: 1, error: null,
        provenance: { provider: "ACRA", environment: "MOCK", operation: "ENTITY_PROFILE",
          retrieved_at: "2026-10-02T00:00:00Z", evidence_reference: "safe:registry" } }],
    };
    summary.case.registry_evidence_binding = {
      disposition: "CACHE_HIT", bound_to_case_at: "2026-10-02T00:00:00Z",
      expires_at: "2026-12-01T00:00:00Z", freshness_policy_id: "MOCK_ACRA_FIXED_90D",
      freshness_policy_version: 1, freshness_duration_seconds: 7776000,
      freshness_comparator: "EVALUATION_NOW_LT_EXPIRES_AT",
    };
    if (failure === "acquisition-missing") summary.case.registry_acquisition = null;
    if (failure === "acquisition-invalid") summary.case.registry_acquisition!.retrieved_at = "2026-02-30T00:00:00Z";
    if (failure === "binding-missing") summary.case.registry_evidence_binding.bound_to_case_at = "";
    if (failure === "expiry-invalid") summary.case.registry_evidence_binding.expires_at = "broken";
    if (failure === "operation-invalid") summary.case.registry_acquisition!.operation_results[0].provenance!.retrieved_at = "broken";
    const markup = renderToStaticMarkup(<>
      <RegistryStatePanel summary={summary} />
      <RegistryProvenancePanel acquisition={summary.case.registry_acquisition} binding={summary.case.registry_evidence_binding} />
    </>);
    expect(markup).toContain("Registry evidence reused");
    expect(markup).toContain("CACHE_HIT");
    expect(markup).not.toContain("Reused fresh registry evidence");
    expect(markup.match(/Retained registry reuse; valid-at-use timestamps unavailable\./g)).toHaveLength(2);
    expect(registryPresentation(summary).attention).toBe(false);
  },
);

it("compact Registry preserves truthful retained absence when the legacy state panel is omitted", () => {
  const summary = summaryWithPipeline([]);
  expect(renderToStaticMarkup(<RegistryStatePanel summary={summary} />)).toBe("");
  const compact = renderToStaticMarkup(<RegistryStatePanel summary={summary} compact />);
  expect(compact).toContain("Registry acquisition is not retained. Completion and provider activity cannot be inferred.");
  expect(compact).toContain("Retained registry state");
  expect(compact).not.toContain("In progress");
  expect(compact).not.toContain("Successful / data retrieved");
  expect(compact).not.toContain("progress-list");
  expect(compact).toContain("SG");
});


it("retains reconciliation status and safe lineage in Technical after the document checkpoint", () => {
  const summary = summaryWithPipeline([]);
  summary.current_stage = "READINESS";
  summary.reconciliation = { reconciliation_id: "safe-reconciliation", version: 4, status: "RESOLVED", source_document_ids: ["safe-document"], source_document_event_counts: [3],
    updated_at: "2026-10-15T12:00:00Z", fields: [{ field_name: "legal_name", outcome: "CONFLICT", observations: [{ observation_id: "safe-observation", source_kind: "DOCUMENT_IDP", source_system: "LOCAL_PDF_TEXT", environment: "LOCAL", evidence_reference: "safe:reference" }], discrepancy_id: null }], discrepancies: [] } as unknown as NonNullable<ZeroTouchCaseSummary["reconciliation"]>;
  const technical = renderToStaticMarkup(<ConfirmDetailsPanel presentation="technical" summary={summary} />);
  expect(technical).toContain("RESOLVED"); expect(technical).toContain("LOCAL_PDF_TEXT"); expect(technical).toContain("safe:reference");
  expect(technical).toContain("event count 3"); expect(technical).toContain("CONFLICT");
  expect(technical).not.toMatch(/<details|<button|<input|<select/);
  expect(renderToStaticMarkup(<ConfirmDetailsPanel summary={summary} />)).toBe("");
});

it("compares registry value, document value with confidence, and the reviewer's choice in plain words", () => {
  const summary = summaryWithPipeline([]);
  summary.current_stage = "DOCUMENT";
  const observation = (field: string, kind: string, value: string | null) => ({ observation_id: `${field}-${kind}`, field_name: field, source_kind: kind, normalized_value: value, validity: value ? "VALID" : "MISSING", confidence: null });
  summary.reconciliation = { reconciliation_id: "r", version: 1, status: "REVIEW_REQUIRED", source_document_ids: ["doc"], source_document_event_counts: [1], updated_at: "2026-10-15T12:00:00Z",
    fields: ["legal_name", "registration_identifier", "registered_address"].map(field => ({ field_name: field, outcome: "MISSING_IN_SOURCE",
      observations: [observation(field, "REGISTRY", "REG"), observation(field, "DOCUMENT_IDP", null)], discrepancy_id: null })),
    discrepancies: [] } as unknown as NonNullable<ZeroTouchCaseSummary["reconciliation"]>;
  const doc = { document_id: "doc", superseded_by_document_id: null, fields: [
    { field_key: "legal_name", review_status: "REJECTED", original_extracted_value: "DOC NAME", reviewed_value: null, confidence: 0.97 },
    { field_key: "registration_number", review_status: "CORRECTED", original_extracted_value: "11111998B", reviewed_value: "11111999A", confidence: 0.9 },
    { field_key: "registered_address", review_status: "ACCEPTED", original_extracted_value: "1 DOC ROAD", reviewed_value: "1 DOC ROAD", confidence: 0.8 },
  ] } as unknown as DocumentProcessingRecord;
  const markup = renderToStaticMarkup(<ConfirmDetailsPanel presentation="main" summary={summary} documents={[doc]} />);
  for (const header of ["Registry value", "Document value", "Your choice"]) expect(markup).toContain(header);
  // The document's own value stays visible even when the comparison saw none.
  expect(markup).toContain("DOC NAME"); expect(markup).toContain("97% confidence");
  expect(markup).toContain("Manual input: 11111999A");
  expect(markup).toContain(">Document value<");
  // A rejected suggestion is shown as such; it records no registry or document choice, so nothing is highlighted for it.
  expect(markup).toContain("Suggestion rejected");
  // The chosen value's cell is highlighted: document for the address, manual in Your choice.
  expect(markup.match(/is-chosen/g)).toHaveLength(2);
  expect(markup).not.toMatch(/data-label="Registry value" class="is-chosen"/);
  expect(markup).toMatch(/data-label="Document value" class="is-chosen"/);
  expect(markup).toMatch(/data-label="Your choice" class="is-chosen"/);
});

describe("stages waiting for earlier steps (presentation only)", () => {
  function staged(nodeId: string, label: string, status: ProcessingNode["status"], backend_stage: ProcessingNode["backend_stage"], blocker_code: string | null = null): ProcessingNode {
    return { node_id: nodeId, label, status, backend_stage, blocker_code, children: [] };
  }
  /** A case at Document waiting for uploads; later stages report BLOCKED only for missing prerequisites. */
  function pendingDocuments(overrides: Record<string, unknown> = {}): ZeroTouchCaseSummary {
    const value = summaryWithPipeline([
      staged("ACRA_REGISTRY", "Registry verification", "COMPLETE", "REGISTRY"),
      staged("GOLDTIER_SEARCH", "Existing-customer search", "COMPLETE", "GOLDTIER_SEARCH"),
      staged("DOCUMENT_IDP", "Document verification", "BLOCKED", "DOCUMENT"),
      staged("RECONCILIATION", "Data reconciliation", "NOT_REACHED", "DOCUMENT"),
      staged("OWNERSHIP_UBO", "Ownership & UBO", "BLOCKED", "OWNERSHIP"),
      staged("READINESS", "Submission readiness", "BLOCKED", "READINESS", "DOCUMENT_REQUIRED"),
      staged("GOLDTIER_TARGET", "GoldTier submission package", "BLOCKED", "READINESS", "DOCUMENT_REQUIRED"),
      staged("FINAL_REVIEW_SEND", "Final review & send", "BLOCKED", "MOCK_GOLDTIER", "DOCUMENT_REQUIRED"),
    ]);
    const clm = { ...value.clm, readiness: { blockers: ["DOCUMENT_REQUIRED", "OWNERSHIP_REQUIRED"] } };
    return { ...value, clm, status: "PENDING_INPUTS", current_stage: "DOCUMENT", completed_stages: ["REGISTRY", "GOLDTIER_SEARCH"], ...overrides } as ZeroTouchCaseSummary;
  }
  const tile = (markup: string, label: string) => {
    const match = new RegExp(`<li[^>]*>(?:(?!</li>).)*?aria-label="Open details for ${label.replace("&", "&amp;")}"(?:(?!</li>).)*</li>`).exec(markup);
    expect(match, label).not.toBeNull();
    return match![0];
  };

  it("shows later prerequisite-only stages as waiting while keeping data-status, counts and the genuine blocker", () => {
    const summary = pendingDocuments();
    const markup = renderToStaticMarkup(<OnboardingProgressPanel summary={summary} onStageActivate={() => undefined} />);
    const documents = tile(markup, "Document verification");
    expect(documents).toContain('data-status="BLOCKED"');
    expect(documents).not.toContain("data-display-state");
    expect(documents).toContain(">Blocked<");
    expect(documents).toContain(">Resolve issue<");
    for (const label of ["Ownership & UBO", "GoldTier Details & Status", "Final review & send"]) {
      const later = tile(markup, label);
      expect(later, label).toContain('data-status="BLOCKED"');
      expect(later, label).toContain('data-display-state="waiting"');
      expect(later, label).toContain(">Waiting for earlier steps<");
      expect(later, label).not.toContain("Resolve issue");
    }
    // The genuine blocker stays current; counts and percentage are unchanged (2 of 7 steps).
    expect(markup).toContain("current: Document verification — Blocked");
    expect(markup).toContain("2 of 7 stages complete or skipped");
    expect(markup).toContain('aria-valuenow="29"');
  });

  it("keeps an earlier-stage review visible and actionable while later stages wait", () => {
    const summary = pendingDocuments({ status: "WAITING_FOR_REVIEW" });
    summary.processing_pipeline![2] = staged("DOCUMENT_IDP", "Document verification", "REVIEW_REQUIRED", "DOCUMENT", "DOCUMENT_LOW_CONFIDENCE");
    summary.active_exceptions = [{ exception_id: "e1", stage: "DOCUMENT", status: "OPEN", blocker_code: "DOCUMENT_LOW_CONFIDENCE", blocker_codes: ["DOCUMENT_LOW_CONFIDENCE"], exception_type: "DOCUMENT_LOW_CONFIDENCE" }] as unknown as ZeroTouchCaseSummary["active_exceptions"];
    const markup = renderToStaticMarkup(<OnboardingProgressPanel summary={summary} onStageActivate={() => undefined} />);
    expect(tile(markup, "Document verification")).toContain(">Review required<");
    expect(tile(markup, "Document verification")).toContain(">Review<");
    expect(tile(markup, "Ownership & UBO")).toContain(">Waiting for earlier steps<");
    expect(markup).toContain("current: Document verification — Review required");
    expect(markup).toMatch(/Active issues.*?<dd>1<\/dd>/);
  });

  it("keeps a later stage blocked when its own exception is open, even at an earlier current stage", () => {
    const summary = pendingDocuments({ status: "WAITING_FOR_REVIEW" });
    summary.active_exceptions = [{ exception_id: "e2", stage: "OWNERSHIP", status: "OPEN", blocker_code: "OWNERSHIP_INCOMPLETE", blocker_codes: ["OWNERSHIP_INCOMPLETE"], exception_type: "OWNERSHIP_INCOMPLETE" }] as unknown as ZeroTouchCaseSummary["active_exceptions"];
    const markup = renderToStaticMarkup(<OnboardingProgressPanel summary={summary} onStageActivate={() => undefined} />);
    expect(tile(markup, "Ownership & UBO")).not.toContain("data-display-state");
    expect(tile(markup, "Ownership & UBO")).not.toContain("Waiting for earlier steps");
    expect(tile(markup, "Ownership & UBO")).toContain(">Blocked<");
    // Stages after the open Ownership exception still wait for it.
    expect(tile(markup, "Final review & send")).toContain(">Waiting for earlier steps<");
    expect(tile(markup, "Ownership & UBO")).toContain(">Resolve issue<");
  });

  it("keeps readiness-derived steps blocked when a later readiness blocker is not a prerequisite", () => {
    const summary = pendingDocuments();
    summary.clm.readiness.blockers = ["DOCUMENT_REQUIRED", "GOLDTIER_CLASSIFICATION_REQUIRED"];
    const markup = renderToStaticMarkup(<OnboardingProgressPanel summary={summary} onStageActivate={() => undefined} />);
    expect(tile(markup, "GoldTier Details & Status")).not.toContain("data-display-state");
    expect(tile(markup, "GoldTier Details & Status")).toContain(">Blocked<");
    expect(tile(markup, "Final review & send")).not.toContain("data-display-state");
    // Ownership does not derive from the readiness list, so it still only waits.
    expect(tile(markup, "Ownership & UBO")).toContain(">Waiting for earlier steps<");
  });

  it("keeps the backend display during recovery and for legacy stage order", () => {
    for (const overrides of [{ status: "RECOVERY_PENDING" }, { status: "TECHNICAL_FAILURE" }, { stage_order_version: 1 }]) {
      const markup = renderToStaticMarkup(<OnboardingProgressPanel summary={pendingDocuments(overrides)} />);
      expect(markup).not.toContain("data-display-state");
      expect(markup).not.toContain("Waiting for earlier steps");
      expect(tile(markup, "Ownership & UBO")).toContain(">Blocked<");
    }
  });

  it("shows the authoritative backend status in stage details and the technical processing record", () => {
    const summary = pendingDocuments();
    const details = renderToStaticMarkup(<OnboardingProgressPanel summary={summary} initialFocusNodeId="OWNERSHIP_UBO" />);
    // initialFocusNodeId is applied in an effect; render the stage facts through the rail instead.
    const rail = renderToStaticMarkup(<PipelineRail summary={summary} />);
    expect(rail).toMatch(/data-node-id="OWNERSHIP_UBO" data-status="BLOCKED" data-display-state="waiting"/);
    expect(rail).toContain("<strong>Status:</strong> Waiting for earlier steps");
    expect(rail).toContain("<strong>Backend status:</strong> Blocked");
    expect(rail).toMatch(/data-node-id="DOCUMENT_IDP" data-status="BLOCKED">.*?ds-stage-node attention/);
    expect(rail).toMatch(/data-node-id="OWNERSHIP_UBO"[^>]*>.*?ds-stage-node "/);
    const inspector = renderToStaticMarkup(<DetailedProcessingInspector summary={summary} />);
    expect(inspector).not.toContain("Waiting for earlier steps");
    expect(inspector.match(/aria-label="Status: BLOCKED"/g)).toHaveLength(5);
    expect(details).toContain("2 of 7 stages done");
  });
});

// D-141 (amends D-121 display only): an advisory ownership review is amber "Review advised", never green.
describe("Ownership & UBO advisory review display", () => {
  type OwnershipState = "blocking" | "advised" | "complete";
  function ownershipSummary(state: OwnershipState): ZeroTouchCaseSummary {
    const ownership: ProcessingNode = {
      ...processingNode("OWNERSHIP_UBO", "Ownership & UBO", state === "blocking" ? "REVIEW_REQUIRED" : "COMPLETE"),
      advisory_review: state === "advised" ? true : null,
    };
    const summary = summaryWithPipeline([
      processingNode("ACRA_REGISTRY", "Registry verification", "COMPLETE"),
      processingNode("DOCUMENT_IDP", "Document verification", "COMPLETE"),
      ownership,
      processingNode("ADVISORY", "Risk assessment", "NOT_REACHED"),
    ]);
    summary.current_stage = state === "blocking" ? "OWNERSHIP" : "READINESS";
    summary.completed_stages = state === "blocking" ? ["REGISTRY", "DOCUMENT"] : ["REGISTRY", "DOCUMENT", "OWNERSHIP"];
    return summary;
  }
  const header = (summary: ZeroTouchCaseSummary) => {
    // Server rendering only: silence React's useLayoutEffect notice for the client-side disclosure.
    const quiet = vi.spyOn(console, "error").mockImplementation(() => undefined);
    try {
      return renderToStaticMarkup(
        <StageDisclosure title="Ownership & UBO" status={stageStatusFor(summary, ["OWNERSHIP_UBO"])} summary="Ownership summary." scopeKey="case" main={<p>Body</p>} />,
      );
    } finally {
      quiet.mockRestore();
    }
  };
  const railStep = (summary: ZeroTouchCaseSummary) => {
    const rail = renderToStaticMarkup(<PipelineRail summary={summary} />);
    const start = rail.indexOf('data-node-id="OWNERSHIP_UBO"');
    return rail.slice(start, rail.indexOf('data-node-id="ADVISORY"', start));
  };

  it("shows a blocking review as the existing red Review required", () => {
    const summary = ownershipSummary("blocking");
    expect(stageStatusFor(summary, ["OWNERSHIP_UBO"])).toEqual({ tone: "attention", label: "Review required" });
    expect(header(summary)).toContain('data-tone="attention"');
    expect(header(summary)).toContain(">Review required<");
    const step = railStep(summary);
    expect(step).toContain("ds-stage-node attention");
    expect(step).not.toContain("advised");
    expect(step).not.toContain("Review advised");
  });

  it("shows an advisory review as amber Review advised, never a green Complete", () => {
    const summary = ownershipSummary("advised");
    expect(stageStatusFor(summary, ["OWNERSHIP_UBO"])).toEqual({ tone: "advised", label: "Review advised" });
    const chip = header(summary);
    expect(chip).toContain('data-tone="advised"');
    expect(chip).not.toContain('data-tone="done"');
    // The chip carries the words, not colour alone.
    expect(chip).toMatch(/class="stage-disclosure__status"[^>]*>Review advised</);
    const step = railStep(summary);
    expect(step).toMatch(/^data-node-id="OWNERSHIP_UBO" data-status="COMPLETE" data-display-state="advised"/);
    expect(step).toContain("ds-stage-node advised");
    expect(step).not.toContain("ds-stage-node done");
    expect(step).not.toContain("✓");
    // The sidebar marker is accompanied by visible status text.
    expect(step).toContain('<div class="text-muted">Review advised</div>');
    expect(step).toContain("<strong>Status:</strong> Review advised");
    expect(step).not.toContain(">Complete<");
  });

  it("shows the advisory review on the progress tile with amber state and a Review action", () => {
    const markup = renderToStaticMarkup(<OnboardingProgressPanel summary={ownershipSummary("advised")} onStageActivate={() => undefined} />);
    const start = markup.indexOf('aria-label="Open details for Ownership &amp; UBO"');
    const tileStart = markup.lastIndexOf("<li", start);
    const tile = markup.slice(tileStart, markup.indexOf("</li>", start));
    expect(tile).toContain('data-status="COMPLETE"');
    expect(tile).toContain('data-display-state="advised"');
    expect(tile).toContain(">Review advised<");
    expect(tile).not.toContain(">Complete<");
  });

  it("keeps green Complete when there is no open review", () => {
    const summary = ownershipSummary("complete");
    expect(stageStatusFor(summary, ["OWNERSHIP_UBO"])).toEqual({ tone: "done", label: "Complete" });
    expect(header(summary)).toContain('data-tone="done"');
    const step = railStep(summary);
    expect(step).toContain("ds-stage-node done");
    expect(step).not.toContain("advised");
    expect(step).toContain('<div class="text-muted">Complete</div>');
  });
});
