import { expect, test, type Page } from "@playwright/test";
import { createBrowserNetworkPolicy, handleBrowserRoute, retainedEvidencePath } from "../playwright.config";

// Small synthetic PDFs built here (no committed binaries). The real backend worker rejects
// each one; the banner must show the plain reason, hide case/retry wording in Technical
// details, and offer the case's own upload control instead of re-sending the same file.

function buildPdf(objects: string[]): Buffer {
  let body = "%PDF-1.7\n";
  const offsets: number[] = [];
  objects.forEach((object, index) => {
    offsets.push(Buffer.byteLength(body, "latin1"));
    body += `${index + 1} 0 obj\n${object}\nendobj\n`;
  });
  const xref = Buffer.byteLength(body, "latin1");
  body += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  body += offsets.map(offset => `${String(offset).padStart(10, "0")} 00000 n \n`).join("");
  body += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return Buffer.from(body, "latin1");
}

/** One Letter page carrying a hyperlink annotation, as "Save as PDF" from a dashboard tool produces. */
export function linkAnnotationPdf(): Buffer {
  return buildPdf([
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Annots [4 0 R] >>",
    "<< /Type /Annot /Subtype /Link /Rect [10 10 100 30] /A << /S /URI /URI (https://example.invalid/) >> >>",
  ]);
}

/** Eleven blank Letter pages: one over the 10-page limit. */
export function elevenPagePdf(): Buffer {
  const pages = Array.from({ length: 11 }, (_, index) => `${index + 3} 0 R`).join(" ");
  return buildPdf([
    "<< /Type /Catalog /Pages 2 0 R >>",
    `<< /Type /Pages /Kids [${pages}] /Count 11 >>`,
    ...Array.from({ length: 11 }, () => "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>"),
  ]);
}

function requiredEnvironment(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`The task-owned E2E launcher must provide ${name}`);
  return value;
}

async function login(page: Page) {
  await page.goto("/");
  await page.getByLabel("User ID").fill("maya-lim");
  await page.getByLabel("Password").fill(requiredEnvironment("CLM_E2E_PASSWORD"));
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("navigation", { name: "Main workspace" })).toBeVisible({ timeout: 30_000 });
}

async function startCaseWith(page: Page, name: string, buffer: Buffer) {
  await login(page);
  await page.getByRole("link", { name: "New onboarding", exact: true }).click();
  await page.getByLabel("Jurisdiction").selectOption("SG");
  await page.getByLabel("Company Legal Name").fill("MERLION CIRCULAR LABS PTE. LTD.");
  await page.getByLabel("Registration ID / UEN").fill("202400001A");
  await page.locator("#home-document").setInputFiles({ name, mimeType: "application/pdf", buffer });
  await page.getByRole("button", { name: "Create onboarding" }).click();
  await expect(page).toHaveURL(/\/cases\/([0-9a-f-]{36})$/i, { timeout: 30_000 });
  const caseId = page.url().split("/").at(-1)!;
  const banner = page.locator(".pending-documents");
  await expect(banner.locator("#pending-documents-title")).toHaveText("Your document couldn't be uploaded", { timeout: 60_000 });
  return { banner, caseId };
}

// The backend's fixed timeout wording (apps/backend/app/services/document_errors.py).
const TIMEOUT_MESSAGE = "Processing this file took too long. Try uploading it again; if it keeps happening, upload a smaller or simpler copy.";

test.describe.configure({ mode: "serial" });

let networkViolations: string[] = [];
test.beforeEach(async ({ page }) => {
  networkViolations = [];
  const policy = createBrowserNetworkPolicy({
    frontendOrigin: requiredEnvironment("PLAYWRIGHT_BASE_URL"),
    backendOrigin: requiredEnvironment("CLM_E2E_BACKEND_ORIGIN"),
    allowDirectBackend: false,
  });
  const violations = networkViolations;
  await page.route("**/*", async (route) => { await handleBrowserRoute(route, policy, violations); });
});

test.afterEach(() => {
  expect(networkViolations, "Browser network policy blocked request(s)").toEqual([]);
});

test("a PDF with links shows the plain reason and moves to the case's upload control", async ({ page }) => {
  test.setTimeout(180_000);
  await page.setViewportSize({ width: 1280, height: 900 });
  const { banner, caseId } = await startCaseWith(page, "Forecast in Tableau.pdf", linkAnnotationPdf());

  await expect(banner).toContainText(
    "Forecast in Tableau.pdf: This PDF contains links or interactive content, which isn't allowed. Print it to PDF ('Save as PDF') and upload that copy.",
  );
  await expect(banner).not.toContainText("bounded local structure checks");
  // Case ID and retry wording sit in collapsed Technical details.
  const technical = banner.locator("details.pending-documents__technical");
  await expect(technical).not.toHaveAttribute("open", /.*/);
  await expect(technical.getByText(`Case ${caseId} was retained.`, { exact: false })).toBeHidden();
  await expect(banner.getByRole("button", { name: "Try upload again", exact: true })).toHaveCount(0);
  await banner.screenshot({ path: retainedEvidencePath("1-links-pdf-banner.png") });
  await technical.locator("summary").click();
  await expect(technical).toContainText(`Case ${caseId} was retained.`);
  await expect(technical).toContainText("DOCUMENT_ACTIVE_CONTENT");

  await banner.getByRole("button", { name: "Choose a different file", exact: true }).click();
  // The existing Discard ran: the banner is gone and the retained case page stays open.
  await expect(page.locator(".pending-documents")).toHaveCount(0);
  await expect(page).toHaveURL(new RegExp(`/cases/${caseId}$`));
  await expect(page.locator("#case-document-upload input[type=file]")).toBeFocused({ timeout: 10_000 });
});

test("an 11-page PDF says to upload only the pages needed", async ({ page }) => {
  test.setTimeout(180_000);
  await page.setViewportSize({ width: 1280, height: 900 });
  const { banner } = await startCaseWith(page, "eleven-pages.pdf", elevenPagePdf());
  await expect(banner).toContainText("eleven-pages.pdf: This file has more than 10 pages. Upload only the pages needed (up to 10).");
  await expect(banner.getByRole("button", { name: "Choose a different file", exact: true })).toBeVisible();
  await banner.screenshot({ path: retainedEvidencePath("2-eleven-page-banner.png") });
});

test("a timeout keeps Try upload again with its plain message", async ({ page }) => {
  test.setTimeout(180_000);
  await page.setViewportSize({ width: 1280, height: 900 });
  // The backend's real timeout response shape; the worker itself is not slowed down.
  await page.route("**/api/clm/zero-touch/cases/*/intake/documents", async (route) => {
    if (route.request().method() !== "POST") { await route.fallback(); return; }
    await route.fulfill({
      status: 422,
      contentType: "application/json",
      body: JSON.stringify({ detail: { code: "DOCUMENT_PROCESSING_TIMEOUT", message: TIMEOUT_MESSAGE } }),
    });
  });
  const { banner } = await startCaseWith(page, "Forecast in Tableau.pdf", linkAnnotationPdf());
  await expect(banner).toContainText(`Forecast in Tableau.pdf: ${TIMEOUT_MESSAGE}`);
  await expect(banner.getByRole("button", { name: "Try upload again", exact: true })).toBeVisible();
  await expect(banner.getByRole("button", { name: "Choose a different file", exact: true })).toHaveCount(0);
  await banner.screenshot({ path: retainedEvidencePath("3-timeout-banner.png") });
});
