/// <reference types="vitest/config" />

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

  return {
    appType: "mpa",
    plugins: [react(), developmentNavigationFallback()],
    server: {
      proxy: {
        "/api": backendProxyTarget,
      },
    },
    test: {
      environment: "node",
    },
  };
});
