# UI / UX Retrospective — April 26, 2026

**Focus:** Desktop UI rejuvenation for Dodgeball Manager  
**Area touched:** Tkinter GUI only  
**Tests:** `python -m pytest -q` passing throughout final state

---

## What Changed

This session moved the product from “retro management utility” toward “playable dodgeball sim sandbox.”

Major work completed:

- introduced a centralized theme + reusable UI primitives
- restructured the GUI into product-facing destinations
- added a clearer `Home` screen with immediate actions
- demoted the control rail and made it collapsible
- promoted replay to a first-class destination
- improved roster, tactics, and league-wire readability
- performed repeated manual screenshot reviews and used those findings to drive follow-up passes

New/updated supporting modules:

- `src/dodgeball_sim/ui_style.py`
- `src/dodgeball_sim/ui_components.py`
- `src/dodgeball_sim/ui_formatters.py`
- `src/dodgeball_sim/court_renderer.py`
- `src/dodgeball_sim/gui.py`

---

## What Worked

### 1. Iterating Through Screenshots Instead of Guessing

Three screenshot passes were valuable:

- `output/ui-review/`
- `output/ui-review-phase2/`
- `output/ui-review-phase3/`

The work improved meaningfully only after reviewing actual captured windows. The most important improvements came from fixing things that looked wrong on-screen rather than things that merely felt incomplete in code.

### 2. Content-First Home Screen

The strongest UX improvement came from replacing the “controls-first” opening state with:

- a clear one-line promise
- direct next actions
- a visible court surface
- team spotlights and matchup context

This made the app easier to understand without documentation.

### 3. Replay-Centered Framing

Putting the court at the top of `Replay Arena` made the UI feel more like a game and less like an analysis console.

---

## What Still Feels Weak

### 1. Native Tkinter Chrome Is Still Visible

The app is much clearer now, but it still does not read like a fully modern game client. The toolkit imposes limits on:

- tab styling
- button feel
- typography richness
- spacing precision

The current result is better product UX, not yet a strong visual identity.

### 2. Character and Team Identity Are Still Thin

The screens are more understandable, but teams and players still need stronger personality:

- richer team-color framing
- better player cards
- more expressive spotlight areas
- stronger visual differentiation between squads

### 3. Replay Readability Can Go Further

Replay is now correctly emphasized, but it still has room for:

- clearer possession markers
- better event emphasis
- highlight state styling
- stronger mapping between selected event and court focus

---

## Recommended Next Steps

1. Add a stronger team identity layer to `Home`, `Roster Lab`, and `Replay Arena`.
2. Improve selected-player presentation so the roster screen feels more collectible and less tabular.
3. Add more replay-state affordances: selected thrower, target emphasis, out-zone clarity, and better event badges.
4. Revisit tab/navigation styling if Tkinter allows further improvement without brittle hacks.
5. Keep manual screenshot review as a required checkpoint for all UI changes.

---

## Final Assessment

This was a successful UX correction pass.

The product now communicates:

- what it is
- what the player can do next
- where to inspect results
- why replay matters

It still does not feel like a fully branded game client, but it no longer opens with the “what am I looking at?” reaction that triggered the redesign. The current UI is a much better foundation for future presentation work.
