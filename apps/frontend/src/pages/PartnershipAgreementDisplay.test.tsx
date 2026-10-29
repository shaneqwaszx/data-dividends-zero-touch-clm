// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";

import type { DocumentOwnershipObservation, DocumentProcessingRecord, OwnershipAnalysisRecord } from "../types";
import ManualOwnershipEvidenceForm from "./ManualOwnershipEvidenceForm";
import OwnershipPathExplorer from "./OwnershipPathExplorer";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const NOW = "2026-10-29T08:00:00Z";
const PENDING = "Partner shares from partnership agreement, awaiting RM confirmation";
const IDENTITY_ID = "11111111-1111-4111-8111-111111111111";
const AGREEMENT_ID = "22222222-2222-4222-8222-222222222222";

let root: Root | null = null;
let container: HTMLDivElement | null = null;

afterEach(() => {
  if (root) act(() => root?.unmount());
  container?.remove();
  root = null;
  container = null;
  vi.restoreAllMocks();
});

function mount(element: React.ReactElement): HTMLDivElement {
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
  act(() => root?.render(element));
  return container;
}

function shareRow(index: number, percent: string): DocumentOwnershipObservation {
  return {
    observation_id: `3333333${index}-3333-4333-8333-333333333333`,
    document_id: AGREEMENT_ID,
    document_version: 1,
    page_number: 1,
    source_reference: `PAGE_1_PARTNER_SHARE_ROW_${index + 5}`,
    owner_name: `DEMO GAMMA PERSON P${index}`,
    owner_type: "NATURAL_PERSON",
    owner_registration_identifier: null,
    owned_entity_name: null,
    owned_entity_registration_identifier: "209990103C",
    share_count: null,
    explicit_percentage: percent,
    explicit_total_shares: null,
    share_class: null,
    as_of_date: "2026-01-05",
    extraction_quality: "HIGH",
    extraction_method: "LOCAL_TESSERACT_OCR",
    evidence_score: 0.915,
    decision_state: "PROPOSED",
  } as unknown as DocumentOwnershipObservation;
}

function reviewed(id: string, name: string, rows: DocumentOwnershipObservation[]): DocumentProcessingRecord {
  return {
    document_id: id, display_name: name, state: "REVIEWED", superseded_by_document_id: null,
    events: [{ sequence: 1 }, { sequence: 2 }], ownership_observations: rows,
  } as unknown as DocumentProcessingRecord;
}

function gammaRecord(discrepancies: OwnershipAnalysisRecord["document_discrepancies"]): OwnershipAnalysisRecord {
  const rows = [shareRow(1, "30"), shareRow(2, "25")];
  return {
    case_id: "case-gamma", analysis_id: "analysis-gamma", correlation_id: "correlation-gamma",
    root_party_id: "ENTITY_209990103C", provider_name: "ACRA_REGISTRY_ACQUISITION", provider_environment: "MOCK",
    state: "REVIEW_REQUIRED",
    parties: [
      { party_id: "ENTITY_209990103C", display_name: "DEMO GAMMA TECHNOLOGIES FYP TEST PARTNERSHIP", party_type: "LEGAL_ENTITY", registration_number: "209990103C", country: "SG" },
      { party_id: "DEMO_GAMMA_P1", display_name: "DEMO GAMMA PERSON P1", party_type: "NATURAL_PERSON", registration_number: null, country: "SG" },
    ],
    relationships: [], candidates: [],
    issues: [{ code: "INCOMPLETE_LEGAL_ENTITY", message: "A reachable legal-entity ownership chain has no disclosed owners.", affected_party_ids: ["ENTITY_209990103C"] }],
    threshold_percent: "25", threshold_comparator: "GREATER_THAN_OR_EQUAL_TO", events: [], error: null,
    document_observations: rows, document_discrepancies: discrepancies,
    created_at: NOW, loaded_at: NOW, analyzed_at: NOW, updated_at: NOW,
  } as unknown as OwnershipAnalysisRecord;
}

