import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test, type Page } from "@playwright/test";
import { createBrowserNetworkPolicy, handleBrowserRoute } from "../playwright.config";
import { openStage } from "./stage-disclosures";

const fixture = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../backend/tests/fixtures/uat/garden-business-clean-onboarding-profile.pdf");
let violations: string[];
test.beforeEach(async ({ page }) => {
  violations = [];
  const policy = createBrowserNetworkPolicy({ frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!, backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false });
  await page.route("**/*", (route) => handleBrowserRoute(route, policy, violations));
});
test.afterEach(() => expect(violations).toEqual([]));
async function summary(page: Page, caseId: string) {
  const response = await page.request.get(`/api/clm/zero-touch/cases/${caseId}`); expect(response.status()).toBe(200); return response.json();
}
async function ownership(page: Page, caseId: string) {
  const response = await page.request.get(`/api/onboarding/cases/${caseId}/ownership`); expect(response.status()).toBe(200); return response.json();
}
async function createGarden(page: Page) {
  await page.goto("/");
  await page.getByLabel("User ID").fill("maya-lim"); await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("link", { name: "New onboarding", exact: true }).click();
  await page.getByLabel("Jurisdiction", { exact: true }).selectOption("SG");
  await page.getByLabel("Company Legal Name", { exact: true }).fill("GARDEN BUSINESS");
  await page.getByLabel("Registration ID / UEN").fill("11111999A");
  await page.locator("#home-document").setInputFiles(fixture);
  await page.getByRole("button", { name: "Create onboarding", exact: true }).click();
  await expect(page).toHaveURL(/\/new-onboarding\/[0-9a-f-]{36}$/i);
  const caseId = page.url().split("/").at(-1)!;
  await expect.poll(async () => (await summary(page, caseId)).status).toBe("WAITING_FOR_REVIEW");
  await page.getByRole("button", { name: "Open full case", exact: true }).click();
  await expect(page).toHaveURL(`/cases/${caseId}`);
  await expect(page.locator(".document-card:not(.document-card--history)")).toHaveCount(1);
  await openStage(page, "Readiness check");
  for (const name of ["KYC customer type", "Client segment"]) {
    const control = page.getByLabel(name, { exact: true });
    const value = await control.locator("option").evaluateAll((options) => options.map((item) => (item as HTMLOptionElement).value).find(Boolean));
    await control.selectOption(value!);
  }
  const classification = page.waitForResponse((response) => response.request().method() === "PUT" && response.url().endsWith("/target-classification"));
  await page.getByRole("button", { name: "Save target classification", exact: true }).click(); expect((await classification).status()).toBe(200);
  await openStage(page, "Ownership & UBO");
  await expect(page.getByRole("heading", { name: "Review or edit ownership evidence", exact: true })).toBeVisible();
  return caseId;
}
async function submitDecision(page: Page) {
  const response = page.waitForResponse((result) => result.request().method() === "POST" && result.url().endsWith("/manual-ownership-evidence"), { timeout: 15_000 });
  await page.locator(".manual-ownership").getByRole("button", { name: "Submit manual ownership evidence", exact: true }).click();
  const result = await response; expect(result.status()).toBe(200); return result.json();
}

