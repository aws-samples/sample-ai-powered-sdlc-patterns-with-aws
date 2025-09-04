// AWS configuration for React frontend
// This file will be populated with values from Terraform outputs during deployment

import { FrontendConfig } from '@/types/api';

// Production configuration from Terraform outputs
const defaultConfig: FrontendConfig = {
  aws_region: 'us-west-2',
  cognito_user_pool_id: 'us-west-2_FLJTm8Xt8',
  cognito_user_pool_client_id: '3gr32ei5n768d88h02klhmpn8v',
  cognito_user_pool_domain: 'ai-assistant-auth-3gja49wa',
  api_gateway_url: 'https://jpt8wzkowd.execute-api.us-west-2.amazonaws.com/dev',
  cloudfront_url: 'https://dq9tlzfsf1veq.cloudfront.net',
  environment: 'dev',
  project_name: 'ai-assistant'
};

// Configuration validation
const validateConfig = (config: FrontendConfig): void => {
  const requiredFields: (keyof FrontendConfig)[] = [
    'aws_region',
    'cognito_user_pool_id',
    'cognito_user_pool_client_id',
    'api_gateway_url'
  ];

  const missingFields = requiredFields.filter(field => !config[field]);
  
  if (missingFields.length > 0) {
    console.error('Missing required configuration fields:', missingFields);
    throw new Error(`Missing required configuration: ${missingFields.join(', ')}`);
  }

  // Validate AWS region format
  if (!/^[a-z]{2}-[a-z]+-\d+$/.test(config.aws_region)) {
    throw new Error(`Invalid AWS region format: ${config.aws_region}`);
  }

  // Validate Cognito User Pool ID format
  if (!/^[a-z0-9-]+_[a-zA-Z0-9]+$/.test(config.cognito_user_pool_id)) {
    throw new Error(`Invalid Cognito User Pool ID format: ${config.cognito_user_pool_id}`);
  }

  // Validate API Gateway URL format
  if (!config.api_gateway_url.startsWith('https://')) {
    throw new Error(`API Gateway URL must use HTTPS: ${config.api_gateway_url}`);
  }
};

// Get configuration with validation
export const getAWSConfig = (): FrontendConfig => {
  try {
    validateConfig(defaultConfig);
    return defaultConfig;
  } catch (error) {
    console.error('Configuration validation failed:', error);
    
    // In development, show helpful error message
    if (process.env.NODE_ENV === 'development') {
      console.warn('Using fallback configuration for development');
      return {
        ...defaultConfig,
        // Provide development fallbacks
        cognito_user_pool_id: defaultConfig.cognito_user_pool_id || 'us-west-2_XXXXXXXXX',
        cognito_user_pool_client_id: defaultConfig.cognito_user_pool_client_id || 'xxxxxxxxxxxxxxxxxxxxxxxxxx',
        api_gateway_url: defaultConfig.api_gateway_url || 'https://api.example.com/dev'
      };
    }
    
    throw error;
  }
};

// AWS Amplify configuration
export const getAmplifyConfig = () => {
  const config = getAWSConfig();
  
  return {
    Auth: {
      Cognito: {
        region: config.aws_region,
        userPoolId: config.cognito_user_pool_id,
        userPoolClientId: config.cognito_user_pool_client_id,
        loginWith: {
          oauth: {
            domain: config.cognito_user_pool_domain,
            scopes: ['email', 'openid', 'profile'],
            redirectSignIn: [`${config.cloudfront_url || window.location.origin}/callback`],
            redirectSignOut: [`${config.cloudfront_url || window.location.origin}/logout`],
            responseType: 'code' as const
          }
        }
      }
    },
    API: {
      REST: {
        'ai-assistant-api': {
          endpoint: config.api_gateway_url,
          region: config.aws_region
        }
      }
    }
  };
};

// API configuration
export const getAPIConfig = () => {
  const config = getAWSConfig();
  
  return {
    baseURL: config.api_gateway_url,
    timeout: 30000, // 30 seconds
    headers: {
      'Content-Type': 'application/json',
      'X-API-Version': '1.0'
    },
    retries: 3,
    retryDelay: 1000
  };
};

// Feature flags based on environment
export const getFeatureFlags = () => {
  const config = getAWSConfig();
  
  return {
    enableAdvancedRAG: config.environment !== 'dev',
    enableRealTimeUpdates: true,
    enableFileUpload: true,
    enableAdminFeatures: true,
    enableAnalytics: config.environment === 'prod',
    enableDebugMode: config.environment === 'dev',
    maxFileSize: 10 * 1024 * 1024, // 10MB
    maxFilesPerUpload: 5,
    supportedFileTypes: ['.pdf', '.docx', '.txt', '.md'],
    chatHistoryLimit: 50,
    documentListPageSize: 20
  };
};

// Environment-specific settings
export const getEnvironmentSettings = () => {
  const config = getAWSConfig();
  
  const settings = {
    dev: {
      logLevel: 'debug',
      enableMockData: true,
      apiTimeout: 60000,
      enableHotReload: true
    },
    staging: {
      logLevel: 'info',
      enableMockData: false,
      apiTimeout: 30000,
      enableHotReload: false
    },
    prod: {
      logLevel: 'error',
      enableMockData: false,
      apiTimeout: 30000,
      enableHotReload: false
    }
  };
  
  return settings[config.environment as keyof typeof settings] || settings.dev;
};

// Export the main configuration
export const AWS_CONFIG = getAWSConfig();
export const AMPLIFY_CONFIG = getAmplifyConfig();
export const API_CONFIG = getAPIConfig();
export const FEATURE_FLAGS = getFeatureFlags();
export const ENVIRONMENT_SETTINGS = getEnvironmentSettings();

// Default export for compatibility
export default {
  AWS_CONFIG,
  AMPLIFY_CONFIG,
  API_CONFIG,
  FEATURE_FLAGS,
  ENVIRONMENT_SETTINGS
};

// Configuration constants
export const CONFIG_CONSTANTS = {
  APP_NAME: 'AI Assistant',
  APP_VERSION: '1.0.0',
  SUPPORTED_LANGUAGES: ['en'],
  DEFAULT_LANGUAGE: 'en',
  SESSION_TIMEOUT: 8 * 60 * 60 * 1000, // 8 hours
  REFRESH_TOKEN_THRESHOLD: 5 * 60 * 1000, // 5 minutes
  MAX_RETRY_ATTEMPTS: 3,
  DEBOUNCE_DELAY: 300,
  ANIMATION_DURATION: 200,
  TOAST_DURATION: 5000
} as const;