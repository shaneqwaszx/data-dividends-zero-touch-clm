// Governance notices (RD-6, ADR-017 §4/§5). HR acknowledges; Directors see them read-only.
// UI shaping only: the backend allows acknowledgement for HR alone.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { ApiError } from "../../api";
import type { AuthenticatedProfile } from "../../types";
import { workflowQueryKeys } from "../../workflowApi";
import { governanceRefusal } from "../../workflowGovernanceApi";
import type { NoticeItem } from "../../workflowGovernanceTypes";
import { acknowledgeNotice, fetchNotices, workflowRecoveryQueryKeys } from "../../workflowRecoveryApi";

function when(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

function noticeHeadline(item: NoticeItem): string {
  const { notice } = item;
  const what = notice.kind === "EMERGENCY_FALLBACK" ? "Emergency fallback" : notice.kind.replaceAll("_", " ").toLowerCase();
  const approval = notice.kind === "EMERGENCY_FALLBACK" ? " — not approved" : "";
  return `${what} on ${item.workflow_name}: version ${notice.version} by ${notice.raised_by} at ${when(notice.raised_at)}${approval}`;
}

export function WorkflowNoticesPanel({ actor, workflowId }: {
  actor: Pick<AuthenticatedProfile, "user_id" | "capabilities">;
  /** Only this workflow's notices; all workflows when omitted. */
  workflowId?: string;
}) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: workflowRecoveryQueryKeys.notices(actor.user_id),
    queryFn: ({ signal }) => fetchNotices(signal),
    retry: false,
  });
  const [message, setMessage] = useState<string | null>(null);
  const canAcknowledge = actor.capabilities.includes("POLICY_MUTATE");
  const acknowledge = useMutation({
    mutationFn: (item: NoticeItem) => acknowledgeNotice(item.notice.notice_id, {
      workflow_id: item.workflow_id,
      expected_workflow_revision: item.workflow_revision,
    }),
    retry: false,
    onMutate: () => setMessage(null),
    onSuccess: async () => {
      setMessage("Notice acknowledged.");
      // The workflow list key prefixes the notices key, so this refreshes both.
      await queryClient.invalidateQueries({ queryKey: workflowQueryKeys.list(actor.user_id) });
    },
    onError: async error => {
      if (error instanceof ApiError && error.status === 409) {
        setMessage("This notice or its workflow changed. Nothing was changed. The notices were reloaded; check them and acknowledge again.");
        await queryClient.invalidateQueries({ queryKey: workflowRecoveryQueryKeys.notices(actor.user_id) });
      } else {
        setMessage(governanceRefusal(error).message);
      }
    },
  });

  // A failed read (other than 404, which means notices are unavailable) never blocks the page.
  if (query.isError && !query.data) {
    if (!canAcknowledge) return null;
    return (
      <div className="ds-banner ds-banner-warn" role="status" data-testid="workflow-notices-error" style={{ marginBottom: 16 }}>
        Notices could not be loaded.{" "}
        <button type="button" className="btn btn-secondary" disabled={query.isFetching} onClick={() => void query.refetch()}>Retry</button>
      </div>
    );
  }
  if (!query.data) return null;
  const items = query.data.items.filter(item => !workflowId || item.workflow_id === workflowId);
  if (items.length === 0 && !message) return null;
  return (
    <section className="ds-banner ds-banner-warn" role="region" aria-labelledby="workflow-notices" data-testid="workflow-notices" style={{ marginBottom: 16 }}>
      <h2 id="workflow-notices" style={{ marginTop: 0 }}>Workflow notices ({items.length})</h2>
      <p style={{ margin: 0 }}>
        {canAcknowledge
          ? (items.every(item => item.notice.kind === "EMERGENCY_FALLBACK")
            ? "A Director published an emergency fallback without approval. Review it and acknowledge each notice."
            : "These workflow events need HR attention. Review each one and acknowledge it.")
          : "Read-only: an HR user must acknowledge these notices."}
      </p>
      {message && <p role="status" style={{ margin: "6px 0 0" }}>{message}</p>}
      <ul>{items.map(item => (
        <li key={item.notice.notice_id} data-notice-id={item.notice.notice_id}>
          <strong>{noticeHeadline(item)}</strong>
          <div>Reason: {item.notice.reason}</div>
          {canAcknowledge && (
            <button type="button" className="btn btn-secondary" disabled={acknowledge.isPending}
              aria-label={`Acknowledge notice for ${item.workflow_name} version ${item.notice.version}`}
              onClick={() => acknowledge.mutate(item)}>Acknowledge</button>
          )}
        </li>
      ))}</ul>
    </section>
  );
}
