// ADR-018 conditional applicability helpers (contract CC-8). UI shaping only: the backend validates
// the canonical form, field ⊆ stage, the onboarding anchors, B6/B9 and RR-8, and decides every run's
// applicability. Nothing here evaluates an entity.

import type { WorkflowField, WorkflowStage } from "../../workflowApi";
import {
  CONDITIONAL_LEGAL_FORMS,
  CONDITIONAL_ONBOARDING_ANCHORS,
  type ConditionalLegalForm,
} from "../../workflowGovernanceTypes";

export const CONDITIONAL_FORM_LABEL: Record<ConditionalLegalForm, string> = {
  BUSINESS_PARTNERSHIP: "Business / partnership",
  COMPANY: "Company",
  GOVERNMENT: "Government",
  LLP: "LLP",
  LP: "LP",
};

export const CONDITIONS_EXPLANATION =
  "Conditions only add steps for matching entities. They never remove or relax a step that applies to everyone. If an entity's legal form is unknown, every conditional step applies.";
export const OTHER_EXPLANATION = "Entities with another or unverified legal form always receive every condition.";
export const BEFORE_REGISTRY_EXPLANATION =
  "Conditions need the registry result, so they are available only from Registry verification onwards.";
export const FULL_SET_EXPLANATION = "Choosing every legal form is the same as All entities.";
export const RR8_EXPLANATION = "RR-8: where a required step or field applies cannot be narrowed.";
export const B9_EXPLANATION =
  "An optional field for everyone can't become a conditional required field. Keep it and add a new conditional required field beside it.";

/**
 * The one canonical representation (ADR-018 §2.1): undefined for All entities, otherwise a sorted,
 * duplicate-free, non-empty set that never names every selectable form.
 */
export function canonicalAppliesTo(forms: Iterable<string> | null | undefined): ConditionalLegalForm[] | undefined {
  if (!forms) return undefined;
  const chosen = new Set(forms);
  const sorted = CONDITIONAL_LEGAL_FORMS.filter(form => chosen.has(form));
  if (sorted.length === 0 || sorted.length === CONDITIONAL_LEGAL_FORMS.length) return undefined;
  return [...sorted];
}

/** Returns a copy without the key when All, so requests carry no applies_to for unconditional content. */
export function withAppliesTo<T extends WorkflowStage | WorkflowField>(item: T, forms: Iterable<string> | null | undefined): T {
  const next = { ...item };
  const canonical = canonicalAppliesTo(forms);
  if (canonical) next.applies_to = canonical;
  else delete next.applies_to;
  return next;
}

export function isConditional(item: { applies_to?: readonly string[] | null }): boolean {
  return Array.isArray(item.applies_to) && item.applies_to.length > 0;
}

/** Field ⊆ stage, with All as the identity. */
export function fieldWithinStage(stage: Pick<WorkflowStage, "applies_to">, field: Pick<WorkflowField, "applies_to">): boolean {
  if (!isConditional(field)) return true;
  if (!isConditional(stage)) return true;
  return field.applies_to!.every(form => stage.applies_to!.includes(form));
}

/** Effective applicability of a field: stage ∩ field, with All (undefined) as the identity. */
export function effectiveAppliesTo(stage: Pick<WorkflowStage, "applies_to">, field?: Pick<WorkflowField, "applies_to">): ConditionalLegalForm[] | undefined {
  if (!field || !isConditional(field)) return isConditional(stage) ? [...stage.applies_to!] : undefined;
  if (!isConditional(stage)) return [...field.applies_to!];
  return field.applies_to!.filter(form => stage.applies_to!.includes(form));
}

/** B2: on onboarding, conditional content only at ACRA_REGISTRY or a later anchor. */
export function conditionalAnchorAllowed(onboarding: boolean, afterNodeId: string | null): boolean {
  if (!onboarding) return true;
  return afterNodeId !== null && (CONDITIONAL_ONBOARDING_ANCHORS as readonly string[]).includes(afterNodeId);
}

export function stageHasConditions(stage: WorkflowStage): boolean {
  return isConditional(stage) || stage.fields.some(isConditional);
}

export function appliesToText(forms: readonly string[] | null | undefined): string {
  if (!forms || forms.length === 0) return "All entities";
  const labels = forms.map(form => CONDITIONAL_FORM_LABEL[form as ConditionalLegalForm] ?? form);
  return `Only ${labels.join(", ")} (and entities whose legal form is unverified)`;
}

/** The forms a field may name: its stage's set, or every selectable form when the stage is All. */
export function fieldUniverse(stage: Pick<WorkflowStage, "applies_to">): ConditionalLegalForm[] {
  return isConditional(stage) ? CONDITIONAL_LEGAL_FORMS.filter(form => stage.applies_to!.includes(form)) : [...CONDITIONAL_LEGAL_FORMS];
}
