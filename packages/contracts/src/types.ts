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
