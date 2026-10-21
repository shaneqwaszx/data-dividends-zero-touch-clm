// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import type { DocumentProcessingRecord, ZeroTouchCaseSummary } from "../types";
import BlockerDecisionReview, { followUpSourceDecisions } from "./BlockerDecisionReview";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root | undefined;
let container: HTMLDivElement;
afterEach(() => { act(() => root?.unmount()); container?.remove(); vi.restoreAllMocks(); });
const summary = { version: 1, case: { events: [{}], policy_snapshot: { idp_review_confidence_threshold: "0.85" } },
  active_exceptions: [{ exception_id: "synthetic-document-review", stage: "DOCUMENT", exception_type: "DOCUMENT_REVIEW_REQUIRED" }],
  evidence_decision_authorized: true } as unknown as ZeroTouchCaseSummary;
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
  pick("legal_name", "REGISTRY"); expect(container.textContent).toContain("Draft not saved");
  act(() => button("Confirm decisions & continue onboarding").click());
  expect(confirm).toHaveBeenCalledTimes(1);
  expect(confirm.mock.calls[0][0].documents[0].decisions).toHaveLength(4);
  // Registry choice is step one of two: the document value is accepted (it was read correctly), never rejected.
  expect(confirm.mock.calls[0][0].documents[0].decisions[0].decision).toBe("ACCEPTED");
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

it("tabbing through the correction box keeps an explicit choice and the enabled confirm", () => {
  const confirm = mount();
  for (const field of ["legal_name", "registration_number", "registered_address", "country_of_incorporation"]) pick(field, "ACCEPTED");
  expect(button("Confirm decisions & continue onboarding").disabled).toBe(false);
  for (const field of ["legal name", "registration number", "registered address", "country of incorporation"]) {
    const box = container.querySelector<HTMLInputElement>(`input[aria-label="Correction for ${field}"]`)!;
    act(() => box.focus()); expect(document.activeElement).toBe(box);
    act(() => box.blur());
  }
  expect(values()).toEqual(["ACCEPTED", "ACCEPTED", "ACCEPTED", "ACCEPTED"]);
  expect(container.textContent).not.toContain("Enter each correction before confirming.");
  expect(button("Confirm decisions & continue onboarding").disabled).toBe(false);
  act(() => button("Confirm decisions & continue onboarding").click());
  expect(confirm.mock.calls[0][0].documents[0].decisions.map((item: { decision: string }) => item.decision)).toEqual(["ACCEPTED", "ACCEPTED", "ACCEPTED", "ACCEPTED"]);
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
  // With no document value, only manual input remains: the registry route needs the document value accepted first.
  expect(radio("legal_name", "REGISTRY").disabled).toBe(true);
  expect(radio("legal_name", "CORRECTED").disabled).toBe(false);
  expect(confirm).not.toHaveBeenCalled();
});

it("source decisions display compared values and expose only backend-permitted actions", () => {
  const confirm = mount();
  const sourceSummary = { ...summary, active_exceptions: [...summary.active_exceptions, { exception_id: "source-one" }], reconciliation: { version: 3, source_document_ids: [], source_document_event_counts: [], discrepancies: [{ discrepancy_id: "source-one", field_name: "registration_identifier", status: "OPEN", allowed_actions: ["KEEP_REGISTRY_VALUE"], evidence_fingerprint: "a".repeat(64), observations: [{ source_kind: "REGISTRY", normalized_value: "202400001A" }, { source_kind: "DOCUMENT_IDP", normalized_value: "202400002B" }] }] } } as unknown as ZeroTouchCaseSummary;
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
  const accept = button("Use document suggestion for all undecided"); expect(accept).toBeTruthy();
  act(() => { accept.click(); accept.click(); });
  expect(values()).toEqual(["CORRECTED", "ACCEPTED", "ACCEPTED", "ACCEPTED"]);
  act(() => button("Use registry value for all undecided").click());
  expect(values()).toEqual(["CORRECTED", "ACCEPTED", "ACCEPTED", "ACCEPTED"]);
  expect(confirm).not.toHaveBeenCalled(); expect(fetch).not.toHaveBeenCalled();
  act(() => button("Confirm decisions & continue onboarding").click());
  expect(confirm).toHaveBeenCalledOnce();
  expect(confirm.mock.calls[0][0].documents[0].decisions[0]).toMatchObject({ decision: "CORRECTED", corrected_value: "CORRECTED SYNTHETIC" });
  expect(container.querySelectorAll(".blocker-review__cards > fieldset")).toHaveLength(4);
});

