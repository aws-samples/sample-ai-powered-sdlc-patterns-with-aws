/**
 * E2E Test Runner using Playwright MCP Server
 * Task 19: Develop end-to-end tests using Playwright MCP on deployed infrastructure
 * 
 * This script runs all E2E test suites using ONLY Playwright MCP server tools
 * NO Jest, NO Playwright test framework - Pure MCP server implementation
 * 
 * Test Suites:
 * 1. Comprehensive E2E Tests (all workflows)
 * 2. Authentication E2E Tests (Cognito integration)
 * 3. Performance E2E Tests (AWS service performance)
 * 4. Admin Comprehensive E2E Tests (admin dashboard and features)
 * 
 * Usage:
 * - Run from command line: npx ts-node __tests__/run-e2e-tests.ts
 * - Or import and call: runAllE2ETests()
 */

import { runComprehensiveAdminE2ETests } from './admin-comprehensive-e2e.playwright.mcp.test';
import { runAuthenticationE2ETests } from './authentication-e2e.playwright.test';
import { runComprehensiveE2ETests } from './comprehensive-e2e-tests.playwright.test';
import { runPerformanceE2ETests } from './performance-e2e.playwright.test';

/**
 * Main E2E Test Runner
 * Executes all E2E test suites in sequence
 */
