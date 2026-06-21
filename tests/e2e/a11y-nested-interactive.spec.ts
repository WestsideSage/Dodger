import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';
import { launchTokenHeaders } from './_token';

// Defaults to the standard e2e server (8000) so this runs in the normal suite /
// CI. Override locally with E2E_BASE_URL to point at an isolated server (e.g.
// http://127.0.0.1:8010) when the dev game owns 8000 — creating a save here
// switches the target server's active save.
const baseUrl = process.env.E2E_BASE_URL ?? 'http://127.0.0.1:8000';

// axe `nested-interactive` is a WCAG "serious" violation: an interactive
// control (e.g. a TermTip <button>) nested inside another interactive ancestor
// (a `<tr role="button">` standings row, a `<button role="checkbox">` prospect
// card). It also trips React's `validateDOMNesting` hydration warning. Both
// surfaces render the archetype as a non-interactive TermLabel to stay clean.
const NESTED_INTERACTIVE = 'nested-interactive';

test.describe('a11y: no nested-interactive controls', () => {
  test('standings table rows have no nested interactive controls', async ({ page, request }) => {
    const create = await request.post(`${baseUrl}/api/saves/new`, {
      headers: await launchTokenHeaders(request, baseUrl),
      data: { name: `e2e-a11y-standings-${Date.now()}`, club_id: 'aurora' },
    });
    expect(create.ok()).toBeTruthy();

    await page.goto(`${baseUrl}/?tab=standings`);
    await expect(page.locator('[data-testid="standings-table"]')).toBeVisible();

    const results = await new AxeBuilder({ page })
      .include('[data-testid="standings-table"]')
      .withRules([NESTED_INTERACTIVE])
      .analyze();

    expect(
      results.violations,
      `nested-interactive violations:\n${JSON.stringify(results.violations, null, 2)}`,
    ).toEqual([]);
  });

  test('new-game recruit step has no nested interactive controls', async ({ page, request }) => {
    // Deterministically start at the save menu: unload any active save (a prior
    // test on this server process may have left one active) via the API rather
    // than depending on reskin-sensitive "back to menu" button copy.
    await request.post(`${baseUrl}/api/saves/unload`, {
      headers: await launchTokenHeaders(request, baseUrl),
    });

    await page.goto(baseUrl);
    await expect(page.getByTestId('save-menu')).toBeVisible();

    // Build from Scratch -> Identity -> Coach -> Staff Hiring -> Recruit Roster.
    await page.getByTestId('new-game-tab').click();
    await page.locator('button:has-text("Build from Scratch")').click();

    await page.locator('input[placeholder="My Career"]').fill(`e2e-a11y-recruit-${Date.now()}`);
    await page.locator('input[placeholder="e.g. Iron Hawks"]').fill('Seattle Steelheads');
    await page.locator('input[placeholder="e.g. Northwood"]').fill('Seattle');
    await page.locator('button[title="Ocean"]').click();
    await page.locator('button:has-text("Next: Coach Profile")').click();

    await page.locator('input[placeholder="e.g. Ray Holloway"]').fill('Coach Maurice');
    await page.locator('button:has-text("Tactical Mastermind")').click();
    await page.locator('button:has-text("Next: Recruit Roster")').first().click();

    // The Coach step's "Next" may land on the Staff Hiring step (default hires
    // pre-fill). If the prospect checkboxes aren't up yet, advance once more.
    const prospectButtons = page.locator('button[role="checkbox"]');
    if (!(await prospectButtons.first().isVisible().catch(() => false))) {
      await page.getByRole('button', { name: /Next: Recruit Roster/i }).click();
    }
    await prospectButtons.first().waitFor({ state: 'visible', timeout: 8000 });

    const results = await new AxeBuilder({ page })
      .include('[data-testid="prospect-scroll"]')
      .withRules([NESTED_INTERACTIVE])
      .analyze();

    expect(
      results.violations,
      `nested-interactive violations:\n${JSON.stringify(results.violations, null, 2)}`,
    ).toEqual([]);
  });
});
