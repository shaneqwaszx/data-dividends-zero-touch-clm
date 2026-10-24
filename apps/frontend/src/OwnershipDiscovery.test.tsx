// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it } from "vitest";

import OwnershipPathExplorer from "./pages/OwnershipPathExplorer";
import { formatPolicyValue, policyCategory, policyExplanation, policyRangeHint } from "./pages/PolicyRules";
import type { OwnershipAnalysisRecord, OwnershipDiscoveryAudit, PolicyRule } from "./types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const now = "2026-10-23T00:00:00Z";

function rule(policy_id: string, value: PolicyRule["value"], minimum: string | number | null, maximum: string | number | null): PolicyRule {
  return { policy_id, category: "Ownership", name: policy_id, description: "Synthetic", value, value_type: value.type, default_value: value, minimum, maximum, allowed_values: [], classifications: ["PROJECT_DEFAULT"], authority: null, default_authority: null, enforcement: "RUNTIME_ENFORCED", version: 1, created_at: now, updated_at: now, updated_by: "system-bootstrap" } as PolicyRule;
}

function audit(overrides: Partial<OwnershipDiscoveryAudit> = {}): OwnershipDiscoveryAudit {
  return {
    method: "REGISTRY_CORPORATE_DISCOVERY_V1", trace_threshold_percent: "10.000000", ubo_threshold_percent: "25.000000",
    max_corporate_depth: 5, call_budget_enabled: false, call_budget_max: 10, graph_complete: true,
    classification_certainty: "COMPLETE", unresolved_upper_bound_percent: "0", registry_lookups: 1,
    provider_backed_lookups: 0, cache_hits: 1, unresolved_person_party_ids: [],
    records: [{ party_id: "111111111M", display_name: "SIM LIM PTE. LTD.", registration_number: "111111111M", depth: 1, outcome: "CACHE_HIT", max_effective_percent: "62.500000", reason_code: null }],
    ...overrides,
  };
}

function record(discovery: OwnershipDiscoveryAudit | null): OwnershipAnalysisRecord {
  return {
    case_id: "case", analysis_id: "analysis", correlation_id: "correlation", root_party_id: "ENTITY_11111999A", provider_name: "ACRA_REGISTRY_ACQUISITION", provider_environment: "MOCK",
    state: discovery?.graph_complete === false ? "REVIEW_REQUIRED" : "ANALYZED", parties: [], relationships: [], candidates: [],
    issues: discovery?.graph_complete === false ? [{ code: "CORPORATE_OWNERSHIP_UNRESOLVED", message: "1 corporate ownership branch(es) remain unresolved; up to 5% root-equivalent interest is undisclosed.", affected_party_ids: ["300000001B"] }] : [],
    discovery, threshold_percent: "25.000000", threshold_comparator: "GREATER_THAN_OR_EQUAL_TO", events: [], error: null, created_at: now, loaded_at: now, analyzed_at: now, updated_at: now,
  };
}

let root: Root | null = null; let container: HTMLDivElement | null = null;
afterEach(() => { if (root) act(() => root?.unmount()); container?.remove(); root = null; container = null; });
function render(value: OwnershipAnalysisRecord) { container = document.createElement("div"); document.body.append(container); root = createRoot(container); act(() => root?.render(<OwnershipPathExplorer record={value} presentation="main" />)); return container; }

describe("recursive ownership discovery policy and display", () => {
  it("explains and formats the editable discovery rules in the Ownership category", () => {
    const trace = rule("OWNERSHIP_TRACE_THRESHOLD_PERCENT", { type: "DECIMAL", value: "10.000000" }, "0.000001", "100");
    const depth = rule("OWNERSHIP_DISCOVERY_MAX_CORPORATE_DEPTH", { type: "INTEGER", value: 5 }, 1, 7);
    const enabled = rule("OWNERSHIP_REGISTRY_CALL_BUDGET_ENABLED", { type: "BOOLEAN", value: false }, null, null);
    const budget = rule("OWNERSHIP_REGISTRY_CALL_BUDGET_MAX", { type: "INTEGER", value: 10 }, 1, 32);
    for (const item of [trace, depth, enabled, budget]) {
      expect(policyCategory(item)).toBe("Ownership & UBO");
      expect(policyExplanation(item).formula).not.toBe("Fixed contract or system definition");
    }
    expect(policyExplanation(trace).affects).toContain("never marks anyone non-UBO");
    expect(policyExplanation(depth).affects).toContain("8-edge calculation limit is unchanged");
    expect(policyExplanation(enabled).affects).toContain("fixed technical safeguards");
    expect(formatPolicyValue(trace, trace.value)).toBe("10.000000%");
    expect(formatPolicyValue(depth, depth.value)).toBe("5 levels");
    expect(policyRangeHint(budget)).toBe("Allowed 1 – 32 acquisitions");
  });

  it("shows each corporate owner's own-record outcome without recalculating Decimal strings", () => {
    const view = render(record(audit()));
    const summary = view.querySelector("details.ownership-discovery");
    expect(summary).not.toBeNull();
    const text = summary!.textContent ?? "";
    expect(text).toContain("Corporate owners from separate registry records (1)");
    expect(text).toContain("SIM LIM PTE. LTD.");
    expect(text).toContain("Reused fresh registry evidence");
    expect(text).toContain("62.5%");
    expect(text).toContain("1 registry lookup (0 provider-backed, 1 reused from cache)");
  });

  it("keeps a deferred branch visibly partial with its exposure and review issue", () => {
    const view = render(record(audit({
      graph_complete: false, classification_certainty: "BOUNDED_NO_THRESHOLD_CHANGE", unresolved_upper_bound_percent: "5", registry_lookups: 0, cache_hits: 0,
      records: [{ party_id: "CORP_B", display_name: "B CO", registration_number: "300000001B", depth: 1, outcome: "DEFERRED_BELOW_TRACE_THRESHOLD", max_effective_percent: "5", reason_code: null }],
    })));
    const text = view.textContent ?? "";
    expect(text).toContain("Graph partial · partial; bound shows no threshold change");
    expect(text).toContain("Up to 5% root-equivalent interest remains undisclosed.");
    expect(text).toContain("Deferred below tracing priority");
    expect(text).toContain("Non-definitive partial ownership view");
    expect(text).toContain("CORPORATE_OWNERSHIP_UNRESOLVED");
  });

  it("renders nothing extra for historical analyses without a discovery audit", () => {
    const view = render(record(null));
    expect(view.querySelector("details.ownership-discovery")).toBeNull();
  });
});
