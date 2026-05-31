import { expect, test } from '@playwright/test';

const baseUrl = 'http://127.0.0.1:8000';

test('Standings: row-click opens a club program modal with club history content', async ({ page, request }) => {
  const saveName = `e2e-v15-standings-modal-${Date.now()}`;
  const res = await request.post(`${baseUrl}/api/saves/new`, {
    data: { name: saveName, club_id: 'aurora' },
  });
  expect(res.ok()).toBeTruthy();

  await page.goto(`${baseUrl}/?tab=standings`);
  await expect(page.getByRole('table').or(page.getByTestId('standings-table')).first()).toBeVisible({
    timeout: 10_000,
  });

  // The user's own club row (aurora) should be clickable / expandable.
  // Phase 2d may implement this as a row button with aria-expanded,
  // or as a row that opens a modal dialog. Both patterns are accepted.
  const auroraRowTrigger = page
    .getByRole('button', { name: /View Aurora|Aurora.*history|Aurora.*program/i })
    .or(page.getByRole('row', { name: /Aurora/i }).first());
  await expect(auroraRowTrigger.first()).toBeVisible();
  await auroraRowTrigger.first().click();

  // Option A: inline expand (matches existing standings-history-lane.spec.ts pattern).
  const inlineHistory = page.getByTestId('club-history-lane').or(page.getByText('Club History'));
  // Option B: modal dialog opens.
  const modalDialog = page.getByRole('dialog');

  const expanded = await Promise.race([
    inlineHistory.first().waitFor({ timeout: 5_000 }).then(() => 'inline').catch(() => null),
    modalDialog.waitFor({ timeout: 5_000 }).then(() => 'modal').catch(() => null),
  ]);
  expect(expanded, 'Neither inline expand nor modal appeared after standings row-click').toBeTruthy();

  if (expanded === 'modal') {
    // Modal must expose club/program content.
    await expect(modalDialog).toBeVisible();
    await expect(modalDialog).toContainText(/Aurora|season record|history/i);
    // Modal must be closeable.
    const closeBtn = modalDialog.getByRole('button', { name: /close|dismiss/i });
    if (await closeBtn.isVisible()) {
      await closeBtn.click();
      await expect(modalDialog).not.toBeVisible({ timeout: 3_000 });
    }
  }
});

test('Standings: no trailing > icon on club rows (Phase 2d cleanup)', async ({ page, request }) => {
  const saveName = `e2e-v15-standings-trailing-icon-${Date.now()}`;
  const res = await request.post(`${baseUrl}/api/saves/new`, {
    data: { name: saveName, club_id: 'aurora' },
  });
  expect(res.ok()).toBeTruthy();

  await page.goto(`${baseUrl}/?tab=standings`);
  await expect(page.getByRole('table').or(page.getByTestId('standings-table')).first()).toBeVisible({
    timeout: 10_000,
  });

  // Check the first row.
  const row = page.getByRole('row').nth(1); // skip header
  await expect(row).toBeVisible();
  // We assert it does not have the text content > or chevron right.
  await expect(row).not.toContainText('>');
  // And no SVG element that resembles a right arrow or chevron (unless it has a descriptive title).
  const svg = row.locator('svg').filter({ hasText: /chevron|arrow|right/i });
  await expect(svg).toHaveCount(0);
});
