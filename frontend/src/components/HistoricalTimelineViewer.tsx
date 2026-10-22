"use client";

import React, { useEffect, useState, useMemo } from "react";
import {
  GitCommit,
  GitPullRequest,
  CircleDot,
  History,
  Sparkles,
  Zap,
  RefreshCw,
  Bug,
  Landmark,
  Wrench,
  Search,
  Filter,
  Calendar,
  User,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  FolderTree,
  FileCode,
  ShieldCheck,
  Tag,
  ArrowRight,
  TrendingUp,
  Clock,
  Layers,
  Check,
  Copy,
  ArrowDownUp,
  SlidersHorizontal,
} from "lucide-react";
import type {
  Repository,
  ArchitectureOverview,
  ComponentMilestoneEvent,
  ComponentTimelineResponse,
} from "@codeatlas/contracts";
import { fetchComponentTimeline, fetchRepositoryTimeline } from "@/lib/api";

export interface HistoricalTimelineViewerProps {
  repository: Repository;
  architecture?: ArchitectureOverview | null;
  initialComponentPath?: string;
  onSelectComponent?: (path: string) => void;
  onNavigateToPR?: (prNumber: number) => void;
  onNavigateToIssue?: (issueNumber: number) => void;
  onInvestigateFiles?: (files: string[], rationale?: string) => void;
}

const EVENT_TYPE_CONFIG: Record<
  ComponentMilestoneEvent["eventType"],
  {
    label: string;
    icon: React.ComponentType<{ className?: string }>;
    badgeBg: string;
    badgeText: string;
    border: string;
    dotColor: string;
    barColor: string;
  }
> = {
  introduction: {
    label: "Introduction",
    icon: Sparkles,
    badgeBg: "bg-emerald-500/10",
    badgeText: "text-emerald-300",
    border: "border-emerald-500/30",
    dotColor: "bg-emerald-500 ring-emerald-500/20",
    barColor: "bg-emerald-500",
  },
  feature_addition: {
    label: "Feature Addition",
    icon: Zap,
    badgeBg: "bg-cyan-500/10",
    badgeText: "text-cyan-300",
    border: "border-cyan-500/30",
    dotColor: "bg-cyan-500 ring-cyan-500/20",
    barColor: "bg-cyan-500",
  },
  refactor: {
    label: "Refactor",
    icon: RefreshCw,
    badgeBg: "bg-purple-500/10",
    badgeText: "text-purple-300",
    border: "border-purple-500/30",
    dotColor: "bg-purple-500 ring-purple-500/20",
    barColor: "bg-purple-500",
  },
  bug_fix: {
    label: "Bug Fix",
    icon: Bug,
    badgeBg: "bg-rose-500/10",
    badgeText: "text-rose-300",
    border: "border-rose-500/30",
    dotColor: "bg-rose-500 ring-rose-500/20",
    barColor: "bg-rose-500",
  },
  architectural_decision: {
    label: "Architecture ADR",
    icon: Landmark,
    badgeBg: "bg-amber-500/10",
    badgeText: "text-amber-300",
    border: "border-amber-500/30",
    dotColor: "bg-amber-500 ring-amber-500/20",
    barColor: "bg-amber-500",
  },
  maintenance: {
    label: "Maintenance",
    icon: Wrench,
    badgeBg: "bg-slate-500/10",
    badgeText: "text-slate-300",
    border: "border-slate-500/30",
    dotColor: "bg-slate-500 ring-slate-500/20",
    barColor: "bg-slate-500",
  },
};

