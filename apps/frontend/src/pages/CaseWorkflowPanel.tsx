import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { RunApplicabilityBasis } from "../components/workflow-governance/RunApplicabilityBasis";
import StageDisclosure from "./StageDisclosure";
import { CONDITIONAL_ONBOARDING_ANCHORS } from "../workflowGovernanceTypes";
import {
  confirmStage,
  saveStageAnswers,
  workflowErrorMessage,
  workflowQueryKeys,
  type WorkflowRun,
  type WorkflowRunField,
  type WorkflowRunStage,
} from "../workflowApi";

const INPUT_TYPE: Record<WorkflowRunField["kind"], string> = { TEXT: "text", DATE: "date", NUMBER: "number", YES_NO: "text", CHOICE: "text" };

function FieldInput({ field, value, disabled, onChange }: {
  field: WorkflowRunField; value: string; disabled: boolean; onChange: (next: string) => void;
}) {
  if (field.kind === "YES_NO" || field.kind === "CHOICE") {
    const options = field.kind === "YES_NO" ? ["Yes", "No"] : field.options;
    return (
      <label>{field.label}
        <select className="input" value={value} disabled={disabled} required={field.required} onChange={event => onChange(event.target.value)}>
          <option value="">Select</option>
          {options.map(option => <option key={option} value={option}>{option}</option>)}
        </select>
      </label>
    );
  }
  return (
    <label>{field.label}
      <input className="input" type={INPUT_TYPE[field.kind]} value={value} disabled={disabled} required={field.required} maxLength={512}
        onChange={event => onChange(event.target.value)} />
    </label>
  );
}

function StageForm({ caseId, run, stage, canFill, onChanged }: {
  caseId: string | null; run: WorkflowRun; stage: WorkflowRunStage; canFill: boolean; onChanged: () => void;
}) {
  const saved = Object.fromEntries(stage.fields.map(field => [field.field_id, field.value ?? ""]));
  const [values, setValues] = useState<Record<string, string>>(saved);
  const dirty = stage.fields.some(field => (values[field.field_id] ?? "") !== (field.value ?? ""));
  const missing = stage.fields.some(field => field.required && !(values[field.field_id] ?? "").trim());
  const save = useMutation({
    mutationFn: async (confirm: boolean) => {
      const latest = dirty ? await saveStageAnswers(caseId, run, stage.stage_id, values) : run;
      return confirm ? confirmStage(caseId, latest, stage.stage_id) : latest;
    },
    onSuccess: onChanged,
  });
  return (
    <div id={`workflow-stage-${stage.stage_id}`} tabIndex={-1}>
      {stage.fields.map(field => (
        <div key={field.field_id}>
          <FieldInput field={field} value={values[field.field_id] ?? ""} disabled={!canFill}
            onChange={next => setValues(current => ({ ...current, [field.field_id]: next }))} />
          {field.source === "CASE" && values[field.field_id] === field.value && (
            <p className="control-help" style={{ margin: 0 }}>Loaded from the onboarded case. Please check.</p>
          )}
          {field.source === "DOCUMENT" && values[field.field_id] === field.value && (
            <p className="control-help" style={{ margin: 0 }}>Found in document{field.page_number ? `, page ${field.page_number}` : ""}. Please check.</p>
          )}
        </div>
      ))}
      {save.isError && <p className="ds-banner ds-banner-warn">{workflowErrorMessage(save.error)}</p>}
      {canFill && (
        <div className="case-header-actions" style={{ justifyContent: "flex-start" }}>
          <button type="button" className="btn btn-secondary" disabled={!dirty || save.isPending} onClick={() => save.mutate(false)}>Save</button>
          <button type="button" className="btn btn-primary" disabled={missing || save.isPending || (stage.status === "COMPLETE" && !dirty)} onClick={() => save.mutate(true)}>Confirm</button>
        </div>
      )}
    </div>
  );
}

const SECTION_STATUS: Record<WorkflowRunStage["status"], { tone: string; label: string }> = {
  COMPLETE: { tone: "done", label: "Complete" },
  OPEN: { tone: "attention", label: "Review required" },
  LOCKED: { tone: "pending", label: "Not started yet" },
};

