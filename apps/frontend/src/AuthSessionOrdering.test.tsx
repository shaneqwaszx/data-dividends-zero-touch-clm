// @vitest-environment jsdom

import { StrictMode, act, type ReactNode } from "react";
import { createRoot, type Root } from "react-dom/client";
import { useQueryClient, type QueryClient } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  configureAuthenticatedTransport,
  fetchExecutionProfile,
  updateCasePriority,
} from "./api";
import { AuthProvider, useAuth } from "./auth";
import type { AuthSession, AuthenticatedProfile } from "./types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean })
  .IS_REACT_ACT_ENVIRONMENT = true;

interface Deferred<T> {
  promise: Promise<T>;
  resolve(value: T): void;
}

interface RequestRecord {
  path: string;
  init: RequestInit;
  deferred: Deferred<Response>;
}

type CapturedResult<T> =
  | { ok: true; value: T }
  | { ok: false; error: unknown };

function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((promiseResolve) => {
    resolve = promiseResolve;
  });
  return { promise, resolve };
}

function capture<T>(promise: Promise<T>): Promise<CapturedResult<T>> {
  return promise.then(
    (value) => ({ ok: true, value }),
    (error: unknown) => ({ ok: false, error }),
  );
}

function profile(userId: string): AuthenticatedProfile {
  return {
    user_id: userId,
    display_name: userId === "maya-lim" ? "Maya Lim" : "Sophia Ng",
    role: "CLIENT_ONBOARDER",
    team_id: userId === "maya-lim" ? "TEAM_A" : "TEAM_B",
    team_display_name: userId === "maya-lim" ? "Alpha" : "Beta",
    team_type: "Corporate Client Onboarding",
    team_description: "Synthetic team",
    client_scope_label: userId === "maya-lim" ? "Alpha" : "Beta",
    capabilities: ["POLICY_VIEW", "CASE_ACCESS"],
  };
}

function session(userId: string, csrfToken: string): AuthSession {
  return { profile: profile(userId), csrf_token: csrfToken };
}

