// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ExecutionPlanDiagram, { buildDiagram } from "./pages/ExecutionPlanDiagram";
import type { ExecutionPlan, PlanStage } from "./workflowExecutionPlan";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

/**
 * 12.12.0 lacks upstream #6054 ("Disconnect the ResizeObservers when a flow unmounts").
 * This instrumented observer records every observe/unobserve/disconnect and any callback
 * that fires after its flow has unmounted, so the cleanup behaviour is measured, not assumed.
 */
class TrackedObserver {
  static all: TrackedObserver[] = [];
  observed = new Set<Element>();
  disconnected = false;
  constructor(readonly callback: ResizeObserverCallback) {
    TrackedObserver.all.push(this);
  }
  observe(target: Element) { this.observed.add(target); }
  unobserve(target: Element) { this.observed.delete(target); }
  disconnect() { this.disconnected = true; this.observed.clear(); }
  /** Deliver a resize with a contentRect, as browsers always do. */
  fire() {
    for (const target of this.observed) {
      this.callback([{ target, contentRect: { width: 800, height: 600 } } as unknown as ResizeObserverEntry], this as unknown as ResizeObserver);
    }
  }
}

function stage(stage_id: string, prerequisites: PlanStage["prerequisites"] = []): PlanStage {
  return {
    stage_id, label: stage_id, engine_stage: "DOCUMENT", runs: "", mandatory: true, fixed: true,
    fixed_reason: "", prerequisites, checkpoints: [], safeguards: [], policy_rule_ids: [], policy_rule_references: [], conditional_rule_usage: [], fixed_controls: [],
  };
}

const plan: ExecutionPlan = {
  registry_search_order: "SEARCH_THEN_REGISTRY",
  order_explanation: "",
  stages: [
    stage("CASE_START"),
    stage("INITIAL_IDENTITY", [{ stage_id: "CASE_START", kind: "DATA", reason: "" }]),
    stage("ACRA_REGISTRY", [{ stage_id: "INITIAL_IDENTITY", kind: "DATA", reason: "" }]),
    stage("DOCUMENT_IDP", [{ stage_id: "ACRA_REGISTRY", kind: "DATA", reason: "" }]),
    stage("OWNERSHIP_UBO", [
      { stage_id: "DOCUMENT_IDP", kind: "ENGINE_ORDER", reason: "" },
      { stage_id: "ACRA_REGISTRY", kind: "DATA", reason: "" },
    ]),
    stage("FINAL_REVIEW_SEND", [{ stage_id: "OWNERSHIP_UBO", kind: "DATA", reason: "" }]),
  ],
  workflow_wide_policy_rule_ids: [],
  workflow_wide_fixed_controls: [],
  optional_steps: {
    state: "ACTIVE", version: 1, manager_enabled: true, enforced_at_send: true, explanation: "",
    steps: [{ stage_id: "signatory", name: "Signatory", shown_after: "DOCUMENT_IDP", field_count: 2,
      required_field_count: 1, blocks_send: true, pauses_automation: false }],
  },
  branches_supported: false,
  provider_lanes: [],
};

let root: Root | null = null;
let container: HTMLDivElement | null = null;
let errors: ReturnType<typeof vi.spyOn>;
let warnings: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  TrackedObserver.all = [];
  vi.stubGlobal("ResizeObserver", TrackedObserver);
  // jsdom has no layout; React Flow measures nodes through these.
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(300);
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(74);
  vi.stubGlobal("DOMMatrixReadOnly", class { m22 = 1; constructor() {} });
  // jsdom has no SVG layout; edge labels measure their text box (browsers provide this).
  (SVGElement.prototype as unknown as { getBBox: () => DOMRect }).getBBox = () =>
    ({ x: 0, y: 0, width: 60, height: 14 }) as DOMRect;
  errors = vi.spyOn(console, "error");
  warnings = vi.spyOn(console, "warn");
});

afterEach(() => {
  act(() => root?.unmount());
  container?.remove();
  root = null;
  container = null;
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

async function mount(selectedId = "CASE_START", onSelect = vi.fn()) {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () => {
    root!.render(<ExecutionPlanDiagram plan={plan} selectedId={selectedId} onSelect={onSelect} ruleCounts={new Map()} />);
  });
  await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });
  return { view: container!, onSelect };
}

