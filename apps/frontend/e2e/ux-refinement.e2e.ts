import { expect, test, type Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { createBrowserNetworkPolicy, handleBrowserRoute, retainedEvidencePath } from "../playwright.config";
import { openStage } from "./stage-disclosures";
import { reviewPendingFields, reviewSourceChoices } from "./blocker-decisions";
import { showAllIssues } from "./attention";
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
  const stage = page.locator(".stage-disclosure").filter({ has: page.getByRole("heading", { name: title, exact: true }) });
  await expect(stage).toHaveCount(1);
  const control = stage.getByRole("button", { name: title, exact: true });
  if (await control.count()) {
    if (await control.getAttribute("aria-expanded") === "true") await control.click();
    await expect(control).toHaveAttribute("aria-expanded", "false");
    return;
  }
  await expect(stage.locator(":scope > h2")).toHaveText(title);
  for (const details of await stage.locator(":scope > details").all()) {
    if (await details.getAttribute("open") !== null) await details.locator(":scope > summary").click();
    await expect(details).not.toHaveAttribute("open", "");
  }
  await expect(stage.locator(":scope > div").first()).toBeVisible();
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
  await showAllIssues(page); const action = attention.getByRole("button", { name: /^Blocker:/ }).first();
  await action.focus(); await action.press("Enter"); await expect(page.locator("#identity-registration-number")).toBeFocused();
  const registry = page.getByRole("region", { name: "Registry verification", exact: true });
  await expect(registry.locator(":scope > div").first()).toBeVisible();
  await expect(registry.getByLabel("Singapore UEN", { exact: true })).toBeVisible();
  await expect(registry.getByLabel("Singapore UEN", { exact: true })).toBeEnabled();
  await expect(registry.getByRole("button", { name: "Verify UEN and resume", exact: true })).toBeVisible();
  await expect(registry.getByRole("button", { name: "Verify UEN and resume", exact: true })).toBeDisabled();
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
  await showAllIssues(page); await attention.getByRole("button", { name: /^Blocker:/ }).first().click();
  await expect(page.locator("input[data-review-field]:focus, input[data-discrepancy-id]:focus")).toHaveCount(1);
  expect(navigationMutations).toEqual([]); page.off("request", listener);
  await reviewPendingFields(page); await reviewSourceChoices(page);
  await expect(attention).not.toContainText("DOCUMENT SOURCE CONFLICT");
  await expect(attention).toContainText("No immediate blockers");
  const finalAction = attention.getByRole("button", { name: "Action: Review and send", exact: true });
  await showAllIssues(page); await expect(finalAction).toBeVisible(); await collapse(page, "Final review & send");
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
    expect(original.clm.target_search_checkpoint.status).toBe("COMPLETED");
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
    await showAllIssues(page); const action = attention.getByRole("button", { name: /Correct identity/ });
    const evidence = retainedEvidencePath("pr84-projection-attention"); await mkdir(evidence, { recursive: true });
    for (const width of [1280, 360]) {
      await page.setViewportSize({ width, height: 900 }); await collapse(page, "Registry verification");
      await action.focus(); await action.press("Enter");
      await expect(page.locator("#identity-registration-number")).toBeFocused();
      const registry = page.getByRole("region", { name: "Registry verification", exact: true });
      await expect(registry.locator(":scope > div").first()).toBeVisible();
      await expect(registry.getByLabel("Singapore UEN", { exact: true })).toBeVisible();
      await expect(registry.getByLabel("Singapore UEN", { exact: true })).toBeEnabled();
      await expect(registry.getByRole("button", { name: "Save details and recheck Search", exact: true })).toBeVisible();
      await expect(registry.getByRole("button", { name: "Save details and recheck Search", exact: true })).toBeDisabled();
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

test("PR84 mixed identity blockers preserve registry correction", async ({ page }) => {
  const { headers, violations } = await login(page);
  const cid = await create(page, headers, "99999999Z");
  const current = await (await page.request.get(`/api/clm/zero-touch/cases/${cid}`)).json();
  expect(current.case.initial_identity).toBeNull();
  expect(current.case.error.code).toBe("ACRA_ENTITY_NOT_FOUND");
  expect(current.interventions).toHaveLength(2); expect(current.active_exceptions).toHaveLength(1);
  expect(current.clm.target_search_checkpoint).toBeNull();
  const input = { legal_name: "MERLION CIRCULAR LABS PTE. LTD.", registration_number: "202400001A",
    country_of_incorporation: "SG", expected_automation_version: current.version,
    expected_clm_version: current.clm.version, expected_case_event_count: current.case.events.length };
  const rejected = await page.request.post(`/api/clm/zero-touch/cases/${cid}/identity-search-recheck`, { headers, data: input });
  expect(rejected.status()).toBe(409);
  expect((await rejected.json()).detail.code).toBe("ZERO_TOUCH_IDENTITY_RECHECK_NOT_ALLOWED");
  await page.setViewportSize({ width: 360, height: 900 }); await page.goto(`/cases/${cid}`);
  const requests: string[] = [];
  page.on("request", request => { if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method())) requests.push(new URL(request.url()).pathname); });
  const attention = page.getByRole("region", { name: "Attention required", exact: true });
  await expect(attention).toContainText("2 active blockers");
  await collapse(page, "Registry verification");
  // Two identity blockers exist; the accepted target is the exact "Correct identity" action, not "Correct identity and recheck".
  await showAllIssues(page); const action = attention.getByRole("button", { name: /Correct identity →$/ });
  await action.focus(); await action.press("Enter");
  await expect(page.locator("#identity-registration-number")).toBeFocused();
  expect(requests).toEqual([]);
  await expect(page.getByRole("button", { name: "Verify UEN and resume", exact: true })).toHaveCount(1);
  await page.getByLabel("Legal company name", { exact: true }).fill(input.legal_name);
  await page.getByLabel("Singapore UEN", { exact: true }).fill(input.registration_number);
  const corrected = page.waitForResponse(response => response.url().endsWith(`/cases/${cid}/registry-identity`) && response.request().method() === "POST");
  await page.getByRole("button", { name: "Verify UEN and resume", exact: true }).click();
  const response = await corrected; expect(response.status()).toBe(200);
  const saved = await response.json();
  expect(saved.case.case_id).toBe(cid); expect(saved.case.requested_uen).toBe(input.registration_number);
  expect(saved.case.initial_identity.legal_name).toBe(input.legal_name);
  expect(saved.case.identity_corrections).toHaveLength(1);
  expect(saved.case.target_dispatch_confirmation).toBeNull(); expect(saved.case.goldtier_result).toBeNull();
  expect(saved.target_operations.filter((item: { operation: string }) => item.operation !== "SEARCH")
    .every((item: { status: string }) => item.status === "NOT_ATTEMPTED")).toBe(true);
  expect(saved.clm.submission).toBeNull();
  await expect(attention).not.toContainText("Registry identity requires correction");
  await expect(attention).not.toContainText("Initial identity incomplete");
  expect(requests).toEqual([`/api/clm/zero-touch/cases/${cid}/registry-identity`]); expect(violations).toEqual([]);
});
