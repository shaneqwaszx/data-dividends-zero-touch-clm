// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ModelOverview, ModelProfileView, ModelQualification } from "../aiAssistant";
import { configureAuthenticatedTransport } from "../api";
import { requiredCapabilityForPath, paths, WorkspaceTabs } from "../navigation";
import type { AuthenticatedProfile } from "../types";
import AiModelManagement, {
  AUDIT_REFRESH_MS,
  modelManagementQueryKeys,
  readable,
  RUNNING_REFRESH_MS,
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

function mount(fetchMock: ReturnType<typeof vi.fn>): HTMLDivElement {
  vi.stubGlobal("fetch", fetchMock);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
  act(() => root?.render(<QueryClientProvider client={client}><AiModelManagement actor={hr} /></QueryClientProvider>));
  return container;
}

function button(view: HTMLElement, label: string, row?: string): HTMLButtonElement {
  const scope = row
    ? [...view.querySelectorAll("tr")].find((tr) => tr.textContent?.includes(row)) ?? view
    : view;
  const found = [...scope.querySelectorAll("button")].find((item) => item.textContent === label);
  if (!found) throw new Error(`no button ${label}`);
  return found as HTMLButtonElement;
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
    await waitFor(() => expect(view.textContent).toContain("Access refused"));
    expect(button(view, "No earlier model to roll back to").disabled).toBe(true);
  });

  it("shows qualification as technical only, with answer quality not scored and G-5 reported only", async () => {
    const view = mount(server(overview));
    await waitFor(() => expect(view.textContent).toContain("Qwen3 8B (LM Studio)"));
    act(() => button(view, "Passed", "Qwen3").click());
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
    act(() => button(view, "Activate", "Qwen3").click());
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
    await act(async () => button(view, "Test connection", "Qwen3").click());
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
    act(() => root?.render(<QueryClientProvider client={client}><AiModelManagement actor={hr} /></QueryClientProvider>));
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
    act(() => button(view, "Failed", "Qwen3").click());
    await waitFor(() => expect(view.textContent).toContain("Gates failed: G-6, G-7"));
    expect(view.textContent).not.toContain("g-7");
  });
});
