import { test, expect } from '@playwright/test';

const baseUrl = 'http://127.0.0.1:8000';

test.describe('v15-p2d standings legibility', () => {
  test.beforeEach(async ({ request }) => {
    // Create a save so we have a fresh career and standings
    const saveName = `e2e-standings-p2d-${Date.now()}`;
    const create = await request.post(`${baseUrl}/api/saves/new`, {
      data: { name: saveName, club_id: 'aurora' },
    });
    expect(create.ok()).toBeTruthy();
  });

  test('standings row click opens program modal', async ({ page }) => {
    await page.goto(`${baseUrl}/?tab=standings`);

    // Wait for the standings table to be visible.
    const table = page.locator('.ls-table');
    await expect(table).toBeVisible();

    // Click the first non-cut-line row.
    const firstRow = page.locator('.ls-table tbody tr[role="button"]').first();
    await firstRow.click();

    // ProgramModal should open — it uses the command-policy-overlay class.
    const modal = page.locator('.command-policy-overlay');
    await expect(modal).toBeVisible();

    // The modal should show the League Archive kicker.
    // Scope to the header element to avoid matching inner kickers rendered by MyProgramView.
    await expect(modal.locator('.do-hist-modal-header .dm-kicker')).toContainText('League Archive');

    // Close with Escape.
    await page.keyboard.press('Escape');
    await expect(modal).not.toBeVisible();
  });

  test('standings row click is keyboard operable', async ({ page }) => {
    await page.goto(`${baseUrl}/?tab=standings`);
    const firstRow = page.locator('.ls-table tbody tr[role="button"]').first();
    await firstRow.focus();
    await page.keyboard.press('Enter');
    await expect(page.locator('.command-policy-overlay')).toBeVisible();
    await page.keyboard.press('Escape');
  });

  test('standings row has aria-haspopup dialog', async ({ page }) => {
    await page.goto(`${baseUrl}/?tab=standings`);
    const firstRow = page.locator('.ls-table tbody tr[role="button"]').first();
    await expect(firstRow).toHaveAttribute('aria-haspopup', 'dialog');
  });

  test('table legend does not reference the > icon', async ({ page }) => {
    await page.goto(`${baseUrl}/?tab=standings`);
    const legend = page.locator('.ls-table-foot');
    await expect(legend).toBeVisible();
    
    // The old legend said "Click any row >" — the new one does not use the > chevron.
    const legendText = await legend.innerText();
    expect(legendText).not.toMatch(/Click any row >/i);
    expect(legendText).toMatch(/program history/i);
  });

  test('Survivor Diff header has TermTip', async ({ page }) => {
    await page.goto(`${baseUrl}/?tab=standings`);
    // TermTip wraps children in a button with aria-label "What is ${def.label}?".
    // The term standings.diff has label "Differential" (from terms.ts Phase 1 seed),
    // so the button's aria-label is "What is Differential?" — NOT "What is Survivor Diff?".
    const tip = page.getByRole('button', { name: /What is Differential\?/i });
    await expect(tip).toBeVisible();
  });
});
