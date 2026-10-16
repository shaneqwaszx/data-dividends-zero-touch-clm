import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";
import { createBrowserNetworkPolicy, handleBrowserRoute, retainedEvidencePath } from "../playwright.config";
import { openStage, openStageSupport } from "./stage-disclosures";

test.use({ timezoneId: "America/Los_Angeles" });

const company = { name: "MERLION CIRCULAR LABS PTE. LTD.", uen: "202400001A" };
const fixture = path.resolve("../backend/tests/fixtures/uat/clean-company-profile.pdf");

async function read(page: Page, caseId: string) {
  const response = await page.request.get(`/api/clm/zero-touch/cases/${caseId}`);
  expect(response.status()).toBe(200);
  return response.json();
}
async function ownership(page: Page, caseId: string) {
  const response = await page.request.get(`/api/onboarding/cases/${caseId}/ownership`);
  expect(response.status()).toBe(200);
  return response.json();
}
function checkpoint(summary: any, analysis: any) {
  return { caseId: summary.case.case_id, actor: "maya-lim", automationId: summary.automation_id,
    automationVersion: summary.version, status: summary.status, stage: summary.current_stage,
    completedStages: summary.completed_stages, caseEventCount: summary.case.events.length,
    analysisId: analysis.analysis_id, ownershipVersion: analysis.version,
    documentBindings: analysis.document_bindings, classification: summary.target_classification,
    policyIdentity: summary.case.policy_snapshot?.catalogue_version, clmVersion: summary.clm.version,
    readiness: summary.clm.readiness, preparationId: summary.clm.related_party_preparation?.analysis_reference,
    submissionId: summary.clm.submission?.submission_id ?? null, targetSubmission: summary.target_submission,
    blockers: summary.active_exceptions.map((item: any) => ({ id: item.exception_id, stage: item.stage, type: item.exception_type, code: item.blocker_code })),
    targetOperations: summary.target_operations, targetConfirmed: summary.case.target_dispatch_confirmation !== null };
}
async function create(page: Page, fresh = false) {
  await page.getByRole("link", { name: "New onboarding", exact: true }).click();
  if (fresh) await page.getByRole("button", { name: "Start a new case", exact: true }).click();
  await page.getByLabel("Jurisdiction", { exact: true }).selectOption("SG");
  await page.getByLabel("Company Legal Name", { exact: true }).fill(company.name);
  await page.getByLabel("Registration ID / UEN").fill(company.uen);
  await page.locator("#home-document").setInputFiles(fixture);
  const intake = page.waitForResponse(r => r.request().method() === "POST" && r.url().endsWith("/intake/complete"));
  await page.getByRole("button", { name: "Create onboarding", exact: true }).click();
  expect((await intake).status()).toBe(200);
  expect((await intake).request().postDataJSON()).toEqual({ expected_document_count: 1 });
  const caseId = page.url().split("/").at(-1)!;
  await page.getByRole("button", { name: "Open full case", exact: true }).click();
  await openStage(page, "Submission readiness");
  await page.getByLabel("KYC customer type", { exact: true }).selectOption("Company - Private");
  await page.getByLabel("Client segment", { exact: true }).selectOption("Corporate");
  const classified = page.waitForResponse(r => r.request().method() === "PUT" && r.url().endsWith("/target-classification"));
  await page.getByRole("button", { name: "Save target classification", exact: true }).click();
  expect((await classified).status()).toBe(200);
  await expect(page.getByRole("button", { name: "Confirm and send to Mock GoldTier", exact: true })).toBeEnabled();
  return caseId;
}
async function balancedCorrection(page: Page, reuse: boolean) {
    const start = Date.now();
    const violations: string[] = [];
    const policy = createBrowserNetworkPolicy({ frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!, backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false });
    await page.route("**/*", route => handleBrowserRoute(route, policy, violations));
    await page.goto("/");
    await page.getByLabel("User ID").fill("maya-lim");
    await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    let caseId = await create(page);
    if (reuse) {
      // Separate synthetic setup case proves the existing provider identity; the primary case is never sent.
      const confirmation = page.waitForResponse(r => r.request().method() === "POST" && r.url().endsWith("/target-confirmation"));
      await page.getByRole("button", { name: "Confirm and send to Mock GoldTier", exact: true }).click();
      expect((await confirmation).status()).toBe(200);
      await expect.poll(async () => (await read(page, caseId)).status).toBe("COMPLETED");
      caseId = await create(page, true);
    }
    const before = await read(page, caseId);
    const initial = await ownership(page, caseId);
    if (reuse) expect(before.clm.target_search_checkpoint.disposition).toBe("EXACT_MATCH");
    expect(initial.relationships.map((edge: any) => Number(edge.ownership_percent))).toEqual([60, 40]);
    const evidence = retainedEvidencePath("am18"); await mkdir(evidence, { recursive: true });
    await writeFile(path.join(evidence, "before.json"), JSON.stringify(checkpoint(before, initial), null, 2));
    const targetPosts: string[] = [];
    page.on("request", request => { if (request.method() === "POST" && /target-confirmation|\/submit|\/resume/.test(request.url())) targetPosts.push(new URL(request.url()).pathname); });
    await page.getByRole("button", { name: "Edit ownership", exact: true }).click();
    const form = page.locator(".manual-ownership");
    await form.getByLabel("Economic interest %", { exact: true }).nth(0).fill("55");
    await form.getByLabel("Economic interest %", { exact: true }).nth(1).fill("45");
    await form.getByLabel("As-of date").fill("2026-10-04");
    const correction = page.waitForResponse(r => r.request().method() === "POST" && r.url().endsWith("/manual-ownership-evidence"));
    await form.getByRole("button", { name: "Submit manual ownership evidence", exact: true }).click();
    const corrected = await correction;
    await writeFile(path.join(evidence, "response.json"), JSON.stringify({ status: corrected.status(), publicError: corrected.ok() ? null : await corrected.json() }, null, 2));
    expect(corrected.status()).toBe(200);
    await expect(page.getByRole("button", { name: "Confirm and send to Mock GoldTier", exact: true })).toBeEnabled();
    const after = await read(page, caseId);
    const revised = await ownership(page, caseId);
    expect(revised.analysis_id).not.toBe(initial.analysis_id);
    expect(revised.relationships.map((edge: any) => Number(edge.ownership_percent))).toEqual([55, 45]);
    expect(revised.relationships.map((edge: any) => edge.relationship_id)).toEqual(initial.relationships.map((edge: any) => edge.relationship_id));
    expect(after.target_classification.current).not.toBe(false);
    expect(after.target_classification.kyc_customer_type.selected_value).toBe("Company - Private");
    expect(after.target_classification.client_segment.selected_value).toBe("Corporate");
    expect(after.clm.version).toBeGreaterThan(before.clm.version);
    expect(after.case.target_dispatch_confirmation).toBeNull();
    expect(after.case.goldtier_result).toBeNull();
    expect(after.clm.submission).toBeNull();
    expect(after.target_submission.state).toBe("NOT_SUBMITTED");
    expect(after.target_submission.attempted_operations).toEqual([]);
    expect(after.target_operations.filter((operation: any) => operation.operation !== "SEARCH").every((operation: any) => ["NOT_ATTEMPTED", "SKIPPED"].includes(operation.status))).toBe(true);
    expect(after.active_exceptions.map((item: any) => item.blocker_code)).toEqual(["TARGET_CONFIRMATION_REQUIRED"]);
    await openStage(page, "Final review & send");
    await page.locator(".review-and-send").screenshot({ path: path.join(evidence, "final-review.png") });
    await page.reload();
    await expect(page.getByRole("button", { name: "Confirm and send to Mock GoldTier", exact: true })).toBeEnabled();
    const reloaded = await read(page, caseId);
    expect(reloaded.version).toBe(after.version);
    expect(reloaded.case.goldtier_result).toBeNull();
    expect(targetPosts).toEqual([]); expect(violations).toEqual([]);
    await writeFile(path.join(evidence, "after.json"), JSON.stringify({ ...checkpoint(after, revised), elapsedMs: Date.now() - start, targetPosts, primaryCase: "NOT_SUBMITTED", externalCalls: 0 }, null, 2));
}

