// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { DocumentProcessingRecord, ReconciliationDiscrepancy, ReconciliationObservation, ZeroTouchCaseSummary } from "../types";
import DocumentEvidencePanel from "./DocumentEvidencePanel";
import { documentIdentityWarning } from "./DocumentIdentityWarning";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const CASE_ID = "00000000-0000-4000-8000-000000000201";
const NOW = "2026-10-29T01:00:00Z";
const CASE_NAME = "MERLION CIRCULAR LABS PTE. LTD.";
const CASE_UEN = "202400001A";
let sequence = 0;

type Field = "legal_name" | "registration_identifier";
type Validity = ReconciliationObservation["validity"];

function observation(field: Field, kind: ReconciliationObservation["source_kind"], value: string | null, documentId: string | null, validity: Validity = "VALID"): ReconciliationObservation {
  return {
    observation_id: `obs-${sequence += 1}`, field_name: field, normalized_value: value, source_kind: kind,
    source_system: null, environment: "LOCAL", observed_at: NOW, evidence_reference: null,
    document_id: documentId, document_display_name: null, confidence: validity === "UNVERIFIABLE" ? 0.4 : 0.97, validity,
  };
}

function discrepancy(field: Field, documentId: string, documentValue: string | null, options: {
  outcome?: ReconciliationDiscrepancy["outcome"]; validity?: Validity; status?: ReconciliationDiscrepancy["status"]; fingerprint?: string;
} = {}): ReconciliationDiscrepancy {
  return {
    discrepancy_id: `disc-${field}-${documentId}`, field_name: field, outcome: options.outcome ?? "CONFLICT",
    observations: [
      observation(field, "REGISTRY", field === "legal_name" ? CASE_NAME : CASE_UEN, null),
      observation(field, "DOCUMENT_IDP", documentValue, documentId, options.validity ?? "VALID"),
    ],
    status: options.status ?? "OPEN", allowed_actions: options.outcome && options.outcome !== "CONFLICT" ? [] : ["KEEP_REGISTRY_VALUE", "USE_DOCUMENT_VALUE"],
    evidence_fingerprint: options.fingerprint ?? `fp-${field}-${documentId}`, decision: null,
  };
}

function summary(discrepancies: ReconciliationDiscrepancy[], overrides: Partial<ZeroTouchCaseSummary> = {}): ZeroTouchCaseSummary {
  return {
    case: { case_id: CASE_ID, policy_snapshot: { idp_review_confidence_threshold: "0.85" } },
    status: "WAITING_FOR_REVIEW", current_stage: "DOCUMENT", evidence_decision_authorized: true,
    document_replacement_authorized: true, timeline: [], timing: { automation_elapsed_ms: 10 },
    reconciliation: { discrepancies },
    ...overrides,
  } as unknown as ZeroTouchCaseSummary;
}

function documentFixture(documentId: string, overrides: Partial<DocumentProcessingRecord> = {}): DocumentProcessingRecord {
  return {
    case_id: CASE_ID, document_id: documentId, correlation_id: "safe-correlation", display_name: `${documentId}.pdf`,
    media_type: "application/pdf", size_bytes: 100, profile: "PROVISIONAL_CORPORATE", provider_environment: "LOCAL",
    state: "REVIEWED", fields: [], events: [], error: null, created_at: NOW, processed_at: NOW, reviewed_at: NOW,
    supersedes_document_id: null, superseded_by_document_id: null, updated_at: NOW, ...overrides,
  };
}

let root: Root | null = null;
let container: HTMLDivElement | null = null;
afterEach(() => { if (root) act(() => root?.unmount()); container?.remove(); root = null; container = null; vi.restoreAllMocks(); });

function render(documents: DocumentProcessingRecord[], value: ZeroTouchCaseSummary, handlers: {
  onReplace?: (document: DocumentProcessingRecord, file: File) => void; onReviewDifference?: () => void; onCorrectIdentity?: () => void;
  presentation?: "main" | "full";
} = {}) {
  const element = <DocumentEvidencePanel summary={value} documents={documents} busy={false} busyLabel={null} mutationBlocked={false}
    presentation={handlers.presentation ?? "main"} onReview={() => undefined} onReplace={handlers.onReplace ?? (() => undefined)}
    onRetry={() => undefined} onContinue={() => undefined} onRefresh={() => undefined}
    onReviewDifference={handlers.onReviewDifference} onCorrectIdentity={handlers.onCorrectIdentity} />;
  if (!root) { container = document.createElement("div"); document.body.append(container); root = createRoot(container); }
  act(() => root?.render(element));
  return container!;
}

function warning(view: HTMLElement, documentId: string): HTMLElement | null {
  return view.querySelector(`[data-document-id="${documentId}"] .document-identity-warning`);
}

function buttonNames(element: HTMLElement): string[] {
  return [...element.querySelectorAll("button")].map((item) => item.textContent ?? "");
}

