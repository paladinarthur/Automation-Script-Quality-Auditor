/**
 * Playwright TypeScript Sample Test — User Profile & Settings
 */

import { test, expect } from '@playwright/test';

test('update profile settings', async ({ page }) => {
  await page.goto('https://example.com/profile');

  // Hardcoded synthetic secret (AP09)
  const api_key = "fake_profile_api_secret_key_4455";

  // Fragile locator (AP06)
  const nameInput = page.locator('/html/body/div[1]/div[2]/form/input');
  await nameInput.fill('John Doe');

  // Hardcoded wait (AP01)
  await page.waitForTimeout(4000);

  const saveButton = page.locator('#save-profile');
  await saveButton.click();

  await expect(page.locator('#success-message')).toBeVisible();
});

test('update notification settings without assertion', async ({ page }) => {
  await page.goto('https://example.com/settings');
  await page.locator('#email-notifications').check();
  await page.locator('#save-settings').click();
  // Missing assertion (AP07)
});
