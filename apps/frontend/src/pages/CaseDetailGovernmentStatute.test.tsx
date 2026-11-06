// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as api from "../api";
import { caseQueryKeys } from "../caseQueries";
import type { AuthenticatedProfile, ZeroTouchCaseSummary } from "../types";
import CaseDetail from "./CaseDetail";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
HTMLElement.prototype.scrollIntoView ??= () => undefined;
const NOW = "2026-11-06T01:00:00Z";
const CASE_ID = "00000000-0000-4000-8000-000000001250";
const DOCUMENT_ID = "00000000-0000-4000-8000-000000001251";
const FOUNDING = "Demo Parks FYP Test Authority Act (fictional FYP test instrument)";
const actor: AuthenticatedProfile = {
  user_id: "ethan-tan", display_name: "Ethan Tan", role: "RELATIONSHIP_MANAGER",
  team_id: "TEAM_A", team_display_name: "Synthetic Team", team_type: "CLIENT",
  team_description: "Synthetic test scope", client_scope_label: "Synthetic", capabilities: ["CASE_ACCESS"],
} as AuthenticatedProfile;

function governmentCase(): ZeroTouchCaseSummary {
  return {
    version: 5, automation_id: "synthetic-automation", status: "AWAITING_HUMAN", current_stage: "OWNERSHIP",
    completed_stages: ["REGISTRY", "DOCUMENT"], active_exceptions: [], historical_exceptions: [],
    non_blocking_decisions: [], interventions: [], reconciliation: null, technical_failure: null, target_submission: null,
    evidence_decision_authorized: false, ownership_edit_authorized: true,
    entity_type_basis: {
      entity_type: "GOVERNMENT", label: "Singapore Government entity (government register).", partnership_state: null,
      government_status: {
        state: "CONFIRMATION_REQUIRED", document_id: DOCUMENT_ID, document_event_count: 3,
        founding_instrument: FOUNDING, confirmed_by_actor_id: null, confirmed_at: null,
      },
    },
    case: {
      case_id: CASE_ID, requested_uen: "T99GB0105G", team_id: "TEAM_A", client_scope_label: "Synthetic", priority: null,
      initial_identity: null, entity: null, events: [], registry_acquisition: null, jurisdiction_resolution: null,
      goldtier_result: null, target_dispatch_confirmation: null,
    },
    clm: {
      version: 2, status: "DRAFT", submission: null,
      submission_plan: { environment: "SANDBOX", provider_classification: "SANDBOX_PARTIAL", base_operations: [], real_ready_for_approval: "NOT_AVAILABLE", request_preview: null },
      target_search_checkpoint: null,
      readiness: { registry: { status: "READY" }, document: { status: "READY" }, ownership: { status: "BLOCKED" }, goldtier: { status: "NOT_SUBMITTED" }, blockers: [], warnings: [] },
    },
    classification_consistency: { status: "COMPATIBLE", title: "Consistent", explanation: "Consistent", blocking: false, authority: "PROJECT_ADVISORY_ONLY" },
    target_operations: [], processing_pipeline: [], timeline: [],
    metrics: { automated_stages_completed: 2, human_interventions: 0, exceptions_raised: 0, exceptions_resolved: 0, final_outcome: null, total_duration_ms: null, stage_durations_ms: {} },
    timing: { observed_at: NOW, case_elapsed_ms: 0, time_since_last_update_ms: 0, automation_elapsed_ms: null, recorded_total_duration_ms: null },
    created_at: NOW, updated_at: NOW,
  } as unknown as ZeroTouchCaseSummary;
}

let host: HTMLDivElement | null = null;
let root: Root | null = null;
let client: QueryClient | null = null;
afterEach(async () => {
  if (root) await act(async () => root!.unmount());
  host?.remove(); client?.clear(); root = null; host = null; client = null;
  vi.restoreAllMocks(); vi.unstubAllGlobals();
});

async function mount(summary: ZeroTouchCaseSummary) {
  // The 409 path re-reads case evidence; serve the unchanged case so no other banner appears.
  vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("unexpected network call"))));
  vi.spyOn(api, "fetchZeroTouchCase").mockResolvedValue(summary);
  vi.spyOn(api, "fetchDocuments").mockResolvedValue([]);
  vi.spyOn(api, "fetchOwnership").mockResolvedValue(null as never);
  vi.spyOn(api, "fetchIntelligence").mockResolvedValue(null as never);
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
  client = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity, retry: false }, mutations: { retry: false } } });
  client.setQueryData(caseQueryKeys.detail(actor.user_id, CASE_ID), summary);
  client.setQueryData(caseQueryKeys.documents(actor.user_id, CASE_ID), []);
  client.setQueryData(caseQueryKeys.ownership(actor.user_id, CASE_ID), null);
  client.setQueryData(caseQueryKeys.intelligence(actor.user_id, CASE_ID), null);
  await act(async () => root!.render(<QueryClientProvider client={client!}>
    <CaseDetail caseId={CASE_ID} actor={actor} onBack={() => undefined} onViewAudit={() => undefined} />
  </QueryClientProvider>));
}

