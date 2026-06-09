import { test, expect } from '@playwright/test';
import { launchTokenHeaders } from './_token';

// Verifies the Season Preview information-density upgrade:
// - The Playoff Cut stat label is a TermTip that reveals its explanation.
// - The strength/weakness archetype labels are TermTips that reveal mechanical explanations.
// Precondition: a fresh career must be in Week 1 (Season Preview is visible).
test.describe('Season Preview density (Phase 3c)', () => {
  test.beforeEach(async ({ page, request }) => {
    // Navigate to a fresh-career command center so the Season Preview is shown.
    const saveName = `e2e-season-preview-${Date.now()}`;
    const create = await request.post(`http://127.0.0.1:8000/api/saves/new`, {
      headers: await launchTokenHeaders(request),
      data: { name: saveName, club_id: 'aurora' },
    });
    expect(create.ok()).toBeTruthy();

    await page.goto('http://127.0.0.1:8000/');
    // Wait for the season preview section.
    await expect(page.getByTestId('season-preview')).toBeVisible({ timeout: 10_000 });
  });

  test('Playoff Cut label reveals a TermTip explanation', async ({ page }) => {
    const cutButton = page.getByRole('button', { name: /What is Playoff Line\?/i });
    await expect(cutButton).toBeVisible();
    await cutButton.focus();
    const tooltip = page.getByRole('tooltip');
    await expect(tooltip).toContainText(/cutoff seed/i);
    await expect(tooltip).toContainText(/AFFECTS PLAY/i);
  });

  test('Strength archetype label reveals a TermTip explanation', async ({ page }) => {
    // The specific archetype depends on the roster; look for any TermTip button
    // inside the Roster Strength card specifically.
    const strengthHeading = page.getByText('Roster strength', { exact: true });
    const strengthCard = strengthHeading.locator('xpath=..');
    const tipButton = strengthCard.getByRole('button', { name: /What is/i });
    await expect(tipButton).toBeVisible();
    await tipButton.focus();
    const tooltip = page.getByRole('tooltip');
    await expect(tooltip).toContainText(/AFFECTS PLAY/i);
  });
});
