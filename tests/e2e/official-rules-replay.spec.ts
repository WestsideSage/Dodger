import { expect, test } from '@playwright/test';
import { launchTokenHeaders } from './_token';

const baseUrl = 'http://127.0.0.1:8000';

test('official rules replay surfaces rules state and explanation panels', async ({ page, request }) => {
  const saveName = `e2e-official-replay-${Date.now()}`;
  const create = await request.post(`${baseUrl}/api/saves/new`, {
    headers: await launchTokenHeaders(request),
    data: {
      name: saveName,
      club_id: 'aurora',
      ruleset_selection: 'official_foam',
    },
  });
  expect(create.ok()).toBeTruthy();

  await page.goto(`${baseUrl}/?tab=command`);
  
  await expect(page.locator('[data-testid="weekly-command-center"], [data-testid="season-preview"]').first()).toBeVisible({ timeout: 10000 });
  if (await page.getByTestId('season-preview').isVisible()) {
    await page.getByRole('button', { name: /To the Command Center/i }).click();
  }
  await expect(page.getByTestId('weekly-command-center')).toBeVisible();

  if (await page.getByTestId('scout-opponent').isVisible().catch(() => false)) {
    await page.getByTestId('scout-opponent').click();
  }
  if (await page.getByTestId('confirm-lineup').isVisible().catch(() => false)) {
    await page.getByTestId('confirm-lineup').click();
  }
  await page.getByTestId('lock-weekly-plan').click();
  await expect(page.getByTestId('simulate-command-week')).toBeEnabled();
  await page.getByTestId('simulate-command-week').click();

  await expect(page.getByTestId('post-week-dashboard')).toBeVisible({ timeout: 20000 });
  await page.keyboard.press('Space');

  await page.getByRole('button', { name: /view full replay/i }).click();
  await expect(page.getByTestId('official-ruleset-banner')).toBeVisible();
  await expect(page.getByText('GAME CLOCK', { exact: true })).toBeVisible();
  await expect(page.getByText('MATCH CLOCK', { exact: true })).toBeVisible();
  await expect(page.getByText('BURDEN', { exact: true })).toBeVisible();
  await expect(page.getByText('BALL STATES', { exact: true })).toBeVisible();
  await expect(page.getByText('RULE CALLS', { exact: true })).toBeVisible();
});
