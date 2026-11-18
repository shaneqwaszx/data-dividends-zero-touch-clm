import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { presentationDisplay, presentationIssueCount } from "../stageDisplay";
import type { ProcessingNode, StagePresentation, StagePresentationState, ZeroTouchCaseSummary } from "../types";
import { OnboardingProgressPanel, PipelineRail, stagePresentationNote, stageStatusFor } from "./CaseStatePanels";
import StageDisclosure from "./StageDisclosure";

// OPQ S2: the frontend renders the backend stage verdict (OPQ S1) and derives nothing itself.

function verdict(state: StagePresentationState, extra: Partial<StagePresentation> = {}): StagePresentation {
  return {
    state,
    reason_code: null,
    owned_exception_ids: [],
    linked_exception_ids: [],
    counts_as_done: state === "COMPLETE" || state === "SKIPPED",
    blocks_send: false,
    ...extra,
  };
}

function node(
  nodeId: string, label: string, status: ProcessingNode["status"], presentation?: StagePresentation | null,
): ProcessingNode {
  const result: ProcessingNode = { node_id: nodeId, label, status, children: [] };
  if (presentation !== undefined) result.presentation = presentation;
  return result;
}

function summaryWith(nodes: ProcessingNode[], exceptionIds: string[] = []): ZeroTouchCaseSummary {
  return {
    case: {
      case_id: "00000000-0000-4000-8000-000000000001",
      requested_uen: "11111999A",
      registry_route: { status: "SELECTED", jurisdiction: "SG", provider: "ACRA", decided_at: "2026-09-28T00:00:00Z" },
      registry_acquisition: null,
      entity: null,
    },
    clm: { submission_plan: { environment: "SANDBOX" } },
    automation_id: "00000000-0000-4000-8000-000000000002",
    version: 3,
    status: "WAITING_FOR_REVIEW",
    current_stage: "DOCUMENT",
    completed_stages: ["REGISTRY", "GOLDTIER_SEARCH"],
    active_exceptions: exceptionIds.map(exception_id => ({
      exception_id, exception_type: "SOURCE_CONFLICT", stage: "DOCUMENT", status: "OPEN",
      blocker_code: "SOURCE_CONFLICT_REQUIRES_POLICY", evidence: [],
    })),
    interventions: [],
    reconciliation: null,
    technical_failure: null,
    metrics: {
      automated_stages_completed: 2, human_interventions: 0, exceptions_resolved: 0,
      total_duration_ms: null, final_outcome: null, stage_durations_ms: {},
    },
    target_operations: [],
    stage_order_version: 2,
    processing_pipeline: nodes,
    timeline: [],
    created_at: "2026-09-28T00:00:00Z",
    updated_at: "2026-09-28T00:00:02Z",
    timing: {
      observed_at: "2026-09-28T00:00:02Z", case_elapsed_ms: 2000, time_since_last_update_ms: 0,
      automation_elapsed_ms: 2000, recorded_total_duration_ms: null,
    },
  } as unknown as ZeroTouchCaseSummary;
}

function railStep(summary: ZeroTouchCaseSummary, nodeId: string): string {
  const rail = renderToStaticMarkup(<PipelineRail summary={summary} onStageActivate={() => undefined} />);
  const start = rail.indexOf(`data-node-id="${nodeId}"`);
  const next = rail.indexOf('class="ds-stage"', start);
  return rail.slice(start, next < 0 ? undefined : next);
}

function header(summary: ZeroTouchCaseSummary, nodeIds: string[]): string {
  const quiet = vi.spyOn(console, "error").mockImplementation(() => undefined);
  try {
    return renderToStaticMarkup(
      <StageDisclosure title="Stage" status={stageStatusFor(summary, nodeIds)} summary="Summary." scopeKey="case" main={<p>Body</p>} />,
    );
  } finally {
    quiet.mockRestore();
  }
}

function progress(summary: ZeroTouchCaseSummary): string {
  return renderToStaticMarkup(<OnboardingProgressPanel summary={summary} onStageActivate={() => undefined} />);
}

