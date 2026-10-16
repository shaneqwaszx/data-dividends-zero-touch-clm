import { expect, test, type Page } from "@playwright/test";
import { createBrowserNetworkPolicy, handleBrowserRoute } from "../playwright.config";
import { expectDisclosureContrast, focusPipelineAction, openStage } from "./stage-disclosures";

let violations: string[];
test.beforeEach(async ({ page }) => {
  violations = [];
  const policy = createBrowserNetworkPolicy({
    frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!,
    backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false,
  });
  await page.route("**/*", (route) => handleBrowserRoute(route, policy, violations));
});
test.afterEach(() => expect(violations).toEqual([]));

async function login(page: Page): Promise<Record<string, string>> {
  await page.goto("/");
  await page.getByLabel("User ID").fill("maya-lim");
  await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
  const result = page.waitForResponse((response) => response.url().endsWith("/api/auth/login"));
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  const authenticated = await result;
  expect(authenticated.status()).toBe(200);
  const session = await authenticated.json();
  return { "X-CSRF-Token": session.csrf_token, Origin: process.env.PLAYWRIGHT_BASE_URL! };
}

async function create(page: Page, headers: Record<string, string>, uen = "202400001A") {
  const result = await page.request.post("/api/clm/zero-touch/cases", {
    headers, data: { uen, country_of_incorporation: "SG", legal_name: "Synthetic test entity" },
  });
  expect(result.status()).toBe(201);
  return result.json();
}

