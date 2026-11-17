import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useId, useState } from "react";

import type { AuthenticatedProfile } from "../types";
import type { WorkflowField } from "../workflowApi";
import {
  approvalErrorView,
  buildDecisionRequest,
  decideProposal,
  decisionReasonValid,
  DECISION_REASON_MAX,
  DECISION_REASON_MIN,
  fetchProposalComparison,
  trimmedReasonLength,
  workflowApprovalQueryKeys,
  type ApprovalErrorView,
} from "../workflowApprovalsApi";
import {
  PERMANENT_OBLIGATION_WARNING,
  type ComparisonResponse,
  type DecisionOutcome,
  type DecisionResponse,
  type DiffChange,
  type FieldDiff,
  type PermanentObligation,
  type PermanentObligationChange,
  type PublicationReport,
  type StageDiff,
  type ValidationIssue,
  type VersionProvenance,
} from "../workflowGovernanceTypes";
import { PROPOSAL_KIND_EXPLANATION, PROPOSAL_KIND_LABEL } from "../workflowRecoveryApi";
import { formatTimestamp, noDecisionReason, versionLabel } from "./WorkflowApprovals";

/** ADR-017 §1.4: the fixed note for versions activated before approval governance. */
export const LEGACY_PROVENANCE_NOTE = "Activated by a Director before approval governance; not independently approved.";

const CHANGE_LABEL: Record<DiffChange, string> = { ADDED: "Added", REMOVED: "Removed", CHANGED: "Changed", UNCHANGED: "Unchanged" };
const CHANGE_TAG: Record<DiffChange, string> = { ADDED: "tag tag-ok", REMOVED: "tag tag-critical", CHANGED: "tag tag-amber", UNCHANGED: "tag tag-neutral" };
const OBLIGATION_LABEL: Record<PermanentObligationChange, string> = {
  NEW_REQUIRED_STAGE: "New required stage",
  NEW_REQUIRED_FIELD: "New required field",
  TIGHTENED: "Tightened",
};
const FIELD_KIND_LABEL: Record<WorkflowField["kind"], string> = { TEXT: "Text", DATE: "Date", NUMBER: "Number", YES_NO: "Yes/No", CHOICE: "Choice" };

export function fieldSummary(field: WorkflowField): string {
  const options = field.kind === "CHOICE" && field.options.length ? `: ${field.options.join(", ")}` : "";
  return `${field.label} (${FIELD_KIND_LABEL[field.kind] ?? field.kind}${options}, ${field.required ? "required" : "optional"}${field.autofill ? ", autofill" : ""})`;
}

function nodeLabels(comparison: ComparisonResponse): Map<string, string> {
  const labels = new Map<string, string>(comparison.locked_stages.map(([id, label]) => [id, label]));
  for (const stage of comparison.active_version?.stages ?? []) labels.set(stage.stage_id, stage.name);
  for (const stage of comparison.proposal.stages) labels.set(stage.stage_id, stage.name);
  return labels;
}

function Position({ value, labels }: { value: string | null; labels: Map<string, string> }) {
  if (!value) return <>—</>;
  return <>after {labels.get(value) ?? value}</>;
}

function FieldRow({ diff }: { diff: FieldDiff }) {
  const label = diff.after?.label ?? diff.before?.label ?? diff.field_id;
  return (
    <li>
      <span className={CHANGE_TAG[diff.change]}>{CHANGE_LABEL[diff.change]}</span>{" "}
      <strong>{label}</strong>
      {diff.change === "CHANGED" && diff.before && diff.after
        ? <> · was {fieldSummary(diff.before)} · now {fieldSummary(diff.after)}</>
        : <> · {fieldSummary((diff.after ?? diff.before)!)}</>}
    </li>
  );
}

