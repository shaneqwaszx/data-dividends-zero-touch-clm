import {
  Background,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  useReactFlow,
  useStore,
  type Edge,
  type Node,
  type NodeProps,
  type NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { memo, useEffect, useMemo } from "react";

import type { ExecutionPlan, PlanOptionalStep, PlanStage } from "../workflowExecutionPlan";
import type { DiagramProps, RuleCount } from "./WorkflowDesigner";

/**
 * Read-only canvas (P1). Mandatory stages are fixed in run order; edges are the real
 * prerequisites from the backend. Nothing can be dragged, connected, deleted or edited.
 */

const STAGE_WIDTH = 300;
const STAGE_HEIGHT = 74;
const ROW_GAP = 100;
const ADDED_X = -360;

type StageData = { stage: PlanStage; index: number; selected: boolean; ruleCount: RuleCount; onSelect: (id: string) => void };
type AddedData = { step: PlanOptionalStep };

const hiddenHandle = { opacity: 0, pointerEvents: "none" as const };

function HandleSet() {
  return (
    <>
      <Handle type="target" position={Position.Top} id="top" isConnectable={false} style={hiddenHandle} />
      <Handle type="source" position={Position.Bottom} id="bottom" isConnectable={false} style={hiddenHandle} />
      <Handle type="source" position={Position.Right} id="right-out" isConnectable={false} style={hiddenHandle} />
      <Handle type="target" position={Position.Right} id="right-in" isConnectable={false} style={hiddenHandle} />
      <Handle type="source" position={Position.Left} id="left-out" isConnectable={false} style={hiddenHandle} />
      <Handle type="target" position={Position.Left} id="left-in" isConnectable={false} style={hiddenHandle} />
    </>
  );
}

const StageNode = memo(function StageNode({ data }: NodeProps<Node<StageData>>) {
  const { stage, index, selected, ruleCount, onSelect } = data;
  return (
    <div className={`wfd-node${selected ? " wfd-node--selected" : ""}`} style={{ width: STAGE_WIDTH }}>
      <HandleSet />
      <button
        type="button"
        className="wfd-node__button nodrag nopan"
        aria-pressed={selected}
        aria-label={`Stage ${index + 1}: ${stage.label}, mandatory and fixed`}
        onClick={() => onSelect(stage.stage_id)}
      >
        <span className="wfd-node__top">
          <span className="wfd-node__number" aria-hidden="true">{index + 1}</span>
          <span className="wfd-node__label">{stage.label}</span>
          <span className="wfd-node__lock" aria-hidden="true">Fixed</span>
        </span>
        <span className="wfd-node__meta">
          Engine {stage.engine_stage} · {ruleCount.own === 1 ? "1 rule" : `${ruleCount.own} rules`}
          {ruleCount.shared > 0 && ` · ${ruleCount.shared} shared`}
        </span>
      </button>
    </div>
  );
});

const AddedNode = memo(function AddedNode({ data }: NodeProps<Node<AddedData>>) {
  const { step } = data;
  return (
    <div className="wfd-node wfd-node--added" style={{ width: 300 }} role="note" aria-label={`Added stage ${step.name}`}>
      <HandleSet />
      <span className="wfd-node__label">{step.name}</span>
      <span className="wfd-node__meta">
        {step.blocks_send ? "Must be confirmed before send · does not pause automation" : "No required fields · does not block the send"}
      </span>
    </div>
  );
});

/** Refit whenever the canvas is resized (window, orientation), so stages never drift out of view. */
function FitOnResize() {
  const width = useStore(state => state.width);
  const height = useStore(state => state.height);
  const { fitView } = useReactFlow();
  useEffect(() => {
    if (width > 0 && height > 0) void fitView({ padding: 0.12 });
  }, [width, height, fitView]);
  return null;
}

const nodeTypes: NodeTypes = { stage: StageNode, added: AddedNode };

const DATA_STYLE = { stroke: "var(--color-neutral-700)", strokeWidth: 1.6 };
const ORDER_STYLE = { stroke: "var(--color-neutral-500)", strokeWidth: 1.4, strokeDasharray: "6 4" };
const ADDED_STYLE = { stroke: "var(--color-accent-600)", strokeWidth: 1.4, strokeDasharray: "3 4" };

export function buildDiagram(plan: ExecutionPlan, selectedId: string, onSelect: (id: string) => void, ruleCounts: Map<string, RuleCount>) {
  const index = new Map(plan.stages.map((stage, position) => [stage.stage_id, position]));
  const nodes: Node[] = plan.stages.map((stage, position) => ({
    id: stage.stage_id,
    type: "stage",
    position: { x: 0, y: position * ROW_GAP },
    data: { stage, index: position, selected: stage.stage_id === selectedId, ruleCount: ruleCounts.get(stage.stage_id) ?? { own: 0, shared: 0 }, onSelect },
    draggable: false,
    connectable: false,
    deletable: false,
    selectable: false,
    focusable: false,
  }));
  const edges: Edge[] = [];
  for (const stage of plan.stages) {
    const to = index.get(stage.stage_id) ?? 0;
    for (const prerequisite of stage.prerequisites) {
      const from = index.get(prerequisite.stage_id);
      if (from === undefined) continue;
      const adjacent = to - from === 1;
      edges.push({
        id: `dep-${prerequisite.stage_id}-${stage.stage_id}`,
        source: prerequisite.stage_id,
        target: stage.stage_id,
        sourceHandle: adjacent ? "bottom" : "right-out",
        targetHandle: adjacent ? "top" : "right-in",
        type: adjacent ? "straight" : "default",
        style: prerequisite.kind === "DATA" ? DATA_STYLE : ORDER_STYLE,
        markerEnd: { type: MarkerType.ArrowClosed, width: 14, height: 14 },
        selectable: false,
        focusable: false,
        deletable: false,
        reconnectable: false,
        ariaLabel: `${stage.label} depends on ${prerequisite.stage_id} (${prerequisite.kind === "DATA" ? "data" : "engine order"})`,
      });
    }
  }
  const finalReview = plan.stages.find(stage => stage.stage_id === "FINAL_REVIEW_SEND");
  const offsets = new Map<string, number>();
  for (const step of plan.optional_steps.steps) {
    const anchor = step.shown_after ?? "CASE_START";
    const anchorIndex = index.get(anchor) ?? 0;
    const offset = offsets.get(anchor) ?? 0;
    offsets.set(anchor, offset + 1);
    const id = `added-${step.stage_id}`;
    nodes.push({
      id,
      type: "added",
      position: { x: ADDED_X, y: anchorIndex * ROW_GAP + 46 + offset * 80 },
      data: { step },
      draggable: false,
      connectable: false,
      deletable: false,
      selectable: false,
      focusable: false,
    });
    edges.push({
      id: `shown-after-${id}`,
      source: anchor,
      target: id,
      sourceHandle: "left-out",
      targetHandle: "right-in",
      type: "default",
      style: ADDED_STYLE,
      label: "shown after",
      selectable: false,
      focusable: false,
      deletable: false,
      reconnectable: false,
    });
    if (step.blocks_send && finalReview) {
      edges.push({
        id: `holds-send-${id}`,
        source: id,
        target: finalReview.stage_id,
        sourceHandle: "left-out",
        targetHandle: "left-in",
        type: "default",
        style: ADDED_STYLE,
        label: "holds the send",
        markerEnd: { type: MarkerType.ArrowClosed, width: 14, height: 14 },
        selectable: false,
        focusable: false,
        deletable: false,
        reconnectable: false,
      });
    }
  }
  return { nodes, edges };
}

export default function ExecutionPlanDiagram({ plan, selectedId, onSelect, ruleCounts }: DiagramProps) {
  const { nodes, edges } = useMemo(
    () => buildDiagram(plan, selectedId, onSelect, ruleCounts),
    [plan, selectedId, onSelect, ruleCounts],
  );
  // Tall enough that twelve stages fit at a readable zoom; pan and zoom remain available.
  const height = Math.max(560, Math.min(1180, plan.stages.length * ROW_GAP * 0.9));
  return (
    <>
    <div className="card wfd-canvas" style={{ height: `min(${height}px, 85vh)` }} role="region" aria-label="Execution plan diagram (read-only). The Outline view lists the same stages.">
      <ReactFlow
        // Explicit size: the lazily loaded stylesheet can arrive after the first mount.
        style={{ width: "100%", height: "100%" }}
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.12 }}
        minZoom={0.25}
        maxZoom={1.75}
        nodesDraggable={false}
        nodesConnectable={false}
        nodesFocusable={false}
        edgesFocusable={false}
        edgesReconnectable={false}
        elementsSelectable={false}
        // Without a click handler React Flow gives read-only nodes `pointer-events: none`,
        // and the pane swallows clicks. Clicking only selects for the details panel.
        onNodeClick={(_, node) => { if (node.type === "stage") onSelect(node.id); }}
        connectOnClick={false}
        deleteKeyCode={null}
        selectionKeyCode={null}
        multiSelectionKeyCode={null}
        panOnDrag
        zoomOnScroll
        zoomOnDoubleClick={false}
      >
        <Background gap={20} size={1} />
        <Controls showInteractive={false} position="top-right" />
        <FitOnResize />
      </ReactFlow>
    </div>
    <p className="wfd-legend" aria-label="Diagram legend">
      <span>Data dependency</span>
      <span className="wfd-legend__order">Engine-order constraint</span>
      <span className="wfd-legend__added">Added stage (shown after · holds the send)</span>
    </p>
    </>
  );
}
