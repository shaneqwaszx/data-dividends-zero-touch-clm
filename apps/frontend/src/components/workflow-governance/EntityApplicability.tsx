// Entity applicability (ADR-018 §5, contract CC-8): the functional successor of the C-5 placeholder.
// Legal-form conditions on a stage and on its fields, add-only. UI shaping only: the backend
// validates the canonical form, field ⊆ stage, the onboarding anchors (B2), B6, B9 and RR-8, and
// decides every run's applicability. No UBO, ownership, screening, policy or risk options.

import { useEffect, useId, useState } from "react";

import type { WorkflowField, WorkflowStage } from "../../workflowApi";
import { CONDITIONAL_LEGAL_FORMS, type ConditionalLegalForm } from "../../workflowGovernanceTypes";
import {
  appliesToText,
  B9_EXPLANATION,
  BEFORE_REGISTRY_EXPLANATION,
  canonicalAppliesTo,
  CONDITIONAL_FORM_LABEL,
  CONDITIONS_EXPLANATION,
  conditionalAnchorAllowed,
  effectiveAppliesTo,
  fieldUniverse,
  FULL_SET_EXPLANATION,
  isConditional,
  OTHER_EXPLANATION,
  RR8_EXPLANATION,
  stageHasConditions,
  withAppliesTo,
} from "./applicability";

/**
 * Mirrors the backend RegistryLegalForm enum in apps/backend/app/domain/registry_legal_form.py. A
 * parity test reads that file. OTHER is listed here for parity only and is never selectable (B5).
 */
export const ENTITY_APPLICABILITY_OPTIONS = [
  { value: "COMPANY", label: "Company" },
  { value: "BUSINESS_PARTNERSHIP", label: "Business / partnership" },
  { value: "LLP", label: "LLP" },
  { value: "LP", label: "LP" },
  { value: "GOVERNMENT", label: "Government" },
  { value: "OTHER", label: "Other" },
] as const;

type ConditionalOption = { value: ConditionalLegalForm; label: string };

/** The selectable options: ConditionalLegalForm, in display order (parity-tested against the backend). */
export const CONDITIONAL_APPLICABILITY_OPTIONS: readonly ConditionalOption[] = ENTITY_APPLICABILITY_OPTIONS
  .filter(option => (CONDITIONAL_LEGAL_FORMS as readonly string[]).includes(option.value))
  .map(option => ({ value: option.value as ConditionalLegalForm, label: option.label }));

export { CONDITIONS_EXPLANATION, OTHER_EXPLANATION, BEFORE_REGISTRY_EXPLANATION };

interface ControlProps {
  legend: string;
  value: ConditionalLegalForm[] | undefined;
  /** The forms this control may name (a field: its stage's set). */
  universe: readonly ConditionalLegalForm[];
  onChange: (next: ConditionalLegalForm[] | undefined) => void;
  /** Whole control disabled (read-only, or before the registry anchor). */
  disabledReason: string | null;
  /** "Only these legal forms" refused, with the reason (RR-8, B9, full set). */
  onlyRefusal: string | null;
  /** Checked forms that cannot be unchecked, with their reason. */
  locked: { forms: readonly string[]; reason: string } | null;
  /** The set to start from when switching to "Only these legal forms". */
  onlyInitial?: readonly ConditionalLegalForm[];
  testId: string;
}

