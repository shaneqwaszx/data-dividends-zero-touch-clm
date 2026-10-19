import { mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test, type Locator, type Page } from "@playwright/test";
import { expectDisclosureContrast, openStage } from "./stage-disclosures";
import {
  retainedEvidencePath,
  createBrowserNetworkPolicy,
  handleBrowserRoute,
  type BrowserNetworkPolicy,
} from "../playwright.config";

const currentDirectory = path.dirname(fileURLToPath(import.meta.url));
const cleanFixture = path.resolve(
  currentDirectory,
  "../../backend/tests/fixtures/uat/clean-company-profile.pdf",
);
const lowConfidenceFixture = path.resolve(
  currentDirectory,
  "../../backend/tests/fixtures/uat/low-confidence.pdf",
);

const VIEWPORTS = [320, 360, 390, 480, 768, 1024, 1280, 1440, 1920] as const;
const REPRESENTATIVE_VIEWPORTS = [360, 768, 1440] as const;
const TILE_VIEWPORTS = [320, 360, 768, 1280, 1440, 1920] as const;

function requiredEnvironment(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`The task-owned E2E launcher must provide ${name}`);
  return value;
}

async function guardLocalNetwork(page: Page, policy: BrowserNetworkPolicy) {
  const violations: string[] = [];
  await page.route("**/*", async (route) => {
    await handleBrowserRoute(route, policy, violations);
  });
  return () => {
    expect(
      violations,
      "Browser network policy blocked request(s); only sanitized structure follows",
    ).toEqual([]);
  };
}

async function login(page: Page, userId = "maya-lim") {
  await page.goto("/");
  await page.getByLabel("User ID").fill(userId);
  await page.getByLabel("Password").fill(requiredEnvironment("CLM_E2E_PASSWORD"));
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("navigation", { name: "Main workspace" })).toBeVisible({
    timeout: 30_000,
  });
}

async function logout(page: Page) {
  await page.locator(".operator-account__button").click();
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
}

async function openWorkspaceTab(page: Page, name: string) {
  await page.getByRole("link", { name, exact: true }).click();
}

async function expectDocumentContained(page: Page) {
  const layout = await page.evaluate(() => {
    const initialScrollX = window.scrollX;
    window.scrollTo({ left: 10_000, top: window.scrollY });
    const rootScrollX = window.scrollX;
    window.scrollTo({ left: initialScrollX, top: window.scrollY });
    return {
      bodyClientWidth: document.body.clientWidth,
      bodyScrollWidth: document.body.scrollWidth,
      pathname: window.location.pathname,
      viewportWidth: document.documentElement.clientWidth,
      rootScrollX,
      visibleOverflow: Array.from(document.querySelectorAll<HTMLElement>("body *"))
        .filter((element) => {
          const box = element.getBoundingClientRect();
          if (box.right <= document.documentElement.clientWidth + 1) return false;
          for (let ancestor = element.parentElement; ancestor; ancestor = ancestor.parentElement) {
            const overflowX = getComputedStyle(ancestor).overflowX;
            if (overflowX === "auto" || overflowX === "scroll" || overflowX === "hidden" || overflowX === "clip") return false;
          }
          return true;
        })
        .slice(0, 12)
        .map((element) => ({ tag: element.tagName, className: element.className, box: element.getBoundingClientRect().toJSON() })),
    };
  });
  expect(layout.bodyScrollWidth).toBeLessThanOrEqual(layout.bodyClientWidth + 1);
  expect(layout.bodyClientWidth).toBeLessThanOrEqual(layout.viewportWidth + 1);
  expect(layout.rootScrollX, JSON.stringify({ pathname: layout.pathname, visibleOverflow: layout.visibleOverflow })).toBeLessThanOrEqual(1);
}

async function expectBoxContained(page: Page, locator: Locator) {
  await expect(locator).toBeVisible();
  const layout = await locator.evaluate((element) => {
    const bounds = element.getBoundingClientRect();
    return {
      left: Math.round(bounds.left),
      right: Math.round(bounds.right),
      width: Math.round(bounds.width),
      viewportWidth: document.documentElement.clientWidth,
    };
  });
  expect(layout.width).toBeGreaterThan(0);
  expect(layout.left).toBeGreaterThanOrEqual(-1);
  expect(layout.right).toBeLessThanOrEqual(layout.viewportWidth + 1);
}

async function expectLocalHorizontalScroller(page: Page, locator: Locator) {
  await expectBoxContained(page, locator);
  const layout = await locator.evaluate((element) => {
    const scroller = element as HTMLElement;
    const initial = scroller.scrollLeft;
    scroller.scrollLeft = scroller.scrollWidth;
    const moved = scroller.scrollLeft;
    scroller.scrollLeft = initial;
    return {
      clientWidth: scroller.clientWidth,
      moved,
      overflowX: getComputedStyle(scroller).overflowX,
      scrollWidth: scroller.scrollWidth,
    };
  });
  expect(layout.overflowX).toBe("auto");
  if (layout.scrollWidth > layout.clientWidth + 1) expect(layout.moved).toBeGreaterThan(0);
}

async function expectCaseTableColumnsAligned(page: Page) {
  const columns = await page.locator("table.case-table").evaluate((table) => {
    const headers = Array.from(table.querySelectorAll<HTMLTableCellElement>("thead th"));
    const cells = Array.from(table.querySelectorAll<HTMLTableCellElement>("tbody tr:first-child td"));
    return headers.map((header, index) => {
      const headerBox = header.getBoundingClientRect();
      const cellBox = cells[index]?.getBoundingClientRect();
      return {
        headerLeft: headerBox.left,
        headerWidth: headerBox.width,
        cellLeft: cellBox?.left,
        cellWidth: cellBox?.width,
      };
    });
  });
  expect(columns).toHaveLength(12);
  for (const column of columns) {
    expect(column.cellLeft).toBeDefined();
    expect(Math.abs(column.headerLeft - column.cellLeft!)).toBeLessThanOrEqual(1);
    expect(Math.abs(column.headerWidth - column.cellWidth!)).toBeLessThanOrEqual(1);
  }
}

