// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClient } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";

import { submitManualOwnershipEvidence, type ManualOwnershipEvidenceInput } from "../api";
import { caseQueryKeys, manualOwnershipMutationEffect } from "../caseQueries";
import type { DocumentProcessingRecord, ZeroTouchCaseSummary } from "../types";
import ManualOwnershipEvidenceForm, { ownershipTotalIsExactly100, shouldShowManualOwnershipEvidence } from "./ManualOwnershipEvidenceForm";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const reviewedDocument = {
  document_id: "11111111-1111-4111-8111-111111111111",
  display_name: "Garden ownership declaration.pdf",
  state: "REVIEWED",
  superseded_by_document_id: null,
  events: [{ sequence: 1 }, { sequence: 2 }, { sequence: 3 }],
} as DocumentProcessingRecord;

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

function render(documents: DocumentProcessingRecord[] = [reviewedDocument], onSubmit = vi.fn()) {
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
  act(() => root?.render(
    <ManualOwnershipEvidenceForm
      canonicalRootUen="202400001A"
      initialRootLegalName="Garden synthetic company"
      documents={documents}
      disabled={false}
      onSubmit={onSubmit}
    />,
  ));
  return { view: container, onSubmit };
}

function enter(element: HTMLInputElement | HTMLTextAreaElement, value: string): void {
  const prototype = element instanceof HTMLTextAreaElement
    ? HTMLTextAreaElement.prototype
    : HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(prototype, "value")?.set?.call(element, value);
  element.dispatchEvent(new Event("input", { bubbles: true }));
}

