import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { EntityApplicabilityPlaceholder, EntityConditionsPlaceholder } from "../components/workflow-governance/EntityApplicability";
import {
  GovernanceRefusalPanel,
  ProposalStatus,
  ValidationReportPanel,
} from "../components/workflow-governance/GovernancePanels";
import { WorkflowNoticesPanel } from "../components/workflow-governance/NoticesPanel";
import { EmergencyFallbackPanel, HistoryRecoveryPanel, ReleaseDraftPanel } from "../components/workflow-governance/RecoveryPanels";
import { SimulationPanel } from "../components/workflow-governance/SimulationPanel";
import { ApiError } from "../api";
import type { AuthenticatedProfile } from "../types";
import {
  createWorkflow,
  fetchWorkflow,
  fetchWorkflows,
  workflowErrorMessage,
  workflowQueryKeys,
  type WorkflowCaseSource,
  type WorkflowDetail,
  type WorkflowField,
  type WorkflowFieldKind,
  type WorkflowStage,
} from "../workflowApi";
import {
  createProposal,
  governanceErrorMessage,
  governanceRefusal,
  RELOADABLE_CODES,
  SHOW_STATUS_CODES,
  isAccessLoss,
  submitProposal,
  updateProposal,
  validateProposal,
  withdrawProposal,
  type GovernanceRefusal,
} from "../workflowGovernanceApi";
import type { CreateProposalRequest, ValidationReport } from "../workflowGovernanceTypes";
import { fixedContentKind } from "../workflowRecoveryApi";
import { ONBOARDING_STAGE_TEMPLATES } from "../workflowStageTemplates";

const FIELD_KINDS: Array<{ kind: WorkflowFieldKind; label: string }> = [
  { kind: "TEXT", label: "Text" },
  { kind: "DATE", label: "Date" },
  { kind: "NUMBER", label: "Number" },
  { kind: "YES_NO", label: "Yes or no" },
  { kind: "CHOICE", label: "Dropdown list" },
];

function newId(): string {
  return crypto.randomUUID();
}

function emptyField(): WorkflowField {
  return { field_id: newId(), label: "New field", kind: "TEXT", required: true, options: [], autofill: false, document_label: null };
}

/** Onboarding is always live: its existing stages run whether or not any stage was added. */
export function workflowStatusLabel(workflow: Pick<WorkflowDetail, "active_version" | "is_onboarding">): string {
  return workflow.active_version !== null || workflow.is_onboarding ? "Active" : "Draft";
}

export type EditorRow =
  | { kind: "existing"; node_id: string; label: string }
  | { kind: "added"; stage: WorkflowStage };

/** One ordered list: each added stage sits straight after the stage it follows. */
export function editorRows(workflow: Pick<WorkflowDetail, "is_onboarding" | "locked_stages">, stages: WorkflowStage[]): EditorRow[] {
  if (!workflow.is_onboarding) return stages.map(stage => ({ kind: "added", stage }));
  return workflow.locked_stages.flatMap((locked): EditorRow[] => [
    { kind: "existing", ...locked },
    ...stages.filter(stage => stage.after_node_id === locked.node_id).map((stage): EditorRow => ({ kind: "added", stage })),
  ]);
}

export interface ReusableStage {
  source: string;
  stage: WorkflowStage;
  /** An existing onboarding stage, offered as a form with mock fields. */
  mock: boolean;
}

/** Stages from other workflows in their own order, once per name, leaving out names already here. */
export function reusableStages(current: Pick<WorkflowDetail, "workflow_id">, workflows: WorkflowDetail[], stages: WorkflowStage[]): ReusableStage[] {
  const seen = new Set(stages.map(stage => stage.name.trim().toLowerCase()));
  return workflows.filter(item => item.workflow_id !== current.workflow_id).flatMap(item => editorRows(item, item.draft_stages).flatMap(row => {
    const mock = row.kind === "existing";
    const stage: WorkflowStage = mock
      ? { stage_id: row.node_id.toLowerCase().replaceAll("_", "-"), name: row.label, fields: ONBOARDING_STAGE_TEMPLATES[row.node_id] ?? [], after_node_id: null }
      : row.stage;
    const key = stage.name.trim().toLowerCase();
    if (seen.has(key) || stage.fields.length === 0) return [];
    seen.add(key);
    return [{ source: item.name, stage, mock }];
  }));
}

/** An independent copy: later edits here never reach the workflow it came from. */
export function copyStage(stage: WorkflowStage, afterNodeId: string | null): WorkflowStage {
  return {
    ...stage,
    stage_id: newId(),
    after_node_id: afterNodeId,
    fields: stage.fields.map(field => ({ ...field, field_id: newId() })),
  };
}

