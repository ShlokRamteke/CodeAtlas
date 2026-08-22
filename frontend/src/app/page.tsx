"use client";

import { useEffect, useState } from "react";
import {
  Compass,
  Database,
  GitCommit,
  Layers,
  Search,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Code2,
  FileCode,
  History,
  ShieldCheck,
} from "lucide-react";
import type { HealthResponse, Repository } from "@archaeologist/contracts";
import { fetchHealth, fetchRepositories } from "@/lib/api";

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");

  useEffect(() => {
    async function loadData() {
      const [h, repos] = await Promise.all([fetchHealth(), fetchRepositories()]);
      setHealth(h);
      setRepositories(repos);
      setLoading(false);
    }
    loadData();
  }, []);

  return (
    <div className="min-h-screen flex flex-col">
      {/* Top Navigation */}
      <header className="border-b border-border/60 bg-card/40 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-primary/10 border border-primary/20 text-primary">
              <Compass className="h-6 w-6" />
            </div>
            <div>
              <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
                Project Archaeologist
              </span>
              <span className="ml-2 text-xs font-medium px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20">
                Phase 1 MVP
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 text-xs">
              <div
                className={`h-2 w-2 rounded-full ${
                  health?.status === "ok" ? "bg-emerald-400 animate-pulse" : "bg-amber-400"
                }`}
              />
              <span className="text-muted-foreground">
                API:{" "}
                <span className="text-foreground font-mono font-medium">
                  {health ? health.status : "connecting..."}
                </span>
              </span>
            </div>

            <div className="hidden sm:flex items-center space-x-2 text-xs border-l border-border/80 pl-4">
              <Database className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="text-muted-foreground">
                DB:{" "}
                <span className="text-foreground font-mono font-medium">
                  {health ? health.database : "connecting..."}
                </span>
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-12">
        {/* Hero Section */}
        <section className="text-center max-w-3xl mx-auto space-y-4 pt-4">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-secondary/80 border border-border text-xs text-muted-foreground">
            <Sparkles className="h-3.5 w-3.5 text-primary" />
            <span>Understand unfamiliar software before you change it</span>
          </div>

          <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight">
            Evidence-Backed{" "}
            <span className="bg-gradient-to-r from-blue-400 via-indigo-300 to-purple-400 bg-clip-text text-transparent">
              Project Intelligence
            </span>
          </h1>

          <p className="text-muted-foreground text-base sm:text-lg leading-relaxed">
            Reconstruct how architecture, git history, PRs, and decisions connect to answer
            complex developer questions deterministically and with AI reasoning.
          </p>

          {/* Quick Search Preview */}
          <div className="pt-4 max-w-2xl mx-auto">
            <div className="relative flex items-center">
              <Search className="absolute left-4 h-5 w-5 text-muted-foreground" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask: Why does this retry workaround exist? How does auth work?"
                className="w-full pl-12 pr-28 py-3.5 rounded-xl bg-card border border-border focus:outline-none focus:ring-2 focus:ring-primary/50 text-sm shadow-lg shadow-black/20"
              />
              <button
                type="button"
                className="absolute right-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground font-medium text-xs hover:bg-primary/90 transition-colors"
              >
                Investigate
              </button>
            </div>
          </div>
        </section>

        {/* Intelligence Pillars */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-6 rounded-xl bg-card border border-border space-y-3">
            <div className="h-10 w-10 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400 flex items-center justify-center">
              <Code2 className="h-5 w-5" />
            </div>
            <h3 className="font-semibold text-lg">1. Current System</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Deterministic AST & symbol analysis for files, functions, dependencies, callers, and
              test relationships.
            </p>
          </div>

          <div className="p-6 rounded-xl bg-card border border-border space-y-3">
            <div className="h-10 w-10 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-400 flex items-center justify-center">
              <History className="h-5 w-5" />
            </div>
            <h3 className="font-semibold text-lg">2. Historical Context</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Evolutionary commit lineage, PR discussions, blame graphs, and linked issue
              requirements.
            </p>
          </div>

          <div className="p-6 rounded-xl bg-card border border-border space-y-3">
            <div className="h-10 w-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center">
              <Layers className="h-5 w-5" />
            </div>
            <h3 className="font-semibold text-lg">3. Engineering Context</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Architecture decisions (ADRs), RFCs, specs, and constraints synthesized before bounded
              model reasoning.
            </p>
          </div>
        </section>

        {/* Foundation Status & Contracts Card */}
        <section className="p-6 rounded-xl bg-card/60 border border-border space-y-4">
          <div className="flex items-center justify-between border-b border-border/80 pb-4">
            <div className="flex items-center space-x-2">
              <ShieldCheck className="h-5 w-5 text-primary" />
              <h2 className="text-base font-semibold">Phase 1 Foundation Readiness</h2>
            </div>
            <span className="text-xs font-mono text-muted-foreground">Contracts: @archaeologist/contracts</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-xs font-mono">
            <div className="p-3 rounded-lg bg-muted/40 border border-border/60">
              <div className="text-muted-foreground">FastAPI Engine</div>
              <div className="text-foreground font-semibold mt-1 flex items-center space-x-1.5">
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                <span>v0.1.0 (Python 3.11+)</span>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-muted/40 border border-border/60">
              <div className="text-muted-foreground">PostgreSQL + pgvector</div>
              <div className="text-foreground font-semibold mt-1 flex items-center space-x-1.5">
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                <span>1536-dim vector store</span>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-muted/40 border border-border/60">
              <div className="text-muted-foreground">Shared Contracts</div>
              <div className="text-foreground font-semibold mt-1 flex items-center space-x-1.5">
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                <span>TypeScript & Pydantic</span>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-muted/40 border border-border/60">
              <div className="text-muted-foreground">Next.js 14 Frontend</div>
              <div className="text-foreground font-semibold mt-1 flex items-center space-x-1.5">
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                <span>App Router & Tailwind</span>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-border/60 py-6 text-center text-xs text-muted-foreground">
        <p>Project Archaeologist &mdash; Architecture, History, Engineering Context, and Bounded Reasoning</p>
      </footer>
    </div>
  );
}
