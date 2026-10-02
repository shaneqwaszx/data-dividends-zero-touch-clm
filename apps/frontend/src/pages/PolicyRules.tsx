import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { ApiError, fetchPolicies, savePolicyProposal, submitPolicyProposal, decidePolicyProposal, fetchPolicyImpact, fetchClassifierBenchmark } from "../api";
import type { AuthenticatedProfile, PolicyCatalogue, PolicyRule, PolicyValue, PolicyProposal, PolicyImpact, ClassifierBenchmark } from "../types";

export function displayPolicyValue(value: PolicyValue): string { return Array.isArray(value.value) ? value.value.join(", ") : String(value.value); }
export function policyIsEditable(rule: PolicyRule, allowed: boolean): boolean { return allowed && rule.enforcement === "RUNTIME_ENFORCED" && !rule.policy_id.startsWith("GOLDTIER_"); }
export function parsePolicyValueInput(rule: PolicyRule, value: string): PolicyValue {
  switch (rule.value_type) {
    case "BOOLEAN": return { type: "BOOLEAN", value: value === "true" };
    case "INTEGER": return { type: "INTEGER", value: Number(value) };
    case "DECIMAL": return { type: "DECIMAL", value };
    case "STRING_LIST": return { type: "STRING_LIST", value: value.split(",").map(v => v.trim()).filter(Boolean) };
    case "STRING": return { type: "STRING", value };
  }
}
export function proposalEditChanges(catalogue: PolicyCatalogue, draft: PolicyProposal | null, changes: Record<string, PolicyValue>): Record<string, PolicyValue> {
  const resetRemoved = Object.fromEntries((draft?.rules ?? []).filter(rule => JSON.stringify(rule.value) !== JSON.stringify(catalogue.rules.find(active => active.policy_id === rule.policy_id)?.value)).map(rule => [rule.policy_id, catalogue.rules.find(active => active.policy_id === rule.policy_id)!.value]));
  return { ...resetRemoved, ...changes };
}
export function beginPolicyMutation(guard: { current: boolean }): boolean { if (guard.current) return false; guard.current = true; return true; }
export function shouldCancelPolicyReset(key: string, busy: boolean): boolean { return key === "Escape" && !busy; }
export async function executePolicyMutation(run: () => Promise<PolicyCatalogue>, refresh: () => Promise<PolicyCatalogue>, fallback: string): Promise<{ succeeded: boolean; catalogue?: PolicyCatalogue; error: string | null }> {
  try { return { succeeded: true, catalogue: await run(), error: null }; }
  catch (error) {
    if (error instanceof ApiError && error.status === 409) {
      try { return { succeeded: false, catalogue: await refresh(), error: "The policy catalogue changed. Review the refreshed values before trying again." }; }
      catch { return { succeeded: false, error: "The policy catalogue changed, but refreshed values are temporarily unavailable." }; }
    }
    return { succeeded: false, error: error instanceof ApiError ? error.message : fallback };
  }
}
export function PolicyClassificationBadge({ classification }: { classification: string }) { return <span className={`policy-classification policy-classification--${classification.toLowerCase().replaceAll(" ", "-")}`}>{classification}</span>; }
export type PolicyResetConfirmation = { kind: "single"; rule: PolicyRule } | { kind: "all" };
export function PolicyResetDialog({ confirmation, busy, onCancel, onConfirm }: { confirmation: PolicyResetConfirmation; busy: boolean; onCancel: () => void; onConfirm: () => void }) {
  const cancel = useRef<HTMLButtonElement>(null);
  useEffect(() => { cancel.current?.focus(); }, []);
  function keyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (shouldCancelPolicyReset(event.key, busy)) { event.preventDefault(); onCancel(); }
    if (event.key === "Tab") {
      const buttons = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>("button:not(:disabled)"));
      if ((event.shiftKey && document.activeElement === buttons[0]) || (!event.shiftKey && document.activeElement === buttons.at(-1))) { event.preventDefault(); (event.shiftKey ? buttons.at(-1) : buttons[0])?.focus(); }
    }
  }
  return <div className="dialog-backdrop" role="presentation"><div className="dialog" role="alertdialog" aria-modal="true" aria-labelledby="policy-reset-title" aria-describedby="policy-reset-description" onKeyDown={keyDown}>
    <h2 id="policy-reset-title">Propose reset {confirmation.kind === "single" ? confirmation.rule.name : "of editable business parameters"}?</h2>
    <p id="policy-reset-description">The default becomes a proposed value. Active values change only after independent Director approval. Existing cases keep their frozen policy.</p>
    <div className="dialog-actions"><button ref={cancel} type="button" className="btn btn-ghost" onClick={onCancel} disabled={busy}>Cancel</button><button type="button" className="btn btn-primary" onClick={onConfirm} disabled={busy}>Use default in proposal</button></div>
  </div></div>;
}
export function policyExplanation(rule: PolicyRule): { formula: string; affects: string } {
  const id = rule.policy_id;
  if (id === "REGISTRY_FRESHNESS_DAYS") return { formula: "Fresh when evaluation UTC < oldest successful operation UTC + freshness days × 86,400 seconds", affects: "New cases: normalized registry operation reuse and complete evidence binding" };
  if (id === "REGISTRY_NOT_FOUND_TTL_SECONDS") return { formula: "Reuse definitive NOT_FOUND when evaluation UTC < result UTC + TTL seconds", affects: "New cases: repeated missing-UEN lookup; uncertain failures are never negative hits" };
  if (id.startsWith("EVIDENCE_")) return { formula: "Semantic score = kind weight × recognized kind + binding weight × identifier present + confidence weight × source confidence; recognized evidence requires score ≥ threshold", affects: "New analyses: deterministic semantic labels; ownership arithmetic and legal findings remain separate" };
  if (id === "DOCUMENT_IDP_REVIEW_CONFIDENCE_THRESHOLD") return { formula: "Provisional document continuation when field confidence ≥ threshold", affects: "New cases: document review and reconciliation" };
  if (id.startsWith("OWNERSHIP_UBO_")) return { formula: "Numeric UBO candidate when aggregated Decimal ownership percent ≥ threshold", affects: "New cases: ownership candidates; unresolved control and contradiction still require review" };
  if (id.startsWith("ENTITY_RESOLUTION_")) return { formula: "Resolution score = Σ(feature similarity × approved feature weight); thresholds and ambiguity margin determine match or review", affects: "New cases: advisory entity resolution" };
  if (id.startsWith("UBO_ADVISORY_")) return { formula: "Advisory score is compared with likely and unlikely thresholds", affects: "New cases: advisory classification; never a legal UBO decision" };
  if (id.startsWith("MOCK_RISK_")) return { formula: "Mock risk score is compared with medium/high thresholds; blocking applies only when enabled", affects: "New cases: mock advisory risk and readiness" };
  return { formula: "Fixed contract or system definition", affects: rule.enforcement === "DISPLAY_SHOWCASE_ONLY" ? "Historical display metadata only" : rule.category };
}
export function policyCategory(rule: PolicyRule): string {
  if (rule.policy_id.startsWith("REGISTRY_")) return "Registry & External Data";
  if (rule.policy_id.startsWith("DOCUMENT_") || rule.policy_id.startsWith("RECONCILIATION_") || rule.policy_id.startsWith("ENTITY_RESOLUTION_")) return "Documents & Reconciliation";
  if (rule.policy_id.startsWith("OWNERSHIP_") || rule.policy_id.startsWith("UBO_")) return "Ownership & UBO";
  if (rule.policy_id.startsWith("EVIDENCE_")) return "Ownership Evidence Classification";
  return "Workflow / Intervention";
}
export function PolicyTable({ catalogue, canMutate, onSave, onReset }: { catalogue: PolicyCatalogue; canMutate: boolean; onSave: (rule: PolicyRule, value: PolicyValue) => Promise<boolean>; onReset: (rule: PolicyRule) => void }) {
  return <div className="policy-card-grid">{catalogue.rules.map(rule => <PolicyCard key={rule.policy_id} rule={rule} canMutate={canMutate} onSave={onSave} onReset={onReset} />)}</div>;
}
function PolicyCard({ rule, canMutate, onSave, onReset }: { rule: PolicyRule; canMutate: boolean; onSave: (rule: PolicyRule, value: PolicyValue) => Promise<boolean>; onReset: (rule: PolicyRule) => void }) {
  const [editing, setEditing] = useState(false); const [value, setValue] = useState(displayPolicyValue(rule.value)); const [busy, setBusy] = useState(false);
  useEffect(() => { setValue(displayPolicyValue(rule.value)); setEditing(false); }, [rule]);
  const explanation = policyExplanation(rule);
  async function save(event: FormEvent) { event.preventDefault(); if (busy) return; setBusy(true); try { if (await onSave(rule, parsePolicyValueInput(rule, value))) setEditing(false); } finally { setBusy(false); } }
  return <article className="card policy-parameter"><h3>{rule.name}</h3><p>{rule.description}</p>
    <dl className="policy-values"><div><dt>Current</dt><dd>{displayPolicyValue(rule.value)}</dd></div><div><dt>Default</dt><dd>{displayPolicyValue(rule.default_value)}</dd></div><div><dt>Rule version</dt><dd>{rule.version}</dd></div></dl>
    <p className="policy-formula"><strong>Formula:</strong> {explanation.formula}</p><p><strong>Affects:</strong> {explanation.affects}</p>
    <p className="text-muted">{rule.authority?.replaceAll("_", " ") ?? "Project definition"} · {rule.enforcement === "DISPLAY_SHOWCASE_ONLY" ? "Showcase only · Not runtime enforced" : rule.enforcement === "NOT_EDITABLE" ? "Fixed definition" : "Runtime enforced"}</p>
    {policyIsEditable(rule, canMutate) && (editing ? <form onSubmit={event => void save(event)} className="policy-editor"><label>Proposed value for {rule.name}{rule.value_type === "BOOLEAN" ? <select value={value} onChange={event => setValue(event.target.value)} disabled={busy}><option value="true">true</option><option value="false">false</option></select> : <input value={value} onChange={event => setValue(event.target.value)} type="number" step={rule.value_type === "INTEGER" ? "1" : "0.000001"} min={rule.minimum ?? undefined} max={rule.maximum ?? undefined} required disabled={busy} />}</label><button className="btn btn-secondary" disabled={busy} type="submit">Use proposed value</button><button className="btn btn-ghost" disabled={busy} type="button" onClick={() => setEditing(false)}>Cancel edit</button></form> : <div className="policy-actions"><button className="btn btn-secondary" type="button" onClick={() => setEditing(true)}>Propose change</button><button className="btn btn-ghost" type="button" onClick={() => onReset(rule)}>Reset to default</button></div>)}
  </article>;
}
const percent = (value: number) => `${(value * 100).toFixed(1)}%`;
export function ClassifierMetrics({ benchmark }: { benchmark: ClassifierBenchmark }) {
  return <details className="card policy-metrics"><summary>{benchmark.label} · labelled synthetic benchmark</summary><p>{benchmark.scope}. Support {benchmark.support}; exact accuracy {percent(benchmark.exact_accuracy)}.</p>
    <p>Macro precision {percent(benchmark.macro.precision)}, recall {percent(benchmark.macro.recall)}, F1 {percent(benchmark.macro.f1)}. Micro precision {percent(benchmark.micro.precision)}, recall {percent(benchmark.micro.recall)}, F1 {percent(benchmark.micro.f1)}.</p><p>Rule {benchmark.rule_version} · policy version {benchmark.policy_version} · benchmark {benchmark.benchmark_id}</p>
    <div className="table-scroll" tabIndex={0} role="region" aria-label="Synthetic classification metrics"><table className="table"><caption>Per-class synthetic semantic metrics</caption><thead><tr><th>Class</th><th>Precision</th><th>Recall</th><th>F1</th><th>Support</th></tr></thead><tbody>{benchmark.classes.map(row => <tr key={row.label}><th scope="row">{row.label.replaceAll("_", " ")}</th><td>{percent(row.precision)}</td><td>{percent(row.recall)}</td><td>{percent(row.f1)}</td><td>{row.support}</td></tr>)}</tbody></table></div>
    <details><summary>Confusion matrix and benchmark identity</summary><p className="policy-formula">{benchmark.benchmark_hash}</p><div className="table-scroll" tabIndex={0} role="region" aria-label="Synthetic confusion matrix"><table className="table"><caption>Rows actual; columns predicted</caption><thead><tr><th>Actual / predicted</th>{Object.keys(benchmark.confusion_matrix).map(label => <th key={label}>{label.replaceAll("_", " ")}</th>)}</tr></thead><tbody>{Object.entries(benchmark.confusion_matrix).map(([label, row]) => <tr key={label}><th scope="row">{label.replaceAll("_", " ")}</th>{Object.entries(row).map(([predicted, count]) => <td key={predicted}>{count}</td>)}</tr>)}</tbody></table></div></details>
  </details>;
}
function ProposalReview({ proposal, catalogue, actor, busy, onMutation, onEdit }: { proposal: PolicyProposal; catalogue: PolicyCatalogue; actor: AuthenticatedProfile; busy: boolean; onMutation: (run: () => Promise<PolicyCatalogue>) => Promise<boolean>; onEdit: (proposal: PolicyProposal) => void }) {
  const [impact, setImpact] = useState<PolicyImpact | null>(null); const [error, setError] = useState<string | null>(null); const [reason, setReason] = useState(""); const [loading, setLoading] = useState(false); const abort = useRef<AbortController | null>(null);
  useEffect(() => { setImpact(null); setError(null); setLoading(false); return () => abort.current?.abort(); }, [proposal.version, catalogue.version, actor.user_id]);
  const stale = proposal.base_active_version !== catalogue.active_version; const owner = proposal.proposer_id === actor.user_id; const decider = actor.capabilities.includes("POLICY_APPROVE") && !owner && proposal.status === "PENDING_APPROVAL" && !stale;
  async function simulate() { abort.current?.abort(); const controller = new AbortController(); abort.current = controller; setLoading(true); setError(null); try { const value = await fetchPolicyImpact(proposal.proposal_id, controller.signal); if (!controller.signal.aborted) setImpact(value); } catch { if (!controller.signal.aborted) setError("Impact is unavailable. Check proposed values and retry."); } finally { if (!controller.signal.aborted) setLoading(false); } }
  const baseRules = proposal.base_active_version === catalogue.active_version ? catalogue.rules : catalogue.superseded_versions?.find(version => version.version === proposal.base_active_version)?.rules;
  const changed = proposal.rules.filter(rule => JSON.stringify(rule.value) !== JSON.stringify(baseRules?.find(base => base.policy_id === rule.policy_id)?.value));
  return <article className="card policy-proposal"><h3>Proposal · {proposal.status.replaceAll("_", " ")}</h3><p>Proposer: {proposal.proposer_id} · base active version {proposal.base_active_version} · proposal version {proposal.version}</p><p>Created {new Date(proposal.created_at).toLocaleString()} · {proposal.reason}</p>{stale && <p role="status">This proposal has a stale base version. Create a new proposal against the active policy.</p>}
    <div className="policy-card-grid">{changed.map(rule => <div key={rule.policy_id}><strong>{rule.name}</strong><p>Base: {baseRules?.find(base => base.policy_id === rule.policy_id) ? displayPolicyValue(baseRules.find(base => base.policy_id === rule.policy_id)!.value) : "Retained base unavailable"} · Current: {displayPolicyValue(catalogue.rules.find(base => base.policy_id === rule.policy_id)!.value)} · Default: {displayPolicyValue(rule.default_value)} · Proposed: {displayPolicyValue(rule.value)}</p><p>Affects: {policyExplanation(rule).affects}</p></div>)}</div>
    <div className="policy-actions">{owner && actor.capabilities.includes("POLICY_MUTATE") && proposal.status === "DRAFT" && !stale && <><button type="button" className="btn btn-secondary" disabled={busy} onClick={() => onEdit(proposal)}>Edit draft</button><button type="button" className="btn btn-primary" disabled={busy} onClick={() => void onMutation(() => submitPolicyProposal(proposal.proposal_id, catalogue.version, proposal.version))}>Submit for approval</button></>}<button type="button" className="btn btn-secondary" disabled={busy || loading} onClick={() => void simulate()}>{loading ? "Evaluating…" : "Evaluate synthetic impact"}</button></div>{error && <p role="status">{error}</p>}
    {impact && <section aria-label="Policy impact comparison"><p>{impact.label}</p><div className="policy-card-grid">{(["before", "after"] as const).map(side => <section key={side}><h4>{side === "before" ? "Before: active policy" : "After: proposed policy"}</h4><p>Registry freshness: {impact[side].runtime.registry_freshness_seconds / 86400} days · not-found TTL: {impact[side].runtime.not_found_ttl_seconds} seconds</p><p>Document confidence 0.84 / 0.85 / 0.90: {impact[side].runtime.document_auto_confirm.map(v => v ? "continue" : "review").join(" / ")}</p><p>Numeric ownership 24.999999% / 25% / 30%: {impact[side].runtime.ownership_numeric_candidates.map(v => v ? "candidate" : "below threshold").join(" / ")}</p><ClassifierMetrics benchmark={impact[side].classifier} /></section>)}</div></section>}
    {decider && <div className="policy-editor"><label>Decision reason<textarea value={reason} onChange={event => setReason(event.target.value)} minLength={10} maxLength={240} disabled={busy} /></label><p>Approval affects new cases only. Review synthetic impact before deciding.</p><div className="policy-actions">{[true, false].map(approve => <button key={String(approve)} type="button" className={approve ? "btn btn-primary" : "btn btn-secondary"} disabled={busy || reason.trim().length < 10 || !impact || impact.stale} onClick={() => void onMutation(() => decidePolicyProposal(proposal.proposal_id, catalogue.version, proposal.version, approve, reason.trim()))}>{approve ? "Approve and activate" : "Reject proposal"}</button>)}</div></div>}
    {owner && proposal.status === "PENDING_APPROVAL" && actor.capabilities.includes("POLICY_APPROVE") && <p>Four-eyes control: another Director must decide this proposal.</p>}{proposal.decided_by && <p>Decision by {proposal.decided_by} at {new Date(proposal.decided_at!).toLocaleString()} · {proposal.decision_reason}{proposal.activated_version ? ` · activated version ${proposal.activated_version}` : ""}</p>}
  </article>;
}
export default function PolicyRules({ actor }: { actor: AuthenticatedProfile }) {
  const [catalogue, setCatalogue] = useState<PolicyCatalogue | null>(null); const [benchmark, setBenchmark] = useState<ClassifierBenchmark | null>(null); const [error, setError] = useState<string | null>(null); const [busy, setBusy] = useState(false); const [changes, setChanges] = useState<Record<string, PolicyValue>>({}); const [reason, setReason] = useState(""); const [draft, setDraft] = useState<PolicyProposal | null>(null); const [confirmation, setConfirmation] = useState<PolicyResetConfirmation | null>(null);
  const guard = useRef(false); const generation = useRef(0); const resetTrigger = useRef<HTMLElement | null>(null); const canPropose = actor.capabilities.includes("POLICY_MUTATE");
  useEffect(() => { const current = ++generation.current; const controller = new AbortController(); setCatalogue(null); setBenchmark(null); setChanges({}); setReason(""); setDraft(null); setConfirmation(null); guard.current = false; setBusy(false); setError(null);
    void Promise.all([fetchPolicies(controller.signal), fetchClassifierBenchmark(controller.signal)]).then(([value, metrics]) => { if (!controller.signal.aborted && current === generation.current) { setCatalogue(value); setBenchmark(metrics); } }).catch(() => { if (!controller.signal.aborted) setError("Policy is temporarily unavailable."); });
    return () => { controller.abort(); generation.current++; };
  }, [actor.user_id, actor.role, actor.capabilities]);
  async function mutate(run: () => Promise<PolicyCatalogue>): Promise<boolean> { if (!beginPolicyMutation(guard)) return false; const current = generation.current; setBusy(true); try { const result = await executePolicyMutation(run, fetchPolicies, "Policy proposal could not be saved."); if (current !== generation.current) return false; if (result.catalogue) setCatalogue(result.catalogue); setError(result.error); if (result.succeeded) { setChanges({}); setDraft(null); setReason(""); try { const metrics = await fetchClassifierBenchmark(); if (current === generation.current) setBenchmark(metrics); } catch { if (current === generation.current) setError("Policy saved; benchmark is temporarily unavailable."); } } return result.succeeded; } finally { if (current === generation.current) { guard.current = false; setBusy(false); } } }
  async function save(event: FormEvent) { event.preventDefault(); if (!catalogue || busy) return; await mutate(() => savePolicyProposal({ expected_catalogue_version: catalogue.version, expected_proposal_version: draft?.version, changes: proposalEditChanges(catalogue, draft, changes), reason: reason.trim() }, draft?.proposal_id)); }
  function edit(proposal: PolicyProposal) { setDraft(proposal); setReason(proposal.reason); setChanges(Object.fromEntries(proposal.rules.filter(rule => JSON.stringify(rule.value) !== JSON.stringify(catalogue?.rules.find(base => base.policy_id === rule.policy_id)?.value)).map(rule => [rule.policy_id, rule.value]))); }
  function closeReset() { setConfirmation(null); resetTrigger.current?.focus(); }
  function confirmReset() { if (!catalogue || !confirmation) return; const rules = confirmation.kind === "single" ? [confirmation.rule] : catalogue.rules.filter(rule => policyIsEditable(rule, true)); setChanges(current => ({ ...current, ...Object.fromEntries(rules.map(rule => [rule.policy_id, rule.default_value])) })); closeReset(); }
  const groups = catalogue ? [...new Set(catalogue.rules.map(rule => policyCategory(rule)))] : [];
  return <div className="ds-root ds-page policy-control-plane"><h1>Policy and rules</h1><p>Active policy applies to new cases. In-flight and completed cases keep their frozen policy. HR proposes; an independent Director approves or rejects.</p>{error && <div className="ds-banner ds-banner-warn" role="status">{error}</div>}{!catalogue && !error && <p>Loading policy…</p>}
    {catalogue && <><section className="card"><h2>Active policy · version {catalogue.active_version ?? catalogue.version}</h2><p>{catalogue.active_origin ?? "DEFAULT"} · {catalogue.active_effective_at ? new Date(catalogue.active_effective_at).toLocaleString() : "Project baseline"}</p><details><summary>Active policy identity</summary><p className="policy-formula">{catalogue.active_identity}</p></details></section>
      {canPropose && <form className="card policy-editor" onSubmit={event => void save(event)}><h2>{draft ? "Edit policy draft" : "Prepare policy proposal"}</h2><p>Choose proposed values below. Reset stages defaults for approval.</p>{Object.entries(changes).map(([id, value]) => <p key={id}><strong>{catalogue.rules.find(rule => rule.policy_id === id)?.name}</strong> · proposed {displayPolicyValue(value)} <button type="button" className="btn btn-ghost" onClick={() => setChanges(current => { const next = { ...current }; delete next[id]; return next; })} disabled={busy}>Remove proposed change</button></p>)}<label htmlFor="policy-proposal-reason">Change reason</label><textarea id="policy-proposal-reason" value={reason} onChange={event => setReason(event.target.value)} minLength={10} maxLength={240} required disabled={busy} /><div className="policy-actions"><button type="submit" className="btn btn-primary" disabled={busy || (!Object.keys(changes).length && !draft) || reason.trim().length < 10}>{busy ? "Saving…" : "Save draft"}</button><button type="button" className="btn btn-secondary" disabled={busy} onClick={() => { resetTrigger.current = document.activeElement as HTMLElement; setConfirmation({ kind: "all" }); }}>Reset business parameters to defaults</button>{draft && <button type="button" className="btn btn-ghost" onClick={() => { setDraft(null); setChanges({}); setReason(""); }}>Cancel draft edit</button>}</div></form>}
      {groups.map(group => <details key={group} className="policy-category" open={group === "Documents & Reconciliation" || group === "Registry & External Data"}><summary>{group}</summary><PolicyTable catalogue={{ ...catalogue, rules: catalogue.rules.filter(rule => policyCategory(rule) === group) }} canMutate={canPropose && !busy} onSave={async (rule, value) => { setChanges(current => ({ ...current, [rule.policy_id]: value })); return true; }} onReset={rule => { resetTrigger.current = document.activeElement as HTMLElement; setConfirmation({ kind: "single", rule }); }} /></details>)}{benchmark && <ClassifierMetrics benchmark={benchmark} />}
      <section aria-label="Policy proposals and decisions"><h2>Proposals and decisions</h2>{!(catalogue.proposals?.length) && <p>No proposals yet.</p>}{[...(catalogue.proposals ?? [])].reverse().map(proposal => <ProposalReview key={proposal.proposal_id} proposal={proposal} catalogue={catalogue} actor={actor} busy={busy} onMutation={mutate} onEdit={edit} />)}</section><details className="card"><summary>Superseded active policies</summary>{catalogue.superseded_versions?.map(version => <p key={version.version}>Version {version.version} · SUPERSEDED at {new Date(version.superseded_at).toLocaleString()}</p>)}</details>
    </>}{confirmation && <PolicyResetDialog confirmation={confirmation} busy={busy} onCancel={closeReset} onConfirm={confirmReset} />}
  </div>;
}
