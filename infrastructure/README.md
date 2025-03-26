# Infrastructure 

This module contains the CDK code to deploy your infrastructure. Please refer to the specific samples on how to perform the deploy.

## How to Deploy the infrastructure

npm install

cdk bootstrap

cdk deploy AmazonQBusinessStack --parameters AmazonQBusinessStack:appName=<APP_NAME> \
    --parameters AmazonQBusinessStack:iamIdentityCenterArn=<IDC_ARN>

cdk deploy AmazonQConfluenceSourceStack --parameters AmazonQConfluenceSourceStack:confluenceUrl=<CONFLUENCE_URL> \
    --parameters AmazonQConfluenceSourceStack:confluenceUsername=<EMAIL> \
    --parameters AmazonQConfluenceSourceStack:confluencePassword=<TOKEN>

cdk deploy AmazonQJiraPluginStack --parameters AmazonQJiraPluginStack:jiraClientId=<JIRA_CLIENT_ID> \
    --parameters AmazonQJiraPluginStack:jiraClientSecret=<JIRA_CLIENT_SECRET> \
    --parameters AmazonQJiraPluginStack:jiraRedirectUrl=<JIRA_REDIRECT_URL> \
    --parameters AmazonQJiraPluginStack:jiraUrl=<JIRA_URL> \
    --parameters AmazonQJiraPluginStack:jiraAuthUrl=<JIRA_AUTH_URL> \
    --parameters AmazonQJiraPluginStack:jiraAccessTokenUrl=<JIRA_ACCESS_TOKEN_URL>