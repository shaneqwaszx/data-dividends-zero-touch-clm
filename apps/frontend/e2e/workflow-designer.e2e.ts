import { expect, test, type Page } from "@playwright/test";
import { createBrowserNetworkPolicy, handleBrowserRoute, retainedEvidencePath } from "../playwright.config";

/** P1 smoke: the read-only workflow designer in a real browser against the real backend. */

let violations: string[];
let pageErrors: string[];
let consoleProblems: string[];
let step = "start";

test.beforeEach(async ({ page }) => {
  violations = [];
  pageErrors = [];
  consoleProblems = [];
  page.on("pageerror", error => pageErrors.push(`${error.name}: ${error.message}`));
  page.on("console", message => {
    if (message.type() === "error" || message.type() === "warning") consoleProblems.push(`[${step}] ${message.type()}: ${message.text()}`);
  });
  const policy = createBrowserNetworkPolicy({
    frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!,
    backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!,
    allowDirectBackend: false,
  });
  await page.route("**/*", route => handleBrowserRoute(route, policy, violations));
});

test.afterEach(() => {
  expect(violations).toEqual([]);
  expect(pageErrors).toEqual([]);
  expect(consoleProblems).toEqual([]);
});

async function signIn(page: Page, user: string) {
  await page.goto("/");
  await page.getByLabel("User ID").fill(user);
  await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("link", { name: "Policy", exact: true })).toBeVisible();
  // The signed-out session probe answers 401 by design; judge the console from here on.
  consoleProblems = [];
  step = `${user}-signed-in`;
}

async function openDesigner(page: Page) {
  await page.getByRole("link", { name: "Policy", exact: true }).click();
  await page.getByRole("navigation", { name: "Policy and Workflow" }).getByRole("link", { name: "Workflow designer" }).click();
  await expect(page.getByRole("heading", { name: "Workflow designer", level: 1 })).toBeVisible();
  await expect(page.locator(".react-flow__node")).toHaveCount(12);
}

test("Workflow designer read-only smoke for HR, with repeated navigation", async ({ page }) => {
  test.setTimeout(90000);
  // Viewport-sized screenshots: a fullPage capture re-emulates the viewport mid-shot and
  // React Flow then warns about a zero-sized container (seen only under capture, never in use).
  await page.setViewportSize({ width: 1440, height: 1800 });
  await signIn(page, "biz-ops");
  await openDesigner(page);

  // Fixed, read-only canvas: no draggable or connectable element, no interactive lock toggle.
  await expect(page.locator(".react-flow__node.draggable")).toHaveCount(0);
  await expect(page.locator(".react-flow__handle.connectable")).toHaveCount(0);
  await expect(page.locator(".react-flow__controls-interactive")).toHaveCount(0);
  await expect(page.getByText("Conditional branches are not supported by the current backend.")).toBeVisible();
  step = "shot-diagram";
  await page.screenshot({ path: retainedEvidencePath("clm-p1-workflow-designer-diagram-1440.png") });

  // Selecting a stage shows its real dependencies and live policy rules.
  step = "select-stage";
  await page.getByRole("button", { name: /Stage \d+: Ownership & UBO/ }).click();
  const panel = page.getByRole("complementary", { name: "Selected stage details" });
  await expect(panel.getByRole("heading", { name: "Ownership & UBO", level: 2 })).toBeVisible();
  await expect(panel.getByText("OWNERSHIP_UBO_THRESHOLD_PERCENT")).toBeVisible();
  await expect(panel.getByText("Runtime enforced").first()).toBeVisible();
  await page.screenshot({ path: retainedEvidencePath("clm-p1-workflow-designer-panel-1440.png") });

  // Shared entity-resolution rules: defined once under Risk assessment, read by reference at
  // Existing-customer search and Final review & send (P2-1).
  step = "shared-primary";
  await page.getByRole("button", { name: /Stage \d+: Risk assessment/ }).click();
  await expect(panel.getByRole("heading", { name: "Risk assessment", level: 2 })).toBeVisible();
  await expect(panel.getByText("Also used by Existing-customer search, Final review & send.").first()).toBeVisible();
  await expect(panel.getByRole("note", { name: "Conditional runtime use" })).toContainText("In this environment:");
  await page.screenshot({ path: retainedEvidencePath("clm-p1-workflow-designer-shared-primary-1440.png") });
  step = "shared-reference";
  await page.getByRole("button", { name: /Stage \d+: Existing-customer search/ }).click();
  const shared = panel.getByRole("group", { name: "Shared rules defined under Risk assessment" });
  await expect(shared.getByText("Usage reference")).toBeVisible();
  await expect(shared.getByText("ENTITY_RESOLUTION_AUTO_MATCH_THRESHOLD")).toBeVisible();
  await expect(shared.getByText(/Also used by Final review & send\./)).toBeVisible();
  await expect(page.getByRole("button", { name: /Stage \d+: Existing-customer search/ })).toContainText("8 shared");
  await page.screenshot({ path: retainedEvidencePath("clm-p1-workflow-designer-shared-reference-1440.png") });

  // The accessible outline lists the same twelve stages in run order.
  step = "outline";
  await page.getByRole("button", { name: "Outline", exact: true }).click();
  await expect(page.getByRole("list", { name: /in run order/ }).getByRole("button")).toHaveCount(12);
  await page.screenshot({ path: retainedEvidencePath("clm-p1-workflow-designer-outline-1440.png") });

  // Repeated navigation mounts and unmounts the canvas without errors or warnings.
  for (let round = 0; round < 3; round += 1) {
    step = `navigate-${round}`;
    await page.getByRole("navigation", { name: "Policy and Workflow" }).getByRole("link", { name: "Policy rules" }).click();
    await expect(page.getByRole("heading", { name: /Active policy/ })).toBeVisible();
    await page.getByRole("navigation", { name: "Policy and Workflow" }).getByRole("link", { name: "Workflow designer" }).click();
    await expect(page.locator(".react-flow__node")).toHaveCount(12);
  }

  step = "resize-390";
  await page.setViewportSize({ width: 390, height: 3200 });
  await expect(page.locator(".react-flow__node")).toHaveCount(12);
  // The canvas refits on resize: the first and last stages are visible, not stranded off-canvas.
  await expect(page.getByRole("button", { name: /^Stage 1: / })).toBeInViewport();
  await expect(page.getByRole("button", { name: /^Stage 12: / })).toBeInViewport();
  await page.screenshot({ path: retainedEvidencePath("clm-p1-workflow-designer-390.png") });
});

test("Workflow designer is shown to a Director and hidden from an onboarder", async ({ page }) => {
  test.setTimeout(60000);
  await signIn(page, "olivia-koh");
  await openDesigner(page);
  expect(consoleProblems).toEqual([]);
  await page.locator(".operator-account__button").click();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Sign in", exact: true })).toBeVisible();

  await signIn(page, "maya-lim");
  await page.getByRole("link", { name: "Policy", exact: true }).click();
  await expect(page.getByRole("heading", { name: /Active policy/ })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Policy and Workflow" })).toHaveCount(0);
});
