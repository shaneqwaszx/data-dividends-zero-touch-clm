// @vitest-environment jsdom

import { act, StrictMode, useState } from "react";
import { createRoot, type Root } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MODEL_AUDIT_LIMIT, type AnthropicSetup, type ModelAuditEvent, type ModelBudgetStatus, type ModelClaudeBudget, type ModelClaudeReconciliation, type ModelClaudeSpendingControls, type ModelDataAccess, type ModelOverview, type ModelProfileView, type ModelQualification } from "../aiAssistant";
import { configureAuthenticatedTransport } from "../api";
import { requiredCapabilityForPath, paths, WorkspaceTabs } from "../navigation";
import type { AuthenticatedProfile } from "../types";
import { ConsoleDialog, consoleSection, sectionSearch, type ConsoleSection } from "./aiModels/ConsoleShell";
import AiModelManagement, {
  ANY_PROVIDER,
  AUDIT_REFRESH_MS,
  modelManagementQueryKeys,
  profileName,
  readable,
  amountText,
  RUNNING_REFRESH_MS,
  toMicroUsd,
} from "./AiModelManagement";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const hr: AuthenticatedProfile = {
  user_id: "hr-admin", display_name: "HR Admin", role: "HR", team_id: null,
  team_display_name: null, team_type: null, team_description: "", client_scope_label: "",
  capabilities: ["IDENTITY_ADMIN", "MODEL_CONFIG_MANAGE"],
};
const director: AuthenticatedProfile = {
  ...hr, user_id: "olivia-koh", role: "DIRECTOR",
  capabilities: ["CASE_ACCESS", "CASE_GLOBAL", "POLICY_APPROVE", "POLICY_VIEW", "TARGET_RECOVERY"],
};
const rm: AuthenticatedProfile = {
  ...hr, user_id: "ethan-tan", role: "RELATIONSHIP_MANAGER", team_id: "TEAM_A",
  capabilities: ["CASE_ACCESS", "POLICY_VIEW"],
};

const qualification: ModelQualification = {
  qualification_id: "a".repeat(32), status: "passed", code: null,
  started_at: "2026-10-27T01:00:00+00:00", started_by: "hr-admin",
  finished_at: "2026-10-27T01:05:00+00:00", done_turns: 84, total_turns: 84,
  cancel_requested: false, current: true,
  gates: [
    { gate: "G-3", rule: "unsafe displayed lines = 0", value: 0, passed: true, gating: true },
    { gate: "G-5", rule: "no allowed line selected (reported only)", value: 0.25, passed: true, gating: false },
    { gate: "G-6", rule: "kept / written model lines >= 0.70", value: 0.82, passed: true, gating: true },
  ],
  metrics: { fallback_reasons: { none: 80, policy_no_allowed_line: 4 }, latency_total_ms_p50: 900, latency_total_ms_p95: 1600 },
  lines: { model_selected_lines: 120, guard_withheld_lines: 9, application_required_lines: 6, deterministic_fallbacks: 4 },
  capacity: { status: "verified", prompt_limit: 31000 },
  connection: null,
  quality: { status: "NOT_SCORED", reason: "OWNER_GOLD_NOT_LABELLED" },
  reproducibility: { harness_version: "model-qualification/1", turns: 84 },
};

function profile(overrides: Partial<ModelProfileView>): ModelProfileView {
  return {
    profile_id: "env_default", display_name: "Environment baseline", source: "environment",
    deployment: "openai_compatible", model_id: "ministral-3:8b", model_version: null,
    endpoint: "127.0.0.1:11434", context_window_tokens: null, max_answer_tokens: 600,
    temperature: 0.2, timeout_seconds: 90, streaming: true, fingerprint: "0123456789ab",
    status: "selectable", reason: null, active: true, connection_test: null,
    qualification: null, activation_blockers: [], ...overrides,
  };
}

const overview: ModelOverview = {
  configured: true, file_status: "ok", file_errors: [], model_enabled: true, revision: 3,
  active: {
    profile_id: "env_default", display_name: "Environment baseline", model_id: "ministral-3:8b",
    prompt_limit: null, qualification_id: null, changed_at: null, changed_by: null,
    config_changed: false, reverted: null,
  },
  last_good: null,
  quality: { status: "NOT_SCORED", reason: "OWNER_GOLD_NOT_LABELLED" },
  basis: "abcdef012345",
  running: null,
  profiles: [
    profile({}),
    profile({
      profile_id: "lmstudio_qwen3_8b", display_name: "Qwen3 8B (LM Studio)", source: "file",
      deployment: "lm_studio", model_id: "qwen3:8b", endpoint: "127.0.0.1:1234",
      context_window_tokens: 32768, active: false, qualification,
    }),
    profile({
      profile_id: "openrouter_gpt_oss_120b", display_name: "GPT-OSS 120B via OpenRouter (remote)",
      source: "code", deployment: "remote", endpoint: null, status: "pending_authorisation",
      reason: "REMOTE_NOT_AUTHORISED", active: false, activation_blockers: ["REMOTE_NOT_AUTHORISED"],
    }),
  ],
};

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

function server(data: ModelOverview, onPost?: (url: string, body: unknown) => Response) {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (init?.method === "POST") return onPost ? onPost(url, JSON.parse(String(init.body))) : json({});
    if (url.endsWith("/api/assistant/admin/models")) return json(data);
    if (url.includes("/api/assistant/admin/models/audit")) {
      return json({ events: [{ seq: 1, at: "2026-10-27T01:00:00+00:00", actor: "ethan-tan", role: "RELATIONSHIP_MANAGER", action: "ACCESS_REFUSED", profile_id: null, fingerprint: null, outcome: "refused", code: "MODEL_CONFIG_FORBIDDEN", revision: null }] });
    }
    return json({ detail: { code: "NOT_FOUND", message: "No such model profile." } }, 404);
  });
}

function mount(fetchMock: ReturnType<typeof vi.fn>, section: ConsoleSection = "overview"): HTMLDivElement {
  vi.stubGlobal("fetch", fetchMock);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
  const entry = `${paths.aiModels}${sectionSearch(section)}`;
  act(() => root?.render(<MemoryRouter initialEntries={[entry]}><QueryClientProvider client={client}><AiModelManagement actor={hr} /></QueryClientProvider></MemoryRouter>));
  return container;
}

// D-100: a configuration's actions are in the inspector once its tile is selected.
function button(view: HTMLElement, label: string, row?: string): HTMLButtonElement {
  let scope: ParentNode = view;
  if (row) {
    const tile = [...view.querySelectorAll<HTMLButtonElement>("[data-config-tile]")].find((item) => item.textContent?.includes(row));
    if (!tile) throw new Error(`no configuration ${row}`);
    if (tile.getAttribute("aria-pressed") !== "true") act(() => tile.click());
    scope = view.querySelector("[data-testid=model-inspector]") ?? view;
  }
  const found = [...scope.querySelectorAll("button")].find((item) => item.textContent === label);
  if (!found) throw new Error(`no button ${label}`);
  return found as HTMLButtonElement;
}

/** Opens a console section from its navigation link, as HR would. */
function go(view: HTMLElement, label: string): void {
  const link = [...view.querySelectorAll<HTMLAnchorElement>(".console-nav__link")].find((item) => item.textContent?.startsWith(label));
  if (!link) throw new Error(`no section ${label}`);
  act(() => link.click());
}

describe("AI model management access", () => {
  it("is navigable only with MODEL_CONFIG_MANAGE, which Directors and RMs do not hold", () => {
    const markup = (actor: AuthenticatedProfile) => renderToStaticMarkup(<MemoryRouter><WorkspaceTabs actor={actor} /></MemoryRouter>);
    expect(markup(hr)).toContain("AI Models");
    expect(markup(hr)).toContain("/admin/ai-models");
    expect(markup(director)).not.toContain("AI Models");
    expect(markup(rm)).not.toContain("AI Models");
    expect(requiredCapabilityForPath(paths.aiModels)).toBe("MODEL_CONFIG_MANAGE");
  });

  it("keeps its server state under the signed-in user's key, apart from any case", () => {
    expect(modelManagementQueryKeys.overview("hr-a")).toEqual(["auth", "hr-a", "assistant-models", "overview"]);
    expect(modelManagementQueryKeys.overview("hr-a")).not.toEqual(modelManagementQueryKeys.overview("hr-b"));
    expect(JSON.stringify(modelManagementQueryKeys.audit("hr-a"))).not.toContain("cases");
  });
});

describe("AiModelManagement", () => {
  it("shows the active model, the catalogue, a pending remote model and the audit history", async () => {
    const view = mount(server(overview));
    await waitFor(() => expect(view.textContent).toContain("Qwen3 8B (LM Studio)"));
    expect(view.textContent).toContain("Active model");
    expect(view.textContent).toContain("Pending authorisation");
    expect(view.textContent).toContain("Remote inference is not authorised for CLM use");
    expect(button(view, "Activate", "GPT-OSS").disabled).toBe(true);
    expect(button(view, "Test connection", "GPT-OSS").disabled).toBe(true);
    expect(button(view, "No earlier model to roll back to").disabled).toBe(true);
    go(view, "Audit History");
    await waitFor(() => expect(view.textContent).toContain("Access refused"));
  });

  it("shows qualification as technical only, with answer quality not scored and G-5 reported only", async () => {
    const view = mount(server(overview));
    await waitFor(() => expect(view.textContent).toContain("Qwen3 8B (LM Studio)"));
    { const target = button(view, "View qualification results", "Qwen3"); act(() => target.click()); }
    await waitFor(() => expect(view.textContent).toContain("Qualification: Qwen3 8B"));
    expect(view.textContent).toContain("NOT SCORED");
    expect(view.textContent).toContain("A pass is not proof of answer quality");
    expect(view.textContent).toContain("Reported only");
    expect(view.textContent).toContain("Application-required lines");
    expect(view.textContent).toContain("Guard-withheld lines");
  });

  it("requires the not-scored acknowledgement before activating and sends only the profile id and revision", async () => {
    const posts: Array<{ url: string; body: unknown }> = [];
    const fetchMock = server(overview, (url, body) => {
      posts.push({ url, body });
      return json(overview);
    });
    const view = mount(fetchMock);
    await waitFor(() => expect(view.textContent).toContain("Qwen3 8B (LM Studio)"));
    { const target = button(view, "Activate", "Qwen3"); act(() => target.click()); }
    expect(view.textContent).toContain("Activate Qwen3 8B (LM Studio)?");
    const confirm = button(view, "Confirm");
    expect(confirm.disabled).toBe(true);
    const box = view.querySelector('[role="dialog"] input[type="checkbox"]') as HTMLInputElement;
    act(() => box.click());
    expect(button(view, "Confirm").disabled).toBe(false);
    await act(async () => button(view, "Confirm").click());
    await waitFor(() => expect(posts).toHaveLength(1));
    expect(posts[0].url).toContain("/api/assistant/admin/models/lmstudio_qwen3_8b/activate");
    expect(posts[0].body).toEqual({ expected_revision: 3, acknowledge_quality_unscored: true });
  });

  it("shows a refusal from the service with its fixed message", async () => {
    const view = mount(server(overview, () => json({ detail: { code: "REVISION_CONFLICT", message: "The model settings changed since this view. Refresh and try again." } }, 409)));
    await waitFor(() => expect(view.textContent).toContain("Qwen3 8B (LM Studio)"));
    { const target = button(view, "Test connection", "Qwen3"); await act(async () => target.click()); }
    await waitFor(() => expect(view.textContent).toContain("The model settings changed since this view."));
  });

  it("explains a start-up revert, an unconfigured server and an invalid profiles file", async () => {
    const reverted = { ...overview, active: { ...overview.active, reverted: "PROFILE_CHANGED" } };
    let view = mount(server(reverted));
    await waitFor(() => expect(view.textContent).toContain("could not be used at start-up"));
    expect(view.textContent).toContain("Its settings changed in the profiles file.");
    act(() => root?.unmount());
    root = null;
    container?.remove();

    view = mount(server({ ...overview, configured: false, file_status: "not_configured", profiles: [profile({})] }));
    await waitFor(() => expect(view.textContent).toContain("Model management is not configured on this server."));
    act(() => root?.unmount());
    root = null;
    container?.remove();

    view = mount(server({ ...overview, file_status: "invalid", file_errors: ["profiles.0.api_key"] }));
    await waitFor(() => expect(view.textContent).toContain("profiles.0.api_key"));
  });

  it("calls the session boundary on 401 so cached data is cleared", async () => {
    const client = new QueryClient();
    client.setQueryData(["auth", "hr-admin", "sentinel"], "cached");
    const unauthorized = vi.fn(() => client.clear());
    configureAuthenticatedTransport({ csrfToken: null, onUnauthorized: unauthorized });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json({ detail: { code: "AUTHENTICATION_REQUIRED", message: "Please sign in again." } }, 401)));
    container = document.createElement("div"); document.body.append(container); root = createRoot(container);
    act(() => root?.render(<MemoryRouter initialEntries={[paths.aiModels]}><QueryClientProvider client={client}><AiModelManagement actor={hr} /></QueryClientProvider></MemoryRouter>));
    await waitFor(() => expect(unauthorized).toHaveBeenCalled());
    expect(client.getQueryCache().getAll().some((query) => query.queryKey.includes("sentinel"))).toBe(false);
  });
});

describe("AiModelManagement smoke-test fixes (S-1 to S-3)", () => {
  it("re-reads the audit history when a background qualification ends, and on its own interval (S-1)", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      let overviewCalls = 0;
      let auditCalls = 0;
      const running: ModelOverview = {
        ...overview,
        running: { qualification_id: "b".repeat(32), profile_id: "lmstudio_qwen3_8b", done_turns: 40, total_turns: 84, started_by: "hr-admin" },
      };
      const view = mount(vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/api/assistant/admin/models")) {
          overviewCalls += 1;
          return json(overviewCalls === 1 ? running : overview);
        }
        if (url.includes("/api/assistant/admin/models/audit")) {
          auditCalls += 1;
          return json({ events: [] });
        }
        return json({ detail: { code: "NOT_FOUND", message: "No such model profile." } }, 404);
      }));
      await waitFor(() => expect(view.textContent).toContain("Qualification running"));
      await waitFor(() => expect(auditCalls).toBe(1));

      // The run ends in the background: the next overview no longer lists it.
      await act(async () => { await vi.advanceTimersByTimeAsync(RUNNING_REFRESH_MS + 100); });
      await waitFor(() => expect(view.textContent).not.toContain("Qualification running"));
      await waitFor(() => expect(auditCalls).toBe(2));

      // Events made elsewhere appear on the audit interval, with no page action.
      await act(async () => { await vi.advanceTimersByTimeAsync(AUDIT_REFRESH_MS + 100); });
      await waitFor(() => expect(auditCalls).toBe(3));
    } finally {
      vi.useRealTimers();
    }
  });

  it("names the rollback target in the confirmation heading (S-2)", async () => {
    const rolledForward: ModelOverview = {
      ...overview,
      active: { ...overview.active, profile_id: "lmstudio_qwen3_8b", display_name: "Qwen3 8B (LM Studio)" },
      last_good: { profile_id: "env_default", display_name: "Environment baseline" },
    };
    const view = mount(server(rolledForward));
    await waitFor(() => expect(view.textContent).toContain("Roll back to Environment baseline"));
    act(() => button(view, "Roll back to Environment baseline").click());
    expect(view.querySelector("#confirm-heading")?.textContent).toBe("Roll back to Environment baseline?");
  });

  it("shows failed gate ids as written (S-3)", async () => {
    expect(readable("GATES_FAILED:G-6,G-7")).toBe("Gates failed: G-6, G-7");
    expect(readable("GATES_FAILED:G-7")).toBe("Gates failed: G-7");
    expect(readable("QUALIFICATION_BUSY")).toBe("Qualification busy");
    const failed: ModelOverview = {
      ...overview,
      profiles: overview.profiles.map((item) => item.qualification
        ? { ...item, qualification: { ...item.qualification, status: "failed", code: "GATES_FAILED:G-6,G-7" } }
        : item),
    };
    const view = mount(server(failed));
    await waitFor(() => expect(view.textContent).toContain("Qwen3 8B (LM Studio)"));
    { const target = button(view, "View qualification results", "Qwen3"); act(() => target.click()); }
    await waitFor(() => expect(view.textContent).toContain("Gates failed: G-6, G-7"));
    expect(view.textContent).not.toContain("g-7");
  });
});

describe("AiModelManagement D-094 local synthetic test mode", () => {
  const remote: ModelOverview = {
    ...overview,
    profiles: overview.profiles.map((item) => item.profile_id === "openrouter_gpt_oss_120b"
      ? {
        ...item,
        display_name: "GPT-OSS 120B via OpenRouter (synthetic test only, D-094)",
        deployment: "openrouter",
        endpoint: "openrouter.ai · deepinfra/bf16",
        status: "selectable",
        reason: null,
        activation_blockers: [],
      }
      : item),
  };

  it("marks the external model, keeps its actions usable and warns before activating it", async () => {
    const view = mount(server(remote));
    await waitFor(() => expect(view.textContent).toContain("synthetic test only, D-094"));
    expect(view.textContent).toContain("answers only on the approved synthetic test case");
    expect(view.textContent).toContain("Test connection is a free preflight; qualification makes paid calls.");
    expect(button(view, "Run qualification…", "GPT-OSS").disabled).toBe(false);
    { const target = button(view, "Activate", "GPT-OSS"); act(() => target.click()); }
    expect(view.textContent).toContain("This is an external, paid API (D-094 local synthetic test mode).");
  });

  it("explains the remote model's own refusals", () => {
    expect(readable("NOT_DEVELOPMENT_ENVIRONMENT")).toContain("local development set-up");
    expect(readable("REMOTE_MANIFEST_MISSING")).toContain("AI_ASSISTANT_LOCAL_API_TEST_QUALIFICATION_QUESTIONS");
    expect(readable("REMOTE_MANIFEST_MISSING")).toContain("the approved two questions then apply");
    expect(readable("PREFLIGHT_FAILED:key.limit_set,ledger.healthy")).toBe(
      "Preflight failed: key.limit_set, ledger.healthy",
    );
  });
});

// --- D-095: daily spending limit and the OpenRouter key -----------------------------------------

// Built at run time so the secret scanner never sees a key-shaped literal.
const FAKE_KEY = ["sk", "or", "v1-fake-browser-test-key-0000000000"].join("-");

function budget(credential: Partial<ModelBudgetStatus["credential"]> = {}): ModelBudgetStatus {
  return {
    configured: true, mode: "D-095", timezone: "Asia/Singapore",
    daily_cap_default_micro_usd: 1_000_000, daily_cap_micro_usd: 1_000_000,
    next_reset_at: "2026-10-28T16:00:00Z",
    credential: {
      source: "none", status: "missing", hr_editable: true, persistence: "memory_only",
      set_at: null, set_by: null, ...credential,
    },
    provider: null,
    ledger: {
      cap_micro_usd: 1_100_000, committed_micro_usd: 1_001_076, headroom_micro_usd: 98_924,
      headroom_usd: "0.098924", open_calls: 0, breaker_open: false, breaker_code: null,
    },
    daily: {
      cap_micro_usd: 1_000_000, settled_today_micro_usd: 1_440, settled_today_usd: "0.001440",
      in_flight_micro_usd: 0, in_flight_usd: "0.000000", in_flight_calls: 0,
      remaining_micro_usd: 998_560, remaining_usd: "0.998560", day_started_at: "2026-10-27T16:00:00Z",
    },
    effective_remaining_micro_usd: 98_924, effective_remaining_usd: "0.098924",
    reservation_micro_usd: 21_300, refusal: "PROVIDER_LIMIT_NOT_CHECKED",
  };
}

const remoteSelectable = profile({
  profile_id: "openrouter_gpt_oss_120b", display_name: "GPT-OSS 120B via OpenRouter (synthetic test only, D-094)",
  source: "code", deployment: "openrouter", endpoint: "deepinfra/bf16", status: "selectable",
  active: false, activation_blockers: ["NOT_QUALIFIED"],
});

