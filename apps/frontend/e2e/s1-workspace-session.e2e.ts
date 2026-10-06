import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test, type Page } from "@playwright/test";
import {
  classifyBrowserRequest,
  createBrowserNetworkPolicy,
  handleBrowserRoute,
} from "../playwright.config";
import { openStage } from "./stage-disclosures";

const fixture = path.resolve(path.dirname(fileURLToPath(import.meta.url)),
  "../../backend/tests/fixtures/uat/clean-company-profile.pdf");
const stageNames = [
  "Case created", "Initial identity", "Jurisdiction", "Existing-customer search",
  "Registry verification", "Document verification", "Data reconciliation", "Ownership & UBO",
  "Risk assessment", "Submission readiness", "GoldTier submission package", "Final review & send",
];
let violations: string[];
let holdCreation: Promise<void> | null;
let failDocuments: boolean;

function requiredEnvironment(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`The task-owned E2E launcher must provide ${name}`);
  return value;
}

async function login(page: Page, userId: string) {
  await page.getByLabel("User ID").fill(userId);
  await page.getByLabel("Password").fill(requiredEnvironment("CLM_E2E_PASSWORD"));
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("navigation", { name: "Main workspace" })).toBeVisible();
}

async function logout(page: Page) {
  await page.locator(".operator-account__button").click();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Sign in", exact: true })).toBeVisible();
  await expect(page).toHaveURL(/\/$/);
}

async function openNew(page: Page) {
  await page.getByRole("link", { name: "New onboarding", exact: true }).click();
  const reset = page.getByRole("button", { name: "Start a new case", exact: true });
  if (await reset.isVisible()) await reset.click();
  await expect(page.getByRole("heading", { name: "Start onboarding", exact: true })).toBeVisible();
}

async function expectBlankDraft(page: Page) {
  await expect(page.getByLabel("Company Legal Name", { exact: true })).toHaveValue("");
  await expect(page.getByLabel("Registration ID / UEN", { exact: true })).toHaveValue("");
  await expect(page.getByLabel("Jurisdiction", { exact: true })).toHaveValue("");
  await expect(page.getByLabel("Case priority", { exact: true })).toHaveValue("");
  await expect(page.getByText(/file\(s\).*selected/)).toHaveCount(0);
}

async function expectContained(page: Page) {
  const widths = await page.evaluate(() => ({
    actual: document.body.scrollWidth, available: document.documentElement.clientWidth,
  }));
  expect(widths.actual).toBeLessThanOrEqual(widths.available + 1);
}

test.beforeEach(async ({ page }) => {
  violations = [];
  holdCreation = null;
  failDocuments = false;
  const policy = createBrowserNetworkPolicy({
    frontendOrigin: requiredEnvironment("PLAYWRIGHT_BASE_URL"),
    backendOrigin: requiredEnvironment("CLM_E2E_BACKEND_ORIGIN"),
    allowDirectBackend: false,
  });
  await page.route("**/*", async (route) => {
    const request = route.request();
    const decision = classifyBrowserRequest(request.url(), policy, request.resourceType());
    if (decision.classification === "OWNED_LOOPBACK") {
      const pathname = new URL(request.url()).pathname;
      if (request.method() === "POST" && pathname === "/api/clm/zero-touch/cases") {
        await holdCreation;
      }
      if (failDocuments && request.method() === "GET"
        && /^\/api\/onboarding\/cases\/[^/]+\/documents$/.test(pathname)) {
        await route.fulfill({ status: 503, contentType: "application/json",
          body: JSON.stringify({ detail: "Synthetic document query unavailable" }) });
        return;
      }
    }
    await handleBrowserRoute(route, policy, violations);
  });
});
test.afterEach(() => expect(violations).toEqual([]));

