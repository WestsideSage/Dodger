import { expect, test } from '@playwright/test';

const baseUrl = 'http://127.0.0.1:8000';

test('Command Center pre-sim keeps the core dashboard above the fold', async ({ page, request }) => {
  const saveName = `e2e-command-center-presim-${Date.now()}`;
  const create = await request.post(`${baseUrl}/api/saves/new`, {
    data: { name: saveName, club_id: 'aurora' },
  });
  expect(create.ok()).toBeTruthy();

  await page.setViewportSize({ width: 2048, height: 633 });
  await page.goto(`${baseUrl}/?tab=command`);

  await expect(page.getByTestId('weekly-command-center')).toBeVisible();
  await expect(page.getByTestId('presim-command-strip')).toBeVisible();
  await expect(page.getByText('WAR ROOM', { exact: true })).toHaveCount(1);
  await expect(page.getByRole('heading', { name: 'Command Center' })).toHaveCount(1);
  await expect(page.getByTestId('plan-editor-panel')).toBeVisible();
  await expect(page.getByText('Tactical Approach', { exact: true })).toBeVisible();
  await expect(page.getByText('Training', { exact: true })).toBeVisible();
  await expect(page.getByText('Development', { exact: true })).toBeVisible();
  await expect(page.getByTestId('scout-read-panel')).toBeVisible();
  await expect(page.getByTestId('readiness-panel')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Lock Plan' })).toBeVisible();
  await expect(page.getByTestId('secondary-intel-rail')).toBeVisible();

  const foldCheck = await page.evaluate(() => {
    const selectors = [
      '[data-testid="presim-command-strip"]',
      '[data-testid="plan-editor-panel"]',
      '[data-testid="scout-read-panel"]',
      '[data-testid="readiness-panel"]',
    ];
    return selectors.map(selector => {
      const rect = document.querySelector(selector)?.getBoundingClientRect();
      return {
        selector,
        bottom: rect?.bottom ?? Number.POSITIVE_INFINITY,
        viewportHeight: window.innerHeight,
      };
    });
  });

  expect(foldCheck.every(item => item.bottom <= item.viewportHeight)).toBeTruthy();

  const desktopScroll = await page.evaluate(() => ({
    scrollHeight: document.documentElement.scrollHeight,
    viewportHeight: window.innerHeight,
  }));
  expect(desktopScroll.scrollHeight).toBeLessThanOrEqual(desktopScroll.viewportHeight);

  await expect(page.getByTestId('plan-readout')).toBeVisible();

  const scoutChip = page.getByTestId('readiness-panel').locator('.command-readiness-chips span').first();
  await expect(scoutChip).toHaveAttribute(
    'title',
    'Scout report, threat profile, and staff recommendation available.',
  );

  const rawThreatRows = page.getByTestId('scout-read-panel').locator('.command-threat-row');
  await expect(rawThreatRows).toHaveCount(1);
  await expect(page.locator('.command-threat-card')).toHaveCount(0);
});