function keyServer(data: ModelOverview, calls: Array<{ method: string; url: string; body: string | null }>) {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    calls.push({ method, url, body: typeof init?.body === "string" ? init.body : null });
    if (url.endsWith("/admin/models/credential") && method === "PUT") {
      return json({ source: "hr_session", status: "configured", hr_editable: true, persistence: "memory_only", set_at: 1, set_by: "hr-admin" });
    }
    if (url.endsWith("/admin/models/credential") && method === "DELETE") {
      return json({ source: "none", status: "missing", hr_editable: true, persistence: "memory_only", set_at: null, set_by: null });
    }
    if (method === "POST") return json({ outcome: "passed", code: null, listed: null, complete_ms: null, stream_ms: null, first_piece_ms: null });
    if (url.endsWith("/api/assistant/admin/models")) return json(data);
    if (url.includes("/admin/models/audit")) return json({ events: [] });
    return json({ detail: { code: "NOT_FOUND", message: "No such model profile." } }, 404);
  });
}

function typeInto(input: HTMLInputElement, value: string): void {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
  act(() => {
    setter?.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

describe("AiModelManagement OpenRouter key and daily limit (D-095)", () => {
  it("shows Not Configured with a masked input, sends the key once and keeps no copy", async () => {
    const calls: Array<{ method: string; url: string; body: string | null }> = [];
    const data = { ...overview, profiles: [profile({}), remoteSelectable], budget: budget() };
    const view = mount(keyServer(data, calls), "providers");
    await waitFor(() => expect(view.textContent).toContain("OpenRouter API Key — Not Configured"));
    const input = view.querySelector<HTMLInputElement>("#openrouter-key-input");
    expect(input?.type).toBe("password");
    expect(input?.autocomplete).toBe("off");
    expect(button(view, "Save for Session").disabled).toBe(true);
    expect(button(view, "Test Connection").disabled).toBe(true);
    typeInto(input!, FAKE_KEY);
    await act(async () => button(view, "Save for Session").click());
    await waitFor(() => expect(view.textContent).toContain("Key saved for this session on the server."));
    const put = calls.find((call) => call.method === "PUT");
    expect(put?.url).toContain("/api/assistant/admin/models/credential");
    expect(JSON.parse(put?.body ?? "{}")).toEqual({ api_key: FAKE_KEY });
    expect(view.querySelector<HTMLInputElement>("#openrouter-key-input")?.value).toBe("");
    expect(view.innerHTML).not.toContain(FAKE_KEY);
    expect(JSON.stringify({ ...localStorage })).not.toContain(FAKE_KEY);
    expect(JSON.stringify({ ...sessionStorage })).not.toContain(FAKE_KEY);
    expect(document.cookie).not.toContain(FAKE_KEY);
  });

  it("offers Clear Session Key and Test Connection for an HR session key, with its expiry and fallback", async () => {
    const calls: Array<{ method: string; url: string; body: string | null }> = [];
    const data = {
      ...overview, profiles: [profile({}), remoteSelectable],
      budget: budget({ source: "hr_session", status: "configured", set_by: "hr-admin", set_at: 1, expires_at: 28_801, fallback: "env_file" }),
    };
    const view = mount(keyServer(data, calls), "providers");
    await waitFor(() => expect(view.textContent).toContain("OpenRouter API Key — Configured"));
    expect(view.textContent).toContain("ends when the HR session that entered it signs out or expires");
    expect(view.textContent).toContain("Ends with the HR session that entered it, and no later than");
    expect(view.textContent).toContain("the server key from apps/assistant/.env");
    await act(async () => button(view, "Test Connection").click());
    await waitFor(() => expect(calls.some((call) => call.method === "POST" && call.url.endsWith("/openrouter_gpt_oss_120b/connection-test"))).toBe(true));
    await act(async () => button(view, "Clear Session Key").click());
    await waitFor(() => expect(calls.some((call) => call.method === "DELETE" && call.url.endsWith("/admin/models/credential"))).toBe(true));
  });

  it("D-106: offers a session key even when the server has a .env key, but nothing to clear", async () => {
    const data = {
      ...overview, profiles: [profile({}), remoteSelectable],
      budget: budget({ source: "env_file", status: "configured", hr_editable: true, persistence: "server" }),
    };
    const view = mount(keyServer(data, []), "providers");
    await waitFor(() => expect(view.textContent).toContain("OpenRouter API Key — Configured"));
    expect(view.textContent).toContain("Server key from apps/assistant/.env. A session key entered here is used instead");
    expect(view.querySelector<HTMLInputElement>("#openrouter-key-input")?.type).toBe("password");
    expect(button(view, "Save for Session")).toBeTruthy();
    expect(() => button(view, "Clear Session Key")).toThrow();
  });

  it("D-106: says a key whose HR session cannot be checked is held back", async () => {
    const data = {
      ...overview, profiles: [profile({}), remoteSelectable],
      budget: budget({ source: "hr_session", status: "unverified", set_by: "hr-admin", set_at: 1, expires_at: 28_801, fallback: "none" }),
    };
    const view = mount(keyServer(data, []), "providers");
    await waitFor(() => expect(view.textContent).toContain("OpenRouter API Key — Session Not Verified"));
    expect(view.textContent).toContain("the key is held back and no server key is used in its place");
    expect(button(view, "Test Connection").disabled).toBe(true);
  });

  it("shows the US$1.00 Singapore-day limit, today's spending and why calls are refused", async () => {
    const data = { ...overview, profiles: [profile({}), remoteSelectable], budget: { ...budget(), refusal: "DAILY_ALLOWANCE_EXHAUSTED" } };
    const view = mount(keyServer(data, []), "spending");
    await waitFor(() => expect(view.textContent).toContain("OpenRouter daily spending limit"));
    expect(view.textContent).toContain("US$1.00 of reserved plus settled OpenRouter spending per Singapore calendar day");
    expect(view.textContent).toContain("US$0.001440");
    expect(view.textContent).toContain("US$0.998560");
    expect(view.textContent).toContain("US$0.098924");
    expect(view.textContent).toContain("midnight, Singapore");
    expect(view.textContent).toContain("has no room for another call");
  });

  it("shows no key or spending panel when the remote test mode is not configured", async () => {
    const view = mount(server(overview));
    await waitFor(() => expect(view.textContent).toContain("Qwen3 8B (LM Studio)"));
    expect(view.textContent).not.toContain("OpenRouter API Key");
    expect(view.textContent).not.toContain("daily spending limit");
  });
});

// --- D-096: HR spending controls -----------------------------------------------------------------

function controlled(overrides: Partial<NonNullable<ModelBudgetStatus["controls"]>> = {}): ModelBudgetStatus {
  return {
    ...budget({ source: "hr_session", status: "configured", set_by: "hr-admin", set_at: 1 }),
    controls: {
      revision: 3, readable: true,
      daily_cap_micro_usd: 1_000_000, daily_cap_max_micro_usd: 1_000_000_000_000, daily_cap_source: "hr",
      max_calls: 20, max_calls_range: [1, 200], max_calls_source: "hr",
      calls_used: 20, calls_remaining: 0,
      changed_at: "2026-10-28T03:00:00Z", changed_by: "hr-admin",
      lifetime: {
        opening_usage_micro_usd: 100_000, cap_micro_usd: 600_000,
        max_cap_micro_usd: 1_000_000_000_000, committed_micro_usd: 590_000,
      },
      ...overrides,
    },
  };
}

function controlsServer(data: ModelOverview, calls: Array<{ method: string; url: string; body: string | null }>) {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    calls.push({ method, url, body: typeof init?.body === "string" ? init.body : null });
    if (url.includes("/admin/models/budget/")) return json(data.budget);
    if (url.endsWith("/api/assistant/admin/models")) return json(data);
    if (url.includes("/admin/models/audit")) return json({ events: [] });
    return json({ detail: { code: "NOT_FOUND", message: "No such model profile." } }, 404);
  });
}

function input(view: HTMLElement, id: string): HTMLInputElement {
  const found = view.querySelector<HTMLInputElement>(`#${id}`);
  if (!found) throw new Error(`no #${id}`);
  return found;
}

describe("AiModelManagement HR spending controls (D-096)", () => {
  it("converts typed US$ amounts to whole micro-USD and refuses anything else", () => {
    expect(toMicroUsd("0.25")).toBe(250_000);
    expect(toMicroUsd("1")).toBe(1_000_000);
    expect(toMicroUsd(" 0.000001 ")).toBe(1);
    for (const bad of ["", "-1", "1e3", "0.0000001", "abc", "1,5", "0x10"]) expect(toMicroUsd(bad)).toBeNull();
  });

  it("shows calls used and remaining, the effective allowance, and saves both limits", async () => {
    const calls: Array<{ method: string; url: string; body: string | null }> = [];
    const data = { ...overview, profiles: [profile({}), remoteSelectable], budget: controlled() };
    const view = mount(controlsServer(data, calls), "spending");
    await waitFor(() => expect(view.textContent).toContain("Chat calls this session"));
    expect(view.textContent).toContain("20 used, 0 remaining of 20");
    expect(view.textContent).toContain("the strictest of today's allowance, the lifetime headroom and the OpenRouter key limit");
    expect(view.textContent).toContain("Set by hr-admin");
    typeInto(input(view, "daily-limit-input"), "0.5");
    typeInto(input(view, "call-limit-input"), "40");
    await act(async () => button(view, "Save Limits").click());
    await waitFor(() => expect(view.textContent).toContain("Limits saved."));
    const put = calls.find((call) => call.method === "PUT" && call.url.endsWith("/admin/models/budget/controls"));
    expect(JSON.parse(put?.body ?? "{}")).toEqual({ expected_revision: 3, daily_cap_micro_usd: 500_000, max_calls: 40 });
  });

  it("does not send invalid limits or an unconfirmed daily raise (D-098: no US$1 ceiling)", async () => {
    const calls: Array<{ method: string; url: string; body: string | null }> = [];
    const data = { ...overview, profiles: [profile({}), remoteSelectable], budget: controlled() };
    const view = mount(controlsServer(data, calls), "spending");
    await waitFor(() => expect(view.textContent).toContain("Daily and call limits"));
    for (const [daily, count] of [["1.01", "20"], ["0.5", "0"], ["0.5", "201"], ["-0.1", "20"], ["0.5", "2.5"]]) {
      typeInto(input(view, "daily-limit-input"), daily);
      typeInto(input(view, "call-limit-input"), count);
      expect(button(view, "Save Limits").disabled).toBe(true);
    }
    expect(calls.some((call) => call.method === "PUT")).toBe(false);
  });

  it("needs an explicit confirmation to raise the lifetime limit, and none to lower it", async () => {
    const calls: Array<{ method: string; url: string; body: string | null }> = [];
    const data = { ...overview, profiles: [profile({}), remoteSelectable], budget: controlled() };
    const view = mount(controlsServer(data, calls), "spending");
    await waitFor(() => expect(view.textContent).toContain("Lifetime limit (ledger)"));
    expect(view.textContent).toContain("with no fixed ceiling");
    typeInto(input(view, "lifetime-limit-input"), "1.2"); // above the old allocation: a raise, unconfirmed
    expect(button(view, "Update Lifetime Limit").disabled).toBe(true);
    typeInto(input(view, "lifetime-limit-input"), "0.9");
    expect(button(view, "Update Lifetime Limit").disabled).toBe(true); // not confirmed yet
    const confirm = [...view.querySelectorAll<HTMLInputElement>("input[type=checkbox]")]
      .find((item) => item.parentElement?.textContent?.includes("I confirm raising the lifetime limit to US$0.900000"));
    expect(confirm).toBeDefined();
    act(() => confirm!.click());
    await act(async () => button(view, "Update Lifetime Limit").click());
    await waitFor(() => expect(view.textContent).toContain("Lifetime limit updated."));
    const raise = calls.filter((call) => call.method === "PUT" && call.url.endsWith("/admin/models/budget/lifetime-cap"));
    expect(JSON.parse(raise[0]?.body ?? "{}")).toEqual({ cap_micro_usd: 900_000, confirm_cap_micro_usd: 900_000, expected_cap_micro_usd: 600_000 });

    typeInto(input(view, "lifetime-limit-input"), "0.4"); // lower: no confirmation
    expect(view.textContent).not.toContain("I confirm raising");
    await act(async () => button(view, "Update Lifetime Limit").click());
    await waitFor(() => expect(calls.filter((call) => call.url.endsWith("/budget/lifetime-cap"))).toHaveLength(2));
    const lower = calls.filter((call) => call.url.endsWith("/budget/lifetime-cap"))[1];
    expect(JSON.parse(lower?.body ?? "{}")).toEqual({ cap_micro_usd: 400_000, confirm_cap_micro_usd: null, expected_cap_micro_usd: 600_000 });
  });

  it("refreshes the OpenRouter limits read-only and never shows the key", async () => {
    const calls: Array<{ method: string; url: string; body: string | null }> = [];
    const data = { ...overview, profiles: [profile({}), remoteSelectable], budget: controlled() };
    const view = mount(controlsServer(data, calls), "spending");
    await waitFor(() => expect(view.textContent).toContain("Refresh OpenRouter Limits"));
    await act(async () => button(view, "Refresh OpenRouter Limits").click());
    await waitFor(() => expect(view.textContent).toContain("OpenRouter limits refreshed."));
    const refresh = calls.find((call) => call.url.endsWith("/admin/models/budget/provider-refresh"));
    expect(refresh?.method).toBe("POST");
    expect(view.textContent).toContain("The API key and its OpenRouter limit are never shown or changed here.");
    expect(refresh?.body).toBe("{}"); // nothing is sent but the request itself
  });

  it("refills the form when another administrator changed the limits, so a save never reverts them (QG F1)", async () => {
    const calls: Array<{ method: string; url: string; body: string | null }> = [];
    const data = { ...overview, profiles: [profile({}), remoteSelectable], budget: controlled() };
    const view = mount(controlsServer(data, calls), "spending");
    await waitFor(() => expect(input(view, "daily-limit-input").value).toBe("1.00"));
    // Elsewhere: daily limit lowered to US$0.05 (revision 4). This page re-reads on refresh.
    data.budget = controlled({ revision: 4, daily_cap_micro_usd: 50_000 });
    await act(async () => button(view, "Refresh OpenRouter Limits").click());
    await waitFor(() => expect(input(view, "daily-limit-input").value).toBe("0.05"));
    typeInto(input(view, "call-limit-input"), "30"); // only the call limit is changed here
    await act(async () => button(view, "Save Limits").click());
    await waitFor(() => expect(calls.some((call) => call.url.endsWith("/budget/controls"))).toBe(true));
    const put = calls.find((call) => call.url.endsWith("/budget/controls"));
    expect(JSON.parse(put?.body ?? "{}")).toEqual({ expected_revision: 4, daily_cap_micro_usd: 50_000, max_calls: 30 });
  });

  it("shows stored amounts exactly, so saving another field keeps them (QG F3)", async () => {
    expect(amountText(1_000_000)).toBe("1.00");
    expect(amountText(50_000)).toBe("0.05");
    expect(amountText(5_000)).toBe("0.005");
    expect(amountText(125_000)).toBe("0.125");
    expect(amountText(1_500)).toBe("0.0015");
    expect(amountText(1)).toBe("0.000001");
    for (const micro of [0, 1, 1_500, 5_000, 125_000, 999_999, 1_000_000]) expect(toMicroUsd(amountText(micro))).toBe(micro);
    const calls: Array<{ method: string; url: string; body: string | null }> = [];
    const data = { ...overview, profiles: [profile({}), remoteSelectable], budget: controlled({ daily_cap_micro_usd: 5_000 }) };
    const view = mount(controlsServer(data, calls), "spending");
    await waitFor(() => expect(input(view, "daily-limit-input").value).toBe("0.005"));
    typeInto(input(view, "call-limit-input"), "25");
    await act(async () => button(view, "Save Limits").click());
    await waitFor(() => expect(calls.some((call) => call.url.endsWith("/budget/controls"))).toBe(true));
    const put = calls.find((call) => call.url.endsWith("/budget/controls"));
    expect(JSON.parse(put?.body ?? "{}").daily_cap_micro_usd).toBe(5_000);
  });

  it("shows the fixed refusal when a raise is not reconciled", async () => {
    const data = { ...overview, profiles: [profile({}), remoteSelectable], budget: controlled() };
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/budget/lifetime-cap")) {
        return json({ detail: { code: "RECONCILIATION_REQUIRED", message: "The ledger must be reconciled with OpenRouter (no open call, no stop, usage accounted for) before the lifetime limit can be raised. Nothing changed." } }, 409);
      }
      if (url.endsWith("/api/assistant/admin/models")) return json(data);
      if (url.includes("/admin/models/audit")) return json({ events: [] });
      return json({}, init?.method === "POST" ? 200 : 404);
    });
    const view = mount(fetchMock, "spending");
    await waitFor(() => expect(view.textContent).toContain("Lifetime limit (ledger)"));
    typeInto(input(view, "lifetime-limit-input"), "0.9");
    const confirm = [...view.querySelectorAll<HTMLInputElement>("input[type=checkbox]")]
      .find((item) => item.parentElement?.textContent?.includes("I confirm raising"));
    act(() => confirm!.click());
    await act(async () => button(view, "Update Lifetime Limit").click());
    await waitFor(() => expect(view.textContent).toContain("The ledger must be reconciled with OpenRouter"));
  });
});

// --- GPT-OSS 120B naming and the optional Fast configuration ------------------------------------

describe("AiModelManagement GPT-OSS 120B naming", () => {
  const details = (effort: string) => ({
    model: "GPT-OSS 120B", provider: "OPENROUTER_DEEPINFRA", scope: "VERIFIED_SYNTHETIC_CASES",
    reasoning_effort: effort, decision: "D-095",
  });
  const balanced = profile({
    profile_id: "openrouter_gpt_oss_120b", display_name: "GPT-OSS 120B (reasoning medium)",
    source: "code", deployment: "openrouter", endpoint: "openrouter.ai · deepinfra/bf16", status: "selectable",
    active: true, activation_blockers: [], details: details("medium"),
  });
  const fast = profile({
    profile_id: "openrouter_gpt_oss_120b_low", display_name: "GPT-OSS 120B (reasoning low)",
    source: "code", deployment: "openrouter", endpoint: "openrouter.ai · deepinfra/bf16", status: "selectable",
    active: false, activation_blockers: ["NOT_QUALIFIED"], details: details("low"),
  });

  it("names the configurations by model and reasoning setting, not by a decision id", () => {
    expect(profileName(balanced)).toBe("GPT-OSS 120B — Balanced");
    expect(profileName(fast)).toBe("GPT-OSS 120B — Fast");
    expect(profileName(profile({}))).toBe("Environment baseline"); // other profiles keep their own names
  });

  it("shows provider, framework, reasoning and eligibility separately, and Fast's own qualification", async () => {
    const data = { ...overview, active: { ...overview.active, profile_id: "openrouter_gpt_oss_120b", display_name: "GPT-OSS 120B (reasoning medium)" }, profiles: [profile({}), balanced, fast] };
    const view = mount(server(data));
    await waitFor(() => expect(view.textContent).toContain("GPT-OSS 120B — Fast"));
    expect(view.textContent).toContain("GPT-OSS 120B — Balanced");
    expect(view.textContent).toContain("Provider: OpenRouter / DeepInfra · Framework: Case-grounded Assistant · Reasoning: Medium");
    expect(view.textContent).toContain("External inference: Verified synthetic cases only (D-095)");
    expect(view.textContent).toContain("Reasoning: Low");
    expect(view.textContent).toContain("the Balanced qualification does not count for it");
    expect(view.textContent).not.toContain("synthetic test only, D-094");
    expect(button(view, "Activate", "GPT-OSS 120B — Fast").disabled).toBe(true);
  });
});

// --- D-099 (proposed): Claude Sonnet 5.5 Balanced and Fast, listed but never usable ---------------

