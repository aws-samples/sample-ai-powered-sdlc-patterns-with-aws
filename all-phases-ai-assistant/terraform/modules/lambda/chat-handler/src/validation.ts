import { z } from 'zod';
import { QueryComplexity } from './types';

// Comprehensive input validation schemas using Zod
export const ChatRequestSchema = z.object({
  question: z.string()
    .min(1, 'Question cannot be empty')
    .max(4000, 'Question must be less than 4000 characters')
    .trim()
    .refine(msg => msg.length > 0, 'Question cannot be only whitespace')
    .refine(msg => !msg.includes('<script>'), 'Question contains potentially malicious content')
    .refine(msg => !msg.includes('javascript:'), 'Question contains potentially malicious content'),
  
  userId: z.string()
    .min(1, 'User ID is required')
    .max(128, 'User ID too long')
    .regex(/^[a-zA-Z0-9@._-]+$/, 'Invalid user ID format'),
  
  conversationId: z.string()
    .max(100, 'Conversation ID must be less than 100 characters')
    .regex(/^[a-zA-Z0-9_-]+$/, 'Conversation ID can only contain alphanumeric characters, hyphens, and underscores')
    .optional(),
  
  queryComplexity: z.nativeEnum(QueryComplexity)
    .optional(),
  
  includeSourceDetails: z.boolean()
    .default(true),
  
  useAdvancedRAG: z.boolean()
    .default(false)
});

// API Gateway event validation
export const APIGatewayEventSchema = z.object({
  body: z.string().nullable(),
  headers: z.record(z.string(), z.string()).optional(),
  httpMethod: z.enum(['POST', 'OPTIONS']),
  path: z.string(),
  queryStringParameters: z.record(z.string(), z.string()).nullable(),
  requestContext: z.object({
    requestId: z.string(),
    authorizer: z.object({
      claims: z.record(z.string(), z.string()).optional()
    }).optional()
  })
});

export type ChatRequest = z.infer<typeof ChatRequestSchema>;

// Enhanced validation function with detailed error handling
export function validateChatRequest(body: any): ChatRequest {
  try {
    // First validate that body exists and is an object
    if (!body || typeof body !== 'object') {
      throw new Error('Request body must be a valid JSON object');
    }

    // Parse and validate with Zod
    const result = ChatRequestSchema.parse(body);
    
    // Additional security validations
    const suspiciousPatterns = [
      /<script[^>]*>.*?<\/script>/gi,
      /javascript:/gi,
      /data:text\/html/gi,
      /vbscript:/gi,
      /onload=/gi,
      /onerror=/gi
    ];
    
    for (const pattern of suspiciousPatterns) {
      if (pattern.test(result.question)) {
        throw new Error('Question contains potentially malicious content');
      }
    }
    
    return result;
  } catch (error) {
    if (error instanceof z.ZodError) {
      const errorMessages = error.issues.map((err: any) => `${err.path.join('.')}: ${err.message}`).join(', ');
      throw new Error(`Validation failed: ${errorMessages}`);
    }
    throw error;
  }
}

// Utility function for sanitizing user input
export function sanitizeInput(input: string): string {
  return input
    .replace(/[<>\"'&]/g, '') // Remove potentially dangerous characters
    .trim()
    .substring(0, 4000); // Ensure length limit
}

// Create validation error response
export function createValidationErrorResponse(errors: string[]): any {
  return {
    statusCode: 400,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': process.env.ALLOWED_ORIGINS || 'https://diaxl2ky359mj.cloudfront.net',
      'X-Content-Type-Options': 'nosniff',
      'X-Frame-Options': 'DENY',
      'X-XSS-Protection': '1; mode=block'
    },
    body: JSON.stringify({
      error: {
        code: 'VALIDATION_ERROR',
        message: 'Request validation failed',
        details: errors,
        timestamp: new Date().toISOString()
      }
    })
  };
}