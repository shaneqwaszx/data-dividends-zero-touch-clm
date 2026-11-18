import type { ReactNode } from "react";

import { RATCHET_RULE_EXPLANATIONS, issuesByRule, type GovernanceRefusal } from "../../workflowGovernanceApi";
import { PROPOSAL_KIND_EXPLANATION, PROPOSAL_KIND_LABEL, provenanceText } from "../../workflowRecoveryApi";
import {
  PERMANENT_OBLIGATION_WARNING,
  type ProposalResponse,
  type SimulationResult,
  type ValidationIssue,
  type ValidationReport,
  type VersionProvenance,
  type WorkflowGovernanceView,
} from "../../workflowGovernanceTypes";

/** The fixed legacy note (ADR-017 §1.4); shown when the server sends no note. */
export const LEGACY_PROVENANCE_NOTE = "Activated by a Director before approval governance; not independently approved.";

function IssueList({ issues }: { issues: ValidationIssue[] }) {
  return (
    <ul data-testid="governance-issues">
      {issuesByRule(issues).map(group => (
        <li key={group.rule ?? "structure"} data-rule={group.rule ?? ""}>
          <strong>{group.rule ?? "Structure"}</strong>
          {group.rule && <> · {RATCHET_RULE_EXPLANATIONS[group.rule]}</>}
          <ul>{group.issues.map((issue, index) => <li key={`${issue.code}-${index}`}>{issue.message}</li>)}</ul>
        </li>
      ))}
    </ul>
  );
}

/** A refused request, with each ratchet issue under its rule id. */
export function GovernanceRefusalPanel({ refusal, onReload, reloadLabel = "Reload" }: {
  refusal: GovernanceRefusal; onReload?: () => void; reloadLabel?: string;
}) {
  return (
    <div className="ds-banner ds-banner-warn" role="alert" data-testid="governance-refusal" style={{ marginBottom: 16 }}>
      <p style={{ margin: 0 }}>{refusal.message}</p>
      {refusal.issues.length > 0 && <IssueList issues={refusal.issues} />}
      {onReload && <button type="button" className="btn btn-secondary" style={{ marginTop: 8 }} onClick={onReload}>{reloadLabel}</button>}
    </div>
  );
}

const PROPOSAL_STATE_TEXT: Record<ProposalResponse["state"], string> = {
  DRAFT: "Draft",
  PENDING_APPROVAL: "Awaiting Director decision",
  APPROVED: "Approved",
  REJECTED: "Rejected",
  WITHDRAWN: "Withdrawn",
  STALE: "Out of date",
};

export function ProposalStatus({ proposal }: { proposal: ProposalResponse }) {
  const who = proposal.author_id ? `by ${proposal.author_id}` : "with no recorded author";
  return (
    <div className="ds-banner" role="status" data-testid="proposal-status" style={{ marginBottom: 16 }}>
      <strong>Open proposal · {PROPOSAL_STATE_TEXT[proposal.state]}</strong>
      {proposal.kind !== "CHANGE" && <> · <span className="tag tag-accent" data-testid="proposal-kind">{PROPOSAL_KIND_LABEL[proposal.kind]}</span></>}
      {" "}· {who} · based on version {proposal.base_version}.{" "}
      {proposal.state === "DRAFT" && (proposal.can_edit
        ? "Not visible to cases or the Director until you submit. One open proposal per workflow."
        : "Only its author can edit it.")}
      {proposal.state === "PENDING_APPROVAL" && "Its content is frozen for one Director decision. It can't be edited."}
      {proposal.kind !== "CHANGE" && <p style={{ margin: "6px 0 0" }}>{PROPOSAL_KIND_EXPLANATION[proposal.kind]}</p>}
      {proposal.note && <p className="text-muted" style={{ margin: "6px 0 0" }}>{proposal.note}</p>}
    </div>
  );
}

function percent(used: number, max: number): string {
  return max > 0 ? `${((used / max) * 100).toFixed(1)}%` : "—";
}

