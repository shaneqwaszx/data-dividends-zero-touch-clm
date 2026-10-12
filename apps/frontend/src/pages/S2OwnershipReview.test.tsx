// @vitest-environment jsdom
import { act, type ReactNode } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { DocumentOwnershipObservation, DocumentProcessingRecord, OwnershipAnalysisRecord, OwnershipParty, ZeroTouchCaseSummary } from "../types";
import ManualOwnershipEvidenceForm, { ownersFromDocumentObservations } from "./ManualOwnershipEvidenceForm";
import DocumentEvidencePanel from "./DocumentEvidencePanel";
import OwnershipPathExplorer from "./OwnershipPathExplorer";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
const rootParty: OwnershipParty = { party_id: "ROOT", display_name: "Synthetic root", party_type: "LEGAL_ENTITY", registration_number: "202400001A", country: "SG" };
const holding: OwnershipParty = { party_id: "HOLDING", display_name: "Synthetic holding", party_type: "LEGAL_ENTITY", registration_number: "202400002B", country: "SG" };
const owner: OwnershipParty = { party_id: "PERSON", display_name: "Synthetic person", party_type: "NATURAL_PERSON", registration_number: null, country: "GB" };
function analysis(): OwnershipAnalysisRecord {
  return { case_id: "case-1", version: 5, analysis_id: "analysis-1", correlation_id: "correlation", root_party_id: "ROOT", provider_name: "ACRA_REGISTRY_ACQUISITION", provider_environment: "MOCK", state: "ANALYZED", parties: [rootParty, owner, holding],
    relationships: [{ relationship_id: "ROOT_HOLDING", parent_party_id: "ROOT", child_party_id: "HOLDING", ownership_percent: "100", relationship_type: "OWNERSHIP", basis: "SHARE_OWNERSHIP", provenance: { provider: "OFFICIAL_MOCK", environment: "MOCK", sourced_at: "2026-10-04T00:00:00Z" } },
      { relationship_id: "HOLDING_PERSON", parent_party_id: "HOLDING", child_party_id: "PERSON", ownership_percent: "100", relationship_type: "OWNERSHIP", basis: "SHARE_OWNERSHIP", provenance: { provider: "LOCAL_SYNTHETIC_SUPPLEMENT", environment: "LOCAL", sourced_at: "2026-10-04T00:00:00Z" } }],
    candidates: [{ party: owner, direct_ownership_percent: "0", indirect_ownership_percent: "100.000000000000000000", aggregated_ownership_percent: "100.000000000000000000", threshold_percent: "25", threshold_comparator: "GREATER_THAN_OR_EQUAL_TO", threshold_result: "MET", classification: "PROVISIONAL_UBO_CANDIDATE", paths: [{ path_id: "path-1", edges: [], effective_ownership_percent: "100.000000000000000000", is_direct: false, calculation: "100 × 100 / 100 = 100.000000000000000000" }] }],
    issues: [], threshold_percent: "25", threshold_comparator: "GREATER_THAN_OR_EQUAL_TO", events: [], error: null, created_at: "now", loaded_at: "now", analyzed_at: "now", updated_at: "now" };
}
function observation(overrides: Partial<DocumentOwnershipObservation> = {}): DocumentOwnershipObservation {
  return { observation_id: "00000000-0000-4000-8000-000000000301", document_id: "00000000-0000-4000-8000-000000000201", document_version: 1, page_number: 2, source_reference: "PAGE_2_ROW_1", extraction_method: "LOCAL_TESSERACT_OCR", extraction_quality: "HIGH", evidence_score: 0.91,
    owner_name: owner.display_name, owner_type: "NATURAL_PERSON", owner_registration_identifier: null, owned_entity_name: holding.display_name, owned_entity_registration_identifier: holding.registration_number,
    share_count: "300", explicit_percentage: "100", explicit_total_shares: null, share_class: "ORDINARY", as_of_date: "2026-10-03", decision_state: "PROPOSED", ...overrides };
}
function document(observations: DocumentOwnershipObservation[] = []): DocumentProcessingRecord {
  return { document_id: "00000000-0000-4000-8000-000000000201", document_version: 1, display_name: "Synthetic declaration.pdf", state: "REVIEWED", provider_environment: "LOCAL", superseded_by_document_id: null, ownership_observations: observations,
    fields: [{ field_key: "legal_name", original_extracted_value: "DOCUMENT NAME", normalized_value: "DOCUMENT NAME", canonical_value: "REGISTRY NAME", comparison_status: "MISMATCH", review_status: "PENDING", confidence: 0.97,
      provenance: { provider: "LOCAL_IDP", environment: "LOCAL", page_number: 2, source_reference: "PAGE_2" }, reviewed_value: null, reviewed_at: null, review_note: null }], events: [{ sequence: 1 }, { sequence: 2 }, { sequence: 3 }] } as DocumentProcessingRecord;
}
let root: Root | null = null;
let container: HTMLDivElement;
afterEach(() => { if (root) act(() => root?.unmount()); container?.remove(); root = null; });
function render(node: ReactNode) { container = window.document.createElement("div"); window.document.body.append(container); root = createRoot(container); act(() => root!.render(node)); return container; }
function input(name: string, value: string) {
  const element = container.querySelector<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>(`[name="${name}"]`)!;
  const prototype = element instanceof HTMLSelectElement ? HTMLSelectElement.prototype : element instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  act(() => { Object.getOwnPropertyDescriptor(prototype, "value")!.set!.call(element, value); element.dispatchEvent(new Event(element instanceof HTMLSelectElement ? "change" : "input", { bubbles: true })); });
}
function submit() { act(() => container.querySelector("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }))); }
function form(onSubmit = vi.fn(), value: OwnershipAnalysisRecord | null = analysis(), docs = [document()]) {
  render(<ManualOwnershipEvidenceForm canonicalRootUen="202400001A" initialRootLegalName="Synthetic root" ownership={value} documents={docs} disabled={false} onSubmit={onSubmit} />); return onSubmit;
}
function panel(value: DocumentProcessingRecord, authorized: boolean | undefined) {
  return render(<DocumentEvidencePanel summary={{ evidence_decision_authorized: authorized, status: "WAITING_FOR_REVIEW", current_stage: "DOCUMENT", timeline: [], case: {} } as unknown as ZeroTouchCaseSummary} documents={[value]} busy={false} busyLabel={null} mutationBlocked={false} onReview={vi.fn()} onReplace={vi.fn()} onRetry={vi.fn()} onContinue={vi.fn()} onRefresh={vi.fn()} />);
}

describe("Session 2 source-bound ownership decisions", () => {
  it("leaves invented shares, percentages, types, countries and dates out of blank declarations", () => {
    form(vi.fn(), null);
    for (const name of ["ownership_percent_0", "ownership_percent_1", "party_type_0", "country_0", "as_of_date"]) expect(container.querySelector<HTMLInputElement>(`[name="${name}"]`)!.value).toBe("");
    expect(container.querySelector('input[type="file"]')).toBeNull();
  });
  it("prefills explicit multi-level direct relationships and retains current party order for keep-current", () => {
    const onSubmit = form(); input("source_selection", "CURRENT_EVIDENCE"); input("rationale", "Keep independently labelled current evidence after comparison."); input("as_of_date", "2026-10-04");
    expect(container.querySelector<HTMLInputElement>('[name="parent_party_id_1"]')!.value).toBe("HOLDING");
    expect(container.querySelector<HTMLInputElement>('[name="ownership_percent_0"]')!.disabled).toBe(true);
    submit(); expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ source_selection: "CURRENT_EVIDENCE", parties: analysis().parties,
      owners: [expect.objectContaining({ parent_party_id: "ROOT", party_id: "HOLDING", ownership_percent: "100" }), expect.objectContaining({ parent_party_id: "HOLDING", party_id: "PERSON", ownership_percent: "100" })] }));
  });
  it.each([false, true])("keeps an exact partial current graph including multiple paths (%s)", (multiplePaths) => {
    const value = analysis(); value.relationships[0].ownership_percent = "40";
    value.relationships[1].ownership_percent = "75";
    if (multiplePaths) value.relationships.push({ ...value.relationships[0], relationship_id: "ROOT_PERSON", child_party_id: "PERSON", ownership_percent: "20" });
    const onSubmit = form(vi.fn(), value); input("source_selection", "CURRENT_EVIDENCE");
    input("rationale", "Retain exact partial evidence without inventing absent ownership."); input("as_of_date", "2026-10-04");
    for (const control of container.querySelectorAll<HTMLInputElement>('[name^="ownership_percent_"]')) expect(control.disabled).toBe(true);
    submit(); expect(onSubmit).toHaveBeenCalledOnce();
    expect(onSubmit.mock.calls[0][0]).toMatchObject({ source_selection: "CURRENT_EVIDENCE", parties: value.parties,
      owners: value.relationships.map((edge) => ({ relationship_id: edge.relationship_id, parent_party_id: edge.parent_party_id, party_id: edge.child_party_id, ownership_percent: edge.ownership_percent })) });
    input("source_selection", "USER_SUPPLIED_DECLARATION"); onSubmit.mockClear(); submit();
    expect(onSubmit).not.toHaveBeenCalled(); expect(container.textContent).toContain("must total exactly 100");
  });
  it("edits calculable multi-level graph while preserving explicit parent bindings", () => {
    const onSubmit = form(); input("rationale", "Reviewed current multi-level declaration and retained explicit quantities."); input("as_of_date", "2026-10-04");
    input("display_name_1", "Reviewed synthetic person"); submit();
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ source_selection: "USER_SUPPLIED_DECLARATION", owners: expect.arrayContaining([expect.objectContaining({ parent_party_id: "HOLDING", party_id: "PERSON", display_name: "Reviewed synthetic person" })]) }));
  });
  it("binds every current observation document revision and selected immutable observation", () => {
    const obs = observation({ owned_entity_name: rootParty.display_name, owned_entity_registration_identifier: rootParty.registration_number });
    const docs = [document([obs]), { ...document(), document_id: "00000000-0000-4000-8000-000000000202", ownership_observations: [observation({ observation_id: "00000000-0000-4000-8000-000000000302", document_id: "00000000-0000-4000-8000-000000000202" })], events: [{ sequence: 1 }] } as DocumentProcessingRecord,
      { ...document([observation()]), document_id: "historical", superseded_by_document_id: "replacement" }];
    const onSubmit = form(vi.fn(), analysis(), docs); input("source_selection", "DOCUMENT_OBSERVATIONS");
    const checkbox = container.querySelector<HTMLInputElement>('input[type="checkbox"]')!; act(() => checkbox.click());
    expect(container.querySelector<HTMLInputElement>('[name="ownership_percent_0"]')!.value).toBe("100");
    input("rationale", "Selected the explicit current source observation after comparison."); input("as_of_date", "2026-10-04"); submit();
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ source_selection: "DOCUMENT_OBSERVATIONS", selected_observation_ids: [obs.observation_id], observed_document_versions: [{ document_id: docs[0].document_id, event_count: 3 }, { document_id: docs[1].document_id, event_count: 1 }] }));
  });
  it("keeps chosen document values read-only until a manual declaration is deliberately selected", () => {
    form(vi.fn(), analysis(), [document([observation({ owned_entity_name: rootParty.display_name, owned_entity_registration_identifier: rootParty.registration_number })])]);
    input("source_selection", "DOCUMENT_OBSERVATIONS"); act(() => container.querySelector<HTMLInputElement>('input[type="checkbox"]')!.click());
    expect(container.querySelector<HTMLInputElement>('[name="ownership_percent_0"]')!.disabled).toBe(true);
    expect([...container.querySelectorAll("button")].find((button) => button.textContent === "Add owner")!.disabled).toBe(true);
    input("source_selection", "USER_SUPPLIED_DECLARATION");
    expect(container.querySelector<HTMLInputElement>('[name="ownership_percent_0"]')!.disabled).toBe(false);
  });
  it("never converts share rows into percentage defaults even with an explicit denominator", () => {
    const drafts = ownersFromDocumentObservations([observation({ explicit_percentage: null, explicit_total_shares: "300" })], analysis().parties);
    expect(drafts[0].ownership_percent).toBe("");
    expect(ownersFromDocumentObservations([observation({ owner_type: null, owned_entity_name: null, owned_entity_registration_identifier: null })], analysis().parties)[0]).toMatchObject({ party_type: "", parent_party_id: "" });
  });
  it("checks each declared owned entity rather than adding all levels to one total", () => {
    const onSubmit = form(); input("ownership_percent_1", "99.999999"); input("rationale", "Reviewed values against current evidence."); input("as_of_date", "2026-10-04"); submit();
    expect(onSubmit).not.toHaveBeenCalled(); expect(container.textContent).toContain("for each owned entity must total exactly 100");
  });
  it("accepts a person reached by multiple explicit paths with one consistent party record", () => {
    const value = analysis(); value.relationships[0].ownership_percent = "50";
    value.relationships.push({ ...value.relationships[0], relationship_id: "ROOT_PERSON", child_party_id: "PERSON", ownership_percent: "50" });
    const onSubmit = form(vi.fn(), value); input("rationale", "Retain multiple explicit paths to the same person after review."); input("as_of_date", "2026-10-04"); submit();
    expect(onSubmit).toHaveBeenCalledOnce(); expect(onSubmit.mock.calls[0][0].parties.filter((party: OwnershipParty) => party.party_id === "PERSON")).toHaveLength(1);
  });
});

