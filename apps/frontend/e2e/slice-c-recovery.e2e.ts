import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test, type Page } from "@playwright/test";
import { createBrowserNetworkPolicy, handleBrowserRoute } from "../playwright.config";
import { openStage } from "./stage-disclosures";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const fixtures = path.join(root, "apps/backend/tests/fixtures/uat");
const cleanName = "MERLION CIRCULAR LABS PTE. LTD.";
const cleanUen = "202400001A";
let violations: string[];

test.beforeEach(async ({ page }) => {
  violations = [];
  const policy = createBrowserNetworkPolicy({
    frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!,
    backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false,
  });
  await page.route("**/*", (route) => handleBrowserRoute(route, policy, violations));
  await page.goto("/");
  await page.getByLabel("User ID").fill("maya-lim");
  await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
});
test.afterEach(() => expect(violations).toEqual([]));

async function summary(page: Page, caseId: string) {
  const response = await page.request.get(`/api/clm/zero-touch/cases/${caseId}`);
  if (response.status() !== 200) {
    const code = await response.json().then((body) => body.detail?.code ?? "NO_SAFE_CODE").catch(() => "UNTYPED_RESPONSE");
    const bodyBytes = (await response.body()).length;
    throw new Error(`Summary GET status=${response.status()} type=${response.headers()["content-type"] ?? "NONE"} bytes=${bodyBytes} code=${code}`);
  }
  return response.json();
}

async function metadata(page: Page) {
  const response = await page.request.get("/api/__slice_c/recovery-metadata");
  expect(response.status()).toBe(200);
  const evidence = await response.json();
  expect(evidence.classification).toBe("SYNTHETIC_OFFLINE");
  expect(evidence.external_calls).toBe(0);
  expect(evidence.operations).not.toContain("AMEND");
  return evidence;
}

function textProfile(overrides: Record<string, string> = {}) {
  const fields = { "Legal Name": cleanName, UEN: cleanUen,
    "Registered Address": "18 INNOVATION WAY, #04-01, 018956, SG", Country: "SG", ...overrides };
  return { name: "synthetic-slice-c.txt", mimeType: "text/plain",
    buffer: Buffer.from("SYNTHETIC TEST DATA\n" + Object.entries(fields).map(([key, value]) => `${key}: ${value}`).join("\n")) };
}

async function create(page: Page, file: string | ReturnType<typeof textProfile> = "clean-company-profile.pdf", uen = cleanUen, status = "WAITING_FOR_REVIEW") {
  await page.getByRole("link", { name: "New onboarding", exact: true }).click();
  await page.getByLabel("Jurisdiction", { exact: true }).selectOption("SG");
  await page.getByLabel("Company Legal Name", { exact: true }).fill(cleanName);
  await page.getByLabel("Registration ID / UEN").fill(uen);
  await page.locator("#home-document").setInputFiles(typeof file === "string" ? path.join(fixtures, file) : file);
  await page.getByRole("button", { name: "Create onboarding", exact: true }).click();
  await expect(page).toHaveURL(/\/new-onboarding\/[0-9a-f-]{36}$/i);
  const caseId = page.url().split("/").at(-1)!;
  await expect.poll(async () => (await summary(page, caseId)).status).toBe(status);
  await page.getByRole("button", { name: "Open full case", exact: true }).click();
  await expect(page).toHaveURL(`/cases/${caseId}`);
  return caseId;
}

async function navigateAction(page: Page, caseId: string, target: string) {
  const current = await summary(page, caseId);
  const action = current.interventions.flatMap((item: any) => item.evidence_actions ?? [])
    .find((item: any) => item.target === target);
  expect(action, `Server must expose a current ${target} action`).toBeTruthy();
  const control = page.getByRole("button", { name: action.label, exact: true });
  await expect(control).toHaveCount(1);
  await control.focus();
  await page.keyboard.press("Enter");
}

async function classify(page: Page, caseId: string) {
  const current = await summary(page, caseId);
  if (current.active_exceptions.some((item: any) => item.blocker_code === "GOLDTIER_CLASSIFICATION_REQUIRED")) {
    await navigateAction(page, caseId, "CLASSIFICATION");
    await expect(page.locator("#case-target-classification")).toBeFocused();
  }
  await openStage(page, "Submission readiness");
  await page.getByLabel("KYC customer type", { exact: true }).selectOption("Company - Private");
  await page.getByLabel("Client segment", { exact: true }).selectOption("Corporate");
  const response = page.waitForResponse((result) => result.request().method() === "PUT"
    && result.url().endsWith("/target-classification"));
  await page.getByRole("button", { name: "Save target classification", exact: true }).click();
  expect((await response).status()).toBe(200);
}

