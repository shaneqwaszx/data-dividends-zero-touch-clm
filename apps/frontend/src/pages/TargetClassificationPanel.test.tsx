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
  reviewRequested = false,
) {
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
  act(() => root?.render(
    <TargetClassificationPanel
      classification={classification}
      disabled={disabled}
      onSubmit={onSubmit}
      reviewRequested={reviewRequested}
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
    expect(view.textContent).toContain("Review the unresolved evidence before selecting a fallback value");

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
    expect(view.textContent).toContain("Unresolved · User selection required");
    expect(view.textContent).toContain("cannot accept a target-classification change");
  });
});

const documentSelection = {
  field_key: "kyc_customer_type" as const, value: "Company - Private", source: "DOCUMENT" as const,
  document_evidence: { document_id: "synthetic-document", document_version: 1, document_event_count: 8,
    page_number: 1, source_reference: "PAGE_1_LINE_6", extraction_method: "LOCAL_TESSERACT_OCR",
    extraction_quality: "HIGH", evidence_score: 0.95, extracted_exact_value: "Company - Private" },
  classified_at: "2026-10-05T00:00:00Z", policy_version: 2, vocabulary_version: "GOLDTIER_OPENAPI_V1_0_0",
};
describe("automatic document selection", () => {
  it("opens current automatic values only for an explicit final review edit", async () => {
    const classification: GoldTierTargetClassification = { ...unresolved, evidence_fingerprint: "current-fixture-fingerprint",
      kyc_customer_type: { ...unresolved.kyc_customer_type, selected_value: "Company - Private", selection: documentSelection },
      client_segment: { ...unresolved.client_segment, selected_value: "Corporate", selection: { ...documentSelection, field_key: "client_segment", value: "Corporate" } },
    };
    const { view, onSubmit } = render(classification, vi.fn(async () => undefined), false, true);
    expect([...view.querySelectorAll("select")].map(select => [select.value, select.disabled])).toEqual([
      ["Company - Private", false], ["Corporate", false],
    ]);
    await act(async () => { view.querySelector("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })); });
    expect(onSubmit).toHaveBeenCalledWith({ kyc_customer_type: "Company - Private", client_segment: "Corporate", expected_classification_evidence_fingerprint: "current-fixture-fingerprint" });
  });
  it("shows source evidence and removes the save form when both fields are automatic", () => {
    const classification: GoldTierTargetClassification = { ...unresolved,
      kyc_customer_type: { ...unresolved.kyc_customer_type, selected_value: "Company - Private", authority: "PROJECT_DERIVED_POC", selection: documentSelection },
      client_segment: { ...unresolved.client_segment, selected_value: "Corporate", authority: "PROJECT_DERIVED_POC", selection: { ...documentSelection, field_key: "client_segment", value: "Corporate", document_evidence: { ...documentSelection.document_evidence, extracted_exact_value: "Corporate" } } },
    };
    const { view, onSubmit } = render(classification);
    expect(view.querySelector("form, select, button")).toBeNull();
    expect(view.textContent).toContain("Automatically classified from document");
    expect(view.textContent).toContain("synthetic-document · version 1 · event 8 · page 1");
    expect(view.textContent).toContain("LOCAL_TESSERACT_OCR");
    expect(view.textContent).not.toContain("Selected by user");
    expect(onSubmit).not.toHaveBeenCalled();
  });
  it("protects the safe automatic field and asks only for the unresolved segment", async () => {
    const { view, onSubmit } = render({ ...unresolved,
      kyc_customer_type: { ...unresolved.kyc_customer_type, selected_value: "Company - Private", authority: "PROJECT_DERIVED_POC", selection: documentSelection },
    });
    expect((view.querySelector('[aria-label="KYC customer type"]') as HTMLSelectElement).disabled).toBe(true);
    expect((view.querySelector('[aria-label="Client segment"]') as HTMLSelectElement).disabled).toBe(false);
    choose("Client segment", "Corporate");
    await act(async () => { view.querySelector("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })); });
    expect(onSubmit).toHaveBeenCalledWith({ kyc_customer_type: "Company - Private", client_segment: "Corporate" });
  });
});

it("replaces an unsaved local value when the authoritative field becomes automatic", async () => {
  const { view, onSubmit } = render({ ...unresolved,
    kyc_customer_type: { ...unresolved.kyc_customer_type, selected_value: "Company - Private" },
  });
  choose("KYC customer type", "Partnership - Regulated");
  const next = { ...unresolved,
    kyc_customer_type: { ...unresolved.kyc_customer_type, selected_value: "Company - Private", selection: documentSelection },
  };
  act(() => root?.render(<TargetClassificationPanel classification={next} disabled={false} onSubmit={onSubmit} />));
  expect((view.querySelector('[aria-label="KYC customer type"]') as HTMLSelectElement).value).toBe("Company - Private");
  choose("Client segment", "Corporate");
  await act(async () => { view.querySelector("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })); });
  expect(onSubmit).toHaveBeenCalledWith({ kyc_customer_type: "Company - Private", client_segment: "Corporate" });
});


describe("current classification evidence review", () => {
  it("shows the conflict and sends the exact displayed fingerprint for a same-value review", async () => {
    const fingerprint = "a".repeat(64);
    const { view, onSubmit } = render({
      ...unresolved, evidence_state: "CONFLICT", current: false, review_required: true,
      evidence_fingerprint: fingerprint,
      evidence_values: { kyc_customer_type: ["Company - Private", "Partnership - Unregulated"], client_segment: ["Corporate"] },
      kyc_customer_type: { ...unresolved.kyc_customer_type, selected_value: "Company - Private" },
      client_segment: { ...unresolved.client_segment, selected_value: "Corporate" },
    });
    expect(view.textContent).toContain("Target classification — conflicting evidence");
    expect(view.textContent).toContain("Company - Private; Partnership - Unregulated");
    await act(async () => { view.querySelector("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })); });
    expect(onSubmit).toHaveBeenCalledWith({
      kyc_customer_type: "Company - Private", client_segment: "Corporate",
      expected_classification_evidence_fingerprint: fingerprint,
    });
  });

  it("allows a stale automatic selection to be reviewed without unlocking a frozen case", () => {
    const stale = { ...unresolved, evidence_state: "CONFLICT" as const, current: false,
      kyc_customer_type: { ...unresolved.kyc_customer_type, selected_value: "Company - Private", selection: documentSelection },
      client_segment: { ...unresolved.client_segment, selected_value: "Corporate", selection: { ...documentSelection, field_key: "client_segment" as const, value: "Corporate" } },
    };
    const { view } = render(stale);
    expect(view.querySelector("form")).not.toBeNull();
    expect([...view.querySelectorAll("select")].every(select => !select.disabled)).toBe(true);
    act(() => root?.render(<TargetClassificationPanel classification={{ ...stale, editable: false }} disabled={false} onSubmit={vi.fn()} />));
    expect(view.querySelector("form, select")).toBeNull();
  });
});
