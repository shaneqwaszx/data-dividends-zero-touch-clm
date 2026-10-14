import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { createBrowserNetworkPolicy, handleBrowserRoute } from "../playwright.config";
import { focusPipelineAction } from "./stage-disclosures";

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
  const registry = page.locator(".stage-disclosure").filter({ has: page.getByRole("heading", { name: "Registry verification", exact: true }) });
  const search = page.getByRole("region", { name: "Existing-customer search", exact: true });
  await expect(page.locator("#case-identity-correction")).toHaveCount(1);
  await expect(registry.locator("#case-identity-correction")).toHaveCount(1);
  await expect(search.locator("#case-identity-correction")).toHaveCount(0);
  await expect(registry.locator("#case-evidence-registry")).toHaveCount(1);
  // Same-team visibility does not grant creator evidence authority. Returning in
  // a new creator session recovers current evidence without an old draft.
  await page.locator(".operator-account__button").click();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await page.getByLabel("User ID").fill("ethan-tan");
  await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("navigation", { name: "Main workspace" })).toBeVisible();
  await page.goto("/cases/" + caseId);
  await expect(search).toBeVisible();
  await expect(page.locator("#case-identity-correction")).toHaveCount(0);
  const deniedSummary = await (await page.request.get("/api/clm/zero-touch/cases/" + caseId)).json();
  expect(deniedSummary.evidence_decision_authorized).toBe(false);
  const deniedMutations: string[] = [];
  const deniedListener = (request: import("@playwright/test").Request) => {
    if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method())) deniedMutations.push(new URL(request.url()).pathname);
  };
  page.on("request", deniedListener);
  const deniedSearchNode = page.locator('.ds-stage[data-node-id="GOLDTIER_SEARCH"]');
  await deniedSearchNode.locator("summary").click();
  await deniedSearchNode.getByRole("button", { name: "Open case stage details", exact: true }).click();
  await expect(page.getByRole("button", { name: "Verify UEN and resume", exact: true })).toHaveCount(0);
  await expect(page.locator("#case-identity-correction")).toHaveCount(0);
  page.off("request", deniedListener);
  expect(deniedMutations).toEqual([]);
  await page.locator(".operator-account__button").click();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await page.getByLabel("User ID").fill("maya-lim");
  await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("navigation", { name: "Main workspace" })).toBeVisible();
  await page.goto("/cases/" + caseId);
  await expect(registry.locator("#case-identity-correction")).toHaveCount(1);
  for (const width of [1280, 360]) {
    await page.setViewportSize({ width, height: 900 });
    await focusPipelineAction(page, "GOLDTIER_SEARCH", page.getByLabel("Singapore UEN", { exact: true }));
    await expect(registry.getByRole("button", { name: "Registry verification", exact: true })).toHaveAttribute("aria-expanded", "true");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  }
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
