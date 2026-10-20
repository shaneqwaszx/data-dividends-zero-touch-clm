// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as api from "./api";
import PolicyRules, { formatPolicyValue, policyDiffersFromDefault, policyMatchesView, policyRangeHint, ProposalReview } from "./pages/PolicyRules";
import type { AuthenticatedProfile, ClassifierBenchmark, PolicyCatalogue, PolicyImpact, PolicyProposal, PolicyRule } from "./types";
(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const now = "2026-10-21T00:00:00Z";
const base: Pick<PolicyRule, "category" | "allowed_values" | "classifications" | "authority" | "default_authority" | "version" | "created_at" | "updated_at" | "updated_by"> = { category: "Synthetic", allowed_values: [], classifications: ["PROJECT_DEFAULT"], authority: null, default_authority: null, version: 1, created_at: now, updated_at: now, updated_by: "system-bootstrap" };
const ubo: PolicyRule = { ...base, policy_id: "OWNERSHIP_UBO_THRESHOLD_PERCENT", name: "UBO threshold percent", description: "Synthetic ownership threshold", value: { type: "DECIMAL", value: "30" }, value_type: "DECIMAL", default_value: { type: "DECIMAL", value: "25" }, minimum: "0", maximum: "100", enforcement: "RUNTIME_ENFORCED" };
const freshness: PolicyRule = { ...base, policy_id: "REGISTRY_FRESHNESS_DAYS", name: "Registry evidence freshness", description: "Synthetic reuse window", value: { type: "INTEGER", value: 90 }, value_type: "INTEGER", default_value: { type: "INTEGER", value: 90 }, minimum: "1", maximum: "365", enforcement: "RUNTIME_ENFORCED" };
const ttl: PolicyRule = { ...freshness, policy_id: "REGISTRY_NOT_FOUND_TTL_SECONDS", name: "Definitive not-found cache TTL", description: "Missing entities only", value: { type: "INTEGER", value: 600 }, default_value: { type: "INTEGER", value: 600 }, minimum: "1", maximum: "3600" };
const fixed: PolicyRule = { ...base, policy_id: "WORKFLOW_FIXED_DEFINITION", name: "Fixed workflow definition", description: "Contract-defined value", value: { type: "STRING", value: "FIXED" }, value_type: "STRING", default_value: { type: "STRING", value: "FIXED" }, minimum: null, maximum: null, enforcement: "NOT_EDITABLE" };
const catalogue: PolicyCatalogue = { catalogue_id: "GLOBAL_POLICY_CATALOGUE", version: 2, active_version: 1, active_identity: "a".repeat(64), active_origin: "DEFAULT", active_effective_at: now, proposals: [], superseded_versions: [], created_at: now, updated_at: now, updated_by: "system-bootstrap", rules: [ubo, freshness, ttl, fixed] };
const metrics: ClassifierBenchmark = { label: "Deterministic", scope: "Synthetic", benchmark_id: "SAFE", benchmark_hash: "b".repeat(64), rule_version: "v2", policy_version: 1, support: 14, exact_accuracy: 1, classes: [], confusion_matrix: {}, macro: { precision: 1, recall: 1, f1: 1 }, micro: { precision: 1, recall: 1, f1: 1 } };
const profile = (user_id: string, role: AuthenticatedProfile["role"], capabilities: AuthenticatedProfile["capabilities"]): AuthenticatedProfile => ({ user_id, display_name: user_id, role, team_id: null, team_display_name: null, team_type: null, team_description: "Synthetic", client_scope_label: "Synthetic", capabilities });
const hr = profile("hr-proposer", "HR", ["POLICY_VIEW", "POLICY_MUTATE"]);
const rm = profile("rm-reader", "RELATIONSHIP_MANAGER", ["POLICY_VIEW"]);
const director = profile("director-decider", "DIRECTOR", ["POLICY_VIEW", "POLICY_APPROVE"]);
const pending: PolicyProposal = { proposal_id: "SAFE_PROPOSAL", version: 1, base_active_version: 1, proposer_id: hr.user_id, status: "PENDING_APPROVAL", rules: [{ ...ubo, value: { type: "DECIMAL", value: "35" } }, freshness, ttl, fixed], reason: "Synthetic pending proposal", created_at: now, updated_at: now, decided_by: null, decided_at: null, decision_reason: null, activated_version: null };

let dispose: (() => void) | undefined;
afterEach(async () => { await act(async () => dispose?.()); dispose = undefined; vi.restoreAllMocks(); document.body.innerHTML = ""; });
async function mountPage(actor: AuthenticatedProfile, value: PolicyCatalogue = catalogue) {
  vi.spyOn(api, "fetchPolicies").mockResolvedValue(value); vi.spyOn(api, "fetchClassifierBenchmark").mockResolvedValue(metrics);
  const host = document.createElement("div"); document.body.append(host); const root = createRoot(host); dispose = () => root.unmount();
  await act(async () => root.render(<PolicyRules actor={actor} />));
  return host;
}
const buttons = (host: HTMLElement, text: string | RegExp) => Array.from(host.querySelectorAll("button")).filter(item => typeof text === "string" ? item.textContent === text : text.test(item.textContent ?? ""));
const button = (host: HTMLElement, text: string | RegExp) => buttons(host, text)[0];
async function click(element: Element | undefined) { expect(element).toBeTruthy(); await act(async () => (element as HTMLElement).click()); }
async function type(element: HTMLInputElement | HTMLTextAreaElement, value: string) {
  const prototype = element instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  await act(async () => { Object.getOwnPropertyDescriptor(prototype, "value")!.set!.call(element, value); element.dispatchEvent(new Event("input", { bubbles: true })); });
}
const ruleNames = (host: HTMLElement) => Array.from(host.querySelectorAll(".policy-parameter h3")).map(item => item.textContent);
const card = (host: HTMLElement, name: string) => Array.from(host.querySelectorAll<HTMLElement>(".policy-parameter")).find(item => item.querySelector("h3")?.textContent === name)!;

describe("presentation helpers", () => {
  it("formats days, seconds, percent and unit-less values", () => {
    expect(formatPolicyValue(freshness, freshness.value)).toBe("90 days");
    expect(formatPolicyValue(ttl, ttl.value)).toBe("600 seconds");
    expect(formatPolicyValue(ubo, ubo.value)).toBe("30%");
    expect(formatPolicyValue(fixed, fixed.value)).toBe("FIXED");
  });
  it("describes the allowed range only when both bounds exist", () => {
    expect(policyRangeHint(freshness)).toBe("Allowed 1 – 365 days");
    expect(policyRangeHint(ubo)).toBe("Allowed 0 – 100%");
    expect(policyRangeHint(fixed)).toBeNull();
    expect(policyRangeHint({ ...freshness, maximum: null })).toBeNull();
  });
  it("filters by editability, change from default, staged draft and search text", () => {
    expect(policyDiffersFromDefault(ubo)).toBe(true); expect(policyDiffersFromDefault(freshness)).toBe(false);
    expect(policyMatchesView(fixed, "editable", "", {})).toBe(false); expect(policyMatchesView(ubo, "editable", "", {})).toBe(true);
    expect(policyMatchesView(ubo, "changed", "", {})).toBe(true); expect(policyMatchesView(freshness, "changed", "", {})).toBe(false);
    expect(policyMatchesView(freshness, "staged", "", {})).toBe(false); expect(policyMatchesView(freshness, "staged", "", { [freshness.policy_id]: { type: "INTEGER", value: 30 } })).toBe(true);
    expect(policyMatchesView(ttl, "all", "  MISSING entities ", {})).toBe(true); expect(policyMatchesView(ubo, "all", "missing", {})).toBe(false);
    expect(policyMatchesView(fixed, "all", "", {})).toBe(true);
  });
});

describe("policy page view", () => {
  it("exposes pressed filters with counts, narrows by search and reports an empty match", async () => {
    const host = await mountPage(hr);
    const all = button(host, "All rules · 4"); const editable = button(host, "Editable · 3"); const changed = button(host, "Changed from default · 1");
    expect(all.getAttribute("aria-pressed")).toBe("true"); expect(editable.getAttribute("aria-pressed")).toBe("false");
    expect(button(host, "Staged in draft · 0")).toBeTruthy();
    expect(host.querySelector('[role="group"][aria-label="Filter policy rules"]')).not.toBeNull();
    await click(editable); expect(editable.getAttribute("aria-pressed")).toBe("true"); expect(ruleNames(host)).not.toContain("Fixed workflow definition"); expect(ruleNames(host)).toHaveLength(3);
    await click(changed); expect(ruleNames(host)).toEqual(["UBO threshold percent"]);
    await click(all);
    await type(host.querySelector<HTMLInputElement>('input[type="search"]')!, "missing entities"); expect(ruleNames(host)).toEqual(["Definitive not-found cache TTL"]);
    await type(host.querySelector<HTMLInputElement>('input[type="search"]')!, "no such synthetic rule");
    expect(ruleNames(host)).toEqual([]); expect(host.textContent).toContain("No rules match this filter.");
  });

  it("stages a proposed value, shows it in the Proposed column, category, tray and filter, and removes it", async () => {
    const host = await mountPage(hr);
    expect(host.textContent).toContain("No changes staged."); expect(host.textContent).toContain("0 changes staged");
    expect(card(host, "UBO threshold percent").textContent).toContain("Modified");
    const freshCard = card(host, "Registry evidence freshness");
    await click(Array.from(freshCard.querySelectorAll("button")).find(item => item.textContent === "Propose change"));
    const input = freshCard.querySelector<HTMLInputElement>('input[type="number"]')!;
    expect(host.querySelector(`#${input.getAttribute("aria-describedby")}`)?.textContent).toBe("Allowed 1 – 365 days");
    await type(input, "30");
    await click(Array.from(freshCard.querySelectorAll("button")).find(item => item.textContent === "Use proposed value"));
    const staged = card(host, "Registry evidence freshness");
    expect(staged.className).toContain("policy-parameter--staged");
    expect(staged.querySelector(".policy-staged-value")?.textContent).toBe("90 days → 30 days");
    expect(host.textContent).toContain("1 change staged"); expect(host.textContent).toContain("1 staged");
    expect(host.querySelector(".policy-draft-tray__changes")?.textContent).toContain("Registry evidence freshness · proposed 30");
    expect(button(host, "Staged in draft · 1")).toBeTruthy();
    await click(button(host, "Staged in draft · 1")); expect(ruleNames(host)).toEqual(["Registry evidence freshness"]);
    await click(button(host, "Remove proposed change"));
    expect(host.textContent).toContain("0 changes staged"); expect(ruleNames(host)).toEqual([]);
    expect(card(host, "UBO threshold percent")).toBeUndefined();
  });

  it("keeps Save draft blocked with an explained hint until a change and a 10-character reason exist", async () => {
    const host = await mountPage(hr);
    const save = button(host, "Save draft");
    expect(save.disabled).toBe(true); expect(host.querySelector(`#${save.getAttribute("aria-describedby")}`)?.textContent).toBe("Stage at least one change with Propose change to save a draft.");
    const freshCard = card(host, "Registry evidence freshness");
    await click(Array.from(freshCard.querySelectorAll("button")).find(item => item.textContent === "Propose change"));
    await type(freshCard.querySelector<HTMLInputElement>('input[type="number"]')!, "45");
    await click(Array.from(freshCard.querySelectorAll("button")).find(item => item.textContent === "Use proposed value"));
    expect(button(host, "Save draft").disabled).toBe(true);
    expect(host.querySelector("#policy-save-hint")?.textContent).toBe("Add a change reason of at least 10 characters to save.");
    await type(host.querySelector<HTMLTextAreaElement>("#policy-proposal-reason")!, "Synthetic reason long enough");
    expect(button(host, "Save draft").disabled).toBe(false); expect(host.querySelector("#policy-save-hint")).toBeNull();
  });

  it("shows read-only actors no staged filter, draft tray or proposal controls", async () => {
    const host = await mountPage(rm);
    expect(buttons(host, /^Staged in draft/)).toHaveLength(0);
    expect(host.textContent).not.toContain("Prepare policy proposal");
    expect(buttons(host, "Propose change")).toHaveLength(0); expect(buttons(host, "Reset to default")).toHaveLength(0);
    expect(host.querySelector(".policy-parameter--fixed")?.textContent).toContain("Fixed definition");
  });

  it("tells a Director a proposal awaits their decision and tells the proposer it awaits another Director", async () => {
    const withPending = { ...catalogue, proposals: [pending] };
    const directorHost = await mountPage(director, withPending);
    expect(directorHost.querySelector(".policy-attention")?.textContent).toContain("1 proposal awaiting your decision.");
    await act(async () => dispose?.()); dispose = undefined; vi.restoreAllMocks(); document.body.innerHTML = "";
    const proposerHost = await mountPage({ ...hr, capabilities: ["POLICY_VIEW", "POLICY_MUTATE"] }, withPending);
    expect(proposerHost.querySelector(".policy-attention")?.textContent).toContain("1 proposal you submitted is awaiting an independent Director.");
    await act(async () => dispose?.()); dispose = undefined; vi.restoreAllMocks(); document.body.innerHTML = "";
    const readerHost = await mountPage(rm, withPending);
    expect(readerHost.querySelector(".policy-attention")).toBeNull();
  });
});

describe("proposal decision step", () => {
  const runtime = { registry_freshness_seconds: 7776000, not_found_ttl_seconds: 600, document_auto_confirm: [false, true, true], ownership_numeric_candidates: [null, null, null] };
  const impact = { proposal_id: pending.proposal_id, proposal_version: 1, catalogue_version: 2, base_active_version: 1, current_active_version: 1, stale: false, comparison_basis: "ACTIVE_PROPOSAL_BASE", comparison_identity: "c".repeat(64), label: "Read-only synthetic policy impact",
    changes: [{ policy_id: ubo.policy_id, name: ubo.name, current: ubo.value, base: ubo.value, default: ubo.default_value, proposed: pending.rules[0].value, direction: "INCREASE", stages: ["OWNERSHIP"], assessment: "ASSESSED", materiality: "HIGH", effect: "AUTOMATIC_REVIEW", scenario_ids: [], coupled_policy_ids: [], reason_codes: [], limitations: ["Synthetic only"] }],
    before: { policy_version_context: "ACTIVE_BASE", classifier: metrics, runtime }, after: { policy_version_context: "PROSPECTIVE_UNRESERVED", classifier: metrics, runtime },
    advisor: { fixture_set_id: "SYNTHETIC_POLICY_IMPACT_V1", fixture_set_hash: "d".repeat(64), scope: "Synthetic impact fixtures only — not production volume forecasting.", classifier_scope: "Deterministic classifier benchmark on synthetic fixtures — not trained ML model performance.", materiality: "HIGH", reason_codes: [], scenarios: [], automation_delta: { automatic_document_confirmations: { before: 7, after: 7, delta: 0 }, provisional_ubo_candidates: { before: 7, after: null, delta: null } }, automation_direction: "NO_OBSERVED_CHANGE", review_direction: "NO_OBSERVED_CHANGE", registry_reuse_direction: "NO_OBSERVED_CHANGE", negative_reuse_direction: "NO_OBSERVED_CHANGE", classifier_metric_delta: { micro_f1: 0 }, unknown_impacts: [], limits: { synthetic_fixtures: 64 } },
  } as unknown as PolicyImpact;
  async function mountReview(actor: AuthenticatedProfile, onMutation = vi.fn(async () => true)) {
    const host = document.createElement("div"); document.body.append(host); const root = createRoot(host); dispose = () => root.unmount();
    await act(async () => root.render(<ProposalReview proposal={pending} catalogue={catalogue} actor={actor} busy={false} onMutation={onMutation} onEdit={() => {}} />));
    return host;
  }

  it("lists proposed changes in an accessible table", async () => {
    const host = await mountReview(director);
    const table = host.querySelector("table.policy-proposal__changes")!;
    expect(table.querySelector("caption")?.textContent).toBe("1 proposed change");
    expect(Array.from(table.querySelectorAll('thead th[scope="col"]')).map(item => item.textContent)).toEqual(["Rule", "Change", "Current", "Default", "Affects"]);
    expect(table.querySelector('tbody th[scope="row"]')?.textContent).toBe("UBO threshold percent");
    expect(table.querySelector("tbody td")?.textContent).toContain("30%"); expect(table.querySelector("tbody td strong")?.textContent).toBe("35%");
  });

  it("keeps Approve and Reject disabled with both hints until impact is simulated and a 10-character reason exists", async () => {
    vi.spyOn(api, "fetchPolicyImpact").mockResolvedValue(impact);
    const onMutation = vi.fn(async () => true);
    const host = await mountReview(director, onMutation);
    const decide = () => [button(host, "Approve and activate"), button(host, "Reject proposal")];
    for (const item of decide()) {
      expect(item.disabled).toBe(true);
      const hints = host.querySelector(`#${item.getAttribute("aria-describedby")}`)!;
      expect(Array.from(hints.querySelectorAll("li")).map(li => li.textContent)).toEqual(["Run Simulate impact before deciding.", "Enter a decision reason of at least 10 characters."]);
    }
    await click(button(host, "Simulate impact"));
    expect(decide().every(item => item.disabled)).toBe(true);
    expect(Array.from(host.querySelectorAll(".policy-blocked-hints li")).map(li => li.textContent)).toEqual(["Enter a decision reason of at least 10 characters."]);
    await type(host.querySelector<HTMLTextAreaElement>(".policy-decision-step textarea")!, "too short");
    expect(decide().every(item => item.disabled)).toBe(true);
    await type(host.querySelector<HTMLTextAreaElement>(".policy-decision-step textarea")!, "Synthetic decision reason");
    expect(decide().every(item => !item.disabled)).toBe(true);
    expect(decide().every(item => item.getAttribute("aria-describedby") === null)).toBe(true);
    expect(onMutation).not.toHaveBeenCalled();
  });

  it("gives the proposer and read-only viewers no decision controls", async () => {
    for (const actor of [{ ...director, user_id: hr.user_id }, rm]) {
      const host = await mountReview(actor);
      expect(buttons(host, "Approve and activate")).toHaveLength(0); expect(buttons(host, "Reject proposal")).toHaveLength(0);
      await act(async () => dispose?.()); dispose = undefined; document.body.innerHTML = "";
    }
  });
});
