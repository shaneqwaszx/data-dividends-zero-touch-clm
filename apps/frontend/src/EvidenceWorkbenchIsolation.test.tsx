// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { caseQueryKeys } from "./caseQueries";
import CaseDetail from "./pages/CaseDetail";
import { clearSessionQueries, createSessionQueryClient } from "./queryClient";
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
let scrollIntoView: ReturnType<typeof vi.fn>;
let scrollDescriptor: PropertyDescriptor | undefined;

beforeEach(() => {
  // jsdom has no scroll/layout implementation. Keep this adapter file-local and
  // restore its descriptor; real focus, target lookup and disclosure still run.
  scrollDescriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "scrollIntoView");
  scrollIntoView = vi.fn();
  if (typeof HTMLElement.prototype.scrollIntoView !== "function") {
    Object.defineProperty(HTMLElement.prototype, "scrollIntoView", { configurable: true, value: scrollIntoView });
  }
  container = document.createElement("div");
  document.body.append(container);
});

afterEach(() => {
  if (root) act(() => root?.unmount());
  container?.remove();
  root = null;
  container = null;
  if (scrollDescriptor) Object.defineProperty(HTMLElement.prototype, "scrollIntoView", scrollDescriptor);
  else Reflect.deleteProperty(HTMLElement.prototype, "scrollIntoView");
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

function openPathInspection(): void {
  const details = [...container!.querySelectorAll("details")].find(item => item.querySelector("summary")?.textContent === "Technical retained path inspection");
  if (details && !details.open) act(() => { details.open = true; details.dispatchEvent(new Event("toggle")); });
}

function click(label: string): void {
  if (label.startsWith("Inspect ")) openPathInspection();
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
    await vi.waitFor(() => expect(container?.querySelector("input[data-review-field]")).not.toBeNull());
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
    expect(container!.querySelector('[aria-label="Selected holder"]')?.textContent).toContain("a Candidate Two");
    expect(container!.querySelector('[aria-label="Ownership hierarchy"] [role="row"].is-selected')?.textContent).toContain("a Candidate Two");
    expect(container!.querySelector('[aria-label^="Ownership candidate "]')).toBeNull();
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
    openPathInspection();
    expect(container?.textContent).toContain("Selected retained path: b-path-1");
    expect(container?.textContent).not.toContain("Selected retained path: a-path-2");
    click("Inspect b-path-2");

    renderCase(client, actorB, CASE_B);
    openPathInspection();
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
    openPathInspection();
    expect(container?.textContent).toContain("Selected retained path: d-path-1");
    expect(container?.textContent).not.toContain("Selected retained path: c-path-2");
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("uses exactly the four existing GET owners for an explicit read-only refresh", async () => {
    const client = createTestClient();
    seedCase(client, actorA, CASE_A, "analysis-a", "a");
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("offline"));
    renderCase(client, actorA, CASE_A);

    const choice = container?.querySelector<HTMLInputElement>('input[data-review-field="legal_name"][value="ACCEPTED"]');
    expect(choice).toBeTruthy();
    await act(async () => { choice!.click(); });
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

  it("renders Search before Registry in pipeline order with independent stage toggles", () => {
    const client = createTestClient();
    seedCase(client, actorA, CASE_A, "analysis-a", "a");
    renderCase(client, actorA, CASE_A);
    const sections = Array.from(container!.querySelectorAll(".stage-disclosure"));
    expect(sections.map((section) => section.querySelector(":scope > h2 button span")?.textContent ?? section.querySelector(":scope > h2")?.textContent)).toEqual([
      "Existing-customer search", "Registry verification", "Document verification", "Ownership & UBO",
      "Submission readiness", "GoldTier submission package",
      "Historical / resolved issues", "Final review & send",
    ]);
    expect(sections[2].querySelector(":scope > h2 button")).not.toBeNull();
    expect([...sections[2].querySelectorAll<HTMLDetailsElement>(":scope > details")].every(item => !item.open)).toBe(true);
    expect(sections[6].querySelector("button")?.getAttribute("aria-expanded")).toBe("false");
    expect(sections[7].querySelector(":scope > h2 button")).not.toBeNull();
    expect(sections[7].textContent).toContain("Not yet available");
    expect(sections[7].querySelector(".review-and-send")).toBeNull();
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
    const stage = [...container!.querySelectorAll<HTMLElement>(".stage-disclosure")].find(item => item.querySelector(":scope > h2")?.textContent === "Registry verification")!;
    const parent = stage.querySelector<HTMLButtonElement>(":scope > h2 button")!;
    act(() => parent.click());
    expect(parent.getAttribute("aria-expanded")).toBe("false");
    expect(stage.querySelector(".stage-disclosure__summary")?.textContent).toContain("Attention required");
    expect(stage.querySelector<HTMLElement>(":scope > div")!.hidden).toBe(true);
    expect([...stage.querySelectorAll<HTMLDetailsElement>(":scope > details")].every(item => !item.open)).toBe(true);
    const action = attentionButton("Blocker: Initial identity"); action.focus(); expect(document.activeElement).toBe(action);
    act(() => action.click());
    await vi.waitFor(() => expect(document.activeElement?.id).toBe("identity-registration-number"));
    expect(stage.contains(document.activeElement)).toBe(true);
    expect(document.activeElement?.closest("details:not([open]), [hidden]")).toBeNull();
    expect([...stage.querySelectorAll<HTMLDetailsElement>(":scope > details")].every(item => !item.open)).toBe(true);
    expect(fetch).not.toHaveBeenCalled();
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
    const stage = [...container!.querySelectorAll<HTMLElement>(".stage-disclosure")].find(item => item.querySelector(":scope > h2")?.textContent === "Registry verification")!;
    act(() => stage.querySelector<HTMLButtonElement>("h2 button")!.click());
    expect(stage.querySelector(".stage-disclosure__summary")?.textContent).toContain("Attention required");
    act(() => attentionButton("Blocker: Initial identity").click());
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
    const stage = [...container!.querySelectorAll<HTMLElement>(".stage-disclosure")].find(item => item.querySelector(":scope > h2")?.textContent === "Submission readiness")!;
    act(() => stage.querySelector<HTMLButtonElement>("h2 button")!.click());
    expect(stage.querySelector(".stage-disclosure__summary")?.textContent).toContain("Attention required");
    act(() => attentionButton("Blocker: Retained risk review").click());
    await vi.waitFor(() => expect(document.activeElement?.id).toBe(`case-intervention-${value.interventions![0].intervention_id}`));
    expect(container!.textContent).toContain("No corrective input is currently authorized here"); expect(fetch).not.toHaveBeenCalled();
  });
  it("keeps document support closed and focuses the specific pending decision without mutating", async () => {
    const client = createTestClient(); seedCase(client, actorA, CASE_A, "analysis-a", "A");
    const summary = summaryFixture(CASE_A);
    summary.active_exceptions[0].evidence = [{ reference_id: `${CASE_A}-document`, field_key: "legal_name", registry_value: null, document_value: null, confidence: null, comparison: null }];
    client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), summary);
    const fetch = vi.spyOn(globalThis, "fetch"); renderCase(client, actorA, CASE_A);
    const stage = [...container!.querySelectorAll<HTMLElement>(".stage-disclosure")].find(item => item.querySelector(":scope > h2")?.textContent === "Document verification")!;
    expect([...stage.querySelectorAll<HTMLDetailsElement>(":scope > details")].every(item => !item.open)).toBe(true);
    const control = attentionButton("Blocker:"); control.focus(); expect(document.activeElement).toBe(control);
    act(() => control.click());
    await vi.waitFor(() => expect(document.activeElement?.getAttribute("data-review-field")).toBe("legal_name"));
    expect([...stage.querySelectorAll<HTMLDetailsElement>(":scope > details")].every(item => !item.open)).toBe(true);
    expect((document.activeElement as HTMLInputElement).checked).toBe(false);
    expect(container!.querySelector('input[data-review-field="legal_name"]:checked')).toBeNull(); expect(fetch).not.toHaveBeenCalled();
  });
  it("switches to the specific reconciliation decision without choosing a source", async () => {
    const client = createTestClient(); seedCase(client, actorA, CASE_A, "analysis-a", "A");
    const summary = summaryFixture(CASE_A); const doc = documentFixture(CASE_A);
    summary.active_exceptions = ["first", "second"].map(id => ({ ...summary.active_exceptions[0], exception_id: id, blocker_code: `DOCUMENT_SOURCE_CONFLICT_${id}` }));
    summary.reconciliation = { reconciliation_id: "current", version: 1, status: "REVIEW_REQUIRED", source_document_ids: [doc.document_id], source_document_event_counts: [doc.events.length], fields: [], updated_at: NOW,
      discrepancies: ["first", "second"].map(id => ({ discrepancy_id: id, field_name: "legal_name", status: "OPEN", allowed_actions: ["KEEP_REGISTRY_VALUE"], evidence_fingerprint: "a".repeat(64), observations: [] })) } as unknown as NonNullable<ZeroTouchCaseSummary["reconciliation"]>;
    client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), summary);
    const fetch = vi.spyOn(globalThis, "fetch"); renderCase(client, actorA, CASE_A);
    expect(container!.querySelector("input[data-discrepancy-id]")).toBeNull();
    act(() => attentionButton("Blocker: DOCUMENT SOURCE CONFLICT second").click());
    await vi.waitFor(() => expect(document.activeElement?.getAttribute("data-discrepancy-id")).toBe("second"));
    expect((document.activeElement as HTMLInputElement).checked).toBe(false);
    expect(container!.querySelector('input[data-discrepancy-id="second"]:checked')).toBeNull(); expect(fetch).not.toHaveBeenCalled();
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
  it.each(["case", "actor", "version", "document revision", "replacement"] as const)(
    "retires bulk decision drafts at the real CaseDetail %s boundary", async change => {
      const client = createTestClient();
      seedCase(client, actorA, CASE_A, "analysis-a", "A");
      seedCase(client, actorA, CASE_B, "analysis-b", "B");
      seedCase(client, actorB, CASE_A, "analysis-c", "C");
      const fetch = vi.spyOn(globalThis, "fetch");
      renderCase(client, actorA, CASE_A);
      click("Reject all undecided suggestions");
      const selected = container!.querySelector<HTMLInputElement>("input[data-review-field]:checked")!;
      expect(selected.value).toBe("REJECTED");
      if (change === "case") renderCase(client, actorA, CASE_B);
      else if (change === "actor") renderCase(client, actorB, CASE_A);
      else await act(async () => {
        if (change === "version") client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), { ...summaryFixture(CASE_A), version: 2 });
        else {
          const doc = documentFixture(CASE_A);
          client.setQueryData(caseQueryKeys.documents(actorA.user_id, CASE_A), change === "replacement"
            ? [{ ...doc, superseded_by_document_id: "replacement-document", events: [...doc.events, {}] },
               { ...doc, document_id: "replacement-document", replaces_document_id: doc.document_id, review_source_fingerprint: "b".repeat(64) }]
            : [{ ...doc, events: [...doc.events, {}] }]);
        }
        await new Promise(resolve => setTimeout(resolve, 0));
      });
      expect(selected.isConnected).toBe(false);
      expect(container!.querySelectorAll("input[data-review-field]:checked")).toHaveLength(0);
      expect(fetch).not.toHaveBeenCalled();
    },
  );

});