describe("AiModelManagement Claude Sonnet 5.5 (D-099 proposed)", () => {
  const claude = (profileId: string, effort: string, thinking: string, reason: string, scope: string) => profile({
    profile_id: profileId, display_name: "Claude Sonnet 5.5", source: "code", deployment: "anthropic",
    model_id: "claude-sonnet-5-5", model_version: effort, endpoint: "api.anthropic.com · claude-sonnet-5-5",
    temperature: null, max_answer_tokens: 3000, status: reason === "ANTHROPIC_NOT_AUTHORISED" ? "pending_authorisation" : "unavailable",
    reason, active: false, activation_blockers: [reason],
    details: { model: "Claude Sonnet 5.5", provider: "ANTHROPIC", scope, reasoning_effort: effort, thinking, decision: "D-099" },
  });

  it("names both configurations, their provider and thinking, and keeps every action disabled", async () => {
    const balanced = claude("anthropic_claude_sonnet_5_5_medium", "medium", "adaptive", "ANTHROPIC_NOT_AUTHORISED", "NOT_AUTHORISED");
    const fast = claude("anthropic_claude_sonnet_5_5_low", "low", "between_tools", "ANTHROPIC_NOT_AUTHORISED", "NOT_AUTHORISED");
    expect(profileName(balanced)).toBe("Claude Sonnet 5.5 — Balanced");
    expect(profileName(fast)).toBe("Claude Sonnet 5.5 — Fast");
    const view = mount(server({ ...overview, profiles: [profile({}), balanced, fast] }));
    await waitFor(() => expect(view.textContent).toContain("Claude Sonnet 5.5 — Fast"));
    expect(view.textContent).toContain("Provider: Anthropic API · Framework: Case-grounded Assistant · Reasoning: Medium · Thinking: adaptive");
    expect(view.textContent).toContain("Reasoning: Low · Thinking: between tool calls only");
    expect(view.textContent).toContain("Claude is not set up yet. HR enables it in Providers → Anthropic");
    for (const row of ["Claude Sonnet 5.5 — Balanced", "Claude Sonnet 5.5 — Fast"]) {
      expect(button(view, "Activate", row).disabled).toBe(true);
    }
  });

  it("shows the service's Anthropic-specific refusal as written (it is a browser-safe fixed message)", async () => {
    const message = "Run Test connection first so the Anthropic workspace and model are checked (a free model read). Nothing started.";
    const view = mount(server(overview, () => json({ detail: { code: "PROVIDER_LIMIT_NOT_CHECKED", message } }, 409)));
    await waitFor(() => expect(view.textContent).toContain("Qwen3 8B (LM Studio)"));
    await act(async () => button(view, "Test connection", "Qwen3").click());
    await waitFor(() => expect(view.textContent).toContain(message));
  });

  it("explains why a named decision still leaves them unusable", () => {
    expect(readable("ANTHROPIC_PROVIDER_CONTROLS_MISSING")).toContain("readable key limit, per-call cost verification and usage reconciliation");
    expect(readable("ANTHROPIC_NOT_AUTHORISED")).toContain("HR enables it in Providers → Anthropic (D-107)");
  });
});

// --- D-099 + D-100 Phase 1 integration: Claude in the AI Model Console ------------------------

describe("AiModelManagement Claude in the console (D-099 with D-100)", () => {
  const paid = { calls: 6, reservation_micro_usd: 96_000, estimate_micro_usd: 576_000, effective_remaining_micro_usd: 1_000_000, refusal: null, sufficient: true };
  const claude = profile({
    profile_id: "anthropic_claude_sonnet_5_5_medium", display_name: "Claude Sonnet 5.5", source: "code", deployment: "anthropic",
    model_id: "claude-sonnet-5-5", model_version: "medium", endpoint: "api.anthropic.com · claude-sonnet-5-5",
    temperature: null, max_answer_tokens: 3000, status: "selectable", reason: null, active: false,
    activation_blockers: [], paid_qualification: paid,
    details: { model: "Claude Sonnet 5.5", provider: "ANTHROPIC", scope: "VERIFIED_SYNTHETIC_CASES", reasoning_effort: "medium", thinking: "adaptive", decision: "D-099" },
  });
  const withClaude = (overrides: Partial<ModelProfileView> = {}): ModelOverview => ({
    ...overview, profiles: [overview.profiles[0], remoteSelectable, { ...claude, ...overrides }],
  });

  it("asks before a paid Claude run, names its own ledger and sends the confirmed calls", async () => {
    const posts: Array<{ url: string; body: unknown }> = [];
    const view = mount(server(withClaude(), (url, body) => { posts.push({ url, body }); return json({ qualification_id: "c".repeat(32) }); }));
    await waitFor(() => expect(view.textContent).toContain("Claude Sonnet 5.5 — Balanced"));
    { const target = button(view, "Run qualification…", "Claude Sonnet 5.5 — Balanced"); act(() => target.click()); }
    const dialog = view.querySelector("[data-testid=paid-confirm]");
    expect(dialog?.textContent).toContain("asks Claude Sonnet 5.5 the configured synthetic questions through the Anthropic API");
    expect(dialog?.textContent).toContain("Claude's separate ledger (the GPT-OSS limits do not apply)");
    expect(dialog?.textContent).not.toContain("OpenRouter");
    expect(dialog?.textContent).toContain("Up to 6");
    expect(posts).toEqual([]);  // nothing starts before the confirmation
    await act(async () => button(view, "Start paid qualification").click());
    await waitFor(() => expect(posts).toHaveLength(1));
    expect(posts[0].url).toContain("/admin/models/anthropic_claude_sonnet_5_5_medium/qualifications");
    expect(posts[0].body).toEqual({ confirm_paid_calls: 6 });
  });

  it("names a Claude refusal in Anthropic terms and keeps the GPT-OSS wording", async () => {
    const view = mount(server(withClaude({ paid_qualification: { ...paid, sufficient: false, refusal: "PROVIDER_LIMIT_NOT_CHECKED" } })));
    await waitFor(() => expect(view.textContent).toContain("Claude Sonnet 5.5 — Balanced"));
    { const target = button(view, "Run qualification…", "Claude Sonnet 5.5 — Balanced"); act(() => target.click()); }
    expect(view.querySelector("[data-testid=paid-confirm]")?.textContent).toContain("Anthropic workspace and model check has not been run");
    expect(button(view, "Start paid qualification").disabled).toBe(true);
    expect(readable("PROVIDER_LIMIT_NOT_CHECKED")).toContain("OpenRouter key's limit");
    expect(readable("PROVIDER_LIMIT_NOT_CHECKED", "openrouter")).toContain("OpenRouter key's limit");
    expect(readable("DAILY_ALLOWANCE_EXHAUSTED", "anthropic")).toContain("Claude's own daily allowance");
  });

  it("explains Claude's own safeguards in the inspector and before activation", async () => {
    const view = mount(server(withClaude()));
    await waitFor(() => expect(view.textContent).toContain("Claude Sonnet 5.5 — Balanced"));
    { const target = button(view, "Activate", "Claude Sonnet 5.5 — Balanced"); act(() => target.click()); }
    const inspector = view.querySelector("[data-testid=model-inspector]")?.textContent ?? "";
    expect(inspector).toContain("Provider: Anthropic API");
    expect(inspector).toContain("Thinking: adaptive");
    expect(inspector).toContain("The GPT-OSS spending controls never apply to it.");
    expect(view.textContent).toContain("This is an external, paid API (Claude Sonnet 5.5 through the Anthropic API, set up by HR under D-107).");
    expect(view.textContent).toContain("Nothing switches to or from Claude automatically.");
  });

  it("labels the overview's spending figures as GPT-OSS when Claude is listed", async () => {
    const view = mount(server({ ...withClaude(), budget: budget() }));
    await waitFor(() => expect(view.textContent).toContain("Available now (GPT-OSS)"));
  });

  it("states on Spending & Limits that the controls are GPT-OSS only", async () => {
    const view = mount(keyServer({ ...withClaude(), budget: budget() }, []), "spending");
    await waitFor(() => expect(view.textContent).toContain("These limits apply to GPT-OSS 120B only."));
    expect(view.textContent).toContain("Claude Sonnet 5.5 (D-099 and D-102 proposed) has its own separate ledger and limits");
  });

  it("explains a Claude recovery in Anthropic terms, not OpenRouter's", async () => {
    const run: ModelQualification = {
      ...qualification, qualification_id: "d".repeat(32), status: "failed", code: "CONNECTION_FAILED",
      diagnosis: { category: "billing_uncertain", cause: "LEDGER_NOT_RECONCILED", action: "ESCALATE_OPERATOR", retryable: false, supersedes_pass: false },
    };
    const view = mount(server(withClaude({ qualification: run, paid_qualification: { ...paid, sufficient: false, refusal: "PROVIDER_LIMIT_NOT_CHECKED" } })), "qualifications");
    await waitFor(() => expect(view.querySelector("[data-testid=recovery-anthropic_claude_sonnet_5_5_medium]")).not.toBeNull());
    const card = view.querySelector("[data-testid=recovery-anthropic_claude_sonnet_5_5_medium]")!.textContent ?? "";
    // D-118 usability: a session store never needs a reconciliation; the stop is resumed or reviewed.
    expect(card).toContain("Paid calls are paused for Claude");
    expect(card).toContain("HR resumes a financial stop in Set up AI");
    expect(card).not.toMatch(/operator (must )?reconcile|reconciled with the Anthropic Console/i);
    expect(card).toContain("Anthropic workspace and model check has not been run");
    expect(card).not.toContain("OpenRouter");
  });

  it("names no provider wrongly when the active external model became unusable", async () => {
    const view = mount(server({ ...withClaude(), active: { ...overview.active, unavailable: true } as ModelOverview["active"] }));
    await waitFor(() => expect(view.querySelector("[data-testid=ai-unavailable]")).not.toBeNull());
    expect(view.querySelector("[data-testid=ai-unavailable]")?.textContent).toContain("external model configuration that was active (GPT-OSS or Claude)");
  });

  it("names the Option B readiness codes", () => {
    for (const code of ["ANTHROPIC_ATTESTATION_MISSING", "WORKSPACE_NOT_ATTESTED", "WORKSPACE_LIMIT_NOT_ATTESTED", "LEDGER_PATH_SHARED", "LEDGER_PROFILE_MISMATCH", "LIFETIME_CEILING_EXCEEDED", "RECONCILIATION_STALE", "CREDENTIAL_ADMIN_REFUSED", "ANTHROPIC_SETTINGS_INVALID"]) {
      expect(readable(code)).not.toBe(code.replaceAll("_", " ").toLowerCase().replace(/^./, (letter) => letter.toUpperCase()));
    }
  });
});

// --- D-098: recovery centre and paid qualification confirmation --------------------------------

describe("AiModelManagement D-098 recovery", () => {
  const paid = { calls: 2, reservation_micro_usd: 30_000, estimate_micro_usd: 60_000, effective_remaining_micro_usd: 900_000, refusal: null, sufficient: true };
  const failedRun = (code: string, diagnosis: NonNullable<ModelQualification["diagnosis"]>, gates = qualification.gates): ModelQualification => ({
    ...qualification, qualification_id: "b".repeat(32), status: "failed", code, gates, diagnosis,
  });
  const withRemote = (overrides: Partial<ModelProfileView>): ModelOverview => ({
    ...overview,
    profiles: [overview.profiles[0], { ...remoteSelectable, activation_blockers: [], paid_qualification: paid, ...overrides }],
  });

  it("asks before a paid run and sends the confirmed number of calls", async () => {
    const posts: Array<{ url: string; body: unknown }> = [];
    const view = mount(server(withRemote({}), (url, body) => { posts.push({ url, body }); return json({ qualification_id: "c".repeat(32) }); }));
    await waitFor(() => expect(view.textContent).toContain("GPT-OSS"));
    { const target = button(view, "Run qualification…", "GPT-OSS"); act(() => target.click()); }
    const dialog = view.querySelector("[data-testid=paid-confirm]");
    expect(dialog?.textContent).toContain("Up to 2");
    expect(dialog?.textContent).toContain("US$0.060000");
    expect(posts).toEqual([]);  // nothing starts before the confirmation
    await act(async () => button(view, "Start paid qualification").click());
    await waitFor(() => expect(posts).toHaveLength(1));
    expect(posts[0].url).toContain("/admin/models/openrouter_gpt_oss_120b/qualifications");
    expect(posts[0].body).toEqual({ confirm_paid_calls: 2 });
  });

  it("will not start a paid run the limits cannot cover", async () => {
    const view = mount(server(withRemote({ paid_qualification: { ...paid, effective_remaining_micro_usd: 10_000, sufficient: false, refusal: "DAILY_ALLOWANCE_EXHAUSTED" } })));
    await waitFor(() => expect(view.textContent).toContain("GPT-OSS"));
    { const target = button(view, "Run qualification…", "GPT-OSS"); act(() => target.click()); }
    expect(view.querySelector("[data-testid=paid-confirm]")?.textContent).toContain("Today's allowance");
    expect(button(view, "Start paid qualification").disabled).toBe(true);
  });

  it("shows a budget failure as budget, keeps the earlier pass and offers a confirmed retry", async () => {
    const run = failedRun("GATES_FAILED:G-6,G-8", { category: "budget", cause: "CALLS_REFUSED", action: "REVIEW_SPENDING", retryable: true, supersedes_pass: false });
    const view = mount(server(withRemote({ qualification: run, eligible_qualification: { qualification_id: "a".repeat(32), finished_at: "2026-10-27T01:05:00+00:00", is_latest: false } })), "qualifications");
    await waitFor(() => expect(view.querySelector("[data-testid=recovery-openrouter_gpt_oss_120b]")).not.toBeNull());
    const card = view.querySelector("[data-testid=recovery-openrouter_gpt_oss_120b]")!;
    expect(card.textContent).toContain("Budget or limit");
    expect(card.textContent).toContain("refused before anything was sent");
    expect(card.textContent).toContain("Yes (passed");
    expect(card.querySelector("a[href='/admin/ai-models?section=spending']")?.textContent).toBe("Review spending controls");
    act(() => [...card.querySelectorAll("button")].find((b) => b.textContent === "Retry qualification…")!.click());
    expect(view.querySelector("[data-testid=paid-confirm]")).not.toBeNull();
  });

  it("escalates a quality failure without any retry or override", async () => {
    const run = failedRun(
      "GATES_FAILED:G-3",
      { category: "quality", cause: "UNSAFE_LINE", action: "ESCALATE_DEVELOPER", retryable: false, supersedes_pass: true },
      [{ gate: "G-3", rule: "unsafe displayed lines = 0", value: 1, passed: false, gating: true }],
    );
    const view = mount(server(withRemote({ qualification: run, activation_blockers: ["QUALIFICATION_SUPERSEDED"] })), "qualifications");
    await waitFor(() => expect(view.querySelector("[data-testid=recovery-openrouter_gpt_oss_120b]")).not.toBeNull());
    const card = view.querySelector("[data-testid=recovery-openrouter_gpt_oss_120b]")!;
    expect(card.textContent).toContain("Answer quality");
    expect(card.textContent).toContain("No: this quality failure replaces any earlier pass");
    expect(card.textContent).toContain("Failed gates: G-3");
    const labels = [...card.querySelectorAll("button")].map((b) => b.textContent);
    expect(labels).not.toContain("Retry qualification…");
    expect(labels).toContain("Copy escalation summary");
    go(view, "Models & Overview");
    expect(button(view, "Activate", "GPT-OSS").disabled).toBe(true);
  });

  it("recommends a confirmed new qualification for a pass that is out of date", async () => {
    const posts: unknown[] = [];
    const run: ModelQualification = {
      ...qualification, status: "passed", code: null, current: false,
      diagnosis: { category: "configuration", cause: "OUT_OF_DATE", action: "RUN_AGAIN", retryable: true, supersedes_pass: false },
    };
    const view = mount(server(withRemote({ qualification: run, eligible_qualification: null, activation_blockers: ["NOT_QUALIFIED"] }), (_url, body) => { posts.push(body); return json({ qualification_id: "c".repeat(32) }); }), "qualifications");
    await waitFor(() => expect(view.querySelector("[data-testid=recovery-openrouter_gpt_oss_120b]")).not.toBeNull());
    const card = view.querySelector("[data-testid=recovery-openrouter_gpt_oss_120b]")!;
    expect(card.textContent).toContain("Qualification out of date");
    expect(card.textContent).toContain("can no longer be activated");
    expect(card.textContent).toContain("Retry worthwhile nowYes");
    expect(card.textContent).toContain("Run a new qualification with the current configuration and code");
    expect(card.textContent).not.toContain("Nothing to do");
    act(() => [...card.querySelectorAll("button")].find((b) => b.textContent === "Run new qualification…")!.click());
    expect(view.querySelector("[data-testid=paid-confirm]")).not.toBeNull();
    expect(posts).toEqual([]);  // nothing starts before the paid confirmation
    act(() => button(view, "Cancel").click());
    go(view, "Models & Overview");
    expect(button(view, "Activate", "GPT-OSS").disabled).toBe(true);
  });

  it("keeps the quality escalation when a later out-of-date pass is the latest run", async () => {
    const run: ModelQualification = {
      ...qualification, status: "passed", code: null, current: false,
      diagnosis: { category: "quality", cause: "UNSAFE_LINE", action: "ESCALATE_DEVELOPER", retryable: false, supersedes_pass: true },
    };
    const view = mount(server(withRemote({ qualification: run, eligible_qualification: null, activation_blockers: ["QUALIFICATION_SUPERSEDED"] })), "qualifications");
    await waitFor(() => expect(view.querySelector("[data-testid=recovery-openrouter_gpt_oss_120b]")).not.toBeNull());
    const card = view.querySelector("[data-testid=recovery-openrouter_gpt_oss_120b]")!;
    expect(card.textContent).toContain("Answer quality");
    expect(card.textContent).not.toContain("Qualification out of date");
    expect(card.textContent).toContain("No: this quality failure replaces any earlier pass");
    const labels = [...card.querySelectorAll("button")].map((b) => b.textContent);
    expect(labels).not.toContain("Run new qualification…");
    expect(labels).not.toContain("Retry qualification…");
    expect(labels).toContain("Copy escalation summary");
  });

  it("keeps a current pass qualified with no retry advice", async () => {
    const run: ModelQualification = {
      ...qualification, status: "passed", code: null, current: true,
      diagnosis: { category: "passed", cause: "PASSED", action: "NONE", retryable: false, supersedes_pass: false },
    };
    const view = mount(server(withRemote({ qualification: run, eligible_qualification: { qualification_id: run.qualification_id, finished_at: "2026-10-27T01:05:00+00:00", is_latest: true } })), "qualifications");
    await waitFor(() => expect(view.querySelector("[data-testid=recovery-openrouter_gpt_oss_120b]")).not.toBeNull());
    const card = view.querySelector("[data-testid=recovery-openrouter_gpt_oss_120b]")!;
    expect(card.textContent).toContain("Qualified");
    expect(card.textContent).not.toContain("out of date");
    expect(card.textContent).toContain("Retry worthwhile nowNo");
    const labels = [...card.querySelectorAll("button")].map((b) => b.textContent);
    expect(labels).not.toContain("Run new qualification…");
    expect(labels).not.toContain("Retry qualification…");
  });

  it("names the AI-unavailable state and that no other model stood in", async () => {
    const view = mount(server({ ...withRemote({}), active: { ...overview.active, profile_id: "ai_unavailable", display_name: "AI unavailable", model_id: null, reverted: "QUALIFICATION_SUPERSEDED", unavailable: true } }));
    await waitFor(() => expect(view.querySelector("[data-testid=ai-unavailable]")).not.toBeNull());
    expect(view.querySelector("[data-testid=ai-unavailable]")?.textContent).toContain("No other model was put in its place");
  });
});

