import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router";
import { QueryClientProvider } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";

import App, {
  OperatorAccount,
  createRetainedCaseBeforeDocumentIntake,
  isRegistryIntakeUnavailable,
  resetNewCasePresentation,
  targetedIntakeFailurePresentation,
  validateIntakeFiles,
} from "./App";
import {
  ApiError,
  createZeroTouchCase,
  fetchZeroTouchCase,
  fetchZeroTouchCases,
  replaceZeroTouchDocument,
  retryZeroTouchIntakeDocument,
} from "./api";
import { shouldRefreshAfterMutationError } from "./pages/CaseDetail";
import {
  CompletedOverview,
  ConfirmDetailsPanel,
  jurisdictionProgressState,
  RegistryStatePanel,
  registryOperationProgressState,
  registryRouteProgressState,
} from "./pages/CaseStatePanels";
import { PolicyClassificationBadge } from "./pages/PolicyRules";
import { isDocumentReuploadRequired } from "./pages/DocumentEvidencePanel";
import HomeOnboarding from "./pages/HomeOnboarding";
import HumanInterventionPanel from "./pages/HumanInterventionPanel";
import { createSessionQueryClient } from "./queryClient";
import type { AuthenticatedProfile, DocumentProcessingRecord, ReconciliationSummary, SimulationProfile, ZeroTouchCaseListItem, ZeroTouchCaseSummary } from "./types";
import {
  mapExecutionProfileToPolicy,
  mapZeroTouchCaseToCaseRow,
} from "./viewModels";

const listItem: ZeroTouchCaseListItem = {
  case_id: "00000000-0000-4000-8000-000000000001",
  team_id: "TEAM_A",
  client_scope_label: "DBS",
  priority: 8,
  requested_uen: "202400001A",
  legal_name: "SYNTHETIC COMPANY PTE. LTD.",
  status: "COMPLETED",
  current_stage: "COMPLETE",
  updated_at: "2026-09-01T01:00:00Z",
  active_exception_count: 0,
  active_exception_types: [],
  human_interventions: 0,
  final_outcome: "MOCK_GOLDTIER_SUBMITTED",
  resolved_jurisdiction: "SG",
  created_at: "2026-09-01T00:00:00Z",
  completed_at: "2026-09-01T01:00:00Z",
  mock_goldtier_party_id: "GT-MOCK-1",
};

const actor: AuthenticatedProfile = {
  user_id: "maya-lim",
  display_name: "Maya Lim",
  role: "CLIENT_ONBOARDER" as const,
  team_id: "TEAM_A" as const,
  team_display_name: "DBS Corporate Onboarding",
  team_type: "Corporate Client Onboarding",
  team_description: "Type: Corporate Client Onboarding | Client coverage: DBS",
  client_scope_label: "DBS",
  capabilities: ["POLICY_VIEW", "CASE_ACCESS"],
};

const summary = {
  case: { case_id: listItem.case_id },
  timeline: [{
    sequence: 1,
    event_type: "ZERO_TOUCH_CASE_CREATED",
    status: "PENDING_INPUTS",
    stage: "DOCUMENT",
    outcome: "SUCCEEDED",
    timestamp: listItem.updated_at,
    case_id: listItem.case_id,
    code: null,
    message: "The backend created the case.",
  }],
} as unknown as ZeroTouchCaseSummary;

