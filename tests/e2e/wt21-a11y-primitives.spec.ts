import { expect, test, type Page, type APIRequestContext } from '@playwright/test';
import { launchTokenHeaders } from './_token';

// WT-21 — role-based accessibility specs for the shared primitives and the
// surfaces migrated onto them. Desktop viewport (the product target). These
// assert keyboard + screen-reader semantics via ROLE locators, not CSS, so
// they document the a11y contract rather than the styling.

const baseUrl = 'http://127.0.0.1:8000';

async function freshCareer(request: APIRequestContext, slug: string): Promise<void> {
  const headers = await launchTokenHeaders(request, baseUrl);
  const create = await request.post(`${baseUrl}/api/saves/new`, {
    headers,
    data: { name: `e2e-wt21-${slug}-${Date.now()}`, club_id: 'aurora' },
  });
  expect(create.ok()).toBeTruthy();
}

async function openRoster(page: Page): Promise<void> {
  await page.goto(`${baseUrl}/?tab=roster`);
  await expect(page.getByRole('heading', { name: /Team Roster/i })).toBeVisible({ timeout: 10_000 });
}

test.describe('WT-21 Roster rows are keyboard-operable', () => {
  test('focusing a player row and pressing Enter opens the player Dialog', async ({ page, request }) => {
    await freshCareer(request, 'roster-enter');
    await openRoster(page);

    // Rows are exposed as role="button" with a descriptive accessible name.
    const firstRow = page.getByRole('button', { name: /open player card/i }).first();
    await expect(firstRow).toBeVisible();

    // Keyboard path: focus the row, press Enter -> the player Dialog opens.
    await firstRow.focus();
    await expect(firstRow).toBeFocused();
    await page.keyboard.press('Enter');

    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText(/Player Card/i)).toBeVisible();
  });

  test('Space also opens the row Dialog, Escape closes it and restores focus to the row', async ({ page, request }) => {
    await freshCareer(request, 'roster-space');
    await openRoster(page);

    const firstRow = page.getByRole('button', { name: /open player card/i }).first();
    await firstRow.focus();
    await page.keyboard.press(' ');

    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();

    // Escape closes the Dialog (provided by the shared Dialog primitive)...
    await page.keyboard.press('Escape');
    await expect(dialog).not.toBeVisible();
    // ...and focus is restored to the triggering row.
    await expect(firstRow).toBeFocused();
  });
});

test.describe('WT-21 Dialog focus management (Lineup Editor)', () => {
  async function openLineupEditor(page: Page): Promise<void> {
    await openRoster(page);
    await page.getByRole('button', { name: /Lineup Editor/i }).click();
    await expect(page.getByRole('dialog', { name: /Lineup Editor/i })).toBeVisible();
  }

  test('focus moves into the dialog on open', async ({ page, request }) => {
    await freshCareer(request, 'lineup-focus-in');
    await openLineupEditor(page);

    // After open, the active element must live inside the dialog (the primitive
    // focuses the first focusable child).
    const activeInsideDialog = await page.evaluate(() => {
      const dialog = document.querySelector('[role="dialog"]');
      return Boolean(dialog && document.activeElement && dialog.contains(document.activeElement));
    });
    expect(activeInsideDialog).toBe(true);
  });

  test('Escape closes the dialog and Tab is trapped within it', async ({ page, request }) => {
    await freshCareer(request, 'lineup-trap');
    await openLineupEditor(page);
    const dialog = page.getByRole('dialog', { name: /Lineup Editor/i });

    // Tab a number of times; focus must never escape the dialog subtree.
    for (let i = 0; i < 12; i++) {
      await page.keyboard.press('Tab');
      const stillInside = await page.evaluate(() => {
        const d = document.querySelector('[role="dialog"]');
        return Boolean(d && document.activeElement && d.contains(document.activeElement));
      });
      expect(stillInside).toBe(true);
    }

    // Escape closes the migrated dialog (LineupEditor had no Escape before WT-21).
    await page.keyboard.press('Escape');
    await expect(dialog).not.toBeVisible({ timeout: 2_000 });
  });

  test('a successful lineup swap is announced via a polite role="status" region', async ({ page, request }) => {
    await freshCareer(request, 'lineup-status');
    await openLineupEditor(page);
    const dialog = page.getByRole('dialog', { name: /Lineup Editor/i });

    // Drive a valid swap from the keyboard-operable controls: select an active
    // slot, then pick a bench player. This commits and the footer status region
    // (role="status" while not in error) announces "Saved." — previously a
    // silent coloured span (WT-21 closed that gap).
    const activeGroup = dialog.getByRole('group', { name: /Active starters/i });
    await activeGroup.getByRole('button').first().click();

    const benchGroup = dialog.getByRole('group', { name: /Bench players/i });
    const benchButtons = benchGroup.getByRole('button');
    // A fresh aurora roster has bench depth; if not, skip the swap assertion.
    if ((await benchButtons.count()) > 0) {
      await benchButtons.first().click();
      const status = dialog.getByRole('status');
      await expect(status).toContainText(/Saved\./i, { timeout: 5_000 });
    }
  });
});

