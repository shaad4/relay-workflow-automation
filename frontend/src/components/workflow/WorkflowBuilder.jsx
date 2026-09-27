"use client";

import { useState, useCallback, useEffect, useRef, useMemo } from "react";
import {
  useNodesState,
  useEdgesState,
  addEdge,
} from "@xyflow/react";

import WorkflowToolbar from "./WorkflowToolbar";
import NodeLibrary from "./NodeLibrary";
import WorkflowCanvas from "./WorkflowCanvas";
import NodeInspector from "./NodeInspector";
import WorkflowValidation from "./WorkflowValidation";
import { getNodeDefinition } from "./nodeDefinitions";
import {
  createWorkflowNode,
  updateWorkflowNode,
  deleteWorkflowNode,
  createWorkflowEdge,
  deleteWorkflowEdge,
  updateWorkflowEdge,
  validateWorkflow,
  publishWorkflow,
  createDraftVersion,
} from "@/services/workflows";

// ─────────────────────────────────────────────────────────────────────────────
// Icons
// ─────────────────────────────────────────────────────────────────────────────
function SettingsIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  );
}

function LibraryIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <path d="M9 3v18" />
    </svg>
  );
}

function PlusIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}

function EditIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Data transformation helpers
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Transform a backend node into:
 *   - rfNode: React Flow node (uses backend UUID as id)
 *   - serverNode: lightweight server-state snapshot
 */
function transformBackendNode(n) {
  const backendUUID = String(n.id);
  const logicalNodeId = String(n.node_id || n.id);
  const typeId = n.node_type || n.type || "action.http_request";
  const def = getNodeDefinition(typeId);

  // Position — backend returns position_x / position_y (flat ints)
  const posX = Number(n.position_x ?? n.position?.x ?? 250);
  const posY = Number(n.position_y ?? n.position?.y ?? 150);

  // Configuration — backend field may be "configuration" or "config"
  let cfg = def.defaultConfig || {};
  const rawCfg = n.configuration ?? n.config;
  if (rawCfg) {
    if (typeof rawCfg === "string") {
      try { cfg = JSON.parse(rawCfg); } catch { /* ignore */ }
    } else {
      cfg = rawCfg;
    }
  }

  const label = n.label || n.name || def.name;

  const rfNode = {
    id: backendUUID,
    type: "workflowNode",
    position: { x: posX, y: posY },
    data: {
      nodeId: logicalNodeId,   // logical node_id (used in edge references)
      typeId,
      label,
      name: label,
      category: def.category,
      icon: def.icon,
      config: cfg,
    },
  };

  const serverNode = {
    rfId: backendUUID,
    nodeId: logicalNodeId,
    node_type: typeId,
    label,
    position_x: Math.round(posX),
    position_y: Math.round(posY),
    configuration: cfg,
  };

  return { rfNode, serverNode };
}

/**
 * Transform backend edges into RF edges.
 * Requires a nodeId→rfId map because edge source/target fields on the
 * backend are the logical node_id, but RF needs the UUID.
 */
function transformBackendEdge(e, nodeIdToRfId) {
  const backendEdgeId = String(e.id);
  // The backend stores logical node IDs in source_node_id / target_node_id
  const sourceLogical = String(e.source_node_id || e.source);
  const targetLogical = String(e.target_node_id || e.target);
  // Resolve to RF node ids (UUIDs)
  const sourceRfId = nodeIdToRfId[sourceLogical] ?? sourceLogical;
  const targetRfId = nodeIdToRfId[targetLogical] ?? targetLogical;

  const rfEdge = {
    id: backendEdgeId,
    source: sourceRfId,
    target: targetRfId,
    type: "smoothstep",
    animated: true,
    style: { stroke: "var(--text-tertiary)", strokeWidth: 1.5 },
    data: { condition: e.condition ?? null },
    label: e.condition || "",
  };

  const serverEdge = {
    rfId: backendEdgeId,
    source: sourceRfId,
    target: targetRfId,
    sourceNodeId: sourceLogical,
    targetNodeId: targetLogical,
    condition: e.condition ?? null,
  };

  return { rfEdge, serverEdge };
}

// Grid layout constants
const GRID_COL_W = 290;
const GRID_ROW_H = 190;
const GRID_COLS = 3;
const GRID_ORIGIN_X = 100;
const GRID_ORIGIN_Y = 100;

