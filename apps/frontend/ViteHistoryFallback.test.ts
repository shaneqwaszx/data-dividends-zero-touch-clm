import {
  createServer as createHttpServer,
  request as createHttpRequest,
  type IncomingHttpHeaders,
  type Server as HttpServer,
} from "node:http";
import { mkdtemp, mkdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { afterEach, describe, expect, it } from "vitest";
import { createServer, type ViteDevServer } from "vite";

const CONFIG_PATH = fileURLToPath(new URL("./vite.config.ts", import.meta.url));
const SPA_MARKER = "phase15c-spa-index";

interface HttpResult {
  readonly body: string;
  readonly headers: IncomingHttpHeaders;
  readonly status: number;
}

let backend: HttpServer | null = null;
let vite: ViteDevServer | null = null;
let fixtureRoot: string | null = null;
let previousProxyTarget: string | undefined;

function listen(server: HttpServer): Promise<number> {
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      server.off("error", reject);
      const address = server.address();
      if (!address || typeof address === "string") return reject(new Error("Missing TCP address"));
      resolve(address.port);
    });
  });
}

function close(server: HttpServer): Promise<void> {
  return new Promise((resolve, reject) => {
    server.close((error) => error ? reject(error) : resolve());
  });
}

function rawRequest(
  origin: string,
  path: string,
  options: { readonly headers?: Record<string, string>; readonly method?: string } = {},
): Promise<HttpResult> {
  const target = new URL(origin);
  return new Promise((resolve, reject) => {
    const request = createHttpRequest({
      hostname: target.hostname,
      port: target.port,
      path,
      method: options.method ?? "GET",
      headers: options.headers,
    }, (response) => {
      const chunks: Buffer[] = [];
      response.on("data", (chunk: Buffer) => chunks.push(chunk));
      response.on("end", () => resolve({
        body: Buffer.concat(chunks).toString("utf8"),
        headers: response.headers,
        status: response.statusCode ?? 0,
      }));
    });
    request.once("error", reject);
    request.end();
  });
}

function contentType(result: HttpResult): string {
  const value = result.headers["content-type"];
  return Array.isArray(value) ? value.join(",") : value ?? "";
}

function expectSpa(result: HttpResult, label: string, head = false): void {
  expect.soft(result.status, label).toBe(200);
  expect.soft(contentType(result), label).toContain("text/html");
  if (head) expect.soft(result.body, label).toBe("");
  else expect.soft(result.body, label).toContain(SPA_MARKER);
}

function expectNotSpa(result: HttpResult, label: string, status = 404): void {
  expect.soft(result.status, label).toBe(status);
  expect.soft(contentType(result), label).not.toContain("text/html");
  expect.soft(result.body, label).not.toContain(SPA_MARKER);
}

afterEach(async () => {
  if (vite) await vite.close();
  if (backend?.listening) await close(backend);
  if (fixtureRoot) await rm(fixtureRoot, { recursive: true, force: true });
  if (previousProxyTarget === undefined) delete process.env.VITE_BACKEND_PROXY_TARGET;
  else process.env.VITE_BACKEND_PROXY_TARGET = previousProxyTarget;
  backend = null;
  vite = null;
  fixtureRoot = null;
});

