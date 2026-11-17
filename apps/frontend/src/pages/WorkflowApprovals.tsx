import { useQuery } from "@tanstack/react-query";

import type { AuthenticatedProfile } from "../types";
import { approvalErrorView, fetchApprovalInbox, workflowApprovalQueryKeys } from "../workflowApprovalsApi";
import type { ApprovalInboxItem, ChangeCounts } from "../workflowGovernanceTypes";

export function formatTimestamp(value: string | null): string {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

export function changeSummary(changes: ChangeCounts): string {
  const parts: string[] = [];
  const add = (count: number, singular: string, plural: string, verb: string) => {
    if (count > 0) parts.push(`${count} ${count === 1 ? singular : plural} ${verb}`);
  };
  add(changes.stages_added, "stage", "stages", "added");
  add(changes.stages_removed, "stage", "stages", "removed");
  add(changes.stages_changed, "stage", "stages", "changed");
  add(changes.fields_added, "field", "fields", "added");
  add(changes.fields_removed, "field", "fields", "removed");
  add(changes.fields_changed, "field", "fields", "changed");
  return parts.length ? parts.join(", ") : "No stage or field changes";
}

/** Explains why the UI offers no decision. The backend still decides; this only shapes the page. */
export function noDecisionReason(item: { proposal: { author_id: string | null; can_decide: boolean } }, actor: AuthenticatedProfile): string | null {
  if (item.proposal.can_decide) return null;
  if (item.proposal.author_id && item.proposal.author_id === actor.user_id) {
    return "You authored this proposal. Another Director must decide it.";
  }
  return "You cannot decide this proposal.";
}

export function versionLabel(base: number, active: number): string {
  const name = (value: number) => (value === 0 ? "none" : `v${value}`);
  return base === active ? `Base ${name(base)} = active` : `Base ${name(base)} · active ${name(active)} (stale)`;
}

function InboxRow({ item, actor, onOpen }: { item: ApprovalInboxItem; actor: AuthenticatedProfile; onOpen: (workflowId: string, proposalId: string) => void }) {
  const refusal = noDecisionReason(item, actor);
  const obligations = item.permanent_obligation_count;
  return (
    <tr>
      <td>
        <strong>{item.workflow_name}</strong>{" "}
        {item.is_onboarding && <span className="tag tag-accent">Onboarding</span>}
        {item.proposal.note && <div className="text-muted">{item.proposal.note}</div>}
      </td>
      <td>{item.proposal.author_id ?? "—"}</td>
      <td>{formatTimestamp(item.proposal.submitted_at)}</td>
      <td>{versionLabel(item.proposal.base_version, item.active_version)}</td>
      <td>{changeSummary(item.changes)}</td>
      <td>
        {obligations > 0
          ? <span className="tag tag-warn">{obligations} permanent {obligations === 1 ? "obligation" : "obligations"}</span>
          : <span className="text-muted">None</span>}
      </td>
      <td>
        <button
          type="button"
          className={refusal ? "btn btn-ghost" : "btn btn-primary"}
          aria-label={`${refusal ? "View" : "Review and decide"} ${item.workflow_name} proposal`}
          onClick={() => onOpen(item.workflow_id, item.proposal.proposal_id)}
        >
          {refusal ? "View" : "Review"}
        </button>
        {refusal && <div className="text-muted" role="note">{refusal}</div>}
      </td>
    </tr>
  );
}

export default function WorkflowApprovals({ actor, onOpen }: {
  actor: AuthenticatedProfile;
  onOpen: (workflowId: string, proposalId: string) => void;
}) {
  const query = useQuery({
    queryKey: workflowApprovalQueryKeys.inbox(actor),
    queryFn: ({ signal }) => fetchApprovalInbox(signal),
    retry: false,
  });

  const header = (
    <div className="ds-page-header">
      <div>
        <p className="card-kicker">Director · one decision per proposal</p>
        <h1>Workflow approvals</h1>
        <p className="text-muted">HR authors workflow changes. You approve or reject each one with a reason. You cannot edit a proposal or decide your own.</p>
      </div>
    </div>
  );

  if (query.isPending) return <section className="ds-root ds-page">{header}<p className="text-muted" role="status">Loading pending proposals…</p></section>;
  if (query.isError) {
    return (
      <section className="ds-root ds-page">{header}
        <p className="ds-banner ds-banner-warn" role="alert">{approvalErrorView(query.error).message}</p>
        <button type="button" className="btn btn-secondary" onClick={() => void query.refetch()}>Try again</button>
      </section>
    );
  }
  if (query.data === null) {
    return <section className="ds-root ds-page">{header}<p className="text-muted">Workflow approvals are not available on this server.</p></section>;
  }
  const items = query.data.items;
  return (
    <section className="ds-root ds-page">
      {header}
      <section className="card" aria-labelledby="workflow-approvals-pending">
        <h2 id="workflow-approvals-pending">Pending ({items.length})</h2>
        {items.length === 0
          ? <p className="text-muted">No workflow proposals are waiting for a decision.</p>
          : (
            <table>
              <caption className="sr-only">Workflow proposals waiting for a Director decision</caption>
              <thead>
                <tr>
                  <th scope="col">Workflow</th>
                  <th scope="col">Author</th>
                  <th scope="col">Submitted</th>
                  <th scope="col">Version</th>
                  <th scope="col">Changes</th>
                  <th scope="col">Permanent obligations</th>
                  <th scope="col"><span className="sr-only">Action</span></th>
                </tr>
              </thead>
              <tbody>
                {items.map(item => <InboxRow key={`${item.workflow_id}:${item.proposal.proposal_id}`} item={item} actor={actor} onOpen={onOpen} />)}
              </tbody>
            </table>
          )}
      </section>
    </section>
  );
}