function StageDiffView({ diff, labels }: { diff: StageDiff; labels: Map<string, string> }) {
  const name = diff.name_after ?? diff.name_before ?? diff.stage_id;
  const renamed = diff.change === "CHANGED" && diff.name_before && diff.name_after && diff.name_before !== diff.name_after;
  const moved = diff.after_node_id_before !== diff.after_node_id_after && diff.change === "CHANGED";
  const holdsChanged = diff.blocks_send_before !== diff.blocks_send_after;
  const headingId = `stage-diff-${diff.stage_id}`;
  return (
    <li className="card" aria-labelledby={headingId} style={{ marginBottom: 8 }}>
      <h4 id={headingId}>
        <span className={CHANGE_TAG[diff.change]}>{CHANGE_LABEL[diff.change]}</span>{" "}
        {name}{renamed && <span className="text-muted"> (was “{diff.name_before}”)</span>}
      </h4>
      <p>
        Position: {moved
          ? <><Position value={diff.after_node_id_before} labels={labels} /> → <Position value={diff.after_node_id_after} labels={labels} /></>
          : <Position value={diff.after_node_id_after ?? diff.after_node_id_before} labels={labels} />}
      </p>
      <p>
        Holds the send: {holdsChanged
          ? <>{diff.blocks_send_before ? "Yes" : "No"} → <strong>{diff.blocks_send_after ? "Yes" : "No"}</strong></>
          : diff.blocks_send_after ? "Yes" : "No"}
      </p>
      {diff.fields.length > 0 && <ul aria-label={`Field changes in ${name}`}>{diff.fields.map(field => <FieldRow key={field.field_id} diff={field} />)}</ul>}
    </li>
  );
}

export function ProvenanceView({ provenance }: { provenance: VersionProvenance | null }) {
  if (!provenance) return <p className="text-muted">No version is active yet. Approving publishes the first version.</p>;
  if (provenance.origin === "GOVERNED_APPROVAL") {
    return (
      <dl aria-label={`Provenance of version ${provenance.version}`}>
        <dt>Version</dt><dd>v{provenance.version} · <span className="tag tag-ok">Governed approval</span></dd>
        <dt>Author</dt><dd>{provenance.author_id ?? "—"}</dd>
        <dt>Approver</dt><dd>{provenance.approved_by ?? "—"}</dd>
        <dt>Published</dt><dd>{formatTimestamp(provenance.published_at)}</dd>
      </dl>
    );
  }
  if (provenance.origin === "PRE_GOVERNANCE_DIRECTOR_ACTIVATION") {
    // Never shown as approved (ADR-017 §1.4): the fixed note always replaces any other wording.
    return (
      <dl aria-label={`Provenance of version ${provenance.version}`}>
        <dt>Version</dt><dd>v{provenance.version} · <span className="tag tag-neutral">Pre-governance activation</span></dd>
        <dt>Activated by</dt><dd>{provenance.activated_by ?? "—"}</dd>
        <dt>Activated</dt><dd>{formatTimestamp(provenance.published_at)}</dd>
        <dt>Note</dt><dd>{LEGACY_PROVENANCE_NOTE}</dd>
      </dl>
    );
  }
  // A single-actor emergency publication: never approved (ADR-017 §4).
  return (
    <dl aria-label={`Provenance of version ${provenance.version}`}>
      <dt>Version</dt><dd>v{provenance.version} · <span className="tag tag-warn">Emergency fallback — not approved</span></dd>
      <dt>Activated by</dt><dd>{provenance.activated_by ?? "—"}</dd>
      <dt>Activated</dt><dd>{formatTimestamp(provenance.published_at)}</dd>
      {provenance.note && <><dt>Note</dt><dd>{provenance.note}</dd></>}
    </dl>
  );
}

function IssueList({ issues, label }: { issues: ValidationIssue[]; label: string }) {
  return (
    <ul aria-label={label}>
      {issues.map((issue, index) => (
        <li key={`${issue.code}-${issue.stage_id ?? ""}-${issue.field_id ?? ""}-${index}`}>
          {issue.rule && <strong>{issue.rule}: </strong>}{issue.message}
        </li>
      ))}
    </ul>
  );
}

