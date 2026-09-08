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
  PullRequestItem,
  IssueItem,
  HistoricalTraceResponse,
  HistoricalEvidenceRecord,
  SymbolHistoryResponse,
} from "@archaeologist/contracts";
import {
  fetchRepositoryArchitecture,
  fetchRepositorySymbols,
  fetchRepositoryDependencies,
  fetchProjectContext,
  fetchRepositoryCommits,
  fetchFileHistory,
  fetchRepositoryPullRequests,
  fetchRepositoryIssues,
  fetchHistoricalTrace,
  retrieveHistoricalEvidence,
  getSymbolHistory,
  searchHistory,
  ingestRepositoryCommits,
  ingestRepositoryPullRequests,
  ingestRepositoryIssues,
  ingestRepositoryFiles,
  reindexRepository,
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
  RotateCw,
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
  GitPullRequest,
  CircleDot,
  GitMerge,
  ArrowRight,
  ExternalLink,
  History,
  Calendar,
  User,
  PlusCircle,
  Tag,
  Filter,
  Target,
  Clock,
} from "lucide-react";


interface ArchitectureExplorerProps {
  repository: Repository;
}

const TEMPLATES: Record<
  string,
  {
    label: string;
    desc: string;
    files: Record<string, string>;
    commits?: any[];
    pull_requests?: any[];
    issues?: any[];
  }
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
    pull_requests: [
      {
        number: 1,
        title: "feat(models): introduce initial Order and Payment models",
        body: "Initial schema for order processing.\n\nCloses #80",
        state: "merged",
        author: "Alice Developer",
        labels: ["models", "v1"],
        merged_at: "2025-01-15T10:00:00Z",
      },
      {
        number: 12,
        title: "feat(services): implement PaymentService and Stripe connector",
        body: "Connects Stripe transaction gateway.\n\nFixes #88\nRefs #89",
        state: "merged",
        author: "Bob Engineer",
        labels: ["payment", "stripe"],
        merged_at: "2025-02-10T14:30:00Z",
      },
      {
        number: 45,
        title: "feat(checkout): add CheckoutService integration",
        body: "End-to-end checkout orchestration.\n\nFixes #90",
        state: "merged",
        author: "Alice Developer",
        labels: ["checkout", "epic"],
        merged_at: "2025-03-01T09:15:00Z",
      },
    ],
    issues: [
      {
        number: 80,
        title: "Define core domain models for orders and payments",
        body: "Need typed contracts for order state machine.",
        state: "closed",
        author: "Architect",
        labels: ["domain", "v1"],
        closed_at: "2025-01-15T10:00:00Z",
      },
      {
        number: 88,
        title: "Support Stripe card transactions with idempotent receipts",
        body: "Secure payment processing requirement.",
        state: "closed",
        author: "Product Lead",
        labels: ["feature", "payment"],
        closed_at: "2025-02-10T14:30:00Z",
      },
      {
        number: 89,
        title: "Configure Stripe webhook signature verification",
        body: "Verify webhook signatures to prevent forgery.",
        state: "open",
        author: "Security Officer",
        labels: ["security"],
      },
      {
        number: 90,
        title: "Orchestrate single-click checkout with payment verification",
        body: "Checkout pipeline requirement.",
        state: "closed",
        author: "Product Lead",
        labels: ["epic", "checkout"],
        closed_at: "2025-03-01T09:15:00Z",
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
    pull_requests: [
      {
        number: 101,
        title: "feat(auth): initial JWT token issuance and user verification",
        body: "Implements HMAC-SHA256 signature verification.\n\nFixes #200",
        state: "merged",
        author: "Security Lead",
        labels: ["security", "auth"],
        merged_at: "2024-11-20T08:00:00Z",
      },
    ],
    issues: [
      {
        number: 200,
        title: "Design stateless JWT token issuance for API auth",
        body: "Ensure tokens can be verified across distributed microservices.",
        state: "closed",
        author: "CISO",
        labels: ["security"],
        closed_at: "2024-11-20T08:00:00Z",
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
  const [historySubTab, setHistorySubTab] = useState<
    "commits" | "trace" | "prs" | "issues" | "retrieval"
  >("commits");
  const [architecture, setArchitecture] = useState<ArchitectureOverview | null>(null);
  const [symbols, setSymbols] = useState<SymbolItem[]>([]);
  const [symbolQuery, setSymbolQuery] = useState("");
  const [kindFilter, setKindFilter] = useState<string>("");
  const [dependencies, setDependencies] = useState<CodeDependencyItem[]>([]);
  const [projectContext, setProjectContext] = useState<ProjectContext | null>(null);
  const [selectedContextComp, setSelectedContextComp] = useState<string>("");
  const [commits, setCommits] = useState<CommitItem[]>([]);
  const [pullRequests, setPullRequests] = useState<PullRequestItem[]>([]);
  const [issues, setIssues] = useState<IssueItem[]>([]);
  const [selectedHistoryFile, setSelectedHistoryFile] = useState<string>("");
  const [fileHistory, setFileHistory] = useState<FileHistoryResponse | null>(null);
  const [historicalTrace, setHistoricalTrace] = useState<HistoricalTraceResponse | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [traceLoading, setTraceLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [reindexing, setReindexing] = useState(false);
  const [ingesting, setIngesting] = useState(false);

  // Deterministic Historical Retrieval State
  const [retrievalQuery, setRetrievalQuery] = useState("");
  const [retrievalAuthor, setRetrievalAuthor] = useState("");
  const [retrievalPath, setRetrievalPath] = useState("");
  const [retrievalSymbol, setRetrievalSymbol] = useState("");
  const [retrievalType, setRetrievalType] = useState<"all" | "commit" | "pull_request" | "issue">("all");
  const [retrievalState, setRetrievalState] = useState("");
  const [retrievedEvidence, setRetrievedEvidence] = useState<HistoricalEvidenceRecord[]>([]);
  const [evidenceSummary, setEvidenceSummary] = useState<string>("");
  const [symbolHistoryData, setSymbolHistoryData] = useState<SymbolHistoryResponse | null>(null);
  const [retrievalLoading, setRetrievalLoading] = useState(false);

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
      setTraceLoading(true);
      fetchFileHistory(repository.id, selectedHistoryFile).then((res) => {
        setFileHistory(res);
        setHistoryLoading(false);
      });
      fetchHistoricalTrace(repository.id, selectedHistoryFile).then((res) => {
        setHistoricalTrace(res);
        setTraceLoading(false);
      });
    }
  }, [selectedHistoryFile, repository.id]);

  async function loadData() {
    setLoading(true);
    const [arch, deps, pCtx, cList, prList, issList] = await Promise.all([
      fetchRepositoryArchitecture(repository.id),
      fetchRepositoryDependencies(repository.id),
      fetchProjectContext(repository.id),
      fetchRepositoryCommits(repository.id),
      fetchRepositoryPullRequests(repository.id),
      fetchRepositoryIssues(repository.id),
    ]);
    setArchitecture(arch);
    setDependencies(deps);
    setProjectContext(pCtx);
    setCommits(cList);
    setPullRequests(prList);
    setIssues(issList);
    setLoading(false);
  }

  async function loadHistory() {
    const [cList, prList, issList] = await Promise.all([
      fetchRepositoryCommits(repository.id),
      fetchRepositoryPullRequests(repository.id),
      fetchRepositoryIssues(repository.id),
    ]);
    setCommits(cList);
    setPullRequests(prList);
    setIssues(issList);
  }

  async function handleExecuteRetrieval() {
    setRetrievalLoading(true);
    const sourceTypes = retrievalType === "all" ? undefined : [retrievalType];
    const res = await retrieveHistoricalEvidence(repository.id, {
      query: retrievalQuery.trim() || undefined,
      author: retrievalAuthor.trim() || undefined,
      filePath: retrievalPath.trim() || undefined,
      symbolName: retrievalSymbol.trim() || undefined,
      sourceTypes: sourceTypes as any,
      limit: 30,
    });
    if (res) {
      setRetrievedEvidence(res.evidence);
      setEvidenceSummary(res.summary);
    }

    if (retrievalSymbol.trim()) {
      const symRes = await getSymbolHistory(
        repository.id,
        retrievalSymbol.trim(),
        retrievalPath.trim() || undefined
      );
      setSymbolHistoryData(symRes);
    } else {
      setSymbolHistoryData(null);
    }
    setRetrievalLoading(false);
  }

  useEffect(() => {
    if (activeTab === "git_history" && historySubTab === "retrieval") {
      handleExecuteRetrieval();
    }
  }, [activeTab, historySubTab, retrievalType, repository.id]);


  async function handleReindex() {
    setReindexing(true);
    try {
      const res = await reindexRepository(repository.id);
      if (res) {
        setArchitecture(res.architecture);
        await loadData();
        setSuccessMsg(`Successfully re-indexed ${res.repository.fullName}!`);
        setTimeout(() => setSuccessMsg(null), 3000);
      }
    } catch (e: any) {
      console.error("Reindex error:", e);
    } finally {
      setReindexing(false);
    }
  }


  async function handleIngestTemplate(templateKey: string) {
    setIngesting(true);
    setSuccessMsg(null);
    const tpl = TEMPLATES[templateKey];
    if (!tpl) return;

    const arch = await ingestRepositoryFiles(repository.id, tpl.files);
    if (tpl.pull_requests && tpl.pull_requests.length > 0) {
      await ingestRepositoryPullRequests(repository.id, tpl.pull_requests);
    }
    if (tpl.issues && tpl.issues.length > 0) {
      await ingestRepositoryIssues(repository.id, tpl.issues);
    }
    if (tpl.commits && tpl.commits.length > 0) {
      await ingestRepositoryCommits(repository.id, tpl.commits);
    }

    if (arch) {
      setArchitecture(arch);
      await loadData();
      setSuccessMsg(
        `Successfully indexed ${tpl.label} (${arch.symbolCount} symbols, ${tpl.commits?.length || 0} commits, ${tpl.pull_requests?.length || 0} PRs, ${tpl.issues?.length || 0} issues)`
      );
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
            onClick={handleReindex}
            disabled={reindexing}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 border border-slate-700 rounded-lg text-xs font-medium transition"
            title="Re-fetch all files, commits, PRs, and issues from GitHub"
          >
            <RotateCw className={`w-3.5 h-3.5 text-indigo-400 ${reindexing ? "animate-spin" : ""}`} />
            <span>{reindexing ? "Reindexing..." : "Re-index"}</span>
          </button>
          <button
            onClick={loadData}
            disabled={loading}
            className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs transition"
            title="Refresh local data"
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
                  Historical Traceability & Artifact Linking
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
                    PH3-02 Dataset
                  </span>
                </h4>
                <p className="text-xs text-slate-400 mt-0.5">
                  Trace code changes from Files &rarr; Commits &rarr; Pull Requests &rarr; Originating Issues.
                </p>
              </div>

              {/* Sub-tab Navigation */}
              <div className="flex items-center gap-1.5 p-1 bg-slate-900 border border-slate-800 rounded-lg text-xs">
                <button
                  onClick={() => setHistorySubTab("commits")}
                  className={`px-3 py-1 rounded-md font-medium transition flex items-center gap-1.5 ${
                    historySubTab === "commits"
                      ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  <GitCommit className="w-3.5 h-3.5" />
                  Commits ({commits.length})
                </button>
                <button
                  onClick={() => setHistorySubTab("trace")}
                  className={`px-3 py-1 rounded-md font-medium transition flex items-center gap-1.5 ${
                    historySubTab === "trace"
                      ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  <ArrowRight className="w-3.5 h-3.5" />
                  Provenance Trace
                </button>
                <button
                  onClick={() => setHistorySubTab("prs")}
                  className={`px-3 py-1 rounded-md font-medium transition flex items-center gap-1.5 ${
                    historySubTab === "prs"
                      ? "bg-purple-500/20 text-purple-300 border border-purple-500/30"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  <GitPullRequest className="w-3.5 h-3.5" />
                  PRs ({pullRequests.length})
                </button>
                <button
                  onClick={() => setHistorySubTab("issues")}
                  className={`px-3 py-1 rounded-md font-medium transition flex items-center gap-1.5 ${
                    historySubTab === "issues"
                      ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  <CircleDot className="w-3.5 h-3.5" />
                  Issues ({issues.length})
                </button>
                <button
                  onClick={() => setHistorySubTab("retrieval")}
                  className={`px-3 py-1 rounded-md font-medium transition flex items-center gap-1.5 ${
                    historySubTab === "retrieval"
                      ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  <Target className="w-3.5 h-3.5 text-cyan-400" />
                  Search &amp; Evidence
                </button>
              </div>
            </div>


            {/* Commits Sub-Tab */}
            {historySubTab === "commits" && (
              <div className="space-y-4">
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
                        className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 transition space-y-2.5"
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

                        {/* Linked PRs & Issues Badges */}
                        {((c.linkedPullRequests && c.linkedPullRequests.length > 0) ||
                          (c.linkedIssues && c.linkedIssues.length > 0)) && (
                          <div className="pt-2 border-t border-slate-800/80 flex items-center gap-2 flex-wrap">
                            <span className="text-[11px] text-slate-500 font-medium">Trace Links:</span>
                            {c.linkedPullRequests?.map((pr, idx) => (
                              <span
                                key={idx}
                                onClick={() => setHistorySubTab("prs")}
                                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-purple-950/50 hover:bg-purple-900/50 text-purple-300 border border-purple-500/30 text-[10px] font-mono cursor-pointer transition"
                                title={pr.title || `PR #${pr.prNumber}`}
                              >
                                <GitPullRequest className="w-3 h-3 text-purple-400" />
                                PR #{pr.prNumber} ({pr.linkType})
                              </span>
                            ))}
                            {c.linkedIssues?.map((iss, idx) => (
                              <span
                                key={idx}
                                onClick={() => setHistorySubTab("issues")}
                                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-emerald-950/50 hover:bg-emerald-900/50 text-emerald-300 border border-emerald-500/30 text-[10px] font-mono cursor-pointer transition"
                                title={iss.title || `Issue #${iss.issueNumber}`}
                              >
                                <CircleDot className="w-3 h-3 text-emerald-400" />
                                Issue #{iss.issueNumber} ({iss.linkType})
                              </span>
                            ))}
                          </div>
                        )}

                        {c.fileChanges && c.fileChanges.length > 0 && (
                          <div className="pt-1 flex items-center gap-2 flex-wrap">
                            <span className="text-[11px] text-slate-500">Changed Files:</span>
                            {c.fileChanges.map((fc, idx) => (
                              <span
                                key={idx}
                                onClick={() => {
                                  setSelectedHistoryFile(fc.filePath);
                                  setHistorySubTab("trace");
                                }}
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
            )}

            {/* Provenance Trace Sub-Tab */}
            {historySubTab === "trace" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between gap-4 p-4 bg-slate-950/60 border border-slate-800 rounded-xl">
                  <div className="space-y-0.5">
                    <div className="text-xs font-semibold text-white">Select File to Trace Lineage</div>
                    <div className="text-[11px] text-slate-400">
                      Discovers the introducing commit, evolution diffs, linked PRs, and resolving issues.
                    </div>
                  </div>
                  {architecture && (
                    <select
                      value={selectedHistoryFile}
                      onChange={(e) => setSelectedHistoryFile(e.target.value)}
                      className="bg-slate-950 border border-slate-700 text-white text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-indigo-500 font-mono"
                    >
                      <option value="">Select File to Inspect</option>
                      {architecture.majorComponents.map((c) => (
                        <option key={c.path} value={c.path}>
                          {c.path} ({c.name})
                        </option>
                      ))}
                    </select>
                  )}
                </div>

                {selectedHistoryFile ? (
                  <div className="space-y-4">
                    {/* File Header & Introducing Commit */}
                    <div className="p-4 rounded-xl bg-slate-950/80 border border-indigo-500/30 space-y-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <FileCode className="w-4 h-4 text-indigo-400" />
                          <span className="text-xs font-semibold text-white font-mono">{selectedHistoryFile}</span>
                        </div>
                        <span className="text-[11px] px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                          {historicalTrace
                            ? `${historicalTrace.totalCommits} commits • ${historicalTrace.totalPullRequests} PRs • ${historicalTrace.totalIssues} issues`
                            : "Loading trace..."}
                        </span>
                      </div>

                      {fileHistory?.introducingCommit && (
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
                      )}
                    </div>

                    {/* Step-by-Step Provenance Lineage */}
                    {historicalTrace && (
                      <div className="space-y-3">
                        <h5 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                          Code &rarr; Commit &rarr; PR &rarr; Issue Trace Lineage
                        </h5>

                        {historicalTrace.traceChain.map((step, idx) => (
                          <div
                            key={idx}
                            className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3"
                          >
                            <div className="flex items-start justify-between gap-4">
                              <div className="flex items-center gap-2">
                                <span
                                  className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                                    step.changeType === "added"
                                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                      : "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                                  }`}
                                >
                                  {step.changeType}
                                </span>
                                <span className="font-mono text-xs font-semibold text-white">
                                  {step.commitHash.slice(0, 7)}
                                </span>
                                <span className="text-xs text-slate-300 font-medium">
                                  {step.message}
                                </span>
                              </div>
                              <span className="text-[11px] text-slate-500">
                                {step.committedAt.slice(0, 10)} by {step.authorName}
                              </span>
                            </div>

                            {/* Chain Nodes */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 border-t border-slate-800/80">
                              {/* Linked PRs */}
                              <div className="p-2.5 rounded-lg bg-purple-950/20 border border-purple-500/20 space-y-1.5">
                                <div className="text-[10px] font-bold uppercase text-purple-400 flex items-center gap-1.5">
                                  <GitPullRequest className="w-3 h-3" />
                                  Linked Pull Request ({step.linkedPullRequests.length})
                                </div>
                                {step.linkedPullRequests.length === 0 ? (
                                  <div className="text-[11px] text-slate-500 italic">Direct commit (no PR)</div>
                                ) : (
                                  step.linkedPullRequests.map((pr: any, pIdx: number) => (
                                    <div key={pIdx} className="text-xs space-y-0.5">
                                      <div className="text-purple-200 font-semibold flex items-center gap-1.5">
                                        PR #{pr.number}: {pr.title}
                                        <span className="text-[9px] px-1.5 py-0.2 rounded bg-purple-900/60 text-purple-300 uppercase">
                                          {pr.state}
                                        </span>
                                      </div>
                                      {pr.linked_issues && pr.linked_issues.length > 0 && (
                                        <div className="text-[10px] text-emerald-400">
                                          Resolves: {pr.linked_issues.map((i: any) => `#${i.number}`).join(", ")}
                                        </div>
                                      )}
                                    </div>
                                  ))
                                )}
                              </div>

                              {/* Linked Issues */}
                              <div className="p-2.5 rounded-lg bg-emerald-950/20 border border-emerald-500/20 space-y-1.5">
                                <div className="text-[10px] font-bold uppercase text-emerald-400 flex items-center gap-1.5">
                                  <CircleDot className="w-3 h-3" />
                                  Linked Issue / Requirement ({step.linkedIssues.length})
                                </div>
                                {step.linkedIssues.length === 0 ? (
                                  <div className="text-[11px] text-slate-500 italic">No direct issue closure tagged</div>
                                ) : (
                                  step.linkedIssues.map((iss: any, iIdx: number) => (
                                    <div key={iIdx} className="text-xs space-y-0.5">
                                      <div className="text-emerald-200 font-semibold flex items-center gap-1.5">
                                        Issue #{iss.number}: {iss.title}
                                        <span className="text-[9px] px-1.5 py-0.2 rounded bg-emerald-900/60 text-emerald-300 uppercase">
                                          {iss.state}
                                        </span>
                                      </div>
                                      <div className="text-[10px] text-slate-400">
                                        Link Type: <strong>{iss.link_type}</strong>
                                      </div>
                                    </div>
                                  ))
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="py-12 text-center text-slate-500 text-sm">
                    Select a component file above to inspect its full Code &rarr; Commit &rarr; PR &rarr; Issue lineage.
                  </div>
                )}
              </div>
            )}

            {/* Pull Requests Sub-Tab */}
            {historySubTab === "prs" && (
              <div className="space-y-3">
                {pullRequests.length === 0 ? (
                  <div className="py-12 text-center text-slate-500 text-sm">
                    No pull requests indexed yet. Connect a public GitHub repository or load a template.
                  </div>
                ) : (
                  pullRequests.map((pr) => (
                    <div
                      key={pr.id || pr.number}
                      className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2.5 hover:border-slate-700 transition"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <GitPullRequest className="w-4 h-4 text-purple-400" />
                            <span className="text-xs font-bold text-white">
                              PR #{pr.number}: {pr.title}
                            </span>
                            <span
                              className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${
                                pr.state === "merged"
                                  ? "bg-purple-500/10 text-purple-400 border border-purple-500/20"
                                  : pr.state === "closed"
                                  ? "bg-red-500/10 text-red-400 border border-red-500/20"
                                  : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                              }`}
                            >
                              {pr.state}
                            </span>
                          </div>
                          {pr.body && (
                            <p className="text-xs text-slate-400 line-clamp-2">{pr.body}</p>
                          )}
                          <div className="flex items-center gap-3 text-[11px] text-slate-500 pt-1">
                            <span>Author: <strong>{pr.author}</strong></span>
                            {pr.mergedAt && (
                              <span>Merged: {pr.mergedAt.slice(0, 10)}</span>
                            )}
                          </div>
                        </div>

                        {pr.labels && pr.labels.length > 0 && (
                          <div className="flex items-center gap-1 flex-wrap justify-end">
                            {pr.labels.map((lbl, idx) => (
                              <span
                                key={idx}
                                className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 font-mono"
                              >
                                {lbl}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Linked Issues */}
                      {pr.linkedIssues && pr.linkedIssues.length > 0 && (
                        <div className="pt-2 border-t border-slate-800/80 flex items-center gap-2 flex-wrap">
                          <span className="text-[11px] text-slate-500">Resolves Issues:</span>
                          {pr.linkedIssues.map((iss, idx) => (
                            <span
                              key={idx}
                              onClick={() => setHistorySubTab("issues")}
                              className="cursor-pointer text-[10px] px-2 py-0.5 rounded bg-emerald-950/50 text-emerald-300 border border-emerald-500/30 font-mono flex items-center gap-1"
                            >
                              <CircleDot className="w-2.5 h-2.5" />
                              Issue #{iss.issueNumber} ({iss.linkType})
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Issues Sub-Tab */}
            {historySubTab === "issues" && (
              <div className="space-y-3">
                {issues.length === 0 ? (
                  <div className="py-12 text-center text-slate-500 text-sm">
                    No issues indexed yet. Connect a public GitHub repository or load a template.
                  </div>
                ) : (
                  issues.map((issue) => (
                    <div
                      key={issue.id || issue.number}
                      className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2.5 hover:border-slate-700 transition"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <CircleDot className="w-4 h-4 text-emerald-400" />
                            <span className="text-xs font-bold text-white">
                              Issue #{issue.number}: {issue.title}
                            </span>
                            <span
                              className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${
                                issue.state === "closed"
                                  ? "bg-purple-500/10 text-purple-400 border border-purple-500/20"
                                  : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                              }`}
                            >
                              {issue.state}
                            </span>
                          </div>
                          {issue.body && (
                            <p className="text-xs text-slate-400 line-clamp-2">{issue.body}</p>
                          )}
                          <div className="flex items-center gap-3 text-[11px] text-slate-500 pt-1">
                            <span>Author: <strong>{issue.author}</strong></span>
                            {issue.closedAt && (
                              <span>Closed: {issue.closedAt.slice(0, 10)}</span>
                            )}
                          </div>
                        </div>

                        {issue.labels && issue.labels.length > 0 && (
                          <div className="flex items-center gap-1 flex-wrap justify-end">
                            {issue.labels.map((lbl, idx) => (
                              <span
                                key={idx}
                                className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 font-mono"
                              >
                                {lbl}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Linked PRs */}
                      {issue.linkedPullRequests && issue.linkedPullRequests.length > 0 && (
                        <div className="pt-2 border-t border-slate-800/80 flex items-center gap-2 flex-wrap">
                          <span className="text-[11px] text-slate-500">Addressed in PR:</span>
                          {issue.linkedPullRequests.map((pr, idx) => (
                            <span
                              key={idx}
                              onClick={() => setHistorySubTab("prs")}
                              className="cursor-pointer text-[10px] px-2 py-0.5 rounded bg-purple-950/50 text-purple-300 border border-purple-500/30 font-mono flex items-center gap-1"
                            >
                              <GitPullRequest className="w-2.5 h-2.5" />
                              PR #{pr.prNumber} ({pr.linkType})
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Historical Retrieval & Evidence Sub-Tab */}
            {historySubTab === "retrieval" && (
              <div className="space-y-6">
                {/* Search & Filter Header Box */}
                <div className="p-5 rounded-xl bg-slate-950/80 border border-slate-800 space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <div className="p-1.5 bg-cyan-500/10 border border-cyan-500/20 rounded-lg text-cyan-400">
                        <Target className="w-4 h-4" />
                      </div>
                      <div>
                        <h5 className="text-xs font-semibold text-white">
                          Deterministic Historical Retrieval Engine
                        </h5>
                        <p className="text-[11px] text-slate-400">
                          Multi-attribute querying across Commits, Pull Requests, and Issues without LLM invocation.
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 font-mono">
                        Zero LLM Calls &bull; 100% Deterministic
                      </span>
                    </div>
                  </div>

                  {/* Main Query Bar */}
                  <div className="flex items-center gap-2">
                    <div className="relative flex-1">
                      <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                      <input
                        type="text"
                        value={retrievalQuery}
                        onChange={(e) => setRetrievalQuery(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && handleExecuteRetrieval()}
                        placeholder="Search commit messages, PR titles/bodies, and issue descriptions (e.g. 'stripe payment', 'fix: crash', '#45')..."
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-9 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono"
                      />
                    </div>
                    <button
                      onClick={handleExecuteRetrieval}
                      disabled={retrievalLoading}
                      className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold transition flex items-center gap-1.5 shadow-sm"
                    >
                      {retrievalLoading ? (
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Target className="w-3.5 h-3.5" />
                      )}
                      <span>{retrievalLoading ? "Searching..." : "Retrieve"}</span>
                    </button>
                  </div>

                  {/* Advanced Multi-Attribute Filters Grid */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-2 border-t border-slate-800/80">
                    <div>
                      <label className="text-[11px] font-medium text-slate-400 block mb-1">
                        Symbol Scope:
                      </label>
                      <input
                        type="text"
                        value={retrievalSymbol}
                        onChange={(e) => setRetrievalSymbol(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && handleExecuteRetrieval()}
                        placeholder="Symbol name (e.g. Order, processPayment)..."
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500 font-mono"
                      />
                    </div>

                    <div>
                      <label className="text-[11px] font-medium text-slate-400 block mb-1">
                        Component / File Path:
                      </label>
                      <input
                        type="text"
                        value={retrievalPath}
                        onChange={(e) => setRetrievalPath(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && handleExecuteRetrieval()}
                        placeholder="Path prefix (e.g. src/services, app/)..."
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500 font-mono"
                      />
                    </div>

                    <div>
                      <label className="text-[11px] font-medium text-slate-400 block mb-1">
                        Author Name / Email:
                      </label>
                      <input
                        type="text"
                        value={retrievalAuthor}
                        onChange={(e) => setRetrievalAuthor(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && handleExecuteRetrieval()}
                        placeholder="Author (e.g. Shlok, core@)..."
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500 font-mono"
                      />
                    </div>

                    <div>
                      <label className="text-[11px] font-medium text-slate-400 block mb-1">
                        Artifact Filter:
                      </label>
                      <select
                        value={retrievalType}
                        onChange={(e) => setRetrievalType(e.target.value as any)}
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500 font-mono"
                      >
                        <option value="all">All Artifacts (Commits + PRs + Issues)</option>
                        <option value="commit">Commits Only</option>
                        <option value="pull_request">Pull Requests Only</option>
                        <option value="issue">Issues Only</option>
                      </select>
                    </div>
                  </div>
                </div>

                {/* Evidence Summary Banner */}
                {evidenceSummary && (
                  <div className="p-4 rounded-xl bg-slate-950/60 border border-cyan-500/20 flex items-start gap-3">
                    <div className="p-2 bg-cyan-500/10 rounded-lg text-cyan-400 flex-shrink-0 mt-0.5">
                      <Sparkles className="w-4 h-4" />
                    </div>
                    <div className="flex-1">
                      <div className="text-xs font-semibold text-cyan-300">
                        Retrieval Findings Summary
                      </div>
                      <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                        {evidenceSummary}
                      </p>
                    </div>
                  </div>
                )}

                {/* Symbol Evolution Timeline Inspector */}
                {symbolHistoryData && (
                  <div className="p-5 rounded-xl bg-slate-950/90 border border-indigo-500/30 space-y-4">
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <Code2 className="w-4 h-4 text-indigo-400" />
                          <h5 className="text-xs font-bold text-white font-mono">
                            Symbol Evolution: {symbolHistoryData.symbolName}
                          </h5>
                        </div>
                        <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                          {symbolHistoryData.filePath}
                          {symbolHistoryData.lineStart && ` (lines ${symbolHistoryData.lineStart}-${symbolHistoryData.lineEnd})`}
                        </p>
                      </div>

                      {symbolHistoryData.introducingCommit && (
                        <div className="flex items-center gap-1.5 px-3 py-1 bg-amber-500/10 border border-amber-500/20 rounded-lg text-xs text-amber-300">
                          <span className="text-[10px] uppercase font-bold text-amber-400">Origin:</span>
                          <span className="font-mono font-semibold">{symbolHistoryData.introducingCommit.commitHash.slice(0, 7)}</span>
                          <span className="text-slate-400">&bull; {symbolHistoryData.introducingCommit.authorName}</span>
                        </div>
                      )}
                    </div>

                    {/* Timeline Events */}
                    <div className="space-y-3">
                      <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                        Evolutionary Milestones ({symbolHistoryData.evolutionTimeline.length})
                      </div>
                      <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                        {symbolHistoryData.evolutionTimeline.map((ev, idx) => (
                          <div
                            key={idx}
                            className="p-3 rounded-lg bg-slate-900 border border-slate-800 flex items-start justify-between gap-3 text-xs"
                          >
                            <div className="space-y-1">
                              <div className="flex items-center gap-2">
                                <span
                                  className={`px-1.5 py-0.5 rounded text-[10px] font-mono uppercase font-bold ${
                                    ev.eventType === "introduction"
                                      ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                                      : ev.eventType === "symbol_modification"
                                      ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
                                      : "bg-slate-800 text-slate-400"
                                  }`}
                                >
                                  {ev.eventType.replace("_", " ")}
                                </span>
                                <span className="font-mono text-cyan-400 font-semibold">{ev.commitHash.slice(0, 7)}</span>
                                <span className="text-slate-400">&bull; {ev.author}</span>
                              </div>
                              <div className="text-slate-300 text-xs font-mono">{ev.summary}</div>
                            </div>

                            <div className="text-[11px] text-slate-500 flex-shrink-0 font-mono">
                              {ev.timestamp.slice(0, 10)}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Ranked Evidence Results */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h5 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-cyan-400" />
                      Ranked Historical Evidence Records ({retrievedEvidence.length})
                    </h5>
                    <span className="text-[11px] text-slate-500">
                      Ranked by query relevance &bull; recency &bull; confidence
                    </span>
                  </div>

                  {retrievedEvidence.length === 0 ? (
                    <div className="py-12 text-center bg-slate-950/40 rounded-xl border border-slate-800">
                      <Target className="w-8 h-8 text-slate-600 mx-auto mb-3" />
                      <p className="text-slate-400 text-sm font-medium">No matching historical evidence found.</p>
                      <p className="text-slate-500 text-xs mt-1">
                        Try adjusting query keywords, component path, or artifact filters.
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {retrievedEvidence.map((ev) => (
                        <div
                          key={ev.id}
                          className="p-4 rounded-xl bg-slate-950/80 border border-slate-800/90 hover:border-cyan-500/30 transition space-y-3"
                        >
                          <div className="flex flex-wrap items-start justify-between gap-2">
                            <div className="flex items-start gap-2.5">
                              <div className="mt-0.5">
                                {ev.sourceType === "commit" ? (
                                  <div className="p-1.5 bg-amber-500/10 border border-amber-500/20 rounded-md text-amber-400">
                                    <GitCommit className="w-3.5 h-3.5" />
                                  </div>
                                ) : ev.sourceType === "pull_request" ? (
                                  <div className="p-1.5 bg-purple-500/10 border border-purple-500/20 rounded-md text-purple-400">
                                    <GitPullRequest className="w-3.5 h-3.5" />
                                  </div>
                                ) : (
                                  <div className="p-1.5 bg-emerald-500/10 border border-emerald-500/20 rounded-md text-emerald-400">
                                    <CircleDot className="w-3.5 h-3.5" />
                                  </div>
                                )}
                              </div>

                              <div>
                                <div className="text-xs font-semibold text-white flex items-center gap-2 flex-wrap">
                                  <span>{ev.title}</span>
                                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                                    {ev.id}
                                  </span>
                                </div>

                                <div className="flex items-center gap-3 text-[11px] text-slate-400 mt-1 flex-wrap">
                                  {ev.author && <span>Author: <strong className="text-slate-300">{ev.author}</strong></span>}
                                  {ev.timestamp && <span>Timestamp: {ev.timestamp.slice(0, 10)}</span>}
                                  <span>Match Score: <strong className="text-cyan-400">{Math.round(ev.score * 100)}%</strong></span>
                                  <span>Confidence: <strong className="text-emerald-400">{Math.round(ev.confidence * 100)}%</strong></span>
                                </div>
                              </div>
                            </div>
                          </div>

                          {/* Snippet Block */}
                          <div className="p-3 bg-slate-900 rounded-lg border border-slate-800 text-xs font-mono text-slate-300 whitespace-pre-wrap leading-relaxed">
                            {ev.snippet}
                          </div>

                          {/* Citations & Trace Tags */}
                          {ev.citations && ev.citations.length > 0 && (
                            <div className="flex items-center gap-1.5 flex-wrap pt-1 border-t border-slate-800/80">
                              <span className="text-[11px] text-slate-500">Citations:</span>
                              {ev.citations.map((cite, idx) => (
                                <span
                                  key={idx}
                                  className="text-[10px] px-2 py-0.5 rounded bg-cyan-950/40 text-cyan-300 border border-cyan-500/30 font-mono"
                                >
                                  {cite}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
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
