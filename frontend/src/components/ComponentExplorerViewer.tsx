"use client";

import React, { useState, useMemo, useEffect } from "react";
import type {
  Repository,
  ArchitectureOverview,
  ComponentOverviewItem,
  ComponentDetailResponse,
  ComponentSymbolDetail,
} from "@codeatlas/contracts";
import { fetchComponentDetail } from "@/lib/api";
import {
  Boxes,
  FileCode,
  Code2,
  GitFork,
  CheckCircle2,
  AlertTriangle,
  Search,
  Filter,
  ArrowRight,
  ArrowUpRight,
  Layers,
  ExternalLink,
  ShieldCheck,
  History,
  Sparkles,
  RefreshCw,
  X,
  GitCommit,
  Eye,
  Activity,
  Check,
  Copy,
  Network,
  FolderTree,
  Target,
  FileText,
  SlidersHorizontal,
} from "lucide-react";

interface ComponentExplorerViewerProps {
  repository: Repository;
  architecture: ArchitectureOverview;
  onNavigateTab: (tab: string, target?: string) => void;
  onSelectComponentForContext?: (path: string) => void;
  onSelectComponentForTimeline?: (path: string) => void;
}

const ROLE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  service: {
    bg: "bg-blue-500/10",
    text: "text-blue-400",
    border: "border-blue-500/20",
  },
  controller: {
    bg: "bg-purple-500/10",
    text: "text-purple-400",
    border: "border-purple-500/20",
  },
  repository: {
    bg: "bg-amber-500/10",
    text: "text-amber-400",
    border: "border-amber-500/20",
  },
  entity: {
    bg: "bg-emerald-500/10",
    text: "text-emerald-400",
    border: "border-emerald-500/20",
  },
  middleware: {
    bg: "bg-rose-500/10",
    text: "text-rose-400",
    border: "border-rose-500/20",
  },
  utility: {
    bg: "bg-cyan-500/10",
    text: "text-cyan-400",
    border: "border-cyan-500/20",
  },
  general: {
    bg: "bg-slate-500/10",
    text: "text-slate-400",
    border: "border-slate-500/20",
  },
};

