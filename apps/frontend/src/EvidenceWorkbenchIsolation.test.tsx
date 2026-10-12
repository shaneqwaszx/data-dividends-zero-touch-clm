// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { caseQueryKeys } from "./caseQueries";
import CaseDetail from "./pages/CaseDetail";
import { createSessionQueryClient } from "./queryClient";
import attentionProjections from "./test-fixtures/attention-projections.json";
import type {
  AuthenticatedProfile,
  DocumentProcessingRecord,
  OwnershipAnalysisRecord,
  OwnershipPath,
  ZeroTouchCaseSummary,
  ZeroTouchException,
} from "./types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const CASE_A = "00000000-0000-4000-8000-000000000e1a";
const CASE_B = "00000000-0000-4000-8000-000000000e1b";
const NOW = "2026-09-21T01:00:00Z";

const actorA: AuthenticatedProfile = {
  user_id: "evidence-reader-a",
  display_name: "Evidence Reader A",
  role: "CLIENT_ONBOARDER",
  team_id: "TEAM_A",
  team_display_name: "Team A",
  team_type: "Corporate Client Onboarding",
  team_description: "Synthetic team",
  client_scope_label: "Team A clients",
  capabilities: ["CASE_ACCESS", "POLICY_VIEW"],
};

const actorB: AuthenticatedProfile = {
  ...actorA,
  user_id: "evidence-reader-b",
  display_name: "Evidence Reader B",
};

function summaryFixture(caseId: string, label = "EVIDENCE CASE"): ZeroTouchCaseSummary {
  const exception: ZeroTouchException = {
    exception_id: `${caseId}-exception`,
    case_id: caseId,
    exception_type: "DOCUMENT_REVIEW_REQUIRED",
    stage: "DOCUMENT",
    status: "OPEN",
    blocker_code: "DOCUMENT_SOURCE_CONFLICT",
    blocker_codes: ["DOCUMENT_SOURCE_CONFLICT"],
    explanation: "Registry and document evidence require retained human review.",
    evidence_version: "evidence-v1",
    automation_version: 1,
    evidence: [],
    available_actions: [],
    created_at: NOW,
    resolved_at: null,
    resolution: null,
  };
  return {
    case: {
      case_id: caseId,
      requested_uen: label,
      priority: 5,
      client_scope_label: "Team A clients",
      entity: { legal_name: label },
      jurisdiction_resolution: null,
      registry_acquisition: null,
      registry_evidence_binding: null,
      goldtier_result: null,
      events: [{ sequence: 1, event_type: "CASE_CREATED", timestamp: NOW }],
    },
    evidence_decision_authorized: true,
    ownership_edit_authorized: false,
    automation_id: `${caseId}-automation`,
    version: 1,
    status: "WAITING_FOR_REVIEW",
    current_stage: "DOCUMENT",
    completed_stages: ["REGISTRY"],
    active_exceptions: [exception],
    technical_failure: null,
    reconciliation: null,
    metrics: {
      automated_stages_completed: 1,
      human_interventions: 0,
      exceptions_raised: 1,
      exceptions_resolved: 0,
      final_outcome: null,
      total_duration_ms: null,
      stage_durations_ms: {},
    },
    clm: {
      readiness: {
        registry: { status: "READY" },
        document: { status: "REVIEW_REQUIRED" },
        ownership: { status: "READY" },
        goldtier: { status: "NOT_SUBMITTED" },
        blockers: ["Retained document conflict requires review."],
        warnings: [],
      },
      submission_plan: {
        environment: "MOCK",
        base_operations: [],
        real_ready_for_approval: "NOT_AVAILABLE",
      },
    },
    target_operations: [],
    timeline: [],
    timing: {
      observed_at: NOW,
      case_elapsed_ms: 0,
      time_since_last_update_ms: 0,
      automation_elapsed_ms: null,
      recorded_total_duration_ms: null,
    },
    created_at: NOW,
    updated_at: NOW,
  } as unknown as ZeroTouchCaseSummary;
}

function documentFixture(caseId: string): DocumentProcessingRecord {
  return {
    case_id: caseId,
    document_id: `${caseId}-document`,
    correlation_id: `${caseId}-correlation`,
    display_name: "evidence-package.pdf",
    media_type: "application/pdf",
    size_bytes: 8,
    profile: "PROVISIONAL_CORPORATE",
    provider_environment: "LOCAL",
    state: "REVIEW_REQUIRED",
    review_source_fingerprint: "a".repeat(64),
    fields: [{
      field_key: "legal_name",
      original_extracted_value: "EVIDENCE CASE",
      normalized_value: "EVIDENCE CASE",
      confidence: 0.97,
      provenance: {
        provider: "LOCAL_PDF_TEXT",
        environment: "LOCAL",
        page_number: 1,
        source_reference: "safe:evidence-workbench",
      },
      canonical_value: "EVIDENCE CASE",
      comparison_status: "MISMATCH",
      review_status: "PENDING",
      reviewed_value: null,
      reviewed_at: null,
      review_note: null,
    }],
    events: [],
    error: null,
    created_at: NOW,
    processed_at: NOW,
    reviewed_at: null,
    updated_at: NOW,
    supersedes_document_id: null,
    superseded_by_document_id: null,
  } as DocumentProcessingRecord;
}

function retainedPath(id: string, percent: string): OwnershipPath {
  return {
    path_id: id,
    effective_ownership_percent: percent,
    is_direct: true,
    calculation: `${percent} retained exactly`,
    edges: [{
      relationship_id: `${id}-relationship`,
      parent_party_id: `${id}-entity`,
      parent_display_name: `${id} owned entity`,
      child_party_id: `${id}-owner`,
      child_display_name: `${id} owner`,
      ownership_percent: percent,
    }],
  };
}

