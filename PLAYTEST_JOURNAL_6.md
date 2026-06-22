# Playtest 6 Journal

Headline: P1 - Premier top-two-to-Worlds promise is visibly unreliable.

## Setup

- Branch: `feature/v24-the-board`.
- Existing unrelated untracked files before run: `PLAYTEST_JOURNAL_5.md`, `opencode.json`.
- Install completed: `python -m pip install -e '.[dev]'`.
- Frontend production build completed from `frontend/`: `npm run build`.
- Launch command: `python -m dodgeball_sim.web_cli --port 8010`.
- Port result: app bound `127.0.0.1:8010`. Launcher log said "Port 8000 is occupied; using API port 8010." I did not stop or kill anything on 8000.
- Browser console errors: zero.
- Pare MCP: unavailable in this session, so normal local commands were used.

## PT5 Fix Confirmations

- Final score, D3 S1 W1 draw: `Final game score` showed Old Quarter Wanderers 6, Ledger Six 6, with game-by-game set results.
- Final score, D3 S1 W2 official win: `Final game score` showed Ledger Six 7, Harborside Rovers 5, never 0-0.
- Legal-six framing, D3 pre-sim: six selected founders were treated as the fielded six; Sim Lock showed `Lineup: Starting six confirmed`, not a 6/12 shortfall.
- Legal-six framing, D3 Signing Day: `A six fields a full lineup - your 6-player squad is ready for the season. Signings are optional bench depth`, while showing `ROSTER SIZE 6 / 12`.
- Scouting Network upgrades: Level 1 showed `BOARD 31 PROSPECTS`; after paid L2 it still showed 31; after paid L3 it still showed 31.
- Media Moment latch: selected `Take the high road`; option visibly changed to `SELECTED` before `CONFIRM & CONTINUE`.
- Signing Day snipe receipts: Savannah Herrera snipe said `their offer 114 beat yours 101`; Rafael Nguyen snipe said `their offer 98 beat yours 25`.
- Class Report labels: tiles read `RIVAL SIGNINGS (LEAGUE)` and `ROOKIES (LEAGUE)`; zero-signing copy stayed consistent.
- Facility purchase: Staff summary changed from `FACILITIES 0 / No facility upgrades tracked` to `FACILITIES 1 / recovery_suite` after buying Recovery Suite.
- Transfer Period latch: Moana Lund switched to `Letting walk`, then back to `Re-signing`, before confirmation.
- Transfer retention: Moana Lund did not appear in the next Signing Day free-agent list after being left on `Re-signing`.

## New Trust-Break Findings

- P1 - League Wire duplicates and drops scorelines. Screen: D3 S1 W2 and Premier S4 W2 Command Center. Claim/data: debriefs showed 6-6, 7-5, and 9-7 game-point results, but League Wire displayed duplicated rows like `W1 - Draw vs Old Quarter Wanderers` and `W1 - Loss vs Solstice Flare` without game-point scorelines. Repro: play a match, click `NEXT WEEK`.
- P1 - Premier top-two-to-Worlds promise is not faithfully receipted. Screen: Premier takeover offseason recaps. S1: Aurora finished #2, but Worlds only showed Rhein Kollektiv over Stockholm Norrsken. S2: Aurora finished #1 and was Premier champion, but Worlds only showed Osaka Tempo over Bahia Cobras. S3: Aurora finished #3, outside the promised top two, yet Worlds showed Aurora losing the final. Repro: `codex-pt6-prem`, fast-forward S1-S3 to offseason recaps.
- P1 - Transfer Period can show conflicting retention states. Screen: D3 S2 offseason Transfer Period. Eun Keita row showed `Re-signing` and also `legacy F - won't re-sign` at the same time while being chased by Aurora Sentinels.
- P2 - Debrief factor chip still says `Survivors 0-0` inside a correct game-point win. Screen: D3 S1 W2 debrief. Final score was 7-5, but Primary Factor row included `Survivors 0-0`, `Margin 0`, `Set margin 2`.
- P2 - Premier stakes wording is weaker than requested. Preview/Standings say `Bottom two teams face relegation`; pyramid rows mark `DROP`, and movement receipts directly relegate them. Requested copy was `Bottom two relegate`.
- P2 - Weather catch-effect evidence is mixed. Reward-catches samples: `Catches 13-19` over 14 game points and `Catches 19-10` over 15. Tighter-catches samples: `Catches 25-6` over 16 and `Catches 9-15` over 16. The later tighter sample is lower, but the first tighter-catches game was as catch-heavy as reward seasons.
- P2 - AI tactic drift is not visible in sampled Standings plan rows. Premier S1/S2/S4 Week 1 standings showed every AI club with `PLAN BALANCED`, despite multiple seasons of champions and archetype churn. If drift exists, this surface does not expose it.
- P2 - Meta report ticker lines were not found in sampled wires. I saw weather bulletins, result rows, and league-leader lines, but no data-trend ticker line to verify against standings/box data.

## Evidence Ledger

- D3 founded path completed three seasons: District -> Challenger -> Premier promotion path receipted.
- Premier takeover path completed three seasons and sampled Season 4 Week 2.
- D3 S2 reward-catches bulletin: `officials will reward clean catches this season`.
- D3 S2 W1: `Catches 13-19`, 32 total catches over 14 game points.
- D3 S3 W1: `Catches 19-10`, 29 total catches over 15 game points.
- Premier S3 tighter-catches bulletin: `borderline catches are judged tighter`.
- Premier S3 W1: `Catches 25-6`, 31 total catches over 16 game points.
- Premier S4 W1: `Catches 9-15`, 24 total catches over 16 game points.

## Cleanup

- Purged `saves/codex-pt6-d3.db`.
- Purged `saves/codex-pt6-prem.db`.
- Stopped the port 8010 server process started for this run.
- Final check: no listener on 8010 and no `codex-pt6-*` save files remain.
