# V5 Weekly Command Center Learnings

Date: 2026-05-02
Milestone: V5

## Architectural Findings

1. **Tactics Honesty:** Exposing detailed tactical settings on the frontend requires strict alignment with the simulation math. We found that features like `sync_throws` and `rush_frequency` were treated as binary or purely cosmetic until the V5 audit. Tying these directly to RNG-based fatigue and accuracy scales in `engine.py` makes the simulation fundamentally honest to user choices.
2. **Command Context Injection:** Adding the new Command Center layer required updating the `engine.py` pipeline to pass through `rng` states and policies during simulation ticks, confirming that adding high-level program "Intents" seamlessly integrates with the robust V4 engine.
3. **Automated Browser Playthrough:** The Playwright-based AI walkthrough agent relies heavily on robust selectors and clear text identifiers. Ensuring `adversarial_browser_playthrough.mjs` targets the new `command` tab correctly guarantees that the new primary loop (Simulate Command Week -> Post-Week Dashboard) is not skipped in QA passes.

## Post-QA Learnings (2026-05-04)

4. **Shared module extraction is the safe pattern for GUI↔Web parity.** When a flow (offseason ceremony) existed only in the Tkinter GUI, the correct fix was not to duplicate the logic into `server.py` but to extract a `offseason_ceremony.py` module that both consumers import. This prevents the two paths from diverging silently again. Future features that exist in the GUI but are missing from the web app should follow this same extraction pattern.

5. **`finalize_season` must be called before `initialize_manager_offseason`.** Awards, player season stats, and career summaries are computed by `finalize_season`. If `initialize_manager_offseason` runs first it will use stale or missing award data. The `GET /api/offseason/beat` endpoint enforces this order and makes both calls idempotent (keyed on season number) so retries and page refreshes are safe.

6. **Trait variation requires explicit RNG sampling — do not rely on defaults.** `PlayerTraits()` produces flat-50 across all four traits, which makes every player statistically identical and renders the development system meaningless. The fix is to sample with `rng.gauss()` at roster creation time. Any new trait-like field added to the player model should be sampled at init, not left as a default, unless the intent is an explicit baseline.

7. **Real names from a shared name list, not from positional labels.** Using positional labels (`"{Club} Captain"`) as names is a footgun: any logic that parses the name to infer the role will break when names become real. The V5 fix imports `_FIRST_NAMES`/`_LAST_NAMES` from `randomizer.py` and derives role solely from roster-position index via `_ROLE_LABELS`. Do not infer role from name string.

8. **A unified dev launcher eliminates the "two terminals" friction.** `DODGEBALL_DEV=1 python -m dodgeball_sim` now spawns Vite as a subprocess, opens the browser, and starts FastAPI with hot-reload in one command. The key design choices: `npm.cmd` on Windows vs `npm` on Unix, `subprocess.Popen` (not `run`) for the non-blocking Vite process, `vite_proc.terminate()` in a `finally` block to avoid orphaned processes, and a small `_open_browser` thread delay (2.5 s) so Vite is ready before the browser tab appears.

9. **Uvicorn `reload=True` resets module-level globals.** The `_active_save_path` global in `server.py` is cleared on each reload. In dev mode this means any loaded save must be reloaded after a code change triggers a hot-reload. This is an acceptable dev-mode trade-off (saves are persisted to disk) but it should not be papered over with an in-memory workaround — the right fix is for the client to detect a 404 on `/api/status` and offer a reload prompt.

10. **Offseason state routing belongs in App.tsx, not in each screen component.** Checking `OFFSEASON_STATES` at the top-level router (after `/api/status` fetch) is cleaner than adding conditional branches inside `WeeklyCommandCenter` or `PostWeekDashboard`. Any new top-level career state should be added to the `Screen` union type and routed from the same `useEffect` that handles the status check.
