// M2 history, recovery and administration panels (ADR-017 §1.2, §1.4, §4; contract CC-4).
// UI shaping only: the can_* flags and capabilities decide what is offered, the backend decides
// what is allowed. Restore and reset never send stages; the backend computes the safe target.

import { useMutation, useQuery } from "@tanstack/react-query";
import { useId, useState } from "react";

import type { AuthenticatedProfile } from "../../types";
import type { WorkflowDetail } from "../../workflowApi";
import { governanceRefusal, type GovernanceRefusal } from "../../workflowGovernanceApi";
import type { DecidedProposalSummary, ProposalKind, ProposalResponse, VersionProvenance } from "../../workflowGovernanceTypes";
import {
  copyableProposal,
  copyProposal,
  createRecoveryProposal,
  daysSinceActivity,
  deactivateRequest,
  emergencyFallback,
  emergencyFallbackRequest,
  FALLBACK_REASON_MAX,
  FALLBACK_REASON_MIN,
  fallbackReasonValid,
  fetchWorkflowVersion,
  NOTE_MAX,
  offerDraftRelease,
  PROPOSAL_KIND_EXPLANATION,
  PROPOSAL_KIND_LABEL,
  provenanceText,
  reactivateRequest,
  releaseDraft,
  releaseReasonValid,
  RELEASE_REASON_MAX,
  resetToDefaultRequest,
  restoreVersionRequest,
  SAFE_TARGET_EXPLANATION,
  workflowRecoveryQueryKeys,
} from "../../workflowRecoveryApi";
import { GovernanceRefusalPanel, VersionHistoryList } from "./GovernancePanels";

type Actor = Pick<AuthenticatedProfile, "user_id" | "capabilities">;

const isHr = (actor: Actor) => actor.capabilities.includes("POLICY_MUTATE");
const isDirector = (actor: Actor) => actor.capabilities.includes("POLICY_APPROVE");

