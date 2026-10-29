// @vitest-environment jsdom

import { act, StrictMode, useState } from "react";
import { createRoot, type Root } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ModelBudgetStatus, ModelOverview, ModelProfileView, ModelQualification } from "../aiAssistant";
import { configureAuthenticatedTransport } from "../api";
import { requiredCapabilityForPath, paths, WorkspaceTabs } from "../navigation";
import type { AuthenticatedProfile } from "../types";
import { ConsoleDialog, consoleSection, sectionSearch, type ConsoleSection } from "./aiModels/ConsoleShell";
import AiModelManagement, {
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
    expect(readable("REMOTE_MANIFEST_MISSING")).toContain("question list and count");
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
      return json({ source: "hr_memory", status: "configured", hr_editable: true, persistence: "memory_only", set_at: 1, set_by: "hr-admin" });
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
    expect(button(view, "Save Key").disabled).toBe(true);
    expect(button(view, "Test Connection").disabled).toBe(true);
    typeInto(input!, FAKE_KEY);
    await act(async () => button(view, "Save Key").click());
    await waitFor(() => expect(view.textContent).toContain("Key saved on the server."));
    const put = calls.find((call) => call.method === "PUT");
    expect(put?.url).toContain("/api/assistant/admin/models/credential");
    expect(JSON.parse(put?.body ?? "{}")).toEqual({ api_key: FAKE_KEY });
    expect(view.querySelector<HTMLInputElement>("#openrouter-key-input")?.value).toBe("");
    expect(view.innerHTML).not.toContain(FAKE_KEY);
    expect(JSON.stringify({ ...localStorage })).not.toContain(FAKE_KEY);
    expect(JSON.stringify({ ...sessionStorage })).not.toContain(FAKE_KEY);
    expect(document.cookie).not.toContain(FAKE_KEY);
  });

  it("offers Clear Key and Test Connection for an HR-entered key, and says it is memory-only", async () => {
    const calls: Array<{ method: string; url: string; body: string | null }> = [];
    const data = {
      ...overview, profiles: [profile({}), remoteSelectable],
      budget: budget({ source: "hr_memory", status: "configured", set_by: "hr-admin", set_at: 1 }),
    };
    const view = mount(keyServer(data, calls), "providers");
    await waitFor(() => expect(view.textContent).toContain("OpenRouter API Key — Configured"));
    expect(view.textContent).toContain("enter it again after the service restarts");
    await act(async () => button(view, "Test Connection").click());
    await waitFor(() => expect(calls.some((call) => call.method === "POST" && call.url.endsWith("/openrouter_gpt_oss_120b/connection-test"))).toBe(true));
    await act(async () => button(view, "Clear Key").click());
    await waitFor(() => expect(calls.some((call) => call.method === "DELETE")).toBe(true));
  });

  it("does not offer to change an environment-managed key", async () => {
    const data = {
      ...overview, profiles: [profile({}), remoteSelectable],
      budget: budget({ source: "env_file", status: "configured", hr_editable: false, persistence: "server" }),
    };
    const view = mount(keyServer(data, []), "providers");
    await waitFor(() => expect(view.textContent).toContain("OpenRouter API Key — Configured"));
    expect(view.textContent).toContain("apps/assistant/.env");
    expect(view.querySelector("#openrouter-key-input")).toBeNull();
    expect(() => button(view, "Save Key")).toThrow();
    expect(() => button(view, "Clear Key")).toThrow();
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
    ...budget({ source: "hr_memory", status: "configured", set_by: "hr-admin", set_at: 1 }),
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
    await waitFor(() => expect(view.textContent).toContain("Calls this activation"));
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
    expect(view.textContent).toContain("not authorised for CLM use (D-099 proposed)");
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
    expect(readable("ANTHROPIC_NOT_AUTHORISED")).toContain("D-099 proposed");
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
    expect(view.textContent).toContain("This is an external, paid API (Claude Sonnet 5.5 through the Anthropic API, D-099 proposed).");
    expect(view.textContent).toContain("Nothing switches to or from Claude automatically.");
  });

  it("labels the overview's spending figures as GPT-OSS when Claude is listed", async () => {
    const view = mount(server({ ...withClaude(), budget: budget() }));
    await waitFor(() => expect(view.textContent).toContain("Available now (GPT-OSS)"));
  });

  it("states on Spending & Limits that the controls are GPT-OSS only", async () => {
    const view = mount(keyServer({ ...withClaude(), budget: budget() }, []), "spending");
    await waitFor(() => expect(view.textContent).toContain("These limits apply to GPT-OSS 120B only."));
    expect(view.textContent).toContain("Claude Sonnet 5.5 (D-099 proposed) has its own fixed safeguards");
  });

  it("explains a Claude recovery in Anthropic terms, not OpenRouter's", async () => {
    const run: ModelQualification = {
      ...qualification, qualification_id: "d".repeat(32), status: "failed", code: "CONNECTION_FAILED",
      diagnosis: { category: "billing_uncertain", cause: "LEDGER_NOT_RECONCILED", action: "ESCALATE_OPERATOR", retryable: false, supersedes_pass: false },
    };
    const view = mount(server(withClaude({ qualification: run, paid_qualification: { ...paid, sufficient: false, refusal: "PROVIDER_LIMIT_NOT_CHECKED" } })), "qualifications");
    await waitFor(() => expect(view.querySelector("[data-testid=recovery-anthropic_claude_sonnet_5_5_medium]")).not.toBeNull());
    const card = view.querySelector("[data-testid=recovery-anthropic_claude_sonnet_5_5_medium]")!.textContent ?? "";
    expect(card).toContain("reconciled with the Anthropic Console's usage");
    expect(card).toContain("scripts/budget_ledger.py --anthropic");
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

  it("reads the section from the location and falls back to the overview", async () => {
    expect(consoleSection("audit")).toBe("audit");
    expect(consoleSection("unknown")).toBe("overview");
    expect(consoleSection(null)).toBe("overview");
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
    expect(view.textContent).toContain("Calls this activation");
    expect(view.querySelector('a.console-stat[href="/admin/ai-models?section=spending"]')).not.toBeNull();
  });
});
