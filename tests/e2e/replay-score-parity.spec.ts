import { expect, test } from '@playwright/test';
import { launchTokenHeaders } from './_token';

const baseUrl = 'http://127.0.0.1:8000';

// Post-WT-2, official matches lead the aftermath hero with GAME POINTS (a
// 0-0 official draw must not read 0-3); generic/legacy matches still lead
// with survivors. This spec had only ever run against a pre-guard server
// (tokenless setup), so it still pinned the survivor-led hero text.

test('replay header keeps the final survivor score visible from the first frame', async ({ page, request }) => {
  const saveName = `e2e-replay-score-${Date.now()}`;
  const create = await request.post(`${baseUrl}/api/saves/new`, {
    headers: await launchTokenHeaders(request),
    data: { name: saveName, club_id: 'aurora' },
  });
  expect(create.ok()).toBeTruthy();

  await page.goto(`${baseUrl}/?tab=command`);
  
  await expect(page.locator('[data-testid="weekly-command-center"], [data-testid="season-preview"]').first()).toBeVisible({ timeout: 10000 });
  if (await page.getByTestId('season-preview').isVisible()) {
    await page.getByRole('button', { name: /To the Command Center/i }).click();
  }
  await expect(page.getByTestId('weekly-command-center')).toBeVisible();

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

  const hero = page.getByTestId('match-score-hero');
  await expect(hero).toBeVisible();
  // The hero's headline numbers count up from 0 over ~1.5s — let the
  // animation settle before reading, or the parity check races it.
  await page.waitForTimeout(2000);
  const numberTexts = await hero.locator('.command-score-number').allInnerTexts();
  expect(numberTexts, 'hero must show exactly two headline scores').toHaveLength(2);
  const home = Number(numberTexts[0]);
  const away = Number(numberTexts[1]);
  // The per-side detail caption names the unit: "game points" (official) or
  // "N survivors" (generic/legacy).
  const detail = (await hero.locator('.command-score-detail').first().innerText()).toLowerCase();
  const marginUnit = detail.includes('game points') ? 'GAME PTS' : 'SURVIVORS';

  await page.getByRole('button', { name: /view full replay/i }).click();
  const replayScoreboard = page.locator('.mr-scoreboard');
  await expect(replayScoreboard).toBeVisible();
  // Parity: the replay margin badge uses the same unit the hero led with
  // and the same final margin, from the first frame.
  await expect(
    replayScoreboard.getByText(`+${Math.abs(home - away)} ${marginUnit}`),
  ).toBeVisible();
  await expect(page.getByTestId('current-event-card')).toBeVisible();
  await expect(page.getByText('Current Event')).toBeVisible();
});
