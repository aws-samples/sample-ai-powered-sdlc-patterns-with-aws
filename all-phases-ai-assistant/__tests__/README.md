# End-to-End Tests using Playwright MCP Server

This directory contains comprehensive end-to-end tests for the AI Assistant application using **ONLY** Playwright MCP server tools. These tests validate the complete application workflow against deployed AWS infrastructure.

## 🚨 CRITICAL REQUIREMENTS

- **NO Jest Framework**: Tests use ONLY Playwright MCP server tools
- **NO Playwright Test Framework**: Pure MCP server implementation
- **Real AWS Infrastructure**: All tests run against deployed services
- **NO Mocking**: Tests validate actual AWS service integration
- **Deployed CloudFront URL**: Tests run against https://diaxl2ky359mj.cloudfront.net

## 📋 Test Suites

### 1. Comprehensive E2E Tests (`comprehensive-e2e-tests.playwright.test.ts`)
Complete end-to-end validation covering all user workflows:
- Authentication flows with real Cognito
- Document upload and Knowledge Base integration
- Chat interface with real Bedrock
- Admin dashboard functionality
- Performance validation
- Error handling and resilience
- Responsive design and accessibility

### 2. Authentication E2E Tests (`authentication-e2e.playwright.test.ts`)
Focused authentication and authorization testing:
- Authentication interface validation
- Login form validation
- Authentication error handling
- Role-based access control
- Session management
- Logout functionality
- Security measures

### 3. Performance E2E Tests (`performance-e2e.playwright.test.ts`)
Performance requirements validation:
- CloudFront page load performance (< 10 seconds)
- Knowledge Base query response times (< 20 seconds)
- Chat interface responsiveness (< 3 seconds)
- Document upload interface load (< 5 seconds)
- Admin dashboard load (< 8 seconds)
- Concurrent users simulation
- Network latency and resilience

## 🚀 Running Tests

### Run All E2E Tests
```bash
npm run test:e2e
```

### Run Individual Test Suites
```bash
# Comprehensive E2E Tests
npm run test:e2e:comprehensive

# Authentication E2E Tests
npm run test:e2e:auth

# Performance E2E Tests
npm run test:e2e:performance
```

### Direct Execution
```bash
# Run all tests
npx ts-node __tests__/run-e2e-tests.ts

# Run specific test file
npx ts-node __tests__/comprehensive-e2e-tests.playwright.test.ts
```

## 🏗️ Test Architecture

### Playwright MCP Server Tools Used
- `mcp_playwright_browser_install()` - Browser installation
- `mcp_playwright_browser_navigate()` - Page navigation
- `mcp_playwright_browser_snapshot()` - Page content analysis
- `mcp_playwright_browser_type()` - Text input
- `mcp_playwright_browser_click()` - Element interaction
- `mcp_playwright_browser_press_key()` - Keyboard input
- `mcp_playwright_browser_wait_for()` - Timing control
- `mcp_playwright_browser_take_screenshot()` - Visual debugging
- `mcp_playwright_browser_resize()` - Responsive testing
- `mcp_playwright_browser_tab_*()` - Multi-tab testing
- `mcp_playwright_browser_evaluate()` - JavaScript execution
- `mcp_playwright_browser_close()` - Cleanup

### Test Structure
Each test suite follows this pattern:
1. **Setup**: Browser installation and navigation
2. **Test Execution**: Individual test functions using MCP tools
3. **Validation**: Snapshot analysis and assertion logic
4. **Cleanup**: Screenshot capture and browser closure
5. **Reporting**: Detailed console output with results

## 📊 Requirements Coverage

### User Stories Validated
- **US-001**: User Authentication and Role Management
- **US-002**: System Infrastructure and Deployment
- **US-003**: Document Upload
- **US-004**: Document Processing
- **US-005**: Administrative Document Management
- **US-006**: Basic Question Interface
- **US-007**: AI Response Generation
- **US-008**: Conversation History
- **US-009**: Main Chat Interface
- **US-010**: Document Upload Interface

