"use client";

import React, { useState } from "react";
import { Copy, Check, FileCode, Layers } from "lucide-react";
import { MermaidViewer } from "./MermaidViewer";

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export function MarkdownRenderer({ content, className = "" }: MarkdownRendererProps) {
  // Helper to render inline markdown (bold, code, links)
  const renderInline = (text: string): React.ReactNode => {
    // Regex matches inline code `code`, bold **text**, and links [text](url)
    const tokens: React.ReactNode[] = [];
    let remaining = text;
    let key = 0;

    const regex = /(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\))/;

    while (remaining) {
      const match = remaining.match(regex);
      if (!match) {
        tokens.push(remaining);
        break;
      }

      const matchIndex = match.index ?? 0;
      if (matchIndex > 0) {
        tokens.push(remaining.substring(0, matchIndex));
      }

      const matchedStr = match[0];
      if (matchedStr.startsWith("`") && matchedStr.endsWith("`")) {
        tokens.push(
          <code
            key={key++}
            className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-700/60 font-mono text-[11px] text-indigo-300"
          >
            {matchedStr.slice(1, -1)}
          </code>
        );
      } else if (matchedStr.startsWith("**") && matchedStr.endsWith("**")) {
        tokens.push(
          <strong key={key++} className="font-semibold text-white">
            {matchedStr.slice(2, -2)}
          </strong>
        );
      } else if (matchedStr.startsWith("[") && matchedStr.includes("](")) {
        const linkMatch = matchedStr.match(/\[([^\]]+)\]\(([^)]+)\)/);
        if (linkMatch) {
          tokens.push(
            <a
              key={key++}
              href={linkMatch[2]}
              target="_blank"
              rel="noopener noreferrer"
              className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2"
            >
              {linkMatch[1]}
            </a>
          );
        } else {
          tokens.push(matchedStr);
        }
      }

      remaining = remaining.substring(matchIndex + matchedStr.length);
    }

    return <>{tokens}</>;
  };

  // Parse lines into structured blocks
  const renderBlocks = () => {
    const lines = content.split("\n");
    const blocks: React.ReactNode[] = [];
    let i = 0;

    while (i < lines.length) {
      const line = lines[i];

      // 1. Code blocks (```lang ... ```)
      if (line.trim().startsWith("```")) {
        const lang = line.trim().slice(3).trim();
        const codeLines: string[] = [];
        i++;
        while (i < lines.length && !lines[i].trim().startsWith("```")) {
          codeLines.push(lines[i]);
          i++;
        }
        i++; // skip closing ```
        const codeStr = codeLines.join("\n");
        const isMermaid = lang === "mermaid";

        blocks.push(
          <CodeBlockItem key={`code-${i}`} lang={lang} code={codeStr} isMermaid={isMermaid} />
        );
        continue;
      }

      // 2. Table (| Col 1 | Col 2 |)
      if (line.trim().startsWith("|") && line.trim().endsWith("|")) {
        const tableLines: string[] = [];
        while (i < lines.length && lines[i].trim().startsWith("|") && lines[i].trim().endsWith("|")) {
          tableLines.push(lines[i].trim());
          i++;
        }

        if (tableLines.length >= 2) {
          const headerCells = tableLines[0]
            .split("|")
            .slice(1, -1)
            .map((c) => c.trim());
          // tableLines[1] is separator (e.g. | :--- | :--- |)
          const dataRows = tableLines.slice(2).map((rowLine) =>
            rowLine
              .split("|")
              .slice(1, -1)
              .map((c) => c.trim())
          );

          blocks.push(
            <div key={`table-${i}`} className="my-4 overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/80 shadow-sm">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-900/90 text-slate-400 border-b border-slate-800 uppercase text-[10px] tracking-wider">
                  <tr>
                    {headerCells.map((h, hIdx) => (
                      <th key={hIdx} className="py-2.5 px-3.5 font-semibold text-slate-300">
                        {renderInline(h)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-sans">
                  {dataRows.map((row, rIdx) => (
                    <tr key={rIdx} className="hover:bg-slate-900/40 transition">
                      {row.map((cell, cIdx) => (
                        <td key={cIdx} className="py-2 px-3.5 leading-relaxed align-top">
                          {renderInline(cell)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }
        continue;
      }

      // 3. Blockquotes (> ...)
      if (line.trim().startsWith(">")) {
        const quoteLines: string[] = [];
        while (i < lines.length && lines[i].trim().startsWith(">")) {
          quoteLines.push(lines[i].trim().replace(/^>\s?/, ""));
          i++;
        }
        blocks.push(
          <div
            key={`quote-${i}`}
            className="my-3 p-3.5 rounded-r-xl border-l-4 border-indigo-500 bg-indigo-500/10 text-xs text-indigo-200 leading-relaxed font-sans"
          >
            {quoteLines.map((ql, qIdx) => (
              <p key={qIdx}>{renderInline(ql)}</p>
            ))}
          </div>
        );
        continue;
      }

      // 4. Headings
      if (line.startsWith("# ")) {
        blocks.push(
          <h1 key={`h1-${i}`} className="text-xl font-bold text-white tracking-tight mt-6 mb-3 pb-2 border-b border-slate-800 flex items-center gap-2">
            {renderInline(line.slice(2).trim())}
          </h1>
        );
        i++;
        continue;
      }
      if (line.startsWith("## ")) {
        blocks.push(
          <h2 key={`h2-${i}`} className="text-base font-bold text-indigo-300 tracking-tight mt-5 mb-2.5 pb-1.5 border-b border-slate-800/70 flex items-center gap-2">
            {renderInline(line.slice(3).trim())}
          </h2>
        );
        i++;
        continue;
      }
      if (line.startsWith("### ")) {
        blocks.push(
          <h3 key={`h3-${i}`} className="text-sm font-semibold text-white mt-4 mb-2">
            {renderInline(line.slice(4).trim())}
          </h3>
        );
        i++;
        continue;
      }
      if (line.startsWith("#### ")) {
        blocks.push(
          <h4 key={`h4-${i}`} className="text-xs font-semibold text-slate-300 mt-3 mb-1.5">
            {renderInline(line.slice(5).trim())}
          </h4>
        );
        i++;
        continue;
      }

      // 5. Unordered list (- or *)
      if (line.trim().startsWith("- ") || line.trim().startsWith("* ")) {
        const listItems: string[] = [];
        while (i < lines.length && (lines[i].trim().startsWith("- ") || lines[i].trim().startsWith("* "))) {
          listItems.push(lines[i].trim().slice(2));
          i++;
        }
        blocks.push(
          <ul key={`ul-${i}`} className="my-2.5 space-y-1 pl-4 list-disc marker:text-indigo-400 text-xs text-slate-300 font-sans">
            {listItems.map((item, itemIdx) => (
              <li key={itemIdx}>{renderInline(item)}</li>
            ))}
          </ul>
        );
        continue;
      }

      // 6. Horizontal rule
      if (line.trim() === "---" || line.trim() === "***") {
        blocks.push(<hr key={`hr-${i}`} className="my-5 border-slate-800" />);
        i++;
        continue;
      }

      // 7. Regular paragraph / empty line
      if (line.trim() === "") {
        i++;
        continue;
      }

      blocks.push(
        <p key={`p-${i}`} className="my-1.5 text-xs text-slate-300 leading-relaxed font-sans">
          {renderInline(line)}
        </p>
      );
      i++;
    }

    return blocks;
  };

  return <div className={`space-y-1 ${className}`}>{renderBlocks()}</div>;
}

function CodeBlockItem({ lang, code, isMermaid }: { lang: string; code: string; isMermaid: boolean }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isMermaid) {
    return <MermaidViewer chart={code} title="Mermaid Architecture Diagram" className="my-4" />;
  }

  return (
    <div className="my-4 rounded-xl border border-slate-800 bg-slate-950 overflow-hidden shadow-sm">
      <div className="flex items-center justify-between px-3.5 py-2 bg-slate-900/90 border-b border-slate-800/80">
        <div className="flex items-center gap-2">
          {isMermaid ? (
            <Layers className="w-3.5 h-3.5 text-cyan-400" />
          ) : (
            <FileCode className="w-3.5 h-3.5 text-slate-400" />
          )}
          <span className="text-[11px] font-mono font-medium text-slate-300">
            {isMermaid ? "Mermaid Architecture Diagram" : lang || "code"}
          </span>
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
        >
          {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
          {copied ? "Copied" : isMermaid ? "Copy Diagram" : "Copy"}
        </button>
      </div>
      <pre className={`p-4 font-mono text-xs overflow-x-auto whitespace-pre leading-relaxed ${
        isMermaid ? "text-cyan-300 bg-slate-950/90" : "text-slate-200 bg-slate-950"
      }`}>
        {code}
      </pre>
    </div>
  );
}
