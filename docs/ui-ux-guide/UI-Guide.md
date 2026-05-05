Hell yeah — this is the right move. The original Gemini prompt is good for **image generation**, but for **Codex implementation** it needs to be converted into a **design system + UI engineering brief**. Also, the running-track prompt conflicts with the Golden Lap vibe because it asks for realism, cinematic sunlight, shadows, turf detail, and ambient occlusion. That’s pretty, but it’s not the clean “manager sim data toy” look.

For Dodgeball Manager, the style should serve the project’s core rule: **the UI must make the sim feel honest** — visible ratings, visible context, logged RNG, and no “animation decided” ambiguity. That lines up with the project docs: outcome-first rendering, event logs as truth, and data-heavy feedback are foundational pillars.   

Here’s the optimized Codex-ready prompt:

````md
# Codex Task: Implement Dodgeball Manager UI/UX Style Guide
## Golden Lap-Inspired, Dodgeball-Native, Integrity-First Manager Sim UI

You are working on Dodgeball Manager, an integrity-first sports management simulation where match outcomes are driven by visible ratings, visible context, logged RNG, and uniform rules. The UI must reinforce trust: the player should always feel that the game is showing what actually happened, not dressing up hidden magic.

Your task is to implement a cohesive UI/UX style guide inspired by the clean, flat, retro-minimalist presentation of Golden Lap, but translated into Dodgeball Manager’s own identity: fictional dodgeball league, top-down court visualization, tactical manager screens, player progression, match reports, standings, and dynasty history.

Do not clone Golden Lap directly. Use it as a design reference for restraint, clarity, color discipline, flat vector forms, Swiss-style layouts, and readable simulation data.

---

## 1. Product UX North Star

The UI should feel like:

> A retro athletic department dashboard for a fictional dodgeball league: clean, flat, tactile, readable, slightly playful, but never noisy.

The game is a management sim first. The UI should make stats, tactics, ratings, match logs, and season context feel beautiful instead of spreadsheet-grindy.

Core emotional target:
- “I trust what I’m seeing.”
- “I can diagnose why I won or lost.”
- “My fictional players feel real.”
- “The game looks stylish without hiding information.”
- “The match replay is visual proof of the event log, not a separate truth.”

---

## 2. Non-Negotiable Design Principles

### A. Sim Integrity Must Be Visible
Every UI surface should support the project’s prime directive:

- No hidden boosts.
- No fake drama.
- No unexplained outcomes.
- No UI animation that implies something different from the event log.
- No visual effect that obscures probabilities, ratings, rolls, or match state.

When showing an out, catch, dodge, miss, comeback, upset, or clutch play, the UI should be able to surface:
- actor
- target
- relevant ratings
- probability
- RNG roll
- outcome
- event log reference / tick / phase

### B. Event Log Is Canon
All match visuals, reports, highlights, box scores, and story snippets must be derived from the existing MatchEvent log.

Do not create separate UI-only state that can contradict the log.

If visual playback and the log disagree, the visual is wrong.

### C. Flat Vector Over Realism
Use:
- 2D flat vector shapes
- crisp edges
- uniform line weights
- solid colors
- limited palette
- simple panels
- readable tables
- symbolic court/player/ball representations

Avoid:
- photorealism
- 3D
- realistic lighting
- gradients
- glossy buttons
- heavy shadows
- texture-heavy backgrounds
- cinematic sports broadcast clutter
- particle spam
- unnecessary animation

### D. Data Should Look Designed, Not Dumped
Stats are a feature. Make box scores, ratings, sliders, logs, and standings feel curated.

Use:
- cards
- clean stat chips
- progress bars
- compact badges
- sortable tables
- subtle section dividers
- clear hierarchy
- collapsible advanced details

---

## 3. Visual Identity

### Style Keywords
Use this visual DNA across the app:

