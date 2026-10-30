import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test, type Page } from "@playwright/test";
import { openStage } from "./stage-disclosures";

const fixtures = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../backend/tests/fixtures/uat");
const wrongCompanyFixture = path.join(fixtures, "second-case-isolation.pdf");
const cleanFixture = path.join(fixtures, "clean-company-profile.pdf");

async function signIn(page: Page): Promise<Record<string, string>> {
  await page.goto("/");
  const login = page.waitForResponse((response) => response.url().endsWith("/api/auth/login"));
  await page.getByLabel("User ID").fill("maya-lim");
  await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  return { "X-CSRF-Token": (await (await login).json()).csrf_token };
}

test("wrong-company document shows an inline warning until it is replaced with matching evidence", async ({ page }) => {
  test.setTimeout(240_000);
  const headers = await signIn(page);
  const created = await page.request.post("/api/clm/zero-touch/cases", {
    headers, data: { uen: "202400001A", legal_name: "MERLION CIRCULAR LABS PTE. LTD.", country_of_incorporation: "SG" },
  });
  expect(created.status()).toBe(201);
  const caseId = (await created.json()).case.case_id as string;
  expect((await page.request.post(`/api/clm/zero-touch/cases/${caseId}/intake/documents`, {
    headers: { ...headers, "Content-Type": "application/pdf", "X-Document-Name": "second-case-isolation.pdf" },
    data: await readFile(wrongCompanyFixture),
  })).status()).toBe(201);
  expect((await page.request.post(`/api/clm/zero-touch/cases/${caseId}/intake/complete`, {
    headers, data: { expected_document_count: 1 },
  })).status()).toBeLessThan(300);
  await expect.poll(async () => {
    const summary = await (await page.request.get(`/api/clm/zero-touch/cases/${caseId}`)).json();
    return `${summary.status}:${summary.current_stage}`;
  }, { timeout: 120_000 }).toBe("WAITING_FOR_REVIEW:DOCUMENT");

  await page.goto(`/cases/${caseId}`);
  await openStage(page, "Document verification");
  const warning = page.locator(".document-identity-warning");
  await expect(warning).toHaveCount(1);
  await expect(warning).toHaveAttribute("role", "alert");
  await expect(warning.locator("strong").first()).toHaveText("This document looks like it belongs to a different company");
  await expect(warning).toContainText("On this document: LION CITY EXISTING CUSTOMER PTE. LTD.");
  await expect(warning).toContainText("This case: MERLION CIRCULAR LABS PTE. LTD.");
  await expect(warning).toContainText("On this document: 202400005E");
  await expect(warning).toContainText("This case: 202400001A");
  await expect(page.getByText("Action needed: upload a replacement document")).toHaveCount(0);
  await expect(page.getByText("PDF, Word (.docx), text, PNG, JPEG or TIFF · up to 5 MB per file, 25 MB per case").first()).toBeVisible();

  // The warning's button opens the document's existing replacement control (a new version, not a delete).
  const replace = warning.getByRole("button", { name: "Replace document", exact: true });
  await expect(replace).toBeEnabled();
  const chooser = page.waitForEvent("filechooser");
  const replacement = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname.endsWith("/replacement"));
  await replace.click();
  await (await chooser).setFiles(cleanFixture);
  expect((await replacement).status()).toBe(200);

  await expect(page.locator(".document-identity-warning")).toHaveCount(0, { timeout: 120_000 });
  const documents = await (await page.request.get(`/api/onboarding/cases/${caseId}/documents`)).json() as Array<{
    display_name: string; superseded_by_document_id: string | null;
  }>;
  const original = documents.find((item) => item.display_name === "second-case-isolation.pdf");
  expect(original?.superseded_by_document_id, "the wrong file stays as superseded history").toBeTruthy();
  expect(documents.filter((item) => item.superseded_by_document_id === null).map((item) => item.display_name))
    .toEqual(["clean-company-profile.pdf"]);
});
