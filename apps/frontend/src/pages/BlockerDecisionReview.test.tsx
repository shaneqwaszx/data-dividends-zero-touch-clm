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
const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
function radios(selector = "input[data-review-field]") { return Array.from(container.querySelectorAll<HTMLInputElement>(selector)); }
/** The checked backend value of each document field, in render order. */
function chosen(documentId?: string) {
  return radios(`input[data-review-field]:checked${documentId ? `[data-document-id="${documentId}"]` : ""}`).map(item => item.value);
}
function pick(field: string, value: string, documentId = "synthetic-doc") {
  const radio = container.querySelector<HTMLInputElement>(`input[data-document-id="${documentId}"][data-review-field="${field}"][value="${value}"]`)!;
  act(() => radio.click()); return radio;
}
function input(label: string) {
  // Note boxes stay collapsed until "Add note" is clicked.
  const addNote = label.startsWith("Optional note for ")
    && container.querySelector<HTMLButtonElement>(`button[aria-label="Add note for ${label.slice("Optional note for ".length)}"]`);
  if (addNote) act(() => addNote.click());
  return container.querySelector<HTMLInputElement>(`input[aria-label="${label}"]`)
    ?? Array.from(container.querySelectorAll("label")).find(item => item.textContent?.startsWith(label))!.querySelector("input")!;
}
function type(label: string, value: string) {
  const element = input(label);
  act(() => { setter.call(element, value); element.dispatchEvent(new Event("input", { bubbles: true })); }); return element;
}
function button(text: string) { return Array.from(container.querySelectorAll("button")).find(item => item.textContent === text)!; }
function group() {
  const element = container.querySelector<HTMLSelectElement>('select[aria-label="Decision group"]')!;
  return (value: string) => act(() => { element.value = value; element.dispatchEvent(new Event("change", { bubbles: true })); });
}

it("defaults every field to the registry value and keeps choices local until confirmation", () => {
  const fetch = vi.spyOn(globalThis, "fetch"); const confirm = mount();
  expect(container.querySelectorAll("select")).toHaveLength(0);
  expect(chosen()).toEqual(["REJECTED", "REJECTED", "REJECTED", "REJECTED"]);
  expect(container.textContent).toContain("4 of 4 decided · 4 registry value");
  expect(button("Confirm decisions & continue onboarding").disabled).toBe(false);
  const radio = pick("legal_name", "ACCEPTED"); radio.focus(); expect(document.activeElement).toBe(radio);
  expect(chosen()[0]).toBe("ACCEPTED");
  act(() => button("Save draft in this tab").click()); expect(container.textContent).toContain("Draft saved in this tab");
  pick("legal_name", "REJECTED"); expect(container.textContent).toContain("Draft not saved");
  expect(confirm).not.toHaveBeenCalled(); expect(fetch).not.toHaveBeenCalled();
  act(() => button("Confirm decisions & continue onboarding").click());
  expect(confirm).toHaveBeenCalledOnce();
  expect(confirm.mock.calls[0][0].documents[0].decisions.map((item: { decision: string }) => item.decision)).toEqual(["REJECTED", "REJECTED", "REJECTED", "REJECTED"]);
  expect(confirm.mock.calls[0][0].documents[0].decisions[0]).not.toHaveProperty("corrected_value");
  expect(fetch).not.toHaveBeenCalled();
});

it("typing in the manual box selects a correction and blank manual values cannot confirm", () => {
  const confirm = mount();
  act(() => input("Correction for legal name").focus());
  expect(chosen()[0]).toBe("CORRECTED");
  expect(button("Confirm decisions & continue onboarding").disabled).toBe(true);
  expect(container.textContent).toContain("Enter each correction before confirming.");
  type("Correction for legal name", "CORRECTED SYNTHETIC");
  expect(button("Confirm decisions & continue onboarding").disabled).toBe(false);
  act(() => button("Confirm decisions & continue onboarding").click());
  expect(confirm.mock.calls[0][0].documents[0].decisions[0]).toMatchObject({ decision: "CORRECTED", corrected_value: "CORRECTED SYNTHETIC" });
});

it("clicking the manual box selects it and switching away keeps the typed value for later", () => {
  mount();
  act(() => container.querySelector<HTMLElement>(".review-option--manual")!.click());
  expect(chosen()[0]).toBe("CORRECTED");
  expect(document.activeElement?.getAttribute("aria-label")).toBe("Correction for legal name");
  type("Correction for legal name", "KEPT VALUE");
  pick("legal_name", "REJECTED"); expect(chosen()[0]).toBe("REJECTED");
  pick("legal_name", "CORRECTED");
  expect(input("Correction for legal name").value).toBe("KEPT VALUE");
});

