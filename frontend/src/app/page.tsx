"use client";

import { useEffect, useState } from "react";
import {
  Compass,
  Database,
  Layers,
  Search,
  Sparkles,
  CheckCircle2,
  Code2,
  History,
  FolderGit2,
  Plus,
} from "lucide-react";
import type { HealthResponse, Repository } from "@archaeologist/contracts";
import { fetchHealth, fetchRepositories, createRepository } from "@/lib/api";
import { ArchitectureExplorer } from "@/components/ArchitectureExplorer";

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<Repository | null>(null);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [newRepoName, setNewRepoName] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    async function loadData() {
      const [h, repos] = await Promise.all([fetchHealth(), fetchRepositories()]);
      setHealth(h);
      setRepositories(repos);
      if (repos.length > 0) {
        setSelectedRepo(repos[0]);
      }
      setLoading(false);
    }
    loadData();
  }, []);

  async function handleCreateRepository(e: React.FormEvent) {
    e.preventDefault();
    if (!newRepoName.trim()) return;
    setCreating(true);

    const [owner, name] = newRepoName.includes("/")
      ? newRepoName.split("/")
      : ["demo-org", newRepoName.trim()];

    const repo = await createRepository({
      owner,
      name,
      fullName: `${owner}/${name}`,
    });

    if (repo) {
      setRepositories([repo, ...repositories]);
      setSelectedRepo(repo);
      setNewRepoName("");
    }
    setCreating(false);
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Top Navigation */}
      <header className="border-b border-border/60 bg-card/40 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <Compass className="h-6 w-6" />
            </div>
            <div>
              <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
                Project Archaeologist
              </span>
              <span className="ml-2 text-xs font-medium px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                Phase 2 — Repository Understanding
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
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-10">
        {/* Hero Section */}
        <section className="text-center max-w-3xl mx-auto space-y-4 pt-2">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-secondary/80 border border-border text-xs text-muted-foreground">
            <Sparkles className="h-3.5 w-3.5 text-indigo-400" />
            <span>Understand unfamiliar software before you change it</span>
          </div>

          <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight">
            Evidence-Backed{" "}
            <span className="bg-gradient-to-r from-blue-400 via-indigo-300 to-purple-400 bg-clip-text text-transparent">
              Repository Understanding
            </span>
          </h1>

          <p className="text-muted-foreground text-base sm:text-lg leading-relaxed">
            Deterministic AST symbol graphs, test relationships, and dependency maps powering
            deep codebase comprehension.
          </p>

          {/* Quick Search Preview */}
          <div className="pt-2 max-w-2xl mx-auto">
            <div className="relative flex items-center">
              <Search className="absolute left-4 h-5 w-5 text-muted-foreground" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask: Why does this retry workaround exist? How does auth work?"
                className="w-full pl-12 pr-28 py-3 rounded-xl bg-card border border-border focus:outline-none focus:ring-2 focus:ring-indigo-500/50 text-sm shadow-lg shadow-black/20"
              />
              <button
                type="button"
                className="absolute right-2 px-4 py-1.5 rounded-lg bg-indigo-600 text-white font-medium text-xs hover:bg-indigo-500 transition-colors"
              >
                Investigate
              </button>
            </div>
          </div>
        </section>

        {/* Repository Selector / Creator Bar */}
        <section className="bg-slate-900/80 border border-slate-800 p-4 rounded-xl flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <FolderGit2 className="w-5 h-5 text-indigo-400" />
            <span className="text-sm font-semibold text-white">Active Repository:</span>
            {repositories.length > 0 ? (
              <select
                value={selectedRepo?.id || ""}
                onChange={(e) => {
                  const r = repositories.find((x) => x.id === e.target.value);
                  if (r) setSelectedRepo(r);
                }}
                className="bg-slate-950 border border-slate-700 text-white text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-indigo-500 font-mono"
              >
                {repositories.map((repo) => (
                  <option key={repo.id} value={repo.id}>
                    {repo.fullName} ({repo.status})
                  </option>
                ))}
              </select>
            ) : (
              <span className="text-xs text-slate-500">No repositories yet</span>
            )}
          </div>

          <form onSubmit={handleCreateRepository} className="flex items-center gap-2">
            <input
              type="text"
              placeholder="e.g. org/payments-service"
              value={newRepoName}
              onChange={(e) => setNewRepoName(e.target.value)}
              className="bg-slate-950 border border-slate-700 text-white text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-indigo-500 font-mono"
            />
            <button
              type="submit"
              disabled={creating || !newRepoName.trim()}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-medium transition shadow-sm"
            >
              <Plus className="w-3.5 h-3.5" />
              {creating ? "Adding..." : "Add Repo"}
            </button>
          </form>
        </section>

        {/* Phase 2: Architecture Explorer */}
        {selectedRepo ? (
          <ArchitectureExplorer repository={selectedRepo} />
        ) : (
          <div className="p-12 text-center bg-slate-900/40 border border-slate-800 rounded-xl">
            <FolderGit2 className="w-10 h-10 text-slate-600 mx-auto mb-3" />
            <p className="text-white font-medium text-sm">Add or select a repository above to explore architecture.</p>
          </div>
        )}

        {/* Intelligence Pillars */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4">
          <div className="p-6 rounded-xl bg-card border border-border space-y-3">
            <div className="h-10 w-10 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400 flex items-center justify-center">
              <Code2 className="h-5 w-5" />
            </div>
            <h3 className="font-semibold text-lg">1. Current System (Phase 2)</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Deterministic Tree-sitter AST &amp; symbol analysis for files, functions, dependencies,
              callers, and test relationships.
            </p>
          </div>

          <div className="p-6 rounded-xl bg-card border border-border space-y-3">
            <div className="h-10 w-10 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-400 flex items-center justify-center">
              <History className="h-5 w-5" />
            </div>
            <h3 className="font-semibold text-lg">2. Historical Context (Phase 3)</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Evolutionary commit lineage, PR discussions, blame graphs, and linked issue
              requirements.
            </p>
          </div>

          <div className="p-6 rounded-xl bg-card border border-border space-y-3">
            <div className="h-10 w-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center">
              <Layers className="h-5 w-5" />
            </div>
            <h3 className="font-semibold text-lg">3. Engineering Context (Phase 4)</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Architecture decisions (ADRs), RFCs, specs, and constraints synthesized before bounded
              model reasoning.
            </p>
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
