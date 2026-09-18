import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import { ApiError, createShowcasePolicy, fetchPolicies, resetAllPolicies, resetPolicy, updatePolicy } from "../api";
import type { AuthenticatedProfile, PolicyCatalogue, PolicyRule, PolicyValue } from "../types";

export function displayPolicyValue(value: PolicyValue): string {
  return Array.isArray(value.value) ? value.value.join(", ") : String(value.value);
}

export function policyIsEditable(rule: PolicyRule, canMutate: boolean): boolean {
  return canMutate && rule.enforcement !== "NOT_EDITABLE";
}

export function parsePolicyValueInput(rule: PolicyRule, value: string): PolicyValue {
  switch (rule.value_type) {
    case "BOOLEAN":
      return { type: "BOOLEAN", value: value === "true" };
    case "INTEGER":
      return { type: "INTEGER", value: Number.parseInt(value, 10) };
    case "DECIMAL":
      return { type: "DECIMAL", value };
    case "STRING_LIST":
      return { type: "STRING_LIST", value: value.split(",").map((item) => item.trim()).filter(Boolean) };
    case "STRING":
      return { type: "STRING", value };
  }
}

export function beginPolicyMutation(guard: { current: boolean }): boolean {
  if (guard.current) return false;
  guard.current = true;
  return true;
}

export function shouldCancelPolicyReset(key: string, busy: boolean): boolean {
  return key === "Escape" && !busy;
}

export async function executePolicyMutation(
  mutation: () => Promise<PolicyCatalogue>,
  refresh: () => Promise<PolicyCatalogue>,
  failureMessage: string,
): Promise<{ succeeded: boolean; catalogue?: PolicyCatalogue; error: string | null }> {
  try {
    return { succeeded: true, catalogue: await mutation(), error: null };
  } catch (reason) {
    if (reason instanceof ApiError && reason.status === 409) {
      try {
        return {
          succeeded: false,
          catalogue: await refresh(),
          error: "The policy catalogue changed. Review the refreshed values before trying again.",
        };
      } catch {
        return {
          succeeded: false,
          error: "The policy catalogue changed, but refreshed values are temporarily unavailable.",
        };
      }
    }
    return {
      succeeded: false,
      error: reason instanceof ApiError ? reason.message : failureMessage,
    };
  }
}

export function PolicyClassificationBadge({ classification }: { classification: string }) {
  return <span className={`policy-classification policy-classification--${classification.toLowerCase().replaceAll(" ", "-")}`}>{classification}</span>;
}

export type PolicyResetConfirmation = { kind: "single"; rule: PolicyRule } | { kind: "all" };

export function PolicyResetDialog({ confirmation, busy, onCancel, onConfirm }: {
  confirmation: PolicyResetConfirmation;
  busy: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const cancelRef = useRef<HTMLButtonElement>(null);
  const single = confirmation.kind === "single";
  const titleId = "policy-reset-title";
  const descriptionId = "policy-reset-description";

  useEffect(() => {
    cancelRef.current?.focus();
  }, []);

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (shouldCancelPolicyReset(event.key, busy)) {
      event.preventDefault();
      onCancel();
    }
  }

  return (
    <div className="dialog-backdrop" role="presentation">
      <div className="dialog" role="alertdialog" aria-modal="true" aria-labelledby={titleId} aria-describedby={descriptionId} onKeyDown={handleKeyDown}>
        <h2 className="dialog-title" id={titleId}>{single ? `Reset ${confirmation.rule.name} to default?` : "Reset all policies to defaults?"}</h2>
        <div className="dialog-body" id={descriptionId}>
          {single
            ? <p>The current value will be replaced by the project/POC default. This is not a claim of sponsor-approved production policy.</p>
            : <p>Project/POC defaults will be restored. Custom showcase rules remain. Runtime policy changes apply only to future cases through immutable case snapshots; existing cases are not reinterpreted.</p>}
        </div>
        <div className="dialog-actions">
          <button ref={cancelRef} type="button" className="btn btn-ghost" onClick={onCancel} disabled={busy}>Cancel</button>
          <button type="button" className="btn btn-primary" onClick={onConfirm} disabled={busy}>{busy ? "Resetting…" : "Confirm reset"}</button>
        </div>
      </div>
    </div>
  );
}