describe("Phase 15C local Vite namespace contract", () => {
  it("uses Vite-first MPA handling and admits only explicit document navigation", async () => {
    backend = createHttpServer((request, response) => {
      if (request.url === "/api/auth/me") {
        response.writeHead(401, { "Content-Type": "application/json" });
        response.end(JSON.stringify({ detail: { code: "AUTH_REQUIRED", message: "Sign in required." } }));
        return;
      }
      response.writeHead(404, { "Content-Type": "application/json" });
      response.end(JSON.stringify({ detail: { code: "NOT_FOUND", message: "Not found." } }));
    });
    const backendPort = await listen(backend);
    previousProxyTarget = process.env.VITE_BACKEND_PROXY_TARGET;
    process.env.VITE_BACKEND_PROXY_TARGET = `http://127.0.0.1:${backendPort}`;

    fixtureRoot = await mkdtemp(join(tmpdir(), "phase15c-vite-"));
    const knownAsset = join(fixtureRoot, "public", "assets", "known.css");
    const knownRootResource = join(fixtureRoot, "public", "known-root.js");
    const sourceModule = join(fixtureRoot, "src", "main.tsx");
    const sourceStyle = join(fixtureRoot, "src", "styles.css");
    await mkdir(dirname(knownAsset), { recursive: true });
    await mkdir(dirname(sourceModule), { recursive: true });
    await writeFile(
      join(fixtureRoot, "index.html"),
      `<!doctype html><html><body><main id="${SPA_MARKER}">SPA</main><script type="module" src="/src/main.tsx"></script></body></html>`,
      "utf8",
    );
    await writeFile(knownAsset, ".known { color: green; }\n", "utf8");
    await writeFile(knownRootResource, "export const known = true;\n", "utf8");
    await writeFile(sourceModule, 'import "./styles.css";\nexport const fixture = true;\n', "utf8");
    await writeFile(sourceStyle, ".fixture { color: blue; }\n", "utf8");

    const vitePortProbe = createHttpServer();
    const vitePort = await listen(vitePortProbe);
    await close(vitePortProbe);
    vite = await createServer({
      configFile: CONFIG_PATH,
      root: fixtureRoot,
      logLevel: "silent",
      server: { host: "127.0.0.1", port: vitePort, strictPort: true },
    });
    await vite.listen();
    const address = vite.httpServer?.address();
    if (!address || typeof address === "string") throw new Error("Vite did not expose a TCP address");
    const origin = `http://127.0.0.1:${address.port}`;

    for (const path of ["/", "/index.html"]) {
      const get = await rawRequest(origin, path, {
        headers: { Accept: "text/html", "Sec-Fetch-Dest": "document" },
      });
      expectSpa(get, `GET ${path}`);
      expect.soft(get.body, path).toContain("/@vite/client");
      expect.soft(get.body, path).toContain("/@react-refresh");
      expect.soft(get.body, path).toContain("/src/main.tsx");
      expectSpa(await rawRequest(origin, path, {
        method: "HEAD",
        headers: { Accept: "text/html", "Sec-Fetch-Dest": "document" },
      }), `HEAD ${path}`, true);
    }

    const navigationPaths = [
      "/dashboard",
      "/cases",
      "/cases/00000000-0000-4000-8000-00000000015a",
      "/new-onboarding",
      "/new-onboarding/00000000-0000-4000-8000-00000000015a",
      "/onboarded",
      "/onboarded/00000000-0000-4000-8000-00000000015a",
      "/audit",
      "/audit/00000000-0000-4000-8000-00000000015a",
      "/policy",
      "/admin/users",
      "/admin/teams",
      "/unknown-application-path",
      "/wildcard/client-route",
      "/reports/quarter.v2",
      "/customer.v2/profile",
      "/dashboard?view=all",
    ];
    for (const path of navigationPaths) {
      expectSpa(await rawRequest(origin, path, {
        headers: { Accept: "text/html", "Sec-Fetch-Dest": "document" },
      }), path);
    }
    for (const path of ["/dashboard", "/reports/quarter.v2"]) {
      expectSpa(await rawRequest(origin, path, {
        method: "HEAD",
        headers: { Accept: "text/html", "Sec-Fetch-Dest": "document" },
      }), `HEAD ${path}`, true);
    }

    const acceptedHtml: Array<[string, string | undefined]> = [
      ["text/html", undefined],
      ["text/html;q=1", "document"],
      ["text/html;q=1.000", "frame"],
      ["text/html;q=0.5", "iframe"],
      ["TEXT/HTML; Q=0.5", "DoCuMeNt"],
      ["application/json, text/html;q=0.8", " document "],
      ["text/html;charset=utf-8", undefined],
      ["text/html;q=0, text/html;q=0.5", "document"],
    ];
    for (const [accept, destination] of acceptedHtml) {
      const headers: Record<string, string> = { Accept: accept };
      if (destination !== undefined) headers["Sec-Fetch-Dest"] = destination;
      expectSpa(await rawRequest(origin, "/wildcard/client-route", { headers }), accept);
    }

    const rejectedAccept = [
      "",
      "*/*",
      "application/json",
      "text/html;q",
      "text/html;q=",
      "text/html;q=.5",
      "text/html;q=000",
      "text/html;q=-1",
      "text/html;q=2",
      "text/html;q=0.0001",
      "text/html;q=invalid",
      "text/html;q=0",
      "text/html;q=0.0",
      "text/html;q=0.000",
      "text/html;q=0;q=1",
      "text/html;q=0, */*;q=1",
      "text/html; charset",
      'text/html;charset="utf-8"',
    ];
    for (const accept of rejectedAccept) {
      expectNotSpa(await rawRequest(origin, "/wildcard/client-route", {
        headers: { Accept: accept, "Sec-Fetch-Dest": "document" },
      }), `Accept ${accept}`);
    }

    for (const destination of [
      "empty", "script", "style", "image", "font", "manifest", "worker",
      "audio", "video", "object", "report", "embed", "track", "unknown-token",
    ]) {
      expectNotSpa(await rawRequest(origin, "/extensionless-resource", {
        headers: { Accept: "text/html", "Sec-Fetch-Dest": destination },
      }), `destination ${destination}`);
    }

    for (const [path, expectedType, expectedBody] of [
      ["/assets/known.css", "text/css", ".known { color: green; }\n"],
      ["/known-root.js", "text/javascript", "export const known = true;\n"],
    ] as const) {
      const response = await rawRequest(origin, path);
      expect.soft(response.status, path).toBe(200);
      expect.soft(contentType(response), path).toContain(expectedType);
      expect.soft(response.body, path).toBe(expectedBody);
    }

    for (const path of ["/@vite/client", "/@vite/env", "/@react-refresh", "/src/main.tsx", "/src/styles.css"]) {
      const get = await rawRequest(origin, path, {
        headers: { Accept: "*/*", "Sec-Fetch-Dest": "script" },
      });
      expect.soft(get.status, path).toBe(200);
      expect.soft(contentType(get), path).toContain("text/javascript");
      expect.soft(get.body, path).not.toContain(SPA_MARKER);
      const head = await rawRequest(origin, path, {
        method: "HEAD",
        headers: { Accept: "*/*", "Sec-Fetch-Dest": "script" },
      });
      expect.soft(head.status, `HEAD ${path}`).toBe(200);
      expect.soft(head.body, `HEAD ${path}`).toBe("");
    }

    const resourceMisses = [
      "/assets/does-not-exist.js",
      "/assets/nested/does-not-exist.css?cache=1",
      "/assets/nested%2Fdoes-not-exist.css",
      "/missing.js",
      "/modules/missing.mjs",
      "/foo/missing.css",
      "/images/missing.png",
      "/fonts/missing.woff2",
      "/maps/missing.js.map",
      "/missing.json",
      "/missing.pdf",
      "/missing.wasm",
      "/site.webmanifest",
      "/MISSING.JS?cache=1",
      "/missing.js?route=/dashboard",
      "/missing.js;v=1",
      "/missing.css;anything",
      "/missing.js%3Bv=1",
      "/missing.css%3Banything",
      "/foo%2Ejs",
      "/foo%252Ejs",
      "/foo%25252Ejs",
      "/images/foo%252Epng",
      "/trailing-dot.",
      "/nested/path..",
    ];
    for (const path of resourceMisses) {
      expectNotSpa(await rawRequest(origin, path, {
        headers: { Accept: "text/html", "Sec-Fetch-Dest": "document" },
      }), path);
    }
    expectNotSpa(await rawRequest(origin, "/downloads/missing.custom", {
      headers: { Accept: "application/octet-stream" },
    }), "unknown resource extension");

    const malformedPaths = [
      "/bad/%ZZ/path",
      "/malformed%",
      "/dashboard%25",
      "/dashboard%252525",
      "/foo%2Fbar",
      "/foo%252Fbar",
      "/foo%5Cbar",
      "/foo%3Fbar",
      "/foo%23bar",
      "/extensionless;matrix=1",
      "/foo/%2E%2E/bar",
      "/foo/./bar",
      "/foo/../bar",
    ];
    for (const path of malformedPaths) {
      expectNotSpa(await rawRequest(origin, path, {
        headers: { Accept: "text/html", "Sec-Fetch-Dest": "document" },
      }), path);
    }

    const reservedMisses = [
      "/@id/__x00__virtual:phase15c-missing",
      "/@vite/missing",
      "/@fs/phase15c-missing",
      "/@fs/index.html",
      "/@react-refresh/missing",
      "/src/missing.tsx",
      "/node_modules/phase15c-missing/index.js",
      "/__vite_missing",
    ];
    for (const path of reservedMisses) {
      expectNotSpa(await rawRequest(origin, path, {
        headers: { Accept: "text/html", "Sec-Fetch-Dest": "document" },
      }), path);
    }

    for (const [path, status] of [
      ["/api/auth/me", 401],
      ["/api/missing.js", 404],
      ["/api/foo%252Ejs", 404],
      ["/api%2Fmissing", 404],
    ] as const) {
      const api = await rawRequest(origin, path, {
        headers: { Accept: "text/html", "Sec-Fetch-Dest": "document" },
      });
      expectNotSpa(api, path, status);
      expect.soft(contentType(api), path).toContain("application/json");
    }

    for (const path of ["/missing.js", "/missing.js;v=1", "/dashboard%252525", "/@id/missing"]) {
      const response = await rawRequest(origin, path, {
        method: "HEAD",
        headers: { Accept: "text/html", "Sec-Fetch-Dest": "document" },
      });
      expectNotSpa(response, `HEAD ${path}`);
      expect.soft(response.body, `HEAD ${path}`).toBe("");
    }

    for (const method of ["POST", "PUT", "PATCH", "DELETE"]) {
      for (const path of ["/dashboard", "/missing.js", "/index.html"]) {
        expectNotSpa(await rawRequest(origin, path, {
          method,
          headers: { Accept: "text/html", "Sec-Fetch-Dest": "document" },
        }), `${method} ${path}`);
      }
    }
    const options = await rawRequest(origin, "/dashboard", {
      method: "OPTIONS",
      headers: { Accept: "text/html", Origin: "http://example.test" },
    });
    expect.soft(options.status, "OPTIONS /dashboard").toBe(204);
    expect.soft(options.body, "OPTIONS /dashboard").toBe("");
    expect.soft(options.body, "OPTIONS /dashboard").not.toContain(SPA_MARKER);
  });
});
