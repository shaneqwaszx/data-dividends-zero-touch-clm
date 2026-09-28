// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { configureAuthenticatedTransport } from "./api";
import { prefetchSessionQueries } from "./caseQueries";
import { goldTierSandboxQueryKeys } from "./goldTierSandboxQueries";
import GoldTierSandbox from "./pages/GoldTierSandbox";
import { DetailedProcessingInspector } from "./pages/CaseStatePanels";
import { createSessionQueryClient } from "./queryClient";
import type { AuthenticatedProfile, ZeroTouchCaseSummary } from "./types";

const hr: AuthenticatedProfile = {
  user_id: "hr-sandbox",
  display_name: "HR Sandbox Tester",
  role: "HR",
  team_id: null,
  team_display_name: null,
  team_type: null,
  team_description: "Administration only; no client-case access",
  client_scope_label: "Administration only",
  capabilities: ["POLICY_VIEW", "IDENTITY_ADMIN", "TEAM_ADMIN", "PROVIDER_SANDBOX_TEST"],
};

const caseActor: AuthenticatedProfile = {
  ...hr,
  user_id: "case-actor",
  role: "CLIENT_ONBOARDER",
  team_id: "TEAM_A",
  capabilities: ["CASE_ACCESS"],
};

function response(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function setInputValue(input: HTMLInputElement, value: string): void {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
  act(() => {
    setter?.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

function setSelectValue(select: HTMLSelectElement, value: string): void {
  const setter = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value")?.set;
  act(() => {
    setter?.call(select, value);
    select.dispatchEvent(new Event("change", { bubbles: true }));
  });
}

function findButton(label: string): HTMLButtonElement {
  const button = [...container!.querySelectorAll("button")]
    .find((item) => item.textContent?.trim() === label);
  expect(button, `button ${label}`).toBeTruthy();
  return button!;
}

function processingSummary(): ZeroTouchCaseSummary {
  return {
    case: {
      case_id: "00000000-0000-4000-8000-000000000222",
      registry_acquisition: {
        operation_results: [{
          operation: "ENTITY_PROFILE",
          status: "COMPLETE",
          record_count: 1,
          provenance: { provider: "ACRA", environment: "MOCK", evidence_reference: "safe-ref" },
          error: null,
        }],
      },
    },
    clm: { submission_plan: { environment: "SANDBOX" } },
    automation_id: "00000000-0000-4000-8000-000000000223",
    status: "RUNNING",
    current_stage: "GOLDTIER_SEARCH",
    completed_stages: ["REGISTRY"],
    target_operations: [
      { operation: "SEARCH", status: "NO_MATCH" },
      { operation: "SHELL", status: "SKIPPED" },
      { operation: "POLICY", status: "NOT_ATTEMPTED" },
    ],
    stage_order_version: 2,
    processing_pipeline: [
      {
        node_id: "CASE_START",
        label: "Case intake",
        status: "COMPLETE",
        safe_result: "Case accepted",
        children: [],
      },
      {
        node_id: "ACRA_REGISTRY",
        label: "ACRA registry",
        status: "IN_PROGRESS",
        provider: "ACRA",
        environment: "MOCK",
        operation: "ENTITY_PROFILE",
        backend_stage: "REGISTRY",
        timestamp: "2026-09-24T01:00:00Z",
        safe_result: "Registry profile retrieved",
        record_count: 1,
        blocker_code: null,
        retained_goldtier_id: "synthetic-retained-id",
        children: [
          { node_id: "PROFILE", label: "Entity profile", status: "EMPTY", children: [] },
        ],
      },
      { node_id: "DOCUMENT", label: "Documents", status: "SKIPPED", children: [] },
      { node_id: "REVIEW", label: "Human review", status: "REVIEW_REQUIRED", blocker_code: "NEEDS_REVIEW", children: [] },
      { node_id: "RECOVERY", label: "Recovery", status: "BLOCKED", children: [] },
      { node_id: "FAILED", label: "Failed operation", status: "FAILED", children: [] },
      { node_id: "LATER", label: "Later operation", status: "NOT_REACHED", children: [] },
    ],
    timeline: [{
      sequence: 1,
      event_type: "GOLDTIER_SEARCH_COMPLETED",
      status: "RUNNING",
      stage: "GOLDTIER_SEARCH",
      outcome: "SUCCEEDED",
      timestamp: "2026-09-24T01:00:00Z",
      case_id: "00000000-0000-4000-8000-000000000222",
      code: "GOLDTIER_SEARCH_NO_MATCH",
      message: "No GoldTier customer found.",
    }],
    updated_at: "2026-09-24T01:00:00Z",
  } as unknown as ZeroTouchCaseSummary;
}

let root: Root | null = null;
let container: HTMLDivElement | null = null;

beforeEach(() => {
  (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean })
    .IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
});

afterEach(async () => {
  if (root) await act(async () => root?.unmount());
  container?.remove();
  root = null;
  container = null;
  configureAuthenticatedTransport({ csrfToken: null, onUnauthorized: null });
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("GoldTier Sandbox frontend boundary", () => {
  it("uses user-scoped status identity and does not prefetch case data for HR", () => {
    expect(goldTierSandboxQueryKeys.status("hr-a")).toEqual([
      "auth", "hr-a", "provider-sandbox", "goldtier", "status",
    ]);
    expect(goldTierSandboxQueryKeys.status("hr-b")).not.toEqual(
      goldTierSandboxQueryKeys.status("hr-a"),
    );

    const client = createSessionQueryClient();
    const prefetch = vi.spyOn(client, "prefetchQuery").mockResolvedValue(undefined);
    prefetchSessionQueries(client, hr);
    expect(prefetch).not.toHaveBeenCalled();
    prefetchSessionQueries(client, caseActor);
    expect(prefetch).toHaveBeenCalledTimes(2);
  });

  it("blocks blank enumeration, renders safe results, dry-runs, and never enables write", async () => {
    const calls: Array<{ url: string; method: string; body: unknown }> = [];
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();
      const body = typeof init?.body === "string" ? JSON.parse(init.body) : null;
      calls.push({ url, method, body });
      if (url.endsWith("/api/admin/goldtier-sandbox/status")) {
        return response({
          configured: true,
          mode: "SANDBOX",
          classification: "SANDBOX_PARTIAL",
          safe_host: "sandbox.example.test",
          writes_enabled: true,
          timeout_seconds: 5,
          max_response_bytes: 65536,
          last_diagnostic_at: "2026-09-24T01:00:00Z",
          blocker: "Durable guarded-write execution is not yet available.",
          related_party_blocker: "BLOCKED_CHILD_ID_LIFECYCLE",
          vocabulary_version: "GOLDTIER_OPENAPI_1_0_0",
          kyc_customer_types: ["Company - Private"],
          client_segments: ["Corporate"],
          timeline: [{
            event_id: "00000000-0000-4000-8000-000000000224",
            action: "SEARCH",
            outcome: "SUCCEEDED",
            code: "GOLDTIER_SANDBOX_SEARCH_NO_MATCH",
            occurred_at: "2026-09-24T01:00:00Z",
          }],
        });
      }
      if (url.endsWith("/api/admin/goldtier-sandbox/search")) {
        return response({
          status: "NO_MATCH",
          count: 0,
          candidates: [],
          elapsed_ms: 12,
          entity_resolution: "REVIEW_REQUIRED",
        });
      }
      if (url.endsWith("/api/admin/goldtier-sandbox/dry-run")) {
        return response({
          dispatch_ready: false,
          blocker: "Required Sandbox test fields are missing.",
          operations: [{
            operation: "SEARCH",
            validation: "VALID",
            missing_fields: [],
            fields: [{
              target_field: "legalName",
              value: "SYNTHETIC TEST PTE. LTD.",
              provenance: "USER_INPUT",
              authority: "SANDBOX_TEST_ONLY",
              required: true,
              missing: false,
              validation: "VALID",
            }],
          }],
        });
      }
      return response({ detail: { code: "NOT_FOUND", message: "Unavailable." } }, 404);
    }));

    const client = createSessionQueryClient();
    await act(async () => {
      root?.render(
        <QueryClientProvider client={client}>
          <GoldTierSandbox actor={hr} />
        </QueryClientProvider>,
      );
    });
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    await vi.waitFor(() => expect(container?.textContent).toContain("sandbox.example.test"));
    expect(container?.textContent).toContain("GOLDTIER_SANDBOX_SEARCH_NO_MATCH");
    expect(container?.textContent).toContain("BLOCKED CHILD ID LIFECYCLE");

    await act(async () => container?.querySelector("form")?.dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true }),
    ));
    expect(container?.textContent).toContain("Enter at least one bounded search criterion");
    expect(calls.filter((call) => call.method === "POST")).toHaveLength(0);

    setInputValue(container!.querySelector("#sandbox-legal-name")!, "  SYNTHETIC TEST PTE. LTD.  ");
    await act(async () => container?.querySelector("form")?.dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true }),
    ));
    await vi.waitFor(() => expect(container?.textContent).toContain("REVIEW REQUIRED"));
    expect(calls.find((call) => call.url.endsWith("/search"))?.body).toEqual({
      legal_name: "SYNTHETIC TEST PTE. LTD.",
    });
    expect(calls.filter((call) => call.url.endsWith("/search"))).toHaveLength(1);

    await act(async () => findButton("Validate request preview").click());
    expect(container?.textContent).toContain("Select a KYC customer type and Client Segment");
    expect(calls.filter((call) => call.url.endsWith("/dry-run"))).toHaveLength(0);

    setInputValue(container!.querySelector("#sandbox-country")!, "SG");
    setSelectValue(
      container!.querySelector("#sandbox-kyc_customer_type")!,
      "Company - Private",
    );
    setSelectValue(container!.querySelector("#sandbox-client_segment")!, "Corporate");
    await act(async () => findButton("Validate request preview").click());
    await vi.waitFor(() => expect(container?.textContent).toContain("SANDBOX TEST ONLY"));
    expect(calls.find((call) => call.url.endsWith("/dry-run"))?.body).toEqual({
      search: {
        legal_name: "SYNTHETIC TEST PTE. LTD.",
        country_of_incorporation: "SG",
      },
      test_values: {
        kyc_customer_type: "Company - Private",
        client_segment: "Corporate",
        customer_external_system: "DSD",
        registration_type: "ACRA",
        policy: "Singapore",
        booking_entity: "ANZBGL (Singapore Branch)",
      },
    });
    expect(calls.filter((call) => call.url.endsWith("/dry-run"))).toHaveLength(1);

    const writeButton = findButton("Run guarded synthetic write");
    expect(writeButton.disabled).toBe(true);
    expect(container?.textContent).toContain("Durable guarded-write execution is not yet available");
    expect(calls.some((call) => call.url.includes("write"))).toBe(false);
  });
});

