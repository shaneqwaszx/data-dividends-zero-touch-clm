// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { caseQueryKeys } from "../caseQueries";
import type { AuthenticatedProfile, HumanInterventionProjection, ZeroTouchCaseSummary, ZeroTouchException } from "../types";
import CaseDetail from "./CaseDetail";
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


let root: Root;
let container: HTMLDivElement;
let client: QueryClient;
beforeEach(() => {
  container = document.createElement("div"); document.body.append(container); root = createRoot(container);
  client = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity, gcTime: Infinity, retry: false }, mutations: { retry: false } } });
});
afterEach(() => { act(() => root.unmount()); client.clear(); container.remove(); vi.restoreAllMocks(); });
function seed(value: ZeroTouchCaseSummary, actor = actorA) {
  client.setQueryData(caseQueryKeys.detail(actor.user_id, value.case.case_id), value);
  client.setQueryData(caseQueryKeys.documents(actor.user_id, value.case.case_id), []);
  client.setQueryData(caseQueryKeys.ownership(actor.user_id, value.case.case_id), null);
  client.setQueryData(caseQueryKeys.intelligence(actor.user_id, value.case.case_id), null);
}
function render(caseId = CASE_A, actor = actorA) {
  act(() => root.render(<QueryClientProvider client={client}><CaseDetail caseId={caseId} actor={actor}
    onBack={() => undefined} onViewOnboarded={() => undefined} onViewAudit={() => undefined} /></QueryClientProvider>));
}
function stage(title: string): HTMLElement {
  const heading = [...container.querySelectorAll("h2")].find(item => item.textContent?.replace(/[−+]$/, "") === title);
  expect(heading, `Missing workspace heading: ${title}`).toBeTruthy(); return heading!.closest("section")!;
}
function button(label: string, scope: ParentNode = container): HTMLButtonElement {
  const control = [...scope.querySelectorAll<HTMLButtonElement>("button")].find(item => item.textContent === label);
  expect(control, `Missing button: ${label}`).toBeTruthy(); return control!;
}
function projection(owner: "REGISTRY" | "GOLDTIER_SEARCH", id: string = owner): HumanInterventionProjection {
  return { intervention_id: id, owning_stage: owner, owning_stage_label: owner, title: `${owner} issue`,
    blocker_code: owner === "REGISTRY" ? "INITIAL_IDENTITY_INCOMPLETE" : "GT_SEARCH_IDENTITY_REVIEW_REQUIRED", explanation: "Synthetic retained issue", required_evidence_or_input: [],
    authorized_actions: [], candidate_summaries: [], no_action_reason: null, expected_next_step: "Review identity",
    evidence_actions: [{ target: "IDENTITY", label: `${owner} identity action` }] };
}
function searchFixture(): ZeroTouchCaseSummary {
  const value = summaryFixture(CASE_A); value.current_stage = "GOLDTIER_SEARCH"; value.active_exceptions = [];
  value.interventions = [projection("GOLDTIER_SEARCH")]; value.case.requested_uen = "202400001A";
  value.case.initial_identity = { legal_name: "Synthetic entity", registration_number: "202400001A", country_of_incorporation: "SG" } as NonNullable<ZeroTouchCaseSummary["case"]["initial_identity"]>;
  value.case.error = { code: "INITIAL_IDENTITY_INCOMPLETE", message: "Identity required" };
  value.clm.version = 4;
  value.clm.target_search_checkpoint = { status: "REVIEW_REQUIRED", request_id: "search-request-a" } as NonNullable<ZeroTouchCaseSummary["clm"]["target_search_checkpoint"]>;
  value.processing_pipeline = [{ node_id: "GOLDTIER_SEARCH", label: "Existing-customer search", status: "REVIEW_REQUIRED", children: [] }];
  return value;
}
describe("AM-03 Search workspace ownership", () => {
  it("places Search-owned action beneath Existing-customer search rather than Registry", () => {
    seed(searchFixture()); render();
    expect(stage("Existing-customer search").querySelector("#case-intervention-GOLDTIER_SEARCH")).not.toBeNull();
    expect(stage("Registry verification").querySelector("#case-intervention-GOLDTIER_SEARCH")).toBeNull();
  });
  it("keeps Registry-owned actions and provenance beneath Registry", () => {
    const value = searchFixture(); value.interventions = [projection("REGISTRY")]; seed(value); render();
    expect(stage("Registry verification").querySelector("#case-intervention-REGISTRY")).not.toBeNull();
    expect(stage("Registry verification").querySelector("#case-evidence-registry")).not.toBeNull();
    expect(stage("Existing-customer search").querySelector("#case-intervention-REGISTRY")).toBeNull();
  });
  it("retains both stages' actions with exactly one mutable identity editor", () => {
    const value = searchFixture(); value.interventions = [projection("REGISTRY"), projection("GOLDTIER_SEARCH")]; seed(value); render();
    expect(button("REGISTRY identity action", stage("Registry verification"))).toBeTruthy();
    expect(button("GOLDTIER_SEARCH identity action", stage("Existing-customer search"))).toBeTruthy();
    expect(container.querySelectorAll("#case-identity-correction")).toHaveLength(1);
    expect(stage("Registry verification").querySelector("#case-identity-correction")).not.toBeNull();
  });
});