function obligationText(item: PermanentObligation): string {
  const target = item.field_label ? `${item.stage_name} · ${item.field_label}` : item.stage_name;
  return `${OBLIGATION_LABEL[item.change] ?? item.change}: ${target}. ${item.detail}`;
}

function ComparisonView({ comparison }: { comparison: ComparisonResponse }) {
  const labels = nodeLabels(comparison);
  const { proposal, validation } = comparison;
  const activeVersion = comparison.active_version?.version ?? 0;
  const changed = comparison.stages.filter(stage => stage.change !== "UNCHANGED");
  const unchanged = comparison.stages.filter(stage => stage.change === "UNCHANGED");
  const affected = comparison.affected_cases.open_runs_on_active_version;
  return (
    <>
      <div className="ds-page-header">
        <div>
          <p className="card-kicker">Compare and decide</p>
          <h1>{comparison.workflow_name} {comparison.is_onboarding && <span className="tag tag-accent">Onboarding</span>}</h1>
          <p className="text-muted">
            <span data-testid="compare-kind">{PROPOSAL_KIND_LABEL[proposal.kind]}</span> · by {proposal.author_id ?? "—"} · submitted {formatTimestamp(proposal.submitted_at)}
          </p>
          {proposal.note && <p>Proposal note: {proposal.note}</p>}
          <p className="text-muted">
            {versionLabel(proposal.base_version, activeVersion)} · would publish as a new version · content hash {(proposal.content_hash ?? "").slice(0, 12)}… (frozen at submit)
          </p>
        </div>
      </div>

      {proposal.kind !== "CHANGE" && <KindExplanation comparison={comparison} />}

      <section className="card" aria-labelledby="compare-active-provenance" style={{ marginBottom: 16 }}>
        <h2 id="compare-active-provenance">Active version</h2>
        <ProvenanceView provenance={comparison.active_provenance} />
      </section>

      <section className="card" aria-labelledby="compare-diff" style={{ marginBottom: 16 }}>
        <h2 id="compare-diff">Proposed changes</h2>
        {changed.length === 0 ? <p className="text-muted">No stage or field changes.</p> : <ul style={{ listStyle: "none", padding: 0 }}>{changed.map(stage => <StageDiffView key={stage.stage_id} diff={stage} labels={labels} />)}</ul>}
        {unchanged.length > 0 && <p className="text-muted">Unchanged stages: {unchanged.map(stage => stage.name_after ?? stage.stage_id).join(", ")}</p>}
        {comparison.locked_stages.length > 0 && (
          <>
            <h3 id="compare-locked">Fixed onboarding stages</h3>
            <p className="text-muted">Shown for context. A workflow proposal cannot remove, reorder or change them.</p>
            <ol aria-labelledby="compare-locked">
              {comparison.locked_stages.map(([id, label]) => <li key={id}>{label} <span className="tag tag-neutral">Fixed</span></li>)}
            </ol>
          </>
        )}
      </section>

      <section className="card" aria-labelledby="compare-validation" style={{ marginBottom: 16 }}>
        <h2 id="compare-validation">Required-obligation checks</h2>
        {validation.valid && validation.issues.length === 0
          ? <p><span className="tag tag-ok">Passed</span> Re-run against the active version and the required baseline. They run again when you approve.</p>
          : (
            <div role="alert">
              <p><span className="tag tag-critical">Blocked</span> This proposal cannot be approved while these issues remain.</p>
              <IssueList issues={validation.issues} label="Validation issues" />
            </div>
          )}
      </section>

      <section className="card" aria-labelledby="compare-affected" style={{ marginBottom: 16 }}>
        <h2 id="compare-affected">Affected cases</h2>
        <p>
          {affected} open {affected === 1 ? "case runs" : "cases run"} on the active version
          {activeVersion > 0 ? ` (v${activeVersion})` : ""}. Counted {formatTimestamp(comparison.affected_cases.counted_at)}.
        </p>
      </section>
    </>
  );
}

