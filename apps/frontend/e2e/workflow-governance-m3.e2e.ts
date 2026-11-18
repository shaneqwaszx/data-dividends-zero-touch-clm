import { expect, test, type Locator, type Page } from "@playwright/test";
import { createBrowserNetworkPolicy, handleBrowserRoute } from "../playwright.config";

/**
 * ADR-018 workflow governance M3 owner scenarios: conditional, add-only applicability, in a real
 * browser against the real backend (memory stores, Mock ACRA, Mock GoldTier, synthetic users and
 * data only; nothing here is Live). The backend must run with the conditional-applicability gate
 * on (CLM_WORKFLOW_CONDITIONAL_APPLICABILITY_ENABLED=true, passed only by this spec's run); every
 * other spec keeps the product default (off). Run this spec on its own backend.
 *
 * The Mock ACRA dataset has no LLP sample (only companies and the Garden business), so an LLP
 * receiving its stage is proven on the backend (test_workflow_governance_m3_physical and the memory
 * twins). Here a Company receives its Company-only stage and never the LLP-only stage.
 */

const BASE = process.env.PLAYWRIGHT_BASE_URL!;
const WF = "/api/workflows/corporate-onboarding";
const HR = "hr-admin";
const DIRECTOR = "olivia-koh";
const RM = "maya-lim";
const REGISTRY_STAGE = "E2E M3 registry reference";
const REGISTRY_FIELD = "Synthetic registry reference";
const LLP_STAGE = "E2E M3 LLP partners register";
const LLP_FIELD = "Synthetic partner count";
const COMPANY_STAGE = "E2E M3 company secretary check";
const COMPANY_FIELD = "Synthetic secretary name";
const CONDITIONAL_NAMES = [REGISTRY_STAGE, LLP_STAGE, COMPANY_STAGE];
// Mock ACRA samples (apps/backend/app/connectors/mock_acra.py): private companies limited by shares.
const COMPANY_UEN = "202400001A";
const EARLY_COMPANY_UEN = "202400008H";
const LATE_COMPANY_UEN = "202400009I";
const GARDEN_UEN = "11111999A"; // Mock "BUSINESS": a bound business / partnership
const UNKNOWN_UENS = ["209900001Z", "209900002Z"]; // not in the Mock dataset: no entity, no binding
// Mandatory product nodes no workflow condition can remove (ADR-018 §2.1).
const MANDATORY_NODES = ["ACRA_REGISTRY", "DOCUMENT_IDP", "OWNERSHIP_UBO", "ADVISORY", "FINAL_REVIEW_SEND"];
const BEFORE_REGISTRY = "Conditions need the registry result, so they are available only from Registry verification onwards.";
const BEFORE_REGISTRY_ISSUE = "Conditional steps are available only from Registry verification onwards.";

type Headers = Record<string, string>;
type Stage = { stage_id: string; name: string; after_node_id: string | null; applies_to?: string[]; fields: Array<Record<string, unknown>> };
type Run = { run_id: string; revision: number; stages: Stage[]; applicability?: Record<string, unknown> | null };

let violations: string[];
let pageErrors: string[];
let consoleProblems: string[];
let notFound: string[];
let step = "start";

test.describe.configure({ mode: "serial" });
test.skip(process.env.CLM_WORKFLOW_CONDITIONAL_APPLICABILITY_ENABLED !== "true",
  "Workflow governance M3 needs its own backend with the conditional-applicability gate on.");