function makePanelSummary(
  reconciliationOutcome: ReconciliationSummary["fields"][number]["outcome"] = "MATCH",
  status: ZeroTouchCaseSummary["status"] = "RUNNING",
): ZeroTouchCaseSummary {
  const observation = {
    observation_id: "observation-1",
    field_name: "legal_name",
    normalized_value: "SYNTHETIC COMPANY PTE. LTD.",
    source_kind: "REGISTRY",
    source_system: "ACRA",
    environment: "MOCK",
    observed_at: listItem.updated_at,
    evidence_reference: "safe:registry:1",
    confidence: null,
    validity: "VALID",
  } as const;
  const discrepancy = ["MATCH", "REGISTRY_ONLY"].includes(reconciliationOutcome) ? null : {
    discrepancy_id: "discrepancy-1",
    field_name: "legal_name",
    outcome: reconciliationOutcome,
    observations: [observation],
    status: "OPEN",
    allowed_actions: reconciliationOutcome === "CONFLICT" ? ["KEEP_REGISTRY_VALUE"] : [],
    evidence_fingerprint: "a".repeat(64),
    decision: null,
  };
  return {
    case: {
      case_id: listItem.case_id,
      requested_uen: listItem.requested_uen,
      jurisdiction_resolution: {
        status: "RESOLVED",
        resolved_jurisdiction: "SG",
        observations: [{ jurisdiction: "SG", source: "IDENTIFIER_FORMAT", observed_at: listItem.updated_at, evidence_reference: "safe:uen", confidence: null }],
        resolved_at: listItem.updated_at,
      },
      registry_route: { status: "SELECTED", jurisdiction: "SG", provider: "ACRA", decided_at: listItem.updated_at },
      registry_acquisition: {
        requested_identifier: listItem.requested_uen,
        status: "COMPLETE",
        officers: [],
        ownership_parties: [],
        relationships: [],
        operation_results: ["ENTITY_PROFILE", "OFFICERS", "OWNERSHIP_PARTIES", "RELATIONSHIPS"].map((operation) => ({
          operation,
          status: operation === "OFFICERS" ? "EMPTY" : "COMPLETE",
          record_count: operation === "OFFICERS" ? 0 : 1,
          provenance: { provider: "ACRA", environment: "MOCK", operation, retrieved_at: listItem.updated_at, evidence_reference: `safe:${operation}` },
          error: null,
        })),
        issues: [],
        retrieved_at: listItem.updated_at,
      },
      entity: { legal_name: listItem.legal_name, source: { environment: "MOCK" } },
      goldtier_result: status === "COMPLETED" ? { party_id: "GT-MOCK-1" } : null,
    },
    status,
    current_stage: status === "COMPLETED" ? "COMPLETE" : "REGISTRY",
    completed_stages: status === "COMPLETED" ? ["REGISTRY", "DOCUMENT", "OWNERSHIP", "READINESS", "MOCK_GOLDTIER", "COMPLETE"] : [],
    active_exceptions: [],
    technical_failure: null,
    reconciliation: {
      reconciliation_id: "reconciliation-1",
      version: 1,
      status: ["MATCH", "REGISTRY_ONLY"].includes(reconciliationOutcome) ? "MATCHED" : "REVIEW_REQUIRED",
      source_document_ids: [],
      source_document_event_counts: [],
      fields: [{ field_name: "legal_name", observations: [observation], outcome: reconciliationOutcome, discrepancy_id: discrepancy?.discrepancy_id ?? null }],
      discrepancies: discrepancy ? [discrepancy] : [],
      updated_at: listItem.updated_at,
    },
    metrics: { automated_stages_completed: status === "COMPLETED" ? 6 : 0, human_interventions: 0, exceptions_raised: 0, exceptions_resolved: 0, final_outcome: status === "COMPLETED" ? "MOCK_GOLDTIER_SUBMITTED" : null, total_duration_ms: status === "COMPLETED" ? 1200 : null, stage_durations_ms: {} },
    timeline: status === "COMPLETED" ? [{ sequence: 1, event_type: "MOCK_SUBMISSION_COMPLETED", status: "COMPLETED", stage: "COMPLETE", outcome: "SUCCEEDED", timestamp: listItem.updated_at, case_id: listItem.case_id, code: null, message: "Completed" }] : [],
    created_at: "2026-08-31T01:00:00Z",
    updated_at: listItem.updated_at,
  } as unknown as ZeroTouchCaseSummary;
}

afterEach(() => vi.unstubAllGlobals());

