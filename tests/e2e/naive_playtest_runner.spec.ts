import { expect, test } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const baseUrl = 'http://127.0.0.1:8000';
const outputDir = path.join(__dirname, '../../playtest_output');

// Ensure output directory exists
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

test.describe('Dodger Naive Playtester Playthrough', () => {
  test('New Custom Club Dynasty Playthrough', async ({ page }) => {
    // 1. Setup and configurations
    test.setTimeout(480000); // Allow up to 8 minutes for a deep playthrough
    await page.setViewportSize({ width: 1440, height: 900 });

    const consoleLogs: string[] = [];
    const consoleErrors: string[] = [];

    page.on('console', (msg) => {
      const txt = msg.text();
      consoleLogs.push(`[Console ${msg.type()}] ${txt}`);
      console.log(`[Browser Console] ${msg.type().toUpperCase()}: ${txt}`);
    });

    page.on('pageerror', (err) => {
      consoleErrors.push(`[Page Error] ${err.message}`);
      console.error(`[Browser Page Error] ${err.message}`);
    });

    // 2. Open game landing page
    console.log('Navigating to Dodger home page...');
    await page.goto(baseUrl);
    await page.waitForTimeout(2000);

    // 3. Unload save if one is already active to start completely fresh
    const menuBtn = page.getByRole('button', { name: /Back to save menu|Menu/i });
    if (await menuBtn.isVisible()) {
      console.log('Active save detected. Navigating back to save menu for a fresh start.');
      await menuBtn.click();
      await page.waitForTimeout(2000);
    }

    // Double check that we are at the save menu screen
    await expect(page.getByTestId('save-menu')).toBeVisible();
    await page.screenshot({ path: path.join(outputDir, '01_save_menu.png') });

    // 4. Onboarding: Build from Scratch
    console.log('Starting custom "Build from Scratch" game onboarding...');
    await page.getByTestId('new-game-tab').click();
    await page.waitForTimeout(500);

    await page.locator('button:has-text("Build from Scratch")').click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(outputDir, '02_build_identity.png') });

    // Step 1: Program Identity
    const saveName = `playtest-naive-${Date.now()}`;
    console.log(`Creating custom save: ${saveName}`);
    await page.locator('input[placeholder="My Career"]').fill(saveName);
    await page.locator('input[placeholder="e.g. Iron Hawks"]').fill('Seattle Steelheads');
    await page.locator('input[placeholder="e.g. Northwood"]').fill('Seattle');
    
    // Select kit colors preset (Ocean)
    await page.locator('button[title="Ocean"]').click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(outputDir, '03_identity_filled.png') });

    // Move to Step 2
    await page.locator('button:has-text("Next: Coach Profile")').click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(outputDir, '04_coach_step.png') });

    // Step 2: Head Coach
    await page.locator('input[placeholder="e.g. Ray Holloway"]').fill('Coach Maurice');
    // Select Tactical Mastermind archetype
    await page.locator('button:has-text("Tactical Mastermind")').click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(outputDir, '05_coach_filled.png') });

    // Move to Step 3
    await page.locator('button:has-text("Next: Recruit Roster")').click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(outputDir, '06_starting_recruits.png') });

    // Step 3: Starting Roster Recruitment
    console.log('Recruiting starting roster from prospects...');
    const prospectButtons = page.locator('button[role="checkbox"]');
    await prospectButtons.first().waitFor({ state: 'visible', timeout: 5000 });
    
    const prospectCount = await prospectButtons.count();
    console.log(`Starting prospects loaded. Total available: ${prospectCount}`);
    
    // Select the first 6 prospects
    for (let i = 0; i < 6; i++) {
      const prospectText = await prospectButtons.nth(i).innerText();
      console.log(`Selecting prospect ${i + 1}: ${prospectText.split('\n')[0]}`);
      await prospectButtons.nth(i).click();
      await page.waitForTimeout(200);
    }
    
    await page.screenshot({ path: path.join(outputDir, '07_starting_roster_selected.png') });

    // Commit starting roster
    console.log('Committing starting roster...');
    await page.locator('button:has-text("Commit Roster")').click();

    // 5. Game week loop
    console.log('Waiting for the weekly Command Center to load...');
    await expect(page.locator('[data-testid="weekly-command-center"], [data-testid="season-preview"]').first()).toBeVisible({ timeout: 20000 });
    if (await page.getByTestId('season-preview').isVisible()) {
      await page.getByRole('button', { name: /To the Command Center/i }).click();
    }
    await expect(page.getByTestId('weekly-command-center')).toBeVisible();
    await page.screenshot({ path: path.join(outputDir, '08_command_center_loaded.png') });

    let seasonCount = 1;
    let weekCount = 1;
    let loopIterations = 0;
    const maxIterations = 35; // Failsafe to prevent infinite loops

    while (loopIterations < maxIterations) {
      loopIterations++;
      await page.waitForTimeout(1500);

      // Handle Season Preview overlay if present (e.g. at the start of Season 2)
      if (await page.getByTestId('season-preview').isVisible()) {
        console.log('Dismissing Season Preview...');
        await page.getByRole('button', { name: /To the Command Center/i }).click();
        await page.waitForTimeout(500);
        continue;
      }

      // Check if we are in the offseason ceremony state
      const isOffseason = await page.getByTestId('match-week-offseason').isVisible();
      if (isOffseason) {
        console.log(`\n--- OFFSEASON CEREMONY DETECTED (Season ${seasonCount}) ---`);
        
        // Press Space immediately to skip any animation delay in CeremonyShell so the button renders
        await page.keyboard.press('Space');
        await page.waitForTimeout(800);

        // Find the continue button or signing button
        const continueBtn = page.locator('.command-action-buttons button, .command-action-bar button').first();
        
        if (await continueBtn.isVisible()) {
          const btnText = await continueBtn.innerText();
          console.log(`Ceremony action button visible: "${btnText}"`);

          // Check if we are on the Signing Day recruitment choice view
          const isRecruitmentChoice = await page.getByTestId('offseason-recruitment-action').isVisible();
          if (isRecruitmentChoice) {
            console.log('Signing Day: Selecting the highest-rated prospect on our recruit desk.');
            const prospectRows = page.getByTestId('recruitment-prospect-row');
            if (await prospectRows.count() > 0) {
              const bestProspectText = await prospectRows.first().innerText();
              console.log(`Signing prospect: ${bestProspectText.split('\n')[0]}`);
              await prospectRows.first().click();
              await page.waitForTimeout(300);
            }
            await page.screenshot({ path: path.join(outputDir, `s${seasonCount}_offseason_signing_choice.png`) });
          } else {
            const titleLoc = page.locator('.dm-ceremony h1, .command-offseason-shell h2').first();
            let stepTitle = 'Offseason Ceremony Step';
            if (await titleLoc.isVisible()) {
              stepTitle = await titleLoc.innerText();
            }
            console.log(`Viewing ceremony step: "${stepTitle}"`);
            await page.screenshot({ path: path.join(outputDir, `s${seasonCount}_offseason_step_${stepTitle.replace(/\s+/g, '_').toLowerCase()}.png`) });
          }

          // Click the button to advance
          console.log(`Clicking ceremony action button: "${btnText}"`);
          await continueBtn.click();

          // If the button text is "Begin Season" or "Reveal Schedule" or "Reveal Schedule →", we are transitioning to a new season
          if (/begin|reveal schedule/i.test(btnText)) {
            console.log(`Season ${seasonCount} successfully completed! Entering Season ${seasonCount + 1}.`);
            seasonCount++;
            weekCount = 1;
            await page.waitForTimeout(3000);
            
            // If we have completed season 1 and entered season 2 command center, we have completed a full game loop!
            if (seasonCount > 2) {
              console.log('Playthrough has successfully finished two seasons! Stopping.');
              break;
            }
          }
        } else {
          console.log('Offseason visible but no ceremony control action button found. Waiting...');
          await page.waitForTimeout(1000);
        }
        continue;
      }

      // Check if we are in the aftermath (post-sim dashboard) state
      const isPostSim = await page.getByTestId('post-week-dashboard').isVisible();
      if (isPostSim) {
        console.log(`\n--- WEEK ${weekCount} POST-SIM DEBRIEF ---`);
        
        // Skip animation
        await page.keyboard.press('Space');
        await page.waitForTimeout(1000);

        // Fetch score and aftermath summary
        const scoreLoc = page.getByTestId('match-score-hero');
        const verdictLoc = page.getByTestId('match-verdict');
        let score = 'No match scheduled (Bye Week)';
        if (await scoreLoc.isVisible()) {
          score = await scoreLoc.innerText();
        }
        let verdict = 'No verdict line (Bye Week)';
        if (await verdictLoc.isVisible()) {
          verdict = await verdictLoc.innerText();
        }
        
        console.log(`Match score summary: ${score.replace(/\n+/g, ' ')}`);
        console.log(`Match verdict: ${verdict}`);

        // Capture aftermath screenshot
        await page.screenshot({ path: path.join(outputDir, `s${seasonCount}_w${weekCount}_aftermath.png`) });

        // Let's check if there are any console errors
        if (consoleErrors.length > 0) {
          console.log(`WARNING: Console errors detected during week ${weekCount}:`);
          consoleErrors.forEach(err => console.log(`  ${err}`));
          consoleErrors.length = 0; // Clear handled errors
        }

        // Advance to next week
        const advanceBtn = page.getByTestId('after-action-bar').locator('button.command-action-bar-primary');
        await expect(advanceBtn).toBeVisible({ timeout: 10000 });
        const advanceText = await advanceBtn.innerText();
        console.log(`Clicking aftermath advance button: "${advanceText}"`);
        await advanceBtn.click();
        
        weekCount++;
        await page.waitForTimeout(2000);
        continue;
      }

      // Check if we are in the pre-sim weekly command center
      const isPreSim = await page.getByTestId('weekly-command-center').isVisible();
      if (isPreSim) {
        console.log(`\n--- WEEK ${weekCount} PRE-SIM (Season ${seasonCount}) ---`);
        
        // Let's check for bye weeks
        const isByeWeekText = await page.getByTestId('presim-command-strip').innerText();
        const isBye = /BYE WEEK/i.test(isByeWeekText);
        
        if (isBye) {
          console.log('Week is a BYE WEEK. Rest and plan training.');
        } else {
          // Log opponent and edge
          const stripText = await page.getByTestId('presim-command-strip').innerText();
          console.log(`Context strip: ${stripText.replace(/\n+/g, ' | ')}`);
          
          // Tactical adjustments: check for coach recommendation alert and apply it if present
          const planReadout = page.getByTestId('plan-readout');
          if (await planReadout.isVisible()) {
            const readoutText = await planReadout.innerText();
            console.log(`Plan Status Alert: ${readoutText.replace(/\n+/g, ' ')}`);
            
            const recommendationBtn = planReadout.locator('button');
            if (await recommendationBtn.isVisible()) {
              const recLabel = await recommendationBtn.innerText();
              console.log(`Applying coach tactical adjustment: "${recLabel}"`);
              await recommendationBtn.click();
              await page.waitForTimeout(500);
            }
          }
        }

        // Capture pre-sim screenshot
        await page.screenshot({ path: path.join(outputDir, `s${seasonCount}_w${weekCount}_presim.png`) });

        // Lock weekly plan
        const lockBtn = page.getByTestId('lock-weekly-plan');
        if (await lockBtn.isVisible() && await lockBtn.isEnabled()) {
          console.log('Locking weekly plan...');
          await lockBtn.click();
          await page.waitForTimeout(1000);
        }

        // Simulate Command Week
        const simBtn = page.getByTestId('simulate-command-week');
        if (await simBtn.isVisible() && await simBtn.isEnabled()) {
          console.log(`Simulating Week ${weekCount}...`);
          await simBtn.click();
          
          // Wait for simulation to run and post-sim screen to load
          await expect(page.getByTestId('post-week-dashboard')).toBeVisible({ timeout: 40000 });
        } else {
          console.error(`ERROR: Simulate week button was not enabled or visible! Loop iteration: ${loopIterations}`);
          await page.screenshot({ path: path.join(outputDir, `s${seasonCount}_w${weekCount}_error_sim_disabled.png`) });
          break;
        }
        continue;
      }

      // If we are not in any of these major game states, let's log the page content and wait
      console.log('Unknown game state. Current URL:', page.url());
      await page.screenshot({ path: path.join(outputDir, `unknown_state_${Date.now()}.png`) });
      await page.waitForTimeout(2000);
    }

    console.log(`\nPlaythrough finished. Final state: Season ${seasonCount}, Week ${weekCount}`);
    
    // Dump diagnostic errors gathered during playthrough
    console.log(`\n--- PLAYTHROUGH DIAGNOSTICS ---`);
    console.log(`Total console errors: ${consoleErrors.length}`);
    if (consoleErrors.length > 0) {
      consoleErrors.forEach(err => console.log(`- ${err}`));
    }
  });
});
