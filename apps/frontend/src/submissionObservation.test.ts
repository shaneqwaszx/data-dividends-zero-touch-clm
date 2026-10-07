import { afterEach, describe, expect, it, vi } from "vitest";
import * as api from "./api";
import { observeSubmissionOutcome, SUBMISSION_OBSERVATION_READS } from "./submissionObservation";
import type { ZeroTouchCaseSummary } from "./types";

const summary = (state: string) => ({ case: { case_id: "case-a" }, target_submission: { state } }) as ZeroTouchCaseSummary;
afterEach(() => { vi.restoreAllMocks(); vi.useRealTimers(); });

describe("Bounded case-state observation", () => {
  it.each(["headers", "body"] as const)("stops waiting for stalled confirmation %s without retrying the POST", async (stall) => {
    const controller = new AbortController();
    const deadline = vi.spyOn(AbortSignal, "timeout").mockReturnValue(controller.signal);
    const waitForAbort = () => new Promise<Response>((_resolve, reject) => {
      if (controller.signal.aborted) { reject(controller.signal.reason); return; }
      controller.signal.addEventListener("abort", () => reject(controller.signal.reason), { once: true });
    });
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async (_url, options) => {
      expect(options?.signal).toBe(controller.signal);
      if (stall === "headers") return waitForAbort();
      return { ok: true, json: waitForAbort } as unknown as Response;
    });
    const pending = api.confirmZeroTouchTargetDispatch("case-a", {
      expected_automation_version: 1, expected_clm_version: 1, expected_case_event_count: 1,
    });
    const rejected = expect(pending).rejects.toMatchObject({ name: "TimeoutError" });
    await Promise.resolve();
    controller.abort(new DOMException("Response deadline elapsed", "TimeoutError"));
    await rejected;
    expect(deadline).toHaveBeenCalledWith(8000);
    expect(fetch).toHaveBeenCalledOnce();
  });

  it("reads Sending until success without calling a write", async () => {
    vi.useFakeTimers();
    const read = vi.spyOn(api, "fetchZeroTouchCase").mockResolvedValueOnce(summary("SENDING")).mockResolvedValueOnce(summary("SUBMISSION_CONFIRMED"));
    const confirm = vi.spyOn(api, "confirmZeroTouchTargetDispatch");
    const onUpdate = vi.fn();
    const result = observeSubmissionOutcome({ caseId: "case-a", signal: new AbortController().signal, isCurrent: () => true, onUpdate });
    await vi.advanceTimersByTimeAsync(1000);
    expect(await result).toBe(true); expect(read).toHaveBeenCalledTimes(2); expect(onUpdate).toHaveBeenCalledTimes(2);
    expect(confirm).not.toHaveBeenCalled();
  });
  it.each(["SUBMISSION_OUTCOME_UNCERTAIN", "SUBMISSION_FAILED", "FINALIZATION_PENDING"])("publishes authoritative %s without another POST", async (state) => {
    vi.spyOn(api, "fetchZeroTouchCase").mockResolvedValue(summary(state));
    const onUpdate = vi.fn();
    expect(await observeSubmissionOutcome({ caseId: "case-a", signal: new AbortController().signal, isCurrent: () => true, onUpdate })).toBe(true);
    expect(onUpdate).toHaveBeenCalledWith(summary(state));
  });
  it("stops at its read budget and does not declare a Sending submission failed", async () => {
    vi.useFakeTimers();
    const read = vi.spyOn(api, "fetchZeroTouchCase").mockResolvedValue(summary("SENDING"));
    const result = observeSubmissionOutcome({ caseId: "case-a", signal: new AbortController().signal, isCurrent: () => true, onUpdate: vi.fn() });
    await vi.advanceTimersByTimeAsync(10_000);
    expect(await result).toBe(false); expect(read).toHaveBeenCalledTimes(SUBMISSION_OBSERVATION_READS);
  });
  it("discards a late response after session/case cancellation", async () => {
    let finish!: (value: ZeroTouchCaseSummary) => void;
    vi.spyOn(api, "fetchZeroTouchCase").mockReturnValue(new Promise((resolve) => { finish = resolve; }));
    const controller = new AbortController(); const onUpdate = vi.fn();
    const result = observeSubmissionOutcome({ caseId: "case-a", signal: controller.signal, isCurrent: () => true, onUpdate });
    controller.abort(); finish(summary("SUBMISSION_CONFIRMED"));
    expect(await result).toBe(false); expect(onUpdate).not.toHaveBeenCalled();
  });
  it("propagates inaccessible-session errors instead of polling again", async () => {
    const read = vi.spyOn(api, "fetchZeroTouchCase").mockRejectedValue(new api.ApiError("Unavailable", 404, null));
    await expect(observeSubmissionOutcome({ caseId: "case-a", signal: new AbortController().signal, isCurrent: () => true, onUpdate: vi.fn() })).rejects.toMatchObject({ status: 404 });
    expect(read).toHaveBeenCalledOnce();
  });
});
