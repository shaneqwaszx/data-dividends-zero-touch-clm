import path from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test, type Page } from "@playwright/test";
import {
  createBrowserNetworkPolicy,
  handleBrowserRoute,
  type BrowserNetworkPolicy,
} from "../playwright.config";

const currentDirectory = path.dirname(fileURLToPath(import.meta.url));
const cleanFixture = path.resolve(
  currentDirectory,
  "../../backend/tests/fixtures/uat/clean-company-profile.pdf",
);

function requiredEnvironment(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`The task-owned E2E launcher must provide ${name}`);
  }
  return value;
}

type NetworkGuard = {
  assertNoViolations(): void;
};

async function guardLocalNetwork(
  page: Page,
  policy: BrowserNetworkPolicy,
): Promise<NetworkGuard> {
  const violations: string[] = [];
  await page.route("**/*", async (route) => {
    await handleBrowserRoute(route, policy, violations);
  });
  return {
    assertNoViolations() {
      expect(
        violations,
        "Browser network policy blocked request(s); only sanitized structure follows",
      ).toEqual([]);
    },
  };
}

async function login(page: Page) {
  const ephemeralCredential = requiredEnvironment("CLM_E2E_PASSWORD");
  await page.getByLabel("User ID").fill("maya-lim");
  await page.getByLabel("Password").fill(ephemeralCredential);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
}

test.describe.configure({ mode: "serial" });

let networkGuard: NetworkGuard | undefined;

test.beforeEach(async ({ page }) => {
  const frontendOrigin = requiredEnvironment("PLAYWRIGHT_BASE_URL");
  const policy = createBrowserNetworkPolicy({
    frontendOrigin,
    backendOrigin: requiredEnvironment("CLM_E2E_BACKEND_ORIGIN"),
    // The browser uses Vite's same-origin /api proxy; direct backend access is unnecessary.
    allowDirectBackend: false,
  });
  networkGuard = await guardLocalNetwork(page, policy);
});

test.afterEach(() => {
  networkGuard?.assertNoViolations();
  networkGuard = undefined;
});

test("protected workspace requires a real login before navigation", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Main workspace" })).toHaveCount(0);

  await login(page);
  await page.getByRole("button", { name: "New onboarding" }).click();
  await expect(page.getByRole("heading", { name: "Start onboarding" })).toBeVisible();
});

test("Singapore clean fixture completes the truthful Mock target path", async ({ page }) => {
  await page.goto("/");
  await login(page);
  await page.getByRole("button", { name: "New onboarding" }).click();

  await page.getByLabel("Jurisdiction").selectOption("SG");
  await page.getByLabel("Registration ID / UEN").fill("202400001A");
  await page.locator("#home-document").setInputFiles(cleanFixture);
  await page.getByRole("button", { name: "Create onboarding" }).click();

  await expect(page.getByText("Completed Mock workflow")).toBeVisible({ timeout: 120_000 });
  await expect(page.getByText(/GoldTier Mock/).first()).toBeVisible();
  await expect(page.getByText(/not production approval or Ready-for-Approval/i)).toBeVisible();
  await page.getByRole("button", { name: "Cases" }).click();
  await expect(page.getByRole("heading", { name: "Cases" })).toBeVisible();
  await expect(page.getByText("MOCK_GOLDTIER_SUBMITTED", { exact: true })).toBeVisible();
});
