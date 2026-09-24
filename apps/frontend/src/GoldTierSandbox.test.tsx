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
import { STAGE_BANDS } from "./shared";
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
    expect(container?.textContent).toContain("Complete all Sandbox test-only fields");
    expect(calls.filter((call) => call.url.endsWith("/dry-run"))).toHaveLength(0);

    setInputValue(container!.querySelector("#sandbox-country")!, "SG");
    const testValueIds = [
      "kyc_customer_type",
      "client_segment",
      "customer_external_system",
      "registration_type",
      "policy",
      "booking_entity",
      "account_entity_type",
      "product_type",
    ];
    for (const id of testValueIds) {
      setInputValue(container!.querySelector(`#sandbox-${id}`)!, "SANDBOX TEST");
    }
    await act(async () => findButton("Validate request preview").click());
    await vi.waitFor(() => expect(container?.textContent).toContain("SANDBOX TEST ONLY"));
    expect(calls.find((call) => call.url.endsWith("/dry-run"))?.body).toEqual({
      search: {
        legal_name: "SYNTHETIC TEST PTE. LTD.",
        country_of_incorporation: "SG",
      },
      test_values: {
        kyc_customer_type: "SANDBOX TEST",
        client_segment: "SANDBOX TEST",
        customer_external_system: "SANDBOX TEST",
        registration_type: "SANDBOX TEST",
        policy: "SANDBOX TEST",
        booking_entity: "SANDBOX TEST",
        account_entity_type: "SANDBOX TEST",
        product_type: "SANDBOX TEST",
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
  it("adds GoldTier Search to the rail and reveals only occurred operations", () => {
    expect(STAGE_BANDS.map((band) => band.label)).toContain("GoldTier customer search");
    act(() => root?.render(<DetailedProcessingInspector summary={processingSummary()} />));
    expect(container?.textContent).not.toContain("No GoldTier customer found.");

    act(() => findButton("Show processing details").click());
    expect(container?.textContent).toContain("GOLDTIER SEARCH");
    expect(container?.textContent).toContain("No GoldTier customer found.");
    expect(container?.textContent).toContain("NO MATCH");
    expect(container?.textContent).toContain("SKIPPED");
    expect(container?.textContent).not.toContain("NOT ATTEMPTED");
    expect(findButton("Hide processing details").getAttribute("aria-expanded")).toBe("true");
  });
});
