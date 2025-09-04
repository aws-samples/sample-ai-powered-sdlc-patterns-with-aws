import {
    BedrockAgentRuntimeClient,
    RetrieveAndGenerateCommand,
    RetrieveAndGenerateCommandInput,
    RetrieveAndGenerateCommandOutput
} from '@aws-sdk/client-bedrock-agent-runtime';
import {
    BedrockRuntimeClient,
    InvokeModelCommand
} from '@aws-sdk/client-bedrock-runtime';
import { CloudWatchClient, PutMetricDataCommand } from '@aws-sdk/client-cloudwatch';
import { v4 as uuidv4 } from 'uuid';
import { AdvancedRAGConfig } from './advanced-rag-config';
import {
    classifyQueryComplexity,
    getModelConfigByName,
    selectOptimalModel
} from './model-config';
import {
    BedrockError,
    ChatResponse,
    DocumentSource,
    RAGConfiguration,
    ResponseQuality,
    TokenUsage
} from './types';
import { ChatRequest } from './validation';

export class BedrockService {
  private bedrockAgentRuntime: BedrockAgentRuntimeClient;
  private bedrockRuntime: BedrockRuntimeClient;
  private cloudWatch: CloudWatchClient;
  private knowledgeBaseId: string;
  private advancedRAG: AdvancedRAGConfig;
  private lastRequestTime: number = 0;
  private minRequestInterval: number = 1000; // Minimum 1 second between requests

  constructor() {
    // AWS Lambda automatically sets AWS_REGION, but it's a reserved environment variable
    // Use the runtime region or default to us-west-2
    const region = process.env.AWS_DEFAULT_REGION || process.env.AWS_REGION || 'us-west-2';
    
    // Configure AWS clients with proper credentials and extended timeout for Claude 4 models
    const clientConfig: any = { 
      region,
      // Claude 3.7 Sonnet and Claude 4 models require up to 60 minutes timeout
      requestHandler: {
        requestTimeout: 3600000, // 60 minutes in milliseconds
        connectionTimeout: 30000  // 30 seconds for connection
      }
    };
    
    // In test environment, use the aidlc_main profile
    if (process.env.NODE_ENV === 'test' || process.env.AWS_PROFILE) {
      clientConfig.credentials = undefined; // Let AWS SDK handle profile-based credentials
    }
    
    this.bedrockAgentRuntime = new BedrockAgentRuntimeClient(clientConfig);
    this.bedrockRuntime = new BedrockRuntimeClient(clientConfig);
    this.cloudWatch = new CloudWatchClient(clientConfig);
    this.advancedRAG = new AdvancedRAGConfig();
    // Read Knowledge Base ID at runtime instead of construction time
    this.knowledgeBaseId = '';
  }

  private getKnowledgeBaseId(): string {
    const knowledgeBaseId = process.env.KNOWLEDGE_BASE_ID;
    if (!knowledgeBaseId) {
      throw new Error('KNOWLEDGE_BASE_ID environment variable is not set. Please ensure the Knowledge Base is deployed and the Lambda function is configured correctly.');
    }
    return knowledgeBaseId;
  }

  async handleChatQuery(request: ChatRequest): Promise<ChatResponse> {
    const startTime = Date.now();
    
    try {
      // Classify query complexity if not provided
      const queryComplexity = request.queryComplexity || 
        classifyQueryComplexity(request.question);
      
      // Select optimal model
      const selectedModel = selectOptimalModel(queryComplexity);
      
      // Get available model (with fallback)
      const availableModel = await this.getAvailableClaudeModel();
      
      // Use RetrieveAndGenerate API without session management for Claude Sonnet 4
      // Let Bedrock generate a new session ID for each request
      const response = await this.retrieveAndGenerate(
        request.question,
        availableModel
        // Don't pass conversationId as sessionId - let Bedrock manage sessions
      );
      
      // Calculate token usage and cost
      const tokenUsage = this.extractTokenUsage(response);
      const modelConfig = getModelConfigByName(availableModel);
      const cost = this.calculateCost(tokenUsage, modelConfig);
      
      // Track metrics
      await this.trackMetrics(availableModel, tokenUsage, Date.now() - startTime);
      
      // Track Knowledge Base query metrics
      await this.trackKnowledgeBaseQueryMetrics(
        request.question,
        request.userId || 'unknown',
        Date.now() - startTime,
        true,
        response.citations?.length || 0
      );
      
      return {
        answer: response.output?.text || 'No response generated',
        sources: this.extractSources(response),
        conversationId: response.sessionId || request.conversationId || uuidv4(),
        timestamp: new Date().toISOString(),
        modelUsed: this.extractModelName(availableModel),
        tokenUsage,
        cost
      };
      
    } catch (error) {
      console.error('Error in handleChatQuery:', error);
      throw this.handleBedrockError(error as BedrockError);
    }
  }

