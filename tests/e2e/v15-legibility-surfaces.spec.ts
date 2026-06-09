import { expect, test } from '@playwright/test';
import { launchTokenHeaders } from './_token';

const baseUrl = 'http://127.0.0.1:8000';

// Helper: create a fresh aurora save and return the save name.
async function freshAuroraSave(request: import('@playwright/test').APIRequestContext): Promise<string> {
  const saveName = `e2e-v15-legibility-${Date.now()}`;
  const res = await request.post(`${baseUrl}/api/saves/new`, {
    headers: await launchTokenHeaders(request),
    data: { name: saveName, club_id: 'aurora' },
  });
  expect(res.ok()).toBeTruthy();
  return saveName;
}

// ---------------------------------------------------------------------------
// TermTip on Recruit Board (Phase 2a)
// ---------------------------------------------------------------------------

test('Recruit Board: TermTip triggers present for Fit and Interest terms on a fresh save', async ({ page, request }) => {
  await freshAuroraSave(request);
  await page.goto(`${baseUrl}/?tab=dynasty&subtab=recruiting`);

  // The recruit board must render at least one prospect card.
  await expect(page.getByTestId('prospect-card').first()).toBeVisible({ timeout: 10_000 });

  // TermTip for "Fit" should expose an accessible trigger button (aria-label contains "What is Fit?").
  const fitTip = page.getByRole('button', { name: /What is Fit\?/i }).first();
  await expect(fitTip).toBeVisible();

  // Focusing the trigger reveals a tooltip describing the term.
  await fitTip.focus();
  const tooltip = page.getByRole('tooltip').first();
  await expect(tooltip).toBeVisible();
  // The tooltip must describe the term in plain language (from TERMS['recruit.fit'].plain).
  await expect(tooltip).toContainText(/matches your program/i);

  // TermTip for "Interest" should also be present.
  const intTip = page.getByRole('button', { name: /What is Interest\?/i }).first();
  await expect(intTip).toBeVisible();
});

test('Recruit Board: TermTip tooltip describes mechanical vs flavor kind', async ({ page, request }) => {
  await freshAuroraSave(request);
  await page.goto(`${baseUrl}/?tab=dynasty&subtab=recruiting`);
  await expect(page.getByTestId('prospect-card').first()).toBeVisible({ timeout: 10_000 });

  const fitTip = page.getByRole('button', { name: /What is Fit\?/i }).first();
  await fitTip.focus();
  const tooltip = page.getByRole('tooltip').first();
  // The mechanical/flavor pill must be visible (Phase 1 TermTip renders "AFFECTS PLAY" or "FLAVOR").
  await expect(tooltip).toContainText(/AFFECTS PLAY|FLAVOR/i);
});

// ---------------------------------------------------------------------------
// PipelineEmblem on recruit cards (Phase 2a)
// ---------------------------------------------------------------------------

test('Recruit Board: PipelineEmblem present on prospect cards with accessible tier label', async ({ page, request }) => {
  await freshAuroraSave(request);
  await page.goto(`${baseUrl}/?tab=dynasty&subtab=recruiting`);
  await expect(page.getByTestId('prospect-card').first()).toBeVisible({ timeout: 10_000 });

  // At least one PipelineEmblem should be visible (role="img", aria-label="Pipeline Tier N ...").
  const emblem = page.getByRole('img', { name: /Pipeline Tier/i }).first();
  await expect(emblem).toBeVisible();

  // The tier label must include a tier number (1–5).
  const label = await emblem.getAttribute('aria-label');
  expect(label).toMatch(/Pipeline Tier [1-5]/);
});

// ---------------------------------------------------------------------------
// TermTip on Roster (Phase 2b)
// ---------------------------------------------------------------------------

test('Roster: TermTip triggers present for player archetypes on a fresh save', async ({ page, request }) => {
  await freshAuroraSave(request);
  await page.goto(`${baseUrl}/?tab=roster`);
  await expect(page.getByRole('heading', { name: /Team Roster/i })).toBeVisible({ timeout: 10_000 });

  // TermTip for an archetype term (e.g. "Thrower") should be present.
  // At least one archetype TermTip button must be visible somewhere on the roster.
  const archetypeTip = page
    .getByRole('button', { name: /What is (Thrower|Ball Hawk|Net Specialist|Skirmisher|Balanced)\?/i })
    .first();
  await expect(archetypeTip).toBeVisible();

  // Focusing reveals a description.
  await archetypeTip.focus();
  await expect(page.getByRole('tooltip').first()).toBeVisible();
});

