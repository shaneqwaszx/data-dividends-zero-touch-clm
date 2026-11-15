import { useQuery } from "@tanstack/react-query";
import { lazy, Suspense, useCallback, useMemo, useState, type ReactNode } from "react";

import { ApiError, fetchPolicies } from "../api";
import type { AuthenticatedProfile, PolicyRule } from "../types";
import {
  ENFORCEMENT_LABELS,
  EVIDENCE_LABELS,
  WORKFLOW_WIDE_ID,
  bindRules,
  canViewExecutionPlan,
  executionPlanQueryKeys,
  fetchExecutionPlan,
  formatPolicyValue,
  formatRange,
  type BoundRules,
  type ExecutionPlan,
  type PlanFixedControl,
  type PlanConditionalRuleUsage,
  type PlanOptionalStep,
  type PlanStage,
  type SharedRule,
} from "../workflowExecutionPlan";
import "./WorkflowDesigner.css";

export type DesignerView = "diagram" | "outline";

export interface DiagramProps {
  plan: ExecutionPlan;
  selectedId: string;
  onSelect: (stageId: string) => void;
  /** Rules defined at the stage, and shared rules it also reads (defined elsewhere). */
  ruleCounts: Map<string, RuleCount>;
}

export interface RuleCount {
  own: number;
  shared: number;
}

// Loaded only when the designer opens, so the canvas library stays out of the main bundle.
const LazyDiagram = lazy(() => import("./ExecutionPlanDiagram"));

function defaultRenderDiagram(props: DiagramProps) {
  return (
    <Suspense fallback={<p className="text-muted" role="status">Loading the diagram…</p>}>
      <LazyDiagram {...props} />
    </Suspense>
  );
}

const ORDER_LABELS: Record<ExecutionPlan["registry_search_order"], string> = {
  SEARCH_THEN_REGISTRY: "GoldTier search runs before ACRA registry verification",
  REGISTRY_THEN_SEARCH: "ACRA registry verification runs before the GoldTier search",
};

const OPTIONAL_STATE_LABELS: Record<ExecutionPlan["optional_steps"]["state"], string> = {
  ACTIVE: "Active",
  NO_ACTIVE_WORKFLOW: "None active",
  UNAVAILABLE: "Workflow check unavailable",
};

function planError(error: unknown): string {
  if (error instanceof ApiError && error.status === 403) {
    return "The workflow designer is available to HR administrators and Directors.";
  }
  return "The execution plan could not be loaded. Nothing was changed; try again.";
}

/** Optional steps grouped under the mandatory stage they are displayed after. */
export function optionalStepsByAnchor(plan: ExecutionPlan): Map<string, PlanOptionalStep[]> {
  const grouped = new Map<string, PlanOptionalStep[]>();
  for (const step of plan.optional_steps.steps) {
    const anchor = step.shown_after ?? "CASE_START";
    grouped.set(anchor, [...(grouped.get(anchor) ?? []), step]);
  }
  return grouped;
}

export function optionalStepNote(step: PlanOptionalStep): string {
  return step.blocks_send
    ? "Must be confirmed before Final review & send · does not pause automation"
    : "No required fields · does not block the send or pause automation";
}

