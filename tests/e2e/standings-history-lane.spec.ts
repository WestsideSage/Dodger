import { expect, test } from '@playwright/test';

const baseUrl = 'http://127.0.0.1:8000';

test('standings rows expand into an inline club history lane', async ({ page, request }) => {
  const saveName = `e2e-standings-history-${Date.now()}`;
  const create = await request.post(`${baseUrl}/api/saves/new`, {
    data: { name: saveName, club_id: 'aurora' },
  });
  expect(create.ok()).toBeTruthy();

  await page.goto(`${baseUrl}/?tab=standings`);

  const auroraRow = page.getByRole('button', { name: /View Aurora .* history/ });
  await expect(auroraRow).toBeVisible();
  await expect(auroraRow).toHaveAttribute('aria-expanded', 'false');

  await auroraRow.click();

  await expect(page.getByRole('button', { name: /Hide Aurora .* history/ })).toHaveAttribute('aria-expanded', 'true');
  await expect(page.getByText('Club History')).toBeVisible();
  await expect(page.getByText(/season record/i)).toBeVisible();
  await expect(page.getByText(/Current plan:/i)).toBeVisible();
});
