import { expect, test } from '@playwright/test';

const baseUrl = 'http://127.0.0.1:8000';

// V14 legibility hardening: a brand-new save must surface the pre-match
// Tactical Diff and Match-Day Staff panels, and the post-match Aftermath must
// surface the deterministic Primary Factor — all without breaking the existing
// Command Center -> simulate -> Replay flow.
test('V14 legibility: tactical diff + staff impact pre-sim, primary factor post-sim', async ({ page, request }) => {
  const saveName = `e2e-v14-legibility-${Date.now()}`;
  const create = await request.post(`${baseUrl}/api/saves/new`, {
    data: { name: saveName, club_id: 'aurora' },
  });
  expect(create.ok()).toBeTruthy();

  await page.goto(`${baseUrl}/?tab=command`);
  await expect(page.getByTestId('weekly-command-center')).toBeVisible();

  // Task 4: pre-match Tactical Diff renders with player plan rows; the opponent
  // column must be present (fog-of-war: shows real intel or "Unscouted").
  const tacticalDiff = page.getByTestId('tactical-diff');
  await expect(tacticalDiff).toBeVisible();
  await expect(tacticalDiff.getByTestId('tactical-diff-row').first()).toBeVisible();
  await expect(tacticalDiff.getByTestId('tactical-diff-player').first()).toBeVisible();
  await expect(tacticalDiff.getByTestId('tactical-diff-opponent').first()).toBeVisible();

  // Task 3: Match-Day Staff impact renders at least one department row.
  const staffImpact = page.getByTestId('staff-impact');
  await expect(staffImpact).toBeVisible();
  await expect(staffImpact.getByTestId('staff-impact-row').first()).toBeVisible();

  // Existing flow must remain intact: lock -> simulate -> aftermath.
  await page.getByTestId('lock-weekly-plan').click();
  await expect(page.getByTestId('simulate-command-week')).toBeEnabled();
  await page.getByTestId('simulate-command-week').click();

  await expect(page.getByTestId('post-week-dashboard')).toBeVisible({ timeout: 20000 });
  await page.keyboard.press('Space');

  // Task 1: deterministic Primary Factor surfaces in the aftermath.
  await expect(page.getByTestId('primary-factor')).toBeVisible();

  // Regression guard: the rest of the aftermath/replay flow still renders.
  await expect(page.getByTestId('match-score-hero')).toBeVisible();
  await expect(page.getByTestId('replay-timeline')).toBeVisible();
});
