// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, describe, expect, it } from "vitest";
import OnboardingWorkspace, { onboardingIsExecuting } from "./OnboardingWorkspace";
import { OnboardingProgressPanel } from "./CaseStatePanels";
import DocumentEvidencePanel, { documentStatusLabel } from "./DocumentEvidencePanel";
import type { DocumentProcessingRecord, ProcessingNode, ZeroTouchCaseSummary } from "../types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
const host = document.createElement("div");
let root = createRoot(host);
afterEach(async () => { await act(async () => root.unmount()); host.replaceChildren(); host.remove(); root = createRoot(host); });
function summary(status: ZeroTouchCaseSummary["status"] = "RUNNING"): ZeroTouchCaseSummary {
  return { case: { case_id: "synthetic-case" }, status, active_exceptions: [], timeline: [], updated_at: "2026-10-04T01:00:00Z" } as unknown as ZeroTouchCaseSummary;
}
const node: ProcessingNode = { node_id: "DOCUMENT_IDP", label: "Document verification", status: "NOT_REACHED", children: [], safe_result: "Document intake has not started.", provider: "LOCAL_PDF_TEXT", environment: "LOCAL", timestamp: "2026-10-04T01:00:00Z" };

describe("Session 1 workspace presentation", () => {
  it("makes only executing workspace content inert while preserving shell keyboard controls", async () => {
    document.body.append(host);
    const render = (active: boolean) => root.render(<><button id="shell">Navigation</button><OnboardingWorkspace active={active} message="Processing uploaded documents…"><button id="workspace">Document action</button></OnboardingWorkspace></>);
    await act(async () => render(false));
    host.querySelector<HTMLButtonElement>("#workspace")!.focus();
    await act(async () => render(true));
    expect(host.querySelector(".processing-workspace")!.getAttribute("aria-busy")).toBe("true");
    expect(host.querySelector(".processing-workspace__content")!.hasAttribute("inert")).toBe(true);
    expect(host.querySelector("#shell")!.closest("[inert]")).toBeNull();
    expect(document.activeElement).toBe(host.querySelector("[role='status']"));
    expect(host.textContent).toContain("Processing onboarding");
    host.querySelector<HTMLButtonElement>("#shell")!.focus();
    await act(async () => render(false));
    expect(host.querySelector("[inert]")).toBeNull();
    expect(host.querySelector(".processing-workspace__overlay")).toBeNull();
    expect(document.activeElement).toBe(host.querySelector("#shell"));
  });
  it.each(["WAITING_FOR_REVIEW", "TECHNICAL_FAILURE", "RECOVERY_PENDING", "COMPLETED"] as const)("never covers %s with loading", (status) => {
    expect(onboardingIsExecuting(summary(status), true, null)).toBe(false);
  });
  it("removes loading for a genuine action or load error and allows active intake", () => {
    const blocked = summary();
    blocked.active_exceptions = [{}] as ZeroTouchCaseSummary["active_exceptions"];
    expect(onboardingIsExecuting(blocked, true, null)).toBe(false);
    expect(onboardingIsExecuting(summary(), true, "Document information could not be loaded")).toBe(false);
    expect(onboardingIsExecuting(null, true, null)).toBe(true);
    expect(onboardingIsExecuting(summary(), false, null)).toBe(true);
  });
  it.each(["COMPLETE", "SKIPPED", "NOT_REACHED", "IN_PROGRESS"] as const)("opens factual details for %s without inventing a review action", async (status) => {
    const model = summary(); model.processing_pipeline = [{ ...node, status }];
    await act(async () => root.render(<OnboardingProgressPanel summary={model} />));
    const button = host.querySelector<HTMLButtonElement>("button")!;
    expect(button.textContent).toContain("View details");
    await act(async () => button.click());
    expect(button.getAttribute("aria-expanded")).toBe("true");
    const details = host.querySelector("#processing-stage-details")!;
    expect(details.textContent).toContain("Document intake has not started.");
    expect(details.textContent).toContain("LOCAL_PDF_TEXT");
    expect(details.textContent).toContain("LOCAL");
    expect(details.textContent).toContain("Recorded at:");
    expect(details.textContent).not.toContain("Review required");
  });
});

describe("Session 1 document wording", () => {
  const base = { state: "REVIEWED", fields: [{ review_status: "ACCEPTED", comparison_status: "MATCH" }] } as DocumentProcessingRecord;
  it.each([
    ["UPLOADED", "Document uploaded"], ["PROCESSING", "Processing document"],
    ["REVIEW_REQUIRED", "Document review required"], ["FAILED", "Document processing failed"],
  ] as const)("labels %s from the retained state", (state, label) => expect(documentStatusLabel({ ...base, state })).toBe(label));
  it("distinguishes processed/rejected evidence from verified matching evidence", () => {
    expect(documentStatusLabel(base)).toBe("Document verified");
    expect(documentStatusLabel({ ...base, fields: [{ ...base.fields[0], review_status: "REJECTED" }] })).toBe("Document processed");
  });
  it.each([[true, false, "Loading document information…"], [false, true, "Document information could not be loaded"], [false, false, "No document uploaded"]] as const)("distinguishes loading=%s error=%s", async (loading, loadFailed, text) => {
    await act(async () => root.render(<DocumentEvidencePanel summary={summary()} documents={[]} loading={loading} loadFailed={loadFailed} busy={false} busyLabel={null} mutationBlocked={false} onReview={() => undefined} onReplace={() => undefined} onRetry={() => undefined} onContinue={() => undefined} onRefresh={() => undefined} />));
    expect(host.textContent).toContain(text);
    if (loading || loadFailed) expect(host.textContent).not.toContain("No document uploaded");
    expect(host.textContent).not.toContain("No current document evidence is available");
  });
});
