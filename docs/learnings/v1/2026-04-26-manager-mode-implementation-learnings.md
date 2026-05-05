# Manager Mode Implementation Learnings

Date: 2026-04-26

## What Worked

- A dedicated `manager_gui.py` was the right path. The existing `gui.py` is a useful sandbox, but Manager Mode needs a season-first navigation model, career cursor routing, and off-season flows. Keeping the sandbox intact avoided breaking the friendly/testing workflow while letting the new UI move quickly.
- Engine contracts from M0 paid off immediately. `CareerStateCursor`, `LineupResolver`, `compute_match_mvp`, `season_format_summary`, and `win_probability.py` gave the UI real data surfaces instead of forcing display logic to invent state.
- The replay became much more legible once the court renderer read eliminations from `MatchEvent.state_diff["player_out"]`. Earlier rendering looked alive but did not clearly show who went out. The state diff is the reliable source.
- Automatic replay pacing is a large feel improvement even with simple visuals. Holding hits/catches longer than misses makes the match read like a sport without adding animation complexity or changing engine outcomes.
- Pure helper functions made GUI phases testable. Helpers such as `build_league_leaders`, `build_schedule_rows`, `build_wire_items`, `build_player_profile_details`, `build_offseason_ceremony_beat`, and `friendly_match_stats` kept important behavior covered without needing Tkinter automation.
- Parallel agents helped once the vertical slice existed. Player Profile, Off-season Ceremony, and Friendly Mode were separable enough to split, then integrate locally.
- Closing V1 required moving off-season logic from "ceremony copy" to actual persisted state. Reusing the same engine primitives as `dynasty_cli.py` kept Manager Mode accurate: development uses `apply_season_development`, retirements use `should_retire`, and rookies come from `generate_rookie_class`.

## Technical Gotchas

- This workspace is not a git repository, so commit-oriented plan steps cannot be completed here. Document outcomes clearly because there is no local commit log.
- Pytest cache/temp behavior can hit Windows permission issues in this environment. Use `-p no:cacheprovider` when needed, and keep `pyproject.toml` `norecursedirs` pointed away from generated `output/` folders.
- Broad `pytest` collection can accidentally traverse generated output unless ignored. The project now excludes `output`, `.pytest_cache`, build folders, and egg-info from test discovery.
- `show_report()` now has two meanings: career report acknowledgement and non-career report viewing. `_close_report()` must preserve that distinction so opening a past report from League does not advance the career cursor.
- Friendly mode must never call persistence write paths for match records, standings, schedule, stats, or cursor. It should remain in-memory and return to Splash.
- Off-season initialization must be idempotent. The `offseason_initialized_for` state key prevents repeated visits to the ceremony from applying development, aging, retirements, and rookie generation more than once.
- `save_free_agents()` rewrites the full free-agent pool. Draft signing code must remove the selected rookie from the loaded list, then save the complete remaining list.

## Design Lessons

- The app feels more like a manager sim when the first screen after onboarding is operational: next match, standings, wire, roster, tactics, league. Avoid returning to sandbox-style “run any match” framing inside career mode.
- Text is useful, but the match needs visual punctuation. Rings, trajectories, final banner, and MVP callout created more perceived depth than adding more report copy.
- Player attachment starts with click-through. Roster rows and league leaders opening a profile made players feel less like IDs even before portraits or richer history.
- The League tab should behave like memory, not just a table. Past matches opening reports and future matches showing opponent context made it useful between matches.

## Next Engineering Guidance

- Keep preserving the invariant: UI is downstream from the event log and persisted engine records.
- Before expanding off-season mechanics further, build the missing V2 engine systems first. Do not add scouting/recruitment UI that implies AI competition or persistent scouting confidence until those models exist.
- V1 Draft now mutates the user's roster, but it is intentionally simple: one rookie signing, no AI competition, no public/private information split. That makes V2 recruitment planning cleaner because the current feature is a narrow baseline rather than a fake version of the target system.
- The next substantive milestone should be V2-A scouting model planning, followed by V2-B recruitment domain planning. Presentation polish can happen independently, but the major gameplay gap is now engine depth.
