import { mkdir, readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test, type Locator, type Page } from "@playwright/test";
import { openStage, openStageSupport } from "./stage-disclosures";
import { assertRegistryBindingTimestamps } from "./registry-binding-timestamps";
import { reviewPendingFields } from "./blocker-decisions";
import type { OwnershipAnalysisRecord, PolicyCatalogue, RegistryEvidenceBinding } from "../src/types";
import {
  createBrowserNetworkPolicy,
  retainedEvidencePath,
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


function legalNameForUen(uen: string): string {
  return uen === "202400006F"
    ? "CYCLIC HARBOUR HOLDINGS PTE. LTD."
    : "MERLION CIRCULAR LABS PTE. LTD.";
}

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

// A single explicit alias label scores 0.90 under the deterministic native parser.
// Freeze a higher approved POC threshold to retain a genuine low-score suggestion,
// independently of the historical PDF's separate ambiguity fixture.
const singleValueReviewFixture = {
  name: "single-value-low-score.txt",
  mimeType: "text/plain",
  buffer: Buffer.from([
    "UEN: 202400001A",
    "Company: MERLION CIRCULAR LABS PTE. LTD.",
    "Registered Address: 18 INNOVATION WAY, #04-01, 018956, SG",
    "Country: SG",
  ].join("\n")),
};

async function prepareSingleValueReviewPolicy(page: Page) {
  const loginSetupActor = async (userId: string, credential = requiredEnvironment("CLM_E2E_PASSWORD")) => {
    const response = await page.request.post("/api/auth/login", {
      data: { user_id: userId, password: credential },
    });
    expect(response.status()).toBe(200);
    return await response.json() as { csrf_token: string };
  };
  const proposer = await loginSetupActor("hr-admin");
  const proposerHeaders = { "X-CSRF-Token": proposer.csrf_token };
  const currentResponse = await page.request.get("/api/policies");
  expect(currentResponse.status()).toBe(200);
  const current = await currentResponse.json() as PolicyCatalogue;
  const reason = "Synthetic single-value evidence score review fixture";
  const draftResponse = await page.request.post("/api/policies/proposals", {
    data: { expected_catalogue_version: current.version,
      changes: { DOCUMENT_IDP_REVIEW_CONFIDENCE_THRESHOLD: { type: "DECIMAL", value: "0.92" } }, reason },
    headers: proposerHeaders,
  });
  expect(draftResponse.status()).toBe(201);
  const draft = await draftResponse.json() as PolicyCatalogue;
  const proposal = draft.proposals!.find((item) => item.reason === reason)!;
  expect(proposal).toBeDefined();
  const submittedResponse = await page.request.post(`/api/policies/proposals/${proposal.proposal_id}/submit`, {
    data: { expected_catalogue_version: draft.version, expected_proposal_version: proposal.version },
    headers: proposerHeaders,
  });
  expect(submittedResponse.status()).toBe(200);
  const submitted = await submittedResponse.json() as PolicyCatalogue;
  const pending = submitted.proposals!.find((item) => item.proposal_id === proposal.proposal_id)!;
  expect((await page.request.post("/api/auth/logout", { headers: proposerHeaders })).status()).toBe(204);
  const director = await loginSetupActor("olivia-koh");
  const directorHeaders = { "X-CSRF-Token": director.csrf_token };
  const approvedResponse = await page.request.post(`/api/policies/proposals/${proposal.proposal_id}/decision`, {
    data: { expected_catalogue_version: submitted.version, expected_proposal_version: pending.version,
      approve: true, reason: "Independent synthetic Director approval for one-value review coverage" },
    headers: directorHeaders,
  });
  expect(approvedResponse.status()).toBe(200);
  const approved = await approvedResponse.json() as PolicyCatalogue;
  expect(approved.rules.find((rule) => rule.policy_id === "DOCUMENT_IDP_REVIEW_CONFIDENCE_THRESHOLD")?.value)
    .toEqual({ type: "DECIMAL", value: "0.92" });
  expect((await page.request.post("/api/auth/logout", { headers: directorHeaders })).status()).toBe(204);
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

async function confirmMockTarget(page: Page) {
  if (new URL(page.url()).pathname.startsWith("/new-onboarding/")) {
    await page.getByRole("button", { name: "Open full case" }).click();
    await expect(page).toHaveURL(/\/cases\/[0-9a-f-]{36}$/i);
  }
  const confirmation = page.getByRole("button", { name: "Confirm and send to Mock GoldTier" });
  await expect(confirmation).toBeEnabled({ timeout: 120_000 });
  const response = page.waitForResponse((result) => (
    result.request().method() === "POST"
      && new URL(result.url()).pathname.endsWith("/target-confirmation")
  ));
  await confirmation.click();
  expect((await response).status()).toBe(200);
}

async function expectDocumentContained(page: Page) {
  const layout = await page.evaluate(() => {
    const viewportWidth = document.documentElement.clientWidth;
    return {
      bodyClientWidth: document.body.clientWidth,
      bodyScrollWidth: document.body.scrollWidth,
      viewportWidth,
      visibleOverflow: Array.from(document.querySelectorAll<HTMLElement>("body *"))
        .filter((element) => element.getBoundingClientRect().right > viewportWidth + 1)
        .slice(0, 12)
        .map((element) => ({
          tag: element.tagName,
          className: element.className,
          right: Math.round(element.getBoundingClientRect().right),
          width: Math.round(element.getBoundingClientRect().width),
        })),
    };
  });
  expect(layout.bodyScrollWidth, JSON.stringify(layout.visibleOverflow)).toBeLessThanOrEqual(layout.bodyClientWidth + 1);
  expect(layout.bodyClientWidth).toBeLessThanOrEqual(layout.viewportWidth + 1);
}

async function expectReviewContained(page: Page, review: Locator) {
  const layout = await review.evaluate((element) => {
    const bounds = element.getBoundingClientRect();
    return {
      clientWidth: element.clientWidth,
      scrollWidth: element.scrollWidth,
      left: bounds.left,
      right: bounds.right,
      viewportWidth: document.documentElement.clientWidth,
    };
  });
  expect(layout.scrollWidth).toBeLessThanOrEqual(layout.clientWidth + 1);
  expect(layout.left).toBeGreaterThanOrEqual(-1);
  expect(layout.right).toBeLessThanOrEqual(layout.viewportWidth + 1);
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

test("ordinary RM repairs same-case identity, resolves evidence, and reviews without target writes", async ({ page }, testInfo) => {
  const operatorRouteArtifactDirectory = retainedEvidencePath("operator-route");
  test.setTimeout(240_000);
  const mutationRequests: Array<{ method: string; path: string }> = [];
  page.on("request", (request) => {
    if (request.method() !== "GET") {
      mutationRequests.push({ method: request.method(), path: new URL(request.url()).pathname });
    }
  });

  await mkdir(operatorRouteArtifactDirectory, { recursive: true });
  await page.goto("/");
  await login(page, "maya-lim");

  // Setup only: seed a retained legacy case before the reviewer journey begins.
  // The browser then uses Cases, the blocker tile, and every corrective mutation.
  const sessionResponse = await page.request.get("/api/auth/me");
  expect(sessionResponse.status()).toBe(200);
  const session = await sessionResponse.json() as { csrf_token: string };
  const mutationHeaders = { "X-CSRF-Token": session.csrf_token };
  const createResponse = await page.request.post("/api/clm/zero-touch/cases", {
    data: {
      uen: "202400001A",
      legal_name: legalNameForUen("202400001A"),
    },
    headers: mutationHeaders,
  });
  expect(createResponse.status()).toBe(201);
  const created = await createResponse.json() as { case: { case_id: string } };
  const caseId = created.case.case_id;
  const initialResponse = await page.request.get(`/api/clm/zero-touch/cases/${caseId}`);
  expect(initialResponse.status()).toBe(200);
  const initialProjection = await initialResponse.json() as {
    active_exceptions: Array<{ blocker_code: string }>;
    stage_order_version: number;
    processing_pipeline: Array<{
      node_id: string;
      status: string;
      children: Array<any>;
    }>;
  };
  expect(initialProjection.active_exceptions)
    .toEqual(expect.arrayContaining([expect.objectContaining({ blocker_code: "INITIAL_IDENTITY_INCOMPLETE" })]));
  expect(initialProjection.stage_order_version).toBe(2);
  const flattenedPipeline = (nodes: typeof initialProjection.processing_pipeline): typeof initialProjection.processing_pipeline => (
    nodes.flatMap((node) => [node, ...flattenedPipeline(node.children)])
  );
  const initialNodes = flattenedPipeline(initialProjection.processing_pipeline);
  const searchIndex = initialNodes.findIndex((node) => node.node_id === "GOLDTIER_SEARCH");
  const registryIndex = initialNodes.findIndex((node) => node.node_id === "ACRA_REGISTRY");
  expect(searchIndex).toBeGreaterThanOrEqual(0);
  expect(registryIndex).toBeGreaterThan(searchIndex);
  expect(initialNodes[registryIndex]?.status).toBe("NOT_REACHED");
  const evidenceBytes = await readFile(lowConfidenceFixture);
  const seededEvidence = (async () => {
    for (let attempt = 0; attempt < 120; attempt += 1) {
      const documentResponse = await page.request.post(
        `/api/clm/zero-touch/cases/${caseId}/intake/documents`,
        {
          data: evidenceBytes,
          headers: {
            ...mutationHeaders,
            "Content-Type": "application/pdf",
            "X-Document-Name": "low-confidence.pdf",
          },
        },
      );
      if (documentResponse.status() === 201) {
        const completeResponse = await page.request.post(
          `/api/clm/zero-touch/cases/${caseId}/intake/complete`,
          {
            data: { expected_document_count: 1 },
            headers: mutationHeaders,
          },
        );
        expect(completeResponse.status()).toBe(200);
        return;
      }
      expect(documentResponse.status()).toBe(409);
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
    throw new Error("Seeded evidence did not become attachable after identity correction.");
  })();

  await openWorkspaceTab(page, "Cases");
  await page.getByLabel("Search cases").fill(caseId);
  const caseLink = page.locator(`a[href="/cases/${caseId}"]`).first();
  await expect(caseLink).toBeVisible();
  await caseLink.click();
  await expect(page).toHaveURL(`/cases/${caseId}`);
  await expect(page.getByRole("heading", { name: "Action required" })).toBeVisible();
  const identityInterventionDetails = page.locator(".intervention-card .evidence-details")
    .filter({ hasText: "INITIAL_IDENTITY_INCOMPLETE" });
  await expect(identityInterventionDetails).toHaveCount(1);
  await identityInterventionDetails.getByText("Why is this blocked?", { exact: true }).click();
  await expect(identityInterventionDetails.locator(":scope > code")).toHaveText("INITIAL_IDENTITY_INCOMPLETE");
  await expect(identityInterventionDetails.locator(":scope > code")).toBeVisible();
  const identityStage = page.locator(".onboarding-progress__stage--actionable > button").filter({
    hasText: "Initial identity",
  });
  await expect(identityStage).toBeVisible();
  await identityStage.click();
  const identityCorrection = page.locator("#identity-registration-number");
  await expect(identityCorrection).toBeFocused();
  const searchWorkspace = page.getByRole("region", { name: "Existing-customer search", exact: true });
  const registryWorkspace = page.locator(".stage-disclosure").filter({ has: page.getByRole("heading", { name: "Registry verification", exact: true }) });
  await expect(searchWorkspace).toContainText("No Search result is retained for this case.");
  await expect(page.locator("#case-identity-correction")).toHaveCount(1);
  await expect(registryWorkspace.locator("#case-identity-correction")).toHaveCount(1);
  await expect(searchWorkspace.locator("#case-identity-correction")).toHaveCount(0);
  const navigationStart = mutationRequests.length;
  for (const width of [1440, 1280, 900, 360]) {
    await page.setViewportSize({ width, height: 900 });
    const searchLink = searchWorkspace.getByRole("button", { name: "Review identity for Search recheck", exact: true });
    await expect(searchLink).toBeEnabled();
    await searchLink.focus();
    await page.keyboard.press("Enter");
    await expect(identityCorrection).toBeFocused();
    await expect(identityCorrection).toBeVisible();
    const banner = page.locator(".nav-meta .environment-banner");
    await expect(banner.locator(".environment-banner__label")).toBeVisible();
    expect(await banner.ariaSnapshot()).toContain("External access is backend-managed");
    await expectDocumentContained(page);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  }
  expect(mutationRequests.slice(navigationStart)).toEqual([]);
  await expect(page.getByRole("heading", { name: "Complete company details" })).toBeVisible();

  const actionableStage = identityStage;
  await expect(actionableStage).toBeVisible();
  await expect(actionableStage.locator(".onboarding-progress__stage-label")).toHaveText(
    "Initial identity",
  );
  for (const width of [320, 360] as const) {
    await page.setViewportSize({ width, height: 900 });
    await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
    await page.mouse.move(0, 0);
    await actionableStage.scrollIntoViewIfNeeded();
    await expectDocumentContained(page);
    await actionableStage.screenshot({
      path: path.join(operatorRouteArtifactDirectory, `${width}-long-label-default.png`),
    });
    await actionableStage.hover();
    await actionableStage.screenshot({
      path: path.join(operatorRouteArtifactDirectory, `${width}-long-label-hover.png`),
    });
    await page.mouse.move(0, 0);
    await actionableStage.focus();
    await page.keyboard.press("Shift+Tab");
    await page.keyboard.press("Tab");
    await expect(actionableStage).toBeFocused();
    const focusStyle = await actionableStage.evaluate((button) => {
      const style = getComputedStyle(button);
      return {
        color: style.outlineColor,
        offset: style.outlineOffset,
        width: style.outlineWidth,
      };
    });
    expect(focusStyle).toEqual({ color: "rgb(54, 86, 165)", offset: "2px", width: "3px" });
    await actionableStage.screenshot({
      path: path.join(operatorRouteArtifactDirectory, `${width}-long-label-focus.png`),
    });
    await page.locator(".onboarding-progress").screenshot({
      path: path.join(operatorRouteArtifactDirectory, `${width}-long-label-focus-context.png`),
    });
  }

  await page.getByLabel("Legal company name").fill(legalNameForUen("202400001A"));
  await page.getByLabel("Singapore UEN").fill("202400001A");
  const identityResponse = page.waitForResponse((response) => (
    response.request().method() === "POST"
      && new URL(response.url()).pathname === `/api/clm/zero-touch/cases/${caseId}/identity-search-recheck`
  ));
  await page.getByRole("button", { name: "Save details and recheck Search" }).click();
  expect((await identityResponse).status()).toBe(200);
  await seededEvidence;
  await page.reload();
  await expect(page).toHaveURL(`/cases/${caseId}`);
  await expect(page.getByText("INITIAL_IDENTITY_INCOMPLETE", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Document evidence and review" })).toBeVisible();

  await reviewPendingFields(page, { legal_name: legalNameForUen("202400001A") });

  const replacementInput = page.getByLabel("Replace current document");
  await expect(replacementInput).toBeEnabled();
  const replacementResponse = page.waitForResponse((response) => (
    response.request().method() === "POST"
      && new URL(response.url()).pathname.endsWith("/replacement")
  ));
  await replacementInput.setInputFiles(cleanFixture);
  expect((await replacementResponse).status()).toBe(200);

  const classification = page.getByRole("heading", { name: "Target classification" });
  await openStage(page, "Submission readiness");
  await expect(classification).toBeVisible({ timeout: 120_000 });
  const kyc = page.getByLabel("KYC customer type");
  const segment = page.getByLabel("Client segment");
  await expect(kyc).toBeEnabled();
  await expect(segment).toBeEnabled();
  const selectDifferentAllowedValue = async (select: typeof kyc): Promise<string> => {
    const current = await select.inputValue();
    const allowedValues = await select.locator("option").evaluateAll((options) => (
      options.map((option) => (option as HTMLOptionElement).value).filter(Boolean)
    ));
    const next = allowedValues.find((value) => value !== current);
    expect(next, "an allowed value different from the retained selection").toBeDefined();
    await select.selectOption(next!);
    return next!;
  };
  const selectedKyc = await selectDifferentAllowedValue(kyc);
  const selectedSegment = await selectDifferentAllowedValue(segment);
  const saveClassification = page.getByRole("button", { name: "Save target classification" });
  await expect(saveClassification).toBeEnabled();
  const classificationResponse = page.waitForResponse((response) => (
    response.request().method() === "PUT"
      && new URL(response.url()).pathname === `/api/clm/zero-touch/cases/${caseId}/target-classification`
  ));
  await saveClassification.click();
  const classificationResult = await classificationResponse;
  expect(classificationResult.status()).toBe(200);
  const classificationProjection = await classificationResult.json() as {
    ownership_edit_authorized: boolean;
    clm: {
      submission_plan: {
        request_preview: {
          operations: Array<{ operation: string; fields: Array<{ target_field: string }> }>;
        } | null;
      };
    };
  };
  const expectedOperationFields: Record<string, string[]> = {
    SEARCH: ["registrationNumber"],
    SHELL: [
      "party.partyRole",
      "party.partyType",
      "party.names.legalName",
      "party.nonIndividualProfile.countryOfIncorporation",
      "sourceContext.sourceSystem",
      "sourceContext.sourceCaseId",
      "sourceContext.acceptedBy",
      "sourceContext.acceptedAt",
      "sourceContext.sourceChannel",
    ],
    POLICY: [
      "goldTierId",
      "customerExternalSystem",
      "customerExternalSystemKey",
      "policyDetails.policy",
      "sourceContext.sourceSystem",
      "sourceContext.sourceCaseId",
      "sourceContext.acceptedBy",
      "sourceContext.acceptedAt",
      "sourceContext.sourceChannel",
    ],
    AMEND: [
      "partyType",
      "policy",
      "party.names.legalName",
      "party.addresses[0].addressLine1",
      "party.addresses[0].addressLine2",
      "party.addresses[0].postalCode",
      "party.addresses[0].country",
      "sourceContext.sourceSystem",
      "sourceContext.sourceCaseId",
      "sourceContext.acceptedBy",
      "sourceContext.acceptedAt",
      "sourceContext.sourceChannel",
    ],
  };
  const projectedOperations = classificationProjection.clm.submission_plan.request_preview?.operations;
  expect(projectedOperations?.map((operation) => operation.operation)).toEqual([
    "SEARCH",
    "SHELL",
    "POLICY",
    "AMEND",
  ]);
  expect(Object.fromEntries(
    (projectedOperations ?? []).map((operation) => [
      operation.operation,
      operation.fields.map((field) => field.target_field),
    ]),
  )).toEqual(expectedOperationFields);
  const review = page.locator(".review-and-send");
  await expect(review.getByRole("heading", { name: "Review and send" })).toBeVisible();
  const exactLabel = (value: string) => new RegExp(
    `^${value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}$`,
    "i",
  );
  await expect(review.getByText(exactLabel(selectedKyc))).toBeVisible({ timeout: 30_000 });
  await expect(review.getByText(exactLabel(selectedSegment))).toBeVisible();
  await expect(review.getByText("Legal form", { exact: true })).toBeVisible();
  await expect(review.getByText("Owning team", { exact: true })).toBeVisible();
  await expect(review.getByRole("button", { name: "Edit company details" })).toBeVisible();
  await expect(review.getByRole("button", { name: "Edit classification" })).toBeVisible();
  await expect(review.getByRole("button", { name: "Edit documents" })).toBeVisible();
  expect(classificationProjection.ownership_edit_authorized).toBe(true);
  await expect(review.getByRole("button", { name: "Edit ownership" })).toBeEnabled();
  await expect(review.getByText("Ownership source is review-only; no correction action is currently authorized.")).toHaveCount(0);
  const presentedFieldLabel = (value: string) => value
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/^./, (letter) => letter.toUpperCase());
  for (const [operationName, fields] of Object.entries(expectedOperationFields)) {
    const operation = review.locator(".review-and-send__operation").filter({
      has: page.getByRole("heading", { name: `${presentedFieldLabel(operationName)} - Valid` }),
    });
    await expect(operation).toBeVisible();
    expect(await operation.locator("dt").allTextContents()).toEqual(fields.map(presentedFieldLabel));
  }
  await expect(review.getByText("Document review incomplete", { exact: true })).toHaveCount(0);
  await expect(review.getByText("Ownership required", { exact: true })).toHaveCount(0);
  const confirm = review.getByRole("button", { name: "Confirm and send to Mock GoldTier" });
  await expect(confirm).toBeEnabled();

  await review.getByRole("button", { name: "Edit company details" }).click();
  await expect(page.locator("#identity-registration-number")).toBeFocused();
  await expect(page.locator("#case-identity-correction").getByRole("heading", { name: "Registry identity" })).toBeVisible();
  await review.getByRole("button", { name: "Edit classification" }).click();
  await expect(page.getByLabel("KYC customer type", { exact: true })).toBeFocused();
  await review.getByRole("button", { name: "Edit documents" }).click();
  await expect(page.locator("#case-blocker-review select[data-review-field], #case-blocker-review select[data-reconciliation-field], #case-evidence-documents input[type=file]").first()).toBeFocused();
  await review.getByRole("button", { name: "Edit ownership" }).click();
  await expect(page.locator("#case-manual-ownership-evidence :is(input:not([disabled]):not([readonly]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]))").first()).toBeFocused();

  const printButton = review.getByRole("button", { name: "Print / save PDF" });
  for (const width of [320, 360, 768, 1280, 1440, 1920] as const) {
    await page.setViewportSize({ width, height: 1000 });
    await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
    await page.mouse.move(0, 0);
    await review.scrollIntoViewIfNeeded();
    await expectDocumentContained(page);
    await review.screenshot({ path: path.join(operatorRouteArtifactDirectory, `${width}-review-default.png`) });
    await printButton.hover();
    await expectDocumentContained(page);
    await review.screenshot({ path: path.join(operatorRouteArtifactDirectory, `${width}-review-hover.png`) });
    await printButton.focus();
    await expect(printButton).toBeFocused();
    await expectDocumentContained(page);
    await review.screenshot({ path: path.join(operatorRouteArtifactDirectory, `${width}-review-focus.png`) });
  }
  await page.setViewportSize({ width: 320, height: 1000 });
  await review.screenshot({ path: path.join(operatorRouteArtifactDirectory, "320-review-reflow.png") });
  await expectDocumentContained(page);
  await expectReviewContained(page, review);
  await page.setViewportSize({ width: 640, height: 1000 });
  await page.evaluate(() => { document.documentElement.style.zoom = "2"; });
  await expectDocumentContained(page);
  await expectReviewContained(page, review);
  await review.screenshot({ path: path.join(operatorRouteArtifactDirectory, "200-percent-review-reflow.png") });
  await page.evaluate(() => { document.documentElement.style.zoom = ""; });

  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({ path: path.join(operatorRouteArtifactDirectory, "1440-final-review.png"), fullPage: true });
  await review.screenshot({ path: path.join(operatorRouteArtifactDirectory, "1440-review-and-send.png") });

  await page.emulateMedia({ media: "print" });
  await page.evaluate(() => window.dispatchEvent(new Event("beforeprint")));
  await expect(review).toHaveCSS("position", "static");
  await expect(review).toHaveCSS("border-top-width", "0px");
  await expect(review.locator(".review-and-send__print")).toHaveCSS("display", "none");
  await expect(review.locator(".review-and-send__actions")).toHaveCSS("display", "none");
  await expect(review.locator(".review-and-send__technical-content")).toBeVisible();
  const hasA4PageRule = await page.evaluate(() => {
    const containsA4Page = (rules: CSSRuleList): boolean => Array.from(rules).some((rule) => {
      const cssText = rule.cssText.toLowerCase();
      if (cssText.includes("@page") && cssText.includes("size: a4")) return true;
      return "cssRules" in rule && containsA4Page((rule as CSSGroupingRule).cssRules);
    });
    return Array.from(document.styleSheets).some((sheet) => {
      try {
        return containsA4Page(sheet.cssRules);
      } catch {
        return false;
      }
    });
  });
  expect(hasA4PageRule).toBe(true);
  await page.pdf({
    path: path.join(operatorRouteArtifactDirectory, "review-and-send-a4.pdf"),
    format: "A4",
    printBackground: true,
    preferCSSPageSize: true,
    displayHeaderFooter: true,
    headerTemplate: "<span></span>",
    footerTemplate: '<div style="box-sizing:border-box;width:100%;padding:0 14mm;font-size:8px;text-align:right;color:#444">Page <span class="pageNumber"></span></div>',
  });
  await page.evaluate(() => window.dispatchEvent(new Event("afterprint")));

  expect(mutationRequests).toContainEqual({
    method: "POST",
    path: `/api/clm/zero-touch/cases/${caseId}/identity-search-recheck`,
  });
  expect(mutationRequests).toContainEqual({
    method: "PUT",
    path: `/api/clm/zero-touch/cases/${caseId}/target-classification`,
  });
  expect(mutationRequests).not.toContainEqual({
    method: "POST",
    path: `/api/clm/zero-touch/cases/${caseId}/target-confirmation`,
  });
  expect(mutationRequests).not.toContainEqual({
    method: "POST",
    path: `/api/clm/zero-touch/cases/${caseId}/target-recovery`,
  });
});

test("authorized manual ownership action focuses the real evidence form and next action", async ({ page }) => {
  test.setTimeout(180_000);
  await page.goto("/");
  await login(page);

  await openFreshOnboarding(page);
  await page.getByLabel("Jurisdiction").selectOption("SG");
  await page.getByLabel("Company Legal Name").fill(legalNameForUen("202400006F"));
  await page.getByLabel("Registration ID / UEN").fill("202400006F");
  await page.locator("#home-document").setInputFiles(ownershipCycleFixture);
  await page.getByRole("button", { name: "Create onboarding" }).click();
  await expect(page).toHaveURL(/\/new-onboarding\/([0-9a-f-]{36})$/i);
  const caseId = page.url().split("/").at(-1)!;
  await expect.poll(async () => {
    const response = await page.request.get(`/api/clm/zero-touch/cases/${caseId}`);
    if (!response.ok()) return null;
    const summary = await response.json() as {
      ownership_recovery?: { manual_evidence_action: string | null } | null;
    };
    return summary.ownership_recovery?.manual_evidence_action ?? null;
  }, { timeout: 120_000 }).toBe("MANUAL_OWNERSHIP_EVIDENCE");
  const summaryResponse = await page.request.get(`/api/clm/zero-touch/cases/${caseId}`);
  const summaryBody = await summaryResponse.json() as {
    target_operations: Array<{ operation: string; status: string }>;
  };
  expect(Object.fromEntries(summaryBody.target_operations.map((item) => [item.operation, item.status]))).toEqual({
    SEARCH: "NO_MATCH",
    SHELL: "NOT_ATTEMPTED",
    POLICY: "NOT_ATTEMPTED",
    AMEND: "NOT_ATTEMPTED",
  });

  await page.goto(`/cases/${caseId}`);
  const review = page.locator(".review-and-send");
  await expect(review).toHaveCount(0);
  await expect(page.locator(".stage-disclosure--final")).toContainText("Not yet available");
  await expect(page.getByRole("heading", { name: "Review or edit ownership evidence" })).toBeVisible();
  await page.locator(".intervention-card").getByRole("button", { name: "Add structured ownership details" }).click();
  await expect(page.locator("#case-manual-ownership-evidence :is(input:not([disabled]):not([readonly]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]))").first()).toBeFocused();
  await expect(page.getByRole("button", { name: "Submit manual ownership evidence" })).toBeVisible();
});

test("onboarding progress is visible while backend-authored stages advance", async ({ page }, testInfo) => {
  let caseReadCount = 0;
  let showObservedProgress = true;
  await page.route("**/api/clm/zero-touch/cases/*/intake/documents", async (route) => {
    if (route.request().method() !== "POST") {
      await route.fallback();
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 3_500));
    await route.fallback();
  });
  await page.route("**/api/clm/zero-touch/cases/*", async (route) => {
    const url = new URL(route.request().url());
    if (
      route.request().method() !== "GET"
      || !/^\/api\/clm\/zero-touch\/cases\/[0-9a-f-]{36}$/i.test(url.pathname)
    ) {
      await route.fallback();
      return;
    }
    const response = await route.fetch();
    const payload = await response.json() as Record<string, unknown> & {
      processing_pipeline: Array<Record<string, unknown>>;
      version: number;
    };
    if (!showObservedProgress) {
      await route.fulfill({ response, json: payload });
      return;
    }
    caseReadCount += 1;
    const activeNode = caseReadCount === 1 ? "DOCUMENT_IDP" : "OWNERSHIP_UBO";
    const completedNodes = new Set(
      caseReadCount === 1
        ? ["CASE_START", "INITIAL_IDENTITY", "JURISDICTION", "GOLDTIER_SEARCH", "ACRA_REGISTRY"]
        : ["CASE_START", "INITIAL_IDENTITY", "JURISDICTION", "GOLDTIER_SEARCH", "ACRA_REGISTRY", "DOCUMENT_IDP", "RECONCILIATION"],
    );
    payload.status = "RUNNING";
    payload.current_stage = caseReadCount === 1 ? "DOCUMENT" : "OWNERSHIP";
    payload.version += caseReadCount;
    payload.updated_at = caseReadCount === 1
      ? "2026-09-28T04:00:01Z"
      : "2026-09-28T04:00:02Z";
    payload.processing_pipeline = payload.processing_pipeline.map((node) => ({
      ...node,
      status: node.node_id === activeNode
        ? "IN_PROGRESS"
        : completedNodes.has(String(node.node_id))
          ? "COMPLETE"
          : "NOT_REACHED",
    }));
    await route.fulfill({ response, json: payload });
  });

  await page.goto("/");
  await login(page);
  await openFreshOnboarding(page);
  await page.getByLabel("Jurisdiction").selectOption("SG");
  await page.getByLabel("Company Legal Name").fill(legalNameForUen("202400001A"));
  await page.getByLabel("Registration ID / UEN").fill("202400001A");
  await page.locator("#home-document").setInputFiles(cleanFixture);
  await page.getByRole("button", { name: "Create onboarding" }).click();

  const progress = page.getByRole("region", { name: "Onboarding progress" });
  await expect(page).toHaveURL(/\/new-onboarding\/[0-9a-f-]{36}$/i);
  await expect(progress).toBeVisible();
  await expect(progress.getByRole("progressbar")).toHaveAttribute("aria-valuenow");
  await testInfo.attach("progress-immediately-after-case-start", {
    body: await page.screenshot(),
    contentType: "image/png",
  });

  await expect(progress.getByText("Document verification", { exact: true })).toBeVisible();
  await expect(progress.getByText("Current:").locator("..")).toContainText("Document verification — In progress");
  await expect.poll(() => caseReadCount).toBeGreaterThanOrEqual(1);
  await testInfo.attach("progress-document-stage-active", {
    body: await page.screenshot(),
    contentType: "image/png",
  });

  await expect(progress.getByText("Current:").locator("..")).toContainText("Ownership & UBO — In progress");
  await expect.poll(() => caseReadCount).toBeGreaterThanOrEqual(2);
  showObservedProgress = false;
  await confirmMockTarget(page);
  await openStage(page, "GoldTier submission package");
  await expect(page.getByText("Completed POC workflow")).toBeVisible({ timeout: 120_000 });
  await testInfo.attach("progress-completed-endpoint", {
    body: await page.screenshot(),
    contentType: "image/png",
  });
});

test("Director explicitly selects either team and journey or actor reset clears the choice", async ({ page }) => {
  await page.goto("/");
  await login(page, "olivia-koh");
  await openFreshOnboarding(page);

  const team = page.getByLabel("Owning team *", { exact: true });
  const create = page.getByRole("button", { name: "Create onboarding" });
  await expect(team).toHaveValue("");
  await expect(create).toBeDisabled();
  await expect(team.locator("option:checked")).toHaveText("Select a team");

  await team.selectOption("TEAM_A");
  await page.getByLabel("Jurisdiction").selectOption("SG");
  await page.getByLabel("Company Legal Name").fill(legalNameForUen("202400001A"));
  await page.getByLabel("Registration ID / UEN").fill("202400001A");
  await page.locator("#home-document").setInputFiles(cleanFixture);
  const alphaResponse = page.waitForResponse((response) => (
    response.request().method() === "POST"
      && new URL(response.url()).pathname === "/api/clm/zero-touch/cases"
  ));
  await create.click();
  expect((await alphaResponse).request().postDataJSON()).toMatchObject({ team_id: "TEAM_A" });
  await expect(page).toHaveURL(/\/new-onboarding\/[0-9a-f-]{36}$/i);
  await expect(page.getByRole("button", { name: "Delete case" })).toBeVisible();

  await page.getByRole("button", { name: "Start a new case" }).click();
  await expect(page).toHaveURL("/new-onboarding");
  await expect(team).toHaveValue("");
  await expect(create).toBeDisabled();

  await team.selectOption("TEAM_B");
  await page.getByLabel("Jurisdiction").selectOption("SG");
  await page.getByLabel("Company Legal Name").fill(legalNameForUen("202400001A"));
  await page.getByLabel("Registration ID / UEN").fill("202400001A");
  await page.locator("#home-document").setInputFiles(cleanFixture);
  const betaResponse = page.waitForResponse((response) => (
    response.request().method() === "POST"
      && new URL(response.url()).pathname === "/api/clm/zero-touch/cases"
  ));
  await create.click();
  expect((await betaResponse).request().postDataJSON()).toMatchObject({ team_id: "TEAM_B" });
  await expect(page).toHaveURL(/\/new-onboarding\/[0-9a-f-]{36}$/i);

  const deleteResponse = page.waitForResponse((response) => (
    response.request().method() === "DELETE"
      && /^\/api\/clm\/zero-touch\/cases\/[0-9a-f-]{36}$/i.test(new URL(response.url()).pathname)
  ));
  await page.getByRole("button", { name: "Delete case" }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Delete case" }).click();
  expect((await deleteResponse).status()).toBe(204);
  await expect(page).toHaveURL("/new-onboarding");
  await expect(team).toHaveValue("");
  await expect(create).toBeDisabled();

  await team.selectOption("TEAM_A");
  await page.locator(".operator-account__button").click();
  await page.getByRole("button", { name: "Sign out" }).click();
  await login(page, "maya-lim");
  await page.locator(".operator-account__button").click();
  await page.getByRole("button", { name: "Sign out" }).click();
  await login(page, "olivia-koh");
  await openFreshOnboarding(page);
  await expect(page.getByLabel("Owning team *", { exact: true })).toHaveValue("");
  await expect(page.getByRole("button", { name: "Create onboarding" })).toBeDisabled();
});

test("problem pipeline stages focus authorized inputs and explain unavailable correction", async ({ page }) => {
  await page.goto("/");
  await login(page);
  await openFreshOnboarding(page);
  await page.getByLabel("Jurisdiction").selectOption("SG");
  await page.getByLabel("Company Legal Name").fill(legalNameForUen("202400001A"));
  await page.getByLabel("Registration ID / UEN").fill("202400001A");
  await page.locator("#home-document").setInputFiles(cleanFixture);
  await page.getByRole("button", { name: "Create onboarding" }).click();
  await expect(page).toHaveURL(/\/new-onboarding\/[0-9a-f-]{36}$/i);
  const caseId = /\/new-onboarding\/([0-9a-f-]{36})$/i.exec(page.url())?.[1];
  expect(caseId).toBeTruthy();
  await page.emulateMedia({ reducedMotion: "reduce" });
  let interceptedDetailReads = 0;
  await page.route("**/api/clm/zero-touch/cases/*", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (route.request().method() !== "GET" || !/^\/api\/clm\/zero-touch\/cases\/[0-9a-f-]{36}$/i.test(pathname)) {
      await route.fallback();
      return;
    }
    interceptedDetailReads += 1;
    const response = await route.fetch();
    const body = await response.json();
    body.processing_pipeline = body.processing_pipeline.map((node: Record<string, unknown>) => {
      if (node.node_id === "GOLDTIER_SEARCH") return { ...node, status: "FAILED", blocker_code: "SEARCH_TIMEOUT", safe_result: "Customer existence remains unresolved." };
      if (node.node_id === "TARGET_CLASSIFICATION") return { ...node, status: "REVIEW_REQUIRED" };
      if (node.node_id === "GOLDTIER_TARGET") return { ...node, status: "BLOCKED", blocker_code: "GOLDTIER_SEARCH_FAILED" };
      if (node.node_id === "FINAL_REVIEW_SEND") return { ...node, status: "NOT_REACHED", blocker_code: null, safe_result: "Final review awaits authoritative readiness" };
      return node;
    });
    if (!body.processing_pipeline.some((node: Record<string, unknown>) => node.node_id === "TARGET_CLASSIFICATION")) {
      body.processing_pipeline.splice(-2, 0, {
        node_id: "TARGET_CLASSIFICATION",
        label: "Target classification",
        status: "REVIEW_REQUIRED",
        blocker_code: "GOLDTIER_CLASSIFICATION_REQUIRED",
        children: [],
      });
    }
    body.target_classification = {
      vocabulary_version: "goldtier-openapi-1.0.0",
      editable: false,
      kyc_customer_type: {
        allowed_values: ["Company - Private"],
        selected_value: "Company - Private",
        authority: "USER_AUTHORIZED_POC",
        required: true,
      },
      client_segment: {
        allowed_values: ["Corporate"],
        selected_value: "Corporate",
        authority: "USER_AUTHORIZED_POC",
        required: true,
      },
    };
    await route.fulfill({ response, json: body });
  });
  await page.goto(`/cases/${caseId}?focus=GOLDTIER_SEARCH`);
  await expect.poll(() => interceptedDetailReads).toBeGreaterThan(0);
  const progress = page.getByRole("region", { name: "Onboarding progress" });
  await expect(progress).toContainText("Existing-customer search");
  await expect(progress).toContainText("Failed");

  await expect(page).toHaveURL(/\/cases\/[0-9a-f-]{36}\?focus=GOLDTIER_SEARCH$/i);
  await expect(page.getByRole("button", { name: "Back to Cases" })).toBeVisible();
  await expect(page.locator("#identity-registration-number")).toBeFocused();
  await expect(page.locator("#case-search-diagnostic")).toContainText("does not prove that the customer is absent");

  await expect(page.getByRole("button", { name: "Open details for Registry verification" })).toHaveCount(1);
  const classificationStage = page.getByRole("button", { name: "Open details for Target classification" });
  await classificationStage.focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("#case-target-classification")).toBeFocused();
  await expect(page.getByText("No corrective input is currently authorized here. Review the retained reason and required evidence.", { exact: true })).toBeVisible();

  const targetStage = page.getByRole("button", { name: "Open details for GoldTier submission package" });
  await targetStage.focus();
  await page.keyboard.press("Space");
  await expect(page.locator("#case-target-blocker")).toBeFocused();

  const approvalStage = page.getByRole("button", { name: "Open details for Final review & send" });
  await approvalStage.focus();
  await page.keyboard.press("Enter");
  await expect(approvalStage).toBeFocused();
  await expect(page.getByRole("region", { name: "Final review & send details", exact: true }))
    .toContainText("Final review awaits authoritative readiness");
  await expect(page.locator("#case-review-and-send")).toHaveCount(0);
  await expect(page.getByRole("button", { name: /^Confirm and send to/ })).toHaveCount(0);
});

test("Garden partial registry evidence is presented as incomplete, not unavailable", async ({ page }, testInfo) => {
  let retainedPartialSummary: Record<string, any> | null = null;

  await page.route("**/api/clm/zero-touch/cases/*/intake/complete", async (route) => {
    if (route.request().method() !== "POST" || retainedPartialSummary === null) {
      await route.fallback();
      return;
    }
    const caseId = retainedPartialSummary.case.case_id as string;
    if (!new URL(route.request().url()).pathname.includes(`/cases/${caseId}/`)) {
      await route.fallback();
      return;
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(retainedPartialSummary) });
  });

  await page.route("**/api/clm/zero-touch/cases", async (route) => {
    if (route.request().method() !== "POST") {
      await route.fallback();
      return;
    }
    const requestBody = route.request().postDataJSON() as { uen?: string };
    if (requestBody.uen !== "11111999A") {
      await route.fallback();
      return;
    }
    const response = await route.fetch();
    const payload = await response.json() as Record<string, any>;
    const caseId = payload.case.case_id as string;
    payload.status = "WAITING_FOR_REVIEW";
    payload.current_stage = "REGISTRY";
    payload.case.registry_acquisition.status = "PARTIAL";
    payload.case.registry_acquisition.ownership_parties = [];
    payload.case.registry_acquisition.relationships = [];
    payload.case.registry_acquisition.operation_results = payload.case.registry_acquisition.operation_results.map(
      (operation: Record<string, unknown>) => operation.operation === "OWNERSHIP_PARTIES"
        ? { ...operation, status: "EMPTY", record_count: 0 }
        : operation,
    );
    payload.case.registry_acquisition.issues = [{
      code: "REGISTRY_EXPECTED_DATA_MISSING",
      message: "Expected registry ownership evidence was not returned.",
    }];
    payload.active_exceptions = [{
      exception_id: "00000000-0000-4000-8000-000000000090",
      case_id: caseId,
      exception_type: "REGISTRY_REVIEW_REQUIRED",
      stage: "REGISTRY",
      status: "OPEN",
      blocker_code: "REGISTRY_EXPECTED_DATA_MISSING",
      blocker_codes: ["REGISTRY_EXPECTED_DATA_MISSING"],
      explanation: "Expected registry ownership evidence was not returned.",
      evidence_version: "registry:1",
      automation_version: payload.version,
      evidence: [],
      available_actions: [],
      created_at: payload.updated_at,
      resolved_at: null,
      resolution: null,
    }];
    payload.processing_pipeline = payload.processing_pipeline.map((node: Record<string, unknown>) => (
      node.node_id === "ACRA_REGISTRY"
        ? { ...node, status: "REVIEW_REQUIRED", blocker_code: "REGISTRY_EXPECTED_DATA_MISSING" }
        : node
    ));
    retainedPartialSummary = payload;
    await route.fulfill({ response, json: payload });
  });

  await page.goto("/");
  await login(page);
  await openFreshOnboarding(page);
  await page.getByLabel("Jurisdiction").selectOption("SG");
  await page.getByLabel("Company Legal Name").fill("GARDEN BUSINESS");
  await page.getByLabel("Registration ID / UEN").fill("11111999A");
  await page.locator("#home-document").setInputFiles(cleanFixture);
  await page.getByRole("button", { name: "Create onboarding" }).click();

  await expect(page.getByRole("heading", { name: "Registry data incomplete" })).toBeVisible();
  await expect(page.getByText("Successful / data retrieved", { exact: true })).toBeVisible();
  await expect(page.getByText("Ownership evidence incomplete", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Registry unavailable" })).toHaveCount(0);
  await testInfo.attach("garden-partial-registry-state", {
    body: await page.screenshot(),
    contentType: "image/png",
  });
});

test("Singapore clean fixture completes the truthful Mock target path", async ({ page }) => {
  await page.goto("/");
  await login(page);
  const newOnboardingLink = page.getByRole("link", { name: "New onboarding" });
  await expect(newOnboardingLink).toHaveAttribute("href", "/new-onboarding");
  await newOnboardingLink.click();

  await page.getByLabel("Jurisdiction").selectOption("SG");
  await page.getByLabel("Company Legal Name").fill(legalNameForUen("202400001A"));
  await page.getByLabel("Registration ID / UEN").fill("202400001A");
  await page.locator("#home-document").setInputFiles(cleanFixture);
  await page.getByRole("button", { name: "Create onboarding" }).click();

  await expect(page).toHaveURL(/\/new-onboarding\/([0-9a-f-]{36})$/i);
  const caseId = page.url().split("/").at(-1)!;
  await confirmMockTarget(page);
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
  const ownershipRecord = await ownershipResponse.json() as OwnershipAnalysisRecord;
  expect(ownershipRecord.candidates.length).toBeGreaterThan(0);
  const expectedCandidate = ownershipRecord.candidates[0];
  expect(expectedCandidate.paths.length).toBeGreaterThan(0);
  await openStage(page, "GoldTier submission package");
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
  await openStage(page, "Registry verification");
  await expect(page.getByRole("heading", { name: "Registry provenance" })).toBeVisible();
  const bindingResponse = await page.request.get(`/api/clm/zero-touch/cases/${caseId}`);
  expect(bindingResponse.status()).toBe(200);
  const binding = (await bindingResponse.json() as {
    case: { registry_evidence_binding: RegistryEvidenceBinding | null };
  }).case.registry_evidence_binding;
  expect(binding).not.toBeNull();
  expect(binding?.disposition).toBe("PROVIDER_FETCH");
  expect(binding?.freshness_comparator).toBe("EVALUATION_NOW_LT_EXPIRES_AT");
  await openStageSupport(page, "Registry verification", "Technical");
  const bindingView = page.getByLabel("Case evidence binding", { exact: true });
  await expect(bindingView).toBeVisible();
  expect(binding?.synthetic_seed_namespace).toBeNull();
  await expect(bindingView.getByRole("note")).toHaveCount(0);
  const visibleBindingFields = [
    "disposition",
    "freshness_policy_id",
    "freshness_policy_version",
    "freshness_duration_seconds",
    "freshness_comparator",
  ] as const;
  for (const field of visibleBindingFields) {
    await expect(bindingView).toContainText(String(binding![field]));
  }
  await assertRegistryBindingTimestamps(page, binding!);
  await expect(bindingView).toContainText(
    "This is not a current validity assessment or an ACRA validity guarantee.",
  );
  await expect(page.getByText("Case evidence binding not recorded.")).toHaveCount(0);
  await openStage(page, "Ownership & UBO");
  await expect(page.getByRole("heading", { name: "Ownership path explorer" })).toBeVisible();
  await page.getByText("Backend execution details", { exact: true }).click();
  await expect(page.getByRole("heading", { name: "Why this case is in its current state" })).toBeVisible();

  const interactionRequestBaseline = caseRequests.length;
  const storageBefore = await page.evaluate(() => JSON.stringify({
    local: { ...localStorage },
    session: { ...sessionStorage },
  }));
  const ownershipStructure = page.getByRole("region", { name: "Ownership & UBO", exact: true }).locator(":scope > details").filter({ has: page.getByText("Technical details — Ownership & UBO", { exact: true }) });
  await expect(ownershipStructure).not.toHaveAttribute("open", "");
  const calculations = ownershipStructure.getByText("Technical details — Ownership & UBO", { exact: true }); await expect(calculations).toBeVisible(); await calculations.click();
  await expect(page.locator('[aria-label="Ownership candidates"]')).toHaveCount(0);
  const hierarchy = page.getByRole("table", { name: "Ownership hierarchy", exact: true });
  const candidate = hierarchy.getByRole("button", { name: expectedCandidate.party.display_name, exact: true });
  await expect(candidate).toHaveCount(1);
  await expect(candidate).toBeVisible();
  await candidate.click();
  await expect(candidate).toHaveAttribute("aria-pressed", "true");
  const selectedHolder = page.getByRole("complementary", { name: "Selected holder", exact: true });
  await expect(selectedHolder.getByRole("heading", { name: expectedCandidate.party.display_name, exact: true })).toBeVisible();
  await expect(selectedHolder).toContainText(expectedCandidate.classification);
  await expect(selectedHolder).toContainText(expectedCandidate.threshold_result);
  const retainedPath = page.getByRole("button", { name: `Inspect ${expectedCandidate.paths[0].path_id}`, exact: true });
  await expect(retainedPath).toBeVisible();
  await retainedPath.click();
  await expect(retainedPath).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByLabel(`Selected retained path ${expectedCandidate.paths[0].path_id}`, { exact: true })).toBeVisible();
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
  await prepareSingleValueReviewPolicy(page);
  await page.goto("/");
  await login(page);
  await page.getByRole("link", { name: "New onboarding" }).click();
  await page.getByLabel("Jurisdiction").selectOption("SG");
  await page.getByLabel("Company Legal Name").fill(legalNameForUen("202400001A"));
  await page.getByLabel("Registration ID / UEN").fill("202400001A");
  await page.locator("#home-document").setInputFiles(singleValueReviewFixture);
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
    fields: Array<{ field_key: string; review_status: string; comparison_status: string; confidence: number; original_extracted_value: string | null }>;
  }>).find((document) => document.superseded_by_document_id === null);
  expect(currentDocument).toBeDefined();
  expect(currentDocument?.state).toBe("REVIEW_REQUIRED");
  expect(currentDocument?.fields.map((field) => [field.field_key, field.review_status])).toEqual([
    ["registration_number", "ACCEPTED"],
    ["legal_name", "PENDING"],
    ["registered_address", "ACCEPTED"],
    ["country_of_incorporation", "ACCEPTED"],
  ]);
  const pendingField = currentDocument?.fields.find((field) => field.field_key === "legal_name");
  expect(pendingField?.comparison_status).toBe("MATCH");
  expect(pendingField?.confidence).toBe(0.9);
  expect(currentDocument?.fields.every((field) => field.original_extracted_value !== null)).toBe(true);
  await expect(page.getByRole("heading", { name: "Document evidence and review" })).toBeVisible();
  await expect(page.locator("select[data-review-field]").first()).toBeVisible();
});

test("current document review progresses authoritatively and keeps superseded history read-only", async ({ page }) => {
  const reviewRequests: string[] = [];
  const resumeRequests: string[] = [];
  page.on("request", (request) => {
    if (request.method() === "POST" && request.url().endsWith("/review-decisions")) reviewRequests.push(request.postData() ?? "");
    if (request.method() === "POST" && request.url().endsWith("/resume")) resumeRequests.push(request.url());
  });

  await page.goto("/");
  await login(page);
  await page.getByRole("link", { name: "New onboarding" }).click();
  await page.getByLabel("Jurisdiction").selectOption("SG");
  await page.getByLabel("Company Legal Name").fill(legalNameForUen("202400001A"));
  await page.getByLabel("Registration ID / UEN").fill("202400001A");
  await page.locator("#home-document").setInputFiles(mismatchFixture);
  // A stored document is visible before its upload response and intake handoff settle.
  const initialUploadResponse = page.waitForResponse((response) =>
    response.request().method() === "POST" && new URL(response.url()).pathname.endsWith("/intake/documents"));
  const initialIntakeResponse = page.waitForResponse((response) =>
    response.request().method() === "POST" && new URL(response.url()).pathname.endsWith("/intake/complete"));
  await page.getByRole("button", { name: "Create onboarding" }).click();
  await expect(page).toHaveURL(/\/new-onboarding\/([0-9a-f-]{36})$/i);
  const caseId = page.url().split("/").at(-1)!;
  expect((await initialUploadResponse).status()).toBe(201);
  const initialIntake = await initialIntakeResponse;
  expect(initialIntake.status()).toBe(200);
  expect((await initialIntake.json() as { status: string }).status).toBe("WAITING_FOR_REVIEW");
  await expect.poll(async () => {
    const response = await page.request.get(`/api/onboarding/cases/${caseId}/documents`);
    if (!response.ok()) return 0;
    return (await response.json() as unknown[]).length;
  }, { timeout: 120_000 }).toBe(1);

  await page.goto(`/cases/${caseId}`);
  await openStage(page, "Document verification");
  await expect(page.getByRole("heading", { name: "Document evidence and review" })).toBeVisible({ timeout: 30_000 });
  const focusRequestBaseline = reviewRequests.length + resumeRequests.length;
  await openStage(page, "GoldTier submission package");
  await page.getByText("Backend execution details", { exact: true }).click();
  await page.getByRole("button", { name: "Focus documents evidence" }).click();
  await expect(page.locator("#case-blocker-review select[data-review-field], #case-blocker-review select[data-reconciliation-field], #case-evidence-documents input[type=file]").first()).toBeFocused();
  expect(reviewRequests.length + resumeRequests.length).toBe(focusRequestBaseline);
  await expect(page.getByText("3 final / 4 fields")).toBeVisible();
  await expect(page.getByText(/1 field remains for review/)).toBeVisible();
  for (const field of ["registration number", "registered address", "country of incorporation"]) {
    await expect(page.getByRole("button", { name: `Accept ${field} suggestion` })).toHaveCount(0);
  }
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
      fields: Array<{ field_key: string; review_status: string; comparison_status: string; extraction_quality: string }>;
      superseded_by_document_id: string | null;
    }>;
    const current = documents.find((document) => document.superseded_by_document_id === null);
    const reviewedMismatch = current?.fields.find((field) => field.field_key === "legal_name");
    expect(reviewedMismatch?.review_status).toBe("ACCEPTED");
    expect(reviewedMismatch?.comparison_status).toBe("MISMATCH");
    expect(reviewedMismatch?.extraction_quality).toBe("HIGH");
    return current?.fields.filter((item) => item.review_status !== "PENDING").length ?? 0;
  };

  await page.locator('select[data-review-field="legal_name"]').selectOption("ACCEPTED");
  expect(reviewRequests).toHaveLength(0);
  const firstMutationResponse = page.waitForResponse((response) =>
    response.request().method() === "POST" && response.url().endsWith("/review-decisions"));
  const firstDocumentsResponse = page.waitForResponse((response) =>
    response.request().method() === "GET"
      && response.url().endsWith(`/api/onboarding/cases/${caseId}/documents`));
  reviewMilestone("REVIEW_MUTATION_DISPATCHED", 3);
  await page.getByRole("button", { name: "Confirm decisions & continue onboarding", exact: true }).dblclick();
  expect((await firstMutationResponse).status()).toBe(200);
  reviewMilestone("REVIEW_MUTATION_RESPONSE_COMPLETE", 4);
  const firstBackendCount = await reviewedCount(await firstDocumentsResponse);
  expect(firstBackendCount).toBe(4);
  reviewMilestone("REVIEW_DOCUMENTS_GET_COMPLETE", firstBackendCount);
  expect(reviewRequests).toHaveLength(1);
  expect(JSON.parse(reviewRequests[0]).documents[0].decisions).toEqual([{ field_key: "legal_name", decision: "ACCEPTED" }]);
  expect(resumeRequests).toHaveLength(0);
  await openStage(page, "Document verification");
  await expect(page.getByText("4 final / 4 fields")).toBeVisible({ timeout: 30_000 });
  reviewMilestone("REVIEW_RENDERED_COUNT", 4);
  await expect.poll(async () => {
    const response = await page.request.get(`/api/onboarding/cases/${caseId}/documents`);
    if (!response.ok()) return null;
    const documents = await response.json() as Array<{ state: string; superseded_by_document_id: string | null }>;
    return documents.find((document) => document.superseded_by_document_id === null)?.state ?? null;
  }, { timeout: 120_000 }).toBe("REVIEWED");
  await expect(page.locator(".document-card:not(.document-card--history) .document-card__header .tag"))
    .toHaveText("Document processed", { timeout: 30_000 });
  expect(reviewRequests).toHaveLength(1);
  expect(resumeRequests).toHaveLength(0);

  const replacementInput = page.getByLabel("Replace current document");
  await expect(replacementInput).toBeEnabled();
  await replacementInput.focus();
  await expect(replacementInput).toBeFocused();
  const replacementResponse = page.waitForResponse((response) =>
    response.request().method() === "POST"
      && new URL(response.url()).pathname.startsWith(`/api/clm/zero-touch/cases/${caseId}/documents/`)
      && new URL(response.url()).pathname.endsWith("/replacement"));
  await replacementInput.setInputFiles(cleanFixture);
  expect((await replacementResponse).status()).toBe(200);
  await confirmMockTarget(page);
  await openStage(page, "GoldTier submission package");
  await expect(page.getByText("Completed POC workflow")).toBeVisible({ timeout: 120_000 });
  await expect.poll(async () => {
    const response = await page.request.get(`/api/onboarding/cases/${caseId}/documents`);
    if (!response.ok()) return false;
    const documents = await response.json() as Array<{ superseded_by_document_id: string | null }>;
    return documents.length === 2
      && documents.filter((document) => document.superseded_by_document_id === null).length === 1
      && documents.filter((document) => document.superseded_by_document_id !== null).length === 1;
  }, { timeout: 120_000 }).toBe(true);
  await openStage(page, "Document verification");
  await openStageSupport(page, "Document verification", "More");
  const history = page.getByText(/Evidence history \(1\)/);
  await expect(history).toBeVisible();
  const historicalCard = page.locator(".document-card--history");
  await expect(historicalCard).toBeVisible();
  await expect(historicalCard.getByRole("button")).toHaveCount(0);
  await expect(historicalCard.locator("input[type=file]")).toHaveCount(0);

  await page.reload();
  await expect(page).toHaveURL(`/cases/${caseId}`);
  await openStage(page, "Document verification");
  await expect(page.getByRole("heading", { name: "Document evidence and review" })).toBeVisible({
    timeout: 30_000,
  });
  await openStageSupport(page, "Document verification", "More");
  const reloadedHistory = page.getByText(/Evidence history \(1\)/);
  await expect(reloadedHistory).toBeVisible({ timeout: 30_000 });
  await expect(page.locator(".document-card--history")).toBeVisible();
  await expect(page.getByText(/GoldTier Mock/).first()).toBeVisible();
  await openStage(page, "GoldTier submission package");
  await page.getByText("Backend execution details", { exact: true }).click();
  await expect(page.getByText(/Ready-for-Approval: NOT AVAILABLE/i)).toBeVisible();
  expect(resumeRequests).toHaveLength(0);
});

