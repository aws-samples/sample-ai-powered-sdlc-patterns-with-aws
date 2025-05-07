import * as cdk from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";
import * as kms from 'aws-cdk-lib/aws-kms';
import * as qbusiness from 'aws-cdk-lib/aws-qbusiness';
import { Construct } from "constructs";

export class AmazonQBusinessStack extends cdk.Stack {
    public app: qbusiness.CfnApplication;
    public index: qbusiness.CfnIndex;
    public webEndpoint: string;

    constructor(scope: Construct, id: string, props?: cdk.StackProps) {
        super(scope, id, props);

        const awsAccountId = cdk.Stack.of(this).account;
        const region = cdk.Stack.of(this).region

        cdk.Stack.of(this).templateOptions.description = 'Amazon Q Business Base Stack';

        const AppNameParameter = new cdk.CfnParameter(this, 'appName', {
            type: 'String',
            description: 'The Amazon Q application name',
            allowedPattern: '^[a-zA-Z0-9][a-zA-Z0-9_-]*$'
        });

        const iamIdentityCenterArnParameter = new cdk.CfnParameter(this, 'iamIdentityCenterArn', {
            type: 'String',
            description: 'The arn of IAM Identity Center'
        });

        const qBusinessWebRoleArnParameter = new cdk.CfnParameter(this, 'qBusinessWebRoleArn', {
            type: 'String',
            description: 'The Amazon Q Business Web Experience Role'
        });

        const appName = AppNameParameter.valueAsString;
        const iamIdentityCenterArn = iamIdentityCenterArnParameter.valueAsString;
        const qBusinessWebRoleArn = qBusinessWebRoleArnParameter.valueAsString;

        const cdk_app = new qbusiness.CfnApplication(this, 'AmazonQBusinessApp', {
            displayName: appName,
            attachmentsConfiguration: {
                attachmentsControlMode: "ENABLED",
            },
            identityCenterInstanceArn: iamIdentityCenterArn,
            description: "Amazon Q Business Application",

        });

        
        const web_role_policy = new iam.ManagedPolicy(this, "AmazonQBusinessWebManagedPolicy" , {
            roles: [iam.Role.fromRoleArn(this, "AmazonQBusinessWebRole", qBusinessWebRoleArn)],
            document: new iam.PolicyDocument({
                statements:[
                    new iam.PolicyStatement({
                        sid: "AmazonQBusinessIndexPermission",
                        effect: iam.Effect.ALLOW,
                        actions:[
                            "qbusiness:ListIndices"
                        ],
                        resources: [`arn:aws:qbusiness:${region}:${awsAccountId}:application/${cdk_app.attrApplicationId}`]
                    }),
                    new iam.PolicyStatement({
                        sid: "AmazonQBusinessDataSourcePermission",
                        effect: iam.Effect.ALLOW,
                        actions:[
                            "qbusiness:ListDataSources"
                        ],
                        resources: [
                            `arn:aws:qbusiness:${region}:${awsAccountId}:application/${cdk_app.attrApplicationId}`,
                            `arn:aws:qbusiness:${region}:${awsAccountId}:application/${cdk_app.attrApplicationId}/index/*`
                        ]
                    }),
                    new iam.PolicyStatement({
                        sid: "AmazonQBusinessConversationPermission",
                        effect: iam.Effect.ALLOW,
                        actions:[
                            "qbusiness:Chat",
                            "qbusiness:ChatSync",
                            "qbusiness:ListMessages",
                            "qbusiness:ListConversations",
                            "qbusiness:DeleteConversation",
                            "qbusiness:PutFeedback",
                            "qbusiness:GetWebExperience",
                            "qbusiness:GetApplication",
                            "qbusiness:ListPlugins",
                            "qbusiness:ListPluginActions",
                            "qbusiness:GetChatControlsConfiguration",
                            "qbusiness:ListRetrievers",
                            "qbusiness:ListAttachments",
                            "qbusiness:GetMedia"
                        ],
                        resources: [`arn:aws:qbusiness:${region}:${awsAccountId}:application/${cdk_app.attrApplicationId}`]
                    }),
                    new iam.PolicyStatement({
                        sid: "AmazonQBusinessPluginDiscoveryPermissions",
                        effect: iam.Effect.ALLOW,
                        actions:[
                            "qbusiness:ListPluginTypeMetadata",
                            "qbusiness:ListPluginTypeActions"
                        ],
                        resources: ["*"]
                    }),
                    new iam.PolicyStatement({
                        sid: "AmazonQBusinessRetrieverPermission",
                        effect: iam.Effect.ALLOW,
                        actions:[
                            "qbusiness:GetRetriever"
                        ],
                        resources: [
                            `arn:aws:qbusiness:${region}:${awsAccountId}:application/${cdk_app.attrApplicationId}`,
                            `arn:aws:qbusiness:${region}:${awsAccountId}:application/${cdk_app.attrApplicationId}/retriever/*`
                        ]
                    }),
                    new iam.PolicyStatement({
                        sid: "AmazonQAppsResourceAgnosticPermissions",
                        effect: iam.Effect.ALLOW,
                        actions:[
                            "qapps:CreateQApp",
                            "qapps:PredictQApp",
                            "qapps:PredictProblemStatementFromConversation",
                            "qapps:PredictQAppFromProblemStatement",
                            "qapps:ListQApps",
                            "qapps:ListLibraryItems",
                            "qapps:CreateSubscriptionToken",
                            "qapps:ListCategories"
                        ],
                        resources: [
                            `arn:aws:qbusiness:${region}:${awsAccountId}:application/${cdk_app.attrApplicationId}`
                        ]
                    }),
                    new iam.PolicyStatement({
                        sid: "AmazonQAppsAppUniversalPermissions",
                        effect: iam.Effect.ALLOW,
                        actions:[
                            "qapps:DisassociateQAppFromUser"
                        ],
                        resources: [
                            `arn:aws:qapps:${region}:${awsAccountId}:application/${cdk_app.attrApplicationId}/qapp/*`
                        ]
                    }),
                    new iam.PolicyStatement({
                        sid: "AmazonQAppsAppOwnerPermissions",
                        effect: iam.Effect.ALLOW,
                        actions:[
                            "qapps:GetQApp",
                            "qapps:CopyQApp",
                            "qapps:UpdateQApp",
                            "qapps:DeleteQApp",
                            "qapps:ImportDocument",
                            "qapps:ImportDocumentToQApp",
                            "qapps:CreateLibraryItem",
                            "qapps:UpdateLibraryItem",
                            "qapps:StartQAppSession",
                            "qapps:DescribeQAppPermissions",
                            "qapps:UpdateQAppPermissions",
                            "qapps:CreatePresignedUrl"
                        ],
                        resources: [
                            `arn:aws:qapps:${region}:${awsAccountId}:application/${cdk_app.attrApplicationId}/qapp/*`
                        ],
                        conditions:{
                            StringEqualsIgnoreCase: {
                                "qapps:UserIsAppOwner": "true"
                            }
                        }
                    }),
                    new iam.PolicyStatement({
                        sid: "AmazonQAppsPublishedAppPermissions",
                        effect: iam.Effect.ALLOW,
                        actions:[
                            "qapps:GetQApp",
                            "qapps:CopyQApp",
                            "qapps:AssociateQAppWithUser",
                            "qapps:GetLibraryItem",
                            "qapps:CreateLibraryItemReview",
                            "qapps:AssociateLibraryItemReview",
                            "qapps:DisassociateLibraryItemReview",
                            "qapps:StartQAppSession",
                            "qapps:DescribeQAppPermissions"
                        ],
                        resources: [
                            `arn:aws:qapps:${region}:${awsAccountId}:application/${cdk_app.attrApplicationId}/qapp/*`
                        ],
                        conditions:{
                            StringEqualsIgnoreCase: {
                                "qapps:AppIsPublished": "true"
                            }
                        }
                    }),
                    new iam.PolicyStatement({
                        sid: "AmazonQAppsAppSessionModeratorPermissions",
                        effect: iam.Effect.ALLOW,
                        actions:[
                            "qapps:ImportDocument",
                            "qapps:ImportDocumentToQAppSession",
                            "qapps:GetQAppSession",
                            "qapps:GetQAppSessionMetadata",
                            "qapps:UpdateQAppSession",
                            "qapps:UpdateQAppSessionMetadata",
                            "qapps:StopQAppSession",
                            "qapps:ListQAppSessionData",
                            "qapps:ExportQAppSessionData",
                            "qapps:CreatePresignedUrl"
                        ],
                        resources: [
                            `arn:aws:qapps:${region}:${awsAccountId}:application/${cdk_app.attrApplicationId}/qapp/*/session/*`
                        ],
                        conditions:{
                            StringEqualsIgnoreCase: {
                                "qapps:UserIsSessionModerator": "true"
                            }
                        }
                    }),
                    new iam.PolicyStatement({
                        sid: "AmazonQAppsSharedAppSessionPermissions",
                        effect: iam.Effect.ALLOW,
                        actions:[
                            "qapps:ImportDocument",
                            "qapps:ImportDocumentToQAppSession",
                            "qapps:GetQAppSession",
                            "qapps:GetQAppSessionMetadata",
                            "qapps:UpdateQAppSession",
                            "qapps:ListQAppSessionData",
                            "qapps:CreatePresignedUrl"
                        ],
                        resources: [
                            `arn:aws:qapps:${region}:${awsAccountId}:application/${cdk_app.attrApplicationId}/qapp/*/session/*`
                        ],
                        conditions:{
                            StringEqualsIgnoreCase: {
                                "qapps:SessionIsShared": "true"
                            }
                        }
                    }),
                    new iam.PolicyStatement({
                        sid: "AmazonQBusinessToQuickSightGenerateEmbedUrlInvocation",
                        effect: iam.Effect.ALLOW,
                        actions:[
                            "quicksight:GenerateEmbedUrlForRegisteredUserWithIdentity"
                        ],
                        resources: ["*"]
                    })
                ]
            })
        })

        const q_index = new qbusiness.CfnIndex(this, 'AmazonQBusinessIndex', {
            applicationId: cdk_app.attrApplicationId,
            displayName: `${appName}-index`,
            description: "Amazon Q Business Index",
            capacityConfiguration: {
                units: 1,
            },
            type: "STARTER",
        });

        const indexId = cdk.Fn.select(1, cdk.Fn.split("|", q_index.ref))

        const q_retriever = new qbusiness.CfnRetriever(this, 'AmazonQBusinessRetriever', {
            applicationId: cdk_app.attrApplicationId,
            displayName: `${appName}-retriever`,
            type: "NATIVE_INDEX",
            configuration: {
                nativeIndexConfiguration: {
                    indexId: indexId,
                },
            }
        });

        const web_experience = new qbusiness.CfnWebExperience(this, 'AmazonQBusinessWebExperience', {
            applicationId: cdk_app.attrApplicationId,
            roleArn: qBusinessWebRoleArn,
            title: appName,
            welcomeMessage: `Welcome to Amazon Q Business!`,
        });
        this.app = cdk_app;
        this.index = q_index;
        this.webEndpoint = web_experience.attrDefaultEndpoint;
    }
}