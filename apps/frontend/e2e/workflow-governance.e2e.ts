import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test, type Locator, type Page } from "@playwright/test";
import { openStage } from "./stage-disclosures";
import { createBrowserNetworkPolicy, handleBrowserRoute } from "../playwright.config";

/**
 * ADR-017 workflow governance M1 acceptance: HR authors governed proposals, one Director decides,
 * in a real browser against the real backend (memory stores, synthetic users and data only).
 * The tests share one backend lifecycle and run in order.
 */

const PERMANENT_WARNING = "Once approved, this required step or field can never be removed or weakened in the product.";
const LEGACY_NOTE = "Activated by a Director before approval governance; not independently approved.";
const ADDED_STAGE = "E2E synthetic sanctions attestation";
const ADDED_FIELD = "Synthetic attestation reference";
const NEW_WORKFLOW = "E2E synthetic periodic review";
const HR = "biz-ops";
const fixtures = path.join(path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../.."), "apps/backend/tests/fixtures/uat");
const DIRECTOR = "olivia-koh";

let violations: string[];
let pageErrors: string[];
let consoleProblems: string[];
let step = "start";

test.describe.configure({ mode: "serial" });

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
  await expect(mainNav(page).getByRole("link", { name: "Policy", exact: true })).toBeVisible();
  // The signed-out session probe answers 401 by design; judge the console from here on.
  consoleProblems = [];
  step = `${user}-signed-in`;
}

const mainNav = (page: Page) => page.getByRole("navigation", { name: "Main workspace" });

