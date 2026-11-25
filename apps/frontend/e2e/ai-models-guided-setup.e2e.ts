import { createServer } from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";
import { expect, test } from "@playwright/test";
import { createBrowserNetworkPolicy, handleBrowserRoute } from "../playwright.config";

// D-118: real Chromium rendering the actual AI Models page on its landing section, "Set up AI",
// against a local synthetic assistant stub that plays a fresh teammate deployment. The stub
// grants no authority: the server's own checks (sessions, the ledger, RBAC) are covered by the
// assistant's tests. No Live claim; no ledger, key or provider is involved.
test("D-118 a fresh teammate sets up Claude in four steps with two confirmations in real Chromium", async ({ page }) => {
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
      const hr = { user_id: "biz-ops", display_name: "HR Admin", role: "HR", team_id: null,
        team_display_name: null, team_type: null, team_description: "", client_scope_label: "",
        capabilities: ["IDENTITY_ADMIN", "MODEL_CONFIG_MANAGE"] };
      const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
      createRoot(document.getElementById("root")).render(
        <MemoryRouter initialEntries={[paths.aiModels]}>
          <QueryClientProvider client={client}><AiModelManagement actor={hr} /></QueryClientProvider>
        </MemoryRouter>);
    `, loader: "tsx", resolveDir: root },
    bundle: true, write: false, format: "esm", outfile: "client.js", jsx: "automatic",
    define: { "import.meta.env": "{}" },
  });
  const script = compiled.outputFiles!.find((file) => file.path.endsWith("client.js"))!.text;
  const css = compiled.outputFiles!.find((file) => file.path.endsWith("client.css"))?.text ?? "";

  // The fresh deployment's state, changed only by the stub's handlers below.
  const state = { workspaceRead: false, enabled: false, connected: false, qualified: false, active: false, session: false };
  const claudeProfile = () => ({
    profile_id: "anthropic_claude_sonnet_5_5_medium", display_name: "Claude Sonnet 5.5 — Balanced", source: "code",
    deployment: "anthropic", model_id: "claude-sonnet-5-5", model_version: "balanced", endpoint: "api.anthropic.com · claude-sonnet-5-5",
    context_window_tokens: null, max_answer_tokens: 3000, temperature: null, timeout_seconds: 60, streaming: true,
    fingerprint: "0123456789ab", status: "selectable", reason: null, active: state.active,
    connection_test: state.connected ? { outcome: "passed", code: null, listed: null, complete_ms: null, stream_ms: null, first_piece_ms: null } : null,
    qualification: null, activation_blockers: state.qualified ? [] : ["NOT_QUALIFIED"],
    eligible_qualification: state.qualified ? { qualification_id: "q".repeat(32), finished_at: null, is_latest: true } : null,
    paid_qualification: { calls: 2, reservation_micro_usd: 96_000, estimate_micro_usd: 192_000, effective_remaining_micro_usd: 5_000_000, refusal: null, sufficient: true },
    details: { model: "Claude Sonnet 5.5", provider: "ANTHROPIC", reasoning_effort: "medium" },
  });
  const overview = () => ({
    configured: true, file_status: "ok", file_errors: [], model_enabled: true, revision: 3,
    active: state.active
      ? { profile_id: "anthropic_claude_sonnet_5_5_medium", display_name: "Claude Sonnet 5.5 — Balanced", model_id: "claude-sonnet-5-5", prompt_limit: null, qualification_id: null, changed_at: null, changed_by: null, config_changed: false, reverted: null }
      : { profile_id: "env_default", display_name: "Environment baseline", model_id: "ministral-3:8b", prompt_limit: null, qualification_id: null, changed_at: null, changed_by: null, config_changed: false, reverted: null },
    last_good: null, quality: { status: "NOT_SCORED", reason: "OWNER_GOLD_NOT_LABELLED" }, basis: "basis", running: null,
    profiles: [claudeProfile()],
    anthropic_setup: {
      managed: true, readable: true, source: state.enabled ? "hr" : "none", enabled: state.enabled,
      readiness: state.enabled ? null : "ANTHROPIC_NOT_ENABLED", local_deployment: true,
      record: state.enabled ? { revision: 1, enabled: true, workspace_id: "wrkspc_fypteammate", workspace_limit_micro_usd: 5_000_000,
        workspace_limit_basis: "owner_confirmed", confirmations: [], changed_at: new Date().toISOString(), changed_by: "biz-ops" } : null,
      workspace_read: state.workspaceRead ? { workspace_id: "wrkspc_fypteammate", at: new Date().toISOString() } : null,
      confirmations_required: ["dedicated_workspace", "inference_key_only", "key_revoked_at_fyp_end", "workspace_limit_set"],
      workspace_limit_max_micro_usd: 30_000_000,
    },
  });
  const provider = (name: string) => ({
    provider: name, ledger: name === "anthropic" && state.enabled ? "ready" : "missing", code: null,
    accounting_mode: name === "anthropic" && state.enabled ? "provider_capped" : null, origin: null, opening_basis: null,
    allowance_default_micro_usd: 5_000_000, allowance_max_micro_usd: 5_000_000,
    session: name === "anthropic" && state.session ? { session_id: "s".repeat(32), revision: 1, allowance_micro_usd: 5_000_000,
      settled_micro_usd: 150_000, held_micro_usd: 0, committed_micro_usd: 150_000, remaining_micro_usd: 4_850_000, calls: 2,
      chat_calls: 0, started_at: new Date().toISOString() } : null,
    breaker_open: false, breaker_code: null, resumable: false, resume_blocker: null, blockers: [],
  });
  const sent: Array<{ method: string; url: string; body: unknown }> = [];

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
    if (request.method === "POST" || request.method === "PUT") {
      let raw = "";
      request.on("data", (part: Buffer) => { raw += part.toString(); });
      request.on("end", () => {
        const body = JSON.parse(raw || "{}") as Record<string, unknown>;
        sent.push({ method: request.method!, url, body: url.includes("/credential") ? "(key withheld)" : body });
        if (url.endsWith("/credential/anthropic")) { send(200, { source: "hr_session", status: "configured", hr_editable: true, persistence: "memory_only", set_at: 1, set_by: "biz-ops" }); return; }
        if (url.endsWith("/workspace-read")) { state.workspaceRead = true; send(200, { outcome: "passed", code: null, workspace_id: "wrkspc_fypteammate", setup: overview().anthropic_setup }); return; }
        if (url.endsWith("/provider/anthropic")) { state.enabled = true; send(200, overview().anthropic_setup); return; }
        if (url.endsWith("/connection-test")) { state.connected = true; send(200, { outcome: "passed", code: null }); return; }
        if (url.endsWith("/qualifications")) { state.qualified = true; state.session = true; send(202, { qualification_id: "q".repeat(32) }); return; }
        if (url.endsWith("/activate")) { state.active = true; send(200, overview()); return; }
        send(404, { detail: { code: "NOT_FOUND", message: "Nothing changed." } });
      });
      return;
    }
    if (url.endsWith("/api/assistant/admin/models")) { send(200, overview()); return; }
    if (url.endsWith("/api/assistant/admin/models/setup")) { send(200, { providers: { anthropic: provider("anthropic"), openrouter: provider("openrouter") } }); return; }
    if (url.includes("/api/assistant/admin/models/audit")) { send(200, { events: [] }); return; }
    if (url.startsWith("/api/")) { send(404, { detail: { code: "NOT_FOUND", message: "No such model profile." } }); return; }
    response.setHeader("Content-Type", "text/html");
    response.end(`<html><head><meta name="viewport" content="width=device-width, initial-scale=1"><style>${css}</style></head><body><div id="root"></div>
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
  let dialogs = 0;
  try {
    await page.goto(origin);
    const setup = page.getByRole("region", { name: "Choose a model, connect it, qualify it, then activate it" });
    await expect(setup).toBeVisible();
    await expect(setup).not.toContainText(/reconcil|attest|P1/i);

    // 1. Select. 2. Key, then the one-time setup record (no budget to configure or confirm).
    await setup.getByLabel(/Claude Sonnet 5\.5 — Balanced/).check();
    await expect(page.getByTestId("session-strip")).toContainText("Not started (US$5.00 at the first paid action)");
    await setup.getByLabel("Anthropic inference API key").fill("sk-ant-api03-synthetic-test-only");
    await setup.getByRole("button", { name: "Save & test" }).click();
    await expect(setup.getByText("One-time Claude setup")).toBeVisible();
    await setup.getByLabel(/used only for this FYP project/).check();
    await setup.getByLabel("The key will be revoked when the FYP ends.").check();
    await expect(setup.getByText("earlier usage")).toHaveCount(0); // no opening question (P5)
    await setup.getByRole("button", { name: "Enable Claude" }).click();
    await expect(setup.getByRole("button", { name: "Run qualification…" })).toBeEnabled();

    // 3. The free check, then one confirmation for the paid test calls. 4. One to activate.
    await setup.getByRole("button", { name: "Run qualification…" }).click();
    await expect(page.getByTestId("guided-qualify")).toContainText("US$0.19");
    dialogs += 1;
    await page.getByTestId("guided-qualify").getByRole("button", { name: "Run paid test calls" }).click();
    await setup.getByRole("button", { name: "Activate…" }).click();
    dialogs += 1;
    const activate = page.getByTestId("guided-activate");
    await activate.getByRole("checkbox").check();
    await activate.getByRole("button", { name: "Activate" }).click();
    await expect(setup.getByText("Active. Case users can now ask the AI Assistant on an open case.")).toBeVisible();
    await expect(page.getByTestId("session-strip")).toContainText("US$4.85 left of US$5.00");

    expect(dialogs).toBe(2);
    expect(sent.map((item) => `${item.method} ${item.url.replace("/api/assistant/admin/models", "")}`)).toEqual([
      "PUT /credential/anthropic",
      "POST /provider/anthropic/workspace-read",
      "PUT /provider/anthropic",
      "POST /anthropic_claude_sonnet_5_5_medium/connection-test",
      "POST /anthropic_claude_sonnet_5_5_medium/connection-test",
      "POST /anthropic_claude_sonnet_5_5_medium/qualifications",
      "POST /anthropic_claude_sonnet_5_5_medium/activate",
    ]);
    expect(sent[2].body).toMatchObject({ workspace_limit_micro_usd: 5_000_000 });
    expect(sent[2].body).not.toHaveProperty("opening");
    expect(sent[5].body).toEqual({ confirm_paid_calls: 2 });

    // Phone width: no horizontal page scroll.
    await page.setViewportSize({ width: 375, height: 812 });
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(0);
    expect(pageErrors).toEqual([]);
    expect(violations).toEqual([]);
  } finally {
    await new Promise<void>((resolve) => server.close(() => resolve()));
  }
});
