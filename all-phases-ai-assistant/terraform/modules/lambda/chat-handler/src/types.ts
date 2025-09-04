export interface ChatRequest {
  question: string;
  conversationId?: string;
  userId: string;
  queryComplexity?: QueryComplexity;
  includeSourceDetails: boolean;
  useAdvancedRAG: boolean;
}

export interface ChatResponse {
  answer: string;
  sources: DocumentSource[];
  conversationId: string;
  timestamp: string;
  modelUsed: string;
  tokenUsage: TokenUsage;
  cost: number;
  ragConfig?: RAGConfiguration;
  qualityMetrics?: ResponseQuality;
}

export interface RAGConfiguration {
  hybridSearch: HybridSearchConfig;
  retrieval: RetrievalParams;
  qualityThresholds: {
    minConfidence: number;
    minSources: number;
    minAnswerLength: number;
  };
}

export interface HybridSearchConfig {
  searchType: 'HYBRID' | 'SEMANTIC' | 'KEYWORD';
  semanticWeight: number;
  keywordWeight: number;
}

export interface RetrievalParams {
  numberOfResults: number;
  confidenceThreshold: number;
  maxChunkSize?: number;
  overlapPercentage?: number;
}

export interface ResponseQuality {
  isComplete: boolean;
  hasReliableSources: boolean;
  qualityScore: number;
  completenessScore: number;
  reliabilityScore: number;
  coherenceScore: number;
  warnings: string[];
}

export interface DocumentSource {
  documentId: string;
  fileName: string; // Required to match frontend expectations
  excerpt: string;
  confidence: number;
  s3Location?: string;
  pageNumber?: number;
}

export interface TokenUsage {
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
}

export enum QueryComplexity {
  SIMPLE = 'simple',
  MODERATE = 'moderate', 
  COMPLEX = 'complex'
}

export interface ModelConfig {
  modelArn: string;
  name: string;
  costPerInputToken: number;
  costPerOutputToken: number;
  latencyTier: 'fast' | 'moderate' | 'slow';
  capabilities: string[];
  maxContextLength: number;
}

export interface ConversationContext {
  conversationId: string;
  userId: string;
  messages: ConversationMessage[];
  createdAt: string;
  lastActivity: string;
}

export interface ConversationMessage {
  messageId: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sources?: DocumentSource[];
}

export interface BedrockError extends Error {
  code?: string;
  statusCode?: number;
  retryable?: boolean;
}

export interface StreamingResponse {
  stream: any;
  sources: DocumentSource[];
  conversationId: string;
  modelUsed: string;
}

export interface ChatApiRequest {
  question: string;
  conversationId?: string;
  userId: string;
  queryComplexity?: QueryComplexity;
  useAdvancedRAG?: boolean;
  enableStreaming?: boolean;
}

export interface ConversationHistoryRequest {
  conversationId: string;
  userId: string;
  limit?: number;
}

export interface ConversationListRequest {
  userId: string;
  limit?: number;
}