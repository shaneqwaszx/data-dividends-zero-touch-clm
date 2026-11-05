// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ModelOverview, ModelProfileView, ProviderSetup, SetupView } from "../../aiAssistant";
import { configureAuthenticatedTransport } from "../../api";
import { GuidedSetup } from "./GuidedSetup";

// D-118: the guided setup. Synthetic views only; every request is answered by a stub.

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root | null = null;
let container: HTMLDivElement | null = null;

afterEach(() => {
  if (root) act(() => root?.unmount());
  container?.remove();
  root = null;
  container = null;
  configureAuthenticatedTransport({ csrfToken: null, onUnauthorized: null });
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

async function waitFor(assertion: () => void): Promise<void> {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    try {
      assertion();
      return;
    } catch (error) {
      if (attempt === 39) throw error;
      await act(async () => new Promise((resolve) => setTimeout(resolve, 0)));
    }
  }
}

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

function profile(overrides: Partial<ModelProfileView>): ModelProfileView {
  return {
    profile_id: "claude_balanced", display_name: "Claude Sonnet 5.5 Balanced", source: "code", deployment: "anthropic",
    model_id: "claude-sonnet-5-5", model_version: null, endpoint: null, context_window_tokens: null, max_answer_tokens: 3000,
    temperature: null, timeout_seconds: 60, streaming: true, fingerprint: "f", status: "selectable", reason: null,
    details: null, active: false, connection_test: null, qualification: null, activation_blockers: ["NOT_QUALIFIED"],
    eligible_qualification: null,
    paid_qualification: { calls: 2, reservation_micro_usd: 96_000, estimate_micro_usd: 192_000, effective_remaining_micro_usd: 5_000_000, refusal: null, sufficient: true },
    ...overrides,
  };
}

const local = profile({
  profile_id: "local_ministral", display_name: "Local Ministral", source: "file", deployment: "local", model_id: "ministral-3:8b",
  paid_qualification: null,
});

function overviewWith(claude: ModelProfileView, enabled: boolean, read = false): ModelOverview {
  return {
    configured: true, file_status: "ok", file_errors: [], model_enabled: true, revision: 4,
    active: { profile_id: "env_default", display_name: "Environment baseline", model_id: "ministral-3:8b", prompt_limit: null,
      qualification_id: null, changed_at: null, changed_by: null, config_changed: false, reverted: null },
    last_good: null, quality: { status: "NOT_SCORED", reason: null }, basis: "b", running: null,
    profiles: [claude, local],
    anthropic_setup: {
      managed: true, readable: true, source: enabled ? "hr" : "none", enabled, readiness: enabled ? null : "ANTHROPIC_NOT_ENABLED",
      local_deployment: true,
      record: enabled ? { revision: 1, enabled: true, workspace_id: "wrkspc_fyp", workspace_limit_micro_usd: 5_000_000,
        workspace_limit_basis: "owner_confirmed", confirmations: [], changed_at: "2026-11-04T00:00:00Z", changed_by: "hr-admin" } : null,
      workspace_read: read ? { workspace_id: "wrkspc_fyp", at: "2026-11-04T00:00:00Z" } : null,
      confirmations_required: ["dedicated_workspace", "inference_key_only", "key_revoked_at_fyp_end", "workspace_limit_set"],
      workspace_limit_max_micro_usd: 30_000_000,
    },
  };
}

function provider(name: "anthropic" | "openrouter", overrides: Partial<ProviderSetup> = {}): ProviderSetup {
  return {
    provider: name, ledger: "missing", code: null, accounting_mode: null, origin: null, opening_basis: null,
    allowance_default_micro_usd: 5_000_000, allowance_max_micro_usd: 5_000_000, session: null,
    breaker_open: false, breaker_code: null, resumable: false, resume_blocker: null, blockers: [], ...overrides,
  };
}

const setupView = (anthropic: Partial<ProviderSetup> = {}): SetupView => ({
  providers: { anthropic: provider("anthropic", anthropic), openrouter: provider("openrouter") },
});

interface Sent { method: string; url: string; body: unknown }

const PASSED = { outcome: "passed", code: null, listed: null, complete_ms: null, stream_ms: null, first_piece_ms: null };

function stub(setup: SetupView, sent: Sent[], connection: unknown = PASSED) {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    if (method !== "GET") sent.push({ method, url, body: init?.body ? JSON.parse(String(init.body)) : null });
    if (url.includes("/workspace-read")) return json({ outcome: "passed", code: null, workspace_id: "wrkspc_fyp", setup: null });
    if (url.includes("/connection-test")) return json(connection);
    if (url.includes("/setup")) return json(setup);
    return json({});
  });
}

