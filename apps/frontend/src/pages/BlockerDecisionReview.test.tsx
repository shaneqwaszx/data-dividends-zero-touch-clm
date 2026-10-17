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


it("bulk fills only undecided eligible document drafts, preserves corrections and notes, and confirms once", () => {
  const fetch = vi.spyOn(globalThis, "fetch"); const confirm = mount();
  const controls = Array.from(container.querySelectorAll<HTMLSelectElement>("select[data-review-field]"));
  choose(controls[0], "CORRECTED");
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
  act(() => { const correction = container.querySelector<HTMLInputElement>("input")!; setter.call(correction, "CORRECTED SYNTHETIC"); correction.dispatchEvent(new Event("input", { bubbles: true })); });
  const accept = button("Accept all eligible undecided suggestions"); expect(accept).toBeTruthy();
  act(() => { accept.click(); accept.click(); });
  expect(controls.map(item => item.value)).toEqual(["CORRECTED", "ACCEPTED", "ACCEPTED", "ACCEPTED"]);
  act(() => button("Reject all undecided suggestions").click());
  expect(controls.map(item => item.value)).toEqual(["CORRECTED", "ACCEPTED", "ACCEPTED", "ACCEPTED"]);
  expect(confirm).not.toHaveBeenCalled(); expect(fetch).not.toHaveBeenCalled();
  act(() => button("Confirm decisions & continue onboarding").click());
  expect(confirm).toHaveBeenCalledOnce();
  expect(confirm.mock.calls[0][0].documents[0].decisions[0]).toMatchObject({ decision: "CORRECTED", corrected_value: "CORRECTED SYNTHETIC" });
  expect(container.querySelectorAll(".blocker-review__cards > fieldset")).toHaveLength(4);
});

it("bulk skips missing suggestions and reviewed fields without expanding low-score acceptance semantics", () => {
  const confirm = mount();
  const partial = [{ ...documents[0], fields: documents[0].fields.map((field, index) => ({ ...field, original_extracted_value: index === 1 ? null : field.original_extracted_value, review_status: index === 3 ? "ACCEPTED" : field.review_status })) }] as DocumentProcessingRecord[];
  act(() => root!.render(<BlockerDecisionReview key="partial" summary={summary} documents={partial} busy={false} onConfirm={confirm} />));
  const accept = button("Accept all eligible undecided suggestions"); expect(accept).toBeTruthy();
  act(() => accept.click());
  expect(Array.from(container.querySelectorAll<HTMLSelectElement>("select[data-review-field]")).map(item => item.value)).toEqual(["ACCEPTED", "", "ACCEPTED"]);
  expect(container.textContent).toContain("2 filled · 1 skipped · 1 remaining");
  expect(button("Confirm decisions & continue onboarding").disabled).toBe(true);
  act(() => button("Reject all undecided suggestions").click());
  expect(confirm).not.toHaveBeenCalled();
  act(() => button("Confirm decisions & continue onboarding").click());
  expect(confirm.mock.calls[0][0].documents[0].decisions.map((item: { decision: string }) => item.decision)).toEqual(["ACCEPTED", "REJECTED", "ACCEPTED"]);
  expect(confirm.mock.calls[0][0].documents[0].expected_event_count).toBe(1);
});

it.each(["busy", "unauthorized"])("bulk cannot fill or confirm in %s state", state => {
  const confirm = mount();
  act(() => root!.render(<BlockerDecisionReview summary={{ ...summary, evidence_decision_authorized: state !== "unauthorized" }} documents={documents} busy={state === "busy"} onConfirm={confirm} />));
  for (const label of ["Accept all eligible undecided suggestions", "Reject all undecided suggestions"]) {
    expect(button(label).disabled).toBe(true); act(() => button(label).click());
  }
  expect(container.textContent).toContain("0 selected / 4 required"); expect(confirm).not.toHaveBeenCalled();
});

