import { useMutation, useQuery } from "@tanstack/react-query";
import { Fragment, useRef, useState, type CSSProperties, type FormEvent } from "react";
import { NavLink } from "react-router";

import { fetchZeroTouchCases } from "../api";
import type { AuthenticatedProfile } from "../types";
import {
  createWorkflowCase,
  deleteWorkflowCase,
  fetchStartableWorkflows,
  fetchWorkflowRuns,
  startWorkflowRun,
  uploadWorkflowCaseDocument,
  workflowErrorMessage,
  workflowQueryKeys,
  type StartableWorkflow,
  type WorkflowRun,
  type WorkflowRunStage,
} from "../workflowApi";
import { UPLOAD_ACCEPT, UPLOAD_HELP_TEXT } from "../uploadLimits";
import { CaseWorkflowRuns } from "./CaseWorkflowPanel";
import { revealStage } from "./StageDisclosure";
import { mergeSelectedFiles, type JurisdictionSelection } from "./HomeOnboarding";

function startableQuery(userId: string) {
  return {
    queryKey: workflowQueryKeys.startable(userId),
    queryFn: ({ signal }: { signal: AbortSignal }) => fetchStartableWorkflows(signal),
    retry: false,
  };
}

/** One tab per active workflow, for the people who start and fill them in. */
export function WorkflowTabLinks({ actor }: { actor: AuthenticatedProfile }) {
  const fills = actor.role === "CLIENT_ONBOARDER" || actor.role === "RELATIONSHIP_MANAGER";
  const query = useQuery({ ...startableQuery(actor.user_id), enabled: fills });
  return <>
    {(fills ? query.data ?? [] : []).map(item => (
      <Fragment key={item.workflow_id}>
        <NavLink end to={`/workflow-tabs/${encodeURIComponent(item.workflow_id)}`}
          className={({ isActive }) => isActive ? "nav-tab nav-tab--active" : "nav-tab"}>
          {item.name}
        </NavLink>
        <NavLink to={`/workflow-tabs/${encodeURIComponent(item.workflow_id)}/cases`}
          className={({ isActive }) => isActive ? "nav-tab nav-tab--active" : "nav-tab"}>
          {item.name} cases
        </NavLink>
      </Fragment>
    ))}
  </>;
}

/** Onboarded companies that do not already have a case in this workflow. */
export function availableCompanies<Company extends { case_id: string }>(companies: Company[], runs: Array<{ case_id: string | null }>): Company[] {
  const started = new Set(runs.map(item => item.case_id));
  return companies.filter(item => !started.has(item.case_id));
}

function ExistingCaseStart({ actor, workflow, onOpenRun }: {
  actor: AuthenticatedProfile; workflow: StartableWorkflow; onOpenRun: (runId: string) => void;
}) {
  const cases = useQuery({
    queryKey: workflowQueryKeys.tabCases(actor.user_id),
    queryFn: ({ signal }) => fetchZeroTouchCases("COMPLETED", "all", "highest_first", undefined, signal),
  });
  const runs = useWorkflowRuns(actor, workflow.workflow_id);
  const companies = availableCompanies(cases.data ?? [], runs.data ?? []);
  const [caseId, setCaseId] = useState("");
  const start = useMutation({
    mutationFn: () => startWorkflowRun(workflow.workflow_id, caseId),
    onSuccess: run => onOpenRun(run.run_id),
  });
  return <>
    <div className="ds-page-header"><div><h1>{workflow.name}</h1><p className="text-muted">Choose an onboarded company to run this workflow for.</p></div></div>
    <section className="card" aria-label={`Start ${workflow.name}`}>
      <div className="field">
        <label htmlFor="workflow-case">Onboarded company</label>
        <select id="workflow-case" className="input" value={caseId} onChange={event => setCaseId(event.target.value)}>
          <option value="">Choose a company</option>
          {companies.map(item => (
            <option key={item.case_id} value={item.case_id}>{item.legal_name ?? item.requested_uen} ({item.requested_uen})</option>
          ))}
        </select>
        {cases.data?.length === 0 && <p className="control-help">No companies have finished onboarding yet.</p>}
        {Boolean(cases.data?.length) && companies.length === 0 && <p className="control-help">Every onboarded company already has a {workflow.name} case.</p>}
      </div>
      {start.isError && <p className="ds-banner ds-banner-warn">{workflowErrorMessage(start.error)}</p>}
      <button type="button" className="btn btn-primary" disabled={!caseId || start.isPending} onClick={() => start.mutate()}>Start</button>
    </section>
  </>;
}

