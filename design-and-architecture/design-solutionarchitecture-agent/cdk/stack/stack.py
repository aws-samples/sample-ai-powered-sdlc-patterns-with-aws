import os
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    CfnOutput,
    Size,
    aws_lambda as _lambda,
    aws_ecr_assets as ecr_assets,
    aws_iam as iam,
    aws_s3 as s3,
    aws_bedrock as bedrock,
    aws_ecr as ecr,
)
from constructs import Construct
from cdk_ecr_deployment import DockerImageName, ECRDeployment
from aws_cdk.aws_iam import PolicyStatement, AnyPrincipal, Effect, ServicePrincipal

class AWSAgentStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        repo_name = "sa_tools_function"
        region = self.region
        account = self.account

        # 1) Create logging bucket for S3 access logs
        logging_bucket = s3.Bucket(
            self, "AccessLogsBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True
        )
        
        # Main assets bucket with server access logging enabled
        assets_bucket = s3.Bucket(
            self, "SaToolAssetsBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            server_access_logs_bucket=logging_bucket,
            server_access_logs_prefix="assets-bucket-logs/"
        )

        repository = ecr.Repository(
            self, "DockerRepo",
            repository_name=repo_name,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # 2) Build your container from functions/sa_tool_function
        root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        sa_tool_dir = os.path.join(root, "functions", "sa_tool_function")

        image_asset = ecr_assets.DockerImageAsset(
            self, "SaToolImageAsset",
            directory=sa_tool_dir,
            platform=ecr_assets.Platform.LINUX_AMD64
        )

        # 3) Deploy image to the ECR repo with a specific tag
        image_uri = f"{account}.dkr.ecr.{region}.amazonaws.com/{repo_name}:latest"

        # 4) Grant specific permissions instead of using AnyPrincipal
        repository.add_to_resource_policy(PolicyStatement(
            principals=[iam.AccountPrincipal(self.account)],
            actions=[
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchCheckLayerAvailability",
                "ecr:BatchGetImage",
            ]
        ))

        # Create custom Lambda execution role with minimal permissions
        sa_lambda_role = iam.Role(
            self, "SaToolFunctionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            inline_policies={
                "CloudWatchLogsPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=Effect.ALLOW,
                            actions=[
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents"
                            ],
                            resources=[
                                f"arn:aws:logs:{region}:{account}:log-group:/aws/lambda/*"
                            ]
                        )
                    ]
                )
            }
        )

        sa_lambda = _lambda.DockerImageFunction(
            self, "SaToolFunction",
            code=_lambda.DockerImageCode.from_ecr(
                repository=repository,      
                tag_or_digest="latest"    
            ),
            memory_size=10240,
            timeout=Duration.seconds(600),
            environment={
                "VECTORSTORE_PATH": "/var/task/local_index",
            },
            role=sa_lambda_role
        )

        ecr_deployment = ECRDeployment(
            self, "DeployImageToRepo",
            src=DockerImageName(image_asset.image_uri),
            dest=DockerImageName(image_uri)
        )
        sa_lambda.node.add_dependency(ecr_deployment)
        repository.grant_pull(sa_lambda.role)

        # Grant specific S3 permissions
        assets_bucket.grant_read_write(sa_lambda)

        # Grant specific Bedrock permissions
        sa_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=[f"arn:aws:bedrock:{region}::foundation-model/*"]
        ))

        # Bedrock Agent Role with specific permissions
        bedrock_role = iam.Role(
            self, "BedrockAgentRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com")
        )
        
        sa_lambda.grant_invoke(bedrock_role)
        
        bedrock_role.add_to_policy(
            iam.PolicyStatement(
                sid="BedrockModelAccess",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                    "bedrock:GetInferenceProfile",
                    "bedrock:GetFoundationModel"
                ],
                resources=[f"arn:aws:bedrock:{region}::foundation-model/*"]
            )
        )

        # Drawing Function setup
        draw_repo_name = "drawing_function"
        draw_image_uri = f"{account}.dkr.ecr.{region}.amazonaws.com/{draw_repo_name}:latest"

        draw_repo = ecr.Repository(
            self, "DrawFunctionRepo",
            repository_name=draw_repo_name,
            removal_policy=RemovalPolicy.DESTROY,
        )
        
        draw_repo.add_to_resource_policy(PolicyStatement(
            principals=[iam.AccountPrincipal(self.account)],
            actions=[
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchCheckLayerAvailability",
                "ecr:BatchGetImage",
            ]
        ))

        draw_dir = os.path.join(root, "functions", "drawing_function")

        draw_image_asset = ecr_assets.DockerImageAsset(
            self, "DrawingFunctionImageAsset",
            directory=draw_dir,
            platform=ecr_assets.Platform.LINUX_AMD64,
        )

        draw_deploy = ECRDeployment(
            self, "DeployDrawingFunctionImage",
            src=DockerImageName(draw_image_asset.image_uri),
            dest=DockerImageName(draw_image_uri)
        )

        # Create custom role for drawing function
        draw_lambda_role = iam.Role(
            self, "DrawingFunctionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            inline_policies={
                "CloudWatchLogsPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=Effect.ALLOW,
                            actions=[
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents"
                            ],
                            resources=[
                                f"arn:aws:logs:{region}:{account}:log-group:/aws/lambda/*"
                            ]
                        )
                    ]
                )
            }
        )

        draw_lambda = _lambda.DockerImageFunction(
            self, "DrawingFunction",
            code=_lambda.DockerImageCode.from_ecr(
                repository=draw_repo,
                tag_or_digest="latest"
            ),
            memory_size=10240,
            timeout=Duration.seconds(600),
            ephemeral_storage_size=Size.mebibytes(10240),
            environment={
                "S3_BUCKET_NAME": assets_bucket.bucket_name
            },
            role=draw_lambda_role
        )

        draw_lambda.node.add_dependency(draw_deploy)
        draw_repo.grant_pull(draw_lambda.role)
        assets_bucket.grant_read_write(draw_lambda)
        draw_lambda.grant_invoke(bedrock_role)

        draw_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=[f"arn:aws:bedrock:{region}::foundation-model/*"]
        ))

        draw_lambda.add_permission(
            "AllowBedrockInvoke",
            principal=iam.ServicePrincipal("bedrock.amazonaws.com"),
            action="lambda:InvokeFunction"
        )

        # Read OpenAPI JSON
        spec_path = os.path.join(sa_tool_dir, "agent_aws_openapi.json")
        if not os.path.exists(spec_path):
            raise FileNotFoundError(f"Cannot find OpenAPI spec at {spec_path}")

        with open(spec_path, "r") as f:
            schema = f.read()

        agent = bedrock.CfnAgent(
            self, "SaToolAgent",
            agent_name="SaToolAgent",
            agent_resource_role_arn=bedrock_role.role_arn,
            description="Agent AWS is an automated, AI-powered agent that helps customers with knowledge of AWS by querying the AWS Well-Architected Framework and writing code.",
            foundation_model="anthropic.claude-3-5-sonnet-20241022-v2:0",
            auto_prepare=True,
            instruction=(
                "You are an expert AWS Certified Solutions Architect. Your role is to help customers understand best practices on building on AWS."
            ),
            action_groups=[
                bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="SaTools",
                    description="API that helps customer with knowledge of AWS by querying the AWS Well Architected Framework, writing codes and creating diagrams.",
                    action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=sa_lambda.function_arn
                    ),
                    api_schema=bedrock.CfnAgent.APISchemaProperty(
                        payload=schema
                    )
                ),
                bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="drawing",
                    description="API that helps user to draw the architecture with drawio",
                    action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=draw_lambda.function_arn
                    ),
                    function_schema=bedrock.CfnAgent.FunctionSchemaProperty(
                        functions=[
                            bedrock.CfnAgent.FunctionProperty(
                                name="drawingfunction",
                                description="draw an architecture",
                                parameters={
                                    "draw": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="draw architecture",
                                        required=False
                                    ),
                                    "generate": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="generate architecture",
                                        required=False
                                    ),
                                    "create": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="create",
                                        required=False
                                    ),
                                    "show": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="show",
                                        required=False
                                    )
                                }
                            )
                        ]
                    )
                )
            ]
        )

        # Outputs
        CfnOutput(self, "LambdaArn", value=sa_lambda.function_arn)
        CfnOutput(self, "ECRImageUri", value=f"{image_asset.repository.repository_uri}:{image_asset.image_tag}")
        CfnOutput(self, "AgentId", value=agent.attr_agent_id)
        CfnOutput(self, "AssetsBucket", value=assets_bucket.bucket_name)
