#!/bin/bash

# Requirements Validation Script for Document Management API
# Validates implementation against task requirements

echo "=== Document Management API Requirements Validation ==="

# Task Requirements:
# - Implement GET /documents endpoint for listing user documents with KB sync status
# - Create DELETE /documents/{id} endpoint with Knowledge Base cleanup
# - Add document processing status endpoint with ingestion job tracking
# - Implement proper error responses and validation
# - Deploy API endpoints and test document management operations
# - Requirements: US-005 (Document Management), US-005a (Document Viewing)

echo "Checking implementation files..."

# Check main Lambda function
if [ -f "src/index.ts" ]; then
    echo "✓ Main Lambda function exists"
    
    # Check for required endpoints
    if grep -q "GET.*documents" src/index.ts; then
        echo "✓ GET /documents endpoint implemented"
    else
        echo "✗ GET /documents endpoint missing"
    fi
    
    if grep -q "DELETE.*documents" src/index.ts; then
        echo "✓ DELETE /documents/{id} endpoint implemented"
    else
        echo "✗ DELETE /documents/{id} endpoint missing"
    fi
    
    if grep -q "documents/status" src/index.ts; then
        echo "✓ GET /documents/status endpoint implemented"
    else
        echo "✗ GET /documents/status endpoint missing"
    fi
    
    # Check Knowledge Base integration
    if grep -q "BedrockAgentClient" src/index.ts; then
        echo "✓ Bedrock Knowledge Base integration present"
    else
        echo "✗ Bedrock Knowledge Base integration missing"
    fi
    
    # Check error handling
    if grep -q "createErrorResponse" src/index.ts; then
        echo "✓ Error response handling implemented"
    else
        echo "✗ Error response handling missing"
    fi
    
    # Check authentication
    if grep -q "authorizer.*claims" src/index.ts; then
        echo "✓ Authentication validation implemented"
    else
        echo "✗ Authentication validation missing"
    fi
    
    # Check role-based access
    if grep -q "userRole.*admin" src/index.ts; then
        echo "✓ Role-based access control implemented"
    else
        echo "✗ Role-based access control missing"
    fi
    
else
    echo "✗ Main Lambda function missing"
fi

# Check tests
if [ -f "__tests__/index.test.ts" ]; then
    echo "✓ Unit tests exist"
    
    # Check test coverage
    if grep -q "GET /documents" __tests__/index.test.ts; then
        echo "✓ GET /documents tests present"
    else
        echo "✗ GET /documents tests missing"
    fi
    
    if grep -q "DELETE /documents" __tests__/index.test.ts; then
        echo "✓ DELETE /documents tests present"
    else
        echo "✗ DELETE /documents tests missing"
    fi
    
    if grep -q "documents/status" __tests__/index.test.ts; then
        echo "✓ Document status tests present"
    else
        echo "✗ Document status tests missing"
    fi
    
else
    echo "✗ Unit tests missing"
fi

# Check Terraform infrastructure
if [ -f "terraform/main.tf" ]; then
    echo "✓ Terraform infrastructure exists"
    
    # Check API Gateway integration
    if grep -q "aws_api_gateway_method" terraform/main.tf; then
        echo "✓ API Gateway methods configured"
    else
        echo "✗ API Gateway methods missing"
    fi
    
    # Check Lambda permissions
    if grep -q "aws_lambda_permission" terraform/main.tf; then
        echo "✓ Lambda permissions configured"
    else
        echo "✗ Lambda permissions missing"
    fi
    
    # Check CORS configuration
    if grep -q "OPTIONS" terraform/main.tf; then
        echo "✓ CORS configuration present"
    else
        echo "✗ CORS configuration missing"
    fi
    
else
    echo "✗ Terraform infrastructure missing"
fi

# Check deployment scripts
if [ -f "deploy.sh" ]; then
    echo "✓ Deployment script exists"
else
    echo "✗ Deployment script missing"
fi

if [ -f "integration-test.sh" ]; then
    echo "✓ Integration test script exists"
else
    echo "✗ Integration test script missing"
fi

# Check documentation
if [ -f "README.md" ]; then
    echo "✓ Documentation exists"
else
    echo "✗ Documentation missing"
fi

echo ""
echo "=== Requirements Mapping ==="
echo "US-005 (Document Management):"
echo "  - Document listing: GET /documents endpoint"
echo "  - Document deletion: DELETE /documents/{id} endpoint"
echo "  - Admin access: Role-based permissions"
echo "  - Knowledge Base cleanup: S3 and metadata deletion"
echo ""
echo "US-005a (Document Viewing):"
echo "  - Document metadata display: Comprehensive document records"
echo "  - Processing status: Knowledge Base sync status"
echo "  - Permission-based viewing: User vs admin access"
echo ""
echo "Additional Features:"
echo "  - Ingestion job tracking: Real-time Knowledge Base status"
echo "  - Error handling: Comprehensive error responses"
echo "  - Authentication: Cognito JWT validation"
echo "  - CORS support: Cross-origin request handling"
echo ""
echo "=== Validation Complete ==="