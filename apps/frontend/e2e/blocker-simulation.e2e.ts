import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { createBrowserNetworkPolicy, handleBrowserRoute, retainedEvidencePath } from "../playwright.config";
import { focusPipelineAction, openStage } from "./stage-disclosures";
import { confirmBatch } from "./blocker-decisions";

const evidence = () => retainedEvidencePath("blocker-regression");
const identity = { "Legal Name": "MERLION CIRCULAR LABS PTE. LTD.", UEN: "202400001A", "Registered Address": "18 INNOVATION WAY, #04-01, 018956, SG", Country: "SG" };
const scenarios = [
  { name: "legal-name-mismatch", overrides: { "Legal Name": "OTHER SYNTHETIC NAME" }, target: "DOCUMENTS", choice: "source" },
  { name: "address-mismatch", overrides: { "Registered Address": "18 OTHER SYNTHETIC ROAD, SG" }, target: "DOCUMENTS", choice: "source" },
  { name: "country-mismatch", overrides: { Country: "MY" }, target: "DOCUMENTS", choice: "source" },
  { name: "multiple-mismatches", overrides: { "Legal Name": "OTHER SYNTHETIC NAME", "Registered Address": "18 OTHER TEST ROAD, SG", Country: "MY" }, target: "DOCUMENTS", choice: "source" },
  { name: "cross-document-conflict", overrides: { "Legal Name": "OTHER SYNTHETIC NAME" }, target: "DOCUMENTS", choice: "source", second: true },
  { name: "missing-required-field", overrides: { Country: "" }, target: "DOCUMENTS", choice: "document" },
  { name: "ambiguous-low-score", overrides: { "Legal Name": "FIRST TEST NAME\r\nLegal Name: SECOND TEST NAME" }, target: "DOCUMENTS", choice: "document" },
  { name: "uen-source-conflict", overrides: { UEN: "202400002B" }, target: "IDENTITY", choice: "identity" },
  { name: "classification-missing", overrides: { "KYC Customer Type": "Company - Private" }, target: "CLASSIFICATION", choice: "classification" },
  { name: "classification-conflicting", overrides: { "KYC Customer Type": "Company - Private\r\nKYC Customer Type: Government", "Client Segment": "Corporate" }, target: "CLASSIFICATION", choice: "classification" },
] as const;

