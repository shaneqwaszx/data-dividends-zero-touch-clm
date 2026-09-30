import path from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test, type Locator, type Page } from "@playwright/test";
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
const lowConfidenceFixture = path.resolve(
  currentDirectory,
  "../../backend/tests/fixtures/uat/low-confidence.pdf",
);

const VIEWPORTS = [360, 390, 480, 768, 1024, 1280, 1440] as const;
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
    expect(tile.actionText).toBe("Review details");
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
  await page.getByLabel("Legal name").fill("MERLION CIRCULAR LABS PTE. LTD.");
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
  const displayOnlyRule = page.getByText("Add display-only rule", { exact: true });
  const edit = page.getByRole("button", { name: "Edit" });
  const reset = page.getByRole("button", { name: "Reset to default" });
  if (visible) {
    await expect(displayOnlyRule).toBeVisible();
    await expect(edit.first()).toBeVisible();
    await expect(reset.first()).toBeVisible();
    return;
  }
  await expect(displayOnlyRule).toHaveCount(0);
  await expect(edit).toHaveCount(0);
  await expect(reset).toHaveCount(0);
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
    fields: Array<{ review_status: string; original_extracted_value: string | null }>;
  }>).find((document) => document.superseded_by_document_id === null);
  expect(currentDocument).toBeDefined();
  expect(currentDocument?.state).toBe("REVIEW_REQUIRED");
  expect(currentDocument?.fields.some((field) => (
    field.review_status === "PENDING" && field.original_extracted_value !== null
  ))).toBe(true);
  await expect(page.getByRole("heading", { name: "Document evidence and review" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Accept .* suggestion/ }).first()).toBeVisible();
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
  await page.getByLabel("Legal name").fill("MERLION CIRCULAR LABS PTE. LTD.");
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
  const reviewCaseId = await openNewCase(page, lowConfidenceFixture);
  await waitForCaseStatus(page, reviewCaseId, ["WAITING_FOR_REVIEW"]);
  const reviewSummaryResponse = await page.request.get(`/api/clm/zero-touch/cases/${reviewCaseId}`);
  expect(reviewSummaryResponse.ok()).toBe(true);
  const reviewSummary = await reviewSummaryResponse.json() as {
    active_exceptions: Array<{ blocker_code: string }>;
    interventions: Array<{ blocker_code: string }>;
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
  await expect(page.getByText("No action available", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /replay|retry target/i })).toHaveCount(0);
});

test("responsive Relationship Manager controls contain policy and delete dialog", async ({ page }) => {
  test.setTimeout(240_000);
  await page.setViewportSize({ width: 360, height: 900 });
  await login(page, "ethan-tan");
  await openWorkspaceTab(page, "Policy");
  await expectPolicyMutationControls(page, true);
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

test("responsive Director policy exposes mutation controls", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 900 });
  await login(page, "olivia-koh");
  await openWorkspaceTab(page, "Policy");
  await expectPolicyMutationControls(page, true);
  await expectShellContained(page);
});

test("responsive HR administration contains representative routes without policy mutation", async ({ page }) => {
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
        await expectPolicyMutationControls(page, false);
      }
    }
  }
});
