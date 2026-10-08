import { fetchZeroTouchCase, ApiError } from "./api";
import { nextPollingDelay } from "./automationPolling";
import type { ZeroTouchCaseSummary } from "./types";

// UI observation budget, not a provider retry/timeout policy. Use the existing
// progress cadence and backoff ceiling; every request here is a case-summary GET.
export const SUBMISSION_OBSERVATION_READS = 8;

export async function observeSubmissionOutcome({ caseId, signal, isCurrent, onUpdate }: {
  caseId: string;
  signal: AbortSignal;
  isCurrent: () => boolean;
  onUpdate: (summary: ZeroTouchCaseSummary) => void;
}): Promise<boolean> {
  for (let attempt = 0; attempt < SUBMISSION_OBSERVATION_READS; attempt += 1) {
    if (signal.aborted || !isCurrent()) return false;
    try {
      const summary = await fetchZeroTouchCase(caseId, AbortSignal.any([
        signal, AbortSignal.timeout(nextPollingDelay(3)),
      ]));
      if (signal.aborted || !isCurrent() || summary.case.case_id !== caseId) return false;
      onUpdate(summary);
      const state = summary.target_submission?.state;
      if (state && !["NOT_SUBMITTED", "SENDING"].includes(state)) return true;
    } catch (error) {
      if (signal.aborted || !isCurrent()) return false;
      if (error instanceof ApiError && [401, 403, 404].includes(error.status)) throw error;
    }
    if (attempt + 1 < SUBMISSION_OBSERVATION_READS) {
      await new Promise<void>((resolve) => {
        const finish = () => { clearTimeout(timer); signal.removeEventListener("abort", finish); resolve(); };
        const timer = setTimeout(finish, nextPollingDelay(0));
        signal.addEventListener("abort", finish, { once: true });
      });
    }
  }
  return false;
}

export function confirmationResponseMayBeLost(error: unknown): boolean {
  return error instanceof TypeError
    || error instanceof SyntaxError
    || (error instanceof DOMException && ["TimeoutError", "AbortError"].includes(error.name))
    || (error instanceof ApiError && [502, 503, 504].includes(error.status));
}