function exception(owner: "REGISTRY" | "GOLDTIER_SEARCH", code = owner === "REGISTRY" ? "INITIAL_IDENTITY_INCOMPLETE" : "GT_SEARCH_IDENTITY_REVIEW_REQUIRED"): ZeroTouchException {
  return { ...summaryFixture(CASE_A).active_exceptions[0], exception_id: owner, stage: owner,
    blocker_code: code, blocker_codes: [code] };
}
function fetchEvidence(value: ZeroTouchCaseSummary) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async input => {
    const url = String(input);
    const result = url.endsWith("/documents") ? [] : url.endsWith("/ownership") || url.endsWith("/intelligence") ? null : value;
    return new Response(JSON.stringify(result), { status: 200, headers: { "Content-Type": "application/json" } });
  });
}
function setInput(input: HTMLInputElement, value: string) {
  act(() => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true })); });
}
function mutationCalls(fetchSpy: { mock: { calls: Array<Parameters<typeof fetch>> } }) {
  return fetchSpy.mock.calls.filter(([, init]) => init?.method && init.method !== "GET");
}

describe("AM-03 action and adverse paths", () => {
  it.each(["Search", "Registry"] as const)("preserves the %s correction endpoint and expected versions", async mode => {
    const value = searchFixture();
    if (mode === "Registry") { value.active_exceptions = [exception("REGISTRY", "ACRA_ENTITY_NOT_FOUND")];
      value.interventions = [projection("REGISTRY")]; }
    if (mode === "Search") value.interventions = [projection("REGISTRY")];
    seed(value); render();
    if (mode === "Registry") act(() => button("Edit UEN").click());
    const updated = { ...value, version: 2 }; const fetchSpy = fetchEvidence(updated);
    const form = container.querySelector<HTMLFormElement>("#case-identity-correction form")!;
    await act(async () => { form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })); });
    await vi.waitFor(() => expect(mutationCalls(fetchSpy)).toHaveLength(1));
    const [url, init] = mutationCalls(fetchSpy)[0];
    expect(String(url)).toBe(`/api/clm/zero-touch/cases/${CASE_A}/${mode === "Search" ? "identity-search-recheck" : "registry-identity"}`);
    expect(JSON.parse(init!.body as string)).toEqual({ legal_name: "Synthetic entity", registration_number: "202400001A",
      country_of_incorporation: "SG", expected_automation_version: 1, expected_clm_version: 4, expected_case_event_count: 1,
      ...(mode === "Registry" ? { choice: "OTHER" } : {}) });
  });
  it.each(["ACRA_ENTITY_NOT_FOUND", "REGISTRY_IDENTIFIER_NOT_ELIGIBLE", "REGISTRY_RECHECK_INCOMPLETE", "INITIAL_IDENTITY_NOT_ELIGIBLE"])(
    "retains Registry correction for wrong-UEN path %s despite Search and missing-identity projections", code => {
      const value = searchFixture(); value.active_exceptions = [exception("REGISTRY", code)];
      value.interventions = [projection("GOLDTIER_SEARCH"), projection("REGISTRY")]; seed(value); render();
      expect(stage("Registry verification").querySelector("#case-identity-correction")).not.toBeNull();
      expect(stage("Existing-customer search").querySelector("#case-identity-correction")).toBeNull();
      act(() => button("Edit UEN").click()); expect(button("Verify UEN and resume")).toBeTruthy();
      expect(container.textContent).not.toContain("Save details and recheck Search");
    });
  it("makes Registry-owned Search recheck reachable from Search without a duplicate form", async () => {
    const value = searchFixture(); value.interventions = [projection("REGISTRY")]; seed(value); render();
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    act(() => button("Review identity for Search recheck", stage("Existing-customer search")).click());
    await vi.waitFor(() => expect(document.activeElement?.id).toBe("identity-registration-number"));
    expect(hiddenByDisclosure(container.querySelector("#case-identity-correction"))).toBe(false);
    expect(container.querySelectorAll("#case-identity-correction")).toHaveLength(1); expect(fetchSpy).not.toHaveBeenCalled();
  });
  it("retains EXISTING_REUSED candidate identity, confirmation rationale and one confirmation call", async () => {
    const value = searchFixture(); value.active_exceptions = [exception("GOLDTIER_SEARCH", "GOLDTIER_EXISTING_CUSTOMER")];
    value.interventions = [{ ...projection("GOLDTIER_SEARCH"), blocker_code: "GOLDTIER_EXISTING_CUSTOMER", evidence_actions: [],
      candidate_summaries: [{ party_id: "synthetic-target-id", legal_name: "Synthetic entity", registration_number: "202400001A", country: "SG", legal_form: "CORPORATE" }],
      existing_customer_confirmation_action: "CONFIRM_EXISTING_GOLDTIER_CUSTOMER" }];
    value.target_submission = { submission_id: null, state: "NOT_SUBMITTED", goldtier_id: "synthetic-target-id",
      status_check_available: false, customer_handling: "EXISTING_REUSED" };
    value.clm.target_search_checkpoint!.selected_party_id = "synthetic-target-id";
    seed(value); render();
    expect(stage("Existing-customer search").textContent).toContain("synthetic-target-id");
    const rationale = stage("Existing-customer search").querySelector<HTMLInputElement>("#existing-customer-confirmation-rationale")!;
    expect(rationale).toBeTruthy(); expect(button("Confirm existing GoldTier customer").disabled).toBe(true);
    setInput(rationale, "Compared retained synthetic identity");
    const fetchSpy = fetchEvidence({ ...value, version: 2 });
    await act(async () => { rationale.form!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })); });
    await vi.waitFor(() => expect(mutationCalls(fetchSpy)).toHaveLength(1));
    const [url, init] = mutationCalls(fetchSpy)[0];
    expect(String(url)).toBe(`/api/clm/zero-touch/cases/${CASE_A}/confirm-existing-customer`);
    expect(JSON.parse(init!.body as string)).toEqual({ search_request_id: "search-request-a", expected_automation_version: 1,
      expected_clm_version: 4, expected_case_event_count: 1, rationale: "Compared retained synthetic identity" });
    expect(value.interventions[0].candidate_summaries[0].party_id).toBe("synthetic-target-id");
  });
  it.each(["attention", "pipeline", "direct"] as const)("focuses the live Search action through %s without mutation", async navigation => {
    const value = searchFixture(); value.active_exceptions = [exception("GOLDTIER_SEARCH")]; seed(value); render();
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const control = navigation === "attention" ? container.querySelector<HTMLButtonElement>(".case-attention button")!
      : navigation === "pipeline" ? container.querySelector<HTMLButtonElement>('.ds-stage[data-node-id="GOLDTIER_SEARCH"] button')!
      : button("GOLDTIER_SEARCH identity action", stage("Existing-customer search"));
    act(() => control.click());
    await vi.waitFor(() => expect(document.activeElement?.id).toBe("identity-registration-number"));
    expect(document.activeElement?.closest(".stage-disclosure")).toBe(stage("Existing-customer search"));
    expect(document.activeElement?.closest("[hidden]")).toBeNull(); expect(fetchSpy).not.toHaveBeenCalled();
  });
  it("does not expose usable Search controls when backend authority denies them", async () => {
    const value = searchFixture(); value.evidence_decision_authorized = false; seed(value); render();
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    expect(button("GOLDTIER_SEARCH identity action", stage("Existing-customer search")).disabled).toBe(true);
    expect(container.querySelector("#case-identity-correction")).toBeNull();
    act(() => container.querySelector<HTMLButtonElement>(".case-attention button")!.click());
    await vi.waitFor(() => expect(container.textContent).toContain("The required action is not available for the current case evidence"));
    expect(document.activeElement?.id).not.toBe("identity-registration-number"); expect(fetchSpy).not.toHaveBeenCalled();
  });
  it.each(["missing", "FAILED", "COMPLETED"] as const)("states retained %s evidence without inventing a match or required Search input", status => {
    const value = searchFixture(); value.interventions = []; value.case.error = null;
    if (status === "missing") value.clm.target_search_checkpoint = null;
    else value.clm.target_search_checkpoint!.status = status;
    seed(value); render(); const section = stage("Existing-customer search");
    expect(section.textContent).toContain(status === "missing" ? "No Search result is retained" : `Retained Search status: ${status}`);
    expect(section.querySelector("input[required]")).toBeNull(); expect(section.textContent).not.toContain("No match");
    expect(section.querySelector("#case-identity-correction")).toBeNull();
  });
  it("shows a completed case without false Search or identity requirements", () => {
    const value = searchFixture(); value.status = "COMPLETED"; value.interventions = []; value.case.error = null;
    seed(value); render(); expect(stage("Existing-customer search").querySelector("input")).toBeNull();
    expect(container.querySelector("#case-identity-correction")).toBeNull();
  });
  it.each(["case", "actor", "version"] as const)("cancels deferred Search attention when %s changes", async change => {
    const value = searchFixture(); value.active_exceptions = [exception("GOLDTIER_SEARCH")]; seed(value);
    const other = { ...searchFixture(), case: { ...value.case, case_id: CASE_B }, automation_id: "other-automation" };
    seed(other); seed(value, actorB);
    client.removeQueries({ queryKey: caseQueryKeys.documents(actorA.user_id, CASE_A), exact: true });
    let release!: (value: Response) => void;
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise<Response>(resolve => { release = resolve; }));
    render(); act(() => container.querySelector<HTMLButtonElement>(".case-attention button")!.click());
    if (change === "case") render(CASE_B); else if (change === "actor") render(CASE_A, actorB);
    else await act(async () => { client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), { ...value, version: 2 }); });
    await act(async () => { release(new Response("[]", { status: 200 })); });
    expect(document.activeElement?.id).not.toBe("identity-registration-number"); expect(mutationCalls(fetchSpy)).toHaveLength(0);
  });
  it("retains same-case Search placement after refresh and ignores a late old-case response", async () => {
    const value = searchFixture(); seed(value); const other = { ...searchFixture(), case: { ...value.case, case_id: CASE_B, entity: { ...value.case.entity!, legal_name: "OTHER SYNTHETIC CASE" } } }; seed(other);
    render(); let release!: (value: Response) => void;
    vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise<Response>(resolve => { release = resolve; }));
    const old = client.refetchQueries({ queryKey: caseQueryKeys.detail(actorA.user_id, CASE_A), exact: true });
    await act(async () => { client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), { ...value, version: 2 }); });
    expect(stage("Existing-customer search").querySelector("#case-intervention-GOLDTIER_SEARCH")).not.toBeNull();
    expect(client.getQueryData<ZeroTouchCaseSummary>(caseQueryKeys.detail(actorA.user_id, CASE_A))!.version).toBe(2);
    render(CASE_B); await act(async () => { release(new Response(JSON.stringify(value), { status: 200 })); await old; });
    expect(container.querySelector("h1")!.textContent).toBe(other.case.entity!.legal_name);
    expect(container.querySelector("#case-identity-correction")).not.toBeNull();
    expect(document.activeElement?.id).not.toBe("identity-registration-number");
  });
});