/**
 * Build all initial state from raw backend arrays.
 * Returns: { rfNodes, rfEdges, serverNodes, serverEdges }
 *
 * If ALL nodes share the same position (typically 0,0 when created via API
 * without positions), we auto-layout them in a grid so they are visible.
 */
function buildInitialState(rawNodes, rawEdges) {
  const rfNodes = [];
  const serverNodes = [];
  const nodeIdToRfId = {}; // logical node_id → RF id (UUID)

  for (const n of (rawNodes || [])) {
    const { rfNode, serverNode } = transformBackendNode(n);
    rfNodes.push(rfNode);
    serverNodes.push(serverNode);
    nodeIdToRfId[serverNode.nodeId] = serverNode.rfId;
  }

  // Auto-layout when all nodes share the same position (e.g. all at 0,0).
  // This happens when nodes were created via API without explicit positions.
  if (rfNodes.length > 0) {
    const firstX = rfNodes[0].position.x;
    const firstY = rfNodes[0].position.y;
    const allSamePosition = rfNodes.every(
      (n) => n.position.x === firstX && n.position.y === firstY
    );
    if (allSamePosition) {
      rfNodes.forEach((n, i) => {
        const col = i % GRID_COLS;
        const row = Math.floor(i / GRID_COLS);
        n.position = {
          x: GRID_ORIGIN_X + col * GRID_COL_W,
          y: GRID_ORIGIN_Y + row * GRID_ROW_H,
        };
        // Also update the matching serverNode so save diff works correctly
        const sn = serverNodes.find((s) => s.rfId === n.id);
        if (sn) {
          sn.position_x = n.position.x;
          sn.position_y = n.position.y;
        }
      });
    }
  }

  const rfEdges = [];
  const serverEdges = [];
  for (const e of (rawEdges || [])) {
    const { rfEdge, serverEdge } = transformBackendEdge(e, nodeIdToRfId);
    rfEdges.push(rfEdge);
    serverEdges.push(serverEdge);
  }

  return { rfNodes, rfEdges, serverNodes, serverEdges };
}

