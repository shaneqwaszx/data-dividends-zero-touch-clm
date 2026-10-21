import { expect, test, type Page } from "@playwright/test";
import path from "node:path";
import fs from "node:fs/promises";
import { createBrowserNetworkPolicy, handleBrowserRoute } from "../playwright.config";
import type { ZeroTouchCaseSummary } from "../src/types";
import { openStage } from "./stage-disclosures";

const fixtures = [
  { label: "Alpha", mode: "database-alpha", name: "DEMO ALPHA CIRCULAR FYP TEST PTE. LTD.", uen: "209990101A", document: "demo-alpha-scanned.pdf", kyc: "Company - Private" },
  { label: "Partnership", mode: "database-partnership", name: "DEMO GAMMA TECHNOLOGIES FYP TEST PARTNERSHIP", uen: "209990103C", document: "demo-gamma-scanned.pdf", kyc: "Partnership - Unregulated" },
  { label: "Government", mode: "database-government", name: "DEMO GOVERNMENT FYP TEST AUTHORITY", uen: "209990105E", document: "demo-government-scanned.pdf", kyc: "Government" },
];

async function runFixture(page: Page, fixture: typeof fixtures[number]): Promise<void> {
    const violations: string[] = [];
    const policy = createBrowserNetworkPolicy({ frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!, backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false });
    await page.route("**/*", (route) => handleBrowserRoute(route, policy, violations));
    let classificationPuts = 0;
    page.on("request", (request) => { if (request.method() === "PUT" && request.url().endsWith("/target-classification")) classificationPuts += 1; });
    const counts = async () => { const response = await page.request.get("/api/__s3/sandbox-counts"); expect(response.status()).toBe(200); return response.json(); };
    await page.goto("/");
    await page.getByLabel("User ID").fill("maya-lim");
    await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await expect(page.getByRole("link", { name: "New onboarding", exact: true })).toBeVisible();
    expect((await counts()).fixture).toBe(fixture.mode);
    await page.getByRole("link", { name: "New onboarding", exact: true }).click();
    await page.getByLabel("Jurisdiction", { exact: true }).selectOption("SG");
    await page.getByLabel("Company Legal Name", { exact: true }).fill(fixture.name);
    await page.getByLabel("Registration ID / UEN").fill(fixture.uen);
    await page.locator("#home-document").setInputFiles(path.resolve("../backend/tests/fixtures/uat/zero-touch-database", fixture.document));
    await page.getByRole("button", { name: "Create onboarding", exact: true }).click();
    await expect(page).toHaveURL(/\/new-onboarding\/[0-9a-f-]{36}$/i);
    const caseId = page.url().split("/").at(-1)!;
    const read = async (): Promise<ZeroTouchCaseSummary> => (await page.request.get(`/api/clm/zero-touch/cases/${caseId}`)).json();
    if (fixture.label === "Government") {
      await expect.poll(async () => (await read()).target_classification.kyc_customer_type.selected_value).toBe("Government");
    } else await expect.poll(async () => (await read()).active_exceptions.map((item) => item.blocker_code)).toEqual(["TARGET_CONFIRMATION_REQUIRED"]);
    await page.getByRole("button", { name: "Open full case", exact: true }).click();
    await expect(page).toHaveURL(`/cases/${caseId}`);
    const summary = await read();
    expect(summary.clm.target_search_checkpoint?.disposition).toBe("NO_MATCH");
    if (fixture.label === "Government") {
      expect(summary.target_classification.kyc_customer_type.selected_value).toBe("Government");
      expect(summary.target_classification.client_segment.selected_value).toBe("DI - Government");
      expect(summary.target_classification.kyc_customer_type.selection?.source).toBe("DOCUMENT");
      expect(summary.target_classification.kyc_customer_type.selection?.document_evidence?.extraction_method).toBe("LOCAL_TESSERACT_OCR");
      expect(summary.current_stage).toBe("OWNERSHIP"); expect(summary.active_exceptions.length).toBeGreaterThan(0);
      expect(summary.target_submission?.state).toBe("NOT_SUBMITTED");
      const ownership = await (await page.request.get(`/api/onboarding/cases/${caseId}/ownership`)).json();
      expect(ownership.state).toBe("REVIEW_REQUIRED"); expect(ownership.candidates).toEqual([]);
      await openStage(page, "GoldTier Details & Status");
      await expect(page.getByRole("button", { name: "Save target classification", exact: true })).toHaveCount(0);
      await expect(page.getByText("Automatically classified from document", { exact: false }).first()).toBeVisible();
      await openStage(page, "Final review & send");
      await expect(page.getByRole("button", { name: "Confirm and send to GoldTier sandbox", exact: true })).toHaveCount(0);
      const before = await counts();
      expect(before.calls).toEqual({ SEARCH: 1, SHELL: 0, POLICY: 0, AMEND: 0, READBACK: 0 });
      expect(before.external_calls).toBe(0); expect(before.mutation_attempt_count).toBe(0);
      expect(classificationPuts).toBe(0); expect(violations).toEqual([]);
      return;
    }
    expect(summary.case.registry_evidence_binding?.disposition).toBe("CACHE_HIT");
    expect(summary.target_submission?.state).toBe("NOT_SUBMITTED");
    expect(summary.target_classification.kyc_customer_type.selected_value).toBe(fixture.kyc);
    expect(summary.target_classification.client_segment.selected_value).toBe("Corporate");
    for (const field of [summary.target_classification.kyc_customer_type, summary.target_classification.client_segment]) {
      expect(field.selection?.source).toBe("DOCUMENT");
      expect(field.selection?.document_evidence?.extraction_method).toBe("LOCAL_TESSERACT_OCR");
    }
    const nodes = Object.fromEntries(summary.processing_pipeline.map((node) => [node.node_id, node]));
    expect(summary.processing_pipeline).toHaveLength(12);
    expect(nodes.READINESS.status).toBe("COMPLETE"); expect(nodes.READINESS.blocker_code).toBeNull();
    expect(nodes.GOLDTIER_TARGET.status).toBe("COMPLETE"); expect(nodes.FINAL_REVIEW_SEND.status).toBe("REVIEW_REQUIRED");
    await openStage(page, "GoldTier Details & Status");
    await expect(page.getByRole("heading", { name: "GoldTier submission settings", exact: true })).toBeVisible();
    await expect(page.getByText("Automatically classified from document", { exact: false }).first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Save target classification", exact: true })).toHaveCount(0);
    expect(classificationPuts).toBe(0);
    const before = await counts();
    expect(before.persistence).toBe("MONGO"); expect(before.registry_calls).toEqual([]);
    expect(before.calls).toEqual({ SEARCH: 1, SHELL: 0, POLICY: 0, AMEND: 0, READBACK: 0 });
    expect(before.mutation_attempt_count).toBe(0); expect(before.external_calls).toBe(0);
    await openStage(page, "Final review & send");
    const confirmation = page.waitForResponse((response) => response.request().method() === "POST" && response.url().endsWith("/target-confirmation"));
    await page.getByRole("button", { name: "Confirm and send to GoldTier sandbox", exact: true }).click();
    expect((await confirmation).status()).toBe(200);
    await expect.poll(async () => (await read()).target_submission?.state).toBe("SUBMISSION_CONFIRMED");
    const final = await read(); expect(final.status).toBe("COMPLETED"); expect(final.target_submission?.goldtier_id).toBe("SYNTHETIC-GT-S3");
    await expect(page.getByText("Submission confirmed", { exact: true }).first()).toBeVisible();
    const after = await counts(); expect(after.calls).toEqual({ SEARCH: 2, SHELL: 1, POLICY: 1, AMEND: 0, READBACK: 1 });
    expect(after.registry_calls).toEqual([]); expect(after.external_calls).toBe(0);
    expect(violations).toEqual([]);
}

test("database classification Alpha actual scan auto-bound then explicit Send", { tag: "@s3-sandbox-database-alpha" }, async ({ page }) => runFixture(page, fixtures[0]));
test("database classification Partnership actual scan auto-bound then explicit Send", { tag: "@s3-sandbox-database-partnership" }, async ({ page }) => runFixture(page, fixtures[1]));
test("database classification Government actual scan auto-bound with unsupported ownership", { tag: "@s3-sandbox-database-government" }, async ({ page }) => runFixture(page, fixtures[2]));


test("database classification conflict prior USER then explicit current review", { tag: "@s3-sandbox-database-alpha" }, async ({ page }) => {
  const violations: string[] = [];
  const policy = createBrowserNetworkPolicy({
    frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!, backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!,
    allowDirectBackend: false,
  });
  await page.route("**/*", route => handleBrowserRoute(route, policy, violations));
  await page.goto("/");
  await page.getByLabel("User ID").fill("maya-lim");
  await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("link", { name: "New onboarding", exact: true })).toBeVisible();
  const fixture = fixtures[0];
  const sessionResponse = await page.request.get("/api/auth/me");
  expect(sessionResponse.status()).toBe(200);
  const session = await sessionResponse.json() as { csrf_token: string };
  const headers = { Origin: process.env.PLAYWRIGHT_BASE_URL!, "X-CSRF-Token": session.csrf_token };
  const created = await page.request.post("/api/clm/zero-touch/cases", {
    headers, data: { uen: fixture.uen, legal_name: fixture.name, country_of_incorporation: "SG" },
  });
  expect(created.status()).toBe(201);
  const caseId = (await created.json()).case.case_id as string;
  const caseUrl = "/api/clm/zero-touch/cases/" + caseId;
  const read = async (): Promise<ZeroTouchCaseSummary> => (await page.request.get(caseUrl)).json();
  await page.goto("/cases/" + caseId);
  await openStage(page, "GoldTier Details & Status");
  await page.getByLabel("KYC customer type", { exact: true }).selectOption("Company - Private");
  await page.getByLabel("Client segment", { exact: true }).selectOption("Corporate");
  const priorSave = page.waitForResponse(r => r.request().method() === "PUT" && r.url().endsWith("/target-classification"));
  await page.getByRole("button", { name: "Save target classification", exact: true }).click();
  expect((await priorSave).status()).toBe(200);
  const prior = (await read()).target_classification.kyc_customer_type.selection!;
  const scan = await page.request.post(caseUrl + "/intake/documents", {
    headers: { ...headers, "Content-Type": "application/pdf", "X-Document-Name": "fictional-alpha-scan.pdf" },
    data: await fs.readFile(path.resolve("../backend/tests/fixtures/uat/zero-touch-database/demo-alpha-scanned.pdf")),
  });
  expect(scan.status()).toBe(201);
  const contradiction = Buffer.from([
    "FICTIONAL FYP TEST DATA", "Legal Name: " + fixture.name, "UEN: " + fixture.uen,
    "Registered Address: 11 DEMO ALPHA WAY, 000101, SG", "Country: SG",
    "KYC Customer Type: Partnership - Unregulated", "Client Segment: Corporate",
  ].join("\n"));
  const conflicting = await page.request.post(caseUrl + "/intake/documents", {
    headers: { ...headers, "Content-Type": "text/plain", "X-Document-Name": "fictional-conflicting-profile.txt" },
    data: contradiction,
  });
  expect(conflicting.status()).toBe(201);
  const completed = await page.request.post(caseUrl + "/intake/complete", {
    headers, data: { expected_document_count: 2 },
  });
  expect(completed.status()).toBe(200);
  await page.reload();
  await openStage(page, "GoldTier Details & Status");
  await expect(page.getByRole("heading", { name: "Target classification — conflicting evidence", exact: true })).toBeVisible();
  await expect(page.getByText("Company - Private; Partnership - Unregulated", { exact: false })).toBeVisible();
  await openStage(page, "Historical / resolved issues");
  const packageNode = page.locator(".processing-pipeline__node").filter({
    has: page.locator(".processing-pipeline__node-title").filter({ hasText: /^GoldTier Details & Status$/ }),
  });
  await expect(packageNode).not.toContainText("Prepared target plan retained");
  const blocked = await read();
  expect(blocked.target_classification.state).toBe("CONFLICT");
  expect(blocked.target_classification.current).toBe(false);
  const nodes = Object.fromEntries(blocked.processing_pipeline.map(n => [n.node_id, n]));
  expect(nodes.READINESS.status).toBe("REVIEW_REQUIRED");
  expect(nodes.GOLDTIER_TARGET.safe_result).not.toBe("Prepared target plan retained");
  expect(["BLOCKED", "NOT_REACHED"]).toContain(nodes.FINAL_REVIEW_SEND.status);
  await openStage(page, "Final review & send");
  await expect(page.getByRole("button", { name: "Confirm and send to GoldTier sandbox", exact: true })).toHaveCount(0);
  await openStage(page, "GoldTier Details & Status");
  const currentSave = page.waitForResponse(r => r.request().method() === "PUT" && r.url().endsWith("/target-classification"));
  await page.getByRole("button", { name: "Save target classification", exact: true }).click();
  const response = await currentSave;
  expect(response.status()).toBe(200);
  expect(response.request().postDataJSON().expected_classification_evidence_fingerprint)
    .toBe(blocked.target_classification.evidence_fingerprint);
  await expect.poll(async () => (await read()).target_classification.state).toBe("CURRENT");
  await openStage(page, "Historical / resolved issues");
  await expect(packageNode).toContainText("Prepared target plan retained");
  const reviewed = await read();
  expect(reviewed.target_classification.kyc_customer_type.selection?.evidence_fingerprint)
    .toBe(reviewed.target_classification.evidence_fingerprint);
  expect(reviewed.target_classification.kyc_customer_type.selection?.classified_at).not.toBe(prior.classified_at);
  expect(reviewed.target_classification.kyc_customer_type.selection?.actor_id).toBe("maya-lim");
  const ready = Object.fromEntries(reviewed.processing_pipeline.map(n => [n.node_id, n]));
  expect(ready.READINESS.status).toBe("COMPLETE");
  expect(ready.GOLDTIER_TARGET.status).toBe("COMPLETE");
  expect(ready.FINAL_REVIEW_SEND.status).toBe("REVIEW_REQUIRED");
  await openStage(page, "Final review & send");
  await expect(page.getByRole("button", { name: "Confirm and send to GoldTier sandbox", exact: true })).toBeVisible();
  const counts = await (await page.request.get("/api/__s3/sandbox-counts")).json();
  expect(counts.calls).toEqual({ SEARCH: 1, SHELL: 0, POLICY: 0, AMEND: 0, READBACK: 0 });
  expect(counts.mutation_attempt_count).toBe(0); expect(counts.external_calls).toBe(0);
  expect(counts.registry_calls).toEqual([]); expect(violations).toEqual([]);
});
