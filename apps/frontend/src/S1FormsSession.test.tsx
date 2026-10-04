// @vitest-environment jsdom

import { act, useState } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClientProvider, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { MemoryRouter, useLocation, useNavigate } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { configureAuthenticatedTransport, fetchExecutionProfile } from "./api";
import { AuthProvider, useAuth } from "./auth";
import { caseQueryKeys } from "./caseQueries";
import LoginPage from "./pages/LoginPage";
import { createSessionQueryClient } from "./queryClient";
import type { AuthenticatedProfile, AuthSession, AuthenticatedTeam, ZeroTouchCaseSummary } from "./types";

const caseId = "00000000-0000-4000-8000-000000000101";
const rm: AuthenticatedProfile = {
  user_id: "synthetic-rm", display_name: "Synthetic RM", role: "RELATIONSHIP_MANAGER",
  team_id: "TEAM_A", team_display_name: "Alpha onboarding", team_type: "Onboarding",
  team_description: "Synthetic team", client_scope_label: "Alpha", capabilities: ["CASE_ACCESS", "POLICY_VIEW"],
};
const director: AuthenticatedProfile = {
  ...rm, user_id: "synthetic-director", display_name: "Synthetic Director", role: "DIRECTOR",
  team_id: null, team_display_name: null, team_type: null, client_scope_label: "Global",
  capabilities: ["CASE_ACCESS", "CASE_GLOBAL", "POLICY_VIEW"],
};
const hr: AuthenticatedProfile = {
  ...rm, user_id: "synthetic-hr", display_name: "Synthetic HR", role: "HR",
  capabilities: ["IDENTITY_ADMIN", "PROVIDER_SANDBOX_TEST"],
};
const teams: AuthenticatedTeam[] = [
  { team_id: "TEAM_A", display_name: "Alpha onboarding", team_type: "Onboarding", description: "Synthetic team", client_scope_label: "Alpha" },
  { team_id: "TEAM_B", display_name: "Beta onboarding", team_type: "Onboarding", description: "Synthetic team", client_scope_label: "Beta" },
];
const created = {
  case: { case_id: caseId, requested_uen: "202400001A", priority: 10, client_scope_label: "Beta" },
  status: "PENDING_INPUTS", current_stage: "DOCUMENT", completed_stages: ["REGISTRY"],
  active_exceptions: [], technical_failure: null, reconciliation: null, target_operations: [], timeline: [],
  timing: { observed_at: "2026-10-04T01:00:00Z", case_elapsed_ms: 0, time_since_last_update_ms: 0, automation_elapsed_ms: null, recorded_total_duration_ms: null },
  created_at: "2026-10-04T01:00:00Z", updated_at: "2026-10-04T01:00:00Z",
} as unknown as ZeroTouchCaseSummary;