  async handleChatQueryWithAdvancedRAG(request: ChatRequest): Promise<ChatResponse> {
    const startTime = Date.now();
    
    try {
      // Classify query complexity if not provided
      const queryComplexity = request.queryComplexity || 
        classifyQueryComplexity(request.question);
      
      // Get advanced RAG configuration
      const ragConfig = this.advancedRAG.getRAGConfiguration(queryComplexity);
      
      // Select optimal model
      const selectedModel = selectOptimalModel(queryComplexity);
      
      // Get available model (with fallback)
      const availableModel = await this.getAvailableClaudeModel();
      
      // Use RetrieveAndGenerate API with advanced configuration
      // Don't pass conversationId as sessionId for Claude Sonnet 4
      const response = await this.retrieveAndGenerateAdvanced(
        request.question,
        availableModel,
        ragConfig
        // Don't pass conversationId as sessionId - let Bedrock manage sessions
      );
      
      // Extract enhanced sources with advanced processing
      const enhancedSources = this.advancedRAG.extractEnhancedSources(response);
      
      // Apply relevance filtering and ranking
      const filteredSources = this.advancedRAG.filterByRelevance(
        enhancedSources, 
        ragConfig.qualityThresholds.minConfidence
      );
      
      const rankedSources = this.advancedRAG.enhanceSourceRanking(
        filteredSources,
        request.question
      );
      
      // Validate response quality
      const chatResponse = {
        answer: response.output?.text || 'No response generated',
        sources: rankedSources
      };
      
      const qualityMetrics = this.advancedRAG.validateResponseQuality(chatResponse);
      
      // Calculate token usage and cost
      const tokenUsage = this.extractTokenUsage(response);
      const modelConfig = getModelConfigByName(availableModel);
      const cost = this.calculateCost(tokenUsage, modelConfig);
      
      // Track advanced metrics
      await this.trackAdvancedMetrics(
        availableModel, 
        tokenUsage, 
        Date.now() - startTime,
        qualityMetrics,
        ragConfig
      );
      
      return {
        answer: chatResponse.answer,
        sources: rankedSources,
        conversationId: response.sessionId || request.conversationId || uuidv4(),
        timestamp: new Date().toISOString(),
        modelUsed: this.extractModelName(availableModel),
        tokenUsage,
        cost,
        ragConfig,
        qualityMetrics
      };
      
    } catch (error) {
      console.error('Error in handleChatQueryWithAdvancedRAG:', error);
      throw this.handleBedrockError(error as BedrockError);
    }
  }