test.beforeEach(async ({ page }) => {
  violations = [];
  pageErrors = [];
  consoleProblems = [];
  notFound = [];
  page.on("pageerror", error => pageErrors.push(`${error.name}: ${error.message}`));
  page.on("console", message => {
    if (message.type() === "error" || message.type() === "warning") consoleProblems.push(`[${step}] ${message.type()}: ${message.text()}`);
  });
  page.on("dialog", dialog => void dialog.accept());
  page.on("response", response => { if (response.status() === 404) notFound.push(new URL(response.url()).pathname); });
  const policy = createBrowserNetworkPolicy({
    frontendOrigin: BASE,
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

const mainNav = (page: Page) => page.getByRole("navigation", { name: "Main workspace" });
const stagesList = (page: Page) => page.getByRole("region", { name: "Pipeline stages" });
const settings = (page: Page) => page.getByRole("region", { name: "Stage settings" });
const submitButton = (page: Page) => page.getByRole("button", { name: "Submit for approval" });
const stageConditions = (page: Page) => settings(page).getByTestId("entity-stage-applies-to");
const disclosure = (page: Page, name: string) => page.locator(".stage-disclosure").filter({ has: page.getByRole("heading", { name, exact: true }) });

/** Signs in through the UI and returns this session's mutation headers (same-origin, via the proxy). */
async function signIn(page: Page, user: string): Promise<Headers> {
  await page.goto("/");
  await page.getByLabel("User ID").fill(user);
  await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
  const login = page.waitForResponse(response => new URL(response.url()).pathname === "/api/auth/login");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  const session = await (await login).json();
  await expect(mainNav(page).getByRole("link", { name: "Policy", exact: true })).toBeVisible();
  // The signed-out session probe answers 401 by design; judge the console from here on.
  consoleProblems = [];
  step = `${user}-signed-in`;
  return { "X-CSRF-Token": session.csrf_token, Origin: BASE };
}

async function signOut(page: Page) {
  await page.locator(".operator-account__button").click();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Sign in", exact: true })).toBeVisible();
}

async function openOnboarding(page: Page) {
  await mainNav(page).getByRole("link", { name: "Workflows", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Workflows", level: 1 })).toBeVisible();
  await page.getByRole("row").filter({ hasText: "Corporate onboarding" }).getByRole("button", { name: "Edit" }).click();
  await expect(page.getByRole("heading", { name: "Corporate onboarding", level: 1 })).toBeVisible();
}

async function proposeChange(page: Page, note: string) {
  await page.getByTestId("propose-change").getByLabel("What does this change do? (optional)").fill(note);
  await page.getByRole("button", { name: "Propose a change" }).click();
  await expect(page.getByTestId("proposal-status")).toContainText("Open proposal · Draft");
}

async function saveAndValidate(page: Page): Promise<Locator> {
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Changes saved to your proposal" })).toBeVisible();
  await page.getByRole("button", { name: "Validate", exact: true }).click();
  const report = page.getByTestId("validation-report");
  await expect(report).toBeVisible();
  return report;
}

/** Adds a required one-field stage after an existing stage, optionally only for some legal forms. */
async function addStage(page: Page, after: string, name: string, fieldName: string, forms: string[] = []) {
  await stagesList(page).getByRole("button", { name: `Add stage after ${after}`, exact: true }).click();
  await settings(page).getByLabel("Stage name").fill(name);
  await settings(page).getByRole("button", { name: "Add field" }).click();
  await settings(page).getByLabel("Field name").fill(fieldName);
  if (forms.length === 0) return;
  await stageConditions(page).getByLabel("Only these legal forms").check();
  for (const form of forms) await stageConditions(page).getByLabel(form, { exact: true }).check();
}

/** Opens the inbox row, ticks the obligation acknowledgement, gives a reason and approves. */
async function directorApprove(page: Page, reasonText: string) {
  await mainNav(page).getByRole("link", { name: "Workflow approvals", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Workflow approvals", level: 1 })).toBeVisible();
  const row = page.getByRole("row").filter({ hasText: "Corporate onboarding" });
  await expect(row).toContainText(HR);
  await row.getByRole("button", { name: "Review and decide Corporate onboarding proposal" }).click();
  const approve = page.getByRole("button", { name: "Approve and publish" });
  await expect(page.getByLabel(/^Reason \(required/)).toBeVisible();
  // The comparison (and any permanent-obligation acknowledgement) loads with the page.
  await page.waitForLoadState("networkidle");
  const confirm = page.getByLabel(/permanent once approved/);
  if (await confirm.count()) await confirm.check();
  await page.getByLabel(/^Reason \(required/).fill(reasonText);
  await expect(approve).toBeEnabled();
  await approve.click();
  await expect(page.getByRole("heading", { name: /^Approved · version \d+ is now active$/ })).toBeVisible();
}

// ---- API helpers: Playwright requests through the frontend proxy, in the signed-in page session ----

async function api(page: Page, method: "GET" | "POST" | "PUT", url: string, headers?: Headers, data?: unknown) {
  return page.request.fetch(url, { method, headers, data });
}

async function workflow(page: Page) {
  const response = await api(page, "GET", WF);
  expect(response.status()).toBe(200);
  return response.json();
}

function activeStages(detail: { active_version: number | null; versions: Array<{ version: number; stages: Stage[] }> }): Stage[] {
  return detail.versions.find(item => item.version === detail.active_version)?.stages ?? [];
}

const byName = (stages: Stage[], name: string) => stages.find(item => item.name === name);

async function createProposal(page: Page, headers: Headers, body: Record<string, unknown>) {
  const created = await api(page, "POST", `${WF}/proposals`, headers, {
    expected_workflow_revision: (await workflow(page)).revision, ...body,
  });
  expect(created.status(), await created.text()).toBe(201);
  return created.json();
}

async function validate(page: Page, headers: Headers, proposalId: string, stages?: Stage[]) {
  const response = await api(page, "POST", `${WF}/proposals/${proposalId}/validate`, headers, stages ? { stages } : {});
  expect(response.status()).toBe(200);
  return response.json();
}

async function submit(page: Page, headers: Headers, proposal: { proposal_id: string; revision: number }, contentHash: string) {
  return api(page, "POST", `${WF}/proposals/${proposal.proposal_id}/submit`, headers, {
    expected_workflow_revision: (await workflow(page)).revision,
    expected_proposal_revision: proposal.revision,
    content_hash: contentHash,
  });
}

async function withdraw(page: Page, headers: Headers, proposalId: string) {
  const open = (await workflow(page)).governance.open_proposal;
  expect(open.proposal_id).toBe(proposalId);
  const response = await api(page, "POST", `${WF}/proposals/${proposalId}/withdraw`, headers, {
    expected_workflow_revision: (await workflow(page)).revision, expected_proposal_revision: open.revision,
  });
  expect(response.status(), await response.text()).toBe(200);
}

/** HR proposes and submits stages through the API (signed in as HR). */
async function hrSubmits(page: Page, headers: Headers, stages: Stage[], note: string) {
  const proposal = await createProposal(page, headers, { stages, note });
  const report = await validate(page, headers, proposal.proposal_id);
  expect(report.valid, JSON.stringify(report.issues)).toBe(true);
  const submitted = await submit(page, headers, proposal, report.content_hash);
  expect(submitted.status(), await submitted.text()).toBe(200);
}

const apiStage = (id: string, name: string, after: string, fieldId: string, label: string, forms?: string[]): Stage => ({
  stage_id: id, name, after_node_id: after, ...(forms ? { applies_to: forms } : {}),
  fields: [{ field_id: fieldId, label, kind: "TEXT" }],
});

/**
 * Idempotent setup for a test that runs on a fresh backend: the conditional version is published
 * through governance (HR proposes, the Director approves in the UI). Skipped when already active.
 */
async function ensureConditionalVersion(page: Page) {
  const headers = await signIn(page, HR);
  const stages = activeStages(await workflow(page));
  if (CONDITIONAL_NAMES.every(name => byName(stages, name))) {
    await signOut(page);
    return;
  }
  step = "setup-publish";
  await hrSubmits(page, headers, [
    ...stages,
    apiStage("e2e-m3-registry", REGISTRY_STAGE, "ACRA_REGISTRY", "registry-reference", REGISTRY_FIELD),
    apiStage("e2e-m3-llp", LLP_STAGE, "ACRA_REGISTRY", "partner-count", LLP_FIELD, ["LLP"]),
    apiStage("e2e-m3-company", COMPANY_STAGE, "DOCUMENT_IDP", "secretary-name", COMPANY_FIELD, ["COMPANY"]),
  ], "E2E M3 setup: conditional steps");
  await signOut(page);
  await signIn(page, DIRECTOR);
  await directorApprove(page, "E2E synthetic approval of the conditional steps");
  await signOut(page);
}

async function newCase(page: Page, headers: Headers, uen: string): Promise<string> {
  const created = await api(page, "POST", "/api/clm/zero-touch/cases", headers, {
    uen, country_of_incorporation: "SG", legal_name: "Synthetic M3 applicability fixture",
  });
  expect(created.status(), await created.text()).toBe(201);
  return (await created.json()).case.case_id;
}

async function onboardingRun(page: Page, caseId: string): Promise<Run> {
  const response = await api(page, "GET", `/api/clm/zero-touch/cases/${caseId}/workflows`);
  expect(response.status()).toBe(200);
  return (await response.json()).onboarding;
}

async function planNodes(page: Page, caseId: string): Promise<string[]> {
  const response = await api(page, "GET", `/api/clm/zero-touch/cases/${caseId}`);
  expect(response.status()).toBe(200);
  return (await response.json()).processing_pipeline.map((node: { node_id: string }) => node.node_id);
}

/**
 * A case created without documents has no ownership analysis or case intelligence yet; the case page
 * reads both and they answer 404 by design. Only those reads may 404 (and log a resource error).
 */
function acceptPreIntakeNotFound() {
  expect(notFound.filter(item => !/^\/api\/(onboarding|clm\/zero-touch)\/cases\/[0-9a-f-]{36}\/(ownership|intelligence)$/.test(item))).toEqual([]);
  consoleProblems = consoleProblems.filter(message => !message.includes("the server responded with a status of 404"));
  notFound = [];
}

const names = (run: Run) => run.stages.map(item => item.name);

async function expectMandatoryPlan(page: Page, caseId: string, run: Run) {
  expect(await planNodes(page, caseId)).toEqual(expect.arrayContaining(MANDATORY_NODES));
  // The run only ever holds added stages: no product node is a workflow stage.
  for (const item of run.stages) expect(MANDATORY_NODES).not.toContain(item.stage_id.toUpperCase());
}

test("Workflow governance M3 1+2+3: HR authors LLP-only and Company-only steps, the Director approves, each case gets exactly its steps", async ({ page }) => {
  test.setTimeout(300_000);

  // A case bound before any conditional content exists: its basis is never frozen (UNVERIFIED).
  step = "early-case";
  let headers = await signIn(page, RM);
  const earlyCase = await newCase(page, headers, EARLY_COMPANY_UEN);
  await signOut(page);

  step = "author";
  headers = await signIn(page, HR);
  expect(activeStages(await workflow(page)).map(item => item.name)).not.toContain(LLP_STAGE);
  await openOnboarding(page);
  await proposeChange(page, "E2E M3: an LLP-only and a Company-only step");
  await addStage(page, "Registry verification", REGISTRY_STAGE, REGISTRY_FIELD);
  await addStage(page, "Registry verification", LLP_STAGE, LLP_FIELD, ["LLP"]);
  await addStage(page, "Document verification", COMPANY_STAGE, COMPANY_FIELD, ["Company"]);
  const report = await saveAndValidate(page);
  await expect(report).toContainText("Ready to submit");
  const summary = page.getByTestId("entity-applicability");
  await expect(summary).toContainText(`${LLP_STAGE}: Only LLP (and entities whose legal form is unverified)`);
  await expect(summary).toContainText(`${COMPANY_STAGE}: Only Company (and entities whose legal form is unverified)`);
  await submitButton(page).click();
  await expect(page.getByTestId("proposal-status")).toContainText("Awaiting Director decision");
  await signOut(page);

  step = "approve";
  await signIn(page, DIRECTOR);
  await directorApprove(page, "E2E synthetic approval of the LLP-only and Company-only steps");
  const published = activeStages(await workflow(page));
  expect(byName(published, LLP_STAGE)?.applies_to).toEqual(["LLP"]);
  expect(byName(published, COMPANY_STAGE)?.applies_to).toEqual(["COMPANY"]);
  expect(byName(published, REGISTRY_STAGE)?.applies_to ?? null).toBeNull();
  await signOut(page);

  step = "cases";
  headers = await signIn(page, RM);

  // Scenario 2 (and 1's mechanism): the Mock company receives its Company-only step, never the LLP-only one.
  const company = await newCase(page, headers, COMPANY_UEN);
  const companyRun = await onboardingRun(page, company);
  expect(names(companyRun)).toEqual([REGISTRY_STAGE, COMPANY_STAGE]);
  expect(companyRun.applicability).toMatchObject({
    status: "REGISTRY_BOUND", legal_form: "COMPANY", source_environment: "MOCK", frozen: true, effective_legal_form: "COMPANY",
  });
  await expectMandatoryPlan(page, company, companyRun);

  // A bound business / partnership receives neither the LLP-only nor the Company-only step.
  const garden = await newCase(page, headers, GARDEN_UEN);
  const gardenRun = await onboardingRun(page, garden);
  expect(names(gardenRun)).toEqual([REGISTRY_STAGE]);
  expect(gardenRun.applicability).toMatchObject({ status: "REGISTRY_BOUND", legal_form: "BUSINESS_PARTNERSHIP" });
  await expectMandatoryPlan(page, garden, gardenRun);

  // Scenario 3: an unknown entity, and a case bound before the conditions, keep every obligation.
  const unknown = await newCase(page, headers, UNKNOWN_UENS[0]);
  for (const caseId of [unknown, earlyCase]) {
    const run = await onboardingRun(page, caseId);
    expect(names(run).sort()).toEqual([...CONDITIONAL_NAMES].sort());
    expect(run.applicability ?? null).toBeNull(); // never frozen: every condition applies
    await expectMandatoryPlan(page, caseId, run);
  }

  step = "company-case-ui";
  await page.goto(`/cases/${company}`);
  await expect(page.getByTestId("run-applicability-basis")).toHaveText("Registry-bound (Mock): Company");
  await expect(page.getByTestId("run-applicability")).toContainText("The basis is frozen for this run.");
  await expect(disclosure(page, COMPANY_STAGE)).toHaveCount(1);
  await expect(disclosure(page, REGISTRY_STAGE)).toHaveCount(1);
  await expect(disclosure(page, LLP_STAGE)).toHaveCount(0);
  acceptPreIntakeNotFound();

  step = "unknown-case-ui";
  await page.goto(`/cases/${unknown}`);
  for (const name of CONDITIONAL_NAMES) await expect(disclosure(page, name)).toHaveCount(1);
  await expect(page.getByTestId("run-applicability")).toHaveCount(0);
  acceptPreIntakeNotFound();
});

test("Workflow governance M3 5: conditions cannot reach before the registry, cannot narrow an all-entity required step, and never remove UBO or risk nodes", async ({ page }) => {
  test.setTimeout(300_000);
  await ensureConditionalVersion(page);

  step = "api-refusals";
  const headers = await signIn(page, HR);
  const stages = activeStages(await workflow(page));
  const registry = byName(stages, REGISTRY_STAGE)!;
  const proposal = await createProposal(page, headers, { note: "E2E M3: refused conditional edits" });
  // Conditional content before the registry anchor is refused.
  for (const after of ["CASE_START", "GOLDTIER_SEARCH"]) {
    const early = apiStage(`e2e-m3-early-${after.toLowerCase().replace("_", "-")}`, "E2E M3 early condition", after, "early", "Early", ["LLP"]);
    const report = await validate(page, headers, proposal.proposal_id, [...stages, early]);
    expect(report.valid).toBe(false);
    expect(report.issues.map((item: { message: string }) => item.message)).toContain(BEFORE_REGISTRY_ISSUE);
  }
  // An unconditional required stage cannot become conditional (RR-8), at validate and at submit.
  const narrowed = stages.map(item => item.stage_id === registry.stage_id ? { ...item, applies_to: ["COMPANY", "LLP"] } : item);
  const narrowedReport = await validate(page, headers, proposal.proposal_id, narrowed);
  expect(narrowedReport.valid).toBe(false);
  expect(narrowedReport.issues.map((item: { rule: string | null }) => item.rule)).toContain("RR-8");
  const updated = await api(page, "PUT", `${WF}/proposals/${proposal.proposal_id}`, headers, {
    expected_workflow_revision: (await workflow(page)).revision, expected_proposal_revision: proposal.revision, stages: narrowed,
  });
  expect(updated.status(), await updated.text()).toBe(200);
  const stored = await updated.json();
  const storedReport = await validate(page, headers, proposal.proposal_id);
  const refused = await submit(page, headers, stored, storedReport.content_hash);
  expect(refused.status()).toBeGreaterThanOrEqual(400);
  expect((await refused.json()).detail.code).toBe("WORKFLOW_REQUIRED_OBLIGATION_WEAKENED");
  await withdraw(page, headers, proposal.proposal_id);
  expect(activeStages(await workflow(page))).toEqual(stages); // nothing was published

  step = "ui-refusals";
  await openOnboarding(page);
  await proposeChange(page, "E2E M3: try the refused conditional edits in the editor");
  await stagesList(page).getByRole("button", { name: "Add stage after Case created", exact: true }).click();
  await expect(stageConditions(page)).toContainText(BEFORE_REGISTRY);
  await expect(stageConditions(page).getByLabel("Only these legal forms")).toBeDisabled();
  await stagesList(page).getByRole("button", { name: new RegExp(`^\\d+\\. ${REGISTRY_STAGE}$`) }).click();
  await expect(stageConditions(page).getByLabel("Only these legal forms")).toBeDisabled();
  await expect(stageConditions(page)).toContainText("RR-8: where a required step or field applies cannot be narrowed.");
  await page.getByRole("button", { name: "Withdraw" }).click();
  await expect(page.getByTestId("propose-change")).toBeVisible();
  await signOut(page);

  step = "mandatory-nodes";
  const rm = await signIn(page, RM);
  for (const uen of [LATE_COMPANY_UEN, UNKNOWN_UENS[1]]) {
    const caseId = await newCase(page, rm, uen);
    const run = await onboardingRun(page, caseId);
    expect(names(run)).toContain(REGISTRY_STAGE);
    await expectMandatoryPlan(page, caseId, run);
  }
});

test("Workflow governance M3 4: restore, reset and emergency fallback keep the broadest applicability; narrowing is refused RR-8", async ({ page }) => {
  test.setTimeout(300_000);
  await ensureConditionalVersion(page);

  step = "broaden";
  let headers = await signIn(page, HR);
  const before = await workflow(page);
  const narrowVersion: number = before.active_version;
  const llp = byName(activeStages(before), LLP_STAGE)!;
  expect(llp.applies_to).toEqual(["LLP"]);
  const broadened = activeStages(before).map(item => item.stage_id === llp.stage_id ? { ...item, applies_to: ["COMPANY", "LLP"] } : item);
  await hrSubmits(page, headers, broadened, "E2E M3: the LLP step also applies to companies");
  await signOut(page);
  await signIn(page, DIRECTOR);
  await directorApprove(page, "E2E synthetic approval of the broadened LLP step");
  await signOut(page);

  step = "restore-reset";
  headers = await signIn(page, HR);
  const broad = await workflow(page);
  expect(byName(activeStages(broad), LLP_STAGE)?.applies_to).toEqual(["COMPANY", "LLP"]);
  const restore = await createProposal(page, headers, { kind: "RESTORE_VERSION", restore_target_version: narrowVersion });
  expect(byName(restore.stages, LLP_STAGE)?.applies_to).toEqual(["COMPANY", "LLP"]); // never the narrower set
  await withdraw(page, headers, restore.proposal_id);
  const reset = await createProposal(page, headers, { kind: "RESET_TO_DEFAULT" });
  expect(byName(reset.stages, LLP_STAGE)?.applies_to).toEqual(["COMPANY", "LLP"]);
  await withdraw(page, headers, reset.proposal_id);

  step = "rr8";
  const narrowing = await createProposal(page, headers, { stages: activeStages(broad).map(item => item.stage_id === llp.stage_id ? { ...item, applies_to: ["LLP"] } : item) });
  const report = await validate(page, headers, narrowing.proposal_id);
  expect(report.valid).toBe(false);
  expect(report.issues.map((item: { rule: string | null }) => item.rule)).toContain("RR-8");
  const refused = await submit(page, headers, narrowing, report.content_hash);
  expect((await refused.json()).detail.code).toBe("WORKFLOW_REQUIRED_OBLIGATION_WEAKENED");
  await withdraw(page, headers, narrowing.proposal_id);
  await signOut(page);

  step = "fallback";
  await signIn(page, DIRECTOR);
  await openOnboarding(page);
  const panel = page.getByTestId("emergency-fallback");
  await panel.getByRole("button", { name: "Start emergency fallback" }).click();
  await panel.getByLabel("A published version").check();
  await panel.getByRole("combobox").selectOption(String(narrowVersion));
  await panel.getByLabel(/^Reason \(required/).fill(`E2E synthetic emergency fallback to version ${narrowVersion}`);
  await panel.getByLabel("I understand this publishes without approval and HR will be notified.").check();
  await panel.getByRole("button", { name: "Publish emergency fallback" }).click();
  const next = broad.active_version + 1;
  await expect(page.getByRole("status").filter({ hasText: `Emergency fallback published: version ${next} is now active` })).toBeVisible();
  const after = await workflow(page);
  expect(after.active_version).toBe(next);
  // The safe target keeps every obligation in force at its broadest applicability.
  expect(byName(activeStages(after), LLP_STAGE)?.applies_to).toEqual(["COMPANY", "LLP"]);
  expect(byName(activeStages(after), COMPANY_STAGE)?.applies_to).toEqual(["COMPANY"]);
  expect(byName(activeStages(after), REGISTRY_STAGE)?.applies_to ?? null).toBeNull();
  expect(after.governance.version_provenance.at(-1).origin).toBe("EMERGENCY_FALLBACK");
});
