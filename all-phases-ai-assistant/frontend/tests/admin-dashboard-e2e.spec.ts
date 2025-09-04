// Admin Dashboard End-to-End Tests
// Tests admin dashboard functionality against deployed AWS infrastructure

import { expect, test } from '@playwright/test';

test.describe('Admin Dashboard E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the deployed application
    await page.goto('https://dq9tlzfsf1veq.cloudfront.net');
    
    // Wait for page to load
    await page.waitForTimeout(2000);
  });

  test('should display admin dashboard for admin users', async ({ page }) => {
    // This test will fail initially because we need admin user credentials
    
    // Try to login as admin (this will fail first - RED phase)
    await page.fill('input[type="email"]', 'admin@example.com');
    await page.fill('input[type="password"]', 'AdminPassword123!');
    await page.click('button[type="submit"]');
    
    // Wait for navigation after login
    await page.waitForTimeout(3000);
    
    // Navigate to admin dashboard
    await page.goto('https://dq9tlzfsf1veq.cloudfront.net/admin/dashboard');
    
    // Verify admin dashboard elements are present
    await expect(page.locator('h1')).toContainText('Admin Dashboard');
    await expect(page.locator('[data-testid="knowledge-base-status"]')).toBeVisible();
    await expect(page.locator('[data-testid="knowledge-base-metrics"]')).toBeVisible();
    await expect(page.locator('[data-testid="ingestion-jobs"]')).toBeVisible();
  });

  test('should load Knowledge Base status from real AWS API', async ({ page }) => {
    // This test will fail initially - RED phase
    
    // Login as admin user (will fail without proper credentials)
    await page.fill('input[type="email"]', 'admin@example.com');
    await page.fill('input[type="password"]', 'AdminPassword123!');
    await page.click('button[type="submit"]');
    
    await page.waitForTimeout(3000);
    await page.goto('https://dq9tlzfsf1veq.cloudfront.net/admin/dashboard');
    
    // Wait for Knowledge Base status to load from real API
    await page.waitForSelector('[data-testid="kb-status-loaded"]', { timeout: 10000 });
    
    // Verify status shows real data from AWS
    const statusElement = page.locator('[data-testid="kb-status"]');
    await expect(statusElement).toContainText('PQB7MB5ORO'); // Real KB ID
    
    const documentCount = page.locator('[data-testid="document-count"]');
    await expect(documentCount).toBeVisible();
  });

  test('should display ingestion jobs from real Bedrock API', async ({ page }) => {
    // This test will fail initially - RED phase
    
    // Login as admin
    await page.fill('input[type="email"]', 'admin@example.com');
    await page.fill('input[type="password"]', 'AdminPassword123!');
    await page.click('button[type="submit"]');
    
    await page.waitForTimeout(3000);
    await page.goto('https://dq9tlzfsf1veq.cloudfront.net/admin/dashboard');
    
    // Wait for ingestion jobs to load from real Bedrock API
    await page.waitForSelector('[data-testid="ingestion-jobs-loaded"]', { timeout: 10000 });
    
    // Verify jobs list is displayed
    const jobsList = page.locator('[data-testid="ingestion-jobs-list"]');
    await expect(jobsList).toBeVisible();
  });

  test('should start Knowledge Base sync via real AWS API', async ({ page }) => {
    // This test will fail initially - RED phase
    
    // Login as admin
    await page.fill('input[type="email"]', 'admin@example.com');
    await page.fill('input[type="password"]', 'AdminPassword123!');
    await page.click('button[type="submit"]');
    
    await page.waitForTimeout(3000);
    await page.goto('https://dq9tlzfsf1veq.cloudfront.net/admin/dashboard');
    
    // Wait for page to load
    await page.waitForSelector('[data-testid="start-sync-button"]', { timeout: 10000 });
    
    // Click start sync button
    await page.click('[data-testid="start-sync-button"]');
    
    // Verify sync started (should show new ingestion job)
    await page.waitForSelector('[data-testid="sync-started-notification"]', { timeout: 15000 });
    
    // Verify new job appears in the list
    const newJob = page.locator('[data-testid="ingestion-job"]:first-child');
    await expect(newJob).toContainText('STARTING');
  });

  test('should display Knowledge Base metrics from real CloudWatch', async ({ page }) => {
    // This test will fail initially - RED phase
    
    // Login as admin
    await page.fill('input[type="email"]', 'admin@example.com');
    await page.fill('input[type="password"]', 'AdminPassword123!');
    await page.click('button[type="submit"]');
    
    await page.waitForTimeout(3000);
    await page.goto('https://dq9tlzfsf1veq.cloudfront.net/admin/dashboard');
    
    // Wait for metrics to load from real AWS APIs
    await page.waitForSelector('[data-testid="metrics-loaded"]', { timeout: 10000 });
    
    // Verify metrics display real data
    const totalDocs = page.locator('[data-testid="total-documents"]');
    await expect(totalDocs).toBeVisible();
    
    const totalQueries = page.locator('[data-testid="total-queries"]');
    await expect(totalQueries).toBeVisible();
    
    const responseTime = page.locator('[data-testid="avg-response-time"]');
    await expect(responseTime).toBeVisible();
  });

  test('should handle admin dashboard responsive layout', async ({ page }) => {
    // This test will fail initially - RED phase
    
    // Login as admin
    await page.fill('input[type="email"]', 'admin@example.com');
    await page.fill('input[type="password"]', 'AdminPassword123!');
    await page.click('button[type="submit"]');
    
    await page.waitForTimeout(3000);
    await page.goto('https://dq9tlzfsf1veq.cloudfront.net/admin/dashboard');
    
    // Test mobile layout
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(1000);
    
    // Verify mobile layout works
    const dashboard = page.locator('[data-testid="admin-dashboard"]');
    await expect(dashboard).toBeVisible();
    
    // Test desktop layout
    await page.setViewportSize({ width: 1200, height: 800 });
    await page.waitForTimeout(1000);
    
    // Verify desktop layout works
    await expect(dashboard).toBeVisible();
    
    // Verify grid layout adapts properly
    const metricsGrid = page.locator('[data-testid="metrics-grid"]');
    await expect(metricsGrid).toBeVisible();
  });
});