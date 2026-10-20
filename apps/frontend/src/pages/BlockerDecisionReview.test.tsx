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
function button(text: string) { return Array.from(container.querySelectorAll("button")).find(item => item.textContent === text)!; }
/** The radio for one document field decision. */
function radio(field: string, value: string, documentId = "synthetic-doc") {
  return container.querySelector<HTMLInputElement>(`input[type=radio][data-document-id="${documentId}"][data-review-field="${field}"][value="${value}"]`)!;
}
function pick(field: string, value: string, documentId = "synthetic-doc") { const item = radio(field, value, documentId); act(() => item.click()); return item; }
/** The explicit decision of every rendered document field, in order; "" when undecided. */
function values() {
  return Array.from(container.querySelectorAll<HTMLFieldSetElement>(".blocker-review__cards > fieldset")).map(set => (
    set.querySelector<HTMLInputElement>("input[type=radio][data-review-field]:checked")?.value ?? ""));
}
function sourceValue() { return container.querySelector<HTMLInputElement>("input[type=radio][data-discrepancy-id]:checked")?.value ?? ""; }
function type(label: string, value: string) {
  const element = container.querySelector<HTMLInputElement>(`input[aria-label="${label}"]`)
    ?? Array.from(container.querySelectorAll("label")).find(item => item.textContent?.startsWith(label))!.querySelector("input")!;
  act(() => { setter.call(element, value); element.dispatchEvent(new Event("input", { bubbles: true })); }); return element;
}
function note(field: string, value: string) {
  const add = container.querySelector<HTMLButtonElement>(`button[aria-label="Add note for ${field}"]`);
  if (add) act(() => add.click());
  return type(`Optional note for ${field}`, value);
}
function group() {
  const element = container.querySelector<HTMLSelectElement>('select[aria-label="Decision group"]')!;
  return (value: string) => act(() => { element.value = value; element.dispatchEvent(new Event("change", { bubbles: true })); });
}

it("starts with nothing decided and a disabled confirm", () => {
  const confirm = mount();
  expect(values()).toEqual(["", "", "", ""]);
  expect(container.querySelectorAll("input[type=radio]:checked")).toHaveLength(0);
  expect(container.textContent).toContain("0 selected / 4 required · 4 remaining");
  expect(container.textContent).toContain("Select all required decisions before confirming.");
  expect(button("Confirm decisions & continue onboarding").disabled).toBe(true);
  expect(button("Save draft in this tab").disabled).toBe(true);
  act(() => button("Confirm decisions & continue onboarding").click());
  expect(confirm).not.toHaveBeenCalled();
});

it("four local choices, changes, clearing and draft save never call confirmation or fetch", () => {
  const fetch = vi.spyOn(globalThis, "fetch"); const confirm = mount();
  for (const field of ["legal_name", "registration_number", "registered_address", "country_of_incorporation"]) {
    const control = radio(field, "ACCEPTED"); control.focus(); act(() => control.click());
    expect(document.activeElement).toBe(control); expect(control.disabled).toBe(false);
  }
  expect(values()).toEqual(["ACCEPTED", "ACCEPTED", "ACCEPTED", "ACCEPTED"]);
  expect(confirm).not.toHaveBeenCalled(); expect(fetch).not.toHaveBeenCalled();
  act(() => button("Save draft in this tab").click());
  expect(container.textContent).toContain("Draft saved in this tab");
  pick("legal_name", "REJECTED"); expect(container.textContent).toContain("Draft not saved");
  act(() => button("Confirm decisions & continue onboarding").click());
  expect(confirm).toHaveBeenCalledTimes(1);
  expect(confirm.mock.calls[0][0].documents[0].decisions).toHaveLength(4);
  expect(confirm.mock.calls[0][0].documents[0].decisions[0].decision).toBe("REJECTED");
  expect(fetch).not.toHaveBeenCalled();
  act(() => button("Clear draft").click());
  expect(values()).toEqual(["", "", "", ""]);
  expect(button("Confirm decisions & continue onboarding").disabled).toBe(true);
});

it("incomplete or unfilled correction cannot confirm, and a changed evidence key clears drafts", () => {
  const confirm = mount();
  pick("legal_name", "CORRECTED");
  for (const field of ["registration_number", "registered_address", "country_of_incorporation"]) pick(field, "ACCEPTED");
  expect(button("Confirm decisions & continue onboarding").disabled).toBe(true);
  expect(container.textContent).toContain("Enter each correction before confirming.");
  type("Correction for legal name", "CORRECTED SYNTHETIC");
  expect(button("Confirm decisions & continue onboarding").disabled).toBe(false);
  act(() => root!.render(<BlockerDecisionReview key="changed-evidence" summary={{ ...summary, version: 2 }} documents={documents} busy={false} onConfirm={confirm} />));
  expect(button("Confirm decisions & continue onboarding").disabled).toBe(true);
  expect(container.textContent).toContain("0 selected / 4 required");
  expect(confirm).not.toHaveBeenCalled();
});

