// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";

import WorkflowDesigner, { optionalStepNote, optionalStepsByAnchor } from "./pages/WorkflowDesigner";
import { clearSessionQueries } from "./queryClient";
import type { AuthenticatedProfile, Capability, PolicyCatalogue, PolicyRule } from "./types";
import {
  bindRules,
  canViewExecutionPlan,
  executionPlanQueryKeys,
  type ExecutionPlan,
  type PlanStage,
} from "./workflowExecutionPlan";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const LABELS: Array<[string, string, string[]]> = [
  ["CASE_START", "Case created", []],
  ["INITIAL_IDENTITY", "Initial identity", []],
  ["JURISDICTION", "Jurisdiction", ["REGISTRY_PROVIDER"]],
  ["GOLDTIER_SEARCH", "Existing-customer search", []],
  ["ACRA_REGISTRY", "Registry verification", ["REGISTRY_FRESHNESS_DAYS"]],
  ["DOCUMENT_IDP", "Document verification", []],
  ["RECONCILIATION", "Data reconciliation", []],
  ["OWNERSHIP_UBO", "Ownership & UBO", ["OWNERSHIP_UBO_THRESHOLD_PERCENT"]],
  ["ADVISORY", "Risk assessment", ["ENTITY_RESOLUTION_AUTO_MATCH_THRESHOLD"]],
  ["GOLDTIER_DETAILS", "GoldTier Details & Status", []],
  ["FINAL_REVIEW_SEND", "Final review & send", []],
  ["APPROVAL_GATE", "Human approval gate", []],
];

// The entity-resolution rule is defined once under Risk assessment and read by reference
// at Existing-customer search and Final review & send (P2-1).
const SHARED_RULE = "ENTITY_RESOLUTION_AUTO_MATCH_THRESHOLD";
const REFERENCES: Record<string, PlanStage["policy_rule_references"]> = {
  GOLDTIER_SEARCH: [{ rule_id: SHARED_RULE, primary_stage_id: "ADVISORY", consumer: "OnboardingService._resolve_target_candidates", effect: "Scores the GoldTier Search candidates." }],
  FINAL_REVIEW_SEND: [{ rule_id: SHARED_RULE, primary_stage_id: "ADVISORY", consumer: "OnboardingService._submit_to_goldtier", effect: "Decides existing-party reuse at the send." }],
};

// N1: Risk assessment owns the rule in the catalogue but reads it only with demo candidate data.
const CONDITIONAL: PlanStage["conditional_rule_usage"][number] = {
  rule_ids: [SHARED_RULE], consumer: "OnboardingIntelligenceProjectionService.evaluate",
  condition: "Runs only when demo candidate data is enabled (demo controls on).",
  effect: "Scores the case identity against the demo candidate parties.", runs_in_this_environment: false,
};

function stage(stage_id: string, label: string, policy_rule_ids: string[]): PlanStage {
  return {
    stage_id, label, engine_stage: "DOCUMENT", runs: `${label} runs.`, mandatory: true, fixed: true,
    fixed_reason: `${label} is fixed.`, prerequisites: [], checkpoints: ["checkpoint"],
    safeguards: ["safeguard"], policy_rule_ids, policy_rule_references: REFERENCES[stage_id] ?? [],
    conditional_rule_usage: stage_id === "ADVISORY" ? [CONDITIONAL] : [], fixed_controls: [],
  };
}

function plan(overrides: Partial<ExecutionPlan> = {}, registryFirst = false): ExecutionPlan {
  const stages = LABELS.map(([id, label, rules]) => stage(id, label, rules));
  if (registryFirst) [stages[3], stages[4]] = [stages[4], stages[3]];
  return {
    registry_search_order: registryFirst ? "REGISTRY_THEN_SEARCH" : "SEARCH_THEN_REGISTRY",
    order_explanation: "Order explanation.",
    stages,
    workflow_wide_policy_rule_ids: ["WORKFLOW_SUPPORTED_STAGES"],
    workflow_wide_fixed_controls: [{ label: "SLA target (D-127)", value: "10 days", source: "SLA_TARGET_MS" }],
    optional_steps: {
      state: "ACTIVE", version: 2, manager_enabled: true, enforced_at_send: true,
      explanation: "Optional explanation.",
      steps: [
        { stage_id: "signatory", name: "Authorised signatory details", shown_after: "DOCUMENT_IDP",
          field_count: 3, required_field_count: 2, blocks_send: true, pauses_automation: false },
      ],
    },
    branches_supported: false,
    provider_lanes: [{ lane: "GOLDTIER", mode: "SANDBOX", evidence_class: "PARTIAL" }],
    ...overrides,
  };
}

