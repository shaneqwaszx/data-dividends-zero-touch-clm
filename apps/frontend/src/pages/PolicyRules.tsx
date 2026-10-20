import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { ApiError, fetchPolicies, savePolicyProposal, submitPolicyProposal, decidePolicyProposal, fetchPolicyImpact, fetchClassifierBenchmark } from "../api";
import type { AuthenticatedProfile, PolicyCatalogue, PolicyRule, PolicyValue, PolicyProposal, PolicyImpact, ClassifierBenchmark } from "../types";

import PolicyImpactComparison from "./PolicyImpactComparison";

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

// Presentation-only helpers: they format values and filter the view; they never change what is proposed or saved.
const POLICY_UNITS: Record<string, string> = { REGISTRY_FRESHNESS_DAYS: "days", REGISTRY_NOT_FOUND_TTL_SECONDS: "seconds", OWNERSHIP_UBO_THRESHOLD_PERCENT: "%" };
export function formatPolicyValue(rule: PolicyRule, value: PolicyValue): string {
  const unit = POLICY_UNITS[rule.policy_id];
  const text = displayPolicyValue(value);
  return unit ? (unit === "%" ? `${text}%` : `${text} ${unit}`) : text;
}
export function policyRangeHint(rule: PolicyRule): string | null {
  if (rule.minimum == null || rule.maximum == null) return null;
  const unit = POLICY_UNITS[rule.policy_id];
  return `Allowed ${rule.minimum} – ${rule.maximum}${unit ? (unit === "%" ? "%" : ` ${unit}`) : ""}`;
}
export function policyDiffersFromDefault(rule: PolicyRule): boolean { return JSON.stringify(rule.value) !== JSON.stringify(rule.default_value); }
export type PolicyRuleFilter = "all" | "editable" | "changed" | "staged";
export function policyMatchesView(rule: PolicyRule, filter: PolicyRuleFilter, search: string, staged: Record<string, PolicyValue>): boolean {
  const query = search.trim().toLowerCase();
  if (query && !`${rule.name} ${rule.description}`.toLowerCase().includes(query)) return false;
  if (filter === "editable") return policyIsEditable(rule, true);
  if (filter === "changed") return policyDiffersFromDefault(rule);
  if (filter === "staged") return rule.policy_id in staged;
  return true;
}
function plural(count: number, word: string): string { return `${count} ${word}${count === 1 ? "" : "s"}`; }