export function HistoricalTimelineViewer({
  repository,
  architecture,
  initialComponentPath,
  onSelectComponent,
  onNavigateToPR,
  onNavigateToIssue,
  onInvestigateFiles,
}: HistoricalTimelineViewerProps) {
  // Available major components
  const availableComponents = useMemo(() => {
    if (!architecture || !architecture.majorComponents || architecture.majorComponents.length === 0) {
      return ["src", "app", "lib", "backend", "frontend"];
    }
    return architecture.majorComponents.map((c) => c.path);
  }, [architecture]);

  // Scope: 'all' = Repository-wide; or specific component path
  const [selectedPath, setSelectedPath] = useState<string>(
    initialComponentPath && initialComponentPath !== "all" ? initialComponentPath : "all"
  );
  const [customPathInput, setCustomPathInput] = useState<string>("");
  const [timelineData, setTimelineData] = useState<ComponentTimelineResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Filters & display state
  const [selectedEventType, setSelectedEventType] = useState<string>("all");
  const [defectFixesOnly, setDefectFixesOnly] = useState<boolean>(false);
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<"desc" | "asc">("desc");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [expandedEvents, setExpandedEvents] = useState<Record<string, boolean>>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);

  useEffect(() => {
    if (initialComponentPath !== undefined && initialComponentPath !== selectedPath) {
      setSelectedPath(initialComponentPath);
    }
  }, [initialComponentPath]);

  // Load timeline data whenever selectedPath changes
  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    const isAll = !selectedPath || selectedPath === "all" || selectedPath === "*";
    const requestPromise = isAll
      ? fetchRepositoryTimeline(repository.id)
      : fetchComponentTimeline(repository.id, selectedPath);

    requestPromise
      .then((res) => {
        if (!isMounted) return;
        if (res) {
          setTimelineData(res);
        } else {
          setError(
            isAll
              ? "No evolution events found for this repository."
              : `No evolution events found for component '${selectedPath}'.`
          );
        }
      })
      .catch((err) => {
        if (!isMounted) return;
        setError(err.message || "Failed to load evolution timeline.");
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [repository.id, selectedPath]);

  const toggleExpand = (id: string) => {
    setExpandedEvents((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard?.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleCustomPathSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (customPathInput.trim()) {
      const clean = customPathInput.trim();
      setSelectedPath(clean);
      if (onSelectComponent) onSelectComponent(clean);
      setCustomPathInput("");
    }
  };

  // Filtered and sorted milestones
  const filteredMilestones = useMemo(() => {
    if (!timelineData) return [];
    let list = timelineData.milestones.filter((m) => {
      if (selectedEventType !== "all" && m.eventType !== selectedEventType) {
        return false;
      }
      if (defectFixesOnly && !m.isDefectFix && m.eventType !== "bug_fix") {
        return false;
      }
      if (selectedMonth && m.timestamp && !m.timestamp.startsWith(selectedMonth)) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchTitle = m.title.toLowerCase().includes(q);
        const matchSummary = m.summary.toLowerCase().includes(q);
        const matchAuthor = (m.author || "").toLowerCase().includes(q);
        const matchCommit = (m.commitHash || "").toLowerCase().includes(q);
        const matchCitations = (m.citations || []).some((c) => c.toLowerCase().includes(q));
        const matchFiles = (m.touchedFiles || []).some((f) => f.toLowerCase().includes(q));
        return matchTitle || matchSummary || matchAuthor || matchCommit || matchCitations || matchFiles;
      }
      return true;
    });

    list.sort((a, b) => {
      const ta = new Date(a.timestamp).getTime();
      const tb = new Date(b.timestamp).getTime();
      return sortOrder === "desc" ? tb - ta : ta - tb;
    });

    return list;
  }, [timelineData, selectedEventType, defectFixesOnly, selectedMonth, searchQuery, sortOrder]);

  const stats = timelineData?.stats;
  const isRepoWide = selectedPath === "all" || !selectedPath;

  return (
    <div className="space-y-6">
      {/* SaaS Header & Scope Control Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <History className="w-5 h-5 text-indigo-400" />
            <h4 className="text-base font-bold text-white tracking-tight">
              Historical Timeline &amp; Evolution View
            </h4>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 font-semibold">
              PH6-03 SaaS Experience
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Chronological system evolution across introductions, feature additions, refactors, bug fixes, and architectural ADRs with grounded citations.
          </p>
        </div>

        {/* Scope Selector: Repository-Wide vs Component-Scoped */}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center bg-slate-900 border border-slate-700 rounded-lg p-1 text-xs">
            <button
              onClick={() => {
                setSelectedPath("all");
                if (onSelectComponent) onSelectComponent("all");
              }}
              className={`px-3 py-1.5 rounded-md font-medium transition flex items-center gap-1.5 ${
                isRepoWide
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              All Repository
            </button>
            <button
              onClick={() => {
                const target = availableComponents[0] || "src";
                setSelectedPath(target);
                if (onSelectComponent) onSelectComponent(target);
              }}
              className={`px-3 py-1.5 rounded-md font-medium transition flex items-center gap-1.5 ${
                !isRepoWide
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              <FolderTree className="w-3.5 h-3.5" />
              By Component
            </button>
          </div>

          {!isRepoWide && (
            <div className="flex items-center gap-2">
              <select
                value={selectedPath}
                onChange={(e) => {
                  setSelectedPath(e.target.value);
                  if (onSelectComponent) onSelectComponent(e.target.value);
                }}
                className="bg-slate-900 border border-slate-700 text-xs text-white rounded-lg px-3 py-1.5 focus:outline-none focus:border-indigo-500 font-mono"
              >
                {availableComponents.map((comp) => (
                  <option key={comp} value={comp}>
                    {comp}
                  </option>
                ))}
              </select>

              {/* Custom Path Input */}
              <form onSubmit={handleCustomPathSubmit} className="flex items-center gap-1">
                <input
                  type="text"
                  placeholder="Or enter path..."
                  value={customPathInput}
                  onChange={(e) => setCustomPathInput(e.target.value)}
                  className="bg-slate-950 border border-slate-800 text-xs text-slate-200 placeholder-slate-500 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-indigo-500 w-32 font-mono"
                />
                <button
                  type="submit"
                  className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded-lg transition"
                >
                  Go
                </button>
              </form>
            </div>
          )}
        </div>
      </div>

      {/* Executive Evolution & Velocity Metrics Bar */}
      {timelineData && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {/* Total Milestones */}
          <div className="p-3.5 rounded-xl bg-slate-900/50 border border-slate-800/80 flex flex-col justify-between">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-[11px] font-medium uppercase tracking-wider">Milestones</span>
              <History className="w-4 h-4 text-indigo-400" />
            </div>
            <div className="mt-2 flex items-baseline gap-1.5">
              <span className="text-xl font-bold text-white font-mono">{timelineData.totalEvents}</span>
              <span className="text-[10px] text-slate-400">total events</span>
            </div>
            <div className="mt-1 text-[11px] text-indigo-300 font-mono">
              {timelineData.componentPath === "all" ? "Whole Codebase" : timelineData.componentPath}
            </div>
          </div>

          {/* Commits & ADRs */}
          <div className="p-3.5 rounded-xl bg-slate-900/50 border border-slate-800/80 flex flex-col justify-between">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-[11px] font-medium uppercase tracking-wider">Commits &amp; ADRs</span>
              <GitCommit className="w-4 h-4 text-amber-400" />
            </div>
            <div className="mt-2 flex items-baseline gap-1.5">
              <span className="text-xl font-bold text-amber-300 font-mono">
                {stats?.totalCommits ?? timelineData.milestones.filter((m) => m.commitHash).length}
              </span>
              <span className="text-[10px] text-slate-400">
                + {stats?.adrsCount ?? timelineData.milestones.filter((m) => m.eventType === "architectural_decision").length} ADRs
              </span>
            </div>
            <div className="mt-1 text-[11px] text-slate-400 font-mono">100% Provenance</div>
          </div>

          {/* Net Code Churn */}
          <div className="p-3.5 rounded-xl bg-slate-900/50 border border-slate-800/80 flex flex-col justify-between">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-[11px] font-medium uppercase tracking-wider">Net Churn</span>
              <TrendingUp className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="mt-2 flex items-baseline gap-1.5">
              <span className="text-xl font-bold text-emerald-300 font-mono">
                +{stats?.totalInsertions ?? 0}
              </span>
              <span className="text-xs text-rose-400 font-mono">
                -{stats?.totalDeletions ?? 0}
              </span>
            </div>
            <div className="mt-1 text-[11px] text-slate-400 font-mono">
              Δ {stats?.netChurn !== undefined ? (stats.netChurn >= 0 ? `+${stats.netChurn}` : stats.netChurn) : 0} lines
            </div>
          </div>

          {/* Defect Fixes & Repairs */}
          <div className="p-3.5 rounded-xl bg-slate-900/50 border border-slate-800/80 flex flex-col justify-between">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-[11px] font-medium uppercase tracking-wider">Defect Repairs</span>
              <Bug className="w-4 h-4 text-rose-400" />
            </div>
            <div className="mt-2 flex items-baseline gap-1.5">
              <span className="text-xl font-bold text-rose-300 font-mono">
                {stats?.defectFixesCount ?? 0}
              </span>
              <span className="text-[10px] text-slate-400">
                ({timelineData.totalEvents > 0 ? Math.round(((stats?.defectFixesCount ?? 0) / timelineData.totalEvents) * 100) : 0}%)
              </span>
            </div>
            <div className="mt-1 text-[11px] text-slate-400 font-mono">
              Bug fix frequency
            </div>
          </div>

          {/* Active Authors */}
          <div className="p-3.5 rounded-xl bg-slate-900/50 border border-slate-800/80 flex flex-col justify-between">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-[11px] font-medium uppercase tracking-wider">Authors</span>
              <User className="w-4 h-4 text-purple-400" />
            </div>
            <div className="mt-2 flex items-baseline gap-1.5">
              <span className="text-xl font-bold text-purple-300 font-mono">
                {timelineData.topAuthors.length}
              </span>
              <span className="text-[10px] text-slate-400">contributors</span>
            </div>
            <div className="mt-1 text-[11px] text-slate-400 truncate">
              {timelineData.topAuthors[0]?.name || "Unknown"}
            </div>
          </div>

          {/* Timespan */}
          <div className="p-3.5 rounded-xl bg-slate-900/50 border border-slate-800/80 flex flex-col justify-between">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-[11px] font-medium uppercase tracking-wider">Timespan</span>
              <Clock className="w-4 h-4 text-cyan-400" />
            </div>
            <div className="mt-2 flex flex-col">
              <span className="text-xs font-semibold text-white font-mono">
                {stats?.dateRange.start ? stats.dateRange.start.slice(0, 10) : "Initial"}
              </span>
              <span className="text-[10px] text-slate-500 font-mono">
                to {stats?.dateRange.end ? stats.dateRange.end.slice(0, 10) : "Latest"}
              </span>
            </div>
            <div className="mt-1 text-[11px] text-cyan-400 font-mono">Verified Timeline</div>
          </div>
        </div>
      )}

      {/* Monthly Activity Cadence / Velocity Ribbon */}
      {stats?.velocity && stats.velocity.length > 0 && (
        <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <SlidersHorizontal className="w-4 h-4 text-indigo-400" />
              <span className="text-xs font-semibold text-white">Monthly Activity Cadence &amp; Velocity</span>
              <span className="text-[10px] text-slate-500 font-mono">
                (Click month bar to filter milestones)
              </span>
            </div>
            {selectedMonth && (
              <button
                onClick={() => setSelectedMonth(null)}
                className="text-[11px] text-indigo-400 hover:text-indigo-300 font-medium transition"
              >
                Clear Month Filter ({selectedMonth}) &times;
              </button>
            )}
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-12 gap-2 pt-1">
            {stats.velocity.map((v) => {
              const isSelected = selectedMonth === v.month;
              const maxVal = Math.max(...stats.velocity.map((x) => x.totalEvents), 1);
              const heightPct = Math.max(Math.round((v.totalEvents / maxVal) * 100), 20);

              return (
                <div
                  key={v.month}
                  onClick={() => setSelectedMonth(isSelected ? null : v.month)}
                  className={`p-2 rounded-lg cursor-pointer transition flex flex-col justify-between border ${
                    isSelected
                      ? "bg-indigo-950/40 border-indigo-500/80 shadow-md ring-1 ring-indigo-500/30"
                      : "bg-slate-900/60 border-slate-800 hover:border-slate-700 hover:bg-slate-900"
                  }`}
                  title={`${v.month}: ${v.totalEvents} events (${v.features} feat, ${v.bugFixes} fix, ${v.refactors} refactor, ${v.adrs} adr)`}
                >
                  <div className="flex items-center justify-between text-[10px] font-mono text-slate-400">
                    <span className="font-semibold text-slate-300">{v.month.slice(2)}</span>
                    <span className="text-indigo-400 font-bold">{v.totalEvents}</span>
                  </div>

                  {/* Micro Visual Stack Bar */}
                  <div className="h-10 flex items-end my-1 bg-slate-950/60 rounded p-0.5 overflow-hidden">
                    <div
                      style={{ height: `${heightPct}%` }}
                      className="w-full rounded-sm flex flex-col-reverse overflow-hidden"
                    >
                      {v.features > 0 && (
                        <div
                          style={{ height: `${(v.features / v.totalEvents) * 100}%` }}
                          className="bg-cyan-500 w-full"
                        />
                      )}
                      {v.bugFixes > 0 && (
                        <div
                          style={{ height: `${(v.bugFixes / v.totalEvents) * 100}%` }}
                          className="bg-rose-500 w-full"
                        />
                      )}
                      {v.refactors > 0 && (
                        <div
                          style={{ height: `${(v.refactors / v.totalEvents) * 100}%` }}
                          className="bg-purple-500 w-full"
                        />
                      )}
                      {v.adrs > 0 && (
                        <div
                          style={{ height: `${(v.adrs / v.totalEvents) * 100}%` }}
                          className="bg-amber-500 w-full"
                        />
                      )}
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-[9px] font-mono text-slate-500">
                    <span className="text-emerald-400">+{v.insertions}</span>
                    <span className="text-rose-400">-{v.deletions}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Filter, Defect-Fix Toggle, Sort, and Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-slate-950/80 border border-slate-800 rounded-xl">
        {/* Category Filter Chips */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-xs text-slate-400 flex items-center gap-1 font-medium mr-1">
            <Filter className="w-3.5 h-3.5 text-slate-500" />
            Category:
          </span>
          <button
            onClick={() => setSelectedEventType("all")}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition ${
              selectedEventType === "all"
                ? "bg-slate-800 text-white border border-slate-700 shadow-sm"
                : "text-slate-400 hover:text-white"
            }`}
          >
            All ({timelineData?.milestones.length || 0})
          </button>
          {(Object.keys(EVENT_TYPE_CONFIG) as Array<ComponentMilestoneEvent["eventType"]>).map((type) => {
            const cfg = EVENT_TYPE_CONFIG[type];
            const count = timelineData?.milestones.filter((m) => m.eventType === type).length || 0;
            if (count === 0) return null;
            const Icon = cfg.icon;
            return (
              <button
                key={type}
                onClick={() => setSelectedEventType(type)}
                className={`px-2.5 py-1 rounded-md text-xs font-medium transition flex items-center gap-1.5 ${
                  selectedEventType === type
                    ? `${cfg.badgeBg} ${cfg.badgeText} border ${cfg.border} shadow-sm font-semibold`
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <Icon className="w-3 h-3" />
                {cfg.label} ({count})
              </button>
            );
          })}
        </div>

        {/* Right side controls: Defect Toggle, Sort, and Search */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Defect Fixes Only Toggle */}
          <button
            onClick={() => setDefectFixesOnly(!defectFixesOnly)}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition flex items-center gap-1.5 border ${
              defectFixesOnly
                ? "bg-rose-950/60 text-rose-300 border-rose-500/40"
                : "text-slate-400 hover:text-white border-slate-800"
            }`}
          >
            <Bug className="w-3 h-3 text-rose-400" />
            Defect Fixes Only
          </button>

          {/* Sort Order Toggle */}
          <button
            onClick={() => setSortOrder(sortOrder === "desc" ? "asc" : "desc")}
            className="px-2.5 py-1 rounded-md text-xs font-medium text-slate-400 hover:text-white border border-slate-800 flex items-center gap-1.5 transition"
            title={sortOrder === "desc" ? "Sorted Newest First" : "Sorted Oldest First"}
          >
            <ArrowDownUp className="w-3 h-3 text-indigo-400" />
            {sortOrder === "desc" ? "Newest First" : "Oldest First"}
          </button>

          {/* Search Input */}
          <div className="relative w-full sm:w-56">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
            <input
              type="text"
              placeholder="Search milestones, commits, files..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 text-xs text-slate-200 placeholder-slate-500 rounded-lg pl-8 pr-3 py-1.5 focus:outline-none focus:border-indigo-500 font-sans"
            />
          </div>
        </div>
      </div>

      {/* Timeline Stream */}
      {loading ? (
        <div className="py-16 text-center space-y-3">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500" />
          <p className="text-xs text-slate-400">
            Tracing historical milestones and engineering evidence for{" "}
            {isRepoWide ? "repository" : selectedPath}...
          </p>
        </div>
      ) : error ? (
        <div className="py-12 text-center bg-slate-900/30 rounded-xl border border-slate-800">
          <History className="w-8 h-8 text-slate-600 mx-auto mb-2" />
          <p className="text-slate-400 text-sm">{error}</p>
          <p className="text-xs text-slate-500 mt-1">
            Select another component or check if Git commits and documentation are indexed.
          </p>
        </div>
      ) : filteredMilestones.length === 0 ? (
        <div className="py-12 text-center bg-slate-900/30 rounded-xl border border-slate-800 space-y-3">
          <History className="w-8 h-8 text-slate-600 mx-auto" />
          <p className="text-slate-300 text-sm font-medium">No milestones matched your current filter criteria.</p>
          <div className="flex justify-center gap-2">
            <button
              onClick={() => {
                setSelectedEventType("all");
                setDefectFixesOnly(false);
                setSelectedMonth(null);
                setSearchQuery("");
              }}
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 rounded-lg transition"
            >
              Reset Filters
            </button>
          </div>
        </div>
      ) : (
        <div className="relative pl-6 sm:pl-8 border-l-2 border-slate-800 space-y-6 my-4">
          {filteredMilestones.map((milestone, idx) => {
            const cfg = EVENT_TYPE_CONFIG[milestone.eventType] || EVENT_TYPE_CONFIG.maintenance;
            const Icon = cfg.icon;
            const isExpanded = !!expandedEvents[milestone.id];

            return (
              <div key={milestone.id || idx} className="relative group">
                {/* Timeline Dot Indicator */}
                <div
                  className={`absolute -left-[31px] sm:-left-[39px] top-1.5 w-4 h-4 rounded-full ring-4 ${cfg.dotColor} flex items-center justify-center`}
                >
                  <div className="w-1.5 h-1.5 bg-white rounded-full" />
                </div>

                {/* Milestone Event Card */}
                <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800/80 hover:border-slate-700 transition space-y-3 shadow-sm">
                  {/* Header Row */}
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold ${cfg.badgeBg} ${cfg.badgeText} border ${cfg.border}`}
                        >
                          <Icon className="w-3 h-3" />
                          {cfg.label}
                        </span>

                        <span className="text-sm font-semibold text-white leading-snug">
                          {milestone.title}
                        </span>
                      </div>

                      <div className="flex items-center gap-3 text-[11px] text-slate-400 flex-wrap">
                        {milestone.author && (
                          <span className="flex items-center gap-1">
                            <User className="w-3 h-3 text-slate-500" />
                            {milestone.author}
                          </span>
                        )}
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3 text-slate-500" />
                          {milestone.timestamp.slice(0, 10)} {milestone.timestamp.slice(11, 16)}
                        </span>
                      </div>
                    </div>

                    {/* Commit Hash & Diff stats badge */}
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {milestone.commitIntent && (
                        <span
                          className={`text-[10px] uppercase font-mono px-1.5 py-0.5 rounded font-semibold border ${
                            milestone.commitIntent === "bugfix" || milestone.commitIntent === "security_patch"
                              ? "bg-rose-950/60 text-rose-300 border-rose-500/30"
                              : milestone.commitIntent === "feature"
                              ? "bg-emerald-950/60 text-emerald-300 border-emerald-500/30"
                              : milestone.commitIntent === "refactor"
                              ? "bg-amber-950/60 text-amber-300 border-amber-500/30"
                              : "bg-slate-850 text-slate-300 border-slate-700"
                          }`}
                        >
                          {milestone.commitIntent}
                        </span>
                      )}
                      {milestone.isDefectFix && (
                        <span
                          className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-red-950/70 text-red-300 border border-red-500/40 font-semibold"
                          title="Defect Repair"
                        >
                          🐞 Defect Fix
                        </span>
                      )}
                      {milestone.commitHash && (
                        <button
                          onClick={() => handleCopy(milestone.commitHash!, `commit-${milestone.id}`)}
                          className="font-mono text-[11px] px-2 py-0.5 rounded bg-slate-900 text-indigo-300 border border-slate-700 hover:border-indigo-500/50 flex items-center gap-1 transition"
                          title="Click to copy commit hash"
                        >
                          {copiedId === `commit-${milestone.id}` ? (
                            <Check className="w-3 h-3 text-emerald-400" />
                          ) : (
                            <Copy className="w-2.5 h-2.5 text-slate-500" />
                          )}
                          {milestone.commitHash.slice(0, 7)}
                        </button>
                      )}
                      {milestone.insertions !== null && milestone.insertions !== undefined && (
                        <span className="text-[10px] font-mono text-emerald-400">+{milestone.insertions}</span>
                      )}
                      {milestone.deletions !== null && milestone.deletions !== undefined && (
                        <span className="text-[10px] font-mono text-rose-400">-{milestone.deletions}</span>
                      )}
                      {milestone.filesChanged !== null && milestone.filesChanged !== undefined && (
                        <span className="text-[10px] font-mono text-slate-400">
                          {milestone.filesChanged} file{milestone.filesChanged === 1 ? "" : "s"}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Summary / Message Preview */}
                  {milestone.summary && (
                    <div className="text-xs text-slate-300 leading-relaxed font-sans">
                      {isExpanded ? (
                        <p className="whitespace-pre-wrap">{milestone.summary}</p>
                      ) : (
                        <p className="line-clamp-2">{milestone.summary.split("\n\n")[0]}</p>
                      )}
                      {milestone.summary.length > 120 && (
                        <button
                          onClick={() => toggleExpand(milestone.id)}
                          className="text-[11px] text-indigo-400 hover:text-indigo-300 flex items-center gap-1 mt-1 font-medium transition"
                        >
                          {isExpanded ? (
                            <>
                              Show less <ChevronUp className="w-3 h-3" />
                            </>
                          ) : (
                            <>
                              Show full description <ChevronDown className="w-3 h-3" />
                            </>
                          )}
                        </button>
                      )}
                    </div>
                  )}

                  {/* Touched Files Chips (if present) */}
                  {milestone.touchedFiles && milestone.touchedFiles.length > 0 && (
                    <div className="pt-2 border-t border-slate-800/60">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="text-[11px] text-slate-500 font-medium">Touched Files:</span>
                        {milestone.touchedFiles.map((file, fIdx) => (
                          <span
                            key={`f-${fIdx}`}
                            onClick={() => onInvestigateFiles && onInvestigateFiles([file], milestone.title)}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-900/80 hover:bg-indigo-950/50 hover:text-indigo-300 border border-slate-800 text-[10px] font-mono text-slate-300 transition cursor-pointer"
                            title={`Investigate changes on ${file}`}
                          >
                            <FileCode className="w-2.5 h-2.5 text-slate-500" />
                            {file}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Evidence & Grounded Provenance Badges + 1-Click Investigation */}
                  <div className="pt-2 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-[11px] text-slate-500 font-medium">Evidence:</span>

                      {/* Linked PRs */}
                      {milestone.linkedPullRequests &&
                        milestone.linkedPullRequests.map((pr, prIdx) => (
                          <span
                            key={`pr-${prIdx}`}
                            onClick={() => onNavigateToPR && onNavigateToPR(pr.pr_number)}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-purple-950/50 hover:bg-purple-900/50 text-purple-300 border border-purple-500/30 text-[11px] font-mono cursor-pointer transition"
                            title={`PR #${pr.pr_number} (${pr.link_type})`}
                          >
                            <GitPullRequest className="w-3 h-3 text-purple-400" />
                            PR #{pr.pr_number}
                          </span>
                        ))}

                      {/* Linked Issues */}
                      {milestone.linkedIssues &&
                        milestone.linkedIssues.map((iss, issIdx) => (
                          <span
                            key={`iss-${issIdx}`}
                            onClick={() => onNavigateToIssue && onNavigateToIssue(iss.issue_number)}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-emerald-950/50 hover:bg-emerald-900/50 text-emerald-300 border border-emerald-500/30 text-[11px] font-mono cursor-pointer transition"
                            title={`Issue #${iss.issue_number} (${iss.link_type})`}
                          >
                            <CircleDot className="w-3 h-3 text-emerald-400" />
                            Issue #{iss.issue_number}
                          </span>
                        ))}

                      {/* Linked ADRs */}
                      {milestone.linkedAdrs &&
                        milestone.linkedAdrs.map((adr, adrIdx) => (
                          <span
                            key={`adr-${adrIdx}`}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-amber-950/50 text-amber-300 border border-amber-500/30 text-[11px] font-mono"
                            title={`${adr.title} (${adr.status})`}
                          >
                            <Landmark className="w-3 h-3 text-amber-400" />
                            {adr.title}
                            <span className="text-[10px] px-1 py-0.2 rounded bg-amber-500/20 text-amber-200">
                              {adr.status}
                            </span>
                          </span>
                        ))}

                      {/* Citations Badges */}
                      {milestone.citations &&
                        milestone.citations.map((cite, cIdx) => (
                          <span
                            key={`cite-${cIdx}`}
                            className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800 text-[10px] font-mono"
                          >
                            <Tag className="w-2.5 h-2.5 text-slate-500" />
                            {cite}
                          </span>
                        ))}
                    </div>

                    {/* 1-Click Pre-Change Investigation Button */}
                    {onInvestigateFiles && (
                      <button
                        onClick={() => {
                          const targets =
                            milestone.touchedFiles && milestone.touchedFiles.length > 0
                              ? milestone.touchedFiles
                              : [selectedPath !== "all" ? selectedPath : "src"];
                          onInvestigateFiles(targets, `Investigate rationale based on milestone: ${milestone.title}`);
                        }}
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 text-xs font-medium transition"
                      >
                        <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                        Investigate Touched Files
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// Named alias export
export const EvolutionTimelineViewer = HistoricalTimelineViewer;
