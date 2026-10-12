import { expect, test, type Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { createBrowserNetworkPolicy, handleBrowserRoute, retainedEvidencePath } from "../playwright.config";
import { openStage } from "./stage-disclosures";
import { reviewPendingFields, reviewSourceChoices } from "./blocker-decisions";
import attentionProjections from "../src/test-fixtures/attention-projections.json" with { type: "json" };

const clean = "Legal Name: MERLION CIRCULAR LABS PTE. LTD.\nUEN: 202400001A\nRegistered Address: 18 INNOVATION WAY, #04-01, 018956, SG\nCountry: SG";
async function login(page: Page) {
  await page.emulateMedia({ reducedMotion: "reduce" });
  const violations: string[] = [];
  const policy = createBrowserNetworkPolicy({ frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!, backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false });
  await page.route("**/*", route => handleBrowserRoute(route, policy, violations));
  await page.goto("/");
  const loggedIn = page.waitForResponse(response => response.url().endsWith("/api/auth/login"));
  await page.getByLabel("User ID").fill("maya-lim"); await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  expect((await loggedIn).status()).toBe(200);
  return { headers: { "X-CSRF-Token": (await (await loggedIn).json()).csrf_token }, violations };
}
async function create(page: Page, headers: Record<string, string>, uen: string, completeIdentity = false) {
  const response = await page.request.post("/api/clm/zero-touch/cases", { headers, data: { uen,
    ...(completeIdentity ? { legal_name: "MERLION CIRCULAR LABS PTE. LTD.", country_of_incorporation: "SG" } : {}) } });
  expect(response.status()).toBe(201); return (await response.json()).case.case_id as string;
}
async function collapse(page: Page, title: string) {
  const control = page.getByRole("button", { name: title, exact: true });
  if (await control.getAttribute("aria-expanded") === "true") await control.click();
}

test("UX refinement attention identity, sticky twelve-stage rail and mobile keyboard routing", async ({ page }) => {
  const { headers, violations } = await login(page);
  const cid = await create(page, headers, "99999999Z");
  await page.setViewportSize({ width: 1280, height: 720 }); await page.goto(`/cases/${cid}`);
  const mutations: string[] = [];
  page.on("request", request => { if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method())) mutations.push(new URL(request.url()).pathname); });
  const attention = page.getByRole("region", { name: "Attention required", exact: true });
  // The real GET contains the registry exception plus a distinct missing-identity projection.
  const live = await (await page.request.get(`/api/clm/zero-touch/cases/${cid}`)).json();
  expect(live.active_exceptions).toHaveLength(1); expect(live.interventions).toHaveLength(2);
  expect(new Set(live.interventions.map((item: { intervention_id: string }) => item.intervention_id)).size).toBe(2);
  await expect(attention).toContainText("2 active blockers");
  await expect(attention).toContainText("Initial identity incomplete");
  await expect(attention).toContainText("Registry identity requires correction");
  await expect(page.locator(".case-pipeline-panel .ds-stage")).toHaveCount(12);
  await collapse(page, "Registry verification");
  const action = attention.getByRole("button", { name: /^Blocker:/ }).first();
  await action.focus(); await action.press("Enter"); await expect(page.locator("#identity-registration-number")).toBeFocused();
  await expect(page.getByRole("button", { name: "Registry verification", exact: true })).toHaveAttribute("aria-expanded", "true");
  // Open retained sections to make the page tall, then scroll main content independently.
  await openStage(page, "Ownership & UBO"); await openStage(page, "GoldTier submission package");
  await page.evaluate(() => window.scrollTo(0, 500));
  await expect.poll(async () => page.evaluate(() => window.scrollY)).toBeGreaterThan(100);
  const rail = page.locator(".case-pipeline-panel");
  await expect.poll(async () => (await rail.boundingBox())!.y).toBeGreaterThanOrEqual(0);
  expect((await rail.boundingBox())!.y).toBeLessThanOrEqual(13);
  expect((await rail.boundingBox())!.height).toBeLessThanOrEqual(696);
  await rail.locator(".ds-stage").last().locator("summary").focus();
  await expect(rail.locator(".ds-stage").last().locator("summary")).toBeFocused();
  expect(await rail.evaluate(element => element.scrollTop)).toBeGreaterThan(0);
  const evidence = retainedEvidencePath("ux-refinement"); await mkdir(evidence, { recursive: true });
  await rail.evaluate(element => { element.scrollTop = 0; });
  await page.screenshot({ path: path.join(evidence, "desktop-sticky.png") });
  for (const width of [1024, 768, 360]) {
    await page.setViewportSize({ width, height: 900 });
    await page.evaluate(() => window.scrollTo(0, 0));
    if (width <= 900) expect(await rail.evaluate(element => getComputedStyle(element).position)).toBe("static");
    expect(await page.evaluate(() => document.body.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
    await collapse(page, "Registry verification"); await action.focus(); await action.press("Enter");
    await expect(page.locator("#identity-registration-number")).toBeFocused();
    if (width === 360) await page.screenshot({ path: path.join(evidence, "mobile-corrective-focus.png") });
  }
  expect(mutations).toEqual([]); expect(violations).toEqual([]);
});

test("UX refinement specific document decisions, resolved attention and final action across cases", async ({ page }) => {
  const { headers, violations } = await login(page);
  const cid = await create(page, headers, "202400001A", true);
  const uploaded = await page.request.post(`/api/clm/zero-touch/cases/${cid}/intake/documents`, { headers: { ...headers, "Content-Type": "text/plain", "X-Document-Name": "synthetic-ux-conflict.txt" }, data: Buffer.from(clean.replace("MERLION CIRCULAR LABS PTE. LTD.", "OTHER SYNTHETIC NAME")) });
  expect(uploaded.status()).toBe(201);
  const started = await page.request.post(`/api/clm/zero-touch/cases/${cid}/intake/complete`, { headers, data: { expected_document_count: 1 } });
  expect(started.status()).toBe(200); const summary = await started.json(); expect(summary.current_stage).toBe("DOCUMENT");
  await page.goto(`/cases/${cid}`);
  const attention = page.getByRole("region", { name: "Attention required", exact: true });
  await collapse(page, "Document verification");
  const navigationMutations: string[] = [];
  const listener = (request: import("@playwright/test").Request) => { if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method())) navigationMutations.push(new URL(request.url()).pathname); };
  page.on("request", listener);
  await attention.getByRole("button", { name: /^Blocker:/ }).first().click();
  await expect(page.locator("select[data-review-field]:focus, select[data-discrepancy-id]:focus")).toHaveCount(1);
  expect(navigationMutations).toEqual([]); page.off("request", listener);
  await reviewPendingFields(page); await reviewSourceChoices(page);
  await expect(attention).not.toContainText("DOCUMENT SOURCE CONFLICT");
  await expect(attention).toContainText("No immediate blockers");
  const finalAction = attention.getByRole("button", { name: "Action: Review and send", exact: true });
  await expect(finalAction).toBeVisible(); await collapse(page, "Final review & send");
  await finalAction.focus(); await finalAction.press("Enter");
  await expect(page.locator("#case-review-and-send .btn-primary")).toBeFocused();
  const state = await (await page.request.get(`/api/clm/zero-touch/cases/${cid}`)).json();
  expect(state.case.target_dispatch_confirmation).toBeNull(); expect(state.case.goldtier_result).toBeNull();
  const evidence = retainedEvidencePath("ux-refinement"); await mkdir(evidence, { recursive: true });
  await page.setViewportSize({ width: 1280, height: 900 }); await page.screenshot({ path: path.join(evidence, "desktop-final-action.png") });
  await page.setViewportSize({ width: 360, height: 900 }); await finalAction.focus(); await finalAction.press("Enter");
  await expect(page.locator("#case-review-and-send .btn-primary")).toBeFocused();
  await page.screenshot({ path: path.join(evidence, "mobile-final-action.png") });
  const other = await create(page, headers, "99999999Z"); await page.goto(`/cases/${other}`);
  await expect(attention).not.toContainText("Review and send"); await expect(attention).toContainText("2 active blockers");
  await expect(attention).toContainText("Initial identity incomplete");
  expect(violations).toEqual([]);
});

