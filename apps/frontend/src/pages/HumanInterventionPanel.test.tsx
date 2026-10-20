// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { HumanInterventionProjection, ZeroTouchCaseSummary } from "../types";
import HumanInterventionPanel from "./HumanInterventionPanel";

function intervention(index: number, overrides: Partial<HumanInterventionProjection> = {}): HumanInterventionProjection {
  return {
    intervention_id: `document-field-${index}`, owning_stage: "DOCUMENT",
    owning_stage_label: "Documents / reconciliation",
    title: "Document or reconciliation review required",
    blocker_code: `FIELD_REVIEW_${index}`,
    explanation: "Document evidence requires review before reconciliation.",
    required_evidence_or_input: [`Review field ${index} on document ${index}.`],
    authorized_actions: [], no_action_reason: null,
    expected_next_step: `Retain the decision for field ${index}.`, candidate_summaries: [],
    evidence_actions: [{ target: "DOCUMENTS", label: "Review document evidence" }],
    ...overrides,
  };
}

function markup(interventions: HumanInterventionProjection[]) {
  return renderToStaticMarkup(<HumanInterventionPanel
    summary={{ interventions, active_exceptions: [] } as unknown as ZeroTouchCaseSummary}
    isBusy={false} onResolve={vi.fn()} onEvidenceAction={vi.fn()} />);
}

