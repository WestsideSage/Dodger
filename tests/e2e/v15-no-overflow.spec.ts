import { expect, test } from '@playwright/test';

const baseUrl = 'http://127.0.0.1:8000';
const MOBILE = { width: 390, height: 844 };

async function freshSave(request: import('@playwright/test').APIRequestContext): Promise<void> {
  const saveName = `e2e-v15-overflow-${Date.now()}`;
  const res = await request.post(`${baseUrl}/api/saves/new`, {
    data: { name: saveName, club_id: 'aurora' },
  });
  expect(res.ok()).toBeTruthy();
}

async function checkNoHorizontalOverflow(page: import('@playwright/test').Page): Promise<void> {
  const hasOverflow = await page.evaluate(() => {
    const root = document.documentElement;
    return root.scrollWidth > window.innerWidth;
  });
  expect(hasOverflow, `Horizontal overflow detected at 390px on ${page.url()}`).toBe(false);
}

// ---------------------------------------------------------------------------
// Phase 2a — Recruit Board
// ---------------------------------------------------------------------------
test('Recruit Board: no horizontal overflow at 390×844 (Phase 2a)', async ({ page, request }) => {
  await freshSave(request);
  await page.setViewportSize(MOBILE);
  await page.goto(`${baseUrl}/?tab=dynasty&subtab=recruiting`);
  await expect(page.getByTestId('prospect-card').first()).toBeVisible({ timeout: 10_000 });
  await checkNoHorizontalOverflow(page);
});

// ---------------------------------------------------------------------------
// Phase 2b — Roster
// ---------------------------------------------------------------------------
test('Roster: no horizontal overflow at 390×844 (Phase 2b)', async ({ page, request }) => {
  await freshSave(request);
  await page.setViewportSize(MOBILE);
  await page.goto(`${baseUrl}/?tab=roster`);
  await expect(page.getByRole('heading', { name: /Team Roster/i })).toBeVisible({ timeout: 10_000 });
  await checkNoHorizontalOverflow(page);
});

// ---------------------------------------------------------------------------
// Phase 2c — Lineup Editor
// ---------------------------------------------------------------------------
test('Lineup Editor: no horizontal overflow at 390×844 (Phase 2c)', async ({ page, request }) => {
  await freshSave(request);
  await page.setViewportSize(MOBILE);
  await page.goto(`${baseUrl}/?tab=command`);
  await expect(
    page.locator('[data-testid="weekly-command-center"], [data-testid="season-preview"]').first()
  ).toBeVisible({ timeout: 10_000 });
  if (await page.getByTestId('season-preview').isVisible()) {
    await page.getByRole('button', { name: /To the Command Center/i }).click();
  }
  await expect(page.getByTestId('weekly-command-center')).toBeVisible();
  // Open the lineup editor if it's behind a trigger button.
  const lineupEditorTrigger = page
    .getByRole('button', { name: /edit lineup|lineup editor/i })
    .or(page.getByTestId('open-lineup-editor'));
  if (await lineupEditorTrigger.first().isVisible().catch(() => false)) {
    await lineupEditorTrigger.first().click();
  }
  await checkNoHorizontalOverflow(page);
});

// ---------------------------------------------------------------------------
// Phase 2d — Standings
// ---------------------------------------------------------------------------
test('Standings: no horizontal overflow at 390×844 (Phase 2d)', async ({ page, request }) => {
  await freshSave(request);
  await page.setViewportSize(MOBILE);
  await page.goto(`${baseUrl}/?tab=standings`);
  await expect(
    page.getByRole('table').or(page.getByTestId('standings-table')).first()
  ).toBeVisible({ timeout: 10_000 });
  await checkNoHorizontalOverflow(page);
});

// ---------------------------------------------------------------------------
// Phase 3a — Dynasty Office / Credibility
// ---------------------------------------------------------------------------
test('Dynasty Office Credibility: no horizontal overflow at 390×844 (Phase 3a)', async ({ page, request }) => {
  await freshSave(request);
  await page.setViewportSize(MOBILE);
  await page.goto(`${baseUrl}/?tab=dynasty`);
  await expect(
    page.getByRole('heading', { name: /Dynasty Office|Program Credibility|Office/i }).first()
  ).toBeVisible({ timeout: 10_000 });
  await checkNoHorizontalOverflow(page);
});

// ---------------------------------------------------------------------------
// Phase 3b — Staff
// ---------------------------------------------------------------------------
test('Dynasty Office Staff: no horizontal overflow at 390×844 (Phase 3b)', async ({ page, request }) => {
  await freshSave(request);
  await page.setViewportSize(MOBILE);
  await page.goto(`${baseUrl}/?tab=dynasty&subtab=staff`);
  await expect(page.getByRole('heading', { name: 'Candidates' })).toBeVisible({ timeout: 10_000 });
  await checkNoHorizontalOverflow(page);
});

// ---------------------------------------------------------------------------
// Phase 3c — Season Preview
// ---------------------------------------------------------------------------
test('Season Preview: no horizontal overflow at 390×844 (Phase 3c)', async ({ page, request }) => {
  await freshSave(request);
  await page.setViewportSize(MOBILE);
  await page.goto(`${baseUrl}/?tab=command`);
  // Season Preview is shown before Week 1 is locked.
  await expect(
    page.locator('[data-testid="weekly-command-center"], [data-testid="season-preview"]').first()
  ).toBeVisible({ timeout: 10_000 });
  await checkNoHorizontalOverflow(page);
});

// ---------------------------------------------------------------------------
// Phase 4a — History
// ---------------------------------------------------------------------------
test('History (Program): no horizontal overflow at 390×844 (Phase 4a)', async ({ page, request }) => {
  await freshSave(request);
  await page.setViewportSize(MOBILE);
  await page.goto(`${baseUrl}/?tab=dynasty&subtab=history`);
  await expect(
    page.getByRole('heading', { name: /Program History|My Program|History/i }).first()
  ).toBeVisible({ timeout: 10_000 });
  await checkNoHorizontalOverflow(page);
});

// ---------------------------------------------------------------------------
// Phase 4b — App shell (nav + settings resolution)
// ---------------------------------------------------------------------------
test('App shell nav: no horizontal overflow at 390×844 (Phase 4b)', async ({ page, request }) => {
  await freshSave(request);
  await page.setViewportSize(MOBILE);
  await page.goto(`${baseUrl}/`);
  await expect(page.getByRole('navigation').first()).toBeVisible({ timeout: 10_000 });
  await checkNoHorizontalOverflow(page);
});