describe("UI v2 backend integration adapters", () => {
  it("preserves the screenshot navigation and multi-format/folder uploader", () => {
    const markup = renderToStaticMarkup(<MemoryRouter initialEntries={["/new-onboarding"]}><QueryClientProvider client={createSessionQueryClient()}><App actor={actor} onLogout={() => undefined} /></QueryClientProvider></MemoryRouter>);
    expect(markup).not.toContain('href="/onboarded"'); // the Onboarded tab was folded into Cases
    for (const label of ["Autoboard", "New onboarding", "Cases", "Audit", "Policy", "Signed in as", "Maya Lim"]) {
      expect(markup).toContain(label);
    }
    expect(markup).toContain("nav-tab--active");
    expect(markup).toContain("Start onboarding");
    expect(markup).toContain("webkitdirectory");
    expect(markup).toContain("application/pdf");
    expect(markup).toContain(".docx");
    expect(markup).toContain("text/plain");
  });

  it("validates PDF, DOCX, TXT, per-file, count, and total intake limits", () => {
    const accepted = [
      new File(["pdf"], "a.pdf", { type: "application/pdf" }),
      new File(["docx"], "b.docx", { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" }),
      new File(["txt"], "c.txt", { type: "text/plain" }),
    ];
    expect(validateIntakeFiles(accepted)).toBeNull();
    expect(validateIntakeFiles(Array.from({ length: 21 }, (_, index) => new File(["x"], `${index}.txt`, { type: "text/plain" })))).toContain("20");
    expect(validateIntakeFiles([new File([new Uint8Array(5 * 1024 * 1024 + 1)], "large.pdf", { type: "application/pdf" })])).toContain("5 MiB");
    const total = Array.from({ length: 6 }, (_, index) => new File([new Uint8Array(5 * 1024 * 1024)], `${index}.pdf`, { type: "application/pdf" }));
    expect(validateIntakeFiles(total)).toContain("25 MiB");
  });

  it("maps backend list items without inventing assignment, client IDs, or risk", () => {
    const row = mapZeroTouchCaseToCaseRow(listItem);
    expect(row).toMatchObject({ active_exception_types: [], jurisdiction: "SG", status: "COMPLETED" });
    expect(row).not.toHaveProperty("assigned_to");
    expect(row.goldtier_party_id).toBe("GT-MOCK-1");
  });

  it("maps execution-profile truth and marks unsupported policy fields unavailable", () => {
    const profile: SimulationProfile = {
      is_simulated: true,
      registry_system: "ACRA",
      registry_environment: "MOCK",
      target_system: "GOLDTIER",
      target_environment: "MOCK",
      target_provider_classification: "MOCK",
      idp_system: "IDP",
      idp_environment: "LOCAL",
      idp_provider: "LOCAL_PDF_TEXT",
      idp_review_confidence_threshold: 0.85,
      ownership_system: "OWNERSHIP_PROVIDER",
      ownership_environment: "MOCK",
      ubo_ownership_threshold_percent: "25",
      persistence: "Mongo-backed durable POC",
    };
    const policy = mapExecutionProfileToPolicy(profile);
    expect(policy.execution.persistence.value).toBe("Mongo-backed durable POC");
    expect(policy.jurisdiction_rules.find((item) => item.jurisdiction === "SG")?.implemented.value).toBe(true);
    expect(policy.scheduler.next_review_months_low.value).toBe("Not available in current POC");
  });

  it("does not preserve unsupported assignment or generic rework actions in the bounded case-detail slice", () => {
    expect(renderToStaticMarkup(<ConfirmDetailsPanel summary={makePanelSummary()} />)).not.toMatch(/Assign reviewer|Return for rework/);
    expect(JSON.stringify(summary)).not.toMatch(/assign-reviewer|return-for-rework/);
  });

  it("uses the real case-list route with the accepted status filter", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify([listItem]), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(fetchZeroTouchCases("COMPLETED")).resolves.toEqual([listItem]);
    expect(fetchMock.mock.calls[0][0]).toBe("/api/clm/zero-touch/cases?status=COMPLETED");
  });

  it.each([400, 409, 422, 500])("preserves backend %i errors without mock success", async (status) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: { code: `E_${status}`, message: "Safe backend message" } }), { status })));
    await expect(createZeroTouchCase("202400001A")).rejects.toMatchObject({ status, code: `E_${status}` });
  });

  it("surfaces an unavailable backend without fabricating a case", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("network unavailable")));
    await expect(createZeroTouchCase("202400001A")).rejects.toThrow("network unavailable");
  });

  it("keeps safe ApiError metadata for targeted document retry", () => {
    const detail = { code: "DOCUMENT_REUPLOAD_REQUIRED", message: "Retry required", document_id: "doc-1", case_id: listItem.case_id };
    const error = new ApiError(detail.message, 409, detail.code, detail);
    expect(error.detail?.document_id).toBe("doc-1");
  });

  it("binds retry and replacement to the exact case, document, media, and event version", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ document_id: "failed-doc" }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(summary), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const txt = new File(["evidence"], "evidence.txt", { type: "text/plain" });

    await retryZeroTouchIntakeDocument(listItem.case_id, "failed-doc", txt, false);
    await replaceZeroTouchDocument(listItem.case_id, "current-doc", 4, txt);

    expect(fetchMock.mock.calls[0][0]).toContain(`/intake/documents/failed-doc/retry`);
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: "POST" });
    expect(fetchMock.mock.calls[1][0]).toContain(`/documents/current-doc/replacement`);
    const headers = new Headers(fetchMock.mock.calls[1][1]?.headers);
    expect(headers.get("Content-Type")).toBe("text/plain");
    expect(headers.get("X-Document-Name")).toBe("evidence.txt");
    expect(headers.get("X-Document-Event-Count")).toBe("4");
  });

  it("refreshes authoritative evidence after a stale 409 and not after unrelated failures", () => {
    expect(shouldRefreshAfterMutationError(new ApiError("stale", 409, "STALE_DECISION"))).toBe(true);
    expect(shouldRefreshAfterMutationError(new ApiError("invalid", 422, "INVALID"))).toBe(false);
    expect(shouldRefreshAfterMutationError(new ApiError("unavailable", 503, "UNAVAILABLE"))).toBe(true);
    expect(shouldRefreshAfterMutationError(new TypeError("network"))).toBe(true);
  });

  it("renders the authenticated profile separately from the execution profile", () => {
    const account = renderToStaticMarkup(<OperatorAccount profile={actor} onLogout={() => undefined} />);
    const app = renderToStaticMarkup(<MemoryRouter initialEntries={["/dashboard"]}><QueryClientProvider client={createSessionQueryClient()}><App actor={actor} onLogout={() => undefined} /></QueryClientProvider></MemoryRouter>);
    expect(account).toContain("Maya Lim");
    expect(account).toContain("DBS Corporate Onboarding");
    expect(account).toContain("Coverage: DBS");
    expect(account).toContain("aria-expanded=\"false\"");
    expect(app).toContain("nav-meta");
    expect(app).toContain("environment-banner");
    expect(app).toContain("operator-account");
    expect(account).not.toContain("Demo operator");
    expect(app).not.toContain("PingFed login");
  });

  it("renders real registry routing and all four acquisition operations", () => {
    const markup = renderToStaticMarkup(<RegistryStatePanel summary={makePanelSummary()} />);
    expect(markup).toContain("Reading the registry");
    for (const operation of ["entity profile", "officers", "ownership parties", "relationships"]) {
      expect(markup).toContain(operation);
    }
    expect(markup).toContain("ACRA MOCK");
    expect(markup).toContain("Provider classification follows the configured backend execution profile");
    expect(markup).not.toContain("Q-012");
  });

  it.each(["MATCH", "REGISTRY_ONLY", "MISSING_IN_SOURCE", "CONFLICT", "UNVERIFIABLE", "INVALID"] as const)(
    "renders the reconciliation outcome %s without inventing source precedence",
    (outcome) => {
      const summary = { ...makePanelSummary(outcome), current_stage: "DOCUMENT" as const };
      const markup = renderToStaticMarkup(<ConfirmDetailsPanel summary={summary} />);
      expect(markup).toContain("Confirm details");
      expect(markup).toContain(outcome.replaceAll("_", " ").toLowerCase());
      expect(markup).toContain("No source wins automatically");
      if (!["CONFLICT", "MATCH", "REGISTRY_ONLY"].includes(outcome)) expect(markup).toContain("Replacement evidence is required");
    },
  );

  it("renders truthful POC completion, GoldTier party label, and disabled audit download", () => {
    const markup = renderToStaticMarkup(<CompletedOverview summary={makePanelSummary("MATCH", "COMPLETED")} onViewAudit={() => undefined} />);
    expect(markup).toContain("Completed POC workflow");
    expect(markup).toContain("GoldTier party ID");
    expect(markup).toContain("GT-MOCK-1");
    expect(markup).toContain("Download audit trail");
    expect(markup).toContain("disabled");
    expect(markup).not.toContain("Ready for Approval");
  });

  it("detects restart-interrupted documents only from the backend recovery code", () => {
    const failed = {
      state: "FAILED",
      error: { code: "DOCUMENT_REUPLOAD_REQUIRED", message: "Re-upload required" },
    } as DocumentProcessingRecord;
    const ordinaryFailure = {
      state: "FAILED",
      error: { code: "PROCESSOR_FAILURE", message: "Processing failed" },
    } as DocumentProcessingRecord;
    expect(isDocumentReuploadRequired(failed)).toBe(true);
    expect(isDocumentReuploadRequired(ordinaryFailure)).toBe(false);
  });

  it("uses the lightweight list projection for every portfolio row field", () => {
    expect(mapZeroTouchCaseToCaseRow(listItem)).toMatchObject({ jurisdiction: "SG", created_at: listItem.created_at });
    expect(mapZeroTouchCaseToCaseRow(listItem)).toMatchObject({ goldtier_party_id: "GT-MOCK-1", completed_at: listItem.completed_at });
  });

  it("retains and routes a registry-stop case without attempting document intake", async () => {
    const registryStop = {
      ...makePanelSummary("MATCH"),
      status: "WAITING_FOR_REVIEW" as const,
      current_stage: "REGISTRY" as const,
      case: {
        ...makePanelSummary("MATCH").case,
        jurisdiction_resolution: {
          ...makePanelSummary("MATCH").case.jurisdiction_resolution!,
          status: "CONFLICT" as const,
          resolved_jurisdiction: null,
        },
        registry_route: null,
      },
    };
    const retained = vi.fn();
    const routed = vi.fn();
    const intake = vi.fn();

    const result = await createRetainedCaseBeforeDocumentIntake({
      createCase: async () => registryStop,
      onCreated: retained,
      onRegistryStop: routed,
      onDocumentIntake: intake,
    });

    expect(result).toMatchObject({ created: registryStop, intakeAttempted: false });
    expect(retained).toHaveBeenCalledWith(registryStop);
    expect(routed).toHaveBeenCalledWith(registryStop);
    expect(intake).not.toHaveBeenCalled();
    expect(isRegistryIntakeUnavailable(registryStop)).toBe(true);
    const markup = renderToStaticMarkup(<RegistryStatePanel summary={registryStop} />);
    expect(markup).toContain("Registry review required");
    expect(markup).not.toContain("Targeted retry required");
  });

  it("retains documents when GoldTier customer identity requires review before ACRA", async () => {
    const identityReview = {
      ...makePanelSummary("MATCH"),
      status: "WAITING_FOR_REVIEW" as const,
      current_stage: "GOLDTIER_SEARCH" as const,
      active_exceptions: [{
        exception_id: "identity-review-1",
        exception_type: "ENTITY_RESOLUTION_REVIEW_REQUIRED",
        stage: "GOLDTIER_SEARCH",
        blocker_code: "GT_SEARCH_IDENTITY_REVIEW_REQUIRED",
        explanation: "Two retained candidates require exact identity review.",
        evidence_version: "goldtier-search:1",
        available_actions: [],
      }],
    } as unknown as ZeroTouchCaseSummary;
    const retained = vi.fn();
    const routed = vi.fn();
    const intake = vi.fn().mockResolvedValue(undefined);

    await expect(createRetainedCaseBeforeDocumentIntake({
      createCase: async () => identityReview,
      onCreated: retained,
      onRegistryStop: routed,
      onDocumentIntake: intake,
    })).resolves.toMatchObject({ created: identityReview, intakeAttempted: true });
    expect(isRegistryIntakeUnavailable(identityReview)).toBe(false);
    expect(intake).toHaveBeenCalledWith(identityReview);
    expect(routed).not.toHaveBeenCalled();
  });

  it("keeps document intake open for retained registry expected-data gaps", async () => {
    const registryEvidenceGap = {
      ...makePanelSummary("MATCH"),
      status: "WAITING_FOR_REVIEW" as const,
      current_stage: "REGISTRY" as const,
      active_exceptions: [{
        exception_id: "registry-gap-1",
        exception_type: "REGISTRY_REVIEW_REQUIRED",
        stage: "REGISTRY",
        blocker_code: "REGISTRY_EXPECTED_DATA_MISSING",
        explanation: "Expected ownership evidence was not returned.",
        evidence_version: "case:1",
        available_actions: [],
      }],
      case: {
        ...makePanelSummary("MATCH").case,
        registry_acquisition: {
          ...makePanelSummary("MATCH").case.registry_acquisition!,
          status: "PARTIAL" as const,
        },
      },
    } as unknown as ZeroTouchCaseSummary;
    const intake = vi.fn().mockResolvedValue(undefined);

    await expect(createRetainedCaseBeforeDocumentIntake({
      createCase: async () => registryEvidenceGap,
      onCreated: () => undefined,
      onRegistryStop: () => undefined,
      onDocumentIntake: intake,
    })).resolves.toMatchObject({ intakeAttempted: true });
    expect(isRegistryIntakeUnavailable(registryEvidenceGap)).toBe(false);
    expect(intake).toHaveBeenCalledWith(registryEvidenceGap);
  });

  it("renders only backend-authored intervention actions and safe candidate summaries", () => {
    const exception = {
      exception_id: "identity-review-1",
      exception_type: "ENTITY_RESOLUTION_REVIEW_REQUIRED",
      stage: "GOLDTIER_SEARCH",
      blocker_code: "GT_SEARCH_IDENTITY_REVIEW_REQUIRED",
      explanation: "Two retained candidates require exact identity review.",
      evidence_version: "goldtier-search:1",
      available_actions: [],
    } as const;
    const interventionSummary = {
      ...makePanelSummary("MATCH"),
      active_exceptions: [exception],
      interventions: [{
        intervention_id: exception.exception_id,
        owning_stage: "GOLDTIER_SEARCH",
        owning_stage_label: "GoldTier Search / customer identity",
        title: "Possible existing customer found",
        blocker_code: exception.blocker_code,
        explanation: exception.explanation,
        required_evidence_or_input: ["Additional identity evidence."],
        authorized_actions: [],
        no_action_reason: "Candidate selection is not authorized.",
        expected_next_step: "Retain documents while target writes remain blocked.",
        candidate_summaries: [{
          party_id: "GT-SAFE-1",
          registration_number: "202400001A",
          country: "SG",
          legal_name: "SYNTHETIC COMPANY PTE. LTD.",
          legal_form: null,
        }],
      }],
    } as unknown as ZeroTouchCaseSummary;

    const markup = renderToStaticMarkup(
      <HumanInterventionPanel
        summary={interventionSummary}
        isBusy={false}
        onResolve={() => undefined}
      />,
    );
    expect(markup).toContain("Possible existing customer found");
    expect(markup).toContain("GT-SAFE-1");
    expect(markup).toContain("No action available");
    expect(markup).not.toContain("Confirm candidate");
  });

  it("renders a registry-stage authorized action once through the shared panel", () => {
    const registryActionSummary = {
      ...makePanelSummary("MATCH"),
      active_exceptions: [{
        exception_id: "registry-action-1",
        exception_type: "REGISTRY_REVIEW_REQUIRED",
        stage: "REGISTRY",
        blocker_code: "REGISTRY_SOURCE_CONFLICT",
        explanation: "Registry evidence requires a bounded decision.",
        evidence_version: "case:1",
        available_actions: ["KEEP_REGISTRY_VALUE"],
      }],
      interventions: [{
        intervention_id: "registry-action-1",
        owning_stage: "REGISTRY",
        owning_stage_label: "ACRA registry",
        title: "Action required — ACRA registry",
        blocker_code: "REGISTRY_SOURCE_CONFLICT",
        explanation: "Registry evidence requires a bounded decision.",
        required_evidence_or_input: ["Review retained evidence."],
        authorized_actions: [{
          action: "KEEP_REGISTRY_VALUE",
          label: "Keep registry value",
          description: "Retain the observed registry value.",
        }],
        no_action_reason: null,
        expected_next_step: "The backend will re-evaluate the case.",
        candidate_summaries: [],
      }],
    } as unknown as ZeroTouchCaseSummary;

    const markup = renderToStaticMarkup(
      <HumanInterventionPanel
        summary={registryActionSummary}
        isBusy={false}
        onResolve={() => undefined}
      />,
    );
    expect(markup.match(/Keep registry value/g)).toHaveLength(1);
    expect(markup).toContain("Backend-authorized actions");
  });

  it("shows the confirmation next step without inventing an unavailable action", () => {
    const summary = {
      ...makePanelSummary("MATCH"),
      interventions: [{
        intervention_id: "confirmation-1", owning_stage: "READINESS",
        owning_stage_label: "Readiness", title: "Confirm frozen target submission",
        blocker_code: "TARGET_CONFIRMATION_REQUIRED", explanation: "Confirmation required.",
        required_evidence_or_input: ["Review frozen destination and digest."],
        authorized_actions: [], no_action_reason: null,
        expected_next_step: "Use the confirmation control in Review and Send.",
        candidate_summaries: [],
      }],
    } as unknown as ZeroTouchCaseSummary;
    const markup = renderToStaticMarkup(
      <HumanInterventionPanel summary={summary} isBusy={false} onResolve={() => undefined} />,
    );
    expect(markup).toContain("Review and Send");
    expect(markup).not.toContain("No action available");
  });

  it("renders the prominent new-case action with a stable accessible name", () => {
    const markup = renderToStaticMarkup(
      <HomeOnboarding
        summary={makePanelSummary("MATCH", "COMPLETED")}
        uen="202400001A"
        onUenChange={() => undefined}
        countryOfIncorporation="SG"
        onCountryChange={() => undefined}
        documentFiles={[]}
        onDocumentFilesChange={() => undefined}
        caseTeamDisplayName="DBS Corporate Onboarding"
        priority=""
        onPriorityChange={() => undefined}
        isSubmitting={false}
        isResolving={false}
        requestError={null}
        pollingWarning={null}
        intakeProgress={null}
        onStart={() => undefined}
        onResolve={() => undefined}
        onReconcile={() => undefined}
        onReplace={() => undefined}
        onRecovery={() => undefined}
        onStartNewCase={() => undefined}
        onViewAudit={() => undefined}
      />,
    );
    expect(markup).toContain('aria-label="Start a new case"');
    expect(markup).toContain("+ Start a new case");
    expect(markup).toContain("new-case-cta");
  });

  it("continues normal document intake after retaining an intake-open case", async () => {
    const intakeOpen = {
      ...makePanelSummary("MATCH"),
      status: "PENDING_INPUTS" as const,
      current_stage: "DOCUMENT" as const,
    };
    const retained = vi.fn();
    const routed = vi.fn();
    const intake = vi.fn().mockResolvedValue(undefined);

    await expect(createRetainedCaseBeforeDocumentIntake({
      createCase: async () => intakeOpen,
      onCreated: retained,
      onRegistryStop: routed,
      onDocumentIntake: intake,
    })).resolves.toMatchObject({ created: intakeOpen, intakeAttempted: true });
    expect(retained).toHaveBeenCalledBefore(intake);
    expect(routed).not.toHaveBeenCalled();
    expect(intake).toHaveBeenCalledWith(intakeOpen);
  });

  it("keeps document failures on the exact retained-case targeted retry path", () => {
    const presentation = targetedIntakeFailurePresentation(listItem.case_id, ["profile.pdf: processing failed"]);
    expect(presentation.progress).toBe("Targeted retry required");
    expect(presentation.message).toContain(`Case ${listItem.case_id} was retained.`);
    expect(presentation.message).toContain("Retry the same selection");
  });

  it("reopens a retained registry-stop case from Cases by its exact ID", async () => {
    const registryStop = {
      ...makePanelSummary("MATCH"),
      status: "WAITING_FOR_REVIEW" as const,
      current_stage: "REGISTRY" as const,
    };
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify([{ ...listItem, status: "WAITING_FOR_REVIEW", current_stage: "REGISTRY" }]), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(registryStop), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const cases = await fetchZeroTouchCases();
    const reopened = await fetchZeroTouchCase(cases[0].case_id);

    expect(reopened.case.case_id).toBe(listItem.case_id);
    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      "/api/clm/zero-touch/cases",
      `/api/clm/zero-touch/cases/${listItem.case_id}`,
    ]);
  });

  it("clears every transient new-case presentation state without deleting persisted cases", async () => {
    const resetters = Array.from({ length: 11 }, () => vi.fn());
    resetNewCasePresentation({
      clearSummary: resetters[0],
      clearRetainedSummary: resetters[1],
      clearDocuments: resetters[2],
      clearOpenedCaseId: resetters[3],
      resetUen: resetters[4],
      resetJurisdiction: resetters[5],
      clearRequestError: resetters[6],
      clearPollingWarning: resetters[7],
      clearIntakeProgress: resetters[8],
      clearSubmitting: resetters[9],
      clearResolving: resetters[10],
    });
    resetters.forEach((resetter) => expect(resetter).toHaveBeenCalledOnce());

    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify([listItem]), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(fetchZeroTouchCases()).resolves.toEqual([listItem]);
  });

  it.each([
    ["selected SG route", registryRouteProgressState("SELECTED"), "SUCCESS"],
    ["jurisdiction conflict", jurisdictionProgressState("CONFLICT"), "ATTENTION"],
    ["route not selected", registryRouteProgressState(undefined), "NOT_SELECTED"],
    ["failed registry operation", registryOperationProgressState("FAILED"), "FAILED"],
    ["pending jurisdiction", jurisdictionProgressState(undefined), "PENDING"],
  ])("maps %s to semantic state %s", (_label, actual, expected) => {
    expect(actual).toBe(expected);
    if (expected !== "SUCCESS") expect(actual).not.toBe("SUCCESS");
  });

  it("represents all four explicit Policy classifications and keeps open questions non-REAL", () => {
    const profile: SimulationProfile = {
      is_simulated: true,
      registry_system: "ACRA",
      registry_environment: "MOCK",
      target_system: "GOLDTIER",
      target_environment: "MOCK",
      target_provider_classification: "MOCK",
      idp_system: "IDP",
      idp_environment: "LOCAL",
      idp_provider: "LOCAL_PDF_TEXT",
      idp_review_confidence_threshold: 0.85,
      ownership_system: "OWNERSHIP_PROVIDER",
      ownership_environment: "MOCK",
      ubo_ownership_threshold_percent: "25",
      persistence: "Process-local",
    };
    const policy = mapExecutionProfileToPolicy(profile);
    const classifications = [
      ...policy.open_questions.map((item) => item.classification),
      ...policy.jurisdiction_rules.flatMap((rule) => [rule.implemented.classification, rule.id_label.classification, rule.registry.classification, rule.ubo_threshold_percent.classification]),
      policy.pipeline.stages.classification,
      policy.pipeline.screening_auto_clear_threshold.classification,
      policy.pipeline.idp_review_confidence_threshold.classification,
      policy.pipeline.registry_snapshot_staleness_limit_days.classification,
      policy.roles.reviewer_count.classification,
      policy.roles.self_review_blocked.classification,
      ...Object.values(policy.scheduler).map((item) => item.classification),
      ...Object.values(policy.execution).map((item) => item.classification),
    ];
    expect(new Set(classifications)).toEqual(new Set(["REAL", "DERIVED", "PENDING SPONSOR CONFIRMATION", "UNAVAILABLE"]));
    expect(policy.open_questions.every((item) => item.classification === "PENDING SPONSOR CONFIRMATION")).toBe(true);
    const badges = renderToStaticMarkup(<>{["REAL", "DERIVED", "PENDING SPONSOR CONFIRMATION", "UNAVAILABLE"].map((classification) => <PolicyClassificationBadge key={classification} classification={classification as "REAL" | "DERIVED" | "PENDING SPONSOR CONFIRMATION" | "UNAVAILABLE"} />)}</>);
    for (const classification of ["REAL", "DERIVED", "PENDING SPONSOR CONFIRMATION", "UNAVAILABLE"]) expect(badges).toContain(classification);
  });
});
