import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test, type Page } from "@playwright/test";
import { openStage, openStageSupport } from "./stage-disclosures";
import { reviewPendingFields, reviewSourceChoices } from "./blocker-decisions";
import { createBrowserNetworkPolicy, handleBrowserRoute } from "../playwright.config";

const fixtureRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../backend/tests/fixtures/uat");
let violations: string[];
let requests: string[];

test.beforeEach(async ({ page }) => {
  violations = [];
  requests = [];
  const policy = createBrowserNetworkPolicy({
    frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!,
    backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!,
    allowDirectBackend: false,
  });
  await page.route("**/*", (route) => handleBrowserRoute(route, policy, violations));
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.pathname.startsWith("/api/")) requests.push(`${request.method()} ${url.pathname}`);
  });
});
test.afterEach(() => expect(violations).toEqual([]));

async function measured(action: string, run: () => Promise<void>) {
  const before = requests.length;
  const start = Date.now();
  await run();
  console.log("GARDEN_TIMING", JSON.stringify({ action, elapsed_ms: Date.now() - start,
    browser_network_calls: requests.length - before, external_provider_calls: 0,
    evidence: "offline synthetic protocol; local Mock target; includes UI waits" }));
}

async function summary(page: Page, caseId: string) {
  const response = await page.request.get(`/api/clm/zero-touch/cases/${caseId}`);
  expect(response.status()).toBe(200);
  return response.json();
}

async function reviewedCurrentDocument(page: Page, caseId: string) {
  async function readCurrent() {
    const response = await page.request.get(`/api/onboarding/cases/${caseId}/documents`);
    expect(response.status()).toBe(200);
    const documents = (await response.json()).filter((item: any) => !item.superseded_by_document_id);
    expect(documents).toHaveLength(1);
    expect(documents[0].case_id).toBe(caseId);
    return documents[0];
  }
  let document = await readCurrent();
  const card = page.locator(".document-card:not(.document-card--history)");
  await expect(card).toHaveCount(1);
  await openStage(page, "Document verification");
  await expect(card.getByRole("heading", { name: document.display_name, exact: true })).toBeVisible();
  const pending = document.fields.filter((field: any) => field.review_status === "PENDING");
  if (pending.length) await reviewPendingFields(page);
  await expect.poll(async () => (await readCurrent()).state).toBe("REVIEWED");
  document = await readCurrent();
  expect(document.fields.every((item: any) => item.review_status !== "PENDING")).toBe(true);
  await expect(card.locator(".document-card__header .tag")).toHaveText(document.fields.every((field: any) => field.review_status === "ACCEPTED" && field.comparison_status === "MATCH") ? "Document verified" : "Document processed");
  return document;
}

async function startGarden(page: Page, conflicting: boolean): Promise<string> {
  await page.goto("/");
  await page.getByLabel("User ID").fill("maya-lim");
  await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("link", { name: "New onboarding", exact: true }).click();
  await expect(page.getByText(/synthetic offline test evidence/i).first()).toBeVisible();
  await page.getByLabel("Jurisdiction", { exact: true }).selectOption("SG");
  await page.getByLabel("Company Legal Name", { exact: true }).fill("GARDEN BUSINESS");
  await page.getByLabel("Registration ID / UEN").fill("11111999A");
  const name = conflicting ? "garden-business-conflicting-onboarding-profile.pdf"
    : "garden-business-clean-onboarding-profile.pdf";
  await page.locator("#home-document").setInputFiles(path.join(fixtureRoot, name));
  await measured("create/start case", async () => {
    await page.getByRole("button", { name: "Create onboarding" }).click();
    await expect(page).toHaveURL(/\/new-onboarding\/[0-9a-f-]{36}$/i);
  });
  const caseId = page.url().split("/").at(-1)!;
  await expect.poll(async () => (await summary(page, caseId)).status, { timeout: 90_000 })
    .toBe("WAITING_FOR_REVIEW");
  const current = await summary(page, caseId);
  const acquisition = current.case.registry_acquisition;
  expect(acquisition.status).toBe("PARTIAL");
  expect(acquisition.ownership_parties).toEqual([]);
  expect(acquisition.relationships).toEqual([]);
  expect(acquisition.operation_results.find((item: any) => item.operation === "OWNERSHIP_PARTIES").status).toBe("EMPTY");
  const relationships = acquisition.operation_results.find((item: any) => item.operation === "RELATIONSHIPS");
  expect(relationships.status).toBe("UNSUPPORTED");
  expect(relationships.provenance).toBeNull();
  expect(current.active_exceptions.map((item: any) => item.blocker_code)).not.toContain("REGISTRY_NOT_READY");
  return caseId;
}