function jsonResponse(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function unauthorizedResponse(): Response {
  return jsonResponse({
    detail: {
      code: "AUTHENTICATION_REQUIRED",
      message: "Authentication is required.",
    },
  }, 401);
}

function createControlledTransport() {
  const records: RequestRecord[] = [];
  const fetchMock = vi.fn((input: RequestInfo | URL, init: RequestInit = {}) => {
    const path = new URL(String(input), "http://frontend.test").pathname;
    const response = deferred<Response>();
    records.push({ path, init, deferred: response });
    if (path === "/api/clm/zero-touch/dashboard") {
      response.resolve(jsonResponse({}));
    } else if (path === "/api/clm/zero-touch/cases" && init.method !== "PATCH") {
      response.resolve(jsonResponse([]));
    }
    return response.promise;
  });
  vi.stubGlobal("fetch", fetchMock);

  return {
    records,
    byPath(path: string): RequestRecord[] {
      return records.filter((record) => record.path === path);
    },
    async waitFor(path: string, count: number): Promise<RequestRecord[]> {
      await vi.waitFor(() => {
        expect(records.filter((record) => record.path === path)).toHaveLength(count);
      });
      return records.filter((record) => record.path === path);
    },
  };
}

type CurrentAuth = ReturnType<typeof useAuth>;

const mountedRoots: Root[] = [];

async function mountAuthProvider(strict = true) {
  const container = document.createElement("div");
  document.body.append(container);
  const root = createRoot(container);
  mountedRoots.push(root);
  let currentAuth: CurrentAuth | null = null;
  let currentQueryClient: QueryClient | null = null;

  function Probe() {
    currentAuth = useAuth();
    currentQueryClient = useQueryClient();
    return (
      <div>
        <span data-auth-status>{currentAuth.status}</span>
        <span data-auth-user>{currentAuth.session?.profile.user_id ?? "none"}</span>
        <span data-auth-error>{currentAuth.error ?? "none"}</span>
      </div>
    );
  }

  const content: ReactNode = <AuthProvider><Probe /></AuthProvider>;
  await act(async () => {
    root.render(strict ? <StrictMode>{content}</StrictMode> : content);
  });

  return {
    auth(): CurrentAuth {
      if (!currentAuth) throw new Error("AuthProvider probe has not rendered");
      return currentAuth;
    },
    status(): string {
      return container.querySelector("[data-auth-status]")?.textContent ?? "missing";
    },
    user(): string {
      return container.querySelector("[data-auth-user]")?.textContent ?? "missing";
    },
    error(): string {
      return container.querySelector("[data-auth-error]")?.textContent ?? "missing";
    },
    queryClient(): QueryClient {
      if (!currentQueryClient) throw new Error("Session QueryClient has not rendered");
      return currentQueryClient;
    },
  };
}

async function resolve(record: RequestRecord, response: Response): Promise<void> {
  await act(async () => {
    record.deferred.resolve(response);
    await record.deferred.promise;
  });
}

async function startLogin(
  auth: () => CurrentAuth,
  userId: string,
): Promise<{ result: Promise<void> }> {
  let loginResult!: Promise<void>;
  await act(async () => {
    loginResult = auth().login(userId, "test-only-credential");
  });
  return { result: loginResult };
}

async function completeLogin(
  auth: () => CurrentAuth,
  transport: ReturnType<typeof createControlledTransport>,
  userId: string,
  csrfToken: string,
): Promise<void> {
  const { result: loginResult } = await startLogin(auth, userId);
  const [request] = await transport.waitFor("/api/auth/login", 1);
  await act(async () => {
    request.deferred.resolve(jsonResponse(session(userId, csrfToken)));
    await loginResult;
  });
}

afterEach(async () => {
  for (const root of mountedRoots.splice(0)) {
    await act(async () => root.unmount());
  }
  document.body.replaceChildren();
  configureAuthenticatedTransport({ csrfToken: null, onUnauthorized: null });
  vi.unstubAllGlobals();
});

describe("AuthProvider session ordering through the real authenticated transport", () => {
  it("A preserves a successful login when an obsolete StrictMode restoration returns 401", async () => {
    const transport = createControlledTransport();
    const harness = await mountAuthProvider();
    const restorations = await transport.waitFor("/api/auth/me", 2);

    await resolve(restorations[1], unauthorizedResponse());
    await vi.waitFor(() => expect(harness.status()).toBe("anonymous"));

    await completeLogin(harness.auth, transport, "maya-lim", "csrf-login-a");
    await vi.waitFor(() => expect(harness.user()).toBe("maya-lim"));

    await resolve(restorations[0], unauthorizedResponse());

    await vi.waitFor(() => expect(harness.status()).toBe("authenticated"));
    expect(harness.user()).toBe("maya-lim");
  });

  it("B ignores an old-session 401 after a different user's new session is accepted", async () => {
    const transport = createControlledTransport();
    const harness = await mountAuthProvider(false);
    const [restoration] = await transport.waitFor("/api/auth/me", 1);
    await resolve(restoration, jsonResponse(session("maya-lim", "csrf-first")));
    await vi.waitFor(() => expect(harness.user()).toBe("maya-lim"));

    const oldRequestResult = capture(fetchExecutionProfile());
    const oldRequest = transport.records.at(-1)!;
    await completeLogin(harness.auth, transport, "sophia-ng", "csrf-second");
    await vi.waitFor(() => expect(harness.user()).toBe("sophia-ng"));

    await resolve(oldRequest, unauthorizedResponse());
    expect(await oldRequestResult).toMatchObject({ ok: false, error: { status: 401 } });

    expect(harness.status()).toBe("authenticated");
    expect(harness.user()).toBe("sophia-ng");
  });

  it("C ignores an old-session 401 after a new session for the same user is accepted", async () => {
    const transport = createControlledTransport();
    const harness = await mountAuthProvider(false);
    const [restoration] = await transport.waitFor("/api/auth/me", 1);
    await resolve(restoration, jsonResponse(session("maya-lim", "csrf-first")));
    await vi.waitFor(() => expect(harness.user()).toBe("maya-lim"));

    const oldRequestResult = capture(fetchExecutionProfile());
    const oldRequest = transport.records.at(-1)!;
    const existingLoginCount = transport.byPath("/api/auth/login").length;
    const { result: loginResult } = await startLogin(harness.auth, "maya-lim");
    const loginRequests = await transport.waitFor("/api/auth/login", existingLoginCount + 1);
    await act(async () => {
      loginRequests.at(-1)!.deferred.resolve(jsonResponse(session("maya-lim", "csrf-second")));
      await loginResult;
    });

    await resolve(oldRequest, unauthorizedResponse());
    expect(await oldRequestResult).toMatchObject({ ok: false, error: { status: 401 } });

    expect(harness.status()).toBe("authenticated");
    expect(harness.user()).toBe("maya-lim");
  });

  it("D1 does not replace a later login with an obsolete successful StrictMode restoration", async () => {
    const transport = createControlledTransport();
    const harness = await mountAuthProvider();
    const restorations = await transport.waitFor("/api/auth/me", 2);
    await resolve(restorations[1], unauthorizedResponse());
    await vi.waitFor(() => expect(harness.status()).toBe("anonymous"));
    await completeLogin(harness.auth, transport, "maya-lim", "csrf-login-d1");

    await resolve(restorations[0], jsonResponse(session("sophia-ng", "csrf-obsolete")));

    expect(harness.status()).toBe("authenticated");
    expect(harness.user()).toBe("maya-lim");
  });

  it("D2 does not resurrect an obsolete successful restoration after logout", async () => {
    const transport = createControlledTransport();
    const harness = await mountAuthProvider();
    const restorations = await transport.waitFor("/api/auth/me", 2);
    await resolve(restorations[1], unauthorizedResponse());
    await vi.waitFor(() => expect(harness.status()).toBe("anonymous"));
    await completeLogin(harness.auth, transport, "maya-lim", "csrf-login-d");

    let logoutResult!: Promise<void>;
    await act(async () => {
      logoutResult = harness.auth().logout();
    });
    const [logoutRequest] = await transport.waitFor("/api/auth/logout", 1);
    await act(async () => {
      logoutRequest.deferred.resolve(new Response(null, { status: 204 }));
      await logoutResult;
    });
    expect(harness.status()).toBe("anonymous");

    await resolve(restorations[0], jsonResponse(session("maya-lim", "csrf-obsolete")));

    expect(harness.status()).toBe("anonymous");
    expect(harness.user()).toBe("none");
  });

  it("E keeps a genuine current-session 401 fail-closed and removes CSRF from later requests", async () => {
    const transport = createControlledTransport();
    const harness = await mountAuthProvider(false);
    const [restoration] = await transport.waitFor("/api/auth/me", 1);
    await resolve(restoration, jsonResponse(session("maya-lim", "csrf-current")));
    await vi.waitFor(() => expect(harness.status()).toBe("authenticated"));
    const sensitiveQueryKey = ["auth", "maya-lim", "test-sensitive-query"];
    harness.queryClient().setQueryData(sensitiveQueryKey, { retained: true });
    expect(harness.queryClient().getQueryData(sensitiveQueryKey)).toEqual({ retained: true });

    const currentRequestResult = capture(fetchExecutionProfile());
    const currentRequest = transport.records.at(-1)!;
    await resolve(currentRequest, unauthorizedResponse());
    expect(await currentRequestResult).toMatchObject({ ok: false, error: { status: 401 } });
    await vi.waitFor(() => expect(harness.status()).toBe("anonymous"));
    expect(harness.queryClient().getQueryData(sensitiveQueryKey)).toBeUndefined();

    const updateResult = updateCasePriority("00000000-0000-4000-8000-000000000001", 7);
    const updateRequest = transport.records.at(-1)!;
    expect(new Headers(updateRequest.init.headers).has("X-CSRF-Token")).toBe(false);
    await resolve(updateRequest, jsonResponse({ priority: 7 }));
    await updateResult;
  });

  it("F preserves normal restoration, normal login, and actual denied-login behavior", async () => {
    const transport = createControlledTransport();
    const harness = await mountAuthProvider(false);
    const [restoration] = await transport.waitFor("/api/auth/me", 1);
    await resolve(restoration, jsonResponse(session("maya-lim", "csrf-restored")));
    await vi.waitFor(() => expect(harness.user()).toBe("maya-lim"));

    let logoutResult!: Promise<void>;
    await act(async () => {
      logoutResult = harness.auth().logout();
    });
    const [logoutRequest] = await transport.waitFor("/api/auth/logout", 1);
    await act(async () => {
      logoutRequest.deferred.resolve(new Response(null, { status: 204 }));
      await logoutResult;
    });
    expect(harness.status()).toBe("anonymous");

    const successfulLoginCount = transport.byPath("/api/auth/login").length;
    const { result: successfulLogin } = await startLogin(harness.auth, "sophia-ng");
    const loginRequests = await transport.waitFor("/api/auth/login", successfulLoginCount + 1);
    await act(async () => {
      loginRequests.at(-1)!.deferred.resolve(jsonResponse(session("sophia-ng", "csrf-login-f")));
      await successfulLogin;
    });
    expect(harness.user()).toBe("sophia-ng");

    await act(async () => {
      logoutResult = harness.auth().logout();
    });
    const logoutRequests = await transport.waitFor("/api/auth/logout", 2);
    await act(async () => {
      logoutRequests[1].deferred.resolve(new Response(null, { status: 204 }));
      await logoutResult;
    });

    const deniedLoginCount = transport.byPath("/api/auth/login").length;
    const { result: deniedLogin } = await startLogin(harness.auth, "maya-lim");
    const deniedRequests = await transport.waitFor("/api/auth/login", deniedLoginCount + 1);
    await act(async () => {
      deniedRequests.at(-1)!.deferred.resolve(unauthorizedResponse());
      await expect(deniedLogin).rejects.toMatchObject({ status: 401 });
    });

    expect(harness.status()).toBe("anonymous");
    expect(harness.error()).toBe("Authentication is required.");
  });
});
