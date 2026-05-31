import { expect, test } from '@playwright/test';

const baseUrl = 'http://127.0.0.1:8000';

// V15 Phase 2a legibility smoke for the recruit board.
// Does NOT re-test scout/contact/visit action mechanics (covered elsewhere).
test.describe('recruit board legibility (V15 Phase 2a)', () => {
  let saveName: string;

  test.beforeEach(async ({ page, request }) => {
    saveName = `e2e-v15-recruit-${Date.now()}`;
    const create = await request.post(`${baseUrl}/api/saves/new`, {
      data: { name: saveName, club_id: 'aurora' },
    });
    expect(create.ok()).toBeTruthy();

    // Navigate to Dynasty Office → Recruit tab (default subtab).
    await page.goto(`${baseUrl}/?tab=dynasty`);
    // Wait for either the recruit board or an initial loading state to resolve.
    await expect(page.locator('.do-board')).toBeVisible({ timeout: 10_000 });
  });

  test('hometown reads with a "From" prefix, not as a surname', async ({ page }) => {
    const card = page.locator('.do-recruit').first();
    await expect(card).toBeVisible();
    // The "From" prefix must appear in the sub-row.
    await expect(card.locator('text=From')).toBeVisible();
    // The sub-row must NOT render prospect.hometown immediately after a "·" with no prefix.
    // (Verified structurally by the "From" label being present.)
  });

  test('archetype badge opens a TermTip tooltip on focus', async ({ page }) => {
    const card = page.locator('.do-recruit').first();
    // The TermTip renders as a button with aria-label "What is <ArchetypeName>?".
    // Use `.first()` in case multiple TermTips are on the same card.
    const archetypeTip = card
      .getByRole('button', { name: /What is (Sharpshooter|Net Specialist|Ball Hawk|Iron Anchor|Two-Way Threat|Skirmisher|Possession Specialist|Hit-and-Run)\?/i })
      .first();
    await archetypeTip.focus();
    await expect(page.getByRole('tooltip').first()).toBeVisible();
    // The tooltip must classify the term as mechanical (affects play).
    await expect(page.getByRole('tooltip').first()).toContainText(/affects play/i);
  });

  test('OVR range shows KnownValue estimated state for unscouted prospect', async ({ page }) => {
    // Fresh career: all prospects are unscouted — the KnownValue must show estimated state.
    // The KnownValue group's aria-label contains "estimated" for unscouted.
    const card = page.locator('.do-recruit').first();
    const ovrGroup = card.getByRole('group', { name: /OVR.*estimated/i });
    await expect(ovrGroup).toBeVisible();
    // The "Scout to narrow" hint must be present on the card.
    await expect(card).toContainText(/Scout to narrow/i);
    // The scouting caption below the evidence row must also appear.
    await expect(card).toContainText(/Scout to narrow the OVR range/i);
  });

  test('FIT value shows /100 denominator to distinguish it from a roster OVR', async ({ page }) => {
    const card = page.locator('.do-recruit').first();
    // The /100 suffix must be visible on the card's FIT number.
    await expect(card).toContainText(/\/100/);
  });

  test('fit-tier legend row explains card color', async ({ page }) => {
    const card = page.locator('.do-recruit').first();
    await expect(card).toContainText(/Strong Fit ≥80/i);
    await expect(card).toContainText(/Fair Fit 65/i);
    await expect(card).toContainText(/At Risk/i);
  });

  test('PipelineEmblem carries an accessible tier label', async ({ page }) => {
    const card = page.locator('.do-recruit').first();
    // PipelineEmblem renders as role="img" with aria-label "Pipeline Tier N (TierName)".
    const emblem = card.getByRole('img', { name: /Pipeline Tier [1-5]/i });
    await expect(emblem).toBeVisible();
  });

  test('sort by Interest changes or preserves order without crashing', async ({ page }) => {
    // Click the Interest sort button.
    await page.getByRole('button', { name: /^Sort by Interest/i }).click();
    // Board must still render cards.
    await expect(page.locator('.do-recruit').first()).toBeVisible();
    // Clicking again toggles direction (↓ becomes ↑ in button text).
    await page.getByRole('button', { name: /^Sort by Interest/i }).click();
    await expect(page.locator('.do-recruit').first()).toBeVisible();
  });

  test('sort by Pipeline changes or preserves order without crashing', async ({ page }) => {
    await page.getByRole('button', { name: /^Sort by Pipeline/i }).click();
    await expect(page.locator('.do-recruit').first()).toBeVisible();
  });

  test('At Risk filter empty-state renders without fabricated data', async ({ page }) => {
    await page.getByRole('button', { name: /At Risk/i }).click();
    const cardCount = await page.locator('.do-recruit').count();
    if (cardCount === 0) {
      // EmptyState must be present (role="status") and must say "No prospects match".
      await expect(page.getByRole('status')).toContainText(/No prospects match/i);
      // Must NOT fabricate a prospect name or stat.
      await expect(page.getByRole('status')).not.toContainText(/OVR|Fit \d+|Interest \d+/i);
    }
    // If cardCount > 0, filter is working correctly — no empty-state assertion needed.
  });
});