### AWS Services Tested
- **Amazon Cognito**: User authentication and authorization
- **API Gateway**: REST API endpoints and CORS
- **AWS Lambda**: Serverless function execution
- **Amazon Bedrock**: Knowledge Base RetrieveAndGenerate API
- **Amazon S3**: Document storage and retrieval
- **Amazon DynamoDB**: Data persistence
- **Amazon CloudFront**: Content delivery
- **Amazon OpenSearch Serverless**: Vector search
- **Amazon CloudWatch**: Metrics and monitoring

## 🔧 Test Configuration

### Environment Variables
Tests automatically use the deployed CloudFront URL:
```typescript
const DEPLOYED_APP_URL = 'https://diaxl2ky359mj.cloudfront.net';
```

### Performance Thresholds
```typescript
const PERFORMANCE_THRESHOLDS = {
  PAGE_LOAD: 10000,        // 10 seconds
  KNOWLEDGE_BASE_QUERY: 20000,  // 20 seconds
  CHAT_RESPONSE: 3000,     // 3 seconds
  DOCUMENT_UPLOAD_LOAD: 5000,   // 5 seconds
  ADMIN_DASHBOARD_LOAD: 8000    // 8 seconds
};
```

### Browser Configuration
- Automatic browser installation via MCP
- Screenshot capture for debugging
- Full page snapshots for content analysis
- Multi-viewport testing (desktop, tablet, mobile)

## 📸 Debugging

### Screenshots
Tests automatically capture screenshots on failure:
- Location: Current working directory
- Naming: `{test-type}-failure-{timestamp}.png`
- Full page screenshots for complete context

### Console Output
Detailed logging includes:
- Test progress indicators
- Performance measurements
- Validation results
- Error messages with context
- Success confirmations

### Snapshot Analysis
Page snapshots are analyzed for:
- Element presence validation
- Content verification
- State confirmation
- Error detection

## 🎯 Success Criteria

### Test Completion
- All test suites execute without errors
- Browser installation and cleanup successful
- Screenshots captured for debugging
- Detailed results reporting

### Functional Validation
- Authentication flows working with real Cognito
- Document upload and Knowledge Base integration verified
- Chat interface working with real Bedrock
- Admin dashboard functionality confirmed
- Role-based access control functioning
- Error handling and resilience verified

### Performance Validation
- Page load times within thresholds
- Knowledge Base query response acceptable
- Chat interface responsiveness verified
- Concurrent user simulation successful
- Network resilience confirmed

## 🚨 Troubleshooting

### Common Issues
1. **Browser Installation Failure**: Ensure network connectivity
2. **Page Load Timeout**: Check CloudFront URL accessibility
3. **Element Not Found**: Verify application deployment status
4. **Authentication Issues**: Confirm Cognito configuration
5. **Performance Threshold Exceeded**: Check AWS service health

### Debug Steps
1. Check console output for detailed error messages
2. Review captured screenshots for visual debugging
3. Verify deployed application accessibility
4. Confirm AWS service availability
5. Check network connectivity and latency

### Support
For issues with E2E tests:
1. Review test output logs
2. Check captured screenshots
3. Verify AWS service deployment status
4. Confirm application functionality manually
5. Check MCP server tool availability

## 📝 Test Maintenance

### Adding New Tests
1. Create test functions using MCP tools only
2. Follow existing naming conventions
3. Include proper error handling
4. Add screenshot capture on failure
5. Update this README with new test descriptions

### Updating Thresholds
Performance thresholds can be adjusted in individual test files:
```typescript
const PERFORMANCE_THRESHOLDS = {
  // Update values as needed
};
```

### Extending Coverage
To add new test scenarios:
1. Identify user workflow or requirement
2. Create test function using MCP tools
3. Add validation logic with snapshots
4. Include in appropriate test suite
5. Update requirements coverage documentation

---

**Note**: These tests are designed to validate the complete AI Assistant application against real AWS infrastructure using only Playwright MCP server tools. No mocking, stubbing, or simulation is used - all tests interact with actual deployed services.