function mount(overview: ModelOverview, fetchMock: ReturnType<typeof vi.fn>, choose = "claude_balanced",
  describe?: (code: string | null | undefined) => string): HTMLDivElement {
  vi.stubGlobal("fetch", fetchMock);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
  act(() => root?.render(
    <MemoryRouter><QueryClientProvider client={client}>
      <GuidedSetup userId="hr-admin" overview={overview} busy={false} nameOf={(_id, fallback) => fallback} describe={describe} onChanged={() => undefined} />
    </QueryClientProvider></MemoryRouter>,
  ));
  const radio = container.querySelector(`input[name=guided-model][value=${choose}]`) as HTMLInputElement;
  act(() => radio.click());
  return container;
}

function button(scope: ParentNode, label: string): HTMLButtonElement {
  const found = [...scope.querySelectorAll("button")].find((item) => item.textContent?.trim() === label);
  if (!found) throw new Error(`no button ${label}`);
  return found as HTMLButtonElement;
}

function type(input: HTMLInputElement, value: string): void {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
  act(() => {
    setter.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

describe("GuidedSetup (D-118)", () => {
  it("shows the US$5.00 session by default with nothing to confirm, and saves then reads the workspace", async () => {
    const sent: Sent[] = [];
    const page = mount(overviewWith(profile({}), false), stub(setupView(), sent));
    await waitFor(() => expect(page.textContent).toContain("Not started (US$5.00 at the first paid action)"));
    expect(page.textContent).not.toMatch(/reconcil|attest|P1/i);
    type(page.querySelector("#guided-key") as HTMLInputElement, "sk-ant-api03-test-only");
    await act(async () => button(page, "Save & test").click());
    await waitFor(() => expect(sent.map((item) => `${item.method} ${item.url.split("/api/assistant")[1]}`)).toEqual([
      "PUT /admin/models/credential/anthropic",
      "POST /admin/models/provider/anthropic/workspace-read",
    ]));
    expect((page.querySelector("#guided-key") as HTMLInputElement).value).toBe("");
  });

  it("enables Claude only with the owner's statements, and asks nothing about earlier spend", async () => {
    const sent: Sent[] = [];
    const page = mount(overviewWith(profile({}), false, true), stub(setupView(), sent));
    await waitFor(() => expect(page.textContent).toContain("One-time Claude setup"));
    expect(page.querySelector("input[name=guided-opening]")).toBeNull(); // D-118 amendment P5
    const enable = button(page, "Enable Claude");
    expect(enable.disabled).toBe(true);
    const boxes = [...page.querySelectorAll(".guided-claude-setup input[type=checkbox]")] as HTMLInputElement[];
    act(() => boxes[0].click());
    expect(button(page, "Enable Claude").disabled).toBe(true); // the FYP-end revocation is unstated
    act(() => boxes[1].click());
    expect(button(page, "Enable Claude").disabled).toBe(false);
    await act(async () => button(page, "Enable Claude").click());
    await waitFor(() => expect(sent[0]?.url).toContain("/admin/models/provider/anthropic"));
    expect(sent[0].body).toMatchObject({
      enabled: true, workspace_id: "wrkspc_fyp", workspace_limit_micro_usd: 5_000_000,
      confirmations: ["dedicated_workspace", "workspace_limit_set", "inference_key_only", "key_revoked_at_fyp_end"],
    });
  });

  it("runs the free check, then qualifies with one paid confirmation, and activates with one more", async () => {
    const sent: Sent[] = [];
    const ready = profile({ connection_test: { outcome: "passed", code: null, listed: null, complete_ms: null, stream_ms: null, first_piece_ms: null } });
    const page = mount(overviewWith(ready, true), stub(setupView({ ledger: "ready", accounting_mode: "provider_capped" }), sent));
    await act(async () => button(page, "Run qualification…").click());
    await waitFor(() => expect(document.querySelectorAll("[role=dialog]")).toHaveLength(1));
    expect(sent.map((item) => item.url.split("/admin/models")[1])).toEqual(["/claude_balanced/connection-test"]);
    const dialogs = document.querySelectorAll("[role=dialog]");
    expect(dialogs[0].textContent).toContain("Run 2 paid test calls?");
    expect(dialogs[0].textContent).toContain("US$0.19");
    expect(dialogs[0].textContent).not.toContain("no room");
    await act(async () => button(dialogs[0], "Run paid test calls").click());
    await waitFor(() => expect(sent[1]?.body).toEqual({ confirm_paid_calls: 2 }));

    const qualified = profile({ ...ready, eligible_qualification: { qualification_id: "q", finished_at: null, is_latest: true }, activation_blockers: [] });
    if (root) act(() => root?.unmount());
    container?.remove();
    const second: Sent[] = [];
    const page2 = mount(overviewWith(qualified, true), stub(setupView({ ledger: "ready" }), second));
    act(() => button(page2, "Activate…").click());
    const dialog = document.querySelector("[data-testid=guided-activate]") as HTMLElement;
    expect(dialog.textContent).toContain("external, paid API");
    expect(button(dialog, "Activate").disabled).toBe(true);
    act(() => (dialog.querySelector("input[type=checkbox]") as HTMLInputElement).click());
    await act(async () => button(dialog, "Activate").click());
    await waitFor(() => expect(second[0]?.body).toEqual({ expected_revision: 4, acknowledge_quality_unscored: true }));
  });

  it("never opens the paid confirmation when the free connection check fails", async () => {
    const sent: Sent[] = [];
    const ready = profile({ connection_test: PASSED as ModelProfileView["connection_test"] });
    const page = mount(overviewWith(ready, true), stub(setupView({ ledger: "ready" }), sent, { ...PASSED, outcome: "failed", code: "WORKSPACE_MISMATCH" }),
      "claude_balanced", (code) => `text for ${code}`);
    await act(async () => button(page, "Run qualification…").click());
    await waitFor(() => expect(page.textContent).toContain("The connection check did not pass: text for WORKSPACE_MISMATCH"));
    expect(document.querySelectorAll("[role=dialog]")).toHaveLength(0);
    expect(sent.map((item) => item.url.split("/admin/models")[1])).toEqual(["/claude_balanced/connection-test"]);
  });

  it("keeps step 3 waiting until the connection passed, and names a failed one", async () => {
    const failed = profile({ connection_test: { ...PASSED, outcome: "failed", code: "CREDENTIAL_MISSING" } as ModelProfileView["connection_test"] });
    const page = mount(overviewWith(failed, true), stub(setupView({ ledger: "ready" }), []), "claude_balanced", (code) => `text for ${code}`);
    await waitFor(() => expect(page.querySelector("[data-testid=guided-connection]")?.textContent).toContain("Connection check failed: text for CREDENTIAL_MISSING"));
    expect(page.textContent).not.toContain("Run qualification…");
  });

  it("offers the free re-test after a stored failure, without retyping the key", async () => {
    const sent: Sent[] = [];
    const failed = profile({ connection_test: { ...PASSED, outcome: "failed", code: "PREFLIGHT_FAILED" } as ModelProfileView["connection_test"] });
    const page = mount(overviewWith(failed, true), stub(setupView({ ledger: "ready" }), sent), "claude_balanced", (code) => `text for ${code}`);
    await waitFor(() => expect(page.querySelector("[data-testid=guided-connection]")?.textContent).toContain("then test again"));
    await act(async () => button(page, "Test again").click());
    await waitFor(() => expect(sent.map((item) => item.url.split("/admin/models")[1])).toEqual(["/claude_balanced/connection-test"]));
  });

  it("offers no re-test before any check has run", async () => {
    const untested = profile({ connection_test: null });
    const page = mount(overviewWith(untested, true), stub(setupView({ ledger: "ready" }), []), "claude_balanced", (code) => `text for ${code}`);
    await waitFor(() => expect(page.textContent).toContain("Save & test"));
    expect(page.textContent).not.toContain("Test again");
  });

  it("names the missing question list instead of a budget shortfall, and keeps step 3 closed", async () => {
    const ready = profile({
      connection_test: PASSED as ModelProfileView["connection_test"],
      paid_qualification: { calls: null, reservation_micro_usd: 96_000, estimate_micro_usd: null, effective_remaining_micro_usd: 1_000_000,
        refusal: "REMOTE_MANIFEST_MISSING", sufficient: false, unavailable: "REMOTE_MANIFEST_MISSING", limits: { session: 1_000_000 }, blocking: null },
    });
    const page = mount(overviewWith(ready, true), stub(setupView({ ledger: "ready" }), []), "claude_balanced", (code) => `text for ${code}`);
    await waitFor(() => expect(page.querySelector("[data-testid=guided-qualify-blocker]")?.textContent).toContain("text for REMOTE_MANIFEST_MISSING"));
    expect(button(page, "Run qualification…").disabled).toBe(true);
    expect(page.textContent).not.toMatch(/no room|insufficient/i);
  });

  it("qualifies within a deliberate US$1.00 session, and names the session when it is too small", async () => {
    const session = { session_id: "s".repeat(32), revision: 2, allowance_micro_usd: 1_000_000, settled_micro_usd: 0, held_micro_usd: 0,
      committed_micro_usd: 0, remaining_micro_usd: 1_000_000, calls: 0, chat_calls: 0, started_at: "2026-11-04T00:00:00Z" };
    const fits = profile({
      connection_test: PASSED as ModelProfileView["connection_test"],
      paid_qualification: { calls: 2, reservation_micro_usd: 96_000, estimate_micro_usd: 192_000, effective_remaining_micro_usd: 1_000_000,
        refusal: null, sufficient: true, unavailable: null, limits: { session: 1_000_000, daily: 5_000_000, lifetime: 5_000_000 }, blocking: null },
    });
    const page = mount(overviewWith(fits, true), stub(setupView({ ledger: "ready", session }), []));
    await waitFor(() => expect(page.textContent).toContain("Session allowance US$1.00, US$1.00 left"));
    await act(async () => button(page, "Run qualification…").click());
    await waitFor(() => expect(document.querySelector("[data-testid=guided-limits]")?.textContent).toContain("Session allowanceUS$1.00 left"));
    expect(button(document.querySelector("[role=dialog]")!, "Run paid test calls").disabled).toBe(false);

    if (root) act(() => root?.unmount());
    container?.remove();
    const tight = profile({
      connection_test: PASSED as ModelProfileView["connection_test"],
      paid_qualification: { calls: 2, reservation_micro_usd: 96_000, estimate_micro_usd: 192_000, effective_remaining_micro_usd: 100_000,
        refusal: "SESSION_ALLOWANCE_INSUFFICIENT", sufficient: false, unavailable: null, limits: { session: 100_000, daily: 5_000_000, lifetime: 5_000_000 }, blocking: "session" },
    });
    const page2 = mount(overviewWith(tight, true), stub(setupView({ ledger: "ready", session: { ...session, remaining_micro_usd: 100_000 } }), []));
    await act(async () => button(page2, "Run qualification…").click());
    const dialog = await (async () => { await waitFor(() => expect(document.querySelector("[role=dialog]")).not.toBeNull()); return document.querySelector("[role=dialog]")!; })();
    expect(dialog.textContent).toContain("This session's allowance has US$0.10 left");
    expect(dialog.textContent).toContain("Session allowanceUS$0.10 left (too little)");
    expect(dialog.textContent).not.toContain("Today's limitUS$5.00 left (too little)");
    expect(button(dialog, "Run paid test calls").disabled).toBe(true);
  });

  it("lets an enablement record from before D-118 create its session store by confirming again", async () => {
    const sent: Sent[] = [];
    const page = mount(overviewWith(profile({}), true, true), stub(setupView({ ledger: "missing" }), sent));
    await waitFor(() => expect(page.textContent).toContain("Finish Claude setup (creates its session store)"));
    const boxes = [...page.querySelectorAll(".guided-claude-setup input[type=checkbox]")] as HTMLInputElement[];
    act(() => boxes[0].click());
    act(() => boxes[1].click());
    await act(async () => button(page, "Confirm and create the session store").click());
    await waitFor(() => expect(sent[0]?.url).toContain("/admin/models/provider/anthropic"));
    expect(sent[0].body).toMatchObject({ expected_revision: 1, enabled: true, workspace_id: "wrkspc_fyp", workspace_limit_micro_usd: 5_000_000 });
  });

  it("re-confirming an existing record keeps its stored workspace limit (QG M1)", async () => {
    const sent: Sent[] = [];
    const overview = overviewWith(profile({}), true, true);
    overview.anthropic_setup!.record!.workspace_limit_micro_usd = 1_000_000;
    const page = mount(overview, stub(setupView({ ledger: "missing" }), sent));
    await waitFor(() => expect((page.querySelector("#guided-limit") as HTMLInputElement | null)?.value).toBe("1.00"));
    const boxes = [...page.querySelectorAll(".guided-claude-setup input[type=checkbox]")] as HTMLInputElement[];
    act(() => boxes[0].click());
    act(() => boxes[1].click());
    await act(async () => button(page, "Confirm and create the session store").click());
    await waitFor(() => expect(sent[0]?.body).toMatchObject({ workspace_limit_micro_usd: 1_000_000 }));
  });

  it("lets HR lower the allowance but never above US$5.00", async () => {
    const sent: Sent[] = [];
    const ready = profile({ connection_test: { outcome: "passed", code: null, listed: null, complete_ms: null, stream_ms: null, first_piece_ms: null } });
    const page = mount(overviewWith(ready, true), stub(setupView({ ledger: "ready" }), sent));
    act(() => button(page, "Use a smaller amount").click());
    type(page.querySelector("#guided-allowance") as HTMLInputElement, "5.01");
    await act(async () => button(page, "Save").click());
    expect(page.textContent).toContain("no more than US$5.00");
    expect(sent).toEqual([]);
    type(page.querySelector("#guided-allowance") as HTMLInputElement, "2.50");
    await act(async () => button(page, "Save").click());
    await waitFor(() => expect(sent[0]?.body).toEqual({ provider: "anthropic", allowance_micro_usd: 2_500_000, expected_session_id: null }));
  });

  it("needs no key or allowance for a local model", async () => {
    const sent: Sent[] = [];
    const page = mount(overviewWith(profile({}), false), stub(setupView(), sent), "local_ministral");
    expect(page.querySelector("#guided-key")).toBeNull();
    expect(page.textContent).not.toContain("Session allowance");
  });

  it("offers HR a resume for a financial stop, and sends routing stops to the owner", async () => {
    const sent: Sent[] = [];
    const resumable = setupView({
      ledger: "ready", breaker_open: true, breaker_code: "usage_missing", resumable: true,
      blockers: [{ code: "BREAKER_OPEN:usage_missing", who: "hr", action: "RESUME" }],
    });
    const page = mount(overviewWith(profile({}), true), stub(resumable, sent));
    await waitFor(() => expect(page.textContent).toContain("Every charge is kept and nothing is retried"));
    await act(async () => button(page, "Resume, keeping the charge").click());
    await waitFor(() => expect(sent[0]?.body).toEqual({ provider: "anthropic", code: "usage_missing" }));

    if (root) act(() => root?.unmount());
    container?.remove();
    const genuine = setupView({
      ledger: "ready", breaker_open: true, breaker_code: "routing_anomaly", resumable: false,
      blockers: [{ code: "BREAKER_OPEN:routing_anomaly", who: "owner", action: "OWNER" }],
    });
    const page2 = mount(overviewWith(profile({}), true), stub(genuine, []));
    await waitFor(() => expect(page2.textContent).toContain("stopped for the owner (routing_anomaly)"));
    expect([...page2.querySelectorAll("button")].some((item) => item.textContent?.includes("Resume"))).toBe(false);
  });
});
