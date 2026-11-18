// @vitest-environment jsdom
// ADR-018 conditional applicability UI (contract CC-8): controls, gating, comparison and run basis.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, useState, type ReactNode } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";

import proposalConditionalDraft from "../../../docs/contracts/fixtures/workflow-governance/proposal_conditional_draft.json";
import runApplicabilityView from "../../../docs/contracts/fixtures/workflow-governance/run_applicability_view.json";
import {
  BEFORE_REGISTRY_EXPLANATION,
  canonicalAppliesTo,
  conditionalAnchorAllowed,
  effectiveAppliesTo,
  fieldWithinStage,
  withAppliesTo,
} from "./components/workflow-governance/applicability";
import { FieldApplicabilityEditor, StageApplicabilityEditor } from "./components/workflow-governance/EntityApplicability";
import { basisHeadline, RunApplicabilityBasis } from "./components/workflow-governance/RunApplicabilityBasis";
import WorkflowCompare from "./pages/WorkflowCompare";
import { governanceFixtures } from "./test-fixtures/workflowGovernance";
import type { AuthenticatedProfile } from "./types";
import type { WorkflowField, WorkflowStage } from "./workflowApi";
import {
  APPLICABILITY_BROADENED,
  CONDITIONAL_ONBOARDING_ANCHORS,
  type PermanentObligationChange,
  type ProposalResponse,
  type RunApplicabilityView,
} from "./workflowGovernanceTypes";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root | null = null;
let host: HTMLDivElement;
afterEach(() => {
  act(() => root?.unmount());
  root = null;
  document.body.innerHTML = "";
  vi.unstubAllGlobals();
});

async function render(node: ReactNode) {
  host = document.createElement("div");
  document.body.append(host);
  root = createRoot(host);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  await act(async () => { root!.render(<QueryClientProvider client={client}>{node}</QueryClientProvider>); });
  for (let index = 0; index < 6; index += 1) await act(async () => { await new Promise(resolveTick => setTimeout(resolveTick, 0)); });
}

const field = (overrides: Partial<WorkflowField> = {}): WorkflowField => ({
  field_id: "f-1", label: "Partnership deed", kind: "TEXT", required: true, options: [], autofill: false, document_label: null, ...overrides,
});
const stage = (overrides: Partial<WorkflowStage> = {}): WorkflowStage => ({
  stage_id: "s-1", name: "Partnership checks", fields: [field()], after_node_id: "ACRA_REGISTRY", ...overrides,
});
const radio = (scope: Element, value: "ALL" | "ONLY") => scope.querySelector<HTMLInputElement>(`input[type="radio"][value="${value}"]`)!;
const describedBy = (item: Element) => (item.getAttribute("aria-describedby") ?? "").split(" ").filter(Boolean)
  .map(id => document.getElementById(id)?.textContent ?? "").join(" ");

function StageHarness({ initial, onboarding, published, onValue }: {
  initial: WorkflowStage; onboarding: boolean; published?: WorkflowStage; onValue: (next: WorkflowStage) => void;
}) {
  const [value, setValue] = useState(initial);
  return <>
    <StageApplicabilityEditor stage={value} onboarding={onboarding} editable published={published}
      onChange={next => { setValue(next); onValue(next); }} />
    {value.fields.map(item => (
      <FieldApplicabilityEditor key={item.field_id} stage={value} field={item} onboarding={onboarding} editable published={published}
        onChange={next => { const updated = { ...value, fields: value.fields.map(f => f.field_id === next.field_id ? next : f) }; setValue(updated); onValue(updated); }} />
    ))}
  </>;
}

