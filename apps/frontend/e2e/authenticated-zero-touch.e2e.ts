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

async function login(page: Page, userId = "maya-lim") {
  const ephemeralCredential = requiredEnvironment("CLM_E2E_PASSWORD");
  await page.getByLabel("User ID").fill(userId);
  await page.getByLabel("Password").fill(ephemeralCredential);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("navigation", { name: "Main workspace" })).toBeVisible({ timeout: 30_000 });
}

async function openWorkspaceTab(page: Page, name: string) {
  await page.getByRole("link", { name, exact: true }).click();
}

async function openFreshOnboarding(page: Page) {
  await openWorkspaceTab(page, "New onboarding");
  const landing = page.getByRole("heading", { name: "Start onboarding" });
  const startFresh = page.getByRole("button", { name: "Start a new case" });
  await expect(landing.or(startFresh)).toBeVisible();
  if (await startFresh.isVisible()) await startFresh.click();
  await expect(landing).toBeVisible();
}

test.describe.configure({ mode: "serial" });

let networkGuard: NetworkGuard | undefined;

test.beforeEach(async ({ page }) => {
  if (process.env.CLM_E2E_DIAGNOSTICS === "1") {
    page.on("console", (message) => {
      if (message.type() === "info" && message.text().startsWith("E2E_DIAG ")) {
        console.log(message.text());
      }
    });
  }
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
  const ownershipResponsePromise = page.waitForResponse((response) => (
    new URL(response.url()).pathname === `/api/onboarding/cases/${caseId}/ownership`
  ));
  await page.goto(`/cases/${caseId}`);
  const ownershipResponse = await ownershipResponsePromise;
  expect(ownershipResponse.status()).toBe(200);
  expect((await ownershipResponse.json() as { candidates: unknown[] }).candidates.length)
    .toBeGreaterThan(0);
  await expect(page.getByText("Completed POC workflow")).toBeVisible({ timeout: 30_000 });
  const operationalTiming = page.getByRole("region", { name: "Operational timing" });
  await expect(operationalTiming).toBeVisible();
  await expect(operationalTiming.getByText(/^Timing observed at /)).toHaveCount(1);
  await expect(operationalTiming.getByText("Case duration", { exact: true })).toBeVisible();
  await expect(
    operationalTiming.getByText("Recorded total automation duration", { exact: true }),
  ).toBeVisible();
  await expect(
    operationalTiming.getByText(/completed automated processing attempts only/i),
  ).toBeVisible();
  await expect(operationalTiming.getByText(/do not represent human waiting time/i)).toBeVisible();
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
  const portfolioRequests: string[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.pathname === "/api/clm/zero-touch/case-portfolio") {
      portfolioRequests.push(`${url.pathname}${url.search}`);
    }
  });
  await casesLink.click();
  await expect(page.getByRole("heading", { name: "Cases" })).toBeVisible();
  await expect(page.getByText("GoldTier target submitted", { exact: true })).toBeVisible();
  await expect(page.getByText(/^Timing observed at /)).toHaveCount(1);
  const completedTimingRow = page.getByRole("row").filter({
    has: page.locator(`a[href="/cases/${caseId}"]`),
  });
  await expect(completedTimingRow).toContainText("Case duration:");
  await expect(completedTimingRow).toContainText("Last updated:");

  const initialPortfolioResponsePromise = page.waitForResponse((response) => (
    new URL(response.url()).pathname === "/api/clm/zero-touch/case-portfolio"
  ));
  await page.reload();
  const initialPortfolioResponse = await initialPortfolioResponsePromise;
  const initialPortfolio = await initialPortfolioResponse.json() as { observed_at: string };
  const noActionRequestCount = portfolioRequests.length;
  expect(noActionRequestCount).toBeGreaterThanOrEqual(1);
  await page.waitForTimeout(750);
  expect(portfolioRequests).toHaveLength(noActionRequestCount);
  const refreshedPortfolioResponsePromise = page.waitForResponse((response) => (
    new URL(response.url()).pathname === "/api/clm/zero-touch/case-portfolio"
  ));
  await page.reload();
  const refreshedPortfolioResponse = await refreshedPortfolioResponsePromise;
  const refreshedPortfolio = await refreshedPortfolioResponse.json() as { observed_at: string };
  expect(Date.parse(refreshedPortfolio.observed_at)).toBeGreaterThan(
    Date.parse(initialPortfolio.observed_at),
  );
  expect(portfolioRequests.length).toBeGreaterThan(noActionRequestCount);
  expect(portfolioRequests.length).toBeLessThanOrEqual(noActionRequestCount + 2);
  await expect(page.getByText(/^Timing observed at /)).toHaveCount(1);

  const timingSearchResponse = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return url.pathname === "/api/clm/zero-touch/case-portfolio"
      && url.searchParams.get("search") === "209900104A";
  });
  await page.getByLabel("Search cases").fill("209900104A");
  expect((await timingSearchResponse).status()).toBe(200);
  const activeTimingRow = page.getByRole("row").filter({ hasText: "209900104A" });
  await expect(activeTimingRow).toContainText("Case age:");
  await expect(activeTimingRow).toContainText("Last updated:");
});

