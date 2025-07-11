#!/bin/bash

# AWS ECS Fargate Deployment Script for Java 21 Application
# Cost: ~$47-65/month

echo "🐳 Deploying Java 21 App to AWS ECS Fargate"
echo "============================================"

# Configuration
APP_NAME="java21-app"
CLUSTER_NAME="java21-cluster"
SERVICE_NAME="java21-service"
TASK_FAMILY="java21-task"
REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$APP_NAME"

echo "📋 Configuration:"
echo "   Account ID: $ACCOUNT_ID"
echo "   Region: $REGION"
echo "   ECR Repository: $ECR_REPO"

# Check prerequisites
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is required but not installed."
    exit 1
fi

if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

echo "🏗️  Step 1: Building application..."
cd ../java21-app
./mvnw clean package -DskipTests

if [ $? -ne 0 ]; then
    echo "❌ Build failed!"
    exit 1
fi

echo "✅ Application built successfully!"

# Create Dockerfile
cat > Dockerfile << EOF
FROM amazoncorretto:21-alpine

# Set working directory
WORKDIR /app

# Copy the JAR file
COPY target/java21-app-0.0.1-SNAPSHOT.jar app.jar

# Expose port
EXPOSE 8082

# Add health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8082/actuator/health || exit 1

# Run the application
ENTRYPOINT ["java", "-jar", "app.jar"]
EOF

echo "📦 Step 2: Creating ECR repository..."
aws ecr create-repository --repository-name $APP_NAME --region $REGION 2>/dev/null || echo "Repository already exists"

echo "🔐 Step 3: Logging into ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_REPO

echo "🐳 Step 4: Building Docker image..."
docker build -t $APP_NAME .
docker tag $APP_NAME:latest $ECR_REPO:latest

echo "📤 Step 5: Pushing image to ECR..."
docker push $ECR_REPO:latest

echo "🎯 Step 6: Creating ECS cluster..."
aws ecs create-cluster --cluster-name $CLUSTER_NAME --region $REGION