for (const scenario of scenarios) {
  test(`Blocker simulation ${scenario.name}`, async ({ page }) => {
    const violations: string[] = [];
    const policy = createBrowserNetworkPolicy({ frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!, backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false });
    await page.route("**/*", route => handleBrowserRoute(route, policy, violations));
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/");
    const login = page.waitForResponse(response => response.url().endsWith("/api/auth/login") && response.request().method() === "POST");
    await page.getByLabel("User ID").fill("maya-lim"); await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    const headers = { "X-CSRF-Token": (await (await login).json()).csrf_token };
    const created = await page.request.post("/api/clm/zero-touch/cases", { headers, data: { uen: "202400001A", legal_name: identity["Legal Name"], country_of_incorporation: "SG" } });
    expect(created.status()).toBe(201); const cid = (await created.json()).case.case_id;
    const content = Buffer.from(Object.entries({ ...identity, ...scenario.overrides }).map(([key, value]) => `${key}: ${value}`).join("\r\n"));
    expect((await page.request.post(`/api/clm/zero-touch/cases/${cid}/intake/documents`, { headers: { ...headers, "Content-Type": "text/plain", "X-Document-Name": "synthetic-blocker.txt" }, data: content })).status()).toBe(201);
    const second = "second" in scenario;
    if (second) expect((await page.request.post(`/api/clm/zero-touch/cases/${cid}/intake/documents`, { headers: { ...headers, "Content-Type": "text/plain", "X-Document-Name": "synthetic-second.txt" }, data: Buffer.from(Object.entries(identity).map(([key, value]) => `${key}: ${value}`).join("\n")) })).status()).toBe(201);
    const started = await page.request.post(`/api/clm/zero-touch/cases/${cid}/intake/complete`, { headers, data: { expected_document_count: second ? 2 : 1 } });
    expect(started.status()).toBe(200); const before = await started.json();
    expect(before.status).toBe("WAITING_FOR_REVIEW");
    await page.goto(`/cases/${cid}`);
    await expect(page.locator("h1")).toBeVisible();
    const action = before.interventions.flatMap((item: any) => item.evidence_actions ?? []).find((item: any) => item.target === scenario.target);
    if (scenario.choice !== "identity") expect(action, "Current backend action required").toBeTruthy();
    const calls: string[] = [];
    page.on("request", request => { if (new URL(request.url()).pathname.startsWith("/api/")) calls.push(`${request.method()} ${new URL(request.url()).pathname}`); });
    if (scenario.choice === "identity") await focusPipelineAction(page, "RECONCILIATION", page.locator("#identity-registration-number"));
    else if (scenario.choice === "source") await page.locator(".intervention-card").getByRole("button", { name: "Keep registry value", exact: true }).first().click();
    else await page.getByRole("button", { name: action.label, exact: true }).click();
    const selector = scenario.choice === "source" ? "select[data-reconciliation-field]"
      : scenario.choice === "document" ? "select[data-review-field]"
      : scenario.choice === "identity" ? "#identity-registration-number" : "#case-target-classification select:not([disabled])";
    const control = page.locator(selector).first();
    await expect(control).toBeVisible(); await expect(control).toBeEnabled(); await expect(control).toBeFocused();
    const focusedControl = await control.evaluate(element => ({ tag: element.tagName, id: element.id,
      field: element.getAttribute("data-review-field") ?? element.getAttribute("data-reconciliation-field"),
      document: element.getAttribute("data-document-id"), discrepancy: element.getAttribute("data-discrepancy-id") }));
    await expect.poll(async () => control.evaluate(element => { const r = element.getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight; })).toBe(true);
    expect(calls.filter(call => !call.startsWith("GET "))).toEqual([]);
    let decisions = 0, result = before, confirmation = "Not applicable", callsBeforeConfirmation = 0;
    if (scenario.choice === "source" || scenario.choice === "document") {
      const controls = page.locator(selector); decisions = await controls.count();
      for (let index = 0; index < decisions; index++) {
        await controls.nth(index).focus();
        await controls.nth(index).selectOption(scenario.choice === "source" ? "KEEP_REGISTRY_VALUE" : "REJECTED");
        await expect(controls.nth(index)).toBeFocused();
      }
      expect(calls.filter(call => !call.startsWith("GET "))).toEqual([]);
      callsBeforeConfirmation = calls.length;
      result = await confirmBatch(page); confirmation = result.status;
      expect(calls.filter(call => call.startsWith("POST "))).toHaveLength(1);
      expect(result.case.goldtier_result).toBeNull();
      if (scenario.choice === "document") expect(result.active_exceptions.some((item: any) => item.stage === "DOCUMENT")).toBe(true);
      else expect(result.active_exceptions.filter((item: any) => item.stage === "DOCUMENT")).toEqual([]);
    }
    await mkdir(evidence(), { recursive: true });
    await writeFile(path.join(evidence(), `simulation-${scenario.name}.json`), JSON.stringify({ scenario: scenario.name, initial: before.active_exceptions.map((item: any) => item.blocker_code), expected_navigation: selector, actual_control: focusedControl, choices: decisions, calls_before_confirmation: callsBeforeConfirmation, calls, confirmation, final: result.active_exceptions.map((item: any) => item.blocker_code), verdict: "PASS", reduced_motion: true }, null, 2) + "\n");
    expect(violations).toEqual([]);
  });
}

