// D-118 usability: builds the real AI Models page (signed in as the synthetic HR administrator)
// into a folder that apps/assistant/tests/ui_stack.py serves at "/". Test-only; no secrets.
//   node e2e/support/ai-models-page.mjs OUT_DIR
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";

export async function buildAiModelsPage(outDir) {
  const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
  const compiled = await build({
    stdin: {
      contents: `
        import {createRoot} from "react-dom/client";
        import {QueryClient, QueryClientProvider} from "@tanstack/react-query";
        import {MemoryRouter} from "react-router";
        import AiModelManagement from "./src/pages/AiModelManagement";
        import {paths} from "./src/navigation";
        const hr = { user_id: "hr-admin", display_name: "HR Admin", role: "HR", team_id: null,
          team_display_name: null, team_type: null, team_description: "", client_scope_label: "",
          capabilities: ["IDENTITY_ADMIN", "MODEL_CONFIG_MANAGE"] };
        const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
        createRoot(document.getElementById("root")).render(
          <MemoryRouter initialEntries={[paths.aiModels]}>
            <QueryClientProvider client={client}><AiModelManagement actor={hr} /></QueryClientProvider>
          </MemoryRouter>);
      `,
      loader: "tsx",
      resolveDir: root,
    },
    bundle: true, write: false, format: "esm", outfile: "client.js", jsx: "automatic",
    define: { "import.meta.env": "{}" },
  });
  mkdirSync(outDir, { recursive: true });
  for (const file of compiled.outputFiles) writeFileSync(path.join(outDir, path.basename(file.path)), file.contents);
  writeFileSync(path.join(outDir, "index.html"), `<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>AI Models (local stack)</title>
<link rel="stylesheet" href="/client.css"></head><body><div id="root"></div>
<script type="module" src="/client.js"></script></body></html>`);
  return outDir;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  const out = process.argv[2];
  if (!out) { console.error("usage: node e2e/support/ai-models-page.mjs OUT_DIR"); process.exit(2); }
  await buildAiModelsPage(path.resolve(out));
  console.log(`built ${out}`);
}
