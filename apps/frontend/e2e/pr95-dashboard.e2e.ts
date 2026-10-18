import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { createBrowserNetworkPolicy, handleBrowserRoute } from "../playwright.config";

test("PR95 Dashboard v2 filters preserve navigation and authenticated scope", async ({ page }) => {
  const violations: string[] = [];
  const dashboardRanges: Array<string | null> = [];
  page.on("request", request => {
    const url = new URL(request.url());
    if (url.pathname.endsWith("/zero-touch/dashboard")) {
      dashboardRanges.push(url.searchParams.get("date_range"));
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
  // Establish one genuine synthetic Mock completion through the normal UI.
  const fixture = path.resolve(path.dirname(fileURLToPath(import.meta.url)),
    "../../backend/tests/fixtures/uat/clean-company-profile.pdf");
  await page.getByRole("link", { name: "New onboarding", exact: true }).click();
  await page.getByLabel("Jurisdiction", { exact: true }).selectOption("SG");
  await page.getByLabel("Company Legal Name", { exact: true }).fill("MERLION CIRCULAR LABS PTE. LTD.");
  await page.getByLabel("Registration ID / UEN", { exact: true }).fill("202400001A");
  await page.locator("#home-document").setInputFiles(fixture);
  await page.getByRole("button", { name: "Create onboarding", exact: true }).click();
  await expect(page.getByRole("button", { name: "Open full case", exact: true })).toBeEnabled();
  await page.getByRole("button", { name: "Open full case", exact: true }).click();
  const confirmation = page.getByRole("button", { name: "Confirm and send to Mock GoldTier" });
  await expect(confirmation).toBeEnabled();
  const completed = page.waitForResponse(response => response.request().method() === "POST"
    && new URL(response.url()).pathname.endsWith("/target-confirmation"));
  await confirmation.click();
  const completion = await completed;
  expect(completion.status()).toBe(200);
  expect((await completion.json()).status).toBe("COMPLETED");
  await page.getByRole("link", { name: "Dashboard", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Dashboard", exact: true })).toBeVisible();
  await page.locator(".category-card--live").click();
  await expect(page.getByRole("heading", { name: "Onboarding Dashboard" })).toBeVisible();
  await expect(page.locator(".dashboard-date-range")).toHaveValue("30d");
  const recordedSegment = page.locator('.weekly-chart-seg[title="Singapore: 1"]');
  await expect(recordedSegment).toBeVisible();
  const segmentBox = await recordedSegment.boundingBox();
  expect(segmentBox?.height).toBeGreaterThan(0);
  expect(segmentBox?.width).toBeGreaterThan(0);
  await expect(page.locator('.weekly-chart-seg[title^="Australia:"]')).toHaveCount(0);
  expect(dashboardRanges.length).toBeGreaterThan(0);
  expect(dashboardRanges.every(value => value === "30d")).toBe(true);
  // Browser-clock skew must not change the same server duration or its age filters.
  const allCases = page.locator("article").filter({ has: page.getByRole("heading", { name: "All cases", exact: true }) });
  const ageFilter = allCases.locator(".filter-label").filter({ hasText: "Age" }).locator("select");
  await ageFilter.selectOption("lt7");
  await expect(allCases.locator("tbody tr").first()).toBeVisible();
  const observedCount = await allCases.locator("tbody tr").count();
  const observedRow = await allCases.locator("tbody").innerText();
  await page.clock.setFixedTime(new Date(Date.now() + 40 * 86_400_000));
  await ageFilter.selectOption("gt30");
  await expect(allCases.getByText("No cases match these filters.")).toBeVisible();
  await ageFilter.selectOption("lt7");
  await expect(allCases.locator("tbody tr")).toHaveCount(observedCount);
  await expect(allCases.locator("tbody")).toHaveText(observedRow, { useInnerText: true });
  const mine = page.waitForResponse(r => r.url().includes("/zero-touch/dashboard?")
    && new URL(r.url()).searchParams.get("scope") === "mine");
  await page.getByRole("button", { name: "My work", exact: true }).click();
  const mineResponse = await mine;
  expect(mineResponse.status()).toBe(200);
  expect((await mineResponse.json()).view).toBe("mine");
  const range = page.waitForResponse(r => r.url().includes("/zero-touch/dashboard?")
    && new URL(r.url()).searchParams.get("date_range") === "all");
  await page.locator(".dashboard-date-range").selectOption("all");
  expect((await range).status()).toBe(200);
  await page.getByRole("link", { name: "Cases", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Cases", exact: true })).toBeVisible();
  await page.goBack();
  await expect(page.getByRole("heading", { name: "Dashboard", exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "Dashboard", exact: true })).toBeVisible();
  expect(violations).toEqual([]);
});