test("S1 blank login and onboarding forms retain readable team ownership at three widths", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByLabel("User ID")).toHaveValue("");
  await expect(page.getByLabel("User ID")).not.toHaveAttribute("placeholder", "maya-lim");
  await expect(page.getByLabel("Password")).toHaveValue("");
  await login(page, "ethan-tan");
  await openNew(page);
  for (const width of [320, 720, 1280]) {
    await page.setViewportSize({ width, height: 1000 });
    await expectBlankDraft(page);
    await expect(page.getByLabel("Owning team *", { exact: true })).toHaveCount(0);
    await expect(page.getByText("Your assigned team owns this case.", { exact: true })).toBeVisible();
    const team = page.getByText("Your assigned team owns this case.", { exact: true }).locator("..");
    const separation = await team.evaluate((element) => {
      const label = element.querySelector(".control-label")!;
      const value = element.querySelector("strong")!;
      return value.getBoundingClientRect().top - label.getBoundingClientRect().bottom;
    });
    expect(separation).toBeGreaterThanOrEqual(4);
    await expectContained(page);
  }
  await logout(page);
  await login(page, "olivia-koh");
  await openNew(page);
  const selector = page.getByLabel("Owning team *", { exact: true });
  await expect(selector).toHaveValue("");
  await expect(selector.locator("xpath=ancestor::div[contains(@class,'card')][1]")
    .getByLabel("Registration ID / UEN", { exact: true })).toBeVisible();
});

test("S1 executing workspace is inert, all 12 stages inspect, failed documents stay truthful, and reset clears drafts", async ({ page }) => {
  await page.goto("/");
  await login(page, "olivia-koh");
  await openNew(page);
  await page.getByLabel("Jurisdiction", { exact: true }).selectOption("SG");
  await page.getByLabel("Company Legal Name", { exact: true }).fill("MERLION CIRCULAR LABS PTE. LTD.");
  await page.getByLabel("Registration ID / UEN", { exact: true }).fill("202400001A");
  await page.getByLabel("Case priority", { exact: true }).selectOption("10");
  await page.getByLabel("Owning team *", { exact: true }).selectOption("TEAM_A");
  await page.locator('input[type="file"]').first().setInputFiles(fixture);
  let releaseCreation!: () => void;
  holdCreation = new Promise<void>((resolve) => { releaseCreation = resolve; });
  try {
    await page.getByRole("button", { name: "Create onboarding", exact: true }).click();
    const overlay = page.locator(".processing-workspace__overlay");
    await expect(overlay).toBeVisible();
    await expect(overlay).toHaveAttribute("aria-live", "polite");
    await expect(page.locator(".processing-workspace")).toHaveAttribute("aria-busy", "true");
    await expect(page.locator(".processing-workspace__content")).toHaveAttribute("inert", "");
    const navigation = page.getByRole("navigation", { name: "Main workspace" });
    expect(await navigation.evaluate((element) => element.closest("[inert]") === null)).toBe(true);
    const dashboard = navigation.getByRole("link", { name: "Dashboard", exact: true });
    await dashboard.focus();
    await expect(dashboard).toBeFocused();
    await page.keyboard.press("Tab");
    expect(await page.evaluate(() => document.activeElement?.closest("[inert]") === null)).toBe(true);
  } finally {
    releaseCreation();
    holdCreation = null;
  }
  await expect(page.getByRole("button", { name: "Open full case", exact: true })).toBeEnabled();
  await expect(page.locator(".processing-workspace__overlay")).toHaveCount(0);
  await expect(page.locator(".processing-workspace__content[inert]")).toHaveCount(0);
  await page.getByRole("button", { name: "Open full case", exact: true }).click();
  const labels = page.locator(".onboarding-progress__stages .onboarding-progress__stage-label");
  await expect(labels).toHaveText(stageNames);
  for (const name of stageNames) {
    const button = page.getByRole("button", { name: `Open details for ${name}`, exact: true });
    await button.click();
    await expect(page.getByRole("region", { name: `${name} details`, exact: true })).toBeVisible();
  }
  for (const width of [320, 720, 1280]) {
    await page.setViewportSize({ width, height: 1000 });
    await page.getByRole("button", { name: "Open details for Case created", exact: true }).click();
    await expectContained(page);
  }
  const caseUrl = page.url();
  await page.getByRole("link", { name: "New onboarding", exact: true }).click();
  await page.getByRole("button", { name: "Start a new case", exact: true }).click();
  await expectBlankDraft(page);
  await expect(page.getByLabel("Owning team *", { exact: true })).toHaveValue("");
  failDocuments = true;
  await page.goto(caseUrl);
  await expect(page).toHaveURL(caseUrl);
  await openStage(page, "Document verification");
  const documents = page.locator(".document-evidence-panel");
  await expect(documents).toContainText("Document information could not be loaded");
  await expect(documents).not.toContainText("No document uploaded");
  await page.getByRole("link", { name: "New onboarding", exact: true }).click();
  await expectBlankDraft(page);
  await expect(page.getByLabel("Owning team *", { exact: true })).toHaveValue("");
});

