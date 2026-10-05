import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test, type Page } from "@playwright/test";
import { openStage } from "./stage-disclosures";
import { createBrowserNetworkPolicy, handleBrowserRoute } from "../playwright.config";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const fixtures = path.join(root, "apps/backend/tests/fixtures/uat");
const operations = ["ENTITY_PROFILE", "OFFICERS", "OWNERSHIP_PARTIES", "RELATIONSHIPS"];
const garden = { name: "GARDEN BUSINESS", uen: "11111999A", pdf: "garden-partnership-reviewed-client.pdf" };
const second = { name: "MULTIPLE OWNER DEMO PTE. LTD.", uen: "202400008H", pdf: "multiple-owner-demo-client.pdf" };
const merlion = { name: "MERLION CIRCULAR LABS PTE. LTD.", uen: "202400001A", pdf: "clean-company-profile.pdf" };
let violations: string[];

test.beforeEach(async ({ page }) => {
  violations = [];
  const policy = createBrowserNetworkPolicy({
    frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!,
    backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false,
  });
  await page.route("**/*", (route) => handleBrowserRoute(route, policy, violations));
  await page.goto("/");
  await page.getByLabel("User ID").fill("maya-lim");
  await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
  await page.getByRole("button", { name: "Sign in" }).click();
});
test.afterEach(() => expect(violations).toEqual([]));

async function summary(page: Page, caseId: string) {
  const response = await page.request.get("/api/clm/zero-touch/cases/" + caseId);
  expect(response.status()).toBe(200);
  return response.json();
}
async function counts(page: Page) {
  const response = await page.request.get("/api/__slice_b/registry-counts");
  expect(response.status()).toBe(200);
  const result = await response.json();
  expect(result.external_calls).toBe(0);
  return result.calls;
}
async function create(page: Page, company: typeof garden, fresh = false) {
  await page.getByRole("link", { name: "New onboarding", exact: true }).click();
  if (fresh) {
    await page.getByRole("button", { name: "Start a new case", exact: true }).click();
    await expect(page).toHaveURL(/\/new-onboarding$/);
  }
  await page.getByLabel("Jurisdiction", { exact: true }).selectOption("SG");
  await page.getByLabel("Company Legal Name", { exact: true }).fill(company.name);
  await page.getByLabel("Registration ID / UEN").fill(company.uen);
  await page.locator("#home-document").setInputFiles(path.join(fixtures, company.pdf));
  // Normal authenticated classification input before intake. No routing/state override.
  await page.route("**/api/clm/zero-touch/cases", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    const response = await route.fetch();
    expect(response.status()).toBe(201);
    const created = await response.json();
    const bound = await page.request.put("/api/clm/zero-touch/cases/" + created.case.case_id + "/target-classification", {
      headers: { "X-CSRF-Token": route.request().headers()["x-csrf-token"], "Origin": process.env.PLAYWRIGHT_BASE_URL! },
      data: { kyc_customer_type: "Company - Private", client_segment: "Corporate",
        expected_automation_version: created.version, expected_case_event_count: created.case.events.length },
    });
    expect(bound.status()).toBe(200);
    await route.fulfill({ response });
  });
  await page.getByRole("button", { name: "Create onboarding" }).click();
  await expect(page).toHaveURL(/\/new-onboarding\/[0-9a-f-]{36}$/i);
  await page.unroute("**/api/clm/zero-touch/cases");
  const caseId = page.url().split("/").at(-1)!;
  await expect.poll(async () => (await summary(page, caseId)).status).toBe("WAITING_FOR_REVIEW");
  await page.getByRole("button", { name: "Open full case" }).click();
  await expect(page).toHaveURL("/cases/" + caseId);
  await expect(page.locator(".document-card:not(.document-card--history)")).toHaveCount(1);
  await expect(page.locator(".document-field .tag", { hasText: "AUTO CONFIRMED" })).toHaveCount(4);
  return caseId;
}
async function complete(page: Page, caseId: string) {
  await page.getByRole("button", { name: "Confirm and send to Mock GoldTier" }).click();
  await expect.poll(async () => (await summary(page, caseId)).status).toBe("COMPLETED");
  await openStage(page, "GoldTier submission package");
  await expect(page.getByText("Completed POC workflow", { exact: true })).toBeVisible();
  const done = await summary(page, caseId);
  expect(done.active_exceptions).toEqual([]);
  expect(done.case.goldtier_result.readback_status).toBe("VERIFIED");
  expect(done.case.goldtier_result.readback_party_id).toBe(done.case.goldtier_result.party_id);
  expect(done.target_operations.find((item: any) => item.operation === "READBACK").status).toBe("SUCCESS");
  const target = done.processing_pipeline.find((node: any) => node.node_id === "FINAL_REVIEW_SEND");
  expect(target.children.find((node: any) => node.node_id === "GOLDTIER_READBACK").status).toBe("COMPLETE");

}

