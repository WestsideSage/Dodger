import { expect, test } from '@playwright/test';
import { launchTokenHeaders } from './_token';

const baseUrl = 'http://127.0.0.1:8000';

test('AI Program Managers E2E Standings rendering', async ({ page, request }) => {
  const saveName = `e2e-v12-ai-program-${Date.now()}`;
  const create = await request.post(`${baseUrl}/api/saves/new`, {
    headers: await launchTokenHeaders(request),
    data: { name: saveName, club_id: 'aurora' },
  });
  expect(create.ok()).toBeTruthy();

  // Fetch the standings API directly and log the raw response
  const standingsResponse = await request.get(`${baseUrl}/api/standings`);
  const standingsData = await standingsResponse.json();
  console.log("STANDINGS API RESPONSE:", JSON.stringify(standingsData, null, 2));

  // Navigate to standings tab
  await page.goto(`${baseUrl}/?tab=standings`);

  // Wait for the standings table to load
  await expect(page.locator('table.ls-table')).toBeVisible();

  // Verify standings headers and context callout are visible
  await expect(page.getByRole('heading', { name: 'Standings', level: 1 })).toBeVisible();
  
  // Verify that the user club row displays the archetype info
  const userRow = page.locator('tr').filter({ hasText: 'Aurora' });
  await expect(userRow).toBeVisible();
  
  // Assert presence of the current program trajectory/plan info on the row
  await expect(userRow.locator('text=Yr 1')).toBeVisible();
  await expect(userRow.locator('text=Balanced')).toBeVisible();
});
