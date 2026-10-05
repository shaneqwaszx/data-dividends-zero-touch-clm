import { expect, test, type Page } from "@playwright/test";
import path from "node:path";
import { createBrowserNetworkPolicy, handleBrowserRoute } from "../playwright.config";
import type { TargetStatusCheckResult } from "../src/api";
import type { ZeroTouchCaseSummary } from "../src/types";
import { openStage } from "./stage-disclosures";

const syntheticName = "ZERO TOUCH POC ACCEPTANCE TESTS3";
const syntheticUen = "202698765Z";
const syntheticDocument = {
  name: "synthetic-s3-submission.txt", mimeType: "text/plain",
  buffer: Buffer.from([
    `Legal Name: ${syntheticName}`, `UEN: ${syntheticUen}`,
    "Registered Address: 1 SYNTHETIC ACCEPTANCE WAY, #01-01, 018956, SG", "Country: SG",
    "Shareholder | Type | Percentage | Owned entity registration number | As of",
    `POC Synthetic Owner A | NATURAL_PERSON | 70% | ${syntheticUen} | 2026-10-04`,
    `POC Synthetic Owner B | NATURAL_PERSON | 30% | ${syntheticUen} | 2026-10-04`,
  ].join("\n")),
};

let violations: string[];
test.beforeEach(async ({ page }) => {
  violations = [];
  const policy = createBrowserNetworkPolicy({
    frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!, backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false,
  });
  await page.route("**/*", (route) => handleBrowserRoute(route, policy, violations));
});
test.afterEach(() => expect(violations).toEqual([]));

async function readSummary(page: Page, caseId: string): Promise<ZeroTouchCaseSummary> {
  const response = await page.request.get(`/api/clm/zero-touch/cases/${caseId}`);
  expect(response.status()).toBe(200); return response.json();
}
async function counts(page: Page): Promise<{ fixture: string; calls: Record<string, number>; external_calls: number }> {
  const response = await page.request.get("/api/__s3/sandbox-counts");
  expect(response.status()).toBe(200); return response.json();
}

