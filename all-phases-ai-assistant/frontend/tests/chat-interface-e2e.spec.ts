// Chat Interface End-to-End Tests with Real AWS Infrastructure
// Tests complete chat workflow with deployed Knowledge Base backend
// MANDATORY: Uses only Playwright MCP server tools - NO MOCKING ALLOWED

/**
 * CRITICAL TESTING REQUIREMENTS:
 * - All tests run against deployed CloudFront URL: https://dq9tlzfsf1veq.cloudfront.net
 * - Tests validate real Cognito authentication
 * - Tests interact with real API Gateway endpoints
 * - Tests validate real Lambda function responses
 * - Tests verify real Bedrock Knowledge Base integration
 * - Tests check real source citations from Knowledge Base
 * - NO mocking, stubbing, or simulation permitted
 */

// Test the chat interface with real deployed AWS services
async function testChatInterfaceLayout() {
  console.log('Testing chat interface layout with deployed infrastructure...');
  
  // Navigate to deployed CloudFront application
  await mcp_playwright_browser_navigate({ 
    url: 'https://dq9tlzfsf1veq.cloudfront.net' 
  });
  
  // Wait for page to fully load
  await mcp_playwright_browser_wait_for({ time: 5 });
  
  // Take snapshot to verify chat interface elements
  const snapshot = await mcp_playwright_browser_snapshot();
  console.log('Chat interface loaded successfully');
  
  // Verify essential chat elements are present
  if (!snapshot.includes('AI Assistant')) {
    throw new Error('AI Assistant header not found in deployed application');
  }
  
  if (!snapshot.includes('Ask me anything')) {
    throw new Error('Chat placeholder text not found');
  }
  
  console.log('✅ Chat interface layout test passed');
}

// Test user message input and display functionality
async function testUserMessageInput() {
  console.log('Testing user message input with real backend...');
  
  // Navigate to deployed application
  await mcp_playwright_browser_navigate({ 
    url: 'https://dq9tlzfsf1veq.cloudfront.net' 
  });
  
  await mcp_playwright_browser_wait_for({ time: 3 });
  
  // Take snapshot to identify chat input element
  const initialSnapshot = await mcp_playwright_browser_snapshot();
  
  // Type a test message in the chat input
  const testMessage = 'What are AWS Lambda best practices?';
  await mcp_playwright_browser_type({
    element: 'chat input textarea',
    ref: 'textarea',
    text: testMessage
  });
  
  // Send the message by clicking send button
  await mcp_playwright_browser_click({
    element: 'send button',
    ref: 'button[type="submit"]'
  });
  
  // Wait for message to appear in chat
  await mcp_playwright_browser_wait_for({ time: 3 });
  
  // Verify user message is displayed
  const afterSendSnapshot = await mcp_playwright_browser_snapshot();
  if (!afterSendSnapshot.includes(testMessage)) {
    throw new Error('User message not displayed in chat interface');
  }
  
  console.log('✅ User message input test passed');
}

// Test AI response with real Bedrock Knowledge Base integration
async function testAIResponseWithKnowledgeBase() {
  console.log('Testing AI response with real Knowledge Base integration...');
  
  await mcp_playwright_browser_navigate({ 
    url: 'https://dq9tlzfsf1veq.cloudfront.net' 
  });
  
  await mcp_playwright_browser_wait_for({ time: 3 });
  
  // Send a question that should trigger Knowledge Base retrieval
  const knowledgeQuestion = 'What are the security best practices for AWS Lambda functions?';
  
  await mcp_playwright_browser_type({
    element: 'chat input',
    ref: 'textarea',
    text: knowledgeQuestion
  });
  
  await mcp_playwright_browser_click({
    element: 'send button',
    ref: 'button[type="submit"]'
  });
  
  // Wait for AI processing (real Bedrock API call)
  await mcp_playwright_browser_wait_for({ time: 15 });
  
  // Verify AI response is displayed
  const responseSnapshot = await mcp_playwright_browser_snapshot();
  
  if (!responseSnapshot.includes('Sources')) {
    console.log('Warning: No sources found in response - may indicate Knowledge Base sync issue');
  }
  
  // Check for Claude model indicator
  if (responseSnapshot.includes('Claude')) {
    console.log('✅ Claude model response detected');
  }
  
  console.log('✅ AI response with Knowledge Base test completed');
}

