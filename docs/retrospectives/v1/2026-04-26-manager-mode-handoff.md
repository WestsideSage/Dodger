# Manager Mode Handoff

Date: 2026-04-26

## State Snapshot

Manager Mode now has a playable season loop:

- Launch with `python -m dodgeball_sim`.
- Start a new career from a curated club.
- Play weekly matches through Match Preview, automatic Replay, and Match Report.
- Continue through the full regular season to an off-season ceremony.
- Apply v1 off-season development, aging, retirements, and a one-rookie Draft signing before the next season.
- Begin the next season from Schedule Reveal.
- Use Friendly Match from Splash without touching career state.

Major files changed:

- `src/dodgeball_sim/manager_gui.py`
  - Dedicated Manager Mode GUI.
  - Career routing from `CareerStateCursor`.
  - Curated career initialization.
  - Hub, Roster, Tactics, League, Match Preview, Replay, Report, Player Profile, Friendly, and Off-season Ceremony screens.
  - Pure helper functions for leaders, wire, profiles, friendly stats, replay labels, off-season beats, career summaries, and off-season roster mutation.
  - Match Report player links and League Wire award click-through to Player Profile.
  - Deterministic v1 off-season flow: career stat rollup, development/aging, retirements, rookie pool generation, and one signed rookie for the user's club.
- `src/dodgeball_sim/court_renderer.py`
  - More readable court replay.
  - Team color bands, throw trajectories, target rings, possession highlights, eliminations from `state_diff`, and final panel.
- `src/dodgeball_sim/__main__.py`
  - Makes `python -m dodgeball_sim` launch Manager Mode.
- `pyproject.toml`
  - Adds `dodgeball-manager`.
  - Adds pytest discovery exclusions for generated folders.
- `tests/test_manager_gui.py`
  - Covers Manager Mode helper contracts.

M0 engine/state contracts are also in place:

- `src/dodgeball_sim/win_probability.py`
- `src/dodgeball_sim/lineup.py`
- `src/dodgeball_sim/career_state.py`
- schema v7 with club identity and lineup persistence
- `compute_match_mvp`
- scheduler v1 format summary

## Test Status

Latest verified commands:

```powershell
python -m pytest -q -p no:cacheprovider
python -m pytest tests/test_regression.py -v -p no:cacheprovider
```

Both passed. The collected test count after the V1 closeout work was 153.

The Phase 1 golden regression remains unchanged.

## Known Issues

- This workspace is not a git repository, so no commits were created.
- Friendly Mode uses the sample matchup and fixed defaults. It is intentionally minimal and in-memory.
- Player Profile is useful but still text-led. Report top performers, League leaders, and Wire awards now click through, but the presentation can still be richer in V2.
- No automated browser/Tkinter screenshot review was run in this session. The user manually played through and confirmed the season recap path looked good.
- V1 Draft is deliberately simple: one deterministic best-rookie signing for the user's club if they continue without manually pressing Sign Best Rookie. There is no AI competition or sniping until V2 recruitment exists.

## Gotchas

- Do not route past reports through `_acknowledge_report()`. Only the pending career report should advance the cursor.
- Do not persist Friendly Mode results.
- `initialize_manager_offseason()` is idempotent by `offseason_initialized_for`; keep that guard or repeated visits to the ceremony will double-age rosters.
- `save_free_agents()` rewrites the full free-agent pool. Always pass the complete remaining pool after signing a rookie.
- If broad pytest collection fails due generated folders, use `-p no:cacheprovider`; `pyproject.toml` now also excludes `output/`.
- The old `dodgeball-sim-gui` sandbox still exists and should not be removed without a deliberate Friendly Mode replacement decision.

## Next Steps

V1 is now structurally closed enough to begin V2 planning. Recommended V2 planning focus:

1. Stateful scouting model: scout entities, assignments, confidence persistence, and fuzzy profile data.
2. Recruitment domain model: AI club preferences, sign rounds, public/private evaluations, and sniping.
3. Build-a-Club path once scouting/recruitment make expansion play meaningful.
4. Optional V2 presentation upgrades: richer profile card, Records/Hall of Fame beats, and formal screenshot/timing review.

First concrete task for the next agent:

- Start by writing the V2-A scouting model plan. The V1 GUI now has enough season/off-season continuity to consume persistent scouting state when the engine model exists.