/** Move a stage to where another stage sits. */
export function reorderStages(stages: WorkflowStage[], movedId: string, targetId: string): WorkflowStage[] {
  const from = stages.findIndex(stage => stage.stage_id === movedId);
  const to = stages.findIndex(stage => stage.stage_id === targetId);
  if (from < 0 || to < 0 || from === to) return stages;
  const next = [...stages];
  const [moved] = next.splice(from, 1);
  next.splice(to, 0, moved);
  return next;
}

function FieldEditor({ field, onChange, onRemove }: {
  field: WorkflowField; onChange: (next: WorkflowField) => void; onRemove: () => void;
}) {
  return (
    <div className="card" style={{ marginBottom: 10 }}>
      <label>Field name<input className="input" value={field.label} maxLength={80}
        onChange={event => onChange({ ...field, label: event.target.value })} /></label>
      <label>Field type
        <select className="input" value={field.kind}
          onChange={event => onChange({ ...field, kind: event.target.value as WorkflowFieldKind })}>
          {FIELD_KINDS.map(item => <option key={item.kind} value={item.kind}>{item.label}</option>)}
        </select>
      </label>
      {field.kind === "CHOICE" && (
        <label>Options, separated by commas
          <input className="input" value={field.options.join(", ")}
            onChange={event => onChange({ ...field, options: event.target.value.split(",").map(item => item.trim()).filter(Boolean) })} />
        </label>
      )}
      <label><input type="checkbox" checked={field.autofill}
        onChange={event => onChange({ ...field, autofill: event.target.checked, document_label: event.target.checked ? (field.document_label ?? field.label) : null })} /> Try to fill from uploaded documents</label>
      {field.autofill && (
        <label>Label to look for in the document
          <input className="input" value={field.document_label ?? ""} maxLength={80}
            onChange={event => onChange({ ...field, document_label: event.target.value })} />
        </label>
      )}
      <div className="case-header-actions" style={{ justifyContent: "space-between" }}>
        <label><input type="checkbox" checked={field.required}
          onChange={event => onChange({ ...field, required: event.target.checked })} /> Required</label>
        <button type="button" className="btn btn-danger" onClick={onRemove}>Remove field</button>
      </div>
    </div>
  );
}

/** The active version's stages, shown read-only when no proposal is open. */
export function activeStages(workflow: Pick<WorkflowDetail, "active_version" | "versions">): WorkflowStage[] {
  return workflow.versions?.find(item => item.version === workflow.active_version)?.stages ?? [];
}

/** Local hint only; the backend validates structure, budget and the ratchet. */
function draftProblem(stages: WorkflowStage[], onboarding: boolean): string | null {
  if (!onboarding && stages.length === 0) return "Add at least one stage before this proposal can be submitted.";
  const empty = stages.filter(stage => stage.fields.length === 0).map(stage => stage.name);
  return empty.length ? `Add at least one field to: ${empty.join(", ")}.` : null;
}

const snapshot = (stages: WorkflowStage[]) => JSON.stringify(stages);

/**
 * HR authoring through governed proposals (ADR-017, P2-2). The can_* flags only shape the UI; every
 * route reauthorizes the actor. `onChanged` refetches the workflow so the next request carries the
 * current workflow and proposal revisions.
 */
