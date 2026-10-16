import { formatOwnershipPercent, formatOwnershipCalculation } from "../ownershipDisplay";
import { useEffect, useMemo, useRef, useState } from "react";

import type { OwnershipAnalysisRecord, OwnershipPath, RegistryAcquisition } from "../types";

import OwnershipStructure from "./OwnershipStructure";
import UboSummary from "./UboSummary";

const PAGE_SIZE = 20;
const VISUAL_EDGE_LIMIT = 11;

function visualEdges(path: OwnershipPath) {
  if (path.edges.length <= VISUAL_EDGE_LIMIT) return { prefix: path.edges, suffix: [] as typeof path.edges, hidden: 0 };
  const prefix = path.edges.slice(0, 5);
  const suffix = path.edges.slice(-5);
  return { prefix, suffix, hidden: path.edges.length - prefix.length - suffix.length };
}

function EdgeList({ edges }: { edges: OwnershipPath["edges"] }) {
  return edges.map((edge) => (
    <li key={edge.relationship_id}>
      <strong>{edge.parent_display_name}</strong> <span aria-label="is owned by">is owned by</span> <strong>{edge.child_display_name}</strong>
      <span> · {formatOwnershipPercent(edge.ownership_percent)} · {edge.relationship_id}</span>
    </li>
  ));
}

