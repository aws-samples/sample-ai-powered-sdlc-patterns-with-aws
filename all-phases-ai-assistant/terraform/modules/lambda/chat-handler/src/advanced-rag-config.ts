import { RetrieveAndGenerateCommandOutput } from '@aws-sdk/client-bedrock-agent-runtime';
import { DocumentSource } from './types';

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

export interface EnhancedDocumentSource extends DocumentSource {
  chunkId?: string;
  relevanceScore: number;
  contextualRelevance?: number;
  semanticSimilarity?: number;
  keywordMatches?: string[];
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

export interface RAGConfiguration {
  hybridSearch: HybridSearchConfig;
  retrieval: RetrievalParams;
  qualityThresholds: {
    minConfidence: number;
    minSources: number;
    minAnswerLength: number;
  };
}

export class AdvancedRAGConfig {
  private readonly defaultConfigs: Record<string, RAGConfiguration> = {
    simple: {
      hybridSearch: {
        searchType: 'HYBRID',
        semanticWeight: 0.6,
        keywordWeight: 0.4
      },
      retrieval: {
        numberOfResults: 3,
        confidenceThreshold: 0.7
      },
      qualityThresholds: {
        minConfidence: 0.6,
        minSources: 1,
        minAnswerLength: 50
      }
    },
    moderate: {
      hybridSearch: {
        searchType: 'HYBRID',
        semanticWeight: 0.7,
        keywordWeight: 0.3
      },
      retrieval: {
        numberOfResults: 5,
        confidenceThreshold: 0.6
      },
      qualityThresholds: {
        minConfidence: 0.5,
        minSources: 2,
        minAnswerLength: 100
      }
    },
    complex: {
      hybridSearch: {
        searchType: 'HYBRID',
        semanticWeight: 0.8,
        keywordWeight: 0.2
      },
      retrieval: {
        numberOfResults: 8,
        confidenceThreshold: 0.5
      },
      qualityThresholds: {
        minConfidence: 0.4,
        minSources: 3,
        minAnswerLength: 150
      }
    }
  };

  /**
   * Get hybrid search configuration based on query complexity
   */
  getHybridSearchConfig(complexity: string): HybridSearchConfig {
    const config = this.defaultConfigs[complexity] || this.defaultConfigs.moderate;
    return config.hybridSearch;
  }

  /**
   * Get retrieval parameters based on query complexity
   */
  getRetrievalParams(complexity: string): RetrievalParams {
    const config = this.defaultConfigs[complexity] || this.defaultConfigs.moderate;
    return config.retrieval;
  }

  /**
   * Extract enhanced source information from Knowledge Base response
   */
  extractEnhancedSources(response: RetrieveAndGenerateCommandOutput): EnhancedDocumentSource[] {
    if (!response.citations) {
      return [];
    }

    return response.citations.map((citation, index) => {
      const reference = citation.retrievedReferences?.[0];
      const metadata = reference?.metadata || {};
      
      // Extract metadata fields
      const fileName = this.extractMetadataString(metadata, 'x-amz-bedrock-kb-source-uri', 'Unknown');
      const scoreValue = this.extractMetadataString(metadata, 'score', '0');
      const chunkId = this.extractMetadataString(metadata, 'x-amz-bedrock-kb-chunk-id');
      
      // Calculate relevance scores
      const confidence = parseFloat(scoreValue);
      const relevanceScore = this.calculateRelevanceScore(reference, citation);
      
      return {
        documentId: reference?.location?.s3Location?.uri || `doc-${index}`,
        fileName,
        excerpt: reference?.content?.text || '',
        confidence,
        s3Location: reference?.location?.s3Location?.uri,
        chunkId,
        relevanceScore,
        contextualRelevance: this.calculateContextualRelevance(reference),
        semanticSimilarity: confidence, // Use confidence as semantic similarity proxy
        keywordMatches: this.extractKeywordMatches(reference?.content?.text || '')
      };
    });
  }

  /**
   * Filter sources by relevance threshold
   */
  filterByRelevance(sources: any[], threshold: number): any[] {
    return sources.filter(source => source.confidence >= threshold);
  }

  /**
   * Sort sources by relevance (confidence score)
   */
  sortByRelevance(sources: any[]): any[] {
    return [...sources].sort((a, b) => b.confidence - a.confidence);
  }

  /**
   * Validate response quality and completeness
   */
  validateResponseQuality(response: { answer: string; sources: any[] }): ResponseQuality {
    const completenessScore = this.calculateCompletenessScore(response.answer);
    const reliabilityScore = this.calculateReliabilityScore(response.sources);
    const coherenceScore = this.calculateCoherenceScore(response.answer);
    
    const qualityScore = (completenessScore + reliabilityScore + coherenceScore) / 3;
    
    const warnings: string[] = [];
    if (completenessScore < 0.5) warnings.push('Response may be incomplete');
    if (reliabilityScore < 0.5) warnings.push('Low confidence in sources');
    if (coherenceScore < 0.5) warnings.push('Response may lack coherence');
    
    return {
      isComplete: completenessScore >= 0.5, // Inclusive threshold for more realistic assessment
      hasReliableSources: reliabilityScore > 0.6,
      qualityScore,
      completenessScore,
      reliabilityScore,
      coherenceScore,
      warnings
    };
  }

