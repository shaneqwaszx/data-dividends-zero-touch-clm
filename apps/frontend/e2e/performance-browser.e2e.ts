import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createHash } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";
import { createBrowserNetworkPolicy, handleBrowserRoute } from "../playwright.config";

const directory = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(directory, "../../..");
const fixture = path.resolve(directory, "../../backend/tests/fixtures/uat/clean-company-profile.pdf");
const method = createHash("sha256").update(fs.readFileSync(fileURLToPath(import.meta.url))).digest("hex");

async function ready(page: Page) {
  // Eleven business steps over the twelve backend stages; Initial identity always shows (D-123).
  await expect(page.locator(".onboarding-progress__stage-label")).toHaveCount(11);
  await expect(page.getByRole("navigation", { name: "Main workspace" })).toBeVisible();
}

// Methodology revision: the case page now opens while the new case is still processing, so the
// measurement starts only once its document is ingested and its ownership and intelligence evidence
// exist. Observed through the read endpoints (untimed, read-only, finite deadline); results are not
// comparable with earlier method hashes without a controlled comparison.
const METHOD_REVISION = "settled-resource-precondition-v1";
const SETTLE_DEADLINE_MS = 30_000;
const SETTLE_POLL_MS = 250;
// Rows on the first Cases page (apps/frontend/src/caseQueries.ts CASES_PAGE_SIZE, PR #178).
const PORTFOLIO_PAGE_LIMIT = 10;

async function awaitSettledResources(page: Page, casePath: string) {
  const started = Date.now();
  let polls = 0;
  for (;;) {
    polls++;
    const [summary, documents, ownership, intelligence] = await Promise.all([
      page.request.get(`/api/clm/zero-touch${casePath}`),
      page.request.get(`/api/onboarding${casePath}/documents`),
      page.request.get(`/api/onboarding${casePath}/ownership`),
      page.request.get(`/api/clm/zero-touch${casePath}/intelligence`),
    ]);
    const observed = {
      case_status: summary.ok() ? (await summary.json()).status : `HTTP ${summary.status()}`,
      documents: documents.ok() ? (await documents.json() as unknown[]).length : `HTTP ${documents.status()}`,
      ownership: ownership.status(),
      intelligence: intelligence.status(),
    };
    if (typeof observed.documents === "number" && observed.documents >= 1 && observed.ownership === 200 && observed.intelligence === 200) {
      return { ...observed, polls, waited_ms: Date.now() - started };
    }
    if (Date.now() - started >= SETTLE_DEADLINE_MS) {
      throw new Error(`Settled-resource precondition not met within ${SETTLE_DEADLINE_MS} ms after ${polls} polls: ${JSON.stringify(observed)}`);
    }
    await new Promise(resolve => setTimeout(resolve, SETTLE_POLL_MS));
  }
}