describe("AiModelManagement D-098 key limit and owner action", () => {
  it("shows the key's own limit, usage and reset policy, never account credits", async () => {
    const calls: Array<{ method: string; url: string; body: string | null }> = [];
    const status = controlled();
    const provider = {
      checked_at: "2026-10-28T03:00:00Z", passed: true, remaining_micro_usd: 900_000, remaining_usd: "0.900000",
      limit_micro_usd: 1_000_000, limit_usd: "1.000000", usage_micro_usd: 100_000, usage_usd: "0.100000",
      limit_reset: null, account_credits: null, checks: [],
    };
    const data = { ...overview, profiles: [profile({}), remoteSelectable], budget: { ...status, provider } };
    const view = mount(controlsServer(data, calls), "spending");
    await waitFor(() => expect(view.textContent).toContain("Key limit resets"));
    expect(view.textContent).toContain("US$0.900000 remaining of US$1.000000, US$0.100000 used");
    expect(view.textContent).toContain("Never (a lifetime key limit, as required)");
    expect(view.textContent).toContain("Account credits");
    expect(view.textContent).toContain("Not read.");
  });

  it("sends an exhausted key to its owner, not to HR's spending controls", async () => {
    const run: ModelQualification = {
      ...qualification, qualification_id: "d".repeat(32), status: "failed", code: "GATES_FAILED:G-6,G-8",
      diagnosis: { category: "budget", cause: "CALLS_REFUSED", action: "REVIEW_SPENDING", retryable: true, supersedes_pass: false },
    };
    const paid = { calls: 2, reservation_micro_usd: 30_000, estimate_micro_usd: 60_000, effective_remaining_micro_usd: 0, refusal: "PROVIDER_LIMIT_EXHAUSTED", sufficient: false };
    const data = { ...overview, profiles: [overview.profiles[0], { ...remoteSelectable, activation_blockers: [], qualification: run, paid_qualification: paid }] };
    const view = mount(server(data), "qualifications");
    await waitFor(() => expect(view.querySelector("[data-testid=recovery-openrouter_gpt_oss_120b]")).not.toBeNull());
    const card = view.querySelector("[data-testid=recovery-openrouter_gpt_oss_120b]")!;
    expect(card.querySelector("[data-testid=key-owner-action]")?.textContent).toContain("key's owner");
    expect(card.querySelector("a[href='/admin/ai-models?section=spending']")).toBeNull();
  });
});

describe("AiModelManagement D-098 flexible limits", () => {
  it("raises the daily limit above US$1.00 only with an explicit confirmation", async () => {
    const calls: Array<{ method: string; url: string; body: string | null }> = [];
    const data = { ...overview, profiles: [profile({}), remoteSelectable], budget: controlled() };
    const view = mount(controlsServer(data, calls), "spending");
    await waitFor(() => expect(view.textContent).toContain("Daily and call limits"));
    expect(view.textContent).toContain("default US$1.00, may be higher or lower");
    typeInto(input(view, "daily-limit-input"), "3");
    typeInto(input(view, "call-limit-input"), "20");
    expect(button(view, "Save Limits").disabled).toBe(true);  // a raise, not confirmed yet
    const confirm = view.querySelector<HTMLInputElement>("[data-testid=daily-raise-confirm]");
    expect(confirm?.parentElement?.textContent).toContain("I confirm raising the daily limit to US$3.000000");
    act(() => confirm!.click());
    await act(async () => button(view, "Save Limits").click());
    await waitFor(() => expect(calls.some((call) => call.method === "PUT")).toBe(true));
    const put = calls.find((call) => call.method === "PUT" && call.url.endsWith("/budget/controls"));
    expect(JSON.parse(put?.body ?? "{}")).toEqual({
      expected_revision: 3, daily_cap_micro_usd: 3_000_000, max_calls: 20, confirm_daily_cap_micro_usd: 3_000_000,
    });
  });
});

// --- D-100 Phase 1: AI Model Console shell and Models & Overview ---------------------------------

describe("AiModelManagement D-100 console", () => {
  const details = (effort: string) => ({
    model: "GPT-OSS 120B", provider: "OPENROUTER_DEEPINFRA", scope: "VERIFIED_SYNTHETIC_CASES",
    reasoning_effort: effort, decision: "D-095",
  });
  const balanced = profile({
    profile_id: "openrouter_gpt_oss_120b", display_name: "GPT-OSS 120B (reasoning medium)", source: "code",
    deployment: "openrouter", endpoint: "openrouter.ai · deepinfra/bf16", active: false, details: details("medium"),
  });
  const fast = profile({
    profile_id: "openrouter_gpt_oss_120b_low", display_name: "GPT-OSS 120B (reasoning low)", source: "code",
    deployment: "openrouter", endpoint: "openrouter.ai · deepinfra/bf16", active: false,
    activation_blockers: ["NOT_QUALIFIED"], details: details("low"),
  });
  const changes = (fetchMock: ReturnType<typeof vi.fn>) =>
    fetchMock.mock.calls.filter(([, init]) => (init as RequestInit | undefined)?.method && (init as RequestInit).method !== "GET");

  it("reads the section from the location and falls back to the guided setup (D-118)", async () => {
    expect(consoleSection("audit")).toBe("audit");
    expect(consoleSection("overview")).toBe("overview");
    expect(consoleSection("unknown")).toBe("setup");
    expect(consoleSection(null)).toBe("setup");
    const view = mount(server(overview), "audit");
    await waitFor(() => expect(view.textContent).toContain("Access refused"));
    expect(view.querySelector("h1")?.textContent).toBe("Audit History");
    expect(view.querySelector(".console-nav__link[aria-current=page]")?.textContent).toBe("Audit History");
    expect(view.querySelector("[data-testid=model-inspector]")).toBeNull();
  });

  it("changes section without sending anything to the server", async () => {
    const fetchMock = server(overview);
    const view = mount(fetchMock);
    await waitFor(() => expect(view.textContent).toContain("Model catalogue"));
    for (const label of ["Providers", "Spending & Limits", "Qualifications & Recovery", "Audit History", "Models & Overview"]) go(view, label);
    expect(view.querySelector("h1")?.textContent).toBe("Models & Overview");
    expect(changes(fetchMock)).toEqual([]);
  });

  it("keeps availability, technical qualification, answer quality and activation apart on each configuration", async () => {
    const view = mount(server({ ...overview, profiles: [profile({}), fast, balanced, overview.profiles[1]] }));
    await waitFor(() => expect(view.textContent).toContain("GPT-OSS 120B — Fast"));
    const family = view.querySelector('[aria-label="GPT-OSS 120B"]')!;
    expect([...family.querySelectorAll("[data-config-tile]")].map((tile) => tile.getAttribute("data-config-tile")))
      .toEqual(["openrouter_gpt_oss_120b", "openrouter_gpt_oss_120b_low"]); // Balanced before Fast
    const fastTile = view.querySelector('[data-config-tile="openrouter_gpt_oss_120b_low"]')!;
    expect(fastTile.textContent).toContain("AvailabilityAvailable");
    expect(fastTile.textContent).toContain("TechnicalNot run");
    expect(fastTile.textContent).toContain("Answer qualityNot scored");
    expect(fastTile.textContent).toContain("Blocked");
    const qwen = view.querySelector('[data-config-tile="lmstudio_qwen3_8b"]')!;
    expect(qwen.textContent).toContain("TechnicalQualified");
    expect(qwen.textContent).toContain("Ready");
  });

  it("shows the selected configuration in the inspector with the server's own blockers", async () => {
    const view = mount(server({ ...overview, profiles: [profile({}), balanced, fast] }));
    await waitFor(() => expect(view.textContent).toContain("GPT-OSS 120B — Fast"));
    const inspector = () => view.querySelector("[data-testid=model-inspector]")!;
    expect(inspector().querySelector("h2")?.textContent).toBe("Environment baseline"); // the active one first
    act(() => (view.querySelector('[data-config-tile="openrouter_gpt_oss_120b_low"]') as HTMLButtonElement).click());
    expect(view.querySelector('[data-config-tile="openrouter_gpt_oss_120b_low"]')?.getAttribute("aria-pressed")).toBe("true");
    expect(inspector().querySelector("h2")?.textContent).toBe("GPT-OSS 120B — Fast");
    expect(inspector().textContent).toContain("Activation blocked: Needs a passing qualification for the current configuration.");
    expect(inspector().textContent).toContain("the Balanced qualification does not count for it");
    expect(button(view, "Activate", "GPT-OSS 120B — Fast").disabled).toBe(true);
    expect(button(view, "Run qualification…", "GPT-OSS 120B — Fast").disabled).toBe(false);
  });

  it("confirms activation in a modal that Escape cancels without sending anything", async () => {
    const fetchMock = server(overview);
    const view = mount(fetchMock);
    await waitFor(() => expect(view.textContent).toContain("Qwen3 8B (LM Studio)"));
    const activate = button(view, "Activate", "Qwen3");
    activate.focus(); // as a keyboard user would
    act(() => activate.click());
    const dialog = view.querySelector<HTMLElement>('[role="dialog"]')!;
    expect(dialog.getAttribute("aria-modal")).toBe("true");
    expect(dialog.getAttribute("aria-labelledby")).toBe("confirm-heading");
    expect(document.activeElement).toBe(dialog);
    act(() => { dialog.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true })); });
    expect(view.querySelector('[role="dialog"]')).toBeNull();
    await waitFor(() => expect(document.activeElement).toBe(activate));
    expect(changes(fetchMock)).toEqual([]);
  });

  it("folds the section list behind one button on narrow screens", async () => {
    const view = mount(server(overview));
    await waitFor(() => expect(view.textContent).toContain("Model catalogue"));
    const toggle = view.querySelector<HTMLButtonElement>(".console-nav__toggle")!;
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    expect(toggle.textContent).toContain("Models & Overview");
    act(() => toggle.click());
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    go(view, "Spending & Limits");
    expect(view.querySelector(".console-nav__toggle")?.getAttribute("aria-expanded")).toBe("false");
  });

  it("moves focus to the inspector when a confirmed activation leaves its opener disabled (QG M1)", async () => {
    const pendingPost = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (init?.method === "POST") return new Promise<Response>(() => {}); // still running
      return server(overview)(input, init);
    });
    const view = mount(pendingPost);
    await waitFor(() => expect(view.textContent).toContain("Qwen3 8B (LM Studio)"));
    const activate = button(view, "Activate", "Qwen3");
    activate.focus();
    act(() => activate.click());
    act(() => (view.querySelector('[role="dialog"] input[type="checkbox"]') as HTMLInputElement).click());
    await act(async () => button(view, "Confirm").click());
    await waitFor(() => expect(activate.disabled).toBe(true));
    await waitFor(() => expect(document.activeElement?.id).toBe("inspector-heading"));
  });

  it("cancels from the backdrop without sending anything and keeps focus on the opener (QG M1)", async () => {
    const fetchMock = server(overview);
    const view = mount(fetchMock);
    await waitFor(() => expect(view.textContent).toContain("Qwen3 8B (LM Studio)"));
    const activate = button(view, "Activate", "Qwen3");
    activate.focus();
    act(() => activate.click());
    const backdrop = view.querySelector<HTMLElement>(".console-dialog-backdrop")!;
    const press = new MouseEvent("mousedown", { bubbles: true, cancelable: true });
    act(() => { backdrop.dispatchEvent(press); });
    expect(press.defaultPrevented).toBe(true);
    expect(view.querySelector('[role="dialog"]')).toBeNull();
    await waitFor(() => expect(document.activeElement).toBe(activate));
    expect(changes(fetchMock)).toEqual([]);
  });

  it("keeps focus in a dialog opened under StrictMode and returns it to the opener", async () => {
    function Harness() {
      const [open, setOpen] = useState(false);
      return (
        <>
          <button type="button" onClick={() => setOpen(true)}>Open</button>
          {open && <ConsoleDialog labelledBy="harness-heading" onClose={() => setOpen(false)}><h2 id="harness-heading">Title</h2><button type="button">Inside</button></ConsoleDialog>}
        </>
      );
    }
    container = document.createElement("div");
    document.body.append(container);
    root = createRoot(container);
    act(() => root?.render(<StrictMode><Harness /></StrictMode>));
    const opener = container.querySelector("button")!;
    opener.focus();
    act(() => opener.click());
    const dialog = container.querySelector<HTMLElement>('[role="dialog"]')!;
    await act(async () => new Promise((resolve) => setTimeout(resolve, 5))); // a stale restore would fire here
    expect(document.activeElement).toBe(dialog);
    act(() => { dialog.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true })); });
    await waitFor(() => expect(document.activeElement).toBe(opener));
  });

  it("gives each section badge words a screen reader can say (QG M3)", async () => {
    const outOfDate = { ...overview, profiles: overview.profiles.map((item) => item.qualification ? { ...item, qualification: { ...item.qualification, current: false } } : item) };
    const view = mount(server(outOfDate));
    await waitFor(() => expect(view.textContent).toContain("Model catalogue"));
    const link = [...view.querySelectorAll(".console-nav__link")].find((item) => item.textContent?.startsWith("Qualifications & Recovery"))!;
    expect(link.querySelector(".console-nav__badge [aria-hidden=true]")?.textContent).toBe("1");
    expect(link.querySelector(".console-nav__badge .sr-only")?.textContent).toBe(", 1 needs attention");
  });

  it("summarises spending only when the server reports a budget", async () => {
    let view = mount(server(overview));
    await waitFor(() => expect(view.textContent).toContain("Model catalogue"));
    expect(view.textContent).not.toContain("Available now");
    act(() => root?.unmount());
    root = null;
    container?.remove();

    view = mount(server({ ...overview, profiles: [profile({}), remoteSelectable], budget: controlled() }));
    await waitFor(() => expect(view.textContent).toContain("Available now"));
    expect(view.textContent).toContain("US$0.098924");
    expect(view.textContent).toContain("Chat calls this session");
    expect(view.querySelector('a.console-stat[href="/admin/ai-models?section=spending"]')).not.toBeNull();
  });
});

// --- D-100 Phase 2: Providers and Spending & Limits ---------------------------------------------

describe("AiModelManagement D-100 providers and spending", () => {
  const paid = { calls: 6, reservation_micro_usd: 96_000, estimate_micro_usd: 576_000, effective_remaining_micro_usd: 1_000_000, refusal: null, sufficient: true };
  const claude = (effort: string, overrides: Partial<ModelProfileView> = {}) => profile({
    profile_id: `anthropic_claude_sonnet_5_5_${effort}`, display_name: "Claude Sonnet 5.5", source: "code", deployment: "anthropic",
    model_id: "claude-sonnet-5-5", model_version: effort, endpoint: "api.anthropic.com · claude-sonnet-5-5",
    temperature: null, max_answer_tokens: 3000, status: "selectable", reason: null, active: false,
    activation_blockers: ["NOT_QUALIFIED"], paid_qualification: paid,
    details: { model: "Claude Sonnet 5.5", provider: "ANTHROPIC", scope: "VERIFIED_SYNTHETIC_CASES", reasoning_effort: effort, thinking: "adaptive", decision: "D-099" },
    ...overrides,
  });
  const withProviders = (budgetStatus: ModelBudgetStatus | null = controlled(), claudeOverrides: Partial<ModelProfileView> = {}): ModelOverview => ({
    ...overview,
    profiles: [overview.profiles[0], overview.profiles[1], remoteSelectable, claude("medium", claudeOverrides), claude("low", claudeOverrides)],
    budget: budgetStatus,
  });
  const card = (view: HTMLElement, kind: string) => view.querySelector(`[data-testid=provider-${kind}]`);

  it("shows one card per provider, with Balanced and Fast under one Anthropic provider", async () => {
    const view = mount(controlsServer(withProviders(), []), "providers");
    await waitFor(() => expect(card(view, "anthropic")).not.toBeNull());
    expect(card(view, "openrouter")?.textContent).toContain("GPT-OSS 120B");
    expect(card(view, "local")?.textContent).toContain("Qwen3 8B (LM Studio)");
    expect(card(view, "local")?.textContent).toContain("no spending ledger, no paid-run confirmation");
    expect(card(view, "local")?.textContent).toContain("IT sets the environment baseline in the server environment.");
    const anthropic = card(view, "anthropic")!.textContent ?? "";
    expect(anthropic).toContain("One provider for Claude Sonnet 5.5 Balanced and Fast");
    expect(anthropic).toContain("Claude Sonnet 5.5 — Balanced");
    expect(anthropic).toContain("Claude Sonnet 5.5 — Fast");
    expect(anthropic).toContain("2 of 2 configurations available");
    expect(anthropic).not.toContain("OpenRouter");
  });

  it("D-106: offers one Anthropic session key for Balanced and Fast, but no Claude limit inputs on Providers", async () => {
    const view = mount(controlsServer(withProviders(), []), "providers");
    await waitFor(() => expect(card(view, "anthropic")).not.toBeNull());
    const anthropic = card(view, "anthropic")!;
    // Only the key form: one masked input, no limit inputs.
    expect(anthropic.querySelectorAll("input")).toHaveLength(1);
    expect(anthropic.querySelector<HTMLInputElement>("#anthropic-key-input")?.type).toBe("password");
    expect(anthropic.textContent).toContain("Shared by Balanced and Fast");
    expect(anthropic.textContent).toContain("The server did not send this key's status.");
    // D-102: Claude's limits are HR settings, but on Spending & Limits only (linked from here).
    expect(anthropic.textContent).toContain("Spending & Limits shows when it was last done");
    expect(anthropic.textContent).toContain("The GPT-OSS controls never apply to it.");
    // The OpenRouter key form stays in the OpenRouter card only.
    expect(card(view, "openrouter")?.querySelector("#openrouter-key-input")).not.toBeNull();
  });

  it("names a server-reported Anthropic key or reconciliation problem in Anthropic terms, with its code", async () => {
    const data = withProviders(controlled(), {
      status: "unavailable", reason: "CREDENTIAL_MISSING", activation_blockers: ["CREDENTIAL_MISSING", "RECONCILIATION_STALE"], paid_qualification: null,
    });
    const view = mount(controlsServer(data, []), "providers");
    await waitFor(() => expect(card(view, "anthropic")).not.toBeNull());
    const anthropic = card(view, "anthropic")!.textContent ?? "";
    expect(anthropic).toContain("No Anthropic inference key is set: no session key was entered and the server has none.");
    expect(anthropic).toContain("RECONCILIATION_STALE");
    expect(anthropic).toContain("has not been reconciled with the provider's usage recently enough");
    expect(anthropic).toContain("0 of 2 configurations available");
  });

  it("D-106: says HR manages session keys and an operator the optional server key", async () => {
    const envKey = { ...controlled(), credential: { ...controlled().credential, source: "environment" as const, persistence: "server" as const } };
    const view = mount(controlsServer(withProviders(envKey), []), "providers");
    await waitFor(() => expect(card(view, "openrouter")).not.toBeNull());
    const text = card(view, "openrouter")?.textContent ?? "";
    expect(text).toContain("Enter or clear a session key (memory only, used first, ends with your session).");
    expect(text).toContain("Optionally set a server key");
    expect(text).toContain("Server key from the process environment (OPENROUTER_API_KEY)");
  });

  it("D-106: shows the Anthropic key's source and saves, clears and tests it on its own address", async () => {
    const calls: Array<{ method: string; url: string; body: string | null }> = [];
    const claudeKey = ["sk", "ant", "api03", "FakeBrowserTestKey000000000000"].join("-");
    const base = controlled();
    const data = withProviders({
      ...base,
      claude: { ...(base.claude ?? {}), credential: { source: "hr_session", status: "configured", hr_editable: true, persistence: "memory_only", set_at: 1, set_by: "hr-admin", expires_at: 28_801, verified_at: 2, fallback: "env_file" } } as ModelClaudeBudget,
    });
    const fetchMock = controlsServer(data, calls);
    const view = mount(fetchMock, "providers");
    await waitFor(() => expect(view.textContent).toContain("Anthropic API Key — Configured"));
    const anthropic = card(view, "anthropic")!;
    expect(anthropic.textContent).toContain("Session key entered on this page");
    expect(anthropic.textContent).toContain("the server key from apps/assistant/.env");
    typeInto(anthropic.querySelector<HTMLInputElement>("#anthropic-key-input")!, claudeKey);
    await act(async () => button(anthropic as HTMLElement, "Save for Session").click());
    await waitFor(() => expect(calls.some((call) => call.method === "PUT" && call.url.endsWith("/admin/models/credential/anthropic"))).toBe(true));
    expect(JSON.parse(calls.find((call) => call.method === "PUT")?.body ?? "{}")).toEqual({ api_key: claudeKey });
    expect(view.innerHTML).not.toContain(claudeKey);
    await act(async () => button(anthropic as HTMLElement, "Test Connection").click());
    await waitFor(() => expect(calls.some((call) => call.method === "POST" && call.url.endsWith("/anthropic_claude_sonnet_5_5_medium/connection-test"))).toBe(true));
    await act(async () => button(anthropic as HTMLElement, "Clear Session Key").click());
    await waitFor(() => expect(calls.some((call) => call.method === "DELETE" && call.url.endsWith("/admin/models/credential/anthropic"))).toBe(true));
  });

  it("reads providers and spending from the overview only, with no extra request", async () => {
    const fetchMock = controlsServer(withProviders(), []);
    const view = mount(fetchMock, "providers");
    await waitFor(() => expect(card(view, "anthropic")).not.toBeNull());
    go(view, "Spending & Limits");
    await waitFor(() => expect(view.querySelector("[data-testid=claude-spending]")).not.toBeNull());
    const urls = fetchMock.mock.calls.map(([input]) => String(input));
    expect(urls.every((url) => url.endsWith("/api/assistant/admin/models") || url.includes("/api/assistant/admin/models/audit"))).toBe(true);
  });

  it("keeps Claude's paid-qualification figures apart from the GPT-OSS limits when the server sends no Claude view", async () => {
    const view = mount(controlsServer(withProviders(), []), "spending");
    await waitFor(() => expect(view.querySelector("[data-testid=claude-spending]")).not.toBeNull());
    const claudePanel = view.querySelector("[data-testid=claude-spending]")!;
    // An older server (no D-102 Claude view): nothing to edit, and it says so.
    expect(claudePanel.querySelectorAll("input, form, button")).toHaveLength(0);
    expect(claudePanel.textContent).toContain("The GPT-OSS limits never apply to Claude");
    expect(claudePanel.textContent).toContain("This server does not send Claude's spending or limits");
    expect(claudePanel.textContent).toContain("US$1.000000");  // the server's figure, as sent
    expect(claudePanel.textContent).toContain("Allowed");
    expect(claudePanel.textContent).not.toContain("OpenRouter");
    // The GPT-OSS controls keep their own panel and form.
    expect(view.querySelector("#spending-heading")?.textContent).toContain("OpenRouter daily spending limit");
    expect(view.querySelector("#daily-limit-input")).not.toBeNull();
    expect(claudePanel.contains(view.querySelector("#daily-limit-input"))).toBe(false);
  });

  it("shows Claude's limits even when the OpenRouter test mode is off, without claiming no paid limits apply", async () => {
    const view = mount(server(withProviders(null)), "spending");
    await waitFor(() => expect(view.querySelector("[data-testid=claude-spending]")).not.toBeNull());
    expect(view.textContent).toContain("no GPT-OSS spending limits apply here");
    expect(view.textContent).not.toContain("so no paid spending limits apply here");
  });

  it("says a Claude configuration that is not available has no spending figure, not a zero", async () => {
    const view = mount(server(withProviders(null, { status: "pending_authorisation", reason: "ANTHROPIC_NOT_AUTHORISED", paid_qualification: null })), "spending");
    await waitFor(() => expect(view.querySelector("[data-testid=claude-spending]")).not.toBeNull());
    const text = view.querySelector("[data-testid=claude-spending]")!.textContent ?? "";
    expect(text).toContain("Not reported: this configuration is not available");
    expect(text).not.toContain("US$0.000000");
  });

  it("says when the GPT-OSS ledger could not be read instead of showing amounts", async () => {
    const unread = { ...controlled(), ledger: null, daily: null, refusal: "LEDGER_UNAVAILABLE" };
    const view = mount(controlsServer({ ...overview, profiles: [profile({}), remoteSelectable], budget: unread }, []), "spending");
    await waitFor(() => expect(view.textContent).toContain("Unavailable: the ledger could not be read"));
    expect(view.textContent).toContain("The spending ledger is missing or unhealthy.");
    expect(view.querySelector("[aria-label='Who can change the GPT-OSS limits']")?.textContent).toContain("You (HR), on this page");
  });
});

