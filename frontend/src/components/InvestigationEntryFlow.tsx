"use client";

import React, { useState, useEffect, useRef, useMemo } from "react";
import {
  Zap,
  Sparkles,
  Play,
  FileCode,
  Code2,
  Layers,
  GitPullRequest,
  Search,
  Check,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  ShieldCheck,
  Copy,
  X,
  ArrowRight,
  GitBranch,
  FolderTree,
  Loader2,
  ChevronDown,
} from "lucide-react";
import type {
  Repository,
  RepositoryFileItem,
  SymbolItem,
  ArchitectureOverview,
  PullRequestItem,
  PreFlightImpactResponse,
  ArchitecturalRole,
} from "@codeatlas/contracts";
import {
  fetchRepositoryFiles,
  fetchRepositorySymbols,
  fetchRepositoryArchitecture,
  fetchRepositoryPullRequests,
  previewInvestigationImpact,
} from "@/lib/api";

interface InvestigationEntryFlowProps {
  repository: Repository;
  initialTargetPath?: string;
  onRunInvestigation: (params: {
    query: string;
    targetPath?: string;
    targetSymbol?: string;
    targetFiles?: string[];
    diff?: string;
  }) => Promise<void>;
  running: boolean;
  errorMsg: string | null;
}

type SelectorMode = "autocomplete" | "component" | "pull_request";

interface SearchResultItem {
  id: string;
  type: "file" | "symbol";
  title: string;
  subtitle: string;
  filePath: string;
  symbolName?: string;
  kind?: string;
  role?: ArchitecturalRole | null;
  symbolCount?: number;
}

