// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClient } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";

import { rebindZeroTouchPolicy } from "../api";
import { caseQueryKeys, policyRebindMutationEffect } from "../caseQueries";
import type { GoldTierTargetClassification, PolicyRebindMetadata, ZeroTouchCaseSummary } from "../types";
import PolicyRebindPanel from "./PolicyRebindPanel";
import TargetClassificationPanel from "./TargetClassificationPanel";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const current: PolicyRebindMetadata = {
  revision: 2,
  configuration_status: "CURRENT_ACCEPTED_POC",
  accepted_poc_fields: ["customerExternalSystem", "registrationType", "policy", "bookingEntity"],
  editable_fields: ["kycCustomerType", "clientSegment"],
  upstream_fields: ["registrationNumber"],
  unavailable_fields: ["accountEntityType", "productType"],
  last_rebound_by: "case-user",
  last_rebound_at: "2026-09-29T02:00:00Z",
  last_rationale: "Replace superseded SG POC target constants.",
  last_changed_fields: ["customerExternalSystem", "registrationType", "policy", "bookingEntity"],
};

const legacy: PolicyRebindMetadata = {
  ...current,
  revision: 1,
  configuration_status: "REQUIRES_REBIND",
  accepted_poc_fields: [],
  last_rebound_by: null,
  last_rebound_at: null,
  last_rationale: null,
  last_changed_fields: [],
};

let root: Root | null = null;
let container: HTMLDivElement | null = null;

afterEach(() => {
  if (root) act(() => root?.unmount());
  container?.remove();
  root = null;
  container = null;
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function render(metadata = current, onSubmit = vi.fn(), onFocusClassification = vi.fn()) {
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
  act(() => root?.render(
    <PolicyRebindPanel
      metadata={metadata}
      registrationNumber="202400001A"
      disabled={false}
      onSubmit={onSubmit}
      onFocusClassification={onFocusClassification}
    />,
  ));
  return { view: container, onSubmit, onFocusClassification };
}

function enter(element: HTMLTextAreaElement, value: string): void {
  Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")?.set?.call(element, value);
  element.dispatchEvent(new Event("input", { bubbles: true }));
}

describe("PolicyRebindPanel", () => {
  it("shows current authority categories and the latest receipt without offering rebind", () => {
    const { view, onFocusClassification } = render();
    expect(view.textContent).toContain("Accepted system configuration");
    expect(view.textContent).toContain("Customer external system · accepted for this case");
    expect(view.textContent).toContain("Editable operator choices");
    expect(view.textContent).toContain("KYC customer type · User-authorized POC choice");
    expect(view.textContent).toContain("Registration number · 202400001A");
    expect(view.textContent).toContain("Account entity type · unavailable pending sponsor authority");
    expect(view.textContent).toContain("Policy snapshot revision: 2");
    expect(view.textContent).toContain("Last rebound by: case-user");
    expect(view.textContent).toContain("Replace superseded SG POC target constants.");
    expect(view.textContent).not.toContain("Rebind accepted Singapore POC configuration");
    act(() => (view.querySelector(".policy-rebind__categories .btn") as HTMLButtonElement).click());
    expect(onFocusClassification).toHaveBeenCalledTimes(1);
  });

  it("requires rationale and offers the exact legacy rebind action only when required", () => {
    const { view, onSubmit } = render(legacy);
    const button = [...view.querySelectorAll("button")].find((item) => item.textContent?.includes("Rebind accepted"))!;
    expect(button.disabled).toBe(true);
    expect(view.textContent).toContain("preserves operator-selected");
    expect(view.textContent).toContain("not a wholesale reset");
    act(() => enter(view.querySelector("#policy-rebind-rationale")!, "Replace superseded SG POC target constants."));
    expect(button.disabled).toBe(false);
    act(() => view.querySelector("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    expect(onSubmit).toHaveBeenCalledWith("Replace superseded SG POC target constants.");
  });

  it("leaves KYC and segment editable in their separate existing control", () => {
    const classification: GoldTierTargetClassification = {
      vocabulary_version: "v1",
      editable: true,
      kyc_customer_type: { allowed_values: ["Company - Private"], selected_value: "Company - Private", authority: "USER_AUTHORIZED_POC", required: true },
      client_segment: { allowed_values: ["Corporate"], selected_value: "Corporate", authority: "USER_AUTHORIZED_POC", required: true },
    };
    container = document.createElement("div");
    document.body.append(container);
    root = createRoot(container);
    act(() => root?.render(<><PolicyRebindPanel metadata={legacy} registrationNumber="202400001A" disabled={false} onSubmit={() => undefined} onFocusClassification={() => undefined} /><TargetClassificationPanel classification={classification} disabled={false} onSubmit={async () => undefined} /></>));
    expect(container.querySelector(".policy-rebind select")).toBeNull();
    expect(container.querySelectorAll("#case-target-classification select, select")).toHaveLength(2);
    expect(container.textContent).toContain("remain editable before target dispatch confirmation");
  });
});

describe("policy rebind endpoint and cache effect", () => {
  const payload = {
    rationale: "Replace superseded SG POC target constants.",
    expected_automation_version: 9,
    expected_clm_version: 6,
    expected_case_event_count: 8,
  };

  it("posts the exact CAS-bound legacy request", async () => {
    const summary = { case: { case_id: "case-1" } } as ZeroTouchCaseSummary;
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(summary), { status: 200, headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    await rebindZeroTouchPolicy("case-1", payload);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/api/clm/zero-touch/cases/case-1/policy-rebind");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual(payload);
  });

  it("surfaces stale 409 with one request and no retry", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: { code: "ZERO_TOUCH_POLICY_REBIND_STALE", message: "The onboarding case changed before policy rebind." } }), { status: 409, headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(rebindZeroTouchPolicy("case-1", payload)).rejects.toMatchObject({ status: 409, code: "ZERO_TOUCH_POLICY_REBIND_STALE" });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("publishes and invalidates only the acting user's scopes", () => {
    const client = new QueryClient();
    const summary = { case: { case_id: "case-1" } } as ZeroTouchCaseSummary;
    client.setQueryData(caseQueryKeys.detail("other-user", "case-1"), { marker: "untouched" });
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const remove = vi.spyOn(client, "removeQueries");
    policyRebindMutationEffect(client, "case-user", summary);
    expect(client.getQueryData(caseQueryKeys.detail("case-user", "case-1"))).toBe(summary);
    expect(client.getQueryData(caseQueryKeys.detail("other-user", "case-1"))).toEqual({ marker: "untouched" });
    expect(invalidate.mock.calls.every(([filters]) => JSON.stringify(filters?.queryKey).includes("case-user"))).toBe(true);
    expect(remove.mock.calls.every(([filters]) => JSON.stringify(filters?.queryKey).includes("case-user"))).toBe(true);
  });
});