export default function WorkflowDesigner({
  actor,
  renderDiagram = defaultRenderDiagram,
  initialView = "diagram",
}: {
  actor: AuthenticatedProfile;
  /** The read-only canvas; replaceable in tests. The outline view always works. */
  renderDiagram?: (props: DiagramProps) => ReactNode;
  initialView?: DesignerView;
}) {
  const allowed = canViewExecutionPlan(actor);
  const planQuery = useQuery({
    queryKey: executionPlanQueryKeys.plan(actor.user_id),
    queryFn: ({ signal }) => fetchExecutionPlan(signal),
    enabled: allowed,
    retry: false,
  });
  const policyQuery = useQuery({
    queryKey: executionPlanQueryKeys.policies(actor.user_id),
    queryFn: ({ signal }) => fetchPolicies(signal),
    enabled: allowed,
    retry: false,
  });
  const [view, setView] = useState<DesignerView>(initialView);
  const [selectedId, setSelectedId] = useState<string>("CASE_START");
  const select = useCallback((stageId: string) => setSelectedId(stageId), []);
  const bound = useMemo(
    () => (planQuery.data ? bindRules(planQuery.data, policyQuery.data) : null),
    [planQuery.data, policyQuery.data],
  );
  const ruleCounts = useMemo(
    () => new Map(planQuery.data?.stages.map(stage => [
      stage.stage_id,
      { own: stage.policy_rule_ids.length, shared: (stage.policy_rule_references ?? []).length },
    ]) ?? []),
    [planQuery.data],
  );

  if (!allowed) {
    return (
      <section className="ds-root ds-page" aria-labelledby="designer-title">
        <h1 id="designer-title">Workflow designer</h1>
        <p className="text-muted">The workflow designer is available to HR administrators and Directors.</p>
      </section>
    );
  }
  if (planQuery.isPending) {
    return (
      <section className="ds-root ds-page" aria-busy="true" aria-labelledby="designer-title">
        <h1 id="designer-title">Workflow designer</h1>
        <p className="text-muted" role="status">Loading the execution plan…</p>
      </section>
    );
  }
  if (planQuery.isError || !planQuery.data || !bound) {
    return (
      <section className="ds-root ds-page" aria-labelledby="designer-title">
        <h1 id="designer-title">Workflow designer</h1>
        <div className="ds-banner ds-banner-warn" role="alert">
          <p>{planError(planQuery.error)}</p>
          <button type="button" className="btn btn-secondary" onClick={() => void planQuery.refetch()}>Try again</button>
        </div>
      </section>
    );
  }

  const plan = planQuery.data;
  const anchors = optionalStepsByAnchor(plan);
  const selected = plan.stages.find(stage => stage.stage_id === selectedId);

  return (
    <section className="ds-root ds-page wfd" aria-labelledby="designer-title">
      <header className="ds-page-header wfd-header">
        <div>
          <p className="card-kicker">Policy &amp; Workflow · read-only preview</p>
          <h1 id="designer-title">Workflow designer</h1>
          <p className="text-muted">
            The onboarding process this backend actually runs. Nothing here can be edited, moved, saved or published.
          </p>
        </div>
        <div className="wfd-lanes" aria-label="Running provider lanes">
          {plan.provider_lanes.map(lane => (
            <span key={lane.lane} className={`tag ${lane.evidence_class === "PARTIAL" ? "tag-accent" : "tag-neutral"}`}>
              {lane.lane}: {lane.mode} · {EVIDENCE_LABELS[lane.evidence_class]}
            </span>
          ))}
        </div>
      </header>

      <div className="wfd-notices">
        <p className="wfd-notice"><strong>{ORDER_LABELS[plan.registry_search_order]}.</strong> {plan.order_explanation}</p>
        <p className={`wfd-notice${plan.optional_steps.state === "UNAVAILABLE" ? " wfd-notice--warn" : ""}`} role={plan.optional_steps.state === "UNAVAILABLE" ? "alert" : undefined}>
          <strong>Added workflow stages: {OPTIONAL_STATE_LABELS[plan.optional_steps.state]}</strong>
          {plan.optional_steps.version !== null && ` (version ${plan.optional_steps.version})`}
          {!plan.optional_steps.manager_enabled && " · workflow manager switched off"}. {plan.optional_steps.explanation}
        </p>
        <p className="wfd-notice">
          <strong>Conditional branches are not supported by the current backend.</strong> No branch is drawn because none can run.
        </p>
      </div>

      <div className="wfd-toolbar" role="group" aria-label="View">
        <button type="button" className={`btn ${view === "diagram" ? "btn-primary" : "btn-secondary"}`} aria-pressed={view === "diagram"} onClick={() => setView("diagram")}>Diagram</button>
        <button type="button" className={`btn ${view === "outline" ? "btn-primary" : "btn-secondary"}`} aria-pressed={view === "outline"} onClick={() => setView("outline")}>Outline</button>
      </div>

      <div className="wfd-body">
        <div className="wfd-main">
          {view === "diagram"
            ? renderDiagram({ plan, selectedId, onSelect: select, ruleCounts })
            : <PlanOutline plan={plan} anchors={anchors} selectedId={selectedId} onSelect={select} />}
        </div>
        <aside className="card wfd-panel" aria-label="Selected stage details">
          {selectedId === WORKFLOW_WIDE_ID || !selected
            ? <WorkflowWideDetails plan={plan} bound={bound} catalogueLoaded={Boolean(policyQuery.data)} />
            : <StageDetails stage={selected} plan={plan} bound={bound} catalogueLoaded={Boolean(policyQuery.data)} added={anchors.get(selected.stage_id) ?? []} />}
          <button type="button" className="btn btn-ghost wfd-wide-link" onClick={() => setSelectedId(WORKFLOW_WIDE_ID)} aria-pressed={selectedId === WORKFLOW_WIDE_ID}>
            Workflow-wide rules and constants
          </button>
          {policyQuery.isError && <p className="text-muted" role="status">Policy values are temporarily unavailable; rule ids are still shown.</p>}
        </aside>
      </div>
    </section>
  );
}

