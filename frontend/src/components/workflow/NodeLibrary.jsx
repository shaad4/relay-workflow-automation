"use client";

import { useState, useMemo } from "react";
import { NODE_CATEGORIES } from "./nodeDefinitions";

function SearchIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

function ChevronDownIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

function GripIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <circle cx="9" cy="5" r="1" />
      <circle cx="9" cy="12" r="1" />
      <circle cx="9" cy="19" r="1" />
      <circle cx="15" cy="5" r="1" />
      <circle cx="15" cy="12" r="1" />
      <circle cx="15" cy="19" r="1" />
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

export default function NodeLibrary({ onAddNode, onClose }) {
  const [searchQuery, setSearchQuery] = useState("");
  const [collapsedCategories, setCollapsedCategories] = useState({});

  const toggleCategory = (catId) => {
    setCollapsedCategories((prev) => ({
      ...prev,
      [catId]: !prev[catId],
    }));
  };

  const filteredCategories = useMemo(() => {
    if (!searchQuery.trim()) return NODE_CATEGORIES;

    const query = searchQuery.toLowerCase().trim();
    return NODE_CATEGORIES.map((cat) => {
      const matchingNodes = cat.nodes.filter(
        (n) =>
          n.name.toLowerCase().includes(query) ||
          n.typeId.toLowerCase().includes(query) ||
          n.description.toLowerCase().includes(query) ||
          n.category.toLowerCase().includes(query)
      );
      return {
        ...cat,
        nodes: matchingNodes,
      };
    }).filter((cat) => cat.nodes.length > 0);
  }, [searchQuery]);

  const onDragStart = (event, nodeDef) => {
    event.dataTransfer.setData("application/reactflow", JSON.stringify(nodeDef));
    event.dataTransfer.effectAllowed = "move";
  };

  return (
    <div className="w-64 bg-[var(--surface)] border-r border-[var(--border-subtle)] flex flex-col h-full select-none shrink-0 font-sans z-20 animate-in slide-in-from-left duration-150">
      {/* Panel Header */}
      <div className="p-3 border-b border-[var(--border-subtle)] space-y-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="text-[13px] font-semibold text-[var(--text-primary)] tracking-tight">
              Node Library
            </h3>
            <span className="text-[10px] font-mono text-[var(--text-tertiary)] bg-[var(--elevated)] px-1.5 py-0.5 rounded-[4px] border border-[var(--border-subtle)]">
              Drag
            </span>
          </div>

          {onClose && (
            <button
              type="button"
              onClick={onClose}
              title="Close Node Library"
              className="p-1 rounded text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--elevated)] transition-colors cursor-pointer"
            >
              <XIcon className="w-4 h-4 stroke-[1.5]" />
            </button>
          )}
        </div>

        {/* Search Input */}
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none text-[var(--text-tertiary)]">
            <SearchIcon className="w-3.5 h-3.5 stroke-[1.5]" />
          </div>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search nodes..."
            className="w-full h-8 pl-8 pr-2.5 text-[12px] bg-[var(--input-bg)] text-[var(--text-primary)] placeholder-[var(--text-disabled)] rounded-[6px] border border-[var(--border-default)] focus:border-[var(--border-strong)] focus:ring-1 focus:ring-[var(--accent)] focus:outline-none transition-colors duration-100 ease-out"
          />
        </div>
      </div>

      {/* Category List Area */}
      <div className="flex-1 overflow-y-auto p-2 space-y-3">
        {filteredCategories.map((category) => {
          const isCollapsed = Boolean(collapsedCategories[category.id]);
          return (
            <div key={category.id} className="space-y-1">
              {/* Category Header */}
              <button
                type="button"
                onClick={() => toggleCategory(category.id)}
                className="w-full flex items-center justify-between px-2 py-1 text-[11px] font-mono tracking-wider text-[var(--text-tertiary)] uppercase hover:text-[var(--text-primary)] rounded transition-colors cursor-pointer"
              >
                <span>{category.name}</span>
                <ChevronDownIcon
                  className={`w-3.5 h-3.5 stroke-[1.5] transition-transform duration-150 ${
                    isCollapsed ? "-rotate-90" : "rotate-0"
                  }`}
                />
              </button>

              {/* Node Items */}
              {!isCollapsed && (
                <div className="space-y-1">
                  {category.nodes.map((node) => (
                    <div
                      key={node.typeId}
                      draggable
                      onDragStart={(e) => onDragStart(e, node)}
                      onClick={() => onAddNode && onAddNode(node)}
                      className="group flex items-center justify-between p-2 rounded-[6px] bg-[var(--canvas)] hover:bg-[var(--elevated)] border border-[var(--border-subtle)] hover:border-[var(--border-strong)] transition-all duration-100 ease-out cursor-grab active:cursor-grabbing"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="text-[14px] shrink-0">{node.icon}</span>
                        <div className="min-w-0">
                          <div className="text-[12px] font-medium text-[var(--text-primary)] truncate group-hover:text-[var(--accent)] transition-colors leading-tight">
                            {node.name}
                          </div>
                          <div className="text-[10px] font-mono text-[var(--text-tertiary)] truncate leading-tight">
                            {node.typeId}
                          </div>
                        </div>
                      </div>

                      <div className="text-[var(--text-disabled)] group-hover:text-[var(--text-tertiary)] shrink-0">
                        <GripIcon className="w-3.5 h-3.5 fill-current" />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