export function ValidationReportPanel({ report, current }: { report: ValidationReport; current: boolean }) {
  return (
    <section className="card" aria-labelledby="validation-report" data-testid="validation-report" style={{ marginBottom: 16 }}>
      <h2 id="validation-report">Validation report</h2>
      <p className="text-muted">Read-only: nothing is saved, published or sent to a case. The same checks run again when you submit and when the Director decides.</p>
      <p role="status">
        <strong>{report.valid ? "Ready to submit" : "Not ready to submit"}</strong>
        {" · "}{report.issues.length} {report.issues.length === 1 ? "issue" : "issues"}
        {" · "}compared with active version {report.active_version}
        {!current && " · You changed the content after validating; validate again."}
      </p>
      <p className="text-muted" data-testid="validation-size">
        Size {report.encoded_bytes.toLocaleString("en-SG")} of {report.max_encoded_bytes.toLocaleString("en-SG")} bytes ({percent(report.encoded_bytes, report.max_encoded_bytes)})
      </p>
      {report.issues.length > 0 && <IssueList issues={report.issues} />}
      {report.permanent_obligations.length > 0 && (
        <div className="ds-banner ds-banner-warn" data-testid="permanent-obligations" style={{ marginTop: 12 }}>
          <p style={{ margin: 0 }}><strong>{PERMANENT_OBLIGATION_WARNING}</strong></p>
          <ul>{report.permanent_obligations.map(item => (
            <li key={`${item.key.stage_id}:${item.key.field_id ?? ""}`}>
              {item.stage_name}{item.field_label ? ` · ${item.field_label}` : ""}: {item.detail}
            </li>
          ))}</ul>
        </div>
      )}
    </section>
  );
}

export function SimulationResultPanel({ result }: { result: SimulationResult }) {
  return (
    <div data-testid="simulation-result">
      {result.outcomes.map(outcome => (
        <article key={outcome.scenario.scenario_id} className="card" style={{ marginTop: 12 }}>
          <h3>{outcome.scenario.label} <span className="tag tag-neutral">Synthetic</span></h3>
          <p className="text-muted">{outcome.scenario.description}</p>
          <ol>{outcome.steps.map(step => (
            <li key={step.node_id}>
              {step.name}
              {step.added && <> <span className="tag tag-accent">Added step</span></>}
              {step.blocks_send && " · holds the send until confirmed"}
              {step.required_field_labels.length > 0 && ` · required: ${step.required_field_labels.join(", ")}`}
            </li>
          ))}</ol>
          <p role="status"><strong>{outcome.held_before_send ? "Send held" : "Send not held"}</strong> · {outcome.summary}</p>
        </article>
      ))}
    </div>
  );
}

const provenanceLine = provenanceText;

/** Only governed approvals count as approved; legacy activations never do (ADR-017 §1.4). */
export function approvedVersionCount(items: VersionProvenance[]): number {
  return items.filter(item => item.origin === "GOVERNED_APPROVAL" && item.approved_by !== null).length;
}

export function VersionHistoryList({ governance, actions, children }: {
  governance: WorkflowGovernanceView;
  /** M2: per-version actions (View, Propose restore); UI shaping only. */
  actions?: (item: VersionProvenance) => ReactNode;
  children?: ReactNode;
}) {
  const items = [...governance.version_provenance].sort((a, b) => b.version - a.version);
  const approved = approvedVersionCount(items);
  return (
    <section className="card" aria-labelledby="version-history" data-testid="version-history" style={{ marginTop: 16 }}>
      <h2 id="version-history">Version history</h2>
      <p className="text-muted" data-testid="approved-count">
        {items.length} {items.length === 1 ? "version" : "versions"} · {approved} approved through governance
      </p>
      {items.length === 0 && <p className="text-muted">No published versions yet.</p>}
      <ul>{items.map(item => (
        <li key={item.version} data-origin={item.origin}>
          <strong>Version {item.version}</strong> · {new Date(item.published_at).toLocaleString()} · {provenanceLine(item)}
          {item.origin === "PRE_GOVERNANCE_DIRECTOR_ACTIVATION" && (
            <p className="text-muted" style={{ margin: "2px 0 0" }}>{item.note ?? LEGACY_PROVENANCE_NOTE}</p>
          )}
          {item.origin === "EMERGENCY_FALLBACK" && item.note && (
            <p className="text-muted" style={{ margin: "2px 0 0" }}>Note: {item.note}</p>
          )}
          {actions && <div className="case-header-actions" style={{ justifyContent: "flex-start", marginTop: 4 }}>{actions(item)}</div>}
        </li>
      ))}</ul>
      {children}
    </section>
  );
}
