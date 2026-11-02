// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { DocumentOwnershipObservation, DocumentProcessingRecord, ManualOwnershipReviewReceipt, OwnershipAnalysisRecord, OwnershipCandidate } from "../types";
import ManualOwnershipEvidenceForm, { exactPercentTotal, type ManualOwnershipEvidenceValues } from "./ManualOwnershipEvidenceForm";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

// Fictional XYZ ACCOUNTING (ACRA API Marketplace Mock sample record T19PF1111A).
const UEN = "T19PF1111A";
const NAME = "XYZ ACCOUNTING";
const FORM_ID = "11111111-1111-4111-8111-111111111111";
const AGREEMENT_ID = "22222222-2222-4222-8222-222222222222";
const COMPANY_DOC_ID = "44444444-4444-4444-8444-444444444444";

let root: Root | null = null;
let container: HTMLDivElement | null = null;

afterEach(() => {
  if (root) act(() => root?.unmount());
  container?.remove();
  root = null;
  container = null;
});

function row(index: number, name: string, percent: string, overrides: Partial<DocumentOwnershipObservation> = {}): DocumentOwnershipObservation {
  return {
    observation_id: `3333333${index}-3333-4333-8333-333333333333`, document_id: AGREEMENT_ID, document_version: 1,
    page_number: 1, source_reference: `PAGE_1_PARTNER_SHARE_ROW_${40 + index}`, evidence_score: 0.97,
    owner_name: name, owner_type: "NATURAL_PERSON", owner_registration_identifier: null, owned_entity_name: null,
    owned_entity_registration_identifier: UEN, share_count: null, explicit_percentage: percent,
    explicit_total_shares: null, share_class: null, as_of_date: "2020-01-02",
    extraction_quality: "HIGH", extraction_method: "NATIVE_PDF_TEXT", decision_state: "PROPOSED", ...overrides,
  };
}

function reviewed(id: string, name: string, rows: DocumentOwnershipObservation[]): DocumentProcessingRecord {
  return { document_id: id, display_name: name, state: "REVIEWED", superseded_by_document_id: null,
    events: [{ sequence: 1 }, { sequence: 2 }], ownership_observations: rows } as unknown as DocumentProcessingRecord;
}

const XYZ_ROWS = [row(1, "TAN WEI LING", "60"), row(2, "LILY", "40")];
const xyzDocuments = (rows = XYZ_ROWS) => [
  reviewed(FORM_ID, "xyz-accounting-onboarding-form.docx", []),
  reviewed(AGREEMENT_ID, "xyz-accounting-partnership-agreement.pdf", rows),
];

function render(documents = xyzDocuments(), extra: {
  onUploadEvidence?: (file: File) => void; disabled?: boolean;
  ownership?: OwnershipAnalysisRecord | null; partnershipState?: "AWAITING_RM_CONFIRMATION" | "RM_CONFIRMED" | null;
} = {}) {
  const onSubmit = vi.fn<(values: ManualOwnershipEvidenceValues) => void>();
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
  act(() => root?.render(<ManualOwnershipEvidenceForm canonicalRootUen={UEN} initialRootLegalName={NAME} legalFormLabel="Partnership"
    partnershipState={extra.partnershipState} documents={documents} ownership={extra.ownership ?? null}
    disabled={extra.disabled ?? false} onSubmit={onSubmit} onUploadEvidence={extra.onUploadEvidence} />));
  return { view: container, onSubmit };
}

