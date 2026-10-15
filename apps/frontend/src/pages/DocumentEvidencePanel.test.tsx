// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { DocumentProcessingRecord, ZeroTouchCaseSummary } from "../types";
import DocumentEvidencePanel, {
  canContinueRecoveredIntake,
  canRetrySavedReviewCheckpoint,
  exactSavedReviewRequest,
  isCurrentDocument,
} from "./DocumentEvidencePanel";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const CASE_ID = "00000000-0000-4000-8000-000000000101";
const CURRENT_ID = "00000000-0000-4000-8000-000000000102";
const HISTORY_ID = "00000000-0000-4000-8000-000000000103";
const NOW = "2026-09-20T01:00:00Z";

function summary(status: ZeroTouchCaseSummary["status"] = "WAITING_FOR_REVIEW"): ZeroTouchCaseSummary {
  return {
    case: { case_id: CASE_ID, policy_snapshot: { idp_review_confidence_threshold: "0.85" } },
    status,
    evidence_decision_authorized: true,
    current_stage: "DOCUMENT",
    timeline: [],
    timing: { automation_elapsed_ms: 10 },
  } as unknown as ZeroTouchCaseSummary;
}

function documentFixture(overrides: Partial<DocumentProcessingRecord> = {}): DocumentProcessingRecord {
  return {
    case_id: CASE_ID,
    document_id: CURRENT_ID,
    correlation_id: "safe-correlation",
    display_name: "company-profile.pdf",
    media_type: "application/pdf",
    size_bytes: 100,
    profile: "PROVISIONAL_CORPORATE",
    provider_environment: "LOCAL",
    state: "REVIEW_REQUIRED",
    fields: [{
      field_key: "legal_name",
      original_extracted_value: "SYNTHETIC PTE. LTD.",
      normalized_value: "SYNTHETIC PTE. LTD.",
      confidence: 0.97,
      provenance: { provider: "LOCAL_PDF_TEXT", environment: "LOCAL", page_number: 1, source_reference: "safe:field:1" },
      canonical_value: "SYNTHETIC PTE. LTD.",
      comparison_status: "MATCH",
      review_status: "PENDING",
      reviewed_value: null,
      reviewed_at: null,
      review_note: null,
    }],
    events: [],
    error: null,
    created_at: NOW,
    processed_at: NOW,
    reviewed_at: null,
    supersedes_document_id: null,
    superseded_by_document_id: null,
    updated_at: NOW,
    ...overrides,
  };
}

let root: Root | null = null;
let container: HTMLDivElement | null = null;

afterEach(() => {
  if (root) act(() => root?.unmount());
  container?.remove();
  root = null;
  container = null;
});

function renderPanel(
  documents: DocumentProcessingRecord[],
  onReview = vi.fn(),
  suppliedSummary = summary(),
  uploads: { onReplace?: (document: DocumentProcessingRecord, file: File) => void; onRetry?: (document: DocumentProcessingRecord, file: File) => void; onRecoverRefresh?: () => void } = {},
  readState: { presentation?: "more" | "technical"; loading?: boolean; loadFailed?: boolean; mutationBlocked?: boolean } = {},
) {
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
  act(() => root?.render(
    <DocumentEvidencePanel
      summary={suppliedSummary}
      documents={documents}
      busy={false}
      busyLabel={null}
      mutationBlocked={false}
      onReview={onReview}
      onReplace={uploads.onReplace ?? (() => undefined)}
      onRetry={uploads.onRetry ?? (() => undefined)}
      onContinue={() => undefined}
      onRecoverRefresh={uploads.onRecoverRefresh}
      onRefresh={() => undefined}
      {...readState}
    />,
  ));
  return { container, onReview };
}

function clickButton(name: string) {
  const button = [...container!.querySelectorAll("button")].find((item) => item.textContent === name);
  expect(button, `button ${name}`).toBeTruthy();
  act(() => button!.dispatchEvent(new MouseEvent("click", { bubbles: true })));
}

