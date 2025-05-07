import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";
import * as iam from 'aws-cdk-lib/aws-iam';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';

export interface CustomProps extends cdk.StackProps {
    readonly index: cdk.aws_qbusiness.CfnIndex;
    readonly app: cdk.aws_qbusiness.CfnApplication;
}

export class AmazonQConfluenceSourceStack extends cdk.Stack {
    public confluence_datasource_role: cdk.aws_iam.Role;

    constructor(scope: Construct, id: string, props: CustomProps) {
        super(scope, id, props);

        const region = cdk.Stack.of(this).region
        const awsAccountId = cdk.Stack.of(this).account;

        cdk.Stack.of(this).templateOptions.description = 'Amazon Q Business Confluence Data Source Stack';

        const confluenceUrlParameter = new cdk.CfnParameter(this, 'confluenceUrl', {
            type: 'String',
            description: 'The Confluence URL, for example: https://example.atlassian.net'
        });

        const confluenceUsernameParameter = new cdk.CfnParameter(this, 'confluenceUsername', {
            type: 'String',
            description: 'Email ID used to log into Confluence'
        });

        const confluencePasswordParameter = new cdk.CfnParameter(this, 'confluencePassword', {
            type: 'String',
            description: 'Confluence API token'
        });

        const confluenceUrl = confluenceUrlParameter.valueAsString;
        const confluenceUsername = confluenceUsernameParameter.valueAsString;
        const confluencePassword = confluencePasswordParameter.valueAsString;

        const encryptionKey = new kms.Key(this, "EncryptionKey",{
            enableKeyRotation: true
        });

        const secret = new secretsmanager.Secret(this, `AmazonQBusinessConfluenceSecret`, {
            secretObjectValue: {
                username: cdk.SecretValue.unsafePlainText(confluenceUsername),
                password: cdk.SecretValue.unsafePlainText(confluencePassword),
            },
            encryptionKey: encryptionKey
        },
        );

        const confluencePolicy = new iam.ManagedPolicy(this, 'ConfluencePolicy', {
            statements: [
                new iam.PolicyStatement({
                    sid: 'AllowsAmazonQToGetS3Objects',
                    actions: ['s3:GetObject'],
                    resources: ['arn:aws:s3:::bucket/*'],
                    conditions: {
                        StringEquals: {
                            'aws:ResourceAccount': awsAccountId,
                        },
                    },
                }),
                new iam.PolicyStatement({
                    sid: 'AllowsAmazonQToGetSecret',
                    actions: ['secretsmanager:GetSecretValue'],
                    resources: [secret.secretArn],
                }),
                new iam.PolicyStatement({
                    sid: 'AllowsAmazonQToDecryptSecret',
                    actions: ['kms:Decrypt'],
                    resources: [encryptionKey.keyArn],
                    conditions: {
                        StringLike: {
                            'kms:ViaService': [
                                'secretsmanager.*.amazonaws.com',
                            ],
                        },
                    },
                }),
                new iam.PolicyStatement({
                    sid: 'AllowsAmazonQToIngestDocuments',
                    actions: [
                        'qbusiness:BatchPutDocument',
                        'qbusiness:BatchDeleteDocument',
                    ],
                    resources: [props.index.attrIndexArn],
                }),
                new iam.PolicyStatement({
                    sid: 'AllowsAmazonQToIngestPrincipalMapping',
                    actions: [
                        'qbusiness:PutGroup',
                        'qbusiness:CreateUser',
                        'qbusiness:DeleteGroup',
                        'qbusiness:UpdateUser',
                        'qbusiness:ListGroups',
                    ],
                    resources: [
                        props.app.attrApplicationArn,
                        props.index.attrIndexArn,
                        `${props.index.attrIndexArn}/data-source/*`,
                    ],
                }),
            ]
        });

        const confluenceRole = new iam.Role(this, 'ConfluenceSourceRole', {
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
            managedPolicies: [confluencePolicy],
        },
        );

        new cdk.aws_qbusiness.CfnDataSource(this, 'ConfluenceSource', {
            applicationId: props.app.attrApplicationId,
            displayName: `${props.app.displayName}-ConfluenceDataSource`,
            indexId: props.index.attrIndexId,
            description: "Amazon Q Business Confluence Source",
            roleArn: confluenceRole.roleArn,
            configuration: {
                type: 'CONFLUENCEV2',
                secretArn: secret.secretArn,
                syncMode: 'FORCED_FULL_CRAWL',
                enableIdentityCrawler: true,
                connectionConfiguration: {
                    repositoryEndpointMetadata: {
                        type: 'SAAS',
                        hostUrl: confluenceUrl,
                        authType: 'Basic',
                    },
                },
                repositoryConfigurations: {
                    space: {
                        fieldMappings: [{
                            dataSourceFieldName: 'itemType',
                            indexFieldName: '_category',
                            indexFieldType: 'STRING',
                        }, {
                            dataSourceFieldName: 'url',
                            indexFieldName: '_source_uri',
                            indexFieldType: 'STRING',
                        }, {
                            dataSourceFieldName: 'spaceName',
                            indexFieldName: '_document_title',
                            indexFieldType: 'STRING',
                        }, {
                            dataSourceFieldName: 'spaceKey',
                            indexFieldName: 'cf_space_key',
                            indexFieldType: 'STRING',
                        }, {
                            dataSourceFieldName: 'description',
                            indexFieldName: 'cf_description',
                            indexFieldType: 'STRING',
                        }, {
                            dataSourceFieldName: 'spaceType',
                            indexFieldName: 'cf_type',
                            indexFieldType: 'STRING',
                        }],
                    },
                    page: {
                        fieldMappings: [{
                            dataSourceFieldName: 'author',
                            indexFieldName: '_authors',
                            indexFieldType: 'STRING_LIST',
                        }, {
                            dataSourceFieldName: 'createdDate',
                            indexFieldName: '_created_at',
                            dateFieldFormat: "yyyy-MM-dd'T'HH:mm:ss'Z'",
                            indexFieldType: 'DATE',
                        }, {
                            dataSourceFieldName: 'modifiedDate',
                            indexFieldName: '_last_updated_at',
                            dateFieldFormat: "yyyy-MM-dd'T'HH:mm:ss'Z'",
                            indexFieldType: 'DATE',
                        }, {
                            dataSourceFieldName: 'itemType',
                            indexFieldName: '_category',
                            indexFieldType: 'STRING'
                        }, {
                            dataSourceFieldName: 'url',
                            indexFieldName: '_source_uri',
                            indexFieldType: 'STRING'
                        }, {
                            dataSourceFieldName: 'title',
                            indexFieldName: '_document_title',
                            indexFieldType: 'STRING'
                        }, {
                            dataSourceFieldName: 'labels',
                            indexFieldName: 'cf_labels',
                            indexFieldType: 'STRING_LIST'
                        }, {
                            dataSourceFieldName: 'spaceKey',
                            indexFieldName: 'cf_space_key',
                            indexFieldType: 'STRING'
                        }, {
                            dataSourceFieldName: 'spaceName',
                            indexFieldName: 'cf_space_name',
                            indexFieldType: 'STRING'
                        }, {
                            dataSourceFieldName: 'status',
                            indexFieldName: 'cf_status',
                            indexFieldType: 'STRING'
                        }, {
                            dataSourceFieldName: 'parentId',
                            indexFieldName: 'cf_parent_id',
                            indexFieldType: 'STRING'
                        }]
                    },
                    blog: {
                        fieldMappings: [{
                            dataSourceFieldName: 'author',
                            indexFieldName: '_authors',
                            indexFieldType: 'STRING_LIST',
                        }, {
                            dataSourceFieldName: 'createdDate',
                            indexFieldName: '_created_at',
                            dateFieldFormat: "yyyy-MM-dd'T'HH:mm:ss'Z'",
                            indexFieldType: 'DATE',
                        }, {
                            dataSourceFieldName: 'modifiedDate',
                            indexFieldName: '_last_updated_at',
                            dateFieldFormat: "yyyy-MM-dd'T'HH:mm:ss'Z'",
                            indexFieldType: 'DATE',
                        }, {
                            dataSourceFieldName: 'itemType',
                            indexFieldName: '_category',
                            indexFieldType: 'STRING'
                        }, {
                            dataSourceFieldName: 'url',
                            indexFieldName: '_source_uri',
                            indexFieldType: 'STRING'
                        }, {
                            dataSourceFieldName: 'title',
                            indexFieldName: '_document_title',
                            indexFieldType: 'STRING'
                        }, {
                            dataSourceFieldName: 'labels',
                            indexFieldName: 'cf_labels',
                            indexFieldType: 'STRING_LIST'
                        }, {
                            dataSourceFieldName: 'spaceKey',
                            indexFieldName: 'cf_space_key',
                            indexFieldType: 'STRING'
                        }, {
                            dataSourceFieldName: 'spaceName',
                            indexFieldName: 'cf_space_name',
                            indexFieldType: 'STRING'
                        }, {
                            dataSourceFieldName: 'status',
                            indexFieldName: 'cf_status',
                            indexFieldType: 'STRING'
                        }, {
                            dataSourceFieldName: 'parentId',
                            indexFieldName: 'cf_parent_id',
                            indexFieldType: 'STRING'
                        }]
                    },
                    comment: {
                        fieldMappings: [{
                            dataSourceFieldName: 'author',
                            indexFieldName: '_authors',
                            indexFieldType: 'STRING_LIST',
                        }, {
                            dataSourceFieldName: 'createdDate',
                            indexFieldName: '_created_at',
                            dateFieldFormat: "yyyy-MM-dd'T'HH:mm:ss'Z'",
                            indexFieldType: 'DATE',
                        }, {
                            dataSourceFieldName: 'itemType',
                            indexFieldName: '_category',
                            indexFieldType: 'STRING'
                        }, {
                            dataSourceFieldName: 'url',
                            indexFieldName: '_source_uri',
                            indexFieldType: 'STRING'
                        }, {
                            dataSourceFieldName: 'title',
                            indexFieldName: '_document_title',
                            indexFieldType: 'STRING'
                        }, {
                            dataSourceFieldName: 'contentType',
                            indexFieldName: 'cf_content_type',
                            indexFieldType: 'STRING'
                        }, {
                            dataSourceFieldName: 'spaceKey',
                            indexFieldName: 'cf_space_key',
                            indexFieldType: 'STRING'
                        }, {
                            dataSourceFieldName: 'spaceName',
                            indexFieldName: 'cf_space_name',
                            indexFieldType: 'STRING'
                        }, {
                            dataSourceFieldName: 'status',
                            indexFieldName: 'cf_status',
                            indexFieldType: 'STRING'
                        }, {
                            dataSourceFieldName: 'parentId',
                            indexFieldName: 'cf_parent_id',
                            indexFieldType: 'STRING'
                        }]
                    }
                },
                additionalProperties: {
                    isCrawlBlog: true,
                    isCrawlPageComment: true,
                    isCrawlPage: true,
                    isCrawlBlogAttachment: true,
                    isCrawlPageAttachment: true,
                    isCrawlAcl: true,
                    isCrawlPersonalSpace: false,
                    isCrawlArchivedSpace: false,
                    isCrawlArchivedPage: false,
                    isCrawlBlogComment: false,

                    exclusionUrlPatterns: [],
                    inclusionFileTypePatterns: [],
                    blogTitleRegEX: [],
                    proxyPort: '',
                    inclusionUrlPatterns: [],
                    attachmentTitleRegEX: [],
                    includeSupportedFileType: false,
                    commentTitleRegEX: [],
                    exclusionSpaceKeyFilter: [],
                    exclusionFileTypePatterns: [],
                    inclusionSpaceKeyFilter: [],
                    maxFileSizeInMegaBytes: '50',
                    proxyHost: '',
                    pageTitleRegEX: []
                },
            },
        });
    }
}