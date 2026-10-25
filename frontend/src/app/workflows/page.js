"use client";

import { useState, useEffect, useMemo } from "react";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import DashboardShell from "@/components/dashboard/DashboardShell";
import Pagination from "@/components/Pagination";
import { useAuth } from "@/context/AuthContext";
import { getWorkflows } from "@/services/workflows";

import WorkflowSkeleton from "@/components/workflows/WorkflowSkeleton";
import WorkflowEmptyState from "@/components/workflows/WorkflowEmptyState";
import WorkflowSearchEmptyState from "@/components/workflows/WorkflowSearchEmptyState";
import WorkflowErrorState from "@/components/workflows/WorkflowErrorState";
import WorkflowList from "@/components/workflows/WorkflowList";

import CreateWorkflowDialog from "@/components/workflows/CreateWorkflowDialog";

const PAGE_SIZE = 12;

function PlusIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}

function SearchIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

function XIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

function RefreshCwIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <path d="M21.5 2v6h-6" />
      <path d="M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
    </svg>
  );
}

function WorkflowsContent() {
  const { isInitializing } = useAuth();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [workflows, setWorkflows] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [page, setPage] = useState(1);
  const [reloadKey, setReloadKey] = useState(0);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  useEffect(() => {
    document.title = "Workflows | Relay";
  }, []);

  const handleRetry = () => {
    setLoading(true);
    setError(null);
    setReloadKey((prev) => prev + 1);
  };

  useEffect(() => {
    let isSubscribed = true;

    async function loadWorkflows() {
      if (isInitializing) return;
      try {
        const data = await getWorkflows();
        if (!isSubscribed) return;
        const items = Array.isArray(data)
          ? data
          : data?.workflows || data?.data || [];
        setWorkflows(items);
        setError(null);
      } catch (err) {
        if (!isSubscribed) return;
        console.error("Failed to load workflows:", err);
        setError(
          err?.message || "Something went wrong while loading your workflows.",
        );
      } finally {
        if (isSubscribed) {
          setLoading(false);
        }
      }
    }

    loadWorkflows();

    return () => {
      isSubscribed = false;
    };
  }, [isInitializing, reloadKey]);

  // Combined status and query filtering
  const filteredWorkflows = useMemo(() => {
    return workflows.filter((wf) => {
      // Status filter
      if (statusFilter !== "all") {
        const rawStatus = String(wf.status || "draft").toLowerCase();
        const wfStatus = rawStatus === "published" ? "active" : rawStatus;
        if (wfStatus !== statusFilter) return false;
      }

      // Keyword search query filter
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase().trim();
        const name = (wf.name || "").toLowerCase();
        const description = (wf.description || "").toLowerCase();
        if (!name.includes(query) && !description.includes(query)) {
          return false;
        }
      }

      return true;
    });
  }, [workflows, statusFilter, searchQuery]);

  const pageCount = Math.max(
    1,
    Math.ceil(filteredWorkflows.length / PAGE_SIZE),
  );
  const paginatedWorkflows = filteredWorkflows.slice(
    (page - 1) * PAGE_SIZE,
    page * PAGE_SIZE,
  );
  useEffect(() => {
    setPage((current) => Math.min(current, pageCount));
  }, [pageCount]);

  return (
    <div className="w-full min-w-0 space-y-6 font-sans">
      <header className="flex flex-col gap-5 border-b border-[var(--border-subtle)] pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="mb-2 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[.18em] text-[var(--text-tertiary)]">
            <span
              aria-hidden="true"
              className="h-1.5 w-1.5 rounded-full bg-[var(--accent)]"
            />
            Workspace automation
          </div>
          <h1 className="text-[26px] font-semibold leading-8 tracking-tight text-[var(--text-primary)] sm:text-[30px]">
            Workflows
          </h1>
          <p className="mt-1.5 max-w-xl text-[13px] leading-5 text-[var(--text-secondary)]">
            Connect your tools and turn everyday processes into reliable
            automations.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {!loading && (
            <button
              type="button"
              aria-label="Refresh workflows"
              onClick={handleRetry}
              className="grid h-10 w-10 place-items-center rounded-lg border border-[var(--border-default)] text-[var(--text-tertiary)] transition-colors hover:bg-[var(--elevated)] hover:text-[var(--text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            >
              <RefreshCwIcon className="h-4 w-4 stroke-[1.5]" />
            </button>
          )}
          <button
            type="button"
            onClick={() => setIsCreateModalOpen(true)}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-[var(--accent)] px-4 text-[13px] font-medium text-white transition-colors hover:bg-[var(--accent-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--surface)]"
          >
            <PlusIcon className="h-4 w-4 stroke-[1.8]" />
            Create Workflow
          </button>
        </div>
      </header>

      {/* Search and status filters */}
      {!loading && !error && workflows.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-[12px] text-[var(--text-tertiary)]">
            <span className="font-mono text-[var(--text-primary)]">
              {workflows.length.toString().padStart(2, "0")}
            </span>
            {workflows.length === 1 ? "workflow" : "workflows"}
            <span
              aria-hidden="true"
              className="mx-1 h-3 w-px bg-[var(--border-default)]"
            />
            <span>Built to keep work moving</span>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            {/* Search Box */}
            <div className="relative flex-1 max-w-md">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[var(--text-tertiary)]">
                <SearchIcon className="w-3.5 h-3.5 stroke-[1.5]" />
              </div>

              <input
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setPage(1);
                }}
                aria-label="Search workflows"
                placeholder="Search by name or description..."
                className="w-full h-9 pl-9 pr-8 text-[12px] font-sans bg-[var(--surface)] text-[var(--text-primary)] placeholder-[var(--text-disabled)] rounded-[6px] border border-[var(--border-default)] focus:border-[var(--border-strong)] focus:ring-1 focus:ring-[var(--accent)] focus:outline-none transition-colors duration-100 ease-out"
              />

              {searchQuery && (
                <button
                  type="button"
                  aria-label="Clear search"
                  onClick={() => setSearchQuery("")}
                  className="absolute inset-y-0 right-0 pr-2.5 flex items-center text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
                >
                  <XIcon className="w-3.5 h-3.5 stroke-[1.5]" />
                </button>
              )}
            </div>

            {/* Status Filter Segmented Controls */}
            <div className="flex items-center p-0.5 bg-[var(--elevated)] border border-[var(--border-subtle)] rounded-[6px] shrink-0 self-start sm:self-auto">
              {[
                { id: "all", label: "All" },
                { id: "active", label: "Active" },
                { id: "inactive", label: "Inactive" },
                { id: "draft", label: "Draft" },
              ].map((tab) => {
                const isSelected = statusFilter === tab.id;
                return (
                  <button
                    key={tab.id}
                    type="button"
                    aria-pressed={isSelected}
                    onClick={() => {
                      setStatusFilter(tab.id);
                      setPage(1);
                    }}
                    className={`px-3 py-1 text-[12px] font-medium rounded-[4px] transition-all duration-100 cursor-pointer ${
                      isSelected
                        ? "bg-[var(--surface)] text-[var(--text-primary)] border border-[var(--border-subtle)] shadow-2xs"
                        : "text-[var(--text-tertiary)] hover:text-[var(--text-primary)] border border-transparent"
                    }`}
                  >
                    {tab.label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Main Content View States */}
      {loading ? (
        <WorkflowSkeleton />
      ) : error ? (
        <WorkflowErrorState errorMessage={error} onRetry={handleRetry} />
      ) : workflows.length === 0 ? (
        <WorkflowEmptyState onCreateNew={() => setIsCreateModalOpen(true)} />
      ) : filteredWorkflows.length === 0 ? (
        <WorkflowSearchEmptyState
          query={searchQuery}
          statusFilter={statusFilter}
          onClearSearch={() => {
            setSearchQuery("");
            setStatusFilter("all");
            setPage(1);
          }}
        />
      ) : (
        <div className="space-y-4">
          <WorkflowList
            workflows={paginatedWorkflows}
            onDeleteSuccess={() => setReloadKey((prev) => prev + 1)}
            onWorkflowStatusChange={(workflowId, status) => {
              setWorkflows((current) =>
                current.map((workflow) =>
                  workflow.id === workflowId
                    ? { ...workflow, status }
                    : workflow,
                ),
              );
            }}
          />
          <Pagination
            page={page}
            pageSize={PAGE_SIZE}
            total={filteredWorkflows.length}
            onPageChange={setPage}
          />
        </div>
      )}

      {/* Create Workflow Modal */}
      <CreateWorkflowDialog
        open={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={() => setReloadKey((prev) => prev + 1)}
      />
    </div>
  );
}

export default function WorkflowsPage() {
  return (
    <ProtectedRoute>
      <DashboardShell pageTitle="Workflows">
        <WorkflowsContent />
      </DashboardShell>
    </ProtectedRoute>
  );
}
