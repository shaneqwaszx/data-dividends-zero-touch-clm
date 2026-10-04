import { useEffect, useRef, type ReactNode } from "react";

import type { ZeroTouchCaseSummary } from "../types";

export function onboardingIsExecuting(summary: ZeroTouchCaseSummary | null, busy: boolean, error: string | null): boolean {
  if (error || summary?.technical_failure || summary?.active_exceptions.length) return false;
  if (summary && ["WAITING_FOR_REVIEW", "TECHNICAL_FAILURE", "RECOVERY_PENDING", "COMPLETED"].includes(summary.status)) return false;
  return busy || summary?.status === "RUNNING" || summary?.status === "RESUMING";
}

export function onboardingExecutionMessage(summary: ZeroTouchCaseSummary | null, progress?: string | null): string {
  if (progress) return progress;
  const messages: Record<string, string> = {
    REGISTRY: "Verifying registry information…",
    GOLDTIER_SEARCH: "Searching for an existing customer…",
    DOCUMENT: "Processing uploaded documents…",
    RECONCILIATION: "Reconciling registry and document observations…",
    OWNERSHIP: "Calculating ownership…",
    READINESS: "Preparing GoldTier submission…",
    MOCK_GOLDTIER: "Sending reviewed GoldTier submission…",
  };
  return messages[summary?.current_stage ?? ""] ?? "Waiting for the current backend stage…";
}

export default function OnboardingWorkspace({ active, message, children }: {
  active: boolean;
  message: string;
  children: ReactNode;
}) {
  const content = useRef<HTMLDivElement>(null);
  const status = useRef<HTMLDivElement>(null);
  const priorFocus = useRef<HTMLElement | null>(null);
  useEffect(() => {
    if (active) {
      const focused = document.activeElement;
      if (focused instanceof HTMLElement && content.current?.contains(focused)) {
        priorFocus.current = focused;
        status.current?.focus({ preventScroll: true });
      }
    } else if (priorFocus.current) {
      if (priorFocus.current.isConnected && document.activeElement === document.body) {
        priorFocus.current.focus({ preventScroll: true });
      }
      priorFocus.current = null;
    }
  }, [active]);
  return (
    <div className={`processing-workspace${active ? " processing-workspace--active" : ""}`} aria-busy={active}>
      <div ref={content} className="processing-workspace__content" {...(active ? { inert: "" } : {})}>
        {children}
      </div>
      {active && <div ref={status} className="processing-workspace__overlay" role="status" aria-live="polite" tabIndex={-1}>
        <span className="processing-workspace__spinner" aria-hidden="true" />
        <strong>Processing onboarding</strong>
        <span>{message}</span>
      </div>}
    </div>
  );
}
