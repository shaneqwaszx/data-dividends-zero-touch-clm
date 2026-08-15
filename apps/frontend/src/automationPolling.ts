import type { ZeroTouchCaseSummary } from "./types";

export interface AutomationPollingOptions {
  caseId: string;
  generation: number;
  currentGeneration: () => number;
  fetchCase: (caseId: string, signal: AbortSignal) => Promise<ZeroTouchCaseSummary>;
  onUpdate: (summary: ZeroTouchCaseSummary) => void;
  onWarning: (message: string | null) => void;
  shouldContinue: (status: ZeroTouchCaseSummary["status"]) => boolean;
  initialDelayMs?: number;
}

export function nextPollingDelay(failures: number): number {
  return Math.min(1000 * 2 ** Math.min(failures, 3), 8000);
}

export function startAutomationPolling(options: AutomationPollingOptions): () => void {
  let stopped = false;
  let timer = 0;
  let failures = 0;
  let requestActive = false;
  const controller = new AbortController();

  const schedule = (delay: number) => {
    timer = globalThis.setTimeout(() => void poll(), delay) as unknown as number;
  };
  const poll = async () => {
    if (stopped || options.currentGeneration() !== options.generation) return;
    if (requestActive) {
      schedule(250);
      return;
    }
    requestActive = true;
    try {
      const latest = await options.fetchCase(options.caseId, controller.signal);
      if (stopped || options.currentGeneration() !== options.generation) return;
      failures = 0;
      options.onWarning(null);
      options.onUpdate(latest);
      if (options.shouldContinue(latest.status)) schedule(1000);
    } catch {
      if (stopped || controller.signal.aborted) return;
      failures += 1;
      options.onWarning(
        "Live progress refresh is retrying; the last confirmed state remains shown.",
      );
      schedule(nextPollingDelay(failures));
    } finally {
      requestActive = false;
    }
  };

  schedule(options.initialDelayMs ?? 1000);
  return () => {
    stopped = true;
    controller.abort();
    globalThis.clearTimeout(timer);
  };
}
