import path from "node:path";
import fs from "node:fs";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import { expect, test, type Page } from "@playwright/test";
import { createBrowserNetworkPolicy, handleBrowserRoute, retainedEvidencePath } from "../playwright.config";
import { openStage } from "./stage-disclosures";
import { reviewPendingFields, reviewSourceChoices } from "./blocker-decisions";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const fixtures = path.join(root, "apps/backend/tests/fixtures/uat/zero-touch-database");
const happy = [
  { code: "aurora", name: "AURORA SYNTHETIC SIGNALS PTE. LTD.", uen: "202400019S", candidates: { AURORA_PERSON_A: "65", AURORA_PERSON_B: "35" } },
  { code: "pacific", name: "PACIFIC SYNTHETIC LEDGER PTE. LTD.", uen: "202400015O", candidates: { PACIFIC_OWNER_A: "40", PACIFIC_OWNER_B: "35", PACIFIC_OWNER_C: "25" } },
  { code: "straits", name: "STRAITS SYNTHETIC HOLDINGS PTE. LTD.", uen: "202400016P", candidates: { STRAITS_PERSON_A: "48", STRAITS_DIRECT: "40", STRAITS_PERSON_B: "12" } },
  { code: "meridian", name: "MERIDIAN SYNTHETIC INFRASTRUCTURE PTE. LTD.", uen: "202400017Q", candidates: { MERIDIAN_PERSON_A: "30", MERIDIAN_PERSON_B: "20", MERIDIAN_DIRECT_A: "30", MERIDIAN_DIRECT_B: "20" } },
];
const blocked = [
  { code: "garden", name: "GARDEN BUSINESS", uen: "11111999A", address: "306C XYZ LINK, #03-21, ABC GARDEN, 333333, SG" },
  { code: "merlion", name: "MERLION CIRCULAR LABS PTE. LTD.", uen: "202400001A", address: "18 INNOVATION WAY, #04-01, 018956, SG" },
  { code: "multiple", name: "MULTIPLE OWNER DEMO PTE. LTD.", uen: "202400008H", address: "18 SHAREHOLDER ROAD, #03-01, 049003, SG" },
  { code: "multilevel", name: "MULTI LEVEL OWNERSHIP DEMO PTE. LTD.", uen: "202400009I", address: "18 HIERARCHY WALK, #04-01, 049004, SG" },
];
type Company = { code: string; name: string; uen: string; address?: string };
type Upload = { name: string; mimeType: string; buffer: Buffer };

