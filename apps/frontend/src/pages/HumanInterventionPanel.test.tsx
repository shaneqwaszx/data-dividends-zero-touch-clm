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
