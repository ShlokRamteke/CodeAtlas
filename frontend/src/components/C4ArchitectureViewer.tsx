"use client";

import React, { useEffect, useState } from "react";
import {
  Layers,
  Box,
  Network,
  Download,
  Copy,
  Check,
  FileText,
  Sparkles,
  Database,
  Cpu,
  Share2,
  ExternalLink,
  ShieldCheck,
  ArrowRight,
  FolderTree,
  Code2,
  RefreshCw,
  Eye,
} from "lucide-react";
import type { C4ArchitectureExport } from "@codeatlas/contracts";
import { fetchRepositoryC4Architecture, exportRepositoryArchitectureUrl } from "@/lib/api";
import { MermaidViewer } from "./MermaidViewer";
import { MarkdownRenderer } from "./MarkdownRenderer";

interface C4ArchitectureViewerProps {
  repositoryId: string;
  repositoryName: string;
  majorComponents?: Array<{ name: string; path: string }>;
}

export function C4ArchitectureViewer({
  repositoryId,
  repositoryName,
  majorComponents = [],
}: C4ArchitectureViewerProps) {
  const [c4Data, setC4Data] = useState<C4ArchitectureExport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedComponent, setSelectedComponent] = useState<string>("");
  const [activeDiagramLevel, setActiveDiagramLevel] = useState<
    "context" | "container" | "component" | "flowchart" | "markdown"
  >("flowchart");
  const [markdownViewMode, setMarkdownViewMode] = useState<"rendered" | "source">("rendered");
  const [copiedDiagram, setCopiedDiagram] = useState(false);
  const [copiedMarkdown, setCopiedMarkdown] = useState(false);
  const [expandedContainer, setExpandedContainer] = useState<string | null>(null);

  useEffect(() => {
    async function loadC4() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchRepositoryC4Architecture(repositoryId, selectedComponent || undefined);
        if (data) {
          setC4Data(data);
          if (data.containers && data.containers.length > 0) {
            setExpandedContainer(data.containers[0].id);
          }
        } else {
          setError("Failed to generate C4 architectural export.");
        }
      } catch (err: any) {
        setError(err.message || "An error occurred fetching C4 architecture.");
      } finally {
        setLoading(false);
      }
    }
    loadC4();
  }, [repositoryId, selectedComponent]);

  const getCurrentDiagramCode = (): string => {
    if (!c4Data || !c4Data.diagrams) return "";
    const d = c4Data.diagrams;
    switch (activeDiagramLevel) {
      case "context":
        return d.context_mermaid || d.contextMermaid || "";
      case "container":
        return d.container_mermaid || d.containerMermaid || "";
      case "component":
        return d.component_mermaid || d.componentMermaid || "";
      case "flowchart":
        return d.flowchart_mermaid || d.flowchartMermaid || "";
      case "markdown":
        return c4Data.markdown_export || c4Data.markdownExport || "";
      default:
        return d.flowchart_mermaid || d.flowchartMermaid || "";
    }
  };

  const getDiagramTitle = (): string => {
    switch (activeDiagramLevel) {
      case "flowchart":
        return "System Dependency Flowchart";
      case "context":
        return "C4 Level 1: System Context Diagram";
      case "container":
        return "C4 Level 2: Container Diagram";
      case "component":
        return "C4 Level 3: Component Diagram";
      default:
        return "Architecture Diagram";
    }
  };

  const handleCopy = (text: string, setCopied: (v: boolean) => void) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 space-y-4">
        <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin" />
        <div className="text-sm text-slate-400">
          Synthesizing C4 container models &amp; Mermaid architecture diagrams...
        </div>
      </div>
    );
  }

  if (error || !c4Data) {
    return (
      <div className="p-8 rounded-xl bg-slate-900/60 border border-slate-800 text-center space-y-3">
        <div className="text-rose-400 text-sm font-semibold">Architecture Export Unavailable</div>
        <p className="text-xs text-slate-400 max-w-md mx-auto">
          {error || "Unable to extract C4 models for this repository."}
        </p>
      </div>
    );
  }

  const containers = c4Data.containers || [];
  const components = c4Data.components || [];
  const relationships = c4Data.relationships || [];
  const constraints = c4Data.constraints || [];
  const persons = c4Data.persons || [];
  const systems = c4Data.systems || [];

  return (
    <div className="space-y-6">
      {/* 1. Header Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-5 rounded-xl bg-slate-900/80 border border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-semibold text-white flex items-center gap-2">
              <Layers className="w-5 h-5 text-indigo-400" />
              C4 Architecture &amp; Dependency Export
            </h3>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
              Portable C4 Model
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            System Context, Container boundaries, Component structures, and standard Mermaid diagrams.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Scope Selector */}
          {majorComponents.length > 0 && (
            <select
              value={selectedComponent}
              onChange={(e) => setSelectedComponent(e.target.value)}
              className="bg-slate-950 border border-slate-700 text-white text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-indigo-500 font-mono"
            >
              <option value="">Full System Scope</option>
              {majorComponents.map((c) => (
                <option key={c.path} value={c.path}>
                  Scope: {c.name}
                </option>
              ))}
            </select>
          )}

          {/* Download Markdown */}
          <a
            href={exportRepositoryArchitectureUrl(repositoryId, "markdown", selectedComponent || undefined)}
            download={`${repositoryName}_architecture.md`}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition shadow-sm"
          >
            <Download className="w-3.5 h-3.5" />
            Download ARCHITECTURE.md
          </a>

          {/* Download JSON */}
          <a
            href={exportRepositoryArchitectureUrl(repositoryId, "json", selectedComponent || undefined)}
            download={`${repositoryName}_c4.json`}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition border border-slate-700"
          >
            <Code2 className="w-3.5 h-3.5" />
            Export JSON
          </a>
        </div>
      </div>

      {/* 2. C4 High-Level Summary Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800">
          <div className="flex items-center gap-2 text-slate-400 text-xs mb-1">
            <Box className="w-3.5 h-3.5 text-indigo-400" />
            Containers
          </div>
          <div className="text-lg font-bold text-white">{containers.length}</div>
          <div className="text-[11px] text-slate-500">Deployable Units</div>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800">
          <div className="flex items-center gap-2 text-slate-400 text-xs mb-1">
            <Cpu className="w-3.5 h-3.5 text-purple-400" />
            Components
          </div>
          <div className="text-lg font-bold text-white">{components.length}</div>
          <div className="text-[11px] text-slate-500">Modular Subsystems</div>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800">
          <div className="flex items-center gap-2 text-slate-400 text-xs mb-1">
            <Network className="w-3.5 h-3.5 text-emerald-400" />
            Relationships
          </div>
          <div className="text-lg font-bold text-white">{relationships.length}</div>
          <div className="text-[11px] text-slate-500">Verified Edge Links</div>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800">
          <div className="flex items-center gap-2 text-slate-400 text-xs mb-1">
            <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />
            Invariants &amp; Docs
          </div>
          <div className="text-lg font-bold text-white">{constraints.length}</div>
          <div className="text-[11px] text-slate-500">Design Invariants</div>
        </div>
      </div>

      {/* 3. Diagram Level Switcher & Viewer */}
      <div className="rounded-xl bg-slate-900/80 border border-slate-800 overflow-hidden">
        <div className="flex flex-wrap items-center justify-between border-b border-slate-800 bg-slate-950/60 px-4 py-2.5 gap-2">
          {/* Level Switcher Buttons */}
          <div className="flex items-center gap-1.5 overflow-x-auto">
            <button
              onClick={() => setActiveDiagramLevel("flowchart")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition flex items-center gap-1.5 ${
                activeDiagramLevel === "flowchart"
                  ? "bg-indigo-600 text-white font-semibold"
                  : "text-slate-400 hover:text-white hover:bg-slate-800/60"
              }`}
            >
              <Share2 className="w-3.5 h-3.5" />
              Dependency Flowchart
            </button>
            <button
              onClick={() => setActiveDiagramLevel("context")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition flex items-center gap-1.5 ${
                activeDiagramLevel === "context"
                  ? "bg-indigo-600 text-white font-semibold"
                  : "text-slate-400 hover:text-white hover:bg-slate-800/60"
              }`}
            >
              <Box className="w-3.5 h-3.5" />
              L1: System Context
            </button>
            <button
              onClick={() => setActiveDiagramLevel("container")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition flex items-center gap-1.5 ${
                activeDiagramLevel === "container"
                  ? "bg-indigo-600 text-white font-semibold"
                  : "text-slate-400 hover:text-white hover:bg-slate-800/60"
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              L2: Container Diagram
            </button>
            <button
              onClick={() => setActiveDiagramLevel("component")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition flex items-center gap-1.5 ${
                activeDiagramLevel === "component"
                  ? "bg-indigo-600 text-white font-semibold"
                  : "text-slate-400 hover:text-white hover:bg-slate-800/60"
              }`}
            >
              <Cpu className="w-3.5 h-3.5" />
              L3: Component Diagram
            </button>
            <button
              onClick={() => setActiveDiagramLevel("markdown")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition flex items-center gap-1.5 ${
                activeDiagramLevel === "markdown"
                  ? "bg-indigo-600 text-white font-semibold"
                  : "text-slate-400 hover:text-white hover:bg-slate-800/60"
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              Markdown Specification
            </button>
          </div>

          {/* Controls for Markdown view */}
          {activeDiagramLevel === "markdown" && (
            <div className="flex items-center gap-2">
              <div className="flex items-center rounded-lg bg-slate-900 p-0.5 border border-slate-800 text-xs">
                <button
                  onClick={() => setMarkdownViewMode("rendered")}
                  className={`flex items-center gap-1 px-2.5 py-1 rounded-md transition ${
                    markdownViewMode === "rendered"
                      ? "bg-indigo-600 text-white font-medium"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  <Eye className="w-3.5 h-3.5" />
                  Rendered Document
                </button>
                <button
                  onClick={() => setMarkdownViewMode("source")}
                  className={`flex items-center gap-1 px-2.5 py-1 rounded-md transition ${
                    markdownViewMode === "source"
                      ? "bg-indigo-600 text-white font-medium"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  <Code2 className="w-3.5 h-3.5" />
                  Raw Source
                </button>
              </div>

              <button
                onClick={() =>
                  handleCopy(c4Data.markdown_export || c4Data.markdownExport || "", setCopiedMarkdown)
                }
                className="flex items-center gap-1 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded text-xs text-slate-200 transition"
              >
                {copiedMarkdown ? (
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <Copy className="w-3.5 h-3.5" />
                )}
                {copiedMarkdown ? "Copied" : "Copy Markdown"}
              </button>
            </div>
          )}
        </div>

        {/* Display Pane */}
        {activeDiagramLevel === "markdown" ? (
          <div className="p-5 bg-slate-950 max-h-[650px] overflow-y-auto">
            {markdownViewMode === "rendered" ? (
              <MarkdownRenderer content={c4Data.markdown_export || c4Data.markdownExport || ""} />
            ) : (
              <pre className="whitespace-pre-wrap font-mono text-xs text-slate-300 leading-relaxed">
                {c4Data.markdown_export || c4Data.markdownExport}
              </pre>
            )}
          </div>
        ) : (
          <MermaidViewer
            chart={getCurrentDiagramCode()}
            title={getDiagramTitle()}
            className="border-0 rounded-none bg-slate-950"
          />
        )}
      </div>

      {/* 4. Container & Component Catalog */}
      <div className="space-y-4">
        <h4 className="text-sm font-semibold text-white flex items-center gap-2">
          <FolderTree className="w-4 h-4 text-indigo-400" />
          Container &amp; Component Inventory
        </h4>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {containers.map((c) => {
            const isExpanded = expandedContainer === c.id;
            return (
              <div
                key={c.id}
                className={`p-4 rounded-xl border transition ${
                  isExpanded
                    ? "bg-slate-900/90 border-indigo-500/40"
                    : "bg-slate-950/60 border-slate-800 hover:border-slate-700"
                }`}
              >
                <div
                  className="cursor-pointer"
                  onClick={() => setExpandedContainer(isExpanded ? null : c.id)}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <span className="text-sm font-semibold text-white">{c.name}</span>
                      <div className="text-[11px] font-mono text-indigo-400 mt-0.5">{c.technology}</div>
                    </div>
                    <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                      {c.container_type || c.containerType || "container"}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-2">{c.description}</p>
                  <div className="flex items-center justify-between text-xs text-slate-500 mt-3 pt-2 border-t border-slate-800">
                    <span>{c.components ? c.components.length : 0} Components</span>
                    <span className="text-indigo-400 hover:underline">
                      {isExpanded ? "Collapse" : "Inspect Components"}
                    </span>
                  </div>
                </div>

                {isExpanded && c.components && c.components.length > 0 && (
                  <div className="mt-4 pt-3 border-t border-slate-800/80 space-y-2">
                    {c.components.map((comp) => (
                      <div
                        key={comp.id}
                        className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs space-y-1.5"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-slate-200">{comp.name}</span>
                          <span className="text-[10px] font-mono text-slate-500">
                            {comp.file_count ?? comp.fileCount ?? 0} files &bull;{" "}
                            {comp.symbol_count ?? comp.symbolCount ?? 0} syms
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-400 font-mono truncate">
                          {comp.source_path || comp.sourcePath}
                        </div>
                        {comp.dependencies && comp.dependencies.length > 0 && (
                          <div className="flex items-center gap-1 flex-wrap pt-1">
                            <span className="text-[10px] text-slate-500">Dependencies:</span>
                            {comp.dependencies.map((dep, idx) => (
                              <span
                                key={idx}
                                className="text-[10px] px-1.5 py-0.5 rounded bg-slate-900 text-indigo-300 border border-indigo-500/20"
                              >
                                {dep}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* 5. Invariants Table (if available) */}
      {constraints.length > 0 && (
        <div className="space-y-3 pt-2">
          <h4 className="text-sm font-semibold text-white flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            Governing Architectural Invariants (Linked from Engineering Context)
          </h4>
          <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/80">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-900/80 text-slate-400 border-b border-slate-800 uppercase text-[10px]">
                <tr>
                  <th className="py-2.5 px-3">Domain</th>
                  <th className="py-2.5 px-3">Priority</th>
                  <th className="py-2.5 px-3">Invariant Statement</th>
                  <th className="py-2.5 px-3">Source Document</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans">
                {constraints.map((c, i) => (
                  <tr key={i} className="hover:bg-slate-900/40">
                    <td className="py-2.5 px-3 font-semibold text-indigo-400">{c.domain || "General"}</td>
                    <td className="py-2.5 px-3">
                      <span className="text-[10px] px-1.5 py-0.5 rounded font-mono font-bold bg-amber-500/10 text-amber-300 border border-amber-500/20">
                        {c.priority || "MUST"}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 leading-relaxed">{c.constraint_text || c.statement}</td>
                    <td className="py-2.5 px-3 font-mono text-[11px] text-slate-500">
                      {c.source_doc_path || "Repository Invariant"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