// --- D-100 Phase 3: Qualifications and Recovery ------------------------------------------------

describe("AiModelManagement D-100 qualifications and recovery", () => {
  const paid = { calls: 6, reservation_micro_usd: 96_000, estimate_micro_usd: 576_000, effective_remaining_micro_usd: 1_000_000, refusal: null, sufficient: true };
  const claude = (overrides: Partial<ModelProfileView> = {}) => profile({
    profile_id: "anthropic_claude_sonnet_5_5_medium", display_name: "Claude Sonnet 5.5", source: "code", deployment: "anthropic",
    model_id: "claude-sonnet-5-5", model_version: "medium", endpoint: "api.anthropic.com · claude-sonnet-5-5",
    temperature: null, max_answer_tokens: 3000, status: "selectable", reason: null, active: false,
    activation_blockers: ["NOT_QUALIFIED"], paid_qualification: paid,
    details: { model: "Claude Sonnet 5.5", provider: "ANTHROPIC", scope: "VERIFIED_SYNTHETIC_CASES", reasoning_effort: "medium", thinking: "adaptive", decision: "D-099" },
    ...overrides,
  });
  const failed = (code: string, diagnosis: NonNullable<ModelQualification["diagnosis"]>): ModelQualification => ({
    ...qualification, qualification_id: "b".repeat(32), status: "failed", code, diagnosis,
  });
  const recoveryCard = (view: HTMLElement, id: string) => view.querySelector(`[data-testid=recovery-${id}]`);
  const withClaude = (overrides: Partial<ModelProfileView> = {}): ModelOverview => ({ ...overview, profiles: [overview.profiles[0], claude(overrides)] });

  it("lists an unqualified Claude configuration and starts its first run only through the paid confirmation (I-1)", async () => {
    const posts: unknown[] = [];
    const view = mount(server(withClaude(), (_url, body) => { posts.push(body); return json({ qualification_id: "c".repeat(32) }); }), "qualifications");
    await waitFor(() => expect(recoveryCard(view, "anthropic_claude_sonnet_5_5_medium")).not.toBeNull());
    const card = recoveryCard(view, "anthropic_claude_sonnet_5_5_medium")!;
    expect(card.textContent).toContain("Not qualified yet.");
    expect(card.textContent).toContain("A first paid qualification makes up to 6 calls");
    act(() => [...card.querySelectorAll("button")].find((item) => item.textContent === "Run first qualification…")!.click());
    expect(view.querySelector("[data-testid=paid-confirm]")).not.toBeNull();
    expect(posts).toEqual([]);  // nothing starts before the confirmation
    await act(async () => button(view, "Start paid qualification").click());
    await waitFor(() => expect(posts).toEqual([{ confirm_paid_calls: 6 }]));
  });

  it("lists an unavailable Claude configuration without any action and says why", async () => {
    const view = mount(server(withClaude({ status: "pending_authorisation", reason: "ANTHROPIC_NOT_AUTHORISED", activation_blockers: ["ANTHROPIC_NOT_AUTHORISED"], paid_qualification: null })), "qualifications");
    await waitFor(() => expect(recoveryCard(view, "anthropic_claude_sonnet_5_5_medium")).not.toBeNull());
    const card = recoveryCard(view, "anthropic_claude_sonnet_5_5_medium")!;
    expect(card.textContent).toContain("Not available now: Claude is not set up yet.");
    expect(card.querySelectorAll("button")).toHaveLength(0);
  });

  it("shows technical qualification and answer quality apart, with quality never a gate", async () => {
    const view = mount(server(withClaude({ qualification: { ...qualification, diagnosis: { category: "passed", cause: "PASSED", action: "NONE", retryable: false, supersedes_pass: false } } })), "qualifications");
    await waitFor(() => expect(recoveryCard(view, "anthropic_claude_sonnet_5_5_medium")).not.toBeNull());
    const states = recoveryCard(view, "anthropic_claude_sonnet_5_5_medium")!.querySelector(".console-recovery-states")!;
    const pairs = [...states.querySelectorAll("div")].map((item) => `${item.querySelector("dt")?.textContent}=${item.querySelector("dd")?.textContent}`);
    expect(pairs).toEqual(["Technical qualification=Qualified", "Answer quality=Not scored", "Availability=Available"]);
    expect(view.querySelector("[data-testid=qualification-kinds]")?.textContent).toContain("Answer quality is reported only, never a gate");
  });

  it("keeps the server's raw codes beside their meaning", async () => {
    const run = failed("GATES_FAILED:G-6,G-8", { category: "budget", cause: "CALLS_REFUSED", action: "REVIEW_SPENDING", retryable: true, supersedes_pass: false });
    const view = mount(server({ ...overview, profiles: [overview.profiles[0], { ...remoteSelectable, qualification: run }] }), "qualifications");
    await waitFor(() => expect(recoveryCard(view, "openrouter_gpt_oss_120b")).not.toBeNull());
    const codes = [...recoveryCard(view, "openrouter_gpt_oss_120b")!.querySelectorAll(".console-codes-line code")].map((item) => item.textContent);
    expect(codes).toEqual(["failed", "GATES_FAILED:G-6,G-8", "budget", "CALLS_REFUSED", "REVIEW_SPENDING"]);
  });

  it("explains an interrupted run as a service stop, not a model fault", async () => {
    const run = failed("INTERRUPTED", { category: "technical", cause: "INTERRUPTED", action: "RUN_AGAIN", retryable: true, supersedes_pass: false });
    const view = mount(server({ ...overview, profiles: [overview.profiles[0], { ...remoteSelectable, qualification: run, paid_qualification: paid }] }), "qualifications");
    await waitFor(() => expect(recoveryCard(view, "openrouter_gpt_oss_120b")).not.toBeNull());
    const card = recoveryCard(view, "openrouter_gpt_oss_120b")!;
    expect(card.textContent).toContain("The run stopped because the AI assistant service stopped or restarted. It was not restarted automatically.");
    expect([...card.querySelectorAll("button")].map((item) => item.textContent)).toContain("Retry qualification…");
  });

  it("names a Claude run's code and results in Anthropic terms (M-1)", async () => {
    const run = failed("CREDENTIAL_INVALID", { category: "configuration", cause: "SERVER_SETTINGS", action: "ESCALATE_IT", retryable: false, supersedes_pass: false });
    const view = mount(server(withClaude({ qualification: run })), "qualifications");
    await waitFor(() => expect(recoveryCard(view, "anthropic_claude_sonnet_5_5_medium")).not.toBeNull());
    const card = recoveryCard(view, "anthropic_claude_sonnet_5_5_medium")!.textContent ?? "";
    expect(card).toContain("The configured Anthropic key is not a valid inference key.");
    expect(card).toContain("Troubleshooting Claude Sonnet 5.5 (Anthropic API)");
    expect(card).not.toContain("OpenRouter");
  });

  it("names a provider-unknown code without naming a provider (M-1)", async () => {
    expect(readable("CREDENTIAL_INVALID", ANY_PROVIDER)).not.toContain("OpenRouter");
    expect(readable("PROVIDER_LIMIT_NOT_CHECKED", ANY_PROVIDER)).not.toContain("OpenRouter");
    expect(readable("CREDENTIAL_INVALID")).toContain("OpenRouter");  // GPT-OSS wording unchanged
    const view = mount(server({ ...withClaude(), active: { ...overview.active, profile_id: "ai_unavailable", unavailable: true, reverted: "CREDENTIAL_INVALID" } }));
    await waitFor(() => expect(view.querySelector("[data-testid=ai-unavailable]")).not.toBeNull());
    const banner = view.querySelector("[data-testid=ai-unavailable]")!.textContent ?? "";
    expect(banner).toContain("The configured provider key is not valid.");
    expect(banner).toContain("CREDENTIAL_INVALID");
    expect(banner).not.toContain("OpenRouter");
  });

  it("never sends Claude to the GPT-OSS spending controls (M-2)", async () => {
    const run = failed("GATES_FAILED:G-8", { category: "budget", cause: "CALLS_REFUSED", action: "REVIEW_SPENDING", retryable: true, supersedes_pass: false });
    const view = mount(server(withClaude({ qualification: run, paid_qualification: { ...paid, sufficient: false, refusal: "DAILY_ALLOWANCE_EXHAUSTED" } })), "qualifications");
    await waitFor(() => expect(recoveryCard(view, "anthropic_claude_sonnet_5_5_medium")).not.toBeNull());
    const card = recoveryCard(view, "anthropic_claude_sonnet_5_5_medium")!;
    expect(card.querySelector("a[href='/admin/ai-models?section=spending']")?.textContent).toBe("Review Claude's limits");
    expect(card.textContent).not.toContain("Review spending controls");
    act(() => [...card.querySelectorAll("button")].find((item) => item.textContent === "Retry qualification…")!.click());
    const dialog = view.querySelector("[data-testid=paid-confirm]")!.textContent ?? "";
    expect(dialog).toContain("Review Claude's own limits in Spending & Limits");
    expect(dialog).not.toContain("spending controls");
    expect(button(view, "Start paid qualification").disabled).toBe(true);
  });

  it("keeps the GPT-OSS paid dialog pointing at its own spending controls", async () => {
    const view = mount(server({ ...overview, profiles: [overview.profiles[0], { ...remoteSelectable, activation_blockers: [], paid_qualification: { ...paid, sufficient: false, refusal: "DAILY_ALLOWANCE_EXHAUSTED" } }] }));
    await waitFor(() => expect(view.textContent).toContain("GPT-OSS"));
    { const target = button(view, "Run qualification…", "GPT-OSS"); act(() => target.click()); }
    expect(view.querySelector("[data-testid=paid-confirm]")?.textContent).toContain("Review the GPT-OSS spending controls or run Test connection first.");
  });
});

// --- D-100 Phase 4: Audit History, accessibility debt (D3, D5, D6) ------------------------------

describe("AiModelManagement D-100 audit history", () => {
  const event = (seq: number, overrides: Partial<ModelAuditEvent> = {}): ModelAuditEvent => ({
    seq, at: `2026-10-29T0${seq % 10}:00:00+00:00`, actor: "hr-admin", role: "HR", action: "ACTIVATE",
    profile_id: "lmstudio_qwen3_8b", fingerprint: "0123456789ab", outcome: "applied", code: null, revision: 4, ...overrides,
  });
  const events = [
    event(3),
    event(2, { action: "CONNECTION_TEST", outcome: "failed", code: "PROVIDER_CHECK_FAILED", profile_id: "anthropic_claude_sonnet_5_5_medium", revision: null }),
    event(1, { actor: "ethan-tan", role: "RELATIONSHIP_MANAGER", action: "ACCESS_REFUSED", outcome: "refused", code: "CREDENTIAL_INVALID", profile_id: null, revision: null }),
  ];
  const claude = profile({ profile_id: "anthropic_claude_sonnet_5_5_medium", display_name: "Claude Sonnet 5.5", source: "code", deployment: "anthropic", active: false,
    details: { model: "Claude Sonnet 5.5", provider: "ANTHROPIC", scope: "VERIFIED_SYNTHETIC_CASES", reasoning_effort: "medium", thinking: "adaptive", decision: "D-099" } });
  const data: ModelOverview = { ...overview, profiles: [...overview.profiles, claude] };
  function auditServer(list: ModelAuditEvent[] | (() => Response)) {
    return vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/assistant/admin/models")) return json(data);
      if (url.includes("/admin/models/audit")) return typeof list === "function" ? list() : json({ events: list });
      return json({ detail: { code: "NOT_FOUND", message: "No such model profile." } }, 404);
    });
  }
  const rows = (view: HTMLElement) => [...view.querySelectorAll(".console-audit__table tbody tr")];
  const select = (view: HTMLElement, id: string, choice: string) => {
    const element = view.querySelector<HTMLSelectElement>(`#${id}`)!;
    act(() => { element.value = choice; element.dispatchEvent(new Event("change", { bubbles: true })); });
  };

  it("shows each event's time, person, action, configuration, outcome and code, words and raw codes", async () => {
    const view = mount(auditServer(events), "audit");
    await waitFor(() => expect(rows(view)).toHaveLength(3));
    const second = rows(view)[1];
    expect(second.querySelector("time")?.getAttribute("datetime")).toBe("2026-10-29T02:00:00+00:00");
    expect(second.textContent).toContain("Event #2");
    expect(second.textContent).toContain("Claude Sonnet 5.5 — Balanced");
    expect(second.textContent).toContain("anthropic_claude_sonnet_5_5_medium");
    expect(second.textContent).toContain("The last Anthropic workspace and model check failed.");
    expect(second.textContent).toContain("PROVIDER_CHECK_FAILED");
    // No configuration: the code is worded for any provider, never as OpenRouter's.
    expect(rows(view)[2].textContent).toContain("The configured provider key is not valid.");
    expect(rows(view)[2].textContent).not.toContain("OpenRouter");
    expect(rows(view)[2].textContent).toContain("RELATIONSHIP_MANAGER");
  });

  it("searches and filters only the loaded events, says so, and sends no request to do it", async () => {
    const fetchMock = auditServer(events);
    const view = mount(fetchMock, "audit");
    await waitFor(() => expect(rows(view)).toHaveLength(3));
    expect(view.querySelector("[data-testid=audit-scope]")?.textContent).toContain("Search and filters look only at these loaded events.");
    const before = fetchMock.mock.calls.length;
    typeInto(view.querySelector<HTMLInputElement>("#audit-search")!, "provider_check");
    expect(rows(view)).toHaveLength(1);
    expect(view.querySelector(".console-audit__count")?.textContent).toBe("1 of 3 events loaded match.");
    act(() => button(view, "Clear filters").click());
    expect(rows(view)).toHaveLength(3);
    select(view, "audit-outcome", "refused");
    expect(rows(view).map((row) => row.textContent)).toEqual([expect.stringContaining("ethan-tan")]);
    select(view, "audit-action", "ACTIVATE");
    expect(rows(view)).toHaveLength(0);
    expect(view.textContent).toContain("No loaded event matches these filters. Older events are not loaded, so they are not searched.");
    expect(fetchMock.mock.calls.length).toBe(before);
  });

  it("says when older events were not loaded", async () => {
    const many = Array.from({ length: MODEL_AUDIT_LIMIT }, (_, index) => event(MODEL_AUDIT_LIMIT - index));
    const view = mount(auditServer(many), "audit");
    await waitFor(() => expect(rows(view)).toHaveLength(MODEL_AUDIT_LIMIT));
    expect(view.querySelector("[data-testid=audit-scope]")?.textContent).toContain(`The server sent the ${MODEL_AUDIT_LIMIT} events most recently recorded (the most this page asks for; older events are not loaded).`);
  });

  it("explains an empty history and offers a retry when it cannot be read", async () => {
    let view = mount(auditServer([]), "audit");
    await waitFor(() => expect(view.textContent).toContain("No model events recorded yet."));
    expect(view.querySelector("#audit-search")).toBeNull();
    act(() => root?.unmount());
    root = null;
    container?.remove();

    let calls = 0;
    const fetchMock = auditServer(() => { calls += 1; return json({ detail: { code: "SERVICE_UNAVAILABLE", message: "The AI assistant service is unavailable." } }, 503); });
    view = mount(fetchMock, "audit");
    await waitFor(() => expect(view.querySelector("[role=alert]")?.textContent).toContain("The AI assistant service is unavailable right now."));
    const seen = calls;
    await act(async () => button(view, "Try again").click());
    await waitFor(() => expect(calls).toBeGreaterThan(seen));
  });
});

