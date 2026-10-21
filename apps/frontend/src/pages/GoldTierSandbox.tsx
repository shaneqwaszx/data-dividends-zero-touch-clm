import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  ApiError,
  dryRunGoldTierSandbox,
  searchGoldTierSandbox,
} from "../api";
import { goldTierSandboxStatusQueryOptions } from "../goldTierSandboxQueries";
import { formatTimestamp } from "../shared";
import type {
  AuthenticatedProfile,
  GoldTierSandboxDryRunInput,
  GoldTierSandboxSearchInput,
  GoldTierSandboxSearchResult,
  GoldTierSandboxTestValues,
} from "../types";

// Optional backend diagnostics read defensively until the shared contract type adopts them.
type SandboxSearchDiagnostics = GoldTierSandboxSearchResult & {
  error_code?: unknown;
  upstream_status?: unknown;
  correlation_id?: unknown;
};

const NO_EXISTENCE_CONCLUSION = "No conclusion can be drawn about whether the customer exists.";

const EMPTY_SEARCH: Required<GoldTierSandboxSearchInput> = {
  goldtier_id: "",
  legal_name: "",
  country_of_incorporation: "",
  group_company_name: "",
};

const EMPTY_TEST_VALUES: Required<GoldTierSandboxTestValues> = {
  kyc_customer_type: "",
  client_segment: "",
  customer_external_system: "DSD",
  registration_type: "ACRA",
  policy: "Singapore",
  booking_entity: "ANZBGL (Singapore Branch)",
  account_entity_type: "",
  product_type: "",
};

const TEST_VALUE_LABELS: Array<[keyof GoldTierSandboxTestValues, string]> = [
  ["kyc_customer_type", "KYC customer type"],
  ["client_segment", "Client segment"],
  ["customer_external_system", "Customer external system"],
  ["registration_type", "Registration type"],
  ["policy", "Policy"],
  ["booking_entity", "Booking entity"],
  ["account_entity_type", "Account entity type"],
  ["product_type", "Product type"],
];

function compactValues<T extends Record<string, string>>(values: T): Partial<T> {
  return Object.fromEntries(
    Object.entries(values)
      .map(([key, value]) => [key, value.trim()])
      .filter(([, value]) => value.length > 0),
  ) as Partial<T>;
}