function PlanOutline({ plan, anchors, selectedId, onSelect }: {
  plan: ExecutionPlan;
  anchors: Map<string, PlanOptionalStep[]>;
  selectedId: string;
  onSelect: (stageId: string) => void;
}) {
  return (
    <ol className="wfd-outline" aria-label="Onboarding execution plan, in run order">
      {plan.stages.map((stage, index) => (
        <li key={stage.stage_id} className="wfd-outline__item">
          <button
            type="button"
            className={`wfd-stage${selectedId === stage.stage_id ? " wfd-stage--selected" : ""}`}
            aria-pressed={selectedId === stage.stage_id}
            onClick={() => onSelect(stage.stage_id)}
          >
            <span className="wfd-stage__number" aria-hidden="true">{index + 1}</span>
            <span className="wfd-stage__text">
              <span className="wfd-stage__label">{stage.label}</span>
              <span className="wfd-stage__meta">Mandatory · fixed · engine {stage.engine_stage}</span>
            </span>
            <span className="tag tag-neutral wfd-stage__lock">Fixed</span>
          </button>
          {(anchors.get(stage.stage_id) ?? []).map(step => (
            <div key={step.stage_id} className="wfd-added" role="note" aria-label={`Added stage ${step.name}`}>
              <span className="wfd-added__name">{step.name}</span>
              <span className="wfd-added__note">{optionalStepNote(step)}</span>
            </div>
          ))}
        </li>
      ))}
    </ol>
  );
}

function RuleFacts({ rule }: { rule: PolicyRule }) {
  return (
    <dl className="wfd-rule__facts">
      <div><dt>Value</dt><dd>{formatPolicyValue(rule.value)}</dd></div>
      <div><dt>Range</dt><dd>{formatRange(rule)}</dd></div>
      <div><dt>Enforcement</dt><dd>{ENFORCEMENT_LABELS[rule.enforcement]}</dd></div>
    </dl>
  );
}

function stageNames(ids: string[], labels: Map<string, string>): string {
  return ids.map(id => labels.get(id) ?? id).join(", ");
}

