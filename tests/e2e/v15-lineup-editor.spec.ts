import { expect, test, type Page, type APIRequestContext } from '@playwright/test';
import { launchTokenHeaders } from './_token';

const baseUrl = 'http://127.0.0.1:8000';

async function openLineupEditor(page: Page, request: APIRequestContext): Promise<void> {
  const saveName = `e2e-v15-lineup-${Date.now()}`;
  const create = await request.post(`${baseUrl}/api/saves/new`, {
    headers: await launchTokenHeaders(request),
    data: { name: saveName, club_id: 'aurora' },
  });
  expect(create.ok()).toBeTruthy();

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${baseUrl}/?tab=roster`);
  await expect(page.getByRole('heading', { name: /Team Roster/i })).toBeVisible({ timeout: 10000 });

  // Open the lineup editor from the Roster screen header button.
  await page.getByRole('button', { name: /Lineup Editor/i }).click();
  await expect(page.getByRole('dialog', { name: /Lineup Editor/i })).toBeVisible();
}

test('V15 2c: active/bench split headers are unambiguous', async ({ page, request }) => {
  await openLineupEditor(page, request);
  const dialog = page.getByRole('dialog', { name: /Lineup Editor/i });

  // Active group carries the cyan "6 fielded" badge.
  const activeGroup = dialog.getByRole('group', { name: /Active starters/i });
  await expect(activeGroup).toBeVisible();
  await expect(activeGroup.getByText(/6 fielded/i)).toBeVisible();

  // Bench group carries the muted "not fielded" badge.
  const benchGroup = dialog.getByRole('group', { name: /Bench players/i });
  await expect(benchGroup).toBeVisible();
  await expect(benchGroup.getByText(/not fielded/i)).toBeVisible();
});

test('V15 2c: slot-order TermTip is keyboard-focusable and reveals tooltip', async ({ page, request }) => {
  await openLineupEditor(page, request);
  const dialog = page.getByRole('dialog', { name: /Lineup Editor/i });

  // The TermTip wraps "Slot order" as a focusable button with aria-label "What is Slot Order?"
  const termTipTrigger = dialog.getByRole('button', { name: /What is Slot Order\?/i });
  await expect(termTipTrigger).toBeVisible();

  // Focus via keyboard — Tab into the dialog then navigate.
  await termTipTrigger.focus();
  await expect(page.getByRole('tooltip')).toBeVisible();
  await expect(page.getByRole('tooltip')).toContainText(/slot/i);
  await expect(page.getByRole('tooltip')).toContainText(/Captain/i);
});

test('V15 2c: role-label legend shows all six slots', async ({ page, request }) => {
  await openLineupEditor(page, request);
  const dialog = page.getByRole('dialog', { name: /Lineup Editor/i });

  // All six ROLE_LABELS should be visible in the legend.
  for (const label of ['Captain', 'Striker', 'Anchor', 'Runner', 'Rookie', 'Utility']) {
    await expect(dialog.getByText(new RegExp(label, 'i')).first()).toBeVisible();
  }
});

test('V15 2c: Auto-Pick button has accessible label and secondary style (not destructive)', async ({ page, request }) => {
  await openLineupEditor(page, request);
  const dialog = page.getByRole('dialog', { name: /Lineup Editor/i });

  // Button must be findable by its accessible label.
  const autoPick = dialog.getByRole('button', { name: /Auto-Pick/i });
  await expect(autoPick).toBeVisible();
  await expect(autoPick).toBeEnabled();

  // The button's title must describe the recoverable action.
  const titleAttr = await autoPick.getAttribute('title');
  expect(titleAttr).toMatch(/lineup resolver/i);

  // Confirm "Reset" no longer appears as the button label (old destructive framing gone).
  await expect(dialog.getByRole('button', { name: /^Reset to Auto$/i })).toHaveCount(0);
});

test('V15 2c: dialog has no horizontal overflow at 390px', async ({ page, request }) => {
  await openLineupEditor(page, request);

  const hasHorizontalOverflow = await page.evaluate(() => {
    const root = document.documentElement;
    return root.scrollWidth > window.innerWidth;
  });
  expect(hasHorizontalOverflow).toBe(false);
});

test('V15 2c: Escape key closes the dialog', async ({ page, request }) => {
  await openLineupEditor(page, request);
  await expect(page.getByRole('dialog', { name: /Lineup Editor/i })).toBeVisible();

  await page.keyboard.press('Escape');

  // The close handler fires via the overlay onClick; confirm dialog gone.
  // Note: if the close handler does not wire Escape natively, this test
  // documents the gap — do not add Escape handling in this phase (out of scope).
  // The test is written to be a soft-regression: if Escape already works, it passes.
  // If it does not, the dialog stays visible and this test fails, surfacing the gap for Phase 5.
  await expect(page.getByRole('dialog', { name: /Lineup Editor/i })).not.toBeVisible({ timeout: 2000 });
});
