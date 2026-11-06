import type { ZeroTouchCaseSummary } from "../types";

/** D-124: the explicit step that continues a case held before its review became advisory. */
export default function AdvisoryContinuation({ summary, disabled, onContinue }: {
  summary: ZeroTouchCaseSummary;
  disabled: boolean;
  onContinue: () => void;
}) {
  const continuation = summary.advisory_continuation;
  if (!continuation) return null;
  const retry = summary.status === "TECHNICAL_FAILURE";
  const identityDecision = !retry && summary.current_stage === "GOLDTIER_SEARCH";
  return (
    <section className="ds-banner" aria-label="Continue onboarding" data-testid="advisory-continuation">
      <p>
        {retry
          ? "Continuing onboarding did not finish. Nothing was sent to GoldTier."
          : identityDecision
          ? "The existing-customer decision is saved. Continue to apply it to this case."
          : "The ownership review is advisory here, so this case can continue. The review stays open, and nothing is sent to GoldTier until you confirm."}
      </p>
      {continuation.can_resume
        ? <button type="button" className="btn btn-primary" disabled={disabled} onClick={onContinue}>{retry ? "Try again" : "Continue onboarding"}</button>
        : <p>The onboarding user who created this case can continue it.</p>}
    </section>
  );
}
