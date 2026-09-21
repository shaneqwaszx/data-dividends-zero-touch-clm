import path from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test, type Page } from "@playwright/test";
import {
  createBrowserNetworkPolicy,
  handleBrowserRoute,
  type BrowserNetworkPolicy,
} from "../playwright.config";

const currentDirectory = path.dirname(fileURLToPath(import.meta.url));
const cleanFixture = path.resolve(
  currentDirectory,
  "../../backend/tests/fixtures/uat/clean-company-profile.pdf",
);
const mismatchFixture = path.resolve(
  currentDirectory,
  "../../backend/tests/fixtures/uat/legal-name-mismatch.pdf",
);
const lowConfidenceFixture = path.resolve(
  currentDirectory,
  "../../backend/tests/fixtures/uat/low-confidence.pdf",
);
const ownershipCycleFixture = path.resolve(
  currentDirectory,
  "../../backend/tests/fixtures/uat/cycle-uen-clean.pdf",
);

function requiredEnvironment(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`The task-owned E2E launcher must provide ${name}`);
  }
  return value;
}

type NetworkGuard = {
  assertNoViolations(): void;
};

async function guardLocalNetwork(
  page: Page,
  policy: BrowserNetworkPolicy,
): Promise<NetworkGuard> {
  const violations: string[] = [];
  await page.route("**/*", async (route) => {
    await handleBrowserRoute(route, policy, violations);
  });
  return {
    assertNoViolations() {
      expect(
        violations,
        "Browser network policy blocked request(s); only sanitized structure follows",
      ).toEqual([]);
    },
  };
}

async function login(page: Page) {
  const ephemeralCredential = requiredEnvironment("CLM_E2E_PASSWORD");
  await page.getByLabel("User ID").fill("maya-lim");
  await page.getByLabel("Password").fill(ephemeralCredential);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("navigation", { name: "Main workspace" })).toBeVisible({ timeout: 30_000 });
}

test.describe.configure({ mode: "serial" });

let networkGuard: NetworkGuard | undefined;

test.beforeEach(async ({ page }) => {
  const frontendOrigin = requiredEnvironment("PLAYWRIGHT_BASE_URL");
  const policy = createBrowserNetworkPolicy({
    frontendOrigin,
    backendOrigin: requiredEnvironment("CLM_E2E_BACKEND_ORIGIN"),
    // The browser uses Vite's same-origin /api proxy; direct backend access is unnecessary.
    allowDirectBackend: false,
  });
  networkGuard = await guardLocalNetwork(page, policy);
});

test.afterEach(() => {
  networkGuard?.assertNoViolations();
  networkGuard = undefined;
});

test("protected workspace requires a real login before navigation", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Main workspace" })).toHaveCount(0);

  await login(page);
  const newOnboardingLink = page.getByRole("link", { name: "New onboarding" });
  await expect(newOnboardingLink).toHaveAttribute("href", "/new-onboarding");
  await newOnboardingLink.click();
  await expect(page.getByRole("heading", { name: "Start onboarding" })).toBeVisible();
});

