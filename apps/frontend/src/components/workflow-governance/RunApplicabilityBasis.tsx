// A run's applicability basis (ADR-018 §3.5, §5; owner decision B11). Display only: the backend
// decides and freezes the basis. The status is always shown with its environment, and no raw source
// value is ever shown.

import type {
  ApplicabilityBasisReason,
  RunApplicabilityView,
  SourceEnvironment,
} from "../../workflowGovernanceTypes";
import { CONDITIONAL_FORM_LABEL } from "./applicability";

const ENVIRONMENT_LABEL: Record<SourceEnvironment, string> = { MOCK: "Mock", SANDBOX: "Sandbox" };

export const BASIS_REASON_TEXT: Record<ApplicabilityBasisReason, string> = {
  REGISTRY_BINDING: "Bound to the registry record.",
  NO_ENTITY: "No entity is linked yet.",
  NO_BINDING: "No registry record is bound yet.",
  OTHER_FORM: "The registry reports another legal form.",
  CONFLICTING_CLASSIFICATION: "The registry classification conflicts.",
  AMBIGUOUS_BINDING: "The registry binding is ambiguous.",
  TOO_LATE_TO_NARROW: "The registry result arrived after a conditional step was already reached.",
  NO_CASE_RECORD: "There is no case record to read.",
  READ_FAILED: "The registry result could not be read.",
};

export function environmentLabel(environment: SourceEnvironment | null): string {
  return environment ? ENVIRONMENT_LABEL[environment] ?? environment : "no registry source";
}

const formLabel = (form: string | null) => (form ? CONDITIONAL_FORM_LABEL[form as keyof typeof CONDITIONAL_FORM_LABEL] ?? form : "—");

/** "Registry-bound (Mock): LLP" or "Not verified (Mock): all conditional steps apply". */
export function basisHeadline(view: RunApplicabilityView): string {
  const environment = environmentLabel(view.source_environment);
  return view.status === "REGISTRY_BOUND"
    ? `Registry-bound (${environment}): ${formLabel(view.legal_form)}`
    : `Not verified (${environment}): all conditional steps apply`;
}

export function RunApplicabilityBasis({ view }: { view: RunApplicabilityView | null | undefined }) {
  if (!view) return null;
  const { conflict } = view;
  const allApply = view.effective_legal_form === null;
  return (
    <section className="card" aria-label="Entity applicability basis" data-testid="run-applicability" style={{ marginBottom: 12 }}>
      <p className="card-kicker">Entity applicability</p>
      <p style={{ margin: 0 }}>
        <strong data-testid="run-applicability-basis">{basisHeadline(view)}</strong>{" "}
        <span className={view.status === "REGISTRY_BOUND" ? "tag tag-ok" : "tag tag-neutral"}>
          {view.status === "REGISTRY_BOUND" ? "REGISTRY_BOUND" : "UNVERIFIED"} · {environmentLabel(view.source_environment)}
        </span>
      </p>
      <p className="text-muted" style={{ margin: "4px 0 0" }}>
        {BASIS_REASON_TEXT[view.reason] ?? view.reason}{" "}
        {view.frozen ? "The basis is frozen for this run." : "The basis is set once, at the first eligible registry binding."}
      </p>
      {view.status === "REGISTRY_BOUND" && allApply && (
        <p data-testid="run-applicability-effective" style={{ margin: "4px 0 0" }}>Effective: every conditional step applies to this run.</p>
      )}
      {conflict && (
        <div className="ds-banner ds-banner-warn" role="alert" data-testid="run-applicability-conflict" style={{ marginTop: 8 }}>
          <p style={{ margin: 0 }}>
            <strong>Applicability conflict.</strong> The registry now reports{" "}
            {conflict.observed_status === "REGISTRY_BOUND" ? formLabel(conflict.observed_legal_form) : "an unverified legal form"}, which differs
            from the frozen basis. The case is held before send until the conflict is escalated.
          </p>
          {conflict.escalated
            ? <p style={{ margin: "4px 0 0" }}>Escalated by {conflict.escalated_by ?? "—"}{conflict.escalated_at ? ` at ${new Date(conflict.escalated_at).toLocaleString()}` : ""}: every conditional step now applies to this run, permanently.</p>
            : <p style={{ margin: "4px 0 0" }}>The recovery is the audited escalation "Apply all conditional steps": every conditional step then applies to this run, permanently, and the added steps must be completed before send.</p>}
        </div>
      )}
    </section>
  );
}