export function PolicyTable({ catalogue, canMutate, onSave, onReset, staged = {} }: { catalogue: PolicyCatalogue; canMutate: boolean; onSave: (rule: PolicyRule, value: PolicyValue) => Promise<boolean>; onReset: (rule: PolicyRule) => void; staged?: Record<string, PolicyValue> }) {
  const business = catalogue.rules.filter(rule => policyIsEditable(rule, true));
  const fixed = catalogue.rules.filter(rule => !policyIsEditable(rule, true));
  const card = (rule: PolicyRule) => <PolicyCard key={rule.policy_id} rule={rule} canMutate={canMutate} onSave={onSave} onReset={onReset} staged={staged[rule.policy_id]} />;
  return <div className="policy-rule-list">
    <div className="policy-rule-list__head" aria-hidden="true"><span>Rule</span><span className="policy-rule-list__values"><span>Current</span><span>Default</span><span>Proposed</span></span><span className="policy-rule-list__action">Action</span></div>
    {business.map(card)}
    {business.length > 0 && fixed.length > 0 && <p className="policy-rule-list__divider">Fixed definitions · not editable</p>}
    {fixed.map(card)}
  </div>;
}
function PolicyCard({ rule, canMutate, onSave, onReset, staged }: { rule: PolicyRule; canMutate: boolean; onSave: (rule: PolicyRule, value: PolicyValue) => Promise<boolean>; onReset: (rule: PolicyRule) => void; staged?: PolicyValue }) {
  const [editing, setEditing] = useState(false); const [value, setValue] = useState(displayPolicyValue(rule.value)); const [busy, setBusy] = useState(false);
  useEffect(() => { setValue(displayPolicyValue(rule.value)); setEditing(false); }, [rule]);
  const explanation = policyExplanation(rule);
  async function save(event: FormEvent) { event.preventDefault(); if (busy) return; setBusy(true); try { if (await onSave(rule, parsePolicyValueInput(rule, value))) setEditing(false); } finally { setBusy(false); } }
  const fixed = !policyIsEditable(rule, true); const range = policyRangeHint(rule); const hintId = `policy-hint-${rule.policy_id}`;
  const enforcement = rule.enforcement === "DISPLAY_SHOWCASE_ONLY" ? "Showcase only · Not runtime enforced" : rule.enforcement === "NOT_EDITABLE" ? "Fixed definition" : "Runtime enforced";
  return <article className={`policy-parameter${staged ? " policy-parameter--staged" : ""}${fixed ? " policy-parameter--fixed" : ""}`}>
    <div className="policy-parameter__rule"><h3>{rule.name}</h3><p>{rule.description}</p>
      <details className="policy-parameter__how"><summary>How it's calculated</summary>
        <p className="policy-formula"><strong>Formula:</strong> {explanation.formula}</p><p><strong>Affects:</strong> {explanation.affects}</p>
        <p className="text-muted">Rule version {rule.version} · {rule.authority?.replaceAll("_", " ") ?? "Project definition"} · {enforcement}</p>
      </details>
    </div>
    <dl className="policy-values">
      <div><dt>Current</dt><dd>{formatPolicyValue(rule, rule.value)}{policyDiffersFromDefault(rule) && <span className="tag tag-neutral policy-tag">Modified</span>}</dd></div>
      <div><dt>Default</dt><dd>{formatPolicyValue(rule, rule.default_value)}</dd></div>
      <div><dt>Proposed</dt><dd>{staged ? <span className="policy-staged-value">{formatPolicyValue(rule, rule.value)} → {formatPolicyValue(rule, staged)}</span> : <><span aria-hidden="true" className="text-muted">—</span><span className="sr-only">No staged change</span></>}</dd></div>
    </dl>
    <div className="policy-parameter__actions">
      {fixed && <span className="policy-fixed-label"><svg aria-hidden="true" width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.4"><rect x="2.5" y="5.5" width="7" height="5" rx="1" /><path d="M4 5.5V4a2 2 0 014 0v1.5" /></svg>{enforcement}</span>}
      {policyIsEditable(rule, canMutate) && (editing ? <form onSubmit={event => void save(event)} className="policy-editor policy-inline-editor"><label>Proposed value for {rule.name}{rule.value_type === "BOOLEAN" ? <select value={value} onChange={event => setValue(event.target.value)} disabled={busy}><option value="true">true</option><option value="false">false</option></select> : <input value={value} onChange={event => setValue(event.target.value)} type="number" step={rule.value_type === "INTEGER" ? "1" : "0.000001"} min={rule.minimum ?? undefined} max={rule.maximum ?? undefined} required disabled={busy} aria-describedby={range ? hintId : undefined} />}</label>{range && <span id={hintId} className="policy-hint">{range}</span>}<div className="policy-actions"><button className="btn btn-secondary" disabled={busy} type="submit">Use proposed value</button><button className="btn btn-ghost" disabled={busy} type="button" onClick={() => setEditing(false)}>Cancel edit</button></div></form> : <div className="policy-actions"><button className="btn btn-secondary" type="button" onClick={() => setEditing(true)}>Propose change</button><button className="btn btn-ghost" type="button" onClick={() => onReset(rule)}>Reset to default</button></div>)}
    </div>
  </article>;
}
const percent = (value: number) => `${(value * 100).toFixed(1)}%`;
export function ClassifierMetrics({ benchmark, policyVersionLabel = "policy version" }: { benchmark: ClassifierBenchmark; policyVersionLabel?: string }) {
  return <details className="card policy-metrics"><summary>{benchmark.label} · labelled synthetic benchmark</summary><p>{benchmark.scope}. Support {benchmark.support}; exact accuracy {percent(benchmark.exact_accuracy)}.</p>
    <p>Macro precision {percent(benchmark.macro.precision)}, recall {percent(benchmark.macro.recall)}, F1 {percent(benchmark.macro.f1)}. Micro precision {percent(benchmark.micro.precision)}, recall {percent(benchmark.micro.recall)}, F1 {percent(benchmark.micro.f1)}.</p><p>Rule {benchmark.rule_version} · {policyVersionLabel} {benchmark.policy_version} · benchmark {benchmark.benchmark_id}</p>
    <div className="table-scroll" tabIndex={0} role="region" aria-label="Synthetic classification metrics"><table className="table"><caption>Per-class synthetic semantic metrics</caption><thead><tr><th>Class</th><th>Precision</th><th>Recall</th><th>F1</th><th>Support</th></tr></thead><tbody>{benchmark.classes.map(row => <tr key={row.label}><th scope="row">{row.label.replaceAll("_", " ")}</th><td>{percent(row.precision)}</td><td>{percent(row.recall)}</td><td>{percent(row.f1)}</td><td>{row.support}</td></tr>)}</tbody></table></div>
    <details><summary>Confusion matrix and benchmark identity</summary><p className="policy-formula">{benchmark.benchmark_hash}</p><div className="table-scroll" tabIndex={0} role="region" aria-label="Synthetic confusion matrix"><table className="table"><caption>Rows actual; columns predicted</caption><thead><tr><th>Actual / predicted</th>{Object.keys(benchmark.confusion_matrix).map(label => <th key={label}>{label.replaceAll("_", " ")}</th>)}</tr></thead><tbody>{Object.entries(benchmark.confusion_matrix).map(([label, row]) => <tr key={label}><th scope="row">{label.replaceAll("_", " ")}</th>{Object.entries(row).map(([predicted, count]) => <td key={predicted}>{count}</td>)}</tr>)}</tbody></table></div></details>
  </details>;
}
export function ProposalReview({ proposal, catalogue, actor, busy, onMutation, onEdit }: { proposal: PolicyProposal; catalogue: PolicyCatalogue; actor: AuthenticatedProfile; busy: boolean; onMutation: (run: () => Promise<PolicyCatalogue>) => Promise<boolean>; onEdit: (proposal: PolicyProposal) => void }) {
  const [impact, setImpact] = useState<PolicyImpact | null>(null); const [impactScope, setImpactScope] = useState("");
  const scope = JSON.stringify([proposal.proposal_id, proposal.version, catalogue.version, actor.user_id, actor.role, actor.team_id, actor.capabilities]); const [error, setError] = useState<string | null>(null); const [reason, setReason] = useState(""); const [loading, setLoading] = useState(false); const abort = useRef<AbortController | null>(null);
  useEffect(() => { setImpact(null); setError(null); setLoading(false); return () => abort.current?.abort(); }, [scope]);
  const stale = proposal.base_active_version !== catalogue.active_version; const owner = proposal.proposer_id === actor.user_id; const decider = actor.capabilities.includes("POLICY_APPROVE") && !owner && proposal.status === "PENDING_APPROVAL" && !stale;
  async function simulate() { abort.current?.abort(); const controller = new AbortController(); abort.current = controller; setLoading(true); setError(null); try { const value = await fetchPolicyImpact(proposal.proposal_id, controller.signal); if (!controller.signal.aborted) { if (value.proposal_id !== proposal.proposal_id || value.proposal_version !== proposal.version || value.catalogue_version !== catalogue.version) throw new Error("Impact identity changed"); setImpactScope(scope); setImpact(value); } } catch { if (!controller.signal.aborted) setError("Impact is unavailable. Check proposed values and retry."); } finally { if (!controller.signal.aborted) setLoading(false); } }
  const currentImpact = impactScope === scope ? impact : null;
  const baseRules = proposal.base_active_version === catalogue.active_version ? catalogue.rules : catalogue.superseded_versions?.find(version => version.version === proposal.base_active_version)?.rules;
  const changed = proposal.rules.filter(rule => JSON.stringify(rule.value) !== JSON.stringify(baseRules?.find(base => base.policy_id === rule.policy_id)?.value));
  const decisionBlocked = busy || reason.trim().length < 10 || !currentImpact || currentImpact.stale;
  const decisionHints = [!currentImpact ? "Run Simulate impact before deciding." : currentImpact.stale ? "The impact result is stale. Run Simulate impact again." : null, reason.trim().length < 10 ? "Enter a decision reason of at least 10 characters." : null].filter((hint): hint is string => hint !== null);
  const decisionHintId = `policy-decision-hint-${proposal.proposal_id}`;
  const simulateButton = <button type="button" className="btn btn-secondary" disabled={busy || loading} onClick={() => void simulate()}>{loading ? "Evaluating…" : "Simulate impact"}</button>;
  return <article className={`card policy-proposal policy-proposal--${proposal.status.toLowerCase().replaceAll("_", "-")}`}>
    <div className="policy-proposal__header"><h3>Proposal · {proposal.status.replaceAll("_", " ")}</h3>{stale && <span className="tag tag-neutral policy-tag">Stale base</span>}</div>
    <p className="policy-proposal__reason">{proposal.reason}</p>
    <p className="text-muted">Proposer: {proposal.proposer_id}{owner ? " (you)" : ""} · base active version {proposal.base_active_version} · proposal version {proposal.version} · created {new Date(proposal.created_at).toLocaleString()}</p>
    {stale && <p role="status">This proposal has a stale base version. Create a new proposal against the active policy.</p>}
    {changed.length ? <div className="table-scroll" tabIndex={0} role="region" aria-label={`Proposed changes, proposal version ${proposal.version}`}><table className="table policy-proposal__changes"><caption>{plural(changed.length, "proposed change")}</caption>
      <thead><tr><th scope="col">Rule</th><th scope="col">Change</th><th scope="col">Current</th><th scope="col">Default</th><th scope="col">Affects</th></tr></thead>
      <tbody>{changed.map(rule => { const base = baseRules?.find(item => item.policy_id === rule.policy_id); return <tr key={rule.policy_id}><th scope="row">{rule.name}</th><td><span className="policy-diff__from">{base ? formatPolicyValue(rule, base.value) : "Retained base unavailable"}</span> <span aria-hidden="true">→</span><span className="sr-only">to</span> <strong>{formatPolicyValue(rule, rule.value)}</strong></td><td>{formatPolicyValue(rule, catalogue.rules.find(item => item.policy_id === rule.policy_id)!.value)}</td><td>{formatPolicyValue(rule, rule.default_value)}</td><td>{policyExplanation(rule).affects}</td></tr>; })}</tbody>
    </table></div> : <p className="text-muted">No parameter differences from the base version.</p>}
    {decider ? <div className="policy-decision-step"><h4><span className="policy-step-number" aria-hidden="true">1</span>Simulate impact {currentImpact && <span className={`tag policy-tag ${currentImpact.stale ? "tag-neutral" : "tag-accent"}`}>{currentImpact.stale ? "Stale" : "Up to date"}</span>}</h4><p className="text-muted">Runs the proposal against synthetic fixtures. Required before deciding.</p><div className="policy-actions">{simulateButton}</div></div>
      : <div className="policy-actions">{owner && actor.capabilities.includes("POLICY_MUTATE") && proposal.status === "DRAFT" && !stale && <><button type="button" className="btn btn-secondary" disabled={busy} onClick={() => onEdit(proposal)}>Edit draft</button><button type="button" className="btn btn-primary" disabled={busy} onClick={() => void onMutation(() => submitPolicyProposal(proposal.proposal_id, catalogue.version, proposal.version))}>Submit for approval</button></>}{simulateButton}</div>}
    {error && <p role="status">{error}</p>}
    {currentImpact && <PolicyImpactComparison impact={currentImpact} catalogue={catalogue} proposal={proposal} metrics={(benchmark, policyVersionLabel) => <ClassifierMetrics benchmark={benchmark} policyVersionLabel={policyVersionLabel} />} />}
    {decider && <div className="policy-editor policy-decision-step"><h4><span className="policy-step-number" aria-hidden="true">2</span>Decide</h4><label>Decision reason<textarea value={reason} onChange={event => setReason(event.target.value)} minLength={10} maxLength={240} disabled={busy} /></label><p className="policy-hint">{reason.trim().length} / 240 · minimum 10 characters</p><p>Approval affects new cases only. Review synthetic impact before deciding.</p><div className="policy-actions">{[true, false].map(approve => <button key={String(approve)} type="button" className={approve ? "btn btn-primary" : "btn btn-secondary"} disabled={decisionBlocked} aria-describedby={decisionHints.length ? decisionHintId : undefined} onClick={() => void onMutation(() => decidePolicyProposal(proposal.proposal_id, catalogue.version, proposal.version, approve, reason.trim()))}>{approve ? "Approve and activate" : "Reject proposal"}</button>)}</div>{decisionHints.length > 0 && <ul id={decisionHintId} className="policy-hint policy-blocked-hints">{decisionHints.map(hint => <li key={hint}>{hint}</li>)}</ul>}</div>}
    {owner && proposal.status === "PENDING_APPROVAL" && actor.capabilities.includes("POLICY_APPROVE") && <p>Four-eyes control: another Director must decide this proposal.</p>}{proposal.decided_by && <p>Decision by {proposal.decided_by} at {new Date(proposal.decided_at!).toLocaleString()} · {proposal.decision_reason}{proposal.activated_version ? ` · activated version ${proposal.activated_version}` : ""}</p>}
  </article>;
}
const EVIDENCE_CATEGORY = "Ownership Evidence Classification";
export default function PolicyRules({ actor }: { actor: AuthenticatedProfile }) {
  const [catalogue, setCatalogue] = useState<PolicyCatalogue | null>(null); const [benchmark, setBenchmark] = useState<ClassifierBenchmark | null>(null); const [error, setError] = useState<string | null>(null); const [busy, setBusy] = useState(false); const [changes, setChanges] = useState<Record<string, PolicyValue>>({}); const [reason, setReason] = useState(""); const [draft, setDraft] = useState<PolicyProposal | null>(null); const [confirmation, setConfirmation] = useState<PolicyResetConfirmation | null>(null);
  const [filter, setFilter] = useState<PolicyRuleFilter>("all"); const [search, setSearch] = useState(""); const proposalsSection = useRef<HTMLElement>(null);
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
  const narrowed = filter !== "all" || search.trim() !== "";
  const visibleRules = catalogue ? catalogue.rules.filter(rule => policyMatchesView(rule, filter, search, changes)) : [];
  const visibleGroups = groups.filter(group => visibleRules.some(rule => policyCategory(rule) === group));
  const stagedCount = Object.keys(changes).length;
  const saveBlocked = busy || (!Object.keys(changes).length && !draft) || reason.trim().length < 10;
  const saveHint = busy ? null : !Object.keys(changes).length && !draft ? "Stage at least one change with Propose change to save a draft." : reason.trim().length < 10 ? "Add a change reason of at least 10 characters to save." : null;
  const proposals = [...(catalogue?.proposals ?? [])].reverse();
  const awaitingDecision = catalogue ? proposals.filter(proposal => actor.capabilities.includes("POLICY_APPROVE") && proposal.proposer_id !== actor.user_id && proposal.status === "PENDING_APPROVAL" && proposal.base_active_version === catalogue.active_version).length : 0;
  const awaitingDirector = proposals.filter(proposal => proposal.proposer_id === actor.user_id && proposal.status === "PENDING_APPROVAL").length;
  const proposalCard = (proposal: PolicyProposal) => catalogue && <ProposalReview key={JSON.stringify([proposal.proposal_id, proposal.version, catalogue.version, actor.user_id, actor.role, actor.team_id, actor.capabilities])} proposal={proposal} catalogue={catalogue} actor={actor} busy={busy} onMutation={mutate} onEdit={edit} />;
  const metrics = benchmark && <ClassifierMetrics benchmark={benchmark} />;
  const filters: { id: PolicyRuleFilter; label: string; count: number }[] = catalogue ? [
    { id: "all", label: "All rules", count: catalogue.rules.length },
    { id: "editable", label: "Editable", count: catalogue.rules.filter(rule => policyIsEditable(rule, true)).length },
    { id: "changed", label: "Changed from default", count: catalogue.rules.filter(policyDiffersFromDefault).length },
    ...(canPropose ? [{ id: "staged" as const, label: "Staged in draft", count: stagedCount }] : []),
  ] : [];
  return <div className="ds-root ds-page policy-control-plane"><h1>Policy and rules</h1><p>Active policy applies to new cases. In-flight and completed cases keep their frozen policy. HR proposes; an independent Director approves or rejects.</p>{error && <div className="ds-banner ds-banner-warn" role="status">{error}</div>}{!catalogue && !error && <p>Loading policy…</p>}
    {catalogue && <><section className="card policy-active-summary"><div className="policy-active-summary__main"><h2>Active policy · version {catalogue.active_version ?? catalogue.version}</h2><p className="text-muted">{catalogue.active_origin ?? "DEFAULT"} · {catalogue.active_effective_at ? new Date(catalogue.active_effective_at).toLocaleString() : "Project baseline"}</p></div><details><summary>Active policy identity</summary><p className="policy-formula">{catalogue.active_identity}</p></details></section>
      {(awaitingDecision > 0 || awaitingDirector > 0) && <div className="policy-attention"><p>{awaitingDecision > 0 ? `${plural(awaitingDecision, "proposal")} awaiting your decision.` : `${plural(awaitingDirector, "proposal")} you submitted ${awaitingDirector === 1 ? "is" : "are"} awaiting an independent Director.`}</p><button type="button" className="btn btn-secondary" onClick={() => { proposalsSection.current?.scrollIntoView({ block: "start" }); proposalsSection.current?.focus(); }}>Go to proposals</button></div>}
      <div className="policy-toolbar"><div className="policy-filters" role="group" aria-label="Filter policy rules">{filters.map(item => <button key={item.id} type="button" className={`policy-filter${filter === item.id ? " policy-filter--active" : ""}`} aria-pressed={filter === item.id} onClick={() => setFilter(item.id)}>{item.label} · {item.count}</button>)}</div>
        <label className="policy-search">Search rules<input type="search" value={search} onChange={event => setSearch(event.target.value)} placeholder="Rule name or description" /></label></div>
      {visibleGroups.length === 0 && <p className="card">No rules match this filter.</p>}
      {visibleGroups.map(group => { const rules = catalogue.rules.filter(rule => policyCategory(rule) === group); const shown = visibleRules.filter(rule => policyCategory(rule) === group); const staged = rules.filter(rule => rule.policy_id in changes).length; const modified = rules.filter(policyDiffersFromDefault).length; const formulas = [...new Set(rules.filter(rule => policyIsEditable(rule, true)).map(rule => policyExplanation(rule).formula))];
        return <details key={group} className="policy-category" open={narrowed || group === "Documents & Reconciliation" || group === "Registry & External Data"}><summary><span className="policy-category__title">{group}</span><span className="policy-category__meta">{plural(rules.length, "rule")} · {rules.filter(rule => policyIsEditable(rule, true)).length} editable</span>{staged > 0 && <span className="tag tag-accent policy-tag">{staged} staged</span>}{modified > 0 && <span className="tag tag-neutral policy-tag">{modified} changed from default</span>}</summary>
          {formulas.length === 1 && rules.filter(rule => policyIsEditable(rule, true)).length > 1 && <p className="policy-category__formula"><strong>Shared formula:</strong> {formulas[0]}</p>}
          <PolicyTable catalogue={{ ...catalogue, rules: shown }} canMutate={canPropose && !busy} staged={changes} onSave={async (rule, value) => { setChanges(current => ({ ...current, [rule.policy_id]: value })); return true; }} onReset={rule => { resetTrigger.current = document.activeElement as HTMLElement; setConfirmation({ kind: "single", rule }); }} />
          {group === EVIDENCE_CATEGORY && metrics}
        </details>; })}
      {!visibleGroups.includes(EVIDENCE_CATEGORY) && metrics}
      {canPropose && <form className={`card policy-editor policy-draft-tray${stagedCount || draft ? " policy-draft-tray--active" : ""}`} onSubmit={event => void save(event)}><div className="policy-draft-tray__header"><h2>{draft ? "Edit policy draft" : "Prepare policy proposal"}</h2><span className="tag tag-accent policy-tag">{plural(stagedCount, "change")} staged</span></div>
        {stagedCount ? <ul className="policy-draft-tray__changes">{Object.entries(changes).map(([id, value]) => <li key={id}><span><strong>{catalogue.rules.find(rule => rule.policy_id === id)?.name}</strong> · proposed {displayPolicyValue(value)}</span> <button type="button" className="btn btn-ghost" onClick={() => setChanges(current => { const next = { ...current }; delete next[id]; return next; })} disabled={busy}>Remove proposed change</button></li>)}</ul> : <p className="text-muted">No changes staged. Use Propose change on a rule; reset stages defaults for approval.</p>}
        <div className="policy-draft-tray__reason"><label htmlFor="policy-proposal-reason">Change reason</label><textarea id="policy-proposal-reason" value={reason} onChange={event => setReason(event.target.value)} minLength={10} maxLength={240} required disabled={busy} aria-describedby="policy-proposal-reason-count" /><span id="policy-proposal-reason-count" className="policy-hint">{reason.trim().length} / 240 · minimum 10 characters</span></div>
        <div className="policy-actions"><button type="submit" className="btn btn-primary" disabled={saveBlocked} aria-describedby={saveHint ? "policy-save-hint" : undefined}>{busy ? "Saving…" : "Save draft"}</button>{draft && <button type="button" className="btn btn-ghost" onClick={() => { setDraft(null); setChanges({}); setReason(""); }}>Cancel draft edit</button>}<button type="button" className="btn btn-ghost policy-draft-tray__reset" disabled={busy} onClick={() => { resetTrigger.current = document.activeElement as HTMLElement; setConfirmation({ kind: "all" }); }}>Reset business parameters to defaults</button></div>
        {saveHint && <p id="policy-save-hint" className="policy-hint">{saveHint}</p>}</form>}
      <section ref={proposalsSection} tabIndex={-1} className="policy-proposals" aria-label="Policy proposals and decisions"><h2>Proposals and decisions</h2>{!proposals.length && <p>No proposals yet.</p>}
        {proposals.map(proposalCard)}
      </section>
      <details className="card policy-history"><summary>Superseded active policies · {catalogue.superseded_versions?.length ?? 0}</summary>{catalogue.superseded_versions?.length ? catalogue.superseded_versions.map(version => <p key={version.version}>Version {version.version} · SUPERSEDED at {new Date(version.superseded_at).toLocaleString()}</p>) : <p className="text-muted">No superseded versions yet.</p>}</details>
    </>}{confirmation && <PolicyResetDialog confirmation={confirmation} busy={busy} onCancel={closeReset} onConfirm={confirmReset} />}
  </div>;
}