describe("AM-03 retained failed-Search correction", () => {
  it("preserves the pipeline's live Registry correction for failed Search", async () => {
    const value = searchFixture(); value.interventions = []; value.case.error = null;
    value.clm.target_search_checkpoint!.status = "FAILED";
    seed(value); render(); const fetchSpy = vi.spyOn(globalThis, "fetch");
    act(() => container.querySelector<HTMLButtonElement>('.ds-stage[data-node-id="GOLDTIER_SEARCH"] button')!.click());
    await vi.waitFor(() => expect(document.activeElement?.id).toBe("identity-registration-number"));
    expect(button("Verify UEN and resume")).toBeTruthy(); expect(fetchSpy).not.toHaveBeenCalled();
  });
});

// Wave 2 tests describe caller composition; native visibility is additionally checked in Chromium.
function hiddenByDisclosure(element: Element | null): boolean {
  for (let item = element; item; item = item.parentElement) {
    if (item.hasAttribute("hidden")) return true;
    if (item instanceof HTMLDetailsElement && !item.open && element !== item.querySelector("summary")) return true;
  }
  return false;
}
function optional(title: string, kind: "More" | "Technical"): HTMLDetailsElement {
  const result = [...stage(title).querySelectorAll<HTMLDetailsElement>(":scope > details")]
    .find(item => item.querySelector("summary")?.textContent === `${kind} details — ${title}`);
  expect(result, `${kind} slot missing for ${title}`).toBeTruthy(); return result!;
}

