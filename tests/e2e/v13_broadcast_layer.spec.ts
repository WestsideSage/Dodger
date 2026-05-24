import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const baseUrl = 'http://127.0.0.1:8000';

async function lockAndSimCurrentWeek(page: Page) {
  await page.getByTestId('lock-weekly-plan').click();
  await expect(page.getByTestId('simulate-command-week')).toBeEnabled();
  await page.getByTestId('simulate-command-week').click();
}

async function fastForwardToWeek(request: APIRequestContext, week: number) {
  for (let currentWeek = 1; currentWeek < week; currentWeek += 1) {
    const center = await request.get(`${baseUrl}/api/command-center`);
    expect(center.ok()).toBeTruthy();
    const plan = await center.json();
    const sim = await request.post(`${baseUrl}/api/command-center/simulate`, {
      data: { intent: plan.plan.intent },
    });
    expect(sim.ok()).toBeTruthy();
  }
}

async function advanceToOffseasonBeat(page: Page, testId: string) {
  for (let step = 0; step < 6; step += 1) {
    const beat = page.getByTestId(testId);
    if (await beat.count()) {
      await expect(beat).toBeVisible();
      return;
    }
    await page.getByRole('button', { name: /continue/i }).click();
  }
  await expect(page.getByTestId(testId)).toBeVisible();
}

test('V13 broadcast framing and highlights keep proof one click away', async ({ page, request }) => {
  const saveName = `e2e-v13-${Date.now()}`;
  const create = await request.post(`${baseUrl}/api/saves/new`, {
    data: { name: saveName, club_id: 'aurora' },
  });
  expect(create.ok()).toBeTruthy();

  await page.goto(`${baseUrl}/?tab=command`);
  await expect(page.getByTestId('weekly-command-center')).toBeVisible();

  await expect(page.getByText('Broadcast Frame')).toBeVisible();
  await expect(page.getByTestId('broadcast-proof-toggle').first()).toBeVisible();

  await lockAndSimCurrentWeek(page);

  await expect(page.getByTestId('post-week-dashboard')).toBeVisible({ timeout: 20000 });
  await page.keyboard.press('Space');
  await page.getByRole('button', { name: /view full replay/i }).click();

  await expect(page.getByRole('button', { name: /back to results/i })).toBeVisible({ timeout: 20000 });
  await expect(page.getByRole('button', { name: 'HIGHLIGHTS' })).toBeVisible();
  const timelineButtons = page.getByRole('button', { name: /show in timeline/i });
  await expect(timelineButtons.first()).toBeVisible();
  expect(await timelineButtons.count()).toBeGreaterThanOrEqual(4);
  await expect(page.locator('[data-broadcast-proof-source]').first()).toBeVisible();

  await timelineButtons.first().click();
  await expect(page.getByText('PLAY-BY-PLAY')).toBeVisible();
  await expect(page.getByText('PLAY 1').first()).toBeVisible();
});

test('V13 playoff framing and offseason record cards stay browser-visible', async ({ page, request }) => {
  const saveName = `e2e-v13-playoffs-${Date.now()}`;
  const create = await request.post(`${baseUrl}/api/saves/new`, {
    data: { name: saveName, club_id: 'aurora' },
  });
  expect(create.ok()).toBeTruthy();

  await fastForwardToWeek(request, 6);

  await page.goto(`${baseUrl}/?tab=command`);
  await expect(page.getByTestId('weekly-command-center')).toBeVisible();
  await expect(page.getByText('Broadcast Frame')).toBeVisible();

  await lockAndSimCurrentWeek(page);

  await expect(page.getByTestId('post-week-dashboard')).toBeVisible({ timeout: 20000 });
  await page.keyboard.press('Space');
  await page.getByRole('button', { name: /view full replay/i }).click();

  const playoffFrame = page.getByTestId('playoff-frame');
  await expect(playoffFrame).toBeVisible({ timeout: 20000 });
  await expect(playoffFrame).toHaveAttribute('data-broadcast-proof-source', /match:/);
  await expect(page.getByRole('button', { name: 'HIGHLIGHTS' })).toBeVisible();

  await page.getByRole('button', { name: /back to results/i }).click();
  await expect(page.getByTestId('post-week-dashboard')).toBeVisible();
  await page.getByRole('button', { name: /(bank the result|move on|shake it off)/i }).click();

  await advanceToOffseasonBeat(page, 'offseason-records-ratified');
  await expect(page.getByTestId('offseason-records-ratified').locator('[data-broadcast-proof-source]').first()).toBeVisible();
  await expect(page.getByTestId('offseason-records-ratified').locator('[data-testid=\"broadcast-proof-toggle\"]').first()).toBeVisible();
});
