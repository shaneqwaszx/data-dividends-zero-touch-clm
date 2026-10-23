import { formatRegistryTimestamp, registryReuseDescription, registryTimestampIsUsable } from "../shared";
import type { RegistryAcquisition, RegistryEvidenceBinding, SimulationProfile } from "../types";

/** Safe subsets of the same retained evidence; the caller owns disclosure placement. */
export default function RegistryProvenancePanel({ acquisition, binding, entityType, providerMode, part = "all" }: {
  acquisition?: RegistryAcquisition | null;
  binding?: RegistryEvidenceBinding | null;
  entityType?: string | null;
  providerMode?: SimulationProfile["registry_provider_mode"];
  part?: "all" | "main" | "more" | "technical";
}) {
  const identity = acquisition?.operation_results.find(result => result.operation === "ENTITY_PROFILE");
  const ownership = acquisition?.operation_results.find(result => result.operation === "OWNERSHIP_PARTIES");
  const partnershipUnsupported = ownership?.status === "UNSUPPORTED" && entityType === "PARTNERSHIP"
    && ["API_MARKETPLACE_MOCK", "API_MARKETPLACE_PROTOCOL_TEST"].includes(providerMode ?? "");
  const timestamps = [acquisition?.retrieved_at, binding?.bound_to_case_at, binding?.expires_at,
    ...(acquisition?.operation_results.filter(result => result.provenance).map(result => result.provenance!.retrieved_at) ?? [])];
  const main = <>
    {acquisition ? <>
      <dl aria-label="Registry evidence availability">
        <div><dt>Identity</dt><dd>{identity?.status === "COMPLETE" ? "Identity retrieved" : `Registry identity: ${identity?.status ?? "not available"}`}</dd></div>
        <div><dt>Ownership</dt><dd>{ownership?.status === "EMPTY" ? "Ownership unavailable from current registry evidence"
          : ownership?.status === "COMPLETE" ? `${ownership.record_count} ownership record(s) retrieved`
            : ownership?.status === "FAILED" ? "Ownership retrieval failed"
              : ownership?.status === "UNSUPPORTED" ? "Ownership retrieval is unsupported by this registry route"
                : ownership?.status === "NOT_ATTEMPTED" ? "Ownership retrieval was not attempted" : "Registry ownership status is not available"}</dd></div>
      </dl>
      <p>Retained identity source: {identity?.provenance ? `${identity.provenance.provider} · ${identity.provenance.environment}` : "Not recorded"}.</p>
      {partnershipUnsupported && <p className="control-help">Registry identity retrieved. The available official Mock company-shareholder operation is not an authoritative partnership-ownership source. Reviewed supplementary ownership evidence is required.</p>}
    </> : <p className="text-muted">Registry acquisition provenance is not available.</p>}
    {binding ? <>
      {binding.synthetic_seed_namespace === "LOCAL_SYNTHETIC_UAT_V1" && <p role="note">Local Synthetic Seed · LOCAL PROJECT SYNTHETIC MOCK · LOCAL_SYNTHETIC_UAT_V1. Original local seed evidence; configured provider is unchanged.</p>}
      <div className="kv-row"><span className="kv-label">Case use</span><span className="kv-value">{binding.disposition === "CACHE_HIT" ? registryReuseDescription(acquisition, binding) : "Original provider fetch"}</span></div>
      <p className="control-help">Provisional Mock POC policy recorded when this evidence was bound. This is not a current validity assessment or an ACRA validity guarantee.</p>
    </> : <div className="ds-banner" role="note"><strong>Case evidence binding not recorded.</strong><span>Acquisition disposition, case-use time, retained freshness policy, and validity-at-use are unknown. This does not indicate a cache miss, disabled cache, provider fetch, freshness, or current validity.</span></div>}
    {(acquisition || binding) && timestamps.some(value => !registryTimestampIsUsable(value)) && <p className="control-help">One or more registry timestamps are missing or invalid. Valid-at-use timestamps are unavailable; freshness and current validity cannot be inferred.</p>}
  </>;
  const more = <>
    {acquisition && <>
      <div className="kv-row"><span className="kv-label">Acquisition status</span><span className="kv-value">{acquisition.status}</span></div>
      <div className="kv-row"><span className="kv-label">Acquisition retrieved at</span><span className="kv-value">{formatRegistryTimestamp(acquisition.retrieved_at)}</span></div>
    </>}
    {binding && <div aria-label="Registry case-use times">
      <div className="kv-row"><span className="kv-label">Bound to this case at</span><span className="kv-value">{formatRegistryTimestamp(binding.bound_to_case_at)}</span></div>
      <div className="kv-row"><span className="kv-label">Valid-at-use expiry</span><span className="kv-value">{formatRegistryTimestamp(binding.expires_at)}</span></div>
    </div>}
  </>;
  const technical = <>
    {acquisition && <>
      <ul aria-label="Original registry operations">{acquisition.operation_results.map(result => <li key={result.operation}>
        <strong>{result.operation}</strong>: {result.status} · {result.record_count} record(s)
        {result.status === "UNSUPPORTED" && " · Connector capability not implemented; no provider call occurred. Case evidence completeness is evaluated separately."}
        {result.provenance && <> · {result.provenance.provider} · {result.provenance.environment} · retrieved {formatRegistryTimestamp(result.provenance.retrieved_at)} · reference {result.provenance.evidence_reference}</>}
        {result.error && <> · {result.error.code}: {result.error.message}</>}
      </li>)}</ul>
      {acquisition.issues.map(issue => <p key={issue.code}><strong>{issue.code}</strong> · {issue.message}</p>)}
    </>}
    {binding && <div aria-label="Case evidence binding">
      <div className="kv-row"><span className="kv-label">Disposition</span><span className="kv-value">{binding.disposition}</span></div>
      <div className="kv-row"><span className="kv-label">Policy</span><span className="kv-value">{binding.freshness_policy_id} version {binding.freshness_policy_version}</span></div>
      <div className="kv-row"><span className="kv-label">Retained duration</span><span className="kv-value">{binding.freshness_duration_seconds} seconds</span></div>
      <div className="kv-row"><span className="kv-label">Freshness comparator</span><span className="kv-value">{binding.freshness_comparator}</span></div>
      <p className="control-help">Provisional Mock POC policy recorded when this evidence was bound. This is not a current validity assessment or an ACRA validity guarantee.</p>
    </div>}
  </>;
  const audit = <dl>
    {acquisition && <>
      <div><dt>Acquisition retrieved at — original ISO UTC</dt><dd><AuditTime value={acquisition.retrieved_at} /></dd></div>
      {acquisition.operation_results.filter(result => result.provenance).map(result => <div key={result.operation}><dt>{result.operation} retrieved at — original ISO UTC</dt><dd><AuditTime value={result.provenance!.retrieved_at} /></dd></div>)}
    </>}
    {binding && <>
      <div><dt>Bound to this case at — original ISO UTC</dt><dd><AuditTime value={binding.bound_to_case_at} /></dd></div>
      <div><dt>Valid-at-use expiry — original ISO UTC</dt><dd><AuditTime value={binding.expires_at} /></dd></div>
    </>}
  </dl>;
  const headingId = part === "all" || part === "main" ? "registry-provenance-heading" : `registry-provenance-${part}-heading`;
  return <section className="evidence-section-block registry-provenance" aria-labelledby={headingId}>
    <p className="card-kicker">Case-bound registry evidence</p>
    <h4 id={headingId}>{part === "all" || part === "main" ? "Registry provenance" : part === "more" ? "Registry acquisition and case use" : "Registry audit evidence"}</h4>
    {(part === "all" || part === "main") && main}
    {(part === "all" || part === "more") && more}
    {(part === "all" || part === "technical") && technical}
    {part === "technical" && audit}
    {part === "all" && (acquisition || binding) && <details className="evidence-details"><summary>Technical timestamps (original ISO UTC)</summary>{audit}</details>}
  </section>;
}

/** Audit evidence shows the exact retained value (readable SGT times are in the Main and More views). */
function AuditTime({ value }: { value: string | null | undefined }) {
  if (!value) return <>Not recorded</>;
  return registryTimestampIsUsable(value) ? <time dateTime={value}>{value}</time> : <>{value}</>;
}
