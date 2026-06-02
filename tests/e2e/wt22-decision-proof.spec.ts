import { expect, test, type Page } from '@playwright/test';
import { launchTokenHeaders } from './_token';

/**
 * WT-22 — decision-proof: a CHANGED decision must reach the rendered
 * aftermath/replay text, and that text must MATCH the canonical
 * /api/matches/{id}/replay payload (SEES == PLAYS for the decision).
 *
 * This closes a regression gap: nothing previously proved through the browser
 * that a tactic the player CHANGED (a) is recorded by the sim and (b) is
 * faithfully rendered. The risk is the UI rendering stale text vs the backend
 * proof. (Authority: docs/specs/2026-06-01-master-roadmap-grill-resolutions.md
 * WT-22; ADR 0002 faithfulness-first.)
 *
 * Design (grounded in source + an in-process probe, not assumption):
 *
 *  - Lever = a NON-DEFAULT TACTIC, not a lineup. Every curated club has exactly
 *    six players and fields six, so a lineup *swap* is mechanically impossible
 *    (benching no one), and `report.top_performers` is a cross-team leaderboard,
 *    so it never cleanly encodes "the six I fielded." The tactic is the decision
 *    that genuinely changes the recorded + rendered payload. The default
 *    `approach` is `mixed`; we change it to `aggressive` through the UI.
 *
 *  - The change is driven THROUGH THE UI (PolicyEditor pill), so the per-process
 *    launch token (WT-12) rides the real user action — no forged header. The
 *    save POST is intent-only on lock + simulate, but the backend PRESERVES an
 *    already-saved tactic when the intent is unchanged (the WT-9 fix in
 *    command_week_service.save_command_center_plan_payload). The probe confirmed
 *    the non-default tactic survives lock+simulate into the replay payload.
 *
 *  - SEES == PLAYS is asserted against the LITERAL payload the SPA rendered from:
 *    we capture the `/api/matches/{id}/replay` response the app fetched
 *    (MatchWeek.tsx fetches it via commandApi.replay and feeds
 *    `report.turning_point` into the tactical summary and `report.top_performers`
 *    into the key-players panel). We then assert the on-screen strings equal that
 *    payload — not hardcoded text, and not a second independent fetch.
 *
 *  - HONEST SCOPE NOTE: the verbatim "Command plan" evidence lane (which names
 *    the chosen tactic, e.g. "Approach: Aggressive …") is part of the payload but
 *    is NOT rendered on any aftermath/replay surface today (the only
 *    `evidence_lanes` consumer, TacticalSummaryCard, surfaces lane[0] +
 *    turning_point). So the *decision-verbatim* proof is asserted on the payload,
 *    while the *rendered* proof is the decision-DERIVED fields (turning_point +
 *    performers) that the same tactic drives. This spec asserts the FIXED
 *    behavior; it does not claim the tactic label renders on screen, and it must
 *    not be "fixed" by adding rendering — this file is the test, not app source.
 */

const baseUrl = 'http://127.0.0.1:8000';

// The PolicyEditor pill we click. Default approach is `mixed`; `aggressive` is a
// genuine non-default change. The label the player sees + the lane copy both come
// from the same tier-1 voice string `policy.approach.aggressive.label`.
const CHANGED_KEY = 'approach';
const CHANGED_VALUE = 'aggressive';
const CHANGED_LABEL = /Aggressive/i;

async function reachCommandCenter(page: Page): Promise<void> {
  await page.goto(`${baseUrl}/?tab=command`);
  await expect(
    page.locator('[data-testid="weekly-command-center"], [data-testid="season-preview"]').first(),
  ).toBeVisible({ timeout: 10000 });
  if (await page.getByTestId('season-preview').isVisible()) {
    await page.getByRole('button', { name: /To the Command Center/i }).click();
  }
  await expect(page.getByTestId('weekly-command-center')).toBeVisible();
}

