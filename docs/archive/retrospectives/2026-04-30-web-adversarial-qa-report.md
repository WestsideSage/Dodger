# 2026-04-30 Web Adversarial QA Report

## Verdict

**Not stable enough to move cleanly into the next phase without a small hardening pass.**

The fresh web career playthrough is broadly healthy: all six screens rendered, the match replay/report flow survived reload and tab switching, progression controls completed, bad SPA/API paths behaved correctly, and no browser console errors appeared. The blocker is recovery/state truth: the active restored save was already in a stale Week 5 pre-match state even though every Week 5 match had been recorded, leaving the hub enabled but unable to play anything.

## What Ran

- Preflight DB backup: `output/web-adversarial-qa/dodgeball_sim.20260430-003645.qa-backup.db`
- Browser runner: `tools/web_qa/adversarial_browser_playthrough.mjs`
- Node launcher: `tools/web_qa/run_browser_playthrough.mjs`
- Final browser results: `output/web-adversarial-qa/results.json`
- Screenshots: `output/web-adversarial-qa/screenshots/`
- API snapshots: `output/web-adversarial-qa/api/`
- Console captures: `output/web-adversarial-qa/console/`

Preflight checks:

- `npm.cmd run build` from `frontend/` passed.
- `python -m pytest tests/test_server.py -q` passed with the known pytest cache permission warning.

Final corrected browser pass:

- 19 assertions passed.
- 0 assertions failed.
- 3 findings remained, all tied to tactics slider mutation through browser automation.
- 0 console errors/warnings were captured across the tested screens and flows.

## Findings

### 1. Active Save Can Become Stuck In A Completed-Week Pre-Match State

Severity: **High**

The restored active DB reported:

- `career_state_cursor`: `season_active_pre_match`, season 1, week 5
- `match_records`: 15 total matches, including all 3 Week 5 matches

The browser hub therefore showed “Ready for Week 5 matchup” with enabled sim buttons, but clicking `Play Next Match` produced “No matches simulated.” That is a dead-end-feeling state for the player because the UI says play is available while the schedule has no unplayed match left.

Evidence:

- Preserved DB: `output/web-adversarial-qa/dodgeball_sim.20260430-004037.pre-fresh-run.db`
- Screenshot from the stale run was superseded by later screenshots, but the DB evidence is durable: all Week 5 records exist while the cursor is still pre-match.

Recommended fix:

- Add startup/status normalization that detects “current week has no remaining matches” and advances the cursor to the correct next state.
- Add a server regression using a copied stale cursor + completed week fixture: `/api/status` should not report a playable pre-match state when no eligible match remains.

### 2. Tactics Sliders Do Not Become Dirty Under Keyboard-Driven Browser Control

Severity: **Medium**

The browser runner found all eight range inputs, but setting them to `0`, `1`, and `0.5` through click + keyboard input never exposed `Save Tactics`; the button remained `Saved`.

Evidence:

- `output/web-adversarial-qa/screenshots/tactics-save-missing-0.png`
- `output/web-adversarial-qa/screenshots/tactics-save-missing-1.png`
- `output/web-adversarial-qa/screenshots/tactics-save-missing-0-5.png`
- `output/web-adversarial-qa/results.json`

This may be either a real keyboard-accessibility issue with the range controls or a limitation of the current browser automation surface. It should be manually checked with keyboard-only input. If manual keyboard input works, add stable test hooks for the QA runner. If it does not, the sliders need accessible keyboard behavior before the tactics screen can be considered robust.

### 3. Mobile Visual Pass Was Not Automated

Severity: **Low**

The in-app browser API available in this session did not expose viewport resizing, so the script could not perform the planned mobile-width inspection. Desktop screenshots show no obvious layout overlap in the tested flows.

Evidence:

- `output/web-adversarial-qa/results.json`
- Desktop screenshots under `output/web-adversarial-qa/screenshots/`

Recommended fix:

- Use a Playwright CLI fallback or add a browser-runner capability for viewport sizing in a later QA pass.

## Healthy Areas

- Hub, roster, tactics, standings, schedule, and news all rendered from a fresh DB.
- `Play Next Match` opened `Match Replay` from a fresh career.
- Replay controls worked: `Next`, `Key Play`, `Back`.
- Pending replay survived browser reload.
- Pending replay survived leaving the hub and returning.
- `Continue` closed the report and returned to the hub.
- `Sim Week`, `Sim To User Match`, `Sim 2 Weeks`, and `Sim To Milestone` completed without console errors.
- `/api/not-real` returned the explicit unknown API JSON response rather than the SPA shell.
- Non-API deep paths loaded the SPA fallback.

## Next Hardening Pass

Fix the stale cursor recovery first. After that, verify tactics keyboard behavior manually and either repair the sliders or add stable automation hooks. The current web foundation is close, but the stale active-save state is exactly the kind of recovery edge that will confuse players during longer seasons.
