import UboSummary from "./UboSummary";
import { useEffect, useRef, type ReactNode } from "react";
import StageDisclosure from "./StageDisclosure";

import type { TargetSearchObservation } from "../api";

import type {
  AuthenticatedProfile,
  DocumentProcessingRecord,
  OwnershipAnalysisRecord,
  ZeroTouchCaseSummary,
} from "../types";
import { decisionLabel, uniqueDecisions, uniqueValues } from "./BlockerDecisionDetails";

function label(value: string | null | undefined): string {
  return value
    ? value
      .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
      .replaceAll("_", " ")
      .toLowerCase()
      .replace(/^./, (letter) => letter.toUpperCase())
    : "Not available";
}

function displayValue(value: string | null): string {
  return value ?? "Not provided";
}

type ReviewNote = {
  code: string;
  title: string;
  impact: string;
  blocking: boolean;
};

const REVIEW_NOTE_COPY: Record<string, Pick<ReviewNote, "title" | "impact">> = {
  IDP_PROFILE_PROVISIONAL: {
    title: "Document extraction uses the current POC parser",
    impact: "Review extracted document fields before relying on them.",
  },
  UBO_POLICY_NOT_SPONSOR_CONFIRMED: {
    title: "Check the configured ownership threshold",
    impact: "The sponsor confirmed aggregated ownership at or above 25%. This note may reflect an older assessment or a different configured threshold. Incomplete ownership evidence still requires review. Final Send confirms the prepared submission.",
  },
  LIVE_HIERARCHY_UNAVAILABLE: {
    title: "External hierarchy data is not available",
    impact: "Only the ownership evidence retained in this case is included in the review.",
  },
  RELATED_PARTY_MAPPING_PENDING: {
    title: "Related-party submission is not included",
    impact: "Related-party information stays in this case and will not be sent to GoldTier.",
  },
  RELATED_PARTY_WRITE_NOT_EXECUTED: {
    title: "Related-party submission is not included",
    impact: "Related-party information stays in this case and will not be sent to GoldTier.",
  },
  READY_FOR_APPROVAL_UNAVAILABLE: {
    title: "GoldTier approval status is outside this POC",
    impact: "Sending this case does not approve the customer in GoldTier.",
  },
  READY_FOR_APPROVAL_NOT_IMPLEMENTED: {
    title: "GoldTier approval status is outside this POC",
    impact: "Sending this case does not approve the customer in GoldTier.",
  },
  SANDBOX_PARTIAL: {
    title: "GoldTier Sandbox coverage is partial",
    impact: "Only the operations and fields listed below are included in this sandbox review.",
  },
};

function reviewNote(
  code: string,
  blocking: boolean,
  environment: "MOCK" | "SANDBOX",
): ReviewNote | null {
  if (code === "TARGET_CONFIRMATION_REQUIRED") return null;
  if (code === "REAL_GOLDTIER_NOT_CONFIGURED") {
    return environment === "SANDBOX"
      ? {
        code,
        title: "GoldTier Sandbox coverage is partial",
        impact: "Only the configured sandbox operations listed below are available.",
        blocking,
      }
      : {
        code,
        title: "This review uses Mock GoldTier only",
        impact: "No external GoldTier submission will be made from this local POC review.",
        blocking,
      };
  }
  const copy = REVIEW_NOTE_COPY[code];
  return {
    code,
    title: copy?.title ?? label(code),
    impact: copy?.impact ?? "Review this retained case note before sending.",
    blocking,
  };
}