describe("Search and Registry persistent disclosure migration", () => {
  it("keeps both Main workspaces and one correction visible with all optional support closed", () => {
    const value = searchFixture(); value.interventions = [projection("REGISTRY"), projection("GOLDTIER_SEARCH")];
    seed(value); render();
    for (const title of ["Registry verification", "Existing-customer search"]) {
      expect(stage(title).querySelector(":scope > h2 > button")).not.toBeNull();
      expect(optional(title, "More").open).toBe(false); expect(optional(title, "Technical").open).toBe(false);
    }
    expect(hiddenByDisclosure(container.querySelector("#case-identity-correction"))).toBe(false);
    expect(hiddenByDisclosure(container.querySelector("#case-intervention-REGISTRY"))).toBe(false);
    expect(hiddenByDisclosure(container.querySelector("#case-intervention-GOLDTIER_SEARCH"))).toBe(false);
    expect(container.querySelectorAll("#case-identity-correction")).toHaveLength(1);
    expect(hiddenByDisclosure(stage("Registry verification").querySelector(".case-corporate-evidence"))).toBe(true);
  });
  it("toggles independently, keeps same-scope support state and inputs on refresh, and resets on case replacement", () => {
    const value = searchFixture(); seed(value); render();
    const more = optional("Existing-customer search", "More");
    const technical = optional("Registry verification", "Technical");
    more.open = true; technical.open = true;
    act(() => button("Edit UEN").click());
    const input = container.querySelector<HTMLInputElement>("#identity-registration-number")!;
    setInput(input, "202400002B");
    act(() => client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), { ...value }));
    expect(optional("Existing-customer search", "More").open).toBe(true);
    expect(optional("Registry verification", "Technical").open).toBe(true);
    expect(optional("Existing-customer search", "Technical").open).toBe(false);
    expect(input.value).toBe("202400002B");
    const next = { ...searchFixture(), case: { ...searchFixture().case, case_id: CASE_B } }; seed(next); render(CASE_B);
    expect(optional("Existing-customer search", "More").open).toBe(false);
    expect(optional("Registry verification", "Technical").open).toBe(false);
  });
  it("keeps failed Search warning Main while placing its single diagnostic and checkpoint references in Technical", () => {
    const value = searchFixture(); value.clm.target_search_checkpoint!.status = "FAILED";
    value.processing_pipeline![0].status = "FAILED"; seed(value); render();
    const main = stage("Existing-customer search").querySelector(":scope > div")!;
    expect(main.textContent).toContain("A failed Search does not prove that the customer is absent");
    expect(hiddenByDisclosure(main)).toBe(false);
    const technical = optional("Existing-customer search", "Technical");
    expect(technical.querySelector("#case-search-diagnostic")).not.toBeNull();
    expect(technical.textContent).toContain("search-request-a");
    expect(container.querySelectorAll("#case-search-diagnostic")).toHaveLength(1);
    expect(main.textContent).not.toContain("NO_MATCH");
  });
  it("keeps truthful absence in Main and never invents a Search record", () => {
    const value = searchFixture(); value.clm.target_search_checkpoint = null; value.interventions = [];
    seed(value); render();
    const main = stage("Existing-customer search").querySelector(":scope > div")!;
    expect(main.textContent).toContain("No Search result is retained for this case.");
    expect(main.textContent).not.toMatch(/NO_MATCH|CONFIRMED_EXISTING/);
    expect(optional("Existing-customer search", "More").textContent).not.toMatch(/NO_MATCH|CONFIRMED_EXISTING/);
  });
});