test("Slice B Garden partnership automatically uses labelled local ownership", { tag: "@slice-b-garden-partnership" }, async ({ page }) => {
  const caseId = await create(page, garden);
  await openStage(page, "Registry verification");
  await expect(page.getByText(/ACRA Marketplace protocol · synthetic offline test evidence \| GoldTier/) ).toBeVisible();
  await expect(page.getByText(/not an authoritative partnership-ownership source/)).toBeVisible();
  await expect(page.getByRole("heading", { name: "Registry officers and roles", exact: true })).toBeVisible();
  const initial = await summary(page, caseId);
  expect(initial.case.entity.party_type).toBe("PARTNERSHIP");
  expect(initial.case.registry_acquisition.status).toBe("PARTIAL");
  expect(initial.case.registry_evidence_binding).toBeNull();
  expect(initial.case.registry_acquisition.operation_results.map((item: any) => item.status))
    .toEqual(["COMPLETE", "COMPLETE", "UNSUPPORTED", "UNSUPPORTED"]);
  expect(await counts(page)).toEqual(["TOKEN", "ENTITY_PROFILE", "ENTITY_PROFILE"]);
  const ownership = await (await page.request.get(`/api/onboarding/cases/${caseId}/ownership`)).json();
  expect(ownership.state).toBe("ANALYZED");
  expect(ownership.source_classification).toBe("OFFICIAL_MOCK_PLUS_LOCAL_SUPPLEMENT");
  expect(ownership.manual_review_receipt).toBeNull();
  expect(ownership.candidates.find((item: any) => item.party.display_name === "ABCD123").aggregated_ownership_percent).toMatch(/^51\.136363750*$/);
  const current = await summary(page, caseId);
  expect(current.active_exceptions.map((item: any) => item.blocker_code)).toEqual(["TARGET_CONFIRMATION_REQUIRED"]);
  await complete(page, caseId);
  await page.reload();
  await expect.poll(async () => (await summary(page, caseId)).active_exceptions).toEqual([]);
  expect((await summary(page, caseId)).case.registry_acquisition).toEqual(initial.case.registry_acquisition);
  expect(await counts(page)).toEqual(["TOKEN", "ENTITY_PROFILE", "ENTITY_PROFILE"]);
});

test("Slice B second synthetic company completes", { tag: "@slice-b-synthetic-cache" }, async ({ page }) => {
  const caseId = await create(page, second);
  await openStage(page, "Registry verification");
  await expect(page.getByText(/ACRA Local Mock \| GoldTier/)).toBeVisible();
  expect(await counts(page)).toEqual(operations.map((operation) => [operation, second.uen]));
  expect((await summary(page, caseId)).case.registry_acquisition.status).toBe("COMPLETE");
  await complete(page, caseId);
  expect(await counts(page)).toEqual(operations.map((operation) => [operation, second.uen]));
});

test("Slice B Merlion fresh cache makes zero new ACRA calls", { tag: "@slice-b-synthetic-cache" }, async ({ page }) => {
  const warmId = await create(page, merlion); // Keep target unsubmitted.
  const before = await counts(page);
  expect(before).toEqual(operations.map((operation) => [operation, merlion.uen]));
  const warm = await summary(page, warmId);
  const caseId = await create(page, merlion, true);
  expect(caseId).not.toBe(warmId);
  expect(await counts(page)).toEqual(before);
  await openStage(page, "Registry verification");
  await expect(page.getByText("Reused fresh registry evidence — no ACRA request required.", { exact: true }).first()).toBeVisible();
  const bindingView = page.getByLabel("Case evidence binding", { exact: true });
  const hit = await summary(page, caseId);
  expect(hit.case.registry_evidence_binding.disposition).toBe("CACHE_HIT");
  expect(hit.case.registry_acquisition).toEqual(warm.case.registry_acquisition);
  for (const value of Object.values(hit.case.registry_evidence_binding)) {
    await expect(bindingView).toContainText(String(value));
  }
  await complete(page, caseId);
  expect(await counts(page)).toEqual(before);
});