export default function ReviewAndSend({
  summary,
  documents,
  ownership,
  actor,
  busy,
  error,
  onConfirm,
  onSaveDraft,
  onReviewOutstanding,
  onEditIdentity,
  onEditClassification,
  onEditDocuments,
  onEditOwnership,
  statusChecking = false,
  statusCheckResult,
  statusCheckError,
  onCheckStatus,
  disclosureScopeKey,
  readNotice,
}: {
  summary: ZeroTouchCaseSummary;
  documents: DocumentProcessingRecord[];
  ownership: OwnershipAnalysisRecord | null;
  actor: AuthenticatedProfile;
  busy: boolean;
  error?: string | null;
  onConfirm: () => void;
  onSaveDraft: () => void;
  onReviewOutstanding: () => void;
  onEditIdentity: () => void;
  onEditClassification: () => void;
  onEditDocuments: () => void;
  onEditOwnership: () => void;
  statusChecking?: boolean;
  statusCheckResult?: TargetSearchObservation | null;
  statusCheckError?: string | null;
  onCheckStatus?: () => void;
  /** Opt in to persistent disclosure; direct consumers retain the legacy layout. */
  disclosureScopeKey?: string;
  readNotice?: ReactNode;
}) {
  const technicalDetailsRef = useRef<HTMLDetailsElement>(null);
  const technicalDetailsWasOpen = useRef(false);
  useEffect(() => {
    const beforePrint = () => {
      if (disclosureScopeKey !== undefined || !technicalDetailsRef.current) return;
      technicalDetailsWasOpen.current = technicalDetailsRef.current.open;
      technicalDetailsRef.current.open = true;
    };
    const afterPrint = () => {
      if (technicalDetailsRef.current) {
        technicalDetailsRef.current.open = technicalDetailsWasOpen.current;
      }
    };
    window.addEventListener("beforeprint", beforePrint);
    window.addEventListener("afterprint", afterPrint);
    return () => {
      window.removeEventListener("beforeprint", beforePrint);
      window.removeEventListener("afterprint", afterPrint);
    };
  }, [disclosureScopeKey]);
  const { case: onboardingCase, clm } = summary;
  const preview = clm.submission_plan.request_preview;
  const checkpoint = clm.target_search_checkpoint;
  const confirmation = onboardingCase.target_dispatch_confirmation;
  const ownershipReceipt = summary.ownership_recovery?.review_receipt;
  const policyRebind = onboardingCase.policy_rebind;
  const classificationConsistency = summary.classification_consistency ?? {
    status: "UNKNOWN_LEGAL_FORM" as const,
    title: "Legal form needs operator review",
    explanation: "The available legal form could not be compared with the selected KYC customer type; review the classification before sending.",
    blocking: false as const,
    authority: "PROJECT_ADVISORY_ONLY" as const,
  };
  const submission = summary.target_submission;
  const submissionStarted = Boolean(submission && submission.state !== "NOT_SUBMITTED");
  const projectionFrozen = Boolean(clm.submission || confirmation || submissionStarted);
  const submissionCopy = submission ? {
    NOT_SUBMITTED: {
      title: "Submission not started",
      detail: "The backend has not started target execution for this reviewed submission.",
    },
    SENDING: {
      title: "Sending to GoldTier",
      detail: "The reviewed submission is running. Retained target operations determine its outcome.",
    },
    SUBMISSION_CONFIRMED: {
      title: "Submission confirmed",
      detail: "The reviewed submission and required customer readback are confirmed. GoldTier approval and KYC completion remain separate.",
    },
    SUBMISSION_FAILED: {
      title: "Submission failed",
      detail: "The submission has a definitive retained failure. Previously completed operations and target identifiers remain recorded.",
    },
    SUBMISSION_OUTCOME_UNCERTAIN: {
      title: statusChecking
        ? "Submission outcome uncertain — checking GoldTier status"
        : "Submission outcome uncertain",
      detail: "An attempted target operation has no definitive retained outcome. Status checking does not resend this submission.",
    },
    FINALIZATION_PENDING: {
      title: "Submission finalization pending",
      detail: "Retained target operations are resolved. Backend recovery can finish the approved submission without repeating them.",
    },
  }[submission.state] : projectionFrozen ? {
    title: "Submission status unavailable",
    detail: "This retained review has no current backend submission-state projection. Inspect the retained execution evidence.",
  } : null;
  const matchingStatusCheck = statusCheckResult?.submission_id === submission?.submission_id
    ? statusCheckResult : null;
  const canCheckStatus = submission?.state === "SUBMISSION_OUTCOME_UNCERTAIN"
    && submission.status_check_available && Boolean(onCheckStatus);
  const canVerifyCompleted = submission?.state === "SUBMISSION_CONFIRMED"
    && submission.verification_available === true && Boolean(submission.goldtier_id)
    && Boolean(onCheckStatus) && clm.submission_plan.environment === "SANDBOX";
  const completedResult = submission?.state === "SUBMISSION_CONFIRMED"
    && matchingStatusCheck && "goldtier_id" in matchingStatusCheck
    && matchingStatusCheck.goldtier_id === submission.goldtier_id ? matchingStatusCheck : null;
  const confirmationRequired = summary.active_exceptions.some(
    (exception) => exception.exception_type === "TARGET_CONFIRMATION_REQUIRED",
  );
  const canAccessCase = actor.capabilities.includes("CASE_ACCESS");
  const canEditReview = canAccessCase && !projectionFrozen;
  const canEditEvidence = canEditReview && summary.evidence_decision_authorized === true;
  const canReplaceDocument = canEditEvidence && summary.document_replacement_authorized === true;
  const canEditOwnership = canEditReview && summary.ownership_edit_authorized === true;
  const eligibleForConfirmation = confirmationRequired
    && preview?.dispatch_ready
    && (clm.readiness?.blockers?.length ?? 0) === 0;
  const destination = clm.submission_plan.environment === "SANDBOX"
    ? "GoldTier Sandbox"
    : "Mock GoldTier (local POC)";
  const confirmationLabel = clm.submission_plan.environment === "SANDBOX"
    ? "Confirm and send to GoldTier sandbox"
    : "Confirm and send to Mock GoldTier";
  const targetState = checkpoint?.disposition === "CONFIRMED_EXISTING"
    ? "Human-confirmed existing customer"
    : checkpoint?.disposition === "EXACT_MATCH"
    ? "Verified existing customer"
    : checkpoint?.disposition === "NO_MATCH"
      ? "New customer"
      : "Target match requires review";
  const identity = onboardingCase.entity ?? onboardingCase.initial_identity;
  const warnings = [...(clm.readiness?.warnings ?? []), ...(confirmation?.warnings ?? [])];
  const blockers = clm.readiness?.blockers ?? [];
  const nonBlockingDecisions = uniqueDecisions(summary.non_blocking_decisions ?? []);
  const nonBlockingCodes = uniqueValues(nonBlockingDecisions.map((decision) => decision.metadata.blocker_code));
  const nonBlockingDependencies = uniqueValues(nonBlockingDecisions.flatMap(
    (decision) => decision.metadata.invalidated_dependencies,
  ));
  const technicalCodes = uniqueValues([...warnings, ...blockers, ...nonBlockingCodes]);
  const notesByTitle = new Map<string, ReviewNote>();
  for (const code of uniqueValues([...warnings, ...blockers, ...nonBlockingCodes])) {
    const note = reviewNote(code, blockers.includes(code), clm.submission_plan.environment);
    if (note) notesByTitle.set(note.title, note);
  }
  if (classificationConsistency.status !== "COMPATIBLE") {
    notesByTitle.set(classificationConsistency.title, {
      code: classificationConsistency.status,
      title: classificationConsistency.title,
      impact: classificationConsistency.explanation,
      blocking: classificationConsistency.blocking,
    });
  }
  notesByTitle.set("GoldTier approval status is outside this POC", {
    code: "READY_FOR_APPROVAL_UNAVAILABLE",
    ...REVIEW_NOTE_COPY.READY_FOR_APPROVAL_UNAVAILABLE,
    blocking: false,
  });
  const importantNotes = [...notesByTitle.values()];

  const moreDetails = (
        <section>
          <h3>Corrections</h3>
          {(onboardingCase.identity_corrections?.length ?? 0) === 0
            ? <p>No retained identity corrections.</p>
            : <ul>{onboardingCase.identity_corrections?.map((correction) => <li key={correction.correction_id}>{correction.corrected_identity.legal_name} - user-supplied same-case correction - not provider verified - {new Date(correction.corrected_at).toLocaleString()}</li>)}</ul>}
        </section>
  );
  const technicalDetails = (
        <div className="review-and-send__technical-content">
          <p><strong>Retained codes:</strong> {technicalCodes.length > 0 ? technicalCodes.join(", ") : "None"}</p>
          <p><strong>Vocabulary version:</strong> {summary.target_classification?.vocabulary_version ?? "Not available"}</p>
          <p><strong>Automation / CLM / event count:</strong> {summary.version} / {clm.version ?? "not available"} / {onboardingCase.events?.length ?? 0}</p>
          <p>{clm.submission ? `Snapshot ${clm.submission.snapshot_id} - readiness ${clm.submission.readiness_policy_version}` : "A submission snapshot has not been created."}</p>
          {preview?.operations.map((operation) => (
            <div key={`technical:${operation.operation}`}>
              <strong>{operation.operation}</strong>
              <ul>{operation.fields.map((field) => (
                <li key={`technical:${operation.operation}:${field.target_field}`}>
                  {field.target_field}: {field.provenance} / {field.authority} / {field.validation}
                </li>
              ))}</ul>
            </div>
          ))}
          {ownershipReceipt && (
            <p>Manual ownership reviewed by {ownershipReceipt.actor_id} on {new Date(ownershipReceipt.reviewed_at).toLocaleString()}{` - document ${ownershipReceipt.evidence_document_id} version ${ownershipReceipt.evidence_document_version} - ${ownershipReceipt.evidence_reference} - as of ${ownershipReceipt.as_of_date}`}</p>
          )}
          {policyRebind && <p>POC configuration revision {policyRebind.revision} - {policyRebind.configuration_status}</p>}
          {policyRebind?.last_rebound_by && policyRebind.last_rebound_at && <p>Configuration rebound by {policyRebind.last_rebound_by} on {new Date(policyRebind.last_rebound_at).toLocaleString()}</p>}
          {nonBlockingDecisions.map((decision) => (
            <p key={decision.decision_id}>{decisionLabel(decision.metadata.classification)} decision {decision.decision_id} - {decision.metadata.policy_version} - rule {decision.metadata.rule_version} - recorded {new Date(decision.recorded_at).toLocaleString()}</p>
          ))}
          {nonBlockingDependencies.length > 0 && <p><strong>Invalidated dependencies:</strong> {nonBlockingDependencies.map(decisionLabel).join(", ")}</p>}
          <p>{confirmation ? `Confirmed by ${confirmation.actor_id} on ${new Date(confirmation.confirmed_at).toLocaleString()} - review digest ${confirmation.review_digest}` : "The server will compute and validate the review digest when you confirm."}</p>
        </div>
  );

  const main = (
    <section id="case-review-and-send" tabIndex={-1} className="review-and-send" aria-labelledby="review-and-send-title">
      <header className="review-and-send__header">
        <div>
          <p className="card-kicker">
            {projectionFrozen ? "Frozen server review projection" : "Current server review projection"}
          </p>
          <h2 id="review-and-send-title">Review and send</h2>
          <p>Review exactly what this case will send. Send is the final human approval in this application; subsequent GoldTier approval is outside this workflow.</p>
        </div>
        <button type="button" className="btn btn-ghost review-and-send__print" onClick={() => window.print()}>
          Print / save PDF
        </button>
      </header>

      {error && <p className="ds-banner ds-banner-warn" role="alert">{error}</p>}
      {submissionCopy && (
        <section className="ds-banner" aria-labelledby="submission-state-title" aria-live="polite" aria-atomic="true">
          <h3 id="submission-state-title" tabIndex={-1}>{submissionCopy.title}</h3>
          <p>{submissionCopy.detail}</p>
          {submission?.state === "SUBMISSION_CONFIRMED" ? (
            <dl aria-label="Completed GoldTier submission">
              <div><dt>GoldTier ID</dt><dd>{submission.goldtier_id ?? "Not retained"}</dd></div>
              <div><dt>Customer handling</dt><dd>{submission.customer_handling === "EXISTING_REUSED"
                ? "Existing GoldTier customer reused" : submission.customer_handling === "NEW_CREATED"
                ? "New GoldTier customer created" : "Not recorded"}</dd></div>
              <div><dt>Provider</dt><dd>{clm.submission_plan.environment === "SANDBOX" ? "GoldTier XPI" : "GoldTier Mock"}</dd></div>
              <div><dt>Environment</dt><dd>{label(clm.submission_plan.environment)}</dd></div>
              <div><dt>Submission status</dt><dd>Confirmed</dd></div>
              <div><dt>Readback</dt><dd>{summary.target_operations.find((item) => item.operation === "READBACK")?.status ?? "Not recorded"}</dd></div>
              {summary.target_operations.map((item) => <div key={item.operation}>
                <dt>{label(item.operation)}</dt><dd>{label(item.status)}</dd>
              </div>)}
              {completedResult && <>
                <div><dt>Verification</dt><dd>{completedResult.result === "VERIFIED" ? "Verified in Sandbox"
                  : completedResult.result === "REQUIRES_REVIEW" ? "Verification requires review" : "Verification unavailable"}</dd></div>
                <div><dt>Checked at</dt><dd>{new Date(completedResult.checked_at).toLocaleString()}</dd></div>
                {completedResult.result === "VERIFIED" && <div><dt>Identity</dt><dd>{[
                  completedResult.legal_name, completedResult.registration_number, completedResult.country,
                ].filter(Boolean).join(" · ")}</dd></div>}
              </>}
            </dl>
          ) : submission?.goldtier_id && <p>Retained GoldTier ID: {submission.goldtier_id}</p>}
          {matchingStatusCheck && "message" in matchingStatusCheck && (
            <div>
              <p>{matchingStatusCheck.message}</p>
              <p>Checked at {new Date(matchingStatusCheck.checked_at).toLocaleString()}.</p>
              <p>Customer identity checking does not establish Policy completion, GoldTier approval or KYC completion.</p>
            </div>
          )}
          {statusCheckError && <p role="alert">{statusCheckError}</p>}
        </section>
      )}
      {checkpoint && checkpoint.status !== "COMPLETED" && (
        <p className="ds-banner ds-banner-warn" role="status">
          Target search evidence is {label(checkpoint.status)}. Review outstanding items before confirming.
        </p>
      )}

      <div className="review-and-send__summary" aria-label="Destination and target state">
        <div><span>Destination</span><strong>{destination}</strong></div>
        <div><span>Customer state</span><strong>{targetState}</strong></div>
        <div><span>Classification</span><strong>{clm.submission_plan.environment === "SANDBOX" ? "Sandbox Partial" : "Mock"}</strong></div>
      </div>

      <UboSummary record={ownership} />
      <div className="review-and-send__grid">
        <section>
          <div className="review-and-send__section-heading">
            <h3>Customer identity</h3>
            {canEditEvidence && <button type="button" className="btn btn-ghost review-and-send__edit" onClick={onEditIdentity}>Edit company details</button>}
          </div>
          <dl>
            <div><dt>Legal name</dt><dd>{identity?.legal_name ?? "Not provided"}</dd></div>
            <div><dt>Registration number</dt><dd>{identity?.registration_number ?? onboardingCase.requested_uen}</dd></div>
            <div><dt>Country</dt><dd>{identity?.country_of_incorporation ?? "Not provided"}</dd></div>
            <div><dt>Legal form</dt><dd>{label(onboardingCase.entity?.party_type)}</dd></div>
            <div><dt>Owning team</dt><dd>{onboardingCase.team_id ?? "Unassigned"}</dd></div>
            <div><dt>Existing party</dt><dd>{checkpoint?.selected_party_id ?? "No verified existing party selected"}</dd></div>
          </dl>
        </section>

        <section>
          <div className="review-and-send__section-heading">
            <h3>KYC and segment</h3>
            {canEditEvidence && <button type="button" className="btn btn-ghost review-and-send__edit" onClick={onEditClassification}>Edit classification</button>}
          </div>
          <dl>
            <div><dt>KYC customer type</dt><dd>{label(summary.target_classification?.kyc_customer_type.selected_value)}</dd></div>
            <div><dt>Client segment</dt><dd>{label(summary.target_classification?.client_segment.selected_value)}</dd></div>
          </dl>
          {classificationConsistency.status !== "COMPATIBLE" && (
            <div className="review-and-send__classification-advisory" role="note">
              <strong>{classificationConsistency.title}</strong>
              <p>{classificationConsistency.explanation}</p>
              <span>Non-blocking advisory - no sponsor or regulatory incompatibility rule is claimed.</span>
              {canEditEvidence && <button type="button" className="btn btn-ghost review-and-send__edit" onClick={onEditClassification}>Review KYC classification</button>}
            </div>
          )}
        </section>
      </div>

      <section className="review-and-send__operations">
        <h3>What will be sent</h3>
        {!preview && <p>No target request preview is available. Nothing can be confirmed.</p>}
        {preview?.operations.map((operation) => (
          <article key={operation.operation} className="review-and-send__operation">
            <h4>{label(operation.operation)} - {label(operation.validation)}</h4>
            <dl>
              {operation.fields.map((field) => (
                <div key={`${operation.operation}:${field.target_field}`}>
                  <dt>{label(field.target_field)}</dt>
                  <dd>{displayValue(field.value)}</dd>
                </div>
              ))}
            </dl>
          </article>
        ))}
      </section>

      <div className="review-and-send__grid">
        <section>
          <div className="review-and-send__section-heading">
            <h3>Evidence and limitations</h3>
            {(canReplaceDocument || canEditOwnership) && (
              <div className="review-and-send__section-actions">
                {canReplaceDocument && <button type="button" className="btn btn-ghost review-and-send__edit" onClick={onEditDocuments}>Edit documents</button>}
                {canEditOwnership ? (
                  <button type="button" className="btn btn-ghost review-and-send__edit" onClick={onEditOwnership}>Edit ownership</button>
                ) : (
                  <small className="review-and-send__ownership-read-only">
                    Ownership source is review-only; no correction action is currently authorized.
                  </small>
                )}
              </div>
            )}
          </div>
          <ul>
            <li>Registry: {onboardingCase.entity?.source ? `${onboardingCase.entity.source.source_system} ${label(onboardingCase.entity.source.environment)}` : "not available"}</li>
            <li>Documents: {documents.length} retained; {documents.filter((document) => document.state === "REVIEWED").length} reviewed.</li>
            <li>Ownership: {ownership ? `${ownership.candidates.length} provisional candidate(s), ${label(ownership.provider_environment)}` : "not available"}.</li>
            {ownershipReceipt && (
              <li>
                Ownership source: user-supplied declaration retained locally.
                This is not ACRA or verified ownership evidence.
              </li>
            )}
            <li>Related-party information is saved in this case; not transmitted to GoldTier.</li>
            {policyRebind?.unavailable_fields.map((field) => (
              <li key={field}>{label(field)}: Saved in this case; not transmitted to GoldTier.</li>
            ))}
          </ul>
        </section>
        {disclosureScopeKey === undefined && moreDetails}
      </div>

      <section className="review-and-send__notes" aria-labelledby="review-notes-title">
        <h3 id="review-notes-title">Important notes before sending</h3>
        <ul>{importantNotes.map((note) => (
          <li key={note.title}>
            <strong>{note.title}</strong>
            <span>{note.impact}</span>
            <span className={`review-and-send__note-status ${note.blocking ? "is-blocking" : ""}`}>
              {note.blocking ? "Blocking" : "Non-blocking"}
            </span>
          </li>
        ))}</ul>
      </section>

      {disclosureScopeKey === undefined && <details ref={technicalDetailsRef} className="review-and-send__technical">
        <summary>Technical details and audit appendix</summary>
        {technicalDetails}
      </details>}

      <div className="review-and-send__actions">
        {eligibleForConfirmation && canAccessCase && !projectionFrozen ? (
          <button type="button" className="btn btn-primary" disabled={busy} onClick={onConfirm}>{confirmationLabel}</button>
        ) : !projectionFrozen ? (
          <>
            <button type="button" className="btn btn-secondary" disabled={busy} onClick={onSaveDraft}>Save draft</button>
            <button type="button" className="btn btn-ghost" disabled={busy} onClick={onReviewOutstanding}>Review outstanding items</button>
          </>
        ) : null}
        {(canCheckStatus || canVerifyCompleted) && canAccessCase && (
          <button type="button" className="btn btn-secondary" disabled={busy || statusChecking} onClick={onCheckStatus}>
            {canVerifyCompleted ? "Verify in GoldTier" : "Check GoldTier status"}
          </button>
        )}
        {!canAccessCase && <p role="status">You do not have the case capability required to confirm this dispatch.</p>}
        {confirmation && <p role="status">Dispatch confirmation is retained. The reviewed version cannot be confirmed again.</p>}
      </div>
    </section>
  );
  return disclosureScopeKey === undefined ? main : <StageDisclosure
    title="Final review & send" summary={confirmation ? "Dispatch confirmation retained — review the current submission status." : eligibleForConfirmation && canAccessCase && !projectionFrozen ? "Action required — review the package before Confirm and send." : "Review current blockers, frozen status and outstanding items before sending."} scopeKey={disclosureScopeKey} final
    main={<>{readNotice}{main}</>}
    moreDetails={<>{readNotice}{moreDetails}</>}
    technicalDetails={<>{readNotice}{technicalDetails}</>}
  />;
}
