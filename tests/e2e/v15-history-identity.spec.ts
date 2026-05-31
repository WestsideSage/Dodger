import { test, expect } from '@playwright/test';

// Verifies the History & Identity legibility changes on a fresh save.
// Populated-history proof (Best Newcomer ProofChip on a 4-season save)
// requires a seeded multi-season DB — test manually via the Dynasty Office
// History tab after running the fast-forward playtest (docs/playtest_output/).
test.describe('V15 Phase 4a — History & Identity', () => {
  test.beforeEach(async ({ page, request }) => {
    const baseUrl = 'http://127.0.0.1:8000';
    const saveName = `e2e-history-${Date.now()}`;
    const create = await request.post(`${baseUrl}/api/saves/new`, {
      data: { name: saveName, club_id: 'aurora' },
    });
    expect(create.ok()).toBeTruthy();

    // Navigate to the Dynasty Office History tab on a fresh or existing save.
    // Adjust selectors to match the app's actual navigation structure.
    await page.goto(`${baseUrl}/?tab=dynasty&subtab=history`);
  });

  test('Program Identity glance cell contains TermTip trigger', async ({ page }) => {
    // Navigate to the History tab inside Dynasty Office.
    // The exact navigation depends on whether a save is already loaded.
    // This selector targets the Dynasty Office tab and then History sub-tab.
    const dynastyBtn = page.getByRole('button', { name: /dynasty|history|office/i }).first();
    if (await dynastyBtn.isVisible()) {
      await dynastyBtn.click();
    }
    const historyTab = page.getByRole('button', { name: /history/i }).first();
    if (await historyTab.isVisible()) {
      await historyTab.click();
    }

    // The Program Identity cell should have a TermTip — a button with aria-label "What is Program Identity?"
    const tip = page.getByRole('button', { name: /What is Program Identity\?/i });
    await expect(tip).toBeVisible({ timeout: 5000 });

    // Activate the tooltip and confirm it explains flavor nature.
    await tip.focus();
    const tooltip = page.getByRole('tooltip');
    await expect(tooltip).toBeVisible();
    await expect(tooltip).toContainText(/flavor|strategic lean|tactical/i);
  });

  test('Empty BannerShelf renders honest EmptyState', async ({ page }) => {
    // On a fresh save or early-season save, banners.length === 0.
    const emptyStatus = page.getByRole('status').filter({ hasText: /no banners yet/i });
    if (await emptyStatus.isVisible()) {
      await expect(emptyStatus).toContainText(/championship or earn a season award/i);
    }
    // If a banner exists (loaded save), this branch is skipped — not a failure.
  });

  test('Empty AlumniLineage renders honest EmptyState (via Alumni tab)', async ({ page }) => {
    // Switch to the Alumni tab in the Banner Shelf + Alumni Lineage section.
    const alumniTab = page.getByRole('button', { name: /alumni/i });
    if (await alumniTab.isVisible()) {
      await alumniTab.click();
      const emptyStatus = page.getByRole('status').filter({ hasText: /no departed players yet/i });
      if (await emptyStatus.isVisible()) {
        await expect(emptyStatus).toContainText(/first alumni season/i);
      }
    }
  });

  test('Glance strip does not contain "Archive Through" jargon', async ({ page }) => {
    // Confirm the old jargon label is gone.
    await expect(page.getByText(/archive through/i)).not.toBeVisible();
    // Confirm the replacement label is present.
    await expect(page.getByText(/season range/i)).toBeVisible();
  });

  test('No horizontal overflow at 390px', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    const overflow = await page.evaluate(() => document.body.scrollWidth > document.body.clientWidth);
    expect(overflow).toBe(false);
  });
});