test("AM18 new customer classification then balanced correction retains reachable final review", async ({ page }) => {
  await balancedCorrection(page, false);
});

test("AM18 existing-customer reuse classification then balanced correction retains reachable final review", { tag: "@slice-f-target-reuse" }, async ({ page }) => {
  await balancedCorrection(page, true);
});

test("AM14 Singapore midnight new declaration default is accepted by real backend and historical review dates survive", async ({ page }) => {
  const violations: string[] = [];
  const policy = createBrowserNetworkPolicy({ frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!, backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false });
  await page.route("**/*", route => handleBrowserRoute(route, policy, violations));
  await page.clock.install({ time: new Date("2026-10-13T16:00:00Z") });
  await page.goto("/");
  await page.getByLabel("User ID").fill("maya-lim"); await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  const caseId = await create(page);
  await page.getByRole("button", { name: "Edit ownership", exact: true }).click();
  const form = page.locator(".manual-ownership");
  await expect(form.getByLabel("As-of date")).toHaveValue("2026-10-14");
  await form.getByLabel("Economic interest %", { exact: true }).nth(0).fill("55");
  await form.getByLabel("Economic interest %", { exact: true }).nth(1).fill("45");
  const corrected = page.waitForResponse(r => r.request().method() === "POST" && r.url().endsWith("/manual-ownership-evidence"));
  await form.getByRole("button", { name: "Submit manual ownership evidence", exact: true }).click();
  expect((await corrected).status()).toBe(200);
  expect((await ownership(page, caseId)).manual_review_receipt).toMatchObject({ as_of_date: "2026-10-14", rationale: null });
  await expect(page.getByRole("button", { name: "Confirm and send to Mock GoldTier", exact: true })).toBeEnabled();
  await page.reload(); await openStage(page, "Ownership & UBO");
  await expect(form.getByLabel("As-of date")).toHaveValue("2026-10-14");
  await form.getByLabel("As-of date").fill("2026-10-04");
  await form.getByLabel("Ownership source decision").selectOption("CURRENT_EVIDENCE");
  await expect(form.getByLabel("As-of date")).toHaveValue("2026-10-14");
  await expect(form.getByLabel("As-of date")).toHaveAttribute("readonly", "");
  await form.getByLabel("Ownership source decision").selectOption("USER_SUPPLIED_DECLARATION");
  await expect(form.getByLabel("As-of date")).toHaveValue("2026-10-04");
  const current = await read(page, caseId);
  expect(current.target_submission.state).toBe("NOT_SUBMITTED"); expect(current.target_submission.attempted_operations).toEqual([]);
  expect(violations).toEqual([]);
  const evidence = retainedEvidencePath("am14"); await mkdir(evidence, { recursive: true });
  await form.screenshot({ path: path.join(evidence, "date-draft.png") });
  await writeFile(path.join(evidence, "receipt.json"), JSON.stringify({ caseId, browserTimezone: "America/Los_Angeles", browserInstant: "2026-10-13T16:00:00Z", retainedDate: "2026-10-14", editedDraft: "2026-10-04", note: null, primaryCase: "NOT_SUBMITTED" }, null, 2));
});

