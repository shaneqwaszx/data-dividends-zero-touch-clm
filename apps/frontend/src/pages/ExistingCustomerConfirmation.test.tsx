// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { describe, expect, it, vi } from "vitest";
import type { ZeroTouchCaseSummary } from "../types";
import HumanInterventionPanel from "./HumanInterventionPanel";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean })
  .IS_REACT_ACT_ENVIRONMENT = true;

function summary(authorized = true, actionable = true): ZeroTouchCaseSummary {
  return {
    evidence_decision_authorized: authorized, active_exceptions: [],
    interventions: [{
      intervention_id: "retained-search", owning_stage: "GOLDTIER_SEARCH",
      owning_stage_label: "Existing-customer search", title: "Possible existing customer found",
      explanation: "Retained provider candidate needs a creator decision.",
      blocker_code: "GT_SEARCH_IDENTITY_REVIEW_REQUIRED",
      candidate_summaries: [{ party_id: "143878", legal_name: "SYNTHETIC CUSTOMER" }],
      required_evidence_or_input: ["Compare identity evidence"], authorized_actions: [],
      expected_next_step: "Retain maker confirmation without target dispatch",
      existing_customer_confirmation_action: actionable
        ? "CONFIRM_EXISTING_GOLDTIER_CUSTOMER" : null,
    }],
  } as unknown as ZeroTouchCaseSummary;
}

describe("Existing customer confirmation", () => {
  it("requires a rationale and submits only that decision about the retained candidate", () => {
    const callback = vi.fn();
    const container = document.createElement("div");
    document.body.append(container);
    const root = createRoot(container);
    try {
      act(() => root.render(<HumanInterventionPanel summary={summary()} isBusy={false}
        onResolve={vi.fn()} onConfirmExisting={callback} />));
      expect(container.textContent).toContain("143878");
      expect(container.textContent).not.toContain("Correct identity and recheck");
      expect(container.querySelectorAll("input")).toHaveLength(1);
      const button = container.querySelector<HTMLButtonElement>("button")!;
      expect(button.disabled).toBe(true);
      const input = container.querySelector<HTMLInputElement>("input")!;
      act(() => {
        Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!
          .call(input, "Compared synthetic registry and candidate.");
        input.dispatchEvent(new Event("input", { bubbles: true }));
      });
      expect(button.disabled).toBe(false);
      act(() => container.querySelector("form")!.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      ));
      expect(callback).toHaveBeenCalledWith("Compared synthetic registry and candidate.");
    } finally {
      act(() => root.unmount()); container.remove();
    }
  });

  it.each([[false, true], [true, false]])(
    "hides confirmation without creator authority or a backend action (%s, %s)",
    (authorized, actionable) => {
      const container = document.createElement("div");
      const root = createRoot(container);
      act(() => root.render(<HumanInterventionPanel summary={summary(authorized, actionable)}
        isBusy={false} onResolve={vi.fn()} onConfirmExisting={vi.fn()} />));
      expect(container.querySelector("form")).toBeNull();
      act(() => root.unmount());
    },
  );
});