const pendingShares = [shareRow(1, "30"), shareRow(2, "25")].map((row) => ({
  observation_id: row.observation_id, document_id: AGREEMENT_ID, document_version: 1 as const,
  agreement: "NOT_COMPARABLE" as const, compared_relationship_ids: [], current_percentage: null,
  proposed_percentage: row.explicit_percentage, reason_code: "PARTNERSHIP_AGREEMENT_SHARE" as const,
  verification_state: "REVIEW_REQUIRED" as const,
}));

it("1. defaults a partnership agreement to the document-observations source and agreement document", () => {
  const onSubmit = vi.fn();
  const view = mount(<ManualOwnershipEvidenceForm canonicalRootUen="209990103C" initialRootLegalName="DEMO GAMMA TECHNOLOGIES FYP TEST PARTNERSHIP"
    documents={[reviewed(IDENTITY_ID, "demo-gamma-scanned.pdf", []), reviewed(AGREEMENT_ID, "demo-gamma-partnership-agreement.pdf", [shareRow(1, "30"), shareRow(2, "70")])]}
    ownership={null} disabled={false} onSubmit={onSubmit} />);
  expect(view.querySelector<HTMLSelectElement>('[name="source_selection"]')!.value).toBe("DOCUMENT_OBSERVATIONS");
  expect(view.querySelector<HTMLSelectElement>('[aria-label="Evidence document"]')!.value).toBe(AGREEMENT_ID);
  // Rows are not preselected and nothing is submitted: the RM still confirms explicitly.
  expect([...view.querySelectorAll<HTMLInputElement>('input[type="checkbox"]')].every((box) => !box.checked)).toBe(true);
  expect(onSubmit).not.toHaveBeenCalled();
});

it("1. keeps the earlier default when no partnership agreement rows exist", () => {
  const view = mount(<ManualOwnershipEvidenceForm canonicalRootUen="202400001A" initialRootLegalName="Garden synthetic company"
    documents={[reviewed(IDENTITY_ID, "garden.pdf", [])]} ownership={null} disabled={false} onSubmit={vi.fn()} />);
  expect(view.querySelector<HTMLSelectElement>('[name="source_selection"]')!.value).toBe("USER_SUPPLIED_DECLARATION");
});

it("2. shows a partnership agreement share as pending, not as a registry conflict", () => {
  const view = mount(<OwnershipPathExplorer presentation="main" record={gammaRecord(pendingShares)} partnershipPendingLabel={PENDING} />);
  expect(view.textContent).toContain("No registry percentage (partnership); from partnership agreement, awaiting RM confirmation");
  expect(view.textContent).not.toContain("OWNERSHIP_DOCUMENT_CONFLICT");
  expect(view.textContent).not.toContain("MISMATCH");
});

it("2. keeps a real registry conflict unchanged", () => {
  const conflict = [{ ...pendingShares[0], agreement: "MISMATCH" as const, current_percentage: "40", reason_code: "OWNERSHIP_DOCUMENT_CONFLICT" as const }];
  const view = mount(<OwnershipPathExplorer presentation="main" record={gammaRecord(conflict)} />);
  expect(view.textContent).toContain("MISMATCH");
  expect(view.textContent).toContain("OWNERSHIP_DOCUMENT_CONFLICT");
});

it("3. replaces the incomplete-chain banner while a partnership awaits RM confirmation", () => {
  const pending = mount(<OwnershipPathExplorer presentation="main" record={gammaRecord(pendingShares)} partnershipPendingLabel={PENDING} />);
  expect(pending.textContent).not.toContain("INCOMPLETE_LEGAL_ENTITY");
  act(() => root?.unmount()); container?.remove(); root = null;
  const other = mount(<OwnershipPathExplorer presentation="main" record={gammaRecord(pendingShares)} />);
  expect(other.textContent).toContain("INCOMPLETE_LEGAL_ENTITY");
});

it("4. hints why an unlinked partner has no retained root path yet", () => {
  const view = mount(<OwnershipPathExplorer presentation="main" record={gammaRecord(pendingShares)} partnershipPendingLabel={PENDING} />);
  expect(view.textContent).toContain("No retained root path");
  const row = [...view.querySelectorAll(".ownership-node__context")].find((item) => item.textContent?.includes("No retained root path"));
  expect(row?.textContent).toContain(PENDING);
});
