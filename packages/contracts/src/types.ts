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
  introducingCommit?: string;
  introducingDate?: string;
  lastModifiedCommit?: string;
  lastModifiedDate?: string;
  changeCount?: number;
  activeAuthors?: string[];
  relatedAdrs?: string[];
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
  kind: string; // 'ast_symbol' | 'import_statement' | 'test_binding' | 'file_header' | 'git_commit' | 'pull_request' | 'issue' | 'architecture_decision' | 'design_constraint'
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

export interface ContextHistoricalChange {
  commitHash: string;
  message: string;
  author: string;
  committedAt: string;
  changeType?: 'added' | 'modified' | 'deleted' | 'renamed' | string;
  filesChanged?: string[];
  isIntroducing?: boolean;
  prNumber?: number;
}

export interface ContextPullRequest {
  prNumber: number;
  title: string;
  state: string;
  author: string;
  mergedAt?: string;
  url?: string;
  linkedIssueNumbers?: number[];
}

export interface ContextIssue {
  issueNumber: number;
  title: string;
  state: string;
  author: string;
  closedAt?: string;
  labels?: string[];
  url?: string;
}

export interface ContextDocument {
  id: string;
  path: string;
  title: string;
  docType: string;
  status?: string;
  deciders?: string;
  summary?: string;
}

