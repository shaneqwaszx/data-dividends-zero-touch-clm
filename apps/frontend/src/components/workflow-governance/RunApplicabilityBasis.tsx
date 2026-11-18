// A run's applicability basis (ADR-018 §3.5, §5; owner decision B11). Display only: the backend
// decides and freezes the basis. The status is always shown with its environment, and no raw source
// value is ever shown. The escalation action is UI shaping only: the backend reauthorizes it.

import { useMutation } from "@tanstack/react-query";
import { useId, useState } from "react";

import { ApiError } from "../../api";
import { workflowErrorMessage } from "../../workflowApi";
import {
  ESCALATION_REASON_MAX,
  ESCALATION_REASON_MIN,
  escalateApplicability,
} from "../../workflowRecoveryApi";
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

export interface EscalationTarget {
  caseId: string;
  run: { run_id: string; revision: number };
  /** Reload the run after an escalation or a 409. */
  onChanged: () => void;
}

/** The audited "Apply all conditional steps" (ADR-018 §3.5 F6), with a mandatory reason. Never retried. */
function EscalationAction({ target }: { target: EscalationTarget }) {
  const id = useId();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const escalate = useMutation({
    mutationFn: () => escalateApplicability(target.caseId, {
      run_id: target.run.run_id, expected_revision: target.run.revision, reason: reason.trim(),
    }),
    retry: false,
    onMutate: () => setMessage(null),
    onSuccess: () => {
      setOpen(false);
      setReason("");
      setMessage("All conditional steps now apply to this run. Complete the added steps before sending.");
      target.onChanged();
    },
    onError: error => {
      if (error instanceof ApiError && error.status === 409) {
        setMessage("This run changed while you were working. Nothing was changed. It has been reloaded; check it and try again.");
        setOpen(false);
        target.onChanged();
      } else {
        setMessage(workflowErrorMessage(error));
      }
    },
  });
  const length = reason.trim().length;
  const valid = length >= ESCALATION_REASON_MIN && length <= ESCALATION_REASON_MAX;
  return (
    <div data-testid="run-applicability-escalation" style={{ marginTop: 8 }}>
      {message && <p role="status" style={{ margin: "0 0 6px" }}>{message}</p>}
      {!open && (
        <button type="button" className="btn btn-secondary" aria-expanded={false} aria-controls={`${id}-form`}
          onClick={() => { setMessage(null); setReason(""); setOpen(true); }}>Apply all conditional steps…</button>
      )}
      <div id={`${id}-form`}>
        {open && <>
          <p style={{ margin: "0 0 6px" }}>
            This only adds steps: every conditional step will apply to this run, permanently. Answers and confirmations
            are kept. It can't be undone, and it is audited with your name and reason.
          </p>
          <label htmlFor={`${id}-reason`}>Reason (required, {ESCALATION_REASON_MIN}–{ESCALATION_REASON_MAX} characters)</label>
          <textarea id={`${id}-reason`} className="input" value={reason} maxLength={ESCALATION_REASON_MAX + 40}
            aria-invalid={reason.length > 0 && !valid} aria-describedby={`${id}-count`} disabled={escalate.isPending}
            onChange={event => setReason(event.target.value)} />
          <p id={`${id}-count`} className="text-muted" aria-live="polite" style={{ margin: "2px 0" }}>{length} / {ESCALATION_REASON_MAX}
            {reason.length > 0 && length < ESCALATION_REASON_MIN && ` · at least ${ESCALATION_REASON_MIN} characters`}
            {length > ESCALATION_REASON_MAX && ` · at most ${ESCALATION_REASON_MAX} characters`}
          </p>
          <div className="case-header-actions" style={{ justifyContent: "flex-start" }}>
            <button type="button" className="btn btn-danger" disabled={!valid || escalate.isPending} onClick={() => escalate.mutate()}>
              Apply all conditional steps
            </button>
            <button type="button" className="btn btn-ghost" disabled={escalate.isPending} onClick={() => { setOpen(false); setReason(""); }}>Cancel</button>
          </div>
        </>}
      </div>
    </div>
  );
}

export function RunApplicabilityBasis({ view, escalation = null }: {
  view: RunApplicabilityView | null | undefined;
  /** Offered to case fillers (UI shaping only) while an unescalated conflict holds the run. */
  escalation?: EscalationTarget | null;
}) {
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
          {!conflict.escalated && escalation && <EscalationAction target={escalation} />}
        </div>
      )}
    </section>
  );
}