export function WorkflowEditor({ workflow, workflows, userId, actor, onBack, onChanged, notice = null, onNotice = () => {}, refreshError = null }: {
  workflow: WorkflowDetail; workflows: WorkflowDetail[]; userId: string; onBack: () => void;
  /** M2 UI shaping (HR recovery, Director emergency fallback); the backend decides. */
  actor?: Pick<AuthenticatedProfile, "user_id" | "capabilities">;
  onChanged: () => Promise<unknown>; notice?: string | null; onNotice?: (text: string | null) => void;
  /** A background refetch failed; the cached workflow and any unsaved edits stay on screen. */
  refreshError?: string | null;
}) {
  const viewer = actor ?? { user_id: userId, capabilities: [] };
  const governance = workflow.governance?.migrated ? workflow.governance : null;
  const proposal = governance?.open_proposal ?? null;
  // The backend sets can_edit false for fixed-content kinds but can_submit true for their author,
  // so either flag marks the viewer's own draft (UI shaping only; the backend decides).
  const ownDraft = proposal !== null && proposal.state === "DRAFT" && (proposal.can_edit || proposal.can_submit);
  // Restore, reset and deactivate carry backend-computed content: validate and submit only, never edit.
  const fixedDraft = ownDraft && fixedContentKind(proposal!.kind);
  const editable = ownDraft && !fixedDraft;
  const [stages, setStages] = useState<WorkflowStage[]>(() => proposal?.stages ?? activeStages(workflow));
  const [selectedId, setSelectedId] = useState<string | null>(stages[0]?.stage_id ?? null);
  const [dirty, setDirty] = useState(false);
  const [draggedId, setDraggedId] = useState<string | null>(null);
  const [refusal, setRefusal] = useState<GovernanceRefusal | null>(null);
  const [validation, setValidation] = useState<{ report: ValidationReport; snapshot: string } | null>(null);
  const [validating, setValidating] = useState(false);
  const [simulating, setSimulating] = useState(false);
  const [note, setNote] = useState("");
  // The proposal revision the local stages are based on. A newer server revision while there are
  // unsaved edits means the proposal changed elsewhere: never rebase silently (QG R1 P3-1).
  const [basedOn, setBasedOn] = useState<number | null>(proposal?.revision ?? null);
  const validateController = useRef<AbortController | null>(null);
  useEffect(() => () => validateController.current?.abort(), []);
  useEffect(() => {
    // Without local edits, simply follow the server's latest content.
    if (proposal && !dirty && proposal.revision !== basedOn) {
      setStages(proposal.stages);
      setBasedOn(proposal.revision);
      setValidation(null);
    }
  }, [proposal, dirty, basedOn]);
  const anchors = workflow.locked_stages.slice(0, -1);
  const selected = stages.find(stage => stage.stage_id === selectedId) ?? null;
  const problem = editable ? draftProblem(stages, workflow.is_onboarding) : null;
  const suggestions = editable ? reusableStages(workflow, workflows, stages) : [];

  function change(next: WorkflowStage[]) {
    if (!editable) return;
    setStages(next);
    setDirty(true);
    setRefusal(null);
    onNotice(null);
  }
  function updateSelected(patch: Partial<WorkflowStage>) {
    change(stages.map(stage => stage.stage_id === selectedId ? { ...stage, ...patch } : stage));
  }
  function addStage(afterNodeId: string | null, afterStageId?: string) {
    const stage: WorkflowStage = { stage_id: newId(), name: "New stage", fields: [], after_node_id: afterNodeId };
    const position = stages.findIndex(item => item.stage_id === afterStageId);
    change(position < 0 ? [...stages, stage] : [...stages.slice(0, position + 1), stage, ...stages.slice(position + 1)]);
    setSelectedId(stage.stage_id);
  }
  function reuseStage(source: WorkflowStage) {
    const anchor = workflow.is_onboarding ? (selected?.after_node_id ?? anchors[anchors.length - 1]?.node_id ?? null) : null;
    const stage = copyStage(source, anchor);
    change([...stages, stage]);
    setSelectedId(stage.stage_id);
  }
  function move(delta: number) {
    const index = stages.findIndex(stage => stage.stage_id === selectedId);
    const next = [...stages];
    [next[index], next[index + delta]] = [next[index + delta], next[index]];
    change(next);
  }

  const onError = (error: unknown) => setRefusal(governanceRefusal(error));
  const create = useMutation({
    mutationFn: async () => {
      const body: CreateProposalRequest = { kind: "CHANGE", expected_workflow_revision: workflow.revision };
      if (note.trim()) body.note = note.trim();
      await createProposal(workflow.workflow_id, body);
      await onChanged();
    },
    onSuccess: () => onNotice("Proposal created from the active version. Edit it, validate it, then submit it for approval."),
    onError,
  });
  // Edits made while a save is in flight must stay dirty: only the content actually sent is marked saved.
  const stagesRef = useRef(stages);
  stagesRef.current = stages;
  const save = useMutation({
    mutationFn: async () => {
      const sent = snapshot(stages);
      const saved = await updateProposal(workflow.workflow_id, proposal!.proposal_id, {
        expected_workflow_revision: workflow.revision,
        expected_proposal_revision: proposal!.revision,
        stages,
        note: proposal!.note,
      });
      setBasedOn(saved.revision);
      await onChanged();
      return sent;
    },
    onSuccess: sent => {
      if (snapshot(stagesRef.current) === sent) setDirty(false);
      onNotice("Changes saved to your proposal. It is not submitted.");
    },
    onError,
  });
  const submit = useMutation({
    mutationFn: async () => {
      await submitProposal(workflow.workflow_id, proposal!.proposal_id, {
        expected_workflow_revision: workflow.revision,
        expected_proposal_revision: proposal!.revision,
        content_hash: validation!.report.content_hash,
      });
      await onChanged();
    },
    onSuccess: () => onNotice("Submitted for approval. A Director will decide it."),
    onError,
  });
  const withdraw = useMutation({
    mutationFn: async () => {
      await withdrawProposal(workflow.workflow_id, proposal!.proposal_id, {
        expected_workflow_revision: workflow.revision,
        expected_proposal_revision: proposal!.revision,
      });
      await onChanged();
    },
    onSuccess: () => onNotice("Proposal withdrawn. Its content is kept in the history."),
    onError,
  });

  async function validate() {
    if (!proposal) return;
    validateController.current?.abort();
    const controller = new AbortController();
    validateController.current = controller;
    const sent = snapshot(stages);
    setValidating(true);
    setRefusal(null);
    try {
      const report = await validateProposal(workflow.workflow_id, proposal.proposal_id, fixedDraft ? {} : { stages }, controller.signal);
      if (!controller.signal.aborted) setValidation({ report, snapshot: sent });
    } catch (error) {
      if (!controller.signal.aborted) onError(error);
    } finally {
      if (validateController.current === controller) setValidating(false);
    }
  }

  const busy = create.isPending || save.isPending || submit.isPending || withdraw.isPending || validating;
  const diverged = editable && dirty && !save.isPending && basedOn !== null && proposal!.revision !== basedOn;
  const validatedCurrent = validation !== null && validation.snapshot === snapshot(stages);
  const canSubmit = ownDraft && proposal!.can_submit && !dirty && !busy && problem === null
    && validation !== null && validation.report.valid && validatedCurrent;
  const selectedIndex = stages.findIndex(stage => stage.stage_id === selectedId);
  function leave() {
    if (!dirty || window.confirm("Leave without saving your changes?")) onBack();
  }
  /** Refetch the workflow (new revisions) without discarding local edits; the old validation no longer applies. */
  function reload() {
    validateController.current?.abort();
    setRefusal(null);
    setValidation(null);
    onNotice(null);
    void onChanged();
  }
  function discardLocalEdits() {
    if (!proposal) return;
    setStages(proposal.stages);
    setBasedOn(proposal.revision);
    setDirty(false);
    setValidation(null);
    setSelectedId(proposal.stages[0]?.stage_id ?? null);
  }
  function keepLocalEdits() {
    // The edits stay unsaved; an old validation never carries over, so submit needs a new one.
    setBasedOn(proposal!.revision);
    setValidation(null);
  }
  function confirmWithdraw() {
    if (window.confirm("Withdraw this proposal? It ends here and can't be submitted again.")) withdraw.mutate();
  }

  return (
    <>
      <div className="ds-page-header">
        <div>
          <button type="button" className="btn btn-ghost" onClick={leave}>← Back to Workflows</button>
          <h1>{workflow.name}</h1>
          <p className="text-muted">{workflow.country}{workflow.is_onboarding ? "" : ` · ${workflow.case_source === "NEW_CASE" ? "New case" : "Existing case"}`} · {workflowStatusLabel(workflow)}{dirty ? " · Unsaved changes" : ""}</p>
        </div>
        <div className="case-header-actions">
          {editable && <>
            <button type="button" className="btn btn-secondary" disabled={busy || !dirty || diverged} onClick={() => save.mutate()}>Save changes</button>
            <button type="button" className="btn btn-secondary" disabled={busy || problem !== null} onClick={() => void validate()}>Validate</button>
            <button type="button" className="btn btn-secondary" aria-expanded={simulating} aria-controls="workflow-simulation" onClick={() => setSimulating(value => !value)}>Simulate</button>
            <button type="button" className="btn btn-primary" disabled={!canSubmit} aria-describedby="submit-hint" onClick={() => submit.mutate()}>Submit for approval</button>
          </>}
          {fixedDraft && <>
            <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => void validate()}>Validate</button>
            <button type="button" className="btn btn-primary" disabled={!canSubmit} aria-describedby="submit-hint" onClick={() => submit.mutate()}>Submit for approval</button>
          </>}
          {proposal && proposal.can_withdraw && (proposal.state === "DRAFT" || proposal.state === "PENDING_APPROVAL") && (
            <button type="button" className="btn btn-danger" disabled={busy} onClick={confirmWithdraw}>Withdraw</button>
          )}
        </div>
      </div>

      {!governance && (
        <div className="ds-banner" role="note" data-testid="governance-not-enabled" style={{ marginBottom: 16 }}>
          <strong>Workflow governance is not yet enabled.</strong> Changes can't be proposed until it is. The active
          version is shown read-only.
        </div>
      )}
      {governance && !proposal && (
        <section className="card" aria-labelledby="propose-change" data-testid="propose-change" style={{ marginBottom: 16 }}>
          <h2 id="propose-change">Change this workflow</h2>
          <p className="text-muted">
            Changes are made through a proposal: you edit a draft, validate and submit it, and one Director approves or
            rejects it. Cases keep following the active version until then.
          </p>
          {governance.can_create_proposal ? <>
            <label>What does this change do? (optional)
              <input className="input" value={note} maxLength={240} onChange={event => setNote(event.target.value)} />
            </label>
            <button type="button" className="btn btn-primary" disabled={busy} onClick={() => create.mutate()}>Propose a change</button>
          </> : <p className="text-muted">You can view this workflow. Proposing changes is for HR authors.</p>}
        </section>
      )}
      {proposal && <ProposalStatus proposal={proposal} />}
      {proposal && <ReleaseDraftPanel workflow={workflow} proposal={proposal} actor={viewer} onChanged={onChanged} onNotice={onNotice} />}
      {ownDraft && (
        <p id="submit-hint" className="text-muted" style={{ marginTop: 0 }}>
          {dirty ? "Save your changes, then validate before submitting."
            : !validatedCurrent ? "Validate the current content before submitting."
              : validation?.report.valid ? "Validated. You can submit this content for approval." : "Fix the validation issues before submitting."}
        </p>
      )}
      {notice && <div className="ds-banner" role="status" style={{ marginBottom: 16 }}>{notice}</div>}
      {refreshError && (
        <div className="ds-banner ds-banner-warn" role="alert" data-testid="workflow-refresh-error" style={{ marginBottom: 16 }}>
          The latest version of this workflow could not be loaded: {refreshError} What you see, including unsaved changes, is kept.{" "}
          <button type="button" className="btn btn-secondary" onClick={reload}>Reload</button>
        </div>
      )}
      {diverged && (
        <div className="ds-banner ds-banner-warn" role="alert" data-testid="proposal-changed-elsewhere" style={{ marginBottom: 16 }}>
          <p style={{ margin: 0 }}>
            <strong>This proposal was changed elsewhere.</strong> The saved version is now revision {proposal!.revision}; your
            unsaved edits are based on revision {basedOn}. Choose what to do before saving.
          </p>
          <p className="card-kicker" style={{ marginTop: 8 }}>Saved version</p>
          <ol data-testid="server-version">{proposal!.stages.map(stage => (
            <li key={stage.stage_id}>{stage.name} · {stage.fields.length} {stage.fields.length === 1 ? "field" : "fields"}</li>
          ))}</ol>
          <div className="case-header-actions" style={{ justifyContent: "flex-start" }}>
            <button type="button" className="btn btn-secondary" onClick={discardLocalEdits}>Discard my edits and load the saved version</button>
            <button type="button" className="btn btn-ghost" onClick={keepLocalEdits}>Keep my edits</button>
          </div>
          <p className="text-muted" style={{ margin: "6px 0 0" }}>Keeping your edits replaces the saved version when you save, and you must validate again before submitting.</p>
        </div>
      )}
      {refusal && <GovernanceRefusalPanel refusal={refusal}
        onReload={refusal.code && (RELOADABLE_CODES.has(refusal.code) || SHOW_STATUS_CODES.has(refusal.code)) ? reload : undefined}
        reloadLabel={refusal.code && SHOW_STATUS_CODES.has(refusal.code) ? "Show current status" : "Reload"} />}
      {problem && <div className="ds-banner ds-banner-warn" style={{ marginBottom: 16 }}>{problem}</div>}
      {ownDraft && validation && <ValidationReportPanel report={validation.report} current={validatedCurrent} />}
      {editable && simulating && proposal && (
        <SimulationPanel id="workflow-simulation" userId={userId} workflowId={workflow.workflow_id} proposalId={proposal.proposal_id} stages={stages} />
      )}

      <div className="ds-two-col">
        <section className="card" aria-label="Pipeline stages" style={{ flex: 3, minWidth: 0 }}>
          <p className="card-kicker">{editable ? "Stages in your proposal" : proposal ? "Stages in the open proposal (read-only)" : "Active version stages (read-only)"}</p>
          {workflow.is_onboarding && <p className="text-muted">Existing stages run exactly as they do today and can't be changed here.</p>}
          {stages.length === 0 && !workflow.is_onboarding && <p className="text-muted">No stages yet.</p>}
          {editable && stages.length > 1 && !workflow.is_onboarding && <p className="text-muted">Drag a stage to reorder it.</p>}
          <ol style={{ listStyle: "none", margin: 0, padding: 0 }}>
            {editorRows(workflow, stages).map((row, index) => row.kind === "existing" ? (
              <li key={row.node_id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, padding: "6px 12px" }}>
                <span>{index + 1}. {row.label}</span>
                {editable && anchors.some(item => item.node_id === row.node_id) && (
                  <button type="button" className="btn btn-ghost" aria-label={`Add stage after ${row.label}`} onClick={() => addStage(row.node_id)}>Add after</button>
                )}
              </li>
            ) : (
              <li key={row.stage.stage_id} draggable={editable && !workflow.is_onboarding}
                onDragStart={() => setDraggedId(row.stage.stage_id)}
                onDragEnd={() => setDraggedId(null)}
                onDragOver={event => { if (draggedId) event.preventDefault(); }}
                onDrop={event => {
                  event.preventDefault();
                  if (draggedId && draggedId !== row.stage.stage_id) change(reorderStages(stages, draggedId, row.stage.stage_id));
                  setDraggedId(null);
                }}
                style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, padding: "6px 12px", cursor: editable && !workflow.is_onboarding ? "grab" : undefined, opacity: draggedId === row.stage.stage_id ? 0.5 : undefined }}>
                {editable && !workflow.is_onboarding && <span aria-hidden="true" className="text-muted">⠿</span>}
                <button type="button"
                  style={{ all: "unset", cursor: "pointer", flex: 1, minWidth: 0, fontWeight: row.stage.stage_id === selectedId ? 600 : undefined }}
                  aria-pressed={row.stage.stage_id === selectedId}
                  onClick={() => setSelectedId(row.stage.stage_id)}>
                  {index + 1}. {row.stage.name}
                </button>
                {editable && workflow.is_onboarding && <button type="button" className="btn btn-ghost" aria-label={`Add stage after ${row.stage.name}`} onClick={() => addStage(row.stage.after_node_id, row.stage.stage_id)}>Add after</button>}
              </li>
            ))}
          </ol>
          {editable && !workflow.is_onboarding && <button type="button" className="btn btn-primary" style={{ marginTop: 10 }} onClick={() => addStage(null)}>Add stage</button>}
          {suggestions.length > 0 && <>
            <p className="card-kicker" style={{ marginTop: 16 }}>Reuse from other workflows</p>
            {suggestions.some(item => item.mock) && <p className="text-muted">Onboarding stages come with mock fields for someone to fill in. They don't run the automated check.</p>}
            <select className="input" aria-label="Reuse a stage" value=""
              onChange={event => {
                const item = suggestions[Number(event.target.value)];
                if (item) reuseStage(item.stage);
              }}>
              <option value="">Choose a stage to reuse</option>
              {suggestions.map((item, index) => (
                <option key={`${item.source}-${item.stage.stage_id}`} value={index}>
                  {item.stage.name} ({item.stage.fields.length} {item.mock ? "mock " : ""}{item.stage.fields.length === 1 ? "field" : "fields"})
                </option>
              ))}
            </select>
          </>}
        </section>

        <section className="card" aria-label="Stage settings" style={{ flex: 2, minWidth: 0 }}>
          {!selected && <p className="text-muted">{editable ? "Select a stage to edit it, or add a new one." : "Select a stage to see its fields."}</p>}
          {selected && <fieldset disabled={!editable} style={{ border: 0, margin: 0, padding: 0, minWidth: 0 }}>
            <label>Stage name<input className="input" value={selected.name} maxLength={80}
              onChange={event => updateSelected({ name: event.target.value })} /></label>
            {workflow.is_onboarding && (
              <label>Show after
                <select className="input" value={selected.after_node_id ?? ""}
                  onChange={event => updateSelected({ after_node_id: event.target.value })}>
                  {anchors.map(stage => <option key={stage.node_id} value={stage.node_id}>{stage.label}</option>)}
                </select>
              </label>
            )}
            <p className="card-kicker">Fields to collect</p>
            {selected.fields.map(field => (
              <FieldEditor key={field.field_id} field={field}
                onChange={next => updateSelected({ fields: selected.fields.map(item => item.field_id === field.field_id ? next : item) })}
                onRemove={() => updateSelected({ fields: selected.fields.filter(item => item.field_id !== field.field_id) })} />
            ))}
            {editable && <div className="case-header-actions" style={{ justifyContent: "flex-start" }}>
              <button type="button" className="btn btn-secondary" onClick={() => updateSelected({ fields: [...selected.fields, emptyField()] })}>Add field</button>
              {!workflow.is_onboarding && <>
                <button type="button" className="btn btn-ghost" disabled={selectedIndex <= 0} onClick={() => move(-1)}>Move up</button>
                <button type="button" className="btn btn-ghost" disabled={selectedIndex >= stages.length - 1} onClick={() => move(1)}>Move down</button>
              </>}
              <button type="button" className="btn btn-danger" onClick={() => {
                change(stages.filter(stage => stage.stage_id !== selectedId));
                setSelectedId(null);
              }}>Remove stage</button>
            </div>}
            <EntityConditionsPlaceholder stageName={selected.name} />
          </fieldset>}
          {selected && <button type="button" className="btn btn-primary" style={{ marginTop: 12, width: "100%" }} onClick={() => setSelectedId(null)}>{editable ? "Confirm stage" : "Close"}</button>}
        </section>
      </div>

      <EntityApplicabilityPlaceholder />
      {governance && <HistoryRecoveryPanel workflow={workflow} actor={viewer} onChanged={onChanged} onNotice={onNotice} />}
      {governance && <EmergencyFallbackPanel workflow={workflow} actor={viewer} onChanged={onChanged} onNotice={onNotice} />}

      <section className="card" aria-labelledby="workflow-history" style={{ marginTop: 16 }}>
        <h2 id="workflow-history">History</h2>
        <p className="text-muted">Open cases follow the latest active version. Cases already sent stay as they were.</p>
        {workflow.audit.length === 0 && <p className="text-muted">No changes yet.</p>}
        <ul>{[...workflow.audit].reverse().map(item => (
          <li key={`${item.occurred_at}-${item.action}`}>{new Date(item.occurred_at).toLocaleString()} · {item.actor_id} · {item.summary}</li>
        ))}</ul>
      </section>
    </>
  );
}

