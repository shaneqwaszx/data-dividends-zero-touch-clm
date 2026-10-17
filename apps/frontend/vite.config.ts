/// <reference types="vitest/config" />

// @ts-expect-error The browser tsconfig intentionally excludes Node ambient types.
import { Agent as HttpAgent } from "node:http";
import { defineConfig, loadEnv, type Plugin } from "vite";
import react from "@vitejs/plugin-react";

interface DevelopmentHttpRequest {
  readonly headers?: Record<string, string | string[] | undefined>;
  readonly method?: string;
  readonly originalUrl?: string;
  url?: string;
}

const RESOURCE_EXTENSIONS = new Set([
  "apng", "avif", "bmp", "cjs", "css", "csv", "eot", "gif", "html", "ico",
  "jpeg", "jpg", "js", "json", "jsx", "less", "map", "mjs", "mp3", "mp4",
  "ogg", "otf", "pdf", "png", "scss", "svg", "ts", "tsx", "ttf", "txt",
  "wasm", "wav", "webm", "webmanifest", "webp", "woff", "woff2", "xml", "zip",
]);

const DOCUMENT_DESTINATIONS = new Set(["document", "frame", "iframe"]);
const MAX_PATH_DECODE_ROUNDS = 3;
const HTTP_TOKEN = /^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$/;
const HTTP_PARAMETER_VALUE = /^[!#$%&'*+\-.^_`|~0-9A-Za-z:/]+$/;
const HTTP_QUALITY = /^(?:0(?:\.\d{0,3})?|1(?:\.0{0,3})?)$/;
const ENCODED_PATH_AMBIGUITY = /%(?:2f|3f|23|5c)/i;
const CONTROL_CHARACTER = /[\u0000-\u001f\u007f]/;
const E2E_REQUEST_ID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const E2E_INTAKE_PATH = /^\/api(?:\/demo)?\/clm\/zero-touch\/cases\/([0-9a-f-]{36})\/intake\/documents(?:\?|$)/i;
const nodeRuntime = globalThis as unknown as {
  console: { info: (...values: unknown[]) => void };
  process: {
    env: Record<string, string | undefined>;
    hrtime: { bigint: () => bigint };
    pid: number;
  };
};

interface DiagnosticProxyRequest {
  once(event: "finish", listener: () => void): void;
}

interface DiagnosticProxyResponse {
  readonly statusCode?: number;
  once(event: "end", listener: () => void): void;
}

interface DiagnosticProxy {
  on(
    event: "proxyReq",
    listener: (proxyRequest: DiagnosticProxyRequest, request: DevelopmentHttpRequest) => void,
  ): void;
  on(
    event: "proxyRes",
    listener: (proxyResponse: DiagnosticProxyResponse, request: DevelopmentHttpRequest) => void,
  ): void;
}

function e2eProxyMilestone(
  request: DevelopmentHttpRequest,
  milestone: string,
  status?: number,
): void {
  if (nodeRuntime.process.env.CLM_E2E_DIAGNOSTICS !== "1") return;
  const requestId = requestHeader(request, "x-e2e-request-id");
  const match = E2E_INTAKE_PATH.exec(request.url ?? "");
  if (!E2E_REQUEST_ID.test(requestId) || !match) return;
  nodeRuntime.console.info("E2E_DIAG", JSON.stringify({
    milestone,
    request_id: requestId,
    method: request.method ?? "UNKNOWN",
    route_family: "/api[/demo]/clm/zero-touch/cases/{case_id}/intake/documents",
    case_id: match[1],
    monotonic_ms: Number(nodeRuntime.process.hrtime.bigint() / 1_000_000n),
    pid: nodeRuntime.process.pid,
    frontend_port: Number(nodeRuntime.process.env.CLM_E2E_FRONTEND_PORT),
    ...(status === undefined ? {} : { status }),
  }));
}

function requestHeader(request: DevelopmentHttpRequest, name: string): string {
  const value = request.headers?.[name];
  return Array.isArray(value) ? value.join(",") : value ?? "";
}

function resourceExtension(pathname: string): string | null {
  const lastSegment = pathname.slice(pathname.lastIndexOf("/") + 1);
  const stem = lastSegment.split(";", 1)[0];
  const match = /\.([^.]+)$/.exec(stem);
  return match?.[1]?.toLowerCase() ?? null;
}

function acceptsHtml(accept: string): boolean {
  let positiveHtmlRange = false;

  for (const rawRange of accept.split(",")) {
    const parts = rawRange.split(";");
    if (parts[0]?.trim().toLowerCase() !== "text/html") continue;

    let quality = 1;
    let qualitySeen = false;
    const parameterNames = new Set<string>();
    for (const rawParameter of parts.slice(1)) {
      const parameter = rawParameter.trim();
      const separator = parameter.indexOf("=");
      if (separator <= 0 || separator !== parameter.lastIndexOf("=")) return false;

      const name = parameter.slice(0, separator).trim().toLowerCase();
      const value = parameter.slice(separator + 1).trim();
      if (!HTTP_TOKEN.test(name) || !HTTP_PARAMETER_VALUE.test(value)) return false;
      if (parameterNames.has(name)) return false;
      parameterNames.add(name);

      if (name !== "q") continue;
      if (qualitySeen || !HTTP_QUALITY.test(value)) return false;
      qualitySeen = true;
      quality = Number(value);
    }

    if (quality > 0) positiveHtmlRange = true;
  }

  return positiveHtmlRange;
}

interface CanonicalPathResult {
  readonly ambiguous: boolean;
  readonly forms: readonly string[];
}

function hasValidPercentEncoding(pathname: string): boolean {
  for (let index = pathname.indexOf("%"); index >= 0; index = pathname.indexOf("%", index + 3)) {
    if (!/^[0-9a-f]{2}$/i.test(pathname.slice(index + 1, index + 3))) return false;
  }
  return true;
}

function hasDotSegment(pathname: string): boolean {
  return pathname.split("/").some((segment) => segment === "." || segment === "..");
}

function isUnambiguousAbsolutePath(pathname: string): boolean {
  return pathname.startsWith("/")
    && !pathname.includes("?")
    && !pathname.includes("#")
    && !pathname.includes("\\")
    && !CONTROL_CHARACTER.test(pathname)
    && !hasDotSegment(pathname);
}

function canonicalPathForms(rawPath: string): CanonicalPathResult {
  if (!isUnambiguousAbsolutePath(rawPath)) return { ambiguous: true, forms: [rawPath] };

  const forms = [rawPath];
  let current = rawPath;
  for (let round = 0; round < MAX_PATH_DECODE_ROUNDS; round += 1) {
    if (!current.includes("%")) return { ambiguous: false, forms };
    if (!hasValidPercentEncoding(current) || ENCODED_PATH_AMBIGUITY.test(current)) {
      return { ambiguous: true, forms };
    }

    let decoded: string;
    try {
      decoded = decodeURIComponent(current);
    } catch {
      return { ambiguous: true, forms };
    }
    if (!isUnambiguousAbsolutePath(decoded)) return { ambiguous: true, forms };
    if (decoded === current) return { ambiguous: true, forms };

    forms.push(decoded);
    current = decoded;
  }

  return { ambiguous: current.includes("%"), forms };
}

function isResourcePath(pathname: string): boolean {
  const lastSegment = pathname.slice(pathname.lastIndexOf("/") + 1);
  if (lastSegment.endsWith(".")) return true;
  const extension = resourceExtension(pathname);
  return extension !== null && RESOURCE_EXTENSIONS.has(extension);
}

function isApiPath(pathname: string): boolean {
  const lowerPath = pathname.toLowerCase();
  return lowerPath === "/api" || lowerPath.startsWith("/api/");
}

function isReservedResourcePath(pathname: string): boolean {
  const lowerPath = pathname.toLowerCase();
  const reservedTrees = [
    "/@vite",
    "/@fs",
    "/@id",
    "/@react-refresh",
    "/src",
    "/node_modules",
    "/assets",
    "/__open-in-editor",
  ];
  if (reservedTrees.some((prefix) => lowerPath === prefix || lowerPath.startsWith(`${prefix}/`))) {
    return true;
  }
  return /^\/__vite(?:$|[\/_])/.test(lowerPath);
}

function rawPathFromRequestTarget(target: string): string | null {
  const queryIndex = target.indexOf("?");
  const rawPath = queryIndex < 0 ? target : target.slice(0, queryIndex);
  return rawPath.startsWith("/") && !rawPath.includes("#") ? rawPath : null;
}

function isSpaDocumentNavigation(rawPath: string, request: DevelopmentHttpRequest): boolean {
  if (request.method !== "GET" && request.method !== "HEAD") return false;

  const canonical = canonicalPathForms(rawPath);
  if (canonical.ambiguous) return false;
  if (canonical.forms.some((pathname) => (
    isApiPath(pathname)
    || isReservedResourcePath(pathname)
    || isResourcePath(pathname)
    || pathname.split("/").some((segment) => segment.includes(";"))
  ))) return false;

  if (!acceptsHtml(requestHeader(request, "accept"))) return false;

  const destination = requestHeader(request, "sec-fetch-dest").trim().toLowerCase();
  return destination === "" || DOCUMENT_DESTINATIONS.has(destination);
}

function isViteOwnedHtmlRequest(
  currentPath: string | null,
  originalPath: string | null,
  request: DevelopmentHttpRequest,
): boolean {
  if (request.method !== "GET" && request.method !== "HEAD") return false;
  if (currentPath === null || originalPath === null || !currentPath.toLowerCase().endsWith(".html")) {
    return false;
  }

  const canonical = canonicalPathForms(originalPath);
  return !canonical.ambiguous && !canonical.forms.some((pathname) => (
    isApiPath(pathname)
    || isReservedResourcePath(pathname)
    || pathname.split("/").some((segment) => segment.includes(";"))
  ));
}

function developmentNavigationFallback(): Plugin {
  return {
    name: "phase15c-development-navigation-fallback",
    apply: "serve",
    configureServer(server) {
      return () => {
        server.middlewares.use((request, _response, next) => {
          const httpRequest = request as unknown as DevelopmentHttpRequest;
          const currentTarget = httpRequest.url ?? "/";
          const currentPath = rawPathFromRequestTarget(currentTarget);
          const originalTarget = httpRequest.originalUrl ?? currentTarget;
          const originalPath = rawPathFromRequestTarget(originalTarget);

          // Vite's MPA fallback has already resolved existing HTML. Preserve that
          // rewrite so indexHtmlMiddleware remains the only HTML-serving owner.
          if (isViteOwnedHtmlRequest(currentPath, originalPath, httpRequest)) {
            next();
            return;
          }

          if (originalPath !== null && isSpaDocumentNavigation(originalPath, httpRequest)) {
            httpRequest.url = "/index.html";
          } else if (currentPath?.toLowerCase().endsWith(".html")) {
            // Do not let an unsafe method or a Vite-reserved URL rewritten by an
            // earlier middleware accidentally enter indexHtmlMiddleware.
            httpRequest.url = `${currentPath}/`;
          }
          // Admitted navigation reaches Vite's index middleware. Everything else
          // reaches Vite's own final not-found middleware.
          next();
        });
      };
    },
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  const backendProxyTarget = env.VITE_BACKEND_PROXY_TARGET || "http://127.0.0.1:8000";
  const aiAssistantProxyTarget = env.VITE_AI_ASSISTANT_PROXY_TARGET || "http://127.0.0.1:8100";
  const guardedE2eBackendAgent = env.CLM_E2E_FRONTEND_PORT
    ? new HttpAgent({ keepAlive: true, maxFreeSockets: 1 })
    : undefined;

  return {
    appType: "mpa",
    plugins: [react(), developmentNavigationFallback()],
    server: {
      proxy: {
        // Separate AI Assistant service (apps/assistant). It sits under /api so the
        // browser sends the session cookie (scoped to /api); listed before "/api" to win.
        "/api/assistant": {
          target: aiAssistantProxyTarget,
          rewrite: (path: string) => path.replace(/^\/api\/assistant/, "/assistant"),
        },
        "/api": {
          target: backendProxyTarget,
          agent: guardedE2eBackendAgent,
          configure(proxy) {
            const diagnosticProxy = proxy as unknown as DiagnosticProxy;
            diagnosticProxy.on("proxyReq", (proxyRequest, request) => {
              e2eProxyMilestone(request, "VITE_PROXY_REQUEST_ACCEPTED");
              e2eProxyMilestone(request, "VITE_PROXY_UPSTREAM_STARTED");
              proxyRequest.once("finish", () => {
                e2eProxyMilestone(request, "VITE_PROXY_UPSTREAM_COMPLETE");
              });
            });
            diagnosticProxy.on("proxyRes", (proxyResponse, request) => {
              e2eProxyMilestone(request, "VITE_PROXY_UPSTREAM_RESPONSE", proxyResponse.statusCode);
              proxyResponse.once("end", () => {
                e2eProxyMilestone(request, "VITE_PROXY_RESPONSE_COMPLETE", proxyResponse.statusCode);
              });
            });
          },
        },
      },
    },
    test: {
      environment: "node",
    },
  };
});