describe("canonical applies_to (ADR-018 §2.1)", () => {
  it("sorts, removes duplicates, and uses no key for All or the full set", () => {
    expect(canonicalAppliesTo(["LP", "LLP", "LP"])).toEqual(["LLP", "LP"]);
    expect(canonicalAppliesTo(["GOVERNMENT", "BUSINESS_PARTNERSHIP", "COMPANY"])).toEqual(["BUSINESS_PARTNERSHIP", "COMPANY", "GOVERNMENT"]);
    expect(canonicalAppliesTo([])).toBeUndefined();
    expect(canonicalAppliesTo(["COMPANY", "BUSINESS_PARTNERSHIP", "LLP", "LP", "GOVERNMENT"])).toBeUndefined();
    expect(canonicalAppliesTo(["OTHER"])).toBeUndefined();
    expect(withAppliesTo(stage({ applies_to: ["LLP"] }), undefined)).not.toHaveProperty("applies_to");
    expect(withAppliesTo(stage(), ["LP", "LLP"]).applies_to).toEqual(["LLP", "LP"]);
  });

  it("keeps a field within its stage and intersects them", () => {
    expect(fieldWithinStage({ applies_to: ["LLP", "LP"] }, { applies_to: ["LP"] })).toBe(true);
    expect(fieldWithinStage({ applies_to: ["LLP"] }, { applies_to: ["LP"] })).toBe(false);
    expect(fieldWithinStage({}, { applies_to: ["LP"] })).toBe(true);
    expect(effectiveAppliesTo({ applies_to: ["LLP", "LP"] }, { applies_to: ["LP"] })).toEqual(["LP"]);
    expect(effectiveAppliesTo({}, {})).toBeUndefined();
    expect(effectiveAppliesTo({ applies_to: ["LLP"] }, {})).toEqual(["LLP"]);
    const fixture = proposalConditionalDraft as unknown as ProposalResponse;
    for (const item of fixture.stages) for (const f of item.fields) expect(fieldWithinStage(item, f)).toBe(true);
  });
});

describe("onboarding anchor gating (B2)", () => {
  it("allows conditions only at the registry anchor or later on onboarding", () => {
    for (const anchor of CONDITIONAL_ONBOARDING_ANCHORS) expect(conditionalAnchorAllowed(true, anchor)).toBe(true);
    for (const anchor of ["CASE_START", "INITIAL_IDENTITY", "JURISDICTION", "GOLDTIER_SEARCH", null]) {
      expect(conditionalAnchorAllowed(true, anchor)).toBe(false);
    }
    expect(conditionalAnchorAllowed(false, null)).toBe(true);
  });

  it("disables the stage and field controls before the registry anchor, with the explanation", async () => {
    await render(<StageHarness initial={stage({ after_node_id: "INITIAL_IDENTITY" })} onboarding onValue={vi.fn()} />);
    expect(host.textContent).toContain(BEFORE_REGISTRY_EXPLANATION);
    for (const fieldset of host.querySelectorAll("fieldset")) {
      const only = radio(fieldset, "ONLY");
      expect(only.disabled).toBe(true);
      expect(only.getAttribute("aria-disabled")).toBe("true");
      expect(describedBy(only)).toContain(BEFORE_REGISTRY_EXPLANATION);
      expect(radio(fieldset, "ALL").disabled).toBe(true);
    }
  });

  it("enables the controls at the registry anchor and on non-onboarding workflows", async () => {
    const onValue = vi.fn();
    await render(<StageHarness initial={stage()} onboarding onValue={onValue} />);
    expect(radio(host.querySelector("fieldset")!, "ONLY").disabled).toBe(false);
    act(() => root?.unmount());
    document.body.innerHTML = "";
    await render(<StageHarness initial={stage({ after_node_id: null })} onboarding={false} onValue={onValue} />);
    await act(async () => { radio(host.querySelector("fieldset")!, "ONLY").click(); });
    await act(async () => { host.querySelector<HTMLInputElement>('input[value="LP"]')!.click(); });
    expect(onValue).toHaveBeenLastCalledWith(expect.objectContaining({ applies_to: ["LP"] }));
  });

  it("lets HR clear an existing condition at an early anchor, but not add one", async () => {
    const onValue = vi.fn();
    await render(<StageHarness initial={stage({ after_node_id: "INITIAL_IDENTITY", applies_to: ["LLP"] })} onboarding onValue={onValue} />);
    const stageSet = host.querySelector("fieldset")!;
    expect(stageSet.querySelector<HTMLInputElement>('input[value="LLP"]')!.disabled).toBe(true);
    await act(async () => { radio(stageSet, "ALL").click(); });
    expect(onValue).toHaveBeenLastCalledWith(expect.not.objectContaining({ applies_to: expect.anything() }));
  });

  it("refuses an optional field for everyone becoming a conditional required field (B9)", async () => {
    const published = stage({ fields: [field({ required: false })] });
    await render(<StageHarness initial={stage({ fields: [field({ required: true })] })} onboarding published={published} onValue={vi.fn()} />);
    const fieldSet = host.querySelectorAll("fieldset")[1];
    expect(radio(fieldSet, "ONLY").disabled).toBe(true);
    expect(describedBy(radio(fieldSet, "ONLY"))).toContain("B9");
  });
});