test("review-ready actions render after authoritative current document evidence loads", async ({ page }) => {
  await page.goto("/");
  await login(page);
  await page.getByRole("link", { name: "New onboarding" }).click();
  await page.getByLabel("Jurisdiction").selectOption("SG");
  await page.getByLabel("Registration ID / UEN").fill("202400001A");
  await page.locator("#home-document").setInputFiles(lowConfidenceFixture);
  await page.getByRole("button", { name: "Create onboarding" }).click();
  await expect(page).toHaveURL(/\/new-onboarding\/([0-9a-f-]{36})$/i);
  const caseId = page.url().split("/").at(-1)!;
  await expect.poll(async () => {
    const response = await page.request.get(`/api/clm/zero-touch/cases/${caseId}`);
    if (!response.ok()) return null;
    return (await response.json() as { status: string }).status;
  }, { timeout: 120_000 }).toBe("WAITING_FOR_REVIEW");

  const documentsResponse = page.waitForResponse((response) => (
    response.request().method() === "GET"
      && new URL(response.url()).pathname === `/api/onboarding/cases/${caseId}/documents`
  ));
  await page.goto(`/cases/${caseId}`);
  const response = await documentsResponse;
  expect(response.status()).toBe(200);
  const currentDocument = (await response.json() as Array<{
    state: string;
    superseded_by_document_id: string | null;
    fields: Array<{ review_status: string; original_extracted_value: string | null }>;
  }>).find((document) => document.superseded_by_document_id === null);
  expect(currentDocument).toBeDefined();
  expect(currentDocument?.state).toBe("REVIEW_REQUIRED");
  expect(currentDocument?.fields.every((field) => field.review_status === "PENDING")).toBe(true);
  expect(currentDocument?.fields.every((field) => field.original_extracted_value !== null)).toBe(true);
  await expect(page.getByRole("heading", { name: "Document evidence and review" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Accept .* suggestion/ }).first()).toBeVisible();
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

  const reviewMilestone = (milestone: string, reviewedFieldCount: number) => {
    if (process.env.CLM_E2E_DIAGNOSTICS !== "1") return;
    console.log("E2E_DIAG", JSON.stringify({
      milestone,
      case_id: caseId,
      reviewed_field_count: reviewedFieldCount,
    }));
  };
  const reviewedCount = async (response: import("@playwright/test").Response) => {
    const documents = await response.json() as Array<{
      fields: Array<{ review_status: string }>;
      superseded_by_document_id: string | null;
    }>;
    return documents.find((document) => document.superseded_by_document_id === null)
      ?.fields.filter((item) => item.review_status !== "PENDING").length ?? 0;
  };

  const acceptRegistration = page.getByRole("button", { name: "Accept registration number suggestion" });
  const firstMutationResponse = page.waitForResponse((response) =>
    response.request().method() === "POST" && response.url().endsWith("/reviews"));
  const firstDocumentsResponse = page.waitForResponse((response) =>
    response.request().method() === "GET"
      && response.url().endsWith(`/api/onboarding/cases/${caseId}/documents`));
  reviewMilestone("REVIEW_MUTATION_DISPATCHED", 0);
  await acceptRegistration.dblclick();
  expect((await firstMutationResponse).status()).toBe(200);
  reviewMilestone("REVIEW_MUTATION_RESPONSE_COMPLETE", 1);
  const firstBackendCount = await reviewedCount(await firstDocumentsResponse);
  expect(firstBackendCount).toBe(1);
  reviewMilestone("REVIEW_DOCUMENTS_GET_COMPLETE", firstBackendCount);
  expect(reviewRequests).toHaveLength(1);
  expect(JSON.parse(reviewRequests[0])).toEqual({ field_key: "registration_number", decision: "ACCEPTED" });
  expect(resumeRequests).toHaveLength(0);
  await expect(page.getByText("1 final / 4 fields")).toBeVisible({ timeout: 30_000 });
  reviewMilestone("REVIEW_RENDERED_COUNT", 1);
  await expect(page.getByText(/3 fields remain for review/)).toBeVisible();

  for (const [index, field] of ["legal name", "registered address", "country of incorporation"].entries()) {
    await expect(page.getByText(`${index + 1} final / 4 fields`)).toBeVisible({
      timeout: 30_000,
    });
    const action = page.getByRole("button", { name: `Accept ${field} suggestion` });
    await expect(action).toBeVisible({ timeout: 30_000 });
    const mutationResponse = page.waitForResponse((response) =>
      response.request().method() === "POST" && response.url().endsWith("/reviews"));
    const documentsResponse = page.waitForResponse((response) =>
      response.request().method() === "GET"
        && response.url().endsWith(`/api/onboarding/cases/${caseId}/documents`));
    reviewMilestone("REVIEW_MUTATION_DISPATCHED", index + 1);
    await action.click();
    expect((await mutationResponse).status()).toBe(200);
    reviewMilestone("REVIEW_MUTATION_RESPONSE_COMPLETE", index + 2);
    const backendCount = await reviewedCount(await documentsResponse);
    expect(backendCount).toBe(index + 2);
    reviewMilestone("REVIEW_DOCUMENTS_GET_COMPLETE", backendCount);
    await expect(page.getByText(`${index + 2} final / 4 fields`)).toBeVisible({
      timeout: 30_000,
    });
    reviewMilestone("REVIEW_RENDERED_COUNT", index + 2);
  }
  await expect.poll(async () => {
    const response = await page.request.get(`/api/onboarding/cases/${caseId}/documents`);
    if (!response.ok()) return null;
    const documents = await response.json() as Array<{ state: string; superseded_by_document_id: string | null }>;
    return documents.find((document) => document.superseded_by_document_id === null)?.state ?? null;
  }, { timeout: 120_000 }).toBe("REVIEWED");
  await expect(page.getByText("REVIEWED", { exact: true }).first()).toBeVisible({ timeout: 30_000 });
  expect(reviewRequests).toHaveLength(4);
  expect(resumeRequests).toHaveLength(0);

  const replacementInput = page.getByLabel("Replace current document");
  await replacementInput.focus();
  await expect(replacementInput).toBeFocused();
  await replacementInput.setInputFiles(cleanFixture);
  await expect(page.getByText("Completed POC workflow")).toBeVisible({ timeout: 120_000 });
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
  await expect(page.getByRole("heading", { name: "Document evidence and review" })).toBeVisible({
    timeout: 30_000,
  });
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
    await openFreshOnboarding(page);
    await page.getByLabel("Jurisdiction").selectOption("SG");
    await page.getByLabel("Registration ID / UEN").fill(uen);
    await page.locator("#home-document").setInputFiles(fixture);
    await page.getByRole("button", { name: "Create onboarding" }).click();
    await expect(page).toHaveURL(/\/new-onboarding\/([0-9a-f-]{36})$/i, {
      timeout: 30_000,
    });
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

  await openWorkspaceTab(page, "Cases");
  await expect(page.getByRole("heading", { name: "Cases" })).toBeVisible();
  const attentionFilter = page.getByLabel("Open business exception type");
  await expect(attentionFilter).toBeVisible();

  const filterRequests: Array<{ method: string; path: string }> = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.pathname === "/api/clm/zero-touch/case-portfolio") {
      filterRequests.push({ method: request.method(), path: `${url.pathname}${url.search}` });
    }
  });

  const lowConfidenceResponse = page.waitForResponse((response) => (
    new URL(response.url()).pathname === "/api/clm/zero-touch/case-portfolio"
      && new URL(response.url()).searchParams.get("attention_type")
        === "DOCUMENT_LOW_CONFIDENCE"
  ));
  await attentionFilter.selectOption("DOCUMENT_LOW_CONFIDENCE");
  const lowConfidencePage = await lowConfidenceResponse;
  expect(lowConfidencePage.status()).toBe(200);
  expect((await lowConfidencePage.json() as { items: Array<{ case_id: string }> }).items)
    .toEqual(expect.arrayContaining([
      expect.objectContaining({ case_id: lowConfidenceCaseId }),
    ]));
  await expect(page.getByText("202400001A", { exact: true })).toBeVisible();
  await expect(page.getByText("202400006F", { exact: true })).toHaveCount(0);
  await expect(
    page.getByLabel("Cases table").getByText("Document low confidence", { exact: true }),
  ).toBeVisible();

  const ownershipResponse = page.waitForResponse((response) => (
    new URL(response.url()).pathname === "/api/clm/zero-touch/case-portfolio"
      && new URL(response.url()).searchParams.get("attention_type") === "OWNERSHIP_CYCLE"
  ));
  await attentionFilter.selectOption("OWNERSHIP_CYCLE");
  const ownershipPage = await ownershipResponse;
  expect(ownershipPage.status()).toBe(200);
  expect((await ownershipPage.json() as { items: Array<{ case_id: string }> }).items)
    .toEqual(expect.arrayContaining([
      expect.objectContaining({ case_id: ownershipCycleCaseId }),
    ]));
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
      path: "/api/clm/zero-touch/case-portfolio?attention_type=DOCUMENT_LOW_CONFIDENCE",
    },
    {
      method: "GET",
      path: "/api/clm/zero-touch/case-portfolio?attention_type=OWNERSHIP_CYCLE",
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

test("Cases uses one bounded backend page for search, filters, paging, mutation refresh, and deletion", async ({ page }) => {
  const portfolioRequests: string[] = [];
  const detailRequests: string[] = [];
  const legacyListRequests: string[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.pathname === "/api/clm/zero-touch/case-portfolio") {
      portfolioRequests.push(`${url.pathname}${url.search}`);
    }
    if (/^\/api\/clm\/zero-touch\/cases\/[0-9a-f-]{36}$/i.test(url.pathname)) {
      detailRequests.push(url.pathname);
    }
    if (request.method() === "GET" && url.pathname === "/api/clm/zero-touch/cases") {
      legacyListRequests.push(url.pathname);
    }
  });
  await page.goto("/");
  await login(page);
  const targetUen = "209900104A";

  await openWorkspaceTab(page, "Cases");
  await expect(page.getByText(/Showing 1–50 on page 1/)).toBeVisible();
  // React StrictMode may cancel and replay the initial development-mode fetch. Both
  // observations must still be the same single bounded page shape, never row fan-out.
  expect(new Set(portfolioRequests)).toEqual(new Set([
    "/api/clm/zero-touch/case-portfolio",
  ]));
  expect(detailRequests).toEqual([]);
  expect(legacyListRequests).toEqual([]);

  const search = page.getByLabel("Search cases");
  await search.fill(targetUen);
  const searchedRow = page.getByRole("row").filter({ hasText: targetUen });
  await expect(searchedRow).toBeVisible();
  const searchedHref = await searchedRow.getByRole("link", { name: "Open" }).getAttribute("href");
  const targetCaseId = searchedHref?.split("/").at(-1);
  if (!targetCaseId) throw new Error("Seeded portfolio row did not expose its case identifier");
  expect(targetCaseId).toMatch(/^[0-9a-f-]{36}$/i);
  await expect.poll(() => portfolioRequests.at(-1)).toContain(`search=${targetUen}`);
  await page.getByLabel("Jurisdiction filter").selectOption("SG");
  await expect.poll(() => portfolioRequests.at(-1)).toContain("jurisdiction=SG");
  await expect.poll(() => portfolioRequests.at(-1)).toContain(`search=${targetUen}`);
  await search.fill("");
  await page.getByLabel("Jurisdiction filter").selectOption("");
  await page.getByLabel("Priority filter").selectOption("unset");
  await page.getByLabel("Priority sort").selectOption("lowest_first");
  await expect.poll(() => portfolioRequests.at(-1)).toContain("priority_filter=unset");
  await expect.poll(() => portfolioRequests.at(-1)).toContain("priority_sort=lowest_first");
  await page.getByLabel("Priority filter").selectOption("all");
  await page.getByLabel("Priority sort").selectOption("highest_first");
  await expect(page.getByText(/Showing 1–50 on page 1/)).toBeVisible();

  const nextResponse = page.waitForResponse((response) => (
    new URL(response.url()).pathname === "/api/clm/zero-touch/case-portfolio"
      && new URL(response.url()).searchParams.get("offset") === "50"
  ));
  await page.getByRole("button", { name: "Next" }).click();
  await nextResponse;
  await expect(page.getByText(/Showing 51–/)).toBeVisible();
  await page.getByRole("button", { name: "Previous" }).click();
  await expect(page.getByText(/Showing 1–50 on page 1/)).toBeVisible();

  await search.fill(targetUen);
  const targetRow = page.getByRole("row").filter({ hasText: targetUen });
  await expect(targetRow).toBeVisible();
  const open = targetRow.getByRole("link", { name: "Open" });
  await expect(open).toHaveAttribute("href", `/cases/${targetCaseId}`);
  await open.click();
  await expect(page).toHaveURL(`/cases/${targetCaseId}`);
  await openWorkspaceTab(page, "Cases");

  await page.locator(".operator-account__button").click();
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  await login(page, "ethan-tan");
  await openWorkspaceTab(page, "Cases");
  await page.getByLabel("Search cases").fill(targetUen);
  const mutableRow = page.getByRole("row").filter({ hasText: targetUen });
  await expect(mutableRow).toBeVisible();
  const priorityResponse = page.waitForResponse((response) => (
    response.request().method() === "PATCH"
      && new URL(response.url()).pathname === `/api/clm/zero-touch/cases/${targetCaseId}/priority`
  ));
  await mutableRow.locator("select.priority-select").selectOption("5");
  await mutableRow.getByRole("button", { name: "Set" }).click();
  expect((await priorityResponse).status()).toBe(200);
  await expect(mutableRow.locator(".priority-badge")).toHaveText("Medium");

  const deleteResponse = page.waitForResponse((response) => (
    response.request().method() === "DELETE"
      && new URL(response.url()).pathname === `/api/clm/zero-touch/cases/${targetCaseId}`
  ));
  await mutableRow.getByRole("button", { name: `Delete ${targetUen}` }).click();
  await page.getByRole("button", { name: "Delete case" }).click();
  expect((await deleteResponse).status()).toBe(204);
  await expect(page.getByText(targetUen, { exact: true })).toHaveCount(0);
  await page.waitForTimeout(400);
  await expect(page.getByText(targetUen, { exact: true })).toHaveCount(0);

  await page.getByLabel("Search cases").fill("");
  await expect(page.getByText(/Showing 1–50 on page 1/)).toBeVisible();
  await page.setViewportSize({ width: 480, height: 900 });
  const scroller = page.getByLabel("Cases table");
  await scroller.focus();
  await expect(scroller).toBeFocused();
  const layout = await scroller.evaluate((element) => ({
    clientWidth: element.clientWidth,
    scrollWidth: element.scrollWidth,
  }));
  expect(layout.scrollWidth).toBeGreaterThan(layout.clientWidth);
});

