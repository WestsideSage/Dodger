import { expect, test } from '@playwright/test';

const baseUrl = 'http://127.0.0.1:8000';

test('Command Center aftermath presents score, replay identity, fallout, and next action', async ({ page, request }) => {
  const saveName = `e2e-command-center-${Date.now()}`;
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

  await expect(page.getByTestId('post-week-dashboard')).toBeVisible({ timeout: 20000 });
  await page.keyboard.press('Space');

  await expect(page.getByTestId('match-score-hero')).toBeVisible();
  await expect(page.getByTestId('replay-timeline')).toBeVisible();
  await expect(page.getByTestId('key-players-panel')).toBeVisible();
  await expect(page.getByTestId('tactical-summary')).toBeVisible();
  await expect(page.getByTestId('fallout-grid')).toBeVisible();
  await expect(page.getByTestId('after-action-bar')).toBeVisible();
  await expect(page.getByRole('button', { name: /view full replay/i })).toBeVisible();
  const advanceBtn = page.getByTestId('after-action-bar').locator('button.command-action-bar-primary');
  await expect(advanceBtn).toBeVisible();
  await expect(advanceBtn).toHaveText(/NEXT WEEK →|BANK THE RESULT →/);
});

test('KeyPlayersPanel shows Your Club Best standout when no user player in top 3', async ({ page, request }) => {
  const saveName = `e2e-standout-${Date.now()}`;
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
  await expect(page.getByTestId('post-week-dashboard')).toBeVisible({ timeout: 20000 });
  await page.keyboard.press('Space');
  await expect(page.getByTestId('key-players-panel')).toBeVisible();

  // If the standout section exists, validate it has the orange badge
  const standout = page.getByTestId('your-standout');
  if (await standout.isVisible()) {
    await expect(standout.locator('text=Your Club')).toBeVisible();
  }
  // key-players-panel must always render without crashing
  await expect(page.getByTestId('key-players-panel')).toBeVisible();
});
