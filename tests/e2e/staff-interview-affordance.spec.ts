import { expect, test } from '@playwright/test';

const baseUrl = 'http://127.0.0.1:8000';

test('staff candidates expose a hire action with visible state', async ({ page, request }) => {
  const saveName = `e2e-staff-interview-${Date.now()}`;
  const create = await request.post(`${baseUrl}/api/saves/new`, {
    data: { name: saveName, club_id: 'aurora' },
  });
  expect(create.ok()).toBeTruthy();

  await page.goto(`${baseUrl}/?tab=dynasty&subtab=staff`);

  await expect(page.getByRole('heading', { name: 'Candidates' })).toBeVisible();
  await expect(page.getByText(/available/i).first()).toBeVisible();

  const hire = page.getByRole('button', { name: 'Hire' }).first();
  await expect(hire).toBeVisible();
  await hire.click();

  await expect(page.getByText(/recent staff moves/i)).toBeVisible();
});
