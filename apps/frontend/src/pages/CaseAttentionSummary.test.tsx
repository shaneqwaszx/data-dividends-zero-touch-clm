// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";
import projections from "../test-fixtures/attention-projections.json";
import type { HumanInterventionProjection, ZeroTouchCaseSummary, ZeroTouchException } from "../types";
import CaseAttentionSummary, { CasePipelineAttention } from "./CaseAttentionSummary";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
const identity = projections.identityOnly.interventions[0] as HumanInterventionProjection;
const documentProjection = projections.identityAndDocument.interventions[1] as HumanInterventionProjection;
const documentException = projections.identityAndDocument.active_exceptions[0] as ZeroTouchException;
function summary(interventions = [identity], active_exceptions: ZeroTouchException[] = []): ZeroTouchCaseSummary {
  return { interventions, active_exceptions, technical_failure: null, status: "WAITING_FOR_REVIEW", current_stage: "REGISTRY" } as ZeroTouchCaseSummary;
}
let root: Root | null = null; let host: HTMLDivElement | null = null;
afterEach(() => { act(() => root?.unmount()); host?.remove(); root = null; host = null; vi.restoreAllMocks(); });
function render(value: ZeroTouchCaseSummary, navigate = vi.fn()) {
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
  act(() => root!.render(<CaseAttentionSummary summary={value} onNavigate={navigate} />)); return host;
}

describe("authoritative attention record union", () => {
  it("shows the actual backend projection-only identity blocker and its navigation action", () => {
    const navigate = vi.fn(); const value = summary(); const snapshot = structuredClone(value);
    const view = render(value, navigate);
    expect(view.textContent).toContain("1 active blocker"); expect(view.textContent).not.toContain("No immediate blockers");
    const button = [...view.querySelectorAll("button")].find(item => item.textContent === "Action: Correct identity")!;
    expect(button).toBeTruthy(); button.focus(); expect(document.activeElement).toBe(button);
    act(() => button.click()); expect(navigate).toHaveBeenCalledExactlyOnceWith({ kind: "evidence", target: "IDENTITY" });
    expect(value).toEqual(snapshot);
  });
  it("preserves an independent document blocker beside the projection-only identity blocker", () => {
    const view = render(summary([identity, documentProjection], [documentException]));
    expect(view.textContent).toContain("2 active blockers");
    expect(view.textContent).toContain("Initial identity incomplete");
    expect(view.textContent).toContain(documentProjection.title);
  });
  it("counts linked exception and projection once by their record identity", () => {
    const view = render(summary([documentProjection], [documentException]));
    expect(view.textContent).toContain("1 active blocker");
    expect(view.querySelectorAll("li")).toHaveLength(1);
  });
  it("preserves independent projection/exception records even when their codes match", () => {
    const independent = { ...documentProjection, intervention_id: "independent-document-id" };
    const view = render(summary([documentProjection, independent], [documentException]));
    expect(view.textContent).toContain("2 active blockers"); expect(view.querySelectorAll("li")).toHaveLength(2);
  });
  it("lists a projection-only WARNING without counting it as a blocker", () => {
    const warning = { ...identity, blocker_class: "WARNING" as const };
    const view = render(summary([warning, documentProjection], [documentException]));
    expect(view.textContent).toContain("1 active blocker"); expect(view.textContent).toContain("Attention: Initial identity incomplete");
  });
  it("labels projection-only final confirmation as an action, never a blocker", () => {
    const final = { ...identity, blocker_code: "TARGET_CONFIRMATION_REQUIRED", evidence_actions: [{ target: "REVIEW_SEND" as const, label: "Review and send" }] };
    const navigate = vi.fn(); const view = render(summary([final]), navigate);
    expect(view.textContent).toContain("0 active blockers"); expect(view.textContent).toContain("No immediate blockers");
    expect(view.querySelectorAll("button")).toHaveLength(1);
    act(() => view.querySelector("button")!.click()); expect(navigate).toHaveBeenCalledExactlyOnceWith({ kind: "final" });
  });
  it("does not count a WARNING linked to an exception or a linked final action", () => {
    const final = { ...documentException, exception_type: "TARGET_CONFIRMATION_REQUIRED" as const, exception_id: "final" };
    const view = render(summary([{ ...documentProjection, blocker_class: "WARNING" }], [documentException, final]));
    expect(view.textContent).toContain("0 active blockers"); expect(view.textContent).toContain("Action: Review and send");
  });
  it("retains one technical failure and excludes its cancelled exception", () => {
    // Technical-failure automation cancels open exceptions; the backend projects no cancelled record.
    const value = summary([documentProjection], [{ ...documentException, status: "CANCELLED" }]);
    value.status = "TECHNICAL_FAILURE"; value.technical_failure = { code: "SAFE_FAILURE", message: "Safe diagnostic" };
    const view = render(value);
    expect(view.textContent).toContain("1 active blocker"); expect(view.querySelectorAll("li")).toHaveLength(1);
    expect(view.textContent).toContain("Technical failure: SAFE_FAILURE"); expect(view.textContent).not.toContain("No immediate blockers");
  });
  it("does not add intake attention beside a projection-only document blocker", () => {
    const value = summary([documentProjection]); value.status = "PENDING_INPUTS"; value.current_stage = "DOCUMENT";
    const view = render(value);
    expect(view.textContent).toContain("1 active blocker"); expect(view.textContent).not.toContain("Complete document intake");
  });
  it("removes resolved projections on authoritative refresh and replaces them on case switch", () => {
    const view = render(summary()); expect(view.textContent).toContain("Initial identity incomplete");
    act(() => root!.render(<CaseAttentionSummary summary={summary([])} onNavigate={vi.fn()} />));
    expect(view.textContent).not.toContain("Initial identity incomplete"); expect(view.textContent).toContain("No immediate blockers");
    act(() => root!.render(<CaseAttentionSummary summary={summary([documentProjection], [documentException])} onNavigate={vi.fn()} />));
    expect(view.textContent).toContain(documentProjection.title); expect(view.textContent).not.toContain("Initial identity incomplete");
  });
});