describe("Document persistent disclosure migration", () => {
  function documentStage() {
    return [...container!.querySelectorAll<HTMLElement>(".stage-disclosure")]
      .find(item => item.querySelector(":scope > h2")?.textContent === "Document verification")!;
  }
  it("keeps document actions and conflicts in Main with independent closed support", () => {
    const client = createTestClient(); seedCase(client, actorA, CASE_A, "analysis-a", "a");
    const fetch = vi.spyOn(globalThis, "fetch"); renderCase(client, actorA, CASE_A);
    const stage = documentStage(); expect(stage).toBeTruthy();
    expect(stage.querySelector(":scope > h2 button")).not.toBeNull();
    const support = [...stage.querySelectorAll<HTMLDetailsElement>(":scope > details")];
    expect(support.map(item => item.querySelector("summary")?.textContent)).toEqual([
      "More details — Document verification", "Technical details — Document verification",
    ]);
    expect(support.every(item => !item.open)).toBe(true);
    const main = stage.querySelector(":scope > div")!;
    expect(main.querySelector("#case-blocker-review input[data-review-field]")).not.toBeNull();
    expect(main.querySelector("#case-evidence-documents")).not.toBeNull();
    expect(main.textContent).toContain("1 field remains for review");
    expect(main.textContent).toContain("MISMATCH");
    act(() => { support[0].open = true; }); expect(support[1].open).toBe(false);
    act(() => { support[1].open = true; support[0].open = false; });
    expect(support[1].open).toBe(true); expect(fetch).not.toHaveBeenCalled();
  });
  it("retains unconfirmed document choices when support collapses and same-scope data refreshes", async () => {
    const client = createTestClient(); seedCase(client, actorA, CASE_A, "analysis-a", "a");
    const fetch = vi.spyOn(globalThis, "fetch"); renderCase(client, actorA, CASE_A);
    const stage = documentStage(); expect(stage).toBeTruthy();
    const support = [...stage.querySelectorAll<HTMLDetailsElement>(":scope > details")];
    expect(support).toHaveLength(2);
    const choice = stage.querySelector<HTMLInputElement>('input[data-review-field][value="ACCEPTED"]')!;
    act(() => { choice.click(); support[0].open = true; support[0].open = false; });
    await act(async () => { client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), { ...summaryFixture(CASE_A), updated_at: "2026-10-15T12:00:00Z" }); await new Promise(resolve => setTimeout(resolve, 0)); });
    expect(stage.querySelector<HTMLInputElement>("input[data-review-field]:checked")!.value).toBe("ACCEPTED");
    expect(support[0].open).toBe(false); expect(fetch).not.toHaveBeenCalled();
  });
  it.each(["loading", "failed-empty", "failed-retained"] as const)(
    "projects %s document query state into visible optional sections without mutations", async state => {
      const client = createTestClient(); seedCase(client, actorA, CASE_A, "analysis-a", "a");
      const key = caseQueryKeys.documents(actorA.user_id, CASE_A);
      if (state !== "failed-retained") client.removeQueries({ queryKey: key, exact: true });
      let release!: (value: Response) => void;
      const pending = new Promise<Response>(resolve => { release = resolve; });
      const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(() => state === "loading"
        ? pending : Promise.resolve(new Response("", { status: 503 })));
      renderCase(client, actorA, CASE_A);
      if (state === "failed-retained") await act(async () => { await client.invalidateQueries({ queryKey: key, exact: true }); });
      if (state !== "loading") await vi.waitFor(() => expect(client.getQueryState(key)?.status).toBe("error"));
      else expect(client.getQueryState(key)?.status).toBe("pending");
      await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });
      const stage = documentStage(); expect(stage).toBeTruthy();
      const support = [...stage.querySelectorAll<HTMLDetailsElement>(":scope > details")];
      expect(support).toHaveLength(2);
      const callsBeforeExpansion = fetch.mock.calls.length;
      for (const section of support) {
        act(() => { section.open = true; });
        expect(section.open).toBe(true);
        const panel = section.querySelector<HTMLElement>(".document-support-panel")!;
        expect(panel.closest("details")?.open).toBe(true);
        const notice = panel.querySelector<HTMLElement>(state === "loading" ? "[role=status]" : "[role=alert]");
        expect(notice).not.toBeNull();
        expect(notice!.closest("[hidden], [aria-hidden=true]")).toBeNull();
        expect(notice!.textContent).toContain(state === "loading" ? "Loading document information" : "Document information could not be loaded.");
        expect(panel.textContent).not.toContain("No current document is retained.");
        expect(panel.textContent).not.toContain("No document processing evidence is retained.");
        if (state === "failed-retained") expect(notice!.textContent).toContain("Last-confirmed document information remains visible and may be stale.");
        else expect(panel.querySelector("article")).toBeNull();
        expect(panel.querySelector("button, input, select, textarea")).toBeNull();
        act(() => { section.open = false; });
      }
      expect(fetch.mock.calls).toHaveLength(callsBeforeExpansion);
      expect(fetch.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
      if (state === "loading") await act(async () => { release(response([])); });
    },
  );

});