it("bulk preserves a note on an undecided field and source-family switching keeps drafts local", () => {
  const confirm = mount();
  const mixed = { ...summary, active_exceptions: [{ exception_id: "source-one" }], reconciliation: { version: 3, source_document_ids: ["synthetic-doc"], source_document_event_counts: [1], discrepancies: [{ discrepancy_id: "source-one", field_name: "registration_identifier", status: "OPEN", allowed_actions: ["KEEP_REGISTRY_VALUE"], evidence_fingerprint: "a".repeat(64), observations: [] }] } } as unknown as ZeroTouchCaseSummary;
  act(() => root!.render(<BlockerDecisionReview key="mixed" summary={mixed} documents={documents} busy={false} onConfirm={confirm} />));
  const group = container.querySelector<HTMLSelectElement>('select[aria-label="Decision group"]')!;
  choose(group, "source"); expect(button("Accept all eligible undecided suggestions")).toBeUndefined();
  choose(group, "document");
  const note = container.querySelector<HTMLInputElement>("input")!;
  act(() => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(note, "Retained optional synthetic note"); note.dispatchEvent(new Event("input", { bubbles: true })); });
  act(() => button("Accept all eligible undecided suggestions").click());
  choose(group, "source"); expect(button("Reject all undecided suggestions")).toBeUndefined();
  expect(container.querySelector<HTMLSelectElement>("select[data-discrepancy-id]")!.value).toBe("");
  choose(group, "document"); expect(container.querySelector<HTMLInputElement>("input")!.value).toBe("Retained optional synthetic note");
  expect(confirm).not.toHaveBeenCalled();
  act(() => button("Confirm decisions & continue onboarding").click());
  expect(confirm.mock.calls[0][0].documents[0].decisions[0].note).toBe("Retained optional synthetic note");
  expect(confirm.mock.calls[0][0].reconciliation).toBeUndefined();
});


it("invalidates only replaced evidence drafts and confirms with current version bindings", () => {
  const confirm = mount();
  const second = { ...documents[0], document_id: "second-doc", display_name: "second.pdf" };
  const pair = [documents[0], second];
  const render = (docs: DocumentProcessingRecord[], version: number) => act(() => root!.render(
    <BlockerDecisionReview summary={{ ...summary, version }} documents={docs} busy={false} onConfirm={confirm} />));
  render(pair, 1);
  const controls = () => [...container.querySelectorAll<HTMLSelectElement>("select[data-review-field]")];
  choose(controls()[0], "REJECTED"); choose(controls()[4], "ACCEPTED");
  render(pair.map(doc => ({ ...doc })), 2);
  expect(controls()[0].value).toBe("REJECTED"); expect(controls()[4].value).toBe("ACCEPTED");
  render([{ ...pair[0], review_source_fingerprint: "1".repeat(64) }, second], 3);
  expect(controls()[0].value).toBe(""); expect(controls()[4].value).toBe("ACCEPTED");
  expect(confirm).not.toHaveBeenCalled();
  act(() => button("Reject all undecided suggestions").click());
  act(() => button("Confirm decisions & continue onboarding").click());
  expect(confirm).toHaveBeenCalledOnce();
  expect(confirm.mock.calls[0][0]).toMatchObject({ expected_automation_version: 3, expected_case_event_count: 1,
    documents: [{ source_fingerprint: "1".repeat(64), expected_event_count: 1 }, { source_fingerprint: "0".repeat(64), expected_event_count: 1 }] });
});


it("keeps an explicitly selected source choice while bulk filling document drafts", () => {
  const confirm = mount();
  const mixed = { ...summary, active_exceptions: [{ exception_id: "source-one" }], reconciliation: { reconciliation_id: "current-source", version: 3,
    source_document_ids: ["synthetic-doc"], source_document_event_counts: [1], discrepancies: [{ discrepancy_id: "source-one", field_name: "legal_name", status: "OPEN",
      allowed_actions: ["KEEP_REGISTRY_VALUE", "USE_DOCUMENT_VALUE"], evidence_fingerprint: "a".repeat(64), observations: [] }] } } as unknown as ZeroTouchCaseSummary;
  act(() => root!.render(<BlockerDecisionReview key="explicit-source" summary={mixed} documents={documents} busy={false} onConfirm={confirm} />));
  const group = container.querySelector<HTMLSelectElement>('select[aria-label="Decision group"]')!;
  choose(group, "source"); choose(container.querySelector<HTMLSelectElement>("select[data-discrepancy-id]")!, "USE_DOCUMENT_VALUE");
  choose(group, "document"); act(() => button("Accept all eligible undecided suggestions").click());
  choose(group, "source");
  expect(container.querySelector<HTMLSelectElement>("select[data-discrepancy-id]")!.value).toBe("USE_DOCUMENT_VALUE");
  expect(confirm).not.toHaveBeenCalled();
  act(() => button("Confirm decisions & continue onboarding").click());
  expect(confirm).toHaveBeenCalledOnce();
  expect(confirm.mock.calls[0][0]).toEqual({ expected_automation_version: 1, expected_case_event_count: 1, expected_reconciliation_version: 3,
    reconciliation: [{ discrepancy_id: "source-one", action: "USE_DOCUMENT_VALUE", evidence_fingerprint: "a".repeat(64) }] });
});