  private async getAvailableClaudeModel(): Promise<string> {
    const environment = process.env.ENVIRONMENT || 'development';
    
    // TASK 1: Use Claude 3.5 Haiku as primary model with fallback chain
    // Primary: Claude 3.5 Haiku (reliable, cost-effective, proven compatibility)
    // Secondary: Claude 3.5 Sonnet v2 (high quality, may have compatibility issues)
    
    const modelFallbackChain = [
      {
        modelId: 'anthropic.claude-3-5-haiku-20241022-v1:0',
        modelArn: 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0',
        name: 'Claude 3.5 Haiku',
        priority: 1
      },
      {
        modelId: 'anthropic.claude-3-5-sonnet-20241022-v2:0',
        modelArn: 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0',
        name: 'Claude 3.5 Sonnet v2',
        priority: 2
      }
    ];

    // Try each model in priority order with availability validation
    for (const model of modelFallbackChain) {
      try {
        console.log(`Validating model availability: ${model.name} (${model.modelId})`);
        
        // Validate model availability before use
        const isAvailable = await this.validateModelAvailability(model.modelId);
        
        if (isAvailable) {
          console.log(`✓ Selected model: ${model.name} (${model.modelId})`);
          console.log(`Model selection reason: Priority ${model.priority} - ${model.name} is available and compatible`);
          
          // Log model selection decision for monitoring
          await this.logModelSelection(model.modelId, model.name, 'AVAILABLE', []);
          
          return model.modelId;
        } else {
          console.log(`✗ Model unavailable: ${model.name} (${model.modelId})`);
        }
        
      } catch (error) {
        console.log(`✗ Model validation failed: ${model.name} - ${error}`);
        // Continue to next model in fallback chain
      }
    }
    
    // If all models fail validation, fall back to Claude 3.5 Haiku (most reliable)
    const fallbackModel = modelFallbackChain[0];
    console.log(`⚠️ All models failed validation, using fallback: ${fallbackModel.name}`);
    
    await this.logModelSelection(
      fallbackModel.modelId, 
      fallbackModel.name, 
      'FALLBACK_USED', 
      modelFallbackChain.map(m => m.modelId)
    );
    
    return fallbackModel.modelId;
  }

  private async validateModelAvailability(modelId: string): Promise<boolean> {
    try {
      // Test model availability with a minimal request
      const testCommand = new InvokeModelCommand({
        modelId,
        body: JSON.stringify({
          anthropic_version: "bedrock-2023-05-31",
          max_tokens: 1,
          messages: [{ role: 'user', content: 'test' }]
        })
      });
      
      await this.executeWithRetry(() => this.bedrockRuntime.send(testCommand));
      return true;
      
    } catch (error: any) {
      console.error(`Model availability validation failed for ${modelId}:`, error.message);
      
      // Check if it's a model-specific error vs general API error
      if (error.name === 'AccessDeniedException' && error.message?.includes('GetInferenceProfile')) {
        console.error(`Model ${modelId} is being resolved as inference profile - this indicates a compatibility issue`);
        return false;
      }
      
      // Other errors might be temporary, so we'll consider the model potentially available
      // but log the issue for monitoring
      if (error.name === 'ThrottlingException' || error.name === 'ServiceUnavailableException') {
        console.warn(`Temporary error validating ${modelId}, assuming available: ${error.message}`);
        return true;
      }
      
      return false;
    }
  }

  private async logModelSelection(
    selectedModelId: string,
    selectedModelName: string,
    selectionReason: string,
    fallbacksAttempted: string[]
  ): Promise<void> {
    try {
      // Log to CloudWatch for monitoring and debugging
      const logData = {
        timestamp: new Date().toISOString(),
        selectedModel: selectedModelId,
        selectedModelName,
        selectionReason,
        fallbacksAttempted,
        environment: process.env.ENVIRONMENT || 'development'
      };
      
      console.log('MODEL_SELECTION_LOG:', JSON.stringify(logData));
      
      // Track model selection metrics
      const command = new PutMetricDataCommand({
        Namespace: 'AI-Assistant/ModelSelection',
        MetricData: [
          {
            MetricName: 'ModelSelectionEvent',
            Value: 1,
            Unit: 'Count',
            Dimensions: [
              { Name: 'SelectedModel', Value: selectedModelName },
              { Name: 'SelectionReason', Value: selectionReason }
            ]
          },
          {
            MetricName: 'FallbacksAttempted',
            Value: fallbacksAttempted.length,
            Unit: 'Count',
            Dimensions: [
              { Name: 'SelectedModel', Value: selectedModelName }
            ]
          }
        ]
      });
      
      await this.cloudWatch.send(command);
      
    } catch (error) {
      console.error('Failed to log model selection:', error);
      // Don't throw - logging failure shouldn't break the main flow
    }
  }