export function ComponentExplorerViewer({
  repository,
  architecture,
  onNavigateTab,
  onSelectComponentForContext,
  onSelectComponentForTimeline,
}: ComponentExplorerViewerProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedRole, setSelectedRole] = useState<string>("all");
  const [coverageFilter, setCoverageFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState<"symbols" | "name" | "fanIn" | "fanOut">("symbols");
  const [viewMode, setViewMode] = useState<"grid" | "topology">("grid");

  // Detail Modal State
  const [inspectingComponent, setInspectingComponent] = useState<ComponentOverviewItem | null>(null);
  const [detailData, setDetailData] = useState<ComponentDetailResponse | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [detailTab, setDetailTab] = useState<"symbols" | "dependencies" | "files">("symbols");
  const [symbolSearch, setSymbolSearch] = useState("");
  const [copiedSymbol, setCopiedSymbol] = useState<string | null>(null);

  const components = architecture.majorComponents || [];

  // Architecture High-Level Metrics
  const metrics = useMemo(() => {
    const totalComponents = components.length;
    const guardedCount = components.filter(
      (c) => c.testCoverageStatus === "guarded" || !!c.testedBy
    ).length;
    const guardedPercentage =
      totalComponents > 0 ? Math.round((guardedCount / totalComponents) * 100) : 0;

    const totalDependencies = components.reduce((acc, c) => acc + (c.dependencies?.length || 0), 0);
    const avgCoupling =
      totalComponents > 0 ? (totalDependencies / totalComponents).toFixed(1) : "0.0";

    const roleCounts: Record<string, number> = {};
    components.forEach((c) => {
      const role = c.dominantRole?.toLowerCase() || "utility";
      roleCounts[role] = (roleCounts[role] || 0) + 1;
    });

    return {
      totalComponents,
      guardedCount,
      guardedPercentage,
      totalDependencies,
      avgCoupling,
      roleCounts,
    };
  }, [components]);

  // Filtered & Sorted Components
  const filteredComponents = useMemo(() => {
    return components
      .filter((comp) => {
        // Search query
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          const matchName = comp.name.toLowerCase().includes(q);
          const matchPath = comp.path.toLowerCase().includes(q);
          const matchFiles = comp.files?.some((f) => f.toLowerCase().includes(q));
          if (!matchName && !matchPath && !matchFiles) return false;
        }

        // Role filter
        if (selectedRole !== "all") {
          const compRole = comp.dominantRole?.toLowerCase() || "utility";
          if (compRole !== selectedRole) return false;
        }

        // Coverage filter
        if (coverageFilter === "guarded") {
          const isGuarded = comp.testCoverageStatus === "guarded" || !!comp.testedBy;
          if (!isGuarded) return false;
        } else if (coverageFilter === "untested") {
          const isGuarded = comp.testCoverageStatus === "guarded" || !!comp.testedBy;
          if (isGuarded) return false;
        }

        return true;
      })
      .sort((a, b) => {
        if (sortBy === "symbols") {
          return (b.symbolCount || 0) - (a.symbolCount || 0);
        } else if (sortBy === "fanIn") {
          return (b.inboundCallers?.length || 0) - (a.inboundCallers?.length || 0);
        } else if (sortBy === "fanOut") {
          return (b.dependencies?.length || 0) - (a.dependencies?.length || 0);
        } else {
          return a.name.localeCompare(b.name);
        }
      });
  }, [components, searchQuery, selectedRole, coverageFilter, sortBy]);

  // Fetch component detail when inspecting
  useEffect(() => {
    if (!inspectingComponent) {
      setDetailData(null);
      return;
    }

    let active = true;
    setLoadingDetail(true);
    fetchComponentDetail(repository.id, inspectingComponent.path)
      .then((res) => {
        if (active) {
          setDetailData(res);
          setLoadingDetail(false);
        }
      })
      .catch(() => {
        if (active) setLoadingDetail(false);
      });

    return () => {
      active = false;
    };
  }, [inspectingComponent, repository.id]);

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedSymbol(id);
    setTimeout(() => setCopiedSymbol(null), 1500);
  };

  const getRoleStyle = (role?: string | null) => {
    const key = (role || "").toLowerCase();
    return ROLE_COLORS[key] || ROLE_COLORS.general;
  };

  return (
    <div className="space-y-6">
      {/* 1. Architecture Metrics Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Total Components</span>
            <Boxes className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-1">{metrics.totalComponents}</div>
          <div className="text-[11px] text-slate-500 mt-0.5">
            across {architecture.fileCount} files
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Guarded Components</span>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-1">
            {metrics.guardedPercentage}%
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">
            {metrics.guardedCount} of {metrics.totalComponents} covered by tests
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Coupling Density</span>
            <GitFork className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-1">{metrics.avgCoupling}</div>
          <div className="text-[11px] text-slate-500 mt-0.5">
            avg external dependencies / component
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Architectural Roles</span>
            <Layers className="w-4 h-4 text-purple-400" />
          </div>
          <div className="flex items-center gap-1.5 flex-wrap mt-2">
            {Object.entries(metrics.roleCounts).slice(0, 3).map(([role, count]) => {
              const style = getRoleStyle(role);
              return (
                <span
                  key={role}
                  className={`text-[10px] px-1.5 py-0.5 rounded border capitalize ${style.bg} ${style.text} ${style.border} font-medium`}
                >
                  {role}: {count}
                </span>
              );
            })}
          </div>
        </div>
      </div>

      {/* 2. Controls & Filter Bar */}
      <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
        <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
          {/* Search Box */}
          <div className="relative flex-1 min-w-[240px]">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search components, file paths, or symbols..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 transition"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-2.5 top-2.5 text-slate-400 hover:text-white"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* View Mode Toggle */}
          <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800 self-start md:self-auto">
            <button
              onClick={() => setViewMode("grid")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition ${
                viewMode === "grid"
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              <Boxes className="w-3.5 h-3.5" />
              Directory Grid
            </button>
            <button
              onClick={() => setViewMode("topology")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition ${
                viewMode === "topology"
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              <Network className="w-3.5 h-3.5" />
              Coupling Topology
            </button>
          </div>
        </div>

        {/* Filter Chips & Sorting */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-800/60 text-xs">
          {/* Role Filters */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-slate-500 text-[11px] font-medium mr-1">Role:</span>
            {["all", "service", "controller", "repository", "entity", "middleware", "utility"].map(
              (role) => (
                <button
                  key={role}
                  onClick={() => setSelectedRole(role)}
                  className={`px-2 py-0.5 rounded text-[11px] capitalize font-medium transition ${
                    selectedRole === role
                      ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/40"
                      : "bg-slate-950 text-slate-400 border border-slate-800 hover:text-white"
                  }`}
                >
                  {role}
                </button>
              )
            )}
          </div>

          {/* Test Coverage & Sorting Dropdowns */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span className="text-slate-500 text-[11px]">Testing:</span>
              <select
                value={coverageFilter}
                onChange={(e) => setCoverageFilter(e.target.value)}
                className="bg-slate-950 border border-slate-800 text-slate-300 text-[11px] rounded px-2 py-1 focus:outline-none focus:border-indigo-500"
              >
                <option value="all">All Coverage</option>
                <option value="guarded">Guarded by Tests</option>
                <option value="untested">Untested / Gap</option>
              </select>
            </div>

            <div className="flex items-center gap-1.5">
              <span className="text-slate-500 text-[11px]">Sort:</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="bg-slate-950 border border-slate-800 text-slate-300 text-[11px] rounded px-2 py-1 focus:outline-none focus:border-indigo-500"
              >
                <option value="symbols">Symbols (High to Low)</option>
                <option value="fanIn">Inbound Callers (Fan-in)</option>
                <option value="fanOut">Dependencies (Fan-out)</option>
                <option value="name">Component Name</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* 3. Main View: Grid vs Topology */}
      {filteredComponents.length === 0 ? (
        <div className="py-16 text-center bg-slate-900/30 border border-slate-800 rounded-xl">
          <FolderTree className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <p className="text-white font-medium text-sm">No matching components found.</p>
          <p className="text-slate-500 text-xs mt-1">
            Try adjusting your search query, role filter, or test coverage setting.
          </p>
        </div>
      ) : viewMode === "grid" ? (
        /* Component Cards Grid */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredComponents.map((comp) => {
            const roleStyle = getRoleStyle(comp.dominantRole);
            const isGuarded = comp.testCoverageStatus === "guarded" || !!comp.testedBy;
            const fanIn = comp.inboundCallers?.length || 0;
            const fanOut = comp.dependencies?.length || 0;

            return (
              <div
                key={comp.path}
                className="p-4 rounded-xl bg-slate-950/70 border border-slate-800/90 hover:border-slate-700 transition flex flex-col justify-between space-y-3 group shadow-sm hover:shadow-md"
              >
                <div>
                  {/* Card Header */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="text-sm font-semibold text-white flex items-center gap-2 truncate group-hover:text-indigo-300 transition">
                        <FileCode className="w-4 h-4 text-indigo-400 flex-shrink-0" />
                        <span className="truncate">{comp.name}</span>
                      </div>
                      <div className="text-[11px] font-mono text-slate-400 truncate mt-0.5">
                        {comp.path}
                      </div>
                    </div>

                    {/* Dominant Role Badge */}
                    {comp.dominantRole && (
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded border capitalize font-medium flex-shrink-0 ${roleStyle.bg} ${roleStyle.text} ${roleStyle.border}`}
                      >
                        {comp.dominantRole}
                      </span>
                    )}
                  </div>

                  {/* Metrics Badges */}
                  <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-slate-800/60 text-center">
                    <div className="p-1.5 rounded bg-slate-900/80 border border-slate-800/50">
                      <div className="text-xs font-bold text-white">{comp.symbolCount}</div>
                      <div className="text-[10px] text-slate-500">Symbols</div>
                    </div>
                    <div className="p-1.5 rounded bg-slate-900/80 border border-slate-800/50">
                      <div className="text-xs font-bold text-cyan-400">{fanIn}</div>
                      <div className="text-[10px] text-slate-500">Callers (In)</div>
                    </div>
                    <div className="p-1.5 rounded bg-slate-900/80 border border-slate-800/50">
                      <div className="text-xs font-bold text-purple-400">{fanOut}</div>
                      <div className="text-[10px] text-slate-500">Imports (Out)</div>
                    </div>
                  </div>

                  {/* Test Protection Status */}
                  <div className="mt-3 text-xs flex items-center justify-between">
                    <span className="text-slate-500 text-[11px]">Test Protection:</span>
                    {isGuarded ? (
                      <span className="text-emerald-400 flex items-center gap-1 font-mono text-[11px]">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        {comp.testedBy ? comp.testedBy.split("/").pop() : "Guarded"}
                      </span>
                    ) : (
                      <span className="text-amber-400/90 flex items-center gap-1 text-[11px]">
                        <AlertTriangle className="w-3.5 h-3.5" />
                        Verification Gap
                      </span>
                    )}
                  </div>

                  {/* Contained Files Preview */}
                  {comp.files && comp.files.length > 0 && (
                    <div className="mt-2.5 text-xs flex items-center gap-1 flex-wrap">
                      <span className="text-slate-500 text-[10px]">Files:</span>
                      {comp.files.slice(0, 2).map((f) => (
                        <span
                          key={f}
                          className="px-1.5 py-0.2 rounded bg-slate-900 text-slate-400 font-mono text-[10px] truncate max-w-[130px]"
                        >
                          {f.split("/").pop()}
                        </span>
                      ))}
                      {comp.files.length > 2 && (
                        <span className="text-slate-500 text-[10px]">
                          +{comp.files.length - 2} more
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {/* Card Actions Footer */}
                <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setInspectingComponent(comp)}
                      className="inline-flex items-center gap-1 text-slate-300 hover:text-white font-medium hover:bg-slate-800/60 px-2 py-1 rounded transition"
                      title="Inspect AST symbols and dependencies"
                    >
                      <Eye className="w-3.5 h-3.5 text-indigo-400" />
                      Inspect
                    </button>
                    <button
                      onClick={() => {
                        if (onSelectComponentForTimeline) onSelectComponentForTimeline(comp.path);
                        onNavigateTab("git_history", comp.path);
                      }}
                      className="inline-flex items-center gap-1 text-slate-400 hover:text-slate-200 px-2 py-1 rounded transition"
                      title="View component historical timeline"
                    >
                      <History className="w-3.5 h-3.5" />
                      Timeline
                    </button>
                  </div>

                  {/* 1-Click Investigate Button */}
                  <button
                    onClick={() => onNavigateTab("investigation", comp.path)}
                    className="inline-flex items-center gap-1 text-[11px] text-indigo-400 hover:text-indigo-300 font-medium bg-indigo-500/10 hover:bg-indigo-500/20 px-2 py-1 rounded border border-indigo-500/20 transition"
                    title="Investigate proposed changes on this component"
                  >
                    <Target className="w-3.5 h-3.5" />
                    Investigate &rarr;
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* Topology / Coupling Matrix View */
        <div className="p-5 rounded-xl bg-slate-950/70 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Network className="w-4 h-4 text-indigo-400" />
                Component Coupling &amp; Dependency Topology
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Evaluates fan-in (inbound callers) and fan-out (outbound dependencies) across
                component boundaries.
              </p>
            </div>
            <span className="text-xs text-slate-500">
              {filteredComponents.length} components shown
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 font-medium">
                  <th className="py-2.5 px-3">Component</th>
                  <th className="py-2.5 px-3">Role</th>
                  <th className="py-2.5 px-3 text-center">Symbols</th>
                  <th className="py-2.5 px-3">Inbound Callers (Fan-in)</th>
                  <th className="py-2.5 px-3">Outbound Imports (Fan-out)</th>
                  <th className="py-2.5 px-3">Protection</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredComponents.map((comp) => {
                  const roleStyle = getRoleStyle(comp.dominantRole);
                  const isGuarded = comp.testCoverageStatus === "guarded" || !!comp.testedBy;

                  return (
                    <tr key={comp.path} className="hover:bg-slate-900/50 transition">
                      <td className="py-2.5 px-3">
                        <div className="font-semibold text-white">{comp.name}</div>
                        <div className="font-mono text-[10px] text-slate-500">{comp.path}</div>
                      </td>
                      <td className="py-2.5 px-3">
                        {comp.dominantRole && (
                          <span
                            className={`text-[10px] px-2 py-0.5 rounded border capitalize font-medium ${roleStyle.bg} ${roleStyle.text} ${roleStyle.border}`}
                          >
                            {comp.dominantRole}
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-center font-bold text-slate-200">
                        {comp.symbolCount}
                      </td>
                      <td className="py-2.5 px-3">
                        {comp.inboundCallers && comp.inboundCallers.length > 0 ? (
                          <div className="flex items-center gap-1 flex-wrap max-w-[220px]">
                            {comp.inboundCallers.map((c) => (
                              <span
                                key={c}
                                className="px-1.5 py-0.2 rounded bg-slate-900 text-cyan-300 font-mono text-[10px] border border-cyan-500/20"
                              >
                                {c}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span className="text-slate-600 italic text-[11px]">No inbound callers</span>
                        )}
                      </td>
                      <td className="py-2.5 px-3">
                        {comp.dependencies && comp.dependencies.length > 0 ? (
                          <div className="flex items-center gap-1 flex-wrap max-w-[220px]">
                            {comp.dependencies.slice(0, 3).map((dep) => (
                              <span
                                key={dep}
                                className="px-1.5 py-0.2 rounded bg-slate-900 text-purple-300 font-mono text-[10px] border border-purple-500/20 truncate max-w-[120px]"
                              >
                                {dep.split("/").pop()}
                              </span>
                            ))}
                            {comp.dependencies.length > 3 && (
                              <span className="text-slate-500 text-[10px]">
                                +{comp.dependencies.length - 3}
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-600 italic text-[11px]">Leaf component</span>
                        )}
                      </td>
                      <td className="py-2.5 px-3">
                        {isGuarded ? (
                          <span className="inline-flex items-center gap-1 text-emerald-400 font-medium text-[11px]">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            Guarded
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-amber-400/90 text-[11px]">
                            <AlertTriangle className="w-3.5 h-3.5" />
                            Gap
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => setInspectingComponent(comp)}
                            className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition"
                            title="Inspect details"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => onNavigateTab("investigation", comp.path)}
                            className="p-1 rounded bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 border border-indigo-500/30 transition"
                            title="Investigate change"
                          >
                            <Target className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 4. Interactive Component Detail Modal */}
      {inspectingComponent && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-950 border border-slate-800 rounded-2xl w-full max-w-4xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="p-5 border-b border-slate-800 flex items-start justify-between bg-slate-900/60">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <FileCode className="w-5 h-5 text-indigo-400" />
                  <h2 className="text-base font-bold text-white">{inspectingComponent.name}</h2>
                  {inspectingComponent.dominantRole && (
                    <span
                      className={`text-xs px-2 py-0.5 rounded border capitalize font-medium ${getRoleStyle(
                        inspectingComponent.dominantRole
                      ).bg} ${getRoleStyle(inspectingComponent.dominantRole).text} ${
                        getRoleStyle(inspectingComponent.dominantRole).border
                      }`}
                    >
                      {inspectingComponent.dominantRole}
                    </span>
                  )}
                  {inspectingComponent.testCoverageStatus === "guarded" ? (
                    <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" />
                      Guarded
                    </span>
                  ) : (
                    <span className="text-xs px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 font-medium flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3" />
                      Untested
                    </span>
                  )}
                </div>
                <div className="text-xs font-mono text-slate-400">{inspectingComponent.path}</div>
              </div>
              <button
                onClick={() => setInspectingComponent(null)}
                className="p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Tabs Bar */}
            <div className="px-5 pt-3 border-b border-slate-800/80 flex items-center gap-4 text-xs font-medium bg-slate-950">
              <button
                onClick={() => setDetailTab("symbols")}
                className={`pb-2 border-b-2 flex items-center gap-1.5 transition ${
                  detailTab === "symbols"
                    ? "border-indigo-500 text-indigo-400"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                <Code2 className="w-3.5 h-3.5" />
                AST Symbols ({detailData?.symbols.length || inspectingComponent.symbolCount})
              </button>
              <button
                onClick={() => setDetailTab("dependencies")}
                className={`pb-2 border-b-2 flex items-center gap-1.5 transition ${
                  detailTab === "dependencies"
                    ? "border-indigo-500 text-indigo-400"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                <GitFork className="w-3.5 h-3.5" />
                Callers &amp; Dependencies
              </button>
              <button
                onClick={() => setDetailTab("files")}
                className={`pb-2 border-b-2 flex items-center gap-1.5 transition ${
                  detailTab === "files"
                    ? "border-indigo-500 text-indigo-400"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                <FileText className="w-3.5 h-3.5" />
                Contained Files ({detailData?.files.length || inspectingComponent.files?.length || 0})
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              {loadingDetail ? (
                <div className="py-16 text-center flex flex-col items-center justify-center space-y-3">
                  <RefreshCw className="w-7 h-7 text-indigo-400 animate-spin" />
                  <p className="text-xs text-slate-400">Loading structured component intelligence...</p>
                </div>
              ) : detailTab === "symbols" ? (
                /* Tab 1: AST Symbols */
                <div className="space-y-3">
                  {/* Symbol Search */}
                  <div className="relative">
                    <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
                    <input
                      type="text"
                      placeholder="Filter symbols in this component..."
                      value={symbolSearch}
                      onChange={(e) => setSymbolSearch(e.target.value)}
                      className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-indigo-500"
                    />
                  </div>

                  <div className="space-y-2">
                    {detailData?.symbols
                      ?.filter((sym) =>
                        symbolSearch.trim()
                          ? sym.name.toLowerCase().includes(symbolSearch.toLowerCase()) ||
                            sym.kind.toLowerCase().includes(symbolSearch.toLowerCase())
                          : true
                      )
                      .map((sym) => {
                        const symRoleStyle = getRoleStyle(sym.architecturalRole);

                        return (
                          <div
                            key={sym.id}
                            className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition space-y-1.5"
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <span className="font-mono text-xs font-semibold text-white">
                                  {sym.name}
                                </span>
                                <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 uppercase font-mono">
                                  {sym.kind}
                                </span>
                                {sym.architecturalRole && (
                                  <span
                                    className={`text-[10px] px-1.5 py-0.2 rounded border capitalize ${symRoleStyle.bg} ${symRoleStyle.text} ${symRoleStyle.border}`}
                                  >
                                    {sym.architecturalRole}
                                  </span>
                                )}
                              </div>
                              <div className="flex items-center gap-2 text-xs text-slate-500 font-mono">
                                <span>
                                  L{sym.lineStart}-{sym.lineEnd}
                                </span>
                                <button
                                  onClick={() => handleCopy(sym.name, sym.id)}
                                  className="text-slate-400 hover:text-white"
                                  title="Copy symbol name"
                                >
                                  {copiedSymbol === sym.id ? (
                                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                                  ) : (
                                    <Copy className="w-3.5 h-3.5" />
                                  )}
                                </button>
                              </div>
                            </div>

                            {sym.signature && (
                              <div className="text-[11px] font-mono text-slate-400 bg-slate-950 p-2 rounded border border-slate-900 truncate">
                                {sym.signature}
                              </div>
                            )}

                            {sym.filePath && (
                              <div className="text-[10px] text-slate-500 font-mono">
                                file: {sym.filePath}
                              </div>
                            )}
                          </div>
                        );
                      })}
                  </div>
                </div>
              ) : detailTab === "dependencies" ? (
                /* Tab 2: Callers & Dependencies */
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Inbound Callers */}
                  <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800 space-y-3">
                    <h4 className="text-xs font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-1.5">
                      <ArrowRight className="w-3.5 h-3.5" />
                      Inbound Callers (Fan-in: {detailData?.inboundCallers.length || 0})
                    </h4>
                    {detailData?.inboundCallers && detailData.inboundCallers.length > 0 ? (
                      <div className="space-y-1.5">
                        {detailData.inboundCallers.map((caller) => (
                          <div
                            key={caller}
                            className="p-2 rounded bg-slate-950 border border-slate-800/80 text-xs font-mono text-cyan-300 flex items-center justify-between"
                          >
                            <span>{caller}</span>
                            <span className="text-[10px] text-slate-500">imports this</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-slate-500 italic">
                        No external components directly import this component.
                      </p>
                    )}
                  </div>

                  {/* Outbound Dependencies */}
                  <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800 space-y-3">
                    <h4 className="text-xs font-bold text-purple-400 uppercase tracking-wider flex items-center gap-1.5">
                      <ArrowUpRight className="w-3.5 h-3.5" />
                      Outbound Dependencies (Fan-out: {detailData?.dependencies.length || 0})
                    </h4>
                    {detailData?.dependencies && detailData.dependencies.length > 0 ? (
                      <div className="space-y-1.5">
                        {detailData.dependencies.map((dep) => (
                          <div
                            key={dep}
                            className="p-2 rounded bg-slate-950 border border-slate-800/80 text-xs font-mono text-purple-300 flex items-center justify-between"
                          >
                            <span className="truncate">{dep}</span>
                            <span className="text-[10px] text-slate-500 flex-shrink-0">imported</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-slate-500 italic">
                        Leaf component — imports no external components.
                      </p>
                    )}
                  </div>
                </div>
              ) : (
                /* Tab 3: Contained Files */
                <div className="space-y-2">
                  {detailData?.files.map((file) => (
                    <div
                      key={file}
                      className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center justify-between text-xs"
                    >
                      <div className="flex items-center gap-2">
                        <FileCode className="w-4 h-4 text-indigo-400" />
                        <span className="font-mono text-slate-200">{file}</span>
                      </div>
                      <button
                        onClick={() => onNavigateTab("investigation", file)}
                        className="text-[11px] text-indigo-400 hover:text-indigo-300 font-medium"
                      >
                        Investigate file &rarr;
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Modal Actions Footer */}
            <div className="p-4 border-t border-slate-800 bg-slate-900/60 flex items-center justify-between">
              <div className="flex items-center gap-3 text-xs text-slate-400">
                {detailData?.originCommit && (
                  <span className="font-mono text-[11px] flex items-center gap-1">
                    <GitCommit className="w-3 h-3 text-indigo-400" />
                    origin: {detailData.originCommit.slice(0, 7)}
                  </span>
                )}
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={() => {
                    const target = inspectingComponent.path;
                    setInspectingComponent(null);
                    if (onSelectComponentForTimeline) onSelectComponentForTimeline(target);
                    onNavigateTab("git_history", target);
                  }}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition flex items-center gap-1.5"
                >
                  <History className="w-3.5 h-3.5" />
                  View Timeline
                </button>

                <button
                  onClick={() => {
                    const target = inspectingComponent.path;
                    setInspectingComponent(null);
                    onNavigateTab("investigation", target);
                  }}
                  className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition flex items-center gap-1.5 shadow-sm"
                >
                  <Target className="w-3.5 h-3.5" />
                  Investigate Change on Component &rarr;
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
