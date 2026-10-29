import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchSessionEndReason } from "./api";
import { SESSION_END_TEXT, transitionAuthState, type AuthState } from "./auth";

// D-098: the sign-in page says why a session ended (closed codes only), and never while
// signed in; nothing extends or renews a session.
describe("session end reasons", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("reads only a known reason from a 401, never anything else", async () => {
    const reply = (status: number, reason?: string) => vi.fn(async () => new Response(null, {
      status,
      headers: reason ? { "X-Session-End-Reason": reason } : {},
    }));
    vi.stubGlobal("fetch", reply(401, "SESSION_REPLACED"));
    expect(await fetchSessionEndReason()).toBe("SESSION_REPLACED");
    vi.stubGlobal("fetch", reply(401, "<script>"));
    expect(await fetchSessionEndReason()).toBeNull();
    vi.stubGlobal("fetch", reply(401));
    expect(await fetchSessionEndReason()).toBeNull();
    vi.stubGlobal("fetch", reply(200, "SESSION_EXPIRED"));
    expect(await fetchSessionEndReason()).toBeNull();
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("offline"); }));
    expect(await fetchSessionEndReason()).toBeNull();
  });

  it("explains on the anonymous page only and clears on sign-in", () => {
    const anonymous: AuthState = { status: "anonymous", session: null, error: null };
    const ended = transitionAuthState(anonymous, { type: "SESSION_ENDED", notice: SESSION_END_TEXT.SESSION_REPLACED });
    expect(ended.notice).toContain("signed in somewhere else");
    expect(ended.notice).toContain("keeps running");

    const loading: AuthState = { status: "loading", session: null, error: null };
    expect(transitionAuthState(loading, { type: "SESSION_ENDED", notice: "x" })).toBe(loading);

    const session = { profile: { user_id: "hr-admin" }, csrf_token: "t" } as never;
    expect(transitionAuthState(ended, { type: "AUTHENTICATED", session }).notice).toBeUndefined();
  });
});
