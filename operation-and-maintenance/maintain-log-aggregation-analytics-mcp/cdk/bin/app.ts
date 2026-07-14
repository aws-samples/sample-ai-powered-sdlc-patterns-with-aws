#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { SampleAppStack } from '../lib/sample-app-stack';

const app = new cdk.App();
new SampleAppStack(app, 'LogAnalysisSampleApp', {
  description: 'Sample application for log analysis MCP server demonstration'
});
