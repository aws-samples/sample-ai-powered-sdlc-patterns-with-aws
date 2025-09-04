// Chat Interface End-to-End Tests
// Tests the complete chat workflow with deployed Knowledge Base backend
// Uses Playwright MCP server for browser automation

import { afterEach, beforeEach, describe, expect, test } from '@jest/globals';

describe('Chat Interface with Knowledge Base Integration', () => {
  const DEPLOYED_APP_URL = 'https://dq9tlzfsf1veq.cloudfront.net';
  
  beforeEach(async () => {
    // Navigate to deployed application
    await mcp_playwright_browser_navigate({ 
      url: DEPLOYED_APP_URL 
    });
    
    // Wait for page load
    await mcp_playwright_browser_wait_for({ time: 3 });
  });

  afterEach(async () => {
    // Take screenshot for debugging if test fails
    await mcp_playwright_browser_take_screenshot({
      filename: `chat-test-${Date.now()}.png`
    });
  });

  test('should display chat interface with proper layout', async () => {
    // Take snapshot to identify elements
    const snapshot = await mcp_playwright_browser_snapshot();
    
    // Verify chat interface elements are present
    expect(snapshot).toContain('AI Assistant');
    expect(snapshot).toContain('Ask me anything about your documents');
    expect(snapshot).toContain('Type your message');
  });

  test('should handle user message input and display', async () => {
    // Take snapshot to identify chat input
    const snapshot = await mcp_playwright_browser_snapshot();
    
    // Type a test message
    const testMessage = 'What is AWS Lambda?';
    await mcp_playwright_browser_type({
      element: 'chat input textarea',
      ref: 'textarea',
      text: testMessage
    });
    
    // Send the message
    await mcp_playwright_browser_click({
      element: 'send button',
      ref: 'button[type="submit"]'
    });
    
    // Wait for message to appear
    await mcp_playwright_browser_wait_for({ time: 2 });
    
    // Verify user message is displayed
    const afterSendSnapshot = await mcp_playwright_browser_snapshot();
    expect(afterSendSnapshot).toContain(testMessage);
  });

  test('should show typing indicator during AI processing', async () => {
    // Type and send a message
    await mcp_playwright_browser_type({
      element: 'chat input',
      ref: 'textarea',
      text: 'Tell me about testing strategies'
    });
    
    await mcp_playwright_browser_click({
      element: 'send button',
      ref: 'button[type="submit"]'
    });
    
    // Check for typing indicator immediately after sending
    await mcp_playwright_browser_wait_for({ time: 1 });
    const typingSnapshot = await mcp_playwright_browser_snapshot();
    expect(typingSnapshot).toContain('AI is thinking');
  });

  test('should display AI response with source citations', async () => {
    // Send a question that should have document sources
    await mcp_playwright_browser_type({
      element: 'chat input',
      ref: 'textarea',
      text: 'What are the best practices for AWS Lambda development?'
    });
    
    await mcp_playwright_browser_click({
      element: 'send button',
      ref: 'button[type="submit"]'
    });
    
    // Wait for AI response (up to 15 seconds)
    await mcp_playwright_browser_wait_for({ time: 15 });
    
    // Verify AI response is displayed
    const responseSnapshot = await mcp_playwright_browser_snapshot();
    expect(responseSnapshot).toContain('Sources');
    
    // Check for source citation elements
    expect(responseSnapshot).toMatch(/confidence|excerpt|document/i);
  });

  test('should handle conversation history properly', async () => {
    // Send first message
    await mcp_playwright_browser_type({
      element: 'chat input',
      ref: 'textarea',
      text: 'What is serverless computing?'
    });
    
    await mcp_playwright_browser_click({
      element: 'send button',
      ref: 'button[type="submit"]'
    });
    
    // Wait for response
    await mcp_playwright_browser_wait_for({ time: 10 });
    
    // Send follow-up message
    await mcp_playwright_browser_type({
      element: 'chat input',
      ref: 'textarea',
      text: 'Can you give me more details about AWS Lambda?'
    });
    
    await mcp_playwright_browser_click({
      element: 'send button',
      ref: 'button[type="submit"]'
    });
    
    // Wait for second response
    await mcp_playwright_browser_wait_for({ time: 10 });
    
    // Verify both messages are in conversation history
    const historySnapshot = await mcp_playwright_browser_snapshot();
    expect(historySnapshot).toContain('serverless computing');
    expect(historySnapshot).toContain('AWS Lambda');
  });

  test('should display model information in responses', async () => {
    // Send a complex question to trigger Claude Opus
    await mcp_playwright_browser_type({
      element: 'chat input',
      ref: 'textarea',
      text: 'Analyze the architectural trade-offs between microservices and monolithic applications in cloud environments'
    });
    
    await mcp_playwright_browser_click({
      element: 'send button',
      ref: 'button[type="submit"]'
    });
    
    // Wait for response
    await mcp_playwright_browser_wait_for({ time: 15 });
    
    // Check for model badge
    const modelSnapshot = await mcp_playwright_browser_snapshot();
    expect(modelSnapshot).toMatch(/Claude (Opus|Sonnet)/i);
  });

  test('should handle source citation clicks', async () => {
    // Send a question
    await mcp_playwright_browser_type({
      element: 'chat input',
      ref: 'textarea',
      text: 'What are the security best practices for AWS?'
    });
    
    await mcp_playwright_browser_click({
      element: 'send button',
      ref: 'button[type="submit"]'
    });
    
    // Wait for response with sources
    await mcp_playwright_browser_wait_for({ time: 15 });
    
    // Try to click on a source citation
    const sourcesSnapshot = await mcp_playwright_browser_snapshot();
    if (sourcesSnapshot.includes('Sources')) {
      // Click on first source if available
      await mcp_playwright_browser_click({
        element: 'source citation',
        ref: '[data-testid="source-citation"]'
      });
      
      // Verify source click handling
      await mcp_playwright_browser_wait_for({ time: 2 });
    }
  });

  test('should handle error scenarios gracefully', async () => {
    // Test with very long message to trigger validation
    const longMessage = 'A'.repeat(600); // Exceeds 500 char limit
    
    await mcp_playwright_browser_type({
      element: 'chat input',
      ref: 'textarea',
      text: longMessage
    });
    
    // Verify character limit warning
    const limitSnapshot = await mcp_playwright_browser_snapshot();
    expect(limitSnapshot).toMatch(/characters (over limit|remaining)/i);
    
    // Send button should be disabled
    const sendButton = await mcp_playwright_browser_snapshot();
    expect(sendButton).toContain('cursor-not-allowed');
  });

  test('should support keyboard shortcuts', async () => {
    // Type a message
    await mcp_playwright_browser_type({
      element: 'chat input',
      ref: 'textarea',
      text: 'Test keyboard shortcut'
    });
    
    // Press Enter to send (instead of clicking button)
    await mcp_playwright_browser_press_key({ key: 'Enter' });
    
    // Wait for message to be sent
    await mcp_playwright_browser_wait_for({ time: 2 });
    
    // Verify message was sent
    const shortcutSnapshot = await mcp_playwright_browser_snapshot();
    expect(shortcutSnapshot).toContain('Test keyboard shortcut');
  });

  test('should handle new conversation creation', async () => {
    // Send initial message
    await mcp_playwright_browser_type({
      element: 'chat input',
      ref: 'textarea',
      text: 'Initial message'
    });
    
    await mcp_playwright_browser_click({
      element: 'send button',
      ref: 'button[type="submit"]'
    });
    
    // Wait for response
    await mcp_playwright_browser_wait_for({ time: 10 });
    
    // Click "New Chat" button
    await mcp_playwright_browser_click({
      element: 'new chat button',
      ref: 'button'
    });
    
    // Verify conversation is cleared
    const newChatSnapshot = await mcp_playwright_browser_snapshot();
    expect(newChatSnapshot).toContain('Start a conversation');
    expect(newChatSnapshot).not.toContain('Initial message');
  });

  test('should be responsive on different screen sizes', async () => {
    // Test desktop view
    await mcp_playwright_browser_resize({ width: 1920, height: 1080 });
    await mcp_playwright_browser_wait_for({ time: 1 });
    
    let responsiveSnapshot = await mcp_playwright_browser_snapshot();
    expect(responsiveSnapshot).toContain('AI Assistant');
    
    // Test tablet view
    await mcp_playwright_browser_resize({ width: 768, height: 1024 });
    await mcp_playwright_browser_wait_for({ time: 1 });
    
    responsiveSnapshot = await mcp_playwright_browser_snapshot();
    expect(responsiveSnapshot).toContain('AI Assistant');
    
    // Test mobile view
    await mcp_playwright_browser_resize({ width: 375, height: 667 });
    await mcp_playwright_browser_wait_for({ time: 1 });
    
    responsiveSnapshot = await mcp_playwright_browser_snapshot();
    expect(responsiveSnapshot).toContain('AI Assistant');
  });
});

