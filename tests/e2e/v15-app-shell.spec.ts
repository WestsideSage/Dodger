import { expect, test } from '@playwright/test';
import { launchTokenHeaders } from './_token';

const baseUrl = 'http://127.0.0.1:8000';

test.describe('V15 Phase 4b — App shell: nav hamburger + Settings hidden', () => {
  test.beforeEach(async ({ request }) => {
    // Create a throwaway save so the game shell renders (not the save menu).
    const saveName = `e2e-v15-shell-${Date.now()}`;
    const res = await request.post(`${baseUrl}/api/saves/new`, {
      headers: await launchTokenHeaders(request),
      data: { name: saveName, club_id: 'aurora' },
    });
    expect(res.ok()).toBeTruthy();
  });

  test('Settings disabled item is not rendered', async ({ page }) => {
    await page.goto(`${baseUrl}/?tab=command`);
    // Wait for the game shell to load (not the save menu).
    await expect(page.locator('.left-nav')).toBeVisible({ timeout: 10000 });

    // The disabled Settings button must not appear in the DOM at all.
    // It should not be found by its accessible name or by its known text.
    await expect(page.getByRole('button', { name: /Settings/i })).toHaveCount(0);

    // The "Settings are coming soon" title must also be absent.
    await expect(page.locator('[title="Settings are coming soon"]')).toHaveCount(0);
  });

  test('hamburger toggles nav collapsed/expanded — keyboard operable', async ({ page }) => {
    await page.goto(`${baseUrl}/?tab=command`);
    await expect(page.locator('.left-nav')).toBeVisible({ timeout: 10000 });

    const hamburger = page.getByRole('button', { name: /Toggle navigation/i });
    await expect(hamburger).toBeVisible();

    // Initial state: nav is expanded (aria-expanded = true).
    await expect(hamburger).toHaveAttribute('aria-expanded', 'true');
    await expect(hamburger).toHaveAttribute('aria-controls', 'primary-nav');

    // Click to collapse.
    await hamburger.click();
    await expect(hamburger).toHaveAttribute('aria-expanded', 'false');

    // The <nav> has display:none when collapsed (primary AT safety).
    // tabIndex=-1 on items is belt-and-suspenders.
    // toHaveAttribute reads the DOM attribute regardless of display:none,
    // so this assertion works even though the nav is visually hidden.
    const firstNavItem = page.locator('#primary-nav .nav-item').first();
    await expect(firstNavItem).toHaveAttribute('tabindex', '-1');

    // Click to expand.
    await hamburger.click();
    await expect(hamburger).toHaveAttribute('aria-expanded', 'true');

    // Nav items are keyboard-reachable again (tabIndex restored to 0).
    const tabIdx = await firstNavItem.getAttribute('tabindex');
    expect(tabIdx === null || tabIdx === '0').toBe(true);
  });

  test('hamburger is operable via keyboard (Enter key)', async ({ page }) => {
    await page.goto(`${baseUrl}/?tab=command`);
    await expect(page.locator('.left-nav')).toBeVisible({ timeout: 10000 });

    const hamburger = page.getByRole('button', { name: /Toggle navigation/i });

    // Focus the hamburger and press Enter.
    await hamburger.focus();
    await page.keyboard.press('Enter');
    await expect(hamburger).toHaveAttribute('aria-expanded', 'false');

    // Press Enter again to expand.
    await page.keyboard.press('Enter');
    await expect(hamburger).toHaveAttribute('aria-expanded', 'true');
  });

  test('no horizontal overflow at 390x844 in collapsed state', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(`${baseUrl}/?tab=command`);
    await expect(page.locator('.left-nav')).toBeVisible({ timeout: 10000 });

    // Collapse the nav.
    const hamburger = page.getByRole('button', { name: /Toggle navigation/i });
    await hamburger.click();
    await expect(hamburger).toHaveAttribute('aria-expanded', 'false');

    // Check for horizontal overflow: scrollWidth must not exceed clientWidth.
    const overflow = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });
    expect(overflow).toBe(false);

    // And the workspace content area must still be visible.
    await expect(page.locator('.workspace')).toBeVisible();
  });
});
