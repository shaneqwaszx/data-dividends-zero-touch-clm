// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { GoldTierTargetClassification } from "../types";
import { updateGoldTierTargetClassification } from "../api";
import TargetClassificationPanel from "./TargetClassificationPanel";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const unresolved: GoldTierTargetClassification = {
  vocabulary_version: "goldtier-openapi-1.0.0",
  editable: true,
  kyc_customer_type: {
    allowed_values: ["Company - Private", "Partnership - Regulated"],
    selected_value: null,
    authority: null,
    required: true,
  },
  client_segment: {
    allowed_values: ["Corporate", "Commercial BB (Business Banking)"],
    selected_value: null,
    authority: null,
    required: true,
  },
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

function render(
  classification = unresolved,
  onSubmit = vi.fn(async () => undefined),
  disabled = false,
) {
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
  act(() => root?.render(
    <TargetClassificationPanel
      classification={classification}
      disabled={disabled}
      onSubmit={onSubmit}
    />,
  ));
  return { view: container, onSubmit };
}

function choose(label: string, value: string): void {
  const select = container!.querySelector(`select[aria-label="${label}"]`) as HTMLSelectElement;
  act(() => {
    select.value = value;
    select.dispatchEvent(new Event("change", { bubbles: true }));
  });
}

describe("TargetClassificationPanel", () => {
  it("offers only the backend-provided vocabulary and submits both selections", async () => {
    const { view, onSubmit } = render();
    const selects = [...view.querySelectorAll("select")];
    expect(selects.map((select) => [...select.options].map((option) => option.value))).toEqual([
      ["", "Company - Private", "Partnership - Regulated"],
      ["", "Corporate", "Commercial BB (Business Banking)"],
    ]);
    expect(view.querySelector("input, textarea")).toBeNull();

    choose("KYC customer type", "Company - Private");
    choose("Client segment", "Corporate");
    await act(async () => {
      view.querySelector("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      await Promise.resolve();
    });

    expect(onSubmit).toHaveBeenCalledWith({
      kyc_customer_type: "Company - Private",
      client_segment: "Corporate",
    });
  });

  it("keeps retained selections editable while the backend says editable", async () => {
    const { view, onSubmit } = render({
      ...unresolved,
      kyc_customer_type: {
        ...unresolved.kyc_customer_type,
        selected_value: "Company - Private",
        authority: "USER_AUTHORIZED_POC",
      },
      client_segment: {
        ...unresolved.client_segment,
        selected_value: "Corporate",
        authority: "USER_AUTHORIZED_POC",
      },
    });

    expect(view.querySelector("form")).not.toBeNull();
    expect((view.querySelector('[aria-label="KYC customer type"]') as HTMLSelectElement).value).toBe("Company - Private");
    expect((view.querySelector('[aria-label="Client segment"]') as HTMLSelectElement).value).toBe("Corporate");
    expect(view.textContent).toContain("remain editable before target dispatch confirmation");

    choose("Client segment", "Commercial BB (Business Banking)");
    await act(async () => {
      view.querySelector("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      await Promise.resolve();
    });
    expect(onSubmit).toHaveBeenCalledWith({
      kyc_customer_type: "Company - Private",
      client_segment: "Commercial BB (Business Banking)",
    });
  });

  it("sends CAS values once and surfaces a stale response without retry", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      detail: { code: "ZERO_TOUCH_TARGET_CLASSIFICATION_STALE", message: "The case changed." },
    }), { status: 409, headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(updateGoldTierTargetClassification("case-1", {
      kyc_customer_type: "Company - Private",
      client_segment: "Corporate",
      expected_automation_version: 8,
      expected_case_event_count: 6,
    })).rejects.toMatchObject({ status: 409, code: "ZERO_TOUCH_TARGET_CLASSIFICATION_STALE" });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/api/clm/zero-touch/cases/case-1/target-classification");
    expect(JSON.parse(String(init.body))).toEqual({
      kyc_customer_type: "Company - Private",
      client_segment: "Corporate",
      expected_automation_version: 8,
      expected_case_event_count: 6,
    });
  });

  it("does not expose an edit form when the backend marks an unresolved case non-editable", () => {
    const { view } = render({ ...unresolved, editable: false });
    expect(view.querySelector("form, select")).toBeNull();
    expect(view.textContent).toContain("Unresolved · Not recorded");
    expect(view.textContent).toContain("cannot accept a target-classification change");
  });
});
