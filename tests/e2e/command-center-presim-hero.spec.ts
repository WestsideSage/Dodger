import { expect, test } from '@playwright/test';
import { launchTokenHeaders } from './_token';

const baseUrl = 'http://127.0.0.1:8000';

test('Command Center pre-sim keeps the core dashboard surfaces visible', async ({ page, request }) => {
  const saveName = `e2e-command-center-presim-${Date.now()}`;
  const create = await request.post(`${baseUrl}/api/saves/new`, {
    headers: await launchTokenHeaders(request),
    data: { name: saveName, club_id: 'aurora' },
  });
  expect(create.ok()).toBeTruthy();

  await page.setViewportSize({ width: 2048, height: 633 });
  await page.goto(`${baseUrl}/?tab=command`);

  await expect(page.locator('[data-testid="weekly-command-center"], [data-testid="season-preview"]').first()).toBeVisible({ timeout: 10000 });
  if (await page.getByTestId('season-preview').isVisible()) {
    await page.getByRole('button', { name: /To the Command Center/i }).click();
  }
  await expect(page.getByTestId('weekly-command-center')).toBeVisible();
  await expect(page.getByTestId('presim-command-strip')).toBeVisible();
  await expect(page.getByText('WAR ROOM', { exact: true })).toHaveCount(1);
  await expect(page.getByRole('heading', { name: 'Command Center' })).toHaveCount(1);
  await expect(page.getByTestId('plan-editor-panel')).toBeVisible();
  await expect(page.getByText('Tactical Approach', { exact: true })).toBeVisible();
  await expect(page.getByTestId('plan-editor-panel').getByText('Training', { exact: true })).toBeVisible();
  await expect(page.getByText('Development', { exact: true })).toBeVisible();
  await expect(page.getByTestId('scout-read-panel')).toBeVisible();
  await expect(page.getByTestId('readiness-panel')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Lock Plan' })).toBeVisible();
  await expect(page.getByTestId('secondary-intel-rail')).toBeVisible();

  await expect(page.getByTestId('plan-readout')).toBeVisible();

  // D3: scout is a deliberate-action gate that starts UNMET on a fresh save and
  // is cleared only by a real scout action — so clear it before asserting the
  // reviewed title (mirrors command-center-aftermath / official-rules-replay).
  if (await page.getByTestId('scout-opponent').isVisible().catch(() => false)) {
    await page.getByTestId('scout-opponent').click();
  }

  const scoutChip = page.getByTestId('readiness-panel').locator('.command-readiness-chips .cc-gate').first();
  await expect(scoutChip).toHaveAttribute(
    'title',
    'Opponent lineup reviewed.',
  );

  const rawThreatRows = page.locator('.command-threat-row');
  await expect(rawThreatRows).toHaveCount(1);
  await expect(page.locator('.command-threat-card')).toHaveCount(0);
});