function json(value: unknown, status = 200) {
  return new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } });
}
function session(profile: AuthenticatedProfile): AuthSession {
  return { profile, csrf_token: `synthetic-session-${profile.user_id}` };
}
function denied() {
  return json({ detail: { code: "AUTHENTICATION_REQUIRED", message: "Authentication is required." } }, 401);
}
let root: Root;
let container: HTMLDivElement;
beforeEach(() => {
  (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  configureAuthenticatedTransport({ csrfToken: null, onUnauthorized: null });
  vi.restoreAllMocks();
});
async function change(selector: string, value: string) {
  const input = container.querySelector<HTMLInputElement | HTMLSelectElement>(selector)!;
  const prototype = input instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
  await act(async () => {
    Object.getOwnPropertyDescriptor(prototype, "value")!.set!.call(input, value);
    input.dispatchEvent(new Event(input instanceof HTMLSelectElement ? "change" : "input", { bubbles: true }));
  });
}
async function mountOnboarding(profile: AuthenticatedProfile) {
  const client = createSessionQueryClient();
  client.setQueryData(caseQueryKeys.executionProfile(profile.user_id), {
    registry_provider_mode: "LOCAL_MOCK", target_environment: "MOCK",
    registry_system: "ACRA", registry_environment: "MOCK", idp_environment: "LOCAL", persistence: "Process-local",
  });
  await act(async () => root.render(
    <MemoryRouter initialEntries={["/new-onboarding"]}>
      <QueryClientProvider client={client}><App actor={profile} onLogout={() => undefined} /></QueryClientProvider>
    </MemoryRouter>,
  ));
  return client;
}

describe("Session 1 onboarding forms", () => {
  it("starts ordinary onboarding with blank identity, no documents, and a spaced fixed team", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(json([]));
    const client = await mountOnboarding(rm);
    expect(container.querySelector<HTMLInputElement>("#home-uen")!.value).toBe("");
    expect(container.querySelector<HTMLInputElement>("#home-legal-name")!.value).toBe("");
    expect(container.querySelector("label[for='home-legal-name']")!.textContent).toBe("Company Legal Name");
    expect(container.querySelector<HTMLInputElement>("#home-document")!.files).toHaveLength(0);
    expect(container.querySelector<HTMLSelectElement>("#home-priority")!.value).toBe("");
    expect(container.querySelector("#director-team-id")).toBeNull();
    const teamLabel = Array.from(container.querySelectorAll<HTMLElement>(".control-label")).find((label) => label.textContent === "Team")!;
    expect(teamLabel.style.display).toBe("block");
    expect(teamLabel.style.marginBottom).toBe("6px");
    expect(teamLabel.parentElement!.textContent).toContain("Alpha onboarding");
    expect(teamLabel.parentElement!.textContent).toContain("Your assigned team owns this case.");
    client.clear();
  });

  it("keeps Director team selection inside the details card and clears all drafts on a fresh start", async () => {
    const request = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const path = new URL(String(input), "http://frontend.test").pathname;
      if (path === "/api/teams/options") return json(teams);
      if (path === "/api/clm/zero-touch/cases" && init?.method === "POST") return json(created, 201);
      if (path.endsWith("/intake/documents")) return json({ detail: { code: "SYNTHETIC_INTAKE_STOP", message: "Synthetic intake paused." } }, 400);
      return json([]);
    });
    const client = await mountOnboarding(director);
    await vi.waitFor(() => expect(container.querySelector<HTMLSelectElement>("#director-team-id")!.options).toHaveLength(3));
    const team = container.querySelector<HTMLSelectElement>("#director-team-id")!;
    expect(team.closest(".card")).toBe(container.querySelector("#home-uen")!.closest(".card"));
    expect(team.closest("form")).not.toBeNull();
    expect(team.value).toBe("");
    expect(container.querySelector<HTMLButtonElement>("button[type='submit']")!.disabled).toBe(true);
    expect(container.textContent).not.toContain("Select a team above");
    await change("#director-team-id", "TEAM_B");
    await change("#home-uen", "202400001A");
    await change("#home-legal-name", "SYNTHETIC SESSION ONE PTE. LTD.");
    await change("#home-country", "SG");
    await change("#home-priority", "10");
    const file = new File(["synthetic"], "synthetic-session-one.txt", { type: "text/plain" });
    const fileInput = container.querySelector<HTMLInputElement>("#home-document")!;
    Object.defineProperty(fileInput, "files", { configurable: true, value: [file] });
    await act(async () => fileInput.dispatchEvent(new Event("change", { bubbles: true })));
    await act(async () => container.querySelector("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    await vi.waitFor(() => expect(container.textContent).toContain("Synthetic intake paused."));
    const createRequest = request.mock.calls.find(([input, init]) => String(input).endsWith("/api/clm/zero-touch/cases") && init?.method === "POST")!;
    expect(JSON.parse(createRequest[1]!.body as string)).toMatchObject({ uen: "202400001A", legal_name: "SYNTHETIC SESSION ONE PTE. LTD.", team_id: "TEAM_B", priority: 10 });
    await act(async () => container.querySelector<HTMLButtonElement>("button[aria-label='Start a new case']")!.click());
    await vi.waitFor(() => expect(container.querySelector("#home-uen")).not.toBeNull());
    for (const selector of ["#home-uen", "#home-legal-name", "#home-country", "#home-priority", "#director-team-id"]) {
      expect(container.querySelector<HTMLInputElement | HTMLSelectElement>(selector)!.value).toBe("");
    }
    expect(container.textContent).not.toContain(file.name);
    expect(container.textContent).not.toContain("Synthetic intake paused.");
    expect(container.querySelector<HTMLInputElement>("#home-document")!.files).toHaveLength(0);
    expect(request.mock.calls.filter(([, init]) => init?.method === "DELETE")).toHaveLength(0);
    client.clear();
  });
});