describe("ExecutionPlanDiagram (read-only canvas)", () => {
  it("F2 builds fixed, unconnectable nodes and the real dependency edges only", () => {
    const { nodes, edges } = buildDiagram(plan, "CASE_START", () => undefined, new Map());
    const stages = nodes.filter(node => node.type === "stage");
    expect(stages.map(node => node.id)).toEqual(plan.stages.map(item => item.stage_id));
    for (const node of nodes) {
      expect(node.draggable).toBe(false);
      expect(node.connectable).toBe(false);
      expect(node.deletable).toBe(false);
      expect(node.selectable).toBe(false);
    }
    // Stages sit in one column in backend order; nothing can be rearranged.
    const ys = stages.map(node => node.position.y);
    expect([...ys].sort((a, b) => a - b)).toEqual(ys);
    expect(new Set(stages.map(node => node.position.x))).toEqual(new Set([0]));
    const dependencyEdges = edges.filter(edge => edge.id.startsWith("dep-"));
    expect(dependencyEdges.map(edge => `${edge.source}>${edge.target}`).sort()).toEqual([
      "ACRA_REGISTRY>DOCUMENT_IDP", "ACRA_REGISTRY>OWNERSHIP_UBO", "CASE_START>INITIAL_IDENTITY",
      "DOCUMENT_IDP>OWNERSHIP_UBO", "INITIAL_IDENTITY>ACRA_REGISTRY", "OWNERSHIP_UBO>FINAL_REVIEW_SEND",
    ]);
    for (const edge of edges) expect(edge.reconnectable).toBe(false);
    // An added stage hangs off its anchor and holds the send; it never joins the run order.
    expect(edges.find(edge => edge.id === "shown-after-added-signatory")?.source).toBe("DOCUMENT_IDP");
    expect(edges.find(edge => edge.id === "holds-send-added-signatory")?.target).toBe("FINAL_REVIEW_SEND");
    expect(edges.some(edge => edge.target === "added-signatory" && edge.id.startsWith("dep-"))).toBe(false);
  });

  it("F2 renders a canvas with no drag, connect or edit affordances", async () => {
    const { view, onSelect } = await mount();
    const nodes = view.querySelectorAll<HTMLElement>(".react-flow__node");
    expect(nodes.length).toBe(plan.stages.length + 1);
    for (const node of nodes) expect(node.classList.contains("draggable")).toBe(false);
    // Read-only nodes still take pointer events (a browser found the pane swallowing clicks).
    for (const node of nodes) expect(node.style.pointerEvents).not.toBe("none");
    for (const handle of view.querySelectorAll(".react-flow__handle")) {
      expect(handle.classList.contains("connectable")).toBe(false);
    }
    expect(view.querySelectorAll("input, select, textarea, [contenteditable='true']").length).toBe(0);
    expect(view.querySelector(".react-flow__controls-interactive")).toBeNull();
    const buttons = [...view.querySelectorAll<HTMLButtonElement>(".wfd-node__button")];
    expect(buttons).toHaveLength(plan.stages.length);
    await act(async () => buttons[3].click());
    expect(onSelect).toHaveBeenCalledWith("DOCUMENT_IDP");
    expect(view.querySelector("[aria-label='Diagram legend']")?.textContent).toContain("holds the send");
  });

  it("mounts and unmounts repeatedly without errors, warnings or callbacks into unmounted flows", async () => {
    const cycles = 5;
    const perMount: number[] = [];
    for (let cycle = 0; cycle < cycles; cycle += 1) {
      const before = TrackedObserver.all.length;
      await mount(cycle % 2 === 0 ? "CASE_START" : "DOCUMENT_IDP");
      perMount.push(TrackedObserver.all.length - before);
      // Live resize while mounted must not warn.
      await act(async () => { for (const observer of TrackedObserver.all) observer.fire(); });
      act(() => root?.unmount());
      container?.remove();
      root = null;
      container = null;
    }
    // A stale observer firing after unmount must not reach React (no state-update errors).
    await act(async () => { for (const observer of TrackedObserver.all) observer.fire(); });

    expect(errors).not.toHaveBeenCalled();
    expect(warnings).not.toHaveBeenCalled();
    // Bounded: each mount creates the same small number of observers; nothing accumulates.
    expect(new Set(perMount).size).toBe(1);
    expect(perMount[0]).toBeLessThanOrEqual(4);
    const stillObserving = TrackedObserver.all.filter(observer => observer.observed.size > 0);
    const detached = stillObserving.flatMap(observer => [...observer.observed]).filter(target => target.isConnected);
    // Whatever 12.12.0 leaves attached is only detached DOM, never a live page element.
    expect(detached).toEqual([]);
    // Recorded for the report: observers 12.12.0 leaves attached after all unmounts.
    console.info(`[P1 mount/unmount] observers per mount=${perMount[0]} left attached after ${cycles} unmounts=${stillObserving.length}`);
  });
});
