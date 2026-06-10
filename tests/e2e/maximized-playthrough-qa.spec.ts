import { expect, test } from '@playwright/test';
import { launchTokenHeaders } from './_token';

const baseUrl = 'http://127.0.0.1:8000';

test.describe('Maximized browser playthrough and V11 QA Pass', () => {
  let saveName: string;

  test.beforeAll(() => {
    saveName = `qa-playthrough-${Date.now()}`;
  });

  test('multi-viewport playthrough, aftermath, and replay audit', async ({ page, request }, testInfo) => {
    const screenshotPath = (name: string) => testInfo.outputPath(name);
    const consoleErrors: string[] = [];
    page.on('pageerror', (err) => {
      consoleErrors.push(`[Console Error] ${err.message}`);
    });
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(`[Console Error Log] ${msg.text()}`);
      }
    });

    // 1. Create a new career with Official Cloth ruleset (highly distinct from Foam)
    await test.step('Create official cloth ruleset save', async () => {
      const createRes = await request.post(`${baseUrl}/api/saves/new`, {
        headers: await launchTokenHeaders(request),
        data: {
          name: saveName,
          club_id: 'aurora',
          ruleset_selection: 'official_cloth',
        },
      });
      expect(createRes.ok()).toBeTruthy();
    });

    // 2. Multi-viewport verification on pre-sim weekly command center
    await test.step('Verify pre-sim hub across viewports', async () => {
      await page.goto(`${baseUrl}/?tab=command`);
      await expect(page.locator('[data-testid="weekly-command-center"], [data-testid="season-preview"]').first()).toBeVisible({ timeout: 10000 });
  if (await page.getByTestId('season-preview').isVisible()) {
    await page.getByRole('button', { name: /To the Command Center/i }).click();
  }
  await expect(page.getByTestId('weekly-command-center')).toBeVisible();

      // Wide Desktop Viewport
      await page.setViewportSize({ width: 1920, height: 1080 });
      await page.waitForTimeout(500);
      await page.screenshot({ path: screenshotPath('presim_desktop_1920x1080.png') });
      
      // Check for visual properties and structural completeness
      await expect(page.getByRole('heading', { name: 'Command Center' })).toBeVisible();
      await expect(page.getByTestId('plan-editor-panel')).toBeVisible();
      await expect(page.getByTestId('scout-read-panel')).toBeVisible();
      await expect(page.getByTestId('readiness-panel')).toBeVisible();

      // Medium Tablet Viewport
      await page.setViewportSize({ width: 1024, height: 768 });
      await page.waitForTimeout(500);
      await page.screenshot({ path: screenshotPath('presim_tablet_1024x768.png') });
      
      // Mobile Viewport
      await page.setViewportSize({ width: 375, height: 812 });
      await page.waitForTimeout(500);
      await page.screenshot({ path: screenshotPath('presim_mobile_375x812.png') });

      // Restore Desktop Viewport for continuation
      await page.setViewportSize({ width: 1440, height: 900 });
    });

    // 3. Locking plan and simulating Week 1
    await test.step('Lock plan and simulate Week 1', async () => {
      await page.goto(`${baseUrl}/?tab=command`);
      await expect(page.locator('[data-testid="weekly-command-center"], [data-testid="season-preview"]').first()).toBeVisible({ timeout: 10000 });
  if (await page.getByTestId('season-preview').isVisible()) {
    await page.getByRole('button', { name: /To the Command Center/i }).click();
  }
  await expect(page.getByTestId('weekly-command-center')).toBeVisible();
      
      // D3: clear the deliberate-action readiness gates (scout + confirm
      // lineup) before the plan can be locked.
      if (await page.getByTestId('scout-opponent').isVisible().catch(() => false)) {
        await page.getByTestId('scout-opponent').click();
      }
      if (await page.getByTestId('confirm-lineup').isVisible().catch(() => false)) {
        await page.getByTestId('confirm-lineup').click();
      }

      // Lock weekly plan
      await page.getByTestId('lock-weekly-plan').click();
      await expect(page.getByTestId('simulate-command-week')).toBeEnabled();

      // Simulate
      await page.getByTestId('simulate-command-week').click();

      // Verify post-week dashboard transition
      await expect(page.getByTestId('post-week-dashboard')).toBeVisible({ timeout: 25000 });
      await page.screenshot({ path: screenshotPath('post_week_dashboard.png') });

      // Press Space to bypass animations/revelation sequence if active
      await page.keyboard.press('Space');
    });

    // 4. Inspect Aftermath panels across viewports
    await test.step('Verify aftermath across viewports', async () => {
      // Desktop Viewport
      await page.setViewportSize({ width: 1440, height: 900 });
      await page.waitForTimeout(500);
      await page.screenshot({ path: screenshotPath('aftermath_desktop.png') });

      await expect(page.getByTestId('match-score-hero')).toBeVisible();
      await expect(page.getByTestId('replay-timeline')).toBeVisible();
      await expect(page.getByTestId('key-players-panel')).toBeVisible();
      await expect(page.getByTestId('tactical-summary')).toBeVisible();
      await expect(page.getByTestId('fallout-grid')).toBeVisible();
      await expect(page.getByTestId('after-action-bar')).toBeVisible();

      // Mobile Viewport
      await page.setViewportSize({ width: 375, height: 812 });
      await page.waitForTimeout(500);
      await page.screenshot({ path: screenshotPath('aftermath_mobile.png') });
      
      // Restore Desktop Viewport
      await page.setViewportSize({ width: 1440, height: 900 });
    });

    // 5. Watch full replay and verify V11-specific features
    let replayMatchId = '';
    await test.step('Verify V11 Replay features', async () => {
      await page.getByRole('button', { name: /view full replay/i }).click();

      // Check V11 rules panel elements
      await expect(page.getByTestId('official-ruleset-banner')).toBeVisible();
      
      // Exact checks on headers in OfficialRulesPanel
      await expect(page.getByText('RULESET', { exact: true })).toBeVisible();
      await expect(page.getByText('MODE', { exact: true })).toBeVisible();
      await expect(page.getByText('GAME CLOCK', { exact: true })).toBeVisible();
      await expect(page.getByText('MATCH CLOCK', { exact: true })).toBeVisible();
      await expect(page.getByText('BURDEN', { exact: true })).toBeVisible();
      await expect(page.getByText('BALL STATES', { exact: true })).toBeVisible();
      await expect(page.getByText('RULE CALLS', { exact: true })).toBeVisible();

      // Check the canonical ruleset display name (WT-5: "Cloth Division", not
      // the raw "CLOTH-OPEN" profile key this assertion predates).
      await expect(page.getByTestId('official-ruleset-banner')).toContainText('Cloth Division');

      // Check ball count (Cloth profile has 5 balls)
      const ballContainer = page.getByText('BALL STATES', { exact: true }).locator('xpath=./following-sibling::div');
      const ballSpans = ballContainer.locator('span');
      const count = await ballSpans.count();
      expect(count).toBe(5);

      await page.screenshot({ path: screenshotPath('v11_cloth_replay.png') });

      // Click continue / exit replay
      await page.getByRole('button', { name: /back to results/i }).click();
    });

    // 6. Roster Tab exploration
    await test.step('Verify Roster Tab', async () => {
      await page.getByRole('button', { name: /Roster/i }).click();
      await expect(page.getByText('ROSTER LAB', { exact: true })).toBeVisible();
      await page.screenshot({ path: screenshotPath('roster_tab_desktop.png') });
      
      // Check viewport on mobile
      await page.setViewportSize({ width: 375, height: 812 });
      await page.waitForTimeout(500);
      await page.screenshot({ path: screenshotPath('roster_tab_mobile.png') });
      await page.setViewportSize({ width: 1440, height: 900 });
    });

    // 7. Dynasty Office Tab exploration
    await test.step('Verify Dynasty Office Tab', async () => {
      await page.getByRole('button', { name: /Dynasty Office/i }).click();
      await expect(page.getByText(/Front Office/i)).toBeVisible();
      await page.screenshot({ path: screenshotPath('dynasty_office_desktop.png') });

      // Verify that sub-tabs like Recruitment can be interacted with
      const recruitTab = page.getByRole('button', { name: /Recruit/i });
      if (await recruitTab.isVisible()) {
        await recruitTab.click();
        await page.screenshot({ path: screenshotPath('dynasty_recruitment.png') });
      }
      
      const historyTab = page.getByRole('button', { name: /History/i });
      if (await historyTab.isVisible()) {
        await historyTab.click();
        await page.screenshot({ path: screenshotPath('dynasty_history.png') });
      }

      // Check viewport on mobile
      await page.setViewportSize({ width: 375, height: 812 });
      await page.waitForTimeout(500);
      await page.screenshot({ path: screenshotPath('dynasty_office_mobile.png') });
      await page.setViewportSize({ width: 1440, height: 900 });
    });

    // 8. Standings Tab exploration
    await test.step('Verify Standings Tab', async () => {
      await page.getByRole('button', { name: /Standings/i }).click();
      await expect(page.getByText('LEAGUE OFFICE', { exact: true })).toBeVisible();
      await page.screenshot({ path: screenshotPath('standings_desktop.png') });
      
      // Check viewport on mobile
      await page.setViewportSize({ width: 375, height: 812 });
      await page.waitForTimeout(500);
      await page.screenshot({ path: screenshotPath('standings_mobile.png') });
      await page.setViewportSize({ width: 1440, height: 900 });
    });

    // 9. Advance to next week and simulate Week 2 to confirm loop stability
    await test.step('Advance and simulate Week 2', async () => {
      await page.getByRole('button', { name: /Command Center/i }).click();
      
      // Click Advance
      const advanceBtn = page.getByTestId('after-action-bar').locator('button.command-action-bar-primary');
      await advanceBtn.click();

      await expect(page.getByTestId('weekly-command-center').getByText(/week\s*0?2/i)).toBeVisible();

      // D3: clear the deliberate-action readiness gates (scout + confirm
      // lineup) before the plan can be locked.
      if (await page.getByTestId('scout-opponent').isVisible().catch(() => false)) {
        await page.getByTestId('scout-opponent').click();
      }
      if (await page.getByTestId('confirm-lineup').isVisible().catch(() => false)) {
        await page.getByTestId('confirm-lineup').click();
      }

      // Lock weekly plan
      await page.getByTestId('lock-weekly-plan').click();
      await expect(page.getByTestId('simulate-command-week')).toBeEnabled();

      // Simulate
      await page.getByTestId('simulate-command-week').click();

      // Verify aftermath Week 2
      await expect(page.getByTestId('post-week-dashboard')).toBeVisible({ timeout: 25000 });
      await page.keyboard.press('Space');
      await page.screenshot({ path: screenshotPath('aftermath_week2.png') });
    });

    // 10. Check that no console errors occurred
    await test.step('Verify no console errors occurred', () => {
      expect(consoleErrors, consoleErrors.join('\n')).toEqual([]);
    });
  });
});
