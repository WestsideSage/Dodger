# UI / UX Implementation Learnings — April 26, 2026

Technical and product-facing lessons from the Tkinter UX overhaul. These are the decisions that are easy to forget and expensive to rediscover.

---

## First Impression Matters More Than Feature Count

The app already had meaningful functionality, but the initial screen read like a utility panel instead of a playable sim. The biggest usability improvement came from changing the **first 10 seconds** of the experience:

- hide the control rail by default
- lead with a clear home screen
- show direct actions (`Play Now`, `Edit Teams`, `Randomize`)
- put a court surface on screen immediately

The lesson is that onboarding hierarchy mattered more than adding more features.

---

## Tkinter Can Support Better Product UX If Layout Carries the Weight

The toolkit still looks native and somewhat rigid, but it became much more legible once the UI stopped depending on raw form rows and default notebook behavior for structure.

The highest-leverage changes were:

- shared theme tokens in `ui_style.py`
- a few reusable presentation primitives in `ui_components.py`
- renaming tabs to product-facing destinations (`Home`, `Roster Lab`, `Coach Board`, `Replay Arena`)
- using summary strips and spotlight panels instead of long unstructured text

The constraint is not “Tkinter cannot look good.” The constraint is “Tkinter punishes weak hierarchy very quickly.”

---

## Replay Must Be a Destination, Not a Subpanel

The replay surface only started to feel like “game UI” once it became the dominant object on the screen.

Useful pattern:

- make the court span the top of the replay screen
- keep controls close to it
- treat the event log and inspector as support systems
- reflect the currently selected event in a compact summary strip

If the court is visually smaller or less important than forms or logs, the app stops feeling like a game.

---

## Sidebars Should Be Optional in Sandbox-Style Screens

A permanently visible control rail made the product feel like configuration software. Making it collapsible improved both clarity and mood.

Recommendation for future screens:

- default to content-first
- make setup/config surfaces summonable
- avoid dedicating the left edge permanently to dense controls unless the user is actively editing

This is especially important for replay and roster exploration.

---

## Narrative Copy Has To Stay Utility-First

Some early phrasing risked sounding like design copy instead of product copy. The better pattern was:

- short headline with one job
- one sentence explaining what the screen is for
- labels that describe action or state
- replay/report text that stays tied to actual sim evidence

Good UX improvement came from sounding more like a simulation product and less like a themed mockup.

---

## Manual Screenshot Review Was Necessary

The biggest issues were not obvious from reading code:

- clipping at realistic widths
- the control rail overpowering the app
- the replay court lacking authority
- text blocks feeling flat even when technically correct

The screenshot walkthroughs in:

- `output/ui-review/`
- `output/ui-review-phase2/`
- `output/ui-review-phase3/`

were essential. Future UI work should continue using screenshot review as a required verification step, not a nice-to-have.

---

## Safe Refactor Boundary

The UI overhaul stayed safe because the refactor respected this boundary:

- UI modules can consume canonical data
- UI modules must not modify simulation logic
- replay rendering is derived from `MatchEvent`
- tests remain the safety net for engine integrity

That separation held. `python -m pytest -q` stayed green through the full UX pass.
