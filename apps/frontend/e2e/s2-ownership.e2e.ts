import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test, type Page } from "@playwright/test";
import { createBrowserNetworkPolicy, handleBrowserRoute } from "../playwright.config";
import { focusPipelineAction, openStage, openStageSupport } from "./stage-disclosures";
import { showAllIssues } from "./attention";

const fixture = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../backend/tests/fixtures/uat/garden-business-clean-onboarding-profile.pdf");
let violations: string[];
test.beforeEach(async ({ page }) => {
  violations = [];
  const policy = createBrowserNetworkPolicy({ frontendOrigin: process.env.PLAYWRIGHT_BASE_URL!, backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false });
  await page.route("**/*", (route) => handleBrowserRoute(route, policy, violations));
});
test.afterEach(() => expect(violations).toEqual([]));
async function summary(page: Page, caseId: string) {
  const response = await page.request.get(`/api/clm/zero-touch/cases/${caseId}`); expect(response.status()).toBe(200); return response.json();
}
async function ownership(page: Page, caseId: string) {
  const response = await page.request.get(`/api/onboarding/cases/${caseId}/ownership`); expect(response.status()).toBe(200); return response.json();
}
async function createGarden(page: Page, customDocument?: { name: string; mimeType: string; buffer: Buffer }) {
  await page.goto("/");
  await page.getByLabel("User ID").fill("maya-lim"); await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("link", { name: "New onboarding", exact: true }).click();
  await page.getByLabel("Jurisdiction", { exact: true }).selectOption("SG");
  await page.getByLabel("Company Legal Name", { exact: true }).fill("GARDEN BUSINESS");
  await page.getByLabel("Registration ID / UEN").fill("11111999A");
  await page.locator("#home-document").setInputFiles(customDocument ?? fixture);
  await page.getByRole("button", { name: "Create onboarding", exact: true }).click();
  await expect(page).toHaveURL(/\/cases\/[0-9a-f-]{36}$/i);
  const caseId = page.url().split("/").at(-1)!;
  await expect.poll(async () => (await summary(page, caseId)).status).toBe("WAITING_FOR_REVIEW");
  await expect(page).toHaveURL(`/cases/${caseId}`);
  await expect(page.locator(".document-card:not(.document-card--history)")).toHaveCount(1);
  await openStage(page, "Submission readiness");
  for (const name of ["KYC customer type", "Client segment"]) {
    const control = page.getByLabel(name, { exact: true });
    const value = await control.locator("option").evaluateAll((options) => options.map((item) => (item as HTMLOptionElement).value).find(Boolean));
    await control.selectOption(value!);
  }
  const classification = page.waitForResponse((response) => response.request().method() === "PUT" && response.url().endsWith("/target-classification"));
  await page.getByRole("button", { name: "Save target classification", exact: true }).click(); expect((await classification).status()).toBe(200);
  await openStage(page, "Ownership & UBO");
  await expect(page.getByRole("heading", { name: "Review or edit ownership evidence", exact: true })).toBeVisible();
  return caseId;
}
async function submitDecision(page: Page) {
  const response = page.waitForResponse((result) => result.request().method() === "POST" && result.url().endsWith("/manual-ownership-evidence"), { timeout: 15_000 });
  await page.locator(".manual-ownership").getByRole("button", { name: "Submit manual ownership evidence", exact: true }).click();
  const result = await response; expect(result.status()).toBe(200); return result.json();
}

