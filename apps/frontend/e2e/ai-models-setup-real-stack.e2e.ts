import { spawn, spawnSync, type ChildProcess } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { createServer } from "node:net";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test, type Locator, type Page } from "@playwright/test";
import { createBrowserNetworkPolicy, handleBrowserRoute } from "../playwright.config";
// @ts-expect-error A plain ESM build helper shared with manual smoke runs (no declarations).
import { buildAiModelsPage } from "./support/ai-models-page.mjs";

// D-118 usability: the real AI Models page in real Chromium against the REAL assistant service
// (model admin, setup view, session stores, the qualification job) started by
// apps/assistant/tests/ui_stack.py with mock Anthropic and OpenRouter APIs, the assistant
// tests' fake CLM backend and a new disposable data folder per stack. No network, no paid
// call, no real key, never the owner's stores. Evidence class: Local. Windows and POSIX: the
// stack is started with the runner's own Python (CLM_E2E_PYTHON) and stopped as a process tree.

const FRONTEND = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const ASSISTANT = path.resolve(FRONTEND, "..", "assistant");
// Built at run time so no key-shaped literal is in the repository (test sentinels only).
const CLAUDE_KEY = "sk-" + "ant-" + "api03-" + "RuntimeSentinel".repeat(3);
const OPENROUTER_KEY = "sk-" + "or-" + "v1-" + "synthetic-ui-stack-key-0001";

interface Stack { origin: string; dataDir: string; stop: () => void }

async function freePort(): Promise<number> {
  return await new Promise((resolve, reject) => {
    const server = createServer();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      const port = typeof address === "object" && address ? address.port : 0;
      server.close(() => resolve(port));
    });
  });
}

function stopTree(child: ChildProcess): void {
  if (child.pid === undefined || child.exitCode !== null) return;
  if (process.platform === "win32") {
    // A virtual-environment python.exe starts the real interpreter as a child: end the tree.
    spawnSync("taskkill", ["/pid", String(child.pid), "/T", "/F"], { stdio: "ignore" });
  } else {
    try { process.kill(-child.pid, "SIGKILL"); } catch { child.kill("SIGKILL"); }
  }
}