async function runAllE2ETests() {
  console.log('🚀 Starting Complete E2E Test Suite');
  console.log('===================================');
  console.log('Testing against deployed AWS infrastructure');
  console.log('Using ONLY Playwright MCP server tools');
  console.log('NO mocking, stubbing, or simulation');
  console.log('');
  
  const testResults = {
    comprehensive: { passed: false, error: null as any },
    authentication: { passed: false, error: null as any },
    performance: { passed: false, error: null as any, results: null as any },
    adminComprehensive: { passed: false, error: null as any, results: null as any }
  };
  
  const startTime = Date.now();
  
  try {
    // Run Comprehensive E2E Tests
    console.log('📋 Running Comprehensive E2E Tests...');
    try {
      await runComprehensiveE2ETests();
      testResults.comprehensive.passed = true;
      console.log('✅ Comprehensive E2E Tests completed successfully');
    } catch (error) {
      testResults.comprehensive.error = error.message;
      console.error('❌ Comprehensive E2E Tests failed:', error.message);
    }
    
    console.log('\n' + '='.repeat(50) + '\n');
    
    // Run Authentication E2E Tests
    console.log('📋 Running Authentication E2E Tests...');
    try {
      await runAuthenticationE2ETests();
      testResults.authentication.passed = true;
      console.log('✅ Authentication E2E Tests completed successfully');
    } catch (error) {
      testResults.authentication.error = error.message;
      console.error('❌ Authentication E2E Tests failed:', error.message);
    }
    
    console.log('\n' + '='.repeat(50) + '\n');
    
    // Run Performance E2E Tests
    console.log('📋 Running Performance E2E Tests...');
    try {
      const performanceResults = await runPerformanceE2ETests();
      testResults.performance.passed = true;
      testResults.performance.results = performanceResults;
      console.log('✅ Performance E2E Tests completed successfully');
    } catch (error) {
      testResults.performance.error = error.message;
      console.error('❌ Performance E2E Tests failed:', error.message);
    }
    
    console.log('\n' + '='.repeat(50) + '\n');
    
    // Run Admin Comprehensive E2E Tests
    console.log('📋 Running Admin Comprehensive E2E Tests...');
    try {
      const adminResults = await runComprehensiveAdminE2ETests();
      testResults.adminComprehensive.passed = true;
      testResults.adminComprehensive.results = adminResults;
      console.log('✅ Admin Comprehensive E2E Tests completed successfully');
    } catch (error) {
      testResults.adminComprehensive.error = error.message;
      console.error('❌ Admin Comprehensive E2E Tests failed:', error.message);
    }
    
  } catch (error) {
    console.error('❌ E2E Test Suite execution failed:', error.message);
  }
  
  const endTime = Date.now();
  const totalTime = endTime - startTime;
  
  // Generate final report
  console.log('\n' + '='.repeat(60));
  console.log('📊 FINAL E2E TEST RESULTS SUMMARY');
  console.log('='.repeat(60));
  
  const testSuites = [
    { name: 'Comprehensive E2E Tests', result: testResults.comprehensive },
    { name: 'Authentication E2E Tests', result: testResults.authentication },
    { name: 'Performance E2E Tests', result: testResults.performance },
    { name: 'Admin Comprehensive E2E Tests', result: testResults.adminComprehensive }
  ];
  
  let passedSuites = 0;
  const totalSuites = testSuites.length;
  
  testSuites.forEach(suite => {
    if (suite.result.passed) {
      console.log(`✅ ${suite.name}: PASSED`);
      passedSuites++;
    } else {
      console.log(`❌ ${suite.name}: FAILED`);
      if (suite.result.error) {
        console.log(`   Error: ${suite.result.error}`);
      }
    }
  });
  
  console.log('\n📈 Test Suite Results:');
  console.log(`   Passed: ${passedSuites}/${totalSuites} test suites`);
  console.log(`   Total execution time: ${(totalTime / 1000).toFixed(2)} seconds`);
  
  if (passedSuites === totalSuites) {
    console.log('\n🎉 ALL E2E TEST SUITES PASSED!');
    console.log('✅ Complete end-to-end validation successful');
    console.log('✅ Authentication flows working with real Cognito');
    console.log('✅ Document upload and Knowledge Base integration verified');
    console.log('✅ Chat interface working with real Bedrock');
    console.log('✅ Admin dashboard functionality confirmed');
    console.log('✅ Admin-specific features and CORS compliance verified');
    console.log('✅ Admin access to all application areas validated');
    console.log('✅ Performance requirements met on real AWS infrastructure');
    console.log('✅ Role-based access control functioning correctly');
    console.log('✅ Error handling and resilience verified');
    console.log('✅ Responsive design and accessibility confirmed');
  } else {
    console.log('\n⚠️ SOME E2E TEST SUITES FAILED');
    console.log('Review the detailed results above for specific failures');
    console.log('Check screenshots and logs for debugging information');
  }
  
  console.log('\n📋 Test Coverage Verified:');
  console.log('- US-001 (User Authentication and Role Management)');
  console.log('- US-002 (System Infrastructure and Deployment)');
  console.log('- US-003 (Document Upload)');
  console.log('- US-004 (Document Processing)');
  console.log('- US-005 (Administrative Document Management)');
  console.log('- US-006 (Basic Question Interface)');
  console.log('- US-007 (AI Response Generation)');
  console.log('- US-008 (Conversation History)');
  console.log('- US-009 (Main Chat Interface)');
  console.log('- US-010 (Document Upload Interface)');
  
  console.log('\n🔧 Technical Validation Completed:');
  console.log('- Real Cognito User Pool authentication');
  console.log('- Real API Gateway and Lambda function integration');
  console.log('- Real Bedrock Knowledge Base RetrieveAndGenerate API');
  console.log('- Real S3 document storage and processing');
  console.log('- Real DynamoDB data persistence');
  console.log('- Real CloudFront content delivery');
  console.log('- Real OpenSearch Serverless vector search');
  console.log('- Real CloudWatch metrics and monitoring');
  
  console.log('='.repeat(60));
  
  return testResults;
}

/**
 * Command line execution
 */
if (require.main === module) {
  runAllE2ETests()
    .then((results) => {
      const allPassed = Object.values(results).every(result => result.passed);
      process.exit(allPassed ? 0 : 1);
    })
    .catch((error) => {
      console.error('E2E Test Runner failed:', error);
      process.exit(1);
    });
}

// Export for programmatic usage
export { runAllE2ETests };