- 2D flat vector interface
- retro sports management dashboard
- Swiss International Style layout
- Dieter Rams-inspired restraint
- analog gym scoreboard energy
- fictional athletic department paperwork
- clean rec-league stat sheet
- minimalist indie sim UI
- warm paper background
- matte colors
- crisp geometric shapes
- restrained playful character

### Era + Mood
Do not make it “1970s motorsport.” Translate that influence into dodgeball:

- late-70s / early-80s gymnasium signage
- school athletics record board
- retro rec-center bulletin board
- analog scoreboard typography
- printed tournament bracket sheets
- physical education class nostalgia
- league office paperwork

The game should feel warm, smart, and slightly scrappy — not sterile SaaS, not AAA sports broadcast.

---

## 4. Color System

Implement centralized design tokens. Do not scatter hex values through the codebase.

Suggested palette:

```css
--dm-cream: #F4F1EA;        /* primary background, warm paper */
--dm-paper: #FFF9EC;        /* raised panels */
--dm-charcoal: #242428;     /* primary text / dark UI */
--dm-muted-charcoal: #3A3A40;
--dm-brick: #B75A3A;        /* dodgeball / court accent */
--dm-burnt-orange: #C66A32; /* primary action accent */
--dm-mustard: #D6A23A;      /* warnings, highlights, awards */
--dm-teal: #6FA6A0;         /* secondary accent, calm info */
--dm-sage: #8FA87E;         /* success, growth, scouting */
--dm-gym-blue: #6C8FB3;     /* cool team accent */
--dm-red: #C94E3F;          /* danger, eliminated, high risk */
--dm-off-white-line: #EEE3D0;
--dm-border: #2F2F35;
````

### Color Usage Rules

* Backgrounds should usually be cream or paper.
* Use charcoal for text and borders.
* Use burnt orange / brick for dodgeballs, danger, and match action.
* Use teal / gym blue for information and neutral UI states.
* Use mustard sparingly for awards, milestones, and “signature moments.”
* Use sage for development, scouting, facilities, and positive growth.
* Red should mean risk, eliminated, injury, fatigue danger, or negative swing.
* Never use bright neon unless intentionally added later as a separate theme.

### Accessibility

* Maintain strong contrast for all text.
* Ratings bars must remain distinguishable without relying only on color.
* Use labels, icons, and numbers alongside color coding.

---

## 5. Typography

Use clean sans-serif typography. Prefer available system-safe fonts unless the project already supports bundled fonts.

Recommended hierarchy:

* App title / major headers: bold condensed sans-serif feel if available.
* Section headers: uppercase or small caps, tracked slightly.
* Body/table text: readable sans-serif.
* Numeric data: tabular figures if available.

Suggested CSS/font stack if applicable:

```css
font-family: Inter, IBM Plex Sans, Atkinson Hyperlegible, system-ui, sans-serif;
font-variant-numeric: tabular-nums;
```

If using Tkinter or another non-web UI toolkit, create equivalent constants:

* FONT_TITLE
* FONT_HEADER
* FONT_BODY
* FONT_MONO_NUMERIC
* FONT_SMALL
* FONT_BADGE

Typography should feel like a clean stat sheet, not a fantasy RPG menu.

---

## 6. Layout System

Use a strict grid-based layout.

General rules:

* 8px spacing base unit.
* Panels should align cleanly.
* Avoid floating random widgets.
* Keep dense screens readable through grouping.
* Prioritize left-to-right diagnostic flow:

  1. Current context
  2. Main decision/data
  3. Supporting details
  4. Advanced audit trail

Recommended screen structure:

* Top bar: league/team/season context
* Left rail or tabs: major sections
* Main content panel: primary information
* Right inspector panel: selected item details
* Bottom drawer: logs, tooltips, advanced audit data

Use these shared layout primitives:

* `Page`
* `Panel`
* `Card`
* `StatChip`
* `Badge`
* `Table`
* `RatingBar`
* `TendencySlider`
* `EventLogRow`
* `CourtCanvas`
* `Timeline`
* `Tooltip`
* `InspectorDrawer`

---

## 7. Core Components

### A. Panels / Cards

Flat rectangular panels with:

* cream or paper fill
* 1px charcoal or muted border
* no heavy shadow
* optional 2px offset border for retro print feel
* rounded corners only if already present in project style; keep subtle

Card types:

* PlayerCard
* TeamCard
* MatchCard
* AwardCard
* SignatureMomentCard
* FacilityCard
* NewsHeadlineCard

### B. Rating Bars

Rating bars are critical.

Each player rating should show:

* rating name
* numeric value
* horizontal bar
* optional role relevance indicator

Example:

* Power 84
* Accuracy 77
* Catching 62
* Dodge 91
* Awareness 70
* Stamina 68

Use flat solid fills only. No gradients.

### C. Badges

Use compact badges for:

* archetype
* trait
* fatigue state
* morale state
* coach tendency
* injury risk
* rookie/veteran
* role label
* meta patch modifier

Examples:

* POWER ARM
* IRONWALL
* CLUTCH
* LOW STAMINA
* HIGH TEMPO
* TARGETS STARS

### D. Sliders

Tactics sliders should feel mechanical and legible.

Coach tendency sliders:

* Target Stars
* Target Ball-Holder
* Risk Tolerance
* Sync Throws
* Tempo / Stall
* Rush Frequency
* Catch Attempt Bias
* Rush Proximity

Each slider should include:

* label
* current value
* short readable effect
* expected behavior preview
* warning if behavior has stamina/risk cost

Example:
“Sync Throws: High — more 2v1 volleys, higher stamina burn.”

### E. Tables

Tables are first-class UI objects.

Must support:

* clear row spacing
* sticky headers if possible
* sortable columns if current UI stack supports it
* numeric alignment
* team/player icons or color chips
* compact but readable density

Tables needed:

* roster
* standings
* schedule
* box score
* player stats
* career stats
* match log
* record book

### F. Event Log Rows

Every event row should be scannable at two levels:

Collapsed:

* tick/time
* event type
* actor
* target
* outcome

Expanded:

* relevant ratings
* probability
* RNG roll
* modifiers
* coach policy context
* rule/meta patch context
* state diff

Example collapsed:
`00:18 | THROW | Marlon “Laser” Reed → Theo Park | HIT`

Example expanded:
`Accuracy 82 vs Dodge 69 | p_on_target 0.71 | roll 0.43 | outcome HIT | seed 18422 | phase volley_3`

---

## 8. Top-Down Match Visualization

Implement a flat 2D top-down dodgeball court visualization.

### Court Style

The court should be:

* rectangular gym court
* flat vector
* warm muted maple/tan or cream base
* center line clearly visible
* neutral zone / attack lines if ruleset uses them
* back boundary lines
* team sides visually distinct but not overwhelming
* no realistic wood grain unless extremely subtle and flat
* no dynamic lighting
* no shadows that obscure gameplay

### Players

Represent players as simple circles or rounded tokens:

* team color ring
* jersey number or initials
* tiny status indicator if holding ball
* eliminated players move to bench/out zone
* selected player has clean outline, not glow spam

### Balls

Represent dodgeballs as small brick/burnt-orange circles.
Show possession clearly:

* ball next to player token if held
* ball path line during replay
* small flat motion trail only if it does not obscure the court

### Replay Principle

The court visualization must consume the MatchEvent log.

Do not implement physics that can change the result.
The renderer may animate trajectories consistent with already-resolved outcomes.

Architecture:

1. Outcome already resolved by engine.
2. UI receives event log.
3. Court renderer draws feasible trajectory consistent with event.
4. Animation plays as visual explanation only.

### Court Negative Prompt

Do not make the court:

* realistic 3D
* glossy
* cinematic
* shadow-heavy
* crowded with spectators
* hard to read
* more detailed than the player/ball tokens

The court is an information surface, not a poster.

---

## 9. Screen-Specific Direction

### A. Main Dynasty Hub

Purpose: “Where am I in the season?”

Show:

* current team record
* next match
* league week
* recent result
* top player snapshot
* League Wire headlines
* standings mini-table
* facility/scouting reminders

Visual tone:

* dashboard
* clean league office corkboard
* retro stat packet

### B. Roster Screen

Purpose: “Who are my players and what are they good at?”

Show:

* player table
* role/archetype
* core ratings
* fatigue
* traits
* age
* development arrow
* season stats
* selected player inspector

Important:

* Make role fit obvious.
* Let the player quickly identify throwers, catchers, dodgers, all-rounders, and liabilities.

### C. Tactics Screen

Purpose: “How do I want my team to play?”

Show:

* coach tendency sliders
* preset playstyles
* expected behavior summary
* roster fit warnings
* stamina/risk implications

Preset cards:

* Power-Arm Aggro
* Catch-Heavy Attrition
* Sniper Control
* Swarm & Overload
* Balanced Spreadsheet Enjoyer

Each preset card should show:

* strengths
* risks
* best roster fit
* expected match log changes

### D. Match Preview

Purpose: “Why might we win or lose?”

Show:

* team comparison
* star players
* key matchup
* style clash
* relevant ratings
* coach tendencies
* expected pressure points

Example:
“Your Catch-Heavy Attrition style counters their Power-Arm Aggro if your catchers survive the opening volley.”

### E. Match Playback

Purpose: “Show me the sim truth.”

Show:

* top-down court
* current players alive
* balls in possession
* active event
* compact log
* optional speed controls
* probability drawer for selected event

Must support:

* pause
* step event
* jump to highlight
* inspect event

### F. Match Report

Purpose: “Why did that result happen?”

Show:

* final score / survivors
* MVP / hero
* box score
* player stats
* turning points
* event log
* probability outliers
* upset explanation if applicable
* shot/target map if available

Important:
If a weird upset happens, the report must explain it through ratings, probabilities, rolls, tactics, fatigue, and key moments.

### G. Player Profile

Purpose: “Make fictional players matter.”

Show:

* portrait/avatar placeholder
* archetype
* nickname
* ratings
* traits
* season stats
* career stats
* signature moments
* development history
* awards
* injury/fatigue history

Visual tone:

* retro trading card meets scouting dossier.

### H. League / Standings Screen

Purpose: “Make the world feel alive.”

Show:

* standings
* schedule
* league leaders
* awards race
* recent headlines
* rivalries
* record book

### I. League Wire

Purpose: “Generate narrative from real sim events.”

Show:

* template-based headlines
* matchday summaries
* records broken
* upset alerts
* rivalry moments
* player milestones

Do not use fake narrative not backed by data.

---

## 10. Art Direction for Generated/Static Assets

If creating or prompting for assets, use these dodgeball-specific prompts.

### A. Dodgeball Player Portrait

A minimalist 2D flat vector portrait of a fictional dodgeball athlete for a sports management simulation game. Clean ligne claire line art, uniform medium line weight, solid colors only, no gradients, no shading. The athlete wears a retro gym jersey with simple geometric details, sweatband, and warm rec-league attitude. Matte cream background, muted brick orange, mustard yellow, teal, sage, and charcoal palette. Stylized cartoon proportions, tasteful retro athletic department aesthetic, indie sim UI asset. No realism, no 3D, no glossy lighting, no shadows, no busy background.

### B. Coach Portrait

A minimalist 2D flat vector portrait of a fictional dodgeball coach, clipboard in hand, retro gym polo, whistle, calm tactical expression. Swiss-style sports management UI asset, clean lines, solid color blocks, warm cream background, muted retro palette, no gradients, no realism, no lighting effects.

### C. Top-Down Dodgeball Court

A minimalist top-down 2D flat vector dodgeball court for a sports management simulation replay screen. Rectangular gym court, clean center line, neutral zone markings, back boundary lines, simple player circles, small burnt-orange ball dots, readable spacing, warm matte cream/maple court color, charcoal linework, teal and brick team accents. Designed as a functional UI surface, not realistic art. No 3D, no shadows, no cinematic lighting, no spectators, no texture-heavy floor, no glossy effects.

### D. UI Screen Mockup

A clean 2D user interface screen for a fictional dodgeball management simulation game. Retro-minimalist sports dashboard, flat vector panels, warm cream paper background, charcoal text, burnt orange and teal accents, Swiss International typography, compact stat cards, player rating bars, coach tendency sliders, box score table, collapsible event log. Sleek indie sim UI, information-dense but uncluttered. No realism, no gradients, no drop shadows, no glossy buttons, no busy background.

---

## 11. Implementation Plan

First inspect the existing repo and UI stack. Do not rewrite the app unless necessary.

If the app currently uses Tkinter:

* Add a centralized style/theme module.
* Define colors, fonts, spacing, border styles, and component helpers.
* Refactor existing GUI screens to use shared style constants.
* Preserve current functionality.
* Do not break CLI output, persistence, deterministic match logs, or tests.

If the app has or later gains a web UI:

* Implement design tokens as CSS variables.
* Build reusable components.
* Keep match visualization data-driven from event logs.

Suggested file/module additions:

* `src/dodgeball_sim/ui_style.py`
* `src/dodgeball_sim/ui_components.py`
* `src/dodgeball_sim/court_renderer.py`
* `src/dodgeball_sim/ui_formatters.py`

The UI style layer should not modify simulation logic.

---

## 12. Engineering Guardrails

Do:

* centralize style tokens
* keep UI derived from canonical data
* add snapshot/demo screens if useful
* keep event-log inspection easy
* make hidden details expandable, not absent
* preserve all existing tests
* add UI smoke tests if feasible
* keep deterministic output stable

Do not:

* hardcode colors everywhere
* introduce unlogged UI randomness
* imply outcomes not backed by MatchEvents
* let animation override resolved outcomes
* add heavy dependencies without justification
* replace working GUI architecture casually
* hide probabilities/rolls behind vibes
* make the app look like generic SaaS
* over-polish before core screens are coherent

---

## 13. Acceptance Criteria

The implementation is successful when:

1. The UI has a centralized Golden Lap-inspired, Dodgeball-native theme.
2. Existing screens use consistent colors, fonts, spacing, panels, and tables.
3. Roster, tactics, match report, and event log are more readable than before.
4. Match visualization, if touched, is clearly event-log-driven.
5. Probabilities, rolls, and outcomes remain inspectable.
6. No sim logic changes are introduced unless explicitly requested.
7. All existing tests still pass.
8. The app feels like a stylish retro sports management sim, not a generic desktop utility.
9. The design improves trust in the simulation instead of covering it up.
10. Any new component has a clear reason to exist and supports the manager-sim loop.

---

## 14. Final Design Mantra

Make Dodgeball Manager feel like:

> Golden Lap’s clean retro information design, Teamfight Manager’s readable tactical loop, and Pocket GM’s sim-integrity obsession — but inside a fictional dodgeball league with its own identity.

The UI should be pretty because it is clear.
The replay should be exciting because it is truthful.
The data should be dense because it is useful.
The player should lose, inspect the evidence, and say: “Yeah… that’s on me.”

```

**My blunt take:** this is way stronger than trying to prompt Codex with “make it look like Golden Lap.” That phrase alone is too vague and also risks Codex doing cosmetic surface-level stuff. This version tells Codex **what to build, what not to break, where the style belongs, and why the UI exists**. That’s the sauce.
```