test("Blocker simulation missing upload focuses actual file then permits one continuation", async ({ page }) => {
  const violations: string[] = [];
  const policy = createBrowserNetworkPolicy({ frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!, backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false });
  await page.route("**/*", route => handleBrowserRoute(route, policy, violations));
  await page.goto("/");
  const login = page.waitForResponse(response => response.url().endsWith("/api/auth/login") && response.request().method() === "POST");
  await page.getByLabel("User ID").fill("maya-lim"); await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  const headers = { "X-CSRF-Token": (await (await login).json()).csrf_token };
  const created = await page.request.post("/api/clm/zero-touch/cases", { headers, data: { uen: "202400001A" } });
  expect(created.status()).toBe(201); const cid = (await created.json()).case.case_id;
  await page.goto(`/cases/${cid}?focus=DOCUMENT_IDP`);
  const upload = page.locator("#case-document-upload input[type=file]");
  await expect(upload).toHaveCount(1);
  await expect(upload).toBeFocused();
  await expect(page.locator("#case-document-upload")).toBeInViewport({ ratio: 1 });
  const applied = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/intake/documents"));
  await upload.setInputFiles({ name: "synthetic-required.txt", mimeType: "text/plain", buffer: Buffer.from(Object.entries(identity).map(([key, value]) => `${key}: ${value}`).join("\n")) });
  expect((await applied).status()).toBe(201);
  await openStage(page, "Document verification");
  const continued = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/resume"));
  await page.getByRole("button", { name: "Continue evidence review", exact: true }).click();
  const result = await continued; expect(result.status()).toBe(200);
  const final = await result.json(); expect(final.case.goldtier_result).toBeNull();
  await mkdir(evidence(), { recursive: true });
  await writeFile(path.join(evidence(), "simulation-missing-upload.json"), JSON.stringify({ scenario: "missing-upload",
    initial: "PENDING_INPUTS / DOCUMENT_IDP", expected_navigation: "#case-document-upload input[type=file]",
    actual_control: "INPUT:file (focused, upload label fully in viewport)", choices: 0, calls_before_confirmation: 0,
    confirmation: "One upload POST then explicit Resume POST", final: final.active_exceptions.map((item: any) => item.blocker_code), verdict: "PASS" }, null, 2) + "\n");
  expect(violations).toEqual([]);
});

for (const fixture of [
  { name: "ownership-cycle", uen: "202400006F", legal: "CYCLIC HARBOUR HOLDINGS PTE. LTD.", address: "18 CYCLE STREET, #01-01, 049001, SG" },
  { name: "ownership-incomplete", uen: "202400011K", legal: "MISSING OWNERSHIP EVIDENCE DEMO PTE. LTD.", address: "18 PARTIAL STREET, #06-01, 049006, SG" },
  { name: "provider-relationship-failure", uen: "202400013M", legal: "FAILED RELATIONSHIP STEP DEMO PTE. LTD.", address: "18 FAILURE CLOSE, #08-01, 049008, SG" },
]) {
  test(`Blocker simulation ${fixture.name}`, async ({ page }) => {
    const violations: string[] = [];
    const policy = createBrowserNetworkPolicy({ frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!, backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false });
    await page.route("**/*", route => handleBrowserRoute(route, policy, violations));
    await page.goto("/");
    const login = page.waitForResponse(response => response.url().endsWith("/api/auth/login") && response.request().method() === "POST");
    await page.getByLabel("User ID").fill("maya-lim"); await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    const headers = { "X-CSRF-Token": (await (await login).json()).csrf_token };
    const created = await page.request.post("/api/clm/zero-touch/cases", { headers, data: { uen: fixture.uen, legal_name: fixture.legal, country_of_incorporation: "SG" } });
    expect(created.status()).toBe(201); const createdBody = await created.json(); const cid = createdBody.case.case_id;
    const content = Buffer.from(`Legal Name: ${fixture.legal}\nUEN: ${fixture.uen}\nRegistered Address: ${fixture.address}\nCountry: SG\nKYC Customer Type: Company - Private\nClient Segment: Corporate`);
    let initial = createdBody;
    if (createdBody.status === "PENDING_INPUTS") {
      expect((await page.request.post(`/api/clm/zero-touch/cases/${cid}/intake/documents`, { headers: { ...headers, "Content-Type": "text/plain", "X-Document-Name": "synthetic-ownership.txt" }, data: content })).status()).toBe(201);
      const started = await page.request.post(`/api/clm/zero-touch/cases/${cid}/intake/complete`, { headers, data: { expected_document_count: 1 } });
      expect(started.status()).toBe(200); initial = await started.json();
    } else expect(fixture.name).toBe("provider-relationship-failure");
    expect(initial.status).not.toBe("COMPLETED"); expect(initial.case.goldtier_result).toBeNull();
    await page.goto(`/cases/${cid}`);
    await expect(page.getByRole("button", { name: "Confirm and send to Mock GoldTier", exact: true })).toHaveCount(0);
    const action = initial.interventions.flatMap((item: any) => item.evidence_actions ?? []).find((item: any) => item.target === "OWNERSHIP_DETAILS");
    let focused = "No authorized local corrective action";
    const mutations: string[] = [];
    page.on("request", request => { if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method())) mutations.push(request.url()); });
    if (action) {
      await page.getByRole("button", { name: action.label, exact: true }).click();
      const form = page.locator("#case-manual-ownership-evidence");
      await expect(form).toBeVisible();
      const active = form.locator("input:not([disabled]):not([readonly]), select:not([disabled]), textarea:not([disabled]), button:not([disabled])").first();
      await expect(active).toBeFocused(); focused = await active.evaluate(element => element.tagName + ":" + element.id);
    } else {
      await openStage(page, initial.current_stage === "OWNERSHIP" ? "Ownership & UBO" : "Registry verification");
      const code = initial.technical_failure?.code ?? initial.case.error?.code;
      expect(code).toBeTruthy();
      await expect(page.getByText(code, { exact: true }).first()).toBeVisible();
      await expect(page.getByRole("button", { name: /retry target|ignore and continue/i })).toHaveCount(0);
    }
    expect(mutations).toEqual([]);
    await mkdir(evidence(), { recursive: true });
    await writeFile(path.join(evidence(), `simulation-${fixture.name}.json`), JSON.stringify({ scenario: fixture.name, initial: initial.active_exceptions.map((item: any) => item.blocker_code), actual_control: focused, choices: 0, calls_before_confirmation: 0, confirmation: "Evidence must be supplied; blocker not waived", final: initial.status, verdict: "PASS" }, null, 2) + "\n");
    expect(violations).toEqual([]);
  });
}

