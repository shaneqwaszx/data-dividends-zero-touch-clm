import { createServer } from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";
import { expect, test } from "@playwright/test";
import { createBrowserNetworkPolicy, handleBrowserRoute } from "../playwright.config";

// Real Chromium rendering the actual panel and Knowledge review window against a synthetic
// assistant API. The fixture is synthetic; it grants no backend authority or Live-model claim.
// The fake service keeps the answer record contract: feedback must name the answer_id the
// stream returned, and only the record linked to a request is served as "What happened".
test("answer records: RM asks, marks it Not helpful, and a Director sees What happened", async ({ page }) => {
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
        const [director, setDirector] = useState(false);
        return director
          ? <KnowledgeReview onClose={()=>{}} />
          : <><button onClick={()=>setDirector(true)}>Sign in as the Director</button>
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
  const allowed = ["Keep the registry value.", "Open Documents to compare the values."];
  const record = {
    answer_id: answerId, case_id: "case-one", created_at: "2026-10-25T00:00:00+00:00", question,
    earlier_answer_ids: [],
    case_snapshot: { blocker_codes: ["DOCUMENT_SOURCE_CONFLICT"], stage: "Documents", steps_done: 3, steps_total: 10, facts_hash: "f".repeat(64) },
    knowledge: { confidence: "low", degraded: false, entries: [] },
    allowed_lines: allowed, chosen_lines: [],
    dropped_lines: ["The document says [ADDRESS] but ACRA says [ADDRESS]."],
    result: { answered_by: "case_data", notices: [], fallback_reason: "nothing_allowed", left_out: 1, model: "synthetic", elapsed_ms: 1200 },
    rated: true,
  };
  const feedbackBodies: unknown[] = [];
  const gaps: Record<string, unknown>[] = [];
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
        response.end(JSON.stringify({ type: "done", answer: "The registered address comes from ACRA.",
          answered_by: "case_data", model: null, notice: "The model response could not be verified, so this answer comes from the case data.",
          suggested_questions: [], answer_id: answerId }) + "\n"); return;
      }
      if (url.endsWith("/cases/case-one/feedback")) {
        const sent = JSON.parse(body) as { helpful: boolean; note: string; answer_id?: string };
        feedbackBodies.push(sent);
        // Like the service: "Not helpful" must name an answer it recorded for this user and case.
        if (sent.answer_id !== answerId) { json(response, { detail: { code: "NOT_FOUND", message: "No such answer." } }, 404); return; }
        gaps.push({ id: 1, note: sent.note, blocker_codes: ["DOCUMENT_SOURCE_CONFLICT"], fields: [], stages: [],
          created_at: "2026-10-25T00:00:01+00:00", answer_id: answerId });
        json(response, { feedback_id: 1, message: "Thanks. This has been flagged so the answer can be improved." }); return;
      }
      if (url.endsWith("/knowledge/me")) {
        json(response, { user_id: "olivia-koh", can_review: true, can_edit_guidance: false, single_reviewer: true }); return;
      }
      if (url.endsWith("/knowledge/reviews")) { json(response, { pending: [], gaps }); return; }
      if (url.endsWith("/knowledge/stats")) {
        json(response, { entries: {}, feedback: { total: gaps.length, helpful: 0, not_helpful: gaps.length, helpful_rate: 0, open_gaps: gaps.length }, by_topic: {} }); return;
      }
      if (url.endsWith("/knowledge/entries")) { json(response, []); return; }
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
    // The RM asks and marks the answer Not helpful, with the required note.
    await page.getByRole("button", { name: "Ask AI Assistant", exact: true }).click();
    await expect(page.getByText("Case One · read-only", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: question, exact: true }).click();
    await expect(page.getByText("The registered address comes from ACRA.", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Not helpful", exact: true }).click();
    const form = page.locator(".ai-assistant-feedback-form");
    await form.getByRole("textbox", { name: "What was missing?" }).fill("It did not show the two addresses.");
    await form.getByRole("button", { name: "Send", exact: true }).click();
    await expect(page.getByText("Thanks. This has been flagged so the answer can be improved.", { exact: true })).toBeVisible();
    expect(feedbackBodies).toEqual([{ helpful: false, note: "It did not show the two addresses.", answer_id: answerId }]);

    // The Director opens the request and sees what happened, loaded only when opened.
    await page.getByRole("button", { name: "Sign in as the Director", exact: true }).click();
    const requestCard = page.getByRole("article", { name: "Enhancement request 1" });
    await expect(requestCard.getByText("It did not show the two addresses.", { exact: true })).toBeVisible();
    expect(recordViews).toEqual([]);
    await requestCard.getByText("What happened", { exact: true }).click();
    await expect(requestCard.getByRole("alert")).toContainText("No allowed line matched.");
    await expect(requestCard.getByText(question, { exact: true })).toBeVisible();
    await expect(requestCard.getByText("The document says [ADDRESS] but ACRA says [ADDRESS].", { exact: true })).toBeVisible();
    await requestCard.getByText("Allowed lines (2)", { exact: true }).click();
    for (const line of allowed) await expect(requestCard.getByText(line, { exact: true })).toBeVisible();
    expect(recordViews).toHaveLength(1);
    expect(violations).toEqual([]);
    expect(pageErrors).toEqual([]);
  } finally {
    await page.close();
    server.closeAllConnections();
    await new Promise<void>((resolve) => server.close(() => resolve()));
  }
});