export function InvestigationEntryFlow({
  repository,
  initialTargetPath,
  onRunInvestigation,
  running,
  errorMsg,
}: InvestigationEntryFlowProps) {
  // Selector Mode
  const [selectorMode, setSelectorMode] = useState<SelectorMode>("autocomplete");

  // Repository Data
  const [files, setFiles] = useState<RepositoryFileItem[]>([]);
  const [symbols, setSymbols] = useState<SymbolItem[]>([]);
  const [architecture, setArchitecture] = useState<ArchitectureOverview | null>(null);
  const [openPRs, setOpenPRs] = useState<PullRequestItem[]>([]);
  const [loadingData, setLoadingData] = useState(true);

  // Form inputs
  const [query, setQuery] = useState(
    initialTargetPath ? `Investigate changes in ${initialTargetPath}` : ""
  );
  const [targetPath, setTargetPath] = useState(initialTargetPath || "");
  const [targetSymbol, setTargetSymbol] = useState("");
  const [targetFiles, setTargetFiles] = useState<string[]>(
    initialTargetPath ? [initialTargetPath] : []
  );
  const [diff, setDiff] = useState("");
  const [showDiffInput, setShowDiffInput] = useState(false);

  // Combobox Autocomplete state
  const [searchQuery, setSearchQuery] = useState("");
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Pre-Flight Impact Preview State
  const [impactPreview, setImpactPreview] = useState<PreFlightImpactResponse | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [copiedSummary, setCopiedSummary] = useState(false);

  // Initial target path propagation
  useEffect(() => {
    if (initialTargetPath) {
      setTargetPath(initialTargetPath);
      setTargetFiles([initialTargetPath]);
      if (!query) {
        setQuery(`Investigate changes in ${initialTargetPath}`);
      }
    }
  }, [initialTargetPath]);

  // Load files, symbols, architecture, and open PRs
  useEffect(() => {
    let cancelled = false;
    async function loadRepoIntelligence() {
      setLoadingData(true);
      try {
        const [filesRes, symsRes, archRes, prsRes] = await Promise.all([
          fetchRepositoryFiles(repository.id),
          fetchRepositorySymbols(repository.id),
          fetchRepositoryArchitecture(repository.id),
          fetchRepositoryPullRequests(repository.id, "open"),
        ]);
        if (!cancelled) {
          setFiles(filesRes);
          setSymbols(symsRes);
          setArchitecture(archRes);
          setOpenPRs(prsRes);
        }
      } catch (err) {
        console.error("Failed loading repository intelligence:", err);
      } finally {
        if (!cancelled) setLoadingData(false);
      }
    }
    loadRepoIntelligence();
    return () => {
      cancelled = true;
    };
  }, [repository.id]);

  // Filtered autocomplete search results
  const searchResults: SearchResultItem[] = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    const results: SearchResultItem[] = [];

    // Filter files
    const matchedFiles = files
      .filter((f) => !q || f.path.toLowerCase().includes(q))
      .slice(0, 15)
      .map((f) => ({
        id: `file-${f.id}`,
        type: "file" as const,
        title: f.path,
        subtitle: `${f.language} &bull; ${f.symbolCount} symbols &bull; ${(f.sizeBytes / 1024).toFixed(1)} KB`,
        filePath: f.path,
        symbolCount: f.symbolCount,
      }));

    // Filter symbols
    const matchedSymbols = symbols
      .filter(
        (s) =>
          !q ||
          s.name.toLowerCase().includes(q) ||
          (s.filePath && s.filePath.toLowerCase().includes(q)) ||
          (s.architecturalRole && s.architecturalRole.toLowerCase().includes(q))
      )
      .slice(0, 20)
      .map((s) => ({
        id: `sym-${s.id}`,
        type: "symbol" as const,
        title: s.name,
        subtitle: s.filePath
          ? `in ${s.filePath}${s.lineStart ? `:${s.lineStart}` : ""}`
          : "in target file",
        filePath: s.filePath || "",
        symbolName: s.name,
        kind: s.kind,
        role: s.architecturalRole,
      }));

    // Order: symbols first if typed query matches symbol name directly, else files
    if (q && symbols.some((s) => s.name.toLowerCase().startsWith(q))) {
      results.push(...matchedSymbols, ...matchedFiles);
    } else {
      results.push(...matchedFiles, ...matchedSymbols);
    }

    return results.slice(0, 30);
  }, [searchQuery, files, symbols]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(e.target as Node)
      ) {
        setIsDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Keyboard navigation for combobox
  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!isDropdownOpen && (e.key === "ArrowDown" || e.key === "Enter")) {
      setIsDropdownOpen(true);
      return;
    }

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev < searchResults.length - 1 ? prev + 1 : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : searchResults.length - 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (searchResults[highlightedIndex]) {
        selectSearchResult(searchResults[highlightedIndex]);
      }
    } else if (e.key === "Escape") {
      setIsDropdownOpen(false);
    }
  }

  function selectSearchResult(item: SearchResultItem) {
    if (item.type === "file") {
      setTargetPath(item.filePath);
      setTargetSymbol("");
      setTargetFiles([item.filePath]);
      if (!query || query.startsWith("Investigate") || query.startsWith("Refactor")) {
        setQuery(`Refactor ${item.filePath} to enhance modularity`);
      }
    } else {
      setTargetSymbol(item.symbolName || "");
      if (item.filePath) {
        setTargetPath(item.filePath);
        setTargetFiles([item.filePath]);
      }
      if (!query || query.startsWith("Investigate") || query.startsWith("Refactor")) {
        setQuery(`Refactor ${item.symbolName} in ${item.filePath || "target file"}`);
      }
    }
    setSearchQuery("");
    setIsDropdownOpen(false);
  }

  // Component Selection
  function selectComponent(comp: any) {
    const compFiles = comp.files || [];
    const primaryFile = compFiles.length > 0 ? compFiles[0] : comp.path;
    setTargetPath(primaryFile);
    setTargetFiles(compFiles.length > 0 ? compFiles : [primaryFile]);
    setTargetSymbol("");
    setQuery(`Refactor ${comp.name} subsystem: verify architectural invariants and guarding tests`);
  }

  // PR Selection
  function selectPR(pr: PullRequestItem) {
    const prFiles = pr.touchedFiles || [];
    const primaryFile = prFiles.length > 0 ? prFiles[0] : "";
    setTargetPath(primaryFile);
    setTargetFiles(prFiles);
    setTargetSymbol("");
    setQuery(`Investigate in-flight PR #${pr.number}: ${pr.title} on branch ${pr.headBranch || "feature"}`);
  }

  // Check collision for a PR against currently active targetFiles
  function checkPRCollision(pr: PullRequestItem): boolean {
    if (!pr.touchedFiles || pr.touchedFiles.length === 0) return false;
    if (targetFiles.length === 0 && !targetPath) return false;
    const currentSet = new Set(targetFiles.concat(targetPath ? [targetPath] : []));
    return pr.touchedFiles.some((f) => currentSet.has(f));
  }

  // Intent Presets
  const INTENT_PRESETS = [
    {
      id: "refactor",
      label: "Refactor API",
      icon: "🔨",
      makeQuery: (tgt: string) => `Refactor API contracts and endpoints in ${tgt || "target files"}`,
    },
    {
      id: "migration",
      label: "Schema Migration",
      icon: "🗄️",
      makeQuery: (tgt: string) => `Migrate schema models and database constraints for ${tgt || "target files"}`,
    },
    {
      id: "bugfix",
      label: "Bug Fix",
      icon: "🐛",
      makeQuery: (tgt: string) => `Fix defect in ${tgt || "target"} and verify guarding test reachability`,
    },
    {
      id: "add_endpoint",
      label: "Add Endpoint",
      icon: "🚀",
      makeQuery: (tgt: string) => `Add new service endpoint and request/response validation in ${tgt || "target"}`,
    },
    {
      id: "security",
      label: "Security Patch",
      icon: "🛡️",
      makeQuery: (tgt: string) => `Apply security validation, sanitization, and auth guards to ${tgt || "target"}`,
    },
  ];

  function applyPreset(preset: (typeof INTENT_PRESETS)[0]) {
    const tgt = targetSymbol || targetPath || "target component";
    setQuery(preset.makeQuery(tgt));
  }

  // Debounced Pre-Flight Impact Preview
  useEffect(() => {
    const effectiveTargets = targetFiles.length > 0 ? targetFiles : (targetPath ? [targetPath] : []);
    if (effectiveTargets.length === 0 && !targetSymbol && !diff.trim()) {
      setImpactPreview(null);
      return;
    }

    let cancelled = false;
    const timer = setTimeout(async () => {
      setLoadingPreview(true);
      try {
        const preview = await previewInvestigationImpact({
          repositoryId: repository.id,
          query: query.trim() || undefined,
          targetPath: targetPath.trim() || undefined,
          targetSymbol: targetSymbol.trim() || undefined,
          targetFiles: effectiveTargets,
          diff: diff.trim() || undefined,
        });
        if (!cancelled) {
          setImpactPreview(preview);
        }
      } catch (err) {
        console.error("Preview impact failed:", err);
      } finally {
        if (!cancelled) setLoadingPreview(false);
      }
    }, 350);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [repository.id, targetPath, targetSymbol, targetFiles.join(","), diff, query]);

  function handleCopyImpactSummary() {
    if (!impactPreview) return;
    const br = impactPreview.blastRadius;
    const gt = impactPreview.guardingTests;
    const cr = impactPreview.changeRisk;
    const co = impactPreview.concurrentOverlaps;

    const summaryText = `### ⚡ Pre-Flight Impact Summary
- **Targets**: ${impactPreview.targetFiles.join(", ") || targetSymbol || "None"}
- **Blast Radius**: ${br.total_affected_count ?? 0} affected files (${(br.upstream_callers || []).length} upstream callers)
- **Guarding Tests**: ${gt.total_guarding_tests ?? 0} suites (${(gt.untested_changes || []).length} untested files)
- **Change Risk**: ${cr.risk_level ?? "MODERATE"} (Defect Pressure: ${(cr.defect_pressure ?? 0).toFixed(2)})
- **In-Flight PR Collisions**: ${co.overlapping_pr_count ?? 0} open PRs`;

    navigator.clipboard.writeText(summaryText);
    setCopiedSummary(true);
    setTimeout(() => setCopiedSummary(false), 2000);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    await onRunInvestigation({
      query: query.trim(),
      targetPath: targetPath.trim() || undefined,
      targetSymbol: targetSymbol.trim() || undefined,
      targetFiles: targetFiles.length > 0 ? targetFiles : undefined,
      diff: diff.trim() || undefined,
    });
  }

  return (
    <div className="p-6 rounded-2xl bg-slate-900/90 border border-slate-800 shadow-xl space-y-6">
      {/* Header & Mode Switcher */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/80 pb-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
            <Zap className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-white">Propose a Code Change</h3>
            <p className="text-xs text-slate-400">
              Select AST targets, pick components, or link open PRs before launching investigation
            </p>
          </div>
        </div>

        {/* Mode Selector Tabs */}
        <div className="flex items-center gap-1 p-1 rounded-xl bg-slate-950/80 border border-slate-800 text-xs">
          <button
            type="button"
            onClick={() => setSelectorMode("autocomplete")}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all flex items-center gap-1.5 ${
              selectorMode === "autocomplete"
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Search className="w-3.5 h-3.5" />
            <span>Files & Symbols</span>
          </button>
          <button
            type="button"
            onClick={() => setSelectorMode("component")}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all flex items-center gap-1.5 ${
              selectorMode === "component"
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>By Component</span>
          </button>
          <button
            type="button"
            onClick={() => setSelectorMode("pull_request")}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all flex items-center gap-1.5 ${
              selectorMode === "pull_request"
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <GitPullRequest className="w-3.5 h-3.5" />
            <span>In-Flight PRs</span>
            {openPRs.length > 0 && (
              <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-indigo-500/30 text-indigo-300">
                {openPRs.length}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Target Selector Body depending on Mode */}
      <div className="space-y-4">
        {/* MODE 1: Accessible Autocomplete Combobox */}
        {selectorMode === "autocomplete" && (
          <div className="space-y-2">
            <label className="block text-xs font-medium text-slate-300">
              Search Target AST File or Symbol <span className="text-slate-500">(Fuzzy Autocomplete)</span>
            </label>
            <div className="relative">
              <div className="relative flex items-center">
                <Search className="w-4 h-4 text-slate-500 absolute left-3 pointer-events-none" />
                <input
                  ref={inputRef}
                  type="text"
                  role="combobox"
                  aria-expanded={isDropdownOpen}
                  aria-autocomplete="list"
                  aria-controls="target-autocomplete-list"
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setIsDropdownOpen(true);
                    setHighlightedIndex(0);
                  }}
                  onFocus={() => setIsDropdownOpen(true)}
                  onKeyDown={handleKeyDown}
                  placeholder={
                    loadingData
                      ? "Indexing repository AST files and symbols..."
                      : "Type file path (e.g. auth_controller.py) or symbol (e.g. AuthService)..."
                  }
                  className="w-full pl-9 pr-8 py-2 text-xs rounded-xl bg-slate-950 border border-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 text-white placeholder:text-slate-600 font-mono"
                />
                {searchQuery && (
                  <button
                    type="button"
                    onClick={() => {
                      setSearchQuery("");
                      inputRef.current?.focus();
                    }}
                    className="absolute right-2.5 p-1 text-slate-500 hover:text-slate-300"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>

              {/* Combobox Dropdown */}
              {isDropdownOpen && (
                <div
                  ref={dropdownRef}
                  id="target-autocomplete-list"
                  role="listbox"
                  className="absolute z-30 left-0 right-0 mt-1.5 max-h-64 overflow-y-auto rounded-xl bg-slate-950 border border-slate-800 shadow-2xl divide-y divide-slate-800/40"
                >
                  {searchResults.length === 0 ? (
                    <div className="p-4 text-center text-xs text-slate-500 italic">
                      No matching AST files or symbols found.
                    </div>
                  ) : (
                    searchResults.map((item, idx) => {
                      const isHighlighted = idx === highlightedIndex;
                      return (
                        <div
                          key={item.id}
                          role="option"
                          aria-selected={isHighlighted}
                          onClick={() => selectSearchResult(item)}
                          onMouseEnter={() => setHighlightedIndex(idx)}
                          className={`p-2.5 text-xs cursor-pointer flex items-center justify-between gap-3 transition-colors ${
                            isHighlighted
                              ? "bg-indigo-600/20 text-white"
                              : "text-slate-300 hover:bg-slate-900"
                          }`}
                        >
                          <div className="flex items-center gap-2.5 min-w-0">
                            {item.type === "file" ? (
                              <FileCode className="w-4 h-4 text-sky-400 flex-shrink-0" />
                            ) : (
                              <Code2 className="w-4 h-4 text-indigo-400 flex-shrink-0" />
                            )}
                            <div className="truncate">
                              <span className="font-semibold text-white">{item.title}</span>
                              <span className="ml-2 text-[11px] text-slate-400 truncate">
                                {item.subtitle}
                              </span>
                            </div>
                          </div>
                          <div className="flex items-center gap-1.5 flex-shrink-0">
                            {item.role && (
                              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-purple-500/10 text-purple-400 border border-purple-500/20">
                                {item.role}
                              </span>
                            )}
                            {item.kind && (
                              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-400">
                                {item.kind}
                              </span>
                            )}
                            <span className="text-[10px] uppercase font-mono px-1 rounded bg-slate-800/80 text-slate-500">
                              {item.type}
                            </span>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* MODE 2: Component-Scoped Selector */}
        {selectorMode === "component" && (
          <div className="space-y-2">
            <label className="block text-xs font-medium text-slate-300">
              Pick Architectural Component <span className="text-slate-500">(1-Click Canonical Files)</span>
            </label>
            {!architecture || architecture.majorComponents.length === 0 ? (
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-500 italic text-center">
                No components indexed for this repository.
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-48 overflow-y-auto pr-1">
                {architecture.majorComponents.map((comp) => {
                  const isSelected = targetPath === comp.path || targetFiles.includes(comp.path);
                  return (
                    <button
                      key={comp.name}
                      type="button"
                      onClick={() => selectComponent(comp)}
                      className={`p-2.5 rounded-xl border text-left transition-all flex flex-col justify-between gap-1.5 ${
                        isSelected
                          ? "bg-indigo-600/20 border-indigo-500/50 text-white"
                          : "bg-slate-950/60 border-slate-800 text-slate-300 hover:bg-slate-800/40"
                      }`}
                    >
                      <div className="flex items-center justify-between w-full">
                        <span className="font-semibold text-xs text-white truncate">
                          {comp.name}
                        </span>
                        {comp.dominantRole && (
                          <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-purple-500/10 text-purple-400">
                            {comp.dominantRole}
                          </span>
                        )}

                      </div>
                      <div className="text-[11px] text-slate-400 flex items-center gap-3">
                        <span>{comp.fileCount ?? 0} files</span>
                        <span>&bull;</span>
                        <span>{comp.symbolCount ?? 0} symbols</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* MODE 3: In-Flight PR Selector */}
        {selectorMode === "pull_request" && (
          <div className="space-y-2">
            <label className="block text-xs font-medium text-slate-300">
              Pick Open In-Flight PR <span className="text-slate-500">(Check Concurrent Collisions)</span>
            </label>
            {openPRs.length === 0 ? (
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-500 italic text-center">
                No open pull requests recorded for this repository.
              </div>
            ) : (
              <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                {openPRs.map((pr) => {
                  const isColliding = checkPRCollision(pr);
                  const isSelected = query.includes(`PR #${pr.number}`);
                  return (
                    <button
                      key={pr.id}
                      type="button"
                      onClick={() => selectPR(pr)}
                      className={`w-full p-2.5 rounded-xl border text-left transition-all flex items-center justify-between gap-3 ${
                        isSelected
                          ? "bg-indigo-600/20 border-indigo-500/50 text-white"
                          : "bg-slate-950/60 border-slate-800 text-slate-300 hover:bg-slate-800/40"
                      }`}
                    >
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-indigo-400 font-bold">#{pr.number}</span>
                          <span className="font-medium text-white truncate">{pr.title}</span>
                        </div>
                        <div className="text-[11px] text-slate-400 flex items-center gap-2 mt-0.5">
                          <span>by @{pr.author}</span>
                          <span>&bull;</span>
                          <span className="font-mono text-slate-400 truncate max-w-[120px]">
                            {pr.headBranch || "branch"}
                          </span>
                          <span>&bull;</span>
                          <span>{(pr.touchedFiles || []).length} files</span>
                        </div>
                      </div>

                      {isColliding && (
                        <div className="flex items-center gap-1 px-2 py-1 rounded bg-amber-500/10 border border-amber-500/20 text-amber-400 text-[10px] font-mono flex-shrink-0 animate-pulse">
                          <AlertTriangle className="w-3 h-3" />
                          <span>Collision Risk</span>
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Active Target Chips */}
        {(targetPath || targetSymbol || targetFiles.length > 0) && (
          <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 flex flex-wrap items-center gap-2">
            <span className="text-[11px] text-slate-400 uppercase tracking-wider font-semibold">
              Active Targets:
            </span>
            {targetSymbol && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-indigo-500/15 border border-indigo-500/30 text-indigo-300 text-xs font-mono">
                <Code2 className="w-3.5 h-3.5" />
                <span>{targetSymbol}</span>
                <button
                  type="button"
                  onClick={() => setTargetSymbol("")}
                  className="hover:text-white"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}
            {targetPath && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-sky-500/15 border border-sky-500/30 text-sky-300 text-xs font-mono">
                <FileCode className="w-3.5 h-3.5" />
                <span className="max-w-[200px] truncate">{targetPath}</span>
                <button
                  type="button"
                  onClick={() => {
                    setTargetPath("");
                    setTargetFiles([]);
                  }}
                  className="hover:text-white"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}
            {targetFiles.length > 1 && (
              <span className="px-2 py-0.5 rounded text-[11px] bg-slate-800 text-slate-400 font-mono">
                +{targetFiles.length - 1} more files
              </span>
            )}
          </div>
        )}

        {/* Intent Presets Toolbar */}
        <div className="space-y-1.5 pt-1">
          <label className="block text-xs font-medium text-slate-400">
            Intent Templates <span className="text-slate-500">(1-Click Action Verbs)</span>
          </label>
          <div className="flex flex-wrap gap-1.5">
            {INTENT_PRESETS.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => applyPreset(p)}
                className="px-2.5 py-1 rounded-lg text-xs bg-slate-950/80 hover:bg-indigo-600/20 text-slate-300 hover:text-white border border-slate-800 transition-colors flex items-center gap-1.5"
              >
                <span>{p.icon}</span>
                <span>{p.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Change Intent Form */}
        <form onSubmit={handleSubmit} className="space-y-4 pt-1">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Change Intent Query <span className="text-rose-400">*</span>
            </label>
            <textarea
              rows={3}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. Refactor AuthService session token rotation in src/services/auth_service.py"
              className="w-full px-3.5 py-2.5 text-xs rounded-xl bg-slate-950 border border-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 text-white placeholder:text-slate-600 resize-none font-sans"
              required
            />
          </div>

          {/* Optional Diff Input Toggle */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs font-medium text-slate-300">
                Proposed Git Diff / Patch <span className="text-slate-500">(Optional &bull; Kamei Churn)</span>
              </label>
              <button
                type="button"
                onClick={() => setShowDiffInput(!showDiffInput)}
                className="text-[11px] text-indigo-400 hover:text-indigo-300 font-mono"
              >
                {showDiffInput ? "Hide Diff" : "+ Add Git Diff"}
              </button>
            </div>
            {showDiffInput && (
              <textarea
                rows={4}
                value={diff}
                onChange={(e) => setDiff(e.target.value)}
                placeholder="Paste unified git diff to calculate exact Kamei metrics (LA, LD, entropy)..."
                className="w-full px-3 py-2 text-xs rounded-xl bg-slate-950 border border-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 text-white font-mono placeholder:text-slate-600 resize-y"
              />
            )}
          </div>

          {/* PRE-FLIGHT IMPACT PREVIEW CARD */}
          {(impactPreview || loadingPreview) && (
            <div className="p-4 rounded-xl bg-gradient-to-br from-indigo-950/40 via-slate-950 to-slate-900 border border-indigo-500/30 space-y-3.5 shadow-lg">
              <div className="flex items-center justify-between border-b border-indigo-500/20 pb-2.5">
                <div className="flex items-center gap-2">
                  <div className="p-1 rounded bg-indigo-500/20 text-indigo-400">
                    <Sparkles className="w-3.5 h-3.5" />
                  </div>
                  <span className="text-xs font-bold text-white uppercase tracking-wider">
                    Pre-Flight Impact Preview
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                    0 Tokens Used
                  </span>
                </div>

                {impactPreview && (
                  <button
                    type="button"
                    onClick={handleCopyImpactSummary}
                    className="flex items-center gap-1 text-[11px] font-mono text-slate-400 hover:text-indigo-300"
                  >
                    {copiedSummary ? (
                      <>
                        <Check className="w-3 h-3 text-emerald-400" />
                        <span className="text-emerald-400">Copied!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3" />
                        <span>Copy Summary</span>
                      </>
                    )}
                  </button>
                )}
              </div>

              {loadingPreview ? (
                <div className="py-6 flex items-center justify-center gap-2 text-xs text-indigo-400">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Computing deterministic blast radius & risk...</span>
                </div>
              ) : impactPreview ? (
                <div className="space-y-3">
                  {/* 4-Tile High-Signal KPI Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    {/* Blast Radius */}
                    <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800 flex flex-col justify-between">
                      <span className="text-[10px] text-slate-400 font-medium">Blast Radius</span>
                      <div className="text-base font-bold text-white mt-1">
                        {impactPreview.blastRadius.total_affected_count ?? 0}
                        <span className="text-[11px] font-normal text-slate-400 ml-1">files</span>
                      </div>
                      <span className="text-[10px] text-slate-500 truncate mt-0.5">
                        {(impactPreview.blastRadius.upstream_callers || []).length} callers
                      </span>
                    </div>

                    {/* Guarding Tests */}
                    <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800 flex flex-col justify-between">
                      <span className="text-[10px] text-slate-400 font-medium">Guarding Tests</span>
                      <div className="text-base font-bold text-white mt-1">
                        {impactPreview.guardingTests.total_guarding_tests ?? 0}
                        <span className="text-[11px] font-normal text-slate-400 ml-1">suites</span>
                      </div>
                      <div className="mt-0.5">
                        {(impactPreview.guardingTests.untested_changes || []).length === 0 ? (
                          <span className="text-[10px] text-emerald-400 font-mono">Guarded</span>
                        ) : (
                          <span className="text-[10px] text-rose-400 font-mono">Untested Gaps</span>
                        )}
                      </div>
                    </div>

                    {/* Change Risk */}
                    <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800 flex flex-col justify-between">
                      <span className="text-[10px] text-slate-400 font-medium">Risk Tier</span>
                      <div className="mt-1">
                        <span
                          className={`text-xs font-bold px-2 py-0.5 rounded font-mono uppercase ${
                            impactPreview.changeRisk.risk_level === "LOW"
                              ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                              : impactPreview.changeRisk.risk_level === "MODERATE"
                              ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                              : "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                          }`}
                        >
                          {impactPreview.changeRisk.risk_level || "LOW"}
                        </span>
                      </div>
                      <span className="text-[10px] text-slate-500 mt-0.5">
                        Defect: {(impactPreview.changeRisk.defect_pressure ?? 0).toFixed(1)}
                      </span>
                    </div>

                    {/* In-Flight Collisions */}
                    <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800 flex flex-col justify-between">
                      <span className="text-[10px] text-slate-400 font-medium">In-Flight PRs</span>
                      <div className="mt-1">
                        <span
                          className={`text-xs font-bold px-2 py-0.5 rounded font-mono ${
                            (impactPreview.concurrentOverlaps.overlapping_pr_count ?? 0) === 0
                              ? "bg-emerald-500/10 text-emerald-400"
                              : "bg-amber-500/20 text-amber-400 border border-amber-500/30 animate-pulse"
                          }`}
                        >
                          {impactPreview.concurrentOverlaps.overlapping_pr_count ?? 0} Collisions
                        </span>
                      </div>
                      <span className="text-[10px] text-slate-500 mt-0.5">
                        {impactPreview.governingConstraintsCount} Invariants
                      </span>
                    </div>
                  </div>

                  {/* Warning Banners if untested or collisions */}
                  {(impactPreview.guardingTests.untested_changes || []).length > 0 && (
                    <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
                      <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-400" />
                      <span>
                        Untested change gap detected on:{" "}
                        <span className="font-mono font-semibold">
                          {(impactPreview.guardingTests.untested_changes || [])
                            .map((u) => u.target_file)
                            .join(", ")}
                        </span>
                      </span>
                    </div>
                  )}

                  {(impactPreview.concurrentOverlaps.overlapping_prs || []).length > 0 && (
                    <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 flex-shrink-0 text-amber-400" />
                      <span>
                        Concurrent PR overlap with:{" "}
                        {(impactPreview.concurrentOverlaps.overlapping_prs || []).map((p) => (
                          <span key={p.pr_number} className="font-mono font-semibold mr-1.5">
                            #{p.pr_number} (@{p.pr_author})
                          </span>
                        ))}
                      </span>
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          )}

          {/* Error Message */}
          {errorMsg && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Submit Action Button */}
          <button
            type="submit"
            disabled={running || !query.trim()}
            className="w-full py-3 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-sm transition-all flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/20"
          >
            {running ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
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
    </div>
  );
}
