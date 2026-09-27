"use client";

import { useMemo, useCallback, useEffect } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useReactFlow,
  ReactFlowProvider,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import WorkflowNode from "./WorkflowNode";

const nodeTypes = {
  workflowNode: WorkflowNode,
};

function PlusIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}

export default function WorkflowCanvas({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onConnect,
  onEdgeUpdate,
  onNodeSelect,
  onEdgeSelect,
  onDropNode,
  onQuickAddReady,
  onNodeDragStop,
  onNodeDragStart,
  onContextMenu,
  isReadOnly = false,
}) {
  return (
    <ReactFlowProvider>
      <WorkflowCanvasInner
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onEdgeUpdate={onEdgeUpdate}
        onNodeSelect={onNodeSelect}
        onEdgeSelect={onEdgeSelect}
        onDropNode={onDropNode}
        onQuickAddReady={onQuickAddReady}
        onNodeDragStop={onNodeDragStop}
        onNodeDragStart={onNodeDragStart}
        onContextMenu={onContextMenu}
        isReadOnly={isReadOnly}
      />
    </ReactFlowProvider>
  );
}

function WorkflowCanvasInner({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onConnect,
  onEdgeUpdate,
  onNodeSelect,
  onEdgeSelect,
  onDropNode,
  onQuickAddReady,
  onNodeDragStop,
  onNodeDragStart,
  onContextMenu,
  isReadOnly,
}) {
  const { screenToFlowPosition } = useReactFlow();

  useEffect(() => {
    if (onQuickAddReady) {
      onQuickAddReady(() => (width = 0, height = 0) => {
        const bounds = document.querySelector(".workflow-flow")?.getBoundingClientRect();
        if (!bounds) return { x: 0, y: 0 };
        const center = screenToFlowPosition({
          x: bounds.left + (bounds.width - width) / 2,
          y: bounds.top + (bounds.height - height) / 2,
        });
        return { x: center.x - width / 2, y: center.y - height / 2 };
      });
    }
  }, [onQuickAddReady, screenToFlowPosition]);
  const defaultEdgeOptions = useMemo(
    () => ({
      type: "smoothstep",
      animated: true,
      style: { stroke: "var(--workflow-edge, #52545c)", strokeWidth: 2 },
      selectedStyle: { stroke: "var(--accent)", strokeWidth: 2.5 },
      labelStyle: { fill: "var(--workflow-edge-label-text, #dedee4)", fontSize: 10, fontWeight: 600 },
      labelBgStyle: { fill: "var(--workflow-edge-label-bg, #18191e)", fillOpacity: 0.96 },
      labelBgPadding: [7, 4],
      labelBgBorderRadius: 5,
    }),
    []
  );

  const handleDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, []);

  const handleDrop = useCallback(
    (event) => {
      event.preventDefault();
      if (isReadOnly) return;

      const rawData = event.dataTransfer.getData("application/reactflow");
      if (!rawData) return;

      try {
        const nodeDef = JSON.parse(rawData);
        // React Flow performs the viewport and zoom transform so the node lands
        // exactly at the drop pointer in flow coordinates.
        const flowPoint = screenToFlowPosition({
          x: event.clientX,
          y: event.clientY,
        });
        const position = {
          x: Math.round(flowPoint.x - 124),
          y: Math.round(flowPoint.y - 42),
        };
        if (onDropNode) onDropNode(nodeDef, position);
      } catch (err) {
        console.error("Error handling node drop:", err);
      }
    },
    [isReadOnly, onDropNode, screenToFlowPosition]
  );

  const getNodeColor = useCallback((node) => {
    const typeId = node.data?.typeId ?? "";
    if (typeId.startsWith("trigger.")) return "#f59e0b";
    if (typeId.startsWith("action.")) return "#38bdf8";
    if (typeId.startsWith("ai.")) return "#a78bfa";
    if (typeId.startsWith("logic.")) return "#34d399";
    if (typeId.startsWith("human.")) return "#fb7185";
    return "var(--border-strong)";
  }, []);

  return (
    <div
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      className="workflow-canvas relative flex-1 w-full h-full select-none overflow-hidden"
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onEdgeUpdate={onEdgeUpdate}
        onNodeClick={(_, node) => onNodeSelect && onNodeSelect(node)}
        onPaneClick={() => onNodeSelect && onNodeSelect(null)}
        onEdgeClick={(_, edge) => onEdgeSelect && onEdgeSelect(edge)}
        onNodeDragStop={onNodeDragStop}
        onNodeDragStart={onNodeDragStart}
        onNodeContextMenu={(event, node) => onContextMenu?.(event, { type: "node", id: node.id })}
        onEdgeContextMenu={(event, edge) => onContextMenu?.(event, { type: "edge", id: edge.id })}
        nodeTypes={nodeTypes}
        defaultEdgeOptions={defaultEdgeOptions}
        connectionLineStyle={{ stroke: "var(--accent)", strokeWidth: 2 }}
        nodesDraggable={!isReadOnly}
        nodesConnectable={!isReadOnly}
        elementsSelectable={true}
        fitView
        fitViewOptions={{ padding: 0.3, maxZoom: 0.9 }}
        minZoom={0.1}
        maxZoom={2}
        className="workflow-flow text-[var(--text-primary)]"
        deleteKeyCode={null}
      >
        <Background variant="dots" gap={22} size={1.1} color="var(--canvas-grid)" />

      <Controls className="workflow-controls !bg-[var(--surface)] !border !border-[var(--border-default)] !rounded-xl !shadow-xl fill-[var(--text-secondary)] stroke-[var(--text-secondary)]" />

        <MiniMap
          bgColor="var(--surface)"
          nodeColor={getNodeColor}
          nodeStrokeColor="var(--border-default)"
          nodeBorderRadius={4}
          nodeStrokeWidth={2}
          maskColor="rgba(111, 113, 126, 0.28)"
          maskStrokeColor="var(--accent)"
          maskStrokeWidth={2}
          pannable
          zoomable
          ariaLabel="Workflow minimap navigation"
          className="workflow-minimap !bg-[var(--surface)] !border !border-[var(--border-default)] !rounded-2xl !shadow-xl cursor-grab active:cursor-grabbing"
          style={{ width: 196, height: 132 }}
        />
      </ReactFlow>

      {/* Empty canvas overlay */}
      {nodes.length === 0 && (
        <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center pointer-events-none select-none z-10">
          <div className="w-12 h-12 rounded-[14px] bg-[var(--surface)] border border-[var(--border-default)] flex items-center justify-center mb-3 text-[var(--accent)] shadow-lg">
            <PlusIcon className="w-6 h-6 stroke-[1.5]" />
          </div>
          <h4 className="text-[15px] font-semibold text-[var(--text-primary)] tracking-tight mb-1">
            {isReadOnly ? "Empty workflow" : "Your canvas is ready"}
          </h4>
          <p className="text-[13px] text-[var(--text-secondary)] max-w-xs leading-relaxed">
            {isReadOnly
              ? "This version has no workflow steps."
              : "Add a trigger, then connect steps to design your workflow."}
          </p>
        </div>
      )}
    </div>
  );
}
