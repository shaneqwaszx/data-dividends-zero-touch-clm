// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { QueryClientProvider, QueryObserver } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import App, { SimulationBanner } from "./App";
import { caseQueryKeys, caseSummaryMutationEffect, caseSupportingMutationEffect } from "./caseQueries";
import { createSessionQueryClient } from "./queryClient";
import { registryOperationProgressState } from "./pages/CaseStatePanels";
import type { AuthenticatedProfile, SimulationProfile, ZeroTouchCaseSummary } from "./types";

afterEach(() => vi.unstubAllGlobals());

describe("Garden action performance boundaries", () => {
  it("reproduces the previous two-request supporting recipe as the comparison baseline", async () => {
    const client = createSessionQueryClient();
    const key = caseQueryKeys.intelligence("actor", "case-1");
    client.setQueryData(key, { revision: 1 });
    const signals: AbortSignal[] = [];
    const requests = vi.fn(async ({ signal }: { signal: AbortSignal }) => {
      signals.push(signal);
      await new Promise((resolve) => setTimeout(resolve, 5));
      return { revision: 2 };
    });
    const observer = new QueryObserver(client, { queryKey: key, queryFn: requests });
    const unsubscribe = observer.subscribe(() => undefined);
    const summary = { case: { case_id: "case-1" } } as ZeroTouchCaseSummary;
    // The accepted base called the summary effect before invalidating this same resource.
    caseSummaryMutationEffect(client, "actor", summary);
    await client.invalidateQueries({ queryKey: key, exact: true });
    expect(requests).toHaveBeenCalledTimes(2);
    expect(signals.map((signal) => signal.aborted)).toEqual([true, false]);
    unsubscribe();
    client.clear();
  });

  it("refetches active supporting intelligence exactly once without cancelling and restarting", async () => {
    const client = createSessionQueryClient();
    const key = caseQueryKeys.intelligence("actor", "case-1");
    client.setQueryData(key, { revision: 1 });
    const requests = vi.fn(async ({ signal }: { signal: AbortSignal }) => {
      await new Promise((resolve) => setTimeout(resolve, 5));
      expect(signal.aborted).toBe(false);
      return { revision: 2 };
    });
    const observer = new QueryObserver(client, { queryKey: key, queryFn: requests });
    const unsubscribe = observer.subscribe(() => undefined);
    const summary = { case: { case_id: "case-1" } } as ZeroTouchCaseSummary;
    await caseSupportingMutationEffect(client, "actor", summary);
    expect(requests).toHaveBeenCalledTimes(1);
    expect(client.getQueryData(key)).toEqual({ revision: 2 });
    expect(client.getQueryData(caseQueryKeys.detail("actor", "case-1"))).toBe(summary);
    unsubscribe();
    client.clear();
  });

  it("dispatches one create for two same-turn submits and permits retry after failure", async () => {
    (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    const client = createSessionQueryClient();
    const actor = {
      user_id: "actor", display_name: "Synthetic operator", role: "RELATIONSHIP_MANAGER",
      team_id: "TEAM_A", capabilities: ["CASE_ACCESS"],
    } as AuthenticatedProfile;
    client.setQueryData(caseQueryKeys.executionProfile(actor.user_id), {
      registry_provider_mode: "LOCAL_MOCK", target_environment: "MOCK",
      registry_system: "ACRA", registry_environment: "MOCK", idp_environment: "LOCAL",
    });
    let failCreate: (() => void) | undefined;
    const requests = vi.fn(() => new Promise<Response>((resolve) => {
      failCreate = () => resolve(new Response(JSON.stringify({ detail: "Synthetic failure" }), { status: 400 }));
    }));
    vi.stubGlobal("fetch", requests);
    const container = document.createElement("div");
    document.body.append(container);
    const root = createRoot(container);
    try {
      await act(async () => root.render(<QueryClientProvider client={client}><MemoryRouter initialEntries={["/new-onboarding"]}><App actor={actor} onLogout={() => undefined} /></MemoryRouter></QueryClientProvider>));
      const form = container.querySelector("form")!;
      expect(form).not.toBeNull();
      const setValue = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
      await act(async () => {
        for (const [id, value] of [["#home-uen", "202400001A"], ["#home-legal-name", "SYNTHETIC PERFORMANCE PTE. LTD."]] as const) {
          const input = container.querySelector<HTMLInputElement>(id)!;
          setValue.call(input, value);
          input.dispatchEvent(new Event("input", { bubbles: true }));
        }
      });
      const fileInput = container.querySelector<HTMLInputElement>("#home-document")!;
      Object.defineProperty(fileInput, "files", { configurable: true, value: [new File(["synthetic test"], "synthetic.txt", { type: "text/plain" })] });
      await act(async () => fileInput.dispatchEvent(new Event("change", { bubbles: true })));
      await act(async () => {
        form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      });
      expect(requests).toHaveBeenCalledTimes(1);
      expect(container.textContent).toContain("Creating case…");
      await act(async () => failCreate?.());
      await act(async () => form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
      expect(requests).toHaveBeenCalledTimes(2);
      await act(async () => failCreate?.());
    } finally {
      await act(async () => root.unmount());
      container.remove();
      client.clear();
    }
  });

  it("labels offline protocol evidence explicitly and never treats unsupported as empty success", () => {
    const profile = { registry_provider_mode: "API_MARKETPLACE_PROTOCOL_TEST", target_environment: "MOCK" } as SimulationProfile;
    const html = renderToStaticMarkup(<SimulationBanner profile={profile} />);
    expect(html).toContain("ACRA Marketplace protocol · synthetic offline test evidence");
    expect(html).not.toContain("Official ACRA");
    expect(registryOperationProgressState("UNSUPPORTED")).toBe("UNAVAILABLE");
    expect(registryOperationProgressState("EMPTY")).toBe("SUCCESS");
  });
});


it("labels isolated document refresh as Local/Mock evidence", () => {
  vi.stubEnv("VITE_E2E_RECOVERY_DEMO", "document-refresh");
  try {
    const html = renderToStaticMarkup(<SimulationBanner profile={null} />);
    expect(html).toContain("Local document evidence and Mock target");
    expect(html).toContain("Zero external provider calls");
    expect(html).toContain('<span class="environment-banner__label">');
    expect(html).toContain('role="status"');
    expect(html).toContain("no interoperability is demonstrated");
    expect(html).not.toContain('aria-hidden="true"');
    expect(html).not.toContain("XPI");
  } finally { vi.unstubAllEnvs(); }
});

it("labels the isolated Slice C inert XPI seam as synthetic offline evidence", () => {
  vi.stubEnv("VITE_E2E_RECOVERY_DEMO", "optional-amend");
  try {
    const html = renderToStaticMarkup(<SimulationBanner profile={null} />);
    expect(html).toContain("Slice C synthetic offline recovery fixture");
    expect(html).toContain("zero external provider calls");
    expect(html).toContain('<span class="environment-banner__label">');
    expect(html).toContain('role="status"');
    expect(html).toContain("no interoperability is demonstrated");
    expect(html).not.toContain('aria-hidden="true"');
  } finally { vi.unstubAllEnvs(); }
});
