"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import DashboardShell from "@/components/dashboard/DashboardShell";
import { useAuth } from "@/context/AuthContext";
import { getWorkflows } from "@/services/workflows";

import WorkflowSkeleton from "@/components/workflows/WorkflowSkeleton";
import WorkflowEmptyState from "@/components/workflows/WorkflowEmptyState";
import WorkflowSearchEmptyState from "@/components/workflows/WorkflowSearchEmptyState";
import WorkflowErrorState from "@/components/workflows/WorkflowErrorState";
import WorkflowList from "@/components/workflows/WorkflowList";

import CreateWorkflowDialog from "@/components/workflows/CreateWorkflowDialog";

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
  const { accessToken } = useAuth();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [workflows, setWorkflows] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all"); // 'all' | 'published' | 'draft'
  const [reloadKey, setReloadKey] = useState(0);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  const handleRetry = () => {
    setLoading(true);
    setError(null);
    setReloadKey((prev) => prev + 1);
  };

  useEffect(() => {
    let isSubscribed = true;

    async function loadWorkflows() {
      try {
        const data = await getWorkflows(accessToken);
        if (!isSubscribed) return;
        const items = Array.isArray(data) ? data : data?.workflows || data?.data || [];
        setWorkflows(items);
        setError(null);
      } catch (err) {
        if (!isSubscribed) return;
        console.error("Failed to load workflows:", err);
        setError(err?.message || "Something went wrong while loading your workflows.");
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
  }, [accessToken, reloadKey]);

  // Combined status and query filtering
  const filteredWorkflows = useMemo(() => {
    return workflows.filter((wf) => {
      // Status filter
      if (statusFilter !== "all") {
        const wfStatus = String(wf.status || "draft").toLowerCase();
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

  return (
    <div className="w-full space-y-5 max-w-7xl mx-auto font-sans">
      {/* Top Header & Action */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-[var(--border-subtle)]">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-[22px] sm:text-[24px] leading-[30px] font-semibold text-[var(--text-primary)] tracking-tight">
              Workflows
            </h1>
            {!loading && !error && (
              <span className="px-2 py-0.5 text-[11px] font-mono font-medium rounded-full bg-[var(--elevated)] text-[var(--text-tertiary)] border border-[var(--border-subtle)]">
                {workflows.length}
              </span>
            )}
          </div>
          <p className="mt-0.5 text-[13px] sm:text-[14px] leading-[20px] text-[var(--text-secondary)]">
            Manage and automate your workflows.
          </p>
        </div>

        {/* Create New Workflow CTA Button */}
        <div className="flex items-center gap-2">
          {!loading && (
            <button
              type="button"
              aria-label="Refresh workflows"
              onClick={handleRetry}
              className="p-2 rounded-[6px] border border-[var(--border-default)] bg-[var(--surface)] hover:bg-[var(--elevated)] hover:border-[var(--border-strong)] text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-all duration-100 ease-out focus:outline-none focus:ring-1 focus:ring-[var(--accent)] cursor-pointer"
            >
              <RefreshCwIcon className="w-4 h-4 stroke-[1.5]" />
            </button>
          )}

          <button
            type="button"
            onClick={() => setIsCreateModalOpen(true)}
            className="inline-flex items-center justify-center gap-1.5 h-9 px-3.5 rounded-[6px] bg-[#4F46E5] hover:bg-[#6366F1] active:opacity-90 text-white font-medium text-[13px] transition-all duration-100 ease-out focus:outline-none focus:ring-2 focus:ring-[#4F46E5]/40 cursor-pointer shrink-0 shadow-none"
          >
            <PlusIcon className="w-4 h-4 stroke-[2]" />
            <span>New Workflow</span>
          </button>
        </div>
      </div>

      {/* Vercel-style Controls & Toolbar */}
      {!loading && !error && workflows.length > 0 && (
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 select-none">
          {/* Search Box */}
          <div className="relative flex-1 max-w-md">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[var(--text-tertiary)]">
              <SearchIcon className="w-3.5 h-3.5 stroke-[1.5]" />
            </div>

            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter workflows..."
              className="w-full h-8 pl-9 pr-8 text-[13px] font-sans bg-[var(--surface)] text-[var(--text-primary)] placeholder-[var(--text-disabled)] rounded-[6px] border border-[var(--border-default)] focus:border-[var(--border-strong)] focus:ring-1 focus:ring-[var(--accent)] focus:outline-none transition-colors duration-100 ease-out"
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
              { id: "published", label: "Published" },
              { id: "draft", label: "Draft" },
            ].map((tab) => {
              const isSelected = statusFilter === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setStatusFilter(tab.id)}
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
      )}

      {/* Main Content View States */}
      {loading ? (
        <WorkflowSkeleton />
      ) : error ? (
        <WorkflowErrorState
          errorMessage={error}
          onRetry={handleRetry}
        />
      ) : workflows.length === 0 ? (
        <WorkflowEmptyState onCreateNew={() => setIsCreateModalOpen(true)} />
      ) : filteredWorkflows.length === 0 ? (
        <WorkflowSearchEmptyState
          query={searchQuery}
          onClearSearch={() => {
            setSearchQuery("");
            setStatusFilter("all");
          }}
        />
      ) : (
        <WorkflowList
          workflows={filteredWorkflows}
          onDeleteSuccess={() => setReloadKey((prev) => prev + 1)}
        />
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