describe("wrong-document warning on the document card", () => {
  it("says the document belongs to a different company when name and UEN both conflict", () => {
    const view = render([documentFixture("doc-wrong-company")], summary([
      discrepancy("legal_name", "doc-wrong-company", "LION CITY EXISTING CUSTOMER PTE. LTD."),
      discrepancy("registration_identifier", "doc-wrong-company", "202400005E"),
    ]), { onReviewDifference: vi.fn(), onCorrectIdentity: vi.fn() });
    const card = warning(view, "doc-wrong-company")!;
    expect(card.querySelector("strong")?.textContent).toBe("This document looks like it belongs to a different company");
    expect(card.textContent).toContain("On this document: LION CITY EXISTING CUSTOMER PTE. LTD.");
    expect(card.textContent).toContain(`This case: ${CASE_NAME}`);
    expect(card.textContent).toContain("On this document: 202400005E");
    expect(card.textContent).toContain(`This case: ${CASE_UEN}`);
    expect(buttonNames(card)).toEqual(["Replace document"]);
    expect(card.querySelector("button")?.tagName).toBe("BUTTON");
  });

  it("names only the company name when that is the one field that conflicts, with the review and identity options", () => {
    const onReviewDifference = vi.fn();
    const onCorrectIdentity = vi.fn();
    const view = render([documentFixture("doc-name")], summary([discrepancy("legal_name", "doc-name", "MERLION CIRCULAR LAB PTE. LTD.")]),
      { onReviewDifference, onCorrectIdentity });
    const card = warning(view, "doc-name")!;
    expect(card.querySelector("strong")?.textContent).toBe("The company name on this document doesn't match this case");
    expect(card.textContent).toContain("On this document: MERLION CIRCULAR LAB PTE. LTD.");
    expect(card.textContent).not.toContain("UEN");
    expect(buttonNames(card)).toEqual(["Replace document", "Review the difference", "The details I entered are wrong"]);
    act(() => (card.querySelectorAll("button")[1] as HTMLButtonElement).click());
    act(() => (card.querySelectorAll("button")[2] as HTMLButtonElement).click());
    expect(onReviewDifference).toHaveBeenCalledOnce();
    expect(onCorrectIdentity).toHaveBeenCalledOnce();
  });

  it("names only the UEN when that is the one field that conflicts", () => {
    const view = render([documentFixture("doc-uen")], summary([discrepancy("registration_identifier", "doc-uen", "202400009Z")]));
    const card = warning(view, "doc-uen")!;
    expect(card.querySelector("strong")?.textContent).toBe("The UEN on this document doesn't match this case");
    expect(card.textContent).toContain("On this document: 202400009Z");
    expect(card.textContent).toContain(`This case: ${CASE_UEN}`);
    // Optional actions appear only when CaseDetail supplies their targets.
    expect(buttonNames(card)).toEqual(["Replace document"]);
  });

  it("says the value couldn't be read, not that it is a mismatch, for an unreadable document", () => {
    const view = render([documentFixture("doc-no-text")], summary([
      discrepancy("legal_name", "doc-no-text", null, { outcome: "MISSING_IN_SOURCE", validity: "MISSING" }),
    ]));
    const card = warning(view, "doc-no-text")!;
    expect(card.querySelector("strong")?.textContent).toBe("We couldn't read the company name from this document");
    expect(card.textContent).not.toMatch(/match|different company/i);
    expect(buttonNames(card)).toEqual(["Replace document"]);
  });

  it.each([
    ["UNVERIFIABLE", "UNVERIFIABLE" as const],
    ["AMBIGUOUS", "INVALID" as const],
  ])("treats a %s (low-confidence) identity as unreadable", (validity, outcome) => {
    const view = render([documentFixture("doc-low")], summary([
      discrepancy("legal_name", "doc-low", "MERLION OR LION CITY", { outcome, validity: validity as Validity }),
      discrepancy("registration_identifier", "doc-low", "20240000?A", { outcome, validity: validity as Validity }),
    ]));
    const card = warning(view, "doc-low")!;
    expect(card.querySelector("strong")?.textContent).toBe("We couldn't read the company name and UEN from this document");
    expect(card.querySelector("dl")).toBeNull();
  });

  it("treats a CONFLICT whose document value is not VALID as unreadable", () => {
    const value = summary([discrepancy("registration_identifier", "doc-x", "2024", { validity: "INVALID" })]);
    expect(documentIdentityWarning(documentFixture("doc-x"), value)?.kind).toBe("UNREADABLE");
  });

  it("ignores resolved discrepancies, other fields and other documents' observations", () => {
    const value = summary([
      discrepancy("legal_name", "doc-a", "OTHER PTE. LTD.", { status: "RESOLVED" }),
      discrepancy("registration_identifier", "doc-other", "202400005E"),
      { ...discrepancy("legal_name", "doc-a", "x"), field_name: "registered_address" },
    ]);
    expect(documentIdentityWarning(documentFixture("doc-a"), value)).toBeNull();
  });

  it("Replace document opens this card's existing replacement input and runs the replacement flow", () => {
    const onReplace = vi.fn();
    const doc = documentFixture("doc-replace");
    const view = render([doc], summary([discrepancy("legal_name", "doc-replace", "A"), discrepancy("registration_identifier", "doc-replace", "B")]), { onReplace });
    const input = view.querySelector<HTMLInputElement>(`[data-document-id="doc-replace"] .document-upload-input`)!;
    const click = vi.spyOn(input, "click").mockImplementation(() => undefined);
    act(() => warning(view, "doc-replace")!.querySelector("button")!.click());
    expect(click).toHaveBeenCalledOnce();
    const file = new File(["%PDF"], "clean-company-profile.pdf", { type: "application/pdf" });
    Object.defineProperty(input, "files", { value: [file], configurable: true });
    act(() => input.dispatchEvent(new Event("change", { bubbles: true })));
    expect(onReplace).toHaveBeenCalledWith(doc, file);
  });

  it("disables Replace document without permission and hides it when no replacement is allowed", () => {
    const discrepancies = [discrepancy("legal_name", "doc-p", "A"), discrepancy("registration_identifier", "doc-p", "B")];
    let view = render([documentFixture("doc-p")], summary(discrepancies, { evidence_decision_authorized: false }));
    expect(warning(view, "doc-p")!.querySelector("button")!.disabled).toBe(true);
    view = render([documentFixture("doc-p")], summary(discrepancies, { document_replacement_authorized: false }));
    expect(warning(view, "doc-p")!.textContent).toContain("This document looks like it belongs to a different company");
    expect(buttonNames(warning(view, "doc-p")!)).toEqual([]);
  });

  it("clears after a successful replacement, keeps the old version in history, and returns for another wrong document", () => {
    const old = documentFixture("doc-old");
    const wrong = [discrepancy("legal_name", "doc-old", "LION CITY"), discrepancy("registration_identifier", "doc-old", "202400005E")];
    let view = render([old], summary(wrong), { presentation: "full" });
    expect(warning(view, "doc-old")).not.toBeNull();

    const superseded = { ...old, superseded_by_document_id: "doc-clean" };
    const clean = documentFixture("doc-clean", { supersedes_document_id: "doc-old" });
    view = render([superseded, clean], summary(wrong.map((item) => ({ ...item, status: "RESOLVED" as const }))), { presentation: "full" });
    expect(view.querySelector(".document-identity-warning")).toBeNull();
    expect(view.textContent).toContain("Evidence history (1)");
    expect(view.querySelector('.evidence-history [data-document-id="doc-old"]')).not.toBeNull();

    const again = documentFixture("doc-wrong-again", { supersedes_document_id: "doc-clean" });
    view = render([superseded, { ...clean, superseded_by_document_id: "doc-wrong-again" }, again], summary([
      discrepancy("legal_name", "doc-wrong-again", "LION CITY"), discrepancy("registration_identifier", "doc-wrong-again", "202400005E"),
    ]), { presentation: "full" });
    const card = warning(view, "doc-wrong-again")!;
    expect(card.querySelector("strong")?.textContent).toBe("This document looks like it belongs to a different company");
    expect(card.getAttribute("role")).toBe("alert");
    expect(view.querySelectorAll(".document-identity-warning")).toHaveLength(1);
  });

  it("is announced with role=alert only the first time a given warning appears", () => {
    const value = summary([discrepancy("legal_name", "doc-once", "A", { fingerprint: "fp-once" })]);
    let view = render([documentFixture("doc-once")], value);
    expect(warning(view, "doc-once")!.getAttribute("role")).toBe("alert");
    act(() => root?.unmount()); root = null; container?.remove();
    view = render([documentFixture("doc-once")], value);
    expect(warning(view, "doc-once")!.hasAttribute("role")).toBe(false);
    expect(warning(view, "doc-once")!.textContent).toContain("The company name on this document doesn't match this case");
    view = render([documentFixture("doc-once")], summary([discrepancy("legal_name", "doc-once", "B", { fingerprint: "fp-changed" })]));
    expect(warning(view, "doc-once")!.getAttribute("role")).toBe("alert");
  });

  it("is not shown on historical evidence", () => {
    const value = summary([discrepancy("legal_name", "doc-h", "A")]);
    expect(documentIdentityWarning(documentFixture("doc-h"), value)).not.toBeNull();
    const view = render([documentFixture("doc-h", { superseded_by_document_id: "doc-n" }), documentFixture("doc-n")], value, { presentation: "full" });
    expect(view.querySelector(".document-identity-warning")).toBeNull();
  });
});
