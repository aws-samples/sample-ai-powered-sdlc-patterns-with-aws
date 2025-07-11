#!/bin/bash

# AWS Lambda Deployment Script for Java 21 Application
# Cost: ~$2-10/month (serverless, pay per request)

echo "⚡ Deploying Java 21 App to AWS Lambda"
echo "======================================"

# Configuration
FUNCTION_NAME="java21-app-lambda"
REGION="us-east-1"
RUNTIME="java21"
HANDLER="com.example.java21app.LambdaHandler::handleRequest"
ROLE_NAME="java21-lambda-role"
API_NAME="java21-api"

echo "📋 Configuration:"
echo "   Function Name: $FUNCTION_NAME"
echo "   Region: $REGION"
echo "   Runtime: $RUNTIME"

# Check prerequisites
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "🏗️  Step 1: Preparing Lambda-compatible application..."
cd ../java21-app

# Add Lambda dependencies to pom.xml
echo "📦 Adding Lambda dependencies..."
cat > lambda-dependencies.xml << EOF
        <!-- AWS Lambda Dependencies -->
        <dependency>
            <groupId>com.amazonaws</groupId>
            <artifactId>aws-lambda-java-core</artifactId>
            <version>1.2.3</version>
        </dependency>
        <dependency>
            <groupId>com.amazonaws</groupId>
            <artifactId>aws-lambda-java-events</artifactId>
            <version>3.11.4</version>
        </dependency>
        <dependency>
            <groupId>com.amazonaws</groupId>
            <artifactId>aws-lambda-java-log4j2</artifactId>
            <version>1.6.0</version>
        </dependency>
EOF

# Create Lambda Handler
mkdir -p src/main/java/com/example/java21app/lambda
cat > src/main/java/com/example/java21app/lambda/LambdaHandler.java << 'EOF'
package com.example.java21app.lambda;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import com.amazonaws.services.lambda.runtime.events.APIGatewayProxyRequestEvent;
import com.amazonaws.services.lambda.runtime.events.APIGatewayProxyResponseEvent;
import com.example.java21app.model.Product;
import com.example.java21app.service.ProductService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.boot.SpringApplication;
import org.springframework.context.ConfigurableApplicationContext;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class LambdaHandler implements RequestHandler<APIGatewayProxyRequestEvent, APIGatewayProxyResponseEvent> {
    
    private static ConfigurableApplicationContext applicationContext;
    private static ProductService productService;
    private static ObjectMapper objectMapper = new ObjectMapper();
    
    static {
        // Initialize Spring Boot context
        System.setProperty("spring.main.web-application-type", "none");
        applicationContext = SpringApplication.run(com.example.java21app.Java21Application.class);
        productService = applicationContext.getBean(ProductService.class);
    }
    
    @Override
    public APIGatewayProxyResponseEvent handleRequest(APIGatewayProxyRequestEvent input, Context context) {
        try {
            String path = input.getPath();
            String httpMethod = input.getHttpMethod();
            
            APIGatewayProxyResponseEvent response = new APIGatewayProxyResponseEvent();
            Map<String, String> headers = new HashMap<>();
            headers.put("Content-Type", "application/json");
            headers.put("Access-Control-Allow-Origin", "*");
            response.setHeaders(headers);
            
            switch (httpMethod) {
                case "GET":
                    if (path.equals("/products") || path.equals("/")) {
                        List<Product> products = productService.getAllProducts();
                        response.setStatusCode(200);
                        response.setBody(objectMapper.writeValueAsString(products));
                    } else if (path.equals("/products/available")) {
                        List<Product> availableProducts = productService.getAvailableProducts();
                        response.setStatusCode(200);
                        response.setBody(objectMapper.writeValueAsString(availableProducts));
                    } else if (path.equals("/products/sorted")) {
                        List<Product> sortedProducts = productService.getSortedProductsByPrice();
                        response.setStatusCode(200);
                        response.setBody(objectMapper.writeValueAsString(sortedProducts));
                    } else {
                        response.setStatusCode(404);
                        response.setBody("{\"error\":\"Not Found\"}");
                    }
                    break;
                    
                case "POST":
                    if (path.equals("/products")) {
                        Product newProduct = objectMapper.readValue(input.getBody(), Product.class);
                        Product savedProduct = productService.saveProduct(newProduct);
                        response.setStatusCode(201);
                        response.setBody(objectMapper.writeValueAsString(savedProduct));
                    } else {
                        response.setStatusCode(404);
                        response.setBody("{\"error\":\"Not Found\"}");
                    }
                    break;
                    
                default:
                    response.setStatusCode(405);
                    response.setBody("{\"error\":\"Method Not Allowed\"}");
            }
            
            return response;
            
        } catch (Exception e) {
            context.getLogger().log("Error: " + e.getMessage());
            APIGatewayProxyResponseEvent errorResponse = new APIGatewayProxyResponseEvent();
            errorResponse.setStatusCode(500);
            errorResponse.setBody("{\"error\":\"Internal Server Error\"}");
            return errorResponse;
        }
    }
}
EOF

