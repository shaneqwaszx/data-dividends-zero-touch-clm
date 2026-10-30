import { createServer } from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";
import { expect, test } from "@playwright/test";
import { createBrowserNetworkPolicy, handleBrowserRoute } from "../playwright.config";

// Real Chromium rendering the actual panel and the Knowledge Review tab against a synthetic
// assistant API. The fixture is synthetic; it grants no backend authority or Live-model claim.
// The fake service keeps the conversation contract (D-104): End conversation must name the
// conversation the stream returned, and only the record linked to its request is served.
test("answer records: RM ends the conversation unsatisfied, and Support reviews it", async ({ page }) => {
  test.setTimeout(45000);
  page.setDefaultTimeout(8000);
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.name));
  const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
  const compiled = await build({
    stdin: { contents: `
      import React, {useState} from "react";
      import {createRoot} from "react-dom/client";
      import Panel from "./src/pages/AiAssistantPanel";
      import KnowledgeReview from "./src/pages/KnowledgeReview";
      function App() {
        const [support, setSupport] = useState(false);
        return support
          ? <KnowledgeReview />
          : <><button onClick={()=>setSupport(true)}>Sign in as Support</button>
              <Panel caseId="case-one" onOpenCases={()=>{}} /></>;
      }
      createRoot(document.getElementById("root")).render(<App/>);
    `, loader: "tsx", resolveDir: root },
    bundle: true, write: false, format: "esm", outfile: "client.js", jsx: "automatic",
    define: { "import.meta.env": "{}" },
  });
  const script = compiled.outputFiles!.find((file) => file.path.endsWith("client.js"))!.text;
  const css = compiled.outputFiles!.find((file) => file.path.endsWith("client.css"))?.text ?? "";

  const question = "Explain the registered address difference";
  const answerId = "Ab3_dE5-gH7iJ9kL1mN2oP";
  const conversationId = "Cv3_dE5-gH7iJ9kL1mN2oP";
  const allowed = [
    { text: "Registry and document differences require the current case decision; neither source automatically overrides the other.", source: "policy" },
    { text: 'The current case offers "Keep registry value".', source: "case" },
  ];
  const shownAnswer = "The registered address comes from ACRA.";
  const notice = "The model response could not be verified, so this answer comes from the case data.";
  const record = {
    answer_id: answerId, case_id: "case-one", created_at: "2026-10-25T00:00:00+00:00", question,
    earlier_answer_ids: [],
    case_snapshot: { blocker_codes: ["DOCUMENT_SOURCE_CONFLICT"], stage: "Documents", steps_done: 3, steps_total: 10, facts_hash: "f".repeat(64) },
    knowledge: { confidence: "none", degraded: false, thresholds: { guidance: 0.3, resolution: 0.4 }, entries: [] },
    allowed_lines: allowed, chosen_lines: [], shown_answer: shownAnswer,
    dropped_lines: ["The document says [ADDRESS] but ACRA says [ADDRESS]."],
    result: { answered_by: "case_data", notices: [notice], fallback_reason: "nothing_allowed", left_out: 1, model: "synthetic", elapsed_ms: 1200 },
    rated: true,
  };
  const feedbackBodies: unknown[] = [];
  const gaps: Record<string, unknown>[] = [];
  const rated: Record<string, unknown>[] = [];
  const recordViews: string[] = [];

  const json = (response: import("node:http").ServerResponse, body: unknown, status = 200) => {
    response.statusCode = status;
    response.setHeader("Content-Type", "application/json");
    response.end(JSON.stringify(body));
  };
  const server = createServer((request, response) => {
    request.on("error", () => undefined);
    response.on("error", () => undefined);
    const url = request.url ?? "";
    let body = "";
    request.on("data", (part: Buffer) => { body += part.toString(); });
    request.on("end", () => {
      if (url === "/client.js") {
        response.setHeader("Content-Type", "text/javascript"); response.end(script); return;
      }
      if (url.endsWith("/cases/case-one/brief")) {
        json(response, { company: "Case One", message: "Synthetic current case", suggested_questions: [question],
          blocker_count: 1, steps_done: 3, steps_total: 10 }); return;
      }
      if (url.endsWith("/cases/case-one/chat/stream")) {
        response.setHeader("Content-Type", "application/x-ndjson");
        response.end(JSON.stringify({ type: "done", answer: shownAnswer,
          answered_by: "case_data", model: null, notice, suggested_questions: [], answer_id: answerId,
          conversation_id: conversationId }) + "\n"); return;
      }
      if (url.endsWith(`/conversations/${conversationId}/end`)) {
        const sent = JSON.parse(body) as { resolved: boolean; satisfaction: string; comment: string };
        feedbackBodies.push(sent);
        gaps.push({ id: 1, note: sent.comment, blocker_codes: ["DOCUMENT_SOURCE_CONFLICT"], fields: [], stages: [],
          created_at: new Date().toISOString(), answer_id: answerId, question });
        rated.push({ conversation_id: conversationId, case_id: "case-one", title: question,
          created_at: new Date().toISOString(), updated_at: new Date().toISOString(), ended_at: new Date().toISOString(),
          resolved: sent.resolved, satisfaction: sent.satisfaction, priority: "high", review_status: "not_reviewed",
          answers: 1, team: "TEAM_A", user_id: "maya-lim" });
        json(response, { conversation_id: conversationId, message: "Thanks. Your feedback has been sent so the answers can be improved." }); return;
      }
      if (url.includes("/knowledge/conversations?")) {
        json(response, { items: rated, total: rated.length, page: 1, page_size: 10 }); return;
      }
      if (url.endsWith(`/knowledge/conversations/${conversationId}`)) {
        json(response, { ...rated[0], comment: gaps[0]?.note ?? null, close_reason: null, request: gaps[0] ?? null,
          draft: null, draft_by: null, draft_at: null,
          turns: [{ answer_id: answerId, created_at: record.created_at, question, answer: shownAnswer, notices: [notice], answered_by: "case_data" }] });
        return;
      }
      if (url.endsWith("/knowledge/me")) {
        json(response, { user_id: "support-user", can_review: true, can_edit_guidance: false, single_reviewer: true }); return;
      }
      if (url.endsWith("/knowledge/reviews")) { json(response, { pending: [], gaps }); return; }
      if (url.endsWith("/knowledge/stats")) {
        json(response, { entries: {}, feedback: { total: gaps.length, helpful: 0, not_helpful: gaps.length, helpful_rate: 0, open_gaps: gaps.length }, by_topic: {} }); return;
      }
      if (url.endsWith("/knowledge/entries")) { json(response, []); return; }
      if (url.endsWith("/knowledge/feedback/1/fix-start")) {
        // Like the service: the record's left-out line, redacted; no model call, nothing saved.
        json(response, { title: "Document source conflict", lines: record.dropped_lines }); return;
      }
      if (url.endsWith("/knowledge/feedback/1/answer")) {
        if (!gaps.length) { json(response, { detail: { code: "NOT_FOUND", message: "No such answer." } }, 404); return; }
        recordViews.push(url);
        json(response, record); return;
      }
      if (url.startsWith("/api/")) { json(response, { detail: "not found" }, 404); return; }
      response.setHeader("Content-Type", "text/html");
      response.end(`<html><head><style>${css}</style></head><body><div id="root"></div>
        <script type="module" src="/client.js"></script></body></html>`);
    });
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  if (!address || typeof address === "string") throw new Error("missing owned address");
  const origin = `http://127.0.0.1:${address.port}`;
  const violations: string[] = [];
  const policy = createBrowserNetworkPolicy({ frontendOrigin: origin,
    backendOrigin: process.env.CLM_E2E_BACKEND_ORIGIN!, allowDirectBackend: false });
  await page.route("**/*", (route) => handleBrowserRoute(route, policy, violations));
  try {
    await page.goto(origin);
    // The RM asks, then ends the conversation: not resolved, very unsatisfied, with how to improve.
    await page.getByRole("button", { name: "Ask AI Assistant", exact: true }).click();
    await expect(page.getByText("Case One · read-only", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: question, exact: true }).click();
    await expect(page.getByText(shownAnswer, { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Not helpful", exact: true })).toHaveCount(0);
    await page.getByRole("button", { name: "End conversation", exact: true }).click();
    const form = page.getByRole("form", { name: "End conversation" });
    await form.getByRole("radio", { name: "No", exact: true }).check();
    await expect(form.getByRole("radio")).toHaveCount(5); // Yes, No and three ratings
    await form.getByRole("radio", { name: "Very unsatisfied", exact: true }).check();
    await form.getByRole("textbox", { name: "How should it be improved?" }).fill("It did not show the two addresses.");
    await form.getByRole("button", { name: "Submit and end", exact: true }).click();
    await expect(page.getByText("Thanks. Your feedback has been sent so the answers can be improved.", { exact: true })).toBeVisible();
    expect(feedbackBodies).toEqual([{ resolved: false, satisfaction: "very_unsatisfied", comment: "It did not show the two addresses." }]);

    // Support opens the conversation; the record is loaded (and the view logged) only then.
    await page.getByRole("button", { name: "Sign in as Support", exact: true }).click();
    const row = page.locator(".knowledge-review-table tbody tr");
    await expect(row).toContainText(question);
    await expect(row).toContainText("Very unsatisfied");
    await expect(row).toContainText("High");
    const review = row.getByRole("button", { name: "Review", exact: true });
    await expect(page.getByRole("group", { name: "Write the fix" })).toHaveCount(0);
    expect(recordViews).toEqual([]);
    await review.click();
    await expect(page.getByRole("heading", { name: "Review conversation" })).toBeVisible();
    const saw = page.getByRole("region", { name: "What the RM saw" });
    await expect(saw.getByText(question, { exact: true })).toBeVisible();
    await expect(saw.getByText(shownAnswer, { exact: true })).toBeVisible();
    await expect(saw.getByText(notice, { exact: true })).toBeVisible();
    await expect(saw.getByText("It did not show the two addresses.", { exact: true })).toBeVisible();
    const why = page.getByRole("region", { name: "Information / rules used" });
    const cause = why.getByRole("note", { name: "Suggested cause" });
    await expect(cause).toContainText("Rule-based hint, not a verdict");
    await expect(cause).toContainText("Catalog gap: no allowed line matched");
    await expect(why.locator("del")).toHaveText("The document says [ADDRESS] but ACRA says [ADDRESS].");
    await why.getByText("All rules offered (2)", { exact: true }).click();
    const allowedList = why.locator(".request-page-allowed li");
    await expect(allowedList).toHaveText(allowed.map((line) => `${line.source === "policy" ? "Policy" : "Case"} ${line.text}`));
    // Side by side on a wide screen.
    const [left, right] = [await saw.boundingBox(), await why.boundingBox()];
    expect(left && right && right.x > left.x + left.width - 1).toBe(true);
    expect(recordViews).toHaveLength(1);
    // The fix is written on the request page, below what happened.
    const fix = page.getByRole("region", { name: "Edit how the AI should respond" });
    await expect(fix.getByRole("group", { name: "Write the fix" })).toBeVisible();
    // Started from the AI's answer, with the placeholders to rewrite marked; nothing saved yet.
    await expect(fix.getByRole("note")).toContainText("Started from the AI's answer.");
    await expect(fix.getByRole("textbox", { name: "Title" })).toHaveValue("Document source conflict");
    await expect(fix.getByRole("textbox", { name: /Guidance text/ })).toHaveValue(record.dropped_lines[0]);
    await expect(fix.locator(".knowledge-review-placeholders mark")).toHaveText(["[ADDRESS]"]);
    // Save waits until the placeholders are rewritten in general terms.
    await expect(fix.locator(".knowledge-review-placeholders")).toHaveText("Rewrite [ADDRESS] in general terms before saving.");
    await expect(fix.getByRole("button", { name: "Save and publish", exact: true })).toBeDisabled();
    await expect(fix.getByRole("button", { name: "Save as draft", exact: true })).toBeEnabled();
    await fix.getByRole("textbox", { name: /Guidance text/ }).fill("Ask the client for proof of the new address before choosing a value.");
    await fix.getByRole("textbox", { name: "Source reference" }).fill("docs/decisions/DECISION_LOG.md#D-030");
    await expect(fix.getByRole("button", { name: "Save and publish", exact: true })).toBeEnabled();
    const [columns, fixBox] = [await why.boundingBox(), await fix.boundingBox()];
    expect(columns && fixBox && fixBox.y >= columns.y + columns.height - 1).toBe(true);
    await page.getByRole("button", { name: "← Back to all conversations" }).click();
    await expect(review).toBeFocused();
    expect(violations).toEqual([]);
    expect(pageErrors).toEqual([]);
  } finally {
    await page.close();
    server.closeAllConnections();
    await new Promise<void>((resolve) => server.close(() => resolve()));
  }
});