describe("Automation polling document read authority", () => {
  const rejectionEvents = (globalThis as unknown as { process: {
    on: (event: "unhandledRejection", listener: (reason: unknown) => void) => void;
    removeListener: (event: "unhandledRejection", listener: (reason: unknown) => void) => void;
  } }).process;
  const clients: QueryClient[] = [];
  const unhandled: unknown[] = [];
  const recordUnhandled = (reason: unknown) => { unhandled.push(reason); };
  beforeEach(() => { vi.useFakeTimers(); unhandled.length = 0; rejectionEvents.on("unhandledRejection", recordUnhandled); });
  afterEach(() => {
    clients.splice(0).forEach(client => client.clear());
    rejectionEvents.removeListener("unhandledRejection", recordUnhandled);
    vi.useRealTimers();
  });
  function deferred() {
    let resolve!: (value: Response) => void;
    const promise = new Promise<Response>(done => { resolve = done; });
    return { promise, resolve };
  }
  async function tick(ms = 1) { await act(async () => { await vi.advanceTimersByTimeAsync(ms); }); }
  function setup(documents: DocumentProcessingRecord[] = [documentFixture(CASE_A)], productionDefaults = false) {
    const client = productionDefaults ? createSessionQueryClient() : createTestClient(); clients.push(client);
    seedCase(client, actorA, CASE_A, "analysis-a", "a");
    const running = { ...summaryFixture(CASE_A), status: "RUNNING" as const };
    client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), running);
    client.setQueryData(caseQueryKeys.documents(actorA.user_id, CASE_A), documents);
    const docRead = vi.fn<(...args: [RequestInit | undefined]) => Promise<Response>>().mockImplementation(async () => response(documents));
    const ownerRead = vi.fn().mockImplementation(async () => response(ownershipFixture(CASE_A, "polled-owner", "polled")));
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      expect((init?.method ?? "GET").toUpperCase()).toBe("GET");
      const url = String(input);
      if (url.endsWith(`/api/clm/zero-touch/cases/${CASE_A}`)) return response(running);
      if (url.endsWith(`/api/onboarding/cases/${CASE_A}/documents`)) return docRead(init);
      if (url.endsWith(`/api/onboarding/cases/${CASE_A}/ownership`)) return ownerRead();
      if (url.endsWith(`/api/clm/zero-touch/cases/${CASE_A}/intelligence`)) return response(null);
      throw new Error("Unexpected synthetic polling route");
    });
    renderCase(client, actorA, CASE_A);
    return { client, docRead, ownerRead, fetch, key: caseQueryKeys.documents(actorA.user_id, CASE_A) };
  }
  function panels() {
    const stage = [...container!.querySelectorAll<HTMLElement>(".stage-disclosure")]
      .find(item => item.querySelector(":scope > h2")?.textContent === "Document verification")!;
    expect(stage).toBeTruthy();
    const details = [...stage.querySelectorAll<HTMLDetailsElement>(":scope > details")];
    act(() => { details.forEach(section => { section.open = true; }); });
    expect(details).toHaveLength(2); expect(details.every(section => section.open)).toBe(true);
    return [stage.querySelector<HTMLElement>(".document-evidence-panel")!,
      ...details.map(section => section.querySelector<HTMLElement>(".document-support-panel")!)];
  }
  function failed(retained: boolean) {
    const visible = panels();
    for (const panel of visible) {
      const alert = panel.querySelector<HTMLElement>("[role=alert]");
      expect(alert).not.toBeNull(); expect(alert!.closest("[hidden], [aria-hidden=true]")).toBeNull();
      expect(alert!.textContent).toContain("Document information could not be loaded.");
      if (retained) expect(alert!.textContent).toContain("Last-confirmed document information remains visible");
      expect(panel.textContent).not.toContain("No current document is retained.");
      expect(panel.textContent).not.toContain("No document processing evidence is retained.");
    }
    if (!retained) for (const panel of visible.slice(1)) {
      expect(panel.textContent).toContain("Document availability cannot currently be confirmed.");
      expect(panel.querySelector("article")).toBeNull();
    }
  }
  it.each([true, false])("shows truthful polling document failure in all visible projections, retained=%s", async retained => {
    const { client, docRead, key } = setup(retained ? [documentFixture(CASE_A)] : []);
    docRead.mockImplementation(async () => new Response("", { status: 503 }));
    await tick(1000); await tick();
    expect(client.getQueryState(key)?.status).toBe("error"); failed(retained);
  });
  it("labels retained information refreshing while the actual polling read is pending", async () => {
    const { docRead } = setup(); const pending = deferred(); docRead.mockReturnValue(pending.promise);
    await tick(1000); await tick();
    for (const panel of panels()) expect(panel.querySelector("[role=status]")?.textContent).toContain("Loading document information");
    for (const panel of panels().slice(1)) expect(panel.textContent).toContain("Last-confirmed document information remains visible");
    pending.resolve(response([documentFixture(CASE_A)])); await tick();
  });
  it("keeps successful completed empty polling results truthful", async () => {
    const { client, key } = setup([]); await tick(1000); await tick();
    expect(client.getQueryState(key)?.status).toBe("success");
    const [main, more, technical] = panels();
    expect(main.textContent).toContain("No document uploaded"); expect(more.textContent).toContain("No current document is retained.");
    expect(technical.textContent).toContain("No document processing evidence is retained.");
    for (const panel of [main, more, technical]) expect(panel.querySelector("[role=alert], [role=status]")).toBeNull();
  });
  it("retains the polling failure until a current successful recovery finishes", async () => {
    const { docRead, client, key } = setup(); const pending = deferred();
    docRead.mockImplementationOnce(async () => new Response("", { status: 503 })).mockReturnValueOnce(pending.promise);
    await tick(1000); await tick(); failed(true);
    await tick(1000); failed(true);
    pending.resolve(response([{ ...documentFixture(CASE_A), display_name: "fresh-evidence.pdf" }])); await tick();
    expect(client.getQueryState(key)?.status).toBe("success");
    for (const panel of panels()) { expect(panel.textContent).toContain("fresh-evidence.pdf"); expect(panel.querySelector("[role=alert]")).toBeNull(); }
  });
  it("does not let an older polling failure mark a newer query success stale", async () => {
    const { docRead, client, key } = setup(); const old = deferred();
    docRead.mockReturnValueOnce(old.promise).mockImplementationOnce(async () => response([{ ...documentFixture(CASE_A), display_name: "newer-evidence.pdf" }]));
    await tick(1000); const signal = docRead.mock.calls[0][0]?.signal;
    await act(async () => { await client.refetchQueries({ queryKey: key, exact: true }, { cancelRefetch: true, throwOnError: true }); }); await tick();
    old.resolve(new Response("", { status: 503 })); await tick();
    expect(signal?.aborted).toBe(true); expect(client.getQueryState(key)?.status).toBe("success");
    for (const panel of panels()) { expect(panel.textContent).toContain("newer-evidence.pdf"); expect(panel.querySelector("[role=alert]")).toBeNull(); }
    expect(unhandled).toEqual([]);
  });
  it.each(["case", "actor", "logout", "unmount"] as const)("cancels polling support and rejects late publication after %s", async change => {
    const { docRead, client, key } = setup(); const old = deferred(); docRead.mockReturnValue(old.promise); await tick(1000);
    const signal = docRead.mock.calls[0][0]?.signal;
    if (change === "unmount" || change === "logout") act(() => { root!.unmount(); root = null; if (change === "logout") clearSessionQueries(client); });
    const nextActor = change === "actor" || change === "logout" ? actorB : actorA;
    const nextCase = change === "case" || change === "logout" ? CASE_B : CASE_A;
    if (change !== "unmount") {
      seedCase(client, nextActor, nextCase, "next-owner", "next");
      client.setQueryData(caseQueryKeys.documents(nextActor.user_id, nextCase), [{ ...documentFixture(nextCase), display_name: "next-identity.pdf" }]);
      renderCase(client, nextActor, nextCase);
    }
    old.resolve(response([{ ...documentFixture(CASE_A), display_name: "late-old-evidence.pdf" }])); await tick();
    expect(signal?.aborted).toBe(true);
    if (change === "logout") expect(client.getQueryData(key)).toBeUndefined();
    if (change === "unmount") expect(client.getQueryData<DocumentProcessingRecord[]>(key)?.[0].display_name).toBe("evidence-package.pdf");
    else { expect(container!.textContent).not.toContain("late-old-evidence.pdf"); for (const panel of panels()) expect(panel.querySelector("[role=alert]")).toBeNull(); }
    expect(unhandled).toEqual([]);
  });
  it("publishes a successful ownership read independently of a failed document read", async () => {
    const { docRead, client } = setup(); docRead.mockImplementation(async () => new Response("", { status: 503 }));
    await tick(1000); await tick();
    expect(client.getQueryData<OwnershipAnalysisRecord>(caseQueryKeys.ownership(actorA.user_id, CASE_A))?.analysis_id).toBe("polled-owner");
    expect(unhandled).toEqual([]);
  });
  it("handles rejected polling work without an implicit retry, business write or automatic submission", async () => {
    const { docRead, fetch, client, key } = setup(undefined, true); docRead.mockImplementation(async () => new Response("", { status: 503 }));
    await tick(1000); await tick();
    expect(client.getQueryState(key)?.fetchStatus).toBe("idle"); expect(client.getQueryState(key)?.status).toBe("error");
    expect(docRead).toHaveBeenCalledTimes(1); expect(unhandled).toEqual([]);
    expect(fetch.mock.calls.every(([, init]) => (init?.method ?? "GET") === "GET")).toBe(true);
  });
  it("shares a slow in-flight supporting read across unchanged polling cadence", async () => {
    const { docRead } = setup(); const pending: ReturnType<typeof deferred>[] = [];
    docRead.mockImplementation(() => { const read = deferred(); pending.push(read); return read.promise; });
    await tick(1000); await tick(1000);
    const count = docRead.mock.calls.length;
    pending.forEach(read => read.resolve(response([documentFixture(CASE_A)]))); await tick();
    expect(count).toBe(1);
  });
  it("classifies an explicit read-only failure through the same document query authority", async () => {
    const client = createTestClient(); clients.push(client); seedCase(client, actorA, CASE_A, "analysis-a", "a");
    const key = caseQueryKeys.documents(actorA.user_id, CASE_A); let rejectDocuments = true;
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if ((init?.method ?? "GET") !== "GET") return new Response("", { status: 503 });
      if (url.endsWith(`/api/clm/zero-touch/cases/${CASE_A}`)) return response(summaryFixture(CASE_A));
      if (url.endsWith(`/api/onboarding/cases/${CASE_A}/documents`)) return rejectDocuments
        ? new Response("", { status: 503 }) : response([documentFixture(CASE_A)]);
      if (url.endsWith(`/api/onboarding/cases/${CASE_A}/ownership`)) return response(ownershipFixture(CASE_A, "refreshed-owner", "refreshed"));
      if (url.endsWith(`/api/clm/zero-touch/cases/${CASE_A}/intelligence`)) return response(null);
      throw new Error("Unexpected synthetic explicit refresh route");
    });
    renderCase(client, actorA, CASE_A);
    const choice = container!.querySelector<HTMLInputElement>('input[data-review-field="legal_name"][value="ACCEPTED"]')!;
    act(() => choice.click());
    act(() => button("Confirm decisions & continue onboarding").click()); await tick(10);
    expect(container!.textContent).toContain("Evidence reload could not be confirmed.");
    rejectDocuments = false;
    await act(async () => { await client.refetchQueries({ queryKey: key, exact: true }); }); await tick();
    expect(client.getQueryState(key)?.status).toBe("success");
    const writes = fetch.mock.calls.filter(([, init]) => (init?.method ?? "GET") !== "GET").length;
    rejectDocuments = true; act(() => button("Refresh case evidence").click()); await tick(10);
    expect(client.getQueryState(key)?.status).toBe("error"); failed(true);
    expect(fetch.mock.calls.filter(([, init]) => (init?.method ?? "GET") !== "GET")).toHaveLength(writes);
    expect(unhandled).toEqual([]);
  });

});