async function confirm(page: Page, caseId: string, sandbox = false) {
  await expect.poll(async () => (await summary(page, caseId)).active_exceptions.map((item: any) => item.blocker_code))
    .toEqual(["TARGET_CONFIRMATION_REQUIRED"]);
  await openStage(page, "Final review & send");
  await expect(page.locator("#case-review-and-send")).toBeVisible();
  const response = page.waitForResponse((result) => result.request().method() === "POST"
    && result.url().endsWith("/target-confirmation"));
  await page.getByRole("button", { name: sandbox ? "Confirm and send to GoldTier sandbox" : "Confirm and send to Mock GoldTier", exact: true }).click();
  expect((await response).status()).toBe(200);
}

async function assertHistorical(page: Page, caseId: string, codes: string[]) {
  const current = await summary(page, caseId);
  expect(current.active_exceptions.filter((item: any) => codes.includes(item.blocker_code))).toEqual([]);
  for (const code of codes) {
    expect(current.historical_exceptions.some((item: any) => item.blocker_code === code)).toBe(true);
  }
  await openStage(page, "Historical / resolved issues");
  const history = page.locator(".intervention-history");
  await expect(history).toHaveCount(1);
  await history.locator("summary").click();
  for (const code of codes) await expect(history).toContainText(code);
}

test("Slice C optional Amend and NO_MATCH complete with neutral progress", { tag: "@slice-c-optional-amend" }, async ({ page }) => {
  const caseId = await create(page);
  await expect(page.getByText(/synthetic offline/i).first()).toBeVisible();
  await openStage(page, "Historical / resolved issues");
  await page.getByRole("button", { name: "Show processing details", exact: true }).click();
  await expect(page.getByText("No existing customer found. Continuing as a new customer.", { exact: true }).first()).toBeVisible();
  await classify(page, caseId);
  const before = await summary(page, caseId);
  const completed = before.processing_pipeline.filter((node: any) => ["COMPLETE", "SKIPPED"].includes(node.status)).length;
  await expect(page.getByRole("progressbar")).toHaveAttribute("aria-valuenow", String(Math.round(completed / before.processing_pipeline.length * 100)));
  await confirm(page, caseId, true);
  await expect.poll(async () => (await summary(page, caseId)).status).toBe("COMPLETED");
  const done = await summary(page, caseId);
  expect(done.case.goldtier_result.amend_status).toBe("AMEND_NOT_REQUIRED");
  const target = done.processing_pipeline.find((node: any) => node.node_id === "FINAL_REVIEW_SEND");
  expect(target.children.find((node: any) => node.node_id === "GOLDTIER_AMEND").status).toBe("SKIPPED");
  await expect(page.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "100");
  expect((await metadata(page)).operations).toEqual(["SEARCH", "SEARCH", "SHELL", "POLICY", "READBACK"]);
  await assertHistorical(page, caseId, ["GOLDTIER_CLASSIFICATION_REQUIRED", "TARGET_CONFIRMATION_REQUIRED"]);
});

test("Slice C stale policy rebind preserves selection and resumes", { tag: "@slice-c-stale-policy" }, async ({ page }) => {
  const caseId = await create(page);
  await classify(page, caseId);
  const before = await summary(page, caseId);
  expect(before.case.policy_rebind.configuration_status).toBe("REQUIRES_REBIND");
  await openStage(page, "Submission readiness");
  await page.getByLabel("Rebind rationale", { exact: true }).fill("Replace synthetic retained legacy target configuration.");
  const response = page.waitForResponse((result) => result.request().method() === "POST"
    && result.url().endsWith("/policy-rebind"));
  await page.getByRole("button", { name: "Rebind accepted Singapore POC configuration", exact: true }).click();
  expect((await response).status()).toBe(200);
  await expect(page.getByLabel("Latest policy rebind receipt", { exact: true })).toBeVisible();
  const rebound = await summary(page, caseId);
  expect(rebound.case.policy_snapshot_revision).toBe(2);
  expect(rebound.target_classification.kyc_customer_type.selected_value).toBe("Company - Private");
  expect((await metadata(page)).operations).toEqual(["SEARCH"]);
  await confirm(page, caseId, true);
  await expect.poll(async () => (await summary(page, caseId)).status).toBe("COMPLETED");
});