describe("backend-authored detailed processing", () => {
  it("starts collapsed and reveals the server-ordered semantic pipeline", () => {
    act(() => root?.render(<DetailedProcessingInspector summary={processingSummary()} />));
    const toggle = findButton("Show processing details");
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    const controlledContentId = toggle.getAttribute("aria-controls");
    expect(controlledContentId).toBeTruthy();
    expect(container?.ownerDocument.getElementById(controlledContentId!)?.hasAttribute("hidden")).toBe(true);

    act(() => toggle.click());
    const tree = container?.querySelector('ol[aria-label="Backend processing pipeline"]');
    expect(tree).toBeTruthy();
    const topLevelNodes = Array.from(tree!.children);
    expect(topLevelNodes.map((item) => item.querySelector(".processing-pipeline__node-title")?.textContent))
      .toEqual([
        "Case intake",
        "ACRA registry",
        "Documents",
        "Human review",
        "Recovery",
        "Failed operation",
        "Later operation",
      ]);
    expect(tree?.tagName).toBe("OL");
    expect(topLevelNodes.every((item) => item.tagName === "LI")).toBe(true);
    expect(tree?.querySelector("ol[aria-label='ACRA registry steps'] li .processing-pipeline__node-title")?.textContent)
      .toBe("Entity profile");

    for (const status of [
      "COMPLETE",
      "IN_PROGRESS",
      "EMPTY",
      "SKIPPED",
      "REVIEW_REQUIRED",
      "BLOCKED",
      "FAILED",
      "NOT_REACHED",
    ]) {
      const badge = container?.querySelector(`.processing-pipeline__status[data-status="${status}"]`);
      expect(badge?.textContent).toBe(status.replaceAll("_", " "));
      expect(badge?.getAttribute("aria-label")).toBe(`Status: ${status.replaceAll("_", " ")}`);
    }
    expect(container?.textContent).toContain("Registry profile retrieved");
    expect(container?.textContent).toContain("Retained GoldTier ID");

    const technicalDetails = [...container!.querySelectorAll("details")]
      .find((details) => details.querySelector("summary")?.textContent === "Technical details");
    expect(technicalDetails).toBeTruthy();
    expect(technicalDetails?.open).toBe(false);
    expect(technicalDetails?.querySelectorAll("table").length).toBeGreaterThan(0);
    expect(technicalDetails?.querySelector("table")?.closest("details")?.open).toBe(false);
    expect(findButton("Hide processing details").getAttribute("aria-expanded")).toBe("true");
  });

  it("renders a historical v1 pipeline in the exact backend-provided order", () => {
    const summary = processingSummary();
    summary.stage_order_version = 1;
    summary.processing_pipeline = [
      { node_id: "CASE_START", label: "Case start", status: "COMPLETE", children: [] },
      { node_id: "DOCUMENT_IDP", label: "Document and IDP", status: "COMPLETE", children: [] },
      {
        node_id: "GOLDTIER_TARGET",
        label: "GoldTier target",
        status: "COMPLETE",
        children: [
          { node_id: "GOLDTIER_SEARCH", label: "Search", status: "COMPLETE", children: [] },
        ],
      },
    ];
    act(() => root?.render(<DetailedProcessingInspector summary={summary} />));
    act(() => findButton("Show processing details").click());

    const tree = container?.querySelector('ol[aria-label="Backend processing pipeline"]');
    expect(Array.from(tree!.children).map(
      (item) => item.querySelector(".processing-pipeline__node-title")?.textContent,
    )).toEqual(["Case start", "Document and IDP", "GoldTier target"]);
    expect(tree?.querySelector("ol[aria-label='GoldTier target steps'] .processing-pipeline__node-title")?.textContent)
      .toBe("Search");
  });

  it("does not render retained event message text in the inspector", () => {
    const summary = processingSummary();
    const sensitiveMessage = [
      "Author",
      "ization: ",
      "Bea",
      "rer ",
      "secret",
      "-token raw-provider-body",
    ].join("");
    summary.timeline[0]!.message = sensitiveMessage;

    act(() => root?.render(<DetailedProcessingInspector summary={summary} />));
    act(() => findButton("Show processing details").click());
    const technicalDetails = [...container!.querySelectorAll("details")]
      .find((details) => details.querySelector("summary")?.textContent === "Technical details");
    act(() => {
      technicalDetails!.open = true;
      technicalDetails!.dispatchEvent(new Event("toggle"));
    });

    expect(container?.textContent).toContain("GOLDTIER_SEARCH_NO_MATCH");
    expect(container?.textContent).not.toContain("secret-token");
    expect(container?.textContent).not.toContain("raw-provider-body");
  });
});