describe("Ownership and Readiness persistent disclosure", () => {
  function stage(title: string): HTMLElement {
    const found = [...container!.querySelectorAll<HTMLElement>(".stage-disclosure")]
      .find(item => item.querySelector(":scope > h2")?.textContent === title);
    expect(found).toBeTruthy(); return found!;
  }
  function partitions(title: string) {
    const region = stage(title);
    expect(region.querySelector(":scope > h2 button")).not.toBeNull();
    const support = [...region.querySelectorAll<HTMLDetailsElement>(":scope > details")];
    expect(support.map(item => item.querySelector("summary")?.textContent)).toEqual([
      `More details — ${title}`, `Technical details — ${title}`,
    ]);
    return { region, main: region.querySelector<HTMLElement>(":scope > div")!, support };
  }
  function editableSummary() {
    const summary = summaryFixture(CASE_A);
    summary.ownership_edit_authorized = true;
    summary.ownership_recovery = { analysis_id: "analysis-a", version: 3, state: "ANALYZED", manual_evidence_action: null, review_receipt: null };
    summary.clm.version = 7;
    summary.target_classification = {
      vocabulary_version: "synthetic-v1", evidence_fingerprint: "fingerprint-a", current: true, editable: true,
      kyc_customer_type: { allowed_values: ["Company - Private", "Government"], selected_value: null, authority: null, required: true },
      client_segment: { allowed_values: ["Corporate"], selected_value: null, authority: null, required: true },
    };
    summary.case.policy_rebind = {
      revision: 1, configuration_status: "REQUIRES_REBIND", accepted_poc_fields: [], editable_fields: ["kycCustomerType", "clientSegment"],
      upstream_fields: ["registrationNumber"], unavailable_fields: [], last_rebound_by: null, last_rebound_at: null,
      last_rationale: null, last_changed_fields: [],
    };
    return summary;
  }
  function setup() {
    const client = createTestClient(); seedCase(client, actorA, CASE_A, "analysis-a", "a");
    client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), editableSummary());
    client.setQueryData(caseQueryKeys.documents(actorA.user_id, CASE_A), [{ ...documentFixture(CASE_A), state: "REVIEWED" }]);
    return client;
  }
  function input(element: HTMLTextAreaElement, value: string) {
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!.call(element, value);
    element.dispatchEvent(new Event("input", { bubbles: true }));
  }
  it("keeps graph and single correction in Main with lazy optional retained path inspection", () => {
    const client = setup(); const fetch = vi.spyOn(globalThis, "fetch"); renderCase(client, actorA, CASE_A);
    const { main, support, region } = partitions("Ownership & UBO");
    expect(support.every(item => !item.open)).toBe(true);
    expect(main.querySelector(".manual-ownership form")).not.toBeNull();
    expect(main.querySelector('[aria-label="Hierarchical ownership structure"]')).not.toBeNull();
    expect(main.querySelector('[aria-label="Selected retained path a-path-1"]')).toBeNull();
    openPathInspection();
    expect(main.querySelector('[aria-label="Selected retained path a-path-1"]')).not.toBeNull();
    expect(main.querySelector('button[aria-pressed]')).not.toBeNull();
    expect(region.querySelectorAll(".manual-ownership form")).toHaveLength(1);
    for (const panel of support) expect(panel.querySelector("button, input, select, textarea, details")).toBeNull();
    act(() => { support[0].open = true; }); expect(support[1].open).toBe(false);
    act(() => { support[1].open = true; support[0].open = false; });
    expect(main.textContent).toContain("37.5%"); expect(main.textContent).toContain("GREATER_THAN_OR_EQUAL_TO");
    expect(main.textContent).toContain("LOCAL");
    expect(support[1].textContent).toContain("37.500000000000000010");
    const ids = [...region.querySelectorAll("[id]")].map(item => item.id);
    expect(new Set(ids).size).toBe(ids.length); expect(fetch).not.toHaveBeenCalled();
  });
  it("keeps readiness blockers, rebind and vocabulary-bound classification forms in Main", () => {
    const client = setup(); const fetch = vi.spyOn(globalThis, "fetch"); renderCase(client, actorA, CASE_A);
    const { main, support, region } = partitions("Submission readiness");
    expect(support.every(item => !item.open)).toBe(true);
    expect(main.textContent).toContain("Retained document conflict requires review.");
    expect(main.textContent).toContain("Registry: READY");
    expect(main.querySelector("#policy-rebind-rationale")).not.toBeNull();
    expect(main.querySelectorAll("select")).toHaveLength(2);
    expect([...main.querySelectorAll<HTMLSelectElement>("select")].map(select => [...select.options].map(option => option.value)))
      .toEqual([["", "Company - Private", "Government"], ["", "Corporate"]]);
    expect(main.querySelectorAll("details")).toHaveLength(0);
    for (const panel of support) expect(panel.querySelector("button, input, select, textarea, details")).toBeNull();
    expect(support[1].textContent).toContain("fingerprint-a"); expect(support[1].textContent).toContain("synthetic-v1");
    const ids = [...region.querySelectorAll("[id]")].map(item => item.id);
    expect(new Set(ids).size).toBe(ids.length); expect(fetch).not.toHaveBeenCalled();
  });
  it("preserves all three drafts and path selection through support toggles and harmless refresh", async () => {
    const client = setup(); const fetch = vi.spyOn(globalThis, "fetch"); renderCase(client, actorA, CASE_A);
    const owner = partitions("Ownership & UBO"); const readiness = partitions("Submission readiness");
    const note = owner.main.querySelector<HTMLTextAreaElement>('[name="rationale"]')!;
    const rationale = readiness.main.querySelector<HTMLTextAreaElement>("#policy-rebind-rationale")!;
    const select = readiness.main.querySelector<HTMLSelectElement>('select[aria-label="KYC customer type"]')!;
    act(() => { input(note, "Unsaved ownership note"); input(rationale, "Unsaved rebind rationale");
      select.value = "Government"; select.dispatchEvent(new Event("change", { bubbles: true })); });
    click("Inspect a-path-2");
    act(() => { for (const section of [...owner.support, ...readiness.support]) { section.open = true; section.open = false; } });
    await act(async () => { client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), { ...editableSummary(), updated_at: "2026-10-16T03:00:00Z" }); await new Promise(resolve => setTimeout(resolve, 0)); });
    expect(note.isConnected).toBe(true); expect(note.value).toBe("Unsaved ownership note");
    expect(rationale.isConnected).toBe(true); expect(rationale.value).toBe("Unsaved rebind rationale");
    expect(select.isConnected).toBe(true); expect(select.value).toBe("Government");
    expect(owner.main.querySelector('[aria-label="Selected retained path a-path-2"]')).not.toBeNull();
    expect(fetch).not.toHaveBeenCalled();
  });
  it.each(["fingerprint", "policy revision", "actor", "case"] as const)("retires incompatible readiness drafts at %s", async change => {
    const client = setup(); seedCase(client, actorB, CASE_A, "analysis-b", "b"); seedCase(client, actorA, CASE_B, "analysis-b", "b");
    client.setQueryData(caseQueryKeys.detail(actorB.user_id, CASE_A), editableSummary());
    client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_B), { ...editableSummary(), case: { ...editableSummary().case, case_id: CASE_B } });
    renderCase(client, actorA, CASE_A); const { main } = partitions("Submission readiness");
    const rationale = main.querySelector<HTMLTextAreaElement>("#policy-rebind-rationale")!;
    const select = main.querySelector<HTMLSelectElement>('select[aria-label="KYC customer type"]')!;
    act(() => { input(rationale, "Old case policy rationale"); select.value = "Government"; select.dispatchEvent(new Event("change", { bubbles: true })); });
    if (change === "actor") renderCase(client, actorB, CASE_A);
    else if (change === "case") renderCase(client, actorA, CASE_B);
    else await act(async () => { const next = editableSummary();
      if (change === "fingerprint") next.target_classification = { ...next.target_classification!, evidence_fingerprint: "fingerprint-new" };
      else next.case.policy_rebind = { ...next.case.policy_rebind!, revision: 2 };
      client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), next); await new Promise(resolve => setTimeout(resolve, 0)); });
    const next = partitions("Submission readiness").main;
    if (change !== "fingerprint") expect(next.querySelector<HTMLTextAreaElement>("#policy-rebind-rationale")!.value).toBe("");
    if (change !== "policy revision") expect(next.querySelector<HTMLSelectElement>('select[aria-label="KYC customer type"]')!.value).toBe("");
  });
  it.each(["loading", "failed-empty", "confirmed-empty", "failed-retained", "pending-retained", "recovery"] as const)(
    "truthfully projects %s ownership reads in every partition", async state => {
      const client = setup(); const key = caseQueryKeys.ownership(actorA.user_id, CASE_A);
      if (["loading", "failed-empty"].includes(state)) client.removeQueries({ queryKey: key, exact: true });
      if (state === "confirmed-empty") client.setQueryData(key, null);
      let release!: (value: Response) => void;
      const pending = new Promise<Response>(resolve => { release = resolve; });
      const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(() => ["loading", "pending-retained"].includes(state)
        ? pending : Promise.resolve(new Response("", { status: 503 })));
      renderCase(client, actorA, CASE_A);
      let refresh: Promise<void> | undefined;
      if (["failed-retained", "pending-retained", "recovery"].includes(state)) await act(async () => {
        refresh = client.invalidateQueries({ queryKey: key, exact: true });
        if (state !== "pending-retained") await refresh;
      });
      if (state === "recovery") {
        fetch.mockImplementation(async () => response(ownershipFixture(CASE_A, "analysis-a", "a")));
        await act(async () => { await client.refetchQueries({ queryKey: key, exact: true }); });
      } else if (state.startsWith("failed")) await vi.waitFor(() => expect(client.getQueryState(key)?.status).toBe("error"));
      await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });
      const { main, support } = partitions("Ownership & UBO");
      const calls = fetch.mock.calls.length;
      for (const panel of [main, ...support]) {
        if (panel instanceof HTMLDetailsElement) act(() => { panel.open = true; });
        if (state === "confirmed-empty") expect(panel.textContent).toContain("No ownership analysis is retained in the confirmed response.");
        else if (state === "recovery") expect(panel.textContent).not.toContain("could not be loaded");
        else {
          const notice = panel.querySelector(state.startsWith("failed") ? "[role=alert]" : "[role=status]");
          expect(notice).not.toBeNull();
          expect(notice!.textContent).toContain(state.startsWith("failed") ? "Ownership information could not be loaded." : "Loading ownership information");
          if (state.endsWith("retained")) expect(notice!.textContent).toContain("Last-confirmed ownership information");
          expect(panel.textContent).not.toContain("No ownership analysis is retained");
        }
      }
      expect(fetch.mock.calls).toHaveLength(calls);
      if (["loading", "pending-retained"].includes(state)) await act(async () => { release(response(null)); await refresh; });
      client.clear();
    },
  );
  it.each(["failed-retained", "pending-retained", "recovery"] as const)("qualifies %s readiness instead of claiming current success", async state => {
    const client = setup(); const key = caseQueryKeys.detail(actorA.user_id, CASE_A);
    let release!: (value: Response) => void; const pending = new Promise<Response>(resolve => { release = resolve; });
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(() => state === "pending-retained" ? pending : Promise.resolve(new Response("", { status: 503 })));
    renderCase(client, actorA, CASE_A); let refresh: Promise<void> | undefined;
    await act(async () => { refresh = client.invalidateQueries({ queryKey: key, exact: true }); if (state !== "pending-retained") await refresh; });
    if (state === "recovery") { fetch.mockImplementation(async () => response(editableSummary())); await act(async () => { await client.refetchQueries({ queryKey: key, exact: true }); }); }
    await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });
    const { main, support } = partitions("Submission readiness");
    for (const panel of [main, ...support]) {
      if (panel instanceof HTMLDetailsElement) act(() => { panel.open = true; });
      if (state === "recovery") expect(panel.textContent).not.toContain("could not be loaded");
      else {
        const notice = panel.querySelector(state === "failed-retained" ? "[role=alert]" : "[role=status]");
        expect(notice).not.toBeNull(); expect(notice!.textContent).toContain("Last-confirmed readiness information");
        expect(panel.textContent).not.toContain("No readiness evidence");
        for (const control of main.querySelectorAll<HTMLButtonElement | HTMLSelectElement | HTMLTextAreaElement>("form button, form select, form textarea")) expect(control.disabled).toBe(true);
      }
    }
    if (state === "pending-retained") await act(async () => { release(response(editableSummary())); await refresh; });
    client.clear();
  });
  it.each(["loading", "failed-empty"] as const)("keeps %s initial case/readiness unavailable without inferred success", async state => {
    const client = createTestClient();
    client.setQueryData(caseQueryKeys.documents(actorA.user_id, CASE_A), []);
    client.setQueryData(caseQueryKeys.ownership(actorA.user_id, CASE_A), null);
    client.setQueryData(caseQueryKeys.intelligence(actorA.user_id, CASE_A), null);
    let release!: (value: Response) => void; const pending = new Promise<Response>(resolve => { release = resolve; });
    vi.spyOn(globalThis, "fetch").mockImplementation(() => state === "loading" ? pending : Promise.resolve(new Response("", { status: 503 })));
    renderCase(client, actorA, CASE_A);
    if (state === "failed-empty") await vi.waitFor(() => expect(client.getQueryState(caseQueryKeys.detail(actorA.user_id, CASE_A))?.status).toBe("error"));
    expect(container!.querySelector('[aria-label="Backend-projected readiness"]')).toBeNull();
    expect(container!.querySelector(".review-and-send, .stage-disclosure--final")).toBeNull();
    expect(container!.textContent).not.toContain("Backend submission state:");
    expect(container!.textContent).not.toContain("No readiness evidence");
    expect(container!.textContent).not.toContain("Current accepted POC");
    expect(container!.querySelector("form")).toBeNull();
    if (state === "loading") {
      expect(container!.textContent).toContain("Loading case");
      await act(async () => { release(response(summaryFixture(CASE_A))); });
    }
    client.clear();
  });
  it("shows confirmed missing readiness inputs and the backend blockers without manufacturing a result", () => {
    const client = setup(); const summary = summaryFixture(CASE_A);
    summary.target_classification = { ...editableSummary().target_classification!, evidence_state: "NO_EVIDENCE", current: false };
    summary.case.policy_rebind = undefined;
    summary.clm.readiness.registry.status = "MISSING";
    summary.clm.readiness.ownership.status = "BLOCKED";
    client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), summary);
    const fetch = vi.spyOn(globalThis, "fetch"); renderCase(client, actorA, CASE_A);
    const { main, support } = partitions("Submission readiness");
    expect(main.textContent).toContain("Registry: MISSING"); expect(main.textContent).toContain("Ownership: BLOCKED");
    expect(main.textContent).toContain("Retained document conflict requires review.");
    expect(main.querySelector("#case-policy-rebind")).toBeNull();
    expect(main.querySelector<HTMLSelectElement>('select[aria-label="KYC customer type"]')!.value).toBe("");
    expect(main.querySelector<HTMLSelectElement>('select[aria-label="Client segment"]')!.value).toBe("");
    for (const panel of support) { act(() => { panel.open = true; }); expect(panel.textContent).not.toContain("No readiness evidence"); expect(panel.textContent).not.toContain("Current accepted POC"); }
    expect(fetch).not.toHaveBeenCalled();
  });
  it.each(["ownership", "readiness"] as const)("ignores an older failed %s read after a newer success", async resource => {
    const client = setup(); const key = resource === "ownership" ? caseQueryKeys.ownership(actorA.user_id, CASE_A) : caseQueryKeys.detail(actorA.user_id, CASE_A);
    let release!: (value: Response) => void; const old = new Promise<Response>(resolve => { release = resolve; });
    const next = resource === "ownership" ? ownershipFixture(CASE_A, "newer-success", "fresh") : { ...editableSummary(), version: 2 };
    const fetch = vi.spyOn(globalThis, "fetch").mockReturnValueOnce(old).mockImplementation(async () => response(next));
    renderCase(client, actorA, CASE_A); let refresh: Promise<void> | undefined;
    await act(async () => { refresh = client.invalidateQueries({ queryKey: key, exact: true }); await new Promise(resolve => setTimeout(resolve, 0)); });
    const signal = (fetch.mock.calls[0][1] as RequestInit).signal;
    await act(async () => { await client.refetchQueries({ queryKey: key, exact: true }, { cancelRefetch: true, throwOnError: true }); });
    await act(async () => { release(new Response("", { status: 503 })); await refresh; await new Promise(resolve => setTimeout(resolve, 0)); });
    expect(signal?.aborted).toBe(true); expect(client.getQueryState(key)?.status).toBe("success");
    const { main, support } = partitions(resource === "ownership" ? "Ownership & UBO" : "Submission readiness");
    for (const panel of [main, ...support]) {
      if (panel instanceof HTMLDetailsElement) act(() => { panel.open = true; });
      expect(panel.textContent).not.toContain("information could not be loaded");
      expect(panel.textContent).not.toContain("Last-confirmed");
    }
    expect(fetch.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true); client.clear();
  });
  it.each(["ownership", "readiness"] as const)("rejects late %s evidence across case, actor and session replacement", async resource => {
    const client = setup(); const key = resource === "ownership" ? caseQueryKeys.ownership(actorA.user_id, CASE_A) : caseQueryKeys.detail(actorA.user_id, CASE_A);
    let release!: (value: Response) => void; const old = new Promise<Response>(resolve => { release = resolve; });
    const fetch = vi.spyOn(globalThis, "fetch").mockReturnValue(old);
    renderCase(client, actorA, CASE_A); let refresh: Promise<void> | undefined;
    await act(async () => { refresh = client.invalidateQueries({ queryKey: key, exact: true }); await new Promise(resolve => setTimeout(resolve, 0)); });
    const signal = (fetch.mock.calls[0][1] as RequestInit).signal;
    act(() => { root!.unmount(); root = null; clearSessionQueries(client); });
    seedCase(client, actorB, CASE_B, "new-session-analysis", "NEXT"); renderCase(client, actorB, CASE_B);
    const late = resource === "ownership" ? ownershipFixture(CASE_A, "late-old-analysis", "LATE_OLD") : { ...editableSummary(), case: { ...editableSummary().case, requested_uen: "LATE_OLD" } };
    await act(async () => { release(response(late)); await refresh; await new Promise(resolve => setTimeout(resolve, 0)); });
    expect(signal?.aborted).toBe(true); expect(client.getQueryData(key)).toBeUndefined();
    expect(container!.textContent).not.toContain("LATE_OLD");
    for (const name of ["Ownership & UBO", "Submission readiness"]) {
      const { main, support } = partitions(name);
      for (const panel of [main, ...support]) { if (panel instanceof HTMLDetailsElement) act(() => { panel.open = true; }); expect(panel.textContent).not.toContain("LATE_OLD"); }
    }
    client.clear();
  });

  it("keeps exact current conflicting classification values beside the authorized Main choices", () => {
    const client = setup(); const summary = editableSummary();
    summary.target_classification = { ...summary.target_classification, evidence_state: "CONFLICT", current: false,
      evidence_values: { kyc_customer_type: ["Company - Private", "Partnership - Unregulated"], client_segment: ["Corporate"] } };
    client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), summary);
    renderCase(client, actorA, CASE_A); const { main, support } = partitions("Submission readiness");
    expect(support.every(item => !item.open)).toBe(true);
    expect(main.querySelector('[aria-label="Current trusted classification values"]')?.textContent).toContain("Company - Private; Partnership - Unregulated");
    expect(main.querySelector('select[aria-label="KYC customer type"]')).not.toBeNull();
    expect(container!.querySelectorAll('[aria-label="Current trusted classification values"]')).toHaveLength(1);
  });

});


