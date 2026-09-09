"use client";

import React, { useState, useEffect } from "react";
import {
  Sparkles,
  Zap,
  Play,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Clock,
  Coins,
  FileCode,
  GitCommit,
  BookOpen,
  ArrowRight,
  ShieldAlert,
  Search,
  ExternalLink,
} from "lucide-react";
import type { InvestigationResponse, Repository } from "@codeatlas/contracts";
import {
  createInvestigation,
  runInvestigation,
  fetchRepositoryInvestigations,
  previewInvestigationIntent,
} from "@/lib/api";

interface PreChangeInvestigationViewerProps {
  repository: Repository;
}

export function PreChangeInvestigationViewer({
  repository,
}: PreChangeInvestigationViewerProps) {
  const [investigations, setInvestigations] = useState<InvestigationResponse[]>([]);
  const [selectedInv, setSelectedInv] = useState<InvestigationResponse | null>(null);
  const [loadingList, setLoadingList] = useState(false);

  // Form state
  const [query, setQuery] = useState("");
  const [targetPath, setTargetPath] = useState("");
  const [targetSymbol, setTargetSymbol] = useState("");
  const [running, setRunning] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Load repository investigations
  useEffect(() => {
    async function load() {
      setLoadingList(true);
      const items = await fetchRepositoryInvestigations(repository.id);
      setInvestigations(items);
      if (items.length > 0) {
        setSelectedInv(items[0]);
      } else {
        setSelectedInv(null);
      }
      setLoadingList(false);
    }
    load();
  }, [repository.id]);

  async function handleRunInvestigation(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;

    setRunning(true);
    setErrorMsg(null);

    try {
      // 1. Create investigation record
      const created = await createInvestigation({
        repositoryId: repository.id,
        query: query.trim(),
        type: "before_change",
        targetPath: targetPath.trim() || undefined,
        targetSymbol: targetSymbol.trim() || undefined,
      });

      if (!created) {
        throw new Error("Failed to initialize investigation");
      }

      // 2. Execute bounded investigation engine with LLM
      const executed = await runInvestigation(
        created.id,
        targetPath.trim() || undefined,
        targetSymbol.trim() || undefined
      );

      if (!executed) {
        throw new Error("Investigation engine run failed");
      }

      setInvestigations((prev) => [executed, ...prev]);
      setSelectedInv(executed);
    } catch (err: any) {
      setErrorMsg(err.message || "Investigation failed to execute");
    } finally {
      setRunning(false);
    }
  }

  const PRESETS = [
    {
      label: "Refactor Query Parser",
      q: "Refactor ingest_query in gitingest/query_parser.py",
      path: "gitingest/query_parser.py",
      sym: "ingest_query",
    },
    {
      label: "Auth Token Rotation",
      q: "Upgrade session authentication token rotation and timeout handling",
      path: "backend/app/auth/session.py",
      sym: "SessionManager",
    },
    {
      label: "Payment Interface",
      q: "Replace payment gateway provider with multi-vendor adapter interface",
      path: "backend/app/payments/gateway.py",
      sym: "PaymentHandler",
    },
  ];

  return (
    <div className="space-y-8">
      {/* Header Banner */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-indigo-950/40 via-purple-950/30 to-slate-900/80 border border-indigo-500/20 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-xs font-semibold text-indigo-400 mb-2">
            <Sparkles className="w-3.5 h-3.5" />
            Phase 4 Investigation Engine &bull; OpenRouter Powered
          </div>
          <h2 className="text-xl sm:text-2xl font-bold text-white">
            Pre-Change Investigation Brief
          </h2>
          <p className="text-sm text-slate-400 mt-1 max-w-2xl">
            Input a proposed change. The bounded engine collects deterministic AST relationships,
            commit history, and risk metrics, then reasons via OpenRouter to deliver an evidence-backed brief.
          </p>
        </div>
      </div>

      {/* Main Grid: Input Form + Brief Viewer */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Form & History (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Form Card */}
          <div className="p-6 rounded-xl bg-slate-900/80 border border-slate-800 space-y-4 shadow-lg">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Zap className="w-4 h-4 text-indigo-400" />
              Propose a Code Change
            </h3>

            {/* Quick Presets */}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {PRESETS.map((p, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => {
                    setQuery(p.q);
                    setTargetPath(p.path);
                    setTargetSymbol(p.sym);
                  }}
                  className="px-2.5 py-1 text-xs rounded-md bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 border border-slate-700/60 transition-colors"
                >
                  {p.label}
                </button>
              ))}
            </div>

            <form onSubmit={handleRunInvestigation} className="space-y-4 pt-2">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Change Intent Query <span className="text-rose-400">*</span>
                </label>
                <textarea
                  rows={3}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="e.g. Refactor ingest_query in gitingest/query_parser.py to support custom branch parameters"
                  className="w-full px-3 py-2 text-sm rounded-lg bg-slate-950 border border-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 text-white placeholder:text-slate-600 resize-none font-sans"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Target File (Optional)
                  </label>
                  <input
                    type="text"
                    value={targetPath}
                    onChange={(e) => setTargetPath(e.target.value)}
                    placeholder="path/to/file.py"
                    className="w-full px-3 py-1.5 text-xs rounded-lg bg-slate-950 border border-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 text-white font-mono placeholder:text-slate-600"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Target Symbol (Optional)
                  </label>
                  <input
                    type="text"
                    value={targetSymbol}
                    onChange={(e) => setTargetSymbol(e.target.value)}
                    placeholder="SymbolName"
                    className="w-full px-3 py-1.5 text-xs rounded-lg bg-slate-950 border border-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 text-white font-mono placeholder:text-slate-600"
                  />
                </div>
              </div>

              {errorMsg && (
                <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{errorMsg}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={running || !query.trim()}
                className="w-full py-2.5 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-sm transition-colors flex items-center justify-center gap-2 shadow-sm"
              >
                {running ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Investigating via OpenRouter...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-current" />
                    <span>Run Pre-Change Investigation</span>
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Past Investigations List */}
          <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Investigation History ({investigations.length})
            </h3>
            {investigations.length === 0 ? (
              <p className="text-xs text-slate-500 italic py-2">
                No investigations recorded for this repository yet.
              </p>
            ) : (
              <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                {investigations.map((inv) => (
                  <button
                    key={inv.id}
                    onClick={() => setSelectedInv(inv)}
                    className={`w-full text-left p-3 rounded-lg border transition-all text-xs flex flex-col gap-1.5 ${
                      selectedInv?.id === inv.id
                        ? "bg-indigo-500/10 border-indigo-500/40 text-white"
                        : "bg-slate-950/60 border-slate-800 text-slate-400 hover:bg-slate-800/40"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold truncate max-w-[240px] text-slate-200">
                        {inv.query}
                      </span>
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded font-mono uppercase ${
                          inv.status === "completed"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : "bg-amber-500/10 text-amber-400"
                        }`}
                      >
                        {inv.status}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-[10px] text-slate-500">
                      <span>{new Date(inv.createdAt).toLocaleTimeString()}</span>
                      {inv.tokenUsage && (
                        <span>{inv.tokenUsage.totalTokens} tokens</span>
                      )}
                      {inv.latencyMs && <span>{inv.latencyMs}ms</span>}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Pre-Change Brief Results (7 cols) */}
        <div className="lg:col-span-7">
          {selectedInv ? (
            <div className="space-y-6">
              {/* Brief Header Card */}
              <div className="p-6 rounded-xl bg-slate-900/90 border border-slate-800 space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold uppercase tracking-wider px-2.5 py-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      {selectedInv.status}
                    </span>
                    <span className="text-xs text-slate-400">
                      ID: <span className="font-mono text-slate-300">{selectedInv.id.slice(0, 8)}</span>
                    </span>
                  </div>

                  {/* Telemetry Chips */}
                  <div className="flex items-center gap-2 font-mono text-xs">
                    {selectedInv.tokenUsage && (
                      <div className="flex items-center gap-1 px-2.5 py-1 rounded bg-purple-500/10 border border-purple-500/20 text-purple-300">
                        <Coins className="w-3.5 h-3.5 text-purple-400" />
                        <span>
                          {selectedInv.tokenUsage.totalTokens} tokens ({selectedInv.tokenUsage.promptTokens} in / {selectedInv.tokenUsage.completionTokens} out)
                        </span>
                      </div>
                    )}
                    {selectedInv.latencyMs && (
                      <div className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300">
                        <Clock className="w-3.5 h-3.5 text-slate-400" />
                        <span>{(selectedInv.latencyMs / 1000).toFixed(1)}s</span>
                      </div>
                    )}
                  </div>
                </div>

                <div>
                  <h3 className="text-base font-bold text-white">{selectedInv.query}</h3>
                  {selectedInv.summary && (
                    <p className="text-sm text-slate-300 mt-2 leading-relaxed bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                      {selectedInv.summary}
                    </p>
                  )}
                </div>
              </div>

              {/* Synthesized Claims Section */}
              <div className="p-6 rounded-xl bg-slate-900/70 border border-slate-800 space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-bold text-white flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-indigo-400" />
                    Synthesized Findings &amp; Claims ({selectedInv.claims?.length || 0})
                  </h4>
                  <span className="text-xs text-slate-500">
                    Classified via OpenRouter
                  </span>
                </div>

                <div className="space-y-3">
                  {selectedInv.claims && selectedInv.claims.length > 0 ? (
                    selectedInv.claims.map((claim, idx) => {
                      const isFact = claim.classification === "fact";
                      const isInf = claim.classification === "inference";
                      return (
                        <div
                          key={idx}
                          className="p-3.5 rounded-lg bg-slate-950/80 border border-slate-800/90 space-y-2"
                        >
                          <div className="flex items-center justify-between">
                            <span
                              className={`text-[11px] font-semibold px-2 py-0.5 rounded uppercase ${
                                isFact
                                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                  : isInf
                                  ? "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                                  : "bg-purple-500/10 text-purple-400 border border-purple-500/20"
                              }`}
                            >
                              {claim.classification}
                            </span>
                            {claim.evidenceIds?.length > 0 && (
                              <span className="text-[10px] font-mono text-slate-500">
                                {claim.evidenceIds.length} evidence link(s)
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-slate-200 leading-relaxed font-sans">
                            {claim.statement}
                          </p>
                        </div>
                      );
                    })
                  ) : (
                    <p className="text-xs text-slate-500 italic">No claims generated.</p>
                  )}
                </div>
              </div>

              {/* Verified Evidence Cards */}
              <div className="p-6 rounded-xl bg-slate-900/70 border border-slate-800 space-y-4">
                <h4 className="text-sm font-bold text-white flex items-center gap-2">
                  <FileCode className="w-4 h-4 text-emerald-400" />
                  Underlying Gathered Evidence ({selectedInv.evidence?.length || 0})
                </h4>

                <div className="space-y-3">
                  {selectedInv.evidence && selectedInv.evidence.length > 0 ? (
                    selectedInv.evidence.map((ev, idx) => (
                      <div
                        key={idx}
                        className="p-3.5 rounded-lg bg-slate-950 border border-slate-800/80 space-y-2"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold text-indigo-300 flex items-center gap-1.5">
                            {ev.sourceType === "code" ? (
                              <FileCode className="w-3.5 h-3.5 text-indigo-400" />
                            ) : ev.sourceType === "commit" ? (
                              <GitCommit className="w-3.5 h-3.5 text-amber-400" />
                            ) : (
                              <BookOpen className="w-3.5 h-3.5 text-blue-400" />
                            )}
                            {ev.title}
                          </span>
                          <span className="text-[10px] font-mono text-slate-500">
                            Confidence: {(ev.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                        {ev.path && (
                          <div className="text-[11px] font-mono text-slate-400">
                            Path: {ev.path}
                          </div>
                        )}
                        <pre className="p-2.5 rounded bg-slate-900 text-slate-300 font-mono text-xs overflow-x-auto">
                          {ev.snippet}
                        </pre>
                      </div>
                    ))
                  ) : (
                    <p className="text-xs text-slate-500 italic">No evidence items recorded.</p>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-12 rounded-xl bg-slate-900/30 border border-dashed border-slate-800 text-center space-y-3">
              <Sparkles className="w-8 h-8 text-indigo-400/60 mx-auto" />
              <h3 className="text-sm font-semibold text-slate-300">
                No Investigation Selected
              </h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Select an investigation from the history on the left, or input a new proposed change to trigger the investigation engine.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