async function startStack(staticDir: string, dataDir: string, options: { scenario?: string; set?: Record<string, string | number> } = {}): Promise<Stack> {
  const python = process.env.CLM_E2E_PYTHON || (process.platform === "win32" ? "python" : "python3");
  const port = await freePort();
  const args = ["-m", "tests.ui_stack", "--data-dir", dataDir, "--static", staticDir, "--port", String(port)];
  if (options.scenario) args.push("--scenario", options.scenario);
  for (const [name, value] of Object.entries(options.set ?? {})) args.push("--set", `${name}=${value}`);
  const env: Record<string, string> = {};
  for (const name of ["PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP", "TMPDIR", "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "LANG"]) {
    const value = process.env[name];
    if (value) env[name] = value;
  }
  const child = spawn(python, args, {
    cwd: ASSISTANT,
    env: { ...env, PYTHONPATH: ASSISTANT, PYTHONIOENCODING: "utf-8", PYTHONDONTWRITEBYTECODE: "1" },
    stdio: ["ignore", "pipe", "pipe"],
    detached: process.platform !== "win32",
  });
  let output = "";
  child.stdout?.on("data", (part: Buffer) => { output += part.toString(); });
  child.stderr?.on("data", (part: Buffer) => { output += part.toString(); });
  const origin = `http://127.0.0.1:${port}`;
  const deadline = Date.now() + 60_000;
  for (;;) {
    if (child.exitCode !== null) throw new Error(`ui_stack exited early (${child.exitCode}): ${output.slice(-2000)}`);
    try {
      const response = await fetch(`${origin}/api/assistant/admin/models/setup`);
      if (response.ok) break;
    } catch { /* not listening yet */ }
    if (Date.now() > deadline) { stopTree(child); throw new Error(`ui_stack not ready: ${output.slice(-2000)}`); }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  return { origin, dataDir, stop: () => stopTree(child) };
}

async function open(page: Page, stack: Stack, violations: string[]): Promise<Locator> {
  const policy = createBrowserNetworkPolicy({ frontendOrigin: stack.origin,
    backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false });
  await page.unrouteAll({ behavior: "ignoreErrors" });
  await page.route("**/*", (route) => handleBrowserRoute(route, policy, violations));
  await page.goto(stack.origin);
  const setup = page.getByRole("region", { name: "Choose a model, connect it, qualify it, then activate it" });
  await expect(setup).toBeVisible();
  return setup;
}

const step = (setup: Locator, title: string) => setup.locator("li.guided-step").filter({ has: setup.page().getByRole("heading", { name: title, exact: true }) });

async function saveKey(setup: Locator, label: string, key: string): Promise<void> {
  await setup.getByLabel(label).fill(key);
  await setup.getByRole("button", { name: "Save & test" }).click();
}

async function enableClaude(setup: Locator, button = "Enable Claude"): Promise<void> {
  await setup.getByLabel(/used only for this FYP project/).check();
  await setup.getByLabel("The key will be revoked when the FYP ends.").check();
  await setup.getByRole("button", { name: button }).click();
  await expect(setup.getByTestId("guided-connection")).toHaveText("Connection check passed.");
}

async function setAllowance(setup: Locator, amount: string): Promise<void> {
  await setup.getByRole("button", { name: /Use a smaller amount|Change the allowance/ }).click();
  await setup.getByLabel("US$", { exact: true }).fill(amount);
  await setup.getByRole("button", { name: "Save", exact: true }).click();
  await expect(setup.getByText(`Session allowance US$${amount}`)).toBeVisible();
}

async function qualifyAndActivate(page: Page, setup: Locator, calls = 2): Promise<void> {
  await setup.getByRole("button", { name: "Run qualification…" }).click();
  const dialog = page.getByTestId("guided-qualify");
  await expect(dialog.getByRole("heading", { name: `Run ${calls} paid test calls?` })).toBeVisible();
  await expect(dialog).not.toContainText(/no room|at most —/);
  await expect(dialog).toContainText(/reserve at most US\$\d+\.\d\d/);
  await dialog.getByRole("button", { name: "Run paid test calls" }).click();
  await expect(step(setup, "Run qualification")).toContainText("Done", { timeout: 30_000 });
  await setup.getByRole("button", { name: "Activate…" }).click();
  const activate = page.getByTestId("guided-activate");
  await activate.getByRole("checkbox").check();
  await activate.getByRole("button", { name: "Activate", exact: true }).click();
  await expect(setup.getByText("Active. Case users can now ask the AI Assistant on an open case.")).toBeVisible();
}

const sha256 = (file: string) => createHash("sha256").update(readFileSync(file)).digest("hex");

test.describe("D-118 Set up AI on the real assistant service (mock providers)", () => {
  let staticDir = "";
  const stacks: Stack[] = [];
  const folders: string[] = [];
  const violations: string[] = [];

  test.beforeEach(async ({ page }) => {
    test.setTimeout(150_000);
    page.setDefaultTimeout(15_000);
    staticDir = mkdtempSync(path.join(os.tmpdir(), "clm-ai-page-"));
    folders.push(staticDir);
    await buildAiModelsPage(staticDir);
    violations.length = 0;
  });

  test.afterEach(() => {
    for (const stack of stacks.splice(0)) stack.stop();
    for (const folder of folders.splice(0)) rmSync(folder, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
    expect(violations).toEqual([]);
  });

  const dataDir = () => { const dir = mkdtempSync(path.join(os.tmpdir(), "clm-ui-stack-")); folders.push(dir); return dir; };
  const start = async (dir: string, options?: Parameters<typeof startStack>[2]) => {
    const stack = await startStack(staticDir, dir, options); stacks.push(stack); return stack;
  };

  test("A, E and H: a fresh Claude set-up qualifies within a deliberate US$1.00 session and survives a restart", async ({ page }) => {
    const dir = dataDir();
    // The example file's blank question list and count 0: the approved two calls apply.
    let stack = await start(dir, { set: { local_api_test_qualification_questions: "", local_api_test_qualification_count: 0 } });
    let setup = await open(page, stack, violations);
    await expect(setup).not.toContainText(/reconcil|attest|P1\b/i);
    await setup.getByLabel(/Claude Sonnet 5\.5 — Fast/).check();
    await saveKey(setup, "Anthropic inference API key", CLAUDE_KEY);
    await expect(setup.getByText("One-time Claude setup")).toBeVisible();
    await enableClaude(setup);
    await expect(setup.getByTestId("guided-cost")).toContainText(/Qualification makes 2 paid calls, reserving at most US\$0\.\d\d/);
    await setAllowance(setup, "1.00");
    await setup.getByRole("button", { name: "Run qualification…" }).click();
    const dialog = page.getByTestId("guided-qualify");
    await expect(dialog.getByTestId("guided-limits")).toContainText("Session allowanceUS$1.00 left");
    await dialog.getByRole("button", { name: "Cancel" }).click();
    await qualifyAndActivate(page, setup);
    await expect(page.getByTestId("session-strip")).toContainText(/left of US\$1\.00/);

    // H: restart on the same data folder. The stores, the allowance and the activation stay;
    // the HR key does not (memory only), so the free check refuses until it is entered again.
    stacks.splice(0).forEach((item) => item.stop());
    stack = await start(dir);
    setup = await open(page, stack, violations);
    await setup.getByLabel(/Claude Sonnet 5\.5 — Fast/).check();
    await expect(page.getByTestId("session-strip")).toContainText(/left of US\$1\.00/);
    await expect(setup.getByLabel(/Claude Sonnet 5\.5 — Fast/)).toBeChecked();
    await expect(setup.getByText("Active. Case users can now ask the AI Assistant on an open case.")).toBeVisible();
    await setup.getByRole("button", { name: "Test again" }).click();
    await expect(setup.getByRole("alert").first()).toBeVisible();
    await expect(page.getByTestId("guided-qualify")).toHaveCount(0);
    await saveKey(setup, "Anthropic inference API key", CLAUDE_KEY);
    await expect(setup.getByText("Key saved for this session (never stored in the browser). The connection check passed.")).toBeVisible();
  });

  test("B: an enablement record from before D-118 creates its session store from the page", async ({ page }) => {
    const stack = await start(dataDir(), { scenario: "claude-existing-record" });
    const setup = await open(page, stack, violations);
    await setup.getByLabel(/Claude Sonnet 5\.5 — Fast/).check();
    await saveKey(setup, "Anthropic inference API key", CLAUDE_KEY);
    await expect(setup.getByText("Finish Claude setup (creates its session store)")).toBeVisible();
    await enableClaude(setup, "Confirm and create the session store");
    await expect(page.getByTestId("session-strip")).toContainText("Not started (US$5.00 at the first paid action)");
    await qualifyAndActivate(page, setup);
  });

  test("C: a fresh GPT-OSS set-up creates its store at the first check and qualifies", async ({ page }) => {
    const stack = await start(dataDir());
    const setup = await open(page, stack, violations);
    await setup.getByLabel(/GPT-OSS 120B — Balanced/).check();
    await saveKey(setup, "OpenRouter API key", OPENROUTER_KEY);
    await expect(setup.getByText("Key saved for this session (never stored in the browser). The connection check passed.")).toBeVisible();
    await expect(setup.getByTestId("guided-cost")).toContainText("Qualification makes 2 paid calls");
    await qualifyAndActivate(page, setup);
  });

  test("D: existing GPT-OSS history (an earlier-design ledger) is kept untouched while a new session store is used", async ({ page }) => {
    const dir = dataDir();
    const stack = await start(dir, { scenario: "gptoss-existing-history" });
    const legacy = path.join(dir, "budget", "ledger.sqlite3");
    const before = sha256(legacy);
    const setup = await open(page, stack, violations);
    await setup.getByLabel(/GPT-OSS 120B — Balanced/).check();
    await saveKey(setup, "OpenRouter API key", OPENROUTER_KEY);
    await qualifyAndActivate(page, setup);
    expect(sha256(legacy)).toBe(before);
  });

  test("F: a genuine session or daily shortfall is named, and nothing paid can start", async ({ page }) => {
    let stack = await start(dataDir());
    let setup = await open(page, stack, violations);
    await setup.getByLabel(/Claude Sonnet 5\.5 — Fast/).check();
    await saveKey(setup, "Anthropic inference API key", CLAUDE_KEY);
    await enableClaude(setup);
    await setAllowance(setup, "0.15");
    await setup.getByRole("button", { name: "Run qualification…" }).click();
    let dialog = page.getByTestId("guided-qualify");
    await expect(dialog).toContainText("This session's allowance has US$0.15 left");
    await expect(dialog.getByTestId("guided-limits")).toContainText("Session allowanceUS$0.15 left (too little)");
    await expect(dialog.getByRole("button", { name: "Run paid test calls" })).toBeDisabled();
    await dialog.getByRole("button", { name: "Cancel" }).click();

    stacks.splice(0).forEach((item) => item.stop());
    stack = await start(dataDir(), { set: { anthropic_daily_cap_micro_usd: 150_000 } });
    setup = await open(page, stack, violations);
    await setup.getByLabel(/Claude Sonnet 5\.5 — Fast/).check();
    await saveKey(setup, "Anthropic inference API key", CLAUDE_KEY);
    await enableClaude(setup);
    await setup.getByRole("button", { name: "Run qualification…" }).click();
    dialog = page.getByTestId("guided-qualify");
    await expect(dialog).toContainText("Today's limit has US$0.15 left");
    await expect(dialog.getByTestId("guided-limits")).toContainText("Session allowanceUS$5.00 left");
    await expect(dialog.getByRole("button", { name: "Run paid test calls" })).toBeDisabled();
  });

  test("G: an inconsistent question list is named as the owner's setting, never as a budget problem", async ({ page }) => {
    const stack = await start(dataDir(), { set: { local_api_test_qualification_questions: "P01#1", local_api_test_qualification_count: 2 } });
    const setup = await open(page, stack, violations);
    await setup.getByLabel(/Claude Sonnet 5\.5 — Fast/).check();
    await saveKey(setup, "Anthropic inference API key", CLAUDE_KEY);
    await enableClaude(setup);
    const blocker = setup.getByTestId("guided-qualify-blocker");
    await expect(blocker).toContainText("AI_ASSISTANT_LOCAL_API_TEST_QUALIFICATION_QUESTIONS");
    await expect(blocker).not.toContainText(/no room|insufficient|allowance/i);
    await expect(setup.getByRole("button", { name: "Run qualification…" })).toBeDisabled();
  });
});
