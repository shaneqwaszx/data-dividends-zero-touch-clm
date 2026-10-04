import type { ReactNode } from "react";
import type { ClassifierBenchmark, ImpactOutcome, PolicyCatalogue, PolicyImpact, PolicyProposal, PolicyValue } from "../types";

const value = (v: PolicyValue) => Array.isArray(v.value) ? v.value.join(", ") : String(v.value);
const words = (v: string) => v.replaceAll("_", " ");
const count = (v: number | null) => v === null ? "NOT_ASSESSED" : String(v);
function Outcome({ outcome }: { outcome: ImpactOutcome }) {
  return <><strong>{outcome.label}</strong>{outcome.value !== null && <p>Input / engine value: {outcome.value}</p>}
    {outcome.score !== null && <p>Score: {outcome.score}</p>}{outcome.threshold !== null && <p>Threshold: {outcome.threshold}</p>}
    <p>{outcome.reason_codes.join(" · ")}</p></>;
}
export default function PolicyImpactComparison({ impact, catalogue, proposal, metrics }: {
  impact: PolicyImpact; catalogue: PolicyCatalogue; proposal: PolicyProposal;
  metrics: (benchmark: ClassifierBenchmark, policyVersionLabel: string) => ReactNode;
}) {
  const advisor = impact.advisor;
  return <section aria-label="Policy impact comparison">
    <h4>Change summary</h4><p>{impact.label}</p><p>{advisor.scope}</p>
    <p>Simulation uses controlled synthetic fixtures and current deterministic rule engines. It does not predict production volume, legal/compliance outcomes, or sponsor approval.</p>
    <p role="status">Descriptive materiality: {advisor.materiality}. Automation: {words(advisor.automation_direction)}. Document review: {words(advisor.review_direction)}.</p>
    <p>{advisor.reason_codes.join(" · ")}</p>
    {impact.stale && <p role="status">STALE_PROPOSAL_BASE: retained base version {impact.base_active_version}; current active version {impact.current_active_version}. This comparison does not make the proposal approvable.</p>}
    <details open><summary>Parameter comparison</summary>
      <div className="table-scroll" tabIndex={0} role="region" aria-label="Changed policy parameters">
        <table className="table"><caption>Current, default, retained base and proposed values</caption>
          <thead><tr><th>Parameter</th><th>Current</th><th>Default</th><th>Base</th><th>Proposed</th><th>Impact</th></tr></thead>
          <tbody>{impact.changes.map(change => <tr key={change.policy_id}><th scope="row">{change.name}<p>{change.policy_id}</p></th>
            <td>{value(change.current)}</td><td>{value(change.default)}</td><td>{value(change.base)}</td><td>{value(change.proposed)}</td>
            <td>{change.direction} · {change.materiality}<p>{change.assessment} · {change.effect}</p><p>{change.reason_codes.join(" · ")}</p>{change.limitations.map(text => <p key={text}>{text}</p>)}</td></tr>)}</tbody>
        </table>
      </div>
      {impact.changes.filter(change => change.coupled_policy_ids.length > 0).map(change => <details key={change.policy_id}><summary>Coupled parameters for {change.name}</summary>
        {change.coupled_policy_ids.map(id => {
          const proposed = proposal.rules.find(rule => rule.policy_id === id);
          const active = catalogue.rules.find(rule => rule.policy_id === id);
          const base = (impact.stale ? catalogue.superseded_versions?.find(v => v.version === impact.base_active_version)?.rules : catalogue.rules)?.find(rule => rule.policy_id === id);
          return <p key={id}>{proposed?.name ?? id} · Current {active ? value(active.value) : "NOT_ASSESSED"} · Default {proposed ? value(proposed.default_value) : "NOT_ASSESSED"} · Base {base ? value(base.value) : "NOT_ASSESSED"} · Proposed {proposed ? value(proposed.value) : "NOT_ASSESSED"}</p>;
        })}</details>)}
    </details>
    <details><summary>Workflow impact</summary>{impact.changes.map(change => <p key={change.policy_id}>{change.name}: {change.stages.join(" · ")} · {change.effect} · {change.scenario_ids.length} supplied scenarios ({change.assessment})</p>)}</details>
    <details><summary>Synthetic scenario transitions</summary>
      <p>Identical synthetic inputs are evaluated before and after. Counts include named boundary scenarios, including coincident inputs; they are fixture counts, not independent production cases.</p>
      <div className="table-scroll" tabIndex={0} role="region" aria-label="Synthetic policy transitions"><table className="table"><caption>Authoritative engine outcomes for controlled inputs</caption>
        <thead><tr><th>Fixture / stage</th><th>Before</th><th>After</th></tr></thead>
        <tbody>{advisor.scenarios.map(row => <tr key={row.fixture_id}><th scope="row">{row.fixture_id}<p>{row.stage} · {row.effect}</p></th><td><Outcome outcome={row.before}/></td><td><Outcome outcome={row.after}/></td></tr>)}</tbody>
      </table></div>
    </details>
    <details open><summary>Automation/review delta</summary><p>{advisor.scope}</p>
      <div className="table-scroll" tabIndex={0} role="region" aria-label="Synthetic automation counts"><table className="table"><caption>Stage-specific synthetic counts; unknown values remain NOT_ASSESSED</caption>
        <thead><tr><th>Concept</th><th>Before</th><th>After</th><th>Delta</th></tr></thead><tbody>{Object.entries(advisor.automation_delta).map(([id, row]) => <tr key={id}><th scope="row">{words(id)}</th><td>{count(row.before)}</td><td>{count(row.after)}</td><td>{count(row.delta)}</td></tr>)}</tbody>
      </table></div>
    </details>
    <details><summary>Registry freshness implications</summary><p>Freshness: {words(advisor.registry_reuse_direction)}. Definitive NOT_FOUND cache: {words(advisor.negative_reuse_direction)}.</p><p>Evidence expires at equality. Uncertain failures are not negative cache hits. No expected ACRA traffic or cost is calculated.</p>
      {(["before", "after"] as const).map(side => <p key={side}>{side}: {impact[side].runtime.registry_freshness_seconds / 86400} days; definitive NOT_FOUND TTL {impact[side].runtime.not_found_ttl_seconds} seconds.</p>)}
    </details>
    <details><summary>Ownership threshold implications</summary><p>Existing Decimal engine; inclusive comparator. Candidates remain provisional. Incomplete legal entities retain review.</p>
      {(["before", "after"] as const).map(side => <p key={side}>{side} direct 24.999999% / 25% / 30%: {impact[side].runtime.ownership_numeric_candidates.map(v => v === null ? "NOT_ASSESSED" : v ? "candidate" : "below threshold").join(" / ")}</p>)}
      <p>A zero policy threshold is NOT_ASSESSED because the current ownership engine accepts positive thresholds only.</p>
    </details>
    <details open><summary>Classifier benchmark delta</summary><p>{advisor.classifier_scope}</p>
      <div className="policy-card-grid">{(["before", "after"] as const).map(side => <section key={side}><h5>{side === "before" ? impact.stale ? "Before: retained proposal base" : "Before: active policy" : "After: proposed policy"}</h5>{metrics(impact[side].classifier, impact[side].policy_version_context === "PROSPECTIVE_UNRESERVED" ? "prospective policy version (not reserved or activated)" : impact[side].policy_version_context === "ACTIVATED_PROPOSAL" ? "activated proposal policy version" : "base policy version")}</section>)}</div>
      <p>{Object.entries(advisor.classifier_metric_delta).map(([id, delta]) => `${words(id)}: ${delta.toFixed(6)}`).join(" · ")}</p>
    </details>
    <details open><summary>Unknown / not-assessed impacts</summary><p>NOT_ASSESSED means unknown, not zero impact.</p>{advisor.unknown_impacts.map(row => <p key={row.concept}><strong>{row.concept}: {row.status}</strong> · {row.reason_code} · {row.limitation}</p>)}</details>
    <details open><summary>Approval boundary</summary><p>This read-only, on-demand comparison does not activate policy or approve cases. Existing capabilities and four-eyes controls govern proposal decisions. Existing cases keep their frozen policy; new cases bind the newly active policy.</p></details>
    <details><summary>Fixture identity and evaluation bounds</summary><p>{advisor.fixture_set_id} · {advisor.fixture_set_hash}</p><p>Comparison {impact.comparison_identity}</p><p>{Object.entries(advisor.limits).map(([id, limit]) => `${words(id)}: ${limit}`).join(" · ")}</p></details>
  </section>;
}