it("retires candidate drafts on a new retained request while preserving them on ordinary refresh and support toggles", async () => {
  const value = searchFixture();
  value.interventions = [{ ...projection("GOLDTIER_SEARCH"), evidence_actions: [],
    candidate_summaries: [{ party_id: "synthetic-target-id", legal_name: "Synthetic entity", registration_number: "202400001A", country: "SG", legal_form: "CORPORATE" }],
    existing_customer_confirmation_action: "CONFIRM_EXISTING_GOLDTIER_CUSTOMER" }];
  seed(value); render();
  const input = container.querySelector<HTMLInputElement>("#existing-customer-confirmation-rationale")!;
  expect(hiddenByDisclosure(input)).toBe(false); setInput(input, "Retained comparison draft");
  optional("Existing-customer search", "More").open = true;
  optional("Existing-customer search", "Technical").open = true;
  act(() => client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), { ...value }));
  expect(container.querySelector<HTMLInputElement>("#existing-customer-confirmation-rationale")!.value).toBe("Retained comparison draft");
  expect(hiddenByDisclosure(input)).toBe(false);
  act(() => client.setQueryData(caseQueryKeys.detail(actorA.user_id, CASE_A), { ...value,
    clm: { ...value.clm, target_search_checkpoint: { ...value.clm.target_search_checkpoint!, request_id: "replacement-request" } } }));
  await vi.waitFor(() => expect(container.querySelector<HTMLInputElement>("#existing-customer-confirmation-rationale")!.value).toBe(""));
  expect(optional("Existing-customer search", "More").open).toBe(false);
  expect(optional("Existing-customer search", "Technical").open).toBe(false);
});
it("does not introduce hidden raw checkpoint/provider fields into either disclosure DOM", () => {
  const value = searchFixture();
  Object.assign(value.clm.target_search_checkpoint!, { raw_provider_body: "FORBIDDEN_SYNTHETIC_BODY", private_exception: "FORBIDDEN_SYNTHETIC_ERROR" });
  seed(value); render();
  for (const title of ["Registry verification", "Existing-customer search"]) {
    optional(title, "More").open = true; optional(title, "Technical").open = true;
  }
  expect(container.textContent).not.toContain("FORBIDDEN_SYNTHETIC");
});


it("reopens collapsed Search and focuses its named fallback when no corrective input is authorized", async () => {
  const value = summaryFixture(CASE_A); value.current_stage = "GOLDTIER_SEARCH";
  value.active_exceptions = [exception("GOLDTIER_SEARCH", "GT_SEARCH_REVIEW_REQUIRED")];
  value.interventions = []; value.evidence_decision_authorized = false; value.case.error = null;
  value.clm.target_search_checkpoint = null; seed(value); render();
  const fetchSpy = vi.spyOn(globalThis, "fetch");
  const parent = stage("Existing-customer search").querySelector<HTMLButtonElement>("h2 button")!;
  act(() => parent.click()); expect(parent.getAttribute("aria-expanded")).toBe("false");
  act(() => button("Blocker: GT SEARCH REVIEW REQUIRED").click());
  await vi.waitFor(() => expect(document.activeElement?.id).toBe("case-existing-customer-search"));
  expect(parent.getAttribute("aria-expanded")).toBe("true");
  expect(container.textContent).toContain("No corrective input is currently authorized here.");
  expect(fetchSpy).not.toHaveBeenCalled();
});