describe("Session 2 extraction and verification meanings", () => {
  it("shows high-quality conflicting evidence separately from agreement and pending verification", () => {
    const value = document(); value.state = "REVIEW_REQUIRED";
    Object.assign(value.fields[0], { extraction_quality: "HIGH", extraction_method: "LOCAL_TESSERACT_OCR", score_kind: "DETERMINISTIC_EVIDENCE_SCORE", score_formula: "LABEL_SCORE_TIMES_OCR_MEAN_OVER_100", raw_ocr_mean_confidence: 94.125, raw_ocr_word_count: 24 });
    const view = panel(value, true); expect(view.textContent).toContain("HIGH"); expect(view.textContent).toContain("MISMATCH"); expect(view.textContent).toContain("PENDING");
    expect(view.textContent).toContain("0.97"); expect(view.textContent).not.toContain("97%"); expect(view.textContent).toContain("not a probability"); expect(view.textContent).toContain("94.125"); expect(view.textContent).toContain("Raw OCR word count24"); expect(view.textContent).toContain("LABEL_SCORE_TIMES_OCR_MEAN_OVER_100");
  });
  it("keeps historical unspecified extraction metadata UNKNOWN", () => {
    const view = panel(document(), true); expect(view.textContent).toContain("Extraction qualityUNKNOWN"); expect(view.textContent).toContain("Extraction methodUNKNOWN"); expect(view.textContent).toContain("LEGACY_UNSPECIFIED");
  });
  it("retains page-local ambiguous candidates, page metadata and immutable proposed ownership", () => {
    const value = document([observation({ explicit_percentage: null })]);
    value.fields[0].candidates = [{ value: "PAGE ONE NAME", page_number: 1, source_reference: "PAGE_1", extraction_quality: "HIGH", extraction_method: "NATIVE_PDF_TEXT" }, { value: "PAGE TWO NAME", page_number: 2, source_reference: "PAGE_2", extraction_quality: "AMBIGUOUS", extraction_method: "LOCAL_TESSERACT_OCR" }];
    value.pages = [{ page_number: 2, source_reference: "PAGE_2", extraction_quality: "HIGH", extraction_method: "LOCAL_TESSERACT_OCR" }];
    const view = panel(value, true); expect(view.textContent).toContain("PAGE ONE NAME"); expect(view.textContent).toContain("PAGE TWO NAME"); expect(view.textContent).toContain("AMBIGUOUS"); expect(view.textContent).toContain("document version 1"); expect(view.textContent).toContain("PAGE_2_ROW_1"); expect(view.textContent).toContain("PROPOSED"); expect(view.textContent).toContain("Not supplied — no percentage inferred");
  });
  it.each([false, undefined])("keeps all decision and upload controls read-only without a true backend capability (%s)", (authorized) => {
    const value = document(); value.state = "REVIEW_REQUIRED"; const view = panel(value, authorized);
    for (const control of view.querySelectorAll<HTMLInputElement | HTMLButtonElement>("button,input[type=file]")) expect(control.disabled).toBe(true);
  });
  it("accepts bounded image media in existing native upload controls", () => {
    const view = panel(document(), true); expect(view.querySelector<HTMLInputElement>('input[type="file"]')!.accept).toContain("image/tiff"); expect(view.querySelector<HTMLInputElement>('input[type="file"]')!.accept).toContain(".jpeg");
  });
});

