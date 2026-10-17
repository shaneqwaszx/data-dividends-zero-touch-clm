import { createServer, type ServerResponse } from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";
import { expect, test } from "@playwright/test";
import { createBrowserNetworkPolicy, handleBrowserRoute } from "../playwright.config";

// Real Chromium + real finite chunked HTTP, rendering the actual unchanged panel.
// The fixture is synthetic; it grants no backend authority or Live-model claim.
test("PR89 streaming resources preserve browser answers and cancel old case and actor reads", async ({ page }) => {
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
      function App() {
        const [caseId,setCase] = useState("case-one");
        const [actor,setActor] = useState(0);
        return <><button onClick={()=>setCase("case-two")}>Replace case</button>
          <button onClick={()=>setActor(actor+1)}>Replace actor</button>
          <Panel key={actor} caseId={caseId} onOpenCases={()=>{}} /></>;
      }
      createRoot(document.getElementById("root")).render(<App/>);
    `, loader: "tsx", resolveDir: root },
    bundle: true, write: false, format: "esm", outfile: "client.js", jsx: "automatic",
    define: { "import.meta.env": "{}" },
  });
  const script = compiled.outputFiles!.find((file) => file.path.endsWith("client.js"))!.text;
  const css = compiled.outputFiles!.find((file) => file.path.endsWith("client.css"))?.text ?? "";
  const text = 'The current case offers "Keep registry value".';
  const notice = "This answer was cut short. Ask me to continue for the rest.";
  let cancelled = 0;
  let pending = 0;
  const timers = new Set<ReturnType<typeof setTimeout>>();
  const delayed = (response: ServerResponse, callback: () => void) => {
    pending++;
    const timer = setTimeout(() => { timers.delete(timer); callback(); }, 2000);
    timers.add(timer);
    response.on("close", () => {
      if (timers.delete(timer)) { clearTimeout(timer); cancelled++; }
    });
  };
  const server = createServer((request, response) => {
    request.on("error", () => undefined);
    response.on("error", () => undefined);
    if (request.url === "/client.js") {
      response.setHeader("Content-Type", "text/javascript"); response.end(script); return;
    }
    if (request.url?.endsWith("/brief")) {
      response.setHeader("Content-Type", "application/json");
      response.end(JSON.stringify({ company: request.url.includes("case-two") ? "Case Two" : "Case One",
        message: "Synthetic current case", suggested_questions: [], blocker_count: 0,
        steps_done: 0, steps_total: 1 })); return;
    }
    if (request.url?.endsWith("/chat/stream")) {
      let body = "";
      request.on("data", (part: Buffer) => { body += part.toString(); });
      request.on("end", () => {
        const message = (JSON.parse(body) as { message: string }).message;
        response.setHeader("Content-Type", "application/x-ndjson");
        response.setHeader("Cache-Control", "no-store");
        const done = (answer: string, note: string | null) => JSON.stringify({ type: "done",
          answer, answered_by: "model", model: "synthetic", notice: note,
          suggested_questions: [] }) + "\n";
        if (message === "error503") {
          response.statusCode = 503;
          response.setHeader("Content-Type", "application/json");
          response.write('{"detail":{"message":"' + "x".repeat(17 * 1024));
          delayed(response, () => response.end('"}}'));
        } else if (message === "oversized") {
          response.write("x".repeat(129 * 1024));
          delayed(response, () => response.end());
        } else if (message === "wait") {
          response.write(JSON.stringify({ type: "text", text: "old case partial" }) + "\n");
          delayed(response, () => response.end(done("stale answer must not appear", null)));
        } else {
          // Separate writes split a UTF-8 code point and NDJSON newline terminators.
          const content = Buffer.from(JSON.stringify({ type: "text", text: "café 🌍" }) + "\n");
          const split = content.indexOf(Buffer.from("é")) + 1;
          response.write(content.subarray(0, split));
          const timer = setTimeout(() => {
            timers.delete(timer);
            response.write(content.subarray(split));
            response.end(done(text, message === "partial" ? notice : null));
          }, 30);
          timers.add(timer);
        }
      }); return;
    }
    response.setHeader("Content-Type", "text/html");
    response.end(`<html><head><style>${css}</style></head><body><div id="root"></div>
      <script type="module" src="/client.js"></script></body></html>`);
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
    await page.getByRole("button", { name: "Ask AI Assistant", exact: true }).click();
    await expect(page.getByText("Case One · read-only", { exact: true })).toBeVisible();
    const ask = async (message: string) => {
      await page.getByRole("textbox", { name: "Ask the AI assistant about this case" }).fill(message);
      await page.getByRole("button", { name: "Send", exact: true }).click();
    };
    await ask("normal");
    await expect(page.locator(".ai-assistant-message").filter({ hasText: text })).toHaveCount(1);
    await ask("partial");
    await expect(page.getByText(notice, { exact: true })).toBeVisible();
    await ask("oversized");
    await expect(page.getByRole("alert")).toHaveText(/limit/);
    await expect.poll(() => cancelled).toBe(1);
    await ask("error503");
    await expect(page.getByRole("alert")).toHaveText("The AI assistant service is unavailable right now.");
    await expect.poll(() => cancelled).toBe(2);
    await ask("wait");
    await expect(page.getByText("old case partial", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Replace case", exact: true }).click();
    await expect(page.getByText("Case Two · read-only", { exact: true })).toBeVisible();
    await expect.poll(() => cancelled).toBe(3);
    await expect(page.getByText("old case partial", { exact: true })).toHaveCount(0);
    await ask("wait");
    await expect(page.getByText("old case partial", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Replace actor", exact: true }).click();
    await expect(page.getByRole("button", { name: "Ask AI Assistant", exact: true })).toBeVisible();
    await expect.poll(() => cancelled).toBe(4);
    expect(pending).toBe(4);
    await expect(page.getByText("stale answer must not appear", { exact: true })).toHaveCount(0);
    expect(violations).toEqual([]);
    expect(pageErrors).toEqual([]);
  } finally {
    await page.close();
    for (const timer of timers) clearTimeout(timer);
    server.closeAllConnections();
    await new Promise<void>((resolve) => server.close(() => resolve()));
  }
});
