import type {
  HealthResponse,
  Repository,
  InvestigationResponse,
  InvestigationRequest,
  ArchitectureOverview,
  SymbolItem,
  CodeDependencyItem,
  ContextBriefResponse,
  ProjectContext,
  CommitItem,
  FileHistoryResponse,
  ComponentHistoryResponse,
  PullRequestItem,
  IssueItem,
  HistoricalTraceResponse,
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

function mapRepository(data: any): Repository {
  return {
    id: data.id,
    owner: data.owner,
    name: data.name,
    fullName: data.full_name || data.fullName || `${data.owner}/${data.name}`,
    defaultBranch: data.default_branch || data.defaultBranch || "main",
    status: data.status || "ready",
    indexedAt: data.indexed_at || data.indexedAt,
    fileCount: data.file_count ?? data.fileCount ?? 0,
    symbolCount: data.symbol_count ?? data.symbolCount ?? 0,
    commitCount: data.commit_count ?? data.commitCount ?? 0,
    createdAt: data.created_at || data.createdAt || new Date().toISOString(),
    updatedAt: data.updated_at || data.updatedAt || new Date().toISOString(),
  };
}

export async function fetchRepositories(): Promise<Repository[]> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/repositories/`, { cache: "no-store" });
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data) ? data.map(mapRepository) : [];
  } catch (error) {
    return [];
  }
}

export async function connectGitHubRepository(
  urlOrSlug: string
): Promise<{ repository: Repository; architecture: ArchitectureOverview } | null> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/repositories/connect-github`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url_or_slug: urlOrSlug,
      }),
    });
    if (!res.ok) {
      let errDetail = "Failed to connect repository";
      try {
        const err = await res.json();
        errDetail = err.detail || err.message || errDetail;
      } catch {
        const text = await res.text();
        if (text) errDetail = text;
      }
      throw new Error(errDetail);
    }
    const data = await res.json();
    return {
      repository: mapRepository(data.repository),

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

export async function reindexRepository(
  repositoryId: string
): Promise<{ repository: Repository; architecture: ArchitectureOverview } | null> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/repositories/${repositoryId}/reindex`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });

    if (!res.ok) {
      let errDetail = "Failed to reindex repository";
      try {
        const err = await res.json();
        errDetail = err.detail || err.message || errDetail;
      } catch {
        const text = await res.text();
        if (text) errDetail = text;
      }
      throw new Error(errDetail);
    }
    const data = await res.json();

    return {
      repository: mapRepository(data.repository),
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
    console.error("reindexRepository error:", error);
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

export async function fetchProjectContext(
  repositoryId: string,
  component?: string
): Promise<ProjectContext | null> {
  try {
    const url = new URL(`${API_BASE}/api/v1/repositories/${repositoryId}/context`);
    if (component) url.searchParams.set("component", component);
    const res = await fetch(url.toString(), { cache: "no-store" });
    if (!res.ok) return null;
    const data = await res.json();
    return {
      targetType: data.target_type,
      targetId: data.target_id,
      targetName: data.target_name,
      summary: data.summary,
      confidence: data.confidence,
      provenance: data.provenance,
      entities: (data.entities || []).map((e: any) => ({
        id: e.id,
        name: e.name,
        kind: e.kind,
        path: e.path,
        language: e.language,
        signature: e.signature,
        lineStart: e.line_start,
        lineEnd: e.line_end,
      })),
      relationships: (data.relationships || []).map((r: any) => ({
        sourceName: r.source_name,
        sourcePath: r.source_path,
        targetName: r.target_name,
        targetPath: r.target_path,
        type: r.type,
        confidence: r.confidence,
        resolutionMethod: r.resolution_method,
      })),
      evidence: (data.evidence || []).map((ev: any) => ({
        id: ev.id,
        sourcePath: ev.source_path,
        kind: ev.kind,
        content: ev.content,
        confidence: ev.confidence,
        provenance: ev.provenance,
      })),
      unknowns: (data.unknowns || []).map((u: any) => ({
        kind: u.kind,
        target: u.target,
        description: u.description,
        severity: u.severity,
      })),
      humanMarkdown: data.human_markdown,
      llmPromptContext: data.llm_prompt_context,
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

export async function fetchRepositoryCommits(
  repositoryId: string,
  filePath?: string,
  author?: string
): Promise<CommitItem[]> {
  try {
    const url = new URL(`${API_BASE}/api/v1/repositories/${repositoryId}/commits`);
    if (filePath) url.searchParams.set("file_path", filePath);
    if (author) url.searchParams.set("author", author);
    const res = await fetch(url.toString(), { cache: "no-store" });
    if (!res.ok) return [];
    const data = await res.json();
    return data.map((c: any) => ({
      id: c.id,
      repositoryId: c.repository_id,
      commitHash: c.commit_hash,
      authorName: c.author_name,
      authorEmail: c.author_email,
      committedAt: c.committed_at,
      message: c.message,
      filesChangedCount: c.files_changed_count,
      insertions: c.insertions,
      deletions: c.deletions,
      fileChanges: (c.file_changes || []).map((fc: any) => ({
        id: fc.id,
        commitId: fc.commit_id,
        filePath: fc.file_path,
        changeType: fc.change_type,
        insertions: fc.insertions,
        deletions: fc.deletions,
        oldPath: fc.old_path,
      })),
      linkedPullRequests: (c.linked_pull_requests || []).map((pl: any) => ({
        prNumber: pl.pr_number,
        linkType: pl.link_type,
        rawReference: pl.raw_reference,
        confidence: pl.confidence,
        title: pl.title,
        state: pl.state,
        author: pl.author,
        mergedAt: pl.merged_at,
        labels: pl.labels || [],
        htmlUrl: pl.html_url,
      })),
      linkedIssues: (c.linked_issues || []).map((il: any) => ({
        issueNumber: il.issue_number,
        linkType: il.link_type,
        rawReference: il.raw_reference,
        confidence: il.confidence,
        title: il.title,
        state: il.state,
        author: il.author,
        closedAt: il.closed_at,
        labels: il.labels || [],
        htmlUrl: il.html_url,
      })),
    }));
  } catch (error) {
    return [];
  }
}

export async function fetchRepositoryPullRequests(
  repositoryId: string,
  state?: string
): Promise<PullRequestItem[]> {
  try {
    const url = new URL(`${API_BASE}/api/v1/repositories/${repositoryId}/pull-requests`);
    if (state) url.searchParams.set("state", state);
    const res = await fetch(url.toString(), { cache: "no-store" });
    if (!res.ok) return [];
    const data = await res.json();
    return data.map((p: any) => ({
      id: p.id,
      repositoryId: p.repository_id,
      number: p.number,
      title: p.title,
      body: p.body,
      state: p.state,
      author: p.author,
      mergedAt: p.merged_at,
      closedAt: p.closed_at,
      labels: p.labels || [],
      htmlUrl: p.html_url,
      createdAt: p.created_at,
      linkedIssues: (p.linked_issues || []).map((il: any) => ({
        issueNumber: il.issue_number,
        linkType: il.link_type,
        rawReference: il.raw_reference,
        confidence: il.confidence,
        title: il.title,
        state: il.state,
        author: il.author,
        closedAt: il.closed_at,
        labels: il.labels || [],
        htmlUrl: il.html_url,
      })),
      linkedCommits: p.linked_commits || [],
    }));
  } catch (error) {
    return [];
  }
}

export async function fetchRepositoryIssues(
  repositoryId: string,
  state?: string
): Promise<IssueItem[]> {
  try {
    const url = new URL(`${API_BASE}/api/v1/repositories/${repositoryId}/issues`);
    if (state) url.searchParams.set("state", state);
    const res = await fetch(url.toString(), { cache: "no-store" });
    if (!res.ok) return [];
    const data = await res.json();
    return data.map((i: any) => ({
      id: i.id,
      repositoryId: i.repository_id,
      number: i.number,
      title: i.title,
      body: i.body,
      state: i.state,
      author: i.author,
      closedAt: i.closed_at,
      labels: i.labels || [],
      htmlUrl: i.html_url,
      createdAt: i.created_at,
      linkedPullRequests: (i.linked_pull_requests || []).map((pl: any) => ({
        prNumber: pl.pr_number,
        linkType: pl.link_type,
        rawReference: pl.raw_reference,
        confidence: pl.confidence,
        title: pl.title,
        state: pl.state,
        author: pl.author,
        mergedAt: pl.merged_at,
        labels: pl.labels || [],
        htmlUrl: pl.html_url,
      })),
      linkedCommits: i.linked_commits || [],
    }));
  } catch (error) {
    return [];
  }
}

export async function fetchHistoricalTrace(
  repositoryId: string,
  filePath: string
): Promise<HistoricalTraceResponse | null> {
  try {
    const res = await fetch(
      `${API_BASE}/api/v1/repositories/${repositoryId}/trace/${encodeURIComponent(filePath)}`,
      { cache: "no-store" }
    );
    if (!res.ok) return null;
    const data = await res.json();
    return {
      filePath: data.file_path,
      totalCommits: data.total_commits,
      totalPullRequests: data.total_pull_requests,
      totalIssues: data.total_issues,
      traceChain: (data.trace_chain || []).map((tc: any) => ({
        commitHash: tc.commit_hash,
        authorName: tc.author_name,
        committedAt: tc.committed_at,
        message: tc.message,
        changeType: tc.change_type,
        insertions: tc.insertions,
        deletions: tc.deletions,
        linkedPullRequests: tc.linked_pull_requests || [],
        linkedIssues: tc.linked_issues || [],
      })),
      allPullRequests: data.all_pull_requests || [],
      allIssues: data.all_issues || [],
    };
  } catch (error) {
    return null;
  }
}

export async function fetchFileHistory(
  repositoryId: string,
  filePath: string
): Promise<FileHistoryResponse | null> {
  try {
    const res = await fetch(
      `${API_BASE}/api/v1/repositories/${repositoryId}/files/${encodeURIComponent(filePath)}/history`,
      { cache: "no-store" }
    );
    if (!res.ok) return null;
    return await res.json();
  } catch (error) {
    return null;
  }
}

export async function fetchComponentHistory(
  repositoryId: string,
  componentPath: string
): Promise<ComponentHistoryResponse | null> {
  try {
    const res = await fetch(
      `${API_BASE}/api/v1/repositories/${repositoryId}/components/${encodeURIComponent(componentPath)}/history`,
      { cache: "no-store" }
    );
    if (!res.ok) return null;
    return await res.json();
  } catch (error) {
    return null;
  }
}

export async function ingestRepositoryCommits(
  repositoryId: string,
  commits: any[]
): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/repositories/${repositoryId}/commits/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ commits }),
    });
    return res.ok;
  } catch (error) {
    return false;
  }
}

export async function ingestRepositoryPullRequests(
  repositoryId: string,
  pullRequests: any[]
): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/repositories/${repositoryId}/pull-requests/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pull_requests: pullRequests }),
    });
    return res.ok;
  } catch (error) {
    return false;
  }
}

export async function ingestRepositoryIssues(
  repositoryId: string,
  issues: any[]
): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/repositories/${repositoryId}/issues/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ issues }),
    });
    return res.ok;
  } catch (error) {
    return false;
  }
}