for (const withDocument of [false, true]) {
  test(`PR84 projection-only identity attention ${withDocument ? "with independent document" : "without exception"}`, async ({ page }) => {
    const { headers, violations } = await login(page);
    const created = await page.request.post("/api/clm/zero-touch/cases", { headers,
      data: { uen: "202400001A", legal_name: "MERLION CIRCULAR LABS PTE. LTD.", country_of_incorporation: "SG" } });
    expect(created.status()).toBe(201); const original = await created.json(); const cid = original.case.case_id;
    expect(original.status).toBe("PENDING_INPUTS"); expect(original.evidence_decision_authorized).toBe(true);
    // Auth/backend are real. Only this case's GET projection is a controlled legacy-input fixture,
    // generated by unchanged project_human_interventions from validated backend models.
    let resolved = false;
    await page.route(`**/api/clm/zero-touch/cases/${cid}`, async route => {
      expect(route.request().method()).toBe("GET");
      const response = await route.fetch(); expect(response.status()).toBe(200);
      const actual = await response.json();
      const fixture = withDocument ? attentionProjections.identityAndDocument : attentionProjections.identityOnly;
      await route.fulfill({ response, json: resolved ? { ...actual, version: actual.version + 1 } : {
        ...actual, case: { ...actual.case, initial_identity: null },
        interventions: fixture.interventions,
        active_exceptions: fixture.active_exceptions.map(item => ({ ...item, case_id: cid })),
      } });
    });
    const mutations: string[] = [];
    page.on("request", request => { if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method())) mutations.push(new URL(request.url()).pathname); });
    await page.goto(`/cases/${cid}`);
    const attention = page.getByRole("region", { name: "Attention required", exact: true });
    await expect(attention).toContainText(`${withDocument ? 2 : 1} active blocker`);
    await expect(attention).not.toContainText("No immediate blockers");
    if (withDocument) await expect(attention).toContainText("Document or reconciliation review required");
    const action = attention.getByRole("button", { name: "Action: Correct identity", exact: true });
    const evidence = retainedEvidencePath("pr84-projection-attention"); await mkdir(evidence, { recursive: true });
    for (const width of [1280, 360]) {
      await page.setViewportSize({ width, height: 900 }); await collapse(page, "Registry verification");
      await action.focus(); await action.press("Enter");
      await expect(page.locator("#identity-registration-number")).toBeFocused();
      await expect(page.getByRole("button", { name: "Registry verification", exact: true })).toHaveAttribute("aria-expanded", "true");
      await expect(page.getByRole("button", { name: "Save details and recheck Search", exact: true })).toHaveCount(1);
      expect(await page.evaluate(() => document.body.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
      await page.screenshot({ path: path.join(evidence, `projection-${withDocument ? "document" : "identity"}-${width}.png`) });
    }
    resolved = true; await page.reload();
    await expect(attention).not.toContainText("Correct identity"); await expect(attention).toContainText("No immediate blockers");
    const otherResponse = await page.request.post("/api/clm/zero-touch/cases", { headers,
      data: { uen: "202400001A", legal_name: "MERLION CIRCULAR LABS PTE. LTD.", country_of_incorporation: "SG" } });
    expect(otherResponse.status()).toBe(201); const other = (await otherResponse.json()).case.case_id;
    await page.goto(`/cases/${other}`);
    await expect(attention).not.toContainText("Correct identity"); await expect(attention).toContainText("No immediate blockers");
    const retained = await (await page.request.get(`/api/clm/zero-touch/cases/${cid}`)).json();
    expect(retained.version).toBe(original.version); expect(retained.case).toEqual(original.case);
    expect(mutations).toEqual([]); expect(violations).toEqual([]);
  });
}
