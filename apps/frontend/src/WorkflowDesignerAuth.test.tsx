// @vitest-environment jsdom
import { useQueryClient, type QueryClient } from "@tanstack/react-query";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { MemoryRouter, useLocation } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { configureAuthenticatedTransport } from "./api";
import { AuthProvider, useAuth } from "./auth";
import WorkflowDesigner from "./pages/WorkflowDesigner";
import type { AuthenticatedProfile, AuthSession } from "./types";
import { executionPlanQueryKeys, fetchExecutionPlan, type ExecutionPlan } from "./workflowExecutionPlan";

/** P2-2: the execution plan travels on the app's session transport, never a plain fetch. */

const PLAN_PATH = "/api/workflows/onboarding/execution-plan";

const hr: AuthenticatedProfile = {
  user_id: "synthetic-hr", display_name: "Synthetic HR", role: "HR", team_id: null, team_display_name: null,
  team_type: null, team_description: "", client_scope_label: "Global", capabilities: ["POLICY_VIEW", "POLICY_MUTATE"],
};
const director: AuthenticatedProfile = {
  ...hr, user_id: "synthetic-director", display_name: "Synthetic Director", role: "DIRECTOR",
  capabilities: ["POLICY_VIEW", "POLICY_APPROVE"],
};

function plan(explanation: string): ExecutionPlan {
  return {
    registry_search_order: "SEARCH_THEN_REGISTRY",
    order_explanation: explanation,
    stages: [{
      stage_id: "CASE_START", label: "Case created", engine_stage: "CREATION", runs: "", mandatory: true, fixed: true,
      fixed_reason: "", prerequisites: [], checkpoints: [], safeguards: [], policy_rule_ids: [],
      policy_rule_references: [], conditional_rule_usage: [], fixed_controls: [],
    }],
    workflow_wide_policy_rule_ids: [],
    workflow_wide_fixed_controls: [],
    optional_steps: { state: "NO_ACTIVE_WORKFLOW", version: null, manager_enabled: true, enforced_at_send: false, explanation: "", steps: [] },
    branches_supported: false,
    provider_lanes: [],
  };
}

function json(value: unknown, status = 200, headers: Record<string, string> = {}) {
  return new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json", ...headers } });
}
const catalogue = { catalogue_id: "GLOBAL_POLICY_CATALOGUE", version: 1, created_at: "", updated_at: "", updated_by: "system", rules: [] };
const session = (profile: AuthenticatedProfile): AuthSession => ({ profile, csrf_token: `synthetic-csrf-${profile.user_id}` });
const unauthenticated = () => json({ detail: { code: "AUTHENTICATION_REQUIRED", message: "Authentication is required." } }, 401, { "X-Session-End-Reason": "SESSION_EXPIRED" });
const forbidden = () => json({ detail: { code: "EXECUTION_PLAN_FORBIDDEN", message: "Forbidden" } }, 403);

let root: Root;
let container: HTMLDivElement;

beforeEach(() => {
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
});

afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  configureAuthenticatedTransport({ csrfToken: null, onUnauthorized: null });
  vi.restoreAllMocks();
  vi.unstubAllEnvs();
  vi.resetModules();
});

const settle = () => act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });

type PlanHandler = (user: string) => Response | Promise<Response>;

/** The real AuthProvider owns the session, the 401 handler and the session query cache. */
async function mountSignedIn(profile: AuthenticatedProfile, onPlan: PlanHandler) {
  let signedIn: AuthenticatedProfile | null = profile;
  let auth!: ReturnType<typeof useAuth>;
  let client!: QueryClient;
  const request = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const pathname = new URL(String(input), "http://frontend.test").pathname;
    if (pathname === "/api/auth/me") return signedIn ? json(session(signedIn)) : unauthenticated();
    if (pathname === "/api/auth/login") {
      const userId = JSON.parse(init!.body as string).user_id as string;
      signedIn = [hr, director].find(candidate => candidate.user_id === userId)!;
      return json(session(signedIn));
    }
    if (pathname === "/api/auth/logout") {
      signedIn = null;
      return new Response(null, { status: 204 });
    }
    if (pathname === PLAN_PATH) return onPlan(signedIn?.user_id ?? "anonymous");
    if (pathname === "/api/policies") return json(catalogue);
    return json({});
  });
  function Probe() {
    auth = useAuth();
    client = useQueryClient();
    const location = useLocation();
    return (
      <>
        <output data-status>{auth.status}</output>
        <output data-location>{location.pathname}</output>
        {auth.session && <WorkflowDesigner key={auth.session.profile.user_id} actor={auth.session.profile} initialView="outline" />}
      </>
    );
  }
  await act(async () => root.render(<MemoryRouter initialEntries={["/policy/workflow-designer"]}><AuthProvider><Probe /></AuthProvider></MemoryRouter>));
  await vi.waitFor(() => expect(container.querySelector("[data-status]")!.textContent).toBe("authenticated"));
  await settle();
  return { auth: () => auth, client: () => client, request };
}

type FetchSpy = Awaited<ReturnType<typeof mountSignedIn>>["request"];
const planCalls = (request: FetchSpy) =>
  request.mock.calls.filter(([input]) => String(input).includes(PLAN_PATH));