it("bulk keeps an explicit registry choice when accepting the rest", () => {
  const confirm = mount();
  pick("registration_number", "REGISTRY");
  act(() => button("Use document suggestion for all undecided").click());
  expect(values()).toEqual(["ACCEPTED", "REGISTRY", "ACCEPTED", "ACCEPTED"]);
  expect(container.textContent).toContain("3 filled · 1 skipped · 0 remaining");
  act(() => button("Confirm decisions & continue onboarding").click());
  expect(confirm.mock.calls[0][0].documents[0].decisions.map((item: { decision: string }) => item.decision)).toEqual(["ACCEPTED", "ACCEPTED", "ACCEPTED", "ACCEPTED"]);
});

it("bulk skips missing suggestions and reviewed fields without expanding low-score acceptance semantics", () => {
  const confirm = mount();
  const partial = [{ ...documents[0], fields: documents[0].fields.map((field, index) => ({ ...field, original_extracted_value: index === 1 ? null : field.original_extracted_value, review_status: index === 3 ? "ACCEPTED" : field.review_status })) }] as DocumentProcessingRecord[];
  act(() => root!.render(<BlockerDecisionReview key="partial" summary={summary} documents={partial} busy={false} onConfirm={confirm} />));
  const accept = button("Use document suggestion for all undecided"); expect(accept).toBeTruthy();
  act(() => accept.click());
  expect(values()).toEqual(["ACCEPTED", "", "ACCEPTED"]);
  expect(container.textContent).toContain("2 filled · 1 skipped · 1 remaining");
  expect(button("Confirm decisions & continue onboarding").disabled).toBe(true);
  // Registry bulk also skips the field with no document value; only manual input can complete it.
  act(() => button("Use registry value for all undecided").click());
  expect(values()).toEqual(["ACCEPTED", "", "ACCEPTED"]);
  type("Correction for registration number", "202400001A");
  expect(confirm).not.toHaveBeenCalled();
  act(() => button("Confirm decisions & continue onboarding").click());
  expect(confirm.mock.calls[0][0].documents[0].decisions.map((item: { decision: string }) => item.decision)).toEqual(["ACCEPTED", "CORRECTED", "ACCEPTED"]);
  expect(confirm.mock.calls[0][0].documents[0].expected_event_count).toBe(1);
});

it.each(["busy", "unauthorized"])("bulk cannot fill or confirm in %s state", state => {
  const confirm = mount();
  act(() => root!.render(<BlockerDecisionReview summary={{ ...summary, evidence_decision_authorized: state !== "unauthorized" }} documents={documents} busy={state === "busy"} onConfirm={confirm} />));
  for (const label of ["Use document suggestion for all undecided", "Use registry value for all undecided"]) {
    expect(button(label).disabled).toBe(true); act(() => button(label).click());
  }
  expect(container.textContent).toContain("0 selected / 4 required"); expect(confirm).not.toHaveBeenCalled();
});

it("with both decision kinds pending, shows only document field reviews (no group dropdown) and keeps notes", () => {
  const confirm = mount();
  const mixed = { ...summary, active_exceptions: [...summary.active_exceptions, { exception_id: "source-one" }], reconciliation: { version: 3, source_document_ids: ["synthetic-doc"], source_document_event_counts: [1], discrepancies: [{ discrepancy_id: "source-one", field_name: "registration_identifier", status: "OPEN", allowed_actions: ["KEEP_REGISTRY_VALUE"], evidence_fingerprint: "a".repeat(64), observations: [] }] } } as unknown as ZeroTouchCaseSummary;
  act(() => root!.render(<BlockerDecisionReview key="mixed" summary={mixed} documents={documents} busy={false} onConfirm={confirm} />));
  expect(container.querySelector('select[aria-label="Decision group"]')).toBeNull();
  expect(container.querySelector("input[data-discrepancy-id]")).toBeNull();
  note("legal name", "Retained optional synthetic note");
  act(() => button("Use document suggestion for all undecided").click());
  expect(container.querySelector<HTMLInputElement>(".review-item__note input")!.value).toBe("Retained optional synthetic note");
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
  pick("legal_name", "REGISTRY"); pick("legal_name", "ACCEPTED", "second-doc");
  render(pair.map(doc => ({ ...doc })), 2);
  expect(values()[0]).toBe("REGISTRY"); expect(values()[4]).toBe("ACCEPTED");
  render([{ ...pair[0], review_source_fingerprint: "1".repeat(64) }, second], 3);
  expect(values()[0]).toBe(""); expect(values()[4]).toBe("ACCEPTED");
  expect(confirm).not.toHaveBeenCalled();
  act(() => button("Use registry value for all undecided").click());
  act(() => button("Confirm decisions & continue onboarding").click());
  expect(confirm).toHaveBeenCalledOnce();
  expect(confirm.mock.calls[0][0]).toMatchObject({ expected_automation_version: 3, expected_case_event_count: 1,
    documents: [{ source_fingerprint: "1".repeat(64), expected_event_count: 1 }, { source_fingerprint: "0".repeat(64), expected_event_count: 1 }] });
});

