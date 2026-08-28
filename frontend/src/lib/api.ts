import type {
  HealthResponse,
  Repository,
  InvestigationResponse,
  InvestigationRequest,
  ArchitectureOverview,
  SymbolItem,
  CodeDependencyItem,
  ContextBriefResponse,
} from "@archaeologist/contracts";


const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchHealth(): Promise<HealthResponse> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/health`, { cache: "no-store" });
    if (!res.ok) {
      return {
        status: "error",
        version: "unknown",
        database: "disconnected",
        timestamp: new Date().toISOString(),
      };
    }
    return await res.json();
  } catch (error) {
    return {
      status: "error",
      version: "offline",
      database: "disconnected",
      timestamp: new Date().toISOString(),
    };
  }
}

export async function fetchRepositories(): Promise<Repository[]> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/repositories/`, { cache: "no-store" });
    if (!res.ok) return [];
    return await res.json();
  } catch (error) {
    return [];
  }
}

export async function connectGitHubRepository(
  urlOrSlug: string,
  githubToken?: string
): Promise<{ repository: Repository; architecture: ArchitectureOverview } | null> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/repositories/connect-github`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url_or_slug: urlOrSlug,
        github_token: githubToken || undefined,
      }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to connect repository");
    }
    const data = await res.json();
    return {
      repository: data.repository,
      architecture: {
        repositoryId: data.architecture.repository_id,
        fileCount: data.architecture.file_count,
        symbolCount: data.architecture.symbol_count,
        dependencyCount: data.architecture.dependency_count,
        languages: data.architecture.languages,
        majorComponents: data.architecture.major_components.map((c: any) => ({
          name: c.name,
          path: c.path,
          symbolCount: c.symbol_count,
          dependencies: c.dependencies,
          testedBy: c.tested_by,
        })),
        relationships: data.architecture.relationships.map((r: any) => ({
          sourceName: r.source_name,
          sourcePath: r.source_path,
          targetName: r.target_name,
          targetPath: r.target_path,
          type: r.type,
        })),
      },
    };
  } catch (error: any) {
    console.error("connectGitHubRepository error:", error);
    throw error;
  }
}


export async function ingestRepositoryFiles(
  repositoryId: string,
  files: Record<string, string>
): Promise<ArchitectureOverview | null> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/repositories/${repositoryId}/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ files }),
    });
    if (!res.ok) return null;
    const data = await res.json();
    return {
      repositoryId: data.repository_id,
      fileCount: data.file_count,
      symbolCount: data.symbol_count,
      dependencyCount: data.dependency_count,
      languages: data.languages,
      majorComponents: data.major_components.map((c: any) => ({
        name: c.name,
        path: c.path,
        symbolCount: c.symbol_count,
        dependencies: c.dependencies,
        testedBy: c.tested_by,
      })),
      relationships: data.relationships.map((r: any) => ({
        sourceName: r.source_name,
        sourcePath: r.source_path,
        targetName: r.target_name,
        targetPath: r.target_path,
        type: r.type,
      })),
    };
  } catch (error) {
    return null;
  }
}

export async function fetchRepositoryContextBrief(
  repositoryId: string,
  component?: string
): Promise<ContextBriefResponse | null> {
  try {
    const url = new URL(`${API_BASE}/api/v1/repositories/${repositoryId}/context-brief`);
    if (component) url.searchParams.set("component", component);
    const res = await fetch(url.toString(), { cache: "no-store" });
    if (!res.ok) return null;
    const data = await res.json();
    return {
      repositoryId: data.repository_id,
      fullName: data.full_name,
      fileCount: data.file_count,
      symbolCount: data.symbol_count,
      dependencyCount: data.dependency_count,
      languages: data.languages,
      components: data.components.map((c: any) => ({
        name: c.name,
        path: c.path,
        language: c.language,
        symbolCount: c.symbol_count,
        symbols: c.symbols,
        dependencies: c.dependencies,
        callers: c.callers,
        tests: c.tests,
        humanSummary: c.human_summary,
        llmContext: c.llm_context,
      })),
      humanSummary: data.human_summary,
      llmContext: data.llm_context,
    };
  } catch (error) {
    return null;
  }
}

export async function fetchRepositoryArchitecture(
  repositoryId: string
): Promise<ArchitectureOverview | null> {

  try {
    const res = await fetch(`${API_BASE}/api/v1/repositories/${repositoryId}/architecture`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    const data = await res.json();
    return {
      repositoryId: data.repository_id,
      fileCount: data.file_count,
      symbolCount: data.symbol_count,
      dependencyCount: data.dependency_count,
      languages: data.languages,
      majorComponents: data.major_components.map((c: any) => ({
        name: c.name,
        path: c.path,
        symbolCount: c.symbol_count,
        dependencies: c.dependencies,
        testedBy: c.tested_by,
      })),
      relationships: data.relationships.map((r: any) => ({
        sourceName: r.source_name,
        sourcePath: r.source_path,
        targetName: r.target_name,
        targetPath: r.target_path,
        type: r.type,
      })),
    };
  } catch (error) {
    return null;
  }
}

export async function fetchRepositorySymbols(
  repositoryId: string,
  name?: string,
  kind?: string
): Promise<SymbolItem[]> {
  try {
    const params = new URLSearchParams();
    if (name) params.append("name", name);
    if (kind) params.append("kind", kind);
    const res = await fetch(
      `${API_BASE}/api/v1/repositories/${repositoryId}/symbols?${params.toString()}`,
      { cache: "no-store" }
    );
    if (!res.ok) return [];
    const data = await res.json();
    return data.map((s: any) => ({
      id: s.id,
      fileId: s.file_id,
      repositoryId: s.repository_id,
      name: s.name,
      kind: s.kind,
      lineStart: s.line_start,
      lineEnd: s.line_end,
      signature: s.signature,
      docstring: s.docstring,
      createdAt: s.created_at,
    }));
  } catch (error) {
    return [];
  }
}

export async function fetchRepositoryDependencies(
  repositoryId: string,
  sourcePath?: string
): Promise<CodeDependencyItem[]> {
  try {
    const params = new URLSearchParams();
    if (sourcePath) params.append("source_path", sourcePath);
    const res = await fetch(
      `${API_BASE}/api/v1/repositories/${repositoryId}/dependencies?${params.toString()}`,
      { cache: "no-store" }
    );
    if (!res.ok) return [];
    const data = await res.json();
    return data.map((d: any) => ({
      id: d.id,
      sourceFileId: d.source_file_id,
      sourcePath: d.source_path,
      targetPath: d.target_path,
      importedSymbol: d.imported_symbol,
      kind: d.kind,
    }));
  } catch (error) {
    return [];
  }
}

export async function createInvestigation(
  data: InvestigationRequest
): Promise<InvestigationResponse | null> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/investigations/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        repository_id: data.repositoryId,
        query: data.query,
        type: data.type || "understand",
        target_path: data.targetPath,
        target_symbol: data.targetSymbol,
      }),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (error) {
    return null;
  }
}