export interface ContextDesignConstraint {
  id: string;
  domain: string;
  constraintText: string;
  sourceDocPath: string;
  priority?: string;
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
  historicalChanges?: ContextHistoricalChange[];
  relatedPrs?: ContextPullRequest[];
  relatedIssues?: ContextIssue[];
  documents?: ContextDocument[];
  designConstraints?: ContextDesignConstraint[];
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

export interface CommitFileChangeItem {
  id: string;
  commitId: string;
  filePath: string;
  changeType: 'added' | 'modified' | 'deleted' | 'renamed';
  insertions: number;
  deletions: number;
  oldPath?: string | null;
}

export interface LinkedPullRequest {
  prNumber: number;
  linkType: string;
  rawReference?: string | null;
  confidence?: number;
  title?: string | null;
  state?: 'open' | 'closed' | 'merged' | null;
  author?: string | null;
  mergedAt?: string | null;
  labels?: string[];
  htmlUrl?: string | null;
}

export interface LinkedIssue {
  issueNumber: number;
  linkType: string;
  rawReference?: string | null;
  confidence?: number;
  title?: string | null;
  state?: 'open' | 'closed' | null;
  author?: string | null;
  closedAt?: string | null;
  labels?: string[];
  htmlUrl?: string | null;
}

export interface CommitItem {
  id: string;
  repositoryId: string;
  commitHash: string;
  authorName: string;
  authorEmail: string;
  committedAt: string;
  message: string;
  filesChangedCount?: number;
  insertions?: number;
  deletions?: number;
  fileChanges?: CommitFileChangeItem[];
  linkedPullRequests?: LinkedPullRequest[];
  linkedIssues?: LinkedIssue[];
}

export interface FileHistoryResponse {
  filePath: string;
  totalCommits: number;
  introducingCommit?: {
    commit_hash: string;
    author_name: string;
    author_email: string;
    committed_at: string;
    message: string;
    change_type: string;
    insertions: number;
    deletions: number;
    linked_pull_requests?: Array<Record<string, any>>;
    linked_issues?: Array<Record<string, any>>;
  } | null;
  commits: Array<{
    commit_hash: string;
    author_name: string;
    author_email: string;
    committed_at: string;
    message: string;
    change_type: string;
    insertions: number;
    deletions: number;
    linked_pull_requests?: Array<Record<string, any>>;
    linked_issues?: Array<Record<string, any>>;
  }>;
  authors: Array<{
    name: string;
    email: string;
    commit_count: number;
  }>;
}

export interface ComponentHistoryResponse {
  componentPath: string;
  totalCommits: number;
  introducingCommit?: Record<string, any> | null;
  commits: Array<Record<string, any>>;
  topAuthors: Array<{ name: string; commits: number }>;
  filesTouched: Array<{ path: string; modifications: number }>;
  evolutionTimeline?: ComponentMilestoneEvent[];
}

export interface ComponentMilestoneEvent {
  id: string;
  eventType: 'introduction' | 'feature_addition' | 'refactor' | 'bug_fix' | 'architectural_decision' | 'maintenance';
  title: string;
  summary: string;
  timestamp: string;
  author?: string | null;
  commitHash?: string | null;
  insertions?: number | null;
  deletions?: number | null;
  filesChanged?: number | null;
  linkedPullRequests?: Array<{
    pr_number: number;
    link_type: string;
    raw_reference?: string;
  }>;
  linkedIssues?: Array<{
    issue_number: number;
    link_type: string;
    raw_reference?: string;
  }>;
  linkedAdrs?: Array<{
    id: string;
    title: string;
    path: string;
    status: string;
    deciders?: string | null;
  }>;
  citations?: string[];
}

export interface ComponentTimelineResponse {
  repositoryId: string;
  componentPath: string;
  totalEvents: number;
  introducingEvent?: ComponentMilestoneEvent | null;
  milestones: ComponentMilestoneEvent[];
  summary: string;
  topAuthors: Array<{ name: string; commits: number }>;
}

export interface HistoricalTraceItem {
  commitHash: string;
  authorName: string;
  committedAt: string;
  message: string;
  changeType: string;
  insertions: number;
  deletions: number;
  linkedPullRequests: Array<Record<string, any>>;
  linkedIssues: Array<Record<string, any>>;
}

export interface HistoricalTraceResponse {
  filePath: string;
  totalCommits: number;
  totalPullRequests: number;
  totalIssues: number;
  traceChain: HistoricalTraceItem[];
  allPullRequests: Array<Record<string, any>>;
  allIssues: Array<Record<string, any>>;
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
  closedAt?: string | null;
  labels?: string[];
  htmlUrl?: string | null;
  createdAt: string;
  linkedIssues?: LinkedIssue[];
  linkedCommits?: Array<{
    commitHash: string;
    message: string;
    authorName: string;
    committedAt: string;
    linkType: string;
  }>;
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
  labels?: string[];
  htmlUrl?: string | null;
  createdAt: string;
  linkedPullRequests?: LinkedPullRequest[];
  linkedCommits?: Array<{
    commitHash: string;
    message: string;
    authorName: string;
    committedAt: string;
    linkType: string;
  }>;
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

export interface KameiMetrics {
  linesAdded: number;
  linesDeleted: number;
  filesTouched: number;
  distinctDirectories: number;
  distinctSubsystems: number;
  shannonEntropy: number;
}

export interface ChangeRiskReport {
  riskScore: number;
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  kameiMetrics: KameiMetrics;
  defectPressure: number;
  explanatoryFactors: string[];
  fixCommitCount?: number;
}

export interface InvestigationRequest {
  repositoryId: string;
  query: string;
  type?: InvestigationType;
  targetPath?: string;
  targetSymbol?: string;
  diff?: string;
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

export interface HistoricalEvidenceRecord {
  id: string;
  sourceType: 'commit' | 'pull_request' | 'issue';
  sourceId: string;
  title: string;
  snippet: string;
  author?: string | null;
  timestamp?: string | null;
  confidence: number;
  score: number;
  metadata?: Record<string, unknown>;
  citations?: string[];
}

export interface HistoricalSearchQuery {
  query?: string;
  author?: string;
  filePath?: string;
  state?: string;
  label?: string;
  since?: string;
  until?: string;
  limit?: number;
}

export interface HistoricalSearchResponse {
  repositoryId: string;
  query?: string | null;
  totalCommits: number;
  totalPullRequests: number;
  totalIssues: number;
  commits: CommitItem[];
  pullRequests: PullRequestItem[];
  issues: IssueItem[];
}

export interface HistoricalRetrievalRequest {
  query?: string;
  componentPath?: string;
  filePath?: string;
  symbolName?: string;
  author?: string;
  since?: string;
  until?: string;
  sourceTypes?: Array<'commit' | 'pull_request' | 'issue'>;
  limit?: number;
}

export interface HistoricalRetrievalResponse {
  repositoryId: string;
  query?: string | null;
  scope: Record<string, unknown>;
  totalEvidenceCount: number;
  evidence: HistoricalEvidenceRecord[];
  summary: string;
}

export interface SymbolHistoryResponse {
  symbolName: string;
  filePath: string;
  lineStart?: number | null;
  lineEnd?: number | null;
  introducingCommit?: {
    commitHash: string;
    authorName: string;
    committedAt: string;
    message: string;
  } | null;
  totalCommits: number;
  commits: Array<{
    commitHash: string;
    authorName: string;
    committedAt: string;
    message: string;
    changeType: string;
    insertions: number;
    deletions: number;
    mentionsSymbol: boolean;
    linkedPullRequests: LinkedPullRequest[];
    linkedIssues: LinkedIssue[];
  }>;
  linkedPullRequests: LinkedPullRequest[];
  linkedIssues: LinkedIssue[];
  evolutionTimeline: Array<{
    eventType: string;
    timestamp: string;
    commitHash: string;
    author: string;
    summary: string;
    linkedPrs: number[];
    linkedIssues: number[];
  }>;
}

export type EngineeringDocType =
  | 'readme'
  | 'architecture'
  | 'adr'
  | 'design_doc'
  | 'testing_guide'
  | 'general_doc';

export type ADRStatus =
  | 'accepted'
  | 'superseded'
  | 'proposed'
  | 'deprecated'
  | 'draft'
  | 'n/a';

export type ConstraintCategory =
  | 'security'
  | 'performance'
  | 'architecture'
  | 'testing'
  | 'data_integrity'
  | 'general';

export type ConstraintLevel = 'must' | 'should' | 'must_not';

export interface DesignConstraintItem {
  id: string;
  repositoryId: string;
  documentId?: string | null;
  category: ConstraintCategory;
  level: ConstraintLevel;
  title: string;
  statement: string;
  sourcePath: string;
  lineStart?: number | null;
  lineEnd?: number | null;
  confidence: number;
  extraMetadata?: Record<string, unknown>;
  createdAt: string;
}

export interface EngineeringDocumentItem {
  id: string;
  repositoryId: string;
  path: string;
  docType: EngineeringDocType;
  title: string;
  format: string;
  contentHash: string;
  status: ADRStatus;
  deciders?: string | null;
  summary?: string | null;
  extraMetadata?: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface EngineeringDocumentDetailItem extends EngineeringDocumentItem {
  rawContent: string;
  constraints: DesignConstraintItem[];
}

export interface ADRItem {
  id: string;
  repositoryId: string;
  path: string;
  title: string;
  status: ADRStatus;
  deciders?: string | null;
  summary?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface EngineeringSearchResponse {
  repositoryId: string;
  query: string;
  totalMatches: number;
  docs: Array<Record<string, unknown>>;
  constraints: Array<Record<string, unknown>>;
}

export interface EngineeringContextOverviewResponse {
  repositoryId: string;
  totalDocs: number;
  totalAdrs: number;
  totalConstraints: number;
  docsByType: Record<string, number>;
  constraintsByCategory: Record<string, number>;
  adrs: ADRItem[];
  topConstraints: DesignConstraintItem[];
}


