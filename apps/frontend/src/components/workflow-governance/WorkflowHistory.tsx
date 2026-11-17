// Workflow History: governance events (ADR-017 §5) newest first, then the pre-governance audit.
// Only a Director's decision on a proposal is ever worded as approval; an emergency fallback and
// legacy (pre-governance) entries never are (ADR-017 §1.4, §4).

import type { WorkflowDetail } from "../../workflowApi";
import type { GovernanceEvent, GovernanceEventKind } from "../../workflowGovernanceTypes";

const versionText = (event: GovernanceEvent) => (event.version !== null ? ` · version ${event.version}` : "");

export function governanceEventLabel(event: GovernanceEvent): string {
  const labels: Record<GovernanceEventKind, string> = {
    MIGRATED: "Approval governance enabled",
    WORKFLOW_CREATED: "Workflow created",
    PROPOSAL_CREATED: "Proposal created",
    PROPOSAL_EDITED: "Proposal edited",
    PROPOSAL_SUBMITTED: "Proposal submitted",
    PROPOSAL_WITHDRAWN: "Proposal withdrawn",
    PROPOSAL_APPROVED: "Proposal approved by a Director",
    PROPOSAL_REJECTED: "Proposal rejected",
    PROPOSAL_STALE: "Proposal out of date",
    VERSION_PUBLISHED: event.version !== null ? `Version ${event.version} published` : "Version published",
    DRAFT_RELEASED: "Draft released",
    DRAFT_COPIED: "Copied into a new draft",
    EMERGENCY_FALLBACK: `Emergency fallback (not approved)${versionText(event)}`,
    NOTICE_RAISED: "Notice raised for HR",
    NOTICE_ACKNOWLEDGED: "Notice acknowledged",
    DEACTIVATED: "Workflow deactivated",
    REACTIVATED: `Workflow reactivated${versionText(event)}`,
  };
  return labels[event.kind] ?? "Workflow event";
}

function when(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

export function WorkflowHistory({ workflow }: { workflow: Pick<WorkflowDetail, "audit" | "governance"> }) {
  const governance = workflow.governance?.migrated ? workflow.governance : null;
  const legacy = [...workflow.audit].reverse();
  const intro = <p className="text-muted">Open cases follow the latest active version. Cases already sent stay as they were.</p>;

  if (!governance) {
    // Not migrated: the existing audit view, unchanged.
    return (
      <section className="card" aria-labelledby="workflow-history" style={{ marginTop: 16 }}>
        <h2 id="workflow-history">History</h2>
        {intro}
        {legacy.length === 0 && <p className="text-muted">No changes yet.</p>}
        <ul>{legacy.map(item => (
          <li key={`${item.occurred_at}-${item.action}`}>{when(item.occurred_at)} · {item.actor_id} · {item.summary}</li>
        ))}</ul>
      </section>
    );
  }

  const events = [...governance.recent_events].sort((a, b) => b.sequence - a.sequence);
  return (
    <section className="card" aria-labelledby="workflow-history" data-testid="workflow-history" style={{ marginTop: 16 }}>
      <h2 id="workflow-history">History</h2>
      {intro}
      {events.length === 0 && legacy.length === 0 && <p className="text-muted">No changes yet.</p>}
      {events.length > 0 && (
        <ul aria-label="Governance events" data-testid="governance-events">{events.map(event => (
          <li key={event.sequence} data-kind={event.kind}>
            <strong>{governanceEventLabel(event)}</strong> · {event.actor_id ?? "system"} · {when(event.occurred_at)}
          </li>
        ))}</ul>
      )}
      {legacy.length > 0 && <>
        <h3 id="workflow-history-legacy">Before approval governance</h3>
        <p className="text-muted">Recorded before approval governance; these changes were not independently approved.</p>
        <ul aria-labelledby="workflow-history-legacy" data-testid="legacy-audit">{legacy.map(item => (
          <li key={`${item.occurred_at}-${item.action}`}>
            <span className="tag tag-neutral">Before approval governance</span> {when(item.occurred_at)} · {item.actor_id} · {item.summary}
          </li>
        ))}</ul>
      </>}
    </section>
  );
}
