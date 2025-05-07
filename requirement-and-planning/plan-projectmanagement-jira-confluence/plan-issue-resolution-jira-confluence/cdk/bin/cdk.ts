#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { AmazonQBusinessStack } from '../../../../../cdk-common/lib/amazon-q-stack';
import { AmazonQConfluenceSourceStack } from '../../../../../cdk-common/lib/amazon-q-confluence-stack';
import { AmazonQJiraPluginStack } from '../../../../../cdk-common/lib/amazon-q-jira-plugin-stack';

const app = new cdk.App();

const amazonQBusiness = new AmazonQBusinessStack(app,  'AmazonQBusinessStack', {});

//Require AmazonQBusinessStack
const AmazonQConfluenceSource = new AmazonQConfluenceSourceStack(app,  'AmazonQConfluenceSourceStack', {
  app: amazonQBusiness.app,
  index: amazonQBusiness.index
});

//Require AmazonQBusinessStack
const AmazonQJiraPlugin = new AmazonQJiraPluginStack(app,  'AmazonQJiraPluginStack', {
  app: amazonQBusiness.app,
  appWebEndpoint: amazonQBusiness.webEndpoint
});