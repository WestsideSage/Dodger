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
  // V23 witness (re-derived for the 28-club pyramid): root_seed 12
  // deterministically lands aurora as the Premier League #1 seed, so the
  // week-8 fast-forward (7 regular weeks + semis) reaches an aurora playoff
  // semifinal. (Pre-V23 this fixture was root_seed 7 / week 6 on the flat
  // 6-club league.)
  const create = await request.post(`${baseUrl}/api/saves/new`, {
    headers: await launchTokenHeaders(request),
    data: { name: saveName, club_id: 'aurora', root_seed: 12 },
  });
  expect(create.ok()).toBeTruthy();

  await fastForwardToWeek(request, 8);

  await page.goto(`${baseUrl}/?tab=command`);
  const commandStrip = page.getByTestId('presim-command-strip');

  await expect(commandStrip).toBeVisible();
  await expect(commandStrip.getByText('Record')).toBeVisible();
  await expect(commandStrip.getByText('Form')).toHaveCount(0);
});
