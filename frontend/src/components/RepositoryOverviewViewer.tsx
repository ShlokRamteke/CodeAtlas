"use client";

import React, { useEffect, useState } from "react";
import type { Repository, RepositoryOverviewResponse } from "@codeatlas/contracts";
import { fetchRepositoryOverview } from "@/lib/api";
import {
  ShieldCheck,
  AlertTriangle,
  AlertCircle,
  CheckCircle2,
  Activity,
  Flame,
  Users,
  Boxes,
  FileCode,
  GitCommit,
  GitPullRequest,
  BookOpen,
  ArrowRight,
  Sparkles,
  Layers,
  RefreshCw,
  GitFork,
  Target,
  CircleDot,
  Clock,
  Compass,
} from "lucide-react";

interface RepositoryOverviewViewerProps {
  repository: Repository;
  onNavigateTab: (tab: string, targetFile?: string) => void;
}

export function RepositoryOverviewViewer({
  repository,
  onNavigateTab,
}: RepositoryOverviewViewerProps) {
  const [data, setData] = useState<RepositoryOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadOverview() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchRepositoryOverview(repository.id);
      if (res) {
        setData(res);
      } else {
        setError("Failed to load repository overview.");
      }
    } catch (err: any) {
      setError(err?.message || "Error fetching repository overview.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadOverview();
  }, [repository.id]);

  if (loading) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-12 text-center flex flex-col items-center justify-center space-y-4">
        <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin" />
        <div className="space-y-1">
          <p className="text-white font-medium text-sm">Computing Repository Health & Overview...</p>
          <p className="text-xs text-slate-400">
            Synthesizing test reachability, bus factor, defect pressure, and architectural coupling.
          </p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-8 text-center space-y-4">
        <AlertCircle className="w-10 h-10 text-amber-400 mx-auto" />
        <p className="text-slate-300 text-sm">{error || "No overview data available."}</p>
        <button
          onClick={loadOverview}
          className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition"
        >
          Try Again
        </button>
      </div>
    );
  }

  const { health } = data;
  const compositeScore = Math.round(health.composite_score ?? 0);

  // Status badges & styling
  const getStatusBadge = (status: string) => {
    switch (status) {
      case "healthy":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold">
            <CheckCircle2 className="w-3.5 h-3.5" /> Healthy
          </span>
        );
      case "stable":
      case "warning":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs font-semibold">
            <AlertTriangle className="w-3.5 h-3.5" /> Stable / Moderate Attention
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-semibold">
            <AlertCircle className="w-3.5 h-3.5" /> Attention Needed
          </span>
        );
    }
  };

  const getMetricIcon = (category: string) => {
    switch (category) {
      case "testing":
        return <ShieldCheck className="w-4 h-4 text-emerald-400" />;
      case "ownership":
        return <Users className="w-4 h-4 text-purple-400" />;
      case "stability":
        return <Activity className="w-4 h-4 text-blue-400" />;
      case "architecture":
        return <Boxes className="w-4 h-4 text-cyan-400" />;
      case "governance":
        return <BookOpen className="w-4 h-4 text-amber-400" />;
      case "concurrency":
        return <GitFork className="w-4 h-4 text-rose-400" />;
      default:
        return <Activity className="w-4 h-4 text-indigo-400" />;
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 75) return "text-emerald-400";
    if (score >= 50) return "text-amber-400";
    return "text-red-400";
  };

  const getScoreProgressBg = (score: number) => {
    if (score >= 75) return "bg-emerald-500";
    if (score >= 50) return "bg-amber-500";
    return "bg-red-500";
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* 1. Executive Summary & Health Gauge Header */}
      <div className="bg-gradient-to-br from-slate-900/90 via-slate-900/60 to-slate-950 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500/5 rounded-full blur-3xl -z-10 pointer-events-none" />

        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-3 max-w-2xl">
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-xs uppercase tracking-wider font-semibold text-indigo-400 flex items-center gap-1.5">
                <Compass className="w-3.5 h-3.5" /> Repository Overview &amp; Health
              </span>
              {getStatusBadge(health.status)}
            </div>

            <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              {data.full_name}
            </h2>

            <p className="text-slate-300 text-sm leading-relaxed">{health.summary}</p>

            {/* Vital Statistics Pills */}
            <div className="flex flex-wrap items-center gap-2 pt-2 text-xs">
              <span className="px-2.5 py-1 rounded-md bg-slate-800/80 border border-slate-700/60 text-slate-300 font-mono">
                {data.file_count} files
              </span>
              <span className="px-2.5 py-1 rounded-md bg-slate-800/80 border border-slate-700/60 text-slate-300 font-mono">
                {data.symbol_count} AST symbols
              </span>
              <span className="px-2.5 py-1 rounded-md bg-slate-800/80 border border-slate-700/60 text-slate-300 font-mono">
                {data.dependency_count} dependencies
              </span>
              <span className="px-2.5 py-1 rounded-md bg-slate-800/80 border border-slate-700/60 text-slate-300 font-mono">
                {data.commit_count} commits
              </span>
              <span className="px-2.5 py-1 rounded-md bg-slate-800/80 border border-slate-700/60 text-slate-300 font-mono">
                {data.adr_count} ADRs &bull; {data.constraint_count} constraints
              </span>
            </div>
          </div>

          {/* Health Score Meter & Quick Action */}
          <div className="flex flex-col sm:flex-row items-center gap-6 lg:border-l lg:border-slate-800 lg:pl-8">
            <div className="text-center sm:text-right space-y-1">
              <div className="flex items-baseline justify-center sm:justify-end gap-1">
                <span className={`text-5xl font-black tracking-tight ${getScoreColor(compositeScore)}`}>
                  {compositeScore}
                </span>
                <span className="text-slate-500 font-medium text-lg">/100</span>
              </div>
              <p className="text-xs text-slate-400 font-medium">Composite Health Score</p>
            </div>

            <div className="flex flex-col gap-2 w-full sm:w-auto">
              <button
                onClick={() => onNavigateTab("investigation")}
                className="flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition shadow-lg shadow-indigo-600/20"
              >
                <Target className="w-4 h-4 text-indigo-200" />
                <span>Investigate a Change</span>
                <ArrowRight className="w-3.5 h-3.5 text-indigo-200" />
              </button>

              <button
                onClick={() => onNavigateTab("c4_export")}
                className="flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl bg-slate-800/80 hover:bg-slate-800 text-slate-300 text-xs font-medium border border-slate-700 transition"
              >
                <Layers className="w-3.5 h-3.5 text-cyan-400" />
                <span>View C4 Architecture</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Six Multi-Dimensional Health Indicators */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <Activity className="w-4 h-4 text-indigo-400" />
            Health Dimensions
          </h3>
          <span className="text-xs text-slate-500">6 deterministic indicators</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.entries(health.metrics).map(([key, metric]) => {
            const mScore = Math.round(metric.score);
            return (
              <div
                key={key}
                className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-slate-700/80 transition space-y-3 flex flex-col justify-between"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="p-1.5 rounded-lg bg-slate-800 border border-slate-700">
                        {getMetricIcon(metric.category)}
                      </div>
                      <span className="text-sm font-semibold text-white">{metric.name}</span>
                    </div>
                    <span className={`text-base font-bold font-mono ${getScoreColor(mScore)}`}>
                      {mScore}%
                    </span>
                  </div>

                  {/* Progress bar */}
                  <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${getScoreProgressBg(mScore)} transition-all duration-500`}
                      style={{ width: `${Math.max(5, mScore)}%` }}
                    />
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed pt-1">{metric.summary}</p>
                </div>

                {/* Metric detail tags */}
                <div className="pt-2 border-t border-slate-800/80 flex flex-wrap items-center gap-1.5 text-[11px] text-slate-400 font-mono">
                  {metric.category === "testing" && metric.details && (
                    <>
                      <span>{metric.details.covered_source_files} tested</span>
                      <span>&bull;</span>
                      <span>{metric.details.untested_source_files} untested</span>
                    </>
                  )}
                  {metric.category === "ownership" && metric.details && (
                    <>
                      <span>Bus factor: {metric.details.bus_factor}</span>
                      <span>&bull;</span>
                      <span>{metric.details.contributor_count} authors</span>
                    </>
                  )}
                  {metric.category === "stability" && metric.details && (
                    <>
                      <span>{metric.details.defect_commits} defect fixes</span>
                      <span>&bull;</span>
                      <span>{Math.round((metric.details.defect_ratio || 0) * 100)}% churn</span>
                    </>
                  )}
                  {metric.category === "architecture" && metric.details && (
                    <>
                      <span>{metric.details.coupling_density} deps/file</span>
                    </>
                  )}
                  {metric.category === "governance" && metric.details && (
                    <>
                      <span>{metric.details.adr_count} ADRs</span>
                      <span>&bull;</span>
                      <span>{metric.details.constraint_count} constraints</span>
                    </>
                  )}
                  {metric.category === "concurrency" && metric.details && (
                    <>
                      <span>{metric.details.open_pr_count} open PRs</span>
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. Hotspots & High-Risk Files Table */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Flame className="w-4 h-4 text-amber-400" />
            <h3 className="text-lg font-bold text-white">Defect &amp; Churn Hotspots</h3>
          </div>
          <span className="text-xs text-slate-500">Top frequently modified and bug-fixed files</span>
        </div>

        {data.hotspots.length === 0 ? (
          <div className="p-8 text-center bg-slate-900/40 border border-slate-800 rounded-xl text-slate-400 text-xs">
            No defect hotspots identified. Churn is evenly distributed.
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/50">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/80 text-slate-400 font-semibold border-b border-slate-800 uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="py-3 px-4">File Path</th>
                  <th className="py-3 px-4">Total Changes</th>
                  <th className="py-3 px-4">Defect Repairs</th>
                  <th className="py-3 px-4">Risk Level</th>
                  <th className="py-3 px-4 text-right">Quick Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {data.hotspots.map((h) => (
                  <tr key={h.file_path} className="hover:bg-slate-800/30 transition">
                    <td className="py-3 px-4 text-slate-200 font-medium">
                      <div className="flex items-center gap-2">
                        <FileCode className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
                        <span className="truncate max-w-md" title={h.file_path}>
                          {h.file_path}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-slate-300">{h.change_count}</td>
                    <td className="py-3 px-4">
                      {h.defect_count > 0 ? (
                        <span className="text-red-400 font-semibold">{h.defect_count} fixes</span>
                      ) : (
                        <span className="text-slate-500">0</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      {h.risk_level === "high" && (
                        <span className="px-2 py-0.5 rounded bg-red-500/10 border border-red-500/30 text-red-400 text-[10px] font-bold">
                          HIGH CHURN
                        </span>
                      )}
                      {h.risk_level === "medium" && (
                        <span className="px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-400 text-[10px] font-bold">
                          MODERATE
                        </span>
                      )}
                      {h.risk_level === "low" && (
                        <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-400 text-[10px]">
                          LOW
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => onNavigateTab("investigation", h.file_path)}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/40 text-[11px] font-medium transition"
                        title="Investigate proposed change targeting this hotspot"
                      >
                        <Target className="w-3 h-3" />
                        <span>Investigate</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 4. Contributors & Dominant Architectural Roles Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Contributors & Blame Distribution */}
        <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-bold text-white flex items-center gap-2">
              <Users className="w-4 h-4 text-purple-400" />
              Key Maintainers &amp; Authorship Blame
            </h4>
            <span className="text-xs text-slate-500">
              {data.top_contributors.length} top authors
            </span>
          </div>

          {data.top_contributors.length === 0 ? (
            <p className="text-xs text-slate-500">No contributor records indexed yet.</p>
          ) : (
            <div className="space-y-3">
              {data.top_contributors.map((c) => (
                <div
                  key={c.name}
                  className="flex items-center justify-between p-3 rounded-lg bg-slate-950/60 border border-slate-800/80"
                >
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-white">{c.name}</span>
                      <span className="text-[10px] px-1.5 py-0.2 rounded bg-purple-500/10 border border-purple-500/20 text-purple-300">
                        {c.role}
                      </span>
                    </div>
                    {c.email && <p className="text-[11px] text-slate-500">{c.email}</p>}
                  </div>

                  <div className="text-right">
                    <span className="text-xs font-mono font-bold text-white">
                      {c.ownership_percentage}%
                    </span>
                    <p className="text-[10px] text-slate-500">{c.commit_count} commits</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Architectural Roles Composition */}
        <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-bold text-white flex items-center gap-2">
              <Boxes className="w-4 h-4 text-cyan-400" />
              Architectural Symbol Composition
            </h4>
            <span className="text-xs text-slate-500">
              {Object.keys(data.dominant_roles).length} classified roles
            </span>
          </div>

          {Object.keys(data.dominant_roles).length === 0 ? (
            <p className="text-xs text-slate-500">No symbols classified into architectural roles yet.</p>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(data.dominant_roles).map(([role, count]) => (
                <div
                  key={role}
                  className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 flex items-center justify-between"
                >
                  <span className="text-xs font-medium text-slate-300 capitalize">{role}</span>
                  <span className="text-xs font-mono font-bold text-indigo-400">{count}</span>
                </div>
              ))}
            </div>
          )}

          {/* Quick Subsystems Jump */}
          <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
            <span>Containers / Modules: {data.container_count}</span>
            <button
              onClick={() => onNavigateTab("components")}
              className="text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-medium transition"
            >
              <span>Explore Components</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