export default function OwnershipPathExplorer({ record, acquisition, primaryBlockerVisible = false, presentation = "full" }: { record: OwnershipAnalysisRecord | null; acquisition?: RegistryAcquisition | null; primaryBlockerVisible?: boolean; presentation?: "full" | "main" }) {
  const [candidateId, setCandidateId] = useState<string | null>(null);
  const [pathId, setPathId] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [inspectionOpen, setInspectionOpen] = useState(false);

  const candidate = record?.candidates.find((item) => item.party.party_id === candidateId)
    ?? record?.candidates[0]
    ?? null;
  const path = candidate?.paths.find((item) => item.path_id === pathId) ?? candidate?.paths[0] ?? null;

  useEffect(() => {
    setCandidateId(record?.candidates[0]?.party.party_id ?? null);
    setPathId(record?.candidates[0]?.paths[0]?.path_id ?? null);
    setPage(0);
    setInspectionOpen(false);
  }, [record?.analysis_id]);

  useEffect(() => {
    if (!record) return;
    if (!record.candidates.some((item) => item.party.party_id === candidateId)) {
      setCandidateId(record.candidates[0]?.party.party_id ?? null);
      setPathId(record.candidates[0]?.paths[0]?.path_id ?? null);
      setPage(0);
      return;
    }
    if (candidate && !candidate.paths.some((item) => item.path_id === pathId)) {
      setPathId(candidate.paths[0]?.path_id ?? null);
      setPage(0);
    }
  }, [record, candidate, candidateId, pathId]);

  useEffect(() => {
    const maxPage = Math.max(0, Math.ceil((candidate?.paths.length ?? 0) / PAGE_SIZE) - 1);
    setPage((current) => Math.min(current, maxPage));
  }, [record?.analysis_id, candidate?.party.party_id, candidate?.paths.length]);

  const partialIssues = record?.issues.filter((issue) => [
    "CYCLE_DETECTED",
    "INCOMPLETE_LEGAL_ENTITY",
    "MAXIMUM_DEPTH_EXCEEDED",
    "PATH_LIMIT_EXCEEDED",
  ].includes(issue.code)) ?? [];
  const totalPages = Math.max(1, Math.ceil((candidate?.paths.length ?? 0) / PAGE_SIZE));
  const visiblePaths = useMemo(
    () => candidate?.paths.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE) ?? [],
    [candidate, page],
  );
  const visual = path ? visualEdges(path) : null;
  const registryEmpty = acquisition?.operation_results.some((result) => result.operation === "OWNERSHIP_PARTIES" && result.status === "EMPTY")
    && record?.provider_name === "ACRA_REGISTRY_ACQUISITION" && record.state === "REVIEW_REQUIRED" && !record.error;
  const clientSupplied = record?.provider_name === "MANUAL_DECLARATION_POC" && record.provider_environment === "LOCAL";

  if (!record) {
    return <section className="evidence-section-block"><h4>Ownership path explorer</h4><p className="text-muted">Ownership analysis is not available.</p></section>;
  }

  const candidateInspection = <>
      {record.candidates.length === 0 ? <p className="text-muted">No retained ownership candidates are available. This does not establish that the hierarchy is complete.</p> : (
        <>


          {candidate && (
            <article aria-label={`Ownership candidate ${candidate.party.display_name}`}>
              <h5>{candidate.party.display_name}</h5>
              <dl>
                <div><dt>Direct</dt><dd>{formatOwnershipPercent(candidate.direct_ownership_percent)}</dd></div>
                <div><dt>Indirect</dt><dd>{formatOwnershipPercent(candidate.indirect_ownership_percent)}</dd></div>
                <div><dt>Aggregated</dt><dd>{formatOwnershipPercent(candidate.aggregated_ownership_percent)}</dd></div>
                <div><dt>Threshold comparison</dt><dd>{candidate.threshold_comparator} {formatOwnershipPercent(candidate.threshold_percent)} → {candidate.threshold_result}</dd></div>
                <div><dt>Classification</dt><dd>{candidate.classification}</dd></div>
              </dl>

              {path ? (
                <div aria-label={`Selected retained path ${path.path_id}`}>
                  <h6>Selected retained path: {path.path_id}</h6>
                  <p>{formatOwnershipCalculation(path.calculation)}</p>
                  <p>Effective ownership: {formatOwnershipPercent(path.effective_ownership_percent)}</p>
                  <p className="control-help">Semantic direction: owned entity → owner. This selected retained path is not a complete hierarchy.</p>
                  <ol aria-label="Selected ownership path visual">
                    <EdgeList edges={visual!.prefix} />
                    {visual!.hidden > 0 && <li data-hidden-edge-boundary>… {visual!.hidden} hidden edge{visual!.hidden === 1 ? "" : "s"} between bounded prefix and suffix …</li>}
                    <EdgeList edges={visual!.suffix} />
                  </ol>
                </div>
              ) : <p className="text-muted">No retained calculation path is available for this candidate.</p>}

              <div className="table-scroll">
                <table>
                  <caption>Retained paths — page {page + 1} of {totalPages}; not a complete hierarchy</caption>
                  <thead><tr><th>Path</th><th>Effective ownership</th><th>Calculation</th><th>Inspect</th></tr></thead>
                  <tbody>
                    {visiblePaths.map((item) => (
                      <tr key={item.path_id}>
                        <td>{item.path_id}</td><td>{formatOwnershipPercent(item.effective_ownership_percent)}</td><td>{formatOwnershipCalculation(item.calculation)}</td>
                        <td><button type="button" className="btn btn-ghost" aria-pressed={path?.path_id === item.path_id} onClick={() => setPathId(item.path_id)}>Inspect {item.path_id}</button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {totalPages > 1 && <nav aria-label="Retained path pages"><button type="button" disabled={page === 0} onClick={() => setPage((value) => value - 1)}>Previous paths</button><button type="button" disabled={page + 1 >= totalPages} onClick={() => setPage((value) => value + 1)}>Next paths</button></nav>}
            </article>
          )}
        </>
      )}
  </>;

  return (
    <section className="evidence-section-block" aria-labelledby="ownership-path-heading">
      <p className="card-kicker">Local deterministic analysis · provisional, not a legal determination</p>
      <h4 id="ownership-path-heading">Ownership path explorer</h4>
      <div className="kv-row"><span className="kv-label">Analysis state</span><span className="kv-value">{record.state}</span></div>
      <div className="kv-row"><span className="kv-label">Threshold</span><span className="kv-value">{record.threshold_comparator} {formatOwnershipPercent(record.threshold_percent)}</span></div>
      <p className="control-help">Source: {record.provider_name ?? "not available"} · {record.provider_environment ?? "not available"}</p>
      {clientSupplied && <p className="control-help">Client-supplied ownership evidence · LOCAL · USER_SUPPLIED_DECLARATION · MANUAL_DECLARATION_POC · not ACRA-derived. This declaration is retained for local analysis, not independently verified ownership.</p>}
      {registryEmpty && !primaryBlockerVisible && <div className="ds-banner ds-banner-warn" role="note">
        <strong>Ownership information required</strong>
        <span>Ownership is unavailable from current registry evidence. Use Add structured ownership details or Upload ownership evidence to provide reviewed client evidence for UBO analysis.</span>
      </div>}
      <p className="s2-ownership-summary">{record.candidates.length} retained natural-person candidate{record.candidates.length === 1 ? "" : "s"} · {record.parties.length} parties · {record.relationships.length} direct relationships. {record.state === "ANALYZED" ? "Calculable provisional view." : "Incomplete or disputed evidence requires review."}</p>
      <p className="control-help">{record.candidates.slice(0, 3).map((item) => `${item.party.display_name}: ${formatOwnershipPercent(item.aggregated_ownership_percent)} effective (${item.classification})`).join("; ") || "No calculable candidate retained."}</p>
      {record.source_classification === "OFFICIAL_MOCK_PLUS_LOCAL_SUPPLEMENT" && <p className="ds-banner">Official Marketplace Mock facts with separately labelled LOCAL_SYNTHETIC_SUPPLEMENT ownership evidence. These sources remain distinct and are not Live registry evidence.</p>}
      <UboSummary record={record} />
      <OwnershipStructure key={`structure:${record.analysis_id}`} record={record} selectedPartyId={candidate?.party.party_id ?? null} onSelectPerson={(partyId) => { setCandidateId(partyId); setPathId(null); setPage(0); if (candidate?.party.party_id !== partyId) setInspectionOpen(false); }} />
      {presentation === "main" ? <>
        {partialIssues.length > 0 && <div className="ds-banner ds-banner-warn" role="note"><strong>Non-definitive partial ownership view.</strong>{partialIssues.map(issue => <p key={`${issue.code}-${issue.message}`}>{issue.code}: {issue.message}</p>)}</div>}
        {record.error && !primaryBlockerVisible && <p role="alert">{record.error.code}: {record.error.message}</p>}
        <OwnershipObservations record={record} />
        {candidate && (candidate.paths.length > 1 || candidate.paths.some(item => !item.is_direct)) &&
          <details key={`${record.analysis_id}:${candidate.party.party_id}`} className="evidence-details" onToggle={event => {
            const details = event.currentTarget;
            if (!details.open && details.contains(document.activeElement)) details.querySelector("summary")?.focus();
            setInspectionOpen(details.open);
          }}>
            <summary>Technical retained path inspection</summary>
            {inspectionOpen && candidateInspection}
          </details>}
      </> : <details key={record.analysis_id} className="evidence-details s2-ownership-structure">
        <summary>Technical calculations and retained paths</summary>
        <OwnershipSupportingDetails record={record} presentation="full" primaryBlockerVisible={primaryBlockerVisible} />
        {candidateInspection}
      </details>}

    </section>
  );
}

/** Passive projections never create candidate/path or form state. */
export function OwnershipSupportingDetails({ record, presentation, primaryBlockerVisible = false }: {
  record: OwnershipAnalysisRecord | null; presentation: "full" | "more" | "technical"; primaryBlockerVisible?: boolean;
}) {
  const panel = useRef<HTMLElement>(null);
  const [technicalOpen, setTechnicalOpen] = useState(false);
  const hasRecord = record !== null;
  useEffect(() => {
    // Observe after the parent layout effect has settled native scope-reset closure.
    if (presentation !== "technical" || !hasRecord) return;
    const disclosure = panel.current?.closest("details");
    // Native StageDisclosure remains the open-state owner; no path selection is copied.
    const update = () => setTechnicalOpen(disclosure?.open ?? true);
    update();
    disclosure?.addEventListener("toggle", update);
    return () => disclosure?.removeEventListener("toggle", update);
  }, [presentation, hasRecord]);
  if (!record) return null;
  const Disclosure = presentation === "full" ? "details" : "section";
  const Label = presentation === "full" ? "summary" : "h5";
  const partialIssues = record?.issues.filter((issue) => [
    "CYCLE_DETECTED",
    "INCOMPLETE_LEGAL_ENTITY",
    "MAXIMUM_DEPTH_EXCEEDED",
    "PATH_LIMIT_EXCEEDED",
  ].includes(issue.code)) ?? [];
  return <section ref={panel} className="ownership-support-panel">
    {presentation !== "more" && <>
      {presentation === "technical" && <>
      <h4>Retained calculation and source metadata</h4>
      <p>Analysis {record.analysis_id} · version {record.version ?? "UNKNOWN"} · {record.provider_name} · {record.provider_environment}</p>
      <p>Created {record.created_at} · updated {record.updated_at}</p>
      <p>Exact retained threshold: {record.threshold_comparator} {record.threshold_percent}</p>
      <div className="table-scroll" tabIndex={0}><table><caption>Exact backend Decimal values — read-only, no recalculation</caption>
        <thead><tr><th>Candidate</th><th>Direct</th><th>Indirect</th><th>Aggregated</th><th>Threshold / result</th><th>Retained paths</th></tr></thead>
        <tbody>{record.candidates.map(item => <tr key={item.party.party_id}>
          <td>{item.party.display_name} · {item.classification}</td><td>{item.direct_ownership_percent}</td><td>{item.indirect_ownership_percent}</td><td>{item.aggregated_ownership_percent}</td>
          <td>{item.threshold_comparator} {item.threshold_percent} · {item.threshold_result}</td>
          <td>{technicalOpen ? item.paths.map(path => <p key={path.path_id}>{path.path_id} · {path.effective_ownership_percent} · <span>{path.calculation}</span>{path.edges.map(edge => <span key={edge.relationship_id}> · {edge.relationship_id}: {edge.ownership_percent}</span>)}</p>) : <span>{item.paths.length} retained paths; open Technical details to inspect exact path values.</span>}</td>
        </tr>)}</tbody>
      </table></div>
      </>}
      {record.parties.length > 0 && <div className="table-scroll" tabIndex={0} aria-label="Ownership parties and retained calculations"><table className="table">
        <caption>Parties and backend-calculated effective interests</caption>
        <thead><tr><th>Party</th><th>Type</th><th>Country</th><th>Identifier</th><th>Direct interests in owned entities</th><th>Effective in root</th></tr></thead>
        <tbody>{record.parties.map((party) => <tr key={party.party_id}>
          <td>{party.display_name} · {party.party_id}</td><td>{party.party_type.replaceAll("_", " ")}</td><td>{party.country ?? "Not supplied"}</td><td>{party.registration_number ?? "Not supplied"}</td>
          <td>{record.relationships.filter((edge) => edge.child_party_id === party.party_id).map((edge) => `${formatOwnershipPercent(edge.ownership_percent)} in ${record.parties.find((item) => item.party_id === edge.parent_party_id)?.display_name ?? edge.parent_party_id}`).join("; ") || "No direct interest retained"}</td>
          <td>{record.candidates.find((item) => item.party.party_id === party.party_id)?.aggregated_ownership_percent ? formatOwnershipPercent(record.candidates.find((item) => item.party.party_id === party.party_id)!.aggregated_ownership_percent) : "Not calculated by retained analysis"}</td>
        </tr>)}</tbody>
      </table></div>}
      {record.relationships.length > 0 && <div className="table-scroll">
        <table aria-label="Retained ownership details">
          <caption>Retained ownership parties and direct interests</caption>
          <thead><tr><th>Owned entity</th><th>Owner</th><th>Identifier</th><th>Direct ownership</th><th>Source</th></tr></thead>
          <tbody>{record.relationships.map((relationship) => {
            const party = record.parties.find((item) => item.party_id === relationship.child_party_id);
            const ownedEntity = record.parties.find((item) => item.party_id === relationship.parent_party_id);
            return <tr key={relationship.relationship_id}>
              <td>{ownedEntity?.display_name ?? relationship.parent_party_id}</td>
              <td>{party?.display_name ?? relationship.child_party_id}</td>
              <td>{party?.registration_number ?? "Not supplied"}</td>
              <td>{formatOwnershipPercent(relationship.ownership_percent)}</td>
              <td>{relationship.provenance.provider} · {relationship.provenance.environment}</td>
            </tr>;
          })}</tbody>
        </table>
      </div>}

      {partialIssues.length > 0 && (
        <Disclosure className="evidence-details"><Label>Why is this blocked?</Label>
          <strong>Non-definitive partial ownership view.</strong>
          {partialIssues.map((issue) => <span key={`${issue.code}-${issue.message}`}>{issue.code}: {issue.message}</span>)}
        </Disclosure>
      )}
      {record.evidence?.length ? <div className="table-scroll" tabIndex={0} aria-label="Original ownership evidence">
        <table className="table"><caption>Original ownership evidence — percentages are shown only when justified</caption>
          <thead><tr><th>Entity</th><th>Evidence</th><th>Original value</th><th>Source</th></tr></thead>
          <tbody>{record.evidence.map((item) => <tr key={item.evidence_id}>
            <td>{item.entity_identifier ?? "Unknown binding"}</td><td>{item.kind.replaceAll("_", " ")}</td>
            <td>{item.kind === "DIRECT_PERCENTAGE" ? formatOwnershipPercent(item.numeric_value ?? item.raw_value.replace(/%$/, "")) : item.raw_value}{item.kind === "SHARE_UNITS" ? " units" : ""}</td>
            <td>{item.provider} · {item.environment} · {item.source_operation} · {item.retrieved_at}</td>
          </tr>)}</tbody>
        </table>
      </div> : null}
      {record.tagging && <Disclosure className="evidence-details"><Label>Ownership evidence classification</Label>
        <p>Parameterized deterministic evidence classifier · not a trained ML model · no legal determination</p>
        {record.tagging.tags.map((item) => <section key={`${item.tag}:${item.evidence_ids.join()}`}>
          <p>{item.tag.replaceAll("_", " ")} · evidence score {item.confidence} · not a probability</p>
          {item.score != null && <p>Score {item.score} · threshold {item.threshold} · policy version {item.policy_version}</p>}
          <p>Rule {item.rule_version} · evidence {item.evidence_ids.join(", ")} · case {item.case_version} / evidence {item.evidence_version}</p>
          <Disclosure><Label>Why is this blocked?</Label><p>Classification reasons: {(item.reason_codes?.length ? item.reason_codes : [item.reason_code]).join(" · ")}. A semantic label does not decide arithmetic sufficiency or legal ownership.</p></Disclosure>
        </section>)}
      </Disclosure>}
      {record.error && !primaryBlockerVisible && <Disclosure className="evidence-details"><Label>Why is this blocked?</Label><p>{record.error.code}: {record.error.message}</p></Disclosure>}

    </>}
    {presentation !== "technical" && <>
      {!!record.supplemental_relationships?.length && <Disclosure className="evidence-details"><Label>Retained local supplement graph</Label>
        <p>LOCAL_SYNTHETIC_SUPPLEMENT originals remain separate from conflicting official quantitative evidence. They have not replaced official identity or officer facts.</p>
        <div className="table-scroll" tabIndex={0}><table className="table"><caption>Original local supplement direct relationships</caption><thead><tr><th>Owned entity</th><th>Owner</th><th>Explicit percentage</th><th>Source</th></tr></thead>
          <tbody>{record.supplemental_relationships.map((edge) => <tr key={edge.relationship_id}><td>{record.supplemental_parties?.find((party) => party.party_id === edge.parent_party_id)?.display_name ?? edge.parent_party_id}</td><td>{record.supplemental_parties?.find((party) => party.party_id === edge.child_party_id)?.display_name ?? edge.child_party_id}</td><td>{formatOwnershipPercent(edge.ownership_percent)}</td><td>{edge.provenance.provider} · {edge.provenance.environment}</td></tr>)}</tbody>
        </table></div>
        {record.supplemental_evidence?.map((item) => <p key={item.evidence_id}>{item.entity_identifier ?? "Unknown binding"} · {item.kind} · original {item.kind === "DIRECT_PERCENTAGE" ? formatOwnershipPercent(item.numeric_value ?? item.raw_value.replace(/%$/, "")) : item.raw_value} · {item.provider} · {item.environment} · {item.source_operation}</p>)}
      </Disclosure>}
      {presentation === "full" && <OwnershipObservations record={record} />}
      {record.manual_review_receipt && <section className="s2-ownership-receipt"><h5>Current ownership decision receipt</h5><p>{record.manual_review_receipt.source_selection ?? record.manual_review_receipt.source_type} · {record.manual_review_receipt.actor_id} · {record.manual_review_receipt.reviewed_at}</p><p>{record.manual_review_receipt.rationale ?? "No reviewer note supplied"}</p><p>Evidence document {record.manual_review_receipt.evidence_document_id} · review revision {record.manual_review_receipt.evidence_document_version} · as of {record.manual_review_receipt.as_of_date}</p><p>Observed document review revisions: {record.manual_review_receipt.observed_document_versions?.map((item) => `${item.document_id} / ${item.event_count}`).join("; ") || "None recorded"}</p><p>Selected immutable observations: {record.manual_review_receipt.selected_observation_ids?.join(", ") || "None recorded"}</p><p className="control-help">Reviewed client evidence, not independently verified ownership.</p></section>}
      {!!record.prior_analyses?.length && <Disclosure className="evidence-history"><Label>Retained ownership history ({record.prior_analyses.length}){presentation === "more" ? " — Historical / read-only" : ""}</Label>
        {record.prior_analyses.map((prior) => <section key={prior.analysis_id}><h5>Prior analysis {prior.analysis_id} · version {prior.version ?? "UNKNOWN"}</h5><p>{prior.provider_name} · {prior.provider_environment} · {prior.state}</p>
          <div className="table-scroll" tabIndex={0}><table className="table"><caption>Prior retained ownership relationships</caption><thead><tr><th>Owned entity</th><th>Owner</th><th>Direct percentage</th><th>Source</th></tr></thead><tbody>{prior.relationships.map((edge) => <tr key={edge.relationship_id}><td>{prior.parties.find((party) => party.party_id === edge.parent_party_id)?.display_name ?? edge.parent_party_id}</td><td>{prior.parties.find((party) => party.party_id === edge.child_party_id)?.display_name ?? edge.child_party_id}</td><td>{formatOwnershipPercent(edge.ownership_percent)}</td><td>{edge.provenance.provider} · {edge.provenance.environment}</td></tr>)}</tbody></table></div>
          {prior.evidence?.map((item) => <p key={item.evidence_id}>Original scalar {item.kind} · {item.kind === "DIRECT_PERCENTAGE" ? formatOwnershipPercent(item.numeric_value ?? item.raw_value.replace(/%$/, "")) : item.raw_value} · {item.provider} · {item.environment} · {item.source_operation}</p>)}
          {prior.supplemental_relationships?.map((edge) => <p key={edge.relationship_id}>Original supplement relationship {edge.parent_party_id} → {edge.child_party_id} · {formatOwnershipPercent(edge.ownership_percent)} · {edge.provenance.provider} · {edge.provenance.environment}</p>)}
          {prior.supplemental_evidence?.map((item) => <p key={item.evidence_id}>Original supplement scalar {item.kind} · {item.kind === "DIRECT_PERCENTAGE" ? formatOwnershipPercent(item.numeric_value ?? item.raw_value.replace(/%$/, "")) : item.raw_value} · {item.provider} · {item.environment} · {item.source_operation}</p>)}
          {prior.candidates.map((item) => <p key={item.party.party_id}>{item.party.display_name} · {formatOwnershipPercent(item.aggregated_ownership_percent)} effective · {item.classification}</p>)}
          {prior.manual_review_receipt && <p>Prior decision {prior.manual_review_receipt.source_selection ?? prior.manual_review_receipt.source_type} · {prior.manual_review_receipt.actor_id} · {prior.manual_review_receipt.reviewed_at} · {prior.manual_review_receipt.rationale ?? "No reviewer note supplied"} · document {prior.manual_review_receipt.evidence_document_id} / review revision {prior.manual_review_receipt.evidence_document_version}</p>}
          {prior.document_observations?.map((item) => <p key={item.observation_id}>Original proposal {item.owner_name} · {formatOwnershipPercent(item.explicit_percentage)} · shares {item.share_count ?? "not supplied"} / denominator {item.explicit_total_shares ?? "not supplied"} · {item.extraction_quality ?? "UNKNOWN"} · {item.extraction_method ?? "UNKNOWN"} · document {item.document_id} / version {item.document_version} / page {item.page_number} / {item.source_reference} · {item.decision_state}</p>)}
          {prior.document_discrepancies?.map((item) => <p key={item.observation_id}>Original discrepancy {item.agreement} · {item.reason_code} · {item.verification_state}</p>)}
        </section>)}
      </Disclosure>}

    </>}
  </section>;
}

function OwnershipObservations({ record }: { record: OwnershipAnalysisRecord }) {
  return <>
      {!!record.document_observations?.length && <div className="table-scroll" tabIndex={0}><table className="table"><caption>Proposed document ownership and source comparison</caption>
        <thead><tr><th>Owner / owned entity</th><th>Explicit source quantities</th><th>Extraction quality / method / evidence score</th><th>Agreement</th><th>Verification</th><th>Immutable source</th></tr></thead>
        <tbody>{record.document_observations.map((observation) => {
          const discrepancy = record.document_discrepancies?.find((item) => item.observation_id === observation.observation_id);
          return <tr key={observation.observation_id}>
            <td>{observation.owner_name} ({observation.owner_type ?? "Type unknown"}) → {observation.owned_entity_name ?? observation.owned_entity_registration_identifier ?? "Unknown owned entity"}</td>
            <td>Percentage {observation.explicit_percentage !== null ? `${formatOwnershipPercent(observation.explicit_percentage)}` : "not supplied"} · shares {observation.share_count ?? "not supplied"} · denominator {observation.explicit_total_shares ?? "not supplied"} · class {observation.share_class ?? "not supplied"} · as of {observation.as_of_date ?? "not supplied"}</td>
            <td>{observation.extraction_quality ?? "UNKNOWN"} · {observation.extraction_method ?? "UNKNOWN"} · {observation.evidence_score} (not a probability)</td>
            <td>{discrepancy?.agreement ?? "NOT COMPARED"} · current {formatOwnershipPercent(discrepancy?.current_percentage)} / proposed {formatOwnershipPercent(discrepancy?.proposed_percentage)}{discrepancy && ` · ${discrepancy.reason_code}`}</td>
            <td>{observation.decision_state} · {discrepancy?.verification_state ?? "REVIEW_REQUIRED"}</td>
            <td>{observation.document_id} · document version {observation.document_version} · page {observation.page_number} · {observation.source_reference} · {observation.observation_id}</td>
          </tr>;
        })}</tbody>
      </table></div>}
  </>;
}
