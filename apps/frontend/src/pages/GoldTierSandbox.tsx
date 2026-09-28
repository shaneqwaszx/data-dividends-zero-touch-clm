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
  GoldTierSandboxTestValues,
} from "../types";

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
        <button type="submit" className="btn btn-primary" disabled={searchMutation.isPending}>
          {searchMutation.isPending ? "Searching…" : "Search Sandbox"}
        </button>
        {searchMutation.isError && (
          <div className="ds-banner ds-banner-warn" role="alert">
            {safeError(searchMutation.error, "GoldTier Sandbox search could not be completed.")}
          </div>
        )}
        {searchMutation.data && (
          <div aria-live="polite">
            <p><strong>{readable(searchMutation.data.status)}</strong> · {searchMutation.data.count} candidate(s) · {searchMutation.data.elapsed_ms.toLocaleString()} ms</p>
            <p className="control-help">Entity resolution: {readable(searchMutation.data.entity_resolution)}</p>
            {searchMutation.data.candidates.length > 0 && (
              <div className="table-scroll" tabIndex={0}>
                <table className="table">
                  <thead><tr><th>GoldTier ID</th><th>Legal name</th><th>Registration</th><th>Country</th><th>Legal form</th><th>Registered address</th></tr></thead>
                  <tbody>
                    {searchMutation.data.candidates.map((candidate) => (
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