describe("pipeline-grouped attention", () => {
  const pipeline = [
    { node_id: "ACRA_REGISTRY", label: "Registry verification", status: "REVIEW_REQUIRED", backend_stage: "REGISTRY", children: [] },
    { node_id: "DOCUMENT_IDP", label: "Document verification", status: "REVIEW_REQUIRED", backend_stage: "DOCUMENT", children: [] },
    { node_id: "RECONCILIATION", label: "Data reconciliation", status: "REVIEW_REQUIRED", backend_stage: "DOCUMENT", children: [] },
  ];
  function renderGrouped(value: ZeroTouchCaseSummary, navigate = vi.fn()) {
    host = document.createElement("div"); document.body.append(host); root = createRoot(host);
    act(() => root!.render(<CasePipelineAttention summary={{ ...value, processing_pipeline: pipeline } as ZeroTouchCaseSummary} onNavigate={navigate} />)); return host;
  }
  const stage = (view: HTMLElement, id: string) => view.querySelector<HTMLElement>(`.ds-stage[data-node-id="${id}"]`)!;
  it("nests each item under the first step owning its stage, collapsed by default", () => {
    const view = renderGrouped(summary([identity, documentProjection], [documentException]));
    expect(view.textContent).toContain("2 active blockers");
    expect(stage(view, "ACRA_REGISTRY").textContent).toContain("Initial identity incomplete");
    expect(stage(view, "DOCUMENT_IDP").textContent).toContain(documentProjection.title);
    expect(stage(view, "RECONCILIATION").querySelector(".stage-attention")).toBeNull();
    expect([...view.querySelectorAll<HTMLElement>(".stage-attention__list")].every(list => list.hidden)).toBe(true);
  });
  it("opens one step, then all steps, and navigates without mutating", () => {
    const navigate = vi.fn(); const value = summary([identity, documentProjection], [documentException]); const snapshot = structuredClone(value);
    const view = renderGrouped(value, navigate);
    const toggle = stage(view, "ACRA_REGISTRY").querySelector<HTMLButtonElement>(".stage-attention__toggle")!;
    expect(toggle.getAttribute("aria-expanded")).toBe("false"); act(() => toggle.click());
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    expect(stage(view, "DOCUMENT_IDP").querySelector<HTMLElement>(".stage-attention__list")!.hidden).toBe(true);
    const all = [...view.querySelectorAll("button")].find(item => item.textContent === "Show all issues")!;
    act(() => all.click());
    expect([...view.querySelectorAll<HTMLElement>(".stage-attention__list")].every(list => !list.hidden)).toBe(true);
    expect(all.textContent).toBe("Hide all issues");
    const action = [...view.querySelectorAll(".attention-line")].find(item => item.textContent?.startsWith("Blocker: Initial identity"))! as HTMLButtonElement;
    expect(action.textContent).toContain("Correct identity →");
    act(() => action.click()); expect(navigate).toHaveBeenCalledExactlyOnceWith({ kind: "evidence", target: "IDENTITY" });
    act(() => all.click());
    expect([...view.querySelectorAll<HTMLElement>(".stage-attention__list")].every(list => list.hidden)).toBe(true);
    expect(value).toEqual(snapshot);
  });
  it("keeps a technical failure visible at the top and hides the toggle when nothing is grouped", () => {
    const value = summary([], []); value.status = "TECHNICAL_FAILURE"; value.technical_failure = { code: "SAFE_FAILURE", message: "Safe diagnostic" };
    const view = renderGrouped(value);
    expect(view.querySelector(".case-attention__general")!.textContent).toContain("Technical failure: SAFE_FAILURE");
    expect([...view.querySelectorAll("button")].some(item => item.textContent === "Show all issues")).toBe(false);
  });
});
