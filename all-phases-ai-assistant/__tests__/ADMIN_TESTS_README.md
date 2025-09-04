# Admin Dashboard and Features E2E Tests

## Overview

This directory contains comprehensive end-to-end tests for admin dashboard functionality and admin-specific features using Playwright MCP Server. These tests validate admin functionality against the deployed AWS infrastructure without any mocking or simulation.

## Requirements Coverage

These tests implement **Task 13** from the CORS API Gateway Fix specification:

- **8.4**: Playwright MCP testing for admin-specific features
- **7.4**: Admin access to /dashboard functionality  
- **7.5**: Admin access to admin-specific features
- **7.6**: Admin functionality works without CORS errors

## Test Files

### 1. `admin-dashboard-e2e.playwright.mcp.test.ts`
Tests core admin dashboard functionality:
- Admin dashboard access and loading
- Knowledge Base management features
- Admin metrics and analytics
- Admin quick actions
- Dashboard responsive design
- Real-time updates
- Error handling

### 2. `admin-features-e2e.playwright.mcp.test.ts`
Tests admin-specific features:
- Admin user management
- Admin Knowledge Base management
- Admin system settings and configuration
- Admin navigation structure
- Admin permissions and role-based access
- Admin monitoring and alerts
- Admin data export and reporting

### 3. `admin-comprehensive-e2e.playwright.mcp.test.ts`
Comprehensive admin testing including:
- Complete admin workflow end-to-end
- CORS validation for all admin features
- Admin access to all application areas
- Integration of dashboard and features testing

### 4. `run-admin-tests.ts`
Test runner that executes all admin test suites in sequence and provides comprehensive reporting.

## Test Execution

### Run All Admin Tests
```bash
npm run test:admin
```

### Run Individual Test Suites
```bash
# Admin Dashboard Tests
npm run test:admin:dashboard

# Admin Features Tests  
npm run test:admin:features

# Comprehensive Admin Tests
npm run test:admin:comprehensive
```

### Run as Part of Complete E2E Suite
```bash
npm run test:e2e
```

## Test Architecture

### Playwright MCP Server Only
- **NO Jest framework** - Pure MCP server implementation
- **NO Playwright test framework** - Uses MCP browser automation tools
- **NO mocking or stubbing** - Tests against real AWS infrastructure

### MCP Tools Used
- `mcp_playwright_browser_navigate` - Page navigation
- `mcp_playwright_browser_click` - Element interaction
- `mcp_playwright_browser_type` - Text input
- `mcp_playwright_browser_fill_form` - Form completion
- `mcp_playwright_browser_snapshot` - Page state capture
- `mcp_playwright_browser_wait_for` - Timing control
- `mcp_playwright_browser_console_messages` - CORS error detection
- `mcp_playwright_browser_evaluate` - JavaScript execution
- `mcp_playwright_browser_take_screenshot` - Debug screenshots
- `mcp_playwright_browser_resize` - Responsive testing

## Admin Test Scenarios

### Authentication
- Admin user login with elevated permissions
- Admin role validation in UI
- Admin access control verification

### Dashboard Functionality
- Admin dashboard loading and display
- Knowledge Base status monitoring
- Ingestion jobs management
- System metrics and analytics
- Quick actions panel
- Real-time updates and refresh

### Admin Features
- User management interface
- Knowledge Base administration
- System settings and configuration
- Navigation between admin sections
- Monitoring and alerting
- Data export and reporting

### CORS Validation
- Comprehensive CORS error detection
- API endpoint CORS compliance
- Cross-origin request validation
- Preflight request handling

### Application Access
- Admin access to all user areas (/chat, /documents, etc.)
- Admin-specific route access (/admin/*)
- Permission-based UI element display
- Role-based functionality availability

## AWS Services Tested

### Real AWS Integration
- **Cognito User Pool**: Admin authentication and role management
- **API Gateway**: Admin API endpoints and CORS configuration
- **Lambda Functions**: Admin-specific Lambda functions
- **Bedrock Knowledge Base**: Admin KB management and monitoring
- **DynamoDB**: Admin data access and management
- **S3**: Admin document management
- **CloudWatch**: Admin metrics and monitoring
- **CloudFront**: Admin interface delivery

### No Simulation
- All tests run against deployed AWS infrastructure
- Real API calls to AWS services
- Actual authentication with Cognito
- Live Knowledge Base operations
- Real-time metrics from CloudWatch

## Test Results and Reporting

### Comprehensive Reporting
- Individual test suite results
- Overall pass/fail statistics
- Detailed error reporting with screenshots
- CORS compliance validation results
- Performance timing information

### Debug Information
- Automatic screenshot capture on failures
- Console message analysis for CORS errors
- Network request monitoring
- Browser state snapshots

### Requirements Validation
- Explicit mapping to specification requirements
- Coverage verification for each requirement
- Detailed validation of admin functionality

## Admin User Configuration

### Test Credentials
Tests use admin credentials configured in Cognito:
- Email: `admin@example.com`
- Password: `AdminPassword123!`

### Required Setup
- Admin user must exist in Cognito User Pool
- Admin user must have appropriate role/permissions
- Admin user must have access to all admin routes

## Troubleshooting

### Common Issues
1. **Admin Authentication Failure**: Verify admin user exists in Cognito
2. **CORS Errors**: Check API Gateway CORS configuration
3. **Access Denied**: Verify admin role permissions
4. **Page Not Found**: Ensure admin routes are properly configured

### Debug Steps
1. Check screenshot files for visual debugging
2. Review console messages for CORS errors
3. Verify admin user permissions in Cognito
4. Test individual admin routes manually

## Integration with CI/CD

### Automated Testing
- Tests can be integrated into CI/CD pipelines
- Exit codes indicate pass/fail status
- Comprehensive reporting for build systems
- Screenshot artifacts for debugging

### Environment Requirements
- Access to deployed AWS infrastructure
- Valid admin credentials
- Network access to CloudFront distribution
- Playwright browser dependencies

## Future Enhancements

### Potential Additions
- Admin audit log testing
- Admin backup/restore functionality testing
- Admin security settings validation
- Admin performance optimization testing
- Admin mobile responsiveness testing

### Scalability
- Additional admin user roles testing
- Multi-tenant admin functionality
- Admin API rate limiting testing
- Admin bulk operations testing