describe("AiModelManagement D-100 dialogs and badges (D3, D5, D6)", () => {
  it("makes the background inert and stops page scrolling while a dialog is open (D3)", async () => {
    const view = mount(server(overview));
    await waitFor(() => expect(view.textContent).toContain("Qwen3 8B (LM Studio)"));
    const layout = view.querySelector<HTMLElement>(".console-layout")!;
    { const target = button(view, "Activate", "Qwen3"); act(() => target.click()); }
    expect(layout.hasAttribute("inert")).toBe(true);
    expect(document.body.style.overflow).toBe("hidden");
    expect(view.querySelector('[role="dialog"]')?.closest("[inert]")).toBeNull();
    act(() => button(view, "Cancel").click());
    expect(layout.hasAttribute("inert")).toBe(false);
    expect(document.body.style.overflow).toBe("");
  });

  it("never moves focus out of a dialog that replaced the one just closed (D5)", async () => {
    function Swap() {
      const [step, setStep] = useState(0);
      return (
        <>
          <button type="button" onClick={() => setStep(1)}>Open</button>
          {step === 1 && <ConsoleDialog key="first" labelledBy="first-heading" onClose={() => setStep(0)}><h2 id="first-heading">First</h2><button type="button" onClick={() => setStep(2)}>Next</button></ConsoleDialog>}
          {step === 2 && <ConsoleDialog key="second" labelledBy="second-heading" onClose={() => setStep(0)}><h2 id="second-heading">Second</h2><button type="button">Inside</button></ConsoleDialog>}
        </>
      );
    }
    container = document.createElement("div");
    document.body.append(container);
    root = createRoot(container);
    act(() => root?.render(<StrictMode><Swap /></StrictMode>));
    const opener = container.querySelector("button")!;
    opener.focus();
    act(() => opener.click());
    act(() => [...container!.querySelectorAll("button")].find((item) => item.textContent === "Next")!.click());
    await act(async () => new Promise((resolve) => setTimeout(resolve, 5)));  // the first dialog's restore fires here
    expect(document.activeElement?.closest('[aria-labelledby="second-heading"]')).not.toBeNull();
  });

  it("names the key, spending and running states in each section badge (D6)", async () => {
    const badge = (view: HTMLElement, section: string) => {
      const link = [...view.querySelectorAll(".console-nav__link")].find((item) => item.textContent?.startsWith(section));
      return link?.querySelector(".console-nav__badge .sr-only")?.textContent ?? null;
    };
    const cases: Array<[Partial<ModelOverview>, string, string]> = [
      [{ budget: budget() }, "Providers", ", no OpenRouter key is set"],
      [{ budget: budget({ status: "invalid", source: "environment" }) }, "Providers", ", the OpenRouter key is not valid"],
      [{ budget: { ...controlled(), refusal: "DAILY_ALLOWANCE_EXHAUSTED" } }, "Spending & Limits", ", paid calls are refused now"],
      [{ budget: { ...controlled(), ledger: { ...controlled().ledger!, breaker_open: true, breaker_code: "MISMATCH" } } }, "Spending & Limits", ", paid calls are stopped until an operator reconciles"],
      [{ running: { qualification_id: "r".repeat(32), profile_id: "lmstudio_qwen3_8b", done_turns: 1, total_turns: 84, started_by: "hr-admin" } }, "Qualifications & Recovery", ", a qualification is running"],
    ];
    for (const [overrides, section, label] of cases) {
      const view = mount(server({ ...overview, profiles: [profile({}), remoteSelectable], ...overrides }));
      await waitFor(() => expect(view.textContent).toContain("Model catalogue"));
      expect(badge(view, section)).toBe(label);
      act(() => root?.unmount());
      root = null;
      container?.remove();
    }
  });
});

// --- D-102: Claude's own HR spending controls on Spending & Limits ---------------------------------