echo "🔧 Step 2: Building Lambda deployment package..."
./mvnw clean package -DskipTests

if [ $? -ne 0 ]; then
    echo "❌ Build failed!"
    exit 1
fi

echo "✅ Application built successfully!"

echo "🔐 Step 3: Creating IAM role for Lambda..."
# Create trust policy
cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create IAM role
ROLE_ARN=$(aws iam create-role \
    --role-name $ROLE_NAME \
    --assume-role-policy-document file://trust-policy.json \
    --query 'Role.Arn' --output text 2>/dev/null || \
    aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)

# Attach basic execution policy
aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

echo "⚡ Step 4: Creating Lambda function..."
# Create deployment package
cp target/java21-app-0.0.1-SNAPSHOT.jar deployment-package.jar

# Create Lambda function
aws lambda create-function \
    --function-name $FUNCTION_NAME \
    --runtime $RUNTIME \
    --role $ROLE_ARN \
    --handler $HANDLER \
    --zip-file fileb://deployment-package.jar \
    --timeout 30 \
    --memory-size 512 \
    --environment Variables='{SPRING_PROFILES_ACTIVE=lambda}' \
    --region $REGION 2>/dev/null || \
    aws lambda update-function-code \
    --function-name $FUNCTION_NAME \
    --zip-file fileb://deployment-package.jar \
    --region $REGION

echo "🌐 Step 5: Creating API Gateway..."
# Create REST API
API_ID=$(aws apigateway create-rest-api \
    --name $API_NAME \
    --description "API for Java 21 Lambda function" \
    --region $REGION \
    --query 'id' --output text 2>/dev/null || \
    aws apigateway get-rest-apis \
    --query "items[?name=='$API_NAME'].id" --output text --region $REGION)

# Get root resource ID
ROOT_RESOURCE_ID=$(aws apigateway get-resources \
    --rest-api-id $API_ID \
    --region $REGION \
    --query 'items[?path==`/`].id' --output text)

# Create proxy resource
PROXY_RESOURCE_ID=$(aws apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $ROOT_RESOURCE_ID \
    --path-part '{proxy+}' \
    --region $REGION \
    --query 'id' --output text 2>/dev/null || \
    aws apigateway get-resources \
    --rest-api-id $API_ID \
    --region $REGION \
    --query "items[?pathPart=='{proxy+}'].id" --output text)

# Create ANY method
aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $PROXY_RESOURCE_ID \
    --http-method ANY \
    --authorization-type NONE \
    --region $REGION 2>/dev/null || echo "Method already exists"

# Set up integration
LAMBDA_ARN="arn:aws:lambda:$REGION:$ACCOUNT_ID:function:$FUNCTION_NAME"
aws apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $PROXY_RESOURCE_ID \
    --http-method ANY \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri "arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/$LAMBDA_ARN/invocations" \
    --region $REGION

# Add permission for API Gateway to invoke Lambda
aws lambda add-permission \
    --function-name $FUNCTION_NAME \
    --statement-id api-gateway-invoke \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:$REGION:$ACCOUNT_ID:$API_ID/*/*" \
    --region $REGION 2>/dev/null || echo "Permission already exists"

# Deploy API
aws apigateway create-deployment \
    --rest-api-id $API_ID \
    --stage-name prod \
    --region $REGION

# Get API endpoint
API_ENDPOINT="https://$API_ID.execute-api.$REGION.amazonaws.com/prod"

echo "✅ Lambda deployment completed!"
echo ""
echo "📊 Deployment Summary:"
echo "   Function Name: $FUNCTION_NAME"
echo "   Runtime: $RUNTIME"
echo "   Memory: 512 MB"
echo "   Timeout: 30 seconds"
echo "   Expected Cost: ~$2-10/month (pay per request)"
echo ""
echo "🌐 Your API is available at:"
echo "   $API_ENDPOINT"
echo ""
echo "🔍 Test endpoints:"
echo "   GET  $API_ENDPOINT/products"
echo "   GET  $API_ENDPOINT/products/available"
echo "   GET  $API_ENDPOINT/products/sorted"
echo "   POST $API_ENDPOINT/products"
echo ""
echo "📈 Monitor function:"
echo "   aws lambda get-function --function-name $FUNCTION_NAME --region $REGION"
echo ""
echo "💰 Cost Benefits:"
echo "   • No charges when not in use"
echo "   • Pay only for requests and compute time"
echo "   • First 1M requests per month are free"
echo "   • First 400,000 GB-seconds of compute time are free"

# Cleanup temporary files
rm -f trust-policy.json deployment-package.jar lambda-dependencies.xml

echo "🎉 Serverless deployment completed!"