echo "📝 Step 7: Creating task definition..."
cat > task-definition.json << EOF
{
  "family": "$TASK_FAMILY",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::$ACCOUNT_ID:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::$ACCOUNT_ID:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "$APP_NAME",
      "image": "$ECR_REPO:latest",
      "portMappings": [
        {
          "containerPort": 8082,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/$TASK_FAMILY",
          "awslogs-region": "$REGION",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "environment": [
        {
          "name": "SPRING_PROFILES_ACTIVE",
          "value": "production"
        }
      ],
      "healthCheck": {
        "command": [
          "CMD-SHELL",
          "curl -f http://localhost:8082/actuator/health || exit 1"
        ],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
EOF

# Create CloudWatch log group
aws logs create-log-group --log-group-name "/ecs/$TASK_FAMILY" --region $REGION 2>/dev/null || echo "Log group already exists"

# Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json --region $REGION

echo "🌐 Step 8: Creating Application Load Balancer..."
# Get default VPC and subnets
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=is-default,Values=true" --query 'Vpcs[0].VpcId' --output text --region $REGION)
SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[*].SubnetId' --output text --region $REGION)
SUBNET_ARRAY=($SUBNET_IDS)

# Create security group for ALB
ALB_SG_ID=$(aws ec2 create-security-group \
    --group-name "$APP_NAME-alb-sg" \
    --description "Security group for $APP_NAME ALB" \
    --vpc-id $VPC_ID \
    --region $REGION \
    --query 'GroupId' --output text 2>/dev/null || \
    aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=$APP_NAME-alb-sg" \
    --query 'SecurityGroups[0].GroupId' --output text --region $REGION)

# Allow HTTP traffic to ALB
aws ec2 authorize-security-group-ingress \
    --group-id $ALB_SG_ID \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0 \
    --region $REGION 2>/dev/null || echo "HTTP rule already exists"

# Create security group for ECS tasks
ECS_SG_ID=$(aws ec2 create-security-group \
    --group-name "$APP_NAME-ecs-sg" \
    --description "Security group for $APP_NAME ECS tasks" \
    --vpc-id $VPC_ID \
    --region $REGION \
    --query 'GroupId' --output text 2>/dev/null || \
    aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=$APP_NAME-ecs-sg" \
    --query 'SecurityGroups[0].GroupId' --output text --region $REGION)

# Allow traffic from ALB to ECS tasks
aws ec2 authorize-security-group-ingress \
    --group-id $ECS_SG_ID \
    --protocol tcp \
    --port 8082 \
    --source-group $ALB_SG_ID \
    --region $REGION 2>/dev/null || echo "ECS rule already exists"

# Create Application Load Balancer
ALB_ARN=$(aws elbv2 create-load-balancer \
    --name "$APP_NAME-alb" \
    --subnets ${SUBNET_ARRAY[0]} ${SUBNET_ARRAY[1]} \
    --security-groups $ALB_SG_ID \
    --region $REGION \
    --query 'LoadBalancers[0].LoadBalancerArn' --output text 2>/dev/null || \
    aws elbv2 describe-load-balancers \
    --names "$APP_NAME-alb" \
    --query 'LoadBalancers[0].LoadBalancerArn' --output text --region $REGION)

# Create target group
TG_ARN=$(aws elbv2 create-target-group \
    --name "$APP_NAME-tg" \
    --protocol HTTP \
    --port 8082 \
    --vpc-id $VPC_ID \
    --target-type ip \
    --health-check-path "/actuator/health" \
    --region $REGION \
    --query 'TargetGroups[0].TargetGroupArn' --output text 2>/dev/null || \
    aws elbv2 describe-target-groups \
    --names "$APP_NAME-tg" \
    --query 'TargetGroups[0].TargetGroupArn' --output text --region $REGION)

# Create listener
aws elbv2 create-listener \
    --load-balancer-arn $ALB_ARN \
    --protocol HTTP \
    --port 80 \
    --default-actions Type=forward,TargetGroupArn=$TG_ARN \
    --region $REGION 2>/dev/null || echo "Listener already exists"

echo "🚀 Step 9: Creating ECS service..."
cat > service-definition.json << EOF
{
  "serviceName": "$SERVICE_NAME",
  "cluster": "$CLUSTER_NAME",
  "taskDefinition": "$TASK_FAMILY",
  "desiredCount": 1,
  "launchType": "FARGATE",
  "networkConfiguration": {
    "awsvpcConfiguration": {
      "subnets": ["${SUBNET_ARRAY[0]}", "${SUBNET_ARRAY[1]}"],
      "securityGroups": ["$ECS_SG_ID"],
      "assignPublicIp": "ENABLED"
    }
  },
  "loadBalancers": [
    {
      "targetGroupArn": "$TG_ARN",
      "containerName": "$APP_NAME",
      "containerPort": 8082
    }
  ],
  "healthCheckGracePeriodSeconds": 300
}
EOF

aws ecs create-service --cli-input-json file://service-definition.json --region $REGION

# Get ALB DNS name
ALB_DNS=$(aws elbv2 describe-load-balancers --load-balancer-arns $ALB_ARN --query 'LoadBalancers[0].DNSName' --output text --region $REGION)

echo "✅ ECS Fargate deployment completed!"
echo ""
echo "📊 Deployment Summary:"
echo "   Cluster: $CLUSTER_NAME"
echo "   Service: $SERVICE_NAME"
echo "   Task Definition: $TASK_FAMILY"
echo "   Expected Cost: ~$47-65/month"
echo ""
echo "🌐 Your application will be available at:"
echo "   http://$ALB_DNS"
echo ""
echo "🔍 Monitor deployment:"
echo "   aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $REGION"
echo ""
echo "⏱️  Deployment typically takes 5-10 minutes"

# Cleanup temporary files
rm -f Dockerfile task-definition.json service-definition.json

echo "🎉 Deployment completed! Check AWS Console for detailed status."