function safeError(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

function readable(value: string): string {
  return value.replaceAll("_", " ");
}

function safeText(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

function safeStatus(value: unknown): number | null {
  return typeof value === "number" && Number.isInteger(value) ? value : null;
}

function searchFailureExplanation(upstreamStatus: number | null): string {
  if (upstreamStatus === 400) return "GoldTier rejected the Search request (HTTP 400).";
  if (upstreamStatus !== null && upstreamStatus >= 500) {
    return `The GoldTier Search service failed or was unavailable (HTTP ${upstreamStatus}).`;
  }
  return "The GoldTier Search did not complete.";
}

function retrievalSummary(result: GoldTierSandboxSearchResult): string {
  if (result.status === "NO_MATCH") return "No match — the provider Search completed and returned no candidate.";
  if (result.status === "MATCH_FOUND") return "Candidate retrieved — the provider Search returned one candidate.";
  if (result.status === "MULTIPLE_MATCHES") return "Candidates retrieved — the provider Search returned multiple candidates.";
  return readable(result.status);
}

function resolutionSummary(result: GoldTierSandboxSearchResult): string {
  if (result.status === "FAILURE") return "Not assessed — the provider Search did not succeed.";
  if (result.entity_resolution === "NOT_ASSESSED") {
    return result.candidates.length > 0
      ? "Not assessed — the Search criteria and returned candidate gave the resolver no identity feature it could compare. A retrieved GoldTier ID is not a verified identity match."
      : "Not assessed.";
  }
  return `${readable(result.entity_resolution)} — advisory only; not identity authority or existing-customer reuse approval.`;
}

export default function GoldTierSandbox({ actor }: { actor: AuthenticatedProfile }) {
  const [searchValues, setSearchValues] = useState(EMPTY_SEARCH);
  const [testValues, setTestValues] = useState(EMPTY_TEST_VALUES);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [dryRunValidationError, setDryRunValidationError] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const statusOptions = goldTierSandboxStatusQueryOptions(actor.user_id);
  const statusQuery = useQuery(statusOptions);
  const searchMutation = useMutation({
    mutationFn: searchGoldTierSandbox,
    retry: false,
    onSettled: () => queryClient.invalidateQueries({ queryKey: statusOptions.queryKey, exact: true }),
  });
  const dryRunMutation = useMutation({
    mutationFn: dryRunGoldTierSandbox,
    retry: false,
    onSettled: () => queryClient.invalidateQueries({ queryKey: statusOptions.queryKey, exact: true }),
  });

  function searchInput(): GoldTierSandboxSearchInput | null {
    const compact = compactValues(searchValues) as GoldTierSandboxSearchInput;
    return Object.keys(compact).length > 0 ? compact : null;
  }

  function updateSearch<K extends keyof typeof searchValues>(
    key: K,
    value: (typeof searchValues)[K],
  ): void {
    setSearchValues((current) => ({ ...current, [key]: value }));
    setValidationError(null);
    setDryRunValidationError(null);
    searchMutation.reset();
    dryRunMutation.reset();
  }

  function runSearch(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    const input = searchInput();
    if (!input) {
      setValidationError("Enter at least one bounded search criterion.");
      return;
    }
    if (!statusQuery.data?.configured) {
      setValidationError("Sandbox is unavailable in the effective backend configuration.");
      return;
    }
    setValidationError(null);
    searchMutation.mutate(input);
  }

  function runDryRun(): void {
    const search = searchInput();
    if (!search) {
      setDryRunValidationError("Enter at least one bounded search criterion before validating a preview.");
      return;
    }
    const compactTestValues = compactValues(testValues);
    if (!testValues.kyc_customer_type || !testValues.client_segment) {
      setDryRunValidationError("Select a KYC customer type and Client Segment before validating a preview.");
      return;
    }
    setDryRunValidationError(null);
    dryRunMutation.mutate({
      search,
      test_values: compactTestValues as GoldTierSandboxTestValues,
    } satisfies GoldTierSandboxDryRunInput);
  }

  const status = statusQuery.data;
  const writeBlocker = status?.blocker
    ?? "Guarded synthetic write execution is not enabled in this frontend slice.";
  const searchResult = searchMutation.data as SandboxSearchDiagnostics | undefined;
  const searchFailed = searchResult?.status === "FAILURE";
  const searchErrorCode = searchMutation.error instanceof ApiError ? searchMutation.error.code : null;
  const searchErrorDetail: Record<string, unknown> | null = searchMutation.error instanceof ApiError
    ? { ...searchMutation.error.detail }
    : null;
  const searchErrorCorrelation = safeText(searchErrorDetail?.correlation_id);
  const searchErrorStatus = safeStatus(searchErrorDetail?.upstream_status);
  const searchErrorElapsed = safeStatus(searchErrorDetail?.elapsed_ms);

  return (
    <section className="ds-root ds-page" aria-labelledby="goldtier-sandbox-heading">
      <div className="ds-page-header">
        <div>
          <p className="card-kicker">HR provider tooling</p>
          <h1 id="goldtier-sandbox-heading">GoldTier Sandbox console</h1>
          <p className="text-muted">
            Read-only diagnostics and request validation for synthetic Sandbox test data.
            This console does not prove Live interoperability or authorize customer writes.
          </p>
        </div>
      </div>

      <section className="card" aria-labelledby="sandbox-status-heading">
        <p className="card-kicker">Safe connection projection</p>
        <h2 id="sandbox-status-heading">Connection status</h2>
        {statusQuery.isPending && <p className="text-muted">Loading provider status…</p>}
        {statusQuery.isError && (
          <div className="ds-banner ds-banner-warn" role="alert">
            {safeError(statusQuery.error, "GoldTier Sandbox status is unavailable.")}
          </div>
        )}
        {status && (
          <dl>
            <div><dt>Configured</dt><dd>{status.configured ? "Yes" : "No"}</dd></div>
            <div><dt>Mode / classification</dt><dd>{status.mode} / {status.classification}</dd></div>
            <div><dt>Safe host identity</dt><dd>{status.safe_host ?? "Not disclosed"}</dd></div>
            <div><dt>Writes enabled by configuration</dt><dd>{status.writes_enabled ? "Yes" : "No"}</dd></div>
            <div><dt>Timeout</dt><dd>{status.timeout_seconds}s</dd></div>
            <div><dt>Maximum response body</dt><dd>{status.max_response_bytes.toLocaleString()} bytes</dd></div>
            <div><dt>Last diagnostic</dt><dd>{status.last_diagnostic_at ? formatTimestamp(status.last_diagnostic_at) : "Not run"}</dd></div>
            <div><dt>Vocabulary</dt><dd>{status.vocabulary_version}</dd></div>
          </dl>
        )}
        {status && !status.configured && <p role="status" className="control-help">Sandbox is unavailable in the effective backend configuration. No connection was attempted. The backend owner should verify GOLDTIER_CONNECTOR_MODE, GOLDTIER_SANDBOX_BASE_URL, GOLDTIER_SANDBOX_ENVIRONMENT, GOLDTIER_SANDBOX_USER_ID and GOLDTIER_SANDBOX_ALLOW_WRITES. Configuration values are not displayed here.</p>}
        {status && (
          <div className="provider-readiness" aria-label="Backend-authored GoldTier operation readiness">
            <article className="ds-banner">
              <strong>Customer operations</strong>
              <span>{readable(status.customer_operations)} — Search and offline request validation remain independently available; customer writes stay case-ledger controlled.</span>
            </article>
            <article className="ds-banner ds-banner-warn">
              <strong>Related-party operations</strong>
              <span>Blocked — integration contract incomplete.</span>
              <span>GoldTier related-party Policy and Amend require an existing childId, but the supplied contract does not define how that identity is created or retrieved.</span>
              <span>Required before enabling: {readable(status.required_authority)} for the child-ID lifecycle and relationship semantics.</span>
              <p><strong>What is missing:</strong> an authoritative way to search, retrieve or create the child party and bind it to the parent customer.</p>
              <p><strong>Why the system cannot safely continue:</strong> a parent ID or a locally generated ID cannot replace a provider-issued childId. Related-party network calls remain blocked.</p>
              <p><strong>What the sponsor/API owner must provide:</strong> childId meaning; creation and retrieval endpoints; identity evidence for reuse; parent/child binding and relationship vocabulary; multiple-parent rules; Policy and Amend retry/idempotency semantics; and whether Amend RP goldTierId identifies the child.</p>
              <p><strong>Future lifecycle once confirmed:</strong> search/retrieve an existing child identity or perform confirmed creation → retain the durable provider-issued childId → bind the confirmed parent/child relationship → ledger-controlled Policy and Amend.</p>
              <details>
                <summary>Technical details</summary>
                <code>{status.blocker_code}</code>
              </details>
            </article>
          </div>
        )}
        {status && status.timeline.length > 0 && (
          <div className="table-scroll" tabIndex={0} aria-label="Safe Sandbox operation timeline">
            <table className="table">
              <thead><tr><th>Time</th><th>Operation</th><th>Outcome</th><th>Code</th></tr></thead>
              <tbody>
                {status.timeline.map((event) => (
                  <tr key={event.event_id}>
                    <td>{formatTimestamp(event.occurred_at)}</td>
                    <td>{readable(event.action)}</td>
                    <td>{readable(event.outcome)}</td>
                    <td>{event.code}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="control-help">Credentials, authorization headers, raw endpoints, and provider payloads are never displayed.</p>
      </section>

      <details className="card">
        <summary>How to test this console</summary>
        <ol>
          <li>Enter at least one Search criterion.</li>
          <li>Run read-only Search.</li>
          <li>Inspect candidates and any missing identity evidence.</li>
          <li>Choose KYC customer type and client segment. Supply legal name and country before validating a preview.</li>
          <li>Inspect the accepted POC constants and ephemeral SANDBOX_TEST_ONLY inputs.</li>
          <li>Select Validate request preview.</li>
          <li>Inspect Search, Shell, Policy and Amend validation. The preview uses synthetic test identity and address data.</li>
          <li>No provider mutation occurred. Dispatch-valid preview is offline validation, not provider acceptance.</li>
        </ol>
      </details>
      <form className="card" onSubmit={runSearch} aria-labelledby="sandbox-search-heading">
        <p className="card-kicker">Read-only provider operation</p>
        <h2 id="sandbox-search-heading">Customer search</h2>
        <p className="text-muted">At least one criterion is required. Blank customer enumeration is blocked.</p>
        <div className="ds-two-col">
          <div className="field">
            <label htmlFor="sandbox-goldtier-id">GoldTier ID</label>
            <input id="sandbox-goldtier-id" className="input" maxLength={96} value={searchValues.goldtier_id} onChange={(event) => updateSearch("goldtier_id", event.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="sandbox-legal-name">Legal name</label>
            <input id="sandbox-legal-name" className="input" maxLength={240} value={searchValues.legal_name} onChange={(event) => updateSearch("legal_name", event.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="sandbox-country">Country</label>
            <input id="sandbox-country" className="input" maxLength={2} value={searchValues.country_of_incorporation} onChange={(event) => updateSearch("country_of_incorporation", event.target.value.toUpperCase())} />
          </div>
          <div className="field">
            <label htmlFor="sandbox-group-company">Group-company name</label>
            <input id="sandbox-group-company" className="input" maxLength={240} value={searchValues.group_company_name} onChange={(event) => updateSearch("group_company_name", event.target.value)} />
          </div>
        </div>
        {validationError && <div className="ds-banner ds-banner-warn" role="alert">{validationError}</div>}
        <button type="submit" className="btn btn-primary" disabled={searchMutation.isPending || !status?.configured}>
          {searchMutation.isPending ? "Searching…" : "Search Sandbox"}
        </button>
        {searchMutation.isError && (
          <div className="ds-banner ds-banner-warn" role="alert">
            <span>{safeError(searchMutation.error, "GoldTier Sandbox search could not be completed.")}</span>
            <span> {NO_EXISTENCE_CONCLUSION}</span>
            {(searchErrorCode || searchErrorStatus !== null || searchErrorElapsed !== null || searchErrorCorrelation) && (
              <span className="control-help">
                {searchErrorCode && <> Code: <code>{searchErrorCode}</code></>}
                {searchErrorStatus !== null && <> · Provider HTTP status: {searchErrorStatus}</>}
                {searchErrorElapsed !== null && <> · Elapsed: {searchErrorElapsed.toLocaleString()} ms</>}
                {searchErrorCorrelation && <> · Correlation ID: <code>{searchErrorCorrelation}</code></>}
              </span>
            )}
          </div>
        )}
        {searchResult && (
          <div aria-live="polite">
            {searchFailed ? (
              <div className="ds-banner ds-banner-warn" role="alert">
                <strong>Search failed</strong>
                <span> {searchFailureExplanation(safeStatus(searchResult.upstream_status))} {NO_EXISTENCE_CONCLUSION}</span>
              </div>
            ) : (
              <p><strong>{retrievalSummary(searchResult)}</strong> · {searchResult.count} candidate(s)</p>
            )}
            <p className="control-help">Advisory identity resolution: {resolutionSummary(searchResult)}</p>
            <dl aria-label="Safe Search diagnostics">
              <div><dt>Search outcome</dt><dd>{readable(searchResult.status)}</dd></div>
              {safeText(searchResult.error_code) && (
                <div><dt>Trusted error code</dt><dd><code>{safeText(searchResult.error_code)}</code></dd></div>
              )}
              {safeStatus(searchResult.upstream_status) !== null && (
                <div><dt>Provider HTTP status</dt><dd>{safeStatus(searchResult.upstream_status)}</dd></div>
              )}
              <div><dt>Elapsed</dt><dd>{searchResult.elapsed_ms.toLocaleString()} ms</dd></div>
              {safeText(searchResult.correlation_id) && (
                <div><dt>Correlation ID</dt><dd><code>{safeText(searchResult.correlation_id)}</code></dd></div>
              )}
            </dl>
            {searchResult.candidates.length > 0 && (
              <div className="table-scroll" tabIndex={0}>
                <table className="table">
                  <thead><tr><th>GoldTier ID</th><th>Legal name</th><th>Registration</th><th>Country</th><th>Legal form</th><th>Registered address</th></tr></thead>
                  <tbody>
                    {searchResult.candidates.map((candidate) => (
                      <tr key={candidate.party_id}>
                        <td>{candidate.party_id}</td>
                        <td>{candidate.legal_name ?? "—"}</td>
                        <td>{candidate.registration_number ?? "—"}</td>
                        <td>{candidate.country ?? "—"}</td>
                        <td>{candidate.legal_form ?? "—"}</td>
                        <td>{candidate.registered_address ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </form>

      <section className="card" aria-labelledby="sandbox-preview-heading">
        <p className="card-kicker">No network mutation</p>
        <h2 id="sandbox-preview-heading">Request preview and dry run</h2>
        <p className="text-muted">
          Values entered here are ephemeral <strong>SANDBOX_TEST_ONLY</strong> inputs. They do not update the global policy catalogue.
        </p>
        <div className="ds-two-col">
          {TEST_VALUE_LABELS.map(([key, label]) => (
            <div className="field" key={key}>
              <label htmlFor={`sandbox-${key}`}>{label}</label>
              {key === "kyc_customer_type" || key === "client_segment" ? (
                <select
                  id={`sandbox-${key}`}
                  className="input"
                  required
                  value={testValues[key]}
                  onChange={(event) => {
                    setTestValues((current) => ({ ...current, [key]: event.target.value }));
                    setDryRunValidationError(null);
                    dryRunMutation.reset();
                  }}
                >
                  <option value="">Select a sponsor-documented value</option>
                  {(key === "kyc_customer_type"
                    ? status?.kyc_customer_types ?? []
                    : status?.client_segments ?? []).map((value) => (
                    <option key={value} value={value}>{value}</option>
                  ))}
                </select>
              ) : (
                <input
                  id={`sandbox-${key}`}
                  className="input"
                  maxLength={160}
                  readOnly={!["account_entity_type", "product_type"].includes(key)}
                  value={testValues[key]}
                  onChange={(event) => {
                    setTestValues((current) => ({ ...current, [key]: event.target.value }));
                    setDryRunValidationError(null);
                    dryRunMutation.reset();
                  }}
                />
              )}
            </div>
          ))}
        </div>
        {dryRunValidationError && <div className="ds-banner ds-banner-warn" role="alert">{dryRunValidationError}</div>}
        <button type="button" className="btn btn-secondary" disabled={dryRunMutation.isPending} onClick={runDryRun}>
          {dryRunMutation.isPending ? "Validating…" : "Validate request preview"}
        </button>
        {dryRunMutation.isError && (
          <div className="ds-banner ds-banner-warn" role="alert">
            {safeError(dryRunMutation.error, "GoldTier Sandbox request preview is unavailable.")}
          </div>
        )}
        {dryRunMutation.data && (
          <div aria-live="polite">
            <p><strong>{dryRunMutation.data.dispatch_ready ? "Dispatch-valid preview" : "Dispatch blocked"}</strong></p>
            {dryRunMutation.data.blocker && <p className="control-help">{dryRunMutation.data.blocker}</p>}
            {dryRunMutation.data.operations.map((operation) => (
              <article className="submission-plan" key={operation.operation}>
                <h3>{readable(operation.operation)} · {readable(operation.validation)}</h3>
                <dl>
                  {operation.fields.map((field) => (
                    <div key={field.target_field}>
                      <dt>{field.target_field}</dt>
                      <dd>
                        {field.missing ? "Missing" : field.value ?? "—"}
                        {" · "}{readable(field.provenance)} · {readable(field.authority)} · {readable(field.validation)}
                      </dd>
                    </div>
                  ))}
                </dl>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="card" aria-labelledby="sandbox-write-heading">
        <p className="card-kicker">Guarded synthetic operation</p>
        <h2 id="sandbox-write-heading">Synthetic write test</h2>
        <button type="button" className="btn btn-primary" disabled aria-describedby="sandbox-write-blocker">
          Run guarded synthetic write
        </button>
        <p id="sandbox-write-blocker" className="control-help">Backend blocker: {writeBlocker}</p>
        <p className="control-help">No write request is sent from this control. Search and dry-run results above are the complete safe operation timeline for this slice.</p>
      </section>
    </section>
  );
}