/** Loads the workflow with its governance view; remounts the editor when the open proposal changes. */
function GovernedWorkflowEditor({ actor, workflowId, workflows, onBack }: {
  actor: AuthenticatedProfile; workflowId: string; workflows: WorkflowDetail[]; onBack: () => void;
}) {
  const queryClient = useQueryClient();
  const detail = useQuery({
    queryKey: workflowQueryKeys.detail(actor.user_id, workflowId),
    queryFn: ({ signal }) => fetchWorkflow(workflowId, signal),
    retry: false,
  });
  const [notice, setNotice] = useState<string | null>(null);
  // The list key prefixes the detail key, so this refetches both before the next request.
  const refresh = useCallback(
    () => queryClient.invalidateQueries({ queryKey: workflowQueryKeys.list(actor.user_id) }),
    [queryClient, actor.user_id],
  );
  const detailKey = workflowQueryKeys.detail(actor.user_id, workflowId);
  const accessLost = detail.isError && isAccessLoss(detail.error);
  // Lost access (401/403/404): the cached workflow is dropped when leaving while access is lost, never
  // on recovery (true -> false), so a recovered editor keeps its cache.
  const accessLostRef = useRef(accessLost);
  accessLostRef.current = accessLost;
  const leaveCleanup = useRef({ queryClient, detailKey });
  useEffect(() => () => {
    if (accessLostRef.current) {
      leaveCleanup.current.queryClient.removeQueries({ queryKey: leaveCleanup.current.detailKey, exact: true });
    }
  }, []);
  if (detail.isPending) return <p className="text-muted">Loading workflow…</p>;
  // A failed first load, or lost access, replaces the editor. A network or 5xx refetch failure keeps the cached data.
  if (detail.isError && (detail.data === undefined || accessLost)) {
    return <>
      <button type="button" className="btn btn-ghost" onClick={onBack}>← Back to Workflows</button>
      <p className="ds-banner ds-banner-warn" data-testid="workflow-unavailable">
        {accessLost && detail.error instanceof ApiError && detail.error.status !== 401
          ? "This workflow is not available." : governanceErrorMessage(detail.error)}
      </p>
    </>;
  }
  const workflow = detail.data;
  const proposalId = workflow.governance?.open_proposal?.proposal_id ?? "none";
  return (
    <WorkflowEditor key={`${workflow.workflow_id}:${proposalId}`} workflow={workflow} workflows={workflows}
      userId={actor.user_id} actor={actor} onBack={onBack} onChanged={refresh} notice={notice} onNotice={setNotice}
      refreshError={detail.isError ? governanceErrorMessage(detail.error) : null} />
  );
}

