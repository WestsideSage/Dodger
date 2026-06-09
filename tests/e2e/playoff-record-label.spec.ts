import { expect, test, type APIRequestContext } from '@playwright/test';
import { launchTokenHeaders } from './_token';

const baseUrl = 'http://127.0.0.1:8000';

async function fastForwardToWeek(request: APIRequestContext, week: number) {
  for (let currentWeek = 1; currentWeek < week; currentWeek += 1) {
    const center = await request.get(`${baseUrl}/api/command-center`);
    expect(center.ok()).toBeTruthy();
    const plan = await center.json();
    const sim = await request.post(`${baseUrl}/api/command-center/simulate`, {
      headers: await launchTokenHeaders(request),
      data: { intent: plan.plan.intent },
    });
    expect(sim.ok()).toBeTruthy();
  }
}

test('playoff command strip labels regular-season record instead of recent form', async ({ page, request }) => {
  const saveName = `e2e-playoff-record-label-${Date.now()}`;
  // root_seed 7 deterministically lands aurora as the #1 seed, so the week-6
  // fast-forward reaches an aurora playoff semifinal (the default seed leaves
  // aurora out of the top 4, ending the season before any playoff week).
  const create = await request.post(`${baseUrl}/api/saves/new`, {
    headers: await launchTokenHeaders(request),
    data: { name: saveName, club_id: 'aurora', root_seed: 7 },
  });
  expect(create.ok()).toBeTruthy();

  await fastForwardToWeek(request, 6);

  await page.goto(`${baseUrl}/?tab=command`);
  const commandStrip = page.getByTestId('presim-command-strip');

  await expect(commandStrip).toBeVisible();
  await expect(commandStrip.getByText('Record')).toBeVisible();
  await expect(commandStrip.getByText('Form')).toHaveCount(0);
});