async function measure(page: Page, width: number) {
    await page.setViewportSize({ width, height: 900 });
    const frontendOrigin = process.env.PLAYWRIGHT_BASE_URL!;
    const backendOrigin = process.env.CLM_E2E_BACKEND_ORIGIN!;
    const policy = createBrowserNetworkPolicy({ frontendOrigin, backendOrigin, allowDirectBackend: false });
    const violations: string[] = [];
    await page.route("**/*", route => handleBrowserRoute(route, policy, violations));
    let attempts = new Map<object, { endpoint: string; method: string; outcome: string | number }>();
    let targetWrites = 0;
    const sanitize = (value: string) => new URL(value).pathname.replace(/[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}/gi, "{case}");
    page.on("request", request => {
      if (new URL(request.url()).pathname.startsWith("/api/")) attempts.set(request, { endpoint: sanitize(request.url()), method: request.method(), outcome: "PENDING" });
      if (request.method() === "POST" && new URL(request.url()).pathname.endsWith("/target-confirmation")) targetWrites++;
    });
    page.on("response", response => {
      const entry = attempts.get(response.request());
      if (entry) entry.outcome = response.status();
    });
    page.on("requestfailed", request => {
      const entry = attempts.get(request);
      if (entry) entry.outcome = request.failure()?.errorText === "net::ERR_ABORTED" ? "CANCELLED" : "NETWORK_FAILURE";
    });
    await page.goto("/");
    await page.getByLabel("User ID").fill("maya-lim");
    await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await expect(page.getByRole("navigation", { name: "Main workspace" })).toBeVisible();
    await page.getByRole("link", { name: "New onboarding", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Start onboarding", exact: true })).toBeVisible();
    await page.getByLabel("Jurisdiction", { exact: true }).selectOption("SG");
    await page.getByLabel("Company Legal Name", { exact: true }).fill("MERLION CIRCULAR LABS PTE. LTD.");
    await page.getByLabel("Registration ID / UEN", { exact: true }).fill("202400001A");
    await page.locator('input[type="file"]').first().setInputFiles(fixture);
    await page.getByRole("button", { name: "Create onboarding", exact: true }).click();
    await expect(page).toHaveURL(/\/cases\/[0-9a-f-]{36}$/i);
    await ready(page);
    const casePath = new URL(page.url()).pathname;
    // Untimed structure check: Initial identity always shows (D-123), and the backend still
    // reports all twelve authoritative stages.
    await expect(page.locator(".onboarding-progress__stage-label").filter({ hasText: /^Initial identity$/ })).toHaveCount(1);
    expect((await (await page.request.get(`/api/clm/zero-touch${casePath}`)).json()).processing_pipeline).toHaveLength(12);
    const precondition = await awaitSettledResources(page, casePath);
    await page.waitForTimeout(500); // untimed settling, same protocol in both arms
    const samples: object[] = [];
    for (let index = 0; index < 22; index++) {
      for (const kind of ["cold_client_cache", "warm_navigation"]) {
        attempts = new Map();
        await page.evaluate(() => performance.clearResourceTimings());
        const start = performance.now();
        if (kind === "cold_client_cache") {
          await page.reload(); // same authenticated session; resets query cache; routing disables HTTP cache
        } else {
          await page.getByRole("link", { name: "Cases", exact: true }).click();
          await expect(page.getByRole("heading", { name: "Cases", exact: true })).toBeVisible();
          // The Cases tab renders one full first page (CASES_PAGE_SIZE = 10, PR #178) before the warm
          // navigation continues to the same case.
          await expect(page.getByText(`Showing 1–${PORTFOLIO_PAGE_LIMIT}`, { exact: true })).toBeVisible();
          await expect(page.locator("table.case-table tbody tr")).toHaveCount(PORTFOLIO_PAGE_LIMIT);
          await page.locator(`a[href="${casePath}"]`).click();
        }
        await ready(page);
        const elapsed_ms = performance.now() - start;
        await page.waitForTimeout(500); // request accounting tail excluded from UI latency
        const entries = await page.evaluate(() => performance.getEntriesByType("resource")
          .filter(entry => new URL(entry.name).pathname.startsWith("/api/"))
          .map(entry => {
            const value = entry as PerformanceResourceTiming;
            return { endpoint: new URL(value.name).pathname.replace(/[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}/gi, "{case}"), duration_ms: value.duration, decoded_bytes: value.decodedBodySize, transfer_bytes: value.transferSize };
          }));
        const records = [...attempts.values()];
        expect(records.every(item => item.outcome === "CANCELLED" || (typeof item.outcome === "number" && item.outcome >= 200 && item.outcome < 300))).toBe(true);
        expect(entries.length).toBe(records.length);
        const layout = await page.evaluate(() => ({ client: document.body.clientWidth, scroll: document.body.scrollWidth, viewport: document.documentElement.clientWidth }));
        expect(layout.scroll).toBeLessThanOrEqual(layout.client + 1);
        expect(layout.client).toBeLessThanOrEqual(layout.viewport + 1);
        if (index >= 2) samples.push({ kind, elapsed_ms, requests: records.length, completed_requests: records.filter(item => typeof item.outcome === "number").length, cancelled_requests: records.filter(item => item.outcome === "CANCELLED").length, request_records: records, decoded_bytes: entries.reduce((sum, item) => sum + item.decoded_bytes, 0), entries });
      }
    }
    expect(violations).toEqual([]);
    expect(targetWrites).toBe(0);
    expect(samples).toHaveLength(40);
    const raw = path.join(root, ".runtime/performance-optimization");
    fs.mkdirSync(raw, { recursive: true });
    fs.writeFileSync(path.join(raw, `browser-${width}.json`), JSON.stringify({ claim: "DEVELOPMENT_MEASUREMENT", method_sha256: method, method_revision: METHOD_REVISION, precondition, width, seeded_cases: 105, portfolio_page_limit: PORTFOLIO_PAGE_LIMIT, measured_each_kind: 20, warmup_each_kind: 2, assets_cache: "HTTP cache disabled by Playwright routing", cold_scope: "query cache reset by page reload, same authenticated browser/session", warm_scope: "Cases -> same case within same loaded session", accounting_tail_ms: 500, render_work: "not separately instrumented", target_confirmation_requests: targetWrites, samples }, null, 2) + "\n");
 }

test("Performance browser cache measurement width1440", async ({ page }) => measure(page, 1440));
test("Performance browser cache measurement width360", async ({ page }) => measure(page, 360));
