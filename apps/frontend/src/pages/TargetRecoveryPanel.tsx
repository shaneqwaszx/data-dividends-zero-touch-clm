import { useState } from "react";
import type { TargetRecoveryInput, TargetSearchObservation } from "../api";
import type { AuthenticatedProfile, ZeroTouchCaseSummary } from "../types";

const observationText = {
  CUSTOMER_IDENTITY_VERIFIED: "A matching GoldTier customer was found. A Director can verify and recover a Shell step without creating the customer again. Customer Search does not establish Policy completion.",
  NO_MATCH: "No matching customer was found. The previous operation still cannot be assumed to have failed. Do not resubmit automatically; Director verification is required.",
  AMBIGUOUS: "Multiple possible GoldTier records were found. Director verification is required; none has been selected for recovery.",
  IDENTITY_UNVERIFIED: "GoldTier returned a record whose exact identity could not be verified. A Director must inspect the provider evidence before recovery.",
  CHECK_FAILED: "GoldTier could not be checked safely. Try the read-only check again later.",
};
const display = (operation: string) => operation === "READBACK" ? "Customer readback" : operation.charAt(0) + operation.slice(1).toLowerCase();

export default function TargetRecoveryPanel({ summary, actor, busy, checking, result, error, onCheck, onRecover }: {
  summary: ZeroTouchCaseSummary;
  actor: AuthenticatedProfile;
  busy: boolean;
  checking: boolean;
  result: TargetSearchObservation | null;
  error: string | null;
  onCheck?: () => void;
  onRecover: (input: TargetRecoveryInput) => void;
}) {
  const [confirmedCandidate, setConfirmedCandidate] = useState<string | null>(null);
  const [policyVerified, setPolicyVerified] = useState(false);
  const [policyStatus, setPolicyStatus] = useState<"" | "Requested">("");
  const target = summary.target_submission;
  if (!target || target.state !== "SUBMISSION_OUTCOME_UNCERTAIN") return null;
  const attempted = target.attempted_operations ?? [];
  const completed = target.definitively_completed_operations ?? [];
  const resolved = target.lifecycle_resolved_operations ?? [];
  const affected = attempted.find((item) => !resolved.includes(item))
    ?? summary.target_operations.find((item) => item.status === "OUTCOME_UNCERTAIN")?.operation;
  const observation = result?.submission_id === target.submission_id && "message" in result ? result : null;
  const candidateId = observation?.result === "CUSTOMER_IDENTITY_VERIFIED" ? observation.verified_party_id : null;
  const candidateKey = candidateId ? `${target.submission_id}:${candidateId}:${observation?.checked_at}` : null;
  const director = actor.capabilities.includes("TARGET_RECOVERY");
  const eligible = director && target.recovery_available === true && Boolean(target.submission_id);
  const locked = busy || checking;
  const identity = summary.case.entity ?? summary.case.initial_identity;
  const resolve = (operation: "SHELL" | "POLICY", partyId: string) => onRecover({
    expected_submission_id: target.submission_id!, operation, recovered_party_id: partyId,
    origin: "UNCERTAIN_DURABLE_LEDGER",
    ...(operation === "POLICY" ? {
      provider_policy: target.provider_policy!, provider_policy_status: "Requested" as const,
    } : {}),
  });

  return <section id="case-target-recovery" className="ds-banner ds-banner-warn target-recovery-panel" aria-labelledby="target-recovery-title" aria-busy={locked}>
    <h3 id="target-recovery-title" tabIndex={-1}>GoldTier submission needs verification</h3>
    <p>GoldTier did not return a definitive result for one submission step. The system stopped to prevent a duplicate submission. Your case data and completed work have been preserved.</p>
    <dl className="target-recovery-facts">
      <dt>Affected step</dt><dd>{affected ? display(affected) : "Retained target operation"}</dd>
      <dt>Write attempted</dt><dd>{affected && attempted.includes(affected) ? "Yes — its result remains unconfirmed" : "Inspect retained evidence; the original outcome is unknown"}</dd>
      <dt>Definitively completed</dt><dd>{completed.length ? completed.map(display).join(", ") : "No definitive prefix available"}</dd>
      <dt>Verified recovery retained</dt><dd>{resolved.filter((item) => !completed.includes(item)).map(display).join(", ") || "None"}</dd>
      <dt>Blocked work</dt><dd>The remaining submission steps. Repeating an unconfirmed write could create a duplicate.</dd>
    </dl>
    {onCheck && <button type="button" className="btn btn-secondary" disabled={locked} onClick={onCheck}>{checking ? "Checking GoldTier status…" : "Check GoldTier status"}</button>}
    {!onCheck && <p>The read-only check is unavailable for this retained provider context. A Director must inspect GoldTier evidence.</p>}
    <div role="status" aria-live="polite">
      {observation && <><p>{observation.result === "CUSTOMER_IDENTITY_VERIFIED" && affected === "POLICY"
        ? "A matching GoldTier customer was found. This does not verify the Policy result. A Director must inspect the retained Policy independently before the submission can continue."
        : observationText[observation.result]}</p><p className="control-help">Checked at {new Date(observation.checked_at).toLocaleString()}</p></>}
      {error && <p>{error}</p>}
    </div>
    {!director && <><h4>Director verification required</h4><p>A Director must verify the retained GoldTier result before the submission can continue. Share this case and submission ID with your Director.</p></>}
    {director && !eligible && <p>Director verification required. This operation cannot currently be resolved by the supported browser recovery contract. Inspect provider evidence with the submission ID below; automatic replay remains blocked.</p>}
    {eligible && target.recovery_operation === "SHELL" && <div>
      <h4>Verify the exact GoldTier record</h4>
      <p>Run the safe status check, then compare the exact candidate with the retained identity: {identity?.legal_name} · {identity?.registration_number} · {identity?.country_of_incorporation}.</p>
      {candidateId && <p>Verified GoldTier customer ID: <strong>{candidateId}</strong></p>}
      <label className="target-recovery-attestation"><input type="checkbox" disabled={locked || !candidateKey} checked={Boolean(candidateKey && confirmedCandidate === candidateKey)} onChange={(event) => setConfirmedCandidate(event.target.checked ? candidateKey : null)} /> I verified this exact candidate against the retained case identity.</label>
      <button type="button" className="btn btn-primary" disabled={locked || !candidateId || confirmedCandidate !== candidateKey} onClick={() => candidateId && resolve("SHELL", candidateId)}>Resolve using verified GoldTier record</button>
      <p className="control-help">The backend checks fresh provider evidence again before recording recovery.</p>
    </div>}
    {eligible && target.recovery_operation === "POLICY" && <form onSubmit={(event) => {
      event.preventDefault();
      if (!locked && policyVerified && policyStatus === "Requested" && target.goldtier_id && target.provider_policy) resolve("POLICY", target.goldtier_id);
    }}>
      <h4>Verified provider evidence</h4>
      <p>Customer Search cannot prove that a Policy was created. Inspect the Policy independently in GoldTier, then attest to the matching provider request. Requested does not mean completed KYC or approval.</p>
      <div className="target-recovery-fields">
        <label>GoldTier customer ID<input value={target.goldtier_id ?? ""} readOnly /></label>
        <label>Retained Policy name<input value={target.provider_policy ?? ""} readOnly /></label>
        <div><label htmlFor="verified-provider-policy-status">Verified provider Policy status</label><select id="verified-provider-policy-status" value={policyStatus} disabled={locked} onChange={(event) => setPolicyStatus(event.target.value as "" | "Requested")}><option value="">Select verified status</option><option value="Requested">Requested</option></select></div>
      </div>
      <label className="target-recovery-attestation"><input type="checkbox" disabled={locked} checked={policyVerified} onChange={(event) => setPolicyVerified(event.target.checked)} /> Verified against GoldTier: this customer has the retained Policy in Requested status.</label>
      <button type="submit" className="btn btn-primary" disabled={locked || !policyVerified || policyStatus !== "Requested" || !target.goldtier_id || !target.provider_policy}>Resolve verified Policy result</button>
    </form>}
    <details className="evidence-details"><summary>Technical details</summary>
      <dl className="target-recovery-facts">
        <dt>Error code</dt><dd>CLM_TARGET_OUTCOME_UNCERTAIN</dd>
        <dt>Submission ID</dt><dd>{target.submission_id ?? "Unknown historical submission"}</dd>
        <dt>Operation</dt><dd>{affected ?? "UNKNOWN"}</dd>
        <dt>Uncertainty category</dt><dd>{target.uncertainty_reason ?? "UNKNOWN"}</dd>
        <dt>Ledger state</dt><dd>{target.ledger_state ?? "Unknown"}</dd>
        <dt>Attempted prefix</dt><dd>{attempted.join(" → ") || "Unknown"}</dd>
        <dt>Definitive prefix</dt><dd>{completed.join(" → ") || "Unknown"}</dd>
        <dt>Lifecycle-resolved prefix</dt><dd>{resolved.join(" → ") || "Unknown"}</dd>
        {observation && <><dt>Read-only observation</dt><dd>{observation.result}</dd></>}
      </dl>
    </details>
  </section>;
}