  private async retrieveAndGenerate(
    question: string,
    modelId: string
  ): Promise<RetrieveAndGenerateCommandOutput> {
    const knowledgeBaseId = this.getKnowledgeBaseId();
    
    // CRITICAL FIX: Use model ID directly for on-demand foundation models
    // For on-demand models like Claude 3.5 Sonnet v2, use model ID directly
    // Using full ARN causes AWS SDK to try resolving as inference profile
    console.log(`Using model ID for Knowledge Base (on-demand): ${modelId}`);
    
    const input: RetrieveAndGenerateCommandInput = {
      input: {
        text: question
      },
      retrieveAndGenerateConfiguration: {
        type: 'KNOWLEDGE_BASE',
        knowledgeBaseConfiguration: {
          knowledgeBaseId: knowledgeBaseId,
          modelArn: modelId, // Use model ID directly for on-demand models
          retrievalConfiguration: {
            vectorSearchConfiguration: {
              numberOfResults: 5,
              overrideSearchType: 'HYBRID' // Semantic + keyword search
            }
          }
        }
      }
      // No session management for Claude Sonnet 4 - let Bedrock handle sessions
      // Removed sessionId and sessionConfiguration for Claude Sonnet 4 compatibility
    };

    const command = new RetrieveAndGenerateCommand(input);
    return await this.executeWithRetry(() => this.bedrockAgentRuntime.send(command));
  }

  private async retrieveAndGenerateAdvanced(
    question: string,
    modelId: string,
    ragConfig: RAGConfiguration
  ): Promise<RetrieveAndGenerateCommandOutput> {
    const knowledgeBaseId = this.getKnowledgeBaseId();
    
    // Map our search type to AWS SDK search type
    const awsSearchType = this.mapSearchType(ragConfig.hybridSearch.searchType);
    
    // CRITICAL FIX: Use model ID directly for on-demand foundation models
    // For on-demand models like Claude 3.5 Sonnet v2, use model ID directly
    // Using full ARN causes AWS SDK to try resolving as inference profile
    console.log(`Using model ID for Advanced RAG (on-demand): ${modelId}`);
    
    const input: RetrieveAndGenerateCommandInput = {
      input: {
        text: question
      },
      retrieveAndGenerateConfiguration: {
        type: 'KNOWLEDGE_BASE',
        knowledgeBaseConfiguration: {
          knowledgeBaseId: knowledgeBaseId,
          modelArn: modelId, // Use model ID directly for on-demand models
          retrievalConfiguration: {
            vectorSearchConfiguration: {
              numberOfResults: ragConfig.retrieval.numberOfResults,
              overrideSearchType: awsSearchType,
              // Note: AWS Bedrock Knowledge Base doesn't currently support 
              // custom semantic/keyword weights in the API, but we track them
              // for future use and for our own relevance scoring
            }
          },
          generationConfiguration: {
            promptTemplate: {
              textPromptTemplate: this.buildAdvancedPromptTemplate(ragConfig)
            }
          }
        }
      }
      // No session management for Claude Sonnet 4 - let Bedrock handle sessions
      // Removed sessionId and sessionConfiguration for Claude Sonnet 4 compatibility
    };

    const command = new RetrieveAndGenerateCommand(input);
    return await this.executeWithRetry(() => this.bedrockAgentRuntime.send(command));
  }

  private extractSources(response: RetrieveAndGenerateCommandOutput): DocumentSource[] {
    if (!response.citations) {
      return [];
    }

    return response.citations.flatMap((citation, citationIndex) => {
      return citation.retrievedReferences?.map((reference, refIndex) => {
        // Extract file name from S3 URI properly
        const s3Uri = reference.location?.s3Location?.uri || '';
        const fileName = s3Uri.split('/').pop() || `Document ${citationIndex}-${refIndex}`;
        
        // Get confidence from retrieval metadata - Bedrock uses different field names
        let confidence = 0.0;
        if (reference.metadata) {
          // Try different possible confidence field names from Bedrock
          const scoreFields = ['score', 'confidence', 'relevanceScore', '_score'];
          for (const field of scoreFields) {
            if (reference.metadata[field] !== undefined) {
              const scoreValue = reference.metadata[field];
              confidence = typeof scoreValue === 'string' ? 
                parseFloat(scoreValue) : 
                typeof scoreValue === 'number' ? scoreValue : 0.0;
              break;
            }
          }
        }
        
        // Extract page number if available
        let pageNumber: number | undefined;
        if (reference.metadata?.page) {
          const pageValue = reference.metadata.page;
          pageNumber = typeof pageValue === 'string' ? 
            parseInt(pageValue) : 
            typeof pageValue === 'number' ? pageValue : undefined;
        }
        
        return {
          documentId: s3Uri || `doc-${citationIndex}-${refIndex}`,
          fileName: fileName.replace(/\.[^/.]+$/, '') || 'Unknown Document', // Remove file extension for display, ensure not empty
          excerpt: reference.content?.text || '',
          confidence: Math.min(Math.max(confidence, 0), 1), // Clamp between 0-1
          s3Location: s3Uri,
          pageNumber
        };
      }) || [];
    });
  }