function ownershipFixture(caseId: string, analysisId: string, pathPrefix = "a"): OwnershipAnalysisRecord {
  const first = retainedPath(`${pathPrefix}-path-1`, "25.000000000000000001");
  const second = retainedPath(`${pathPrefix}-path-2`, "12.500000000000000009");
  const value: OwnershipAnalysisRecord = {
    case_id: caseId,
    analysis_id: analysisId,
    correlation_id: `${analysisId}-correlation`,
    root_party_id: `${analysisId}-root`,
    provider_name: "DECIMAL_GRAPH_ENGINE",
    provider_environment: "LOCAL",
    state: "REVIEW_REQUIRED",
    parties: [],
    relationships: [],
    candidates: [{
      party: {
        party_id: `${analysisId}-candidate-1`,
        display_name: `${pathPrefix} Candidate One`,
        party_type: "NATURAL_PERSON",
        registration_number: null,
        country: "SG",
      },
      direct_ownership_percent: "25.000000000000000001",
      indirect_ownership_percent: "12.500000000000000009",
      aggregated_ownership_percent: "37.500000000000000010",
      threshold_percent: "25.000000000000000000",
      threshold_comparator: "GREATER_THAN_OR_EQUAL_TO",
      threshold_result: "MET",
      classification: "REVIEW_REQUIRED",
      paths: [first, second],
    }, {
      party: {
        party_id: `${analysisId}-candidate-2`,
        display_name: `${pathPrefix} Candidate Two`,
        party_type: "NATURAL_PERSON",
        registration_number: null,
        country: "SG",
      },
      direct_ownership_percent: "30.000000000000000000",
      indirect_ownership_percent: "0.000000000000000000",
      aggregated_ownership_percent: "30.000000000000000000",
      threshold_percent: "25.000000000000000000",
      threshold_comparator: "GREATER_THAN_OR_EQUAL_TO",
      threshold_result: "MET",
      classification: "PROVISIONAL_UBO_CANDIDATE",
      paths: [retainedPath(`${pathPrefix}-candidate-two-path`, "30.000000000000000000")],
    }],
    issues: [],
    threshold_percent: "25.000000000000000000",
    threshold_comparator: "GREATER_THAN_OR_EQUAL_TO",
    events: [],
    error: null,
    created_at: NOW,
    loaded_at: NOW,
    analyzed_at: NOW,
    updated_at: NOW,
  };
  value.parties = value.candidates.map(item => item.party);
  return value;
}

function createTestClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { staleTime: Infinity, gcTime: Infinity, retry: false },
      mutations: { retry: false },
    },
  });
}

function seedCase(
  client: QueryClient,
  actor: AuthenticatedProfile,
  caseId: string,
  analysisId: string,
  pathPrefix: string,
): void {
  client.setQueryData(caseQueryKeys.detail(actor.user_id, caseId), summaryFixture(caseId, `${pathPrefix} CASE`));
  client.setQueryData(caseQueryKeys.documents(actor.user_id, caseId), [documentFixture(caseId)]);
  client.setQueryData(caseQueryKeys.ownership(actor.user_id, caseId), ownershipFixture(caseId, analysisId, pathPrefix));
  client.setQueryData(caseQueryKeys.intelligence(actor.user_id, caseId), null);
}