function rule(policy_id: string, overrides: Partial<PolicyRule> = {}): PolicyRule {
  return {
    policy_id, category: "Test", name: `${policy_id} name`, description: "d",
    value: { type: "INTEGER", value: 90 }, value_type: "INTEGER",
    default_value: { type: "INTEGER", value: 90 }, minimum: 1, maximum: 365, allowed_values: [],
    classifications: ["PROJECT_DEFAULT"], authority: null, default_authority: null,
    enforcement: "RUNTIME_ENFORCED", version: 1, created_at: "", updated_at: "", updated_by: "system",
    ...overrides,
  };
}

const catalogue = (extra: PolicyRule[] = []): PolicyCatalogue => ({
  catalogue_id: "GLOBAL_POLICY_CATALOGUE", version: 1, created_at: "", updated_at: "", updated_by: "system",
  rules: [
    rule("REGISTRY_PROVIDER", { enforcement: "NOT_EDITABLE", value: { type: "STRING", value: "ACRA" }, value_type: "STRING", minimum: null, maximum: null, allowed_values: ["ACRA"] }),
    rule("REGISTRY_FRESHNESS_DAYS"),
    rule("OWNERSHIP_UBO_THRESHOLD_PERCENT"),
    rule("ENTITY_RESOLUTION_AUTO_MATCH_THRESHOLD"),
    rule("WORKFLOW_SUPPORTED_STAGES"),
    ...extra,
  ],
});

function actor(capabilities: Capability[], user_id = "biz-ops"): AuthenticatedProfile {
  return {
    user_id, display_name: user_id, role: "HR", team_id: null, team_display_name: null, team_type: null,
    team_description: "", client_scope_label: "", capabilities,
  };
}

const HR = actor(["POLICY_VIEW", "POLICY_MUTATE"]);

let root: Root | null = null;
let container: HTMLDivElement | null = null;

afterEach(() => {
  act(() => root?.unmount());
  container?.remove();
  root = null;
  container = null;
  vi.unstubAllGlobals();
});

