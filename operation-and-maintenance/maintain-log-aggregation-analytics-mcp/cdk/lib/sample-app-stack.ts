import * as cdk from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as apigateway from "aws-cdk-lib/aws-apigateway";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as events from "aws-cdk-lib/aws-events";
import * as targets from "aws-cdk-lib/aws-events-targets";
import * as logs from "aws-cdk-lib/aws-logs";
import * as iam from "aws-cdk-lib/aws-iam";
import { Construct } from "constructs";

export class SampleAppStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // DynamoDB table with explicit encryption and point-in-time recovery
    const table = new dynamodb.Table(this, "SampleTable", {
      partitionKey: { name: "pk", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      pointInTimeRecovery: true,
    });

    // Lambda that generates various log patterns
    const sampleLambda = new lambda.Function(this, "SampleFunction", {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "index.handler",
      code: lambda.Code.fromInline(`
import json
import random
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    request_id = context.aws_request_id
    logger.info(f"Processing request {request_id}")
    
    # Simulate various scenarios
    scenario = random.choice(['success', 'success', 'success', 'slow', 'error', 'warning'])
    
    if scenario == 'error':
        logger.error(f"Database connection failed for request {request_id}")
        raise Exception("Simulated database error")
    elif scenario == 'warning':
        logger.warning(f"High latency detected for request {request_id}")
    elif scenario == 'slow':
        import time
        time.sleep(2)
        logger.info(f"Slow operation completed for request {request_id}")
    
    logger.info(f"Request {request_id} completed successfully")
    return {'statusCode': 200, 'body': json.dumps({'status': 'ok', 'requestId': request_id})}
`),
      timeout: cdk.Duration.seconds(10),
      environment: { TABLE_NAME: table.tableName },
      tracing: lambda.Tracing.ACTIVE,
      logRetention: logs.RetentionDays.ONE_WEEK,
    });

    table.grantReadWriteData(sampleLambda);

    // API Gateway access logs
    const apiAccessLogs = new logs.LogGroup(this, "ApiAccessLogs", {
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // API Gateway with access logging, throttling, and API key authentication
    const api = new apigateway.RestApi(this, "SampleApi", {
      restApiName: "Log Analysis Sample API",
      deployOptions: {
        tracingEnabled: true,
        accessLogDestination: new apigateway.LogGroupLogDestination(
          apiAccessLogs,
        ),
        accessLogFormat: apigateway.AccessLogFormat.jsonWithStandardFields(),
        throttlingRateLimit: 10,
        throttlingBurstLimit: 20,
      },
    });
    api.root.addMethod("GET", new apigateway.LambdaIntegration(sampleLambda), {
      apiKeyRequired: true,
    });

    // API key and usage plan for authenticated access
    const apiKey = api.addApiKey("SampleApiKey", {
      apiKeyName: "log-analysis-sample-key",
    });

    const usagePlan = api.addUsagePlan("SampleUsagePlan", {
      name: "Standard",
      throttle: {
        rateLimit: 10,
        burstLimit: 20,
      },
      quota: {
        limit: 1000,
        period: apigateway.Period.DAY,
      },
    });
    usagePlan.addApiKey(apiKey);
    usagePlan.addApiStage({ stage: api.deploymentStage });

    // EventBridge rule to invoke Lambda periodically (for generating logs)
    new events.Rule(this, "ScheduleRule", {
      schedule: events.Schedule.rate(cdk.Duration.minutes(5)),
      targets: [new targets.LambdaFunction(sampleLambda)],
      enabled: false, // Enable manually when testing
    });

    // Least-privilege IAM role for the MCP server.
    // Developers assume this role via `aws sts assume-role` to get temporary credentials
    // scoped to only the actions the MCP server needs.
    // Configure MCP_SERVER_PRINCIPAL_ARN context variable to restrict who can assume this role.
    // Example: cdk deploy -c mcpServerPrincipalArn=arn:aws:iam::123456789012:user/developer
    const principalArn = this.node.tryGetContext("mcpServerPrincipalArn");
    const assumedBy = principalArn
      ? new iam.ArnPrincipal(principalArn)
      : new iam.AccountRootPrincipal(); // fallback: any principal in account

    const mcpServerRole = new iam.Role(this, "McpServerRole", {
      roleName: "LogAnalysisMcpServerRole",
      assumedBy,
      maxSessionDuration: cdk.Duration.hours(1),
      description: "Least-privilege role for the Log Analysis MCP Server",
    });

    // CloudWatch Logs — read-only, scoped to this stack's log groups
    mcpServerRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "CloudWatchLogsReadOnly",
        actions: [
          "logs:FilterLogEvents",
          "logs:DescribeLogGroups",
          "logs:GetLogEvents",
        ],
        resources: [
          sampleLambda.logGroup.logGroupArn,
          apiAccessLogs.logGroupArn,
        ],
      }),
    );

    // CloudWatch Metrics — read-only (does not support resource-level permissions)
    mcpServerRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "CloudWatchMetricsReadOnly",
        actions: ["cloudwatch:GetMetricStatistics", "cloudwatch:GetMetricData"],
        resources: ["*"],
        conditions: {
          StringEquals: { "aws:RequestedRegion": cdk.Stack.of(this).region },
        },
      }),
    );

    // X-Ray — read-only (does not support resource-level permissions)
    mcpServerRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "XRayReadOnly",
        actions: ["xray:BatchGetTraces", "xray:GetTraceSummaries"],
        resources: ["*"],
        conditions: {
          StringEquals: { "aws:RequestedRegion": cdk.Stack.of(this).region },
        },
      }),
    );

    // Bedrock — invoke only Claude 3 Haiku
    mcpServerRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "BedrockInvokeModel",
        actions: ["bedrock:InvokeModel"],
        resources: [
          `arn:aws:bedrock:${cdk.Stack.of(this).region}::foundation-model/anthropic.claude-3-haiku*`,
        ],
      }),
    );

    // Outputs
    new cdk.CfnOutput(this, "ApiUrl", { value: api.url });
    new cdk.CfnOutput(this, "LambdaLogGroup", {
      value: sampleLambda.logGroup.logGroupName,
    });
    new cdk.CfnOutput(this, "LambdaName", { value: sampleLambda.functionName });
    new cdk.CfnOutput(this, "ApiKeyId", { value: apiKey.keyId });
    new cdk.CfnOutput(this, "McpServerRoleArn", {
      value: mcpServerRole.roleArn,
      description: "Assume this role for least-privilege MCP server access",
    });
  }
}
