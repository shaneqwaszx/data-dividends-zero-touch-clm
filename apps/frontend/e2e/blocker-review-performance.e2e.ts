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
          await page.locator(".stage-disclosure > h2 > button").filter({ hasText: "Document verification" }).click();
          const stage = page.locator('.ds-stage[data-node-id="DOCUMENT_IDP"]');
          await stage.locator("summary").click();
          await stage.getByRole("button", { name: "Open case stage details" }).click();
          await expect(page.locator("select[data-review-field]").first()).toBeFocused();
          await expect.poll(() => page.locator("select[data-review-field]").first().evaluate(element => {
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
          const control = page.locator(`select[data-review-field="${field}"]`);
          await control.focus();
          await expect.poll(() => control.evaluate(element => {
            const r = element.getBoundingClientRect();
            const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
            return hit === element || (hit !== null && element.contains(hit));
          })).toBe(true);
          await control.selectOption("REJECTED");
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
