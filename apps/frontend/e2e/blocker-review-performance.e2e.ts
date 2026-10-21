import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";
import { createBrowserNetworkPolicy, handleBrowserRoute, retainedEvidencePath } from "../playwright.config";
import { expectDisclosureContrast, openStage } from "./stage-disclosures";

const fields = ["legal_name", "registration_number", "registered_address", "country_of_incorporation"];
const content = Buffer.from([
  "LOCAL PROJECT SYNTHETIC AMBIGUITY TEST ONLY",
  "Legal Name: MERLION CIRCULAR LABS PTE. LTD.", "Legal Name: SECOND SYNTHETIC NAME",
  "UEN: 202400001A", "UEN: 202400002B",
  "Registered Address: 18 INNOVATION WAY, #04-01, 018956, SG", "Registered Address: 18 OTHER TEST ROAD, SG",
  "Country: SG", "Country: MY",
].join("\r\n"));

async function runPerformanceGroup(page: Page, group: number) {
    const evidence = retainedEvidencePath("blocker-regression");
    await page.setViewportSize({ width: 1280, height: 900 });
    const violations: string[] = [];
    const policy = createBrowserNetworkPolicy({ frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!, backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false });
    await page.route("**/*", route => handleBrowserRoute(route, policy, violations));
    await page.goto("/");
    const loginResponse = page.waitForResponse(response => response.url().endsWith("/api/auth/login") && response.request().method() === "POST");
    await page.getByLabel("User ID").fill("maya-lim"); await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    const headers = { "X-CSRF-Token": (await (await loginResponse).json()).csrf_token };
    await expect(page.getByRole("link", { name: "New onboarding", exact: true })).toBeVisible();
    const rows: object[] = [];
    const requests: { method: string; path: string }[] = [];
    page.on("request", request => { const url = new URL(request.url()); if (url.pathname.startsWith("/api/")) requests.push({ method: request.method(), path: url.pathname }); });
    await mkdir(evidence, { recursive: true });
    for (let sample = 0; sample < 10; sample++) {
      const created = await page.request.post("/api/clm/zero-touch/cases", { headers, data: { uen: "202400001A", legal_name: "MERLION CIRCULAR LABS PTE. LTD.", country_of_incorporation: "SG" } });
      expect(created.status()).toBe(201); const cid = (await created.json()).case.case_id;
      const uploaded = await page.request.post(`/api/clm/zero-touch/cases/${cid}/intake/documents`, { headers: { ...headers, "Content-Type": "text/plain", "X-Document-Name": "synthetic-ambiguous.txt" }, data: content });
      expect(uploaded.status()).toBe(201);
      expect((await page.request.post(`/api/clm/zero-touch/cases/${cid}/intake/complete`, { headers, data: { expected_document_count: 1 } })).status()).toBe(200);
      await page.goto(`/cases/${cid}`); await openStage(page, "Document verification");
      await expect(page.locator(".document-field .tag").filter({ hasText: "PENDING" })).toHaveCount(4);
      const batch = await page.locator("#case-blocker-review").count() > 0;
      if (batch) {
        const warning = page.locator(".intervention-card").filter({ has: page.getByRole("heading", {
          name: "Document or reconciliation review required", exact: true,
        }) });
        await expect(warning).toHaveCount(1);
        await expect(warning.getByText("4 related blockers", { exact: true })).toBeVisible();
        const retained = warning.locator(".intervention-evidence-record");
        await expect(retained).toHaveCount(4);
        const current = await (await page.request.get(`/api/clm/zero-touch/cases/${cid}`)).json();
        const ids = current.interventions.filter((item: { owning_stage: string }) => item.owning_stage === "DOCUMENT")
          .map((item: { intervention_id: string }) => item.intervention_id).sort();
        expect(await retained.evaluateAll(elements => elements.map(element => element.getAttribute("data-intervention-id")).sort())).toEqual(ids);
        await warning.locator("details > summary").first().click();
        await expect(retained.first()).toBeVisible();
        await warning.locator("details > summary").first().click();
      }
      if (group === 0 && sample === 0) {
        await page.screenshot({ path: path.join(evidence, batch ? "candidate-before-navigation.png" : "baseline-before-navigation.png") });
        if (batch) {
          const documents = page.getByRole("region", { name: "Document verification", exact: true });
          await expect(documents.locator(":scope > div").first()).toBeVisible();
          await expect(documents.locator(":scope > details[open]")).toHaveCount(0);
          const stage = page.locator('.ds-stage[data-node-id="DOCUMENT_IDP"]');
          await stage.locator("summary").click();
          await stage.getByRole("button", { name: "Open case stage details" }).click();
          await expect(page.locator("input[data-review-field]:not([disabled])").first()).toBeFocused();
          await expect.poll(() => page.locator("input[data-review-field]:not([disabled])").first().evaluate(element => {
            const r = element.getBoundingClientRect();
            const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
            return hit === element || (hit !== null && element.contains(hit));
          })).toBe(true);
          await page.screenshot({ path: path.join(evidence, "candidate-after-action-focus.png") });
        }
      }
      const beginning = requests.length;
      const elapsedStart = Date.now();
      const choiceTimes: number[] = [];
      for (const field of fields) {
        const start = Date.now();
        if (batch) {
          const control = page.locator(`input[data-review-field="${field}"][value="REJECTED"]`);
          await control.focus();
          await expect.poll(() => control.evaluate(element => {
            const r = element.getBoundingClientRect();
            const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
            return hit === element || (hit !== null && element.contains(hit));
          })).toBe(true);
          await control.check();
          await expect(control).toBeFocused(); await expect(control).toBeEnabled();
        } else {
          const button = page.getByRole("button", { name: `Reject ${field.replaceAll("_", " ")} suggestion`, exact: true });
          await expect(button).toBeEnabled();
          const applied = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/reviews"));
          await button.click(); expect((await applied).status()).toBe(200);
          await expect(page.getByText("Saving", { exact: true })).toHaveCount(0);
          await expect(page.locator(".case-action-progress")).toHaveCount(0);
        }
        choiceTimes.push(Date.now() - start);
      }
      const selectionMs = Date.now() - elapsedStart;
      const selectionRequests = requests.slice(beginning);
      let confirmationMs = 0;
      if (batch) {
        expect(selectionRequests.filter(request => request.method !== "GET")).toEqual([]);
        expect(selectionRequests.filter(request => request.method === "GET")).toEqual([]);
        const confirm = page.getByRole("button", { name: "Confirm decisions & continue onboarding", exact: true });
        await expect(confirm).toBeEnabled(); await expectDisclosureContrast(confirm);
        if (group === 0 && sample === 0) {
          await confirm.scrollIntoViewIfNeeded();
          await page.screenshot({ path: path.join(evidence, "candidate-four-draft-choices.png") });
          await page.setViewportSize({ width: 390, height: 844 });
          await expect(confirm).toBeVisible();
          await confirm.scrollIntoViewIfNeeded();
          await expect(confirm).toBeInViewport({ ratio: 1 });
          expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
          await page.screenshot({ path: path.join(evidence, "candidate-mobile-draft.png") });
          await page.setViewportSize({ width: 1280, height: 900 });
        }
        const applied = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/review-decisions"));
        const confirmationStart = Date.now();
        await confirm.click(); expect((await applied).status()).toBe(200);
        await expect(page.locator("#case-blocker-review")).toHaveCount(0);
        confirmationMs = Date.now() - confirmationStart;
      }
      const measured = requests.slice(beginning);
      expect(measured.filter(request => request.method === "POST")).toHaveLength(batch ? 1 : 4);
      const current = await (await page.request.get(`/api/clm/zero-touch/cases/${cid}`)).json();
      expect(current.status).toBe("WAITING_FOR_REVIEW"); expect(current.case.goldtier_result).toBeNull();
      expect(measured.some(request => request.path.endsWith("/target-confirmation"))).toBe(false);
      if (group === 0 && sample === 0) {
        await page.locator(".intervention-card").first().scrollIntoViewIfNeeded();
        await page.screenshot({ path: path.join(evidence, batch ? "candidate-after-confirm-remaining-blocker.png" : "baseline-after-four-decisions.png") });
      }
      rows.push({ sample: group * 10 + sample, mode: batch ? "batch" : "baseline", viewport: page.viewportSize(), selection_ms: selectionMs, confirmation_ms: confirmationMs, total_ms: selectionMs + confirmationMs, choice_ms: choiceTimes, requests: measured, selection_requests: selectionRequests });
    }
    await writeFile(path.join(evidence, `group-${group + 1}.json`), JSON.stringify(rows, null, 2)+"\n");
    expect(violations).toEqual([]);
}

