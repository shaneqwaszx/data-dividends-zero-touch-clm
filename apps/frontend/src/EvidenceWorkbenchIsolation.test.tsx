// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { caseQueryKeys } from "./caseQueries";
import CaseDetail from "./pages/CaseDetail";
import { createSessionQueryClient } from "./queryClient";
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
    },
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
  return {
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
  it("keeps candidate, retained-path, and explanation exploration local and read only", () => {
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

    expect(document.activeElement?.id).toBe("case-evidence-documents");
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(storageSet).not.toHaveBeenCalled();
    expect(storageRemove).not.toHaveBeenCalled();
    expect(storageClear).not.toHaveBeenCalled();
  });

  it("reports a missing fixed evidence destination without issuing a request", () => {
    const client = createTestClient();
    seedCase(client, actorA, CASE_A, "analysis-a", "a");
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    renderCase(client, actorA, CASE_A);
    click("Focus evidence for DOCUMENT_SOURCE_CONFLICT");

    expect(container?.textContent).toContain("reconciliation evidence is not available for this case.");
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("clears focused evidence and its notice synchronously across case and actor identities", () => {
    const client = createTestClient();
    seedCase(client, actorA, CASE_A, "analysis-a", "a");
    seedCase(client, actorA, CASE_B, "analysis-b", "b");
    seedCase(client, actorB, CASE_B, "analysis-c", "c");
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    renderCase(client, actorA, CASE_A);
    click("Focus documents evidence");
    const caseADocuments = document.activeElement;
    expect(caseADocuments?.id).toBe("case-evidence-documents");
    click("Focus evidence for DOCUMENT_SOURCE_CONFLICT");
    expect(container?.textContent).toContain("reconciliation evidence is not available for this case.");

    renderCase(client, actorA, CASE_B);
    expect(caseADocuments?.isConnected).toBe(false);
    expect(document.activeElement?.id).not.toBe("case-evidence-documents");
    expect(container?.textContent).not.toContain("reconciliation evidence is not available for this case.");

    click("Focus documents evidence");
    const actorADocuments = document.activeElement;
    expect(actorADocuments?.id).toBe("case-evidence-documents");
    click("Focus evidence for DOCUMENT_SOURCE_CONFLICT");

    renderCase(client, actorB, CASE_B);
    expect(actorADocuments?.isConnected).toBe(false);
    expect(document.activeElement?.id).not.toBe("case-evidence-documents");
    expect(container?.textContent).not.toContain("reconciliation evidence is not available for this case.");
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

    await clickAndFlush("Accept legal name suggestion");
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
      "Registry identity", "Documents & reconciliation", "Ownership & UBO",
      "Classification & readiness", "Target preparation / submission state",
      "Historical / resolved issues", "Review & Send",
    ]);
    expect(sections[1].querySelector("button")?.getAttribute("aria-expanded")).toBe("true");
    expect(sections[5].querySelector("button")?.getAttribute("aria-expanded")).toBe("false");
    expect(sections[6].querySelector("button")?.getAttribute("aria-expanded")).toBe("false");
    expect(sections[6].textContent).toContain("Not yet available");
    expect(sections[6].querySelector(".review-and-send")).toBeNull();
  });
});