test("S2 creator edits calculable multi-level ownership before send and inspects exact collapsed calculations", { tag: "@garden-protocol" }, async ({ page }) => {
  const caseId = await createGarden(page);
  const form = page.locator(".manual-ownership");
  await expect(form.getByLabel("Economic interest %", { exact: true }).nth(0)).toHaveValue("");
  await expect(form.getByLabel("Owner type", { exact: true }).nth(0)).toHaveValue("");
  await form.getByLabel("As-of date").fill("2026-10-04");
  await form.getByLabel("Review rationale").fill("Reviewed the synthetic direct economic-interest declaration with explicit sixty and forty percent interests.");
  for (const [index, percentage] of ["60", "40"].entries()) {
    await form.getByLabel("Owner name", { exact: true }).nth(index).fill(`Synthetic reviewed owner ${index + 1}`);
    await form.getByLabel("Owner type", { exact: true }).nth(index).selectOption("NATURAL_PERSON");
    await form.getByLabel("Economic interest %", { exact: true }).nth(index).fill(percentage);
  }
  await submitDecision(page);
  await expect(page.getByRole("button", { name: "Confirm and send to Mock GoldTier", exact: true })).toBeEnabled();
  const first = await ownership(page, caseId); expect(first.state).toBe("ANALYZED");
  expect((await summary(page, caseId)).ownership_edit_authorized).toBe(true);
  await page.getByRole("button", { name: "Edit ownership", exact: true }).click();
  await expect(page.locator("#case-manual-ownership-evidence")).toBeFocused();
  await form.getByLabel("Owner type", { exact: true }).nth(0).selectOption("LEGAL_ENTITY");
  await form.getByLabel("Owner name", { exact: true }).nth(0).fill("Synthetic holding entity");
  await form.getByLabel("Registration number (optional)", { exact: true }).nth(0).fill("202400002B");
  await form.getByLabel("Economic interest %", { exact: true }).nth(0).fill("100");
  const holdingId = await form.getByLabel("Owner ID", { exact: true }).nth(0).inputValue();
  await form.getByLabel("Owned legal entity", { exact: true }).nth(1).selectOption(holdingId);
  await form.getByLabel("Economic interest %", { exact: true }).nth(1).fill("100");
  await form.getByLabel("As-of date").fill("2026-10-04");
  await form.getByLabel("Review rationale").fill("Reviewed the explicit holding entity and its sole natural-person owner before submission.");
  await submitDecision(page);
  const revised = await ownership(page, caseId);
  expect(revised.analysis_id).not.toBe(first.analysis_id); expect(revised.state).toBe("ANALYZED");
  expect(revised.relationships.some((edge: any) => edge.parent_party_id === holdingId)).toBe(true);
  expect(revised.candidates[0].aggregated_ownership_percent).toMatch(/^100(?:\.0+)?$/);
  expect(revised.prior_analyses.some((prior: any) => prior.analysis_id === first.analysis_id && prior.manual_review_receipt.rationale === first.manual_review_receipt.rationale)).toBe(true);
  expect((await summary(page, caseId)).target_operations.filter((operation: any) => operation.operation !== "SEARCH").every((operation: any) => operation.status === "NOT_ATTEMPTED")).toBe(true);
  await openStage(page, "Ownership & UBO");
  const disclosure = page.locator(".s2-ownership-structure");
  await expect(disclosure).not.toHaveAttribute("open", "");
  const toggle = disclosure.locator(":scope > summary"); await toggle.focus(); await expect(toggle).toBeFocused(); await toggle.press("Enter"); await expect(disclosure).toHaveAttribute("open", "");
  await expect(disclosure.getByText(revised.candidates[0].paths[0].calculation, { exact: true }).first()).toBeVisible();
  for (const width of [320, 720, 1280]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(await page.evaluate(() => document.body.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
    await expect(toggle).toBeVisible();
  }
  await openStage(page, "Final review & send");
  const confirmation = page.waitForResponse((response) => response.request().method() === "POST" && response.url().endsWith("/target-confirmation"));
  await page.getByRole("button", { name: "Confirm and send to Mock GoldTier", exact: true }).click(); expect((await confirmation).status()).toBe(200);
  await expect.poll(async () => (await summary(page, caseId)).status).toBe("COMPLETED");
  expect((await summary(page, caseId)).ownership_edit_authorized).toBe(false);
  await expect(page.locator(".manual-ownership")).toHaveCount(0); await expect(page.getByRole("button", { name: "Edit ownership", exact: true })).toHaveCount(0);
});

test("S2 document proposals require deliberate creator source selection and retain immutable source bindings", { tag: "@garden-protocol" }, async ({ page }) => {
  const caseId = await createGarden(page);
  const records = await (await page.request.get(`/api/onboarding/cases/${caseId}/documents`)).json();
  const canonical = Object.fromEntries(records[0].fields.map((field: any) => [field.field_key, field.canonical_value]));
  const text = [`Legal Name: ${canonical.legal_name}`, `UEN: ${canonical.registration_number}`, `Registered Address: ${canonical.registered_address}`, `Country: ${canonical.country_of_incorporation}`,
    "Shareholder: Synthetic document owner one | Type: NATURAL_PERSON | Percentage: 30% | Owned Entity: GARDEN BUSINESS | Owned Entity Registration Number: 11111999A | As Of: 2026-10-04",
    "Shareholder: Synthetic document owner two | Type: NATURAL_PERSON | Percentage: 70% | Owned Entity: GARDEN BUSINESS | Owned Entity Registration Number: 11111999A | As Of: 2026-10-04"].join("\n");
  const intake = page.waitForResponse((response) => response.request().method() === "POST" && response.url().endsWith("/intake/documents"));
  await page.locator("#case-ownership-evidence-upload input").setInputFiles({ name: "synthetic-ownership-proposals.txt", mimeType: "text/plain", buffer: Buffer.from(text, "utf8") });
  const intakeResult = await intake;
  const intakePayload = await intakeResult.json();
  expect(intakeResult.status(), `public code: ${intakePayload.detail?.code ?? "none"}`).toBe(201);
  await expect.poll(async () => (await ownership(page, caseId)).document_observations.length).toBe(2);
  const proposed = await ownership(page, caseId); expect(proposed.state).toBe("REVIEW_REQUIRED");
  expect(proposed.document_observations.every((item: any) => item.decision_state === "PROPOSED" && item.document_version === 1)).toBe(true);
  await openStage(page, "Ownership & UBO");
  const form = page.locator(".manual-ownership");
  await form.getByLabel("Ownership source decision").selectOption("DOCUMENT_OBSERVATIONS");
  const choices = form.locator('input[type="checkbox"]'); await expect(choices).toHaveCount(2);
  await choices.nth(0).check(); await choices.nth(1).check();
  await form.getByLabel("As-of date").fill("2026-10-04");
  await form.getByLabel("Review rationale").fill("Selected both explicit synthetic document ownership percentages after comparing current source evidence.");
  await submitDecision(page);
  const revised = await ownership(page, caseId); expect(revised.manual_review_receipt.source_selection).toBe("DOCUMENT_OBSERVATIONS");
  expect([...revised.manual_review_receipt.selected_observation_ids].sort()).toEqual(proposed.document_observations.map((item: any) => item.observation_id).sort());
  expect(revised.manual_review_receipt.observed_document_versions).toEqual(proposed.document_bindings);
  expect(revised.document_observations).toEqual(proposed.document_observations);
  expect(revised.document_discrepancies.every((item: any) => item.verification_state === "REVIEWED")).toBe(true);
  expect(revised.prior_analyses.at(-1).document_observations).toEqual(proposed.document_observations);
  await openStage(page, "Document verification");
  const proposals = page.getByText("Proposed ownership observations (2)", { exact: true }); await proposals.click();
  await expect(page.getByText("Source agreement", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Evidence score", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Verification state", { exact: true }).first()).toBeVisible();
  expect((await summary(page, caseId)).status).not.toBe("COMPLETED");
});