function NewCaseStart({ actor, workflow, onOpenRun }: {
  actor: AuthenticatedProfile; workflow: StartableWorkflow; onOpenRun: (runId: string) => void;
}) {
  const [country, setCountry] = useState<JurisdictionSelection>("");
  const [legalName, setLegalName] = useState("");
  const [uen, setUen] = useState("");
  const [priority, setPriority] = useState<number | "">("");
  const [files, setFiles] = useState<File[]>([]);
  const fileInput = useRef<HTMLInputElement>(null);
  // Kept across a failed upload, so pressing Start again never opens a second case.
  const createdRun = useRef<WorkflowRun | null>(null);
  const start = useMutation({
    mutationFn: async () => {
      createdRun.current ??= (await createWorkflowCase(workflow.workflow_id, {
        legal_name: legalName.trim(),
        registration_id: uen.trim(),
        jurisdiction: country || null,
        priority: priority === "" ? null : priority,
      })).run;
      const run = createdRun.current;
      for (const file of files) await uploadWorkflowCaseDocument(run, file);
      return run.run_id;
    },
    onSuccess: onOpenRun,
  });
  function addFiles(selected: FileList | null) {
    // Copied now: the browser empties this list as soon as the input is cleared.
    const incoming = [...(selected ?? [])];
    setFiles(current => mergeSelectedFiles(current, incoming));
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    start.mutate();
  }
  return <>
    <div className="ds-page-header"><div>
      <p className="card-kicker">New case</p>
      <h1>Start {workflow.name}</h1>
      <p className="text-muted">Provide the company details and supporting documents to open a new case for this workflow.</p>
    </div></div>
    {start.isError && <div className="ds-banner ds-banner-warn" style={{ marginBottom: 16 }}>{workflowErrorMessage(start.error)}</div>}
    <form onSubmit={submit}>
      <div className="ds-two-col" style={{ alignItems: "stretch" }}>
        <div className="card" style={{ width: 420, flex: "none" }}>
          <div className="field">
            <label htmlFor="workflow-country">Jurisdiction</label>
            <select id="workflow-country" className="input" value={country} onChange={event => setCountry(event.target.value as JurisdictionSelection)}>
              <option value="">Not specified</option>
              <option value="SG">Singapore</option>
              <option value="AU">Australia</option>
              <option value="MY">Malaysia</option>
              <option value="HK">Hong Kong</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="workflow-legal-name">Company Legal Name</label>
            <input id="workflow-legal-name" className="input" value={legalName} maxLength={160} required onChange={event => setLegalName(event.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="workflow-uen">Registration ID / UEN</label>
            <input id="workflow-uen" className="input" value={uen} maxLength={32} required onChange={event => setUen(event.target.value.toUpperCase())} />
          </div>
          <div className="field">
            <span className="control-label" style={{ display: "block", marginBottom: 6 }}>Team</span>
            <strong>{actor.team_display_name ?? "Team unavailable"}</strong>
            <p className="control-help">Your assigned team owns this case.</p>
          </div>
          <div className="field">
            <label htmlFor="workflow-priority">Case priority</label>
            <select id="workflow-priority" className="input" value={priority} onChange={event => setPriority(event.target.value === "" ? "" : Number(event.target.value))}>
              <option value="">Unset</option>
              <option value={1}>Low</option>
              <option value={5}>Medium</option>
              <option value={10}>High</option>
            </select>
          </div>
        </div>
        <div className="card" style={{ flex: 1, minWidth: 380 }}>
          <p className="card-kicker">Documents</p>
          <div className="drop" onClick={() => fileInput.current?.click()}
            onDragOver={event => event.preventDefault()}
            onDrop={event => { event.preventDefault(); addFiles(event.dataTransfer.files); }}
            style={{ marginTop: 10, minHeight: 130, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
            <span>Drop files here or <span className="drop-browse">browse</span></span>
            <span className="text-muted" style={{ fontSize: 11, marginTop: 5 }}>{UPLOAD_HELP_TEXT} · up to 20 files</span>
            <input ref={fileInput} aria-label="Upload documents" type="file" accept={UPLOAD_ACCEPT} multiple hidden
              onChange={event => { addFiles(event.target.files); event.target.value = ""; }} />
          </div>
          {files.map((file, index) => (
            <div key={`${file.name}-${index}`} style={{ display: "flex", alignItems: "center", gap: 9, marginTop: 8 }}>
              <span style={{ flex: 1, fontSize: 12.5 }}>{file.name}</span>
              <button type="button" className="btn btn-ghost" onClick={() => setFiles(current => current.filter((_, position) => position !== index))}>Remove</button>
            </div>
          ))}
        </div>
      </div>
      <div style={{ marginTop: 16 }}>
        <button type="submit" className="btn btn-primary" disabled={start.isPending || files.length === 0}>{start.isPending ? "Starting…" : "Start"}</button>
      </div>
    </form>
  </>;
}

/** Progress shown for one workflow case, in the same terms as onboarding. */
export function runProgress(run: Pick<WorkflowRun, "stages">) {
  const done = run.stages.filter(stage => stage.status === "COMPLETE").length;
  const total = run.stages.length;
  return {
    done,
    total,
    percent: total === 0 ? 0 : Math.round((done / total) * 100),
    current: run.stages.find(stage => stage.status === "OPEN") ?? null,
  };
}

const STAGE_DISPLAY: Record<WorkflowRunStage["status"], { node: string; symbol: string; label: string; status: string }> = {
  COMPLETE: { node: "done", symbol: "✓", label: "Complete", status: "COMPLETE" },
  OPEN: { node: "now", symbol: "!", label: "Review required", status: "REVIEW_REQUIRED" },
  LOCKED: { node: "", symbol: "○", label: "Not reached", status: "NOT_REACHED" },
};

function focusStage(stage: WorkflowRunStage) {
  const form = document.getElementById(`workflow-stage-${stage.stage_id}`);
  if (!form) return;
  revealStage(form);
  form.scrollIntoView({ behavior: "smooth", block: "center" });
  form.focus({ preventScroll: true });
}

function useWorkflowRuns(actor: AuthenticatedProfile, workflowId: string) {
  return useQuery({
    queryKey: workflowQueryKeys.runs(actor.user_id, workflowId),
    queryFn: ({ signal }) => fetchWorkflowRuns(workflowId, signal),
    refetchOnMount: "always",
  });
}

/** The cases started under one workflow, kept apart from the onboarding Cases list. */
export function WorkflowCasesPage({ actor, workflowId, onOpenRun }: {
  actor: AuthenticatedProfile; workflowId: string; onOpenRun: (runId: string) => void;
}) {
  const workflows = useQuery(startableQuery(actor.user_id));
  const runs = useWorkflowRuns(actor, workflowId);
  const name = workflows.data?.find(item => item.workflow_id === workflowId)?.name ?? "Workflow";
  return (
    <section className="ds-root ds-page">
      <div className="ds-page-header"><div><h1>{name} cases</h1></div></div>
      <section className="card" aria-label={`${name} cases`}>
        {runs.isPending && <p className="text-muted">Loading…</p>}
        {runs.data?.length === 0 && <p className="empty-copy">No {name} cases yet.</p>}
        {Boolean(runs.data?.length) && (
          <table>
            <thead><tr><th>Company</th><th>Registration ID</th><th>Progress</th><th>Status</th><th><span className="sr-only">Actions</span></th></tr></thead>
            <tbody>{runs.data?.map(item => {
              const progress = runProgress(item.run);
              return (
                <tr key={item.run.run_id}>
                  <td>{item.company}</td><td>{item.registration_id}</td>
                  <td>{progress.done} of {progress.total} stages done</td>
                  <td>{item.run.is_complete ? "Complete" : "In progress"}</td>
                  <td><button type="button" className="btn btn-secondary" onClick={() => onOpenRun(item.run.run_id)}>Open</button></td>
                </tr>
              );
            })}</tbody>
          </table>
        )}
      </section>
    </section>
  );
}

/** One workflow case, laid out like an onboarding case but separate from it. */
export function WorkflowRunPage({ actor, workflowId, runId, onBack }: {
  actor: AuthenticatedProfile; workflowId: string; runId: string; onBack: () => void;
}) {
  const runs = useWorkflowRuns(actor, workflowId);
  const item = runs.data?.find(entry => entry.run.run_id === runId);
  const remove = useMutation({
    mutationFn: () => deleteWorkflowCase(item!.run),
    onSuccess: onBack,
  });
  // A run started moments ago may be missing from the cached list until this reload lands.
  if (runs.isPending || (!item && runs.isFetching)) return <section className="ds-root ds-page"><p className="text-muted">Loading…</p></section>;
  if (!item) {
    return <section className="ds-root ds-page"><h1>Workflow unavailable</h1><p className="text-muted">This workflow is not available.</p></section>;
  }
  const { run } = item;
  const progress = runProgress(run);
  return (
    <div className="ds-root detail-layout">
      <div className="side-panel case-pipeline-panel">
        <button type="button" className="btn btn-ghost" onClick={onBack} style={{ paddingLeft: 0 }}>← Back to {run.workflow_name} cases</button>
        <p className="card-kicker">Pipeline</p>
        <div className="ds-stage-rail" aria-label="Workflow stages">
          {run.stages.map((stage, index) => {
            const display = STAGE_DISPLAY[stage.status];
            return (
              <div className="ds-stage" key={stage.stage_id} data-status={display.status}>
                <div className="ds-stage-marker">
                  <span className={`ds-stage-node ${display.node}`}>{stage.status === "COMPLETE" ? "✓" : index + 1}</span>
                  {index < run.stages.length - 1 && <span className={`ds-stage-line ${stage.status === "COMPLETE" ? "done" : ""}`} />}
                </div>
                <div className="ds-stage-copy">
                  <button type="button" className="btn btn-ghost" style={{ padding: 0 }} onClick={() => focusStage(stage)}>{stage.name}</button>
                  <div className="text-muted">{display.label}</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
      <div className="ds-page" style={{ flex: 1 }}>
        <div className="ds-page-header"><div>
          <p className="card-kicker case-header-meta"><span>{item.registration_id} · {run.workflow_name}</span></p>
          <h1>{item.company}</h1>
        </div>
        {item.case_id === null && actor.role === "RELATIONSHIP_MANAGER" && (
          <div className="case-header-actions">
            <button type="button" className="btn btn-danger" disabled={remove.isPending}
              onClick={() => { if (window.confirm(`Delete this ${run.workflow_name} case?`)) remove.mutate(); }}>Delete case</button>
          </div>
        )}
        </div>
        {remove.isError && <div className="ds-banner ds-banner-warn" style={{ marginBottom: 16 }}>{workflowErrorMessage(remove.error)}</div>}
        <section className="card onboarding-progress" aria-labelledby="workflow-progress-heading" aria-live="polite">
          <div className="state-composition__header">
            <div>
              <p className="card-kicker">Live workflow state</p>
              <h2 id="workflow-progress-heading">{run.workflow_name} progress</h2>
            </div>
            <p className="onboarding-progress__percent" aria-hidden="true">
              <strong>{progress.percent}%</strong>
              <span>{progress.done} of {progress.total} stages done</span>
            </p>
          </div>
          <div className="onboarding-progress__bar" role="progressbar" aria-labelledby="workflow-progress-heading"
            aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress.percent}>
            <span style={{ "--onboarding-progress": `${progress.percent}%` } as CSSProperties} />
          </div>
          <dl className="onboarding-progress__facts">
            <div className="onboarding-progress__current"><dt>Current<span className="sr-only">: </span></dt><dd>{progress.current ? `${progress.current.name} — Review required` : "All stages complete"}</dd></div>
            <div><dt>Next action<span className="sr-only">: </span></dt><dd>{progress.current ? "Fill in and confirm this stage." : "No action required."}</dd></div>
          </dl>
          <ol className="onboarding-progress__stages" aria-label="Workflow stages">
            {run.stages.map(stage => {
              const display = STAGE_DISPLAY[stage.status];
              return (
                <li key={stage.stage_id} className="onboarding-progress__stage onboarding-progress__stage--actionable" data-status={display.status}>
                  <button type="button" onClick={() => focusStage(stage)}>
                    <span className="onboarding-progress__title-row">
                      <span className="onboarding-progress__symbol" aria-hidden="true">{display.symbol}</span>
                      <span className="onboarding-progress__stage-label">{stage.name}</span>
                    </span>
                    <span className="onboarding-progress__stage-status">{display.label}</span>
                    <span className="onboarding-progress__stage-action">{stage.status === "OPEN" ? "Review" : "View details"}</span>
                  </button>
                </li>
              );
            })}
          </ol>
        </section>
        <CaseWorkflowRuns caseId={item.case_id} userId={actor.user_id} scopeKey={actor.user_id}
          canFill={actor.role === "CLIENT_ONBOARDER" || actor.role === "RELATIONSHIP_MANAGER"} runs={[run]} />
      </div>
    </div>
  );
}

export default function WorkflowTab({ actor, workflowId, onOpenRun }: {
  actor: AuthenticatedProfile; workflowId: string; onOpenRun: (runId: string) => void;
}) {
  const workflows = useQuery(startableQuery(actor.user_id));
  const workflow = workflows.data?.find(item => item.workflow_id === workflowId);
  if (workflows.isPending) return <section className="ds-root ds-page"><p className="text-muted">Loading…</p></section>;
  if (!workflow) {
    return <section className="ds-root ds-page"><h1>Workflow unavailable</h1><p className="text-muted">This workflow is not available.</p></section>;
  }
  return (
    <section className="ds-root ds-page">
      {workflow.case_source === "NEW_CASE"
        ? <NewCaseStart actor={actor} workflow={workflow} onOpenRun={onOpenRun} />
        : <ExistingCaseStart actor={actor} workflow={workflow} onOpenRun={onOpenRun} />}
    </section>
  );
}
