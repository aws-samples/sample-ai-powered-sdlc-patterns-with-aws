// Security utilities for frontend application

/**
 * Sanitize user input to prevent XSS attacks
 */
export function sanitizeInput(input: string): string {
  return input
    .replace(/[<>\"'&]/g, '') // Remove potentially dangerous characters
    .replace(/javascript:/gi, '') // Remove javascript: protocol
    .replace(/data:text\/html/gi, '') // Remove data URLs
    .replace(/vbscript:/gi, '') // Remove vbscript: protocol
    .trim()
    .substring(0, 4000); // Ensure length limit
}

/**
 * Validate message content for security
 */
export function validateMessage(message: string): { isValid: boolean; error?: string } {
  if (!message || typeof message !== 'string') {
    return { isValid: false, error: 'Message must be a non-empty string' };
  }

  if (message.length > 4000) {
    return { isValid: false, error: 'Message too long (maximum 4000 characters)' };
  }

  if (message.trim().length === 0) {
    return { isValid: false, error: 'Message cannot be empty or only whitespace' };
  }

  // Check for potentially malicious content
  const suspiciousPatterns = [
    /<script[^>]*>.*?<\/script>/gi,
    /javascript:/gi,
    /data:text\/html/gi,
    /vbscript:/gi,
    /onload=/gi,
    /onerror=/gi,
    /<iframe/gi,
    /<object/gi,
    /<embed/gi
  ];

  for (const pattern of suspiciousPatterns) {
    if (pattern.test(message)) {
      return { isValid: false, error: 'Message contains potentially unsafe content' };
    }
  }

  return { isValid: true };
}

/**
 * Securely get authentication token with validation
 */
export function getSecureAuthToken(authState: any): string | null {
  // First try to get token from auth state
  if (authState?.idToken) {
    return authState.idToken;
  }

  // Secure fallback to localStorage with validation
  try {
    const tokenKey = Object.keys(localStorage).find(key => 
      key.includes('CognitoIdentityServiceProvider') && 
      key.includes('idToken') &&
      !key.includes('script') && // Basic XSS protection
      key.length < 200 && // Reasonable key length limit
      /^[a-zA-Z0-9._-]+$/.test(key) // Only allow safe characters
    );
    
    if (tokenKey) {
      const storedToken = localStorage.getItem(tokenKey);
      // Basic JWT format validation (3 parts separated by dots)
      if (storedToken && 
          typeof storedToken === 'string' && 
          storedToken.split('.').length === 3 &&
          storedToken.length > 100 && // Reasonable minimum length
          storedToken.length < 4000) { // Reasonable maximum length
        return storedToken;
      }
    }
  } catch (error) {
    console.error('Error accessing localStorage:', error);
  }

  return null;
}

/**
 * Content Security Policy configuration
 */
export const CSP_CONFIG = {
  'default-src': "'self'",
  'script-src': "'self' 'unsafe-inline'", // Note: In production, use nonces instead of unsafe-inline
  'style-src': "'self' 'unsafe-inline'",
  'img-src': "'self' data: https:",
  'connect-src': "'self' https://*.amazonaws.com https://*.cloudfront.net",
  'font-src': "'self'",
  'object-src': "'none'",
  'media-src': "'self'",
  'frame-src': "'none'"
};

/**
 * Rate limiting for client-side requests
 */
class RateLimiter {
  private requests: Map<string, number[]> = new Map();
  private readonly windowMs: number;
  private readonly maxRequests: number;

  constructor(windowMs: number = 60000, maxRequests: number = 10) {
    this.windowMs = windowMs;
    this.maxRequests = maxRequests;
  }

  isAllowed(key: string): boolean {
    const now = Date.now();
    const requests = this.requests.get(key) || [];
    
    // Remove old requests outside the window
    const validRequests = requests.filter(time => now - time < this.windowMs);
    
    if (validRequests.length >= this.maxRequests) {
      return false;
    }

    // Add current request
    validRequests.push(now);
    this.requests.set(key, validRequests);
    
    return true;
  }
}

export const chatRateLimiter = new RateLimiter(60000, 10); // 10 requests per minute
export const uploadRateLimiter = new RateLimiter(300000, 3); // 3 uploads per 5 minutes

/**
 * Secure error handling - don't expose sensitive information
 */
export function createSecureErrorMessage(error: any): string {
  // Map internal errors to user-friendly messages
  const errorMap: { [key: string]: string } = {
    'KNOWLEDGE_BASE_NOT_FOUND': 'The knowledge base is temporarily unavailable. Please try again later.',
    'RATE_LIMIT_EXCEEDED': 'Too many requests. Please wait a moment and try again.',
    'AUTHORIZATION_FAILED': 'Your session has expired. Please log in again.',
    'VALIDATION_ERROR': 'Please check your input and try again.',
    'NETWORK_ERROR': 'Network connection issue. Please check your internet connection.',
    'TIMEOUT': 'Request timed out. Please try again.',
    'INTERNAL_ERROR': 'An unexpected error occurred. Please try again later.'
  };

  if (error?.code && errorMap[error.code]) {
    return errorMap[error.code] || 'An unexpected error occurred. Please try again later.';
  }

  if (error?.message && typeof error.message === 'string') {
    // Check if it's a known safe message
    const safeMessages = [
      'Authentication required',
      'Invalid input',
      'Request failed',
      'Service unavailable'
    ];
    
    for (const safeMessage of safeMessages) {
      if (error.message.includes(safeMessage)) {
        return error.message;
      }
    }
  }

  // Default generic error message
  return 'An unexpected error occurred. Please try again later.';
}