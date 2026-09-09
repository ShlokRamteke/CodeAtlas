"use client";

import React, { useState, useEffect } from "react";
import type {
  EngineeringContextOverviewResponse,
  EngineeringDocumentItem,
  EngineeringDocumentDetailItem,
  DesignConstraintItem,
  ADRItem,
  ConstraintCategory,
  ADRStatus,
  ConstraintLevel,
} from "@archaeologist/contracts";
import {
  fetchEngineeringOverview,
  fetchEngineeringDocs,
  fetchEngineeringDocDetail,
  fetchADRs,
  fetchDesignConstraints,
  searchEngineeringContext,
} from "@/lib/api";
import {
  BookOpen,
  FileText,
  ShieldCheck,
  ShieldAlert,
  Search,
  Filter,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Layers,
  ArrowUpRight,
  ChevronRight,
  Tag,
  Clock,
  User,
  Scale,
  Hash,
  ExternalLink,
} from "lucide-react";

interface EngineeringContextViewerProps {
  repositoryId: string;
}

export function EngineeringContextViewer({ repositoryId }: EngineeringContextViewerProps) {
  const [subTab, setSubTab] = useState<"overview" | "adrs" | "constraints" | "docs" | "search">(
    "overview"
  );
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState<EngineeringContextOverviewResponse | null>(null);

  // ADRs
  const [adrs, setAdrs] = useState<ADRItem[]>([]);
  const [adrStatusFilter, setAdrStatusFilter] = useState<string>("all");
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [selectedDocDetail, setSelectedDocDetail] = useState<EngineeringDocumentDetailItem | null>(null);
  const [docDetailLoading, setDocDetailLoading] = useState(false);

  // Constraints
  const [constraints, setConstraints] = useState<DesignConstraintItem[]>([]);
  const [constraintCatFilter, setConstraintCatFilter] = useState<string>("all");
  const [constraintLevelFilter, setConstraintLevelFilter] = useState<string>("all");
  const [constraintSearch, setConstraintSearch] = useState<string>("");

  // Docs
  const [docs, setDocs] = useState<EngineeringDocumentItem[]>([]);
  const [docTypeFilter, setDocTypeFilter] = useState<string>("all");

  // Search
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any>(null);
  const [searching, setSearching] = useState(false);

  // Initial load
  useEffect(() => {
    loadOverview();
  }, [repositoryId]);

  const loadOverview = async () => {
    setLoading(true);
    try {
      const data = await fetchEngineeringOverview(repositoryId);
      setOverview(data);
    } finally {
      setLoading(false);
    }
  };

  // Load ADRs on tab switch
  useEffect(() => {
    if (subTab === "adrs") {
      fetchADRs(repositoryId, adrStatusFilter === "all" ? undefined : adrStatusFilter).then(setAdrs);
    }
  }, [subTab, adrStatusFilter, repositoryId]);

  // Load Constraints on tab switch
  useEffect(() => {
    if (subTab === "constraints") {
      fetchDesignConstraints(
        repositoryId,
        constraintCatFilter === "all" ? undefined : constraintCatFilter,
        constraintLevelFilter === "all" ? undefined : constraintLevelFilter
      ).then(setConstraints);
    }
  }, [subTab, constraintCatFilter, constraintLevelFilter, repositoryId]);

  // Load Docs on tab switch
  useEffect(() => {
    if (subTab === "docs") {
      fetchEngineeringDocs(
        repositoryId,
        docTypeFilter === "all" ? undefined : docTypeFilter
      ).then(setDocs);
    }
  }, [subTab, docTypeFilter, repositoryId]);

  // Load single doc detail
  useEffect(() => {
    if (selectedDocId) {
      setDocDetailLoading(true);
      fetchEngineeringDocDetail(repositoryId, selectedDocId).then((data) => {
        setSelectedDocDetail(data);
        setDocDetailLoading(false);
      });
    } else {
      setSelectedDocDetail(null);
    }
  }, [selectedDocId, repositoryId]);

  // Perform search
  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const res = await searchEngineeringContext(repositoryId, searchQuery.trim());
      setSearchResults(res);
    } finally {
      setSearching(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case "accepted":
        return "bg-emerald-500/20 text-emerald-300 border-emerald-500/30";
      case "proposed":
        return "bg-amber-500/20 text-amber-300 border-amber-500/30";
      case "superseded":
      case "deprecated":
        return "bg-rose-500/20 text-rose-300 border-rose-500/30";
      case "draft":
        return "bg-sky-500/20 text-sky-300 border-sky-500/30";
      default:
        return "bg-slate-700/50 text-slate-300 border-slate-600/30";
    }
  };

  const getLevelBadge = (level: string) => {
    switch (level.toLowerCase()) {
      case "must_not":
        return "bg-rose-500/20 text-rose-300 border-rose-500/40 font-bold";
      case "must":
        return "bg-amber-500/20 text-amber-300 border-amber-500/40 font-semibold";
      case "should":
        return "bg-blue-500/20 text-blue-300 border-blue-500/40";
      default:
        return "bg-slate-700/50 text-slate-300 border-slate-600/30";
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category.toLowerCase()) {
      case "security":
        return <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />;
      case "performance":
        return <Clock className="w-3.5 h-3.5 text-amber-400" />;
      case "architecture":
        return <Layers className="w-3.5 h-3.5 text-indigo-400" />;
      case "testing":
        return <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />;
      case "data_integrity":
        return <Scale className="w-3.5 h-3.5 text-purple-400" />;
      default:
        return <Tag className="w-3.5 h-3.5 text-slate-400" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Sub Navigation */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSubTab("overview")}
            className={`px-3 py-1.5 text-xs rounded-md transition ${
              subTab === "overview"
                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-semibold"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => setSubTab("adrs")}
            className={`px-3 py-1.5 text-xs rounded-md transition ${
              subTab === "adrs"
                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-semibold"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Decisions (ADRs) ({overview?.totalAdrs ?? 0})
          </button>
          <button
            onClick={() => setSubTab("constraints")}
            className={`px-3 py-1.5 text-xs rounded-md transition ${
              subTab === "constraints"
                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-semibold"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Design Constraints ({overview?.totalConstraints ?? 0})
          </button>
          <button
            onClick={() => setSubTab("docs")}
            className={`px-3 py-1.5 text-xs rounded-md transition ${
              subTab === "docs"
                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-semibold"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Document Catalog ({overview?.totalDocs ?? 0})
          </button>
          <button
            onClick={() => setSubTab("search")}
            className={`px-3 py-1.5 text-xs rounded-md transition flex items-center gap-1.5 ${
              subTab === "search"
                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-semibold"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Search className="w-3 h-3" />
            Context Search
          </button>
        </div>
      </div>

      {/* OVERVIEW SUB-TAB */}
      {subTab === "overview" && (
        <div className="space-y-6">
          {/* Key Metric Tiles */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">Indexed Docs</span>
                <BookOpen className="w-4 h-4 text-emerald-400" />
              </div>
              <p className="text-2xl font-bold text-slate-100 mt-2">
                {overview?.totalDocs ?? 0}
              </p>
              <div className="text-[11px] text-slate-400 mt-1">
                Architecture, READMEs, & guides
              </div>
            </div>

            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">ADRs (Decisions)</span>
                <Scale className="w-4 h-4 text-purple-400" />
              </div>
              <p className="text-2xl font-bold text-purple-300 mt-2">
                {overview?.totalAdrs ?? 0}
              </p>
              <div className="text-[11px] text-slate-400 mt-1">
                Documented architectural decisions
              </div>
            </div>

            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">Design Constraints</span>
                <ShieldAlert className="w-4 h-4 text-amber-400" />
              </div>
              <p className="text-2xl font-bold text-amber-300 mt-2">
                {overview?.totalConstraints ?? 0}
              </p>
              <div className="text-[11px] text-slate-400 mt-1">
                RFC 2119 invariants & rules
              </div>
            </div>

            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">Security Invariants</span>
                <ShieldCheck className="w-4 h-4 text-rose-400" />
              </div>
              <p className="text-2xl font-bold text-rose-300 mt-2">
                {overview?.constraintsByCategory?.security ?? 0}
              </p>
              <div className="text-[11px] text-slate-400 mt-1">
                Sanitization & secret policies
              </div>
            </div>
          </div>

          {/* Categories Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Category Distribution */}
            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-5">
              <h3 className="text-sm font-semibold text-slate-200 mb-4 flex items-center gap-2">
                <Layers className="w-4 h-4 text-emerald-400" />
                Constraints by Domain
              </h3>
              <div className="space-y-3">
                {overview && Object.entries(overview.constraintsByCategory).length > 0 ? (
                  Object.entries(overview.constraintsByCategory).map(([cat, count]) => (
                    <div key={cat} className="flex items-center justify-between text-xs">
                      <span className="flex items-center gap-2 text-slate-300 capitalize">
                        {getCategoryIcon(cat)}
                        {cat.replace("_", " ")}
                      </span>
                      <div className="flex items-center gap-3">
                        <div className="w-32 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                          <div
                            className="bg-emerald-500 h-full rounded-full"
                            style={{
                              width: `${Math.min(
                                100,
                                ((count as number) / (overview.totalConstraints || 1)) * 100
                              )}%`,
                            }}
                          />
                        </div>
                        <span className="text-slate-400 font-mono w-6 text-right">{count}</span>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-400 italic">No constraints indexed yet.</p>
                )}
              </div>
            </div>

            {/* Document Types Distribution */}
            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-5">
              <h3 className="text-sm font-semibold text-slate-200 mb-4 flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-purple-400" />
                Documentation Breakdown
              </h3>
              <div className="space-y-3">
                {overview && Object.entries(overview.docsByType).length > 0 ? (
                  Object.entries(overview.docsByType).map(([docType, count]) => (
                    <div key={docType} className="flex items-center justify-between text-xs">
                      <span className="text-slate-300 uppercase tracking-wider text-[11px] font-mono">
                        {docType.replace("_", " ")}
                      </span>
                      <div className="flex items-center gap-3">
                        <div className="w-32 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                          <div
                            className="bg-purple-500 h-full rounded-full"
                            style={{
                              width: `${Math.min(
                                100,
                                ((count as number) / (overview.totalDocs || 1)) * 100
                              )}%`,
                            }}
                          />
                        </div>
                        <span className="text-slate-400 font-mono w-6 text-right">{count}</span>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-400 italic">No documents indexed yet.</p>
                )}
              </div>
            </div>
          </div>

          {/* Top Constraints Preview */}
          <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-amber-400" />
                Critical Architectural Invariants
              </h3>
              <button
                onClick={() => setSubTab("constraints")}
                className="text-xs text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
              >
                View all ({overview?.totalConstraints}) <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {overview?.topConstraints?.slice(0, 6).map((c) => (
                <div
                  key={c.id}
                  className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3 space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded border uppercase ${getLevelBadge(
                        c.level
                      )}`}
                    >
                      {c.level.replace("_", " ")}
                    </span>
                    <span className="text-[10px] text-slate-400 flex items-center gap-1 font-mono">
                      {getCategoryIcon(c.category)}
                      {c.category}
                    </span>
                  </div>
                  <p className="text-xs font-medium text-slate-200 line-clamp-1">{c.title}</p>
                  <p className="text-[11px] text-slate-400 line-clamp-2 italic">
                    "{c.statement}"
                  </p>
                  <div className="text-[10px] text-slate-400 font-mono pt-1">
                    {c.sourcePath}:{c.lineStart}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ADRs SUB-TAB */}
      {subTab === "adrs" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 flex items-center gap-1">
                <Filter className="w-3.5 h-3.5" /> Status:
              </span>
              {["all", "accepted", "proposed", "superseded", "deprecated"].map((st) => (
                <button
                  key={st}
                  onClick={() => setAdrStatusFilter(st)}
                  className={`px-2.5 py-1 text-xs rounded capitalize transition ${
                    adrStatusFilter === st
                      ? "bg-purple-500/20 text-purple-300 border border-purple-500/30 font-semibold"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {st}
                </button>
              ))}
            </div>
            <span className="text-xs text-slate-400">{adrs.length} decisions recorded</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {adrs.map((adr) => (
              <div
                key={adr.id}
                onClick={() => {
                  setSelectedDocId(adr.id);
                  setSubTab("docs");
                }}
                className="bg-slate-900/50 hover:bg-slate-900/80 border border-slate-800 hover:border-purple-500/40 rounded-xl p-4 cursor-pointer transition space-y-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <h4 className="text-sm font-semibold text-slate-100 flex-1">{adr.title}</h4>
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded border uppercase whitespace-nowrap ${getStatusBadge(
                      adr.status
                    )}`}
                  >
                    {adr.status}
                  </span>
                </div>
                {adr.summary && (
                  <p className="text-xs text-slate-400 line-clamp-2">{adr.summary}</p>
                )}
                <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-400 pt-1 border-t border-slate-800/60 font-mono">
                  <span>{adr.path}</span>
                  {adr.deciders && (
                    <span className="flex items-center gap-1 text-slate-400">
                      <User className="w-3 h-3 text-purple-400" />
                      {adr.deciders}
                    </span>
                  )}
                </div>
              </div>
            ))}
            {adrs.length === 0 && (
              <div className="col-span-2 text-center py-12 text-slate-400 text-xs">
                No Architecture Decision Records matched the selected filter.
              </div>
            )}
          </div>
        </div>
      )}

      {/* DESIGN CONSTRAINTS SUB-TAB */}
      {subTab === "constraints" && (
        <div className="space-y-4">
          {/* Filter Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/40 p-3 rounded-lg border border-slate-800">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-slate-400">Domain:</span>
              {[
                "all",
                "security",
                "architecture",
                "performance",
                "testing",
                "data_integrity",
              ].map((cat) => (
                <button
                  key={cat}
                  onClick={() => setConstraintCatFilter(cat)}
                  className={`px-2.5 py-1 text-xs rounded capitalize transition ${
                    constraintCatFilter === cat
                      ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-semibold"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {cat.replace("_", " ")}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">Level:</span>
              {["all", "must", "must_not", "should"].map((lvl) => (
                <button
                  key={lvl}
                  onClick={() => setConstraintLevelFilter(lvl)}
                  className={`px-2 py-0.5 text-xs rounded uppercase font-mono transition ${
                    constraintLevelFilter === lvl
                      ? "bg-amber-500/20 text-amber-300 border border-amber-500/30 font-bold"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {lvl.replace("_", " ")}
                </button>
              ))}
            </div>
          </div>

          {/* Constraints List */}
          <div className="space-y-3">
            {constraints.map((c) => (
              <div
                key={c.id}
                className="bg-slate-900/50 border border-slate-800 rounded-lg p-4 space-y-2 hover:border-slate-700 transition"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded border uppercase ${getLevelBadge(
                        c.level
                      )}`}
                    >
                      {c.level.replace("_", " ")}
                    </span>
                    <span className="text-xs font-semibold text-slate-200">{c.title}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] px-2 py-0.5 rounded bg-slate-800/80 text-slate-300 flex items-center gap-1.5 capitalize font-mono">
                      {getCategoryIcon(c.category)}
                      {c.category.replace("_", " ")}
                    </span>
                    <span className="text-[10px] text-slate-400 font-mono">
                      conf: {Math.round(c.confidence * 100)}%
                    </span>
                  </div>
                </div>

                <div className="text-xs text-slate-300 bg-slate-950/60 p-2.5 rounded border border-slate-800/60">
                  {c.statement}
                </div>

                <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono pt-1">
                  <span>
                    Source: {c.sourcePath}
                    {c.lineStart ? ` (lines ${c.lineStart}-${c.lineEnd || c.lineStart})` : ""}
                  </span>
                  <button
                    onClick={() => {
                      if (c.documentId) {
                        setSelectedDocId(c.documentId);
                        setSubTab("docs");
                      }
                    }}
                    className="text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
                  >
                    View Document <ExternalLink className="w-3 h-3" />
                  </button>
                </div>
              </div>
            ))}
            {constraints.length === 0 && (
              <div className="text-center py-12 text-slate-400 text-xs">
                No design constraints matched the selected filters.
              </div>
            )}
          </div>
        </div>
      )}

      {/* DOCUMENT CATALOG SUB-TAB */}
      {subTab === "docs" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Doc List Column */}
          <div className="lg:col-span-1 space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <span className="text-xs font-semibold text-slate-300">Repository Documents</span>
              <select
                value={docTypeFilter}
                onChange={(e) => setDocTypeFilter(e.target.value)}
                className="bg-slate-900 border border-slate-800 text-xs rounded px-2 py-1 text-slate-300"
              >
                <option value="all">All Types</option>
                <option value="readme">README</option>
                <option value="architecture">Architecture</option>
                <option value="adr">ADR</option>
                <option value="testing_guide">Testing</option>
                <option value="design_doc">Design</option>
                <option value="general_doc">General</option>
              </select>
            </div>

            <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
              {docs.map((d) => (
                <div
                  key={d.id}
                  onClick={() => setSelectedDocId(d.id)}
                  className={`p-3 rounded-lg border cursor-pointer transition ${
                    selectedDocId === d.id
                      ? "bg-emerald-500/10 border-emerald-500/40 text-slate-100"
                      : "bg-slate-900/40 border-slate-800 hover:border-slate-700 text-slate-300"
                  }`}
                >
                  <div className="flex items-center justify-between gap-1 mb-1">
                    <span className="text-xs font-semibold truncate flex-1">{d.title}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 uppercase font-mono">
                      {d.docType}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400 font-mono truncate">{d.path}</div>
                </div>
              ))}
              {docs.length === 0 && (
                <div className="text-center py-8 text-slate-400 text-xs">
                  No documents found.
                </div>
              )}
            </div>
          </div>

          {/* Doc Detail Column */}
          <div className="lg:col-span-2 bg-slate-900/50 border border-slate-800 rounded-xl p-5">
            {docDetailLoading ? (
              <div className="text-center py-20 text-slate-400 text-xs">
                Loading document detail...
              </div>
            ) : selectedDocDetail ? (
              <div className="space-y-5">
                <div className="border-b border-slate-800 pb-3 flex items-start justify-between gap-4">
                  <div>
                    <h3 className="text-base font-bold text-slate-100">
                      {selectedDocDetail.title}
                    </h3>
                    <p className="text-xs text-slate-400 font-mono mt-0.5">
                      {selectedDocDetail.path}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 uppercase font-mono">
                      {selectedDocDetail.docType}
                    </span>
                    {selectedDocDetail.status !== "n/a" && (
                      <span
                        className={`text-[11px] px-2 py-0.5 rounded border uppercase ${getStatusBadge(
                          selectedDocDetail.status
                        )}`}
                      >
                        {selectedDocDetail.status}
                      </span>
                    )}
                  </div>
                </div>

                {/* Extracted Constraints in this doc */}
                {selectedDocDetail.constraints && selectedDocDetail.constraints.length > 0 && (
                  <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3 space-y-2">
                    <h4 className="text-xs font-semibold text-amber-300 flex items-center gap-1.5">
                      <ShieldAlert className="w-3.5 h-3.5" />
                      Extracted Constraints ({selectedDocDetail.constraints.length})
                    </h4>
                    <div className="space-y-1.5">
                      {selectedDocDetail.constraints.map((c) => (
                        <div
                          key={c.id}
                          className="flex items-start gap-2 text-xs text-slate-300 bg-slate-900/60 p-2 rounded"
                        >
                          <span
                            className={`text-[9px] px-1.5 py-0.5 rounded border uppercase shrink-0 mt-0.5 ${getLevelBadge(
                              c.level
                            )}`}
                          >
                            {c.level.replace("_", " ")}
                          </span>
                          <div className="flex-1">
                            <span className="font-medium text-slate-200">{c.title}: </span>
                            <span className="text-slate-400">{c.statement}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Content Render */}
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Document Content
                  </h4>
                  <pre className="text-xs text-slate-300 bg-slate-950 p-4 rounded-lg overflow-x-auto max-h-[450px] font-mono whitespace-pre-wrap leading-relaxed border border-slate-800/80">
                    {selectedDocDetail.rawContent}
                  </pre>
                </div>
              </div>
            ) : (
              <div className="text-center py-20 text-slate-400 text-xs">
                Select a document from the left list to inspect its content and constraints.
              </div>
            )}
          </div>
        </div>
      )}

      {/* SEARCH SUB-TAB */}
      {subTab === "search" && (
        <div className="space-y-6">
          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="relative flex-1">
              <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search across READMEs, architecture docs, ADRs, & design constraints..."
                className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-9 pr-4 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
              />
            </div>
            <button
              type="submit"
              disabled={searching || !searchQuery.trim()}
              className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white px-4 py-2 text-xs rounded-lg font-medium transition flex items-center gap-1.5"
            >
              {searching ? "Searching..." : "Search"}
            </button>
          </form>

          {searchResults && (
            <div className="space-y-6">
              <div className="text-xs text-slate-400">
                Found {searchResults.totalMatches} matches for query:{" "}
                <span className="font-semibold text-slate-200">"{searchResults.query}"</span>
              </div>

              {/* Matched Constraints */}
              {searchResults.constraints && searchResults.constraints.length > 0 && (
                <div className="space-y-3">
                  <h4 className="text-xs font-semibold text-amber-300 flex items-center gap-1.5">
                    <ShieldAlert className="w-4 h-4" />
                    Matched Constraints ({searchResults.constraints.length})
                  </h4>
                  <div className="space-y-2">
                    {searchResults.constraints.map((c: any) => (
                      <div
                        key={c.id}
                        className="bg-slate-900/50 border border-slate-800 rounded-lg p-3 space-y-1.5"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span
                              className={`text-[10px] px-2 py-0.5 rounded border uppercase ${getLevelBadge(
                                c.level
                              )}`}
                            >
                              {c.level}
                            </span>
                            <span className="text-xs font-semibold text-slate-200">{c.title}</span>
                          </div>
                          <span className="text-[10px] text-emerald-400 font-mono">
                            score: {c.relevance_score}
                          </span>
                        </div>
                        <p className="text-xs text-slate-300 bg-slate-950/50 p-2 rounded">
                          {c.statement}
                        </p>
                        <div className="text-[10px] text-slate-400 font-mono">
                          {c.source_path}:{c.line_start}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Matched Documents */}
              {searchResults.docs && searchResults.docs.length > 0 && (
                <div className="space-y-3">
                  <h4 className="text-xs font-semibold text-purple-300 flex items-center gap-1.5">
                    <BookOpen className="w-4 h-4" />
                    Matched Documents ({searchResults.docs.length})
                  </h4>
                  <div className="space-y-2">
                    {searchResults.docs.map((d: any) => (
                      <div
                        key={d.id}
                        onClick={() => {
                          setSelectedDocId(d.id);
                          setSubTab("docs");
                        }}
                        className="bg-slate-900/50 hover:bg-slate-900/80 border border-slate-800 rounded-lg p-3 cursor-pointer transition space-y-1"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold text-slate-100">{d.title}</span>
                          <span className="text-[10px] text-emerald-400 font-mono">
                            score: {d.relevance_score}
                          </span>
                        </div>
                        <p className="text-xs text-slate-400 line-clamp-2">{d.summary}</p>
                        <div className="text-[10px] text-slate-400 font-mono">{d.path}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
