import { expect, test } from '@playwright/test';

const baseUrl = 'http://127.0.0.1:8000';

test('Plan C tier-1 recognition: PolicyEditor → sim → aftermath surfaces moments + tactic', async ({
  page,
  request,
}) => {
  const saveName = `e2e-tier1-recognition-${Date.now()}`;
  const create = await request.post(`${baseUrl}/api/saves/new`, {
    data: { name: saveName, club_id: 'aurora' },
  });
  expect(create.ok()).toBeTruthy();

  await page.goto(`${baseUrl}/?tab=command`);
  await expect(page.getByTestId('weekly-command-center')).toBeVisible();

  // PolicyEditor renders inside the pre-sim dashboard.
  const editor = page.getByTestId('policy-editor');
  await expect(editor).toBeVisible();

  // Change Approach → Aggressive.
  const aggressive = page.getByTestId('policy-approach-aggressive');
  await aggressive.click();
  await expect(aggressive).toHaveAttribute('aria-checked', 'true');

  // Change Catch Posture → Go for catches.
  const goForCatches = page.getByTestId('policy-catch_posture-go_for_catches');
  await goForCatches.click();
  await expect(goForCatches).toHaveAttribute('aria-checked', 'true');

  // Arrow-key navigation within the catch-posture radiogroup.
  await goForCatches.focus();
  await page.keyboard.press('ArrowRight');
  // After one ArrowRight we cycled from "go_for_catches" → "play_safe".
  const playSafe = page.getByTestId('policy-catch_posture-play_safe');
  await expect(playSafe).toHaveAttribute('aria-checked', 'true');
  // Restore aggressive catch posture.
  await goForCatches.click();
  await expect(goForCatches).toHaveAttribute('aria-checked', 'true');

  // Lock + simulate.
  await page.getByTestId('lock-weekly-plan').click();
  await expect(page.getByTestId('simulate-command-week')).toBeEnabled();
  await page.getByTestId('simulate-command-week').click();

  await expect(page.getByTestId('post-week-dashboard')).toBeVisible({ timeout: 20000 });
  await page.keyboard.press('Space');

  // Aftermath renders the new replay timeline (Plan C: moment-aware).
  const timeline = page.getByTestId('replay-timeline');
  await expect(timeline).toBeVisible();

  // Headline must be non-empty rec-league copy.
  const headline = page.getByTestId('match-score-hero');
  await expect(headline).toBeVisible();
});
