"use client";

import { use, useState, useEffect, useCallback } from "react";
import Link from "next/link";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import DashboardShell from "@/components/dashboard/DashboardShell";
import WorkflowBuilder from "@/components/workflow/WorkflowBuilder";
import { useAuth } from "@/context/AuthContext";
import {
  getWorkflow,
  getWorkflowVersions,
  getWorkflowNodes,
  getWorkflowEdges,
} from "@/services/workflows";

function RefreshIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <path d="M21.5 2v6h-6M2.5 22v-6h6" />
      <path d="M2 11.5a10 10 0 0 1 18.8-4.3L21.5 8M22 12.5a10 10 0 0 1-18.8 4.2L2.5 16" />
    </svg>
  );
}

function AlertTriangleIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

/**
 * Normalize API list responses — backend may return:
 *   array directly, { results: [] }, { data: [] }, { nodes: [] }, etc.
 */
function normalizeList(raw, key) {
  if (Array.isArray(raw)) return raw;
  if (Array.isArray(raw?.[key])) return raw[key];
  if (Array.isArray(raw?.results)) return raw.results;
  if (Array.isArray(raw?.data)) return raw.data;
  return [];
}

/**
 * Choose best version to load for editing:
 *   - Prefer the newest draft version
 *   - Fall back to the newest published version (read-only)
 */
function selectVersion(versions, workflow) {
  if (!versions || versions.length === 0) return null;

  // Sort descending by version_number so newest is first
  const sorted = [...versions].sort(
    (a, b) => (b.version_number ?? b.version ?? 0) - (a.version_number ?? a.version ?? 0)
  );

  const draft = sorted.find((v) => v.status === "draft");
  if (draft) return draft;

  // If there is no draft, prefer the version published by the workflow record.
  const publishedId = workflow?.published_version_id;
  return sorted.find((version) => version.id === publishedId) ?? sorted[0];
}