it("a changed evidence key resets drafts to the registry default", () => {
  const confirm = mount(); pick("legal_name", "ACCEPTED");
  act(() => root!.render(<BlockerDecisionReview key="changed-evidence" summary={{ ...summary, version: 2 }} documents={documents} busy={false} onConfirm={confirm} />));
  expect(chosen()).toEqual(["REJECTED", "REJECTED", "REJECTED", "REJECTED"]);
  expect(confirm).not.toHaveBeenCalled();
});

it("read-only actor cannot select or confirm", () => {
  mount(); act(() => root!.render(<BlockerDecisionReview summary={{ ...summary, evidence_decision_authorized: false }} documents={documents} busy={false} onConfirm={vi.fn()} />));
  expect(container.querySelectorAll("input").length).toBeGreaterThan(0);
  expect(Array.from(container.querySelectorAll("input")).every(item => item.disabled)).toBe(true);
  expect(button("Confirm decisions & continue onboarding").disabled).toBe(true);
});

it("offers registry, document and manual boxes and marks a missing document suggestion unavailable", () => {
  const confirm = mount();
  expect(radios('input[data-review-field="legal_name"]').map(item => item.value)).toEqual(["REJECTED", "ACCEPTED", "CORRECTED"]);
  expect(container.querySelector(".review-option.is-chosen")!.textContent).toContain("Registry value");
  const missing = [{ ...documents[0], fields: documents[0].fields.map(field => ({ ...field, original_extracted_value: null })) }] as DocumentProcessingRecord[];
  act(() => root!.render(<BlockerDecisionReview key="missing" summary={summary} documents={missing} busy={false} onConfirm={confirm} />));
  const unavailable = container.querySelector<HTMLInputElement>('input[data-review-field="legal_name"][value="ACCEPTED"]')!;
  expect(unavailable.disabled).toBe(true);
  expect(unavailable.closest(".review-option")!.textContent).toContain("Not found in document");
  expect(confirm).not.toHaveBeenCalled();
});

it("source decisions display compared values, default to the registry and expose only backend-permitted actions", () => {
  const confirm = mount();
  const sourceSummary = { ...summary, active_exceptions: [{ exception_id: "source-one" }], reconciliation: { version: 3, source_document_ids: [], source_document_event_counts: [], discrepancies: [{ discrepancy_id: "source-one", field_name: "registration_identifier", status: "OPEN", allowed_actions: ["KEEP_REGISTRY_VALUE"], evidence_fingerprint: "a".repeat(64), observations: [{ source_kind: "REGISTRY", normalized_value: "202400001A" }, { source_kind: "DOCUMENT_IDP", normalized_value: "202400002B" }] }] } } as unknown as ZeroTouchCaseSummary;
  act(() => root!.render(<BlockerDecisionReview key="source" summary={sourceSummary} documents={[]} busy={false} onConfirm={confirm} />));
  expect(container.textContent).toContain("202400001A"); expect(container.textContent).toContain("202400002B");
  const options = radios("input[data-discrepancy-id]");
  expect(options.map(item => [item.value, item.disabled])).toEqual([["KEEP_REGISTRY_VALUE", false], ["USE_DOCUMENT_VALUE", true]]);
  expect(options[0].checked).toBe(true); expect(confirm).not.toHaveBeenCalled();
  act(() => button("Confirm decisions & continue onboarding").click());
  expect(confirm.mock.calls[0][0].reconciliation[0].action).toBe("KEEP_REGISTRY_VALUE");
  expect(confirm.mock.calls[0][0].documents).toBeUndefined();
  act(() => root!.render(<BlockerDecisionReview key="changed-source" summary={{ ...sourceSummary,
    reconciliation: { ...sourceSummary.reconciliation!, source_document_ids: ["superseded-source"], source_document_event_counts: [1] },
  }} documents={documents} busy={false} onConfirm={confirm} />));
  expect(container.querySelector("input[data-reconciliation-field]")).toBeNull();
  expect(container.querySelector("input[data-review-field]")).not.toBeNull();
});

