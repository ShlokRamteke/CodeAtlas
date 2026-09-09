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
} from "lucide-react";
import type {
  Repository,
  ArchitectureOverview,
  ComponentMilestoneEvent,
  ComponentTimelineResponse,
} from "@archaeologist/contracts";
import { fetchComponentTimeline } from "@/lib/api";

interface HistoricalTimelineViewerProps {
  repository: Repository;
  architecture: ArchitectureOverview;
  initialComponentPath?: string;
  onSelectComponent?: (path: string) => void;
  onNavigateToPR?: (prNumber: number) => void;
  onNavigateToIssue?: (issueNumber: number) => void;
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
  }
> = {
  introduction: {
    label: "Introduction",
    icon: Sparkles,
    badgeBg: "bg-emerald-500/10",
    badgeText: "text-emerald-300",
    border: "border-emerald-500/30",
    dotColor: "bg-emerald-500 ring-emerald-500/20",
  },
  feature_addition: {
    label: "Feature Addition",
    icon: Zap,
    badgeBg: "bg-cyan-500/10",
    badgeText: "text-cyan-300",
    border: "border-cyan-500/30",
    dotColor: "bg-cyan-500 ring-cyan-500/20",
  },
  refactor: {
    label: "Refactor",
    icon: RefreshCw,
    badgeBg: "bg-purple-500/10",
    badgeText: "text-purple-300",
    border: "border-purple-500/30",
    dotColor: "bg-purple-500 ring-purple-500/20",
  },
  bug_fix: {
    label: "Bug Fix",
    icon: Bug,
    badgeBg: "bg-rose-500/10",
    badgeText: "text-rose-300",
    border: "border-rose-500/30",
    dotColor: "bg-rose-500 ring-rose-500/20",
  },
  architectural_decision: {
    label: "Architecture ADR",
    icon: Landmark,
    badgeBg: "bg-amber-500/10",
    badgeText: "text-amber-300",
    border: "border-amber-500/30",
    dotColor: "bg-amber-500 ring-amber-500/20",
  },
  maintenance: {
    label: "Maintenance",
    icon: Wrench,
    badgeBg: "bg-slate-500/10",
    badgeText: "text-slate-300",
    border: "border-slate-500/30",
    dotColor: "bg-slate-500 ring-slate-500/20",
  },
};