/** Plain explanation of a recovery proposal (M2, CC-4). */
function KindExplanation({ comparison }: { comparison: ComparisonResponse }) {
  const { kind } = comparison.proposal;
  return (
    <section className="card" aria-labelledby="compare-kind-explanation" data-testid="compare-kind-explanation" style={{ marginBottom: 16 }}>
      <h2 id="compare-kind-explanation">What this proposal does: {PROPOSAL_KIND_LABEL[kind]}</h2>
      <p>{PROPOSAL_KIND_EXPLANATION[kind]}</p>
      {(kind === "RESTORE_VERSION" || kind === "RESET_TO_DEFAULT") && (
        <p className="text-muted">The server computed this content; the HR author did not edit it. The changes below show exactly what would be published.</p>
      )}
      {kind === "DEACTIVATE" && (
        <ul data-testid="deactivate-effects">
          <li>Existing runs keep their frozen stages and stay completable: they can still be answered, confirmed and viewed.</li>
          <li>New runs of this workflow are blocked until it is reactivated.</li>
          <li>No run is changed, and the required baseline is kept.</li>
          <li>If a case is confirming a required step at that moment, approval is refused and nothing changes; try again shortly.</li>
        </ul>
      )}
    </section>
  );
}

function PublicationReportView({ report }: { report: PublicationReport }) {
  return (
    <dl aria-label="Publication report">
      <dt>Cases past their first write under an earlier version</dt><dd>{report.cases_past_first_write_under_earlier_version}</dd>
      <dt>Cases authorised under an earlier version</dt><dd>{report.cases_authorised_under_earlier_version}</dd>
      <dt>Possibly authorised</dt><dd>{report.cases_possibly_authorised}</dd>
      <dt>Counted</dt><dd>{formatTimestamp(report.counted_at)}</dd>
    </dl>
  );
}

export function DecisionResult({ result, onBack }: { result: DecisionResponse; onBack: () => void }) {
  const approved = result.proposal.state === "APPROVED";
  const deactivated = approved && result.proposal.kind === "DEACTIVATE";
  const heading = deactivated
    ? "Approved · the workflow is deactivated: new runs are blocked and existing runs stay completable"
    : approved ? `Approved · version ${result.published_version ?? result.active_version} is now active` : "Rejected · nothing was published";
  return (
    <section className="card" aria-labelledby="decision-result" role="status">
      <h2 id="decision-result">{heading}</h2>
      <p>Decided by {result.proposal.decided_by ?? "—"} at {formatTimestamp(result.proposal.decided_at)}. Reason: {result.proposal.decision_reason ?? "—"}</p>
      {approved && !deactivated && (
        <>
          <h3>Provenance</h3>
          <ProvenanceView provenance={result.provenance} />
          <h3>Publication report</h3>
          {result.publication_report
            ? <>
              <PublicationReportView report={result.publication_report} />
              <p className="text-muted">Possibly authorised counts live tentative claims that may already have passed the send check before this publication.</p>
            </>
            : <p className="text-muted">The publication report is not available.</p>}
        </>
      )}
      <button type="button" className="btn btn-secondary" onClick={onBack}>Back to workflow approvals</button>
    </section>
  );
}

