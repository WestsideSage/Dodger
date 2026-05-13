import { expect, test } from '@playwright/test';

const baseUrl = 'http://127.0.0.1:8000';

test('Command Center aftermath presents score, replay identity, fallout, and next action', async ({ page, request }) => {
  const saveName = `e2e-command-center-${Date.now()}`;
  const create = await request.post(`${baseUrl}/api/saves/new`, {
    data: { name: saveName, club_id: 'aurora' },
  });
  expect(create.ok()).toBeTruthy();

  await page.goto(`${baseUrl}/?tab=command`);
  await expect(page.getByTestId('weekly-command-center')).toBeVisible();

  await page.getByRole('button', { name: 'Confirm Plan' }).click();
  await expect(page.getByTestId('simulate-command-week')).toBeEnabled();
  await page.getByTestId('simulate-command-week').click();

  await expect(page.getByTestId('post-week-dashboard')).toBeVisible({ timeout: 20000 });
  await page.keyboard.press('Space');

  await expect(page.getByTestId('match-score-hero')).toBeVisible();
  await expect(page.getByTestId('replay-timeline')).toBeVisible();
  await expect(page.getByTestId('key-players-panel')).toBeVisible();
  await expect(page.getByTestId('tactical-summary')).toBeVisible();
  await expect(page.getByTestId('fallout-grid')).toBeVisible();
  await expect(page.getByTestId('after-action-bar')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Watch Replay' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Advance to Next Week ->' })).toBeVisible();
});
