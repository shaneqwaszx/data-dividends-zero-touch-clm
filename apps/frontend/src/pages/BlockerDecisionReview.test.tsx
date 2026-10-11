// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import type { DocumentProcessingRecord, ZeroTouchCaseSummary } from "../types";
import BlockerDecisionReview from "./BlockerDecisionReview";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root | undefined;
let container: HTMLDivElement;
afterEach(() => { act(() => root?.unmount()); container?.remove(); vi.restoreAllMocks(); });
const summary = { version: 1, case: { events: [{}], policy_snapshot: { idp_review_confidence_threshold: "0.85" } },
  active_exceptions: [], evidence_decision_authorized: true } as unknown as ZeroTouchCaseSummary;
const documents = [{ document_id: "synthetic-doc", display_name: "synthetic.pdf", state: "REVIEW_REQUIRED", events: [{}], review_source_fingerprint: "0".repeat(64),
  fields: ["legal_name", "registration_number", "registered_address", "country_of_incorporation"].map(field_key => ({ field_key, review_status: "PENDING", original_extracted_value: "SYNTHETIC", canonical_value: "SYNTHETIC", confidence: 0.6 })) }] as unknown as DocumentProcessingRecord[];
function mount(onConfirm = vi.fn()) {
  container = document.createElement("div"); document.body.append(container); root = createRoot(container);
  act(() => root!.render(<BlockerDecisionReview summary={summary} documents={documents} busy={false} onConfirm={onConfirm} />));
  return onConfirm;
}
function choose(select: HTMLSelectElement, value: string) { act(() => { select.value = value; select.dispatchEvent(new Event("change", { bubbles: true })); }); }
function button(text: string) { return Array.from(container.querySelectorAll("button")).find(item => item.textContent === text)!; }

it("four local choices, changes, clearing and draft save never call confirmation or fetch", () => {
  const fetch = vi.spyOn(globalThis, "fetch"); const confirm = mount();
  const controls = Array.from(container.querySelectorAll<HTMLSelectElement>("select[data-review-field]"));
  for (const control of controls) { control.focus(); choose(control, "ACCEPTED"); expect(document.activeElement).toBe(control); expect(control.disabled).toBe(false); }
  expect(confirm).not.toHaveBeenCalled(); expect(fetch).not.toHaveBeenCalled();
  act(() => button("Save draft in this tab").click());
  expect(container.textContent).toContain("Draft saved in this tab");
  choose(controls[0], "REJECTED"); expect(container.textContent).toContain("Draft not saved");
  act(() => button("Confirm decisions & continue onboarding").click());
  expect(confirm).toHaveBeenCalledTimes(1);
  expect(confirm.mock.calls[0][0].documents[0].decisions).toHaveLength(4);
  expect(confirm.mock.calls[0][0].documents[0].decisions[0].decision).toBe("REJECTED");
  expect(fetch).not.toHaveBeenCalled();
});

it("incomplete or unfilled correction cannot confirm, and a changed evidence key clears drafts", () => {
  const confirm = mount(); const controls = Array.from(container.querySelectorAll<HTMLSelectElement>("select[data-review-field]"));
  choose(controls[0], "CORRECTED"); for (const control of controls.slice(1)) choose(control, "ACCEPTED");
  expect(button("Confirm decisions & continue onboarding").disabled).toBe(true);
  const input = container.querySelector<HTMLInputElement>("input")!;
  act(() => { const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!; setter.call(input, "CORRECTED SYNTHETIC"); input.dispatchEvent(new Event("input", { bubbles: true })); });
  expect(button("Confirm decisions & continue onboarding").disabled).toBe(false);
  act(() => root!.render(<BlockerDecisionReview key="changed-evidence" summary={{ ...summary, version: 2 }} documents={documents} busy={false} onConfirm={confirm} />));
  expect(button("Confirm decisions & continue onboarding").disabled).toBe(true);
  expect(container.textContent).toContain("0 selected / 4 required");
  expect(confirm).not.toHaveBeenCalled();
});

it("read-only actor cannot select or confirm", () => {
  mount(); act(() => root!.render(<BlockerDecisionReview summary={{ ...summary, evidence_decision_authorized: false }} documents={documents} busy={false} onConfirm={vi.fn()} />));
  expect(Array.from(container.querySelectorAll("select")).every(item => item.disabled)).toBe(true);
  expect(button("Confirm decisions & continue onboarding").disabled).toBe(true);
});

it("source decisions display compared values and expose only backend-permitted actions", () => {
  const confirm = mount();
  const sourceSummary = { ...summary, active_exceptions: [{ exception_id: "source-one" }], reconciliation: { version: 3, source_document_ids: [], source_document_event_counts: [], discrepancies: [{ discrepancy_id: "source-one", field_name: "registration_identifier", status: "OPEN", allowed_actions: ["KEEP_REGISTRY_VALUE"], evidence_fingerprint: "a".repeat(64), observations: [{ source_kind: "REGISTRY", normalized_value: "202400001A" }, { source_kind: "DOCUMENT_IDP", normalized_value: "202400002B" }] }] } } as unknown as ZeroTouchCaseSummary;
  act(() => root!.render(<BlockerDecisionReview key="source" summary={sourceSummary} documents={[]} busy={false} onConfirm={confirm} />));
  expect(container.textContent).toContain("202400001A"); expect(container.textContent).toContain("202400002B");
  const control = container.querySelector<HTMLSelectElement>("select[data-discrepancy-id]")!;
  expect(Array.from(control.options).map(item => item.value)).toEqual(["", "KEEP_REGISTRY_VALUE"]);
  choose(control, "KEEP_REGISTRY_VALUE"); expect(confirm).not.toHaveBeenCalled();
  act(() => button("Confirm decisions & continue onboarding").click());
  expect(confirm.mock.calls[0][0].reconciliation[0].action).toBe("KEEP_REGISTRY_VALUE");
  expect(confirm.mock.calls[0][0].documents).toBeUndefined();
  act(() => root!.render(<BlockerDecisionReview key="changed-source" summary={{ ...sourceSummary,
    reconciliation: { ...sourceSummary.reconciliation!, source_document_ids: ["superseded-source"], source_document_event_counts: [1] },
  }} documents={documents} busy={false} onConfirm={confirm} />));
  expect(container.querySelector("select[data-reconciliation-field]")).toBeNull();
  expect(container.querySelector("select[data-review-field]")).not.toBeNull();
});