/** "All entities" or "Only these legal forms", with the selectable forms as checkboxes. */
export function AppliesToControl({ legend, value, universe, onChange, disabledReason, onlyRefusal, locked, onlyInitial = [], testId }: ControlProps) {
  const id = useId();
  const conditional = value !== undefined && value.length > 0;
  const [only, setOnly] = useState(conditional);
  useEffect(() => { if (conditional) setOnly(true); }, [conditional]);
  const selected = new Set<string>(value ?? []);
  const readOnly = disabledReason !== null;
  const reasonId = `${id}-reason`;
  const onlyId = `${id}-only-refusal`;
  const lockId = `${id}-locked`;
  const fullId = `${id}-full`;
  const explainId = `${id}-explain`;
  const commit = (forms: Iterable<string>) => onChange(canonicalAppliesTo(forms));
  // All stays available to clear existing conditions, even when new ones can't be added here.
  const allDisabled = readOnly && (!conditional || disabledReason === "Read-only.");
  const onlyDisabled = readOnly || (onlyRefusal !== null && !only);
  const onlyWhy = readOnly ? reasonId : onlyDisabled ? onlyId : undefined;

  return (
    <fieldset style={{ border: 0, margin: "8px 0", padding: 0, minWidth: 0 }} data-testid={testId} aria-describedby={explainId}>
      <legend>{legend}</legend>
      <p id={explainId} className="sr-only">{CONDITIONS_EXPLANATION} {OTHER_EXPLANATION}</p>
      {disabledReason && <p id={reasonId} className="text-muted" style={{ margin: "2px 0" }}>{disabledReason}</p>}
      <label style={{ display: "block" }}>
        <input type="radio" name={`${id}-mode`} value="ALL" checked={!only}
          disabled={allDisabled} aria-disabled={allDisabled ? "true" : undefined} aria-describedby={allDisabled ? reasonId : undefined}
          onChange={() => { setOnly(false); onChange(undefined); }} /> All entities
      </label>
      <label style={{ display: "block" }} className={onlyDisabled ? "text-muted" : undefined}>
        <input type="radio" name={`${id}-mode`} value="ONLY" checked={only}
          disabled={onlyDisabled} aria-disabled={onlyDisabled ? "true" : undefined} aria-describedby={onlyWhy}
          onChange={() => { setOnly(true); if (onlyInitial.length) commit(onlyInitial); }} /> Only these legal forms
      </label>
      {onlyRefusal && !readOnly && !only && <p id={onlyId} className="text-muted" style={{ margin: "2px 0" }}>{onlyRefusal}</p>}
      {only && (
        <div style={{ paddingLeft: 20 }}>
          {CONDITIONAL_APPLICABILITY_OPTIONS.filter(option => universe.includes(option.value)).map(option => {
            const checked = selected.has(option.value);
            const isLocked = checked && locked !== null && locked.forms.includes(option.value);
            const wouldBeFull = !checked && selected.size + 1 >= CONDITIONAL_LEGAL_FORMS.length;
            const disabled = readOnly || isLocked || wouldBeFull;
            const why = readOnly ? reasonId : isLocked ? lockId : wouldBeFull ? fullId : undefined;
            return (
              <label key={option.value} style={{ display: "block" }} className={disabled ? "text-muted" : undefined}>
                <input type="checkbox" value={option.value} checked={checked}
                  disabled={disabled} aria-disabled={disabled ? "true" : undefined} aria-describedby={why}
                  onChange={event => {
                    const next = new Set(selected);
                    if (event.target.checked) next.add(option.value); else next.delete(option.value);
                    commit(next);
                  }} /> {CONDITIONAL_FORM_LABEL[option.value]}
              </label>
            );
          })}
          {locked && locked.forms.some(form => selected.has(form)) && (
            <p id={lockId} className="text-muted" style={{ margin: "2px 0" }}>{locked.reason}</p>
          )}
          {selected.size + 1 >= CONDITIONAL_LEGAL_FORMS.length && (
            <p id={fullId} className="text-muted" style={{ margin: "2px 0" }}>{FULL_SET_EXPLANATION}</p>
          )}
          {!conditional && <p className="text-muted" style={{ margin: "2px 0" }}>Choose at least one legal form. Until then this applies to all entities.</p>}
        </div>
      )}
    </fieldset>
  );
}

const requiredStage = (stage: WorkflowStage | undefined) => stage !== undefined && stage.fields.some(field => field.required);

