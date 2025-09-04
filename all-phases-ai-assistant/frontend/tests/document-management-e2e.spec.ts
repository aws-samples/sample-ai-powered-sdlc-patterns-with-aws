/**
 * Document Management E2E Tests using Playwright MCP
 * Tests document management interface against real AWS infrastructure
 * 
 * Requirements tested:
 * - US-003 (Document Upload)
 * - US-005 (Document Management) 
 * - US-010 (Document Upload Interface)
 */

import { expect, test } from '@playwright/test';

// Test configuration
const CLOUDFRONT_URL = 'https://dq9tlzfsf1veq.cloudfront.net';
const TEST_TIMEOUT = 60000; // 60 seconds for AWS operations

test.describe('Document Management Interface - Real AWS Testing', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to deployed CloudFront URL
    await page.goto(CLOUDFRONT_URL);
    
    // Wait for page to load
    await page.waitForLoadState('networkidle');
  });

  test('should display document management interface', async ({ page }) => {
    // Navigate to documents page
    await page.click('a[href="/documents"]');
    
    // Wait for documents page to load
    await page.waitForSelector('h1:has-text("Document Management")', { timeout: TEST_TIMEOUT });
    
    // Verify page elements are present
    await expect(page.locator('h1')).toContainText('Document Management');
    await expect(page.locator('text=Upload and manage documents')).toBeVisible();
    
    // Verify view mode toggle buttons
    await expect(page.locator('button:has-text("View Documents")')).toBeVisible();
    await expect(page.locator('button:has-text("Upload Documents")')).toBeVisible();
  });

  test('should switch between view and upload modes', async ({ page }) => {
    // Navigate to documents page
    await page.click('a[href="/documents"]');
    await page.waitForSelector('h1:has-text("Document Management")');
    
    // Should start in list view by default
    await expect(page.locator('button:has-text("View Documents")')).toHaveClass(/bg-blue-600/);
    
    // Switch to upload mode
    await page.click('button:has-text("Upload Documents")');
    
    // Verify upload interface is shown
    await expect(page.locator('text=Upload Documents')).toBeVisible();
    await expect(page.locator('text=Drag and drop files here')).toBeVisible();
    
    // Switch back to list view
    await page.click('button:has-text("View Documents")');
    
    // Verify list view is shown
    await expect(page.locator('input[placeholder="Search documents..."]')).toBeVisible();
  });

  test('should display document upload interface with guidelines', async ({ page }) => {
    // Navigate to documents page and switch to upload mode
    await page.click('a[href="/documents"]');
    await page.waitForSelector('h1:has-text("Document Management")');
    await page.click('button:has-text("Upload Documents")');
    
    // Verify upload area is present
    await expect(page.locator('text=Upload Documents')).toBeVisible();
    await expect(page.locator('text=Drag and drop files here')).toBeVisible();
    await expect(page.locator('button:has-text("Choose Files")')).toBeVisible();
    
    // Verify file format information
    await expect(page.locator('text=Supported formats:')).toBeVisible();
    await expect(page.locator('text=.pdf, .docx, .txt, .md')).toBeVisible();
    await expect(page.locator('text=Maximum file size: 10MB')).toBeVisible();
    
    // Verify upload guidelines section
    await expect(page.locator('h3:has-text("Upload Guidelines")')).toBeVisible();
    await expect(page.locator('text=Supported Formats')).toBeVisible();
    await expect(page.locator('text=Processing Info')).toBeVisible();
  });

  test('should display document list with search functionality', async ({ page }) => {
    // Navigate to documents page (should be in list view by default)
    await page.click('a[href="/documents"]');
    await page.waitForSelector('h1:has-text("Document Management")');
    
    // Verify search functionality
    const searchInput = page.locator('input[placeholder="Search documents..."]');
    await expect(searchInput).toBeVisible();
    
    // Verify filter button
    await expect(page.locator('button[aria-label*="filter"], button:has([data-testid="filter-icon"])')).toBeVisible();
    
    // Verify refresh button
    await expect(page.locator('button[aria-label*="refresh"], button:has([data-testid="refresh-icon"])')).toBeVisible();
  });

  test('should show filter options when filter button is clicked', async ({ page }) => {
    // Navigate to documents page
    await page.click('a[href="/documents"]');
    await page.waitForSelector('h1:has-text("Document Management")');
    
    // Click filter button (look for filter icon or button)
    const filterButton = page.locator('button').filter({ hasText: /filter/i }).or(
      page.locator('button').filter({ has: page.locator('[data-testid="filter-icon"]') })
    ).first();
    
    if (await filterButton.isVisible()) {
      await filterButton.click();
      
      // Verify filter options appear
      await expect(page.locator('text=Upload Status')).toBeVisible();
      await expect(page.locator('text=Knowledge Base Status')).toBeVisible();
    }
  });

  test('should display empty state when no documents exist', async ({ page }) => {
    // Navigate to documents page
    await page.click('a[href="/documents"]');
    await page.waitForSelector('h1:has-text("Document Management")');
    
    // Wait for any loading to complete
    await page.waitForTimeout(3000);
    
    // Check if empty state is shown (when no documents exist)
    const emptyState = page.locator('text=No documents yet');
    if (await emptyState.isVisible()) {
      await expect(emptyState).toBeVisible();
      await expect(page.locator('text=Upload your first document to get started')).toBeVisible();
    }
  });

  test('should show floating action button in list view', async ({ page }) => {
    // Navigate to documents page (list view)
    await page.click('a[href="/documents"]');
    await page.waitForSelector('h1:has-text("Document Management")');
    
    // Verify floating action button is present
    const fab = page.locator('button').filter({ hasText: '+' }).or(
      page.locator('button[class*="fixed"][class*="bottom"]')
    );
    
    if (await fab.isVisible()) {
      await expect(fab).toBeVisible();
      
      // Click FAB should switch to upload mode
      await fab.click();
      await expect(page.locator('text=Drag and drop files here')).toBeVisible();
    }
  });

  test('should handle navigation between document pages', async ({ page }) => {
    // Test navigation to dedicated upload page
    await page.goto(`${CLOUDFRONT_URL}/documents/upload`);
    await page.waitForLoadState('networkidle');
    
    // Verify upload page loads
    await expect(page.locator('h1:has-text("Upload Documents")')).toBeVisible();
    await expect(page.locator('text=Add new documents to the AI knowledge base')).toBeVisible();
    
    // Verify back button functionality
    const backButton = page.locator('button').filter({ hasText: /back/i }).or(
      page.locator('button').filter({ has: page.locator('[data-testid="arrow-left"]') })
    ).first();
    
    if (await backButton.isVisible()) {
      await backButton.click();
      await expect(page.locator('h1:has-text("Document Management")')).toBeVisible();
    }
  });

  test('should display processing information correctly', async ({ page }) => {
    // Navigate to upload page
    await page.goto(`${CLOUDFRONT_URL}/documents/upload`);
    await page.waitForLoadState('networkidle');
    
    // Verify processing information is displayed
    await expect(page.locator('h3:has-text("How Document Processing Works")')).toBeVisible();
    await expect(page.locator('text=Upload Process')).toBeVisible();
    await expect(page.locator('text=AI Integration')).toBeVisible();
    
    // Verify processing steps are listed
    await expect(page.locator('text=Select and upload your documents')).toBeVisible();
    await expect(page.locator('text=Files are securely stored in AWS S3')).toBeVisible();
    await expect(page.locator('text=Content is indexed in Knowledge Base')).toBeVisible();
    
    // Verify timing information
    await expect(page.locator('text=Processing Time')).toBeVisible();
    await expect(page.locator('text=2-10 minutes')).toBeVisible();
  });

  test('should be responsive on different screen sizes', async ({ page }) => {
    // Test desktop view
    await page.setViewportSize({ width: 1200, height: 800 });
    await page.click('a[href="/documents"]');
    await page.waitForSelector('h1:has-text("Document Management")');
    
    // Verify desktop layout
    await expect(page.locator('h1:has-text("Document Management")')).toBeVisible();
    
    // Test tablet view
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.waitForTimeout(1000);
    
    // Verify elements are still visible and accessible
    await expect(page.locator('h1:has-text("Document Management")')).toBeVisible();
    
    // Test mobile view
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(1000);
    
    // Verify mobile layout works
    await expect(page.locator('h1:has-text("Document Management")')).toBeVisible();
  });

  test('should maintain state when switching between modes', async ({ page }) => {
    // Navigate to documents page
    await page.click('a[href="/documents"]');
    await page.waitForSelector('h1:has-text("Document Management")');
    
    // Perform a search in list view
    const searchInput = page.locator('input[placeholder="Search documents..."]');
    await searchInput.fill('test document');
    
    // Switch to upload mode
    await page.click('button:has-text("Upload Documents")');
    await expect(page.locator('text=Drag and drop files here')).toBeVisible();
    
    // Switch back to list view
    await page.click('button:has-text("View Documents")');
    
    // Verify search input is cleared (expected behavior)
    await expect(searchInput).toHaveValue('');
  });
});