test("S2 creator edits calculable multi-level ownership before send and inspects exact collapsed calculations", { tag: "@garden-protocol" }, async ({ page }) => {
  const caseId = await createGarden(page);
  const form = page.locator(".manual-ownership");
  await expect(form.getByLabel("Economic interest %", { exact: true }).nth(0)).toHaveValue("62.500000");
  await expect(form.getByLabel("Owner type", { exact: true }).nth(0)).toHaveValue("LEGAL_ENTITY");
  while (await form.getByLabel("Owner name", { exact: true }).count() > 2) {
    await form.getByRole("button", { name: /^Remove owner/ }).last().click();
  }
  const singaporeToday = await page.evaluate(() => new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Singapore", year: "numeric", month: "2-digit", day: "2-digit",
  }).format(new Date()));
  await expect(form.getByLabel("As-of date")).toHaveValue(singaporeToday);
  await form.getByLabel("As-of date").fill("2026-10-04");
  await expect(form.getByLabel("Reviewer note (optional)")).toHaveValue("");
  for (const [index, percentage] of ["60", "40"].entries()) {
    await form.getByLabel("Owner name", { exact: true }).nth(index).fill(`Synthetic reviewed owner ${index + 1}`);
    await form.getByLabel("Owner type", { exact: true }).nth(index).selectOption("NATURAL_PERSON");
    await form.getByLabel("Registration number (optional)", { exact: true }).nth(index).fill("");
    await form.getByLabel("Economic interest %", { exact: true }).nth(index).fill(percentage);
  }
  await submitDecision(page);
  await expect(page.getByRole("button", { name: "Confirm and send to Mock GoldTier", exact: true })).toBeEnabled();
  const first = await ownership(page, caseId); expect(first.state).toBe("ANALYZED");
  expect(first.manual_review_receipt.rationale).toBeNull();
  expect((await summary(page, caseId)).ownership_edit_authorized).toBe(true);
  await page.getByRole("button", { name: "Edit ownership", exact: true }).click();
  await expect(page.locator("#case-manual-ownership-evidence :is(input:not([disabled]):not([readonly]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]))").first()).toBeFocused();
  await form.getByLabel("Owner type", { exact: true }).nth(0).selectOption("LEGAL_ENTITY");
  await form.getByLabel("Owner name", { exact: true }).nth(0).fill("Synthetic holding entity");
  await form.getByLabel("Registration number (optional)", { exact: true }).nth(0).fill("202400002B");
  await form.getByLabel("Economic interest %", { exact: true }).nth(0).fill("100");
  const holdingId = await form.getByLabel("Owner ID", { exact: true }).nth(0).inputValue();
  await form.getByLabel("Owned legal entity", { exact: true }).nth(1).selectOption(holdingId);
  await form.getByLabel("Economic interest %", { exact: true }).nth(1).fill("100");
  await form.getByLabel("As-of date").fill("2026-10-04");
  await form.getByLabel("Reviewer note (optional)").fill("Reviewed the explicit holding entity and its sole natural-person owner before submission.");
  await submitDecision(page);
  const revised = await ownership(page, caseId);
  expect(revised.analysis_id).not.toBe(first.analysis_id); expect(revised.state).toBe("ANALYZED");
  expect(revised.relationships.some((edge: any) => edge.parent_party_id === holdingId)).toBe(true);
  expect(revised.candidates[0].aggregated_ownership_percent).toMatch(/^100(?:\.0+)?$/);
  expect(revised.prior_analyses.some((prior: any) => prior.analysis_id === first.analysis_id && prior.manual_review_receipt.rationale === first.manual_review_receipt.rationale)).toBe(true);
  expect((await summary(page, caseId)).target_operations.filter((operation: any) => operation.operation !== "SEARCH").every((operation: any) => operation.status === "NOT_ATTEMPTED")).toBe(true);
  // Both current analysis rendering and the legitimate post-edit focus handoff
  // must complete before starting a separate ownership inspection action.
  await expect(page.locator(".s2-ownership-summary")).toContainText("1 retained natural-person candidate");
  await expect(page.getByRole("button", { name: "Confirm and send to Mock GoldTier", exact: true })).toBeFocused();
  await openStage(page, "Ownership & UBO");
  const disclosure = page.getByRole("region", { name: "Ownership & UBO", exact: true }).locator(":scope > details").filter({ has: page.getByText("Technical details — Ownership & UBO", { exact: true }) });
  await expect(disclosure).not.toHaveAttribute("open", "");
  await expect(disclosure.getByText(revised.candidates[0].paths[0].calculation, { exact: true })).toHaveCount(0);
  const toggle = disclosure.locator(":scope > summary");
  await toggle.focus();
  await expect(toggle).toBeFocused();
  await toggle.press("Enter");
  await expect(toggle).toBeFocused();
  await expect(disclosure).toHaveAttribute("open", "");
  await expect(disclosure.getByText(revised.candidates[0].paths[0].calculation, { exact: true }).first()).toBeVisible();
  for (const width of [320, 360, 720, 900, 1280, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(await page.evaluate(() => document.body.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
    await expect(toggle).toBeVisible();
  }
  await toggle.press("Enter");
  await expect(disclosure).not.toHaveAttribute("open", "");
  await expect(disclosure.getByText(revised.candidates[0].paths[0].calculation, { exact: true })).toHaveCount(0);
  await toggle.press("Space");
  await expect(disclosure.getByText(revised.candidates[0].paths[0].calculation, { exact: true }).first()).toBeVisible();
  // AM-18: retain a real incomplete legal-owner declaration with safe 409,
  // then use current backend versions for deliberate recovery. No target write.
  const beforeIncomplete = await summary(page, caseId);
  const oldConfirmationId = beforeIncomplete.active_exceptions.find((item: any) => item.blocker_code === "TARGET_CONFIRMATION_REQUIRED").exception_id;
  await focusPipelineAction(page, "OWNERSHIP_UBO", page.locator('#case-manual-ownership-evidence :is(input:not([disabled]):not([readonly]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]))').first());
  await form.getByRole("button", { name: /^Remove owner/ }).last().click();
  await form.getByLabel("Reviewer note (optional)").fill("");
  const rejected = page.waitForResponse((response) => response.request().method() === "POST" && response.url().endsWith("/manual-ownership-evidence"));
  await form.getByRole("button", { name: "Submit manual ownership evidence", exact: true }).click();
  const retainedError = await rejected;
  expect(retainedError.status()).toBe(409);
  expect((await retainedError.json()).detail.code).toBe("ZERO_TOUCH_MANUAL_OWNERSHIP_REVIEW_REQUIRED");
  const attention = page.getByRole("region", { name: "Attention required", exact: true });
  await expect(attention).toContainText("1 active blocker");
  await expect(attention).not.toContainText("No immediate blockers");
  await expect(attention.getByRole("button", { name: "Action: Review and send", exact: true })).toHaveCount(0);
  const progress = page.getByRole("heading", { name: "Onboarding progress", exact: true }).locator('..').locator('..').locator('..');
  await expect(progress).toContainText("Active issues: 1");
  await expect(progress).toContainText("Add structured ownership details");
  await expect(page.getByRole("button", { name: "Confirm and send to Mock GoldTier", exact: true })).toHaveCount(0);
  const blocked = await summary(page, caseId);
  const incomplete = await ownership(page, caseId);
  expect(blocked.current_stage).toBe("OWNERSHIP");
  expect(incomplete.state).toBe("REVIEW_REQUIRED");
  expect(incomplete.issues.some((issue: any) => issue.code === "INCOMPLETE_LEGAL_ENTITY")).toBe(true);
  expect(incomplete.relationships).toHaveLength(1);
  await expect(form.getByLabel("Owner name", { exact: true })).toHaveCount(1);
  expect(incomplete.manual_review_receipt.rationale).toBeNull();
  expect(blocked.clm.readiness.blockers).toContain("OWNERSHIP_REVIEW_REQUIRED");
  expect(blocked.active_exceptions.map((item: any) => item.blocker_code)).toEqual(["OWNERSHIP_INCOMPLETE"]);
  expect(blocked.historical_exceptions.some((item: any) => item.exception_id === oldConfirmationId)).toBe(true);
  expect(blocked.historical_exceptions.find((item: any) => item.exception_id === oldConfirmationId).status).toBe("CANCELLED");
  expect(blocked.metrics.exceptions_resolved).toBe(beforeIncomplete.metrics.exceptions_resolved);
  expect(blocked.active_exceptions[0].status).toBe("OPEN");
  expect(blocked.target_operations.filter((item: any) => item.operation !== "SEARCH").every((item: any) => item.status === "NOT_ATTEMPTED")).toBe(true);
  for (const width of [1440, 1280, 900, 360]) {
    await page.setViewportSize({ width, height: 1000 });
    await showAllIssues(page); await attention.getByRole("button", { name: /Add structured ownership details/ }).click();
    await expect(page.locator('#case-manual-ownership-evidence :is(input:not([disabled]):not([readonly]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]))').first()).toBeFocused();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  }
  await page.reload();
  await expect(attention).toContainText("1 active blocker");
  expect((await summary(page, caseId)).version).toBe(blocked.version);
  expect((await ownership(page, caseId)).analysis_id).toBe(incomplete.analysis_id);
  await focusPipelineAction(page, "OWNERSHIP_UBO", page.locator('#case-manual-ownership-evidence :is(input:not([disabled]):not([readonly]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]))').first());
  await expect(form.getByLabel("As-of date")).toHaveValue("2026-10-04");
  await form.getByRole("button", { name: "Add owner", exact: true }).click();
  await form.getByLabel("Owner name", { exact: true }).nth(1).fill("Synthetic corrected ultimate owner");
  await form.getByLabel("Owner type", { exact: true }).nth(1).selectOption("NATURAL_PERSON");
  await form.getByLabel("Owned legal entity", { exact: true }).nth(1).selectOption(holdingId);
  await form.getByLabel("Economic interest %", { exact: true }).nth(1).fill("100");
  await submitDecision(page);
  const recovered = await summary(page, caseId);
  expect(recovered.clm.readiness.blockers).toEqual([]);
  expect(recovered.current_stage).toBe("READINESS");
  expect(recovered.active_exceptions[0].exception_id).not.toBe(oldConfirmationId);
  expect(recovered.historical_exceptions.find((item: any) => item.exception_id === oldConfirmationId).status).toBe("CANCELLED");
  expect(recovered.historical_exceptions.find((item: any) => item.exception_id === blocked.active_exceptions[0].exception_id).status).toBe("RESOLVED");
  expect(recovered.metrics.exceptions_resolved).toBe(blocked.metrics.exceptions_resolved + 1);
  expect(recovered.target_classification).toEqual(beforeIncomplete.target_classification);
  expect((await ownership(page, caseId)).state).toBe("ANALYZED");
  await expect(attention).toContainText("No immediate blockers");
  await openStage(page, "Final review & send");
  const confirmation = page.waitForResponse((response) => response.request().method() === "POST" && response.url().endsWith("/target-confirmation"));
  await page.getByRole("button", { name: "Confirm and send to Mock GoldTier", exact: true }).click(); expect((await confirmation).status()).toBe(200);
  await expect.poll(async () => (await summary(page, caseId)).status).toBe("COMPLETED");
  expect((await summary(page, caseId)).ownership_edit_authorized).toBe(false);
  await expect(page.locator(".manual-ownership")).toHaveCount(0); await expect(page.getByRole("button", { name: "Edit ownership", exact: true })).toHaveCount(0);
});

test("S2 document proposals require deliberate creator source selection and retain immutable source bindings", { tag: "@garden-protocol" }, async ({ page }) => {
  const text = ["Legal Name: GARDEN BUSINESS", "UEN: 11111999A", "Registered Address: 18 GARDEN WALK, #01-01, 018919, SG", "Country: SG",
    "Shareholder: Synthetic document owner one | Type: NATURAL_PERSON | Percentage: 30% | Owned Entity: GARDEN BUSINESS | Owned Entity Registration Number: 11111999A | As Of: 2026-10-04",
    "Shareholder: Synthetic document owner two | Type: NATURAL_PERSON | Percentage: 70% | Owned Entity: GARDEN BUSINESS | Owned Entity Registration Number: 11111999A | As Of: 2026-10-04"].join("\n");
  const caseId = await createGarden(page, { name: "synthetic-ownership-proposals.txt", mimeType: "text/plain", buffer: Buffer.from(text, "utf8") });
  await expect.poll(async () => (await ownership(page, caseId)).document_observations.length).toBe(2);
  const proposed = await ownership(page, caseId); expect(proposed.state).toBe("REVIEW_REQUIRED");
  expect(proposed.document_observations.every((item: any) => item.decision_state === "PROPOSED" && item.document_version === 1)).toBe(true);
  await openStage(page, "Ownership & UBO");
  const form = page.locator(".manual-ownership");
  await form.getByLabel("Ownership source decision").selectOption("DOCUMENT_OBSERVATIONS");
  const choices = form.locator('input[type="checkbox"]'); await expect(choices).toHaveCount(2);
  await choices.nth(0).check(); await choices.nth(1).check();
  await expect(form.getByLabel("As-of date")).toHaveValue("2026-10-04");
  await expect(form.getByLabel("As-of date")).toHaveAttribute("readonly", "");
  await form.getByLabel("Reviewer note (optional)").fill("Selected both explicit synthetic document ownership percentages after comparing current source evidence.");
  await submitDecision(page);
  const revised = await ownership(page, caseId); expect(revised.manual_review_receipt.source_selection).toBe("DOCUMENT_OBSERVATIONS");
  expect([...revised.manual_review_receipt.selected_observation_ids].sort()).toEqual(proposed.document_observations.map((item: any) => item.observation_id).sort());
  expect(revised.manual_review_receipt.observed_document_versions).toEqual(proposed.document_bindings);
  expect(revised.document_observations).toEqual(proposed.document_observations);
  expect(revised.document_discrepancies.every((item: any) => item.verification_state === "REVIEWED")).toBe(true);
  expect(revised.prior_analyses.at(-1).document_observations).toEqual(proposed.document_observations);
  await openStage(page, "Document verification");
  await openStageSupport(page, "Document verification", "More");
  const proposals = page.getByText("Proposed ownership observations (2)", { exact: true }); await proposals.click();
  await openStageSupport(page, "Document verification", "Technical");
  await expect(page.getByText("Source agreement", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Evidence score", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Verification state", { exact: true }).first()).toBeVisible();
  expect((await summary(page, caseId)).status).not.toBe("COMPLETED");
});


// Gate browser animation frames only inside this test, preserving callback order,
// cancellation and native frame timestamps. No source-string matching or sleeps.
async function gateOwnershipReturnFrames(page: Page) {
  await page.evaluate(() => {
    const request = window.requestAnimationFrame.bind(window);
    const cancel = window.cancelAnimationFrame.bind(window);
    let next = -1;
    const callbacks = new Map<number, FrameRequestCallback>();
    window.requestAnimationFrame = (callback) => { const id = next--; callbacks.set(id, callback); return id; };
    window.cancelAnimationFrame = (id) => { if (!callbacks.delete(id)) cancel(id); };
    const advance = () => new Promise<void>((resolve) => request((timestamp) => {
      const current = [...callbacks];
      for (const [id, callback] of current) {
        if (!callbacks.delete(id)) continue;
        callback(timestamp);
      }
      resolve();
    }));
    (window as unknown as { s2FocusFrames: { pending: () => number; advance: () => Promise<void>; flush: () => Promise<void>; restore: () => void } }).s2FocusFrames = {
      pending: () => callbacks.size,
      advance,
      flush: async () => {
        for (let frame = 0; frame < 4 && callbacks.size; frame++) await advance();
        if (callbacks.size) throw new Error("Ownership focus exceeded its bounded frame chain");
      },
      restore: () => { callbacks.clear(); window.requestAnimationFrame = request; window.cancelAnimationFrame = cancel; },
    };
  });
}

for (const timing of ["queued return", "nested handoff"] as const) {
for (const interaction of ["keyboard", "pointer", "none"] as const) {
  test(`R3 ownership intent preserves ${interaction} focus against ${timing}`, { tag: "@garden-protocol" }, async ({ page }) => {
    const caseId = await createGarden(page);
    const form = page.locator(".manual-ownership");
    while (await form.getByLabel("Owner name", { exact: true }).count() > 2) {
      await form.getByRole("button", { name: /^Remove owner/ }).last().click();
    }
    for (const [index, percentage] of ["60", "40"].entries()) {
      await form.getByLabel("Owner name", { exact: true }).nth(index).fill(`Synthetic focus owner ${index + 1}`);
      await form.getByLabel("Owner type", { exact: true }).nth(index).selectOption("NATURAL_PERSON");
      await form.getByLabel("Registration number (optional)", { exact: true }).nth(index).fill("");
      await form.getByLabel("Economic interest %", { exact: true }).nth(index).fill(percentage);
    }
    await submitDecision(page);
    const first = await ownership(page, caseId);
    await expect(page.getByRole("button", { name: "Confirm and send to Mock GoldTier", exact: true })).toBeEnabled();
    await page.getByRole("button", { name: "Edit ownership", exact: true }).click();
    await expect(form.locator("input:not([disabled]):not([readonly]), select:not([disabled]), button:not([disabled])").first()).toBeFocused();
    const oldAnalysis = await page.getByRole("region", { name: "Ownership & UBO", exact: true }).locator(":scope > details").filter({ has: page.getByText("Technical details — Ownership & UBO", { exact: true }) }).locator(".ownership-support-panel").elementHandle();
    expect(oldAnalysis).not.toBeNull();
    await gateOwnershipReturnFrames(page);
    try {
      await submitDecision(page);
      const revised = await ownership(page, caseId);
      expect(revised.state).toBe("ANALYZED");
      expect(revised.analysis_id).not.toBe(first.analysis_id);
      await expect.poll(() => oldAnalysis!.evaluate((element) => element.isConnected)).toBe(false);
      await expect.poll(() => page.evaluate(() => (window as unknown as { s2FocusFrames: { pending: () => number } }).s2FocusFrames.pending())).toBeGreaterThan(0);
      if (timing === "nested handoff") {
        await page.evaluate(async () => {
          const gate = (window as unknown as { s2FocusFrames: { advance: () => Promise<void> } }).s2FocusFrames;
          await gate.advance();
          await gate.advance();
        });
        await expect.poll(() => page.evaluate(() => (window as unknown as { s2FocusFrames: { pending: () => number } }).s2FocusFrames.pending())).toBeGreaterThan(0);
      }
      const disclosure = page.getByRole("region", { name: "Ownership & UBO", exact: true }).locator(":scope > details").filter({ has: page.getByText("Technical details — Ownership & UBO", { exact: true }) });
      const toggle = disclosure.locator(":scope > summary");
      await expect(toggle).toBeVisible();
      await expect(disclosure).not.toHaveAttribute("open", "");
      if (interaction === "keyboard") {
        await toggle.focus();
        await expect(toggle).toBeFocused();
        await toggle.press("Enter");
      } else if (interaction === "pointer") {
        await toggle.click();
      }
      if (interaction !== "none") {
        await expect(toggle).toBeFocused();
        await expect(disclosure).toHaveAttribute("open", "");
      }
      await page.evaluate(() => (window as unknown as { s2FocusFrames: { flush: () => Promise<void> } }).s2FocusFrames.flush());
      if (interaction === "none") {
        await expect(page.getByRole("button", { name: "Confirm and send to Mock GoldTier", exact: true })).toBeFocused();
      } else {
        await expect(toggle).toBeFocused();
        await expect(disclosure).toHaveAttribute("open", "");
        await expect(disclosure.getByRole("table").first()).toBeVisible();
      }
      expect((await summary(page, caseId)).target_operations.filter((item: any) => item.operation !== "SEARCH").every((item: any) => item.status === "NOT_ATTEMPTED")).toBe(true);
    } finally {
      await page.evaluate(() => (window as unknown as { s2FocusFrames: { restore: () => void } }).s2FocusFrames.restore());
    }
  });
}
}