test("Blocker simulation draft isolation and same-team/cross-team authorization", async ({ page }) => {
  const violations: string[] = [];
  const policy = createBrowserNetworkPolicy({ frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!, backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false });
  await page.route("**/*", route => handleBrowserRoute(route, policy, violations));
  async function signIn(user: string) {
    const loggedIn = page.waitForResponse(response => response.url().endsWith("/api/auth/login") && response.request().method() === "POST");
    await page.getByLabel("User ID").fill(user);
    await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await expect(page.getByRole("navigation", { name: "Main workspace" })).toBeVisible();
    return { "X-CSRF-Token": (await (await loggedIn).json()).csrf_token };
  }
  async function signOut() {
    await page.locator(".operator-account__button").click();
    await page.getByRole("button", { name: "Sign out", exact: true }).click();
  }
  await page.goto("/"); const headers = await signIn("maya-lim");
  const created = await page.request.post("/api/clm/zero-touch/cases", { headers, data: { uen: "202400001A" } });
  expect(created.status()).toBe(201); const cid = (await created.json()).case.case_id;
  const content = Buffer.from(Object.entries(identity).map(([key, value]) => `${key}: ${value}\n${key}: OTHER SYNTHETIC VALUE`).join("\n"));
  expect((await page.request.post(`/api/clm/zero-touch/cases/${cid}/intake/documents`, { headers: { ...headers, "Content-Type": "text/plain", "X-Document-Name": "synthetic-isolation.txt" }, data: content })).status()).toBe(201);
  const completed = await page.request.post(`/api/clm/zero-touch/cases/${cid}/intake/complete`, { headers, data: { expected_document_count: 1 } });
  expect(completed.status()).toBe(200); const current = await completed.json();
  const docs = await (await page.request.get(`/api/onboarding/cases/${cid}/documents`)).json();
  const batch = { expected_automation_version: current.version, expected_case_event_count: current.case.events.length,
    documents: docs.map((doc: any) => ({ document_id: doc.document_id, expected_event_count: doc.events.length, source_fingerprint: doc.review_source_fingerprint,
      decisions: doc.fields.map((field: any) => ({ field_key: field.field_key, decision: "REJECTED" })) })) };
  await page.goto(`/cases/${cid}`); await openStage(page, "Document verification");
  const draft = page.locator("select[data-review-field]").first();
  const mutations: string[] = [];
  const listener = (request: import("@playwright/test").Request) => { if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method())) mutations.push(new URL(request.url()).pathname); };
  page.on("request", listener); await draft.selectOption("REJECTED");
  await page.getByRole("button", { name: "Save draft in this tab", exact: true }).click();
  await expect(page.getByText("Draft saved in this tab", { exact: false })).toBeVisible();
  expect(mutations).toEqual([]); page.off("request", listener);
  await signOut(); const otherHeaders = await signIn("ethan-tan");
  await page.goto(`/cases/${cid}`); await openStage(page, "Document verification");
  await expect(page.locator("select[data-review-field]").first()).toHaveValue("");
  for (const control of await page.locator("select[data-review-field]").all()) await expect(control).toBeDisabled();
  await expect(page.getByRole("button", { name: "Confirm decisions & continue onboarding", exact: true })).toBeDisabled();
  expect((await page.request.post(`/api/clm/zero-touch/cases/${cid}/review-decisions`, { headers: otherHeaders, data: batch })).status()).toBe(403);
  await signOut(); const crossHeaders = await signIn("sophia-ng");
  const unavailable = page.waitForResponse(response => new URL(response.url()).pathname === `/api/clm/zero-touch/cases/${cid}` && response.request().method() === "GET");
  await page.goto(`/cases/${cid}`); expect((await unavailable).status()).toBe(404);
  await expect(page.locator("#case-blocker-review")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Confirm decisions & continue onboarding", exact: true })).toHaveCount(0);
  expect((await page.request.post(`/api/clm/zero-touch/cases/${cid}/review-decisions`, { headers: crossHeaders, data: batch })).status()).toBe(404);
  await mkdir(evidence(), { recursive: true });
  await writeFile(path.join(evidence(), "simulation-authorization-isolation.json"), JSON.stringify({ scenario: "unauthorized/cross-team", initial: current.status,
    actual_control: "Creator draft select; same-team controls disabled; cross-team controls absent", choices: 1, calls_before_confirmation: 0,
    confirmation: "Same-team noncreator 403; cross-team 404", final: "No accepted review or target write", verdict: "PASS", draft_leak: false }, null, 2)+"\n");
  expect(violations).toEqual([]);
});

