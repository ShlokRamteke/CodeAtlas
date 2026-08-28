"use client";

import React, { useState, useEffect } from "react";
import type {
  Repository,
  ArchitectureOverview,
  SymbolItem,
  CodeDependencyItem,
  ContextBriefResponse,
} from "@archaeologist/contracts";
import {
  fetchRepositoryArchitecture,
  fetchRepositorySymbols,
  fetchRepositoryDependencies,
  fetchRepositoryContextBrief,
  ingestRepositoryFiles,
} from "@/lib/api";
import {
  Boxes,
  Code2,
  GitFork,
  CheckCircle2,
  Search,
  Layers,
  FileCode,
  Network,
  RefreshCw,
  FolderTree,
  UploadCloud,
  FilePlus,
  Play,
  Check,
  FileText,
  Copy,
  Sparkles,
} from "lucide-react";

interface ArchitectureExplorerProps {
  repository: Repository;
}

const TEMPLATES: Record<
  string,
  { label: string; desc: string; files: Record<string, string> }
> = {
  ecommerce: {
    label: "E-Commerce Checkout & Payment",
    desc: "TypeScript services with Order processing, Stripe payments, and linked tests",
    files: {
      "src/models/Order.ts": `export interface OrderItem {
  id: string;
  name: string;
  price: number;
  quantity: number;
}

export interface Order {
  id: string;
  userId: string;
  items: OrderItem[];
  totalAmount: number;
  status: 'pending' | 'paid' | 'shipped';
}`,
      "src/services/PaymentService.ts": `import { Order } from '../models/Order';
import stripe from 'stripe';

export interface PaymentReceipt {
  transactionId: string;
  success: boolean;
}

export class PaymentService {
  async processPayment(order: Order): Promise<PaymentReceipt> {
    // Process transaction
    return { transactionId: 'tx_123', success: true };
  }
}`,
      "src/services/PaymentService.test.ts": `import { PaymentService } from './PaymentService';
import { Order } from '../models/Order';

export const testPaymentSuccess = async () => {
  const service = new PaymentService();
  const sampleOrder: Order = {
    id: '1',
    userId: 'u1',
    items: [],
    totalAmount: 99.99,
    status: 'pending',
  };
  return await service.processPayment(sampleOrder);
};`,
      "src/services/CheckoutService.ts": `import { Order } from '../models/Order';
import { PaymentService } from './PaymentService';

export class CheckoutService {
  private paymentService: PaymentService;

  constructor() {
    this.paymentService = new PaymentService();
  }

  async executeCheckout(order: Order): Promise<boolean> {
    const result = await this.paymentService.processPayment(order);
    return result.success;
  }
}`,
    },
  },
  auth: {
    label: "Authentication & Token Engine",
    desc: "User credential verification, JWT token issuance, and unit tests",
    files: {
      "src/models/User.ts": `export interface User {
  id: string;
  email: string;
  role: 'admin' | 'user';
}`,
      "src/auth/AuthService.ts": `import { User } from '../models/User';
import jwt from 'jsonwebtoken';

export class AuthService {
  async login(email: string, pass: string): Promise<string> {
    return 'token_jwt_xyz';
  }

  verifyToken(token: string): boolean {
    return token.length > 10;
  }
}`,
      "src/auth/AuthService.test.ts": `import { AuthService } from './AuthService';

export const testLogin = async () => {
  const auth = new AuthService();
  return await auth.login('user@domain.com', 'secret');
};`,
    },
  },
  python_backend: {
    label: "Python FastAPI Backend",
    desc: "Python classes, async functions, docstrings, and test_*.py test files",
    files: {
      "app/services/analytics.py": `import os
from typing import List, Dict

class AnalyticsEngine:
    """Computes daily platform telemetry and metric trends."""

    def __init__(self, sample_rate: float = 1.0):
        self.sample_rate = sample_rate

    async def compute_aggregates(self, events: List[Dict]) -> Dict:
        """Calculate event summaries."""
        return {"count": len(events)}
`,
      "app/services/test_analytics.py": `from app.services.analytics import AnalyticsEngine

def test_aggregates():
    engine = AnalyticsEngine()
    assert engine.sample_rate == 1.0
`,
    },
  },
};