it("a source without a registry action must be chosen explicitly", () => {
  const confirm = mount();
  const sourceSummary = { ...summary, active_exceptions: [{ exception_id: "source-one" }], reconciliation: { version: 3, source_document_ids: [], source_document_event_counts: [], discrepancies: [{ discrepancy_id: "source-one", field_name: "legal_name", status: "OPEN", allowed_actions: ["USE_DOCUMENT_VALUE"], evidence_fingerprint: "a".repeat(64), observations: [] }] } } as unknown as ZeroTouchCaseSummary;
  act(() => root!.render(<BlockerDecisionReview key="document-only" summary={sourceSummary} documents={[]} busy={false} onConfirm={confirm} />));
  expect(button("Confirm decisions & continue onboarding").disabled).toBe(true);
  act(() => container.querySelector<HTMLInputElement>('input[value="USE_DOCUMENT_VALUE"]')!.click());
  act(() => button("Confirm decisions & continue onboarding").click());
  expect(confirm.mock.calls[0][0].reconciliation[0].action).toBe("USE_DOCUMENT_VALUE");
});

it("apply-to-all updates every field but keeps typed manual values and notes, and confirms once", () => {
  const fetch = vi.spyOn(globalThis, "fetch"); const confirm = mount();
  type("Correction for legal name", "CORRECTED SYNTHETIC");
  type("Optional note for registration number", "Retained optional synthetic note");
  act(() => { button("Use document suggestion for all").click(); button("Use document suggestion for all").click(); });
  expect(chosen()).toEqual(["CORRECTED", "ACCEPTED", "ACCEPTED", "ACCEPTED"]);
  expect(container.textContent).toContain("3 updated · 1 kept");
  act(() => button("Use registry value for all").click());
  expect(chosen()).toEqual(["CORRECTED", "REJECTED", "REJECTED", "REJECTED"]);
  expect(confirm).not.toHaveBeenCalled(); expect(fetch).not.toHaveBeenCalled();
  act(() => button("Confirm decisions & continue onboarding").click());
  expect(confirm).toHaveBeenCalledOnce();
  const decisions = confirm.mock.calls[0][0].documents[0].decisions;
  expect(decisions[0]).toMatchObject({ decision: "CORRECTED", corrected_value: "CORRECTED SYNTHETIC" });
  expect(decisions[1]).toMatchObject({ decision: "REJECTED", note: "Retained optional synthetic note" });
  expect(container.querySelectorAll(".blocker-review__cards > fieldset")).toHaveLength(4);
});

it("document suggestion for all skips missing suggestions and reviewed fields", () => {
  const confirm = mount();
  const partial = [{ ...documents[0], fields: documents[0].fields.map((field, index) => ({ ...field, original_extracted_value: index === 1 ? null : field.original_extracted_value, review_status: index === 3 ? "ACCEPTED" : field.review_status })) }] as DocumentProcessingRecord[];
  act(() => root!.render(<BlockerDecisionReview key="partial" summary={summary} documents={partial} busy={false} onConfirm={confirm} />));
  act(() => button("Use document suggestion for all").click());
  expect(chosen()).toEqual(["ACCEPTED", "REJECTED", "ACCEPTED"]);
  expect(container.textContent).toContain("2 updated · 1 kept");
  act(() => button("Confirm decisions & continue onboarding").click());
  expect(confirm.mock.calls[0][0].documents[0].decisions.map((item: { decision: string }) => item.decision)).toEqual(["ACCEPTED", "REJECTED", "ACCEPTED"]);
  expect(confirm.mock.calls[0][0].documents[0].expected_event_count).toBe(1);
});

it.each(["busy", "unauthorized"])("bulk cannot change or confirm in %s state", state => {
  const confirm = mount();
  act(() => root!.render(<BlockerDecisionReview summary={{ ...summary, evidence_decision_authorized: state !== "unauthorized" }} documents={documents} busy={state === "busy"} onConfirm={confirm} />));
  for (const label of ["Use document suggestion for all", "Use registry value for all"]) {
    expect(button(label).disabled).toBe(true); act(() => button(label).click());
  }
  expect(chosen()).toEqual(["REJECTED", "REJECTED", "REJECTED", "REJECTED"]);
  act(() => button("Confirm decisions & continue onboarding").click()); expect(confirm).not.toHaveBeenCalled();
});

