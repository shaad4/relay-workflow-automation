"use client";

import { useMemo, useCallback } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
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
  onDropNode,
  onNodeDragStop,
  isReadOnly = false,
}) {
  const defaultEdgeOptions = useMemo(
    () => ({
      type: "smoothstep",
      animated: true,
      style: { stroke: "var(--text-tertiary)", strokeWidth: 1.5 },
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
        // Use bounding rect to convert screen coords to canvas-relative coords.
        // This is reliable at zoom=1. For zoomed/panned canvases, React Flow's
        // internal onNodesChange will handle the actual RF-space position.
        const bounds = event.currentTarget.getBoundingClientRect();
        const position = {
          x: Math.round(event.clientX - bounds.left - 90),
          y: Math.round(event.clientY - bounds.top - 25),
        };
        if (onDropNode) onDropNode(nodeDef, position);
      } catch (err) {
        console.error("Error handling node drop:", err);
      }
    },
    [isReadOnly, onDropNode]
  );

  const getNodeColor = useCallback((node) => {
    const typeId = node.data?.typeId ?? "";
    if (typeId.startsWith("trigger.")) return "#4F46E5";
    if (typeId.startsWith("action.")) return "#0EA5E9";
    if (typeId.startsWith("ai.")) return "#8B5CF6";
    if (typeId.startsWith("logic.") || typeId.startsWith("human.")) return "#D29922";
    return "var(--border-strong)";
  }, []);

  return (
    <div
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      className="relative flex-1 w-full h-full bg-[var(--canvas)] select-none overflow-hidden"
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
        onNodeDragStop={onNodeDragStop}
        nodeTypes={nodeTypes}
        defaultEdgeOptions={defaultEdgeOptions}
        nodesDraggable={!isReadOnly}
        nodesConnectable={!isReadOnly}
        elementsSelectable={true}
        fitView
        fitViewOptions={{ padding: 0.3, maxZoom: 0.9 }}
        minZoom={0.1}
        maxZoom={2}
        className="text-[var(--text-primary)]"
        deleteKeyCode={null}
      >
        <Background variant="dots" gap={20} size={1.25} color="var(--canvas-grid)" />

        <Controls className="!bg-[var(--surface)] !border !border-[var(--border-subtle)] !rounded-lg !shadow-xs fill-[var(--text-secondary)] stroke-[var(--text-secondary)]" />

        <MiniMap
          bgColor="var(--canvas)"
          nodeColor={getNodeColor}
          nodeStrokeColor="var(--border-subtle)"
          nodeBorderRadius={4}
          nodeStrokeWidth={2}
          maskColor="rgba(0,0,0,0.45)"
          maskStrokeColor="var(--accent)"
          maskStrokeWidth={1.5}
          pannable
          zoomable
          ariaLabel="Workflow minimap navigation"
          className="!bg-[var(--surface)] !border !border-[var(--border-subtle)] !rounded-lg !shadow-sm cursor-grab active:cursor-grabbing"
          style={{ width: 170, height: 110 }}
        />
      </ReactFlow>

      {/* Empty canvas overlay */}
      {nodes.length === 0 && (
        <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center pointer-events-none select-none z-10">
          <div className="w-12 h-12 rounded-[12px] bg-[var(--surface)] border border-[var(--border-subtle)] flex items-center justify-center mb-3 text-[var(--text-tertiary)] shadow-sm">
            <PlusIcon className="w-6 h-6 stroke-[1.5]" />
          </div>
          <h4 className="text-[15px] font-semibold text-[var(--text-primary)] tracking-tight mb-1">
            {isReadOnly ? "Empty workflow" : "Start building"}
          </h4>
          <p className="text-[13px] text-[var(--text-secondary)] max-w-xs leading-relaxed">
            {isReadOnly
              ? "This workflow has no nodes."
              : "Open the Node Library and drag a node onto the canvas to get started."}
          </p>
        </div>
      )}
    </div>
  );
}