function respond(planBody: unknown, status = 200, catalogueBody: unknown = catalogue()) {
  const fetchMock = vi.fn(async (url: string) => {
    const body = String(url).includes("execution-plan") ? planBody : catalogueBody;
    const code = String(url).includes("execution-plan") ? status : 200;
    return new Response(JSON.stringify(code === 200 ? body : { detail: { code: "EXECUTION_PLAN_FORBIDDEN", message: "Forbidden" } }), {
      status: code, headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

async function render(profile: AuthenticatedProfile = HR, client = new QueryClient()) {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () => {
    root!.render(<QueryClientProvider client={client}><WorkflowDesigner actor={profile} initialView="outline" /></QueryClientProvider>);
  });
  await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });
  return { container: container!, client };
}

const stageButtons = (element: HTMLElement) =>
  [...element.querySelectorAll<HTMLButtonElement>(".wfd-stage")];

describe("WorkflowDesigner", () => {
  it("F1 renders the twelve mandatory stages in the backend's order, both environments", async () => {
    for (const registryFirst of [false, true]) {
      respond(plan({}, registryFirst));
      const { container: view } = await render();
      const labels = stageButtons(view).map(button => button.querySelector(".wfd-stage__label")?.textContent);
      expect(labels).toEqual(plan({}, registryFirst).stages.map(item => item.label));
      expect(view.textContent).toContain(
        registryFirst ? "ACRA registry verification runs before the GoldTier search" : "GoldTier search runs before ACRA registry verification",
      );
      act(() => root?.unmount());
      container?.remove();
    }
  });

  it("F2 offers no editing, moving, inserting, saving or publishing", async () => {
    respond(plan());
    const { container: view } = await render();
    expect(view.querySelector("[draggable='true']")).toBeNull();
    const words = [...view.querySelectorAll("button")].map(button => button.textContent?.toLowerCase() ?? "");
    for (const forbidden of ["save", "publish", "insert", "move", "delete", "add stage", "connect"]) {
      expect(words.some(text => text.includes(forbidden))).toBe(false);
    }
    expect(view.querySelectorAll("input, select, textarea").length).toBe(0);
    for (const button of stageButtons(view)) expect(button.textContent).toContain("Fixed");
  });

  it("F3 labels added stages as blocking the send, never pausing automation", async () => {
    respond(plan());
    const { container: view } = await render();
    const added = view.querySelector(".wfd-added");
    expect(added?.textContent).toContain("Authorised signatory details");
    expect(added?.textContent).toContain("does not pause automation");
    expect(added?.textContent).toContain("Must be confirmed before Final review & send");
    expect(view.textContent).toContain("Conditional branches are not supported by the current backend");
    const grouped = optionalStepsByAnchor(plan());
    expect(grouped.get("DOCUMENT_IDP")?.map(step => step.stage_id)).toEqual(["signatory"]);
    expect(optionalStepNote({ ...plan().optional_steps.steps[0], blocks_send: false })).toContain("does not block the send");
  });

  it("F4 shows each bound rule with its value, range and enforcement, and keeps unbound rules", async () => {
    respond(plan(), 200, catalogue([rule("CUSTOM_SHOWCASE_RULE", { enforcement: "DISPLAY_SHOWCASE_ONLY" })]));
    const { container: view } = await render();
    const registry = stageButtons(view).find(button => button.textContent?.includes("Registry verification"))!;
    await act(async () => registry.click());
    const panel = view.querySelector(".wfd-panel")!;
    expect(panel.textContent).toContain("REGISTRY_FRESHNESS_DAYS");
    expect(panel.textContent).toContain("90");
    expect(panel.textContent).toContain("1–365");
    expect(panel.textContent).toContain("Runtime enforced");
    const wide = [...panel.querySelectorAll("button")].find(button => button.textContent?.includes("Workflow-wide"))!;
    await act(async () => wide.click());
    expect(panel.textContent).toContain("WORKFLOW_SUPPORTED_STAGES");
    expect(panel.textContent).toContain("CUSTOM_SHOWCASE_RULE");
    expect(panel.textContent).toContain("10 days");
    const bound = bindRules(plan(), catalogue());
    expect(bound.missing).toEqual([]);
    expect(bound.byStage.get("ADVISORY")?.map(item => item.policy_id)).toEqual(["ENTITY_RESOLUTION_AUTO_MATCH_THRESHOLD"]);
  });

  it("F4b shows a shared rule once, with its other consumers and as a reference where it is read", async () => {
    respond(plan(), 200, catalogue());
    const { container: view } = await render();
    const pick = async (name: string) => {
      const button = stageButtons(view).find(item => item.textContent?.includes(name))!;
      await act(async () => button.click());
      return view.querySelector(".wfd-panel")!;
    };
    // Primary binding: the definition and value, plus every other stage that reads it.
    const risk = await pick("Risk assessment");
    const primary = risk.querySelector("[aria-label='Policy rules for this stage'] .wfd-rule")!;
    expect(primary.textContent).toContain(SHARED_RULE);
    expect(primary.textContent).toContain("90");
    expect(primary.querySelector(".wfd-rule__shared")?.textContent)
      .toContain("Also used by Existing-customer search, Final review & send. Changing it changes those stages too.");
    expect(risk.textContent).not.toContain("Shared rules also used here");
    // N1: catalogue ownership is distinguished from conditional runtime use.
    const note = risk.querySelector("[role='note'][aria-label='Conditional runtime use']")!;
    expect(note.textContent).toContain("Catalogue owner · conditional use");
    expect(note.textContent).toContain("Runs only when demo candidate data is enabled");
    expect(note.textContent).toContain("In this environment: not running (demo candidate data off).");

    // Usage reference: same catalogue value, labelled as defined elsewhere, never a second definition.
    const search = await pick("Existing-customer search");
    expect(search.textContent).not.toContain("No policy rule applies to this stage");
    expect(search.textContent).toContain("it reads the shared rules below");
    expect(search.querySelector("[aria-label='Policy rules for this stage']")).toBeNull();
    const group = search.querySelector("[role='group'][aria-label='Shared rules defined under Risk assessment']")!;
    expect(group.textContent).toContain("Usage reference");
    expect(group.textContent).toContain("Defined under Risk assessment");
    expect(group.textContent).toContain("Scores the GoldTier Search candidates.");
    expect(group.textContent).toContain("Also used by Final review & send.");
    expect(group.querySelector(".wfd-rule--shared")?.textContent).toContain("90");

    expect(search.querySelector("[aria-label='Conditional runtime use']")).toBeNull();

    const send = await pick("Final review & send");
    expect(send.textContent).toContain("Decides existing-party reuse at the send.");
    expect(send.textContent).toContain("Also used by Existing-customer search.");

    expect(send.querySelector("[aria-label='Conditional runtime use']")).toBeNull();

    const running = plan();
    running.stages = running.stages.map(item => item.stage_id === "ADVISORY"
      ? { ...item, conditional_rule_usage: [{ ...CONDITIONAL, runs_in_this_environment: true }] }
      : item);
    act(() => root?.unmount());
    container?.remove();
    respond(running, 200, catalogue());
    const { container: demo } = await render();
    const riskButton = stageButtons(demo).find(item => item.textContent?.includes("Risk assessment"))!;
    await act(async () => riskButton.click());
    expect(demo.querySelector("[aria-label='Conditional runtime use']")?.textContent)
      .toContain("In this environment: running (demo candidate data on).");

    const bound = bindRules(plan(), catalogue());
    expect(bound.usedBy.get(SHARED_RULE)).toEqual(["GOLDTIER_SEARCH", "FINAL_REVIEW_SEND"]);
    expect(bound.sharedByStage.get("GOLDTIER_SEARCH")?.[0].rule).toBe(bound.byStage.get("ADVISORY")?.[0]);
    expect(bound.missing).toEqual([]);
    // A reference to a rule the catalogue does not hold is reported, never silently dropped.
    const without = catalogue();
    without.rules = without.rules.filter(item => item.policy_id !== SHARED_RULE);
    expect(bindRules(plan(), without).missing).toContain(SHARED_RULE);
  });

  it("F5 the outline is an ordered list of keyboard-operable buttons", async () => {
    respond(plan());
    const { container: view } = await render();
    const list = view.querySelector("ol.wfd-outline");
    expect(list?.getAttribute("aria-label")).toContain("in run order");
    const buttons = stageButtons(view);
    expect(buttons).toHaveLength(12);
    for (const button of buttons) {
      expect(button.tagName).toBe("BUTTON");
      expect(button.getAttribute("type")).toBe("button");
    }
    buttons[7].focus();
    expect(document.activeElement).toBe(buttons[7]);
    await act(async () => buttons[7].click());
    expect(buttons[7].getAttribute("aria-pressed")).toBe("true");
    expect(view.querySelector(".wfd-panel h2")?.textContent).toBe("Ownership & UBO");
  });

  it("F6 only HR and Directors see it, and its data is user-scoped and cleared with the session", async () => {
    expect(canViewExecutionPlan(actor(["POLICY_VIEW", "POLICY_MUTATE"]))).toBe(true);
    expect(canViewExecutionPlan(actor(["POLICY_VIEW", "POLICY_APPROVE"]))).toBe(true);
    expect(canViewExecutionPlan(actor(["POLICY_VIEW", "CASE_ACCESS"]))).toBe(false);
    const fetchMock = respond(plan());
    const { container: view } = await render(actor(["POLICY_VIEW", "CASE_ACCESS"], "maya-lim"));
    expect(view.textContent).toContain("available to HR administrators and Directors");
    expect(fetchMock).not.toHaveBeenCalled();
    act(() => root?.unmount());
    container?.remove();

    respond(plan());
    const client = new QueryClient();
    await render(HR, client);
    expect(executionPlanQueryKeys.plan("biz-ops")).toEqual(["auth", "biz-ops", "workflows", "execution-plan"]);
    expect(client.getQueryData(executionPlanQueryKeys.plan("biz-ops"))).toBeTruthy();
    clearSessionQueries(client);
    expect(client.getQueryData(executionPlanQueryKeys.plan("biz-ops"))).toBeUndefined();
  });

  it("F7 a refused or failed load shows a safe message, never a blank canvas", async () => {
    respond(plan(), 403);
    const { container: denied } = await render();
    expect(denied.querySelector("[role='alert']")?.textContent).toContain("available to HR administrators and Directors");
    act(() => root?.unmount());
    container?.remove();

    respond(plan(), 500);
    const { container: failed } = await render();
    expect(failed.querySelector("[role='alert']")?.textContent).toContain("could not be loaded");
    expect(failed.querySelector("[role='alert'] button")?.textContent).toBe("Try again");
  });

  it("F7 an unreadable workflow store is announced, not shown as empty", async () => {
    respond(plan({
      optional_steps: {
        state: "UNAVAILABLE", version: null, manager_enabled: false, enforced_at_send: true,
        explanation: "The workflow store cannot be read.", steps: [],
      },
    }));
    const { container: view } = await render();
    const alert = [...view.querySelectorAll("[role='alert']")].map(item => item.textContent ?? "").join(" ");
    expect(alert).toContain("Workflow check unavailable");
    expect(alert).toContain("workflow manager switched off");
  });
});
