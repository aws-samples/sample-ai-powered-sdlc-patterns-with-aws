#!/usr/bin/env node
import 'source-map-support/register';
import * as dotenv from 'dotenv';
import * as path from 'path';

// Load environment variables from .env file FIRST, before importing config
dotenv.config({ path: path.join(__dirname, '../.env') });

// Debug: Log environment variables
console.log('Environment variables loaded:');
console.log('CDK_DEFAULT_ACCOUNT:', process.env.CDK_DEFAULT_ACCOUNT);
console.log('CDK_DEFAULT_REGION:', process.env.CDK_DEFAULT_REGION);
console.log('ALLOWED_IP_ADDRESS:', process.env.ALLOWED_IP_ADDRESS);
console.log('CLAUDE_MODEL_ID:', process.env.CLAUDE_MODEL_ID);

// Now import the config and CDK modules AFTER environment variables are loaded
import * as cdk from 'aws-cdk-lib';
import { AwsSolutionsChecks } from 'cdk-nag';
import { ICodeStack } from '../lib/icode-stack';
import { config } from '../lib/config';

const app = new cdk.App();

// Add CDK Nag checks
cdk.Aspects.of(app).add(new AwsSolutionsChecks({ verbose: true }));

const stack = new ICodeStack(app, 'ICodeStack', {
  env: {
    account: config.env.account,
    region: config.env.region,
  },
  description: 'iCode application stack with ECS Fargate, ALB, Cognito, and S3',
});

app.synth();