async function expectShellContained(page: Page) {
  await expectDocumentContained(page);
  await expectBoxContained(page, page.getByRole("navigation", { name: "Main workspace" }));
  await expectBoxContained(page, page.locator(".nav-brand"));
  await expectBoxContained(page, page.locator(".nav-tabs"));
  await expectBoxContained(page, page.locator(".nav-meta .environment-banner"));
  await expect(page.locator(".nav-meta .environment-banner__label")).toBeVisible();
  await expectBoxContained(page, page.locator(".operator-account__button"));
}

async function expectActionableStageTiles(page: Page) {
  const actionable = page.locator(".onboarding-progress__stage--actionable > button").first();
  await expect(actionable).toBeVisible();

  for (const width of TILE_VIEWPORTS) {
    await page.setViewportSize({ width, height: 900 });
    await expectDocumentContained(page);
    await expectBoxContained(page, page.locator(".onboarding-progress__stages"));
    await expectBoxContained(page, actionable);
    const tile = await actionable.evaluate((button) => {
      const bounds = button.getBoundingClientRect();
      const label = button.querySelector<HTMLElement>(".onboarding-progress__stage-label")!;
      const status = button.querySelector<HTMLElement>(".onboarding-progress__stage-status")!;
      const action = button.querySelector<HTMLElement>(".onboarding-progress__stage-action")!;
      const labelStyle = getComputedStyle(label);
      return {
        actionText: action.textContent,
        height: bounds.height,
        labelOverflowWrap: labelStyle.overflowWrap,
        labelWordBreak: labelStyle.wordBreak,
        statusTop: status.getBoundingClientRect().top,
        titleBottom: label.getBoundingClientRect().bottom,
        actionTop: action.getBoundingClientRect().top,
      };
    });
    expect(tile.height).toBeGreaterThanOrEqual(44);
    expect(tile.labelOverflowWrap).toBe("break-word");
    expect(tile.labelWordBreak).toBe("normal");
    expect(tile.statusTop).toBeGreaterThanOrEqual(tile.titleBottom - 1);
    expect(tile.actionTop).toBeGreaterThanOrEqual(tile.statusTop);
    expect(tile.actionText).toBe("View details");
  }

  await actionable.hover();
  const hover = await actionable.evaluate((button) => {
    const style = getComputedStyle(button);
    return { background: style.backgroundColor, color: style.color };
  });
  expect(hover.background).toBe("rgb(243, 234, 219)");
  expect(hover.color).toBe("rgb(32, 31, 29)");
  await actionable.focus();
  await expect(actionable).toBeFocused();
  expect(await actionable.evaluate((button) => getComputedStyle(button).outlineStyle)).not.toBe("none");
}

async function openNewCase(page: Page, fixture: string): Promise<string> {
  await openWorkspaceTab(page, "New onboarding");
  const startFresh = page.getByRole("button", { name: "Start a new case" });
  if (await startFresh.isVisible()) await startFresh.click();
  await expect(page.getByRole("heading", { name: "Start onboarding" })).toBeVisible();
  await page.getByLabel("Jurisdiction").selectOption("SG");
  await page.getByLabel("Company Legal Name").fill("MERLION CIRCULAR LABS PTE. LTD.");
  await page.getByLabel("Registration ID / UEN").fill("202400001A");
  await page.locator("#home-document").setInputFiles(fixture);
  await page.getByRole("button", { name: "Create onboarding" }).click();
  await expect(page).toHaveURL(/\/new-onboarding\/([0-9a-f-]{36})$/i, {
    timeout: 30_000,
  });
  return page.url().split("/").at(-1)!;
}

async function confirmMockTarget(page: Page) {
  await page.getByRole("button", { name: "Open full case" }).click();
  await expect(page).toHaveURL(/\/cases\/[0-9a-f-]{36}$/i);
  const confirmation = page.getByRole("button", { name: "Confirm and send to Mock GoldTier" });
  await expect(confirmation).toBeEnabled({ timeout: 120_000 });
  const response = page.waitForResponse((result) => (
    result.request().method() === "POST"
      && new URL(result.url()).pathname.endsWith("/target-confirmation")
  ));
  await confirmation.click();
  expect((await response).status()).toBe(200);
}

async function waitForCaseStatus(page: Page, caseId: string, accepted: string[]) {
  await expect.poll(async () => {
    const response = await page.request.get(`/api/clm/zero-touch/cases/${caseId}`);
    if (!response.ok()) return false;
    return accepted.includes((await response.json() as { status: string }).status);
  }, { timeout: 120_000 }).toBe(true);
}

test.describe.configure({ mode: "serial" });

let assertNoNetworkViolations: (() => void) | undefined;

test.beforeEach(async ({ page }) => {
  if (process.env.CLM_E2E_DIAGNOSTICS === "1") {
    page.on("console", (message) => {
      if (message.type() === "info" && message.text().startsWith("E2E_DIAG ")) {
        console.log(message.text());
      }
    });
  }
  assertNoNetworkViolations = await guardLocalNetwork(page, createBrowserNetworkPolicy({
    frontendOrigin: requiredEnvironment("PLAYWRIGHT_BASE_URL"),
    backendOrigin: requiredEnvironment("CLM_E2E_BACKEND_ORIGIN"),
    allowDirectBackend: false,
  }));
});

test.afterEach(() => {
  assertNoNetworkViolations?.();
  assertNoNetworkViolations = undefined;
});

async function expectPolicyMutationControls(page: Page, visible: boolean) {
  const draft = page.getByRole("heading", { name: "Prepare policy proposal" });
  const edit = page.getByRole("button", { name: "Propose change", exact: true });
  const reset = page.getByRole("button", { name: "Reset to default", exact: true });
  await expect(page.getByText("Add display-only rule", { exact: true })).toHaveCount(0);
  if (visible) {
    await expect(draft).toBeVisible(); await expect(edit.first()).toBeVisible(); await expect(reset.first()).toBeVisible(); return;
  }
  await expect(draft).toHaveCount(0); await expect(edit).toHaveCount(0); await expect(reset).toHaveCount(0);
}