function response(value: unknown): Response {
  return new Response(JSON.stringify(value), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

let root: Root | null = null;
let container: HTMLDivElement | null = null;

beforeEach(() => {
  container = document.createElement("div");
  document.body.append(container);
});

afterEach(() => {
  if (root) act(() => root?.unmount());
  container?.remove();
  root = null;
  container = null;
  vi.restoreAllMocks();
});

function renderCase(client: QueryClient, actor: AuthenticatedProfile, caseId: string): void {
  const view = (
    <QueryClientProvider client={client}>
      <CaseDetail
        caseId={caseId}
        actor={actor}
        onBack={() => undefined}
        onViewOnboarded={() => undefined}
        onViewAudit={() => undefined}
      />
    </QueryClientProvider>
  );
  if (!root) root = createRoot(container!);
  act(() => root?.render(view));
}

function button(label: string): HTMLButtonElement {
  const result = [...container!.querySelectorAll<HTMLButtonElement>("button")]
    .find((candidate) => candidate.textContent === label);
  expect(result).toBeTruthy();
  return result!;
}

function click(label: string): void {
  act(() => button(label).click());
}

async function clickAndFlush(label: string): Promise<void> {
  await act(async () => {
    button(label).click();
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

describe("Evidence workbench integration isolation", () => {
  it.each(["case", "version"] as const)("cancels a pending stage focus when its %s changes", async change => {
    const client = createTestClient();
    seedCase(client, actorA, CASE_A, "analysis-a", "A");
    seedCase(client, actorA, CASE_B, "analysis-b", "B");
    const summary = summaryFixture(CASE_A);
    summary.processing_pipeline = [{ node_id: "DOCUMENT_IDP", label: "Document verification",
      status: "REVIEW_REQUIRED", children: [] }];
    client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), summary);
    client.removeQueries({ queryKey: caseQueryKeys.documents(actorA.user_id, CASE_A), exact: true });
    let release!: (value: Response) => void;
    const pending = new Promise<Response>(resolve => { release = resolve; });
    vi.spyOn(globalThis, "fetch").mockReturnValue(pending);
    renderCase(client, actorA, CASE_A);
    const stage = container!.querySelector<HTMLButtonElement>('.ds-stage[data-node-id="DOCUMENT_IDP"] button')!;
    act(() => stage.click());
    if (change === "case") renderCase(client, actorA, CASE_B);
    else act(() => client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), { ...summary, version: 2 }));
    await act(async () => { release(response([documentFixture(CASE_A)])); });
    await vi.waitFor(() => expect(container?.querySelector("select[data-review-field]")).not.toBeNull());
    expect(document.activeElement?.getAttribute("data-review-field")).toBeNull();
  });

  it("defers a clicked document stage until its current decision control mounts", async () => {
    const client = createTestClient();
    seedCase(client, actorA, CASE_A, "analysis-1", "LOADING");
    const summary = summaryFixture(CASE_A);
    summary.processing_pipeline = [{ node_id: "DOCUMENT_IDP", label: "Document verification",
      status: "REVIEW_REQUIRED", children: [] }];
    client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), summary);
    client.removeQueries({ queryKey: caseQueryKeys.documents(actorA.user_id, CASE_A), exact: true });
    let release!: (value: Response) => void;
    const pending = new Promise<Response>(resolve => { release = resolve; });
    const fetch = vi.spyOn(globalThis, "fetch").mockReturnValue(pending);
    renderCase(client, actorA, CASE_A);
    const stage = container!.querySelector<HTMLButtonElement>('.ds-stage[data-node-id="DOCUMENT_IDP"] button')!;
    expect(stage).toBeTruthy();
    act(() => stage.click());
    await act(async () => { release(response([documentFixture(CASE_A)])); });
    await vi.waitFor(() => expect(document.activeElement?.getAttribute("data-review-field")).toBe("legal_name"));
    expect(fetch.mock.calls.every(([, options]) => !options?.method || options.method === "GET")).toBe(true);
  });

  it("waits for current document controls before enabling the blocker action", async () => {
    const client = createTestClient();
    seedCase(client, actorA, CASE_A, "analysis-1", "LOADING");
    const summary = summaryFixture(CASE_A);
    summary.interventions = [{
      intervention_id: summary.active_exceptions[0].exception_id,
      owning_stage: "DOCUMENT", owning_stage_label: "Document review",
      title: "Review current document", blocker_code: "DOCUMENT_REVIEW_REQUIRED",
      explanation: "Current document evidence is loading.",
      required_evidence_or_input: ["Current document"], authorized_actions: [],
      no_action_reason: null,
      expected_next_step: "Review current fields", candidate_summaries: [],
      evidence_actions: [{ target: "DOCUMENTS", label: "Open current review" }],
    }] as ZeroTouchCaseSummary["interventions"];
    client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), summary);
    client.removeQueries({ queryKey: caseQueryKeys.documents(actorA.user_id, CASE_A), exact: true });
    let release!: (value: Response) => void;
    const pending = new Promise<Response>(resolve => { release = resolve; });
    const fetch = vi.spyOn(globalThis, "fetch").mockReturnValue(pending);
    renderCase(client, actorA, CASE_A);
    expect(button("Open current review").disabled).toBe(true);
    await act(async () => { release(response([documentFixture(CASE_A)])); });
    await vi.waitFor(() => expect(button("Open current review").disabled).toBe(false));
    click("Open current review");
    await vi.waitFor(() => expect(document.activeElement?.getAttribute("data-review-field")).toBe("legal_name"));
    expect(fetch.mock.calls.every(([, options]) => !options?.method || options.method === "GET")).toBe(true);
  });

  it("exposes retained source checkpoint continuation without inventing pending field decisions", async () => {
    const client = createTestClient();
    seedCase(client, actorA, CASE_A, "analysis-1", "RETAINED");
    const summary = summaryFixture(CASE_A);
    const doc = { ...documentFixture(CASE_A), semantic_completion: "RECONCILIATION_RESOLVED" as const };
    summary.reconciliation = {
      reconciliation_id: "safe-reconciliation", version: 2, status: "RESOLVED",
      source_document_ids: [doc.document_id], source_document_event_counts: [doc.events.length],
      fields: [], discrepancies: [], updated_at: NOW,
    };
    client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), summary);
    client.setQueryData(caseQueryKeys.documents(actorA.user_id, CASE_A), [doc]);
    const fetch = vi.spyOn(globalThis, "fetch");
    renderCase(client, actorA, CASE_A);
    expect(button("Continue retained review checkpoint").disabled).toBe(false);
    expect(container?.querySelector("#case-blocker-review")).toBeNull();
    click("Focus documents evidence");
    await vi.waitFor(() => expect(document.activeElement).toBe(button("Continue retained review checkpoint")));
    expect(fetch).not.toHaveBeenCalled();
  });

  it.each([true, false, undefined])("uses the backend ownership edit capability for calculable evidence (%s)", (authorized) => {
    const client = createTestClient();
    seedCase(client, actorA, CASE_A, "analysis-1", "CALCULABLE");
    const summary = summaryFixture(CASE_A);
    summary.evidence_decision_authorized = authorized;
    summary.ownership_edit_authorized = authorized;
    summary.ownership_recovery = { analysis_id: "analysis-1", version: 3, state: "ANALYZED", manual_evidence_action: null, review_receipt: null };
    client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), summary);
    const reviewed = { ...documentFixture(CASE_A), state: "REVIEWED" } as DocumentProcessingRecord;
    client.setQueryData(caseQueryKeys.documents(actorA.user_id, CASE_A), [reviewed]);
    renderCase(client, actorA, CASE_A);
    expect(container!.querySelector(".manual-ownership") !== null).toBe(authorized === true);
    if (authorized !== true) {
      expect(container!.textContent).toContain("Evidence decisions are read-only");
      expect(container!.querySelector("#identity-registration-number")).toBeNull();
    }
  });

  it.each([true, false, undefined])("offers ownership upload only with the backend-declared evidence action (%s)", (uploadAction) => {
    const client = createTestClient();
    seedCase(client, actorA, CASE_A, "analysis-1", "OWNERSHIP");
    const summary = summaryFixture(CASE_A);
    summary.ownership_edit_authorized = true;
    summary.ownership_recovery = { analysis_id: "analysis-1", version: 3, state: "ANALYZED", manual_evidence_action: null, review_receipt: null };
    summary.interventions = uploadAction === undefined ? undefined : [{
      intervention_id: "ownership-review", owning_stage: "OWNERSHIP", owning_stage_label: "Ownership & UBO",
      title: "Ownership review", blocker_code: "OWNERSHIP_DOCUMENT_CONFLICT", explanation: "Review current proposed evidence.",
      required_evidence_or_input: [], authorized_actions: [], no_action_reason: null, expected_next_step: "Review evidence",
      candidate_summaries: [], evidence_actions: uploadAction ? [{ target: "OWNERSHIP_UPLOAD", label: "Upload ownership evidence" }] : [],
    }];
    client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), summary);
    client.setQueryData(caseQueryKeys.documents(actorA.user_id, CASE_A), [{ ...documentFixture(CASE_A), state: "REVIEWED" }]);
    renderCase(client, actorA, CASE_A);
    expect(container!.querySelector(".manual-ownership")).not.toBeNull();
    expect(container!.querySelector("#case-ownership-evidence-upload") !== null).toBe(uploadAction === true);
  });

  it("waits for the matching ownership analysis before initializing an editable graph", async () => {
    const client = createTestClient();
    seedCase(client, actorA, CASE_A, "old-analysis", "OLD");
    const summary = summaryFixture(CASE_A);
    summary.ownership_edit_authorized = true;
    summary.ownership_recovery = { analysis_id: "new-analysis", version: 5, state: "ANALYZED", manual_evidence_action: null, review_receipt: null };
    client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), summary);
    client.setQueryData(caseQueryKeys.documents(actorA.user_id, CASE_A), [{ ...documentFixture(CASE_A), state: "REVIEWED" }]);
    renderCase(client, actorA, CASE_A);
    expect(container!.querySelector(".manual-ownership")).toBeNull();
    const current = { ...ownershipFixture(CASE_A, "new-analysis", "CURRENT"), version: 5 };
    await act(async () => { client.setQueryData(caseQueryKeys.ownership(actorA.user_id, CASE_A), current); await new Promise((resolve) => setTimeout(resolve, 0)); });
    expect(container!.querySelector(".manual-ownership")).not.toBeNull();
  });

  it("resets ownership decision drafts when the actor or analysis version changes", () => {
    const client = createTestClient();
    for (const actor of [actorA, actorB]) {
      seedCase(client, actor, CASE_A, "analysis-1", "CURRENT");
      const summary = summaryFixture(CASE_A);
      summary.ownership_edit_authorized = true;
      summary.ownership_recovery = { analysis_id: "analysis-1", version: 3, state: "ANALYZED", manual_evidence_action: null, review_receipt: null };
      client.setQueryData(caseQueryKeys.detail(actor.user_id, CASE_A), summary);
      client.setQueryData(caseQueryKeys.documents(actor.user_id, CASE_A), [{ ...documentFixture(CASE_A), state: "REVIEWED" }]);
    }
    renderCase(client, actorA, CASE_A);
    const rationale = container!.querySelector<HTMLTextAreaElement>('[name="rationale"]')!;
    act(() => { Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!.call(rationale, "Actor A unsaved decision."); rationale.dispatchEvent(new Event("input", { bubbles: true })); });
    renderCase(client, actorB, CASE_A);
    expect(container!.querySelector<HTMLTextAreaElement>('[name="rationale"]')!.value).toBe("");
    const next = client.getQueryData<ZeroTouchCaseSummary>(caseQueryKeys.detail(actorB.user_id, CASE_A))!;
    act(() => client.setQueryData(caseQueryKeys.detail(actorB.user_id, CASE_A), { ...next, version: 2, ownership_recovery: { ...next.ownership_recovery, version: 4 } }));
    expect(container!.querySelector<HTMLTextAreaElement>('[name="rationale"]')!.value).toBe("");
  });

  it.each(["WAITING_FOR_REVIEW", "PENDING_INPUTS", "TECHNICAL_FAILURE"] as const)(
    "retires identity-dependent cached ownership at %s, including a late old GET",
    async (status) => {
      const client = createSessionQueryClient();
      seedCase(client, actorA, CASE_A, "old-analysis", "OLD_UEN");
      const initial = summaryFixture(CASE_A, "Synthetic entity");
      initial.case.requested_uen = "202400001A";
      initial.case.initial_identity = {
        legal_name: "Synthetic entity", registration_number: "202400001A",
        country_of_incorporation: "SG",
      } as ZeroTouchCaseSummary["case"]["initial_identity"];
      initial.case.events = [{}] as ZeroTouchCaseSummary["case"]["events"];
      initial.clm.version = 1;
      client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), initial);
      const updated = {
        ...initial, version: 2, status, clm: { ...initial.clm, version: 2 },
        case: { ...initial.case, requested_uen: "202400009I", events: [{}, {}],
                entity: { ...initial.case.entity, registration_number: "202400009I" } },
      };
      const nextOwnership = { ...ownershipFixture(CASE_A, "new-analysis", "NEW_UEN"), version: 6 };
      const oldOwnership = { ...ownershipFixture(CASE_A, "old-analysis", "OLD_UEN"), version: 4 };
      client.setQueryData(caseQueryKeys.ownership(actorA.user_id, CASE_A), oldOwnership);
      let releaseOld!: (value: Response) => void;
      const oldGet = new Promise<Response>((resolve) => { releaseOld = resolve; });
      let ownerReads = 0;
      const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
        const url = String(input);
        if (url.endsWith("/registry-identity")) {
          expect(init?.method).toBe("POST");
          expect(JSON.parse(String(init?.body)).expected_case_event_count).toBe(1);
          expect(JSON.parse(String(init?.body)).expected_clm_version).toBe(1);
          return response(updated);
        }
        if (url.endsWith("/ownership")) {
          ownerReads += 1;
          return ownerReads === 1 ? oldGet : response(nextOwnership);
        }
        if (url.endsWith("/documents")) return response([documentFixture(CASE_A)]);
        if (url.endsWith("/intelligence")) return response(null);
        throw new Error("Unexpected local fixture request");
      });
      renderCase(client, actorA, CASE_A);
      const late = client.refetchQueries({
        queryKey: caseQueryKeys.ownership(actorA.user_id, CASE_A), exact: true,
      }).catch(() => undefined);
      await vi.waitFor(() => expect(ownerReads).toBe(1));
      await clickAndFlush("Edit UEN");
      const input = container!.querySelector<HTMLInputElement>("#identity-registration-number")!;
      act(() => {
        Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(input, "202400009I");
        input.dispatchEvent(new Event("input", { bubbles: true }));
      });
      await clickAndFlush("Verify UEN and resume");
      await vi.waitFor(() => expect(
        client.getQueryData<OwnershipAnalysisRecord>(caseQueryKeys.ownership(actorA.user_id, CASE_A))?.analysis_id,
      ).toBe("new-analysis"));
      await act(async () => { releaseOld(response(oldOwnership)); await late; });
      expect(container!.textContent).not.toContain("OLD_UEN Candidate");
      expect(container!.textContent).toContain("NEW_UEN Candidate");
      expect(client.getQueryData<ZeroTouchCaseSummary>(
        caseQueryKeys.detail(actorA.user_id, CASE_A),
      )?.case.requested_uen).toBe("202400009I");
      expect(fetchSpy.mock.calls.some(([url]) => String(url).endsWith("/documents"))).toBe(true);
    },
  );

  it("retires a previous analysis when corrected identity has no current ownership", async () => {
    const client = createSessionQueryClient();
    seedCase(client, actorA, CASE_A, "old-analysis", "OLD_UEN");
    const initial = summaryFixture(CASE_A, "Synthetic entity");
    initial.case.initial_identity = { legal_name: "Synthetic entity",
      registration_number: "202400001A", country_of_incorporation: "SG" } as ZeroTouchCaseSummary["case"]["initial_identity"];
    initial.case.events = [{}] as ZeroTouchCaseSummary["case"]["events"];
    initial.clm.version = 1;
    client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), initial);
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/registry-identity")) return response({
        ...initial, version: 2, case: { ...initial.case, requested_uen: "202400009I", events: [{}, {}] },
      });
      if (url.endsWith("/ownership") || url.endsWith("/intelligence")) return response(null);
      if (url.endsWith("/documents")) return response([documentFixture(CASE_A)]);
      throw new Error("Unexpected local fixture request");
    });
    renderCase(client, actorA, CASE_A);
    await clickAndFlush("Edit UEN");
    await clickAndFlush("Verify UEN and resume");
    await vi.waitFor(() => expect(client.getQueryData(
      caseQueryKeys.ownership(actorA.user_id, CASE_A),
    )).toBeNull());
    expect(container!.textContent).not.toContain("OLD_UEN Candidate");
  });
  it("keeps candidate, retained-path, and explanation exploration local and read only", async () => {
    const client = createTestClient();
    seedCase(client, actorA, CASE_A, "analysis-a", "a");
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const storageSet = vi.spyOn(Storage.prototype, "setItem");
    const storageRemove = vi.spyOn(Storage.prototype, "removeItem");
    const storageClear = vi.spyOn(Storage.prototype, "clear");

    renderCase(client, actorA, CASE_A);
    click("Inspect a-path-2");
    expect(container?.textContent).toContain("Selected retained path: a-path-2");
    click("a Candidate Two");
    expect(container?.textContent).toContain("Selected retained path: a-candidate-two-path");
    click("Focus documents evidence");

    await vi.waitFor(() => expect(document.activeElement?.getAttribute("data-review-field")).toBe("legal_name"));
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(storageSet).not.toHaveBeenCalled();
    expect(storageRemove).not.toHaveBeenCalled();
    expect(storageClear).not.toHaveBeenCalled();
  });

  it("reports an unavailable corrective control without issuing a request", async () => {
    const client = createTestClient();
    seedCase(client, actorA, CASE_A, "analysis-a", "a");
    client.setQueryData(caseQueryKeys.documents(actorA.user_id, CASE_A), []);
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    renderCase(client, actorA, CASE_A);
    click("Focus documents evidence");
    await vi.waitFor(() => expect(container?.textContent).toContain("No corrective input is currently authorized here."));
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("clears focused draft controls synchronously across case and actor identities", async () => {
    const client = createTestClient();
    seedCase(client, actorA, CASE_A, "analysis-a", "a");
    seedCase(client, actorA, CASE_B, "analysis-b", "b");
    seedCase(client, actorB, CASE_B, "analysis-c", "c");
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    renderCase(client, actorA, CASE_A);
    click("Focus documents evidence");
    await vi.waitFor(() => expect(document.activeElement?.getAttribute("data-review-field")).toBe("legal_name"));
    const caseAControl = document.activeElement;
    renderCase(client, actorA, CASE_B);
    expect(caseAControl?.isConnected).toBe(false);
    expect(document.activeElement).not.toBe(caseAControl);
    click("Focus documents evidence");
    await vi.waitFor(() => expect(document.activeElement?.getAttribute("data-review-field")).toBe("legal_name"));
    const actorAControl = document.activeElement;
    renderCase(client, actorB, CASE_B);
    expect(actorAControl?.isConnected).toBe(false);
    expect(document.activeElement).not.toBe(actorAControl);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("does not retain local path selection across case, actor, or analysis identity changes", async () => {
    const client = createTestClient();
    seedCase(client, actorA, CASE_A, "analysis-a", "a");
    seedCase(client, actorA, CASE_B, "analysis-b", "b");
    seedCase(client, actorB, CASE_B, "analysis-c", "c");
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    renderCase(client, actorA, CASE_A);
    click("Inspect a-path-2");
    expect(container?.textContent).toContain("Selected retained path: a-path-2");

    renderCase(client, actorA, CASE_B);
    expect(container?.textContent).toContain("Selected retained path: b-path-1");
    expect(container?.textContent).not.toContain("Selected retained path: a-path-2");
    click("Inspect b-path-2");

    renderCase(client, actorB, CASE_B);
    expect(container?.textContent).toContain("Selected retained path: c-path-1");
    expect(container?.textContent).not.toContain("Selected retained path: b-path-2");
    click("Inspect c-path-2");

    await act(async () => {
      client.setQueryData(
        caseQueryKeys.ownership(actorB.user_id, CASE_B),
        ownershipFixture(CASE_B, "analysis-d", "d"),
      );
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    expect(container?.textContent).toContain("Selected retained path: d-path-1");
    expect(container?.textContent).not.toContain("Selected retained path: c-path-2");
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("uses exactly the four existing GET owners for an explicit read-only refresh", async () => {
    const client = createTestClient();
    seedCase(client, actorA, CASE_A, "analysis-a", "a");
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("offline"));
    renderCase(client, actorA, CASE_A);

    const choice = container?.querySelector<HTMLSelectElement>('select[data-review-field="legal_name"]');
    expect(choice).toBeTruthy();
    await act(async () => {
      choice!.value = "ACCEPTED";
      choice!.dispatchEvent(new Event("change", { bubbles: true }));
    });
    expect(fetchSpy).not.toHaveBeenCalled();
    await clickAndFlush("Confirm decisions & continue onboarding");
    await vi.waitFor(() => expect(container?.textContent).toContain("Evidence reload could not be confirmed."));

    fetchSpy.mockClear();
    fetchSpy.mockImplementation(async (input, init) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();
      expect(method).toBe("GET");
      if (url.endsWith(`/api/clm/zero-touch/cases/${CASE_A}`)) return response(summaryFixture(CASE_A));
      if (url.endsWith(`/api/onboarding/cases/${CASE_A}/documents`)) return response([documentFixture(CASE_A)]);
      if (url.endsWith(`/api/onboarding/cases/${CASE_A}/ownership`)) return response(ownershipFixture(CASE_A, "analysis-refreshed", "refreshed"));
      if (url.endsWith(`/api/clm/zero-touch/cases/${CASE_A}/intelligence`)) return response(null);
      throw new Error(`Unexpected refresh request: ${method} ${url}`);
    });

    await clickAndFlush("Refresh case evidence");
    await vi.waitFor(() => expect(container?.textContent).not.toContain("Evidence reload could not be confirmed."));

    expect(fetchSpy.mock.calls.map(([input, init]) => ({
      url: String(input),
      method: (init?.method ?? "GET").toUpperCase(),
    }))).toEqual([
      { url: `/api/clm/zero-touch/cases/${CASE_A}`, method: "GET" },
      { url: `/api/onboarding/cases/${CASE_A}/documents`, method: "GET" },
      { url: `/api/onboarding/cases/${CASE_A}/ownership`, method: "GET" },
      { url: `/api/clm/zero-touch/cases/${CASE_A}/intelligence`, method: "GET" },
    ]);
  });

  it("renders seven disclosures in order with Review & Send last and compact before readiness", () => {
    const client = createTestClient();
    seedCase(client, actorA, CASE_A, "analysis-a", "a");
    renderCase(client, actorA, CASE_A);
    const sections = Array.from(container!.querySelectorAll(".stage-disclosure"));
    expect(sections.map((section) => section.querySelector("h2 button span")?.textContent)).toEqual([
      "Registry verification", "Document verification", "Ownership & UBO",
      "Submission readiness", "GoldTier submission package",
      "Historical / resolved issues", "Final review & send",
    ]);
    expect(sections[1].querySelector("button")?.getAttribute("aria-expanded")).toBe("true");
    expect(sections[5].querySelector("button")?.getAttribute("aria-expanded")).toBe("false");
    expect(sections[6].querySelector("button")?.getAttribute("aria-expanded")).toBe("false");
    expect(sections[6].textContent).toContain("Not yet available");
    expect(sections[6].querySelector(".review-and-send")).toBeNull();
  });
});


describe("Case attention corrective navigation", () => {
  function attentionButton(prefix: string) {
    const control = [...container!.querySelectorAll<HTMLButtonElement>(".case-attention button")].find(item => item.textContent?.startsWith(prefix));
    expect(control).toBeTruthy(); return control!;
  }
  function projectionOnlySummary() {
    const value = summaryFixture(CASE_A);
    value.current_stage = "REGISTRY";
    value.active_exceptions = [];
    value.interventions = attentionProjections.identityOnly.interventions as ZeroTouchCaseSummary["interventions"];
    value.case.initial_identity = null;
    value.case.requested_uen = "202400001A";
    return value;
  }
  it("opens the registry stage and focuses authorized UEN for a projection-only identity action without a request", async () => {
    const client = createTestClient(); seedCase(client, actorA, CASE_A, "analysis-a", "A");
    client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), projectionOnlySummary());
    const fetch = vi.spyOn(globalThis, "fetch"); renderCase(client, actorA, CASE_A);
    const stage = [...container!.querySelectorAll<HTMLButtonElement>(".stage-disclosure h2 button")].find(item => item.textContent?.startsWith("Registry verification"))!;
    act(() => stage.click()); expect(stage.getAttribute("aria-expanded")).toBe("false");
    const action = attentionButton("Action: Correct identity"); action.focus(); expect(document.activeElement).toBe(action);
    act(() => action.click());
    await vi.waitFor(() => expect(document.activeElement?.id).toBe("identity-registration-number"));
    expect(stage.getAttribute("aria-expanded")).toBe("true"); expect(fetch).not.toHaveBeenCalled();
    expect((document.activeElement as HTMLInputElement).value).toBe("202400001A");
  });
  it("retains registry verification when the identity projection has no eligible Search checkpoint or identity error", () => {
    const client = createTestClient(); seedCase(client, actorA, CASE_A, "analysis-a", "A");
    client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), projectionOnlySummary());
    renderCase(client, actorA, CASE_A);
    expect(button("Verify UEN and resume")).toBeTruthy();
    expect(container!.textContent).not.toContain("Save details and recheck Search");
  });
  it("retains Search recheck for the actual initial-identity error with a projection-only blocker", () => {
    const client = createTestClient(); seedCase(client, actorA, CASE_A, "analysis-a", "A");
    const value = projectionOnlySummary();
    value.case.error = { code: "INITIAL_IDENTITY_INCOMPLETE", message: "Identity required" };
    client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), value);
    renderCase(client, actorA, CASE_A);
    expect(button("Save details and recheck Search")).toBeTruthy();
    expect(container!.textContent).not.toContain("Verify UEN and resume");
  });
  it.each(["REGISTRY_IDENTIFIER_NOT_ELIGIBLE", "ACRA_ENTITY_NOT_FOUND", "REGISTRY_RECHECK_INCOMPLETE", "INITIAL_IDENTITY_NOT_ELIGIBLE"])(
    "preserves registry correction beside a missing-identity projection for %s", code => {
      const client = createTestClient(); seedCase(client, actorA, CASE_A, "analysis-a", "A");
      const value = projectionOnlySummary();
      value.case.error = { code, message: "Registry correction required" };
      value.active_exceptions = [{ ...summaryFixture(CASE_A).active_exceptions[0], stage: "REGISTRY",
        exception_type: "REGISTRY_IDENTIFIER_NOT_ELIGIBLE", blocker_code: code, blocker_codes: [code] }];
      client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), value);
      const fetch = vi.spyOn(globalThis, "fetch"); renderCase(client, actorA, CASE_A);
      expect(button("Verify UEN and resume")).toBeTruthy();
      expect(container!.textContent).not.toContain("Save details and recheck Search");
      expect(fetch).not.toHaveBeenCalled();
    },
  );
  it.each(["COMPLETED", "FAILED", "REVIEW_REQUIRED"] as const)("retains projection-only Search recheck with its eligible %s checkpoint", status => {
    const client = createTestClient(); seedCase(client, actorA, CASE_A, "analysis-a", "A");
    const value = projectionOnlySummary();
    value.clm.target_search_checkpoint = { status } as NonNullable<ZeroTouchCaseSummary["clm"]["target_search_checkpoint"]>;
    client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), value);
    renderCase(client, actorA, CASE_A);
    expect(button("Save details and recheck Search")).toBeTruthy();
  });
  it("gives truthful feedback when a projection-only identity control is disabled", async () => {
    const client = createTestClient(); seedCase(client, actorA, CASE_A, "analysis-a", "A");
    const value = projectionOnlySummary(); value.evidence_decision_authorized = false;
    client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), value);
    const fetch = vi.spyOn(globalThis, "fetch"); renderCase(client, actorA, CASE_A);
    act(() => attentionButton("Action: Correct identity").click());
    await vi.waitFor(() => expect(container!.textContent).toContain("No corrective input is currently authorized here"));
    expect(document.activeElement?.id).not.toBe("identity-registration-number"); expect(fetch).not.toHaveBeenCalled();
  });
  it("replaces projection-only attention after refresh and ignores a late old-case summary", async () => {
    const client = createTestClient(); seedCase(client, actorA, CASE_A, "analysis-a", "A"); seedCase(client, actorA, CASE_B, "analysis-b", "B");
    const value = projectionOnlySummary(); client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), value);
    let release!: (value: Response) => void;
    vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise<Response>(resolve => { release = resolve; }));
    renderCase(client, actorA, CASE_A); expect(container!.querySelector(".case-attention")!.textContent).toContain("Correct identity");
    const oldRequest = client.refetchQueries({ queryKey: caseQueryKeys.detail(actorA.user_id, CASE_A), exact: true });
    await act(async () => { client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), { ...value, version: 2, interventions: [] }); });
    await vi.waitFor(() => expect(container!.querySelector(".case-attention")!.textContent).not.toContain("Correct identity"));
    renderCase(client, actorA, CASE_B);
    await act(async () => { release(response(value)); await oldRequest; });
    expect(container!.querySelector(".case-attention")!.textContent).not.toContain("Correct identity");
    expect(container!.querySelector(".case-attention")!.textContent).toContain("DOCUMENT SOURCE CONFLICT");
  });
  it("navigates a projection-only blocker with no authorized action to its retained reason", async () => {
    const client = createTestClient(); seedCase(client, actorA, CASE_A, "analysis-a", "A");
    const value = projectionOnlySummary();
    value.interventions = [{ ...value.interventions![0],
      blocker_code: "MOCK_RISK_REVIEW_REQUIRED", owning_stage: "READINESS", title: "Retained risk review",
      evidence_actions: [], no_action_reason: "No authorized POC risk decision is available." }];
    client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), value);
    const fetch = vi.spyOn(globalThis, "fetch"); renderCase(client, actorA, CASE_A);
    act(() => attentionButton("Blocker: Retained risk review").click());
    await vi.waitFor(() => expect(document.activeElement?.id).toBe(`case-intervention-${value.interventions![0].intervention_id}`));
    expect(container!.textContent).toContain("No corrective input is currently authorized here"); expect(fetch).not.toHaveBeenCalled();
  });
  it("opens a collapsed document stage and focuses the specific pending decision without mutating", async () => {
    const client = createTestClient(); seedCase(client, actorA, CASE_A, "analysis-a", "A");
    const summary = summaryFixture(CASE_A);
    summary.active_exceptions[0].evidence = [{ reference_id: `${CASE_A}-document`, field_key: "legal_name", registry_value: null, document_value: null, confidence: null, comparison: null }];
    client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), summary);
    const fetch = vi.spyOn(globalThis, "fetch"); renderCase(client, actorA, CASE_A);
    const stage = [...container!.querySelectorAll<HTMLButtonElement>(".stage-disclosure h2 button")].find(item => item.textContent?.startsWith("Document verification"))!;
    act(() => stage.click()); expect(stage.getAttribute("aria-expanded")).toBe("false");
    const control = attentionButton("Blocker:"); control.focus(); expect(document.activeElement).toBe(control);
    act(() => control.click());
    await vi.waitFor(() => expect(document.activeElement?.getAttribute("data-review-field")).toBe("legal_name"));
    expect(stage.getAttribute("aria-expanded")).toBe("true");
    expect((document.activeElement as HTMLSelectElement).value).toBe(""); expect(fetch).not.toHaveBeenCalled();
  });
  it("switches to the specific reconciliation decision without choosing a source", async () => {
    const client = createTestClient(); seedCase(client, actorA, CASE_A, "analysis-a", "A");
    const summary = summaryFixture(CASE_A); const doc = documentFixture(CASE_A);
    summary.active_exceptions = ["first", "second"].map(id => ({ ...summary.active_exceptions[0], exception_id: id, blocker_code: `DOCUMENT_SOURCE_CONFLICT_${id}` }));
    summary.reconciliation = { reconciliation_id: "current", version: 1, status: "REVIEW_REQUIRED", source_document_ids: [doc.document_id], source_document_event_counts: [doc.events.length], fields: [], updated_at: NOW,
      discrepancies: ["first", "second"].map(id => ({ discrepancy_id: id, field_name: "legal_name", status: "OPEN", allowed_actions: ["KEEP_REGISTRY_VALUE"], evidence_fingerprint: "a".repeat(64), observations: [] })) } as unknown as NonNullable<ZeroTouchCaseSummary["reconciliation"]>;
    client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), summary);
    const fetch = vi.spyOn(globalThis, "fetch"); renderCase(client, actorA, CASE_A);
    expect(container!.querySelector("select[data-discrepancy-id]")).toBeNull();
    act(() => attentionButton("Blocker: DOCUMENT SOURCE CONFLICT second").click());
    await vi.waitFor(() => expect(document.activeElement?.getAttribute("data-discrepancy-id")).toBe("second"));
    expect((document.activeElement as HTMLSelectElement).value).toBe(""); expect(fetch).not.toHaveBeenCalled();
  });
  it("opens the document-specific replacement upload", async () => {
    const client = createTestClient(); seedCase(client, actorA, CASE_A, "analysis-a", "A");
    const summary = summaryFixture(CASE_A); summary.status = "PENDING_INPUTS";
    summary.active_exceptions[0].blocker_code = "DOCUMENT_REUPLOAD_REQUIRED";
    summary.active_exceptions[0].evidence = [{ reference_id: `${CASE_A}-document`, field_key: "legal_name", registry_value: null, document_value: null, confidence: null, comparison: null }];
    client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), summary);
    client.setQueryData(caseQueryKeys.documents(actorA.user_id, CASE_A), [{ ...documentFixture(CASE_A), state: "FAILED", error: { code: "DOCUMENT_REUPLOAD_REQUIRED", message: "Replacement required" } }]);
    renderCase(client, actorA, CASE_A); act(() => attentionButton("Blocker:").click());
    await vi.waitFor(() => expect((document.activeElement as HTMLInputElement).type).toBe("file"));
    expect(document.activeElement?.closest(".document-card")?.getAttribute("data-document-id")).toBe(`${CASE_A}-document`);
  });
  it("uses replacement rather than a retained discrepancy with no authorized source choices", async () => {
    const client = createTestClient(); seedCase(client, actorA, CASE_A, "analysis-a", "A");
    const summary = summaryFixture(CASE_A); summary.document_replacement_authorized = true;
    summary.active_exceptions[0].evidence = [{ reference_id: `${CASE_A}-document`, field_key: "legal_name", registry_value: null, document_value: null, confidence: null, comparison: null }];
    summary.reconciliation = { reconciliation_id: "retained", version: 1, status: "REVIEW_REQUIRED", source_document_ids: [`${CASE_A}-document`], source_document_event_counts: [0], fields: [], updated_at: NOW,
      discrepancies: [{ discrepancy_id: summary.active_exceptions[0].exception_id, field_name: "legal_name", status: "OPEN", allowed_actions: [], evidence_fingerprint: "a".repeat(64), observations: [] }] } as unknown as NonNullable<ZeroTouchCaseSummary["reconciliation"]>;
    client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), summary);
    const doc = documentFixture(CASE_A); doc.state = "REVIEWED"; doc.fields[0].review_status = "REJECTED";
    client.setQueryData(caseQueryKeys.documents(actorA.user_id, CASE_A), [doc]); renderCase(client, actorA, CASE_A);
    act(() => attentionButton("Blocker:").click());
    await vi.waitFor(() => expect((document.activeElement as HTMLInputElement).type).toBe("file"));
    expect(document.activeElement?.closest(".document-card")?.getAttribute("data-document-id")).toBe(`${CASE_A}-document`);
  });
  it("routes retained existing-customer attention to the confirmation rationale", async () => {
    const client = createTestClient(); seedCase(client, actorA, CASE_A, "analysis-a", "A");
    const summary = summaryFixture(CASE_A); summary.current_stage = "GOLDTIER_SEARCH";
    summary.active_exceptions[0].stage = "GOLDTIER_SEARCH"; summary.active_exceptions[0].blocker_code = "GOLDTIER_EXISTING_CUSTOMER";
    summary.interventions = [{ intervention_id: summary.active_exceptions[0].exception_id, owning_stage: "GOLDTIER_SEARCH", owning_stage_label: "Customer search", title: "Confirm existing customer", blocker_code: "GOLDTIER_EXISTING_CUSTOMER", explanation: "Review the retained customer", required_evidence_or_input: [], authorized_actions: [], no_action_reason: null, expected_next_step: "Confirm customer", candidate_summaries: [], existing_customer_confirmation_action: "CONFIRM_EXISTING_GOLDTIER_CUSTOMER" }];
    client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), summary);
    const fetch = vi.spyOn(globalThis, "fetch"); renderCase(client, actorA, CASE_A);
    act(() => attentionButton("Blocker:").click());
    await vi.waitFor(() => expect(document.activeElement?.id).toBe("existing-customer-confirmation-rationale")); expect(fetch).not.toHaveBeenCalled();
  });
  it("routes ownership attention to retained authorized evidence controls", async () => {
    const client = createTestClient(); seedCase(client, actorA, CASE_A, "analysis-a", "A");
    const summary = summaryFixture(CASE_A); summary.current_stage = "OWNERSHIP";
    summary.active_exceptions[0].stage = "OWNERSHIP"; summary.active_exceptions[0].blocker_code = "OWNERSHIP_REVIEW_REQUIRED";
    summary.ownership_edit_authorized = true;
    summary.ownership_recovery = { analysis_id: "analysis-a", version: 3, state: "ANALYZED", manual_evidence_action: null, review_receipt: null };
    client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), summary);
    client.setQueryData(caseQueryKeys.documents(actorA.user_id, CASE_A), [{ ...documentFixture(CASE_A), state: "REVIEWED" }]);
    const fetch = vi.spyOn(globalThis, "fetch"); renderCase(client, actorA, CASE_A); act(() => attentionButton("Blocker:").click());
    await vi.waitFor(() => expect(document.activeElement?.closest("#case-manual-ownership-evidence")).not.toBeNull()); expect(fetch).not.toHaveBeenCalled();
  });
  it("focuses the retained mock risk reason without inventing a corrective action", async () => {
    const client = createTestClient(); seedCase(client, actorA, CASE_A, "analysis-a", "A");
    const summary = summaryFixture(CASE_A); summary.current_stage = "READINESS";
    summary.active_exceptions[0].stage = "READINESS"; summary.active_exceptions[0].blocker_code = "MOCK_RISK_REVIEW_REQUIRED";
    summary.interventions = [{ intervention_id: summary.active_exceptions[0].exception_id, owning_stage: "READINESS", owning_stage_label: "Readiness", title: "Review mock risk", blocker_code: "MOCK_RISK_REVIEW_REQUIRED", explanation: "A retained risk decision requires review", required_evidence_or_input: [], authorized_actions: [], no_action_reason: "No authorized POC risk decision is available.", expected_next_step: "Review risk", candidate_summaries: [] }];
    client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), summary);
    const fetch = vi.spyOn(globalThis, "fetch"); renderCase(client, actorA, CASE_A); act(() => attentionButton("Blocker:").click());
    await vi.waitFor(() => expect(document.activeElement?.id).toBe(`case-intervention-${summary.active_exceptions[0].exception_id}`)); expect(container!.textContent).toContain("No corrective input is currently authorized here"); expect(fetch).not.toHaveBeenCalled();
  });
  it("replaces resolved attention on refresh and case switching; final confirmation is an action", async () => {
    const client = createTestClient(); seedCase(client, actorA, CASE_A, "analysis-a", "A"); seedCase(client, actorA, CASE_B, "analysis-b", "B");
    renderCase(client, actorA, CASE_A);
    expect(container!.querySelector(".case-attention")!.textContent).toContain("1 active blocker");
    const resolved = summaryFixture(CASE_A); resolved.version = 2;
    resolved.active_exceptions = [{ ...resolved.active_exceptions[0], exception_type: "TARGET_CONFIRMATION_REQUIRED", blocker_code: "TARGET_CONFIRMATION_REQUIRED", stage: "READINESS" }];
    await act(async () => { client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), resolved); await new Promise(resolve => setTimeout(resolve, 0)); });
    const panel = container!.querySelector(".case-attention")!;
    expect(panel.textContent).toContain("0 active blockers"); expect(panel.textContent).toContain("No immediate blockers"); expect(panel.textContent).toContain("Action: Review and send"); expect(panel.textContent).not.toContain("DOCUMENT SOURCE CONFLICT");
    renderCase(client, actorA, CASE_B);
    expect(container!.querySelector(".case-attention")!.textContent).not.toContain("Review and send");
    expect(container!.querySelector(".case-attention")!.textContent).toContain("DOCUMENT SOURCE CONFLICT");
  });
  it("reports unavailable authorized controls and exposes technical diagnostics truthfully", async () => {
    const client = createTestClient(); seedCase(client, actorA, CASE_A, "analysis-a", "A");
    const summary = summaryFixture(CASE_A); summary.evidence_decision_authorized = false;
    summary.technical_failure = { code: "SAFE_TECHNICAL_FAILURE", message: "Safe retained diagnostic." };
    client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), summary);
    const fetch = vi.spyOn(globalThis, "fetch"); renderCase(client, actorA, CASE_A);
    act(() => attentionButton("Blocker:").click());
    await vi.waitFor(() => expect(container!.textContent).toContain("No corrective input is currently authorized here"));
    act(() => attentionButton("Technical failure:").click());
    await vi.waitFor(() => expect(container!.querySelector("#case-evidence-recovery")?.closest("[hidden]")).toBeNull());
    expect(fetch).not.toHaveBeenCalled();
  });
  it.each(["case", "version"] as const)("cancels delayed attention focus when %s changes", async change => {
    const client = createTestClient(); seedCase(client, actorA, CASE_A, "analysis-a", "A"); seedCase(client, actorA, CASE_B, "analysis-b", "B");
    client.removeQueries({ queryKey: caseQueryKeys.documents(actorA.user_id, CASE_A), exact: true });
    let release!: (value: Response) => void; const pending = new Promise<Response>(resolve => { release = resolve; });
    vi.spyOn(globalThis, "fetch").mockReturnValue(pending); renderCase(client, actorA, CASE_A);
    act(() => attentionButton("Blocker:").click());
    if (change === "case") renderCase(client, actorA, CASE_B);
    else await act(async () => { client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), { ...summaryFixture(CASE_A), version: 2 }); await new Promise(resolve => setTimeout(resolve, 0)); });
    await act(async () => { release(response([documentFixture(CASE_A)])); });
    expect(document.activeElement?.getAttribute("data-review-field")).toBeNull();
  });
});