async function openGardenDocuments(page: Page, conflicting: boolean): Promise<void> {
  // The heading mounts before the documents query completes. Current evidence
  // can then reveal a UEN conflict and move the active disclosure to Registry.
  // Wait for that query-driven presentation before explicitly inspecting Documents.
  await expect(page.locator(".document-card:not(.document-card--history)")).toHaveCount(1);
  if (conflicting) {
    await expect(page.getByRole("button", { name: "Use document UEN", exact: true })).toBeVisible();
  }
  await openStage(page, "Document verification");
  await expect(page.getByRole("heading", { name: "Document evidence and review" })).toBeVisible();
}

async function createGarden(page: Page, conflicting: boolean): Promise<string> {
  const caseId = await startGarden(page, conflicting);
  await measured("open case", async () => {
    await page.getByRole("button", { name: "Open full case" }).click();
    await expect(page).toHaveURL(`/cases/${caseId}`);
    await openGardenDocuments(page, conflicting);
  });
  return caseId;
}

async function selectClassification(page: Page) {
  await openStage(page, "GoldTier Details & Status");
  const kyc = page.getByLabel("KYC customer type", { exact: true });
  const segment = page.getByLabel("Client segment", { exact: true });
  await expect(kyc).toBeEnabled();
  for (const control of [kyc, segment]) {
    const value = await control.locator("option").evaluateAll((options) =>
      options.map((item) => (item as HTMLOptionElement).value).find(Boolean));
    expect(value).toBeTruthy();
    await control.selectOption(value!);
  }
  await measured("classification save", async () => {
    const response = page.waitForResponse((result) => result.request().method() === "PUT"
      && result.url().endsWith("/target-classification"), { timeout: 15_000 });
    await page.getByRole("button", { name: "Save target classification" }).click();
    expect((await response).status()).toBe(200);
  });
}

async function reviewedOwnership(page: Page, caseId: string) {
  const response = await page.request.get(`/api/onboarding/cases/${caseId}/ownership`);
  expect(response.status()).toBe(200);
  const ownership = await response.json();
  expect(ownership.state).toBe("ANALYZED");
  expect(ownership.source_classification).toBe("OFFICIAL_MOCK_PLUS_LOCAL_SUPPLEMENT");
  expect(ownership.manual_review_receipt).toBeNull();
  expect(ownership.relationships.every((edge: any) => edge.provenance.provider === "LOCAL_SYNTHETIC_SUPPLEMENT"
    && edge.provenance.environment === "LOCAL")).toBe(true);
  expect(ownership.candidates.find((item: any) => item.party.display_name === "ABCD123").aggregated_ownership_percent).toMatch(/^51\.136363750*$/);
  const current = await summary(page, caseId);
  expect(current.case.registry_acquisition.ownership_parties).toEqual([]);
  expect(current.active_exceptions.map((item: any) => item.blocker_code)).toEqual(["TARGET_CONFIRMATION_REQUIRED"]);
  await openStage(page, "Final review & send");
  await expect(page.getByRole("button", { name: "Confirm and send to Mock GoldTier" })).toBeEnabled();
}