describe("HumanInterventionPanel compact summaries", () => {
  it("shows one equivalent warning and count while retaining every distinct evidence record", () => {
    const html = markup([1, 2, 3, 4].map(index => intervention(index)));
    expect(html.match(/<h3[^>]*>Document or reconciliation review required/g)).toHaveLength(1);
    expect(html.match(/Document evidence requires review before reconciliation\./g)).toHaveLength(1);
    expect(html).toContain("4 related blockers");
    expect(html.match(/class="intervention-evidence-record"/g)).toHaveLength(4);
    for (const index of [1, 2, 3, 4]) {
      expect(html).toContain(`data-intervention-id="document-field-${index}"`);
      expect(html).toContain(`FIELD_REVIEW_${index}`);
      expect(html).toContain(`Review field ${index} on document ${index}.`);
      expect(html).toContain(`Retain the decision for field ${index}.`);
    }
    expect(html.match(/>Review document evidence<\/button>/g)).toHaveLength(1);
  });

  it("keeps different reasons and unavailable-action boundaries separate", () => {
    const html = markup([
      intervention(1),
      intervention(2, { explanation: "A different current source needs replacement." }),
      intervention(3, { no_action_reason: "Provider evidence is unavailable." }),
    ]);
    expect(html.match(/class="card intervention-card"/g)).toHaveLength(3);
    expect(html).toContain("A different current source needs replacement.");
    expect(html).toContain("Provider evidence is unavailable.");
    expect(html).not.toContain("related blockers");
  });

  it("never groups distinct resolution or existing-customer authorities into an informational warning", () => {
    const html = markup([
      intervention(1), intervention(2),
      intervention(3, { authorized_actions: [{ action: "KEEP_REGISTRY_VALUE", label: "Keep registry value", description: "Retain current source." }] }),
      intervention(4, { existing_customer_confirmation_action: "CONFIRM_EXISTING_GOLDTIER_CUSTOMER" }),
    ]);
    expect(html.match(/class="card intervention-card"/g)).toHaveLength(3);
    expect(html).toContain("2 related blockers");
    expect(html).toContain("Keep registry value");
    expect(html.match(/data-intervention-id="document-field-/g)).toHaveLength(2);
  });
});


(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

function visiblyAvailable(element: Element): boolean {
  for (let node: Element | null = element; node; node = node.parentElement) {
    if (node instanceof HTMLElement && (node.hidden || getComputedStyle(node).display === "none")) return false;
    if (node instanceof HTMLDetailsElement && !node.open
      && !node.querySelector(":scope > summary")?.contains(element)) return false;
  }
  return true;
}

describe("current intervention essentials", () => {
  it("shows every distinct required input, next step and resolution condition with Why closed and performs no mutation on toggles", async () => {
    const host = document.createElement("div"); document.body.append(host); const root = createRoot(host);
    const onResolve = vi.fn(), onEvidenceAction = vi.fn(), onConfirmExisting = vi.fn();
    const items = [1, 2].map(index => intervention(index, { resolution_condition: `Current evidence ${index} retained.` }));
    try {
      await act(async () => root.render(<HumanInterventionPanel
        summary={{ interventions: items, active_exceptions: [] } as unknown as ZeroTouchCaseSummary}
        isBusy={false} onResolve={onResolve} onEvidenceAction={onEvidenceAction} onConfirmExisting={onConfirmExisting} />));
      expect(host.querySelector("details")!.open).toBe(false);
      for (const item of items) {
        for (const text of [...item.required_evidence_or_input, item.expected_next_step, item.resolution_condition!]) {
          const field = [...host.querySelectorAll("dd")].find(e => e.textContent === text)!;
          expect(field, text).toBeDefined(); expect(visiblyAvailable(field), text).toBe(true);
        }
      }
      expect(host.querySelectorAll("button")).toHaveLength(1);
      for (const open of [true, false]) await act(async () => { host.querySelector("details")!.open = open; });
      expect(onResolve).not.toHaveBeenCalled(); expect(onEvidenceAction).not.toHaveBeenCalled(); expect(onConfirmExisting).not.toHaveBeenCalled();
    } finally { await act(async () => root.unmount()); host.remove(); }
  });
});


describe("intervention authority and drafts", () => {
  it("retains explicit candidate rationale through disclosure toggles and denies confirmation when backend authority is absent", async () => {
    const host = document.createElement("div"); document.body.append(host); const root = createRoot(host);
    const onResolve = vi.fn(), onConfirmExisting = vi.fn();
    const item = intervention(1, {
      existing_customer_confirmation_action: "CONFIRM_EXISTING_GOLDTIER_CUSTOMER",
      candidate_summaries: [{ party_id: "SYNTHETIC_PARTY", legal_name: "Synthetic retained customer", registration_number: null, country: null, legal_form: null }],
    });
    const render = async (authorized: boolean, busy = false) => { await act(async () => root.render(<HumanInterventionPanel
      summary={{ interventions: [item], active_exceptions: [], evidence_decision_authorized: authorized } as unknown as ZeroTouchCaseSummary}
      isBusy={busy} onResolve={onResolve} onConfirmExisting={onConfirmExisting} />)); };
    try {
      await render(true);
      const input = host.querySelector<HTMLInputElement>("#existing-customer-confirmation-rationale")!;
      await act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(input, "Compared explicit synthetic identity"); input.dispatchEvent(new Event("input", { bubbles: true })); });
      for (const open of [true, false]) await act(async () => { host.querySelector("details")!.open = open; });
      expect(input.value).toBe("Compared explicit synthetic identity"); expect(visiblyAvailable(input)).toBe(true);
      expect(onResolve).not.toHaveBeenCalled(); expect(onConfirmExisting).not.toHaveBeenCalled();
      await render(true, true); expect(input.disabled).toBe(true);
      expect(input.value).toBe("Compared explicit synthetic identity");
      expect([...host.querySelectorAll("button")].every(button => button.disabled)).toBe(true);
      await act(async () => host.querySelector("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
      expect(onConfirmExisting).not.toHaveBeenCalled();
      await render(true, false);
      await act(async () => host.querySelector("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
      expect(onConfirmExisting).toHaveBeenCalledExactlyOnceWith("Compared explicit synthetic identity");
      await render(false); expect(host.querySelector("form")).toBeNull(); expect(onConfirmExisting).toHaveBeenCalledTimes(1);
    } finally { await act(async () => root.unmount()); host.remove(); }
  });

  it("keeps unavailable and frozen explanations visible without creating fallback actions", async () => {
    const host = document.createElement("div"); document.body.append(host); const root = createRoot(host);
    try {
      await act(async () => root.render(<HumanInterventionPanel summary={{ interventions: [intervention(1, {
        evidence_actions: [], no_action_reason: "Current evidence is frozen; no correction is authorized.",
        resolution_condition: "An authorized new review is required.",
      })], active_exceptions: [] } as unknown as ZeroTouchCaseSummary} isBusy={false} onResolve={vi.fn()} />));
      expect(host.querySelectorAll("button,input,select,textarea")).toHaveLength(0);
      expect(visiblyAvailable(host.querySelector('[role="status"]')!)).toBe(true);
      expect([...host.querySelectorAll("dd")].every(visiblyAvailable)).toBe(true);
      expect(host.querySelector("details")!.open).toBe(false);
    } finally { await act(async () => root.unmount()); host.remove(); }
  });
});
