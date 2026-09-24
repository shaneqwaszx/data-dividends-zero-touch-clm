import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";

import { caseDetailQueryOptions, documentQueryOptions, ownershipQueryOptions } from "../caseQueries";
import { paths } from "../navigation";
import type { AuthenticatedProfile } from "../types";
import { mapZeroTouchCaseToClientDetail } from "../viewModels";

const UNAVAILABLE = "Not available in current POC";

function DownloadIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3v12m0 0 4-4m-4 4-4-4" />
      <path d="M4 19h16" />
    </svg>
  );
}

export function ClientRecordActions() {
  return (
    <div className="client-record-actions">
      <button type="button" className="btn btn-secondary" disabled title="Record export is not available in current POC">Export record</button>
      <button type="button" className="btn btn-secondary" disabled title={UNAVAILABLE}>Start a review</button>
    </div>
  );
}

export default function ClientDetail({
  clientId,
  actor,
}: {
  clientId: string;
  actor: AuthenticatedProfile;
}) {
  const summary = useQuery(caseDetailQueryOptions(actor.user_id, clientId));
  const documents = useQuery(documentQueryOptions(actor.user_id, clientId));
  const ownership = useQuery(ownershipQueryOptions(actor.user_id, clientId));
  const client = summary.data && documents.data && ownership.data
    ? mapZeroTouchCaseToClientDetail(summary.data, documents.data, ownership.data)
    : null;
  const requestError = summary.error ?? documents.error ?? ownership.error;

  if (summary.data && summary.data.status !== "COMPLETED") {
    return (
      <section className="ds-root ds-page">
        <h1>Client record unavailable</h1>
        <p className="text-muted">This case has not completed the POC onboarding workflow.</p>
        <Link className="btn btn-secondary" to={paths.caseDetail(clientId)}>Open case details</Link>
      </section>
    );
  }
  if (requestError && !client) {
    return <div className="ds-root ds-page"><Link className="btn btn-ghost" style={{ paddingLeft: 0 }} to={paths.onboarded}>← Back to Onboarded</Link><div className="ds-banner ds-banner-warn">{requestError instanceof Error ? requestError.message : "The client detail is unavailable."}</div></div>;
  }
  if (!client) return <div className="ds-root ds-page"><Link className="btn btn-ghost" style={{ paddingLeft: 0 }} to={paths.onboarded}>← Back to Onboarded</Link><p className="text-muted">Loading client…</p></div>;

  return (
    <div className="ds-root detail-layout">
      <div className="side-panel">
        <h4 style={{ marginTop: 0 }}>Client record</h4>
        <div>
          <div className="kv-row"><span className="kv-label">GoldTier party ID</span><span className="kv-value">{client.mock_goldtier_party_id ?? "—"}</span></div>
          <div className="kv-row"><span className="kv-label">Status</span><span className="kv-value"><span className="tag tag-accent">{client.status.replaceAll("_", " ")}</span></span></div>
          <div className="kv-row"><span className="kv-label">Onboarded</span><span className="kv-value">{new Date(client.onboarded_at).toLocaleString()}</span></div>
          <div className="kv-row"><span className="kv-label">Risk rating</span><span className="kv-value">—</span></div>
          <div className="kv-row"><span className="kv-label">Case</span><span className="kv-value">{client.case_id}</span></div>
          <div className="kv-row"><span className="kv-label">Jurisdiction</span><span className="kv-value">{client.jurisdiction ?? "—"}</span></div>
        </div>
        <hr className="hr" />
        <h4>Schedule</h4>
        <div>
          <div className="kv-row"><span className="kv-label">Next review</span><span className="kv-value">{UNAVAILABLE}</span></div>
          <div className="kv-row"><span className="kv-label">Re-screening</span><span className="kv-value">{UNAVAILABLE}</span></div>
          <div className="kv-row"><span className="kv-label">Registry refresh</span><span className="kv-value">{UNAVAILABLE}</span></div>
        </div>
        <hr className="hr" />
        <h4>Documents</h4>
        <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
          {client.documents.length === 0 && <span className="text-muted">No document records available.</span>}
          {client.documents.map((document) => (
            <div key={`${document.name}-${document.note}`} title={document.details} style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ flex: 1, fontSize: 12, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{document.name}</span>
              <span className="text-muted" style={{ fontSize: 11 }}>{document.note}</span>
              <button type="button" className="btn btn-ghost" style={{ padding: 2, minWidth: 0 }} disabled title="Download unavailable: raw files are not retained"><DownloadIcon /></button>
            </div>
          ))}
        </div>
        <hr className="hr" />
        <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
          <Link className="btn btn-ghost" style={{ justifyContent: "flex-start", paddingLeft: 0 }} to={paths.auditCase(client.case_id)}>Audit trail</Link>
          <Link className="btn btn-ghost" style={{ justifyContent: "flex-start", paddingLeft: 0 }} to={paths.onboarded}>Back to Onboarded</Link>
        </div>
      </div>

      <div className="ds-page" style={{ flex: 1 }}>
        <div className="ds-page-header">
          <div><p className="card-kicker">{client.mock_goldtier_party_id ?? "GoldTier party —"} · {client.case_id} · {client.registration_id} · {client.jurisdiction ?? "—"}</p><h1>{client.company_name ?? client.registration_id}</h1></div>
          <ClientRecordActions />
        </div>
        <div className="ds-banner poc-boundary">
          Completed zero-touch POC workflow evidence. This view is not a production client master, approval record, or live GoldTier acceptance.
        </div>

        <div className="ds-two-col">
          <div style={{ flex: 1 }}>
            <h4>Corporate particulars</h4>
            <div style={{ marginBottom: 20 }}>
              <div className="kv-row"><span className="kv-label">Company name</span><span className="kv-value">{client.company_name ?? "—"}</span></div>
              <div className="kv-row"><span className="kv-label">Registration ID</span><span className="kv-value">{client.registration_id}</span></div>
              <div className="kv-row"><span className="kv-label">Entity type</span><span className="kv-value">{client.entity_type ?? "—"}</span></div>
              <div className="kv-row"><span className="kv-label">Registry status</span><span className="kv-value">{client.registry_status ?? "—"}</span></div>
              <div className="kv-row"><span className="kv-label">Registration date</span><span className="kv-value">{client.registration_date ?? "—"}</span></div>
              <div className="kv-row"><span className="kv-label">Registered address</span><span className="kv-value">{client.registered_address ?? "—"}</span></div>
              <div className="kv-row"><span className="kv-label">Principal place of business</span><span className="kv-value">{UNAVAILABLE}</span></div>
              <div className="kv-row"><span className="kv-label">Financial year end</span><span className="kv-value">{UNAVAILABLE}</span></div>
              <div className="kv-row"><span className="kv-label">Tax residency</span><span className="kv-value">{UNAVAILABLE}</span></div>
            </div>

            <h4>Capital and activity</h4>
            <div style={{ marginBottom: 20 }}>
              {['Issued capital','Issued shares','Principal activity','Secondary activity','Countries of operation','Expected annual volume'].map((label) => <div className="kv-row" key={label}><span className="kv-label">{label}</span><span className="kv-value">{UNAVAILABLE}</span></div>)}
            </div>

            <h4>Directors</h4>
            <div className="table-card" style={{ marginBottom: 20 }}><table className="table"><thead><tr><th>Name</th><th>Identification</th><th>Date of birth</th><th>Appointed</th><th>Source</th></tr></thead><tbody>
              {client.directors.length === 0 && <tr><td colSpan={5}>Not available.</td></tr>}
              {client.directors.map((director) => <tr key={director.name}><td>{director.name}</td><td>{director.identification ?? "—"}</td><td>—</td><td>{director.appointed ?? "—"}</td><td className="src2">{director.source}</td></tr>)}
            </tbody></table></div>

            <h4>Provisional beneficial-owner candidates</h4>
            <div className="table-card" style={{ marginBottom: 20 }}><table className="table"><thead><tr><th>Owner</th><th>Holding</th><th>Type</th><th>Path</th><th>Source</th></tr></thead><tbody>
              {client.beneficial_owners.length === 0 && <tr><td colSpan={5}>No provisional candidate is available.</td></tr>}
              {client.beneficial_owners.map((owner) => <tr key={owner.owner}><td>{owner.owner}</td><td>{owner.holding}</td><td>{owner.type}</td><td>{owner.path}</td><td>{owner.source}</td></tr>)}
            </tbody></table></div>

            <h4>Relationship</h4>
            <div>{['Purpose','Source of funds','Primary contact','Contact email','Onboarded by'].map((label) => <div className="kv-row" key={label}><span className="kv-label">{label}</span><span className="kv-value">{UNAVAILABLE}</span></div>)}</div>
          </div>

          <div style={{ width: 352 }}>
            <h4>Onboarding record</h4>
            <div className="table-card" style={{ marginBottom: 12 }}><table className="table"><thead><tr><th>Stage</th><th>Method</th><th>Cleared</th></tr></thead><tbody>
              {client.onboarding_record.map((row) => <tr key={row.stage}><td>{row.stage}</td><td>{row.method}</td><td>{row.cleared_at === "—" ? "—" : new Date(row.cleared_at).toLocaleString()}</td></tr>)}
            </tbody></table></div>
            <div style={{ marginBottom: 20 }}>
              <div className="kv-row"><span className="kv-label">Loops</span><span className="kv-value">—</span></div>
              <div className="kv-row"><span className="kv-label">Human touches</span><span className="kv-value">{client.human_touches}</span></div>
              <div className="kv-row"><span className="kv-label">Elapsed</span><span className="kv-value">{client.elapsed_time_ms === null ? "—" : `${client.elapsed_time_ms} ms`}</span></div>
            </div>

            <h4>Check results at completion</h4>
            <div className="table-card" style={{ marginBottom: 20 }}><table className="table"><thead><tr><th>Check</th><th>Outcome</th></tr></thead><tbody>
              {client.check_results.map((result) => <tr key={result.check}><td>{result.check}</td><td><span className="tag tag-accent">{result.outcome}</span></td></tr>)}
            </tbody></table></div>

            <h4>Registry operation evidence</h4>
            <div className="table-card table-scroll" tabIndex={0} style={{ marginBottom: 20 }}><table className="table"><thead><tr><th>Operation</th><th>Status</th><th>Records</th><th>Provenance</th></tr></thead><tbody>
              {client.registry_operations.length === 0 && <tr><td colSpan={4}>Not available in current POC state.</td></tr>}
              {client.registry_operations.map((operation) => <tr key={operation.operation}><td>{operation.operation.replaceAll("_", " ")}</td><td>{operation.status}</td><td>{operation.record_count}</td><td>{operation.provenance}</td></tr>)}
            </tbody></table></div>

            <h4>GoldTier target operations</h4>
            <div style={{ marginBottom: 20 }}>
              {client.target_operations.map((operation) => <div className="kv-row" key={operation.operation}><span className="kv-label">{operation.operation}</span><span className="kv-value">{operation.status}</span></div>)}
              <div className="kv-row"><span className="kv-label">Final outcome</span><span className="kv-value">{client.final_outcome ?? "—"}</span></div>
              <div className="kv-row"><span className="kv-label">Blockers</span><span className="kv-value">{client.readiness_blockers.length ? client.readiness_blockers.join(" · ") : "None"}</span></div>
              <div className="kv-row"><span className="kv-label">Warnings</span><span className="kv-value">{client.readiness_warnings.length ? client.readiness_warnings.join(" · ") : "None"}</span></div>
            </div>

            <h4>Since onboarding</h4>
            <div>{client.since_onboarding.map((event, index) => <div className="kv-row" key={`${event.date}-${index}`}><span className="kv-label">{new Date(event.date).toLocaleString()}</span><span className="kv-value">{event.event}</span></div>)}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