export function ArchitectureExplorer({ repository }: ArchitectureExplorerProps) {
  const [activeTab, setActiveTab] = useState<
    "components" | "symbols" | "relationships" | "briefing" | "ingest"
  >("components");
  const [architecture, setArchitecture] = useState<ArchitectureOverview | null>(null);
  const [symbols, setSymbols] = useState<SymbolItem[]>([]);
  const [symbolQuery, setSymbolQuery] = useState("");
  const [kindFilter, setKindFilter] = useState<string>("");
  const [dependencies, setDependencies] = useState<CodeDependencyItem[]>([]);
  const [contextBrief, setContextBrief] = useState<ContextBriefResponse | null>(null);
  const [selectedBriefComp, setSelectedBriefComp] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [ingesting, setIngesting] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [copiedLlm, setCopiedLlm] = useState(false);

  // Custom File Editor state for Ingest tab
  const [customPath, setCustomPath] = useState("src/utils/calculator.ts");
  const [customCode, setCustomCode] = useState(
    `export function calculateSum(a: number, b: number): number {\n  return a + b;\n}`
  );
  const [stagedFiles, setStagedFiles] = useState<Record<string, string>>({});

  useEffect(() => {
    loadData();
  }, [repository.id]);

  useEffect(() => {
    if (activeTab === "symbols") {
      fetchRepositorySymbols(
        repository.id,
        symbolQuery || undefined,
        kindFilter || undefined
      ).then(setSymbols);
    }
  }, [activeTab, symbolQuery, kindFilter, repository.id]);

  useEffect(() => {
    if (activeTab === "briefing") {
      fetchRepositoryContextBrief(repository.id, selectedBriefComp || undefined).then(
        setContextBrief
      );
    }
  }, [activeTab, selectedBriefComp, repository.id]);

  async function loadData() {
    setLoading(true);
    const [arch, deps, brief] = await Promise.all([
      fetchRepositoryArchitecture(repository.id),
      fetchRepositoryDependencies(repository.id),
      fetchRepositoryContextBrief(repository.id),
    ]);
    setArchitecture(arch);
    setDependencies(deps);
    setContextBrief(brief);
    setLoading(false);
  }

  async function handleIngestTemplate(templateKey: string) {
    setIngesting(true);
    setSuccessMsg(null);
    const tpl = TEMPLATES[templateKey];
    if (!tpl) return;

    const arch = await ingestRepositoryFiles(repository.id, tpl.files);
    if (arch) {
      setArchitecture(arch);
      await loadData();
      setSuccessMsg(`Successfully indexed ${tpl.label} (${arch.symbolCount} symbols extracted)`);
      setTimeout(() => {
        setActiveTab("components");
        setSuccessMsg(null);
      }, 1200);
    }
    setIngesting(false);
  }

  async function handleStageFile() {
    if (!customPath.trim() || !customCode.trim()) return;
    setStagedFiles({
      ...stagedFiles,
      [customPath.trim()]: customCode,
    });
    setCustomPath("");
    setCustomCode("");
  }

  async function handleIngestStaged() {
    if (Object.keys(stagedFiles).length === 0) return;
    setIngesting(true);
    setSuccessMsg(null);

    const arch = await ingestRepositoryFiles(repository.id, stagedFiles);
    if (arch) {
      setArchitecture(arch);
      setStagedFiles({});
      await loadData();
      setSuccessMsg(`Indexed ${arch.fileCount} custom files (${arch.symbolCount} symbols)!`);
      setTimeout(() => {
        setActiveTab("components");
        setSuccessMsg(null);
      }, 1200);
    }
    setIngesting(false);
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
      {/* Header Bar */}
      <div className="px-6 py-4 border-b border-slate-800 flex flex-wrap items-center justify-between gap-4 bg-slate-950/50">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-500/10 border border-indigo-500/20 rounded-lg text-indigo-400">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-white flex items-center gap-2">
              Current System Architecture
              <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
                Tree-sitter AST &bull; 100% Deterministic
              </span>
            </h3>
            <p className="text-xs text-slate-400">
              Symbol graphs, test relationships, and Context Builder briefings
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTab("briefing")}
            className="flex items-center gap-2 px-3 py-1.5 bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/30 rounded-lg text-xs font-medium transition"
          >
            <Sparkles className="w-3.5 h-3.5 text-purple-400" />
            Context Brief
          </button>
          <button
            onClick={() => setActiveTab("ingest")}
            className="flex items-center gap-2 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition shadow-sm"
          >
            <UploadCloud className="w-3.5 h-3.5" />
            Add / Index Code
          </button>
          <button
            onClick={loadData}
            disabled={loading}
            className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs transition"
            title="Refresh"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-6 bg-slate-900/60 border-b border-slate-800">
        <div className="bg-slate-950/40 p-3 rounded-lg border border-slate-800/80">
          <div className="text-xs text-slate-400 font-medium">Source Files</div>
          <div className="text-xl font-bold text-white mt-1">
            {architecture?.fileCount ?? repository.fileCount}
          </div>
        </div>
        <div className="bg-slate-950/40 p-3 rounded-lg border border-slate-800/80">
          <div className="text-xs text-slate-400 font-medium">AST Symbols</div>
          <div className="text-xl font-bold text-indigo-400 mt-1">
            {architecture?.symbolCount ?? repository.symbolCount}
          </div>
        </div>
        <div className="bg-slate-950/40 p-3 rounded-lg border border-slate-800/80">
          <div className="text-xs text-slate-400 font-medium">Dependencies</div>
          <div className="text-xl font-bold text-cyan-400 mt-1">
            {architecture?.dependencyCount ?? dependencies.length}
          </div>
        </div>
        <div className="bg-slate-950/40 p-3 rounded-lg border border-slate-800/80">
          <div className="text-xs text-slate-400 font-medium">Languages</div>
          <div className="text-sm font-semibold text-emerald-400 mt-1.5 flex gap-2 flex-wrap">
            {architecture && Object.keys(architecture.languages).length > 0 ? (
              Object.entries(architecture.languages).map(([lang, count]) => (
                <span key={lang} className="capitalize">
                  {lang} ({count})
                </span>
              ))
            ) : (
              <span className="text-slate-500">TypeScript / JS / Py</span>
            )}
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex border-b border-slate-800 px-6 bg-slate-950/20 text-xs font-medium text-slate-400 overflow-x-auto">
        <button
          onClick={() => setActiveTab("components")}
          className={`py-3 px-4 border-b-2 flex items-center gap-2 transition whitespace-nowrap ${
            activeTab === "components"
              ? "border-indigo-500 text-indigo-400 font-semibold"
              : "border-transparent hover:text-slate-200"
          }`}
        >
          <Boxes className="w-4 h-4" />
          Components ({architecture?.majorComponents.length || 0})
        </button>
        <button
          onClick={() => setActiveTab("symbols")}
          className={`py-3 px-4 border-b-2 flex items-center gap-2 transition whitespace-nowrap ${
            activeTab === "symbols"
              ? "border-indigo-500 text-indigo-400 font-semibold"
              : "border-transparent hover:text-slate-200"
          }`}
        >
          <Code2 className="w-4 h-4" />
          Symbols Outline
        </button>
        <button
          onClick={() => setActiveTab("relationships")}
          className={`py-3 px-4 border-b-2 flex items-center gap-2 transition whitespace-nowrap ${
            activeTab === "relationships"
              ? "border-indigo-500 text-indigo-400 font-semibold"
              : "border-transparent hover:text-slate-200"
          }`}
        >
          <Network className="w-4 h-4" />
          Relationships ({architecture?.relationships.length || 0})
        </button>
        <button
          onClick={() => setActiveTab("briefing")}
          className={`py-3 px-4 border-b-2 flex items-center gap-2 transition whitespace-nowrap ${
            activeTab === "briefing"
              ? "border-purple-500 text-purple-400 font-semibold"
              : "border-transparent hover:text-slate-200"
          }`}
        >
          <FileText className="w-4 h-4" />
          Context Briefing
        </button>
        <button
          onClick={() => setActiveTab("ingest")}
          className={`py-3 px-4 border-b-2 flex items-center gap-2 transition whitespace-nowrap ${
            activeTab === "ingest"
              ? "border-indigo-500 text-indigo-400 font-semibold"
              : "border-transparent hover:text-slate-200"
          }`}
        >
          <UploadCloud className="w-4 h-4" />
          Add / Index Code
        </button>
      </div>

      {/* Tab Content */}
      <div className="p-6 min-h-[320px]">
        {successMsg && (
          <div className="mb-4 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-2">
            <Check className="w-4 h-4" />
            {successMsg}
          </div>
        )}

        {loading ? (
          <div className="py-12 text-center text-slate-500 text-sm">
            Loading architecture graph...
          </div>
        ) : activeTab === "components" ? (
          <div>
            {!architecture || architecture.majorComponents.length === 0 ? (
              <div className="py-12 text-center">
                <FolderTree className="w-8 h-8 text-slate-600 mx-auto mb-3" />
                <p className="text-slate-400 text-sm font-medium">No components indexed yet.</p>
                <p className="text-slate-500 text-xs mt-1">
                  Click the <strong>&quot;Add / Index Code&quot;</strong> tab to load templates or custom code.
                </p>
                <button
                  onClick={() => setActiveTab("ingest")}
                  className="mt-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition"
                >
                  Choose Repository Template
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {architecture.majorComponents.map((comp) => (
                  <div
                    key={comp.path}
                    className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 transition"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="text-sm font-semibold text-white flex items-center gap-2">
                          <FileCode className="w-4 h-4 text-indigo-400" />
                          {comp.name}
                        </div>
                        <div className="text-xs font-mono text-slate-400 mt-0.5">{comp.path}</div>
                      </div>
                      <span className="text-xs px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 font-medium">
                        {comp.symbolCount} symbols
                      </span>
                    </div>

                    {/* Linked Tests */}
                    <div className="mt-3 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs">
                      <span className="text-slate-500">Test Relationship:</span>
                      {comp.testedBy ? (
                        <span className="text-emerald-400 flex items-center gap-1 font-mono text-[11px]">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          {comp.testedBy}
                        </span>
                      ) : (
                        <span className="text-slate-500 italic">No direct test match</span>
                      )}
                    </div>

                    {/* Dependencies */}
                    {comp.dependencies.length > 0 && (
                      <div className="mt-2 text-xs flex items-center gap-1.5 flex-wrap">
                        <span className="text-slate-500">Imports:</span>
                        {comp.dependencies.slice(0, 3).map((dep) => (
                          <span
                            key={dep}
                            className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[10px]"
                          >
                            {dep}
                          </span>
                        ))}
                        {comp.dependencies.length > 3 && (
                          <span className="text-slate-500 text-[10px]">
                            +{comp.dependencies.length - 3} more
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : activeTab === "symbols" ? (
          <div>
            {/* Search & Filters */}
            <div className="flex flex-wrap items-center gap-3 mb-4">
              <div className="relative flex-1 min-w-[200px]">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Filter symbols by name (e.g. AuthService, processPayment)..."
                  value={symbolQuery}
                  onChange={(e) => setSymbolQuery(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>
              <select
                value={kindFilter}
                onChange={(e) => setKindFilter(e.target.value)}
                className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
              >
                <option value="">All Symbol Kinds</option>
                <option value="class">Classes</option>
                <option value="function">Functions</option>
                <option value="interface">Interfaces</option>
                <option value="type">Types</option>
                <option value="method">Methods</option>
              </select>
            </div>

            {/* Symbols Table */}
            <div className="border border-slate-800 rounded-lg overflow-hidden">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-950 text-slate-400 font-semibold border-b border-slate-800">
                  <tr>
                    <th className="p-3">Symbol</th>
                    <th className="p-3">Kind</th>
                    <th className="p-3">Signature</th>
                    <th className="p-3 text-right">Lines</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 bg-slate-950/40">
                  {symbols.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="p-6 text-center text-slate-500">
                        No symbols match your filter.
                      </td>
                    </tr>
                  ) : (
                    symbols.map((sym) => (
                      <tr key={sym.id} className="hover:bg-slate-800/30 transition font-mono">
                        <td className="p-3 font-semibold text-white">{sym.name}</td>
                        <td className="p-3">
                          <span className="px-2 py-0.5 rounded-full text-[10px] uppercase font-bold bg-slate-800 text-indigo-300 border border-indigo-500/20">
                            {sym.kind}
                          </span>
                        </td>
                        <td className="p-3 text-slate-400 truncate max-w-xs">{sym.signature || "—"}</td>
                        <td className="p-3 text-right text-slate-500">
                          {sym.lineStart}-{sym.lineEnd}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        ) : activeTab === "relationships" ? (
          <div>
            {!architecture || architecture.relationships.length === 0 ? (
              <div className="py-12 text-center text-slate-500 text-sm">
                No relationship edges discovered yet.
              </div>
            ) : (
              <div className="space-y-2">
                {architecture.relationships.map((rel, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 flex items-center justify-between text-xs"
                  >
                    <div className="flex items-center gap-2 font-mono">
                      <span className="text-white font-semibold">{rel.sourceName}</span>
                      <span className="text-slate-500">({rel.sourcePath})</span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          rel.type === "tested_by"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"
                        }`}
                      >
                        {rel.type}
                      </span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
                        {rel.confidence ? `${Math.round(rel.confidence * 100)}%` : "100%"} conf
                      </span>
                      <GitFork className="w-3.5 h-3.5 text-slate-500" />
                    </div>

                    <div className="flex items-center gap-2 font-mono">
                      <span className="text-slate-300 font-semibold">{rel.targetName}</span>
                      <span className="text-slate-500">({rel.targetPath})</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : activeTab === "briefing" ? (
          /* Context Builder Briefing Tab */
          <div className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
              <div>
                <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-purple-400" />
                  Current-System Context Builder
                </h4>
                <p className="text-xs text-slate-400 mt-0.5">
                  Compact human briefing and token-efficient LLM prompt context block.
                </p>
              </div>

              {/* Component filter selector */}
              {contextBrief && contextBrief.components.length > 0 && (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400">Target Component:</span>
                  <select
                    value={selectedBriefComp}
                    onChange={(e) => setSelectedBriefComp(e.target.value)}
                    className="bg-slate-950 border border-slate-700 text-white text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-purple-500 font-mono"
                  >
                    <option value="">All Components Overview</option>
                    {contextBrief.components.map((c) => (
                      <option key={c.name} value={c.name}>
                        {c.name} ({c.symbolCount} symbols)
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            {/* Content Display: Split Human View & LLM Context Block */}
            {contextBrief ? (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* 1. Human Markdown Summary */}
                <div className="bg-slate-950/80 p-5 rounded-xl border border-slate-800 space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">
                      Human Briefing
                    </span>
                    <span className="text-[11px] px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                      Deterministic Facts
                    </span>
                  </div>

                  <div className="text-xs text-slate-300 whitespace-pre-wrap leading-relaxed font-sans">
                    {contextBrief.humanSummary}
                  </div>
                </div>

                {/* 2. Token-Efficient LLM Context Block */}
                <div className="bg-slate-950/80 p-5 rounded-xl border border-slate-800 space-y-4 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-semibold text-purple-400 uppercase tracking-wider">
                        LLM Context Block (Compact)
                      </span>
                      <button
                        onClick={() => {
                          navigator.clipboard.writeText(contextBrief.llmContext);
                          setCopiedLlm(true);
                          setTimeout(() => setCopiedLlm(false), 1500);
                        }}
                        className="flex items-center gap-1 px-2.5 py-1 bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/20 rounded text-[11px] text-purple-300 transition"
                      >
                        {copiedLlm ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                        {copiedLlm ? "Copied!" : "Copy Context Block"}
                      </button>
                    </div>

                    <pre className="p-3 bg-slate-900 rounded-lg text-[11px] font-mono text-purple-300/90 whitespace-pre-wrap leading-relaxed overflow-x-auto border border-purple-500/10">
                      {contextBrief.llmContext}
                    </pre>
                  </div>

                  <div className="text-[11px] text-slate-500 border-t border-slate-800/80 pt-3">
                    💡 This compact block is injected into reasoning prompts (Phases 4–5) without polluting LLM token context with raw repo source.
                  </div>
                </div>
              </div>
            ) : (
              <div className="py-12 text-center text-slate-500 text-sm">
                No context brief available yet. Index some code first!
              </div>
            )}
          </div>
        ) : (
          /* Ingest / Add Code Tab */
          <div className="space-y-8">
            {/* 1. Quick Ingest Templates */}
            <div>
              <h4 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
                <Play className="w-4 h-4 text-indigo-400" />
                Option 1: Load Pre-Built Codebase Templates
              </h4>
              <p className="text-xs text-slate-400 mb-4">
                Instant full-stack architectures with modules, interfaces, and test relationships.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {Object.entries(TEMPLATES).map(([key, tpl]) => (
                  <div
                    key={key}
                    className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 flex flex-col justify-between"
                  >
                    <div>
                      <h5 className="text-sm font-semibold text-white">{tpl.label}</h5>
                      <p className="text-xs text-slate-400 mt-1">{tpl.desc}</p>
                      <div className="text-[11px] font-mono text-slate-500 mt-2">
                        {Object.keys(tpl.files).length} files included
                      </div>
                    </div>

                    <button
                      onClick={() => handleIngestTemplate(key)}
                      disabled={ingesting}
                      className="mt-4 w-full py-2 bg-slate-800 hover:bg-indigo-600 disabled:opacity-50 text-white rounded-lg text-xs font-medium transition flex items-center justify-center gap-2"
                    >
                      <UploadCloud className="w-3.5 h-3.5" />
                      {ingesting ? "Indexing..." : "Load & Index Template"}
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* 2. Custom Code Editor */}
            <div className="pt-6 border-t border-slate-800">
              <h4 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
                <FilePlus className="w-4 h-4 text-indigo-400" />
                Option 2: Add Custom Code Files
              </h4>
              <p className="text-xs text-slate-400 mb-4">
                Paste any TypeScript, JavaScript, or Python code to parse with Tree-sitter.
              </p>

              <div className="space-y-3 bg-slate-950 p-4 rounded-xl border border-slate-800">
                <div>
                  <label className="text-xs text-slate-400 block mb-1">File Path:</label>
                  <input
                    type="text"
                    value={customPath}
                    onChange={(e) => setCustomPath(e.target.value)}
                    placeholder="e.g. src/services/PaymentService.ts or app/models.py"
                    className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="text-xs text-slate-400 block mb-1">Code Contents:</label>
                  <textarea
                    rows={6}
                    value={customCode}
                    onChange={(e) => setCustomCode(e.target.value)}
                    placeholder="Paste code here..."
                    className="w-full bg-slate-900 border border-slate-800 rounded-lg p-3 text-xs text-white font-mono focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div className="flex items-center justify-between pt-2">
                  <button
                    onClick={handleStageFile}
                    className="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-medium transition"
                  >
                    + Stage File ({Object.keys(stagedFiles).length} staged)
                  </button>

                  <button
                    onClick={async () => {
                      if (customPath && customCode) {
                        const files = { ...stagedFiles, [customPath]: customCode };
                        setIngesting(true);
                        const arch = await ingestRepositoryFiles(repository.id, files);
                        if (arch) {
                          setArchitecture(arch);
                          setStagedFiles({});
                          await loadData();
                          setSuccessMsg(`Successfully indexed files!`);
                          setTimeout(() => {
                            setActiveTab("components");
                            setSuccessMsg(null);
                          }, 1200);
                        }
                        setIngesting(false);
                      } else {
                        await handleIngestStaged();
                      }
                    }}
                    disabled={ingesting || (!customPath.trim() && Object.keys(stagedFiles).length === 0)}
                    className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-medium transition flex items-center gap-1.5 shadow-sm"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${ingesting ? "animate-spin" : ""}`} />
                    {ingesting ? "Parsing AST..." : "Parse & Index Now"}
                  </button>
                </div>

                {Object.keys(stagedFiles).length > 0 && (
                  <div className="mt-3 pt-3 border-t border-slate-800/80">
                    <div className="text-xs text-slate-400 font-medium mb-1">Staged Files:</div>
                    <ul className="text-xs font-mono text-indigo-400 space-y-1">
                      {Object.keys(stagedFiles).map((p) => (
                        <li key={p}>• {p}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