function PolicyRow({ catalogue, rule, canMutate, onSave, onReset }: {
  catalogue: PolicyCatalogue;
  rule: PolicyRule;
  canMutate: boolean;
  onSave: (rule: PolicyRule, value: PolicyValue, name?: string, description?: string) => Promise<boolean>;
  onReset: (rule: PolicyRule) => void;
}) {
  const [value, setValue] = useState(displayPolicyValue(rule.value));
  const [name, setName] = useState(rule.name);
  const [description, setDescription] = useState(rule.description);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const editable = policyIsEditable(rule, canMutate);
  const showcase = rule.enforcement === "DISPLAY_SHOWCASE_ONLY";

  useEffect(() => {
    setValue(displayPolicyValue(rule.value));
    setName(rule.name);
    setDescription(rule.description);
    setEditing(false);
    setSaving(false);
  }, [catalogue.version, rule.description, rule.name, rule.value, rule.version]);

  async function save() {
    if (saving) return;
    setSaving(true);
    const succeeded = await onSave(rule, parsePolicyValueInput(rule, value), showcase ? name : undefined, showcase ? description : undefined);
    if (!succeeded) setSaving(false);
  }

  return (
    <tr>
      <td>
        {editing && showcase
          ? <><input aria-label={`${rule.policy_id} name`} value={name} onChange={(event) => setName(event.target.value)} /><textarea aria-label={`${rule.policy_id} description`} value={description} onChange={(event) => setDescription(event.target.value)} /></>
          : <><strong>{rule.name}</strong><div className="text-muted">{rule.description}</div></>}
      </td>
      <td>{editing ? <input aria-label={`${rule.name} value`} value={value} onChange={(event) => setValue(event.target.value)} /> : displayPolicyValue(rule.value)}</td>
      <td>{rule.value_type}</td>
      <td>{rule.classifications.join(" · ")}</td>
      <td>{showcase ? "Showcase only · Not runtime enforced" : rule.enforcement.replaceAll("_", " ")}</td>
      <td>{rule.version}</td>
      <td>{editable && (editing
        ? <><button type="button" className="btn btn-secondary" disabled={saving} onClick={() => void save()}>{saving ? "Saving…" : "Save"}</button><button type="button" className="btn btn-ghost" disabled={saving} onClick={() => setEditing(false)}>Cancel edit</button></>
        : <><button type="button" className="btn btn-secondary" onClick={() => setEditing(true)}>Edit</button><button type="button" className="btn btn-ghost" onClick={() => onReset(rule)}>Reset to default</button></>)}</td>
    </tr>
  );
}

export function PolicyTable({ catalogue, canMutate, onSave, onReset }: {
  catalogue: PolicyCatalogue;
  canMutate: boolean;
  onSave: (rule: PolicyRule, value: PolicyValue, name?: string, description?: string) => Promise<boolean>;
  onReset: (rule: PolicyRule) => void;
}) {
  return (
    <div className="table-card table-scroll" tabIndex={0}>
      <table className="table"><thead><tr><th>Rule</th><th>Value</th><th>Type</th><th>Classification</th><th>Enforcement</th><th>Version</th><th>Actions</th></tr></thead>
        <tbody>{catalogue.rules.map((rule) => <PolicyRow key={rule.policy_id} catalogue={catalogue} rule={rule} canMutate={canMutate} onSave={onSave} onReset={onReset} />)}</tbody>
      </table>
    </div>
  );
}

