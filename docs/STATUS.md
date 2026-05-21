# Repository Status

Canonical snapshot of what is actually built and what is still open. When code
state changes materially, update this file in the same pass. If this file and
the source disagree, the source wins — then fix this file.

Last updated: 2026-05-20.

## Current Phase

Post-V11. The game is playable end to end: career creation, weekly command
loop, official-rules match replay, playoffs, offseason ceremonies, and
multi-season dynasty history all work in the browser. The post-V11 redesign
is now in progress: **Plan A (hybrid driver architecture + Tier 1 engine)
shipped on 2026-05-20**, and Plans B/C/D live in
`docs/specs/2026-05-20-post-v11-redesign-brief/`. The current focus remains
**refinement and gameplay optimization**, not unrelated new systems.

## Shipped And Verified

- **V11 — Official USA Dodgeball Rules Integration** (shipped 2026-05-19) — see `docs/specs/MILESTONES.md` and `docs/specs/2026-05-20-v11-official-usad-rules/design.md`. Fully integrates warning records, blue cards, and discipline states (Section 34 & 35) with a complete conformance matrix verification.
  - Career creation only: the official ruleset cannot be opted into mid-career. Existing V1–V10 saves remain on the generic ruleset.
  - Rulesets: Foam, No-Sting, and Cloth ruleset profiles are fully supported.
  - Deferred: yellow/red card tournament persistence, designated retriever realism, pinching, flight kills, injuries, interference, player collision, bracket expansion, and full administrative rules.
  - Conformance matrix reference: verified completeness of all must-have official rules in `tests/test_official_conformance_matrix.py`.
- **Post-V11 redesign — Plan A: Hybrid driver architecture + Tier 1 engine** (landed 2026-05-20) — see `docs/specs/2026-05-20-post-v11-redesign-brief/plan-a-hybrid-driver.md`. New `EngineDriver` protocol with `RecTier1Driver` (Local Rec League, brief §3.5) and `OfficialDriver` (wraps V11). New primitives: `fatigue`, `flood_throws`, `stall_timer`, and `moment_events` (six-moment contract). V11 / USAD tests still pass. Tier 1 sanity probe lives at `tools/tier_1_sanity_probe.py`. Plans B/C/D remain queued in `tier-1-roadmap.md`.
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
2. **Future AI Program Managers / Rival Adaptation Loop (partially
   scaffolded).** `ai_program_manager.py` (~100 lines) exists and is wired into
   `command_week_service.py` and `use_cases.py`, but this work no longer owns
   the V11 label because V11 shipped as Official USA Dodgeball Rules. Re-slot it
   into the next milestone before writing a spec. Roadmap intent:
   `docs/specs/long-range-playable-roadmap.md`.
3. **Future Broadcast / Presentation layer.** Not started. Roadmap only. Its
   milestone number should be assigned after the AI Program Managers work is
   re-slotted.
4. **Product-coherence-audit follow-ups.** The 2026-05-15 audit
   (`docs/archive/product-coherence-audit.md`) proposed 10 coherence fixes plus
   10 "make it feel real" changes. Several label/copy fixes appear to have
   landed in later commits, and Fix 1 ("Did Your Plan Work?" verdict) now has a
   backend generator in `voice_verdict.py` plus aftermath payload coverage. The
   audit was still **never systematically reconciled** against current code, so
   a verification pass is owed for the remaining items.
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
