import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { classifyBrowserRequest, createBrowserNetworkPolicy, handleBrowserRoute } from "../playwright.config";

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
  // R6 faults are bounded to the guarded owned frontend Dashboard GET; success
  // still uses the actual authenticated local backend, never a synthetic snapshot.
  let dashboardMode: "503" | "network" | "pending" | "pass" = "503";
  let dashboardRequests = 0;
  let releaseRetry = () => {};
  let retryGate = Promise.resolve();
  await page.route("**/*", async route => {
    const url = new URL(route.request().url());
    const decision = classifyBrowserRequest(url.href, policy, route.request().resourceType());
    if (decision.classification === "OWNED_LOOPBACK"
      && url.origin === process.env.PLAYWRIGHT_BASE_URL
      && url.pathname === "/api/clm/zero-touch/dashboard") {
      dashboardRequests++;
      if (dashboardMode === "503") return route.fulfill({ status: 503, contentType: "application/json",
        body: JSON.stringify({ detail: { code: "DASHBOARD_UNAVAILABLE", message: "SYNTHETIC_PRIVATE_RESPONSE_DETAIL" } }) });
      if (dashboardMode === "network") return route.abort("failed");
      if (dashboardMode === "pending") await retryGate;
    }
    return handleBrowserRoute(route, policy, violations);
  });
  await page.goto("/");
  await page.getByLabel("User ID").fill("maya-lim");
  await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  // Initial 503 and network failures recover directly from the category picker.
  await page.getByRole("link", { name: "Dashboard", exact: true }).click();
  const error = page.getByRole("alert").filter({ hasText: "Dashboard data is unavailable" });
  const retry = page.getByRole("button", { name: "Try again", exact: true });
  const dashboardLoading = page.getByRole("status").filter({ hasText: /^(Loading|Refreshing) dashboard/ });
  await expect(error).toBeVisible();
  await expect(page.getByRole("heading", { name: "Dashboard", exact: true })).toBeVisible();
  await expect(page.locator(".category-card--live")).not.toContainText("Loading");
  await expect(page.locator("body")).not.toContainText("SYNTHETIC_PRIVATE_RESPONSE_DETAIL");
  await expect(page.locator(".category-card--live button")).toHaveCount(0);
  dashboardMode = "network";
  const beforeNetwork = dashboardRequests;
  await retry.focus(); await page.keyboard.press("Enter");
  // The refetch and its automatic query retry (retry: 1) must both fail in network mode.
  // Otherwise the banner check can pass against the stale pre-refetch render, and the
  // retry is later parked on the pending gate below, hiding "Try again" (R1 hang).
  await expect.poll(() => dashboardRequests).toBeGreaterThanOrEqual(beforeNetwork + 2);
  await expect(error).toBeVisible();
  await expect(dashboardLoading).toHaveCount(0);
  dashboardMode = "pending";
  retryGate = new Promise<void>(resolve => { releaseRetry = resolve; });
  try {
    await retry.focus(); await page.keyboard.press("Space");
    await expect(dashboardLoading).toHaveText("Loading dashboard…");
    const pendingRequests = dashboardRequests;
    const card = page.locator(".category-card--live");
    await card.focus(); await page.keyboard.press("Enter");
    await expect(page.getByRole("heading", { name: "Onboarding Dashboard" })).toBeVisible();
    await page.getByRole("button", { name: "All categories" }).click();
    await expect(page.getByRole("heading", { name: "Dashboard", exact: true })).toBeVisible();
    expect(dashboardRequests).toBe(pendingRequests);
    const recovered = page.waitForResponse(response => new URL(response.url()).pathname === "/api/clm/zero-touch/dashboard" && response.status() === 200);
    dashboardMode = "pass"; releaseRetry();
    const genuine = await (await recovered).json();
    await expect(error).toHaveCount(0);
    await expect(card).toContainText(`${genuine.totals.non_completed_cases} open`);
    await card.click();
    dashboardMode = "503";
    await page.getByRole("button", { name: "Refresh", exact: true }).click();
    await expect(page.getByRole("alert")).toHaveText("Refresh failed; the last dashboard snapshot remains visible.");
    await page.getByRole("button", { name: "All categories" }).click();
    await expect(card).toContainText(`${genuine.totals.non_completed_cases} open`);
    await expect(page.getByRole("alert")).toHaveText("Refresh failed; the last dashboard snapshot remains visible.");
    dashboardMode = "pass";
    const refreshed = page.waitForResponse(response => new URL(response.url()).pathname === "/api/clm/zero-touch/dashboard" && response.status() === 200);
    await retry.focus(); await page.keyboard.press("Enter");
    expect((await refreshed).status()).toBe(200);
    await expect(page.getByRole("alert")).toHaveCount(0);
  } finally { dashboardMode = "pass"; releaseRetry(); }

  // Establish one genuine synthetic Mock completion through the normal UI.
  const fixture = path.resolve(path.dirname(fileURLToPath(import.meta.url)),
    "../../backend/tests/fixtures/uat/clean-company-profile.pdf");
  await page.getByRole("link", { name: "New onboarding", exact: true }).click();
  await page.getByLabel("Jurisdiction", { exact: true }).selectOption("SG");
  await page.getByLabel("Company Legal Name", { exact: true }).fill("MERLION CIRCULAR LABS PTE. LTD.");
  await page.getByLabel("Registration ID / UEN", { exact: true }).fill("202400001A");
  await page.locator("#home-document").setInputFiles(fixture);
  await page.getByRole("button", { name: "Create onboarding", exact: true }).click();
  await expect(page).toHaveURL(/\/cases\/[0-9a-f-]{36}$/i);
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
  // The weekly chart shows fixed mock figures; the week of 2026-10-26 is Singapore: 10.
  const recordedSegment = page.locator('.weekly-chart-seg[title="Singapore: 10"]');
  await expect(recordedSegment).toBeVisible();
  const segmentBox = await recordedSegment.boundingBox();
  expect(segmentBox?.height).toBeGreaterThan(0);
  expect(segmentBox?.width).toBeGreaterThan(0);
  await expect(page.locator('.weekly-chart-seg[title^="Australia:"]')).toHaveCount(8);
  expect(dashboardRanges.length).toBeGreaterThan(0);
  expect(dashboardRanges.every(value => value === "30d")).toBe(true);
  // Browser-clock skew must not change the same server duration or its age filters.
  const allCases = page.locator("article").filter({ has: page.getByRole("heading", { name: "All cases", exact: true }) });
  // Every sortable header is reachable and works with native keyboard activation.
  const exerciseSorts = async (heading: string) => {
    const article = page.locator("article").filter({ has: page.getByRole("heading", { name: heading, exact: true }) });
    const headers = article.locator("thead th.sortable-th");
    expect(await headers.count()).toBeGreaterThan(0);
    for (let i = 0; i < await headers.count(); i++) {
      const header = headers.nth(i);
      const button = header.getByRole("button");
      await expect(button).toHaveCount(1);
      await expect(header).toHaveAttribute("scope", "col");
      await button.focus();
      await page.keyboard.press("Shift+Tab");
      await page.keyboard.press("Tab");
      await expect(button).toBeFocused();
      const before = await header.getAttribute("aria-sort");
      await page.keyboard.press("Enter");
      await expect(header).toHaveAttribute("aria-sort", before === "ascending" ? "descending" : "ascending");
      await page.keyboard.press("Space");
      await expect(header).toHaveAttribute("aria-sort", before === "ascending" ? "ascending" : "descending");
      await expect(article.locator('th[aria-sort="ascending"], th[aria-sort="descending"]')).toHaveCount(1);
    }
  };
  await exerciseSorts("Time per pipeline step");
  const pipeline = page.locator("article").filter({ has: page.getByRole("heading", { name: "Time per pipeline step", exact: true }) });
  const disclosures = await pipeline.locator('tbody button[aria-controls]').evaluateAll(buttons => buttons.map(button => button.id));
  expect(disclosures).toHaveLength(6);
  const disclosureIds = new Set<string>();
  for (const controlId of disclosures) {
    const control = pipeline.locator(`[id="${controlId}"]`);
    const id = (await control.getAttribute("aria-controls"))!;
    expect(disclosureIds.has(id)).toBe(false); disclosureIds.add(id);
    const region = pipeline.locator(`[id="${id}"]`);
    await expect(region).toHaveAttribute("role", "region");
    await expect(control).toHaveAttribute("aria-expanded", "false");
    await control.focus(); await page.keyboard.press("Shift+Tab"); await page.keyboard.press("Tab");
    await expect(control).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(control).toHaveAttribute("aria-expanded", "true"); await expect(region).toBeVisible();
    await pipeline.getByRole("button", { name: "Step", exact: true }).click();
    await expect(control).toHaveAttribute("aria-expanded", "true"); await expect(region).toBeVisible();
    await control.focus(); await page.keyboard.press("Space");
    await expect(control).toHaveAttribute("aria-expanded", "false"); await expect(region).toBeHidden();
  }

  await exerciseSorts("Workload by person");
  await exerciseSorts("All cases");
  await expect(allCases.getByRole("columnheader", { name: "Case age / duration" })).toBeVisible();
  await allCases.getByRole("button", { name: "Completed", exact: true }).click();
  await expect(allCases.locator('td[aria-label^="Case duration:"]').first()).toBeVisible();
  await allCases.getByRole("button", { name: "All", exact: true }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  // Wide tables remain contained in their own scroll boxes at narrow widths.
  for (const scroll of await page.locator(".dashboard-page .table-scroll").all()) {
    const box = await scroll.boundingBox();
    expect(box!.width).toBeLessThanOrEqual(390);
    expect(box!.x + box!.width).toBeLessThanOrEqual(390);
  }
  await page.setViewportSize({ width: 1440, height: 900 });
  const ageFilter = allCases.locator(".filter-label").filter({ hasText: "Case age / duration" }).locator("select");
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
  await exerciseSorts("Your cases");
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


test("PR95 R4 recent activity pages past100 real authorized events", async ({ page }) => {
  const violations: string[] = [];
  const policy = createBrowserNetworkPolicy({ frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!,
    backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false });
  await page.route("**/*", route => handleBrowserRoute(route, policy, violations));
  await page.goto("/");
  await page.getByLabel("User ID").fill("maya-lim");
  await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
  const login = page.waitForResponse(response => new URL(response.url()).pathname === "/api/auth/login");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  const session = await (await login).json();
  const headers = { "X-CSRF-Token": session.csrf_token, Origin: process.env.PLAYWRIGHT_BASE_URL! };
  const priorMine = await (await page.request.get("/api/clm/zero-touch/dashboard?scope=mine&date_range=30d")).json();
  const priorTeam = await (await page.request.get("/api/clm/zero-touch/dashboard?date_range=30d")).json();
  const expectedMineTotal = priorMine.totals.total_cases + 205;
  const expectedTeamTotal = priorTeam.totals.total_cases + 205;
  // Genuine local test-mode case creation; no provider start or mocked API replies.
  for (let batch = 0; batch < 21; batch++) {
    const responses = await Promise.all(Array.from({ length: Math.min(10, 205 - batch * 10) }, (_, item) =>
      page.request.post("/api/clm/zero-touch/cases", { headers, data: {
        uen: `2088${String(batch * 10 + item).padStart(5, "0")}A`,
        country_of_incorporation: "SG", legal_name: "Synthetic R4 activity fixture",
      } })));
    expect(responses.every(response => response.status() === 201)).toBe(true);
  }
  const first = await (await page.request.get("/api/clm/zero-touch/activity?created_by=maya-lim&limit=100")).json();
  expect(first.items).toHaveLength(100); expect(first.has_more).toBe(true);
  const expected: string[] = first.items.map((item: { case_id: string; sequence: number }) => `${item.case_id}-${item.sequence}`);
  let finalPage = false;
  // Bounded fixture oracle; product UI itself holds only one10-event page.
  for (let offset = 100; offset < 1000; offset += 100) {
    const tail = await (await page.request.get(`/api/clm/zero-touch/activity?created_by=maya-lim&limit=100&offset=${offset}`)).json();
    expected.push(...tail.items.map((item: { case_id: string; sequence: number }) => `${item.case_id}-${item.sequence}`));
    if (!tail.has_more) { finalPage = true; break; }
  }
  expect(finalPage).toBe(true);
  await page.getByRole("link", { name: "Dashboard", exact: true }).click();
  await page.locator(".category-card--live").click();
  await page.getByRole("button", { name: "My work", exact: true }).click();
  await expect(page.getByRole("combobox", { name: "Dashboard date range", exact: true })).toHaveValue("30d");
  const yourCases = page.locator("article").filter({ has: page.getByRole("heading", { name: "Your cases", exact: true }) });
  await expect(yourCases).toContainText(`Loaded subset: 200 of ${expectedMineTotal} creator-only cases`);
  await expect(yourCases).toContainText("filters apply only to the loaded subset");
  await expect(yourCases.getByRole("link", { name: "View or search Cases" })).toHaveAttribute("href", "/cases");
  const blockedCases = page.locator("article").filter({ has: page.getByRole("heading", { name: "Blocked cases", exact: true }) });
  await expect(blockedCases).toContainText(`Loaded subset: 200 of ${expectedMineTotal}`);
  const activity = page.locator("article").filter({ has: page.getByRole("heading", { name: "Recent activity on your cases · all dates", exact: true }) });
  const seen: string[] = [];
  for (let offset = 0; offset < expected.length; offset += 10) {
    await expect(activity.locator(".activity-row")).toHaveCount(Math.min(10, expected.length - offset));
    expect(await activity.locator(".pagination").innerText()).not.toContain("of 100");
    const response = await page.request.get(`/api/clm/zero-touch/activity?created_by=maya-lim&limit=10&offset=${offset}`);
    const current = await response.json();
    expect(await activity.locator(".activity-row > div").allTextContents()).toEqual(current.items.map((item: { message: string }) => item.message));
    seen.push(...current.items.map((item: { case_id: string; sequence: number }) => `${item.case_id}-${item.sequence}`));
    if (offset + 10 < expected.length) {
      const next = page.waitForResponse(response => new URL(response.url()).pathname.endsWith("/zero-touch/activity")
        && new URL(response.url()).searchParams.get("offset") === String(offset + 10));
      await activity.getByRole("button", { name: "Next ›", exact: true }).click();
      expect((await next).status()).toBe(200);
    }
  }
  expect(seen).toEqual(expected); expect(new Set(seen).size).toBe(seen.length);
  await expect(activity.getByRole("button", { name: "Next ›", exact: true })).toBeDisabled();
  await activity.getByRole("button", { name: "‹ Prev", exact: true }).click();
  await expect(activity.locator(".activity-row")).toHaveCount(10);
  const reset = page.waitForResponse(response => new URL(response.url()).pathname.endsWith("/zero-touch/activity")
    && !new URL(response.url()).searchParams.has("offset"));
  await activity.getByRole("button", { name: "Refresh activity", exact: true }).click();
  expect((await reset).status()).toBe(200);
  await expect(activity.getByRole("button", { name: "‹ Prev", exact: true })).toBeDisabled();
  await expect(activity.getByRole("link", { name: "Audit →" })).toHaveAttribute("href", "/audit");
  await page.getByRole("button", { name: "Manager", exact: true }).click();
  const allCases = page.locator("article").filter({ has: page.getByRole("heading", { name: "All cases", exact: true }) });
  // Direct fixture API writes bypass app mutation invalidation; refresh the fixed snapshot.
  await page.getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(allCases).toContainText(`Loaded subset: 200 of ${expectedTeamTotal} cases in the authorized cohort`);
  await allCases.getByRole("link", { name: "View or search Cases" }).click();
  await expect(page).toHaveURL(/\/cases$/);
  expect(violations).toEqual([]);
});
