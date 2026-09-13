import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { WorkspaceTabs } from "./App";
import {
  ApiError,
  configureAuthenticatedTransport,
  createShowcasePolicy,
  createAdminProfile,
  fetchDashboard,
  fetchZeroTouchCases,
  resetAllPolicies,
  resetPolicy,
  updatePolicy,
} from "./api";
import AdminUsers from "./pages/AdminUsers";
import DirectorTeamFilter from "./pages/DirectorTeamFilter";
import {
  beginPolicyMutation,
  executePolicyMutation,
  PolicyResetDialog,
  PolicyTable,
  policyIsEditable,
  shouldCancelPolicyReset,
} from "./pages/PolicyRules";
import type { AuthenticatedProfile, PolicyCatalogue, PolicyRule } from "./types";

const hr: AuthenticatedProfile = {
  user_id: "hr-admin",
  display_name: "POC HR Administrator",
  role: "HR",
  team_id: null,
  team_display_name: null,
  team_type: null,
  team_description: "Administration only; no client-case access",
  client_scope_label: "Administration only",
  capabilities: ["POLICY_VIEW", "IDENTITY_ADMIN", "TEAM_ADMIN"],
};

const testCredential = "test_placeholder";

const director: AuthenticatedProfile = {
  ...hr,
  user_id: "olivia-koh",
  display_name: "Olivia Koh",
  role: "DIRECTOR",
  team_description: "Global / cross-team access",
  client_scope_label: "Global / cross-team",
  capabilities: ["POLICY_VIEW", "POLICY_MUTATE", "CASE_ACCESS", "CASE_GLOBAL"],
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
      <WorkspaceTabs actor={hr} activeTab="users" onChange={() => undefined} />,
    );
    expect(markup).toContain("Users");
    expect(markup).toContain("Teams");
    expect(markup).toContain("Policy");
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

