import { mkdirSync } from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";
import { createBrowserNetworkPolicy, handleBrowserRoute } from "../playwright.config";

/**
 * Owner review walkthrough of workflow governance (ADR-017 M1/M2): one coherent story with
 * numbered full-page screenshots. Local Mock harness only (memory stores, synthetic users and
 * data). Titles start with "Walkthrough" so the "Governance [0-9]" acceptance grep never runs it.
 */

const OUTPUT_DIR = process.env.CLM_E2E_WALKTHROUGH_DIR
  ?? "C:/Users/shane/Desktop/FYP/data-dividends-zero-touch-clm/outputs/workflow-governance-m1-20261117/walkthrough";
const STAGE = "Synthetic sanctions attestation";
const FIELD = "Synthetic attestation reference";
const HR = "hr-admin";
const DIRECTOR = "olivia-koh";

let violations: string[];
let pageErrors: string[];
let consoleProblems: string[];

test.beforeEach(async ({ page }) => {
  violations = [];
  pageErrors = [];
  consoleProblems = [];
  page.on("pageerror", error => pageErrors.push(`${error.name}: ${error.message}`));
  page.on("console", message => {
    if (message.type() === "error" || message.type() === "warning") consoleProblems.push(`${message.type()}: ${message.text()}`);
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

async function shot(page: Page, name: string) {
  mkdirSync(OUTPUT_DIR, { recursive: true });
  // Let transient focus rings and spinners settle before the capture.
  await page.waitForLoadState("networkidle");
  await page.screenshot({ path: path.join(OUTPUT_DIR, `${name}.png`), fullPage: true });
}

const mainNav = (page: Page) => page.getByRole("navigation", { name: "Main workspace" });
const stagesList = (page: Page) => page.getByRole("region", { name: "Pipeline stages" });
const settings = (page: Page) => page.getByRole("region", { name: "Stage settings" });
const submitButton = (page: Page) => page.getByRole("button", { name: "Submit for approval" });

async function signIn(page: Page, user: string) {
  await page.goto("/");
  await page.getByLabel("User ID").fill(user);
  await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(mainNav(page).getByRole("link", { name: "Policy", exact: true })).toBeVisible();
  // The signed-out session probe answers 401 by design.
  consoleProblems = [];
}

async function signOut(page: Page) {
  await page.locator(".operator-account__button").click();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Sign in", exact: true })).toBeVisible();
}

async function openWorkflows(page: Page) {
  await mainNav(page).getByRole("link", { name: "Workflows", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Workflows", level: 1 })).toBeVisible();
}

async function openOnboarding(page: Page) {
  await openWorkflows(page);
  await page.getByRole("row").filter({ hasText: "Corporate onboarding" }).getByRole("button", { name: "Edit" }).click();
  await expect(page.getByRole("heading", { name: "Corporate onboarding", level: 1 })).toBeVisible();
}

async function saveAndValidate(page: Page) {
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Changes saved to your proposal" })).toBeVisible();
  await page.getByRole("button", { name: "Validate", exact: true }).click();
  const report = page.getByTestId("validation-report");
  await expect(report).toBeVisible();
  return report;
}

test("Walkthrough: HR proposes, the Director approves, a weakening edit is refused, emergency fallback and notice", async ({ page }) => {
  test.setTimeout(600_000);
  await page.setViewportSize({ width: 1440, height: 1000 });

  // HR authors a governed change.
  await signIn(page, HR);
  await openWorkflows(page);
  await expect(page.getByRole("row").filter({ hasText: "Corporate onboarding" })).toBeVisible();
  await shot(page, "01-hr-workflows-list");

  await page.getByRole("row").filter({ hasText: "Corporate onboarding" }).getByRole("button", { name: "Edit" }).click();
  await expect(stagesList(page).getByText("Existing stages run exactly as they do today and can't be changed here.")).toBeVisible();
  await shot(page, "02-hr-onboarding-locked-stages");

  await page.getByTestId("propose-change").getByLabel("What does this change do? (optional)").fill("Synthetic: add a required attestation step");
  await page.getByRole("button", { name: "Propose a change" }).click();
  await expect(page.getByTestId("proposal-status")).toContainText("Open proposal · Draft");
  await stagesList(page).getByRole("button", { name: "Add stage after Document verification", exact: true }).click();
  await settings(page).getByLabel("Stage name").fill("Ownership & UBO");
  await settings(page).getByRole("button", { name: "Add field" }).click();
  await settings(page).getByLabel("Field name").fill(FIELD);
  await shot(page, "03-hr-proposal-editor-added-stage");

  let report = await saveAndValidate(page);
  await expect(report.locator('[data-rule="RR-9"]')).toBeVisible();
  await expect(submitButton(page)).toBeDisabled();
  await shot(page, "04-hr-validation-rr9-refusal");

  await stagesList(page).getByRole("button", { name: /^\d+\. Ownership & UBO$/ }).click();
  await settings(page).getByLabel("Stage name").fill(STAGE);
  report = await saveAndValidate(page);
  await expect(report).toContainText("Ready to submit");
  await expect(page.getByTestId("permanent-obligations")).toContainText(FIELD);
  await shot(page, "05-hr-validation-ready-permanent-obligations");

  await page.getByRole("button", { name: "Simulate", exact: true }).click();
  const simulation = page.getByTestId("simulation-panel");
  await simulation.getByRole("button", { name: "Run synthetic simulation" }).click();
  await expect(simulation.getByTestId("simulation-result").getByText("Send held").first()).toBeVisible();
  await shot(page, "06-hr-simulation-synthetic");

  await submitButton(page).click();
  await expect(page.getByTestId("proposal-status")).toContainText("Awaiting Director decision");
  await shot(page, "07-hr-submitted-awaiting-director");
  await signOut(page);

  // One Director decides.
  await signIn(page, DIRECTOR);
  await mainNav(page).getByRole("link", { name: "Workflow approvals", exact: true }).click();
  const row = page.getByRole("row").filter({ hasText: "Corporate onboarding" });
  await expect(row).toContainText(HR);
  await shot(page, "08-director-approvals-inbox");

  await row.getByRole("button", { name: "Review and decide Corporate onboarding proposal" }).click();
  await expect(page.getByRole("list", { name: "Permanent obligations" })).toContainText(FIELD);
  await page.getByLabel(/permanent once approved/).check();
  await page.getByLabel(/^Reason \(required/).fill("Synthetic approval of the attestation step");
  await expect(page.getByRole("button", { name: "Approve and publish" })).toBeEnabled();
  await shot(page, "09-director-comparison-warning");

  await page.getByRole("button", { name: "Approve and publish" }).click();
  await expect(page.getByRole("heading", { name: /^Approved · version \d+ is now active$/ })).toBeVisible();
  await expect(page.getByText("Governed approval")).toBeVisible();
  await shot(page, "10-director-approved-provenance");
  await signOut(page);

  // HR sees the governed version; a weakening edit is refused.
  await signIn(page, HR);
  await openOnboarding(page);
  await expect(page.getByTestId("version-history").locator('li[data-origin="GOVERNED_APPROVAL"]')).toContainText(`approved by ${DIRECTOR}`);
  await shot(page, "11-hr-version-history-active");

  await page.getByTestId("propose-change").getByLabel("What does this change do? (optional)").fill("Synthetic: try to make the field optional");
  await page.getByRole("button", { name: "Propose a change" }).click();
  await stagesList(page).getByRole("button", { name: new RegExp(`^\\d+\\. ${STAGE}$`) }).click();
  await settings(page).getByLabel("Required").uncheck();
  report = await saveAndValidate(page);
  await expect(report.locator('[data-rule="RR-3"]')).toBeVisible();
  await expect(submitButton(page)).toBeDisabled();
  await shot(page, "12-hr-weakening-edit-refused");
  page.once("dialog", dialog => void dialog.accept());
  await page.getByRole("button", { name: "Withdraw" }).click();
  await expect(page.getByTestId("propose-change")).toBeVisible();
  await signOut(page);

  // Director emergency fallback to the default (safe target keeps every obligation).
  await signIn(page, DIRECTOR);
  await openOnboarding(page);
  const panel = page.getByTestId("emergency-fallback");
  await panel.getByRole("button", { name: "Start emergency fallback" }).click();
  await panel.getByLabel("The default").check();
  await panel.getByLabel(/^Reason \(required/).fill("Synthetic emergency fallback to the default content");
  await panel.getByLabel("I understand this publishes without approval and HR will be notified.").check();
  await expect(panel.getByRole("button", { name: "Publish emergency fallback" })).toBeEnabled();
  await panel.scrollIntoViewIfNeeded();
  await shot(page, "13-director-emergency-fallback-form");

  await panel.getByRole("button", { name: "Publish emergency fallback" }).click();
  await expect(page.getByRole("status").filter({ hasText: /^Emergency fallback published: version \d+ is now active/ })).toBeVisible();
  const fallback = page.getByTestId("version-history").locator('li[data-origin="EMERGENCY_FALLBACK"]');
  await expect(fallback).toContainText(`Emergency fallback by ${DIRECTOR} — not approved`);
  await shot(page, "14-director-fallback-result");
  await signOut(page);

  // HR is notified and acknowledges.
  await signIn(page, HR);
  await openWorkflows(page);
  const notices = page.getByTestId("workflow-notices");
  await expect(notices).toContainText("Emergency fallback on Corporate onboarding");
  await expect(notices).toContainText("— not approved");
  await shot(page, "15-hr-notice-banner");

  await notices.getByRole("button", { name: /^Acknowledge notice for Corporate onboarding version \d+$/ }).click();
  // Nothing left to acknowledge: the alert is replaced by a polite, dismissible status (703a0057).
  await expect(page.getByTestId("workflow-notices-cleared")).toContainText("All notices acknowledged.");
  await expect(notices).toHaveCount(0);
  await shot(page, "16-hr-notice-acknowledged");
});