function RuleList({ rules, catalogueLoaded, ids, usedBy, labels, hasShared = false }: {
  rules: PolicyRule[];
  catalogueLoaded: boolean;
  ids: string[];
  usedBy?: Map<string, string[]>;
  labels?: Map<string, string>;
  hasShared?: boolean;
}) {
  if (ids.length === 0 && rules.length === 0) {
    return (
      <p className="text-muted">
        {hasShared ? "No rule is defined at this stage; it reads the shared rules below." : "No policy rule applies to this stage."}
      </p>
    );
  }
  if (!catalogueLoaded) {
    return <ul className="wfd-list">{ids.map(id => <li key={id}><code>{id}</code></li>)}</ul>;
  }
  // A stacked list rather than a wide table: every value stays visible in the narrow panel.
  return (
    <ul className="wfd-rule-list" aria-label="Policy rules for this stage">
      {rules.map(rule => (
        <li key={rule.policy_id} className="wfd-rule">
          <span className="wfd-rule__name">{rule.name}</span>
          <code className="wfd-rule__id">{rule.policy_id}</code>
          <RuleFacts rule={rule} />
          {labels && (usedBy?.get(rule.policy_id) ?? []).length > 0 && (
            <p className="wfd-rule__shared">
              <span className="tag tag-accent">Shared</span>{" "}
              Also used by {stageNames(usedBy?.get(rule.policy_id) ?? [], labels)}. Changing it changes those stages too.
            </p>
          )}
        </li>
      ))}
    </ul>
  );
}

/** Catalogue ownership is not runtime use: say when this stage only reads its rules conditionally. */
function ConditionalUsage({ usage }: { usage: PlanConditionalRuleUsage[] }) {
  if (usage.length === 0) return null;
  return (
    <>
      {usage.map(item => (
        <p key={item.consumer} className="wfd-conditional" role="note" aria-label="Conditional runtime use">
          <span className="tag tag-neutral">Catalogue owner · conditional use</span>{" "}
          {item.rule_ids.length} of these rules are defined here. {item.condition} {item.effect}{" "}
          <strong>
            In this environment: {item.runs_in_this_environment ? "running (demo candidate data on)." : "not running (demo candidate data off)."}
          </strong>
        </p>
      ))}
    </>
  );
}

/** Rules this stage reads but does not own: one definition and value, shown with their primary stage. */
function SharedRuleList({ shared, catalogueLoaded, labels, usedBy, stageId }: {
  shared: SharedRule[];
  catalogueLoaded: boolean;
  labels: Map<string, string>;
  usedBy: Map<string, string[]>;
  stageId: string;
}) {
  if (shared.length === 0) return null;
  const groups = new Map<string, SharedRule[]>();
  for (const item of shared) {
    const key = `${item.reference.primary_stage_id}|${item.reference.effect}`;
    groups.set(key, [...(groups.get(key) ?? []), item]);
  }
  return (
    <>
      <h3 className="wfd-subhead">Shared rules also used here</h3>
      {[...groups.entries()].map(([key, group]) => {
        const { primary_stage_id: primary, effect, rule_id: firstRule } = group[0].reference;
        const primaryName = labels.get(primary) ?? primary;
        const others = (usedBy.get(firstRule) ?? []).filter(id => id !== stageId);
        return (
          <div key={key} className="wfd-shared" role="group" aria-label={`Shared rules defined under ${primaryName}`}>
            <p className="wfd-shared__summary">
              <span className="tag tag-accent">Usage reference</span>{" "}
              Defined under <strong>{primaryName}</strong>; this stage reads the same values. {effect}
              {others.length > 0 && ` Also used by ${stageNames(others, labels)}.`}
            </p>
            <ul className="wfd-rule-list" aria-label={`Shared rules read by this stage, defined under ${primaryName}`}>
              {group.map(({ reference, rule }) => (
                <li key={reference.rule_id} className="wfd-rule wfd-rule--shared">
                  <span className="wfd-rule__name">{rule?.name ?? reference.rule_id}</span>
                  <code className="wfd-rule__id">{reference.rule_id}</code>
                  {catalogueLoaded && rule && <RuleFacts rule={rule} />}
                </li>
              ))}
            </ul>
          </div>
        );
      })}
    </>
  );
}