function DecisionForm({ comparison, actor, onDecided, onReload }: {
  comparison: ComparisonResponse;
  actor: AuthenticatedProfile;
  onDecided: (result: DecisionResponse) => void;
  onReload: () => void;
}) {
  const queryClient = useQueryClient();
  const id = useId();
  const [reason, setReason] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [failure, setFailure] = useState<ApprovalErrorView | null>(null);
  const decide = useMutation({
    mutationFn: (outcome: DecisionOutcome) => decideProposal(
      comparison.workflow_id,
      comparison.proposal.proposal_id,
      buildDecisionRequest(comparison, outcome, reason),
    ),
    retry: false,
    onMutate: () => setFailure(null),
    onSuccess: result => {
      void queryClient.invalidateQueries({ queryKey: workflowApprovalQueryKeys.inbox(actor) });
      void queryClient.invalidateQueries({
        queryKey: workflowApprovalQueryKeys.comparison(actor, comparison.workflow_id, comparison.proposal.proposal_id),
        refetchType: "none",
      });
      onDecided(result);
    },
    onError: error => setFailure(approvalErrorView(error)),
  });

  const obligations = comparison.permanent_obligations;
  const pending = comparison.proposal.state === "PENDING_APPROVAL";
  const uiRefusal = noDecisionReason(comparison, actor);
  const refused = failure?.refused ?? false;
  const offerDecision = pending && !uiRefusal && !refused;
  const reasonLength = trimmedReasonLength(reason);
  const reasonOk = decisionReasonValid(reason);
  const validationBlocks = !comparison.validation.valid || comparison.validation.issues.length > 0;
  const needsConfirmation = obligations.length > 0;
  const hashMissing = !comparison.proposal.content_hash;
  const mustReload = failure?.reload ?? false;
  const busy = decide.isPending;
  const approveHints = [
    validationBlocks ? "Approve is blocked until every required-obligation issue is resolved." : null,
    needsConfirmation && !confirmed ? "Confirm the permanent obligations to approve." : null,
    !reasonOk ? `Enter a reason of ${DECISION_REASON_MIN}–${DECISION_REASON_MAX} characters.` : null,
    hashMissing ? "This proposal has no frozen content hash; reload it." : null,
    mustReload ? "Reload the comparison before deciding." : null,
  ].filter((hint): hint is string => hint !== null);
  const approveDisabled = !offerDecision || busy || approveHints.length > 0;
  const rejectDisabled = !offerDecision || busy || !reasonOk || hashMissing || mustReload;
  const warningId = `${id}-warning`;
  const reasonCountId = `${id}-reason-count`;
  const hintsId = `${id}-hints`;

  return (
    <section className="card" aria-labelledby={`${id}-decision`}>
      {obligations.length > 0 && (
        <fieldset aria-labelledby={warningId} style={{ border: 0, padding: 0, margin: "0 0 16px" }}>
          <div className="ds-banner ds-banner-warn">
            <p id={warningId}><strong>{PERMANENT_OBLIGATION_WARNING}</strong></p>
            <ul aria-label="Permanent obligations">
              {obligations.map(item => <li key={`${item.key.stage_id}:${item.key.field_id ?? ""}`}>{obligationText(item)}</li>)}
            </ul>
            {offerDecision && (
              <label>
                <input
                  type="checkbox"
                  checked={confirmed}
                  disabled={busy || mustReload}
                  aria-describedby={warningId}
                  onChange={event => setConfirmed(event.target.checked)}
                />{" "}
                I understand that {obligations.length === 1 ? "this obligation becomes" : `these ${obligations.length} obligations become`} permanent once approved.
              </label>
            )}
          </div>
        </fieldset>
      )}

      <h2 id={`${id}-decision`}>Your decision</h2>
      {!pending && <p role="status">This proposal is {comparison.proposal.state.replace("_", " ").toLowerCase()} and is no longer awaiting a decision.</p>}
      {pending && uiRefusal && <p className="ds-banner ds-banner-warn" role="note">{uiRefusal}</p>}
      {failure && (
        <div className="ds-banner ds-banner-warn" role="alert">
          <p>{failure.message}</p>
          {failure.issues.length > 0 && <IssueList issues={failure.issues} label="Refusal issues" />}
          {failure.reload && <button type="button" className="btn btn-secondary" onClick={onReload}>Reload comparison</button>}
          {failure.retryLater && <p className="text-muted" style={{ margin: "6px 0 0" }}>Your reason is kept. You can try the same decision again.</p>}
        </div>
      )}
      {offerDecision && (
        <>
          <label htmlFor={`${id}-reason`}>Reason (required, {DECISION_REASON_MIN}–{DECISION_REASON_MAX} characters, recorded permanently)</label>
          <textarea
            id={`${id}-reason`}
            className="input"
            value={reason}
            maxLength={DECISION_REASON_MAX + 40}
            disabled={busy}
            aria-invalid={reason.length > 0 && !reasonOk}
            aria-describedby={reasonCountId}
            onChange={event => setReason(event.target.value)}
          />
          <p id={reasonCountId} className="text-muted" aria-live="polite">
            {reasonLength} / {DECISION_REASON_MAX}
            {reason.length > 0 && reasonLength < DECISION_REASON_MIN && ` · at least ${DECISION_REASON_MIN} characters`}
            {reasonLength > DECISION_REASON_MAX && ` · at most ${DECISION_REASON_MAX} characters`}
          </p>
          <div className="case-header-actions" style={{ justifyContent: "flex-start" }}>
            <button
              type="button"
              className="btn btn-primary"
              disabled={approveDisabled}
              aria-describedby={approveHints.length ? hintsId : undefined}
              onClick={() => decide.mutate("APPROVE")}
            >
              {comparison.proposal.kind === "DEACTIVATE" ? "Approve and deactivate" : "Approve and publish"}
            </button>
            <button type="button" className="btn btn-secondary" disabled={rejectDisabled} onClick={() => decide.mutate("REJECT")}>
              Reject
            </button>
          </div>
          {approveHints.length > 0 && <ul id={hintsId} className="text-muted">{approveHints.map(hint => <li key={hint}>{hint}</li>)}</ul>}
          <p className="text-muted">One decision, final and immutable. If another version is published first, this proposal becomes stale and cannot be approved.</p>
        </>
      )}
    </section>
  );
}

