export type RepositoryStatus = 'idle' | 'indexing' | 'ready' | 'failed';

export interface HealthResponse {
  status: 'ok' | 'degraded' | 'error';
  version: string;
  database: 'connected' | 'disconnected';
  timestamp: string;
}

export interface Repository {
  id: string;
  owner: string;
  name: string;
  fullName: string;
  defaultBranch: string;
  status: RepositoryStatus;
  indexedAt?: string | null;
  fileCount: number;
  symbolCount: number;
  commitCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface SourceFile {
  id: string;
  repositoryId: string;
  path: string;
  language: string;
  contentHash: string;
  sizeBytes: number;
  summary?: string | null;
  createdAt: string;
  updatedAt: string;
}

export type SymbolKind = 'function' | 'class' | 'interface' | 'type' | 'variable' | 'constant' | 'module' | 'method';

export interface SymbolItem {
  id: string;
  fileId: string;
  repositoryId: string;
  name: string;
  kind: SymbolKind;
  lineStart: number;
  lineEnd: number;
  signature?: string | null;
  docstring?: string | null;
  createdAt: string;
}

export interface CodeDependencyItem {
  id: string;
  sourceFileId: string;
  sourcePath: string;
  targetPath: string;
  importedSymbol?: string | null;
  kind: 'internal' | 'external' | 'relative';
}

export interface ContextEntity {
  id: string;
  name: string;
  kind: string; // 'file' | 'symbol' | 'component'
  path: string;
  language?: string;
  signature?: string;
  lineStart?: number;
  lineEnd?: number;
}

export interface ContextRelationship {
  sourceName: string;
  sourcePath: string;
  targetName: string;
  targetPath: string;
  type: string; // 'imports' | 'calls' | 'extends' | 'implements' | 'tested_by'
  confidence: number;
  resolutionMethod: string;
}

export interface ContextEvidence {
  id: string;
  sourcePath: string;
  kind: string; // 'ast_symbol' | 'import_statement' | 'test_binding' | 'file_header'
  content: string;
  confidence: number;
  provenance: string;
}

export interface ContextUnknown {
  kind: string; // 'untested' | 'unresolved_dependency' | 'missing_signature' | 'empty_file' | 'low_confidence'
  target: string;
  description: string;
  severity: 'low' | 'medium' | 'high';
}

export interface ProjectContext {
  targetType: 'repository' | 'component' | 'file' | 'symbol';
  targetId: string;
  targetName: string;
  summary: string;
  confidence: number;
  provenance: string;
  entities: ContextEntity[];
  relationships: ContextRelationship[];
  evidence: ContextEvidence[];
  unknowns: ContextUnknown[];
  humanMarkdown: string;
  llmPromptContext: string;
}

export interface ComponentRelationship {
  sourceName: string;
  sourcePath: string;
  targetName: string;
  targetPath: string;
  type: 'imports' | 'calls' | 'extends' | 'implements' | 'tested_by';
  confidence?: number;
  resolutionMethod?: string;
}

export interface ComponentBriefItem {
  name: string;
  path: string;
  language: string;
  symbolCount: number;
  symbols: Array<{ name: string; kind: string; signature?: string }>;
  dependencies: Array<{ target: string; symbol?: string; kind: string; confidence?: string }>;
  callers: Array<{ caller: string; path: string; type: string }>;
  tests: string[];
  humanSummary: string;
  llmContext: string;
}

export interface ContextBriefResponse {
  repositoryId: string;
  fullName: string;
  fileCount: number;
  symbolCount: number;
  dependencyCount: number;
  languages: Record<string, number>;
  components: ComponentBriefItem[];
  humanSummary: string;
  llmContext: string;
  projectContext?: ProjectContext;
}


export interface ArchitectureOverview {
  repositoryId: string;
  fileCount: number;
  symbolCount: number;
  dependencyCount: number;
  languages: Record<string, number>;
  majorComponents: Array<{
    name: string;
    path: string;
    symbolCount: number;
    dependencies: string[];
    testedBy?: string | null;
  }>;
  relationships: ComponentRelationship[];
}


export interface RepositoryTreeItem {
  path: string;
  type: 'file' | 'directory';
  language?: string;
  symbolCount?: number;
  children?: RepositoryTreeItem[];
}

export interface CommitItem {
  id: string;
  repositoryId: string;
  commitHash: string;
  authorName: string;
  authorEmail: string;
  committedAt: string;
  message: string;
}

export interface PullRequestItem {
  id: string;
  repositoryId: string;
  number: number;
  title: string;
  body?: string | null;
  state: 'open' | 'closed' | 'merged';
  author: string;
  mergedAt?: string | null;
  createdAt: string;
}

export interface IssueItem {
  id: string;
  repositoryId: string;
  number: number;
  title: string;
  body?: string | null;
  state: 'open' | 'closed';
  author: string;
  closedAt?: string | null;
  createdAt: string;
}

export type InvestigationType = 'understand' | 'why' | 'history' | 'before_change';
export type InvestigationStatus = 'pending' | 'planning' | 'gathering' | 'reasoning' | 'completed' | 'failed';
export type ClaimClassification = 'fact' | 'inference' | 'unknown';

export interface EvidenceItem {
  id: string;
  sourceType: 'code' | 'commit' | 'pull_request' | 'issue' | 'doc';
  sourceId: string;
  title: string;
  snippet: string;
  path?: string | null;
  lineStart?: number | null;
  lineEnd?: number | null;
  confidence: number;
  metadata?: Record<string, unknown>;
}

export interface InvestigationClaim {
  id: string;
  classification: ClaimClassification;
  statement: string;
  evidenceIds: string[];
}

export interface InvestigationRequest {
  repositoryId: string;
  query: string;
  type?: InvestigationType;
  targetPath?: string;
  targetSymbol?: string;
}

export interface InvestigationResponse {
  id: string;
  repositoryId: string;
  query: string;
  type: InvestigationType;
  status: InvestigationStatus;
  summary: string;
  answer: string;
  evidence: EvidenceItem[];
  claims: InvestigationClaim[];
  tokenUsage?: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
  latencyMs?: number;
  createdAt: string;
}
