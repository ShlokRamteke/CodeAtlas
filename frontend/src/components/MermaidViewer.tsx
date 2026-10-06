"use client";

import React, { useEffect, useRef, useState } from "react";
import { Copy, Check, Download, AlertCircle, RefreshCw, Code2, Eye } from "lucide-react";

interface MermaidViewerProps {
  chart: string;
  className?: string;
  title?: string;
}

function sanitizeMermaidSource(source: string): string {
  if (!source) return "";
  // Sanitize flowchart edge labels |...| to eliminate unescaped parens/arrows/brackets
  return source.replace(/(-->|---|==>|-\.->|--)\s*\|([^|\r\n]+)\|/g, (match, arrow, label) => {
    const cleanLabel = label
      .replace(/[\(\)\[\]\{\}]/g, "")
      .replace(/-+>+/g, " to ")
      .replace(/"/g, "'")
      .trim();
    return `${arrow}|${cleanLabel}|`;
  });
}

export function MermaidViewer({ chart, className = "", title }: MermaidViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svgHtml, setSvgHtml] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<"visual" | "code">("visual");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let isMounted = true;

    async function renderChart() {
      if (!chart.trim()) {
        setSvgHtml("");
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const mermaidModule = await import("mermaid");
        const mermaid = mermaidModule.default;

        mermaid.initialize({
          startOnLoad: false,
          theme: "dark",
          themeVariables: {
            darkMode: true,
            background: "#020617",
            primaryColor: "#4f46e5",
            primaryTextColor: "#f8fafc",
            primaryBorderColor: "#6366f1",
            lineColor: "#64748b",
            secondaryColor: "#0f172a",
            tertiaryColor: "#1e293b",
          },
          securityLevel: "loose",
          fontFamily: "ui-sans-serif, system-ui, sans-serif",
        });

        const cleanChart = sanitizeMermaidSource(chart);
        // Generate clean unique ID
        const id = `mermaid_${Math.random().toString(36).substring(2, 9)}`;
        const { svg } = await mermaid.render(id, cleanChart);

        if (isMounted) {
          setSvgHtml(svg);
          setLoading(false);
        }
      } catch (err: any) {
        if (isMounted) {
          console.warn("Mermaid render error:", err);
          setError(err.message || "Failed to render Mermaid diagram.");
          setLoading(false);
        }
      }
    }

    renderChart();

    return () => {
      isMounted = false;
    };
  }, [chart]);

  const handleCopy = () => {
    navigator.clipboard.writeText(chart);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadSvg = () => {
    if (!svgHtml) return;
    const blob = new Blob([svgHtml], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title || "architecture_diagram"}.svg`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className={`flex flex-col bg-slate-950 overflow-hidden ${className ? className : "rounded-xl border border-slate-800 shadow-sm"}`}>
      {/* Header Controls */}
      <div className="flex flex-wrap items-center justify-between px-4 py-2.5 bg-slate-900/90 border-b border-slate-800 gap-2">
        <div className="flex items-center gap-2">
          {title && <span className="text-xs font-semibold text-white">{title}</span>}
          {/* Mode Switcher */}
          <div className="flex items-center rounded-lg bg-slate-950 p-0.5 border border-slate-800 text-xs">
            <button
              onClick={() => setViewMode("visual")}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-md transition ${
                viewMode === "visual"
                  ? "bg-indigo-600 text-white font-medium"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              <Eye className="w-3.5 h-3.5" />
              Rendered Diagram
            </button>
            <button
              onClick={() => setViewMode("code")}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-md transition ${
                viewMode === "code"
                  ? "bg-indigo-600 text-white font-medium"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              <Code2 className="w-3.5 h-3.5" />
              Mermaid Source
            </button>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          {svgHtml && viewMode === "visual" && (
            <button
              onClick={handleDownloadSvg}
              className="flex items-center gap-1 px-2.5 py-1 rounded text-xs bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 transition"
              title="Download diagram as SVG"
            >
              <Download className="w-3.5 h-3.5" />
              SVG
            </button>
          )}
          <button
            onClick={handleCopy}
            className="flex items-center gap-1 px-2.5 py-1 rounded text-xs bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 transition"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            {copied ? "Copied" : "Copy Code"}
          </button>
        </div>
      </div>

      {/* Content View */}
      <div className="p-4 overflow-auto max-h-[600px] flex items-center justify-center bg-slate-950">
        {viewMode === "code" ? (
          <pre className="w-full font-mono text-xs text-cyan-300 whitespace-pre leading-relaxed overflow-x-auto">
            {chart}
          </pre>
        ) : loading ? (
          <div className="py-16 flex flex-col items-center justify-center space-y-2 text-slate-400 text-xs">
            <RefreshCw className="w-6 h-6 animate-spin text-indigo-400" />
            <span>Rendering diagram...</span>
          </div>
        ) : error ? (
          <div className="w-full p-4 rounded-lg bg-rose-500/10 border border-rose-500/20 text-xs space-y-2">
            <div className="flex items-center gap-2 text-rose-400 font-semibold">
              <AlertCircle className="w-4 h-4" />
              Diagram Rendering Notice
            </div>
            <p className="text-slate-300 font-mono text-[11px] whitespace-pre-wrap">{error}</p>
            <div className="pt-2 border-t border-rose-500/20">
              <span className="text-slate-400">Mermaid Syntax Source:</span>
              <pre className="mt-1 p-2 rounded bg-slate-900 text-slate-300 text-[11px] overflow-x-auto">
                {chart}
              </pre>
            </div>
          </div>
        ) : (
          <div
            ref={containerRef}
            className="w-full flex justify-center items-center [&_svg]:max-w-full [&_svg]:h-auto [&_svg]:rounded-lg"
            dangerouslySetInnerHTML={{ __html: svgHtml }}
          />
        )}
      </div>
    </div>
  );
}
