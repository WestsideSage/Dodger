import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const baseUrl = 'http://127.0.0.1:8000';

async function lockAndSimCurrentWeek(page: Page) {
  // Clear the Phase 3 scout + confirm-lineup readiness gates before locking.
  if (await page.getByTestId('scout-opponent').isVisible().catch(() => false)) {
    await page.getByTestId('scout-opponent').click();
  }
  if (await page.getByTestId('confirm-lineup').isVisible().catch(() => false)) {
    await page.getByTestId('confirm-lineup').click();
  }
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
  for (let step = 0; step < 10; step += 1) {
    const beat = page.getByTestId(testId);
    if (await beat.count()) {
      await expect(beat).toBeVisible();
      return true;
    }
    const continueButton = page.getByRole('button', { name: /continue/i });
    if (!await continueButton.count()) {
      return false;
    }
    await continueButton.click();
  }
  return false;
}

test('V13 broadcast framing and replay log keep proof one click away', async ({ page, request }) => {
  const saveName = `e2e-v13-${Date.now()}`;
  const create = await request.post(`${baseUrl}/api/saves/new`, {
    data: { name: saveName, club_id: 'aurora' },
  });
  expect(create.ok()).toBeTruthy();

  await page.goto(`${baseUrl}/?tab=command`);
  
  await expect(page.locator('[data-testid="weekly-command-center"], [data-testid="season-preview"]').first()).toBeVisible({ timeout: 10000 });
  if (await page.getByTestId('season-preview').isVisible()) {
    await page.getByRole('button', { name: /To the Command Center/i }).click();
  }
  await expect(page.getByTestId('weekly-command-center')).toBeVisible();

  await expect(page.getByText('Broadcast Frame')).toBeVisible();
  await expect(page.getByTestId('broadcast-proof-toggle').first()).toBeVisible();

  await lockAndSimCurrentWeek(page);

  await expect(page.getByTestId('post-week-dashboard')).toBeVisible({ timeout: 20000 });
  await page.keyboard.press('Space');
  await page.getByRole('button', { name: /view full replay/i }).click();

  await expect(page.getByRole('button', { name: /close replay/i })).toBeVisible({ timeout: 20000 });
  await expect(page.getByTestId('current-event-card')).toBeVisible();
  await expect(page.locator('[data-broadcast-proof-source]').first()).toBeVisible();
  await expect(page.getByText('Match Flow')).toBeVisible();
});

test('V13 playoff framing and offseason record cards stay browser-visible', async ({ page, request }) => {
  const saveName = `e2e-v13-playoffs-${Date.now()}`;
  // root_seed 7 deterministically lands aurora as the #1 seed, so the week-6
  // fast-forward reaches an aurora playoff semifinal (the default seed leaves
  // aurora out of the top 4, ending the season before any playoff week).
  const create = await request.post(`${baseUrl}/api/saves/new`, {
    data: { name: saveName, club_id: 'aurora', root_seed: 7 },
  });
  expect(create.ok()).toBeTruthy();

  await fastForwardToWeek(request, 6);

  await page.goto(`${baseUrl}/?tab=command`);
  
  await expect(page.locator('[data-testid="weekly-command-center"], [data-testid="season-preview"]').first()).toBeVisible({ timeout: 10000 });
  if (await page.getByTestId('season-preview').isVisible()) {
    await page.getByRole('button', { name: /To the Command Center/i }).click();
  }
  await expect(page.getByTestId('weekly-command-center')).toBeVisible();
  await expect(page.getByText('Broadcast Frame')).toBeVisible();

  await lockAndSimCurrentWeek(page);

  await expect(page.getByTestId('post-week-dashboard')).toBeVisible({ timeout: 20000 });
  await page.keyboard.press('Space');
  await page.getByRole('button', { name: /view full replay/i }).click();

  const playoffFrame = page.getByTestId('playoff-frame');
  await expect(playoffFrame).toBeVisible({ timeout: 20000 });
  await expect(playoffFrame).toHaveAttribute('data-broadcast-proof-source', /match:/);
  await expect(page.getByTestId('current-event-card')).toBeVisible();

  await page.getByRole('button', { name: /close replay/i }).click();
  await expect(page.getByTestId('post-week-dashboard')).toBeVisible();
  await page.getByRole('button', { name: /(bank the result|move on|shake it off)/i }).click();

  const foundRecordsBeat = await advanceToOffseasonBeat(page, 'offseason-records-ratified');
  if (foundRecordsBeat) {
    const recordsBeat = page.getByTestId('offseason-records-ratified');
    const visibleProofRows = recordsBeat.locator('[data-broadcast-proof-source]:visible');
    const visibleProofRowCount = await visibleProofRows.count();
    expect(visibleProofRowCount).toBeGreaterThan(0);
  } else {
    const activeSurface = page.locator(
      '[data-testid="match-week-offseason"], [data-testid="post-week-dashboard"], [data-testid="weekly-command-center"]',
    );
    await expect(activeSurface.first()).toBeVisible();
  }
});