test("Case activity uses one paged read with accessible filters, scoped links, and mobile scrolling", async ({ page }) => {
  await page.goto("/");
  await login(page);

  const activityRequests: string[] = [];
  const caseDetailRequests: string[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.pathname === "/api/clm/zero-touch/activity") {
      activityRequests.push(`${url.pathname}${url.search}`);
    }
    if (/^\/api\/clm\/zero-touch\/cases\/[0-9a-f-]{36}$/i.test(url.pathname)) {
      caseDetailRequests.push(url.pathname);
    }
  });

  const initialResponsePromise = page.waitForResponse((response) => (
    new URL(response.url()).pathname === "/api/clm/zero-touch/activity"
  ));
  await page.getByRole("link", { name: "Audit" }).click();
  const initialResponse = await initialResponsePromise;
  const initialPage = await initialResponse.json() as {
    items: Array<{ case_id: string; timestamp: string }>;
    has_more: boolean;
  };
  await expect(page.getByRole("heading", { name: "Case activity" })).toBeVisible();
  await expect(page.getByText("Actor attribution is not recorded", { exact: false })).toBeVisible();
  expect(activityRequests).toEqual(["/api/clm/zero-touch/activity"]);
  expect(caseDetailRequests).toEqual([]);
  expect(initialPage.items.length).toBeGreaterThan(0);

  const precisionItem = initialPage.items.find((item) => /\.\d{6}(?:Z|\+00:00)$/.test(item.timestamp));
  expect(precisionItem).toBeDefined();
  if (!precisionItem) throw new Error("Expected an activity event with microsecond UTC precision");
  const displayedTimestamp = precisionItem.timestamp.replace(/\+00:00$/, "Z");
  await expect(page.getByText(displayedTimestamp, { exact: true }).first()).toBeVisible();

  const firstCaseId = initialPage.items[0].case_id;
  const firstCaseLink = page.getByRole("link", { name: firstCaseId }).first();
  await expect(firstCaseLink).toHaveAttribute("href", `/cases/${firstCaseId}`);

  const documentResponse = page.waitForResponse((response) => response.url().includes("action=DOCUMENT"));
  await page.getByRole("button", { name: "document" }).click();
  await documentResponse;
  await expect.poll(() => activityRequests.at(-1)).toContain("action=DOCUMENT");

  const stageResponse = page.waitForResponse((response) => response.url().includes("stage=DOCUMENT"));
  await page.getByLabel("Stage").selectOption("DOCUMENT");
  await stageResponse;
  await expect.poll(() => activityRequests.at(-1)).toContain("stage=DOCUMENT");

  const outcomeResponse = page.waitForResponse((response) => response.url().includes("outcome=REVIEW_REQUIRED"));
  await page.getByLabel("Outcome").selectOption("REVIEW_REQUIRED");
  await outcomeResponse;
  await expect.poll(() => activityRequests.at(-1)).toContain("outcome=REVIEW_REQUIRED");

  await page.getByRole("button", { name: "All", exact: true }).click();
  await page.getByLabel("Stage").selectOption("");
  await page.getByLabel("Outcome").selectOption("");
  const pageSizeResponse = page.waitForResponse((response) => response.url().includes("limit=25"));
  await page.getByLabel("Events per page").selectOption("25");
  const boundedPage = await pageSizeResponse;
  const boundedBody = await boundedPage.json() as { has_more: boolean };

  expect(boundedBody.has_more).toBe(true);
  const nextResponse = page.waitForResponse((response) => response.url().includes("offset=25"));
  await page.getByRole("button", { name: "Next" }).click();
  await nextResponse;
  await expect(page.getByText(/Offset 25;/)).toBeVisible();
  await page.getByRole("button", { name: "Previous" }).click();
  await expect(page.getByText(/Offset 0;/)).toBeVisible();

  await page.goto(`/audit/${firstCaseId}`);
  await expect(page.getByText(`for case ${firstCaseId}`, { exact: false })).toBeVisible();
  const clear = page.getByRole("link", { name: "Clear case filter" });
  await expect(clear).toHaveAttribute("href", "/audit");
  await clear.click();
  await expect(page).toHaveURL(/\/audit$/);

  await page.setViewportSize({ width: 480, height: 900 });
  const scroller = page.getByLabel("Case activity events");
  await expect(scroller).toBeVisible();
  await expect.poll(async () => {
    await scroller.focus();
    return scroller.evaluate((element) => document.activeElement === element);
  }).toBe(true);
  const layout = await scroller.evaluate((element) => {
    const bounds = element.getBoundingClientRect();
    return {
      clientWidth: element.clientWidth,
      scrollWidth: element.scrollWidth,
      left: Math.round(bounds.left),
      right: Math.round(bounds.right),
      viewportWidth: document.documentElement.clientWidth,
      rootScrollWidth: document.documentElement.scrollWidth,
    };
  });
  expect(layout.scrollWidth).toBeGreaterThan(layout.clientWidth);
  expect(layout.left).toBeGreaterThanOrEqual(-1);
  expect(layout.right).toBeLessThanOrEqual(layout.viewportWidth + 1);
  expect(layout.rootScrollWidth).toBeLessThanOrEqual(layout.viewportWidth + 1);
});