it("typing a correction or clicking the correction box records an explicit correction", () => {
  const confirm = mount();
  type("Correction for legal name", "CORRECTED SYNTHETIC");
  expect(values()[0]).toBe("CORRECTED");
  act(() => container.querySelectorAll<HTMLElement>(".review-option--manual")[1].click());
  expect(values()[1]).toBe("CORRECTED");
  expect(document.activeElement?.getAttribute("aria-label")).toBe("Correction for registration number");
  for (const field of ["registration_number", "registered_address", "country_of_incorporation"]) pick(field, "ACCEPTED");
  act(() => button("Confirm decisions & continue onboarding").click());
  expect(confirm.mock.calls[0][0].documents[0].decisions[0]).toMatchObject({ decision: "CORRECTED", corrected_value: "CORRECTED SYNTHETIC" });
});

it("read-only actor cannot select or confirm", () => {
  mount(); act(() => root!.render(<BlockerDecisionReview summary={{ ...summary, evidence_decision_authorized: false }} documents={documents} busy={false} onConfirm={vi.fn()} />));
  expect(container.querySelectorAll("input").length).toBeGreaterThan(0);
  expect(Array.from(container.querySelectorAll("input")).every(item => item.disabled)).toBe(true);
  expect(button("Confirm decisions & continue onboarding").disabled).toBe(true);
});

it("a missing document suggestion cannot be accepted", () => {
  const confirm = mount();
  const missing = [{ ...documents[0], fields: documents[0].fields.map(field => ({ ...field, original_extracted_value: null })) }] as DocumentProcessingRecord[];
  act(() => root!.render(<BlockerDecisionReview key="missing" summary={summary} documents={missing} busy={false} onConfirm={confirm} />));
  const unavailable = radio("legal_name", "ACCEPTED");
  expect(unavailable.disabled).toBe(true);
  expect(unavailable.closest(".review-option")!.textContent).toContain("Not found in document");
  expect(radio("legal_name", "REJECTED").disabled).toBe(false);
  expect(confirm).not.toHaveBeenCalled();
});

it("source decisions display compared values and expose only backend-permitted actions", () => {
  const confirm = mount();
  const sourceSummary = { ...summary, active_exceptions: [{ exception_id: "source-one" }], reconciliation: { version: 3, source_document_ids: [], source_document_event_counts: [], discrepancies: [{ discrepancy_id: "source-one", field_name: "registration_identifier", status: "OPEN", allowed_actions: ["KEEP_REGISTRY_VALUE"], evidence_fingerprint: "a".repeat(64), observations: [{ source_kind: "REGISTRY", normalized_value: "202400001A" }, { source_kind: "DOCUMENT_IDP", normalized_value: "202400002B" }] }] } } as unknown as ZeroTouchCaseSummary;
  act(() => root!.render(<BlockerDecisionReview key="source" summary={sourceSummary} documents={[]} busy={false} onConfirm={confirm} />));
  expect(container.textContent).toContain("202400001A"); expect(container.textContent).toContain("202400002B");
  const options = Array.from(container.querySelectorAll<HTMLInputElement>("input[type=radio][data-discrepancy-id]"));
  expect(options.filter(item => !item.disabled).map(item => item.value)).toEqual(["KEEP_REGISTRY_VALUE"]);
  expect(sourceValue()).toBe("");
  expect(button("Confirm decisions & continue onboarding").disabled).toBe(true);
  act(() => options.find(item => item.value === "USE_DOCUMENT_VALUE")!.click());
  expect(sourceValue()).toBe("");
  act(() => options.find(item => item.value === "KEEP_REGISTRY_VALUE")!.click()); expect(confirm).not.toHaveBeenCalled();
  act(() => button("Confirm decisions & continue onboarding").click());
  expect(confirm.mock.calls[0][0].reconciliation[0].action).toBe("KEEP_REGISTRY_VALUE");
  expect(confirm.mock.calls[0][0].documents).toBeUndefined();
  act(() => root!.render(<BlockerDecisionReview key="changed-source" summary={{ ...sourceSummary,
    reconciliation: { ...sourceSummary.reconciliation!, source_document_ids: ["superseded-source"], source_document_event_counts: [1] },
  }} documents={documents} busy={false} onConfirm={confirm} />));
  expect(container.querySelector("input[data-reconciliation-field]")).toBeNull();
  expect(container.querySelector("input[data-review-field]")).not.toBeNull();
});