export default function WorkflowBuilderPage({ params }) {
  const resolvedParams = use(params);
  const workflowId = resolvedParams?.workflowId ?? "";
  const { accessToken, token: legacyToken } = useAuth();
  const token = accessToken || legacyToken;

  const [workflow, setWorkflow] = useState(null);
  const [version, setVersion] = useState(null);
  const [versions, setVersions] = useState([]);
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  // Key to force full remount of WorkflowBuilder when version changes
  const [builderKey, setBuilderKey] = useState(0);

  const fetchWorkflowData = useCallback(async () => {
    if (!workflowId) {
      setError("Missing workflow ID");
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // ── 1. Fetch workflow metadata ────────────────────────────────────────
      if (!token) throw new Error("Your session has expired. Sign in and try again.");
      const rawWorkflow = await getWorkflow(token, workflowId);
      let wfData = rawWorkflow?.data ?? rawWorkflow?.workflow ?? rawWorkflow;

      if (!wfData || !wfData.id) throw new Error("Workflow was not found.");

      // ── 2. Fetch versions and select best one ─────────────────────────────
      let selectedVersion = null;
      const rawVersions = await getWorkflowVersions(token, workflowId);
      const versionsList = normalizeList(rawVersions, "versions");
      selectedVersion = selectVersion(versionsList, wfData);

      if (!selectedVersion) throw new Error("No workflow version was returned by the server.");

      // ── 3. Fetch nodes and edges for selected version ─────────────────────
      const vn = selectedVersion.version_number ?? selectedVersion.version;
      if (vn == null) throw new Error("The selected workflow version has no version number.");
      const [nodesResponse, edgesResponse] = await Promise.all([
        getWorkflowNodes(token, workflowId, vn),
        getWorkflowEdges(token, workflowId, vn),
      ]);
      const nodesData = normalizeList(nodesResponse, "nodes");
      const edgesData = normalizeList(edgesResponse, "edges");

      setWorkflow(wfData);
      setVersion(selectedVersion);
      setVersions(versionsList);
      setNodes(nodesData);
      setEdges(edgesData);
      // Force WorkflowBuilder to fully remount with fresh state
      setBuilderKey((k) => k + 1);
    } catch (err) {
      console.error("Critical workflow load error:", err);
      setError(err?.message || "Unable to load this workflow. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }, [token, workflowId]);

  const selectWorkflowVersion = useCallback(async (versionNumber) => {
    if (!token || !workflowId || Number(versionNumber) === Number(version?.version_number ?? version?.version)) return;
    setIsLoading(true);
    setError(null);
    try {
      const selectedVersion = versions.find((item) =>
        Number(item.version_number ?? item.version) === Number(versionNumber)
      );
      if (!selectedVersion) throw new Error("Workflow version was not found.");
      const [nodesResponse, edgesResponse] = await Promise.all([
        getWorkflowNodes(token, workflowId, versionNumber),
        getWorkflowEdges(token, workflowId, versionNumber),
      ]);
      setVersion(selectedVersion);
      setNodes(normalizeList(nodesResponse, "nodes"));
      setEdges(normalizeList(edgesResponse, "edges"));
      setBuilderKey((key) => key + 1);
    } catch (err) {
      setError(err?.message || "Unable to load this workflow version.");
    } finally {
      setIsLoading(false);
    }
  }, [token, workflowId, version, versions]);

  useEffect(() => {
    fetchWorkflowData();
  }, [fetchWorkflowData]);

  useEffect(() => {
    document.title = workflow?.name ? `${workflow.name} | Workflow Builder | Relay` : "Workflow Builder | Relay";
  }, [workflow?.name]);

  // ── Loading skeleton ───────────────────────────────────────────────────────
  const LoadingSkeleton = () => (
    <div className="w-full h-full flex flex-col bg-[var(--canvas)] select-none">
      <div className="h-12 px-4 bg-[var(--surface)] border-b border-[var(--border-subtle)] flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <div className="h-4 w-20 bg-[var(--elevated)] rounded animate-pulse" />
          <span className="text-[var(--text-tertiary)]">/</span>
          <div className="h-4 w-36 bg-[var(--elevated)] rounded animate-pulse" />
        </div>
        <div className="flex items-center gap-2">
          <div className="h-8 w-16 bg-[var(--elevated)] rounded animate-pulse" />
          <div className="h-8 w-20 bg-[var(--elevated)] rounded animate-pulse" />
          <div className="h-8 w-20 bg-[#4F46E5]/40 rounded animate-pulse" />
        </div>
      </div>
      <div className="flex-1 flex">
        <div className="w-60 bg-[var(--surface)] border-r border-[var(--border-subtle)] p-4 space-y-3 shrink-0">
          <div className="h-7 w-full bg-[var(--elevated)] rounded animate-pulse" />
          <div className="h-16 w-full bg-[var(--elevated)] rounded animate-pulse" />
          <div className="h-16 w-full bg-[var(--elevated)] rounded animate-pulse" />
          <div className="h-16 w-full bg-[var(--elevated)] rounded animate-pulse" />
        </div>
        <div className="flex-1 flex items-center justify-center bg-[var(--canvas)]">
          <div className="flex items-center gap-2.5 text-[var(--text-tertiary)] text-[14px]">
            <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
            <span>Loading workflow canvas...</span>
          </div>
        </div>
        <div className="w-72 bg-[var(--surface)] border-l border-[var(--border-subtle)] p-4 space-y-3 shrink-0">
          <div className="h-6 w-28 bg-[var(--elevated)] rounded animate-pulse" />
          <div className="h-24 w-full bg-[var(--elevated)] rounded animate-pulse" />
          <div className="h-12 w-full bg-[var(--elevated)] rounded animate-pulse" />
        </div>
      </div>
    </div>
  );

  // ── Error state ────────────────────────────────────────────────────────────
  const ErrorState = () => (
    <div className="w-full h-full flex flex-col items-center justify-center p-6 bg-[var(--canvas)] text-center">
      <div className="w-12 h-12 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-500 mb-4">
        <AlertTriangleIcon className="w-6 h-6 stroke-[1.5]" />
      </div>
      <h3 className="text-[18px] font-semibold text-[var(--text-primary)] tracking-tight mb-1">
        Unable to load workflow
      </h3>
      <p className="text-[14px] text-[var(--text-secondary)] max-w-sm mb-6 leading-relaxed">
        {error ?? "We encountered an issue loading this workflow."}
      </p>
      <div className="flex items-center gap-3">
        <Link
          href="/workflows"
          className="h-9 px-4 rounded-[6px] border border-[var(--border-default)] bg-[var(--surface)] hover:bg-[var(--elevated)] text-[14px] font-medium text-[var(--text-primary)] transition-colors"
        >
          Back to Workflows
        </Link>
        <button
          type="button"
          onClick={fetchWorkflowData}
          className="h-9 px-4 rounded-[6px] bg-[#4F46E5] hover:bg-[#6366F1] text-white text-[14px] font-medium transition-colors flex items-center gap-2 cursor-pointer"
        >
          <RefreshIcon className="w-4 h-4 stroke-[1.5]" />
          <span>Retry</span>
        </button>
      </div>
    </div>
  );

  return (
    <ProtectedRoute>
      <DashboardShell pageTitle={workflow?.name ?? "Workflow Builder"} fullWidth={true}>
        {isLoading ? (
          <LoadingSkeleton />
        ) : error ? (
          <ErrorState />
        ) : (
          <WorkflowBuilder
            key={builderKey}
            workflow={workflow}
            version={version}
            versions={versions}
            initialNodes={nodes}
            initialEdges={edges}
            token={token}
            onRefresh={fetchWorkflowData}
            onSelectVersion={selectWorkflowVersion}
          />
        )}
      </DashboardShell>
    </ProtectedRoute>
  );
}