const TONES: Record<StagePresentationState, string> = {
  NOT_STARTED: "pending",
  RUNNING: "current",
  COMPLETE: "done",
  SKIPPED: "done",
  REVIEW_ADVISED: "advised",
  ACTION_REQUIRED: "attention",
  BLOCKED: "attention",
  FAILED: "attention",
};
const RAILS: Record<StagePresentationState, string> = {
  NOT_STARTED: "", RUNNING: "now", COMPLETE: "done", SKIPPED: "done",
  REVIEW_ADVISED: "advised", ACTION_REQUIRED: "attention", BLOCKED: "attention", FAILED: "attention",
};

describe("OPQ S2 shared stage presentation", () => {
  it.each(Object.keys(TONES) as StagePresentationState[])("sidebar and section header agree for %s", (state) => {
    // The backend status deliberately disagrees, so only the verdict can produce the display.
    const summary = summaryWith([node("OWNERSHIP_UBO", "Ownership & UBO", "COMPLETE", verdict(state))]);
    const label = presentationDisplay(verdict(state)).label;
    expect(label.length).toBeGreaterThan(0);
    expect(stageStatusFor(summary, ["OWNERSHIP_UBO"])).toEqual({ tone: TONES[state], label });
    const chip = header(summary, ["OWNERSHIP_UBO"]);
    expect(chip).toContain(`data-tone="${TONES[state]}"`);
    expect(chip).toMatch(new RegExp(`class="stage-disclosure__status"[^>]*>${label}<`));
    const step = railStep(summary, "OWNERSHIP_UBO");
    expect(step).toContain(`data-presentation-state="${state}"`);
    expect(step).toContain(`class="ds-stage-node ${RAILS[state]}"`);
    // Accessibility: visible words accompany the colour on the rail and in the stage facts.
    expect(step).toContain(`<div class="text-muted">${label}</div>`);
    expect(step).toContain(`<strong>Status:</strong> ${label}`);
    // Green "Complete" only for COMPLETE / SKIPPED.
    expect(step.includes("ds-stage-node done")).toBe(state === "COMPLETE" || state === "SKIPPED");
  });

  it("labels review advised amber and an action with its reason", () => {
    expect(presentationDisplay(verdict("REVIEW_ADVISED"))).toMatchObject({ label: "Review advised", rail: "advised", symbol: "!" });
    expect(presentationDisplay(verdict("ACTION_REQUIRED", { reason_code: "IDENTITY_CONFIRMATION_REQUIRED" })).label)
      .toBe("Action required — confirm UEN");
    expect(presentationDisplay(verdict("ACTION_REQUIRED", { reason_code: "OPEN_EXCEPTION" })).label).toBe("Action required");
    expect(presentationDisplay(verdict("ACTION_REQUIRED", { reason_code: "OWNERSHIP_REVIEW_REQUIRED" })).label)
      .toBe("Action required — ownership review required");
    expect(presentationDisplay(verdict("NOT_STARTED", { reason_code: "WAITING_FOR_EARLIER_STEPS" })))
      .toMatchObject({ label: "Waiting for earlier steps", waiting: true, rail: "" });
  });
});