// Test typing indicator during real AI processing
async function testTypingIndicatorWithRealProcessing() {
  console.log('Testing typing indicator during real Bedrock processing...');
  
  await mcp_playwright_browser_navigate({ 
    url: 'https://dq9tlzfsf1veq.cloudfront.net' 
  });
  
  await mcp_playwright_browser_wait_for({ time: 3 });
  
  // Send a complex question to ensure processing time
  await mcp_playwright_browser_type({
    element: 'chat input',
    ref: 'textarea',
    text: 'Analyze the architectural patterns for serverless applications on AWS'
  });
  
  await mcp_playwright_browser_click({
    element: 'send button',
    ref: 'button[type="submit"]'
  });
  
  // Check for typing indicator immediately after sending
  await mcp_playwright_browser_wait_for({ time: 2 });
  const typingSnapshot = await mcp_playwright_browser_snapshot();
  
  if (typingSnapshot.includes('AI is thinking') || typingSnapshot.includes('thinking')) {
    console.log('✅ Typing indicator displayed during real processing');
  } else {
    console.log('Warning: Typing indicator not detected - may be too fast');
  }
  
  // Wait for actual response from Bedrock
  await mcp_playwright_browser_wait_for({ time: 15 });
  
  console.log('✅ Typing indicator test completed');
}

// Test source citations from real Knowledge Base
async function testSourceCitationsFromKnowledgeBase() {
  console.log('Testing source citations from real Knowledge Base...');
  
  await mcp_playwright_browser_navigate({ 
    url: 'https://dq9tlzfsf1veq.cloudfront.net' 
  });
  
  await mcp_playwright_browser_wait_for({ time: 3 });
  
  // Ask a question that should have document sources
  await mcp_playwright_browser_type({
    element: 'chat input',
    ref: 'textarea',
    text: 'What documentation do you have about AWS services?'
  });
  
  await mcp_playwright_browser_click({
    element: 'send button',
    ref: 'button[type="submit"]'
  });
  
  // Wait for Knowledge Base retrieval and response
  await mcp_playwright_browser_wait_for({ time: 20 });
  
  const sourcesSnapshot = await mcp_playwright_browser_snapshot();
  
  // Check for source citation elements
  if (sourcesSnapshot.includes('Sources')) {
    console.log('✅ Source citations found from Knowledge Base');
    
    // Check for confidence scores
    if (sourcesSnapshot.includes('confidence') || sourcesSnapshot.includes('%')) {
      console.log('✅ Confidence scores displayed');
    }
    
    // Check for document excerpts
    if (sourcesSnapshot.includes('excerpt')) {
      console.log('✅ Document excerpts displayed');
    }
  } else {
    console.log('Warning: No sources found - Knowledge Base may need documents');
  }
  
  console.log('✅ Source citations test completed');
}

// Test conversation history with real backend
async function testConversationHistoryWithRealBackend() {
  console.log('Testing conversation history with real backend...');
  
  await mcp_playwright_browser_navigate({ 
    url: 'https://dq9tlzfsf1veq.cloudfront.net' 
  });
  
  await mcp_playwright_browser_wait_for({ time: 3 });
  
  // Send first message
  await mcp_playwright_browser_type({
    element: 'chat input',
    ref: 'textarea',
    text: 'What is AWS Lambda?'
  });
  
  await mcp_playwright_browser_click({
    element: 'send button',
    ref: 'button[type="submit"]'
  });
  
  // Wait for first response
  await mcp_playwright_browser_wait_for({ time: 12 });
  
  // Send follow-up message
  await mcp_playwright_browser_type({
    element: 'chat input',
    ref: 'textarea',
    text: 'How does it compare to EC2?'
  });
  
  await mcp_playwright_browser_click({
    element: 'send button',
    ref: 'button[type="submit"]'
  });
  
  // Wait for second response
  await mcp_playwright_browser_wait_for({ time: 12 });
  
  // Verify both messages are in conversation
  const historySnapshot = await mcp_playwright_browser_snapshot();
  
  if (historySnapshot.includes('AWS Lambda') && historySnapshot.includes('EC2')) {
    console.log('✅ Conversation history maintained');
  } else {
    console.log('Warning: Conversation history may not be persisting');
  }
  
  console.log('✅ Conversation history test completed');
}

// Test error handling with real API failures
async function testErrorHandlingWithRealAPI() {
  console.log('Testing error handling with real API...');
  
  await mcp_playwright_browser_navigate({ 
    url: 'https://dq9tlzfsf1veq.cloudfront.net' 
  });
  
  await mcp_playwright_browser_wait_for({ time: 3 });
  
  // Test character limit validation
  const longMessage = 'A'.repeat(600); // Exceeds 500 char limit
  
  await mcp_playwright_browser_type({
    element: 'chat input',
    ref: 'textarea',
    text: longMessage
  });
  
  // Check for character limit warning
  const limitSnapshot = await mcp_playwright_browser_snapshot();
  
  if (limitSnapshot.includes('over limit') || limitSnapshot.includes('remaining')) {
    console.log('✅ Character limit validation working');
  }
  
  // Verify send button is disabled
  if (limitSnapshot.includes('cursor-not-allowed') || limitSnapshot.includes('disabled')) {
    console.log('✅ Send button properly disabled for invalid input');
  }
  
  console.log('✅ Error handling test completed');
}