  private extractTokenUsage(response: RetrieveAndGenerateCommandOutput): TokenUsage {
    // For now, estimate token usage based on text length
    // In a real implementation, this would come from the response metadata
    const outputText = response.output?.text || '';
    
    // Estimate input tokens based on typical question length
    const inputTokens = Math.ceil(200 / 4); // Rough estimate: 4 chars per token, assume 200 char question
    const outputTokens = Math.ceil(outputText.length / 4);
    
    return {
      inputTokens,
      outputTokens,
      totalTokens: inputTokens + outputTokens
    };
  }

  private calculateCost(tokenUsage: TokenUsage, modelConfig: any): number {
    if (!modelConfig) {
      return 0;
    }
    
    const inputCost = tokenUsage.inputTokens * modelConfig.costPerInputToken;
    const outputCost = tokenUsage.outputTokens * modelConfig.costPerOutputToken;
    
    return inputCost + outputCost;
  }

  private async trackMetrics(
    modelUsed: string,
    tokenUsage: TokenUsage,
    responseTime: number
  ): Promise<void> {
    try {
      const command = new PutMetricDataCommand({
        Namespace: 'AI-Assistant/Chat',
        MetricData: [
          {
            MetricName: 'ResponseTime',
            Value: responseTime,
            Unit: 'Milliseconds',
            Dimensions: [
              {
                Name: 'ModelUsed',
                Value: modelUsed
              }
            ]
          },
          {
            MetricName: 'TokenUsage',
            Value: tokenUsage.totalTokens,
            Unit: 'Count',
            Dimensions: [
              {
                Name: 'ModelUsed',
                Value: modelUsed
              }
            ]
          }
        ]
      });
      
      await this.cloudWatch.send(command);
    } catch (error) {
      console.error('Failed to track metrics:', error);
      // Don't throw - metrics failure shouldn't break the main flow
    }
  }

  private extractModelName(modelId: string): string {
    // Extract readable model name from model ID
    if (modelId.includes('claude-opus-4-1')) {
      return 'claude-opus-4-1';
    } else if (modelId.includes('claude-3-7-sonnet')) {
      return 'claude-3-7-sonnet';
    } else if (modelId.includes('claude-3-5-sonnet')) {
      return 'claude-3-5-sonnet-v2';
    }
    return modelId; // Return model ID if no match
  }

  private mapSearchType(searchType: string): 'HYBRID' | 'SEMANTIC' | undefined {
    // Map our internal search types to AWS SDK types
    switch (searchType) {
      case 'HYBRID':
        return 'HYBRID';
      case 'SEMANTIC':
        return 'SEMANTIC';
      case 'KEYWORD':
        // AWS SDK doesn't have a pure KEYWORD type, use HYBRID as fallback
        return 'HYBRID';
      default:
        return 'HYBRID';
    }
  }

  private buildAdvancedPromptTemplate(ragConfig: RAGConfiguration): string {
    return `
You are an AI assistant helping with software development questions. 
Please provide comprehensive, accurate answers based on the retrieved context.

Guidelines:
- Use the provided context to answer the question thoroughly
- Include specific examples and code snippets when relevant
- If the context doesn't contain sufficient information, clearly state this
- Cite your sources by referencing the document names
- Prioritize information from sources with higher confidence scores
- Ensure your response meets these quality standards:
  - Minimum length: ${ragConfig.qualityThresholds.minAnswerLength} characters
  - Include at least ${ragConfig.qualityThresholds.minSources} supporting sources
  - Maintain confidence threshold of ${ragConfig.qualityThresholds.minConfidence}

Question: $query$

Context: $search_results$

Please provide a detailed, well-structured answer:
    `.trim();
  }

