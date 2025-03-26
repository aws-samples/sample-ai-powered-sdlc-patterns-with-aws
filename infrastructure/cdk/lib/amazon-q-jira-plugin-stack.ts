import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as qbusiness from 'aws-cdk-lib/aws-qbusiness';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';

interface CustomProps extends cdk.StackProps {
    readonly app: qbusiness.CfnApplication;
    readonly appWebEndpoint: string;
}

export class AmazonQJiraPluginStack extends cdk.Stack {
    constructor(scope: Construct, id: string, props: CustomProps) {
        super(scope, id, props);

        const awsAccountId = cdk.Stack.of(this).account;

        cdk.Stack.of(this).templateOptions.description = 'Amazon Q Business Jira Plugin Stack';

        const jiraUrlParameter = new cdk.CfnParameter(this, 'jiraUrl', {
            type: 'String',
            description: 'Domain URL of your Jira Cloud organization'
        });

        const jiraAuthUrlParameter = new cdk.CfnParameter(this, 'jiraAuthUrl', {
            type: 'String',
            description: 'The URL for Jira Cloud’s authorization server, to retrieve the auth code. This may be provided by Jira Cloud during OAuth app creation.'
        });

        const jiraAccessTokenUrlParameter = new cdk.CfnParameter(this, 'jiraAccessTokenUrl', {
            type: 'String',
            description: "The URL for Jira Cloud's authentication server, to exchange an authorization code for an access token. Usually ends with 'oauth/token' or 'oauth2/token'."
        });

        const jiraClientIdParameter = new cdk.CfnParameter(this, 'jiraClientId', {
            type: 'String',
            description: 'The client ID generated when you create your OAuth 2.0 application in Jira Cloud.'
        });

        const jiraClientSecretParameter = new cdk.CfnParameter(this, 'jiraClientSecret', {
            type: 'String',
            description: 'The client secret generated when you create your OAuth 2.0 application in Jira Cloud.'
        });

        const jiraRedirectPathParameter = new cdk.CfnParameter(this, 'jiraRedirectPath', {
            type: 'String',
            description: 'The URL path to which user needs to be redirected after authentication.'
        });

        const jiraUrl = jiraUrlParameter.valueAsString;
        const jiraAuthUrl = jiraAuthUrlParameter.valueAsString;
        const jiraAccessTokenUrl = jiraAccessTokenUrlParameter.valueAsString;
        const jiraClientId = jiraClientIdParameter.valueAsString;
        const jiraClientSecret = jiraClientSecretParameter.valueAsString;
        const jiraRedirectUrl = props.appWebEndpoint + jiraRedirectPathParameter.valueAsString;

        const secret = new secretsmanager.Secret(this, `QBusinessJiraSecret`, {
            secretName: `QBusiness-Jira-${props.app.displayName}`,
            secretObjectValue: {
                client_id: cdk.SecretValue.unsafePlainText(jiraClientId),
                client_secret: cdk.SecretValue.unsafePlainText(jiraClientSecret),
                redirect_uri: cdk.SecretValue.unsafePlainText(jiraRedirectUrl),
            },
        });

        // IAM policy and role for the Q Business Confluence Data Source
        const jiraPolicy = new iam.ManagedPolicy(this, 'JiraPolicy', {
            statements: [
                new iam.PolicyStatement({
                    sid: 'AllowQBusinessToGetSecretValue',
                    actions: ["secretsmanager:GetSecretValue"],
                    resources: [secret.secretArn],
                }),
            ]
        });

        const jiraRole = new iam.Role(this, 'JiraRole', {
            roleName: `QBusiness-Jira-Role-${props.app.displayName}`,
            assumedBy: new iam.ServicePrincipal('qbusiness.amazonaws.com', {
                conditions: {
                    StringEquals: {
                        'aws:SourceAccount': awsAccountId,
                    },
                    ArnEquals: {
                        'aws:SourceArn':
                            props.app.attrApplicationArn,
                    },
                },
            },
            ),
            managedPolicies: [jiraPolicy],
        },
        );

        new qbusiness.CfnPlugin(this, 'JiraPlugin', {
            applicationId: props.app.attrApplicationId,
            displayName: `JiraPlugin-${props.app.displayName}`,
            type: 'JIRA_CLOUD',
            serverUrl: jiraUrl,
            authConfiguration: {
                oAuth2ClientCredentialConfiguration: {
                    roleArn: jiraRole.roleArn,
                    secretArn: secret.secretArn,
                    authorizationUrl: jiraAuthUrl,
                    tokenUrl: jiraAccessTokenUrl,
                },
            }
        });
    }
}