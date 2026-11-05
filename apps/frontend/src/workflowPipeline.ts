import type { ProcessingNode } from "./types";
import type { WorkflowRun } from "./workflowApi";

const STAGE_NODE_PREFIX = "WORKFLOW_STAGE_";

/** The on-page anchor of an added stage's form, or null for any other node. */
export function workflowStageElementId(nodeId: string): string | null {
  return nodeId.startsWith(STAGE_NODE_PREFIX) ? `workflow-stage-${nodeId.slice(STAGE_NODE_PREFIX.length)}` : null;
}

const GROUPED_ANCHORS: Record<string, string> = { READINESS: "GOLDTIER_DETAILS", GOLDTIER_TARGET: "GOLDTIER_DETAILS" };

function stageNode(stage: WorkflowRun["stages"][number]): ProcessingNode {
  return {
    node_id: `${STAGE_NODE_PREFIX}${stage.stage_id}`,
    label: stage.name,
    status: stage.status === "COMPLETE" ? "COMPLETE" : "REVIEW_REQUIRED",
    safe_result: stage.status === "COMPLETE" ? "Ready" : "Not ready",
    timestamp: stage.confirmed_at,
    children: [],
  };
}

/**
 * Display-only: added stages join the shown business steps after their anchor. They never
 * enter summary.processing_pipeline, so nothing that reads backend state reacts to them.
 * An anchor that is not shown (Initial identity once done) falls back to the stage before it.
 */
export function withWorkflowStages(pipeline: ProcessingNode[], run: WorkflowRun | null | undefined): ProcessingNode[] {
  if (!run) return pipeline;
  const merged = [...pipeline];
  for (const stage of run.stages) {
    const anchor = stage.after_node_id ?? "";
    const anchorId = GROUPED_ANCHORS[anchor] ?? anchor;
    let index = merged.findIndex(node => node.node_id === anchorId);
    if (index < 0) index = merged.findIndex(node => node.node_id === "CASE_START");
    while (merged[index + 1]?.node_id.startsWith(STAGE_NODE_PREFIX)) index += 1;
    merged.splice(index + 1, 0, stageNode(stage));
  }
  return merged;
}