it("source-family switching keeps drafts local and a note survives", () => {
  const confirm = mount();
  const mixed = { ...summary, active_exceptions: [{ exception_id: "source-one" }], reconciliation: { version: 3, source_document_ids: ["synthetic-doc"], source_document_event_counts: [1], discrepancies: [{ discrepancy_id: "source-one", field_name: "registration_identifier", status: "OPEN", allowed_actions: ["KEEP_REGISTRY_VALUE"], evidence_fingerprint: "a".repeat(64), observations: [] }] } } as unknown as ZeroTouchCaseSummary;
  act(() => root!.render(<BlockerDecisionReview key="mixed" summary={mixed} documents={documents} busy={false} onConfirm={confirm} />));
  const choose = group();
  choose("source"); expect(button("Use document suggestion for all")).toBeUndefined();
  choose("document"); type("Optional note for legal name", "Retained optional synthetic note");
  act(() => button("Use document suggestion for all").click());
  choose("source"); expect(container.querySelector<HTMLInputElement>("input[data-discrepancy-id]:checked")!.value).toBe("KEEP_REGISTRY_VALUE");
  choose("document"); expect(input("Optional note for legal name").value).toBe("Retained optional synthetic note");
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
  pick("legal_name", "ACCEPTED"); pick("legal_name", "ACCEPTED", "second-doc");
  render(pair.map(doc => ({ ...doc })), 2);
  expect(chosen("synthetic-doc")[0]).toBe("ACCEPTED"); expect(chosen("second-doc")[0]).toBe("ACCEPTED");
  render([{ ...pair[0], review_source_fingerprint: "1".repeat(64) }, second], 3);
  expect(chosen("synthetic-doc")[0]).toBe("REJECTED"); expect(chosen("second-doc")[0]).toBe("ACCEPTED");
  expect(confirm).not.toHaveBeenCalled();
  act(() => button("Confirm decisions & continue onboarding").click());
  expect(confirm).toHaveBeenCalledOnce();
  expect(confirm.mock.calls[0][0]).toMatchObject({ expected_automation_version: 3, expected_case_event_count: 1,
    documents: [{ source_fingerprint: "1".repeat(64), expected_event_count: 1 }, { source_fingerprint: "0".repeat(64), expected_event_count: 1 }] });
});

it("keeps an explicitly selected source choice while applying a document source to all", () => {
  const confirm = mount();
  const mixed = { ...summary, active_exceptions: [{ exception_id: "source-one" }], reconciliation: { reconciliation_id: "current-source", version: 3,
    source_document_ids: ["synthetic-doc"], source_document_event_counts: [1], discrepancies: [{ discrepancy_id: "source-one", field_name: "legal_name", status: "OPEN",
      allowed_actions: ["KEEP_REGISTRY_VALUE", "USE_DOCUMENT_VALUE"], evidence_fingerprint: "a".repeat(64), observations: [] }] } } as unknown as ZeroTouchCaseSummary;
  act(() => root!.render(<BlockerDecisionReview key="explicit-source" summary={mixed} documents={documents} busy={false} onConfirm={confirm} />));
  const choose = group();
  choose("source"); act(() => container.querySelector<HTMLInputElement>('input[value="USE_DOCUMENT_VALUE"]')!.click());
  choose("document"); act(() => button("Use document suggestion for all").click());
  choose("source");
  expect(container.querySelector<HTMLInputElement>("input[data-discrepancy-id]:checked")!.value).toBe("USE_DOCUMENT_VALUE");
  expect(confirm).not.toHaveBeenCalled();
  act(() => button("Confirm decisions & continue onboarding").click());
  expect(confirm).toHaveBeenCalledOnce();
  expect(confirm.mock.calls[0][0]).toEqual({ expected_automation_version: 1, expected_case_event_count: 1, expected_reconciliation_version: 3,
    reconciliation: [{ discrepancy_id: "source-one", action: "USE_DOCUMENT_VALUE", evidence_fingerprint: "a".repeat(64) }] });
});

it("keeps the note box collapsed until requested and open while a note exists", () => {
  mount();
  expect(Array.from(container.querySelectorAll("label")).some(item => item.textContent?.startsWith("Optional note for"))).toBe(false);
  const add = container.querySelector<HTMLButtonElement>('button[aria-label="Add note for legal name"]')!;
  act(() => add.click());
  const note = input("Optional note for legal name");
  expect(document.activeElement).toBe(note);
  expect(container.querySelector('button[aria-label="Add note for legal name"]')).toBeNull();
  expect(container.querySelector('button[aria-label="Add note for registration number"]')).not.toBeNull();
});

it("removing a note clears it and collapses the box", () => {
  const confirm = mount();
  type("Optional note for legal name", "Draft note");
  act(() => container.querySelector<HTMLButtonElement>('button[aria-label="Remove note for legal name"]')!.click());
  expect(container.querySelector('input[aria-label="Optional note for legal name"], .review-item__note')).toBeNull();
  expect(container.querySelector('button[aria-label="Add note for legal name"]')).not.toBeNull();
  act(() => button("Confirm decisions & continue onboarding").click());
  expect(confirm.mock.calls[0][0].documents[0].decisions[0]).not.toHaveProperty("note");
});