function nativePdf(fields: Record<string, string>): Upload {
  const lines = ["SYNTHETIC TEST DATA", "CORPORATE PROFILE", ...Object.entries(fields).map(([key, value]) => `${key}: ${value}`)];
  const escape = (line: string) => line.replaceAll("\\", "\\\\").replaceAll("(", "\\(").replaceAll(")", "\\)");
  const stream = "BT /F1 12 Tf 72 720 Td " + lines.map(line => `(${escape(line)})`).join(" Tj 0 -16 Td ") + " Tj ET";
  const objects = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>", `<< /Length ${Buffer.byteLength(stream, "latin1")} >>\nstream\n${stream}\nendstream`];
  let pdf = "%PDF-1.4\n"; const offsets: number[] = [];
  objects.forEach((object, index) => { offsets.push(Buffer.byteLength(pdf, "latin1")); pdf += `${index + 1} 0 obj\n${object}\nendobj\n`; });
  const xref = Buffer.byteLength(pdf, "latin1");
  pdf += "xref\n0 6\n0000000000 65535 f\n" + offsets.map(offset => `${String(offset).padStart(10, "0")} 00000 n\n`).join("");
  pdf += `trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return { name: "synthetic-sponsor-corporate-profile.pdf", mimeType: "application/pdf", buffer: Buffer.from(pdf, "latin1") };
}
function fields(company: Company) {
  return { "Legal Name": company.name, UEN: company.uen, "Registered Address": company.address!, Country: "SG",
    "KYC Customer Type": "Company - Private", "Client Segment": "Corporate" };
}
async function summary(page: Page, caseId: string) {
  const response = await page.request.get(`/api/clm/zero-touch/cases/${caseId}`); expect(response.status()).toBe(200); return response.json();
}
async function documents(page: Page, caseId: string) {
  return (await (await page.request.get(`/api/onboarding/cases/${caseId}/documents`)).json());
}
async function counts(page: Page) { return (await (await page.request.get("/api/__s3/sandbox-counts")).json()); }
function versions(current: any) {
  return { expected_automation_version: current.version, expected_clm_version: current.clm.version, expected_case_event_count: current.case.events.length };
}
async function login(page: Page, user = "maya-lim") {
  await page.goto("/");
  const signedIn = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/auth/login"));
  await page.getByLabel("User ID").fill(user); await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  expect((await signedIn).status()).toBe(200); return { "X-CSRF-Token": (await (await signedIn).json()).csrf_token };
}
async function create(page: Page, company: Company, upload: Upload, enteredUen = company.uen) {
  await page.getByRole("link", { name: "New onboarding", exact: true }).click();
  await page.getByLabel("Jurisdiction", { exact: true }).selectOption("SG");
  await page.getByLabel("Company Legal Name", { exact: true }).fill(company.name);
  await page.getByLabel("Registration ID / UEN").fill(enteredUen);
  await page.locator("#home-document").setInputFiles(upload);
  console.log("SPONSOR_DEMO_STAGE", company.code, "intake-filled");
  await page.getByRole("button", { name: "Create onboarding", exact: true }).click();
  await expect(page).toHaveURL(/\/cases\/[0-9a-f-]{36}$/i);
  const cid = page.url().split("/").at(-1)!;
  const createdState = await summary(page, cid);
  console.log("SPONSOR_DEMO_STAGE", company.code, "case-created", createdState.status, createdState.current_stage, createdState.active_exceptions.map((e: any) => e.blocker_code));
  await expect.poll(async () => (await summary(page, cid)).status).toBe("WAITING_FOR_REVIEW");
  await expect(page).toHaveURL(`/cases/${cid}`);
  await expect(page.locator(".document-card:not(.document-card--history)")).toHaveCount(1);
  return cid;
}

async function currentKnownReview(page: Page, cid: string, checkpoints: any[]) {
  let current = await summary(page, cid);
  if (current.current_stage === "DOCUMENT") {
    await openStage(page, "Document verification");
    const doc = (await documents(page, cid)).find((d: any) => !d.superseded_by_document_id);
    if (doc.state === "REVIEW_REQUIRED" && !doc.semantic_completion && doc.fields.some((f: any) => f.review_status === "PENDING")) await reviewPendingFields(page);
    current = await summary(page, cid);
    if (current.current_stage === "DOCUMENT" && current.reconciliation?.discrepancies.some((d: any) => d.status === "OPEN" && d.allowed_actions.includes("KEEP_REGISTRY_VALUE"))) await reviewSourceChoices(page);
    current = await summary(page, cid);
    checkpoints.push({ stage: current.current_stage, blockers: current.active_exceptions.map((e: any) => e.blocker_code), version: current.version });
  }
  if (current.active_exceptions.some((e: any) => e.blocker_code === "GOLDTIER_CLASSIFICATION_REQUIRED")) {
    await openStage(page, "Submission readiness");
    await page.getByLabel("KYC customer type", { exact: true }).selectOption("Company - Private");
    await page.getByLabel("Client segment", { exact: true }).selectOption("Corporate");
    const saved = page.waitForResponse(r => r.request().method() === "PUT" && r.url().endsWith("/target-classification"));
    await page.getByRole("button", { name: "Save target classification", exact: true }).click();
    expect((await saved).status()).toBe(200); await expect(page.locator(".case-action-progress")).toHaveCount(0);
    current = await summary(page, cid); checkpoints.push({ stage: current.current_stage, blockers: current.active_exceptions.map((e: any) => e.blocker_code), version: current.version });
  }
}
async function finish(page: Page, company: Company, cid: string, headers: Record<string, string>, receipt: any) {
  const evidence = retainedEvidencePath("sponsor-demo");
  await expect.poll(async () => (await summary(page, cid)).active_exceptions.map((e: any) => e.blocker_code)).toEqual(["TARGET_CONFIRMATION_REQUIRED"]);
  const current = await summary(page, cid); const doc = (await documents(page, cid)).find((d: any) => !d.superseded_by_document_id);
  expect(current.case.entity.registration_number).toBe(company.uen);
  expect(current.clm.readiness.blockers).toEqual([]); expect(current.case.target_dispatch_confirmation).toBeNull();
  const before = await counts(page); expect(before.calls.SHELL + before.calls.POLICY + before.calls.AMEND).toBe(0);
  const stale = await page.request.post(`/api/clm/zero-touch/cases/${cid}/target-confirmation`, { headers, data: { ...versions(current), expected_automation_version: current.version - 1 } });
  expect(stale.status()).toBe(409); expect((await counts(page)).calls).toEqual(before.calls);
  const other = await page.context().browser()!.newContext({ baseURL: process.env.PLAYWRIGHT_BASE_URL });
  const otherViolations: string[] = [];
  const otherPolicy = createBrowserNetworkPolicy({ frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!, backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false });
  await other.route("**/*", route => handleBrowserRoute(route, otherPolicy, otherViolations));
  try {
    const otherPage = await other.newPage(); const otherHeaders = await login(otherPage, "ethan-tan");
    const unauthorized = await otherPage.request.post(`/api/clm/zero-touch/cases/${cid}/documents/${doc.document_id}/replacement`, {
      headers: { ...otherHeaders, "Content-Type": "application/pdf", "X-Document-Name": "unauthorized-synthetic.pdf", "X-Document-Event-Count": String(doc.events.length) }, data: nativePdf({}).buffer,
    });
    expect(unauthorized.status()).toBe(403); receipt.unauthorized_status = unauthorized.status();
    const unauthorizedClassification = await otherPage.request.put(`/api/clm/zero-touch/cases/${cid}/target-classification`, {
      headers: otherHeaders, data: { kyc_customer_type: "Company - Private", client_segment: "Corporate",
        expected_automation_version: current.version, expected_case_event_count: current.case.events.length },
    });
    expect(unauthorizedClassification.status()).toBe(403); receipt.unauthorized_classification_status = unauthorizedClassification.status();
  } finally { await other.close(); }
  expect(otherViolations).toEqual([]);
  expect((await counts(page)).calls).toEqual(before.calls);
  await openStage(page, "Final review & send");
  const send = page.getByRole("button", { name: "Confirm and send to GoldTier sandbox", exact: true }); await expect(send).toBeEnabled();
  fs.mkdirSync(evidence, { recursive: true });
  await page.screenshot({ path: path.join(evidence, `${company.code}-final-review.png`), fullPage: true });
  await openStage(page, "GoldTier submission package");
  const preview = current.clm.submission_plan.request_preview;
  expect(preview.dispatch_ready).toBe(true);
  await openStage(page, "Final review & send");
  const sent = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/target-confirmation"));
  await send.click(); expect((await sent).status()).toBe(200);
  await expect.poll(async () => (await summary(page, cid)).status).toBe("COMPLETED");
  const done = await summary(page, cid); const completedCounts = await counts(page);
  expect(done.target_submission.state).toBe("SUBMISSION_CONFIRMED");
  expect(done.case.goldtier_result.readback_status).toBe("VERIFIED");
  expect(done.case.goldtier_result.readback_party_id).toBe(done.case.goldtier_result.party_id);
  expect(completedCounts.calls).toEqual({ SEARCH: before.calls.SEARCH + 1, SHELL: 1, POLICY: 1, AMEND: 0, READBACK: 1 });
  const frozenReplacement = await page.request.post(`/api/clm/zero-touch/cases/${cid}/documents/${doc.document_id}/replacement`, {
    headers: { ...headers, "Content-Type": "application/pdf", "X-Document-Name": "frozen-synthetic.pdf", "X-Document-Event-Count": String(doc.events.length),
      "X-Automation-Version": String(done.version), "X-Clm-Version": String(done.clm.version), "X-Case-Event-Count": String(done.case.events.length) }, data: nativePdf({}).buffer,
  });
  expect(frozenReplacement.status()).toBe(409);
  const frozenClassification = await page.request.put(`/api/clm/zero-touch/cases/${cid}/target-classification`, {
    headers, data: { kyc_customer_type: "Company - Private", client_segment: "Corporate",
      expected_automation_version: done.version, expected_case_event_count: done.case.events.length },
  });
  expect(frozenClassification.status()).toBe(409);
  receipt.frozen_replacement_status = frozenReplacement.status(); receipt.frozen_classification_status = frozenClassification.status();
  await page.reload(); await openStage(page, "GoldTier submission package");
  await expect(page.getByText("Completed POC workflow", { exact: true })).toBeVisible();
  expect((await counts(page)).calls).toEqual(completedCounts.calls);
  expect((await summary(page, cid)).target_operations).toEqual(done.target_operations);
  await page.screenshot({ path: path.join(evidence, `${company.code}-completed.png`), fullPage: true });
  const retainedDocuments = await documents(page, cid);
  const retainedOwnership = await (await page.request.get(`/api/onboarding/cases/${cid}/ownership`)).json();
  const evaluationCounts: Record<string, number> = {};
  for (const event of done.timeline ?? []) evaluationCounts[event.code] = (evaluationCounts[event.code] ?? 0) + 1;
  Object.assign(receipt, { company: company.name, uen: company.uen, case_id: cid, evidence: "AUTOMATED_OFFLINE_SIMULATION", real_sandbox_uat: "NOT_VERIFIED",
    registry: { status: current.case.registry_acquisition.status, binding: current.case.registry_evidence_binding }, initial_search: current.clm.target_search_checkpoint.disposition,
    final_review_version: current.version, clm_version: current.clm.version, readiness: current.clm.readiness, target_before: before.calls, target_after: completedCounts.calls,
    stale_status: stale.status(), document_states: (await documents(page, cid)).map((d: any) => ({ id: d.document_id, state: d.state, current: !d.superseded_by_document_id, completion_method: d.completion_method })),
    final_status: done.status, submission_state: done.target_submission.state, exact_readback_id: done.case.goldtier_result.readback_party_id, reopen_mutations: 0, verdict: "PASS" });
  Object.assign(receipt, {
    document_evidence: retainedDocuments.map((d: any) => ({ document_id: d.document_id, state: d.state,
      supersedes: d.supersedes_document_id, superseded_by: d.superseded_by_document_id, semantic_completion: d.semantic_completion,
      event_count: d.events.length, fields: d.fields.map((f: any) => ({ field: f.field_key, decision: f.review_status,
        comparison: f.comparison_status, method: f.extraction_method, quality: f.extraction_quality, score: f.confidence,
        score_kind: f.score_kind, formula: f.score_formula, page: f.provenance.page_number,
        references: f.candidates.map((c: any) => c.source_reference) })) })),
    classification: current.target_classification, preview_ready: preview.dispatch_ready,
    ownership_state: retainedOwnership.state, ownership_version: retainedOwnership.version,
    ownership_source_classification: retainedOwnership.source_classification, ownership_provider: retainedOwnership.provider_name,
    ownership_source_environment: retainedOwnership.provider_environment,
    ownership_review: retainedOwnership.manual_review_receipt ? { source_selection: retainedOwnership.manual_review_receipt.source_selection,
      actor: retainedOwnership.manual_review_receipt.actor_id, document_id: retainedOwnership.manual_review_receipt.evidence_document_id } : null,
    ownership_results: retainedOwnership.candidates.map((c: any) => ({ party_id: c.party.party_id,
      direct: c.direct_ownership_percent, indirect: c.indirect_ownership_percent, effective: c.aggregated_ownership_percent, classification: c.classification })),
    source_decisions: current.reconciliation?.discrepancies.map((d: any) => ({ field: d.field_name, status: d.status, decision: d.decision })) ?? [],
    evaluation_counts: evaluationCounts, metrics: done.metrics, target_operations: done.target_operations,
  });
  fs.writeFileSync(path.join(evidence, `${company.code}.json`), JSON.stringify(receipt, null, 2));
}

function happyJourney(company: typeof happy[number]) {
  return async ({ page }: { page: Page }) => {
    const violations: string[] = []; const mutations: string[] = [];
    const policy = createBrowserNetworkPolicy({ frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!, backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false });
    await page.route("**/*", route => handleBrowserRoute(route, policy, violations));
    page.on("request", request => { if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method()) && /\/api\/(clm|onboarding)\//.test(request.url())) mutations.push(new URL(request.url()).pathname); });
    const headers = await login(page); const filename = `${company.code}-sponsor-demo-registry-annex.pdf`; const buffer = fs.readFileSync(path.join(fixtures, filename));
    const cid = await create(page, company, { name: filename, mimeType: "application/pdf", buffer });
    const current = await summary(page, cid); const docs = await documents(page, cid);
    expect(current.metrics.human_interventions).toBe(0);
    expect(docs[0].completion_method).toBe("AUTO_CONFIRMED");
    expect(docs[0].fields.every((f: any) => f.review_status === "ACCEPTED" && f.comparison_status === "MATCH" && f.extraction_method === "NATIVE_PDF_TEXT" && f.extraction_quality === "HIGH")).toBe(true);
    expect(docs[0].ownership_observations).toEqual([]);
    expect(current.case.registry_evidence_binding.synthetic_seed_namespace).toBe("LOCAL_SYNTHETIC_UAT_V1");
    expect(current.case.registry_acquisition.operation_results.map((r: any) => r.status)).toEqual(["COMPLETE", "COMPLETE", "COMPLETE", "COMPLETE"]);
    expect(current.target_classification.kyc_customer_type.selection.source).toBe("DOCUMENT"); expect(current.target_classification.client_segment.selection.source).toBe("DOCUMENT");
    const owned = await (await page.request.get(`/api/onboarding/cases/${cid}/ownership`)).json(); expect(owned.state).toBe("ANALYZED"); expect(owned.manual_review_receipt).toBeNull();
    expect(Object.fromEntries(owned.candidates.map((c: any) => [c.party.party_id, Number(c.aggregated_ownership_percent)]))).toEqual(Object.fromEntries(Object.entries(company.candidates).map(([key, value]) => [key, Number(value)])));
    expect(mutations.filter(p => /review-decisions|manual-ownership|target-classification|replacement|identity-/.test(p))).toEqual([]);
    expect((await counts(page)).marketplace_calls).toEqual([]);
    await finish(page, company, cid, headers, { track: "B", document: filename, document_sha256: createHash("sha256").update(buffer).digest("hex"), intermediate_human_interventions: 0, intermediate_mutations: mutations.slice(), ownership: owned.candidates.map((c: any) => ({ party_id: c.party.party_id, direct: c.direct_ownership_percent, indirect: c.indirect_ownership_percent, effective: c.aggregated_ownership_percent, classification: c.classification })) });
    expect(violations).toEqual([]);
  };
}

function blockerJourney(company: typeof blocked[number]) {
  return async ({ page }: { page: Page }) => {
    const violations: string[] = []; const mutations: string[] = []; const checkpoints: any[] = [];
    const policy = createBrowserNetworkPolicy({ frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!, backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false });
    await page.route("**/*", route => handleBrowserRoute(route, policy, violations));
    page.on("request", request => { if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method()) && /\/api\/(clm|onboarding)\//.test(request.url())) {
      mutations.push(new URL(request.url()).pathname); console.log("SPONSOR_DEMO_MUTATION", request.method(), new URL(request.url()).pathname);
    } });
    const headers = await login(page); let source = fields(company);
    if (["garden", "multiple"].includes(company.code)) source = { ...source, "Legal Name": "INCORRECT SYNTHETIC DOCUMENT NAME", "Registered Address": "999 SYNTHETIC SOURCE ROAD, 999999, SG" };
    if (company.code === "multilevel") delete (source as Partial<typeof source>).Country;
    const upload = nativePdf(source); const cid = await create(page, company, upload, company.code === "merlion" ? "202499998Y" : company.uen);
    const original = (await documents(page, cid))[0]; const initial = await summary(page, cid);
    console.log("SPONSOR_DEMO_STAGE", company.code, "initial", initial.current_stage, initial.active_exceptions.map((e: any) => e.blocker_code));
    checkpoints.push({ stage: initial.current_stage, blockers: initial.active_exceptions.map((e: any) => e.blocker_code), version: initial.version });
    expect(initial.active_exceptions.some((e: any) => e.blocker_code !== "TARGET_CONFIRMATION_REQUIRED")).toBe(true);
    if (company.code === "merlion") {
      await openStage(page, "Registry verification");
      const corrected = page.waitForResponse(r => r.request().method() === "POST" && r.url().endsWith("/registry-identity"));
      // UEN conflict: choose the document UEN in the "UEN to verify" choice, then confirm.
      const documentChoice = page.getByRole("radio", { name: /^Document UEN/ });
      if (await documentChoice.count()) {
        await documentChoice.check();
        await page.getByRole("button", { name: "Confirm UEN and resume", exact: true }).click();
      } else {
        await page.getByRole("button", { name: "Edit UEN", exact: true }).click();
        await page.locator("#identity-registration-number").fill(company.uen);
        await page.getByRole("button", { name: "Verify UEN and resume", exact: true }).click();
      }
      expect((await corrected).status()).toBe(200); await expect(page.locator(".case-action-progress")).toHaveCount(0);
      await expect.poll(async () => (await summary(page, cid)).case.entity?.registration_number).toBe(company.uen);
      expect((await documents(page, cid))[0].document_id).toBe(original.document_id);
      await currentKnownReview(page, cid, checkpoints);
      await expect.poll(async () => (await summary(page, cid)).active_exceptions.map((e: any) => e.blocker_code)).toEqual(["TARGET_CONFIRMATION_REQUIRED"]);
      await openStage(page, "Final review & send"); await page.getByRole("button", { name: "Edit company details", exact: true }).click();
      const uen = page.locator("#identity-registration-number"); await expect(uen).toBeFocused(); await expect(uen).toHaveValue(company.uen);
      const unchanged = mutations.length; await uen.fill("INVALID-UEN"); await page.getByRole("button", { name: "Verify UEN and resume", exact: true }).click();
      await expect(page.locator(".identity-correction [role=alert]")).toContainText("Singapore UEN"); expect(mutations.length).toBe(unchanged);
      await uen.fill(company.uen); const verified = page.waitForResponse(r => r.request().method() === "POST" && r.url().endsWith("/registry-identity"));
      await page.getByRole("button", { name: "Verify UEN and resume", exact: true }).click(); expect((await verified).status()).toBe(200);
      await expect(page.locator(".case-action-progress")).toHaveCount(0); await currentKnownReview(page, cid, checkpoints);
    } else if (company.code === "multilevel") {
      await openStage(page, "Document verification"); const input = page.locator(".document-card:not(.document-card--history) input[type=file]"); await input.focus(); await expect(input).toBeFocused();
      const replaced = page.waitForResponse(r => r.request().method() === "POST" && r.url().endsWith("/replacement")); await input.setInputFiles(nativePdf(fields(company))); expect((await replaced).status()).toBe(200);
      await expect.poll(async () => (await summary(page, cid)).active_exceptions.map((e: any) => e.blocker_code)).toEqual(["TARGET_CONFIRMATION_REQUIRED"]);
      await openStage(page, "Final review & send"); await page.getByRole("button", { name: "Edit documents", exact: true }).click();
      const currentInput = page.locator(".document-card:not(.document-card--history) input[type=file]"); await expect(currentInput).toBeFocused();
      const revised = page.waitForResponse(r => r.request().method() === "POST" && r.url().endsWith("/replacement"));
      await currentInput.setInputFiles(nativePdf({ ...fields(company), "Client Segment": "Commercial BB (Business Banking)" })); expect((await revised).status()).toBe(200);
      await expect.poll(async () => (await summary(page, cid)).target_classification.client_segment.selected_value).toBe("Commercial BB (Business Banking)");
    } else {
      await openStage(page, "Document verification");
      console.log("SPONSOR_DEMO_STAGE", company.code, "document-controls-opened");
      const currentDocument = (await documents(page, cid))[0];
      console.log("SPONSOR_DEMO_REVIEW_CONTROLS", company.code, currentDocument.state, currentDocument.semantic_completion, await page.locator('input[data-review-field][value="REJECTED"]').count(), await page.locator('input[data-reconciliation-field][value="KEEP_REGISTRY_VALUE"]').count());
      console.log("SPONSOR_DEMO_REVIEW_AUTH", company.code, (await summary(page, cid)).evidence_decision_authorized,
        await page.locator('input[data-review-field][value="REJECTED"]').evaluateAll(items => items.map(item => ({ field: item.getAttribute('data-review-field'), disabled: (item as HTMLSelectElement).disabled }))));
      if (await page.locator('input[data-review-field][value="REJECTED"]').count()) await expect(page.locator('input[data-review-field][value="REJECTED"]').first()).toBeEnabled();
      if (currentDocument.state === "REVIEW_REQUIRED" && !currentDocument.semantic_completion
        && currentDocument.fields.some((f: any) => f.review_status === "PENDING")) { const reviewed = await reviewPendingFields(page); checkpoints.push({ stage: reviewed.current_stage, blockers: reviewed.active_exceptions.map((e: any) => e.blocker_code), version: reviewed.version }); }
      const resolved = await reviewSourceChoices(page); checkpoints.push({ stage: resolved.current_stage, blockers: resolved.active_exceptions.map((e: any) => e.blocker_code), version: resolved.version });
      console.log("SPONSOR_DEMO_STAGE", company.code, "source-group-confirmed", resolved.current_stage, resolved.active_exceptions.map((e: any) => e.blocker_code));
      if (company.code === "garden") { expect(resolved.case.registry_acquisition.status).toBe("PARTIAL"); expect(resolved.case.registry_acquisition.relationships).toEqual([]); }
      if (resolved.active_exceptions.some((e: any) => e.blocker_code === "GOLDTIER_CLASSIFICATION_REQUIRED")) {
        await openStage(page, "Submission readiness");
        await page.getByLabel("KYC customer type", { exact: true }).selectOption("Company - Private");
        await page.getByLabel("Client segment", { exact: true }).selectOption("Corporate");
        const classified = page.waitForResponse(r => r.request().method() === "PUT" && r.url().endsWith("/target-classification"));
        await page.getByRole("button", { name: "Save target classification", exact: true }).click();
        expect((await classified).status()).toBe(200); await expect(page.locator(".case-action-progress")).toHaveCount(0);
        const refreshed = await summary(page, cid); checkpoints.push({ stage: refreshed.current_stage, blockers: refreshed.active_exceptions.map((e: any) => e.blocker_code), version: refreshed.version });
      }
      await expect.poll(async () => (await summary(page, cid)).active_exceptions.map((e: any) => e.blocker_code)).toEqual(["TARGET_CONFIRMATION_REQUIRED"]);
      await openStage(page, "Final review & send");
      if (company.code === "multiple") {
        await page.getByRole("button", { name: "Edit classification", exact: true }).click(); await expect(page.getByLabel("KYC customer type", { exact: true })).toBeFocused();
        await expect(page.getByLabel("Client segment", { exact: true })).toHaveValue("Corporate");
        const saved = page.waitForResponse(r => r.request().method() === "PUT" && r.url().endsWith("/target-classification"));
        await page.getByRole("button", { name: "Save target classification", exact: true }).click(); expect((await saved).status()).toBe(200);
      } else {
        await page.getByRole("button", { name: "Edit ownership", exact: true }).click();
        console.log("SPONSOR_DEMO_STAGE", company.code, "final-review-ownership-opened");
        const form = page.locator(".manual-ownership"); await expect(form).toBeVisible();
        await expect(form.locator("input:not([disabled]):not([readonly]), select:not([disabled]), textarea:not([disabled]), button:not([disabled])").first()).toBeFocused();
        while (await form.getByLabel("Owner name", { exact: true }).count() > 2) await form.getByRole("button", { name: /^Remove owner/ }).last().click();
        for (const [index, value] of ["60", "40"].entries()) {
          await form.getByLabel("Owner name", { exact: true }).nth(index).fill(`Synthetic reviewed sponsor owner ${index + 1}`);
          await form.getByLabel("Owner type", { exact: true }).nth(index).selectOption("NATURAL_PERSON");
          await form.getByLabel("Registration number (optional)", { exact: true }).nth(index).fill("");
          await form.getByLabel("Economic interest %", { exact: true }).nth(index).fill(value);
        }
        await form.getByLabel("As-of date").fill("2026-10-10");
        console.log("SPONSOR_DEMO_STAGE", company.code, "ownership-draft-filled");
        const saved = page.waitForResponse(r => r.request().method() === "POST" && r.url().endsWith("/manual-ownership-evidence"));
        await form.getByRole("button", { name: "Submit manual ownership evidence", exact: true }).click(); expect((await saved).status()).toBe(200);
        console.log("SPONSOR_DEMO_STAGE", company.code, "ownership-confirmed");
      }
    }
    await finish(page, company, cid, headers, { track: "A", document: upload.name, document_sha256: createHash("sha256").update(upload.buffer).digest("hex"), original_document_id: original.document_id, initial_blockers: initial.active_exceptions.map((e: any) => e.blocker_code), checkpoints, draft_mutations: 0, actions: mutations.slice(), final_review_edit: { garden: "ownership", merlion: "identity re-verification", multiple: "classification", multilevel: "document replacement and classification refresh" }[company.code] });
    expect(violations).toEqual([]);
  };
}

// Distinct source locations let the existing lifecycle scheduler isolate each mode.
test("Sponsor happy path aurora has zero intermediate interventions and guarded Sandbox completion", { tag: "@s3-sandbox-sponsor-aurora" }, happyJourney(happy[0]));
test("Sponsor happy path pacific has zero intermediate interventions and guarded Sandbox completion", { tag: "@s3-sandbox-sponsor-pacific" }, happyJourney(happy[1]));
test("Sponsor happy path straits has zero intermediate interventions and guarded Sandbox completion", { tag: "@s3-sandbox-sponsor-straits" }, happyJourney(happy[2]));
test("Sponsor happy path meridian has zero intermediate interventions and guarded Sandbox completion", { tag: "@s3-sandbox-sponsor-meridian" }, happyJourney(happy[3]));
test("Sponsor blocker journey garden recovers through current controls and guarded Sandbox completion", { tag: "@s3-sandbox-sponsor-garden" }, blockerJourney(blocked[0]));
test("Sponsor blocker journey merlion recovers through current controls and guarded Sandbox completion", { tag: "@s3-sandbox-sponsor-merlion" }, blockerJourney(blocked[1]));
test("Sponsor blocker journey multiple recovers through current controls and guarded Sandbox completion", { tag: "@s3-sandbox-sponsor-multiple" }, blockerJourney(blocked[2]));
test("Sponsor blocker journey multilevel recovers through current controls and guarded Sandbox completion", { tag: "@s3-sandbox-sponsor-multilevel" }, blockerJourney(blocked[3]));
