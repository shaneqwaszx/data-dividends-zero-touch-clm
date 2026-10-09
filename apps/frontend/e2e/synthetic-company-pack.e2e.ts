import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test, type Page } from "@playwright/test";
import { openStage } from "./stage-disclosures";
import { createBrowserNetworkPolicy, handleBrowserRoute } from "../playwright.config";

const fixtures = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../backend/tests/fixtures/uat/zero-touch-database");
const companies = [
  { code: "Orion", uen: "202400014N", name: "ORION SYNTHETIC TECHNOLOGIES PTE. LTD.", pdf: "orion-synthetic-technologies-client.pdf", candidates: ["Avery Synthetic", "Blair Synthetic"] },
  { code: "Pacific", uen: "202400015O", name: "PACIFIC SYNTHETIC LEDGER PTE. LTD.", pdf: "pacific-synthetic-ledger-client.pdf", candidates: ["Casey Synthetic", "Dana Synthetic", "Ellis Synthetic"] },
  { code: "Straits", uen: "202400016P", name: "STRAITS SYNTHETIC HOLDINGS PTE. LTD.", pdf: "straits-synthetic-holdings-client.pdf", candidates: ["Fiona Synthetic", "Jordan Synthetic"] },
  { code: "Meridian", uen: "202400017Q", name: "MERIDIAN SYNTHETIC INFRASTRUCTURE PTE. LTD.", pdf: "meridian-synthetic-infrastructure-client.pdf", candidates: ["Hannah Synthetic", "Iris Synthetic"] },
];

async function summary(page: Page, caseId: string) {
  const response = await page.request.get(`/api/clm/zero-touch/cases/${caseId}`);
  expect(response.status()).toBe(200);
  return response.json();
}

for (const company of companies) {
  test(`Synthetic company pack ${company.code} complete database-first Marketplace happy path`, { tag: "@slice-b-synthetic-seed" }, async ({ page }) => {
    const violations: string[] = [];
    const posts: string[] = [];
    const policy = createBrowserNetworkPolicy({ frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!,
      backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false });
    await page.route("**/*", (route) => handleBrowserRoute(route, policy, violations));
    page.on("request", (request) => { if (request.method() === "POST") posts.push(new URL(request.url()).pathname); });
    await page.goto("/");
    await page.getByLabel("User ID").fill("maya-lim");
    await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
    await page.getByRole("button", { name: "Sign in" }).click();
    await page.getByRole("link", { name: "New onboarding", exact: true }).click();
    await expect(page.getByText(/ACRA API Marketplace Mock/).first()).toBeVisible();
    const priorCounts = await (await page.request.get("/api/__slice_b/registry-counts")).json();
    expect(priorCounts.external_calls).toBe(0);
    await page.getByLabel("Jurisdiction", { exact: true }).selectOption("SG");
    await page.getByLabel("Company Legal Name", { exact: true }).fill(company.name);
    await page.getByLabel("Registration ID / UEN").fill(company.uen);
    await page.locator("#home-document").setInputFiles(path.join(fixtures, company.pdf));
    await page.getByRole("button", { name: "Create onboarding" }).click();
    await expect(page).toHaveURL(/\/new-onboarding\/[0-9a-f-]{36}$/i);
    const caseId = page.url().split("/").at(-1)!;
    await expect.poll(async () => (await summary(page, caseId)).status).toBe("WAITING_FOR_REVIEW");
    await page.getByRole("button", { name: "Open full case" }).click();
    await expect(page).toHaveURL(`/cases/${caseId}`);
    await expect(page.locator(".document-card:not(.document-card--history)")).toHaveCount(1);
    await openStage(page, "Document verification");
    await expect(page.locator(".document-field .tag", { hasText: "AUTO CONFIRMED" })).toHaveCount(4);
    const initial = await summary(page, caseId);
    expect(initial.case.entity.registration_number).toBe(company.uen);
    expect(initial.clm.target_search_checkpoint.disposition).toBe("NO_MATCH");
    expect(initial.case.registry_acquisition.status).toBe("COMPLETE");
    expect(initial.case.registry_evidence_binding.disposition).toBe("CACHE_HIT");
    expect(initial.case.registry_evidence_binding.synthetic_seed_namespace).toBe("LOCAL_SYNTHETIC_UAT_V1");
    expect(initial.case.registry_acquisition.operation_results.every((r: any) => r.provenance.evidence_reference.startsWith("LOCAL_SYNTHETIC_SEED_"))).toBe(true);
    await openStage(page, "Registry verification");
    await expect(page.getByText(/Local Synthetic Seed.*LOCAL PROJECT SYNTHETIC MOCK/)).toBeVisible();
    expect(initial.case.registry_acquisition.operation_results.map((r: any) => r.status)).toEqual(["COMPLETE", "COMPLETE", "COMPLETE", "COMPLETE"]);
    expect(initial.case.goldtier_result).toBeNull();
    const ownership = await (await page.request.get(`/api/onboarding/cases/${caseId}/ownership`)).json();
    expect(ownership.state).toBe("ANALYZED");
    expect(ownership.candidates.filter((c: any) => c.classification === "PROVISIONAL_UBO_CANDIDATE").map((c: any) => c.party.display_name).sort()).toEqual([...company.candidates].sort());
    await openStage(page, "Submission readiness");
    await page.getByLabel("KYC customer type", { exact: true }).selectOption("Company - Private");
    await page.getByLabel("Client segment", { exact: true }).selectOption("Corporate");
    const saved = page.waitForResponse((r) => r.request().method() === "PUT" && r.url().endsWith("/target-classification"));
    await page.getByRole("button", { name: "Save target classification" }).click();
    expect((await saved).status()).toBe(200);
    await expect.poll(async () => (await summary(page, caseId)).active_exceptions.map((e: any) => e.blocker_code)).toEqual(["TARGET_CONFIRMATION_REQUIRED"]);
    expect(posts.some((p) => p.endsWith("/target-confirmation"))).toBe(false);
    const counts = await (await page.request.get("/api/__slice_b/registry-counts")).json();
    expect(counts.external_calls).toBe(0);
    expect(counts.calls).toEqual([]);
    await openStage(page, "Final review & send");
    await page.getByRole("button", { name: "Confirm and send to Mock GoldTier" }).click();
    await expect.poll(async () => (await summary(page, caseId)).status).toBe("COMPLETED");
    const done = await summary(page, caseId);
    expect(done.target_submission.state).toBe("SUBMISSION_CONFIRMED");
    expect(done.case.goldtier_result.readback_status).toBe("VERIFIED");
    expect(done.case.goldtier_result.readback_party_id).toBe(done.case.goldtier_result.party_id);
    const before = posts.length;
    await page.reload();
    await openStage(page, "GoldTier submission package");
    await expect(page.getByText("Completed POC workflow", { exact: true })).toBeVisible();
    const retained = await summary(page, caseId);
    expect(retained.target_operations).toEqual(done.target_operations);
    expect(posts.length).toBe(before);
    expect((await (await page.request.get("/api/__slice_b/registry-counts")).json()).calls).toEqual(counts.calls);
    expect(violations).toEqual([]);
  });
}