function setValue(input: HTMLInputElement, value: string) {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
  setter.call(input, value);
  input.dispatchEvent(new Event("input", { bubbles: true }));
}

async function submitStatute(statute: string) {
  const form = host!.querySelector<HTMLFormElement>('form[aria-label="Confirm Government status"]');
  expect(form).not.toBeNull();
  await act(async () => {
    setValue(form!.querySelector<HTMLInputElement>('input[name="founding_statute"]')!, statute);
    form!.querySelector<HTMLInputElement>('input[type="radio"][value="STATUTORY_BOARD"]')!.click();
  });
  await act(async () => {
    form!.querySelector<HTMLButtonElement>('button[type="submit"]')!.click();
  });
  await act(async () => { await new Promise<void>((resolve) => setTimeout(resolve, 0)); });
}

function pageBanners(): string[] {
  // The CaseDetail page banner is a warn banner outside the Government panel.
  return Array.from(host!.querySelectorAll<HTMLElement>(".ds-banner-warn"))
    .filter((banner) => !banner.closest('section[aria-labelledby="government-status-title"]'))
    .map((banner) => banner.textContent ?? "");
}

describe("D-125 CaseDetail page banner for a Government statute mismatch", () => {
  it("shows a statute mismatch only inline, keeping the RM's input, with no page banner", async () => {
    const summary = governmentCase();
    const confirm = vi.spyOn(api, "confirmGovernmentStatus").mockRejectedValue(new api.ApiError(
      "The statute entered does not match the Founding Instrument on the reviewed document.", 409, "GOVERNMENT_STATUTE_MISMATCH",
    ));
    await mount(summary);
    await submitStatute("Some Other Act");

    expect(confirm).toHaveBeenCalledTimes(1);
    expect(confirm.mock.calls[0][1]).toMatchObject({ founding_statute: "Some Other Act", government_body_type: "STATUTORY_BOARD" });
    const inline = host!.querySelector('section[aria-labelledby="government-status-title"] [role="alert"]');
    expect(inline?.textContent).toContain(`on the reviewed document: "${FOUNDING}". Check the document`);
    expect(host!.querySelector<HTMLInputElement>('input[name="founding_statute"]')!.value).toBe("Some Other Act");
    expect(pageBanners()).toEqual([]);
    expect(host!.textContent).not.toContain("The statute entered does not match");
  });

  it("still shows every other Government confirmation error in the page banner", async () => {
    const summary = governmentCase();
    vi.spyOn(api, "confirmGovernmentStatus").mockRejectedValue(new api.ApiError(
      "Current reviewed Government status evidence is required.", 409, "ZERO_TOUCH_GOVERNMENT_STATUS_EVIDENCE_REQUIRED",
    ));
    await mount(summary);
    await submitStatute("Demo Parks FYP Test Authority Act");

    expect(pageBanners()).toEqual(["Current reviewed Government status evidence is required."]);
    expect(host!.querySelector('section[aria-labelledby="government-status-title"] [role="alert"]')).toBeNull();
  });

  it("Continue onboarding calls the existing resume with the case's concurrency context", async () => {
    const summary = governmentCase();
    summary.entity_type_basis!.government_status!.resume_required = true;
    const resume = vi.spyOn(api, "resumeZeroTouchCase").mockResolvedValue(summary);
    const confirm = vi.spyOn(api, "confirmGovernmentStatus");
    await mount(summary);
    expect(host!.querySelector('form[aria-label="Confirm Government status"]')).toBeNull();
    const button = Array.from(host!.querySelectorAll("button")).find((item) => item.textContent === "Continue onboarding")!;
    await act(async () => { button.click(); });
    await act(async () => { await new Promise<void>((resolve) => setTimeout(resolve, 0)); });
    expect(resume).toHaveBeenCalledTimes(1);
    expect(resume.mock.calls[0][0]).toBe(CASE_ID);
    expect(resume.mock.calls[0][1]).toMatchObject({ automation_id: summary.automation_id, version: summary.version });
    expect(confirm).not.toHaveBeenCalled();
  });
});
