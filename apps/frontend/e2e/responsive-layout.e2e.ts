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

async function expectShellContained(page: Page) {
  await expectDocumentContained(page);
  await expectBoxContained(page, page.getByRole("navigation", { name: "Main workspace" }));
  await expectBoxContained(page, page.locator(".nav-brand"));
  await expectBoxContained(page, page.locator(".nav-tabs"));
  await expectBoxContained(page, page.locator(".nav-meta .environment-banner"));
  await expect(page.locator(".nav-meta .environment-banner__label")).toBeVisible();
  await expectBoxContained(page, page.locator(".operator-account__button"));
}

async function openNewCase(page: Page, fixture: string): Promise<string> {
  await openWorkspaceTab(page, "New onboarding");
  const startFresh = page.getByRole("button", { name: "Start a new case" });
  if (await startFresh.isVisible()) await startFresh.click();
  await expect(page.getByRole("heading", { name: "Start onboarding" })).toBeVisible();
  await page.getByLabel("Jurisdiction").selectOption("SG");
  await page.getByLabel("Registration ID / UEN").fill("202400001A");
  await page.locator("#home-document").setInputFiles(fixture);
  await page.getByRole("button", { name: "Create onboarding" }).click();
  await expect(page).toHaveURL(/\/new-onboarding\/([0-9a-f-]{36})$/i, {
    timeout: 30_000,
  });
  return page.url().split("/").at(-1)!;
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

test("responsive shell contains primary screens, account hover, forms, tables, and dialogs", async ({ page }) => {
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

  const completedCaseId = await openNewCase(page, cleanFixture);
  await waitForCaseStatus(page, completedCaseId, ["COMPLETED"]);
  const reviewCaseId = await openNewCase(page, lowConfidenceFixture);
  await waitForCaseStatus(page, reviewCaseId, ["WAITING_FOR_REVIEW"]);
  await expect(page.getByRole("button", { name: "Assign reviewer" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Return for rework" })).toHaveCount(0);

  for (const width of REPRESENTATIVE_VIEWPORTS) {
    await page.setViewportSize({ width, height: 900 });
    const representativeRoutes = [
      ["Dashboard", "/dashboard", "Dashboard"],
      ["New onboarding", "/new-onboarding", ""],
      ["Cases", "/cases", "Cases"],
      [`/cases/${reviewCaseId}`, `/cases/${reviewCaseId}`, "Document evidence and review"],
      ["Onboarded", "/onboarded", "Onboarded"],
      [`/onboarded/${completedCaseId}`, `/onboarded/${completedCaseId}`, ""],
      ["Audit", "/audit", "Case activity"],
      ["Policy", "/policy", "Policy and rules"],
    ] as const;
    for (const [target, route, heading] of representativeRoutes) {
      await test.step(`${width}px ${route}`, async () => {
        if (target.startsWith("/")) {
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
      });
    }
  }

  await page.setViewportSize({ width: 360, height: 900 });
  await logout(page);
  await login(page, "ethan-tan");
  await page.goto(`/cases/${completedCaseId}`);
  const deleteButton = page.getByRole("button", { name: "Delete case" });
  await expect(deleteButton).toBeVisible();
  await deleteButton.click();
  await expectBoxContained(page, page.getByRole("alertdialog"));
  await expectBoxContained(page, page.getByRole("button", { name: "Cancel" }));
  await page.getByRole("button", { name: "Cancel" }).click();

  await page.goto(`/cases/${reviewCaseId}`);
  await expect(page.getByRole("heading", { name: "Document evidence and review" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Accept .* suggestion/ }).first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Assign reviewer" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Return for rework" })).toHaveCount(0);
  await expectDocumentContained(page);

  await logout(page);
  await login(page, "hr-admin");
  for (const width of REPRESENTATIVE_VIEWPORTS) {
    await page.setViewportSize({ width, height: 900 });
    for (const [tab, heading] of [["Users", "Users"], ["Teams", "Teams"], ["Policy", "Policy and rules"]] as const) {
      await openWorkspaceTab(page, tab);
      await expect(page.getByRole("heading", { name: heading })).toBeVisible();
      await expectShellContained(page);
    }
  }
});