type Auth = ReturnType<typeof useAuth>;
async function mountSession(profile: AuthenticatedProfile | null, path: string) {
  let auth!: Auth;
  let client!: QueryClient;
  let navigate!: ReturnType<typeof useNavigate>;
  const renders: Array<{ user: string; path: string }> = [];
  const request = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const pathname = new URL(String(input), "http://frontend.test").pathname;
    if (pathname === "/api/auth/me") return profile ? json(session(profile)) : denied();
    if (pathname === "/api/auth/login") {
      const userId = JSON.parse(init!.body as string).user_id;
      return json(session([rm, director, hr].find((candidate) => candidate.user_id === userId)!));
    }
    if (pathname === "/api/auth/logout") return new Response(null, { status: 204 });
    if (pathname === "/api/system/execution-profile") return denied();
    return json([]);
  });
  function Probe() {
    auth = useAuth();
    client = useQueryClient();
    navigate = useNavigate();
    const location = useLocation();
    const [draft, setDraft] = useState("");
    if (auth.session) renders.push({ user: auth.session.profile.user_id, path: location.pathname });
    return <><output data-location>{location.pathname}</output><output data-status>{auth.status}</output>
      {auth.session ? <input data-session-draft value={draft} onChange={(event) => setDraft(event.target.value)} /> : <LoginPage />}</>;
  }
  await act(async () => root.render(<MemoryRouter initialEntries={[path]}><AuthProvider><Probe /></AuthProvider></MemoryRouter>));
  await vi.waitFor(() => expect(container.querySelector("[data-status]")!.textContent).toBe(profile ? "authenticated" : "anonymous"));
  return { auth: () => auth, client: () => client, navigate: (destination: string) => navigate(destination), renders, request };
}

describe("Session 1 session navigation", () => {
  it("keeps login identity empty with no Maya placeholder", async () => {
    await mountSession(null, "/");
    const userId = container.querySelector<HTMLInputElement>("#user-id")!;
    expect(userId.value).toBe("");
    expect(userId.getAttribute("placeholder")).toBeNull();
    expect(container.textContent).not.toContain("Maya");
  });

  it.each([
    [hr, director, "/admin/goldtier-sandbox"],
    [director, hr, "/cases"],
    [rm, director, "/new-onboarding"],
  ] as const)("resets logout and replacement login from %s", async (first, second, path) => {
    const harness = await mountSession(first, path);
    await change("[data-session-draft]", "first-session-draft");
    const oldKey = caseQueryKeys.detail(first.user_id, caseId);
    harness.client().setQueryData(oldKey, { private: "first-session-only" });
    let aborted = false;
    let release!: (value: unknown) => void;
    const pending = harness.client().fetchQuery({ queryKey: ["auth", first.user_id, "pending"], queryFn: ({ signal }) => {
      signal.addEventListener("abort", () => { aborted = true; });
      return new Promise((resolve) => { release = resolve; });
    } }).catch(() => undefined);
    await act(async () => harness.auth().logout());
    expect(container.querySelector("[data-location]")!.textContent).toBe("/");
    expect(harness.client().getQueryData(oldKey)).toBeUndefined();
    expect(aborted).toBe(true);
    // An anonymous user may browse a path; interactive login still starts at root.
    await act(async () => harness.navigate(path));
    await act(async () => harness.auth().login(second.user_id, "synthetic-test-credential"));
    expect(container.querySelector("[data-location]")!.textContent).toBe("/");
    expect(container.querySelector<HTMLInputElement>("[data-session-draft]")!.value).toBe("");
    expect(harness.renders.filter((render) => render.user === second.user_id).every((render) => render.path === "/")).toBe(true);
    await act(async () => { release({ private: "late-first-session-only" }); await pending; });
    expect(harness.client().getQueryData(["auth", first.user_id, "pending"])).toBeUndefined();
    expect(harness.request.mock.calls.filter(([input]) => String(input).includes("/api/auth/me"))).toHaveLength(1);
  });

  it("preserves a restored deep link and resets draft state even on same-user interactive replacement", async () => {
    const path = `/cases/${caseId}`;
    const harness = await mountSession(rm, path);
    expect(container.querySelector("[data-location]")!.textContent).toBe(path);
    await change("[data-session-draft]", "old-draft");
    await act(async () => harness.auth().login(rm.user_id, "synthetic-test-credential"));
    expect(container.querySelector("[data-location]")!.textContent).toBe("/");
    expect(container.querySelector<HTMLInputElement>("[data-session-draft]")!.value).toBe("");
    expect(harness.request.mock.calls.filter(([input]) => String(input).includes("/api/auth/me"))).toHaveLength(1);
  });

  it("clears current-session 401 cache and route without restoring a previous privileged route", async () => {
    const harness = await mountSession(hr, "/admin/goldtier-sandbox");
    harness.client().setQueryData(["auth", hr.user_id, "sensitive"], { private: true });
    await act(async () => { await expect(fetchExecutionProfile()).rejects.toMatchObject({ status: 401 }); });
    expect(container.querySelector("[data-status]")!.textContent).toBe("anonymous");
    expect(container.querySelector("[data-location]")!.textContent).toBe("/");
    expect(harness.client().getQueryCache().getAll()).toHaveLength(0);
  });
});