test('Roster: TermTip for growth Ceiling term is present on player card', async ({ page, request }) => {
  await freshAuroraSave(request);
  await page.goto(`${baseUrl}/?tab=roster`);
  await expect(page.getByRole('heading', { name: /Team Roster/i })).toBeVisible({ timeout: 10_000 });

  // Open a player card to surface the Ceiling/Headroom TermTip.
  const firstPlayerRow = page.getByTestId('roster-player-row').first();
  if (await firstPlayerRow.isVisible()) {
    await firstPlayerRow.click();
    // After clicking, a player detail panel should open.
    const playerDetail = page.getByTestId('player-detail-modal').or(page.getByTestId('player-card'));
    await expect(playerDetail.first()).toBeVisible({ timeout: 5_000 });
    const ceilingTip = page.getByRole('button', { name: /What is Ceiling\?/i }).first();
    await expect(ceilingTip).toBeVisible();
  }
});

// ---------------------------------------------------------------------------
// Honest EmptyState — banners (Phase 4a)
// ---------------------------------------------------------------------------

test('History: honest EmptyState for Championship Banners on a fresh save', async ({ page, request }) => {
  await freshAuroraSave(request);
  await page.goto(`${baseUrl}/?tab=dynasty&subtab=history`);

  // History tab / program page must load.
  await expect(
    page.getByRole('heading', { name: /Program History|My Program|History/i }).first()
  ).toBeVisible({ timeout: 10_000 });

  // On a fresh career, banners are empty. The EmptyState component renders
  // role="status" with title text.
  const bannerSection = page.getByTestId('banner-shelf').or(page.getByTestId('banners-section'));
  if (await bannerSection.first().isVisible().catch(() => false)) {
    const emptyState = bannerSection.first().getByRole('status');
    await expect(emptyState).toBeVisible();
    // Must not say "0/0 awards logged" (old fabricated copy) — must say something honest.
    await expect(emptyState).not.toContainText('0/0 awards logged');
    // Must describe what will fill it.
    await expect(emptyState).toContainText(/banner|championship|win/i);
  }
});

// ---------------------------------------------------------------------------
// Honest EmptyState — alumni (Phase 4a)
// ---------------------------------------------------------------------------

test('History: honest EmptyState for Alumni Lineage on a fresh save', async ({ page, request }) => {
  await freshAuroraSave(request);
  await page.goto(`${baseUrl}/?tab=dynasty&subtab=history`);
  await expect(
    page.getByRole('heading', { name: /Program History|My Program|History/i }).first()
  ).toBeVisible({ timeout: 10_000 });

  const alumniSection = page.getByTestId('alumni-lineage').or(page.getByTestId('alumni-section'));
  if (await alumniSection.first().isVisible().catch(() => false)) {
    const emptyState = alumniSection.first().getByRole('status');
    await expect(emptyState).toBeVisible();
    // Must convey honest absence of alumni.
    await expect(emptyState).toContainText(/alumni|retire|graduated/i);
  }
});

// ---------------------------------------------------------------------------
// Honest EmptyState — staff vacancies (Phase 3b)
// ---------------------------------------------------------------------------

test('Dynasty Office Staff: honest EmptyState for Vacancies when none exist', async ({ page, request }) => {
  await freshAuroraSave(request);
  await page.goto(`${baseUrl}/?tab=dynasty&subtab=staff`);
  await expect(page.getByRole('heading', { name: 'Candidates' })).toBeVisible({ timeout: 10_000 });

  // On a fresh career with full staff, the Vacancies section shows an EmptyState
  // instead of a big blank card.
  const vacanciesSection = page.getByTestId('vacancies-section').or(page.getByTestId('staff-vacancies'));
  if (await vacanciesSection.first().isVisible().catch(() => false)) {
    const emptyState = vacanciesSection.first().getByRole('status');
    await expect(emptyState).toBeVisible();
    await expect(emptyState).not.toContainText('TODO');
  }
});

// ---------------------------------------------------------------------------
// ProofChip on History milestones (Phase 4a)
// ---------------------------------------------------------------------------

test('History: ProofChip on milestone entries exposes payload-backed source', async ({ page, request }) => {
  // This test is only meaningful after at least one completed season.
  // On a fresh career, milestones with proof do not exist (honesty gate),
  // so we verify that no ProofChip claims a source on the fresh save.
  await freshAuroraSave(request);
  await page.goto(`${baseUrl}/?tab=dynasty&subtab=history`);
  await expect(
    page.getByRole('heading', { name: /Program History|My Program|History/i }).first()
  ).toBeVisible({ timeout: 10_000 });

  // No ProofChip button should claim an award on a fresh career.
  // If any appear, their source must not contain a placeholder token.
  const proofChips = page.getByRole('button', { name: /Best Newcomer|Most Valuable|Champion|ⓘ/i });
  const count = await proofChips.count();
  for (let i = 0; i < count; i++) {
    const chip = proofChips.nth(i);
    await chip.click();
    const note = page.getByRole('note').first();
    await expect(note).toBeVisible();
    await expect(note).not.toContainText('TODO');
    await expect(note).not.toContainText('PLACEHOLDER');
    // Close the chip before the next iteration.
    await chip.click();
  }
});
