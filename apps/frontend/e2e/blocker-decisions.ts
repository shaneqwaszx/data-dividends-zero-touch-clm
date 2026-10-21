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
  // Nothing is pre-selected: every pending field needs an explicit decision.
  const fields = page.locator('input[data-review-field][value="REJECTED"]');
  await expect(fields.first()).toBeVisible();
  // Case navigation focuses the review two animation frames after render; let it land before deciding,
  // so it cannot move focus away from the control being decided.
  await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => requestAnimationFrame(() => resolve())))));
  const count = await fields.count();
  expect(count).toBeGreaterThan(0);
  for (let index = 0; index < count; index++) {
    const key = (await fields.nth(index).getAttribute("data-review-field"))!;
    const documentId = (await fields.nth(index).getAttribute("data-document-id"))!;
    if (key in corrections) {
      // Typing the corrected value records the correction (the box overlays its radio), as a reviewer does.
      const correction = page.getByLabel(`Correction for ${key.replaceAll("_", " ")}`, { exact: true });
      await correction.focus();
      await correction.fill(corrections[key]);
      await expect(correction).toBeFocused();
      await expect(page.locator(`input[data-document-id="${documentId}"][data-review-field="${key}"][value="CORRECTED"]`)).toBeChecked();
      continue;
    }
    const control = page.locator(`input[data-document-id="${documentId}"][data-review-field="${key}"][value="ACCEPTED"]`);
    await control.focus();
    await control.check();
    await expect(control).toBeFocused();
    await expect(control).toBeChecked();
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
  const controls = page.locator(`input[data-reconciliation-field][value="${action}"]`);
  await expect(controls.first()).toBeVisible();
  const count = await controls.count();
  expect(count).toBeGreaterThan(0);
  for (let index = 0; index < count; index++) {
    await controls.nth(index).focus();
    await controls.nth(index).check();
    await expect(controls.nth(index)).toBeFocused();
    await expect(controls.nth(index)).toBeChecked();
  }
  page.off("request", listener);
  expect(mutations).toEqual([]);
  return confirmBatch(page);
}
