"use client";

import React, { useState, useEffect } from "react";
import type {
  Repository,
  ArchitectureOverview,
  SymbolItem,
  CodeDependencyItem,
  ProjectContext,
  CommitItem,
  FileHistoryResponse,
} from "@archaeologist/contracts";
import {
  fetchRepositoryArchitecture,
  fetchRepositorySymbols,
  fetchRepositoryDependencies,
  fetchProjectContext,
  fetchRepositoryCommits,
  fetchFileHistory,
  ingestRepositoryCommits,
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
  AlertTriangle,
  ShieldCheck,
  HelpCircle,
  FileCheck,
  GitCommit,
  History,
  Calendar,
  User,
  PlusCircle,
  Tag,
} from "lucide-react";

interface ArchitectureExplorerProps {
  repository: Repository;
}

const TEMPLATES: Record<
  string,
  { label: string; desc: string; files: Record<string, string>; commits?: any[] }
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
    commits: [
      {
        commit_hash: "a1b2c3d4",
        author_name: "Alice Developer",
        author_email: "alice@payments.io",
        committed_at: "2025-01-15T10:00:00Z",
        message: "feat(models): introduce initial Order and Payment models (#1)",
        file_changes: [
          { file_path: "src/models/Order.ts", change_type: "added", insertions: 15, deletions: 0 },
        ],
      },
      {
        commit_hash: "e5f6a7b8",
        author_name: "Bob Engineer",
        author_email: "bob@payments.io",
        committed_at: "2025-02-10T14:30:00Z",
        message: "feat(services): implement PaymentService and Stripe connector (#12)",
        file_changes: [
          { file_path: "src/services/PaymentService.ts", change_type: "added", insertions: 22, deletions: 0 },
          { file_path: "src/services/PaymentService.test.ts", change_type: "added", insertions: 18, deletions: 0 },
        ],
      },
      {
        commit_hash: "9c0d1e2f",
        author_name: "Alice Developer",
        author_email: "alice@payments.io",
        committed_at: "2025-03-01T09:15:00Z",
        message: "feat(checkout): add CheckoutService integration (#45)",
        file_changes: [
          { file_path: "src/services/CheckoutService.ts", change_type: "added", insertions: 19, deletions: 0 },
          { file_path: "src/services/PaymentService.ts", change_type: "modified", insertions: 4, deletions: 1 },
        ],
      },
    ],
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
    commits: [
      {
        commit_hash: "11aa22bb",
        author_name: "Security Lead",
        author_email: "security@company.com",
        committed_at: "2024-11-20T08:00:00Z",
        message: "feat(auth): initial JWT token issuance and user verification (#101)",
        file_changes: [
          { file_path: "src/models/User.ts", change_type: "added", insertions: 8, deletions: 0 },
          { file_path: "src/auth/AuthService.ts", change_type: "added", insertions: 25, deletions: 0 },
          { file_path: "src/auth/AuthService.test.ts", change_type: "added", insertions: 14, deletions: 0 },
        ],
      },
    ],
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
    commits: [
      {
        commit_hash: "py_init_01",
        author_name: "Data Engineer",
        author_email: "data@python.org",
        committed_at: "2025-01-01T12:00:00Z",
        message: "feat(analytics): bootstrap analytics aggregation engine",
        file_changes: [
          { file_path: "app/services/analytics.py", change_type: "added", insertions: 15, deletions: 0 },
          { file_path: "app/services/test_analytics.py", change_type: "added", insertions: 10, deletions: 0 },
        ],
      },
    ],
  },
};

