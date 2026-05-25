import { expect, test } from '@playwright/test';

const baseUrl = 'http://127.0.0.1:8000';

function extractSurvivorScores(text: string): [number, number] {
  const values = Array.from(text.matchAll(/(\d+)\s+survivors/gi)).map((match) => Number(match[1]));
  expect(values, `expected two survivor counts in aftermath hero, got: ${text}`).toHaveLength(2);
  return [values[0], values[1]];
}

test('replay header keeps the final survivor score visible from the first frame', async ({ page, request }) => {
  const saveName = `e2e-replay-score-${Date.now()}`;
  const create = await request.post(`${baseUrl}/api/saves/new`, {
    data: { name: saveName, club_id: 'aurora' },
  });
  expect(create.ok()).toBeTruthy();

  await page.goto(`${baseUrl}/?tab=command`);
  await expect(page.getByTestId('weekly-command-center')).toBeVisible();

  await page.getByTestId('lock-weekly-plan').click();
  await expect(page.getByTestId('simulate-command-week')).toBeEnabled();
  await page.getByTestId('simulate-command-week').click();

  await expect(page.getByTestId('post-week-dashboard')).toBeVisible({ timeout: 20000 });
  await page.keyboard.press('Space');

  const [homeSurvivors, awaySurvivors] = extractSurvivorScores(
    await page.getByTestId('match-score-hero').innerText(),
  );

  await page.getByRole('button', { name: /view full replay/i }).click();
  await expect(
    page.getByText(new RegExp(`^${homeSurvivors}\\s*[—-]\\s*${awaySurvivors}$`)),
  ).toBeVisible();
});
