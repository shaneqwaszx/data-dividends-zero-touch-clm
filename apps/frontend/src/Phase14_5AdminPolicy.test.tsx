import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import { WorkspaceTabs } from "./navigation";
import {
  ApiError,
  configureAuthenticatedTransport,
  createAdminProfile,
  fetchDashboard,
  fetchZeroTouchCases,
} from "./api";
import AdminUsers from "./pages/AdminUsers";
import DirectorTeamFilter from "./pages/DirectorTeamFilter";
import {
  beginPolicyMutation,
  executePolicyMutation,
  policyExplanation,
  proposalEditChanges,
  policyCategory,
  PolicyResetDialog,
  PolicyTable,
  policyIsEditable,
  shouldCancelPolicyReset,
} from "./pages/PolicyRules";
import type { AuthenticatedProfile, PolicyCatalogue, PolicyRule } from "./types";

const hr: AuthenticatedProfile = {
  user_id: "biz-ops",
  display_name: "POC Biz Ops Administrator",
  role: "HR",
  team_id: null,
  team_display_name: null,
  team_type: null,
  team_description: "Administration only; no client-case access",
  client_scope_label: "Administration only",
  capabilities: ["POLICY_VIEW", "POLICY_MUTATE", "IDENTITY_ADMIN", "TEAM_ADMIN", "PROVIDER_SANDBOX_TEST"],
};

const testCredential = "test_placeholder";

const director: AuthenticatedProfile = {
  ...hr,
  user_id: "olivia-koh",
  display_name: "Olivia Koh",
  role: "DIRECTOR",
  team_description: "Global / cross-team access",
  client_scope_label: "Global / cross-team",
  capabilities: ["POLICY_VIEW", "POLICY_APPROVE", "CASE_ACCESS", "CASE_GLOBAL"],
};

const showcaseRule: PolicyRule = {
  policy_id: "SHOWCASE_NOTE",
  category: "Demonstration",
  name: "Showcase note",
  description: "Display-only custom demonstration rule.",
  value: { type: "STRING", value: "Enhanced Review" },
  value_type: "STRING",
  default_value: { type: "STRING", value: "Enhanced Review" },
  minimum: null,
  maximum: null,
  allowed_values: [],
  classifications: ["DISPLAY_ONLY_NOT_RUNTIME_ENFORCED"],
  authority: null,
  default_authority: null,
  enforcement: "DISPLAY_SHOWCASE_ONLY",
  version: 1,
  created_at: "2026-09-11T00:00:00Z",
  updated_at: "2026-09-11T00:00:00Z",
  updated_by: "olivia-koh",
};

function catalogue(rule: PolicyRule = showcaseRule): PolicyCatalogue {
  return {
    catalogue_id: "GLOBAL_POLICY_CATALOGUE",
    version: rule.version,
    rules: [rule],
    created_at: "2026-09-11T00:00:00Z",
    updated_at: "2026-09-11T00:00:00Z",
    updated_by: "olivia-koh",
  };
}

afterEach(() => {
  vi.restoreAllMocks();
  configureAuthenticatedTransport({ csrfToken: null, onUnauthorized: null });
});

describe("Phase 14.5 administration and team filtering", () => {
  it("renders capability-driven HR navigation without case surfaces", () => {
    const markup = renderToStaticMarkup(
      <MemoryRouter initialEntries={["/admin/users"]}><WorkspaceTabs actor={hr} /></MemoryRouter>,
    );
    expect(markup).toContain("Users");
    expect(markup).toContain("Teams");
    expect(markup).toContain("Policy");
    expect(markup).toContain("GoldTier Sandbox");
    expect(markup).not.toContain("Dashboard");
    expect(markup).not.toContain("New onboarding");
    const adminMarkup = renderToStaticMarkup(<AdminUsers />);
    expect(adminMarkup.match(/type="password"/g)).toHaveLength(2);
    expect(adminMarkup).toContain("Confirm password");
  });

  it("shows a Director-only server query selector with legacy unassigned", () => {
    const markup = renderToStaticMarkup(
      <DirectorTeamFilter actor={director} value="all" onChange={() => undefined} />,
    );
    expect(markup).toContain("All teams");
    expect(markup).toContain("Legacy unassigned");
    expect(renderToStaticMarkup(
      <DirectorTeamFilter actor={hr} value="all" onChange={() => undefined} />,
    )).toBe("");
  });

  it("sends Director filters to both portfolio endpoints", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async () =>
      new Response(JSON.stringify([]), { status: 200 }),
    );
    await fetchZeroTouchCases(undefined, "all", "highest_first", "TEAM_0123456789ABCDEF01234567");
    await fetchDashboard("unassigned");
    expect(String(fetchMock.mock.calls[0][0])).toContain("team_filter=TEAM_0123456789ABCDEF01234567");
    expect(String(fetchMock.mock.calls[1][0])).toContain("team_filter=unassigned");
  });

  it("keeps profile creation password in the unsafe request body only", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ user_id: "gamma-rm" }), { status: 201 }),
    );
    configureAuthenticatedTransport({ csrfToken: "opaque-test-csrf", onUnauthorized: null });
    await createAdminProfile({
      user_id: "gamma-rm",
      display_name: "Gamma RM",
      role: "RELATIONSHIP_MANAGER",
      team_id: "TEAM_0123456789ABCDEF01234567",
      password: testCredential,
    });
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(String(init.body)).toContain('"password"');
    expect(new Headers(init.headers).get("X-CSRF-Token")).toBe("opaque-test-csrf");
  });
});


