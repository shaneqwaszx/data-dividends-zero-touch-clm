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
  await page.getByRole("link", { name: "Dashboard", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Dashboard", exact: true })).toBeVisible();
  await page.locator(".category-card--live").click();
  await expect(page.getByRole("heading", { name: "Onboarding Dashboard" })).toBeVisible();
  await expect(page.locator(".dashboard-date-range")).toHaveValue("30d");
  expect(dashboardRanges.length).toBeGreaterThan(0);
  expect(dashboardRanges.every(value => value === "30d")).toBe(true);
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
