import path from "node:path";
import { expect, test, type Page } from "@playwright/test";
import { createBrowserNetworkPolicy, handleBrowserRoute } from "../playwright.config";
import { openStage } from "./stage-disclosures";

async function summary(page: Page, id: string) {
  const response = await page.request.get(`/api/clm/zero-touch/cases/${id}`);
  expect(response.status()).toBe(200);
  return response.json();
}
async function choose(page: Page, id: string, label: string) {
  const response = page.waitForResponse((item) => item.request().method() === "POST"
    && item.url().endsWith(`/cases/${id}/registry-identity`));
  await page.getByRole("button", { name: label, exact: true }).click();
  const result = await response;
  expect(result.status()).toBe(200);
  return result.json();
}

for (const choice of ["manual", "entered"] as const) {
  test(`Garden PARTIAL wrong UEN correction resumes through ${choice} choice`,
    { tag: "@s3-sandbox-garden-existing-customer" }, async ({ page }) => {
    const violations: string[] = [];
    const policy = createBrowserNetworkPolicy({
      frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!,
      backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false,
    });
    await page.route("**/*", (route) => handleBrowserRoute(route, policy, violations));
    await page.goto("/");
    await page.getByLabel("User ID").fill("maya-lim");
    await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await expect(page.getByRole("navigation", { name: "Main workspace" })).toBeVisible();
    const initialCountsResponse = await page.request.get("/api/__s3/sandbox-counts");
    expect(initialCountsResponse.status()).toBe(200);
    const initialCounts = await initialCountsResponse.json();
    await page.getByRole("link", { name: "New onboarding", exact: true }).click();
    await page.getByLabel("Jurisdiction", { exact: true }).selectOption("SG");
    await page.getByLabel("Company Legal Name", { exact: true }).fill("GARDEN BUSINESS");
    await page.getByLabel("Registration ID / UEN").fill("11111998B");
    const filename = choice === "manual" ? "garden-partnership-reviewed-client.pdf"
      : "garden-business-conflicting-onboarding-profile.pdf";
    await page.locator("#home-document").setInputFiles(path.resolve("../backend/tests/fixtures/uat", filename));
    const intake = page.waitForResponse((item) => item.request().method() === "POST"
      && item.url().endsWith("/intake/complete"));
    await page.getByRole("button", { name: "Create onboarding", exact: true }).click();
    await expect(page).toHaveURL(/\/new-onboarding\/[0-9a-f-]{36}$/i);
    expect((await intake).status()).toBe(200);
    const id = page.url().split("/").at(-1)!;
    const before = await summary(page, id);
    expect(before.current_stage).toBe("REGISTRY");
    const docs = await (await page.request.get(`/api/onboarding/cases/${id}/documents`)).json();
    expect(docs).toHaveLength(1);
    await page.getByRole("button", { name: "Open full case", exact: true }).click();
    await openStage(page, "Registry verification");
    if (choice === "manual") {
      await expect(page.getByText("Document-detected UEN:")).toContainText("11111999A");
      await page.getByRole("button", { name: "Enter another UEN", exact: true }).click();
    } else {
      await page.getByRole("button", { name: "Edit UEN", exact: true }).click();
    }
    await page.getByLabel("Singapore UEN", { exact: true }).fill("11111999A");
    let corrected = await choose(page, id, "Verify UEN and resume");
    if (choice === "entered") {
      await expect(page.getByText("Original entered UEN:")).toContainText("11111998B");
      await expect(page.getByText("Current corrected UEN:")).toContainText("11111999A");
      await expect(page.getByText("Document-detected UEN:")).toContainText("11111998B");
      corrected = await choose(page, id, "Use entered UEN");
      expect(corrected.case.identity_corrections.at(-1).choice).toBe("ENTERED");
    }
    expect(corrected.case.case_id).toBe(id);
    expect(corrected.case.requested_uen).toBe("11111999A");
    expect(corrected.case.registry_acquisition.status).toBe("PARTIAL");
    expect(corrected.current_stage).toBe("GOLDTIER_SEARCH");
    expect(corrected.active_exceptions.map((item: any) => item.blocker_code))
      .toEqual(["GT_SEARCH_IDENTITY_REVIEW_REQUIRED"]);
    expect(corrected.historical_exceptions.some((item: any) =>
      item.blocker_code === "ACRA_ENTITY_NOT_FOUND" && item.status === "CANCELLED")).toBe(true);
    await expect(page.getByRole("button", { name: "Confirm existing GoldTier customer", exact: true })).toBeVisible();
    const after = await (await page.request.get(`/api/onboarding/cases/${id}/documents`)).json();
    expect(after[0].document_id).toBe(docs[0].document_id);
    expect(after[0].fields.map((item: any) => item.original_extracted_value))
      .toEqual(docs[0].fields.map((item: any) => item.original_extracted_value));
    await page.reload();
    await expect(page.getByRole("heading", { name: "GARDEN BUSINESS", exact: true })).toBeVisible();
    const reloaded = await summary(page, id);
    expect(reloaded.version).toBe(corrected.version);
    expect(reloaded.case.registry_acquisition).toEqual(corrected.case.registry_acquisition);
    expect(reloaded.active_exceptions).toEqual(corrected.active_exceptions);
    const counts = await (await page.request.get("/api/__s3/sandbox-counts")).json();
    expect(counts.external_calls).toBe(0);
    expect(counts.calls).toEqual({ SEARCH: initialCounts.calls.SEARCH + (choice === "entered" ? 3 : 2),
      SHELL: 0, POLICY: 0, AMEND: 0, READBACK: 0 });
    expect(violations).toEqual([]);
  });
}
