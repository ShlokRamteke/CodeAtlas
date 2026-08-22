"use client";

import React, { useState, useEffect } from "react";
import type {
  Repository,
  ArchitectureOverview,
  SymbolItem,
  CodeDependencyItem,
} from "@archaeologist/contracts";
import {
  fetchRepositoryArchitecture,
  fetchRepositorySymbols,
  fetchRepositoryDependencies,
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
} from "lucide-react";

interface ArchitectureExplorerProps {
  repository: Repository;
}

export function ArchitectureExplorer({ repository }: ArchitectureExplorerProps) {
  const [activeTab, setActiveTab] = useState<"components" | "symbols" | "relationships" | "ingest">("components");
  const [architecture, setArchitecture] = useState<ArchitectureOverview | null>(null);
  const [symbols, setSymbols] = useState<SymbolItem[]>([]);
  const [symbolQuery, setSymbolQuery] = useState("");
  const [kindFilter, setKindFilter] = useState<string>("");
  const [dependencies, setDependencies] = useState<CodeDependencyItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [ingesting, setIngesting] = useState(false);

  useEffect(() => {
    loadData();
  }, [repository.id]);

  useEffect(() => {
    if (activeTab === "symbols") {
      fetchRepositorySymbols(repository.id, symbolQuery || undefined, kindFilter || undefined)
        .then(setSymbols);
    }
  }, [activeTab, symbolQuery, kindFilter, repository.id]);

  async function loadData() {
    setLoading(true);
    const [arch, deps] = await Promise.all([
      fetchRepositoryArchitecture(repository.id),
      fetchRepositoryDependencies(repository.id),
    ]);
    setArchitecture(arch);
    setDependencies(deps);
    setLoading(false);
  }

  async function handleDemoIngest() {
    setIngesting(true);
    const demoFiles: Record<string, string> = {
      "src/auth/AuthService.ts": `
import { User, Session } from '../models/User';
import { TokenGenerator } from './TokenGenerator';
import axios from 'axios';

export interface LoginCredentials {
  email: string;
  secretHash: string;
}

export class AuthService {
  private generator: TokenGenerator;

  constructor() {
    this.generator = new TokenGenerator();
  }

  async authenticate(creds: LoginCredentials): Promise<Session> {
    return { token: "sample_jwt_123", valid: true };
  }
}
`,
      "src/auth/AuthService.test.ts": `
import { AuthService } from './AuthService';

export const testAuthFlow = async () => {
  const service = new AuthService();
  return await service.authenticate({ email: "dev@example.com", secretHash: "abc" });
};
`,
      "src/models/User.ts": `
export interface User {
  id: string;
  email: string;
  role: 'admin' | 'member';
}

export interface Session {
  token: string;
  valid: boolean;
}
`,
      "src/services/PaymentGateway.ts": `
import { User } from '../models/User';
import stripe from 'stripe';

export class PaymentGateway {
  async chargeUser(user: User, amountCents: number): Promise<boolean> {
    return true;
  }
}
`,
      "src/services/PaymentGateway.test.ts": `
import { PaymentGateway } from './PaymentGateway';

export const testPayment = async () => {
  const gateway = new PaymentGateway();
  return await gateway.chargeUser({ id: '1', email: 'a@b.com', role: 'member' }, 5000);
};
`,
    };

    const arch = await ingestRepositoryFiles(repository.id, demoFiles);
    if (arch) {
      setArchitecture(arch);
      setActiveTab("components");
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
              <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Deterministic Model
              </span>
            </h3>
            <p className="text-xs text-slate-400">
              Tree-sitter AST symbol graphs, test relationships, and dependency maps
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleDemoIngest}
            disabled={ingesting}
            className="flex items-center gap-2 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-medium transition shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${ingesting ? "animate-spin" : ""}`} />
            {ingesting ? "Parsing AST..." : "Ingest & Index Code"}
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
      <div className="flex border-b border-slate-800 px-6 bg-slate-950/20 text-xs font-medium text-slate-400">
        <button
          onClick={() => setActiveTab("components")}
          className={`py-3 px-4 border-b-2 flex items-center gap-2 transition ${
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
          className={`py-3 px-4 border-b-2 flex items-center gap-2 transition ${
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
          className={`py-3 px-4 border-b-2 flex items-center gap-2 transition ${
            activeTab === "relationships"
              ? "border-indigo-500 text-indigo-400 font-semibold"
              : "border-transparent hover:text-slate-200"
          }`}
        >
          <Network className="w-4 h-4" />
          Relationships ({architecture?.relationships.length || 0})
        </button>
      </div>

      {/* Tab Content */}
      <div className="p-6 min-h-[300px]">
        {loading ? (
          <div className="py-12 text-center text-slate-500 text-sm">
            Loading architecture graph...
          </div>
        ) : activeTab === "components" ? (
          <div>
            {!architecture || architecture.majorComponents.length === 0 ? (
              <div className="py-12 text-center">
                <FolderTree className="w-8 h-8 text-slate-600 mx-auto mb-3" />
                <p className="text-slate-400 text-sm font-medium">No component index found yet.</p>
                <p className="text-slate-500 text-xs mt-1">
                  Click <strong>&quot;Ingest &amp; Index Code&quot;</strong> to run Tree-sitter AST extraction.
                </p>
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
        ) : (
          <div>
            {/* Relationships View */}
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
        )}
      </div>
    </div>
  );
}
