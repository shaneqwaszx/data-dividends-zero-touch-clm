import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";

import { caseDetailQueryOptions, documentQueryOptions } from "../caseQueries";
import { paths } from "../navigation";
import type { AuthenticatedProfile } from "../types";

export default function RetainedIntakeRecovery({
  actor,
  caseId,
  onStartFresh,
}: {
  actor: AuthenticatedProfile;
  caseId: string;
  onStartFresh: () => void;
}) {
  const caseQuery = useQuery(caseDetailQueryOptions(actor.user_id, caseId));
  const documentQuery = useQuery(documentQueryOptions(actor.user_id, caseId));
  const error = caseQuery.error ?? documentQuery.error;

  return (
    <section className="ds-root ds-page" aria-labelledby="retained-intake-heading">
      <p className="section-label">Retained onboarding case</p>
      <h1 id="retained-intake-heading">Continue from retained backend state</h1>
      <p className="text-muted">
        Case {caseId} remains on the backend. Browser-selected files cannot be restored
        after refresh or in a new tab, so this page does not retry or reconstruct the
        original package.
      </p>

      {error && (
        <div className="ds-banner ds-banner-warn">
          {error instanceof Error ? error.message : "The retained case is unavailable."}
        </div>
      )}
      {!error && (caseQuery.isPending || documentQuery.isPending) && (
        <p className="text-muted">Loading retained case state…</p>
      )}
      {!error && caseQuery.data && documentQuery.data && (
        <div className="card">
          <div className="kv-row"><span className="kv-label">Case</span><span className="kv-value">{caseId}</span></div>
          <div className="kv-row"><span className="kv-label">Status</span><span className="kv-value">{caseQuery.data.status.replaceAll("_", " ")}</span></div>
          <div className="kv-row"><span className="kv-label">Current stage</span><span className="kv-value">{caseQuery.data.current_stage.replaceAll("_", " ")}</span></div>
          <div className="kv-row"><span className="kv-label">Current documents</span><span className="kv-value">{documentQuery.data.filter((item) => !item.superseded_by_document_id).length}</span></div>
          {documentQuery.data.length > 0 && (
            <ul>
              {documentQuery.data.map((document) => (
                <li key={document.document_id}>{document.display_name} · {document.state.replaceAll("_", " ")}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 16 }}>
        <Link className="btn btn-primary" to={paths.caseDetail(caseId)}>Open case details</Link>
        <Link className="btn btn-secondary" to={paths.cases}>Back to Cases</Link>
        <button className="btn btn-ghost" type="button" onClick={onStartFresh}>Start a fresh case</button>
      </div>
      <p className="control-help">
        Any supported targeted retry or recovery action remains in the authorized case
        detail view and requires a separate user action.
      </p>
    </section>
  );
}