test("Singapore clean fixture completes the truthful Mock target path", async ({ page }) => {
  await page.goto("/");
  await login(page);
  const newOnboardingLink = page.getByRole("link", { name: "New onboarding" });
  await expect(newOnboardingLink).toHaveAttribute("href", "/new-onboarding");
  await newOnboardingLink.click();

  await page.getByLabel("Jurisdiction").selectOption("SG");
  await page.getByLabel("Registration ID / UEN").fill("202400001A");
  await page.locator("#home-document").setInputFiles(cleanFixture);
  await page.getByRole("button", { name: "Create onboarding" }).click();

  await expect(page).toHaveURL(/\/new-onboarding\/([0-9a-f-]{36})$/i);
  const caseId = page.url().split("/").at(-1)!;
  await expect.poll(async () => {
    const response = await page.request.get(`/api/clm/zero-touch/cases/${caseId}`);
    if (!response.ok()) return null;
    return (await response.json() as { status: string }).status;
  }, { timeout: 120_000 }).toBe("COMPLETED");
  const caseRequests: Array<{ method: string; url: string }> = [];
  page.on("request", (request) => {
    if (request.url().includes(caseId)) caseRequests.push({ method: request.method(), url: request.url() });
  });
  await page.goto(`/cases/${caseId}`);
  await expect(page.getByText("Completed Mock workflow")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText(/GoldTier Mock/).first()).toBeVisible();
  await expect(page.getByText(/not production approval or Ready-for-Approval/i)).toBeVisible();
  await expect(page.getByRole("heading", { name: "Registry provenance" })).toBeVisible();
  await expect(page.getByText("Case evidence binding not recorded.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Ownership path explorer" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Why this case is in its current state" })).toBeVisible();

  const interactionRequestBaseline = caseRequests.length;
  const storageBefore = await page.evaluate(() => JSON.stringify({
    local: { ...localStorage },
    session: { ...sessionStorage },
  }));
  const candidate = page.locator('[aria-label="Ownership candidates"] button').first();
  await expect(candidate).toBeVisible();
  await candidate.click();
  const retainedPath = page.getByRole("button", { name: /^Inspect / }).first();
  await expect(retainedPath).toBeVisible();
  await retainedPath.click();
  await expect(retainedPath).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Focus registry evidence" }).click();
  await expect(page.locator("#case-evidence-registry")).toBeFocused();
  await page.waitForTimeout(250);
  expect(caseRequests.slice(interactionRequestBaseline)).toEqual([]);
  expect(await page.evaluate(() => JSON.stringify({
    local: { ...localStorage },
    session: { ...sessionStorage },
  }))).toBe(storageBefore);

  await page.setViewportSize({ width: 480, height: 900 });
  await expect(page.getByRole("heading", { name: "Registry provenance" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Ownership path explorer" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Why this case is in its current state" })).toBeVisible();
  const horizontalLayout = await page.evaluate(() => ({
    rootClientWidth: document.documentElement.clientWidth,
    rootScrollWidth: document.documentElement.scrollWidth,
  }));
  expect(horizontalLayout.rootScrollWidth).toBeLessThanOrEqual(horizontalLayout.rootClientWidth + 1);
  const ownershipTableScroller = page.locator("#case-evidence-ownership .table-scroll").first();
  const tableLayout = await ownershipTableScroller.evaluate((element) => {
    const bounds = element.getBoundingClientRect();
    return {
      clientWidth: element.clientWidth,
      scrollWidth: element.scrollWidth,
      left: Math.round(bounds.left),
      right: Math.round(bounds.right),
    };
  });
  expect(tableLayout.scrollWidth).toBeGreaterThan(tableLayout.clientWidth);
  expect(tableLayout.left).toBeGreaterThanOrEqual(-1);
  expect(tableLayout.right).toBeLessThanOrEqual(horizontalLayout.rootClientWidth + 1);
  const casesLink = page.getByRole("link", { name: "Cases" });
  await expect(casesLink).toHaveAttribute("href", "/cases");
  await casesLink.click();
  await expect(page.getByRole("heading", { name: "Cases" })).toBeVisible();
  await expect(page.getByText("MOCK_GOLDTIER_SUBMITTED", { exact: true })).toBeVisible();
});

test("current document review progresses authoritatively and keeps superseded history read-only", async ({ page }) => {
  const reviewRequests: string[] = [];
  const resumeRequests: string[] = [];
  page.on("request", (request) => {
    if (request.method() === "POST" && request.url().endsWith("/reviews")) reviewRequests.push(request.postData() ?? "");
    if (request.method() === "POST" && request.url().endsWith("/resume")) resumeRequests.push(request.url());
  });

  await page.goto("/");
  await login(page);
  await page.getByRole("link", { name: "New onboarding" }).click();
  await page.getByLabel("Jurisdiction").selectOption("SG");
  await page.getByLabel("Registration ID / UEN").fill("202400001A");
  await page.locator("#home-document").setInputFiles(mismatchFixture);
  await page.getByRole("button", { name: "Create onboarding" }).click();
  await expect(page).toHaveURL(/\/new-onboarding\/([0-9a-f-]{36})$/i);
  const caseId = page.url().split("/").at(-1)!;
  await expect.poll(async () => {
    const response = await page.request.get(`/api/onboarding/cases/${caseId}/documents`);
    if (!response.ok()) return 0;
    return (await response.json() as unknown[]).length;
  }, { timeout: 120_000 }).toBe(1);

  await page.goto(`/cases/${caseId}`);
  await expect(page.getByRole("heading", { name: "Document evidence and review" })).toBeVisible({ timeout: 30_000 });
  const focusRequestBaseline = reviewRequests.length + resumeRequests.length;
  await page.getByRole("button", { name: "Focus documents evidence" }).click();
  await expect(page.locator("#case-evidence-documents")).toBeFocused();
  expect(reviewRequests.length + resumeRequests.length).toBe(focusRequestBaseline);
  await expect(page.getByText("0 final / 4 fields")).toBeVisible();
  await expect(page.getByText(/4 fields remain for review/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Assign reviewer" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Return for rework" })).toHaveCount(0);

  const acceptRegistration = page.getByRole("button", { name: "Accept registration number suggestion" });
  await acceptRegistration.dblclick();
  await expect.poll(async () => {
    const response = await page.request.get(`/api/onboarding/cases/${caseId}/documents`);
    if (!response.ok()) return 0;
    const documents = await response.json() as Array<{ fields: Array<{ review_status: string }>; superseded_by_document_id: string | null }>;
    return documents.find((document) => document.superseded_by_document_id === null)
      ?.fields.filter((item) => item.review_status !== "PENDING").length ?? 0;
  }, { timeout: 120_000 }).toBe(1);
  expect(reviewRequests).toHaveLength(1);
  expect(JSON.parse(reviewRequests[0])).toEqual({ field_key: "registration_number", decision: "ACCEPTED" });
  expect(resumeRequests).toHaveLength(0);
  await page.goto(`/cases/${caseId}`);
  await expect(page.getByText("1 final / 4 fields")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText(/3 fields remain for review/)).toBeVisible();

  for (const [index, field] of ["legal name", "registered address", "country of incorporation"].entries()) {
    const action = page.getByRole("button", { name: `Accept ${field} suggestion` });
    if (await action.count() === 0) await page.goto(`/cases/${caseId}`);
    await expect(action).toBeVisible({ timeout: 30_000 });
    await action.click();
    await expect.poll(async () => {
      const response = await page.request.get(`/api/onboarding/cases/${caseId}/documents`);
      if (!response.ok()) return 0;
      const documents = await response.json() as Array<{ fields: Array<{ review_status: string }>; superseded_by_document_id: string | null }>;
      return documents.find((document) => document.superseded_by_document_id === null)
        ?.fields.filter((item) => item.review_status !== "PENDING").length ?? 0;
    }, { timeout: 120_000 }).toBe(index + 2);
    if (index < 2) await page.goto(`/cases/${caseId}`);
  }
  await expect.poll(async () => {
    const response = await page.request.get(`/api/onboarding/cases/${caseId}/documents`);
    if (!response.ok()) return null;
    const documents = await response.json() as Array<{ state: string; superseded_by_document_id: string | null }>;
    return documents.find((document) => document.superseded_by_document_id === null)?.state ?? null;
  }, { timeout: 120_000 }).toBe("REVIEWED");
  await page.goto(`/cases/${caseId}`);
  await expect(page.getByText("REVIEWED", { exact: true }).first()).toBeVisible({ timeout: 30_000 });
  expect(reviewRequests).toHaveLength(4);
  expect(resumeRequests).toHaveLength(0);

  const replacementInput = page.getByLabel("Replace current document");
  await replacementInput.focus();
  await expect(replacementInput).toBeFocused();
  await replacementInput.setInputFiles(cleanFixture);
  await expect(page.getByText("Completed Mock workflow")).toBeVisible({ timeout: 120_000 });
  await expect.poll(async () => {
    const response = await page.request.get(`/api/onboarding/cases/${caseId}/documents`);
    if (!response.ok()) return false;
    const documents = await response.json() as Array<{ superseded_by_document_id: string | null }>;
    return documents.length === 2
      && documents.filter((document) => document.superseded_by_document_id === null).length === 1
      && documents.filter((document) => document.superseded_by_document_id !== null).length === 1;
  }, { timeout: 120_000 }).toBe(true);
  const history = page.getByText(/Evidence history \(1\)/);
  await history.click();
  const historicalCard = page.locator(".document-card--history");
  await expect(historicalCard).toBeVisible();
  await expect(historicalCard.getByRole("button")).toHaveCount(0);
  await expect(historicalCard.locator("input[type=file]")).toHaveCount(0);

  await page.reload();
  await expect(page).toHaveURL(`/cases/${caseId}`);
  await expect(page.getByRole("heading", { name: "Document evidence and review" })).toBeVisible();
  const reloadedHistory = page.getByText(/Evidence history \(1\)/);
  await expect(reloadedHistory).toBeVisible({ timeout: 30_000 });
  await reloadedHistory.click();
  await expect(page.locator(".document-card--history")).toBeVisible();
  await expect(page.getByText(/GoldTier Mock/).first()).toBeVisible();
  await expect(page.getByText(/Ready-for-Approval: NOT AVAILABLE/i)).toBeVisible();
  expect(resumeRequests).toHaveLength(0);
});

test("Cases filters exact open business-exception types without hiding other attention states", async ({ page }) => {
  await page.goto("/");
  await login(page);

  async function createPausedCase(uen: string, fixture: string): Promise<string> {
    await page.goto("/new-onboarding");
    await expect(page.getByRole("heading", { name: "Start onboarding" })).toBeVisible();
    await page.getByLabel("Jurisdiction").selectOption("SG");
    await page.getByLabel("Registration ID / UEN").fill(uen);
    await page.locator("#home-document").setInputFiles(fixture);
    await page.getByRole("button", { name: "Create onboarding" }).click();
    await expect(page).toHaveURL(/\/new-onboarding\/([0-9a-f-]{36})$/i);
    const caseId = page.url().split("/").at(-1)!;
    await expect.poll(async () => {
      const response = await page.request.get(`/api/clm/zero-touch/cases/${caseId}`);
      if (!response.ok()) return null;
      return (await response.json() as { status: string }).status;
    }, { timeout: 120_000 }).toBe("WAITING_FOR_REVIEW");
    return caseId;
  }

  const lowConfidenceCaseId = await createPausedCase("202400001A", lowConfidenceFixture);
  const ownershipCycleCaseId = await createPausedCase("202400006F", ownershipCycleFixture);

  await page.goto("/cases");
  await expect(page.getByRole("heading", { name: "Cases" })).toBeVisible();
  const attentionFilter = page.getByLabel("Open business exception type");
  await expect(attentionFilter).toBeVisible();

  const filterRequests: Array<{ method: string; path: string }> = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.pathname === "/api/clm/zero-touch/cases") {
      filterRequests.push({ method: request.method(), path: `${url.pathname}${url.search}` });
    }
  });

  await attentionFilter.selectOption("DOCUMENT_LOW_CONFIDENCE");
  await expect(page.getByText("202400001A", { exact: true })).toBeVisible();
  await expect(page.getByText("202400006F", { exact: true })).toHaveCount(0);
  await expect(
    page.getByLabel("Cases table").getByText("Document low confidence", { exact: true }),
  ).toBeVisible();

  await attentionFilter.selectOption("OWNERSHIP_CYCLE");
  await expect(page.getByText("202400006F", { exact: true })).toBeVisible();
  await expect(page.getByText("202400001A", { exact: true })).toHaveCount(0);
  await expect(
    page.getByLabel("Cases table").getByText("Ownership cycle", { exact: true }),
  ).toBeVisible();

  await attentionFilter.selectOption("");
  await expect(page.getByText("202400001A", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("202400006F", { exact: true })).toBeVisible();

  expect(filterRequests).toEqual(expect.arrayContaining([
    {
      method: "GET",
      path: "/api/clm/zero-touch/cases?attention_type=DOCUMENT_LOW_CONFIDENCE",
    },
    {
      method: "GET",
      path: "/api/clm/zero-touch/cases?attention_type=OWNERSHIP_CYCLE",
    },
  ]));
  expect(filterRequests.every((request) => request.method === "GET")).toBe(true);

  await page.setViewportSize({ width: 480, height: 900 });
  await attentionFilter.focus();
  await expect(attentionFilter).toBeFocused();
  await expect(attentionFilter).toBeVisible();
  const queueScroller = page.getByLabel("Cases table");
  const scrollerLayout = await queueScroller.evaluate((element) => {
    const bounds = element.getBoundingClientRect();
    return {
      clientWidth: element.clientWidth,
      scrollWidth: element.scrollWidth,
      left: Math.round(bounds.left),
      right: Math.round(bounds.right),
      viewportWidth: document.documentElement.clientWidth,
    };
  });
  expect(scrollerLayout.scrollWidth).toBeGreaterThan(scrollerLayout.clientWidth);
  expect(scrollerLayout.left).toBeGreaterThanOrEqual(-1);
  expect(scrollerLayout.right).toBeLessThanOrEqual(scrollerLayout.viewportWidth + 1);

  const ownershipRow = page.getByRole("row").filter({ hasText: "202400006F" });
  const openLink = ownershipRow.getByRole("link", { name: "Open" });
  await expect(openLink).toHaveAttribute("href", `/cases/${ownershipCycleCaseId}`);
  await openLink.click();
  await expect(page).toHaveURL(`/cases/${ownershipCycleCaseId}`);
  await expect(
    page.getByRole("heading", { name: "Why this case is in its current state" }),
  ).toBeVisible();
  expect(lowConfidenceCaseId).not.toBe(ownershipCycleCaseId);
});
