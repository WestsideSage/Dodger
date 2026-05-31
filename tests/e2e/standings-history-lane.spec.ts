import { expect, test } from '@playwright/test';

const baseUrl = 'http://127.0.0.1:8000';

test('standings rows expand into an inline club history lane', async ({ page, request }) => {
  const saveName = `e2e-standings-history-${Date.now()}`;
  const create = await request.post(`${baseUrl}/api/saves/new`, {
    data: { name: saveName, club_id: 'aurora' },
  });
  expect(create.ok()).toBeTruthy();

  await page.goto(`${baseUrl}/?tab=standings`);

  const auroraRow = page.getByRole('button', { name: 'Open Aurora Sentinels program history' });
  await expect(auroraRow).toBeVisible();

  await auroraRow.click();

  await expect(page.getByRole('button', { name: 'Close' })).toBeVisible();
  await expect(page.getByText('Archive Through')).toBeVisible();
  await expect(page.getByText('Current Record')).toBeVisible();
  await expect(page.getByText('Program Identity', { exact: true })).toBeVisible();
});