export default function WorkflowManager({ actor }: { actor: AuthenticatedProfile }) {
  const queryClient = useQueryClient();
  const key = workflowQueryKeys.list(actor.user_id);
  const query = useQuery({ queryKey: key, queryFn: ({ signal }) => fetchWorkflows(signal), retry: false });
  const [openId, setOpenId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [country, setCountry] = useState("Singapore");
  const [caseSource, setCaseSource] = useState<WorkflowCaseSource>("EXISTING_CASE");
  const workflows = query.data ?? [];
  const open = useMemo(() => workflows.find(item => item.workflow_id === openId) ?? null, [workflows, openId]);
  const create = useMutation({
    // The workflow's name is its use case.
    mutationFn: () => createWorkflow({ name: name.trim(), use_case: name.trim(), country: country.trim(), case_source: caseSource }),
    onSuccess: async created => {
      await queryClient.invalidateQueries({ queryKey: key });
      setCreating(false);
      setName("");
      setOpenId(created.workflow_id);
    },
  });

  if (query.isPending) return <section className="ds-root ds-page"><p className="text-muted">Loading workflows…</p></section>;
  if (query.isError && (query.data === undefined || isAccessLoss(query.error))) return <section className="ds-root ds-page"><p className="ds-banner ds-banner-warn">{workflowErrorMessage(query.error)}</p></section>;
  if (query.data === null) {
    return <section className="ds-root ds-page"><h1>Workflows</h1><p className="text-muted">Workflow management is switched off on this server.</p></section>;
  }
  if (open) {
    return (
      <section className="ds-root ds-page">
        <WorkflowNoticesPanel actor={actor} workflowId={open.workflow_id} />
        <GovernedWorkflowEditor key={open.workflow_id} actor={actor} workflowId={open.workflow_id} workflows={workflows} onBack={() => setOpenId(null)} />
      </section>
    );
  }
  return (
    <section className="ds-root ds-page">
      <div className="ds-page-header">
        <div><p className="card-kicker">Policy &amp; Workflow</p><h1>Workflows</h1><p className="text-muted">Each workflow is the pipeline for one use case.</p></div>
        {/* D-7: HR (POLICY_MUTATE) creates workflows. UI shaping only; the backend decides. */}
        {actor.capabilities.includes("POLICY_MUTATE") && (
          <div className="case-header-actions"><button type="button" className="btn btn-primary" onClick={() => setCreating(true)}>New workflow</button></div>
        )}
      </div>
      <WorkflowNoticesPanel actor={actor} />
      {query.isError && (
        <div className="ds-banner ds-banner-warn" role="alert" data-testid="workflow-list-refresh-error" style={{ marginBottom: 16 }}>
          The latest workflow list could not be loaded: {workflowErrorMessage(query.error)} The list below may be out of date.{" "}
          <button type="button" className="btn btn-secondary" disabled={query.isFetching} onClick={() => void query.refetch()}>Reload</button>
        </div>
      )}
      {creating && (
        <section className="card" aria-labelledby="new-workflow" style={{ marginBottom: 16 }}>
          <h2 id="new-workflow">New workflow</h2>
          <label>Workflow name<input className="input" value={name} maxLength={64} onChange={event => setName(event.target.value)} /></label>
          <label>Country<input className="input" value={country} maxLength={64} onChange={event => setCountry(event.target.value)} /></label>
          <fieldset style={{ border: 0, margin: "12px 0", padding: 0 }}>
            <legend>Does this workflow use an existing case or a new case?</legend>
            <label><input type="radio" name="case-source" checked={caseSource === "EXISTING_CASE"} onChange={() => setCaseSource("EXISTING_CASE")} /> Existing case</label>{" "}
            <label><input type="radio" name="case-source" checked={caseSource === "NEW_CASE"} onChange={() => setCaseSource("NEW_CASE")} /> New case</label>
          </fieldset>
          {create.isError && <p className="ds-banner ds-banner-warn">{workflowErrorMessage(create.error)}</p>}
          <div className="case-header-actions" style={{ justifyContent: "flex-start" }}>
            <button type="button" className="btn btn-primary" disabled={!name.trim() || !country.trim() || create.isPending} onClick={() => create.mutate()}>Create workflow</button>
            <button type="button" className="btn btn-ghost" onClick={() => setCreating(false)}>Cancel</button>
          </div>
        </section>
      )}
      <section className="card" aria-label="All workflows">
        <table>
          <thead><tr><th>Workflow</th><th>Country</th><th>Status</th><th><span className="sr-only">Actions</span></th></tr></thead>
          <tbody>{workflows.map(item => (
            <tr key={item.workflow_id}>
              <td>{item.name}</td><td>{item.country}</td>
              <td>{workflowStatusLabel(item)}</td>
              <td><button type="button" className="btn btn-secondary" onClick={() => setOpenId(item.workflow_id)}>Edit</button></td>
            </tr>
          ))}</tbody>
        </table>
      </section>
    </section>
  );
}
