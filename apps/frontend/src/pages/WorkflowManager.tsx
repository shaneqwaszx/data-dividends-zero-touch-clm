import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import type { AuthenticatedProfile } from "../types";
import {
  createWorkflow,
  fetchWorkflows,
  saveWorkflowDraft,
  workflowErrorMessage,
  workflowQueryKeys,
  type WorkflowCaseSource,
  type WorkflowDetail,
  type WorkflowField,
  type WorkflowFieldKind,
  type WorkflowStage,
} from "../workflowApi";
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

function activationProblem(stages: WorkflowStage[], onboarding: boolean): string | null {
  if (!onboarding && stages.length === 0) return "Add at least one stage before this workflow can be published.";
  const empty = stages.filter(stage => stage.fields.length === 0).map(stage => stage.name);
  return empty.length ? `Add at least one field to: ${empty.join(", ")}.` : null;
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

export function WorkflowEditor({ workflow, workflows, onBack, onSaved }: {
  workflow: WorkflowDetail; workflows: WorkflowDetail[]; onBack: () => void; onSaved: (next: WorkflowDetail) => void;
}) {
  const [stages, setStages] = useState<WorkflowStage[]>(workflow.draft_stages);
  const [selectedId, setSelectedId] = useState<string | null>(workflow.draft_stages[0]?.stage_id ?? null);
  const [dirty, setDirty] = useState(false);
  const [draggedId, setDraggedId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const anchors = workflow.locked_stages.slice(0, -1);
  const selected = stages.find(stage => stage.stage_id === selectedId) ?? null;
  const problem = activationProblem(stages, workflow.is_onboarding);
  const suggestions = reusableStages(workflow, workflows, stages);

  function change(next: WorkflowStage[]) {
    setStages(next);
    setDirty(true);
    setNotice(null);
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

  // ADR-017 P2-0 freezes publication; governed publication returns with P2-1, P2-2 and P3-1.
  // Only the draft is saved here, so no request reaches the frozen activation route.
  const save = useMutation({
    mutationFn: () => saveWorkflowDraft(workflow, stages),
    onSuccess: next => {
      setDirty(false);
      setNotice("Draft saved. It is not published.");
      onSaved(next);
    },
    onError: error => setNotice(workflowErrorMessage(error)),
  });
  const selectedIndex = stages.findIndex(stage => stage.stage_id === selectedId);
  function leave() {
    if (!dirty || window.confirm("Leave without saving your changes?")) onBack();
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
          <button type="button" className="btn btn-secondary" disabled={save.isPending || !dirty} onClick={() => save.mutate()}>Save draft</button>
        </div>
      </div>
      <div className="ds-banner" role="note" data-testid="workflow-publication-paused" style={{ marginBottom: 16 }}>
        <strong>Publishing is paused.</strong> Drafts are saved, but a new version can't be published while
        approval governance is introduced. Publishing will return through HR proposals and Director approval.
      </div>
      {notice && <div className="ds-banner" role="status" style={{ marginBottom: 16 }}>{notice}</div>}
      {problem && <div className="ds-banner ds-banner-warn" style={{ marginBottom: 16 }}>{problem}</div>}

      <div className="ds-two-col">
        <section className="card" aria-label="Pipeline stages" style={{ flex: 3, minWidth: 0 }}>
          <p className="card-kicker">Stages</p>
          {workflow.is_onboarding && <p className="text-muted">Existing stages run exactly as they do today and can't be changed here.</p>}
          {stages.length === 0 && !workflow.is_onboarding && <p className="text-muted">No stages yet.</p>}
          {stages.length > 1 && !workflow.is_onboarding && <p className="text-muted">Drag a stage to reorder it.</p>}
          <ol style={{ listStyle: "none", margin: 0, padding: 0 }}>
            {editorRows(workflow, stages).map((row, index) => row.kind === "existing" ? (
              <li key={row.node_id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, padding: "6px 12px" }}>
                <span>{index + 1}. {row.label}</span>
                {anchors.some(item => item.node_id === row.node_id) && (
                  <button type="button" className="btn btn-ghost" aria-label={`Add stage after ${row.label}`} onClick={() => addStage(row.node_id)}>Add after</button>
                )}
              </li>
            ) : (
              <li key={row.stage.stage_id} draggable={!workflow.is_onboarding}
                onDragStart={() => setDraggedId(row.stage.stage_id)}
                onDragEnd={() => setDraggedId(null)}
                onDragOver={event => { if (draggedId) event.preventDefault(); }}
                onDrop={event => {
                  event.preventDefault();
                  if (draggedId && draggedId !== row.stage.stage_id) change(reorderStages(stages, draggedId, row.stage.stage_id));
                  setDraggedId(null);
                }}
                style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, padding: "6px 12px", cursor: workflow.is_onboarding ? undefined : "grab", opacity: draggedId === row.stage.stage_id ? 0.5 : undefined }}>
                {!workflow.is_onboarding && <span aria-hidden="true" className="text-muted">⠿</span>}
                <button type="button"
                  style={{ all: "unset", cursor: "pointer", flex: 1, minWidth: 0, fontWeight: row.stage.stage_id === selectedId ? 600 : undefined }}
                  aria-pressed={row.stage.stage_id === selectedId}
                  onClick={() => setSelectedId(row.stage.stage_id)}>
                  {index + 1}. {row.stage.name}
                </button>
                {workflow.is_onboarding && <button type="button" className="btn btn-ghost" aria-label={`Add stage after ${row.stage.name}`} onClick={() => addStage(row.stage.after_node_id, row.stage.stage_id)}>Add after</button>}
              </li>
            ))}
          </ol>
          {!workflow.is_onboarding && <button type="button" className="btn btn-primary" style={{ marginTop: 10 }} onClick={() => addStage(null)}>Add stage</button>}
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
          {!selected && <p className="text-muted">Select a stage to edit it, or add a new one.</p>}
          {selected && <>
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
            <div className="case-header-actions" style={{ justifyContent: "flex-start" }}>
              <button type="button" className="btn btn-secondary" onClick={() => updateSelected({ fields: [...selected.fields, emptyField()] })}>Add field</button>
              {!workflow.is_onboarding && <>
                <button type="button" className="btn btn-ghost" disabled={selectedIndex <= 0} onClick={() => move(-1)}>Move up</button>
                <button type="button" className="btn btn-ghost" disabled={selectedIndex >= stages.length - 1} onClick={() => move(1)}>Move down</button>
              </>}
              <button type="button" className="btn btn-danger" onClick={() => {
                change(stages.filter(stage => stage.stage_id !== selectedId));
                setSelectedId(null);
              }}>Remove stage</button>
            </div>
            <button type="button" className="btn btn-primary" style={{ marginTop: 12, width: "100%" }} onClick={() => setSelectedId(null)}>Confirm stage</button>
          </>}
        </section>
      </div>

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
  if (query.isError) return <section className="ds-root ds-page"><p className="ds-banner ds-banner-warn">{workflowErrorMessage(query.error)}</p></section>;
  if (query.data === null) {
    return <section className="ds-root ds-page"><h1>Workflows</h1><p className="text-muted">Workflow management is switched off on this server.</p></section>;
  }
  if (open) {
    return (
      <section className="ds-root ds-page">
        <WorkflowEditor key={open.workflow_id} workflow={open} workflows={workflows} onBack={() => setOpenId(null)}
          onSaved={next => queryClient.setQueryData<WorkflowDetail[] | null>(key, current => current?.map(item => item.workflow_id === next.workflow_id ? next : item) ?? current)} />
      </section>
    );
  }
  return (
    <section className="ds-root ds-page">
      <div className="ds-page-header">
        <div><p className="card-kicker">Director</p><h1>Workflows</h1><p className="text-muted">Each workflow is the pipeline for one use case.</p></div>
        <div className="case-header-actions"><button type="button" className="btn btn-primary" onClick={() => setCreating(true)}>New workflow</button></div>
      </div>
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
