import { expect, test, type Page, type APIRequestContext } from '@playwright/test';
import { launchTokenHeaders } from './_token';

const baseUrl = 'http://127.0.0.1:8000';

async function ensureSaveMenu(page: Page, request: APIRequestContext) {
  await request.post(`${baseUrl}/api/saves/unload`, { headers: await launchTokenHeaders(request) });
  await page.goto(baseUrl);
  await expect(page.getByTestId('save-menu')).toBeVisible();
}

test('build-from-scratch identity fields expose real label associations', async ({ page, request }) => {
  await ensureSaveMenu(page, request);

  await page.getByTestId('new-game-tab').click();
  await page.locator('button:has-text("Build from Scratch")').click();

  const orphanLabels = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('label'))
      .map((label) => {
        const htmlFor = label.getAttribute('for');
        const target = htmlFor ? document.getElementById(htmlFor) : null;
        return {
          text: label.textContent?.trim() ?? '',
          hasControlDescendant: Boolean(label.querySelector('input, select, textarea')),
          hasTarget: Boolean(target),
        };
      })
      .filter((label) => Boolean(label.text) && !label.hasControlDescendant && !label.hasTarget)
      .map((label) => label.text);
  });

  expect(orphanLabels).toEqual([]);
});

test('roster stays inside a 390px viewport without horizontal scrolling', async ({ page, request }) => {
  const saveName = `e2e-roster-mobile-${Date.now()}`;
  const create = await request.post(`${baseUrl}/api/saves/new`, {
    headers: await launchTokenHeaders(request),
    data: { name: saveName, club_id: 'aurora' },
  });
  expect(create.ok()).toBeTruthy();

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${baseUrl}/?tab=roster`);
  await expect(page.getByRole('heading', { name: /Team Roster/i })).toBeVisible();

  const hasHorizontalOverflow = await page.evaluate(() => {
    const root = document.documentElement;
    return root.scrollWidth > window.innerWidth;
  });

  expect(hasHorizontalOverflow).toBe(false);
});