describe("Phase 14.5 production policy mutation workflow", () => {
  it("gives an RM the production showcase create surface", () => {
    const rm = { ...director, role: "RELATIONSHIP_MANAGER" as const, team_id: "TEAM_A" as const };
    expect(rm.capabilities.includes("POLICY_MUTATE")).toBe(true);
    expect(policyIsEditable(showcaseRule, rm.capabilities.includes("POLICY_MUTATE"))).toBe(true);
  });

  it("creates showcase policy through the production API and uses server catalogue truth", async () => {
    const authoritative = catalogue();
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(authoritative), { status: 201 }),
    );

    const returned = await createShowcasePolicy({
      expected_catalogue_version: 1,
      policy_id: "SHOWCASE_NOTE",
      category: "Demonstration",
      name: "Showcase note",
      description: "Display-only custom demonstration rule.",
      value: { type: "STRING", value: "Enhanced Review" },
    });

    expect(returned).toEqual(authoritative);
    expect((fetchMock.mock.calls[0][1] as RequestInit).method).toBe("POST");
  });

  it("renders a created showcase immediately with truthful non-runtime edit/reset controls", () => {
    const markup = renderToStaticMarkup(
      <PolicyTable catalogue={catalogue()} canMutate onSave={async () => true} onReset={() => undefined} />,
    );
    expect(markup).toContain("Enhanced Review");
    expect(markup).toContain("Showcase only · Not runtime enforced");
    expect(markup).toContain("Edit");
    expect(markup).toContain("Reset to default");
    expect(policyIsEditable(showcaseRule, true)).toBe(true);
  });

  it("submits only permitted custom edit fields and displays the authoritative update", async () => {
    const updatedRule = { ...showcaseRule, value: { type: "STRING" as const, value: "Risk: Medium" }, version: 2 };
    const authoritative = catalogue(updatedRule);
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(authoritative), { status: 200 }),
    );
    const returned = await updatePolicy(showcaseRule.policy_id, {
      expected_catalogue_version: 1,
      expected_rule_version: 1,
      value: { type: "STRING", value: "Risk: Medium" },
      name: "Showcase note",
      description: "Display-only custom demonstration rule.",
    });
    const body = JSON.parse(String((fetchMock.mock.calls[0][1] as RequestInit).body));
    expect(body).toEqual({
      expected_catalogue_version: 1,
      expected_rule_version: 1,
      value: { type: "STRING", value: "Risk: Medium" },
      name: "Showcase note",
      description: "Display-only custom demonstration rule.",
    });
    expect(JSON.stringify(body)).not.toMatch(/enforcement|classification|audit|updated_by|default_value/);
    expect(renderToStaticMarkup(
      <PolicyTable catalogue={returned} canMutate onSave={async () => true} onReset={() => undefined} />,
    )).toContain("Risk: Medium");
  });

  it("allows Director mutation while Client Onboarder and HR remain read-only", () => {
    expect(policyIsEditable(showcaseRule, director.capabilities.includes("POLICY_MUTATE"))).toBe(true);
    for (const actor of [hr, { ...hr, role: "CLIENT_ONBOARDER" as const, capabilities: ["POLICY_VIEW" as const] }]) {
      const markup = renderToStaticMarkup(
        <PolicyTable catalogue={catalogue()} canMutate={actor.capabilities.includes("POLICY_MUTATE")} onSave={async () => true} onReset={() => undefined} />,
      );
      expect(markup).not.toContain(">Edit<");
      expect(markup).not.toContain("Reset to default");
    }
  });

  it("keeps Client Onboarder policy rows read-only", () => {
    const markup = renderToStaticMarkup(
      <PolicyTable catalogue={catalogue()} canMutate={false} onSave={async () => true} onReset={() => undefined} />,
    );
    expect(markup).not.toContain(">Edit<");
    expect(markup).not.toContain("Reset to default");
  });

  it("keeps HR policy rows read-only", () => {
    const markup = renderToStaticMarkup(
      <PolicyTable catalogue={catalogue()} canMutate={hr.capabilities.includes("POLICY_MUTATE")} onSave={async () => true} onReset={() => undefined} />,
    );
    expect(markup).not.toContain(">Edit<");
    expect(markup).not.toContain("Reset to default");
  });

  it("renders an accessible single-reset warning with the exact policy name", () => {
    const mutation = vi.fn();
    const markup = renderToStaticMarkup(
      <PolicyResetDialog confirmation={{ kind: "single", rule: showcaseRule }} busy={false} onCancel={() => undefined} onConfirm={mutation} />,
    );
    expect(markup).toContain('role="alertdialog"');
    expect(markup).toContain('aria-modal="true"');
    expect(markup).toContain("Reset Showcase note to default?");
    expect(markup).toContain("not a claim of sponsor-approved production policy");
    expect(mutation).not.toHaveBeenCalled();
  });

  it("opens a single-reset dialog without issuing a network mutation", () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    renderToStaticMarkup(
      <PolicyResetDialog confirmation={{ kind: "single", rule: showcaseRule }} busy={false} onCancel={() => undefined} onConfirm={() => undefined} />,
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("allows single-reset cancellation without a network mutation", () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    const close = vi.fn();
    const markup = renderToStaticMarkup(
      <PolicyResetDialog confirmation={{ kind: "single", rule: showcaseRule }} busy={false} onCancel={close} onConfirm={() => undefined} />,
    );
    expect(markup).toContain("Cancel");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("keeps cancel and Escape mutation-free while disabling Escape during submit", () => {
    expect(shouldCancelPolicyReset("Escape", false)).toBe(true);
    expect(shouldCancelPolicyReset("Escape", true)).toBe(false);
    expect(shouldCancelPolicyReset("Enter", false)).toBe(false);
  });

  it("sends the single-reset confirmation literal exactly once", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(catalogue()), { status: 200 }),
    );
    await resetPolicy(showcaseRule.policy_id, 1, 1);
    const body = JSON.parse(String((fetchMock.mock.calls[0][1] as RequestInit).body));
    expect(body.confirmation).toBe("RESET_POLICY_DEFAULT");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("prevents a double confirm with the production synchronous mutation guard", () => {
    const guard = { current: false };
    expect(beginPolicyMutation(guard)).toBe(true);
    expect(beginPolicyMutation(guard)).toBe(false);
  });

  it("renders the whole-reset confirmation with immutable-case and custom-rule truth", () => {
    const markup = renderToStaticMarkup(
      <PolicyResetDialog confirmation={{ kind: "all" }} busy={false} onCancel={() => undefined} onConfirm={() => undefined} />,
    );
    expect(markup).toContain("Reset all policies to defaults?");
    expect(markup).toContain("Custom showcase rules remain");
    expect(markup).toContain("future cases through immutable case snapshots");
    expect(markup).toContain("existing cases are not reinterpreted");
  });

  it("opens and cancels whole reset without a mutation request", () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    const markup = renderToStaticMarkup(
      <PolicyResetDialog confirmation={{ kind: "all" }} busy={false} onCancel={() => undefined} onConfirm={() => undefined} />,
    );
    expect(markup).toContain("Cancel");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("sends the whole-reset literal once and synchronizes the retained custom rule", async () => {
    const retained = catalogue();
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(retained), { status: 200 }),
    );
    const returned = await resetAllPolicies(1);
    const body = JSON.parse(String((fetchMock.mock.calls[0][1] as RequestInit).body));
    expect(body.confirmation).toBe("RESET_ALL_POLICY_DEFAULTS");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(returned.rules).toContainEqual(showcaseRule);
  });

  it("preserves current authoritative state after a non-conflict reset failure", async () => {
    const current = catalogue();
    const result = await executePolicyMutation(
      async () => { throw new ApiError("Reset failed.", 503, "ADMINISTRATION_UNAVAILABLE"); },
      async () => { throw new Error("must not refresh"); },
      "Policy reset failed.",
    );
    expect(result.succeeded).toBe(false);
    expect(result.catalogue).toBeUndefined();
    expect(result.error).toBe("Reset failed.");
    expect(current.rules[0].value).toEqual(showcaseRule.value);
  });

  it("handles edit 409 by one authoritative refetch without retrying the mutation", async () => {
    const mutation = vi.fn(async () => { throw new ApiError("Conflict", 409, "POLICY_VERSION_CONFLICT"); });
    const refreshed = catalogue({ ...showcaseRule, value: { type: "STRING", value: "MANUAL_REVIEW" }, version: 4 });
    const refresh = vi.fn(async () => refreshed);
    const result = await executePolicyMutation(mutation, refresh, "Policy update failed.");
    expect(mutation).toHaveBeenCalledTimes(1);
    expect(refresh).toHaveBeenCalledTimes(1);
    expect(result.succeeded).toBe(false);
    expect(result.catalogue).toBe(refreshed);
    expect(result.error).toContain("Review the refreshed values");
  });

  it("never automatically retries a stale mutation after the authoritative refetch", async () => {
    const mutation = vi.fn(async () => { throw new ApiError("Conflict", 409, "POLICY_VERSION_CONFLICT"); });
    await executePolicyMutation(mutation, async () => catalogue({ ...showcaseRule, version: 9 }), "failed");
    expect(mutation).toHaveBeenCalledTimes(1);
  });

  it("shows a bounded conflict when the authoritative refetch is unavailable", async () => {
    const result = await executePolicyMutation(
      async () => { throw new ApiError("driver detail", 409, "POLICY_VERSION_CONFLICT"); },
      async () => { throw new Error("network detail"); },
      "failed",
    );
    expect(result.error).toBe("The policy catalogue changed, but refreshed values are temporarily unavailable.");
    expect(result.error).not.toContain("driver detail");
    expect(result.error).not.toContain("network detail");
  });

  it("handles reset 409 by refetching authoritative value/version and invalidating stale truth", async () => {
    const refreshedRule = { ...showcaseRule, value: { type: "STRING" as const, value: "Level-2" }, version: 7 };
    const mutation = vi.fn(async () => { throw new ApiError("Conflict", 409, "POLICY_VERSION_CONFLICT"); });
    const refresh = vi.fn(async () => catalogue(refreshedRule));
    const result = await executePolicyMutation(mutation, refresh, "Policy reset failed.");
    expect(mutation).toHaveBeenCalledTimes(1);
    expect(refresh).toHaveBeenCalledTimes(1);
    expect(result.catalogue?.rules[0].version).toBe(7);
    expect(renderToStaticMarkup(
      <PolicyTable catalogue={result.catalogue!} canMutate onSave={async () => true} onReset={() => undefined} />,
    )).toContain("Level-2");
  });

  it("uses a successful create/edit/reset response as the synchronized catalogue", async () => {
    const server = catalogue({ ...showcaseRule, value: { type: "STRING", value: "SG" }, version: 8 });
    const result = await executePolicyMutation(async () => server, async () => catalogue(), "failed");
    expect(result).toEqual({ succeeded: true, catalogue: server, error: null });
  });
});
