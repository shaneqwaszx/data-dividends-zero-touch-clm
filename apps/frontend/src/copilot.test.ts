// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { configureAuthenticatedTransport } from "./api";
import { fetchCopilotBrief } from "./copilot";
import { clearSessionQueries, createSessionQueryClient } from "./queryClient";

afterEach(() => {
  configureAuthenticatedTransport({ csrfToken: null, onUnauthorized: null });
  vi.unstubAllGlobals();
});

function expired(): Response {
  return new Response(JSON.stringify({ detail: { message: "Please sign in again." } }), {
    status: 401, headers: { "Content-Type": "application/json" },
  });
}

describe("Copilot and the owning session transport", () => {
  it("clears authenticated business cache when the current Copilot session expires", async () => {
    const cache = createSessionQueryClient();
    cache.setQueryData(["auth", "test-user", "cases", "detail", "test-case"], { state: "REVIEW_REQUIRED" });
    const clear = vi.fn(() => clearSessionQueries(cache));
    configureAuthenticatedTransport({ csrfToken: null, onUnauthorized: clear });
    vi.stubGlobal("fetch", vi.fn(async () => expired()));
    await expect(fetchCopilotBrief("test-case")).rejects.toThrow("Please sign in again.");
    expect(clear).toHaveBeenCalledTimes(1);
    expect(cache.getQueryCache().getAll()).toEqual([]);
  });

  it("does not let an old Copilot401 clear a replacement session", async () => {
    let finish!: (response: Response) => void;
    const previous = vi.fn();
    configureAuthenticatedTransport({ csrfToken: null, onUnauthorized: previous });
    vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>((resolve) => { finish = resolve; })));
    const pending = fetchCopilotBrief("previous-case");
    const current = vi.fn();
    configureAuthenticatedTransport({ csrfToken: null, onUnauthorized: current });
    finish(expired());
    await expect(pending).rejects.toThrow();
    expect(previous).not.toHaveBeenCalled();
    expect(current).not.toHaveBeenCalled();
  });
});
