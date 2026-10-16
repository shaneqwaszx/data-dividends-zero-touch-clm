import { formatOwnershipPercent } from "../src/ownershipDisplay";
import { expect, test } from "@playwright/test";
import { createBrowserNetworkPolicy, handleBrowserRoute, retainedEvidencePath } from "../playwright.config";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { openStage, openStageSupport } from "./stage-disclosures";
import { confirmBatch, reviewPendingFields, reviewSourceChoices } from "./blocker-decisions";
import type { OwnershipAnalysisRecord } from "../src/types";

const validIdentityFixture = JSON.parse(await readFile(new URL("../src/pages/ownershipValidIdentityFixture.json", import.meta.url), "utf8")) as OwnershipAnalysisRecord;

const clean = "Legal Name: MERLION CIRCULAR LABS PTE. LTD.\nUEN: 202400001A\nRegistered Address: 18 INNOVATION WAY, #04-01, 018956, SG\nCountry: SG";

test("PR83 initial multi-file intake remains pending until explicit count completion", async ({ page }) => {
  const violations: string[] = [];
  const policy = createBrowserNetworkPolicy({ frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!, backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false });
  await page.route("**/*", route => handleBrowserRoute(route, policy, violations));
  await page.goto("/");
  const login = page.waitForResponse(response => response.url().endsWith("/api/auth/login") && response.request().method() === "POST");
  await page.getByLabel("User ID").fill("maya-lim");
  await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  const headers = { "X-CSRF-Token": (await (await login).json()).csrf_token };
  const created = await page.request.post("/api/clm/zero-touch/cases", { headers, data: { uen: "202400001A" } });
  expect(created.status()).toBe(201);
  const cid = (await created.json()).case.case_id;
  const uploaded = await page.request.post(`/api/clm/zero-touch/cases/${cid}/intake/documents`, {
    headers: { ...headers, "Content-Type": "text/plain", "X-Document-Name": "initial-partial.txt" },
    data: Buffer.from(clean.replace("MERLION CIRCULAR LABS PTE. LTD.", "OTHER SYNTHETIC NAME")),
  });
  expect(uploaded.status()).toBe(201);
  await page.goto(`/cases/${cid}`); await openStage(page, "Document verification");
  const mutations: string[] = [];
  page.on("request", request => { if (request.method() === "POST") mutations.push(new URL(request.url()).pathname); });
  const reviewed = await reviewPendingFields(page, { legal_name: "MERLION CIRCULAR LABS PTE. LTD." });
  expect(reviewed.status).toBe("PENDING_INPUTS"); expect(reviewed.current_stage).toBe("DOCUMENT");
  expect(reviewed.timing.automation_elapsed_ms).toBeNull();
  expect(reviewed.timeline.some((event: { event_type: string }) => event.event_type === "ONBOARDING_STARTED")).toBe(false);
  const count = page.getByLabel("Intended document count", { exact: true });
  await expect(count).toHaveValue("");
  await expect(page.getByRole("button", { name: "Continue recovered intake", exact: true })).toHaveCount(0);
  expect(mutations).toHaveLength(1);
  await count.fill("2");
  const incomplete = page.waitForResponse(response => response.url().endsWith("/intake/complete") && response.request().method() === "POST");
  await page.getByRole("button", { name: "Complete document intake", exact: true }).click();
  expect((await incomplete).status()).toBe(409);
  await expect(page.locator(".case-action-progress")).toHaveCount(0);
  const stillPending = await (await page.request.get(`/api/clm/zero-touch/cases/${cid}`)).json();
  expect(stillPending.status).toBe("PENDING_INPUTS"); expect(stillPending.version).toBe(reviewed.version);
  await page.reload(); await openStage(page, "Document verification");
  await expect(count).toHaveValue("");
  const received = page.waitForResponse(response => response.url().endsWith("/intake/documents") && response.request().method() === "POST");
  await page.locator("#case-document-upload input").setInputFiles({ name: "second-intended.txt", mimeType: "text/plain", buffer: Buffer.from(clean) });
  expect((await received).status()).toBe(201);
  await expect(page.locator(".case-action-progress")).toHaveCount(0);
  await expect(count).toHaveValue("");
  const evidence = retainedEvidencePath("pr83-initial-intake"); await mkdir(evidence, { recursive: true });
  await page.setViewportSize({ width: 360, height: 1000 });
  expect(await page.evaluate(() => document.body.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
  await page.locator("#case-document-intake-start").screenshot({ path: path.join(evidence, "explicit-count-mobile.png") });
  await count.fill("2");
  const completion = page.waitForResponse(response => response.url().endsWith("/intake/complete") && response.request().method() === "POST");
  await page.getByRole("button", { name: "Complete document intake", exact: true }).click();
  const response = await completion;
  expect(response.status()).toBe(200); expect(response.request().postDataJSON()).toEqual({ expected_document_count: 2 });
  const final = await response.json();
  expect(final.status).toBe("WAITING_FOR_REVIEW"); expect(final.current_stage).toBe("READINESS");
  expect(final.case.target_dispatch_confirmation).toBeNull(); expect(final.case.goldtier_result).toBeNull();
  expect(final.timeline.filter((event: { event_type: string }) => event.event_type === "ONBOARDING_STARTED")).toHaveLength(1);
  await expect(count).toHaveCount(0);
  expect(mutations).toHaveLength(4);
  expect(mutations.some(route => route.endsWith("/resume") || route.endsWith("/target-confirmation"))).toBe(false);
  expect(violations).toEqual([]);
  await writeFile(path.join(evidence, "receipt.json"), JSON.stringify({ before: reviewed.status, expectedCount: 2, wrongCountRejected: true, status: final.status, stage: final.current_stage, mutations, targetConfirmed: false }, null, 2));
});

test("Ownership hotfix valid root identity selects retained holder with keyboard and mobile reload", async ({ page }) => {
  const violations: string[] = [];
  const policy = createBrowserNetworkPolicy({ frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!, backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false });
  await page.route("**/*", route => handleBrowserRoute(route, policy, violations));
  const duplicateKeys: string[] = [];
  page.on("console", message => { if (message.text().includes("same key")) duplicateKeys.push(message.text()); });
  await page.goto("/");
  const login = page.waitForResponse(response => response.url().endsWith("/api/auth/login") && response.request().method() === "POST");
  await page.getByLabel("User ID").fill("maya-lim");
  await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  const headers = { "X-CSRF-Token": (await (await login).json()).csrf_token };
  const created = await page.request.post("/api/clm/zero-touch/cases", {
    headers, data: { uen: "202400006F" },
  });
  expect(created.status()).toBe(201);
  const cid = (await created.json()).case.case_id;
  const uploaded = await page.request.post(`/api/clm/zero-touch/cases/${cid}/intake/documents`, {
    headers: { ...headers, "Content-Type": "application/pdf", "X-Document-Name": "synthetic-cycle-profile.pdf" },
    data: await readFile(new URL("../../backend/tests/fixtures/uat/cycle-uen-clean.pdf", import.meta.url)),
  });
  expect(uploaded.status()).toBe(201);
  const started = await page.request.post(`/api/clm/zero-touch/cases/${cid}/intake/complete`, { headers, data: { expected_document_count: 1 } });
  expect(started.status()).toBe(200);
  const paused = await started.json();
  expect(paused.current_stage).toBe("OWNERSHIP");
  const ownership = await (await page.request.get(`/api/onboarding/cases/${cid}/ownership`)).json();
  const documents = await (await page.request.get(`/api/onboarding/cases/${cid}/documents`)).json();
  const document = documents.find((item: { state: string; superseded_by_document_id: string | null }) => !item.superseded_by_document_id && item.state === "REVIEWED");
  expect(document).toBeTruthy();
  await page.goto(`/cases/${cid}`);
  await page.getByRole("region", { name: "Attention required", exact: true }).getByRole("button", { name: /^Blocker:/ }).first().click();
  await expect(page.locator("#case-manual-ownership-evidence input:focus, #case-manual-ownership-evidence select:focus")).toHaveCount(1);
  const parties = structuredClone(validIdentityFixture.parties);
  const rootParty = parties.find(party => party.party_id === validIdentityFixture.root_party_id)!;
  rootParty.registration_number = "202400006F";
  rootParty.display_name = paused.case.entity.legal_name;
  const submitted = await page.request.post(`/api/clm/zero-touch/cases/${cid}/manual-ownership-evidence`, {
    headers, data: {
      root_registration_number: "202400006F", evidence_document_id: document.document_id,
      evidence_document_version: document.events.length, as_of_date: paused.updated_at.slice(0, 10),
      rationale: "Controlled synthetic ownership declaration reviewed against current document.",
      root_party_id: validIdentityFixture.root_party_id, parties,
      relationships: validIdentityFixture.relationships.map(edge => ({ relationship_id: edge.relationship_id,
        parent_party_id: edge.parent_party_id, child_party_id: edge.child_party_id,
        ownership_percent: edge.ownership_percent, relationship_type: "DIRECT_ECONOMIC_INTEREST" })),
      expected_automation_version: paused.version, expected_ownership_version: ownership.version,
      expected_case_event_count: paused.case.events.length,
    },
  });
  expect(submitted.status()).toBe(200);
  const record = await (await page.request.get(`/api/onboarding/cases/${cid}/ownership`)).json();
  expect(record.state).toBe("ANALYZED");
  expect(record.relationships[0].relationship_id).toBe("root");
  const candidate = record.candidates.find((item: { party: { display_name: string } }) => item.party.display_name === "Avery Tan");
  expect(candidate.classification).toBe("PROVISIONAL_UBO_CANDIDATE");
  const evidence = retainedEvidencePath("ownership-valid-identity"); await mkdir(evidence, { recursive: true });
  await page.goto(`/cases/${cid}`); await openStage(page, "Ownership & UBO");
  for (const width of [1280, 360]) {
    await page.setViewportSize({ width, height: 1000 });
    const person = page.locator('[aria-label="Ownership hierarchy"]').getByRole("button", { name: "Avery Tan", exact: true });
    await person.focus(); await person.press("Enter");
    await expect(page.getByRole("complementary", { name: "Selected holder" }).locator("h5")).toHaveText("Avery Tan");
    await expect(page.getByRole("complementary", { name: "Selected holder" })).toContainText(formatOwnershipPercent(candidate.aggregated_ownership_percent));
    expect(await page.evaluate(() => document.body.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
    await page.locator(".ownership-structure").screenshot({ path: path.join(evidence, `valid-root-${width}.png`) });
  }
  await page.reload(); await openStage(page, "Ownership & UBO");
  await page.locator('[aria-label="Ownership hierarchy"]').getByRole("button", { name: "Avery Tan", exact: true }).click();
  await expect(page.getByRole("complementary", { name: "Selected holder" }).locator("h5")).toHaveText("Avery Tan");
  const final = await (await page.request.get(`/api/clm/zero-touch/cases/${cid}`)).json();
  expect(final.case.target_dispatch_confirmation).toBeNull(); expect(final.case.goldtier_result).toBeNull();
  expect(duplicateKeys).toEqual([]); expect(violations).toEqual([]);
  await writeFile(path.join(evidence, "receipt.json"), JSON.stringify({ relationship_id: "root", selected: "Avery Tan",
    effective: candidate.aggregated_ownership_percent, provider: record.provider_name,
    status: final.status, stage: final.current_stage, targetConfirmed: false }, null, 2));
});

for (const replace of [false, true]) {
  test(`Ownership hotfix ${replace ? "replacement" : "confirmation"} continues without extra resume`, async ({ page }) => {
    const violations: string[] = [];
    const policy = createBrowserNetworkPolicy({ frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!, backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false });
    await page.route("**/*", route => handleBrowserRoute(route, policy, violations));
    await page.goto("/");
    const login = page.waitForResponse(r => r.url().endsWith("/api/auth/login") && r.request().method() === "POST");
    await page.getByLabel("User ID").fill("maya-lim");
    await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    const headers = { "X-CSRF-Token": (await (await login).json()).csrf_token };
    const created = await page.request.post("/api/clm/zero-touch/cases", { headers, data: { uen: "202400001A" } });
    expect(created.status()).toBe(201);
    const cid = (await created.json()).case.case_id;
    const uploaded = await page.request.post(`/api/clm/zero-touch/cases/${cid}/intake/documents`, {
      headers: { ...headers, "Content-Type": "text/plain", "X-Document-Name": "synthetic-conflict.txt" },
      data: Buffer.from(replace ? "SYNTHETIC DOCUMENT MISSING REQUIRED FIELDS\n".repeat(3) : clean.replace("MERLION CIRCULAR LABS PTE. LTD.", "OTHER SYNTHETIC NAME")),
    });
    expect(uploaded.status()).toBe(201);
    const completed = await page.request.post(`/api/clm/zero-touch/cases/${cid}/intake/complete`, {
      headers, data: { expected_document_count: 1 },
    });
    expect(completed.status()).toBe(200);
    expect((await completed.json()).current_stage).toBe("DOCUMENT");
    await page.goto(`/cases/${cid}`);
    await openStage(page, "Document verification");
    const evidence = retainedEvidencePath("ownership-hotfix"); await mkdir(evidence, { recursive: true });
    await page.locator("#case-blocker-review").screenshot({ path: path.join(evidence, `${replace ? "replacement" : "confirmation"}-before.png`) });
    const mutations: string[] = [];
    page.on("request", request => { if (request.method() === "POST") mutations.push(new URL(request.url()).pathname); });
    if (replace) {
      const fields = page.locator("select[data-review-field]"); expect(await fields.count()).toBe(4);
      for (let index = 0; index < 4; index++) await fields.nth(index).selectOption("REJECTED");
      const rejected = await confirmBatch(page); expect(rejected.current_stage).toBe("DOCUMENT");
      expect(rejected.case.goldtier_result).toBeNull();
      await page.getByRole("region", { name: "Attention required", exact: true }).getByRole("button", { name: /^Blocker:/ }).first().click();
      await expect(page.getByLabel("Replace current document", { exact: true })).toBeFocused();
      const replacement = page.waitForResponse(r => r.url().includes("/replace") && r.request().method() === "POST");
      await page.getByLabel("Replace current document", { exact: true }).setInputFiles({ name: "synthetic-replacement.txt", mimeType: "text/plain", buffer: Buffer.from(clean) });
      expect((await replacement).status()).toBe(200);
      await expect(page.locator(".case-action-progress")).toHaveCount(0);
      await openStageSupport(page, "Document verification", "More");
      await expect(page.getByText("Evidence history (1)", { exact: true })).toBeVisible();
      await page.locator(".document-evidence-panel").screenshot({ path: path.join(evidence, "replacement-after.png") });
    } else {
      const confirmed = await reviewPendingFields(page);
      expect(confirmed.status).toBe("WAITING_FOR_REVIEW");
      expect(confirmed.current_stage).toBe("DOCUMENT");
      await reviewSourceChoices(page, "KEEP_REGISTRY_VALUE");
    }
    await expect(page.getByRole("button", { name: "Continue evidence review", exact: true })).toHaveCount(0);
    expect(mutations.some(p => p.endsWith("/resume"))).toBe(false);
    expect(mutations).toHaveLength(2);
    const final = await (await page.request.get(`/api/clm/zero-touch/cases/${cid}`)).json();
    expect(final.active_exceptions.some((e: { stage: string }) => e.stage === "DOCUMENT")).toBe(false);
    expect(final.case.goldtier_result).toBeNull();
    expect(final.case.target_dispatch_confirmation).toBeNull();
    await page.locator(".document-evidence-panel").screenshot({ path: path.join(evidence, "document-after-continuation.png") });
    await openStage(page, "Ownership & UBO");
    await expect(page.getByRole("heading", { name: "Ownership structure", exact: true })).toBeVisible();
    await expect(page.getByRole("region", { name: /Identified UBO candidates/ }).first()).toBeVisible();
    for (const width of [1280, 360]) {
      await page.setViewportSize({ width, height: 1100 });
      expect(await page.evaluate(() => document.body.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
      await page.locator(".ownership-structure").screenshot({ path: path.join(evidence, `ownership-${replace ? "replacement" : "confirmation"}-${width}.png`) });
    }
    await page.reload(); await openStage(page, "Ownership & UBO");
    await expect(page.locator(".ownership-structure")).toBeVisible();
    const ownership = await (await page.request.get(`/api/onboarding/cases/${cid}/ownership`)).json();
    await writeFile(path.join(evidence, "receipt.json"), JSON.stringify({ mode: replace ? "replacement" : "confirmation", mutations, status: final.status, stage: final.current_stage, targetConfirmed: false, ownership: { analysis_id: ownership.analysis_id, source: ownership.source_classification, provider: ownership.provider_name, candidates: ownership.candidates.map((c: any) => ({ name: c.party.display_name, effective: c.aggregated_ownership_percent, classification: c.classification, threshold: c.threshold_result })) } }, null, 2));
    expect(violations).toEqual([]);
  });
}

test("Ownership hotfix Garden hierarchy and matching final candidates", { tag: "@garden-protocol" }, async ({ page }) => {
  const violations: string[] = [];
  const policy = createBrowserNetworkPolicy({ frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!, backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false });
  await page.route("**/*", route => handleBrowserRoute(route, policy, violations));
  await page.goto("/");
  const login = page.waitForResponse(r => r.url().endsWith("/api/auth/login") && r.request().method() === "POST");
  await page.getByLabel("User ID").fill("maya-lim"); await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  const headers = { "X-CSRF-Token": (await (await login).json()).csrf_token };
  const created = await page.request.post("/api/clm/zero-touch/cases", { headers, data: { uen: "11111999A", legal_name: "GARDEN BUSINESS", country_of_incorporation: "SG" } });
  expect(created.status()).toBe(201); const cid = (await created.json()).case.case_id;
  const uploaded = await page.request.post(`/api/clm/zero-touch/cases/${cid}/intake/documents`, {
    headers: { ...headers, "Content-Type": "text/plain", "X-Document-Name": "garden-synthetic.txt" },
    data: Buffer.from("Legal Name: GARDEN BUSINESS\nUEN: 11111999A\nRegistered Address: 18 GARDEN WALK, #01-01, 018919, SG\nCountry: SG\nKYC Customer Type: Company - Private\nClient Segment: Corporate"),
  });
  expect(uploaded.status()).toBe(201);
  const started = await page.request.post(`/api/clm/zero-touch/cases/${cid}/intake/complete`, { headers, data: { expected_document_count: 1 } });
  expect(started.status()).toBe(200);
  const evidence = retainedEvidencePath("ownership-hotfix-garden"); await mkdir(evidence, { recursive: true });
  await page.goto(`/cases/${cid}`); await openStage(page, "Ownership & UBO");
  const result = await (await page.request.get(`/api/onboarding/cases/${cid}/ownership`)).json();
  expect(result.state).toBe("ANALYZED");
  const qualifying = result.candidates.filter((c: any) => c.party.party_type === "NATURAL_PERSON" && c.threshold_result === "MET" && c.classification === "PROVISIONAL_UBO_CANDIDATE");
  expect(qualifying).toHaveLength(2);
  // Display expectations are independent of the production formatter. Threshold
  // results and the retained receipt continue to use the exact backend values.
  const displayPercent = new Intl.NumberFormat("en-US", { useGrouping: false, maximumFractionDigits: 2 });
  const effectiveDisplay = (candidate: any) => `${displayPercent.format(Number(candidate.aggregated_ownership_percent))}% effective`;
  await expect(page.locator('[aria-label="Ownership candidates"]')).toHaveCount(0);
  const hierarchy = page.getByRole("table", { name: "Ownership hierarchy", exact: true });
  await expect(hierarchy).toBeVisible();
  for (const candidate of qualifying) {
    await expect(page.locator(".ubo-summary").first()).toContainText(candidate.party.display_name);
    await expect(page.locator(".ubo-summary").first()).toContainText(effectiveDisplay(candidate));
    const person = hierarchy.getByRole("button", { name: candidate.party.display_name, exact: true });
    await expect(person).toHaveCount(1);
    await person.click();
    await expect(person).toHaveAttribute("aria-pressed", "true");
    const selected = page.getByRole("complementary", { name: "Selected holder", exact: true });
    await expect(selected.getByRole("heading", { name: candidate.party.display_name, exact: true })).toBeVisible();
    await expect(selected).toContainText(candidate.classification);
    await expect(selected).toContainText(candidate.threshold_result);
  }
  const collapse = page.locator(".ownership-structure__toggle").first();
  await collapse.focus(); await collapse.press("Enter"); await expect(collapse).toHaveAttribute("aria-expanded", "false");
  await collapse.press("Enter"); await expect(collapse).toHaveAttribute("aria-expanded", "true");
  const firstCandidate = hierarchy.getByRole("button", { name: qualifying[0].party.display_name, exact: true });
  await expect(firstCandidate).toHaveCount(1);
  await firstCandidate.click();
  await expect(firstCandidate).toHaveAttribute("aria-pressed", "true");
  for (const width of [1280, 360]) {
    await page.setViewportSize({ width, height: 1100 });
    expect(await page.evaluate(() => document.body.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
    await page.locator(".ownership-structure").screenshot({ path: path.join(evidence, `garden-${width}.png`) });
  }
  await page.evaluate(() => { document.documentElement.style.fontSize = "200%"; });
  expect(await page.evaluate(() => document.body.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
  await page.reload(); await openStage(page, "Ownership & UBO");
  await expect(page.locator(".ownership-structure")).toContainText("LOCAL_SYNTHETIC_SUPPLEMENT");
  await openStage(page, "Final review & send");
  const finalSummary = page.locator(".review-and-send .ubo-summary");
  for (const candidate of qualifying) {
    await expect(finalSummary).toContainText(candidate.party.display_name);
    await expect(finalSummary).toContainText(effectiveDisplay(candidate));
    await expect(finalSummary).toContainText(candidate.classification);
  }
  await finalSummary.screenshot({ path: path.join(evidence, "garden-final-review.png") });
  await writeFile(path.join(evidence, "receipt.json"), JSON.stringify({ analysis_id: result.analysis_id, source: result.source_classification, provider: result.provider_name, provider_environment: result.provider_environment, candidates: qualifying.map((c: any) => ({ name: c.party.display_name, effective: c.aggregated_ownership_percent, direct: c.direct_ownership_percent, indirect: c.indirect_ownership_percent, threshold: c.threshold_percent, result: c.threshold_result })), targetConfirmed: false }, null, 2));
  expect(violations).toEqual([]);
});