export function ArchitectureExplorer({ repository }: ArchitectureExplorerProps) {
  const [activeTab, setActiveTab] = useState<
    "components" | "symbols" | "relationships" | "project_context" | "git_history" | "ingest"
  >("components");
  const [architecture, setArchitecture] = useState<ArchitectureOverview | null>(null);
  const [symbols, setSymbols] = useState<SymbolItem[]>([]);
  const [symbolQuery, setSymbolQuery] = useState("");
  const [kindFilter, setKindFilter] = useState<string>("");
  const [dependencies, setDependencies] = useState<CodeDependencyItem[]>([]);
  const [projectContext, setProjectContext] = useState<ProjectContext | null>(null);
  const [selectedContextComp, setSelectedContextComp] = useState<string>("");
  const [commits, setCommits] = useState<CommitItem[]>([]);
  const [selectedHistoryFile, setSelectedHistoryFile] = useState<string>("");
  const [fileHistory, setFileHistory] = useState<FileHistoryResponse | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
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
    if (activeTab === "project_context") {
      fetchProjectContext(repository.id, selectedContextComp || undefined).then(
        setProjectContext
      );
    }
  }, [activeTab, selectedContextComp, repository.id]);

  useEffect(() => {
    if (activeTab === "git_history") {
      loadHistory();
    }
  }, [activeTab, repository.id]);

  useEffect(() => {
    if (selectedHistoryFile) {
      setHistoryLoading(true);
      fetchFileHistory(repository.id, selectedHistoryFile).then((res) => {
        setFileHistory(res);
        setHistoryLoading(false);
      });
    }
  }, [selectedHistoryFile, repository.id]);

  async function loadData() {
    setLoading(true);
    const [arch, deps, pCtx, cList] = await Promise.all([
      fetchRepositoryArchitecture(repository.id),
      fetchRepositoryDependencies(repository.id),
      fetchProjectContext(repository.id),
      fetchRepositoryCommits(repository.id),
    ]);
    setArchitecture(arch);
    setDependencies(deps);
    setProjectContext(pCtx);
    setCommits(cList);
    setLoading(false);
  }

  async function loadHistory() {
    const cList = await fetchRepositoryCommits(repository.id);
    setCommits(cList);
  }

  async function handleIngestTemplate(templateKey: string) {
    setIngesting(true);
    setSuccessMsg(null);
    const tpl = TEMPLATES[templateKey];
    if (!tpl) return;

    const arch = await ingestRepositoryFiles(repository.id, tpl.files);
    if (tpl.commits && tpl.commits.length > 0) {
      await ingestRepositoryCommits(repository.id, tpl.commits);
    }

    if (arch) {
      setArchitecture(arch);
      await loadData();
      setSuccessMsg(`Successfully indexed ${tpl.label} (${arch.symbolCount} symbols, ${tpl.commits?.length || 0} commits)`);
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
                Unified ProjectContext &bull; 100% Deterministic
              </span>
            </h3>
            <p className="text-xs text-slate-400">
              Single canonical context layer powering both Human UI and AI/Agent prompt pipelines
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTab("git_history")}
            className="flex items-center gap-2 px-3 py-1.5 bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded-lg text-xs font-medium transition"
          >
            <GitCommit className="w-3.5 h-3.5 text-amber-400" />
            Git History ({commits.length})
          </button>
          <button
            onClick={() => setActiveTab("project_context")}
            className="flex items-center gap-2 px-3 py-1.5 bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/30 rounded-lg text-xs font-medium transition"
          >
            <Sparkles className="w-3.5 h-3.5 text-purple-400" />
            Project Context
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
          <div className="text-xs text-slate-400 font-medium">Git Commits</div>
          <div className="text-xl font-bold text-amber-400 mt-1">
            {commits.length}
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
          onClick={() => setActiveTab("git_history")}
          className={`py-3 px-4 border-b-2 flex items-center gap-2 transition whitespace-nowrap ${
            activeTab === "git_history"
              ? "border-amber-500 text-amber-400 font-semibold"
              : "border-transparent hover:text-slate-200"
          }`}
        >
          <GitCommit className="w-4 h-4" />
          Git History ({commits.length})
        </button>
        <button
          onClick={() => setActiveTab("project_context")}
          className={`py-3 px-4 border-b-2 flex items-center gap-2 transition whitespace-nowrap ${
            activeTab === "project_context"
              ? "border-purple-500 text-purple-400 font-semibold"
              : "border-transparent hover:text-slate-200"
          }`}
        >
          <FileText className="w-4 h-4" />
          Unified ProjectContext
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
        ) : activeTab === "git_history" ? (
          /* Git History & File Evolution Tab */
          <div className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
              <div>
                <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                  <GitCommit className="w-4 h-4 text-amber-400" />
                  Deterministic Git History Index
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
                    PH3-01 Dataset
                  </span>
                </h4>
                <p className="text-xs text-slate-400 mt-0.5">
                  Trace commit origins, changed files, author timelines, and introducing commits.
                </p>
              </div>

              {/* File / Component filter for introducing commit discovery */}
              {architecture && (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400">File Evolution:</span>
                  <select
                    value={selectedHistoryFile}
                    onChange={(e) => setSelectedHistoryFile(e.target.value)}
                    className="bg-slate-950 border border-slate-700 text-white text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-amber-500 font-mono"
                  >
                    <option value="">Select File to Trace Origins</option>
                    {architecture.majorComponents.map((c) => (
                      <option key={c.path} value={c.path}>
                        {c.path} ({c.name})
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            {/* If a file is selected for history analysis */}
            {selectedHistoryFile && (
              <div className="p-4 rounded-xl bg-slate-950/80 border border-amber-500/30 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <FileCode className="w-4 h-4 text-amber-400" />
                    <span className="text-xs font-semibold text-white font-mono">{selectedHistoryFile}</span>
                  </div>
                  <span className="text-[11px] px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
                    {fileHistory ? `${fileHistory.totalCommits} changes tracked` : "Loading..."}
                  </span>
                </div>

                {fileHistory?.introducingCommit ? (
                  <div className="p-3 bg-emerald-950/30 border border-emerald-500/30 rounded-lg flex items-start gap-3">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <div className="text-xs font-bold text-emerald-400 flex items-center gap-2">
                        Introducing Commit (Origin)
                        <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-emerald-900/50 text-emerald-300">
                          {fileHistory.introducingCommit.commit_hash.slice(0, 7)}
                        </span>
                      </div>
                      <div className="text-xs text-slate-200 mt-1 font-medium">
                        {fileHistory.introducingCommit.message}
                      </div>
                      <div className="text-[11px] text-slate-400 mt-1 flex items-center gap-3">
                        <span>Author: <strong>{fileHistory.introducingCommit.author_name}</strong></span>
                        <span>Date: {fileHistory.introducingCommit.committed_at.slice(0, 10)}</span>
                        <span className="text-emerald-300 font-mono">+{fileHistory.introducingCommit.insertions} lines</span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-xs text-slate-500 italic">No introducing commit record indexed.</div>
                )}
              </div>
            )}

            {/* Commits Feed */}
            {commits.length === 0 ? (
              <div className="py-12 text-center">
                <History className="w-8 h-8 text-slate-600 mx-auto mb-3" />
                <p className="text-slate-400 text-sm font-medium">No Git commits indexed yet.</p>
                <p className="text-slate-500 text-xs mt-1">
                  Connect a public GitHub repository or load an architecture template.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {commits.map((c) => (
                  <div
                    key={c.id || c.commitHash}
                    className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 transition space-y-2"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="space-y-1">
                        <div className="text-xs font-semibold text-white leading-snug">
                          {c.message}
                        </div>
                        <div className="flex items-center gap-3 text-[11px] text-slate-400 flex-wrap">
                          <span className="flex items-center gap-1">
                            <User className="w-3 h-3 text-slate-500" />
                            {c.authorName}
                          </span>
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3 h-3 text-slate-500" />
                            {c.committedAt.slice(0, 10)}
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 flex-shrink-0">
                        <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-slate-800 text-indigo-300 border border-slate-700">
                          {c.commitHash.slice(0, 7)}
                        </span>
                        {c.insertions !== undefined && (
                          <span className="text-[10px] font-mono text-emerald-400">+{c.insertions}</span>
                        )}
                        {c.deletions !== undefined && (
                          <span className="text-[10px] font-mono text-red-400">-{c.deletions}</span>
                        )}
                      </div>
                    </div>

                    {c.fileChanges && c.fileChanges.length > 0 && (
                      <div className="pt-2 border-t border-slate-800/80 flex items-center gap-2 flex-wrap">
                        <span className="text-[11px] text-slate-500">Changed Files:</span>
                        {c.fileChanges.map((fc, idx) => (
                          <span
                            key={idx}
                            onClick={() => setSelectedHistoryFile(fc.filePath)}
                            className="cursor-pointer px-1.5 py-0.5 rounded bg-slate-900 hover:bg-slate-800 text-slate-300 font-mono text-[10px] border border-slate-800 hover:border-slate-600 transition"
                          >
                            {fc.filePath} ({fc.changeType})
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : activeTab === "project_context" ? (
          /* Canonical Unified ProjectContext Tab */
          <div className="space-y-6">
            {/* Target Header Bar */}
            <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
              <div>
                <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-purple-400" />
                  Canonical ProjectContext
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20">
                    Single Knowledge Source
                  </span>
                </h4>
                <p className="text-xs text-slate-400 mt-0.5">
                  One structured context model shared between Human UI and AI/Agent reasoning.
                </p>
              </div>

              {/* Component Scope Filter */}
              {architecture && architecture.majorComponents.length > 0 && (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400">Context Scope:</span>
                  <select
                    value={selectedContextComp}
                    onChange={(e) => setSelectedContextComp(e.target.value)}
                    className="bg-slate-950 border border-slate-700 text-white text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-purple-500 font-mono"
                  >
                    <option value="">Full Repository Context</option>
                    {architecture.majorComponents.map((c) => (
                      <option key={c.path} value={c.path}>
                        Component: {c.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            {projectContext ? (
              <div className="space-y-6">
                {/* Meta & Provenance Pill Bar */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 bg-slate-950/60 p-3.5 rounded-xl border border-slate-800">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                    <div>
                      <div className="text-[10px] text-slate-500 uppercase font-semibold">Confidence</div>
                      <div className="text-xs font-bold text-emerald-400">
                        {Math.round(projectContext.confidence * 100)}% Verified
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <FileCheck className="w-4 h-4 text-indigo-400 flex-shrink-0" />
                    <div>
                      <div className="text-[10px] text-slate-500 uppercase font-semibold">Entities &amp; Edges</div>
                      <div className="text-xs font-bold text-white">
                        {projectContext.entities.length} entities &bull; {projectContext.relationships.length} rels
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <HelpCircle className="w-4 h-4 text-amber-400 flex-shrink-0" />
                    <div>
                      <div className="text-[10px] text-slate-500 uppercase font-semibold">Identified Unknowns</div>
                      <div className="text-xs font-bold text-amber-400">
                        {projectContext.unknowns.length} gaps flagged
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <FileCode className="w-4 h-4 text-cyan-400 flex-shrink-0" />
                    <div>
                      <div className="text-[10px] text-slate-500 uppercase font-semibold">Provenance</div>
                      <div className="text-xs font-mono font-medium text-cyan-300 truncate">
                        {projectContext.provenance}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Dual Views: Human Markdown vs AI/Agent Prompt */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* 1. Human UI View */}
                  <div className="bg-slate-950/80 p-5 rounded-xl border border-slate-800 space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider flex items-center gap-1.5">
                        <FileText className="w-3.5 h-3.5" />
                        Human UI View (Markdown Projection)
                      </span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                        Rendered for Developer
                      </span>
                    </div>

                    <div className="text-xs text-slate-300 whitespace-pre-wrap leading-relaxed font-sans max-h-[420px] overflow-y-auto pr-2">
                      {projectContext.humanMarkdown}
                    </div>
                  </div>

                  {/* 2. AI / Agent Context Block */}
                  <div className="bg-slate-950/80 p-5 rounded-xl border border-slate-800 space-y-4 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-semibold text-purple-400 uppercase tracking-wider flex items-center gap-1.5">
                          <Sparkles className="w-3.5 h-3.5" />
                          AI / Agent Projection (Token-Efficient)
                        </span>
                        <button
                          onClick={() => {
                            navigator.clipboard.writeText(projectContext.llmPromptContext);
                            setCopiedLlm(true);
                            setTimeout(() => setCopiedLlm(false), 1500);
                          }}
                          className="flex items-center gap-1 px-2.5 py-1 bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/20 rounded text-[11px] text-purple-300 transition"
                        >
                          {copiedLlm ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                          {copiedLlm ? "Copied!" : "Copy Agent Prompt"}
                        </button>
                      </div>

                      <pre className="p-3 bg-slate-900 rounded-lg text-[11px] font-mono text-purple-300/90 whitespace-pre-wrap leading-relaxed overflow-x-auto max-h-[380px] border border-purple-500/10">
                        {projectContext.llmPromptContext}
                      </pre>
                    </div>

                    <div className="text-[11px] text-slate-500 border-t border-slate-800/80 pt-3">
                      💡 <strong>Unified Pipeline:</strong> Both Human UI and LLM reasoning consume this exact same <code>ProjectContext</code> structure.
                    </div>
                  </div>
                </div>

                {/* Unknowns & Architectural Gaps Panel */}
                {projectContext.unknowns.length > 0 && (
                  <div className="bg-slate-950/80 p-5 rounded-xl border border-amber-500/20">
                    <h5 className="text-xs font-semibold text-amber-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4" />
                      Identified Uncertainties &amp; Gaps ({projectContext.unknowns.length})
                    </h5>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {projectContext.unknowns.map((u, i) => (
                        <div
                          key={i}
                          className="p-3 rounded-lg bg-slate-900 border border-slate-800 flex items-start gap-2 text-xs"
                        >
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] uppercase font-bold flex-shrink-0 ${
                              u.severity === "high"
                                ? "bg-red-500/10 text-red-400 border border-red-500/20"
                                : u.severity === "medium"
                                ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                                : "bg-slate-800 text-slate-400"
                            }`}
                          >
                            {u.kind}
                          </span>
                          <div>
                            <div className="font-mono text-white font-medium">{u.target}</div>
                            <div className="text-slate-400 text-[11px] mt-0.5">{u.description}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="py-12 text-center text-slate-500 text-sm">
                No ProjectContext generated yet. Index repository code to inspect context!
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
                        {Object.keys(tpl.files).length} files &bull; {tpl.commits?.length || 0} commits
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