const ROOT_ID = `ENTITY_${UEN}`;
/** The saved analysis and receipt the backend returns after the RM confirmed (as on a reload). */
function confirmedOwnership(shares: Array<[string, string, OwnershipCandidate["classification"]]> = [
  ["TAN WEI LING", "60", "PROVISIONAL_UBO_CANDIDATE"], ["LILY", "40", "PROVISIONAL_UBO_CANDIDATE"],
], receipt: Partial<ManualOwnershipReviewReceipt> = {}): OwnershipAnalysisRecord {
  const partners = shares.map(([name], index) => ({ party_id: `PARTNER_${index + 1}`, display_name: name,
    party_type: "NATURAL_PERSON" as const, registration_number: null, country: "SG" }));
  return {
    analysis_id: "analysis-xyz", version: 3, root_party_id: ROOT_ID, state: "ANALYZED",
    parties: [{ party_id: ROOT_ID, display_name: NAME, party_type: "LEGAL_ENTITY", registration_number: UEN, country: "SG" }, ...partners],
    relationships: shares.map(([, percent], index) => ({ relationship_id: `SHARE_${index + 1}`, parent_party_id: ROOT_ID,
      child_party_id: `PARTNER_${index + 1}`, ownership_percent: percent })),
    candidates: shares.map(([, percent, classification], index) => ({ party: partners[index], aggregated_ownership_percent: percent,
      threshold_percent: "25", classification })),
    threshold_percent: "25",
    manual_review_receipt: {
      case_id: "case-xyz", actor_id: "ethan-tan", reviewed_at: "2026-11-02T03:15:00Z",
      rationale: "Checked against the signed agreement dated 2 Jan 2020.",
      evidence_document_id: AGREEMENT_ID, evidence_document_version: 2, evidence_reference: "AGREEMENT",
      source_type: "USER_SUPPLIED_DECLARATION", source_selection: "DOCUMENT_OBSERVATIONS",
      observed_document_versions: [{ document_id: AGREEMENT_ID, event_count: 2 }],
      selected_observation_ids: XYZ_ROWS.slice(0, shares.length).map((item) => item.observation_id),
      provider_name: "MANUAL_DECLARATION_POC", provider_environment: "LOCAL", as_of_date: "2020-01-03", ...receipt,
    },
  } as unknown as OwnershipAnalysisRecord;
}