describe("GoldTier and Final Review persistent disclosure", () => {
  function partitions(title: string) {
    const region = [...container!.querySelectorAll<HTMLElement>(".stage-disclosure")]
      .find(item => item.querySelector(":scope > h2")?.textContent === title)!;
    expect(region).toBeTruthy();
    expect(region.querySelector(":scope > h2 button")).not.toBeNull();
    const support = [...region.querySelectorAll<HTMLDetailsElement>(":scope > details")];
    expect(support.map(item => item.querySelector("summary")?.textContent)).toEqual([
      `More details — ${title}`, `Technical details — ${title}`,
    ]);
    return { region, main: region.querySelector<HTMLElement>(":scope > div")!, support };
  }
  function targetSummary(state: NonNullable<ZeroTouchCaseSummary["target_submission"]>["state"] = "NOT_SUBMITTED") {
    const summary = summaryFixture(CASE_A);
    summary.current_stage = "READINESS";
    summary.active_exceptions = [{ ...summary.active_exceptions[0], exception_type: "TARGET_CONFIRMATION_REQUIRED", blocker_code: "TARGET_CONFIRMATION_REQUIRED", stage: "MOCK_GOLDTIER" }];
    summary.clm.readiness.blockers = [];
    summary.clm.version = 4;
    summary.clm.submission_plan.request_preview = {
      environment: "MOCK", dispatch_ready: true, policy_version: 2,
      operations: [{ operation: "SHELL", validation: "VALID", missing_fields: [], fields: [
        { target_field: "legal_name", value: "Synthetic review identity", provenance: "REGISTRY", authority: "CANONICAL_EVIDENCE", required: true, missing: false, validation: "VALID" },
      ] }],
    };
    summary.case.identity_corrections = [];
    summary.target_submission = { state, submission_id: "00000000-0000-4000-8000-00000000f001", status_check_available: state === "SUBMISSION_OUTCOME_UNCERTAIN", recovery_available: true, recovery_operation: "SHELL", attempted_operations: ["SEARCH", "SHELL"], definitively_completed_operations: ["SEARCH"], lifecycle_resolved_operations: ["SEARCH"], ledger_state: "OUTCOME_UNCERTAIN" } as NonNullable<ZeroTouchCaseSummary["target_submission"]>;
    return summary;
  }
  function setup(summary = targetSummary(), profile = actorA) {
    const client = createTestClient(); seedCase(client, profile, CASE_A, "analysis-a", "a");
    client.setQueryData(caseQueryKeys.detail(profile.user_id, CASE_A), summary);
    renderCase(client, profile, CASE_A); return client;
  }
  function collapsedTargetHeader() {
    const { region, main } = partitions("GoldTier submission package");
    const toggle = region.querySelector<HTMLButtonElement>(":scope > h2 button")!;
    if (toggle.getAttribute("aria-expanded") === "true") act(() => toggle.click());
    expect(main.hidden).toBe(true);
    const description = document.getElementById(toggle.getAttribute("aria-describedby")!)!;
    expect(description).toBe(region.querySelector(":scope > .stage-disclosure__summary"));
    expect(description.hidden).toBe(false);
    expect(description.closest("[hidden]")).toBeNull();
    return description.textContent!;
  }
  it.each([
    ["NOT_SUBMITTED", "Submission not started."],
    ["SENDING", "Submission in progress — do not send again. Reviewed package frozen."],
    ["SUBMISSION_CONFIRMED", "Submission confirmed. Reviewed package frozen."],
    ["SUBMISSION_FAILED", "Submission failed — review required. Reviewed package frozen."],
    ["SUBMISSION_OUTCOME_UNCERTAIN", "Submission outcome uncertain — verification required. Reviewed package frozen."],
    ["FINALIZATION_PENDING", "Submission finalization pending — review required. Reviewed package frozen."],
  ] as const)("Round4 complete Final header for %s across current, pending and failed reads", async (state, status) => {
    const summary = targetSummary(state); const client = setup(summary);
    const key = caseQueryKeys.documents(actorA.user_id, CASE_A);
    const fetch = vi.spyOn(globalThis, "fetch");
    function inspect(prefix: string, current: boolean) {
      const { region, main } = partitions("Final review & send");
      const toggle = region.querySelector<HTMLButtonElement>(":scope > h2 button")!;
      if (toggle.getAttribute("aria-expanded") === "true") act(() => toggle.click());
      const description = region.querySelector<HTMLElement>(":scope > .stage-disclosure__summary")!;
      expect(main.hidden).toBe(true); expect(description.closest("[hidden]")).toBeNull();
      expect(document.getElementById(toggle.getAttribute("aria-describedby")!)).toBe(description);
      const ready = current && state === "NOT_SUBMITTED";
      expect(description.textContent!.trim()).toBe(prefix + status + (ready ? " Action required — review the package before Confirm and send." : ""));
      if (!ready) expect(description.textContent).not.toMatch(/before sending|before Confirm and send|Action required — review the package/);
      const sends = [...main.querySelectorAll("button")].filter(item => item.textContent?.startsWith("Confirm and send"));
      expect(sends).toHaveLength(state === "NOT_SUBMITTED" ? 1 : 0);
      expect(main.textContent).toContain("What will be sent"); expect(main.textContent).toContain("Synthetic review identity");
      act(() => { window.dispatchEvent(new Event("beforeprint")); window.dispatchEvent(new Event("afterprint")); });
      expect(toggle.getAttribute("aria-expanded")).toBe("false");
      expect(fetch).not.toHaveBeenCalled();
    }
    inspect("", true);
    let reject!: (error: Error) => void;
    const pending = new Promise<unknown>((_resolve, fail) => { reject = fail; });
    let read!: Promise<unknown>;
    await act(async () => { read = client.fetchQuery({ queryKey: key, queryFn: () => pending, staleTime: 0, retry: false }).catch(() => undefined); });
    await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });
    inspect("Last-confirmed final review information (refresh in progress). ", false);
    await act(async () => { reject(new Error("Synthetic unavailable supporting read")); await read; });
    await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });
    inspect("Last-confirmed final review information (refresh failed; may be stale). ", false);
    client.clear();
  });
  it.each(["blocked", "unauthorized", "confirmation", "legacy-frozen", "intervention-frozen", "safe-continuation"] as const)(
    "Round4 complete Final header preserves %s priority without another Send", mode => {
      const summary = targetSummary(mode === "intervention-frozen" ? "SUBMISSION_FAILED" : mode === "safe-continuation" ? "FINALIZATION_PENDING" : "NOT_SUBMITTED");
      let expected = "Submission not started. ";
      if (mode === "blocked") { summary.clm.readiness.blockers = ["Retained blocker"]; expected += "Review current blockers and outstanding items."; }
      if (mode === "unauthorized") expected += "You do not have the case capability required to confirm this dispatch.";
      if (mode === "confirmation") {
        summary.case.target_dispatch_confirmation = { confirmation_id: "retained", actor_id: "synthetic", confirmed_at: NOW, case_event_count: 1, clm_version: 4, destination: "GOLDTIER_MOCK", warnings: [], review_digest: "a".repeat(64), classification: "USER_AUTHORIZED_POC" };
        expected += "Reviewed package frozen.";
      }
      if (mode === "legacy-frozen") { summary.target_submission = undefined; summary.clm.submission = {} as NonNullable<ZeroTouchCaseSummary["clm"]["submission"]>; expected = "Submission state not available in retained evidence. Reviewed package frozen."; }
      if (mode === "intervention-frozen") { summary.interventions = [{ intervention_id: "r4-target", owning_stage: "MOCK_GOLDTIER", owning_stage_label: "Target", title: "Review", blocker_code: "TARGET_REVIEW", explanation: "Retained review", required_evidence_or_input: [], authorized_actions: [], no_action_reason: "No action", expected_next_step: "Review", candidate_summaries: [] }]; expected = "Target intervention requires review. Reviewed package frozen."; }
      if (mode === "safe-continuation") { summary.status = "RECOVERY_PENDING"; expected = "Verified work retained — safe continuation requires review. Reviewed package frozen."; }
      const fetch = vi.spyOn(globalThis, "fetch"); const client = setup(summary, mode === "unauthorized" ? { ...actorA, capabilities: [] } : actorA);
      const { region, main } = partitions("Final review & send"); const toggle = region.querySelector<HTMLButtonElement>(":scope > h2 button")!;
      act(() => toggle.click()); const description = document.getElementById(toggle.getAttribute("aria-describedby")!)!;
      expect(description.textContent!.trim()).toBe(expected); expect(description.closest("[hidden]")).toBeNull(); expect(main.hidden).toBe(true);
      expect(description.textContent).not.toMatch(/before sending|before Confirm and send/);
      expect([...main.querySelectorAll("button")].some(item => item.textContent?.startsWith("Confirm and send"))).toBe(false);
      expect(fetch).not.toHaveBeenCalled(); client.clear();
    },
  );
  it.each(["ownership", "documents"] as const)("Round4 missing %s read omits confirmation guidance while loading and unavailable", async resource => {
    const summary = targetSummary(); const client = createTestClient(); seedCase(client, actorA, CASE_A, "r4", "R4");
    client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), summary);
    const key = caseQueryKeys[resource](actorA.user_id, CASE_A); client.removeQueries({ queryKey: key, exact: true });
    let release!: (value: Response) => void; const pending = new Promise<Response>(resolve => { release = resolve; });
    const fetch = vi.spyOn(globalThis, "fetch").mockReturnValue(pending); renderCase(client, actorA, CASE_A);
    const { region } = partitions("Final review & send"); const toggle = region.querySelector<HTMLButtonElement>(":scope > h2 button")!; act(() => toggle.click());
    const description = document.getElementById(toggle.getAttribute("aria-describedby")!)!;
    expect(description.textContent!.trim()).toBe("Loading final review information — current evidence not yet confirmed. Submission not started.");
    await act(async () => { release(new Response("", { status: 503 })); });
    await vi.waitFor(() => expect(description.textContent!.trim()).toBe("Current evidence unavailable; absence not confirmed. Submission not started."));
    expect(description.textContent).not.toMatch(/before sending|before Confirm and send|Last-confirmed/);
    expect(fetch.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true); client.clear();
  });
  it.each([
    ["NOT_SUBMITTED", "Submission not started"],
    ["SENDING", "Submission in progress — do not send again"],
    ["SUBMISSION_FAILED", "Submission failed — review required"],
    ["SUBMISSION_CONFIRMED", "Submission confirmed"],
    ["SUBMISSION_OUTCOME_UNCERTAIN", "Submission outcome uncertain — verification required"],
    ["FINALIZATION_PENDING", "Submission finalization pending — review required"],
  ] as const)("collapsed target header describes backend %s", (state, message) => {
    const summary = targetSummary(state); summary.active_exceptions = [];
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => response({ submission_id: summary.target_submission!.submission_id, result: "CHECK_FAILED", message: "Synthetic observation unavailable", checked_at: NOW }));
    const client = setup(summary, { ...actorA, capabilities: [] });
    expect(collapsedTargetHeader()).toContain(message);
    expect(collapsedTargetHeader()).toContain("MOCK");
    expect(fetch).not.toHaveBeenCalled(); client.clear();
  });
  it.each([true, false])("collapsed target header exposes preflight attention for authorized=%s without granting an action", authorized => {
    const summary = targetSummary(); summary.active_exceptions = [];
    summary.case.initial_identity = { legal_name: "Synthetic identity", registration_number: "202400001A", country_of_incorporation: "SG" };
    summary.clm.target_search_checkpoint = { status: "FAILED", disposition: "FAILED" } as NonNullable<ZeroTouchCaseSummary["clm"]["target_search_checkpoint"]>;
    const fetch = vi.spyOn(globalThis, "fetch"); const client = setup(summary, { ...actorA, capabilities: authorized ? ["CASE_ACCESS"] : [] });
    expect(collapsedTargetHeader()).toContain("Attention required — GoldTier availability check needed");
    expect(collapsedTargetHeader()).not.toContain("available.");
    expect([...partitions("GoldTier submission package").main.querySelectorAll("button")].some(item => item.textContent === "Check GoldTier availability")).toBe(authorized);
    expect(fetch).not.toHaveBeenCalled(); client.clear();
  });
  it.each([true, false])("collapsed target header retains projection-only intervention with action authorized=%s", authorized => {
    const summary = targetSummary(); summary.active_exceptions = []; summary.evidence_decision_authorized = authorized;
    summary.interventions = [{ intervention_id: "target-review", owning_stage: "MOCK_GOLDTIER", owning_stage_label: "GoldTier", title: "Review target evidence", blocker_code: "MOCK_GOLDTIER_REVIEW_REQUIRED", explanation: "Synthetic target evidence needs review", required_evidence_or_input: [], authorized_actions: [], no_action_reason: "No correction is currently authorized.", expected_next_step: "Review retained evidence", candidate_summaries: [] }];
    const fetch = vi.spyOn(globalThis, "fetch"); const client = setup(summary);
    expect(collapsedTargetHeader()).toContain("Target intervention requires review");
    expect(collapsedTargetHeader()).not.toContain("available");
    expect(partitions("GoldTier submission package").main.querySelector(".intervention-card button")).toBeNull();
    expect(fetch).not.toHaveBeenCalled(); client.clear();
  });
  it.each(["NOT_SUBMITTED", "SUBMISSION_CONFIRMED", "SUBMISSION_OUTCOME_UNCERTAIN", "SENDING"] as const)("collapsed target header prioritizes intervention and uncertainty over routine %s", state => {
    const summary = targetSummary(state); summary.active_exceptions = [];
    summary.interventions = [{ intervention_id: "target-priority", owning_stage: "MOCK_GOLDTIER", owning_stage_label: "GoldTier", title: "Review target", blocker_code: "MOCK_GOLDTIER_REVIEW_REQUIRED", explanation: "Retained target review", required_evidence_or_input: [], authorized_actions: [], no_action_reason: "No correction authorized", expected_next_step: "Review", candidate_summaries: [] }];
    const fetch = vi.spyOn(globalThis, "fetch"); const client = setup(summary, { ...actorA, capabilities: [] });
    expect(collapsedTargetHeader()).toContain(state === "SUBMISSION_OUTCOME_UNCERTAIN" ? "Submission outcome uncertain — verification required"
      : state === "SENDING" ? "Submission in progress — do not send again" : "Target intervention requires review");
    expect(fetch).not.toHaveBeenCalled(); client.clear();
  });
  it.each([true, false])("collapsed target header exposes pending recovery with submission projection=%s", retained => {
    const summary = targetSummary("FINALIZATION_PENDING"); summary.status = "RECOVERY_PENDING"; summary.active_exceptions = [];
    if (!retained) summary.target_submission = undefined;
    const fetch = vi.spyOn(globalThis, "fetch"); const client = setup(summary);
    expect(collapsedTargetHeader()).toContain(retained ? "Verified work retained — safe continuation requires review" : "Backend recovery pending — review required");
    expect(fetch).not.toHaveBeenCalled(); client.clear();
  });
  it.each(["pending", "failed"] as const)("collapsed target header qualifies %s refresh and retains attention without new confirmation", async state => {
    const summary = targetSummary(); summary.active_exceptions = [];
    summary.clm.target_search_checkpoint = { status: "FAILED", disposition: "FAILED" } as NonNullable<ZeroTouchCaseSummary["clm"]["target_search_checkpoint"]>;
    const client = setup(summary); collapsedTargetHeader();
    let release!: (value: Response) => void; const pending = new Promise<Response>(resolve => { release = resolve; });
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(() => state === "pending" ? pending : Promise.resolve(new Response("", { status: 503 })));
    let refresh: Promise<void> | undefined;
    await act(async () => { refresh = client.invalidateQueries({ queryKey: caseQueryKeys.detail(actorA.user_id, CASE_A), exact: true }); if (state === "failed") await refresh; });
    await vi.waitFor(() => expect(collapsedTargetHeader()).toContain(state === "pending" ? "refresh in progress" : "refresh failed; may be stale"));
    expect(collapsedTargetHeader()).toContain("Last-confirmed target information");
    expect(collapsedTargetHeader()).toContain("GoldTier availability check needed");
    expect(collapsedTargetHeader()).not.toContain("Submission confirmed");
    expect(fetch.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
    if (state === "pending") await act(async () => { release(response(summary)); await refresh; }); client.clear();
  });
  it("collapsed target header updates retained state without reopening or mutating", async () => {
    const summary = targetSummary(); summary.active_exceptions = [];
    const fetch = vi.spyOn(globalThis, "fetch"); const client = setup(summary);
    expect(collapsedTargetHeader()).toContain("Submission not started");
    const next = targetSummary("SUBMISSION_CONFIRMED"); next.version += 1; next.active_exceptions = [];
    await act(async () => { client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), next); await new Promise(resolve => setTimeout(resolve, 0)); });
    expect(partitions("GoldTier submission package").region.querySelector(":scope > h2 button")!.getAttribute("aria-expanded")).toBe("false");
    expect(collapsedTargetHeader()).toContain("Submission confirmed");
    expect([...container!.querySelectorAll("button")].some(item => item.textContent?.startsWith("Confirm and send"))).toBe(false);
    const toggle = partitions("GoldTier submission package").region.querySelector<HTMLButtonElement>(":scope > h2 button")!;
    act(() => { toggle.click(); toggle.click(); });
    expect(fetch).not.toHaveBeenCalled(); client.clear();
  });
  it.each(["NOT_SUBMITTED", "SENDING", "SUBMISSION_CONFIRMED", "SUBMISSION_FAILED", "SUBMISSION_OUTCOME_UNCERTAIN", "FINALIZATION_PENDING"] as const)(
    "keeps %s target/review state and one authorized action owner visible with support closed", state => {
      const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => response({ submission_id: "00000000-0000-4000-8000-00000000f001", result: "CHECK_FAILED", message: "Synthetic read-only observation unavailable", checked_at: NOW })); const client = setup(targetSummary(state));
      const target = partitions("GoldTier submission package"); const review = partitions("Final review & send");
      for (const { region, main, support } of [target, review]) {
        expect(main.hidden).toBe(false); expect(support.every(item => !item.open)).toBe(true);
        for (const panel of support) expect(panel.querySelector("button, input, select, textarea, details")).toBeNull();
        const ids = [...region.querySelectorAll("[id]")].map(item => item.id); expect(new Set(ids).size).toBe(ids.length);
      }
      expect(target.main.textContent).toContain(state);
      expect(target.main.textContent).toContain("MOCK");
      expect(review.main.textContent).toContain("What will be sent");
      expect(review.main.textContent).toContain("Synthetic review identity");
      expect(review.main.textContent).toContain("Important notes before sending");
      expect(review.main.textContent).toContain("not transmitted to GoldTier");
      expect(container!.querySelectorAll("#case-review-and-send")).toHaveLength(1);
      const sends = [...review.region.querySelectorAll("button")].filter(item => item.textContent?.startsWith("Confirm and send"));
      expect(sends).toHaveLength(state === "NOT_SUBMITTED" ? 1 : 0);
      if (state === "SUBMISSION_OUTCOME_UNCERTAIN") {
        expect(target.main.querySelector("#case-target-recovery")).not.toBeNull();
        expect(target.main.textContent).toContain("Director verification required");
        expect(target.main.textContent).toContain("Repeating an unconfirmed write could create a duplicate");
      }
      expect(fetch.mock.calls.every(([url]) => String(url).endsWith("/target-status-check"))).toBe(true);
      fetch.mockClear();
      act(() => { for (const panel of [...target.support, ...review.support]) { panel.open = true; panel.open = false; } });
      expect(fetch).not.toHaveBeenCalled(); client.clear();
    },
  );
  it("retains Director recovery attestation in Main and ledger diagnostics in Technical", () => {
    const client = setup(targetSummary("SUBMISSION_OUTCOME_UNCERTAIN"), { ...actorA, capabilities: [...actorA.capabilities, "TARGET_RECOVERY"] });
    const { main, support } = partitions("GoldTier submission package");
    expect(main.textContent).toContain("I verified this exact candidate");
    expect(main.querySelector('input[type="checkbox"]')).not.toBeNull();
    expect(main.querySelector("#case-target-recovery details")).toBeNull();
    expect(support[1].textContent).toContain("Ledger state");
    expect(support[1].textContent).toContain("OUTCOME_UNCERTAIN"); client.clear();
  });
  it.each([[false, false], [true, false], [false, true], [true, true]])("prints one complete appendix and restores support %s/%s with zero writes", (moreOpen, technicalOpen) => {
    const fetch = vi.spyOn(globalThis, "fetch"); const print = vi.spyOn(window, "print").mockImplementation(() => undefined);
    const client = setup(); const { main, support, region } = partitions("Final review & send");
    act(() => { support[0].open = moreOpen; support[1].open = technicalOpen; });
    act(() => { window.dispatchEvent(new Event("beforeprint")); });
    expect(support.every(item => item.open)).toBe(true);
    expect(main.textContent).toContain("What will be sent");
    expect(region.textContent!.match(/Vocabulary version:/g)).toHaveLength(1);
    expect(region.querySelectorAll(".review-and-send__technical-content")).toHaveLength(1);
    act(() => { window.dispatchEvent(new Event("beforeprint")); window.dispatchEvent(new Event("afterprint")); });
    expect(support.map(item => item.open)).toEqual([moreOpen, technicalOpen]);
    expect(button("Confirm and send to Mock GoldTier").disabled).toBe(false);
    click("Print / save PDF"); expect(print).toHaveBeenCalledTimes(1); expect(fetch).not.toHaveBeenCalled(); client.clear();
  });
  it.each(["pending-retained", "failed-retained", "recovery"] as const)("qualifies %s target and final projections using the current query owner", async state => {
    const summary = targetSummary(); const client = setup(summary); const key = caseQueryKeys.detail(actorA.user_id, CASE_A);
    let release!: (value: Response) => void; const pending = new Promise<Response>(resolve => { release = resolve; });
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(() => state === "pending-retained" ? pending : Promise.resolve(new Response("", { status: 503 })));
    let refresh: Promise<void> | undefined;
    await act(async () => { refresh = client.invalidateQueries({ queryKey: key, exact: true }); if (state !== "pending-retained") await refresh; });
    if (state === "recovery") { fetch.mockImplementation(async () => response(summary)); await act(async () => { await client.refetchQueries({ queryKey: key, exact: true }); }); }
    await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });
    for (const name of ["GoldTier submission package", "Final review & send"]) {
      const { main, support } = partitions(name);
      for (const panel of [main, ...support]) {
        if (state === "recovery") expect(panel.textContent).not.toContain("Last-confirmed");
        else expect(panel.textContent).toContain("Last-confirmed");
      }
    }
    if (state === "pending-retained") await act(async () => { release(response(summary)); await refresh; });
    client.clear();
  });
  it("keeps preflight failure and safe continuation actions and focus anchors in Main", () => {
    const summary = targetSummary();
    summary.case.initial_identity = { legal_name: "Synthetic preflight identity", registration_number: "202400001A", country_of_incorporation: "SG" };
    summary.clm.target_search_checkpoint = { status: "FAILED", disposition: "FAILED" } as NonNullable<ZeroTouchCaseSummary["clm"]["target_search_checkpoint"]>;
    summary.clm.submission_plan.request_preview!.dispatch_ready = false;
    const client = setup(summary); let target = partitions("GoldTier submission package");
    expect(target.main.textContent).toContain("GoldTier availability check needed");
    expect(target.main.textContent).toContain("No target write was attempted");
    expect(target.main.querySelector("#target-preflight-title")).not.toBeNull();
    expect(button("Check GoldTier availability").closest("details")).toBeNull();
    const continued = targetSummary("FINALIZATION_PENDING"); continued.status = "RECOVERY_PENDING";
    act(() => { client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), continued); }); renderCase(client, actorA, CASE_A);
    target = partitions("GoldTier submission package");
    expect(target.main.querySelector("#target-continuation-title")).not.toBeNull();
    expect(target.main.querySelector("#case-evidence-recovery")).not.toBeNull();
    expect(button("Complete safe recovery").closest("details")).toBeNull();
    expect(target.main.textContent).toContain("Previously completed or verified steps will not be sent again"); client.clear();
  });
  it("ignores an older failed target read after a newer confirmed current read", async () => {
    const frames = new Map<number, FrameRequestCallback>(); let frameId = 0;
    vi.spyOn(globalThis, "requestAnimationFrame").mockImplementation(callback => { const id = ++frameId; frames.set(id, callback); return id; });
    vi.spyOn(globalThis, "cancelAnimationFrame").mockImplementation(id => { frames.delete(id); });
    const client = setup(); const key = caseQueryKeys.detail(actorA.user_id, CASE_A);
    let release!: (value: Response) => void; const old = new Promise<Response>(resolve => { release = resolve; });
    const next = targetSummary("SUBMISSION_CONFIRMED"); next.version = 2;
    const fetch = vi.spyOn(globalThis, "fetch").mockReturnValueOnce(old).mockImplementation(async () => response(next));
    let refresh: Promise<void> | undefined;
    await act(async () => { refresh = client.invalidateQueries({ queryKey: key, exact: true }); await new Promise(resolve => setTimeout(resolve, 0)); });
    const signal = (fetch.mock.calls[0][1] as RequestInit).signal;
    await act(async () => { await client.refetchQueries({ queryKey: key, exact: true }, { cancelRefetch: true, throwOnError: true }); });
    await act(async () => { release(new Response("", { status: 503 })); await refresh; await new Promise(resolve => setTimeout(resolve, 0)); });
    expect(signal?.aborted).toBe(true); expect(client.getQueryState(key)?.status).toBe("success");
    for (const name of ["GoldTier submission package", "Final review & send"]) {
      const { main, support } = partitions(name);
      for (const panel of [main, ...support]) { expect(panel.textContent).not.toContain("information could not be loaded"); expect(panel.textContent).not.toContain("Last-confirmed"); }
    }
    expect(partitions("GoldTier submission package").main.textContent).toContain("SUBMISSION_CONFIRMED");
    const target = document.getElementById("submission-state-title")!;
    expect(target).toBeInstanceOf(HTMLElement);
    expect(frames.size).toBe(1);
    act(() => { for (const callback of frames.values()) callback(16); frames.clear(); });
    expect(document.activeElement).toBe(target);
    expect(scrollIntoView).toHaveBeenCalledExactlyOnceWith({ block: "center", behavior: "auto" });
    expect(scrollIntoView.mock.instances[0]).toBe(target);
    expect([...container!.querySelectorAll("button")].some(item => item.textContent?.startsWith("Confirm and send"))).toBe(false);
    expect(fetch.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true); client.clear();
  });
  it("retires support and late target evidence across case, actor and authenticated session replacement", async () => {
    const client = setup(); const key = caseQueryKeys.detail(actorA.user_id, CASE_A);
    const oldReview = partitions("Final review & send"); act(() => { oldReview.support[0].open = true; oldReview.support[1].open = true; });
    let release!: (value: Response) => void; const old = new Promise<Response>(resolve => { release = resolve; });
    const fetch = vi.spyOn(globalThis, "fetch").mockReturnValue(old); let refresh: Promise<void> | undefined;
    await act(async () => { refresh = client.invalidateQueries({ queryKey: key, exact: true }); await new Promise(resolve => setTimeout(resolve, 0)); });
    const signal = (fetch.mock.calls[0][1] as RequestInit).signal;
    act(() => { root!.unmount(); root = null; clearSessionQueries(client); });
    seedCase(client, actorB, CASE_B, "new-session-analysis", "NEXT");
    const current = targetSummary(); current.case.case_id = CASE_B;
    client.setQueryData(caseQueryKeys.detail(actorB.user_id, CASE_B), current); renderCase(client, actorB, CASE_B);
    const late = targetSummary("SUBMISSION_CONFIRMED"); late.case.requested_uen = "LATE_OLD";
    await act(async () => { release(response(late)); await refresh; await new Promise(resolve => setTimeout(resolve, 0)); });
    expect(signal?.aborted).toBe(true); expect(client.getQueryData(key)).toBeUndefined();
    expect(container!.textContent).not.toContain("LATE_OLD");
    for (const name of ["GoldTier submission package", "Final review & send"]) expect(partitions(name).support.every(item => !item.open)).toBe(true);
    expect(collapsedTargetHeader()).toContain("Submission not started");
    expect(partitions("GoldTier submission package").main.textContent).toContain("NOT_SUBMITTED"); client.clear();
  });

});