describe("Phase24C proposal policy surfaces", () => {
  const business: PolicyRule = { ...showcaseRule, policy_id: "DOCUMENT_IDP_REVIEW_CONFIDENCE_THRESHOLD", name: "Document confidence", value: { type: "DECIMAL", value: "0.90" }, default_value: { type: "DECIMAL", value: "0.85" }, value_type: "DECIMAL", enforcement: "RUNTIME_ENFORCED", minimum: "0", maximum: "1" };
  it("exposes current, default, formula, description, Affects and version to read-only actors", () => {
    const markup = renderToStaticMarkup(<PolicyTable catalogue={catalogue(business)} canMutate={false} onSave={async () => true} onReset={() => undefined} />);
    for (const value of ["Current", "Default", "Formula:", "Affects:", "Rule version", "0.90", "0.85"]) expect(markup).toContain(value);
    expect(markup).not.toContain("Propose change");
  });
  it("offers HR business proposals and keeps Director decision authority separate", () => {
    expect(policyIsEditable(business, hr.capabilities.includes("POLICY_MUTATE"))).toBe(true);
    expect(policyIsEditable(business, director.capabilities.includes("POLICY_MUTATE"))).toBe(false);
    expect(director.capabilities.includes("POLICY_APPROVE")).toBe(true);
    const markup = renderToStaticMarkup(<PolicyTable catalogue={catalogue(business)} canMutate onSave={async () => true} onReset={() => undefined} />);
    expect(markup).toContain("Propose change"); expect(markup).toContain("Reset to default");
  });
  it("does not offer decorative showcase or provider invariant editing", () => {
    expect(policyIsEditable(showcaseRule, true)).toBe(false);
    expect(policyIsEditable({ ...business, policy_id: "GOLDTIER_ACCOUNT_ENTITY_TYPE" }, true)).toBe(false);
    expect(policyIsEditable({ ...business, enforcement: "NOT_EDITABLE" }, true)).toBe(false);
  });
  it("reset is a proposal with an accessible labelled confirmation", () => {
    const markup = renderToStaticMarkup(<PolicyResetDialog confirmation={{ kind: "single", rule: business }} busy={false} onCancel={() => undefined} onConfirm={() => undefined} />);
    expect(markup).toContain('role="alertdialog"'); expect(markup).toContain('aria-modal="true"');
    expect(markup).toContain("only after independent Director approval"); expect(markup).toContain("frozen policy");
    expect(markup).not.toContain("Confirm reset");
    expect(shouldCancelPolicyReset("Escape", false)).toBe(true); expect(shouldCancelPolicyReset("Escape", true)).toBe(false);
  });
  it("retains one mutation owner and handles stale CAS by refreshing server truth", async () => {
    const guard = { current: false }; expect(beginPolicyMutation(guard)).toBe(true); expect(beginPolicyMutation(guard)).toBe(false);
    const refreshed = { ...catalogue(business), version: 7 }; const refresh = vi.fn(async () => refreshed);
    const result = await executePolicyMutation(async () => { throw new ApiError("safe conflict", 409, "POLICY_VERSION_CONFLICT"); }, refresh, "failed");
    expect(result.succeeded).toBe(false); expect(result.catalogue).toEqual(refreshed); expect(refresh).toHaveBeenCalledOnce();
    expect(result.error).toContain("Review the refreshed values");
  });
  it("removing a saved draft change restores the active value in its update", () => {
    const active = catalogue(business);
    const draft = { rules: [{ ...business, value: { type: "DECIMAL", value: "0.95" } }] } as import("./types").PolicyProposal;
    expect(proposalEditChanges(active, draft, {})).toEqual({ [business.policy_id]: business.value });
    expect(proposalEditChanges(active, draft, { [business.policy_id]: { type: "DECIMAL", value: "0.85" } })[business.policy_id].value).toBe("0.85");
  });
  it("uses truthful formulas and exactly the five business categories", () => {
    const ids = ["REGISTRY_FRESHNESS_DAYS", "DOCUMENT_IDP_REVIEW_CONFIDENCE_THRESHOLD", "OWNERSHIP_UBO_THRESHOLD_PERCENT", "EVIDENCE_KIND_WEIGHT", "WORKFLOW_SUPPORTED_STAGES"];
    expect(new Set(ids.map(policy_id => policyCategory({ ...business, policy_id }))).size).toBe(5);
    expect(policyExplanation({ ...business, policy_id: "EVIDENCE_KIND_WEIGHT" }).formula).toContain("source confidence");
    expect(policyExplanation({ ...business, policy_id: "REGISTRY_NOT_FOUND_TTL_SECONDS" }).affects).toContain("uncertain failures are never negative hits");
  });
});