describe("AiModelManagement D-102 Claude spending controls", () => {
  const paid = { calls: 6, reservation_micro_usd: 96_000, estimate_micro_usd: 576_000, effective_remaining_micro_usd: 1_000_000, refusal: null, sufficient: true };
  const claudeProfile = profile({
    profile_id: "anthropic_claude_sonnet_5_5_medium", display_name: "Claude Sonnet 5.5", source: "code", deployment: "anthropic",
    model_id: "claude-sonnet-5-5", model_version: "medium", endpoint: "api.anthropic.com · claude-sonnet-5-5",
    temperature: null, max_answer_tokens: 3000, status: "selectable", reason: null, active: false,
    activation_blockers: ["NOT_QUALIFIED"], paid_qualification: paid,
    details: { model: "Claude Sonnet 5.5", provider: "ANTHROPIC", reasoning_effort: "medium", decision: "D-099" },
  });
  const claudeView = (controls: Partial<ModelClaudeSpendingControls> = {}): ModelClaudeBudget => ({
    configured: true,
    timezone: "Asia/Singapore",
    daily_cap_micro_usd: 1_000_000,
    workspace_limit_micro_usd: 30_000_000,
    lifetime_ceiling_micro_usd: 30_000_000,
    next_reset_at: "2026-10-30T16:00:00Z",
    preflight: null,
    ledger: { profile_ok: true, cap_micro_usd: 5_000_000, committed_micro_usd: 830_000, headroom_micro_usd: 4_170_000, headroom_usd: "4.170000", open_calls: 0, breaker_open: false, breaker_code: null, reconciled_at: "2026-10-29T10:00:00Z" },
    daily: { cap_micro_usd: 1_000_000, settled_today_micro_usd: 0, in_flight_micro_usd: 0, remaining_micro_usd: 1_000_000, remaining_usd: "1.000000" },
    effective_remaining_micro_usd: 1_000_000,
    effective_remaining_usd: "1.000000",
    reservation_micro_usd: 96_000,
    refusal: null,
    controls: {
      revision: 2, readable: true, daily_cap_micro_usd: 1_000_000, daily_cap_range: [1, 5_000_000],
      daily_cap_default_micro_usd: 1_000_000, raise_requires: ["confirmation", "reconciled_within_one_day"],
      daily_cap_source: "hr", max_calls: 20, max_calls_range: [1, 20], max_calls_source: "hr",
      calls_used: null, calls_remaining: null, changed_at: "2026-10-29T10:00:00Z", changed_by: "hr-admin",
      lifetime: { opening_usage_micro_usd: 830_000, cap_micro_usd: 5_000_000, max_cap_micro_usd: 30_000_000, committed_micro_usd: 830_000 },
      ...controls,
    },
  });
  const withClaudeBudget = (claude: ModelClaudeBudget | undefined = claudeView()): ModelOverview => ({
    ...overview,
    profiles: [overview.profiles[0], remoteSelectable, claudeProfile],
    budget: { ...controlled(), claude },
  });
  const panel = (view: HTMLElement) => view.querySelector<HTMLElement>("[data-testid=claude-spending]")!;
  const put = (calls: Array<{ method: string; url: string; body: string | null }>, path: string) =>
    calls.filter((call) => call.method === "PUT" && call.url.endsWith(path));

  it("shows Claude's own figures and saves lower limits on Claude's route only", async () => {
    const calls: Array<{ method: string; url: string; body: string | null }> = [];
    const view = mount(controlsServer(withClaudeBudget(), calls), "spending");
    await waitFor(() => expect(view.querySelector("#claude-daily-limit-input")).not.toBeNull());
    const text = panel(view).textContent ?? "";
    expect(text).toContain("US$30.00 a month (owner-confirmed, not read from Anthropic");
    expect(text).toContain("US$4.170000");
    expect(text).toContain("the lower of US$30.00 and the owner-attested Anthropic workspace limit");
    expect(text).not.toContain("OpenRouter");
    typeInto(input(view, "claude-daily-limit-input"), "0.5");
    typeInto(input(view, "claude-call-limit-input"), "5");
    expect(view.querySelector("[data-testid=claude-daily-raise-confirm]")).toBeNull(); // lowering
    await act(async () => button(view, "Save Claude Limits").click());
    await waitFor(() => expect(view.textContent).toContain("Claude's limits saved."));
    const saved = put(calls, "/admin/models/budget/claude/controls");
    expect(saved).toHaveLength(1);
    expect(JSON.parse(saved[0].body ?? "{}")).toEqual({ expected_revision: 2, daily_cap_micro_usd: 500_000, max_calls: 5 });
    expect(put(calls, "/admin/models/budget/controls")).toHaveLength(0); // GPT-OSS untouched
  });

  it("needs a confirmation to raise Claude's daily limit and never sends one above US$5.00", async () => {
    const calls: Array<{ method: string; url: string; body: string | null }> = [];
    const view = mount(controlsServer(withClaudeBudget(), calls), "spending");
    await waitFor(() => expect(view.querySelector("#claude-daily-limit-input")).not.toBeNull());
    typeInto(input(view, "claude-daily-limit-input"), "5.01");
    expect(button(view, "Save Claude Limits").disabled).toBe(true);
    typeInto(input(view, "claude-call-limit-input"), "21");
    expect(button(view, "Save Claude Limits").disabled).toBe(true);
    typeInto(input(view, "claude-call-limit-input"), "20");
    typeInto(input(view, "claude-daily-limit-input"), "5");
    expect(button(view, "Save Claude Limits").disabled).toBe(true); // not confirmed yet
    await act(async () => view.querySelector<HTMLInputElement>("[data-testid=claude-daily-raise-confirm]")!.click());
    await act(async () => button(view, "Save Claude Limits").click());
    await waitFor(() => expect(put(calls, "/admin/models/budget/claude/controls")).toHaveLength(1));
    expect(JSON.parse(put(calls, "/admin/models/budget/claude/controls")[0].body ?? "{}")).toEqual({
      expected_revision: 2, daily_cap_micro_usd: 5_000_000, max_calls: 20, confirm_daily_cap_micro_usd: 5_000_000,
    });
  });

  it("names the checks a session store's raise needs, never a reconciliation (D-118)", async () => {
    const claude = claudeView({ raise_requires: ["confirmation", "breaker_closed_no_open_call"] });
    claude.ledger = { ...claude.ledger!, accounting_mode: "provider_capped", reconciled_at: null };
    const view = mount(controlsServer(withClaudeBudget(claude), []), "spending");
    await waitFor(() => expect(view.querySelector("#claude-daily-limit-input")).not.toBeNull());
    typeInto(input(view, "claude-daily-limit-input"), "5");
    typeInto(input(view, "claude-call-limit-input"), "20");
    const label = view.querySelector("[data-testid=claude-daily-raise-confirm]")!.closest("label")!.textContent ?? "";
    expect(label).toContain("no paid call is open and paid calls are not paused");
    expect(label).not.toMatch(/reconcil/i);
    expect(view.textContent).toContain("Never (not needed: a session store is bounded by the Anthropic workspace limit)");
    expect(view.textContent).not.toContain("Raising it needs your confirmation and a reconciliation");
  });

  it("raises Claude's lifetime limit up to US$30.00 with the shown cap and a confirmation", async () => {
    const calls: Array<{ method: string; url: string; body: string | null }> = [];
    const view = mount(controlsServer(withClaudeBudget(), calls), "spending");
    await waitFor(() => expect(view.querySelector("#claude-lifetime-limit-input")).not.toBeNull());
    typeInto(input(view, "claude-lifetime-limit-input"), "30.01");
    expect(button(view, "Update Claude Lifetime Limit").disabled).toBe(true);
    typeInto(input(view, "claude-lifetime-limit-input"), "0.83"); // not above the opening usage
    expect(button(view, "Update Claude Lifetime Limit").disabled).toBe(true);
    typeInto(input(view, "claude-lifetime-limit-input"), "30");
    expect(button(view, "Update Claude Lifetime Limit").disabled).toBe(true);
    await act(async () => view.querySelector<HTMLInputElement>("[data-testid=claude-cap-raise-confirm]")!.click());
    await act(async () => button(view, "Update Claude Lifetime Limit").click());
    await waitFor(() => expect(put(calls, "/admin/models/budget/claude/lifetime-cap")).toHaveLength(1));
    expect(JSON.parse(put(calls, "/admin/models/budget/claude/lifetime-cap")[0].body ?? "{}")).toEqual({
      cap_micro_usd: 30_000_000, confirm_cap_micro_usd: 30_000_000, expected_cap_micro_usd: 5_000_000,
    });
    expect(put(calls, "/admin/models/budget/lifetime-cap")).toHaveLength(0);
  });

  it("caps the lifetime input at a lower attested workspace limit and explains a missing ledger", async () => {
    const lower = claudeView();
    lower.controls.lifetime = { ...lower.controls.lifetime!, max_cap_micro_usd: 10_000_000 };
    const view = mount(controlsServer(withClaudeBudget(lower), []), "spending");
    await waitFor(() => expect(view.querySelector("#claude-lifetime-limit-input")).not.toBeNull());
    typeInto(input(view, "claude-lifetime-limit-input"), "10.01");
    expect(button(view, "Update Claude Lifetime Limit").disabled).toBe(true);
    expect(panel(view).textContent).toContain("at most US$10.00");

    const noLedger = mount(controlsServer(withClaudeBudget(claudeView({ lifetime: null })), []), "spending");
    await waitFor(() => expect(noLedger.querySelector("#claude-daily-limit-input")).not.toBeNull());
    expect(noLedger.querySelector("#claude-lifetime-limit-input")).toBeNull();
    expect(panel(noLedger).textContent).toContain("The Claude ledger is not set up yet");
  });

  it("needs a confirmation to raise Claude's call limit and sends it (QG L1)", async () => {
    const calls: Array<{ method: string; url: string; body: string | null }> = [];
    const view = mount(controlsServer(withClaudeBudget(claudeView({ max_calls: 5 })), calls), "spending");
    await waitFor(() => expect(view.querySelector("#claude-call-limit-input")).not.toBeNull());
    typeInto(input(view, "claude-call-limit-input"), "10");
    expect(button(view, "Save Claude Limits").disabled).toBe(true); // not confirmed yet
    expect(view.querySelector("[data-testid=claude-daily-raise-confirm]")).toBeNull();
    await act(async () => view.querySelector<HTMLInputElement>("[data-testid=claude-calls-raise-confirm]")!.click());
    await act(async () => button(view, "Save Claude Limits").click());
    await waitFor(() => expect(put(calls, "/admin/models/budget/claude/controls")).toHaveLength(1));
    expect(JSON.parse(put(calls, "/admin/models/budget/claude/controls")[0].body ?? "{}")).toEqual({
      expected_revision: 2, daily_cap_micro_usd: 1_000_000, max_calls: 10, confirm_max_calls: 10,
    });
  });

  it("allows only a strictly lower lifetime limit when no workspace limit is attested (QG L2)", async () => {
    const calls: Array<{ method: string; url: string; body: string | null }> = [];
    const unattested = claudeView();
    unattested.workspace_limit_micro_usd = 0;
    unattested.controls.lifetime = { ...unattested.controls.lifetime!, max_cap_micro_usd: 0 };
    const view = mount(controlsServer(withClaudeBudget(unattested), calls), "spending");
    await waitFor(() => expect(view.querySelector("#claude-lifetime-limit-input")).not.toBeNull());
    typeInto(input(view, "claude-lifetime-limit-input"), "6");
    expect(button(view, "Update Claude Lifetime Limit").disabled).toBe(true); // a raise
    typeInto(input(view, "claude-lifetime-limit-input"), "5");
    expect(button(view, "Update Claude Lifetime Limit").disabled).toBe(true); // unchanged
    typeInto(input(view, "claude-lifetime-limit-input"), "2");
    expect(view.querySelector("[data-testid=claude-cap-raise-confirm]")).toBeNull();
    await act(async () => button(view, "Update Claude Lifetime Limit").click());
    await waitFor(() => expect(put(calls, "/admin/models/budget/claude/lifetime-cap")).toHaveLength(1));
    expect(JSON.parse(put(calls, "/admin/models/budget/claude/lifetime-cap")[0].body ?? "{}")).toEqual({
      cap_micro_usd: 2_000_000, confirm_cap_micro_usd: null, expected_cap_micro_usd: 5_000_000,
    });
  });
  it("shows Claude's own figures on the overview when Claude is the active model", async () => {
    const active = { ...claudeProfile, active: true };
    const data: ModelOverview = {
      ...withClaudeBudget(claudeView({ calls_used: 3, calls_remaining: 17 })),
      active: { ...overview.active, profile_id: active.profile_id, display_name: "Claude Sonnet 5.5", model_id: "claude-sonnet-5-5" },
      profiles: [overview.profiles[0], remoteSelectable, active],
    };
    const view = mount(controlsServer(data, []));
    await waitFor(() => expect(view.textContent).toContain("Available now (Claude)"));
    expect(view.textContent).toContain("Chat calls this session (Claude)");
    expect(view.textContent).toContain("17 remaining");
    expect(view.textContent).not.toContain("Available now (GPT-OSS)");
    expect(view.textContent).not.toContain("GPT-OSS is not the active model");
  });

  it("shows Claude's figures on the overview even when the GPT-OSS spending view is not configured", async () => {
    const active = { ...claudeProfile, active: true };
    const base = withClaudeBudget(claudeView({ calls_used: 2, calls_remaining: 18 }));
    const data: ModelOverview = {
      ...base,
      budget: { ...base.budget!, configured: false },
      active: { ...overview.active, profile_id: active.profile_id, display_name: "Claude Sonnet 5.5", model_id: "claude-sonnet-5-5" },
      profiles: [overview.profiles[0], remoteSelectable, active],
    };
    const view = mount(controlsServer(data, []));
    await waitFor(() => expect(view.textContent).toContain("Available now (Claude)"));
    expect(view.textContent).toContain("18 remaining");
    expect(view.textContent).not.toContain("Available now (GPT-OSS)");
  });

  // --- B1 Phase A: the Claude ledger's accounting and reconciliation windows (read-only) ---

  const HOUR = 3_600_000;
  const iso = (ms: number) => new Date(ms).toISOString();
  const reconciliationView = (reconciledAgoMs: number | null, extra: Partial<ModelClaudeReconciliation> = {}): ModelClaudeReconciliation => {
    const reconciled = reconciledAgoMs === null ? null : Date.now() - reconciledAgoMs;
    return {
      key_alias: "key-02",
      reconciled_at: reconciled === null ? null : iso(reconciled),
      chat_deadline_at: reconciled === null ? null : iso(reconciled + 7 * 24 * HOUR),
      paid_deadline_at: reconciled === null ? null : iso(reconciled + 24 * HOUR),
      chat_fresh: reconciled !== null && reconciledAgoMs! <= 7 * 24 * HOUR,
      paid_fresh: reconciled !== null && reconciledAgoMs! <= 24 * HOUR,
      chat_window_seconds: 604_800,
      paid_window_seconds: 86_400,
      baseline_micro_usd: 20_000,
      local_charged_micro_usd: 54_136,
      estimate_micro_usd: 74_136,
      last_provider_usage_micro_usd: 20_000,
      open_reserved_micro_usd: 0,
      tolerance_micro_usd: 50_000,
      calls: { total: 6, open: 0, settled: 6, unsettled: 0, abandoned: 0, verified: 6, quarantined: 0, unverified: 0, charged_micro_usd: 54_136 },
      ...extra,
    };
  };
  const withReconciliation = (reconciliation: ModelClaudeReconciliation | null | undefined) =>
    withClaudeBudget({ ...claudeView(), reconciliation });
  const reconciliationPanel = (view: HTMLElement) => view.querySelector<HTMLElement>("[data-testid=claude-reconciliation]");

  it("shows the Claude ledger's accounting and both reconciliation windows, read-only", async () => {
    const calls: Array<{ method: string; url: string; body: string | null }> = [];
    const view = mount(controlsServer(withReconciliation(reconciliationView(2 * HOUR)), calls), "spending");
    await waitFor(() => expect(reconciliationPanel(view)).not.toBeNull());
    const text = reconciliationPanel(view)!.textContent ?? "";
    expect(text).toContain("key-02 (alias only; the key itself is never shown)");
    expect(text).toContain("US$0.074136"); // the ledger's estimate
    expect(text).toContain("US$0.020000"); // usage at the last reconciliation
    expect(text).toContain("US$0.054136"); // charged since
    expect(text).toContain("US$0.050000"); // the drift tolerance
    expect(text).toContain("6 (6 settled, 0 unsettled, 0 abandoned, 0 open)");
    expect(text).toContain("6 verified, 0 quarantined, 0 not yet verified");
    expect(text).toMatch(/Chat window \(7 days\)Open until /);
    expect(text).toContain("(ends within a day)"); // the 24-hour window ends in 22 hours
    expect(reconciliationPanel(view)!.querySelector("[role=alert]")).toBeNull();
    // Read-only: no form, input or button, and nothing is sent.
    expect(reconciliationPanel(view)!.querySelector("form, input, button")).toBeNull();
    expect(calls.filter((call) => call.method !== "GET")).toHaveLength(0);
    expect(text).not.toContain("OpenRouter");
  });

  it("marks a stale paid window while chat is still open", async () => {
    const view = mount(controlsServer(withReconciliation(reconciliationView(2 * 24 * HOUR)), []), "spending");
    await waitFor(() => expect(reconciliationPanel(view)).not.toBeNull());
    const text = reconciliationPanel(view)!.textContent ?? "";
    expect(text).toMatch(/Paid qualification and activation window \(24 hours\)Ended .*reconciliation required/);
    expect(text).toMatch(/Chat window \(7 days\)Open until /);
    expect(reconciliationPanel(view)!.querySelector("[role=alert]")).toBeNull();
  });

  it("warns when the chat window has ended", async () => {
    const view = mount(controlsServer(withReconciliation(reconciliationView(8 * 24 * HOUR)), []), "spending");
    await waitFor(() => expect(reconciliationPanel(view)).not.toBeNull());
    expect(reconciliationPanel(view)!.querySelector("[role=alert]")?.textContent).toContain("Claude chat is refused until it is reconciled with the Anthropic Console (below, or by an operator)");
    expect(reconciliationPanel(view)!.textContent).toMatch(/Chat window \(7 days\)Ended .*reconciliation required/);
  });

  it("explains a never-reconciled ledger without inventing a deadline", async () => {
    const view = mount(controlsServer(withReconciliation(reconciliationView(null)), []), "spending");
    await waitFor(() => expect(reconciliationPanel(view)).not.toBeNull());
    expect(reconciliationPanel(view)!.textContent).toContain("Not open: the Claude ledger has never been reconciled");
  });

  it("shows no figures when the Claude ledger could not be read", async () => {
    const view = mount(controlsServer(withReconciliation(null), []), "spending");
    await waitFor(() => expect(reconciliationPanel(view)).not.toBeNull());
    expect(reconciliationPanel(view)!.textContent).toContain("could not be read, so its reconciliation figures are not shown");
    expect(reconciliationPanel(view)!.textContent).not.toContain("US$");
  });

  it("shows nothing extra for an older server without the reconciliation view", async () => {
    const view = mount(controlsServer(withReconciliation(undefined), []), "spending");
    await waitFor(() => expect(view.querySelector("#claude-daily-limit-input")).not.toBeNull());
    expect(reconciliationPanel(view)).toBeNull();
  });

  // QG L2: the baseline is shown apart from the provider's report, and the terms add up.
  const terms = (text: string) => ({
    provider: text.match(/Anthropic usage reported at the last reconciliationUS\$([\d.]+)/)?.[1],
    baseline: text.match(/Ledger baseline \(reported usage \+ overcount kept\)US\$([\d.]+)/)?.[1],
    since: text.match(/Charged by the ledger since the last reconciliationUS\$([\d.]+)/)?.[1],
    estimate: text.match(/\(baseline \+ charged since\)US\$([\d.]+)/)?.[1],
  });
  const micro = (amount: string | undefined) => Math.round(Number(amount) * 1_000_000);

  it("shows a kept overcount between the provider's report and the ledger baseline, and the sums add up", async () => {
    const data = reconciliationView(2 * HOUR, { baseline_micro_usd: 30_000, estimate_micro_usd: 84_136 });
    const view = mount(controlsServer(withReconciliation(data), []), "spending");
    await waitFor(() => expect(reconciliationPanel(view)).not.toBeNull());
    const text = reconciliationPanel(view)!.textContent ?? "";
    expect(view.querySelector("[data-testid=claude-overcount]")?.textContent).toContain("US$0.010000: at the last reconciliation the ledger had counted more than Anthropic reported");
    const shown = terms(text);
    expect(shown).toEqual({ provider: "0.020000", baseline: "0.030000", since: "0.054136", estimate: "0.084136" });
    expect(micro(shown.provider) + 10_000).toBe(micro(shown.baseline)); // reported + kept = baseline
    expect(micro(shown.baseline) + micro(shown.since)).toBe(micro(shown.estimate)); // baseline + since = estimate
    expect(reconciliationPanel(view)!.querySelector("[role=alert]")).toBeNull();
  });

  it("says no overcount is kept when the baseline equals the provider's report", async () => {
    const view = mount(controlsServer(withReconciliation(reconciliationView(2 * HOUR)), []), "spending");
    await waitFor(() => expect(reconciliationPanel(view)).not.toBeNull());
    expect(view.querySelector("[data-testid=claude-overcount]")?.textContent).toContain("None");
    const shown = terms(reconciliationPanel(view)!.textContent ?? "");
    expect(shown.provider).toBe(shown.baseline);
    expect(micro(shown.baseline) + micro(shown.since)).toBe(micro(shown.estimate));
  });

  it("flags figures that do not add up instead of presenting them as consistent", async () => {
    const data = reconciliationView(2 * HOUR, { estimate_micro_usd: 99_999 });
    const view = mount(controlsServer(withReconciliation(data), []), "spending");
    await waitFor(() => expect(reconciliationPanel(view)).not.toBeNull());
    expect(reconciliationPanel(view)!.querySelector("[role=alert]")?.textContent).toContain("These ledger figures do not add up as expected");
  });

  it("labels every reconciliation time as Singapore time", async () => {
    const view = mount(controlsServer(withReconciliation(reconciliationView(2 * HOUR)), []), "spending");
    await waitFor(() => expect(reconciliationPanel(view)).not.toBeNull());
    const text = reconciliationPanel(view)!.textContent ?? "";
    expect(text).toMatch(/Last reconciled[^]*? SGTChat window/);
    expect(text).toMatch(/Chat window \(7 days\)Open until [^]*? SGT/);
    expect(text).toMatch(/\(24 hours\)Open until [^]*? SGT \(ends within a day\)/);
  });

  it("explains withheld figures while the Claude ledger was changing, without claiming no Claude is active", async () => {
    const busy: ModelClaudeBudget = {
      ...claudeView({ calls_used: null, calls_remaining: null, lifetime: null }),
      ledger: null, daily: null, reconciliation: null,
      effective_remaining_micro_usd: 0, effective_remaining_usd: "0.000000", refusal: "LEDGER_BUSY",
    };
    const view = mount(controlsServer(withClaudeBudget(busy), []), "spending");
    await waitFor(() => expect(reconciliationPanel(view)).not.toBeNull());
    const text = panel(view).textContent ?? "";
    expect(text).toContain("The Claude ledger was changing while this page read it, so its figures are not shown. Refresh in a moment.");
    expect(text).toMatch(/Chat calls this sessionUnavailable: the ledger could not be read \(limit 20 per session\)/);
    expect(text).not.toContain("No Claude configuration is active");
    expect(reconciliationPanel(view)!.textContent).not.toContain("US$");
  });

  it("never shows a GPT-OSS figure in the Claude ledger panel", async () => {
    const view = mount(controlsServer(withReconciliation(reconciliationView(2 * HOUR)), []), "spending");
    await waitFor(() => expect(reconciliationPanel(view)).not.toBeNull());
    const text = reconciliationPanel(view)!.textContent ?? "";
    // GPT-OSS's own fixture values (lifetime, committed, opening, headroom) are on the page...
    expect(view.textContent).toContain("US$0.590000");
    // ...but never in the Claude panel, which shows only the Claude ledger's figures.
    for (const gptoss of ["0.590000", "0.600000", "0.100000", "0.098924", "1.001076"]) {
      expect(text).not.toContain(gptoss);
    }
  });

  // --- D-110 (B1 Phase B): HR reconciles the Claude ledger with the Anthropic Console -------

  type Call = { method: string; url: string; body: string | null };
  const RUN = "a".repeat(32);
  const listingOf = (extra: Record<string, unknown> = {}) => ({
    runs: [], prerequisite_recorded: true, marker_readable: true, marker_run_id: null, marker_overridden: false, ...extra,
  });
  const previewOf = (extra: Record<string, unknown> = {}) => ({
    preview_id: "b".repeat(32),
    expires_at: iso(Date.now() + 300_000),
    fallback: false,
    settle_lag_seconds: 700,
    margin_seconds: 600,
    before: { baseline_micro_usd: 20_000, local_charged_micro_usd: 54_136, estimate_micro_usd: 74_136, last_provider_usage_micro_usd: 20_000, reconciled_at: iso(Date.now() - 2 * HOUR) },
    after: { baseline_micro_usd: 80_000, local_charged_micro_usd: 0, estimate_micro_usd: 80_000, last_provider_usage_micro_usd: 80_000 },
    drift_micro_usd: 5_864,
    tolerance_micro_usd: 50_000,
    breaker_opens: false,
    carried_micro_usd: 0,
    cap_micro_usd: 25_000_000,
    chat_deadline_at: iso(Date.now() + 7 * 24 * HOUR),
    paid_deadline_at: iso(Date.now() + 24 * HOUR),
    inputs: { usage_micro_usd: 80_000, as_of: iso(Date.now() - 60_000), as_of_kind: "console_refreshed", viewed_at: iso(Date.now() - 30_000) },
    ...extra,
  });
  const reconcileServer = (
    calls: Call[],
    options: { listing?: unknown; preview?: Response; apply?: Response; resolve?: Response } = {},
  ) => vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    calls.push({ method, url, body: typeof init?.body === "string" ? init.body : null });
    const data = withReconciliation(reconciliationView(2 * HOUR));
    if (url.endsWith("/budget/claude/reconciliation/preview")) return options.preview ?? json(previewOf());
    if (url.endsWith("/budget/claude/reconciliation/apply")) {
      return options.apply ?? json({ outcome: "applied", run: null, budget: data.budget });
    }
    if (url.includes("/budget/claude/reconciliation/runs/")) {
      return options.resolve ?? json({ outcome: "failed", run: { run_id: RUN, status: "failed" }, budget: data.budget });
    }
    if (url.endsWith("/budget/claude/reconciliation")) return json(options.listing ?? listingOf());
    if (url.includes("/admin/models/budget/")) return json(data.budget);
    if (url.endsWith("/api/assistant/admin/models")) return json(data);
    if (url.includes("/admin/models/audit")) return json({ events: [] });
    return json({ detail: { code: "NOT_FOUND", message: "No such model profile." } }, 404);
  });
  const reconcilePanel = (view: HTMLElement) => view.querySelector<HTMLElement>("[data-testid=claude-reconcile]");
  const tick = (view: HTMLElement, testId: string) => act(() => view.querySelector<HTMLInputElement>(`[data-testid=${testId}]`)!.click());
  const fillReading = (view: HTMLElement) => {
    typeInto(input(view, "reconcile-usage"), "0.08");
    typeInto(input(view, "reconcile-as-of"), "2026-10-31T10:00");
    typeInto(input(view, "reconcile-viewed"), "2026-10-31T10:05");
    for (const id of ["reconcile-scope-workspace", "reconcile-scope-only", "reconcile-scope-cumulative"]) tick(view, id);
  };
  const clickTestId = (view: HTMLElement, testId: string) =>
    act(async () => view.querySelector<HTMLButtonElement>(`[data-testid=${testId}]`)!.click());

  it("previews a Console reading, then applies it only after the figure is typed again", async () => {
    const calls: Call[] = [];
    const view = mount(reconcileServer(calls), "spending");
    await waitFor(() => expect(reconcilePanel(view)).not.toBeNull());
    const previewButton = view.querySelector<HTMLButtonElement>("[data-testid=reconcile-preview]")!;
    expect(previewButton.disabled).toBe(true);
    fillReading(view);
    expect(previewButton.disabled).toBe(false);
    await clickTestId(view, "reconcile-preview");
    await waitFor(() => expect(view.querySelector("[data-testid=reconcile-preview-result]")).not.toBeNull());
    const sent = JSON.parse(calls.find((call) => call.url.endsWith("/reconciliation/preview"))!.body!);
    expect(sent).toMatchObject({ usage_micro_usd: 80_000, as_of_kind: "console_refreshed", scope_workspace: true, scope_only: true, scope_cumulative: true });
    expect(sent.as_of).toBe(new Date("2026-10-31T10:00").toISOString());
    expect(sent.viewed_at).toBe(new Date("2026-10-31T10:05").toISOString());
    expect(view.querySelector("[data-testid=reconcile-drift]")?.textContent).toContain("US$0.005864");
    expect(calls.some((call) => call.url.endsWith("/reconciliation/apply"))).toBe(false);
    await clickTestId(view, "reconcile-apply-open");
    const apply = view.querySelector<HTMLButtonElement>("[data-testid=reconcile-apply]")!;
    expect(apply.disabled).toBe(true);
    typeInto(view.querySelector<HTMLInputElement>("[data-testid=reconcile-echo]")!, "0.07");
    expect(apply.disabled).toBe(true);
    typeInto(view.querySelector<HTMLInputElement>("[data-testid=reconcile-echo]")!, "0.08");
    expect(apply.disabled).toBe(false);
    await act(async () => apply.click());
    await waitFor(() => expect(view.querySelector("[data-testid=reconcile-message]")?.textContent).toContain("Reconciled."));
    expect(JSON.parse(calls.find((call) => call.url.endsWith("/reconciliation/apply"))!.body!)).toEqual({
      preview_id: "b".repeat(32), confirm_usage_micro_usd: 80_000, scope_workspace: true, scope_only: true, scope_cumulative: true,
    });
  });

  it("needs every scope statement before a preview is sent", async () => {
    const calls: Call[] = [];
    const view = mount(reconcileServer(calls), "spending");
    await waitFor(() => expect(reconcilePanel(view)).not.toBeNull());
    typeInto(input(view, "reconcile-usage"), "0.08");
    typeInto(input(view, "reconcile-as-of"), "2026-10-31T10:00");
    tick(view, "reconcile-scope-workspace");
    tick(view, "reconcile-scope-only");
    expect(view.querySelector<HTMLButtonElement>("[data-testid=reconcile-preview]")!.disabled).toBe(true);
    expect(calls.some((call) => call.method === "POST")).toBe(false);
  });

  it("warns before applying an undercount that stops Claude", async () => {
    const calls: Call[] = [];
    const view = mount(reconcileServer(calls, { preview: json(previewOf({ breaker_opens: true, drift_micro_usd: 120_000 })) }), "spending");
    await waitFor(() => expect(reconcilePanel(view)).not.toBeNull());
    fillReading(view);
    await clickTestId(view, "reconcile-preview");
    await waitFor(() => expect(view.querySelector("[data-testid=reconcile-breaker-warning]")).not.toBeNull());
    expect(view.querySelector("[data-testid=reconcile-breaker-warning]")!.textContent).toContain("stops Claude (breaker open) until the owner reconciles again");
  });

  it("words a refusal from its code and safe facts only", async () => {
    const calls: Call[] = [];
    const refusal = json({ detail: { code: "CALL_TOO_RECENT", message: "Nothing changed.", earliest_as_of: "2026-10-31T02:10:00+00:00", path: "C:\\secret\\ledger" } }, 409);
    const view = mount(reconcileServer(calls, { preview: refusal }), "spending");
    await waitFor(() => expect(reconcilePanel(view)).not.toBeNull());
    fillReading(view);
    await clickTestId(view, "reconcile-preview");
    await waitFor(() => expect(view.querySelector("[data-testid=reconcile-message]")).not.toBeNull());
    const text = view.querySelector("[data-testid=reconcile-message]")!.textContent ?? "";
    expect(text).toContain("A Claude call finished too close to the reading");
    expect(text).toContain("SGT");
    expect(text).not.toContain("secret");
    expect(view.querySelector("[data-testid=reconcile-preview-result]")).toBeNull();
  });

  it("explains that the owner's prerequisite is missing and offers no preview", async () => {
    const view = mount(reconcileServer([], { listing: listingOf({ prerequisite_recorded: false }) }), "spending");
    await waitFor(() => expect(view.querySelector("[data-testid=reconcile-prerequisite]")).not.toBeNull());
    fillReading(view);
    expect(view.querySelector<HTMLButtonElement>("[data-testid=reconcile-preview]")!.disabled).toBe(true);
  });

  it("uses the viewing time as the reading time only in the no-refresh-time fallback", async () => {
    const calls: Call[] = [];
    const view = mount(reconcileServer(calls), "spending");
    await waitFor(() => expect(reconcilePanel(view)).not.toBeNull());
    tick(view, "reconcile-kind-viewed");
    expect(view.querySelector("#reconcile-as-of")).toBeNull();
    typeInto(input(view, "reconcile-usage"), "0.08");
    typeInto(input(view, "reconcile-viewed"), "2026-10-31T10:05");
    for (const id of ["reconcile-scope-workspace", "reconcile-scope-only", "reconcile-scope-cumulative"]) tick(view, id);
    await clickTestId(view, "reconcile-preview");
    await waitFor(() => expect(calls.some((call) => call.url.endsWith("/reconciliation/preview"))).toBe(true));
    const sent = JSON.parse(calls.find((call) => call.url.endsWith("/reconciliation/preview"))!.body!);
    expect(sent.as_of_kind).toBe("viewed");
    expect(sent.as_of).toBe(sent.viewed_at);
  });

  it("reports an unconfirmed outcome as open, never as reconciled", async () => {
    const calls: Call[] = [];
    const view = mount(reconcileServer(calls, { apply: json({ outcome: "uncertain", run: null }) }), "spending");
    await waitFor(() => expect(reconcilePanel(view)).not.toBeNull());
    fillReading(view);
    await clickTestId(view, "reconcile-preview");
    await waitFor(() => expect(view.querySelector("[data-testid=reconcile-apply-open]")).not.toBeNull());
    await clickTestId(view, "reconcile-apply-open");
    typeInto(view.querySelector<HTMLInputElement>("[data-testid=reconcile-echo]")!, "0.08");
    await clickTestId(view, "reconcile-apply");
    await waitFor(() => expect(view.querySelector("[data-testid=reconcile-message]")).not.toBeNull());
    const text = view.querySelector("[data-testid=reconcile-message]")!.textContent ?? "";
    expect(text).toContain("could not be confirmed");
    expect(text).not.toContain("Reconciled.");
  });

  it("lists runs and resolves an unfinished one on request", async () => {
    const calls: Call[] = [];
    const run = { run_id: RUN, status: "requested", actor: "hr-admin", intent_at: iso(Date.now() - 120_000), finished_at: null, usage_micro_usd: 80_000, drift_micro_usd: 0, as_of: iso(Date.now() - 180_000), as_of_kind: "console_refreshed", event_id: null, reason: null, attribution_basis: null, owner_reference: null, acknowledged_state: null, resolvable_after: iso(Date.now() - 60_000) };
    const unresolved = { ...run, run_id: "c".repeat(32), status: "unresolved", resolvable_after: undefined };
    const view = mount(reconcileServer(calls, { listing: listingOf({ runs: [run, unresolved] }) }), "spending");
    await waitFor(() => expect(view.querySelector("[data-testid=reconcile-runs]")).not.toBeNull());
    const table = view.querySelector("[data-testid=reconcile-runs]")!;
    expect(table.textContent).toContain("Not finished (resolve it)");
    expect(table.textContent).toContain("Unresolved: the owner must check and close it");
    expect([...table.querySelectorAll("button")]).toHaveLength(1);
    await act(async () => table.querySelector("button")!.click());
    await waitFor(() => expect(calls.some((call) => call.url.endsWith(`/reconciliation/runs/${RUN}/resolve`))).toBe(true));
    await waitFor(() => expect(view.querySelector("[data-testid=reconcile-message]")?.textContent).toContain("Failed (nothing changed)"));
  });

  it("never trusts a malformed run listing", async () => {
    const view = mount(reconcileServer([], { listing: { runs: "nope" } }), "spending");
    await waitFor(() => expect(reconcilePanel(view)).not.toBeNull());
    expect(view.querySelector("[data-testid=reconcile-runs]")).toBeNull();
    expect(view.querySelector("[data-testid=reconcile-prerequisite]")).toBeNull();
  });
});