test("Blocker decision review performance sample group 1", async ({ page }) => {
  await runPerformanceGroup(page, 0);
});

test("Blocker decision review performance sample group 2", async ({ page }) => {
  await runPerformanceGroup(page, 1);
});

test("Blocker decision review performance sample group 3", async ({ page }) => {
  await runPerformanceGroup(page, 2);
});

test("Blocker decision review keyboard focus stays unobscured and footer text readable at review widths", async ({ page }) => {
  const violations: string[] = [];
  const policy = createBrowserNetworkPolicy({ frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!, backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false });
  await page.route("**/*", route => handleBrowserRoute(route, policy, violations));
  await page.goto("/");
  const loginResponse = page.waitForResponse(response => response.url().endsWith("/api/auth/login") && response.request().method() === "POST");
  await page.getByLabel("User ID").fill("maya-lim"); await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  const headers = { "X-CSRF-Token": (await (await loginResponse).json()).csrf_token };
  await expect(page.getByRole("link", { name: "New onboarding", exact: true })).toBeVisible();
  const created = await page.request.post("/api/clm/zero-touch/cases", { headers, data: { uen: "202400001A", legal_name: "MERLION CIRCULAR LABS PTE. LTD.", country_of_incorporation: "SG" } });
  expect(created.status()).toBe(201); const cid = (await created.json()).case.case_id;
  const uploaded = await page.request.post(`/api/clm/zero-touch/cases/${cid}/intake/documents`, { headers: { ...headers, "Content-Type": "text/plain", "X-Document-Name": "synthetic-ambiguous.txt" }, data: content });
  expect(uploaded.status()).toBe(201);
  expect((await page.request.post(`/api/clm/zero-touch/cases/${cid}/intake/complete`, { headers, data: { expected_document_count: 1 } })).status()).toBe(200);
  for (const viewport of [{ width: 768, height: 1024 }, { width: 1024, height: 768 }]) {
    await page.setViewportSize(viewport);
    await page.goto(`/cases/${cid}`); await openStage(page, "Document verification");
    const review = page.locator("#case-blocker-review");
    await expect(review).toHaveCount(1);
    await review.locator("select:enabled, button:enabled").first().focus();
    const visited: string[] = [];
    for (let stop = 0; stop < 40; stop++) {
      const focused = await page.evaluate(() => {
        const element = document.activeElement;
        return element?.closest("#case-blocker-review") ? element.getAttribute("aria-label") ?? element.textContent?.trim() ?? element.tagName : null;
      });
      if (focused === null) break;
      visited.push(focused);
      // WCAG 2.2 SC 2.4.11: the focused review control is inside the viewport and nothing covers its centre.
      await expect.poll(() => page.evaluate(() => {
        const element = document.activeElement!;
        const r = element.getBoundingClientRect();
        const { clientWidth, clientHeight } = document.documentElement;
        // Layout rects are fractional; painting snaps them to whole pixels.
        const [left, top, right, bottom] = [r.left, r.top, r.right, r.bottom].map(Math.round);
        if (top < 0 || left < 0 || bottom > clientHeight || right > clientWidth) {
          return `outside the ${clientWidth}x${clientHeight} viewport at ${[left, top, right, bottom].join(",")}`;
        }
        const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
        return hit === element || (hit !== null && element.contains(hit)) ? "unobscured" : `covered by ${hit?.closest("[class]")?.className ?? "nothing"}`;
      }), `${focused} at ${viewport.width}x${viewport.height}`).toBe("unobscured");
      await page.keyboard.press("Tab");
    }
    expect(await page.evaluate(() => document.activeElement?.closest("#case-blocker-review") == null)).toBe(true);
    expect(visited.filter(name => /^(Accept|Reject) document suggestion for /.test(name))).toHaveLength(fields.length);
    expect(visited.filter(name => name.startsWith("Correction for "))).toHaveLength(fields.length);
    expect(visited.filter(name => name.startsWith("Add note for "))).toHaveLength(fields.length);
    expect(visited).toContain("Use registry value for all undecided");
    expect(visited).toContain("How drafts work");
  }
  // WCAG 2.2 SC 1.4.4: the footer status, hint and "How drafts work" keep a readable column at every review width.
  for (const viewport of [{ width: 360, height: 780 }, { width: 768, height: 1024 }, { width: 960, height: 800 }, { width: 1024, height: 768 }, { width: 1280, height: 800 }, { width: 1440, height: 900 }]) {
    await page.setViewportSize(viewport);
    await page.goto(`/cases/${cid}`); await openStage(page, "Document verification");
    const footer = page.locator("#case-blocker-review .blocker-review__footer");
    await expect(footer).toHaveCount(1);
    const measure = () => footer.evaluate(element => {
      const style = getComputedStyle(element);
      const column = element.getBoundingClientRect().width - ["borderLeftWidth", "borderRightWidth", "paddingLeft", "paddingRight"]
        .reduce((total, side) => total + parseFloat(style[side as "paddingLeft"]), 0);
      const texts = [...element.querySelectorAll(":scope > p, :scope > details, :scope > details[open] > p")];
      const actions = element.querySelector(":scope > .document-card__actions")!.getBoundingClientRect();
      const status = element.querySelector(":scope > .blocker-review__status")!.getBoundingClientRect();
      return {
        column, narrowest: Math.min(...texts.map(text => text.getBoundingClientRect().width)), texts: texts.length,
        height: element.getBoundingClientRect().height, beside: actions.left >= status.right,
      };
    });
    for (const [state, texts, maxHeight] of [["closed", 3, 400], ["open", 5, 720]] as const) {
      if (state === "open") await footer.getByText("How drafts work", { exact: true }).click();
      const geometry = await measure();
      const where = `${state} footer at ${viewport.width}x${viewport.height}: ${JSON.stringify(geometry)}`;
      expect(geometry.texts, where).toBe(texts);
      // At least 18rem, or the whole column where the review is narrower; 1px absorbs sub-pixel layout.
      expect(geometry.narrowest, where).toBeGreaterThanOrEqual(Math.min(288, geometry.column) - 1);
      expect(geometry.height, where).toBeLessThanOrEqual(maxHeight);
      // The side-by-side footer is kept where the review is wide enough for it.
      expect(geometry.beside, where).toBe(viewport.width >= 1440);
    }
  }
  expect(violations).toEqual([]);
});
