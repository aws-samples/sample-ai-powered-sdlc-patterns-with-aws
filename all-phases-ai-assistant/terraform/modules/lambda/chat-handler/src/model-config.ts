import { ModelConfig, QueryComplexity } from './types';

// TASK 1: Updated model hierarchy - Claude 3.5 Haiku as primary, Claude 3.5 Sonnet v2 as fallback
// Use foundation model IDs for on-demand access
export const CLAUDE_FOUNDATION_MODEL_HIERARCHY = [
  'anthropic.claude-3-5-haiku-20241022-v1:0',     // Claude 3.5 Haiku (Primary - reliable, cost-effective)
  'anthropic.claude-3-5-sonnet-20241022-v2:0',   // Claude 3.5 Sonnet v2 (Secondary - high quality)
  'anthropic.claude-3-7-sonnet-20250219-v1:0',   // Claude 3.7 Sonnet (Tertiary fallback)
  'anthropic.claude-3-5-sonnet-20240620-v1:0'    // Claude 3.5 Sonnet v1 (Final fallback)
];

// Foundation model ARNs for direct API calls (when full ARN is needed)
// Updated to match new hierarchy: Claude 3.5 Haiku primary, Claude 3.5 Sonnet v2 secondary
export const CLAUDE_FOUNDATION_MODEL_ARNS = [
  'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0',
  'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0',
  'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-7-sonnet-20250219-v1:0',
  'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0'
];

// TASK 1: Updated MODEL_CONFIGS with Claude 3.5 Haiku as primary model
// Use foundation model IDs for on-demand access
export const MODEL_CONFIGS: ModelConfig[] = [
  {
    modelArn: 'anthropic.claude-3-5-haiku-20241022-v1:0', // Primary: Claude 3.5 Haiku
    name: 'claude-3-5-haiku',
    costPerInputToken: 0.00000025,  // $0.25/MTok - most cost-effective
    costPerOutputToken: 0.00000125, // $1.25/MTok
    latencyTier: 'fast',
    capabilities: ['cost-effective', 'fast-response', 'on-demand', 'knowledge-base-compatible'],
    maxContextLength: 200000
  },
  {
    modelArn: 'anthropic.claude-3-5-sonnet-20241022-v2:0', // Secondary: Claude 3.5 Sonnet v2
    name: 'claude-3-5-sonnet-v2',
    costPerInputToken: 0.000003,  // $3/MTok
    costPerOutputToken: 0.000015, // $15/MTok
    latencyTier: 'fast',
    capabilities: ['high-availability', 'multiple-context-lengths', 'on-demand', 'high-quality'],
    maxContextLength: 200000
  },
  {
    modelArn: 'anthropic.claude-3-7-sonnet-20250219-v1:0', // Tertiary: Claude 3.7 Sonnet
    name: 'claude-3-7-sonnet',
    costPerInputToken: 0.000003,  // $3/MTok
    costPerOutputToken: 0.000015, // $15/MTok
    latencyTier: 'fast',
    capabilities: ['extended-thinking', 'balanced-performance', 'on-demand'],
    maxContextLength: 200000
  },
  {
    modelArn: 'anthropic.claude-3-5-sonnet-20240620-v1:0', // Final fallback: Claude 3.5 Sonnet v1
    name: 'claude-3-5-sonnet-v1',
    costPerInputToken: 0.000003,  // $3/MTok
    costPerOutputToken: 0.000015, // $15/MTok
    latencyTier: 'fast',
    capabilities: ['high-availability', 'on-demand'],
    maxContextLength: 200000
  }
];

export function classifyQueryComplexity(question: string, documentCount: number = 0): QueryComplexity {
  // Simple: Short questions, single document references
  if (question.length < 100 && documentCount <= 2) {
    return QueryComplexity.SIMPLE;
  }
  
  // Complex: Long questions, multiple documents, analysis keywords
  const complexKeywords = ['analyze', 'compare', 'evaluate', 'design', 'architecture', 'comprehensive'];
  if (question.length > 300 || documentCount > 5 || 
      complexKeywords.some(keyword => question.toLowerCase().includes(keyword))) {
    return QueryComplexity.COMPLEX;
  }
  
  return QueryComplexity.MODERATE;
}

export function selectOptimalModel(
  queryComplexity: QueryComplexity,
  requiresMultimodal: boolean = false
): ModelConfig {
  
  // TASK 1: Updated model selection to use Claude 3.5 Haiku as primary
  // Primary model: Claude 3.5 Haiku (reliable, cost-effective, proven compatibility)
  // Fallback model: Claude 3.5 Sonnet v2 (high quality, may have compatibility issues)
  
  // For complex queries, still prefer Claude 3.5 Haiku for reliability
  // The BedrockService will handle fallback to Claude 3.5 Sonnet v2 if needed
  if (queryComplexity === QueryComplexity.COMPLEX) {
    return {
      modelArn: 'anthropic.claude-3-5-haiku-20241022-v1:0', // Primary: Claude 3.5 Haiku
      name: 'claude-3-5-haiku',
      costPerInputToken: 0.00000025,  // More cost-effective
      costPerOutputToken: 0.00000125,
      latencyTier: 'fast',
      capabilities: ['cost-effective', 'fast-response', 'on-demand', 'knowledge-base-compatible'],
      maxContextLength: 200000
    };
  }
  
  // For all other cases (simple, moderate), use Claude 3.5 Haiku as primary
  return {
    modelArn: 'anthropic.claude-3-5-haiku-20241022-v1:0', // Primary: Claude 3.5 Haiku
    name: 'claude-3-5-haiku',
    costPerInputToken: 0.00000025,  // More cost-effective
    costPerOutputToken: 0.00000125,
    latencyTier: 'fast',
    capabilities: ['cost-effective', 'fast-response', 'on-demand', 'knowledge-base-compatible'],
    maxContextLength: 200000
  };
}

export function getModelConfigByName(modelName: string): ModelConfig | undefined {
  return MODEL_CONFIGS.find(config => 
    config.name === modelName || config.modelArn.includes(modelName)
  );
}