test("Garden late preconfirmation detail GET cannot replace completed case", async ({ page }) => {
  const caseId = await createGarden(page, false);
  await selectClassification(page);
  await reviewedOwnership(page, caseId);
  let release!: () => void;
  let captured!: () => void;
  let delivered!: () => void;
  const held = new Promise<void>((resolve) => { release = resolve; });
  const ready = new Promise<void>((resolve) => { captured = resolve; });
  const finished = new Promise<void>((resolve) => { delivered = resolve; });
  let intercepted = false;
  await page.route(`**/api/clm/zero-touch/cases/${caseId}`, async (route) => {
    if (route.request().method() !== "GET" || intercepted) return route.fallback();
    intercepted = true;
    const response = await route.fetch();
    const old = await response.json();
    expect(old.status).toBe("WAITING_FOR_REVIEW");
    expect(old.active_exceptions.map((item: any) => item.blocker_code)).toEqual(["TARGET_CONFIRMATION_REQUIRED"]);
    console.log("GARDEN_STALE_GET", JSON.stringify({ status: old.status, version: old.version,
      current_stage: old.current_stage, source: "ordinary reconnect detail query; offline synthetic" }));
    captured();
    await held;
    // Cancellation is the expected successful outcome after the mutation owner is repaired.
    await route.fulfill({ response }).catch(() => undefined);
    delivered();
  });
  try {
    await page.clock.install();
    await page.clock.fastForward(46_000);
    await page.evaluate(() => window.dispatchEvent(new Event("offline")));
    await page.evaluate(() => window.dispatchEvent(new Event("online")));
    await page.clock.runFor(50);
    await ready;
    const confirmation = page.waitForResponse((result) => result.request().method() === "POST"
      && result.url().endsWith("/target-confirmation"));
    await page.getByRole("button", { name: "Confirm and send to Mock GoldTier" }).click();
    expect((await confirmation).status()).toBe(200);
    const overview = page.getByText("Completed POC workflow", { exact: true });
    await openStage(page, "GoldTier Details & Status");
    await expect(overview).toBeVisible();
    release();
    await finished;
    await page.clock.runFor(100);
    await expect(overview).toBeVisible();
    expect((await summary(page, caseId)).status).toBe("COMPLETED");
    for (const endpoint of ["/api/clm/zero-touch/cases", "/api/clm/zero-touch/cases?status=COMPLETED"]) {
      const response = await page.request.get(endpoint);
      expect(response.status()).toBe(200);
      expect((await response.json()).some((item: any) => item.case_id === caseId && item.status === "COMPLETED"))
        .toBe(true);
    }
    await page.getByRole("link", { name: "Cases", exact: true }).click();
    await expect(page.locator(`a[href="/cases/${caseId}"]`).first()).toBeVisible();
    await page.getByRole("link", { name: "Onboarded", exact: true }).click();
    await expect(page.locator(`a[href="/onboarded/${caseId}"]`).first()).toBeVisible();
  } finally {
    release();
  }
});