it("bulk fills only undecided eligible document drafts, preserves corrections and notes, and confirms once", () => {
  const fetch = vi.spyOn(globalThis, "fetch"); const confirm = mount();
  pick("legal_name", "CORRECTED");
  type("Correction for legal name", "CORRECTED SYNTHETIC");
  const accept = button("Accept all eligible undecided suggestions"); expect(accept).toBeTruthy();
  act(() => { accept.click(); accept.click(); });
  expect(values()).toEqual(["CORRECTED", "ACCEPTED", "ACCEPTED", "ACCEPTED"]);
  act(() => button("Reject all undecided suggestions").click());
  expect(values()).toEqual(["CORRECTED", "ACCEPTED", "ACCEPTED", "ACCEPTED"]);
  expect(confirm).not.toHaveBeenCalled(); expect(fetch).not.toHaveBeenCalled();
  act(() => button("Confirm decisions & continue onboarding").click());
  expect(confirm).toHaveBeenCalledOnce();
  expect(confirm.mock.calls[0][0].documents[0].decisions[0]).toMatchObject({ decision: "CORRECTED", corrected_value: "CORRECTED SYNTHETIC" });
  expect(container.querySelectorAll(".blocker-review__cards > fieldset")).toHaveLength(4);
});

it("bulk keeps an explicit reject when accepting the rest", () => {
  const confirm = mount();
  pick("registration_number", "REJECTED");
  act(() => button("Accept all eligible undecided suggestions").click());
  expect(values()).toEqual(["ACCEPTED", "REJECTED", "ACCEPTED", "ACCEPTED"]);
  expect(container.textContent).toContain("3 filled · 1 skipped · 0 remaining");
  act(() => button("Confirm decisions & continue onboarding").click());
  expect(confirm.mock.calls[0][0].documents[0].decisions.map((item: { decision: string }) => item.decision)).toEqual(["ACCEPTED", "REJECTED", "ACCEPTED", "ACCEPTED"]);
});

it("bulk skips missing suggestions and reviewed fields without expanding low-score acceptance semantics", () => {
  const confirm = mount();
  const partial = [{ ...documents[0], fields: documents[0].fields.map((field, index) => ({ ...field, original_extracted_value: index === 1 ? null : field.original_extracted_value, review_status: index === 3 ? "ACCEPTED" : field.review_status })) }] as DocumentProcessingRecord[];
  act(() => root!.render(<BlockerDecisionReview key="partial" summary={summary} documents={partial} busy={false} onConfirm={confirm} />));
  const accept = button("Accept all eligible undecided suggestions"); expect(accept).toBeTruthy();
  act(() => accept.click());
  expect(values()).toEqual(["ACCEPTED", "", "ACCEPTED"]);
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
  const choose = group();
  choose("source"); expect(button("Accept all eligible undecided suggestions")).toBeUndefined();
  choose("document");
  note("legal name", "Retained optional synthetic note");
  act(() => button("Accept all eligible undecided suggestions").click());
  choose("source"); expect(button("Reject all undecided suggestions")).toBeUndefined();
  expect(sourceValue()).toBe("");
  choose("document"); expect(container.querySelector<HTMLInputElement>(".review-item__note input")!.value).toBe("Retained optional synthetic note");
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
  pick("legal_name", "REJECTED"); pick("legal_name", "ACCEPTED", "second-doc");
  render(pair.map(doc => ({ ...doc })), 2);
  expect(values()[0]).toBe("REJECTED"); expect(values()[4]).toBe("ACCEPTED");
  render([{ ...pair[0], review_source_fingerprint: "1".repeat(64) }, second], 3);
  expect(values()[0]).toBe(""); expect(values()[4]).toBe("ACCEPTED");
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
  const choose = group();
  choose("source"); act(() => container.querySelector<HTMLInputElement>('input[data-discrepancy-id][value="USE_DOCUMENT_VALUE"]')!.click());
  choose("document"); act(() => button("Accept all eligible undecided suggestions").click());
  choose("source");
  expect(sourceValue()).toBe("USE_DOCUMENT_VALUE");
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
  const input = container.querySelector<HTMLInputElement>(".review-item__note input")!;
  expect(document.activeElement).toBe(input);
  expect(container.querySelector('button[aria-label="Add note for legal name"]')).toBeNull();
  expect(container.querySelector('button[aria-label="Add note for registration number"]')).not.toBeNull();
});

it("removing a note clears it and collapses the box", () => {
  const confirm = mount();
  note("legal name", "Draft note");
  act(() => container.querySelector<HTMLButtonElement>('button[aria-label="Remove note for legal name"]')!.click());
  expect(container.querySelector(".review-item__note")).toBeNull();
  expect(container.querySelector('button[aria-label="Add note for legal name"]')).not.toBeNull();
  act(() => button("Reject all undecided suggestions").click());
  act(() => button("Confirm decisions & continue onboarding").click());
  expect(confirm.mock.calls[0][0].documents[0].decisions[0]).not.toHaveProperty("note");
});