describe("Session 2 collapsed exact ownership presentation", () => {
  it("collapses by default, exposes a keyboard-native summary and resets on analysis changes", () => {
    const view = render(<OwnershipPathExplorer record={analysis()} />);
    const details = view.querySelector<HTMLDetailsElement>(".s2-ownership-structure")!; expect(details.open).toBe(false);
    const toggle = details.querySelector<HTMLElement>("summary")!; expect(toggle.textContent).toBe("Technical calculations and retained paths"); toggle.focus(); expect(window.document.activeElement).toBe(toggle);
    details.open = true; act(() => root!.render(<OwnershipPathExplorer record={{ ...analysis(), analysis_id: "analysis-2" }} />)); expect(view.querySelector<HTMLDetailsElement>(".s2-ownership-structure")!.open).toBe(false);
  });
  it("shows exact backend paths, party type/country, separate mixed sources and retained receipts", () => {
    const value = analysis(); value.source_classification = "OFFICIAL_MOCK_PLUS_LOCAL_SUPPLEMENT";
    value.document_observations = [observation()]; value.document_discrepancies = [{ observation_id: observation().observation_id, document_id: document().document_id, document_version: 1, agreement: "MISMATCH", compared_relationship_ids: ["HOLDING_PERSON"], current_percentage: "100", proposed_percentage: "95", reason_code: "OWNERSHIP_DOCUMENT_CONFLICT", verification_state: "REVIEW_REQUIRED" }];
    value.prior_analyses = [{ ...analysis(), analysis_id: "prior-analysis", manual_review_receipt: { actor_id: "previous-creator", reviewed_at: "previous-time", rationale: "Previous retained rationale.", source_selection: "CURRENT_EVIDENCE", source_type: "USER_SUPPLIED_DECLARATION", evidence_document_id: document().document_id, evidence_document_version: 3 } as NonNullable<OwnershipAnalysisRecord["manual_review_receipt"]> }];
    const view = render(<OwnershipPathExplorer record={value} />); expect(view.textContent).toContain("100 × 100 / 100 = 100.000000000000000000"); expect(view.textContent).toContain("LEGAL ENTITY"); expect(view.textContent).toContain("GB"); expect(view.textContent).toContain("LOCAL_SYNTHETIC_SUPPLEMENT"); expect(view.textContent).toContain("Official Marketplace Mock facts"); expect(view.textContent).toContain("MISMATCH"); expect(view.textContent).toContain("previous-creator"); expect(view.textContent).toContain("Previous retained rationale.");
  });
});