test("Garden happy path uses truthful offline protocol evidence and explicit Mock confirmation", async ({ page }, testInfo) => {
  const caseId = await createGarden(page, false);
  const documentsResponse = await page.request.get(`/api/onboarding/cases/${caseId}/documents`);
  const documents = await documentsResponse.json();
  expect(documents).toHaveLength(1);
  expect(documents[0].state).toBe("REVIEWED");
  expect(documents[0].provider_environment).toBe("LOCAL");
  await selectClassification(page);
  await reviewedOwnership(page, caseId);
  await openStage(page, "Document verification");
  await openStage(page, "Registry verification");
  await openStage(page, "Ownership & UBO");
  for (const width of [320, 360, 768, 1280, 1440, 1920]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(page.getByRole("button", { name: "Confirm and send to Mock GoldTier" })).toBeEnabled();
    expect(await page.evaluate(() => document.body.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
    const evidenceWidths = await page.locator(".document-field__evidence dd").evaluateAll((values) => values.filter((value) => value.getClientRects().length > 0).map((value) => value.getBoundingClientRect().width));
    expect(Math.min(...evidenceWidths)).toBeGreaterThan(100);
    await testInfo.attach(`Garden-${width}`, { body: await page.screenshot({ fullPage: true }), contentType: "image/png" });
  }
  // CSS zoom exercises 200% content magnification/reflow in headless Chromium.
  await page.setViewportSize({ width: 1440, height: 900 });
  const header = page.locator(".detail-layout .ds-page-header");
  // Available header width can shrink under content zoom independently of viewport media queries.
  await header.evaluate((element) => { element.style.width = "280px"; });
  try {
    const headerLayout = await header.evaluate((element) => ({
      client: element.clientWidth, scroll: element.scrollWidth,
    }));
    expect(headerLayout.scroll, JSON.stringify(headerLayout)).toBeLessThanOrEqual(headerLayout.client + 1);
    await expect(header.getByRole("combobox", { name: "Case priority", exact: true })).toBeVisible();
    await expect(header.getByRole("button", { name: "Set", exact: true })).toBeVisible();
    await expect(header.locator(".case-header-actions > .tag").last()).toBeVisible();
  } finally {
    await header.evaluate((element) => { element.style.width = ""; });
  }
  await page.evaluate(() => { document.documentElement.style.zoom = "2"; });
  const zoomLayout = await page.evaluate(() => ({
    bodyScroll: document.body.scrollWidth, rootScroll: document.documentElement.scrollWidth,
    rootClient: document.documentElement.clientWidth, innerWidth: window.innerWidth,
    overflow: Array.from(document.querySelectorAll<HTMLElement>("body *"))
      .filter((element) => element.getBoundingClientRect().right > window.innerWidth + 1)
      .slice(0, 20).map((element) => ({ tag: element.tagName, className: element.className,
        right: Math.round(element.getBoundingClientRect().right), width: Math.round(element.getBoundingClientRect().width) })),
  }));
  expect(Math.max(zoomLayout.bodyScroll, zoomLayout.rootScroll), JSON.stringify(zoomLayout)).toBeLessThanOrEqual(zoomLayout.rootClient + 1);
  const zoomEvidenceWidths = await page.locator(".document-field__evidence dd").evaluateAll((values) => values.filter((value) => value.getClientRects().length > 0).map((value) => value.getBoundingClientRect().width));
  expect(Math.min(...zoomEvidenceWidths)).toBeGreaterThan(100);
  const corporateWidths = await page.locator(".case-corporate-evidence .kv-value").evaluateAll((values) => values.filter((value) => value.getClientRects().length > 0).map((value) => value.getBoundingClientRect().width));
  expect(corporateWidths.length).toBeGreaterThan(0);
  expect(Math.min(...corporateWidths)).toBeGreaterThan(100);
  await testInfo.attach("Garden-200-percent-content-zoom", { body: await page.screenshot({ fullPage: true }), contentType: "image/png" });
  await page.evaluate(() => { document.documentElement.style.zoom = ""; });
  const focusBaseline = requests.length;
  await openStage(page, "GoldTier Details & Status");
  await openStageSupport(page, "GoldTier Details & Status", "Technical");
  await page.getByRole("button", { name: "Focus registry evidence" }).click();
  await expect(page.locator("#case-evidence-registry")).toBeFocused();
  await expect(page.getByRole("heading", { name: "Registry data incomplete" })).toHaveCount(0);
  expect(requests.length).toBe(focusBaseline);
  const confirmation = page.waitForResponse((result) => result.request().method() === "POST"
    && result.url().endsWith("/target-confirmation"), { timeout: 15_000 });
  await page.getByRole("button", { name: "Confirm and send to Mock GoldTier" }).click();
  expect((await confirmation).status()).toBe(200);
  await openStage(page, "GoldTier Details & Status");
  await expect(page.getByText("Completed POC workflow")).toBeVisible({ timeout: 90_000 });
  const completed = await summary(page, caseId);
  expect(completed.status).toBe("COMPLETED");
  expect(completed.active_exceptions).toEqual([]);
  expect(completed.processing_pipeline.find((item: any) => item.node_id === "ACRA_REGISTRY").status).toBe("COMPLETE");
  const history = await page.request.get("/api/clm/zero-touch/cases");
  const onboarded = await page.request.get("/api/clm/zero-touch/cases?status=COMPLETED");
  expect(history.status()).toBe(200);
  expect(onboarded.status()).toBe(200);
  expect((await history.json()).some((item: any) => item.case_id === caseId && item.status === "COMPLETED"))
    .toBe(true);
  expect((await onboarded.json()).some((item: any) => item.case_id === caseId && item.status === "COMPLETED"))
    .toBe(true);
  await page.getByRole("link", { name: "Cases", exact: true }).click();
  await expect(page.locator(`a[href="/cases/${caseId}"]`).first()).toBeVisible();
  await page.getByRole("link", { name: "Onboarded", exact: true }).click();
  await expect(page.locator(`a[href="/onboarded/${caseId}"]`)).toBeVisible();
});

test("Garden discrepancy human intervention clears reviewed conflicts and continues onboarding", async ({ page }) => {
  const caseId = await createGarden(page, true);
  await reviewedCurrentDocument(page, caseId);
  await expect(page.locator('input[data-reconciliation-field][value="KEEP_REGISTRY_VALUE"]')).toHaveCount(4);
  await measured("reconciliation decision group", () => reviewSourceChoices(page).then(() => undefined));
  const reconciled = await summary(page, caseId);
  expect(reconciled.case.entity.legal_name).toBe("GARDEN BUSINESS");
  expect(reconciled.case.entity.registration_number).toBe("11111999A");
  expect(reconciled.reconciliation.discrepancies.filter((item: any) => item.decision)).toHaveLength(4);
  await selectClassification(page);
  await reviewedOwnership(page, caseId);
  expect((await summary(page, caseId)).status).not.toBe("COMPLETED");
});

test("Garden delayed current document rendering cannot skip required field review", async ({ page }) => {
  let release!: () => void;
  const held = new Promise<void>((resolve) => { release = resolve; });
  let delayed = false;
  await page.route("**/api/onboarding/cases/*/documents", async (route) => {
    if (route.request().method() === "GET") {
      delayed = true;
      await held;
    }
    await route.fallback();
  });
  try {
    const caseId = await startGarden(page, true);
    await page.getByRole("button", { name: "Open full case" }).click();
    await expect(page).toHaveURL(`/cases/${caseId}`);
    await expect.poll(() => delayed).toBe(true);
    // Reproduce the former verifier's instantaneous optional-control check while
    // the real document GET is held. None of the four pending fields was reviewed.
    const fields = ["registration number", "legal name", "registered address", "country of incorporation"];
    const instantSkipped = [];
    for (const field of fields) {
      if (!(await page.getByRole("button", { name: `Accept ${field} suggestion` }).count())) {
        instantSkipped.push(field);
      }
    }
    expect(instantSkipped).toEqual(fields);
    const response = await page.request.get(`/api/onboarding/cases/${caseId}/documents`);
    const initial = (await response.json())[0];
    expect(initial.fields.every((field: any) => field.review_status === "PENDING")).toBe(true);
    // Start the repaired verifier before releasing the GET. Its condition-based
    // waits must remain pending until the actual current evidence renders.
    let settled = false;
    const repaired = (async () => {
      await openGardenDocuments(page, true);
      const document = await reviewedCurrentDocument(page, caseId);
      settled = true;
      return document;
    })();
    expect(settled).toBe(false);
    release();
    const reviewed = await repaired;
    expect(reviewed.document_id).toBe(initial.document_id);
    expect(reviewed.events.filter((event: any) => event.event_type === "DOCUMENT_FIELD_ACCEPTED"))
      .toHaveLength(4);
    expect(reviewed.events.length).toBeGreaterThanOrEqual(initial.events.length + 4);
    expect(reviewed.state).toBe("REVIEWED");
  } finally {
    release();
  }
});

test("Garden document arrival settles identity focus before explicit Documents inspection", async ({ page }) => {
  let release!: () => void;
  const held = new Promise<void>((resolve) => { release = resolve; });
  await page.route("**/api/onboarding/cases/*/documents", async (route) => {
    if (route.request().method() === "GET") await held;
    await route.fallback();
  });
  try {
    const caseId = await startGarden(page, true);
    await page.getByRole("button", { name: "Open full case" }).click();
    await expect(page).toHaveURL(`/cases/${caseId}`);
    await openStage(page, "Document verification");
    const documents = page.getByRole("region", { name: "Document verification", exact: true });
    await expect(documents.locator(":scope > div").first()).toBeVisible();
    await expect(documents.locator(":scope > details[open]")).toHaveCount(0);
    release();
    await expect(page.getByRole("button", { name: "Use document UEN", exact: true })).toBeVisible();
    await expect(documents.locator(":scope > div").first()).toBeVisible();
    await expect(documents.locator(":scope > details[open]")).toHaveCount(0);
    expect(await page.locator("#documents-heading").count()).toBe(1);
    // The original createGarden heading assertion failed here for 15 seconds:
    // the panel is mounted, but the query-derived active-stage change hid it.
    await openGardenDocuments(page, true);
    await expect(documents.locator(":scope > div").first()).toBeVisible();
    await expect(documents.locator(":scope > details[open]")).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Document evidence and review" })).toBeVisible();
    expect((await summary(page, caseId)).current_stage).toBe("DOCUMENT");
  } finally {
    release();
  }
});
