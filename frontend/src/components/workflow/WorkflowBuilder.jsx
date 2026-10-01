"use client";

import { useState, useCallback, useEffect, useRef, useMemo } from "react";
import { useRouter } from "next/navigation";
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

function EdgeInspector({ edge, isReadOnly, onConditionChange, onDelete, onClose }) {
  const source = edge.source || "Unknown";
  const target = edge.target || "Unknown";
  return (
    <aside className="w-72 shrink-0 bg-[var(--surface)] border-l border-[var(--border-subtle)] flex flex-col">
      <header className="h-12 px-4 border-b border-[var(--border-subtle)] flex items-center justify-between">
        <div>
          <div className="text-[13px] font-semibold text-[var(--text-primary)]">Connection</div>
          <div className="text-[10px] text-[var(--text-tertiary)]">{source} → {target}</div>
        </div>
        <button type="button" onClick={onClose} aria-label="Close connection inspector" className="text-[var(--text-tertiary)] hover:text-[var(--text-primary)]">×</button>
      </header>
      <div className="p-4 space-y-4">
        <label className="block">
          <span className="block text-[11px] font-semibold text-[var(--text-secondary)] mb-1 uppercase tracking-wide">Condition label</span>
          <input
            value={edge.data?.condition ?? ""}
            disabled={isReadOnly}
            onChange={(event) => onConditionChange(event.target.value)}
            placeholder="Optional, e.g. approved"
            className="w-full h-8 px-2.5 text-[12px] bg-[var(--input-bg)] text-[var(--text-primary)] rounded-[6px] border border-[var(--border-default)] focus:border-[var(--accent)] focus:outline-none disabled:opacity-60"
          />
        </label>
        {!isReadOnly && (
          <button type="button" onClick={onDelete} className="h-8 px-3 rounded-[6px] border border-red-500/30 text-red-500 hover:bg-red-500/10 text-[12px] font-medium">
            Delete connection
          </button>
        )}
      </div>
    </aside>
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
    style: { stroke: "var(--workflow-edge, #52545c)", strokeWidth: 2 },
    data: { condition: e.condition ?? null },
    label: e.condition || "",
    labelStyle: { fill: "var(--workflow-edge-label-text, #dedee4)", fontSize: 10, fontWeight: 600 },
    labelBgStyle: { fill: "var(--workflow-edge-label-bg, #18191e)", fillOpacity: 0.96 },
    labelBgPadding: [7, 4],
    labelBgBorderRadius: 5,
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
  versions = [],
  onRefresh = () => {},
  onSelectVersion = () => {},
}) {
  const router = useRouter();
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
  const [getViewportCenter, setGetViewportCenter] = useState(null);
  const [isInspectorOpen, setIsInspectorOpen] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState(null);
  const [contextMenu, setContextMenu] = useState(null);
  const [pendingNavigation, setPendingNavigation] = useState(null);
  const [undoStack, setUndoStack] = useState([]);
  const [redoStack, setRedoStack] = useState([]);
  const historyFrameRef = useRef(null);
  const historyTimerRef = useRef(null);
  const canvasStateRef = useRef({ nodes: rfNodes, edges: rfEdges });
  const allowNextPopRef = useRef(false);
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
  const selectedEdge = useMemo(
    () => (selectedEdgeId ? edges.find((edge) => edge.id === selectedEdgeId) ?? null : null),
    [edges, selectedEdgeId]
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
        const num = Number.parseInt(match[1], 10);
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

  const hasUnsavedChanges = saveState === "unsaved" || saveState === "failed";
  const navigateWithGuard = useCallback((href) => {
    if (hasUnsavedChanges) {
      setPendingNavigation(href);
      return;
    }
    router.push(href);
  }, [hasUnsavedChanges, router]);

  useEffect(() => {
    if (!hasUnsavedChanges) return;
    const handleLinkClick = (event) => {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const link = event.target.closest("a[href]");
      if (!link || link.target === "_blank" || link.hasAttribute("download")) return;
      const destination = new URL(link.href, window.location.href);
      if (destination.origin !== window.location.origin || destination.href === window.location.href) return;
      event.preventDefault();
      setPendingNavigation(`${destination.pathname}${destination.search}${destination.hash}`);
    };
    const handlePopState = () => {
      if (allowNextPopRef.current) {
        allowNextPopRef.current = false;
        return;
      }
      window.history.go(1);
      setPendingNavigation("back");
    };
    document.addEventListener("click", handleLinkClick, true);
    window.addEventListener("popstate", handlePopState);
    return () => {
      document.removeEventListener("click", handleLinkClick, true);
      window.removeEventListener("popstate", handlePopState);
    };
  }, [hasUnsavedChanges]);

  const confirmLeaveWithoutSaving = useCallback(() => {
    const destination = pendingNavigation;
    setPendingNavigation(null);
    if (!destination) return;
    if (destination === "back") {
      allowNextPopRef.current = true;
      window.history.back();
    }
    else router.push(destination);
  }, [pendingNavigation, router]);

  // ── Node selection ────────────────────────────────────────────────────────
  const handleNodeSelect = useCallback((node) => {
    setSelectedNodeId(node ? node.id : null);
    setSelectedEdgeId(null);
    if (node) setIsInspectorOpen(true);
    else setIsInspectorOpen(false);
  }, []);

  const handleEdgeSelect = useCallback((edge) => {
    setSelectedEdgeId(edge ? edge.id : null);
    setSelectedNodeId(null);
    if (edge) setIsInspectorOpen(true);
    else setIsInspectorOpen(false);
  }, []);

  const handleCanvasContextMenu = useCallback((event, target) => {
    event.preventDefault();
    if (target.type === "node") handleNodeSelect(nodes.find((node) => node.id === target.id) ?? null);
    else handleEdgeSelect(edges.find((edge) => edge.id === target.id) ?? null);
    setContextMenu({ ...target, x: event.clientX, y: event.clientY });
  }, [nodes, edges, handleNodeSelect, handleEdgeSelect]);

  // ── Mark unsaved helper ───────────────────────────────────────────────────
  const markUnsaved = useCallback(() => {
    setSaveState((prev) => (prev !== "saving" ? "unsaved" : prev));
  }, []);

  const recordHistory = useCallback(() => {
    const current = canvasStateRef.current;
    if (!historyFrameRef.current) historyFrameRef.current = current;
    if (historyTimerRef.current) clearTimeout(historyTimerRef.current);
    historyTimerRef.current = setTimeout(() => {
      const frame = historyFrameRef.current;
      if (frame) setUndoStack((stack) => [...stack.slice(-49), frame]);
      setRedoStack([]);
      historyFrameRef.current = null;
    }, 250);
  }, []);

  const applyHistorySnapshot = useCallback((snapshot) => {
    if (!snapshot) return;
    const next = { nodes: snapshot.nodes, edges: snapshot.edges };
    canvasStateRef.current = next;
    setNodes(next.nodes);
    setEdges(next.edges);
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    markUnsaved();
  }, [setNodes, setEdges, markUnsaved]);

  const handleUndo = useCallback(() => {
    if (isCanvasReadOnly) return;
    let history = undoStack;
    if (historyTimerRef.current && historyFrameRef.current) {
      clearTimeout(historyTimerRef.current);
      history = [...history, historyFrameRef.current];
      historyFrameRef.current = null;
      setUndoStack(history);
    }
    if (history.length === 0) return;
    const prior = history[history.length - 1];
    setUndoStack(history.slice(0, -1));
    setRedoStack((stack) => [...stack, canvasStateRef.current]);
    historyFrameRef.current = null;
    applyHistorySnapshot(prior);
  }, [undoStack, isCanvasReadOnly, applyHistorySnapshot]);

  const handleRedo = useCallback(() => {
    if (redoStack.length === 0 || isCanvasReadOnly) return;
    const next = redoStack[redoStack.length - 1];
    setRedoStack((stack) => stack.slice(0, -1));
    setUndoStack((stack) => [...stack, canvasStateRef.current]);
    applyHistorySnapshot(next);
  }, [redoStack, isCanvasReadOnly, applyHistorySnapshot]);

  useEffect(() => {
    canvasStateRef.current = { nodes, edges };
  }, [nodes, edges]);

  useEffect(() => () => {
    if (historyTimerRef.current) clearTimeout(historyTimerRef.current);
  }, []);

  // ── Node: drop from library ───────────────────────────────────────────────
  const handleDropNode = useCallback(
    (nodeDef, position) => {
      if (isCanvasReadOnly) return;
      recordHistory();
      const logicalId = getNextNodeId(nodeDef.typeId);
      const tempId = `temp-node-${globalThis.crypto.randomUUID()}`;
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
    [isCanvasReadOnly, markUnsaved, recordHistory]
  );

  // Quick-add via sub-bar buttons
  const handleQuickAdd = useCallback(
    (typeId) => {
      const def = getNodeDefinition(typeId);
      const position = getViewportCenter?.(248, 84) ?? { x: 0, y: 0 };
      handleDropNode(def, position);
    },
    [handleDropNode, getViewportCenter]
  );

  // ── Node: drag-stop (position update, local only) ─────────────────────────
  const handleNodeDragStop = useCallback(
    () => {
      if (isCanvasReadOnly) return;
      if (!historyFrameRef.current) historyFrameRef.current = canvasStateRef.current;
      if (historyTimerRef.current) clearTimeout(historyTimerRef.current);
      const frame = historyFrameRef.current;
      if (frame) setUndoStack((stack) => [...stack.slice(-49), frame]);
      setRedoStack([]);
      historyFrameRef.current = null;
      // Update local position already applied by RF; just mark unsaved
      markUnsaved();
    },
    [isCanvasReadOnly, markUnsaved]
  );

  const handleNodeDragStart = useCallback(() => {
    if (!isCanvasReadOnly) historyFrameRef.current = canvasStateRef.current;
  }, [isCanvasReadOnly]);

  const handleReconnect = useCallback((oldEdge, connection) => {
    if (isCanvasReadOnly) return;
    recordHistory();
    setEdges((current) => current.map((edge) => edge.id === oldEdge.id ? {
      ...edge,
      source: connection.source,
      target: connection.target,
      sourceHandle: connection.sourceHandle,
      targetHandle: connection.targetHandle,
    } : edge));
    markUnsaved();
  }, [isCanvasReadOnly, markUnsaved, setEdges, recordHistory]);

  const handleEdgeConditionChange = useCallback((value) => {
    if (isCanvasReadOnly || !selectedEdgeId) return;
    recordHistory();
    setEdges((current) => current.map((edge) => edge.id === selectedEdgeId
      ? { ...edge, data: { ...edge.data, condition: value || null }, label: value || "" }
      : edge));
    markUnsaved();
  }, [isCanvasReadOnly, selectedEdgeId, setEdges, markUnsaved, recordHistory]);

  const handleDeleteEdge = useCallback((id) => {
    if (isCanvasReadOnly) return;
    recordHistory();
    setEdges((current) => current.filter((edge) => edge.id !== id));
    setSelectedEdgeId(null);
    markUnsaved();
  }, [isCanvasReadOnly, setEdges, markUnsaved, recordHistory]);

  // ── Node: update config from inspector (local only) ───────────────────────
  const handleUpdateNodeData = useCallback(
    (id, newData) => {
      if (isCanvasReadOnly) return;
      recordHistory();
      setNodes((nds) =>
        nds.map((n) =>
          n.id === id
            ? { ...n, data: { ...n.data, ...newData } }
            : n
        )
      );
      markUnsaved();
    },
    [isCanvasReadOnly, markUnsaved, setNodes, recordHistory]
  );

  // ── Node: delete (local only) ─────────────────────────────────────────────
  const handleDeleteNode = useCallback(
    (id) => {
      if (isCanvasReadOnly) return;
      recordHistory();
      setNodes((nds) => nds.filter((n) => n.id !== id));
      setEdges((eds) => eds.filter((e) => e.source !== id && e.target !== id));
      if (selectedNodeId === id) setSelectedNodeId(null);
      if (selectedEdgeId && edges.some((edge) => edge.id === selectedEdgeId && (edge.source === id || edge.target === id))) {
        setSelectedEdgeId(null);
      }
      markUnsaved();
    },
    [isCanvasReadOnly, selectedNodeId, selectedEdgeId, edges, markUnsaved, setNodes, setEdges, recordHistory]
  );

  const handleDuplicateNode = useCallback((id) => {
    if (isCanvasReadOnly) return;
    const original = nodes.find((node) => node.id === id);
    if (!original) return;
    recordHistory();
    const typeId = original.data?.typeId || "action.http_request";
    const definition = getNodeDefinition(typeId);
    const duplicate = {
      ...original,
      id: `temp-node-${globalThis.crypto.randomUUID()}`,
      position: { x: original.position.x + 48, y: original.position.y + 48 },
      selected: false,
      data: { ...original.data, nodeId: getNextNodeId(typeId), label: `${original.data?.label || definition.name} copy` },
    };
    setNodes((current) => current.concat(duplicate));
    setSelectedNodeId(duplicate.id);
    setSelectedEdgeId(null);
    setIsInspectorOpen(true);
    setContextMenu(null);
    markUnsaved();
  }, [isCanvasReadOnly, nodes, recordHistory, setNodes, markUnsaved]);

  useEffect(() => {
    if (!contextMenu) return;
    const closeMenu = () => setContextMenu(null);
    const onMouseDown = (event) => {
      const target = event.target;
      if (target instanceof Element && !target.closest("[data-workflow-context-menu]")) {
        closeMenu();
      }
    };
    const onKeyDown = (event) => { if (event.key === "Escape") closeMenu(); };
    document.addEventListener("pointerdown", onMouseDown);
    window.addEventListener("scroll", closeMenu, true);
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onMouseDown);
      window.removeEventListener("scroll", closeMenu, true);
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [contextMenu]);

  // ── Edge: connect (local only) ────────────────────────────────────────────
  const handleConnect = useCallback(
    (connection) => {
      if (isCanvasReadOnly) return;
      recordHistory();
      const tempEdgeId = `temp-edge-${Date.now()}`;
      const newEdge = {
        ...connection,
        id: tempEdgeId,
        type: "smoothstep",
        animated: true,
        style: { stroke: "var(--workflow-edge, #52545c)", strokeWidth: 2 },
        data: { condition: null },
      };
      setEdges((eds) => addEdge(newEdge, eds));
      markUnsaved();
    },
    [isCanvasReadOnly, markUnsaved, setEdges, recordHistory]
  );

  // ── Edge: changes (local; deletes mark unsaved) ───────────────────────────
  const handleEdgesChange = useCallback(
    (changes) => {
      if (changes.some((change) => change.type === "remove")) recordHistory();
      onEdgesChange(changes);
      if (isCanvasReadOnly) return;
      const hasRemoval = changes.some((c) => c.type === "remove");
      if (hasRemoval) markUnsaved();
    },
    [onEdgesChange, isCanvasReadOnly, markUnsaved, recordHistory]
  );

  const handleNodeChanges = useCallback((changes) => {
    if (changes.some((change) => change.type === "remove")) recordHistory();
    onNodesChange(changes);
    if (isCanvasReadOnly) return;
    if (changes.some((change) => change.type === "position" && change.dragging === false)) {
      markUnsaved();
    }
  }, [onNodesChange, isCanvasReadOnly, markUnsaved, recordHistory]);

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
    const newNodes = nodesSnap.filter((n) => n.id.startsWith("temp-node-"));
    const existingNodes = nodesSnap.filter((n) => !n.id.startsWith("temp-node-"));
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
    const newEdges = edgesSnap.filter((e) => e.id.startsWith("temp-edge-"));
    const existingEdges = edgesSnap.filter((e) => !e.id.startsWith("temp-edge-"));
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
        const res = await createWorkflowNode(workflowId, versionNumber, {
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
        await updateWorkflowNode(workflowId, versionNumber, targetNodeId, {
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
        if (!se.rfId.startsWith("temp-edge-")) {
          await deleteWorkflowEdge(workflowId, versionNumber, se.rfId);
        }
        serverEdgesRef.current = serverEdgesRef.current.filter(
          (s) => s.rfId !== se.rfId
        );
      }

      // ── 4. Delete removed nodes ──────────────────────────────────────────
      for (const sn of deletedNodes) {
        await deleteWorkflowNode(workflowId, versionNumber, sn.nodeId ?? sn.rfId);
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

        const res = await createWorkflowEdge(workflowId, versionNumber, {
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
        await updateWorkflowEdge(workflowId, versionNumber, edge.id, {
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
      setUndoStack((stack) => stack.map((snapshot) => ({
        nodes: snapshot.nodes.map((node) => tempToReal[node.id] ? { ...node, id: tempToReal[node.id] } : node),
        edges: snapshot.edges.map((edge) => ({
          ...edge,
          id: tempEdgeToReal[edge.id] ?? edge.id,
          source: tempToReal[edge.source] ?? edge.source,
          target: tempToReal[edge.target] ?? edge.target,
        })),
      })));
      setRedoStack((stack) => stack.map((snapshot) => ({
        nodes: snapshot.nodes.map((node) => tempToReal[node.id] ? { ...node, id: tempToReal[node.id] } : node),
        edges: snapshot.edges.map((edge) => ({
          ...edge,
          id: tempEdgeToReal[edge.id] ?? edge.id,
          source: tempToReal[edge.source] ?? edge.source,
          target: tempToReal[edge.target] ?? edge.target,
        })),
      })));
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
      if (workflowId) {
        try {
          res = await validateWorkflow(workflowId, versionNumber);
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
  }, [saveState, handleSave, nodes, edges, workflowId, versionNumber]);

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
      if (workflowId) {
        const validation = await validateWorkflow(workflowId, versionNumber);
        if (!validation.valid) {
          setValidationResult({
            isValid: false,
            errors: validation.errors ?? [],
          });
          setValidationOpen(true);
          return;
        }
        await publishWorkflow(workflowId, versionNumber);
      }
      setCurrentVersionStatus("published");
      onRefresh();
    } catch (err) {
      console.error("Publish failed:", err);
      if (String(err?.message || "").toLowerCase().includes("validation")) {
        let errors = [{
          code: "PUBLISH_VALIDATION_FAILED",
          message: err.message || "Workflow validation failed. Review the workflow requirements and try again.",
        }];

        try {
          const validation = await validateWorkflow(workflowId, versionNumber);
          if (validation.errors?.length) errors = validation.errors;
        } catch (validationError) {
          console.warn("Could not load publish validation details:", validationError);
        }

        setValidationResult({ isValid: false, errors });
        setValidationOpen(true);
      }
    } finally {
      setIsPublishing(false);
    }
  }, [isCanvasReadOnly, saveState, handleSave, workflowId, versionNumber, onRefresh]);

  // ── Edit Workflow (create draft from published) ───────────────────────────
  const handleEditWorkflow = useCallback(async () => {
    if (!workflowId) return;
    setIsCreatingDraft(true);
    try {
      await createDraftVersion(workflowId);
      if (onRefresh) onRefresh();
    } catch (err) {
      console.error("Failed to create draft:", err);
    } finally {
      setIsCreatingDraft(false);
    }
  }, [workflowId, onRefresh]);

  // ── Keyboard shortcuts ────────────────────────────────────────────────────
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (
        ["INPUT", "TEXTAREA", "SELECT"].includes(e.target.tagName) ||
        e.target.isContentEditable
      )
        return;

      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") {
        e.preventDefault();
        if (e.shiftKey) handleRedo();
        else handleUndo();
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "y") {
        e.preventDefault();
        handleRedo();
      } else if ((e.key === "Delete" || e.key === "Backspace") && selectedEdgeId && !isCanvasReadOnly) {
        e.preventDefault();
        handleDeleteEdge(selectedEdgeId);
      } else if ((e.key === "Delete" || e.key === "Backspace") && selectedNodeId && !isCanvasReadOnly) {
        handleDeleteNode(selectedNodeId);
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        handleSave();
      } else if (e.key === "Escape") {
        setContextMenu(null);
        setSelectedNodeId(null);
        setSelectedEdgeId(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [selectedNodeId, selectedEdgeId, isCanvasReadOnly, handleDeleteNode, handleDeleteEdge, handleSave, handleUndo, handleRedo]);

  // ─────────────────────────────────────────────────────────────────────────
  // Render
  // ─────────────────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col h-full w-full bg-[var(--canvas)] select-none overflow-hidden font-sans">
      {/* ── 1. Top Toolbar ─────────────────────────────────────────────────── */}
      <WorkflowToolbar
        workflowName={workflow?.name || "Workflow"}
        workflowStatus={workflow?.status || "draft"}
        onNavigate={navigateWithGuard}
        workflowDescription={workflow?.description || ""}
        workflowId={workflowId}
        onWorkflowUpdated={onRefresh}
        onWorkflowStatusChange={(status) => onRefresh({ status })}
        onWorkflowDeleted={() => router.push("/workflows")}
        versionNumber={versionNumber}
        versions={versions}
        onSelectVersion={(nextVersion) => {
          if (saveState !== "saved") {
            setSaveError("Save or discard your changes before switching versions.");
            return;
          }
          onSelectVersion(nextVersion);
        }}
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
        canUndo={undoStack.length > 0}
        canRedo={redoStack.length > 0}
        onUndo={handleUndo}
        onRedo={handleRedo}
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
            onReconnect={handleReconnect}
            onNodeSelect={handleNodeSelect}
            onEdgeSelect={handleEdgeSelect}
            onDropNode={handleDropNode}
            onQuickAddReady={setGetViewportCenter}
            onNodeDragStop={handleNodeDragStop}
            onNodeDragStart={handleNodeDragStart}
            onContextMenu={handleCanvasContextMenu}
            isReadOnly={isCanvasReadOnly}
          />

          {contextMenu && (
            <div
              role="menu"
              tabIndex={-1}
              className="fixed z-[70] min-w-44 rounded-xl border border-[var(--border-default)] bg-[var(--surface)] p-1.5 text-[12px] text-[var(--text-primary)] shadow-2xl"
              data-workflow-context-menu
              style={{ left: Math.max(8, Math.min(contextMenu.x, window.innerWidth - 190)), top: Math.max(8, Math.min(contextMenu.y, window.innerHeight - (contextMenu.type === "node" ? 190 : 145))) }}
              onContextMenu={(event) => event.preventDefault()}
            >
              {contextMenu.type === "node" ? (
                <>
                  <button type="button" role="menuitem" onClick={() => { setIsInspectorOpen(true); setContextMenu(null); }} className="workflow-context-action">Open node inspector</button>
                  {!isCanvasReadOnly && <button type="button" role="menuitem" onClick={() => handleDuplicateNode(contextMenu.id)} className="workflow-context-action">Duplicate node</button>}
                  {!isCanvasReadOnly && <button type="button" role="menuitem" onClick={() => { handleDeleteNode(contextMenu.id); setContextMenu(null); }} className="workflow-context-action is-destructive">Delete node <span>⌫</span></button>}
                </>
              ) : (
                <>
                  <button type="button" role="menuitem" onClick={() => { setIsInspectorOpen(true); setContextMenu(null); }} className="workflow-context-action">Edit connection</button>
                  {!isCanvasReadOnly && <button type="button" role="menuitem" onClick={() => { handleDeleteEdge(contextMenu.id); setContextMenu(null); }} className="workflow-context-action is-destructive">Delete connection <span>⌫</span></button>}
                </>
              )}
            </div>
          )}
        </div>

        {/* Right: Node Inspector */}
        {isInspectorOpen && selectedEdge ? (
          <EdgeInspector
            edge={selectedEdge}
            isReadOnly={isCanvasReadOnly}
            onConditionChange={handleEdgeConditionChange}
            onDelete={() => handleDeleteEdge(selectedEdge.id)}
            onClose={() => { setIsInspectorOpen(false); setSelectedEdgeId(null); }}
          />
        ) : isInspectorOpen && (
          <NodeInspector
            selectedNode={selectedNode}
            onUpdateNode={handleUpdateNodeData}
            onDeleteNode={handleDeleteNode}
            onClose={() => setIsInspectorOpen(false)}
            isReadOnly={isCanvasReadOnly}
            workflowId={workflowId}
            workflowVersionId={version?.id}
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

      {pendingNavigation && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/55 p-4 backdrop-blur-[2px]" role="presentation">
          <div role="alertdialog" aria-modal="true" aria-labelledby="unsaved-navigation-title" aria-describedby="unsaved-navigation-description" className="w-full max-w-sm rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface)] p-5 shadow-2xl">
            <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl border border-amber-500/20 bg-amber-500/10 text-amber-500">!</div>
            <h2 id="unsaved-navigation-title" className="text-[15px] font-semibold text-[var(--text-primary)]">Leave without saving?</h2>
            <p id="unsaved-navigation-description" className="mt-1.5 text-[13px] leading-5 text-[var(--text-secondary)]">Your workflow has unsaved changes. If you leave now, those changes will be lost.</p>
            <div className="mt-5 flex justify-end gap-2 border-t border-[var(--border-subtle)] pt-3">
              <button type="button" onClick={() => setPendingNavigation(null)} className="h-9 rounded-lg border border-[var(--border-default)] px-3 text-[12px] font-medium text-[var(--text-primary)] hover:bg-[var(--elevated)]">Stay in builder</button>
              <button type="button" onClick={confirmLeaveWithoutSaving} className="h-9 rounded-lg bg-red-600 px-3 text-[12px] font-medium text-white hover:bg-red-700">Leave without saving</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
