import { useEffect, useState } from "react";

import { ApiError, fetchClient } from "../api";
import type { ClientRecord } from "../types";

function downloadJson(filename: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function downloadDocument(name: string) {
  const blob = new Blob([`Placeholder content for ${name} — no source file is stored in this POC.`], {
    type: "text/plain",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}

function DownloadIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3v12m0 0 4-4m-4 4-4-4" />
      <path d="M4 19h16" />
    </svg>
  );
}

export default function ClientDetail({
  clientId,
  onBack,
  onOpenAudit,
}: {
  clientId: string;
  onBack: () => void;
  onOpenAudit: (caseId: string) => void;
}) {
  const [client, setClient] = useState<ClientRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetchClient(clientId)
      .then((value) => {
        setClient(value);
        setError(null);
      })
      .catch((requestError) => {
        setError(
          requestError instanceof ApiError ? requestError.message : "The client record is unavailable.",
        );
      });
  }, [clientId]);

  if (error) {
    return (
      <div className="ds-root ds-page">
        <button type="button" className="btn btn-ghost" style={{ paddingLeft: 0 }} onClick={onBack}>
          ← Back to Onboarded
        </button>
        <div className="ds-banner ds-banner-warn">{error}</div>
      </div>
    );
  }

  if (!client) {
    return (
      <div className="ds-root ds-page">
        <button type="button" className="btn btn-ghost" style={{ paddingLeft: 0 }} onClick={onBack}>
          ← Back to Onboarded
        </button>
        <p className="text-muted">Loading client…</p>
      </div>
    );
  }

  return (
    <div className="ds-root" style={{ display: "flex", alignItems: "stretch" }}>
      <div className="side-panel">
        <h4 style={{ marginTop: 0 }}>Client record</h4>
        <div>
          <div className="kv-row"><span className="kv-label">Client ID</span><span className="kv-value">{client.client_id}</span></div>
          <div className="kv-row"><span className="kv-label">Status</span><span className="kv-value"><span className="tag tag-accent">Onboarded</span></span></div>
          <div className="kv-row"><span className="kv-label">Onboarded</span><span className="kv-value">{new Date(client.onboarded_at).toLocaleString()}</span></div>
          <div className="kv-row"><span className="kv-label">Risk rating</span><span className="kv-value">{client.risk_rating ?? "—"}</span></div>
          <div className="kv-row"><span className="kv-label">Case</span><span className="kv-value">{client.case_id}</span></div>
          <div className="kv-row"><span className="kv-label">Jurisdiction</span><span className="kv-value">{client.jurisdiction ?? "—"}</span></div>
        </div>
        <hr className="hr" />
        <h4>Schedule</h4>
        <div>
          <div className="kv-row"><span className="kv-label">Next review</span><span className="kv-value">{new Date(client.next_review_date).toLocaleDateString()}</span></div>
          <div className="kv-row"><span className="kv-label">Re-screening</span><span className="kv-value">Every {client.re_screening_cadence_months} month(s)</span></div>
          <div className="kv-row"><span className="kv-label">Registry refresh</span><span className="kv-value">Annual with the review</span></div>
        </div>
        <hr className="hr" />
        <h4>Documents</h4>
        <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
          {client.documents.map((document) => (
            <div key={document.name} style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ flex: 1, fontSize: 12, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {document.name}
              </span>
              <span className="text-muted" style={{ fontSize: 11 }}>{document.note}</span>
              <button
                type="button"
                className="btn btn-ghost"
                style={{ padding: 2, minWidth: 0 }}
                title={`Download ${document.name}`}
                onClick={() => downloadDocument(document.name)}
              >
                <DownloadIcon />
              </button>
            </div>
          ))}
        </div>
        <hr className="hr" />
        <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
          <button type="button" className="btn btn-ghost" style={{ justifyContent: "flex-start", paddingLeft: 0 }} onClick={() => onOpenAudit(client.case_id)}>
            Audit trail
          </button>
          <button type="button" className="btn btn-ghost" style={{ justifyContent: "flex-start", paddingLeft: 0 }} onClick={onBack}>
            Back to Onboarded
          </button>
        </div>
      </div>

      <div className="ds-page" style={{ flex: 1 }}>
        <div className="ds-page-header">
          <div>
            <p className="card-kicker">
              {client.client_id} · {client.case_id} · {client.registration_id} · {client.jurisdiction ?? "—"}
            </p>
            <h1>{client.company_name ?? client.client_id}</h1>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button type="button" className="btn btn-secondary" onClick={() => downloadJson(`${client.client_id}.json`, client)}>
              Export record
            </button>
            <button type="button" className="btn btn-secondary">Start a review</button>
          </div>
        </div>

        <div className="ds-two-col">
          <div style={{ flex: 1 }}>
            <h4>Corporate particulars</h4>
            <div style={{ marginBottom: 20 }}>
              <div className="kv-row"><span className="kv-label">Company name</span><span className="kv-value">{client.company_name ?? "—"}</span></div>
              <div className="kv-row"><span className="kv-label">{client.registration_id_label}</span><span className="kv-value">{client.registration_id}</span></div>
              <div className="kv-row"><span className="kv-label">Entity type</span><span className="kv-value">{client.entity_type ?? "—"}</span></div>
              <div className="kv-row"><span className="kv-label">Registry status</span><span className="kv-value">{client.registry_status ?? "—"}</span></div>
              <div className="kv-row"><span className="kv-label">Registration date</span><span className="kv-value">{client.registration_date ?? "—"}</span></div>
              <div className="kv-row"><span className="kv-label">Registered address</span><span className="kv-value">{client.registered_address ?? "—"}</span></div>
              <div className="kv-row"><span className="kv-label">Principal place of business</span><span className="kv-value">{client.principal_place_of_business ?? "—"}</span></div>
              <div className="kv-row"><span className="kv-label">Financial year end</span><span className="kv-value">{client.financial_year_end ?? "—"}</span></div>
              <div className="kv-row"><span className="kv-label">Tax residency</span><span className="kv-value">{client.tax_residency ?? "—"}</span></div>
            </div>

            <h4>Capital and activity</h4>
            <div style={{ marginBottom: 20 }}>
              <div className="kv-row"><span className="kv-label">Issued capital</span><span className="kv-value">{client.issued_capital ?? "—"}</span></div>
              <div className="kv-row"><span className="kv-label">Issued shares</span><span className="kv-value">{client.issued_shares ?? "—"}</span></div>
              <div className="kv-row"><span className="kv-label">Principal activity</span><span className="kv-value">{client.principal_activity ?? "—"}</span></div>
              <div className="kv-row"><span className="kv-label">Secondary activity</span><span className="kv-value">{client.secondary_activity ?? "—"}</span></div>
              <div className="kv-row"><span className="kv-label">Countries of operation</span><span className="kv-value">{client.countries_of_operation ?? "—"}</span></div>
              <div className="kv-row"><span className="kv-label">Expected annual volume</span><span className="kv-value">{client.expected_annual_volume ?? "—"}</span></div>
            </div>

            <h4>Directors</h4>
            <div className="table-card" style={{ marginBottom: 20 }}>
              <table className="table">
                <thead>
                  <tr><th>Name</th><th>Identification</th><th>Date of birth</th><th>Appointed</th><th>Source</th></tr>
                </thead>
                <tbody>
                  {client.directors.map((director) => (
                    <tr key={director.name}>
                      <td>{director.name}</td>
                      <td>{director.identification}</td>
                      <td>{director.date_of_birth ?? "—"}</td>
                      <td>{director.appointed}</td>
                      <td className="src2">{director.source}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <h4>Beneficial owners above 25%</h4>
            <div className="table-card" style={{ marginBottom: 20 }}>
              <table className="table">
                <thead>
                  <tr><th>Owner</th><th>Holding</th><th>Type</th><th>Path</th><th>Source</th></tr>
                </thead>
                <tbody>
                  {client.beneficial_owners.map((owner) => (
                    <tr key={owner.owner}>
                      <td>{owner.owner}</td>
                      <td>{owner.holding}</td>
                      <td>{owner.type}</td>
                      <td>{owner.path}</td>
                      <td>{owner.source}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <h4>Relationship</h4>
            <div>
              <div className="kv-row"><span className="kv-label">Purpose</span><span className="kv-value">{client.relationship.purpose ?? "—"}</span></div>
              <div className="kv-row"><span className="kv-label">Source of funds</span><span className="kv-value">{client.relationship.source_of_funds ?? "—"}</span></div>
              <div className="kv-row"><span className="kv-label">Primary contact</span><span className="kv-value">{client.relationship.primary_contact ?? "—"}</span></div>
              <div className="kv-row"><span className="kv-label">Contact email</span><span className="kv-value">{client.relationship.contact_email ?? "—"}</span></div>
              <div className="kv-row"><span className="kv-label">Onboarded by</span><span className="kv-value">{client.relationship.onboarded_by ?? "—"}</span></div>
            </div>
          </div>

          <div style={{ width: 352 }}>
            <h4>Onboarding record</h4>
            <div className="table-card" style={{ marginBottom: 12 }}>
              <table className="table">
                <thead>
                  <tr><th>Stage</th><th>Method</th><th>Cleared</th></tr>
                </thead>
                <tbody>
                  {client.onboarding_record.map((row) => (
                    <tr key={row.stage}>
                      <td>{row.stage}</td>
                      <td>{row.method}</td>
                      <td>{row.cleared_at}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{ marginBottom: 20 }}>
              <div className="kv-row"><span className="kv-label">Loops</span><span className="kv-value">{client.loops_count}</span></div>
              <div className="kv-row"><span className="kv-label">Human touches</span><span className="kv-value">{client.human_touches}</span></div>
              <div className="kv-row">
                <span className="kv-label">Elapsed</span>
                <span className="kv-value">{client.elapsed_time_ms === null ? "—" : `${Math.round(client.elapsed_time_ms / 86_400_000)} day(s)`}</span>
              </div>
            </div>

            <h4>Check results at completion</h4>
            <div className="table-card" style={{ marginBottom: 20 }}>
              <table className="table">
                <thead>
                  <tr><th>Check</th><th>Outcome</th></tr>
                </thead>
                <tbody>
                  {client.check_results.map((result) => (
                    <tr key={result.check}>
                      <td>{result.check}</td>
                      <td><span className="tag tag-accent">{result.outcome}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <h4>Since onboarding</h4>
            <div>
              {client.since_onboarding.map((event, index) => (
                <div className="kv-row" key={`${event.date}-${index}`}>
                  <span className="kv-label">{event.date}</span>
                  <span className="kv-value">{event.event}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