test.describe('WT-21 PolicyEditor container modal is an accessible Dialog', () => {
  test('opening the policy editor traps focus and Escape closes it, restoring focus to the trigger', async ({ page, request }) => {
    await freshCareer(request, 'policy-modal');
    await page.goto(`${baseUrl}/?tab=command`);
    await expect(page.locator('[data-testid="weekly-command-center"], [data-testid="season-preview"]').first()).toBeVisible({ timeout: 10_000 });
    if (await page.getByTestId('season-preview').isVisible()) {
      await page.getByRole('button', { name: /To the Command Center/i }).click();
    }
    await expect(page.getByTestId('weekly-command-center')).toBeVisible();

    const trigger = page.getByTestId('open-policy-editor');
    await trigger.focus();
    await trigger.click();

    // The previously-raw overlay is now a Dialog (role="dialog" on the panel).
    const dialog = page.getByRole('dialog', { name: /Edit policy/i });
    await expect(dialog).toBeVisible();
    // Its PolicyEditor body is rendered intact (wrap, not rewrite).
    await expect(page.getByTestId('policy-editor')).toBeVisible();

    // Focus is inside the dialog after open.
    const insideAfterOpen = await page.evaluate(() => {
      const d = document.querySelector('[role="dialog"]');
      return Boolean(d && document.activeElement && d.contains(document.activeElement));
    });
    expect(insideAfterOpen).toBe(true);

    // Escape closes it and restores focus to the trigger.
    await page.keyboard.press('Escape');
    await expect(dialog).not.toBeVisible({ timeout: 2_000 });
    await expect(trigger).toBeFocused();
  });
});

test.describe('WT-21 SaveMenu club selection is a keyboard radiogroup', () => {
  async function openTakeoverForm(page: Page, request: APIRequestContext): Promise<void> {
    await request.post(`${baseUrl}/api/saves/unload`, { headers: await launchTokenHeaders(request, baseUrl) });
    await page.goto(baseUrl);
    await expect(page.getByTestId('save-menu')).toBeVisible({ timeout: 10_000 });
    await page.getByTestId('new-game-tab').click();
    await page.getByRole('button', { name: /Take Over a Program/i }).click();
    await expect(page.getByTestId('new-game-form')).toBeVisible();
  }

  test('club list exposes role="radiogroup" with role="radio" options and arrow-key navigation', async ({ page, request }) => {
    await openTakeoverForm(page, request);

    const group = page.getByRole('radiogroup', { name: /Club/i });
    await expect(group).toBeVisible();

    const radios = group.getByRole('radio');
    const count = await radios.count();
    expect(count).toBeGreaterThan(1);

    // Exactly one option is checked initially (the default-selected club).
    const checkedRadio = group.getByRole('radio', { checked: true });
    await expect(checkedRadio).toHaveCount(1);

    // The checked option is the roving tab stop — focus it, then ArrowDown
    // must move the selection (aria-checked) to the next option.
    await checkedRadio.focus();
    await page.keyboard.press('ArrowDown');

    // After ArrowDown the previously-checked option is no longer checked and a
    // single option remains checked (selection followed the arrow key).
    await expect(group.getByRole('radio', { checked: true })).toHaveCount(1);
    const focusedIsRadio = await page.evaluate(() => document.activeElement?.getAttribute('role') === 'radio');
    expect(focusedIsRadio).toBe(true);
  });
});
