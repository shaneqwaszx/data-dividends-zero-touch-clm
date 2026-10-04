import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { createBrowserNetworkPolicy, handleBrowserRoute } from "../playwright.config";

test("S1 wrong UEN retains uploaded document and resumes the real onboarding journey", async ({ page }) => {
  const violations: string[] = [];
  const policy = createBrowserNetworkPolicy({
    frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!,
    backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!,
    allowDirectBackend: false,
  });
  await page.route("**/*", (route) => handleBrowserRoute(route, policy, violations));
  await page.goto("/");
  await page.getByLabel("User ID").fill("maya-lim");
  await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("navigation", { name: "Main workspace" })).toBeVisible();
  await page.getByRole("link", { name: "New onboarding", exact: true }).click();
  await page.getByLabel("Jurisdiction", { exact: true }).selectOption("SG");
  await page.getByLabel(/Legal name|Company Legal Name/i).fill("MERLION CIRCULAR LABS PTE. LTD.");
  await page.getByLabel("Registration ID").fill("99999999Z");
  const fixture = path.resolve(path.dirname(fileURLToPath(import.meta.url)),
    "../../backend/tests/fixtures/uat/clean-company-profile.pdf");
  await page.locator('input[type="file"]').first().setInputFiles(fixture);
  const createdResponse = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname === "/api/clm/zero-touch/cases");
  const intakeResponse = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname.endsWith("/intake/documents"));
  await page.getByRole("button", { name: "Create onboarding", exact: true }).click();
  const created = await (await createdResponse).json();
  const caseId = created.case.case_id;
  expect(created.active_exceptions.map((item: { blocker_code: string }) => item.blocker_code))
    .toContain("ACRA_ENTITY_NOT_FOUND");
  expect((await intakeResponse).status()).toBe(201);
  const documentsResponse = await page.request.get(`/api/onboarding/cases/${caseId}/documents`);
  expect(documentsResponse.status()).toBe(200);
  const documents = await documentsResponse.json();
  expect(documents).toHaveLength(1);
  const documentId = documents[0].document_id;
  await page.getByRole("button", { name: "Open full case", exact: true }).click();
  await page.getByRole("button", { name: "Edit UEN", exact: true }).click();
  await page.getByLabel("Singapore UEN").fill("202400001A");
  const correctedResponse = page.waitForResponse((response) => response.request().method() === "POST"
    && response.url().endsWith(`/cases/${caseId}/registry-identity`));
  await page.getByRole("button", { name: "Verify UEN and resume", exact: true }).click();
  const corrected = await (await correctedResponse).json();
  expect(corrected.case.case_id).toBe(caseId);
  expect(corrected.case.entity.registration_number).toBe("202400001A");
  expect(corrected.active_exceptions.some((item: { blocker_code: string }) =>
    item.blocker_code === "NO_CURRENT_DOCUMENT_EVIDENCE")).toBe(false);
  const after = await (await page.request.get(`/api/onboarding/cases/${caseId}/documents`)).json();
  expect(after.map((item: { document_id: string }) => item.document_id)).toContain(documentId);
  expect(corrected.current_stage).not.toBe("DOCUMENT");
  expect(violations).toEqual([]);
});