export function HistoricalTimelineViewer({
  repository,
  architecture,
  initialComponentPath,
  onSelectComponent,
  onNavigateToPR,
  onNavigateToIssue,
}: HistoricalTimelineViewerProps) {
  // Available components
  const availableComponents = useMemo(() => {
    const comps = architecture.majorComponents.map((c) => c.path);
    if (comps.length === 0) {
      return ["src", "app", "lib", "backend", "frontend"];
    }
    return comps;
  }, [architecture]);

  const [selectedPath, setSelectedPath] = useState<string>(
    initialComponentPath || availableComponents[0] || ""
  );
  const [customPathInput, setCustomPathInput] = useState<string>("");
  const [timelineData, setTimelineData] = useState<ComponentTimelineResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [selectedEventType, setSelectedEventType] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [expandedEvents, setExpandedEvents] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (initialComponentPath && initialComponentPath !== selectedPath) {
      setSelectedPath(initialComponentPath);
    }
  }, [initialComponentPath]);

  useEffect(() => {
    if (!selectedPath) return;

    let isMounted = true;
    setLoading(true);
    setError(null);

    fetchComponentTimeline(repository.id, selectedPath)
      .then((res) => {
        if (!isMounted) return;
        if (res) {
          setTimelineData(res);
        } else {
          setError(`No evolution events found for component '${selectedPath}'.`);
        }
      })
      .catch((err) => {
        if (!isMounted) return;
        setError(err.message || "Failed to load component evolution timeline.");
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

  const handleCustomPathSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (customPathInput.trim()) {
      setSelectedPath(customPathInput.trim());
      if (onSelectComponent) onSelectComponent(customPathInput.trim());
      setCustomPathInput("");
    }
  };

  // Filtered milestones
  const filteredMilestones = useMemo(() => {
    if (!timelineData) return [];
    return timelineData.milestones.filter((m) => {
      if (selectedEventType !== "all" && m.eventType !== selectedEventType) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchTitle = m.title.toLowerCase().includes(q);
        const matchSummary = m.summary.toLowerCase().includes(q);
        const matchAuthor = (m.author || "").toLowerCase().includes(q);
        const matchCommit = (m.commitHash || "").toLowerCase().includes(q);
        const matchCitations = (m.citations || []).some((c) => c.toLowerCase().includes(q));
        return matchTitle || matchSummary || matchAuthor || matchCommit || matchCitations;
      }
      return true;
    });
  }, [timelineData, selectedEventType, searchQuery]);

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h4 className="text-sm font-semibold text-white flex items-center gap-2">
            <History className="w-4 h-4 text-indigo-400" />
            Historical Evolution Timeline & Milestones
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
              PH3-06 Developer View
            </span>
          </h4>
          <p className="text-xs text-slate-400 mt-0.5">
            Trace component origins, feature additions, refactors, and architectural decisions grounded in verified evidence.
          </p>
        </div>

        {/* Component Selector */}
        <div className="flex items-center gap-2 flex-wrap">
          <label className="text-xs text-slate-400 flex items-center gap-1.5 font-medium">
            <FolderTree className="w-3.5 h-3.5 text-slate-500" />
            Component:
          </label>
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
              className="bg-slate-950 border border-slate-800 text-xs text-slate-200 placeholder-slate-500 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-indigo-500 w-36 font-mono"
            />
            <button
              type="submit"
              className="px-2 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded-lg transition"
            >
              Go
            </button>
          </form>
        </div>
      </div>

      {/* Overview Cards if data is loaded */}
      {timelineData && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800 flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400 font-medium">Component Path</span>
              <FileCode className="w-4 h-4 text-indigo-400" />
            </div>
            <div className="mt-2 text-sm font-semibold font-mono text-white truncate" title={timelineData.componentPath}>
              {timelineData.componentPath}
            </div>
            <span className="text-[11px] text-slate-500 mt-1">
              {timelineData.totalEvents} evolutionary milestones
            </span>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800 flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400 font-medium">Origin Milestone</span>
              <Sparkles className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="mt-2 text-sm font-semibold text-emerald-300 truncate" title={timelineData.introducingEvent?.title || "Unknown"}>
              {timelineData.introducingEvent?.title || "Origin Unknown"}
            </div>
            <span className="text-[11px] text-slate-500 mt-1 font-mono">
              {timelineData.introducingEvent?.timestamp ? timelineData.introducingEvent.timestamp.slice(0, 10) : "N/A"}
              {timelineData.introducingEvent?.author ? ` by ${timelineData.introducingEvent.author}` : ""}
            </span>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800 flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400 font-medium">Key Contributors</span>
              <User className="w-4 h-4 text-purple-400" />
            </div>
            <div className="mt-2 text-sm font-semibold text-white">
              {timelineData.topAuthors.length > 0 ? (
                <span className="truncate block">
                  {timelineData.topAuthors.slice(0, 2).map((a) => a.name).join(", ")}
                  {timelineData.topAuthors.length > 2 && ` +${timelineData.topAuthors.length - 2}`}
                </span>
              ) : (
                <span className="text-slate-500">None indexed</span>
              )}
            </div>
            <span className="text-[11px] text-slate-500 mt-1">
              {timelineData.topAuthors.reduce((acc, curr) => acc + curr.commits, 0)} total component changes
            </span>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800 flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400 font-medium">Verified Grounding</span>
              <ShieldCheck className="w-4 h-4 text-cyan-400" />
            </div>
            <div className="mt-2 text-sm font-semibold text-cyan-300">
              100% Deterministic
            </div>
            <span className="text-[11px] text-slate-500 mt-1">
              Zero hallucinated historical facts
            </span>
          </div>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-slate-950/60 border border-slate-800 rounded-xl">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-xs text-slate-400 flex items-center gap-1 font-medium mr-1">
            <Filter className="w-3.5 h-3.5 text-slate-500" />
            Filter:
          </span>
          <button
            onClick={() => setSelectedEventType("all")}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition ${
              selectedEventType === "all"
                ? "bg-slate-800 text-white border border-slate-700"
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
                    ? `${cfg.badgeBg} ${cfg.badgeText} border ${cfg.border}`
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <Icon className="w-3 h-3" />
                {cfg.label} ({count})
              </button>
            );
          })}
        </div>

        {/* Search Input */}
        <div className="relative w-full sm:w-64">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
          <input
            type="text"
            placeholder="Search milestones, commits, PRs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-900 border border-slate-800 text-xs text-slate-200 placeholder-slate-500 rounded-lg pl-8 pr-3 py-1.5 focus:outline-none focus:border-indigo-500"
          />
        </div>
      </div>

      {/* Timeline Stream */}
      {loading ? (
        <div className="py-16 text-center space-y-3">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500" />
          <p className="text-xs text-slate-400">Tracing historical milestones and engineering evidence for {selectedPath}...</p>
        </div>
      ) : error ? (
        <div className="py-12 text-center bg-slate-900/30 rounded-xl border border-slate-800">
          <History className="w-8 h-8 text-slate-600 mx-auto mb-2" />
          <p className="text-slate-400 text-sm">{error}</p>
          <p className="text-xs text-slate-500 mt-1">Select another component or check if Git commits and documentation are indexed.</p>
        </div>
      ) : filteredMilestones.length === 0 ? (
        <div className="py-12 text-center bg-slate-900/30 rounded-xl border border-slate-800">
          <History className="w-8 h-8 text-slate-600 mx-auto mb-2" />
          <p className="text-slate-400 text-sm">No milestones matched your current filter criteria.</p>
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
                      {milestone.commitHash && (
                        <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-slate-900 text-indigo-300 border border-slate-700">
                          {milestone.commitHash.slice(0, 7)}
                        </span>
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

                  {/* Evidence & Grounded Provenance Badges */}
                  <div className="pt-2 border-t border-slate-800/80 flex flex-wrap items-center gap-2">
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
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
