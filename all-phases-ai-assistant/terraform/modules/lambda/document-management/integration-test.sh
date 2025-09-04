#!/bin/bash

# Document Management API Integration Tests
# Tests against deployed AWS infrastructure following TDD principles

set -e

# Configuration
API_BASE_URL="https://your-api-gateway-url.execute-api.us-west-2.amazonaws.com/dev"
TEST_USER_TOKEN="your-test-user-jwt-token"
ADMIN_USER_TOKEN="your-admin-user-jwt-token"

echo "=== Document Management API Integration Tests ==="
echo "Testing against deployed AWS infrastructure"
echo "API Base URL: $API_BASE_URL"

# Test 1: GET /documents - List user documents
echo "Test 1: GET /documents - List user documents"
curl -X GET "$API_BASE_URL/documents" \
  -H "Authorization: Bearer $TEST_USER_TOKEN" \
  -H "Content-Type: application/json" \
  -w "\nStatus: %{http_code}\n" || echo "Test 1 failed"

# Test 2: GET /documents (Admin) - List all documents
echo "Test 2: GET /documents (Admin) - List all documents"
curl -X GET "$API_BASE_URL/documents" \
  -H "Authorization: Bearer $ADMIN_USER_TOKEN" \
  -H "Content-Type: application/json" \
  -w "\nStatus: %{http_code}\n" || echo "Test 2 failed"

# Test 3: GET /documents/status - Document processing status
echo "Test 3: GET /documents/status - Document processing status"
curl -X GET "$API_BASE_URL/documents/status" \
  -H "Authorization: Bearer $TEST_USER_TOKEN" \
  -H "Content-Type: application/json" \
  -w "\nStatus: %{http_code}\n" || echo "Test 3 failed"

# Test 4: DELETE /documents/{id} - Delete document (should fail for non-existent)
echo "Test 4: DELETE /documents/non-existent - Delete non-existent document"
curl -X DELETE "$API_BASE_URL/documents/non-existent" \
  -H "Authorization: Bearer $TEST_USER_TOKEN" \
  -H "Content-Type: application/json" \
  -w "\nStatus: %{http_code}\n" || echo "Test 4 failed"

# Test 5: Unauthorized request
echo "Test 5: Unauthorized request"
curl -X GET "$API_BASE_URL/documents" \
  -H "Content-Type: application/json" \
  -w "\nStatus: %{http_code}\n" || echo "Test 5 failed"

# Test 6: CORS preflight request
echo "Test 6: CORS preflight request"
curl -X OPTIONS "$API_BASE_URL/documents" \
  -H "Origin: https://example.com" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Authorization" \
  -w "\nStatus: %{http_code}\n" || echo "Test 6 failed"

echo "=== Integration Tests Completed ==="
echo "Review the responses above to verify:"
echo "1. Authentication is working correctly"
echo "2. Role-based access control is enforced"
echo "3. CORS headers are properly configured"
echo "4. Error responses are appropriate"
echo "5. Knowledge Base sync status is included"