test("AM05 AM09 AM10 real registry audit and responsive bulk document drafts require explicit Confirm", async ({ page }) => {
  const violations: string[] = [];
  const policy = createBrowserNetworkPolicy({ frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!, backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false });
  await page.route("**/*", route => handleBrowserRoute(route, policy, violations));
  await page.goto("/");
  await page.getByLabel("User ID").fill("maya-lim"); await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("link", { name: "New onboarding", exact: true }).click();
  await page.getByLabel("Jurisdiction", { exact: true }).selectOption("SG");
  await page.getByLabel("Company Legal Name", { exact: true }).fill(company.name);
  await page.getByLabel("Registration ID / UEN").fill(company.uen);
  const synthetic = [`Legal Name: OTHER SYNTHETIC COMPANY ${"LONG VALUE ".repeat(8)}`, "UEN: 202400002B", "Country: SG"].join("\n");
  await page.locator("#home-document").setInputFiles({ name: "synthetic-review-with-missing-address.txt", mimeType: "text/plain", buffer: Buffer.from(synthetic) });
  const intake = page.waitForResponse(r => r.request().method() === "POST" && r.url().endsWith("/intake/complete"));
  await page.getByRole("button", { name: "Create onboarding", exact: true }).click(); expect((await intake).status()).toBe(200);
  const caseId = page.url().split("/").at(-1)!;
  await page.getByRole("button", { name: "Open full case", exact: true }).click();
  const before = await read(page, caseId);
  const documentsBeforeResponse = await page.request.get(`/api/onboarding/cases/${caseId}/documents`);
  expect(documentsBeforeResponse.status()).toBe(200);
  const documentsBefore = await documentsBeforeResponse.json();
  await openStage(page, "Registry verification");
  await openStageSupport(page, "Registry verification", "More");
  const provenance = page.locator('[aria-labelledby="registry-provenance-more-heading"]');
  await expect(provenance).toBeVisible();
  await expect(provenance).toContainText("SGT (UTC+08:00)");
  await openStageSupport(page, "Registry verification", "Technical");
  const audit = page.locator('[aria-labelledby="registry-provenance-technical-heading"]');
  const original = audit.getByText("Acquisition retrieved at — original ISO UTC", { exact: true }).locator("..").locator("dd");
  await expect(original).toBeVisible();
  await expect(original).toHaveText(before.case.registry_acquisition.retrieved_at);
  await openStage(page, "Document verification");
  const review = page.locator("#case-blocker-review");
  const controls = review.locator("select[data-review-field]"); await expect(controls).toHaveCount(3);
  const name = review.locator('select[data-review-field="legal_name"]'); await name.selectOption("CORRECTED");
  await review.getByLabel("Correction for legal name", { exact: true }).fill(company.name);
  await review.getByLabel("Optional note for legal name", { exact: true }).fill("Reviewed synthetic field deliberately.");
  const eligible = await controls.evaluateAll(nodes => nodes.filter(node => !(node as HTMLSelectElement).value && Array.from((node as HTMLSelectElement).options).some(option => option.value === "ACCEPTED")).map(node => node.getAttribute("data-review-field")));
  const businessWrites: string[] = [];
  page.on("request", request => { if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method())) businessWrites.push(new URL(request.url()).pathname); });
  await review.getByRole("button", { name: "Accept all eligible undecided suggestions", exact: true }).click();
  expect(await name.inputValue()).toBe("CORRECTED");
  for (const key of eligible) await expect(review.locator(`select[data-review-field="${key}"]`)).toHaveValue("ACCEPTED");
  await expect(review.locator('select[data-review-field="registered_address"]')).toHaveValue("");
  await expect(review.getByRole("button", { name: "Confirm decisions & continue onboarding", exact: true })).toBeDisabled();
  const evidence = retainedEvidencePath("am-review"); await mkdir(evidence, { recursive: true });
  for (const width of [1440, 900, 360]) {
    await page.setViewportSize({ width, height: 1000 });
    const columns = await review.locator(".blocker-review__cards").evaluate(node => getComputedStyle(node).gridTemplateColumns.split(" ").length);
    expect(columns).toBe(width > 900 ? 2 : 1);
    expect(await page.evaluate(() => document.body.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
    await review.screenshot({ path: path.join(evidence, `document-cards-${width}.png`) });
  }
  expect(businessWrites).toEqual([]);
  const unchanged = await read(page, caseId); expect(unchanged.version).toBe(before.version);
  await review.getByRole("button", { name: "Reject all undecided suggestions", exact: true }).click();
  await expect(review.locator('select[data-review-field="registered_address"]')).toHaveValue("REJECTED");
  await expect(review.getByLabel("Optional note for legal name", { exact: true })).toHaveValue("Reviewed synthetic field deliberately.");
  expect(businessWrites).toEqual([]);
  const confirmed = page.waitForResponse(r => r.request().method() === "POST" && r.url().endsWith("/review-decisions"));
  await review.getByRole("button", { name: "Confirm decisions & continue onboarding", exact: true }).click();
  const response = await confirmed; expect(response.status()).toBe(200);
  const payload = response.request().postDataJSON();
  expect(payload.expected_automation_version).toBe(before.version);
  expect(payload.expected_case_event_count).toBe(before.case.events.length);
  for (const request of payload.documents) {
    const retained = documentsBefore.find((doc: any) => doc.document_id === request.document_id);
    expect(retained).toBeDefined();
    expect(request.source_fingerprint).toBe(retained.review_source_fingerprint);
    expect(request.expected_event_count).toBe(retained.events.length);
  }
  const decisions = payload.documents[0].decisions;
  expect(decisions.find((item: any) => item.field_key === "legal_name")).toEqual({ field_key: "legal_name", decision: "CORRECTED", corrected_value: company.name, note: "Reviewed synthetic field deliberately." });
  expect(decisions.find((item: any) => item.field_key === "registered_address").decision).toBe("REJECTED");
  expect(decisions.filter((item: any) => item.decision === "ACCEPTED").map((item: any) => item.field_key).sort()).toEqual(eligible.sort());
  const after = await read(page, caseId);
  expect(after.target_submission.state).toBe("NOT_SUBMITTED"); expect(after.target_submission.attempted_operations).toEqual([]);
  expect(after.active_exceptions.length).toBeGreaterThan(0);
  await expect.poll(async () => (await read(page, caseId)).active_exceptions.length).toBeGreaterThan(0);
  await page.reload(); await openStage(page, "Document verification");
  await expect(page.getByRole("button", { name: "Accept all eligible undecided suggestions", exact: true })).toHaveCount(0);
  expect((await read(page, caseId)).target_submission.attempted_operations).toEqual([]);
  expect(violations).toEqual([]);
  await writeFile(path.join(evidence, "receipt.json"), JSON.stringify({ caseId, widths: [1440, 900, 360], eligible, payload, status: after.status, blockers: after.active_exceptions.map((item: any) => item.blocker_code), businessWrites }, null, 2));
});