it("shows registry-vs-document decisions once no document field review is pending", () => {
  const confirm = mount();
  // Only the source discrepancy is active: no document-stage field review remains.
  const sourceOnly = { ...summary, active_exceptions: [{ exception_id: "source-one" }], reconciliation: { reconciliation_id: "current-source", version: 3,
    source_document_ids: ["synthetic-doc"], source_document_event_counts: [1], discrepancies: [{ discrepancy_id: "source-one", field_name: "legal_name", status: "OPEN",
      allowed_actions: ["KEEP_REGISTRY_VALUE", "USE_DOCUMENT_VALUE"], evidence_fingerprint: "a".repeat(64), observations: [] }] } } as unknown as ZeroTouchCaseSummary;
  act(() => root!.render(<BlockerDecisionReview key="explicit-source" summary={sourceOnly} documents={documents} busy={false} onConfirm={confirm} />));
  expect(container.querySelector('select[aria-label="Decision group"]')).toBeNull();
  act(() => container.querySelector<HTMLInputElement>('input[data-discrepancy-id][value="USE_DOCUMENT_VALUE"]')!.click());
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
  act(() => button("Use registry value for all undecided").click());
  act(() => button("Confirm decisions & continue onboarding").click());
  expect(confirm.mock.calls[0][0].documents[0].decisions[0]).not.toHaveProperty("note");
});

it("hides stale pending field decisions once no document-stage issue is active", () => {
  mount();
  act(() => root!.render(<BlockerDecisionReview summary={{ ...summary, active_exceptions: [] }} documents={documents} busy={false} onConfirm={vi.fn()} />));
  expect(container!.querySelector(".blocker-review")).toBeNull();
  expect(container!.textContent).not.toContain("Confirm decisions & continue onboarding");
});

it("offers exactly three choices per document field: registry value, document suggestion, manual input", () => {
  mount();
  const card = container!.querySelector("fieldset.review-item")!;
  expect([...card.querySelectorAll(".review-option__label")].map(item => item.textContent!.trim()))
    .toEqual(["Use registry value", "Use document suggestion", "Enter manually"]);
});

it("a registry choice is sent as an accepted field, then pre-selects keep-registry in the next step for confirmation", () => {
  const confirm = mount();
  const caseSummary = { ...summary, case: { ...summary.case, case_id: "two-step-case" } } as unknown as ZeroTouchCaseSummary;
  act(() => root!.render(<BlockerDecisionReview key="step-one" summary={caseSummary} documents={documents} busy={false} onConfirm={confirm} />));
  pick("legal_name", "REGISTRY");
  for (const field of ["registration_number", "registered_address", "country_of_incorporation"]) pick(field, "ACCEPTED");
  act(() => button("Confirm decisions & continue onboarding").click());
  expect(confirm.mock.calls[0][0].documents[0].decisions[0]).toMatchObject({ field_key: "legal_name", decision: "ACCEPTED" });
  // Step two: only the registry-vs-document conflict is active.
  const stepTwo = { ...caseSummary, active_exceptions: [{ exception_id: "conflict-name" }], reconciliation: { reconciliation_id: "r2", version: 2,
    source_document_ids: ["synthetic-doc"], source_document_event_counts: [1], discrepancies: [{ discrepancy_id: "conflict-name", field_name: "legal_name", status: "OPEN",
      allowed_actions: ["KEEP_REGISTRY_VALUE", "USE_DOCUMENT_VALUE"], evidence_fingerprint: "b".repeat(64), observations: [] }] } } as unknown as ZeroTouchCaseSummary;
  act(() => root!.render(<BlockerDecisionReview key="step-two" summary={stepTwo} documents={documents} busy={false} onConfirm={confirm} />));
  expect(sourceValue()).toBe("KEEP_REGISTRY_VALUE");
  expect(container.textContent).toContain("Pre-selected from your choice in the previous step");
  expect(confirm).toHaveBeenCalledTimes(1);
  act(() => button("Confirm decisions & continue onboarding").click());
  expect(confirm.mock.calls[1][0].reconciliation).toEqual([{ discrepancy_id: "conflict-name", action: "KEEP_REGISTRY_VALUE", evidence_fingerprint: "b".repeat(64) }]);
});