export default function PolicyRules({ actor }: { actor: AuthenticatedProfile }) {
  const [catalogue, setCatalogue] = useState<PolicyCatalogue | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmation, setConfirmation] = useState<PolicyResetConfirmation | null>(null);
  const [resetting, setResetting] = useState(false);
  const [creating, setCreating] = useState(false);
  const mutationInFlight = useRef(false);
  const canMutate = actor.capabilities.includes("POLICY_MUTATE");
  const [newPolicyId, setNewPolicyId] = useState("");
  const [newPolicyName, setNewPolicyName] = useState("");
  const [newPolicyValue, setNewPolicyValue] = useState("");

  async function loadCatalogue() {
    const authoritative = await fetchPolicies();
    setCatalogue(authoritative);
    return authoritative;
  }

  useEffect(() => {
    void loadCatalogue().then(() => setError(null)).catch((reason) => setError(reason instanceof ApiError ? reason.message : "Policy is unavailable."));
  }, []);

  async function applyMutation(mutation: () => Promise<PolicyCatalogue>, failureMessage: string): Promise<boolean> {
    const result = await executePolicyMutation(mutation, fetchPolicies, failureMessage);
    if (result.catalogue) setCatalogue(result.catalogue);
    setError(result.error);
    return result.succeeded;
  }

  async function saveRule(rule: PolicyRule, value: PolicyValue, name?: string, description?: string) {
    if (!catalogue) return false;
    return applyMutation(() => updatePolicy(rule.policy_id, {
      expected_catalogue_version: catalogue.version,
      expected_rule_version: rule.version,
      value,
      ...(name !== undefined ? { name } : {}),
      ...(description !== undefined ? { description } : {}),
    }), "Policy update failed.");
  }

  async function confirmReset() {
    if (!catalogue || !confirmation || !beginPolicyMutation(mutationInFlight)) return;
    setResetting(true);
    const selected = confirmation;
    await applyMutation(
      selected.kind === "single"
        ? () => resetPolicy(selected.rule.policy_id, catalogue.version, selected.rule.version)
        : () => resetAllPolicies(catalogue.version),
      "Policy reset failed.",
    );
    mutationInFlight.current = false;
    setResetting(false);
    setConfirmation(null);
  }

  async function createShowcase(event: FormEvent) {
    event.preventDefault();
    if (!catalogue || creating) return;
    setCreating(true);
    const succeeded = await applyMutation(() => createShowcasePolicy({
      expected_catalogue_version: catalogue.version,
      policy_id: newPolicyId,
      category: "Demonstration",
      name: newPolicyName,
      description: "Display-only custom demonstration rule; not runtime enforced.",
      value: { type: "STRING", value: newPolicyValue },
    }), "Policy creation failed.");
    if (succeeded) {
      setNewPolicyId("");
      setNewPolicyName("");
      setNewPolicyValue("");
    }
    setCreating(false);
  }

  return (
    <div className="ds-root ds-page">
      <div className="page-heading-row">
        <div><h1>Policy and rules</h1><p className="text-muted">Persistent typed catalogue. Runtime-enforced edits bind only to cases created afterwards.</p></div>
        {canMutate && <button type="button" className="btn btn-secondary" onClick={() => setConfirmation({ kind: "all" })}>Reset all to defaults</button>}
      </div>
      <div className="ds-banner policy-open-questions"><strong>Truthful scope</strong><span>Showcase-only rules are display metadata and never alter onboarding execution.</span></div>
      {error && <div className="ds-banner ds-banner-warn" role="status">{error}</div>}
      {!catalogue && !error && <p className="text-muted">Loading policy…</p>}
      {catalogue && <>
        {canMutate && <form className="card form-row" onSubmit={(event) => void createShowcase(event)}>
          <strong>Add display-only rule</strong>
          <input aria-label="Policy ID" placeholder="SHOWCASE_RULE" pattern="[A-Z][A-Z0-9_]{2,63}" value={newPolicyId} onChange={(event) => setNewPolicyId(event.target.value)} required />
          <input aria-label="Policy name" placeholder="Rule name" minLength={2} maxLength={80} value={newPolicyName} onChange={(event) => setNewPolicyName(event.target.value)} required />
          <input aria-label="Policy value" placeholder="Display value" maxLength={128} pattern="[A-Za-z0-9][A-Za-z0-9 _./:+%\-]{0,127}" value={newPolicyValue} onChange={(event) => setNewPolicyValue(event.target.value)} required />
          <button type="submit" className="btn btn-secondary" disabled={creating}>{creating ? "Adding…" : "Add showcase rule"}</button>
        </form>}
        <PolicyTable catalogue={catalogue} canMutate={canMutate} onSave={saveRule} onReset={(selected) => setConfirmation({ kind: "single", rule: selected })} />
      </>}
      {confirmation && <PolicyResetDialog confirmation={confirmation} busy={resetting} onCancel={() => setConfirmation(null)} onConfirm={() => void confirmReset()} />}
    </div>
  );
}