async function expectAuthoritativeReviewReady(page: Page, caseId: string) {
  const reviewDocumentsResponse = page.waitForResponse((response) => (
    response.request().method() === "GET"
      && new URL(response.url()).pathname === `/api/onboarding/cases/${caseId}/documents`
  ));
  await page.goto(`/cases/${caseId}`);
  const authoritativeDocuments = await reviewDocumentsResponse;
  expect(authoritativeDocuments.status()).toBe(200);
  const currentDocument = (await authoritativeDocuments.json() as Array<{
    state: string;
    superseded_by_document_id: string | null;
    fields: Array<{ review_status: string; original_extracted_value: string | null; extraction_quality: string; candidates: unknown[] }>;
  }>).find((document) => document.superseded_by_document_id === null);
  expect(currentDocument).toBeDefined();
  expect(currentDocument?.state).toBe("REVIEW_REQUIRED");
  expect(currentDocument?.fields.some((field) => (
    field.review_status === "PENDING" && field.original_extracted_value === null
      && field.extraction_quality === "AMBIGUOUS" && field.candidates.length === 2
  ))).toBe(true);
  await expect(page.getByRole("heading", { name: "Document evidence and review" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Accept legal name suggestion" })).toHaveCount(0);
  await expect(page.locator('input[data-review-field="legal_name"][value="REJECTED"]')).toBeVisible();
  await expect(page.getByRole("button", { name: "Assign reviewer" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Return for rework" })).toHaveCount(0);
  await expectDocumentContained(page);
}

test("responsive shell contains anonymous auth, navigation, forms, hover, and focus", async ({ page }) => {
  test.setTimeout(240_000);
  await page.setViewportSize({ width: 360, height: 900 });
  await page.goto("/");
  await expectBoxContained(page, page.locator(".auth-card"));
  await expectDocumentContained(page);
  await login(page);

  for (const width of VIEWPORTS) {
    await page.setViewportSize({ width, height: 900 });
    await openWorkspaceTab(page, "Dashboard");
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    await expectShellContained(page);

    await openWorkspaceTab(page, "New onboarding");
    await expect(page.getByRole("heading", { name: "Start onboarding" })).toBeVisible();
    await expectShellContained(page);
    await expectBoxContained(page, page.locator("form .ds-two-col"));
    await expectBoxContained(page, page.getByRole("button", { name: "Create onboarding" }));
  }

  await page.setViewportSize({ width: 1024, height: 900 });
  await openWorkspaceTab(page, "Dashboard");
  const account = page.locator(".operator-account__button");
  await account.hover();
  const hoverStyle = await account.evaluate((element) => {
    const style = getComputedStyle(element);
    return { background: style.backgroundColor, color: style.color };
  });
  expect(hoverStyle.background).not.toBe("rgb(14, 61, 44)");
  expect(hoverStyle.background).toMatch(/^rgb\((?:2[3-5]\d), (?:2[3-5]\d), (?:2[3-5]\d)\)$/);
  expect(hoverStyle.color).toBe("rgb(32, 31, 29)");
  await page.getByRole("link", { name: "Policy", exact: true }).focus();
  await page.keyboard.press("Tab");
  await expect(account).toBeFocused();
  expect(await account.evaluate((element) => getComputedStyle(element).outlineStyle)).not.toBe("none");
  await logout(page);
});

test("responsive cases and representative routes preserve tables, priorities, and policy visibility", async ({ page }) => {
  test.setTimeout(240_000);
  await page.setViewportSize({ width: 1024, height: 900 });
  await login(page);
  const completedCaseId = await openNewCase(page, cleanFixture);
  await confirmMockTarget(page);
  await waitForCaseStatus(page, completedCaseId, ["COMPLETED"]);

  for (const width of REPRESENTATIVE_VIEWPORTS) {
    await page.setViewportSize({ width, height: 900 });
    const representativeRoutes = [
      ["Dashboard", "/dashboard", "Dashboard"],
      ["New onboarding", "/new-onboarding", ""],
      ["Cases", "/cases", "Cases"],
      [`/cases/${completedCaseId}`, `/cases/${completedCaseId}`, "Document evidence and review"],
      ["Onboarded", "/onboarded", "Onboarded"],
      [`/onboarded/${completedCaseId}`, `/onboarded/${completedCaseId}`, ""],
      ["Audit", "/audit", "Case activity"],
      ["Policy", "/policy", "Policy and rules"],
    ] as const;
    for (const [target, route, heading] of representativeRoutes) {
      await test.step(`${width}px ${route}`, async () => {
        if (target.startsWith("/")) {
          if (target.startsWith("/cases/") && await page.locator(`a[href="${target}"]`).count() === 0) {
            await page.getByLabel("Search cases").fill(target.split("/").at(-1)!);
            await expect(page.locator(`a[href="${target}"]`).first()).toBeVisible();
          }
          await page.locator(`a[href="${target}"]`).first().click();
        } else {
          await openWorkspaceTab(page, target);
        }
        const expectedRoute = route === "/new-onboarding"
          ? /\/new-onboarding(?:\/[0-9a-f-]{36})?(?:$|\?)/i
          : new RegExp(`${route.replaceAll("/", "\\/")}(?:$|\\?)`);
        await expect(page).toHaveURL(expectedRoute);
        if (route === `/cases/${completedCaseId}`) {
          await openStage(page, "Document verification");
        }
        if (heading) await expect(page.getByRole("heading", { name: heading })).toBeVisible();
        await expectShellContained(page);
        if (route === "/cases" || route === "/onboarded" || route === "/audit" || route === "/policy") {
          const scroller = page.locator(".table-scroll").first();
          if (await scroller.isVisible()) await expectLocalHorizontalScroller(page, scroller);
        }
        if (route === "/cases" && width >= 768) {
          await expectCaseTableColumnsAligned(page);
          const options = await page.locator(".priority-select").first().locator("option").allTextContents();
          expect(options).toEqual(["Unset", "Low", "Medium", "High"]);
        }
        if (route === "/policy") {
          await expectPolicyMutationControls(page, false);
        }
      });
    }
  }
});

test("starting a fresh onboarding after a retained case binds the new case route", async ({ page }) => {
  test.setTimeout(240_000);
  await page.setViewportSize({ width: 1024, height: 900 });
  await login(page);
  const firstCaseId = await openNewCase(page, cleanFixture);

  await openWorkspaceTab(page, "New onboarding");
  const startFresh = page.getByRole("button", { name: "Start a new case" });
  await expect(startFresh).toBeVisible();
  const [buttonBox, sidebarBox] = await Promise.all([
    startFresh.boundingBox(),
    page.locator(".side-panel").boundingBox(),
  ]);
  expect(buttonBox).not.toBeNull();
  expect(sidebarBox).not.toBeNull();
  expect(buttonBox!.height).toBeGreaterThanOrEqual(44);
  expect(buttonBox!.width).toBeGreaterThanOrEqual(sidebarBox!.width - 56);
  await startFresh.focus();
  await expect(startFresh).toBeFocused();
  expect(await startFresh.evaluate((element) => getComputedStyle(element).outlineStyle))
    .not.toBe("none");
  await startFresh.click();
  await expect(page).toHaveURL(/\/new-onboarding$/);

  await page.getByLabel("Jurisdiction").selectOption("SG");
  await page.getByLabel("Company Legal Name").fill("MERLION CIRCULAR LABS PTE. LTD.");
  await page.getByLabel("Registration ID / UEN").fill("202400001A");
  await page.locator("#home-document").setInputFiles(cleanFixture);
  await page.getByRole("button", { name: "Create onboarding" }).click();
  await expect(page).toHaveURL(/\/new-onboarding\/([0-9a-f-]{36})$/i, {
    timeout: 30_000,
  });
  const secondCaseId = page.url().split("/").at(-1)!;
  expect(secondCaseId).not.toBe(firstCaseId);
});

test("responsive review case exposes only supported authoritative review controls", async ({ page }) => {
  test.setTimeout(240_000);
  await page.setViewportSize({ width: 360, height: 900 });
  await login(page);
  // Existing no-text UAT asset: retain the real local extraction failure and retry owner.
  const noTextId = await openNewCase(page, path.resolve(currentDirectory, "../../backend/tests/fixtures/uat/no-text.pdf"));
  await expect.poll(async () => {
    const result = await page.request.get(`/api/onboarding/cases/${noTextId}/documents`);
    const state = result.ok() ? (await result.json())[0]?.state : null;
    return ["FAILED", "REVIEW_REQUIRED"].includes(state);
  }).toBe(true);
  const noTextResponse = await page.request.get(`/api/onboarding/cases/${noTextId}/documents`);
  expect(noTextResponse.status()).toBe(200);
  const noTextDocument = (await noTextResponse.json())[0];
  if (noTextDocument.state === "REVIEW_REQUIRED") await waitForCaseStatus(page, noTextId, ["WAITING_FOR_REVIEW"]);
  await page.goto(`/cases/${noTextId}`);
  const unavailable = page.getByRole("region", { name: "Document verification", exact: true });
  await expect(unavailable.locator(":scope > details[open]")).toHaveCount(0);
  if (noTextDocument.state === "FAILED") {
    expect(noTextDocument.error.code).toBe("OCR_RUNTIME_UNAVAILABLE");
    await expect(unavailable.locator(".document-card")).toContainText("OCR_RUNTIME_UNAVAILABLE");
    await expect(unavailable.getByLabel("Retry affected document", { exact: true })).toBeEnabled();
    await expect(unavailable.locator("#case-blocker-review")).toHaveCount(0);
  } else {
    expect(noTextDocument.state).toBe("REVIEW_REQUIRED");
    expect(noTextDocument.fields).toHaveLength(4);
    expect(noTextDocument.fields.every((field: any) => field.original_extracted_value === null && field.confidence === 0
      && field.extraction_quality === "UNAVAILABLE" && field.provenance.source_reference === "DOCUMENT_TEXT_UNAVAILABLE")).toBe(true);
    await expect(unavailable.locator(".document-card")).toContainText("Missing extracted evidence");
    await expect(unavailable.locator(".document-card")).toContainText("Extraction quality: UNAVAILABLE");
    await expect(unavailable.getByLabel("Replace current document", { exact: true })).toBeEnabled();
    expect(await unavailable.locator('input[data-review-field][value="ACCEPTED"]:not([disabled])').count()).toBe(0);
  }
  const reviewCaseId = await openNewCase(page, lowConfidenceFixture);
  await waitForCaseStatus(page, reviewCaseId, ["WAITING_FOR_REVIEW"]);
  const reviewSummaryResponse = await page.request.get(`/api/clm/zero-touch/cases/${reviewCaseId}`);
  expect(reviewSummaryResponse.ok()).toBe(true);
  const reviewSummary = await reviewSummaryResponse.json() as {
    active_exceptions: Array<{ blocker_code: string }>;
    interventions: Array<{ blocker_code: string; required_evidence_or_input: string[]; expected_next_step: string; resolution_condition?: string | null }>;
  };
  expect(
    reviewSummary.interventions.length,
    JSON.stringify({
      exception_codes: reviewSummary.active_exceptions.map((item) => item.blocker_code),
      intervention_codes: reviewSummary.interventions.map((item) => item.blocker_code),
    }),
  ).toBeGreaterThan(0);
  await page.reload();
  await expectAuthoritativeReviewReady(page, reviewCaseId);
  await expectActionableStageTiles(page);
  await expect(page.getByRole("heading", { name: "Action required" })).toBeVisible();
  await expect(page.getByText("No action available", { exact: true })).toHaveCount(0);
  const evidenceAction = page.getByRole("button", { name: "Review document evidence", exact: true });
  await expect(evidenceAction).toBeVisible();
  const mutations: string[] = [];
  page.on("request", (request) => {
    if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method())) mutations.push(request.method());
  });
  // Actual backend-authored intervention essentials stay visible with diagnostics closed.
  const diagnostics = page.locator(".intervention-card > details.evidence-details");
  for (const width of [1440, 1280, 900, 360]) {
    await page.setViewportSize({ width, height: 900 });
    for (const item of reviewSummary.interventions) {
      for (const value of [item.required_evidence_or_input.join(" "), item.expected_next_step, item.resolution_condition].filter(Boolean)) {
        const field = page.locator(".intervention-card__details dd").filter({ hasText: value! }).first();
        await expect(field).toBeVisible();
      }
    }
    await expect(diagnostics.first()).not.toHaveAttribute("open", "");
    const diagnosticToggle = diagnostics.first().locator(":scope > summary");
    await diagnosticToggle.focus(); await diagnosticToggle.press("Enter");
    await expect(diagnostics.first()).toHaveAttribute("open", "");
    await diagnosticToggle.press("Space");
    await expect(diagnostics.first()).not.toHaveAttribute("open", "");
    await expectDocumentContained(page);
  }
  expect(mutations).toEqual([]);
  await evidenceAction.click();
  await expect(page.locator("input[data-review-field]:checked").first()).toBeFocused();
  expect(mutations).toEqual([]);
  await expect(page.getByRole("button", { name: /replay|retry target/i })).toHaveCount(0);
});

test("responsive Relationship Manager policy view and delete dialog", async ({ page }) => {
  test.setTimeout(240_000);
  await page.setViewportSize({ width: 360, height: 900 });
  await login(page, "ethan-tan");
  await openWorkspaceTab(page, "Policy");
  await expectPolicyMutationControls(page, false);
  const completedCaseId = await openNewCase(page, cleanFixture);
  await confirmMockTarget(page);
  await waitForCaseStatus(page, completedCaseId, ["COMPLETED"]);
  await page.goto(`/cases/${completedCaseId}`);
  const deleteButton = page.getByRole("button", { name: "Delete case" });
  await expect(deleteButton).toBeVisible();
  await deleteButton.click();
  await expectBoxContained(page, page.getByRole("alertdialog"));
  await expectBoxContained(page, page.getByRole("button", { name: "Cancel" }));
  await page.getByRole("button", { name: "Cancel" }).click();
});

test("responsive Director policy separates decision authority", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 900 });
  await login(page, "olivia-koh");
  await openWorkspaceTab(page, "Policy");
  await expectPolicyMutationControls(page, false);
  await expectShellContained(page);
});

test("responsive HR administration contains proposal-only policy controls", async ({ page }) => {
  test.setTimeout(240_000);
  await page.setViewportSize({ width: 360, height: 900 });
  await login(page, "hr-admin");
  for (const width of REPRESENTATIVE_VIEWPORTS) {
    await page.setViewportSize({ width, height: 900 });
    for (const [tab, heading] of [["Users", "Users"], ["Teams", "Teams"], ["Policy", "Policy and rules"]] as const) {
      await openWorkspaceTab(page, tab);
      await expect(page.getByRole("heading", { name: heading })).toBeVisible();
      await expectShellContained(page);
      if (tab === "Policy") {
        await expectPolicyMutationControls(page, true);
      }
    }
  }
});


type DisclosureBrowser = Window & { __disclosureFoundation: {
  render: (scope: string, active?: boolean, revision?: string, omitted?: "more" | "technical") => void;
  revealDiagnostic: () => void;
  dispose: () => void;
  actions: number;
} };

test("disclosure foundation browser fixture preserves Main, independent native controls, scoped drafts and print", async ({ page }) => {
  await login(page);
  const mutations: string[] = [];
  page.on("request", request => {
    if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method())) mutations.push(request.method());
  });
  // The additive foundation is intentionally not adopted by CaseDetail in this slice.
  // Mount its actual Vite module in the authenticated shell to exercise native browser semantics.
  await page.evaluate(async () => {
    const reactPath = "/node_modules/.vite/deps/react.js";
    const domPath = "/node_modules/.vite/deps/react-dom_client.js";
    const stagePath = "/src/pages/StageDisclosure.tsx";
    const [{ default: React }, { default: { createRoot } }, { default: Stage, revealStage }] = await Promise.all([
      import(reactPath), import(domPath), import(stagePath),
    ]);
    const host = document.createElement("div"); host.id = "disclosure-foundation-browser"; host.className = "card";
    document.body.append(host); const root = createRoot(host);
    const unrelatedHost = document.createElement("div"); unrelatedHost.id = "disclosure-unrelated-workspace";
    document.body.append(unrelatedHost); const unrelatedRoot = createRoot(unrelatedHost);
    unrelatedRoot.render(React.createElement(Stage, {
      title: "Unrelated workspace", scopeKey: "unrelated-scope",
      main: React.createElement(React.Fragment, null,
        React.createElement("p", { id: "fixture-unrelated-main" }, "Unrelated workspace must not print"),
        React.createElement("button", { id: "fixture-external-action", type: "button" }, "Other workspace action")),
      moreDetails: React.createElement("p", { id: "fixture-unrelated-support" }, "Unrelated support must not print"),
    }));
    const fixture = {
      actions: 0,
      render(scopeKey: string, active = true, revision = "one", omitted?: "more" | "technical") {
        root.render(React.createElement(Stage, {
          title: "Foundation readiness", scopeKey, active, final: true,
          main: React.createElement("section", { className: "review-and-send" },
            React.createElement("p", { id: "fixture-main", tabIndex: -1 }, "Blocked " + revision),
            React.createElement("button", { id: "fixture-required", type: "button", className: "review-and-send__edit", onClick: () => { fixture.actions += 1; } }, "Required fixture correction")),
          moreDetails: omitted === "more" ? undefined : React.createElement("label", null, "Optional fixture draft",
            React.createElement("input", { id: "fixture-draft", defaultValue: "retained scope draft" }),
            React.createElement("span", { id: "fixture-hidden-detail", hidden: true }, "Hidden detail must remain excluded")),
          technicalDetails: omitted === "technical" ? undefined : React.createElement("button", { id: "fixture-diagnostic", type: "button" }, "Safe fixture diagnostic"),
        }));
      },
      revealDiagnostic() { revealStage(host.querySelector("#fixture-diagnostic")!); },
      dispose() { root.unmount(); host.remove(); unrelatedRoot.unmount(); unrelatedHost.remove(); },
    };
    (window as DisclosureBrowser).__disclosureFoundation = fixture;
    fixture.render("actor-a:session-a:case-a", true);
  });
  const fixture = page.locator("#disclosure-foundation-browser");
  const more = fixture.locator("details").nth(0), technical = fixture.locator("details").nth(1);
  const moreToggle = fixture.getByText("More details — Foundation readiness", { exact: true });
  const technicalToggle = fixture.getByText("Technical details — Foundation readiness", { exact: true });
  const draft = fixture.getByLabel("Optional fixture draft");
  try {
    await expect(more).not.toHaveAttribute("open", ""); await expect(technical).not.toHaveAttribute("open", "");
    await fixture.getByRole("button", { name: "Required fixture correction" }).focus();
    await page.keyboard.press("Tab"); await expect(moreToggle).toBeFocused();
    await page.keyboard.press("Tab"); await expect(technicalToggle).toBeFocused();
    await expect(moreToggle).toHaveAccessibleName("More details — Foundation readiness");
    await expect(technicalToggle).toHaveAccessibleName("Technical details — Foundation readiness");
    expect(await technicalToggle.evaluate(element => getComputedStyle(element).outlineStyle)).not.toBe("none");
    for (const width of [1440, 1280, 900, 360]) {
      await page.setViewportSize({ width, height: 900 });
      for (const [moreOpen, technicalOpen] of [[false, false], [true, false], [true, true], [false, true]]) {
        for (const [details, toggle, open] of [[more, moreToggle, moreOpen], [technical, technicalToggle, technicalOpen]] as const) {
          if (await details.evaluate(element => (element as HTMLDetailsElement).open) !== open) {
            await toggle.focus(); await toggle.press("Enter");
          }
          if (open) await expect(details).toHaveAttribute("open", "");
          else await expect(details).not.toHaveAttribute("open", "");
        }
        await expect(fixture.getByRole("button", { name: "Required fixture correction" })).toBeVisible();
        if (moreOpen) await expect(draft).toBeVisible(); else await expect(draft).toBeHidden();
        if (technicalOpen) await expect(fixture.getByRole("button", { name: "Safe fixture diagnostic" })).toBeVisible();
        else await expect(fixture.getByRole("button", { name: "Safe fixture diagnostic" })).toBeHidden();
        await expectDocumentContained(page);
        await expectBoxContained(page, fixture.getByRole("button", { name: "Required fixture correction" }));
        const parent = fixture.locator(":scope > section > h2 > button");
        await parent.focus(); await expect(parent).toBeFocused();
        expect(await parent.evaluate(element => getComputedStyle(element).outlineStyle)).not.toBe("none");
        await parent.press("Enter"); await expect(parent).toHaveAttribute("aria-expanded", "false");
        await expect(fixture.locator("#fixture-main")).toBeHidden(); await expect(draft).toBeHidden();
        await expect(fixture.locator("#fixture-diagnostic")).toBeHidden();
        await parent.press("Space"); await expect(parent).toHaveAttribute("aria-expanded", "true");
        expect(await more.evaluate(element => (element as HTMLDetailsElement).open)).toBe(moreOpen);
        expect(await technical.evaluate(element => (element as HTMLDetailsElement).open)).toBe(technicalOpen);
      }
    }
    await fixture.getByRole("button", { name: "Safe fixture diagnostic" }).focus();
    await technical.evaluate(element => { (element as HTMLDetailsElement).open = false; });
    await expect(technicalToggle).toBeFocused();
    await moreToggle.focus(); await moreToggle.press("Space");
    await expect(more).toHaveAttribute("open", ""); await draft.fill("Unsaved same-scope draft");
    await page.evaluate(() => (window as DisclosureBrowser).__disclosureFoundation.render("actor-a:session-a:case-a", false, "refreshed"));
    await expect(fixture.locator("#fixture-main")).toHaveText("Blocked refreshed");
    await expect(more).toHaveAttribute("open", ""); await expect(draft).toHaveValue("Unsaved same-scope draft");
    await expect(draft).toBeFocused();
    for (const scope of ["actor-b:session-a:case-a", "actor-b:session-b:case-a", "actor-b:session-b:case-b", "actor-b:session-b:case-b:analysis-b"]) {
      if (!(await more.evaluate(element => (element as HTMLDetailsElement).open))) await moreToggle.click();
      await draft.fill("Other scope private draft"); await draft.focus();
      await page.evaluate(scopeKey => (window as DisclosureBrowser).__disclosureFoundation.render(scopeKey, true), scope);
      await expect(more).not.toHaveAttribute("open", ""); await expect(technical).not.toHaveAttribute("open", "");
      await expect(fixture.getByRole("heading", { name: "Foundation readiness", exact: true })).toBeFocused();
      await moreToggle.click(); await expect(draft).toHaveValue("retained scope draft"); await moreToggle.click();
    }
    // Removal must retire historical focus ownership before a later actor/session/case reset.
    const externalAction = page.locator("#fixture-external-action");
    for (const omitted of ["more", "technical"] as const) {
      let scope = "actor-a:session-a:case-a";
      for (const [index, nextScope] of ["actor-b:session-a:case-a", "actor-b:session-b:case-a", "actor-b:session-b:case-b"].entries()) {
        await page.evaluate(scopeKey => (window as DisclosureBrowser).__disclosureFoundation.render(scopeKey), scope);
        await expect(moreToggle).toBeVisible(); await expect(technicalToggle).toBeVisible();
        const control = omitted === "more" ? draft : fixture.locator("#fixture-diagnostic");
        await (omitted === "more" ? moreToggle : technicalToggle).click();
        await control.focus(); await expect(control).toBeFocused();
        await page.evaluate(({ scopeKey, removed }) => (window as DisclosureBrowser).__disclosureFoundation.render(scopeKey, false, "removed", removed), { scopeKey: scope, removed: omitted });
        await expect(control).toHaveCount(0);
        expect(await page.evaluate(() => document.activeElement === document.body)).toBe(true);
        if (index % 2 === 0) await externalAction.click();
        else {
          await fixture.locator("details summary").last().focus();
          await page.keyboard.press("Tab");
          const externalParent = page.locator("#disclosure-unrelated-workspace h2 > button");
          await expect(externalParent).toBeFocused();
          await page.keyboard.press("Tab");
        }
        await expect(externalAction).toBeFocused();
        await page.evaluate(({ scopeKey, removed }) => (window as DisclosureBrowser).__disclosureFoundation.render(scopeKey, true, "changed", removed), { scopeKey: nextScope, removed: omitted });
        await expect(fixture.locator("#fixture-main")).toHaveText("Blocked changed");
        await expect(externalAction).toBeFocused();
        scope = nextScope;
      }
    }
    await page.evaluate(() => (window as DisclosureBrowser).__disclosureFoundation.render("actor-b:session-b:case-b:analysis-b"));
    await expect(moreToggle).toBeVisible(); await expect(technicalToggle).toBeVisible();
    await page.evaluate(() => (window as DisclosureBrowser).__disclosureFoundation.revealDiagnostic());
    await expect(technical).toHaveAttribute("open", ""); await expect(more).not.toHaveAttribute("open", "");
    // Real print media must include Final support, preserve exclusions and restore every prior combination.
    await page.locator("#disclosure-unrelated-workspace details").evaluate(element => { (element as HTMLDetailsElement).open = true; });
    const parent = fixture.locator(":scope > section > h2 > button");
    for (const parentOpen of [true, false]) for (const [moreOpen, technicalOpen] of [[false, false], [true, false], [true, true], [false, true]]) {
      if ((await parent.getAttribute("aria-expanded") === "true") !== parentOpen) await parent.click();
      await more.evaluate((element, open) => { (element as HTMLDetailsElement).open = open; }, moreOpen);
      await technical.evaluate((element, open) => { (element as HTMLDetailsElement).open = open; }, technicalOpen);
      await page.evaluate(() => window.dispatchEvent(new Event("beforeprint")));
      await fixture.locator("#fixture-main").focus();
      await expect(more).toHaveAttribute("open", ""); await expect(technical).toHaveAttribute("open", "");
      try {
        await page.emulateMedia({ media: "print" });
        for (const content of [fixture.locator("#fixture-main"), more, draft, technical, fixture.locator("#fixture-diagnostic")]) {
          await expect(content).toHaveCSS("visibility", "visible");
          await expect(content).not.toHaveCSS("display", "none");
          await expect(content).toBeVisible();
        }
        await expect(fixture.locator("#fixture-main")).toBeFocused();
        await expect(fixture.locator(".review-and-send")).toHaveCSS("position", "static");
        await expect(fixture.locator(".review-and-send")).toHaveCSS("padding-top", "0px");
        await expect(fixture.locator("#fixture-required")).toHaveCSS("display", "none");
        await expect(fixture.locator("#fixture-required")).toBeHidden();
        await expect(fixture.locator("#fixture-hidden-detail")).toHaveCSS("display", "none");
        await expect(fixture.locator("#fixture-hidden-detail")).toBeHidden();
        for (const unrelated of [page.locator("#root"), page.locator("#fixture-unrelated-main"), page.locator("#fixture-unrelated-support")]) {
          await expect(unrelated).toHaveCSS("visibility", "hidden");
          await expect(unrelated).toBeHidden();
        }
      } finally {
        await page.emulateMedia({ media: "screen" });
        await page.evaluate(() => window.dispatchEvent(new Event("afterprint")));
      }
      expect(await more.evaluate(element => (element as HTMLDetailsElement).open)).toBe(moreOpen);
      expect(await technical.evaluate(element => (element as HTMLDetailsElement).open)).toBe(technicalOpen);
      await expect(parent).toHaveAttribute("aria-expanded", String(parentOpen));
      if (parentOpen) {
        await expect(fixture.locator("#fixture-required")).toBeVisible();
        await expect(fixture.locator("#fixture-main")).toBeFocused();
      } else {
        await expect(fixture.locator("#fixture-required")).toBeHidden();
        await expect(parent).toBeFocused();
      }
    }
    expect(await page.evaluate(() => (window as DisclosureBrowser).__disclosureFoundation.actions)).toBe(0);
    expect(mutations).toEqual([]);
  } finally {
    await page.evaluate(() => (window as DisclosureBrowser).__disclosureFoundation.dispose());
  }
});