// ─────────────────────────────────────────────────────────────────────────────
// WorkflowBuilder component
// ─────────────────────────────────────────────────────────────────────────────
export default function WorkflowBuilder({
  workflow = {},
  version = {},
  initialNodes = [],
  initialEdges = [],
  token = null,
  onRefresh = () => {},
}) {
  const workflowId = workflow?.id ?? "";
  const versionNumber = version?.version_number ?? version?.version ?? 1;
  const isReadOnly = (version?.status ?? "draft") === "published";

  // ── Initialise from props ──────────────────────────────────────────────────
  const { rfNodes, rfEdges, serverNodes, serverEdges } = useMemo(
    () => buildInitialState(initialNodes, initialEdges),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [] // intentionally run once — builder re-mounts via key when version changes
  );

  // ── Server state refs (what the backend currently has) ─────────────────────
  // We mutate these refs directly during save operations.
  const serverNodesRef = useRef(serverNodes);
  const serverEdgesRef = useRef(serverEdges);

  // ── React Flow local editor state ─────────────────────────────────────────
  const [nodes, setNodes, onNodesChange] = useNodesState(rfNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(rfEdges);

  // ── UI states ─────────────────────────────────────────────────────────────
  const [isLibraryOpen, setIsLibraryOpen] = useState(false);
  const [isInspectorOpen, setIsInspectorOpen] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  // saveState: 'saved' | 'unsaved' | 'saving' | 'failed'
  const [saveState, setSaveState] = useState("saved");
  const [saveError, setSaveError] = useState(null);
  const [isValidating, setIsValidating] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  const [isCreatingDraft, setIsCreatingDraft] = useState(false);
  const [validationOpen, setValidationOpen] = useState(false);
  const [validationResult, setValidationResult] = useState({ isValid: true, errors: [] });
  const [currentVersionStatus, setCurrentVersionStatus] = useState(version?.status ?? "draft");

  // ── Derived ───────────────────────────────────────────────────────────────
  const isCanvasReadOnly = currentVersionStatus === "published";

  const selectedNode = useMemo(
    () => (selectedNodeId ? nodes.find((n) => n.id === selectedNodeId) ?? null : null),
    [nodes, selectedNodeId]
  );

  // ── Counter for generating logical node IDs ────────────────────────────────
  const nodeCounterRef = useRef({});

  function getNextNodeId(typeId) {
    const prefix = typeId.split(".").pop();
    const current = nodeCounterRef.current[prefix] ?? 0;
    nodeCounterRef.current[prefix] = current + 1;
    return `${prefix}_${current + 1}`;
  }

  // Seed counter from existing nodes on mount
  useEffect(() => {
    for (const n of rfNodes) {
      const prefix = (n.data.typeId ?? "").split(".").pop();
      if (!prefix) continue;
      const match = (n.data.nodeId ?? "").match(/_(\d+)$/);
      if (match) {
        const num = parseInt(match[1], 10);
        nodeCounterRef.current[prefix] = Math.max(
          nodeCounterRef.current[prefix] ?? 0,
          num
        );
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── beforeunload guard ────────────────────────────────────────────────────
  useEffect(() => {
    const handler = (e) => {
      if (saveState === "unsaved" || saveState === "failed") {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [saveState]);

  // ── Node selection ────────────────────────────────────────────────────────
  const handleNodeSelect = useCallback((node) => {
    setSelectedNodeId(node ? node.id : null);
    if (node) setIsInspectorOpen(true);
  }, []);

  // ── Mark unsaved helper ───────────────────────────────────────────────────
  const markUnsaved = useCallback(() => {
    setSaveState((prev) => (prev !== "saving" ? "unsaved" : prev));
  }, []);

  // ── Node: drop from library ───────────────────────────────────────────────
  const handleDropNode = useCallback(
    (nodeDef, position) => {
      if (isCanvasReadOnly) return;
      const logicalId = getNextNodeId(nodeDef.typeId);
      const tempId = `temp-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
      const def = getNodeDefinition(nodeDef.typeId);

      const newNode = {
        id: tempId,
        type: "workflowNode",
        position: { x: Math.round(position.x), y: Math.round(position.y) },
        data: {
          nodeId: logicalId,
          typeId: nodeDef.typeId,
          label: nodeDef.name,
          name: nodeDef.name,
          category: def.category,
          icon: def.icon,
          config: { ...(nodeDef.defaultConfig ?? {}) },
        },
      };

      setNodes((nds) => nds.concat(newNode));
      setSelectedNodeId(tempId);
      setIsInspectorOpen(true);
      markUnsaved();
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [isCanvasReadOnly, markUnsaved]
  );

  // Quick-add via sub-bar buttons
  const handleQuickAdd = useCallback(
    (typeId) => {
      const def = getNodeDefinition(typeId);
      const position = {
        x: 250 + Math.random() * 60,
        y: 150 + nodes.length * 80,
      };
      handleDropNode(def, position);
    },
    [handleDropNode, nodes.length]
  );

  // ── Node: drag-stop (position update, local only) ─────────────────────────
  const handleNodeDragStop = useCallback(
    (_event, node) => {
      if (isCanvasReadOnly) return;
      // Update local position already applied by RF; just mark unsaved
      markUnsaved();
    },
    [isCanvasReadOnly, markUnsaved]
  );

  const handleEdgeUpdate = useCallback((oldEdge, connection) => {
    if (isCanvasReadOnly) return;
    setEdges((current) => current.map((edge) => edge.id === oldEdge.id ? {
      ...edge,
      source: connection.source,
      target: connection.target,
      sourceHandle: connection.sourceHandle,
      targetHandle: connection.targetHandle,
    } : edge));
    markUnsaved();
  }, [isCanvasReadOnly, markUnsaved, setEdges]);

  // ── Node: update config from inspector (local only) ───────────────────────
  const handleUpdateNodeData = useCallback(
    (id, newData) => {
      if (isCanvasReadOnly) return;
      setNodes((nds) =>
        nds.map((n) =>
          n.id === id
            ? { ...n, data: { ...n.data, ...newData } }
            : n
        )
      );
      markUnsaved();
    },
    [isCanvasReadOnly, markUnsaved, setNodes]
  );

  // ── Node: delete (local only) ─────────────────────────────────────────────
  const handleDeleteNode = useCallback(
    (id) => {
      if (isCanvasReadOnly) return;
      setNodes((nds) => nds.filter((n) => n.id !== id));
      setEdges((eds) => eds.filter((e) => e.source !== id && e.target !== id));
      if (selectedNodeId === id) setSelectedNodeId(null);
      markUnsaved();
    },
    [isCanvasReadOnly, selectedNodeId, markUnsaved, setNodes, setEdges]
  );

  // ── Edge: connect (local only) ────────────────────────────────────────────
  const handleConnect = useCallback(
    (connection) => {
      if (isCanvasReadOnly) return;
      const tempEdgeId = `temp-edge-${Date.now()}`;
      const newEdge = {
        ...connection,
        id: tempEdgeId,
        type: "smoothstep",
        animated: true,
        style: { stroke: "var(--text-tertiary)", strokeWidth: 1.5 },
        data: { condition: null },
      };
      setEdges((eds) => addEdge(newEdge, eds));
      markUnsaved();
    },
    [isCanvasReadOnly, markUnsaved, setEdges]
  );

  // ── Edge: changes (local; deletes mark unsaved) ───────────────────────────
  const handleEdgesChange = useCallback(
    (changes) => {
      onEdgesChange(changes);
      if (isCanvasReadOnly) return;
      const hasRemoval = changes.some((c) => c.type === "remove");
      if (hasRemoval) markUnsaved();
    },
    [onEdgesChange, isCanvasReadOnly, markUnsaved]
  );

  const handleNodeChanges = useCallback((changes) => {
    onNodesChange(changes);
    if (isCanvasReadOnly) return;
    if (changes.some((change) => change.type === "position" && change.dragging === false)) {
      markUnsaved();
    }
  }, [onNodesChange, isCanvasReadOnly, markUnsaved]);

  // ── SAVE: diff-based sync to backend ─────────────────────────────────────
  const handleSave = useCallback(async () => {
    if (isCanvasReadOnly || saveState === "saving") return;
    setSaveState("saving");
    setSaveError(null);

    // Snapshot local state at this moment
    // Note: nodes/edges from closure captured at call time
    // We need latest — use functional form trick below via ref
    const nodesSnap = [...nodes];
    const edgesSnap = [...edges];
    const srvNodes = serverNodesRef.current;
    const srvEdges = serverEdgesRef.current;

    // Categorise nodes
    const newNodes = nodesSnap.filter((n) => n.id.startsWith("temp-"));
    const existingNodes = nodesSnap.filter((n) => !n.id.startsWith("temp-"));
    const updatedNodes = existingNodes.filter((n) => {
      const sn = srvNodes.find((s) => s.rfId === n.id);
      if (!sn) return false;
      return (
        Math.round(n.position.x) !== sn.position_x ||
        Math.round(n.position.y) !== sn.position_y ||
        (n.data.label ?? "") !== (sn.label ?? "") ||
        JSON.stringify(n.data.config ?? {}) !== JSON.stringify(sn.configuration ?? {})
      );
    });
    const deletedNodes = srvNodes.filter(
      (sn) => !nodesSnap.find((n) => n.id === sn.rfId)
    );

    // Categorise edges
    const newEdges = edgesSnap.filter((e) => e.id.startsWith("temp-"));
    const existingEdges = edgesSnap.filter((e) => !e.id.startsWith("temp-"));
    const updatedEdges = existingEdges.filter((edge) => {
      const serverEdge = srvEdges.find((candidate) => candidate.rfId === edge.id);
      if (!serverEdge) return false;
      const sourceNode = nodesSnap.find((node) => node.id === edge.source);
      const targetNode = nodesSnap.find((node) => node.id === edge.target);
      return (
        (sourceNode?.data?.nodeId ?? edge.source) !== (nodesSnap.find((node) => node.id === serverEdge.source)?.data?.nodeId ?? serverEdge.source) ||
        (targetNode?.data?.nodeId ?? edge.target) !== (nodesSnap.find((node) => node.id === serverEdge.target)?.data?.nodeId ?? serverEdge.target) ||
        (edge.data?.condition ?? null) !== (serverEdge.condition ?? null)
      );
    });
    const deletedEdges = srvEdges.filter(
      (se) => !edgesSnap.find((e) => e.id === se.rfId)
    );
    const nodeIdsBeingDeleted = new Set(deletedNodes.map((node) => node.nodeId));
    const deletedEdgesForRemovedNodes = srvEdges.filter((edge) =>
      nodeIdsBeingDeleted.has(edge.sourceNodeId) || nodeIdsBeingDeleted.has(edge.targetNodeId)
    );
    const edgesToDelete = [...new Map(
      [...deletedEdges, ...deletedEdgesForRemovedNodes].map((edge) => [edge.rfId, edge])
    ).values()];

    // Map: tempNodeId → realUUID (populated as we create nodes)
    const tempToReal = {};

    try {
      // ── 1. Create new nodes ──────────────────────────────────────────────
      for (const node of newNodes) {
        const res = await createWorkflowNode(token, workflowId, versionNumber, {
          node_id: node.data.nodeId,
          node_type: node.data.typeId,
          label: node.data.label,
          position_x: Math.round(node.position.x),
          position_y: Math.round(node.position.y),
          configuration: node.data.config ?? {},
        });
        const created = res?.data ?? res?.node ?? res;
        const realId = String(created?.id ?? created?.node_id ?? "");
        if (!realId) throw new Error("The server created a node but did not return its ID.");
        tempToReal[node.id] = realId;
        // Add to server state ref
        serverNodesRef.current.push({
          rfId: realId,
          nodeId: node.data.nodeId,
          node_type: node.data.typeId,
          label: node.data.label,
          position_x: Math.round(node.position.x),
          position_y: Math.round(node.position.y),
          configuration: node.data.config ?? {},
        });
      }

      // ── 2. Update changed existing nodes ────────────────────────────────
      for (const node of updatedNodes) {
        const targetNodeId = node.data?.nodeId ?? node.id;
        await updateWorkflowNode(token, workflowId, versionNumber, targetNodeId, {
          label: node.data.label,
          position_x: Math.round(node.position.x),
          position_y: Math.round(node.position.y),
          configuration: node.data.config ?? {},
        });
        const si = serverNodesRef.current.findIndex((s) => s.rfId === node.id);
        if (si >= 0) {
          serverNodesRef.current[si] = {
            ...serverNodesRef.current[si],
            label: node.data.label,
            position_x: Math.round(node.position.x),
            position_y: Math.round(node.position.y),
            configuration: node.data.config ?? {},
          };
        }
      }

      // ── 3. Delete removed edges first (FK constraint) ───────────────────
      for (const se of edgesToDelete) {
        if (!se.rfId.startsWith("temp-")) {
          await deleteWorkflowEdge(token, workflowId, versionNumber, se.rfId);
        }
        serverEdgesRef.current = serverEdgesRef.current.filter(
          (s) => s.rfId !== se.rfId
        );
      }

      // ── 4. Delete removed nodes ──────────────────────────────────────────
      for (const sn of deletedNodes) {
        await deleteWorkflowNode(token, workflowId, versionNumber, sn.nodeId ?? sn.rfId);
        serverNodesRef.current = serverNodesRef.current.filter(
          (s) => s.rfId !== sn.rfId
        );
      }

      // ── 5. Create new edges ──────────────────────────────────────────────
      // Map: RF node id / UUID → logical node_id (needed for edge API payload)
      const rfIdToNodeId = {};
      for (const sn of serverNodesRef.current) {
        rfIdToNodeId[sn.rfId] = sn.nodeId;
      }
      for (const n of nodesSnap) {
        const logicalId = n.data?.nodeId;
        if (logicalId) {
          rfIdToNodeId[n.id] = logicalId;
          if (tempToReal[n.id]) {
            rfIdToNodeId[tempToReal[n.id]] = logicalId;
          }
        }
      }

      const tempEdgeToReal = {};
      for (const edge of newEdges) {
        const sourceRfId = tempToReal[edge.source] ?? edge.source;
        const targetRfId = tempToReal[edge.target] ?? edge.target;
        const sourceNodeId = rfIdToNodeId[sourceRfId] ?? rfIdToNodeId[edge.source] ?? sourceRfId;
        const targetNodeId = rfIdToNodeId[targetRfId] ?? rfIdToNodeId[edge.target] ?? targetRfId;

        const res = await createWorkflowEdge(token, workflowId, versionNumber, {
          source_node_id: sourceNodeId,
          target_node_id: targetNodeId,
          condition: edge.data?.condition ?? null,
        });
        const created = res?.data ?? res?.edge ?? res;
        const realEdgeId = String(created?.id ?? "");
        if (!realEdgeId) throw new Error("The server created a connection but did not return its ID.");
        tempEdgeToReal[edge.id] = realEdgeId;
        serverEdgesRef.current.push({
          rfId: realEdgeId,
          source: sourceRfId,
          target: targetRfId,
          sourceNodeId: sourceNodeId,
          targetNodeId: targetNodeId,
          condition: edge.data?.condition ?? null,
        });
      }

      // ── 6. Update existing edges ────────────────────────────────────────
      for (const edge of updatedEdges) {
        const sourceNode = nodesSnap.find((node) => node.id === edge.source);
        const targetNode = nodesSnap.find((node) => node.id === edge.target);
        const sourceNodeId = sourceNode?.data?.nodeId ?? edge.source;
        const targetNodeId = targetNode?.data?.nodeId ?? edge.target;
        await updateWorkflowEdge(token, workflowId, versionNumber, edge.id, {
          source_node_id: sourceNodeId,
          target_node_id: targetNodeId,
          condition: edge.data?.condition ?? null,
        });
        const index = serverEdgesRef.current.findIndex((item) => item.rfId === edge.id);
        if (index >= 0) serverEdgesRef.current[index] = {
          ...serverEdgesRef.current[index],
          source: edge.source,
          target: edge.target,
          sourceNodeId: sourceNodeId,
          targetNodeId: targetNodeId,
          condition: edge.data?.condition ?? null,
        };
      }

      // ── 7. Replace temp IDs in React Flow state ──────────────────────────
      if (Object.keys(tempToReal).length > 0 || Object.keys(tempEdgeToReal).length > 0) {
        setNodes((prev) =>
          prev.map((n) => {
            if (tempToReal[n.id]) return { ...n, id: tempToReal[n.id] };
            return n;
          })
        );
        setEdges((prev) =>
          prev.map((e) => {
            const newId = tempEdgeToReal[e.id] ?? e.id;
            const newSource = tempToReal[e.source] ?? e.source;
            const newTarget = tempToReal[e.target] ?? e.target;
            return { ...e, id: newId, source: newSource, target: newTarget };
          })
        );
        // Update selectedNodeId if it was a temp node
        if (selectedNodeId && tempToReal[selectedNodeId]) {
          setSelectedNodeId(tempToReal[selectedNodeId]);
        }
      }

      // Changes made while this request was in flight remain unsaved.
      const nodesChangedDuringSave = nodes.some((node) => {
        const snapshot = nodesSnap.find((item) => item.id === node.id);
        return !snapshot || JSON.stringify(node) !== JSON.stringify(snapshot);
      }) || nodesSnap.some((snapshot) => !nodes.some((node) => node.id === snapshot.id));
      const edgesChangedDuringSave = edges.some((edge) => {
        const snapshot = edgesSnap.find((item) => item.id === edge.id);
        return !snapshot || JSON.stringify(edge) !== JSON.stringify(snapshot);
      }) || edgesSnap.some((snapshot) => !edges.some((edge) => edge.id === snapshot.id));
      setSaveState(nodesChangedDuringSave || edgesChangedDuringSave ? "unsaved" : "saved");
    } catch (err) {
      console.error("Save failed:", err);
      setSaveState("failed");
      setSaveError(err.message ?? "Save failed. Please try again.");
    }
  }, [
    isCanvasReadOnly,
    saveState,
    nodes,
    edges,
    token,
    workflowId,
    versionNumber,
    selectedNodeId,
    setNodes,
    setEdges,
  ]);

  // ── Validate ──────────────────────────────────────────────────────────────
  const handleValidate = useCallback(async () => {
    setIsValidating(true);
    try {
      // Save first if there are unsaved changes
      if (saveState === "unsaved" || saveState === "failed") {
        const priorSaveState = saveState;
        await handleSave();
        if (priorSaveState === "failed") {
          setValidationResult({ isValid: false, errors: [{ code: "SAVE_FAILED", message: "Save failed. Fix the save issue before validating." }] });
          return;
        }
      }

      let res = null;
      if (token && workflowId) {
        try {
          res = await validateWorkflow(token, workflowId, versionNumber);
        } catch (err) {
          console.warn("API Validate error, falling back to local validation:", err);
        }
      }

      if (res && res.valid !== undefined) {
        setValidationResult({
          isValid: Boolean(res.valid),
          errors: res.errors ?? [],
        });
      } else {
        // Local structural validation fallback
        const hasTrigger = nodes.some((n) => n.data.typeId?.startsWith("trigger."));
        if (!hasTrigger) {
          setValidationResult({
            isValid: false,
            errors: [{ code: "NO_TRIGGER", message: "Workflow must have at least one Trigger node." }],
          });
        } else if (nodes.length > 1 && edges.length === 0) {
          setValidationResult({
            isValid: false,
            errors: [{ code: "DISCONNECTED_NODES", message: "All nodes must be connected with edges before publishing." }],
          });
        } else {
          setValidationResult({ isValid: true, errors: [] });
        }
      }
    } finally {
      setIsValidating(false);
      setValidationOpen(true);
    }
  }, [saveState, handleSave, nodes, edges, token, workflowId, versionNumber]);

  // ── Publish ───────────────────────────────────────────────────────────────
  const handlePublish = useCallback(async () => {
    if (isCanvasReadOnly) return;
    setIsPublishing(true);
    try {
      // Save first
      if (saveState === "unsaved" || saveState === "failed") {
        const priorSaveState = saveState;
        await handleSave();
        if (priorSaveState === "failed") throw new Error("Save failed. Publish was not started.");
      }
      if (token && workflowId) {
        await publishWorkflow(token, workflowId, versionNumber);
      }
      setCurrentVersionStatus("published");
      if (onRefresh) onRefresh();
    } catch (err) {
      console.error("Publish failed:", err);
    } finally {
      setIsPublishing(false);
    }
  }, [isCanvasReadOnly, saveState, handleSave, token, workflowId, versionNumber, onRefresh]);

  // ── Edit Workflow (create draft from published) ───────────────────────────
  const handleEditWorkflow = useCallback(async () => {
    if (!token || !workflowId) return;
    setIsCreatingDraft(true);
    try {
      await createDraftVersion(token, workflowId);
      if (onRefresh) onRefresh();
    } catch (err) {
      console.error("Failed to create draft:", err);
    } finally {
      setIsCreatingDraft(false);
    }
  }, [token, workflowId, onRefresh]);

  // ── Keyboard shortcuts ────────────────────────────────────────────────────
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (
        ["INPUT", "TEXTAREA", "SELECT"].includes(e.target.tagName) ||
        e.target.isContentEditable
      )
        return;

      if ((e.key === "Delete" || e.key === "Backspace") && selectedNodeId && !isCanvasReadOnly) {
        handleDeleteNode(selectedNodeId);
      } else if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        handleSave();
      } else if (e.key === "Escape") {
        setSelectedNodeId(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [selectedNodeId, isCanvasReadOnly, handleDeleteNode, handleSave]);

  // ─────────────────────────────────────────────────────────────────────────
  // Render
  // ─────────────────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col h-full w-full bg-[var(--canvas)] select-none overflow-hidden font-sans">
      {/* ── 1. Top Toolbar ─────────────────────────────────────────────────── */}
      <WorkflowToolbar
        workflowName={workflow?.name || "Workflow"}
        versionNumber={versionNumber}
        status={currentVersionStatus}
        saveState={saveState}
        saveError={saveError}
        isReadOnly={isCanvasReadOnly}
        onSave={handleSave}
        onValidate={handleValidate}
        onPublish={handlePublish}
        onEditWorkflow={handleEditWorkflow}
        isValidating={isValidating}
        isPublishing={isPublishing}
        isCreatingDraft={isCreatingDraft}
      />

      {/* ── 2. Sub-bar: Library / Inspector toggles + Quick Add ────────────── */}
      {!isCanvasReadOnly && (
        <div className="h-9 px-4 bg-[var(--surface)] border-b border-[var(--border-subtle)] flex items-center gap-2 text-[12px] text-[var(--text-secondary)] shrink-0 z-10">
          {/* Library toggle */}
          <button
            type="button"
            onClick={() => setIsLibraryOpen((v) => !v)}
            className={`px-2.5 py-1 rounded-[6px] border text-[12px] font-medium flex items-center gap-1.5 transition-all duration-100 ease-out cursor-pointer ${
              isLibraryOpen
                ? "bg-[#4F46E5] text-white border-[#4F46E5] shadow-xs"
                : "bg-[var(--canvas)] hover:bg-[var(--elevated)] text-[var(--text-primary)] border-[var(--border-default)] hover:border-[var(--border-strong)]"
            }`}
          >
            <LibraryIcon className="w-3.5 h-3.5 stroke-[1.5]" />
            <span>Node Library</span>
            <span className="text-[10px] font-mono opacity-70">{isLibraryOpen ? "◀" : "▶"}</span>
          </button>

          {/* Inspector toggle */}
          <button
            type="button"
            onClick={() => setIsInspectorOpen((v) => !v)}
            className={`px-2.5 py-1 rounded-[6px] border text-[12px] font-medium flex items-center gap-1.5 transition-all duration-100 ease-out cursor-pointer ${
              isInspectorOpen
                ? "bg-[#4F46E5] text-white border-[#4F46E5] shadow-xs"
                : "bg-[var(--canvas)] hover:bg-[var(--elevated)] text-[var(--text-primary)] border-[var(--border-default)] hover:border-[var(--border-strong)]"
            }`}
          >
            <SettingsIcon className="w-3.5 h-3.5 stroke-[1.5]" />
            <span>Inspector</span>
            <span className="text-[10px] font-mono opacity-70">{isInspectorOpen ? "▶" : "◀"}</span>
          </button>

          <span className="h-4 w-px bg-[var(--border-subtle)] mx-1" />

          <span className="font-semibold text-[var(--text-tertiary)] flex items-center gap-1">
            <PlusIcon className="w-3.5 h-3.5 stroke-[1.5]" />
            Quick Add:
          </span>
          {[
            { typeId: "ai.decision", label: "🧠 AI Decision" },
            { typeId: "logic.condition", label: "🔀 Condition" },
            { typeId: "action.http_request", label: "🌐 HTTP Request" },
          ].map(({ typeId, label }) => (
            <button
              key={typeId}
              type="button"
              onClick={() => handleQuickAdd(typeId)}
              className="px-2 py-0.5 rounded border border-[var(--border-subtle)] bg-[var(--canvas)] hover:bg-[var(--elevated)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
            >
              {label}
            </button>
          ))}
        </div>
      )}

      {/* ── 3. Main studio layout ──────────────────────────────────────────── */}
      <div className="flex-1 flex min-h-0 overflow-hidden relative">
        {/* Left: Node Library */}
        {isLibraryOpen && !isCanvasReadOnly && (
          <NodeLibrary onClose={() => setIsLibraryOpen(false)} />
        )}

        {/* Center: Canvas */}
        <div className="relative flex-1 flex flex-col h-full min-w-0">
          {/* Floating "open library" hint */}
          {!isLibraryOpen && !isCanvasReadOnly && (
            <button
              type="button"
              onClick={() => setIsLibraryOpen(true)}
              className="absolute left-3 top-3 z-20 h-8 px-2.5 rounded-[6px] bg-[var(--surface)] border border-[var(--border-default)] hover:border-[var(--border-strong)] shadow-xs text-[12px] font-medium text-[var(--text-primary)] flex items-center gap-1.5 transition-all duration-100 ease-out cursor-pointer hover:bg-[var(--elevated)]"
            >
              <LibraryIcon className="w-3.5 h-3.5 stroke-[1.5]" />
              <span>Node Library</span>
            </button>
          )}

          {/* Floating "open inspector" hint */}
          {!isInspectorOpen && !isCanvasReadOnly && (
            <button
              type="button"
              onClick={() => setIsInspectorOpen(true)}
              className="absolute right-3 top-3 z-20 h-8 px-2.5 rounded-[6px] bg-[var(--surface)] border border-[var(--border-default)] hover:border-[var(--border-strong)] shadow-xs text-[12px] font-medium text-[var(--text-primary)] flex items-center gap-1.5 transition-all duration-100 ease-out cursor-pointer hover:bg-[var(--elevated)]"
            >
              <SettingsIcon className="w-3.5 h-3.5 stroke-[1.5]" />
              <span>Inspector</span>
            </button>
          )}

          <WorkflowCanvas
            nodes={nodes}
            edges={edges}
            onNodesChange={handleNodeChanges}
            onEdgesChange={handleEdgesChange}
            onConnect={handleConnect}
            onEdgeUpdate={handleEdgeUpdate}
            onNodeSelect={handleNodeSelect}
            onDropNode={handleDropNode}
            onNodeDragStop={handleNodeDragStop}
            isReadOnly={isCanvasReadOnly}
          />
        </div>

        {/* Right: Node Inspector */}
        {isInspectorOpen && (
          <NodeInspector
            selectedNode={selectedNode}
            onUpdateNode={handleUpdateNodeData}
            onDeleteNode={handleDeleteNode}
            onClose={() => setIsInspectorOpen(false)}
            isReadOnly={isCanvasReadOnly}
          />
        )}
      </div>

      {/* ── 4. Validation modal ───────────────────────────────────────────── */}
      <WorkflowValidation
        open={validationOpen}
        isValid={validationResult.isValid}
        errors={validationResult.errors}
        onClose={() => setValidationOpen(false)}
      />
    </div>
  );
}