describe("ManualOwnershipEvidenceForm", () => {
  it("submits the displayed reviewed document when documents arrive after mount", () => {
    const { view, onSubmit } = render([]);
    act(() => root?.render(
      <ManualOwnershipEvidenceForm canonicalRootUen="202400001A" initialRootLegalName="Garden synthetic company" documents={[reviewedDocument]} disabled={false} onSubmit={onSubmit} />,
    ));
    act(() => {
      enter(view.querySelector('[name="as_of_date"]')!, "2026-10-04");
      enter(view.querySelector('[name="ownership_percent_0"]')!, "60");
      enter(view.querySelector('[name="ownership_percent_1"]')!, "40");
      for (const select of view.querySelectorAll<HTMLSelectElement>('select[name^="party_type_"]')) {
        Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value")?.set?.call(select, "NATURAL_PERSON");
        select.dispatchEvent(new Event("change", { bubbles: true }));
      }
      enter(view.querySelector('[name="rationale"]')!, "Reviewed against signed evidence.");
      enter(view.querySelector('[name="display_name_0"]')!, "Owner A");
      enter(view.querySelector('[name="display_name_1"]')!, "Owner B");
    });
    act(() => view.querySelector("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    expect(onSubmit).toHaveBeenCalledOnce();
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({
      evidence_document_id: reviewedDocument.document_id,
      evidence_document_version: 3,
    }));
  });

  it("is offered only for the explicit server action", () => {
    expect(shouldShowManualOwnershipEvidence("MANUAL_OWNERSHIP_EVIDENCE")).toBe(true);
    expect(shouldShowManualOwnershipEvidence(null)).toBe(false);
    expect(shouldShowManualOwnershipEvidence(undefined)).toBe(false);
    expect(shouldShowManualOwnershipEvidence("OWNERSHIP_REVIEW_REQUIRED")).toBe(false);
  });

  it("submits the fictional Garden 60/40 declaration with the reviewed document version", () => {
    const { view, onSubmit } = render();
    act(() => {
      enter(view.querySelector('[name="root_party_id"]')!, "GARDEN_ROOT");
      enter(view.querySelector('[name="as_of_date"]')!, "2026-10-04");
      enter(view.querySelector('[name="ownership_percent_0"]')!, "60");
      enter(view.querySelector('[name="ownership_percent_1"]')!, "40");
      for (const select of view.querySelectorAll<HTMLSelectElement>('select[name^="party_type_"]')) {
        Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value")?.set?.call(select, "NATURAL_PERSON");
        select.dispatchEvent(new Event("change", { bubbles: true }));
      }
      enter(view.querySelector('[name="rationale"]')!, "Reviewed against the signed declaration.");
      enter(view.querySelector('[name="relationship_id_0"]')!, "GARDEN_DIRECT_60");
      enter(view.querySelector('[name="party_id_0"]')!, "GARDEN_OWNER_A");
      enter(view.querySelector('[name="display_name_0"]')!, "Synthetic Garden Owner A");
      enter(view.querySelector('[name="relationship_id_1"]')!, "GARDEN_DIRECT_40");
      enter(view.querySelector('[name="party_id_1"]')!, "GARDEN_OWNER_B");
      enter(view.querySelector('[name="display_name_1"]')!, "Synthetic Garden Owner B");
    });
    act(() => view.querySelector("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));

    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({
      evidence_document_id: reviewedDocument.document_id,
      evidence_document_version: 3,
      root_party_id: "GARDEN_ROOT",
      root_display_name: "Garden synthetic company",
      rationale: "Reviewed against the signed declaration.",
      owners: [
        expect.objectContaining({ relationship_id: "GARDEN_DIRECT_60", party_id: "GARDEN_OWNER_A", display_name: "Synthetic Garden Owner A", ownership_percent: "60" }),
        expect.objectContaining({ relationship_id: "GARDEN_DIRECT_40", party_id: "GARDEN_OWNER_B", display_name: "Synthetic Garden Owner B", ownership_percent: "40" }),
      ],
    }));
    expect(view.textContent).toContain("Supplementary client-supplied evidence · operator review · LOCAL · MANUAL_DECLARATION_POC");
    expect(view.textContent).toContain("not ACRA evidence or verified ownership");
    expect(view.textContent).toContain("independent blockers remain authoritative");
  });

  it("validates the total exactly without floating-point arithmetic", () => {
    expect(ownershipTotalIsExactly100(["60", "40"])).toBe(true);
    expect(ownershipTotalIsExactly100(["33.333333", "66.666667"])).toBe(true);
    expect(ownershipTotalIsExactly100(["60", "39.999999"])).toBe(false);
    expect(ownershipTotalIsExactly100(["60", "40.0000001"])).toBe(false);

    const { view, onSubmit } = render();
    act(() => {
      enter(view.querySelector('[name="as_of_date"]')!, "2026-10-04");
      enter(view.querySelector('[name="ownership_percent_0"]')!, "60");
      enter(view.querySelector('[name="ownership_percent_1"]')!, "40");
      for (const select of view.querySelectorAll<HTMLSelectElement>('select[name^="party_type_"]')) {
        Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value")?.set?.call(select, "NATURAL_PERSON");
        select.dispatchEvent(new Event("change", { bubbles: true }));
      }
      enter(view.querySelector('[name="rationale"]')!, "Reviewed against signed evidence.");
      enter(view.querySelector('[name="display_name_0"]')!, "Owner A");
      enter(view.querySelector('[name="display_name_1"]')!, "Owner B");
      enter(view.querySelector('[name="ownership_percent_1"]')!, "39.9");
    });
    act(() => view.querySelector("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    expect(onSubmit).not.toHaveBeenCalled();
    expect(view.textContent).toContain("must total exactly 100");
  });

  it("does not offer submission without a current reviewed document", () => {
    const { view } = render([]);
    expect(view.textContent).toContain("No current reviewed document is available");
    expect(view.querySelector("form")).toBeNull();
  });
});

describe("manual ownership endpoint and cache effect", () => {
  const payload: ManualOwnershipEvidenceInput = {
    root_registration_number: "202400001A",
    evidence_document_id: reviewedDocument.document_id,
    evidence_document_version: 3,
    as_of_date: "2026-09-29",
    rationale: "Reviewed against the signed declaration.",
    root_party_id: "GARDEN_ROOT",
    parties: [
      { party_id: "GARDEN_ROOT", display_name: "Garden synthetic company", party_type: "LEGAL_ENTITY", registration_number: "202400001A", country: "SG" },
      { party_id: "GARDEN_OWNER_A", display_name: "Synthetic Garden Owner A", party_type: "NATURAL_PERSON", registration_number: null, country: "SG" },
      { party_id: "GARDEN_OWNER_B", display_name: "Synthetic Garden Owner B", party_type: "NATURAL_PERSON", registration_number: null, country: "SG" },
    ],
    relationships: [
      { relationship_id: "GARDEN_DIRECT_60", parent_party_id: "GARDEN_ROOT", child_party_id: "GARDEN_OWNER_A", ownership_percent: "60", relationship_type: "DIRECT_ECONOMIC_INTEREST" },
      { relationship_id: "GARDEN_DIRECT_40", parent_party_id: "GARDEN_ROOT", child_party_id: "GARDEN_OWNER_B", ownership_percent: "40", relationship_type: "DIRECT_ECONOMIC_INTEREST" },
    ],
    expected_automation_version: 8,
    expected_ownership_version: 5,
    expected_case_event_count: 7,
  };

  it("posts the exact CAS-bound Garden payload once", async () => {
    const response = { case: { case_id: "case-1" } } as ZeroTouchCaseSummary;
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(response), { status: 200, headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    await submitManualOwnershipEvidence("case-1", payload);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/api/clm/zero-touch/cases/case-1/manual-ownership-evidence");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual(payload);
  });

  it("surfaces a stale 409 and never retries", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: { code: "ZERO_TOUCH_MANUAL_OWNERSHIP_STALE", message: "The reviewed ownership version is stale." } }), { status: 409, headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(submitManualOwnershipEvidence("case-1", payload)).rejects.toMatchObject({ status: 409, code: "ZERO_TOUCH_MANUAL_OWNERSHIP_STALE" });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("publishes and invalidates only the acting user's case resources", async () => {
    const client = new QueryClient();
    const summary = { case: { case_id: "case-1" } } as ZeroTouchCaseSummary;
    client.setQueryData(caseQueryKeys.detail("other-user", "case-1"), { marker: "untouched" });
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const remove = vi.spyOn(client, "removeQueries");
    await manualOwnershipMutationEffect(client, "case-user", summary);
    expect(client.getQueryData(caseQueryKeys.detail("case-user", "case-1"))).toBe(summary);
    expect(client.getQueryData(caseQueryKeys.detail("other-user", "case-1"))).toEqual({ marker: "untouched" });
    expect(invalidate.mock.calls.every(([filters]) => JSON.stringify(filters?.queryKey).includes("case-user"))).toBe(true);
    expect(remove.mock.calls.every(([filters]) => JSON.stringify(filters?.queryKey).includes("case-user"))).toBe(true);
  });
});
