import { expect, test } from '@playwright/test';

const baseUrl = 'http://127.0.0.1:8000';

test('staff candidates expose an interview action with visible state', async ({ page, request }) => {
  const saveName = `e2e-staff-interview-${Date.now()}`;
  const create = await request.post(`${baseUrl}/api/saves/new`, {
    data: { name: saveName, club_id: 'aurora' },
  });
  expect(create.ok()).toBeTruthy();

  await page.goto(`${baseUrl}/?tab=dynasty&subtab=staff`);

  await expect(page.getByRole('heading', { name: 'Candidates' })).toBeVisible();
  await expect(page.getByText(/available/i).first()).toBeVisible();

  const interview = page.getByRole('button', { name: 'Interview' }).first();
  await expect(interview).toBeVisible();
  await interview.click();

  await expect(page.getByText(/recent staff moves/i)).toBeVisible();
});
