import path from "node:path";
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { expect, test, type Page, type TestInfo } from "@playwright/test";
import { openStage } from "./stage-disclosures";
import { reviewSourceChoices } from "./blocker-decisions";
import { createBrowserNetworkPolicy, handleBrowserRoute, retainedEvidencePath } from "../playwright.config";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const fixtures = path.join(root, "apps/backend/tests/fixtures/uat");
let requests: string[];
let violations: string[];

test.beforeEach(async ({ page }) => {
  requests = []; violations = [];
  const policy = createBrowserNetworkPolicy({
    frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!,
    backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false,
  });
  await page.route("**/*", (route) => handleBrowserRoute(route, policy, violations));
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.pathname.startsWith("/api/")) requests.push(`${request.method()} ${url.pathname}`);
  });
});
test.afterEach(() => expect(violations).toEqual([]));

async function capture(page: Page, info: TestInfo, milestone: string) {
  const evidence = retainedEvidencePath("zero-touch");
  mkdirSync(evidence, { recursive: true });
  const filename = path.join(evidence, `${info.title.replaceAll(/[^A-Za-z0-9]/g, "-")}-${milestone}.png`);
  await page.screenshot({ path: filename, fullPage: true });
  await page.screenshot({ path: filename.replace(".png", "-viewport.png") });
  console.log("ZERO_TOUCH_SCREENSHOT", JSON.stringify({ milestone, path: filename }));
}
async function summary(page: Page, caseId: string) {
  const response = await page.request.get(`/api/clm/zero-touch/cases/${caseId}`);
  expect(response.status()).toBe(200);
  return response.json();
}
async function create(page: Page, garden: boolean, conflict = false) {
  await page.goto("/");
  await page.getByLabel("User ID").fill("maya-lim");
  await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("link", { name: "New onboarding", exact: true }).click();
  await page.getByLabel("Jurisdiction", { exact: true }).selectOption("SG");
  await page.getByLabel("Company Legal Name", { exact: true }).fill(garden ? "GARDEN BUSINESS" : "MERLION CIRCULAR LABS PTE. LTD.");
  await page.getByLabel("Registration ID / UEN").fill(garden ? "11111999A" : "202400001A");
  const file = garden ? `garden-business-${conflict ? "conflicting" : "clean"}-onboarding-profile.pdf` : "clean-company-profile.pdf";
  await page.locator("#home-document").setInputFiles(path.join(fixtures, file));
  if (!garden) {
    // Supply the explicit complete-evidence Mock fixture as normal business input
    // before Start. Every request uses the normal authenticated owner; no state override.
    await page.route("**/api/clm/zero-touch/cases", async (route) => {
      if (route.request().method() !== "POST") return route.fallback();
      const response = await route.fetch();
      expect(response.status()).toBe(201);
      const created = await response.json();
      const headers = route.request().headers();
      const bound = await page.request.put(`/api/clm/zero-touch/cases/${created.case.case_id}/target-classification`, {
        headers: { "X-CSRF-Token": headers["x-csrf-token"], "Origin": process.env.PLAYWRIGHT_BASE_URL! },
        data: { kyc_customer_type: "Company - Private", client_segment: "Corporate",
          expected_automation_version: created.version, expected_case_event_count: created.case.events.length },
      });
      expect(bound.status()).toBe(200);
      await route.fulfill({ response });
    });
  }
  await page.getByRole("button", { name: "Create onboarding" }).click();
  await expect(page).toHaveURL(/\/new-onboarding\/[0-9a-f-]{36}$/i);
  const caseId = page.url().split("/").at(-1)!;
  await expect.poll(async () => (await summary(page, caseId)).status).toBe("WAITING_FOR_REVIEW");
  await page.getByRole("button", { name: "Open full case" }).click();
  await expect(page).toHaveURL(`/cases/${caseId}`);
  await expect(page.locator(".document-card:not(.document-card--history)")).toHaveCount(1);
  return caseId;
}

async function classification(page: Page) {
  await openStage(page, "GoldTier Details & Status");
  await page.getByLabel("KYC customer type", { exact: true }).selectOption("Company - Private");
  await page.getByLabel("Client segment", { exact: true }).selectOption("Corporate");
  const response = page.waitForResponse((response) => response.request().method() === "PUT"
    && response.url().endsWith("/target-classification"));
  await page.getByRole("button", { name: "Save target classification" }).click();
  expect((await response).status()).toBe(200);
  await expect(page.getByRole("button", { name: "Save target classification" })).toBeEnabled();
}

async function boundedMutation(page: Page, info: TestInfo, suffix: string, action: () => Promise<void>, milestone: string) {
  const before = requests.length;
  let release!: () => void;
  let arrived!: () => void;
  const held = new Promise<void>((resolve) => { release = resolve; });
  const ready = new Promise<void>((resolve) => { arrived = resolve; });
  const pattern = `**/*${suffix}`;
  await page.route(pattern, async (route) => {
    if (!["POST", "PUT"].includes(route.request().method())) return route.fallback();
    const response = await route.fetch();
    expect(response.status()).toBe(200);
    arrived();
    await held;
    await route.fulfill({ response });
  });
  try {
    const performed = action();
    await Promise.race([ready, performed.then(() => ready)]);
    await capture(page, info, `${milestone}-during`);
    release();
    await performed;
    await expect(page.getByRole("status").filter({ hasText: /Saving|Submitting|Recording/ }).first()).toHaveCount(0);
  } finally {
    release();
    await page.unroute(pattern);
  }
  return () => {
    const calls = requests.slice(before);
    console.log("ZERO_TOUCH_REQUESTS", JSON.stringify({ action: milestone, requests: calls,
      mutation_count: calls.filter((call) => /^(POST|PUT) /.test(call)).length, external_calls: 0 }));
    expect(calls.filter((call) => /^(POST|PUT) /.test(call))).toHaveLength(1);
    expect(calls.length).toBeLessThanOrEqual(10);
  };
}

