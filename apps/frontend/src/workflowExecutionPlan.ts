import { API_BASE_URL, authenticatedFetch, parseResponse } from "./api";
import type { AuthenticatedProfile, PolicyCatalogue, PolicyRule, PolicyValue } from "./types";

/** Read-only P1 view of what the backend actually runs. Nothing here edits a workflow. */

export type RegistrySearchOrder = "SEARCH_THEN_REGISTRY" | "REGISTRY_THEN_SEARCH";

export interface PlanPrerequisite {
  stage_id: string;
  kind: "DATA" | "ENGINE_ORDER";
  reason: string;
}

export interface PlanFixedControl {
  label: string;
  value: string;
  source: string;
}

/** This stage also reads a rule whose one authoritative definition sits under another stage. */
export interface PlanRuleReference {
  rule_id: string;
  primary_stage_id: string;
  consumer: string;
  effect: string;
}

/** Rules this stage owns in the catalogue but reads at runtime only under a condition. */
export interface PlanConditionalRuleUsage {
  rule_ids: string[];
  consumer: string;
  condition: string;
  effect: string;
  runs_in_this_environment: boolean;
}

export interface PlanStage {
  stage_id: string;
  label: string;
  engine_stage: string;
  runs: string;
  mandatory: true;
  fixed: true;
  fixed_reason: string;
  prerequisites: PlanPrerequisite[];
  checkpoints: string[];
  safeguards: string[];
  policy_rule_ids: string[];
  policy_rule_references: PlanRuleReference[];
  conditional_rule_usage: PlanConditionalRuleUsage[];
  fixed_controls: PlanFixedControl[];
}

export interface PlanOptionalStep {
  stage_id: string;
  name: string;
  shown_after: string | null;
  field_count: number;
  required_field_count: number;
  blocks_send: boolean;
  pauses_automation: false;
}

export interface PlanOptionalSteps {
  state: "ACTIVE" | "NO_ACTIVE_WORKFLOW" | "UNAVAILABLE";
  version: number | null;
  manager_enabled: boolean;
  enforced_at_send: boolean;
  explanation: string;
  steps: PlanOptionalStep[];
}

export interface PlanProviderLane {
  lane: "REGISTRY" | "GOLDTIER" | "IDP" | "PERSISTENCE";
  mode: string;
  evidence_class: "MOCK" | "PARTIAL" | "LOCAL" | "UNCLASSIFIED";
}

export interface ExecutionPlan {
  registry_search_order: RegistrySearchOrder;
  order_explanation: string;
  stages: PlanStage[];
  workflow_wide_policy_rule_ids: string[];
  workflow_wide_fixed_controls: PlanFixedControl[];
  optional_steps: PlanOptionalSteps;
  branches_supported: false;
  provider_lanes: PlanProviderLane[];
}

export const WORKFLOW_WIDE_ID = "WORKFLOW_WIDE";

export const executionPlanQueryKeys = {
  plan: (userId: string) => ["auth", userId, "workflows", "execution-plan"] as const,
  policies: (userId: string) => ["auth", userId, "workflows", "execution-plan", "policies"] as const,
};

// The app's session transport: sends the session cookie (also cross-origin) and a 401 ends
// the session through the auth owner, which clears every session-scoped query.
export async function fetchExecutionPlan(signal?: AbortSignal): Promise<ExecutionPlan> {
  return parseResponse<ExecutionPlan>(
    await authenticatedFetch(`${API_BASE_URL}/api/workflows/onboarding/execution-plan`, { signal }),
  );
}

/** Cosmetic only: the backend decides access and refuses everyone else. */
export function canViewExecutionPlan(actor: Pick<AuthenticatedProfile, "capabilities">): boolean {
  return actor.capabilities.includes("POLICY_MUTATE") || actor.capabilities.includes("POLICY_APPROVE");
}

export interface SharedRule {
  reference: PlanRuleReference;
  /** The same catalogue entry as at its primary stage: one definition, one value. */
  rule: PolicyRule | undefined;
}

export interface BoundRules {
  byStage: Map<string, PolicyRule[]>;
  /** Rules this stage also reads, each defined once under its primary stage. */
  sharedByStage: Map<string, SharedRule[]>;
  /** For each rule id, the other stages that also read it (in run order). */
  usedBy: Map<string, string[]>;
  workflowWide: PolicyRule[];
  /** Rule ids the plan names but the live catalogue does not hold (should be none). */
  missing: string[];
}

/**
 * Attach live catalogue rules to the stages that use them. A catalogue rule that no stage
 * names (for example a custom display-only rule) is shown as workflow-wide, so nothing in
 * the catalogue is ever dropped from the view.
 */
export function bindRules(plan: ExecutionPlan, catalogue: PolicyCatalogue | null | undefined): BoundRules {
  const rules = new Map((catalogue?.rules ?? []).map(rule => [rule.policy_id, rule]));
  const claimed = new Set<string>();
  const missing: string[] = [];
  const pick = (ids: string[]): PolicyRule[] => ids.flatMap(id => {
    claimed.add(id);
    const rule = rules.get(id);
    if (!rule) {
      missing.push(id);
      return [];
    }
    return [rule];
  });
  const byStage = new Map(plan.stages.map(stage => [stage.stage_id, pick(stage.policy_rule_ids)]));
  const workflowWide = [
    ...pick(plan.workflow_wide_policy_rule_ids),
    ...[...rules.values()].filter(rule => !claimed.has(rule.policy_id)),
  ];
  const usedBy = new Map<string, string[]>();
  const sharedByStage = new Map(plan.stages.map(stage => [
    stage.stage_id,
    (stage.policy_rule_references ?? []).map(reference => {
      usedBy.set(reference.rule_id, [...(usedBy.get(reference.rule_id) ?? []), stage.stage_id]);
      if (!rules.has(reference.rule_id) && !missing.includes(reference.rule_id)) missing.push(reference.rule_id);
      return { reference, rule: rules.get(reference.rule_id) };
    }),
  ]));
  return { byStage, sharedByStage, usedBy, workflowWide, missing: catalogue ? missing : [] };
}

export function formatPolicyValue(value: PolicyValue): string {
  switch (value.type) {
    case "BOOLEAN":
      return value.value ? "On" : "Off";
    case "STRING_LIST":
      return value.value.join(", ");
    default:
      return String(value.value);
  }
}

export function formatRange(rule: PolicyRule): string {
  if (rule.minimum !== null && rule.maximum !== null) return `${rule.minimum}–${rule.maximum}`;
  if (rule.allowed_values.length > 0 && rule.allowed_values.length <= 4) return `One of: ${rule.allowed_values.join(", ")}`;
  if (rule.allowed_values.length > 4) return `${rule.allowed_values.length} allowed values`;
  return rule.value_type === "BOOLEAN" ? "On / off" : "—";
}

export const ENFORCEMENT_LABELS: Record<PolicyRule["enforcement"], string> = {
  RUNTIME_ENFORCED: "Runtime enforced",
  NOT_EDITABLE: "Not editable",
  DISPLAY_SHOWCASE_ONLY: "Display only",
};

export const EVIDENCE_LABELS: Record<PlanProviderLane["evidence_class"], string> = {
  MOCK: "Mock",
  PARTIAL: "Partial (Sandbox)",
  LOCAL: "Local",
  UNCLASSIFIED: "Unclassified",
};