describe("OPQ S2 counters", () => {
  function pipeline(ownership: StagePresentation): ProcessingNode[] {
    return [
      node("ACRA_REGISTRY", "Registry verification", "COMPLETE", verdict("COMPLETE")),
      node("DOCUMENT_IDP", "Document verification", "COMPLETE", verdict("COMPLETE")),
      node("OWNERSHIP_UBO", "Ownership & UBO", "COMPLETE", ownership),
      node("ADVISORY", "Risk assessment", "NOT_REACHED", verdict("NOT_STARTED")),
    ];
  }

  it("A1: Review advised is not counted as done", () => {
    const advised = progress(summaryWith(pipeline(verdict("REVIEW_ADVISED", { reason_code: "EVIDENCE_ABSENT" }))));
    expect(advised).toContain("2 of 4 stages done");
    const complete = progress(summaryWith(pipeline(verdict("COMPLETE", { reason_code: "NO_QUALIFYING_UBO" }))));
    expect(complete).toContain("3 of 4 stages done");
  });

  it("counts owned exception ids only, never linked ids", () => {
    const nodes = [
      node("ACRA_REGISTRY", "Registry verification", "COMPLETE", verdict("ACTION_REQUIRED", {
        reason_code: "IDENTITY_CONFIRMATION_REQUIRED", linked_exception_ids: ["exc-uen"], blocks_send: true,
      })),
      node("DOCUMENT_IDP", "Document verification", "REVIEW_REQUIRED", verdict("ACTION_REQUIRED", {
        owned_exception_ids: ["exc-uen"], blocks_send: true,
      })),
      node("RECONCILIATION", "Reconciliation", "REVIEW_REQUIRED", verdict("ACTION_REQUIRED", {
        linked_exception_ids: ["exc-uen"], blocks_send: true,
      })),
    ];
    const summary = summaryWith(nodes, ["exc-uen"]);
    expect(presentationIssueCount(summary)).toBe(1);
    expect(progress(summary)).toMatch(/Active issues<span class="sr-only">: <\/span><\/dt><dd>1<\/dd>/);
    summary.technical_failure = { code: "X" } as ZeroTouchCaseSummary["technical_failure"];
    expect(presentationIssueCount(summary)).toBe(2);
  });

  it("uses the legacy count when any stage lacks a verdict", () => {
    const summary = summaryWith([
      node("ACRA_REGISTRY", "Registry verification", "COMPLETE", verdict("COMPLETE")),
      node("DOCUMENT_IDP", "Document verification", "REVIEW_REQUIRED", null),
    ], ["exc-a", "exc-b"]);
    expect(presentationIssueCount(summary)).toBeNull();
    expect(progress(summary)).toMatch(/Active issues<span class="sr-only">: <\/span><\/dt><dd>2<\/dd>/);
  });
});

describe("OPQ S2 A3 UEN conflict on Registry verification", () => {
  const conflict = () => summaryWith([
    node("ACRA_REGISTRY", "Registry verification", "COMPLETE", verdict("ACTION_REQUIRED", {
      reason_code: "IDENTITY_CONFIRMATION_REQUIRED", linked_exception_ids: ["exc-uen"], blocks_send: true,
    })),
    node("DOCUMENT_IDP", "Document verification", "REVIEW_REQUIRED", verdict("ACTION_REQUIRED", {
      owned_exception_ids: ["exc-uen"], blocks_send: true,
    })),
  ], ["exc-uen"]);
  // Either resolution path (keep the entered UEN, or use the document UEN) yields the same verdicts.
  const resolved = () => summaryWith([
    node("ACRA_REGISTRY", "Registry verification", "COMPLETE", verdict("COMPLETE")),
    node("DOCUMENT_IDP", "Document verification", "COMPLETE", verdict("COMPLETE")),
  ]);

  it("shows Action required — confirm UEN with a link to the owning Document stage", () => {
    const summary = conflict();
    expect(stageStatusFor(summary, ["ACRA_REGISTRY"])).toEqual({ tone: "attention", label: "Action required — confirm UEN" });
    const step = railStep(summary, "ACRA_REGISTRY");
    expect(step).toContain('data-status="COMPLETE"');
    expect(step).toContain("Action required — confirm UEN");
    expect(step).toContain("Linked issue — owned and counted in Document verification.");
    expect(step).toContain(">Open Document verification</button>");
    const note = stagePresentationNote(summary, "ACRA_REGISTRY");
    expect(note.state).toBe("ACTION_REQUIRED");
    expect(note.linkedTo.map(owner => owner.node_id)).toEqual(["DOCUMENT_IDP"]);
    // The owning stage carries no link to itself, and the issue is counted once.
    expect(railStep(summary, "DOCUMENT_IDP")).not.toContain("Linked issue");
    expect(presentationIssueCount(summary)).toBe(1);
  });

  it.each(["entered UEN confirmed", "document UEN accepted"])("returns to Complete after %s", () => {
    const summary = resolved();
    expect(stageStatusFor(summary, ["ACRA_REGISTRY"])).toEqual({ tone: "done", label: "Complete" });
    const step = railStep(summary, "ACRA_REGISTRY");
    expect(step).not.toContain("Linked issue");
    expect(step).not.toContain("Action required");
    expect(presentationIssueCount(summary)).toBe(0);
  });
});