test('a changed tactic is recorded by the sim AND the rendered aftermath matches the replay payload', async ({
  page,
  request,
}) => {
  // (1) Fresh career. The save-creation POST is a raw APIRequestContext call,
  //     so it must carry the WT-12 launch token itself (the guard has no route
  //     exemption); every later mutation rides the UI, which attaches the token
  //     automatically via the injected <meta> tag.
  const saveName = `e2e-wt22-decision-${Date.now()}`;
  const create = await request.post(`${baseUrl}/api/saves/new`, {
    headers: await launchTokenHeaders(request, baseUrl),
    data: { name: saveName, club_id: 'aurora' },
  });
  expect(create.ok()).toBeTruthy();

  await reachCommandCenter(page);

  // (2) Change a NON-DEFAULT tactic through the UI. Open the Policy Editor and
  //     click the `aggressive` approach pill (default is `mixed`). The POST that
  //     persists it carries the launch token automatically because it originates
  //     from a real user action.
  await page.getByTestId('open-policy-editor').click();
  const policyEditor = page.getByTestId('policy-editor');
  await expect(policyEditor).toBeVisible();

  const changedPill = page.getByTestId(`policy-${CHANGED_KEY}-${CHANGED_VALUE}`);
  // Wait for the save round-trip so the backend has the non-default tactic before
  // we lock. The save reloads the command center; aria-checked flips to true.
  const savePlanResponse = page.waitForResponse(
    (res) => res.url().includes('/api/command-center/plan') && res.request().method() === 'POST',
  );
  await changedPill.click();
  await savePlanResponse;
  await expect(changedPill).toHaveAttribute('aria-checked', 'true');

  // Close the overlay so the lock/simulate controls are reachable.
  await page.getByRole('button', { name: /Close policy editor/i }).click();
  await expect(policyEditor).not.toBeVisible({ timeout: 5000 });

  // (3) Clear the Phase 3 readiness gates, lock the plan, and simulate. Lock +
  //     simulate POST the intent only; the saved non-default tactic is preserved
  //     because the intent does not change (WT-9 fix).
  if (await page.getByTestId('scout-opponent').isVisible().catch(() => false)) {
    await page.getByTestId('scout-opponent').click();
  }
  if (await page.getByTestId('confirm-lineup').isVisible().catch(() => false)) {
    await page.getByTestId('confirm-lineup').click();
  }
  await page.getByTestId('lock-weekly-plan').click();
  await expect(page.getByTestId('simulate-command-week')).toBeEnabled();

  // Capture the EXACT replay payload the SPA fetches + renders from. MatchWeek
  // fetches /api/matches/{id}/replay after the sim; we assert the DOM against
  // these literal bytes (no second independent fetch -> no tautology).
  const replayResponsePromise = page.waitForResponse(
    (res) => /\/api\/matches\/[^/]+\/replay/.test(res.url()) && res.request().method() === 'GET',
    { timeout: 20000 },
  );

  await page.getByTestId('simulate-command-week').click();
  await expect(page.getByTestId('post-week-dashboard')).toBeVisible({ timeout: 20000 });
  // Skip the staged reveal so every aftermath card is mounted at once.
  await page.keyboard.press('Space');

  const replayResponse = await replayResponsePromise;
  expect(replayResponse.ok()).toBeTruthy();
  const replay = await replayResponse.json();
  const report = replay.report;
  expect(report, 'replay payload must carry a report').toBeTruthy();

  // (4a) DECISION RECORDED — the changed tactic reached what the sim recorded.
  //      The canonical replay payload's "Command plan" evidence lane names the
  //      tactic the player chose. This is the SEES==PLAYS proof for the decision
  //      itself (the value we clicked is what the engine logged for the match).
  const commandPlanLane = (report.evidence_lanes ?? []).find(
    (lane: { title: string }) => lane.title === 'Command plan',
  );
  expect(commandPlanLane, 'a Command plan evidence lane must be present').toBeTruthy();
  const approachItem: string | undefined = (commandPlanLane.items ?? []).find((item: string) =>
    item.startsWith('Approach:'),
  );
  expect(approachItem, 'Command plan must name the Approach the player set').toBeTruthy();
  expect(approachItem).toMatch(CHANGED_LABEL);

  // (4b) SEES == PLAYS (RENDERED) — the on-screen aftermath text equals the
  //      payload the app rendered from. The tactical summary's read text is fed
  //      directly from report.turning_point.
  const tacticalSummary = page.getByTestId('tactical-summary');
  await expect(tacticalSummary).toBeVisible();
  expect(typeof report.turning_point).toBe('string');
  expect(report.turning_point.length).toBeGreaterThan(0);
  await expect(tacticalSummary).toContainText(report.turning_point);

  // (4c) SEES == PLAYS (RENDERED) — the key-performers panel renders the
  //      payload's top performers. The rank-1 performer is always in the rendered
  //      top three, so its name must be visible. (We assert "visible," not
  //      list-equality: the Your-Club-Best path can surface an extra name.)
  const keyPlayers = page.getByTestId('key-players-panel');
  await expect(keyPlayers).toBeVisible();
  const performers = report.top_performers ?? [];
  expect(performers.length, 'sim must record at least one top performer').toBeGreaterThan(0);
  const topPerformerName: string = performers[0].player_name;
  expect(topPerformerName.length).toBeGreaterThan(0);
  await expect(keyPlayers.getByText(topPerformerName, { exact: false }).first()).toBeVisible();
});
