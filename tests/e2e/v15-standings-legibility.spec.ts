import { test, expect } from '@playwright/test';
import { launchTokenHeaders } from './_token';

const baseUrl = 'http://127.0.0.1:8000';

test.describe('v15-p2d standings legibility', () => {
  test.beforeEach(async ({ request }) => {
    // Create a save so we have a fresh career and standings
    const saveName = `e2e-standings-p2d-${Date.now()}`;
    const create = await request.post(`${baseUrl}/api/saves/new`, {
      headers: await launchTokenHeaders(request),
      data: { name: saveName, club_id: 'aurora' },
    });
    expect(create.ok()).toBeTruthy();
  });

  test('standings row click opens program modal', async ({ page }) => {
    await page.goto(`${baseUrl}/?tab=standings`);

    // Wait for the standings table to be visible.
    const table = page.locator('[data-testid="standings-table"]');
    await expect(table).toBeVisible();

    // Click the first non-cut-line row.
    const firstRow = page.locator('[data-testid="standings-table"] tbody tr[role="button"]').first();
    await firstRow.click();

    // ProgramModal should open — it uses the command-policy-overlay class.
    const modal = page.getByTestId('program-archive-modal');
    await expect(modal).toBeVisible();

    // The modal should show the League Archive kicker. "League Archive" is unique
    // to the ProgramModal header (MyProgramView's inner kickers are season labels),
    // so a modal-scoped text assertion is stable across the CSS-Modules reskin.
    await expect(modal).toContainText('League Archive');

    // Close with Escape.
    await page.keyboard.press('Escape');
    await expect(modal).not.toBeVisible();
  });

  test('standings row click is keyboard operable', async ({ page }) => {
    await page.goto(`${baseUrl}/?tab=standings`);
    const firstRow = page.locator('[data-testid="standings-table"] tbody tr[role="button"]').first();
    await firstRow.focus();
    await page.keyboard.press('Enter');
    await expect(page.getByTestId('program-archive-modal')).toBeVisible();
    await page.keyboard.press('Escape');
  });

  test('standings row has aria-haspopup dialog', async ({ page }) => {
    await page.goto(`${baseUrl}/?tab=standings`);
    const firstRow = page.locator('[data-testid="standings-table"] tbody tr[role="button"]').first();
    await expect(firstRow).toHaveAttribute('aria-haspopup', 'dialog');
  });

  test('table legend does not reference the > icon', async ({ page }) => {
    await page.goto(`${baseUrl}/?tab=standings`);
    const legend = page.locator('[data-testid="standings-legend"]');
    await expect(legend).toBeVisible();
    
    // The old legend said "Click any row >" — the new one does not use the > chevron.
    const legendText = await legend.innerText();
    expect(legendText).not.toMatch(/Click any row >/i);
    expect(legendText).toMatch(/program history/i);
  });

  test('Survivor Diff header has TermTip', async ({ page }) => {
    await page.goto(`${baseUrl}/?tab=standings`);
    // TermTip wraps the diff column header in a button with aria-label
    // "What is ${def.label}?". The label depends on the career's scoring model:
    // foam careers show "Differential" (standings.diff); official careers show
    // "Game-Point Differential" (standings.gp_diff). The intent of this test is
    // that the diff header IS an explained TermTip either way.
    const tip = page.getByRole('button', { name: /What is (Game-Point )?Differential\?/i });
    await expect(tip).toBeVisible();
  });
});
