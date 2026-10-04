import { useEffect, useRef, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, fetchAcraDiagnosticStatus, lookupAcraDiagnostic } from "../api";
import { formatTimestamp } from "../shared";
import type {
  AcraDiagnosticOperation,
  AcraDiagnosticReceipt,
  AcraDiagnosticResult,
  AuthenticatedProfile,
} from "../types";

export const acraDiagnosticQueryKeys = {
  root: (userId: string) => ["auth", userId, "provider-sandbox", "acra"] as const,
  status: (userId: string) => ["auth", userId, "provider-sandbox", "acra", "status"] as const,
};

export function acraDiagnosticStatusQueryOptions(userId: string) {
  return {
    queryKey: acraDiagnosticQueryKeys.status(userId),
    queryFn: ({ signal }: { signal: AbortSignal }) => fetchAcraDiagnosticStatus(signal),
    retry: false as const,
  };
}

function readable(value: string): string {
  return value.replaceAll("_", " ").toLowerCase().replace(/^./, (letter) => letter.toUpperCase());
}

function safeError(error: unknown): string {
  return error instanceof ApiError ? error.message : "The ACRA diagnostic could not be completed.";
}

export function sanitizedReceiptText(receipt: AcraDiagnosticReceipt): string {
  return [
    `Diagnostic: ${receipt.diagnostic_id}`,
    `Provider: ${receipt.provider}`,
    `Classification: ${receipt.classification}`,
    `Operation: ${receipt.operation}`,
    `Request reference: ${receipt.request_reference}`,
    `Started: ${receipt.started_at}`,
    `Completed: ${receipt.completed_at}`,
    `Outcome: ${receipt.outcome}`,
    `Code: ${receipt.code}`,
    `Provider called: ${receipt.provider_called ? "Yes" : "No"}`,
    `Record count: ${receipt.record_count}`,
  ].join("\n");
}

export function AcraDiagnosticOutcomePanel({ result }: { result: AcraDiagnosticResult }) {
  const explanation: Record<AcraDiagnosticResult["outcome"], string> = {
    COMPLETE: "The supported lookup completed with retained records.",
    EMPTY: "The lookup completed, but the supported collection was empty.",
    PARTIAL: "The lookup returned safe data with identified completeness limitations.",
    NOT_FOUND: "No matching entity profile was returned for the requested UEN.",
    FAILED: "The provider lookup failed safely; no raw provider response is shown.",
    UNSUPPORTED: "This operation is not implemented by the configured connector.",
    INVALID_REQUEST: "The request was rejected before a provider lookup.",
    CANCELLED: "The request was cancelled before provider dispatch.",
    RATE_LIMITED: "A local diagnostic safety bound prevented provider dispatch.",
  };
  return (
    <section className={`acra-result acra-result--${result.outcome.toLowerCase()}`} aria-labelledby="acra-result-heading">
      <p className="card-kicker">Safe diagnostic result</p>
      <h2 id="acra-result-heading">Outcome: {readable(result.outcome)}</h2>
      <p>{explanation[result.outcome]}</p>
      <p>{result.message}</p>
      {result.missing_fields.length > 0 && <p><strong>Missing supported fields:</strong> {result.missing_fields.map(readable).join(", ")}</p>}
      {result.company && (
        <dl className="acra-detail-list">
          <div><dt>Legal name</dt><dd>{result.company.legal_name}</dd></div>
          <div><dt>UEN</dt><dd>{result.company.uen}</dd></div>
          <div><dt>Country / entity type</dt><dd>{result.company.country_code} · {result.company.entity_type}</dd></div>
          <div><dt>Status</dt><dd>{result.company.entity_status ?? "Not provided"}</dd></div>
          <div><dt>Registration date</dt><dd>{result.company.registration_date ?? "Not provided"}</dd></div>
          <div><dt>Source</dt><dd>{result.company.source_environment} · retrieved {formatTimestamp(result.company.retrieved_at)}</dd></div>
          <div><dt>Registered address</dt><dd>{result.company.registered_address ? [result.company.registered_address.address_line_1, result.company.registered_address.address_line_2, result.company.registered_address.postal_code, result.company.registered_address.country_code].filter(Boolean).join(", ") : "Not provided"}</dd></div>
        </dl>
      )}
      {result.officers.length > 0 && <div className="table-card"><table className="table"><caption>Officer summary</caption><thead><tr><th>Name</th><th>Role</th><th>Appointment</th><th>Country</th></tr></thead><tbody>{result.officers.map((officer) => <tr key={officer.officer_id}><td>{officer.name}</td><td>{officer.role}</td><td>{officer.appointment_date ?? "Not provided"}</td><td>{officer.country ?? "Not provided"}</td></tr>)}</tbody></table></div>}
      {result.shareholders.length > 0 && <div className="table-card"><table className="table"><caption>Shareholder summary</caption><thead><tr><th>Name</th><th>Type</th><th>Country</th><th>Ownership</th></tr></thead><tbody>{result.shareholders.map((shareholder) => <tr key={shareholder.party_id}><td>{shareholder.name}</td><td>{readable(shareholder.party_type)}</td><td>{shareholder.country ?? "Not provided"}</td><td>{shareholder.ownership_percentage ?? "Not provided"}</td></tr>)}</tbody></table></div>}
      <details className="acra-receipt">
        <summary>Sanitized diagnostic receipt</summary>
        <pre>{sanitizedReceiptText(result.receipt)}</pre>
        <button type="button" className="btn btn-secondary" onClick={() => void navigator.clipboard?.writeText(sanitizedReceiptText(result.receipt))}>Copy sanitized receipt</button>
      </details>
    </section>
  );
}