async function openWorkflow(page: Page, name: string) {
  await mainNav(page).getByRole("link", { name: "Workflows", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Workflows", level: 1 })).toBeVisible();
  await page.getByRole("row").filter({ hasText: name }).getByRole("button", { name: "Edit" }).click();
  await expect(page.getByRole("heading", { name, level: 1 })).toBeVisible();
}

const stagesList = (page: Page) => page.getByRole("region", { name: "Pipeline stages" });
const settings = (page: Page) => page.getByRole("region", { name: "Stage settings" });
const submitButton = (page: Page) => page.getByRole("button", { name: "Submit for approval" });

async function saveAndValidate(page: Page): Promise<Locator> {
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Changes saved to your proposal" })).toBeVisible();
  await page.getByRole("button", { name: "Validate", exact: true }).click();
  const report = page.getByTestId("validation-report");
  await expect(report).toBeVisible();
  return report;
}

async function proposeChange(page: Page, note: string) {
  await page.getByTestId("propose-change").getByLabel("What does this change do? (optional)").fill(note);
  await page.getByRole("button", { name: "Propose a change" }).click();
  await expect(page.getByTestId("proposal-status")).toContainText("Open proposal · Draft");
  await expect(page.getByTestId("proposal-status")).toContainText(`by ${HR}`);
}

async function decideFromInbox(page: Page, workflowName: string) {
  await mainNav(page).getByRole("link", { name: "Workflow approvals", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Workflow approvals", level: 1 })).toBeVisible();
  const row = page.getByRole("row").filter({ hasText: workflowName });
  await expect(row).toContainText(HR);
  await row.getByRole("button", { name: `Review and decide ${workflowName} proposal` }).click();
  await expect(page.getByRole("heading", { name: new RegExp(`^${workflowName}`), level: 1 })).toBeVisible();
}

test("Governance 1+3: HR proposes a required stage on onboarding; locked stages and RR-9 hold", async ({ page }) => {
  test.setTimeout(120_000);
  await signIn(page, HR);

  // Self-decision (6): HR has no Workflow approvals entry and cannot open the page or the API.
  step = "hr-no-approvals";
  await expect(mainNav(page).getByRole("link", { name: "Workflow approvals", exact: true })).toHaveCount(0);
  await page.goto("/workflow-approvals");
  await expect(page.getByRole("heading", { name: "Page unavailable" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Workflow approvals", level: 1 })).toHaveCount(0);
  const inboxStatus = await page.evaluate(async () => (await fetch("/api/workflow-approvals", { credentials: "same-origin" })).status);
  expect([403, 404]).toContain(inboxStatus);
  // The refused fetch above logs a resource error by design.
  consoleProblems = [];

  step = "open-onboarding";
  await openWorkflow(page, "Corporate onboarding");
  // Locked stages (3): listed, read-only, nothing to select or edit before a proposal exists.
  const lockedNames = ["Case created", "Registry verification", "Document verification", "Ownership & UBO", "Final review & send"];
  for (const name of lockedNames) await expect(stagesList(page).getByText(new RegExp(`^\\d+\\. ${name.replace("&", "\\&")}$`))).toBeVisible();
  await expect(stagesList(page).getByText("Existing stages run exactly as they do today and can't be changed here.")).toBeVisible();
  await expect(stagesList(page).getByRole("button", { name: /^Add stage after/ })).toHaveCount(0);
  await expect(page.getByTestId("version-history")).toBeVisible();
  await expect(page.getByTestId("approved-count")).toContainText("0 approved through governance");

  step = "propose";
  await proposeChange(page, "E2E synthetic: add a required attestation step");
  // Locked rows stay plain text: only "Add after" anchors appear, never an editable locked stage.
  await expect(stagesList(page).getByRole("button", { name: "Add stage after Final review & send" })).toHaveCount(0);
  await expect(stagesList(page).getByRole("button", { name: "Ownership & UBO", exact: true })).toHaveCount(0);

  step = "add-stage";
  await stagesList(page).getByRole("button", { name: "Add stage after Document verification", exact: true }).click();
  await settings(page).getByLabel("Stage name").fill("Ownership & UBO");
  await settings(page).getByRole("button", { name: "Add field" }).click();
  await settings(page).getByLabel("Field name").fill(ADDED_FIELD);
  await expect(settings(page).getByLabel("Required")).toBeChecked();

  // RR-9 (3): an added stage named like a locked stage is refused and Submit stays disabled.
  step = "rr9";
  let report = await saveAndValidate(page);
  await expect(report).toContainText("Not ready to submit");
  await expect(report.locator('[data-rule="RR-9"]')).toContainText("The built-in mandatory stages and their order cannot be changed.");
  await expect(report.locator('[data-rule="RR-9"]')).toContainText("cannot take the identity of a built-in onboarding stage");
  await expect(submitButton(page)).toBeDisabled();

  step = "valid";
  await stagesList(page).getByRole("button", { name: /^\d+\. Ownership & UBO$/ }).click();
  await settings(page).getByLabel("Stage name").fill(ADDED_STAGE);
  report = await saveAndValidate(page);
  await expect(report).toContainText("Ready to submit");
  await expect(report).toContainText("0 issues");
  // Permanent-obligation preview (1).
  const obligations = page.getByTestId("permanent-obligations");
  await expect(obligations).toContainText(PERMANENT_WARNING);
  await expect(obligations).toContainText(ADDED_STAGE);
  await expect(obligations).toContainText(ADDED_FIELD);

  // Synthetic simulation (1): the added step holds the send until confirmed.
  step = "simulate";
  await page.getByRole("button", { name: "Simulate", exact: true }).click();
  const simulation = page.getByTestId("simulation-panel");
  await expect(simulation).toContainText("Synthetic simulation: fictional companies from a fixed catalogue.");
  await simulation.getByRole("button", { name: "Run synthetic simulation" }).click();
  const result = simulation.getByTestId("simulation-result");
  await expect(result.locator("article").first()).toBeVisible();
  await expect(result).toContainText(ADDED_STAGE);
  await expect(result.getByText("Added step").first()).toBeVisible();
  await expect(result.getByText(`required: ${ADDED_FIELD}`).first()).toBeVisible();
  await expect(result.getByText("Send held").first()).toBeVisible();

  step = "submit";
  await expect(submitButton(page)).toBeEnabled();
  await submitButton(page).click();
  await expect(page.getByRole("status").filter({ hasText: "Submitted for approval. A Director will decide it." })).toBeVisible();
  await expect(page.getByTestId("proposal-status")).toContainText("Awaiting Director decision");
  await expect(submitButton(page)).toHaveCount(0);
});

test("Governance 6+4: the Director cannot author, then approves with acknowledgement and reason", async ({ page }) => {
  test.setTimeout(120_000);
  await signIn(page, DIRECTOR);

  // Self-decision (6): the Director reads workflows but cannot propose.
  step = "director-no-author";
  await openWorkflow(page, "Corporate onboarding");
  await expect(page.getByTestId("proposal-status")).toContainText("Awaiting Director decision");
  await expect(page.getByRole("button", { name: "Propose a change" })).toHaveCount(0);
  await expect(submitButton(page)).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Save changes" })).toHaveCount(0);

  step = "compare";
  await decideFromInbox(page, "Corporate onboarding");
  await expect(page.getByRole("region", { name: "Proposed changes" })).toContainText(ADDED_STAGE);
  await expect(page.getByRole("region", { name: "Proposed changes" })).toContainText("after Document verification");
  await expect(page.getByRole("region", { name: "Required-obligation checks" })).toContainText("Passed");
  await expect(page.getByText(PERMANENT_WARNING)).toBeVisible();
  await expect(page.getByRole("list", { name: "Permanent obligations" })).toContainText(ADDED_FIELD);

  step = "approve-gating";
  const approve = page.getByRole("button", { name: "Approve and publish" });
  const confirm = page.getByLabel(/permanent once approved/);
  const reason = page.getByLabel(/^Reason \(required/);
  await expect(approve).toBeDisabled();
  await reason.fill("Too short");
  await expect(approve).toBeDisabled();
  await confirm.check();
  await expect(approve).toBeDisabled();
  await reason.fill("E2E synthetic approval of the attestation step");
  await expect(approve).toBeEnabled();
  await confirm.uncheck();
  await expect(approve).toBeDisabled();
  await confirm.check();

  step = "approve";
  await approve.click();
  const decided = page.getByRole("status").filter({ has: page.getByRole("heading", { name: /^Approved · version \d+ is now active$/ }) });
  await expect(decided).toBeVisible();
  await expect(decided).toContainText(`Decided by ${DIRECTOR}`);
  const provenance = decided.getByRole("definition");
  await expect(decided.getByText("Governed approval")).toBeVisible();
  await expect(provenance.filter({ hasText: HR })).toHaveCount(1);
  await expect(provenance.filter({ hasText: new RegExp(`^${DIRECTOR}$`) })).toHaveCount(1);

  step = "inbox-empty";
  await decided.getByRole("button", { name: "Back to workflow approvals" }).click();
  await expect(page.getByText("No workflow proposals are waiting for a decision.")).toBeVisible();
});

test("Governance 2+7: version history shows the governed version; a weakening edit is refused", async ({ page }) => {
  test.setTimeout(120_000);
  await signIn(page, HR);
  step = "history";
  await openWorkflow(page, "Corporate onboarding");
  const history = page.getByTestId("version-history");
  await expect(page.getByTestId("approved-count")).toContainText("1 approved through governance");
  const governed = history.locator('li[data-origin="GOVERNED_APPROVAL"]');
  await expect(governed).toHaveCount(1);
  await expect(governed).toContainText(`Proposed by ${HR} · approved by ${DIRECTOR}`);
  await expect(page.getByTestId("approved-count")).toContainText("1 version · 1 approved through governance");
  // Legacy versions (7) are never labelled approved. The memory store provisions onboarding born
  // governed (active_version 0), so this lifecycle has no pre-governance version to show.
  const legacy = history.locator('li[data-origin="PRE_GOVERNANCE_DIRECTOR_ACTIVATION"]');
  await expect(legacy).toHaveCount(0);
  await expect(history).not.toContainText(LEGACY_NOTE);
  // Audit history records the proposal and the decision.
  await expect(page.getByRole("region", { name: "History" }).getByRole("listitem").first()).toBeVisible();
  await expect(stagesList(page).getByText(new RegExp(`^\\d+\\. ${ADDED_STAGE}$`))).toBeVisible();

  step = "weaken-optional";
  await proposeChange(page, "E2E synthetic: try to weaken the attestation step");
  await stagesList(page).getByRole("button", { name: new RegExp(`^\\d+\\. ${ADDED_STAGE}$`) }).click();
  await settings(page).getByLabel("Required").uncheck();
  let report = await saveAndValidate(page);
  await expect(report).toContainText("Not ready to submit");
  await expect(report.locator('[data-rule="RR-3"]')).toContainText("A required field cannot be removed or made optional.");
  await expect(submitButton(page)).toBeDisabled();

  step = "weaken-remove";
  await settings(page).getByLabel("Required").check();
  await settings(page).getByRole("button", { name: "Remove field" }).click();
  await settings(page).getByRole("button", { name: "Add field" }).click();
  report = await saveAndValidate(page);
  await expect(report).toContainText("Not ready to submit");
  await expect(report.locator('[data-rule="RR-3"]')).toBeVisible();
  await expect(submitButton(page)).toBeDisabled();

  step = "weaken-remove-stage";
  await settings(page).getByRole("button", { name: "Remove stage" }).click();
  report = await saveAndValidate(page);
  await expect(report.locator('[data-rule="RR-1"]')).toContainText("A required step cannot be removed.");
  await expect(submitButton(page)).toBeDisabled();

  step = "withdraw";
  page.once("dialog", dialog => void dialog.accept());
  await page.getByRole("button", { name: "Withdraw" }).click();
  await expect(page.getByTestId("propose-change")).toBeVisible();
});

test("Governance 1+5: HR creates a new workflow and submits; the Director rejects; nothing publishes", async ({ page }) => {
  test.setTimeout(120_000);
  await signIn(page, HR);
  step = "create-workflow";
  await mainNav(page).getByRole("link", { name: "Workflows", exact: true }).click();
  await page.getByRole("button", { name: "New workflow" }).click();
  await page.getByLabel("Workflow name").fill(NEW_WORKFLOW);
  await page.getByRole("button", { name: "Create workflow" }).click();
  await expect(page.getByRole("heading", { name: NEW_WORKFLOW, level: 1 })).toBeVisible();
  await expect(page.getByText(/Existing case · Draft/)).toBeVisible();
  await expect(page.getByTestId("version-history")).toContainText("No published versions yet.");

  step = "propose-new";
  await proposeChange(page, "E2E synthetic: first version of the periodic review");
  await page.getByRole("button", { name: "Add stage", exact: true }).click();
  await settings(page).getByLabel("Stage name").fill("Synthetic review checklist");
  await settings(page).getByRole("button", { name: "Add field" }).click();
  await settings(page).getByLabel("Field name").fill("Synthetic reviewer note");
  const report = await saveAndValidate(page);
  await expect(report).toContainText("Ready to submit");
  await submitButton(page).click();
  await expect(page.getByTestId("proposal-status")).toContainText("Awaiting Director decision");

  step = "director-reject";
  await page.locator(".operator-account__button").click();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Sign in", exact: true })).toBeVisible();
  await signIn(page, DIRECTOR);
  await decideFromInbox(page, NEW_WORKFLOW);
  await expect(page.getByText("No version is active yet. Approving publishes the first version.")).toBeVisible();
  const reject = page.getByRole("button", { name: "Reject", exact: true });
  await expect(reject).toBeDisabled();
  await page.getByLabel(/^Reason \(required/).fill("short");
  await expect(reject).toBeDisabled();
  await page.getByLabel(/^Reason \(required/).fill("E2E synthetic rejection: checklist incomplete");
  await expect(reject).toBeEnabled();
  await reject.click();
  await expect(page.getByRole("heading", { name: "Rejected · nothing was published" })).toBeVisible();

  step = "unchanged";
  await openWorkflow(page, NEW_WORKFLOW);
  await expect(page.getByText(/Existing case · Draft/)).toBeVisible();
  await expect(page.getByTestId("version-history")).toContainText("No published versions yet.");
  await expect(page.getByTestId("proposal-status")).toHaveCount(0);
  // The onboarding workflow keeps exactly the one governed version.
  await page.getByRole("button", { name: "← Back to Workflows" }).click();
  await openWorkflow(page, "Corporate onboarding");
  await expect(page.getByTestId("approved-count")).toContainText("1 approved through governance");
});

test("Governance 8: a new onboarding case is held by the approved required stage until it is confirmed", async ({ page }) => {
  test.setTimeout(180_000);
  await signIn(page, "maya-lim");
  step = "create-case";
  await mainNav(page).getByRole("link", { name: "New onboarding", exact: true }).click();
  await page.getByLabel("Jurisdiction", { exact: true }).selectOption("SG");
  await page.getByLabel("Company Legal Name", { exact: true }).fill("MERLION CIRCULAR LABS PTE. LTD.");
  await page.getByLabel("Registration ID / UEN").fill("202400001A");
  await page.locator("#home-document").setInputFiles(path.join(fixtures, "clean-company-profile.pdf"));
  // Same complete-evidence Mock classification as the Golden STP spec, supplied before Start.
  await page.route("**/api/clm/zero-touch/cases", async route => {
    if (route.request().method() !== "POST") return route.fallback();
    const response = await route.fetch();
    expect(response.status()).toBe(201);
    const created = await response.json();
    const headers = route.request().headers();
    const bound = await page.request.put(`/api/clm/zero-touch/cases/${created.case.case_id}/target-classification`, {
      headers: { "X-CSRF-Token": headers["x-csrf-token"], "Origin": process.env.PLAYWRIGHT_BASE_URL! },
      data: { kyc_customer_type: "Company - Private", client_segment: "Corporate",
        expected_automation_version: created.version, expected_case_event_count: created.case.events.length },
    });
    expect(bound.status()).toBe(200);
    await route.fulfill({ response });
  });
  await page.getByRole("button", { name: "Create onboarding" }).click();
  await expect(page).toHaveURL(/\/cases\/[0-9a-f-]{36}$/i);
  const caseId = page.url().split("/").at(-1)!;
  const summary = async () => (await page.request.get(`/api/clm/zero-touch/cases/${caseId}`)).json();
  await expect.poll(async () => (await summary()).status, { timeout: 90_000 }).toBe("WAITING_FOR_REVIEW");

  step = "stage-shown";
  const section = page.locator(".stage-disclosure").filter({ has: page.getByRole("heading", { name: ADDED_STAGE, exact: true }) });
  await expect(section).toHaveCount(1);
  await expect(section).toContainText("Must be confirmed before the case can be sent.");

  step = "send-held";
  const sendAttempt = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/target-confirmation"));
  await page.getByRole("button", { name: "Confirm and send to Mock GoldTier" }).click();
  const held = await sendAttempt;
  expect(held.status()).not.toBe(200);
  const afterHold = await summary();
  expect(afterHold.status).not.toBe("COMPLETED");
  expect(afterHold.timeline.filter((event: any) => event.event_type === "TARGET_DISPATCH_CONFIRMED")).toHaveLength(0);
  // The refused send logs a resource error by design.
  consoleProblems = [];

  step = "confirm-stage";
  await openStage(page, ADDED_STAGE);
  await section.getByLabel(ADDED_FIELD).fill("SYN-ATTEST-0001");
  await section.getByRole("button", { name: "Confirm", exact: true }).click();
  await expect(section).toContainText("Complete");

  step = "send";
  await page.reload();
  const sent = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/target-confirmation"));
  await page.getByRole("button", { name: "Confirm and send to Mock GoldTier" }).click();
  expect((await sent).status()).toBe(200);
  await expect.poll(async () => (await summary()).status, { timeout: 60_000 }).toBe("COMPLETED");
  const completed = await summary();
  expect(completed.timeline.filter((event: any) => event.event_type === "TARGET_DISPATCH_CONFIRMED")).toHaveLength(1);
});

// ---- M2: history, recovery and administration (contract CC-4 to CC-6) ----

const SECOND_STAGE = "E2E synthetic secondary check";
const SECOND_FIELD = "Synthetic secondary reference";

async function signOut(page: Page) {
  await page.locator(".operator-account__button").click();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Sign in", exact: true })).toBeVisible();
}

/** Opens the inbox row, ticks any obligation acknowledgement, gives a reason and approves. */
async function directorApprove(page: Page, workflowName: string, reasonText: string, buttonName = "Approve and publish") {
  await decideFromInbox(page, workflowName);
  const approve = page.getByRole("button", { name: buttonName });
  await expect(approve).toBeDisabled();
  const confirm = page.getByLabel(/permanent once approved/);
  if (await confirm.count()) await confirm.check();
  await page.getByLabel(/^Reason \(required/).fill(reasonText);
  await expect(approve).toBeEnabled();
  await approve.click();
  const decided = page.getByRole("status").filter({ has: page.getByRole("heading", { name: /^Approved/ }) });
  await expect(decided).toBeVisible();
  return decided;
}

/** HR, inside an open workflow: a fixed-content recovery proposal is created, validated and submitted. */
async function proposeRecovery(page: Page, button: string) {
  const recovery = page.getByTestId("recovery-actions");
  await recovery.getByRole("button", { name: button }).click();
  const confirm = recovery.getByTestId("recovery-confirm");
  await confirm.getByLabel("Why is this needed? (optional)").fill(`E2E synthetic: ${button.toLowerCase()}`);
  await confirm.getByRole("button", { name: "Create proposal" }).click();
  await expect(page.getByTestId("proposal-status")).toContainText("Open proposal · Draft");
  await page.getByRole("button", { name: "Validate", exact: true }).click();
  await expect(page.getByTestId("validation-report")).toContainText("Ready to submit");
  await expect(submitButton(page)).toBeEnabled();
  await submitButton(page).click();
  await expect(page.getByTestId("proposal-status")).toContainText("Awaiting Director decision");
}

async function workflowIdByName(page: Page, name: string): Promise<string> {
  const items = await page.evaluate(async () => (await fetch("/api/workflows", { credentials: "same-origin" })).json());
  const found = (items as Array<{ workflow_id: string; name: string }>).find(item => item.name === name);
  expect(found).toBeTruthy();
  return found!.workflow_id;
}

test("Governance 9: reset to default after a second version keeps every required obligation", async ({ page }) => {
  test.setTimeout(180_000);
  await signIn(page, HR);
  step = "second-version";
  await openWorkflow(page, "Corporate onboarding");
  await proposeChange(page, "E2E synthetic: second required step");
  await stagesList(page).getByRole("button", { name: "Add stage after Registry verification", exact: true }).click();
  await settings(page).getByLabel("Stage name").fill(SECOND_STAGE);
  await settings(page).getByRole("button", { name: "Add field" }).click();
  await settings(page).getByLabel("Field name").fill(SECOND_FIELD);
  await expect(await saveAndValidate(page)).toContainText("Ready to submit");
  await submitButton(page).click();
  await expect(page.getByTestId("proposal-status")).toContainText("Awaiting Director decision");
  await signOut(page);
  await signIn(page, DIRECTOR);
  await directorApprove(page, "Corporate onboarding", "E2E synthetic approval of the second step");
  await signOut(page);

  step = "reset";
  await signIn(page, HR);
  await openWorkflow(page, "Corporate onboarding");
  await expect(page.getByTestId("approved-count")).toContainText("2 versions · 2 approved through governance");
  await proposeRecovery(page, "Propose reset to default");
  await signOut(page);
  await signIn(page, DIRECTOR);
  const decided = await directorApprove(page, "Corporate onboarding", "E2E synthetic reset to the default content");
  await expect(decided.getByRole("heading", { name: "Approved · version 3 is now active" })).toBeVisible();
  await expect(decided.getByText("Governed approval")).toBeVisible();

  step = "safe-target";
  await openWorkflow(page, "Corporate onboarding");
  await page.getByTestId("version-history").getByRole("button", { name: "View v3" }).click();
  const view = page.getByTestId("version-view");
  await expect(view).toContainText("Active version");
  await expect(view).toContainText(`${ADDED_FIELD}, required`);
  await expect(view).toContainText(`${SECOND_FIELD}, required`);
  await expect(view).toContainText(ADDED_STAGE);
  await expect(view).toContainText(SECOND_STAGE);
});

test("Governance 10: Director emergency fallback is never approved; HR acknowledges the notice", async ({ page }) => {
  test.setTimeout(120_000);
  await signIn(page, DIRECTOR);
  step = "fallback";
  await openWorkflow(page, "Corporate onboarding");
  // Counted, not assumed, so this test also stands when Governance 9 could not publish.
  const before = await page.getByTestId("approved-count").innerText();
  const [, versionsBefore, approvedBefore] = before.match(/^(\d+) versions? · (\d+) approved/)!.map(Number);
  const next = versionsBefore + 1;
  const panel = page.getByTestId("emergency-fallback");
  await panel.getByRole("button", { name: "Start emergency fallback" }).click();
  const publish = panel.getByRole("button", { name: "Publish emergency fallback" });
  await expect(publish).toBeDisabled();
  await panel.getByLabel("A published version").check();
  await expect(publish).toBeDisabled();
  await panel.getByRole("combobox").selectOption("1");
  await panel.getByLabel(/^Reason \(required/).fill("short");
  await panel.getByLabel("I understand this publishes without approval and HR will be notified.").check();
  await expect(publish).toBeDisabled();
  await panel.getByLabel(/^Reason \(required/).fill("E2E synthetic emergency fallback to version 1");
  await expect(publish).toBeEnabled();
  await publish.click();
  await expect(page.getByRole("status").filter({ hasText: `Emergency fallback published: version ${next} is now active` })).toBeVisible();
  const history = page.getByTestId("version-history");
  const fallback = history.locator('li[data-origin="EMERGENCY_FALLBACK"]');
  await expect(fallback).toHaveCount(1);
  await expect(fallback).toContainText(`Version ${next}`);
  await expect(fallback).toContainText(`Emergency fallback by ${DIRECTOR} — not approved`);
  await expect(page.getByTestId("approved-count")).toContainText(`${next} versions · ${approvedBefore} approved through governance`);
  // Safe target: version 1's content plus every obligation in force.
  await history.getByRole("button", { name: `View v${next}` }).click();
  await expect(page.getByTestId("version-view")).toContainText(`${ADDED_FIELD}, required`);
  if (versionsBefore >= 2) await expect(page.getByTestId("version-view")).toContainText(`${SECOND_FIELD}, required`);
  // Directors see the notice read-only.
  await expect(page.getByTestId("workflow-notices")).toContainText("Read-only: an HR user must acknowledge these notices.");
  await expect(page.getByTestId("workflow-notices").getByRole("button", { name: /^Acknowledge/ })).toHaveCount(0);
  await signOut(page);

  step = "acknowledge";
  await signIn(page, HR);
  await mainNav(page).getByRole("link", { name: "Workflows", exact: true }).click();
  const notices = page.getByTestId("workflow-notices");
  await expect(notices).toContainText("Workflow notices (1)");
  await expect(notices).toContainText(`Emergency fallback on Corporate onboarding: version ${next} by ${DIRECTOR}`);
  await expect(notices).toContainText("— not approved");
  await expect(notices).toContainText("Reason: E2E synthetic emergency fallback to version 1");
  await notices.getByRole("button", { name: `Acknowledge notice for Corporate onboarding version ${next}` }).click();
  // Nothing left to acknowledge: the alert is replaced by a polite, dismissible status (703a0057).
  await expect(page.getByTestId("workflow-notices-cleared")).toContainText("All notices acknowledged.");
  await expect(notices).toHaveCount(0);
  await page.reload();
  await expect(page.getByRole("heading", { name: "Workflows", level: 1 })).toBeVisible();
  await expect(page.getByTestId("workflow-notices")).toHaveCount(0);
});

test("Governance 11: a non-onboarding workflow is deactivated and reactivated through approvals", async ({ page }) => {
  test.setTimeout(240_000);
  await signIn(page, HR);
  step = "publish";
  await openWorkflow(page, NEW_WORKFLOW);
  await proposeChange(page, "E2E synthetic: publish the periodic review");
  await page.getByRole("button", { name: "Add stage", exact: true }).click();
  await settings(page).getByLabel("Stage name").fill("Synthetic review checklist");
  await settings(page).getByRole("button", { name: "Add field" }).click();
  await settings(page).getByLabel("Field name").fill("Synthetic reviewer note");
  await expect(await saveAndValidate(page)).toContainText("Ready to submit");
  await submitButton(page).click();
  await signOut(page);
  await signIn(page, DIRECTOR);
  await directorApprove(page, NEW_WORKFLOW, "E2E synthetic first version of the review");
  await signOut(page);
  await signIn(page, "maya-lim");
  await expect(mainNav(page).getByRole("link", { name: NEW_WORKFLOW, exact: true })).toBeVisible();
  await signOut(page);

  step = "deactivate";
  await signIn(page, HR);
  await openWorkflow(page, NEW_WORKFLOW);
  await expect(page.getByText(/Existing case · Active/)).toBeVisible();
  await proposeRecovery(page, "Propose deactivate");
  await signOut(page);
  await signIn(page, DIRECTOR);
  await directorApprove(page, NEW_WORKFLOW, "E2E synthetic deactivation of the review", "Approve and deactivate");
  await signOut(page);
  await signIn(page, HR);
  await openWorkflow(page, NEW_WORKFLOW);
  await expect(page.getByTestId("workflow-deactivated")).toContainText("This workflow is deactivated: new runs are blocked.");
  await expect(page.getByText(/Existing case · Active/)).toHaveCount(0);
  await signOut(page);
  await signIn(page, "maya-lim");
  await expect(mainNav(page).getByRole("link", { name: "Cases", exact: true })).toBeVisible();
  await expect(mainNav(page).getByRole("link", { name: NEW_WORKFLOW, exact: true })).toHaveCount(0);
  await signOut(page);

  step = "reactivate";
  await signIn(page, HR);
  await openWorkflow(page, NEW_WORKFLOW);
  await page.getByTestId("recovery-actions").getByRole("button", { name: "Propose reactivate" }).click();
  await page.getByTestId("recovery-confirm").getByRole("button", { name: "Create proposal" }).click();
  await expect(page.getByTestId("proposal-status")).toContainText("Open proposal · Draft");
  await page.getByRole("button", { name: "Validate", exact: true }).click();
  await expect(page.getByTestId("validation-report")).toContainText("Ready to submit");
  await submitButton(page).click();
  await expect(page.getByTestId("proposal-status")).toContainText("Awaiting Director decision");
  await signOut(page);
  await signIn(page, DIRECTOR);
  await directorApprove(page, NEW_WORKFLOW, "E2E synthetic reactivation of the review");
  await signOut(page);
  await signIn(page, HR);
  await openWorkflow(page, NEW_WORKFLOW);
  await expect(page.getByText(/Existing case · Active/)).toBeVisible();
  await expect(page.getByTestId("workflow-deactivated")).toHaveCount(0);
  await signOut(page);
  await signIn(page, "maya-lim");
  await expect(mainNav(page).getByRole("link", { name: NEW_WORKFLOW, exact: true })).toBeVisible();
});

test("Governance 12: a withdrawn proposal is copied into a new draft authored by the copier", async ({ page }) => {
  test.setTimeout(120_000);
  await signIn(page, HR);
  step = "copy";
  await openWorkflow(page, "Corporate onboarding");
  const earlier = page.getByTestId("earlier-proposals");
  const withdrawn = earlier.locator('li[data-state="WITHDRAWN"]');
  await expect(withdrawn).toHaveCount(1);
  await expect(withdrawn).toContainText(`by ${HR}`);
  await withdrawn.getByRole("button", { name: "Copy into new draft" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Copied into a new draft authored by you." })).toBeVisible();
  await expect(page.getByTestId("proposal-status")).toContainText(`Open proposal · Draft · by ${HR}`);
  // The original keeps its record; the copy names it.
  await expect(withdrawn).toHaveCount(1);
  const id = await workflowIdByName(page, "Corporate onboarding");
  const detail = await page.evaluate(async wid => (await fetch(`/api/workflows/${encodeURIComponent(wid)}`, { credentials: "same-origin" })).json(), id);
  const original = detail.governance.decided_proposals.find((item: { state: string }) => item.state === "WITHDRAWN");
  expect(detail.governance.open_proposal.author_id).toBe(HR);
  expect(detail.governance.open_proposal.copied_from).toBe(original.proposal_id);
  expect(detail.governance.open_proposal.proposal_id).not.toBe(original.proposal_id);
});