function setInputValue(input: HTMLInputElement, value: string) {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
  act(() => {
    setter?.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

describe("DocumentEvidencePanel", () => {
  it.each([true, false])("projects retained replacement recovery using backend eligibility %s", (canResume) => {
    const retained = summary("RESUMING");
    retained.document_refresh_recovery = { can_resume: canResume };
    const recover = vi.fn();
    renderPanel([documentFixture({ state: "REVIEWED" })], vi.fn(), retained, { onRecoverRefresh: recover });
    const button = container!.querySelector<HTMLButtonElement>("#case-document-refresh-recovery button")!;
    expect(button.disabled).toBe(!canResume);
    expect(container!.textContent).toContain("Replacement saved; evidence refresh needs recovery.");
    if (canResume) {
      button.focus(); expect(document.activeElement).toBe(button);
      act(() => button.click()); expect(recover).toHaveBeenCalledTimes(1);
    } else {
      act(() => button.click()); expect(recover).not.toHaveBeenCalled();
    }
  });
  it("keeps creator document decisions usable while GoldTier Search is unresolved", () => {
    const onReview = vi.fn();
    const paused = summary();
    paused.current_stage = "GOLDTIER_SEARCH";
    const document = documentFixture();
    const { container: view } = renderPanel([document], onReview, paused);
    const accept = [...view.querySelectorAll("button")].find(
      (item) => item.textContent === "Accept legal name suggestion",
    )!;
    expect(accept.disabled).toBe(false);
    clickButton("Accept legal name suggestion");
    expect(onReview).toHaveBeenCalledWith(
      document, { fieldKey: "legal_name", decision: "ACCEPTED" }, false,
    );
  });
  it("classifies null/absent supersession as current and keeps history read-only", () => {
    const current = documentFixture();
    const historical = documentFixture({ document_id: HISTORY_ID, display_name: "old-profile.pdf", superseded_by_document_id: CURRENT_ID });
    const { container: view } = renderPanel([historical, current]);

    expect(isCurrentDocument(current)).toBe(true);
    expect(isCurrentDocument({ ...current, superseded_by_document_id: undefined })).toBe(true);
    expect(isCurrentDocument(historical)).toBe(false);
    expect(view.textContent).toContain("Current evidence");
    expect(view.textContent).toContain("Evidence history (1)");
    const history = view.querySelector(".document-card--history")!;
    expect(history.textContent).toContain("old-profile.pdf");
    expect(history.querySelector("button")).toBeNull();
    expect(history.querySelector("input[type=file]")).toBeNull();
  });

  it("offers valid pending decisions, omits Accept without a suggestion, and sends exact enums", () => {
    const onReview = vi.fn();
    const missing = documentFixture({ fields: [{ ...documentFixture().fields[0], original_extracted_value: null, comparison_status: "MISSING_FROM_DOCUMENT" }] });
    const { container: view } = renderPanel([missing], onReview);

    expect(view.textContent).not.toContain("Accept legal name suggestion");
    clickButton("Reject legal name suggestion");
    expect(onReview).toHaveBeenCalledWith(missing, { fieldKey: "legal_name", decision: "REJECTED" }, false);
  });

  it("uses an accessible inline correction editor and enforces the existing limits", () => {
    const onReview = vi.fn();
    const pending = documentFixture();
    renderPanel([pending], onReview);
    clickButton("Record legal name correction");

    const correction = container!.querySelector<HTMLInputElement>("input.input")!;
    expect(document.activeElement).toBe(correction);
    setInputValue(correction, "   ");
    clickButton("Save legal name correction");
    expect(container!.textContent).toContain("Enter a correction before saving.");
    expect(onReview).not.toHaveBeenCalled();

    setInputValue(correction, "CORRECTED SYNTHETIC NAME");
    clickButton("Save legal name correction");
    expect(onReview).toHaveBeenCalledWith(pending, {
      fieldKey: "legal_name",
      decision: "CORRECTED",
      correctedValue: "CORRECTED SYNTHETIC NAME",
    }, false);
  });

  it("shows dynamic partial-review counts and retains independent-blocker wording", () => {
    const partial = documentFixture({
      fields: [
        { ...documentFixture().fields[0], review_status: "ACCEPTED", reviewed_at: NOW },
        { ...documentFixture().fields[0], field_key: "registered_address", original_extracted_value: "1 TEST STREET" },
      ],
    });
    const { container: view } = renderPanel([partial]);
    expect(view.textContent).toContain("1 final / 2 fields");
    expect(view.textContent).toContain("1 field remains for review");
    expect(view.textContent).toContain("Independent readiness blockers remain authoritative");
  });

  it.each([
    ["missing", null, 0.97],
    ["below-threshold", "SYNTHETIC PTE. LTD.", 0.54],
  ])("labels a retained %s correction as replacement-required", (_case, original, confidence) => {
    const corrected = documentFixture({
      fields: [{
        ...documentFixture().fields[0],
        original_extracted_value: original,
        confidence,
        review_status: "CORRECTED",
        reviewed_value: "RETAINED CORRECTION",
        reviewed_at: NOW,
      }],
    });
    const { container: view } = renderPanel([corrected]);
    expect(view.textContent).toContain("Correction retained, but replacement evidence is still required");
  });

  it("builds only the exact retained final request and keeps the decision read-only", () => {
    const correctedField = {
      ...documentFixture().fields[0],
      review_status: "CORRECTED" as const,
      reviewed_value: "EXACT RETAINED VALUE",
      review_note: "Exact retained note",
      reviewed_at: NOW,
    };
    const reviewed = documentFixture({ state: "REVIEWED", reviewed_at: NOW, fields: [correctedField] });
    const onReview = vi.fn();
    const { container: view } = renderPanel([reviewed], onReview);

    expect(exactSavedReviewRequest(correctedField)).toEqual({ fieldKey: "legal_name", decision: "CORRECTED", correctedValue: "EXACT RETAINED VALUE", note: "Exact retained note" });
    expect(canRetrySavedReviewCheckpoint(summary(), reviewed)).toBe(true);
    expect(view.textContent).not.toContain("Record legal name correction");
    clickButton("Retry saved legal name review checkpoint");
    expect(onReview).toHaveBeenCalledWith(reviewed, exactSavedReviewRequest(correctedField), true);
  });

  it("does not expose checkpoint repair for partial, superseded, malformed, or wrong-stage evidence", () => {
    const finalField = { ...documentFixture().fields[0], review_status: "ACCEPTED" as const, reviewed_at: NOW };
    const partial = documentFixture({ fields: [finalField, { ...documentFixture().fields[0], field_key: "registered_address" }] });
    const superseded = documentFixture({ state: "REVIEWED", fields: [finalField], superseded_by_document_id: "new" });
    const malformed = documentFixture({ state: "REVIEWED", fields: [{ ...finalField, review_status: "CORRECTED", reviewed_value: null }] });
    expect(canRetrySavedReviewCheckpoint(summary(), partial)).toBe(false);
    expect(canRetrySavedReviewCheckpoint(summary(), superseded)).toBe(false);
    expect(canRetrySavedReviewCheckpoint(summary(), malformed)).toBe(false);
    expect(canRetrySavedReviewCheckpoint({ ...summary(), current_stage: "OWNERSHIP" }, documentFixture({ state: "REVIEWED", fields: [finalField] }))).toBe(false);
  });

  it("requires current bidirectional failed-replacement lineage and the latest typed timeline event", () => {
    const failed = documentFixture({ document_id: HISTORY_ID, state: "FAILED", error: { code: "DOCUMENT_REUPLOAD_REQUIRED", message: "Retry required" }, superseded_by_document_id: CURRENT_ID });
    const recovered = documentFixture({ state: "REVIEW_REQUIRED", supersedes_document_id: HISTORY_ID });
    const pending = {
      ...summary("PENDING_INPUTS"),
      timeline: [{ event_type: "DOCUMENT_REUPLOAD_REQUIRED" }],
    } as ZeroTouchCaseSummary;
    expect(canContinueRecoveredIntake(pending, [failed, recovered])).toBe(true);
    expect(canContinueRecoveredIntake({
      ...pending, timing: { ...pending.timing, automation_elapsed_ms: null },
    }, [failed, recovered])).toBe(false);
    expect(canContinueRecoveredIntake(pending, [failed, { ...recovered, supersedes_document_id: "unrelated" }])).toBe(false);
    expect(canContinueRecoveredIntake({ ...pending, timeline: [{ event_type: "OTHER" }] } as ZeroTouchCaseSummary, [failed, recovered])).toBe(false);
    expect(canContinueRecoveredIntake(pending, [failed, { ...recovered, state: "FAILED" }])).toBe(false);
    expect(canContinueRecoveredIntake(pending, [
      failed,
      recovered,
      documentFixture({
        document_id: "00000000-0000-4000-8000-000000000104",
        state: "FAILED",
        error: { code: "DOCUMENT_REUPLOAD_REQUIRED", message: "A second current document still failed" },
      }),
    ])).toBe(false);
    expect(canContinueRecoveredIntake(summary(), [failed, recovered])).toBe(false);
  });

  it.each([
    ["Replace current document", documentFixture()],
    ["Retry affected document", documentFixture({ state: "FAILED", error: { code: "DOCUMENT_REUPLOAD_REQUIRED", message: "Retry required" } })],
  ])("keeps the %s native file input keyboard-focusable", (label, record) => {
    const { container: view } = renderPanel([record], vi.fn(), summary(record.state === "FAILED" ? "PENDING_INPUTS" : "WAITING_FOR_REVIEW"));
    const input = view.querySelector<HTMLInputElement>(".document-upload-input")!;
    expect(input).not.toBeNull();
    expect(input.hidden).toBe(false);
    expect(input.disabled).toBe(false);
    expect(input.labels?.[0]?.textContent).toContain(label);
    act(() => input.focus());
    expect(document.activeElement).toBe(input);
    expect(input.closest("label")?.classList.contains("document-upload-control")).toBe(true);
  });

  it("dispatches a targeted retry from the keyboard-focusable native upload control", () => {
    const failed = documentFixture({ state: "FAILED", error: { code: "DOCUMENT_REUPLOAD_REQUIRED", message: "Retry required" } });
    const onRetry = vi.fn();
    const { container: view } = renderPanel([failed], vi.fn(), summary("PENDING_INPUTS"), { onRetry });
    const input = view.querySelector<HTMLInputElement>(".document-upload-input")!;
    const file = new File(["safe synthetic retry"], "retry.txt", { type: "text/plain" });
    Object.defineProperty(input, "files", { configurable: true, value: [file] });
    act(() => input.dispatchEvent(new Event("change", { bubbles: true })));
    expect(onRetry).toHaveBeenCalledOnce();
    expect(onRetry).toHaveBeenCalledWith(failed, file);
  });

  it("shows exact reconciliation completion without requesting duplicate source field accepts", () => {
    const { container: view } = renderPanel([documentFixture({ semantic_completion: "RECONCILIATION_RESOLVED", reconciliation_version: 7 })]);
    expect(view.textContent).toContain("RECONCILIATION RESOLVED");
    expect(view.textContent).toContain("OPERATOR RESOLVED");
    expect(view.textContent).toContain("Original extraction and field review evidence is preserved");
    expect(view.textContent).toContain("source field reviews final");
    expect(Array.from(view.querySelectorAll("button")).some((button) => /Accept .* suggestion/.test(button.textContent ?? ""))).toBe(false);
  });

  it("blocks all mutation inputs after a refresh failure and offers only a read-only refresh", () => {
    container = document.createElement("div");
    document.body.append(container);
    root = createRoot(container);
    act(() => root?.render(<DocumentEvidencePanel summary={summary()} documents={[documentFixture()]} busy={false} busyLabel={null} mutationBlocked onReview={() => undefined} onReplace={() => undefined} onRetry={() => undefined} onContinue={() => undefined} onRefresh={() => undefined} />));
    expect(container.textContent).toContain("Evidence reload could not be confirmed.");
    expect(container.textContent).toContain("Refresh case evidence");
    for (const control of container.querySelectorAll<HTMLButtonElement | HTMLInputElement>("button, input[type=file]")) {
      if (control.textContent === "Refresh case evidence") expect(control.disabled).toBe(false);
      else expect(control.disabled).toBe(true);
    }
  });
});


it("partitions essential actions, read-only history and safe extraction without changing legacy defaults", () => {
  const current = documentFixture();
  const historical = documentFixture({ document_id: HISTORY_ID, display_name: "superseded.pdf", superseded_by_document_id: CURRENT_ID });
  renderPanel([current, historical]);
  const props = { summary: summary(), documents: [current, historical], busy: false, busyLabel: null, mutationBlocked: false,
    reviewInWorkspace: true, onReview: vi.fn(), onReplace: vi.fn(), onRetry: vi.fn(), onContinue: vi.fn(), onRefresh: vi.fn() };
  const expectNamedFields = () => expect([...container!.querySelectorAll<HTMLElement>(".document-field[aria-labelledby]")].every(field =>
    field.querySelector("[id]")?.id === field.getAttribute("aria-labelledby"))).toBe(true);
  expectNamedFields();
  act(() => root!.render(<DocumentEvidencePanel {...props} presentation="main" />));
  expectNamedFields();
  expect(container!.textContent).toContain("company-profile.pdf");
  expect(container!.textContent).toContain("1 field remains for review");
  expect(container!.textContent).not.toContain("superseded.pdf");
  expect(container!.textContent).not.toContain("Score formula");
  expect(container!.querySelector("input[type=file]")).not.toBeNull();
  act(() => root!.render(<DocumentEvidencePanel {...props} presentation="more" />));
  expect(container!.textContent).toContain("superseded.pdf");
  expect(container!.textContent).toContain("Historical evidence");
  expectNamedFields();
  expect(container!.querySelector("button, input, select, textarea")).toBeNull();
  act(() => root!.render(<DocumentEvidencePanel {...props} presentation="technical" />));
  expect(container!.textContent).toContain("LOCAL_PDF_TEXT");
  expect(container!.textContent).toContain("Score formula");
  expect(container!.textContent).toContain("Document version");
  expect(container!.querySelector("details")).toBeNull();
  expect(container!.querySelector("button, input, select, textarea")).toBeNull();
});


it("keeps missing and low-score evidence distinct in essential presentation", () => {
  const current = documentFixture({ fields: [
    { ...documentFixture().fields[0], original_extracted_value: null, comparison_status: "MISSING_FROM_DOCUMENT", extraction_quality: "UNAVAILABLE" },
    { ...documentFixture().fields[0], field_key: "registered_address", confidence: 0.54, extraction_quality: "LOW", comparison_status: "MISMATCH" },
  ] });
  renderPanel([current]);
  act(() => root!.render(<DocumentEvidencePanel presentation="main" reviewInWorkspace summary={summary()} documents={[current]} busy={false} busyLabel={null} mutationBlocked={false} onReview={vi.fn()} onReplace={vi.fn()} onRetry={vi.fn()} onContinue={vi.fn()} onRefresh={vi.fn()} />));
  expect(container!.textContent).toContain("Missing extracted evidence");
  expect(container!.textContent).toContain("Low evidence score");
  expect(container!.textContent).toContain("Extraction quality: UNAVAILABLE");
  expect(container!.textContent).toContain("MISSING FROM DOCUMENT");
  expect(container!.textContent).toContain("MISMATCH");
  expect(container!.querySelector("details")).toBeNull();
});


it("shows ambiguous current candidates needed for correction directly in Main", () => {
  const current = documentFixture({ fields: [{ ...documentFixture().fields[0], extraction_quality: "AMBIGUOUS", candidates: [
    { value: "SYNTHETIC CANDIDATE A", page_number: 1, source_reference: "synthetic:page:1" },
    { value: "SYNTHETIC CANDIDATE B", page_number: 2, source_reference: "synthetic:page:2" },
  ] }] });
  renderPanel([current]);
  act(() => root!.render(<DocumentEvidencePanel presentation="main" reviewInWorkspace summary={summary()} documents={[current]} busy={false} busyLabel={null} mutationBlocked={false} onReview={vi.fn()} onReplace={vi.fn()} onRetry={vi.fn()} onContinue={vi.fn()} onRefresh={vi.fn()} />));
  expect(container!.textContent).toContain("SYNTHETIC CANDIDATE A");
  expect(container!.textContent).toContain("SYNTHETIC CANDIDATE B");
  expect(container!.querySelector("details")).toBeNull();
});


describe.each(["more", "technical"] as const)("%s document support read states", presentation => {
  const emptyText = presentation === "more" ? "No current document is retained." : "No document processing evidence is retained.";
  function visibleNotice(role: "status" | "alert") {
    const notice = container!.querySelector<HTMLElement>(`[role=${role}]`);
    expect(notice).not.toBeNull();
    expect(notice!.closest("[hidden], [aria-hidden=true]")).toBeNull();
    expect(getComputedStyle(notice!).display).not.toBe("none");
    return notice!.textContent;
  }
  it("explains initial loading without asserting absence or inventing evidence", () => {
    renderPanel([], vi.fn(), summary(), {}, { presentation, loading: true });
    expect(visibleNotice("status")).toContain("Loading document information");
    expect(container!.textContent).not.toContain(emptyText);
    expect(container!.querySelector("article")).toBeNull();
  });
  it("explains a failed empty read and unconfirmed document availability", () => {
    renderPanel([], vi.fn(), summary(), {}, { presentation, loadFailed: true });
    expect(visibleNotice("alert")).toContain("Document information could not be loaded.");
    expect(visibleNotice("alert")).toContain("Document availability cannot currently be confirmed.");
    expect(container!.textContent).not.toContain(emptyText);
    expect(container!.querySelector("article")).toBeNull();
  });
  it("qualifies retained current and historical evidence after failed refresh", () => {
    const history = documentFixture({ document_id: HISTORY_ID, display_name: "superseded.pdf", superseded_by_document_id: CURRENT_ID });
    renderPanel([documentFixture(), history], vi.fn(), summary(), {}, { presentation, loadFailed: true });
    expect(visibleNotice("alert")).toContain("Last-confirmed document information remains visible and may be stale.");
    expect(container!.textContent).toContain("company-profile.pdf");
    expect(container!.textContent).toContain("superseded.pdf");
    expect(container!.textContent).toContain("Historical evidence");
    expect(container!.querySelector("button, input, select, textarea")).toBeNull();
  });
  it("keeps a completed successful empty result truthful", () => {
    renderPanel([], vi.fn(), summary(), {}, { presentation });
    expect(container!.textContent).toContain(emptyText);
    expect(container!.querySelector("[role=status], [role=alert]")).toBeNull();
  });
  it("preserves successful retained support and provenance without failure wording", () => {
    renderPanel([documentFixture()], vi.fn(), summary(), {}, { presentation });
    expect(container!.textContent).toContain("company-profile.pdf");
    expect(container!.textContent).toContain(presentation === "technical" ? "LOCAL_PDF_TEXT" : "SYNTHETIC PTE. LTD.");
    expect(container!.textContent).not.toContain(emptyText);
    expect(container!.querySelector("[role=status], [role=alert], button, input, select, textarea")).toBeNull();
  });
  it("keeps mutation-blocked retained evidence explicitly unconfirmed and read-only", () => {
    renderPanel([documentFixture()], vi.fn(), { ...summary(), evidence_decision_authorized: false }, {}, { presentation, mutationBlocked: true });
    expect(visibleNotice("alert")).toContain("Evidence reload could not be confirmed.");
    expect(visibleNotice("alert")).toContain("Last-confirmed document information remains visible and may be stale.");
    expect(container!.querySelector("button, input, select, textarea")).toBeNull();
  });
  it("does not assert empty evidence while a blocked reload is unconfirmed", () => {
    renderPanel([], vi.fn(), summary(), {}, { presentation, mutationBlocked: true });
    expect(visibleNotice("alert")).toContain("Document availability cannot currently be confirmed.");
    expect(container!.textContent).not.toContain(emptyText);
  });
});