function FixedControls({ controls }: { controls: PlanFixedControl[] }) {
  if (controls.length === 0) return null;
  return (
    <>
      <h3 className="wfd-subhead">Fixed controls</h3>
      <dl className="wfd-controls">
        {controls.map(control => (
          <div key={control.source}><dt>{control.label}</dt><dd>{control.value} <code>{control.source}</code></dd></div>
        ))}
      </dl>
    </>
  );
}

function StageDetails({ stage, plan, bound, catalogueLoaded, added }: {
  stage: PlanStage;
  plan: ExecutionPlan;
  bound: BoundRules;
  catalogueLoaded: boolean;
  added: PlanOptionalStep[];
}) {
  const labels = new Map(plan.stages.map(item => [item.stage_id, item.label]));
  return (
    <div className="wfd-details">
      <p className="card-kicker">Mandatory stage · fixed</p>
      <h2>{stage.label}</h2>
      <p>{stage.runs}</p>
      <p className="wfd-fixed"><strong>Why it is fixed:</strong> {stage.fixed_reason}</p>
      <h3 className="wfd-subhead">Depends on</h3>
      {stage.prerequisites.length === 0
        ? <p className="text-muted">Nothing; this is the first stage.</p>
        : (
          <ul className="wfd-list">
            {stage.prerequisites.map(item => (
              <li key={item.stage_id}>
                <strong>{labels.get(item.stage_id) ?? item.stage_id}</strong>{" "}
                <span className="tag tag-neutral">{item.kind === "DATA" ? "Data" : "Engine order"}</span>
                <span className="wfd-reason"> {item.reason}</span>
              </li>
            ))}
          </ul>
        )}
      <h3 className="wfd-subhead">Checkpoints and blockers</h3>
      <ul className="wfd-list">{stage.checkpoints.map(item => <li key={item}>{item}</li>)}</ul>
      <h3 className="wfd-subhead">Mandatory safeguards</h3>
      <ul className="wfd-list">{stage.safeguards.map(item => <li key={item}>{item}</li>)}</ul>
      <h3 className="wfd-subhead">Policy rules</h3>
      <ConditionalUsage usage={stage.conditional_rule_usage ?? []} />
      <RuleList
        rules={bound.byStage.get(stage.stage_id) ?? []}
        catalogueLoaded={catalogueLoaded}
        ids={stage.policy_rule_ids}
        usedBy={bound.usedBy}
        labels={labels}
        hasShared={(bound.sharedByStage.get(stage.stage_id) ?? []).length > 0}
      />
      <SharedRuleList
        shared={bound.sharedByStage.get(stage.stage_id) ?? []}
        catalogueLoaded={catalogueLoaded}
        labels={labels}
        usedBy={bound.usedBy}
        stageId={stage.stage_id}
      />
      <FixedControls controls={stage.fixed_controls} />
      {added.length > 0 && (
        <>
          <h3 className="wfd-subhead">Added stages shown after this one</h3>
          <ul className="wfd-list">
            {added.map(step => (
              <li key={step.stage_id}>
                <strong>{step.name}</strong> · {step.required_field_count} of {step.field_count} fields required · {optionalStepNote(step)}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

function WorkflowWideDetails({ plan, bound, catalogueLoaded }: { plan: ExecutionPlan; bound: BoundRules; catalogueLoaded: boolean }) {
  return (
    <div className="wfd-details">
      <p className="card-kicker">Workflow-wide</p>
      <h2>Rules and constants for the whole workflow</h2>
      <p className="text-muted">Catalogue rules not tied to one stage, including any custom display-only rule, and the D-127 dashboard constants.</p>
      <h3 className="wfd-subhead">Policy rules</h3>
      <RuleList rules={bound.workflowWide} catalogueLoaded={catalogueLoaded} ids={plan.workflow_wide_policy_rule_ids} />
      <FixedControls controls={plan.workflow_wide_fixed_controls} />
      {bound.missing.length > 0 && (
        <p className="ds-banner ds-banner-warn" role="alert">The catalogue does not hold: {bound.missing.join(", ")}.</p>
      )}
    </div>
  );
}
