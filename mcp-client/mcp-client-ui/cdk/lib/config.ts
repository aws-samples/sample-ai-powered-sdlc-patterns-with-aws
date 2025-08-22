export interface ICodeConfig {
  // General configuration
  appName: string;
  env: {
    account: string;
    region: string;
  };

  // Network configuration
  allowedIpAddress: string;

  // SSL/HTTPS configuration - HTTPS is mandatory for security compliance
  certificateArn: string; // Required for HTTPS
  domainName?: string;

  // ECS configuration
  containerPort: number;
  cpu: number;
  memory: number;
  desiredCount: number;

  // ECR configuration
  repositoryName: string;
  imageTag: string;

  // Cognito configuration
  userPoolName: string;
  clientName: string;
  identityPoolName: string;



  // MCP Server configuration
  mcpServerUrls: string[];

  // Bedrock access
  bedrockModelArns: string[];
  knowledgeBaseId?: string;
}

export const config: ICodeConfig = {
  appName: 'icode',
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT || '',
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
  },

  // Network configuration - users must set their own IP
  allowedIpAddress: process.env.ALLOWED_IP_ADDRESS || '', // No default - users must specify

  // SSL/HTTPS configuration - HTTPS is mandatory for security compliance
  certificateArn: (() => {
    const certArn = process.env.CERTIFICATE_ARN;
    if (!certArn) {
      throw new Error(`
🔒 CERTIFICATE_ARN is required for security compliance.

To deploy with HTTPS (required for production):
1. Create/import an SSL certificate in AWS Certificate Manager
2. Add CERTIFICATE_ARN to your .env file

For certificate creation help, see: https://docs.aws.amazon.com/acm/latest/userguide/gs-acm-request-public.html

For development with self-signed certificate:
openssl req -x509 -newkey rsa:2048 -keyout private.key -out certificate.crt -days 365 -nodes
aws acm import-certificate --certificate fileb://certificate.crt --private-key fileb://private.key
      `);
    }
    return certArn;
  })(),
  domainName: process.env.DOMAIN_NAME || undefined,

  containerPort: 8000,
  cpu: 1024,       
  memory: 2048,
  desiredCount: 1,

  repositoryName: process.env.ECR_REPOSITORY_NAME || 'icode-fullstack',
  imageTag: process.env.IMAGE_TAG || 'latest',

  userPoolName: 'icode-user-pool',
  clientName: 'icode-client',
  identityPoolName: 'icode-identity-pool',



  // MCP Server URLs - Parse comma-separated list
  mcpServerUrls: process.env.MCP_SERVER_URLS ? 
    process.env.MCP_SERVER_URLS.split(',').map(url => url.trim()).filter(url => url.length > 0) : 
    [],

  // Bedrock model ARNs - Fully configurable via environment variables
  bedrockModelArns: (() => {
    if (!process.env.CLAUDE_MODEL_ID) {
      throw new Error('CLAUDE_MODEL_ID environment variable is required');
    }
    
    const region = process.env.CDK_DEFAULT_REGION || 'us-east-1';
    const account = process.env.CDK_DEFAULT_ACCOUNT;
    const modelId = process.env.CLAUDE_MODEL_ID;
    
    console.log(`🔍 Configuring Bedrock ARN for model: ${modelId}`);
    console.log(`🔍 Account: ${account}, Region: ${region}`);
    
    // Check if it's an inference profile (starts with region prefix like 'us.')
    if (modelId.startsWith('us.') || modelId.startsWith('eu.') || modelId.startsWith('ap.')) {
      // It's an inference profile
      const arn = `arn:aws:bedrock:${region}:${account}:inference-profile/${modelId}`;
      console.log(`✅ Using inference profile ARN: ${arn}`);
      return [arn];
    } else {
      // It's a foundation model
      const arn = `arn:aws:bedrock:${region}::foundation-model/${modelId}`;
      console.log(`✅ Using foundation model ARN: ${arn}`);
      return [arn];
    }
  })(),

  // Knowledge Base ID (optional - users set this after creating their KB)
  knowledgeBaseId: process.env.BEDROCK_KNOWLEDGE_BASE_ID || ''
};