  private async trackAdvancedMetrics(
    modelUsed: string,
    tokenUsage: TokenUsage,
    responseTime: number,
    qualityMetrics: ResponseQuality,
    ragConfig: RAGConfiguration
  ): Promise<void> {
    try {
      const command = new PutMetricDataCommand({
        Namespace: 'AI-Assistant/AdvancedRAG',
        MetricData: [
          {
            MetricName: 'ResponseTime',
            Value: responseTime,
            Unit: 'Milliseconds',
            Dimensions: [
              { Name: 'ModelUsed', Value: modelUsed },
              { Name: 'SearchType', Value: ragConfig.hybridSearch.searchType }
            ]
          },
          {
            MetricName: 'QualityScore',
            Value: qualityMetrics.qualityScore,
            Unit: 'None',
            Dimensions: [
              { Name: 'ModelUsed', Value: modelUsed }
            ]
          },
          {
            MetricName: 'CompletenessScore',
            Value: qualityMetrics.completenessScore,
            Unit: 'None',
            Dimensions: [
              { Name: 'ModelUsed', Value: modelUsed }
            ]
          },
          {
            MetricName: 'ReliabilityScore',
            Value: qualityMetrics.reliabilityScore,
            Unit: 'None',
            Dimensions: [
              { Name: 'ModelUsed', Value: modelUsed }
            ]
          },
          {
            MetricName: 'NumberOfResults',
            Value: ragConfig.retrieval.numberOfResults,
            Unit: 'Count',
            Dimensions: [
              { Name: 'ModelUsed', Value: modelUsed }
            ]
          },
          {
            MetricName: 'TokenUsage',
            Value: tokenUsage.totalTokens,
            Unit: 'Count',
            Dimensions: [
              { Name: 'ModelUsed', Value: modelUsed }
            ]
          }
        ]
      });
      
      await this.cloudWatch.send(command);
    } catch (error) {
      console.error('Failed to track advanced metrics:', error);
      // Don't throw - metrics failure shouldn't break the main flow
    }
  }

  private async trackKnowledgeBaseQueryMetrics(
    question: string,
    userId: string,
    responseTime: number,
    success: boolean,
    sourcesFound: number
  ): Promise<void> {
    try {
      const command = new PutMetricDataCommand({
        Namespace: 'AI-Assistant/KnowledgeBase',
        MetricData: [
          {
            MetricName: 'QueryResponseTime',
            Value: responseTime,
            Unit: 'Milliseconds',
            Timestamp: new Date(),
            Dimensions: [
              { Name: 'KnowledgeBaseId', Value: this.getKnowledgeBaseId() }
            ]
          },
          {
            MetricName: 'QueriesExecuted',
            Value: 1,
            Unit: 'Count',
            Timestamp: new Date(),
            Dimensions: [
              { Name: 'KnowledgeBaseId', Value: this.getKnowledgeBaseId() },
              { Name: 'Success', Value: success.toString() }
            ]
          },
          {
            MetricName: 'QuerySuccessRate',
            Value: success ? 100 : 0,
            Unit: 'Percent',
            Timestamp: new Date(),
            Dimensions: [
              { Name: 'KnowledgeBaseId', Value: this.getKnowledgeBaseId() }
            ]
          },
          {
            MetricName: 'SourcesFoundPerQuery',
            Value: sourcesFound,
            Unit: 'Count',
            Timestamp: new Date(),
            Dimensions: [
              { Name: 'KnowledgeBaseId', Value: this.getKnowledgeBaseId() }
            ]
          }
        ]
      });
      
      await this.cloudWatch.send(command);
      
      // Also log detailed query metrics to CloudWatch Logs
      const logGroupName = process.env.METRICS_LOG_GROUP;
      if (logGroupName) {
        console.log(JSON.stringify({
          eventType: 'KNOWLEDGE_BASE_QUERY',
          timestamp: new Date().toISOString(),
          userId,
          question: question.substring(0, 100) + (question.length > 100 ? '...' : ''), // Truncate for privacy
          responseTime,
          success,
          sourcesFound,
          knowledgeBaseId: this.getKnowledgeBaseId()
        }));
      }
      
    } catch (error) {
      console.error('Failed to track Knowledge Base query metrics:', error);
      // Don't throw - metrics failure shouldn't break the main flow
    }
  }

