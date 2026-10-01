// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import { configureAuthenticatedTransport } from "../api";
import { WorkspaceTabs } from "../navigation";
import type {
  AcraDiagnosticOutcome,
  AcraDiagnosticResult,
  AcraDiagnosticStatus,
  AuthenticatedProfile,
} from "../types";
import AcraDiagnostics, {
  AcraDiagnosticOutcomePanel,
  acraDiagnosticQueryKeys,
  sanitizedReceiptText,
} from "./AcraDiagnostics";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const hr: AuthenticatedProfile = {
  user_id: "hr-user", display_name: "HR User", role: "HR", team_id: null,
  team_display_name: null, team_type: null, team_description: "", client_scope_label: "",
  capabilities: ["PROVIDER_SANDBOX_TEST"],
};
const rm: AuthenticatedProfile = {
  ...hr, user_id: "rm-user", display_name: "RM User", role: "RELATIONSHIP_MANAGER",
  capabilities: ["CASE_ACCESS"],
};

const receipt = {
  diagnostic_id: "00000000-0000-4000-8000-000000000001",
  provider: "ACRA_GENERIC_SANDBOX",
  classification: "PARTIAL",
  operation: "ENTITY_PROFILE",
  request_reference: "acra-diagnostic:0123456789abcdef",
  started_at: "2026-09-29T00:00:00Z",
  completed_at: "2026-09-29T00:00:01Z",
  outcome: "COMPLETE",
  code: "ACRA_DIAGNOSTIC_ENTITY_PROFILE_COMPLETE",
  provider_called: true,
  record_count: 1,
} as const;

const status: AcraDiagnosticStatus = {
  configuration: {
    provider: "ACRA_GENERIC_SANDBOX", mode: "sandbox", classification: "PARTIAL",
    configured: true, safe_host: "sandbox.example.test", client_id_present: true,
    secret_key_present: true, generic_auth_present: false, timeout_seconds: 5,
    max_response_bytes: 65536,
  },
  connectivity: "NOT_CHECKED",
  last_actual_check_at: null,
  cancellation_semantics: "PRE_DISPATCH_ONLY_IN_FLIGHT_USES_TIMEOUT",
  coverage: [
    { operation: "ENTITY_PROFILE", availability: "SUPPORTED", reason_code: "IMPLEMENTED_STRICT_CONNECTOR_OPERATION" },
    { operation: "LLP_HIGHLIGHTS", availability: "UNSUPPORTED", reason_code: "PROVIDER_CONTRACT_NOT_IMPLEMENTED" },
  ],
  samples: [{
    uen: "11111999A", legal_name: "Garden Business",
    classification: "DOCUMENTED_SAMPLE_CANDIDATE", operations: ["ENTITY_PROFILE"],
    limitation_codes: ["REQUIRES_CURRENT_DIAGNOSTIC_RUN"],
  }],
  timeline: [],
};

function result(outcome: AcraDiagnosticOutcome): AcraDiagnosticResult {
  return {
    requested_uen: "11111999A",
    operation: "ENTITY_PROFILE",
    outcome,
    code: `ACRA_DIAGNOSTIC_${outcome}`,
    message: `Safe ${outcome} message.`,
    missing_fields: outcome === "PARTIAL" ? ["registered_address"] : [],
    company: null,
    officers: [],
    shareholders: [],
    receipt: { ...receipt, outcome, code: `ACRA_DIAGNOSTIC_${outcome}`, record_count: 0 },
  };
}

let root: Root | null = null;
let container: HTMLDivElement | null = null;

