/**
 * Standardized CORS utilities for all Lambda functions
 * Provides consistent CORS header handling across the application
 */

import { APIGatewayProxyResult } from 'aws-lambda';

export interface CORSConfig {
  allowedOrigins: string[];
  allowedMethods: string[];
  allowedHeaders: string[];
  maxAge?: number;
  allowCredentials?: boolean;
}

/**
 * Default CORS configuration for the AI Assistant application
 */
export const DEFAULT_CORS_CONFIG: CORSConfig = {
  allowedOrigins: [
    process.env.ALLOWED_ORIGINS || 'https://dq9tlzfsf1veq.cloudfront.net',
    'https://diaxl2ky359mj.cloudfront.net', // Legacy CloudFront domain
    'http://localhost:3000', // Development
    'http://localhost:5173'  // Vite development server
  ],
  allowedMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: [
    'Content-Type',
    'X-Amz-Date',
    'Authorization',
    'X-Api-Key',
    'X-Amz-Security-Token',
    'X-Requested-With'
  ],
  maxAge: 86400, // 24 hours
  allowCredentials: true
};

/**
 * Security headers that should be included in all responses
 */
export const SECURITY_HEADERS = {
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'X-XSS-Protection': '1; mode=block',
  'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
};

/**
 * Validate if the request origin is allowed
 */
export function isOriginAllowed(origin: string | undefined, config: CORSConfig = DEFAULT_CORS_CONFIG): boolean {
  if (!origin) {
    return false;
  }

  // Check if origin is in allowed list
  return config.allowedOrigins.some(allowedOrigin => {
    // Handle wildcard origins
    if (allowedOrigin === '*') {
      return true;
    }
    
    // Handle exact matches
    if (allowedOrigin === origin) {
      return true;
    }
    
    // Handle subdomain patterns (e.g., *.example.com)
    if (allowedOrigin.startsWith('*.')) {
      const domain = allowedOrigin.substring(2);
      return origin.endsWith(domain);
    }
    
    return false;
  });
}

/**
 * Get the appropriate Access-Control-Allow-Origin header value
 */
export function getAllowOriginHeader(origin: string | undefined, config: CORSConfig = DEFAULT_CORS_CONFIG): string {
  // If no origin provided, use the first allowed origin
  if (!origin) {
    return config.allowedOrigins[0] || '*';
  }

  // If origin is allowed, return it
  if (isOriginAllowed(origin, config)) {
    return origin;
  }

  // If origin is not allowed, return the first allowed origin
  return config.allowedOrigins[0] || '*';
}

/**
 * Generate CORS headers for a response
 */
export function generateCORSHeaders(
  requestOrigin?: string,
  config: CORSConfig = DEFAULT_CORS_CONFIG
): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': getAllowOriginHeader(requestOrigin, config),
    'Access-Control-Allow-Methods': config.allowedMethods.join(', '),
    'Access-Control-Allow-Headers': config.allowedHeaders.join(', '),
    'Access-Control-Max-Age': (config.maxAge || 86400).toString(),
    ...SECURITY_HEADERS
  };

  if (config.allowCredentials) {
    headers['Access-Control-Allow-Credentials'] = 'true';
  }

  return headers;
}

/**
 * Handle OPTIONS preflight requests
 */
export function handleOPTIONSRequest(
  requestOrigin?: string,
  config: CORSConfig = DEFAULT_CORS_CONFIG
): APIGatewayProxyResult {
  return {
    statusCode: 200,
    headers: generateCORSHeaders(requestOrigin, config),
    body: JSON.stringify({ message: 'CORS preflight successful' })
  };
}

/**
 * Add CORS headers to an existing response
 */
export function addCORSHeaders(
  response: any,
  requestOrigin?: string,
  config: CORSConfig = DEFAULT_CORS_CONFIG
): any {
  const corsHeaders = generateCORSHeaders(requestOrigin, config);
  
  return {
    ...response,
    headers: {
      ...response.headers,
      ...corsHeaders
    }
  };
}

/**
 * Create a standardized success response with CORS headers
 */
export function createSuccessResponse(
  data: any,
  statusCode: number = 200,
  requestOrigin?: string,
  config: CORSConfig = DEFAULT_CORS_CONFIG
): APIGatewayProxyResult {
  return {
    statusCode,
    headers: generateCORSHeaders(requestOrigin, config),
    body: JSON.stringify({
      success: true,
      data,
      timestamp: new Date().toISOString()
    })
  };
}

/**
 * Create a standardized error response with CORS headers
 */
export function createErrorResponse(
  statusCode: number,
  message: string,
  requestId?: string,
  code?: string,
  requestOrigin?: string,
  config: CORSConfig = DEFAULT_CORS_CONFIG
): APIGatewayProxyResult {
  // Log error without sensitive information
  console.error(`Error ${statusCode}:`, { message, code, requestId });
  
  return {
    statusCode,
    headers: generateCORSHeaders(requestOrigin, config),
    body: JSON.stringify({
      success: false,
      error: {
        code: code || 'INTERNAL_ERROR',
        message,
        requestId,
        timestamp: new Date().toISOString()
      }
    })
  };
}

/**
 * Extract the origin from an API Gateway event
 */
export function extractOriginFromEvent(event: any): string | undefined {
  return event.headers?.Origin || 
         event.headers?.origin || 
         event.headers?.['Origin'] ||
         event.headers?.['origin'];
}

/**
 * Validate CORS configuration
 */
export function validateCORSConfig(config: CORSConfig): boolean {
  if (!config.allowedOrigins || config.allowedOrigins.length === 0) {
    console.error('CORS configuration error: allowedOrigins cannot be empty');
    return false;
  }

  if (!config.allowedMethods || config.allowedMethods.length === 0) {
    console.error('CORS configuration error: allowedMethods cannot be empty');
    return false;
  }

  if (!config.allowedHeaders || config.allowedHeaders.length === 0) {
    console.error('CORS configuration error: allowedHeaders cannot be empty');
    return false;
  }

  return true;
}

/**
 * Create CORS configuration from environment variables
 */
export function createCORSConfigFromEnv(): CORSConfig {
  const allowedOrigins = process.env.ALLOWED_ORIGINS 
    ? process.env.ALLOWED_ORIGINS.split(',').map(origin => origin.trim())
    : DEFAULT_CORS_CONFIG.allowedOrigins;

  const allowedMethods = process.env.ALLOWED_METHODS
    ? process.env.ALLOWED_METHODS.split(',').map(method => method.trim())
    : DEFAULT_CORS_CONFIG.allowedMethods;

  const allowedHeaders = process.env.ALLOWED_HEADERS
    ? process.env.ALLOWED_HEADERS.split(',').map(header => header.trim())
    : DEFAULT_CORS_CONFIG.allowedHeaders;

  const maxAge = process.env.CORS_MAX_AGE
    ? parseInt(process.env.CORS_MAX_AGE)
    : DEFAULT_CORS_CONFIG.maxAge;

  const allowCredentials = process.env.CORS_ALLOW_CREDENTIALS
    ? process.env.CORS_ALLOW_CREDENTIALS.toLowerCase() === 'true'
    : DEFAULT_CORS_CONFIG.allowCredentials;

  return {
    allowedOrigins,
    allowedMethods,
    allowedHeaders,
    maxAge,
    allowCredentials
  };
}