export default function AcraDiagnostics({ actor }: { actor: AuthenticatedProfile }) {
  const queryClient = useQueryClient();
  const statusOptions = acraDiagnosticStatusQueryOptions(actor.user_id);
  const statusQuery = useQuery(statusOptions);
  const [uen, setUen] = useState("");
  const [operation, setOperation] = useState<AcraDiagnosticOperation>("ENTITY_PROFILE");
  const [sampleUen, setSampleUen] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);
  const lookupController = useRef<AbortController | null>(null);
  const lookupMutation = useMutation({
    mutationFn: (input: { uen: string; operation: AcraDiagnosticOperation }) => {
      lookupController.current?.abort();
      lookupController.current = new AbortController();
      return lookupAcraDiagnostic(input, lookupController.current.signal);
    },
    retry: false,
    onSettled: () => void queryClient.invalidateQueries({ queryKey: statusOptions.queryKey, exact: true }),
  });

  useEffect(() => () => lookupController.current?.abort(), []);

  function chooseSample(value: string): void {
    setSampleUen(value);
    const sample = statusQuery.data?.samples.find((item) => item.uen === value);
    if (!sample) return;
    setUen(sample.uen);
    setOperation(sample.operations[0] ?? "ENTITY_PROFILE");
    setValidationError(null);
    lookupMutation.reset();
  }

  function submit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    const normalized = uen.trim().toUpperCase();
    if (!/^[A-Z0-9]{9,10}$/.test(normalized)) {
      setValidationError("Enter a bounded 9- or 10-character Singapore UEN.");
      return;
    }
    setValidationError(null);
    lookupMutation.mutate({ uen: normalized, operation });
  }

  const status = statusQuery.data;
  const selectedSample = status?.samples.find((sample) => sample.uen === sampleUen);
  return (
    <section className="ds-root ds-page acra-console" aria-labelledby="acra-console-heading">
      <div className="ds-page-header"><div><p className="card-kicker">HR provider tooling · read only</p><h1 id="acra-console-heading">ACRA diagnostics</h1><p className="text-muted">Bounded provider checks only. This console does not alter onboarding cases or prove Live interoperability.</p></div></div>
      <details className="card">
        <summary>What this tab does</summary>
        <ul>
          <li>Shows safe connector configuration.</li>
          <li>Lets HR run bounded read-only provider lookups.</li>
          <li>Displays sanitized receipts.</li>
          <li>Never changes onboarding cases.</li>
          <li>Does not prove Live interoperability.</li>
        </ul>
      </details>

      {statusQuery.isPending && <p>Loading ACRA diagnostic status…</p>}
      {statusQuery.isError && <p className="ds-banner ds-banner-warn" role="alert">{safeError(statusQuery.error)}</p>}
      {status && <div className="acra-status-grid">
        <section className="card"><h2>Configuration</h2><dl className="acra-detail-list">
          <div><dt>Configured</dt><dd>{status.configuration.configured ? "Yes" : "No"}</dd></div>
          <div><dt>Provider / mode</dt><dd>{status.configuration.provider} · {status.configuration.mode}</dd></div>
          <div><dt>Classification</dt><dd>{status.configuration.classification}</dd></div>
          <div><dt>Safe host</dt><dd>{status.configuration.safe_host ?? "Not disclosed"}</dd></div>
          <div><dt>Client ID present</dt><dd>{status.configuration.client_id_present ? "Yes" : "No"}</dd></div>
          <div><dt>Secret key present</dt><dd>{status.configuration.secret_key_present ? "Yes" : "No"}</dd></div>
          <div><dt>Generic static-header auth</dt><dd>{status.configuration.mode === "api_marketplace_mock" ? "Not applicable for API Marketplace Mock" : status.configuration.mode === "mock" ? "Not applicable for local Mock" : status.configuration.generic_auth_present ? "Present" : "Not configured"}</dd></div>
          <div><dt>Timeout / response bound</dt><dd>{status.configuration.timeout_seconds}s · {status.configuration.max_response_bytes.toLocaleString()} bytes</dd></div>
        </dl></section>
        <section className="card"><h2>Connectivity</h2><p className={`tag acra-connectivity--${status.connectivity.toLowerCase()}`}>{readable(status.connectivity)}</p><p>Last actual check: {status.last_actual_check_at ? formatTimestamp(status.last_actual_check_at) : "Not checked"}</p><p className="control-help">Cancellation is reliable before dispatch. An in-flight provider request uses the configured timeout.</p></section>
        <section className="card"><h2>Connector capabilities</h2><p className="control-help">Supported operations describe this connector. Each case's evidence completeness is assessed separately in its onboarding workspace.</p><ul className="acra-coverage">{status.coverage.map((item) => <li key={item.operation}><strong>{readable(item.operation)}</strong><span className={`tag ${item.availability === "SUPPORTED" ? "tag-success" : "tag-muted"}`}>{readable(item.availability)}</span><small>{item.availability === "UNSUPPORTED" ? "Not available in current provider contract. Provider called: No (provider_called = false)." : readable(item.reason_code)}</small></li>)}</ul></section>
      </div>}

      {status && <section className="card" aria-labelledby="acra-lookup-heading"><h2 id="acra-lookup-heading">Bounded lookup</h2>
        <label htmlFor="acra-sample">Documented sample (optional)</label>
        <select id="acra-sample" value={sampleUen} onChange={(event) => chooseSample(event.target.value)}><option value="">Choose a sample to prefill</option>{status.samples.map((sample) => <option key={sample.uen} value={sample.uen}>{sample.legal_name} · {sample.uen}</option>)}</select>
        {selectedSample && <p className="control-help">{readable(selectedSample.classification)}. Limitations: {selectedSample.limitation_codes.length ? selectedSample.limitation_codes.map(readable).join(", ") : "None recorded"}. Selection prefills only; it does not run a lookup.</p>}
        <form className="acra-lookup-form" onSubmit={submit}>
          <div><label htmlFor="acra-uen">Singapore UEN</label><input id="acra-uen" className="input" value={uen} minLength={9} maxLength={10} pattern="[A-Z0-9]{9,10}" onChange={(event) => { setUen(event.target.value.toUpperCase()); setValidationError(null); lookupMutation.reset(); }} required /></div>
          <div><label htmlFor="acra-operation">Operation</label><select id="acra-operation" value={operation} onChange={(event) => { setOperation(event.target.value as AcraDiagnosticOperation); lookupMutation.reset(); }}>{status.coverage.map((item) => <option key={item.operation} value={item.operation}>{readable(item.operation)} · {readable(item.availability)}</option>)}</select></div>
          <button type="submit" className="btn btn-primary" disabled={lookupMutation.isPending}>{lookupMutation.isPending ? "Running lookup…" : "Run read-only lookup"}</button>
        </form>
        {validationError && <p className="ds-banner ds-banner-warn" role="alert">{validationError}</p>}
        {lookupMutation.isError && <p className="ds-banner ds-banner-warn" role="alert">{safeError(lookupMutation.error)}</p>}
      </section>}

      {lookupMutation.data && <AcraDiagnosticOutcomePanel result={lookupMutation.data} />}
      {status && <section className="card"><h2>Recent safe receipts</h2>{status.timeline.length === 0 ? <p>No diagnostics have been recorded in this process.</p> : <ol className="acra-timeline">{status.timeline.map((receipt) => <li key={receipt.diagnostic_id}><strong>{readable(receipt.operation)} · {readable(receipt.outcome)}</strong><span>{formatTimestamp(receipt.completed_at)} · {receipt.request_reference} · {receipt.record_count} record(s)</span></li>)}</ol>}</section>}
    </section>
  );
}