function when(value: string | null): string {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

const STATE_TEXT: Record<DecidedProposalSummary["state"], string> = {
  DRAFT: "Draft",
  PENDING_APPROVAL: "Awaiting Director decision",
  APPROVED: "Approved",
  REJECTED: "Rejected",
  WITHDRAWN: "Withdrawn",
  STALE: "Out of date",
};

type PendingAction =
  | { kind: "RESTORE_VERSION"; version: number }
  | { kind: "RESET_TO_DEFAULT" }
  | { kind: "DEACTIVATE" }
  | { kind: "REACTIVATE"; version: number };

function pendingTitle(action: PendingAction): string {
  switch (action.kind) {
    case "RESTORE_VERSION": return `Propose restore of v${action.version}`;
    case "RESET_TO_DEFAULT": return "Propose reset to default";
    case "DEACTIVATE": return "Propose deactivate";
    case "REACTIVATE": return "Propose reactivate";
  }
}

function pendingDetail(action: PendingAction): string {
  switch (action.kind) {
    case "RESTORE_VERSION":
      return `This creates a proposal to bring back version ${action.version}. ${SAFE_TARGET_EXPLANATION} The server works out that content; you can't edit it. Validate and submit it, then one Director must approve it before anything changes.`;
    case "RESET_TO_DEFAULT":
      return `This creates a proposal to return the workflow to its default content. ${SAFE_TARGET_EXPLANATION} The server works out that content; you can't edit it. Validate and submit it, then one Director must approve it before anything changes.`;
    case "DEACTIVATE":
      return `${PROPOSAL_KIND_EXPLANATION.DEACTIVATE} Nothing changes until it is approved.`;
    case "REACTIVATE":
      return `This starts a draft from version ${action.version}. Edit it if you need to, then validate and submit it as usual. ${PROPOSAL_KIND_EXPLANATION.REACTIVATE}`;
  }
}

function VersionViewer({ userId, workflowId, version, onClose }: {
  userId: string; workflowId: string; version: number; onClose: () => void;
}) {
  const query = useQuery({
    queryKey: workflowRecoveryQueryKeys.version(userId, workflowId, version),
    queryFn: ({ signal }) => fetchWorkflowVersion(workflowId, version, signal),
    retry: false,
  });
  return (
    <section className="card" aria-labelledby={`version-view-${version}`} data-testid="version-view" style={{ marginTop: 12 }}>
      <h3 id={`version-view-${version}`}>Version {version} (read-only)</h3>
      {query.isPending && <p className="text-muted" role="status">Loading version {version}…</p>}
      {query.isError && <p className="ds-banner ds-banner-warn" role="alert">{governanceRefusal(query.error).message}</p>}
      {query.data && <>
        <p className="text-muted">
          {query.data.is_active ? "Active version · " : ""}
          {query.data.provenance ? provenanceText(query.data.provenance) : `Activated by ${query.data.version.activated_by}`}
          {" · "}{when(query.data.version.activated_at)}
        </p>
        {query.data.version.stages.length === 0
          ? <p className="text-muted">No added stages.</p>
          : <ol>{query.data.version.stages.map(stage => (
            <li key={stage.stage_id}>{stage.name} · {stage.fields.length} {stage.fields.length === 1 ? "field" : "fields"}
              {stage.fields.length > 0 && ` (${stage.fields.map(field => `${field.label}${field.required ? ", required" : ""}`).join("; ")})`}
            </li>
          ))}</ol>}
      </>}
      <button type="button" className="btn btn-ghost" onClick={onClose}>Close version {version}</button>
    </section>
  );
}

/**
 * History & recovery (HR): versions with provenance, View, restore, reset, deactivate/reactivate and
 * copy of earlier proposals. One open proposal per workflow: every create action is hidden while one is open.
 */
export function HistoryRecoveryPanel({ workflow, actor, onChanged, onNotice }: {
  workflow: WorkflowDetail; actor: Actor; onChanged: () => Promise<unknown>; onNotice: (text: string | null) => void;
}) {
  const id = useId();
  const governance = workflow.governance!;
  const open = governance.open_proposal;
  const canPropose = governance.can_create_proposal && open === null;
  const active = workflow.active_version ?? 0;
  const [viewing, setViewing] = useState<number | null>(null);
  const [pending, setPending] = useState<PendingAction | null>(null);
  const [note, setNote] = useState("");
  const [refusal, setRefusal] = useState<GovernanceRefusal | null>(null);

  const create = useMutation({
    mutationFn: async (action: PendingAction) => {
      const revision = workflow.revision;
      if (action.kind === "RESTORE_VERSION") await createRecoveryProposal(workflow.workflow_id, restoreVersionRequest(revision, action.version, note));
      else if (action.kind === "RESET_TO_DEFAULT") await createRecoveryProposal(workflow.workflow_id, resetToDefaultRequest(revision, note));
      else if (action.kind === "DEACTIVATE") await createRecoveryProposal(workflow.workflow_id, deactivateRequest(revision, note));
      else {
        // Reactivate starts from the latest published content; the HR author edits it in the editor.
        const latest = await fetchWorkflowVersion(workflow.workflow_id, action.version);
        await createRecoveryProposal(workflow.workflow_id, reactivateRequest(revision, latest.version.stages, note));
      }
      return action.kind;
    },
    retry: false,
    onMutate: () => setRefusal(null),
    onSuccess: async (kind: ProposalKind) => {
      setPending(null);
      setNote("");
      await onChanged();
      onNotice(kind === "REACTIVATE"
        ? "Reactivation draft created. Edit it if needed, validate it, then submit it for approval."
        : `${PROPOSAL_KIND_LABEL[kind]} proposal created. Validate it, then submit it for one Director to approve.`);
    },
    onError: error => setRefusal(governanceRefusal(error)),
  });

  const copy = useMutation({
    mutationFn: (item: DecidedProposalSummary) => copyProposal(workflow.workflow_id, item.proposal_id, {
      expected_workflow_revision: workflow.revision,
    }),
    retry: false,
    onMutate: () => setRefusal(null),
    onSuccess: async () => {
      await onChanged();
      onNotice("Copied into a new draft authored by you. Edit it, validate it, then submit it for approval.");
    },
    onError: error => setRefusal(governanceRefusal(error)),
  });

  const busy = create.isPending || copy.isPending;
  const hr = isHr(actor);

  function versionActions(item: VersionProvenance) {
    return <>
      <button type="button" className="btn btn-ghost" aria-pressed={viewing === item.version}
        onClick={() => setViewing(value => value === item.version ? null : item.version)}>View v{item.version}</button>
      {canPropose && item.version !== active && (
        <button type="button" className="btn btn-secondary" disabled={busy}
          onClick={() => { setPending({ kind: "RESTORE_VERSION", version: item.version }); setRefusal(null); }}>
          Propose restore of v{item.version}
        </button>
      )}
    </>;
  }

  const decided = [...governance.decided_proposals].sort((a, b) => b.ended_at.localeCompare(a.ended_at));
  return (
    <VersionHistoryList governance={governance} actions={versionActions}>
      {viewing !== null && <VersionViewer userId={actor.user_id} workflowId={workflow.workflow_id} version={viewing} onClose={() => setViewing(null)} />}

      {hr && (
        <section aria-labelledby={`${id}-recovery`} data-testid="recovery-actions" style={{ marginTop: 16 }}>
          <h3 id={`${id}-recovery`}>Recovery</h3>
          {open !== null && (
            <p className="text-muted" role="note" data-testid="recovery-blocked">
              Recovery and copy are unavailable while a proposal is open. Only one proposal can be open per workflow:
              finish, withdraw or release it first.
            </p>
          )}
          {canPropose && <>
            <p className="text-muted">Recovery goes through a proposal, like any change. One Director approves or rejects it.</p>
            <div className="case-header-actions" style={{ justifyContent: "flex-start" }}>
              <button type="button" className="btn btn-secondary" disabled={busy}
                onClick={() => { setPending({ kind: "RESET_TO_DEFAULT" }); setRefusal(null); }}>Propose reset to default</button>
              {!workflow.is_onboarding && active > 0 && (
                <button type="button" className="btn btn-secondary" disabled={busy}
                  onClick={() => { setPending({ kind: "DEACTIVATE" }); setRefusal(null); }}>Propose deactivate</button>
              )}
              {!workflow.is_onboarding && active === 0 && governance.latest_version > 0 && (
                <button type="button" className="btn btn-secondary" disabled={busy}
                  onClick={() => { setPending({ kind: "REACTIVATE", version: governance.latest_version }); setRefusal(null); }}>Propose reactivate</button>
              )}
            </div>
            {!workflow.is_onboarding && active === 0 && governance.latest_version > 0 && (
              <p className="text-muted" data-testid="workflow-deactivated">This workflow is deactivated: new runs are blocked. Existing runs stay completable.</p>
            )}
          </>}
          {pending && canPropose && (
            <div className="card" role="group" aria-labelledby={`${id}-pending`} data-testid="recovery-confirm" style={{ marginTop: 12 }}>
              <h4 id={`${id}-pending`}>{pendingTitle(pending)}</h4>
              <p>{pendingDetail(pending)}</p>
              <label>Why is this needed? (optional)
                <input className="input" value={note} maxLength={NOTE_MAX} onChange={event => setNote(event.target.value)} />
              </label>
              <div className="case-header-actions" style={{ justifyContent: "flex-start" }}>
                <button type="button" className="btn btn-primary" disabled={busy} onClick={() => create.mutate(pending)}>Create proposal</button>
                <button type="button" className="btn btn-ghost" disabled={busy} onClick={() => setPending(null)}>Cancel</button>
              </div>
            </div>
          )}
          {refusal && <GovernanceRefusalPanel refusal={refusal} onReload={() => { setRefusal(null); void onChanged(); }} />}
        </section>
      )}

      {decided.length > 0 && (
        <section aria-labelledby={`${id}-earlier`} data-testid="earlier-proposals" style={{ marginTop: 16 }}>
          <h3 id={`${id}-earlier`}>Earlier proposals</h3>
          <ul>{decided.map(item => (
            <li key={item.proposal_id} data-state={item.state} data-origin={item.origin}>
              <strong>{PROPOSAL_KIND_LABEL[item.kind]}</strong> · {STATE_TEXT[item.state]}
              {" · "}{item.origin === "PRE_GOVERNANCE_DRAFT" ? "Pre-governance draft (never approved)" : `by ${item.author_id ?? "unknown"}`}
              {item.decided_by && item.state !== "WITHDRAWN" && item.state !== "STALE" && ` · decided by ${item.decided_by}`}
              {item.published_version !== null && item.state === "APPROVED" && ` · published as v${item.published_version}`}
              {" · "}{when(item.ended_at)}
              {hr && canPropose && copyableProposal(item) && <>
                {" "}<button type="button" className="btn btn-ghost" disabled={busy}
                  aria-describedby={`${id}-copy-hint`} onClick={() => copy.mutate(item)}>Copy into new draft</button>
              </>}
            </li>
          ))}</ul>
          {hr && canPropose && decided.some(copyableProposal) && (
            <p id={`${id}-copy-hint`} className="text-muted">Copying makes a new draft authored by you. The original keeps its author and history.</p>
          )}
        </section>
      )}
    </VersionHistoryList>
  );
}

/** Release an idle draft authored by someone else (HR, not the author). The backend decides. */
export function ReleaseDraftPanel({ workflow, proposal, actor, onChanged, onNotice, now }: {
  workflow: WorkflowDetail; proposal: ProposalResponse; actor: Actor;
  onChanged: () => Promise<unknown>; onNotice: (text: string | null) => void; now?: number;
}) {
  const id = useId();
  const [reason, setReason] = useState("");
  const [refusal, setRefusal] = useState<GovernanceRefusal | null>(null);
  const release = useMutation({
    mutationFn: () => releaseDraft(workflow.workflow_id, proposal.proposal_id, {
      reason: reason.trim(),
      expected_workflow_revision: workflow.revision,
      expected_proposal_revision: proposal.revision,
    }),
    retry: false,
    onMutate: () => setRefusal(null),
    onSuccess: async () => {
      await onChanged();
      onNotice("Draft released. It is now withdrawn, its content is kept, and it can be copied into a new draft.");
    },
    onError: error => setRefusal(governanceRefusal(error)),
  });
  if (!offerDraftRelease(proposal, actor, now)) return null;
  const days = daysSinceActivity(proposal, now);
  return (
    <section className="card" aria-labelledby={`${id}-release`} data-testid="release-draft" style={{ marginBottom: 16 }}>
      <h2 id={`${id}-release`}>Release this draft</h2>
      <p>
        This draft by {proposal.author_id ?? "an unknown author"} has had no activity for {days} days. Releasing it ends it as
        withdrawn so a new proposal can be made. Its content is kept and can be copied into a new draft. Releasing never
        submits or publishes anything.
      </p>
      <label htmlFor={`${id}-reason`}>Reason (required)</label>
      <input id={`${id}-reason`} className="input" value={reason} maxLength={RELEASE_REASON_MAX}
        disabled={release.isPending} onChange={event => setReason(event.target.value)} />
      <button type="button" className="btn btn-danger" style={{ marginTop: 8 }}
        disabled={release.isPending || !releaseReasonValid(reason)} onClick={() => release.mutate()}>Release draft</button>
      {refusal && <GovernanceRefusalPanel refusal={refusal} onReload={() => { setRefusal(null); void onChanged(); }} />}
    </section>
  );
}

/** Director only (UI shaping): the single-actor emergency publication of a safe target. */
export function EmergencyFallbackPanel({ workflow, actor, onChanged, onNotice }: {
  workflow: WorkflowDetail; actor: Actor; onChanged: () => Promise<unknown>; onNotice: (text: string | null) => void;
}) {
  const id = useId();
  const governance = workflow.governance!;
  const versions = [...governance.version_provenance].sort((a, b) => b.version - a.version);
  const [expanded, setExpanded] = useState(false);
  const [target, setTarget] = useState<"VERSION" | "DEFAULT">(versions.length ? "VERSION" : "DEFAULT");
  const [version, setVersion] = useState<number | null>(versions[0]?.version ?? null);
  const [reason, setReason] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [refusal, setRefusal] = useState<GovernanceRefusal | null>(null);
  const publish = useMutation({
    mutationFn: () => emergencyFallback(workflow.workflow_id, emergencyFallbackRequest(
      workflow.revision, reason, target === "DEFAULT" ? "DEFAULT" : { version: version! },
    )),
    retry: false,
    onMutate: () => setRefusal(null),
    onSuccess: async result => {
      setExpanded(false);
      setReason("");
      setConfirmed(false);
      onNotice(
        `Emergency fallback published: version ${result.published_version} is now active (${provenanceText(result.provenance)}). `
        + `HR has been notified and the notice stays until an HR user acknowledges it.`
        + (result.staled_proposal_ids.length ? ` ${result.staled_proposal_ids.length} open proposal${result.staled_proposal_ids.length === 1 ? " is" : "s are"} now out of date.` : ""),
      );
      await onChanged();
    },
    onError: error => setRefusal(governanceRefusal(error)),
  });
  if (!isDirector(actor)) return null;
  const length = reason.trim().length;
  const ready = fallbackReasonValid(reason) && confirmed && (target === "DEFAULT" || version !== null) && !publish.isPending;
  return (
    <section className="card" aria-labelledby={`${id}-fallback`} data-testid="emergency-fallback" style={{ marginTop: 16 }}>
      <h2 id={`${id}-fallback`}>Emergency fallback</h2>
      <p className="text-muted">
        For emergencies only. A Director can publish a safe earlier version or the default alone, without a proposal or approval.
      </p>
      {!expanded && <button type="button" className="btn btn-secondary" aria-expanded={false} onClick={() => setExpanded(true)}>Start emergency fallback</button>}
      {expanded && <>
        <fieldset style={{ border: 0, margin: "8px 0", padding: 0 }}>
          <legend>Fall back to</legend>
          <label><input type="radio" name={`${id}-target`} checked={target === "VERSION"} disabled={versions.length === 0}
            onChange={() => setTarget("VERSION")} /> A published version</label>{" "}
          <label><input type="radio" name={`${id}-target`} checked={target === "DEFAULT"} onChange={() => setTarget("DEFAULT")} /> The default</label>
          {target === "VERSION" && versions.length > 0 && (
            <label>Version
              <select className="input" value={version ?? ""} onChange={event => setVersion(Number(event.target.value))}>
                {versions.map(item => <option key={item.version} value={item.version}>v{item.version} · {provenanceText(item)}</option>)}
              </select>
            </label>
          )}
        </fieldset>
        <label htmlFor={`${id}-reason`}>Reason (required, {FALLBACK_REASON_MIN}–{FALLBACK_REASON_MAX} characters, recorded permanently and shown to HR)</label>
        <textarea id={`${id}-reason`} className="input" value={reason} maxLength={FALLBACK_REASON_MAX + 40}
          aria-invalid={reason.length > 0 && !fallbackReasonValid(reason)} aria-describedby={`${id}-count`}
          onChange={event => setReason(event.target.value)} />
        <p id={`${id}-count`} className="text-muted" aria-live="polite">{length} / {FALLBACK_REASON_MAX}
          {reason.length > 0 && length < FALLBACK_REASON_MIN && ` · at least ${FALLBACK_REASON_MIN} characters`}
          {length > FALLBACK_REASON_MAX && ` · at most ${FALLBACK_REASON_MAX} characters`}
        </p>
        <div className="ds-banner ds-banner-warn" id={`${id}-warning`}>
          <p style={{ margin: 0 }}>
            <strong>This is a single-actor emergency publication.</strong> It is published at once with no approval and is
            recorded as an emergency fallback, never as approved. {SAFE_TARGET_EXPLANATION} Any open proposal becomes out of
            date (it is kept). HR is notified, and the notice stays until an HR user acknowledges it.
          </p>
          <label>
            <input type="checkbox" checked={confirmed} aria-describedby={`${id}-warning`} onChange={event => setConfirmed(event.target.checked)} />{" "}
            I understand this publishes without approval and HR will be notified.
          </label>
        </div>
        <div className="case-header-actions" style={{ justifyContent: "flex-start", marginTop: 8 }}>
          <button type="button" className="btn btn-danger" disabled={!ready} onClick={() => publish.mutate()}>Publish emergency fallback</button>
          <button type="button" className="btn btn-ghost" disabled={publish.isPending} onClick={() => setExpanded(false)}>Cancel</button>
        </div>
      </>}
      {refusal && <GovernanceRefusalPanel refusal={refusal} onReload={() => { setRefusal(null); void onChanged(); }} />}
    </section>
  );
}
