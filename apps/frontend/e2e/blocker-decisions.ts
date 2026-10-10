import { expect, type Page } from "@playwright/test";

/** Normal rendered controls; choices must stay entirely local until confirmation. */
export async function confirmBatch(page: Page) {
  const applied = page.waitForResponse(response => response.request().method() === "POST"
    && response.url().endsWith("/review-decisions"));
  await page.getByRole("button", { name: "Confirm decisions & continue onboarding", exact: true }).click();
  const response = await applied;
  expect(response.status()).toBe(200);
  // The response precedes the owning view's four supporting-query publications.
  // Do not select an optional group control from the previous evidence render.
  await expect(page.locator(".case-action-progress")).toHaveCount(0);
  return response.json();
}

export async function reviewPendingFields(page: Page, corrections: Record<string, string> = {}) {
  const mutations: string[] = [];
  const listener = (request: import("@playwright/test").Request) => {
    if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method())) mutations.push(request.url());
  };
  page.on("request", listener);
  const family = page.getByLabel("Decision group", { exact: true });
  if (await family.count()) await family.selectOption("document");
  const controls = page.locator("select[data-review-field]");
  await expect(controls.first()).toBeVisible();
  const count = await controls.count();
  expect(count).toBeGreaterThan(0);
  for (let index = 0; index < count; index++) {
    const control = controls.nth(index);
    const key = (await control.getAttribute("data-review-field"))!;
    await control.focus();
    await control.selectOption(key in corrections ? "CORRECTED" : "ACCEPTED");
    await expect(control).toBeFocused();
    if (key in corrections) await page.getByLabel(`Correction for ${key.replaceAll("_", " ")}`, { exact: true }).fill(corrections[key]);
  }
  page.off("request", listener);
  expect(mutations).toEqual([]);
  return confirmBatch(page);
}

export async function reviewSourceChoices(page: Page, action = "KEEP_REGISTRY_VALUE") {
  const mutations: string[] = [];
  const listener = (request: import("@playwright/test").Request) => {
    if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method())) mutations.push(request.url());
  };
  page.on("request", listener);
  const family = page.getByLabel("Decision group", { exact: true });
  if (await family.count()) await family.selectOption("source");
  const controls = page.locator("select[data-reconciliation-field]");
  await expect(controls.first()).toBeVisible();
  const count = await controls.count();
  expect(count).toBeGreaterThan(0);
  for (let index = 0; index < count; index++) {
    await controls.nth(index).focus();
    await controls.nth(index).selectOption(action);
    await expect(controls.nth(index)).toBeFocused();
  }
  page.off("request", listener);
  expect(mutations).toEqual([]);
  return confirmBatch(page);
}
