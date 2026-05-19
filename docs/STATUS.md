# Repository Status

Canonical snapshot of what is actually built and what is still open. When code
state changes materially, update this file in the same pass. If this file and
the source disagree, the source wins — then fix this file.

Last updated: 2026-05-19.

## Current Phase

Post-V10. The game is playable end to end: career creation, weekly command
loop, match replay, playoffs, offseason ceremonies, and multi-season dynasty
history all work in the browser. No milestone is in active development. The
current focus is **refinement and gameplay optimization**, not new systems.

## Shipped And Verified

- **V1–V10** — see `docs/specs/MILESTONES.md` for the per-milestone index.
- **UX Polish initiative** (three waves, 15 subplans; plan archived at
  `docs/archive/plans/2026-05-08-ux-polish/`). The frontend reflects it:
  the three-mode `MatchWeek` shell, sequenced aftermath blocks, the Roster
  theater view, Dynasty Office `Recruit`/`History` sub-tabs, the `voice_*`
  writer modules, offseason ceremony takeovers, the Build-From-Scratch new-game
  flow, and the rebuilt Match Replay.
- **Playoff bracket** on the Standings screen (`/api/playoffs/bracket` +
  `PlayoffBracket` component).
- **Browser playthrough bug fixes B1–B14** from the 2026-05-18/19 Playwright
  playthrough — see `docs/archive/playthrough-bug-log.md`.

## Open Work And Known Gaps

1. **O1 — engine balance (highest-priority open item).** A read-only Monte
   Carlo (`tools/o1_variance_probe.py`) shows a +72 net-OVR favorite wins only
   ~52% of matches; OVR barely matters until the gap is enormous. A fix is
   *proposed but deliberately not applied* — per the engine integrity rules it
   needs explicit sign-off and golden-log regeneration in the same commit.
   Full write-up: `docs/archive/playthrough-bug-log.md` (O1 section).
2. **V11 — AI Program Managers (partially scaffolded).** `ai_program_manager.py`
   (~100 lines) exists and is wired into `command_week_service.py` and
   `use_cases.py`, but V11 has no spec and no row in `MILESTONES.md`. Roadmap
   intent: `docs/specs/long-range-playable-roadmap.md`.
3. **V12 — Broadcast / Presentation layer.** Not started. Roadmap only.
4. **Product-coherence-audit follow-ups.** The 2026-05-15 audit
   (`docs/archive/product-coherence-audit.md`) proposed 10 coherence fixes plus
   10 "make it feel real" changes. Several label/copy fixes appear to have
   landed in later commits, but the audit was **never systematically
   reconciled** against current code. Fix 1 ("Did Your Plan Work?" verdict) was
   explicitly deferred and still needs a backend verdict generator. A
   verification pass is owed.
5. **Dead Tkinter-era code.** `gui.py`, `manager_gui.py`, `ui_components.py`,
   `ui_formatters.py`, `ui_style.py`, and likely `court_renderer.py`
   (~5,900+ lines combined) are imported by nothing the web app runs. The
   `PlayerArchetype` enum/field is vestigial (defaults to `TACTICAL`, never
   assigned). These are code-cleanup candidates; not touched by the
   documentation pass that produced this file.

## Sources Of Truth

1. `AGENTS.md` — repo rules, workflow, architecture snapshot, current facts.
2. `docs/README.md` — documentation map and reading order.
3. `docs/STATUS.md` — this file: current build state and open work.
4. `docs/specs/MILESTONES.md` — the milestone history index.
5. Source code and tests — final authority when docs and code disagree.