async function prepareReview(page: Page, existing = false): Promise<string> {
  await page.goto("/");
  await page.getByLabel("User ID").fill("maya-lim");
  await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("link", { name: "New onboarding", exact: true }).click();
  await page.getByLabel("Jurisdiction", { exact: true }).selectOption("SG");
  await page.getByLabel("Company Legal Name", { exact: true }).fill(syntheticName);
  await page.getByLabel("Registration ID / UEN").fill(syntheticUen);
  await page.locator("#home-document").setInputFiles(existing ? {
    ...syntheticDocument,
    buffer: Buffer.from(syntheticDocument.buffer.toString().replace(
      `Legal Name: ${syntheticName}`, `Legal Name: ${syntheticName} DOCUMENT`,
    )),
  } : syntheticDocument);
  await page.getByRole("button", { name: "Create onboarding", exact: true }).click();
  await expect(page).toHaveURL(/\/new-onboarding\/[0-9a-f-]{36}$/i);
  const caseId = page.url().split("/").at(-1)!;
  await expect.poll(async () => (await readSummary(page, caseId)).status).toBe("WAITING_FOR_REVIEW");
  await page.getByRole("button", { name: "Open full case", exact: true }).click();
  await expect(page).toHaveURL(`/cases/${caseId}`);
  await expect(page.locator(".document-card:not(.document-card--history)")).toHaveCount(1);
  if (existing) {
    await openStage(page, "Document verification");
    const decision = page.waitForResponse((response) => response.request().method() === "POST"
      && response.url().endsWith("/reviews"));
    await page.getByRole("button", { name: "Record legal name correction", exact: true }).click();
    await page.getByLabel("Correction", { exact: true }).fill(syntheticName);
    await page.getByRole("button", { name: "Save legal name correction", exact: true }).click();
    expect((await decision).status()).toBe(200);
    await expect.poll(async () => (await readSummary(page, caseId)).current_stage)
      .toBe("GOLDTIER_SEARCH");
    await openStage(page, "Registry verification");
    await expect(page.getByRole("button", { name: "Correct identity and recheck", exact: true }))
      .toHaveCount(0);
    await page.getByLabel("Existing customer confirmation rationale").fill(
      "Compared synthetic retained candidate with independent registry and corrected document.",
    );
    const confirmation = page.waitForResponse((response) => response.request().method() === "POST"
      && response.url().endsWith("/confirm-existing-customer"));
    await page.getByRole("button", { name: "Confirm existing GoldTier customer", exact: true }).click();
    expect((await confirmation).status()).toBe(200);
    const confirmed = await readSummary(page, caseId);
    expect(confirmed.clm.target_search_checkpoint?.disposition).toBe("CONFIRMED_EXISTING");
    expect(confirmed.clm.target_search_checkpoint?.selected_party_id).toBe("SYNTHETIC-GT-S3");
    const before = await counts(page);
    expect(before.calls).toEqual({ SEARCH: 1, SHELL: 0, POLICY: 0, AMEND: 0, READBACK: 0 });
    expect(before.external_calls).toBe(0);
    if (confirmed.status === "PENDING_INPUTS") {
      await openStage(page, "Document verification");
      await page.getByRole("button", { name: "Continue evidence review", exact: true }).click();
    } else {
      expect(confirmed.current_stage).toBe("OWNERSHIP");
    }
  }
  await openStage(page, "Submission readiness");
  await page.getByLabel("KYC customer type", { exact: true }).selectOption("Company - Private");
  await page.getByLabel("Client segment", { exact: true }).selectOption("Corporate");
  const classification = page.waitForResponse((response) => response.request().method() === "PUT" && response.url().endsWith("/target-classification"));
  await page.getByRole("button", { name: "Save target classification", exact: true }).click();
  expect((await classification).status()).toBe(200);
  await openStage(page, "Ownership & UBO");
  const form = page.locator(".manual-ownership");
  await expect(form.getByRole("heading", { name: "Review or edit ownership evidence", exact: true })).toBeVisible();
  await form.getByLabel("Ownership source decision", { exact: true }).selectOption("CURRENT_EVIDENCE");
  await expect(form.getByLabel("Economic interest %", { exact: true }).nth(0)).toHaveValue(/^(70|30)(?:\.0+)?$/);
  await expect(form.getByLabel("Economic interest %", { exact: true }).nth(1)).toHaveValue(/^(70|30)(?:\.0+)?$/);
  await form.getByLabel("As-of date").fill("2026-10-04");
  await form.getByLabel("Reviewer note (optional)").fill("Synthetic creator reviewed both matching explicit document owners and retained current ownership evidence.");
  const decision = page.waitForResponse((response) => response.request().method() === "POST" && response.url().endsWith("/manual-ownership-evidence"));
  await form.getByRole("button", { name: "Submit manual ownership evidence", exact: true }).click();
  expect((await decision).status()).toBe(200);
  await openStage(page, "Final review & send");
  await expect(page.getByRole("button", { name: "Confirm and send to GoldTier sandbox", exact: true })).toBeEnabled();
  const prepared = await readSummary(page, caseId);
  expect(prepared.clm.submission_plan.environment).toBe("SANDBOX");
  expect(prepared.clm.submission_plan.provider_classification).toBe("SANDBOX_PARTIAL");
  expect(prepared.target_submission?.state).toBe("NOT_SUBMITTED");
  const before = await counts(page);
  expect(before.external_calls).toBe(0); expect(before.calls.SHELL).toBe(0);
  expect(before.calls.POLICY).toBe(0); expect(before.calls.AMEND).toBe(0);
  return caseId;
}

test("post-closeout existing-customer confirmation preserves independent review and skips writes", { tag: "@s3-sandbox-existing-customer" }, async ({ page }) => {
  const caseId = await prepareReview(page, true);
  const response = page.waitForResponse((value) => value.request().method() === "POST"
    && value.url().endsWith("/target-confirmation"));
  await page.getByRole("button", { name: "Confirm and send to GoldTier sandbox", exact: true }).click();
  expect((await response).status()).toBe(200);
  await expect.poll(async () => (await readSummary(page, caseId)).target_submission?.state)
    .toBe("SUBMISSION_CONFIRMED");
  const result = await counts(page);
  expect(result.calls).toEqual({ SEARCH: 1, SHELL: 0, POLICY: 0, AMEND: 0, READBACK: 1 });
  expect(result.external_calls).toBe(0);
  const retained = await readSummary(page, caseId);
  expect(retained.clm.target_search_checkpoint?.disposition).toBe("CONFIRMED_EXISTING");
  expect(retained.case.goldtier_result?.party_id).toBe("SYNTHETIC-GT-S3");
});