test("Blocker simulation actual native PDF intake failure targets retry and one continuation", { tag: "@slice-c-document-refresh" }, async ({ page }) => {
  const violations: string[] = [];
  const policy = createBrowserNetworkPolicy({ frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!, backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false });
  await page.route("**/*", route => handleBrowserRoute(route, policy, violations));
  await page.goto("/");
  const loggedIn = page.waitForResponse(response => response.url().endsWith("/api/auth/login") && response.request().method() === "POST");
  await page.getByLabel("User ID").fill("maya-lim"); await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  const headers = { "X-CSRF-Token": (await (await loggedIn).json()).csrf_token };
  const created = await page.request.post("/api/clm/zero-touch/cases", { headers, data: { uen: "202400001A" } });
  expect(created.status()).toBe(201); const cid = (await created.json()).case.case_id;
  await page.goto(`/cases/${cid}`); await openStage(page, "Document verification");
  await expect(page.getByText(/Synthetic offline document refresh recovery fixture/)).toBeVisible();
  // Six valid pages fit the media bounds but exceed the unchanged native text
  // limit during extraction. No provider stub or timeout/configuration change.
  const stream = "BT /F1 6 Tf 72 720 Td " + Array.from({ length: 100 }, () => `(SYNTHETIC ${"A".repeat(140)})`).join(" Tj 0 -6 Td ") + " Tj ET";
  const objects = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R 4 0 R 5 0 R 6 0 R 7 0 R 8 0 R] /Count 6 >>",
    ...Array.from({ length: 6 }, () => "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 9 0 R >> >> /Contents 10 0 R >>"),
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>", `<< /Length ${Buffer.byteLength(stream)} >>\nstream\n${stream}\nendstream`];
  let pdf = "%PDF-1.4\n"; const offsets = [0];
  for (const [index, object] of objects.entries()) { offsets.push(Buffer.byteLength(pdf)); pdf += `${index + 1} 0 obj\n${object}\nendobj\n`; }
  const xref = Buffer.byteLength(pdf);
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f\n` + offsets.slice(1).map(offset => `${String(offset).padStart(10, "0")} 00000 n\n`).join("");
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  const broken = { name: "synthetic-native-text-bound.pdf", mimeType: "application/pdf", buffer: Buffer.from(pdf) };
  const replacement = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/intake/documents"));
  await page.locator("#case-document-upload input[type=file]").setInputFiles(broken);
  expect((await replacement).status()).toBe(503);
  await expect(page.getByLabel("Retry affected document", { exact: true })).toBeEnabled();
  await page.goto(`/cases/${cid}?focus=DOCUMENT_IDP`);
  const retry = page.getByLabel("Retry affected document", { exact: true });
  await expect(retry).toBeFocused();
  await expect(page.locator("#case-document-upload")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Continue evidence review", exact: true })).toHaveCount(0);
  const failedRetry = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/retry"));
  await retry.setInputFiles(broken); expect((await failedRetry).status()).toBe(503);
  await expect(page.getByLabel("Retry affected document", { exact: true })).toBeEnabled();
  const retained = await (await page.request.get(`/api/clm/zero-touch/cases/${cid}`)).json();
  expect(retained.status).toBe("PENDING_INPUTS"); expect(retained.case.goldtier_result).toBeNull();
  const goodRetry = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/retry"));
  const fixture = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../backend/tests/fixtures/uat/clean-company-profile.pdf");
  await page.getByLabel("Retry affected document", { exact: true }).setInputFiles(fixture);
  expect((await goodRetry).status()).toBe(201);
  await expect(page.locator(".case-action-progress")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Continue evidence review", exact: true })).toHaveCount(0);
  const final = await (await page.request.get(`/api/clm/zero-touch/cases/${cid}`)).json();
  expect(final.status).toBe("WAITING_FOR_REVIEW"); expect(final.current_stage).toBe("READINESS");
  expect(final.case.target_dispatch_confirmation).toBeNull(); expect(final.case.goldtier_result).toBeNull();
  await mkdir(evidence(), { recursive: true });
  await writeFile(path.join(evidence(), "simulation-native-failed-retry.json"), JSON.stringify({ scenario: "failed document retry", initial: "Actual native extraction text bound / PENDING_INPUTS",
    actual_control: "Retry affected document INPUT:file; automatic owning continuation", choices: 0, calls_before_confirmation: 0,
    confirmation: "Initial intake 503, failed retry 503, valid native retry 201, automatic continuation with no Resume", final: final.active_exceptions.map((item: any) => item.blocker_code), verdict: "PASS", external_calls: 0 }, null, 2)+"\n");
  // Continue the same real case through a saved replacement / failed dependent
  // refresh. No browser response interception or direct recovery POST.
  await openStage(page, "Document verification");
  const replace = page.getByLabel("Replace current document", { exact: true });
  await expect(replace).toBeEnabled();
  const savedBefore = await (await page.request.get(`/api/onboarding/cases/${cid}/documents`)).json();
  const replacementRefresh = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/replacement"));
  await replace.setInputFiles(fixture);
  expect((await replacementRefresh).status()).toBe(503);
  await expect(page.getByRole("button", { name: "Resume document evidence refresh", exact: true })).toBeEnabled();
  const pending = await (await page.request.get(`/api/clm/zero-touch/cases/${cid}`)).json();
  expect(pending.status).toBe("RESUMING"); expect(pending.current_stage).toBe("DOCUMENT");
  expect(pending.document_refresh_recovery).toEqual({ can_resume: true });
  expect(pending.active_exceptions).toEqual([]); expect(pending.technical_failure).toBeNull();
  const saved = await (await page.request.get(`/api/onboarding/cases/${cid}/documents`)).json();
  const targetBeforeRecovery = await (await page.request.get("/api/__slice_c/document-refresh-metadata")).json();
  expect(targetBeforeRecovery.operations).toEqual(["SEARCH"]);
  expect(targetBeforeRecovery.refresh_attempts).toBe(1);
  expect(saved).toHaveLength(savedBefore.length + 1);
  const currentDocument = saved.filter((item: any) => item.superseded_by_document_id === null);
  expect(currentDocument).toHaveLength(1);
  expect(saved.find((item: any) => item.document_id === currentDocument[0].supersedes_document_id).superseded_by_document_id).toBe(currentDocument[0].document_id);
  await page.reload(); await openStage(page, "Document verification");
  const recovery = page.getByRole("button", { name: "Resume document evidence refresh", exact: true });
  await expect(recovery).toBeEnabled();
  await expect(page.getByText("Replacement saved; evidence refresh needs recovery.", { exact: true })).toBeVisible();
  await expect(page.locator(".processing-workspace__content[inert]")).toHaveCount(0);
  await expect(page.locator(".processing-workspace__overlay")).toHaveCount(0);
  await recovery.focus(); await expect(recovery).toBeFocused();
  const recoveredResponse = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/resume"));
  await recovery.click(); const recovered = await recoveredResponse;
  expect(recovered.status()).toBe(200);
  expect(recovered.request().headers()["x-automation-id"]).toBe(pending.automation_id);
  const after = await recovered.json();
  expect(after.document_refresh_recovery).toBeNull();
  expect(after.status).toBe("WAITING_FOR_REVIEW"); expect(after.current_stage).toBe("READINESS");
  expect(after.technical_failure).toBeNull();
  expect(after.clm.version).toBeGreaterThan(pending.clm.version);
  expect(after.active_exceptions.map((item: any) => item.blocker_code)).toEqual(["TARGET_CONFIRMATION_REQUIRED"]);
  expect(after.active_exceptions[0].exception_id).not.toBe(final.active_exceptions[0].exception_id);
  expect(after.case.goldtier_result).toBeNull();
  expect(after.case.initial_target_search).toEqual(pending.case.initial_target_search);
  expect(after.target_operations).toEqual(pending.target_operations);
  const targetAfterRecovery = await (await page.request.get("/api/__slice_c/document-refresh-metadata")).json();
  expect(targetAfterRecovery.operations).toEqual(["SEARCH"]);
  expect(targetAfterRecovery.refresh_attempts).toBe(2);
  expect(targetAfterRecovery.external_calls).toBe(0);
  expect((await (await page.request.get(`/api/onboarding/cases/${cid}/documents`)).json()).map((item: any) => item.document_id).sort()).toEqual(saved.map((item: any) => item.document_id).sort());
  await expect(recovery).toHaveCount(0);
  await writeFile(path.join(evidence(), "simulation-document-refresh-recovery.json"), JSON.stringify({ scenario: "saved replacement refresh 503",
    classification: "AUTOMATED_OFFLINE_SIMULATION", actual_control: "Visible enabled focused Resume document evidence refresh BUTTON after reload",
    checkpoint: "RESUMING/DOCUMENT", final_stage: after.current_stage, final_status: after.status,
    fresh_confirmation_required: true, response: 200, documents_before: savedBefore.length, documents_retained: saved.length,
    duplicate_documents: 0, retained_search_unchanged: true, target_operations_unchanged: true, verdict: "PASS" }, null, 2)+"\n");
  expect(violations).toEqual([]);
});

test("Blocker simulation unsupported initial country requires explicit Singapore correction", async ({ page }) => {
  const violations: string[] = [];
  const policy = createBrowserNetworkPolicy({ frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!, backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false });
  await page.route("**/*", route => handleBrowserRoute(route, policy, violations));
  await page.goto("/");
  const loggedIn = page.waitForResponse(response => response.url().endsWith("/api/auth/login") && response.request().method() === "POST");
  await page.getByLabel("User ID").fill("maya-lim"); await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  const headers = { "X-CSRF-Token": (await (await loggedIn).json()).csrf_token };
  const created = await page.request.post("/api/clm/zero-touch/cases", { headers, data: { uen: "MY-REG-123", legal_name: "SYNTHETIC MALAYSIA ENTITY", country_of_incorporation: "MY" } });
  expect(created.status()).toBe(201); const initial = await created.json(); const cid = initial.case.case_id;
  expect(initial.case.error.code).toBe("INITIAL_IDENTITY_NOT_ELIGIBLE");
  expect(initial.case.registry_route).toBeNull();
  expect(initial.target_operations.every((operation: any) => operation.status === "NOT_ATTEMPTED")).toBe(true);
  await page.goto(`/cases/${cid}`); await openStage(page, "Registry verification");
  await expect(page.getByRole("heading", { name: "Registry identity", exact: true })).toBeVisible();
  const detail = page.locator(".intervention-card .evidence-details").filter({ hasText: "INITIAL_IDENTITY_NOT_ELIGIBLE" });
  await detail.locator(":scope > summary").click();
  await expect(detail.locator(":scope > code")).toBeVisible();
  await expect(page.getByRole("button", { name: /enable.*provider|ignore.*continue|confirm and send/i })).toHaveCount(0);
  const mutations: string[] = [];
  page.on("request", request => { if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method())) mutations.push(new URL(request.url()).pathname); });
  await focusPipelineAction(page, "INITIAL_IDENTITY", page.locator("#identity-registration-number"));
  await expect(page.getByLabel("Country of incorporation", { exact: true })).toHaveValue("SG");
  expect(mutations).toEqual([]); expect(initial.case.goldtier_result).toBeNull();
  await mkdir(evidence(), { recursive: true });
  await writeFile(path.join(evidence(), "simulation-unsupported-registry.json"), JSON.stringify({ scenario: "unsupported initial country", initial: initial.case.error.code,
    actual_control: "Editable Singapore UEN; explicit fixed SG correction; no provider enablement", choices: 0, calls_before_confirmation: 0,
    confirmation: "No correction submitted; explicit SG identity required", final: initial.status, verdict: "PASS", target_calls: 0 }, null, 2)+"\n");
  expect(violations).toEqual([]);
});

test("Blocker simulation early stage click waits for the actual current document decision", async ({ page }) => {
  const violations: string[] = [];
  const policy = createBrowserNetworkPolicy({ frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!, backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false });
  await page.route("**/*", route => handleBrowserRoute(route, policy, violations));
  await page.goto("/");
  const loggedIn = page.waitForResponse(response => response.url().endsWith("/api/auth/login") && response.request().method() === "POST");
  await page.getByLabel("User ID").fill("maya-lim"); await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  const headers = { "X-CSRF-Token": (await (await loggedIn).json()).csrf_token };
  const created = await page.request.post("/api/clm/zero-touch/cases", { headers, data: { uen: "202400001A" } });
  expect(created.status()).toBe(201); const cid = (await created.json()).case.case_id;
  const content = Buffer.from(Object.entries({ ...identity, Country: "" }).map(([key, value]) => `${key}: ${value}`).join("\n"));
  expect((await page.request.post(`/api/clm/zero-touch/cases/${cid}/intake/documents`, { headers: { ...headers, "Content-Type": "text/plain", "X-Document-Name": "synthetic-delayed-review.txt" }, data: content })).status()).toBe(201);
  const started = await page.request.post(`/api/clm/zero-touch/cases/${cid}/intake/complete`, { headers, data: { expected_document_count: 1 } });
  expect(started.status()).toBe(200); const initial = await started.json();
  expect(initial.active_exceptions.some((item: any) => item.blocker_code === "DOCUMENT_REQUIRED_FIELD_MISSING")).toBe(true);
  let release!: () => void;
  let held = false;
  const delayedRead = new Promise<void>(resolve => { release = resolve; });
  await page.route(`**/api/onboarding/cases/${cid}/documents`, async route => {
    held = true; await delayedRead; await route.fallback();
  });
  const requests: string[] = [];
  page.on("request", request => { if (new URL(request.url()).pathname.startsWith("/api/")) requests.push(request.method()); });
  await page.goto(`/cases/${cid}`);
  await expect.poll(() => held).toBe(true);
  const node = page.locator('.ds-stage[data-node-id="DOCUMENT_IDP"]');
  await node.locator("summary").click();
  await node.getByRole("button", { name: "Open case stage details", exact: true }).click();
  await expect(page.locator("select[data-review-field]")).toHaveCount(0);
  release();
  const control = page.locator('select[data-review-field="country_of_incorporation"]');
  await expect(control).toBeVisible(); await expect(control).toBeEnabled(); await expect(control).toBeFocused();
  await expect(control).toBeInViewport({ ratio: 1 });
  const boundary = requests.length;
  await control.selectOption("REJECTED");
  expect(requests.slice(boundary)).toEqual([]);
  expect(requests.every(method => method === "GET")).toBe(true);
  expect(initial.case.goldtier_result).toBeNull();
  await mkdir(evidence(), { recursive: true });
  await writeFile(path.join(evidence(), "simulation-delayed-stage-focus.json"), JSON.stringify({ scenario: "early stage click with delayed actual document read",
    initial: initial.active_exceptions.map((item: any) => item.blocker_code), expected_navigation: "Current missing-country decision SELECT",
    actual_control: "SELECT:data-review-field=country_of_incorporation (visible, enabled, focused, in viewport)", choices: 1,
    calls_before_confirmation: 0, initial_reads: requests.length, confirmation: "Local draft only; no confirmation submitted",
    final: initial.active_exceptions.map((item: any) => item.blocker_code), verdict: "PASS", fabricated_response: false }, null, 2)+"\n");
  expect(violations).toEqual([]);
});
