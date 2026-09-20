import { useEffect, useMemo, useState } from "react";

import type { OwnershipAnalysisRecord, OwnershipPath } from "../types";

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
      <span> · {edge.ownership_percent} · {edge.relationship_id}</span>
    </li>
  ));
}

export default function OwnershipPathExplorer({ record }: { record: OwnershipAnalysisRecord | null }) {
  const [candidateId, setCandidateId] = useState<string | null>(null);
  const [pathId, setPathId] = useState<string | null>(null);
  const [page, setPage] = useState(0);

  const candidate = record?.candidates.find((item) => item.party.party_id === candidateId)
    ?? record?.candidates[0]
    ?? null;
  const path = candidate?.paths.find((item) => item.path_id === pathId) ?? candidate?.paths[0] ?? null;

  useEffect(() => {
    setCandidateId(record?.candidates[0]?.party.party_id ?? null);
    setPathId(record?.candidates[0]?.paths[0]?.path_id ?? null);
    setPage(0);
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

  if (!record) {
    return <section className="evidence-section-block"><h4>Ownership path explorer</h4><p className="text-muted">Ownership analysis is not available.</p></section>;
  }

  return (
    <section className="evidence-section-block" aria-labelledby="ownership-path-heading">
      <p className="card-kicker">Local deterministic analysis · provisional, not a legal determination</p>
      <h4 id="ownership-path-heading">Ownership path explorer</h4>
      <div className="kv-row"><span className="kv-label">Analysis state</span><span className="kv-value">{record.state}</span></div>
      <div className="kv-row"><span className="kv-label">Threshold</span><span className="kv-value">{record.threshold_comparator} {record.threshold_percent}</span></div>

      {partialIssues.length > 0 && (
        <div className="ds-banner ds-banner-warn" role="note">
          <strong>Non-definitive partial ownership view.</strong>
          {partialIssues.map((issue) => <span key={`${issue.code}-${issue.message}`}>{issue.code}: {issue.message}</span>)}
        </div>
      )}
      {record.error && <div className="ds-banner ds-banner-warn"><strong>{record.error.code}</strong><span>{record.error.message}</span></div>}

      {record.candidates.length === 0 ? <p className="text-muted">No retained ownership candidates are available. This does not establish that the hierarchy is complete.</p> : (
        <>
          <div aria-label="Ownership candidates">
            {record.candidates.map((item) => (
              <button
                className="btn btn-secondary"
                type="button"
                key={item.party.party_id}
                aria-pressed={candidate?.party.party_id === item.party.party_id}
                onClick={() => { setCandidateId(item.party.party_id); setPathId(item.paths[0]?.path_id ?? null); setPage(0); }}
              >
                {item.party.display_name}
              </button>
            ))}
          </div>

          {candidate && (
            <article aria-label={`Ownership candidate ${candidate.party.display_name}`}>
              <h5>{candidate.party.display_name}</h5>
              <dl>
                <div><dt>Direct</dt><dd>{candidate.direct_ownership_percent}</dd></div>
                <div><dt>Indirect</dt><dd>{candidate.indirect_ownership_percent}</dd></div>
                <div><dt>Aggregated</dt><dd>{candidate.aggregated_ownership_percent}</dd></div>
                <div><dt>Threshold comparison</dt><dd>{candidate.threshold_comparator} {candidate.threshold_percent} → {candidate.threshold_result}</dd></div>
                <div><dt>Classification</dt><dd>{candidate.classification}</dd></div>
              </dl>

              {path ? (
                <div aria-label={`Selected retained path ${path.path_id}`}>
                  <h6>Selected retained path: {path.path_id}</h6>
                  <p>{path.calculation}</p>
                  <p>Effective ownership: {path.effective_ownership_percent}</p>
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
                        <td>{item.path_id}</td><td>{item.effective_ownership_percent}</td><td>{item.calculation}</td>
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
    </section>
  );
}
