import path from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test, type Page } from "@playwright/test";
import { createBrowserNetworkPolicy, handleBrowserRoute } from "../playwright.config";
import { openStage } from "./stage-disclosures";

/*
 * D-141 (amends D-121 display only). The browser harness runs the blocking review mode
 * (scripts/e2e_backend_server.py), so a real case reaches a complete Ownership & UBO stage and
 * this spec sets or clears only the backend's presentation flag `advisory_review` on that node
 * in the case read. The flag itself is pinned against the official Mock lane in
 * apps/backend/tests/test_advisory_review_node_flag.py.
 */

const currentDirectory = path.dirname(fileURLToPath(import.meta.url));
const cleanFixture = path.resolve(currentDirectory, "../../backend/tests/fixtures/uat/clean-company-profile.pdf");

function requiredEnvironment(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`The task-owned E2E launcher must provide ${name}`);
  return value;
}

const violations: string[] = [];

test.beforeEach(async ({ page }) => {
  violations.length = 0;
  const policy = createBrowserNetworkPolicy({
    frontendOrigin: requiredEnvironment("PLAYWRIGHT_BASE_URL"),
    backendOrigin: requiredEnvironment("CLM_E2E_BACKEND_ORIGIN"),
    allowDirectBackend: false,
  });
  await page.route("**/*", (route) => handleBrowserRoute(route, policy, violations));
});

test.afterEach(() => expect(violations).toEqual([]));

async function createCleanCase(page: Page): Promise<string> {
  await page.goto("/");
  await page.getByLabel("User ID").fill("maya-lim");
  await page.getByLabel("Password").fill(requiredEnvironment("CLM_E2E_PASSWORD"));
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("link", { name: "New onboarding", exact: true }).click();
  const startFresh = page.getByRole("button", { name: "Start a new case" });
  const landing = page.getByRole("heading", { name: "Start onboarding" });
  await expect(landing.or(startFresh)).toBeVisible();
  if (await startFresh.isVisible()) await startFresh.click();
  await page.getByLabel("Jurisdiction").selectOption("SG");
  await page.getByLabel("Company Legal Name").fill("MERLION CIRCULAR LABS PTE. LTD.");
  await page.getByLabel("Registration ID / UEN").fill("202400001A");
  await page.locator("#home-document").setInputFiles(cleanFixture);
  await page.getByRole("button", { name: "Create onboarding" }).click();
  await expect(page).toHaveURL(/\/cases\/[0-9a-f-]{36}$/i);
  return page.url().split("/").at(-1)!;
}

function ownershipSection(page: Page) {
  return page.locator(".stage-disclosure").filter({ has: page.getByRole("heading", { name: "Ownership & UBO", exact: true }) });
}

function sidebarStep(page: Page) {
  return page.locator('.ds-stage-rail .ds-stage[data-node-id="OWNERSHIP_UBO"]');
}

test("advisory ownership review shows amber Review advised, never green Complete", { tag: "@advisory-review-status" }, async ({ page }) => {
  let advisory = true;
  await page.route("**/api/clm/zero-touch/cases/*", async (route) => {
    const url = new URL(route.request().url());
    if (route.request().method() !== "GET" || !/^\/api\/clm\/zero-touch\/cases\/[0-9a-f-]{36}$/i.test(url.pathname)) {
      await route.fallback();
      return;
    }
    const response = await route.fetch();
    const payload = await response.json() as { processing_pipeline: Array<Record<string, unknown>> };
    payload.processing_pipeline = payload.processing_pipeline.map((node) => (
      node.node_id === "OWNERSHIP_UBO" && node.status === "COMPLETE"
        ? { ...node, advisory_review: advisory ? true : null }
        : node
    ));
    await route.fulfill({ response, json: payload });
  });

  const caseId = await createCleanCase(page);
  await expect.poll(async () => {
    const summary = await (await page.request.get(`/api/clm/zero-touch/cases/${caseId}`)).json();
    return summary.processing_pipeline.find((node: { node_id: string }) => node.node_id === "OWNERSHIP_UBO")?.status;
  }, { timeout: 120_000 }).toBe("COMPLETE");
  await page.reload();

  // Advisory: amber header chip and sidebar step, each with the words, not colour alone.
  await openStage(page, "Ownership & UBO");
  const section = ownershipSection(page);
  await expect(section).toHaveAttribute("data-tone", "advised");
  await expect(section.locator(".stage-disclosure__status")).toHaveText("Review advised");
  await expect(section.getByText("Not blocking. Review ownership before Review & Send.", { exact: false })).toBeVisible();
  const step = sidebarStep(page);
  await expect(step).toHaveAttribute("data-status", "COMPLETE");
  await expect(step).toHaveAttribute("data-display-state", "advised");
  await expect(step.locator(".ds-stage-node")).toHaveClass(/\badvised\b/);
  await expect(step.locator(".ds-stage-node")).not.toHaveText("✓");
  await expect(step.locator(".ds-stage-copy > .text-muted")).toHaveText("Review advised");

  // No open review: green Complete is unchanged.
  advisory = false;
  await page.reload();
  await expect(ownershipSection(page)).toHaveAttribute("data-tone", "done");
  await expect(ownershipSection(page).locator(".stage-disclosure__status")).toHaveText("Complete");
  await expect(sidebarStep(page)).not.toHaveAttribute("data-display-state", "advised");
  await expect(sidebarStep(page).locator(".ds-stage-copy > .text-muted")).toHaveText("Complete");
});
