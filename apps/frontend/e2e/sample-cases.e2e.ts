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
  const casePage = page.locator(".readonly-case-detail");
  // Same layout as a live case: Pipeline rail, Onboarding progress and one section per step.
  await expect(casePage.getByRole("heading", { name: "Onboarding progress" })).toBeVisible();
  await expect(casePage.getByLabel("Attention required")).toBeVisible();
  await expect(casePage.getByRole("heading", { name: "Steps" })).toBeVisible();
  await expect(casePage.getByRole("heading", { name: "Blockers" })).toBeVisible();
  // Buttons only open steps and sections or expand blockers; there are no case actions.
  const buttonNames = await casePage.locator("button").evaluateAll(buttons => buttons
    .filter(button => !button.matches(".stage-disclosure > h2 > button"))
    .map(button => button.getAttribute("aria-label") ?? button.textContent ?? ""));
  expect(buttonNames.length).toBeGreaterThan(0);
  for (const name of buttonNames) {
    expect(name).toMatch(/^(Open details for |Open case stage details$|Show all issues$|Hide all issues$|\d+ blockers?$|\d+ items?$|Blocker: )/);
  }
  await expect(casePage).not.toContainText(/sample|illustrative|demonstration/i);

  // Back to Cases: sample cases are rows of the same table and follow the search.
  await casePage.getByRole("link", { name: "← Back to Cases" }).click();
  await expect(page.getByRole("heading", { name: "Cases", exact: true })).toBeVisible();
  await page.getByLabel("Search", { exact: true }).fill("Hougang");
  const table = page.getByLabel("Cases table");
  await expect(table.locator("tbody tr")).toHaveCount(1);
  await expect(page.locator("body")).not.toContainText(/\bsample\b/i);
  await table.getByRole("link", { name: "Open" }).click();
  await expect(page.getByRole("heading", { name: "Hougang Pet Supplies Pte. Ltd." })).toBeVisible();
  await expect(casePage).toContainText("Stopped for review");
  // Clicking the blocked step opens its section, like a live case.
  const documentSection = casePage.locator(".stage-disclosure").filter({ has: page.getByRole("button", { name: /^Document verification/ }) });
  await documentSection.getByRole("button", { name: /^Document verification/ }).click();
  await expect(documentSection.getByRole("button", { name: /^Document verification/ })).toHaveAttribute("aria-expanded", "false");
  await casePage.getByRole("button", { name: "Open details for Document verification" }).click();
  await expect(documentSection.getByRole("button", { name: /^Document verification/ })).toHaveAttribute("aria-expanded", "true");

  // Deep links survive a reload.
  await page.reload();
  await expect(page.getByRole("heading", { name: "Hougang Pet Supplies Pte. Ltd." })).toBeVisible();

  expect(SAMPLE_CASES.length).toBeGreaterThan(0);
  expect(sampleApiRequests).toEqual([]);
  expect(violations).toEqual([]);
});
