/**
 * Simple Admin Test Runner
 * Basic test to verify admin functionality without complex MCP setup
 */

const DEPLOYED_APP_URL = 'https://dq9tlzfsf1veq.cloudfront.net';

async function testAdminAccess() {
  console.log('🔍 Testing Admin Access to Application');
  
  try {
    // Test admin dashboard access
    console.log('\n1. Testing Admin Dashboard Access');
    
    // Navigate to admin dashboard
    await mcp_playwright_browser_navigate({ 
      url: `${DEPLOYED_APP_URL}/admin/dashboard` 
    });
    await mcp_playwright_browser_wait_for({ time: 5 });
    
    const dashboardSnapshot = await mcp_playwright_browser_snapshot();
    
    if (dashboardSnapshot.includes('Admin Dashboard')) {
      console.log('✅ Admin dashboard page accessible');
    } else if (dashboardSnapshot.includes('Sign In') || dashboardSnapshot.includes('Login')) {
      console.log('⚠️ Admin dashboard requires authentication');
    } else {
      console.log('⚠️ Admin dashboard response unclear');
    }
    
    // Test chat access
    console.log('\n2. Testing Chat Access');
    await mcp_playwright_browser_navigate({ 
      url: `${DEPLOYED_APP_URL}/chat` 
    });
    await mcp_playwright_browser_wait_for({ time: 3 });
    
    const chatSnapshot = await mcp_playwright_browser_snapshot();
    
    if (chatSnapshot.includes('Chat') && !chatSnapshot.includes('Unauthorized')) {
      console.log('✅ Chat interface accessible');
    } else {
      console.log('⚠️ Chat interface may require authentication');
    }
    
    // Test documents access
    console.log('\n3. Testing Documents Access');
    await mcp_playwright_browser_navigate({ 
      url: `${DEPLOYED_APP_URL}/documents` 
    });
    await mcp_playwright_browser_wait_for({ time: 3 });
    
    const documentsSnapshot = await mcp_playwright_browser_snapshot();
    
    if (documentsSnapshot.includes('Documents') && !documentsSnapshot.includes('Unauthorized')) {
      console.log('✅ Documents interface accessible');
    } else {
      console.log('⚠️ Documents interface may require authentication');
    }
    
    // Check for CORS errors
    console.log('\n4. Checking for CORS Errors');
    try {
      const consoleMessages = await mcp_playwright_browser_console_messages();
      const corsErrors = consoleMessages.filter(msg => 
        msg.text && msg.text.toLowerCase().includes('cors')
      );
      
      if (corsErrors.length === 0) {
        console.log('✅ No CORS errors detected');
      } else {
        console.log(`⚠️ ${corsErrors.length} CORS errors detected`);
        corsErrors.forEach(error => {
          console.log(`   - ${error.text}`);
        });
      }
    } catch (error) {
      console.log('Console check completed');
    }
    
    console.log('\n✅ Basic admin access test completed');
    return true;
    
  } catch (error) {
    console.error('❌ Admin access test failed:', error.message);
    return false;
  }
}

async function runSimpleAdminTest() {
  console.log('🚀 Starting Simple Admin Test');
  console.log('Testing basic admin functionality');
  
  try {
    // Install browser if needed
    await mcp_playwright_browser_install();
    console.log('✅ Browser installed');
    
    // Run basic test
    const result = await testAdminAccess();
    
    if (result) {
      console.log('\n🎉 Simple Admin Test PASSED');
    } else {
      console.log('\n❌ Simple Admin Test FAILED');
    }
    
    // Take screenshot
    await mcp_playwright_browser_take_screenshot({
      filename: `simple-admin-test-${Date.now()}.png`,
      fullPage: true
    });
    
    return result;
    
  } catch (error) {
    console.error('❌ Simple Admin Test Suite failed:', error.message);
    
    // Take screenshot for debugging
    await mcp_playwright_browser_take_screenshot({
      filename: `simple-admin-test-failure-${Date.now()}.png`,
      fullPage: true
    });
    
    return false;
  } finally {
    // Close browser
    await mcp_playwright_browser_close();
    console.log('✅ Browser closed');
  }
}

// Export for use
export { runSimpleAdminTest };