// --- Data Access & Privacy: "Restrict AI to verified synthetic cases" ------------------------------

describe("AiModelManagement data access policy", () => {
  const policy = (changes: Partial<ModelDataAccess> = {}, localRestricted = false): ModelDataAccess => ({
    status: "default", revision: 0, changed_at: null,
    classes: [
      { provider_class: "openrouter", restricted: true, locked: true },
      { provider_class: "anthropic", restricted: true, locked: true },
      { provider_class: "it_configured", restricted: true, locked: true },
      { provider_class: "local_internal", restricted: localRestricted, locked: false },
    ],
    active_class: "local_internal", active_restricted: localRestricted,
    verification: "D-095", ...changes,
  });
  const policyServer = (data: ModelDataAccess, calls: Array<{ method: string; url: string; body: string | null }>) =>
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      calls.push({ method, url, body: typeof init?.body === "string" ? init.body : null });
      if (url.endsWith("/admin/models/data-access")) return json(data);
      if (url.endsWith("/api/assistant/admin/models")) return json({ ...overview, data_access: data });
      if (url.includes("/admin/models/audit")) return json({ events: [] });
      return json({ detail: { code: "NOT_FOUND", message: "No such model profile." } }, 404);
    });
  const box = (view: HTMLElement, name: string) => view.querySelector<HTMLInputElement>(`[data-testid=restrict-${name}]`)!;
  const puts = (calls: Array<{ method: string; url: string; body: string | null }>) =>
    calls.filter((call) => call.method === "PUT" && call.url.endsWith("/admin/models/data-access"));

  it("is a console section that shows the server's effective policy with external models locked", async () => {
    const view = mount(policyServer(policy(), []));
    await waitFor(() => expect(view.textContent).toContain("Models & Overview"));
    go(view, "Data Access & Privacy");
    await waitFor(() => expect(view.querySelector("[data-testid=data-access]")).not.toBeNull());
    expect(view.querySelector("h1")?.textContent).toBe("Data Access & Privacy");
    // D-107: external providers show what they may receive as text, never a disabled checkbox.
    for (const name of ["openrouter", "anthropic", "it_configured"]) {
      expect(view.querySelector(`[data-testid=restrict-${name}]`)).toBeNull();
      const row = view.querySelector(`[data-testid=access-${name}]`)!;
      expect(row.textContent).toContain("Verified synthetic cases only");
      expect(row.textContent).toContain("This does not stop the provider from being used.");
      expect(row.querySelector("input")).toBeNull();
    }
    expect(view.querySelector("[data-testid=access-anthropic]")!.textContent).toContain("Provider");
    expect(box(view, "local_internal").checked).toBe(false);
    expect(box(view, "local_internal").disabled).toBe(false);
    expect(view.textContent).toContain("Restrict AI to verified synthetic cases");
    expect(view.textContent).toContain("it cannot be enabled on this page");
    expect(view.textContent).toContain("D-095 verified synthetic cases");
  });

  it("restricts a local model without confirmation and always keeps external models restricted", async () => {
    const calls: Array<{ method: string; url: string; body: string | null }> = [];
    const view = mount(policyServer(policy(), calls), "privacy");
    await waitFor(() => expect(view.querySelector("[data-testid=data-access]")).not.toBeNull());
    act(() => box(view, "local_internal").click());
    expect(view.querySelector("[data-testid=data-access-widen-confirm]")).toBeNull();
    await act(async () => button(view, "Save Data Access Policy").click());
    await waitFor(() => expect(puts(calls)).toHaveLength(1));
    expect(JSON.parse(puts(calls)[0].body ?? "{}")).toEqual({
      expected_revision: 0, restrict_external: true, restrict_local: true, confirm_widen: false,
    });
  });

  it("needs an explicit confirmation to widen a restricted local model", async () => {
    const calls: Array<{ method: string; url: string; body: string | null }> = [];
    const view = mount(policyServer(policy({ status: "stored", revision: 4 }, true), calls), "privacy");
    await waitFor(() => expect(view.querySelector("[data-testid=data-access]")).not.toBeNull());
    act(() => box(view, "local_internal").click());
    expect(button(view, "Save Data Access Policy").disabled).toBe(true);
    act(() => view.querySelector<HTMLInputElement>("[data-testid=data-access-widen-confirm]")!.click());
    await act(async () => button(view, "Save Data Access Policy").click());
    await waitFor(() => expect(puts(calls)).toHaveLength(1));
    expect(JSON.parse(puts(calls)[0].body ?? "{}")).toEqual({
      expected_revision: 4, restrict_external: true, restrict_local: false, confirm_widen: true,
    });
  });

  it("says when the policy is unreadable or only the D-094 fixture applies, and allows no change", async () => {
    const view = mount(policyServer(policy({ status: "unavailable", revision: null, verification: "D-094" }, true), []), "privacy");
    await waitFor(() => expect(view.querySelector("[data-testid=data-access]")).not.toBeNull());
    expect(view.textContent).toContain("could not be read, so local models are restricted");
    expect(view.textContent).toContain("D-094 fixed synthetic fixture only");
    expect(box(view, "local_internal").checked && box(view, "local_internal").disabled).toBe(true);
  });
});

// --- D-106: qualification progress -------------------------------------------------------------

describe("AiModelManagement qualification progress (D-106)", () => {
  const claudeBalanced = (run: ModelQualification | null) => profile({
    profile_id: "anthropic_claude_sonnet_5_5_medium", display_name: "Claude Sonnet 5.5", source: "code", deployment: "anthropic",
    model_id: "claude-sonnet-5-5", model_version: "medium", endpoint: "api.anthropic.com · claude-sonnet-5-5",
    status: "selectable", active: false, qualification: run, activation_blockers: ["NOT_QUALIFIED"],
    details: { model: "Claude Sonnet 5.5", provider: "ANTHROPIC", scope: "VERIFIED_SYNTHETIC_CASES", reasoning_effort: "medium", thinking: "adaptive", decision: "D-099" },
  });
  const runningRun = (done: number, total: number): ModelQualification => ({
    ...qualification, qualification_id: "c".repeat(32), status: "running", finished_at: null,
    done_turns: done, total_turns: total, gates: null, metrics: null, lines: null, capacity: null,
    started_at: "2026-10-30T09:00:00+00:00",
    diagnosis: { category: "running", cause: "RUNNING", action: "WAIT", retryable: false, supersedes_pass: false },
  });
  const withRun = (done: number, total: number): ModelOverview => ({
    ...overview,
    running: { qualification_id: "c".repeat(32), profile_id: "anthropic_claude_sonnet_5_5_medium", done_turns: done, total_turns: total, started_by: "hr-admin" },
    profiles: [...overview.profiles, claudeBalanced(runningRun(done, total))],
  });

  it("shows a spinner, a bar from the server's turn counts, the provider and the active model", async () => {
    const view = mount(server(withRun(1, 2)), "qualifications");
    await waitFor(() => expect(view.querySelector("[data-testid=qualification-progress]")).not.toBeNull());
    const panel = view.querySelector<HTMLElement>("[data-testid=qualification-progress]")!;
    expect(panel.querySelector(".console-spinner")).not.toBeNull();
    const bar = panel.querySelector<HTMLProgressElement>("progress")!;
    expect(bar.getAttribute("max")).toBe("2");
    expect(bar.getAttribute("value")).toBe("1");
    expect(panel.textContent).toContain("1 of 2 turns completed (50%)");
    expect(panel.textContent).toContain("Anthropic API");
    expect(panel.textContent).toContain("Claude Sonnet 5.5 — Balanced");
    expect(panel.textContent).toContain("Environment baseline");
    expect(panel.textContent).toContain("every 3 seconds");
    expect(panel.textContent).toContain("No time estimate is shown");
    expect(panel.textContent).not.toMatch(/remaining|ETA/);
    expect(button(view, "Cancel qualification").disabled).toBe(false);
  });

  it("shows an indeterminate bar when the server has not reported a total", async () => {
    const view = mount(server(withRun(0, 0)), "qualifications");
    await waitFor(() => expect(view.querySelector("[data-testid=qualification-progress]")).not.toBeNull());
    const bar = view.querySelector<HTMLProgressElement>("[data-testid=qualification-progress] progress")!;
    expect(bar.hasAttribute("value")).toBe(false);
    expect(view.textContent).toContain("The server has not reported the number of turns yet.");
  });

  it("says when a cancel was requested and stops offering it", async () => {
    const data = withRun(1, 2);
    data.profiles[data.profiles.length - 1].qualification = { ...runningRun(1, 2), cancel_requested: true };
    const view = mount(server(data), "qualifications");
    await waitFor(() => expect(view.textContent).toContain("Cancel requested; stopping"));
    expect(button(view, "Cancel qualification").disabled).toBe(true);
  });

  it.each([
    [{ status: "passed", code: null }, "Passed"],
    [{ status: "failed", code: "GATES_FAILED:G-3" }, "Failed"],
    [{ status: "cancelled", code: "CANCELLED" }, "Cancelled"],
    [{ status: "error", code: "INTERRUPTED" }, "Interrupted"],
    [{ status: "error", code: "CREDENTIAL_REVOKED" }, "Stopped (error)"],
  ] as const)("shows how the followed run ended (%o) with its recovery", async (end, label) => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      let calls = 0;
      const finished: ModelQualification = {
        ...runningRun(2, 2), status: end.status, code: end.code, finished_at: "2026-10-30T09:01:00+00:00",
        diagnosis: end.status === "passed"
          ? { category: "passed", cause: "PASSED", action: "NONE", retryable: false, supersedes_pass: false }
          : end.code === "CREDENTIAL_REVOKED"
            ? { category: "configuration", cause: "CREDENTIAL_REVOKED", action: "TEST_CONNECTION", retryable: false, supersedes_pass: false }
            : { category: "technical", cause: end.code ?? "UNKNOWN", action: "RUN_AGAIN", retryable: true, supersedes_pass: false },
      };
      const done: ModelOverview = { ...overview, profiles: [...overview.profiles, claudeBalanced(finished)] };
      const view = mount(vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/api/assistant/admin/models")) {
          calls += 1;
          return json(calls === 1 ? withRun(1, 2) : done);
        }
        if (url.includes("/admin/models/audit")) return json({ events: [] });
        return json({ detail: { code: "NOT_FOUND", message: "No such model profile." } }, 404);
      }), "qualifications");
      await waitFor(() => expect(view.querySelector("[data-testid=qualification-progress]")).not.toBeNull());
      await act(async () => { await vi.advanceTimersByTimeAsync(RUNNING_REFRESH_MS + 100); });
      await waitFor(() => expect(view.querySelector("[data-testid=qualification-finished]")).not.toBeNull());
      const panel = view.querySelector<HTMLElement>("[data-testid=qualification-finished]")!;
      expect(panel.querySelector("h2")?.textContent).toBe(`Qualification finished: Claude Sonnet 5.5 — Balanced ${label}`);
      expect(panel.textContent).toContain("2 of 2 turns completed");
      expect(panel.textContent).toContain("Next:");
      if (end.code === "CREDENTIAL_REVOKED") expect(panel.textContent).toContain("The session key the run was given ended");
      expect(view.querySelector("[data-testid=qualification-progress]")).toBeNull();
      await act(async () => button(view, "Show technical results").click());
      await waitFor(() => expect(view.querySelector("#qualification-heading")).not.toBeNull());
    } finally {
      vi.useRealTimers();
    }
  });
});

// --- D-107: Claude set up by HR on Providers ---------------------------------------------------

describe("AiModelManagement Claude setup by HR (D-107)", () => {
  const claudeProfile = (overrides: Partial<ModelProfileView> = {}) => profile({
    profile_id: "anthropic_claude_sonnet_5_5_medium", display_name: "Claude Sonnet 5.5", source: "code", deployment: "anthropic",
    model_id: "claude-sonnet-5-5", model_version: "medium", endpoint: "api.anthropic.com · claude-sonnet-5-5",
    status: "pending_authorisation", reason: "ANTHROPIC_NOT_AUTHORISED", active: false, activation_blockers: ["ANTHROPIC_NOT_AUTHORISED"],
    details: { model: "Claude Sonnet 5.5", provider: "ANTHROPIC", scope: "NOT_AUTHORISED", reasoning_effort: "medium", thinking: "adaptive", decision: "D-099" },
    ...overrides,
  });
  const CODES = ["dedicated_workspace", "inference_key_only", "key_revoked_at_fyp_end", "workspace_limit_set"];
  const setup = (overrides: Partial<AnthropicSetup> = {}): AnthropicSetup => ({
    managed: true, readable: true, source: "none", enabled: false, readiness: "ANTHROPIC_NOT_AUTHORISED", local_deployment: true,
    record: null, workspace_read: null, confirmations_required: CODES, workspace_limit_max_micro_usd: 30_000_000, ...overrides,
  });
  const data = (anthropicSetup: AnthropicSetup): ModelOverview => ({
    ...overview, profiles: [overview.profiles[0], claudeProfile()], anthropic_setup: anthropicSetup,
  });
  function setupServer(first: AnthropicSetup, calls: Array<{ method: string; url: string; body: string | null }>, after?: AnthropicSetup) {
    let current = first;
    return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      calls.push({ method, url, body: typeof init?.body === "string" ? init.body : null });
      if (url.endsWith("/provider/anthropic/workspace-read")) {
        current = { ...current, workspace_read: { workspace_id: "wrkspc_01TestWorkspace", at: "2026-10-30T10:00:00+00:00" } };
        return json({ outcome: "passed", code: null, workspace_id: "wrkspc_01TestWorkspace", setup: current });
      }
      if (url.endsWith("/provider/anthropic") && method === "PUT") {
        current = after ?? current;
        return json(current);
      }
      if (url.endsWith("/api/assistant/admin/models")) return json(data(current));
      if (url.includes("/admin/models/audit")) return json({ events: [] });
      return json({ detail: { code: "NOT_FOUND", message: "No such model profile." } }, 404);
    });
  }
  const panel = (view: HTMLElement) => view.querySelector<HTMLElement>("[data-testid=claude-setup]")!;

  it("reads the workspace, needs every confirmation and a limit, then enables Claude", async () => {
    const calls: Array<{ method: string; url: string; body: string | null }> = [];
    const view = mount(setupServer(setup(), calls), "providers");
    await waitFor(() => expect(view.querySelector("[data-testid=claude-setup]")).not.toBeNull());
    expect(panel(view).textContent).toContain("Claude setup — Not enabled");
    const enable = () => button(panel(view), "Enable Claude for Verified Synthetic Cases");
    expect(enable().disabled).toBe(true);
    await act(async () => button(panel(view), "Read Workspace").click());
    await waitFor(() => expect(panel(view).textContent).toContain("wrkspc_01TestWorkspace"));
    expect(enable().disabled).toBe(true);
    for (const code of CODES) act(() => panel(view).querySelector<HTMLInputElement>(`[data-testid=confirm-${code}]`)!.click());
    expect(enable().disabled).toBe(true);  // no limit yet
    typeInto(panel(view).querySelector<HTMLInputElement>("#claude-workspace-limit")!, "31");
    expect(enable().disabled).toBe(true);  // above US$30.00
    typeInto(panel(view).querySelector<HTMLInputElement>("#claude-workspace-limit")!, "30");
    expect(enable().disabled).toBe(false);
    await act(async () => enable().click());
    const put = calls.find((call) => call.method === "PUT");
    expect(put?.url).toContain("/api/assistant/admin/models/provider/anthropic");
    expect(JSON.parse(put?.body ?? "{}")).toEqual({
      expected_revision: 0, enabled: true, workspace_id: "wrkspc_01TestWorkspace",
      workspace_limit_micro_usd: 30_000_000, confirmations: CODES,
    });
  });

  it("shows an enabled setup with its owner-confirmed limit and offers to disable it", async () => {
    const calls: Array<{ method: string; url: string; body: string | null }> = [];
    const enabled = setup({
      source: "hr", enabled: true, readiness: null,
      record: { revision: 2, enabled: true, workspace_id: "wrkspc_01TestWorkspace", workspace_limit_micro_usd: 30_000_000,
        workspace_limit_basis: "owner_confirmed", confirmations: CODES, changed_at: "2026-10-30T10:00:00+00:00", changed_by: "hr-admin" },
    });
    const view = mount(setupServer(enabled, calls), "providers");
    await waitFor(() => expect(view.querySelector("[data-testid=claude-setup]")).not.toBeNull());
    const text = panel(view).textContent ?? "";
    expect(text).toContain("Claude setup — Enabled for verified synthetic cases");
    expect(text).toContain("US$30.00, owner-confirmed. It is not read from Anthropic, and the app cannot verify it.");
    expect(text).toContain("wrkspc_01TestWorkspace");
    expect(() => button(panel(view), "Enable Claude for Verified Synthetic Cases")).toThrow();
    await act(async () => button(panel(view), "Disable Claude").click());
    expect(JSON.parse(calls.find((call) => call.method === "PUT")?.body ?? "{}")).toEqual({ expected_revision: 2, enabled: false });
  });

  it("lets HR take over or disable a Claude configured on the server (QG L1, L2)", async () => {
    const calls: Array<{ method: string; url: string; body: string | null }> = [];
    const view = mount(setupServer(setup({ source: "environment", enabled: true, readiness: null }), calls), "providers");
    await waitFor(() => expect(view.querySelector("[data-testid=claude-setup]")).not.toBeNull());
    expect(panel(view).textContent).toContain("Setting it up here replaces that configuration");
    expect(button(panel(view), "Read Workspace")).toBeTruthy();
    await act(async () => button(panel(view), "Disable Claude").click());
    expect(JSON.parse(calls.find((call) => call.method === "PUT")?.body ?? "{}")).toEqual({ expected_revision: 0, enabled: false });
  });

  it("says who enabled Claude on Data Access & Privacy (QG L2)", async () => {
    const policy: ModelDataAccess = {
      status: "default", revision: 0, changed_at: null,
      classes: [{ provider_class: "anthropic", restricted: true, locked: true }, { provider_class: "local_internal", restricted: false, locked: false }],
      active_class: null, active_restricted: false, verification: "D-095",
    };
    const view = mount(server({ ...data(setup({ source: "environment", enabled: true, readiness: null })), data_access: policy }), "privacy");
    await waitFor(() => expect(view.querySelector("[data-testid=access-anthropic]")).not.toBeNull());
    const row = view.querySelector("[data-testid=access-anthropic]")!.textContent ?? "";
    expect(row).toContain("Enabled by the server configuration (D-099)");
    expect(row).not.toContain("Enabled by HR");
  });

  it("offers no setup outside the approved local deployment", async () => {
    const view = mount(setupServer(setup({ local_deployment: false }), []), "providers");
    await waitFor(() => expect(view.querySelector("[data-testid=claude-setup]")).not.toBeNull());
    expect(panel(view).textContent).toContain("not the approved local development set-up");
    expect(button(panel(view), "Read Workspace").disabled).toBe(true);
  });

  it("names a provider as enabled apart from what it may receive", async () => {
    const policy: ModelDataAccess = {
      status: "default", revision: 0, changed_at: null,
      classes: [
        { provider_class: "openrouter", restricted: true, locked: true },
        { provider_class: "anthropic", restricted: true, locked: true },
        { provider_class: "it_configured", restricted: true, locked: true },
        { provider_class: "local_internal", restricted: false, locked: false },
      ],
      active_class: "local_internal", active_restricted: false, verification: "D-095",
    };
    const enabled = setup({ source: "hr", enabled: true, readiness: null });
    const view = mount(server({ ...data(enabled), data_access: policy }), "privacy");
    await waitFor(() => expect(view.querySelector("[data-testid=access-anthropic]")).not.toBeNull());
    const row = view.querySelector("[data-testid=access-anthropic]")!.textContent ?? "";
    expect(row).toContain("Enabled by HR (Providers → Anthropic)");
    expect(row).toContain("Verified synthetic cases only");
  });
});