const q = <T extends Element>(view: HTMLElement, selector: string) => view.querySelector<T>(selector)!;
const box = (view: HTMLElement, label: string) => q<HTMLInputElement>(view, `input[aria-label="${label}"]`);
const button = (view: HTMLElement) => [...view.querySelectorAll("button")].find((item) => item.textContent === "Confirm partner shares")!;
const total = (view: HTMLElement) => q(view, '[data-testid="partner-shares-total"]');
const click = (element: HTMLElement) => act(() => element.click());
function setDate(view: HTMLElement, value: string) {
  const input = q<HTMLInputElement>(view, 'input[name="as_of_date"]');
  act(() => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set?.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}
const submit = (view: HTMLElement) => act(() => q(view, "form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));

describe("partnership mode: Confirm partner shares", () => {
  it("shows the title, summary and the agreement preselected with its date filled in and editable", () => {
    const { view } = render();
    expect(q(view, "h2").textContent).toBe("Confirm partner shares from the partnership agreement");
    expect(view.textContent).toContain("Partnership · shares from the agreement");
    expect(q(view, '[data-testid="partner-shares-summary"]').textContent).toBe(`${NAME}UEN ${UEN}Partnership`);
    expect(q<HTMLSelectElement>(view, 'select[aria-label="Partnership agreement"]').value).toBe(AGREEMENT_ID);
    const date = q<HTMLInputElement>(view, 'input[name="as_of_date"]');
    // The label is exactly the field name; the hint is linked by aria-describedby, not inside it.
    expect(date.closest("label")!.textContent).toBe("Agreement date (as-of date)");
    expect(date.getAttribute("aria-describedby")).toBe("partner-shares-date-hint");
    expect(date.value).toBe("2020-01-02");
    expect(date.readOnly).toBe(false);
    setDate(view, "2020-03-01");
    expect(date.value).toBe("2020-03-01");
    // The old mode's boxes are gone from this view.
    expect(view.querySelector('[name="source_selection"]')).toBeNull();
    expect(view.querySelector('[name="root_party_id"]')).toBeNull();
    expect(view.textContent).not.toContain("Declared ownership relationships");
    expect(view.textContent).not.toContain("On ACRA's partner list?");
  });

  it("lists each partner row with its share and where it was found, nothing ticked", () => {
    const { view } = render();
    expect(box(view, "Confirm TAN WEI LING at 60 percent").checked).toBe(false);
    expect(box(view, "Confirm LILY at 40 percent").checked).toBe(false);
    expect(view.textContent).toContain("Page 1 · PAGE_1_PARTNER_SHARE_ROW_41");
    expect(view.textContent).toContain("Page 1 · PAGE_1_PARTNER_SHARE_ROW_42");
  });

  it("moves through the three total states and their button reasons", () => {
    const { view } = render();
    expect(total(view).className).toContain("partner-shares__total--empty");
    expect(total(view).textContent).toContain("Nothing selected yet");
    expect(button(view).disabled).toBe(true);
    expect(view.textContent).toContain("Tick the partners whose shares you have checked.");

    click(box(view, "Confirm TAN WEI LING at 60 percent"));
    expect(total(view).textContent).toContain("Selected total: 60%");
    expect(total(view).textContent).toContain("Must add up to 100% for the partnership");
    expect(total(view).className).toContain("partner-shares__total--warn");
    expect(button(view).disabled).toBe(true);
    expect(view.textContent).toContain("Selected shares must add up to 100%.");

    click(box(view, "Confirm LILY at 40 percent"));
    expect(total(view).textContent).toContain("Selected total: 100%");
    expect(total(view).textContent).toContain("✓ Adds up to 100%");
    expect(total(view).className).toContain("partner-shares__total--ok");
    expect(button(view).disabled).toBe(false);
    expect(view.querySelector("#partner-shares-hint")).toBeNull();

    setDate(view, "");
    expect(button(view).disabled).toBe(true);
    expect(view.textContent).toContain("Add the agreement date to continue.");
  });

  it("select all ticks every partner and clears them again", () => {
    const { view } = render();
    const all = box(view, "Select all partners");
    click(all);
    expect(XYZ_ROWS.every((item) => box(view, `Confirm ${item.owner_name} at ${item.explicit_percentage} percent`).checked)).toBe(true);
    expect(all.checked).toBe(true);
    click(all);
    expect([...view.querySelectorAll<HTMLInputElement>('input[type="checkbox"]')].some((item) => item.checked)).toBe(false);
  });

  it("totals exact decimal strings without floating-point drift", () => {
    expect(exactPercentTotal(["33.333333", "66.666667"])).toEqual({ display: "100", exactly100: true });
    expect(exactPercentTotal(["0.1", "0.2"])).toEqual({ display: "0.3", exactly100: false });
    expect(exactPercentTotal([])).toEqual({ display: "0", exactly100: false });
    expect(exactPercentTotal(["60", "not a number"])).toBeNull();
    const { view } = render(xyzDocuments([row(1, "TAN WEI LING", "33.3"), row(2, "LILY", "66.7")]));
    click(box(view, "Select all partners"));
    expect(total(view).textContent).toContain("Selected total: 100%");
    expect(button(view).disabled).toBe(false);
  });

  it("submits the same document-observation decision as before, with the date shown", () => {
    const { view, onSubmit } = render();
    click(box(view, "Select all partners"));
    setDate(view, "2020-01-03");
    submit(view);
    expect(onSubmit).toHaveBeenCalledTimes(1);
    const values = onSubmit.mock.calls[0][0];
    expect(values).toMatchObject({
      evidence_document_id: AGREEMENT_ID, evidence_document_version: 2, source_selection: "DOCUMENT_OBSERVATIONS",
      observed_document_versions: [{ document_id: AGREEMENT_ID, event_count: 2 }],
      selected_observation_ids: XYZ_ROWS.map((item) => item.observation_id),
      as_of_date: "2020-01-03", rationale: null, root_party_id: `ROOT_${UEN}`, root_display_name: NAME,
    });
    expect(values.owners.map((owner) => [owner.display_name, owner.ownership_percent, owner.parent_party_id, owner.party_type]))
      .toEqual([["TAN WEI LING", "60", `ROOT_${UEN}`, "NATURAL_PERSON"], ["LILY", "40", `ROOT_${UEN}`, "NATURAL_PERSON"]]);
  });

  it("does not submit while the button reason applies", () => {
    const { view, onSubmit } = render();
    click(box(view, "Confirm TAN WEI LING at 60 percent"));
    expect(button(view).disabled).toBe(true);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("keeps every control disabled while the case is busy", () => {
    const { view } = render(xyzDocuments(), { disabled: true });
    expect([...view.querySelectorAll<HTMLInputElement | HTMLButtonElement | HTMLSelectElement | HTMLTextAreaElement>("input, button, select, textarea")]
      .every((item) => item.disabled)).toBe(true);
  });

  it("keeps the source, bindings, row references and fine print under Technical details", () => {
    const { view } = render();
    const details = q<HTMLDetailsElement>(view, "details.partner-shares__technical");
    expect(details.open).toBe(false);
    expect(details.textContent).toContain("MANUAL_DECLARATION_POC · DOCUMENT_OBSERVATIONS");
    expect(details.textContent).toContain(`Root legal-entity ID: ROOT_${UEN}`);
    expect(details.textContent).toContain(`${AGREEMENT_ID} · review revision 2`);
    expect(details.textContent).toContain("PAGE_1_PARTNER_SHARE_ROW_41 (TAN WEI LING) · HIGH · NATIVE_PDF_TEXT · score 0.97");
    expect(details.textContent).toContain("This declaration is not ACRA evidence");
  });

  it("hides the upload box until the RM chooses manual entry, which shows the old fields unchanged", () => {
    const { view } = render(xyzDocuments(), { onUploadEvidence: vi.fn() });
    expect(view.querySelector("#case-ownership-evidence-upload")).toBeNull();
    click([...view.querySelectorAll("button")].find((item) => item.textContent === "Shares not in the agreement? Enter them manually")!);
    expect(q(view, "h2").textContent).toBe("Review or edit ownership evidence");
    expect(q<HTMLSelectElement>(view, '[name="source_selection"]').value).toBe("USER_SUPPLIED_DECLARATION");
    expect(view.querySelector("#case-ownership-evidence-upload")).not.toBeNull();
    expect(view.textContent).toContain("Declared ownership relationships");
    expect([...view.querySelectorAll("button")].some((item) => item.textContent === "Add owner")).toBe(true);
    expect(view.textContent).toContain("Submit manual ownership evidence");
  });
});

describe("after the RM confirmed: Partner shares confirmed", () => {
  it("shows the saved confirmation read-only after a reload, from the receipt and analysis only", () => {
    const { view } = render(xyzDocuments(), { ownership: confirmedOwnership(), partnershipState: "RM_CONFIRMED" });
    expect(q(view, "h2").textContent).toBe("Partner shares confirmed");
    const facts = q(view, ".partner-shares__facts").textContent!;
    expect(facts).toContain("Confirmed byethan-tan");
    expect(facts).toContain("2 Nov 2026");
    expect(facts).toContain("11:15");
    expect(facts).toContain("xyz-accounting-partnership-agreement.pdf · review revision 2");
    expect(facts).toContain("Agreement date (as-of date)2020-01-03");
    const rows = [...view.querySelectorAll(".partner-shares__confirmed-table tbody tr")].map((item) => item.textContent);
    expect(rows).toEqual(["TAN WEI LING60%Yes", "LILY40%Yes"]);
    expect(q(view, ".partner-shares__confirmed-table thead").textContent).toContain("Provisional UBO (25% or more)");
    expect(q(view, ".partner-shares__confirmed-table tfoot").textContent).toContain("Total100%");
    expect(view.textContent).toContain("Checked against the signed agreement dated 2 Jan 2020.");
    // No editable form and no confirm button until the RM chooses to change the shares.
    expect(view.querySelectorAll('input[type="checkbox"]')).toHaveLength(0);
    expect([...view.querySelectorAll("button")].map((item) => item.textContent)).toEqual(["Change partner shares"]);
  });

  it("shows below-threshold partners as not provisional UBOs, and an empty note plainly", () => {
    const ownership = confirmedOwnership([["TAN WEI LING", "90", "PROVISIONAL_UBO_CANDIDATE"], ["LILY", "10", "BELOW_PROVISIONAL_THRESHOLD"]], { rationale: null });
    const { view } = render(xyzDocuments([row(1, "TAN WEI LING", "90"), row(2, "LILY", "10")]), { ownership, partnershipState: "RM_CONFIRMED" });
    expect([...view.querySelectorAll(".partner-shares__confirmed-table tbody tr")].map((item) => item.textContent))
      .toEqual(["TAN WEI LING90%Yes", "LILY10%No"]);
    expect(view.textContent).toContain("No note was added.");
  });

  it("Change partner shares reopens the form with the confirmed rows and date, and submits a new decision", () => {
    const { view, onSubmit } = render(xyzDocuments(), { ownership: confirmedOwnership(), partnershipState: "RM_CONFIRMED" });
    click([...view.querySelectorAll("button")].find((item) => item.textContent === "Change partner shares")!);
    expect(q(view, "h2").textContent).toBe("Confirm partner shares from the partnership agreement");
    expect(box(view, "Confirm TAN WEI LING at 60 percent").checked).toBe(true);
    expect(box(view, "Confirm LILY at 40 percent").checked).toBe(true);
    expect(q<HTMLInputElement>(view, 'input[name="as_of_date"]').value).toBe("2020-01-03");
    expect(total(view).textContent).toContain("Selected total: 100%");
    expect(button(view).disabled).toBe(false);
    submit(view);
    expect(onSubmit).toHaveBeenCalledTimes(1);
    const values = onSubmit.mock.calls[0][0];
    expect(values).toMatchObject({ source_selection: "DOCUMENT_OBSERVATIONS", evidence_document_id: AGREEMENT_ID,
      selected_observation_ids: XYZ_ROWS.map((item) => item.observation_id), as_of_date: "2020-01-03", root_party_id: ROOT_ID });
    expect(values.owners.map((owner) => [owner.party_id, owner.ownership_percent, owner.parent_party_id]))
      .toEqual([["PARTNER_1", "60", ROOT_ID], ["PARTNER_2", "40", ROOT_ID]]);
  });

  it("keeps the unconfirmed form unchanged while the backend still awaits the RM", () => {
    const awaiting = { ...confirmedOwnership(), state: "REVIEW_REQUIRED", relationships: [], candidates: [], manual_review_receipt: null } as unknown as OwnershipAnalysisRecord;
    const { view } = render(xyzDocuments(), { ownership: awaiting, partnershipState: "AWAITING_RM_CONFIRMATION" });
    expect(q(view, "h2").textContent).toBe("Confirm partner shares from the partnership agreement");
    expect([...view.querySelectorAll<HTMLInputElement>('input[type="checkbox"]')].some((item) => item.checked)).toBe(false);
    expect(total(view).textContent).toContain("Nothing selected yet");
  });

  it("does not show the summary without the backend's RM_CONFIRMED state or for a manual declaration", () => {
    const { view } = render(xyzDocuments(), { ownership: confirmedOwnership() });
    expect(q(view, "h2").textContent).toBe("Confirm partner shares from the partnership agreement");
    act(() => root?.unmount()); container?.remove(); root = null;
    const manual = confirmedOwnership(undefined, { source_selection: "USER_SUPPLIED_DECLARATION", selected_observation_ids: [] });
    const second = render(xyzDocuments(), { ownership: manual, partnershipState: "RM_CONFIRMED" }).view;
    expect(q(second, "h2").textContent).not.toBe("Partner shares confirmed");
  });
});

describe("other modes stay as they were", () => {
  it("company document observations keep the existing form", () => {
    const company = row(1, "SYNTHETIC HOLDINGS PTE. LTD.", "100", { source_reference: "PAGE_1_SHAREHOLDER_ROW_3", document_id: COMPANY_DOC_ID });
    const { view } = render([reviewed(COMPANY_DOC_ID, "register.pdf", [company])]);
    expect(q(view, "h2").textContent).toBe("Review or edit ownership evidence");
    expect(q<HTMLSelectElement>(view, '[name="source_selection"]').value).toBe("USER_SUPPLIED_DECLARATION");
    expect(view.querySelector(".partner-shares")).toBeNull();
  });

  it("documents without ownership rows keep the existing manual declaration", () => {
    const { view } = render([reviewed(FORM_ID, "garden.pdf", [])]);
    expect(q(view, "h2").textContent).toBe("Review or edit ownership evidence");
    expect(view.querySelector(".partner-shares")).toBeNull();
  });

  it("choosing a document without partner rows returns to the existing document-observation form", () => {
    const { view } = render();
    const select = q<HTMLSelectElement>(view, 'select[aria-label="Partnership agreement"]');
    act(() => {
      Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value")?.set?.call(select, FORM_ID);
      select.dispatchEvent(new Event("change", { bubbles: true }));
    });
    expect(q(view, "h2").textContent).toBe("Review or edit ownership evidence");
    expect(q<HTMLSelectElement>(view, '[name="source_selection"]').value).toBe("DOCUMENT_OBSERVATIONS");
    expect(q<HTMLSelectElement>(view, '[aria-label="Evidence document"]').value).toBe(FORM_ID);
  });
});