test("Slice C retained finalization recovery makes no target replay", { tag: "@slice-c-retained-recovery" }, async ({ page }) => {
  const caseId = await create(page);
  await classify(page, caseId);
  await confirm(page, caseId, true);
  await expect.poll(async () => (await summary(page, caseId)).status).toBe("RECOVERY_PENDING");
  const before = await metadata(page);
  expect(before.operations).toEqual(["SEARCH", "SEARCH", "SHELL", "POLICY", "READBACK"]);
  expect((await summary(page, caseId)).target_submission.state).toBe("FINALIZATION_PENDING");
  let resumeCalls = 0;
  page.on("request", (request) => {
    if (request.method() === "POST" && request.url().endsWith("/resume")) resumeCalls += 1;
  });
  await openStage(page, "Final review & send");
  await expect(page.getByText("Retained target operations are resolved. Backend recovery can finish the approved submission without repeating them.", { exact: true })).toBeVisible();
  expect(resumeCalls).toBe(0);
  await openStage(page, "GoldTier submission package");
  const resume = page.waitForResponse((result) => result.request().method() === "POST"
    && result.url().endsWith("/resume"));
  await page.getByRole("button", { name: "Complete safe recovery", exact: true }).focus();
  await page.keyboard.press("Enter");
  const resumed = await resume;
  expect(resumed.status()).toBe(200);
  expect((await resumed.json()).status).toBe("COMPLETED");
  expect(resumeCalls).toBe(1);
  // Completion retires the active target stage; its receipt must be revealed explicitly.
  await expect(page.getByRole("button", { name: /^GoldTier submission package/ }))
    .toHaveAttribute("aria-expanded", "false");
  await openStage(page, "GoldTier submission package");
  await expect(page.getByText("Completed POC workflow", { exact: true })).toBeVisible();
  expect((await metadata(page)).operations).toEqual(before.operations);
  expect((await summary(page, caseId)).active_exceptions).toEqual([]);
});

test("Slice C failed Search exposes bounded read-only recheck", { tag: "@slice-c-search-recheck" }, async ({ page }) => {
  const caseId = await create(page);
  await classify(page, caseId);
  await expect.poll(async () => (await summary(page, caseId)).status).toBe("TECHNICAL_FAILURE");
  const blocked = await summary(page, caseId);
  expect(blocked.clm.target_search_checkpoint.disposition).toBe("FAILED");
  expect((await metadata(page)).operations).toEqual(["SEARCH"]);
  await openStage(page, "Registry verification");
  expect(blocked.case.registry_acquisition.status).toBe("COMPLETE");
  expect(blocked.processing_pipeline.find((node: any) => node.node_id === "ACRA_REGISTRY").status)
    .toBe("COMPLETE");
  await expect(page.locator("#registry-state-heading")).toHaveCount(0);
  await expect(page.locator("#registry-provenance-heading")).toBeVisible();
  await expect(page.locator(".identity-correction")).toBeVisible();
  await page.getByRole("button", { name: "Edit UEN", exact: true }).click();
  await page.getByLabel("Singapore UEN", { exact: true }).fill(cleanUen);
  const response = page.waitForResponse((result) => result.request().method() === "POST"
    && result.url().endsWith("/registry-identity"));
  await page.getByRole("button", { name: "Verify UEN and resume", exact: true }).click();
  expect((await response).status()).toBe(200);
  await expect.poll(async () => (await summary(page, caseId)).clm.target_search_checkpoint.disposition).toBe("NO_MATCH");
  expect((await metadata(page)).operations).toEqual(["SEARCH", "SEARCH"]);
  await confirm(page, caseId, true);
  await expect.poll(async () => (await summary(page, caseId)).status).toBe("COMPLETED");
});

async function resolveDiscrepancy(page: Page, file: string | ReturnType<typeof textProfile>) {
    const caseId = await create(page, file);
    const before = await summary(page, caseId);
    const codes = before.active_exceptions.filter((item: any) => item.stage === "DOCUMENT").map((item: any) => item.blocker_code);
    expect(codes.length).toBeGreaterThan(0);
    await navigateAction(page, caseId, "DOCUMENTS");
    await expect(page.locator("#case-evidence-documents")).toBeFocused();
    await expect(page.getByRole("button", { name: /Confirm and send/ })).toHaveCount(0);
    const response = page.waitForResponse((result) => result.request().method() === "POST"
      && result.url().endsWith("/resolve"));
    await page.getByRole("button", { name: "Keep registry value", exact: true }).click();
    expect((await response).status()).toBe(200);
    await expect.poll(async () => (await summary(page, caseId)).active_exceptions.filter((item: any) => item.stage === "DOCUMENT")).toEqual([]);
    await expect(page.getByRole("button", { name: "Keep registry value", exact: true })).toHaveCount(0);
    await classify(page, caseId);
    await confirm(page, caseId);
    await expect.poll(async () => (await summary(page, caseId)).status).toBe("COMPLETED");
    await assertHistorical(page, caseId, codes);
}

