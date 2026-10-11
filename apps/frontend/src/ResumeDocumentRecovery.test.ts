import { afterEach, expect, it, vi } from "vitest";
import { resumeZeroTouchCase } from "./api";
import type { ZeroTouchCaseSummary } from "./types";

afterEach(() => vi.unstubAllGlobals());

const context = {
  automation_id: "synthetic-automation", version: 7,
  case: { case_id: "synthetic-case", events: [{}, {}] }, clm: { version: 4 },
} as unknown as ZeroTouchCaseSummary;

it("binds explicit document recovery to identity and all current versions", async () => {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: "WAITING_FOR_REVIEW" })));
  vi.stubGlobal("fetch", fetch);
  await resumeZeroTouchCase("synthetic-case", context);
  expect(fetch).toHaveBeenCalledTimes(1);
  const [url, request] = fetch.mock.calls[0];
  expect(url).toBe("/api/clm/zero-touch/cases/synthetic-case/resume");
  expect(request.method).toBe("POST"); expect(request.credentials).toBe("include");
  expect(Object.fromEntries(new Headers(request.headers).entries())).toEqual({
    "x-automation-id": "synthetic-automation", "x-automation-version": "7",
    "x-clm-version": "4", "x-case-event-count": "2",
  });
});

it("rejects another case's captured recovery context before any request", async () => {
  const fetch = vi.fn(); vi.stubGlobal("fetch", fetch);
  await expect(resumeZeroTouchCase("different-case", context)).rejects.toThrow("Reload the current case");
  expect(fetch).not.toHaveBeenCalled();
});