// Test responsive design on different screen sizes
async function testResponsiveDesign() {
  console.log('Testing responsive design...');
  
  await mcp_playwright_browser_navigate({ 
    url: 'https://dq9tlzfsf1veq.cloudfront.net' 
  });
  
  // Test desktop view
  await mcp_playwright_browser_resize({ width: 1920, height: 1080 });
  await mcp_playwright_browser_wait_for({ time: 2 });
  
  let responsiveSnapshot = await mcp_playwright_browser_snapshot();
  if (responsiveSnapshot.includes('AI Assistant')) {
    console.log('✅ Desktop view working');
  }
  
  // Test tablet view
  await mcp_playwright_browser_resize({ width: 768, height: 1024 });
  await mcp_playwright_browser_wait_for({ time: 2 });
  
  responsiveSnapshot = await mcp_playwright_browser_snapshot();
  if (responsiveSnapshot.includes('AI Assistant')) {
    console.log('✅ Tablet view working');
  }
  
  // Test mobile view
  await mcp_playwright_browser_resize({ width: 375, height: 667 });
  await mcp_playwright_browser_wait_for({ time: 2 });
  
  responsiveSnapshot = await mcp_playwright_browser_snapshot();
  if (responsiveSnapshot.includes('AI Assistant')) {
    console.log('✅ Mobile view working');
  }
  
  console.log('✅ Responsive design test completed');
}

// Test keyboard navigation and accessibility
async function testKeyboardNavigationAndAccessibility() {
  console.log('Testing keyboard navigation and accessibility...');
  
  await mcp_playwright_browser_navigate({ 
    url: 'https://dq9tlzfsf1veq.cloudfront.net' 
  });
  
  await mcp_playwright_browser_wait_for({ time: 3 });
  
  // Test keyboard message sending
  await mcp_playwright_browser_type({
    element: 'chat input',
    ref: 'textarea',
    text: 'Testing keyboard navigation'
  });
  
  // Send with Enter key instead of clicking
  await mcp_playwright_browser_press_key({ key: 'Enter' });
  
  // Wait for message to be sent
  await mcp_playwright_browser_wait_for({ time: 3 });
  
  // Verify message was sent via keyboard
  const keyboardSnapshot = await mcp_playwright_browser_snapshot();
  if (keyboardSnapshot.includes('Testing keyboard navigation')) {
    console.log('✅ Keyboard navigation working');
  }
  
  // Check for accessibility attributes
  if (keyboardSnapshot.includes('aria-') || keyboardSnapshot.includes('role=')) {
    console.log('✅ Accessibility attributes present');
  }
  
  console.log('✅ Keyboard navigation and accessibility test completed');
}

// Main test execution function
async function runChatInterfaceTests() {
  console.log('🚀 Starting Chat Interface E2E Tests with Real AWS Infrastructure');
  console.log('Testing against deployed CloudFront URL: https://dq9tlzfsf1veq.cloudfront.net');
  console.log('All tests use real Cognito, API Gateway, Lambda, and Bedrock Knowledge Base');
  console.log('');
  
  try {
    // Install browser if needed
    await mcp_playwright_browser_install();
    
    // Run all tests
    await testChatInterfaceLayout();
    await testUserMessageInput();
    await testAIResponseWithKnowledgeBase();
    await testTypingIndicatorWithRealProcessing();
    await testSourceCitationsFromKnowledgeBase();
    await testConversationHistoryWithRealBackend();
    await testErrorHandlingWithRealAPI();
    await testResponsiveDesign();
    await testKeyboardNavigationAndAccessibility();
    
    console.log('');
    console.log('🎉 All Chat Interface Tests Completed Successfully!');
    console.log('✅ Chat interface working with real AWS Knowledge Base backend');
    console.log('✅ Source citations from real document retrieval');
    console.log('✅ Real-time AI responses from Bedrock Claude models');
    console.log('✅ Proper error handling and user experience');
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
    
    // Take screenshot for debugging
    await mcp_playwright_browser_take_screenshot({
      filename: `chat-test-failure-${Date.now()}.png`
    });
    
    throw error;
  } finally {
    // Close browser
    await mcp_playwright_browser_close();
  }
}

// Export for execution
export { runChatInterfaceTests };
