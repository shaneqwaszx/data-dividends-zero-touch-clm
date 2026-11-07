import { expect, test } from "@playwright/test";
import { createBrowserNetworkPolicy, handleBrowserRoute } from "../playwright.config";
import { SAMPLE_CASES, sampleCaseIdFromUrlId } from "../src/pages/mockDashboards/onboardingSample";

// Fixed dashboard sample cases open a read-only case page from the dashboard and the Cases tab.
// By request they are not labelled as sample data, and they never reach the backend.
const isSampleCasePath = (href: string | null) =>
  Boolean(href?.startsWith("/cases/") && sampleCaseIdFromUrlId(href.slice("/cases/".length)));

test("sample cases open read-only from the dashboard and the Cases tab", async ({ page }) => {
  const violations: string[] = [];
  const sampleApiRequests: string[] = [];
  page.on("request", request => {
    const url = new URL(request.url());
    if (url.pathname.startsWith("/api/") && sampleCaseIdFromUrlId(url.pathname.split("/").find(part => part.length === 36) ?? "")) {
      sampleApiRequests.push(url.pathname);
    }
  });
  const policy = createBrowserNetworkPolicy({
    frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!,
    backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false,
  });
  await page.route("**/*", route => handleBrowserRoute(route, policy, violations));
  await page.goto("/");
  await page.getByLabel("User ID").fill("maya-lim");
  await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();

  // Dashboard -> Onboarding -> a sample case.
  await page.getByRole("link", { name: "Dashboard", exact: true }).click();
  await page.locator(".category-card--live").click();
  await expect(page.getByRole("heading", { name: "Onboarding Dashboard" })).toBeVisible();
  await expect(page.locator("main, body").first()).not.toContainText(/\bsample\b/i);
  const caseLinks = page.locator('a[href^="/cases/"]');
  await expect(caseLinks.first()).toBeVisible();
  const hrefs = await caseLinks.evaluateAll(links => links.map(link => link.getAttribute("href")));
  const sampleHref = hrefs.find(isSampleCasePath)!;
  expect(sampleHref).toBeTruthy();
  await page.locator(`a[href="${sampleHref}"]`).first().click();
  await expect(page).toHaveURL(new RegExp(`${sampleHref}$`));
  const casePage = page.locator("section.readonly-case-detail");
  await expect(casePage.getByRole("heading", { name: "Steps" })).toBeVisible();
  await expect(casePage.getByRole("heading", { name: "Blockers" })).toBeVisible();
  await expect(casePage.locator("button")).toHaveCount(0);
  await expect(casePage).not.toContainText(/sample|illustrative|demonstration/i);

  // Back to Cases: sample cases are rows of the same table and follow the search.
  await casePage.getByRole("link", { name: "← Cases" }).click();
  await expect(page.getByRole("heading", { name: "Cases", exact: true })).toBeVisible();
  await page.getByLabel("Search", { exact: true }).fill("Hougang");
  const table = page.getByLabel("Cases table");
  await expect(table.locator("tbody tr")).toHaveCount(1);
  await expect(page.locator("body")).not.toContainText(/\bsample\b/i);
  await table.getByRole("link", { name: "Open" }).click();
  await expect(page.getByRole("heading", { name: "Hougang Pet Supplies Pte. Ltd." })).toBeVisible();
  await expect(casePage).toContainText("Stopped for review");

  // Deep links survive a reload.
  await page.reload();
  await expect(page.getByRole("heading", { name: "Hougang Pet Supplies Pte. Ltd." })).toBeVisible();

  expect(SAMPLE_CASES.length).toBeGreaterThan(0);
  expect(sampleApiRequests).toEqual([]);
  expect(violations).toEqual([]);
});
