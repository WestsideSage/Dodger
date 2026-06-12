import { expect, test } from '@playwright/test';
import { launchTokenHeaders } from './_token';

const baseUrl = 'http://127.0.0.1:8000';

test('official rules replay surfaces rules state and explanation panels', async ({ page, request }) => {
  const saveName = `e2e-official-replay-${Date.now()}`;
  const create = await request.post(`${baseUrl}/api/saves/new`, {
    headers: await launchTokenHeaders(request),
    data: {
      name: saveName,
      club_id: 'aurora',
      ruleset_selection: 'official_foam',
    },
  });
  expect(create.ok()).toBeTruthy();

  await page.goto(`${baseUrl}/?tab=command`);
  
  await expect(page.locator('[data-testid="weekly-command-center"], [data-testid="season-preview"]').first()).toBeVisible({ timeout: 10000 });
  if (await page.getByTestId('season-preview').isVisible()) {
    await page.getByRole('button', { name: /To the Command Center/i }).click();
  }
  await expect(page.getByTestId('weekly-command-center')).toBeVisible();

  // V23: seven-club divisions schedule one bye per week, so the user's first
  // match is not always week 1 — sim forward until a real match week
  // produces a replay surface (max 3 weeks).
  let sawMatchWeek = false;
  for (let attempt = 0; attempt < 3 && !sawMatchWeek; attempt++) {
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
    sawMatchWeek = await page
      .getByRole('button', { name: /view full replay/i })
      .isVisible()
      .catch(() => false);
    if (!sawMatchWeek) {
      await page.getByRole('button', { name: /next week/i }).click();
      await expect(page.getByTestId('weekly-command-center')).toBeVisible({ timeout: 10000 });
    }
  }
  expect(sawMatchWeek, 'no real match week within 3 simulated weeks').toBeTruthy();

  await page.getByRole('button', { name: /view full replay/i }).click();
  await expect(page.getByTestId('official-ruleset-banner')).toBeVisible();
  await expect(page.getByText('GAME CLOCK', { exact: true })).toBeVisible();
  await expect(page.getByText('MATCH CLOCK', { exact: true })).toBeVisible();
  await expect(page.getByText('BURDEN', { exact: true })).toBeVisible();
  await expect(page.getByText('BALL STATES', { exact: true })).toBeVisible();
  await expect(page.getByText('RULE CALLS', { exact: true })).toBeVisible();

  // 2026-06-09 watchability pass: an official match is a series of games —
  // the replay must show the set-by-set story, and every set chip on a fresh
  // sim must jump (the event stream carries per-game metadata).
  const setStrip = page.getByTestId('replay-set-strip');
  await expect(setStrip).toBeVisible();
  const setChips = setStrip.locator('.mr-set-chip');
  expect(await setChips.count()).toBeGreaterThan(0);
  await expect(setChips.first()).toBeEnabled();
  await expect(page.getByTestId('replay-set-running')).toContainText('on game points');

  // The biggest-swing block jumps to the exact event its headline describes.
  await expect(page.getByText('BIGGEST SWING', { exact: true })).toBeVisible();
  const swingText = (await page.locator('.mr-turning-text').innerText()).trim();
  await page.getByRole('button', { name: /jump to this play/i }).click();
  await expect(page.locator('.mr-active-readout .title')).toHaveText(swingText);
});