it("registry-vs-document cards still list manual input, unavailable with a reason and a replacement path", () => {
  const confirm = mount();
  const onReplace = vi.fn();
  const sourceOnly = { ...summary, active_exceptions: [{ exception_id: "source-one" }], reconciliation: { reconciliation_id: "s", version: 3,
    source_document_ids: ["synthetic-doc"], source_document_event_counts: [1], discrepancies: [{ discrepancy_id: "source-one", field_name: "legal_name", status: "OPEN",
      allowed_actions: ["KEEP_REGISTRY_VALUE"], evidence_fingerprint: "a".repeat(64), observations: [] }] } } as unknown as ZeroTouchCaseSummary;
  act(() => root!.render(<BlockerDecisionReview key="manual-source" summary={sourceOnly} documents={documents} busy={false} onConfirm={confirm} onReplaceDocument={onReplace} />));
  const card = container.querySelector("fieldset.review-item")!;
  expect([...card.querySelectorAll(".review-option__label")].map(item => item.textContent!.trim())).toEqual(["Use registry value", "Use document value", "Enter manually"]);
  expect(card.textContent).toContain("Manual input is only available while reviewing the document fields.");
  act(() => button("Upload a replacement document to enter it manually").click());
  expect(onReplace).toHaveBeenCalledOnce(); expect(confirm).not.toHaveBeenCalled();
});

it("one Confirm can finish both steps: choices map to the follow-up registry-vs-document decisions only when all are permitted", () => {
  const confirm = mount();
  const caseSummary = { ...summary, case: { ...summary.case, case_id: "follow-up-case" } } as unknown as ZeroTouchCaseSummary;
  act(() => root!.render(<BlockerDecisionReview key="follow-one" summary={caseSummary} documents={documents} busy={false} onConfirm={confirm} />));
  pick("legal_name", "REGISTRY"); pick("registered_address", "ACCEPTED");
  pick("registration_number", "ACCEPTED"); pick("country_of_incorporation", "ACCEPTED");
  act(() => button("Confirm decisions & continue onboarding").click());
  const refreshed = (allowAddressDocument: boolean) => ({ ...caseSummary, version: 2,
    active_exceptions: [{ exception_id: "name" }, { exception_id: "address" }],
    reconciliation: { version: 5, discrepancies: [
      { discrepancy_id: "name", field_name: "legal_name", status: "OPEN", allowed_actions: ["KEEP_REGISTRY_VALUE", "USE_DOCUMENT_VALUE"], evidence_fingerprint: "n".repeat(64) },
      { discrepancy_id: "address", field_name: "registered_address", status: "OPEN", allowed_actions: allowAddressDocument ? ["KEEP_REGISTRY_VALUE", "USE_DOCUMENT_VALUE"] : ["KEEP_REGISTRY_VALUE"], evidence_fingerprint: "a".repeat(64) },
    ] } } as unknown as ZeroTouchCaseSummary);
  expect(followUpSourceDecisions(refreshed(true))).toEqual({ expected_automation_version: 2, expected_case_event_count: 1, expected_reconciliation_version: 5,
    reconciliation: [
      { discrepancy_id: "name", action: "KEEP_REGISTRY_VALUE", evidence_fingerprint: "n".repeat(64) },
      { discrepancy_id: "address", action: "USE_DOCUMENT_VALUE", evidence_fingerprint: "a".repeat(64) },
    ] });
  // A choice the backend does not permit for a field leaves the panel for the reviewer instead.
  expect(followUpSourceDecisions(refreshed(false))).toBeNull();
});