/** Stage-level conditions, in the step editor. */
export function StageApplicabilityEditor({ stage, onboarding, editable, published, onChange }: {
  stage: WorkflowStage;
  onboarding: boolean;
  editable: boolean;
  /** The same stage in the active version, when it is published. */
  published: WorkflowStage | undefined;
  onChange: (next: WorkflowStage) => void;
}) {
  const anchorOk = conditionalAnchorAllowed(onboarding, stage.after_node_id);
  const disabledReason = !editable ? "Read-only." : !anchorOk ? BEFORE_REGISTRY_EXPLANATION : null;
  const fieldForms = CONDITIONAL_LEGAL_FORMS.filter(form => stage.fields.some(field => field.applies_to?.includes(form)));
  // RR-8: a published required step can broaden, never narrow.
  const publishedRequired = requiredStage(published);
  const publishedSet = published?.applies_to ?? [];
  let onlyRefusal: string | null = null;
  if (publishedRequired && !isConditional(published!)) onlyRefusal = `${RR8_EXPLANATION} This published step applies to all entities.`;
  else if (fieldForms.length > 0 && canonicalAppliesTo(fieldForms) === undefined) onlyRefusal = FULL_SET_EXPLANATION;
  const lockedForms = [...new Set([...(publishedRequired ? publishedSet : []), ...fieldForms])];
  const locked = lockedForms.length
    ? {
      forms: lockedForms,
      reason: publishedRequired && publishedSet.length
        ? `${RR8_EXPLANATION} The published step's forms, and forms used by its fields, stay selected.`
        : "Forms used by a field in this step stay selected.",
    }
    : null;
  return (
    <section aria-label={`Entity-specific conditions for ${stage.name}`} data-testid="entity-conditions" style={{ marginTop: 12 }}>
      <p className="card-kicker">Entity-specific conditions</p>
      <p className="text-muted">{CONDITIONS_EXPLANATION}</p>
      <AppliesToControl testId="entity-stage-applies-to" legend="Show this step for" value={stage.applies_to} universe={CONDITIONAL_LEGAL_FORMS}
        disabledReason={disabledReason} onlyRefusal={onlyRefusal} locked={locked} onlyInitial={fieldForms}
        onChange={next => onChange(withAppliesTo(stage, next))} />
      <p className="text-muted" style={{ margin: "2px 0" }}>{OTHER_EXPLANATION}</p>
    </section>
  );
}

/** Field-level conditions, inside the field editor: limited to the stage's forms. */
export function FieldApplicabilityEditor({ stage, field, onboarding, editable, published, onChange }: {
  stage: WorkflowStage;
  field: WorkflowField;
  onboarding: boolean;
  editable: boolean;
  /** The same stage in the active version, when it is published. */
  published: WorkflowStage | undefined;
  onChange: (next: WorkflowField) => void;
}) {
  const anchorOk = conditionalAnchorAllowed(onboarding, stage.after_node_id);
  const universe = fieldUniverse(stage);
  const publishedField = published?.fields.find(item => item.field_id === field.field_id);
  const disabledReason = !editable ? "Read-only." : !anchorOk ? BEFORE_REGISTRY_EXPLANATION : null;
  let onlyRefusal: string | null = null;
  let locked: ControlProps["locked"] = null;
  if (publishedField?.required) {
    if (effectiveAppliesTo(published!, publishedField) === undefined) {
      onlyRefusal = `${RR8_EXPLANATION} This published required field applies to all entities.`;
    } else if (publishedField.applies_to?.length) {
      locked = { forms: publishedField.applies_to, reason: `${RR8_EXPLANATION} Its published forms stay selected.` };
    }
  } else if (publishedField && effectiveAppliesTo(published!, publishedField) === undefined && field.required) {
    onlyRefusal = `B9: ${B9_EXPLANATION}`;
  }
  if (onlyRefusal === null && universe.length === 1 && !isConditional(field)) {
    onlyRefusal = "This field already follows its step's only legal form.";
  }
  return (
    <AppliesToControl testId="entity-field-applies-to" legend={`Collect "${field.label}" for`} value={field.applies_to} universe={universe}
      disabledReason={disabledReason} onlyRefusal={onlyRefusal} locked={locked}
      onChange={next => onChange(withAppliesTo(field, next))} />
  );
}

/** Workflow-level summary: the fixed explanation and every condition in the shown content. */
export function EntityApplicabilitySummary({ stages }: { stages: WorkflowStage[] }) {
  const base = "entity-applicability";
  const conditional = stages.filter(stageHasConditions);
  return (
    <section className="card" aria-labelledby={`${base}-title`} data-testid="entity-applicability" style={{ marginTop: 16 }}>
      <h2 id={`${base}-title`}>Entity applicability</h2>
      <p className="text-muted">{CONDITIONS_EXPLANATION}</p>
      <p className="text-muted">
        Selectable legal forms: {CONDITIONAL_APPLICABILITY_OPTIONS.map(option => option.label).join(", ")}. {OTHER_EXPLANATION}
      </p>
      {conditional.length === 0
        ? <p data-testid="entity-applicability-none">Every step and field applies to all entities.</p>
        : <ul aria-label="Conditional steps and fields">{conditional.map(stage => (
          <li key={stage.stage_id}>
            <strong>{stage.name}</strong>: {appliesToText(stage.applies_to)}
            {stage.fields.some(isConditional) && <ul>{stage.fields.filter(isConditional).map(field => (
              <li key={field.field_id}>{field.label}: {appliesToText(effectiveAppliesTo(stage, field))}</li>
            ))}</ul>}
          </li>
        ))}</ul>}
    </section>
  );
}