describe('Chat Interface Performance Tests', () => {
  const DEPLOYED_APP_URL = 'https://dq9tlzfsf1veq.cloudfront.net';
  
  test('should load chat interface within acceptable time', async () => {
    const startTime = Date.now();
    
    await mcp_playwright_browser_navigate({ 
      url: DEPLOYED_APP_URL 
    });
    
    // Wait for chat interface to be fully loaded
    await mcp_playwright_browser_wait_for({ time: 5 });
    
    const loadTime = Date.now() - startTime;
    
    // Chat interface should load within 5 seconds
    expect(loadTime).toBeLessThan(5000);
  });

  test('should handle rapid message sending', async () => {
    await mcp_playwright_browser_navigate({ 
      url: DEPLOYED_APP_URL 
    });
    
    await mcp_playwright_browser_wait_for({ time: 3 });
    
    // Send multiple messages quickly
    const messages = [
      'First quick message',
      'Second quick message',
      'Third quick message'
    ];
    
    for (const message of messages) {
      await mcp_playwright_browser_type({
        element: 'chat input',
        ref: 'textarea',
        text: message
      });
      
      await mcp_playwright_browser_press_key({ key: 'Enter' });
      await mcp_playwright_browser_wait_for({ time: 1 });
    }
    
    // Verify all messages are displayed
    const rapidSnapshot = await mcp_playwright_browser_snapshot();
    messages.forEach(message => {
      expect(rapidSnapshot).toContain(message);
    });
  });
});