function sectionSummary(run: WorkflowRun, stage: WorkflowRunStage): string {
  const state = stage.status === "COMPLETE" ? "Status: Complete."
    : stage.status === "LOCKED" ? "Opens after the previous stage."
    : run.is_onboarding && stage.blocks_send ? "Needs input. Must be confirmed before the case can be sent."
    : "Needs input.";
  return run.is_onboarding ? state : `${run.workflow_name}. ${state}`;
}

interface StageSectionProps {
  caseId: string | null;
  userId: string;
  canFill: boolean;
  scopeKey: string;
}

function StageSection({ caseId, userId, canFill, scopeKey, run, stage }: StageSectionProps & {
  run: WorkflowRun; stage: WorkflowRunStage;
}) {
  const queryClient = useQueryClient();
  const refresh = () => { void queryClient.invalidateQueries({ queryKey: workflowQueryKeys.list(userId) }); };
  return (
    <StageDisclosure
      title={stage.name}
      status={SECTION_STATUS[stage.status]}
      summary={sectionSummary(run, stage)}
      scopeKey={`${scopeKey}:${run.run_id}:${stage.stage_id}`}
      main={stage.status === "LOCKED"
        ? <p className="text-muted">Opens after the previous stage.</p>
        : <StageForm key={run.revision} caseId={caseId} run={run} stage={stage} canFill={canFill} onChanged={refresh} />}
    />
  );
}

/** Only the RM or onboarder fills in stages, and only until the case has been sent. */
export function canFillOnboardingStages(role: string, summary: { status: string; current_stage: string } | null): boolean {
  return (role === "CLIENT_ONBOARDER" || role === "RELATIONSHIP_MANAGER")
    && summary?.status !== "COMPLETED" && summary?.current_stage !== "MOCK_GOLDTIER";
}

/**
 * ADR-018: the run's applicability basis, only when the run carries one. The escalation is offered to
 * case fillers on a case (UI shaping only; the backend reauthorizes it).
 */
function RunBasis({ run, caseId, userId, canFill }: Pick<StageSectionProps, "caseId" | "userId" | "canFill"> & { run: WorkflowRun }) {
  const queryClient = useQueryClient();
  if (!run.applicability) return null;
  const escalation = caseId && canFill ? {
    caseId,
    run: { run_id: run.run_id, revision: run.revision },
    onChanged: () => { void queryClient.invalidateQueries({ queryKey: workflowQueryKeys.list(userId) }); },
  } : null;
  return <RunApplicabilityBasis view={run.applicability} escalation={escalation} />;
}

/** The added onboarding stages that follow any of the given existing stages. */
export function CaseWorkflowStages({ run, anchors, ...props }: StageSectionProps & {
  run: WorkflowRun | null | undefined; anchors: string[];
}) {
  // The page renders one group per anchor; the basis is shown once, before the run's first added stage.
  // A run whose resolved copy has no added stage (every stage was conditional and none applies) still
  // shows its basis, at the registry step where the basis is frozen, so a held case keeps its
  // escalation path (M3 QG P2-2).
  const first = run?.stages.find(stage => stage.after_node_id !== null);
  const basisAnchor = first ? first.after_node_id! : CONDITIONAL_ONBOARDING_ANCHORS[0];
  const showBasis = run && anchors.includes(basisAnchor);
  return <>
    {showBasis && <RunBasis run={run} caseId={props.caseId} userId={props.userId} canFill={props.canFill} />}
    {run?.stages.filter(stage => stage.after_node_id !== null && anchors.includes(stage.after_node_id))
      .map(stage => <StageSection key={stage.stage_id} {...props} run={run} stage={stage} />)}
  </>;
}

/** Director-started workflows, each in its own stage order. */
export function CaseWorkflowRuns({ runs, ...props }: StageSectionProps & { runs: WorkflowRun[] | undefined }) {
  return <>
    {runs?.flatMap(run => [
      <RunBasis key={`${run.run_id}-basis`} run={run} caseId={props.caseId} userId={props.userId} canFill={props.canFill} />,
      ...run.stages.map(stage => (
        <StageSection key={`${run.run_id}-${stage.stage_id}`} {...props} run={run} stage={stage} />
      )),
    ])}
  </>;
}