describe("Execution plan transport (P2-2)", () => {
  it("sends an authenticated request with the session cookie and no state-changing header", async () => {
    const onUnauthorized = vi.fn();
    configureAuthenticatedTransport({ csrfToken: "synthetic-csrf", onUnauthorized });
    const request = vi.spyOn(globalThis, "fetch").mockResolvedValue(json(plan("Loaded.")));
    const controller = new AbortController();
    await expect(fetchExecutionPlan(controller.signal)).resolves.toMatchObject({ order_explanation: "Loaded." });
    const [url, init] = request.mock.calls[0];
    expect(String(url)).toBe(PLAN_PATH);
    expect(init).toMatchObject({ credentials: "include", signal: controller.signal });
    expect(new Headers(init!.headers).has("X-CSRF-Token")).toBe(false);
    expect(onUnauthorized).not.toHaveBeenCalled();
  });

  it("includes credentials when the backend is on another origin", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://localhost:8000");
    vi.resetModules();
    const api = await import("./api");
    const module = await import("./workflowExecutionPlan");
    api.configureAuthenticatedTransport({ csrfToken: null, onUnauthorized: vi.fn() });
    const request = vi.spyOn(globalThis, "fetch").mockResolvedValue(json(plan("Cross-origin.")));
    await module.fetchExecutionPlan();
    expect(String(request.mock.calls[0][0])).toBe(`http://localhost:8000${PLAN_PATH}`);
    expect(request.mock.calls[0][1]).toMatchObject({ credentials: "include" });
    api.configureAuthenticatedTransport({ csrfToken: null, onUnauthorized: null });
  });

  it("an expired session (401) ends the session and clears every session-scoped query", async () => {
    let release!: () => void;
    const gate = new Promise<void>(resolve => { release = resolve; });
    const harness = await mountSignedIn(hr, async () => {
      await gate;
      return unauthenticated();
    });
    harness.client().setQueryData(["auth", hr.user_id, "sensitive"], { private: true });
    expect(container.textContent).toContain("Loading the execution plan");
    await act(async () => { release(); await gate; });
    await vi.waitFor(() => expect(container.querySelector("[data-status]")!.textContent).toBe("anonymous"));
    expect(container.querySelector("[data-location]")!.textContent).toBe("/");
    expect(harness.client().getQueryData(["auth", hr.user_id, "sensitive"])).toBeUndefined();
    expect(harness.client().getQueryData(executionPlanQueryKeys.plan(hr.user_id))).toBeUndefined();
    expect(harness.client().getQueryCache().getAll()).toHaveLength(0);
    expect(container.textContent).not.toContain("Workflow designer");
    // The session-end reason is asked once, outside the transport; the plan is not retried.
    expect(planCalls(harness.request)).toHaveLength(1);
  });

  it("a refused plan (403) keeps the session and shows the safe message", async () => {
    const harness = await mountSignedIn(hr, () => forbidden());
    harness.client().setQueryData(["auth", hr.user_id, "kept"], { kept: true });
    await vi.waitFor(() => expect(container.querySelector("[role='alert']")?.textContent).toContain("available to HR administrators and Directors"));
    expect(container.querySelector("[data-status]")!.textContent).toBe("authenticated");
    expect(harness.client().getQueryData(["auth", hr.user_id, "kept"])).toEqual({ kept: true });
  });

  it("retrying after a failure never shows another user's plan", async () => {
    const failFor = new Set([director.user_id]);
    const harness = await mountSignedIn(hr, user => {
      if (failFor.has(user)) {
        failFor.delete(user);
        return json({ detail: { code: "UNAVAILABLE", message: "Unavailable" } }, 500);
      }
      return json(plan(`Plan for ${user}.`));
    });
    await vi.waitFor(() => expect(container.textContent).toContain(`Plan for ${hr.user_id}.`));

    await act(async () => harness.auth().logout());
    expect(harness.client().getQueryData(executionPlanQueryKeys.plan(hr.user_id))).toBeUndefined();
    await act(async () => harness.auth().login(director.user_id, "synthetic-test-credential"));
    await vi.waitFor(() => expect(container.querySelector("[data-status]")!.textContent).toBe("authenticated"));
    await vi.waitFor(() => expect(container.querySelector("[role='alert']")?.textContent).toContain("could not be loaded"));
    expect(container.textContent).not.toContain(`Plan for ${hr.user_id}.`);
    expect(harness.client().getQueryData(executionPlanQueryKeys.plan(hr.user_id))).toBeUndefined();

    const retry = container.querySelector<HTMLButtonElement>("[role='alert'] button")!;
    expect(retry.textContent).toBe("Try again");
    await act(async () => retry.click());
    await vi.waitFor(() => expect(container.textContent).toContain(`Plan for ${director.user_id}.`));
    expect(container.textContent).not.toContain(`Plan for ${hr.user_id}.`);
    const lastPlanCall = planCalls(harness.request).at(-1)!;
    expect(lastPlanCall[1]).toMatchObject({ credentials: "include" });
  });
});