test("Slice C legal name discrepancy resolves through document owner and history", async ({ page }) => {
  await resolveDiscrepancy(page, "legal-name-mismatch.pdf");
});
test("Slice C address discrepancy resolves through document owner and history", async ({ page }) => {
  await resolveDiscrepancy(page, "address-mismatch.pdf");
});
test("Slice C country discrepancy resolves through document owner and history", async ({ page }) => {
  await resolveDiscrepancy(page, textProfile({ Country: "AU" }));
});

async function replaceAfterCorrection(page: Page, scenario: { file: string; field: string; value: string }) {
    const caseId = await create(page, scenario.file);
    const before = await summary(page, caseId);
    const codes = before.active_exceptions.filter((item: any) => item.stage === "DOCUMENT").map((item: any) => item.blocker_code);
    await navigateAction(page, caseId, "DOCUMENTS");
    await page.getByRole("button", { name: `Record ${scenario.field.replaceAll("_", " ")} correction`, exact: true }).click();
    await expect(page.getByLabel("Correction", { exact: true })).toBeFocused();
    await page.getByLabel("Correction", { exact: true }).fill(scenario.value);
    const review = page.waitForResponse((result) => result.request().method() === "POST"
      && result.url().includes("/review"));
    await page.getByRole("button", { name: `Save ${scenario.field.replaceAll("_", " ")} correction`, exact: true }).click();
    expect((await review).status()).toBe(200);
    await expect(page.getByText(/Correction retained, but replacement evidence is still required/)).toBeVisible();
    expect((await summary(page, caseId)).active_exceptions.some((item: any) => item.stage === "DOCUMENT")).toBe(true);
    const replacement = page.waitForResponse((result) => result.request().method() === "POST"
      && result.url().includes("/replace"));
    await page.getByLabel("Replace current document", { exact: true }).setInputFiles(path.join(fixtures, "clean-company-profile.pdf"));
    expect((await replacement).status()).toBe(200);
    await expect(page.locator(".document-card--history")).toHaveCount(1);
    await expect.poll(async () => (await summary(page, caseId)).active_exceptions.filter((item: any) => item.stage === "DOCUMENT")).toEqual([]);
    await classify(page, caseId);
    await confirm(page, caseId);
    await expect.poll(async () => (await summary(page, caseId)).status).toBe("COMPLETED");
    await assertHistorical(page, caseId, codes);
}

test("Slice C ambiguous extraction correction retains blocker until replacement evidence", async ({ page }) => {
  await replaceAfterCorrection(page, { file: "low-confidence.pdf", field: "legal_name", value: cleanName });
});
test("Slice C missing field correction retains blocker until replacement evidence", async ({ page }) => {
  await replaceAfterCorrection(page, { file: "missing-field.pdf", field: "country_of_incorporation", value: "SG" });
});


test("Slice C resolved mixed sibling leaves only current missing-field policy", async ({ page }) => {
  const caseId = await create(page, textProfile({ "Legal Name": "OTHER NAME", Country: "" }));
  await openStage(page, "Document verification");
  const response = page.waitForResponse((result) => result.request().method() === "POST"
    && result.url().endsWith("/resolve"));
  await page.getByRole("button", { name: "Keep registry value", exact: true }).click();
  expect((await response).status()).toBe(200);
  const pending = await summary(page, caseId);
  expect(pending.active_exceptions.map((item: any) => item.blocker_code))
    .toEqual(["DOCUMENT_REQUIRED_FIELD_MISSING"]);
  expect(pending.interventions.flatMap((item: any) => item.decisions ?? [])
    .map((item: any) => item.metadata.blocker_code)).toEqual(["DOCUMENT_REQUIRED_FIELD_MISSING"]);
  const current = page.locator(".intervention-card");
  await expect(current).toHaveCount(1);
  await current.getByText("Why is this blocked?", { exact: true }).click();
  await expect(current).toContainText("DOCUMENT_REQUIRED_FIELD_MISSING");
  await expect(current).not.toContainText("DOCUMENT_SOURCE_CONFLICT");
  await expect(current).not.toContainText("retained hard stop");
  expect(pending.historical_exceptions.some((item: any) =>
    item.blocker_code === "DOCUMENT_SOURCE_CONFLICT" && item.status === "RESOLVED")).toBe(true);
  await openStage(page, "Document verification");
  const replacement = page.waitForResponse((result) => result.request().method() === "POST"
    && result.url().includes("/replace"));
  await page.getByLabel("Replace current document", { exact: true })
    .setInputFiles(path.join(fixtures, "clean-company-profile.pdf"));
  expect((await replacement).status()).toBe(200);
  await classify(page, caseId);
  await confirm(page, caseId);
  await expect.poll(async () => (await summary(page, caseId)).status).toBe("COMPLETED");
  await assertHistorical(page, caseId, ["DOCUMENT_SOURCE_CONFLICT", "DOCUMENT_REQUIRED_FIELD_MISSING"]);
});