test("Cases filters exact open business-exception types without hiding other attention states", async ({ page }) => {
  await page.goto("/");
  await login(page);

  async function createPausedCase(uen: string, fixture: string): Promise<string> {
    await openFreshOnboarding(page);
    await page.getByLabel("Jurisdiction").selectOption("SG");
    await page.getByLabel("Company Legal Name").fill(legalNameForUen(uen));
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
  const ambiguitySummaryResponse = await page.request.get(`/api/clm/zero-touch/cases/${lowConfidenceCaseId}`);
  expect(ambiguitySummaryResponse.status()).toBe(200);
  const ambiguitySummary = await ambiguitySummaryResponse.json() as {
    active_exceptions: Array<{ exception_type: string; blocker_code: string }>;
  };
  expect(ambiguitySummary.active_exceptions).toEqual(expect.arrayContaining([
    expect.objectContaining({ exception_type: "DOCUMENT_REVIEW_REQUIRED", blocker_code: "DOCUMENT_AMBIGUOUS_EXTRACTION" }),
  ]));

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
        === "DOCUMENT_REVIEW_REQUIRED"
  ));
  await attentionFilter.selectOption("DOCUMENT_REVIEW_REQUIRED");
  const lowConfidencePage = await lowConfidenceResponse;
  expect(lowConfidencePage.status()).toBe(200);
  expect((await lowConfidencePage.json() as { items: Array<{ case_id: string }> }).items)
    .toEqual(expect.arrayContaining([
      expect.objectContaining({ case_id: lowConfidenceCaseId }),
    ]));
  await expect(page.getByText("202400001A", { exact: true })).toBeVisible();
  await expect(page.getByText("202400006F", { exact: true })).toHaveCount(0);
  await expect(
    page.getByLabel("Cases table").getByText("Document review required", { exact: true }),
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
      path: "/api/clm/zero-touch/case-portfolio?attention_type=DOCUMENT_REVIEW_REQUIRED",
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
  await openStage(page, "GoldTier submission package");
  await page.getByText("Backend execution details", { exact: true }).click();
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