test("Slice F same-process verified target reuse retains readback", { tag: "@slice-f-target-reuse" }, async ({ page }) => {
  const firstId = await create(page, merlion);
  await complete(page, firstId);
  const first = await summary(page, firstId);
  const before = await counts(page);
  const nextId = await create(page, merlion, true);
  expect(nextId).not.toBe(firstId);
  const reused = await summary(page, nextId);
  expect(reused.clm.target_search_checkpoint.disposition).toBe("EXACT_MATCH");
  const search = reused.processing_pipeline.find((node: any) => node.node_id === "GOLDTIER_SEARCH");
  expect(search.children.find((node: any) => node.node_id === "EXISTING_TARGET_STATE").status).toBe("COMPLETE");
  expect(await counts(page)).toEqual(before);
  await complete(page, nextId);
  const done = await summary(page, nextId);
  expect(done.case.goldtier_result.party_id).toBe(first.case.goldtier_result.party_id);
  expect(Object.fromEntries(done.target_operations.map((item: any) => [item.operation, item.status])))
    .toEqual({ SEARCH: "MATCH_FOUND", SHELL: "SKIPPED", POLICY: "SKIPPED", AMEND: "SUCCESS", READBACK: "SUCCESS" });
  await page.reload();
  await expect.poll(async () => (await summary(page, nextId)).case.goldtier_result.readback_status).toBe("VERIFIED");
  expect((await summary(page, nextId)).historical_exceptions.some((item: any) => item.blocker_code === "TARGET_CONFIRMATION_REQUIRED")).toBe(true);
  expect(await counts(page)).toEqual(before);
});

test("Slice F ambiguous target match pauses without mutation", { tag: "@slice-f-target-ambiguity" }, async ({ page }) => {
  await page.getByRole("link", { name: "New onboarding", exact: true }).click();
  await page.getByLabel("Jurisdiction", { exact: true }).selectOption("SG");
  await page.getByLabel("Company Legal Name", { exact: true }).fill(merlion.name);
  await page.getByLabel("Registration ID / UEN").fill(merlion.uen);
  await page.locator("#home-document").setInputFiles(path.join(fixtures, merlion.pdf));
  await page.getByRole("button", { name: "Create onboarding", exact: true }).click();
  await expect(page).toHaveURL(/\/new-onboarding\/[0-9a-f-]{36}$/i);
  const caseId = page.url().split("/").at(-1)!;
  await expect.poll(async () => (await summary(page, caseId)).status).toBe("WAITING_FOR_REVIEW");
  await page.getByRole("button", { name: "Open full case", exact: true }).click();
  const paused = await summary(page, caseId);
  expect(paused.clm.target_search_checkpoint.provider_outcome).toBe("MULTIPLE_MATCHES");
  expect(paused.clm.target_search_checkpoint.candidate_count).toBe(2);
  expect(paused.active_exceptions.map((item: any) => item.exception_type)).toContain("ENTITY_RESOLUTION_REVIEW_REQUIRED");
  expect(Object.fromEntries(paused.target_operations.map((item: any) => [item.operation, item.status])))
    .toEqual({ SEARCH: "REVIEW_REQUIRED", SHELL: "NOT_ATTEMPTED", POLICY: "NOT_ATTEMPTED", AMEND: "NOT_ATTEMPTED" });
  await expect(page.getByRole("button", { name: "Confirm and send to Mock GoldTier" })).toHaveCount(0);
  expect(await counts(page)).toEqual(operations.map((operation) => [operation, merlion.uen]));
  const meta = await (await page.request.get("/api/__slice_f/target-metadata")).json();
  expect(meta).toEqual({ fixture: "synthetic-target-ambiguity", classification: "SYNTHETIC_MOCK", setup_target_mutations: 4, external_calls: 0 });
  await page.reload();
  expect((await summary(page, caseId)).clm.target_search_checkpoint.candidate_count).toBe(2);
});
