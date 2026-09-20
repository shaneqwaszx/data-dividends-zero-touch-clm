import type { RegistryAcquisition, RegistryEvidenceBinding } from "../types";

export default function RegistryProvenancePanel({
  acquisition,
  binding,
}: {
  acquisition?: RegistryAcquisition | null;
  binding?: RegistryEvidenceBinding | null;
}) {
  return (
    <section className="evidence-section-block" aria-labelledby="registry-provenance-heading">
      <p className="card-kicker">Case-bound registry evidence</p>
      <h4 id="registry-provenance-heading">Registry provenance</h4>

      {acquisition ? (
        <>
          <div className="kv-row"><span className="kv-label">Acquisition status</span><span className="kv-value">{acquisition.status}</span></div>
          <div className="kv-row"><span className="kv-label">Acquisition retrieved at</span><span className="kv-value">{acquisition.retrieved_at}</span></div>
          <ul aria-label="Original registry operations">
            {acquisition.operation_results.map((result) => (
              <li key={result.operation}>
                <strong>{result.operation}</strong>: {result.status}
                {result.provenance && (
                  <> · {result.provenance.provider} · {result.provenance.environment} · retrieved {result.provenance.retrieved_at} · reference {result.provenance.evidence_reference}</>
                )}
              </li>
            ))}
          </ul>
        </>
      ) : (
        <p className="text-muted">Registry acquisition provenance is not available.</p>
      )}

      {binding ? (
        <div aria-label="Case evidence binding">
          <div className="kv-row"><span className="kv-label">Case use</span><span className="kv-value">{binding.disposition === "CACHE_HIT" ? "Reused cached snapshot" : "Original provider fetch"}</span></div>
          <div className="kv-row"><span className="kv-label">Disposition</span><span className="kv-value">{binding.disposition}</span></div>
          <div className="kv-row"><span className="kv-label">Bound to this case at</span><span className="kv-value">{binding.bound_to_case_at}</span></div>
          <div className="kv-row"><span className="kv-label">Valid-at-use expiry</span><span className="kv-value">{binding.expires_at}</span></div>
          <div className="kv-row"><span className="kv-label">Policy</span><span className="kv-value">{binding.freshness_policy_id} version {binding.freshness_policy_version}</span></div>
          <div className="kv-row"><span className="kv-label">Retained duration</span><span className="kv-value">{binding.freshness_duration_seconds} seconds — 90 elapsed 24-hour periods</span></div>
          <p className="control-help">Provisional Mock POC policy recorded when this evidence was bound. This is not a current validity assessment or an ACRA validity guarantee.</p>
        </div>
      ) : (
        <div className="ds-banner" role="note">
          <strong>Case evidence binding not recorded.</strong>
          <span>Acquisition disposition, case-use time, retained freshness policy, and validity-at-use are unknown. This does not indicate a cache miss, disabled cache, provider fetch, freshness, or current validity.</span>
        </div>
      )}
    </section>
  );
}