describe("OPQ S2 zero-UBO versus no evidence", () => {
  const ownershipOnly = (presentation: StagePresentation) => summaryWith([
    node("OWNERSHIP_UBO", "Ownership & UBO", "COMPLETE", presentation),
  ]);

  it("shows a valid zero-UBO result as complete with a plain note", () => {
    const summary = ownershipOnly(verdict("COMPLETE", { reason_code: "NO_QUALIFYING_UBO" }));
    expect(stageStatusFor(summary, ["OWNERSHIP_UBO"])).toEqual({ tone: "done", label: "Complete" });
    const step = railStep(summary, "OWNERSHIP_UBO");
    expect(step).toContain("No qualifying UBOs identified.");
    expect(step).not.toContain("No ownership evidence");
    expect(stagePresentationNote(summary, "OWNERSHIP_UBO").note).toBe("No qualifying UBOs identified.");
  });

  it("shows absent evidence as review advised, not as zero UBOs", () => {
    const summary = ownershipOnly(verdict("REVIEW_ADVISED", { reason_code: "EVIDENCE_ABSENT" }));
    expect(stageStatusFor(summary, ["OWNERSHIP_UBO"])).toEqual({ tone: "advised", label: "Review advised" });
    const step = railStep(summary, "OWNERSHIP_UBO");
    expect(step).toContain("No ownership evidence was available to analyse.");
    expect(step).not.toContain("No qualifying UBOs");
    expect(step).not.toContain("ds-stage-node done");
  });
});

describe("OPQ S2 fallback without a verdict", () => {
  const legacyNodes = (presentation?: null) => [
    node("ACRA_REGISTRY", "Registry verification", "COMPLETE", presentation),
    node("DOCUMENT_IDP", "Document verification", "REVIEW_REQUIRED", presentation),
    { ...node("OWNERSHIP_UBO", "Ownership & UBO", "COMPLETE", presentation), advisory_review: true },
    node("READINESS", "Readiness", "BLOCKED", presentation),
    node("GOLDTIER_TARGET", "GoldTier package", "NOT_REACHED", presentation),
  ];

  it("renders a null verdict exactly as an older backend without the field", () => {
    const absent = summaryWith(legacyNodes(), ["exc-a"]);
    const nulled = summaryWith(legacyNodes(null), ["exc-a"]);
    const rail = (summary: ZeroTouchCaseSummary) => renderToStaticMarkup(<PipelineRail summary={summary} onStageActivate={() => undefined} />);
    expect(rail(nulled)).toBe(rail(absent));
    expect(progress(nulled)).toBe(progress(absent));
    for (const ids of [["ACRA_REGISTRY"], ["DOCUMENT_IDP"], ["OWNERSHIP_UBO"], ["READINESS", "GOLDTIER_TARGET"]]) {
      expect(stageStatusFor(nulled, ids)).toEqual(stageStatusFor(absent, ids));
    }
  });

  it("keeps the legacy labels, D-141 advised display and counting", () => {
    const summary = summaryWith(legacyNodes(null), ["exc-a"]);
    expect(stageStatusFor(summary, ["ACRA_REGISTRY"])).toEqual({ tone: "done", label: "Complete" });
    expect(stageStatusFor(summary, ["DOCUMENT_IDP"])).toEqual({ tone: "attention", label: "Review required" });
    expect(stageStatusFor(summary, ["OWNERSHIP_UBO"])).toEqual({ tone: "advised", label: "Review advised" });
    const markup = progress(summary);
    // Legacy counting: the advisory COMPLETE node still counts (unchanged before OPQ S2).
    expect(markup).toContain("2 of 4 stages done");
    expect(markup).toMatch(/Active issues<span class="sr-only">: <\/span><\/dt><dd>1<\/dd>/);
    expect(markup).not.toContain("data-presentation-state");
    expect(markup).not.toContain("Linked issue");
  });

  it("ignores an unrecognised verdict state and keeps the legacy display", () => {
    const summary = summaryWith([
      node("ACRA_REGISTRY", "Registry verification", "COMPLETE", verdict("FUTURE_STATE" as StagePresentationState)),
    ]);
    expect(stageStatusFor(summary, ["ACRA_REGISTRY"])).toEqual({ tone: "done", label: "Complete" });
    expect(presentationIssueCount(summary)).toBeNull();
  });
});