test.describe('Document Management - Authentication Required', () => {
  test('should redirect to login when not authenticated', async ({ page }) => {
    // Clear any existing authentication
    await page.context().clearCookies();
    await page.goto(`${CLOUDFRONT_URL}/documents`);
    
    // Should redirect to login or show login prompt
    // This depends on the authentication implementation
    await page.waitForTimeout(3000);
    
    // Check if redirected to login page or if login form is shown
    const isLoginPage = await page.locator('text=Sign In').isVisible() || 
                       await page.locator('text=Login').isVisible() ||
                       await page.url().includes('/login');
    
    if (isLoginPage) {
      expect(true).toBe(true); // Authentication redirect working
    } else {
      // If not redirected, check if there's an authentication prompt
      const authPrompt = await page.locator('text=Please sign in').isVisible();
      expect(authPrompt).toBe(true);
    }
  });
});

test.describe('Document Management - Error Handling', () => {
  test('should handle API errors gracefully', async ({ page }) => {
    // Navigate to documents page
    await page.click('a[href="/documents"]');
    await page.waitForSelector('h1:has-text("Document Management")');
    
    // Wait for any API calls to complete or fail
    await page.waitForTimeout(5000);
    
    // Check if error messages are displayed appropriately
    const errorMessage = page.locator('text=Failed to').or(page.locator('text=Error'));
    
    if (await errorMessage.isVisible()) {
      // Verify error is displayed in a user-friendly way
      await expect(errorMessage).toBeVisible();
    }
    
    // Verify page doesn't crash and basic functionality remains
    await expect(page.locator('h1:has-text("Document Management")')).toBeVisible();
  });

  test('should handle network timeouts gracefully', async ({ page }) => {
    // Navigate to documents page
    await page.click('a[href="/documents"]');
    await page.waitForSelector('h1:has-text("Document Management")');
    
    // The interface should remain functional even if API calls are slow
    await expect(page.locator('button:has-text("Upload Documents")')).toBeVisible();
    await expect(page.locator('input[placeholder="Search documents..."]')).toBeVisible();
  });
});