describe('Chat Interface Accessibility Tests', () => {
  const DEPLOYED_APP_URL = 'https://dq9tlzfsf1veq.cloudfront.net';
  
  test('should support keyboard navigation', async () => {
    await mcp_playwright_browser_navigate({ 
      url: DEPLOYED_APP_URL 
    });
    
    await mcp_playwright_browser_wait_for({ time: 3 });
    
    // Tab to chat input
    await mcp_playwright_browser_press_key({ key: 'Tab' });
    await mcp_playwright_browser_press_key({ key: 'Tab' });
    
    // Type message using keyboard
    await mcp_playwright_browser_type({
      element: 'focused element',
      ref: ':focus',
      text: 'Keyboard navigation test'
    });
    
    // Send with Enter key
    await mcp_playwright_browser_press_key({ key: 'Enter' });
    
    // Verify message was sent
    await mcp_playwright_browser_wait_for({ time: 2 });
    const keyboardSnapshot = await mcp_playwright_browser_snapshot();
    expect(keyboardSnapshot).toContain('Keyboard navigation test');
  });

  test('should have proper ARIA labels and roles', async () => {
    await mcp_playwright_browser_navigate({ 
      url: DEPLOYED_APP_URL 
    });
    
    await mcp_playwright_browser_wait_for({ time: 3 });
    
    // Check accessibility snapshot for ARIA attributes
    const accessibilitySnapshot = await mcp_playwright_browser_snapshot();
    
    // Verify essential accessibility features
    expect(accessibilitySnapshot).toMatch(/role="(button|textbox|main|region)"/i);
    expect(accessibilitySnapshot).toMatch(/aria-label/i);
  });
});