afterEach(() => {
  if (root) act(() => root?.unmount());
  container?.remove();
  root = null;
  container = null;
  configureAuthenticatedTransport({ csrfToken: null, onUnauthorized: null });
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

async function waitFor(assertion: () => void): Promise<void> {
  for (let attempt = 0; attempt < 30; attempt += 1) {
    try {
      assertion();
      return;
    } catch (error) {
      if (attempt === 29) throw error;
      await act(async () => new Promise((resolve) => setTimeout(resolve, 0)));
    }
  }
}

function mount(fetchMock: ReturnType<typeof vi.fn>): { view: HTMLDivElement; client: QueryClient } {
  vi.stubGlobal("fetch", fetchMock);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
  act(() => root?.render(<QueryClientProvider client={client}><AcraDiagnostics actor={hr} /></QueryClientProvider>));
  return { view: container, client };
}

describe("ACRA diagnostics access and query ownership", () => {
  it("shows navigation to HR capability holders and omits it for relationship managers", () => {
    const hrMarkup = renderToStaticMarkup(<MemoryRouter><WorkspaceTabs actor={hr} /></MemoryRouter>);
    const rmMarkup = renderToStaticMarkup(<MemoryRouter><WorkspaceTabs actor={rm} /></MemoryRouter>);
    expect(hrMarkup).toContain("ACRA Diagnostics");
    expect(hrMarkup).toContain('/admin/acra');
    expect(rmMarkup).not.toContain("ACRA Diagnostics");
  });

  it("uses a user-scoped provider key without any case namespace", () => {
    expect(acraDiagnosticQueryKeys.status("hr-a")).not.toEqual(acraDiagnosticQueryKeys.status("hr-b"));
    expect(acraDiagnosticQueryKeys.status("hr-a")).toEqual(["auth", "hr-a", "provider-sandbox", "acra", "status"]);
    expect(JSON.stringify(acraDiagnosticQueryKeys.status("hr-a"))).not.toContain("cases");
  });
});

describe("AcraDiagnostics", () => {
  it("explains marketplace authentication and provides collapsed keyboard-accessible help without a lookup", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({
      ...status,
      configuration: { ...status.configuration, provider: "ACRA_API_MARKETPLACE_MOCK", mode: "api_marketplace_mock", classification: "MOCK" },
    }), { status: 200, headers: { "Content-Type": "application/json" } }));
    const { view } = mount(fetchMock);
    await waitFor(() => expect(view.textContent).toContain("Not applicable for API Marketplace Mock"));
    expect(view.textContent).toContain("unsupported does not mean empty");
    const help = view.querySelector("details")!;
    expect(help.open).toBe(false);
    const summary = help.querySelector("summary")!;
    expect(summary.textContent).toBe("What this tab does");
    summary.focus();
    expect(document.activeElement).toBe(summary);
    act(() => summary.click());
    expect(help.open).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("separates configuration, connectivity, completeness, and prefills samples without submitting", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).endsWith("/api/admin/acra/status")) return new Response(JSON.stringify(status), { status: 200, headers: { "Content-Type": "application/json" } });
      return new Response(JSON.stringify(result("COMPLETE")), { status: 200, headers: { "Content-Type": "application/json" } });
    });
    const { view } = mount(fetchMock);
    await waitFor(() => expect(view.textContent).toContain("Data completeness"));
    expect(view.textContent).toContain("Configuration");
    expect(view.textContent).toContain("Connectivity");
    expect(view.textContent).toContain("sandbox.example.test");
    expect(fetchMock.mock.calls.filter(([url]) => String(url).includes("/cases"))).toHaveLength(0);

    const sample = view.querySelector("#acra-sample") as HTMLSelectElement;
    act(() => { sample.value = "11111999A"; sample.dispatchEvent(new Event("change", { bubbles: true })); });
    expect((view.querySelector("#acra-uen") as HTMLInputElement).value).toBe("11111999A");
    expect((view.querySelector("#acra-operation") as HTMLSelectElement).value).toBe("ENTITY_PROFILE");
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(0);
    expect(view.textContent).toContain("Selection prefills only; it does not run a lookup");

    await act(async () => {
      view.querySelector("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    });
    await waitFor(() => expect(view.textContent).toContain("Outcome: Complete"));
    const posts = fetchMock.mock.calls.filter(([, init]) => init?.method === "POST");
    expect(posts).toHaveLength(1);
    expect(JSON.parse(String(posts[0][1]?.body))).toEqual({ uen: "11111999A", operation: "ENTITY_PROFILE" });
  });

  it("handles a 401 once and lets the session boundary clear cached data", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: { code: "AUTHENTICATION_REQUIRED", message: "A valid authenticated session is required." } }), { status: 401, headers: { "Content-Type": "application/json" } }));
    const client = new QueryClient();
    client.setQueryData(["auth", "hr-user", "sentinel"], "cached");
    const unauthorized = vi.fn(() => client.clear());
    configureAuthenticatedTransport({ csrfToken: null, onUnauthorized: unauthorized });
    vi.stubGlobal("fetch", fetchMock);
    container = document.createElement("div"); document.body.append(container); root = createRoot(container);
    act(() => root?.render(<QueryClientProvider client={client}><AcraDiagnostics actor={hr} /></QueryClientProvider>));
    await waitFor(() => expect(unauthorized).toHaveBeenCalledTimes(1));
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(client.getQueryCache().getAll()).toHaveLength(0);
  });
});

describe("safe ACRA outcome presentation", () => {
  it.each(["EMPTY", "NOT_FOUND", "PARTIAL", "FAILED"] as const)("distinguishes %s without exposing raw payloads", (outcome) => {
    const markup = renderToStaticMarkup(<AcraDiagnosticOutcomePanel result={result(outcome)} />);
    expect(markup).toContain(`Outcome: ${outcome === "NOT_FOUND" ? "Not found" : readableForTest(outcome)}`);
    expect(markup).not.toContain("raw_payload");
  });

  it("builds a copyable receipt without the requested UEN", () => {
    const text = sanitizedReceiptText(receipt);
    expect(text).toContain("acra-diagnostic:0123456789abcdef");
    expect(text).not.toContain("11111999A");
    expect(text).not.toContain("token");
  });
});

function readableForTest(value: string): string {
  return value.toLowerCase().replace(/^./, (letter) => letter.toUpperCase());
}