describe("Director comparison with applicability (ADR-018 §4.4, §5)", () => {
  const director: AuthenticatedProfile = {
    user_id: "director-synthetic-1", display_name: "Director", role: "DIRECTOR", team_id: null, team_display_name: null,
    team_type: null, team_description: "", client_scope_label: "", capabilities: ["POLICY_APPROVE"],
  };

  it("labels APPLICABILITY_BROADENED, shows the applicability change and lists conditional obligations", async () => {
    const data = governanceFixtures.comparison();
    const proposed = { ...data.proposal.stages[0], applies_to: ["LLP", "LP"] as WorkflowStage["applies_to"] };
    data.proposal.stages = [proposed];
    data.active_version = { version: 1, stages: [{ ...proposed, applies_to: ["LLP"] }], activated_at: "2026-11-17T10:00:00Z", activated_by: "director-legacy-1" };
    data.stages = data.stages.map(item => ({ ...item, change: "CHANGED" as const }));
    data.permanent_obligations[0] = { ...data.permanent_obligations[0], change: APPLICABILITY_BROADENED as PermanentObligationChange };
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(data), { status: 200, headers: { "Content-Type": "application/json" } })));
    await render(<WorkflowCompare actor={director} workflowId={data.workflow_id} proposalId={data.proposal.proposal_id} onBack={vi.fn()} />);

    expect(host.querySelector('[data-testid="applicability-change"]')!.textContent)
      .toBe("Applies to: Only LLP (and entities whose legal form is unverified) → Only LLP, LP (and entities whose legal form is unverified)");
    const obligations = host.querySelector('[aria-label="Permanent obligations"]')!;
    expect(obligations.textContent).toContain("Applicability broadened: Sanctions attestation.");
    expect(obligations.textContent).toContain("Conditional: applies to LLP, LP");
    expect(host.querySelector('[data-testid="compare-conditional-obligations"]')!.textContent).toContain("Sanctions attestation: Only LLP, LP");
  });

  it("shows no applicability section for unconditional proposals", async () => {
    const data = governanceFixtures.comparison();
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(data), { status: 200, headers: { "Content-Type": "application/json" } })));
    await render(<WorkflowCompare actor={director} workflowId={data.workflow_id} proposalId={data.proposal.proposal_id} onBack={vi.fn()} />);
    expect(host.querySelector('[data-testid="compare-conditional-obligations"]')).toBeNull();
    expect(host.textContent).toContain("Applies to: All entities");
    expect(host.textContent).not.toContain("Conditional:");
  });
});

describe("run applicability basis (B11, §3.5 F6)", () => {
  const view = () => structuredClone(runApplicabilityView) as unknown as RunApplicabilityView;

  it("shows REGISTRY_BOUND with its environment, the escalated conflict and the effective basis", async () => {
    await render(<RunApplicabilityBasis view={view()} />);
    expect(host.querySelector('[data-testid="run-applicability-basis"]')!.textContent).toBe("Registry-bound (Mock): LLP");
    expect(host.textContent).toContain("REGISTRY_BOUND · Mock");
    expect(host.textContent).toContain("The basis is frozen for this run.");
    expect(host.querySelector('[data-testid="run-applicability-effective"]')!.textContent).toContain("every conditional step applies");
    const conflict = host.querySelector('[data-testid="run-applicability-conflict"]')!;
    expect(conflict.textContent).toContain("The registry now reports LP");
    expect(conflict.textContent).toContain("held before send");
    expect(conflict.textContent).toContain("Escalated by rm-synthetic-1");
  });

  it("shows UNVERIFIED with its environment and an unescalated conflict's recovery", async () => {
    expect(basisHeadline({ ...view(), status: "UNVERIFIED", legal_form: null, source_environment: null, conflict: null }))
      .toBe("Not verified (no registry source): all conditional steps apply");
    expect(basisHeadline({ ...view(), status: "UNVERIFIED", legal_form: null, source_environment: "SANDBOX", conflict: null }))
      .toBe("Not verified (Sandbox): all conditional steps apply");
    const pending = view();
    pending.effective_legal_form = "LLP";
    pending.conflict = { ...pending.conflict!, escalated: false, escalated_by: null, escalated_at: null };
    await render(<RunApplicabilityBasis view={pending} />);
    expect(host.querySelector('[data-testid="run-applicability-effective"]')).toBeNull();
    expect(host.querySelector('[data-testid="run-applicability-conflict"]')!.textContent).toContain('"Apply all conditional steps"');
  });

  it("renders nothing without a basis", async () => {
    await render(<RunApplicabilityBasis view={null} />);
    expect(host.textContent).toBe("");
  });
});