export default function WorkflowCompare({ actor, workflowId, proposalId, onBack }: {
  actor: AuthenticatedProfile;
  workflowId: string;
  proposalId: string;
  onBack: () => void;
}) {
  const [result, setResult] = useState<DecisionResponse | null>(null);
  const [generation, setGeneration] = useState(0);
  const query = useQuery({
    queryKey: workflowApprovalQueryKeys.comparison(actor, workflowId, proposalId),
    queryFn: ({ signal }) => fetchProposalComparison(workflowId, proposalId, signal),
    retry: false,
    enabled: result === null,
  });
  const back = <button type="button" className="btn btn-ghost" onClick={onBack}>← Workflow approvals</button>;

  if (result) return <section className="ds-root ds-page">{back}<DecisionResult result={result} onBack={onBack} /></section>;
  if (query.isPending) return <section className="ds-root ds-page">{back}<p className="text-muted" role="status">Loading the comparison…</p></section>;
  if (query.isError) {
    return (
      <section className="ds-root ds-page">{back}
        <p className="ds-banner ds-banner-warn" role="alert">{approvalErrorView(query.error).message}</p>
        <button type="button" className="btn btn-secondary" onClick={() => void query.refetch()}>Try again</button>
      </section>
    );
  }
  const comparison = query.data;
  const formKey = `${generation}:${comparison.workflow_revision}:${comparison.proposal.revision}:${comparison.proposal.content_hash ?? ""}`;
  return (
    <section className="ds-root ds-page">
      {back}
      {query.isFetching && <p className="text-muted" role="status">Reloading…</p>}
      <ComparisonView comparison={comparison} />
      <DecisionForm
        key={formKey}
        comparison={comparison}
        actor={actor}
        onDecided={setResult}
        onReload={() => { setGeneration(value => value + 1); void query.refetch(); }}
      />
    </section>
  );
}
