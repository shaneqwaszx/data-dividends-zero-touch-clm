import { createServer } from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";
import { expect, test } from "@playwright/test";
import { createBrowserNetworkPolicy, handleBrowserRoute } from "../playwright.config";

// D-110: real Chromium rendering the actual AI Models page, Spending & Limits, against a local
// synthetic assistant stub. The stub grants no authority: the server's own checks are covered
// by the assistant's tests. No Live claim; no ledger, key or provider is involved.
test("D-110 HR previews and applies a Claude ledger reconciliation in real Chromium", async ({ page }) => {
  test.setTimeout(60000);
  page.setDefaultTimeout(8000);
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.name));
  const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
  const compiled = await build({
    stdin: { contents: `
      import {createRoot} from "react-dom/client";
      import {QueryClient, QueryClientProvider} from "@tanstack/react-query";
      import {MemoryRouter} from "react-router";
      import AiModelManagement from "./src/pages/AiModelManagement";
      import {paths} from "./src/navigation";
      import {sectionSearch} from "./src/pages/aiModels/ConsoleShell";
      const hr = { user_id: "hr-admin", display_name: "HR Admin", role: "HR", team_id: null,
        team_display_name: null, team_type: null, team_description: "", client_scope_label: "",
        capabilities: ["IDENTITY_ADMIN", "MODEL_CONFIG_MANAGE"] };
      const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
      createRoot(document.getElementById("root")).render(
        <MemoryRouter initialEntries={[paths.aiModels + sectionSearch("spending")]}>
          <QueryClientProvider client={client}><AiModelManagement actor={hr} /></QueryClientProvider>
        </MemoryRouter>);
    `, loader: "tsx", resolveDir: root },
    bundle: true, write: false, format: "esm", outfile: "client.js", jsx: "automatic",
    define: { "import.meta.env": "{}" },
  });
  const script = compiled.outputFiles!.find((file) => file.path.endsWith("client.js"))!.text;
  const css = compiled.outputFiles!.find((file) => file.path.endsWith("client.css"))?.text ?? "";

  const now = Date.now();
  const iso = (ms: number) => new Date(ms).toISOString();
  const HOUR = 3_600_000;
  const profile = (extra: Record<string, unknown>) => ({
    profile_id: "env_default", display_name: "Environment baseline", source: "environment",
    deployment: "openai_compatible", model_id: "ministral-3:8b", model_version: null,
    endpoint: "127.0.0.1:11434", context_window_tokens: null, max_answer_tokens: 600,
    temperature: 0.2, timeout_seconds: 90, streaming: true, fingerprint: "0123456789ab",
    status: "selectable", reason: null, active: true, connection_test: null,
    qualification: null, activation_blockers: [], ...extra,
  });
  const claude = {
    configured: true, timezone: "Asia/Singapore", daily_cap_micro_usd: 1_000_000,
    workspace_limit_micro_usd: 30_000_000, lifetime_ceiling_micro_usd: 30_000_000,
    next_reset_at: iso(now + 6 * HOUR), preflight: null,
    ledger: { profile_ok: true, cap_micro_usd: 25_000_000, committed_micro_usd: 74_136, headroom_micro_usd: 24_925_864, headroom_usd: "24.925864", open_calls: 0, breaker_open: false, breaker_code: null, reconciled_at: iso(now - 2 * HOUR) },
    daily: { cap_micro_usd: 1_000_000, settled_today_micro_usd: 0, in_flight_micro_usd: 0, remaining_micro_usd: 1_000_000, remaining_usd: "1.000000" },
    effective_remaining_micro_usd: 1_000_000, effective_remaining_usd: "1.000000", reservation_micro_usd: 96_000, refusal: null,
    controls: {
      revision: 2, readable: true, daily_cap_micro_usd: 1_000_000, daily_cap_range: [1, 5_000_000],
      daily_cap_default_micro_usd: 1_000_000, raise_requires: ["confirmation", "reconciled_within_one_day"],
      daily_cap_source: "hr", max_calls: 20, max_calls_range: [1, 20], max_calls_source: "hr",
      calls_used: 3, calls_remaining: 17, changed_at: iso(now - 24 * HOUR), changed_by: "hr-admin",
      lifetime: { opening_usage_micro_usd: 20_000, cap_micro_usd: 25_000_000, max_cap_micro_usd: 30_000_000, committed_micro_usd: 74_136 },
    },
    reconciliation: {
      key_alias: "key-02", reconciled_at: iso(now - 2 * HOUR), chat_deadline_at: iso(now + 166 * HOUR),
      paid_deadline_at: iso(now + 22 * HOUR), chat_fresh: true, paid_fresh: true,
      chat_window_seconds: 604_800, paid_window_seconds: 86_400, baseline_micro_usd: 20_000,
      local_charged_micro_usd: 54_136, estimate_micro_usd: 74_136, last_provider_usage_micro_usd: 20_000,
      open_reserved_micro_usd: 0, tolerance_micro_usd: 50_000,
      calls: { total: 6, open: 0, settled: 6, unsettled: 0, abandoned: 0, verified: 6, quarantined: 0, unverified: 0, charged_micro_usd: 54_136 },
    },
  };
  const claudeProfile = profile({
    profile_id: "anthropic_claude_sonnet_5_5_fast", display_name: "Claude Sonnet 5.5 — Fast", source: "code",
    deployment: "anthropic", model_id: "claude-sonnet-5-5", model_version: "fast", endpoint: "api.anthropic.com · claude-sonnet-5-5",
    temperature: null, max_answer_tokens: 3000, active: false, activation_blockers: [],
    paid_qualification: { calls: 2, reservation_micro_usd: 96_000, estimate_micro_usd: 192_000, effective_remaining_micro_usd: 1_000_000, refusal: null, sufficient: true },
    details: { model: "Claude Sonnet 5.5", provider: "ANTHROPIC", reasoning_effort: "low", decision: "D-099" },
  });
  const overview = {
    configured: true, file_status: "ok", file_errors: [], model_enabled: true, revision: 3,
    active: { profile_id: "env_default", display_name: "Environment baseline", model_id: "ministral-3:8b", prompt_limit: null, qualification_id: null, changed_at: null, changed_by: null, config_changed: false, reverted: null },
    last_good: null, quality: { status: "NOT_SCORED", reason: "OWNER_GOLD_NOT_LABELLED" }, basis: "5dc26b296026", running: null,
    profiles: [profile({}), claudeProfile],
    budget: { configured: false, claude },
  };
  const preview = {
    preview_id: "b".repeat(32), expires_at: iso(now + 300_000), fallback: false, settle_lag_seconds: 700, margin_seconds: 600,
    before: { baseline_micro_usd: 20_000, local_charged_micro_usd: 54_136, estimate_micro_usd: 74_136, last_provider_usage_micro_usd: 20_000, reconciled_at: iso(now - 2 * HOUR) },
    after: { baseline_micro_usd: 80_000, local_charged_micro_usd: 0, estimate_micro_usd: 80_000, last_provider_usage_micro_usd: 80_000 },
    drift_micro_usd: 5_864, tolerance_micro_usd: 50_000, breaker_opens: false, carried_micro_usd: 0, cap_micro_usd: 25_000_000,
    chat_deadline_at: iso(now + 168 * HOUR), paid_deadline_at: iso(now + 24 * HOUR),
    inputs: { usage_micro_usd: 80_000, as_of: iso(now - 60_000), as_of_kind: "console_refreshed", viewed_at: iso(now - 30_000) },
  };
  const runs: unknown[] = [];
  const posts: Array<{ url: string; body: unknown }> = [];

  const server = createServer((request, response) => {
    request.on("error", () => undefined);
    response.on("error", () => undefined);
    const url = request.url ?? "/";
    const send = (status: number, body: unknown) => {
      response.statusCode = status;
      response.setHeader("Content-Type", "application/json");
      response.end(JSON.stringify(body));
    };
    if (url === "/client.js") {
      response.setHeader("Content-Type", "text/javascript"); response.end(script); return;
    }
    if (request.method === "POST") {
      let raw = "";
      request.on("data", (part: Buffer) => { raw += part.toString(); });
      request.on("end", () => {
        const body = JSON.parse(raw || "{}") as Record<string, unknown>;
        posts.push({ url, body });
        if (url.endsWith("/budget/claude/reconciliation/preview")) { send(200, preview); return; }
        if (url.endsWith("/budget/claude/reconciliation/apply")) {
          const run = { run_id: "c".repeat(32), status: "applied", actor: "hr-admin", intent_at: iso(Date.now()), finished_at: iso(Date.now()),
            usage_micro_usd: 80_000, drift_micro_usd: 5_864, as_of: preview.inputs.as_of, as_of_kind: "console_refreshed",
            event_id: 9, reason: "apply_returned", attribution_basis: "apply_returned", owner_reference: null, acknowledged_state: null };
          runs.unshift(run);
          send(200, { outcome: "applied", run, budget: overview.budget }); return;
        }
        send(404, { detail: { code: "NOT_FOUND", message: "Nothing changed." } });
      });
      return;
    }
    if (url.endsWith("/api/assistant/admin/models")) { send(200, overview); return; }
    if (url.includes("/api/assistant/admin/models/audit")) { send(200, { events: [] }); return; }
    if (url.endsWith("/api/assistant/admin/models/budget/claude/reconciliation")) {
      send(200, { runs, prerequisite_recorded: true, marker_readable: true, marker_run_id: null, marker_overridden: false }); return;
    }
    if (url.startsWith("/api/")) { send(404, { detail: { code: "NOT_FOUND", message: "No such model profile." } }); return; }
    response.setHeader("Content-Type", "text/html");
    response.end(`<html><head><style>${css}</style></head><body><div id="root"></div>
      <script type="module" src="/client.js"></script></body></html>`);
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  if (!address || typeof address === "string") throw new Error("missing owned address");
  const origin = `http://127.0.0.1:${address.port}`;
  const violations: string[] = [];
  const policy = createBrowserNetworkPolicy({ frontendOrigin: origin,
    backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false });
  await page.route("**/*", (route) => handleBrowserRoute(route, policy, violations));
  try {
    await page.goto(origin);
    const panel = page.getByTestId("claude-reconcile");
    await expect(panel.getByRole("heading", { name: "Reconcile with the Anthropic Console (HR, D-110)" })).toBeVisible();
    const previewButton = panel.getByTestId("reconcile-preview");
    await expect(previewButton).toBeDisabled();
    await panel.getByLabel("Cumulative workspace cost in the Console (US$)").fill("0.08");
    await panel.getByLabel("Console data refreshed at").fill("2026-10-31T10:00");
    await panel.getByLabel("I looked at the Console at").fill("2026-10-31T10:05");
    await panel.getByTestId("reconcile-scope-workspace").check();
    await panel.getByTestId("reconcile-scope-only").check();
    await expect(previewButton).toBeDisabled();
    await panel.getByTestId("reconcile-scope-cumulative").check();
    await expect(previewButton).toBeEnabled();
    await previewButton.click();
    await expect(panel.getByTestId("reconcile-drift")).toContainText("US$0.005864");
    expect(posts.filter((post) => post.url.endsWith("/apply"))).toHaveLength(0);

    // The dialog: Escape closes it without applying; the figure must be typed again.
    await panel.getByTestId("reconcile-apply-open").click();
    const dialog = page.getByTestId("reconcile-confirm");
    await expect(dialog).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
    await panel.getByTestId("reconcile-apply-open").click();
    const apply = dialog.getByTestId("reconcile-apply");
    await expect(apply).toBeDisabled();
    await dialog.getByTestId("reconcile-echo").fill("0.07");
    await expect(apply).toBeDisabled();
    await dialog.getByTestId("reconcile-echo").fill("0.08");
    await apply.click();
    await expect(page.getByTestId("reconcile-message")).toContainText("Reconciled.");
    await expect(page.getByTestId("reconcile-runs")).toContainText("Applied");

    const sent = posts.find((post) => post.url.endsWith("/preview"))!.body as Record<string, unknown>;
    expect(sent).toMatchObject({ usage_micro_usd: 80_000, as_of_kind: "console_refreshed", scope_workspace: true, scope_only: true, scope_cumulative: true });
    expect(posts.find((post) => post.url.endsWith("/apply"))!.body).toEqual({
      preview_id: "b".repeat(32), confirm_usage_micro_usd: 80_000, scope_workspace: true, scope_only: true, scope_cumulative: true,
    });
    expect(pageErrors).toEqual([]);
    expect(violations).toEqual([]);
  } finally {
    await new Promise<void>((resolve) => server.close(() => resolve()));
  }
});