  /**
   * Get complete RAG configuration for a given complexity
   */
  getRAGConfiguration(complexity: string): RAGConfiguration {
    return this.defaultConfigs[complexity] || this.defaultConfigs.moderate;
  }

  /**
   * Apply advanced filtering and ranking to sources
   */
  enhanceSourceRanking(sources: EnhancedDocumentSource[], query: string): EnhancedDocumentSource[] {
    // Apply contextual relevance scoring
    const enhancedSources = sources.map(source => ({
      ...source,
      contextualRelevance: this.calculateQuerySpecificRelevance(source, query)
    }));

    // Sort by combined relevance score
    return enhancedSources.sort((a, b) => {
      const scoreA = (a.confidence * 0.4) + (a.relevanceScore * 0.3) + (a.contextualRelevance || 0) * 0.3;
      const scoreB = (b.confidence * 0.4) + (b.relevanceScore * 0.3) + (b.contextualRelevance || 0) * 0.3;
      return scoreB - scoreA;
    });
  }

  // Private helper methods

  private extractMetadataString(metadata: any, key: string, defaultValue: string = ''): string {
    const value = metadata[key];
    return typeof value === 'string' ? value : defaultValue;
  }

  private calculateRelevanceScore(reference: any, citation: any): number {
    // Calculate relevance based on multiple factors
    let score = 0;
    
    // Text length factor (longer excerpts may be more informative)
    const textLength = reference?.content?.text?.length || 0;
    score += Math.min(textLength / 500, 0.3); // Max 0.3 for length
    
    // Citation span factor (how much of the response is supported)
    const spanLength = citation?.generatedResponsePart?.textResponsePart?.span?.end - 
                      citation?.generatedResponsePart?.textResponsePart?.span?.start || 0;
    score += Math.min(spanLength / 100, 0.3); // Max 0.3 for span coverage
    
    // Base relevance
    score += 0.4;
    
    return Math.min(score, 1.0);
  }

  private calculateContextualRelevance(reference: any): number {
    // Simple heuristic based on content characteristics
    const text = reference?.content?.text || '';
    
    // Prefer sources with structured content (headings, lists, etc.)
    let score = 0.5;
    if (text.includes('##') || text.includes('- ')) score += 0.2;
    if (text.includes('```') || text.includes('`')) score += 0.1; // Code examples
    if (text.length > 200) score += 0.1; // Substantial content
    if (text.length > 500) score += 0.1; // Comprehensive content
    
    return Math.min(score, 1.0);
  }

  private extractKeywordMatches(text: string): string[] {
    // Simple keyword extraction (in production, use more sophisticated NLP)
    const words = text.toLowerCase().match(/\b\w{4,}\b/g) || [];
    const uniqueWords = [...new Set(words)];
    return uniqueWords.slice(0, 10); // Top 10 keywords
  }

  private calculateCompletenessScore(answer: string): number {
    if (!answer || answer.trim().length === 0) return 0;
    
    let score = 0.3; // Base score for having any answer
    
    // Length factor
    const length = answer.length;
    if (length > 50) score += 0.2;
    if (length > 150) score += 0.2;
    if (length > 300) score += 0.1;
    
    // Structure indicators
    if (answer.includes('.') && answer.split('.').length > 2) score += 0.1; // Multiple sentences
    if (answer.includes(':') || answer.includes('-')) score += 0.05; // Lists or explanations
    if (answer.match(/\b(because|therefore|however|additionally)\b/i)) score += 0.05; // Reasoning words
    
    return Math.min(score, 1.0);
  }

  private calculateReliabilityScore(sources: any[]): number {
    if (!sources || sources.length === 0) return 0;
    
    const avgConfidence = sources.reduce((sum, source) => sum + (source.confidence || 0), 0) / sources.length;
    const sourceCount = Math.min(sources.length / 3, 1); // Normalize to max 3 sources
    
    return (avgConfidence * 0.7) + (sourceCount * 0.3);
  }

  private calculateCoherenceScore(answer: string): number {
    if (!answer || answer.trim().length === 0) return 0;
    
    let score = 0.5; // Base score
    
    // Check for coherence indicators
    const sentences = answer.split(/[.!?]+/).filter(s => s.trim().length > 0);
    if (sentences.length > 1) {
      // Multiple sentences suggest structured response
      score += 0.2;
      
      // Check for transition words
      const transitions = answer.match(/\b(first|second|next|then|finally|however|therefore|additionally|furthermore)\b/gi);
      if (transitions && transitions.length > 0) score += 0.2;
    }
    
    // Penalize very short or very repetitive responses
    if (answer.length < 30) score -= 0.3;
    
    return Math.max(0, Math.min(score, 1.0));
  }

  private calculateQuerySpecificRelevance(source: EnhancedDocumentSource, query: string): number {
    const queryWords = query.toLowerCase().split(/\s+/);
    const sourceText = source.excerpt.toLowerCase();
    
    let matches = 0;
    for (const word of queryWords) {
      if (word.length > 3 && sourceText.includes(word)) {
        matches++;
      }
    }
    
    return Math.min(matches / queryWords.length, 1.0);
  }
}