function profilePdf(uen: string, useNewProfile: boolean): Buffer {
  const lines = [
    "SYNTHETIC TEST DATA", "CORPORATE PROFILE",
    `UEN: ${uen}`,
    `Legal Name: ${useNewProfile ? "MULTI LEVEL OWNERSHIP DEMO PTE. LTD." : "MERLION CIRCULAR LABS PTE. LTD."}`,
    `Registered Address: ${useNewProfile ? "18 HIERARCHY WALK, #04-01, 049004, SG" : "18 INNOVATION WAY, #04-01, 018956, SG"}`,
    "Country: SG",
  ];
  const operations = "BT /F1 12 Tf 72 720 Td " +
    lines.map((line) => `(${line})`).join(" Tj 0 -16 Td ") + " Tj ET";
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    `<< /Length ${operations.length} >>\nstream\n${operations}\nendstream`,
  ];
  let output = "%PDF-1.4\n";
  const offsets = [0];
  objects.forEach((object, index) => {
    offsets.push(output.length);
    output += `${index + 1} 0 obj\n${object}\nendobj\n`;
  });
  const xref = output.length;
  output += "xref\n0 6\n0000000000 65535 f\n";
  output += offsets.slice(1).map((offset) => `${String(offset).padStart(10, "0")} 00000 n\n`).join("");
  output += `trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return Buffer.from(output, "latin1");
}

async function attachConflict(page: Page, headers: Record<string, string>, caseId: string, newProfile: boolean) {
  const result = await page.request.post(`/api/clm/zero-touch/cases/${caseId}/documents`, {
    headers: { ...headers, "Content-Type": "application/pdf", "X-Document-Name": "synthetic-phase24.pdf" },
    data: profilePdf("202400009I", newProfile),
  });
  expect(result.status()).toBe(200);
}

async function choose(page: Page, caseId: string, label: string) {
  const response = page.waitForResponse((result) => result.request().method() === "POST"
    && result.url().endsWith(`/cases/${caseId}/registry-identity`));
  await page.getByRole("button", { name: label, exact: true }).click();
  const result = await response;
  expect(result.status()).toBe(200);
  return result.json();
}

test("Phase24 invalid registry identity corrects the same case and keeps final review last", async ({ page }) => {
  const headers = await login(page);
  const created = await create(page, headers, "99999999Z");
  expect(created.status).toBe("WAITING_FOR_REVIEW");
  expect(created.technical_failure).toBeNull();
  expect(created.active_exceptions.map((item: any) => item.blocker_code)).toEqual(["ACRA_ENTITY_NOT_FOUND"]);
  const caseId = created.case.case_id;
  await page.goto(`/cases/${caseId}`);
  await expect(page.getByText("Registry verification could not verify this UEN.", { exact: true })).toBeVisible();
  await focusPipelineAction(page, "ACRA_REGISTRY", page.getByLabel("Singapore UEN", { exact: true }));
  await page.getByLabel("Singapore UEN").fill("202400001A");
  const corrected = await choose(page, caseId, "Verify UEN and resume");
  expect(corrected.case.case_id).toBe(caseId);
  expect(corrected.case.entity.registration_number).toBe("202400001A");
  expect(corrected.case.identity_corrections.at(-1).previous_identity.registration_number).toBe("99999999Z");
  expect(corrected.historical_exceptions.some((item: any) => item.blocker_code === "ACRA_ENTITY_NOT_FOUND"
    && item.status === "CANCELLED")).toBe(true);
  let previous = corrected;
  for (const uen of ["202400009I", "202400001A", "202400001A"]) {
    await openStage(page, "Registry verification");
    await page.getByRole("button", { name: "Edit UEN", exact: true }).click();
    await page.getByLabel("Singapore UEN").fill(uen);
    const next = await choose(page, caseId, "Verify UEN and resume");
    expect(next.case.case_id).toBe(caseId);
    expect(next.case.requested_uen).toBe(uen);
    expect(next.case.registry_acquisition.requested_identifier).toBe(uen);
    expect(next.case.identity_corrections).toHaveLength(previous.case.identity_corrections.length + 1);
    expect(next.case.identity_corrections.at(-1).previous_identity.registration_number)
      .toBe(previous.case.requested_uen);
    expect(next.version).toBeGreaterThan(previous.version);
    expect(next.active_exceptions.some((item: any) => item.blocker_code === "ACRA_ENTITY_NOT_FOUND")).toBe(false);
    previous = next;
  }
  await expect(page.locator(".stage-disclosure > h2 > button").last()).toHaveText("Final review & send+");
  await expect(page.locator(".stage-disclosure--final")).toContainText("Not yet available");
  await expect(page.getByText(/Not yet available —/)).toBeVisible();
  await expect(page.locator(".review-and-send")).toHaveCount(0);
  await page.setViewportSize({ width: 320, height: 900 });
  await expect.poll(() => page.evaluate(() =>
    document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
  )).toBe(true);
  const documents = page.getByRole("region", { name: "Document verification", exact: true });
  await expect(documents.locator(":scope > div").first()).toBeVisible();
  for (const kind of ["More", "Technical"]) {
    const control = documents.getByText(`${kind} details — Document verification`, { exact: true });
    const support = control.locator("..");
    await expect(support).not.toHaveAttribute("open", "");
    await page.mouse.move(0, 0);
    await expectDisclosureContrast(control);
    await control.hover();
    await expectDisclosureContrast(control);
    await page.mouse.move(0, 0);
    await control.focus();
    await expectDisclosureContrast(control);
    await page.keyboard.press("Enter");
    await expect(support).toHaveAttribute("open", "");
    await expect(documents.locator(":scope > div").first()).toBeVisible();
    await page.keyboard.press("Space");
    await expect(support).not.toHaveAttribute("open", "");
    await expect(documents.locator(":scope > details[open]")).toHaveCount(0);
  }
});

test("Phase24 entered UEN choice resolves current identity conflict without silent source selection", async ({ page }) => {
  const headers = await login(page);
  const created = await create(page, headers);
  const caseId = created.case.case_id;
  await attachConflict(page, headers, caseId, false);
  await page.goto(`/cases/${caseId}`);
  await expect(page.getByRole("heading", { name: "Entity identity requires confirmation" })).toBeVisible();
  const corrected = await choose(page, caseId, "Use entered UEN");
  expect(corrected.case.requested_uen).toBe("202400001A");
  expect(corrected.case.identity_corrections.at(-1).choice).toBe("ENTERED");
  expect(corrected.reconciliation.discrepancies.some((item: any) =>
    item.field_name === "registration_identifier" && item.status === "RESOLVED" &&
    item.decision.action === "KEEP_REGISTRY_VALUE",
  )).toBe(true);
  expect(corrected.active_exceptions.some((item: any) => item.stage === "DOCUMENT")).toBe(false);
  await expect(page.getByRole("heading", { name: "Entity identity requires confirmation" })).toHaveCount(0);
});

for (const choice of ["DOCUMENT", "OTHER"] as const) {
  test(`Phase24 ${choice.toLowerCase()} UEN choice rebinds ownership with retained history`, async ({ page }) => {
    const headers = await login(page);
    const created = await create(page, headers);
    const caseId = created.case.case_id;
    for (const operation of ["load", "analyze"]) {
      const response = await page.request.post(`/api/onboarding/cases/${caseId}/ownership/${operation}`, { headers });
      expect(response.status()).toBe(operation === "load" ? 201 : 200);
    }
    const oldResponse = await page.request.get(`/api/onboarding/cases/${caseId}/ownership`);
    const old = await oldResponse.json();
    await attachConflict(page, headers, caseId, true);
    await page.goto(`/cases/${caseId}`);
    let corrected;
    if (choice === "DOCUMENT") corrected = await choose(page, caseId, "Use document UEN");
    else {
      await page.getByRole("button", { name: "Enter another UEN" }).click();
      await page.getByLabel("Singapore UEN").fill("202400009I");
      corrected = await choose(page, caseId, "Verify UEN and resume");
    }
    expect(corrected.case.case_id).toBe(caseId);
    expect(corrected.case.entity.registration_number).toBe("202400009I");
    expect(corrected.case.identity_corrections.at(-1).choice).toBe(choice);
    const response = await page.request.get(`/api/onboarding/cases/${caseId}/ownership`);
    const ownership = await response.json();
    expect(ownership.analysis_id).not.toBe(old.analysis_id);
    expect(ownership.parties.find((item: any) => item.party_id === ownership.root_party_id).registration_number).toBe("202400009I");
    expect(corrected.case.identity_corrections.at(-1).previous_identity.registration_number).toBe("202400001A");
    await openStage(page, "Ownership & UBO");
    await expect(page.getByRole("heading", { name: "Ownership path explorer" })).toBeVisible();
    const ownershipStructure = page.getByRole("region", { name: "Ownership & UBO", exact: true }).locator(":scope > details").filter({ has: page.getByText("Technical details — Ownership & UBO", { exact: true }) });
    await expect(ownershipStructure).not.toHaveAttribute("open", "");
    const calculations = ownershipStructure.getByText("Technical details — Ownership & UBO", { exact: true }); await expect(calculations).toBeVisible(); await calculations.click();
    const evidence = page.getByLabel("Original ownership evidence", { exact: true });
    await expect(evidence).toBeVisible();
    await expect(evidence).toContainText("202400009I");
    await expect(evidence).not.toContainText("202400001A");
    await expect(evidence.locator("tbody tr")).toHaveCount(ownership.evidence.length);
    await expect(page.getByLabel("Ownership candidates", { exact: true })).toHaveCount(0);
    const hierarchy = page.getByRole("table", { name: "Ownership hierarchy", exact: true });
    await expect(hierarchy).toBeVisible();
    expect(ownership.candidates.length).toBeGreaterThan(0);
    for (const candidate of ownership.candidates) {
      const person = hierarchy.getByRole("button", { name: candidate.party.display_name, exact: true });
      await expect(person).toHaveCount(1);
      await expect(person).toBeVisible();
      await person.click();
      await expect(person).toHaveAttribute("aria-pressed", "true");
      const selected = page.getByRole("complementary", { name: "Selected holder", exact: true });
      await expect(selected.getByRole("heading", { name: candidate.party.display_name, exact: true })).toBeVisible();
      await expect(selected).toContainText(candidate.classification);
      await expect(selected).toContainText(candidate.threshold_result);
    }
  });
}