describe("Round3 collapsed header read truthfulness", () => {
  const titles = ["Existing-customer search", "Registry verification", "Document verification", "Ownership & UBO", "Submission readiness", "GoldTier submission package", "Final review & send"];
  function header(title: string, collapse = true) {
    const region = [...container!.querySelectorAll<HTMLElement>(".stage-disclosure")].find(item => item.querySelector(":scope > h2")?.textContent === title)!;
    expect(region).toBeTruthy(); const toggle = region.querySelector<HTMLButtonElement>(":scope > h2 button")!;
    if (collapse && toggle.getAttribute("aria-expanded") === "true") act(() => toggle.click());
    const description = region.querySelector<HTMLElement>(":scope > .stage-disclosure__summary")!;
    expect(description).not.toBeNull(); expect(description.closest("[hidden]")).toBeNull(); expect(toggle.getAttribute("aria-describedby")).toBe(description.id);
    if (collapse) { expect(toggle.getAttribute("aria-expanded")).toBe("false"); expect(region.querySelector<HTMLElement>(":scope > div")!.hidden).toBe(true); }
    return { region, toggle, text: description.textContent! };
  }
  function setup(final = false, profile = actorA) {
    const client = createTestClient(); seedCase(client, profile, CASE_A, "analysis-current", "CURRENT");
    const summary = summaryFixture(CASE_A);
    if (final) {
      summary.active_exceptions = [{ ...summary.active_exceptions[0], stage: "MOCK_GOLDTIER", exception_type: "TARGET_CONFIRMATION_REQUIRED", blocker_code: "TARGET_CONFIRMATION_REQUIRED" }];
      summary.clm.readiness.blockers = [];
      summary.clm.submission_plan.request_preview = { environment: "MOCK", dispatch_ready: true, policy_version: 2, operations: [] };
    }
    client.setQueryData(caseQueryKeys.detail(profile.user_id, CASE_A), summary);
    renderCase(client, profile, CASE_A); return { client, summary };
  }
  async function flush() { await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); }); }
  it.each([false, true])("qualifies actual detail refresh failure and recovery in all seven collapsed headers; final=%s", async final => {
    const { client, summary } = setup(final); titles.forEach(title => header(title));
    let release!: (value: Response) => void; const pending = new Promise<Response>(resolve => { release = resolve; });
    const fetch = vi.spyOn(globalThis, "fetch").mockReturnValue(pending); let refresh: Promise<void> | undefined;
    const key = caseQueryKeys.detail(actorA.user_id, CASE_A);
    await act(async () => { refresh = client.invalidateQueries({ queryKey: key, exact: true }); }); await flush();
    for (const title of titles) { const h = header(title, false); expect(h.toggle.getAttribute("aria-expanded")).toBe("false"); expect.soft(h.text).toContain("refresh in progress"); expect.soft(h.text).toContain("Last-confirmed"); }
    await act(async () => { release(new Response("", { status: 503 })); await refresh; }); await flush();
    for (const title of titles) { expect.soft(header(title, false).text).toContain("refresh failed; may be stale"); expect(header(title, false).toggle.getAttribute("aria-expanded")).toBe("false"); }
    fetch.mockImplementation(async () => response(summary)); await act(async () => { await client.refetchQueries({ queryKey: key, exact: true }); }); await flush();
    for (const title of titles) { expect.soft(header(title, false).text).not.toMatch(/Last-confirmed|may be stale|refresh in progress/); expect(header(title, false).toggle.getAttribute("aria-expanded")).toBe("false"); }
    expect(fetch.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true); client.clear();
  });
  it.each(["ownership", "documents"] as const)("qualifies independent %s refresh/failure/recovery in its collapsed header and final", async resource => {
    const { client } = setup(true); const key = caseQueryKeys[resource](actorA.user_id, CASE_A);
    const affected = [resource === "ownership" ? "Ownership & UBO" : "Document verification", "Final review & send"]; affected.forEach(title => header(title));
    let release!: (value: Response) => void; const pending = new Promise<Response>(resolve => { release = resolve; });
    const fetch = vi.spyOn(globalThis, "fetch").mockReturnValue(pending); let refresh: Promise<void> | undefined;
    await act(async () => { refresh = client.invalidateQueries({ queryKey: key, exact: true }); }); await flush();
    for (const title of affected) { expect.soft(header(title, false).text).toContain("refresh in progress"); expect(header(title, false).toggle.getAttribute("aria-expanded")).toBe("false"); }
    await act(async () => { release(new Response("", { status: 503 })); await refresh; }); await flush();
    for (const title of affected) { expect.soft(header(title, false).text).toContain("refresh failed; may be stale"); expect(header(title, false).toggle.getAttribute("aria-expanded")).toBe("false"); }
    fetch.mockImplementation(async () => response(resource === "ownership" ? ownershipFixture(CASE_A, "restored", "FRESH") : [documentFixture(CASE_A)]));
    await act(async () => { await client.refetchQueries({ queryKey: key, exact: true }); }); await flush();
    for (const title of affected) { expect.soft(header(title, false).text).not.toContain("Last-confirmed"); expect(header(title, false).toggle.getAttribute("aria-expanded")).toBe("false"); }
    expect(fetch.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true); client.clear();
  });
  it.each(["ownership", "documents"] as const)("does not claim retained %s during initial loading or failed initial read", async resource => {
    const client = createTestClient(); seedCase(client, actorA, CASE_A, "analysis", "A"); const key = caseQueryKeys[resource](actorA.user_id, CASE_A);
    client.removeQueries({ queryKey: key, exact: true }); let release!: (value: Response) => void; const pending = new Promise<Response>(resolve => { release = resolve; });
    const fetch = vi.spyOn(globalThis, "fetch").mockReturnValue(pending); renderCase(client, actorA, CASE_A);
    const title = resource === "ownership" ? "Ownership & UBO" : "Document verification";
    expect(header(title).text).toContain("Loading"); expect(header(title).text).toContain("not yet confirmed"); expect(header(title).text).not.toContain("Last-confirmed");
    await act(async () => { release(new Response("", { status: 503 })); }); await vi.waitFor(() => expect(client.getQueryState(key)?.status).toBe("error")); await flush();
    expect.soft(header(title, false).text).toContain("Current evidence unavailable; absence not confirmed"); expect.soft(header(title, false).text).not.toContain("Last-confirmed"); expect(header(title, false).toggle.getAttribute("aria-expanded")).toBe("false");
    expect(fetch.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true); client.clear();
  });
  it.each(["ANALYZED", "REVIEW_REQUIRED", "FAILED"] as const)("retains confirmed %s and intervention without granting actions", async state => {
    const profile = { ...actorA, capabilities: [] }; const { client, summary } = setup(false, profile);
    const analysis = ownershipFixture(CASE_A, "analysis", "A"); analysis.state = state; summary.active_exceptions = []; summary.evidence_decision_authorized = false;
    summary.interventions = [{ intervention_id: "owner-review", owning_stage: "OWNERSHIP", owning_stage_label: "Ownership", title: "Review ownership", blocker_code: "OWNERSHIP_REVIEW_REQUIRED", explanation: "Retained ownership review", required_evidence_or_input: [], authorized_actions: [], no_action_reason: "No action is currently authorized", expected_next_step: "Review", candidate_summaries: [] }];
    act(() => { client.setQueryData(caseQueryKeys.ownership(actorA.user_id, CASE_A), analysis); client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), summary); }); await flush();
    const fetch = vi.spyOn(globalThis, "fetch"); const h = header("Ownership & UBO"); expect(h.text).toContain(state.replaceAll("_", " ")); expect(h.text).toContain("Attention required"); expect(h.text).not.toContain("Last-confirmed");
    expect(h.region.querySelector(".intervention-card button")).toBeNull(); expect(fetch).not.toHaveBeenCalled(); client.clear();
  });
  it.each(["INCOMPLETE_LEGAL_ENTITY", "CONTRADICTORY_OWNERSHIP_EVIDENCE"] as const)("exposes %s as requiring attention without an exception action", async code => {
    const { client, summary } = setup(); summary.active_exceptions = []; summary.interventions = [];
    const analysis = ownershipFixture(CASE_A, "analysis", "A"); analysis.state = "REVIEW_REQUIRED"; analysis.issues = [{ code, message: "Synthetic retained analysis requires review", affected_party_ids: [] }];
    act(() => { client.setQueryData(caseQueryKeys.ownership(actorA.user_id, CASE_A), analysis); client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), summary); }); await flush();
    const fetch = vi.spyOn(globalThis, "fetch"); const h = header("Ownership & UBO"); expect(h.text).toContain("REVIEW REQUIRED"); expect(h.text).toContain("Attention required"); expect(h.region.textContent).toContain("Incomplete or disputed evidence requires review."); expect(fetch).not.toHaveBeenCalled(); client.clear();
  });
  it("distinguishes confirmed empty ownership from unavailable ownership", async () => {
    const client = createTestClient(); seedCase(client, actorA, CASE_A, "analysis", "A"); client.removeQueries({ queryKey: caseQueryKeys.ownership(actorA.user_id, CASE_A), exact: true }); client.setQueryData(caseQueryKeys.ownership(actorA.user_id, CASE_A), null); renderCase(client, actorA, CASE_A); await flush();
    expect(header("Ownership & UBO").text).toContain("No ownership analysis retained in the confirmed response"); expect(header("Ownership & UBO").text).not.toContain("unavailable"); client.clear();
  });
  it.each(["SUBMISSION_OUTCOME_UNCERTAIN", "SUBMISSION_CONFIRMED"] as const)("keeps %s and frozen state visible in actual Final Review", async state => {
    const { client, summary } = setup(true); summary.target_submission = { state, submission_id: "00000000-0000-4000-8000-00000000f003", status_check_available: false, recovery_available: false, attempted_operations: ["SEARCH", "SHELL"], definitively_completed_operations: ["SEARCH"], lifecycle_resolved_operations: ["SEARCH"], ledger_state: "OUTCOME_UNCERTAIN" } as NonNullable<ZeroTouchCaseSummary["target_submission"]>;
    if (state === "SUBMISSION_CONFIRMED") summary.status = "COMPLETED"; act(() => client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), summary)); await flush();
    const h = header("Final review & send"); expect(h.text).toContain(state === "SUBMISSION_OUTCOME_UNCERTAIN" ? "Submission outcome uncertain" : "Submission confirmed"); expect(h.text).toContain("frozen");
    expect([...h.region.querySelectorAll("button")].some(item => item.textContent?.startsWith("Confirm and send"))).toBe(false); client.clear();
  });
  it.each(["ownership", "documents", "detail"] as const)("retires late %s header freshness across actor/case/session replacement", async resource => {
    const { client } = setup(true); const key = caseQueryKeys[resource](actorA.user_id, CASE_A);
    let release!: (value: Response) => void; const pending = new Promise<Response>(resolve => { release = resolve; });
    const fetch = vi.spyOn(globalThis, "fetch").mockReturnValue(pending); let refresh: Promise<void> | undefined; titles.forEach(title => header(title));
    await act(async () => { refresh = client.invalidateQueries({ queryKey: key, exact: true }); }); await flush(); const signal = (fetch.mock.calls[0][1] as RequestInit).signal;
    act(() => { root!.unmount(); root = null; clearSessionQueries(client); }); seedCase(client, actorB, CASE_B, "NEW_SESSION", "NEW"); renderCase(client, actorB, CASE_B);
    await act(async () => { release(new Response("", { status: 503 })); await refresh; }); await flush(); expect(signal?.aborted).toBe(true); expect(client.getQueryData(key)).toBeUndefined();
    for (const title of titles) expect(header(title).text).not.toMatch(/Last-confirmed|may be stale|refresh in progress/); expect(container!.textContent).not.toContain("CURRENT Candidate");
    expect(fetch.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true); client.clear();
  });
});