test("Zero-touch Golden STP normal UI has zero exception interventions", async ({ page }, info) => {
  const caseId = await create(page, false);
  await capture(page, info, "before");
  await expect(page.locator(".intervention-card")).toHaveCount(0);
  await expect(page.getByRole("button", { name: /^Accept .* suggestion$/ })).toHaveCount(0);
  await expect(page.locator(".document-field .tag", { hasText: "AUTO CONFIRMED" })).toHaveCount(4);
  expect((await summary(page, caseId)).metrics.human_interventions).toBe(0);
  const ready = await summary(page, caseId);
  const search = ready.processing_pipeline.find((item: any) => item.node_id === "GOLDTIER_SEARCH");
  expect(search.status).toBe("COMPLETE");
  expect(search.safe_result).toBe("No existing customer found. Continuing as a new customer.");
  expect(ready.active_exceptions.some((item: any) => item.stage === "GOLDTIER_SEARCH")).toBe(false);
  expect(ready.target_operations.find((item: any) => item.operation === "AMEND").status).toBe("NOT_ATTEMPTED");
  await openStage(page, "Historical / resolved issues");
  await page.getByRole("button", { name: "Show processing details", exact: true }).click();
  await expect(page.getByText("No existing customer found. Continuing as a new customer.", { exact: true }).first()).toBeVisible();
  expect(ready.target_classification.kyc_customer_type.selected_value).toBe("Company - Private");
  expect(ready.target_classification.client_segment.selected_value).toBe("Corporate");
  const measure = await boundedMutation(page, info, "/target-confirmation", async () => {
    await page.getByRole("button", { name: "Confirm and send to Mock GoldTier" }).click();
  }, "confirmation");
  await openStage(page, "GoldTier Details & Status");
  await expect(page.getByText("Completed POC workflow", { exact: true })).toBeVisible();
  await expect(page.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "100");
  await expect(page.getByRole("progressbar")).toHaveAttribute("aria-valuemax", "100");
  await expect(page.getByRole("progressbar")).toHaveAttribute("aria-valuetext", "100% — reviewed POC submission complete; retained target outcome remains authoritative.");
  const completed = await summary(page, caseId);
  expect(completed.status).toBe("COMPLETED");
  expect(completed.metrics.human_interventions).toBe(0);
  expect(completed.timeline.filter((event: any) => event.event_type === "TARGET_DISPATCH_CONFIRMED")).toHaveLength(1);
  await capture(page, info, "after"); measure();
  expect(requests.some((request) => request.includes("/api/demo/"))).toBe(false);
});

for (const conflict of [false, true]) {
  test(`Zero-touch Garden ${conflict ? "conflict" : "clean"} exception automatically resumes`, { tag: "@garden-protocol" }, async ({ page }, info) => {
    const caseId = await create(page, true, conflict);
    await capture(page, info, "before");
    if (conflict) {
      await openStage(page, "Document verification");
      await page.getByLabel("Decision group", { exact: true }).selectOption("source");
      await expect(page.locator('input[data-reconciliation-field][value="KEEP_REGISTRY_VALUE"]')).toHaveCount(4);
      const measure = await boundedMutation(page, info, "/review-decisions", async () => {
        await reviewSourceChoices(page);
      }, "conflict-group");
      await expect(page.locator("input[data-reconciliation-field]")).toHaveCount(0);
      measure();
    } else {
      await expect(page.locator(".document-field .tag", { hasText: "AUTO CONFIRMED" })).toHaveCount(4);
      await expect(page.getByRole("button", { name: /^Accept .* suggestion$/ })).toHaveCount(0);
      expect((await summary(page, caseId)).metrics.human_interventions).toBe(0);
    }
    await classification(page);
    const current = await summary(page, caseId);
    expect(current.active_exceptions.map((item: any) => item.blocker_code)).toEqual(["TARGET_CONFIRMATION_REQUIRED"]);
    const owner = await (await page.request.get(`/api/onboarding/cases/${caseId}/ownership`)).json();
    expect(owner.state).toBe("ANALYZED");
    expect(owner.source_classification).toBe("OFFICIAL_MOCK_PLUS_LOCAL_SUPPLEMENT");
    expect(owner.manual_review_receipt).toBeNull();
    expect(owner.relationships.every((edge: any) => edge.provenance.provider === "LOCAL_SYNTHETIC_SUPPLEMENT"
      && edge.provenance.environment === "LOCAL")).toBe(true);
    expect(owner.candidates.find((item: any) => item.party.display_name === "ABCD123").aggregated_ownership_percent).toMatch(/^51\.136363750*$/);
    expect(current.case.registry_acquisition.ownership_parties).toEqual([]);
    await expect(page.getByRole("button", { name: "Add structured ownership details", exact: true })).toHaveCount(0);
    await openStage(page, "Final review & send");
    await expect(page.getByRole("button", { name: "Confirm and send to Mock GoldTier" })).toBeEnabled();
    await capture(page, info, "after");

    expect(requests.some((request) => request.includes("/api/demo/"))).toBe(false);
  });
}