test("Search and Registry disclosure keeps Main visible with independent native support and zero writes", async ({ page }) => {
  await login(page);
  const caseId = await openNewCase(page, lowConfidenceFixture);
  await waitForCaseStatus(page, caseId, ["WAITING_FOR_REVIEW"]);
  await page.goto(`/cases/${caseId}`);
  const retainedOwnershipResponse = await page.request.get(`/api/onboarding/cases/${caseId}/ownership`);
  expect([200, 404]).toContain(retainedOwnershipResponse.status());
  // Match fetchOwnership: an authorized absent ownership record projects null.
  const retainedOwnership = retainedOwnershipResponse.status() === 404 ? null : await retainedOwnershipResponse.json();
  const mutations: string[] = [];
  page.on("request", request => {
    if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method())) mutations.push(request.method());
  });
  const comparison = retainedEvidencePath("ux-correction-comparison");
  await mkdir(comparison, { recursive: true });
  await expect(page.getByRole("heading", { name: "Existing-customer search", exact: true })).toBeVisible();
  const label = await page.locator(".stage-disclosure > h2 > button").count() === 8 ? "after" : "before";
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({ path: path.join(comparison, `${label}-case-sections.png`), fullPage: true });
  expect(await page.locator(".stage-disclosure > h2").evaluateAll(items => items.map(item => item.querySelector("button > span")?.textContent ?? item.textContent))).toEqual([
    "Existing-customer search", "Registry verification", "Document verification", "Ownership & UBO",
    "Submission readiness", "GoldTier submission package", "Final review & send", "Historical / resolved issues",
  ]);
  for (const width of [1440, 1280, 900, 360]) {
    await page.setViewportSize({ width, height: 900 });
    for (const name of ["Existing-customer search", "Registry verification", "Document verification", "Ownership & UBO", "Submission readiness", "GoldTier submission package"]) {
      const section = page.getByRole("region", { name, exact: true });
      const more = section.locator(":scope > details").filter({ has: page.getByText(`More details — ${name}`, { exact: true }) });
      const technical = section.locator(":scope > details").filter({ has: page.getByText(`Technical details — ${name}`, { exact: true }) });
      await expect(section.getByRole("heading", { name, exact: true })).toBeVisible();
      const parent = section.locator(":scope > h2 > button");
      await expect(parent).toHaveAttribute("aria-expanded", "true");
      const describedBy = await parent.getAttribute("aria-describedby");
      expect(describedBy).toBeTruthy();
      await parent.focus(); await expectDisclosureContrast(parent);
      await parent.press("Enter"); await expect(parent).toHaveAttribute("aria-expanded", "false");
      await expect(section.locator(":scope > div").first()).toBeHidden();
      await expect(more).toBeHidden(); await expect(technical).toBeHidden();
      await expect(section.locator(":scope > .stage-disclosure__summary")).toBeVisible();
      await parent.press("Space"); await expect(parent).toHaveAttribute("aria-expanded", "true");
      await expect(section.locator(":scope > div").first()).toBeVisible();
      if (name === "Document verification") {
        await expect(section.locator("#case-blocker-review")).toBeVisible();
        await expect(section.getByRole("button", { name: "Use document suggestion for all", exact: true })).toBeVisible();
        await expect(section.getByRole("button", { name: "Confirm decisions & continue onboarding", exact: true })).toBeVisible();
        await expect(section.locator("#case-evidence-documents input[type=file]")).toBeEnabled();
        await expect(section.locator("#case-evidence-reconciliation")).toBeVisible();
        const choice = section.locator('input[data-review-field][value="REJECTED"]').first();
        await expect(choice).toBeVisible();
        if (width === 1440) await choice.check();
        await expect(choice).toBeChecked();
        await expect(section.getByText("Supporting document evidence", { exact: true })).toBeHidden();
        await expect(section.getByRole("heading", { name: "Document processing provenance", exact: true })).toBeHidden();
      }
      if (name === "Ownership & UBO") {
        if (retainedOwnership) {
          await expect(section.getByRole("heading", { name: "Ownership path explorer", exact: true })).toBeVisible();
          await expect(section.getByLabel("Hierarchical ownership structure", { exact: true })).toBeVisible();
        } else {
          // Document review stops this fixture before ownership acquisition.
          await expect(section.locator(":scope > div").first()).toContainText("No ownership analysis is retained in the confirmed response.");
          await expect(section.getByLabel("Hierarchical ownership structure", { exact: true })).toHaveCount(0);
        }
        await expect(section.getByText("Technical calculations and retained paths", { exact: true })).toHaveCount(0);
      }
      if (name === "Submission readiness") {
        await expect(section.getByLabel("Backend-projected readiness", { exact: true })).toBeVisible();
        await expect(section.getByText("System-set Singapore values", { exact: true })).toBeVisible();
      }
      await expect(more).not.toHaveAttribute("open", "");
      await expect(technical).not.toHaveAttribute("open", "");
      await expect(more.locator(":scope > div")).toBeHidden();
      await expect(technical.locator(":scope > div")).toBeHidden();
      const summary = more.locator(":scope > summary");
      await summary.focus(); await expect(summary).toBeFocused();
      expect(await summary.evaluate(element => getComputedStyle(element).outlineStyle)).not.toBe("none");
      await page.keyboard.press("Enter");
      await expect(more.locator(":scope > div")).toBeVisible();
      await expect(technical.locator(":scope > div")).toBeHidden();
      await page.keyboard.press("Space");
      await expect(more.locator(":scope > div")).toBeHidden();
      await page.keyboard.press("Tab");
      await expect(technical.locator(":scope > summary")).toBeFocused();
      await page.keyboard.press("Space");
      await expect(technical.locator(":scope > div")).toBeVisible();
      await expect(more.locator(":scope > div")).toBeHidden();
      await expect(section.locator(":scope > div").first()).toBeVisible();
      await expectDocumentContained(page);
      if (name === "Document verification") {
        await expect(technical).toContainText("LOCAL_PDF_TEXT");
        await expect(technical.locator("details")).toHaveCount(0);
        await expect(technical.locator("button, input, select, textarea")).toHaveCount(0);
        await expect(more.locator("button, input, select, textarea")).toHaveCount(0);
        await expect(section.locator('input[data-review-field][value="REJECTED"]').first()).toBeChecked();
      }
      if (["Ownership & UBO", "Submission readiness", "GoldTier submission package"].includes(name)) {
        await expect(technical.locator("details, button, input, select, textarea")).toHaveCount(0);
        await expect(more.locator("details, button, input, select, textarea")).toHaveCount(0);
        const ids = await section.locator("[id]").evaluateAll(elements => elements.map(element => element.id));
        expect(new Set(ids).size).toBe(ids.length);
      }
      await page.keyboard.press("Enter");
      await expect(technical.locator(":scope > div")).toBeHidden();
    }
  }
  const finalParent = page.getByRole("region", { name: "Final review & send", exact: true }).locator(":scope > h2 > button");
  await finalParent.press("Enter"); await expect(finalParent).toHaveAttribute("aria-expanded", "false");
  await expect(page.getByRole("region", { name: "Final review & send", exact: true }).locator(":scope > div")).toBeHidden();
  await finalParent.press("Space"); await expect(finalParent).toHaveAttribute("aria-expanded", "true");
  // Bounded legacy/empty GET projection exercises the real no-action focus fallback.
  // Auth, HTTP and navigation remain real; no backend state is changed by this fixture.
  await page.route(`**/api/clm/zero-touch/cases/${caseId}`, async route => {
    if (route.request().method() !== "GET") return route.fallback();
    const response = await route.fetch(); const body = await response.json();
    const original = body.active_exceptions[0];
    body.current_stage = "GOLDTIER_SEARCH"; body.evidence_decision_authorized = false;
    body.case.error = null; body.interventions = []; body.processing_pipeline = [];
    body.clm.target_search_checkpoint = null;
    body.active_exceptions = [{ ...original, stage: "GOLDTIER_SEARCH", blocker_code: "GT_SEARCH_REVIEW_REQUIRED",
      blocker_codes: ["GT_SEARCH_REVIEW_REQUIRED"],
      explanation: "Retained Search evidence needs review; no corrective input is authorized.", available_actions: [] }];
    await route.fulfill({ response, json: body });
  });
  await page.goto(`/cases/${caseId}`);
  const fallback = page.locator("#case-existing-customer-search");
  const action = page.getByRole("button", { name: "Blocker: GT SEARCH REVIEW REQUIRED", exact: true });
  await page.getByRole("region", { name: "Existing-customer search", exact: true }).locator(":scope > h2 > button").click();
  await action.focus(); await action.press("Enter");
  await expect(fallback).toBeFocused();
  await expect(fallback).toHaveAccessibleName("Existing-customer search");
  await expect(page.getByText("No corrective input is currently authorized here. Review the retained reason and required evidence.", { exact: true })).toBeVisible();
  const search = page.getByRole("region", { name: "Existing-customer search", exact: true });
  await expect(search).toBeVisible(); await expect(search.locator(":scope > details[open]")).toHaveCount(0);
  expect(mutations).toEqual([]);
});
