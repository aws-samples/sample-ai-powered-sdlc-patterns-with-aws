#!/bin/bash

# AWS App Runner Deployment Script for Java 21 Application
# Cost: ~$25-51/month

echo "🚀 Deploying Java 21 App to AWS App Runner"
echo "=========================================="

# Configuration
APP_NAME="java21-modernized-app"
SERVICE_NAME="java21-app-service"
REGION="us-east-1"
GITHUB_REPO="your-username/java21-app"  # Update this
GITHUB_BRANCH="main"

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

echo "📦 Building application..."
cd ../java21-app
./mvnw clean package -DskipTests

if [ $? -ne 0 ]; then
    echo "❌ Build failed!"
    exit 1
fi

echo "✅ Build successful!"

# Create apprunner.yaml configuration
cat > apprunner.yaml << EOF
version: 1.0
runtime: java21
build:
  commands:
    build:
      - echo "Building Java 21 application with Maven"
      - ./mvnw clean package -DskipTests
run:
  runtime-version: 21
  command: java -Dserver.port=8080 -jar target/java21-app-0.0.1-SNAPSHOT.jar
  network:
    port: 8080
    env: PORT
  env:
    - name: SPRING_PROFILES_ACTIVE
      value: production
    - name: SERVER_PORT
      value: 8080
EOF

echo "📝 Created apprunner.yaml configuration"

# Create App Runner service configuration
cat > app-runner-config.json << EOF
{
  "ServiceName": "$SERVICE_NAME",
  "SourceConfiguration": {
    "AutoDeploymentsEnabled": true,
    "CodeRepository": {
      "RepositoryUrl": "https://github.com/$GITHUB_REPO",
      "SourceCodeVersion": {
        "Type": "BRANCH",
        "Value": "$GITHUB_BRANCH"
      },
      "CodeConfiguration": {
        "ConfigurationSource": "REPOSITORY",
        "CodeConfigurationValues": {
          "Runtime": "JAVA_21",
          "BuildCommand": "./mvnw clean package -DskipTests",
          "StartCommand": "java -Dserver.port=8080 -jar target/java21-app-0.0.1-SNAPSHOT.jar",
          "RuntimeEnvironmentVariables": {
            "SPRING_PROFILES_ACTIVE": "production",
            "SERVER_PORT": "8080"
          }
        }
      }
    }
  },
  "InstanceConfiguration": {
    "Cpu": "1 vCPU",
    "Memory": "2 GB"
  },
  "AutoScalingConfigurationArn": "",
  "HealthCheckConfiguration": {
    "Protocol": "HTTP",
    "Path": "/actuator/health",
    "Interval": 10,
    "Timeout": 5,
    "HealthyThreshold": 1,
    "UnhealthyThreshold": 5
  }
}
EOF

echo "🔧 Creating App Runner service..."

# Create the App Runner service
aws apprunner create-service \
    --cli-input-json file://app-runner-config.json \
    --region $REGION

if [ $? -eq 0 ]; then
    echo "✅ App Runner service created successfully!"
    echo ""
    echo "📊 Service Details:"
    echo "   Service Name: $SERVICE_NAME"
    echo "   Region: $REGION"
    echo "   Expected Cost: ~$25-51/month"
    echo ""
    echo "🔍 To check service status:"
    echo "   aws apprunner describe-service --service-arn <service-arn> --region $REGION"
    echo ""
    echo "🌐 Your application will be available at:"
    echo "   https://<random-id>.us-east-1.awsapprunner.com"
    echo ""
    echo "⏱️  Deployment typically takes 5-10 minutes"
else
    echo "❌ Failed to create App Runner service"
    exit 1
fi

# Cleanup temporary files
rm -f app-runner-config.json apprunner.yaml

echo "🎉 Deployment initiated! Check AWS Console for progress."
