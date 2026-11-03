import { createServer, type ServerResponse } from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";
import { expect, test } from "@playwright/test";
import { createBrowserNetworkPolicy, handleBrowserRoute } from "../playwright.config";

// D-115 case memory in real Chromium, rendering the actual unchanged panel against a synthetic
// copilot service: a case chat keeps its own memory, leaving it closes its server context, a
// late reply never reaches another case, the general chat starts empty, and sign-out closes
// what is open. The service is a fixture; it grants no backend authority or Live-model claim.
test("D-115 case memory is per case and is closed on leaving, switching and sign-out", async ({ page }) => {
  test.setTimeout(60000);
  page.setDefaultTimeout(8000);
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.name));
  const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
  const compiled = await build({
    stdin: { contents: `
      import React, {useState} from "react";
      import {createRoot} from "react-dom/client";
      import Panel from "./src/pages/AiAssistantPanel";
      function App() {
        const [caseId,setCase] = useState("case-one");
        const [actor,setActor] = useState(0);
        return <><button onClick={()=>setCase("case-one")}>Show case one</button>
          <button onClick={()=>setCase("case-two")}>Show case two</button>
          <button onClick={()=>setCase(null)}>Show no case</button>
          <button onClick={()=>setActor(actor+1)}>Sign out</button>
          <Panel key={actor} caseId={caseId} onOpenCases={()=>{}} canGeneralChat /></>;
      }
      createRoot(document.getElementById("root")).render(<App/>);
    `, loader: "tsx", resolveDir: root },
    bundle: true, write: false, format: "esm", outfile: "client.js", jsx: "automatic",
    define: { "import.meta.env": "{}" },
  });
  const script = compiled.outputFiles!.find((file) => file.path.endsWith("client.js"))!.text;
  const css = compiled.outputFiles!.find((file) => file.path.endsWith("client.css"))?.text ?? "";
  // What the synthetic service saw: contexts opened (with their case), closed, and every
  // question with the context it named.
  const opened: { id: string; caseId: string | null }[] = [];
  const closed: string[] = [];
  const asked: { where: string; context: string | null; message: string }[] = [];
  const timers = new Set<ReturnType<typeof setTimeout>>();
  const json = (response: ServerResponse, body: unknown) => {
    response.setHeader("Content-Type", "application/json");
    response.end(JSON.stringify(body));
  };
  const done = (answer: string) => JSON.stringify({ type: "done", answer, answered_by: "model",
    model: "synthetic", notice: null, suggested_questions: [] }) + "\n";
  const server = createServer((request, response) => {
    request.on("error", () => undefined);
    response.on("error", () => undefined);
    const url = request.url ?? "";
    if (url === "/client.js") {
      response.setHeader("Content-Type", "text/javascript"); response.end(script); return;
    }
    if (url.endsWith("/health")) {
      json(response, { status: "ok", llm_enabled: true, model: "synthetic", answer_mode: "copilot",
        general_chat: true }); return;
    }
    if (url.endsWith("/brief")) {
      json(response, { company: url.includes("case-two") ? "Case Two" : "Case One",
        message: "Synthetic current case", suggested_questions: [], blocker_count: 0,
        steps_done: 0, steps_total: 1 }); return;
    }
    let body = "";
    request.on("data", (part: Buffer) => { body += part.toString(); });
    request.on("end", () => {
      const sent = body ? JSON.parse(body) as Record<string, string | undefined> : {};
      const closing = url.match(/\/contexts\/([^/]+)\/close$/);
      if (closing) { closed.push(decodeURIComponent(closing[1])); response.statusCode = 204; response.end(); return; }
      if (url.endsWith("/contexts")) {
        const id = `ctx-${opened.length + 1}`;
        const caseId = sent.case_id ?? null;
        opened.push({ id, caseId });
        json(response, { context_id: id, scope: caseId ? "case" : "general", case_id: caseId,
          idle_seconds: 1800 }); return;
      }
      if (url.endsWith("/chat/stream")) {
        const where = url.includes("/general/") ? "general" : url.includes("case-two") ? "case-two" : "case-one";
        const message = sent.message ?? "";
        asked.push({ where, context: sent.context_id ?? null, message });
        response.setHeader("Content-Type", "application/x-ndjson");
        response.setHeader("Cache-Control", "no-store");
        if (message === "slow") {
          response.write(JSON.stringify({ type: "text", text: "case one partial" }) + "\n");
          const timer = setTimeout(() => { timers.delete(timer); response.end(done("LATE case one answer")); }, 2000);
          timers.add(timer);
          response.on("close", () => { if (timers.delete(timer)) clearTimeout(timer); });
          return;
        }
        response.end(done(`${where} answer to ${message}`)); return;
      }
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
  const messages = page.locator(".ai-assistant-message");
  const ask = async (label: string, message: string) => {
    await page.getByRole("textbox", { name: label }).fill(message);
    await page.getByRole("button", { name: "Send", exact: true }).click();
  };
  const caseBox = "Ask the AI assistant about this case";
  try {
    await page.goto(origin);
    await page.getByRole("button", { name: "Ask AI Assistant", exact: true }).click();
    await expect(page.getByText("Case One · read-only", { exact: true })).toBeVisible();

    // Within case one: a short question and its follow-up share one server context.
    await ask(caseBox, "Status?");
    await expect(messages.filter({ hasText: "case-one answer to Status?" })).toHaveCount(1);
    await ask(caseBox, "Why?");
    await expect(messages.filter({ hasText: "case-one answer to Why?" })).toHaveCount(1);
    expect(opened).toEqual([{ id: "ctx-1", caseId: "case-one" }]);
    expect(asked.map((item) => item.context)).toEqual(["ctx-1", "ctx-1"]);

    // Switching while a reply is still coming: case one's context closes and its late reply
    // never appears in case two, which starts with an empty memory of its own.
    await ask(caseBox, "slow");
    await expect(page.getByText("case one partial", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Show case two", exact: true }).click();
    await expect(page.getByText("Case Two · read-only", { exact: true })).toBeVisible();
    await expect.poll(() => closed).toContain("ctx-1");
    await expect(messages.filter({ hasText: "case-one answer" })).toHaveCount(0);
    await ask(caseBox, "Status?");
    await expect(messages.filter({ hasText: "case-two answer to Status?" })).toHaveCount(1);
    expect(opened.at(-1)).toEqual({ id: "ctx-2", caseId: "case-two" });
    expect(asked.at(-1)).toEqual({ where: "case-two", context: "ctx-2", message: "Status?" });

    // Leaving for the general chat: case two's context closes; the general chat has its own.
    await page.getByRole("button", { name: "Show no case", exact: true }).click();
    await expect(page.getByText("General onboarding help · read-only", { exact: true })).toBeVisible();
    await expect.poll(() => closed).toContain("ctx-2");
    await expect(messages.filter({ hasText: "case-two answer" })).toHaveCount(0);
    await ask("Ask the AI assistant about corporate onboarding", "What is KYC?");
    await expect(messages.filter({ hasText: "general answer to What is KYC?" })).toHaveCount(1);
    expect(opened.at(-1)).toEqual({ id: "ctx-3", caseId: null });
    expect(asked.at(-1)).toEqual({ where: "general", context: "ctx-3", message: "What is KYC?" });

    // Coming back to case one starts afresh: nothing of its earlier chat, a new context.
    await page.getByRole("button", { name: "Show case one", exact: true }).click();
    await expect(page.getByText("Case One · read-only", { exact: true })).toBeVisible();
    await expect.poll(() => closed).toContain("ctx-3");
    await expect(messages.filter({ hasText: "answer to" })).toHaveCount(0);
    await ask(caseBox, "Status?");
    await expect(messages.filter({ hasText: "case-one answer to Status?" })).toHaveCount(1);
    expect(opened.at(-1)).toEqual({ id: "ctx-4", caseId: "case-one" });

    // Sign-out (the panel unmounts): its open context is closed.
    await page.getByRole("button", { name: "Sign out", exact: true }).click();
    await expect(page.getByRole("button", { name: "Ask AI Assistant", exact: true })).toBeVisible();
    await expect.poll(() => closed).toContain("ctx-4");
    expect(new Set(closed)).toEqual(new Set(["ctx-1", "ctx-2", "ctx-3", "ctx-4"]));
    await expect(page.getByText("LATE case one answer", { exact: true })).toHaveCount(0);
    expect(violations).toEqual([]);
    expect(pageErrors).toEqual([]);
  } finally {
    await page.close();
    for (const timer of timers) clearTimeout(timer);
    server.closeAllConnections();
    await new Promise<void>((resolve) => server.close(() => resolve()));
  }
});