test("S1 logout and interactive role changes start at each role's normal landing and clear onboarding drafts", async ({ page }) => {
  await page.goto("/");
  await login(page, "hr-admin");
  await page.getByRole("link", { name: "GoldTier Sandbox", exact: true }).click();
  await logout(page);
  await login(page, "olivia-koh");
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByText("Page unavailable", { exact: true })).toHaveCount(0);
  await page.getByRole("link", { name: "Cases", exact: true }).click();
  await logout(page);
  await login(page, "hr-admin");
  await expect(page).toHaveURL(/\/admin\/users$/);
  await expect(page.getByText("Page unavailable", { exact: true })).toHaveCount(0);
  await logout(page);
  await login(page, "ethan-tan");
  await openNew(page);
  await page.getByLabel("Company Legal Name", { exact: true }).fill("SYNTHETIC UNSUBMITTED DRAFT");
  await page.getByLabel("Registration ID / UEN", { exact: true }).fill("202400001A");
  await page.getByLabel("Case priority", { exact: true }).selectOption("10");
  await logout(page);
  await login(page, "olivia-koh");
  await expect(page).toHaveURL(/\/dashboard$/);
  await openNew(page);
  await expectBlankDraft(page);
  await expect(page.getByLabel("Owning team *", { exact: true })).toHaveValue("");
});

test("S1 case creation date controls describe Singapore days and reject a reversed range", async ({ page }) => {
  await page.goto("/");
  await login(page, "ethan-tan");
  await page.getByRole("link", { name: "Cases", exact: true }).click();
  await expect(page.getByText("Creation dates include both selected days in Singapore (Asia/Singapore, UTC+08:00).", { exact: true })).toBeVisible();
  const from = page.getByLabel("Created from", { exact: true });
  const to = page.getByLabel("Created to", { exact: true });
  await from.fill("2026-09-29");
  const filtered = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return response.request().method() === "GET" && url.pathname === "/api/clm/zero-touch/case-portfolio"
      && url.searchParams.get("created_from") === "2026-09-29"
      && url.searchParams.get("created_to") === "2026-10-04";
  });
  await to.fill("2026-10-04");
  expect((await filtered).status()).toBe(200);
  await expect(from).toHaveAttribute("max", "2026-10-04");
  await expect(to).toHaveAttribute("min", "2026-09-29");
  await from.fill("2026-10-05");
  await expect(page.getByRole("alert")).toContainText("Created from must be on or before Created to.");
  await from.fill("");
  await to.fill("");
  await expect(page.getByRole("alert")).toHaveCount(0);
  await page.getByRole("link", { name: "Onboarded", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Onboarded", exact: true })).toBeVisible();
  await page.getByLabel("Created from", { exact: true }).fill("2026-09-29");
  const completed = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return response.request().method() === "GET" && url.pathname === "/api/clm/zero-touch/cases"
      && url.searchParams.get("status") === "COMPLETED"
      && url.searchParams.get("created_from") === "2026-09-29"
      && url.searchParams.get("created_to") === "2026-10-04";
  }, { timeout: 15_000 });
  await page.getByLabel("Created to", { exact: true }).fill("2026-10-04");
  expect((await completed).status()).toBe(200);
});