  private async executeWithRetry<T>(
    operation: () => Promise<T>,
    maxRetries: number = 3,
    baseDelayMs: number = 1000
  ): Promise<T> {
    // Implement rate limiting
    await this.enforceRateLimit();
    
    let lastError: any;
    
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const result = await operation();
        this.lastRequestTime = Date.now();
        return result;
      } catch (error: any) {
        lastError = error;
        
        // Check if error is retryable
        const isRetryable = this.isRetryableError(error);
        
        if (!isRetryable || attempt === maxRetries) {
          throw error;
        }
        
        // For throttling errors, use longer delays
        let delay = baseDelayMs * Math.pow(2, attempt);
        if (error.name === 'ThrottlingException') {
          delay = Math.max(delay, 5000); // Minimum 5 seconds for throttling
        }
        
        // Add jitter to prevent thundering herd
        delay += Math.random() * 1000;
        
        console.log(`Attempt ${attempt + 1} failed (${error.name}), retrying in ${delay}ms:`, error.message);
        
        await this.sleep(delay);
      }
    }
    
    throw lastError;
  }

  private async enforceRateLimit(): Promise<void> {
    const now = Date.now();
    const timeSinceLastRequest = now - this.lastRequestTime;
    
    if (timeSinceLastRequest < this.minRequestInterval) {
      const waitTime = this.minRequestInterval - timeSinceLastRequest;
      console.log(`Rate limiting: waiting ${waitTime}ms before next request`);
      await this.sleep(waitTime);
    }
  }

  private isRetryableError(error: any): boolean {
    // Check for retryable error types
    const retryableErrors = [
      'ThrottlingException',
      'ServiceUnavailableException',
      'InternalServerException',
      'ConflictException'
    ];
    
    return retryableErrors.includes(error.name) || 
           error.statusCode >= 500 ||
           error.code === 'ECONNRESET' ||
           error.code === 'ETIMEDOUT';
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  private handleBedrockError(error: BedrockError): BedrockError {
    const bedrockError: BedrockError = new Error(error.message);
    
    // Handle specific Bedrock Knowledge Base errors
    if (error.name === 'ResourceNotFoundException') {
      bedrockError.code = 'KNOWLEDGE_BASE_NOT_FOUND';
      bedrockError.statusCode = 404;
      bedrockError.retryable = false;
      bedrockError.message = 'Knowledge Base not found or not accessible';
    } else if (error.name === 'ValidationException') {
      bedrockError.code = 'VALIDATION_ERROR';
      bedrockError.statusCode = 400;
      bedrockError.retryable = false;
      bedrockError.message = error.message || 'Invalid request parameters';
    } else if (error.name === 'ThrottlingException') {
      bedrockError.code = 'RATE_LIMIT_EXCEEDED';
      bedrockError.statusCode = 429;
      bedrockError.retryable = true;
      bedrockError.message = 'Request rate limit exceeded. Please wait a moment and try again.';
    } else if (error.name === 'ServiceQuotaExceededException') {
      bedrockError.code = 'SERVICE_QUOTA_EXCEEDED';
      bedrockError.statusCode = 400;
      bedrockError.retryable = false;
      bedrockError.message = 'Service quota exceeded';
    } else if (error.name === 'AccessDeniedException') {
      bedrockError.code = 'AUTHORIZATION_FAILED';
      bedrockError.statusCode = 403;
      bedrockError.retryable = false;
      bedrockError.message = 'Access denied to Knowledge Base or model';
    } else if (error.name === 'ConflictException') {
      bedrockError.code = 'KNOWLEDGE_BASE_BUSY';
      bedrockError.statusCode = 409;
      bedrockError.retryable = true;
      bedrockError.message = 'Knowledge Base is currently processing, please retry';
    } else {
      bedrockError.code = error.code || 'UNKNOWN_ERROR';
      bedrockError.statusCode = error.statusCode || 500;
      bedrockError.retryable = error.retryable || false;
    }
    
    return bedrockError;
  }
}