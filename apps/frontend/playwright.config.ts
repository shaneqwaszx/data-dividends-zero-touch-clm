import { defineConfig } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:4173";

type OwnedOrigin = {
  port: string;
};

export type BrowserNetworkPolicy = {
  frontend: OwnedOrigin;
  backend: OwnedOrigin;
  allowDirectBackend: boolean;
};

export type BrowserRequestDecision = {
  action: "continue" | "fulfill" | "abort";
  classification:
    | "OWNED_LOOPBACK"
    | "KNOWN_NEUTRALIZED_FONT_STYLESHEET"
    | "BLOCKED_EXTERNAL"
    | "BLOCKED_INVALID";
  reason: string;
};

type RouteLike = {
  request(): { url(): string; resourceType(): string };
  abort(errorCode?: string): Promise<unknown>;
  continue(): Promise<unknown>;
  fulfill(options: {
    status: number;
    contentType: string;
    body: string;
  }): Promise<unknown>;
};

const KNOWN_FONT_STYLESHEET_PATH = "/css2";
const KNOWN_FONT_STYLESHEET_SEARCH =
  "?family=Cormorant+Garamond:wght@400;600&family=Lora:wght@400;600&display=swap";

function parseOwnedOrigin(value: string, name: string): OwnedOrigin {
  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch {
    throw new Error(`${name} must be a valid HTTP loopback origin`);
  }
  if (
    parsed.protocol !== "http:" ||
    !["127.0.0.1", "localhost"].includes(parsed.hostname) ||
    !parsed.port ||
    parsed.username ||
    parsed.password ||
    parsed.pathname !== "/" ||
    parsed.search ||
    parsed.hash
  ) {
    throw new Error(`${name} must be an explicit-port HTTP loopback origin`);
  }
  return { port: parsed.port };
}

export function createBrowserNetworkPolicy(options: {
  frontendOrigin: string;
  backendOrigin: string;
  allowDirectBackend: boolean;
}): BrowserNetworkPolicy {
  return {
    frontend: parseOwnedOrigin(options.frontendOrigin, "frontend origin"),
    backend: parseOwnedOrigin(options.backendOrigin, "backend origin"),
    allowDirectBackend: options.allowDirectBackend,
  };
}

function safeScheme(parsed: URL | null): string {
  const scheme = parsed?.protocol.replace(/:$/, "") ?? "malformed";
  return /^[a-z][a-z0-9+.-]*$/i.test(scheme) ? scheme.toLowerCase() : "unknown";
}

export function classifyBrowserRequest(
  value: string,
  policy: BrowserNetworkPolicy,
  resourceType = "other",
): BrowserRequestDecision {
  let parsed: URL | null = null;
  try {
    parsed = new URL(value);
  } catch {
    return {
      action: "abort",
      classification: "BLOCKED_INVALID",
      reason:
        "scheme=malformed;host=unknown;port=unknown;path=unknown;resource=unknown;classification=BLOCKED_INVALID",
    };
  }

  const loopback = ["127.0.0.1", "localhost"].includes(parsed.hostname);
  const port = parsed.port;
  const portScope =
    port === policy.frontend.port
      ? "frontend"
      : port === policy.backend.port
        ? "backend"
        : "other";
  const ownedPort =
    portScope === "frontend" || (portScope === "backend" && policy.allowDirectBackend);
  if (parsed.protocol === "http:" && loopback && ownedPort) {
    return {
      action: "continue",
      classification: "OWNED_LOOPBACK",
      reason: `scheme=http;host=loopback;port=${portScope};path=owned;resource=${resourceType};classification=OWNED_LOOPBACK`,
    };
  }

  const knownFontStylesheet =
    parsed.protocol === "https:" &&
    parsed.hostname === "fonts.googleapis.com" &&
    parsed.port === "" &&
    !parsed.username &&
    !parsed.password &&
    parsed.pathname === KNOWN_FONT_STYLESHEET_PATH &&
    parsed.search === KNOWN_FONT_STYLESHEET_SEARCH &&
    parsed.hash === "" &&
    resourceType === "stylesheet";
  if (knownFontStylesheet) {
    return {
      action: "fulfill",
      classification: "KNOWN_NEUTRALIZED_FONT_STYLESHEET",
      reason:
        "scheme=https;host=fonts-googleapis;port=other;path=font-css2;resource=stylesheet;classification=KNOWN_NEUTRALIZED_FONT_STYLESHEET",
    };
  }

  const hostScope = loopback
    ? "loopback"
    : parsed.hostname === "fonts.googleapis.com"
      ? "fonts-googleapis"
      : parsed.hostname === "fonts.gstatic.com"
        ? "fonts-gstatic"
        : "non-loopback";
  const pathScope =
    parsed.hostname === "fonts.googleapis.com" && parsed.pathname === "/css2"
      ? "font-css2"
      : "other";
  return {
    action: "abort",
    classification: "BLOCKED_EXTERNAL",
    reason: `scheme=${safeScheme(parsed)};host=${hostScope};loopback=${String(loopback)};port=${portScope};path=${pathScope};resource=${resourceType};classification=BLOCKED_EXTERNAL`,
  };
}

export async function handleBrowserRoute(
  route: RouteLike,
  policy: BrowserNetworkPolicy,
  violations: string[],
): Promise<void> {
  const request = route.request();
  const decision = classifyBrowserRequest(request.url(), policy, request.resourceType());
  if (decision.action === "continue") {
    await route.continue();
    return;
  }
  if (decision.action === "fulfill") {
    await route.fulfill({
      status: 200,
      contentType: "text/css; charset=utf-8",
      body: "",
    });
    return;
  }
  violations.push(decision.reason);
  await route.abort("blockedbyclient");
}

parseOwnedOrigin(baseURL, "PLAYWRIGHT_BASE_URL");

export default defineConfig({
  testDir: "./e2e",
  testMatch: "*.e2e.ts",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 120_000,
  expect: { timeout: 15_000 },
  preserveOutput: "never",
  reporter: [["line"]],
  use: {
    browserName: "chromium",
    baseURL,
    acceptDownloads: false,
    serviceWorkers: "block",
    screenshot: "off",
    trace: "off",
    video: "off",
  },
});