async function submitAndInspect(page: Page, mode: "success" | "uncertain-policy" | "failed-policy") {
  const caseId = await prepareReview(page);
  let checkRequests = 0;
  page.on("request", (request) => {
    if (request.method() === "POST" && request.url().endsWith("/target-status-check")) checkRequests += 1;
  });
  const automaticCheck = mode === "uncertain-policy"
    ? page.waitForResponse((response) => response.request().method() === "POST" && response.url().endsWith("/target-status-check")) : null;
  const confirmation = page.waitForResponse((response) => response.request().method() === "POST" && response.url().endsWith("/target-confirmation"));
  await page.getByRole("button", { name: "Confirm and send to GoldTier sandbox", exact: true }).click();
  expect((await confirmation).status()).toBe(200);
  const state = mode === "success" ? "SUBMISSION_CONFIRMED"
    : mode === "uncertain-policy" ? "SUBMISSION_OUTCOME_UNCERTAIN" : "SUBMISSION_FAILED";
  await expect.poll(async () => (await readSummary(page, caseId)).target_submission?.state).toBe(state);
  const review = page.locator("#case-review-and-send");
  await expect(review).toBeVisible();
  const title = state === "SUBMISSION_CONFIRMED" ? "Submission confirmed"
    : state === "SUBMISSION_FAILED" ? "Submission failed" : "Submission outcome uncertain";
  if (automaticCheck) {
    const response = await automaticCheck; expect(response.status()).toBe(200);
    const observation = await response.json() as TargetStatusCheckResult;
    expect(observation.result).toBe("CUSTOMER_IDENTITY_VERIFIED");
    await expect(review.getByText(observation.message, { exact: true })).toBeVisible();
    await expect(review.getByText("Customer identity checking does not establish Policy completion, GoldTier approval or KYC completion.", { exact: true })).toBeVisible();
  }
  await expect(review.getByRole("heading", { name: title, exact: true })).toBeVisible();
  await expect(review.getByRole("button", { name: /Confirm and send|Retry|Save draft/ })).toHaveCount(0);
  if (mode === "success") {
    await expect(review.locator('[aria-label="Completed GoldTier submission"] dt').first()).toHaveText("GoldTier ID");
    await expect(review.getByRole("button", { name: "Verify in GoldTier", exact: true })).toBeEnabled();
  } else await expect(review.getByText("Retained GoldTier ID: SYNTHETIC-GT-S3", { exact: true })).toBeVisible();
  const current = await readSummary(page, caseId);
  expect(current.target_submission?.goldtier_id).toBe("SYNTHETIC-GT-S3");
  if (mode === "uncertain-policy") {
    expect(current.target_operations.find((item) => item.operation === "POLICY")?.status).toBe("OUTCOME_UNCERTAIN");
    expect(current.target_operations.find((item) => item.operation === "READBACK")?.status).toBe("NOT_ATTEMPTED");
    expect(current.case.goldtier_result?.policy_status).toBeNull();
    expect(current.processing_pipeline?.find((item) => item.node_id === "FINAL_REVIEW_SEND")?.status).toBe("BLOCKED");
    await expect(page.getByRole("button", { name: "Complete safe recovery", exact: true })).toHaveCount(0);
    await expect(review.getByRole("button", { name: "Check GoldTier status", exact: true })).toBeEnabled();
    expect(checkRequests).toBe(1);
  } else expect(checkRequests).toBe(0);
  const after = await counts(page);
  expect(after.fixture).toBe(mode); expect(after.external_calls).toBe(0);
  expect(after.calls.SHELL).toBe(1); expect(after.calls.POLICY).toBe(1); expect(after.calls.AMEND).toBe(0);
  expect(after.calls.READBACK).toBe(mode === "failed-policy" ? 0 : 1);
  if (mode === "success") {
    expect(current.status).toBe("COMPLETED"); expect(current.case.goldtier_result?.readback_status).toBe("VERIFIED");
  }
  await page.getByRole("link", { name: "Cases", exact: true }).click();
  await page.locator(`a[href="/cases/${caseId}"]`).first().click();
  await expect(page.locator("#case-review-and-send").getByRole("heading", { name: title, exact: true })).toBeVisible();
  expect(checkRequests).toBe(mode === "uncertain-policy" ? 1 : 0);
  expect((await counts(page)).calls).toEqual(after.calls);
  for (const width of [320, 720, 1280]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(await page.evaluate(() => document.body.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
    await expect(page.locator("#submission-state-title")).toBeVisible();
  }
}

test("S3 normal Sandbox submission confirms retained operations and customer readback", { tag: "@s3-sandbox-success" }, async ({ page }) => {
  await submitAndInspect(page, "success");
});
test("S3 uncertain Policy checks customer identity once without completing Policy or replaying writes", { tag: "@s3-sandbox-uncertain-policy" }, async ({ page }) => {
  await submitAndInspect(page, "uncertain-policy");
});
test("S3 definitive Policy failure preserves the target ID and never retries submission", { tag: "@s3-sandbox-failed-policy" }, async ({ page }) => {
  await submitAndInspect(page, "failed-policy");
});

test("post-UAT Garden scanned evidence auto-confirms, calculates local ownership and verifies retained Sandbox identity", { tag: "@s3-sandbox-garden-existing-customer" }, async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("User ID").fill("maya-lim");
  await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("link", { name: "New onboarding", exact: true }).click();
  await page.getByLabel("Jurisdiction", { exact: true }).selectOption("SG");
  await page.getByLabel("Company Legal Name", { exact: true }).fill("GARDEN BUSINESS");
  await page.getByLabel("Registration ID / UEN").fill("11111999A");
  await page.locator("#home-document").setInputFiles(path.resolve("../backend/tests/fixtures/uat/garden-post-uat-scanned.png"));
  await page.getByRole("button", { name: "Create onboarding", exact: true }).click();
  await expect(page).toHaveURL(/\/new-onboarding\/[0-9a-f-]{36}$/i);
  const caseId = page.url().split("/").at(-1)!;
  await expect.poll(async () => (await readSummary(page, caseId)).current_stage).toBe("GOLDTIER_SEARCH");
  await page.getByRole("button", { name: "Open full case", exact: true }).click();
  await openStage(page, "Document verification");
  const documents = await (await page.request.get(`/api/onboarding/cases/${caseId}/documents`)).json();
  expect(documents).toHaveLength(1);
  expect(documents[0].completion_method).toBe("AUTO_CONFIRMED");
  expect(documents[0].state).toBe("REVIEWED");
  expect(documents[0].fields.every((field: any) => field.review_status === "ACCEPTED"
    && field.comparison_status === "MATCH" && field.extraction_method === "LOCAL_TESSERACT_OCR"
    && field.confidence >= 0.85)).toBe(true);
  await expect(page.getByRole("button", { name: /^Accept .* suggestion$/ })).toHaveCount(0);
  await expect(page.locator(".document-field__heading").getByText("AUTO CONFIRMED", { exact: true })).toHaveCount(4);
  expect((await counts(page)).calls).toEqual({ SEARCH: 1, SHELL: 0, POLICY: 0, AMEND: 0, READBACK: 0 });
  await openStage(page, "Registry verification");
  await page.getByLabel("Existing customer confirmation rationale").fill("Compared the retained Garden candidate with current independent identity evidence.");
  await page.getByRole("button", { name: "Confirm existing GoldTier customer", exact: true }).click();
  await expect.poll(async () => (await readSummary(page, caseId)).clm.target_search_checkpoint?.disposition).toBe("CONFIRMED_EXISTING");
  if ((await readSummary(page, caseId)).status === "PENDING_INPUTS") {
    await openStage(page, "Document verification");
    await page.getByRole("button", { name: "Continue evidence review", exact: true }).click();
  }
  await expect.poll(async () => (await readSummary(page, caseId)).ownership_recovery?.state).toBe("ANALYZED");
  const ownership = await (await page.request.get(`/api/onboarding/cases/${caseId}/ownership`)).json();
  expect(ownership.source_classification).toBe("OFFICIAL_MOCK_PLUS_LOCAL_SUPPLEMENT");
  expect(ownership.manual_review_receipt).toBeNull();
  expect(ownership.candidates.find((item: any) => item.party.display_name === "ABCD123").aggregated_ownership_percent).toMatch(/^51\.136363750*$/);
  await openStage(page, "Submission readiness");
  await page.getByLabel("KYC customer type", { exact: true }).selectOption("Company - Private");
  await page.getByLabel("Client segment", { exact: true }).selectOption("Corporate");
  await page.getByRole("button", { name: "Save target classification", exact: true }).click();
  await openStage(page, "Final review & send");
  await page.getByRole("button", { name: "Confirm and send to GoldTier sandbox", exact: true }).click();
  await expect.poll(async () => (await readSummary(page, caseId)).target_submission?.state).toBe("SUBMISSION_CONFIRMED");
  const details = page.locator('[aria-label="Completed GoldTier submission"]');
  await expect(details.locator("dt").first()).toHaveText("GoldTier ID");
  await expect(details.locator("dd").first()).toHaveText("143878");
  await expect(details.getByText("Existing GoldTier customer reused", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Verify in GoldTier", exact: true }).click();
  await expect(details.getByText("Verified in Sandbox", { exact: true })).toBeVisible();
  expect((await readSummary(page, caseId)).target_submission?.goldtier_id).toBe("143878");
  expect((await counts(page)).calls).toEqual({ SEARCH: 1, SHELL: 0, POLICY: 0, AMEND: 0, READBACK: 2 });
  expect((await counts(page)).external_calls).toBe(0);
});
