import { mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test, type Page } from "@playwright/test";
import { openStage } from "./stage-disclosures";
import { createBrowserNetworkPolicy, handleBrowserRoute, retainedEvidencePath } from "../playwright.config";

// Isolated offline protocol composition (D-077): the real official Marketplace Mock
// connector runs against an allowlisted in-process transport. Never an ACRA observation.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const pdf = path.join(root, "apps/backend/tests/fixtures/uat/five-layer-marketplace-hybrid-client.pdf");
const company = { name: "OPQ PTE. LTD.", uen: "201511222D" };
const issuers = ["200811111M", "201688888A", "200811111K", "199801111H", "111111111K"];
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
  expect(result.classification).toBe("AUTOMATED_OFFLINE_SIMULATION");
  expect(result.external_calls).toBe(0);
  return result as { token_requests: number; gets: Array<{ operation: string; uen: string; count: number }> };
}
async function onboard(page: Page, fresh = false) {
  const newOnboarding = page.getByRole("link", { name: "New onboarding", exact: true });
  if (fresh) await expect(newOnboarding).toHaveAttribute("href", "/new-onboarding", { timeout: 60_000 });
  await newOnboarding.click();
  if (fresh) await expect(page.getByLabel("Company Legal Name", { exact: true })).toHaveValue("");
  await page.getByLabel("Jurisdiction", { exact: true }).selectOption("SG");
  await page.getByLabel("Company Legal Name", { exact: true }).fill(company.name);
  await page.getByLabel("Registration ID / UEN").fill(company.uen);
  await page.locator("#home-document").setInputFiles(pdf);
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
  await expect(page).toHaveURL(/\/cases\/[0-9a-f-]{36}$/i);
  await page.unroute("**/api/clm/zero-touch/cases");
  const caseId = page.url().split("/").at(-1)!;
  await expect.poll(async () => {
    const current = await summary(page, caseId);
    return `${current.status}:${current.current_stage}`;
  }, { timeout: 60_000 }).toBe("WAITING_FOR_REVIEW:OWNERSHIP");
  return caseId;
}

// Verification through the existing, unchanged Ownership & UBO components only.
test("Five-layer hybrid onboarding renders five corporate levels in the existing ownership view", { tag: "@slice-b-five-layer-hybrid" }, async ({ page }) => {
  const caseId = await onboard(page);
  const evidence = retainedEvidencePath("five-layer-hybrid"); await mkdir(evidence, { recursive: true });
  const current = await summary(page, caseId);
  expect(current.case.entity.legal_name).toBe(company.name);
  expect(current.case.goldtier_result).toBeNull();
  expect(current.reconciliation.status).toBe("MATCHED");
  const first = await counts(page);
  expect(first.token_requests).toBe(1);
  expect(first.gets).toEqual([
    ...[company.uen, ...issuers].sort().map((uen) => ({ operation: "ENTITY_PROFILE", uen, count: uen === company.uen ? 2 : 1 })),
  ]);

  // Backend/API truth labels; the unchanged UI does not render these optional fields.
  const ownership = await (await page.request.get(`/api/onboarding/cases/${caseId}/ownership`)).json();
  expect(ownership.state).toBe("REVIEW_REQUIRED");
  expect(ownership.source_classification).toBe("OFFICIAL_MOCK_PLUS_LOCAL_DIRECT_OVERLAY");
  expect(ownership.discovery.records.map((item: any) => item.depth).sort()).toEqual([1, 2, 3, 3, 4]);
  expect(new Set(ownership.discovery.records.map((item: any) => item.identity_basis))).toEqual(new Set(["LOCAL_SYNTHETIC_IDENTITY"]));
  expect(Object.fromEntries(ownership.candidates.map((item: any) => [item.party.display_name, item.synthetic_basis_threshold_result]))).toEqual({
    "ALEX TAN (SYNTHETIC PERSON)": "NOT_MET", "BEATRICE LIM (SYNTHETIC PERSON)": "MET",
    "CHARLES ONG (SYNTHETIC PERSON)": "NOT_MET", "DIANA KOH (SYNTHETIC PERSON)": "MET",
    "EDWARD NG (SYNTHETIC PERSON)": "NOT_MET",
  });

  await openStage(page, "Ownership & UBO");
  const stage = page.getByRole("region", { name: "Ownership & UBO", exact: true });
  const hierarchy = stage.getByRole("table", { name: "Ownership hierarchy", exact: true });
  await expect(hierarchy).toBeVisible();
  await expect(stage.getByLabel("Hierarchy summary")).toContainText("5 layers");
  await expect(stage.getByText("Partial or disputed ownership evidence — review required.", { exact: true })).toBeVisible();
  const root = hierarchy.getByRole("row").filter({ has: page.getByRole("button", { name: company.name, exact: true }) }).first();
  await expect(root).toContainText("ACRA_REGISTRY_ACQUISITION · MOCK");
  // L1 -> L2 -> L3 -> L4A -> L5: each company row shows its holding and LOCAL link source.
  for (const [name, holding] of [
    ["FIVE LAYER L2 HOLDINGS (SYNTHETIC)", `Holds 80% of ${company.name}`],
    ["FIVE LAYER L3 INVESTMENTS (SYNTHETIC)", "Holds 62.5% of FIVE LAYER L2 HOLDINGS (SYNTHETIC)"],
    ["FIVE LAYER L4A CAPITAL (SYNTHETIC)", "Holds 60% of FIVE LAYER L3 INVESTMENTS (SYNTHETIC)"],
    ["FIVE LAYER L5 HOLDCO (SYNTHETIC)", "Holds 100% of FIVE LAYER L4A CAPITAL (SYNTHETIC)"],
  ]) {
    const row = hierarchy.getByRole("row").filter({ has: page.getByRole("button", { name, exact: true }) }).first();
    await expect(row).toContainText(holding);
    await expect(row).toContainText("LOCAL_SYNTHETIC_RELATIONSHIP · LOCAL");
  }
  await stage.screenshot({ path: path.join(evidence, "five-layer-ownership-stage.png") });
  const person = hierarchy.getByRole("button", { name: "DIANA KOH (SYNTHETIC PERSON)", exact: true }).first();
  await person.click();
  const detail = stage.getByLabel("Selected holder");
  await expect(detail).toContainText("25%");
  await expect(detail).toContainText("REVIEW_REQUIRED");
  await expect(detail).toContainText("→ INDETERMINATE");
  await expect(detail).toContainText("80% x 62.5% x 60% x 100% x 62.5% = 18.75%");
  await expect(detail).toContainText("2 retained paths reach this person");
  await expect(detail).toContainText("LOCAL_SYNTHETIC_RELATIONSHIP · LOCAL");
  await detail.screenshot({ path: path.join(evidence, "five-layer-selected-holder.png") });
  const discovery = stage.locator(".ownership-discovery");
  await expect(discovery).toContainText("Corporate owners from separate registry records (5)");
  await expect(discovery).toContainText("LOCAL_SYNTHETIC_OVERLAY");
  await expect(page.getByRole("button", { name: /Confirm and send to Mock GoldTier/ })).toHaveCount(0);

  // A second normal onboarding of the same root reuses the official-namespace cache.
  await page.goto("/");
  const secondId = await onboard(page, true);
  expect(secondId).not.toBe(caseId);
  const second = await counts(page);
  expect(second).toEqual(first);
  const secondOwnership = await (await page.request.get(`/api/onboarding/cases/${secondId}/ownership`)).json();
  expect(secondOwnership.discovery.cache_hits).toBe(5);
  expect(secondOwnership.discovery.provider_backed_lookups).toBe(0);
});
